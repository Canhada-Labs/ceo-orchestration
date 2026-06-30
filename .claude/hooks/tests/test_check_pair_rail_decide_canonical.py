"""PLAN-112-FOLLOWUP-pair-rail-decide-canonical — W1 + W3.

W1 — translator unit test: exercise ``_base_to_verdicts(base)`` in
     isolation over every ``base`` dict shape ``_decide()`` can return.

W3 — equivalence proof: assert that, for every verdict triple
     ``_base_to_verdicts()`` can produce, the canonical
     ``_lib.pair_rail_decide.detect_case()`` yields the SAME case as the
     legacy inline classification (re-implemented here as the reference
     oracle). Covers ONLY the reachable {A, B, F, None} surface
     (plan §2a.2/§2a.4) — no C/D/E claims.

``hypothesis`` is NOT a project dependency (stdlib-only invariant,
AC9). The plan §3 W3 sketch used ``@given st.sampled_from(...)`` over a
FINITE verdict-pair domain with ``max_examples=200``; for a finite
domain, EXHAUSTIVE enumeration (done here with a deterministic seed for
the optional shuffle) is strictly stronger than sampling 200 examples.
The equivalence assertion is therefore total over the reachable surface.

Path resolution mirrors test_check_pair_rail_matrix.py. stdlib only.
"""
from __future__ import annotations

import importlib.util
import random
import sys
import types
import unittest
from pathlib import Path
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Path resolution -- staging OR canonical (mirrors matrix test).
# ---------------------------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
_IS_STAGING = "staging" in _THIS_FILE.parts and "phase-3" in _THIS_FILE.parts

if _IS_STAGING:
    _HOOKS_DIR = _THIS_FILE.parents[1] / "hooks"
    _LIB_PARENT = _THIS_FILE.parents[1]
else:
    _HOOKS_DIR = _THIS_FILE.parents[1]  # = .claude/hooks/
    _LIB_PARENT = _THIS_FILE.parents[1]

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
if str(_LIB_PARENT) not in sys.path:
    sys.path.insert(0, str(_LIB_PARENT))

_HOOK_PATH = _HOOKS_DIR / "check_pair_rail.py"


def _load_hook() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_pair_rail_canonical",
        str(_HOOK_PATH),
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


try:
    _CPR = _load_hook()
except Exception as exc:  # pragma: no cover - import guard
    raise ImportError(
        f"Failed to load check_pair_rail.py from {_HOOK_PATH}: {exc}"
    ) from exc

# Canonical pure decision module.
from _lib import pair_rail_decide as _PRD  # type: ignore  # noqa: E402


# ---------------------------------------------------------------------------
# Sysmsg fragments verbatim from check_pair_rail._decide() returns.
# (Verified against source lines 595-679.)
# ---------------------------------------------------------------------------
_SYS_SENTINEL = "PAIR-RAIL: bypass via Architect sentinel (.claude/hooks/_lib/x.py)"
_SYS_UNAVAILABLE = "PAIR-RAIL: Codex unavailable (binary missing); fail-OPEN advisory mode."
_SYS_TIMEOUT = "PAIR-RAIL: Codex timeout (30s); fail-OPEN."
_SYS_MALFORMED = "PAIR-RAIL: Codex malformed response (parse); fail-OPEN."
_SYS_WRITESHAPE = (
    "PAIR-RAIL-ADVISORY: Codex returned a write-shaped patch "
    "(update_file_envelope) in a read-only review context "
    "(advisory-only per ADR-127)."
)
_SYS_CLEAN = "PAIR-RAIL: Codex review clean (no patches detected)."


