"""Mutation S1-02: window size change.

The sliding-window pruner is neutralised — stale failures (older than
``window_s``) remain in the deque. The S1 conformance test requires
that the breaker opens on ``threshold`` failures WITHIN the window. The
test drives enough failures straddling the window boundary that the
real impl should NOT open (old entries pruned), but this mutation keeps
them → breaker opens anyway → conformance test must flag it.
"""

from __future__ import annotations

PROPERTY = "S1"
DESCRIPTION = (
    "window pruner neutralised: `_prune_window_locked` becomes a no-op, so "
    "stale failures older than `window_s` still count toward threshold."
)


def apply(cb_cls: type) -> type:
    """Return a CircuitBreaker subclass with S1-02 applied."""

    class Mutant(cb_cls):  # type: ignore[misc,valid-type]
        def _prune_window_locked(self, now: float) -> None:  # noqa: ARG002
            # MUTATION: window prune disabled. Real impl pops stale entries.
            return

    Mutant.__name__ = "CircuitBreakerMut_S1_02"
    return Mutant
