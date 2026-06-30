"""MCP handlers: ``list_plans`` / ``get_plan`` / ``get_plan_acs`` /
``get_plan_dependencies`` (PLAN-096 Wave B).

Per ADR-042-AMEND-1 §Auth.2 these 4 methods are ``readonly`` class
handlers (no write surface; plan frontmatter exposure only). The
``check_plan_edit.py`` hook continues to enforce write-side semantics —
nothing in this module touches disk except read-only file IO.

## Source of truth

Walks ``.claude/plans/PLAN-NNN-<slug>.md`` (top-level monotonic
3-digit, matching PLAN-SCHEMA §1). The handler does NOT recurse into
``PLAN-NNN/`` subdirectories — only the top-level frontmatter is
exposed.

## Cache

Module-level cache with 30s TTL. Frontmatter is read-mostly during
normal operation; cache misses on plan-status flips are acceptable.

## Fail-open

Any walk/parse error degrades to an empty list or a warning field —
never raises.
"""

from __future__ import annotations

import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


_CACHE_LOCK = threading.Lock()
_LIST_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_PLAN_CACHE: Dict[Tuple[str, str], Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL_S = 30.0


_PLAN_FILE_RE = re.compile(r"^PLAN-(\d{3})-([a-z0-9][a-z0-9-]*)\.md$")


def _reset_cache() -> None:
    """Test helper — drop all caches."""
    with _CACHE_LOCK:
        _LIST_CACHE.clear()
        _PLAN_CACHE.clear()


# ---------------------------------------------------------------------------
# Frontmatter parser (lightweight YAML-ish)
# ---------------------------------------------------------------------------


def _parse_frontmatter(plan_md: Path) -> Dict[str, Any]:
    """Return the frontmatter dict from a plan file.

    Empty dict on any read/parse error. Recognized scalars: strings,
    ints, bools (true/false), lists (block form ``- item`` and inline
    ``[a, b]``).
    """
    try:
        text = plan_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end_idx: Optional[int] = None
    for i in range(1, min(len(lines), 400)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {}
    body = lines[1:end_idx]
    out: Dict[str, Any] = {}
    current_key: Optional[str] = None
    current_list: Optional[List[Any]] = None
    for raw in body:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        # Block-list continuation: indented "- value".
        if current_list is not None and raw.lstrip().startswith("- "):
            current_list.append(_coerce_scalar(raw.lstrip()[2:].strip()))
            continue
        # New top-level key.
        if ":" in raw and not raw.startswith(" "):
            current_list = None
            key, _, value = raw.partition(":")
            key = key.strip()
            value = _strip_inline_comment(value.strip())
            if not key:
                continue
            if not value:
                # Block-list start (next lines are "- item") OR
                # empty key (silently skip below).
                current_list = []
                out[key] = current_list
                current_key = key
                continue
            # Inline list [a, b, c]
            if value.startswith("[") and value.endswith("]"):
                inner = value[1:-1].strip()
                items: List[Any] = []
                if inner:
                    for part in _split_inline_list(inner):
                        items.append(_coerce_scalar(part.strip()))
                out[key] = items
                current_key = key
                continue
            out[key] = _coerce_scalar(value)
            current_key = key
    # Drop empty placeholder lists (block lists that never got items).
    for k, v in list(out.items()):
        if isinstance(v, list) and not v:
            # Keep them as-is (empty list is meaningful).
            pass
    return out


def _strip_inline_comment(value: str) -> str:
    """Strip a YAML inline comment.

    Handles ``key: value   # comment`` by truncating at the first ``#``
    that is NOT inside a quoted string. Preserves ``#`` characters that
    appear inside single- or double-quoted scalars.
    """
    if not value:
        return value
    quote: Optional[str] = None
    for i, ch in enumerate(value):
        if quote is None:
            if ch in ('"', "'"):
                quote = ch
                continue
            if ch == "#":
                # Must be preceded by whitespace or be at start to count
                # as a YAML comment marker. Otherwise it's a literal.
                if i == 0 or value[i - 1].isspace():
                    return value[:i].rstrip()
        else:
            if ch == quote:
                quote = None
    return value


def _split_inline_list(s: str) -> List[str]:
    """Split a YAML inline list body, honoring quoted commas."""
    parts: List[str] = []
    buf: List[str] = []
    quote: Optional[str] = None
    for ch in s:
        if quote is None:
            if ch in ('"', "'"):
                quote = ch
                buf.append(ch)
                continue
            if ch == ",":
                parts.append("".join(buf))
                buf = []
                continue
            buf.append(ch)
        else:
            buf.append(ch)
            if ch == quote:
                quote = None
    if buf:
        parts.append("".join(buf))
    return parts


def _coerce_scalar(value: str) -> Any:
    """Coerce a YAML-ish scalar string to int/bool/str."""
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        return value[1:-1]
    if value.startswith("'") and value.endswith("'") and len(value) >= 2:
        return value[1:-1]
    low = value.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("null", "~", ""):
        return None
    if value.lstrip("-").isdigit():
        try:
            return int(value)
        except ValueError:
            pass
    return value


# ---------------------------------------------------------------------------
# Plan walker
# ---------------------------------------------------------------------------


def _plan_files(project_dir: Path) -> List[Path]:
    plans_dir = project_dir / ".claude" / "plans"
    if not plans_dir.is_dir():
        return []
    out: List[Path] = []
    for entry in sorted(plans_dir.iterdir()):
        if not entry.is_file():
            continue
        if _PLAN_FILE_RE.match(entry.name):
            out.append(entry)
    return out


def _list_plans_uncached(project_dir: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for plan_md in _plan_files(project_dir):
        fm = _parse_frontmatter(plan_md)
        plan_id = fm.get("id") or _id_from_filename(plan_md.name)
        if not plan_id:
            continue
        out.append(
            {
                "id": plan_id,
                "title": fm.get("title", ""),
                "status": fm.get("status", "unknown"),
                "target_tag": fm.get("target_tag", ""),
                "depends_on": fm.get("depends_on", []),
                "external_wait": fm.get("external_wait", []),
                "risk_tier": fm.get("risk_tier", ""),
                "owner": fm.get("owner", ""),
            }
        )
    return out


def _id_from_filename(name: str) -> Optional[str]:
    m = _PLAN_FILE_RE.match(name)
    if not m:
        return None
    return f"PLAN-{m.group(1)}"


def _list_plans_cached(project_dir: Path) -> List[Dict[str, Any]]:
    key = str(project_dir.resolve())
    now_ts = time.monotonic()
    with _CACHE_LOCK:
        entry = _LIST_CACHE.get(key)
        if entry is not None and entry[0] > now_ts:
            return [dict(p) for p in entry[1]]
    fresh = _list_plans_uncached(project_dir)
    with _CACHE_LOCK:
        _LIST_CACHE[key] = (now_ts + _CACHE_TTL_S, fresh)
    return [dict(p) for p in fresh]


def _find_plan_file(project_dir: Path, plan_id: str) -> Optional[Path]:
    if not plan_id:
        return None
    plan_id = plan_id.upper().strip()
    m = re.match(r"^PLAN-(\d{3})$", plan_id)
    if not m:
        return None
    nnn = m.group(1)
    plans_dir = project_dir / ".claude" / "plans"
    if not plans_dir.is_dir():
        return None
    for entry in plans_dir.iterdir():
        if entry.is_file() and entry.name.startswith(f"PLAN-{nnn}-"):
            return entry
    return None


def _plan_cached(project_dir: Path, plan_id: str) -> Optional[Dict[str, Any]]:
    key = (str(project_dir.resolve()), plan_id.upper())
    now_ts = time.monotonic()
    with _CACHE_LOCK:
        entry = _PLAN_CACHE.get(key)
        if entry is not None and entry[0] > now_ts:
            return dict(entry[1])
    plan_md = _find_plan_file(project_dir, plan_id)
    if plan_md is None:
        return None
    fm = _parse_frontmatter(plan_md)
    fm["_filename"] = plan_md.name
    with _CACHE_LOCK:
        _PLAN_CACHE[key] = (now_ts + _CACHE_TTL_S, fm)
    return dict(fm)


# ---------------------------------------------------------------------------
# AC extraction
# ---------------------------------------------------------------------------


_AC_RE = re.compile(
    r"^\s*-?\s*\*\*\s*(AC[\w\-.]*)\s*\*\*\s*[:\-]?\s*(.+)$",
    re.IGNORECASE,
)


def _extract_acs(plan_md: Path) -> List[Dict[str, str]]:
    try:
        text = plan_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out: List[Dict[str, str]] = []
    in_ac_section = False
    current_ac: Optional[Dict[str, str]] = None
    for raw in text.splitlines():
        stripped = raw.strip()
        # Section heading detection — be permissive across formatting
        # styles (## §4. Acceptance criteria, ## Acceptance Criteria, etc).
        low = stripped.lower()
        if stripped.startswith("##") and ("acceptance" in low or "ac" in low.split()):
            in_ac_section = True
            current_ac = None
            continue
        if stripped.startswith("##") and in_ac_section:
            # Left the AC section.
            break
        if not in_ac_section:
            continue
        m = _AC_RE.match(raw)
        if m:
            if current_ac is not None:
                out.append(current_ac)
            current_ac = {
                "id": m.group(1).strip(),
                "text": m.group(2).strip(),
            }
            continue
        if current_ac is not None and stripped:
            # Continuation line — append (collapsed).
            current_ac["text"] = (current_ac["text"] + " " + stripped).strip()
    if current_ac is not None:
        out.append(current_ac)
    return out


# ---------------------------------------------------------------------------
# Handlers (one per method)
# ---------------------------------------------------------------------------


def handle_list_plans(
    params: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """``list_plans`` — return all plan frontmatter summaries.

    Optional ``status`` param filters by status (e.g. ``executing``).
    """
    project_dir_raw = context.get("project_dir")
    if project_dir_raw is None:
        return {"plans": [], "warning": "project_dir_missing"}
    project_dir = Path(project_dir_raw)
    try:
        plans = _list_plans_cached(project_dir)
    except Exception as e:
        return {"plans": [], "warning": f"walk_failed:{type(e).__name__}"}
    status_filter = None
    if isinstance(params, dict):
        sf = params.get("status")
        if isinstance(sf, str) and sf.strip():
            status_filter = sf.strip().lower()
    if status_filter is not None:
        plans = [p for p in plans if str(p.get("status", "")).lower() == status_filter]
    return {"plans": plans, "total": len(plans)}


def handle_get_plan(
    params: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """``get_plan`` — return full frontmatter for one plan.

    Required param: ``plan_id`` (e.g. ``"PLAN-096"``).
    """
    project_dir_raw = context.get("project_dir")
    if project_dir_raw is None:
        return {"plan": None, "warning": "project_dir_missing"}
    project_dir = Path(project_dir_raw)
    plan_id = params.get("plan_id") if isinstance(params, dict) else None
    if not isinstance(plan_id, str) or not plan_id.strip():
        return {
            "plan": None,
            "__error__": {"code": -32602, "message": "missing_plan_id"},
        }
    try:
        plan = _plan_cached(project_dir, plan_id.strip())
    except Exception as e:
        return {"plan": None, "warning": f"read_failed:{type(e).__name__}"}
    if plan is None:
        return {
            "plan": None,
            "__error__": {"code": -32602, "message": f"plan_not_found:{plan_id}"},
        }
    return {"plan": plan}


def handle_get_plan_acs(
    params: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """``get_plan_acs`` — return parsed Acceptance Criteria list.

    Required param: ``plan_id``.
    """
    project_dir_raw = context.get("project_dir")
    if project_dir_raw is None:
        return {"acs": [], "warning": "project_dir_missing"}
    project_dir = Path(project_dir_raw)
    plan_id = params.get("plan_id") if isinstance(params, dict) else None
    if not isinstance(plan_id, str) or not plan_id.strip():
        return {
            "acs": [],
            "__error__": {"code": -32602, "message": "missing_plan_id"},
        }
    plan_md = _find_plan_file(project_dir, plan_id.strip())
    if plan_md is None:
        return {
            "acs": [],
            "__error__": {"code": -32602, "message": f"plan_not_found:{plan_id}"},
        }
    try:
        acs = _extract_acs(plan_md)
    except Exception as e:
        return {"acs": [], "warning": f"parse_failed:{type(e).__name__}"}
    return {"plan_id": plan_id.strip().upper(), "acs": acs, "total": len(acs)}


def handle_get_plan_dependencies(
    params: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """``get_plan_dependencies`` — return depends_on + external_wait.

    Required param: ``plan_id``.
    """
    project_dir_raw = context.get("project_dir")
    if project_dir_raw is None:
        return {"depends_on": [], "external_wait": [], "warning": "project_dir_missing"}
    project_dir = Path(project_dir_raw)
    plan_id = params.get("plan_id") if isinstance(params, dict) else None
    if not isinstance(plan_id, str) or not plan_id.strip():
        return {
            "depends_on": [],
            "external_wait": [],
            "__error__": {"code": -32602, "message": "missing_plan_id"},
        }
    try:
        plan = _plan_cached(project_dir, plan_id.strip())
    except Exception as e:
        return {
            "depends_on": [],
            "external_wait": [],
            "warning": f"read_failed:{type(e).__name__}",
        }
    if plan is None:
        return {
            "depends_on": [],
            "external_wait": [],
            "__error__": {"code": -32602, "message": f"plan_not_found:{plan_id}"},
        }
    depends_on = plan.get("depends_on") or []
    external_wait = plan.get("external_wait") or []
    if not isinstance(depends_on, list):
        depends_on = []
    if not isinstance(external_wait, list):
        external_wait = []
    return {
        "plan_id": plan_id.strip().upper(),
        "depends_on": depends_on,
        "external_wait": external_wait,
    }


HANDLERS: Dict[str, Any] = {
    "list_plans": handle_list_plans,
    "get_plan": handle_get_plan,
    "get_plan_acs": handle_get_plan_acs,
    "get_plan_dependencies": handle_get_plan_dependencies,
}


__all__ = [
    "HANDLERS",
    "handle_list_plans",
    "handle_get_plan",
    "handle_get_plan_acs",
    "handle_get_plan_dependencies",
    "_reset_cache",
]
