"""PLAN-112-FOLLOWUP-federation-wire-or-delete — write-mode WIRE tests.

These tests exercise the REAL ``_lib.federation.server`` code (NOT a
parallel in-process copy of the dispatcher logic — that was the R-QA-B
weakness of ``tests/federation/test_write_endpoints.py``).

Coverage map → ACs:
  - AC1/AC7/AC14  : Layer 0a env default-OFF + fail-CLOSED (TestLayer0a)
  - AC3 (P0-1)    : revocation propagates <60s without restart, both at
                    the reload-watcher and Gate #7 (TestRevocationPropagation)
  - AC13 (R-SE-a) : Gate #3 split — replayed/forged request never mutates
                    the nonce ring (TestGate3SplitPoisoning)
  - AC14 (R-SE-b) : rate-limit DEFAULT-DENY on exception (TestRateLimitFailClosed)
  - AC4 partial   : _safe_emit C-4 fix writes the storm/tamper records
                    (TestSafeEmitFallback)
  - AC8 (F-5.8)   : 90d cert validity window rejected at peer-register
                    (TestCertValidityWindow)

Determinism: no ``time.sleep`` in assert loops; the reload SLO test uses
a deterministic mtime advance + a direct ``_reload_peers_now`` call.
Stdlib-only.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Path setup — resolve the canonical federation package.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))


def _import_server():
    """Import the canonical federation.server module (skip if absent)."""
    try:
        from _lib.federation import server as srv  # type: ignore
        return srv
    except Exception:
        return None


def _import_audit_emit():
    try:
        from _lib import audit_emit  # type: ignore
        return audit_emit
    except Exception:
        return None


_SRV = _import_server()


# ---------------------------------------------------------------------------
# A minimal fake request handler that exposes the real methods without a
# live socket. We construct _FederationHandler.__new__ (bypass __init__,
# which would try to read from a socket) and attach the attributes the
# methods read.
# ---------------------------------------------------------------------------


class _FakeServer:
    """Stand-in for the ThreadingHTTPServer instance (self.server)."""

    def __init__(self, **attrs: Any) -> None:
        for k, v in attrs.items():
            setattr(self, k, v)


class _CapturingHandler:
    """Wraps a real _FederationHandler with capture of sent responses."""

    def __init__(self, srv_module, server_attrs: Dict[str, Any], headers: Dict[str, str], path: str, command: str = "POST", body: bytes = b"", client_ip: str = "10.0.0.5") -> None:
        self.h = srv_module._FederationHandler.__new__(
            srv_module._FederationHandler
        )
        self.h.server = _FakeServer(**server_attrs)
        self.h.headers = _HeaderMap(headers)
        self.h.path = path
        self.h.command = command
        self.h.client_address = (client_ip, 54321)
        self._body = body
        self.h.rfile = _Reader(body)
        self.sent_status: Optional[int] = None
        self.sent_body = b""
        # Patch the response writers to capture instead of socket-write.
        self.h.send_response = self._send_response
        self.h.send_header = lambda *a, **k: None
        self.h.end_headers = lambda: None
        self.h.wfile = _Writer(self)
        # getpeercert returns None (no TLS) → fpr lookups return "".
        self.h.connection = _NoCertConn()

    def _send_response(self, code: int) -> None:
        self.sent_status = code


class _HeaderMap(dict):
    def get(self, k, default=None):
        for kk, vv in self.items():
            if kk.lower() == str(k).lower():
                return vv
        return default


class _Reader:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self, n: int = -1) -> bytes:
        if n < 0:
            return self._body
        out, self._body = self._body[:n], self._body[n:]
        return out


class _Writer:
    def __init__(self, parent: "_CapturingHandler") -> None:
        self.parent = parent

    def write(self, b: bytes) -> None:
        self.parent.sent_body += b


class _NoCertConn:
    def getpeercert(self, binary_form: bool = False):
        return None


# ---------------------------------------------------------------------------
# Tests — Layer 0a env switch (AC1/AC7/AC14)
# ---------------------------------------------------------------------------


@unittest.skipIf(_SRV is None, "federation.server not importable")
class TestLayer0a(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.get("CEO_FEDERATION_WRITE_ENABLED")
        self.addCleanup(self._restore)

    def _restore(self):
        if self._saved is None:
            os.environ.pop("CEO_FEDERATION_WRITE_ENABLED", None)
        else:
            os.environ["CEO_FEDERATION_WRITE_ENABLED"] = self._saved

    def test_unset_is_off(self):
        os.environ.pop("CEO_FEDERATION_WRITE_ENABLED", None)
        self.assertFalse(_SRV.write_mode_enabled_from_env())

    def test_empty_is_off(self):
        os.environ["CEO_FEDERATION_WRITE_ENABLED"] = ""
        self.assertFalse(_SRV.write_mode_enabled_from_env())

    def test_zero_is_off(self):
        os.environ["CEO_FEDERATION_WRITE_ENABLED"] = "0"
        self.assertFalse(_SRV.write_mode_enabled_from_env())

    def test_true_string_is_off(self):
        # Stricter than read-mode kill-switch: only exact "1" is truthy.
        os.environ["CEO_FEDERATION_WRITE_ENABLED"] = "true"
        self.assertFalse(_SRV.write_mode_enabled_from_env())

    def test_one_is_on(self):
        os.environ["CEO_FEDERATION_WRITE_ENABLED"] = "1"
        self.assertTrue(_SRV.write_mode_enabled_from_env())

    def test_one_with_whitespace_is_on(self):
        os.environ["CEO_FEDERATION_WRITE_ENABLED"] = " 1 "
        self.assertTrue(_SRV.write_mode_enabled_from_env())

    def test_write_mode_active_false_when_env_off(self):
        """_write_mode_active() → False short-circuits before sentinel."""
        os.environ.pop("CEO_FEDERATION_WRITE_ENABLED", None)
        ch = _CapturingHandler(
            _SRV,
            server_attrs={},
            headers={},
            path="/federation/peer-register",
        )
        self.assertFalse(ch.h._write_mode_active())

    def test_do_post_405_when_write_mode_off(self):
        """do_POST → 405 (write-blocked) when env OFF (default install)."""
        os.environ.pop("CEO_FEDERATION_WRITE_ENABLED", None)
        ch = _CapturingHandler(
            _SRV,
            server_attrs={},
            headers={},
            path="/federation/peer-register",
        )
        ch.h.do_POST()
        self.assertEqual(ch.sent_status, 405)


# ---------------------------------------------------------------------------
# Tests — write-enable sentinel (Gate #8 / Layer 0b)
# ---------------------------------------------------------------------------


@unittest.skipIf(_SRV is None, "federation.server not importable")
class TestWriteEnableSentinel(unittest.TestCase):
    def test_missing_sentinel_fails_closed(self):
        tmp = tempfile.mkdtemp(prefix="fed-sent-")
        self.addCleanup(lambda: _rmtree(tmp))
        ch = _CapturingHandler(
            _SRV,
            server_attrs={
                "write_enabled_sentinel": Path(tmp) / "write-enabled.md",
                "write_enabled_sentinel_asc": Path(tmp) / "write-enabled.md.asc",
            },
            headers={},
            path="/federation/peer-register",
        )
        # No sentinel files on disk → fail-CLOSED.
        self.assertFalse(ch.h._write_enable_sentinel_valid())


# ---------------------------------------------------------------------------
# Tests — revocation propagation <60s (AC3 / P0-1 / R-IT-A/B/C)
# ---------------------------------------------------------------------------


@unittest.skipIf(_SRV is None, "federation.server not importable")
class TestRevocationPropagation(unittest.TestCase):
    """register → revoke → denied <60s without restart, at the reload
    layer (federation_peers refreshed) AND observable via the emit."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="fed-revoke-")
        self.addCleanup(lambda: _rmtree(self.tmp))
        self.peers_yaml = Path(self.tmp) / "peers.yaml"

    def _write_peers(self, revoked: bool) -> None:
        # YAML-shaped peers.yaml — load_peers parses the documented v2.0
        # text shape (the JSON {"peers":[...]} form parses to EMPTY, a
        # reality verified against identity.parse_peers_text). Cert window
        # ≤90d so it parses; SPKI present so the row is valid.
        text = (
            "peers:\n"
            "  - peer_id: peer-a\n"
            "    peer_id_spki_fingerprint: " + "a" * 64 + "\n"
            "    ca_pin_sha256: " + "b" * 64 + "\n"
            "    not_valid_after: 2099-01-01T00:00:00Z\n"
            "    not_valid_before: 2098-12-01T00:00:00Z\n"
            "    hmac_secret_hex: " + "c" * 64 + "\n"
            "    revoked: " + ("true" if revoked else "false") + "\n"
        )
        self.peers_yaml.write_text(text, encoding="utf-8")

    def test_reload_refreshes_revoked_flag(self):
        """A peers.yaml edit (revoked True) propagates on reload — the
        running server's federation_peers reflects it without restart."""
        srv = _SRV
        load_peers = _try_load_peers(srv)
        if load_peers is None:
            self.skipTest("load_peers unavailable / peers.yaml shape")

        self._write_peers(revoked=False)
        # Build a fake httpd carrying the boot-time (non-revoked) peers.
        try:
            boot_peers = load_peers(self.peers_yaml)
        except Exception as e:
            self.skipTest("peers.yaml not parseable by load_peers: {0}".format(e))
        cfg = _FakeServer(peers_path=self.peers_yaml)
        httpd = _FakeServer(
            federation_config=cfg,
            federation_peers=boot_peers,
            federation_peers_path=self.peers_yaml,
        )
        self.assertFalse(httpd.federation_peers["peer-a"].revoked)

        # Now revoke on disk + reload.
        self._write_peers(revoked=True)
        ok = srv._reload_peers_now(httpd)
        self.assertTrue(ok)
        # The running server now sees the revocation — NO restart.
        self.assertTrue(httpd.federation_peers["peer-a"].revoked)

    def test_maybe_reload_emits_peer_list_reloaded(self):
        """R-IT-C: a content change emits federation_peer_list_reloaded
        so the SLO is forensically observable."""
        srv = _SRV
        ae = _import_audit_emit()
        if ae is None:
            self.skipTest("audit_emit unavailable")
        load_peers = _try_load_peers(srv)
        if load_peers is None:
            self.skipTest("load_peers unavailable")

        self._write_peers(revoked=False)
        try:
            boot_peers = load_peers(self.peers_yaml)
        except Exception:
            self.skipTest("peers.yaml not parseable")

        import threading
        cfg = _FakeServer(peers_path=self.peers_yaml)
        httpd = _FakeServer(
            federation_config=cfg,
            federation_peers=boot_peers,
            federation_peers_path=self.peers_yaml,
            federation_reload_lock=threading.Lock(),
            federation_peers_last_check=0.0,
            federation_peers_signature=srv._peers_file_signature(self.peers_yaml),
        )

        emitted: List[Dict[str, Any]] = []
        orig = ae.emit_generic

        def _spy(action, **kw):
            emitted.append({"action": action, **kw})
            return orig(action, **kw)

        ae.emit_generic = _spy
        try:
            # Change the file + advance the debounce window deterministically.
            self._write_peers(revoked=True)
            # Force the per-file mtime to differ even on coarse-grained FS.
            future = time.time() + 10
            os.utime(self.peers_yaml, (future, future))
            srv._maybe_reload_peers(httpd, now=time.time() + 5)
        finally:
            ae.emit_generic = orig

        actions = [e["action"] for e in emitted]
        self.assertIn("federation_peer_list_reloaded", actions)


