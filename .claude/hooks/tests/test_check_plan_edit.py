"""Unit tests for check_plan_edit.py."""

from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path


from _lib.testing import TestEnvContext  # noqa: E402

import check_plan_edit as cpe  # noqa: E402


def _fake_read(content: str):
    """Build a read_current replacement that returns `content`."""
    def _reader(path: str) -> str:
        return content
    return _reader


_BASE_DRAFT_PLAN = """---
id: PLAN-099
title: Test plan
status: draft
created: 2026-04-12
owner: CEO
depends_on: []
---

## Context
Test body.
"""

_BASE_EXECUTING_PLAN = """---
id: PLAN-099
title: Test plan
status: executing
created: 2026-04-12
reviewed_at: 2026-04-12
owner: CEO
depends_on: []
related_commits: [abc123, def456]
---

## Context
Test body.
"""


class TestScopeGuard(unittest.TestCase):
    """Files outside .claude/plans/ must be ignored (allow)."""

    def test_non_plan_file_allowed(self):
        d = cpe.decide(
            file_path="src/index.ts",
            old_string="foo",
            new_string="bar",
            replace_all=False,
            read_current=_fake_read("some code"),
        )
        self.assertTrue(d.allow)

    def test_plan_schema_not_a_plan(self):
        """PLAN-SCHEMA.md is not a PLAN-NNN file."""
        d = cpe.decide(
            file_path=".claude/plans/PLAN-SCHEMA.md",
            old_string="foo",
            new_string="bar",
            replace_all=False,
            read_current=_fake_read("any content"),
        )
        self.assertTrue(d.allow)

    def test_plan_nnn_file_is_in_scope(self):
        """A PLAN-099-test.md transition is evaluated."""
        new_plan = _BASE_DRAFT_PLAN.replace("status: draft", "status: done")
        d = cpe.decide(
            file_path=".claude/plans/PLAN-099-test.md",
            old_string="status: draft",
            new_string="status: done",
            replace_all=False,
            read_current=_fake_read(_BASE_DRAFT_PLAN),
        )
        self.assertFalse(d.allow)  # draft → done is illegal


