#!/usr/bin/env python3
"""PLAN-133 A2 — check_canonical_edit.py invisible-unicode guard tests.

S225 coverage repair: PLAN-133 shipped `_scan_skill_content_unicode` +
`_staged_content` + the main() SKILL.md wiring in check_canonical_edit.py with
NO direct tests (the A2 test file only exercised the check_agent_spawn side),
dropping the module below the ADR-139 Tier-1 86% gate (90.77% → 76.80%).

Env / HOME isolation via ``TestEnvContext`` (never the real $HOME / audit log).
The trusted_env import-time snapshot is pinned per-test via
``mock.patch.dict(trusted_env.ORIGINAL_CEO_ENV, ...)`` so test order can never
leak a neighbour's CEO_UNICODE_HARDBLOCK into the frozen snapshot.

Asserts:
  - _staged_content extracts Write `content` / Edit `new_string` /
    MultiEdit `edits[].new_string` and fail-OPENs on malformed input;
  - _scan_skill_content_unicode is default-OFF (advisory, returns None),
    fail-CLOSED under CEO_UNICODE_HARDBLOCK=1, killed by CEO_SOTA_DISABLE=1,
    and prefers the trusted_env snapshot over a late-set os.environ value;
  - the block reason never echoes the matched characters (no-value-echo);
  - main() wiring: a sentinel-ALLOWED SKILL.md edit carrying Tag-block chars
    is blocked when enforced, allowed (advisory) when not, and the guard
    never fires for non-SKILL.md canonical paths.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import trusted_env  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402

_HOOK = _HOOKS_DIR / "check_canonical_edit.py"

# A Tag-block char (U+E0041 = TAG LATIN CAPITAL LETTER A) and a bidi RLO.
TAG_A = "\U000E0041"
RLO = "‮"


def _load_canonical_module():
    """Import check_canonical_edit.py under a test-local module name."""
    spec = importlib.util.spec_from_file_location(
        "check_canonical_edit_a2", _HOOK
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_canonical_edit_a2"] = mod
    spec.loader.exec_module(mod)
    return mod


def _event(tool_input):
    """Minimal stand-in for the adapter event object."""
    return types.SimpleNamespace(tool_input=tool_input)


class StagedContentTests(TestEnvContext):
    def setUp(self):
        super().setUp()
        self.mod = _load_canonical_module()

    def test_write_content_extracted(self):
        self.assertEqual(
            self.mod._staged_content(_event({"content": "full file body"})),
            "full file body",
        )

    def test_edit_new_string_extracted(self):
        self.assertEqual(
            self.mod._staged_content(_event({"new_string": "replacement"})),
            "replacement",
        )

    def test_multiedit_new_strings_concatenated(self):
        ti = {
            "edits": [
                {"new_string": "one"},
                {"old_string": "ignored"},
                "not-a-dict",
                {"new_string": "two"},
            ]
        }
        self.assertEqual(self.mod._staged_content(_event(ti)), "one\ntwo")

    def test_content_priority_over_new_string(self):
        ti = {"content": "write-wins", "new_string": "edit-loses"}
        self.assertEqual(self.mod._staged_content(_event(ti)), "write-wins")

    def test_empty_and_non_dict_inputs_return_none(self):
        self.assertIsNone(self.mod._staged_content(_event({})))
        self.assertIsNone(self.mod._staged_content(_event(None)))
        self.assertIsNone(self.mod._staged_content(_event("not-a-dict")))
        self.assertIsNone(
            self.mod._staged_content(_event({"edits": [{"old_string": "x"}]}))
        )
        self.assertIsNone(self.mod._staged_content(_event({"content": ""})))

    def test_event_without_tool_input_attr_fails_open(self):
        self.assertIsNone(self.mod._staged_content(object()))


class ScanSkillContentUnicodeTests(TestEnvContext):
    def setUp(self):
        super().setUp()
        self.mod = _load_canonical_module()
        # Pin the import-time snapshot so neighbouring tests can never leak
        # CEO_UNICODE_HARDBLOCK into it (trusted_env freezes at first import).
        patcher = mock.patch.dict(trusted_env.ORIGINAL_CEO_ENV, {}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _scan(self, content, env):
        return self.mod._scan_skill_content_unicode(
            content, surface="skill_write", env=env
        )

    def test_empty_content_returns_none(self):
        self.assertIsNone(self._scan("", {"CEO_UNICODE_HARDBLOCK": "1"}))

    def test_clean_content_returns_none_even_enforced(self):
        self.assertIsNone(
            self._scan("clean skill body", {"CEO_UNICODE_HARDBLOCK": "1"})
        )

    def test_default_off_is_advisory_no_block(self):
        self.assertIsNone(self._scan("hi " + TAG_A, {}))

    def test_enforced_blocks_tag_block_without_echo(self):
        reason = self._scan("hi " + TAG_A, {"CEO_UNICODE_HARDBLOCK": "1"})
        self.assertIsNotNone(reason)
        self.assertIn("CANONICAL-EDIT-BLOCKED", reason)
        self.assertIn("invisible_unicode_blocked", reason)
        self.assertIn("tag_block", reason)
        # No-value-echo: the matched char is never in the reason string.
        self.assertNotIn(TAG_A, reason)

    def test_enforced_blocks_bidi(self):
        reason = self._scan("a" + RLO + "b", {"CEO_UNICODE_HARDBLOCK": "1"})
        self.assertIsNotNone(reason)
        self.assertNotIn(RLO, reason)

    def test_master_kill_forces_advisory(self):
        self.assertIsNone(
            self._scan(
                "hi " + TAG_A,
                {"CEO_UNICODE_HARDBLOCK": "1", "CEO_SOTA_DISABLE": "1"},
            )
        )

    def test_trusted_snapshot_wins_over_late_set_env(self):
        # Snapshot says unset ("0") — a late-set env "1" must NOT enforce.
        with mock.patch.dict(
            trusted_env.ORIGINAL_CEO_ENV,
            {"CEO_UNICODE_HARDBLOCK": "0"},
            clear=True,
        ):
            self.assertIsNone(
                self._scan("hi " + TAG_A, {"CEO_UNICODE_HARDBLOCK": "1"})
            )

    def test_trusted_snapshot_enforces_when_env_unset(self):
        with mock.patch.dict(
            trusted_env.ORIGINAL_CEO_ENV,
            {"CEO_UNICODE_HARDBLOCK": "1"},
            clear=True,
        ):
            self.assertIsNotNone(self._scan("hi " + TAG_A, {}))

    def test_env_none_falls_back_to_os_environ(self):
        with mock.patch.dict(
            "os.environ", {"CEO_UNICODE_HARDBLOCK": "1"}, clear=False
        ):
            reason = self.mod._scan_skill_content_unicode(
                "hi " + TAG_A, surface="skill_write"
            )
            self.assertIsNotNone(reason)

    def test_advisory_path_emits_breadcrumb(self):
        # Detection with enforcement OFF → None returned but emit fired.
        self.assertIsNone(self._scan("hi " + TAG_A, {}))
        path = self.audit_dir / "audit-log.jsonl"
        self.assertTrue(path.exists(), "advisory emit missing")
        events = [
            json.loads(line)
            for line in path.read_text().splitlines()
            if line.strip()
        ]
        ours = [
            e for e in events if e.get("action") == "invisible_unicode_blocked"
        ]
        self.assertTrue(ours, "invisible_unicode_blocked breadcrumb missing")
        last = ours[-1]
        self.assertEqual(last["surface"], "skill_write")
        self.assertEqual(last["enforced"], 0)
        self.assertNotIn(TAG_A, json.dumps(last))


class MainWiringSubprocessTests(TestEnvContext):
    """Exercise the main() SKILL.md wiring through the real hook subprocess."""

    SKILL_REL = ".claude/skills/core/test-skill/SKILL.md"

    def _layout_with_sentinel(self, scope_rel):
        skill = self.project_dir / self.SKILL_REL
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text("skill", encoding="utf-8")
        (self.project_dir / ".claude" / "team.md").write_text(
            "team", encoding="utf-8"
        )
        sentinel_dir = (
            self.project_dir
            / ".claude"
            / "plans"
            / "PLAN-099"
            / "architect"
            / "round-1"
        )
        sentinel_dir.mkdir(parents=True, exist_ok=True)
        (sentinel_dir / "approved.md").write_text(
            "---\nplan: PLAN-099\nround: 1\ntype: architect-sentinel\n---\n\n"
            "Approved-By: @owner-fixture deadbeef\n"
            "Approved-At: 2026-06-09T15:30:00Z\n"
            "Scope:\n  - " + scope_rel + "\n",
            encoding="utf-8",
        )

    def _invoke(self, payload, extra_env=None):
        env = {**os.environ}
        env.setdefault("CEO_SENTINEL_UNLOCK", "PLAN-091-test-fixture")
        env.setdefault("CEO_SENTINEL_UNLOCK_ACK", "I-ACCEPT")
        env.pop("CEO_UNICODE_HARDBLOCK", None)
        if extra_env:
            env.update(extra_env)
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def test_enforced_blocks_allowed_skill_edit_with_tag_chars(self):
        self._layout_with_sentinel(self.SKILL_REL)
        target = self.project_dir / self.SKILL_REL
        rc, out, _ = self._invoke(
            {
                "tool_input": {
                    "file_path": str(target),
                    "new_string": "payload " + TAG_A,
                }
            },
            extra_env={"CEO_UNICODE_HARDBLOCK": "1"},
        )
        self.assertEqual(rc, 0, msg=out)
        d = json.loads(out)
        self.assertEqual(d["decision"], "block", msg=out)
        self.assertIn("invisible_unicode_blocked", d["reason"])
        self.assertNotIn(TAG_A, d["reason"])

    def test_default_off_allows_skill_edit_with_tag_chars(self):
        self._layout_with_sentinel(self.SKILL_REL)
        target = self.project_dir / self.SKILL_REL
        rc, out, _ = self._invoke(
            {
                "tool_input": {
                    "file_path": str(target),
                    "new_string": "payload " + TAG_A,
                }
            }
        )
        self.assertEqual(rc, 0, msg=out)
        self.assertEqual(json.loads(out).get("decision", "allow"), "allow")

    def test_enforced_clean_skill_edit_still_allows(self):
        self._layout_with_sentinel(self.SKILL_REL)
        target = self.project_dir / self.SKILL_REL
        rc, out, _ = self._invoke(
            {
                "tool_input": {
                    "file_path": str(target),
                    "new_string": "clean ascii content",
                }
            },
            extra_env={"CEO_UNICODE_HARDBLOCK": "1"},
        )
        self.assertEqual(rc, 0, msg=out)
        self.assertEqual(json.loads(out).get("decision", "allow"), "allow")

    def test_enforced_write_content_key_blocks(self):
        self._layout_with_sentinel(self.SKILL_REL)
        target = self.project_dir / self.SKILL_REL
        rc, out, _ = self._invoke(
            {
                "tool_input": {
                    "file_path": str(target),
                    "content": "full body " + TAG_A,
                }
            },
            extra_env={"CEO_UNICODE_HARDBLOCK": "1"},
        )
        self.assertEqual(rc, 0, msg=out)
        d = json.loads(out)
        self.assertEqual(d["decision"], "block", msg=out)
        self.assertIn("invisible_unicode_blocked", d["reason"])

    def test_guard_never_fires_for_non_skill_canonical_path(self):
        # team.md is canonical; a sentinel-allowed edit with tag chars must
        # pass untouched — the unicode guard is SKILL.md-scoped.
        self._layout_with_sentinel(".claude/team.md")
        target = self.project_dir / ".claude" / "team.md"
        rc, out, _ = self._invoke(
            {
                "tool_input": {
                    "file_path": str(target),
                    "new_string": "payload " + TAG_A,
                }
            },
            extra_env={"CEO_UNICODE_HARDBLOCK": "1"},
        )
        self.assertEqual(rc, 0, msg=out)
        self.assertEqual(json.loads(out).get("decision", "allow"), "allow")

    def test_blocked_edit_skips_unicode_guard(self):
        # No sentinel → sentinel gate blocks first; the unicode guard must
        # never relax or replace that block.
        skill = self.project_dir / self.SKILL_REL
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text("skill", encoding="utf-8")
        rc, out, _ = self._invoke(
            {
                "tool_input": {
                    "file_path": str(skill),
                    "new_string": "payload " + TAG_A,
                }
            },
            extra_env={"CEO_UNICODE_HARDBLOCK": "1"},
        )
        self.assertEqual(rc, 0, msg=out)
        d = json.loads(out)
        self.assertEqual(d["decision"], "block")
        # The sentinel block reason, not the unicode one.
        self.assertNotIn("invisible_unicode_blocked", d["reason"])


if __name__ == "__main__":
    unittest.main()
