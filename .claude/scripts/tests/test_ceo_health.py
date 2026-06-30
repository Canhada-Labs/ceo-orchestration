"""Unit tests for ceo-health.py.

Stdlib-only via unittest.discover. Builds a fake project tree with
``.claude/`` and runs run_checks() against it.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


def _load_module():
    here = Path(__file__).resolve().parent.parent
    src = here / "ceo-health.py"
    spec = importlib.util.spec_from_file_location("ceo_health", src)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


ch = _load_module()


def _build_project(root: Path, *, with_settings: bool = True, with_hooks: bool = True,
                   with_plans: bool = True, with_agents: bool = True,
                   bad_settings: bool = False, bad_plan: bool = False) -> None:
    """Create a minimal valid project skeleton."""
    (root / ".claude").mkdir(parents=True)

    if with_settings:
        settings = root / ".claude" / "settings.json"
        if bad_settings:
            settings.write_text("not valid json {", encoding="utf-8")
        else:
            settings.write_text(json.dumps({"hooks": {}}), encoding="utf-8")

    if with_hooks:
        hooks = root / ".claude" / "hooks"
        hooks.mkdir()
        # Required hook files (touch + chmod)
        for name in ch._REQUIRED_HOOKS:
            p = hooks / name
            p.write_text("# stub", encoding="utf-8")
            p.chmod(0o755)
        # python-shim
        shim = hooks / "_python-hook.sh"
        shim.write_text("#!/bin/bash\necho python3", encoding="utf-8")
        shim.chmod(0o755)

    if with_plans:
        plans = root / ".claude" / "plans"
        plans.mkdir()
        valid_plan = plans / "PLAN-001-test.md"
        valid_plan.write_text(
            "---\nid: PLAN-001\ntitle: Test plan\nstatus: draft\n---\n\nbody\n",
            encoding="utf-8",
        )
        if bad_plan:
            broken = plans / "PLAN-002-broken.md"
            broken.write_text("no frontmatter at all\n", encoding="utf-8")

    if with_agents:
        agents = root / ".claude" / "agents"
        agents.mkdir()
        for slug in ch._CANONICAL_AGENTS:
            p = agents / f"{slug}.md"
            p.write_text(
                f"---\nname: {slug}\nmodel: claude-opus-4-7\n---\nbody\n",
                encoding="utf-8",
            )
        (agents / "_dispatch.md").write_text("# dispatch\n", encoding="utf-8")


class HealthIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-health-test-")).resolve()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_healthy_project(self):
        _build_project(self.tmp)
        # Switch CWD so repo_root() finds .claude
        old_cwd = os.getcwd()
        os.chdir(self.tmp)
        try:
            results = ch.run_checks(self.tmp)
            status, exit_code = ch.overall_status(results)
            self.assertEqual(exit_code, 0)
            # All required hooks should be OK
            hook_results = [r for r in results if r.name.startswith("hook:") and r.advisory is False]
            for r in hook_results:
                self.assertEqual(r.status, "ok", f"required hook {r.name}: {r.message}")
            self.assertEqual(status, "healthy")
        finally:
            os.chdir(old_cwd)

    def test_unhealthy_on_bad_settings(self):
        _build_project(self.tmp, bad_settings=True)
        results = ch.run_checks(self.tmp)
        status, exit_code = ch.overall_status(results)
        self.assertEqual(exit_code, 1)
        self.assertEqual(status, "unhealthy")
        settings = next(r for r in results if r.name == "settings.json")
        self.assertEqual(settings.status, "fail")

    def test_unhealthy_on_missing_required_hook(self):
        _build_project(self.tmp)
        # Remove a required hook
        (self.tmp / ".claude" / "hooks" / "audit_log.py").unlink()
        results = ch.run_checks(self.tmp)
        status, exit_code = ch.overall_status(results)
        self.assertEqual(exit_code, 1)
        self.assertEqual(status, "unhealthy")

    def test_unhealthy_on_bad_plan_frontmatter(self):
        _build_project(self.tmp, bad_plan=True)
        results = ch.run_checks(self.tmp)
        plans_result = next(r for r in results if r.name == "plans")
        self.assertEqual(plans_result.status, "fail")

    def test_native_agents_required_when_present(self):
        _build_project(self.tmp)
        # Remove one canonical-5 agent
        (self.tmp / ".claude" / "agents" / "code-reviewer.md").unlink()
        results = ch.run_checks(self.tmp)
        agents_result = next(r for r in results if r.name == "native-agents")
        self.assertEqual(agents_result.status, "fail")
        self.assertIn("code-reviewer", agents_result.message)

    def test_render_text_contains_status_line(self):
        _build_project(self.tmp)
        results = ch.run_checks(self.tmp)
        status, _ = ch.overall_status(results)
        text = ch.render_text(results, status)
        self.assertIn("ceo-health:", text)
        self.assertIn(status.upper(), text)

    def test_render_json_parses(self):
        _build_project(self.tmp)
        results = ch.run_checks(self.tmp)
        status, _ = ch.overall_status(results)
        out = ch.render_json(results, status)
        payload = json.loads(out)
        self.assertEqual(payload["status"], status)
        self.assertIsInstance(payload["checks"], list)
        self.assertGreater(len(payload["checks"]), 0)


class HealthCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-health-cli-")).resolve()
        _build_project(self.tmp)
        self.old_cwd = os.getcwd()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, argv):
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            rc = ch.main(argv)
        finally:
            stdout = sys.stdout.getvalue()
            stderr = sys.stderr.getvalue()
            sys.stdout, sys.stderr = old_stdout, old_stderr
        return rc, stdout, stderr

    def test_cli_quiet_mode(self):
        rc, out, err = self._run(["--quiet"])
        # Healthy → exit 0, no output
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_cli_text_default(self):
        rc, out, err = self._run([])
        self.assertEqual(rc, 0)
        self.assertIn("ceo-health:", out)

    def test_cli_json_format(self):
        rc, out, err = self._run(["--format", "json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertIn("status", payload)
        self.assertIn("checks", payload)


if __name__ == "__main__":
    unittest.main()
