# Security — Bash canonical-path write guards

**Audience:** framework administrators (Owner + CTO + Security on-call).
**Not user-facing.** Users do not need to read this — the hook fails
closed automatically on the surfaces it covers.

**Last updated:** 2026-05-13 (S116-cont, PLAN-089 Wave B draft).
**Related ADRs:** ADR-010, ADR-040, ADR-115, ADR-116, ADR-117,
ADR-121 (proposed in PLAN-089 Wave C).
**Source:** `.claude/hooks/check_bash_safety.py:332-447` (matcher),
`.claude/hooks/check_bash_canonical_forensic.py` (forensic sibling),
`.claude/plans/PLAN-089/wave-b-audit.md` (audit detail).

---

## §1. Threat model

A Claude Code session has full Bash tool access — every command the
model emits is shell-evaluated. Without a write-shape Bash matcher,
the canonical-edit hook (`check_canonical_edit.py`, sentinel-gated)
is the **only** line of defense against catastrophic governance-file
mutation. But `check_canonical_edit` only fires on Edit / Write /
MultiEdit / `mcp__*` tool calls. A Bash command like

```bash
sed -i '' 's/^.*$//' PROTOCOL.md
```

mutates `PROTOCOL.md` (canonical-tier) without ever invoking the
canonical-edit hook. **Single-edit catastrophic bypass.**

PLAN-084 SOTA-finalization audit (S107-cont) elevated this to a
TIER-4 evolution-roadmap item (R-027). PLAN-085 Wave E.3 landed a
**heuristic v1** matcher closing the obvious cases
(`>` / `>>` / `tee` / `tee -a` / `sed -i` / `git checkout -- path`).
PLAN-089 Wave B closes 14 more vectors (the **matrix v2** matcher).

### §1.1 Specific surfaces covered

| Class | Examples | Matcher branch |
|---|---|---|
| Shell redirect | `> path`, `>> path`, `: > path`, `exec > path` | v1 next-arg |
| Tee | `tee path`, `tee -a path` | v1 tee + tee -a |
| sed in-place | `sed -i ... path`, `sed -i.bak ... path` | v1 sed -i |
| git restore | `git checkout REF -- path` | v1 git checkout |
| Interpreter -c/-e bodies | `python -c "..."`, `node -e "..."`, `ruby -e ...`, `perl -e ...` | v2 #1 + `_scan_blob` two-pass |
| Interpreter -i in-place | `perl -i -pe ...`, `ruby -i -pe ...`, `awk -i inplace ...` | v2 #2 |
| File movers | `cp src dest`, `mv src dest`, `truncate -s 0 dest`, `ln -sf src dest`, `rm dest` | v2 #3 |
| `dd of=` kv form | `dd of=path if=src` | v2 #4 |
| Shell-in-shell | `bash -c '...'`, `sh -c '...'`, `zsh -c '...'`, `ksh -c '...'`, `dash -c '...'` | v2 #5 + `_scan_blob` |
| Eval / xargs indirection | `eval "..."`, `xargs -I{} ...` | v2 #6 + `_scan_blob` |

### §1.2 Surfaces NOT covered (advisory-only)

5 vector classes are **structurally infeasible** to block at PreToolUse
time and remain advisory (forensic detector logs them, but the matcher
does NOT block). See §6 below.

---

## §2. Fail-CLOSED semantics

The matcher uses `shlex.split(command, posix=True)` to tokenize.
**Two fail paths are explicitly fail-CLOSED** (block the command):

1. **`shlex.split` raises `ValueError`** — unbalanced quotes,
   unterminated heredoc, etc. Per PLAN-085 Wave E.3 R1 Sec-2: emit
   `bash_parse_failed_fail_closed` audit event + return deny reason
   `"GOVERNANCE: bash command failed shlex.split parse"`.
   (`check_bash_safety.py:372-387`.)
2. **Inner body parse failure in `_scan_blob`** (Wave B addition) —
   if an interpreter `-c` body or shell `-c` body cannot be
   shlex-split, treat it as unparseable → return the body prefix as
   a "hit" → block.
3. **Pathological body length (>16 KiB)** — Wave B `_E3_BODY_CAP_BYTES`
   ReDoS-style cap. Returns the body prefix as a "hit" → block.

**One fail path is fail-OPEN** (allow the command):

- **`check_canonical_edit._CANONICAL_GUARDS` import failure** —
  delayed-import error path at `check_bash_safety.py:393-397`. If
  the canonical-guard list cannot be loaded, the matcher returns
  `None` (fall-through to other checks). Rationale: defense-in-depth
  — if `check_canonical_edit` is itself offline, the Edit/Write hook
  is also offline; blocking Bash here would be redundant noise that
  hides a deeper governance fault. The fault is itself emitted
  (PostToolUse forensic detector logs `canonical_edit_completed`).

