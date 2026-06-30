"""Chaos tests — hook failure injection + fail-open contract (PLAN-011 Phase 10).

Per ADR-037 §Decision §5, for every `(hook, failure_mode)` pair we
assert the framework's observable behaviour matches the fail-open
contract (ADR-005). The chaos strategy is:

1. `chaos_wrapper_factory` generates a chaos-wrapper script that
   stands in for a real hook and produces a known failure mode
   (exit1 / exit99 / garbage_stdout / stderr_spam / timeout).
2. We install the wrapper at a test-local path (`wrappers/<hook>-<mode>.py`).
3. The caller (the framework, simulated here) invokes the wrapper
   via subprocess and must still return `{"decision":"allow"}` to
   Claude Code.

The "caller" in production is Claude Code itself; the relevant
contract is:

    If a hook produces garbage or exits non-zero, the caller MUST NOT
    block the user's tool call. It MUST treat the situation as
    "allow + log a breadcrumb".

We exercise this by running the wrapper directly (subprocess) and
applying the ADR-005 parse rule (`parse_decision_safely`):

- If stdout has a parseable `{"decision":"..."}` JSON on its last line,
  return that decision verbatim.
- Otherwise return `{"decision":"allow", "breadcrumb": "<reason>"}`.

This mirrors what the real framework does — the contract test is
independent of which adapter (Claude/Gemini) produces the hook wiring.

We then additionally run the REAL `audit_log.py` (which is a
PostToolUse hook and silent on stdout) under chaos conditions to
verify it never corrupts the audit log on its own failure modes —
that's the on-disk integrity side of the contract.

Tests cover 6 hooks × 5 failure modes via parametrization.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pytest

# Conftest provides: chaos_env, isolated_audit_log, chaos_wrapper_factory,
# hook_fixture_loader, run_hook_subprocess.


_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"


# The six active hooks (mirrors chaos-inject.ALL_HOOKS).
ALL_HOOKS = [
    "check_agent_spawn",
    "audit_log",
    "check_bash_safety",
    "check_plan_edit",
    "check_read_injection",
    "check_canonical_edit",
]

# The five failure modes (mirrors chaos-inject.ALL_MODES).
ALL_MODES = [
    "exit1",
    "exit99",
    "garbage_stdout",
    "stderr_spam",
    "timeout",
]


# -----------------------------------------------------------------------------
# Fail-open contract implementation (simulates the framework)
# -----------------------------------------------------------------------------


def parse_decision_safely(
    rc: int,
    stdout: str,
    stderr: str,
) -> Dict[str, Any]:
    """ADR-005 fail-open parser.

    Rules:
    - If the subprocess returned -1 (timeout), fall back to allow.
    - If rc != 0, fall back to allow with breadcrumb.
    - If stdout has a parseable JSON decision on its last line, return it.
    - Otherwise allow + breadcrumb.

    This is what a compliant framework caller MUST do per ADR-005.
    Claude Code implements this contract; our test simulates it.
    """
    breadcrumb_reason: Optional[str] = None
    if rc == -1:
        return {"decision": "allow", "breadcrumb": "hook timed out"}
    if rc != 0:
        breadcrumb_reason = f"hook exited non-zero: rc={rc}"

    out = (stdout or "").strip()
    if not out:
        return {
            "decision": "allow",
            "breadcrumb": breadcrumb_reason or "empty stdout",
        }

    # PostToolUse hooks are silent on stdout — that's intentional.
    # Empty stdout on PostToolUse is NOT a failure.
    # For the chaos tests we treat empty stdout as fail-open allow.

    last_line = out.splitlines()[-1]
    try:
        decision = json.loads(last_line)
        if isinstance(decision, dict) and "decision" in decision:
            return decision
    except json.JSONDecodeError:
        pass

    # Unparseable → fail-open.
    return {
        "decision": "allow",
        "breadcrumb": breadcrumb_reason or "unparseable stdout",
    }


# -----------------------------------------------------------------------------
# Per-mode contract tests (parametrized across all hooks)
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("hook_name", ALL_HOOKS)
def test_fail_open_on_exit1(
    hook_name,
    chaos_env,
    chaos_wrapper_factory,
    hook_fixture_loader,
    run_hook_subprocess,
):
    """Mode exit1: chaos wrapper exits 1 → framework emits allow."""
    wrapper = chaos_wrapper_factory(hook_name, "exit1")
    payload = hook_fixture_loader(hook_name)
    rc, stdout, stderr = run_hook_subprocess(wrapper, payload, timeout=3.0)

    assert rc == 1, f"{hook_name}/exit1: expected rc=1, got {rc}"

    decision = parse_decision_safely(rc, stdout, stderr)
    assert decision.get("decision") == "allow", (
        f"{hook_name}/exit1: fail-open violated → {decision}"
    )


@pytest.mark.parametrize("hook_name", ALL_HOOKS)
def test_fail_open_on_exit99(
    hook_name,
    chaos_env,
    chaos_wrapper_factory,
    hook_fixture_loader,
    run_hook_subprocess,
):
    """Mode exit99: chaos wrapper exits 99 → framework emits allow."""
    wrapper = chaos_wrapper_factory(hook_name, "exit99")
    payload = hook_fixture_loader(hook_name)
    rc, stdout, stderr = run_hook_subprocess(wrapper, payload, timeout=3.0)

    assert rc == 99, f"{hook_name}/exit99: expected rc=99, got {rc}"
    decision = parse_decision_safely(rc, stdout, stderr)
    assert decision.get("decision") == "allow"


@pytest.mark.parametrize("hook_name", ALL_HOOKS)
def test_fail_open_on_garbage_stdout(
    hook_name,
    chaos_env,
    chaos_wrapper_factory,
    hook_fixture_loader,
    run_hook_subprocess,
):
    """Mode garbage_stdout: exit 0 + non-JSON stdout → framework emits allow."""
    wrapper = chaos_wrapper_factory(hook_name, "garbage_stdout")
    payload = hook_fixture_loader(hook_name)
    rc, stdout, stderr = run_hook_subprocess(wrapper, payload, timeout=3.0)

    assert rc == 0
    assert "not-json-" in stdout
    decision = parse_decision_safely(rc, stdout, stderr)
    assert decision.get("decision") == "allow"


@pytest.mark.parametrize("hook_name", ALL_HOOKS)
def test_fail_open_on_stderr_spam(
    hook_name,
    chaos_env,
    chaos_wrapper_factory,
    hook_fixture_loader,
    run_hook_subprocess,
):
    """Mode stderr_spam: valid stdout + 100 stderr lines → framework emits allow.

    Verifies noisy stderr does not confuse the parser; the valid
    JSON decision on stdout is preserved.
    """
    wrapper = chaos_wrapper_factory(hook_name, "stderr_spam")
    payload = hook_fixture_loader(hook_name)
    rc, stdout, stderr = run_hook_subprocess(wrapper, payload, timeout=3.0)

    assert rc == 0
    assert '"decision":"allow"' in stdout
    assert stderr.count("spam line") == 100
    decision = parse_decision_safely(rc, stdout, stderr)
    assert decision.get("decision") == "allow"


@pytest.mark.parametrize("hook_name", ALL_HOOKS)
def test_fail_open_on_timeout(
    hook_name,
    chaos_env,
    chaos_wrapper_factory,
    hook_fixture_loader,
    run_hook_subprocess,
):
    """Mode timeout: hook sleeps past caller's timeout → framework emits allow.

    We use a wrapper-sleep longer than our subprocess timeout so the
    caller-side timeout fires. run_hook_subprocess returns rc=-1 on
    TimeoutExpired.
    """
    # Sleep 2s; caller timeout 0.5s → TimeoutExpired.
    wrapper = chaos_wrapper_factory(hook_name, "timeout", timeout_seconds=2.0)
    payload = hook_fixture_loader(hook_name)
    rc, stdout, stderr = run_hook_subprocess(wrapper, payload, timeout=0.5)

    assert rc == -1, f"{hook_name}/timeout: expected timeout rc=-1, got {rc}"
    decision = parse_decision_safely(rc, stdout, stderr)
    assert decision.get("decision") == "allow"
    assert decision.get("breadcrumb") == "hook timed out"


# -----------------------------------------------------------------------------
# Real-hook audit-log integrity (PostToolUse contract)
# -----------------------------------------------------------------------------


def test_real_audit_log_survives_mixed_valid_payloads(
    chaos_env,
    isolated_audit_log,
    hook_fixture_loader,
    run_hook_subprocess,
):
    """Fire the real audit_log hook with mixed valid/invalid stdin payloads.

    Per ADR-005, audit_log must never corrupt audit-log.jsonl even on
    pathological stdin. Covers the PostToolUse silent-on-stdout side
    of the fail-open contract.
    """
    real_hook = _HOOKS_DIR / "audit_log.py"
    valid_payload = hook_fixture_loader("audit_log")
    invalid_payloads = [
        "",                              # empty stdin
        "not-json",                      # not JSON
        '{"session_id":"x"}',            # missing fields
        "\x00" * 64,                     # NUL bytes
        '{"session_id":"y","tool_name":"Agent","tool_input":{}}',
    ]

    for p in [valid_payload] + invalid_payloads:
        rc, stdout, stderr = run_hook_subprocess(real_hook, p, timeout=3.0)
        # audit_log is fail-open: rc must be 0 on ALL payloads.
        assert rc == 0, (
            f"audit_log: payload {p[:32]!r} produced rc={rc}; "
            f"stderr={stderr[:200]!r}"
        )
        # It's silent on stdout.
        assert stdout.strip() == "", (
            f"audit_log broke silence contract: stdout={stdout[:200]!r}"
        )

    # Audit log must be internally consistent.
    if isolated_audit_log.is_file():
        for idx, line in enumerate(isolated_audit_log.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError as e:
                pytest.fail(
                    f"audit-log.jsonl line {idx} corrupted after chaos: {e}\n"
                    f"line={line!r}"
                )


# -----------------------------------------------------------------------------
# Integrity: full matrix (6 hooks × 5 modes = 30 scenarios)
# -----------------------------------------------------------------------------


def test_full_failure_matrix_coverage(
    chaos_env,
    chaos_wrapper_factory,
):
    """Generate every (hook, mode) wrapper — smoke test that the factory
    covers the full 6×5 matrix without error.

    Guards against a regression where ALL_HOOKS or ALL_MODES drifts
    out of sync with the chaos-inject.py module.
    """
    count = 0
    for hook in ALL_HOOKS:
        for mode in ALL_MODES:
            w = chaos_wrapper_factory(hook, mode)
            assert w.is_file(), f"{hook}/{mode}: wrapper not written"
            # Sanity check the file isn't empty.
            assert w.stat().st_size > 200, (
                f"{hook}/{mode}: wrapper suspiciously small"
            )
            count += 1
    assert count == 6 * 5, f"expected 30 wrapper generations, got {count}"


# -----------------------------------------------------------------------------
# Environment invariant (debate §H15 + ADR-037 §Decision §2)
# -----------------------------------------------------------------------------


def test_chaos_env_does_not_leak_real_home(chaos_env):
    """Safety invariant: chaos tests MUST NOT point at real $HOME."""
    home = os.environ.get("HOME", "")
    # TestEnvContext always creates a tempdir prefixed `ceo-hook-test-`.
    assert "ceo-hook-test-" in home or "/tmp" in home or "/var/" in home, (
        f"real $HOME leaked into chaos env: {home!r}"
    )
    # CEO_CHAOS_ALLOWED must be active (for in-process gate-1 checks).
    assert os.environ.get("CEO_CHAOS_ALLOWED") == "1"

    # Audit dir must be inside the tempdir.
    audit_dir = chaos_env.audit_dir
    assert str(audit_dir).startswith(str(chaos_env._tmp_root)), (
        f"audit_dir escaped tempdir: {audit_dir!r}"
    )
