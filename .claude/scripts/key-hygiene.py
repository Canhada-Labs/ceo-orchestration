#!/usr/bin/env python3
"""key-hygiene.py — Anthropic Admin API key hygiene (PLAN-135 W5 O9).

Turns the S206 incident response (revoke every exposed inference key +
record the rotation) into ONE command, backed by the org-level Anthropic
Admin API:

- ``list``        — read-only inventory of org API keys
                    (``GET /v1/organizations/api_keys``, cursor-paginated).
- ``deactivate``  — flip ONE key to ``status: inactive``
                    (``POST /v1/organizations/api_keys/{api_key_id}``) and
                    auto-append a ``docs/rotation-log.md`` entry (audit pair).
- ``incident``    — the S206 shape: deactivate ALL active org keys (minus
                    explicit ``--exclude-key-id`` survivors, e.g. the freshly
                    provisioned replacement) and append ONE rotation-log entry.

Security posture (THREAT-MODEL-WORKSHEET.md §3 admin-keys):

- **Admin key from env ONLY** (``ANTHROPIC_ADMIN_KEY``). There is NO CLI
  flag to pass a key; the key value is never printed, never logged, never
  included in any error message. The Admin API key class has a blast
  radius categorically larger than inference keys (org-wide deactivate +
  org-wide usage read) — custody per ADR-054-AMEND-1: OS keychain / Owner
  launch env only, never in repo, settings, or CI.
- **Fail-soft dormant without a key**: every command prints a DORMANT
  note and exits 0 when ``ANTHROPIC_ADMIN_KEY`` is unset — the script is
  safe to wire into routines that may run on machines without the key.
- **Mutations require explicit ``--confirm``**: ``deactivate`` and
  ``incident`` REFUSE (exit 1, zero network I/O) without it.
- **S206 lesson** (key leaked via a urllib error trace): all error paths
  are routed through ``_redact()`` which scrubs any ``sk-ant-…`` shaped
  substring before it can reach stdout/stderr; raw ``urllib`` exceptions
  (whose reprs can carry request state) are never re-raised.
- **Audit pair**: every successful mutation appends a row to the Log
  table of ``docs/rotation-log.md`` in the documented format
  (date | key | reason | rotated_by | outcome | notes) and emits a
  best-effort closed-enum audit event ``admin_key_lifecycle_event``
  (fail-soft: a missing/older ``_lib`` or unregistered action never
  blocks the hygiene operation).

Notes:

- The Admin API can NOT create keys (Console only) — after an
  ``incident`` run the Owner must provision the replacement key in the
  Claude Console and verify it before resuming work.
- Admin API calls are management-plane: they bill no inference tokens.
- ``--rotation-log`` overrides the log path (tests / dry runs).

Exit codes: 0 ok or dormant · 1 refused (missing ``--confirm``) ·
2 usage error · 3 Admin API / rotation-log error.

Stdlib only, Python >= 3.9.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROTATION_LOG = REPO_ROOT / "docs" / "rotation-log.md"

API_BASE = "https://api.anthropic.com"
API_KEYS_PATH = "/v1/organizations/api_keys"
ANTHROPIC_VERSION = "2023-06-01"
ADMIN_KEY_ENV = "ANTHROPIC_ADMIN_KEY"

PAGE_LIMIT = 100          # 1..1000 per docs; 100 keeps responses small
MAX_PAGES = 50            # hard safety cap on cursor pagination
HTTP_TIMEOUT_S = 30

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2
EXIT_API_ERROR = 3

VALID_REASONS = ("compromise", "suspicion", "scheduled")

# Any sk-ant-shaped substring (api, admin, oat, …) is scrubbed from every
# error/output path. Conservative: matches the documented key prefixes.
_SECRET_RE = re.compile(r"sk-ant-[A-Za-z0-9_\-]{2,}")

# (method, url, headers, body) -> (status_code, response_text)
HttpFn = Callable[[str, str, Dict[str, str], Optional[bytes]], Tuple[int, str]]


def _redact(text: Optional[str]) -> str:
    """Scrub anything sk-ant-shaped out of *text* (S206 lesson)."""
    return _SECRET_RE.sub("sk-ant-[REDACTED]", text or "")


class AdminApiError(RuntimeError):
    """Sanitized Admin API failure — message is pre-redacted, never carries
    headers, the request object, or the admin key."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(_redact(detail))
        self.status = status


