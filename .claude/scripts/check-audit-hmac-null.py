#!/usr/bin/env python3
"""CI gate — fail on the S234 ``hmac=null`` (float-in-HMAC) regression class.

PLAN-136 T2a.

S234 root cause: an audit action (``statusline_sidecar_write``) emitted a
``float`` field. The canonical-JSON encoder behind the HMAC chain FORBIDS
floats (S181), so every such emit was written with ``hmac=null`` plus an
``hmac_error`` breadcrumb (e.g. ``CanonicalJsonError``) and silently EXCLUDED
from the verifiable chain — invisible to the green test suite (the emit
fail-soft path dies downstream of the scrub-only unit test).

This gate scans an audit-log JSONL and FAILS (exit 1) if ANY line belonging
to a **known action** (``_lib.audit_emit._KNOWN_ACTIONS``) carries a broken
HMAC in the active zone — i.e. ``hmac`` is null/absent OR a non-null
``hmac_error`` breadcrumb is present. A clean log exits 0.

This is a regression guard, NOT a full chain verification — for cryptographic
chain integrity use ``audit-verify-chain.py``. The two are complementary: this
gate catches the *birth-defect* class (entries that never entered the chain),
which a chain walk can structurally miss.

## Exit codes

- **0** — no regression found (or log missing → fail-open with a warning).
- **1** — at least one known-action line has ``hmac`` null/absent OR a
  non-null ``hmac_error``, OR the present log contains a malformed
  (un-parseable / non-object) line.

## Flags

- ``--log <path>`` — audit-log JSONL to scan (default: resolved via
  ``CEO_AUDIT_LOG_PATH`` env, then the project audit dir).
- ``--json`` — emit a structured JSON report to stdout.

## Fail-open policy

The gate fail-OPENS **only** when the log file does not exist (a fresh repo /
CI checkout legitimately has no audit-log): exit 0 with a warning on stderr.
Every other anomaly (a present log with a broken known-action entry) FAILS.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_HOOKS = _SCRIPTS_DIR.parent / "hooks"
if str(_REPO_HOOKS) not in sys.path:
    sys.path.insert(0, str(_REPO_HOOKS))


# Reuse the line iterator + entry decoder from audit-verify-chain.py. That
# file is hyphenated (not a regular importable module), so load it by path.
def _load_verify_chain():
    """Import audit-verify-chain.py by file path and return the module."""
    path = _SCRIPTS_DIR / "audit-verify-chain.py"
    spec = importlib.util.spec_from_file_location(
        "_audit_verify_chain_for_gate", path
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError("cannot load audit-verify-chain.py at {p}".format(p=path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_vc = _load_verify_chain()
_iter_lines = _vc._iter_lines  # (Optional[Path]) -> Iterator[(int, str)]
_decode_entry = _vc._decode_entry  # (int, str) -> (stripped, entry|None, exit|None)

from _lib import audit_emit as _ae  # noqa: E402
from _lib import audit_hmac  # noqa: E402

_KNOWN_ACTIONS = _ae._KNOWN_ACTIONS


# Exit codes (mirror the verify-chain contract for the two cases we use).
EXIT_OK = 0
EXIT_REGRESSION = 1


def _err(msg: str) -> None:
    sys.stderr.write(msg + "\n")


def _resolve_default_log() -> Optional[Path]:
    """Resolve the project's default audit-log path (env, then audit dir).

    Returns ``None`` if neither resolution path produces a usable directory.
    """
    env_log = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env_log:
        return Path(env_log)
    try:
        default_dir = audit_hmac._audit_dir_from_env()
    except Exception:
        return None
    return default_dir / "audit-log.jsonl"


def scan(log_path: Optional[Path]) -> List[Dict[str, Any]]:
    """Walk the log; return a list of regression records (one per bad line).

    A regression record is emitted when a line whose ``action`` is in
    ``_KNOWN_ACTIONS`` has either ``hmac`` null/absent OR a non-null
    ``hmac_error``. Healthy entries carry ``hmac_error: null`` (key present,
    value null) — only a NON-null breadcrumb counts as a regression.

    Blank lines are skipped. A PRESENT-but-malformed line (JSON parse error /
    non-object) is itself a FINDING that fails the gate — fail-open is
    reserved for the *absent* log only (handled by the caller). A malformed
    line in a present log could otherwise let a tampered/corrupted log slip
    past this security gate with exit 0.
    """
    findings: List[Dict[str, Any]] = []
    for line_num, raw in _iter_lines(log_path):
        stripped, entry, exit_code = _decode_entry(line_num, raw)
        if exit_code is not None:
            # Present-but-malformed line → FAIL (do NOT fail-open). Only an
            # absent log is allowed to fail-open, and that is decided by the
            # caller before scan() ever runs.
            findings.append({
                "line": line_num,
                "action": None,
                "hmac_present": False,
                "hmac_error": None,
                "reason": "malformed_json",
            })
            continue
        if not stripped or entry is None:
            # Blank line → skip (out of scope for this gate).
            continue
        action = entry.get("action")
        if action not in _KNOWN_ACTIONS:
            continue
        hmac_val = entry.get("hmac")
        hmac_error = entry.get("hmac_error")
        hmac_missing = hmac_val is None  # null OR absent
        has_breadcrumb = hmac_error is not None
        if hmac_missing or has_breadcrumb:
            findings.append({
                "line": line_num,
                "action": action,
                "hmac_present": not hmac_missing,
                "hmac_error": hmac_error,
                "reason": (
                    "hmac_null_or_absent"
                    if hmac_missing
                    else "hmac_error_breadcrumb"
                ),
            })
    return findings


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — fail on any S234-class HMAC-null regression."""
    parser = argparse.ArgumentParser(
        description=(
            "Fail (exit 1) if the audit-log has an S234-class regression: a "
            "known action emitted with hmac=null (float-in-HMAC) or a "
            "non-null hmac_error breadcrumb."
        ),
        epilog="Exit 0 = clean (or log missing), 1 = regression found.",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help=(
            "Path to audit-log.jsonl to scan (default: CEO_AUDIT_LOG_PATH "
            "env, then the resolved project audit dir)."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a structured JSON report to stdout.",
    )
    args = parser.parse_args(argv)

    log_path: Optional[Path] = args.log if args.log is not None else _resolve_default_log()

    if log_path is None:
        _err(
            "warning: cannot resolve a default audit-log path; pass --log. "
            "Fail-open (exit 0)."
        )
        return EXIT_OK

    if not log_path.exists():
        # Fresh repo / CI checkout has no audit-log → fail-open by design.
        _err(
            "warning: audit-log not found at {p}; nothing to check "
            "(fail-open, exit 0).".format(p=log_path)
        )
        if args.json:
            print(json.dumps(
                {"status": "skipped", "reason": "log_missing", "log": str(log_path)},
                separators=(",", ":"),
            ))
        return EXIT_OK

    findings = scan(log_path)

    if args.json:
        print(json.dumps({
            "status": "fail" if findings else "ok",
            "log": str(log_path),
            "regression_count": len(findings),
            "findings": findings,
        }, separators=(",", ":")))

    if findings:
        if not args.json:
            _err(
                "FAIL: {n} S234-class HMAC-null regression(s) in {p}".format(
                    n=len(findings), p=log_path
                )
            )
            for f in findings[:20]:
                _err(
                    "  line {line}: action={action} reason={reason} "
                    "hmac_error={he}".format(
                        line=f["line"],
                        action=f["action"],
                        reason=f["reason"],
                        he=f["hmac_error"],
                    )
                )
            if len(findings) > 20:
                _err("  ... and {n} more".format(n=len(findings) - 20))
            _err(
                "These entries were EXCLUDED from the verifiable HMAC chain "
                "(S234 float-in-HMAC class). Fix the emitter to use integer "
                "basis-points, never float."
            )
        return EXIT_REGRESSION

    if not args.json:
        _err("OK: no HMAC-null regression in {p}".format(p=log_path))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
