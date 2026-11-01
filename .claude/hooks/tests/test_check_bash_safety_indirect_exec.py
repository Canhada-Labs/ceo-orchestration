"""PLAN-195: synthetic indirect-shell class assertions (no shell execution).

Only the returned guard decisions are inspected; every destination is a
disposable-looking /tmp path, and no fixture runs these command strings.
"""

from __future__ import annotations

import sys
import shlex
import io
import json
from unittest import mock
from pathlib import Path

import pytest


HOOKS = Path(__file__).resolve().parents[1]
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))

import check_bash_safety as guard  # noqa: E402
from _lib import bash_indirect_guard as indirect  # noqa: E402


class TestIndirectDestructiveBlocks:
    @pytest.mark.parametrize("command,code", [
        ("bash -c 'rm -rf /tmp/p195-synthetic'", "bash_indirect_rm_rf"),
        ("sh -lc 'rm -rf /tmp/p195-synthetic'", "bash_indirect_rm_rf"),
        ("eval 'git reset --hard HEAD'", "bash_indirect_git_reset"),
        ("xargs -n 1 git push --force origin", "bash_indirect_git_push"),
        ("find . -exec rm -rf /tmp/p195-synthetic {} +", "bash_indirect_rm_rf"),
        ("printf harmless\nrm -rf /tmp/p195-synthetic", "bash_indirect_rm_rf"),
        ("( git -C /tmp reset --hard HEAD )", "bash_indirect_git_reset"),
        ("if true; then rm -rf /tmp/p195-synthetic; fi", "bash_indirect_rm_rf"),
        ("bash -c 'bash -c '\"'\"'git push --force origin'\"'\"''", "bash_indirect_git_push"),
        ("/bin/RM -rf /tmp/p195-synthetic", "bash_indirect_rm_rf"),
        ("{rm,echo} -rf /tmp/p195-synthetic", "bash_indirect_rm_rf"),
        ("rm -f {-r,-n} /tmp/p195-synthetic", "bash_indirect_rm_rf"),
        ("$CMD -rf /tmp/p195-synthetic", "bash_indirect_computed_verb"),
        ('echo "$(rm -rf /tmp/p195-synthetic)"', "bash_indirect_rm_rf"),
        ('echo "`rm -rf /tmp/p195-synthetic`"', "bash_indirect_rm_rf"),
        ('cat <(rm -rf /tmp/p195-synthetic)', "bash_indirect_rm_rf"),
        ('cat >(git reset --hard HEAD)', "bash_indirect_git_reset"),
        ('cat <<EOF\n$(rm -rf /tmp/p195-synthetic)\nEOF', "bash_indirect_rm_rf"),
        ('bash <<EOF\nrm -rf /tmp/p195-synthetic\nEOF', "bash_indirect_rm_rf"),
        ('bash <<< "rm -rf /tmp/p195-synthetic"', "bash_indirect_rm_rf"),
        ('printf harmless | bash', "bash_indirect_opaque_stdin"),
        ('bash < /tmp/p195-script', "bash_indirect_opaque_stdin"),
        ("alias purge='rm -rf /tmp/p195-synthetic'; purge", "bash_indirect_rm_rf"),
        ("alias purge='rm -r'; purge -f /tmp/p195-synthetic", "bash_indirect_rm_rf"),
        ("env -S 'sh -c \"rm -rf /tmp/p195-synthetic\"'", "bash_indirect_rm_rf"),
        ("env --mystery $VERB -rf /tmp/p195-synthetic", "bash_indirect_ambiguous_launcher"),
        ("purge() { rm -rf /tmp/p195-synthetic; }; purge", "bash_indirect_rm_rf"),
    ])
    def test_blocks_indirect_with_specific_reason(self, command, code):
        decision = guard.decide_command(command)
        assert decision.allow is False
        assert decision.destructive is True
        assert decision.reason_code == code
        assert "direct form" in decision.reason


