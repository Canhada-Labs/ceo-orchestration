"""Unit tests for ``_lib.policy_preprocessors`` (PLAN-014 Phase A.4).

Covers both preprocessors:

- :func:`bash_safety_preprocess` — 15 tests across credential scan, shell
  tokenization, rm-rf flag matcher, git-reset-hard + git-push-force
  matchers, and exception-safety.
- :func:`plan_edit_preprocess` — 15 tests across scope guard, frontmatter
  extraction, status-change detection, transition-graph legality,
  required-field detectors, and exception-safety.
"""

from __future__ import annotations

import sys
from pathlib import Path


from _lib.testing import TestEnvContext  # noqa: E402
from _lib import policy_preprocessors as pp  # noqa: E402


# ---------------------------------------------------------------------------
# Bash-safety preprocessor tests
# ---------------------------------------------------------------------------


def _bash_event(command):
    return {"tool": "Bash", "tool_input": {"command": command}}


class TestBashSafetyPreprocessor(TestEnvContext):

    # --- structural / fail-safe -----------------------------------------

    def test_returns_enriched_dict_with_derived_bash(self):
        out = pp.bash_safety_preprocess(_bash_event("ls"))
        self.assertIn("_derived_bash", out)
        self.assertEqual(out["tool"], "Bash")

    def test_empty_command_has_all_false_derived_fields(self):
        d = pp.bash_safety_preprocess(_bash_event(""))["_derived_bash"]
        self.assertEqual(d["command"], "")
        self.assertEqual(d["subcommands"], [])
        self.assertFalse(d["matched_rm_rf"])
        self.assertFalse(d["matched_git_reset_hard"])
        self.assertFalse(d["matched_git_push_force"])
        self.assertEqual(d["credential_leak_provider"], "")

    def test_non_dict_event_fails_safe(self):
        d = pp.bash_safety_preprocess("not-a-dict")["_derived_bash"] if isinstance(
            pp.bash_safety_preprocess("not-a-dict"), dict) else None
        # The function returns {} if event isn't a dict — derived populated
        out = pp.bash_safety_preprocess({})
        self.assertEqual(out["_derived_bash"]["matched_rm_rf"], False)

    def test_missing_tool_input_fails_safe(self):
        d = pp.bash_safety_preprocess({"tool": "Bash"})["_derived_bash"]
        self.assertEqual(d["command"], "")
        self.assertFalse(d["matched_rm_rf"])

    # --- rm -rf matcher --------------------------------------------------

    def test_matches_rm_rf(self):
        d = pp.bash_safety_preprocess(_bash_event("rm -rf /tmp/foo"))["_derived_bash"]
        self.assertTrue(d["matched_rm_rf"])

    def test_matches_rm_Rf_case_insensitive(self):
        d = pp.bash_safety_preprocess(_bash_event("rm -Rf dir"))["_derived_bash"]
        self.assertTrue(d["matched_rm_rf"])

    def test_matches_rm_r_space_f(self):
        d = pp.bash_safety_preprocess(_bash_event("rm -r -f dir"))["_derived_bash"]
        self.assertTrue(d["matched_rm_rf"])

    def test_does_not_match_rm_r_only(self):
        d = pp.bash_safety_preprocess(_bash_event("rm -r dir"))["_derived_bash"]
        self.assertFalse(d["matched_rm_rf"])

    def test_does_not_match_quoted_rm_rf(self):
        d = pp.bash_safety_preprocess(
            _bash_event('echo "rm -rf /tmp"'))["_derived_bash"]
        self.assertFalse(d["matched_rm_rf"])

    def test_matches_long_opt_rm_recursive_force(self):
        """PLAN-019 P0-01: long-option form must match (was a bypass)."""
        d = pp.bash_safety_preprocess(
            _bash_event("rm --recursive --force dir"))["_derived_bash"]
        self.assertTrue(d["matched_rm_rf"])

    def test_matches_mixed_short_long_rm(self):
        """PLAN-019 P0-01: mixed short + long flag spelling."""
        d = pp.bash_safety_preprocess(
            _bash_event("rm -r --force dir"))["_derived_bash"]
        self.assertTrue(d["matched_rm_rf"])

    def test_matches_long_opt_order_reversed(self):
        d = pp.bash_safety_preprocess(
            _bash_event("rm --force -r dir"))["_derived_bash"]
        self.assertTrue(d["matched_rm_rf"])

    def test_matches_recursive_equals_value(self):
        """PLAN-019 P0-01: non-standard --recursive=VALUE form matches."""
        d = pp.bash_safety_preprocess(
            _bash_event("rm --recursive=true dir"))["_derived_bash"]
        self.assertTrue(d["matched_rm_rf"])

    def test_does_not_match_rm_help(self):
        """Control: --help is not destructive."""
        d = pp.bash_safety_preprocess(
            _bash_event("rm --help"))["_derived_bash"]
        self.assertFalse(d["matched_rm_rf"])

    def test_does_not_match_rm_recursive_alone(self):
        """Control: --recursive without --force (parity with `rm -r`)."""
        d = pp.bash_safety_preprocess(
            _bash_event("rm --recursive dir"))["_derived_bash"]
        self.assertFalse(d["matched_rm_rf"])

    # --- P0-02 prefix/absolute-path normalization --------------------------

    def test_matches_sudo_rm_rf(self):
        """PLAN-019 P0-02: `sudo rm -rf /tmp` must match."""
        d = pp.bash_safety_preprocess(
            _bash_event("sudo rm -rf /tmp"))["_derived_bash"]
        self.assertTrue(d["matched_rm_rf"])

    def test_matches_doas_rm_rf(self):
        d = pp.bash_safety_preprocess(
            _bash_event("doas rm -rf /tmp"))["_derived_bash"]
        self.assertTrue(d["matched_rm_rf"])

    def test_matches_nocorrect_rm_rf(self):
        d = pp.bash_safety_preprocess(
            _bash_event("nocorrect rm -rf /tmp"))["_derived_bash"]
        self.assertTrue(d["matched_rm_rf"])

    def test_matches_absolute_path_rm_rf(self):
        """PLAN-019 P0-02: `/bin/rm -rf /tmp` basename-normalized."""
        d = pp.bash_safety_preprocess(
            _bash_event("/bin/rm -rf /tmp"))["_derived_bash"]
        self.assertTrue(d["matched_rm_rf"])

    def test_matches_sudo_u_root_rm_rf(self):
        """PLAN-019 P0-02: sudo flags don't leak into the matched command."""
        d = pp.bash_safety_preprocess(
            _bash_event("sudo -u root rm -rf /tmp"))["_derived_bash"]
        self.assertTrue(d["matched_rm_rf"])

    def test_does_not_match_sudo_ls(self):
        """Control: non-destructive under sudo still allows."""
        d = pp.bash_safety_preprocess(
            _bash_event("sudo ls -la"))["_derived_bash"]
        self.assertFalse(d["matched_rm_rf"])

    def test_matches_sudo_git_reset_hard(self):
        """PLAN-019 P0-02: git reset --hard through sudo."""
        d = pp.bash_safety_preprocess(
            _bash_event("sudo git reset --hard HEAD"))["_derived_bash"]
        self.assertTrue(d["matched_git_reset_hard"])

    def test_matches_absolute_git_reset_hard(self):
        d = pp.bash_safety_preprocess(
            _bash_event("/usr/bin/git reset --hard HEAD"))["_derived_bash"]
        self.assertTrue(d["matched_git_reset_hard"])

    def test_matches_sudo_git_push_force(self):
        d = pp.bash_safety_preprocess(
            _bash_event("sudo git push --force origin main"))["_derived_bash"]
        self.assertTrue(d["matched_git_push_force"])

    def test_does_not_match_sudo_git_push_force_with_lease(self):
        """Control: safe variant not flagged even under sudo."""
        d = pp.bash_safety_preprocess(
            _bash_event("sudo git push --force-with-lease origin main"))[
                "_derived_bash"]
        self.assertFalse(d["matched_git_push_force"])

    def test_normalize_helper_empty(self):
        self.assertEqual(pp._normalize_command_tokens([]), [])

    def test_normalize_helper_sudo_prefix(self):
        self.assertEqual(
            pp._normalize_command_tokens(["sudo", "rm", "-rf", "/"]),
            ["rm", "-rf", "/"],
        )

    def test_normalize_helper_absolute_path(self):
        self.assertEqual(
            pp._normalize_command_tokens(["/bin/rm", "-rf", "/"]),
            ["rm", "-rf", "/"],
        )

    def test_normalize_helper_sudo_user_arg(self):
        self.assertEqual(
            pp._normalize_command_tokens(
                ["sudo", "-u", "root", "rm", "-rf", "/"]),
            ["rm", "-rf", "/"],
        )

    # --- git matchers ----------------------------------------------------

    def test_matches_git_reset_hard(self):
        d = pp.bash_safety_preprocess(
            _bash_event("git reset --hard HEAD"))["_derived_bash"]
        self.assertTrue(d["matched_git_reset_hard"])

    def test_does_not_match_git_reset_soft(self):
        d = pp.bash_safety_preprocess(
            _bash_event("git reset --soft HEAD"))["_derived_bash"]
        self.assertFalse(d["matched_git_reset_hard"])

    def test_matches_git_push_force(self):
        d = pp.bash_safety_preprocess(
            _bash_event("git push --force origin main"))["_derived_bash"]
        self.assertTrue(d["matched_git_push_force"])

    def test_does_not_match_force_with_lease(self):
        d = pp.bash_safety_preprocess(
            _bash_event("git push --force-with-lease origin main"))["_derived_bash"]
        self.assertFalse(d["matched_git_push_force"])

    def test_matches_compound_subcommand(self):
        d = pp.bash_safety_preprocess(
            _bash_event("ls && git reset --hard"))["_derived_bash"]
        self.assertTrue(d["matched_git_reset_hard"])
        self.assertEqual(len(d["subcommands"]), 2)

    # --- credential scan -------------------------------------------------

    def test_detects_anthropic_key(self):
        # Body must be 40-200 chars per KEY_PATTERNS["anthropic"] and contain
        # a mix of characters (all-same-char body trips the placeholder heuristic).
        cmd = ("curl -X POST https://api.anthropic.com/v1/m -H 'x-api-key: " +
               "sk-ant-api03-Zx91pQ7vN3bKmW2rT8yLh4FgJ5cDeR6sUaBnMoXiHfVq'")
        d = pp.bash_safety_preprocess(_bash_event(cmd))["_derived_bash"]
        self.assertEqual(d["credential_leak_provider"], "anthropic")
        self.assertEqual(d["credential_leak_redacted"], "anthropic:sk-ant-****")

    def test_no_credential_on_plain_command(self):
        d = pp.bash_safety_preprocess(_bash_event("ls -la"))["_derived_bash"]
        self.assertEqual(d["credential_leak_provider"], "")


