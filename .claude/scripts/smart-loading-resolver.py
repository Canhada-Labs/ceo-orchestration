#!/usr/bin/env python3
"""Smart-loading resolver — PLAN-083 Wave 0b sub-agent 0.7d.

Implements R2 Spec-A fortified outcome gates per PLAN-083 §5.2 row 0.7d:

  (a) Per-profile max-active numeric cap table:
      frontend <= 10, engine <= 12, fintech <= 15,
      trading-readonly <= 8, generic <= 6.

  (b) Context budget cap: SUM(context_budget_tokens) across the active
      set MUST be <=30000 per profile.

  (c) Duplicate-trigger arbitration ordering when 2+ skills share the
      same activation trigger:
        primary key  = top-level `priority` (1=highest .. 10=lowest)
        tie-break #1 = `risk_class` ascending (low=0, medium=1, high=2)
        tie-break #2 = lexicographic skill path

  (d) Dormant suppression: skills with `inactive_but_retained: true` or
      whose profile binding is absent / `active: false` are never surfaced.

  (e) Emits `smart_loading_resolved` audit action with the Sec MF-3
      whitelist: {profile, active_count, suppressed_count,
      context_total_tokens, arbitration_dropped_count}.

Inputs:
  - `.claude/repo-profile.yaml` (sub-agent 0.6 detect-repo-profile.py
    output). Only `risk_class` is consumed here.
  - Glob of SKILL.md files (default `.claude/skills/**/SKILL.md`).
    Each file's YAML frontmatter is parsed for the smart-loading
    subset defined by repo-profile-skill-binding.schema.json (Wave -1.3).

Stdlib-only. Python 3.9+. No yaml dependency (uses a strict mini-parser
sufficient for the smart-loading subset; foreign-fields tolerated).

CLI:
  python3 smart-loading-resolver.py resolve [--profile-file PATH]
      [--skill-glob GLOB] [--cap-table PATH] [--json]
  env CEO_SMART_LOADING_DEBUG=1 emits filtered-out reasons.

Library API:
  from smart_loading_resolver import resolve
  result = resolve(profile_path, skill_root, cap_table_path)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Profile names match repo-profile-skill-binding.schema.json + repo-profile.schema.json
_VALID_PROFILES = ("frontend", "engine", "fintech", "trading-readonly", "generic")

# risk_class ordering for tie-break #1 (lower = preferred, less surprising).
_RISK_RANK = {"low": 0, "medium": 1, "high": 2}

# Audit-emit Sec MF-3 whitelist (mirrored in smart_loading_resolved-emit.patch).
_AUDIT_ALLOWED_FIELDS = frozenset({
    "profile",
    "active_count",
    "suppressed_count",
    "context_total_tokens",
    "arbitration_dropped_count",
})


# ---------------------------------------------------------------------------
# Module-level resolver cache (ADR-090 ref/inline split — PLAN-086 Wave H)
# ---------------------------------------------------------------------------
# Cache key: (skill_root mtime_ns, skill_root inode). Invalidated when the
# skill_root directory mtime OR inode changes. M-13 fold: invalidation
# verified by call-count spy, NOT timing assertion.
_skill_root_cache: Optional[List[Dict[str, Any]]] = None
_cache_key: Optional[Tuple[float, int]] = None  # (mtime_ns, inode)


# ---------------------------------------------------------------------------
# File-backed frontmatter cache (PLAN-094 Wave B / R-039)
# ---------------------------------------------------------------------------
# Persists per-SKILL.md parse across sessions. Composite key per spec
# §B.2: (mtime_ns, inode, file_size, sha256_first_512) — sha256 of first
# 512 bytes is the tie-breaker on macOS HFS+ 1s mtime granularity (Risk R2).
# Cache file is gitignored (.gitignore line 87: `.claude/cache/`).
# AC3 target: hit-rate ≥0.95 across session-restart cycles.

_FRONTMATTER_CACHE_VERSION = 1
_FRONTMATTER_CACHE_FILENAME = "skill_frontmatter_v1.json"
_FRONTMATTER_CACHE_BYTES_PROBE = 512  # sha256 over first N bytes for tie-break

# Session-scoped hit/miss counters surfaced via skill_cache_stats audit emit
# at session-end. Zero-cost when emit path is unwired.
_CACHE_HITS = 0
_CACHE_MISSES = 0
_CACHE_ERRORS = 0


# ---------------------------------------------------------------------------
# Minimal YAML loader (stdlib-only) for the smart-loading subset
# ---------------------------------------------------------------------------

class _ParseError(Exception):
    """Raised when YAML-like input is malformed beyond the supported subset."""


def _strip_comment(s: str) -> str:
    """Strip inline `# ...` comments outside of quotes."""
    out_chars: List[str] = []
    in_single = False
    in_double = False
    for ch in s:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            break
        out_chars.append(ch)
    return "".join(out_chars).rstrip()


def _parse_scalar(raw: str) -> Any:
    """Parse a YAML scalar: bool / int / null / str (quoted or bare)."""
    s = raw.strip()
    if not s:
        return ""
    if s.lower() in ("true", "yes"):
        return True
    if s.lower() in ("false", "no"):
        return False
    if s.lower() in ("null", "~"):
        return None
    # Quoted string
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    # Integer
    try:
        return int(s)
    except ValueError:
        pass
    # Plain string
    return s


def _parse_inline_mapping(s: str) -> Dict[str, Any]:
    """Parse a flow-style `{k: v, k2: v2}` mapping (single line, no nesting)."""
    s = s.strip()
    if not (s.startswith("{") and s.endswith("}")):
        raise _ParseError(f"expected flow mapping, got: {s!r}")
    inner = s[1:-1].strip()
    if not inner:
        return {}
    result: Dict[str, Any] = {}
    # Split by commas not inside quotes
    parts: List[str] = []
    buf: List[str] = []
    in_single = False
    in_double = False
    depth = 0
    for ch in inner:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "{" and not in_single and not in_double:
            depth += 1
        elif ch == "}" and not in_single and not in_double:
            depth -= 1
        if ch == "," and not in_single and not in_double and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    for part in parts:
        if ":" not in part:
            raise _ParseError(f"missing ':' in inline-mapping part: {part!r}")
        k, _, v = part.partition(":")
        result[k.strip()] = _parse_scalar(v)
    return result


def _parse_inline_list(s: str) -> List[Any]:
    """Parse a flow-style `[a, b, c]` list (single line, scalars only)."""
    s = s.strip()
    if not (s.startswith("[") and s.endswith("]")):
        raise _ParseError(f"expected flow list, got: {s!r}")
    inner = s[1:-1].strip()
    if not inner:
        return []
    items: List[Any] = []
    buf: List[str] = []
    in_single = False
    in_double = False
    for ch in inner:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        if ch == "," and not in_single and not in_double:
            items.append(_parse_scalar("".join(buf)))
            buf = []
        else:
            buf.append(ch)
    if buf:
        items.append(_parse_scalar("".join(buf)))
    return items


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_yaml_block(lines: List[str]) -> Dict[str, Any]:
    """Parse a tiny subset of YAML: nested mappings (2+ spaces) and flow
    inline mappings/lists. Tolerates foreign fields (description, name,
    triggers, owner...) without choking. Sufficient for SKILL.md
    frontmatter parsing in PLAN-083 scope.
    """
    result: Dict[str, Any] = {}
    # Walk lines with an index so block scalars can swallow children.
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = _strip_comment(raw)
        if not line.strip():
            i += 1
            continue
        if line.lstrip().startswith("#"):
            i += 1
            continue
        indent = _indent_of(line)
        if indent != 0:
            # not a top-level key; skip (unsupported block element)
            i += 1
            continue
        # Top-level `key: value` or `key:\n  nested`
        if ":" not in line:
            i += 1
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            # Nested mapping or list. Collect indented children.
            children: List[str] = []
            j = i + 1
            while j < len(lines):
                child_raw = lines[j]
                if not child_raw.strip():
                    j += 1
                    continue
                child_indent = _indent_of(child_raw)
                if child_indent == 0 and child_raw.lstrip()[:1] not in ("-",):
                    break
                children.append(child_raw)
                j += 1
            # Detect list-of-mappings vs nested mapping
            is_list = any(c.lstrip().startswith("- ") or c.lstrip() == "-" for c in children)
            if is_list:
                lst: List[Any] = []
                for c in children:
                    cs = _strip_comment(c).lstrip()
                    if cs.startswith("- "):
                        item = cs[2:].strip()
                        if item.startswith("{") and item.endswith("}"):
                            try:
                                lst.append(_parse_inline_mapping(item))
                            except _ParseError:
                                lst.append(item)
                        else:
                            lst.append(_parse_scalar(item))
                result[key] = lst
            else:
                # Nested mapping; dedent by min child indent
                if not children:
                    result[key] = {}
                else:
                    nested: Dict[str, Any] = {}
                    min_indent = min(_indent_of(c) for c in children if c.strip())
                    for c in children:
                        if not c.strip():
                            continue
                        sub = c[min_indent:]
                        sub = _strip_comment(sub)
                        if ":" not in sub:
                            continue
                        sk, _, sv = sub.partition(":")
                        sk = sk.strip()
                        sv = sv.strip()
                        if sv == "":
                            nested[sk] = {}
                        elif sv.startswith("{") and sv.endswith("}"):
                            try:
                                nested[sk] = _parse_inline_mapping(sv)
                            except _ParseError:
                                nested[sk] = sv
                        elif sv.startswith("[") and sv.endswith("]"):
                            try:
                                nested[sk] = _parse_inline_list(sv)
                            except _ParseError:
                                nested[sk] = sv
                        else:
                            nested[sk] = _parse_scalar(sv)
                    result[key] = nested
            i = j
            continue
        # Inline value on same line
        if rest.startswith("{") and rest.endswith("}"):
            try:
                result[key] = _parse_inline_mapping(rest)
            except _ParseError:
                result[key] = rest
        elif rest.startswith("[") and rest.endswith("]"):
            try:
                result[key] = _parse_inline_list(rest)
            except _ParseError:
                result[key] = rest
        else:
            result[key] = _parse_scalar(rest)
        i += 1
    return result


def _extract_frontmatter(text: str) -> Optional[str]:
    """Extract the YAML frontmatter block bracketed by `---` lines."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    end_idx: Optional[int] = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return None
    return "\n".join(lines[1:end_idx])


