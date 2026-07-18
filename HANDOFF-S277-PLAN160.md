# HANDOFF — S277 — PLAN-160 canonical-edit hardening (Owner-gated ceremony)

**Status:** W1 + W2 DONE; W3 prep DONE; **only the Owner GPG ceremony
remains.** The prep commits (tests + plan + ceremony materials) are **already
pushed to origin/main** (they passed the pre-push CI-equivalent gate) — this is
intentional so the ceremony's origin-sync preflight passes. The **security fix
itself is NOT on origin**: it lives in `staged/` (gitignored) and lands ONLY
via your GPG ceremony below. Review, then run the ceremony and push the
ceremony commit.

## What landed autonomously (main, local — NOT pushed)

| Commit | What |
|---|---|
| `272714a` | plan `reviewed → executing` |
| `489996f` | **W1** verify instruments (`test_canonical_edit_council_findings.py`) |
| `2b8533b` | **W2** C-property → behavioral |
| `7b73777` | **W2** pair-rail regression guards + comment fixes |
| `<this>`  | **W3-prep** ceremony materials + plan update + this handoff |

The **fix itself** and the **2 ADRs** are in `.claude/plans/PLAN-160/staged/`
(gitignored, machine-local) — pinned by the tracked manifest
`.claude/plans/PLAN-160/inputs.sha256`. They land only via the ceremony.

## The change (S276 council findings A/C/D on the canonical-edit gate)

- **A (HIGH gate-bypass)** — multi-candidate events (`mcp__*` / `apply_patch`)
  broke at the first canonical candidate and gated only it, so a granted-first
  path smuggled a later ungranted canonical edit. Fix: most-restrictive scan
  over all candidates, emit-once, cap 512 fail-closed, scan-fault fail-closed.
- **C (MED fail-open)** — `decide()` resolve fault on a confirmed-canonical
  path returned allow. Fix: fail-closed (`canonical_edit_hook_fault`).
- **D (MED path bypass)** — `_is_canonical` anchored only on CWD; a relative
  canonical path from a foreign CWD classified non-canonical → allowed. Fix:
  dual-anchor (CWD + repo_root), made total so a symlink-loop `RuntimeError`
  can't fail-open the scan.
- **B / E / F** — reviewed, no-action (comment-only / documented boundaries).

## Verification already done (CEO)

- Wave-1 repros: HEAD `9 passed / 5 skipped / 5 xfailed`; `--runxfail` fails
  exactly the 5 repros; STAGED (`PLAN160_HOOK_PATH`) `19 passed`.
- Clean-clone mirror (staged overlaid on canonical): full `.claude/hooks/tests/`
  **6242 passed, 0 failed**.
- **Pair-rail to APPROVE:** codex round-2 APPROVE (no findings); security
  round-2 **VETO lifted** (re-ran the symlink-loop exploit → blocks; fuzzed
  totality → zero raises; 591 passed); QA APPROVE_WITH_NITS (nits applied).

## RUN THE CEREMONY (copy-paste)

```bash
cd ~/canhada-labs/ceo-orchestration

# 0. GPG agent sanity (only if a prior session left it wedged)
export GPG_TTY=$(tty); gpgconf --kill gpg-agent

# 1. Rehearsal — does everything EXCEPT sign/commit, then restores the tree.
#    Must end "[dry-run] DONE — full rehearsal green".
bash .claude/plans/PLAN-160/land-plan160.sh --dry-run

# 2. Real ceremony — signs the sentinel INLINE with your key, applies the
#    kernel + 2 ADRs + count bump (178→180), commits -S. No auto-push.
bash .claude/plans/PLAN-160/land-plan160.sh

# 3. Verify + push
git log --oneline -1
git verify-commit HEAD
git push origin main

# 4. Watch Validate
gh run watch $(gh run list --workflow validate.yml --branch main --limit 1 --json databaseId --jq '.[0].databaseId')
```

**Rollback:** before push `git reset --hard 7b73777` (or the tip before the
ceremony commit); after push `git revert HEAD`.

## After Validate is green

Flip the plan to done (the `reviewed→done` shortcut is illegal — go via
`executing` + `completed_at` + `related_commits`). I can do this in the next
session, or you can. Optional Wave 4: re-run `/council` on the fixed file once
the grok-lane arg-contract sibling follow-up lands (so it reaches 3-lane).

## Notes / residual (non-blocking, in the ADRs)

- Near-cap all-granted GPG cost (bounded by cap 512; absurd in practice).
- Foreign-cwd relative over-block (fail-closed-safe; widen-only).
- `_forced_out` audit breadcrumb labels the event's first candidate, not
  necessarily the offender (forensic-only; decision is correct).

## Sibling follow-ups (own plans, not this one)

- Council grok-lane arg-contract (grok 0.2.93 `-p` takes prompt as arg, not
  stdin → incompatible with the ADR-114 one-pipe egress).
- perf-gate D3 inter-attempt backoff (PLAN-159 follow-up).