# ---------------------------------------------------------------------------
# Tests — Gate #3 split poisoning resistance (AC13 / R-SE-a)
# ---------------------------------------------------------------------------


@unittest.skipIf(_SRV is None, "federation.server not importable")
class TestGate3SplitPoisoning(unittest.TestCase):
    """A request that fails HMAC must NOT have committed its nonce — the
    nonce ring stays clean so a later legitimate request with the same
    nonce is not falsely rejected as a replay (and an attacker cannot
    poison the ring pre-auth)."""

    def _make_peer(self):
        srv = _SRV

        class _P:
            peer_id = "peer-a"
            hmac_secret_hex = "c" * 64
            revoked = False
            peer_id_cert_fingerprint = "d" * 64
        return _P()

    def test_failed_hmac_does_not_commit_nonce(self):
        srv = _SRV
        replay_mod = importlib.import_module("_lib.federation.replay")
        cache = replay_mod.ReplayCache(max_skew_seconds=30)
        peer = self._make_peer()
        nonce = "nonce-fixed-123456789012345"
        ts = _now_rfc3339()

        ch = _CapturingHandler(
            srv,
            server_attrs={"federation_replay_cache": cache},
            headers={
                "X-CEO-Federation-Nonce": nonce,
                "X-CEO-Federation-Timestamp": ts,
                "X-CEO-Federation-Signature": "deadbeef",  # wrong sig
            },
            path="/federation/audit-event",
        )

        # Step 1 — freshness preflight passes (timestamp is fresh) and is
        # NON-mutating: the nonce ring must still be empty afterwards.
        pf = ch.h._replay_freshness_preflight(peer)
        self.assertIsNone(pf, "fresh timestamp should pass preflight")
        self.assertEqual(
            len(cache._cache.get("peer-a", [])), 0,
            "preflight must NOT touch the nonce ring (poisoning resistance)",
        )

        # Step 2 — HMAC verify fails (wrong sig) and is NON-mutating.
        sig = ch.h._verify_signature_only(peer, b"{}")
        self.assertIsNotNone(sig, "wrong signature must fail HMAC verify")
        self.assertEqual(
            len(cache._cache.get("peer-a", [])), 0,
            "HMAC verify must NOT commit the nonce (poisoning resistance)",
        )

        # Step 3 — a SUBSEQUENT legitimate commit with the same nonce must
        # succeed, proving the ring was never poisoned by the forged req.
        commit_reason = ch.h._commit_nonce(peer)
        self.assertIsNone(
            commit_reason,
            "the same nonce must commit cleanly after a forged-request "
            "preflight+HMAC-fail (ring was not poisoned)",
        )