# ---------------------------------------------------------------------------
# Plan-edit preprocessor tests
# ---------------------------------------------------------------------------


_BASE_DRAFT_PLAN = """---
id: PLAN-099
title: Test plan
status: draft
created: 2026-04-12
owner: CEO
depends_on: []
---

## Context
Body.
"""

_BASE_REVIEWED_PLAN = """---
id: PLAN-099
title: Test plan
status: reviewed
reviewed_at: 2026-04-12
created: 2026-04-12
owner: CEO
depends_on: []
---

## Context
Body.
"""

_BASE_EXECUTING_PLAN = """---
id: PLAN-099
title: Test plan
status: executing
reviewed_at: 2026-04-12
created: 2026-04-12
owner: CEO
depends_on: []
---

## Context
Body.
"""

_DONE_PLAN = """---
id: PLAN-099
title: Test plan
status: done
reviewed_at: 2026-04-12
completed_at: 2026-04-15
created: 2026-04-12
owner: CEO
depends_on: []
related_commits: [abc123]
---

## Context
Body.
"""


def _fake_reader(content):
    def _r(_path):
        return content
    return _r


def _edit_event(file_path, old_string="", new_string="", replace_all=False):
    return {
        "tool": "Edit",
        "tool_input": {
            "file_path": file_path,
            "old_string": old_string,
            "new_string": new_string,
            "replace_all": replace_all,
        },
    }


