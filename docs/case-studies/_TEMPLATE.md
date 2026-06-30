# Case study — {{ADOPTER_NAME}}

> **Status:** `draft` | `complete`
> **Sprint:** PLAN-{{NNN}} Phase {{X}}
> **Dates:** {{ISO_START}} → {{ISO_END}}
> **Owner verdict:** Y (promote to next sprint) | N (block / iterate) | `pending`

## 1. Adopter context

| Field | Value |
|-------|-------|
| Project name | {{ADOPTER_NAME}} |
| Domain | {{fintech \| trading-hft \| lgpd-heavy-saas \| edtech \| government \| other}} |
| Team size | {{N}} engineers + Owner |
| Stack | {{e.g. Python + FastAPI + PostgreSQL + Stripe}} |
| Repo size at install | {{LOC} / {N files}} |
| Prior framework exposure | {{never / tried X / rolled own}} |
| Why install ceo-orchestration now | {{1-3 sentences}} |

## 2. Install timeline

| Step | Outcome | Time spent | Blockers |
|------|---------|-----------|----------|
| `git clone` framework | {{OK / failed}} | {{N}} min | {{none / ...}} |
| `bash scripts/install.sh --profile {{...}}` | {{OK / failed}} | {{N}} min | {{none / ...}} |
| First Agent spawn | {{OK / failed}} | {{N}} min | {{none / ...}} |
| First audit-log entry | {{OK / failed}} | {{N}} min | {{none / ...}} |
| First friction logged | {{time}} | — | — |

**Time to first productive use:** {{hh:mm}} (from clone to first successful spawn).

**Framework fixes applied mid-install:** {{list of PRs merged during Phase 1}} / none.

## 3. Use period

**Window:** {{ISO_START}} → {{ISO_END}} ({{N}} calendar days)
**Active days** (days with ≥1 spawn): {{N}}
**Pauses ≥48h:** {{N}} ({{impact: extended window? y/n}})

## 4. Quantitative metrics

Coletado via `.claude/scripts/adopter-metrics.py --window 7d` rodado toda
sexta-feira 18:00 local. Raw JSON outputs em
`.claude/plans/PLAN-{{NNN}}/metrics/week-*.json`.

### Summary table (aggregated across weeks)

| Metric | Week 1 | Week 2 | Total | Avg/week | Notes |
|--------|--------|--------|-------|----------|-------|
| Sessions | {{N}} | {{N}} | {{N}} | {{N}} | |
| Spawns | {{N}} | {{N}} | {{N}} | {{N}} | |
| Veto rate | {{X.X}}% | {{X.X}}% | — | {{X.X}}% | |
| Task completion | {{X.X}}% | {{X.X}}% | — | {{X.X}}% | |
| Tokens (actual / predicted) | {{A/P (ratio)}} | {{A/P (ratio)}} | — | — | |
| Custom skills count | {{N}} | {{N}} | — | — | |
| ADRs activated (distinct) | {{N}} | {{N}} | — | — | |

### Trend analysis

- **Spawn growth week-over-week:** {{+N%, -N%, flat}}
- **Veto rate trajectory:** {{increasing signals friction; decreasing signals adaptation}}
- **Completion ratio trajectory:** {{interpretation}}
- **Custom skills introduced:** {{list + why — signals framework gap when count is high}}

## 5. Qualitative friction log highlights

Full log: `.claude/plans/PLAN-{{NNN}}/frictions.md`.

### Top 5 frictions by severity

| # | Severity | Category | Summary | Resolution |
|---|----------|----------|---------|-----------|
| 1 | P0 | {{install/hook/spawn/docs/ux/governance/performance/other}} | {{1-line}} | {{PR ref / deferred / ...}} |
| 2 | P0/P1 | ... | ... | ... |
| 3 | ... | ... | ... | ... |
| 4 | ... | ... | ... | ... |
| 5 | ... | ... | ... | ... |

### Friction distribution

| Severity | Count | % of total |
|----------|-------|-----------|
| P0 (blocker) | {{N}} | {{X.X}}% |
| P1 (serious) | {{N}} | {{X.X}}% |
| P2 (nice-to-have) | {{N}} | {{X.X}}% |
| P3 (cosmetic) | {{N}} | {{X.X}}% |

| Category | Count |
|----------|-------|
| install | {{N}} |
| hook | {{N}} |
| spawn | {{N}} |
| docs | {{N}} |
| ux | {{N}} |
| governance | {{N}} |
| performance | {{N}} |
| other | {{N}} |

## 6. Framework fixes shipped during sprint

| PR | Commit | Summary | Friction ID |
|----|--------|---------|-------------|
| {{#NNN}} | {{sha7}} | {{1-line}} | {{P0#1 ...}} |
| ... | ... | ... | ... |

**Total LOC delta to framework:** {{+N / -N}} across {{N}} files.

## 7. Outstanding issues deferred

| Friction ID | Severity | Reason for defer | Target sprint |
|-------------|----------|------------------|---------------|
| {{P1#3}} | P1 | {{1-line}} | PLAN-{{NNN+1}} |
| ... | ... | ... | ... |

## 8. Owner verdict

**Decision:** `Y` / `N`

**Rationale (2-3 sentences):**

{{Example Y: "Veto rate dropped from 12% week 1 to 3% week 2 — framework guardrails
are helping, not obstructing. P0 fixes shipped were real gaps but now closed. Ready
for second adopter."}}

{{Example N: "Custom skills count jumped from 2 to 11 week 2 — the framework's
core skill library doesn't cover enough of {{ADOPTER_NAME}}'s domain. Before
promoting, need to evaluate whether to ship a new domain profile vs accept gap."}}

**Next-sprint gate satisfied:**
- [ ] Zero P0 unfixed open
- [ ] P1 triaged into next-sprint scope OR defer-with-rationale
- [ ] Smoke install green post-fixes
- [ ] Framework test suite green
- [ ] Case study reviewed and signed off by Owner

---

**Generated from:** `docs/case-studies/_TEMPLATE.md` (PLAN-015 Phase 0.2).
Do not hand-edit the template file — copy it first.
