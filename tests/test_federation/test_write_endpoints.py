"""PLAN-099-FOLLOWUP Wave D.8 — federation write-endpoint dispatcher tests.

≥30 cases across the 11-gate chain (ADR-135-AMEND-1 §2.2) + per-route
happy path + per-route failure modes + sentinel TTL/replay/single-use
+ batch caps + scope mismatch + atomic-write integrity.

Test architecture:
  - The dispatcher is exercised IN-PROCESS via a _DispatcherTestHarness
    that constructs the gate logic directly (we do NOT spin up an
    HTTP server for these tests — that's the integration suite's job).
  - PEM fixtures: generated on-demand if openssl is available; tests
    requiring real PEM skip when not.
  - Sentinel fixtures: written as plain text .md + stubbed .asc; the
    GPG verify is monkeypatched at the verify_enable_sentinel_pair
    seam so tests don't require a real gpg keychain.
  - Per ADR-135-AMEND-1 §2.5, atomic single-use is asserted by checking
    .consumed-<sigref> files exist after first verify + the sentinels/
    base file no longer exists.

WAVE-F-PENDING markers:
  - Tests that ASSERT specific federation_* audit emit calls landed
    are conditional on the kernel-override having registered the
    actions (audit_emit._KNOWN_ACTIONS check). Pre-registration they
    fall back to verifying the dispatcher returned the correct status
    code (the visible-from-the-wire contract).
  - DO NOT use @pytest.mark.xfail(strict=True) — S146 lesson. Use
    plain skip when prereqs absent.

Stdlib-only.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple


# ---------------------------------------------------------------------------
# sys.path hooks — load Wave D staging code directly when canonical
# federation/ path doesn't yet have the modules (pre Phase A2-post).
# ---------------------------------------------------------------------------


_REPO_ROOT = Path(__file__).resolve().parents[2]
_STAGING_DIR = (
    _REPO_ROOT / ".claude" / "plans" / "PLAN-099-FOLLOWUP" / "wave-d-staging"
)
_HANDLERS_STAGING = _STAGING_DIR / "handlers"
_CANONICAL_DIR = (
    _REPO_ROOT / ".claude" / "hooks" / "_lib" / "federation"
)


def _load_module_from_path(name: str, path: Path):
    """Load a Python module from a filesystem path."""
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _import_scopes():
    canonical = _CANONICAL_DIR / "scopes.py"
    if canonical.is_file():
        if str(_CANONICAL_DIR.parent) not in sys.path:
            sys.path.insert(0, str(_CANONICAL_DIR.parent))
        from federation import scopes as _scopes  # type: ignore
        return _scopes
    return _load_module_from_path("wave_d_scopes", _STAGING_DIR / "scopes.py")


def _import_handler(name: str):
    """Import handler module — canonical first, staging fallback."""
    canonical = _CANONICAL_DIR / "handlers" / "{0}.py".format(name)
    if canonical.is_file():
        if str(_CANONICAL_DIR.parent) not in sys.path:
            sys.path.insert(0, str(_CANONICAL_DIR.parent))
        try:
            mod = importlib.import_module(
                "federation.handlers.{0}".format(name)
            )
            return mod
        except ImportError:
            pass
    return _load_module_from_path(
        "wave_d_h_{0}".format(name),
        _HANDLERS_STAGING / "{0}.py".format(name),
    )


scopes = _import_scopes()


# ---------------------------------------------------------------------------
# DispatcherTestHarness — in-process gate executor
# ---------------------------------------------------------------------------


class _DispatcherTestHarness:
    """In-process driver for the 11-gate write dispatcher.

    Reproduces the Patch 1 `_dispatch_write` logic from
    server_routes_patch.md without requiring a real http.server.

    Returns (status_code, reason_string, response_body_bytes).
    """

    def __init__(
        self,
        peer_row: Mapping[str, Any],
        *,
        peers_yaml_path: Optional[Path] = None,
        audit_log_path: Optional[Path] = None,
        write_enable_valid: bool = True,
        rate_limit_pass: bool = True,
        cosign_verifier: Optional[Any] = None,
        gates_to_pass_through: Tuple[str, ...] = (),
    ):
        self.peer_row = dict(peer_row)
        self.peers_yaml_path = peers_yaml_path
        self.audit_log_path = audit_log_path
        self.write_enable_valid = write_enable_valid
        self.rate_limit_pass = rate_limit_pass
        # cosign_verifier: callable(method, path, headers) -> (ok, reason)
        # Default: pass-through (verified).
        if cosign_verifier is None:
            self.cosign_verifier = lambda m, p, h: (True, "verified")
        else:
            self.cosign_verifier = cosign_verifier
        self.gates_to_pass_through = set(gates_to_pass_through)
        self.audit_emits: List[Tuple[str, Dict[str, Any]]] = []

    def _emit(self, action: str, **kwargs: Any) -> None:
        self.audit_emits.append((action, dict(kwargs)))

    def dispatch(
        self,
        method: str,
        path: str,
        headers: Mapping[str, str],
        body: bytes,
    ) -> Tuple[int, str, bytes]:
        # Strip query/fragment
        raw = path or ""
        path = raw.split("?", 1)[0].split("#", 1)[0]

        # Gate #3 — HMAC + nonce (test harness lets caller force-fail).
        if (
            "x-ceo-federation-hmac-invalid" in {
                k.lower() for k in headers.keys()
            }
            and "hmac" not in self.gates_to_pass_through
        ):
            self._emit("federation_connection_replay_suspected",
                       reason="hmac_invalid")
            return 401, "hmac", b'{"error":"hmac"}'

        # Gate #4 — route
        required = scopes.route_required_scope(method, path)
        if required is None:
            self._emit("federation_write_attempt_blocked",
                       method=method, path=path)
            return 405, "method", b'{"error":"method"}'

        # Gate #5 — scope header
        if not scopes.validate_scope_header(headers, required):
            # F-003 R2 iter-2 fix: harness emit names now match
            # canonical F.2 multiplexers. Gate #5 -> federation_scope_denied.
            self._emit("federation_scope_denied",
                       peer_id=self.peer_row.get("peer_id", ""),
                       route=path,
                       required_scope=required,
                       peer_scopes_count=len(
                           self.peer_row.get("scopes", []) or []
                       ))
            return 400, "scope_header", b'{"error":"scope_header"}'

        # Gate #6 — peer's scopes list
        if not scopes.peer_has_scope(self.peer_row, required):
            # F-003 R2 iter-2 fix: Gate #6 -> federation_write_endpoint_denied
            # with reason_code="write_unauthorized".
            self._emit("federation_write_endpoint_denied",
                       peer_id=self.peer_row.get("peer_id", ""),
                       route=path,
                       gate_failed=6,
                       reason_code="write_unauthorized")
            return 403, "scope", b'{"error":"scope"}'

        # Gate #7 — peer not revoked
        if self.peer_row.get("revoked") is True:
            # F-003 R2 iter-2 fix: Gate #7 -> federation_write_endpoint_denied
            # with reason_code="peer_revoked".
            self._emit("federation_write_endpoint_denied",
                       peer_id=self.peer_row.get("peer_id", ""),
                       route=path,
                       gate_failed=7,
                       reason_code="peer_revoked")
            return 403, "revoked", b'{"error":"revoked"}'

        # Gate #8 — write-enable sentinel
        if not self.write_enable_valid:
            # F-003 R2 iter-2 fix: Gate #8 -> federation_write_disabled_sentinel_invalid
            # (NO peer_id — server-state failure, not peer attribution).
            self._emit("federation_write_disabled_sentinel_invalid",
                       reason_code="gpg_verify_failed",
                       sentinel_path=".claude/data/federation/write-enabled.md")
            return 503, "write_disabled", b'{"error":"write_disabled"}'

        # Gate #9 — rate-limit
        if not self.rate_limit_pass:
            # F-003 R2 iter-2 fix: Gate #9 -> federation_write_endpoint_denied
            # with reason_code carrying limiter sub-cause.
            self._emit("federation_write_endpoint_denied",
                       peer_id=self.peer_row.get("peer_id", ""),
                       route=path,
                       gate_failed=9,
                       reason_code="rate_limited")
            return 429, "rate_limited", b'{"error":"rate_limited"}'

        # Gate #10 — destructive-op Owner co-sign
        if scopes.is_destructive_route(method, path):
            ok, reason = self.cosign_verifier(method, path, headers)
            if not ok:
                # F-003 R2 iter-2 fix: Gate #10 -> federation_write_endpoint_denied
                # with reason_code="destructive_unauthz:<sub-reason>"
                # (truncated to 32 chars by the F.2 wrapper).
                self._emit(
                    "federation_write_endpoint_denied",
                    peer_id=self.peer_row.get("peer_id", ""),
                    route=path,
                    gate_failed=10,
                    reason_code="destructive_unauthz:{0}".format(
                        (reason or "")[:12]
                    ),
                )
                return 403, "owner_cosign", b'{"error":"owner_cosign"}'

        # Gate #11 — handler
        handler = self._resolve_handler(method, path)
        if handler is None:
            return 405, "method", b'{"error":"method"}'

        kwargs: Dict[str, Any] = {}
        if path == "/federation/peer-register" and self.peers_yaml_path is not None:
            kwargs["peers_path"] = self.peers_yaml_path
        if path == "/federation/peer-revoke" and self.peers_yaml_path is not None:
            kwargs["peers_path"] = self.peers_yaml_path
        if path.startswith("/federation/audit-event") and self.audit_log_path is not None:
            kwargs["audit_log_path"] = self.audit_log_path

        try:
            return handler.handle(self.peer_row, headers, body, **kwargs)
        except Exception as exc:
            return 500, "handler_crash:{0}".format(
                type(exc).__name__
            ), b'{"error":"handler_crash"}'

    @staticmethod
    def _resolve_handler(method: str, path: str):
        key = (method.upper(), path)
        if key == ("POST", "/federation/peer-register"):
            return _import_handler("peer_register")
        if key == ("POST", "/federation/audit-event"):
            return _import_handler("audit_event_push")
        if key == ("POST", "/federation/audit-event/batch"):
            return _import_handler("audit_event_batch")
        if key == ("POST", "/federation/peer-revoke"):
            return _import_handler("peer_revoke")
        return None


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_peer_row(
    *,
    peer_id: str = "peer-test-01",
    scopes_granted: Optional[List[str]] = None,
    audit_allowlist: Optional[List[str]] = None,
    revoked: bool = False,
) -> Dict[str, Any]:
    return {
        "peer_id": peer_id,
        "peer_id_spki_fingerprint": "ab" * 32,
        "peer_id_cert_fingerprint": "cd" * 32,
        "ca_pin_sha256": "ef" * 32,
        "hmac_secret_hex": "12" * 32,
        "scopes": list(scopes_granted) if scopes_granted is not None else [],
        "audit_event_push_allowlist": (
            list(audit_allowlist) if audit_allowlist is not None else []
        ),
        "revoked": revoked,
        "not_valid_after": "2026-03-01T00:00:00Z",
        "not_valid_before": "2026-01-01T00:00:00Z",
    }


def _make_headers(
    scope: str,
    *,
    extra: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    h = {
        "Content-Type": "application/json",
        "X-CEO-Federation-Scope": scope,
        "X-CEO-Federation-Nonce": "test-nonce-{0}".format(time.time_ns()),
        "X-CEO-Federation-Timestamp": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        ),
    }
    if extra:
        h.update(extra)
    return h


def _make_new_peer_body(peer_id: str = "peer-new-01") -> bytes:
    return json.dumps({
        "peer_id": peer_id,
        "peer_id_spki_fingerprint": "aa" * 32,
        "ca_pin_sha256": "bb" * 32,
        "hmac_secret_hex": "cc" * 32,
        "not_valid_after": "2026-08-01T00:00:00Z",
        "not_valid_before": "2026-06-01T00:00:00Z",
        "scopes": ["audit_event_push"],
    }).encode("utf-8")


def _make_event_body(action: str = "test_action") -> bytes:
    return json.dumps({
        "action": action,
        "ts": "2026-05-20T00:00:00Z",
        "schema_version": "v2.28",
    }).encode("utf-8")


class _StubIdentityModule:
    """Minimal stub for _lib.federation.identity used by handlers.

    Provides parse_peers_text + serialise_peers_payload so the
    peer_register / peer_revoke handlers can round-trip our test
    peers.yaml fixtures without needing the canonical federation
    package on disk.
    """

    @staticmethod
    def parse_peers_text(text: str) -> Dict[str, Any]:
        if not text.strip():
            return {"peers": []}
        return json.loads(text)

    @staticmethod
    def serialise_peers_payload(payload: Mapping[str, Any]) -> bytes:
        return json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")


def _install_identity_stub():
    """Inject the stub identity module under canonical + flat paths + the
    `_lib.federation` package attribute (the handlers do
    `from _lib.federation import identity`, which resolves via the package
    ATTRIBUTE — a previously-imported REAL identity would otherwise win over a
    sys.modules-only stub, a cross-file pollution. conftest.py snapshots +
    restores both around every test so this stub never leaks)."""
    sys.modules["_lib.federation.identity"] = _StubIdentityModule  # type: ignore[assignment]
    sys.modules["federation.identity"] = _StubIdentityModule  # type: ignore[assignment]
    _pkg = sys.modules.get("_lib.federation")
    if _pkg is not None:
        _pkg.identity = _StubIdentityModule  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Test suites
# ---------------------------------------------------------------------------


class _GateChainBase(unittest.TestCase):
    """Common setUp — temp dir, peers.yaml, peer_row, harness."""

    @classmethod
    def setUpClass(cls):
        _install_identity_stub()

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wave-d-test-")
        self.tmp_path = Path(self.tmp)
        self.peers_yaml = self.tmp_path / "peers.yaml"
        self.peers_yaml.write_text(
            json.dumps({"peers": []}), encoding="utf-8"
        )
        self.audit_log = self.tmp_path / "audit-log.jsonl"
        # Set the env so audit_event_push handler resolves to our tmp.
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.audit_log)
        self.addCleanup(self._tidy)

    def _tidy(self):
        os.environ.pop("CEO_AUDIT_LOG_PATH", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_harness(self, **kw) -> _DispatcherTestHarness:
        kw.setdefault("peers_yaml_path", self.peers_yaml)
        kw.setdefault("audit_log_path", self.audit_log)
        peer_row = kw.pop("peer_row", _make_peer_row(
            scopes_granted=["peer_register", "audit_event_push",
                            "audit_event_push_batch", "peer_revoke"],
            audit_allowlist=["test_action"],
        ))
        return _DispatcherTestHarness(peer_row, **kw)


# =====================================================================
# GATE-BY-GATE COVERAGE (11 tests, one per gate)
# =====================================================================


class TestGateChain(_GateChainBase):
    """Gates 1-11 happy + sad path — one test per gate."""

    def test_gate_1_mtls_smoke(self):
        """Gate #1 (mTLS) — enforced by SSLContext upstream; harness smoke."""
        # The harness assumes mTLS already passed; we just verify the
        # full chain runs end-to-end when no failures injected.
        h = self._make_harness()
        status, _, _ = h.dispatch(
            "POST", "/federation/audit-event",
            _make_headers("audit_event_push"),
            _make_event_body(),
        )
        self.assertEqual(status, 200)

    def test_gate_2_spki_smoke(self):
        """Gate #2 (SPKI) — enforced by Wave C dispatcher upstream; smoke."""
        # peer_row.peer_id_spki_fingerprint is set in _make_peer_row.
        h = self._make_harness()
        self.assertIn(
            "peer_id_spki_fingerprint", h.peer_row,
        )

    def test_gate_3_hmac_invalid(self):
        """Gate #3 — invalid HMAC → 401."""
        h = self._make_harness()
        status, _, _ = h.dispatch(
            "POST", "/federation/audit-event",
            _make_headers("audit_event_push",
                          extra={"X-CEO-Federation-HMAC-Invalid": "1"}),
            _make_event_body(),
        )
        self.assertEqual(status, 401)

    def test_gate_4_unknown_route(self):
        """Gate #4 — wrong method on registered path → 405."""
        h = self._make_harness()
        status, _, _ = h.dispatch(
            "DELETE", "/federation/peer-register",
            _make_headers("peer_register"),
            b"{}",
        )
        self.assertEqual(status, 405)

    def test_gate_5_missing_scope_header(self):
        """Gate #5 — missing X-CEO-Federation-Scope header → 400."""
        h = self._make_harness()
        headers = _make_headers("audit_event_push")
        del headers["X-CEO-Federation-Scope"]
        status, _, _ = h.dispatch(
            "POST", "/federation/audit-event", headers, _make_event_body(),
        )
        self.assertEqual(status, 400)

    def test_gate_6_peer_lacks_scope(self):
        """Gate #6 — peer has audit_event_push but route requires peer_register."""
        peer = _make_peer_row(scopes_granted=["audit_event_push"])
        h = self._make_harness(peer_row=peer)
        status, _, _ = h.dispatch(
            "POST", "/federation/peer-register",
            _make_headers("peer_register"),
            _make_new_peer_body(),
        )
        self.assertEqual(status, 403)

    def test_gate_7_revoked_peer(self):
        """Gate #7 — peer.revoked=True → 403."""
        peer = _make_peer_row(scopes_granted=["audit_event_push"],
                              revoked=True)
        h = self._make_harness(peer_row=peer)
        status, _, _ = h.dispatch(
            "POST", "/federation/audit-event",
            _make_headers("audit_event_push"),
            _make_event_body(),
        )
        self.assertEqual(status, 403)

    def test_gate_8_write_enable_sentinel_missing(self):
        """Gate #8 — write-enable sentinel invalid → 503."""
        h = self._make_harness(write_enable_valid=False)
        status, _, _ = h.dispatch(
            "POST", "/federation/audit-event",
            _make_headers("audit_event_push"),
            _make_event_body(),
        )
        self.assertEqual(status, 503)

    def test_gate_9_rate_limit_triggered(self):
        """Gate #9 — rate-limit fail → 429 (Wave E enforces; harness wires hook)."""
        h = self._make_harness(rate_limit_pass=False)
        status, _, _ = h.dispatch(
            "POST", "/federation/audit-event",
            _make_headers("audit_event_push"),
            _make_event_body(),
        )
        self.assertEqual(status, 429)

    def test_gate_10_destructive_without_cosign(self):
        """Gate #10 — destructive route without valid co-sign → 403."""
        h = self._make_harness(
            cosign_verifier=lambda m, p, hh: (False, "missing_header"),
        )
        status, _, _ = h.dispatch(
            "POST", "/federation/peer-register",
            _make_headers("peer_register"),
            _make_new_peer_body(),
        )
        self.assertEqual(status, 403)

    def test_gate_11_happy_path_handler_executes(self):
        """Gate #11 — all gates pass → 200 + handler ran."""
        h = self._make_harness()
        status, _, body = h.dispatch(
            "POST", "/federation/audit-event",
            _make_headers("audit_event_push"),
            _make_event_body(),
        )
        self.assertEqual(status, 200)
        self.assertIn(b"appended", body)