class TestPlanEditPreprocessor(TestEnvContext):

    # --- scope guard -----------------------------------------------------

    def test_non_plan_path_is_not_plan_file(self):
        d = pp.plan_edit_preprocess(
            _edit_event("src/index.ts", "foo", "bar"),
            read_current=_fake_reader("code"),
        )["_derived_plan"]
        self.assertFalse(d["is_plan_file"])
        self.assertEqual(d["plan_id"], "")

    def test_plan_schema_is_not_plan_file(self):
        d = pp.plan_edit_preprocess(
            _edit_event(".claude/plans/PLAN-SCHEMA.md"),
            read_current=_fake_reader("any"),
        )["_derived_plan"]
        self.assertFalse(d["is_plan_file"])

    def test_malformed_plan_id_not_plan_file(self):
        d = pp.plan_edit_preprocess(
            _edit_event(".claude/plans/PLAN-99-test.md"),
            read_current=_fake_reader("any"),
        )["_derived_plan"]
        self.assertFalse(d["is_plan_file"])

    def test_missing_tool_input_fails_safe(self):
        d = pp.plan_edit_preprocess({"tool": "Edit"})["_derived_plan"]
        self.assertFalse(d["is_plan_file"])

    # --- status extraction + change detection ---------------------------

    def test_no_change_when_old_equals_new(self):
        d = pp.plan_edit_preprocess(
            _edit_event(".claude/plans/PLAN-099-test.md",
                        "status: draft", "status: draft"),
            read_current=_fake_reader(_BASE_DRAFT_PLAN),
        )["_derived_plan"]
        self.assertTrue(d["is_plan_file"])
        self.assertFalse(d["status_changed"])

    def test_no_change_when_edit_does_not_apply(self):
        d = pp.plan_edit_preprocess(
            _edit_event(".claude/plans/PLAN-099-test.md",
                        "never-match", "other"),
            read_current=_fake_reader(_BASE_DRAFT_PLAN),
        )["_derived_plan"]
        self.assertFalse(d["status_changed"])

    def test_detects_legal_draft_to_reviewed(self):
        new_plan = _BASE_DRAFT_PLAN.replace(
            "status: draft",
            "status: reviewed\nreviewed_at: 2026-04-15",
        )
        d = pp.plan_edit_preprocess(
            _edit_event(".claude/plans/PLAN-099-test.md",
                        "status: draft",
                        "status: reviewed\nreviewed_at: 2026-04-15"),
            read_current=_fake_reader(_BASE_DRAFT_PLAN),
        )
        _ = new_plan  # for clarity; unused
        d = d["_derived_plan"]
        self.assertTrue(d["status_changed"])
        self.assertEqual(d["old_status"], "draft")
        self.assertEqual(d["new_status"], "reviewed")
        self.assertTrue(d["transition_legal"])
        self.assertTrue(d["reviewed_at_present"])

    # --- illegal transitions --------------------------------------------

    def test_detects_illegal_draft_to_executing(self):
        d = pp.plan_edit_preprocess(
            _edit_event(".claude/plans/PLAN-099-test.md",
                        "status: draft", "status: executing"),
            read_current=_fake_reader(_BASE_DRAFT_PLAN),
        )["_derived_plan"]
        self.assertTrue(d["status_changed"])
        self.assertFalse(d["transition_legal"])
        self.assertEqual(d["transition_reason_key"], "illegal_transition")

    def test_detects_illegal_status_value(self):
        d = pp.plan_edit_preprocess(
            _edit_event(".claude/plans/PLAN-099-test.md",
                        "status: draft", "status: garbage"),
            read_current=_fake_reader(_BASE_DRAFT_PLAN),
        )["_derived_plan"]
        self.assertTrue(d["status_changed"])
        self.assertFalse(d["new_status_legal"])
        self.assertEqual(d["transition_reason_key"], "illegal_status_value")

    def test_detects_done_to_executing_now_legal_post_adr_092(self):
        # audit-v2 Wave C-bis (ADR-092 honest-deferral): done → executing
        # is legal when plan body declares `reopen_via:`. Preprocessor
        # FSM aligned with check_plan_edit.py::_ALLOWED_TRANSITIONS.
        d = pp.plan_edit_preprocess(
            _edit_event(".claude/plans/PLAN-099-test.md",
                        "status: done", "status: executing"),
            read_current=_fake_reader(_DONE_PLAN),
        )["_derived_plan"]
        self.assertTrue(d["transition_legal"])
        # Other transitions FROM done remain illegal (e.g. done→draft).
        d2 = pp.plan_edit_preprocess(
            _edit_event(".claude/plans/PLAN-099-test.md",
                        "status: done", "status: draft"),
            read_current=_fake_reader(_DONE_PLAN),
        )["_derived_plan"]
        self.assertFalse(d2["transition_legal"])

    # --- required-field detectors ---------------------------------------

    def test_detects_missing_reviewed_at(self):
        d = pp.plan_edit_preprocess(
            _edit_event(".claude/plans/PLAN-099-test.md",
                        "status: draft", "status: reviewed"),
            read_current=_fake_reader(_BASE_DRAFT_PLAN),
        )["_derived_plan"]
        self.assertFalse(d["reviewed_at_present"])
        self.assertEqual(d["transition_reason_key"], "missing_reviewed_at")

    def test_detects_missing_completed_at_for_done(self):
        d = pp.plan_edit_preprocess(
            _edit_event(".claude/plans/PLAN-099-test.md",
                        "status: executing", "status: done"),
            read_current=_fake_reader(_BASE_EXECUTING_PLAN),
        )["_derived_plan"]
        self.assertEqual(d["new_status"], "done")
        self.assertFalse(d["completed_at_present"])
        self.assertEqual(d["transition_reason_key"], "missing_completed_at")

    def test_detects_missing_related_commits_for_done(self):
        plan = _BASE_EXECUTING_PLAN.replace(
            "status: executing",
            "status: done\ncompleted_at: 2026-04-16",
        )
        d = pp.plan_edit_preprocess(
            _edit_event(".claude/plans/PLAN-099-test.md",
                        "status: executing",
                        "status: done\ncompleted_at: 2026-04-16"),
            read_current=_fake_reader(_BASE_EXECUTING_PLAN),
        )["_derived_plan"]
        _ = plan
        self.assertTrue(d["completed_at_present"])
        self.assertFalse(d["related_commits_nonempty"])
        self.assertEqual(d["transition_reason_key"], "missing_related_commits")

    def test_detects_missing_abandonment_reason(self):
        d = pp.plan_edit_preprocess(
            _edit_event(".claude/plans/PLAN-099-test.md",
                        "status: draft", "status: abandoned"),
            read_current=_fake_reader(_BASE_DRAFT_PLAN),
        )["_derived_plan"]
        self.assertEqual(d["new_status"], "abandoned")
        self.assertFalse(d["abandonment_reason_present"])
        self.assertEqual(d["transition_reason_key"], "missing_abandonment_reason")

    def test_detects_abandonment_reason_present(self):
        plan = _BASE_DRAFT_PLAN + "\n## Abandonment reason\nSuperseded\n"
        new_plan = plan.replace("status: draft", "status: abandoned")
        _ = new_plan
        d = pp.plan_edit_preprocess(
            _edit_event(".claude/plans/PLAN-099-test.md",
                        "status: draft", "status: abandoned"),
            read_current=_fake_reader(plan),
        )["_derived_plan"]
        self.assertTrue(d["abandonment_reason_present"])
        self.assertTrue(d["transition_legal"])
        self.assertEqual(d["transition_reason_key"], "")

    # --- exception safety -----------------------------------------------

    def test_reader_exception_fails_safe(self):
        def raising_reader(_p):
            raise RuntimeError("boom")
        out = pp.plan_edit_preprocess(
            _edit_event(".claude/plans/PLAN-099-test.md",
                        "status: draft", "status: reviewed"),
            read_current=raising_reader,
        )
        d = out["_derived_plan"]
        # Fail-safe: preprocessor collapses to defaults (no crash).
        self.assertFalse(d["status_changed"])

    def test_plan_id_extracted_correctly(self):
        d = pp.plan_edit_preprocess(
            _edit_event(".claude/plans/PLAN-042-foo-bar.md",
                        "status: draft", "status: draft"),
            read_current=_fake_reader(_BASE_DRAFT_PLAN),
        )["_derived_plan"]
        self.assertEqual(d["plan_id"], "PLAN-042")