def _cache_file_path() -> Path:
    """Cache file location under repo `.claude/cache/` (gitignored).

    Override with `CEO_SKILL_FRONTMATTER_CACHE_PATH` (test isolation).
    """
    override = os.environ.get("CEO_SKILL_FRONTMATTER_CACHE_PATH", "").strip()
    if override:
        return Path(override)
    return Path.cwd() / ".claude" / "cache" / _FRONTMATTER_CACHE_FILENAME


def _cache_disabled() -> bool:
    """Kill-switch for PLAN-094 Wave B file-backed cache. Reverts to
    parse-every-call behavior; module-level _skill_root_cache still applies."""
    return os.environ.get("CEO_SKILL_FRONTMATTER_CACHE_DISABLED", "") == "1"


def _compute_cache_key(path: Path) -> Optional[Dict[str, Any]]:
    """Return composite cache key or None on stat failure.

    Composite per PLAN-094 §B.2: (mtime_ns, inode, file_size, sha256_first_512).
    sha256-of-first-512-bytes resolves Risk R2 (macOS HFS+ 1s mtime granularity).
    """
    import hashlib
    try:
        st = path.stat()
    except OSError:
        return None
    try:
        with open(path, "rb") as f:
            head = f.read(_FRONTMATTER_CACHE_BYTES_PROBE)
    except OSError:
        return None
    return {
        "mtime_ns": st.st_mtime_ns,
        "inode": st.st_ino,
        "size": st.st_size,
        "sha256_first_512": hashlib.sha256(head).hexdigest(),
    }