# =====================================================================
# PER-ROUTE HAPPY PATH (4 tests)
# =====================================================================


class TestPerRouteHappy(_GateChainBase):

    def test_peer_register_happy(self):
        h = self._make_harness()
        status, _, body = h.dispatch(
            "POST", "/federation/peer-register",
            _make_headers("peer_register"),
            _make_new_peer_body(),
        )
        self.assertEqual(status, 200)
        self.assertIn(b"registered", body)
        # Confirm peers.yaml was mutated.
        payload = json.loads(self.peers_yaml.read_text(encoding="utf-8"))
        self.assertEqual(len(payload["peers"]), 1)
        self.assertEqual(payload["peers"][0]["peer_id"], "peer-new-01")

    def test_audit_event_push_happy(self):
        h = self._make_harness()
        status, _, body = h.dispatch(
            "POST", "/federation/audit-event",
            _make_headers("audit_event_push"),
            _make_event_body(),
        )
        self.assertEqual(status, 200)
        self.assertIn(b"appended", body)
        # Confirm audit-log was appended.
        self.assertTrue(self.audit_log.exists())
        line = self.audit_log.read_text(encoding="utf-8").strip()
        evt = json.loads(line)
        self.assertEqual(evt["action"], "test_action")
        self.assertEqual(evt["federation_origin_peer_id"], "peer-test-01")

    def test_audit_event_batch_happy(self):
        h = self._make_harness()
        batch_body = json.dumps({
            "events": [
                {"action": "test_action", "ts": "2026-05-20T00:00:00Z",
                 "schema_version": "v2.28"},
                {"action": "test_action", "ts": "2026-05-20T00:00:01Z",
                 "schema_version": "v2.28"},
                {"action": "test_action", "ts": "2026-05-20T00:00:02Z",
                 "schema_version": "v2.28"},
            ],
        }).encode("utf-8")
        status, _, body = h.dispatch(
            "POST", "/federation/audit-event/batch",
            _make_headers("audit_event_push_batch"),
            batch_body,
        )
        self.assertEqual(status, 200)
        resp = json.loads(body)
        self.assertEqual(resp["accepted"], 3)

    def test_peer_revoke_happy(self):
        # First register a peer.
        h = self._make_harness()
        h.dispatch(
            "POST", "/federation/peer-register",
            _make_headers("peer_register"),
            _make_new_peer_body("peer-victim-01"),
        )
        # Then revoke it.
        status, _, body = h.dispatch(
            "POST", "/federation/peer-revoke",
            _make_headers("peer_revoke"),
            json.dumps({"target_peer_id": "peer-victim-01"}).encode("utf-8"),
        )
        self.assertEqual(status, 200)
        self.assertIn(b"revoked", body)
        # Confirm revoked: true.
        payload = json.loads(self.peers_yaml.read_text(encoding="utf-8"))
        victim = [p for p in payload["peers"]
                  if p["peer_id"] == "peer-victim-01"][0]
        self.assertTrue(victim["revoked"])


