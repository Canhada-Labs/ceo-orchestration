"""Unit tests for handlers/get_audit_log.py — limit + filter + redaction."""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

# Bootstrap sys.path.
_TESTS_DIR = Path(__file__).resolve().parent
_SERVER_DIR = _TESTS_DIR.parent
_CLAUDE_DIR = _SERVER_DIR.parent.parent
_HOOKS_DIR = _CLAUDE_DIR / "hooks"
for _p in (_HOOKS_DIR, _SERVER_DIR, _SERVER_DIR / "handlers"):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

from _lib.testing import TestEnvContext  # noqa: E402

from handlers import get_audit_log  # type: ignore[import-not-found]  # noqa: E402


def _seed_audit(audit_dir: Path, events: list) -> None:
    log = audit_dir / "audit-log.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


class TestGetAuditLog(TestEnvContext):

    def test_happy_path_action_filter(self):
        _seed_audit(
            self.audit_dir,
            [
                {"action": "agent_spawn", "ts": "2026-01-01T00:00:00Z", "id": 1},
                {"action": "debate_event", "ts": "2026-01-01T00:00:01Z", "id": 2},
                {"action": "agent_spawn", "ts": "2026-01-01T00:00:02Z", "id": 3},
            ],
        )
        result = get_audit_log.handle(
            params={"action_filter": "agent_spawn"},
            context={"project_dir": self.project_dir},
        )
        self.assertEqual(result["total_returned"], 2)
        for ev in result["events"]:
            self.assertEqual(ev["action"], "agent_spawn")

    def test_truncation_at_hard_cap(self):
        # Hard cap = 1000; over-large limits silently clamped.
        events = [
            {"action": "agent_spawn", "ts": f"2026-01-01T00:00:{i:02d}Z", "id": i}
            for i in range(60)
        ]
        _seed_audit(self.audit_dir, events)
        # Request 5 — should truncate.
        result = get_audit_log.handle(
            params={"limit": 5},
            context={"project_dir": self.project_dir},
        )
        self.assertEqual(result["total_returned"], 5)
        self.assertTrue(result["truncated"])

    def test_since_timestamp_filter(self):
        _seed_audit(
            self.audit_dir,
            [
                {"action": "agent_spawn", "ts": "2026-01-01T00:00:00Z", "id": 1},
                {"action": "agent_spawn", "ts": "2026-02-01T00:00:00Z", "id": 2},
                {"action": "agent_spawn", "ts": "2026-03-01T00:00:00Z", "id": 3},
            ],
        )
        result = get_audit_log.handle(
            params={"since": "2026-01-15T00:00:00Z"},
            context={"project_dir": self.project_dir},
        )
        ids = sorted(ev["id"] for ev in result["events"])
        self.assertEqual(ids, [2, 3])

    def test_secret_field_pruned_defensively(self):
        _seed_audit(
            self.audit_dir,
            [
                {
                    "action": "agent_spawn",
                    "ts": "2026-01-01T00:00:00Z",
                    "api_key": "should-be-removed",
                    "auth_token": "also-removed",
                    "preserved": "ok",
                }
            ],
        )
        result = get_audit_log.handle(
            params={}, context={"project_dir": self.project_dir}
        )
        ev = result["events"][0]
        self.assertNotIn("api_key", ev)
        self.assertNotIn("auth_token", ev)
        self.assertEqual(ev["preserved"], "ok")


if __name__ == "__main__":
    unittest.main()
