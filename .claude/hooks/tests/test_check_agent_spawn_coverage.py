"""In-process coverage uplift for check_agent_spawn.py.

PLAN-112-FOLLOWUP-coverage-doctrine-reconcile (S157) / ADR-139 Tier-1.

check_agent_spawn.py is the largest hook; its GOAP-deferred-outcome,
persona-coverage, audit-tail and env-resolver helpers (advisory, best-
effort emit functions) are not reached by the subprocess governance
suite. These tests drive them in-process with crafted inputs + an
isolated audit log.
"""

from __future__ import annotations

import json
import os
import time
import unittest
from pathlib import Path
from unittest import mock

from _lib.testing import TestEnvContext  # noqa: E402

import check_agent_spawn as cas  # noqa: E402


class AuditPathAndTsTest(TestEnvContext):

    def test_audit_log_path_normal(self):
        # TestEnvContext sets CEO_AUDIT_LOG_PATH; resolver should yield a path.
        self.assertIsNotNone(cas._audit_log_path())

    def test_audit_log_path_fallback_env_path(self):
        with mock.patch("_lib.audit_emit._log_path", side_effect=RuntimeError("x")):
            self.assertIsNotNone(cas._audit_log_path())

    def test_audit_log_path_fallback_dir(self):
        with mock.patch("_lib.audit_emit._log_path", side_effect=RuntimeError("x")), \
                mock.patch.dict(os.environ,
                                {"CEO_AUDIT_LOG_PATH": "",
                                 "CEO_AUDIT_LOG_DIR": str(self.audit_dir)}):
            p = cas._audit_log_path()
        self.assertIsNotNone(p)

    def test_audit_log_path_fallback_none(self):
        with mock.patch("_lib.audit_emit._log_path", side_effect=RuntimeError("x")), \
                mock.patch.dict(os.environ,
                                {"CEO_AUDIT_LOG_PATH": "", "CEO_AUDIT_LOG_DIR": ""}):
            self.assertIsNone(cas._audit_log_path())

    def test_parse_event_ts_variants(self):
        self.assertIsNone(cas._parse_event_ts(None))
        self.assertEqual(cas._parse_event_ts(123.5), 123.5)
        self.assertEqual(cas._parse_event_ts("456.7"), 456.7)
        self.assertIsNone(cas._parse_event_ts(""))
        self.assertIsNone(cas._parse_event_ts("not-a-date"))
        self.assertIsNone(cas._parse_event_ts([]))
        iso = cas._parse_event_ts("2026-05-23T08:00:00Z")
        self.assertIsInstance(iso, float)

    def test_resolve_session_id_from_env(self):
        self.assertEqual(cas._resolve_session_id_from_env({"CLAUDE_SESSION_ID": "abc"}), "abc")
        self.assertEqual(cas._resolve_session_id_from_env({"CEO_SESSION_ID": "def"}), "def")
        self.assertEqual(cas._resolve_session_id_from_env({}), "")

    def test_resolve_project_from_env(self):
        self.assertEqual(
            cas._resolve_project_from_env({"CLAUDE_PROJECT_DIR": "/a/b/myproj"}),
            "myproj")
        self.assertEqual(cas._resolve_project_from_env({}), "")


class TailRecentRenderedTest(TestEnvContext):

    def _write_log(self, events):
        log = self.audit_dir / "audit-log.jsonl"
        with log.open("w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")
        return log

    def test_no_log_returns_none(self):
        # audit dir exists but no log file written yet.
        log = self.audit_dir / "audit-log.jsonl"
        if log.exists():
            log.unlink()
        self.assertIsNone(cas._tail_recent_rendered("PLAN-999"))

    def test_match_recent(self):
        now = time.time()
        self._write_log([
            {"action": "goap_recommendation_rendered", "plan_id": "PLAN-999",
             "ts": now, "action_ids_csv": "A1,A2", "session_id": "s1"},
        ])
        ev = cas._tail_recent_rendered("PLAN-999")
        self.assertIsNotNone(ev)
        self.assertEqual(ev["plan_id"], "PLAN-999")

    def test_no_plan_match(self):
        now = time.time()
        self._write_log([
            {"action": "goap_recommendation_rendered", "plan_id": "PLAN-111",
             "ts": now, "action_ids_csv": "A1"},
        ])
        self.assertIsNone(cas._tail_recent_rendered("PLAN-999"))

    def test_session_filter_mismatch(self):
        now = time.time()
        self._write_log([
            {"action": "goap_recommendation_rendered", "plan_id": "PLAN-999",
             "ts": now, "action_ids_csv": "A1", "session_id": "other"},
        ])
        self.assertIsNone(cas._tail_recent_rendered("PLAN-999", session_id="s1"))

    def test_stale_ts_skipped(self):
        old = time.time() - 100000
        self._write_log([
            {"action": "goap_recommendation_rendered", "plan_id": "PLAN-999",
             "ts": old, "action_ids_csv": "A1"},
        ])
        self.assertIsNone(cas._tail_recent_rendered("PLAN-999"))


class PersonaCoverageEmitTest(TestEnvContext):

    def test_bypass_env(self):
        with mock.patch.dict(os.environ, {"CEO_PERSONA_COVERAGE_EMIT": "0"}):
            cas._emit_persona_coverage_synthesized(
                "code-reviewer", "review this", "", "spawn", dict(os.environ))

    def test_non_floor_archetype_skips(self):
        cas._emit_persona_coverage_synthesized(
            "devops", "review this", "", "spawn", dict(os.environ))

    def test_floor_archetype_with_keyword_emits(self):
        cas._emit_persona_coverage_synthesized(
            "security-engineer", "please audit the auth", "", "spawn",
            dict(os.environ))

    def test_floor_archetype_no_keyword_skips(self):
        cas._emit_persona_coverage_synthesized(
            "qa-architect", "do something generic", "no signal here", "spawn",
            dict(os.environ))