class TestIndirectLegitAllow:
    @pytest.mark.parametrize("command", [
        "echo 'rm -rf /tmp/p195-synthetic'",
        "printf '%s' 'git reset --hard HEAD'",
        "bash -c 'printf harmless'",
        "bash -lc 'echo harmless'",
        "eval 'printf harmless'",
        "xargs -n 1 echo harmless",
        "find . -exec printf harmless {} +",
        "echo okay#not-a-comment; printf done",
        "echo 'git push --force' # quoted data",
        "rm -r /tmp/p195-synthetic",
        "git push --force-with-lease origin main",
        "echo '$(rm -rf /tmp/p195-synthetic)'",
        "cat <<'EOF'\nrm -rf /tmp/p195-synthetic\nEOF",
        "cat <<EOF\nrm -rf /tmp/p195-synthetic\nEOF",
        "clean() { echo 'rm -rf /tmp/p195-synthetic'; }; clean",
    ])
    def test_legitimate_shell_or_quoted_data_allows(self, command):
        decision = guard.decide_command(command)
        assert decision.allow is True, decision.reason


class TestIndirectParseLimits:
    def test_shell_body_parse_failure_is_closed(self):
        decision = guard.decide_command("bash -c 'echo \"unterminated'")
        assert decision.allow is False
        assert indirect.scan("bash -c 'echo \"unterminated'").reason_code == (
            "bash_indirect_unparseable_shell"
        )

    def test_nested_shell_ceiling_is_closed(self):
        # The quoted nested form also hits the byte ceiling. Assert depth
        # independently so a mutant that raises MAX_DEPTH cannot hide behind
        # MAX_BODY_BYTES while keeping the same reason_code.
        assert indirect._scan("printf harmless", 9, strict=True).reason_code == (
            "bash_indirect_limit"
        )
        command = "rm -r /tmp/p195-synthetic"
        for _ in range(10):
            command = "bash -c " + shlex.quote(command)
        decision = guard.decide_command(command)
        assert decision.allow is False
        assert indirect.scan(command).reason_code == "bash_indirect_limit"


class TestReadRefusalMessage:
    def test_python_read_refusal_names_read_alternatives(self):
        decision = guard.decide_command(
            "python3 -c \"open('PROTOCOL.md','r').read()\""
        )
        assert decision.allow is False
        assert "Read/cat/grep for reading" in decision.reason
        assert "Edit/Write with sentinel for edits" in decision.reason


class TestIndirectSwitchAndHookPayload:
    def test_heuristic_off_keeps_equivalent_destructive_block(self):
        def trusted(key):
            return "0" if key == "CEO_BASH_INDIRECT_HEURISTICS" else None

        with mock.patch.object(guard._trusted_env, "get_trusted", side_effect=trusted):
            assert guard.decide_command("echo harmless | bash").allow is True
            assert guard.decide_command("$CMD -rf /tmp/p195-synthetic").allow is True
            decision = guard.decide_command("sh -c 'rm -rf /tmp/p195-synthetic'")
        assert decision.allow is False
        assert decision.reason_code == "bash_indirect_rm_rf"

    def test_hook_payload_blocks_and_emits_single_veto(self):
        payload = json.dumps({
            "session_id": "p195-isolated",
            "tool_name": "Bash",
            "tool_input": {"command": "bash -c 'rm -rf /tmp/p195-synthetic'"},
        })
        stdout = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(payload)):
            with mock.patch.object(sys, "stdout", stdout):
                with mock.patch.object(guard._audit_emit, "emit_veto_triggered") as emit:
                    assert guard.main() == 0
        output = json.loads(stdout.getvalue())
        assert output["decision"] == "block"
        assert "indirect shell execution" in output["reason"]
        matches = [call for call in emit.call_args_list if (
            call.kwargs.get("reason_code") == "bash_indirect_rm_rf"
        )]
        assert len(matches) == 1

    def test_computed_canonical_payload_blocks_without_destructive_citation(self):
        payload = json.dumps({
            "session_id": "p195-canonical",
            "tool_name": "Bash",
            "tool_input": {"command": "DEST=PROTOCOL.md; tee $DEST"},
        })
        stdout = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(payload)):
            with mock.patch.object(sys, "stdout", stdout):
                with mock.patch.object(guard._audit_emit, "emit_veto_triggered") as emit:
                    assert guard.main() == 0
        decision = json.loads(stdout.getvalue())
        assert decision["decision"] == "block"
        matches = [call for call in emit.call_args_list if (
            call.kwargs.get("reason_code") == "bash_computed_canonical_target"
        )]
        assert len(matches) == 1

    @pytest.mark.parametrize("switch", [
        "CEO_BASH_INDIRECT_GUARD", "CEO_BASH_INDIRECT_HEURISTICS",
    ])
    def test_hook_explicit_off_switch_routes_telemetry(self, switch):
        from _lib import bash_indirect_telemetry as telemetry

        def trusted(key):
            return "0" if key == switch else None

        payload = json.dumps({
            "session_id": "p195-switch",
            "tool_name": "Bash",
            "tool_input": {"command": "printf harmless"},
        })
        with mock.patch.object(guard._trusted_env, "get_trusted", side_effect=trusted):
            with mock.patch.object(telemetry, "disabled_once") as emit:
                with mock.patch.object(sys, "stdin", io.StringIO(payload)):
                    with mock.patch.object(sys, "stdout", io.StringIO()):
                        assert guard.main() == 0
        emit.assert_called_once_with(switch, "p195-switch")


