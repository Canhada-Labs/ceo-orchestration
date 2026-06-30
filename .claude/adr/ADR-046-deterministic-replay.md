# ADR-046: Deterministic replay of session graph + audit log

**Status:** ACCEPTED (flipped from PROPOSED on PLAN-014 Phase G commit fdc2d89)
**Date:** 2026-04-16
**Supersedes:** none
**Superseded by:** none
**Related:** ADR-038 (session graph), ADR-007 (SemVer + additive-only), ADR-040 §7 (live adapter observability)

## Context

PLAN-014 Phase F.1 ships `.claude/scripts/replay/replay-session.py` consuming session graph (ADR-038) + audit log to re-execute a plan in exact spawn order. The scenario: an adopter hits a production incident (wrong spawn order, incorrect decision at debate round 2, audit trail looks off); operator needs to re-run the same plan deterministically to diagnose.

Debate Round 1 (2026-04-17 Session 23) surfaced four constraints:
1. **C15 HIGH — Information Disclosure class.** Live-adapter re-call amplification: a naive `--execute` mode could re-post to production providers, doubling quota + leaking cost signal to an adversary watching token-count ramps. Default MUST be dry-run.
2. **Dirty worktree pre-flight.** `--execute` on a dirty tree risks mixing replay output with in-progress work. Refuse.
3. **Multi-user distinction.** Replayer OS-user ≠ original session owner — audit event MUST distinguish to prevent accountability laundering.
4. **Determinism regression class.** A replay that isn't byte-identical across runs is useless as a debugging primitive. Needs TestReplayDeterminism fixture (≥10 tests per ADJ-027).

Co-landing with PLAN-014 Phase F.1 (per Phase 0.3 ADR→Phase dependency; reversibility HIGH — additive script, no existing hook impact).

## Decision drivers

- **Live-adapter re-call amplification** (RR-5 appended to threat model)
- **Cross-OS determinism** (Phase F.1b TestReplayDeterminism ≥10 tests — macOS + Linux targets)
- **Read-API stability** required to support the tool (Phase F.0 `check-audit-read-api-stable.py` freeze)
- **Stub-default correctness** — `--execute` auto-sets `CEO_LIVE_ADAPTER_STUB=1` + `CEO_OTEL_DISABLED=1`
- **One-way-ratchet accuracy** (NOT applicable here; belongs to ADR-047)
- **Stdlib-only** (ADR-002 invariant)

## Options considered

### Option A — Full replay (invoke each spawn through real harness, stub by default)

**Shape:** The tool replays exact spawn order, invoking the real Claude Code harness per spawn with stubbed adapters. Output captured to `state/replay-out/<replay_id>/`. Diff against original audit payloads.

**Pros:**
- True E2E reproduction of the session path
- Stub adapters = deterministic per-run outputs
- Catches harness-level regressions (ordering, hook invocation)
- Minimal code surface (reuse existing harness)

