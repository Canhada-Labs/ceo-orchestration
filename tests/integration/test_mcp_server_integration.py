"""End-to-end integration test for the MCP server (PLAN-013 Phase A.7).

Exercises all 7 handlers via the stdio transport against a real
subprocess invocation of ``mcp-server/server.py``. Verifies:

1. server starts cleanly with seeded settings.json + secret
2. each of the 7 handlers responds with a proper JSON-RPC envelope
3. audit log accumulates ``mcp_server_started`` + ``mcp_handler_invoked``
4. byte-identity governance: ``spawn_agent`` with malformed prompt
   returns the same ``block_reason`` as
   ``check_agent_spawn.decide()`` invoked directly with the same
   inputs (PLAN-013 §C2 / ADR-042 §Decision)

Uses TestEnvContext via the ``ceo_env`` fixture (xdist-safe). NO raw
monkeypatch. NO time.sleep — subprocess EOF on stdin terminates the
server cleanly.
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

# Conftest sets up sys.path; we just import what we need.
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / ".claude" / "hooks"),
)
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[2]
        / ".claude"
        / "scripts"
        / "mcp-server"
    ),
)

import check_agent_spawn  # noqa: E402
from _lib import team as _team  # noqa: E402


_SECRET = b"\x42" * 32
_CLIENT_ID = "0123456789abcdef"
_NONCE = "fedcba9876543210"
_TEAM_MD_FIXTURE = """\
# Team

## ICs

