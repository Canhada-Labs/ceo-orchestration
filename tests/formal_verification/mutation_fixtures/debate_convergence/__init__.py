"""Debate-convergence mutation set — 13 mutations (S1=3, S2=3, S3=2, S4=2, Auth=3).

Each mutation module exposes:

- ``PROPERTY``: one of ``"S1" | "S2" | "S3" | "S4" | "Auth"``.
- ``DESCRIPTION``: plain-English summary.
- ``apply(...)`` or ``apply_fn(...)``: takes the unmutated function/config
  and returns a mutated version. The conformance test runs its core
  assertion; MUST fail on every mutation.
"""

from __future__ import annotations
