---
name: ml-serving-patterns
description: >
  From checkpoint to production inference: safe model export and loading
  (state_dict with weights_only, safetensors for distribution,
  TorchScript/ONNX trade-offs), eval-mode and no-grad inference
  discipline, training-serving preprocessing parity via a shared
  transform module plus golden-batch tests, inference-server shape
  (health/readiness, versioned model registry, warmup), dynamic batching
  under an explicit latency budget, GPU memory measured at peak load
  before rollout, staged rollout (shadow, canary, full) with a pinned
  warm rollback, and drift plus quality monitoring wired as part of the
  deployment. Front-loads the production-breaking anti-patterns:
  pickle-loading untrusted checkpoints, reimplemented preprocessing skew,
  dropout left on in production, and rollouts whose only rollback plan is
  "redeploy the old container". Use when exporting, serving, deploying,
  rolling back, or monitoring a model in production.
version: 1.0.0
metadata:
  activation_triggers:
    - "torchscript|onnx|safetensors"
    - "weights_only"
    - "inference|model server|serving"
    - "model registry|rollout|canary|shadow deploy"
    - "drift|monitoring"
    - "dynamic batching|batch(ing)? latency"
    - "rollback"
  paths:
    - "**/*.py"
    - "**/Dockerfile"
  risk_class: low
  domain: data-ml
---

# ML Serving Patterns

Everything between "the checkpoint is done" and "the model is safely
taking traffic". The through-line: treat every checkpoint as untrusted
input, make serving import the training-time transforms instead of
reimplementing them, measure GPU memory at peak before launch, and
never roll forward without a pinned, warm way back.

## When to Activate

