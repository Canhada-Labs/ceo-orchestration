#!/usr/bin/env python3
"""Verify the HMAC chain in audit-log.jsonl.

PLAN-023 Phase B / ADR-055.

Walks an audit-log.jsonl file (or stdin) from first to last entry,
recomputing the HMAC chain and comparing against the recorded ``hmac``
field on each line. Exits 0 iff the chain is intact.

## Exit codes

- **0** — chain intact (or log empty / pre-v2.9 zone only).
- **1** — tamper detected (line-level report on stderr).
- **2** — audit-key file missing or unreadable.
- **3** — malformed JSONL line (distinct from tamper — operator action
  is "recover the partial line", not "investigate tamper").
- **4** — permission error on key or log.

## Semantics

1. Genesis ``prev_hmac = b'\\x00' * 32``.
2. Entry without ``hmac`` field in pre-v2.9 zone: tolerated (warning
   only). As soon as the first ``hmac``-bearing entry appears, the
   chain is ACTIVE for that file. Any subsequent entry WITHOUT
   ``hmac`` → tamper (transition-entry rule is one-way).
3. Entry with ``hmac`` field in CHAIN_ACTIVE state: recompute HMAC
   from (key, prev_hmac, entry_sans_hmac_and_hmac_error) and compare.
4. Chain resets ONLY on file boundary (log rotation). A single file
   does not carry multiple chains.

## Non-goals

- Does not read or rely on the sidecar ``audit-log.last-hmac`` file
  (the log itself is the source of truth for verification).
- Does not detect tail truncation (covered by external anchor,
  post-v1.6.0).
- Does not detect rollback to an older log+key snapshot pair.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple


_REPO_HOOKS = Path(__file__).resolve().parent.parent / "hooks"
if str(_REPO_HOOKS) not in sys.path:
    sys.path.insert(0, str(_REPO_HOOKS))

from _lib import audit_hmac  # noqa: E402
from _lib.audit_hmac import (  # noqa: E402
    AuditHmacError,
    GENESIS_PREV,
    HMAC_BYTES,
    HMAC_HEX_LEN,
    STATUS_INTACT,
    STATUS_KEY_MISSING,
    STATUS_MALFORMED,
    STATUS_PERM_ERROR,
    STATUS_TAMPER,
    VerifyResult,
    compute_entry_hmac,
    from_hex,
    verify_chain,
)


# Exit code constants
EXIT_INTACT = 0
EXIT_TAMPER = 1
EXIT_KEY_MISSING = 2
EXIT_MALFORMED = 3
EXIT_PERM = 4


def _err(msg: str) -> None:
    sys.stderr.write(msg + "\n")


def _read_key(key_file: Optional[Path]) -> bytes:
    """Read and validate the audit-key.

    If ``key_file`` is None, use :func:`audit_hmac.key_path`.
    """
    p = key_file if key_file is not None else audit_hmac.key_path()
    if not p.exists():
        _err(
            "error: audit-key not found at {p}; "
            "generate one by writing an audit entry, or pass --key-file".format(p=p)
        )
        sys.exit(EXIT_KEY_MISSING)
    try:
        mode = p.stat().st_mode
    except OSError as e:
        _err("error: stat failed on {p}: {e}".format(p=p, e=e))
        sys.exit(EXIT_PERM)
    if mode & 0o077 != 0:
        _err(
            "error: unsafe perms on {p} (must be owner-only 0600)".format(p=p)
        )
        sys.exit(EXIT_PERM)
    try:
        data = p.read_bytes()
    except OSError as e:
        _err("error: cannot read {p}: {e}".format(p=p, e=e))
        sys.exit(EXIT_PERM)
    if len(data) != audit_hmac.KEY_BYTES:
        _err(
            "error: {p} is {n} bytes (expected {k})".format(
                p=p, n=len(data), k=audit_hmac.KEY_BYTES
            )
        )
        sys.exit(EXIT_PERM)
    return data


def _format_report(
    status: str,
    line_num: int,
    entry: Dict[str, Any],
    expected_hmac: Optional[str],
    actual_hmac: Optional[str],
    reason: str,
) -> Dict[str, Any]:
    """Build structured JSON report for --json output."""
    return {
        "status": status,
        "line": line_num,
        "reason": reason,
        "entry_ts": entry.get("ts"),
        "entry_action": entry.get("action"),
        "expected_hmac": expected_hmac,
        "actual_hmac": actual_hmac,
    }


def _emit_human_report(report: Dict[str, Any]) -> None:
    """Pretty-print tamper report to stderr."""
    sys.stderr.write(
        "TAMPER DETECTED at line {line}\n".format(line=report["line"])
    )
    sys.stderr.write(
        "  entry_ts:      {ts}\n".format(ts=report.get("entry_ts"))
    )
    sys.stderr.write(
        "  entry_action:  {a}\n".format(a=report.get("entry_action"))
    )
    sys.stderr.write("  reason:        {r}\n".format(r=report.get("reason")))
    if report.get("expected_hmac"):
        sys.stderr.write(
            "  expected_hmac: {h}\n".format(h=report["expected_hmac"])
        )
    if report.get("actual_hmac"):
        sys.stderr.write(
            "  actual_hmac:   {h}\n".format(h=report["actual_hmac"])
        )
    sys.stderr.write(
        "Chain broken. Do not trust entries >= line {n}.\n".format(
            n=report["line"]
        )
    )


def _emit_report(report, json_output: bool) -> None:
    """Emit a tamper/malformed report either as JSON or human text."""
    if json_output:
        print(json.dumps(report, separators=(",", ":")))
    else:
        _emit_human_report(report)


def _decode_entry(line_num: int, raw: str) -> "tuple[Optional[str], Optional[dict], Optional[int]]":
    """Parse raw line → (stripped, entry_dict or None, exit_code or None).

    Returns ``(None, None, exit_code)`` on decode failure; returns
    ``("", None, None)`` for blank lines; otherwise ``(stripped, entry, None)``.
    """
    stripped = raw.strip()
    if not stripped:
        return "", None, None
    try:
        entry = json.loads(stripped)
    except json.JSONDecodeError as e:
        _err(
            "error: line {n} is malformed JSON: {e}".format(n=line_num, e=e)
        )
        return None, None, EXIT_MALFORMED
    if not isinstance(entry, dict):
        _err("error: line {n} is not a JSON object".format(n=line_num))
        return None, None, EXIT_MALFORMED
    return stripped, entry, None


def _classify_hmac_presence(
    state: str, entry: dict, line_num: int, json_output: bool,
) -> "tuple[str, Any]":
    """Handle the hmac-missing vs. hmac-present fork.

    Returns ``(status, payload)`` where status is one of:
      - ``"pre_v29"`` — pre-v2.9 entry, skip with counter bump
      - ``"transition"`` — violation: hmac-bearing → hmac-less, exit tamper
      - ``"malformed"`` — hmac field wrong type/length, exit malformed
      - ``"ok"`` — payload is the validated hmac_hex string
    """
    hmac_hex = entry.get("hmac")
    if hmac_hex is None:
        if state == "CHAIN_START":
            return "pre_v29", None
        report = _format_report(
            "tamper", line_num, entry, None, None,
            "transition_violation: hmac-bearing entry followed by "
            "hmac-less entry (one-way rule)",
        )
        _emit_report(report, json_output)
        return "transition", EXIT_TAMPER

    if not isinstance(hmac_hex, str) or len(hmac_hex) != HMAC_HEX_LEN:
        report = _format_report(
            "malformed", line_num, entry, None, str(hmac_hex),
            "hmac_field_malformed: not 64 hex chars",
        )
        _emit_report(report, json_output)
        return "malformed", EXIT_MALFORMED

    return "ok", hmac_hex


def _verify_entry_hmac(
    key: bytes,
    prev_hmac: bytes,
    entry: dict,
    hmac_hex: str,
    line_num: int,
    json_output: bool,
) -> "tuple[Optional[bytes], Optional[int]]":
    """Recompute entry HMAC + constant-time compare against recorded.

    Returns ``(new_prev_hmac, exit_code)``. On success returns
    ``(actual_bytes, None)``; on failure returns ``(None, exit_code)``.
    """
    entry_sans = {
        k: v for k, v in entry.items()
        if k != "hmac" and k != "hmac_error"
    }
    try:
        expected = compute_entry_hmac(key, prev_hmac, entry_sans)
    except AuditHmacError as e:
        _err(
            "error: HMAC compute failed at line {n}: {e}".format(
                n=line_num, e=e
            )
        )
        return None, EXIT_MALFORMED

    try:
        actual = from_hex(hmac_hex)
    except AuditHmacError as e:
        _err(
            "error: hmac field not parseable at line {n}: {e}".format(
                n=line_num, e=e
            )
        )
        return None, EXIT_MALFORMED

    import hmac as _h
    if not _h.compare_digest(expected, actual):
        report = _format_report(
            "tamper", line_num, entry,
            expected.hex(), hmac_hex,
            "hmac_mismatch: recomputed does not match recorded",
        )
        _emit_report(report, json_output)
        return None, EXIT_TAMPER

    return actual, None


def verify(
    log_lines,
    key: bytes,
    since: int = 1,
    json_output: bool = False,
    verbose: bool = False,
    enforce_marker_if_manifest: bool = True,
    log_dir: Optional[Path] = None,
    strict_against_counter: bool = False,
    counter_override: Optional[int] = None,
) -> int:
    """Walk lines; return an exit code.

    ``log_lines`` is an iterable of (line_num, raw_line) tuples.
    ``since`` is 1-indexed starting line.

    Chain state machine:
      CHAIN_START — no hmac seen yet (pre-v2.9 zone).
      CHAIN_ACTIVE — at least one hmac seen; prev_hmac tracked.

    PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3 / ADR-055-AMEND-2:
    If ``enforce_marker_if_manifest=True`` AND the
    ``audit-log.rotation-manifest.json`` sidecar exists, line 1 of the
    log MUST be an entry with ``action == "chain_reset_marker"``;
    otherwise STATUS_TAMPER. Verifier uses LOCAL semantics (line 1
    inspection + sidecar presence); does NOT walk archives.
    """
    # AC12 enforcement: manifest-mode marker check on line 1. Read manifest
    # from log's SAME directory (NOT _audit_dir_from_env) so test envs with
    # custom log paths don't inherit production manifest state.
    manifest_present = False
    if enforce_marker_if_manifest and log_dir is not None:
        try:
            manifest_path = log_dir / audit_hmac.ROTATION_MANIFEST_FILENAME
            manifest_present = manifest_path.exists()
        except Exception:
            manifest_present = False

    state = "CHAIN_START"
    prev_hmac = GENESIS_PREV
    verified_count = 0
    pre_v29_count = 0
    first_chain_line_checked = False

    for line_num, raw in log_lines:
        if line_num < since:
            continue

        stripped, entry, exit_code = _decode_entry(line_num, raw)
        if exit_code is not None:
            return exit_code
        if not stripped:
            continue
        assert entry is not None

        status, payload = _classify_hmac_presence(
            state, entry, line_num, json_output
        )
        if status == "pre_v29":
            pre_v29_count += 1
            continue
        if status in ("transition", "malformed"):
            return payload  # type: ignore[return-value]

        hmac_hex = payload  # "ok" path
        assert isinstance(hmac_hex, str)

        if state == "CHAIN_START":
            state = "CHAIN_ACTIVE"
            prev_hmac = GENESIS_PREV

        # AC12 enforcement: if rotation-manifest sidecar present, FIRST
        # chain-active entry MUST be chain_reset_marker. Non-marker line 1
        # in marker-required mode = STATUS_TAMPER per ADR-055-AMEND-2.
        if (enforce_marker_if_manifest and manifest_present
                and not first_chain_line_checked):
            first_chain_line_checked = True
            if entry.get("action") != "chain_reset_marker":
                report = _format_report(
                    "tamper", line_num, entry, None, None,
                    "marker_required_but_absent: audit-log.rotation-manifest.json "
                    "present but line 1 action is not chain_reset_marker per "
                    "ADR-055-AMEND-2",
                )
                _emit_report(report, json_output)
                return EXIT_TAMPER

        new_prev, exit_code = _verify_entry_hmac(
            key, prev_hmac, entry, hmac_hex, line_num, json_output
        )
        if exit_code is not None:
            return exit_code
        assert new_prev is not None
        prev_hmac = new_prev
        verified_count += 1

    # PLAN-118 AC-B9-ii — strict-against-counter tail-truncation detection.
    # The persisted ``audit-log.chain-length`` counter is the monotonic
    # number of HMAC-bearing entries ever written (incremented under the
    # same FileLock as the entry itself). If the walker saw FEWER
    # HMAC-bearing entries than the counter says, the chain tail has
    # been truncated even though the surviving prefix verifies clean.
    # Flag as STATUS_TAMPER with reason=chain_length_truncation.
    if strict_against_counter:
        try:
            expected_length = (
                counter_override if counter_override is not None
                else audit_hmac.read_chain_length()
            )
        except Exception as e:
            report = _format_report(
                "tamper", 0, None, None, None,
                f"chain_length_read_failed: {type(e).__name__}: {e}",
            )
            _emit_report(report, json_output)
            return EXIT_TAMPER
        if verified_count < expected_length:
            report = _format_report(
                "tamper", 0, None,
                str(verified_count), str(expected_length),
                "chain_length_truncation: walker counted fewer "
                "HMAC-bearing entries than persisted counter",
            )
            _emit_report(report, json_output)
            return EXIT_TAMPER

    if json_output:
        print(json.dumps({
            "status": "intact",
            "verified_count": verified_count,
            "pre_v29_count": pre_v29_count,
        }, separators=(",", ":")))
    elif verbose:
        sys.stderr.write(
            "OK: chain intact. verified={v} pre_v29={p}\n".format(
                v=verified_count, p=pre_v29_count
            )
        )
    return EXIT_INTACT


def _iter_lines(log_path: Optional[Path]) -> "Iterator[tuple[int, str]]":
    """Yield ``(line_num, raw_line)`` pairs from file or stdin."""
    if log_path is None:
        for i, raw in enumerate(sys.stdin, start=1):
            yield (i, raw)
        return
    if not log_path.exists():
        _err("error: log file not found: {p}".format(p=log_path))
        sys.exit(EXIT_MALFORMED)
    with log_path.open("r", encoding="utf-8") as f:
        for i, raw in enumerate(f, start=1):
            yield (i, raw)


def main() -> int:
    """CLI entrypoint — verify an audit-log HMAC chain end-to-end."""
    parser = argparse.ArgumentParser(
        description="Verify the HMAC chain in audit-log.jsonl.",
        epilog="Exit 0=intact, 1=tamper, 2=key missing, 3=malformed, 4=perm.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Path to audit-log.jsonl (default: resolved via env / stdin)",
    )
    parser.add_argument(
        "--key-file",
        type=Path,
        default=None,
        help="Path to audit-key (default: resolved via env)",
    )
    parser.add_argument(
        "--since",
        type=int,
        default=1,
        help="1-indexed starting line (default: 1 = verify from genesis)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report to stdout",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print 'OK' summary on success (default: silent success)",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read log from stdin (equivalent to --log-file -)",
    )
    parser.add_argument(
        "--strict-against-counter",
        action="store_true",
        help=(
            "PLAN-118 AC-B9 — additionally enforce "
            "verified_count >= audit-log.chain-length (tail-truncation "
            "detection). Without this flag, a truncated tail whose "
            "surviving prefix verifies clean would be reported intact."
        ),
    )
    parser.add_argument(
        "--counter-override",
        type=int,
        default=None,
        help=(
            "Test/forensic-only: override the persisted "
            "audit-log.chain-length counter (paired with "
            "--strict-against-counter). Default reads the on-disk sidecar."
        ),
    )
    args = parser.parse_args()

    # Resolve log path.
    log_path: Optional[Path]
    if args.stdin or (args.log_file is not None and str(args.log_file) == "-"):
        log_path = None
    elif args.log_file is not None:
        log_path = args.log_file
    else:
        env_log = os.environ.get("CEO_AUDIT_LOG_PATH")
        if env_log:
            log_path = Path(env_log)
        else:
            # Default: sibling of audit-key resolution.
            try:
                default_dir = audit_hmac._audit_dir_from_env()
            except Exception:
                _err("error: cannot resolve default audit-log path; "
                     "pass --log-file")
                return EXIT_MALFORMED
            log_path = default_dir / "audit-log.jsonl"

    # Read key.
    try:
        key = _read_key(args.key_file)
    except SystemExit:
        raise

    return verify(
        _iter_lines(log_path),
        key,
        since=args.since,
        json_output=args.json,
        verbose=args.verbose,
        log_dir=log_path.parent if hasattr(log_path, "parent") else None,
        strict_against_counter=args.strict_against_counter,
        counter_override=args.counter_override,
    )


if __name__ == "__main__":
    sys.exit(main())
