#!/usr/bin/env python3
"""PLAN-099-FOLLOWUP Wave B.3 — peers.yaml v1.x -> v2.0 migration tool.

Per ``peers-yaml-schema-migration.md`` §5 contract. Stdlib-only.

The tool reads a v1.x ``peers.yaml`` (DER-only fingerprints, no scopes,
no key_floor_verified_at) and emits a v2.0 file with:

- ``peer_id_spki_fingerprint`` populated from cert inspection
  (rotation-survives primary pin)
- ``peer_id_cert_fingerprint`` preserved verbatim (90d soak backward-
  compat per ADR-129-AMEND-1 §3)
- ``scopes: []`` (default empty -- read-only, principle-of-least-priv;
  Owner edits per-peer post-migration)
- ``key_floor_verified_at`` set to current UTC ISO-8601 timestamp
  (or ``"unknown"`` under ``--skip-cert-inspect``)

Idempotency: re-running on a pure-v2.0 file (every row already has
SPKI + scopes + key_floor_verified_at) is a **byte-identical
short-circuit** — the tool emits the input bytes verbatim without
re-rendering the header. Mixed inputs (some v1.x + some v2.0 rows)
preserve v2.0 rows in place while migrating the v1.x rows; the output
will not be byte-identical to the input in that case (the v1.x rows
gain new fields + the canonical header is re-rendered).

Fail-loud (abort, no files written): if cert_inspector.inspect()
fails on ANY peer AND ``--skip-cert-inspect`` is not set, the tool
aborts with an explicit per-peer error and leaves the output file
untouched (atomic). Also aborts (F-003) when a peer carries a
``peer_id_cert_fingerprint`` whose DER SHA-256 differs from what
``cert_inspector`` computes for the cert on disk.

Sidecar advisory (F-004, migration continues): peers whose cert fails
``cert_inspector.enforce_key_floor()`` produce an advisory file
``<peer-id>.floor-fail`` next to the output ``peers.yaml`` and a
warning on stderr. The migrated row is still written.

Exit codes:
    0 = success
    1 = generic error (I/O / argv / cert_inspector failure)
    6 = v1.x schema corrupt (parse error / missing required field)
    7 = v2.0 conformance failure (under --verify-only)

Usage:
    python3 tools/migrate-peers-yaml.py \\
        --in .claude/data/federation/peers.yaml \\
        --out .claude/data/federation/peers.yaml.v2 \\
        --cert-dir .claude/data/federation/certs/
    python3 tools/migrate-peers-yaml.py --in PATH --out PATH --dry-run
    python3 tools/migrate-peers-yaml.py --in PATH --out PATH --skip-cert-inspect
    python3 tools/migrate-peers-yaml.py --verify-only --in PATH

Stdlib-only constraint: no ``import yaml``. Uses minimal hand-rolled
YAML parser (subset matching peers.yaml shape). Mirrors the pattern
used in ``.claude/hooks/_lib/federation/identity.py:load_peers``.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Exit codes (stable; do not renumber)
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_GENERIC = 1
EXIT_SCHEMA_CORRUPT = 6
EXIT_CONFORMANCE_FAIL = 7


# ---------------------------------------------------------------------------
# Schema field sets (v1.x + v2.0)
# ---------------------------------------------------------------------------

# v1.x required fields (per PLAN-099 v1.32.0 ship)
_V1_REQUIRED = (
    "peer_id",
    "peer_id_cert_fingerprint",
    "ca_pin_sha256",
    "not_valid_after",
    "not_valid_before",
    "revoked",
    "hmac_secret_hex",
)

# v2.0 added fields (per peers-yaml-schema-migration.md §2.1)
_V2_ADDED_FIELDS = (
    "peer_id_spki_fingerprint",
    "scopes",
    "key_floor_verified_at",
)

# Locked RBAC scopes (4 routes; ADR-135-AMEND-1 §2.1)
_VALID_SCOPES = frozenset({
    "peer_register",
    "audit_event_push",
    "audit_event_push_batch",
    "peer_revoke",
})

# Regex sanity gates (mirror federation/identity.py)
_PEER_FPR_RE = re.compile(r"^[0-9a-f]{64}$")
_PEER_ID_RE = re.compile(r"^[A-Za-z0-9_\-.]{1,64}$")


# ---------------------------------------------------------------------------
# Minimal YAML parser (subset peers.yaml uses)
#
# Supports:
#   peers:
#     - key: value
#       key: "quoted value"
#       list_key:
#         - item1
#         - item2
#       bool_key: true|false
#
# Comment-strip + quote-strip identical to federation/identity.py.
# ---------------------------------------------------------------------------


class PeersYamlParseError(Exception):
    """Raised on v1.x/v2.0 schema parse failure."""


def _strip_comment(line: str) -> str:
    out: List[str] = []
    in_s = False
    in_d = False
    for ch in line:
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif ch == "#" and not in_s and not in_d:
            break
        out.append(ch)
    return "".join(out).rstrip()


def _unquote(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and (
        (v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")
    ):
        return v[1:-1]
    return v


def _parse_bool(v: str) -> bool:
    s = _unquote(v).strip().lower()
    if s in ("true", "yes", "on"):
        return True
    if s in ("false", "no", "off", ""):
        return False
    raise PeersYamlParseError("not a bool: {0!r}".format(v))


def parse_peers_yaml(text: str) -> List[Dict[str, Any]]:
    """Parse peers.yaml text into a list of peer dicts.

    Each peer dict may contain string values (most fields), a list
    value (for ``scopes``), or a bool (for ``revoked``).

    The parser preserves the *original* string form for fingerprints +
    timestamps so re-emit is round-trip-safe.
    """
    peers_raw: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    in_peers = False
    list_item_indent: Optional[int] = None

    # Tracking nested-list state (for `scopes:` sub-list)
    nested_list_key: Optional[str] = None
    nested_list_indent: Optional[int] = None

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = _strip_comment(raw_line)
        if not line.strip():
            continue

        if line.startswith("peers:") and not line.strip().startswith("- "):
            in_peers = True
            continue

        if not in_peers:
            continue

        # Nested list-item (e.g. under `scopes:`)
        if nested_list_key is not None and nested_list_indent is not None:
            m_nested = re.match(r"^(\s*)-\s+(.*)$", line)
            if m_nested:
                ind = len(m_nested.group(1))
                if ind == nested_list_indent and current is not None:
                    val = _unquote(m_nested.group(2).strip())
                    cur_list = current.setdefault(nested_list_key, [])
                    if not isinstance(cur_list, list):
                        raise PeersYamlParseError(
                            "line {0}: expected list for {1!r}".format(
                                lineno, nested_list_key
                            )
                        )
                    cur_list.append(val)
                    continue
            # End of nested list when indent backs out OR new peer item
            # starts. Fall through to the top-level item / kv handling.
            nested_list_key = None
            nested_list_indent = None

        # Top-level list item (a peer row)
        item_match = re.match(r"^(\s*)-\s+(.*)$", line)
        if item_match and (
            list_item_indent is None
            or len(item_match.group(1)) == list_item_indent
        ):
            indent = len(item_match.group(1))
            if list_item_indent is None:
                list_item_indent = indent
            elif indent != list_item_indent:
                raise PeersYamlParseError(
                    "list-item indent drift at line {0}".format(lineno)
                )
            current = {}
            peers_raw.append(current)
            inner = item_match.group(2)
            if ":" in inner:
                k, _, v = inner.partition(":")
                k = k.strip()
                if not k:
                    raise PeersYamlParseError(
                        "empty key on list-item line {0}".format(lineno)
                    )
                v_strip = v.strip()
                # If `inner` is e.g. `scopes:` with NO value, treat as
                # nested-list opener.
                if v_strip == "":
                    nested_list_key = k
                    nested_list_indent = indent + 4  # convention
                    current[k] = []
                elif v_strip == "[]":
                    current[k] = []
                elif v_strip.lower() in ("true", "false") and k == "revoked":
                    current[k] = (v_strip.lower() == "true")
                else:
                    current[k] = _unquote(v_strip)
            continue

        # Field on current peer ("  key: value" past list_item indent)
        kv_match = re.match(
            r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$", line
        )
        if (
            kv_match
            and current is not None
            and list_item_indent is not None
        ):
            key_indent = len(kv_match.group(1))
            if key_indent <= list_item_indent:
                raise PeersYamlParseError(
                    "line {0} not indented past list marker".format(lineno)
                )
            key = kv_match.group(2)
            value = kv_match.group(3).strip()
            if value == "":
                # Opening a nested list (e.g. scopes:)
                nested_list_key = key
                # The nested-list items are indented one level past the
                # key. Use key_indent + 2 as the floor (any deeper
                # indent works because nested-list match uses ==).
                # To be tolerant, sniff next non-empty line at runtime.
                nested_list_indent = key_indent + 2
                current[key] = []
            elif value == "[]":
                # Inline empty list (e.g. `scopes: []`)
                current[key] = []
            elif value.lower() in ("true", "false") and key == "revoked":
                # Native bool for revoked field.
                current[key] = (value.lower() == "true")
            else:
                current[key] = _unquote(value)
            continue

        raise PeersYamlParseError(
            "unparseable line {0}: {1!r}".format(lineno, raw_line)
        )

    return peers_raw


# ---------------------------------------------------------------------------
# Emitter (deterministic v2.0 output)
# ---------------------------------------------------------------------------

# Canonical key order in v2.0 output (per peers.example.yaml row C/B
# shape). Keys not in this list are written after the listed ones in
# insertion order.
_V2_KEY_ORDER = (
    "peer_id",
    "peer_id_spki_fingerprint",
    "peer_id_cert_fingerprint",
    "ca_pin_sha256",
    "not_valid_after",
    "not_valid_before",
    "revoked",
    "hmac_secret_hex",
    "scopes",
    "key_floor_verified_at",
)


def _emit_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "\"\""
    s = str(value)
    # Always quote string scalars for parser idempotency (ISO timestamps
    # contain `:` which is a YAML mapping char). Booleans + lists are
    # handled elsewhere.
    return "\"{0}\"".format(s.replace("\\", "\\\\").replace("\"", "\\\""))


def emit_peers_yaml(peers: List[Dict[str, Any]], header: Optional[str] = None) -> str:
    """Emit a list of peer dicts as v2.0 YAML text.

    The output is deterministic: keys are written in ``_V2_KEY_ORDER``
    where present; lists are emitted as nested `-` items.
    """
    lines: List[str] = []
    if header:
        for hl in header.splitlines():
            lines.append("# " + hl if hl else "#")
        lines.append("")
    lines.append("peers:")

    for peer in peers:
        # Compute key order: canonical first, then any extras.
        keys_canonical = [k for k in _V2_KEY_ORDER if k in peer]
        keys_extra = [k for k in peer.keys() if k not in _V2_KEY_ORDER]
        all_keys = keys_canonical + keys_extra

        first = True
        for k in all_keys:
            v = peer[k]
            if first:
                prefix = "  - "
                first = False
            else:
                prefix = "    "
            if isinstance(v, list):
                if not v:
                    lines.append("{0}{1}: []".format(prefix, k))
                else:
                    lines.append("{0}{1}:".format(prefix, k))
                    for item in v:
                        lines.append("      - \"{0}\"".format(item))
            else:
                lines.append("{0}{1}: {2}".format(prefix, k, _emit_scalar(v)))
        lines.append("")  # blank between peers
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# cert_inspector lazy import (avoid hard dep when --skip-cert-inspect)
# ---------------------------------------------------------------------------


def _import_cert_inspector():
    """Import cert_inspector from .claude/hooks/_lib/federation/.

    Falls back to the PLAN-099-FOLLOWUP staging path (pre-`git mv`)
    when the canonical landing path is absent.
    """
    repo_root = _find_repo_root()
    candidates = [
        os.path.join(repo_root, ".claude", "hooks", "_lib"),
    ]
    # Staging fallback: bridge file is at
    # .claude/plans/PLAN-099-FOLLOWUP/cert_inspector.py
    staging_path = os.path.join(
        repo_root, ".claude", "plans", "PLAN-099-FOLLOWUP"
    )
    staging_bridge = os.path.join(staging_path, "cert_inspector.py")
    canonical_bridge = os.path.join(
        repo_root, ".claude", "hooks", "_lib", "federation", "cert_inspector.py"
    )

    if os.path.isfile(canonical_bridge):
        # Standard import path: from federation import cert_inspector
        for c in candidates:
            if c not in sys.path:
                sys.path.insert(0, c)
        from federation import cert_inspector  # type: ignore
        return cert_inspector

    if os.path.isfile(staging_bridge):
        # Direct import from staging file by spec loader
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "cert_inspector_staging", staging_bridge
        )
        if spec is None or spec.loader is None:
            raise ImportError(
                "could not load staging cert_inspector at " + staging_bridge
            )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    raise ImportError(
        "cert_inspector not found at canonical or staging path "
        "(canonical: {0}, staging: {1})".format(canonical_bridge, staging_bridge)
    )


def _find_repo_root() -> str:
    """Walk up from this file until we hit a `.git` dir."""
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(8):
        if os.path.isdir(os.path.join(here, ".git")):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    # Last-resort: current working directory.
    return os.getcwd()


# ---------------------------------------------------------------------------
# Migration core
# ---------------------------------------------------------------------------


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _validate_v1_schema(peers: List[Dict[str, Any]]) -> None:
    """Confirm every row has v1.x required fields. Raise on violation."""
    for idx, peer in enumerate(peers):
        for fld in _V1_REQUIRED:
            if fld not in peer or (
                isinstance(peer[fld], str) and not peer[fld].strip()
            ):
                # `revoked` may legitimately be "false" (empty after
                # `_unquote` returns "false"). Allow that case.
                if fld == "revoked" and "revoked" in peer:
                    continue
                raise PeersYamlParseError(
                    "peers[{0}]: missing required v1.x field {1!r}".format(
                        idx, fld
                    )
                )


def _row_is_already_v2(row: Dict[str, Any]) -> bool:
    """A row is v2.0 when it has SPKI fpr AND scopes list AND verified_at."""
    return (
        "peer_id_spki_fingerprint" in row
        and "scopes" in row
        and "key_floor_verified_at" in row
    )


def migrate_one(
    row: Dict[str, Any],
    cert_dir: Optional[str],
    cert_inspector_mod: Optional[Any],
    skip_cert_inspect: bool,
    idempotent_now: Optional[str] = None,
    floor_warnings_sink: Optional[List[Tuple[str, str]]] = None,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Migrate a single v1.x row -> v2.0. Returns (new_row, err_or_None).

    If ``row`` is already v2.0, return it untouched (idempotent path).

    F-003 — when ``cert_dir`` is provided AND the row carries a non-empty
    ``peer_id_cert_fingerprint``, the DER SHA-256 reported by
    ``cert_inspector.inspect()`` MUST match the legacy fingerprint byte-
    for-byte. Mismatch aborts (caller writes nothing).

    F-004 — when ``cert_dir`` is provided AND ``cert_inspector_mod``
    exposes ``enforce_key_floor``, the floor is enforced per peer. On
    floor failure a tuple ``(peer_id, reason)`` is appended to
    ``floor_warnings_sink`` (when supplied) and migration *continues*
    for that row (sidecar advisory model, NOT an abort).
    """
    if _row_is_already_v2(row):
        # Idempotency — preserve as-is.
        return row, None

    peer_id = str(row.get("peer_id", "")).strip()
    if not _PEER_ID_RE.match(peer_id):
        return row, "invalid peer_id: {0!r}".format(peer_id)

    new_row: Dict[str, Any] = dict(row)  # shallow copy

    # SPKI computation path
    if skip_cert_inspect or cert_inspector_mod is None:
        new_row["peer_id_spki_fingerprint"] = ""
        new_row["key_floor_verified_at"] = "unknown"
    else:
        if not cert_dir:
            return row, (
                "cert_dir required when --skip-cert-inspect not set "
                "(peer {0})".format(peer_id)
            )
        cert_path = os.path.join(cert_dir, peer_id + ".pem")
        if not os.path.isfile(cert_path):
            return row, "cert file not found: {0}".format(cert_path)
        try:
            rep = cert_inspector_mod.inspect(cert_path=cert_path)
        except Exception as exc:
            return row, "cert_inspector failed on {0}: {1}".format(
                peer_id, exc
            )
        spki = rep.get("spki_sha256", "")
        if not (isinstance(spki, str) and _PEER_FPR_RE.match(spki)):
            return row, (
                "cert_inspector returned malformed spki_sha256 for {0}: "
                "{1!r}".format(peer_id, spki)
            )

        # F-003 — DER pin match enforcement. When the row carries a
        # legacy peer_id_cert_fingerprint, compare it against the
        # inspected DER SHA-256. Mismatch aborts before render/write.
        legacy_der = str(row.get("peer_id_cert_fingerprint", "") or "").strip().lower()
        if legacy_der:
            inspected_der = str(rep.get("der_sha256", "") or "").strip().lower()
            if not _PEER_FPR_RE.match(inspected_der):
                return row, (
                    "cert_inspector returned malformed der_sha256 for {0}: "
                    "{1!r}".format(peer_id, rep.get("der_sha256"))
                )
            if inspected_der != legacy_der:
                return row, (
                    "DER pin mismatch for peer {0}: peers.yaml has {1} "
                    "but cert at {2} hashes to {3}".format(
                        peer_id, legacy_der, cert_path, inspected_der
                    )
                )

        # F-004 — key-floor enforcement. Best-effort sidecar advisory;
        # never aborts migration. Floor failures land in
        # floor_warnings_sink for the caller to emit per-peer
        # `<peer-id>.floor-fail` sidecar files.
        enforce_fn = getattr(cert_inspector_mod, "enforce_key_floor", None)
        if enforce_fn is not None and floor_warnings_sink is not None:
            try:
                ok, reason = enforce_fn(rep)
            except Exception as exc:
                # Treat enforcement errors as advisory only; do not
                # block migration.
                ok = False
                reason = "enforce_key_floor raised: {0}".format(exc)
            if not ok:
                floor_warnings_sink.append((peer_id, str(reason)))

        new_row["peer_id_spki_fingerprint"] = spki
        new_row["key_floor_verified_at"] = idempotent_now or _now_utc_iso()

    # Default empty scopes (read-only / principle-of-least-priv)
    new_row.setdefault("scopes", [])

    return new_row, None


