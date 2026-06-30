"""PLAN-112-FOLLOWUP-federation-wire (PHASE2) — REMAINING #1 closure.

Proves the load-bearing functional gap (F-1.7) is closed: load_peers now
parses ``scopes`` + ``audit_event_push_allowlist`` from peers.yaml into
PeerRecord, so the federation_peers_extra dict the server builds carries a
non-empty scopes list and Gate #6 (scopes.peer_has_scope) GRANTS a
registered peer its scope — instead of default-DENYING every peer.

Stdlib-only; deterministic.
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
except Exception:  # pragma: no cover
    _ident = None  # type: ignore
    _scopes = None  # type: ignore

_FPR = "a" * 64  # 64-hex placeholder fingerprint / ca-pin


def _peers_yaml(scope_line: str = "", allowlist_line: str = "") -> str:
    extra = ""
    if scope_line:
        extra += "    {0}\n".format(scope_line)
    if allowlist_line:
        extra += "    {0}\n".format(allowlist_line)
    return (
        "peers:\n"
        "  - peer_id: peer-east-01\n"
        '    peer_id_spki_fingerprint: "{fpr}"\n'
        '    ca_pin_sha256: "{fpr}"\n'
        '    not_valid_after: "2027-01-01T00:00:00Z"\n'
        '    not_valid_before: "2026-01-01T00:00:00Z"\n'
        "    revoked: false\n"
        '    hmac_secret_hex: "{fpr}"\n'
        "{extra}"
    ).format(fpr=_FPR, extra=extra)


def _build_extra(peer):
    """Mirror server.py federation_peers_extra construction for one peer."""
    return {
        "peer_id_spki_fingerprint": peer.peer_id_spki_fingerprint,
        "peer_id_cert_fingerprint": peer.peer_id_cert_fingerprint,
        "scopes": list(getattr(peer, "scopes", []) or []),
        "audit_event_push_allowlist": list(
            getattr(peer, "audit_event_push_allowlist", []) or []
        ),
        "revoked": bool(peer.revoked),
    }


@unittest.skipIf(_ident is None or _scopes is None, "federation pkg absent")
class TestScopesParse(unittest.TestCase):
    def _load(self, text):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "peers.yaml"
            p.write_text(text, encoding="utf-8")
            return _ident.load_peers(p)

    def test_flow_list_scopes_parsed(self):
        peers = self._load(
            _peers_yaml(scope_line="scopes: [peer_register, peer_revoke]")
        )
        peer = peers["peer-east-01"]
        self.assertEqual(peer.scopes, ("peer_register", "peer_revoke"))

    def test_comma_separated_scopes_parsed(self):
        peers = self._load(
            _peers_yaml(scope_line="scopes: peer_register,audit_event_push")
        )
        peer = peers["peer-east-01"]
        self.assertEqual(peer.scopes, ("peer_register", "audit_event_push"))

    def test_single_scalar_scope_parsed(self):
        peers = self._load(_peers_yaml(scope_line="scopes: audit_event_push"))
        self.assertEqual(peers["peer-east-01"].scopes, ("audit_event_push",))

    def test_dedup_preserves_order(self):
        peers = self._load(
            _peers_yaml(scope_line="scopes: [a, b, a, c, b]")
        )
        self.assertEqual(peers["peer-east-01"].scopes, ("a", "b", "c"))

    def test_allowlist_parsed(self):
        peers = self._load(
            _peers_yaml(
                scope_line="scopes: audit_event_push",
                allowlist_line="audit_event_push_allowlist: [skill_used, plan_transition]",
            )
        )
        peer = peers["peer-east-01"]
        self.assertEqual(
            peer.audit_event_push_allowlist, ("skill_used", "plan_transition")
        )

    # ----- the F-1.7 functional closure: Gate #6 GRANTS a granted peer -----

    def test_gate6_grants_when_scope_present(self):
        peers = self._load(_peers_yaml(scope_line="scopes: [audit_event_push]"))
        extra = _build_extra(peers["peer-east-01"])
        # peer_row carries scopes from the extra dict, exactly like server.py.
        peer_row = {"peer_id": "peer-east-01", "scopes": list(extra["scopes"])}
        self.assertTrue(_scopes.peer_has_scope(peer_row, "audit_event_push"))
        # A scope NOT granted is still denied.
        self.assertFalse(_scopes.peer_has_scope(peer_row, "peer_revoke"))

    def test_gate6_default_deny_when_no_scopes(self):
        # Regression: a peer with no scopes field stays read-only (default-OFF).
        peers = self._load(_peers_yaml())
        peer = peers["peer-east-01"]
        self.assertEqual(peer.scopes, ())
        extra = _build_extra(peer)
        peer_row = {"peer_id": "peer-east-01", "scopes": list(extra["scopes"])}
        self.assertFalse(_scopes.peer_has_scope(peer_row, "audit_event_push"))

    # ----- fail-CLOSED on malformed grants -----

    def test_malformed_scope_token_raises(self):
        with self.assertRaises(_ident.PeersFileError):
            self._load(_peers_yaml(scope_line="scopes: [peer register]"))  # space

    def test_crlf_injection_token_raises(self):
        with self.assertRaises(_ident.PeersFileError):
            self._load(_peers_yaml(scope_line="scopes: [foo/../bar]"))

    def test_empty_brackets_yield_empty_tuple(self):
        peers = self._load(_peers_yaml(scope_line="scopes: []"))
        self.assertEqual(peers["peer-east-01"].scopes, ())

    def test_positional_peerrecord_compat_preserved(self):
        # Legacy positional call (PLAN-099 v1.32.0 baseline) must still work:
        # the 2 new fields are last + defaulted.
        import datetime as dt
        rec = _ident.PeerRecord(
            "peer-x", _FPR, _FPR,
            dt.datetime(2027, 1, 1, tzinfo=dt.timezone.utc),
            dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
        )
        self.assertEqual(rec.scopes, ())
        self.assertEqual(rec.audit_event_push_allowlist, ())


if __name__ == "__main__":
    unittest.main()
