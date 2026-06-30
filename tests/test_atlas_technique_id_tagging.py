"""ATLAS technique-ID tagging tests (PLAN-085 Wave G.1a).

NOTE: G.1a ships docs + fixtures + this test infrastructure. Production
audit_emit.py wiring of `atlas_technique` field is Wave G.1b (DEFERRED
to post-Wave-E serialization tail; PLAN-085 §8 dispatch order
``B.3 -> D.1 -> E.4 -> G.1b``). When G.1b lands, all 15 cases turn
GREEN. Tests EXIST and EXECUTE cleanly now (no Python tracebacks);
assertion-1 failures are EXPECTED.

Contract — 5 ATLAS mappings x 3 assertions = 15 cases:

    1) emit fires on the should-fire fixture: the production emit
       function for the mapping's action carries an `atlas_technique`
       parameter (or equivalent registry hook) that ends up in the
       emitted event. EXPECTED-FAIL until G.1b lands; the failure
       mode is "audit_emit has no `atlas_technique` parameter / does
       not populate the field in the written event".
    2) emit does NOT fire on the should-not-fire fixture (0 matches).
       Fixture-shape assertion; passes on G.1a.
    3) field value matches the immutable v1.19.0 registry. Fixture-
       shape assertion; passes on G.1a.

15 explicit test methods are generated (one per mapping * assertion)
so pytest reports a 1:1 case count consistent with PLAN-085 AC8.
"""

from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Immutable v1.19.0 ATLAS registry — closed enum.
# Source of truth: docs/EXT-011-mitre-atlas.md §2 SHIPPED table.
# G.1b adds these tags to audit_emit.py; until then, assertion-1
# fails by design when the production emit function is invoked.
_ATLAS_REGISTRY: Dict[str, str] = {
    "prompt_injection_detected": "AML.T0051",
    "secret_leak_detected": "AML.T0024.001",
    "pii_redacted_outgoing": "AML.T0048.004",
    "live_adapter_blocked": "AML.T0049",
    "codex_egress_redacted": "AML.T0054",
}


_REPO_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE_DIR = _REPO_ROOT / "tests" / "fixtures" / "atlas"


def _fixture_path(atlas_id: str, polarity: str) -> Path:
    """Return the fixture path for ``atlas_id`` and ``polarity``.

    polarity is "should-fire" or "should-not-fire". The fixture
    filename uses the parent technique ID number (e.g. AML.T0024.001
    -> AML-T0024-*).
    """
    parent_num = atlas_id.split(".")[1][1:]  # "T0024" -> "0024"
    return _FIXTURE_DIR / f"AML-T{parent_num}-{polarity}.ndjson"


