"""C1 crypto sidecar — cryptography-importing cert inspector implementation.

**STAGING NOTE (NOT PART OF MODULE BODY):** This file is the
PLAN-099-FOLLOWUP Wave B deliverable staged at
``.claude/plans/PLAN-099-FOLLOWUP/sidecar_code/c1-crypto/cryptography-mvp/sidecar_code/cert_inspector.py``
because the parent agent's canonical-edit guard refused a direct
write to ``.claude/sidecars/c1-crypto/cryptography-mvp/sidecar_code/``
(canonical sidecar tree per ADR-126 §Part 2). Owner ``git mv``s this
file at Wave A ceremony commit under
``CEO_KERNEL_OVERRIDE=PLAN-099-FOLLOWUP-WAVE-A-CRYPTO-SIDECAR-LAND``
+ ``CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT``, then deletes this staging
copy. Frontmatter + body are final-form. Strip this paragraph at
move time.

**Final landing**:
``.claude/sidecars/c1-crypto/cryptography-mvp/sidecar_code/cert_inspector.py``.

ADR-126 §Part 2 mandates that all non-stdlib code live under the
``sidecar_code/`` directory of a registered sidecar tree. This file
is the SOLE legitimate importer of the ``cryptography`` package in
the framework. Core (``.claude/hooks/``, ``.claude/scripts/``,
``.claude/policies/``, ``SPEC/``, ``.github/workflows/``) remains
stdlib-only per ADR-002 / ADR-126.

The kernel-side bridge at ``.claude/hooks/_lib/federation/cert_inspector.py``
(STDLIB-ONLY) subprocess-invokes this script when the C1 crypto
sidecar is enabled. The boundary is enforced by:

- ``boundary_test.py`` for cryptography-mvp sidecar (AST scan
  asserts ``cryptography`` imported ONLY from ``sidecar_code/``).
- ``check-stdlib-only.py`` extended (does NOT flag this file because
  it lives under ``.claude/sidecars/`` not ``.claude/hooks/``).

Trust boundary: this module is invoked via subprocess. Input is a
single cert path (positional CLI arg) OR PEM bytes via stdin. Output
is a JSON report on stdout (one line, then exit 0); errors are
written to stderr with exit code != 0.

Primary deliverables:

- :func:`inspect` — returns a normalised report ``dict`` with both
  ``spki_sha256`` AND ``der_sha256`` populated during the 90-day SPKI
  migration window (per ADR-135-AMEND-1 §migration).
- :func:`enforce_key_floor` — rejects RSA<2048, EC non-(P-256/P-384/
  Ed25519), DSA always, weak signature algorithms.

API surface is INTENTIONALLY narrow: no class hierarchy, no global
state, no plugin model. Every call re-parses the PEM input.

Hard-dependency pin documented in
``.claude/sidecars/c1-crypto/cryptography-mvp/manifest.json``:

    cryptography>=42.0,<44.0

Pin rationale: 42.0 introduces stable ``rfc7958`` PEM bundle support;
44.0 (unreleased at draft time) is the first major-version bound we
gate before adoption.

CLI usage (subprocess-invocation contract from the bridge):

    python3 cert_inspector.py <cert_path>           # JSON report on stdout
    python3 cert_inspector.py -                     # read PEM from stdin
    python3 cert_inspector.py --self-test           # smoke roundtrip

Exit codes:
    0 = report on stdout
    2 = openssl binary missing (self-test fallback path)
    3 = cert parse failure
    4 = backend mismatch (self-test only)
    5 = key floor failure (self-test only)
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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

__all__ = [
    "inspect",
    "enforce_key_floor",
    "spki_sha256_hex",
    "der_sha256_hex",
    "KeyFloorError",
    "CertInspectError",
    "RSA_MIN_BITS",
    "EC_ALLOWED_CURVES",
    "DSA_ALLOWED",
]

# Minimum acceptable RSA key size in bits. Anything below MUST be
# rejected at peer-add. ADR-135-AMEND-1 §RBAC matrix references this
# constant by name; do not change the literal without an ADR amend.
RSA_MIN_BITS = 2048

# Allowed EC curve OIDs / human-readable names.
# - P-256 = secp256r1 (NIST) — RFC 8422 baseline
# - P-384 = secp384r1
# - Ed25519 = RFC 8032 (treated as "EC-like" by the cryptography API
#   but is technically EdDSA, not ECDSA; we normalize to a single set
#   for the floor check)
#
# Ed448 is NOT in the allowed set (Codex Loop A P2 finding) —
# amendment floor commits only to RSA-2048+ / EC P-256 / P-384 /
# Ed25519. Future expansion via ADR-129-AMEND-2.
EC_ALLOWED_CURVES = frozenset({"secp256r1", "secp384r1", "ed25519"})

# DSA is rejected outright. The constant exists for symmetry with the
# RSA/EC constants and to make ``enforce_key_floor`` declarations
# self-documenting.
DSA_ALLOWED = False

# Weak signature algorithm OIDs / friendly names. Matched against
# ``cert.signature_algorithm_oid.dotted_string`` AND friendly name
# from ``cert.signature_hash_algorithm.name`` (lower-cased).
_WEAK_SIG_ALGORITHMS = frozenset(
    {
        "md5",
        "sha1",
        # MD5/SHA1-based RSA OIDs (legacy interoperability hazards)
        "1.2.840.113549.1.1.4",  # md5WithRSAEncryption
        "1.2.840.113549.1.1.5",  # sha1WithRSAEncryption
        "1.2.840.10040.4.3",     # dsa-with-sha1
        "1.2.840.10045.4.1",     # ecdsa-with-sha1
    }
)

# Try cryptography import; if unavailable, the openssl subprocess
# fallback is used. The boolean is module-level so that callers can
# branch on capability if they want (e.g., refuse to lift the
# key-floor waiver unless cryptography is present).
try:
    from cryptography import x509  # type: ignore[import-not-found]
    from cryptography.hazmat.primitives import hashes, serialization  # type: ignore[import-not-found]
    from cryptography.hazmat.primitives.asymmetric import (  # type: ignore[import-not-found]
        dsa,
        ec,
        ed25519,
        rsa,
    )

    _CRYPTOGRAPHY_AVAILABLE = True
except Exception:  # pragma: no cover — sidecar-not-installed path
    _CRYPTOGRAPHY_AVAILABLE = False


class CertInspectError(Exception):
    """Raised when a cert cannot be parsed by either backend.

    Wraps the underlying parser exception. Callers MUST fail-CLOSED on
    this (per ADR-129 §Part 8 — "failure modes that MUST trigger
    fail-CLOSED").
    """


class KeyFloorError(Exception):
    """Raised by :func:`enforce_key_floor` when the floor is not met.

    Carries the rejection reason as ``str(exc)``; callers SHOULD emit
    ``federation_key_floor_rejected`` with the reason verbatim (subject
    to the redaction pipeline — no PEM bytes leak through).
    """


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def inspect(
    cert_path: Optional[str] = None,
    cert_pem_bytes: Optional[bytes] = None,
    prefer_backend: str = "auto",
) -> Dict[str, Any]:
    """Inspect a single X.509 cert.

    Exactly ONE of ``cert_path`` or ``cert_pem_bytes`` must be set.

    :param prefer_backend: ``"auto"`` (default) tries cryptography first,
        falls back to openssl. ``"cryptography"`` requires the package;
        ``"openssl"`` forces the subprocess path even when cryptography
        is available (used by the boundary tests to exercise both
        codepaths).

    Returns a dict shaped per ADR-135-AMEND-1 §Cert inspection contract:

        {
            "spki_sha256": "<64-hex>",
            "der_sha256":  "<64-hex>",
            "not_before_iso": "YYYY-MM-DDTHH:MM:SSZ",
            "not_after_iso":  "YYYY-MM-DDTHH:MM:SSZ",
            "issuer":  "RFC 4514 Distinguished Name string",
            "subject": "RFC 4514 Distinguished Name string",
            "signature_alg": "ecdsa-with-sha256" | "rsassa-pss" | ...,
            "key_type": "rsa" | "ec" | "ed25519" | "dsa" | "unknown",
            "key_bits": int (RSA only; 0 for non-RSA),
            "curve_name": "secp256r1" | "secp384r1" | "ed25519" | "" (non-EC),
            "backend": "cryptography" | "openssl",
            "error": Optional[str],   # populated only on partial parse
        }

    Failure semantics: raises :class:`CertInspectError` if neither
    backend succeeds. Partial parse (e.g., openssl path missing SPKI
    extraction) populates ``error`` and the missing fields are empty
    strings; caller MUST check ``error`` before consuming the report.
    """
    if (cert_path is None) == (cert_pem_bytes is None):
        raise CertInspectError(
            "inspect(): exactly one of cert_path/cert_pem_bytes required"
        )
    if cert_path is not None:
        # Defensive read — keep IO bounded; certs are <16 KB.
        try:
            with open(cert_path, "rb") as fh:
                cert_pem_bytes = fh.read(64 * 1024)
        except OSError as exc:
            raise CertInspectError(
                "inspect(): cannot read cert_path: %s" % exc
            ) from exc

    assert cert_pem_bytes is not None  # nosec — guarded above

    if prefer_backend not in ("auto", "cryptography", "openssl"):
        raise CertInspectError(
            "inspect(): prefer_backend must be auto|cryptography|openssl"
        )

    last_err: Optional[Exception] = None
    if prefer_backend in ("auto", "cryptography") and _CRYPTOGRAPHY_AVAILABLE:
        try:
            return _inspect_via_cryptography(cert_pem_bytes)
        except Exception as exc:  # pragma: no cover — fallback path
            last_err = exc
            if prefer_backend == "cryptography":
                raise CertInspectError(
                    "inspect(): cryptography backend failed: %s" % exc
                ) from exc

    # openssl fallback OR forced-openssl
    if prefer_backend in ("auto", "openssl"):
        try:
            return _inspect_via_openssl(cert_pem_bytes)
        except Exception as exc:
            raise CertInspectError(
                "inspect(): openssl backend failed: %s (prior err: %s)"
                % (exc, last_err)
            ) from exc

    # If we land here, cryptography was demanded but absent.
    raise CertInspectError(
        "inspect(): prefer_backend=cryptography but package not importable"
    )


def enforce_key_floor(report: Dict[str, Any]) -> Tuple[bool, str]:
    """Enforce per-cert key floor + signature algorithm floor.

    Returns ``(ok, reason)``. ``reason`` is a short kebab-case slug on
    rejection (suitable for audit ``reason`` field); empty string on
    success.

    Floor rules (locked at this version; changes require ADR-129
    amendment):

    1. RSA  → ``key_bits`` must be ≥ :data:`RSA_MIN_BITS` (2048).
    2. EC   → ``curve_name`` must be in :data:`EC_ALLOWED_CURVES`.
    3. Ed25519 → always allowed (treated as EC-class).
    4. DSA  → REJECTED.
    5. unknown → REJECTED (fail-CLOSED on unrecognised key type).
    6. Signature algorithm — MD5/SHA1-based algorithms REJECTED.

    Note: Ed448 is NOT permitted by the floor (Codex Loop A P2
    finding). The amendment floor commits only to P-256/P-384/
    Ed25519; future expansion to Ed448 requires ADR-129-AMEND-2.

    Implementation notes:

    - This function does NOT touch the network, the filesystem, or any
      audit emit. Pure function.
    - Callers (e.g. ``server.py``) wrap with the appropriate
      :func:`audit_emit.emit_federation_key_floor_rejected` on the
      False branch.
    """
    key_type = (report.get("key_type") or "").lower()
    if key_type == "dsa":
        return (False, "dsa-rejected")
    if key_type == "unknown" or not key_type:
        return (False, "unknown-key-type")
    if key_type == "rsa":
        bits = int(report.get("key_bits") or 0)
        if bits < RSA_MIN_BITS:
            return (False, "rsa-bits-below-floor:%d<%d" % (bits, RSA_MIN_BITS))
    elif key_type in ("ec", "ed25519"):
        curve = (report.get("curve_name") or "").lower()
        if key_type == "ec" and curve not in EC_ALLOWED_CURVES:
            return (False, "ec-curve-not-allowed:%s" % (curve or "missing"))
        # ed25519 passes through; curve_name MAY be empty.
    elif key_type == "ed448":
        # Ed448 NOT permitted by floor (see docstring note).
        return (False, "ed448-not-in-floor")
    else:
        # New key type added in some future cryptography release we
        # haven't reviewed. Fail-CLOSED.
        return (False, "unsupported-key-type:%s" % key_type)

    sig_alg = (report.get("signature_alg") or "").lower()
    for weak in _WEAK_SIG_ALGORITHMS:
        if weak in sig_alg:
            return (False, "weak-signature-algorithm:%s" % sig_alg)

    return (True, "")


def spki_sha256_hex(report_or_pem: Union[Dict[str, Any], bytes, str]) -> str:
    """Return the SPKI SHA-256 (rotation-survives the cert itself).

    Accepts either a pre-computed report (dict) OR raw PEM bytes/str.
    Provided as a convenience so call sites that only need the pin
    don't have to consume the full report dict.
    """
    if isinstance(report_or_pem, dict):
        spki = report_or_pem.get("spki_sha256") or ""
        if not isinstance(spki, str) or len(spki) != 64:
            raise CertInspectError(
                "spki_sha256_hex(): report missing or malformed spki_sha256"
            )
        return spki
    if isinstance(report_or_pem, str):
        report_or_pem = report_or_pem.encode("ascii", errors="replace")
    rep = inspect(cert_pem_bytes=report_or_pem)
    return rep["spki_sha256"]


def der_sha256_hex(report_or_pem: Union[Dict[str, Any], bytes, str]) -> str:
    """Return the full-cert DER SHA-256 (legacy pin used by PLAN-099 MVP).

    Same shape as :func:`spki_sha256_hex`. During the 90-day SPKI
    migration window, both pins are emitted side-by-side; servers
    accept either; ADR-135-AMEND-1 §migration documents the soak.
    """
    if isinstance(report_or_pem, dict):
        der = report_or_pem.get("der_sha256") or ""
        if not isinstance(der, str) or len(der) != 64:
            raise CertInspectError(
                "der_sha256_hex(): report missing or malformed der_sha256"
            )
        return der
    if isinstance(report_or_pem, str):
        report_or_pem = report_or_pem.encode("ascii", errors="replace")
    rep = inspect(cert_pem_bytes=report_or_pem)
    return rep["der_sha256"]


# ---------------------------------------------------------------------------
# Backend: cryptography
# ---------------------------------------------------------------------------


def _inspect_via_cryptography(cert_pem_bytes: bytes) -> Dict[str, Any]:
    """cryptography-backed parser (preferred when sidecar installed)."""
    cert = x509.load_pem_x509_certificate(cert_pem_bytes)

    # SPKI = SubjectPublicKeyInfo DER → SHA-256
    pub = cert.public_key()
    spki_der = pub.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    spki_sha256 = hashlib.sha256(spki_der).hexdigest()

    # Full-cert DER (legacy pin per PLAN-099 MVP)
    der_full = cert.public_bytes(encoding=serialization.Encoding.DER)
    der_sha256 = hashlib.sha256(der_full).hexdigest()

    # Validity window
    try:
        # cryptography ≥42 prefers _utc accessors; older 41.x falls back.
        not_before = cert.not_valid_before_utc.replace(microsecond=0).isoformat()
        not_after = cert.not_valid_after_utc.replace(microsecond=0).isoformat()
    except AttributeError:  # pragma: no cover — cryptography <42 path
        not_before = cert.not_valid_before.replace(
            tzinfo=timezone.utc, microsecond=0
        ).isoformat()
        not_after = cert.not_valid_after.replace(
            tzinfo=timezone.utc, microsecond=0
        ).isoformat()
    # Normalise to ...Z form (drop +00:00) for audit-log consistency.
    not_before = _to_z(not_before)
    not_after = _to_z(not_after)

    issuer = cert.issuer.rfc4514_string()
    subject = cert.subject.rfc4514_string()

    # signature algorithm — prefer the OID short name, fall back to dotted.
    try:
        sig_alg = cert.signature_hash_algorithm.name.lower()  # type: ignore[union-attr]
    except (AttributeError, TypeError):
        sig_alg = cert.signature_algorithm_oid.dotted_string

    # key_type + bits + curve
    key_type, key_bits, curve_name = _classify_public_key(pub)

    return {
        "spki_sha256": spki_sha256,
        "der_sha256": der_sha256,
        "not_before_iso": not_before,
        "not_after_iso": not_after,
        "issuer": issuer,
        "subject": subject,
        "signature_alg": sig_alg,
        "key_type": key_type,
        "key_bits": key_bits,
        "curve_name": curve_name,
        "backend": "cryptography",
        "error": None,
    }


def _classify_public_key(pub: "Any") -> Tuple[str, int, str]:
    """Return ``(key_type, key_bits, curve_name)`` for a public key.

    ``key_bits`` is 0 for non-RSA. ``curve_name`` is "" for non-EC.
    """
    if not _CRYPTOGRAPHY_AVAILABLE:  # pragma: no cover — defensive
        return ("unknown", 0, "")
    if isinstance(pub, rsa.RSAPublicKey):
        return ("rsa", int(pub.key_size), "")
    if isinstance(pub, ec.EllipticCurvePublicKey):
        return ("ec", 0, pub.curve.name.lower())
    if isinstance(pub, ed25519.Ed25519PublicKey):
        return ("ed25519", 0, "ed25519")
    if isinstance(pub, dsa.DSAPublicKey):
        return ("dsa", int(pub.key_size), "")
    return ("unknown", 0, "")


# ---------------------------------------------------------------------------
# Backend: openssl subprocess
# ---------------------------------------------------------------------------


_OPENSSL_TIMEOUT_S = 5


def _inspect_via_openssl(cert_pem_bytes: bytes) -> Dict[str, Any]:
    """openssl-binary fallback parser.

    Used when the cryptography package isn't installed (sidecar
    disabled / install incomplete) OR when ``prefer_backend="openssl"``
    is forced. Performs three subprocess calls — kept short via
    ``-noout`` selectors — and parses the textual output.

    Limitations vs cryptography backend:
    - SPKI extraction via openssl is best-effort; for legacy openssl
      builds without ``-pubkey`` support, ``spki_sha256`` MAY be the
      empty string and ``error`` MAY be populated.
    - signature algorithm parsing depends on locale; we strip locale
      labels and lowercase.
    """
    openssl = shutil.which("openssl")
    if not openssl:
        raise CertInspectError(
            "openssl backend: 'openssl' binary not on PATH"
        )

    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=".pem", delete=False
    ) as fh:
        fh.write(cert_pem_bytes)
        tmp_path = fh.name

    try:
        # Pass 1: text dump with the fields we need.
        txt = _openssl_run(
            openssl,
            ["x509", "-in", tmp_path, "-noout",
             "-issuer", "-subject", "-startdate", "-enddate", "-text"],
        )
        # Pass 2: DER full-cert
        der_full = _openssl_run_bin(
            openssl, ["x509", "-in", tmp_path, "-outform", "DER"]
        )
        der_sha256 = hashlib.sha256(der_full).hexdigest()
        # Pass 3: SPKI DER (best-effort)
        try:
            pub_pem = _openssl_run(
                openssl, ["x509", "-in", tmp_path, "-pubkey", "-noout"]
            )
            pub_der = _openssl_run_bin(
                openssl,
                ["pkey", "-pubin", "-outform", "DER"],
                stdin=pub_pem.encode("ascii", errors="replace"),
            )
            spki_sha256 = hashlib.sha256(pub_der).hexdigest()
            spki_err: Optional[str] = None
        except Exception as exc:  # pragma: no cover — older openssl
            spki_sha256 = ""
            spki_err = "spki-extract-failed:%s" % type(exc).__name__
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    issuer = _grep_line(txt, "issuer=").strip()
    subject = _grep_line(txt, "subject=").strip()
    not_before = _openssl_date(_grep_line(txt, "notBefore="))
    not_after = _openssl_date(_grep_line(txt, "notAfter="))

    # signature algorithm + key type heuristics from the -text body
    sig_alg = ""
    key_type = "unknown"
    key_bits = 0
    curve_name = ""
    for line in txt.splitlines():
        ls = line.strip().lower()
        if ls.startswith("signature algorithm:"):
            sig_alg = ls.split(":", 1)[1].strip()
        elif ls.startswith("public key algorithm:"):
            alg = ls.split(":", 1)[1].strip()
            if "rsa" in alg:
                key_type = "rsa"
            elif "ed25519" in alg:
                key_type = "ed25519"
                curve_name = "ed25519"
            elif "ed448" in alg:
                key_type = "ed448"
                curve_name = "ed448"
            elif "ec" in alg or "id-ecpublickey" in alg:
                key_type = "ec"
            elif "dsa" in alg:
                key_type = "dsa"
        elif "public-key:" in ls or "rsa public-key:" in ls:
            # e.g. "Public-Key: (2048 bit)"
            m = re.search(r"\((\d+)\s*bit\)", ls)
            if m:
                key_bits = int(m.group(1))
        elif ls.startswith("asn1 oid:") or ls.startswith("nist curve:"):
            curve_name = ls.split(":", 1)[1].strip().lower()
            if curve_name.startswith("nist"):
                curve_name = curve_name.split()[-1].lower()

    err: Optional[str] = spki_err  # may be None
    return {
        "spki_sha256": spki_sha256,
        "der_sha256": der_sha256,
        "not_before_iso": not_before,
        "not_after_iso": not_after,
        "issuer": issuer,
        "subject": subject,
        "signature_alg": sig_alg,
        "key_type": key_type,
        "key_bits": key_bits,
        "curve_name": curve_name,
        "backend": "openssl",
        "error": err,
    }


def _openssl_run(openssl: str, args: List[str], stdin: Optional[bytes] = None) -> str:
    proc = subprocess.run(  # nosec — bounded args, fixed binary
        [openssl] + args,
        input=stdin,
        capture_output=True,
        timeout=_OPENSSL_TIMEOUT_S,
        check=False,
    )
    if proc.returncode != 0:
        raise CertInspectError(
            "openssl %s failed rc=%d stderr=%s"
            % (args[0], proc.returncode, proc.stderr.decode("utf-8", "replace")[:200])
        )
    return proc.stdout.decode("utf-8", "replace")


def _openssl_run_bin(openssl: str, args: List[str], stdin: Optional[bytes] = None) -> bytes:
    proc = subprocess.run(  # nosec
        [openssl] + args,
        input=stdin,
        capture_output=True,
        timeout=_OPENSSL_TIMEOUT_S,
        check=False,
    )
    if proc.returncode != 0:
        raise CertInspectError(
            "openssl %s failed rc=%d stderr=%s"
            % (args[0], proc.returncode, proc.stderr.decode("utf-8", "replace")[:200])
        )
    return proc.stdout


def _grep_line(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):]
    return ""


def _openssl_date(raw: str) -> str:
    """Convert openssl date (``MMM DD HH:MM:SS YYYY GMT``) → ISO-8601 Z."""
    raw = raw.strip()
    if not raw:
        return ""
    try:
        dt = datetime.strptime(raw, "%b %d %H:%M:%S %Y %Z")
    except ValueError:
        # try without GMT suffix
        try:
            dt = datetime.strptime(raw, "%b %d %H:%M:%S %Y")
        except ValueError:
            return ""
    return dt.replace(tzinfo=timezone.utc, microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _to_z(iso: str) -> str:
    """Normalise ``2026-01-01T00:00:00+00:00`` → ``2026-01-01T00:00:00Z``."""
    if iso.endswith("+00:00"):
        return iso[:-6] + "Z"
    if iso.endswith("Z"):
        return iso
    # ISO without timezone — assume UTC for audit consistency.
    return iso + "Z"


# ---------------------------------------------------------------------------
# Self-test (`python3 cert_inspector.py --self-test`)
# ---------------------------------------------------------------------------


def _self_test() -> int:
    """Generate a self-signed cert and roundtrip ``inspect``.

    Returns 0 on success, non-zero on failure. Designed to be a smoke
    test, NOT a full unit-test surface (those live in
    ``tests/test_cert_inspector.py``).
    """
    tmp = tempfile.mkdtemp(prefix="cert-inspector-selftest-")
    try:
        openssl = shutil.which("openssl")
        if not openssl:
            sys.stderr.write(
                "self-test: openssl binary not found; cannot generate cert.\n"
            )
            return 2
        # Try ed25519 first (fastest + smallest); fall back to RSA-2048
        # for older openssl / LibreSSL builds that lack ed25519 support
        # (e.g., macOS system libressl-3.3).
        key_pem = os.path.join(tmp, "key.pem")
        cert_pem = os.path.join(tmp, "cert.pem")
        gen = subprocess.run(  # nosec — fixed binary, controlled args
            [
                openssl, "req", "-x509",
                "-newkey", "ed25519",
                "-keyout", key_pem,
                "-out", cert_pem,
                "-days", "1",
                "-nodes",
                "-subj", "/CN=cert-inspector-selftest",
            ],
            capture_output=True,
            timeout=10,
            check=False,
        )
        if gen.returncode != 0:
            # Fallback: RSA-2048
            gen = subprocess.run(  # nosec
                [
                    openssl, "req", "-x509",
                    "-newkey", "rsa:2048",
                    "-keyout", key_pem,
                    "-out", cert_pem,
                    "-days", "1",
                    "-nodes",
                    "-subj", "/CN=cert-inspector-selftest",
                ],
                capture_output=True,
                timeout=15,
                check=False,
            )
        if gen.returncode != 0:
            sys.stderr.write(
                "self-test: openssl gen failed rc=%d stderr=%s\n"
                % (gen.returncode, gen.stderr.decode("utf-8", "replace")[:400])
            )
            return 3

        rep = inspect(cert_path=cert_pem)
        floor_ok, floor_reason = enforce_key_floor(rep)
        out = {
            "backend": rep["backend"],
            "key_type": rep["key_type"],
            "spki_sha256_len": len(rep["spki_sha256"]),
            "der_sha256_len": len(rep["der_sha256"]),
            "not_before_iso": rep["not_before_iso"],
            "not_after_iso": rep["not_after_iso"],
            "floor_ok": floor_ok,
            "floor_reason": floor_reason,
            "cryptography_available": _CRYPTOGRAPHY_AVAILABLE,
        }
        sys.stdout.write(json.dumps(out, indent=2, sort_keys=True) + "\n")

        # Force the openssl backend too, to exercise the fallback path.
        rep_openssl = inspect(cert_path=cert_pem, prefer_backend="openssl")
        sys.stdout.write(
            "openssl-fallback der_sha256_match: %s\n"
            % (rep_openssl["der_sha256"] == rep["der_sha256"])
        )
        if rep["der_sha256"] != rep_openssl["der_sha256"]:
            sys.stderr.write(
                "self-test: DER SHA256 mismatch between backends!\n"
            )
            return 4
        if not floor_ok:
            sys.stderr.write(
                "self-test: cert failed key floor: %s\n" % floor_reason
            )
            return 5
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# CLI entry — subprocess-invocation contract from the bridge
# ---------------------------------------------------------------------------


def _cli_main(argv: List[str]) -> int:
    """Subprocess CLI: receive cert path or stdin PEM; emit JSON report.

    Usage:
        python3 cert_inspector.py <cert_path>           # JSON on stdout
        python3 cert_inspector.py -                     # read PEM from stdin
        python3 cert_inspector.py --self-test           # roundtrip smoke

    Exit codes:
        0 = report on stdout
        2 = openssl binary missing (self-test only)
        3 = cert parse failure
        4 = backend mismatch (self-test only)
        5 = key floor failure (self-test only)
        6 = bad args
    """
    if len(argv) < 2:
        sys.stderr.write(
            "usage: cert_inspector.py <cert_path> | - | --self-test\n"
        )
        return 6
    arg = argv[1]
    if arg == "--self-test":
        return _self_test()
    try:
        if arg == "-":
            pem_bytes = sys.stdin.buffer.read(64 * 1024)
            rep = inspect(cert_pem_bytes=pem_bytes)
        else:
            rep = inspect(cert_path=arg)
    except CertInspectError as exc:
        sys.stderr.write("cert-inspect-error: %s\n" % exc)
        return 3
    sys.stdout.write(json.dumps(rep, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover — script entry
    raise SystemExit(_cli_main(sys.argv))
