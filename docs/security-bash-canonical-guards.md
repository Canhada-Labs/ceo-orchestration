# Security — Bash canonical-path write guards

**Audience:** framework administrators (Owner + CTO + Security on-call).
**Not user-facing.** Users do not need to read this — the hook fails
closed automatically on the surfaces it covers.

**Last updated:** 2026-10-02 (PLAN-195 W0 — coverage claims re-checked against the code; §6 rewritten).
**Related ADRs:** ADR-010, ADR-040, ADR-115, ADR-116, ADR-117,
ADR-121 (proposed in PLAN-089 Wave C).
**Source:** `.claude/hooks/check_bash_safety.py:2167-2449` (`_e3_check_canonical_path_write`),
`.claude/hooks/check_bash_canonical_forensic.py` (forensic sibling),
`.claude/plans/PLAN-089/wave-b-audit.md` (audit detail; not in the public tree).

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
PLAN-089 Wave B closed 15 more vectors (the **matrix v2** matcher);
row 33 followed at S207.

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

### §1.2 Surfaces NOT covered

Three matrix rows (17, 18, 34) are not blocked, and no hook detects
them after the fact. The class of indirect execution and computed write
target is not covered generically (§6.6). Neither is a literal target
written in a spelling other than the guard's own (§6.6, Class B).

---

## §2. Fail-CLOSED semantics

The E3 matcher tokenizes with a POSIX `shlex.shlex` lexer, with
`punctuation_chars` and `whitespace_split` (`check_bash_safety.py:2190-2192`).
**Three fail paths are explicitly fail-CLOSED** (block the command):

1. **The lexer raises `ValueError`** — unbalanced quotes,
   unterminated heredoc, etc. Per PLAN-085 Wave E.3 R1 Sec-2: emit
   `bash_parse_failed_fail_closed` audit event + return deny reason
   `"GOVERNANCE: bash command failed shlex.split parse"`.
   (`check_bash_safety.py:2193-2208`.)
2. **Inner body parse failure in `_scan_blob`** (Wave B addition) —
   if an interpreter `-c` body or shell `-c` body cannot be
   shlex-split, treat it as unparseable → return the body prefix as
   a "hit" → block.
3. **Pathological body length (>16 KiB)** — Wave B `_E3_BODY_CAP_BYTES`
   ReDoS-style cap. Returns the body prefix as a "hit" → block.

**One fail path is fail-OPEN** (allow the command):

- **`check_canonical_edit._CANONICAL_GUARDS` import failure** —
  delayed-import error path at `check_bash_safety.py:2214-2218`. If
  the canonical-guard list cannot be loaded, the matcher returns
  `None` (fall-through to other checks). Rationale: defense-in-depth
  — if `check_canonical_edit` is itself offline, the Edit/Write hook
  is also offline; blocking Bash here would be redundant noise that
  hides a deeper governance fault. No event records this fault: the
  forensic detector imports the same module and logs nothing on failure.

**Non-fail paths:**

- The hook's `main()` fails-OPEN on any uncaught
  Exception (`check_bash_safety.py:4227-4233`). This is by design —
  the hook NEVER bricks a user session on its own bug.
  (CLAUDE.md §5: "Fail-open on infra".) The matcher is best-effort
  defense; the merge-side `CODEOWNERS` branch protection is the
  authoritative gate.

---

## §3. Coverage matrix summary

| Bucket | Pre-Wave-B-3 | Current (`test_check_bash_safety_canonical_matrix.py`) |
|---|---|---|
| BLOCK | 15 / 34 (44%) | 31 / 34 (91%) |
| NOT BLOCKED (no forensic backup either) | 19 / 34 | 3 / 34 (rows 17, 18, 34 — strict xfail) |
| ALLOW false-positives | 0 / 5 | 0 / 5 |
| p95 hook latency | 0.077ms | ~0.10-0.15ms estimated |