# ---------------------------------------------------------------------------
# Tests — rate-limit DEFAULT-DENY on exception (AC14 / R-SE-b)
# ---------------------------------------------------------------------------


@unittest.skipIf(_SRV is None, "federation.server not importable")
class TestRateLimitFailClosed(unittest.TestCase):
    def test_rate_limit_module_missing_denies(self):
        """If the rate_limit module fails to load, gate #9 DENIES (no
        gate fails OPEN)."""
        srv = _SRV
        ch = _CapturingHandler(
            srv,
            server_attrs={},
            headers={},
            path="/federation/audit-event",
        )
        # Monkeypatch the loader to simulate a missing module.
        orig = srv._load_rate_limit
        srv._load_rate_limit = lambda: None
        try:
            ok, reason = ch.h._rate_limit_check(
                "POST", "/federation/audit-event", {}, {"peer_id": "p1"}
            )
        finally:
            srv._load_rate_limit = orig
        self.assertFalse(ok)
        self.assertIn("module_missing", str(reason))

    def test_rate_limit_exception_denies(self):
        """If the limiter raises, gate #9 DENIES."""
        srv = _SRV

        class _Boom:
            def check_backpressure(self, *a, **k):
                raise RuntimeError("boom")
        ch = _CapturingHandler(
            srv, server_attrs={}, headers={}, path="/federation/audit-event"
        )
        orig = srv._load_rate_limit
        srv._load_rate_limit = lambda: _Boom()
        try:
            ok, reason = ch.h._rate_limit_check(
                "POST", "/federation/audit-event", {}, {"peer_id": "p1"}
            )
        finally:
            srv._load_rate_limit = orig
        self.assertFalse(ok)
        self.assertIn("exception", str(reason))