- Exporting a trained model for deployment or distribution.
- Building or reviewing an inference service or batch scorer.
- Planning a model rollout, canary, or rollback.
- Debugging training-serving skew ("offline says 0.84, prod behaves
  like 0.60").
- Wiring drift and quality monitoring for a live model.

## Export and Safe Loading

### Checkpoints are untrusted input

Legacy `torch.load` unpickles arbitrary objects: a malicious checkpoint
is remote code execution on your serving host. Two rules cover it:

```python
# Loading anything you did not produce in this pipeline:
state = torch.load(path, map_location="cpu", weights_only=True)

# Distribution format of choice — no pickle at all:
from safetensors.torch import load_file, save_file
save_file(model.state_dict(), "model.safetensors")
state = load_file("model.safetensors")
```

Save `state_dict()`, never the whole module object — pickling the full
`nn.Module` binds the artifact to your exact class layout and breaks on
the first refactor.

### Export format trade-offs

| Format | Use when | Watch out |
|---|---|---|
| `state_dict` + model code | Same-codebase serving | Needs the Python class importable |
| safetensors | Distribution, registries | Weights only — pair with versioned code |
| TorchScript | Python-free runtimes, mobile | Tracing bakes in control flow for the traced shapes |
| ONNX | Cross-runtime (Triton, TensorRT) | Verify per-op parity on a golden batch after export |

Whatever the format: run a golden-batch check (fixed inputs, saved
expected outputs, tight tolerance) as part of export, so a broken
conversion fails in CI instead of in traffic.

## Inference Discipline

`model.eval()` and `torch.no_grad()` do different jobs and you need
both. Missing `eval()` leaves dropout firing and BatchNorm drifting in
production — predictions are silently wrong, and no exception will ever
tell you.

```python
class Predictor:
    def __init__(self, model: torch.nn.Module) -> None:
        self.model = model.eval()          # once, at load time

    @torch.no_grad()
    def __call__(self, batch: torch.Tensor) -> torch.Tensor:
        return self.model(batch)
```

Load the model once at process start (never per request), warm it with
a synthetic batch before reporting ready, and expose the model version
in both the readiness endpoint and every prediction log line — triage
is impossible when you cannot say which model answered.

## Training-Serving Parity

The most common production quality bug is not the model — it is the
features. If serving reimplements preprocessing, the two copies drift.

- **Structural fix:** serving imports the same transform module the
  training pipeline used. One implementation, two callers.
- **When import is impossible** (different language/runtime): a parity
  test is mandatory — run a golden batch through both pipelines and
  compare outputs within tolerance, in CI.

```python
def test_transform_parity(golden_rows, training_transform, serving_transform):
    expected = training_transform(golden_rows)
    actual = serving_transform(golden_rows)
    assert np.max(np.abs(expected - actual)) < 1e-6
```

## Capacity: GPU Memory Under Load

Measure before rollout, at the worst case the API contract allows:
maximum batch size × maximum input length. An OOM that only appears at
p99 traffic is a launch blocker, not a follow-up ticket.

```python
torch.cuda.reset_peak_memory_stats()
_ = predictor(worst_case_batch)            # max batch x max seq length
peak = torch.cuda.max_memory_allocated() / 2**30
assert peak < CARD_MEMORY_GB * 0.8         # keep documented headroom
```

Dynamic batching trades latency for throughput — cap the queue wait so
the p99 latency budget holds, and document both numbers next to the
deployment config.

## Rollout and Rollback

Version every artifact (model + transform code + config) in a registry;
"latest" is not a version. The rollout ladder:

1. **Shadow** — the candidate scores live traffic, logs predictions,
   serves nothing. Compare shadow scores against the incumbent and
   against offline expectations.
2. **Canary** — a small traffic slice. Promote only when canary
   metrics match the offline evaluation within a documented tolerance.
3. **Full** — with the previous version still pinned warm.

The rollback is part of the deployment definition: the previous model
version stays pinned in the registry, loaded warm (or provably fast to
load), and the flip is drilled before launch. "Redeploy the old
container" is a plan only if the old model version is pinned and the
drill has been run.

## Monitoring Is Part of the Deployment

A model without monitors is an outage with a delay on it. Minimum set,
wired before full traffic:

- **Input drift** — distribution monitors on the top features (PSI /
  KS against a training-window reference).
- **Prediction drift** — score-histogram monitor; a sudden shift is
  the earliest signal you get.
- **Delayed-label quality** — the real metric, computed as labels
  mature, broken down by segment (aggregates hide cohort collapse).
- **Data quality upstream** — NaN/volume alerts on inputs, so triage
  can tell "pipeline broke" from "world changed".

Alert thresholds and the retraining trigger live in the runbook, next
to the rollback procedure.

## Quick Reference

| Idiom | Purpose |
|---|---|
| `weights_only=True` / safetensors | Checkpoints are untrusted input |
| `state_dict()`, never the module | Artifacts survive refactors |
| Golden-batch check at export | Conversion bugs fail in CI, not traffic |
| `model.eval()` + `@torch.no_grad()` | Correct and cheap inference |
| Shared transform module (+ parity test) | Kill training-serving skew |
| Peak-memory probe at worst case | No p99 OOM surprises |
| Shadow → canary → full | Quality evidence before traffic |
| Pinned warm previous version | Rollback is a flip, not a rebuild |
| Drift + delayed-label monitors | Regressions page you, not users |

## Anti-Patterns

```python
# 1) Pickle-loading a bucket-sourced checkpoint — RCE surface
model = torch.load("s3_download.pt")            # unpickles arbitrary code
# Right: torch.load(..., weights_only=True) or safetensors

# 2) Preprocessing reimplemented in the server — silent skew
def serve_features(row):                         # hand-ported from training
    return (row - HARDCODED_MEAN) / HARDCODED_STD
# Right: import the training transform module; parity-test if you can't

# 3) Dropout live in production
model = MyModel(); model.load_state_dict(state)  # default mode is train()
# Right: model.eval() at load time + no_grad on the request path

# 4) Rollback theater
# "If v4 misbehaves we redeploy the old image"    # old model not pinned, cold
# Right: previous version pinned in the registry, warm, flip drilled

# 5) Launch first, monitor "next sprint"
# Right: monitors fire on synthetic drift in staging BEFORE full traffic
```

When production quality diverges from offline evaluation, check in this
order: model version actually serving → transform parity on a golden
batch → input drift vs. the training window. The model itself is the
last suspect, not the first.

## Changelog

- 1.0.0 — Initial clean-room authoring. Covers safe export and loading
  (`weights_only`, safetensors, format trade-off table, golden-batch
  export checks), inference discipline (eval + no_grad, warmup,
  version-stamped predictions), training-serving parity (shared
  transform module + parity tests), peak GPU memory probing, the
  shadow/canary/full rollout ladder with pinned warm rollback, the
  minimum monitoring set (input drift, prediction drift, delayed-label
  quality, upstream data quality), and the five production-breaking
  anti-patterns. Carries forward the pickle-RCE/weights_only posture
  from `pytorch-patterns`.