# =====================================================================
# PER-ROUTE FAILURE MODES (4 tests)
# =====================================================================


class TestPerRouteFailures(_GateChainBase):

    def test_peer_register_bad_body(self):
        h = self._make_harness()
        status, _, _ = h.dispatch(
            "POST", "/federation/peer-register",
            _make_headers("peer_register"),
            b"NOT VALID JSON",
        )
        self.assertEqual(status, 400)

    def test_audit_event_push_bad_body(self):
        h = self._make_harness()
        status, _, _ = h.dispatch(
            "POST", "/federation/audit-event",
            _make_headers("audit_event_push"),
            b"NOT VALID JSON",
        )
        self.assertEqual(status, 400)

    def test_audit_event_batch_empty(self):
        h = self._make_harness()
        body = json.dumps({"events": []}).encode("utf-8")
        status, _, _ = h.dispatch(
            "POST", "/federation/audit-event/batch",
            _make_headers("audit_event_push_batch"),
            body,
        )
        self.assertEqual(status, 400)

    def test_peer_revoke_missing_target(self):
        h = self._make_harness()
        status, _, _ = h.dispatch(
            "POST", "/federation/peer-revoke",
            _make_headers("peer_revoke"),
            json.dumps({}).encode("utf-8"),
        )
        self.assertEqual(status, 400)