| Archetype | Reports to | Focus | Primary skill | Secondary |
|-----------|-----------|-------|---------------|-----------|
| **Staff Backend Engineer** | VP Engineering | APIs | `public-api-design` | — |
| **Principal QA Architect** | VP Engineering | Tests | `testing-strategy` | — |
"""

_SERVER_PATH = (
    Path(__file__).resolve().parents[2]
    / ".claude"
    / "scripts"
    / "mcp-server"
    / "server.py"
)


def _compute_hmac(client_id: str, nonce: str, ts_ms: int, secret: bytes) -> str:
    body = (client_id + nonce + str(int(ts_ms))).encode("ascii")
    mac = _hmac.new(secret, body, hashlib.sha256).hexdigest()
    return mac[:32]


def _make_token(client_id: str, nonce: str, ts_ms: int) -> str:
    return f"v1.{client_id}.{nonce}.{_compute_hmac(client_id, nonce, ts_ms, _SECRET)}"


def _seed_environment(project_dir: Path) -> None:
    """Seed settings.json (full ACL) + secret + team.md + a sample skill + pitfalls."""
    # secret
    secrets_dir = project_dir / "state" / "mcp_client_secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)
    key_file = secrets_dir / f"{_CLIENT_ID}.key"
    key_file.write_bytes(_SECRET)
    os.chmod(str(key_file), 0o600)
    # settings.json — give the client ALL 7 handlers in its allowlist.
    settings = {
        "mcp_client_registry": {
            _CLIENT_ID: {
                "handlers": [
                    "list_skills",
                    "get_skill",
                    "list_agents",
                    "list_pitfalls",
                    "get_audit_log",
                    "spawn_agent",
                    "server.capabilities",
                ],
            }
        }
    }
    sp = project_dir / ".claude" / "settings.json"
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(settings), encoding="utf-8")
    # team.md so list_agents has data + spawn_agent can resolve names.
    team = project_dir / ".claude" / "team.md"
    team.write_text(_TEAM_MD_FIXTURE, encoding="utf-8")
    # one fixture skill so list_skills has data.
    skill_dir = project_dir / ".claude" / "skills" / "core" / "demo-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "---\ndescription: a demo skill for integration tests\n---\n\n# Body\n",
        encoding="utf-8",
    )
    # pitfalls catalog so list_pitfalls has data.
    pitfalls = project_dir / ".claude" / "pitfalls-catalog.yaml"
    pitfalls.write_text(
        "pitfalls:\n  - id: INT-001\n    rule: 'integration test pitfall'\n",
        encoding="utf-8",
    )


def _build_request(method: str, params: dict, request_id: int, ts_ms: int) -> str:
    """Build a stdio JSON-RPC line with auth params inline."""
    full_params = dict(params)
    # PLAN-112-FOLLOWUP-mcp-bearer-defenses-wire S158 — fresh nonce per request.
    # The bearer replay defense (BearerReplayStore.check_request, POST-HMAC)
    # rejects a reused nonce within the freshness window. This e2e predates the
    # defense and reused a single _NONCE across all 7 requests, which is now
    # correctly flagged as replay on the 2nd+ request. A real client uses a fresh
    # nonce per request; mirror that with a unique 16-hex nonce derived from the
    # request_id (preserves the v1.<id>.<nonce>.<hmac> 16-hex-char format).
    _req_nonce = f"{_NONCE[:14]}{request_id:02d}"
    full_params["authorization"] = _make_token(_CLIENT_ID, _req_nonce, ts_ms)
    full_params["timestamp_ms"] = ts_ms
    full_params["session_id"] = f"int-{request_id}"
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": full_params,
        }
    )


def test_mcp_server_seven_handlers_e2e(ceo_env):
    """Spawn server.py via stdio; issue 7 calls; assert envelopes + audit + byte-identity."""
    _seed_environment(ceo_env.project_dir)
    ts = int(time.time() * 1000)

    # The mcp-server emits to whichever audit dir CEO_AUDIT_LOG_PATH
    # points at. The ceo_env fixture has already set this in os.environ
    # to the test's isolated audit dir; we just propagate to subprocess.
    env = os.environ.copy()
    env["CEO_MCP_TRANSPORT"] = "stdio"
    env["CLAUDE_PROJECT_DIR"] = str(ceo_env.project_dir)
    env["CEO_AUDIT_LOG_DIR"] = str(ceo_env.audit_dir)
    env["CEO_AUDIT_LOG_PATH"] = str(ceo_env.audit_dir / "audit-log.jsonl")
    env["CEO_AUDIT_LOG_LOCK"] = str(ceo_env.audit_dir / "audit-log.lock")
    env["CEO_AUDIT_LOG_ERR"] = str(ceo_env.audit_dir / "audit-log.errors")
    # Make sure no kill-switch from outer env.
    env.pop("CEO_SOTA_DISABLE", None)

    # Build all 7 requests.
    requests = []
    requests.append(
        _build_request("list_skills", {}, 1, ts)
    )
    requests.append(
        _build_request(
            "get_skill",
            {"tier": "core", "slug": "demo-skill"},
            2,
            ts,
        )
    )
    requests.append(_build_request("list_agents", {}, 3, ts))
    requests.append(_build_request("list_pitfalls", {}, 4, ts))
    requests.append(_build_request("get_audit_log", {"limit": 10}, 5, ts))
    requests.append(
        _build_request(
            "spawn_agent",
            {
                "agent_name": "Staff Backend Engineer",
                "description": "Staff Backend Engineer for public-api-design task",
                "prompt": (
                    "PERSONA: Staff Backend Engineer\n\n"
                    "Design endpoint X. Missing the required marker section."
                ),
            },
            6,
            ts,
        )
    )
    requests.append(_build_request("server.capabilities", {}, 7, ts))

    stdin_payload = "\n".join(requests) + "\n"

    proc = subprocess.run(
        [sys.executable, str(_SERVER_PATH)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=30.0,
    )
    assert proc.returncode == 0, (
        f"server.py exited non-zero: rc={proc.returncode} "
        f"stderr={proc.stderr!r}"
    )

    # Parse responses (one JSON object per line).
    responses = [
        json.loads(line) for line in proc.stdout.splitlines() if line.strip()
    ]
    assert len(responses) == 7, (
        f"expected 7 responses, got {len(responses)}: {responses!r}"
    )

    # Each response must be a proper JSON-RPC 2.0 envelope.
    for i, resp in enumerate(responses, start=1):
        assert resp["jsonrpc"] == "2.0", f"id={i}: bad jsonrpc"
        assert resp["id"] == i, f"id mismatch on response {i}"
        assert "result" in resp, (
            f"id={i}: expected result envelope but got error: {resp}"
        )

    # spawn_agent (id=6) is a SUCCESSFUL RPC with allowed=False (governance block).
    spawn_resp = responses[5]["result"]
    assert spawn_resp["allowed"] is False, (
        f"spawn_agent should have been governance-blocked: {spawn_resp}"
    )
    assert spawn_resp["block_reason"], "block_reason must be non-empty on deny"

    # ---- BYTE-IDENTITY governance check ----
    # Compute the equivalent decide() call locally and assert byte equality.
    names_regex = _team.load_names(ceo_env.project_dir)
    decision = check_agent_spawn.decide(
        description="Staff Backend Engineer for public-api-design task",
        prompt=(
            "PERSONA: Staff Backend Engineer\n\n"
            "Design endpoint X. Missing the required marker section."
        ),
        names_regex=names_regex,
    )
    assert decision.allow is False
    assert spawn_resp["block_reason"] == decision.reason, (
        "BYTE-IDENTITY violation: MCP spawn_agent block_reason "
        f"{spawn_resp['block_reason']!r} != decide() reason "
        f"{decision.reason!r}. Per ADR-042 §Decision + PLAN-013 §C2 these "
        "MUST match byte-for-byte."
    )

    # server.capabilities (id=7) returns the full handler inventory.
    # 11 handlers after PLAN-096 Waves A-D (audit_query, plan_status,
    # get_debate_state, get_cost_budget added to the original 7). Assert the
    # exact set so the integration rail catches both additions and removals
    # (the unit-level drift guard is
    # test_handlers_server_capabilities.py::test_inventory_matches_dispatch).
    caps = responses[6]["result"]
    expected_handlers = {
        "list_skills",
        "get_skill",
        "list_agents",
        "list_pitfalls",
        "get_audit_log",
        "spawn_agent",
        "server.capabilities",
        "audit_query",
        "plan_status",
        "get_debate_state",
        "get_cost_budget",
    }
    assert set(caps["handlers"]) == expected_handlers, (
        f"handler inventory drift: {sorted(caps['handlers'])} "
        f"!= {sorted(expected_handlers)}"
    )
    assert "spawn_agent" in caps["handlers"]
    assert caps["feature_flags"]["spawn_agent_enabled"] is True

    # Audit log assertions.
    log_path = ceo_env.audit_dir / "audit-log.jsonl"
    assert log_path.is_file(), "audit log was not created"
    log_text = log_path.read_text(encoding="utf-8")
    log_lines = [
        json.loads(line) for line in log_text.splitlines() if line.strip()
    ]
    actions = [ev["action"] for ev in log_lines]
    assert "mcp_server_started" in actions, (
        f"missing mcp_server_started in {actions}"
    )
    invoked_count = actions.count("mcp_handler_invoked")
    denied_count = actions.count("mcp_handler_denied")
    # 6 handlers should have invoked normally; spawn_agent block-reason
    # path emits mcp_handler_denied (governance_block) on a successful
    # RPC. Total: 6 invoked + 1 denied.
    assert invoked_count == 6, (
        f"expected 6 mcp_handler_invoked events, got {invoked_count}; "
        f"actions={actions}"
    )
    assert denied_count == 1, (
        f"expected 1 mcp_handler_denied event (spawn_agent governance), "
        f"got {denied_count}; actions={actions}"
    )
