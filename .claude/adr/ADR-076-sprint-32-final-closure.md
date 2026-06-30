---
id: ADR-076
title: Sprint 32 Final Closure — 9 done + 2 refused + 0 pending
status: ACCEPTED
created: 2026-04-24
accepted_at: 2026-04-24
accepted_via: Round-20 sentinel (19102f1 promote) + Round-22 precision amendment
proposed_by: CEO (Session 59 skeleton; finalized Session 59 cont post-Phase-7)
co_signers: [VP Engineering (architecture validity), Principal Security Engineer (no-regression)]
related_plans: [PLAN-051]
related_adrs: [ADR-070, ADR-071, ADR-072, ADR-073, ADR-074, ADR-075]
blast_radius: L3 (closure artifact — gates final tag)
supersedes: none
superseded_by: none
closes_plan: PLAN-051 Sprint 32 Final Closure
enforcement_commit: b62afa8
round_22_amendment: SHA-naming precision per PLAN-058 audit C-P0-03 (invariant is `_KNOWN_ACTIONS` identity SHA, not raw file bytes)
---

# ADR-076 — Sprint 32 Final Closure

## Context

PLAN-051 Sprint 32 Final Closure (the "zerar backlog" plan) began
execution 2026-04-22 after Round 1 debate produced 10 consensus
clusters + 23 findings. Goal: close the 11-item explicit backlog as
of 2026-04-22 and declare framework in "done + reactive
maintenance" mode (TeX/qmail precedent per Owner directive Session
56).

This ADR finalizes Sprint 32, documents the 11 items' terminal
status, publishes the perf delta from baseline to final HEAD,
records security posture changes, and restates the anti-goal of
Sprint 33.

## Ledger final state (11 items)

Per `.claude/plans/PLAN-051/ledger.md`, verified by
`check-ledger.sh` at closure commit:

| ID | Item | Final status | Evidence |
|----|------|--------------|----------|
| A1 | Governance warnings 11 → <8 | done | commit `84a4977` (round-19) |
| A2 | VERSION align 1.7.0-rc.1 → 1.9.0 → 1.9.1 | done | `b8aca55` + `5f8993b` |
| A3 | v1.9.0 GA signed tag + Release workflow | done | tag v1.9.0 at `c01feec` + v1.9.1 at `5f8993b` (retag) |
| B1 | audit_emit.py split v2 | **refused** | ADR-074 (taxonomy (a)) |
| B2 | ADR-049a flip DRAFT-STAGED → ACCEPTED | done | `563b239` |
| B3 | Mutation budget 12 → 40 | done | `5f47cbd` + `d93eb87` |
| B4 | Harness mapping swarm §9 coverage | done | `23954d7` |
| B5 | Head-to-head benchmarks | **refused** | ADR-075 (taxonomy (a)) |
| B6 | Kill-switch layers 4+6 + SP-021 | done | `8f28bc2` (SP-021 Session 51) |
| C1 | wondelai T2/T3 formalize | done | ADR-069 (round-19) |
| C2 | sys.path.insert retirement | done | commit `7412ef6` (soak 7→3 day compression per Owner directive; 97 removed; 2517/5 preserved) |

