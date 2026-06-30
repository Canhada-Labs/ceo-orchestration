"""PLAN-014 Phase A.6 mutation matrix — policy-as-code engine + policies.

Mutation files are declarative: each exposes a top-level ``MUTATION`` dict
describing the intentional bug and a ``TARGETS`` list of pytest node IDs
(for engine mutations) or a ``POLICY_YAML`` string (for policy mutations)
that the harness in ``test_policy_mutations.py`` uses to verify the
existing test corpus kills the mutation.

Kill-rate gate: ``test_policy_mutations.py::TestMutationKillRateGate``
asserts **100 %** across all mutations. A single surviving mutation
fails the gate and lists the unkilled targets.

See :mod:`.claude/hooks/tests/mutations/README` for the full table.
"""
