"""Breaker mutation set — 21 mutations (S1=6, S2=5, S3=5, L1=5).

Each mutation module is self-contained and exposes:

- ``PROPERTY``: one of ``"S1" | "S2" | "S3" | "L1"``.
- ``DESCRIPTION``: plain-English summary of what the mutation changes.
- ``apply(cb_cls)``: takes the unmutated ``CircuitBreaker`` class (and/or
  the emit_breaker_opened helper exposed via the test harness) and
  returns a *new* mutated subclass with one bug injected. The
  conformance test runs its core assertion against the returned class;
  the assertion MUST fail (raise ``AssertionError``) for the mutation
  to count as killed.

The apply-a-subclass pattern is simpler + more robust than string/AST
source patching: each mutation is readable Python, the diff is one
method-override, and running the test harness needs no separate
temp-source loader. All mutations are deterministic, stdlib-only.

See ``mutation_fixtures/README.md`` for how to add a new mutation.
"""

from __future__ import annotations
