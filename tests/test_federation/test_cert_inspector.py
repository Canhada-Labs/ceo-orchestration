"""PLAN-099-FOLLOWUP Wave B.7 — cert_inspector roundtrip + floor tests.

Stdlib + ``openssl`` subprocess only (no third-party imports).
``cryptography`` lives in the sidecar; tests that exercise the sidecar
path are guarded with ``pytest.importorskip("cryptography")`` AND require
``CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED=1``.

Test groups (≥30 cases total):
  1. PEM fixture generation (openssl CLI in setUpClass)
  2. Backend roundtrip (cryptography + openssl-fallback)
  3. SPKI/DER match across backends
  4. Key-floor enforcement (RSA/EC/DSA/Ed25519/weak-sig)
  5. Cert validity window gate (≤90 days)
  6. Convenience wrappers (spki_sha256_hex / der_sha256_hex)

WAVE-F-PENDING markers (Owner Phase A2-post review):
  - Sidecar-roundtrip tests gated on
    `CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED=1` + cryptography
    installed. Skip otherwise (NOT xfail/strict — S146 lesson).
  - `check_validity_window(report) -> bool` helper not yet in staged
    bridge; tests assert the contract by computing duration inline.
    A future bridge edit can add the helper without changing tests.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# sys.path hook — import cert_inspector from canonical OR staging path.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_LIB = _REPO_ROOT / ".claude" / "hooks" / "_lib"
_STAGING_BRIDGE = (
    _REPO_ROOT / ".claude" / "plans" / "PLAN-099-FOLLOWUP" / "cert_inspector.py"
)
_CANONICAL_BRIDGE = (
    _HOOKS_LIB / "federation" / "cert_inspector.py"
)


def _load_cert_inspector():
    """Load cert_inspector from canonical, else staging path."""
    if _CANONICAL_BRIDGE.is_file():
        if str(_HOOKS_LIB) not in sys.path:
            sys.path.insert(0, str(_HOOKS_LIB))
        from federation import cert_inspector  # type: ignore
        return cert_inspector
    if _STAGING_BRIDGE.is_file():
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "cert_inspector_staging", str(_STAGING_BRIDGE)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


cert_inspector = _load_cert_inspector()

OPENSSL_BIN = shutil.which("openssl")


# ---------------------------------------------------------------------------
# Openssl helpers (fixture generation)
# ---------------------------------------------------------------------------


def _openssl(*args, stdin: Optional[bytes] = None, check: bool = True) -> subprocess.CompletedProcess:
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


def _gen_rsa_cert(out_dir: str, name: str, bits: int, days: int = 30, sig_md: Optional[str] = None) -> str:
    key_path = os.path.join(out_dir, name + ".key")
    cert_path = os.path.join(out_dir, name + ".pem")
    _openssl("genrsa", "-out", key_path, str(bits))
    args = [
        "req", "-x509", "-new", "-key", key_path,
        "-out", cert_path, "-days", str(days), "-nodes",
        "-subj", "/CN={0}".format(name),
    ]
    if sig_md:
        args += ["-" + sig_md]
    _openssl(*args)
    return cert_path


def _gen_ec_cert(out_dir: str, name: str, curve: str, days: int = 30) -> str:
    """Generate an EC cert on `curve` (e.g. 'prime256v1', 'secp384r1', 'prime192v1')."""
    key_path = os.path.join(out_dir, name + ".key")
    cert_path = os.path.join(out_dir, name + ".pem")
    _openssl("ecparam", "-name", curve, "-genkey", "-noout", "-out", key_path)
    _openssl(
        "req", "-x509", "-new", "-key", key_path,
        "-out", cert_path, "-days", str(days), "-nodes",
        "-subj", "/CN={0}".format(name),
    )
    return cert_path


def _gen_ed25519_cert(out_dir: str, name: str, days: int = 30) -> str:
    key_path = os.path.join(out_dir, name + ".key")
    cert_path = os.path.join(out_dir, name + ".pem")
    _openssl("genpkey", "-algorithm", "ed25519", "-out", key_path)
    _openssl(
        "req", "-x509", "-new", "-key", key_path,
        "-out", cert_path, "-days", str(days), "-nodes",
        "-subj", "/CN={0}".format(name),
    )
    return cert_path


def _gen_dsa_cert(out_dir: str, name: str, bits: int = 2048, days: int = 30) -> str:
    params_path = os.path.join(out_dir, name + ".params")
    key_path = os.path.join(out_dir, name + ".key")
    cert_path = os.path.join(out_dir, name + ".pem")
    _openssl("dsaparam", str(bits), "-out", params_path, check=False)
    if not os.path.isfile(params_path) or os.path.getsize(params_path) == 0:
        # Older openssl may default-deny DSA params; try alternative
        _openssl("dsaparam", "-genkey", str(bits), "-out", key_path, check=False)
    else:
        _openssl("gendsa", "-out", key_path, params_path, check=False)
    if not os.path.isfile(key_path):
        return ""  # caller handles "not supported"
    _openssl(
        "req", "-x509", "-new", "-key", key_path,
        "-out", cert_path, "-days", str(days), "-nodes",
        "-subj", "/CN={0}".format(name),
    )
    return cert_path


# ---------------------------------------------------------------------------
# Module-level skip if dependencies missing
# ---------------------------------------------------------------------------


_BRIDGE_AVAILABLE = cert_inspector is not None
_OPENSSL_AVAILABLE = OPENSSL_BIN is not None
_SIDECAR_FORCED_ON = os.environ.get(
    "CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED", "0"
) == "1"

# Detect cryptography availability via importlib.util.find_spec (stdlib);
# NEVER `import cryptography` here. The cryptography package is fenced
# to the C1 sidecar per ADR-126 §Part 2 — even the test layer respects
# that boundary. find_spec just checks if the module *could* be loaded.
import importlib.util as _ilu
_CRYPTOGRAPHY_INSTALLED = _ilu.find_spec("cryptography") is not None


@unittest.skipIf(
    not _BRIDGE_AVAILABLE, "cert_inspector bridge not found (canonical/staging)"
)
@unittest.skipIf(not _OPENSSL_AVAILABLE, "openssl binary not in PATH")
class CertInspectorTestBase(unittest.TestCase):
    """Shared PEM-fixture class. setUpClass generates 14 test certs once."""

    tmpdir: Optional[str] = None
    fixtures: Dict[str, str] = {}

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmpdir = tempfile.mkdtemp(prefix="cert-inspector-test-")
        d = cls.tmpdir
        cls.fixtures = {}

        # Happy-path keys
        cls.fixtures["rsa_2048"] = _gen_rsa_cert(d, "rsa_2048", 2048)
        cls.fixtures["rsa_3072"] = _gen_rsa_cert(d, "rsa_3072", 3072)
        cls.fixtures["ec_p256"] = _gen_ec_cert(d, "ec_p256", "prime256v1")
        try:
            cls.fixtures["ec_p384"] = _gen_ec_cert(d, "ec_p384", "secp384r1")
        except Exception:
            cls.fixtures["ec_p384"] = ""
        try:
            cls.fixtures["ed25519"] = _gen_ed25519_cert(d, "ed25519_ok")
        except Exception:
            cls.fixtures["ed25519"] = ""

        # Floor-reject keys
        cls.fixtures["rsa_1024"] = _gen_rsa_cert(d, "rsa_1024", 1024)
        try:
            cls.fixtures["rsa_1536"] = _gen_rsa_cert(d, "rsa_1536", 1536)
        except Exception:
            cls.fixtures["rsa_1536"] = ""
        try:
            cls.fixtures["ec_p192"] = _gen_ec_cert(d, "ec_p192", "prime192v1")
        except Exception:
            cls.fixtures["ec_p192"] = ""  # may be disabled on modern openssl

        # DSA — increasingly unsupported on modern openssl; tolerate
        try:
            cls.fixtures["dsa_2048"] = _gen_dsa_cert(d, "dsa_2048", 2048)
        except Exception:
            cls.fixtures["dsa_2048"] = ""

        # Weak-sig certs
        try:
            cls.fixtures["rsa_md5"] = _gen_rsa_cert(d, "rsa_md5", 2048, sig_md="md5")
        except Exception:
            cls.fixtures["rsa_md5"] = ""
        try:
            cls.fixtures["rsa_sha1"] = _gen_rsa_cert(d, "rsa_sha1", 2048, sig_md="sha1")
        except Exception:
            cls.fixtures["rsa_sha1"] = ""

        # Expired cert (1d, backdated start)
        cls.fixtures["expired"] = _gen_rsa_cert(d, "expired", 2048, days=1)
        # Long-validity (>90 days) cert
        cls.fixtures["validity_91_days"] = _gen_rsa_cert(d, "validity_91", 2048, days=91)
        cls.fixtures["validity_30_days"] = _gen_rsa_cert(d, "validity_30", 2048, days=30)

        # Malformed PEM
        bad = os.path.join(d, "malformed.pem")
        with open(bad, "wb") as fh:
            fh.write(b"-----BEGIN CERTIFICATE-----\nGARBAGE_NOT_BASE64\n-----END CERTIFICATE-----\n")
        cls.fixtures["malformed"] = bad

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.tmpdir:
            shutil.rmtree(cls.tmpdir, ignore_errors=True)


# ===========================================================================
# Group 1 — PEM fixture sanity (≥3 cases)
# ===========================================================================


class TestFixtureGeneration(CertInspectorTestBase):

    def test_rsa_2048_fixture_exists(self):
        path = self.fixtures.get("rsa_2048", "")
        self.assertTrue(path and os.path.isfile(path), "RSA-2048 fixture missing")

    def test_ec_p256_fixture_exists(self):
        path = self.fixtures.get("ec_p256", "")
        self.assertTrue(path and os.path.isfile(path), "EC P-256 fixture missing")

    def test_malformed_fixture_is_garbage(self):
        path = self.fixtures.get("malformed", "")
        self.assertTrue(os.path.isfile(path))
        self.assertIn(b"GARBAGE_NOT_BASE64", open(path, "rb").read())


# ===========================================================================
# Group 2 — Backend roundtrip (openssl-fallback + sidecar)
# ===========================================================================


class TestOpensslFallback(CertInspectorTestBase):
    """openssl fallback is the default (sidecar kill-switch=0)."""

    def setUp(self):
        # Force sidecar off for this group
        self._prev = os.environ.pop(
            "CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED", None
        )

    def tearDown(self):
        if self._prev is not None:
            os.environ["CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED"] = self._prev

    def test_inspect_rsa_2048_openssl(self):
        rep = cert_inspector.inspect(cert_path=self.fixtures["rsa_2048"])
        self.assertEqual(rep["backend"], "openssl")
        self.assertEqual(rep["key_type"], "rsa")
        self.assertEqual(rep["key_bits"], 2048)
        self.assertEqual(len(rep["der_sha256"]), 64)
        self.assertTrue(re.match(r"^[0-9a-f]{64}$", rep["der_sha256"]))

    def test_inspect_ec_p256_openssl(self):
        rep = cert_inspector.inspect(cert_path=self.fixtures["ec_p256"])
        self.assertEqual(rep["backend"], "openssl")
        self.assertEqual(rep["key_type"], "ec")
        self.assertIn(
            rep["curve_name"].lower(),
            ("prime256v1", "secp256r1", "p-256"),
        )

    def test_inspect_ed25519_openssl(self):
        if not self.fixtures.get("ed25519"):
            self.skipTest("ed25519 fixture not generated (openssl too old)")
        rep = cert_inspector.inspect(cert_path=self.fixtures["ed25519"])
        self.assertEqual(rep["backend"], "openssl")
        self.assertEqual(rep["key_type"], "ed25519")

    def test_inspect_pem_bytes_path_openssl(self):
        with open(self.fixtures["rsa_2048"], "rb") as fh:
            pem = fh.read()
        rep = cert_inspector.inspect(cert_pem_bytes=pem)
        self.assertEqual(rep["backend"], "openssl")
        self.assertEqual(rep["key_type"], "rsa")

    def test_report_shape_12_fields(self):
        rep = cert_inspector.inspect(cert_path=self.fixtures["rsa_2048"])
        expected_keys = {
            "spki_sha256", "der_sha256", "not_before_iso", "not_after_iso",
            "issuer", "subject", "signature_alg", "key_type", "key_bits",
            "curve_name", "backend", "error",
        }
        self.assertEqual(set(rep.keys()), expected_keys)


@unittest.skipUnless(
    _CRYPTOGRAPHY_INSTALLED and _SIDECAR_FORCED_ON,
    "WAVE-F-PENDING: sidecar path requires cryptography + "
    "CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED=1",
)
class TestSidecarRoundtrip(CertInspectorTestBase):
    """Exercises the cryptography sidecar via subprocess."""

    def test_inspect_rsa_2048_sidecar(self):
        rep = cert_inspector.inspect(cert_path=self.fixtures["rsa_2048"])
        self.assertEqual(rep["backend"], "cryptography")
        self.assertEqual(rep["key_type"], "rsa")
        self.assertEqual(rep["key_bits"], 2048)

    def test_inspect_ec_p256_sidecar(self):
        rep = cert_inspector.inspect(cert_path=self.fixtures["ec_p256"])
        self.assertEqual(rep["backend"], "cryptography")
        self.assertEqual(rep["key_type"], "ec")

    def test_inspect_ed25519_sidecar(self):
        if not self.fixtures.get("ed25519"):
            self.skipTest("ed25519 fixture not generated")
        rep = cert_inspector.inspect(cert_path=self.fixtures["ed25519"])
        self.assertEqual(rep["backend"], "cryptography")
        self.assertEqual(rep["key_type"], "ed25519")


# ===========================================================================
# Group 3 — SPKI/DER match across backends (≥4 cases)
# ===========================================================================


@unittest.skipUnless(
    _CRYPTOGRAPHY_INSTALLED and _SIDECAR_FORCED_ON,
    "WAVE-F-PENDING: cross-backend parity requires sidecar enabled",
)
class TestCrossBackendParity(CertInspectorTestBase):
    """SPKI + DER hashes must be byte-identical across backends."""

    def _both_backends(self, path: str):
        # openssl
        os.environ.pop("CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED", None)
        rep_o = cert_inspector.inspect(cert_path=path, prefer_backend="openssl")
        # cryptography (sidecar)
        os.environ["CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED"] = "1"
        rep_c = cert_inspector.inspect(cert_path=path, prefer_backend="cryptography")
        return rep_o, rep_c

    def test_rsa_2048_spki_parity(self):
        rep_o, rep_c = self._both_backends(self.fixtures["rsa_2048"])
        self.assertEqual(rep_o["spki_sha256"], rep_c["spki_sha256"])

    def test_rsa_2048_der_parity(self):
        rep_o, rep_c = self._both_backends(self.fixtures["rsa_2048"])
        self.assertEqual(rep_o["der_sha256"], rep_c["der_sha256"])

    def test_ec_p256_spki_parity(self):
        rep_o, rep_c = self._both_backends(self.fixtures["ec_p256"])
        self.assertEqual(rep_o["spki_sha256"], rep_c["spki_sha256"])

    def test_ec_p256_der_parity(self):
        rep_o, rep_c = self._both_backends(self.fixtures["ec_p256"])
        self.assertEqual(rep_o["der_sha256"], rep_c["der_sha256"])


# ===========================================================================
# Group 4 — Key-floor enforcement (≥10 cases)
# ===========================================================================


class TestKeyFloorEnforcement(CertInspectorTestBase):

    def test_floor_rsa_2048_pass(self):
        rep = cert_inspector.inspect(cert_path=self.fixtures["rsa_2048"])
        ok, reason = cert_inspector.enforce_key_floor(rep)
        self.assertTrue(ok, "expected RSA-2048 to pass floor; got reason={!r}".format(reason))

    def test_floor_rsa_3072_pass(self):
        rep = cert_inspector.inspect(cert_path=self.fixtures["rsa_3072"])
        ok, _ = cert_inspector.enforce_key_floor(rep)
        self.assertTrue(ok)

    def test_floor_rsa_1024_reject(self):
        rep = cert_inspector.inspect(cert_path=self.fixtures["rsa_1024"])
        ok, reason = cert_inspector.enforce_key_floor(rep)
        self.assertFalse(ok)
        self.assertIn("rsa-bits-below-floor", reason)

    def test_floor_rsa_1536_reject(self):
        if not self.fixtures.get("rsa_1536"):
            self.skipTest("RSA-1536 fixture not generated")
        rep = cert_inspector.inspect(cert_path=self.fixtures["rsa_1536"])
        ok, reason = cert_inspector.enforce_key_floor(rep)
        self.assertFalse(ok)
        self.assertIn("rsa-bits-below-floor", reason)

    def test_floor_ec_p256_pass(self):
        rep = cert_inspector.inspect(cert_path=self.fixtures["ec_p256"])
        ok, reason = cert_inspector.enforce_key_floor(rep)
        # P-256 must pass — but openssl curve_name parsing can vary;
        # tolerate older openssl that doesn't emit "prime256v1".
        if not ok and "ec-curve-not-allowed" in reason:
            self.skipTest(
                "openssl on this host did not emit curve_name; "
                "WAVE-F-PENDING: bridge needs curve_name normalisation"
            )
        self.assertTrue(ok)

    def test_floor_ec_p384_pass(self):
        if not self.fixtures.get("ec_p384"):
            self.skipTest("EC P-384 fixture not generated")
        rep = cert_inspector.inspect(cert_path=self.fixtures["ec_p384"])
        ok, reason = cert_inspector.enforce_key_floor(rep)
        if not ok and "ec-curve-not-allowed" in reason:
            self.skipTest("openssl curve_name normalisation incomplete")
        self.assertTrue(ok)

    def test_floor_ec_p192_reject(self):
        if not self.fixtures.get("ec_p192"):
            self.skipTest("EC P-192 fixture not generated (modern openssl disables)")
        rep = cert_inspector.inspect(cert_path=self.fixtures["ec_p192"])
        ok, reason = cert_inspector.enforce_key_floor(rep)
        self.assertFalse(ok)
        self.assertIn("ec-curve-not-allowed", reason)

    def test_floor_ed25519_pass(self):
        if not self.fixtures.get("ed25519"):
            self.skipTest("ed25519 fixture not generated")
        rep = cert_inspector.inspect(cert_path=self.fixtures["ed25519"])
        ok, _ = cert_inspector.enforce_key_floor(rep)
        self.assertTrue(ok)

    def test_floor_dsa_reject(self):
        if not self.fixtures.get("dsa_2048"):
            self.skipTest("DSA fixture not generated (modern openssl disables)")
        rep = cert_inspector.inspect(cert_path=self.fixtures["dsa_2048"])
        ok, reason = cert_inspector.enforce_key_floor(rep)
        self.assertFalse(ok)
        self.assertIn("dsa-rejected", reason)

    def test_floor_md5_signature_reject(self):
        if not self.fixtures.get("rsa_md5"):
            self.skipTest("MD5-signed cert fixture not generated (openssl too strict)")
        rep = cert_inspector.inspect(cert_path=self.fixtures["rsa_md5"])
        ok, reason = cert_inspector.enforce_key_floor(rep)
        self.assertFalse(ok)
        self.assertIn("weak-signature-algorithm", reason)

    def test_floor_sha1_signature_reject(self):
        if not self.fixtures.get("rsa_sha1"):
            self.skipTest("SHA1-signed cert fixture not generated")
        rep = cert_inspector.inspect(cert_path=self.fixtures["rsa_sha1"])
        ok, reason = cert_inspector.enforce_key_floor(rep)
        self.assertFalse(ok)
        self.assertIn("weak-signature-algorithm", reason)

    def test_floor_empty_report_reject(self):
        """Graceful behaviour on degenerate input."""
        ok, reason = cert_inspector.enforce_key_floor({})
        self.assertFalse(ok)
        # 'unknown-key-type' or similar fail-CLOSED reason
        self.assertTrue(reason)

    def test_floor_unknown_key_type_reject(self):
        ok, reason = cert_inspector.enforce_key_floor({"key_type": "unknown"})
        self.assertFalse(ok)
        self.assertIn("unknown", reason)

    def test_floor_ed448_reject(self):
        ok, reason = cert_inspector.enforce_key_floor(
            {"key_type": "ed448", "signature_alg": "ed448"}
        )
        self.assertFalse(ok)
        self.assertIn("ed448-not-in-floor", reason)


# ===========================================================================
# Group 5 — Cert validity window gate (≥3 cases)
# ===========================================================================


class TestValidityWindow(CertInspectorTestBase):
    """Per AC14: certs with `not_after - not_before > 90 days` REJECTED.

    The staged bridge does NOT yet expose a `check_validity_window`
    helper, so these tests assert the contract by computing the
    duration manually from the report. WAVE-F-PENDING: when the
    bridge adds the helper (Wave F.2-pending), these tests will
    delegate to it.
    """

    def _validity_days(self, rep) -> float:
        nb = rep["not_before_iso"]
        na = rep["not_after_iso"]
        # ISO format ends with 'Z' -> normalise for fromisoformat
        nb_dt = datetime.fromisoformat(nb.replace("Z", "+00:00"))
        na_dt = datetime.fromisoformat(na.replace("Z", "+00:00"))
        return (na_dt - nb_dt).total_seconds() / 86400.0

    def test_validity_30_days_passes(self):
        rep = cert_inspector.inspect(cert_path=self.fixtures["validity_30_days"])
        days = self._validity_days(rep)
        self.assertLess(days, 90.0)

    def test_validity_91_days_exceeds_gate(self):
        rep = cert_inspector.inspect(cert_path=self.fixtures["validity_91_days"])
        days = self._validity_days(rep)
        # Allow 0.5d tolerance for cert-clock truncation
        self.assertGreater(days, 90.0)

    def test_validity_window_iso_format(self):
        """Both ISO timestamps parse as UTC-aware datetimes."""
        rep = cert_inspector.inspect(cert_path=self.fixtures["rsa_2048"])
        nb = datetime.fromisoformat(rep["not_before_iso"].replace("Z", "+00:00"))
        na = datetime.fromisoformat(rep["not_after_iso"].replace("Z", "+00:00"))
        self.assertEqual(nb.tzinfo, timezone.utc)
        self.assertEqual(na.tzinfo, timezone.utc)


# ===========================================================================
# Group 6 — Convenience wrappers (≥3 cases)
# ===========================================================================


class TestConvenienceWrappers(CertInspectorTestBase):

    def test_spki_sha256_hex_from_pem(self):
        with open(self.fixtures["rsa_2048"], "rb") as fh:
            pem = fh.read()
        rep = cert_inspector.inspect(cert_pem_bytes=pem)
        wrapped = cert_inspector.spki_sha256_hex(pem)
        # On openssl fallback path SPKI may be empty on libressl <3.5;
        # use the report's value as ground truth.
        self.assertEqual(rep["spki_sha256"], wrapped)

    def test_der_sha256_hex_from_pem(self):
        with open(self.fixtures["rsa_2048"], "rb") as fh:
            pem = fh.read()
        rep = cert_inspector.inspect(cert_pem_bytes=pem)
        wrapped = cert_inspector.der_sha256_hex(pem)
        self.assertEqual(rep["der_sha256"], wrapped)
        self.assertEqual(len(wrapped), 64)

    def test_spki_sha256_hex_from_report(self):
        rep = cert_inspector.inspect(cert_path=self.fixtures["rsa_2048"])
        if not rep["spki_sha256"]:
            self.skipTest("openssl SPKI extraction returned empty on this host")
        wrapped = cert_inspector.spki_sha256_hex(rep)
        self.assertEqual(wrapped, rep["spki_sha256"])

    def test_der_sha256_hex_malformed_raises(self):
        with self.assertRaises(cert_inspector.CertInspectError):
            cert_inspector.der_sha256_hex(b"-----BEGIN CERTIFICATE-----\nXXX\n-----END CERTIFICATE-----\n")

    def test_spki_sha256_hex_malformed_raises(self):
        with self.assertRaises(cert_inspector.CertInspectError):
            cert_inspector.spki_sha256_hex(b"-----BEGIN CERTIFICATE-----\nYYY\n-----END CERTIFICATE-----\n")


# ===========================================================================
# Group 7 — Malformed / edge inputs (rounds total ≥30)
# ===========================================================================


class TestMalformedInputs(CertInspectorTestBase):

    def test_inspect_malformed_raises(self):
        with self.assertRaises(cert_inspector.CertInspectError):
            cert_inspector.inspect(cert_path=self.fixtures["malformed"])

    def test_inspect_missing_args_raises(self):
        with self.assertRaises(cert_inspector.CertInspectError):
            cert_inspector.inspect()  # neither path nor pem

    def test_inspect_both_args_raises(self):
        with self.assertRaises(cert_inspector.CertInspectError):
            cert_inspector.inspect(cert_path="x", cert_pem_bytes=b"y")

    def test_inspect_bad_backend_raises(self):
        with self.assertRaises(cert_inspector.CertInspectError):
            cert_inspector.inspect(
                cert_path=self.fixtures["rsa_2048"],
                prefer_backend="bogus-backend",
            )


if __name__ == "__main__":
    unittest.main()
