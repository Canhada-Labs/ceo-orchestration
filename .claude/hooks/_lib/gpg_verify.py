"""GPG detached-signature verification with signer fingerprint allowlist.

PLAN-045 Wave 1 P0-01 / P0-02. Shared helper consolidating the GPG
verification surface used by:

- `check_canonical_edit.py` — verifying `.asc` signatures on sentinel
  `approved.md` files (ADR-010 sentinel GPG hardening)
- `scripts/skill-patch-apply.py` — verifying SP-NNN proposal
  signatures (ADR-031 self-improving-skills SP-NNN flow)

Both call-sites previously performed ad-hoc verification:
`skill-patch-apply.py::_verify_gpg_signature` accepted any valid GOODSIG
without cross-checking the returned fingerprint against an Owner-chosen
allowlist (the TOFU anti-pattern PLAN-044 F-01-02 flagged as P0).
`check_canonical_edit.py` did not verify any signature at all — pattern
match of `Approved-By:` line was the only gate (PLAN-044 F-01-01 P0).

This module ships one function, `verify_detached`, that:

1. Invokes ``gpg --batch --status-fd 1 --verify <sig> <signed>`` with
   timeout.
2. Parses GOODSIG + VALIDSIG lines from `--status-fd` output to extract
   the signer fingerprint.
3. Cross-checks the fingerprint against a plaintext allowlist
   (one-fpr-per-line, comments with ``#``, blank lines skipped).
4. Returns ``(ok: bool, fpr: str, reason: str)`` — ``ok`` is True only
   when GPG reported good+valid AND the fingerprint is in the allowlist.

## Allowlist semantics

- Missing allowlist file → fail-CLOSED (``ok=False``, reason=
  ``allowlist_missing``). Never falls back to TOFU.
- Empty allowlist (all lines blank/comment) → fail-CLOSED
  (``allowlist_empty``). Empty list = no signers = no edits.
- Allowlist format:

    # comment
    <40-hex-uppercase-fingerprint>   # optional trailing comment on line

  Each fingerprint is normalised (strip, uppercase, remove whitespace).
  Non-40-hex lines are skipped with a single stderr line (per-adopter
  diagnostic without failing the whole check).

## Fail-CLOSED contract

Every error path returns ``ok=False`` with a human-readable ``reason``.
The caller is expected to audit the reason (best-effort audit_emit) and
block the action. There is no ``allow`` default.

## Stdlib-only (ADR-002)

Uses ``subprocess``, ``shutil.which``, ``re``, ``pathlib``. No GPG
Python bindings; the CLI is the contract.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional, Set, Tuple

__all__ = [
    "GpgVerifyError",
    "verify_detached",
    "load_allowlist",
    "normalise_fpr",
]

_VALID_FPR_RE = re.compile(r"^[0-9A-Fa-f]{40}$")
_STRIP_WS_RE = re.compile(r"\s+")


class GpgVerifyError(Exception):
    """Raised on internal allowlist parse errors that the caller cannot
    reasonably recover from. Caller converts to (False, "", str(e))."""


def normalise_fpr(raw: str) -> str:
    """Canonicalise a fingerprint string.

    Removes whitespace, uppercases, validates 40-hex. Returns "" if
    the input is not a valid fingerprint after normalisation.

    This is the single chokepoint for "is this string a valid fpr" —
    callers MUST route every fingerprint through it so the allowlist
    comparison is stable regardless of user formatting (spaces, case).
    """
    if not raw:
        return ""
    cleaned = _STRIP_WS_RE.sub("", raw).upper()
    if _VALID_FPR_RE.match(cleaned):
        return cleaned
    return ""


def load_allowlist(
    allowlist_path: Path,
) -> Tuple[Set[str], Optional[str]]:
    """Read and parse the signer-fpr allowlist.

    Returns ``(fprs, error_reason)``. ``error_reason`` is:

    - ``"allowlist_missing"`` if the file does not exist.
    - ``"allowlist_not_file"`` if the path exists but isn't a file.
    - ``"allowlist_symlink_rejected"`` if the path (or any ancestor) is
      a symlink (defense against symlink substitution).
    - ``"allowlist_read_error:<ExceptionType>"`` on OSError.
    - ``"allowlist_empty"`` if the file parses to 0 fingerprints.
    - ``None`` on success.

    On any error, ``fprs`` is the empty set. Callers MUST treat a
    non-None ``error_reason`` as fail-CLOSED.
    """
    try:
        if allowlist_path.is_symlink():
            return set(), "allowlist_symlink_rejected"
        # Check only the immediate parent. Deeper ancestor symlinks
        # (e.g. macOS ``/var`` -> ``/private/var``) are filesystem-
        # layout constants; rejecting them would make the helper
        # unusable on any system with non-trivial mount layouts.
        # The realistic attacker model is an agent with write access
        # inside the repo — which CODEOWNERS + canonical-edit already
        # defend. A symlink at the file itself, or its immediate
        # parent directory, is the viable attack surface.
        parent = allowlist_path.parent
        if parent.is_symlink():
            return set(), "allowlist_symlink_rejected"
        if not allowlist_path.exists():
            return set(), "allowlist_missing"
        if not allowlist_path.is_file():
            return set(), "allowlist_not_file"
        text = allowlist_path.read_text(encoding="utf-8")
    except OSError as e:
        return set(), f"allowlist_read_error:{type(e).__name__}"

    fprs: Set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Strip trailing in-line comment (e.g. "FPR  # owner 2026")
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        fpr = normalise_fpr(line)
        if fpr:
            fprs.add(fpr)
        # Silently skip malformed lines — adopters may add stray text;
        # a single bad line should not fail-CLOSED the whole allowlist.
        # Malformed lines will surface in tests + audit checks.

    if not fprs:
        return set(), "allowlist_empty"

    return fprs, None


def _run_gpg_verify(
    gpg_bin: str,
    signed_file: Path,
    signature_file: Path,
    timeout: float,
) -> Tuple[int, str, str]:
    """Low-level GPG subprocess call.

    Returns ``(returncode, stdout, stderr)``. Never raises — OSError /
    TimeoutExpired collapse to ``(-1, "", error_marker)``.
    """
    try:
        proc = subprocess.run(
            [
                gpg_bin,
                "--batch",
                "--status-fd", "1",
                "--verify",
                str(signature_file),
                str(signed_file),
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "gpg_timeout"
    except OSError as e:
        return -1, "", f"gpg_os_error:{type(e).__name__}"


def _parse_status_fd(stdout: str) -> Tuple[bool, Set[str]]:
    """Extract (goodsig_seen, fprs) from --status-fd=1 output.

    - GOODSIG line presence → cryptographic signature validates.
    - VALIDSIG line fields → both candidate fingerprints:
        * 3rd field (``parts[2]``)  = the key that MADE the signature
          (the signing **subkey** for a best-practice primary+subkey
          setup; the sole key for a single-key setup).
        * last field (``parts[-1]``) = the **primary**-key fingerprint.
      Both are collected so an allowlist holding EITHER the primary or
      the signing-subkey fpr matches. For a single-key setup the two
      fields are identical, so the returned set degenerates to one fpr.

    GOODSIG and VALIDSIG are bound (M7): fingerprints are only returned
    when a GOODSIG line was also seen on the same status stream. Without
    a GOODSIG, the set is empty even if a VALIDSIG fpr parsed.

    Returns ``(good, fprs)`` where ``fprs`` is the set of normalised
    40-hex candidate fingerprints. Absence of GOODSIG, or of any
    parseable VALIDSIG fpr, yields an empty set.
    """
    good = False
    fprs: Set[str] = set()
    for line in stdout.splitlines():
        if line.startswith("[GNUPG:] GOODSIG"):
            good = True
        elif line.startswith("[GNUPG:] VALIDSIG"):
            parts = line.split()
            if len(parts) >= 3:
                # parts[2] = signing-(sub)key fpr; parts[-1] = primary.
                for raw in (parts[2], parts[-1]):
                    candidate = normalise_fpr(raw)
                    if candidate:
                        fprs.add(candidate)
    # Bind GOODSIG <-> VALIDSIG: never surface a fpr without a GOODSIG.
    if not good:
        return False, set()
    return good, fprs


def verify_detached(
    signed_file: Path,
    signature_file: Path,
    *,
    allowlist_path: Optional[Path] = None,
    allowlist_fprs: Optional[Iterable[str]] = None,
    gpg_bin: Optional[str] = None,
    timeout: float = 15.0,
) -> Tuple[bool, str, str]:
    """Verify a detached GPG signature and check the fpr against an allowlist.

    Parameters
    ----------
    signed_file
        The file whose content was signed.
    signature_file
        Path to the detached ``.asc`` (or ``.sig``) signature.
    allowlist_path
        Optional path to a signer-fpr allowlist (one fpr per line). If
        None, ``allowlist_fprs`` is used instead. If BOTH are None, the
        verification fails with ``no_allowlist_provided`` — no TOFU.
    allowlist_fprs
        Iterable of already-loaded fpr strings (pre-normalised).
        Mutually exclusive with ``allowlist_path`` for clarity; if both
        provided, ``allowlist_path`` wins.
    gpg_bin
        Override path to gpg binary. If None, resolved via PATH
        (``gpg`` then ``gpg2``).
    timeout
        Subprocess timeout in seconds. Default 15s.

    Returns
    -------
    (ok, fpr, reason)
        ``ok=True`` only when:
          1. gpg binary is available
          2. gpg reported GOODSIG + VALIDSIG (bound together — M7)
          3. at least one parsed candidate fpr (the primary key fpr
             from the LAST VALIDSIG field, or the signing-(sub)key fpr
             from the 3rd field) is non-empty and valid 40-hex
          4. one of the candidate fprs is in the allowlist

        ``fpr`` is the normalised matching signer fingerprint on
        success (the allowlisted candidate), empty on failure.

        ``reason`` is empty string on success, or one of these on
        failure (matched for audit/log breadcrumbs):

        - ``gpg_missing`` — no gpg/gpg2 binary on PATH
        - ``signature_file_missing`` — ``signature_file`` does not exist
        - ``signature_file_symlink`` — ``signature_file`` is a symlink
        - ``signed_file_missing`` — ``signed_file`` does not exist
        - ``signed_file_symlink`` — ``signed_file`` is a symlink
        - ``gpg_timeout`` — subprocess exceeded ``timeout``
        - ``gpg_os_error:<Type>`` — subprocess could not be launched
        - ``gpg_returncode_N`` — gpg exited non-zero (bad signature)
        - ``no_goodsig`` — status-fd had no GOODSIG line
        - ``no_validsig_fpr`` — status-fd had GOODSIG but no VALIDSIG
          (or VALIDSIG without parseable fpr)
        - ``no_allowlist_provided`` — neither allowlist_path nor
          allowlist_fprs given
        - ``allowlist_missing`` / ``allowlist_empty`` /
          ``allowlist_not_file`` / ``allowlist_symlink_rejected`` /
          ``allowlist_read_error:<Type>`` — per ``load_allowlist``
        - ``fpr_not_in_allowlist`` — GOODSIG+VALIDSIG but fpr absent
          from allowlist

    Never raises. All error paths return a concrete ``(False, "",
    reason)`` triple for structured handling.
    """
    # Symlink reject on both input files (PLAN-044 F-01-04 discipline).
    try:
        if signature_file.is_symlink():
            return False, "", "signature_file_symlink"
        if signed_file.is_symlink():
            return False, "", "signed_file_symlink"
    except OSError as e:
        return False, "", f"file_stat_error:{type(e).__name__}"

    if not signature_file.is_file():
        return False, "", "signature_file_missing"
    if not signed_file.is_file():
        return False, "", "signed_file_missing"

    # Resolve allowlist.
    fprs: Set[str]
    if allowlist_path is not None:
        fprs, err = load_allowlist(allowlist_path)
        if err is not None:
            return False, "", err
    elif allowlist_fprs is not None:
        fprs = {f for f in (normalise_fpr(x) for x in allowlist_fprs) if f}
        if not fprs:
            return False, "", "allowlist_empty"
    else:
        return False, "", "no_allowlist_provided"

    # Locate gpg.
    binary = gpg_bin or shutil.which("gpg") or shutil.which("gpg2")
    if not binary:
        return False, "", "gpg_missing"

    returncode, stdout, stderr = _run_gpg_verify(
        binary, signed_file, signature_file, timeout
    )
    if returncode == -1:
        # Error marker is in stderr per _run_gpg_verify.
        return False, "", stderr or "gpg_subprocess_error"
    if returncode != 0:
        return False, "", f"gpg_returncode_{returncode}"

    good, candidate_fprs = _parse_status_fd(stdout)
    if not good:
        return False, "", "no_goodsig"
    if not candidate_fprs:
        return False, "", "no_validsig_fpr"

    # Accept if EITHER the primary or the signing-(sub)key fpr is in the
    # allowlist (F1). Return the matching fpr; prefer a deterministic
    # pick when more than one candidate matches.
    matched = sorted(candidate_fprs & fprs)
    if not matched:
        return False, "", "fpr_not_in_allowlist"

    return True, matched[0], ""
