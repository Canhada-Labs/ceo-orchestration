# `benchmarks/calibration-samples/` — directory layout

> **Owner:** Principal QA Architect.
> **Purpose:** PLAN-012 D2 inter-rater / intra-rater κ calibration
> artefacts. Raw grades gitignored until consensus reached; aggregated
> analysis published.

## Tree

```
benchmarks/calibration-samples/
├── README.md           # this file
├── corpus/             # raw items to grade (Sprint 12+ populates)
│   └── .gitkeep
├── grades/             # per-rater CSVs — GITIGNORED
│   └── .gitkeep
└── analysis/           # aggregated κ + CI reports — PUBLISHED
    └── 2026-Q2-initial-run.md
```

## `corpus/` — items to grade

Stratified random draw from `benchmark_run` audit events in last 30
days (see SOP §2). One JSON file per item, pre-redacted per blinding
protocol (SOP §4). Each file: `item_id`, `payload` (input judge saw),
`llm_claim` (textual claim, numeric score stripped), `llm_reasoning`
(prose rationale).

Sprint 13 follow-up: population script + deterministic redactor.
Until then, corpus is hand-populated by a second party per SOP §5.

## `grades/` — per-rater CSVs (gitignored)

Schema (SOP §9):
```
item_id,rater_id,label,timestamp,duration_s
g-001,rater-A,pass,2026-05-01T10:32:00Z,42
```

**Gitignore rationale.** `grades/*.csv` appears in repo-root `.gitignore`:
1. Timing patterns can leak rater identity.
2. Rater-A labels visible to rater-B before disagreement round destroys
   blinding that underwrites the measurement.
3. After disagreement round concludes, aggregated results flow to
   `analysis/`; raw grades retain off-repo for 7-year local retention
   (SOP §10) and never enter git.

**Local storage.** Raters keep CSVs under non-synced local path (e.g.
`~/ceo-calibration/<plan>/<rater>/`). Second party (no conflict of
interest) collects for aggregation step.

## `analysis/` — published κ reports

One markdown per run, named `<year>-Q<quarter>-<run-label>.md`, with:

- Collection window (start/end)
- N (inter-rater) + n (intra-rater retest)
- κ̂ + bootstrap 95% CI (lower/upper) + Landis-Koch band
- Disagreement count + adjudication log
- κ_intra
- Flip-gate status (FLIP-READY / FLIP-BLOCKED / PRELIMINARY)
- Raw-grade SHA-256 hash (integrity)

The **initial seed** `2026-Q2-initial-run.md` documents the
pre-registered plan before any data is collected. Subsequent runs
append new files; nothing deleted or overwritten.

## Scripts

- `.claude/scripts/k-calibration.py` — Cohen's κ + bootstrap CI +
  Landis-Koch (unweighted / nominal — primary Sprint 12)
- `.claude/scripts/calibration-kappa.py` — weighted κ on 0–10 Likert
  (Sprint 11 ordinal, unchanged)

## Related

- `docs/labelling-sop-judge-calibration.md` — pre-registered SOP
- `.claude/benchmarks/human-sample-calibration.md` — living κ protocol
- `docs/measurement-protocols.md` — cross-flip methods
- ADR-030 (LLM-as-judge); PLAN-012 Phase 4 D2 (flip criterion)
