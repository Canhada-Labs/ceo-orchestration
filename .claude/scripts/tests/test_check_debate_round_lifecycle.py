"""Unit tests for `.claude/scripts/check-debate-round-lifecycle.py`.

PLAN-019 F-CHAOS-9. Stdlib-only; Python >=3.9 compatible.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


def _load_module():
    here = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "check_debate_round_lifecycle",
        here / "check-debate-round-lifecycle.py",
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


life = _load_module()


class TestRoundLifecycle(unittest.TestCase):
    def _make_plan(self, td: Path, plan_id: str, rounds: dict) -> Path:
        """rounds: {"debate": [(1, consensus_ok), (2, ...)], ...}."""
        plan = td / plan_id
        plan.mkdir()
        for kind, entries in rounds.items():
            kd = plan / kind
            kd.mkdir()
            sentinel = "consensus.md" if kind == "debate" else "approved.md"
            for n, has_sentinel in entries:
                rd = kd / f"round-{n}"
                rd.mkdir()
                if has_sentinel:
                    (rd / sentinel).write_text("x", encoding="utf-8")
        return plan

    def test_single_round_one_no_sentinel_is_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._make_plan(tdp, "PLAN-001", {"debate": [(1, False)]})
            e, _ = life.validate_all(tdp)
            self.assertEqual(e, [])

    def test_two_rounds_first_missing_consensus_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._make_plan(tdp, "PLAN-001", {"debate": [(1, False), (2, False)]})
            e, _ = life.validate_all(tdp)
            self.assertTrue(
                any("missing `consensus.md`" in msg for msg in e),
                f"expected missing-consensus error, got {e!r}",
            )

    def test_two_rounds_first_with_consensus_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._make_plan(tdp, "PLAN-001", {"debate": [(1, True), (2, False)]})
            e, _ = life.validate_all(tdp)
            self.assertEqual(e, [])

    def test_missing_round_one_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._make_plan(tdp, "PLAN-001", {"debate": [(2, True)]})
            e, _ = life.validate_all(tdp)
            self.assertTrue(
                any("must start at round-1" in msg for msg in e),
                f"expected first-round-1 error, got {e!r}",
            )

    def test_gap_between_rounds_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._make_plan(
                tdp,
                "PLAN-001",
                {"debate": [(1, True), (3, False)]},
            )
            e, _ = life.validate_all(tdp)
            self.assertTrue(
                any("gap between round-1 and round-3" in msg for msg in e),
                f"expected gap error, got {e!r}",
            )

    def test_round_zero_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            # Construct round-0 manually.
            plan = tdp / "PLAN-001"
            (plan / "debate").mkdir(parents=True)
            (plan / "debate" / "round-0").mkdir()
            e, _ = life.validate_all(tdp)
            self.assertTrue(
                any("round-0 is invalid" in msg for msg in e),
                f"expected round-0 error, got {e!r}",
            )

    def test_padded_round_name_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            plan = tdp / "PLAN-001"
            (plan / "debate").mkdir(parents=True)
            (plan / "debate" / "round-01").mkdir()
            e, _ = life.validate_all(tdp)
            self.assertTrue(
                any("zero-padded round name" in msg for msg in e),
                f"expected padded-name error, got {e!r}",
            )

    def test_architect_uses_approved_md_sentinel(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._make_plan(
                tdp,
                "PLAN-001",
                {"architect": [(1, False), (2, False)]},
            )
            e, _ = life.validate_all(tdp)
            self.assertTrue(
                any("missing `approved.md`" in msg for msg in e),
                f"expected approved.md error, got {e!r}",
            )

    def test_unexpected_subdir_is_warning(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            plan = tdp / "PLAN-001"
            (plan / "debate").mkdir(parents=True)
            (plan / "debate" / "round-1").mkdir()
            (plan / "debate" / "notes").mkdir()
            e, w = life.validate_all(tdp)
            self.assertEqual(e, [])
            self.assertTrue(
                any("not a round-<N> directory" in msg for msg in w),
                f"expected unknown-dir warning, got {w!r}",
            )

    def test_main_exit_zero_on_clean(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._make_plan(tdp, "PLAN-001", {"debate": [(1, True), (2, False)]})
            rc = life.main(["--plans-dir", str(tdp)])
            self.assertEqual(rc, 0)

    def test_main_exit_one_on_broken(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._make_plan(tdp, "PLAN-001", {"debate": [(2, True)]})
            rc = life.main(["--plans-dir", str(tdp)])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