def _load_cache_file() -> Dict[str, Dict[str, Any]]:
    """Load disk cache; fail-open → empty dict on any error."""
    cache_path = _cache_file_path()
    if not cache_path.is_file():
        return {}
    try:
        raw = cache_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    if data.get("version") != _FRONTMATTER_CACHE_VERSION:
        return {}
    entries = data.get("entries")
    if not isinstance(entries, dict):
        return {}
    return entries


def _persist_cache_file(entries: Dict[str, Dict[str, Any]]) -> None:
    """Atomic-rename write of cache. Fail-open on any I/O error."""
    cache_path = _cache_file_path()
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    payload = {"version": _FRONTMATTER_CACHE_VERSION, "entries": entries}
    tmp = cache_path.with_suffix(cache_path.suffix + ".tmp")
    try:
        tmp.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        os.replace(tmp, cache_path)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


_LOADED_CACHE: Optional[Dict[str, Dict[str, Any]]] = None
_CACHE_DIRTY = False


def _get_loaded_cache() -> Dict[str, Dict[str, Any]]:
    """Lazy-load disk cache once per process; subsequent calls return same dict."""
    global _LOADED_CACHE  # noqa: PLW0603
    if _LOADED_CACHE is None:
        _LOADED_CACHE = _load_cache_file()
    return _LOADED_CACHE


