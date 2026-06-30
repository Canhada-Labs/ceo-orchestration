"""Plan-lifecycle mutation set — 11 mutations (S1=3, S2=3, S3=2, Auth=3).

Each mutation module exposes:

- ``PROPERTY``: one of ``"S1" | "S2" | "S3" | "Auth"``.
- ``DESCRIPTION``: plain-English summary.
- ``apply(transitions_dict)``: takes the unmutated ``_ALLOWED_TRANSITIONS``
  dict (or equivalent function) and returns a mutated version that
  introduces one bug. The conformance test runs its core assertion
  against the mutated transitions; the assertion MUST fail.
"""

from __future__ import annotations
