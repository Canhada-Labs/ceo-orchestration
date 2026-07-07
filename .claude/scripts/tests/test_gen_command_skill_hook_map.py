"""PLAN-153 Wave C item 6 — gen-command-skill-hook-map.py determinism + gate.

Covers ``.claude/scripts/gen-command-skill-hook-map.py``:

* deterministic generation (byte-stable double runs, no timestamps/dates,
  trailing newline) of the generated ``docs/COMMAND-SKILL-HOOK-MAP.md``;
* edge derivation: command->skill (backticked slug + skills-path segment,
  non-catalog tokens ignored), command->script (``.claude/scripts/tests/``
  excluded), hook registration rows (events sorted, chain order kept,
  matcher pipes escaped, inline-echo labeled), surface-guard source scan
  (skills/commands surfaces + unresolved hook files reported honestly);
* the ``--check`` regen+diff idempotency gate (build-plugin B6 /
  skill-inventory pattern): rc=0 in sync, rc=1 with unified diff on drift
  or missing doc, and --check mutates nothing;
* a live-repo sync smoke — the same assertion CI's --check step makes.

Hermetic: mutation only in tempdir fake repos; live-repo tests read-only.
TestEnvContext base per the env-hygiene gate (belt-and-braces isolation).
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / ".claude" / "scripts" / "gen-command-skill-hook-map.py"

_HOOKS_DIR = REPO / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_spec = importlib.util.spec_from_file_location("gen_cmd_skill_hook_map", SCRIPT)
gen_map = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
assert _spec.loader is not None
_spec.loader.exec_module(gen_map)  # type: ignore[union-attr]

_SHIM = 'bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\"'


def _build_fake_repo(root: Path) -> None:
    """Minimal repo tree exercising every derivation rule."""
    # --- commands ---
    cmds = root / ".claude/commands"
    cmds.mkdir(parents=True)
    (cmds / "alpha.md").write_text(
        "---\ndescription: alpha cmd\n---\n\n"
        "Spawn with the `demo-skill` skill loaded. Run\n"
        "`python3 .claude/scripts/demo.py` (tests live at\n"
        ".claude/scripts/tests/test_demo.py). `not-a-skill` is prose.\n")
    (cmds / "beta.md").write_text(
        "---\ndescription: beta cmd\n---\n\n"
        "Reads .claude/skills/core/demo-skill/SKILL.md before acting.\n")
    # --- skills ---
    demo = root / ".claude/skills/core/demo-skill"
    demo.mkdir(parents=True)
    (demo / "SKILL.md").write_text(
        "---\nname: demo-skill\nactivation_triggers:\n"
        "  - {event: plan-opened}\n  - {event: help-me-invoked}\n---\nbody\n")
    (root / ".claude/skills/core/no-skill-md-dir").mkdir(parents=True)
    fe = root / ".claude/skills/frontend/fe-skill"
    fe.mkdir(parents=True)
    (fe / "SKILL.md").write_text("---\nname: fe-skill\n---\nbody\n")
    dom = root / ".claude/skills/domains/dom1/skills/domain-skill"
    dom.mkdir(parents=True)
    (dom / "SKILL.md").write_text("---\nname: domain-skill\n---\nbody\n")
    # --- hooks + settings (events deliberately NOT in sorted order) ---
    hooks = root / ".claude/hooks"
    hooks.mkdir(parents=True)
    (hooks / "guard_skills.py").write_text(
        '"""guards .claude/skills SKILL.md and .claude/commands surfaces"""\n')
    settings = {
        "hooks": {
            "Stop": [
                {"matcher": "", "hooks": [
                    {"type": "command",
                     "command": "echo '{\"decision\":\"allow\"}'",
                     "timeout": 5}]},
            ],
            "PreToolUse": [
                {"matcher": "Edit|Write", "hooks": [
                    {"type": "command",
                     "command": _SHIM + " guard_skills.py", "timeout": 7}]},
            ],
            "PostToolUse": [
                {"matcher": "Agent", "hooks": [
                    {"type": "command",
                     "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/ghost.py"'}]},
            ],
        }
    }
    (root / ".claude/settings.json").write_text(json.dumps(settings, indent=2))


class _FakeRepoTest(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        self.repo = Path(tempfile.mkdtemp(prefix="ceo-cmd-map-test-"))
        _build_fake_repo(self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)
        super().tearDown()


class TestDeterministicGeneration(_FakeRepoTest):
    def test_double_generation_byte_identical(self) -> None:
        self.assertEqual(gen_map.generate(self.repo), gen_map.generate(self.repo))

    def test_trailing_newline_no_dates(self) -> None:
        text = gen_map.generate(self.repo)
        self.assertTrue(text.endswith("\n"))
        self.assertFalse(text.endswith("\n\n"), "single trailing newline")
        self.assertNotRegex(text, r"20\d\d-\d\d-\d\d",
                            "date-like token breaks determinism contract")

    def test_write_doc_rewrite_idempotent(self) -> None:
        first = gen_map.write_doc(self.repo).read_bytes()
        self.assertEqual(gen_map.write_doc(self.repo).read_bytes(), first)


class TestEdgeDerivation(_FakeRepoTest):
    def setUp(self) -> None:
        super().setUp()
        self.text = gen_map.generate(self.repo)

    def test_command_to_skill_backtick_and_path(self) -> None:
        self.assertIn("| `/alpha` | `demo-skill` |", self.text)
        self.assertIn("| `/beta` | `demo-skill` |", self.text)  # path-segment ref
        self.assertNotIn("not-a-skill", self.text.split("## 2.")[0].split("## 1.")[1])

    def test_reverse_index_row(self) -> None:
        self.assertIn("| `demo-skill` | core | `/alpha`, `/beta` |", self.text)

    def test_script_refs_exclude_tests_tree(self) -> None:
        self.assertIn("`.claude/scripts/demo.py`", self.text)
        self.assertNotIn(".claude/scripts/tests/test_demo.py", self.text)

    def test_hook_rows_sorted_events_escaped_matcher(self) -> None:
        rows_section = self.text.split("## 3.")[1].split("## 4.")[0]
        i_post = rows_section.index("| PostToolUse |")
        i_pre = rows_section.index("| PreToolUse |")
        i_stop = rows_section.index("| Stop |")
        self.assertLess(i_post, i_pre)
        self.assertLess(i_pre, i_stop)
        self.assertIn("| PreToolUse | `Edit\\|Write` | `guard_skills.py` | 7 |",
                      rows_section)
        self.assertIn("| Stop | `(all)` | `(inline)` | 5 |", rows_section)
        self.assertIn("| PostToolUse | `Agent` | `ghost.py` | — |", rows_section)

    def test_surface_guards_and_unresolved(self) -> None:
        surf = self.text.split("## 4.")[1].split("## 5.")[0]
        self.assertIn("Skill files", surf)
        self.assertIn("`guard_skills.py`", surf)
        self.assertIn("Command files", surf)
        self.assertIn("unresolved, honest gap", surf)
        self.assertIn("`ghost.py`", surf)

    def test_totals_section(self) -> None:
        totals = self.text.split("## 5.")[1]
        self.assertIn("- Commands: 2", totals)
        self.assertIn("Skills (SKILL.md-bearing dirs): 3 — core 1, frontend 1, "
                      "domain 1 (across 1 domains)", totals)
        self.assertIn("- Skills with >=1 `activation_triggers` entry: 1", totals)

    def test_trigger_count_parse(self) -> None:
        catalog = {c["slug"]: c for c in gen_map.load_skill_catalog(self.repo)}
        self.assertEqual(catalog["demo-skill"]["triggers"], 2)
        self.assertEqual(catalog["fe-skill"]["triggers"], 0)
        self.assertEqual(catalog["domain-skill"]["tier"], "domain:dom1")
        self.assertNotIn("no-skill-md-dir", catalog)


class TestCheckGate(_FakeRepoTest):
    def _check(self) -> "tuple[int, str]":
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = gen_map.check(self.repo)
        return rc, buf.getvalue()

    def test_missing_doc_returns_one(self) -> None:
        rc, out = self._check()
        self.assertEqual(rc, 1)
        self.assertIn("missing", out)

    def test_clean_roundtrip_returns_zero(self) -> None:
        gen_map.write_doc(self.repo)
        rc, out = self._check()
        self.assertEqual(rc, 0, out)
        self.assertIn("in sync", out)

    def test_planted_drift_returns_one_with_diff(self) -> None:
        doc = gen_map.write_doc(self.repo)
        doc.write_text(doc.read_text().replace("`demo-skill`", "`tampered`"))
        rc, out = self._check()
        self.assertEqual(rc, 1)
        self.assertIn("DRIFT", out)
        self.assertIn("+++ generated/docs/COMMAND-SKILL-HOOK-MAP.md", out)
        self.assertIn("--write", out)  # remediation hint

    def test_check_mode_writes_nothing(self) -> None:
        gen_map.write_doc(self.repo)
        before = sorted(str(p) for p in self.repo.rglob("*"))
        self._check()
        after = sorted(str(p) for p in self.repo.rglob("*"))
        self.assertEqual(before, after, "--check must not create/remove files")

    def test_stale_after_tree_change_is_drift(self) -> None:
        gen_map.write_doc(self.repo)
        (self.repo / ".claude/commands/gamma.md").write_text(
            "---\ndescription: new\n---\nbody\n")
        rc, out = self._check()
        self.assertEqual(rc, 1, "new command must invalidate the committed doc")


class TestCliSurface(_FakeRepoTest):
    def _main(self, *args: str) -> "tuple[int, str]":
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = gen_map.main(list(args) + ["--repo", str(self.repo)])
        return rc, buf.getvalue()

    def test_default_emits_to_stdout(self) -> None:
        rc, out = self._main()
        self.assertEqual(rc, 0)
        self.assertIn("# COMMAND → SKILL → HOOK map", out)

    def test_write_then_check_roundtrip(self) -> None:
        rc_w, _ = self._main("--write")
        self.assertEqual(rc_w, 0)
        rc_c, _ = self._main("--check")
        self.assertEqual(rc_c, 0)

    def test_check_and_write_mutually_exclusive(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stderr(io.StringIO()):
                gen_map.main(["--check", "--write", "--repo", str(self.repo)])
        self.assertEqual(ctx.exception.code, 2)


class TestLiveRepoSync(TestEnvContext):
    """Read-only: committed docs/COMMAND-SKILL-HOOK-MAP.md must match the
    generator — the exact assertion the CI --check step makes."""

    def test_committed_doc_in_sync(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = gen_map.check(REPO)
        self.assertEqual(
            rc, 0,
            "docs/COMMAND-SKILL-HOOK-MAP.md drifted from the generator — run "
            "`python3 .claude/scripts/gen-command-skill-hook-map.py --write` "
            "and commit:\n" + buf.getvalue())

    def test_live_generation_deterministic(self) -> None:
        self.assertEqual(gen_map.generate(REPO), gen_map.generate(REPO))


if __name__ == "__main__":
    unittest.main()
