# ADR-103 — Calendar gate final purge (extends ADR-095, supersedes ADR-093 §moratorium)

**Status:** ACCEPTED (Owner GPG ceremony 2026-05-03 S80; cosmetic body flip 2026-05-05 S87 — drift-fix of S80 ceremony per PLAN-072 §7)
**Date:** 2026-05-03
**Enforcement commit:** 56b8e90 — `ceremony(plan-072): calendar gate final purge — ADR-103 ACCEPTED + ADR-093 superseded + release.yml 7d→24h`
**Supersedes:** ADR-093 §60-day-moratorium clause (the per-plan refusal cap clause is preserved)
**Extends:** ADR-095 (calendar-gate-retraction expanded scope)
**Anchored on:** ADR-096 (vibecoder-only-by-design)

## Decision drivers

- **Owner directive 2026-05-03:** CEO time-estimate errors caused Owner to approve GPG ceremonies for calendar gates that delay release without empirical justification. PLAN-068 §5.3 estimated "~7 weeks calendar to v1.12.0 GA"; v1.11.6 actually shipped Day 1 (50× overestimate). ADR-093 (ACCEPTED 2026-04-27) impose 60-day moratorium until 2026-06-26, blocking PLAN-065 v1.13.0 path 54+ days after ready-to-ship readiness.
- **Same-LLM bias in CEO estimates:** training data carries big-tech / regulated-industry sprint discipline (soak windows, RC hold periods, moratorium cycles) that the CEO copied without questioning fit. Vibecoder-only framework (ADR-096, adopter_count=0) has no external pressure for "settle periods."
- **Mechanical replacement available:** Codex external re-pass per ADR-095 #6 + ADR-052 VETO floor + canonical-edit GPG ceremony are all *mechanical* gates. Calendar buffers add zero protective signal beyond mechanical gates for vibecoder-only thesis.
- **Empirical evidence:** PLAN-068 v1.11.6 GA shipped 1 day after CEO timeline projected 7 weeks. PLAN-069 Phase 1 (this PR) shipped same-session as Round 1 critique. Real cadence is per-session, not per-week.

## Context

The framework accumulated 7 calendar-bound gates between Sprint 30 and Session 73:

1. **14-day CI green streak on `main`** — retracted via ADR-095 (Wave session 73 ceremony 2026-04-29)
2. **30-day no-retag streak** — retracted via ADR-095 same ceremony
3. **emit_mcp_injection_finding shipped** — structural (ship), not calendar; closed Wave B
4. **Cost reporting accurate end-to-end** — structural; closed Wave B
5. **One refused-ADR retracted** — structural (action); ADR-091 closed Wave C
6. **Outside reviewer 1-page second opinion** — replaced by Codex external CLI per ADR-095 §gate-#6 (mechanical, not calendar)
7. **60-day refused-ADR moratorium** (ADR-093) — RETAINED as "structural pattern brake" per ADR-095, but empirical evidence 2026-05-03 shows it's blocking PLAN-065 v1.13.0 without protective benefit.
8. **7-day RC hold** in `release.yml` (PLAN-013 Phase 0 item 0.3) — predates ADR-095; copies external SDK release cycle; calendar without empirical fit for vibecoder-only.
9. **6-week MCP soak window** (PLAN-068 §A3) — copies SDK release cycle; no external SDK consumers per ADR-096.
10. **14-day CI-green soak before tag v1.12.0** (PLAN-068 §S6) — pre-ADR-095 reference still in plan body; retroactive fix needed.
11. **PLAN-068 §5.3 timeline** — "~7 weeks calendar to v1.12.0 GA" — proven 50× wrong by v1.11.6 Day-1 ship.
12. **PLAN-065 §52 calendar gate** — depends on ADR-093 expiry (2026-06-26) for v1.13.0 ship; auto-resolves once ADR-103 lands.

ADR-095 retracted gates 1+2. ADR-103 retracts the rest except where mechanical (CR + Sec VETO floor; Codex re-pass; canonical-edit GPG; pre-tag pytest GREEN).

## Decision

### Retract / supersede

| Gate | Action | Replacement |
|---|---|---|
| ADR-093 §60-day-moratorium | **SUPERSEDED** | Per-PR Codex re-pass per ADR-095 §gate-#6 (mechanical) |
| ADR-093 §per-plan-refusal-cap (≤2) | **PRESERVED** | Structural anti-sandbagging signal — not calendar |
| `release.yml` 7-day RC hold | **REDUCED** to 24h | Mechanical window for Codex re-pass turnaround per ADR-095 §gate-#6 |
| PLAN-068 §5.3 calendar timeline | **DROPPED retroactively** | Estimates re-stated in 2-axis format (compute_hours + owner_physical_min); calendar_buffer_days defaults to 0 |
| PLAN-068 §A3 6-week MCP soak | **DROPPED** | Per ADR-096 vibecoder-only — no external SDK consumers |
| PLAN-068 §S6 14-day CI-green soak | **DROPPED** | Already retracted by ADR-095; remove residual reference |
| PLAN-065 §52 post-2026-06-26 gate | **DROPPED** | Depends on ADR-093 §moratorium superseded above |
| PLAN-070 R6 ADR-093 trigger | **MARKED N/A** | ADR-103 supersedes the trigger condition |

### Preserved mechanical gates (NOT calendar)

| Gate | Mechanism | Why preserved |
|---|---|---|
| ADR-052 VETO floor (Opus for CR + Sec) | Hardcoded in dispatcher | Quality-critical, empirical via tournament |
| Codex external re-pass per ADR-095 §gate-#6 | Pre-tag mechanical | Anti same-LLM bias, mandatory before any GA tag |
| Canonical-edit GPG ceremony per `check_canonical_edit.py` | Hardcoded hook | Owner-physical authorization for sensitive files |
| Pre-tag full pytest GREEN per `release.yml` | Mechanical CI step | Regression detection |
| ADR-093 §per-plan-refusal-cap (≤2) | PLAN-SCHEMA validator | Anti-sandbagging signal — not time-bound |

