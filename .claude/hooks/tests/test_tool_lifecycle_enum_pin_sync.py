"""PLAN-153 wave-backlog — tool_name_enum 3-way pin-sync regression guard.

The `tool_call_lifecycle_recorded` closed enum (SPEC MF-SEC-1) is pinned in
TWO Python surfaces that must never drift:

  * ``_lib/tool_lifecycle._RECOGNIZED_TOOL_NAMES`` — the canonical mapper's
    recognized-tool set (producer side);
  * ``_lib/audit_emit._TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM`` — the emit-side
    re-validation set, enforced at BOTH the typed emitter
    (``emit_tool_call_lifecycle_recorded``) and the ``emit_generic`` scrub
    branch (defense-in-depth: out-of-enum → coerced to ``"other"``).

(The third pin is documentation: the closed enum on the
``tool_call_lifecycle_recorded`` row of ``SPEC/v1/audit-log.schema.md``.)

If only ONE Python pin is updated (e.g. a partial ceremony landing of the
PLAN-153 wave-backlog Task-tools extension), the mapper and the emitter
disagree and first-class names silently collapse to ``"other"`` on the wire.
This test turns that drift RED. It asserts the STRUCTURAL invariant — not a
hardcoded member list — so it is green BEFORE the wave-backlog bundle lands
and stays green AFTER (current behavior preserved; the extension is additive).

Also pins the current-behavior contract that must survive the extension:
``TodoWrite`` stays recognized (back-compat — deprecated upstream by Claude
Code 2.1.x in favor of the Task tools, still emitted by older harnesses),
``mcp__*`` collapses to ``mcp_other``, unknown → ``other``, mapper output is
always a member of the emit-side closed set, and the emitted row carries
exactly the mapper's output.

Stdlib-only, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from _lib import audit_emit  # noqa: E402
from _lib import tool_lifecycle  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402

# The two synthetic values the mapper may produce in addition to recognized
# tool names. Kept as a local literal on purpose: if someone widens the
# synthetic vocabulary, this test must be revisited consciously.
_SYNTHETIC = frozenset({"mcp_other", "other"})

# The Claude Code 2.1.x Task tools (TodoWrite's upstream replacement).
# NOT asserted first-class here — that assertion lives in the STAGED
# test (test_tool_lifecycle_task_tools.py) which lands WITH the _lib
# extension. Here they only feed the closed-set / shape invariants, which
# hold both before (→ "other") and after (→ first-class) the landing.
_TASK_TOOLS = ("TaskCreate", "TaskUpdate", "TaskGet", "TaskList")


class TestEnumPinSync(TestEnvContext):
    """Structural sync between the producer set and the emit-side set."""

    def test_emit_enum_is_exactly_recognized_plus_synthetic(self):
        # THE pin-sync invariant. Equality (not subset) in both directions:
        # a member added to only one of the two Python pins is a drift.
        self.assertEqual(
            audit_emit._TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM,
            tool_lifecycle._RECOGNIZED_TOOL_NAMES | _SYNTHETIC,
        )

    def test_synthetic_values_are_not_recognized_tool_names(self):
        # MF-SEC-1 hygiene: "mcp_other"/"other" are mapper OUTPUTS, never
        # members of the recognized-tool set.
        self.assertFalse(
            tool_lifecycle._RECOGNIZED_TOOL_NAMES & _SYNTHETIC,
        )

    def test_duration_bucket_sets_in_sync(self):
        self.assertEqual(
            audit_emit._TOOL_CALL_LIFECYCLE_DURATION_BUCKETS,
            frozenset(tool_lifecycle.DURATION_BUCKETS),
        )


class TestCurrentMapperContract(TestEnvContext):
    """Current-behavior pins that must survive the additive extension."""

    def test_todowrite_stays_recognized_back_compat(self):
        # TodoWrite is deprecated UPSTREAM but must stay first-class here:
        # older harnesses still emit it (additive-only contract).
        self.assertIn("TodoWrite", tool_lifecycle._RECOGNIZED_TOOL_NAMES)
        self.assertIn(
            "TodoWrite", audit_emit._TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM
        )
        self.assertEqual(
            tool_lifecycle.to_tool_name_enum("TodoWrite"), "TodoWrite"
        )

    def test_mcp_collapse_and_unknown_other(self):
        self.assertEqual(
            tool_lifecycle.to_tool_name_enum("mcp__codex__codex-reply"),
            "mcp_other",
        )
        self.assertEqual(
            tool_lifecycle.to_tool_name_enum("TotallyMadeUpTool"), "other"
        )
        self.assertEqual(tool_lifecycle.to_tool_name_enum(""), "other")
        self.assertEqual(tool_lifecycle.to_tool_name_enum(None), "other")

    def test_mapper_idempotent_on_synthetic_values(self):
        self.assertEqual(tool_lifecycle.to_tool_name_enum("mcp_other"), "mcp_other")
        self.assertEqual(tool_lifecycle.to_tool_name_enum("other"), "other")

    def test_mapper_output_always_in_emit_side_closed_set(self):
        # For ANY input — recognized, Task tools (whether or not yet
        # first-class), MCP names, junk — the mapper's output must be a
        # member of the emit-side closed set, so the emitter's coercion
        # can never DISAGREE with the mapper (silent enum divergence).
        battery = (
            list(tool_lifecycle._RECOGNIZED_TOOL_NAMES)
            + list(_TASK_TOOLS)
            + list(_SYNTHETIC)
            + ["mcp__server__tool", "mcp__x__y-z", "nonsense", "", "Task2"]
        )
        for raw in battery:
            out = tool_lifecycle.to_tool_name_enum(raw)
            self.assertIn(
                out,
                audit_emit._TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM,
                msg="mapper output %r for raw %r escapes the emit-side "
                    "closed set" % (out, raw),
            )

    def test_task_tools_map_to_self_or_other_never_raw_leak(self):
        # Forward-compat shape: before the wave-backlog landing each Task
        # tool maps to "other"; after it, to itself. BOTH are legal here —
        # what is ILLEGAL is any third value (e.g. a mangled/raw string).
        for name in _TASK_TOOLS:
            self.assertIn(
                tool_lifecycle.to_tool_name_enum(name), {name, "other"}
            )


class TestEmitRowMatchesMapper(TestEnvContext):
    """The wire row carries exactly the mapper output (no divergence)."""

    def _rows(self) -> List[Dict[str, Any]]:
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

    def test_emitted_enum_equals_mapper_output_for_task_tool(self):
        # Green pre-landing (mapper → "other" → row "other") AND
        # post-landing (mapper → "TaskCreate" → row "TaskCreate").
        expected = tool_lifecycle.to_tool_name_enum("TaskCreate")
        audit_emit.emit_tool_call_lifecycle_recorded(
            session_id="pin-sync-test",
            tool_name_enum=expected,
            duration_bucket="lt_100ms",
            success=True,
            orphan=False,
        )
        rows = self._rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].get("tool_name_enum"), expected)
        self.assertIn(
            rows[0].get("tool_name_enum"),
            audit_emit._TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM,
        )


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