def migrate_peers(
    peers_v1: List[Dict[str, Any]],
    cert_dir: Optional[str],
    skip_cert_inspect: bool = False,
) -> Tuple[List[Dict[str, Any]], List[str], List[Tuple[str, str]]]:
    """Migrate a list of v1.x rows -> v2.0.

    Returns ``(peers_v2, errors, floor_warnings)`` where:

    - ``peers_v2`` — migrated rows (or originals untouched on error)
    - ``errors`` — per-peer fatal error strings; non-empty triggers
      ABORT (no files written). Empty on full success.
    - ``floor_warnings`` — list of ``(peer_id, reason)`` tuples for
      peers that failed the key floor (F-004). Migration continues for
      these rows; the caller emits sidecar advisory files. Empty list
      when ``--skip-cert-inspect`` is set or the inspector module does
      not expose ``enforce_key_floor``.
    """
    cert_inspector_mod: Optional[Any] = None
    if not skip_cert_inspect:
        try:
            cert_inspector_mod = _import_cert_inspector()
        except ImportError as exc:
            return [], ["cannot import cert_inspector: {0}".format(exc)], []

    # Use a single timestamp across the whole run (deterministic + makes
    # diffs sensible).
    now_iso = _now_utc_iso()

    out: List[Dict[str, Any]] = []
    errors: List[str] = []
    floor_warnings: List[Tuple[str, str]] = []
    for row in peers_v1:
        new_row, err = migrate_one(
            row,
            cert_dir,
            cert_inspector_mod,
            skip_cert_inspect,
            idempotent_now=now_iso,
            floor_warnings_sink=floor_warnings,
        )
        if err:
            errors.append(err)
        out.append(new_row)
    return out, errors, floor_warnings


