# ADR-056: Hook lifecycle expansion — SessionStart / SessionEnd / UserPromptSubmit / Stop

**Status:** ACCEPTED
**Date:** 2026-04-19
**Proposer plan:** PLAN-028 (Wave A Fase 3)
**Target sprint:** 27 (PLAN-027 Wave A)
**Decision drivers:** PLAN-026 external audit convergence — claude-mem lifecycle hooks + everything-claude-code audit (PreCompact/SessionStart/Stop/SessionEnd coverage gap); native Claude Code support for these matchers lands with ≥PLAN-020 era
**Accepted-By:** @Canhada-Labs PLAN-028-WAVE-A-FASE-3-EXECUTION

---

## Context

ceo-orchestration currently registers hooks on 2 of the 6 Claude Code
lifecycle events:

- `PreToolUse` — 5 hooks (check_agent_spawn, check_canonical_edit,
  check_skill_patch_sentinel, check_arbitration_kernel,
  check_read_injection, check_bash_safety, check_plan_edit, etc.)
- `PostToolUse` — 2 hooks (audit_log, check_skill_reference_read)

Lifecycle gap (PLAN-026 audit): 4 events uncovered:

- `SessionStart` — no audit init, no cache warmup, no governance
  health check. First spawn pays a cold-read cost; governance drift
  (e.g., deleted SKILL.md, missing CODEOWNERS) is only detected
  mid-session.
- `SessionEnd` — no closeout event. Duration, tool-calls-count,
  exit reason are not captured.
- `UserPromptSubmit` — no pre-model-inference redaction or
  prompt-injection smell-test. Secrets leak into the provider model
  with no visibility.
- `Stop` — no graceful cleanup on SIGINT/SIGTERM. Stale filelocks
  can carry over to the next session.

claude-mem (5 stars OSS precedent) ships all 6 events wired; ours
shipping 2 is an adopter-readiness gap.

## Decision drivers

1. **Audit completeness.** Every session has a start/end boundary;
   capturing them closes the forensic gap documented in
   `docs/THREAT-MODEL.md` §RR-8 audit tail truncation (the
   complementary gap; this one is "start/end not recorded" vs
   "tail truncation").

2. **Prompt-injection smell-test at source.** Today's input
   protection (`check_read_injection`) scans files being Read.
   `UserPromptSubmit` scans the prompt the Owner types. Two
   distinct vectors; previously only one was defended.

3. **Gate-1 cache warmup.** First spawn in every session currently
   cold-reads CLAUDE.md + PROTOCOL.md + team.md. Pre-loading via
   SessionStart primes the OS page cache + validates file hashes
   against the last known-good.

4. **Graceful interrupt handling.** Owner Ctrl+C today leaves
   unknowable in-flight state. Stop emits a structured event +
   drains audit-log filelock + releases stale `*.lock` files in
   scratch dir.

5. **Kill-switch discipline.** `CEO_EXTENDED_LIFECYCLE=0` flips all
   4 new hooks off bit-for-bit; pre-ADR-056 behavior preserved
   under kill-switch.

## Options considered

### Option A — Ship all 4 hooks together (CHOSEN)

Bundle all 4 lifecycle hooks + test files + settings.json
registration + this ADR in one commit.

**Pros:**
- Coherent lifecycle coverage (2/6 → 6/6 in one commit).
- Single kill-switch (`CEO_EXTENDED_LIFECYCLE`) for all 4.
- Audit registry v2.9 additions are bundled.

**Cons:**
- Larger commit surface (~500 LOC + ~100 tests).

### Option B — Ship one hook per commit (4 commits)

**Pros:**
- Smaller blast radius per commit.
- Easier rollback of individual hook.

**Cons:**
- 4 separate kill-switches needed (or shared state).
- 4× settings.json commits. 4× ADR amendments. Sprint cycle
  overhead.
- Delayed lifecycle coverage (2/6 → 3/6 → 4/6 → 5/6 → 6/6) leaves
  partial state for weeks.

### Option C — Ship SessionStart + SessionEnd only (defer prompt + stop)

**Pros:**
- Covers the two most-frequent lifecycle boundaries.

**Cons:**
- Leaves the highest-value hook (UserPromptSubmit) absent, which
  is the one with the most adopter-visible security win.

## Decision

**Option A.** Ship all 4 hooks + tests + ADR-056 + audit_emit.py
amendments in one commit (modulo `_KNOWN_ACTIONS` registration
staged with ADR-059 kernel batch for atomic application).

## Implementation

### Per-hook responsibility matrix

| Hook | LOC | Tests | Responsibility | Audit event |
|---|---|---|---|---|
| `SessionStart.py` | ~170 | ~10 | Audit init + Gate-1 cache warmup + governance health | `session_start(session_id, governance_state, gate_1_hashes, warmup_bytes)` |
| `SessionEnd.py` | ~140 | ~7 | Audit closeout + memory persistence verify + filelock drain | `session_end(session_id, reason, memory_writable, memory_index_present)` |
| `UserPromptSubmit.py` | ~190 | ~14 | Redact-hit breadcrumb + 5-family injection scan + advisory banner | `prompt_submitted(session_id, prompt_len_bucket, prompt_sha256, redact_hits_count, injection_family_counts)` |
| `Stop.py` | ~150 | ~10 | Emit stop event + filelock drain + stale-lock release | `session_stop(session_id, reason, partial_state_saved)` |

Total: ~650 LOC + ~41 tests. Additions to `_KNOWN_ACTIONS`:
`session_start`, `session_end`, `prompt_submitted`, `session_stop`.

