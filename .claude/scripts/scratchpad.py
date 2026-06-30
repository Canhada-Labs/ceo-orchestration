#!/usr/bin/env python3
"""CRUD CLI for the plan-scoped shared scratchpad.

PLAN-011 Phase 7. Thin wrapper over
:mod:`_lib.scratchpad_lib` + :mod:`_lib.state_store`. No new backend
logic — every operation funnels through the Phase 0 state store.

## Sub-commands

    scratchpad.py set <key> <value> [--ttl SECONDS] [--plan PLAN-NNN] [--json]
    scratchpad.py get <key> [--plan PLAN-NNN] [--json]
    scratchpad.py list [--plan PLAN-NNN] [--json]
    scratchpad.py delete <key> [--plan PLAN-NNN] [--json]
    scratchpad.py clear [--plan PLAN-NNN] --confirm [--json]

When ``--plan`` is omitted, the plan is derived from the audit-log
session linkage (:func:`scratchpad_lib.resolve_plan_id`). Derivation
failure exits non-zero with a clear message — there is NO fallback
env var (consensus M2).

## Kill switch (consensus S4)

``CEO_SOTA_DISABLE=1`` → every sub-command exits 0 with a "disabled"
message. Nothing is read from or written to sqlite.

## Idempotency (consensus M7)

- ``get`` / ``list`` are read-only (idempotent trivially).
- ``delete`` on a missing key → exit 3 (no-op with message), does not
  error.
- ``clear`` requires the literal ``--confirm`` flag; omitting it
  refuses with exit 2 (usage).

## Exit codes

- 0 — success / no-op / kill-switch
- 2 — usage error (missing required arg, bad flag)
- 3 — plan derivation failed OR delete-missing-key no-op
- 4 — value too large (64 KiB per-key cap breached)

## JSON mode

``--json`` switches stdout to a single-line JSON object for machine
consumers. Binary values are base64-encoded under key ``value_b64``.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


_SCRIPT_DIR = Path(__file__).resolve().parent
_HOOKS_DIR = _SCRIPT_DIR.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.scratchpad_lib import (  # noqa: E402
    PlanIdDerivationError,
    open_scratchpad,
    resolve_plan_id,
)
from _lib.state_store import (  # noqa: E402
    SqliteStateStore,
    StateStoreInvalidName,
    StateStoreValueTooLarge,
    open_store,
)


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_OP = 3
EXIT_TOO_LARGE = 4


def _sota_disabled() -> bool:
    """Return True when CEO_SOTA_DISABLE=1 (consensus S4)."""
    return os.environ.get("CEO_SOTA_DISABLE", "").strip() == "1"


def _emit(payload: Dict[str, Any], *, as_json: bool, out=None) -> None:
    """Write payload to stdout in either JSON or human-readable form."""
    stream = out if out is not None else sys.stdout
    if as_json:
        stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return

    # Human mode
    kind = payload.get("kind") or ""
    if kind == "disabled":
        stream.write("scratchpad: disabled (CEO_SOTA_DISABLE=1)\n")
    elif kind == "set":
        stream.write(
            f"set ok: plan={payload.get('plan_id')} "
            f"key={payload.get('key')} bytes={payload.get('bytes')}"
            + (f" ttl={payload['ttl_seconds']}s" if payload.get("ttl_seconds") else "")
            + "\n"
        )
    elif kind == "get":
        if payload.get("found"):
            stream.write(payload.get("value", ""))
            if not str(payload.get("value", "")).endswith("\n"):
                stream.write("\n")
        else:
            stream.write(f"get: key {payload.get('key')!r} not found\n")
    elif kind == "list":
        keys = payload.get("keys") or []
        if not keys:
            stream.write(f"(empty) plan={payload.get('plan_id')}\n")
        else:
            for k in keys:
                stream.write(f"{k}\n")
    elif kind == "delete":
        if payload.get("deleted"):
            stream.write(
                f"delete ok: plan={payload.get('plan_id')} key={payload.get('key')}\n"
            )
        else:
            stream.write(
                f"delete: key {payload.get('key')!r} not present (no-op)\n"
            )
    elif kind == "clear":
        stream.write(
            f"clear ok: plan={payload.get('plan_id')} "
            f"keys_cleared={payload.get('keys_cleared')}\n"
        )
    elif kind == "error":
        stream.write(f"error: {payload.get('message', '')}\n")
    else:
        stream.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _resolve_plan(explicit: Optional[str]) -> str:
    """Resolve the effective plan id or raise PlanIdDerivationError."""
    if explicit:
        return explicit
    return resolve_plan_id()


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------


def cmd_set(args: argparse.Namespace) -> int:
    """Handle the `scratchpad set <key> <value>` sub-command."""
    try:
        plan_id = _resolve_plan(args.plan)
    except PlanIdDerivationError as e:
        _emit({"kind": "error", "message": str(e)}, as_json=args.json)
        return EXIT_NO_OP

    ttl = args.ttl
    if ttl is not None and ttl <= 0:
        _emit(
            {"kind": "error", "message": "--ttl must be positive"},
            as_json=args.json,
        )
        return EXIT_USAGE

    try:
        with open_store("scratchpad", plan_id) as store:
            store.set(args.key, args.value, ttl_seconds=ttl)
            nbytes = len(
                args.value.encode("utf-8", errors="replace")
                if isinstance(args.value, str)
                else args.value
            )
    except StateStoreValueTooLarge as e:
        _emit({"kind": "error", "message": str(e)}, as_json=args.json)
        return EXIT_TOO_LARGE
    except StateStoreInvalidName as e:
        _emit({"kind": "error", "message": str(e)}, as_json=args.json)
        return EXIT_USAGE

    _emit(
        {
            "kind": "set",
            "plan_id": plan_id,
            "key": args.key,
            "bytes": nbytes,
            "ttl_seconds": ttl,
        },
        as_json=args.json,
    )
    return EXIT_OK


def cmd_get(args: argparse.Namespace) -> int:
    """Handle the `scratchpad get <key>` sub-command — read a shared-memory value."""
    try:
        plan_id = _resolve_plan(args.plan)
    except PlanIdDerivationError as e:
        _emit({"kind": "error", "message": str(e)}, as_json=args.json)
        return EXIT_NO_OP

    try:
        with open_store("scratchpad", plan_id) as store:
            raw = store.get(args.key)
    except StateStoreInvalidName as e:
        _emit({"kind": "error", "message": str(e)}, as_json=args.json)
        return EXIT_USAGE

    if raw is None:
        _emit(
            {
                "kind": "get",
                "plan_id": plan_id,
                "key": args.key,
                "found": False,
            },
            as_json=args.json,
        )
        return EXIT_OK

    payload: Dict[str, Any] = {
        "kind": "get",
        "plan_id": plan_id,
        "key": args.key,
        "found": True,
        "bytes": len(raw),
    }
    # Attempt UTF-8 decode; fall back to base64 for binary values.
    try:
        decoded = raw.decode("utf-8")
        payload["value"] = decoded
    except UnicodeDecodeError:
        payload["value_b64"] = base64.b64encode(raw).decode("ascii")
    _emit(payload, as_json=args.json)
    return EXIT_OK


def cmd_list(args: argparse.Namespace) -> int:
    """Handle the `scratchpad list` sub-command — enumerate scratchpad keys."""
    try:
        plan_id = _resolve_plan(args.plan)
    except PlanIdDerivationError as e:
        _emit({"kind": "error", "message": str(e)}, as_json=args.json)
        return EXIT_NO_OP

    try:
        with open_store("scratchpad", plan_id) as store:
            keys: List[str] = store.list_keys(include_expired=False)
    except StateStoreInvalidName as e:
        _emit({"kind": "error", "message": str(e)}, as_json=args.json)
        return EXIT_USAGE

    _emit(
        {"kind": "list", "plan_id": plan_id, "keys": keys, "count": len(keys)},
        as_json=args.json,
    )
    return EXIT_OK


def cmd_delete(args: argparse.Namespace) -> int:
    """Handle the `scratchpad delete <key>` sub-command."""
    try:
        plan_id = _resolve_plan(args.plan)
    except PlanIdDerivationError as e:
        _emit({"kind": "error", "message": str(e)}, as_json=args.json)
        return EXIT_NO_OP

    try:
        with open_store("scratchpad", plan_id) as store:
            deleted = store.delete(args.key)
    except StateStoreInvalidName as e:
        _emit({"kind": "error", "message": str(e)}, as_json=args.json)
        return EXIT_USAGE

    _emit(
        {
            "kind": "delete",
            "plan_id": plan_id,
            "key": args.key,
            "deleted": deleted,
        },
        as_json=args.json,
    )
    return EXIT_OK if deleted else EXIT_NO_OP


def cmd_clear(args: argparse.Namespace) -> int:
    """Handle the `scratchpad clear` sub-command — wipe a plan's shared memory."""
    if not args.confirm:
        _emit(
            {
                "kind": "error",
                "message": "clear refuses without --confirm (safety interlock)",
            },
            as_json=args.json,
        )
        return EXIT_USAGE

    try:
        plan_id = _resolve_plan(args.plan)
    except PlanIdDerivationError as e:
        _emit({"kind": "error", "message": str(e)}, as_json=args.json)
        return EXIT_NO_OP

    try:
        with open_store("scratchpad", plan_id) as store:
            cleared = store.clear_plan()
    except StateStoreInvalidName as e:
        _emit({"kind": "error", "message": str(e)}, as_json=args.json)
        return EXIT_USAGE

    _emit(
        {"kind": "clear", "plan_id": plan_id, "keys_cleared": cleared},
        as_json=args.json,
    )
    return EXIT_OK


