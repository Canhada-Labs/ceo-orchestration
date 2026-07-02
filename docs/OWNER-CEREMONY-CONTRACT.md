# Owner Ceremony Contract

> Single source of truth for what every `OWNER-*.sh` ceremony script
> MUST do. Codified Session 75 (2026-04-29) closing Codex external
> Finding 10 — `OWNER-SESSION-73-FINAL-CEREMONY.sh:240` advertised
> "verify 0 regressions" but the pytest + governance blocks fell
> through with `warn "Continuing — review failures before commit"`
> instead of `exit 1`. Fail-open misadvertised as fail-closed.

## Contract (mandatory)

1. **Fail-closed by default.** A ceremony script that runs validators
   (pytest, governance, lint, schema-consistency, exec-bit, etc.) MUST
   `exit ≠ 0` on validator failure unless explicit opt-in is given.

2. **`--advisory` opt-in.** Scripts MAY accept `--advisory` as the
   first argument to enable the legacy warn-and-continue behavior
   (used for split workflows where the Owner intentionally wants to
   inspect failures before deciding to commit). The flag MUST be
   documented in the script header.

3. **Distinct exit codes per block.** Each fail-closed block uses a
   unique exit code so the failure point is grep-able from CI logs:

   | Block | Exit code |
   |---|---|
   | Sentinel signature verification | 2 |
   | ADR file presence / schema | 3 |
   | Plan flip preflight | 4 |
   | SHA-pin / function-length | 5 |
   | npm version sync | 6 |
   | pytest | 7 |
   | governance validator | 8 |
   | function-length advisory | 9 |
   | Owner-asc populated | 10 |

4. **No silent passes.** A block that prints `[OK]` MUST have actually
   verified the thing. A block that detects failure MUST print `[X]`
   with the cause AND exit ≠ 0 (or warn-only IF `--advisory`).

5. **Idempotent.** Re-running a ceremony after partial completion MUST
   resume from where it left off without duplicating side-effects.
   Use `git status --porcelain` checks before re-staging files.

## Pattern

```bash
#!/usr/bin/env bash
set -u
set -o pipefail

# Fail-closed by default per docs/OWNER-CEREMONY-CONTRACT.md.
# Pass --advisory to opt-in to legacy warn-and-continue.
ADVISORY=0
if [[ "${1:-}" == "--advisory" ]]; then
    ADVISORY=1
    shift
fi

# ... preflight + signing + staging ...

# Validator block — fail-closed unless --advisory
if python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ -q; then
    ok "Tests passed"
else
    fail "Tests had failures (see above)"
    if [ "$ADVISORY" = "1" ]; then
        warn "--advisory mode — continuing despite test failures"
    else
        fail "Aborting ceremony (re-run after fix, or pass --advisory to opt-in)"
        exit 7
    fi
fi
```

## When `--advisory` is appropriate

- **Split workflow:** Owner runs ceremony script BEFORE all canonical
  edits land (pre-stage), expects validators to fail, will run again
  fail-closed after the second commit.
- **Forensic ceremony:** documenting a regression — the script itself
  is the evidence; the failure is the point.
- **Never for promote-to-main:** the GA path (tag cut, release
  workflow) MUST always run fail-closed.

## When fail-closed is non-negotiable

- Every block in `OWNER-SESSION-NN-*-CEREMONY.sh` after the sentinel
  signature step.
- Any block that mutates `.claude/adr/` or canonical-guarded paths.
- Any block that flips plan status to `done`.
- Any block immediately preceding a `git commit` instruction.

## Anti-patterns (never do)

1. **`warn "Continuing — review failures before commit"`** when the
   block label says "verify N regressions" (Session 73 regression
   pattern; closed by Session 75 Finding 10).
2. **Suppress non-zero exit** with `|| true` on a block that's
   supposed to enforce a contract.
3. **`set +e` around a validator block** without restoring `set -e` /
   explicit exit handling immediately after.
4. **Single exit code for all failure modes** — the Owner can't tell
   from CI log whether pytest or governance failed.

## Backport policy

When a new ceremony script is added under `OWNER-*.sh` (repo root) or
`.claude/scripts/owner-ceremony/`, copy the pattern above. When a
legacy script is touched for any reason, audit it for the
warn-and-continue anti-pattern and convert to fail-closed if the
block label promises enforcement.

---

## v2 expansion (PLAN-065 §4.5.B — added 2026-05-04)

### Idempotency contract (per PLAN-063 R1 consensus C2)

A ceremony script run twice on the same input must produce identical
git tree state. Specifically:

1. **No append-only side effects.** A second run must not double-stage
   files, double-commit, or duplicate sentinel `.asc` signatures.