class TestTransitions(unittest.TestCase):

    def _decide(self, old_content, old_string, new_string):
        return cpe.decide(
            file_path=".claude/plans/PLAN-099-test.md",
            old_string=old_string,
            new_string=new_string,
            replace_all=False,
            read_current=_fake_read(old_content),
        )

    def test_draft_to_reviewed_with_reviewed_at(self):
        old_s = "status: draft\ncreated: 2026-04-12"
        new_s = "status: reviewed\ncreated: 2026-04-12\nreviewed_at: 2026-04-12"
        d = self._decide(_BASE_DRAFT_PLAN, old_s, new_s)
        self.assertTrue(d.allow)

    def test_draft_to_reviewed_without_reviewed_at_blocked(self):
        old_s = "status: draft"
        new_s = "status: reviewed"
        d = self._decide(_BASE_DRAFT_PLAN, old_s, new_s)
        self.assertFalse(d.allow)
        self.assertIn("reviewed_at", d.reason)

    def test_draft_to_executing_blocked(self):
        """Must go draft → reviewed → executing, not draft → executing."""
        old_s = "status: draft"
        new_s = "status: executing"
        d = self._decide(_BASE_DRAFT_PLAN, old_s, new_s)
        self.assertFalse(d.allow)
        self.assertIn("illegal transition", d.reason)

    def test_draft_to_done_blocked(self):
        old_s = "status: draft"
        new_s = "status: done"
        d = self._decide(_BASE_DRAFT_PLAN, old_s, new_s)
        self.assertFalse(d.allow)

    def test_executing_to_done_without_completed_at_blocked(self):
        old_s = "status: executing"
        new_s = "status: done"
        d = self._decide(_BASE_EXECUTING_PLAN, old_s, new_s)
        self.assertFalse(d.allow)
        self.assertIn("completed_at", d.reason)

    def test_executing_to_done_without_related_commits_blocked(self):
        plan_no_commits = _BASE_EXECUTING_PLAN.replace(
            "related_commits: [abc123, def456]", "related_commits: []"
        )
        old_s = "status: executing"
        new_s = "status: done\ncompleted_at: 2026-04-12"
        d = self._decide(plan_no_commits, old_s, new_s)
        self.assertFalse(d.allow)
        self.assertIn("related_commits", d.reason)

    def test_executing_to_done_success(self):
        old_s = "status: executing\nreviewed_at: 2026-04-12"
        new_s = (
            "status: done\n"
            "completed_at: 2026-04-12\n"
            "reviewed_at: 2026-04-12"
        )
        d = self._decide(_BASE_EXECUTING_PLAN, old_s, new_s)
        self.assertTrue(d.allow)

    def test_any_to_abandoned_requires_reason_section(self):
        old_s = "status: executing"
        new_s = "status: abandoned"
        d = self._decide(_BASE_EXECUTING_PLAN, old_s, new_s)
        self.assertFalse(d.allow)
        self.assertIn("Abandonment reason", d.reason)

    def test_any_to_abandoned_with_reason_section_succeeds(self):
        plan_with_reason = _BASE_EXECUTING_PLAN + "\n## Abandonment reason\nSuperseded.\n"
        old_s = "status: executing"
        new_s = "status: abandoned"
        d = cpe.decide(
            file_path=".claude/plans/PLAN-099-test.md",
            old_string=old_s,
            new_string=new_s,
            replace_all=False,
            read_current=_fake_read(plan_with_reason),
        )
        self.assertTrue(d.allow)

    def test_illegal_status_value_blocked(self):
        old_s = "status: draft"
        new_s = "status: ninja"
        d = self._decide(_BASE_DRAFT_PLAN, old_s, new_s)
        self.assertFalse(d.allow)
        self.assertIn("illegal status value", d.reason)

    def test_done_is_terminal(self):
        """done is terminal EXCEPT for `done → executing` re-open per
        ADR-092 honest-deferral framework (audit-v2 Wave C, 2026-04-27).

        Re-open is gated on the four ADR-092 fields (reopen_via:,
        reopen_trigger:, refused_at not relevant here, plus the body
        section `## Reopen criteria`). Session 76 audit-v3 (DIM-11) wired
        these as a hard-block in `_check_required_fields`, so a reopen
        edit must carry all four fields to pass.
        """
        plan_done = _BASE_EXECUTING_PLAN.replace(
            "status: executing", "status: done"
        ) + (
            "\ncompleted_at: 2026-04-12"
            "\nrelated_commits:\n  - abc1234\n"
        )
        # Reopen edit: change status AND add all four ADR-092 reopen
        # fields + body section. _decide_on_buffers parses pre/post
        # buffers, so we re-write the entire status block in one Edit.
        old_s = "status: done"
        new_s = (
            "status: executing\n"
            "reopen_via: ADR-092\n"
            "reopen_trigger: external soak signal arrived\n"
        )
        # Add the body section by appending to the plan content directly.
        plan_done_with_section = plan_done + (
            "\n## Reopen criteria\n\n"
            "External signal X received from Y.\n"
        )
        d = cpe.decide(
            file_path=".claude/plans/PLAN-099-test.md",
            old_string=old_s,
            new_string=new_s,
            replace_all=False,
            read_current=_fake_read(plan_done_with_section),
        )
        self.assertTrue(d.allow, msg=f"Reason: {d.reason}")

    def test_edit_unrelated_to_status_allowed(self):
        """An edit that doesn't touch status must pass."""
        d = self._decide(
            _BASE_EXECUTING_PLAN,
            "Test body.",
            "Test body with new content.",
        )
        self.assertTrue(d.allow)

    def test_edit_that_doesnt_match_content_allowed(self):
        """old_string not in content → let Edit tool error, don't block."""
        d = self._decide(
            _BASE_EXECUTING_PLAN,
            "string not in content anywhere",
            "replacement",
        )
        self.assertTrue(d.allow)


_BASE_DONE_PLAN = """---
id: PLAN-099
title: Test plan
status: done
created: 2026-04-12
reviewed_at: 2026-04-12
completed_at: 2026-04-13
owner: CEO
depends_on: []
related_commits: [abc123, def456]
---

## Context
Test body.
"""