# ---------------------------------------------------------------------------
# v2.0 conformance check (--verify-only)
# ---------------------------------------------------------------------------


def verify_v2_conformance(peers: List[Dict[str, Any]]) -> List[str]:
    """Return list of v2.0 conformance violations (empty = OK)."""
    errors: List[str] = []
    for idx, row in enumerate(peers):
        # AT LEAST ONE of SPKI or DER must be non-empty.
        spki = str(row.get("peer_id_spki_fingerprint", "") or "").strip()
        der = str(row.get("peer_id_cert_fingerprint", "") or "").strip()
        if not spki and not der:
            errors.append(
                "peers[{0}]: missing both peer_id_spki_fingerprint "
                "and peer_id_cert_fingerprint".format(idx)
            )

        # scopes must be a list (may be empty).
        scopes = row.get("scopes")
        if scopes is None:
            errors.append("peers[{0}]: scopes field missing".format(idx))
        elif not isinstance(scopes, list):
            errors.append(
                "peers[{0}]: scopes must be a list, got {1}".format(
                    idx, type(scopes).__name__
                )
            )
        else:
            for s in scopes:
                if s not in _VALID_SCOPES:
                    errors.append(
                        "peers[{0}]: invalid scope {1!r} (not in "
                        "RBAC matrix)".format(idx, s)
                    )

        # key_floor_verified_at: required UNLESS row is legacy v1.x
        # (only DER pinned, no SPKI). For migration tool conformance
        # purposes we accept "unknown" as a valid sentinel.
        kfv = row.get("key_floor_verified_at")
        if spki:
            if kfv is None or (isinstance(kfv, str) and not kfv.strip()):
                errors.append(
                    "peers[{0}]: key_floor_verified_at required when "
                    "peer_id_spki_fingerprint is set".format(idx)
                )

    return errors


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------


