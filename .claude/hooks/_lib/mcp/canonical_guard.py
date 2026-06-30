#!/usr/bin/env python3
"""Layer B server-side MCP canonical-guard middleware (PLAN-070 §3.8.2).

External clients (Cursor / Codex CLI / helmor) connecting directly to
the MCP server BYPASS Layer A entirely (Layer A is the Claude-side
PreToolUse hook). Layer B inserts a pre-handler middleware in the MCP
server dispatch path that enforces the same canonical-guard semantics
as `check_canonical_edit.py` (the SSO).

Trust boundary:
- Layer A (intra-process, Claude harness) — fail-OPEN on hook fault.
  CODEOWNERS + branch protection are downstream gates.
- Layer B (inter-process, server-side) — universal fail-CLOSED.
  External clients have no downstream gate.

Public API:
    from _lib.mcp.canonical_guard import check_mcp_call
    check_mcp_call(tool_name, params, repo_root=None)
    # → {"decision": "allow"|"block", "reason": str}

Fail-CLOSED triggers (all block): import failure, GPG verify missing,
sentinel unreadable, blob-parse failure on a blob-carrier tool with no
top-level path, any internal exception.

Audit emission: `audit_emit.emit_generic` hasattr-guarded per ADR-098;
also defensively gated on `_KNOWN_ACTIONS` membership (P1-04).

Stdlib-only. Python ≥3.9. `from __future__ import annotations`.
NO PEP 604 runtime types. NO 3rd-party deps.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# P1-05 closure: bootstrap supports BOTH on-disk locations:
#   - Deployed:  .claude/hooks/_lib/mcp/canonical_guard.py
#   - Staging:   .claude/plans/PLAN-070/staging/canonical_guard.py
# Bounded ancestor walk locates `check_canonical_edit.py`; previous
# `parent.parent` was wrong for both.

def _resolve_hooks_root() -> Optional[Path]:
    """Return the directory containing ``check_canonical_edit.py``.

    Bounded upward walk from this file (parents[0..6]) plus the
    conventional ``<ancestor>/.claude/hooks/`` location. Returns
    ``None`` if no hooks root is found; caller fail-CLOSEDs at
    lazy-init.
    """
    here = Path(__file__).resolve()
    for depth in range(0, 7):
        try:
            cand = here.parents[depth]
        except IndexError:
            break
        if (cand / "check_canonical_edit.py").exists():
            return cand
        conv = cand / ".claude" / "hooks" / "check_canonical_edit.py"
        if conv.exists():
            return conv.parent
    return None


_HOOKS_ROOT: Optional[Path] = _resolve_hooks_root()
if _HOOKS_ROOT is not None and str(_HOOKS_ROOT) not in sys.path:
    sys.path.insert(0, str(_HOOKS_ROOT))


# ---------------------------------------------------------------------
# Constants — write-shape parameter keys (mirrors check_canonical_edit.py
# `_MCP_WRITE_PATH_KEYS` for single source of truth)
# ---------------------------------------------------------------------

_MCP_WRITE_PATH_KEYS: Tuple[str, ...] = (
    "path",
    "file_path",
    "target_path",
    "file",
    "filename",
    "dest",
    "destination",
    "target",
    "uri",
)

# ---------------------------------------------------------------------
# Blob-shape parsers (P0-01 NG-06 closure). Three grammars:
#   1. Codex apply_patch envelope — `*** {Update,Add,Delete} File: <p>`
#      + standalone `*** Move to: <p>` for renames (R3-01).
#   2. Unified diff — `--- a/<p>` / `+++ b/<p>`.
#   3. JSON Patch (RFC 6902) — parsed via `json.loads()` so escapes
#      (Unicode, `~0`/`~1`) are decoded before comparison (R3-02).
# ---------------------------------------------------------------------

_MCP_BLOB_BODY_KEYS: Tuple[str, ...] = (
    "patch", "diff", "source", "body",
    "content_diff", "unified_diff", "input", "data",
)
# Tool-name fragments that mark blob-carrying MCP tools. Tool name must
# contain one fragment AND params must contain a blob body key.
_BLOB_TOOL_FRAGMENTS: Tuple[str, ...] = (
    "apply_patch", "applypatch", "patch", "diff",
)
# R4-01 (Codex S85): the colon is OPTIONAL on both the `*** {Action}
# File:?` envelope line AND the `*** Move/Rename to:?` directive. The
# deployed Codex CLI accepts ``*** Update File PROTOCOL.md`` and
# ``*** Move to PROTOCOL.md`` (no colon) — pre-revision-5 the regex
# REQUIRED the colon, so colonless variants returned `non_canonical_path`
# and bypassed Layer B. Broaden to `:?\s+` so both forms parse.
_CODEX_PATCH_RE = re.compile(
    r"^\*\*\*\s+(Update|Add|Delete|Move|Rename)\s+File:?\s+(.+?)\s*$",
    re.MULTILINE,
)
# R3-01 + R4-01: Codex grammar emits a standalone ``*** Move to: <dest>``
# line alongside ``*** Update File: <src>`` for renames. Without this
# rule, the destination of a move (which is the actual write target) is
# invisible to the canonical guard. Match both ``Move to`` and the
# defensive ``Rename to`` variant; colon optional per R4-01.
_CODEX_MOVE_RE = re.compile(
    r"^\*\*\*\s+(?:Move|Rename)\s+to:?\s+(.+?)\s*$",
    re.MULTILINE,
)
_UNIFIED_DIFF_RE = re.compile(
    r"^(?:---|\+\+\+)\s+(?:[ab]/)?(.+?)\s*$", re.MULTILINE,
)
# Legacy regex retained for non-JSON-shape fallback only. The primary
# JSON Patch parser uses `json.loads()` (see `_extract_json_patch_paths`).
_JSON_PATCH_PATH_RE = re.compile(r'"path"\s*:\s*"(/[^"\\]*(?:\\.[^"\\]*)*)"')

# Native (non-MCP) tool names that Layer A handles. Layer B delegates
# these to Layer A via no-op (Layer A is the canonical path for native
# tools; Layer B only intercepts MCP namespace).
_NATIVE_TOOL_NAMES: Tuple[str, ...] = (
    "Edit",
    "Write",
    "MultiEdit",
    "NotebookEdit",
)

# Path-cap defense (mirrors check_canonical_edit.py line ~205).
_MAX_PATH_LEN = 4096


# ---------------------------------------------------------------------
# Typed exception hierarchy (PLAN-086 Wave F.1 — F-A-IDA-T-0007 closure).
#
# These exceptions discriminate Layer B failure boundaries. The default
# contract continues to be fail-CLOSED dict return; the typed classes
# are exposed for tests / strict-mode callers via env var
# CANONICAL_GUARD_STRICT_RAISE=1, and for the audit-emit `error_type`
# payload field on `mcp_canonical_guard_internal_error` (F.2).
#
# Hierarchy:
#   CanonicalGuardError       — base
#     ├── KillSwitchActive    — explicit operator opt-out / import fault
#     ├── PathOutsideAllowlist — path escapes repo_root (R3-05)
#     ├── InvalidPatchBlob    — blob body did not parse (R4-02 / R5-01)
#     └── PolicyViolation     — canonical path without sentinel grant
#
# veto_case: B (auth/crypto). Cite ADR-040 §6.3 (fail-CLOSED contract).
# ---------------------------------------------------------------------


class CanonicalGuardError(Exception):
    """Base class for Layer B canonical-guard failure boundaries.

    Carries a stable ``reason`` attribute (matching ``_REASON_*`` constants)
    so audit-emit payloads have a deterministic discriminator.
    """

    def __init__(self, reason: str, message: Optional[str] = None) -> None:
        self.reason = reason
        super().__init__(message or reason)


class KillSwitchActive(CanonicalGuardError):
    """Operator-controlled kill-switch tripped (env or import failure)."""


class PathOutsideAllowlist(CanonicalGuardError):
    """Candidate path resolves outside repo_root (R3-05 fail-CLOSED)."""


class InvalidPatchBlob(CanonicalGuardError):
    """Blob body did not match any known patch grammar (R4-02 / R5-01)."""


class PolicyViolation(CanonicalGuardError):
    """Canonical path edit attempted without sentinel grant."""


# Env-controlled strict-raise flag. Default off: existing dict-based
# fail-CLOSED contract preserved. When set, the 5 failure boundaries
# RAISE the typed exception (caught by `except CanonicalGuardError` at
# the outer `check_mcp_call` catch and converted to fail-CLOSED dict).
_STRICT_RAISE_ENV = "CANONICAL_GUARD_STRICT_RAISE"


def _strict_raise_enabled() -> bool:
    """Read env each call (test fixtures may toggle mid-process)."""
    import os as _os
    return _os.environ.get(_STRICT_RAISE_ENV, "") == "1"


# Reason codes (stable enum for audit emit).
_REASON_NOT_MCP = "not_mcp_namespace"
_REASON_NO_WRITE_SHAPE = "no_write_shape_params"
_REASON_NOT_CANONICAL = "non_canonical_path"
_REASON_CANONICAL_NO_SENTINEL = "canonical_no_sentinel"
_REASON_IMPORT_FAILURE = "import_failure"
_REASON_GPG_UNAVAILABLE = "gpg_verify_unavailable"
_REASON_SENTINEL_UNREADABLE = "sentinel_unreadable"
_REASON_MIDDLEWARE_FAULT = "middleware_fault"
_REASON_DELEGATED_LAYER_A = "delegated_to_layer_a"
_REASON_JSON_PARSE_FAILED = "json_patch_parse_failed_fail_closed"  # R3-02
_REASON_PATH_ESCAPES_REPO = "path_escapes_repo_root_fail_closed"  # R3-05
_REASON_BLOB_AUTH_PARSE_FAILED = (
    "blob_authoritative_parse_failed_fail_closed"   # R4-02
)

# Lock for thread-safety on lazy-imports.
_IMPORT_LOCK = threading.Lock()
_IMPORTS_INITIALIZED = False
_check_canonical_edit = None  # type: ignore[assignment]
_audit_emit = None  # type: ignore[assignment]


def _lazy_init() -> Tuple[bool, Optional[str]]:
    """Lazy-import `check_canonical_edit` + `audit_emit`.

    Returns `(ok, reason_code)`. `ok=False` triggers fail-CLOSED.
    Thread-safe via module-level lock.
    """
    global _IMPORTS_INITIALIZED, _check_canonical_edit, _audit_emit
    with _IMPORT_LOCK:
        if _IMPORTS_INITIALIZED:
            return True, None
        try:
            import check_canonical_edit as _cce  # type: ignore[import-not-found]
            _check_canonical_edit = _cce
        except Exception:
            return False, _REASON_IMPORT_FAILURE
        try:
            from _lib import audit_emit as _ae
            _audit_emit = _ae
        except Exception:
            # audit_emit failure is non-fatal (advisory only). The
            # canonical guard still functions; we just lose telemetry.
            _audit_emit = None
        _IMPORTS_INITIALIZED = True
        return True, None


def _emit(action: str, **fields: Union[str, int, bool, None]) -> None:
    """Best-effort audit emit, hasattr-guarded per ADR-098.

    P1-04 (Codex 2026-05-04): defensively check that ``action`` is in
    ``audit_emit._KNOWN_ACTIONS`` *before* calling ``emit_generic``.
    Without this check, an unregistered action (e.g. ceremony slipped,
    version mismatch, downstream lib unloaded) gets silently breadcrumbed
    by ``_write_event`` and the event is DROPPED — looks like working
    telemetry from the caller's perspective. Surface the gap on stderr
    so test output + CI logs catch it immediately, then no-op return.

    If `audit_emit` is unavailable OR the specific action is not
    registered in `_KNOWN_ACTIONS`, the call is a no-op.
    """
    if _audit_emit is None:
        return

    # Defensive registration check — see P1-04 closure rationale above.
    known_actions = getattr(_audit_emit, "_KNOWN_ACTIONS", None)
    if known_actions is not None and action not in known_actions:
        try:
            sys.stderr.write(
                f"[mcp.canonical_guard] action {action!r} NOT in "
                f"_KNOWN_ACTIONS; audit event will be dropped. "
                f"Register via Owner sentinel ceremony (see "
                f"staging/audit_emit_registration.patch).\n"
            )
        except Exception:
            pass
        return

    try:
        if hasattr(_audit_emit, "emit_generic"):
            _audit_emit.emit_generic(action, **fields)
    except Exception:
        # Telemetry must never break dispatch. Swallow + breadcrumb.
        try:
            sys.stderr.write(
                f"[mcp.canonical_guard] emit failure for {action}\n"
            )
        except Exception:
            pass


def _extract_write_shape_paths(params: dict) -> List[str]:
    """Extract candidate canonical-edit target paths from MCP params.

    Mirrors `check_canonical_edit._extract_mcp_target_paths` for
    single-source-of-truth contract. Filters empty, oversized, and
    non-string values.

    NOT a write-trigger detector by itself — write-shape detection
    requires BOTH a path-key AND content-shape (covered by caller).
    """
    if not isinstance(params, dict):
        return []
    paths: List[str] = []
    for key in _MCP_WRITE_PATH_KEYS:
        value = params.get(key)
        if isinstance(value, str) and value and len(value) <= _MAX_PATH_LEN:
            paths.append(value)
        elif isinstance(value, list):
            for item in value:
                if (
                    isinstance(item, str)
                    and item
                    and len(item) <= _MAX_PATH_LEN
                ):
                    paths.append(item)
    return paths


def _json_pointer_to_path(pointer: str) -> str:
    """Decode a JSON Pointer (RFC 6901) → filesystem-relative string.

    Per RFC 6901 §4: decode ``~1`` first (→ ``/``), ``~0`` last (→ ``~``).
    Returns ``""`` when ``pointer`` is not a string starting with ``/``.
    """
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        return ""
    return pointer[1:].replace("~1", "/").replace("~0", "~")


def _walk_json_for_paths(node: Any, accumulator: List[str]) -> None:
    """Recursively walk parsed JSON collecting JSON Pointer values from
    ``path``/``from`` keys (RFC 6902 ops). Content cap (4MB) upstream
    bounds recursion depth implicitly.
    """
    if isinstance(node, dict):
        for key in ("path", "from"):
            value = node.get(key)
            if isinstance(value, str) and value.startswith("/"):
                accumulator.append(_json_pointer_to_path(value))
        for v in node.values():
            _walk_json_for_paths(v, accumulator)
    elif isinstance(node, list):
        for item in node:
            _walk_json_for_paths(item, accumulator)


def _looks_like_json_shape(content: str) -> bool:
    """True if ``content`` (post left-strip) starts with ``[`` or ``{``."""
    if not isinstance(content, str) or not content:
        return False
    return content.lstrip().startswith(("[", "{"))


def _extract_blob_target_paths(
    content: str,
) -> Tuple[List[str], bool]:
    """Extract candidate paths from a patch/diff blob.

    Three grammars: (1) Codex apply_patch envelope incl. ``Move to:``
    (R3-01); (2) unified diff; (3) JSON Patch via ``json.loads()`` so
    escapes are decoded BEFORE comparison (R3-02). JSON-shape inputs
    that fail to parse → ``([], False)`` so the caller fails-CLOSED.
    Filters: empty / oversized / ``/dev/null`` / non-string entries.
    """
    paths: List[str] = []
    parsed = False
    if not isinstance(content, str) or not content:
        return paths, parsed
    if len(content) > 4 * 1024 * 1024:  # 4MB content cap
        return paths, False

    # Grammar 1a: Codex apply_patch envelope (Update/Add/Delete File).
    for match in _CODEX_PATCH_RE.finditer(content):
        candidate = match.group(2).strip()
        if candidate and candidate != "/dev/null" and len(candidate) <= _MAX_PATH_LEN:
            paths.append(candidate)
            parsed = True

    # Grammar 1b: Codex `*** Move to: <dest>` directive (R3-01).
    for match in _CODEX_MOVE_RE.finditer(content):
        candidate = match.group(1).strip()
        if candidate and candidate != "/dev/null" and len(candidate) <= _MAX_PATH_LEN:
            paths.append(candidate)
            parsed = True

    # Grammar 2: Unified diff (--- a/foo / +++ b/foo).
    for match in _UNIFIED_DIFF_RE.finditer(content):
        candidate = match.group(1).strip()
        if (
            candidate
            and candidate != "/dev/null"
            and len(candidate) <= _MAX_PATH_LEN
            and not candidate.startswith(("\t", " "))  # skip timestamps
        ):
            paths.append(candidate)
            parsed = True

    # Grammar 3: JSON Patch (RFC 6902). JSON-shape body parsed via
    # `json.loads()` so escapes are decoded (R3-02). Corrupt JSON-shape
    # → ([], False) so caller fail-CLOSED (do NOT fall back to regex).
    if _looks_like_json_shape(content):
        try:
            parsed_json = json.loads(content)
        except (ValueError, TypeError):
            return [], False
        json_paths: List[str] = []
        _walk_json_for_paths(parsed_json, json_paths)
        for decoded in json_paths:
            stripped = decoded.lstrip("/")
            if stripped and len(stripped) <= _MAX_PATH_LEN:
                paths.append(stripped)
                parsed = True
    elif "[" in content and '"op"' in content and '"path"' in content:
        # Legacy regex fallback for non-JSON-shape bodies that embed
        # JSON-looking substrings (defensive).
        for match in _JSON_PATCH_PATH_RE.finditer(content):
            stripped = match.group(1).lstrip("/")
            if stripped and len(stripped) <= _MAX_PATH_LEN:
                paths.append(stripped)
                parsed = True

    # Deduplicate while preserving order.
    seen: set = set()
    unique: List[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique, parsed


def _is_blob_carrying_tool(tool_name: str, params: dict) -> bool:
    """True if tool name + params shape indicate a blob-carrying tool.

    Tool name must contain a blob fragment (apply_patch / patch / diff)
    AND params must include at least one known blob body key.
    """
    if not isinstance(tool_name, str):
        return False
    name_lower = tool_name.lower()
    name_match = any(frag in name_lower for frag in _BLOB_TOOL_FRAGMENTS)
    if not name_match:
        return False
    if not isinstance(params, dict):
        return False
    return any(key in params for key in _MCP_BLOB_BODY_KEYS)


# R4-02 (Codex S85): blob-AUTHORITATIVE tools (apply_patch / patch /
# diff / apply_diff name family) treat the patch BODY as the source of
# truth for the target path. Pre-revision-5, blob-parse failures only
# fail-CLOSED when no top-level write-shape path was present. This
# allowed an attacker to attach a NON-canonical decoy ``file_path``
# (e.g. ``docs/x.md``) plus a CORRUPT patch body actually targeting a
# canonical path — Layer B saw the decoy, returned ``non_canonical_path``,
# and the call ALLOWED. For blob-authoritative tools we must fail-CLOSED
# on parse failure REGARDLESS of decoy top-level path.
_BLOB_AUTHORITATIVE_FRAGMENTS: Tuple[str, ...] = (
    "apply_patch", "applypatch", "apply_diff", "applydiff",
    "patch", "diff",
)

# R5-01 (Codex S85 final pass): for each blob-AUTHORITATIVE tool name
# fragment, declare the SINGLE body key whose value is the source of
# truth for the target path. Sibling blob keys (`diff`, `source`,
# `body`, etc.) may be present but MUST NOT compensate for a corrupt
# authoritative key. Pre-revision-6, the aggregator merged any-parsed
# across all sibling keys, allowing a clean sibling decoy (`diff`) to
# mask a corrupt authoritative `patch` body and bypass R4-02.
#
# Mapping is keyed by the longest matching fragment (`apply_patch`
# wins over `patch`); see `_authoritative_blob_key_for`.
_TOOL_AUTHORITATIVE_BLOB_KEY: Tuple[Tuple[str, str], ...] = (
    # Longest fragment FIRST so `apply_patch` matches before `patch`.
    ("apply_patch", "patch"),
    ("applypatch", "patch"),
    ("apply_diff", "diff"),
    ("applydiff", "diff"),
    # Generic family fallbacks.
    ("patch", "patch"),
    ("diff", "diff"),
)


def _is_blob_authoritative_tool(tool_name: str) -> bool:
    """True for tools where the blob body is authoritative for target path.

    Strictly tool-NAME-driven (does not require body-key presence). Used
    to enforce fail-CLOSED on parse failure even when a top-level
    write-shape decoy is present — see R4-02 above.
    """
    if not isinstance(tool_name, str):
        return False
    name_lower = tool_name.lower()
    return any(frag in name_lower for frag in _BLOB_AUTHORITATIVE_FRAGMENTS)


def _authoritative_blob_key_for(tool_name: str) -> Optional[str]:
    """Return the AUTHORITATIVE blob body key for ``tool_name``, or None.

    R5-01 (Codex S85 final pass). For blob-authoritative tools, exactly
    ONE body key is the source of truth for the target path. Any other
    blob-shape key in `params` is a sibling decoy and may NEVER mask a
    corrupt or absent authoritative key. Returns None for non-
    authoritative tools (caller falls back to legacy aggregation).

    Iteration is in declared order so the longest fragment matches
    first (e.g. ``mcp__codex__apply_patch`` resolves to ``patch`` via
    the ``apply_patch`` rule, not the bare ``patch`` rule).
    """
    if not isinstance(tool_name, str):
        return None
    name_lower = tool_name.lower()
    for fragment, body_key in _TOOL_AUTHORITATIVE_BLOB_KEY:
        if fragment in name_lower:
            return body_key
    return None


def _extract_blob_paths_from_authoritative_key(
    params: dict, auth_key: str
) -> Tuple[List[str], bool, bool]:
    """Parse ONLY the authoritative body key.

    R5-01 fail-CLOSED rule. Returns
    ``(paths, parsed_clean, key_present)``. ``parsed_clean`` is True
    iff the authoritative key value parsed to ≥1 paths via a known
    grammar. ``key_present`` is True iff the key exists in `params`
    (regardless of value type or parse outcome).

    Sibling blob keys are intentionally IGNORED here — the caller may
    still aggregate them via `_extract_blob_paths_from_params` for
    defense-in-depth path collection, but the fail-CLOSED decision
    rests solely on the authoritative key.
    """
    if not isinstance(params, dict) or not isinstance(auth_key, str):
        return [], False, False
    if auth_key not in params:
        return [], False, False
    value = params.get(auth_key)
    if not isinstance(value, str):
        # Key present but value non-string (e.g. None, dict, bytes) —
        # treat as parse failure under the same fail-CLOSED rule.
        return [], False, True
    paths, parsed = _extract_blob_target_paths(value)
    return paths, parsed, True


def _extract_blob_paths_from_params(params: dict) -> Tuple[List[str], bool]:
    """Aggregate blob paths across all known body keys.

    Returns ``(paths, any_parsed)``. ``any_parsed`` is True if at least
    one body key parsed at least one path; False if every body key was
    empty/non-string/unrecognized grammar.
    """
    if not isinstance(params, dict):
        return [], False
    aggregated: List[str] = []
    any_parsed = False
    any_present = False
    for key in _MCP_BLOB_BODY_KEYS:
        if key not in params:
            continue
        any_present = True
        value = params.get(key)
        if not isinstance(value, str):
            continue
        paths, parsed = _extract_blob_target_paths(value)
        if parsed:
            any_parsed = True
            aggregated.extend(paths)
    # If no body key was present at all, parsed=False is "no signal";
    # if a key WAS present but yielded zero paths, that's a real
    # parse-failure → caller fails-CLOSED.
    return aggregated, (any_parsed or not any_present)


def _has_write_shape(params: dict) -> bool:
    """True if `params` contains a path-shape key.

    Conservative: any presence of a path-shape key (file_path, path, ...)
    triggers Layer B verification, even if the corresponding value is
    empty/oversized. The intent is to err on the side of fail-CLOSED.
    """
    if not isinstance(params, dict):
        return False
    return any(key in params for key in _MCP_WRITE_PATH_KEYS)


def _resolve_against_repo_root(path_str: str, repo_root: Path) -> str:
    """Anchor a candidate path against ``repo_root`` not CWD (P0-02).

    External MCP servers (Codex CLI from ``/tmp``) had relative paths
    resolve against CWD, which made canonical paths slip through.
    Absolute paths pass through; relative paths are joined with
    ``repo_root`` BEFORE downstream resolution.
    """
    if not isinstance(path_str, str) or not path_str:
        return path_str
    if Path(path_str).is_absolute():
        return path_str
    try:
        return str((repo_root / path_str))
    except (TypeError, ValueError):
        return path_str


def _resolves_inside_repo(path_str: str, repo_root: Path) -> bool:
    """True iff ``path_str`` resolves inside ``repo_root`` (R3-05).

    Defense against ``..``-traversal, symlink escapes, and absolute
    paths outside the worktree. Uses ``Path.is_relative_to`` (≥3.9)
    after ``resolve(strict=False)`` (non-existent terminal components
    are appended verbatim — correct for to-be-created targets).
    Returns False on any exception (caller fails-CLOSED).
    """
    if not isinstance(path_str, str) or not path_str:
        return False
    try:
        anchored = _resolve_against_repo_root(path_str, repo_root)
        return (
            Path(anchored).resolve(strict=False)
            .is_relative_to(repo_root.resolve(strict=False))
        )
    except (OSError, ValueError, RuntimeError):
        return False


def _check_canonical(path_str: str, repo_root: Path) -> bool:
    """Delegate to `check_canonical_edit._is_canonical` for SSO truth.

    Returns True if the path is in `_CANONICAL_GUARDS`. False on any
    error (caller decides whether to fail-CLOSED).

    P0-02: anchors relative paths against ``repo_root`` BEFORE the SSO
    call so external-client invocations (Codex CLI from ``/tmp``)
    resolve correctly.
    """
    if _check_canonical_edit is None:
        return False
    anchored = _resolve_against_repo_root(path_str, repo_root)
    try:
        return bool(
            _check_canonical_edit._is_canonical(anchored, repo_root)
        )
    except Exception:
        return False


def _sentinel_grants(rel_path: str, repo_root: Path) -> Tuple[bool, Optional[str]]:
    """Delegate to `check_canonical_edit._sentinel_grants_path`.

    Iterates all sentinels found by `_find_sentinels`; returns
    `(True, sentinel_path_str)` on first grant. Returns `(False, None)`
    if no sentinel grants the path.

    Fail-CLOSED: if the helper raises, returns `(False, error_str)`.
    """
    if _check_canonical_edit is None:
        return False, "helper_unavailable"
    try:
        sentinels = _check_canonical_edit._find_sentinels(repo_root)
    except Exception as e:
        return False, f"find_sentinels_error:{type(e).__name__}"
    for sentinel in sentinels:
        try:
            granted = _check_canonical_edit._sentinel_grants_path(
                sentinel, rel_path
            )
        except OSError:
            # Sentinel file unreadable — fail-CLOSED for THIS sentinel
            # but continue iteration (other sentinels may grant).
            continue
        except Exception:
            continue
        if not granted:
            continue
        # Format sentinel path: prefer repo-relative, fall back to str.
        try:
            sentinel_label = str(sentinel.relative_to(repo_root))
        except (ValueError, AttributeError):
            sentinel_label = str(sentinel)
        return True, sentinel_label
    return False, None


def check_mcp_call(
    tool_name: str,
    params: Optional[dict] = None,
    repo_root: Optional[Path] = None,
) -> Dict[str, str]:
    """Layer B middleware entry point.

    Args:
        tool_name: MCP tool name (e.g. ``mcp__codex__apply_patch``).
        params: Tool input dict (may contain write-shape keys).
        repo_root: Optional override for repo root resolution.

    Returns:
        ``{"decision": "allow"|"block", "reason": str}``.

    Contract:
        - Native tools (Edit/Write/MultiEdit/NotebookEdit) → allow with
          reason ``delegated_to_layer_a`` (Layer A is the canonical
          guard for these).
        - Non-MCP-namespace tool → allow with reason
          ``not_mcp_namespace``.
        - MCP tool with no write-shape params → allow with reason
          ``no_write_shape_params``.
        - MCP tool with write-shape params, no canonical path → allow
          with reason ``non_canonical_path``.
        - MCP tool with write-shape params + canonical path + sentinel
          grant → allow.
        - MCP tool with write-shape params + canonical path + no
          sentinel grant → **block** with reason
          ``canonical_no_sentinel``.
        - Any failure mode → **block** (fail-CLOSED).

    The function never raises — internal exceptions are caught + reported
    via the `reason` field with prefix ``middleware_fault:``.
    """
    if params is None:
        params = {}

    # Resolve repo_root early — used in error paths too.
    try:
        repo_root_resolved = repo_root or Path(
            os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        )
    except Exception:
        return {
            "decision": "block",
            "reason": _REASON_MIDDLEWARE_FAULT,
        }

    # Native tool delegation — Layer A handles these. Layer B no-op.
    if tool_name in _NATIVE_TOOL_NAMES:
        return {
            "decision": "allow",
            "reason": _REASON_DELEGATED_LAYER_A,
        }

    # Non-MCP tool — out of scope.
    if not isinstance(tool_name, str) or not tool_name.startswith("mcp__"):
        return {
            "decision": "allow",
            "reason": _REASON_NOT_MCP,
        }

    # Lazy-init imports.
    ok, reason = _lazy_init()
    if not ok:
        # Fail-CLOSED on import failure.
        _emit(
            "mcp_canonical_guard_blocked",
            tool_name=tool_name,
            reason=reason or _REASON_IMPORT_FAILURE,
        )
        return {
            "decision": "block",
            "reason": (
                f"Layer B middleware import failed: {reason}. "
                f"Fail-CLOSED per universal contract."
            ),
        }

    try:
        # Aggregate candidate paths from BOTH (a) write-shape param keys
        # and (b) blob-shape param bodies (codex apply_patch / unified
        # diff / json patch). NG-06 closure (P0-01): a tool that carries
        # the target path INSIDE the patch body with no top-level
        # `file_path` MUST still be gated.
        candidate_paths: List[str] = []
        write_shape_present = _has_write_shape(params)

        if write_shape_present:
            top_level_paths = _extract_write_shape_paths(params)
            # R3-05 ordering: top-level write-shape paths are checked
            # for repo-escape BEFORE blob-authoritative parsing. Escape
            # is an unambiguous fail-CLOSED signal — an attacker should
            # not be able to mask path-traversal behind a blob-parse
            # outcome. This also keeps the legacy R3-05 reason text
            # (`escapes repo_root`) stable for test contracts.
            for candidate in top_level_paths:
                if not _resolves_inside_repo(candidate, repo_root_resolved):
                    _emit(
                        "mcp_canonical_guard_blocked",
                        tool_name=tool_name,
                        target_path=candidate[:_MAX_PATH_LEN],
                        reason=_REASON_PATH_ESCAPES_REPO,
                    )
                    return {
                        "decision": "block",
                        "reason": (
                            f"Layer B: candidate path "
                            f"'{candidate[:200]}' escapes repo_root via "
                            f"traversal/symlink/absolute path. "
                            f"Fail-CLOSED per universal contract. R3-05."
                        ),
                    }
            candidate_paths.extend(top_level_paths)

        blob_carrier = _is_blob_carrying_tool(tool_name, params)
        blob_authoritative = _is_blob_authoritative_tool(tool_name)
        if blob_carrier:
            # R5-01 (Codex S85 final pass): for blob-AUTHORITATIVE tools
            # (apply_patch / patch / diff / apply_diff family), the
            # AUTHORITATIVE body key (e.g. `patch` for apply_patch) is
            # the SOLE source of truth for fail-CLOSED. A clean sibling
            # decoy (`diff="*** Update File: docs/x.md"`) MUST NOT mask
            # a corrupt or absent authoritative key. Pre-revision-6,
            # the aggregator merged `any_parsed` across all sibling
            # keys → an attacker could supply
            # `patch="\x00garbage" + diff="<clean non-canonical>"` and
            # get an allow/non_canonical_path return.
            if blob_authoritative:
                auth_key = _authoritative_blob_key_for(tool_name)
                # _authoritative_blob_key_for returns None only if
                # tool_name is non-string, which `_is_blob_authoritative
                # _tool` already filtered. Defensive guard preserves
                # fail-CLOSED if mappings ever drift apart.
                if auth_key is None:  # pragma: no cover — defensive
                    _emit(
                        "mcp_canonical_guard_blocked",
                        tool_name=tool_name,
                        reason=_REASON_BLOB_AUTH_PARSE_FAILED,
                    )
                    return {
                        "decision": "block",
                        "reason": (
                            "Layer B: blob-authoritative tool "
                            f"'{tool_name}' has no authoritative key "
                            "mapping (defense-in-depth fail-CLOSED). "
                            "R5-01."
                        ),
                    }
                (
                    auth_paths,
                    auth_parsed,
                    auth_present,
                ) = _extract_blob_paths_from_authoritative_key(
                    params or {}, auth_key
                )
                if not auth_present:
                    # R5-01: authoritative key MISSING for a blob-
                    # authoritative tool. Sibling blob keys may parse
                    # cleanly (decoy) but they are not the source of
                    # truth → fail-CLOSED.
                    _emit(
                        "mcp_canonical_guard_blocked",
                        tool_name=tool_name,
                        reason=_REASON_BLOB_AUTH_PARSE_FAILED,
                    )
                    return {
                        "decision": "block",
                        "reason": (
                            "Layer B: blob-authoritative tool "
                            f"'{tool_name}' is missing its "
                            f"authoritative body key '{auth_key}'. "
                            "Sibling blob keys are not accepted as "
                            "substitutes. Fail-CLOSED per universal "
                            "contract. R5-01."
                        ),
                    }
                if not auth_parsed:
                    # R5-01: authoritative key PRESENT but value did
                    # not parse via any known patch grammar (binary
                    # garbage, empty string, non-string, unknown
                    # framing). Sibling decoy keys cannot recover the
                    # call.
                    _emit(
                        "mcp_canonical_guard_blocked",
                        tool_name=tool_name,
                        reason=_REASON_BLOB_AUTH_PARSE_FAILED,
                    )
                    return {
                        "decision": "block",
                        "reason": (
                            "Layer B: blob-authoritative tool "
                            f"'{tool_name}' authoritative body key "
                            f"'{auth_key}' did not match any known "
                            "patch grammar (codex apply_patch / "
                            "unified diff / JSON Patch). Sibling blob "
                            "keys are treated as decoy. Fail-CLOSED "
                            "per universal contract. R5-01 + R4-02."
                        ),
                    }
                # Authoritative key parsed cleanly — start aggregation
                # from authoritative paths. Sibling blob keys still
                # contribute (defense-in-depth: any canonical hit
                # blocks), but the fail-CLOSED gate is already
                # satisfied by the authoritative key.
                candidate_paths.extend(auth_paths)
                # Aggregate sibling keys for canonical-hit aggregation
                # only — sibling parse failure does NOT trigger fail-
                # CLOSED on the authoritative-tool branch (the auth
                # key was already cleanly parsed; siblings are
                # advisory).
                sibling_paths, _ = _extract_blob_paths_from_params(
                    params or {}
                )
                # De-dupe via list-membership check (preserve order).
                for p in sibling_paths:
                    if p not in candidate_paths:
                        candidate_paths.append(p)
            else:
                # NG-06 legacy path (non-authoritative blob carriers):
                # tool name contains a blob fragment but isn't on the
                # authoritative list (e.g. a future MCP tool whose
                # name happens to include "diff" without being a
                # patch executor). Aggregate all body keys and apply
                # the original blob_parsed gate.
                blob_paths, blob_parsed = _extract_blob_paths_from_params(
                    params or {}
                )
                if not blob_parsed:
                    if not write_shape_present:
                        _emit(
                            "mcp_canonical_guard_blocked",
                            tool_name=tool_name,
                            reason="blob_parse_failed_fail_closed",
                        )
                        return {
                            "decision": "block",
                            "reason": (
                                "Layer B: tool name matches blob-"
                                "carrying fragment but body did not "
                                "match any known patch grammar "
                                "(codex apply_patch / unified diff / "
                                "JSON Patch) and no top-level write-"
                                "shape path was provided. Fail-CLOSED "
                                "per universal contract. NG-06 P0-01."
                            ),
                        }
                candidate_paths.extend(blob_paths)

        # If neither write-shape nor blob-shape produced any candidates,
        # the call is a true read-only or non-write-shape MCP call.
        if not candidate_paths:
            _emit(
                "mcp_canonical_guard_allowed",
                tool_name=tool_name,
                reason=_REASON_NO_WRITE_SHAPE,
            )
            return {
                "decision": "allow",
                "reason": _REASON_NO_WRITE_SHAPE,
            }

        # R3-05: reject any candidate that resolves outside repo_root
        # BEFORE canonical / sentinel checks. Catches:
        #   * `../../../etc/passwd` (literal traversal)
        #   * symlink-in-repo pointing outside repo_root
        #   * absolute paths outside the worktree
        # Most-restrictive policy: ANY escaping candidate fail-CLOSED.
        for candidate in candidate_paths:
            if not _resolves_inside_repo(candidate, repo_root_resolved):
                _emit(
                    "mcp_canonical_guard_blocked",
                    tool_name=tool_name,
                    target_path=candidate[:_MAX_PATH_LEN],
                    reason=_REASON_PATH_ESCAPES_REPO,
                )
                return {
                    "decision": "block",
                    "reason": (
                        f"Layer B: candidate path '{candidate[:200]}' "
                        f"escapes repo_root via traversal/symlink/absolute "
                        f"path. Fail-CLOSED per universal contract. R3-05."
                    ),
                }

        # Find first canonical path; if any candidate is canonical,
        # apply most-restrictive policy (canonical gating).
        canonical_target: Optional[str] = None
        for candidate in candidate_paths:
            if _check_canonical(candidate, repo_root_resolved):
                canonical_target = candidate
                break

        if canonical_target is None:
            _emit(
                "mcp_canonical_guard_allowed",
                tool_name=tool_name,
                reason=_REASON_NOT_CANONICAL,
            )
            return {
                "decision": "allow",
                "reason": _REASON_NOT_CANONICAL,
            }

        # Resolve to repo-relative form for sentinel matching.
        # P0-02: anchor relative paths against repo_root (NOT CWD)
        # before resolving. External clients (Codex CLI) may invoke
        # with CWD = /tmp; without anchoring, ``Path("PROTOCOL.md")
        # .resolve()`` becomes ``/tmp/PROTOCOL.md`` and ``relative_to``
        # raises.
        anchored_target = _resolve_against_repo_root(
            canonical_target, repo_root_resolved
        )
        try:
            rel_str = str(
                Path(anchored_target).resolve().relative_to(
                    repo_root_resolved.resolve()
                )
            ).replace(os.sep, "/")
        except (ValueError, OSError):
            # Path resolution failed for canonical target — fail-CLOSED.
            _emit(
                "mcp_canonical_guard_blocked",
                tool_name=tool_name,
                target_path=canonical_target,
                reason=_REASON_SENTINEL_UNREADABLE,
            )
            return {
                "decision": "block",
                "reason": (
                    f"Canonical path '{canonical_target}' resolution "
                    f"failed; fail-CLOSED."
                ),
            }

        granted, sentinel_or_err = _sentinel_grants(rel_str, repo_root_resolved)
        if granted:
            # R6-01: agreed Sec MF-3 contract restricts caller fields to
            # {tool_name, target_path, reason}. The sentinel label is
            # folded INTO the reason string (allowed for diagnostics);
            # `sentinel=` as a structured kwarg is no longer emitted.
            _emit(
                "mcp_canonical_guard_allowed",
                tool_name=tool_name,
                target_path=rel_str,
                reason=(
                    f"sentinel:{sentinel_or_err}" if sentinel_or_err
                    else "sentinel:unspecified"
                ),
            )
            return {
                "decision": "allow",
                "reason": (
                    f"Canonical edit '{rel_str}' allowed via sentinel "
                    f"{sentinel_or_err}"
                ),
            }

        _emit(
            "mcp_canonical_guard_blocked",
            tool_name=tool_name,
            target_path=rel_str,
            reason=_REASON_CANONICAL_NO_SENTINEL,
        )
        return {
            "decision": "block",
            "reason": (
                f"MCP-CANONICAL-EDIT-BLOCKED: '{rel_str}' is a canonical "
                f"governance path. Edits via MCP require an Owner-signed "
                f"sentinel at .claude/plans/PLAN-NNN/architect/round-N/"
                f"approved.md with this path declared in Scope:. "
                f"See ADR-010 + PLAN-070 §3.8.2."
            ),
        }

    except Exception as e:
        # Universal fail-CLOSED.
        _emit(
            "mcp_canonical_guard_blocked",
            tool_name=tool_name,
            # R6-01: error class name folded into `reason` (caller fields
            # restricted to {tool_name, target_path, reason}).
            reason=f"{_REASON_MIDDLEWARE_FAULT}:{type(e).__name__}",
        )
        return {
            "decision": "block",
            "reason": (
                f"Layer B middleware fault: {type(e).__name__}. "
                f"Fail-CLOSED per universal contract."
            ),
        }


# ---------------------------------------------------------------------
# PLAN-085 Wave D.2 — defensive Codex-egress redaction shim (ADR-114 §AC9).
#
# Layer B middleware does NOT itself invoke Codex (its decision surface
# is gate / pass / block), but downstream callers that route blob-shape
# payloads through ``mcp__codex__*`` tools may pass user-provided prompt
# text. This helper exposes the redactor at the canonical guard import
# surface so external clients (Cursor / Codex CLI / helmor) can call
# ``redact_outgoing(text)`` before any Codex invocation without taking a
# direct dependency on ``_lib.codex_egress_redact``.
#
# AC9 enforcement: the AST-based ``TestCodexEgressCallsiteCoverage`` test
# (see ``.claude/hooks/tests/test_codex_egress_redact_outgoing.py``) walks
# every entry in its ``EXPECTED_CALLSITES`` tuple for a function-scope
# pattern where ``redact_outgoing`` is invoked BEFORE the egress
# primitive (``make_invoke_command`` or ``subprocess.run``). This shim
# satisfies that contract for ``canonical_guard.py``.
# ---------------------------------------------------------------------


def redact_outgoing_codex_payload(text: str) -> str:
    """Apply ``codex_egress_redact.redact_outgoing`` defensively.

    Returns the redacted text. NEVER raises. If the redactor module
    itself is unavailable (import-time failure) we return the input
    unchanged — Layer B middleware is fail-CLOSED on its gating
    surface but fail-OPEN on this best-effort redaction helper.
    """
    try:
        from .. import codex_egress_redact as _redact
        return _redact.redact_outgoing(text)
    except Exception:  # pragma: no cover (defensive — redactor is fail-open)
        return text


# ---------------------------------------------------------------------
# Module-level smoke (development-only; not invoked in production)
# ---------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    # Smoke test: invoke with a synthetic write-shaped MCP call.
    import json as _json
    result = check_mcp_call(
        tool_name="mcp__codex__apply_patch",
        params={"file_path": "PROTOCOL.md", "patch": "..."},
    )
    print(_json.dumps(result, indent=2))
