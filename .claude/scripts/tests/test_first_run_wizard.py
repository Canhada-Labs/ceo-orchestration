#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for PLAN-083 Wave 2 sub-agent 2.1 (first-run-wizard).

Stdlib-only unittest. ≥20 tests covering:
  - 4-step flow (detect / explain / recommend / ask)
  - YAML anchor/alias/tag/flow-map REJECTED (5 fixtures)
  - Path-traversal `../../etc/passwd` REJECTED
  - Confidence labels attached to recs
  - Quiet-mode env var respected
  - --no-interactive for CI
  - Idempotent re-run + --force
  - User response handling (Y / y / yes / "" default-Y / n / customize)
  - Unknown-profile -> exit 2 fail-CLOSED
  - Audit emit fields whitelisted (Sec MF-3)
"""

from __future__ import annotations

import importlib.util
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock


# ---------------------------------------------------------------------------
# Load the module under test from the sibling staging file (hyphenated name).
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_WIZARD_PATH = _HERE.parent / "first-run-wizard.py"
assert _WIZARD_PATH.is_file(), "first-run-wizard.py not found next to tests/"

_spec = importlib.util.spec_from_file_location("first_run_wizard", _WIZARD_PATH)
assert _spec is not None and _spec.loader is not None
wizard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wizard)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo_root(tmp: Path, profile_yaml: Optional[str]) -> Path:
    """Build a minimal repo root with .claude/repo-profile.yaml."""
    claude_dir = tmp / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    if profile_yaml is not None:
        (claude_dir / "repo-profile.yaml").write_text(profile_yaml, encoding="utf-8")
    return tmp


_DEFAULT_PROFILE = """\
risk_class: engine
detected_at: "2026-05-11T22:00:00Z"
confidence: high
signals:
  - "pyproject.toml:fastapi"
  - "dir:src/"