Per-row detail lived in `.claude/plans/PLAN-089/wave-b-audit.md` (not in
the public tree); the matrix test is the live source.
The matrix does not represent the §6.6 class, so 31 / 34 is not a
coverage figure for that class.

---

## §4. Kill-switch — `CEO_BASH_CANONICAL_BYPASS`

> **Status (checked 2026-10-02): NOT implemented.** No code in
> `check_bash_safety.py` reads these variables, the key file, or a
> `_BYPASS_KEY_VERSION` constant; the E3 matcher has no bypass path.
> §4.1–§4.5 and §7.4 describe a design, not shipped behavior. Only the
> PostToolUse forensic hook emits `bash_canonical_bypass_invoked`.

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
| Detection set | matrix v2 (31/34 rows; not the §6.6 class) | regex v1 (`>`, `>>`, `tee`, `sed -i`), literal canonical target only |
| Audit event | none on a canonical-path block; `veto_triggered(bash_parse_failed_fail_closed)` on parse failure | `canonical_edit_completed` breadcrumb |
| False-positive cost | command rejected — user retries | log line emitted — no user impact |
| False-negative cost | bypass succeeds — 16 of 19 v1 gaps closed (15 by Wave B.3, row 33 at S207) | log line missed — forensic gap |
| Decision latency target | ≤50ms p95 | <1ms p99 (regex-only, no dep import) |

**Why two?** Belt-and-suspenders:

- **The blocker has gaps** (§6). The forensic detector is NOT a
  backstop for them. It matches only four literal write shapes in the
  same raw command text, so it never sees the §6 rows, Class A or a
  computed target. It classifies a target with the Edit/Write classifier
  (`check_bash_canonical_forensic.py:63-69` → `check_canonical_edit._is_canonical`),
  which resolves the path and folds ASCII case. By code reading, it can
  log a respelled or symlinked literal target after the fact, in those
  four shapes only. No test pins this, and `canonical_edit_completed` is
  outside `_CRITICAL_SECURITY_ACTIONS`, with no default reader. It is
  not coverage.
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

## §6. Coverage gaps (not blocked by the matcher)

The `PreToolUse` hook receives the raw command text once per Bash tool
call: nothing is expanded yet, and processes the command spawns never
re-enter the hook. The forensic detector (§5) is a regex over that same
text, and `check_canonical_edit.py` never observes Bash. Rows 17, 18 and
34 stay unblocked (`_ADVISORY_ROWS`, strict xfail), with no detection
after the fact. Rows 19 and 33 are blocked today. Every canonical-path
block assumes the target is written in the guard's own spelling (§6.6).

### §6.1 Source / dot indirection (row 17)

NOT covered. The matcher sees the command that loads a script file,
never the script body. No hook observes what the body runs.

### §6.2 Xargs deferred substitution (row 18)

NOT covered. A target that reaches `xargs` through standard input is not
a literal in the command. The children `xargs` spawns never re-enter
`PreToolUse`.

### §6.3 Find -exec (row 19)

BLOCKED while the canonical path is a literal: `find` is in
`_E3_INDIRECTION_VERBS` (`check_bash_safety.py:2157`).

### §6.4 Command-substitution wrapping (row 33)

BLOCKED since S207. The E3 lexer isolates `(`, `)` and the backtick
(`check_bash_safety.py:2190`), so the `eval` body reaches the indirection
scan as raw, unexpanded text.

### §6.5 IFS-driven path injection (row 34)

NOT covered. The E3 lexer does not model the field separator, and the
forensic detector has no shape for this row.

### §6.6 Indirect execution and computed write target — NOT covered

The matchers compare literal tokens of the raw text, in one spelling.
Two classes escape that comparison, and neither is covered generically
today. The cure is tracked in `.claude/plans/PLAN-195-bash-guard-indirect-execution.md`.

