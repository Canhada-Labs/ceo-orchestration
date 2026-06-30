---
name: learning-analytics
description: Engagement metrics, dropout prediction, and early-warning systems for K-12 and higher-ed with explicit fairness and privacy trade-off discipline. Covers aggregation floors (N≥5 FERPA de-identification), privacy-preserving aggregation (k-anonymity, differential privacy), disparate-impact audit per protected subgroup, opt-out propagation through training data, model calibration display, and retrain-schedule fairness re-evaluation. Use when designing any staff-facing or student-facing dashboard, prediction model, early-warning system, or engagement score. Combines with observability-and-ops (core) for telemetry infrastructure.
owner: Dr. Léa Mbeki (Learning Analytics Engineer, domain persona)
secondary_owner: Priya Narayanan (Student Privacy Engineer, domain persona)
tier: domain:edtech
scope_tags: [analytics, ml, fairness, dropout-prediction, engagement, de-identification, disparate-impact]
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: edtech
priority: 8
risk_class: low
stack: []
context_budget_tokens: 600
inactive_but_retained: true
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: false, priority: 10}
  fintech: {active: false, priority: 10}
  trading-readonly: {active: false, priority: 10}
  generic: {active: false, priority: 10}
activation_triggers: []
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/analytics/**"
  - "**/dashboards/**"
  - "**/predictions/**"
  - "**/engagement/**"
  - "**/early-warning/**"
---

# Learning Analytics

## Cardinal Rule

**A prediction is a hypothesis about a child. If you can't audit it
per subgroup, you can't ship it.** Accuracy is not a sufficient
metric; disparate impact is a launch blocker.

## The four failure modes of edtech analytics

1. **De-identification failure** — aggregates that re-identify small
   subgroups via cross-tab (e.g. "1 ESL student in AP Calc at
   School X").
2. **Disparate impact** — model FPR/FNR varies by protected subgroup;
   interventions disproportionately flag certain cohorts.
3. **Opt-out leakage** — student opted out of analytics but their
   data is still in the training set.
4. **Over-certain UI** — single number shown to teacher without
   calibration; staff act on precision they don't have.

Every edtech analytics feature must explicitly defend against all four.

## Aggregation floor (FERPA de-identification)

FERPA de-identification guidance: suppress cells where N is small
enough to risk re-identification. Practical floors:

| Context | Suppress when |
|---|---|
| District-level report | N < 10 per cell |
| School-level report | N < 5 per cell |
| Classroom-level report to staff | Always (staff see the student directly) |
| Public dashboard (state, press) | N < 10 per cell + noise addition |

### Cross-tab trap

A report that shows:
- "Students on IEP in AP Calc: 3"
- "Hispanic students in AP Calc: 2"
- "Total in AP Calc: 12"

...may let an observer deduce "the Hispanic student on IEP in AP
Calc is X" if they know the class roster. **Cross-tab suppression**
must consider the combination, not just cells individually.

Pattern:

```python
def display_cell(n: int, cross_tab_context: dict) -> str:
    floor = AGGREGATION_FLOOR[cross_tab_context["scope"]]
    combined_floor = max(floor, detect_cross_tab_leakage(cross_tab_context))
    if n < combined_floor:
        return "< suppressed >"
    return str(n)
```

## Disparate-impact audit

### Protected subgroups (edtech-specific)

- Race / ethnicity
- Gender (including non-binary — if self-reported, respect the categories)
- Socioeconomic status (free/reduced-lunch flag is a common proxy)
- IEP / 504 status
- ESL / ELL status
- First-generation college (higher-ed)
- Home-language-not-English

### Minimum fairness eval suite per model

For each protected subgroup, report:

1. **Group size** (n in each group)
2. **Confusion matrix** (TP, FP, FN, TN)
3. **FPR and FNR**
4. **Calibration plot** (predicted probability vs. actual rate,
   binned)
5. **Intervention rate** (if the model drives a real-world action,
   what % of each group gets the action?)

### Blocker thresholds

- **FPR disparity:** FPR for any subgroup > 2x majority rate → blocker
- **FNR disparity:** FNR for any subgroup > 2x majority rate → blocker
- **Calibration:** mean predicted probability differs from actual rate
  by > 10 percentage points in any subgroup → blocker
- **Intervention rate disparity:** 3x majority rate → blocker (unless
  directly justified by outcome evidence)

These are floors. Some models warrant tighter bounds.

## Opt-out propagation

Opt-out means:

1. **Training data exclusion.** Student's historical data is excluded
   from the next retrain. Not just suppressed from display.
2. **Inference exclusion.** The model doesn't predict for this
   student.
3. **Display exclusion.** Any derived visualization (engagement heat
   map, class dropout risk average) excludes this student.

Incorrect (common):

```python
# BAD: inference guard only
if not student.analytics_opt_out:
    score = model.predict(student.features)
    display(score)
# Student is still in the training data, still shaping the model's
# behavior. Their privacy choice is partially honored.
```

Correct:

```python
# Training pipeline
training_set = [s for s in all_students if not s.analytics_opt_out_at_snapshot_time]
# (opt_out propagated by the snapshot event, not a live query — this
# matters because a student who opts-out today was in yesterday's
# snapshot; they're excluded from the NEXT retrain, not retroactively
# from already-trained models. Honest SPEC: "effective at next
# retrain, which is scheduled quarterly."
```

## UI contract for prediction surfaces

When showing a predicted risk/score to a human (teacher, advisor,
student):

- [ ] **Calibration interval** ("60%, ±12pp @ 90% confidence")
- [ ] **At least 3 feature attributions** ("driven by: attendance ↓,
      recent quiz score ↓, participation ↑")
- [ ] **Intervention guidance** ("suggested: 1:1 check-in in the
      next 2 weeks")
- [ ] **Uncertainty acknowledgement** ("this is a hypothesis, not a
      diagnosis")
- [ ] **Opt-out respect indicator** ("this student opted out: no
      prediction shown")
- [ ] **Color-blind-safe encoding** (never red/green only)

## Fairness artifact retention

For every launched model:

- Version fairness report (per-subgroup eval) per retrain
- Retain for **model deployment lifetime + 1 year** (EDTECH-018)
- Retain even after model deprecation (audit trail for decisions
  made under that model)

Storage format: append-only, content-addressed (hash of report is
its ID). Never overwritten.

## Privacy-preserving aggregation (when it earns its keep)

- **k-anonymity** (k ≥ 5 minimum, often k ≥ 10): every row is
  indistinguishable from k-1 others on quasi-identifiers.
- **Differential privacy** (ε-DP): noise added to aggregates; strong
  guarantee but reduces utility. Worthwhile for public-facing data;
  usually overkill for internal staff dashboards.
- **Federated learning:** keep raw data on device; train global model
  on gradients. Complex; adopt only with clear privacy benefit.

## Checklist for every analytics / ML feature

- [ ] **Aggregation floor enforced on every dashboard cell?** (EDTECH-014)
- [ ] **Cross-tab suppression considered?**
- [ ] **Per-subgroup fairness eval current?** (EDTECH-015)
- [ ] **Opt-out propagated to training data?** (EDTECH-016)
- [ ] **Calibration interval + feature attributions shown?** (EDTECH-017)
- [ ] **Fairness artifacts versioned + retained?** (EDTECH-018)
- [ ] **Retrain schedule includes fairness re-eval?**
- [ ] **Intervention-rate disparity tracked post-launch?**

## References

- `.claude/skills/domains/edtech/skills/student-data-privacy/SKILL.md`
- `.claude/skills/core/observability-and-ops/SKILL.md`
- NIST SP 800-188 (de-identification of government datasets)
- "Fairness and Machine Learning" (Barocas, Hardt, Narayanan, 2019+)
- IMS Global Caliper Analytics (event model)
- FERPA de-identification guidance (PTAC)
