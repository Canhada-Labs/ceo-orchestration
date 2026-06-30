"""Engine mutations — intentional bugs injected into ``_lib.policy``.

Each file exposes:

- ``MUTATION``  (dict) — human-readable description + function target.
- ``TARGETS``   (list[str]) — pytest node IDs (relative to
  ``.claude/hooks/tests/test_policy_engine.py``) that MUST fail when
  the mutation is applied in-memory.
- ``apply(module)`` — monkeypatch the ``_lib.policy`` module with the
  mutated behaviour; returns a list of (attribute_name, original_value)
  tuples so the harness can restore state.

Coverage floor per PLAN-014 §A.6 ADJ-012:
 ≥6 parser + ≥6 compiler + ≥8 evaluator + ≥5 error-model = ≥25 total.
"""