# ---------------------------------------------------------------------------
# Reference ORACLE — the LEGACY inline classification, re-implemented
# faithfully from check_pair_rail._decide_with_matrix() (lines 1147-1231,
# pre-refactor). This is the byte-identity baseline that detect_case() must
# reproduce on the reachable surface.
#
# Returns (case_or_None, codex_verdict) exactly as the inline arms emit.
# ---------------------------------------------------------------------------
def _legacy_inline_classify(base: dict) -> Tuple[Optional[str], str]:
    decision = base.get("decision", "allow")
    sysmsg = base.get("systemMessage", "")

    # Arm 1: Case F — Codex unavailable / timeout / malformed.
    if "Codex unavailable" in sysmsg or "Codex timeout" in sysmsg or "Codex malformed" in sysmsg:
        sysmsg_lower = sysmsg.lower()
        if "malformed" in sysmsg_lower:
            codex_verdict = "MALFORMED"
        elif "timeout" in sysmsg_lower:
            codex_verdict = "TIMEOUT"
        else:
            codex_verdict = "TIMEOUT"  # unavailable coerces to TIMEOUT
        return "F", codex_verdict

    # Arm 2: sentinel bypass — not a matrix case (no emit).
    if "bypass via Architect sentinel" in sysmsg:
        return None, ""

    # Arm 3: Case B — write-shape advisory (or legacy block).
    is_advisory_writeshape = (
        "PAIR-RAIL-ADVISORY" in sysmsg and "write-shaped" in sysmsg
    )
    if decision == "block" or is_advisory_writeshape:
        return "B", "BLOCK"

    # Arm 4: Case A — review clean.
    if "review clean" in sysmsg:
        return "A", "PASS"

    # Arm 5: fall-through — no emit.
    return None, ""


# All `base` dict shapes `_decide()` can return (verified lines 569-679).
_BASE_SHAPES = [
    ("kill_switch_or_oos", {}),
    ("sentinel", {"systemMessage": _SYS_SENTINEL}),
    ("codex_unavailable", {"systemMessage": _SYS_UNAVAILABLE}),
    ("codex_timeout", {"systemMessage": _SYS_TIMEOUT}),
    ("codex_malformed", {"systemMessage": _SYS_MALFORMED}),
    ("write_shape_advisory", {"systemMessage": _SYS_WRITESHAPE}),
    ("review_clean", {"systemMessage": _SYS_CLEAN}),
    # Defensive belt-and-suspenders: a future-introduced block path.
    ("legacy_block", {"decision": "block", "reason": "x"}),
]


class TestBaseToVerdictsTranslator(unittest.TestCase):
    """W1 — _base_to_verdicts() exercised independently per base shape.

    The translator is assumed present on the refactored module as
    ``_CPR._base_to_verdicts``. If it is absent (pre-W2 module), the
    tests skip with a clear marker so the golden suite still runs.
    """

    def setUp(self) -> None:
        if not hasattr(_CPR, "_base_to_verdicts"):
            self.skipTest(
                "_base_to_verdicts not present yet (apply IMPLEMENTATION.md W1/W2 first)"
            )

    def _xlate(self, base: dict) -> Tuple[str, str, str]:
        return _CPR._base_to_verdicts(base)

    def test_clean_review_maps_pass_pass(self) -> None:
        cv, xv, jb = self._xlate({"systemMessage": _SYS_CLEAN})
        self.assertEqual((cv, xv, jb), ("PASS", "PASS", ""))

    def test_write_shape_maps_pass_block(self) -> None:
        cv, xv, jb = self._xlate({"systemMessage": _SYS_WRITESHAPE})
        self.assertEqual((cv, xv, jb), ("PASS", "BLOCK", ""))

    def test_legacy_block_decision_maps_pass_block(self) -> None:
        cv, xv, jb = self._xlate({"decision": "block", "reason": "x"})
        self.assertEqual((cv, xv, jb), ("PASS", "BLOCK", ""))

    def test_codex_unavailable_maps_pass_timeout(self) -> None:
        cv, xv, jb = self._xlate({"systemMessage": _SYS_UNAVAILABLE})
        self.assertEqual((cv, xv, jb), ("PASS", "TIMEOUT", ""))

    def test_codex_timeout_maps_pass_timeout(self) -> None:
        cv, xv, jb = self._xlate({"systemMessage": _SYS_TIMEOUT})
        self.assertEqual((cv, xv, jb), ("PASS", "TIMEOUT", ""))

    def test_codex_malformed_maps_pass_malformed(self) -> None:
        cv, xv, jb = self._xlate({"systemMessage": _SYS_MALFORMED})
        self.assertEqual((cv, xv, jb), ("PASS", "MALFORMED", ""))

    def test_sentinel_maps_to_no_case_tuple(self) -> None:
        # Sentinel must NOT classify to A/B/F — translator yields a
        # tuple detect_case() maps to None.
        cv, xv, jb = self._xlate({"systemMessage": _SYS_SENTINEL})
        self.assertIsNone(
            _PRD.detect_case(claude_verdict=cv, codex_verdict=xv, jaccard_bucket=jb)
        )

    def test_empty_base_maps_to_no_case_tuple(self) -> None:
        cv, xv, jb = self._xlate({})
        self.assertIsNone(
            _PRD.detect_case(claude_verdict=cv, codex_verdict=xv, jaccard_bucket=jb)
        )

    def test_translator_never_raises_on_garbage(self) -> None:
        # Fail-OPEN: malformed/None inputs must not raise.
        for bad in ({"systemMessage": None}, {"decision": 123}, {"systemMessage": 42}):
            try:
                self._xlate(bad)  # type: ignore[arg-type]
            except Exception as exc:  # pragma: no cover - failure path
                self.fail(f"_base_to_verdicts raised on {bad!r}: {exc}")