**Cons:**
- Requires live Claude Code environment (can't run in pure unit-test CI without stub harness)
- Slow (spawns N subprocesses serially)
- Operator must install Claude Code CLI to replay

**Risk:** MEDIUM — stubbing must be airtight (one leak ⇒ real provider call).
**Evidence:** Pattern precedent: `_lib/adapters/live/_transport.py` stubbed via `CEO_LIVE_ADAPTER_STUB=1`. Breaker tests (ADR-040) use same mechanism.

### Option B — Event-sourced reconstruct (parse audit log, rebuild decision tree, no harness invocation)

**Shape:** Replay is a parser: walk audit log in order, print "would spawn X with payload Y, would get audit event Z". No subprocess, no harness.

**Pros:**
- Pure read-only; no stub-leak risk
- Fast (single process, no subprocesses)
- No CLI install required

**Cons:**
- Cannot catch harness-invocation bugs (the thing replay is MEANT to expose)
- Cannot validate hook logic changed since original session
- Output is a pretty-printed log, not a repro

**Risk:** LOW — read-only; but also low VALUE (doesn't test the system, just the log).
**Evidence:** `audit-query.py` already does event-sourced reads; a "replay mode" here is a feature of audit-query, not a new tool.

### Option C — Hybrid (Option B default for dry-run, Option A for `--execute`)

**Shape:** Dry-run = event-sourced parse (Option B behavior). `--execute` = real-harness invocation (Option A behavior). Same CLI, same audit events, two backends.

**Pros:**
- Dry-run fast + safe (no stub-leak risk in dry mode)
- Execute mode provides E2E reproduction when needed
- Default is the safe path; power mode opt-in

**Cons:**
- Two code paths to maintain + test
- Determinism regression class must cover both

**Risk:** MEDIUM — two paths but both are well-scoped.
**Evidence:** Pattern precedent: `scan-injection.py` has advisory-mode (read-only) + enforcing-mode (blocking); same "safe default, opt-in power" shape.

## Trade-off matrix

| Dimension | A: Full replay | B: Event-sourced | C: Hybrid |
|---|---|---|---|
| Reproduction fidelity | High | Low | High (execute) |
| Safety (stub-leak risk) | Medium | Zero | Low (exec only) |
| Operator install burden | High (CLI) | Zero | Low (dry default) |
| CI-testability | Low | High | High (dry) + Medium (execute) |
| Code surface | Medium | Small | Medium |
| Maintenance cost | Medium | Low | Medium (two paths) |
| Debug utility (the point) | High | Low | High |
| Weighted sum | 72 | 58 | 91 |

Winner: **Option C (Hybrid)** — 91 vs 72, margin +26% (exceeds ADR-044 10% floor).

## Decision

**Option C — Hybrid. Dry-run is the DEFAULT mode (event-sourced parse). `--execute` opts into real-harness invocation with stub adapters + OTEL disabled + clean-worktree pre-flight + acknowledgment flag.**

### 6 revisit conditions (per ADR-044 pattern)

Re-evaluate if ANY of:

1. **Stub-leak bug discovered** in execute mode → escalate to ADR amendment + feature freeze until patched + full re-audit of all `_transport.py` stub points.
2. **Determinism regression rate >5%** across TestReplayDeterminism fixture runs over 7 days → drop Option A execute support and fall back to Option B pure.
3. **Adopter operator requests `--allow-live` in production** >3 times/month (via feedback or audit) → escalate UX decision: either widen the flag with new gates, or deprecate + strip the path.
4. **Audit-log read API destabilized** (Phase F.0 check-audit-read-api-stable.py fails) → pause replay development until freeze restored.
5. **Session graph format changes** (ADR-038 amendment) → re-verify replay accepts both old + new format, or bump replay SPEC.
6. **Cross-OS drift >15% failure rate** on TestReplayDeterminism → remove `--execute` path (dry-only), ADR-046 SUPERSEDED.

## Consequences

### Positive

1. **Replays never reach real providers by default.** Dry-run is default; `--execute` auto-sets stub adapters. Operators must explicitly flip TWO flags (`--allow-live --owner-confirm`) to touch a live provider — no single-flag footgun.
2. **Adopter-debugging primitive unlocked.** Post-incident, operators can reproduce the exact spawn order to diagnose "why did the debate converge at round 2 instead of round 1". Before this, they had the log; now they have re-execution.
3. **CI-testable in dry mode.** Dry-run is pure read + compute; TestReplayDeterminism hits it 100 runs in <5s.
4. **Audit trail for replays.** Every replay emits `replay_started` + `replay_completed` + per-divergence `replay_diff_produced`. No silent replays.
5. **Multi-user accountability preserved.** `--as-user <original-owner>` gate + audit event distinguishes replayer from original.
6. **Dirty worktree pre-flight.** Prevents mixing replay artifacts with in-progress work.

### Negative

1. **Two code paths.** Dry + execute must track each other's semantics (same flags, same audit shape). Maintenance tax.
2. **Stub-leak risk non-zero.** Execute mode relies on airtight stubbing of live adapters. Any future `_transport.py` addition that forgets to honor `CEO_LIVE_ADAPTER_STUB` would breach the invariant. Mitigation: regression test in TestReplayDeterminism ensures zero live-provider calls during execute replay.
3. **Operator install burden for execute.** Requires Claude Code CLI available at replay time. Dry mode has zero deps.
4. **No harness-version pinning.** Replay assumes the current installed harness matches the one used at original session time. If harness changes between original + replay, results drift. Mitigation: audit-log records harness version; diff flags surface "harness_version_mismatch" as divergence.

### Neutral

1. **Session graph is optional input.** If graph absent, replay derives order from audit-log `ts` + `spawn_ordinal`.
2. **Retention of replay artifacts is operator-managed.** No auto-cleanup; `state/replay-out/` grows until operator removes it.
3. **Future: `--export-fixture` flag** to materialize a replay as a regression test fixture. Out of v1 scope.

## Blast radius

**L2** — new subsystem, reversibility HIGH (additive scripts; removing replay-session.py affects nothing beyond its direct users), no existing hook impacted.

**Reversibility:** HIGH. To disable replay entirely: delete `.claude/scripts/replay/` + remove from SPEC index + ADR-046 SUPERSEDED. Existing audit log + session graph untouched.

## Transition Log

Per ADR-041 format.

| Date | From | To | Evidence-link | PR-ref |
|------|------|-----|---------------|--------|
| 2026-04-16 | stub | PROPOSED (full draft) | PLAN-014 §Phase F.2 | pending |

## References

- **PLAN-014 §Phase F.1 / §F.1a / §F.1b / §F.2** — deliverables
- **ADR-038** — Session graph derived registry (input to replay)
- **ADR-007** — SemVer + additive-only (SPEC/v1/replay.schema.md v1.0.0-rc.1 governance)
- **ADR-040 §7** — live-adapter observability (stub mechanism reused)
- **SPEC/v1/replay.schema.md** — 11-section normative contract (created Phase F.1a)
- **PLAN-014/debate/round-1/consensus.md** — C15 (HIGH — Information Disclosure class)
- **`audit-log.schema.md` v2.6** — 3 registered events (`replay_started`, `replay_completed`, `replay_diff_produced`)

---

**End of ADR-046 PROPOSED full draft.** Flips ACCEPTED on PLAN-014 Phase G merge.

## Enforcement commit

`1551f00110be` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