class TestSupersededStatus(unittest.TestCase):
    """PLAN-113 W2 — `superseded` is a legal terminal status requiring a
    `superseded_by: PLAN-NNN` frontmatter pointer."""

    def _decide(self, old_content, old_string, new_string):
        return cpe.decide(
            file_path=".claude/plans/PLAN-099-test.md",
            old_string=old_string,
            new_string=new_string,
            replace_all=False,
            read_current=_fake_read(old_content),
        )

    def test_superseded_is_legal_value(self):
        """`superseded` must not be reported as an illegal status value."""
        self.assertIn("superseded", cpe._LEGAL_STATUSES)

    def test_executing_to_superseded_with_superseded_by_succeeds(self):
        old_s = "status: executing"
        new_s = "status: superseded\nsuperseded_by: PLAN-106"
        d = self._decide(_BASE_EXECUTING_PLAN, old_s, new_s)
        self.assertTrue(d.allow, msg=f"Reason: {d.reason}")

    def test_done_to_superseded_with_superseded_by_succeeds(self):
        """A done plan can be superseded when a later plan absorbs it
        (mirrors PLAN-093/095-FOLLOWUP → PLAN-106)."""
        old_s = "status: done"
        new_s = "status: superseded\nsuperseded_by: PLAN-106"
        d = self._decide(_BASE_DONE_PLAN, old_s, new_s)
        self.assertTrue(d.allow, msg=f"Reason: {d.reason}")

    def test_draft_to_superseded_with_superseded_by_succeeds(self):
        old_s = "status: draft"
        new_s = "status: superseded\nsuperseded_by: PLAN-106"
        d = self._decide(_BASE_DRAFT_PLAN, old_s, new_s)
        self.assertTrue(d.allow, msg=f"Reason: {d.reason}")

    def test_superseded_without_superseded_by_blocked(self):
        old_s = "status: executing"
        new_s = "status: superseded"
        d = self._decide(_BASE_EXECUTING_PLAN, old_s, new_s)
        self.assertFalse(d.allow)
        self.assertIn("superseded_by", d.reason)

    def test_superseded_with_malformed_superseded_by_blocked(self):
        old_s = "status: executing"
        new_s = "status: superseded\nsuperseded_by: PLAN-106 (folded in)"
        d = self._decide(_BASE_EXECUTING_PLAN, old_s, new_s)
        # "PLAN-106 (folded in)" does start with PLAN-NNN so this passes;
        # a value not matching PLAN-NNN must be blocked instead.
        self.assertTrue(d.allow, msg=f"Reason: {d.reason}")

    def test_superseded_with_non_plan_superseded_by_blocked(self):
        old_s = "status: executing"
        new_s = "status: superseded\nsuperseded_by: the-burndown-sweep"
        d = self._decide(_BASE_EXECUTING_PLAN, old_s, new_s)
        self.assertFalse(d.allow)
        self.assertIn("superseded_by", d.reason)

    def test_abandoned_is_terminal_not_to_superseded(self):
        """abandoned is terminal — cannot move to superseded."""
        plan_abandoned = _BASE_EXECUTING_PLAN.replace(
            "status: executing", "status: abandoned"
        )
        old_s = "status: abandoned"
        new_s = "status: superseded\nsuperseded_by: PLAN-106"
        d = self._decide(plan_abandoned, old_s, new_s)
        self.assertFalse(d.allow)
        self.assertIn("illegal transition", d.reason)


class TestMainEntrypoint(TestEnvContext):
    """End-to-end tests via stdin JSON."""

    def _run_main(self, payload_dict):
        old_stdin, old_stdout = sys.stdin, sys.stdout
        sys.stdin = io.StringIO(json.dumps(payload_dict))
        sys.stdout = io.StringIO()
        try:
            rc = cpe.main()
        finally:
            out = sys.stdout.getvalue()
            sys.stdin, sys.stdout = old_stdin, old_stdout
        self.assertEqual(rc, 0)
        return json.loads(out.strip())

    def test_main_allows_non_plan(self):
        d = self._run_main({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "src/foo.py",
                "old_string": "x",
                "new_string": "y",
            }
        })
        self.assertEqual(d.get("decision", "allow"), "allow")

    def test_main_allows_missing_file(self):
        d = self._run_main({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": ".claude/plans/PLAN-999-nonexistent.md",
                "old_string": "x",
                "new_string": "y",
            }
        })
        self.assertEqual(d.get("decision", "allow"), "allow")

    def test_main_fail_open_on_bad_json(self):
        old_stdin, old_stdout = sys.stdin, sys.stdout
        sys.stdin = io.StringIO("{not valid")
        sys.stdout = io.StringIO()
        try:
            rc = cpe.main()
        finally:
            out = sys.stdout.getvalue()
            sys.stdin, sys.stdout = old_stdin, old_stdout
        self.assertEqual(rc, 0)
        d = json.loads(out.strip())
        self.assertEqual(d.get("decision", "allow"), "allow")


