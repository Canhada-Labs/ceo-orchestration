"""Tests for fan-plan-parser.py + the /fan-plan advisory render (PLAN-138 Wave B).

Covers:
- B.2 grammar + defaults (priority/story/path extraction; lenient defaults).
- B.2 ReDoS bound (a 100k-char pathological line completes well under 0.5s).
- B.3 backward-compat numeric scan over the FULL enumerated corpus
  (plans_scanned == count of PLAN-*.md on disk; rejected == 0; 100+ covered;
  zero raised exceptions).
- B.4 advisory-only + cost-envelope render (the /fan-plan proposal block
  carries PROPOSED + a COST ENVELOPE with a numeric agent count + the inert
  model caveat, and contains ZERO executed fan-out primitive calls).

Stdlib-only unittest, env-isolated via TestEnvContext (env-hygiene gate
compliance — no bare ``os.environ[...]=``, no bare ``unittest.TestCase``).
"""
from __future__ import annotations

import importlib.util
import re
import sys
import time
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

# Ensure ``_lib.testing`` (TestEnvContext) is importable for env-isolation.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_PARSER_PATH = _REPO_ROOT / ".claude" / "scripts" / "fan-plan-parser.py"
_PLANS_DIR = _REPO_ROOT / ".claude" / "plans"
_COMMAND_PATH = _REPO_ROOT / ".claude" / "commands" / "fan-plan.md"