**Class A — indirect execution of a destructive command.** The trio
(`_check_rm_rf`, `_check_git_reset_hard`, `_check_git_push_force`,
`check_bash_safety.py:364-465`) reads the leading tokens of each chunk
and never recurses. It has no rule for a verb inside a nested interpreter
body, a dynamic evaluation, a chaining runner or a pipe into an
interpreter. It has none for a command name that an expansion produces.
`_scan_blob` inspects bodies, but seeks only canonical path literals.

**Direct sibling forms.** The direct forms are blocked only in the
canonical spelling: the verb first in a chunk split on `&&`, `||`, `;` or
`|` (`check_bash_safety.py:275`). The command word and the `git`
subcommand are compared case-sensitively, at fixed positions, after
stripping only four launcher prefixes and leading assignments (`:107`).
Other separators, grouping, reserved words, launchers, command-word case,
options before the subcommand, and disagreements between its tokenizers
do not match.

**Class B — computed or respelled write target.** E3 compares each
target string with `_CANONICAL_GUARDS` and expands nothing. When a
variable, a glob, a relative directory change or a program argument
produces the destination, E3 never compares the destination itself. A
LITERAL target is compared only in the guard's own spelling: E3
normalizes just a leading `./` and an absolute path under the root
(`check_bash_safety.py:2222-2240`), and the raw segment matcher it calls
is case-sensitive (`check_canonical_edit.py:949-985`). The Edit/Write
classifier folds case; E3 does not use it. Another spelling of the same
path, or a filesystem alias, is not blocked.

**Detection.** No generic block exists for either class. For Class A
and for a computed target, `PreToolUse` is the only detection, and it
has no rule for them. For a respelled or symlinked literal target, the
forensic hook gives partial detection, after the fact only, and only in
its four literal write shapes (§5); no test pins it and no default
reader consumes the event. Nothing detects copy, move, removal, a hard
link, or the creation of the alias. The OS sandbox is disabled
(`.claude/settings.json`, `sandbox.enabled: false`).

**Residuals declared by form.** Static shell analysis is incomplete by
construction. These forms stay open even after the planned cure (single
source: the PLAN-195 Goal plus its item C12; items 8–10 await decisions):

1. Destructive APIs of the interpreter's own language, with no shell verb.
2. A script in a file, including one the Write tool wrote earlier.
3. Functions and aliases from the shell profile or from earlier calls.
4. Tool configuration that runs a configured value as a program.
5. Shell startup-file variables (env-hijack guard, advisory by default).
6. Arguments that reach `xargs` through standard input.
7. A fully computed command word and arguments, with no literal destructive marker.
8. Removal by a file search with a removal action, with or without a predicate.
9. Recursive removal without the force option (allowed by the trio today).
10. Opaque-feeder sub-forms (input the hook cannot read) demoted to advisory, if any.
11. A directory change made in an earlier tool call (the hook gets no working directory).
12. A comment blind spot in the E4 line-break normalizer (posture-toggle guard).
13. A literal target not byte-equal to the guard's spelling: a path-spelling variant, or a filesystem alias made earlier.

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
6. Update §3 above and the matrix test docstring (`wave-b-audit.md` is not in the public tree).
7. Update §1.1 above (this doc).

### §7.2 Add a new canonical-guard path

Update `_CANONICAL_GUARDS` in `check_canonical_edit.py` (canonical-
tier, sentinel-gated). This automatically widens BOTH detectors
(`check_bash_safety` AND `check_bash_canonical_forensic`) via the
delayed-import dependency at
`check_bash_safety.py:2214-2218` + `check_bash_canonical_forensic.py:64-69`.

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
- **`.claude/plans/PLAN-089/wave-b-audit.md`** — Per-row audit detail (not in the public tree).
- **`.claude/hooks/check_bash_safety.py`** — Source.
- **`.claude/hooks/check_bash_canonical_forensic.py`** — Forensic sibling.
- **`.claude/hooks/tests/test_check_bash_safety_canonical_matrix.py`** — Matrix tests.