**Non-fail paths:**

- `decide_command` outer function fails-OPEN on any uncaught
  Exception (`check_bash_safety.py:541-547`). This is by design —
  the hook NEVER bricks a user session on its own bug.
  (CLAUDE.md §5: "Fail-open on infra".) The matcher is best-effort
  defense; the merge-side `CODEOWNERS` branch protection is the
  authoritative gate.

---

## §3. Coverage matrix summary

| Bucket | Pre-Wave-B-3 | Post-Wave-B-3 (verified via simulation) |
|---|---|---|
| BLOCK | 15 / 34 (44%) | 29 / 34 (85%) |
| ADVISORY (forensic only) | 19 / 34 | 5 / 34 |
| ALLOW false-positives | 0 / 5 | 0 / 5 |
| p95 hook latency | 0.077ms | ~0.10-0.15ms estimated |

Detail per row in `.claude/plans/PLAN-089/wave-b-audit.md` §2 + §3.2.

---

## §4. Kill-switch — `CEO_BASH_CANONICAL_BYPASS`

Bypass token for emergency administrative override. Use ONLY when the
matcher false-positives on a legitimate Owner ceremony command and
re-routing the operation via Edit/Write tool is not feasible.

### §4.1 Token format

The bypass requires **three** parent-shell environment variables set
simultaneously:

```bash
export CEO_BASH_CANONICAL_BYPASS="<base32-hmac-tag>-<nonce>"
export CEO_BASH_CANONICAL_BYPASS_EXP=1746000000   # Unix epoch seconds
export CEO_BASH_CANONICAL_BYPASS_PLAN="PLAN-089-wave-b-canonical-matcher-v2"
```

- `BYPASS` — `base32(hmac-sha256(secret, plan + "|" + exp + "|" + nonce)[:20])`
  + `-` + `nonce`. ~160 bits effective entropy.
- `BYPASS_EXP` — Unix epoch seconds for expiry. The matcher rejects
  any value `≤ time.time()`. Recommended: 1-hour TTL.
- `BYPASS_PLAN` — plan-id slug `^(PLAN-\d{3}|ADR-\d{3,4})-[a-z0-9-]{3,100}$`.
  Same regex as `CEO_SENTINEL_UNLOCK` (per ADR-119 tightening).

### §4.2 Secret material

The HMAC secret lives **outside the repository** at
`~/.claude/secrets/bypass-hmac.key` (mode 0600, Owner-only). The
matcher reads it at invocation time; if missing → bypass fails
(`_check_bypass_token` returns False) → matcher blocks as if no
bypass were attempted.

**Rotation:** Owner regenerates the key monthly. Old tokens become
invalid. A rotation log entry is appended to
`docs/rotation-log.md` (precedent: `ANTHROPIC_API_KEY` rotations).

### §4.3 Audit trail

Every bypass invocation emits:

```
veto_triggered(
    hook="check_bash_safety",
    reason_code="bash_canonical_bypass_invoked",
    reason_preview="plan=<plan> exp=<exp> cmd=<first-200-chars>",
    blocked_tool="Bash",
)
```

### §4.4 FPR budget

**≤ 3 invocations per rolling 7-day window** per ADR-115 anti-churn
budget. SOC alert dashboard threshold pre-configured to fire on
`count(bash_canonical_bypass_invoked) > 3 in 7d`. Three-strike
discipline: 4th invocation in a 7-day window triggers Owner review
+ rotation of the HMAC secret.

### §4.5 Anti-phishing — never stdin

The token MUST be set as a **parent-shell environment variable**.
The matcher reads only `os.environ`. A sub-agent cannot forge
`os.environ` for the parent Claude process; same property as
`CEO_KERNEL_OVERRIDE` (per S110 lesson) and `CEO_SENTINEL_UNLOCK`
(per ADR-119).

The matcher MUST NOT accept the token via:
- stdin payload field (e.g. `tool_input.bypass`)
- file under repo root
- HTTP header / MCP tool parameter

Any code that adds such an alternate path is a CRITICAL security
regression and breaks the parent-shell isolation invariant.

---

## §5. Forensic vs blocking decoupling

The framework ships **two** Bash canonical-write detectors with
intentionally different lifecycles + responsibilities:

| Aspect | `check_bash_safety.py` (PreToolUse) | `check_bash_canonical_forensic.py` (PostToolUse) |
|---|---|---|
| Phase | PreToolUse Bash | PostToolUse Bash |
| Blocks? | **YES** (fail-CLOSED) | **NO** (always allow) |
| Detection set | matrix v2 (29/34 vectors) | regex v1 (`>`, `>>`, `tee`, `sed -i`) |
| Audit event | `veto_triggered(canonical_bypass)` on block | `canonical_edit_completed` breadcrumb |
| False-positive cost | command rejected — user retries | log line emitted — no user impact |
| False-negative cost | bypass succeeds — Wave B closes 14 of 19 v1 gaps | log line missed — forensic gap |
| Decision latency target | ≤50ms p95 | <1ms p99 (regex-only, no dep import) |

**Why two?** Belt-and-suspenders:

- **The blocker can have gaps** (matrix v2 still has 5 advisory
  rows). The forensic detector logs commands that look like writes
  even when the blocker missed them. SOC analyst reviewing audit
  logs sees the breadcrumb and can trace the attack.
- **The forensic detector can have false positives** (the regex is
  intentionally loose). Logging a false positive costs nothing —
  blocking one breaks user velocity. Separating the two lets us
  tune each independently.

**Composition invariant:** the two detectors share
`_CANONICAL_GUARDS` via delayed import from `check_canonical_edit`.
Extending the guard list (e.g. PLAN-089 Wave A's `_KERNEL_PATHS`
expansion) automatically widens BOTH detectors' surfaces with no
code change required.

**Decoupling test contract:** the matcher patch (Wave B.3) MUST NOT
modify `check_bash_canonical_forensic.py` and MUST NOT change the
PostToolUse-always-allow invariant. Verified by
`test_bash_canonical_forensic.py` (advisory-allow assertion) +
`test_bash_canonical_interceptor.py::test_parse_failure_fails_closed`
(blocker fail-CLOSED assertion). Both tests must remain GREEN.

---

## §6. Advisory-only surfaces (not blocked by matcher)

Five vector classes remain advisory post-Wave-B-3 (forensic-only).
Each has documented mitigation; none is a "free" bypass.

### §6.1 Source / dot indirection (row 17)

```bash
source ./attacker.sh
. ./attacker.sh
```

The shell loads `attacker.sh` and evaluates its body. The matcher
sees only the `source` invocation, not the script body. **If** the
script ends up calling sed/cp/tee/etc., those commands fire the
forensic detector PostToolUse + the canonical-edit hook on any
Edit/Write Claude subsequently emits to update the file. The
end-to-end bypass requires Claude to issue the `source` invocation
AND the attacker-controlled script to mutate a canonical path
without going through any tool that re-engages our governance —
which is rare in practice (legitimate scripts use Edit/Write).

### §6.2 Xargs deferred substitution (row 18)

```bash
xargs -I{} sed -i '' 's/x/y/' {} < kernel-list.txt
```

The xargs body is `sed -i '' 's/x/y/' {}` — no literal canonical
path. The list of canonical paths comes from stdin. Matcher v2 #6
scans the xargs body for canonical literals; finds none; allows.
Mitigation: the resulting `sed -i` invocation **per file** is a
new Bash invocation (xargs forks subprocess per record), and each
subprocess invocation hits the PreToolUse matcher AGAIN on the
expanded form `sed -i '' 's/x/y/' PROTOCOL.md` which IS blocked by
v1 sed -i. **Net effect:** the parent xargs command is allowed,
but each child blocks. The advisory is "fork-and-block-child"
rather than "block-at-parent".

### §6.3 Find -exec (row 19)

```bash
find . -name 'PROTOCOL.md' -exec sed -i '' 's/x/y/' {} +
```

Same as §6.2 — the find -exec body is `sed -i '' 's/x/y/' {}`.
The `-name 'PROTOCOL.md'` predicate IS a canonical literal that
`_scan_blob` (b)-pass should catch, BUT find is not in
`_E3_INDIRECTION_VERBS` in the current Wave B.3 patch. Add `find`
to that set in **Wave B.3-bis 1-line follow-up** to close this row.

### §6.4 Command-substitution wrapping (row 33)

```bash
$(eval "sed -i '' s/x/y/ PROTOCOL.md")
```

Bash evaluates `$(...)` before sending tokens to Claude. The
matcher receives a single token `$(...)` with no inner content.
Matcher v2 #6 catches the surrounding form `eval "sed ... PROTOCOL.md"`
when it is the outer command, but not when buried in `$(...)`.
Mitigation: forensic detector PostToolUse for the resulting
`sed -i` invocation that the shell expanded.

### §6.5 IFS-driven path injection (row 34)

```bash
IFS=/ cd ../PROTOCOL.md/.. && touch foo
```