def flush_cache() -> None:
    """Persist in-memory cache delta to disk if dirty. Fail-open."""
    global _CACHE_DIRTY  # noqa: PLW0603
    if not _CACHE_DIRTY or _LOADED_CACHE is None:
        return
    _persist_cache_file(_LOADED_CACHE)
    _CACHE_DIRTY = False


def cache_stats() -> Dict[str, int]:
    """Return session-scoped cache counters for skill_cache_stats audit emit."""
    return {
        "hit_count": _CACHE_HITS,
        "miss_count": _CACHE_MISSES,
        "error_count": _CACHE_ERRORS,
    }


def parse_skill_frontmatter(path: Path) -> Optional[Dict[str, Any]]:
    """Parse a SKILL.md file's frontmatter. Returns None when missing/malformed.

    PLAN-094 Wave B: consults `.claude/cache/skill_frontmatter_v1.json`
    keyed by (mtime_ns, inode, size, sha256_first_512) composite. On cache
    hit, returns the persisted parsed dict; on miss, parses + writes back.
    Kill-switch: CEO_SKILL_FRONTMATTER_CACHE_DISABLED=1.
    """
    global _CACHE_HITS, _CACHE_MISSES, _CACHE_ERRORS, _CACHE_DIRTY  # noqa: PLW0603

    if _cache_disabled():
        return _parse_skill_frontmatter_uncached(path)

    key = _compute_cache_key(path)
    if key is None:
        _CACHE_ERRORS += 1
        return _parse_skill_frontmatter_uncached(path)

    cache = _get_loaded_cache()
    path_str = str(path)
    cached = cache.get(path_str)
    if cached is not None:
        cached_key = cached.get("key")
        if cached_key == key:
            _CACHE_HITS += 1
            frontmatter = cached.get("frontmatter")
            if isinstance(frontmatter, dict):
                return dict(frontmatter)  # defensive copy — callers may mutate

    _CACHE_MISSES += 1
    parsed = _parse_skill_frontmatter_uncached(path)
    if parsed is not None:
        cache[path_str] = {"key": key, "frontmatter": parsed}
        _CACHE_DIRTY = True
    return parsed


