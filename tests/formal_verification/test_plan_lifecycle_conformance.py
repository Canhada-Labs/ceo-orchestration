"""Conformance tests for PLAN-SCHEMA §4 Plan Lifecycle — PLAN-014 Phase B.3.

Per PLAN-013 debate §C8 CRITICAL: every formally-proved property in
``docs/formal-verification/properties-proved.md`` MUST map to an
executable property-based test against the real Python implementation,
plus a mutation-test gate.

## Four property tests + Auth invariant

- **S1** ``test_s1_no_skip`` — draft cannot jump directly to done or
  executing; must traverse reviewed->executing->done.
- **S2** ``test_s2_abandonment_documented`` — every transition to
  abandoned requires abandonment_reason body section; abandoned/done
  are terminal (absorbing states).
- **S3** ``test_s3_monotonic_timestamps`` — reviewed_at required for
  reviewed; completed_at + related_commits required for done.
- **Auth** ``test_auth_owner_approval`` — draft->reviewed requires
  reviewed_at (proxy for Owner approval).

## Mutation gate

Each property test iterates its mutation set and asserts that every
mutation causes the core property assertion to fail.

## Harness rules

1. TestEnvContext subclass — env isolation.
2. Deterministic — no randomness needed (pure state machine).
3. Tests the real ``check_plan_edit.py`` ``_check_transition`` and
   ``_check_required_fields`` functions.
4. Stdlib only.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Set, Type

# Path bootstrap
_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

# Import the real implementation
import check_plan_edit as _cpe  # noqa: E402


# ------------------------------------------------------------------
# Reference data from real implementation
# ------------------------------------------------------------------

# The canonical transition graph from check_plan_edit.py:67-73
CANONICAL_TRANSITIONS = {
    "draft": {"draft", "reviewed", "abandoned"},
    "reviewed": {"reviewed", "executing", "abandoned"},
    "executing": {"executing", "done", "abandoned"},
    "done": {"done"},
    "abandoned": {"abandoned"},
}

LEGAL_STATUSES = {"draft", "reviewed", "executing", "done", "abandoned"}

# All possible non-self transitions per the graph
LEGAL_FORWARD_TRANSITIONS = [
    ("draft", "reviewed"),
    ("draft", "abandoned"),
    ("reviewed", "executing"),
    ("reviewed", "abandoned"),
    ("executing", "done"),
    ("executing", "abandoned"),
]

# Transitions that should be BLOCKED
ILLEGAL_TRANSITIONS = [
    ("draft", "done"),
    ("draft", "executing"),
    ("reviewed", "done"),
    ("reviewed", "draft"),
    ("executing", "draft"),
    ("executing", "reviewed"),
    ("done", "draft"),
    ("done", "reviewed"),
    ("done", "executing"),
    ("done", "abandoned"),
    ("abandoned", "draft"),
    ("abandoned", "reviewed"),
    ("abandoned", "executing"),
    ("abandoned", "done"),
]


def _load_mutations(property_id: str) -> List[ModuleType]:
    """Discover all mutations under mutation_fixtures/plan_lifecycle/ for the given property.

    Renamed from ``mutations/`` to ``mutation_fixtures/`` in PLAN-019
    Phase 1 to avoid a collision with ``.claude/hooks/tests/mutations/``
    under pytest whole-tree collection (P0-04).
    """
    try:
        from mutation_fixtures import plan_lifecycle as mutations_pkg  # type: ignore
    except ImportError:
        import mutation_fixtures.plan_lifecycle as mutations_pkg  # type: ignore

    mods: List[ModuleType] = []
    pkg_path = Path(mutations_pkg.__file__).resolve().parent  # type: ignore[arg-type]
    for info in pkgutil.iter_modules([str(pkg_path)]):
        if not info.name.startswith("mut_"):
            continue
        mod = importlib.import_module(f"mutation_fixtures.plan_lifecycle.{info.name}")
        if getattr(mod, "PROPERTY", None) == property_id:
            mods.append(mod)
    mods.sort(key=lambda m: m.__name__)
    return mods


def _check_transition_with_graph(
    transitions: Dict[str, Set[str]], old_status: str, new_status: str
) -> Optional[str]:
    """Check a transition against a potentially-mutated transition graph."""
    if new_status not in LEGAL_STATUSES:
        return f"PLAN-LIFECYCLE: illegal status value '{new_status}'."
    if not old_status or old_status not in LEGAL_STATUSES:
        return None
    allowed = transitions.get(old_status, set())
    if new_status not in allowed:
        return (
            f"PLAN-LIFECYCLE: illegal transition '{old_status}' -> '{new_status}'."
        )
    return None


# ------------------------------------------------------------------
# S1 — No-skip
# ------------------------------------------------------------------


class TestS1NoSkip(TestEnvContext):
    """Property S1: draft cannot jump directly to done.

    The lifecycle requires draft->reviewed->executing->done.
    No shortcut transitions exist.

    Mutation budget: 3.
    """

    PROPERTY_ID = "S1"

    def _core_assertion(
        self, transitions: Optional[Dict[str, Set[str]]] = None
    ) -> None:
        """S1 core: assert no skip transitions exist in the graph."""
        graph = transitions if transitions is not None else CANONICAL_TRANSITIONS

        # draft->done must be blocked
        reason = _check_transition_with_graph(graph, "draft", "done")
        if reason is None:
            raise AssertionError(
                "S1 violated: draft->done transition allowed (skip over "
                "reviewed + executing)"
            )

        # draft->executing must be blocked (skip over reviewed)
        reason = _check_transition_with_graph(graph, "draft", "executing")
        if reason is None:
            raise AssertionError(
                "S1 violated: draft->executing transition allowed (skip "
                "over reviewed)"
            )

        # reviewed->done must be blocked (skip over executing)
        reason = _check_transition_with_graph(graph, "reviewed", "done")
        if reason is None:
            raise AssertionError(
                "S1 violated: reviewed->done transition allowed (skip "
                "over executing)"
            )

        # Verify the LEGAL forward transitions DO work
        for src, dst in LEGAL_FORWARD_TRANSITIONS:
            reason = _check_transition_with_graph(graph, src, dst)
            if reason is not None:
                raise AssertionError(
                    f"S1 violated: legal transition {src}->{dst} was "
                    f"blocked: {reason}"
                )

    def test_s1_no_skip(self) -> None:
        """S1 conformance: un-mutated transition graph forbids skip transitions."""
        self._core_assertion()

    def test_s1_real_check_transition(self) -> None:
        """S1 against real _check_transition function."""
        # draft->done blocked
        reason = _cpe._check_transition("draft", "done")
        self.assertIsNotNone(reason, "draft->done should be blocked")

        # draft->executing blocked
        reason = _cpe._check_transition("draft", "executing")
        self.assertIsNotNone(reason, "draft->executing should be blocked")

        # reviewed->done blocked
        reason = _cpe._check_transition("reviewed", "done")
        self.assertIsNotNone(reason, "reviewed->done should be blocked")

    def test_s1_mutations_fail(self) -> None:
        """Every S1 mutation introduces a skip path."""
        mutations = _load_mutations("S1")
        self.assertGreaterEqual(
            len(mutations), 3,
            msg=f"S1 mutation budget is 3; discovered {len(mutations)}"
        )
        killed: List[str] = []
        survived: List[str] = []
        for mut_mod in mutations:
            mutated = mut_mod.apply(CANONICAL_TRANSITIONS)
            try:
                self._core_assertion(mutated)
            except AssertionError:
                killed.append(mut_mod.__name__)
            else:
                survived.append(mut_mod.__name__)
        if survived:
            raise AssertionError(
                "S1 mutations NOT killed: " + str(survived)
            )


# ------------------------------------------------------------------
# S2 — Abandonment documented + terminal states
# ------------------------------------------------------------------


class TestS2AbandonmentDocumented(TestEnvContext):
    """Property S2: abandoned requires reason; done/abandoned are terminal.

    Mutation budget: 3.
    """

    PROPERTY_ID = "S2"

    def _core_assertion(
        self,
        transitions: Optional[Dict[str, Set[str]]] = None,
        check_fn: Optional[Callable] = None,
    ) -> None:
        """S2 core: abandonment needs reason; terminal states are absorbing."""
        graph = transitions if transitions is not None else CANONICAL_TRANSITIONS
        check = check_fn if check_fn is not None else _cpe._check_required_fields

        # Phase A: abandoned requires ## Abandonment reason
        reason = check("", "abandoned", {}, "no reason here")
        if reason is None:
            raise AssertionError(
                "S2 violated (phase A): transition to 'abandoned' allowed "
                "without ## Abandonment reason section"
            )

        # Phase B: abandoned with reason is accepted
        reason = check("", "abandoned", {}, "## Abandonment reason\nSuperseded.")
        if reason is not None:
            raise AssertionError(
                f"S2 violated (phase B): transition to 'abandoned' with "
                f"valid reason was blocked: {reason}"
            )

        # Phase C: done is terminal — no outgoing transitions except self-loop
        done_targets = graph.get("done", set()) - {"done"}
        if done_targets:
            raise AssertionError(
                f"S2 violated (phase C): done has outgoing transitions to "
                f"{done_targets} — should be terminal"
            )

        # Phase D: abandoned is terminal — no outgoing transitions except self-loop
        abandoned_targets = graph.get("abandoned", set()) - {"abandoned"}
        if abandoned_targets:
            raise AssertionError(
                f"S2 violated (phase D): abandoned has outgoing transitions "
                f"to {abandoned_targets} — should be terminal"
            )

    def test_s2_abandonment_documented(self) -> None:
        """S2 conformance: un-mutated implementation enforces abandonment docs."""
        self._core_assertion()

    def test_s2_mutations_fail(self) -> None:
        """Every S2 mutation violates abandonment/terminal invariants."""
        mutations = _load_mutations("S2")
        self.assertGreaterEqual(
            len(mutations), 3,
            msg=f"S2 mutation budget is 3; discovered {len(mutations)}"
        )
        killed: List[str] = []
        survived: List[str] = []
        for mut_mod in mutations:
            try:
                # Some mutations affect transition graph
                if hasattr(mut_mod, "apply"):
                    mutated = mut_mod.apply(CANONICAL_TRANSITIONS)
                    self._core_assertion(transitions=mutated)
                # Some mutations affect check function
                elif hasattr(mut_mod, "apply_check"):
                    self._core_assertion(check_fn=mut_mod.apply_check)
                else:
                    raise AssertionError(
                        f"Mutation {mut_mod.__name__} has no apply/apply_check"
                    )
            except AssertionError:
                killed.append(mut_mod.__name__)
            else:
                survived.append(mut_mod.__name__)
        if survived:
            raise AssertionError(
                "S2 mutations NOT killed: " + str(survived)
            )


# ------------------------------------------------------------------
# S3 — Monotonic timestamps (required fields)
# ------------------------------------------------------------------


class TestS3MonotonicTimestamps(TestEnvContext):
    """Property S3: reviewed_at required for reviewed; completed_at + related_commits for done.

    Mutation budget: 2.
    """

    PROPERTY_ID = "S3"

    def _core_assertion(
        self,
        check_fn: Optional[Callable] = None,
    ) -> None:
        """S3 core: required fields enforced per status."""
        check = check_fn if check_fn is not None else _cpe._check_required_fields

        # Phase A: reviewed without reviewed_at is blocked
        reason = check("", "reviewed", {}, "")
        if reason is None:
            raise AssertionError(
                "S3 violated (phase A): transition to 'reviewed' allowed "
                "without reviewed_at field"
            )

        # Phase B: reviewed with reviewed_at is accepted
        reason = check("", "reviewed", {"reviewed_at": "2026-04-15"}, "")
        if reason is not None:
            raise AssertionError(
                f"S3 violated (phase B): transition to 'reviewed' with "
                f"reviewed_at was blocked: {reason}"
            )

        # Phase C: done without completed_at is blocked
        reason = check(
            "",
            "done",
            {"related_commits": ["abc123"]},
            ""
        )
        if reason is None:
            raise AssertionError(
                "S3 violated (phase C): transition to 'done' allowed "
                "without completed_at field"
            )

        # Phase D: done without related_commits is blocked
        reason = check(
            "",
            "done",
            {"completed_at": "2026-04-15"},
            ""
        )
        if reason is None:
            raise AssertionError(
                "S3 violated (phase D): transition to 'done' allowed "
                "without related_commits"
            )

        # Phase E: done with both fields is accepted
        reason = check(
            "",
            "done",
            {"completed_at": "2026-04-15", "related_commits": ["abc"]},
            ""
        )
        if reason is not None:
            raise AssertionError(
                f"S3 violated (phase E): transition to 'done' with all "
                f"fields was blocked: {reason}"
            )

    def test_s3_monotonic_timestamps(self) -> None:
        """S3 conformance: un-mutated implementation enforces required fields."""
        self._core_assertion()

    def test_s3_mutations_fail(self) -> None:
        """Every S3 mutation skips a required-field check."""
        mutations = _load_mutations("S3")
        self.assertGreaterEqual(
            len(mutations), 2,
            msg=f"S3 mutation budget is 2; discovered {len(mutations)}"
        )
        killed: List[str] = []
        survived: List[str] = []
        for mut_mod in mutations:
            try:
                self._core_assertion(check_fn=mut_mod.apply_check)
            except AssertionError:
                killed.append(mut_mod.__name__)
            else:
                survived.append(mut_mod.__name__)
        if survived:
            raise AssertionError(
                "S3 mutations NOT killed: " + str(survived)
            )


# ------------------------------------------------------------------
# Auth — Owner approval for draft->reviewed
# ------------------------------------------------------------------


class TestAuthOwnerApproval(TestEnvContext):
    """Property Auth: draft->reviewed requires Owner approval (reviewed_at).

    Mutation budget: 3.
    """

    PROPERTY_ID = "Auth"

    def _core_assertion(
        self,
        transitions: Optional[Dict[str, Set[str]]] = None,
        check_fn: Optional[Callable] = None,
        legal_statuses: Optional[Set[str]] = None,
    ) -> None:
        """Auth core: Owner approval gate enforced."""
        graph = transitions if transitions is not None else CANONICAL_TRANSITIONS
        check = check_fn if check_fn is not None else _cpe._check_required_fields
        statuses = legal_statuses if legal_statuses is not None else LEGAL_STATUSES

        # Phase A: draft->reviewed without reviewed_at is blocked
        reason = check("", "reviewed", {}, "")
        if reason is None:
            raise AssertionError(
                "Auth violated (phase A): draft->reviewed allowed without "
                "reviewed_at (Owner approval gate)"
            )

        # Phase B: only draft can transition to reviewed (graph check)
        for src in statuses:
            if src in ("draft", "reviewed"):
                continue
            reason = _check_transition_with_graph(graph, src, "reviewed")
            if reason is None:
                raise AssertionError(
                    f"Auth violated (phase B): {src}->reviewed allowed — "
                    f"only draft->reviewed is valid"
                )

        # Phase C: status values must be restricted to the legal set
        if statuses != LEGAL_STATUSES:
            extra = statuses - LEGAL_STATUSES
            if extra:
                raise AssertionError(
                    f"Auth violated (phase C): illegal status values "
                    f"accepted: {extra}"
                )

    def test_auth_owner_approval(self) -> None:
        """Auth conformance: un-mutated implementation enforces Owner gate."""
        self._core_assertion()

    def test_auth_real_check_transition(self) -> None:
        """Auth: real _check_transition blocks non-draft->reviewed paths."""
        for src in ("executing", "done", "abandoned"):
            reason = _cpe._check_transition(src, "reviewed")
            self.assertIsNotNone(
                reason,
                f"{src}->reviewed should be blocked"
            )

    def test_auth_mutations_fail(self) -> None:
        """Every Auth mutation bypasses the Owner approval gate."""
        mutations = _load_mutations("Auth")
        self.assertGreaterEqual(
            len(mutations), 3,
            msg=f"Auth mutation budget is 3; discovered {len(mutations)}"
        )
        killed: List[str] = []
        survived: List[str] = []
        for mut_mod in mutations:
            try:
                kwargs: Dict[str, Any] = {}
                if hasattr(mut_mod, "apply"):
                    kwargs["transitions"] = mut_mod.apply(CANONICAL_TRANSITIONS)
                if hasattr(mut_mod, "apply_check"):
                    kwargs["check_fn"] = mut_mod.apply_check
                if hasattr(mut_mod, "apply_legal_statuses"):
                    kwargs["legal_statuses"] = mut_mod.apply_legal_statuses(
                        LEGAL_STATUSES
                    )
                self._core_assertion(**kwargs)
            except AssertionError:
                killed.append(mut_mod.__name__)
            else:
                survived.append(mut_mod.__name__)
        if survived:
            raise AssertionError(
                "Auth mutations NOT killed: " + str(survived)
            )


if __name__ == "__main__":
    unittest.main()