`IFS=/` rebinds the field separator to `/`. Tokens reaching the
matcher's shlex split are pre-IFS; Python's `shlex.split` does NOT
honor `IFS=` rebinding. The cleanest mitigation would be
parser-level path canonicalization (walking each token through
`os.path.normpath`), but that re-introduces the TOCTOU surface we
are trying to close. Mitigation: forensic detector PostToolUse +
the subsequent `touch foo` fires the canonical-edit hook if
`foo` resolves to a canonical-tier file.

---

## §7. How to extend the matcher

### §7.1 Add a new vector

When a new bypass shape is discovered:

1. Add a row to `BLOCK_VECTORS` in
   `.claude/hooks/tests/test_check_bash_safety_canonical_matrix.py`
   with `pre_patch_expectation="MISSES"` and a `pytest.mark.xfail`.
2. Run the matrix test on current main — it should xfail.
3. Extend the matcher in `check_bash_safety.py::_e3_check_canonical_path_write`.
   Choose the right branch (v2 #1-6) or add a new branch.
4. Re-run the matrix — the new row should flip from xfail → pass.
   Remove the xfail decorator.
5. Commit under a sentinel ceremony (the file is canonical-tier).
6. Update `wave-b-audit.md` §2 + §3.2 + §7 coverage tables.
7. Update §1.1 above (this doc).

### §7.2 Add a new canonical-guard path

Update `_CANONICAL_GUARDS` in `check_canonical_edit.py` (canonical-
tier, sentinel-gated). This automatically widens BOTH detectors
(`check_bash_safety` AND `check_bash_canonical_forensic`) via the
delayed-import dependency at
`check_bash_safety.py:393-395` + `check_bash_canonical_forensic.py:64-69`.

If the new path is ALSO kernel-tier, add it to `_KERNEL_PATHS` in
`check_arbitration_kernel.py` (PLAN-089 Wave A KERNEL HARD-DENY v2
extension territory; requires `CEO_KERNEL_OVERRIDE`).

### §7.3 Add a new interpreter or shell

If a new scripting language or shell variant emerges:

- Languages with `-c`/`-e` body forms → add to
  `_E3_INTERPRETER_C_FLAGS`.
- Languages with `-i`/`--in-place` flag → add to
  `_E3_INPLACE_INTERPRETERS`.
- Shell variants with `-c` body forms → add to
  `_E3_SHELL_C_INTERPRETERS`.

Each constant is a small frozenset/dict; the matcher branches are
already structured to handle additions without code change.

### §7.4 Rotation discipline

`CEO_BASH_CANONICAL_BYPASS_SECRET` rotation is **monthly** (per
§4.2). Log each rotation in `docs/rotation-log.md` with:

```markdown
## bypass-hmac.key rotation
- date: 2026-05-13
- rotated-by: @Canhada-Labs
- previous-fingerprint: <sha256-of-old-key-first-8-bytes>
- new-fingerprint: <sha256-of-new-key-first-8-bytes>
- previous-token-count: <int>  # bash_canonical_bypass_invoked events in window
```

If the rotation is **emergency** (suspected key compromise), bump
the version of `_BYPASS_KEY_VERSION` constant in
`check_bash_safety.py` so that old tokens are rejected even if the
file system still has the old key. Emergency rotation requires
sentinel ceremony (canonical-tier file edit).

---

## §8. References

- **ADR-010** — Canonical-edit sentinel discipline (parent).
- **ADR-040** — Live adapter activation contract (credential rotation,
  related sibling).
- **ADR-115** — Post-SOTA maintenance mode; anti-churn budget.
- **ADR-116** — Kernel HARD-DENY tier-0 (sibling defense layer for
  Edit/Write).
- **ADR-117** — ADR-ID rename / collision-rename policy.
- **ADR-119** — `CEO_SENTINEL_UNLOCK` regex tightening (precedent for
  this doc's §4 token-regex discipline).
- **ADR-121** (proposed, PLAN-089 Wave C) — Sentinel signer rotation
  policy. When ADR-121 lands, this doc's §4.2 secret-material
  storage moves to align with the cold-key registry doctrine.
- **PLAN-085 Wave E.3** — Original matcher v1 (heuristic).
- **PLAN-089 Wave B** — Matrix v2 (this doc's primary surface).
- **`.claude/plans/PLAN-089/wave-b-audit.md`** — Per-row audit detail.
- **`.claude/hooks/check_bash_safety.py`** — Source.
- **`.claude/hooks/check_bash_canonical_forensic.py`** — Forensic sibling.
- **`.claude/hooks/tests/test_check_bash_safety_canonical_matrix.py`** — Matrix tests.
