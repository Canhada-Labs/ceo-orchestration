"""PLAN-087 D.3 — stdlib-only property-style canary for chain_length monotonicity.

Per cross-plan handoff §11.1 + R1 fold M-1 / M-8 (code-reviewer +
qa-architect must-fix convergent), the framework's testing discipline
is STDLIB-ONLY. The `hypothesis` library is REJECTED framework-wide;
no `from hypothesis import` line may appear anywhere in the codebase.

This canary is the foundational "1 property-style test" entry that
unblocks the prior "0 property-style tests" claim. The methodology:

- ``random.seed(42)`` for deterministic reproducibility (no flake
  surface across CI runs).
- N=200 iterations on the property under test.
- Asserts ``write_chain_length(n)`` followed by
  ``read_chain_length() == n`` for monotonically non-decreasing ``n``
  drawn from a small randomized walk.

**Trade-off documented per M-1 R1 fold:** stdlib determinism via fixed
seed loses (a) automated shrinking on failure — when this canary fails,
the operator must inspect the sequence manually rather than receiving
a minimized counter-example; (b) coverage-guided input generation —
the random walk is uniform, not directed by branch coverage. ACCEPTABLE
here because the property's failure surface is small (monotonic
counter on a single integer state), and N=200 fixed-seed amply
exercises it. NO ADR exception or framework-wide dependency added.

Future tests reaching for property-style coverage follow the same
``random.seed`` + bounded-loop pattern. If a future audit surfaces a
property with a wider failure surface, the team may revisit the
stdlib-only constraint via an ADR debate — but the default is
stdlib-only forever.

Source finding: F-A-QA-T-0011 (P2, Codex DEBATE). Closes the
"0 property-style tests" baseline claim.
"""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

_HOOKS = Path(__file__).resolve().parent.parent
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib.testing import TestEnvContext  # noqa: E402
from _lib import audit_hmac  # noqa: E402


class ChainLengthMonotonicityProperty(TestEnvContext):
    """Property-style canary: chain_length write/read round-trips and
    refuses regression on the persisted counter.

    PLAN-087 D.3 — stdlib-only, N=200, ``random.seed(42)`` deterministic.
    """

    # PLAN-087 handoff §11.1 contract: stdlib-only, fixed seed, bounded loop.
    SEED = 42
    ITERATIONS = 200

    def test_monotone_writes_round_trip(self) -> None:
        """N=200 random-walk monotone counter writes survive a read_chain_length.

        Invariant under test: for any monotone non-decreasing sequence
        ``n_0 <= n_1 <= ... <= n_k``, ``write_chain_length(n_i)`` followed
        by ``read_chain_length()`` returns exactly ``n_i``. Idempotent
        writes (``n_i == n_{i-1}``) preserve the counter.

        Negative deltas (regressions) are NOT exercised here — those are
        caller-side discipline (audit_emit increments via
        ``read_chain_length() + 1`` per the docstring contract). The
        canary specifically pins the write/read round-trip + monotone
        progression.
        """
        rng = random.Random(self.SEED)

        # Genesis: counter absent → read returns 0.
        self.assertEqual(audit_hmac.read_chain_length(), 0)

        current = 0
        for i in range(self.ITERATIONS):
            # Monotone non-decreasing delta in [0, 5]. Mixes idempotent
            # writes (delta=0) with strict increases.
            delta = rng.randint(0, 5)
            current += delta
            audit_hmac.write_chain_length(current)
            observed = audit_hmac.read_chain_length()
            self.assertEqual(
                observed,
                current,
                "round-trip failed at iteration {i}: wrote {w}, read {r}".format(
                    i=i, w=current, r=observed
                ),
            )

    def test_negative_value_rejected(self) -> None:
        """write_chain_length refuses negative inputs (caller-side bug guard).

        Complements the round-trip property by pinning the only documented
        rejection path. Stdlib-only; not a property loop but a single-case
        assertion needed to round out the canary suite.
        """
        with self.assertRaises(audit_hmac.AuditHmacError):
            audit_hmac.write_chain_length(-1)


class ChainLengthZeroBoundsProperty(TestEnvContext):
    """Boundary-property canary: explicit zero/genesis handling.

    PLAN-087 D.3 — second canary covering the genesis boundary which
    the main monotonicity loop covers only implicitly at i=0.
    """

    def test_genesis_then_explicit_zero_write_idempotent(self) -> None:
        """An explicit write_chain_length(0) is idempotent with the genesis.

        Genesis (file absent) and explicit-zero-write produce the same
        observable state from read_chain_length(). Validates the
        fail-open semantics documented in audit_hmac.read_chain_length.
        """
        # Genesis observable
        self.assertEqual(audit_hmac.read_chain_length(), 0)

        # Explicit zero write
        audit_hmac.write_chain_length(0)
        self.assertEqual(audit_hmac.read_chain_length(), 0)

        # Round-trip with idempotent re-write
        audit_hmac.write_chain_length(0)
        self.assertEqual(audit_hmac.read_chain_length(), 0)


if __name__ == "__main__":
    unittest.main()
