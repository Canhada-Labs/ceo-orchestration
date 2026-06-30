"""STDLIB-ONLY bridge — federation cert inspector (ADR-126 boundary).

**STAGING NOTE (NOT PART OF MODULE BODY):** This file is the
PLAN-099-FOLLOWUP Wave B deliverable staged at
``.claude/plans/PLAN-099-FOLLOWUP/cert_inspector.py``. Owner ``git mv``s
this file to ``.claude/hooks/_lib/federation/cert_inspector.py`` at the
Wave B ceremony commit under
``CEO_KERNEL_OVERRIDE=PLAN-099-FOLLOWUP-WAVE-B-CERT-INSPECTOR-LAND``
+ ``CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT``, then deletes this staging
copy. Frontmatter + body are final-form; no edits needed at move
time. Strip this staging-note paragraph at move time.

**Boundary contract (ADR-126):** This module lives under
``.claude/hooks/_lib/federation/`` which is KERNEL HARD-DENY for
non-stdlib code (per ADR-126 §Part 1 + ADR-002). It therefore
DOES NOT import ``cryptography`` — instead it subprocess-invokes the
C1 crypto sidecar at
``.claude/sidecars/c1-crypto/cryptography-mvp/sidecar_code/cert_inspector.py``
which IS permitted to import ``cryptography``. The sidecar emits a
JSON report on stdout; this bridge parses + returns it to callers.

Kill-switch: ``CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED=1`` MUST
be set for the bridge to invoke the sidecar. When unset / "0" the
bridge falls back to the in-process openssl-subprocess parse path
(stdlib-only) and the floor enforcement runs with reduced fidelity
(no SPKI extraction on older openssl/libressl builds).

API surface identical to the prior cert_inspector module (callers
need no rewrites): :func:`inspect`, :func:`enforce_key_floor`,
:func:`spki_sha256_hex`, :func:`der_sha256_hex`, plus exception
types. Implementation pivots to subprocess.

Trust boundary:
- This bridge: STDLIB ONLY. No ``cryptography`` import (CI-gated by
  ``check-stdlib-only.py``).
- Sidecar: imports ``cryptography`` per ADR-129-AMEND-1 §5.
- Inter-process IPC: argv (cert path) + stdout (JSON report) +
  stderr (error message) + exit code.

CLI usage (smoke test):
    python3 cert_inspector.py <cert_path>
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

# Constants mirror the sidecar; floor logic in this bridge is the
# fallback path (openssl-only). Sidecar is the primary path.
RSA_MIN_BITS = 2048
EC_ALLOWED_CURVES = frozenset({"secp256r1", "secp384r1", "ed25519"})
DSA_ALLOWED = False
_WEAK_SIG_ALGORITHMS = frozenset(
    {
        "md5",
        "sha1",
        "1.2.840.113549.1.1.4",
        "1.2.840.113549.1.1.5",
        "1.2.840.10040.4.3",
        "1.2.840.10045.4.1",
    }
)

# Sidecar relative path under repo root. Resolved against
# ``CLAUDE_PROJECT_DIR`` at call time (matches kernel _lib pattern).
_SIDECAR_REL_PATH = (
    ".claude/sidecars/c1-crypto/cryptography-mvp/sidecar_code/cert_inspector.py"
)
_SIDECAR_KILLSWITCH_ENV = "CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED"
_SIDECAR_TIMEOUT_S = 15
_OPENSSL_TIMEOUT_S = 5


def _sidecar_enabled() -> bool:
    """Honor kill-switch env var. Default OFF per ADR-126 §Part 5."""
    return os.environ.get(_SIDECAR_KILLSWITCH_ENV, "0") == "1"


def _sidecar_path() -> Optional[str]:
    """Return absolute path to sidecar cert_inspector.py, or None.

    Resolves under ``CLAUDE_PROJECT_DIR`` if set, else relative to the
    bridge module's package root (post-``git mv`` to
    ``.claude/hooks/_lib/federation/`` → repo root is four parents up).
    """
    base = os.environ.get("CLAUDE_PROJECT_DIR")
    if not base:
        # When mv'd to _lib/federation/, parents: [federation, _lib,
        # hooks, .claude, <repo_root>].
        here = os.path.dirname(os.path.abspath(__file__))
        base = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    candidate = os.path.join(base, _SIDECAR_REL_PATH)
    if os.path.isfile(candidate):
        return candidate
    return None


class CertInspectError(Exception):
    """Raised when a cert cannot be parsed by either backend."""


class KeyFloorError(Exception):
    """Raised by :func:`enforce_key_floor` when the floor is not met."""


# ---------------------------------------------------------------------------
# Public API — same shape as prior cert_inspector module.
# ---------------------------------------------------------------------------


def inspect(
    cert_path: Optional[str] = None,
    cert_pem_bytes: Optional[bytes] = None,
    prefer_backend: str = "auto",
) -> Dict[str, Any]:
    """Inspect a single X.509 cert.

    Path resolution:
    - If ``CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED=1`` AND
      sidecar script exists AND ``prefer_backend in {"auto", "cryptography"}``,
      invoke the sidecar via subprocess.
    - Otherwise (kill-switch off, sidecar missing, or
      ``prefer_backend="openssl"``), fall back to the in-process
      openssl-subprocess parse path.

    Returns a normalised report ``dict`` matching the sidecar contract
    (12 fields per ADR-135-AMEND-1 §Cert inspection contract).
    """
    if (cert_path is None) == (cert_pem_bytes is None):
        raise CertInspectError(
            "inspect(): exactly one of cert_path/cert_pem_bytes required"
        )
    if prefer_backend not in ("auto", "cryptography", "openssl"):
        raise CertInspectError(
            "inspect(): prefer_backend must be auto|cryptography|openssl"
        )

    # Sidecar path (cryptography backend via subprocess)
    if prefer_backend in ("auto", "cryptography") and _sidecar_enabled():
        sidecar = _sidecar_path()
        if sidecar:
            try:
                return _inspect_via_sidecar(sidecar, cert_path, cert_pem_bytes)
            except CertInspectError:
                if prefer_backend == "cryptography":
                    raise
                # auto: fall through to openssl
        elif prefer_backend == "cryptography":
            raise CertInspectError(
                "inspect(): prefer_backend=cryptography but sidecar missing at %s"
                % _SIDECAR_REL_PATH
            )

    # Materialise PEM bytes for openssl backend.
    if cert_pem_bytes is None and cert_path is not None:
        try:
            with open(cert_path, "rb") as fh:
                cert_pem_bytes = fh.read(64 * 1024)
        except OSError as exc:
            raise CertInspectError(
                "inspect(): cannot read cert_path: %s" % exc
            ) from exc

    assert cert_pem_bytes is not None  # nosec — guarded above

    if prefer_backend in ("auto", "openssl"):
        return _inspect_via_openssl(cert_pem_bytes)

    raise CertInspectError(
        "inspect(): prefer_backend=cryptography but sidecar disabled "
        "(kill-switch %s != '1')" % _SIDECAR_KILLSWITCH_ENV
    )


def enforce_key_floor(report: Dict[str, Any]) -> Tuple[bool, str]:
    """Enforce per-cert key floor + signature algorithm floor.

    Pure function — identical contract to the sidecar's
    ``enforce_key_floor``. Logic is duplicated (intentionally) so this
    bridge can enforce the floor on openssl-fallback reports without
    a sidecar roundtrip.

    Floor rules (locked at this version; changes require ADR-129
    amendment):

    1. RSA  → ``key_bits`` ≥ :data:`RSA_MIN_BITS` (2048).
    2. EC   → ``curve_name`` ∈ :data:`EC_ALLOWED_CURVES`.
    3. Ed25519 → always allowed.
    4. Ed448  → REJECTED (Codex Loop A P2 — floor commits only to
       P-256/P-384/Ed25519).
    5. DSA  → REJECTED.
    6. unknown → REJECTED (fail-CLOSED).
    7. Signature algorithm — MD5/SHA1-based REJECTED.
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
    elif key_type == "ed448":
        return (False, "ed448-not-in-floor")
    else:
        return (False, "unsupported-key-type:%s" % key_type)

    sig_alg = (report.get("signature_alg") or "").lower()
    for weak in _WEAK_SIG_ALGORITHMS:
        if weak in sig_alg:
            return (False, "weak-signature-algorithm:%s" % sig_alg)

    return (True, "")