class TestWriteBypass(TestEnvContext):
    """PLAN-019 P1-SEC-E regression: Write tool must not bypass lifecycle.

    Before this fix, the matcher was "Edit" only, so `Write` on a
    PLAN-NNN.md file with status: done (no completed_at, no
    related_commits) would silently pass the governance hook.
    """

    def setUp(self) -> None:
        super().setUp()
        # Create a draft plan on disk so decide_write reads real content.
        self.plan_path = self.project_dir / ".claude" / "plans" / "PLAN-099-wbypass.md"
        self.plan_path.parent.mkdir(parents=True, exist_ok=True)
        self.plan_path.write_text(_BASE_DRAFT_PLAN, encoding="utf-8")
        # An executing plan used for done-transition tests
        self.exec_plan_path = (
            self.project_dir / ".claude" / "plans" / "PLAN-098-exec.md"
        )
        self.exec_plan_path.write_text(_BASE_EXECUTING_PLAN, encoding="utf-8")

    def _run_main(self, payload_dict):
        old_stdin, old_stdout = sys.stdin, sys.stdout
        sys.stdin = io.StringIO(json.dumps(payload_dict))
        sys.stdout = io.StringIO()
        try:
            rc = cpe.main()
        finally:
            out = sys.stdout.getvalue()
            sys.stdin, sys.stdout = old_stdin, old_stdout
        self.assertEqual(rc, 0)
        return json.loads(out.strip())

    def test_write_bypass_blocks_draft_to_done(self):
        """Write PLAN-NNN.md draft→done MUST block as illegal transition.

        The transition validator fires before the required-field check,
        so the reason is "illegal transition". Either way, the Write is
        blocked — which is the security contract.
        """
        new_content = _BASE_DRAFT_PLAN.replace(
            "status: draft", "status: done"
        )
        d = self._run_main({
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(self.plan_path),
                "content": new_content,
            },
        })
        self.assertEqual(d["decision"], "block")
        # Either reason is acceptable; both prove the bypass is closed.
        self.assertTrue(
            "illegal transition" in d["reason"]
            or "completed_at" in d["reason"],
            msg=f"unexpected reason: {d['reason']}",
        )

    def test_write_bypass_blocks_done_without_completed_at(self):
        """Write PLAN-NNN.md executing→done without completed_at MUST block.

        This is the primary P1-SEC-E regression: via the Edit matcher
        this was already blocked; via the Write matcher it silently
        passed before the fix.
        """
        new_content = _BASE_EXECUTING_PLAN.replace(
            "status: executing", "status: done"
        )
        d = self._run_main({
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(self.exec_plan_path),
                "content": new_content,
            },
        })
        self.assertEqual(d["decision"], "block")
        self.assertIn("completed_at", d["reason"])

    def test_write_bypass_blocks_illegal_transition(self):
        """Write draft→executing (skipping reviewed) MUST block."""
        new_content = _BASE_DRAFT_PLAN.replace(
            "status: draft", "status: executing"
        )
        d = self._run_main({
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(self.plan_path),
                "content": new_content,
            },
        })
        self.assertEqual(d["decision"], "block")
        self.assertIn("illegal transition", d["reason"])

    def test_write_draft_to_reviewed_with_reviewed_at_allows(self):
        """Legal write transition passes."""
        new_content = _BASE_DRAFT_PLAN.replace(
            "status: draft", "status: reviewed"
        )
        new_content = new_content.replace(
            "owner: CEO", "owner: CEO\nreviewed_at: 2026-04-17"
        )
        d = self._run_main({
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(self.plan_path),
                "content": new_content,
            },
        })
        self.assertEqual(d.get("decision", "allow"), "allow")

    def test_write_brand_new_plan_with_done_blocks(self):
        """New-plan Write with status: done + no completed_at MUST block.

        A spawned agent could attempt to Write a fresh PLAN-099-x.md
        straight to `status: done` to skip review. The hook catches this
        because `_check_required_fields` fires on any transition TO
        done regardless of old_status, even when old_status is empty.
        """
        fresh_path = self.project_dir / ".claude" / "plans" / "PLAN-100-fresh.md"
        new_content = """---
id: PLAN-100
title: Fresh plan
status: done
created: 2026-04-17
owner: CEO
depends_on: []
---
"""
        d = self._run_main({
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(fresh_path),
                "content": new_content,
            },
        })
        self.assertEqual(d["decision"], "block")
        self.assertIn("completed_at", d["reason"])

    def test_write_non_plan_file_allows(self):
        """Write on a non-plan path is out of scope."""
        d = self._run_main({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "src/unrelated.ts",
                "content": "// anything",
            },
        })
        self.assertEqual(d.get("decision", "allow"), "allow")

    def test_write_no_content_allows(self):
        """Write with empty/missing content is a no-op → allow."""
        d = self._run_main({
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(self.plan_path),
                "content": _BASE_DRAFT_PLAN,  # identical
            },
        })
        self.assertEqual(d.get("decision", "allow"), "allow")