def _load_ndjson(path: Path) -> List[Dict[str, object]]:
    """Read a UTF-8 NDJSON file; return list of dict events."""
    events: List[Dict[str, object]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def _emit_atlas_technique(event: Dict[str, object]) -> Optional[str]:
    """Return the ``atlas_technique`` field on an event, if any."""
    value = event.get("atlas_technique")
    if value is None:
        return None
    return str(value)


def _production_emit_supports_atlas(action: str) -> bool:
    """Return True iff the production `audit_emit.py` function for
    ``action`` accepts and writes an `atlas_technique` field.

    This is the Wave G.1b convergence probe. Until G.1b lands, this
    returns False for all 5 mappings and assertion-1 fails-by-design.

    Implementation: best-effort import of `_lib.audit_emit` followed
    by ``inspect.signature`` on the canonical emit function name
    (derived from the action). If the module or function are absent,
    or the parameter is missing, the probe returns False.
    """
    try:
        import inspect

        # Best-effort multi-path import. audit_emit.py lives under
        # `.claude/hooks/_lib/audit_emit.py`; tests pin sys.path via
        # the repo-root conftest.py.
        try:
            audit_emit = importlib.import_module("_lib.audit_emit")
        except ModuleNotFoundError:
            # Fall back: not on sys.path here; G.1a does not require
            # the import to succeed — the probe returning False is
            # the expected G.1a state.
            return False

        # Canonical emit function name = "emit_" + action.
        fn_name = f"emit_{action}"
        fn = getattr(audit_emit, fn_name, None)
        if fn is None:
            return False
        sig = inspect.signature(fn)
        return "atlas_technique" in sig.parameters
    except Exception:  # pragma: no cover — defensive
        return False


def _count_matches_for_action(
    events: List[Dict[str, object]],
    action: str,
    expected_atlas: str,
) -> Tuple[int, int]:
    """Return ``(matches, total_with_action)`` for the given action."""
    total = 0
    matches = 0
    for ev in events:
        if ev.get("action") != action:
            continue
        total += 1
        if _emit_atlas_technique(ev) == expected_atlas:
            matches += 1
    return matches, total


class _AtlasTaggingBase(unittest.TestCase):
    """Common helpers shared across the 15 generated tests."""

    def _skip_if_no_fixture_dir(self) -> None:
        if not _FIXTURE_DIR.is_dir():
            self.skipTest(
                f"ATLAS fixture dir missing: {_FIXTURE_DIR}. "
                "Wave G.1a authors fixtures BEFORE this test runs."
            )

    def assert_fires_on_positive(self, action: str, expected_atlas: str) -> None:
        """Assertion 1 — EXPECTED FAIL until G.1b lands.

        Two-step gate:
          (a) production `emit_<action>` function carries an
              `atlas_technique` parameter (G.1b convergence probe).
              FAILS in G.1a because audit_emit.py is intentionally
              not modified.
          (b) fixture pre-tag confirms the wire contract (sanity
              check for whichever Wave G.1b author writes the wire).
        """
        self._skip_if_no_fixture_dir()
        fixture = _fixture_path(expected_atlas, "should-fire")
        self.assertTrue(fixture.is_file(), f"missing fixture: {fixture}")
        events = _load_ndjson(fixture)
        matches, _total = _count_matches_for_action(
            events, action, expected_atlas
        )
        self.assertGreaterEqual(
            matches, 1,
            f"fixture sanity: expected >=1 event with action={action} "
            f"and atlas_technique={expected_atlas} in {fixture.name}",
        )
        # Production-wire probe (the load-bearing G.1a -> G.1b gate).
        # Until Wave G.1b lands, this assertion fails by design.
        self.assertTrue(
            _production_emit_supports_atlas(action),
            f"production audit_emit.emit_{action} does NOT accept an "
            f"`atlas_technique` parameter — Wave G.1b not yet landed. "
            f"This failure is EXPECTED in G.1a. Once G.1b ships, this "
            f"assertion passes.",
        )

    def assert_does_not_fire_on_negative(
        self, action: str, expected_atlas: str
    ) -> None:
        """Assertion 2 — passes on G.1a (fixture-shape only)."""
        self._skip_if_no_fixture_dir()
        fixture = _fixture_path(expected_atlas, "should-not-fire")
        self.assertTrue(fixture.is_file(), f"missing fixture: {fixture}")
        events = _load_ndjson(fixture)
        matches, _total = _count_matches_for_action(
            events, action, expected_atlas
        )
        self.assertEqual(
            matches, 0,
            f"action={action} must NOT fire on {fixture.name} "
            f"(got {matches} matches)",
        )

    def assert_registry_string_equality(
        self, action: str, expected_atlas: str
    ) -> None:
        """Assertion 3 — passes on G.1a (fixture-shape only)."""
        self._skip_if_no_fixture_dir()
        fixture = _fixture_path(expected_atlas, "should-fire")
        events = _load_ndjson(fixture)
        tagged_values = {
            _emit_atlas_technique(ev)
            for ev in events
            if ev.get("action") == action
        }
        self.assertIn(
            expected_atlas,
            tagged_values,
            f"action={action} expected atlas value {expected_atlas!r} "
            f"in {fixture.name}; found {tagged_values!r}",
        )
        for tv in tagged_values:
            if tv is None:
                continue
            self.assertEqual(
                tv, expected_atlas,
                f"action={action} fixture has divergent "
                f"atlas_technique={tv!r}; registry says "
                f"{expected_atlas!r}",
            )


def _make_test(action: str, atlas_id: str, kind: str):
    """Factory producing one unittest method per (action, assertion).

    PLAN-085 R2 fold (Codex iter-1 P1:F): ``fires`` tests are marked
    ``@unittest.expectedFailure`` until Wave G.1b lands the
    ``atlas_technique`` schema on ``audit_emit.py``. This keeps the
    test suite GREEN at v1.19.0 ship while pinning the G.1a → G.1b
    convergence contract. When G.1b ships, the expected-failure flips
    to "unexpected pass" (failure mode that surfaces the milestone
    landing in CI).
    """
    if kind == "fires":
        def _fn(self: _AtlasTaggingBase) -> None:
            self.assert_fires_on_positive(action, atlas_id)
        # PLAN-085 G.1b SHIPPED: production audit_emit wiring landed.
        # expectedFailure decorator removed; the 5 fires-on-positive
        # tests now turn from xfail -> pass per AC8.
        pass
    elif kind == "not_fires":
        def _fn(self: _AtlasTaggingBase) -> None:
            self.assert_does_not_fire_on_negative(action, atlas_id)
    elif kind == "registry":
        def _fn(self: _AtlasTaggingBase) -> None:
            self.assert_registry_string_equality(action, atlas_id)
    else:  # pragma: no cover
        raise ValueError(f"unknown kind: {kind}")
    _fn.__name__ = f"test_{kind}__{action}__{atlas_id.replace('.', '_')}"
    _fn.__doc__ = (
        f"{kind} assertion for action={action} atlas={atlas_id}"
    )
    return _fn


class TestAtlasTechniqueIdTagging(_AtlasTaggingBase):
    """5 mappings x 3 assertions = 15 generated test methods.

    The pytest collector reports one case per generated method, which
    aligns the runtime case count with PLAN-085 AC8 ("15 cases").
    """


# Attach 15 generated methods to the class.
for _action, _atlas in _ATLAS_REGISTRY.items():
    for _kind in ("fires", "not_fires", "registry"):
        _method = _make_test(_action, _atlas, _kind)
        setattr(TestAtlasTechniqueIdTagging, _method.__name__, _method)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