def _parse_skill_frontmatter_uncached(path: Path) -> Optional[Dict[str, Any]]:
    """Inner parse without cache lookup. Public path = parse_skill_frontmatter."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    block = _extract_frontmatter(text)
    if block is None:
        return None
    try:
        data = _parse_yaml_block(block.split("\n"))
    except _ParseError:
        return None
    # Inject canonical path for arbitration tie-break #2
    try:
        data["_path"] = str(path)
    except Exception:
        pass
    return data


# ---------------------------------------------------------------------------
# Cap-table loader
# ---------------------------------------------------------------------------

def load_cap_table(path: Path) -> Dict[str, Dict[str, int]]:
    """Load the per-profile cap table.

    File is YAML by convention but also accepts JSON (same path .json or
    `--cap-table` pointing at .json). Strict structure:

        version: 1
        profiles:
          <profile>: {max_active: int, context_budget_tokens: int}
    """
    if not path.is_file():
        raise _ParseError(f"cap-table not found: {path}")
    text = path.read_text(encoding="utf-8")
    # JSON fast-path
    stripped = text.lstrip()
    if stripped.startswith("{"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise _ParseError(f"invalid JSON cap-table: {e}")
    else:
        data = _parse_yaml_block(text.split("\n"))
    profiles = data.get("profiles", {})
    if not isinstance(profiles, dict):
        raise _ParseError("cap-table.profiles must be a mapping")
    out: Dict[str, Dict[str, int]] = {}
    for prof in _VALID_PROFILES:
        entry = profiles.get(prof)
        if not isinstance(entry, dict):
            raise _ParseError(f"cap-table.profiles.{prof} missing or malformed")
        try:
            max_active = int(entry.get("max_active", 0))
            ctx_budget = int(entry.get("context_budget_tokens", 0))
        except (TypeError, ValueError) as e:
            raise _ParseError(f"cap-table.profiles.{prof} non-int field: {e}")
        if max_active < 1:
            raise _ParseError(f"cap-table.profiles.{prof}.max_active < 1")
        if ctx_budget < 0:
            raise _ParseError(f"cap-table.profiles.{prof}.context_budget_tokens < 0")
        out[prof] = {"max_active": max_active, "context_budget_tokens": ctx_budget}
    return out


# ---------------------------------------------------------------------------
# Repo-profile reader (only `risk_class` consumed)
# ---------------------------------------------------------------------------

def read_repo_profile(path: Path) -> str:
    """Return the `risk_class` from .claude/repo-profile.yaml.

    Fail-CLOSED: any parse problem returns 'trading-readonly' per
    PLAN-083 §7.1.
    """
    if not path.is_file():
        return "trading-readonly"
    try:
        text = path.read_text(encoding="utf-8")
        data = _parse_yaml_block(text.split("\n"))
    except (OSError, UnicodeDecodeError, _ParseError):
        return "trading-readonly"
    rc = data.get("risk_class")
    if rc in _VALID_PROFILES:
        return rc  # type: ignore[return-value]
    # unknown-needs-owner-confirmation OR malformed -> fail-CLOSED
    return "trading-readonly"


# ---------------------------------------------------------------------------
# Candidate extraction + arbitration
# ---------------------------------------------------------------------------

def _candidate_for_profile(
    skill: Dict[str, Any], profile: str
) -> Optional[Dict[str, Any]]:
    """Return a normalized candidate record or None when the skill is
    suppressed for this profile.
    """
    if not isinstance(skill, dict):
        return None
    if bool(skill.get("inactive_but_retained")):
        return None
    binding = skill.get("repo_profile_binding")
    if not isinstance(binding, dict):
        return None
    entry = binding.get(profile)
    if not isinstance(entry, dict):
        return None
    if not bool(entry.get("active")):
        return None
    # Top-level required fields
    priority = skill.get("priority")
    risk_class = skill.get("risk_class")
    if not isinstance(priority, int) or not isinstance(risk_class, str):
        return None
    if risk_class not in _RISK_RANK:
        return None
    # Per-profile sub-key (tie-break #0 within profile, used after global priority)
    profile_priority = entry.get("priority")
    if not isinstance(profile_priority, int):
        profile_priority = priority
    path = skill.get("_path", "")
    ctx_tokens = skill.get("context_budget_tokens")
    if not isinstance(ctx_tokens, int):
        ctx_tokens = 0
    return {
        "path": path,
        "priority": priority,
        "profile_priority": profile_priority,
        "risk_class": risk_class,
        "risk_rank": _RISK_RANK[risk_class],
        "context_budget_tokens": max(0, int(ctx_tokens)),
        "activation_triggers": skill.get("activation_triggers", []) or [],
    }


def _sort_key(c: Dict[str, Any]) -> Tuple[int, int, int, str]:
    """Deterministic arbitration sort key per spec.

    Lower tuple sorts first (selected first).
    """
    return (
        int(c["priority"]),         # primary: 1 wins over 10
        int(c["risk_rank"]),        # tie #1: low < medium < high
        int(c["profile_priority"]), # tie #1b: per-profile priority
        str(c["path"]),             # tie #2: lex skill path
    )


def _trigger_signature(t: Any) -> str:
    """Canonical signature for a single activation trigger (for dedupe)."""
    if not isinstance(t, dict):
        return ""
    event = str(t.get("event", "")).strip()
    glob = str(t.get("glob", "")).strip()
    regex = str(t.get("regex", "")).strip()
    return f"{event}|{glob}|{regex}"


def _arbitrate_duplicate_triggers(
    candidates: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], int, List[Tuple[str, str]]]:
    """When 2+ candidates share an activation trigger, keep only the
    arbitration winner per the spec sort key. Returns (kept, dropped_count,
    drop_reasons).
    """
    # Build (signature -> [candidates]) grouping
    sig_groups: Dict[str, List[Dict[str, Any]]] = {}
    no_triggers: List[Dict[str, Any]] = []
    for c in candidates:
        triggers = c.get("activation_triggers") or []
        if not triggers:
            no_triggers.append(c)
            continue
        for t in triggers:
            sig = _trigger_signature(t)
            if not sig:
                continue
            sig_groups.setdefault(sig, []).append(c)
    # Determine losers: for each signature with >1 candidate, all but the
    # sort-key winner are losers under that signature.
    loser_paths: Dict[str, str] = {}
    for sig, group in sig_groups.items():
        if len(group) <= 1:
            continue
        ranked = sorted(group, key=_sort_key)
        winner = ranked[0]
        for c in ranked[1:]:
            # Only drop if winner is not the same candidate (paths differ)
            if c["path"] != winner["path"]:
                loser_paths[c["path"]] = f"duplicate_trigger:{sig}->winner:{winner['path']}"
    kept: List[Dict[str, Any]] = []
    drop_reasons: List[Tuple[str, str]] = []
    seen_paths = set()
    for c in candidates:
        if c["path"] in loser_paths:
            drop_reasons.append((c["path"], loser_paths[c["path"]]))
            continue
        if c["path"] in seen_paths:
            continue
        seen_paths.add(c["path"])
        kept.append(c)
    return kept, len(loser_paths), drop_reasons


# ---------------------------------------------------------------------------
# Main resolve() entry point
# ---------------------------------------------------------------------------

def _load_skill_root(
    skill_root: Path,
    skill_glob: str = "**/SKILL.md",
) -> List[Dict[str, Any]]:
    """Walk skill_root and parse SKILL.md frontmatter. Pure disk-reader.

    PLAN-086 Wave H (M-13): extracted so the call-count spy in
    test_smart_loading_resolver_caching.py can target this function
    deterministically. Caching lives in resolve(); this is the cache-miss
    payload only.
    """
    skill_paths = sorted(skill_root.glob(skill_glob))
    skills: List[Dict[str, Any]] = []
    for p in skill_paths:
        meta = parse_skill_frontmatter(p)
        if meta is None:
            continue
        skills.append(meta)
    return skills


def resolve(
    profile_path: Path,
    skill_root: Path,
    cap_table_path: Path,
    skill_glob: str = "**/SKILL.md",
    debug: bool = False,
) -> Dict[str, Any]:
    """Resolve the active skill set for the repo profile.

    Returns a structured result dict with the Sec MF-3 whitelist fields
    plus a debug `dropped` list when `debug=True`.

    PLAN-086 Wave H: module-level (mtime_ns, inode) cache. Second call
    with unchanged skill_root returns cached skill list without re-globbing.
    """
    global _skill_root_cache, _cache_key  # noqa: PLW0603

    profile = read_repo_profile(profile_path)
    cap_table = load_cap_table(cap_table_path)

    current_key: Optional[Tuple[float, int]]
    try:
        st = skill_root.stat()
        current_key = (st.st_mtime_ns, st.st_ino)
    except OSError:
        current_key = None

    if (
        current_key is not None
        and current_key == _cache_key
        and _skill_root_cache is not None
    ):
        skills = _skill_root_cache
    else:
        skills = _load_skill_root(skill_root, skill_glob)
        _skill_root_cache = skills
        _cache_key = current_key

    return _resolve_from_skills(skills, profile, cap_table, debug=debug)


def _resolve_from_skills(
    skills: List[Dict[str, Any]],
    profile: str,
    cap_table: Dict[str, Dict[str, int]],
    debug: bool = False,
) -> Dict[str, Any]:
    """Pure-function resolve over already-parsed skill frontmatter dicts.

    Split out so tests can drive the algorithm without on-disk SKILL.md
    files.
    """
    if profile not in cap_table:
        # Shouldn't happen because read_repo_profile guarantees a known
        # profile or fail-CLOSED -> trading-readonly. Defensive fallback.
        profile = "trading-readonly"
    caps = cap_table[profile]
    max_active = int(caps["max_active"])
    ctx_budget_cap = int(caps["context_budget_tokens"])

    total_skills = len(skills)
    dropped_reasons: List[Tuple[str, str]] = []

    # Stage 1: filter to candidates active for this profile
    candidates: List[Dict[str, Any]] = []
    for s in skills:
        c = _candidate_for_profile(s, profile)
        if c is None:
            dropped_reasons.append((s.get("_path", "?"), "dormant_or_inactive"))
            continue
        candidates.append(c)
    suppressed_dormant = total_skills - len(candidates)

    # Stage 2: arbitrate duplicate-trigger ties
    candidates, arbitration_dropped_count, arb_reasons = _arbitrate_duplicate_triggers(candidates)
    dropped_reasons.extend(arb_reasons)

    # Stage 3: sort by spec key, take top N up to max_active
    ranked = sorted(candidates, key=_sort_key)
    if len(ranked) > max_active:
        for losing in ranked[max_active:]:
            dropped_reasons.append((losing["path"], f"max_active_cap_{max_active}"))
        ranked = ranked[:max_active]

    # Stage 4: enforce context budget cap.
    # Strategy: greedy by sort key; if the running sum exceeds budget,
    # drop the highest-priority-number entries (the least important
    # remaining) until under. Because `ranked` is sorted ascending by
    # priority (1=highest), we drop from the tail.
    current_total = sum(c["context_budget_tokens"] for c in ranked)
    while current_total > ctx_budget_cap and ranked:
        dropped = ranked.pop()
        dropped_reasons.append((dropped["path"], f"context_budget_cap_{ctx_budget_cap}"))
        current_total -= dropped["context_budget_tokens"]

    active_set = ranked
    active_count = len(active_set)
    context_total_tokens = sum(c["context_budget_tokens"] for c in active_set)
    suppressed_count = total_skills - active_count

    # Defensive: enforce Sec MF-3 whitelist on the audit payload
    audit_event = {
        "profile": profile,
        "active_count": active_count,
        "suppressed_count": suppressed_count,
        "context_total_tokens": context_total_tokens,
        "arbitration_dropped_count": arbitration_dropped_count,
    }
    forbidden = set(audit_event.keys()) - _AUDIT_ALLOWED_FIELDS
    if forbidden:  # defensive — should be unreachable
        for f in forbidden:
            audit_event.pop(f, None)

    result: Dict[str, Any] = {
        "profile": profile,
        "active_count": active_count,
        "suppressed_count": suppressed_count,
        "context_total_tokens": context_total_tokens,
        "arbitration_dropped_count": arbitration_dropped_count,
        "max_active_cap": max_active,
        "context_budget_cap": ctx_budget_cap,
        "active_skills": [c["path"] for c in active_set],
        "audit_emit_payload": audit_event,
    }
    if debug:
        result["dropped"] = [
            {"path": p, "reason": r} for (p, r) in dropped_reasons
        ]
    return result


# ---------------------------------------------------------------------------
# Audit-emit hook (optional integration; safe no-op if hooks unavailable)
# ---------------------------------------------------------------------------

def emit_smart_loading_resolved(payload: Dict[str, Any]) -> None:
    """Emit the `smart_loading_resolved` audit action via the framework's
    `_lib.audit_emit.emit_generic`. Failure is silent (fail-open).

    Note: action registration (`smart_loading_resolved` in
    `_KNOWN_ACTIONS` + SPEC row + tests) is the responsibility of the
    Wave 0b ceremony folded patch (`smart_loading_resolved-emit.patch`).
    Until the patch lands, `emit_generic` will breadcrumb-and-skip per
    the fail-open invariant.
    """
    # Sec MF-3 whitelist check: only the 5 allowed fields make it through
    safe_payload = {
        k: v for (k, v) in payload.items() if k in _AUDIT_ALLOWED_FIELDS
    }
    try:
        # Lazy import so the resolver remains useful in target repos
        # that haven't installed the framework's hooks/_lib.
        repo_root = Path(__file__).resolve().parents[3]
        hooks_dir = repo_root / ".claude" / "hooks"
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib import audit_emit  # type: ignore[import-not-found]
        audit_emit.emit_generic("smart_loading_resolved", **safe_payload)
    except Exception:
        # fail-open per framework discipline
        pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_cap_table_path() -> Path:
    # PLAN-085 Wave A.2 (R-002): canonical location is .claude/policies/
    # (sibling to other policy YAMLs: bash-safety.policy.yaml,
    # plan-edit.policy.yaml, grandfather-cap.policy.yaml,
    # secret-patterns-exchange.yaml). Resolver script lives at
    # .claude/scripts/, so go up one and into policies/.
    script_dir = Path(__file__).resolve().parent
    canonical = script_dir.parent / "policies" / "smart-loading-cap-table.yaml"
    if canonical.is_file():
        return canonical
    # Back-compat fallback: pre-Wave-A installs (or in-place adopters
    # with stale framework copy) may still carry the YAML at the old
    # script-sibling path. Honor it if present so existing call sites
    # don't break before adopters upgrade.
    legacy = script_dir / "smart-loading-cap-table.yaml"
    if legacy.is_file():
        return legacy
    # Default: canonical path (resolver consumer reports
    # missing-file error with the correct expected location).
    return canonical


def _default_profile_path() -> Path:
    cwd = Path.cwd()
    return cwd / ".claude" / "repo-profile.yaml"


def _default_skill_root() -> Path:
    return Path.cwd() / ".claude" / "skills"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Smart-loading resolver — PLAN-083 Wave 0b sub-agent 0.7d."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_res = sub.add_parser("resolve", help="Resolve active skill set for the repo profile.")
    p_res.add_argument("--profile-file", type=Path, default=None)
    p_res.add_argument("--skill-root", type=Path, default=None)
    p_res.add_argument("--skill-glob", type=str, default="**/SKILL.md")
    p_res.add_argument("--cap-table", type=Path, default=None)
    p_res.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    p_res.add_argument(
        "--emit-audit",
        action="store_true",
        help="Emit smart_loading_resolved audit event after resolve.",
    )
    args = parser.parse_args(argv)
    if args.cmd != "resolve":
        parser.error("only `resolve` subcommand is implemented")
        return 2

    profile_path = args.profile_file or _default_profile_path()
    skill_root = args.skill_root or _default_skill_root()
    cap_table_path = args.cap_table or _default_cap_table_path()
    debug = os.environ.get("CEO_SMART_LOADING_DEBUG", "") == "1"

    try:
        result = resolve(
            profile_path=profile_path,
            skill_root=skill_root,
            cap_table_path=cap_table_path,
            skill_glob=args.skill_glob,
            debug=debug,
        )
    except _ParseError as e:
        print(f"smart-loading-resolver: {e}", file=sys.stderr)
        return 2

    if args.emit_audit:
        emit_smart_loading_resolved(result["audit_emit_payload"])

    # PLAN-094 Wave B: persist file-backed cache delta on CLI exit.
    flush_cache()

    if args.json:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        print(f"profile: {result['profile']}")
        print(f"active_count: {result['active_count']}")
        print(f"suppressed_count: {result['suppressed_count']}")
        print(f"context_total_tokens: {result['context_total_tokens']}")
        print(f"arbitration_dropped_count: {result['arbitration_dropped_count']}")
        print(f"max_active_cap: {result['max_active_cap']}")
        print(f"context_budget_cap: {result['context_budget_cap']}")
        if debug:
            print(f"--- dropped ({len(result.get('dropped', []))}) ---")
            for d in result.get("dropped", []):
                print(f"  {d['reason']}: {d['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
