"""PLAN-013 Phase D.8 — Property-based conformance tests for formal verification.

Every formally-proved property (`docs/formal-verification/properties-proved.md`)
maps to an executable property-based test in this package. Each test is
paired with >=5 mutations under `mutation_fixtures/<target>/` that MUST
cause the test to fail when applied. This closes the model-drift gap
per PLAN-013 debate round 1 consensus §C8 CRITICAL.

``mutation_fixtures/`` was renamed from ``mutations/`` in PLAN-019
Phase 1 (P0-04) to avoid a top-level package name collision with
``.claude/hooks/tests/mutations/`` under pytest whole-tree collection.
"""

from __future__ import annotations
