"""Unit tests for mcp-server/dispatch.py — JSON-RPC 2.0 + auth pipeline.

ADR-042 §Auth full pipeline. Tests cover:
- parse_envelope (valid + malformed JSON + wrong jsonrpc version + missing method)
- authenticate auth failure paths (token malformed, hmac invalid, skew)
- authenticate ACL deny
- authenticate rate-limit deny
- dispatch handler success → mcp_handler_invoked emit + rpc_result
- dispatch handler exception → mcp_handler_denied + ERR_INTERNAL
- dispatch sentinel-error path (handler returns __error__)
- dispatch spawn_agent governance deny → SUCCESSFUL rpc with allowed=False
- dispatch spawn_agent budget deny → SUCCESSFUL rpc + _budget_reason stripped
- HANDLERS registry shape (7 entries)

Every test subclasses TestEnvContext (xdist-safe).
"""

from __future__ import annotations

import json
import os
import sys
import time
import unittest
from pathlib import Path

# Bootstrap sys.path so mcp-server modules import cleanly.
_TESTS_DIR = Path(__file__).resolve().parent
_SERVER_DIR = _TESTS_DIR.parent
_CLAUDE_DIR = _SERVER_DIR.parent.parent
_HOOKS_DIR = _CLAUDE_DIR / "hooks"
for _p in (_HOOKS_DIR, _SERVER_DIR, _SERVER_DIR / "handlers"):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

from _lib.testing import TestEnvContext  # noqa: E402

import auth  # type: ignore[import-not-found]  # noqa: E402
import dispatch  # type: ignore[import-not-found]  # noqa: E402
import rate_limit  # type: ignore[import-not-found]  # noqa: E402
# PLAN-112-FOLLOWUP-mcp-bearer-defenses-wire — replay store fixture.
from _lib.mcp import bearer_replay  # noqa: E402


_SECRET = b"\x42" * 32
_CLIENT_ID = "0123456789abcdef"
_NONCE = "fedcba9876543210"


def _fresh_nonce(i: int) -> str:
    """Distinct 16-hex nonce per call (replay defense rejects reuse).

    The MCP token nonce field is 16 lowercase hex chars; a real client
    issues a fresh nonce per request. Tests that present more than one
    successful auth must do the same now that replay defense is wired.
    """
    return "%016x" % (0x1111111111111111 + i)


def _seed_secret(project_dir: Path, client_id: str = _CLIENT_ID) -> None:
    secrets_dir = project_dir / "state" / "mcp_client_secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)
    target = secrets_dir / f"{client_id}.key"
    target.write_bytes(_SECRET)
    os.chmod(str(target), 0o600)


def _write_settings(project_dir: Path, registry: dict) -> None:
    settings = {"mcp_client_registry": registry}
    sp = project_dir / ".claude" / "settings.json"
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(settings), encoding="utf-8")


def _make_token(client_id: str, nonce: str, ts_ms: int, secret: bytes) -> str:
    mac = auth.compute_hmac(client_id, nonce, ts_ms, secret)
    return f"v1.{client_id}.{nonce}.{mac}"


class TestParseEnvelope(TestEnvContext):

    def test_valid_envelope(self):
        body = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "list_skills", "params": {}}
        )
        env, err = dispatch.parse_envelope(body)
        self.assertIsNone(err)
        self.assertIsNotNone(env)
        self.assertEqual(env["method"], "list_skills")

    def test_malformed_json_returns_parse_error(self):
        env, err = dispatch.parse_envelope("{not json")
        self.assertIsNone(env)
        self.assertIsNotNone(err)
        self.assertEqual(err["error"]["code"], dispatch.ERR_PARSE)

    def test_wrong_jsonrpc_version_returns_invalid_request(self):
        body = json.dumps(
            {"jsonrpc": "1.0", "id": 1, "method": "list_skills"}
        )
        _env, err = dispatch.parse_envelope(body)
        self.assertIsNotNone(err)
        self.assertEqual(err["error"]["code"], dispatch.ERR_INVALID_REQUEST)

    def test_missing_method_returns_invalid_request(self):
        body = json.dumps({"jsonrpc": "2.0", "id": 1})
        _env, err = dispatch.parse_envelope(body)
        self.assertIsNotNone(err)
        self.assertEqual(err["error"]["code"], dispatch.ERR_INVALID_REQUEST)

    def test_top_level_array_rejected(self):
        body = json.dumps([{"jsonrpc": "2.0", "id": 1, "method": "x"}])
        _env, err = dispatch.parse_envelope(body)
        self.assertIsNotNone(err)
        self.assertEqual(err["error"]["code"], dispatch.ERR_INVALID_REQUEST)

    def test_invalid_id_type_rejected(self):
        body = json.dumps(
            {"jsonrpc": "2.0", "id": [1, 2], "method": "list_skills"}
        )
        _env, err = dispatch.parse_envelope(body)
        self.assertIsNotNone(err)
        self.assertEqual(err["error"]["code"], dispatch.ERR_INVALID_REQUEST)