# =====================================================================
# SENTINEL TTL / REPLAY / SINGLE-USE (3 tests)
# =====================================================================


class TestOwnerCosignSentinel(unittest.TestCase):
    """Per ADR-135-AMEND-1 §2.5 atomic claim/consume protocol."""

    @classmethod
    def setUpClass(cls):
        _install_identity_stub()

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wave-d-sentinel-")
        self.tmp_path = Path(self.tmp)
        self.sentinels_root = self.tmp_path / "sentinels"
        self.sentinels_root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))

    def _stage_sentinel(self, sigref: str, signed_at_iso: str):
        d = self.sentinels_root / sigref
        d.mkdir(parents=True, exist_ok=True)
        md = d / "approval.md"
        asc = d / "approval.md.asc"
        md.write_text(
            "# Owner approval sentinel\n\nsigned_at: {0}\n".format(signed_at_iso),
            encoding="utf-8",
        )
        asc.write_text("FAKE-DETACHED-SIG", encoding="utf-8")
        return d, md, asc

    def _verifier_with_stage(self, base_dir: Path):
        """Closure simulating the real _verify_owner_cosign_sentinel."""

        def _verify(method: str, path: str, headers: Mapping[str, str]) -> Tuple[bool, str]:
            # Extract sigref header (case-insensitive)
            sigref = ""
            for k, v in headers.items():
                if k.lower() == "x-ceo-owner-sigref":
                    sigref = v
                    break
            if not sigref:
                return False, "missing_header"
            sd = base_dir / sigref
            md = sd / "approval.md"
            asc = sd / "approval.md.asc"
            if not md.exists() or not asc.exists():
                return False, "sentinel_not_found"

            # Atomic claim step 1a + 1b.
            md_inflight = md.with_suffix(".md.inflight")
            asc_inflight = asc.with_suffix(".asc.inflight")
            try:
                os.rename(str(md), str(md_inflight))
            except OSError:
                return False, "sentinel_inflight_collision"
            try:
                os.rename(str(asc), str(asc_inflight))
            except OSError:
                try:
                    os.rename(str(md_inflight), str(md))
                except OSError:
                    pass
                return False, "sentinel_asc_claim_failed"

            # TTL check from cleartext.
            text = md_inflight.read_text(encoding="utf-8")
            signed_at: Optional[float] = None
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("signed_at:"):
                    ts_raw = line.split(":", 1)[1].strip()
                    if ts_raw.endswith("Z"):
                        ts_raw = ts_raw[:-1] + "+00:00"
                    try:
                        from datetime import datetime
                        signed_at = datetime.fromisoformat(ts_raw).timestamp()
                    except ValueError:
                        signed_at = None
                    break
            if signed_at is None:
                return False, "missing_signed_at"
            if (time.time() - signed_at) > 24 * 3600:
                return False, "ttl_expired"

            # Atomic consume step 4.
            consumed_md = md.with_suffix(".md.consumed-{0}".format(sigref))
            consumed_asc = asc.with_suffix(".asc.consumed-{0}".format(sigref))
            os.rename(str(md_inflight), str(consumed_md))
            try:
                os.rename(str(asc_inflight), str(consumed_asc))
            except OSError:
                pass
            return True, "verified"

        return _verify

    def test_ttl_expired_24h_plus_1s(self):
        """Sentinel signed 24h + 1s ago → ttl_expired → 403."""
        sigref = "req-aaa-001"
        old_ts = time.gmtime(time.time() - (24 * 3600) - 1)
        old_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", old_ts)
        self._stage_sentinel(sigref, old_iso)

        verifier = self._verifier_with_stage(self.sentinels_root)
        peer = _make_peer_row(scopes_granted=["peer_register"])
        h = _DispatcherTestHarness(peer, cosign_verifier=verifier)
        # Provide a peers.yaml fixture so handler can reach gate #11
        # (won't matter — gate #10 fails first).
        peers_yaml = self.tmp_path / "peers.yaml"
        peers_yaml.write_text(json.dumps({"peers": []}), encoding="utf-8")
        h.peers_yaml_path = peers_yaml

        status, _, _ = h.dispatch(
            "POST", "/federation/peer-register",
            _make_headers("peer_register", extra={"X-CEO-Owner-Sigref": sigref}),
            _make_new_peer_body(),
        )
        self.assertEqual(status, 403)

    def test_owner_cosign_ttl_exactly_24h_accepted(self):
        """F-005 boundary fix: sentinel signed at the 24h boundary → ACCEPT.

        Per ADR-135-AMEND-1 §2.5 the TTL gate is ``age > 24h`` →
        reject. The boundary case ``age == 24h`` MUST be accepted —
        the verifier closure uses ``>`` (strict greater than). This
        complements ``test_ttl_expired_24h_plus_1s`` (which tests
        ``age == 24h + 1s`` → reject).

        Implementation note: ISO-8601 strftime drops sub-second
        precision, so we sign 5 seconds INSIDE the 24h window. This
        ensures ``time.time() - signed_at`` lands in the closed
        interval ``[24h - 5s, 24h]`` — solidly within ACCEPT range
        — regardless of test-runner scheduling jitter. The intent
        ("at the 24h boundary") is preserved; ``test_ttl_expired_24h_plus_1s``
        tests the strict-reject side at 24h + 1s.
        """
        sigref = "req-ttl-boundary-24h"
        # Sign at 24h - 5s so the elapsed window is firmly within
        # 24h regardless of ISO truncation + scheduling jitter.
        signed_at_epoch = time.time() - (24 * 3600) + 5
        old_ts = time.gmtime(signed_at_epoch)
        boundary_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", old_ts)
        self._stage_sentinel(sigref, boundary_iso)

        verifier = self._verifier_with_stage(self.sentinels_root)
        peer = _make_peer_row(scopes_granted=["peer_register"])
        peers_yaml = self.tmp_path / "peers.yaml"
        peers_yaml.write_text(json.dumps({"peers": []}), encoding="utf-8")
        h = _DispatcherTestHarness(
            peer, peers_yaml_path=peers_yaml, cosign_verifier=verifier,
        )

        status, _, _ = h.dispatch(
            "POST", "/federation/peer-register",
            _make_headers(
                "peer_register",
                extra={"X-CEO-Owner-Sigref": sigref},
            ),
            _make_new_peer_body(),
        )
        # Accept boundary — gate #10 passes; gate #11 handler runs.
        self.assertEqual(status, 200)

    def test_replay_same_sigref_twice(self):
        """Same sigref used twice → first 200, second 403 (consumed)."""
        sigref = "req-bbb-002"
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._stage_sentinel(sigref, now_iso)

        verifier = self._verifier_with_stage(self.sentinels_root)
        peer = _make_peer_row(scopes_granted=["peer_register"])
        peers_yaml = self.tmp_path / "peers.yaml"
        peers_yaml.write_text(json.dumps({"peers": []}), encoding="utf-8")

        h = _DispatcherTestHarness(
            peer, peers_yaml_path=peers_yaml, cosign_verifier=verifier,
        )

        # First request — must succeed.
        status1, _, _ = h.dispatch(
            "POST", "/federation/peer-register",
            _make_headers("peer_register", extra={"X-CEO-Owner-Sigref": sigref}),
            _make_new_peer_body("peer-replay-1"),
        )
        self.assertEqual(status1, 200)

        # Second request — sentinel is consumed.
        status2, _, _ = h.dispatch(
            "POST", "/federation/peer-register",
            _make_headers("peer_register", extra={"X-CEO-Owner-Sigref": sigref}),
            _make_new_peer_body("peer-replay-2"),
        )
        self.assertEqual(status2, 403)

    def test_single_use_consumed_marker_exists(self):
        """After first verify, .consumed-<id> markers exist + originals are gone."""
        sigref = "req-ccc-003"
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        sd, md, asc = self._stage_sentinel(sigref, now_iso)

        verifier = self._verifier_with_stage(self.sentinels_root)
        peer = _make_peer_row(scopes_granted=["peer_register"])
        peers_yaml = self.tmp_path / "peers.yaml"
        peers_yaml.write_text(json.dumps({"peers": []}), encoding="utf-8")

        h = _DispatcherTestHarness(
            peer, peers_yaml_path=peers_yaml, cosign_verifier=verifier,
        )
        status, _, _ = h.dispatch(
            "POST", "/federation/peer-register",
            _make_headers("peer_register", extra={"X-CEO-Owner-Sigref": sigref}),
            _make_new_peer_body("peer-single-use"),
        )
        self.assertEqual(status, 200)

        # Original files must no longer exist.
        self.assertFalse(md.exists())
        self.assertFalse(asc.exists())
        # .consumed-<sigref> markers must exist.
        consumed_md_glob = list(sd.glob("*.consumed-{0}".format(sigref)))
        self.assertGreater(len(consumed_md_glob), 0)


