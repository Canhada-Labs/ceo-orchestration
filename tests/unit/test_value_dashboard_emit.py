"""PLAN-085 Wave D.3 — ``value_dashboard_summarized`` production callsite.

Verifies that the value-dashboard CLI emits a ``value_dashboard_summarized``
audit event on every invocation (the cross-link with Wave C.4 sub-2.4
allowlist gate). Sec MF-3 whitelist enforced inside emit_generic + the
CLI wraps the emit in fail-open.

  1. test_value_dashboard_main_emits_audit_event_on_invocation

Discipline: stdlib-only, Python >= 3.9, from __future__ annotations,
typing.Optional/Union.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOKS = REPO_ROOT / ".claude" / "hooks"
_SCRIPTS = REPO_ROOT / ".claude" / "scripts"
for _p in (_HOOKS, _SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


class TestValueDashboardEmit(unittest.TestCase):
    """Wave D.3 — production emit callsite contract."""

    def setUp(self) -> None:
        # Build an isolated audit-log fixture: one fresh dispatch event
        # so rollup_value has non-empty data + the emit_payload is fully
        # populated.
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.audit_dir = Path(self._tmp.name)
        self.log_path = self.audit_dir / "audit-log.jsonl"
        ts_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")
        events = [
            {
                "ts": ts_now,
                "action": "agent_spawn",
                "session_id": "S-D3",
                "tokens_in": 1000,
                "tokens_out": 500,
                "model": "claude-sonnet-4-5",
                "agent_name": "test-agent-D3",
            },
        ]
        with self.log_path.open("w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")

    def _load_dashboard(self):
        # value-dashboard.py is a script with a hyphen → not a normal
        # importable module name. Load via importlib.util.
        spec = importlib.util.spec_from_file_location(
            "_plan085_d3_value_dashboard",
            _SCRIPTS / "value-dashboard.py",
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod

    def test_value_dashboard_main_emits_audit_event_on_invocation(self) -> None:
        """``main()`` MUST call ``_emit_value_dashboard_summarized``."""
        vd = self._load_dashboard()

        captured: List[Dict[str, Any]] = []

        def _fake_emit(payload: Dict[str, Any]) -> None:
            captured.append(dict(payload))

        # Swallow stdout — we only care about the emit side effect.
        with mock.patch.object(
            vd, "_emit_value_dashboard_summarized", side_effect=_fake_emit
        ):
            with mock.patch.object(sys, "stdout", new_callable=io.StringIO):
                rc = vd.main(
                    [
                        "--period", "7d",
                        "--json",
                        "--audit-dir", str(self.audit_dir),
                    ]
                )

        self.assertEqual(rc, 0, "value-dashboard.main must return 0 on success")
        self.assertEqual(
            len(captured), 1,
            "value-dashboard.main must invoke _emit_value_dashboard_summarized "
            "exactly once per run (Wave D.3 production callsite contract).",
        )
        payload = captured[0]
        # Sec MF-3 whitelist: payload keys MUST equal EMIT_WHITELIST_KEYS.
        self.assertEqual(
            set(payload.keys()),
            set(vd.EMIT_WHITELIST_KEYS),
            "audit_emit_payload key drift breaks _VALUE_DASHBOARD_SUMMARIZED_ALLOWLIST",
        )
        self.assertEqual(payload["period_days"], 7)
        self.assertGreaterEqual(payload["dispatches_count"], 1)


if __name__ == "__main__":
    unittest.main()