class TestAuthenticate(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        rate_limit.reset_registry()
        # PLAN-112-FOLLOWUP — the replay store is a per-process singleton;
        # reset it per test so nonce reuse across cases does not bleed.
        dispatch.set_replay_store_for_test(bearer_replay.BearerReplayStore())

    def tearDown(self) -> None:
        dispatch.set_replay_store_for_test(None)
        super().tearDown()

    def _setup_basic_client(self, handlers=("list_skills",)):
        _seed_secret(self.project_dir)
        _write_settings(
            self.project_dir,
            {_CLIENT_ID: {"handlers": list(handlers)}},
        )

    def test_missing_token_denies(self):
        ctx, reason, _ = dispatch.authenticate(
            raw_token=None,
            timestamp_ms=1700000000000,
            method="list_skills",
            origin=None,
            transport="stdio",
            session_id="s",
            project_dir=self.project_dir,
        )
        self.assertIsNone(ctx)
        self.assertEqual(reason, "auth_token_malformed")

    def test_malformed_token_denies(self):
        ctx, reason, _ = dispatch.authenticate(
            raw_token="not-a-valid-token",
            timestamp_ms=1700000000000,
            method="list_skills",
            origin=None,
            transport="stdio",
            session_id="s",
            project_dir=self.project_dir,
        )
        self.assertIsNone(ctx)
        self.assertEqual(reason, "auth_token_malformed")

    def test_unknown_client_denies_as_hmac_invalid(self):
        # No secret + no registry → fail at registry stage.
        ts = int(time.time() * 1000)
        token = _make_token(_CLIENT_ID, _NONCE, ts, _SECRET)
        ctx, reason, _ = dispatch.authenticate(
            raw_token=token,
            timestamp_ms=ts,
            method="list_skills",
            origin=None,
            transport="stdio",
            session_id="s",
            project_dir=self.project_dir,
        )
        self.assertIsNone(ctx)
        self.assertEqual(reason, "auth_hmac_invalid")

    def test_wrong_secret_denies_as_hmac_invalid(self):
        self._setup_basic_client()
        ts = int(time.time() * 1000)
        # Use a different secret to forge.
        token = _make_token(_CLIENT_ID, _NONCE, ts, b"\x99" * 32)
        ctx, reason, _ = dispatch.authenticate(
            raw_token=token,
            timestamp_ms=ts,
            method="list_skills",
            origin=None,
            transport="stdio",
            session_id="s",
            project_dir=self.project_dir,
        )
        self.assertIsNone(ctx)
        self.assertEqual(reason, "auth_hmac_invalid")

    def test_timestamp_skew_denies(self):
        self._setup_basic_client()
        # 90s in past — outside ±60s window.
        ts = int(time.time() * 1000) - 90_000
        token = _make_token(_CLIENT_ID, _NONCE, ts, _SECRET)
        ctx, reason, _ = dispatch.authenticate(
            raw_token=token,
            timestamp_ms=ts,
            method="list_skills",
            origin=None,
            transport="stdio",
            session_id="s",
            project_dir=self.project_dir,
        )
        self.assertIsNone(ctx)
        self.assertEqual(reason, "timestamp_skew")

    def test_acl_denies_when_handler_not_in_allowlist(self):
        self._setup_basic_client(handlers=("list_skills",))
        ts = int(time.time() * 1000)
        token = _make_token(_CLIENT_ID, _NONCE, ts, _SECRET)
        ctx, reason, _ = dispatch.authenticate(
            raw_token=token,
            timestamp_ms=ts,
            method="spawn_agent",
            origin=None,
            transport="stdio",
            session_id="s",
            project_dir=self.project_dir,
        )
        self.assertIsNone(ctx)
        self.assertEqual(reason, "acl_missing_handler")

    def test_cors_denies_on_http_with_unlisted_origin(self):
        _seed_secret(self.project_dir)
        _write_settings(
            self.project_dir,
            {
                _CLIENT_ID: {
                    "handlers": ["list_skills"],
                    "cors_origins": ["https://app.example.com"],
                }
            },
        )
        ts = int(time.time() * 1000)
        token = _make_token(_CLIENT_ID, _NONCE, ts, _SECRET)
        ctx, reason, _ = dispatch.authenticate(
            raw_token=token,
            timestamp_ms=ts,
            method="list_skills",
            origin="https://evil.example.com",
            transport="http",
            session_id="s",
            project_dir=self.project_dir,
        )
        self.assertIsNone(ctx)
        self.assertEqual(reason, "cors_default_deny")

    def test_rate_limit_denies_after_burst(self):
        self._setup_basic_client(handlers=["spawn_agent"])
        ts = int(time.time() * 1000)
        # spawn class burst=2; drain via consecutive legitimate calls.
        # PLAN-112-FOLLOWUP: distinct nonce per call (replay rejects reuse).
        for _i in range(2):
            token = _make_token(_CLIENT_ID, _fresh_nonce(_i), ts, _SECRET)
            ctx, reason, _ = dispatch.authenticate(
                raw_token=token,
                timestamp_ms=ts,
                method="spawn_agent",
                origin=None,
                transport="stdio",
                session_id="s",
                project_dir=self.project_dir,
            )
            self.assertIsNotNone(ctx, f"unexpected deny: {reason}")
        token3 = _make_token(_CLIENT_ID, _fresh_nonce(2), ts, _SECRET)
        ctx, reason, retry_ms = dispatch.authenticate(
            raw_token=token3,
            timestamp_ms=ts,
            method="spawn_agent",
            origin=None,
            transport="stdio",
            session_id="s",
            project_dir=self.project_dir,
        )
        self.assertIsNone(ctx)
        self.assertEqual(reason, "rate_limit")
        self.assertGreater(retry_ms, 0)

    def test_authenticate_succeeds_full_path(self):
        self._setup_basic_client()
        ts = int(time.time() * 1000)
        token = _make_token(_CLIENT_ID, _NONCE, ts, _SECRET)
        ctx, reason, _ = dispatch.authenticate(
            raw_token=token,
            timestamp_ms=ts,
            method="list_skills",
            origin=None,
            transport="stdio",
            session_id="s1",
            project_dir=self.project_dir,
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.client_id, _CLIENT_ID)
        self.assertEqual(ctx.session_id, "s1")


class TestDispatchHandlerSuccess(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        rate_limit.reset_registry()

    def _make_ctx(self):
        return dispatch.AuthContext(
            client_id=_CLIENT_ID,
            registry_entry={"handlers": ["list_skills"]},
            transport="stdio",
            session_id="s",
            project_dir=self.project_dir,
        )

    def test_dispatch_list_skills_emits_invoked(self):
        envelope = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "list_skills",
            "params": {},
        }
        ctx = self._make_ctx()
        resp = dispatch.dispatch(envelope, ctx, "/test")
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 7)
        self.assertIn("result", resp)
        self.assertNotIn("error", resp)
        log = self.read_audit_log()
        self.assertIn("mcp_handler_invoked", log)

    def test_dispatch_unknown_method_returns_method_not_found(self):
        envelope = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "no_such_handler",
            "params": {},
        }
        ctx = self._make_ctx()
        resp = dispatch.dispatch(envelope, ctx, "/test")
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], dispatch.ERR_METHOD_NOT_FOUND)

    def test_dispatch_handler_returns_sentinel_error_path(self):
        # get_skill with an invalid tier returns __error__ sentinel.
        envelope = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "get_skill",
            "params": {"tier": "bogus", "slug": "x"},
        }
        ctx = self._make_ctx()
        resp = dispatch.dispatch(envelope, ctx, "/test")
        self.assertIn("error", resp)
        log = self.read_audit_log()
        self.assertIn("mcp_handler_denied", log)