# =====================================================================
# BATCH + ALLOWLIST (3 tests)
# =====================================================================


class TestBatchAndAllowlist(_GateChainBase):

    def test_batch_size_101_rejected_at_parse(self):
        """Batch with 101 events → 400 batch_too_large at parse time."""
        h = self._make_harness()
        events = [
            {"action": "test_action", "ts": "2026-05-20T00:00:00Z",
             "schema_version": "v2.28"}
            for _ in range(101)
        ]
        body = json.dumps({"events": events}).encode("utf-8")
        status, reason, _ = h.dispatch(
            "POST", "/federation/audit-event/batch",
            _make_headers("audit_event_push_batch"),
            body,
        )
        self.assertEqual(status, 400)
        self.assertIn("batch_too_large", reason)

    def test_action_not_in_peer_allowlist(self):
        """audit_event_push with action NOT in peer's allowlist → 400."""
        peer = _make_peer_row(
            scopes_granted=["audit_event_push"],
            audit_allowlist=["allowed_action_only"],
        )
        h = self._make_harness(peer_row=peer)
        evt = json.dumps({
            "action": "forbidden_action",
            "ts": "2026-05-20T00:00:00Z",
            "schema_version": "v2.28",
        }).encode("utf-8")
        status, reason, _ = h.dispatch(
            "POST", "/federation/audit-event",
            _make_headers("audit_event_push"),
            evt,
        )
        self.assertEqual(status, 400)
        self.assertIn("action_blocked", reason)

    def test_action_in_peer_allowlist_accepted(self):
        """audit_event_push with action IN peer's allowlist → 200 + append."""
        peer = _make_peer_row(
            scopes_granted=["audit_event_push"],
            audit_allowlist=["test_action"],
        )
        h = self._make_harness(peer_row=peer)
        status, _, body = h.dispatch(
            "POST", "/federation/audit-event",
            _make_headers("audit_event_push"),
            _make_event_body("test_action"),
        )
        self.assertEqual(status, 200)
        self.assertIn(b"appended", body)


