"""Policy mutations — intentional bugs injected into the two migrated
policy YAMLs (bash-safety + plan-edit).

Each file exposes:

- ``MUTATION`` (dict) — description + target policy.
- ``POLICY_YAML`` (str) — complete mutated YAML document.
- ``FIXTURE_FILE`` (str) — filename under ``.claude/policies/fixtures/``.

The harness loads the mutated YAML via ``_lib.policy.load`` through a
tmpfile, replays every fixture from ``FIXTURE_FILE``, and asserts
≥1 fixture now produces a different ``(decision, reason)`` than the
un-mutated policy.

Coverage floor: ≥8 per policy × 2 policies = ≥16.
"""