manual_override: false
created_at: "2026-05-11T22:00:00Z"
schema_version: "1"
"""


def _fake_resolver_factory(active_skills: List[str], suppressed: int = 5) -> Any:
    def _resolver(repo_root: Path, skill_glob: str = "**/SKILL.md") -> Dict[str, Any]:
        return {
            "profile": "engine",
            "active_count": len(active_skills),
            "suppressed_count": suppressed,
            "active_skills": list(active_skills),
            "context_total_tokens": 4000,
            "arbitration_dropped_count": 0,
            "max_active_cap": 12,
            "context_budget_cap": 30000,
            "audit_emit_payload": {
                "profile": "engine",
                "active_count": len(active_skills),
                "suppressed_count": suppressed,
                "context_total_tokens": 4000,
                "arbitration_dropped_count": 0,
            },
        }

    return _resolver


# ---------------------------------------------------------------------------
# YAML safety
# ---------------------------------------------------------------------------


class TestSafeLoadYaml(unittest.TestCase):
    """5 fixture YAML files with malicious patterns must be REJECTED."""

    def test_reject_anchor(self) -> None:
        bad = "risk_class: &anchor engine\n"
        with self.assertRaises(ValueError) as cm:
            wizard.safe_load_yaml(bad)
        self.assertIn("anchor", str(cm.exception).lower())

    def test_reject_alias(self) -> None:
        bad = "a: &x foo\nb: *x\n"
        with self.assertRaises(ValueError):
            wizard.safe_load_yaml(bad)

    def test_reject_tag(self) -> None:
        bad = 'risk_class: !!str "engine"\n'
        with self.assertRaises(ValueError):
            wizard.safe_load_yaml(bad)

    def test_reject_flow_map(self) -> None:
        bad = "risk_class: {a: 1, b: 2}\n"
        with self.assertRaises(ValueError):
            wizard.safe_load_yaml(bad)

    def test_reject_flow_seq_with_brace(self) -> None:
        # closing-brace alone in structural portion is rejected
        bad = 'risk_class: engine\nother: } broken\n'
        with self.assertRaises(ValueError):
            wizard.safe_load_yaml(bad)

    def test_accepts_quoted_glob_star(self) -> None:
        # "*" inside quotes is legit (e.g. "strategies/**").
        good = 'risk_class: engine\nmanual_review_paths:\n  - "strategies/**"\n'
        result = wizard.safe_load_yaml(good)
        self.assertEqual(result["risk_class"], "engine")
        self.assertEqual(result["manual_review_paths"], ["strategies/**"])


# ---------------------------------------------------------------------------
# Path-traversal guard
# ---------------------------------------------------------------------------


class TestPathTraversal(unittest.TestCase):
    def test_safe_resolve_rejects_nonexistent(self) -> None:
        with self.assertRaises(ValueError):
            wizard.safe_resolve_target("/nonexistent/__no__/__way__")

    def test_safe_resolve_rejects_null_byte(self) -> None:
        with self.assertRaises(ValueError):
            wizard.safe_resolve_target("/tmp/\x00evil")

    def test_safe_child_path_rejects_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            with self.assertRaises(ValueError) as cm:
                wizard.safe_child_path(repo, Path("/etc/passwd"))
            self.assertIn("traversal", str(cm.exception).lower())

    def test_safe_child_path_dotdot_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "inner"
            repo.mkdir()
            # Attempt to escape via ../../etc/passwd
            with self.assertRaises(ValueError):
                wizard.safe_child_path(repo, repo / ".." / ".." / "etc" / "passwd")

    def test_safe_child_path_accepts_under_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / ".claude").mkdir()
            ok = wizard.safe_child_path(repo, repo / ".claude" / "repo-profile.yaml")
            self.assertTrue(str(ok).startswith(str(repo.resolve())))


# ---------------------------------------------------------------------------
# Step 1 — detect
# ---------------------------------------------------------------------------


class TestStepDetect(unittest.TestCase):
    def test_unknown_profile_exits_2(self) -> None:
        bad = (
            'risk_class: unknown-needs-owner-confirmation\n'
            'detected_at: "2026-05-11T22:00:00Z"\n'
            'confidence: low\n'
            'signals: []\n'
            'manual_override: false\n'
            'created_at: "2026-05-11T22:00:00Z"\n'
            'schema_version: "1"\n'
        )
        with tempfile.TemporaryDirectory() as td:
            repo = _make_repo_root(Path(td), bad)
            buf = io.StringIO()
            rc, prof = wizard.step_detect(repo, stdout=buf, emit_info=lambda _: None)
            self.assertEqual(rc, 2)
            self.assertIn("confirm-profile", buf.getvalue())

    def test_known_profile_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_repo_root(Path(td), _DEFAULT_PROFILE)
            buf = io.StringIO()
            rc, prof = wizard.step_detect(repo, stdout=buf, emit_info=lambda _: None)
            self.assertEqual(rc, 0)
            self.assertEqual(prof["risk_class"], "engine")

    def test_missing_profile_returns_4(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_repo_root(Path(td), None)
            buf = io.StringIO()
            rc, prof = wizard.step_detect(repo, stdout=buf, emit_info=lambda _: None)
            self.assertEqual(rc, 4)


# ---------------------------------------------------------------------------
# Step 2 — explain
# ---------------------------------------------------------------------------


class TestStepExplain(unittest.TestCase):
    def test_explanation_references_resolver_skills(self) -> None:
        profile = {"risk_class": "engine", "confidence": "high"}
        resolve_result = {
            "active_skills": [
                "core/code-review/SKILL.md",
                "core/security-review/SKILL.md",
            ],
            "active_count": 2,
            "suppressed_count": 3,
        }
        buf = io.StringIO()
        wizard.step_explain(profile, resolve_result, stdout=buf)
        text = buf.getvalue()
        self.assertIn("engine", text)
        self.assertIn("HIGH", text)
        self.assertIn("core/code-review/SKILL.md", text)
        self.assertIn("Read-only mode for first 7 days", text)
        self.assertIn("Override via", text)


# ---------------------------------------------------------------------------
# Step 3 — recommend
# ---------------------------------------------------------------------------


class TestStepRecommend(unittest.TestCase):
    def test_top_3_recommendations(self) -> None:
        resolve_result = {
            "active_skills": [
                "core/a/SKILL.md",
                "core/b/SKILL.md",
                "core/c/SKILL.md",
                "core/d/SKILL.md",
            ],
        }
        buf = io.StringIO()
        recs = wizard.step_recommend("engine", resolve_result, stdout=buf)
        self.assertEqual(len(recs), 3)
        for r in recs:
            self.assertIn("marker", r)
            self.assertIn("skill_path", r)
            self.assertIn("rationale", r)

    def test_empty_resolves_to_onboard_fallback(self) -> None:
        resolve_result = {"active_skills": []}
        buf = io.StringIO()
        recs = wizard.step_recommend("engine", resolve_result, stdout=buf)
        self.assertEqual(recs, [])
        self.assertIn("/onboard", buf.getvalue())

    def test_confidence_marker_attached_to_each(self) -> None:
        resolve_result = {"active_skills": ["core/x/SKILL.md"] * 3}
        buf = io.StringIO()
        recs = wizard.step_recommend("engine", resolve_result, stdout=buf)
        self.assertEqual(len(recs), 3)
        for r in recs:
            self.assertIn(
                r["marker"],
                ("[SAFE]", "[NEEDS-CONFIRM]", "[RISKY]"),
            )

    def test_trading_profile_bumps_marker(self) -> None:
        resolve_result = {"active_skills": ["core/x/SKILL.md"] * 3}
        buf = io.StringIO()
        recs = wizard.step_recommend("trading-readonly", resolve_result, stdout=buf)
        for r in recs:
            self.assertEqual(r["marker"], "[NEEDS-CONFIRM]")


# ---------------------------------------------------------------------------
# Step 4 — ask (user response variants)
# ---------------------------------------------------------------------------


class TestStepAsk(unittest.TestCase):
    def _run_ask(
        self, response: str, non_interactive: bool = False
    ) -> Any:
        recs = [
            {"skill_path": "core/a/SKILL.md", "marker": "[SAFE]", "rationale": "r"},
        ]
        stdin = io.StringIO(response)
        stdout = io.StringIO()
        return wizard.step_ask(
            "engine",
            recs,
            stdin=stdin,
            stdout=stdout,
            non_interactive=non_interactive,
        )

    def test_accept_y(self) -> None:
        action, chosen = self._run_ask("y\n")
        self.assertEqual(action, "accepted")
        self.assertEqual(len(chosen), 1)

    def test_accept_yes(self) -> None:
        action, _ = self._run_ask("yes\n")
        self.assertEqual(action, "accepted")

    def test_accept_default_empty(self) -> None:
        action, chosen = self._run_ask("\n")
        self.assertEqual(action, "accepted")
        self.assertEqual(len(chosen), 1)

    def test_decline_n(self) -> None:
        action, chosen = self._run_ask("n\n")
        self.assertEqual(action, "declined")
        self.assertEqual(chosen, [])

    def test_decline_no(self) -> None:
        action, _ = self._run_ask("no\n")
        self.assertEqual(action, "declined")

    def test_non_interactive_defaults_accept(self) -> None:
        action, chosen = self._run_ask("", non_interactive=True)
        self.assertEqual(action, "accepted")
        self.assertEqual(len(chosen), 1)

    def test_eof_declines(self) -> None:
        action, chosen = self._run_ask("")  # EOF -> readline returns ""
        self.assertEqual(action, "declined")
        self.assertEqual(chosen, [])

    def test_customize_toggles_off_then_done(self) -> None:
        recs = [
            {"skill_path": "core/a/SKILL.md", "marker": "[SAFE]", "rationale": "r"},
            {"skill_path": "core/b/SKILL.md", "marker": "[SAFE]", "rationale": "r"},
            {"skill_path": "core/c/SKILL.md", "marker": "[SAFE]", "rationale": "r"},
        ]
        # Pick "customize", toggle off index 2, then done.
        stdin = io.StringIO("customize\n2\ndone\n")
        stdout = io.StringIO()
        action, chosen = wizard.step_ask(
            "engine",
            recs,
            stdin=stdin,
            stdout=stdout,
            non_interactive=False,
        )
        self.assertEqual(action, "customized")
        paths = [c["skill_path"] for c in chosen]
        self.assertNotIn("core/b/SKILL.md", paths)
        self.assertEqual(len(chosen), 2)


# ---------------------------------------------------------------------------
# Quiet-mode env var respected
# ---------------------------------------------------------------------------


class TestQuietMode(unittest.TestCase):
    def test_default_is_quiet(self) -> None:
        self.assertTrue(wizard.is_quiet_mode({}))

    def test_explicit_1_is_quiet(self) -> None:
        self.assertTrue(wizard.is_quiet_mode({"CEO_QUIET_MODE": "1"}))

    def test_explicit_0_is_not_quiet(self) -> None:
        self.assertFalse(wizard.is_quiet_mode({"CEO_QUIET_MODE": "0"}))

    def test_emitter_suppresses_when_quiet(self) -> None:
        buf = io.StringIO()
        emit = wizard.make_emitter(buf, quiet=True)
        emit("info noise")
        self.assertEqual(buf.getvalue(), "")

    def test_emitter_prints_when_loud(self) -> None:
        buf = io.StringIO()
        emit = wizard.make_emitter(buf, quiet=False)
        emit("info loud")
        self.assertIn("info loud", buf.getvalue())


# ---------------------------------------------------------------------------
# cmd_run end-to-end (with fake resolver injection)
# ---------------------------------------------------------------------------


class TestCmdRunEndToEnd(unittest.TestCase):
    def test_happy_path_writes_completion(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_repo_root(Path(td), _DEFAULT_PROFILE)
            stdin = io.StringIO("y\n")
            stdout = io.StringIO()
            rc = wizard.cmd_run(
                repo,
                non_interactive=False,
                force=False,
                emit_json=False,
                stdin=stdin,
                stdout=stdout,
                resolver_fn=_fake_resolver_factory([
                    "core/code-review/SKILL.md",
                    "core/security-review/SKILL.md",
                    "core/onboard/SKILL.md",
                ]),
            )
            self.assertEqual(rc, 0)
            wcp = repo / ".claude" / "wizard-completed.yaml"
            self.assertTrue(wcp.is_file())
            parsed = wizard.safe_load_yaml(wcp.read_text(encoding="utf-8"))
            self.assertEqual(parsed["profile"], "engine")
            self.assertEqual(parsed["user_action"], "accepted")
            self.assertEqual(parsed["recommendation_count"], 3)

    def test_idempotent_rerun_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_repo_root(Path(td), _DEFAULT_PROFILE)
            # Pre-create wizard-completed.yaml.
            (repo / ".claude" / "wizard-completed.yaml").write_text(
                'profile: "engine"\nuser_action: "accepted"\n', encoding="utf-8"
            )
            stdout = io.StringIO()
            rc = wizard.cmd_run(
                repo,
                non_interactive=True,
                force=False,
                emit_json=False,
                stdin=io.StringIO(""),
                stdout=stdout,
                resolver_fn=_fake_resolver_factory(["core/a/SKILL.md"] * 3),
            )
            self.assertEqual(rc, 0)
            self.assertIn("already present", stdout.getvalue())
            self.assertIn("--force", stdout.getvalue())

    def test_force_rerun_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_repo_root(Path(td), _DEFAULT_PROFILE)
            wcp = repo / ".claude" / "wizard-completed.yaml"
            wcp.write_text('profile: "old"\n', encoding="utf-8")
            stdin = io.StringIO("y\n")
            stdout = io.StringIO()
            rc = wizard.cmd_run(
                repo,
                non_interactive=False,
                force=True,
                emit_json=False,
                stdin=stdin,
                stdout=stdout,
                resolver_fn=_fake_resolver_factory(["core/a/SKILL.md"] * 3),
            )
            self.assertEqual(rc, 0)
            new = wizard.safe_load_yaml(wcp.read_text(encoding="utf-8"))
            self.assertEqual(new["profile"], "engine")

    def test_empty_resolver_returns_1(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_repo_root(Path(td), _DEFAULT_PROFILE)
            stdout = io.StringIO()
            rc = wizard.cmd_run(
                repo,
                non_interactive=True,
                force=False,
                emit_json=False,
                stdin=io.StringIO(""),
                stdout=stdout,
                resolver_fn=_fake_resolver_factory([]),
            )
            self.assertEqual(rc, 1)
            self.assertIn("/onboard", stdout.getvalue())

    def test_decline_does_not_write_completion(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_repo_root(Path(td), _DEFAULT_PROFILE)
            stdin = io.StringIO("n\n")
            stdout = io.StringIO()
            rc = wizard.cmd_run(
                repo,
                non_interactive=False,
                force=False,
                emit_json=False,
                stdin=stdin,
                stdout=stdout,
                resolver_fn=_fake_resolver_factory(["core/a/SKILL.md"] * 3),
            )
            self.assertEqual(rc, 0)
            wcp = repo / ".claude" / "wizard-completed.yaml"
            self.assertFalse(wcp.is_file())


# ---------------------------------------------------------------------------
# Audit-emit whitelist (Sec MF-3)
# ---------------------------------------------------------------------------


class TestAuditWhitelist(unittest.TestCase):
    """Sec MF-3: only {profile, recommendation_count, user_action} leave."""

    def test_only_whitelisted_fields_pass(self) -> None:
        # Drive a subprocess where the wizard sits under a fake repo root
        # so the upward-walk in `emit_audit_first_run_wizard` finds our
        # fake `_lib.audit_emit`. We copy the wizard file into the fake
        # tree so its real `__file__` is under the tree.
        import shutil
        import subprocess
        import json as _json

        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td).resolve()
            # Fake hooks tree.
            hooks_lib = tdp / ".claude" / "hooks" / "_lib"
            hooks_lib.mkdir(parents=True)
            (hooks_lib / "__init__.py").write_text("", encoding="utf-8")
            audit_capture = tdp / "audit-capture.json"
            (hooks_lib / "audit_emit.py").write_text(
                "import json, os, pathlib\n"
                "def emit_generic(action, **kwargs):\n"
                "    p = pathlib.Path(os.environ['_TEST_AUDIT'])\n"
                "    p.write_text(json.dumps({'action': action, 'kwargs': kwargs}))\n",
                encoding="utf-8",
            )
            # Copy wizard into the fake tree so its __file__ is under it.
            scripts_dir = tdp / ".claude" / "scripts"
            scripts_dir.mkdir(parents=True)
            copied_wizard = scripts_dir / "first-run-wizard.py"
            shutil.copy2(_WIZARD_PATH, copied_wizard)

            shim = tdp / "shim.py"
            shim.write_text(
                "import importlib.util, sys\n"
                "spec = importlib.util.spec_from_file_location('wz', "
                + repr(str(copied_wizard))
                + ")\n"
                "m = importlib.util.module_from_spec(spec)\n"
                "spec.loader.exec_module(m)\n"
                "m.emit_audit_first_run_wizard({\n"
                "    'profile': 'engine',\n"
                "    'recommendation_count': 3,\n"
                "    'user_action': 'accepted',\n"
                "    'secret_path': '/etc/passwd',\n"
                "    'extra_field': 'leak',\n"
                "})\n",
                encoding="utf-8",
            )
            env = {**os.environ, "_TEST_AUDIT": str(audit_capture)}
            subprocess.check_call([sys.executable, str(shim)], env=env)
            self.assertTrue(audit_capture.is_file())
            data = _json.loads(audit_capture.read_text(encoding="utf-8"))
            self.assertEqual(data["action"], "first_run_wizard_completed")
            kwargs = data["kwargs"]
            self.assertEqual(
                set(kwargs.keys()),
                {"profile", "recommendation_count", "user_action"},
            )
            self.assertNotIn("secret_path", kwargs)
            self.assertNotIn("extra_field", kwargs)

    def test_whitelist_filter_pure_function(self) -> None:
        # Validate the filter logic itself in isolation (no subprocess).
        # We rebuild the filter inline so we don't depend on import side
        # effects.
        allowed = wizard._AUDIT_ALLOWED_FIELDS  # type: ignore[attr-defined]
        payload = {
            "profile": "engine",
            "recommendation_count": 3,
            "user_action": "accepted",
            "leaked_path": "/etc/passwd",
            "leaked_token": "sk-XXXXX",
        }
        filtered = {k: v for (k, v) in payload.items() if k in allowed}
        self.assertEqual(
            set(filtered.keys()),
            {"profile", "recommendation_count", "user_action"},
        )


# ---------------------------------------------------------------------------
# CLI argv plumbing
# ---------------------------------------------------------------------------


class TestCLI(unittest.TestCase):
    def test_path_traversal_via_target_rejected(self) -> None:
        rc = wizard.main([
            "run",
            "--target",
            "/tmp/__definitely_not__/__exists__/" + os.urandom(4).hex(),
        ])
        self.assertEqual(rc, 3)

    def test_show_returns_1_when_no_completion(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / ".claude").mkdir()
            rc = wizard.main(["show", "--target", td])
            self.assertEqual(rc, 1)


# ---------------------------------------------------------------------------
# emit_yaml round-trip
# ---------------------------------------------------------------------------


class TestYamlRoundTrip(unittest.TestCase):
    def test_emit_then_load(self) -> None:
        data = {
            "profile": "engine",
            "recommendation_count": 3,
            "recommendations": ["core/a/SKILL.md", "core/b/SKILL.md"],
            "user_action": "accepted",
            "wizard_version": "1",
            "completed_at": "2026-05-11T22:00:00Z",
        }
        text = wizard.emit_yaml(data)
        parsed = wizard.safe_load_yaml(text)
        self.assertEqual(parsed["profile"], "engine")
        self.assertEqual(parsed["recommendation_count"], 3)
        self.assertEqual(
            parsed["recommendations"], ["core/a/SKILL.md", "core/b/SKILL.md"]
        )


if __name__ == "__main__":
    unittest.main()
