"""PLAN-153 wave-backlog — Task tools are FIRST-CLASS lifecycle enum members.

STAGED: lands together with (never before) the wave-backlog staged copies of
``_lib/tool_lifecycle.py`` + ``_lib/audit_emit.py`` — against the pre-landing
live tree the first-class assertions below are RED by design (Task tools
collapse to ``"other"`` until the enum extension lands).

Claude Code 2.1.x deprecates ``TodoWrite`` in favor of the four Task tools
(``TaskCreate`` / ``TaskUpdate`` / ``TaskGet`` / ``TaskList``). v2.48 adds
them as first-class members of the ``tool_call_lifecycle_recorded`` closed
enum, keeping ``TodoWrite`` for back-compat (additive-only per SPEC/v1).

The always-green structural invariants (pin-sync between
``_RECOGNIZED_TOOL_NAMES`` and ``_TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM``,
mcp-collapse, TodoWrite back-compat) live in the DIRECT-landed
``test_tool_lifecycle_enum_pin_sync.py``; this file asserts only the NEW
behavior.

Stdlib-only, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from _lib import audit_emit  # noqa: E402
from _lib import tool_lifecycle  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402

_TASK_TOOLS = ("TaskCreate", "TaskUpdate", "TaskGet", "TaskList")


class _Event:
    """Minimal NormalizedEvent-shaped carrier (record_pre / record_post)."""

    def __init__(
        self,
        *,
        session_id: str,
        tool_use_id: str,
        tool_name: str,
        duration_ms: Optional[int] = None,
    ) -> None:
        self.session_id = session_id
        self.tool_use_id = tool_use_id
        self.tool_name = tool_name
        self.duration_ms = duration_ms


class _TaskToolsBase(TestEnvContext):
    def _lifecycle_rows(self) -> List[Dict[str, Any]]:
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        out: List[Dict[str, Any]] = []
        if log.exists():
            for line in log.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    evt = json.loads(line)
                    if evt.get("action") == "tool_call_lifecycle_recorded":
                        out.append(evt)
        return out


class TestTaskToolsFirstClass(_TaskToolsBase):
    def test_task_tools_in_recognized_set(self):
        for name in _TASK_TOOLS:
            self.assertIn(name, tool_lifecycle._RECOGNIZED_TOOL_NAMES)

    def test_task_tools_in_emit_side_enum(self):
        for name in _TASK_TOOLS:
            self.assertIn(
                name, audit_emit._TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM
            )

    def test_mapper_returns_identity_for_task_tools(self):
        for name in _TASK_TOOLS:
            self.assertEqual(tool_lifecycle.to_tool_name_enum(name), name)

    def test_todowrite_still_first_class_back_compat(self):
        # The deprecation is UPSTREAM only — additive contract here.
        self.assertEqual(
            tool_lifecycle.to_tool_name_enum("TodoWrite"), "TodoWrite"
        )

    def test_near_miss_names_still_collapse_to_other(self):
        # The extension must not loosen the closed enum: only the four
        # exact names are first-class.
        for name in ("TaskDelete", "TaskWrite", "Todo", "task_create",
                     "TaskcreatE"):
            self.assertEqual(tool_lifecycle.to_tool_name_enum(name), "other")


class TestTaskToolPairedEmit(_TaskToolsBase):
    def test_taskcreate_pre_post_pair_emits_first_class_row(self):
        session = "task-tools-e2e"
        pre = _Event(
            session_id=session, tool_use_id="toolu_task_01",
            tool_name="TaskCreate",
        )
        # Injected clock (MF-QA-B) — pre at t=1000.0, native duration on Post.
        tool_lifecycle.record_pre(pre, now_fn=lambda: 1000.0)
        post = _Event(
            session_id=session, tool_use_id="toolu_task_01",
            tool_name="TaskCreate", duration_ms=250,
        )
        tool_lifecycle.record_post(post, failure=False)

        rows = self._lifecycle_rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.get("tool_name_enum"), "TaskCreate")
        self.assertEqual(row.get("duration_bucket"), "b_100ms_1s")
        self.assertTrue(row.get("success"))
        self.assertFalse(row.get("orphan"))

    def test_typed_emitter_no_longer_coerces_task_tools(self):
        for name in _TASK_TOOLS:
            audit_emit.emit_tool_call_lifecycle_recorded(
                session_id="task-tools-typed",
                tool_name_enum=name,
                duration_bucket="lt_100ms",
                success=True,
                orphan=False,
            )
        got = sorted(r.get("tool_name_enum") for r in self._lifecycle_rows())
        self.assertEqual(got, sorted(_TASK_TOOLS))


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