class TestDispatchHandlerException(TestEnvContext):
    """Handler raising an exception → ERR_INTERNAL + denied event."""

    def setUp(self) -> None:
        super().setUp()
        rate_limit.reset_registry()

    def test_handler_exception_caught_emits_denied(self):
        # Inject a raising handler into the registry.
        original = dispatch.HANDLERS.copy()
        try:
            def boom(_p, _ctx):
                raise RuntimeError("simulated")

            dispatch.HANDLERS["__test_boom__"] = ("readonly", boom)
            envelope = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "__test_boom__",
                "params": {},
            }
            ctx = dispatch.AuthContext(
                client_id=_CLIENT_ID,
                registry_entry={"handlers": ["__test_boom__"]},
                transport="stdio",
                session_id="s",
                project_dir=self.project_dir,
            )
            resp = dispatch.dispatch(envelope, ctx, "/test")
            self.assertIn("error", resp)
            self.assertEqual(resp["error"]["code"], dispatch.ERR_INTERNAL)
            log = self.read_audit_log()
            self.assertIn("mcp_handler_denied", log)
            self.assertIn("internal_error", log)
        finally:
            dispatch.HANDLERS.clear()
            dispatch.HANDLERS.update(original)


class TestHandlersRegistry(TestEnvContext):

    def test_core_handlers_registered(self):
        # PLAN-013 §S4 + ADR-042 §Auth.2 — 7 original handlers.
        # PLAN-096 Wave A/B/C/D added audit_query (27+ sub-commands),
        # plan_status (4 methods), get_debate_state, get_cost_budget.
        # Total method count is now 40+. Assert the 7 original methods
        # are present (not an exact count — PLAN-096 methods are tested
        # separately in their own handler tests).
        original_seven = {
            "list_skills",
            "get_skill",
            "list_agents",
            "list_pitfalls",
            "get_audit_log",
            "spawn_agent",
            "server.capabilities",
        }
        for method in original_seven:
            self.assertIn(
                method,
                dispatch.HANDLERS,
                f"Core handler '{method}' missing from dispatch.HANDLERS",
            )

    def test_plan096_handlers_registered(self):
        # PLAN-096 Wave B/C/D — plan_status, get_debate_state,
        # get_cost_budget added to dispatch.HANDLERS.
        for method in ("list_plans", "get_plan", "get_debate_state", "get_cost_budget"):
            self.assertIn(
                method,
                dispatch.HANDLERS,
                f"PLAN-096 handler '{method}' missing from dispatch.HANDLERS",
            )


if __name__ == "__main__":
    unittest.main()