2. **State-check before mutation.** Before each block that mutates,
   `git status --porcelain` OR a file-existence check OR a checksum
   compare. Skip if the desired state is already reached.
3. **Audit-emit dedupe.** If the ceremony emits audit-log entries
   (e.g. `kernel_override_used`), the entry should NOT be re-emitted
   on a re-run after partial success. Use a state flag (env var,
   `.claude/state/ceremony-<slug>-completed` marker) to gate emit.

### Transactional rollback (per PLAN-063 R1 consensus C2)

A ceremony has a **commit-point** (the `git commit` that finalizes the
flip). Before commit-point: every block's failure must be cleanly
reversible — `git restore --staged` un-stages, file modifications can
be discarded with `git restore`. After commit-point: rollback is via
NEW commit (`git revert <SHA>`) — never `git reset --hard` to a SHA
that was pushed.

Pattern:

```bash
COMMIT_POINT_PASSED=0

# Pre-commit blocks (idempotent, reversible)
do_block_a || { rollback_pre_commit "block_a"; exit 11; }
do_block_b || { rollback_pre_commit "block_b"; exit 12; }

# Commit point
git commit -m "ceremony X" || { rollback_pre_commit "commit"; exit 13; }
COMMIT_POINT_PASSED=1

# Post-commit blocks (must succeed OR rollback via revert)
do_block_c || {
  if [ "$COMMIT_POINT_PASSED" = "1" ]; then
    fail "block_c failed AFTER commit point — rollback needs git revert"
    fail "Inspect: git log -1 --format=%H + decide if revert is safe"
    exit 14
  fi
}
```

### `generate-ceremony.sh` integration

Since S81 Phase 2 (`.claude/scripts/local/generate-ceremony.sh`, 440 LoC + 8
tests), new ceremony scripts MUST be generated by that tool. It
codifies:

- 6 pre-emit guards (G1-G6): scope-cap ≤15 paths, sentinel format
  parser-compatible, ADR slot collision check, plan frontmatter
  status precondition, GPG key allowlist, owner.asc populated
- 8 runtime hardenings (R1-R8): `set -u + set -o pipefail`, distinct
  exit codes, unbuffered stdout, GPG SIGPIPE retries, idempotent
  re-stages, single-batch sentinel sign, fail-closed by default,
  `--advisory` opt-in flag

Hand-written ceremony scripts are deprecated for new work. If you must
write one (e.g. forensic ceremony documenting a regression), comment
explicitly why generate-ceremony.sh wasn't used.

### Single-batch sentinel sign (S81 Phase 2 R6)

A ceremony covering N canonical paths uses ONE sentinel `approved.md`
listing all N paths in its `Scope:` block, ONE GPG sign of the
detached `.asc` signature. Multiple-sentinel ceremonies are an
anti-pattern — they multiply Owner physical (N passphrases) without
adding security (sentinel SHA-binds the bundle directory tree, not
individual files).

Exception: if blocks need to mutate the sentinel itself between sub-
batches (e.g. sentinel scope grows post-validation), use a **retro-
sentinel** pattern (S81 Codex P1 incident `82f0c38`): keep the
original sentinel + add a NEW sentinel for the new scope; do NOT
re-sign the original. Document both `.asc` files in DIFF.md.

### Cross-LLM gate hook (per ADR-095 §gate-#6 + ADR-103)

After commit-point, before `git push`, ceremony SHOULD invoke Codex
MCP cross-LLM re-pass on the diff:

```bash
# Cross-LLM re-pass (advisory; manual eyeball if Codex MCP unavailable)
if command -v codex >/dev/null && [ "${SKIP_CODEX_REPASS:-}" != "1" ]; then
  codex review --base "$ANCHOR_SHA" --head HEAD \
    --output ".claude/state/ceremony-codex-repass-$(date +%s).md" \
    || warn "Codex re-pass had findings — review before push"
fi
```

If Codex MCP is unavailable: ceremony is allowed to proceed (vibecoder-
only thesis ADR-096 — adopters are responsible for their own
cross-LLM discipline). The framework's GA tag pipeline (`release.yml`)
runs validate.yml + actionlint as the Claude-only gate; Codex re-pass
is in addition, not replacement.

### When v2 hardening doesn't apply

- **Documentation-only ceremonies** (no canonical edits, no plan flip):
  v2 transactional rollback is overkill. Use generate-ceremony.sh
  `--mode=docs-only` (G1+G3 guards only).
- **Pure rollback ceremonies** (reverting a prior commit): the
  ceremony IS the rollback. Use a single `git revert` block;
  v2 transactional rollback semantics don't compound.

Last reviewed: 2026-05-04 (PLAN-065 §4.5.B — v2 expansion).