def _default_http(
    method: str, url: str, headers: Dict[str, str], body: Optional[bytes]
) -> Tuple[int, str]:
    """Default urllib transport. Errors are converted to AdminApiError with a
    redacted body excerpt — the raw urllib exception (which can embed request
    state in its repr/trace) is NEVER propagated (S206 lesson)."""
    req = urllib.request.Request(url, data=body, method=method)
    for key, value in headers.items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
            return resp.getcode(), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:500]
        except Exception:  # pragma: no cover - read() failure is best-effort
            detail = ""
        raise AdminApiError(exc.code, detail or "HTTP error") from None
    except urllib.error.URLError as exc:
        raise AdminApiError(0, str(getattr(exc, "reason", exc))) from None


def _admin_key() -> Optional[str]:
    """The admin key comes from the environment ONLY — never argv."""
    value = os.environ.get(ADMIN_KEY_ENV, "").strip()
    return value or None


def _headers(admin_key: str, *, with_body: bool = False) -> Dict[str, str]:
    headers = {
        "x-api-key": admin_key,
        "anthropic-version": ANTHROPIC_VERSION,
    }
    if with_body:
        headers["content-type"] = "application/json"
    return headers


def list_keys(
    http: HttpFn,
    admin_key: str,
    *,
    status: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Cursor-paginated GET /v1/organizations/api_keys."""
    keys: List[Dict[str, Any]] = []
    after_id: Optional[str] = None
    for _page in range(MAX_PAGES):
        params: Dict[str, str] = {"limit": str(PAGE_LIMIT)}
        if status:
            params["status"] = status
        if workspace_id:
            params["workspace_id"] = workspace_id
        if after_id:
            params["after_id"] = after_id
        url = "{}{}?{}".format(API_BASE, API_KEYS_PATH, urllib.parse.urlencode(params))
        code, text = http("GET", url, _headers(admin_key), None)
        if code != 200:
            raise AdminApiError(code, text[:500])
        try:
            payload = json.loads(text)
        except ValueError:
            raise AdminApiError(code, "non-JSON response from Admin API") from None
        keys.extend(payload.get("data") or [])
        if not payload.get("has_more"):
            break
        after_id = payload.get("last_id")
        if not after_id:
            break
    return keys


def deactivate_key(http: HttpFn, admin_key: str, key_id: str) -> Dict[str, Any]:
    """POST /v1/organizations/api_keys/{id} with {"status": "inactive"}."""
    url = "{}{}/{}".format(API_BASE, API_KEYS_PATH, urllib.parse.quote(key_id, safe=""))
    body = json.dumps({"status": "inactive"}).encode("utf-8")
    code, text = http("POST", url, _headers(admin_key, with_body=True), body)
    if code != 200:
        raise AdminApiError(code, text[:500])
    try:
        return json.loads(text)
    except ValueError:
        raise AdminApiError(code, "non-JSON response from Admin API") from None


def build_rotation_row(
    *,
    reason: str,
    rotated_by: str,
    notes: str,
    today: Optional[str] = None,
) -> str:
    """One Log-table row in the documented rotation-log format.

    Notes must already be free of key material — callers pass key IDs and
    names only (never values, never partial hints). Pipes are stripped so a
    note cannot break the markdown table shape.
    """
    date = today or _dt.date.today().isoformat()
    safe_notes = _redact(notes).replace("|", "/").replace("\n", " ").strip()
    safe_by = _redact(rotated_by).replace("|", "/").strip() or "owner"
    return "| {} | ANTHROPIC_API_KEY | {} | {} | ok | {} |".format(
        date, reason, safe_by, safe_notes
    )


def append_rotation_entry(
    log_path: Path,
    row: str,
) -> None:
    """Append *row* after the last contiguous table row under '## Log'.

    Raises AdminApiError(0, …) when the documented structure is missing so
    callers can surface the pre-formatted row for a manual paste instead of
    silently losing the audit pair.
    """
    try:
        text = log_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AdminApiError(0, "rotation log unreadable: {}".format(exc)) from None
    lines = text.splitlines()
    heading_idx = None
    for idx, line in enumerate(lines):
        if line.strip() == "## Log":
            heading_idx = idx
            break
    if heading_idx is None:
        raise AdminApiError(0, "rotation log has no '## Log' heading")
    # First table line after the heading…
    table_start = None
    for idx in range(heading_idx + 1, len(lines)):
        if lines[idx].lstrip().startswith("|"):
            table_start = idx
            break
        if lines[idx].startswith("## "):
            break
    if table_start is None:
        raise AdminApiError(0, "rotation log '## Log' section has no table")
    # …then the last contiguous table line.
    table_end = table_start
    for idx in range(table_start + 1, len(lines)):
        if lines[idx].lstrip().startswith("|"):
            table_end = idx
        else:
            break
    lines.insert(table_end + 1, row)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _audit_emit(operation: str, **fields: Any) -> None:
    """Best-effort closed-enum audit emit — NEVER blocks key hygiene.

    Action ``admin_key_lifecycle_event`` is declared in the PLAN-135 W5
    actions ledger; until it lands in ``_KNOWN_ACTIONS`` the emit is a
    silent no-op breadcrumb inside emit_generic. Any import/runtime
    failure is swallowed (fail-soft per ADR-005).
    """
    try:
        hooks_dir = str(REPO_ROOT / ".claude" / "hooks")
        if hooks_dir not in sys.path:
            sys.path.insert(0, hooks_dir)
        from _lib import audit_emit  # type: ignore[import-not-found]

        audit_emit.emit_generic("admin_key_lifecycle_event", operation=operation, **fields)
    except Exception:
        pass


def _key_label(key: Dict[str, Any]) -> str:
    """id(name) label for log notes — IDs and names only, never key material."""
    return "{}({})".format(key.get("id", "?"), key.get("name", "?"))


def _print_dormant() -> int:
    print(
        "DORMANT: {} not set — no Admin API access; nothing done.\n"
        "Provision an org Admin API key (Console -> Settings -> API keys, admin\n"
        "role required) and export it for this command only; custody per\n"
        "ADR-054-AMEND-1 (OS keychain / Owner launch env; NEVER repo/CI).".format(
            ADMIN_KEY_ENV
        )
    )
    return EXIT_OK


def cmd_list(args: argparse.Namespace, http: HttpFn) -> int:
    admin_key = _admin_key()
    if admin_key is None:
        return _print_dormant()
    keys = list_keys(
        http, admin_key, status=args.status, workspace_id=args.workspace_id
    )
    if args.json:
        print(json.dumps({"count": len(keys), "data": keys}, indent=2, sort_keys=True))
    else:
        print("{} key(s)".format(len(keys)))
        for key in keys:
            print(
                "  {:<32} {:<10} {:<24} {}".format(
                    str(key.get("id", "?")),
                    str(key.get("status", "?")),
                    str(key.get("partial_key_hint", "")),
                    str(key.get("name", "?")),
                )
            )
    _audit_emit("list", key_count=len(keys))
    return EXIT_OK


def cmd_deactivate(args: argparse.Namespace, http: HttpFn) -> int:
    if not args.confirm:
        print(
            "REFUSED: deactivate is a mutation — re-run with explicit --confirm.\n"
            "Would deactivate: {} (no network I/O performed).".format(args.key_id)
        )
        return EXIT_REFUSED
    admin_key = _admin_key()
    if admin_key is None:
        return _print_dormant()
    updated = deactivate_key(http, admin_key, args.key_id)
    notes = (
        "key-hygiene.py deactivate: {} set inactive via Admin API. {}"
        "Admin API cannot CREATE keys - provision any replacement in the "
        "Console and verify before resuming."
    ).format(_key_label(updated), (args.note + " ") if args.note else "")
    row = build_rotation_row(
        reason=args.reason, rotated_by=args.rotated_by, notes=notes
    )
    _append_row_or_surface(Path(args.rotation_log), row)
    print("deactivated: {}".format(_key_label(updated)))
    print("rotation-log: appended 1 entry -> {}".format(args.rotation_log))
    _audit_emit(
        "deactivate",
        key_id=str(updated.get("id", args.key_id)),
        reason=args.reason,
        rotation_log_appended=True,
    )
    return EXIT_OK


def cmd_incident(args: argparse.Namespace, http: HttpFn) -> int:
    if not args.confirm:
        print(
            "REFUSED: incident deactivates ALL active org keys (minus\n"
            "--exclude-key-id survivors) — re-run with explicit --confirm.\n"
            "No network I/O performed."
        )
        return EXIT_REFUSED
    admin_key = _admin_key()
    if admin_key is None:
        return _print_dormant()
    excluded = set(args.exclude_key_id or [])
    active = list_keys(
        http, admin_key, status="active", workspace_id=args.workspace_id
    )
    targets = [key for key in active if key.get("id") not in excluded]
    if not targets:
        print("incident: no active keys to deactivate (excluded: {}).".format(
            len(active) - len(targets)
        ))
        return EXIT_OK
    deactivated: List[Dict[str, Any]] = []
    for key in targets:
        deactivated.append(deactivate_key(http, admin_key, str(key["id"])))
    labels = ", ".join(_key_label(key) for key in deactivated)
    notes = (
        "key-hygiene.py incident (S206 shape): deactivated {} org key(s) via "
        "Admin API: {}. Excluded survivors: {}. {}"
        "Admin API cannot CREATE keys - provision the replacement in the "
        "Console and verify before resuming."
    ).format(
        len(deactivated),
        labels,
        ", ".join(sorted(excluded)) or "none",
        (args.note + " ") if args.note else "",
    )
    row = build_rotation_row(
        reason=args.reason, rotated_by=args.rotated_by, notes=notes
    )
    _append_row_or_surface(Path(args.rotation_log), row)
    print("incident: deactivated {} key(s): {}".format(len(deactivated), labels))
    print("rotation-log: appended 1 entry -> {}".format(args.rotation_log))
    _audit_emit(
        "incident",
        key_count=len(deactivated),
        reason=args.reason,
        rotation_log_appended=True,
    )
    return EXIT_OK


def _append_row_or_surface(log_path: Path, row: str) -> None:
    """Append the audit-pair row; on failure surface it for manual paste.

    The API mutation has already happened at this point — losing the row
    silently would break the audit pair, so the row is printed verbatim
    and the error re-raised for a non-zero exit.
    """
    try:
        append_rotation_entry(log_path, row)
    except AdminApiError:
        print("WARNING: rotation-log append FAILED — paste this row manually:")
        print(row)
        raise


def _default_rotated_by() -> str:
    return (
        os.environ.get("CEO_ROTATED_BY")
        or os.environ.get("USER")
        or "owner"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="key-hygiene.py",
        description=(
            "Anthropic Admin API key hygiene (PLAN-135 W5 O9). Admin key is "
            "read from ${} ONLY — there is deliberately no CLI flag for it.".format(
                ADMIN_KEY_ENV
            )
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="read-only org API key inventory")
    p_list.add_argument(
        "--status", choices=("active", "inactive", "archived", "expired"), default=None
    )
    p_list.add_argument("--workspace-id", default=None)
    p_list.add_argument("--json", action="store_true")

    common_mut = argparse.ArgumentParser(add_help=False)
    common_mut.add_argument(
        "--confirm",
        action="store_true",
        help="explicit Owner confirmation — REQUIRED for any mutation",
    )
    common_mut.add_argument(
        "--reason", choices=VALID_REASONS, default="compromise",
        help="rotation-log reason column (default: compromise)",
    )
    common_mut.add_argument(
        "--rotated-by", default=_default_rotated_by(),
        help="rotation-log rotated_by column (default: $CEO_ROTATED_BY or $USER)",
    )
    common_mut.add_argument(
        "--note", default="", help="extra free text for the rotation-log notes column"
    )
    common_mut.add_argument(
        "--rotation-log", default=str(DEFAULT_ROTATION_LOG),
        help="rotation log path (default: docs/rotation-log.md)",
    )

    p_deact = sub.add_parser(
        "deactivate", parents=[common_mut], help="deactivate ONE key (+ log entry)"
    )
    p_deact.add_argument("--key-id", required=True, help="apikey_… id to deactivate")

    p_inc = sub.add_parser(
        "incident",
        parents=[common_mut],
        help="S206 one-command response: deactivate ALL active keys (+ ONE log entry)",
    )
    p_inc.add_argument(
        "--exclude-key-id", action="append", default=[],
        help="apikey_… id to KEEP active (repeatable; e.g. the fresh replacement)",
    )
    p_inc.add_argument("--workspace-id", default=None)

    return parser


def main(argv: Optional[List[str]] = None, http: Optional[HttpFn] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return EXIT_USAGE if exc.code not in (0, None) else EXIT_OK
    transport: HttpFn = http or _default_http
    handlers = {
        "list": cmd_list,
        "deactivate": cmd_deactivate,
        "incident": cmd_incident,
    }
    try:
        return handlers[args.command](args, transport)
    except AdminApiError as exc:
        print(
            "ERROR: Admin API call failed (status={}): {}".format(
                exc.status, _redact(str(exc))
            ),
            file=sys.stderr,
        )
        return EXIT_API_ERROR


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
