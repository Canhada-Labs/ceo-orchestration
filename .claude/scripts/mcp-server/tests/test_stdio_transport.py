"""Unit tests for mcp-server/stdio_transport.py — line-delimited JSON-RPC.

ADR-042 §Transport. Tests cover:
- Line-delimited JSON in → response on stdout
- Malformed JSON line handled (error response, loop continues)
- EOF clean shutdown (no error)
- Auth field stripped from params before handler sees them

Tests use io.StringIO for stdin/stdout — no subprocess.
"""

from __future__ import annotations

import io
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
import stdio_transport  # type: ignore[import-not-found]  # noqa: E402


_SECRET = b"\x42" * 32
_CLIENT_ID = "0123456789abcdef"
_NONCE = "fedcba9876543210"


def _make_token(client_id: str, nonce: str, ts_ms: int, secret: bytes) -> str:
    mac = auth.compute_hmac(client_id, nonce, ts_ms, secret)
    return f"v1.{client_id}.{nonce}.{mac}"


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


def _read_responses(stdout: io.StringIO) -> list:
    """Parse all newline-delimited JSON from stdout."""
    raw = stdout.getvalue()
    return [
        json.loads(line) for line in raw.splitlines() if line.strip()
    ]


class TestStdioTransport(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        rate_limit.reset_registry()
        # PLAN-112-FOLLOWUP — the replay store is a per-process singleton;
        # reset it per test so reusing _NONCE across cases does not bleed
        # into a spurious replay DENY.
        from _lib.mcp import bearer_replay as _br
        dispatch.set_replay_store_for_test(_br.BearerReplayStore())
        _seed_secret(self.project_dir)
        _write_settings(
            self.project_dir,
            {_CLIENT_ID: {"handlers": ["list_skills"]}},
        )

    def tearDown(self) -> None:
        dispatch.set_replay_store_for_test(None)
        super().tearDown()

    def test_happy_path_single_request(self):
        ts = int(time.time() * 1000)
        token = _make_token(_CLIENT_ID, _NONCE, ts, _SECRET)
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "list_skills",
            "params": {
                "authorization": token,
                "timestamp_ms": ts,
                "session_id": "stdio-1",
            },
        }
        stdin = io.StringIO(json.dumps(request) + "\n")
        stdout = io.StringIO()
        stdio_transport.run(self.project_dir, stdin=stdin, stdout=stdout)
        responses = _read_responses(stdout)
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0]["jsonrpc"], "2.0")
        self.assertIn("result", responses[0])

    def test_malformed_line_handled_loop_continues(self):
        ts = int(time.time() * 1000)
        token = _make_token(_CLIENT_ID, _NONCE, ts, _SECRET)
        good = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "list_skills",
            "params": {
                "authorization": token,
                "timestamp_ms": ts,
            },
        }
        # First line is malformed; second line is valid.
        stdin = io.StringIO(
            "not-valid-json\n" + json.dumps(good) + "\n"
        )
        stdout = io.StringIO()
        stdio_transport.run(self.project_dir, stdin=stdin, stdout=stdout)
        responses = _read_responses(stdout)
        # Two responses: one parse_error + one success.
        self.assertEqual(len(responses), 2)
        self.assertIn("error", responses[0])
        self.assertEqual(responses[0]["error"]["code"], dispatch.ERR_PARSE)
        self.assertIn("result", responses[1])

    def test_eof_clean_shutdown(self):
        # Empty stdin → loop exits cleanly without raising.
        stdin = io.StringIO("")
        stdout = io.StringIO()
        # Should NOT raise; should return without writing.
        stdio_transport.run(self.project_dir, stdin=stdin, stdout=stdout)
        self.assertEqual(stdout.getvalue(), "")

    def test_auth_fields_stripped_from_params(self):
        # Verifies dispatch.dispatch never sees the raw token in params.
        # Use a custom handler that returns the params it received so we
        # can assert on the cleaning.
        original = dispatch.HANDLERS.copy()
        captured = {}

        def echo_params(params, ctx):
            captured["params"] = dict(params)
            captured["ctx"] = ctx
            return {"echoed": True}

        try:
            dispatch.HANDLERS["__test_echo__"] = ("readonly", echo_params)
            _write_settings(
                self.project_dir,
                {_CLIENT_ID: {"handlers": ["__test_echo__"]}},
            )
            ts = int(time.time() * 1000)
            token = _make_token(_CLIENT_ID, _NONCE, ts, _SECRET)
            request = {
                "jsonrpc": "2.0",
                "id": 9,
                "method": "__test_echo__",
                "params": {
                    "authorization": token,
                    "timestamp_ms": ts,
                    "session_id": "stdio-x",
                    "real_arg": "keep-me",
                },
            }
            stdin = io.StringIO(json.dumps(request) + "\n")
            stdout = io.StringIO()
            stdio_transport.run(self.project_dir, stdin=stdin, stdout=stdout)
            responses = _read_responses(stdout)
            self.assertEqual(len(responses), 1)
            self.assertIn("result", responses[0])
            # The handler must have received params WITHOUT auth keys.
            params = captured.get("params", {})
            self.assertNotIn("authorization", params)
            self.assertNotIn("timestamp_ms", params)
            self.assertNotIn("session_id", params)
            self.assertEqual(params.get("real_arg"), "keep-me")
        finally:
            dispatch.HANDLERS.clear()
            dispatch.HANDLERS.update(original)


if __name__ == "__main__":
    unittest.main()
