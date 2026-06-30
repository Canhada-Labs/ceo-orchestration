"""PLAN-112-FOLLOWUP-plan-093-followup-collision W3 — duplicate frontmatter
``id:`` validator (validate_governance_fast.py::_check_plan_id_uniqueness).

The PLAN-093-FOLLOWUP dual-id collision (two files both declaring
``id: PLAN-093-FOLLOWUP``) made every id reference ambiguous and went
undetected because no validator checked id-uniqueness. This pins the new
guard:
- FLAG duplicate ids (the exact PLAN-093-FOLLOWUP collision shape).
- PASS on unique slug-bearing ids (the post-fix shape).
- Scan ROOT-LEVEL only — a nested PLAN-NNN/sandbox/.../project-clone with a
  duplicate id must NOT trip the check (else hundreds of false positives).
- Fail-soft on id-less / non-plan files.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_vgf = _load_module(
    "validate_governance_fast_pidtest",
    REPO_ROOT / ".claude" / "scripts" / "validate_governance_fast.py",
)


def _write_plan(
    plans_dir: Path, filename: str, plan_id: Optional[str], body: str = "x"
) -> None:
    fm = "---\n"
    if plan_id is not None:
        fm += "id: {}\n".format(plan_id)
    fm += "status: done\n---\n"
    (plans_dir / filename).write_text(fm + body + "\n", encoding="utf-8")


class PlanIdUniquenessTest(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        self._tmp = tempfile.mkdtemp(prefix="plan-id-uniq-")
        self.repo = Path(self._tmp)
        self.plans = self.repo / ".claude" / "plans"
        self.plans.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)
        super().tearDown()

    def _run(self) -> List[str]:
        errors: List[str] = []
        _vgf._check_plan_id_uniqueness(self.repo, errors)
        return errors

    def test_duplicate_ids_flagged(self) -> None:
        # The exact PLAN-093-FOLLOWUP collision shape.
        _write_plan(
            self.plans, "PLAN-093-FOLLOWUP-cadence-amendment.md", "PLAN-093-FOLLOWUP"
        )
        _write_plan(
            self.plans,
            "PLAN-093-FOLLOWUP-deferred-callsite-surfaces.md",
            "PLAN-093-FOLLOWUP",
        )
        errors = self._run()
        self.assertEqual(len(errors), 1, errors)
        self.assertTrue(
            errors[0].startswith("plan_id_duplicate:PLAN-093-FOLLOWUP:"), errors
        )
        self.assertIn("PLAN-093-FOLLOWUP-cadence-amendment.md", errors[0])
        self.assertIn("PLAN-093-FOLLOWUP-deferred-callsite-surfaces.md", errors[0])

    def test_unique_slug_bearing_ids_pass(self) -> None:
        # The post-fix shape — distinct slug-bearing ids.
        _write_plan(
            self.plans,
            "PLAN-093-FOLLOWUP-cadence-amendment.md",
            "PLAN-093-FOLLOWUP-cadence-amendment",
        )
        _write_plan(
            self.plans,
            "PLAN-093-FOLLOWUP-deferred-callsite-surfaces.md",
            "PLAN-093-FOLLOWUP-deferred-callsite-surfaces",
        )
        _write_plan(self.plans, "PLAN-112-coverage.md", "PLAN-112-coverage")
        self.assertEqual(self._run(), [])

    def test_nested_sandbox_clone_not_scanned(self) -> None:
        # A nested clone sharing a root plan's id must NOT trip the check —
        # iterdir is root-only. This is the real PLAN-112/sandbox/*/project-clone
        # case that would otherwise produce hundreds of false duplicates.
        _write_plan(self.plans, "PLAN-112-x.md", "PLAN-112-x")
        clone = (
            self.plans / "PLAN-112" / "sandbox" / "A8" / "project-clone"
            / ".claude" / "plans"
        )
        clone.mkdir(parents=True, exist_ok=True)
        _write_plan(clone, "PLAN-112-x.md", "PLAN-112-x")  # same id, but nested
        self.assertEqual(self._run(), [])

    def test_failsoft_on_idless_files(self) -> None:
        # Plans without an id: line are skipped (no crash, no false duplicate).
        _write_plan(self.plans, "PLAN-200-no-id.md", None)
        _write_plan(self.plans, "PLAN-201-also-no-id.md", None)
        self.assertEqual(self._run(), [])

    def test_non_plan_files_ignored(self) -> None:
        # Files that don't match the PLAN filename regex are ignored even if
        # they carry an id (README.md, etc.).
        _write_plan(self.plans, "PLAN-300-a.md", "shared-id")
        (self.plans / "README.md").write_text(
            "---\nid: shared-id\n---\n", encoding="utf-8"
        )
        self.assertEqual(self._run(), [])


if __name__ == "__main__":
    unittest.main()
