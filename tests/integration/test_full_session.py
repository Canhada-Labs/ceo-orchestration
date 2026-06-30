"""End-to-end session integration tests (PLAN-010 Phase 1).

Exercises realistic multi-step flows using real hook subprocesses and
the TestEnvContext isolation fixture from `_lib.testing`. No mocks for
the hooks themselves — we spawn them via subprocess exactly as Claude
Code would.

Scenarios live here that span more than one hook or verify top-level
isolation invariants (e.g. "no test touches real $HOME").
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import pytest

from .conftest import REPO_ROOT, parse_decision, run_hook


# --------------------------------------------------------------------------
# Isolation invariant (explicit per acceptance criterion)
# --------------------------------------------------------------------------

def test_ceo_env_points_at_tmp_dirs_not_real_home(ceo_env):
    """The ceo_env fixture MUST NOT leak into the real $HOME / audit log."""
    current_home = Path(os.environ["HOME"])
    # HOME must point INSIDE the isolated tmp tree built by TestEnvContext.
    tmp_root_resolved = str(ceo_env._tmp_root.resolve())
    assert str(current_home.resolve()).startswith(tmp_root_resolved), (
        f"HOME={current_home} is not under tmp_root={tmp_root_resolved}"
    )

    audit_path = Path(os.environ["CEO_AUDIT_LOG_PATH"])
    assert str(audit_path.resolve()).startswith(tmp_root_resolved), (
        f"CEO_AUDIT_LOG_PATH leaks outside tmpdir: {audit_path}"
    )
    # Definitely not the real framework audit log path.
    real_audit = (
        Path.home() / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"
    )
    assert audit_path.resolve() != real_audit.resolve()


# --------------------------------------------------------------------------
# Scenario 11: audit_log writes JSONL entry with expected shape
# --------------------------------------------------------------------------

def test_audit_log_emits_task_spawn_event(ceo_env):
    """PostToolUse Task → audit-log.jsonl gets one JSON object with tool_name=Task."""
    payload = {
        "session_id": "e2e-session-alpha",
        "hook_event_name": "PostToolUse",
        "tool_name": "Agent",
        "tool_input": {
            "description": "Staff Backend — implement rate limiter",
            "prompt": "PERSONA: Staff Backend\n## SKILL CONTENT\n(skill body)",
            "subagent_type": "general-purpose",
        },
        "tool_response": {"totalDurationMs": 1234, "totalTokens": 2048},
    }
    result = run_hook("audit_log.py", payload)
    assert result.returncode == 0, f"stderr={result.stderr!r}"

    log_path = Path(os.environ["CEO_AUDIT_LOG_PATH"])
    assert log_path.is_file(), "audit-log.jsonl was not created"
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1, f"expected 1 line, got {len(lines)}"
    entry = json.loads(lines[0])
    assert entry.get("tool") in ("Agent", "Task")
    assert entry.get("session_id") == "e2e-session-alpha"
    # Schema spot-checks: timestamp + hook phase fields
    assert "timestamp" in entry or "ts" in entry or "when" in entry or entry.get("tool_name")


# --------------------------------------------------------------------------
# Scenario 12: filelock contention — 2 concurrent writers, no interleave
# --------------------------------------------------------------------------

def test_audit_log_filelock_no_interleaved_lines(ceo_env):
    """Two threads writing 50 entries each produce 100 intact JSON lines.

    Uses threading.Barrier(2) to release both writers simultaneously so
    the filelock is genuinely contended. No time.sleep() — determinism
    comes from the barrier.
    """
    import subprocess
    import sys

    barrier = threading.Barrier(2)
    errors: list[str] = []

    def writer(prefix: str, count: int) -> None:
        barrier.wait()  # align start for real contention
        for i in range(count):
            payload = {
                "session_id": f"{prefix}-{i}",
                "hook_event_name": "PostToolUse",
                "tool_name": "Agent",
                "tool_input": {
                    "description": f"{prefix} writer {i}",
                    "prompt": "PERSONA: test\n## SKILL CONTENT\nx",
                    "subagent_type": "general-purpose",
                },
                "tool_response": {"totalDurationMs": 10, "totalTokens": 1},
            }
            proc = subprocess.run(
                [sys.executable, str(REPO_ROOT / ".claude" / "hooks" / "audit_log.py")],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                env=os.environ.copy(),
                timeout=5,
            )
            if proc.returncode != 0:
                errors.append(f"{prefix}-{i}: rc={proc.returncode} stderr={proc.stderr!r}")

    n_per = 50
    t1 = threading.Thread(target=writer, args=("A", n_per))
    t2 = threading.Thread(target=writer, args=("B", n_per))
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)
    assert not errors, f"subprocess failures: {errors[:3]}"

    log_path = Path(os.environ["CEO_AUDIT_LOG_PATH"])
    assert log_path.is_file()
    raw = log_path.read_text(encoding="utf-8")
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    assert len(lines) == 2 * n_per, f"lost writes: got {len(lines)} / {2 * n_per}"
    # Every line MUST parse as JSON — an interleaved/truncated write corrupts JSON.
    for ln in lines:
        try:
            json.loads(ln)
        except json.JSONDecodeError as e:
            pytest.fail(f"corrupt/interleaved line: {ln[:120]!r} — {e}")


# --------------------------------------------------------------------------
# Session-level: chain check_agent_spawn -> audit_log for a well-formed spawn
# --------------------------------------------------------------------------

def test_full_session_compliant_spawn_then_audit(ceo_env):
    """A compliant Task spawn passes check_agent_spawn AND gets audited."""
    spawn_payload = {
        "session_id": "e2e-chain",
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {
            "description": "Principal QA Architect — write tests",
            "prompt": (
                "## AGENT PROFILE\nPERSONA: Principal QA Architect\n"
                "## SKILL CONTENT\n" + ("skill-rule-body " * 30) + "\n"
                "## FILE ASSIGNMENT\n- tests/integration/test_x.py\n"
            ),
            "subagent_type": "general-purpose",
        },
    }
    pre = run_hook("check_agent_spawn.py", spawn_payload)
    assert pre.returncode == 0
    decision = parse_decision(pre.stdout)
    # This spawn has PERSONA + SKILL CONTENT — should be allowed.
    assert decision.get("decision") == "allow", f"decision={decision}"

    # Now audit the completion (PostToolUse). The audit_log hook is
    # registered under matcher "Agent" in settings.json, so rewrite
    # tool_name to Agent for the post event.
    post_payload = dict(spawn_payload)
    post_payload["hook_event_name"] = "PostToolUse"
    post_payload["tool_name"] = "Agent"
    post_payload["tool_response"] = {"totalDurationMs": 500, "totalTokens": 1024}
    post = run_hook("audit_log.py", post_payload)
    assert post.returncode == 0

    log_path = Path(os.environ["CEO_AUDIT_LOG_PATH"])
    assert log_path.is_file()
    content = log_path.read_text(encoding="utf-8")
    assert "e2e-chain" in content