# ---------------------------------------------------------------------------
# Argparse wiring
# ---------------------------------------------------------------------------


def _add_plan_flag(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--plan",
        default=None,
        help="PLAN-NNN scope override. If omitted, derive from audit-log session.",
    )


def _add_json_flag(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Emit a single-line JSON payload on stdout.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the scratchpad CLI."""
    parser = argparse.ArgumentParser(
        prog="scratchpad.py",
        description=(
            "Plan-scoped shared scratchpad for inter-agent handoff. "
            "Consumes _lib/state_store.py (ADR-027) + derives plan-id "
            "from audit-log session linkage (consensus M2)."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", metavar="<command>")

    p_set = sub.add_parser("set", help="Write a key/value.")
    p_set.add_argument("key")
    p_set.add_argument("value")
    p_set.add_argument(
        "--ttl",
        type=int,
        default=None,
        help="TTL in seconds (positive int). Omit for no-expiry.",
    )
    _add_plan_flag(p_set)
    _add_json_flag(p_set)

    p_get = sub.add_parser("get", help="Read a key.")
    p_get.add_argument("key")
    _add_plan_flag(p_get)
    _add_json_flag(p_get)

    p_list = sub.add_parser("list", help="List non-expired keys.")
    _add_plan_flag(p_list)
    _add_json_flag(p_list)

    p_del = sub.add_parser("delete", help="Delete a key.")
    p_del.add_argument("key")
    _add_plan_flag(p_del)
    _add_json_flag(p_del)

    p_clr = sub.add_parser(
        "clear", help="Drop every key for the plan (requires --confirm)."
    )
    p_clr.add_argument(
        "--confirm",
        action="store_true",
        default=False,
        help="Safety interlock — clear refuses without this flag.",
    )
    _add_plan_flag(p_clr)
    _add_json_flag(p_clr)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — dispatch scratchpad sub-commands (read/write/list/clear/delete)."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # S4 kill switch — bypass sqlite entirely.
    if _sota_disabled():
        _emit(
            {"kind": "disabled", "reason": "CEO_SOTA_DISABLE=1"},
            as_json=getattr(args, "json", False),
        )
        return EXIT_OK

    if args.cmd is None:
        parser.print_help(sys.stderr)
        return EXIT_USAGE

    dispatch = {
        "set": cmd_set,
        "get": cmd_get,
        "list": cmd_list,
        "delete": cmd_delete,
        "clear": cmd_clear,
    }
    handler = dispatch.get(args.cmd)
    if handler is None:  # pragma: no cover — argparse enforces
        parser.print_help(sys.stderr)
        return EXIT_USAGE
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