def _load_parser() -> Any:
    """Load the parser module from disk by file path (hyphenated filename)."""
    spec = importlib.util.spec_from_file_location("fan_plan_parser", _PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestFanPlanGrammar(TestEnvContext):
    """B.2 — AC-line grammar + lenient defaults."""

    def setUp(self) -> None:  # noqa: D102
        super().setUp()
        self.fpp = _load_parser()

    def test_full_token_line(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=False):
            parsed = self.fpp.parse_ac_line("- [P0] [US1] [src/x.py] do thing")
        self.assertEqual(parsed["priority"], "P0")
        self.assertEqual(parsed["story"], "US1")
        self.assertEqual(parsed["path"], "src/x.py")
        self.assertEqual(parsed["description"], "do thing")

    def test_bare_line_defaults(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=False):
            parsed = self.fpp.parse_ac_line("- do thing")
        self.assertEqual(parsed["priority"], "P1")
        self.assertIsNone(parsed["story"])
        self.assertIsNone(parsed["path"])
        self.assertEqual(parsed["description"], "do thing")

    def test_priority_only(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=False):
            parsed = self.fpp.parse_ac_line("- [P2] something")
        self.assertEqual(parsed["priority"], "P2")
        self.assertIsNone(parsed["story"])
        self.assertIsNone(parsed["path"])

    def test_path_only_defaults_priority(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=False):
            parsed = self.fpp.parse_ac_line("- [.claude/x.md] note")
        self.assertEqual(parsed["priority"], "P1")
        self.assertIsNone(parsed["story"])
        self.assertEqual(parsed["path"], ".claude/x.md")

    def test_malformed_never_raises(self) -> None:
        # Unterminated/garbage brackets degrade to defaults, no exception.
        with mock.patch.dict("os.environ", {}, clear=False):
            for bad in ("- [P0 unterminated", "- [[[ junk", "", "   ", "-"):
                parsed = self.fpp.parse_ac_line(bad)
                self.assertIn(parsed["priority"], self.fpp.VALID_PRIORITIES)


class TestFanPlanRedos(TestEnvContext):
    """B.2 — ReDoS bound: a pathological line completes in < 0.5s."""

    def setUp(self) -> None:  # noqa: D102
        super().setUp()
        self.fpp = _load_parser()

    def test_pathological_line_is_linear(self) -> None:
        pathological = "- " + ("[" * 100000) + "P0] do thing"
        with mock.patch.dict("os.environ", {}, clear=False):
            start = time.time()
            parsed = self.fpp.parse_ac_line(pathological)
            elapsed = time.time() - start
        self.assertLess(elapsed, 0.5, "parser is not linear-time (ReDoS risk)")
        # Truncation warning recorded; still returns a dict, never raises.
        self.assertIn(parsed["priority"], self.fpp.VALID_PRIORITIES)


class TestFanPlanCorpusScan(TestEnvContext):
    """B.3 — backward-compat numeric scan over the full enumerated corpus."""

    def setUp(self) -> None:  # noqa: D102
        super().setUp()
        self.fpp = _load_parser()

    def _expected_plan_file_count(self) -> int:
        # Matches `find .claude/plans -maxdepth 1 -type f -name 'PLAN-*.md'`.
        return len([p for p in _PLANS_DIR.glob("PLAN-*.md") if p.is_file()])

    def test_scan_covers_full_corpus_zero_rejects(self) -> None:
        # scan_plans rejects dirs outside the repo plans tree, so seed
        # synthetic numeric plans INSIDE it (cleaned up after) to exercise
        # the PLAN-100+ glob path without depending on the live plan corpus
        # (the distributed repo ships only schemas + examples here).
        synth = [
            _PLANS_DIR / f"PLAN-9{n:02d}-synthetic-fanplan-test.md"
            for n in (1, 2, 50)
        ]
        for p in synth:
            p.write_text("# synthetic plan\nstatus: draft\n", encoding="utf-8")
        self.addCleanup(
            lambda: [q.unlink() for q in synth if q.exists()]
        )
        with mock.patch.dict("os.environ", {}, clear=False):
            summary = self.fpp.scan_plans(_PLANS_DIR, _REPO_ROOT)
        expected = self._expected_plan_file_count()
        self.assertEqual(summary.get("error"), None)
        self.assertEqual(
            summary["plans_scanned"],
            expected,
            "plans_scanned must equal the on-disk PLAN-*.md count",
        )
        self.assertEqual(summary["rejected"], 0, "scan must be lenient (0 rejects)")
        ids = summary["plan_ids"]
        self.assertTrue(ids, "expected at least one numeric plan id")
        self.assertTrue(
            any(i >= 100 for i in ids),
            "numeric scan must cover PLAN-100+ (glob, not PLAN-0[0-9][0-9])",
        )

    def test_scan_rejects_dir_outside_plans_tree(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=False):
            # self.project_dir is an isolated tmp tree outside the repo plans.
            summary = self.fpp.scan_plans(Path(self.project_dir), _REPO_ROOT)
        self.assertEqual(
            summary.get("error"), "scan_plans_dir_outside_repo_plans_tree"
        )
        self.assertEqual(summary["plans_scanned"], 0)


class TestFanPlanRender(TestEnvContext):
    """B.4 — the /fan-plan proposal render is advisory-only with a cost envelope."""

    def setUp(self) -> None:  # noqa: D102
        super().setUp()
        self.fpp = _load_parser()
        self.command_text = _COMMAND_PATH.read_text(encoding="utf-8")

    def _extract_proposal_template(self) -> str:
        # The command documents the EXACT proposal shape in a fenced block
        # delimited by the PROPOSED banner and the END PROPOSAL footer.
        blocks = re.findall(
            r"```\n(=== PROPOSED.*?=== END PROPOSAL.*?)\n```",
            self.command_text,
            re.DOTALL,
        )
        self.assertTrue(blocks, "command must document a PROPOSED proposal block")
        return blocks[0]

    def test_render_has_proposed_and_cost_envelope(self) -> None:
        out = self._extract_proposal_template()
        self.assertIn("PROPOSED", out)
        self.assertIn("cost envelope", out.lower())

    def test_render_has_numeric_agent_count(self) -> None:
        out = self._extract_proposal_template()
        # "up to 17 agents" — a concrete numeric agent count must be present.
        self.assertRegex(out, r"\b17\b")
        self.assertRegex(out, r"8 finders")

    def test_render_has_inert_model_caveat(self) -> None:
        out = self._extract_proposal_template()
        self.assertIn("INERT", out)
        self.assertIn("opts.model", out)
        self.assertIn("session model", out.lower())

    def test_render_executes_zero_fanout_primitives(self) -> None:
        out = self._extract_proposal_template()
        # The rendered proposal must NOT call the harness fan-out primitives.
        self.assertIsNone(
            re.search(r"(^|[^a-z])(parallel|agent)\(", out),
            "the rendered proposal must contain zero fan-out primitive calls",
        )

    def test_command_documents_kill_switch(self) -> None:
        self.assertIn("CEO_FANPLAN=0", self.command_text)


if __name__ == "__main__":
    unittest.main()