class TestReviewW6GuardFallRegressions:
    @pytest.mark.parametrize("command,blocked", [
        pytest.param(
            "printf " + "x " * 1030 + "; bash -c 'rm -rf /tmp/example'",
            True, id="word-ceiling-before-indirect-command",
        ),
        pytest.param(
            "sh -c 'echo {1..130}; rm -rf /tmp/example'",
            True, id="brace-ceiling-before-destructive-command",
        ),
        pytest.param(
            "sh -c 'echo {130..1..1}; rm -rf /tmp/example'",
            True, id="brace-descending-positive-step-ceiling",
        ),
        pytest.param(
            "sh -c 'echo {1..130..-1}; rm -rf /tmp/example'",
            True, id="brace-ascending-negative-step-ceiling",
        ),
        pytest.param(
            "sh -c 'echo {1..130..0}; rm -rf /tmp/example'",
            True, id="brace-zero-step-ceiling",
        ),
        pytest.param(
            "echo ok # $(rm -rf /tmp/example)",
            False, id="comment-does-not-execute-substitution",
        ),
        pytest.param(
            'echo ">(rm -rf /tmp/example)"',
            False, id="quoted-process-substitution-is-literal",
        ),
    ])
    def test_hook_payload_matches_bash_execution_semantics(self, command, blocked):
        """Judge the hook's JSON and emitted veto, not just the helper return."""
        payload = json.dumps({
            "session_id": "p195-review-w6-isolated",
            "tool_name": "Bash",
            "tool_input": {"command": command},
        })
        stdout = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(payload)):
            with mock.patch.object(sys, "stdout", stdout):
                with mock.patch.object(guard._audit_emit, "emit_veto_triggered") as emit:
                    assert guard.main() == 0
        result = json.loads(stdout.getvalue()) if stdout.getvalue() else {}
        if blocked:
            assert result["decision"] == "block"
            assert "bash_indirect_limit" in result["reason"]
            assert emit.call_count == 1
            assert emit.call_args.kwargs["reason_code"] == "bash_indirect_limit"
        else:
            assert result.get("decision", "allow") == "allow", result
            emit.assert_not_called()

    @pytest.mark.parametrize("delimiter,blocked", [
        pytest.param("EOF", True, id="unquoted-heredoc-expands-comment-line"),
        pytest.param("'EOF'", False, id="quoted-heredoc-keeps-comment-line-data"),
    ])
    def test_heredoc_data_expansion_reaches_hook_payload(self, delimiter, blocked):
        command = "cat <<%s\n# $(rm -rf /tmp/example)\nEOF" % delimiter
        payload = json.dumps({
            "session_id": "p195-review-w6-heredoc",
            "tool_name": "Bash",
            "tool_input": {"command": command},
        })
        stdout = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(payload)):
            with mock.patch.object(sys, "stdout", stdout):
                with mock.patch.object(guard._audit_emit, "emit_veto_triggered") as emit:
                    assert guard.main() == 0
        result = json.loads(stdout.getvalue()) if stdout.getvalue() else {}
        if blocked:
            assert result["decision"] == "block"
            assert "indirect shell execution" in result["reason"]
            assert emit.call_count == 1
            assert emit.call_args.kwargs["reason_code"] == "bash_indirect_rm_rf"
        else:
            assert result.get("decision", "allow") == "allow", result
            emit.assert_not_called()