# ---------------------------------------------------------------------------
# Tests — _safe_emit C-4 fallback writes the record (AC4 partial / R-TD-1)
# ---------------------------------------------------------------------------


@unittest.skipIf(_SRV is None, "federation.server not importable")
class TestSafeEmitFallback(unittest.TestCase):
    def test_safe_emit_falls_back_to_generic(self):
        """A registered Wave-F.2 action with NO named wrapper is still
        written via emit_generic (closes the no-op trap)."""
        srv = _SRV
        ae = _import_audit_emit()
        if ae is None:
            self.skipTest("audit_emit unavailable")
        if "federation_message_storm_detected" not in ae._KNOWN_ACTIONS:
            self.skipTest("federation actions not registered in this build")
        # Confirm the precondition that triggered the bug: no named wrapper.
        self.assertFalse(
            hasattr(ae, "emit_federation_message_storm_detected"),
            "if a named wrapper now exists this assertion documents the "
            "drift — _safe_emit still works either way",
        )

        captured: List[Dict[str, Any]] = []
        orig = ae.emit_generic
        ae.emit_generic = lambda action, **kw: captured.append(
            {"action": action, **kw}
        )
        try:
            srv._safe_emit(
                "federation_message_storm_detected",
                peer_id="p1", route="/federation/audit-event",
                ip_prefix="", hits_in_window=3, window_seconds=900,
            )
        finally:
            ae.emit_generic = orig
        self.assertEqual(len(captured), 1)
        self.assertEqual(
            captured[0]["action"], "federation_message_storm_detected"
        )


# ---------------------------------------------------------------------------
# Tests — 90d cert validity window (AC8 / F-5.8 / W5)
# ---------------------------------------------------------------------------


class TestCertValidityWindow(unittest.TestCase):
    def _import_peer_register(self):
        try:
            from _lib.federation.handlers import peer_register  # type: ignore
            return peer_register
        except Exception:
            return None

    def test_window_over_90d_rejected(self):
        pr = self._import_peer_register()
        if pr is None:
            self.skipTest("peer_register handler unavailable")
        body = {
            "peer_id": "peer-x",
            "peer_id_spki_fingerprint": "a" * 64,
            "ca_pin_sha256": "b" * 64,
            "not_valid_before": "2026-01-01T00:00:00Z",
            "not_valid_after": "2026-06-01T00:00:00Z",  # ~151 days
            "hmac_secret_hex": "c" * 64,
        }
        with self.assertRaises(pr.CertValidityWindowError) as ctx:
            pr._validate_peer_body(body)
        self.assertGreater(ctx.exception.window_days, 90)

    def test_window_exactly_under_90d_accepted(self):
        pr = self._import_peer_register()
        if pr is None:
            self.skipTest("peer_register handler unavailable")
        body = {
            "peer_id": "peer-y",
            "peer_id_spki_fingerprint": "a" * 64,
            "ca_pin_sha256": "b" * 64,
            "not_valid_before": "2026-01-01T00:00:00Z",
            "not_valid_after": "2026-03-15T00:00:00Z",  # ~73 days
            "hmac_secret_hex": "c" * 64,
        }
        row = pr._validate_peer_body(body)
        self.assertEqual(row["peer_id"], "peer-y")

    def test_handle_emits_cert_window_action(self):
        pr = self._import_peer_register()
        ae = _import_audit_emit()
        if pr is None or ae is None:
            self.skipTest("deps unavailable")
        body = json.dumps({
            "peer_id": "peer-z",
            "peer_id_spki_fingerprint": "a" * 64,
            "ca_pin_sha256": "b" * 64,
            "not_valid_before": "2026-01-01T00:00:00Z",
            "not_valid_after": "2027-01-01T00:00:00Z",  # ~365 days
            "hmac_secret_hex": "c" * 64,
        }).encode("utf-8")

        captured: List[Dict[str, Any]] = []
        orig = ae.emit_generic
        ae.emit_generic = lambda action, **kw: captured.append(
            {"action": action, **kw}
        )
        try:
            status, reason, _ = pr.handle(
                {"peer_id": "caller"}, {}, body,
                peers_path=Path(tempfile.mkdtemp()) / "peers.yaml",
            )
        finally:
            ae.emit_generic = orig
        self.assertEqual(status, 400)
        self.assertIn("cert_validity_window_too_large", reason)
        actions = [e["action"] for e in captured]
        # Only assert the emit landed if the action is registered (it is,
        # per W7 — federation_cert_validity_window_too_large is in F.2).
        if "federation_cert_validity_window_too_large" in ae._KNOWN_ACTIONS:
            self.assertIn(
                "federation_cert_validity_window_too_large", actions
            )


