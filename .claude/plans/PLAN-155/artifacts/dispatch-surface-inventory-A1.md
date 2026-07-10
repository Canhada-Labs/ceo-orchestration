# PLAN-155 — Dispatch-surface inventory (debate A1) + seam ratification packet

Re-derived S266 (2026-07-09, Wave 0 prep) by direct grep of the working
tree (`grep -n "from _lib.adapters import\|load_adapter\|resolve_adapter"
.claude/hooks/*.py`), main at post-PLAN-153 landing. Presented for Owner
ratification at the morning ceremony (debate A1: the seam design is
ratified at SENT-CX-A signing, never discovered at execution time).

## Finding 1 — `CEO_HOOK_ADAPTER` has ZERO consumers in hook entrypoints

`_lib/contract.py` ships the machinery — `KNOWN_ADAPTERS = ["claude",
"codex"]` (`contract.py:216`), `resolve_adapter()` (`:225`, reads
`CEO_HOOK_ADAPTER`, unknown values silently fall back), `load_adapter()`
(`:243`) — but **no file under `.claude/hooks/*.py` calls
`load_adapter()` or `resolve_adapter()`** (grep: zero hits outside
`_lib/`). Every entrypoint hard-imports the claude adapter. Setting
`CEO_HOOK_ADAPTER=codex` today changes NOTHING — without a seam, every
ENFORCED matrix row silently becomes ABSENT under Codex (the S254
dead-gate class). This confirms the debate-A1 CRITICAL finding.

## Finding 2 — hard-import census: 24 claude-adapter sites across 23 files

### Module-level `from _lib.adapters import claude as _claude_adapter` (9 files)

| File | Line | ENFORCED-rail? |
|---|---|---|
| `audit_log.py` | 176 | audit chain (Wave 4 surface, SENT-CX-B) |
| `check_agent_spawn.py` | 53 | ADVISORY (spawn) |
| `check_bash_safety.py` | 201 | **YES — ENFORCED** |
| `check_budget.py` | 105 | advisory |
| `check_confidence_gate.py` | 68 | advisory |
| `check_config_protection.py` | 119 | config rail |
| `check_plan_edit.py` | 92 | **YES — ENFORCED** |
| `check_scratchpad_access.py` | 54 | advisory |
| `check_worktree_writer.py` | 116 | advisory |

### Function-level (lazy) imports (15 sites, 14 files)

| File | Line(s) | ENFORCED-rail? |
|---|---|---|
| `SessionStart.py` | 311 | boot surface (Wave 3b tripwire home, SENT-CX-E) |
| `Stop.py` | 156 | stop surface (Wave 6 inverted-rail home) |
| `UserPromptSubmit.py` | 289 | advisory |
| `SessionEnd.py` | 323 | advisory |
| `check_adversary.py` | 41 | advisory |
| `check_arbitration_kernel.py` | 448 | **YES — ENFORCED (kernel deny)** |
| `check_bash_canonical_forensic.py` | 36 | forensic |
| `check_canonical_edit.py` | 1081 | **YES — ENFORCED** |
| `check_codex_response.py` | 339 | pair-rail ingress |
| `check_output_safety.py` | 169 | advisory |
| `check_read_injection.py` | 254, 375 | advisory (2 sites, 1 file) |
| `check_skill_reference_read.py` | 478 | advisory |
| `check_skill_patch_sentinel.py` | 362 | skill-patch rail |
| `check_webfetch_injection.py` | 178 | advisory |

### Codex-adapter imports (reviewer-egress direction — NOT host dispatch; untouched by the seam)

- `check_codex_response.py:368` (`from _lib.adapters import codex`)
- `check_pair_rail.py:829` (`from _lib.adapters import codex as _codex`)

These are the PLAN-081/142 pair-rail helpers; the debate-A14
characterization pre-gate locks this surface across the Wave 1 commit.

## Seam options for Owner ratification

### Option (a) — per-entrypoint migration

Replace all 24 hard-import sites with `contract.load_adapter()` calls.
- Touches **~23 files**, most canonical-guarded, several KERNEL
  (`check_arbitration_kernel.py`, `audit_log.py`, `SessionStart.py`, ...).
- SENT-CX-A scope balloons to the full hook surface; every advisory rail
  pays the review/regression cost in the same wave as the linchpin.
- Uniform end-state, but maximal blast radius in the highest-risk wave.

### Option (b) — single shared seam + four ENFORCED hooks migrated in Wave 1 ← **CEO RECOMMENDATION**

Add ONE dispatch function — `resolve()` in
`_lib/adapters/__init__.py` (delegating to `contract.resolve_adapter()` /
`load_adapter()`, with the debate-A2 coherence gate at this single
choke-point: explicitly-set-but-unresolvable `CEO_HOOK_ADAPTER`, or a
recognizably cross-harness envelope, is INPUT → fail-CLOSED deny + audit
breadcrumb, per PLAN-152 C4; whether the gate body lives in
`contract.py` or adapter-side is the sub-decision recorded at signing).
Migrate ONLY the four ENFORCED hooks in Wave 1:

- `check_canonical_edit.py:1081`
- `check_bash_safety.py:201`
- `check_plan_edit.py:92`
- `check_arbitration_kernel.py:448`

Rationale:
1. **Minimal blast radius.** 7 guarded files (3 adapter/lib + 4 hooks)
   instead of ~23; the KERNEL override list stays exactly what SENT-CX-A
   already enumerates.
2. **One auditable seam.** The A2 fail-closed coherence gate exists ONCE,
   at the single point every migrated hook routes through — not
   copy-pasted 24 times where one stale copy is a silent hole. The
   subprocess positive-controls (debate A3) prove dispatch through this
   one seam on the shipped command line.
3. **Advisory rails migrate opportunistically later.** Under Claude Code
   their behavior is byte-identical (seam default = claude); under Codex
   they run with claude-adapter parsing until migrated — an honest,
   named limitation for ADVISORY rows, not a silent hole in an ENFORCED
   claim. Waves 4 (`audit_log.py`), 3b (`SessionStart.py`) and 6
   (`Stop.py`) migrate their own files under their own already-allocated
   sentinels; the long tail follows in a later hygiene plan.
4. **Matrix honesty preserved.** Every ENFORCED row's dispatch is
   Wave-1-verified; no row's truth depends on a file outside SENT-CX-A
   scope.

Cost acknowledged: temporary two-regime state (seam-migrated vs
hard-import) until the tail migrates — tracked as a named residual in
ADR-161, and the drift detector extension (debate A4) flags NEW
hard-imports so the tail cannot grow.

## Ratification ask (morning ceremony)

- [ ] Owner ratifies seam option **(b)** (or (a); SENT-CX-A is re-drafted
      to the ~23-file enumeration in that case).
- [ ] Sub-decision: A2 coherence-gate body home — `contract.py` (then the
      conditional `contract.py` line in SENT-CX-A scope STAYS) vs
      adapter-side `_lib/adapters/__init__.py` (then the Owner strikes
      the `contract.py` line unless registry constants also move).
- [ ] Recorded verbatim into PLAN-155 §Open questions / Wave 0 checklist
      after signing.
