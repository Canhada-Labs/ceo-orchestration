"""PLAN-099-FOLLOWUP Wave C.5 — SPKI dispatcher tests (≥15 cases).

Covers identity.py SPKI primitives + server.py/client.py dispatcher
chain per ``peers-yaml-schema-migration.md`` §3 contract.

CRITICAL test: rotation-survives invariant — when a peer rotates its
cert WITHOUT changing the underlying key, the SPKI SHA-256 is
preserved (so the SPKI pin in peers.yaml STILL authenticates the
rotated cert). The DER SHA-256 changes with every rotation. This is
the single most important property of SPKI pinning.

Test framework: unittest.TestCase (mirrors test_cert_inspector.py).
PEM fixtures: generated via openssl subprocess in setUpClass (same
helper pattern as Wave B); we ALSO rotate-resign with the SAME key
to produce the rotation-survives fixture.

Audit emits for the 3 new actions (federation_spki_fingerprint_mismatch
+ federation_pin_legacy_used + federation_peer_invalid_no_fingerprint)
are exercised via a `_safe_emit` monkey-patch that records the call;
the actions themselves are WAVE-F-PENDING (Owner Phase A2-post
kernel-override registers them at Wave F.2).

NOTE on flakiness: per S146 lesson, NO `@pytest.mark.xfail(strict=True)`
is used; we use plain `skipTest` / `skipUnless` for fixture-availability
branches (older openssl on CI may not support every key type).
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# sys.path hook — load identity.py from canonical or staging path
# (mirrors tests/federation/test_cert_inspector.py loader idiom).
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_LIB = _REPO_ROOT / ".claude" / "hooks" / "_lib"
_FED_DIR = _HOOKS_LIB / "federation"
_STAGING_DIR = _REPO_ROOT / ".claude" / "plans" / "PLAN-099-FOLLOWUP" / "wave-c-staging"


def _load_module_from_path(module_name: str, file_path: Path):
    """Load a Python module from an arbitrary file path."""
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    # Register pre-exec so intra-module relative imports resolve.
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_identity():
    """Load identity module — prefer canonical (post-ceremony), fall back
    to wave-c-staging (pre-ceremony)."""
    # Canonical path (post-ceremony Owner Phase A2-post).
    canonical = _FED_DIR / "identity.py"
    if canonical.is_file():
        # Check whether the canonical file has Wave C extensions yet.
        text = canonical.read_text(encoding="utf-8")
        if "compute_spki_fingerprint" in text:
            if str(_HOOKS_LIB) not in sys.path:
                sys.path.insert(0, str(_HOOKS_LIB))
            from federation import identity as ident  # type: ignore
            return ident
    # Staging fallback (pre-ceremony — Wave C sub-agent landed here).
    staging = _STAGING_DIR / "identity_full.py"
    if staging.is_file():
        return _load_module_from_path("identity_wave_c_staging", staging)
    return None


identity = _load_identity()


# Also load the cert_inspector bridge so we can compute hashes ourselves
# for the parity tests.
def _load_cert_inspector():
    canonical = _FED_DIR / "cert_inspector.py"
    if canonical.is_file():
        if str(_HOOKS_LIB) not in sys.path:
            sys.path.insert(0, str(_HOOKS_LIB))
        from federation import cert_inspector as ci  # type: ignore
        return ci
    staging = _REPO_ROOT / ".claude" / "plans" / "PLAN-099-FOLLOWUP" / "cert_inspector.py"
    if staging.is_file():
        return _load_module_from_path("cert_inspector_staging_for_dispatcher", staging)
    return None


cert_inspector = _load_cert_inspector()


# Module-level skip if dependencies missing.
OPENSSL_BIN = shutil.which("openssl")
_IDENT_AVAILABLE = identity is not None
_CI_AVAILABLE = cert_inspector is not None
_OPENSSL_AVAILABLE = OPENSSL_BIN is not None


# ---------------------------------------------------------------------------
# Openssl helpers (fixture generation + rotation-resign)
# ---------------------------------------------------------------------------


def _openssl(*args: str, stdin: Optional[bytes] = None, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [OPENSSL_BIN] + list(args),
        input=stdin,
        capture_output=True,
        timeout=15,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            "openssl {0} failed rc={1}: {2}".format(
                args[:2], proc.returncode, proc.stderr.decode("utf-8", "replace")[:300]
            )
        )
    return proc


def _gen_cert(out_dir: str, name: str, days: int = 30,
              key_path: Optional[str] = None) -> Tuple[str, str]:
    """Generate (or reuse) a key + RSA-2048 self-signed cert.

    Returns (cert_path, key_path). When ``key_path`` is provided, reuse
    that key (used for the rotation-survives fixture: same key, new
    cert → SAME SPKI, DIFFERENT DER).
    """
    cert_path = os.path.join(out_dir, name + ".pem")
    if key_path is None:
        key_path = os.path.join(out_dir, name + ".key")
        _openssl("genrsa", "-out", key_path, "2048")
    _openssl(
        "req", "-x509", "-new", "-key", key_path,
        "-out", cert_path, "-days", str(days), "-nodes",
        "-subj", "/CN={0}".format(name),
    )
    return cert_path, key_path


def _read_pem_bytes(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Base test class — generates fixtures once per session.
# ---------------------------------------------------------------------------


@unittest.skipIf(not _IDENT_AVAILABLE, "identity.py with Wave C extensions not found (canonical/staging)")
@unittest.skipIf(not _CI_AVAILABLE, "cert_inspector bridge not found (canonical/staging)")
@unittest.skipIf(not _OPENSSL_AVAILABLE, "openssl binary not in PATH")
class SpkiDispatcherTestBase(unittest.TestCase):
    """Shared PEM-fixture class. setUpClass generates 5 test certs once.

    Fixtures
    --------
    cert_v1
        Original cert. Has SPKI(v1) + DER(v1).
    cert_v2_rotated
        Rotated cert — SAME private key as v1, NEW validity / serial.
        Expected: SPKI(v2) == SPKI(v1), DER(v2) != DER(v1).
        (This is THE critical rotation-survives invariant fixture.)
    cert_attacker
        Independent cert (DIFFERENT private key). Expected: SPKI + DER
        both differ from v1/v2.
    cert_other
        Second independent cert (for SPKI+DER mixed peer tests where
        we want a cert that matches NEITHER pin).
    """

    tmpdir: Optional[str] = None
    fixtures: Dict[str, Any] = {}

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = tempfile.mkdtemp(prefix="spki-dispatcher-test-")
        d = cls.tmpdir
        cls.fixtures = {}

        # Original cert + key.
        c1, k1 = _gen_cert(d, "v1", days=30)
        cls.fixtures["cert_v1"] = c1
        cls.fixtures["key_v1"] = k1
        cls.fixtures["pem_v1"] = _read_pem_bytes(c1)

        # Rotation: re-sign a NEW cert with the SAME key.
        # The cert serial + dates differ → DER differs;
        # the public key is identical → SPKI is preserved.
        c2, _ = _gen_cert(d, "v2_rotated", days=60, key_path=k1)
        cls.fixtures["cert_v2_rotated"] = c2
        cls.fixtures["pem_v2_rotated"] = _read_pem_bytes(c2)

        # Independent attacker cert (different key + everything).
        ca, _ = _gen_cert(d, "attacker", days=30)
        cls.fixtures["cert_attacker"] = ca
        cls.fixtures["pem_attacker"] = _read_pem_bytes(ca)

        # Second independent cert.
        co, _ = _gen_cert(d, "other", days=30)
        cls.fixtures["cert_other"] = co
        cls.fixtures["pem_other"] = _read_pem_bytes(co)

        # Pre-compute fingerprints for the four certs (used as expected
        # values in test assertions).
        cls.fixtures["spki_v1"] = cert_inspector.spki_sha256_hex(cls.fixtures["pem_v1"])
        cls.fixtures["der_v1"] = cert_inspector.der_sha256_hex(cls.fixtures["pem_v1"])
        cls.fixtures["spki_v2"] = cert_inspector.spki_sha256_hex(cls.fixtures["pem_v2_rotated"])
        cls.fixtures["der_v2"] = cert_inspector.der_sha256_hex(cls.fixtures["pem_v2_rotated"])
        cls.fixtures["spki_attacker"] = cert_inspector.spki_sha256_hex(cls.fixtures["pem_attacker"])
        cls.fixtures["der_attacker"] = cert_inspector.der_sha256_hex(cls.fixtures["pem_attacker"])
        cls.fixtures["spki_other"] = cert_inspector.spki_sha256_hex(cls.fixtures["pem_other"])
        cls.fixtures["der_other"] = cert_inspector.der_sha256_hex(cls.fixtures["pem_other"])

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.tmpdir:
            shutil.rmtree(cls.tmpdir, ignore_errors=True)


# ===========================================================================
# Group A — identity.py primitives (computation parity + selection)
# ===========================================================================


class TestIdentityPrimitives(SpkiDispatcherTestBase):
    """Direct exercises of compute_spki_fingerprint /
    compute_der_fingerprint_from_pem / select_pin_for_peer."""

    def test_01_spki_computation_parity_with_cert_inspector(self):
        """compute_spki_fingerprint(pem) == cert_inspector.spki_sha256_hex(pem).

        Establishes the delegation contract: identity.py is a thin shim
        over the bridge, no double-hashing or normalisation drift.
        """
        pem = self.fixtures["pem_v1"]
        via_identity = identity.compute_spki_fingerprint(pem)
        via_bridge = cert_inspector.spki_sha256_hex(pem)
        self.assertEqual(via_identity, via_bridge)
        self.assertEqual(len(via_identity), 64)

    def test_02_der_computation_parity_with_cert_inspector(self):
        """compute_der_fingerprint_from_pem(pem) ==
        cert_inspector.der_sha256_hex(pem)."""
        pem = self.fixtures["pem_v1"]
        via_identity = identity.compute_der_fingerprint_from_pem(pem)
        via_bridge = cert_inspector.der_sha256_hex(pem)
        self.assertEqual(via_identity, via_bridge)
        self.assertEqual(len(via_identity), 64)

    def test_03_critical_rotation_survives_invariant(self):
        """SAME key, NEW cert → SAME SPKI, DIFFERENT DER.

        THE single most important Wave C test. Failure here means SPKI
        pinning provides NO operational value over DER pinning.
        """
        spki_v1 = identity.compute_spki_fingerprint(self.fixtures["pem_v1"])
        spki_v2 = identity.compute_spki_fingerprint(self.fixtures["pem_v2_rotated"])
        der_v1 = identity.compute_der_fingerprint_from_pem(self.fixtures["pem_v1"])
        der_v2 = identity.compute_der_fingerprint_from_pem(self.fixtures["pem_v2_rotated"])
        self.assertEqual(
            spki_v1, spki_v2,
            "ROTATION-SURVIVES FAIL: SPKI should be identical across "
            "key-preserving rotations (v1 SPKI={0}, v2 SPKI={1})".format(spki_v1, spki_v2)
        )
        self.assertNotEqual(
            der_v1, der_v2,
            "DER should differ across rotations (different serial + "
            "validity → different DER). Got identical DER {0}".format(der_v1)
        )

    def test_04_select_pin_spki_preferred_when_both_present(self):
        """SPKI+DER row → select_pin_for_peer returns ('spki', spki_value)."""
        peer_row = {
            "peer_id": "peer-east-01",
            "peer_id_spki_fingerprint": "a" * 64,
            "peer_id_cert_fingerprint": "b" * 64,
        }
        pin_type, pin_value = identity.select_pin_for_peer(peer_row)
        self.assertEqual(pin_type, "spki")
        self.assertEqual(pin_value, "a" * 64)

    def test_05_select_pin_der_fallback_when_spki_empty(self):
        """SPKI empty + DER set → ('der', der_value)."""
        peer_row = {
            "peer_id": "peer-legacy-02",
            "peer_id_spki_fingerprint": "",
            "peer_id_cert_fingerprint": "c" * 64,
        }
        pin_type, pin_value = identity.select_pin_for_peer(peer_row)
        self.assertEqual(pin_type, "der")
        self.assertEqual(pin_value, "c" * 64)

    def test_06_select_pin_raises_when_neither_set(self):
        """Neither pin → PinSelectionError (parse-time invariant breach)."""
        peer_row = {"peer_id": "peer-bad-03"}
        with self.assertRaises(identity.PinSelectionError):
            identity.select_pin_for_peer(peer_row)

    def test_07_select_pin_treats_empty_string_as_missing(self):
        """peer_id_spki_fingerprint = "" must NOT match (edge case)."""
        peer_row = {
            "peer_id": "peer-edge-04",
            "peer_id_spki_fingerprint": "",   # empty
            "peer_id_cert_fingerprint": "",   # empty
        }
        with self.assertRaises(identity.PinSelectionError):
            identity.select_pin_for_peer(peer_row)

    def test_08_select_pin_treats_whitespace_as_missing(self):
        """Whitespace-only pin treated as missing (not as match-empty)."""
        peer_row = {
            "peer_id": "peer-ws-05",
            "peer_id_spki_fingerprint": "   ",
            "peer_id_cert_fingerprint": "d" * 64,
        }
        pin_type, pin_value = identity.select_pin_for_peer(peer_row)
        self.assertEqual(pin_type, "der")  # SPKI whitespace fell through
        self.assertEqual(pin_value, "d" * 64)


# ===========================================================================
# Group B — Authentication dispatcher (mirrors server.py §3 chain)
#
# These tests exercise the §3 dispatcher logic directly via a Python
# reimplementation of authenticate_peer() — server.py wires the same
# chain into _lookup_peer_record() but unit-testing the HTTP server
# requires a full TLS stack. The dispatcher logic is the security-
# critical part; this group covers it exhaustively.
# ===========================================================================


def _authenticate_peer_simulator(
    presented_pem: bytes,
    registry_row: Dict[str, Any],
    on_emit: Optional[Any] = None,
) -> Tuple[bool, str]:
    """Pure-Python re-implementation of server.py SPKI dispatcher §3.

    Returns ``(ok, reason_or_pin_type)``. Same chain as
    server.py:_lookup_peer_record but operates on the PEM bytes
    directly (no http.server / ssl stack). on_emit is called as
    ``on_emit(action, **fields)`` for each audit emit; passing
    ``None`` skips emits.
    """
    def emit(action: str, **fields: Any) -> None:
        if on_emit is not None:
            on_emit(action, **fields)

    try:
        pin_type, pin_value = identity.select_pin_for_peer(registry_row)
    except identity.PinSelectionError:
        emit(
            "federation_peer_invalid_no_fingerprint",
            peer_id=registry_row.get("peer_id", ""),
        )
        return (False, "no_pin_configured")

    if pin_type == "spki":
        try:
            presented_spki = identity.compute_spki_fingerprint(presented_pem)
        except (ValueError, TypeError, ImportError) as exc:
            emit(
                "federation_spki_fingerprint_mismatch",
                peer_id=registry_row.get("peer_id", ""),
                reason="presented_spki_compute_failed:{0}".format(type(exc).__name__),
            )
            return (False, "presented_spki_compute_failed")
        if identity.compare_fingerprints(presented_spki, pin_value):
            return (True, "spki-match")
        emit(
            "federation_spki_fingerprint_mismatch",
            peer_id=registry_row.get("peer_id", ""),
            reason="spki_mismatch",
        )
        return (False, "spki-mismatch")

    # pin_type == "der"
    presented_der = identity.compute_der_fingerprint_from_pem(presented_pem)
    if identity.compare_fingerprints(presented_der, pin_value):
        emit(
            "federation_pin_legacy_used",
            peer_id=registry_row.get("peer_id", ""),
            pin_type="der",
        )
        return (True, "der-fallback")
    return (False, "der-mismatch")


class TestAuthenticationDispatcher(SpkiDispatcherTestBase):

    def test_09_spki_only_peer_legitimate_handshake_accepts(self):
        """SPKI-only peer + matching cert → ACCEPT."""
        registry_row = {
            "peer_id": "spki-only-peer",
            "peer_id_spki_fingerprint": self.fixtures["spki_v1"],
            "peer_id_cert_fingerprint": "",
        }
        ok, reason = _authenticate_peer_simulator(
            self.fixtures["pem_v1"], registry_row,
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "spki-match")

    def test_10_spki_only_peer_rotation_still_accepts(self):
        """SPKI-only peer registered with cert_v1's SPKI; peer presents
        cert_v2_rotated (SAME key, NEW cert) → STILL ACCEPTS.

        Rotation-survives invariant at the dispatcher level. This is
        the operational pay-off for SPKI pinning.
        """
        registry_row = {
            "peer_id": "rotated-peer",
            "peer_id_spki_fingerprint": self.fixtures["spki_v1"],  # pin v1
            "peer_id_cert_fingerprint": "",
        }
        # Confirm precondition: SPKI(v1) == SPKI(v2), DER(v1) != DER(v2)
        self.assertEqual(self.fixtures["spki_v1"], self.fixtures["spki_v2"])
        self.assertNotEqual(self.fixtures["der_v1"], self.fixtures["der_v2"])
        # Peer presents v2 (rotated); pin is v1 SPKI.
        ok, reason = _authenticate_peer_simulator(
            self.fixtures["pem_v2_rotated"], registry_row,
        )
        self.assertTrue(
            ok,
            "ROTATION-SURVIVES DISPATCHER FAIL: SPKI pin should match "
            "rotated cert (reason={0!r})".format(reason)
        )
        self.assertEqual(reason, "spki-match")

    def test_11_der_only_legacy_peer_accepts(self):
        """DER-only (legacy v1.x) peer + matching cert → ACCEPT + emit
        federation_pin_legacy_used."""
        emits: List[Tuple[str, Dict[str, Any]]] = []
        registry_row = {
            "peer_id": "legacy-peer",
            "peer_id_spki_fingerprint": "",
            "peer_id_cert_fingerprint": self.fixtures["der_v1"],
        }
        ok, reason = _authenticate_peer_simulator(
            self.fixtures["pem_v1"], registry_row,
            on_emit=lambda action, **fields: emits.append((action, fields)),
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "der-fallback")
        # federation_pin_legacy_used MUST fire on every legacy handshake.
        actions = [a for (a, _) in emits]
        self.assertIn(
            "federation_pin_legacy_used", actions,
            "federation_pin_legacy_used MUST emit on DER fallback (got {0})".format(actions)
        )

    def test_12_spki_plus_der_peer_spki_match_accepts(self):
        """SPKI+DER peer (90d soak); presented cert matches SPKI → ACCEPT."""
        registry_row = {
            "peer_id": "dual-pinned-peer",
            "peer_id_spki_fingerprint": self.fixtures["spki_v1"],
            "peer_id_cert_fingerprint": self.fixtures["der_v1"],
        }
        ok, reason = _authenticate_peer_simulator(
            self.fixtures["pem_v1"], registry_row,
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "spki-match")

    def test_13_downgrade_blocked_spki_mismatch_der_match(self):
        """SPKI+DER peer; presented cert matches DER but NOT SPKI → DENY.

        Downgrade attack scenario: attacker swapped the registered SPKI
        (via separate compromise) but the underlying cert presented
        still has the legitimate DER. Without the no-downgrade rule, an
        attacker could force fallback. Test confirms server REFUSES.
        """
        emits: List[Tuple[str, Dict[str, Any]]] = []
        # Construct a registry row that has v1 DER but an SPKI that
        # belongs to a DIFFERENT cert. Peer presents v1 → DER matches,
        # SPKI mismatches → MUST deny (no downgrade).
        registry_row = {
            "peer_id": "downgrade-target",
            "peer_id_spki_fingerprint": self.fixtures["spki_attacker"],  # NOT v1
            "peer_id_cert_fingerprint": self.fixtures["der_v1"],         # matches v1
        }
        ok, reason = _authenticate_peer_simulator(
            self.fixtures["pem_v1"], registry_row,
            on_emit=lambda action, **fields: emits.append((action, fields)),
        )
        self.assertFalse(
            ok,
            "DOWNGRADE BLOCKED FAIL: SPKI was declared but mismatched; "
            "DER should NOT be consulted; got reason={0!r}".format(reason)
        )
        self.assertEqual(reason, "spki-mismatch")
        # Mismatch MUST emit federation_spki_fingerprint_mismatch.
        actions = [a for (a, _) in emits]
        self.assertIn("federation_spki_fingerprint_mismatch", actions)

    def test_14_no_pin_peer_rejects_at_dispatch(self):
        """Peer row with neither SPKI nor DER → DENY + emit
        federation_peer_invalid_no_fingerprint."""
        emits: List[Tuple[str, Dict[str, Any]]] = []
        registry_row = {
            "peer_id": "no-pin-peer",
            # Both pins absent / empty.
            "peer_id_spki_fingerprint": "",
            "peer_id_cert_fingerprint": "",
        }
        ok, reason = _authenticate_peer_simulator(
            self.fixtures["pem_v1"], registry_row,
            on_emit=lambda action, **fields: emits.append((action, fields)),
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "no_pin_configured")
        actions = [a for (a, _) in emits]
        self.assertIn("federation_peer_invalid_no_fingerprint", actions)

    def test_15_spki_only_peer_attacker_cert_denies(self):
        """SPKI-only peer; attacker presents UNRELATED cert → DENY +
        federation_spki_fingerprint_mismatch."""
        emits: List[Tuple[str, Dict[str, Any]]] = []
        registry_row = {
            "peer_id": "spki-only-peer-2",
            "peer_id_spki_fingerprint": self.fixtures["spki_v1"],
            "peer_id_cert_fingerprint": "",
        }
        ok, reason = _authenticate_peer_simulator(
            self.fixtures["pem_attacker"], registry_row,
            on_emit=lambda action, **fields: emits.append((action, fields)),
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "spki-mismatch")
        actions = [a for (a, _) in emits]
        self.assertIn("federation_spki_fingerprint_mismatch", actions)


# ===========================================================================
# Group C — Client-side mirror (downgrade defense at the client too)
# ===========================================================================


def _client_verify_simulator(
    presented_der_bytes: bytes,
    presented_pem_bytes: bytes,
    server_spki_pin: str,
    server_der_pin: str,
) -> Tuple[bool, str]:
    """Pure-Python re-implementation of client.py SPKI dispatcher
    (the in-_get block).

    Returns ``(ok, reason_or_status)``. Mirrors the server logic — SPKI
    pin takes precedence; mismatch → fail-CLOSED (no downgrade).
    """
    presented_der_fp = hashlib.sha256(presented_der_bytes).hexdigest()
    spki_pin = (server_spki_pin or "").strip()
    der_pin = (server_der_pin or "").strip()
    if spki_pin:
        try:
            presented_spki_fp = identity.compute_spki_fingerprint(presented_pem_bytes)
        except (ValueError, TypeError, ImportError) as exc:
            return (False, "client_spki_compute_failed:{0}".format(type(exc).__name__))
        if identity.compare_fingerprints(presented_spki_fp, spki_pin):
            return (True, "spki-match")
        return (False, "client_spki_mismatch")
    if der_pin:
        if identity.compare_fingerprints(presented_der_fp, der_pin):
            return (True, "der-fallback")
        return (False, "client_der_mismatch")
    return (False, "no_pin_configured")


class TestClientSideMirror(SpkiDispatcherTestBase):

    def test_16_client_spki_pin_legitimate_server_accepts(self):
        """Client has SPKI pin; server presents matching cert → connect OK."""
        # Reconstruct DER bytes (raw DER, not PEM) — client.py gets DER
        # from sock.getpeercert(True).
        der_bytes = ssl.PEM_cert_to_DER_cert(self.fixtures["pem_v1"].decode("ascii"))
        ok, reason = _client_verify_simulator(
            presented_der_bytes=der_bytes,
            presented_pem_bytes=self.fixtures["pem_v1"],
            server_spki_pin=self.fixtures["spki_v1"],
            server_der_pin="",
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "spki-match")

    def test_17_client_spki_pin_attacker_server_denies(self):
        """Client has SPKI pin; server presents UNRELATED cert → fail."""
        der_bytes = ssl.PEM_cert_to_DER_cert(self.fixtures["pem_attacker"].decode("ascii"))
        ok, reason = _client_verify_simulator(
            presented_der_bytes=der_bytes,
            presented_pem_bytes=self.fixtures["pem_attacker"],
            server_spki_pin=self.fixtures["spki_v1"],
            server_der_pin="",
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "client_spki_mismatch")

    def test_18_client_downgrade_blocked_spki_mismatch_der_match(self):
        """Client has BOTH pins. Server presents a cert whose DER matches
        the legacy DER pin but whose SPKI does NOT match the SPKI pin.
        Client MUST refuse the connection (no downgrade)."""
        der_bytes = ssl.PEM_cert_to_DER_cert(self.fixtures["pem_v1"].decode("ascii"))
        ok, reason = _client_verify_simulator(
            presented_der_bytes=der_bytes,
            presented_pem_bytes=self.fixtures["pem_v1"],
            server_spki_pin=self.fixtures["spki_attacker"],  # bogus SPKI
            server_der_pin=self.fixtures["der_v1"],           # legit DER
        )
        self.assertFalse(
            ok,
            "CLIENT DOWNGRADE BLOCKED FAIL: SPKI declared + mismatch; "
            "client MUST NOT fall back to DER pin. Got reason={0!r}".format(reason)
        )
        self.assertEqual(reason, "client_spki_mismatch")

    def test_19_client_der_legacy_only_pin_accepts(self):
        """Client has only DER pin (no SPKI configured) → DER fallback OK."""
        der_bytes = ssl.PEM_cert_to_DER_cert(self.fixtures["pem_v1"].decode("ascii"))
        ok, reason = _client_verify_simulator(
            presented_der_bytes=der_bytes,
            presented_pem_bytes=self.fixtures["pem_v1"],
            server_spki_pin="",
            server_der_pin=self.fixtures["der_v1"],
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "der-fallback")

    def test_20_client_no_pin_at_all_refuses(self):
        """Client config has NEITHER pin → refuse to connect."""
        der_bytes = ssl.PEM_cert_to_DER_cert(self.fixtures["pem_v1"].decode("ascii"))
        ok, reason = _client_verify_simulator(
            presented_der_bytes=der_bytes,
            presented_pem_bytes=self.fixtures["pem_v1"],
            server_spki_pin="",
            server_der_pin="",
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "no_pin_configured")


# ===========================================================================
# Group D — Real-loader + dispatcher integration (Codex Wave-C P1 F-005 fix)
#
# Codex called out that Groups A-C only exercise local Python
# re-implementations of the dispatcher (the `_authenticate_peer_simulator`
# / `_client_verify_simulator` helpers). They never call the actual
# ``identity_full.load_peers`` parser, never load the real
# ``server_full.py`` / ``client_full.py`` modules, and never catch
# the original ``federation_peers_extra`` wire-up gap that motivated
# F-001. This group closes that gap: each test runs the REAL
# ``load_peers`` against a real ``peers.yaml`` file on disk + exercises
# the dispatcher through a thin fake handler that calls the real
# ``server_full._FederationHandler._lookup_peer_record`` method via
# its unbound form (so we don't need a live TLS server).
# ===========================================================================


def _install_server_module_stubs() -> None:
    """Pre-register stub modules so wave-c-staging/server_full.py loads.

    server_full.py imports `identity` / `replay` / `audit_chain` via
    flat-import fallbacks. Those names collide with unrelated top-level
    packages in this repo (e.g. ``.claude/scripts/replay/``). We
    pre-register minimal stubs under each name so the staging file's
    `from replay import ...` etc. resolves to symbols server_full
    needs WITHOUT touching the real modules.

    Idempotent — repeated calls are safe.
    """
    import types as _types

    # identity — alias to the already-loaded identity_full module.
    if identity is not None:
        sys.modules.setdefault("identity", identity)

    # replay — minimal stub with ReplayCache + ReplayDecision +
    # parse_rfc3339_utc symbols. We do NOT exercise replay logic in
    # these tests (the dispatcher tests bypass the replay path by
    # invoking _lookup_peer_record directly), so the stubs only need
    # to be import-resolvable.
    if "replay" not in sys.modules or not hasattr(sys.modules["replay"], "ReplayCache"):
        replay_stub = _types.ModuleType("replay_stub_for_server_full")

        class _StubReplayCache:
            def __init__(self, max_skew_seconds: int = 0) -> None:
                self.max_skew_seconds = max_skew_seconds

            def check_and_record(self, *args: Any, **kwargs: Any):
                return None

        class _StubReplayDecision:
            ACCEPT = "accept"
            REJECT_REPLAY = "reject_replay"
            REJECT_SKEW = "reject_skew"

        def _stub_parse_rfc3339_utc(value: str):
            import datetime as _dt
            return _dt.datetime(2026, 1, 1, tzinfo=_dt.timezone.utc)

        replay_stub.ReplayCache = _StubReplayCache  # type: ignore[attr-defined]
        replay_stub.ReplayDecision = _StubReplayDecision  # type: ignore[attr-defined]
        replay_stub.parse_rfc3339_utc = _stub_parse_rfc3339_utc  # type: ignore[attr-defined]
        sys.modules["replay"] = replay_stub

    # audit_chain — minimal stub with CORRELATION_ID_HEADER +
    # stamp_local_with_correlation.
    if "audit_chain" not in sys.modules or not hasattr(sys.modules["audit_chain"], "CORRELATION_ID_HEADER"):
        ac_stub = _types.ModuleType("audit_chain_stub_for_server_full")
        ac_stub.CORRELATION_ID_HEADER = "X-Federation-Correlation-Id"  # type: ignore[attr-defined]

        def _stub_stamp_local_with_correlation(*args: Any, **kwargs: Any) -> str:
            return ""

        ac_stub.stamp_local_with_correlation = _stub_stamp_local_with_correlation  # type: ignore[attr-defined]
        sys.modules["audit_chain"] = ac_stub


def _load_server_module():
    """Load ``server_full.py`` — prefer canonical, fall back to staging.

    Mirrors ``_load_identity`` idiom. Returns the imported module or
    ``None`` when neither location is available.
    """
    canonical = _FED_DIR / "server.py"
    if canonical.is_file():
        text = canonical.read_text(encoding="utf-8")
        if "_lookup_peer_record" in text and "_resolve_peer" in text:
            if str(_HOOKS_LIB) not in sys.path:
                sys.path.insert(0, str(_HOOKS_LIB))
            from federation import server as srv  # type: ignore
            return srv
    staging = _STAGING_DIR / "server_full.py"
    if staging.is_file():
        # Pre-register identity_full + replay + audit_chain stubs so
        # server_full's flat-import fallback path resolves cleanly even
        # when there are name collisions with other top-level packages
        # in this repo (e.g. `.claude/scripts/replay/`).
        _install_server_module_stubs()
        return _load_module_from_path("server_wave_c_staging", staging)
    return None


server_mod = _load_server_module()
_SERVER_AVAILABLE = server_mod is not None


def _make_peers_yaml(
    rows: List[Dict[str, str]],
    out_path: Path,
) -> Path:
    """Write a minimal peers.yaml file mirroring the loader's grammar.

    Each row dict may include any of:
      peer_id, peer_id_spki_fingerprint, peer_id_cert_fingerprint,
      ca_pin_sha256, not_valid_after, not_valid_before, revoked,
      hmac_secret_hex.
    Missing fields are silently omitted (the loader will validate).
    """
    lines: List[str] = ["peers:"]
    field_order = (
        "peer_id",
        "peer_id_spki_fingerprint",
        "peer_id_cert_fingerprint",
        "ca_pin_sha256",
        "not_valid_after",
        "not_valid_before",
        "revoked",
        "hmac_secret_hex",
    )
    for row in rows:
        first = True
        for fld in field_order:
            if fld not in row:
                continue
            val = row[fld]
            if first:
                lines.append("  - {0}: {1}".format(fld, _yaml_quote(val)))
                first = False
            else:
                lines.append("    {0}: {1}".format(fld, _yaml_quote(val)))
        if first:
            # Empty row — still emit a list marker so loader sees it.
            lines.append("  -")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def _yaml_quote(value: str) -> str:
    """Quote string values for the minimal peers.yaml grammar."""
    s = str(value)
    # Booleans / numbers / ISO datetimes can stay unquoted in the
    # loader's grammar; hex values are safe; quote anything containing
    # `:` or `#` for safety.
    if s.lower() in ("true", "false") or s == "":
        return '"{0}"'.format(s)
    if any(ch in s for ch in (":", "#", "'", '"')):
        return '"{0}"'.format(s.replace('"', '\\"'))
    return '"{0}"'.format(s)


class _FakeConnection:
    """Stand-in for the SSL socket — yields a pre-baked peer cert DER."""

    def __init__(self, der_bytes: bytes) -> None:
        self._der = der_bytes

    def getpeercert(self, binary_form: bool = False):
        if not self._der:
            return None
        return self._der if binary_form else {}


class _FakeServerState:
    """Stand-in for the http.server.HTTPServer instance.

    Carries ``federation_peers`` + ``federation_peers_extra`` exactly
    the way ``serve_forever`` would populate them, so
    ``_lookup_peer_record`` can be called against this object via the
    unbound method form.
    """

    def __init__(
        self,
        peers: Dict[str, Any],
        peers_extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.federation_peers = peers
        self.federation_peers_extra = peers_extra or {}


class _FakeHandler:
    """Minimal stand-in for ``_FederationHandler``.

    Holds the ``connection`` + ``server`` attributes the real
    ``_lookup_peer_record`` reads, plus the audit-emit shims so they
    record calls instead of going to the real audit log.
    """

    def __init__(
        self,
        presented_der: bytes,
        peers: Dict[str, Any],
        peers_extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.connection = _FakeConnection(presented_der)
        self.server = _FakeServerState(peers, peers_extra)
        self.headers: Dict[str, str] = {}
        self.client_address = ("127.0.0.1", 0)
        self.path = "/"
        self.emits: List[Tuple[str, Dict[str, Any]]] = []

    # The real handler computes the DER fingerprint from the presented
    # cert; mirror that helper here.
    def _lookup_peer_fpr(self) -> str:
        der = self.connection.getpeercert(True)
        if not der:
            return ""
        return hashlib.sha256(der).hexdigest()

    def _presented_cert_pem_bytes(self) -> bytes:
        der = self.connection.getpeercert(True)
        if not der:
            return b""
        return ssl.DER_cert_to_PEM_cert(der).encode("ascii")

    def _client_ip(self) -> str:
        return self.client_address[0]

    # Emit recorders — substitute for _safe_emit at the handler level.
    def _emit_spki_fingerprint_mismatch(self, peer_id: str, reason: str = "spki_mismatch") -> None:
        self.emits.append((
            "federation_spki_fingerprint_mismatch",
            {"peer_id": peer_id, "reason": reason},
        ))

    def _emit_pin_legacy_used(self, peer_id: str) -> None:
        self.emits.append((
            "federation_pin_legacy_used",
            {"peer_id": peer_id, "pin_type": "der"},
        ))

    def _emit_peer_invalid_no_fingerprint(self, peer_id: str) -> None:
        self.emits.append((
            "federation_peer_invalid_no_fingerprint",
            {"peer_id": peer_id},
        ))


def _utc_iso(offset_days: int = 0) -> str:
    import datetime as _dt
    base = _dt.datetime(2026, 5, 20, tzinfo=_dt.timezone.utc)
    return (base + _dt.timedelta(days=offset_days)).strftime("%Y-%m-%dT%H:%M:%SZ")


@unittest.skipIf(not _IDENT_AVAILABLE, "identity.py with Wave C extensions not found (canonical/staging)")
@unittest.skipIf(not _CI_AVAILABLE, "cert_inspector bridge not found (canonical/staging)")
@unittest.skipIf(not _OPENSSL_AVAILABLE, "openssl binary not in PATH")
@unittest.skipIf(not _SERVER_AVAILABLE, "server_full.py not loadable (Wave C staging missing)")
class TestRealLoaderDispatcherIntegration(SpkiDispatcherTestBase):
    """Exercise the REAL identity_full.load_peers + real
    server_full._FederationHandler._lookup_peer_record.

    Codex Wave-C P1 F-005: Groups A-C used Python re-implementations
    that masked the original federation_peers_extra wire-up gap.
    This group catches that class of bug by routing through the
    actual loader + the actual dispatcher method.
    """

    # ----- F-002 + F-001: SPKI-only row loads + matches via dispatcher -----

    def test_real_loader_spki_only_row_loads_cleanly(self):
        """A v2.0 SPKI-only row (no DER pin) MUST load without error.

        Codex Wave-C P0 F-002 — pre-fix the loader marked
        peer_id_cert_fingerprint as required and rejected this row at
        startup. Post-fix the at-least-one invariant accepts it.
        """
        tmpdir = tempfile.mkdtemp(prefix="real-loader-spki-only-")
        try:
            peers_path = Path(tmpdir) / "peers.yaml"
            _make_peers_yaml(
                [
                    {
                        "peer_id": "peer-spki-only",
                        "peer_id_spki_fingerprint": self.fixtures["spki_v1"],
                        # peer_id_cert_fingerprint deliberately omitted.
                        "ca_pin_sha256": "e" * 64,
                        "not_valid_after": _utc_iso(60),
                        "not_valid_before": _utc_iso(-1),
                        "revoked": "false",
                    },
                ],
                peers_path,
            )
            peers = identity.load_peers(peers_path)
            self.assertIn("peer-spki-only", peers)
            rec = peers["peer-spki-only"]
            # F-001 fix: SPKI MUST survive load (was dropped pre-fix).
            self.assertEqual(rec.peer_id_spki_fingerprint, self.fixtures["spki_v1"])
            # DER stays empty (legitimate v2.0 SPKI-only install).
            self.assertEqual(rec.peer_id_cert_fingerprint, "")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_real_dispatcher_spki_only_peer_accepts_matching_cert(self):
        """SPKI-only loaded row + matching cert → _lookup_peer_record
        returns the PeerRecord."""
        tmpdir = tempfile.mkdtemp(prefix="real-disp-spki-only-")
        try:
            peers_path = Path(tmpdir) / "peers.yaml"
            _make_peers_yaml(
                [
                    {
                        "peer_id": "peer-spki-only-2",
                        "peer_id_spki_fingerprint": self.fixtures["spki_v1"],
                        "ca_pin_sha256": "e" * 64,
                        "not_valid_after": _utc_iso(60),
                        "not_valid_before": _utc_iso(-1),
                        "revoked": "false",
                    },
                ],
                peers_path,
            )
            peers = identity.load_peers(peers_path)
            # F-001 fix: serve_forever-equivalent peers_extra carry.
            peers_extra = {
                p.peer_id: {
                    "peer_id_spki_fingerprint": p.peer_id_spki_fingerprint,
                    "peer_id_cert_fingerprint": p.peer_id_cert_fingerprint,
                }
                for p in peers.values()
            }
            der_bytes = ssl.PEM_cert_to_DER_cert(
                self.fixtures["pem_v1"].decode("ascii")
            )
            fake = _FakeHandler(der_bytes, peers, peers_extra)
            # Call the real method via the unbound form on the real class.
            handler_cls = server_mod._FederationHandler
            rec = handler_cls._lookup_peer_record(fake)
            self.assertIsNotNone(
                rec,
                "Real dispatcher should ACCEPT SPKI-only peer with matching cert"
            )
            self.assertEqual(rec.peer_id, "peer-spki-only-2")
            # And no mismatch emits along the way.
            mismatches = [e for (e, _) in fake.emits
                          if e == "federation_spki_fingerprint_mismatch"]
            self.assertEqual(
                mismatches, [],
                "Unexpected SPKI mismatch emit during clean-accept path",
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    # ----- F-001: dual-pin row REQUIRES SPKI match (downgrade-blocked) -----

    def test_real_dispatcher_dual_pin_blocks_downgrade(self):
        """Dual-pin row + cert that matches DER but NOT SPKI → DENY.

        Codex Wave-C P0 F-001 — pre-fix the loader stored only DER + the
        dispatcher silently downgraded to DER comparison, accepting the
        cert. Post-fix the loaded PeerRecord carries the declared
        SPKI; the dispatcher takes the SPKI branch + refuses.

        Constructed scenario: register a peer with v1's DER pin + the
        ATTACKER's SPKI. Present v1 cert. DER matches; SPKI does not.
        Pre-F-001: dispatcher would accept (silent downgrade).
        Post-F-001: dispatcher refuses with SPKI-mismatch emit.
        """
        tmpdir = tempfile.mkdtemp(prefix="real-disp-downgrade-")
        try:
            peers_path = Path(tmpdir) / "peers.yaml"
            _make_peers_yaml(
                [
                    {
                        "peer_id": "peer-downgrade-target",
                        # SPKI from attacker cert (the declared SPKI we
                        # want enforced).
                        "peer_id_spki_fingerprint": self.fixtures["spki_attacker"],
                        # DER from v1 cert (matches what will be presented).
                        "peer_id_cert_fingerprint": self.fixtures["der_v1"],
                        "ca_pin_sha256": "e" * 64,
                        "not_valid_after": _utc_iso(60),
                        "not_valid_before": _utc_iso(-1),
                        "revoked": "false",
                    },
                ],
                peers_path,
            )
            peers = identity.load_peers(peers_path)
            # Sanity: post-F-001 PeerRecord MUST carry the declared SPKI.
            rec = peers["peer-downgrade-target"]
            self.assertEqual(
                rec.peer_id_spki_fingerprint,
                self.fixtures["spki_attacker"],
                "F-001 regression: SPKI not preserved through load_peers"
            )

            peers_extra = {
                p.peer_id: {
                    "peer_id_spki_fingerprint": p.peer_id_spki_fingerprint,
                    "peer_id_cert_fingerprint": p.peer_id_cert_fingerprint,
                }
                for p in peers.values()
            }
            der_bytes = ssl.PEM_cert_to_DER_cert(
                self.fixtures["pem_v1"].decode("ascii")
            )
            fake = _FakeHandler(der_bytes, peers, peers_extra)
            handler_cls = server_mod._FederationHandler
            result = handler_cls._lookup_peer_record(fake)
            self.assertIsNone(
                result,
                "DOWNGRADE BLOCKED FAIL: dispatcher returned a peer for a "
                "row whose declared SPKI did NOT match the presented cert "
                "(SPKI must NOT silently downgrade to DER)"
            )
            # Emit must have fired exactly once for SPKI mismatch.
            mismatches = [e for (e, _) in fake.emits
                          if e == "federation_spki_fingerprint_mismatch"]
            self.assertEqual(
                len(mismatches), 1,
                "Expected exactly one federation_spki_fingerprint_mismatch "
                "emit; got emits={0!r}".format(fake.emits),
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    # ----- F-003: no-pin row raises specific subclass + dispatcher emits -----

    def test_real_loader_no_pin_row_raises_specific_subclass(self):
        """Row with NEITHER pin → PeerHasNoFingerprintError (subclass).

        Codex Wave-C P0 F-003 — pre-fix the loader required DER and
        raised generic PeersFileError → server emitted
        federation_connection_rejected, not the required
        federation_peer_invalid_no_fingerprint. Post-fix the specific
        subclass propagates + the server wrapper emits the right
        action BEFORE re-raising.
        """
        tmpdir = tempfile.mkdtemp(prefix="real-loader-no-pin-")
        try:
            peers_path = Path(tmpdir) / "peers.yaml"
            _make_peers_yaml(
                [
                    {
                        "peer_id": "peer-no-pin",
                        # Both fingerprint fields omitted entirely.
                        "ca_pin_sha256": "e" * 64,
                        "not_valid_after": _utc_iso(60),
                        "not_valid_before": _utc_iso(-1),
                        "revoked": "false",
                    },
                ],
                peers_path,
            )
            with self.assertRaises(identity.PeerHasNoFingerprintError) as cm:
                identity.load_peers(peers_path)
            # Subclass must still be a PeersFileError (catch-all path).
            self.assertIsInstance(cm.exception, identity.PeersFileError)
            # peer_id attribute exposed for the audit emit.
            self.assertEqual(getattr(cm.exception, "peer_id", ""), "peer-no-pin")
            self.assertEqual(getattr(cm.exception, "index", -1), 0)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_real_server_emits_no_fingerprint_action_on_load(self):
        """_load_peers_or_raise() catches PeerHasNoFingerprintError + emits
        federation_peer_invalid_no_fingerprint BEFORE re-raising."""
        if server_mod is None:
            self.skipTest("server_full.py not available")
        tmpdir = tempfile.mkdtemp(prefix="real-server-emit-")
        try:
            peers_path = Path(tmpdir) / "peers.yaml"
            _make_peers_yaml(
                [
                    {
                        "peer_id": "peer-no-pin-server",
                        "ca_pin_sha256": "e" * 64,
                        "not_valid_after": _utc_iso(60),
                        "not_valid_before": _utc_iso(-1),
                        "revoked": "false",
                    },
                ],
                peers_path,
            )

            # Build a minimal config + FederationServer; we only need
            # _load_peers_or_raise.
            class _FauxCfg:
                def __init__(self, peers_path: Path) -> None:
                    self.peers_path = peers_path
                    self.cert_file = Path("/dev/null")
                    self.key_file = Path("/dev/null")
                    self.ca_file = Path("/dev/null")
                    self.bind_host = "127.0.0.1"
                    self.bind_port = 0
                    self.enabled_sentinel = Path("/dev/null")
                    self.enabled_sentinel_asc = Path("/dev/null")
                    self.lan_enabled_sentinel = Path("/dev/null")
                    self.lan_enabled_sentinel_asc = Path("/dev/null")
                    self.signer_registry_path = None

            cfg = _FauxCfg(peers_path)
            # Stub the FederationServer-like surface needed by
            # _load_peers_or_raise: just .config + ._now.
            import datetime as _dt
            srv_cls = server_mod.FederationServer

            # Patch _safe_emit at the module level to record emits.
            emits: List[Tuple[str, Dict[str, Any]]] = []
            orig_safe_emit = server_mod._safe_emit

            def _recording_emit(action: str, **fields: Any) -> None:
                emits.append((action, dict(fields)))

            server_mod._safe_emit = _recording_emit
            try:
                # Construct a minimal instance shell — we do not call
                # serve_forever, only _load_peers_or_raise via the
                # unbound method.
                inst = srv_cls.__new__(srv_cls)
                inst.config = cfg
                inst._now = _dt.datetime(2026, 5, 20, tzinfo=_dt.timezone.utc)
                inst._httpd = None
                with self.assertRaises(server_mod.FederationStartError):
                    srv_cls._load_peers_or_raise(inst)
            finally:
                server_mod._safe_emit = orig_safe_emit

            actions = [a for (a, _) in emits]
            self.assertIn(
                "federation_peer_invalid_no_fingerprint", actions,
                "F-003 fix regression: expected "
                "federation_peer_invalid_no_fingerprint emit; got {0!r}".format(actions),
            )
            self.assertNotIn(
                "federation_connection_rejected", actions,
                "F-003 fix regression: no-pin row should NOT take the "
                "generic federation_connection_rejected path"
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    # ----- F-004: Wave D alias is wired -----

    def test_real_handler_exposes_resolve_peer_alias(self):
        """Wave D's expected `_resolve_peer` alias resolves to the same
        impl as `_lookup_peer_record` (Codex Wave-C P0 F-004)."""
        handler_cls = server_mod._FederationHandler
        self.assertTrue(
            hasattr(handler_cls, "_resolve_peer"),
            "_FederationHandler must expose _resolve_peer alias (Wave D contract)"
        )
        self.assertTrue(
            hasattr(handler_cls, "_lookup_peer_record"),
            "_FederationHandler must retain _lookup_peer_record (Wave C name)"
        )
        # Behavioural parity: both methods MUST return the same result
        # for the same fake handler state.
        tmpdir = tempfile.mkdtemp(prefix="real-disp-alias-")
        try:
            peers_path = Path(tmpdir) / "peers.yaml"
            _make_peers_yaml(
                [
                    {
                        "peer_id": "peer-alias-check",
                        "peer_id_spki_fingerprint": self.fixtures["spki_v1"],
                        "ca_pin_sha256": "e" * 64,
                        "not_valid_after": _utc_iso(60),
                        "not_valid_before": _utc_iso(-1),
                        "revoked": "false",
                    },
                ],
                peers_path,
            )
            peers = identity.load_peers(peers_path)
            peers_extra = {
                p.peer_id: {
                    "peer_id_spki_fingerprint": p.peer_id_spki_fingerprint,
                    "peer_id_cert_fingerprint": p.peer_id_cert_fingerprint,
                }
                for p in peers.values()
            }
            der_bytes = ssl.PEM_cert_to_DER_cert(
                self.fixtures["pem_v1"].decode("ascii")
            )
            fake_a = _FakeHandler(der_bytes, peers, peers_extra)
            fake_b = _FakeHandler(der_bytes, peers, peers_extra)
            # Attach the real _lookup_peer_record to the fake instances
            # so the alias (which calls self._lookup_peer_record()) can
            # reach it. This mirrors how the real handler inherits the
            # method from the class — the fake doesn't subclass the
            # real handler (to avoid pulling in the full http.server
            # machinery), so we wire the method on explicitly.
            import types as _types
            fake_a._lookup_peer_record = _types.MethodType(  # type: ignore[attr-defined]
                handler_cls._lookup_peer_record, fake_a,
            )
            fake_b._lookup_peer_record = _types.MethodType(  # type: ignore[attr-defined]
                handler_cls._lookup_peer_record, fake_b,
            )
            r_lookup = handler_cls._lookup_peer_record(fake_a)
            r_resolve = handler_cls._resolve_peer(fake_b)
            self.assertEqual(
                r_lookup.peer_id if r_lookup else None,
                r_resolve.peer_id if r_resolve else None,
                "_resolve_peer alias must be behaviourally identical to "
                "_lookup_peer_record"
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