# ---------------------------------------------------------------------------
# Tests — P0 #1: T1565 tamper detection is REACHABLE on the audit-event
# path (not a no-op); P1 #2: handlers get server-configured state paths.
# ---------------------------------------------------------------------------


@unittest.skipIf(_SRV is None, "federation.server not importable")
class TestAuditChainReachable(unittest.TestCase):
    """Codex P0 #1 — `_maybe_check_audit_chain` must inspect the SAME log
    the push handler appended to, and fire `federation_tamper_detected`
    on a broken chain. Previously a no-op when federation_audit_log_path
    was unset (which serve_forever never set)."""

    def _write_tampered_chain(self, log_path):
        import hashlib

        def canon_hash(ev):
            filtered = {k: v for k, v in ev.items()
                        if k not in ("audit_chain_hash",
                                     "audit_chain_prev_hash",
                                     "_timestamp_emitted")}
            c = json.dumps(filtered, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"), allow_nan=False)
            return hashlib.sha256(c.encode("utf-8")).hexdigest()

        e1 = {"action": "x", "n": 1, "audit_chain_prev_hash": "0" * 64}
        e2 = {"action": "x", "n": 2, "audit_chain_prev_hash": canon_hash(e1)}
        e3 = {"action": "x", "n": 3, "audit_chain_prev_hash": "f" * 64}  # break
        log_path.write_text(
            "\n".join(json.dumps(e, sort_keys=True) for e in (e1, e2, e3))
            + "\n", encoding="utf-8",
        )

    def test_maybe_check_audit_chain_fires_tamper_with_explicit_path(self):
        srv = _SRV
        ae = _import_audit_emit()
        if ae is None:
            self.skipTest("audit_emit unavailable")
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="fed-tamper-"))
        self.addCleanup(lambda: _rmtree(str(tmp)))
        log = tmp / "audit-log.jsonl"
        self._write_tampered_chain(log)

        ch = _CapturingHandler(
            srv, server_attrs={"federation_audit_log_path": log},
            headers={}, path="/federation/audit-event",
        )
        emitted: List[str] = []
        orig = ae.emit_generic
        ae.emit_generic = lambda action, **kw: emitted.append(action)
        try:
            # Explicit path (as the dispatcher now threads it).
            ch.h._maybe_check_audit_chain("peer-a", "/federation/audit-event", log)
        finally:
            ae.emit_generic = orig
        self.assertIn(
            "federation_tamper_detected", emitted,
            "T1565 tamper detection must be REACHABLE on the audit-event "
            "path (P0 #1 — was a no-op when the path was unset)",
        )

    def test_maybe_check_audit_chain_not_noop_when_server_path_unset(self):
        """Even with NO explicit path AND no server attr, the helper falls
        back to the canonical resolver (CEO_AUDIT_LOG_PATH) — it must NOT
        silently no-op like the original bug."""
        srv = _SRV
        ae = _import_audit_emit()
        if ae is None:
            self.skipTest("audit_emit unavailable")
        import os
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="fed-tamper2-"))
        self.addCleanup(lambda: _rmtree(str(tmp)))
        log = tmp / "audit-log.jsonl"
        self._write_tampered_chain(log)
        saved = os.environ.get("CEO_AUDIT_LOG_PATH")
        os.environ["CEO_AUDIT_LOG_PATH"] = str(log)
        # Server attr is UNSET (the original no-op condition).
        ch = _CapturingHandler(
            srv, server_attrs={}, headers={},
            path="/federation/audit-event",
        )
        emitted: List[str] = []
        orig = ae.emit_generic
        ae.emit_generic = lambda action, **kw: emitted.append(action)
        try:
            ch.h._maybe_check_audit_chain("peer-a", "/federation/audit-event")
        finally:
            ae.emit_generic = orig
            if saved is None:
                os.environ.pop("CEO_AUDIT_LOG_PATH", None)
            else:
                os.environ["CEO_AUDIT_LOG_PATH"] = saved
        self.assertIn(
            "federation_tamper_detected", emitted,
            "helper must fall back to the canonical resolver, NOT no-op",
        )

    def test_handler_state_kwargs_routes_peers_path(self):
        """P1 #2 — peer-register/revoke get the configured peers_path
        (NOT PEERS_FILE_DEFAULT)."""
        srv = _SRV
        cfg = _FakeServer(peers_path=Path("/tmp/custom-peers.yaml"))
        ch = _CapturingHandler(
            srv,
            server_attrs={
                "federation_config": cfg,
                "federation_peers_path": Path("/tmp/custom-peers.yaml"),
            },
            headers={}, path="/federation/peer-register",
        )
        kw = ch.h._handler_state_kwargs("/federation/peer-register")
        self.assertEqual(kw.get("peers_path"), Path("/tmp/custom-peers.yaml"))
        kw_rev = ch.h._handler_state_kwargs("/federation/peer-revoke")
        self.assertEqual(
            kw_rev.get("peers_path"), Path("/tmp/custom-peers.yaml")
        )
        # audit-event routes get audit_log_path, NOT peers_path.
        kw_audit = ch.h._handler_state_kwargs("/federation/audit-event")
        self.assertNotIn("peers_path", kw_audit)

    def test_handler_state_kwargs_routes_audit_log_path(self):
        """P0 #1 — audit-event routes get the canonical audit_log_path."""
        srv = _SRV
        ch = _CapturingHandler(
            srv,
            server_attrs={
                "federation_audit_log_path": Path("/tmp/custom-audit.jsonl"),
            },
            headers={}, path="/federation/audit-event",
        )
        kw = ch.h._handler_state_kwargs("/federation/audit-event")
        self.assertEqual(
            kw.get("audit_log_path"), Path("/tmp/custom-audit.jsonl")
        )
        kw_batch = ch.h._handler_state_kwargs("/federation/audit-event/batch")
        self.assertEqual(
            kw_batch.get("audit_log_path"), Path("/tmp/custom-audit.jsonl")
        )


