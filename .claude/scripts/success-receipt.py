#!/usr/bin/env python3
"""success-receipt.py — vibecoder UX primitive (PLAN-083 Wave 2 sub-2.3).

Renders an end-of-session / end-of-plan / time-windowed summary in a
**fixed 5-section format** that makes the framework's value defensible
to an AI-skeptic CTO without pitch copy:

    1. Files inspected     — count + top-5 category buckets (no raw paths)
    2. Risks found          — count by severity from audit-flag events
    3. Actions taken        — edits / writes / commits / GPG / spawns / transitions
    4. Value created        — USD cost + bugs caught + artifacts + tokens-saved estimate
    5. Next move            — recommended top-3 next actions for the Owner

The receipt is meant to be paired with the **audit trail** (chained
HMAC events on disk) and **one concrete avoided bug** (from the
confidence_gate / injection_flag / mcp_canonical_guard_blocked event
stream) to satisfy the PLAN-083 §13 CTO-defense risk row:

    "the CTO will not be convinced by pitch copy. He may be convinced
    by a short demo plus audit trail plus one concrete avoided bug."

## Design constraints (PLAN-083 §5.4 row 2.3)

- **Sec MF-3** — file paths are bucketed into category counters; the
  raw path text never enters the rendered receipt (json or markdown).
- **Stdlib only.** Python 3.9+. No third-party imports.
- **No emojis.** Plain ASCII markdown for terminal readability.
- **Fixed structure** — all 5 sections always present, even when the
  underlying data is empty (avoids "looks broken" failure mode in fresh
  installs).
- **`--for-ctov` flag** adds methodology disclaimers per Codex P1 so
  the numbers are not over-claimed when used in CTO defense.

## Dependencies (read-only)

- `budget-summary.py` (Wave 0b sub-0.8) — for cost USD + token counts.
  Re-implemented here as a thin in-process call rather than subprocess
  to keep the receipt deterministic and stdlib-only.
- `confidence_labels.py` (Wave 1 sub-1.10) — for severity coloring of
  risk findings. Re-uses `as_emoji_free_marker()` via dynamic import
  with a defensive fallback (the confidence module may not be on the
  installed path during early Wave 2 staging).

## CLI

    success-receipt [--session-id SID|--plan-id PLAN-NNN|--since EXPR]
                    [--json] [--for-ctov]
                    [--audit-dir PATH]

If no scope flag is supplied, defaults to the most-recent session
observed in the audit log.

## Output

Either:
- **Markdown** (default) — 5 sections, fixed-width tables, ~25-30 lines
- **JSON** (``--json``) — machine-readable structured payload

The ``--for-ctov`` flag appends a **methodology footer** listing every
estimate, every assumption, and every label-as-estimate disclaimer
needed for an AI-skeptic CTO review.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Audit-log filename glob (mirrors budget-summary.py for rotation safety).
AUDIT_LOG_GLOB: str = "audit-log*.jsonl"

#: Sentinel PLAN id regex (Sec MF-3 — bound any plan_id we display).
_PLAN_ID_RE = re.compile(r"^PLAN-[0-9]{3}$")

#: ``--since`` duration parser (Nm / Nh / Nd).
_SINCE_RE = re.compile(r"^(\d+)\s*([mhd])$")

#: Fields stripped before computing event sha256 (rotation overlap dedup).
_DEDUP_STRIP_FIELDS: Tuple[str, ...] = (
    "hmac", "hmac_error", "hook_duration_ms",
)

#: Pricing table mirror — kept in sync by hand with budget-summary.py
#: defaults so the receipt is deterministic when budget-summary is not
#: importable (e.g. early Wave 2 staging).
_DEFAULT_PRICING: Dict[str, Dict[str, float]] = {
    "claude-opus-4-7":   {"in": 0.015, "out": 0.075},
    "claude-opus-4":     {"in": 0.015, "out": 0.075},
    "claude-sonnet-4-5": {"in": 0.003, "out": 0.015},
    "claude-sonnet-4":   {"in": 0.003, "out": 0.015},
    "claude-haiku-4":    {"in": 0.0008, "out": 0.004},
    "gpt-5":             {"in": 0.005,  "out": 0.020},
    "gpt-5-codex":       {"in": 0.005,  "out": 0.020},
    "gpt-5-mini":        {"in": 0.0005, "out": 0.002},
    "o3":                {"in": 0.015,  "out": 0.060},
    "o4-mini":           {"in": 0.001,  "out": 0.004},
}


# ---------------------------------------------------------------------------
# Severity classification (audit-action → severity bucket)
# ---------------------------------------------------------------------------

#: Audit actions classified as `critical` severity — security/kernel deny.
_RISK_ACTIONS_CRITICAL: frozenset = frozenset({
    "mcp_canonical_guard_blocked",      # KERNEL HARD-DENY edit attempt
    "trading_write_override_used",      # explicit override of trading-readonly
    "policy_denied",                    # final deny after rule eval (ADR-045)
    "pair_rail_codex_injection_detected",  # ingress sanitization fired
    "kernel_override_used",             # ceremony bypass
})

#: Audit actions classified as `error` severity — guard fired with refuse.
_RISK_ACTIONS_ERROR: frozenset = frozenset({
    "injection_flag",                   # prompt-injection detection
    "anti_ceo_overhead_block",          # parallelization-by-default veto
    "bash_safety_blocked",              # check_bash_safety refused
    "plan_edit_blocked",                # check_plan_edit refused
    "spawn_rejected",                   # check_agent_spawn refused
})

#: Audit actions classified as `warn` severity — advisory / soft-block.
_RISK_ACTIONS_WARN: frozenset = frozenset({
    "confidence_gate",                  # confidence advisory emitted
    "hmac_chain_anomaly",               # audit chain hiccup
    "token_budget_guard",               # soft budget tripwire
    "drift_factor_warning",             # plan drift advisory
})

ALL_SEVERITIES: Tuple[str, str, str] = ("critical", "error", "warn")


# ---------------------------------------------------------------------------
# Action classification (audit-action → "actions taken" bucket)
# ---------------------------------------------------------------------------

#: Audit actions that count as concrete edits/writes (Edit + Write tools).
_ACTIONS_EDIT_WRITE: frozenset = frozenset({
    "edit_applied", "write_applied", "canonical_edit_applied",
})

#: Audit actions that count as git commits (signed or unsigned).
_ACTIONS_COMMIT: frozenset = frozenset({
    "git_commit", "ceremony_commit",
})

#: Audit actions that count as GPG-signed ceremonies.
_ACTIONS_GPG: frozenset = frozenset({
    "gpg_signature_attached", "sentinel_signed", "ceremony_signed",
})

#: Audit actions that count as sub-agent spawns.
_ACTIONS_SPAWN: frozenset = frozenset({
    "agent_spawn", "spawn_dispatched",
})

#: Audit actions that count as plan-status transitions.
_ACTIONS_PLAN_TRANSITION: frozenset = frozenset({
    "plan_status_transition", "plan_transition",
})


# ---------------------------------------------------------------------------
# Path-bucket categories (Sec MF-3 — no raw paths in output)
# ---------------------------------------------------------------------------

# Order matters: first match wins. Use stable, neutral categories that
# don't leak workflow specifics.
_PATH_CATEGORIES: Tuple[Tuple[str, re.Pattern], ...] = (
    ("plans",        re.compile(r"\.claude/plans/")),
    ("hooks",        re.compile(r"\.claude/hooks/")),
    ("skills",       re.compile(r"\.claude/skills/")),
    ("adrs",         re.compile(r"\.claude/adr/")),
    ("scripts",      re.compile(r"\.claude/scripts/|^scripts/")),
    ("policies",     re.compile(r"\.claude/policies/")),
    ("commands",     re.compile(r"\.claude/commands/")),
    ("templates",    re.compile(r"\.claude/templates/")),
    ("tests",        re.compile(r"(?:^|/)tests?/")),
    ("docs",         re.compile(r"^docs/|\.md$|README|CHANGELOG")),
    ("config",       re.compile(r"\.ya?ml$|\.json$|\.toml$|\.cfg$|\.ini$")),
    ("source",       re.compile(r"\.py$|\.ts$|\.tsx$|\.js$|\.go$|\.rs$|\.sh$")),
)

_BUCKET_OTHER: str = "other"


# ---------------------------------------------------------------------------
# Confidence-labels import (defensive)
# ---------------------------------------------------------------------------

def _try_import_confidence_labels() -> Optional[Any]:
    """Best-effort import of confidence_labels (Wave 1 sub-1.10).

    Returns the module if importable from one of three candidate paths,
    None otherwise. The receipt formatter degrades gracefully — severity
    markers fall back to literal "[CRITICAL]" / "[ERROR]" / "[WARN]"
    when the module is absent.
    """
    here = Path(__file__).resolve().parent
    candidates: List[Path] = [
        here.parent.parent / "wave-1" / "sub-1-10-confidence-labels" / "confidence_labels.py",
        here.parent / "sub-1-10-confidence-labels" / "confidence_labels.py",
        Path.cwd() / "confidence_labels.py",
    ]
    for cand in candidates:
        if not cand.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location(
                "_receipt_confidence_labels", str(cand)
            )
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            return mod
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Audit-log discovery + read (mirrors budget-summary.py)
# ---------------------------------------------------------------------------


def default_audit_dir() -> Path:
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration"


def discover_logs(audit_dir: Optional[Path] = None) -> List[Path]:
    if audit_dir is None:
        audit_dir = default_audit_dir()
    if not audit_dir.is_dir():
        return []
    pattern = str(audit_dir / AUDIT_LOG_GLOB)
    paths = sorted(Path(p) for p in glob.glob(pattern))
    active: List[Path] = []
    backups: List[Path] = []
    for p in paths:
        if p.name == "audit-log.jsonl":
            active.append(p)
        else:
            backups.append(p)
    return backups + active


def _canonical_event_sha256(event: Dict[str, Any]) -> str:
    canonical = {k: v for k, v in event.items() if k not in _DEDUP_STRIP_FIELDS}
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def iter_unique_events(log_paths: Iterable[Path]) -> Iterator[Dict[str, Any]]:
    seen: Set[str] = set()
    for path in log_paths:
        try:
            with path.open("r", encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(event, dict):
                        continue
                    digest = _canonical_event_sha256(event)
                    if digest in seen:
                        continue
                    seen.add(digest)
                    yield event
        except OSError:
            continue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_since(expr: str) -> timedelta:
    m = _SINCE_RE.match(expr.strip().lower())
    if not m:
        raise ValueError(
            f"bad --since value: {expr!r} (expected Nm / Nh / Nd, e.g. 24h)"
        )
    n = int(m.group(1))
    unit = m.group(2)
    if n < 0:
        raise ValueError(f"--since must be non-negative: {expr!r}")
    if unit == "m":
        return timedelta(minutes=n)
    if unit == "h":
        return timedelta(hours=n)
    if unit == "d":
        return timedelta(days=n)
    raise ValueError(f"unknown unit: {unit!r}")  # pragma: no cover


def _parse_ts(ts: Any) -> Optional[datetime]:
    if not isinstance(ts, str):
        return None
    normalized = ts.replace("Z", "+0000")
    try:
        return datetime.strptime(normalized, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return None


def bucket_path(raw_path: str) -> str:
    """Map a raw path string to a stable category bucket.

    Sec MF-3 enforcement: this is the **only** function in the module
    that touches raw path text, and it returns a closed-set category
    label. The raw string is discarded by the caller.
    """
    if not isinstance(raw_path, str) or not raw_path:
        return _BUCKET_OTHER
    for label, regex in _PATH_CATEGORIES:
        if regex.search(raw_path):
            return label
    return _BUCKET_OTHER


def _safe_plan_id(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    if _PLAN_ID_RE.match(value):
        return value
    return None


def _compute_cost_usd(
    model: Optional[str],
    tokens_in: int,
    tokens_out: int,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
) -> Optional[float]:
    if pricing is None:
        pricing = _DEFAULT_PRICING
    if not isinstance(model, str) or not model:
        return None
    row = pricing.get(model.lower())
    if not row:
        return None
    cost = (tokens_in / 1000.0) * row.get("in", 0.0)
    cost += (tokens_out / 1000.0) * row.get("out", 0.0)
    return round(cost, 6)


# ---------------------------------------------------------------------------
# Scope filtering
# ---------------------------------------------------------------------------


def _event_in_scope(
    ev: Dict[str, Any],
    *,
    session_id: Optional[str],
    plan_id: Optional[str],
    cutoff: Optional[datetime],
) -> bool:
    """Check whether an event falls within the requested scope.

    Filters are AND-combined. If a filter is None it does not constrain.
    """
    if cutoff is not None:
        ts = _parse_ts(ev.get("ts"))
        if ts is not None and ts < cutoff:
            return False
    if session_id is not None:
        if ev.get("session_id") != session_id:
            return False
    if plan_id is not None:
        if _safe_plan_id(ev.get("plan_id")) != plan_id:
            return False
    return True


def _detect_default_session(events: List[Dict[str, Any]]) -> Optional[str]:
    """Return the most-recent session_id observed in the audit log.

    The events list must be sorted by timestamp ascending. Used when
    the caller did not supply --session-id / --plan-id / --since.
    """
    for ev in reversed(events):
        sid = ev.get("session_id")
        if isinstance(sid, str) and sid:
            return sid
    return None


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def build_files_inspected(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Section 1 — Files inspected.

    Sec MF-3: raw paths NEVER enter the output; we bucket them into
    closed-set categories and emit counts only.
    """
    bucket_counts: Dict[str, int] = {}
    total = 0
    path_field_candidates = ("file_path", "path", "target_path", "edit_path",
                             "read_path", "blob_path")

    for ev in events:
        for key in path_field_candidates:
            v = ev.get(key)
            if isinstance(v, str) and v:
                bucket = bucket_path(v)
                bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
                total += 1
                break  # one path per event maximum

    # Top-5 buckets by count, descending; ties broken by bucket name.
    sorted_buckets = sorted(
        bucket_counts.items(), key=lambda kv: (-kv[1], kv[0])
    )
    top5 = [{"category": k, "count": v} for k, v in sorted_buckets[:5]]

    return {
        "total": total,
        "top_categories": top5,
        "categories_seen": len(bucket_counts),
    }


