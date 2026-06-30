#!/usr/bin/env python3
"""PLAN-091 Wave A.1 — 16th Tier-S check `check_tier_policy_misrouting_24h`.

Detects tier-policy misrouting in the last 24h of audit-log.jsonl by
comparing dispatched model slugs against the canonical recommendation
from `_lib/model_routing.resolve()`.

## Contract

Signature mirrors the existing Tier-S checks in `ceo-boot.py`:

    () -> Tuple[str, str, Optional[Dict[str, Any]]]

Status semantics per PLAN-065 §4.3.2 + matching the 15 existing
Tier-S checks (`green` / `yellow` / `red`):

- `green`  — misrouting ratio < 5% OR no `model_routing_advised`
             events in the 24h window (insufficient data).
- `yellow` — 5% ≤ misrouting ratio < 10% OR fail-soft path
             (audit-log absent, router unavailable, unreadable file).
- `red`    — misrouting ratio ≥ 10%.

## Fail-soft contract

This check NEVER raises — every exception path returns a non-error
status tuple. The dispatcher in `ceo-boot.py:_wrap_check()` already
catches at the boundary, but defensive fallbacks here keep the
return shape stable for direct callers (CLI smoke-test entry).

## Audit-log resolution

The check resolves the audit-log path using the same lookup chain
documented in `_lib/audit_emit.py`:

1. `CLAUDE_PROJECT_DIR` env (when set, points at the project's
   `~/.claude/projects/<slug>/` directory directly).
2. Fallback: derive `<slug>` from `Path(__file__).parents[2]` repo
   root and look up `~/.claude/projects/<slug>/audit-log.jsonl`.

A `None` result skips with `yellow` (audit-log absent).

## References

- PLAN-088 §AC11 (18-check Tier-S harness target; this is the
  16th of 18; A.7 lands the remaining 17th + 18th).
- PLAN-091 §4 A.1 (this wave's spec).
- PLAN-086 R-019 (model_routing.resolve foundation).
- ADR-052 (role-to-model dispatch contract).

Stdlib-only. Python ≥3.9. `from __future__ import annotations`.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _audit_log_path() -> Optional[Path]:
    """Resolve audit-log.jsonl path; None when unavailable.

    Lookup order (PLAN-106 Wave D — corrected 2026-05-18):

    1. ``CLAUDE_PROJECT_DIR`` env (when set, points at project root
       or audit-log parent directly).
    2. Fallback A: ``~/.claude/projects/<repo_basename>/audit-log.jsonl``
       (CEO-curated convention; matches ``ceo-boot.py:73`` hardcode +
       CLAUDE.md §3 audit-log location).
    3. Fallback B: ``~/.claude/projects/<slug>/audit-log.jsonl`` where
       ``slug`` = dash-replaced absolute path (legacy harness session-
       state convention; retained for installations that follow the
       harness slug-style directory layout).
    """
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if env_dir:
        candidate = Path(env_dir).expanduser() / "audit-log.jsonl"
        if candidate.exists():
            return candidate
    try:
        repo_root = Path(__file__).resolve().parents[2]
    except (OSError, IndexError):
        return None
    # Wave D fix: prefer CEO-curated basename convention.
    home_path_basename = (
        Path.home() / ".claude" / "projects" / repo_root.name / "audit-log.jsonl"
    )
    if home_path_basename.exists():
        return home_path_basename
    # Fallback to legacy harness slug-style.
    slug = "-" + str(repo_root).replace("/", "-").lstrip("-")
    home_path_slug = (
        Path.home() / ".claude" / "projects" / slug / "audit-log.jsonl"
    )
    if home_path_slug.exists():
        return home_path_slug
    return None


def _resolver() -> Optional[Any]:
    """Lazy-import model_routing.resolve; None if unavailable."""
    try:
        hooks_dir = Path(__file__).resolve().parent
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib.model_routing import resolve  # type: ignore
        return resolve
    except Exception:  # noqa: BLE001
        return None


def check_tier_policy_misrouting_24h() -> Tuple[str, str, Optional[Dict[str, Any]]]:
    """16th Tier-S check — tier-policy misrouting ratio in 24h window."""
    try:
        path = _audit_log_path()
        if path is None:
            return "yellow", "audit-log.jsonl absent", None
        resolve = _resolver()
        if resolve is None:
            return "yellow", "router unavailable", None

        cutoff = time.time() - 86400.0  # 24h window
        misrouted = 0
        total = 0
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        obj = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(obj, dict):
                        continue
                    if obj.get("event") != "model_routing_advised":
                        continue
                    ts = obj.get("ts", obj.get("timestamp", 0))
                    if isinstance(ts, (int, float)) and ts and ts < cutoff:
                        continue
                    task_class = obj.get("task_class") or ""
                    model_advised = (
                        obj.get("model_advised")
                        or obj.get("model")
                        or ""
                    )
                    if not task_class or not model_advised:
                        continue
                    expected = resolve(task_class)
                    if not expected:
                        # Unknown task_class: router cannot classify, so
                        # the entry is excluded from the misrouting ratio
                        # entirely (avoids false-negatives + false-positives).
                        continue
                    if model_advised != expected:
                        misrouted += 1
                    total += 1
        except OSError:
            return "yellow", "audit-log.jsonl unreadable", None

        if total == 0:
            return "green", "no model_routing_advised events in 24h", None

        ratio = misrouted / total
        summary = f"{misrouted}/{total} = {ratio * 100:.0f}% misrouted"
        detail: Dict[str, Any] = {
            "misrouted": misrouted,
            "total": total,
            "ratio": round(ratio, 4),
        }
        if ratio >= 0.10:
            return "red", summary, detail
        if ratio >= 0.05:
            return "yellow", summary, detail
        return "green", summary, detail
    except Exception as exc:  # noqa: BLE001 (Tier-S fail-soft floor)
        return "error", f"{type(exc).__name__}: {exc}", None


if __name__ == "__main__":  # pragma: no cover (CLI smoke-test only)
    status, summary, detail = check_tier_policy_misrouting_24h()
    print(f"{status}: {summary}")
    if detail:
        print(json.dumps(detail, indent=2, sort_keys=True))
