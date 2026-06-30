"""Unit tests for session-resume.py (PLAN-011 Phase 11).

Exercises:
- Prompt rendering has all required sections
- Missing plan → user-friendly error (exit 3, not a traceback)
- --json output parses and has expected shape
- Idempotency — same inputs produce same output modulo ts
- CEO_SOTA_DISABLE kill-switch
- Rebuild-on-stale-cache path

Uses TestEnvContext for HOME / CLAUDE_PROJECT_DIR isolation.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _SCRIPTS_DIR.parent.parent
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _load(mod_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        mod_name, _SCRIPTS_DIR / filename
    )
    m = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(m)
    return m


sgb = _load("session_graph_build", "session-graph-build.py")
srm = _load("session_resume", "session-resume.py")


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class SessionResumeTestBase(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        self.plans_dir = self.project_dir / ".claude" / "plans"
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        os.environ["CEO_PLANS_DIR"] = str(self.plans_dir)
        self.graph_dir = self.home_dir / ".claude" / "projects" / "test" / "session-graphs"
        os.environ["CEO_SESSION_GRAPH_DIR"] = str(self.graph_dir)
        os.environ["CEO_PROJECT_NAME"] = "test"

        # Write a sample plan file for PLAN-010
        plan = self.plans_dir / "PLAN-010-quality.md"
        plan.write_text(
            "---\n"
            "id: PLAN-010\n"
            "title: Sprint 10 Polish\n"
            "status: done\n"
            "created: 2026-04-14\n"
            "owner: CEO\n"
            "depends_on: []\n"
            "---\n"
            "\n"
            "## Phases\n"
            "- [x] Phase 1 — E2E harness\n"
            "- [x] Phase 8 — Closeout\n"
            "\n"
            "## Deferred to Sprint 11\n"
            "- Flip docs-freshness state\n"
            "\n"
            "## Owner action items\n"
            "- Tag v1.0.0-rc.1\n",
            encoding="utf-8",
        )

        # Seed audit fixture
        now = datetime.now(timezone.utc)
        events = [
            {
                "action": "agent_spawn",
                "plan_id": "PLAN-010",
                "session_id": "sess-1",
                "ts": _iso(now - timedelta(hours=2)),
            },
            {
                "action": "debate_event",
                "plan_id": "PLAN-010",
                "session_id": "sess-1",
                "round": 1,
                "phase": "consensus",
                "agent": "consensus",
                "ts": _iso(now - timedelta(hours=1)),
            },
        ]
        log = self.audit_dir / "audit-log.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
        )


class TestRenderText(SessionResumeTestBase):
    def test_text_output_has_required_sections(self) -> None:
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            rc = srm.main(["--plan", "PLAN-010"])
        self.assertEqual(rc, 0, f"stderr: {err.getvalue()}")
        text = buf.getvalue()
        # Required sections per task spec
        self.assertIn("# Resume PLAN-010", text)
        self.assertIn("## Last commit", text)
        self.assertIn("## Last phase", text)
        self.assertIn("## Open deferred", text)
        self.assertIn("## Owner action items", text)
        self.assertIn("## Recommended next action", text)
        # Expected content — title + deferred item + owner action
        self.assertIn("Sprint 10 Polish", text)
        self.assertIn("Flip docs-freshness state", text)
        self.assertIn("Tag v1.0.0-rc.1", text)


class TestJsonOutput(SessionResumeTestBase):
    def test_json_output_parses(self) -> None:
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            rc = srm.main(["--plan", "PLAN-010", "--json"])
        self.assertEqual(rc, 0, f"stderr: {err.getvalue()}")
        payload = json.loads(buf.getvalue())
        self.assertIn("source", payload)
        self.assertIn("projection", payload)
        proj = payload["projection"]
        self.assertEqual(proj["plan_id"], "PLAN-010")
        self.assertEqual(proj["plan_title"], "Sprint 10 Polish")
        self.assertEqual(proj["plan_status"], "done")
        self.assertIsInstance(proj["open_deferred"], list)
        self.assertIsInstance(proj["owner_actions"], list)
        self.assertIn("next_action", proj)
        # Source must be 'live' when no cached graph exists
        self.assertTrue(
            payload["source"] == "live"
            or payload["source"].startswith("disk:")
        )


class TestMissingPlan(SessionResumeTestBase):
    def test_missing_plan_exits_3(self) -> None:
        """An unknown plan ID must produce a user-friendly message on stderr
        and exit 3 — not a Python traceback."""
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            rc = srm.main(["--plan", "PLAN-999"])
        self.assertEqual(rc, 3)
        self.assertIn("not found", err.getvalue())
        # Traceback keyword must be absent — assert it rendered a
        # readable message instead.
        self.assertNotIn("Traceback", err.getvalue())

    def test_invalid_plan_id_exits_2(self) -> None:
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            rc = srm.main(["--plan", "bogus"])
        self.assertEqual(rc, 2)
        self.assertIn("PLAN-NNN", err.getvalue())


class TestIdempotency(SessionResumeTestBase):
    def test_same_output_modulo_timestamp(self) -> None:
        """Two back-to-back runs produce identical output modulo the
        generated_at timestamp in the graph."""
        def _run() -> dict:
            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(io.StringIO()):
                rc = srm.main(["--plan", "PLAN-010", "--json"])
            self.assertEqual(rc, 0)
            return json.loads(buf.getvalue())

        a = _run()
        b = _run()
        # Scrub fields that legitimately change between runs
        for payload in (a, b):
            p = payload["projection"]
            p["generated_at"] = "<scrubbed>"
            # next_action is derived from static inputs; stable across runs
        self.assertEqual(a["projection"], b["projection"])


class TestSotaDisable(SessionResumeTestBase):
    def test_disabled_returns_0_with_no_output(self) -> None:
        os.environ["CEO_SOTA_DISABLE"] = "1"
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            rc = srm.main(["--plan", "PLAN-010", "--json"])
        self.assertEqual(rc, 0)
        self.assertEqual(buf.getvalue(), "")
        self.assertEqual(err.getvalue(), "")


class TestRebuildFlag(SessionResumeTestBase):
    def test_rebuild_bypasses_cache(self) -> None:
        # Seed a fake-fresh plaintext cache (no encryption involved)
        self.graph_dir.mkdir(parents=True, exist_ok=True)
        stale_payload = {
            "plan_id": "PLAN-010",
            "plan_status": "done",
            "plan_title": "STALE CACHE TITLE",
            "generated_at": _iso(datetime.now(timezone.utc)),
            "last_phase_status": "Phase 99: stale",
            "sessions": [],
            "commits": [],
            "deferred": [],
            "owner_actions": [],
            "session_count": 0,
            "event_count": 0,
            "commit_count": 0,
        }
        # Name matches the discovery regex and has a fresh timestamp
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = self.graph_dir / f"PLAN-010-{ts}.json"
        path.write_text(json.dumps(stale_payload), encoding="utf-8")

        # WITHOUT --rebuild → expect cache to be used (STALE title surfaced)
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            rc = srm.main(["--plan", "PLAN-010", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertIn("disk:", payload["source"])
        self.assertEqual(
            payload["projection"]["plan_title"], "STALE CACHE TITLE"
        )

        # WITH --rebuild → fresh build reads the real plan
        buf2 = io.StringIO()
        with redirect_stdout(buf2), redirect_stderr(io.StringIO()):
            rc2 = srm.main(["--plan", "PLAN-010", "--json", "--rebuild"])
        self.assertEqual(rc2, 0)
        payload2 = json.loads(buf2.getvalue())
        self.assertEqual(payload2["source"], "live")
        self.assertEqual(
            payload2["projection"]["plan_title"], "Sprint 10 Polish"
        )


class TestNextActionSynthesis(SessionResumeTestBase):
    def test_next_action_for_done_plan(self) -> None:
        """Done plans surface a DONE message (fixture has status: done)."""
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            srm.main(["--plan", "PLAN-010", "--json"])
        payload = json.loads(buf.getvalue())
        self.assertIn("DONE", payload["projection"]["next_action"])

    def test_next_action_for_executing_plan_with_owner_actions(self) -> None:
        """An executing plan with owner_actions surfaces the 'Owner action' message."""
        # Rewrite the fixture plan to be executing + have owner actions
        plan = self.plans_dir / "PLAN-010-quality.md"
        plan.write_text(
            "---\n"
            "id: PLAN-010\n"
            "title: Sprint 10 Polish\n"
            "status: executing\n"
            "created: 2026-04-14\n"
            "owner: CEO\n"
            "depends_on: []\n"
            "---\n"
            "\n"
            "## Phases\n"
            "- [x] Phase 1 — done\n"
            "- [ ] Phase 2 — pending\n"
            "\n"
            "## Owner action items\n"
            "- Tag v1.0.0-rc.1\n",
            encoding="utf-8",
        )
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            srm.main(["--plan", "PLAN-010", "--json", "--rebuild"])
        payload = json.loads(buf.getvalue())
        self.assertIn(
            "Owner action required", payload["projection"]["next_action"]
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