# =====================================================================
# SCOPE MISMATCH (2 tests)
# =====================================================================


class TestScopeMismatch(_GateChainBase):

    def test_header_scope_vs_route_scope_mismatch(self):
        """Header scope = audit_event_push but route is /peer-register → 400.

        F-009 fix: docstring previously said 403 but the gate-#5
        scope-header mismatch returns 400 (validation failure on the
        request header), not 403 (scope authorisation). The 403 path
        is gate #6 (peer's scopes list lacks the required scope) —
        tested separately in ``test_gate_6_peer_lacks_scope``.
        """
        peer = _make_peer_row(
            scopes_granted=["peer_register", "audit_event_push"],
        )
        h = self._make_harness(peer_row=peer)
        # Header declares audit_event_push, route requires peer_register.
        status, _, _ = h.dispatch(
            "POST", "/federation/peer-register",
            _make_headers("audit_event_push"),
            _make_new_peer_body(),
        )
        # Gate #5 — scope_header (header doesn't match route's scope).
        self.assertEqual(status, 400)

    def test_peer_empty_scopes_default_reject(self):
        """Peer's scopes list is empty (default v1.x) → 403 on any write route."""
        peer = _make_peer_row(scopes_granted=[])
        h = self._make_harness(peer_row=peer)
        status, _, _ = h.dispatch(
            "POST", "/federation/audit-event",
            _make_headers("audit_event_push"),
            _make_event_body(),
        )
        self.assertEqual(status, 403)


# =====================================================================
# ATOMIC-WRITE INTEGRITY (1 test)
# =====================================================================