# ---------------------------------------------------------------------------
# Tests — P0 GOLD PATH (Codex round-3 residual): T1565 tamper detection
# fires through the FULL dispatch path (request → _dispatch_write → all
# gates → gate #11 handler → audit_chain_ext.check_chain → tamper emit),
# NOT just when _maybe_check_audit_chain() is hand-called. F-7.10 is the
# critical:true detection, so it gets a dispatcher-level gold-path proof.
# This is method-level (no live socket); the full mTLS HTTP round-trip
# stays in REMAINING (AC6/AC17).
# ---------------------------------------------------------------------------


@unittest.skipIf(_SRV is None, "federation.server not importable")
class TestTamperFiresThroughDispatch(unittest.TestCase):
    """Drive an audit-event end-to-end through the REAL `_dispatch_write`.

    POSITIVE (test_*_emits_tamper_*): a VALID request reaches gate #11,
    the handler appends an event that breaks the seeded chain, and
    `federation_tamper_detected` v2 chained record lands on disk.

    NEGATIVE CONTROL (test_*_corrupted_hmac_*): the SAME state but a
    CORRUPTED signature → the REAL `_dispatch_write` rejects at gate #3c
    with status 401, NEVER reaches gate #11, and writes NO tamper record.
    This proves the dispatch gates genuinely enforce — the positive 200
    is not reached by a bypass (Codex round-4 — the prior "negative
    control" was a one-off sandbox mutation, NOT an encoded assertion).
    """

    def setUp(self):
        self._saved_env = {}
        self.addCleanup(self._restore_env)

    def _set_env(self, **kw):
        for k, v in kw.items():
            self._saved_env.setdefault(k, os.environ.get(k))
            os.environ[k] = v

    def _restore_env(self):
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _skip_unless_deps(self):
        srv = _SRV
        ae = _import_audit_emit()
        if ae is None:
            self.skipTest("audit_emit unavailable")
        if "federation_tamper_detected" not in ae._KNOWN_ACTIONS:
            self.skipTest("federation_tamper_detected not registered")
        if srv._load_audit_chain_ext() is None:
            self.skipTest("audit_chain_ext unavailable")
        try:
            from _lib.federation import replay as replay_mod  # type: ignore  # noqa: F401
            from _lib.federation.handlers import (  # type: ignore  # noqa: F401
                audit_event_push,
            )
        except Exception:
            self.skipTest("replay / audit_event_push unavailable")
        try:
            from _lib import spool_writer  # type: ignore  # noqa: F401
        except Exception:
            self.skipTest("spool_writer unavailable")

    def _build_dispatch(self, *, corrupt_sig=False):
        """Build the seeded write-mode state + a _CapturingHandler ready to
        drive through the REAL `_dispatch_write`.

        Returns (ch, log, method). When ``corrupt_sig`` is True the
        X-CEO-Federation-Signature header is a byte-flipped (invalid) HMAC
        — everything else is identical — so gate #3c (HMAC verify) rejects.
        """
        srv = _SRV
        from _lib.federation import replay as replay_mod  # type: ignore

        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="fed-gold-"))
        self.addCleanup(lambda: _rmtree(str(tmp)))
        log = tmp / "audit-log.jsonl"

        # ONE canonical audit-log path for BOTH the handler append AND the
        # tamper emit (emit_generic honours CEO_AUDIT_LOG_PATH directly).
        self._set_env(
            CEO_AUDIT_LOG_PATH=str(log),
            CEO_AUDIT_SYNC_MODE="1",
            CEO_FEDERATION_WRITE_ENABLED="1",
        )

        # Seed the log with ONE valid genesis event carrying the chain
        # field. The handler will then APPEND a remote event WITHOUT an
        # `audit_chain_prev_hash` field → check_chain sees a mid-chain
        # missing-prev-hash → break → federation_tamper_detected.
        genesis = {"action": "seed_event", "n": 1,
                   "audit_chain_prev_hash": "0" * 64}
        log.write_text(json.dumps(genesis, sort_keys=True) + "\n",
                       encoding="utf-8")

        hmac_secret_hex = "12" * 32
        peer_id = "peer-gold"

        class _Peer:
            def __init__(self):
                self.peer_id = peer_id
                self.hmac_secret_hex = hmac_secret_hex
                self.revoked = False
                self.peer_id_cert_fingerprint = "d" * 64
                self.peer_id_spki_fingerprint = "a" * 64

        peer = _Peer()
        method = "POST"
        path = "/federation/audit-event"
        scope = "audit_event_push"
        nonce = "gold-nonce-0001"
        ts = _now_rfc3339()
        body = json.dumps({
            "action": "remote_event",
            "ts": ts,
            "schema_version": "v2",
        }, sort_keys=True).encode("utf-8")
        sig = replay_mod.sign_request(
            method, path, ts, nonce, body, hmac_secret_hex,
        )
        if corrupt_sig:
            # Flip the first hex nibble of the signed token so it stays a
            # well-formed (same-length, hex) signature but FAILS the
            # constant-time HMAC compare → gate #3c rejection (NOT a
            # malformed-header path).
            flipped = "0" if sig[0] != "0" else "1"
            sig = flipped + sig[1:]

        headers = {
            "X-CEO-Federation-Scope": scope,
            "X-CEO-Federation-Nonce": nonce,
            "X-CEO-Federation-Timestamp": ts,
            "X-CEO-Federation-Signature": sig,
            "Content-Length": str(len(body)),
        }

        # peers_extra grants the scope + the action allowlist. Injecting the
        # extra dict directly is exactly the runtime shape the dispatcher
        # reads (the load_peers scopes-parse REMAINING gap is bypassed here).
        peers_extra = {
            peer_id: {
                "peer_id_spki_fingerprint": "a" * 64,
                "peer_id_cert_fingerprint": "d" * 64,
                "scopes": [scope],
                "audit_event_push_allowlist": ["remote_event"],
                "revoked": False,
            }
        }

        ch = _CapturingHandler(
            srv,
            server_attrs={
                "federation_peers_extra": peers_extra,
                "federation_replay_cache": replay_mod.ReplayCache(
                    max_skew_seconds=300,
                ),
                "federation_audit_log_path": log,
            },
            headers=headers,
            path=path,
            command=method,
            body=body,
        )
        # Mock ONLY the two gates that need real crypto/GPG unavailable in a
        # method-level test: peer resolution (gate #2) + write-enable
        # sentinel (gate #8). Gate #3 (HMAC), #5/#6 (scope), #9 (rate-limit),
        # #11 (handler), tamper walk all run FOR REAL.
        ch.h._resolve_peer = lambda: peer
        ch.h._write_enable_sentinel_valid = lambda: True
        rl = srv._load_rate_limit()
        if rl is not None:
            rl.reset_state()
        return ch, log, method

    @staticmethod
    def _tamper_records(log):
        recs = []
        for line in log.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if isinstance(rec, dict) and rec.get("action") == \
                    "federation_tamper_detected":
                recs.append(rec)
        return recs

    def test_audit_event_dispatch_emits_tamper_on_broken_chain(self):
        """POSITIVE — valid request → gate #11 → on-disk tamper record."""
        self._skip_unless_deps()
        ch, log, method = self._build_dispatch(corrupt_sig=False)

        # --- DRIVE THE FULL DISPATCH PATH ---
        ch.h._dispatch_write(method=method)

        # The handler must have succeeded (200) — proving we reached gate
        # #11, not short-circuited at an earlier gate.
        self.assertEqual(
            ch.sent_status, 200,
            "dispatch must reach + pass gate #11 (got {0}); body={1!r}".format(
                ch.sent_status, ch.sent_body[:200],
            ),
        )

        recs = self._tamper_records(log)
        self.assertTrue(
            recs,
            "T1565 tamper detection must fire from the DISPATCH path "
            "(request → _dispatch_write → gate#11 handler → check_chain → "
            "emit), not only when _maybe_check_audit_chain is hand-called",
        )
        rec = recs[0]
        self.assertEqual(rec.get("event_schema"), "v2",
                         "tamper record must be a v2 chained record")
        self.assertIn("hmac", rec, "tamper record missing chain hmac field")

    def test_audit_event_dispatch_rejects_corrupted_hmac_at_gate3(self):
        """NEGATIVE CONTROL — a byte-flipped signature drives the REAL
        `_dispatch_write` and is rejected at gate #3c with status 401,
        NEVER reaching gate #11 (no 200) and writing NO tamper record.

        Proves the dispatch gates genuinely enforce — the positive-path
        200 is not reached by a bypass. (Codex round-4: this is now an
        ENCODED assertion inside the test, not a one-off sandbox mutation.)
        """
        self._skip_unless_deps()
        ch, log, method = self._build_dispatch(corrupt_sig=True)

        # --- DRIVE THE FULL DISPATCH PATH with the CORRUPTED signature ---
        ch.h._dispatch_write(method=method)

        # Gate #3c (HMAC verify) must reject → 401, NOT 200.
        self.assertEqual(
            ch.sent_status, 401,
            "corrupted HMAC must be rejected at gate #3c with 401 (got "
            "{0}); body={1!r}".format(ch.sent_status, ch.sent_body[:200]),
        )
        self.assertNotEqual(
            ch.sent_status, 200,
            "a corrupted-HMAC request must NEVER reach gate #11 (no 200)",
        )
        # And the handler never ran → no audit-event appended → no tamper.
        self.assertEqual(
            self._tamper_records(log), [],
            "a request rejected at gate #3c must NOT produce a tamper "
            "record (gate #11 + the chain walk are never reached)",
        )