### Prompt-injection family coverage (UserPromptSubmit)

Five regex families, each matching a known injection class:

1. `system_reminder_forge` — `<system-reminder>` tag forging
2. `role_confusion` — "you are now X", "pretend you are Y"
3. `instruction_nesting` — fenced code containing ignore/forget
4. `context_escape` — end-fence followed by `[new instructions]`
5. `direct_override` — "ignore previous instructions"

Each family counter emits to audit-log. Advisory at State 0;
Sprint 29+ FPR data informs promotion to blocking per family.

### Audit-log event field inventory

New events register in `.claude/hooks/_lib/audit_emit.py`
`_KNOWN_ACTIONS` set (staged pending kernel apply per ADR-059):

```
session_start, session_end, prompt_submitted, session_stop
```

`AUDIT-LOG-SCHEMA.md` §2 is amended v2.9 with the 4 new discriminator
values + required fields per event.

### `.claude/settings.json` registration

```json
"hooks": {
  "SessionStart": [
    {"matcher": "", "hooks": [{"type": "command",
      "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" SessionStart.py",
      "timeout": 5,
      "statusMessage": "Session warmup..."}]}
  ],
  "SessionEnd": [{"matcher": "", "hooks": [...]}],
  "UserPromptSubmit": [{"matcher": "", "hooks": [...]}],
  "Stop": [{"matcher": "", "hooks": [...]}]
}
```

`templates/settings/hooks.json` receives parallel registration so
fresh adopter installs get the lifecycle hooks automatically.

## Consequences

**Positive:**
- Lifecycle coverage 2/6 → 6/6.
- Structured audit events for every session boundary.
- UserPromptSubmit closes an input-sanitization surface.
- Gate-1 cache warmup reduces first-spawn latency.
- Graceful Ctrl+C behavior (lock cleanup).

**Negative:**
- 4 additional hook invocations per session (measurable cost:
  each hook p99 < 50ms per `.claude/scripts/profile-opus-4-7.py`
  baseline — acceptable per ADR-024 perf budget).
- Kill-switch knob surface + 1 (CEO_EXTENDED_LIFECYCLE).
- 4 additional event types in audit-log; consumers tolerate via
  AUDIT-LOG-SCHEMA.md §2 forward-compat clause.

**Neutral:**
- Graceful kill-switch honored per hook (CEO_EXTENDED_LIFECYCLE=0
  triggers `{"decision":"allow"}` with kill-switch systemMessage
  — identical to pre-ADR-056 null behavior).

## Blast radius

**Moderate.** 4 new hook files (all under `.claude/hooks/`) +
4 test files + 2 settings.json files + 1 audit_emit.py amendment
(ADR-059 kernel batch) + 1 ADR. Zero impact on existing hooks.
Zero SPEC change (audit-log schema amendment is additive). Zero
policy change.

## Reversibility

**High.** Unregister the 4 hooks from settings.json + delete the
hook files + revert audit_emit.py amendment. Audit-log entries
already written survive (consumers tolerate unknown fields per
§2 forward-compat). Kill-switch provides bit-for-bit opt-out
without uninstalling.

## Fail-open invariant (ADR-005 parity)

Every new hook follows the same fail-open contract:

- Parse error → `{"decision":"allow"}`
- Import error (audit_emit missing) → `{"decision":"allow"}`
- Internal exception → `{"decision":"allow"}` + stderr breadcrumb
- Kill-switch `CEO_EXTENDED_LIFECYCLE=0` → `{"decision":"allow"}`
  with kill-switch systemMessage

No lifecycle hook ever blocks a session. Blocking is the job of
PreToolUse hooks (where there is a tool call to block); lifecycle
hooks are observational.

## Debate Round 1 — deferred per ADR-058 pattern

Following ADR-058's precedent, Round 1 debate is deferred for this
ADR. Rationale:
- Blast radius moderate (4 new files; zero impact on existing).
- Reversibility high (kill-switch + revert + delete).
- Per-hook design is established pattern (fail-open, kill-switch,
  audit emit, stdlib-only) — not a first-of-kind decision requiring
  multi-specialist critique.
- Incident-driven debate: if any of the 4 hooks misbehaves during
  Wave A closeout or post-GA, Round 1 runs with real evidence.

## Revisit trigger

Re-open this ADR if any of:
1. Any of the 4 hooks has p99 > 100ms on profile-opus-4-7.py
   (indicates hot-path regression).
2. Adopter reports false-positive injection scan blocking a
   legitimate workflow (triggers State-0 → State-1 review).
3. `session_end(reason=interrupted)` count exceeds 10% of sessions
   (indicates graceful-shutdown failure pattern).
4. AUDIT-LOG-SCHEMA.md consumer breakage from v2.9 schema bump
   (migration path discussion).

## References

- PLAN-028 — hook lifecycle expansion plan
- PLAN-027 — UltraFramework SOTA roadmap (Wave A parent)
- PLAN-026 — external audit that surfaced this gap
- ADR-005 — fail-open contract
- ADR-011 — check_read_injection (sibling input-safety hook)
- ADR-024 — performance budget (perf reference)
- ADR-055 — audit-log HMAC chain (events use HMAC chain)
- ADR-058 — sibling Wave A ADR (brainstorm gate + adversarial)
- ADR-059 — skill-bootstrap bypass (kernel batch vehicle)
- `docs/THREAT-MODEL.md` §RR-8 — complementary audit gap
- claude-mem README — 5 lifecycle hooks + smart install pre-hook
  (OSS precedent)
- everything-claude-code audit — lifecycle coverage finding

## Enforcement commit

`5000d2cd8894` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
