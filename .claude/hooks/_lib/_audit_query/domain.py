"""domain audit-query declarations."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

__all__ = ('_BY_DOMAIN_DEFAULT_WINDOW_DAYS', '_UNKNOWN_BUCKET', '_GRANDFATHER_POLICY_RELPATH', '_parse_domain_date', '_resolve_window_bounds', '_load_sunset_domains', '_parse_sunset_from_policy', '_load_sunset_reopen_options', '_parse_sunset_reopen_flags', '_entry_ts_to_dt', 'cmd_by_domain')

_BY_DOMAIN_DEFAULT_WINDOW_DAYS = 30

# Sentinel used when no dispatch_archetype_hint is available
_UNKNOWN_BUCKET = "UNKNOWN"

# Default policy file location (relative to repo root, resolved at runtime)
_GRANDFATHER_POLICY_RELPATH = ".claude/policies/grandfather-cap.policy.yaml"


def _parse_domain_date(raw: str) -> Optional[datetime]:
    """Parse YYYY-MM-DD into a UTC-aware datetime (midnight UTC).

    Returns None on failure (not sys.exit — caller handles the error).
    """
    try:
        dt = datetime.strptime(raw.strip(), "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _resolve_window_bounds(
    args,
) -> Tuple[Optional[datetime], Optional[datetime], str]:
    """Resolve --window / --start / --end into (start_dt, end_dt, window_label).

    Returns (start_dt, end_dt, label) where:
      - start_dt: inclusive lower bound (UTC midnight); None means no lower bound
      - end_dt:   inclusive upper bound (UTC now for default windows)
      - label:    human-readable description of the window

    Validates start <= end; prints error + sys.exit(1) on invalid input.
    """
    now = datetime.now(timezone.utc)
    # --start / --end take precedence over --window
    start_raw = getattr(args, "start", None)
    end_raw = getattr(args, "end", None)
    window_raw = getattr(args, "window", None) or f"{_BY_DOMAIN_DEFAULT_WINDOW_DAYS}d"

    if start_raw or end_raw:
        if not start_raw or not end_raw:
            print(
                "[audit-query] ERROR: by-domain: --start and --end must both be provided",
                file=sys.stderr,
            )
            sys.exit(1)
        start_dt = _parse_domain_date(start_raw)
        end_dt = _parse_domain_date(end_raw)
        if start_dt is None:
            print(
                f"[audit-query] ERROR: by-domain: invalid --start date {start_raw!r} "
                "(use YYYY-MM-DD)",
                file=sys.stderr,
            )
            sys.exit(1)
        if end_dt is None:
            print(
                f"[audit-query] ERROR: by-domain: invalid --end date {end_raw!r} "
                "(use YYYY-MM-DD)",
                file=sys.stderr,
            )
            sys.exit(1)
        # Make end_dt the end of that calendar day (23:59:59 UTC)
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
        if start_dt > end_dt:
            print(
                f"[audit-query] ERROR: by-domain: --start ({start_raw}) is after "
                f"--end ({end_raw})",
                file=sys.stderr,
            )
            sys.exit(1)
        label = f"{start_raw} to {end_raw}"
        return start_dt, end_dt, label

    # Parse --window (e.g. "30d", "7d")
    m = re.fullmatch(r"(\d+)([dhm])", window_raw.strip().lower())
    if not m:
        print(
            f"[audit-query] ERROR: by-domain: invalid --window {window_raw!r}; "
            "expected e.g. 30d, 7d, 14d",
            file=sys.stderr,
        )
        sys.exit(1)
    n, unit = int(m.group(1)), m.group(2)
    delta = {"d": timedelta(days=n), "h": timedelta(hours=n), "m": timedelta(minutes=n)}[unit]
    start_dt = now - delta
    label = f"trailing {window_raw}"
    return start_dt, now, label


def _load_sunset_domains(args) -> Optional[List[str]]:
    """Load sunset domain list for --check-reopen.

    Sources (in priority order):
    1. CEO_GRANDFATHER_POLICY_PATH env var
    2. <repo_root>/.claude/policies/grandfather-cap.policy.yaml (if exists)
    3. stdin JSON list (if CEO_BY_DOMAIN_SUNSET_STDIN=1)

    Returns a list of domain slugs, or None if the policy file is not found
    and stdin mode is not active. An empty list [] means "policy found but
    no sunset members".
    """
    # Check env override
    policy_path_env = os.environ.get("CEO_GRANDFATHER_POLICY_PATH")
    if policy_path_env:
        p = Path(policy_path_env)
        if p.is_file():
            return _parse_sunset_from_policy(p)
        print(
            f"[audit-query] WARN: CEO_GRANDFATHER_POLICY_PATH={policy_path_env!r} "
            "not found; no sunset list loaded",
            file=sys.stderr,
        )
        return []

    # Try conventional project-relative path via CLAUDE_PROJECT_DIR or cwd
    for base_env in ("CLAUDE_PROJECT_DIR",):
        base = os.environ.get(base_env)
        if base:
            p = Path(base) / _GRANDFATHER_POLICY_RELPATH
            if p.is_file():
                return _parse_sunset_from_policy(p)

    # Try cwd-relative (developer convenience)
    p = Path(_GRANDFATHER_POLICY_RELPATH)
    if p.is_file():
        return _parse_sunset_from_policy(p)

    # Stdin JSON fallback (CEO_BY_DOMAIN_SUNSET_STDIN=1 for testing)
    if os.environ.get("CEO_BY_DOMAIN_SUNSET_STDIN") == "1":
        try:
            raw = sys.stdin.read()
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(x) for x in data if x]
        except (json.JSONDecodeError, OSError):
            pass
        return []

    return None  # policy not found — caller will skip reopen check


def _parse_sunset_from_policy(path: Path) -> List[str]:
    """Extract sunset domain members from grandfather-cap.policy.yaml.

    Parses the YAML manually using stdlib (no PyYAML dependency).
    Looks for `domain_bundles.members:` list block.

    Returns list of domain slug strings (may be empty).
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    # Simple line-based YAML parser for the members list.
    # We scan for "members:" under "domain_bundles:" section.
    in_domain_bundles = False
    in_members = False
    members: List[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped == "domain_bundles:":
            in_domain_bundles = True
            in_members = False
            continue
        if in_domain_bundles:
            # Another top-level key → leave domain_bundles section
            if stripped and not line.startswith(" ") and not line.startswith("\t"):
                in_domain_bundles = False
                in_members = False
                continue
            if stripped == "members:":
                in_members = True
                continue
            if in_members:
                if stripped.startswith("- "):
                    member = stripped[2:].strip()
                    if member:
                        members.append(member)
                elif stripped and not stripped.startswith("-"):
                    # End of list
                    in_members = False

    return members


def _load_sunset_reopen_options(args) -> Optional[Dict[str, bool]]:
    """M2-CDX-4 + M2-CDX-7 (Codex Phase 1 iter 1) — load reopen filter flags.

    Returns dict with `requires_hint_match` and `unknown_excluded` boolean
    flags read from the same grandfather-cap.policy.yaml as
    `_load_sunset_domains`. Defaults to {True, True} if either flag is
    missing/unparseable. Returns None if the policy file is not found.
    """
    # Reuse the same path resolution as _load_sunset_domains for consistency
    policy_path_env = os.environ.get("CEO_GRANDFATHER_POLICY_PATH")
    candidates: List[Path] = []
    if policy_path_env:
        candidates.append(Path(policy_path_env))
    base = os.environ.get("CLAUDE_PROJECT_DIR")
    if base:
        candidates.append(Path(base) / _GRANDFATHER_POLICY_RELPATH)
    candidates.append(Path(_GRANDFATHER_POLICY_RELPATH))

    for p in candidates:
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        return _parse_sunset_reopen_flags(text)
    return None


def _parse_sunset_reopen_flags(text: str) -> Dict[str, bool]:
    """Parse `sunset_reopen_requires_hint_match` and `sunset_reopen_unknown_excluded`.

    Both flags default to True if missing (defensive — secure-by-default).
    """
    requires_hint_match = True
    unknown_excluded = True
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            continue
        if s.startswith("sunset_reopen_requires_hint_match:"):
            v = s.split(":", 1)[1].strip().lower()
            requires_hint_match = (v == "true" or v.startswith("true"))
        elif s.startswith("sunset_reopen_unknown_excluded:"):
            v = s.split(":", 1)[1].strip().lower()
            unknown_excluded = (v == "true" or v.startswith("true"))
    return {
        "requires_hint_match": requires_hint_match,
        "unknown_excluded": unknown_excluded,
    }


def _entry_ts_to_dt(ts: str) -> Optional[datetime]:
    """Parse a log entry `ts` field into a UTC datetime."""
    if not ts:
        return None
    try:
        s = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def cmd_by_domain(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """`audit-query by-domain` — spawn activity grouped by dispatch_archetype_hint.

    PLAN-080 Phase 1 — domain-level observability for squad-bundle governance.

    Groups `agent_spawn` events by `dispatch_archetype_hint` field if present;
    falls back to `archetype` field, then to the "UNKNOWN" bucket. Entries
    outside the requested time window are excluded.

    Output columns:
      Domain | Spawns | First seen | Last seen | hint_coverage_pct

    Sorted deterministically by domain name (alphabetic, UNKNOWN last).

    With --check-reopen: additionally filters to domains present in the sunset
    list from grandfather-cap.policy.yaml. Reports domains with >= 1 spawn
    where hint matches a sunset domain (UNKNOWN excluded per M2-CDX-7).
    """
    start_dt, end_dt, window_label = _resolve_window_bounds(args)

    # Load sunset list + reopen options if --check-reopen requested
    check_reopen = getattr(args, "check_reopen", False)
    sunset_domains: Optional[List[str]] = None
    # M2-CDX-4 + M2-CDX-7 (Codex Phase 1 iter 1): honor policy flags.
    # Defaults match policy semantics when flags missing/unparseable.
    requires_hint_match = True       # sunset_reopen_requires_hint_match (default true per §8)
    unknown_excluded = True          # sunset_reopen_unknown_excluded (M2-CDX-7 default true)
    if check_reopen:
        sunset_domains = _load_sunset_domains(args)
        sunset_options = _load_sunset_reopen_options(args)
        if sunset_options is not None:
            requires_hint_match = sunset_options.get("requires_hint_match", True)
            unknown_excluded = sunset_options.get("unknown_excluded", True)
        if sunset_domains is None:
            print(
                "[audit-query] WARN: by-domain --check-reopen: no sunset policy file "
                "found; skipping reopen filter. Set CEO_GRANDFATHER_POLICY_PATH or "
                "place grandfather-cap.policy.yaml at "
                f"{_GRANDFATHER_POLICY_RELPATH}",
                file=sys.stderr,
            )

    # Aggregation state per domain bucket
    # domain → {spawns, first_ts, last_ts, with_hint, total}
    domain_agg: Dict[str, Dict[str, Any]] = {}

    total_in_window = 0
    total_with_hint = 0

    for e in entries:
        if e.get("action") != "agent_spawn":
            continue

        ts_raw = e.get("ts", "")
        entry_dt = _entry_ts_to_dt(ts_raw)

        # Apply window filter
        if start_dt is not None and entry_dt is not None:
            if entry_dt < start_dt:
                continue
        if end_dt is not None and entry_dt is not None:
            if entry_dt > end_dt:
                continue

        total_in_window += 1

        # Determine domain bucket
        hint = e.get("dispatch_archetype_hint")
        if hint and isinstance(hint, str) and hint.strip():
            domain = hint.strip()
            has_hint = True
            total_with_hint += 1
        else:
            # Fallback: archetype field
            arch = e.get("archetype")
            if arch and isinstance(arch, str) and arch.strip():
                domain = arch.strip()
            else:
                domain = _UNKNOWN_BUCKET
            has_hint = False

        bucket = domain_agg.setdefault(
            domain,
            {
                "spawns": 0,
                "first_ts": ts_raw or "",
                "last_ts": ts_raw or "",
                "with_hint": 0,
                "total": 0,
            },
        )
        bucket["spawns"] += 1
        bucket["total"] += 1
        if has_hint:
            bucket["with_hint"] += 1
        if ts_raw:
            if not bucket["first_ts"] or ts_raw < bucket["first_ts"]:
                bucket["first_ts"] = ts_raw
            if ts_raw > bucket["last_ts"]:
                bucket["last_ts"] = ts_raw

    # Build output rows
    rows: List[Dict[str, Any]] = []
    for domain in sorted(domain_agg.keys(), key=lambda d: ("" if d != _UNKNOWN_BUCKET else "\xff") + d):
        b = domain_agg[domain]
        hint_pct = round(b["with_hint"] / b["total"] * 100, 1) if b["total"] > 0 else 0.0
        row: Dict[str, Any] = {
            "domain": domain,
            "spawns": b["spawns"],
            "first_seen": b["first_ts"][:10] if b["first_ts"] else "",
            "last_seen": b["last_ts"][:10] if b["last_ts"] else "",
            "hint_coverage_pct": hint_pct,
        }
        rows.append(row)

    # Apply --check-reopen filter
    # M2-CDX-7: UNKNOWN excluded when sunset_reopen_unknown_excluded=true (default)
    # M2-CDX-4: When sunset_reopen_requires_hint_match=true (default), only
    #   spawns whose ORIGINAL audit row carried `dispatch_archetype_hint`
    #   (has_hint=True) qualify for reopen. archetype-fallback rows do not
    #   trigger reopen (per PLAN-080 §8: "spawn carries dispatch_archetype_hint
    #   matching the sunset domain's archetype set").
    if check_reopen and sunset_domains is not None:
        sunset_set = set(sunset_domains)
        reopen_rows = []
        for r in rows:
            if unknown_excluded and r["domain"] == _UNKNOWN_BUCKET:
                continue
            if r["domain"] not in sunset_set:
                continue
            if r["spawns"] < 1:
                continue
            if requires_hint_match:
                # Reopen requires at least one hint-source spawn matching this
                # sunset domain. Use the per-bucket `with_hint` count from the
                # aggregation — bucket["with_hint"] tracks how many spawns in
                # this domain bucket arrived with dispatch_archetype_hint set.
                bucket = domain_agg.get(r["domain"], {})
                if int(bucket.get("with_hint", 0)) < 1:
                    continue
            reopen_rows.append(r)
    else:
        reopen_rows = []

    # Build markdown table
    def _md_table(table_rows: List[Dict[str, Any]]) -> str:
        if not table_rows:
            return "| Domain | Spawns | First seen | Last seen | hint_coverage_pct |\n" \
                   "| ------ | ------ | ---------- | --------- | ----------------- |\n" \
                   "| (no results) | - | - | - | - |\n"
        lines = [
            "| Domain | Spawns | First seen | Last seen | hint_coverage_pct |",
            "| ------ | ------ | ---------- | --------- | ----------------- |",
        ]
        for r in table_rows:
            lines.append(
                f"| {r['domain']} | {r['spawns']} | {r['first_seen']} "
                f"| {r['last_seen']} | {r['hint_coverage_pct']}% |"
            )
        return "\n".join(lines) + "\n"

    output: Dict[str, Any] = {
        "query": "by-domain",
        "version": "1",
        "window": window_label,
        "total_spawns_in_window": total_in_window,
        "overall_hint_coverage_pct": (
            round(total_with_hint / total_in_window * 100, 1)
            if total_in_window > 0
            else 0.0
        ),
        "domain_count": len(rows),
        "domains": rows,
        "markdown_table": _md_table(rows),
    }

    if check_reopen:
        output["check_reopen"] = {
            "sunset_domains_loaded": len(sunset_domains) if sunset_domains is not None else 0,
            "reopen_candidates": reopen_rows,
            "reopen_count": len(reopen_rows),
            "note": (
                "Domains from sunset list with >= 1 spawn in window. "
                "UNKNOWN bucket excluded per M2-CDX-7."
            ),
        }

    return output


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


