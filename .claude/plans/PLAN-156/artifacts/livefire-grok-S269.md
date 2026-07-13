# PLAN-156 W7 — Grok live-fire positive controls (S269, 2026-07-12)

> T2 tier (Owner's authed machine + the staged grok adapter/shim). Every
> proof is a deterministic hook invocation with the grok wire on stdin
> through the real shim (`_python-hook.sh`) under `CEO_HOOK_ADAPTER=grok`
> — the exact bytes the harness runs. Lab: scratchpad `grok-livefire`
> (staged wave2 adapter+shim + wave6 canonical guard + repo `_lib`).

## The bug this pass caught (fixtures did NOT)

The first run flagged a REAL defect the golden fixtures missed: the grok
adapter's coherence gate checked the NORMALIZED tool name, so a
legitimate grok `search_replace` (which normalizes to `Edit`) tripped
the cross-harness gate and DENIED every benign edit. The golden fixtures
compared normalized output and never exercised the emit-time coherence
decision, so they stayed green over the bug. Fix: `_cross_harness_reason`
now checks the RAW wire tool name (grok emits `search_replace` /
`run_terminal_command` / `spawn_subagent`, never `Edit`/`Write`/`Task`),
so a legit grok edit passes and a genuine Claude-native name on the grok
wire still fails CLOSED. Lesson: a fixture round-trip is not a
substitute for driving the actual decision path — the live-fire is what
proved enforcement, not the fixture replay (the S254 class, one level up).

## Proofs (all via the real shim, grok wire on stdin)

| # | Input (grok `pre_tool_use` wire) | stdout decision | exit | verdict |
|---|---|---|---|---|
| 1 | `search_replace` on `.claude/team.md` (guarded) | `{"decision":"deny", …CANONICAL-EDIT-BLOCKED…}` | **2** | canonical guard DENIES; vocabulary is `deny`, not `block` |
| 2 | `run_terminal_command` `rm -rf ~` (NATIVE name) | `{"decision":"deny", …destructive…}` | **2** | bash-safety DENIES the native-named call; `deny` vocabulary |
| 3 | `search_replace` on `src/app.ts` (unguarded) | `{"decision":"allow"}` | **0** | benign edit ALLOWED (the bug-fix proof) |
| 4 | `Edit` on the grok wire (impossible name) | `{"decision":"deny", …coherence gate…}` | **2** | genuine cross-harness envelope fails CLOSED |

Proof 2 is the acceptance-criterion positive control: a NATIVE-named
call (`run_terminal_command`, not the Claude alias `Bash`) trips
bash-safety — a mapped-name-only test would have proven nothing (the C3
dead-gate). The matcher fired on the native name AND the guard emitted
`deny` (not `block`), so grok enforces rather than fail-opening (P5).

## Exit-2 fail-CLOSED via input-parse (the two halves)

- **input-parse deny → blocked + exit 2**: Proof 4 above — a payload the
  grok adapter recognizes as cross-harness (INPUT-class) emits a
  structured deny and the shim maps it to exit 2. This is a deny on
  bad INPUT, NOT a bare crash.
- **infra crash → ALLOWED (fail-open)**: covered hermetically by
  `hooks/tests/test_exit2_chokepoint.py::test_import_crash_is_fail_OPEN_not_deny`
  — a hook that dies with no decision keeps its own (fail-open) exit code;
  the chokepoint never turns a bare crash into a deny. Both halves of
  CLAUDE.md §4 hold.

## Stop-advisory demonstration

Grok's `Stop` is passive (S269 characterization: it fires with a
`reason` but cannot block). The shim's passive-event carve-out
(`test_exit2_chokepoint.py::PassiveEventCarveOutTest`) proves a deny on
`stop` / `post_tool_use` is NOT mapped to exit 2 — so the Stop-review
gate is ADVISORY by construction and the git pre-push gate
(`templates/grok/pre-push-review-gate.sh`) is the teeth, exactly as the
capability matrix (ADR-162) claims.

## Council 3-lane + degraded 2-lane

Covered hermetically (no live egress) by
`scripts/tests/test-council-fixture.mjs`: scenario A proves a killed grok
lane surfaces `unavailable` with reason + a labeled 2-lane quorum + the
cross-vendor disagreement signal; scenario B proves all-unavailable →
DEGRADED (never CLEAN); scenario C proves full 3-lane + zero findings →
CLEAN. The four BLOCKING source invariants (egress redactor, OS sandbox
flags, fail-loud, fixture-mode) are asserted RED-on-absence.