class GoapDeferredOutcomeTest(TestEnvContext):

    def _write_rendered(self, plan_id, csv, session_id=None):
        log = self.audit_dir / "audit-log.jsonl"
        ev = {"action": "goap_recommendation_rendered", "plan_id": plan_id,
              "ts": time.time(), "action_ids_csv": csv}
        if session_id:
            ev["session_id"] = session_id
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev) + "\n")

    def test_no_plan_id_noop(self):
        cas._emit_goap_deferred_outcome(None, "A1", dict(os.environ))

    def test_kill_switch_noop(self):
        env = dict(os.environ)
        env["CEO_GOAP_ADVISORY_ENABLED"] = "0"
        cas._emit_goap_deferred_outcome("PLAN-999", "A1", env)

    def test_import_fail_noop(self):
        with mock.patch.dict("sys.modules", {"_lib.audit_emit": None}):
            cas._emit_goap_deferred_outcome("PLAN-999", "A1", dict(os.environ))

    def test_diag_force_accept(self):
        env = dict(os.environ)
        env["CEO_GOAP_OVERRIDE_DETECTION_DISABLED"] = "1"
        cas._emit_goap_deferred_outcome("PLAN-999", "A1", env)

    def test_no_render_prior_overridden(self):
        # No rendered event in log -> overridden:no_render_prior
        cas._emit_goap_deferred_outcome("PLAN-NOPE", "A1", dict(os.environ))

    def test_marker_absent_overridden(self):
        self._write_rendered("PLAN-999", "A1,A2")
        cas._emit_goap_deferred_outcome("PLAN-999", None, dict(os.environ))

    def test_accepted_when_action_in_rendered(self):
        self._write_rendered("PLAN-999", "A1,A2")
        cas._emit_goap_deferred_outcome("PLAN-999", "A1", dict(os.environ))

    def test_substituted_when_action_not_in_rendered(self):
        self._write_rendered("PLAN-999", "A1,A2")
        cas._emit_goap_deferred_outcome("PLAN-999", "A9", dict(os.environ))


class AdvisoryRoutingTest(TestEnvContext):

    def setUp(self):
        super().setUp()
        cas._FRONTMATTER_MODEL_CACHE.clear()

    def _agent_file(self, name, model=None):
        d = Path(self.project_dir) / ".claude" / "agents"
        d.mkdir(parents=True, exist_ok=True)
        fm = ["---", f"name: {name}"]
        if model:
            fm.append(f"model: {model}")
        fm += ["---", "Body text."]
        (d / f"{name}.md").write_text("\n".join(fm) + "\n", encoding="utf-8")
        return d

    def test_resolve_task_route_returns(self):
        # Resolves the real repo task-route.py via the _HOOKS_DIR walk-up.
        cas._resolve_task_route()  # must not raise

    def test_extract_archetype_from_payload(self):
        self.assertEqual(
            cas._extract_archetype_from_payload("d", "p", "Security-Engineer"),
            "security-engineer")
        self.assertEqual(
            cas._extract_archetype_from_payload(
                "d", "role: qa-architect\n...", ""),
            "qa-architect")
        self.assertEqual(cas._extract_archetype_from_payload("d", "p", ""), "")

    def test_read_frontmatter_model_present(self):
        agents = self._agent_file("security-engineer", model="claude-opus-4-8")
        model, conf = cas._read_archetype_model_frontmatter(
            "security-engineer", agents)
        self.assertEqual(model, "claude-opus-4-8")
        self.assertEqual(conf, 1.0)
        # Second call exercises the cache fast-path.
        self.assertEqual(
            cas._read_archetype_model_frontmatter("security-engineer", agents),
            (model, conf))

    def test_read_frontmatter_no_model(self):
        agents = self._agent_file("qa-architect", model=None)
        model, conf = cas._read_archetype_model_frontmatter(
            "qa-architect", agents)
        self.assertIsNone(model)
        self.assertEqual(conf, 0.0)

    def test_read_frontmatter_missing_file(self):
        agents = Path(self.project_dir) / ".claude" / "agents"
        agents.mkdir(parents=True, exist_ok=True)
        model, conf = cas._read_archetype_model_frontmatter("ghost", agents)
        self.assertIsNone(model)
        self.assertEqual(conf, 0.0)

    def test_emit_model_routing_bypass(self):
        env = dict(os.environ)
        env["CEO_MODEL_ROUTING"] = "0"
        cas._emit_model_routing_advisory(
            description="d", prompt="p", subagent_type="security-engineer",
            env=env)

    def test_emit_model_routing_no_archetype(self):
        env = dict(os.environ)
        env.pop("CEO_MODEL_ROUTING", None)
        cas._emit_model_routing_advisory(
            description="generic", prompt="no header", subagent_type="", env=env)

    def test_emit_model_routing_frontmatter_path(self):
        self._agent_file("security-engineer", model="claude-opus-4-8")
        env = dict(os.environ)
        env.pop("CEO_MODEL_ROUTING", None)
        cas._emit_model_routing_advisory(
            description="review", prompt="p", subagent_type="security-engineer",
            env=env, project_dir=str(self.project_dir))

    def test_emit_model_routing_classify_path(self):
        # No agent frontmatter -> falls through to the classify branch.
        env = dict(os.environ)
        env.pop("CEO_MODEL_ROUTING", None)
        cas._emit_model_routing_advisory(
            description="review the auth code", prompt="p",
            subagent_type="security-engineer", env=env,
            project_dir=str(self.project_dir))


if __name__ == "__main__":
    unittest.main()