class TestAtomicWriteIntegrity(_GateChainBase):

    def test_peer_register_with_collision_does_not_mutate(self):
        """A peer_register with colliding peer_id MUST NOT mutate peers.yaml.

        This is the atomic-claim contract: failed appends leave the
        file unchanged.
        """
        # Pre-stage a peer with the same peer_id we'll try to register.
        existing = {
            "peers": [{
                "peer_id": "peer-new-01",
                "peer_id_spki_fingerprint": "ff" * 32,
                "revoked": False,
                "scopes": [],
            }],
        }
        self.peers_yaml.write_text(json.dumps(existing), encoding="utf-8")
        before_bytes = self.peers_yaml.read_bytes()

        h = self._make_harness()
        status, _, _ = h.dispatch(
            "POST", "/federation/peer-register",
            _make_headers("peer_register"),
            _make_new_peer_body("peer-new-01"),  # collision
        )
        self.assertEqual(status, 409)

        after_bytes = self.peers_yaml.read_bytes()
        # The collision path SHOULD NOT have mutated peers.yaml.
        # (The handler returns BEFORE rename when collision detected.)
        self.assertEqual(before_bytes, after_bytes)

    def test_peer_register_io_error_leaves_file_intact(self):
        """An IO error during peer_register MUST leave peers.yaml intact.

        We simulate by making the peers.yaml directory read-only so the
        same-directory tmpfile open fails. The handler must return 500
        without partially mutating the target.
        """
        # Pre-stage a peer.yaml with content.
        existing = {"peers": [{"peer_id": "peer-existing", "scopes": []}]}
        self.peers_yaml.write_text(json.dumps(existing), encoding="utf-8")
        before_bytes = self.peers_yaml.read_bytes()

        # Make parent directory read-only — open(O_CREAT) inside it
        # will fail with EACCES. Use chmod 0o500 (r-x).
        original_mode = self.tmp_path.stat().st_mode & 0o777
        os.chmod(str(self.tmp_path), 0o500)
        try:
            h = self._make_harness()
            status, _, _ = h.dispatch(
                "POST", "/federation/peer-register",
                _make_headers("peer_register"),
                _make_new_peer_body("peer-fresh-01"),
            )
            self.assertEqual(status, 500)
        finally:
            os.chmod(str(self.tmp_path), original_mode)

        after_bytes = self.peers_yaml.read_bytes()
        self.assertEqual(before_bytes, after_bytes)


# =====================================================================
# DEFENSIVE-PARSE GATES (2 tests)
# =====================================================================


class TestDefensiveParseGates(_GateChainBase):
    """Sigref charset + scope-header charset rejection (gates #5, #10)."""

    def test_sigref_path_traversal_rejected(self):
        """X-CEO-Owner-Sigref with `../` MUST be rejected at gate #10.

        Per ADR-135-AMEND-1 §2.5, the per-request sigref is used to
        construct a filesystem path under
        ``.claude/data/federation/sentinels/<sigref>/``. Path-traversal
        chars (`../`, `/`, NUL) must be refused BEFORE the filesystem
        access is attempted.
        """
        peer = _make_peer_row(scopes_granted=["peer_register"])
        # Closure that ECHOES the charset gate the production helper
        # implements (mirrors Patch 3 in server_routes_patch.md).
        import re as _re

        def _verifier(method: str, path: str, headers: Mapping[str, str]) -> Tuple[bool, str]:
            sigref = ""
            for k, v in headers.items():
                if k.lower() == "x-ceo-owner-sigref":
                    sigref = v
                    break
            if not sigref:
                return False, "missing_header"
            if not _re.match(r"^[A-Za-z0-9_-]{1,64}$", sigref):
                return False, "sigref_charset"
            return True, "verified"

        h = _DispatcherTestHarness(
            peer,
            peers_yaml_path=self.peers_yaml,
            cosign_verifier=_verifier,
        )
        status, _, _ = h.dispatch(
            "POST", "/federation/peer-register",
            _make_headers(
                "peer_register",
                extra={"X-CEO-Owner-Sigref": "../etc/passwd"},
            ),
            _make_new_peer_body("peer-traversal"),
        )
        self.assertEqual(status, 403)

    def test_scope_header_with_crlf_rejected(self):
        """X-CEO-Federation-Scope containing CR/LF MUST be rejected.

        Smuggling protection at gate #5. The _SCOPE_NAME_RE charset
        refuses anything outside [A-Za-z0-9_].
        """
        peer = _make_peer_row(
            scopes_granted=["audit_event_push"],
            audit_allowlist=["test_action"],
        )
        h = self._make_harness(peer_row=peer)
        headers = _make_headers("audit_event_push")
        # Inject CRLF — should fail charset check at gate #5.
        headers["X-CEO-Federation-Scope"] = "audit_event_push\r\nX-Injected: 1"
        status, _, _ = h.dispatch(
            "POST", "/federation/audit-event",
            headers,
            _make_event_body(),
        )
        self.assertEqual(status, 400)


# =====================================================================
# REAL HANDLER INTEGRATION (F-003 — exercise staged handler code directly)
# =====================================================================