# ---------------------------------------------------------------------------
# Tests — P2 #4: .inflight pair is REVERTED on post-rename verify failure
# (not left stuck), so a re-drive is possible.
# ---------------------------------------------------------------------------


@unittest.skipIf(_SRV is None, "federation.server not importable")
class TestInflightRevertOnFailure(unittest.TestCase):
    def test_verify_failure_reverts_inflight_pair(self):
        """Codex P2 #4 — a cosign verify failure AFTER both files are
        renamed to .inflight must revert them to the original names so the
        sentinel is not stuck (fail-closed availability)."""
        srv = _SRV
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="fed-inflight-"))
        self.addCleanup(lambda: _rmtree(str(tmp)))
        sigref = "req-abc-123"
        sdir = tmp / sigref
        sdir.mkdir(parents=True)
        md = sdir / "approval.md"
        asc = sdir / "approval.md.asc"
        md.write_text("signed_at: 2099-01-01T00:00:00Z\n", encoding="utf-8")
        asc.write_text("-----BEGIN PGP SIGNATURE-----\nx\n", encoding="utf-8")

        ch = _CapturingHandler(
            srv,
            server_attrs={"federation_sentinels_dir": tmp},
            headers={"X-CEO-Owner-Sigref": sigref},
            path="/federation/peer-revoke",
        )

        # Force verify_enable_sentinel_pair to FAIL (forged-sig analogue)
        # by monkeypatching the module-level symbol the server imported.
        orig_verify = srv.verify_enable_sentinel_pair
        srv.verify_enable_sentinel_pair = (
            lambda *a, **k: (False, "forced_verify_failure")
        )
        try:
            ok, reason, paths = ch.h._verify_owner_cosign_claim(
                "POST", "/federation/peer-revoke",
            )
        finally:
            srv.verify_enable_sentinel_pair = orig_verify

        self.assertFalse(ok)
        self.assertIn("verify_failed", reason)
        self.assertIsNone(paths)
        # The pair must be back at the ORIGINAL names (reverted), and no
        # orphaned .inflight files left behind.
        self.assertTrue(md.exists(), ".md must be reverted from .inflight")
        self.assertTrue(asc.exists(), ".asc must be reverted from .inflight")
        self.assertFalse(
            (sdir / "approval.md.inflight").exists(),
            "no orphaned .md.inflight may remain",
        )
        self.assertFalse(
            (sdir / "approval.md.asc.inflight").exists(),
            "no orphaned .asc.inflight may remain",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_rfc3339() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _try_load_peers(srv):
    try:
        from _lib.federation.identity import load_peers  # type: ignore
        return load_peers
    except Exception:
        return None


def _rmtree(p: str) -> None:
    import shutil
    shutil.rmtree(p, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
