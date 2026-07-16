---
name: ml-evaluation-patterns
description: >
  Evaluation and data-split hygiene for ML systems: train/validation/test
  discipline, temporal and grouped splits, the leakage taxonomy (target,
  feature, preprocessing, and split leakage) with concrete checks for each,
  metric selection matched to task and class balance, trivial baselines
  before models, seeded reproducible evaluation harnesses, and statistical
  treatment of model deltas (multi-seed runs, mean and spread, significance
  before celebration). Front-loads the evaluation-invalidating
  anti-patterns: fitting preprocessing on the full dataset before the
  split, random splits on temporal or grouped data, consulting the test
  set for early stopping or model selection, single-seed comparisons, and
  switching metrics mid-experiment. Use when designing an evaluation,
  reviewing a model comparison, gating a model promotion, or auditing a
  suspicious "state of the art" result.
version: 1.0.0
metadata:
  activation_triggers:
    - "train_test_split|KFold|GroupKFold|TimeSeriesSplit"
    - "leakage|data leak"
    - "validation set|test set|holdout"
    - "roc_auc|pr_auc|f1|precision|recall|rmse|mae"
    - "baseline|ablation"
    - "cross[- ]?validation"
    - "early stopping|model selection"
  paths:
    - "**/*.py"
    - "**/*.ipynb"
  risk_class: low
  domain: data-ml
---

# ML Evaluation Patterns

Evaluation that can survive an audit. The through-line: the split is
decided by the data's structure (time, groups), preprocessing is fit
inside the training fold only, the metric is fixed before the sweep,
and every claimed improvement carries multi-seed evidence against a
trivial baseline. Leakage doesn't make the model better — it makes the
test set lie.

## When to Activate

- Designing the split and metric for a new modeling task.
- Reviewing a model comparison or a promotion request.
- Auditing a result that looks too good (sudden large lift, perfect
  scores, metrics that beat the label noise floor).
- Building an evaluation harness that will gate deployments.
- Deciding whether a retrained model actually improved.

## Split Discipline

### The split follows the data's structure

Random splits are only valid for i.i.d. rows. Two structures break that
assumption constantly:

- **Time.** If examples have a time axis and the model will predict the
  future, evaluate it on the future: train on `≤ M`, validate on
  `M+1`, test on `M+2`. A random shuffle leaks future distribution
  shifts (and often future feature values) into training.
- **Groups.** If one entity (customer, patient, device) yields many
  rows, keep every row of an entity in one split. Otherwise the model
  memorizes entities, not patterns.

```python
from sklearn.model_selection import GroupKFold, TimeSeriesSplit

# Grouped: no customer appears in both train and validation
gkf = GroupKFold(n_splits=5)
for train_idx, val_idx in gkf.split(X, y, groups=customer_ids):
    ...

# Temporal: each fold validates strictly after its training window
tss = TimeSeriesSplit(n_splits=5)
for train_idx, val_idx in tss.split(X_time_ordered):
    ...
```

### Three sets, three jobs

- **Train** fits parameters.
- **Validation** steers every decision: early stopping, hyperparameter
  search, model selection, threshold tuning.
- **Test** is consulted once, at the end, to report the final number.

A test set that influenced any decision has become a second validation
set; its estimate is optimistically biased and the honest fix is a new
holdout window.

## Leakage Taxonomy

Four distinct failure modes; check each explicitly.

1. **Target leakage** — a feature encodes the label (e.g.
   `account_closed_date` as a churn feature). Check: for each feature,
   ask "is this knowable strictly before the prediction moment?"
2. **Feature leakage** — features computed over a window that overlaps
   the label period (a 30-day activity window that ends after the
   churn date). Check: assert `feature_window_end < label_date` per
   example.
3. **Preprocessing leakage** — scalers, vocabularies, target encoders,
   imputers fit on the full dataset before splitting. Check: the fit
   call sits inside the fold, or in a `Pipeline` that is fit per fold.
4. **Split leakage** — duplicates or grouped entities spanning splits.
   Check: hash-join train×test on the entity key; the intersection
   must be empty.

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Right: the scaler is fit on each training fold only, inside cross_val
pipe = Pipeline([("scale", StandardScaler()), ("clf", model)])
scores = cross_val_score(pipe, X, y, cv=gkf.split(X, y, groups=customer_ids))

