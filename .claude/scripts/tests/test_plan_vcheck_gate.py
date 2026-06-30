"""PLAN-134 W1 — PLAN-SCHEMA §13 verification-declaration gate
(validate_governance_fast.py::_check_plan_vcheck_declarations).

Doctrine V0 (deterministic-first cascade): every execution unit (markdown
checkbox in a Waves/Progress-log-style section) of a NEW plan must declare
its mechanical check upfront via a ``Check:`` line, or explicitly
``Check: none (doc-only)``. Pinned here:
- PROSPECTIVE: plans with ``created:`` before 2026-06-12 (or missing /
  non-ISO) are grandfathered — the ~155 existing plans must never redden.
- Terminal statuses (done/abandoned/refused/superseded) are exempt.
- Coverage forms per §13.2: inline / continuation / block-level.
- Only §13.3 sections are enforced (Success criteria checkboxes are not).
- Fenced code blocks are ignored; a bare ``Check:`` (no value) never covers.
- Error format names plan + line: ``plan_vcheck_missing:<file>:L<n>:<item>``.
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
    "validate_governance_fast_vchecktest",
    REPO_ROOT / ".claude" / "scripts" / "validate_governance_fast.py",
)

OLD = "2026-06-01"   # pre-enforcement
NEW = "2026-06-12"   # first enforced day


class PlanVcheckGateTest(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        self._tmp = tempfile.mkdtemp(prefix="plan-vcheck-")
        self.repo = Path(self._tmp)
        self.plans = self.repo / ".claude" / "plans"
        self.plans.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)
        super().tearDown()

    def _run(self) -> List[str]:
        errors: List[str] = []
        _vgf._check_plan_vcheck_declarations(self.repo, errors)
        return errors

    def _write_plan(
        self,
        filename: str,
        body: str,
        created: Optional[str] = NEW,
        status: str = "draft",
    ) -> None:
        fm = "---\nid: {}\nstatus: {}\n".format(filename[:-3], status)
        if created is not None:
            fm += "created: {}\n".format(created)
        fm += "---\n"
        (self.plans / filename).write_text(fm + body, encoding="utf-8")

    # --- §13.4 prospective gate ------------------------------------------

    def test_old_plan_untouched(self) -> None:
        # The ~155 existing plans (created < 2026-06-12) must NEVER redden,
        # even with bare checkboxes in an enforced section.
        self._write_plan(
            "PLAN-900-old.md",
            "# T\n\n## Waves\n\n- [ ] bare item, no check anywhere\n",
            created=OLD,
            status="executing",
        )
        self.assertEqual(self._run(), [])

    def test_missing_created_grandfathered(self) -> None:
        self._write_plan(
            "PLAN-901-no-created.md",
            "## Waves\n\n- [ ] bare item\n",
            created=None,
        )
        self.assertEqual(self._run(), [])

    def test_placeholder_created_grandfathered(self) -> None:
        # Non-ISO created (template placeholder shape) → fail-soft skip.
        self._write_plan(
            "PLAN-902-placeholder.md",
            "## Waves\n\n- [ ] bare item\n",
            created="YYYY-MM-DD",
        )
        self.assertEqual(self._run(), [])

    def test_quoted_created_date_still_enforced(self) -> None:
        # Codex S228 finding #5: YAML-quoted dates (created: "2026-06-12")
        # must NOT dodge the prospective gate.
        for quote in ('"', "'"):
            self._write_plan(
                "PLAN-99{}-quoted.md".format(7 if quote == '"' else 8),
                "## Waves\n\n- [ ] bare item, no check\n",
                created="{q}{d}{q}".format(q=quote, d=NEW),
            )
        errors = self._run()
        self.assertEqual(len(errors), 2, errors)
        for e in errors:
            self.assertTrue(e.startswith("plan_vcheck_missing:"), e)

    def test_done_status_exempt(self) -> None:
        for i, status in enumerate(
            ("done", "abandoned", "refused", "superseded")
        ):
            self._write_plan(
                "PLAN-90{}-terminal.md".format(3 + i),
                "## Waves\n\n- [ ] bare item\n",
                status=status,
            )
        self.assertEqual(self._run(), [])

    # --- §13.1/§13.2 coverage forms --------------------------------------

    def test_new_plan_missing_check_fails_with_plan_and_line(self) -> None:
        # fm = 5 lines; body L6..; the bare checkbox lands on line 10.
        self._write_plan(
            "PLAN-910-new.md",
            "# Title\n\n## Waves\n\n- [ ] bare item\n",
        )
        self.assertEqual(
            self._run(),
            ["plan_vcheck_missing:PLAN-910-new.md:L10:bare item"],
        )

    def test_inline_check_passes(self) -> None:
        self._write_plan(
            "PLAN-911-inline.md",
            "## Waves\n\n- [ ] amend schema — Check: pytest tests/ -q\n",
        )
        self.assertEqual(self._run(), [])

    def test_continuation_check_passes(self) -> None:
        self._write_plan(
            "PLAN-912-cont.md",
            "## Waves\n\n- [x] wire gate\n"
            "  Check: python3 .claude/scripts/validate_governance_fast.py\n",
        )
        self.assertEqual(self._run(), [])

    def test_block_level_check_covers_all_items(self) -> None:
        self._write_plan(
            "PLAN-913-block.md",
            "## Waves\n\n### Wave 1\n\nCheck: pytest tests/ -q\n\n"
            "- [ ] item one\n- [~] item two\n- [X] item three\n",
        )
        self.assertEqual(self._run(), [])

    def test_doc_only_opt_out_passes(self) -> None:
        self._write_plan(
            "PLAN-914-doc.md",
            "## Waves\n\n- [ ] rewrite the README intro\n"
            "  Check: none (doc-only)\n",
        )
        self.assertEqual(self._run(), [])

    def test_bare_check_token_without_value_does_not_cover(self) -> None:
        self._write_plan(
            "PLAN-915-empty.md",
            "## Waves\n\n- [ ] item\n  Check:\n",
        )
        errors = self._run()
        self.assertEqual(len(errors), 1)
        self.assertTrue(
            errors[0].startswith("plan_vcheck_missing:PLAN-915-empty.md:L")
        )

    def test_new_heading_resets_block_coverage(self) -> None:
        # Block-level Check on Wave 1 must NOT bleed into Wave 2 (§13.2.3).
        self._write_plan(
            "PLAN-916-reset.md",
            "## Waves\n\n### Wave 1\nCheck: pytest -q\n- [ ] covered\n\n"
            "### Wave 2\n- [ ] uncovered wave-two item\n",
        )
        errors = self._run()
        self.assertEqual(len(errors), 1)
        self.assertIn("PLAN-916-reset.md", errors[0])
        self.assertIn("uncovered wave-two item", errors[0])

    # --- §13.3 section scoping -------------------------------------------

    def test_unenforced_sections_ignored(self) -> None:
        self._write_plan(
            "PLAN-920-scope.md",
            "## Success criteria\n\n- [ ] all green\n\n"
            "## Open questions\n\n- [ ] who signs?\n",
        )
        self.assertEqual(self._run(), [])

    def test_progress_log_and_sprint_plan_enforced(self) -> None:
        self._write_plan(
            "PLAN-921-sections.md",
            "## Progress log\n\n- [x] bare logged item\n\n"
            "## Sprint plan\n\n- [ ] bare sprint item\n",
        )
        errors = self._run()
        self.assertEqual(len(errors), 2)
        self.assertIn("bare logged item", errors[0])
        self.assertIn("bare sprint item", errors[1])

    def test_enforced_region_ends_at_sibling_heading(self) -> None:
        # `## Next` (same level, non-matching) closes the `## Waves` region.
        self._write_plan(
            "PLAN-922-end.md",
            "## Waves\n\n- [ ] covered — Check: pytest -q\n\n"
            "## Next\n\n- [ ] free-form note checkbox\n",
        )
        self.assertEqual(self._run(), [])

    def test_nested_subheadings_stay_enforced(self) -> None:
        # `### Notes` under `## Waves` is still inside the enforced region
        # (ANY enclosing heading matches).
        self._write_plan(
            "PLAN-923-nested.md",
            "## Waves\n\n### Notes\n\n- [ ] bare nested item\n",
        )
        errors = self._run()
        self.assertEqual(len(errors), 1)
        self.assertIn("bare nested item", errors[0])

    def test_code_fence_contents_ignored(self) -> None:
        self._write_plan(
            "PLAN-924-fence.md",
            "## Waves\n\n```\n- [ ] example checkbox inside a fence\n```\n\n"
            "- [ ] real item — Check: grep -q vcheck file.py\n",
        )
        self.assertEqual(self._run(), [])

    # --- wiring ------------------------------------------------------------

    def test_registered_in_fast_profile_run(self) -> None:
        result = _vgf.run(self.repo)
        self.assertIn("plan_vcheck_declarations", result["checks_run"])


if __name__ == "__main__":
    unittest.main()