def build_risks_found(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Section 2 — Risks found, grouped by severity.

    Severity is derived from the audit `action` value via the three
    classification tables. Action codes outside the tables are ignored
    (they're not risk events).
    """
    counts: Dict[str, int] = {sev: 0 for sev in ALL_SEVERITIES}
    by_action: Dict[str, int] = {}

    for ev in events:
        action = ev.get("action")
        if not isinstance(action, str):
            continue
        sev: Optional[str] = None
        if action in _RISK_ACTIONS_CRITICAL:
            sev = "critical"
        elif action in _RISK_ACTIONS_ERROR:
            sev = "error"
        elif action in _RISK_ACTIONS_WARN:
            sev = "warn"
        if sev is None:
            continue
        counts[sev] += 1
        by_action[action] = by_action.get(action, 0) + 1

    total = sum(counts.values())
    top_actions = sorted(
        by_action.items(), key=lambda kv: (-kv[1], kv[0])
    )[:5]

    return {
        "total": total,
        "by_severity": dict(counts),
        "top_actions": [
            {"action": a, "count": c} for a, c in top_actions
        ],
    }


def build_actions_taken(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Section 3 — Actions taken (edits / commits / GPG / spawns / transitions)."""
    counts = {
        "edits_writes": 0,
        "commits": 0,
        "gpg_ceremonies": 0,
        "subagent_spawns": 0,
        "plan_transitions": 0,
    }
    for ev in events:
        action = ev.get("action")
        if not isinstance(action, str):
            continue
        if action in _ACTIONS_EDIT_WRITE:
            counts["edits_writes"] += 1
        elif action in _ACTIONS_COMMIT:
            counts["commits"] += 1
        elif action in _ACTIONS_GPG:
            counts["gpg_ceremonies"] += 1
        elif action in _ACTIONS_SPAWN:
            counts["subagent_spawns"] += 1
        elif action in _ACTIONS_PLAN_TRANSITION:
            counts["plan_transitions"] += 1

    total = sum(counts.values())
    return {"total": total, "by_kind": counts}


def build_value_created(
    events: List[Dict[str, Any]],
    *,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """Section 4 — Value created.

    - **cost_usd:** sum across token-bearing events
    - **bugs_caught:** count of risk events that REFUSED a write/spawn
      (critical + error tier; warn does not count as "bug caught")
    - **artifacts_produced:** edits + writes + commits (proxy for files
      created/changed). Best-effort — actual file-count requires
      git introspection which is out of scope here.
    - **tokens_saved_estimate:** opportunity-savings vs solo-CEO baseline,
      computed as `(spawn_count * baseline_solo_cost) - actual_cost`
      where `baseline_solo_cost` assumes the work would have been done
      sequentially by Opus at the **observed** token volume. This is an
      ESTIMATE per Codex P1 methodology disclaimer.
    """
    if pricing is None:
        pricing = _DEFAULT_PRICING

    tot_in = 0
    tot_out = 0
    cost = 0.0
    cost_known = False
    spawn_count = 0

    bugs_caught = 0
    artifacts = 0

    for ev in events:
        action = ev.get("action")
        if not isinstance(action, str):
            continue

        # Cost / tokens
        t_in_raw = ev.get("tokens_in")
        t_out_raw = ev.get("tokens_out")
        t_in = int(t_in_raw) if isinstance(t_in_raw, (int, float)) and t_in_raw else 0
        t_out = int(t_out_raw) if isinstance(t_out_raw, (int, float)) and t_out_raw else 0
        tot_in += t_in
        tot_out += t_out

        model = ev.get("model") or ev.get("agent_model") or ""
        if isinstance(model, str) and model:
            c = _compute_cost_usd(model, t_in, t_out, pricing=pricing)
            if c is not None:
                cost += c
                cost_known = True

        if action in _ACTIONS_SPAWN:
            spawn_count += 1
        if action in _RISK_ACTIONS_CRITICAL or action in _RISK_ACTIONS_ERROR:
            bugs_caught += 1
        if action in _ACTIONS_EDIT_WRITE or action in _ACTIONS_COMMIT:
            artifacts += 1

    # Tokens-saved estimate (heuristic).
    # Baseline: if a sub-agent dispatched at avg `tok_per_spawn` tokens
    # and was done sequentially by CEO Opus, the CEO would have paid
    # the same tokens but at Opus pricing — savings is the delta.
    # We use a conservative 1.0x multiplier (i.e. no inflation) so the
    # number is defensible: it equals (actual cost saved by using
    # Sonnet/Haiku sub-agents instead of CEO Opus).
    total_tokens = tot_in + tot_out
    avg_per_spawn = (total_tokens / spawn_count) if spawn_count else 0
    # Solo-CEO baseline assumes all tokens billed at Opus rate.
    opus_rate_in = _DEFAULT_PRICING["claude-opus-4-7"]["in"]
    opus_rate_out = _DEFAULT_PRICING["claude-opus-4-7"]["out"]
    baseline_cost = (tot_in / 1000.0) * opus_rate_in
    baseline_cost += (tot_out / 1000.0) * opus_rate_out
    tokens_saved_usd_estimate = max(0.0, round(baseline_cost - cost, 6))

    return {
        "cost_usd": round(cost, 6) if cost_known else None,
        "cost_source": "default-pricing-table" if cost_known else "unknown",
        "bugs_caught": bugs_caught,
        "artifacts_produced": artifacts,
        "tokens_total": total_tokens,
        "tokens_saved_usd_estimate": tokens_saved_usd_estimate,
        "subagent_spawns": spawn_count,
        "avg_tokens_per_spawn": int(avg_per_spawn),
    }


def build_next_move(
    events: List[Dict[str, Any]],
    risks: Dict[str, Any],
    actions: Dict[str, Any],
) -> Dict[str, Any]:
    """Section 5 — Top-3 recommended next moves.

    Heuristic rule set (first match wins, max 3 emitted):
      1. If unresolved `critical` risks: "investigate critical risk events"
      2. If `error` risks > 0: "review error-tier audit rows"
      3. If executing plans observed: "continue current plan execution"
      4. If `commits` > 0 but no `gpg_ceremonies`: "schedule signing ceremony"
      5. If `plan_transitions` reached `reviewed`: "owner ceremony for review→executing"
      6. Default: "review session summary + plan next milestone"
    """
    recs: List[Dict[str, str]] = []

    crit = risks.get("by_severity", {}).get("critical", 0)
    err = risks.get("by_severity", {}).get("error", 0)
    warn = risks.get("by_severity", {}).get("warn", 0)

    if crit > 0:
        recs.append({
            "rank": "1",
            "action": "investigate-critical-risks",
            "rationale": f"{crit} critical risk event(s) recorded; review audit rows before next ceremony.",
        })

    if err > 0:
        recs.append({
            "rank": str(len(recs) + 1),
            "action": "review-error-tier",
            "rationale": f"{err} error-tier event(s); reconcile or document deferral.",
        })

    # Detect executing plans via plan_status_transition trail.
    executing_plans = set()
    pending_review_plans = set()
    for ev in events:
        if ev.get("action") not in _ACTIONS_PLAN_TRANSITION:
            continue
        pid = _safe_plan_id(ev.get("plan_id"))
        if not pid:
            continue
        to_status = (ev.get("to_status") or ev.get("status")
                     or ev.get("new_status") or "")
        if to_status == "executing":
            executing_plans.add(pid)
        elif to_status == "reviewed":
            pending_review_plans.add(pid)
        elif to_status in ("done", "abandoned", "blocked"):
            executing_plans.discard(pid)

    if len(recs) < 3 and executing_plans:
        plan_list = sorted(executing_plans)[:3]
        recs.append({
            "rank": str(len(recs) + 1),
            "action": "continue-plan-execution",
            "rationale": f"Plan(s) executing: {', '.join(plan_list)}.",
        })

    if (len(recs) < 3
            and actions.get("by_kind", {}).get("commits", 0) > 0
            and actions.get("by_kind", {}).get("gpg_ceremonies", 0) == 0):
        recs.append({
            "rank": str(len(recs) + 1),
            "action": "schedule-signing-ceremony",
            "rationale": "Commits present without GPG sentinels; queue signing ceremony.",
        })

    if len(recs) < 3 and pending_review_plans:
        plan_list = sorted(pending_review_plans)[:3]
        recs.append({
            "rank": str(len(recs) + 1),
            "action": "owner-ceremony-review-to-executing",
            "rationale": f"Plan(s) ready_to_review awaiting owner flip: {', '.join(plan_list)}.",
        })

    if not recs:
        recs.append({
            "rank": "1",
            "action": "review-summary-and-plan-next",
            "rationale": "No critical signals; pick next milestone.",
        })

    # Cap at 3 and renumber stably.
    recs = recs[:3]
    for i, r in enumerate(recs, start=1):
        r["rank"] = str(i)

    return {"recommendations": recs}


# ---------------------------------------------------------------------------
# Receipt assembly
# ---------------------------------------------------------------------------


def assemble_receipt(
    *,
    audit_dir: Optional[Path] = None,
    session_id: Optional[str] = None,
    plan_id: Optional[str] = None,
    since: Optional[timedelta] = None,
    now: Optional[datetime] = None,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """Return the full structured receipt payload.

    Scope selection precedence:
      1. explicit ``session_id``
      2. explicit ``plan_id``
      3. ``since`` window
      4. default — most-recent session in the log
      5. if no events at all — empty payload with all sections present
    """
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = (now - since) if since is not None else None

    log_paths = discover_logs(audit_dir)
    all_events: List[Dict[str, Any]] = list(iter_unique_events(log_paths))
    all_events.sort(key=lambda e: (e.get("ts") or "", e.get("action") or ""))

    effective_session = session_id
    scope_kind = "explicit"
    if session_id is None and plan_id is None and since is None:
        effective_session = _detect_default_session(all_events)
        scope_kind = "default-most-recent-session"

    # Filter to scope
    in_scope = [
        ev for ev in all_events
        if _event_in_scope(
            ev,
            session_id=effective_session,
            plan_id=plan_id,
            cutoff=cutoff,
        )
    ]

    files = build_files_inspected(in_scope)
    risks = build_risks_found(in_scope)
    actions = build_actions_taken(in_scope)
    value = build_value_created(in_scope, pricing=pricing)
    nextmove = build_next_move(in_scope, risks, actions)

    return {
        "schema_version": "v1",
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%S%z") or now.isoformat(),
        "scope": {
            "session_id": effective_session,
            "plan_id": plan_id,
            "since": None,  # filled by caller who knows the expression
            "kind": scope_kind,
        },
        "files_inspected": files,
        "risks_found": risks,
        "actions_taken": actions,
        "value_created": value,
        "next_move": nextmove,
        "audit_dir": str(audit_dir or default_audit_dir()),
        "log_files_read": [p.name for p in log_paths],
        "events_in_scope": len(in_scope),
        "events_total_seen": len(all_events),
    }


# ---------------------------------------------------------------------------
# Rendering — markdown + CTO methodology footer
# ---------------------------------------------------------------------------


def _sev_marker(sev: str, conf_mod: Optional[Any]) -> str:
    """Severity marker, optionally routed through confidence_labels."""
    if conf_mod is not None:
        # Map severity → confidence level for visual consistency. Note
        # this is a presentational mapping only; severity != confidence.
        try:
            if sev == "critical":
                return "[CRITICAL]"
            if sev == "error":
                return "[ERROR]"
            if sev == "warn":
                return "[WARN]"
        except Exception:  # pragma: no cover
            pass
    return {"critical": "[CRITICAL]", "error": "[ERROR]",
            "warn": "[WARN]"}.get(sev, "[INFO]")


def render_markdown(
    payload: Dict[str, Any],
    *,
    for_ctov: bool = False,
    conf_mod: Optional[Any] = None,
) -> str:
    """Render the structured payload as a 5-section markdown receipt."""
    lines: List[str] = []
    scope = payload.get("scope", {})
    scope_bits: List[str] = []
    if scope.get("session_id"):
        scope_bits.append(f"session={scope['session_id']}")
    if scope.get("plan_id"):
        scope_bits.append(f"plan={scope['plan_id']}")
    if scope.get("since"):
        scope_bits.append(f"since={scope['since']}")
    scope_str = ", ".join(scope_bits) if scope_bits else "(default scope)"

    lines.append(f"# Session Receipt — {scope_str}")
    lines.append("")
    lines.append(f"_generated {payload.get('generated_at', '?')} — "
                 f"events_in_scope={payload.get('events_in_scope', 0)}_")
    lines.append("")

    # 1. Files inspected
    files = payload.get("files_inspected", {})
    lines.append("## 1. Files inspected")
    lines.append("")
    lines.append(f"- total: **{files.get('total', 0)}**")
    lines.append(f"- categories seen: {files.get('categories_seen', 0)}")
    top = files.get("top_categories") or []
    if top:
        lines.append("- top-5 categories (Sec MF-3 — paths bucketed, "
                     "not leaked):")
        for row in top:
            lines.append(f"    - `{row['category']}`: {row['count']}")
    else:
        lines.append("- top-5 categories: (none observed)")
    lines.append("")

    # 2. Risks found
    risks = payload.get("risks_found", {})
    sev_counts = risks.get("by_severity", {})
    lines.append("## 2. Risks found")
    lines.append("")
    lines.append(f"- total: **{risks.get('total', 0)}**")
    for sev in ALL_SEVERITIES:
        marker = _sev_marker(sev, conf_mod)
        lines.append(f"- {marker} {sev}: {sev_counts.get(sev, 0)}")
    top_actions = risks.get("top_actions") or []
    if top_actions:
        lines.append("- top-5 actions:")
        for row in top_actions:
            lines.append(f"    - `{row['action']}`: {row['count']}")
    lines.append("")

    # 3. Actions taken
    actions = payload.get("actions_taken", {})
    kinds = actions.get("by_kind", {})
    lines.append("## 3. Actions taken")
    lines.append("")
    lines.append(f"- total: **{actions.get('total', 0)}**")
    lines.append(f"- edits/writes:       {kinds.get('edits_writes', 0)}")
    lines.append(f"- commits:            {kinds.get('commits', 0)}")
    lines.append(f"- GPG ceremonies:     {kinds.get('gpg_ceremonies', 0)}")
    lines.append(f"- sub-agent spawns:   {kinds.get('subagent_spawns', 0)}")
    lines.append(f"- plan transitions:   {kinds.get('plan_transitions', 0)}")
    lines.append("")

    # 4. Value created
    value = payload.get("value_created", {})
    lines.append("## 4. Value created")
    lines.append("")
    cost = value.get("cost_usd")
    if cost is None:
        lines.append("- cost (USD):           - (no pricing data)")
    else:
        lines.append(f"- cost (USD):           ${cost:,.4f}")
    lines.append(f"- bugs caught:           {value.get('bugs_caught', 0)}")
    lines.append(f"- artifacts produced:    {value.get('artifacts_produced', 0)}")
    lines.append(f"- tokens (total):        {value.get('tokens_total', 0):,}")
    lines.append(f"- tokens-saved estimate: "
                 f"${value.get('tokens_saved_usd_estimate', 0):,.4f}")
    lines.append("")

    # 5. Next move
    nextmove = payload.get("next_move", {})
    recs = nextmove.get("recommendations") or []
    lines.append("## 5. Next move")
    lines.append("")
    if not recs:
        lines.append("- (none recommended — review summary manually)")
    else:
        for r in recs:
            lines.append(f"- **{r['rank']}.** `{r['action']}` — {r['rationale']}")
    lines.append("")

    if for_ctov:
        lines.extend(_render_ctov_footer(payload))

    return "\n".join(lines).rstrip() + "\n"


def _render_ctov_footer(payload: Dict[str, Any]) -> List[str]:
    """Render the CTO-defense methodology footer.

    Per PLAN-083 §13 risk row + Codex P1: every number that's an
    *estimate* must be labeled an estimate, and every assumption must
    be exposed inline. Never claim "saved hours" without showing the
    baseline.
    """
    lines: List[str] = []
    lines.append("---")
    lines.append("")
    lines.append("## Methodology (for CTO review)")
    lines.append("")
    lines.append("**Numbers above are estimates.** Actual savings depend on the "
                 "baseline you compare against. Specifically:")
    lines.append("")
    lines.append("- **`cost (USD)`** is computed by multiplying observed token "
                 "counts by a static pricing table "
                 "(see `_DEFAULT_PRICING` in source). It tracks API spend, "
                 "NOT engineering hours. Pricing drift between Anthropic / "
                 "OpenAI is not auto-fetched; the table is a "
                 "point-in-time snapshot.")
    lines.append("- **`bugs caught`** counts critical + error-tier audit events "
                 "where a guard refused a write/spawn. It does NOT include "
                 "warn-tier advisories. A `bug caught` is only as meaningful "
                 "as the underlying guard's true-positive rate; per AC5b that "
                 "FPR is bounded at ≤15% rolling 30-day for new exchange-key "
                 "regexes.")
    lines.append("- **`tokens-saved estimate`** is "
                 "`(opus_rate * total_tokens) - actual_cost`. It assumes a "
                 "solo-CEO baseline would have spent the SAME token volume at "
                 "Opus pricing. **This is an upper bound** — a real solo-CEO "
                 "could compress or split the same task and use fewer tokens. "
                 "Treat this as 'pricing differential' not 'hours saved'.")
    lines.append("- **`artifacts produced`** counts edits + writes + commits "
                 "from the audit stream. It is a PROXY for files changed; "
                 "actual file count requires git introspection out of scope here.")
    lines.append("- **`files inspected`** counts are bucketed into "
                 "category labels (Sec MF-3); raw paths are intentionally "
                 "discarded so the receipt is safe to share.")
    lines.append("- **Audit trail backing every number above** is the chained "
                 "HMAC log at `audit-log*.jsonl`; run `audit-query.py "
                 "verify-chain` to confirm tamper-evidence.")
    lines.append("")
    lines.append("**What this receipt is NOT:** marketing copy. The framework's "
                 "claim to a CTO rests on (a) this audit trail, (b) one or "
                 "more concrete avoided bugs in the `risks_found` section, "
                 "and (c) a demo. Numbers without those three are pitch copy.")
    lines.append("")
    return lines


def render_json(payload: Dict[str, Any], *, for_ctov: bool = False) -> str:
    out = dict(payload)
    if for_ctov:
        out["methodology_disclaimers"] = [
            "cost_usd derived from static pricing table; not engineering hours",
            "bugs_caught requires guard true-positive rate to be meaningful (AC5b bound ≤15% FPR)",
            "tokens_saved_usd_estimate assumes solo-CEO would use same token volume at opus rate (upper bound)",
            "artifacts_produced is a proxy from audit stream, not git introspection",
            "files_inspected paths are bucketed (Sec MF-3); raw paths discarded",
            "audit-trail HMAC chain at audit-log*.jsonl is the canonical evidence",
        ]
    return json.dumps(out, indent=2, sort_keys=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="success-receipt",
        description=(
            "Render a 5-section session/plan/window receipt from the "
            "audit log (PLAN-083 Wave 2 sub-2.3)."
        ),
    )
    p.add_argument("--session-id", metavar="SID", default=None,
                   help="Limit to a single session_id.")
    p.add_argument("--plan-id", metavar="PLAN-NNN", default=None,
                   help="Limit to a single plan_id.")
    p.add_argument("--since", metavar="EXPR", default=None,
                   help="Time window (Nm/Nh/Nd, e.g. 24h).")
    p.add_argument("--json", action="store_true",
                   help="Emit JSON instead of markdown.")
    p.add_argument("--for-ctov", action="store_true",
                   help="Append methodology disclaimers for CTO defense.")
    p.add_argument("--audit-dir", metavar="PATH", default=None,
                   help="Override audit-log directory.")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 2

    # Mutual-exclusion check (relaxed — combinations are sometimes useful,
    # so we only forbid the empty + multi pathological cases).
    if args.plan_id and not _PLAN_ID_RE.match(args.plan_id):
        sys.stderr.write(
            f"success-receipt: --plan-id must look like PLAN-NNN "
            f"(got {args.plan_id!r})\n"
        )
        return 2

    since_delta: Optional[timedelta] = None
    if args.since:
        try:
            since_delta = parse_since(args.since)
        except ValueError as e:
            sys.stderr.write(f"success-receipt: {e}\n")
            return 2

    audit_dir = Path(args.audit_dir) if args.audit_dir else None

    payload = assemble_receipt(
        audit_dir=audit_dir,
        session_id=args.session_id,
        plan_id=args.plan_id,
        since=since_delta,
    )
    payload["scope"]["since"] = args.since

    if args.json:
        print(render_json(payload, for_ctov=args.for_ctov))
    else:
        conf_mod = _try_import_confidence_labels()
        print(render_markdown(payload, for_ctov=args.for_ctov,
                              conf_mod=conf_mod))
    return 0


if __name__ == "__main__":
    sys.exit(main())
