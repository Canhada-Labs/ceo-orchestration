"""PLAN-088 W1.3 / W6.1 — estimation calibrator package.

`pipeline.py`: top-level orchestrator consuming audit-log emit stream
+ writing Bayesian-refined posterior into calibration-baseline.yaml.

`bayesian.py`: beta-distribution posterior update math (stdlib only;
math.lgamma for log-likelihood).

Both modules are STDLIB-ONLY per CLAUDE.md section 5.
"""

__all__ = ["pipeline", "bayesian"]
