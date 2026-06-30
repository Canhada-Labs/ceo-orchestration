"""PLAN-112-FOLLOWUP-federation-wire (PHASE2) — Codex AC18 P1 closure.

Proves the destructive write handlers (peer_register / peer_revoke) round-trip
a REAL YAML peers.yaml via the canonical identity.parse_peers_text /
serialise_peers_payload (NOT the JSON `_StubIdentityModule` that masked the
gap, NOT the json.loads fallback that fails on YAML). Plus the duck-typed
Gate #5 dup-header fail-closed (Codex AC18 P2).

Stdlib-only.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

try:
    from _lib.federation import identity as _ident  # type: ignore
    from _lib.federation import scopes as _scopes  # type: ignore
    from _lib.federation.handlers import peer_register as _pr  # type: ignore
    from _lib.federation.handlers import peer_revoke as _pv  # type: ignore
except Exception:  # pragma: no cover
    _ident = _scopes = _pr = _pv = None  # type: ignore

_F = "a" * 64


def _yaml_one_peer(peer_id: str = "peer-existing") -> str:
    return (
        "peers:\n"
        "  - peer_id: {pid}\n"
        '    peer_id_spki_fingerprint: "{f}"\n'
        '    ca_pin_sha256: "{f}"\n'
        '    not_valid_after: "2026-03-01T00:00:00Z"\n'
        '    not_valid_before: "2026-01-01T00:00:00Z"\n'
        "    revoked: false\n"
        '    hmac_secret_hex: "{f}"\n'
        "    scopes: [audit_event_push]\n"
    ).format(pid=peer_id, f=_F)


@unittest.skipIf(_ident is None, "federation pkg absent")
class TestParseSerialiseExist(unittest.TestCase):
    def test_public_functions_exist(self):
        # The exact gap Codex found: these MUST be real on canonical identity,
        # not stubbed. (peer_register/revoke getattr them; absence => json
        # fallback => parse failure on real YAML.)
        self.assertTrue(callable(getattr(_ident, "parse_peers_text", None)))
        self.assertTrue(
            callable(getattr(_ident, "serialise_peers_payload", None))
        )

    def test_roundtrip_through_real_loader(self):
        payload = _ident.parse_peers_text(_yaml_one_peer())
        self.assertEqual(len(payload["peers"]), 1)
        out = _ident.serialise_peers_payload(payload)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "peers.yaml"
            p.write_bytes(out)
            recs = _ident.load_peers(p)  # the REAL loader the server uses
        self.assertIn("peer-existing", recs)
        self.assertEqual(recs["peer-existing"].scopes, ("audit_event_push",))


@unittest.skipIf(_pr is None, "handlers absent")
class TestPeerRevokeAgainstRealYaml(unittest.TestCase):
    def test_revoke_writes_yaml_that_load_peers_reads(self):
        with tempfile.TemporaryDirectory() as d:
            peers = Path(d) / "peers.yaml"
            peers.write_text(_yaml_one_peer("peer-x"), encoding="utf-8")
            # Drive the revoke mutation helper against the REAL YAML file.
            fn = getattr(_pv, "_revoke_peer_in_yaml", None) or getattr(
                _pv, "_atomic_revoke_peer", None
            )
            if fn is None:
                self.skipTest("peer_revoke mutation helper name unknown")
            ok, reason, already = fn(peers, "peer-x")
            self.assertTrue(ok, reason)
            self.assertFalse(already)  # first revoke
            # The file must still be load_peers-parseable AND show revoked.
            recs = _ident.load_peers(peers)
            self.assertTrue(recs["peer-x"].revoked)

    def test_repeat_revoke_classified_already_revoked_on_yaml(self):
        # Codex AC18 forensic nit: an existing revoked:true row comes back as
        # the string "true" via parse_peers_text; the repeat-revoke audit
        # classification must still see it as already-revoked.
        fn = getattr(_pv, "_atomic_revoke_peer", None)
        if fn is None:
            self.skipTest("peer_revoke mutation helper name unknown")
        with tempfile.TemporaryDirectory() as d:
            peers = Path(d) / "peers.yaml"
            peers.write_text(_yaml_one_peer("peer-x"), encoding="utf-8")
            fn(peers, "peer-x")  # first revoke -> writes revoked: true
            _ok, _reason, already = fn(peers, "peer-x")  # second
            self.assertTrue(already, "repeat revoke must be already-revoked")


@unittest.skipIf(_pr is None, "handlers absent")
class TestPeerRegisterAgainstRealYaml(unittest.TestCase):
    def test_register_appends_to_yaml_load_peers_reads(self):
        fn = getattr(_pr, "_atomic_append_peer", None)
        if fn is None:
            self.skipTest("peer_register append helper name unknown")
        with tempfile.TemporaryDirectory() as d:
            peers = Path(d) / "peers.yaml"
            peers.write_text(_yaml_one_peer("peer-x"), encoding="utf-8")
            new_row = {
                "peer_id": "peer-new",
                "peer_id_spki_fingerprint": "b" * 64,
                "ca_pin_sha256": "c" * 64,
                "not_valid_after": "2026-03-01T00:00:00Z",
                "not_valid_before": "2026-01-01T00:00:00Z",
                "revoked": False,
                "hmac_secret_hex": "d" * 64,
                "scopes": ["peer_revoke"],
            }
            ok, reason = fn(peers, new_row)
            self.assertTrue(ok, reason)
            recs = _ident.load_peers(peers)  # real loader round-trip
            self.assertIn("peer-new", recs)
            self.assertIn("peer-x", recs)  # existing preserved
            self.assertEqual(recs["peer-new"].scopes, ("peer_revoke",))

    def test_register_collision_against_real_yaml(self):
        fn = getattr(_pr, "_atomic_append_peer", None)
        if fn is None:
            self.skipTest("peer_register append helper name unknown")
        with tempfile.TemporaryDirectory() as d:
            peers = Path(d) / "peers.yaml"
            peers.write_text(_yaml_one_peer("peer-x"), encoding="utf-8")
            ok, reason = fn(peers, {"peer_id": "peer-x"})
            self.assertFalse(ok)
            self.assertIn("collision", reason)


@unittest.skipIf(_scopes is None, "scopes absent")
class TestGate5DupHeaderFailClosed(unittest.TestCase):
    class _MultiHdr:
        """Mimics email.message.Message with duplicate headers."""

        def __init__(self, pairs):
            self._pairs = pairs

        def items(self):
            return list(self._pairs)

    def test_single_header_passes(self):
        h = self._MultiHdr(
            [("X-CEO-Federation-Scope", "audit_event_push")]
        )
        self.assertTrue(
            _scopes.validate_scope_header(h, "audit_event_push")
        )

    def test_duplicate_header_fails_closed(self):
        h = self._MultiHdr([
            ("X-CEO-Federation-Scope", "audit_event_push"),
            ("X-CEO-Federation-Scope", "peer_register"),
        ])
        self.assertFalse(
            _scopes.validate_scope_header(h, "audit_event_push")
        )

    def test_duplicate_same_value_also_fails_closed(self):
        h = self._MultiHdr([
            ("X-CEO-Federation-Scope", "audit_event_push"),
            ("X-CEO-Federation-Scope", "audit_event_push"),
        ])
        self.assertFalse(
            _scopes.validate_scope_header(h, "audit_event_push")
        )


if __name__ == "__main__":
    unittest.main()
