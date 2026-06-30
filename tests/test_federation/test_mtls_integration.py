"""PLAN-112-FOLLOWUP-federation-wire (PHASE2) — REMAINING #2 / AC6 + AC17.

Full mTLS HTTPS integration test. Closes the seam gap the staged package
named: "a wiring bug in the SSL/handshake -> do_POST seam would not be
caught" by the dispatcher-level (method-call) tests.

Drives the REAL ``FederationServer.serve_forever`` over a real TLS-1.3
mutual-auth socket with a generated CA + server + client cert chain, ONLY
neutralizing the three orthogonal server-bootstrap preflights
(kill-switch / enable-sentinel / lan-sentinel — exercised elsewhere) so the
actual serve_forever wiring (SSL context, httpd attribute attachment,
reload thread, federation_peers_extra incl. the PHASE2 scopes parse) is the
code under test.

Proves over a real socket:
  - mTLS handshake + client-cert -> SPKI -> peer resolution (gate #1/#2)
  - kill-switch: POST returns 405 when CEO_FEDERATION_WRITE_ENABLED off
  - RBAC: a fully-signed request from an UNSCOPED peer is denied at gate #6
  - happy path: a SCOPED peer's signed audit_event_push reaches gate #11
    and writes the event (200) — i.e. write-mode is adopter-functional
    end-to-end, the F-1.7 closure.

Stdlib + ``openssl`` CLI only. Skipped if openssl absent or TLS 1.3
unavailable on the platform.
"""

from __future__ import annotations

import datetime as dt
import http.client
import json
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

try:
    from _lib.federation import server as _SRV  # type: ignore
    from _lib.federation import identity as _ident  # type: ignore
    from _lib.federation import replay as _replay  # type: ignore
except Exception:  # pragma: no cover
    _SRV = None  # type: ignore
    _ident = None  # type: ignore
    _replay = None  # type: ignore

_OPENSSL = shutil.which("openssl")


