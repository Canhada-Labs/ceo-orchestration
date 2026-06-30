"""S213 — frontmatter ``status:`` presence + legality validator
(validate_governance_fast.py::_check_plan_frontmatter_status), mirroring the
bash gate in validate-governance.sh §1 item 4.

The PLAN-128 blind-spot: a plan whose lifecycle status lived only in body
markdown (``- **status:** executing``) and not in the YAML frontmatter was
invisible to ceo-boot's plan-state detectors (which read ``status:`` from the
frontmatter ONLY), so an executing plan silently reported as "0 executing" at
boot. This pins the new guard:
- FLAG a plan with no frontmatter ``status:`` (the exact PLAN-128 shape).
- FLAG a plan whose frontmatter status is not a legal lifecycle state.
- PASS every legal lifecycle state.
- A body-only ``status:`` must NOT satisfy the check (the blind-spot itself).
- Scan ROOT-LEVEL only — a nested PLAN-NNN/sandbox clone must NOT trip it.
- Ignore non-plan files (README.md, schemas).
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
    "validate_governance_fast_statustest",
    REPO_ROOT / ".claude" / "scripts" / "validate_governance_fast.py",
)


def _write_plan(
    plans_dir: Path,
    filename: str,
    fm_status: Optional[str],
    body_status: Optional[str] = None,
) -> None:
    """Write a plan with ``fm_status`` in the frontmatter (omitted if None) and
    optionally a body-only ``- **status:**`` line (the blind-spot shape)."""
    fm = "---\n"
    if fm_status is not None:
        fm += "status: {}\n".format(fm_status)
    fm += "id: {}\n---\n".format(filename[:-3])
    body = "# Title\n"
    if body_status is not None:
        body += "- **status:** {}\n".format(body_status)
    (plans_dir / filename).write_text(fm + body, encoding="utf-8")


class PlanFrontmatterStatusTest(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        self._tmp = tempfile.mkdtemp(prefix="plan-fm-status-")
        self.repo = Path(self._tmp)
        self.plans = self.repo / ".claude" / "plans"
        self.plans.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)
        super().tearDown()

    def _run(self) -> List[str]:
        errors: List[str] = []
        _vgf._check_plan_frontmatter_status(self.repo, errors)
        return errors

    def test_missing_frontmatter_status_flagged(self) -> None:
        _write_plan(self.plans, "PLAN-400-no-status.md", fm_status=None)
        errors = self._run()
        self.assertEqual(errors, ["plan_status_missing:PLAN-400-no-status.md"])

    def test_illegal_status_flagged(self) -> None:
        _write_plan(self.plans, "PLAN-401-bad.md", fm_status="in-progress")
        errors = self._run()
        self.assertEqual(errors, ["plan_status_illegal:PLAN-401-bad.md:in-progress"])

    def test_all_legal_statuses_pass(self) -> None:
        legal = (
            "draft",
            "reviewed",
            "executing",
            "done",
            "abandoned",
            "refused",
            "superseded",
        )
        for i, state in enumerate(legal):
            _write_plan(
                self.plans, "PLAN-41{}-{}.md".format(i, state), fm_status=state
            )
        self.assertEqual(self._run(), [])

    def test_body_only_status_is_the_blind_spot(self) -> None:
        # The exact PLAN-128 shape: status only in body prose, absent from
        # frontmatter → MUST be flagged as missing (this is what S213 fixed).
        _write_plan(
            self.plans,
            "PLAN-420-body-only.md",
            fm_status=None,
            body_status="executing",
        )
        errors = self._run()
        self.assertEqual(errors, ["plan_status_missing:PLAN-420-body-only.md"])

    def test_body_horizontal_rule_not_treated_as_frontmatter(self) -> None:
        # Codex S213 [P2]: a plan with NO leading frontmatter but a later
        # Markdown horizontal rule followed by a plain `status:` line must NOT
        # satisfy the guard — frontmatter is anchored at the start of the file,
        # matching ceo-boot.py's `re.match(r"^---...")`. Otherwise a body-only
        # status passes this gate yet stays invisible to the boot detectors.
        path = self.plans / "PLAN-450-rule-in-body.md"
        path.write_text(
            "# No frontmatter\n\nSome text.\n\n---\nstatus: executing\n---\n",
            encoding="utf-8",
        )
        self.assertEqual(self._run(), ["plan_status_missing:PLAN-450-rule-in-body.md"])

    def test_nested_sandbox_clone_not_scanned(self) -> None:
        _write_plan(self.plans, "PLAN-430-x.md", fm_status="done")
        clone = (
            self.plans / "PLAN-430" / "sandbox" / "A1" / "project-clone"
            / ".claude" / "plans"
        )
        clone.mkdir(parents=True, exist_ok=True)
        _write_plan(clone, "PLAN-430-x.md", fm_status=None)  # nested, no status
        self.assertEqual(self._run(), [])

    def test_non_plan_files_ignored(self) -> None:
        (self.plans / "README.md").write_text(
            "no frontmatter here\n", encoding="utf-8"
        )
        (self.plans / "PLAN-SCHEMA.md").write_text(
            "---\nstatus: accepted\n---\n", encoding="utf-8"
        )
        # Only legal-status plan files are checked; the schema/readme are not
        # PLAN-NNN-slug files so they are skipped even with a non-lifecycle
        # status value.
        _write_plan(self.plans, "PLAN-440-ok.md", fm_status="done")
        self.assertEqual(self._run(), [])


class PlanIdPresenceTest(TestEnvContext):
    """S213 — frontmatter ``id:`` presence guard
    (validate_governance_fast.py::_check_plan_id_presence). The id-uniqueness
    guard is fail-soft on id-less files, so a plan with no id at all escaped
    governance (the 121-128 cluster) until this presence gate."""

    def setUp(self) -> None:
        super().setUp()
        self._tmp = tempfile.mkdtemp(prefix="plan-id-presence-")
        self.repo = Path(self._tmp)
        self.plans = self.repo / ".claude" / "plans"
        self.plans.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)
        super().tearDown()

    def _run(self) -> List[str]:
        errors: List[str] = []
        _vgf._check_plan_id_presence(self.repo, errors)
        return errors

    def _write(self, filename: str, fm_id: Optional[str]) -> None:
        fm = "---\n"
        if fm_id is not None:
            fm += "id: {}\n".format(fm_id)
        fm += "status: done\n---\n# Title\n"
        (self.plans / filename).write_text(fm, encoding="utf-8")

    def test_missing_id_flagged(self) -> None:
        self._write("PLAN-500-no-id.md", None)
        self.assertEqual(self._run(), ["plan_id_missing:PLAN-500-no-id.md"])

    def test_present_id_passes(self) -> None:
        self._write("PLAN-501-ok.md", "PLAN-501")
        self.assertEqual(self._run(), [])

    def test_blank_id_value_flagged(self) -> None:
        # Codex S213 [P2]: a frontmatter line `id:` with no value (or only
        # whitespace) must be rejected — both gates strip the value and
        # require it non-empty, so bash and python never diverge.
        (self.plans / "PLAN-504-blank-id.md").write_text(
            "---\nid:   \nstatus: done\n---\n# x\n", encoding="utf-8"
        )
        self.assertEqual(self._run(), ["plan_id_missing:PLAN-504-blank-id.md"])

    def test_body_horizontal_rule_not_frontmatter(self) -> None:
        # Same anchoring guarantee as status: an `id:` after a body `---` must
        # NOT satisfy the presence gate (frontmatter is anchored at line 1).
        (self.plans / "PLAN-502-rule.md").write_text(
            "# No frontmatter\n\n---\nid: PLAN-502\n---\n", encoding="utf-8"
        )
        self.assertEqual(self._run(), ["plan_id_missing:PLAN-502-rule.md"])

    def test_non_plan_files_ignored(self) -> None:
        (self.plans / "README.md").write_text("no fm\n", encoding="utf-8")
        self._write("PLAN-503-ok.md", "PLAN-503")
        self.assertEqual(self._run(), [])


if __name__ == "__main__":
    unittest.main()