def atomic_write(path: str, content: str) -> None:
    """Write `content` to `path` atomically (tmpfile + fsync + rename)."""
    parent = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(
        prefix=".migrate-peers-", suffix=".tmp", dir=parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.rename(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Diff (--dry-run output)
# ---------------------------------------------------------------------------


def render_diff(
    peers_in: List[Dict[str, Any]],
    peers_out: List[Dict[str, Any]],
) -> str:
    """Produce a human-readable per-peer added/changed report."""
    lines: List[str] = []
    for i, (a, b) in enumerate(zip(peers_in, peers_out)):
        peer_id = b.get("peer_id", "?")
        added: List[str] = []
        changed: List[str] = []
        for k in _V2_ADDED_FIELDS:
            if k not in a and k in b:
                added.append("+ {0}: {1!r}".format(k, b[k]))
            elif a.get(k) != b.get(k) and k in a:
                changed.append(
                    "~ {0}: {1!r} -> {2!r}".format(k, a.get(k), b.get(k))
                )
        if added or changed:
            lines.append("peer #{0} ({1}):".format(i, peer_id))
            for s in added:
                lines.append("  " + s)
            for s in changed:
                lines.append("  " + s)
        else:
            lines.append("peer #{0} ({1}): no changes".format(i, peer_id))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _read_file_bytes(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def _backup(src: str, backup_path: str) -> None:
    shutil.copy2(src, backup_path)


def atomic_write_bytes(path: str, content: bytes) -> None:
    """Write ``content`` bytes to ``path`` atomically (same-FS tmp + fsync + rename)."""
    parent = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(
        prefix=".migrate-peers-", suffix=".tmp", dir=parent
    )
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.rename(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _is_pure_v2(peers: List[Dict[str, Any]]) -> bool:
    """F-001 — return True iff EVERY row is already v2.0.

    A "pure v2.0" input means migrate has nothing to do — every row
    already has SPKI + scopes + key_floor_verified_at. In that case the
    tool short-circuits and emits the *exact input bytes* (no header
    regeneration, no field reorder) so v2.0 -> v2.0 is byte-identical.
    """
    if not peers:
        return False
    return all(_row_is_already_v2(r) for r in peers)


def _emit_floor_fail_sidecar(
    out_path: str,
    peer_id: str,
    reason: str,
    inspected_at: str,
) -> Optional[str]:
    """F-004 — write an advisory sidecar ``<peer-id>.floor-fail`` next to
    ``out_path``. Returns the sidecar path on success, None on I/O fail
    (logged to stderr but never aborts migration).
    """
    out_dir = os.path.dirname(os.path.abspath(out_path)) or "."
    # peer_id is regex-gated by _PEER_ID_RE so filename is safe.
    sidecar_path = os.path.join(out_dir, peer_id + ".floor-fail")
    # Stdlib-only JSON-ish body (3 fields per Wave B contract).
    body = (
        "peer_id: {0}\n"
        "reason: {1}\n"
        "inspected_at: {2}\n"
    ).format(peer_id, reason, inspected_at)
    try:
        atomic_write(sidecar_path, body)
        return sidecar_path
    except OSError as exc:
        sys.stderr.write(
            "WARN: could not write floor-fail sidecar for {0}: {1}\n".format(
                peer_id, exc
            )
        )
        return None


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="migrate-peers-yaml.py",
        description=(
            "PLAN-099-FOLLOWUP Wave B.3 — migrate peers.yaml v1.x -> v2.0. "
            "Idempotent. Stdlib-only."
        ),
    )
    ap.add_argument("--in", dest="in_path", required=True, help="input path")
    ap.add_argument(
        "--out",
        dest="out_path",
        required=False,
        default=None,
        help="output path (required unless --verify-only / --dry-run)",
    )
    ap.add_argument(
        "--cert-dir",
        dest="cert_dir",
        default=None,
        help=(
            "directory containing <peer-id>.pem certs (required unless "
            "--skip-cert-inspect or --verify-only)"
        ),
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="print proposed changes; do not write",
    )
    ap.add_argument(
        "--skip-cert-inspect",
        action="store_true",
        help=(
            "paper-only migration: leave SPKI empty + set "
            "key_floor_verified_at=\"unknown\" (no cert inspection)"
        ),
    )
    ap.add_argument(
        "--verify-only",
        action="store_true",
        help=(
            "check that --in conforms to v2.0; exit 0 if conformant, "
            "{0} otherwise; ignore --out/--cert-dir".format(EXIT_CONFORMANCE_FAIL)
        ),
    )
    ap.add_argument(
        "--backup",
        dest="backup_path",
        default=None,
        help="optional pre-write backup path (copies --in to BACKUP before --out write)",
    )
    args = ap.parse_args(argv)

    # Validate argv combinations
    if not args.verify_only:
        if not args.out_path and not args.dry_run:
            sys.stderr.write(
                "ERROR: --out required (or use --dry-run / --verify-only)\n"
            )
            return EXIT_GENERIC
        if not args.skip_cert_inspect and not args.cert_dir:
            sys.stderr.write(
                "ERROR: --cert-dir required (or use --skip-cert-inspect)\n"
            )
            return EXIT_GENERIC

    # Read input
    if not os.path.isfile(args.in_path):
        sys.stderr.write(
            "ERROR: input file not found: {0}\n".format(args.in_path)
        )
        return EXIT_GENERIC
    try:
        raw_in = _read_file(args.in_path)
    except OSError as exc:
        sys.stderr.write("ERROR: cannot read input: {0}\n".format(exc))
        return EXIT_GENERIC

    # Parse
    try:
        peers_in = parse_peers_yaml(raw_in)
    except PeersYamlParseError as exc:
        sys.stderr.write("ERROR: parse failure: {0}\n".format(exc))
        return EXIT_SCHEMA_CORRUPT

    # --verify-only path
    if args.verify_only:
        errs = verify_v2_conformance(peers_in)
        if errs:
            for e in errs:
                sys.stderr.write("VIOLATION: {0}\n".format(e))
            return EXIT_CONFORMANCE_FAIL
        sys.stdout.write(
            "OK: {0} peer rows pass v2.0 conformance.\n".format(len(peers_in))
        )
        return EXIT_OK

    # v1.x schema validation (allows already-v2.0 rows too — those are
    # passed through idempotent).
    try:
        # Only validate strictly-v1.x rows; v2.0 rows already validated
        # by virtue of having SPKI + scopes + verified_at.
        v1_rows = [r for r in peers_in if not _row_is_already_v2(r)]
        if v1_rows:
            _validate_v1_schema(v1_rows)
    except PeersYamlParseError as exc:
        sys.stderr.write("ERROR: v1.x schema corrupt: {0}\n".format(exc))
        return EXIT_SCHEMA_CORRUPT

    # F-001 — Pure-v2.0 input short-circuit. If every row is already
    # v2.0 there is nothing to migrate. Emit the input bytes verbatim
    # (no header regeneration; no field reorder) so v2.0 -> v2.0 is
    # byte-identical. The diff/verify-only paths short-circuit before
    # write below.
    if _is_pure_v2(peers_in):
        if args.dry_run:
            sys.stdout.write(
                "pure-v2.0 input: no changes (idempotent short-circuit; "
                "{0} peer rows).\n".format(len(peers_in))
            )
            return EXIT_OK
        # Re-verify conformance defensively (cheap; catches malformed
        # v2.0 input where someone hand-edited a row to half-v2 state).
        conformance_errors = verify_v2_conformance(peers_in)
        if conformance_errors:
            sys.stderr.write(
                "ABORT: pure-v2 short-circuit found conformance "
                "violations in input:\n"
            )
            for e in conformance_errors:
                sys.stderr.write("  - {0}\n".format(e))
            return EXIT_CONFORMANCE_FAIL
        if args.backup_path:
            try:
                _backup(args.in_path, args.backup_path)
            except OSError as exc:
                sys.stderr.write(
                    "ERROR: backup failed: {0}\n".format(exc)
                )
                return EXIT_GENERIC
        # Emit raw input bytes verbatim — byte-identical idempotency.
        try:
            raw_bytes = _read_file_bytes(args.in_path)
            atomic_write_bytes(args.out_path, raw_bytes)
        except OSError as exc:
            sys.stderr.write(
                "ERROR: pure-v2 verbatim write failed: {0}\n".format(exc)
            )
            return EXIT_GENERIC
        sys.stdout.write(
            "OK: pure-v2.0 input — wrote verbatim ({0} bytes, {1} peer rows) "
            "-> {2}\n".format(
                len(raw_bytes), len(peers_in), args.out_path
            )
        )
        return EXIT_OK

    # Migrate (mixed-or-v1.x input path)
    peers_out, errors, floor_warnings = migrate_peers(
        peers_in,
        cert_dir=args.cert_dir,
        skip_cert_inspect=args.skip_cert_inspect,
    )
    if errors:
        sys.stderr.write(
            "ABORT: cert_inspector failures (no files written):\n"
        )
        for e in errors:
            sys.stderr.write("  - {0}\n".format(e))
        return EXIT_GENERIC

    # Render diff if dry-run
    if args.dry_run:
        sys.stdout.write(render_diff(peers_in, peers_out))
        if floor_warnings:
            sys.stdout.write("\nKEY-FLOOR WARNINGS (advisory, no abort):\n")
            for pid, reason in floor_warnings:
                sys.stdout.write("  - {0}: {1}\n".format(pid, reason))
        return EXIT_OK

    # Conformance check on the new output
    conformance_errors = verify_v2_conformance(peers_out)
    # Allow legacy v1.x rows preserved (DER-only, no SPKI). Filter
    # those out -- conformance is enforced only on rows we just touched
    # (i.e. rows that now have SPKI). The conformance fn already gates
    # `key_floor_verified_at` to "spki set" rows.
    if conformance_errors:
        sys.stderr.write(
            "ABORT: v2.0 conformance failed post-migration:\n"
        )
        for e in conformance_errors:
            sys.stderr.write("  - {0}\n".format(e))
        return EXIT_CONFORMANCE_FAIL

    # Backup (optional, before write)
    if args.backup_path:
        try:
            _backup(args.in_path, args.backup_path)
        except OSError as exc:
            sys.stderr.write(
                "ERROR: backup failed: {0}\n".format(exc)
            )
            return EXIT_GENERIC

    # Atomic write
    header = (
        "AUTOGENERATED by tools/migrate-peers-yaml.py at {0}.\n"
        "Source: {1}\n"
        "Schema: PLAN-099-FOLLOWUP v2.0 (SPKI primary pin)."
    ).format(_now_utc_iso(), args.in_path)
    out_text = emit_peers_yaml(peers_out, header=header)
    try:
        atomic_write(args.out_path, out_text)
    except OSError as exc:
        sys.stderr.write("ERROR: atomic_write failed: {0}\n".format(exc))
        return EXIT_GENERIC

    # F-004 — emit floor-fail sidecars for each peer that did NOT meet
    # the key floor. Migration already completed; these are advisory.
    inspected_at = _now_utc_iso()
    for pid, reason in floor_warnings:
        sidecar = _emit_floor_fail_sidecar(
            args.out_path, pid, reason, inspected_at
        )
        sys.stderr.write(
            "WARN: key-floor advisory for {0}: {1}{2}\n".format(
                pid,
                reason,
                "" if sidecar is None else " (sidecar: {0})".format(sidecar),
            )
        )

    sys.stdout.write(
        "OK: migrated {0} peer rows -> {1}{2}\n".format(
            len(peers_out),
            args.out_path,
            "" if not floor_warnings else " ({0} key-floor advisor{1})".format(
                len(floor_warnings),
                "y" if len(floor_warnings) == 1 else "ies",
            ),
        )
    )
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover — script entry
    raise SystemExit(main())