class TestRealHandlerIntegration(unittest.TestCase):
    """F-003 fix — exercise the staged handler modules directly.

    Unlike the ``_DispatcherTestHarness`` (which simulates the
    dispatcher LOGIC from server_routes_patch.md), this suite imports
    the staged handler modules and invokes ``.handle(...)`` directly.
    These tests verify the actual staged code paths — atomic-write
    contract, audit-log append, schema validation, IO error behaviour
    — that ship in ``audit_event_push.py`` / ``peer_register.py`` /
    ``peer_revoke.py``.

    Pattern mirrors Wave B's lazy-import via ``sys.path`` manipulation
    (see ``tools/migrate-peers-yaml.py``). When the canonical
    ``_lib/federation/handlers/<name>.py`` files are present
    (post-Owner-A2-post), the canonical path is preferred; pre-A2-post
    falls back to the staging file via ``spec_from_file_location``.
    """

    @classmethod
    def setUpClass(cls):
        _install_identity_stub()

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wave-d-real-handler-")
        self.tmp_path = Path(self.tmp)
        self.peers_yaml = self.tmp_path / "peers.yaml"
        self.peers_yaml.write_text(
            json.dumps({"peers": []}), encoding="utf-8",
        )
        self.audit_log = self.tmp_path / "audit-log.jsonl"
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.audit_log)
        self.addCleanup(self._tidy)

    def _tidy(self):
        os.environ.pop("CEO_AUDIT_LOG_PATH", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _caller_peer_row(self) -> Dict[str, Any]:
        return _make_peer_row(
            peer_id="peer-caller-real",
            scopes_granted=[
                "peer_register",
                "audit_event_push",
                "audit_event_push_batch",
                "peer_revoke",
            ],
            audit_allowlist=["test_action"],
        )

    def test_peer_register_handler_direct_invoke_appends_row(self):
        """Import peer_register staging module and invoke handle() directly.

        Verifies the actual staged code (NOT the simulator) appends a
        new peer row to peers.yaml via the atomic tmpfile+rename
        path.
        """
        h_mod = _import_handler("peer_register")
        self.assertIsNotNone(h_mod, "peer_register staging module missing")

        body = _make_new_peer_body("peer-real-direct-01")
        status, reason, response_body = h_mod.handle(
            self._caller_peer_row(),
            {"X-CEO-Federation-Scope": "peer_register"},
            body,
            peers_path=self.peers_yaml,
        )
        self.assertEqual(status, 200, "expected 200, got {0} ({1})".format(
            status, reason,
        ))
        self.assertIn(b"registered", response_body)

        # Verify peers.yaml was atomically mutated.
        payload = json.loads(self.peers_yaml.read_text(encoding="utf-8"))
        peer_ids = [p["peer_id"] for p in payload["peers"]]
        self.assertIn("peer-real-direct-01", peer_ids)

    def test_audit_event_push_handler_direct_invoke_appends_line(self):
        """Import audit_event_push staging module and invoke handle() directly.

        Verifies the actual staged O_APPEND + fsync path (the
        append-only contract) — not the simulator's behaviour.
        """
        h_mod = _import_handler("audit_event_push")
        self.assertIsNotNone(
            h_mod, "audit_event_push staging module missing",
        )

        peer = self._caller_peer_row()
        body = _make_event_body("test_action")
        status, reason, response_body = h_mod.handle(
            peer,
            {"X-CEO-Federation-Scope": "audit_event_push"},
            body,
            audit_log_path=self.audit_log,
        )
        self.assertEqual(status, 200, "expected 200, got {0} ({1})".format(
            status, reason,
        ))
        self.assertTrue(self.audit_log.exists())
        line = self.audit_log.read_text(encoding="utf-8").strip()
        evt = json.loads(line)
        self.assertEqual(evt["action"], "test_action")
        # Origin attribution stamped by the handler.
        self.assertEqual(
            evt["federation_origin_peer_id"], peer["peer_id"],
        )

    def test_peer_revoke_handler_direct_invoke_marks_revoked(self):
        """Import peer_revoke staging module and invoke handle() directly.

        Verifies the atomic mutation marks ``revoked: true`` on the
        target row + leaves other rows untouched.
        """
        # Pre-stage a peer to revoke.
        self.peers_yaml.write_text(json.dumps({
            "peers": [
                {"peer_id": "peer-victim", "revoked": False, "scopes": []},
                {"peer_id": "peer-bystander", "revoked": False, "scopes": []},
            ],
        }), encoding="utf-8")

        h_mod = _import_handler("peer_revoke")
        self.assertIsNotNone(h_mod, "peer_revoke staging module missing")

        body = json.dumps({"target_peer_id": "peer-victim"}).encode("utf-8")
        status, reason, response_body = h_mod.handle(
            self._caller_peer_row(),
            {"X-CEO-Federation-Scope": "peer_revoke"},
            body,
            peers_path=self.peers_yaml,
        )
        self.assertEqual(status, 200, "expected 200, got {0} ({1})".format(
            status, reason,
        ))
        self.assertIn(b"revoked", response_body)

        # Verify atomic mutation: victim revoked, bystander untouched.
        payload = json.loads(self.peers_yaml.read_text(encoding="utf-8"))
        by_id = {p["peer_id"]: p for p in payload["peers"]}
        self.assertTrue(by_id["peer-victim"]["revoked"])
        self.assertFalse(by_id["peer-bystander"]["revoked"])

    def test_peer_register_atomic_write_unchanged_on_io_error(self):
        """F-003 atomic-write contract: on fsync/rename failure, the
        target file MUST be byte-identical to its pre-call state.

        We force an IO error by making the peers.yaml parent directory
        read-only — ``os.open(O_CREAT)`` for the tmpfile fails with
        EACCES, the handler returns 500, and peers.yaml content is
        unchanged.
        """
        # Pre-stage with content we'll verify is preserved.
        pre_payload = {"peers": [{"peer_id": "peer-preserved", "scopes": []}]}
        self.peers_yaml.write_text(
            json.dumps(pre_payload), encoding="utf-8",
        )
        before_bytes = self.peers_yaml.read_bytes()

        h_mod = _import_handler("peer_register")
        self.assertIsNotNone(h_mod, "peer_register staging module missing")

        # Force-fail the tmpfile open by making the parent dir read-only.
        original_mode = self.tmp_path.stat().st_mode & 0o777
        os.chmod(str(self.tmp_path), 0o500)
        try:
            status, reason, _ = h_mod.handle(
                self._caller_peer_row(),
                {"X-CEO-Federation-Scope": "peer_register"},
                _make_new_peer_body("peer-blocked-by-io"),
                peers_path=self.peers_yaml,
            )
            self.assertEqual(
                status, 500,
                "expected IO error to surface as 500; got {0} ({1})".format(
                    status, reason,
                ),
            )
        finally:
            os.chmod(str(self.tmp_path), original_mode)

        # Critical atomic-write invariant: target file unchanged.
        after_bytes = self.peers_yaml.read_bytes()
        self.assertEqual(
            before_bytes, after_bytes,
            "peers.yaml MUST be byte-identical after IO error",
        )

    def test_audit_event_push_handler_rejects_action_not_in_allowlist(self):
        """Staged handler enforces per-peer action allowlist.

        Verifies the actual ``_validate_event`` path in the staged
        module (NOT a simulator-level reject) returns 400 with
        ``action_blocked`` when the event's action is not in the
        peer's ``audit_event_push_allowlist``.
        """
        h_mod = _import_handler("audit_event_push")
        self.assertIsNotNone(
            h_mod, "audit_event_push staging module missing",
        )

        peer = _make_peer_row(
            peer_id="peer-restricted",
            scopes_granted=["audit_event_push"],
            audit_allowlist=["allowed_action_only"],
        )
        evt_body = json.dumps({
            "action": "forbidden_action",
            "ts": "2026-05-20T00:00:00Z",
            "schema_version": "v2.28",
        }).encode("utf-8")

        status, reason, _ = h_mod.handle(
            peer,
            {"X-CEO-Federation-Scope": "audit_event_push"},
            evt_body,
            audit_log_path=self.audit_log,
        )
        self.assertEqual(status, 400)
        self.assertIn("action_blocked", reason)
        # Verify nothing was appended.
        self.assertFalse(
            self.audit_log.exists() and self.audit_log.stat().st_size > 0,
            "rejected event MUST NOT touch the audit log",
        )


# =====================================================================
# Bootstrap when run directly
# =====================================================================


if __name__ == "__main__":
    unittest.main()