# Wrong: statistics of val/test rows leak into the scaler
X_scaled = StandardScaler().fit_transform(X)   # fit on EVERYTHING
X_train, X_val = train_test_split(X_scaled)
```

## Metrics and Baselines

### Pick the metric before the sweep

The metric is part of the experimental design, not a reporting choice.
Match it to the task and the class balance:

| Task shape | Report | Avoid |
|---|---|---|
| Imbalanced binary (fraud, churn) | PR-AUC, recall@precision=k | Accuracy, bare ROC-AUC alone |
| Balanced multi-class | Macro-F1 + confusion matrix | Micro-averaged accuracy alone |
| Regression | MAE/RMSE + residual plot by segment | R² alone |
| Ranking | NDCG@k / MRR at the serving cutoff | Full-list AUC |

Switching metrics after seeing results requires re-running every
baseline under the new metric — otherwise the comparison is void.

### Baselines are mandatory

Every evaluation report includes the trivial floor and the incumbent:
majority class / mean predictor, a simple linear model, and the current
production model. A deep model that cannot beat logistic regression has
not earned its serving cost.

## Seeded, Reproducible Harness

An evaluation you cannot re-run is an anecdote. The harness pins the
(code SHA, data snapshot ID, seed) triple and seeds every RNG.

```python
import random
from typing import Dict, List

import numpy as np

def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    # plus torch.manual_seed / torch.cuda.manual_seed_all when torch is in play

def evaluate_over_seeds(build_and_eval, seeds: List[int]) -> Dict[str, float]:
    """Run the full train+eval once per seed; report mean and spread."""
    scores = []
    for seed in seeds:
        set_seed(seed)
        scores.append(build_and_eval(seed))
    arr = np.asarray(scores)
    return {"mean": float(arr.mean()), "std": float(arr.std(ddof=1)), "n": float(len(arr))}
```

### Model deltas need spread, not a point

Train ≥3 seeds per variant and compare distributions. If the candidate's
mean lift is smaller than the run-to-run spread, the "improvement" is
noise. For promotion gates, a practical rule: the candidate's worst
seed should beat the incumbent's best seed on the fixed metric, or the
delta gets a formal significance treatment before anyone celebrates.

## Quick Reference

| Idiom | Purpose |
|---|---|
| `TimeSeriesSplit` / temporal holdout | Evaluate the future on the future |
| `GroupKFold(groups=entity_id)` | Keep each entity in one split |
| `Pipeline(fit inside fold)` | Kill preprocessing leakage structurally |
| `feature_window_end < label_date` | Falsifiable feature-leakage check |
| Metric fixed before the sweep | Comparison stays valid |
| Majority/mean + linear + incumbent | The mandatory baseline table |
| ≥3 seeds, mean ± std | Deltas are distributions, not points |
| (code SHA, data snapshot, seed) | Re-runnable evidence triple |

## Anti-Patterns

```python
# 1) Preprocessing fit on the full dataset — leakage by construction
scaler = StandardScaler().fit(X)               # sees val/test statistics
X_train, X_test = train_test_split(scaler.transform(X))
# Right: split first; fit on train only (or Pipeline inside the fold)

# 2) Random split on temporal data — trains on the future
X_train, X_test = train_test_split(clicks_2025, shuffle=True)
# Right: train <= June, validate July, test August

# 3) Test set steering early stopping — test is now a validation set
if test_auc > best_test_auc:                   # WRONG set
    save_checkpoint(model)
# Right: early-stop on validation; touch test once, at the end

# 4) Single-seed victory lap
# "v4 (seed 42): 0.843 vs v3: 0.840  ->  ship it"
# Right: 3+ seeds each; compare mean +/- std before claiming a win

# 5) Metric switched after the results came in
# "Accuracy looked bad, but hey, ROC-AUC is up!"
# Right: the metric was fixed before the sweep; changing it re-runs everything
```

When a result looks too good, assume leakage before genius: re-derive
the split, re-check every feature's timestamp, and re-fit the
preprocessing inside the fold. The bug is usually in the first ten
lines of the data prep.

## Changelog

- 1.0.0 — Initial clean-room authoring. Covers split discipline
  (temporal, grouped, three-set roles), the four-way leakage taxonomy
  with a falsifiable check per class, metric selection matched to task
  and class balance, mandatory baseline tables, the seeded multi-seed
  evaluation harness with the (code SHA, data snapshot, seed) evidence
  triple, and the five evaluation-invalidating anti-patterns. Snippets
  are Python 3.9-compatible (`typing.Dict`/`List`).
