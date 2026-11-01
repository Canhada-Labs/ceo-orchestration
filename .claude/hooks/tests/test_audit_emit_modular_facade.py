"""Regressions for the audit-emitter facade's dynamic lookup contract.

Producers import ``_lib.audit_emit`` and tests patch names on that module.
Extracted emitters must resolve those names at call time, just as functions
defined in the original monolithic module did.
"""

from __future__ import annotations

import sys
from pathlib import Path

from _subprocess_helpers import run_in_process_group
from _lib import audit_emit


def test_extracted_emitter_uses_facade_write_event(monkeypatch):
    """The captured payload must reach the patched facade writer."""
    written = []
    monkeypatch.setattr(audit_emit, "_write_event", written.append)

    audit_emit.emit_debate_event(
        plan_id="PLAN-FACADE",
        round_num=2,
        phase="agent-done",
        agent="test-agent",
    )

    assert len(written) == 1
    assert written[0]["action"] == "debate_event"
    assert written[0]["plan_id"] == "PLAN-FACADE"
    assert written[0]["round"] == 2


def test_extracted_emitter_uses_facade_generic_dispatch(monkeypatch):
    """Typed wrappers must dispatch through the replaceable generic emitter."""
    calls = []

    def record(action, **fields):
        calls.append((action, fields))

    monkeypatch.setattr(audit_emit, "emit_generic", record)
    audit_emit.emit_mcp_injection_finding(
        server_id="server-a",
        mcp_tool_name="lookup",
        source_kind="tool_result",
        family_counts={"role_preamble": 1},
        match_count=1,
        bytes_scanned=42,
        severity="high",
        snippet_preview="synthetic probe",
    )

    assert len(calls) == 1
    action, fields = calls[0]
    assert action == "mcp_injection_finding"
    assert fields["server_id"] == "server-a"
    assert fields["family_counts"] == {"role_preamble": 1}
    assert fields["bytes_scanned"] == 42


def test_extracted_emitter_uses_facade_private_helper(monkeypatch):
    """Private helper substitution must change the emitted payload."""
    written = []
    monkeypatch.setattr(audit_emit, "_write_event", written.append)
    monkeypatch.setattr(audit_emit, "_preview", lambda text: "preview-from-facade")

    audit_emit.emit_veto_triggered(
        hook="check_bash_safety",
        reason_code="synthetic_probe",
        reason_preview="raw text",
    )

    assert len(written) == 1
    assert written[0]["action"] == "veto_triggered"
    assert written[0]["reason_preview"] == "preview-from-facade"


def test_reload_keeps_extracted_emitters_bound_to_current_facade():
    """Reload in a child process, avoiding module-global mutation in pytest."""
    hooks_dir = Path(__file__).resolve().parents[1]
    script = """
import importlib
import sys
sys.path.insert(0, sys.argv[1])
from _lib import audit_emit
audit_emit._KNOWN_ACTIONS.add('synthetic_facade_action')
audit_emit._PLAN088_RATE_STATE['synthetic_facade_action'] = (1.0, 5, 2)
importlib.reload(audit_emit)
assert 'synthetic_facade_action' not in audit_emit._KNOWN_ACTIONS
assert audit_emit._PLAN088_RATE_STATE == {}
written = []
audit_emit._write_event = written.append
audit_emit.emit_plan_transition(
    plan_id='PLAN-FACADE', from_status='draft', to_status='reviewed',
    file_path='plans/PLAN-FACADE.md')
assert len(written) == 1, written
assert written[0]['action'] == 'plan_transition'
assert written[0]['file_path'] == 'plans/PLAN-FACADE.md'
"""
    result = run_in_process_group(
        [sys.executable, "-c", script, str(hooks_dir)],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