### New rule (always-on)

CEO MUST split time estimates in 2 axes:

```yaml
estimate:
  compute_hours: X        # Claude Code wall-clock REAL se rodar agora
  owner_physical_min: Y   # GPG ceremonies + manual Codex review
  calendar_buffer_days: 0 # JUSTIFIED per specific ADR/incident or 0 (default)
```

`calendar_buffer_days > 0` requires explicit empirical citation
(specific ADR or measured incident); generic "best practice" / "settle
period" / "review window" insufficient. Strike if uncited.

## Consequences

### Positive

- **PLAN-065 v1.13.0 path destravado AGORA** (was: post-2026-06-26 = 54-day prison)
- **PLAN-068 v1.12.0 ships when ready** (was: Day 28-50 estimated)
- **Real cadence: per-session, not per-week** — aligned with empirical evidence (S79 v1.11.6, S80 v1.11.7 Phase 1)
- **Owner approval friction reduced** — CEO time estimates now require empirical anchor; Owner can cite ADR-103 to reject inflated calendar buffers
- **Mechanical gates preserved** — quality-critical paths still protected (CR + Sec VETO, Codex re-pass, GPG ceremony, pytest GREEN)

### Negative

- **Loss of "settle period" buffer** — refused-ADR pattern detection now per-PR (Codex), not 60-day window. Cost: if a refusal-pattern emerges between Codex re-passes, detection delayed by 1 PR cycle (~1 session). Mitigation: Codex re-pass cross-model gate per ADR-095 already catches same-LLM bias mechanically.
- **Retroactive amendments to plans** — PLAN-068 §5.3 calendar timeline DROPPED with note explaining the CEO calendar-gate-invention pattern. Some readers may find the historical narrative confusing without the note.
- **`release.yml` 7d → 24h** — narrower window for Codex re-pass turnaround. Mitigation: Owner runs Codex re-pass synchronously before tagging; the 24h is a safety net, not the primary mechanism.

### Neutral

- **ADR-091 RETRACTED** (dogfood deferred) — kept on disk as historical record per ADR-093 §Part-3 reversibility precedent. ADR-093 follows same pattern.
- **`docs/READINESS-STATUS.md`** — non-canonical doc; will need a follow-up update post-ADR-103, not blocking.

## Alternatives considered

- **Option A — Keep ADR-093 60-day moratorium intact:** REJECTED. Empirical evidence 2026-05-03 (S80 audit) shows it blocks PLAN-065 v1.13.0 without protective benefit. Same-LLM bias mitigation already mechanical via ADR-095 §gate-#6 Codex re-pass.
- **Option B — Reduce ADR-093 to 14 days:** REJECTED. Arbitrary cut; doesn't address root cause (CEO inventing calendar gates without empirical base). 14d still blocks current PLAN-065 timeline ~10 days.
- **Option C — Drop ADR-093 entirely (including refusal cap):** REJECTED. Per-plan refusal cap (≤2) is structural anti-sandbagging signal independent of calendar; preserve via ADR-103 §Preserved.
- **Option D — Expand ADR-095 in-place** (re-edit the existing ADR): REJECTED. ADR-095 ACCEPTED 2026-04-29 with specific scope (gates #1+#2). New ADR (-103) preserves attribution + cleaner historical trail.
- **Option E — Drop release.yml 7d RC hold entirely:** REJECTED. Some safety-net window helps when Owner is asynchronous (e.g., overnight tag without immediate Codex re-pass). 24h is the minimum that allows mechanical re-pass turnaround.

## Empirical evidence cited

1. **PLAN-068 §5.3 timeline error:** estimated "Earliest GA v1.12.0 ~7 weeks from this session"; v1.11.6 GA shipped Day 1 (S79 overnight). Source: `git log --oneline v1.11.6` vs PLAN-068 commit `12a4ff0`.
2. **PLAN-069 Phase 1 same-session ship:** Phase 0 gap-analysis + Phase 0.5 PoC + Round 1 + Phase 1 Wave A + Wave B + 89 tests + 97% coverage all in S80 (~10h compute). Plan estimated "2 sessions / 6-10h" — within 2× tolerance.
3. **Audit-tokens 30d window:** zero `weak_model` / `overpowered` / `wasteful_thinking` findings — calendar gates aren't preventing what they claim to prevent (cost waste comes from model misroute, not pattern recurrence). Source: `python3 .claude/scripts/audit-tokens.py --window 30`.
4. **Refused-ADR pattern:** since ADR-093 ACCEPTED 2026-04-27, zero refused ADRs authored. ADRs 094-100 all ACCEPTED. The "moratorium" is fighting a non-recurring pattern.

## References

- ADR-095 — Calendar gate retraction (14d CI + 30d no-retag) — extends here
- ADR-093 — Refused-ADR moratorium — supersedes §60d clause; preserves §per-plan cap
- ADR-096 — Vibecoder-only-by-design — anchor for retraction rationale (no external adopter pressure)
- ADR-052 — Role-to-model VETO floor — preserved (mechanical, not calendar)
- ADR-014 — SemVer + RC policy — original source of `release.yml` 7d hold; 24h replacement preserves SemVer compliance for vibecoder
- PLAN-072 §1 — full audit table
- PLAN-072 §3 — concrete amendment patches
- Memory feedback: `feedback_calendar_gates_invented.md` (always-on)