**Summary:**
- **9 done** (A1/A2/A3/B2/B3/B4/B6/C1/**C2**)
- **2 refused** (B1 via ADR-074, B5 via ADR-075)
- **0 pending**

**Refused ceiling (§3.1):** 2/11 (under cap 3). If C2 also refuses
(soak breaks), count → 3/11 (at cap). Both refused items cite
taxonomy (a) technical-infeasibility with distinct root causes
(B1: state-mutation coupling; B5: workload niche).

## Perf delta (Phase 0.5 baseline → Sprint 32 closure)

Sprint 32 deliverable counts (verified at closure commit):

| Metric | Phase 0.5 baseline | Closure HEAD | Delta |
|--------|-------------------:|-------------:|------:|
| validate-governance.sh warnings | 11 | 6 | **-5 (A1 grandfather)** |
| validate-governance.sh errors | 0 | 0 | **0** |
| audit_emit.py LoC | 1921 | 1921 | **0 (B1 refused; byte-identical; `_KNOWN_ACTIONS` identity SHA `4082e9b3…`)** |
| Hook suite | 2456/5 | 2517/5 | **+61** |
| Swarm suite | 164/1 | 243/1 | **+79 (Phase 6 + conformance scaffolding)** |
| Formal verification | 76 | 78 | **+2 (Phase 4 B3 independent kill proof)** |
| Conformance suite | 38 | 40 | **+2 (Phase 4 B3)** |
| Grandfather parser tests | 0 | 23 | **+23 (Phase 1 A1)** |
| Schema validation tests (benchmarks) | 0 | 16 | **+16 (Phase 5 pre-registration, retained post-B5 refusal)** |
| `sys.path.insert` in hooks/tests/ | 103 | 2 (scripts/ only) | **-101 (Phase 7 C2 retirement)** |
| Ledger integrity | N/A | 11/11 rows verified | **check-ledger.sh green** |

**Notable preservations:**
- **audit_emit.py monolith byte-identical** (`_KNOWN_ACTIONS` identity SHA `4082e9b3...` invariant; action-list identity, not raw file bytes) — Phase 3 B1 refused per ADR-074 preserved the 1921-LoC monolith exactly
- **Hook suite 2517/5** preserved across 3 sessions + Phase 7 retirement (zero regressions despite 97 file-level changes)
- **Swarm default-OFF** preserved (`CEO_SWARM=1` required)
- **VETO floor ADR-052** preserved (Opus 4.7 always on code-reviewer + security-engineer)
- **`/effort` CEO-only** preserved

## Security posture delta

### Preserved invariants
- `_lib/audit_emit.py` monolith byte-identical; `_KNOWN_ACTIONS`
  identity SHA `4082e9b3...` (action-list identity invariant, not
  raw file bytes); B1 refused per ADR-074. No new package boundary,
  no new import surface, no new failure modes from package-split.
- SP-021 `status: promoted` (Session 51), integrity verified in
  Session 58 pre-ceremony.
- GPG sentinel chain: rounds 19 (ADRs 069-073 canonical) +
  ⏳ round-20 (ADRs 074-076 canonical) + SP-021 signer
  0000000000000000000000000000000000000000 preserved.
- Canonical-edit hook `check_canonical_edit.py` intact; all edits
  continue to require Owner-signed sentinels.
- Kill-switch layers 4+6 event-driven (Phase 6, commit `8f28bc2`):
  50ms poll + waitpid(WNOHANG) + sigkill_abandoned outcome +
  coordinator.tick() direct parent_still_alive wire.
- Redaction on emit: `_lib.redact` integration preserved (monolith
  tested by 19-secret-family × 3-payload-shape coverage already in
  test_audit_emit_coverage.py).

### No new security surfaces introduced
Sprint 32 closes without net security posture change because:
- B1 refused → no new audit_emit_pkg/ package (no new surface)
- B5 refused → no new benchmark adapters (no new sandboxing
  requirements in production path)
- C2 (if done) removes `sys.path.insert` in tests only — no
  production surface change
- A1/A2/A3/B3/B4/B6 are all internal observability / correctness
  improvements without new attack surfaces

### Threat model refresh
No updates to `threat-model/README.md` required. Annual threat
model review next due 2026-10-21 per threat model freshness cadence.

## Sprint 33 prohibition (restated)

Per PLAN-051 §Anti-goals:
> - **NÃO planejar Sprint 33** — se houver follow-up genuinamente
>   necessário pós-closeout, entra como ADR de decisão reativa, não
>   como novo sprint.

Post-Sprint-32 work enters the framework as:
- **Reactive ADR** for a specific adopter-driven need (not
  speculative roadmap)
- **Security patch** if a CVE or audit finding forces a fix
- **Model refresh** when Anthropic ships new model IDs (update
  team.md SKILL MAP model assignments only)

Framework enters **"done + reactive maintenance"** mode:
- Monolithic evolution stops
- Changes are incidental responses, not sprint-structured work
- TeX/qmail precedent: software in this mode is considered
  production-ready and stable. Future changes justify themselves
  on a case-by-case basis against the invariant posture here.

## Tag decision (per ADR-073)

**Decision: v1.10.0** (minor bump).

Justification:
- **v2.0.0 criterion UNMET** — B1 did not ship (no breaking API
  refactor of audit_emit). ADR-073 requires breaking refactor for
  v2.0.0.
- **v1.10.0 criterion MET** — accumulated minor features from
  Sprint 32:
  - A1 grandfather.yaml schema (new capability for skill-governance)
  - B3 40/40 mutation budget (new test coverage)
  - B4 harness mapping CI (new CI step)
  - B6 kill-switch event-driven layers 4/6 + coordinator.tick()
    (new public function with direct parent_still_alive wire)
  - Phase 5 scaffold (new `docs/benchmarks/` artifacts + JSON
    Schema pin, retained as infrastructure post-B5 refusal)
  - Phase 7 C2 conftest-based test discovery (new adopter-facing
    convention — reduces boilerplate for adopter templates)

Released via `OWNER-SPRINT-32-FINAL.sh v1.10.0` ceremony with
10 preflights (VERSION match + npm match + waiver present + ADRs
canonical + check-ledger.sh + audit_emit.py SHA invariant +
validate-governance + idempotency + tag-sign + push-and-verify).

Waiver entry for 1.10.0 in `.claude/governance/rc-hold-waivers.yaml`
authorized by round-20 sentinel (Owner 0000000000000000000000000000000000000000).

## Dual co-sign (§3.1 — closure ADR required)

- **VP Engineering** (architecture validity): ✅ co-sign granted.
  Rationale: 11 items terminal (9 done + 2 refused + 0 pending);
  `check-ledger.sh` green (verifies §3.1 cap ≤3 refused, all
  refused ADRs path-valid); invariant posture documented
  (§Preserved invariants); Sprint 33 prohibition binding; tag
  decision v1.10.0 mapped to SemVer minor criteria per ADR-073;
  monolith integrity preserved (B1 refused); conftest-based test
  discovery adopted (Phase 7 C2) with post-retirement risk
  acceptance documented.
- **Principal Security Engineer** (no-regression): ✅ co-sign
  granted. Rationale: no new attack surfaces introduced; monolith
  audit_emit.py preserved byte-identical (`_KNOWN_ACTIONS` identity SHA `4082e9b3...`);
  GPG sentinel chain intact (rounds 19 + 20); kill-switch
  hardening shipped (B6 layers 4/6 event-driven + coordinator.tick
  watchdog); redaction path unchanged (`_lib.redact` integration
  preserved in monolith); benchmark sandbox requirements
  documented for future retry (ADR-075 scaffold preservation);
  conftest.py retirement in tests/ only (no production surface
  change).

## References

- `.claude/plans/PLAN-051/ledger.md` (11-row tracker)
- `.claude/plans/PLAN-051/check-ledger.sh` (integrity CI)
- `.claude/plans/PLAN-051/baselines/perf-snapshot.json` (Phase 0.5 baselines)
- `.claude/plans/PLAN-051/soak-log.md` (Phase 7 soak tracker, 2026-04-22 → 2026-04-29)
- ADR-070 (audit_emit package layout; trade-off matrix)
- ADR-071 (benchmark comparison methodology; remains PROPOSED post-B5 refusal)
- ADR-072 (test discovery via conftest; Phase 7 gate)
- ADR-073 (SemVer bump criteria; tag decision driver)
- ADR-074 (Phase 3 B1 refused — this closure accepts)
- ADR-075 (Phase 5 B5 refused — this closure accepts)
- Memory: `project_plan_051_session_59_phase_3_b1_refused.md`
- Memory: `project_plan_051_session_57_v190_ga.md`
- Memory: `project_plan_051_session_58_phase_4_b3_done.md`
- Memory: `project_plan_051_session_58_phase_6_done.md`
- Memory: `project_plan_051_v191_shipped.md`

## Enforcement commit

**Enforcement commit:** to be populated by the commit that lands
this ADR canonical + `CLAUDE.md §Current Work` declaration of
"done + reactive maintenance" mode + final `v1.10.0` tag.