def _rfc3339_now(offset_s: float = 0.0) -> str:
    t = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=offset_s)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(*args: str, cwd: Optional[str] = None) -> None:
    subprocess.run(
        list(args), cwd=cwd, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


@unittest.skipIf(_SRV is None, "federation pkg not importable")
@unittest.skipIf(_OPENSSL is None, "openssl not on PATH")
@unittest.skipUnless(getattr(ssl, "HAS_TLSv1_3", False), "TLS 1.3 unavailable")
class TestMtlsWriteModeIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.mkdtemp(prefix="fed-mtls-")
        d = cls._dir
        p = lambda *x: os.path.join(d, *x)  # noqa: E731

        # --- CA ---
        _run(_OPENSSL, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
             "-keyout", p("ca.key"), "-out", p("ca.crt"), "-days", "2",
             "-subj", "/CN=phase2-test-ca")

        def _leaf(name: str, cn: str, san: Optional[str]) -> None:
            _run(_OPENSSL, "genrsa", "-out", p(name + ".key"), "2048")
            _run(_OPENSSL, "req", "-new", "-key", p(name + ".key"),
                 "-out", p(name + ".csr"), "-subj", "/CN=" + cn)
            args = [_OPENSSL, "x509", "-req", "-in", p(name + ".csr"),
                    "-CA", p("ca.crt"), "-CAkey", p("ca.key"),
                    "-CAcreateserial", "-out", p(name + ".crt"), "-days", "2"]
            if san:
                ext = p(name + ".ext")
                Path(ext).write_text("subjectAltName=" + san + "\n",
                                     encoding="utf-8")
                args += ["-extfile", ext]
            _run(*args)

        _leaf("server", "127.0.0.1", "IP:127.0.0.1")
        _leaf("client", "phase2-peer-01", None)

        cls._ca = p("ca.crt")
        cls._server_crt = p("server.crt")
        cls._server_key = p("server.key")
        cls._client_crt = p("client.crt")
        cls._client_key = p("client.key")

        # Compute the client cert SPKI fingerprint with the SAME function
        # the server uses, so the peers.yaml pin matches what the server
        # derives from the presented cert (SPKI is round-trip invariant).
        client_pem = Path(cls._client_crt).read_bytes()
        try:
            cls._client_spki = _ident.compute_spki_fingerprint(client_pem)
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(
                "compute_spki_fingerprint unavailable: {0}".format(exc)
            )
        if not cls._client_spki:
            raise unittest.SkipTest("empty client SPKI fingerprint")

        cls._hmac_secret = "ab" * 32  # 64-hex per-peer secret
        cls._ca_pin = "cd" * 32

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._dir, ignore_errors=True)

    # ---- helpers -------------------------------------------------------

    def _write_peers(self, scopes: str, allowlist: str = "") -> str:
        peers = os.path.join(self._dir, "peers.yaml")
        extra = ""
        if scopes:
            extra += "    scopes: {0}\n".format(scopes)
        if allowlist:
            extra += "    audit_event_push_allowlist: {0}\n".format(allowlist)
        Path(peers).write_text(
            "peers:\n"
            "  - peer_id: phase2-peer-01\n"
            '    peer_id_spki_fingerprint: "{spki}"\n'
            '    ca_pin_sha256: "{capin}"\n'
            '    not_valid_after: "2027-01-01T00:00:00Z"\n'
            '    not_valid_before: "2026-01-01T00:00:00Z"\n'
            "    revoked: false\n"
            '    hmac_secret_hex: "{hmac}"\n'
            "{extra}".format(
                spki=self._client_spki, capin=self._ca_pin,
                hmac=self._hmac_secret, extra=extra,
            ),
            encoding="utf-8",
        )
        return peers

    def _start_server(self, peers_path: str) -> int:
        dummy = Path(self._dir) / "nope.md"
        cfg = _SRV.FederationConfig(
            bind_host="127.0.0.1",
            bind_port=0,
            cert_file=Path(self._server_crt),
            key_file=Path(self._server_key),
            ca_file=Path(self._ca),
            peers_path=Path(peers_path),
            enabled_sentinel=dummy,
            enabled_sentinel_asc=dummy,
            lan_enabled_sentinel=dummy,
            lan_enabled_sentinel_asc=dummy,
            audit_log_path=Path(self._dir) / "audit-log.jsonl",
        )
        srv = _SRV.FederationServer(cfg)
        # Neutralize the 3 orthogonal bootstrap preflights (tested elsewhere);
        # everything else in serve_forever is the code under test.
        srv._check_kill_switch = lambda: None
        srv._check_enable_sentinel = lambda: None
        srv._check_lan_sentinel_if_required = lambda: None
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        self.addCleanup(srv.shutdown)
        # Wait for bind (setup phase, not an assert loop).
        deadline = time.time() + 5.0
        while time.time() < deadline:
            httpd = getattr(srv, "_httpd", None)
            if httpd is not None:
                return int(httpd.server_address[1])
            time.sleep(0.01)
        self.fail("server did not bind within 5s")

    def _client_ctx(self) -> ssl.SSLContext:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # we trust our own test server
        ctx.load_cert_chain(self._client_crt, self._client_key)
        return ctx

    def _request(self, port: int, method: str, path: str,
                 headers: dict, body: bytes = b"") -> Tuple[int, bytes]:
        conn = http.client.HTTPSConnection(
            "127.0.0.1", port, context=self._client_ctx(), timeout=5.0,
        )
        try:
            conn.request(method, path, body=body, headers=headers)
            resp = conn.getresponse()
            return resp.status, resp.read()
        finally:
            conn.close()

    def _signed_headers(self, method: str, path: str, scope: str,
                        body: bytes) -> dict:
        nonce = _replay.generate_nonce()
        ts = _rfc3339_now()
        sig = _replay.sign_request(
            method, path, ts, nonce, body, self._hmac_secret,
        )
        return {
            "X-CEO-Federation-Nonce": nonce,
            "X-CEO-Federation-Timestamp": ts,
            "X-CEO-Federation-Signature": sig,
            "X-CEO-Federation-Scope": scope,
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        }

    # ---- tests ---------------------------------------------------------

    def _stub_gate8_valid(self):
        """Stub Gate #8 / Layer 0b (write-enable sentinel GPG) valid.

        Real behavior is unit-covered; here we test the dispatch seam past
        it (the integration test's job is the TLS->do_POST->gates wiring)."""
        saved = _SRV._FederationHandler._write_enable_sentinel_valid
        _SRV._FederationHandler._write_enable_sentinel_valid = (
            lambda self: True
        )
        self.addCleanup(
            lambda: setattr(
                _SRV._FederationHandler,
                "_write_enable_sentinel_valid", saved,
            )
        )

    def test_a_mtls_handshake_authenticated_get(self):
        """Real mTLS handshake + client-cert->SPKI->peer resolve over TLS."""
        port = self._start_server(self._write_peers(scopes=""))
        # Read endpoints are authenticated — sign the GET so the peer
        # resolves AND the HMAC gate passes over the real socket.
        hdrs = self._signed_headers("GET", "/federation/identity", "", b"")
        hdrs.pop("X-CEO-Federation-Scope", None)  # read path needs no scope
        status, _ = self._request(port, "GET", "/federation/identity", hdrs)
        # NOT a TLS/handshake failure, NOT a 401 unresolved/unauth.
        self.assertNotEqual(status, 401, "peer+auth should pass over mTLS")
        self.assertLess(status, 500)

    def test_b_killswitch_post_405_when_write_disabled(self):
        """do_POST -> 405 over a real socket when Layer 0a env is OFF."""
        os.environ.pop("CEO_FEDERATION_WRITE_ENABLED", None)
        port = self._start_server(self._write_peers(scopes="[audit_event_push]"))
        body = b'{"action":"skill_used","ts":"x","schema_version":"2.0"}'
        status, _ = self._request(
            port, "POST", "/federation/audit-event",
            self._signed_headers(
                "POST", "/federation/audit-event", "audit_event_push", body,
            ), body,
        )
        self.assertEqual(status, 405)

    def test_c1_unscoped_peer_denied_at_gate6_over_tls(self):
        """Fully-signed request from an UNSCOPED peer → gate #6 deny (403).

        Reaching gate #6 proves gates #1 (mTLS) #2 (SPKI resolve) #3 (HMAC)
        #5 (scope header) all ran over the real socket.
        """
        self._save_env()
        os.environ["CEO_FEDERATION_WRITE_ENABLED"] = "1"
        self._stub_gate8_valid()  # Layer 0b — reach gate #5/#6 past gate #8
        port = self._start_server(self._write_peers(scopes=""))  # no scopes
        body = b'{"action":"skill_used","ts":"x","schema_version":"2.0"}'
        status, _ = self._request(
            port, "POST", "/federation/audit-event",
            self._signed_headers(
                "POST", "/federation/audit-event", "audit_event_push", body,
            ), body,
        )
        self.assertEqual(status, 403)

    def test_c2_scoped_peer_happy_path_200_over_tls(self):
        """SCOPED peer's signed audit_event_push reaches gate #11 (200).

        The end-to-end F-1.7 closure: write-mode is adopter-functional over
        a real TLS socket once load_peers parses scopes (PHASE2 #1).
        """
        self._save_env()
        os.environ["CEO_FEDERATION_WRITE_ENABLED"] = "1"
        self._stub_gate8_valid()
        port = self._start_server(
            self._write_peers(
                scopes="[audit_event_push]",
                allowlist="[skill_used]",
            )
        )
        body = json.dumps({
            "action": "skill_used",
            "ts": _rfc3339_now(),
            "schema_version": "2.0",
        }).encode("utf-8")
        status, payload = self._request(
            port, "POST", "/federation/audit-event",
            self._signed_headers(
                "POST", "/federation/audit-event", "audit_event_push", body,
            ), body,
        )
        self.assertEqual(status, 200, payload[:200])

    # ---- env save/restore ----

    def _save_env(self):
        saved = os.environ.get("CEO_FEDERATION_WRITE_ENABLED")
        self.addCleanup(
            lambda: (
                os.environ.__setitem__("CEO_FEDERATION_WRITE_ENABLED", saved)
                if saved is not None
                else os.environ.pop("CEO_FEDERATION_WRITE_ENABLED", None)
            )
        )


if __name__ == "__main__":
    unittest.main()