class TestDetectCaseEquivalence(unittest.TestCase):
    """W3 — detect_case() == legacy inline classification (reachable surface).

    For each `base` shape `_decide()` can produce, the canonical
    detect_case() applied to _base_to_verdicts(base) must equal the
    legacy inline classifier's case. Exhaustive over the finite domain.
    """

    def setUp(self) -> None:
        if not hasattr(_CPR, "_base_to_verdicts"):
            self.skipTest(
                "_base_to_verdicts not present yet (apply IMPLEMENTATION.md W1/W2 first)"
            )

    def test_detect_case_matches_legacy_over_all_base_shapes(self) -> None:
        # Deterministic order (optional shuffle pinned to a fixed seed —
        # mirrors hypothesis max_examples but exhaustive over finite set).
        rng = random.Random(20260521)
        shapes = list(_BASE_SHAPES)
        rng.shuffle(shapes)
        for name, base in shapes:
            with self.subTest(shape=name):
                legacy_case, _legacy_xv = _legacy_inline_classify(base)
                cv, xv, jb = _CPR._base_to_verdicts(base)
                got = _PRD.detect_case(
                    claude_verdict=cv, codex_verdict=xv, jaccard_bucket=jb
                )
                got_case = got.value if got is not None else None
                self.assertEqual(
                    got_case,
                    legacy_case,
                    f"shape={name}: detect_case={got_case!r} != legacy={legacy_case!r}",
                )

    def test_codex_verdict_subdiscrimination_matches_legacy(self) -> None:
        """F-arm: translator's codex_verdict must equal the legacy emit's."""
        for name, base in _BASE_SHAPES:
            legacy_case, legacy_xv = _legacy_inline_classify(base)
            if legacy_case != "F":
                continue
            _cv, xv, _jb = _CPR._base_to_verdicts(base)
            with self.subTest(shape=name):
                self.assertEqual(
                    xv, legacy_xv,
                    f"shape={name}: codex_verdict {xv!r} != legacy {legacy_xv!r}",
                )

    def test_reachable_surface_is_exactly_a_b_f_none(self) -> None:
        """No base shape classifies to C/D/E (plan §2a.2 unreachability)."""
        seen = set()
        for _name, base in _BASE_SHAPES:
            cv, xv, jb = _CPR._base_to_verdicts(base)
            got = _PRD.detect_case(claude_verdict=cv, codex_verdict=xv, jaccard_bucket=jb)
            seen.add(got.value if got is not None else None)
        self.assertTrue(
            seen.issubset({"A", "B", "F", None}),
            f"reachable surface leaked beyond A/B/F/None: {seen}",
        )
        self.assertNotIn("C", seen)
        self.assertNotIn("D", seen)
        self.assertNotIn("E", seen)


class TestLegacyOracleSelfConsistency(unittest.TestCase):
    """Sanity: the oracle itself reproduces the documented case table.

    Runs even pre-W2 (no _base_to_verdicts dependency) so the golden
    truth is pinned regardless of refactor state.
    """

    def test_oracle_case_table(self) -> None:
        expect = {
            "kill_switch_or_oos": (None, ""),
            "sentinel": (None, ""),
            "codex_unavailable": ("F", "TIMEOUT"),
            "codex_timeout": ("F", "TIMEOUT"),
            "codex_malformed": ("F", "MALFORMED"),
            "write_shape_advisory": ("B", "BLOCK"),
            "review_clean": ("A", "PASS"),
            "legacy_block": ("B", "BLOCK"),
        }
        for name, base in _BASE_SHAPES:
            with self.subTest(shape=name):
                self.assertEqual(_legacy_inline_classify(base), expect[name])


if __name__ == "__main__":
    unittest.main(verbosity=2)