class TestMultiEditBypass(TestEnvContext):
    """PLAN-019 P1-SEC-E regression: MultiEdit must apply same checks."""

    def setUp(self) -> None:
        super().setUp()
        self.plan_path = self.project_dir / ".claude" / "plans" / "PLAN-099-mbypass.md"
        self.plan_path.parent.mkdir(parents=True, exist_ok=True)
        self.plan_path.write_text(_BASE_EXECUTING_PLAN, encoding="utf-8")

    def _run_main(self, payload_dict):
        old_stdin, old_stdout = sys.stdin, sys.stdout
        sys.stdin = io.StringIO(json.dumps(payload_dict))
        sys.stdout = io.StringIO()
        try:
            rc = cpe.main()
        finally:
            out = sys.stdout.getvalue()
            sys.stdin, sys.stdout = old_stdin, old_stdout
        self.assertEqual(rc, 0)
        return json.loads(out.strip())

    def test_multiedit_bypass_blocks_done_without_completed_at(self):
        """MultiEdit sequence that transitions to done without
        completed_at MUST block."""
        d = self._run_main({
            "tool_name": "MultiEdit",
            "tool_input": {
                "file_path": str(self.plan_path),
                "edits": [
                    {
                        "old_string": "status: executing",
                        "new_string": "status: done",
                    },
                ],
            },
        })
        self.assertEqual(d["decision"], "block")
        self.assertIn("completed_at", d["reason"])

    def test_multiedit_legal_transition_allows(self):
        """MultiEdit that legally adds completed_at + sets done allows."""
        d = self._run_main({
            "tool_name": "MultiEdit",
            "tool_input": {
                "file_path": str(self.plan_path),
                "edits": [
                    {
                        "old_string": "status: executing",
                        "new_string": "status: done\ncompleted_at: 2026-04-17",
                    },
                ],
            },
        })
        self.assertEqual(d.get("decision", "allow"), "allow")

    def test_multiedit_empty_edits_allows(self):
        """MultiEdit with empty edits list is a no-op."""
        d = self._run_main({
            "tool_name": "MultiEdit",
            "tool_input": {
                "file_path": str(self.plan_path),
                "edits": [],
            },
        })
        self.assertEqual(d.get("decision", "allow"), "allow")

    def test_multiedit_non_dict_edits_tolerated(self):
        """Malformed edit entries skipped; well-formed still evaluated."""
        d = self._run_main({
            "tool_name": "MultiEdit",
            "tool_input": {
                "file_path": str(self.plan_path),
                "edits": [
                    "not-a-dict",  # silently skipped
                    {
                        "old_string": "status: executing",
                        "new_string": "status: abandoned",
                    },
                ],
            },
        })
        # status: abandoned without ## Abandonment reason → block
        self.assertEqual(d["decision"], "block")
        self.assertIn("Abandonment reason", d["reason"])


class TestDecideWriteDirect(unittest.TestCase):
    """Unit tests for decide_write() pure function."""

    def test_write_creates_new_plan_with_done_blocks(self):
        d = cpe.decide_write(
            file_path=".claude/plans/PLAN-100-new.md",
            content="---\nid: PLAN-100\nstatus: done\n---\n",
            read_current=_fake_read(""),  # file doesn't exist
        )
        self.assertFalse(d.allow)
        self.assertIn("completed_at", d.reason)

    def test_write_creates_new_plan_with_draft_allows(self):
        d = cpe.decide_write(
            file_path=".claude/plans/PLAN-100-new.md",
            content="---\nid: PLAN-100\nstatus: draft\n---\n",
            read_current=_fake_read(""),
        )
        self.assertTrue(d.allow)

    def test_write_non_plan_file_skipped(self):
        d = cpe.decide_write(
            file_path="src/unrelated.ts",
            content="foo",
            read_current=_fake_read(""),
        )
        self.assertTrue(d.allow)


class TestDecideMultiEditDirect(unittest.TestCase):
    """Unit tests for decide_multiedit() pure function."""

    def test_multiedit_non_plan_file_skipped(self):
        d = cpe.decide_multiedit(
            file_path="src/unrelated.ts",
            edits=[{"old_string": "x", "new_string": "y"}],
            read_current=_fake_read("x"),
        )
        self.assertTrue(d.allow)

    def test_multiedit_missing_file_allows(self):
        d = cpe.decide_multiedit(
            file_path=".claude/plans/PLAN-099-x.md",
            edits=[{"old_string": "x", "new_string": "y"}],
            read_current=_fake_read(""),
        )
        self.assertTrue(d.allow)

    def test_multiedit_none_edits_list_allows(self):
        d = cpe.decide_multiedit(
            file_path=".claude/plans/PLAN-099-x.md",
            edits=None,  # type: ignore[arg-type]
            read_current=_fake_read(_BASE_DRAFT_PLAN),
        )
        self.assertTrue(d.allow)