def spki_sha256_hex(report_or_pem: Union[Dict[str, Any], bytes, str]) -> str:
    """Return the SPKI SHA-256 (rotation-survives the cert itself)."""
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
    """Return the full-cert DER SHA-256 (legacy pin used by PLAN-099 MVP)."""
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
# Backend: sidecar subprocess (cryptography-importing C1 sidecar)
# ---------------------------------------------------------------------------


def _inspect_via_sidecar(
    sidecar: str,
    cert_path: Optional[str],
    cert_pem_bytes: Optional[bytes],
) -> Dict[str, Any]:
    """Subprocess-invoke the sidecar; parse its JSON report."""
    if cert_path is not None:
        argv = [sys.executable, sidecar, cert_path]
        stdin_data: Optional[bytes] = None
    else:
        argv = [sys.executable, sidecar, "-"]
        stdin_data = cert_pem_bytes
    try:
        proc = subprocess.run(  # nosec — fixed binary chain, bounded args
            argv,
            input=stdin_data,
            capture_output=True,
            timeout=_SIDECAR_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        # PLAN-114 F-7.1 — convert the subprocess timeout into the inspector's
        # own error type so the 'auto' backend can fall through to openssl and
        # the caller (server.py handler thread) never sees an uncaught
        # TimeoutExpired that would crash the thread.
        raise CertInspectError(
            "sidecar cert_inspector timed out after %ss" % _SIDECAR_TIMEOUT_S
        ) from exc
    if proc.returncode != 0:
        raise CertInspectError(
            "sidecar cert_inspector rc=%d stderr=%s"
            % (
                proc.returncode,
                proc.stderr.decode("utf-8", "replace")[:400],
            )
        )
    try:
        rep = json.loads(proc.stdout.decode("utf-8", "replace"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CertInspectError(
            "sidecar cert_inspector: invalid JSON on stdout: %s" % exc
        ) from exc
    if not isinstance(rep, dict):
        raise CertInspectError(
            "sidecar cert_inspector: expected dict, got %s" % type(rep).__name__
        )
    # Ensure the report still surfaces the sidecar's backend label.
    if rep.get("backend") not in ("cryptography", "openssl"):
        raise CertInspectError(
            "sidecar cert_inspector: bad 'backend' field: %r"
            % rep.get("backend")
        )
    return rep


# ---------------------------------------------------------------------------
# Backend: openssl subprocess fallback (stdlib-only path)
# ---------------------------------------------------------------------------


def _inspect_via_openssl(cert_pem_bytes: bytes) -> Dict[str, Any]:
    """openssl-binary fallback parser (stdlib-only path)."""
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
        txt = _openssl_run(
            openssl,
            ["x509", "-in", tmp_path, "-noout",
             "-issuer", "-subject", "-startdate", "-enddate", "-text"],
        )
        der_full = _openssl_run_bin(
            openssl, ["x509", "-in", tmp_path, "-outform", "DER"]
        )
        der_sha256 = hashlib.sha256(der_full).hexdigest()
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
            m = re.search(r"\((\d+)\s*bit\)", ls)
            if m:
                key_bits = int(m.group(1))
        elif ls.startswith("asn1 oid:") or ls.startswith("nist curve:"):
            curve_name = ls.split(":", 1)[1].strip().lower()
            if curve_name.startswith("nist"):
                curve_name = curve_name.split()[-1].lower()

    err: Optional[str] = spki_err
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
        try:
            dt = datetime.strptime(raw, "%b %d %H:%M:%S %Y")
        except ValueError:
            return ""
    return dt.replace(tzinfo=timezone.utc, microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


# ---------------------------------------------------------------------------
# Self-test (`python3 cert_inspector.py`)
# ---------------------------------------------------------------------------


def _self_test() -> int:
    """Generate a self-signed cert and roundtrip ``inspect`` (bridge path).

    Exercises whichever backend is active (sidecar if enabled +
    available, else openssl fallback). Returns 0 on success.
    """
    tmp = tempfile.mkdtemp(prefix="cert-inspector-bridge-selftest-")
    try:
        openssl = shutil.which("openssl")
        if not openssl:
            sys.stderr.write(
                "self-test: openssl binary not found; cannot generate cert.\n"
            )
            return 2
        key_pem = os.path.join(tmp, "key.pem")
        cert_pem = os.path.join(tmp, "cert.pem")
        gen = subprocess.run(  # nosec
            [
                openssl, "req", "-x509",
                "-newkey", "ed25519",
                "-keyout", key_pem,
                "-out", cert_pem,
                "-days", "1",
                "-nodes",
                "-subj", "/CN=cert-inspector-bridge-selftest",
            ],
            capture_output=True,
            timeout=10,
            check=False,
        )
        if gen.returncode != 0:
            gen = subprocess.run(  # nosec
                [
                    openssl, "req", "-x509",
                    "-newkey", "rsa:2048",
                    "-keyout", key_pem,
                    "-out", cert_pem,
                    "-days", "1",
                    "-nodes",
                    "-subj", "/CN=cert-inspector-bridge-selftest",
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
            "sidecar_enabled": _sidecar_enabled(),
            "sidecar_available": _sidecar_path() is not None,
        }
        sys.stdout.write(json.dumps(out, indent=2, sort_keys=True) + "\n")
        if not floor_ok:
            sys.stderr.write(
                "self-test: cert failed key floor: %s\n" % floor_reason
            )
            return 5
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":  # pragma: no cover — script entry
    raise SystemExit(_self_test())
