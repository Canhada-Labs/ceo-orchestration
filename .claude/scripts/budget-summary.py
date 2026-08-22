#!/usr/bin/env python3
"""budget-summary.py — multi-rotation FinOps rollup (PLAN-083 Wave 0b sub-0.8).

This is the **PLAN-083 reissue** of ``.claude/scripts/budget-summary.py``.
It supersedes the prior ADR-033 implementation in three dimensions per
PLAN-083 §5.2 row 0.8:

1. **Multi-rotation read** — globs ``audit-log*.jsonl`` in the audit dir
   so cumulative spend reflects all 12 backup rotations + the active
   log. The prior script read only ``audit-log.jsonl`` and therefore
   reported ``$0.28`` against a memory claim of ``~$1003-1543`` for the
   S82-S99 window.

2. **Dedup by event sha256** — per PLAN-083 §13 risk register row
   "FinOps backup glob double-counts events across rotations". On a
   rotation boundary the tail of the previous log may be partially
   mirrored in the next rotation's head (atomic rename + retry
   semantics). We canonicalize each event (drop ``hmac``, ``hmac_error``,
   ``hook_duration_ms``) and compute sha256 over the sorted-keys JSON
   form; first occurrence wins.

3. **Codex MCP tokens included** — ``pair_rail_case`` action events
   contribute ``tokens_in`` / ``tokens_out`` to the rollup. Combined
   with the companion ``codex-adapter-token-wire.patch`` that
   actually populates those fields, this closes the
   "tokens not tracked for Codex" half of the observability gap.

4. **plan_id auto-attribution** — events that carry an explicit
   ``plan_id`` field win. Otherwise we infer ``plan_id`` from the
   nearest preceding ``plan_status_transition`` event in the same
   ``session_id`` whose status is ``executing`` (per ADR-058). Only
   when both signals are absent do we fall back to ``(unknown)``.

5. **Native-source cross-check (PLAN-178 W1.2, default-OFF)** — the
   ``--native`` flag (or ``CEO_BUDGET_NATIVE=1``) appends a cross-check
   of the audit-log spawn ledger against the harness-native transcript
   corpus under ``~/.claude/projects/<cwd-slug>/<SESSION-UUID>/subagents/``
   (probe: ``.claude/plans/PLAN-178/w12-native-cost-probe.md``).
   Doctrine: **cross-check, not authority-swap** — the native source
   NEVER silently replaces the audit-log rollup; UNMATCHED residue on
   BOTH sides is always reported (silencing it would fake a low
   divergence). Model aliases (``opus`` / ``sonnet`` / ``fable`` /
   ``claude-fable-5[1m]`` …) are resolved through the repo's EXISTING
   normalizer (``optimizer/model_normalize.py``) + the pricing registry
   below — an unresolvable/unpriced model is reported as cost ``TBD``,
   never as ``$0``. When the native source is dormant (no transcripts on
   disk) and the flag is OFF, output is byte-for-byte unchanged.

## Usage

::

    python3 budget-summary.py summary
    python3 budget-summary.py summary --since 30d
    python3 budget-summary.py summary --plan-id PLAN-081
    python3 budget-summary.py summary --by-wave
    python3 budget-summary.py summary --json
    python3 budget-summary.py summary --validate-memory-claim
    python3 budget-summary.py summary --native

Stdlib only. Python 3.9+.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple
import sys as _sys_rp
from pathlib import Path as _Path_rp
_HOOKS_RP = _Path_rp(__file__).resolve()
for _anc in _HOOKS_RP.parents:
    if (_anc / ".claude" / "hooks" / "_lib").is_dir():
        if str(_anc / ".claude" / "hooks") not in _sys_rp.path:
            _sys_rp.path.insert(0, str(_anc / ".claude" / "hooks"))
        break
from _lib import runtime_paths as _rp  # noqa: E402  # PLAN-182 W1 single resolver


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: ``--since`` time-expression parser.
_SINCE_RE = re.compile(r"^(\d+)\s*([mhd])$")

#: PLAN-id syntactic check (Sec MF-3 — bound any plan_id we display).
_PLAN_ID_RE = re.compile(r"^PLAN-[0-9]{3}$")

#: Wave-id parser (e.g. ``"wave-0a"``, ``"wave-1"``, ``"wave-minus-1"``).
_WAVE_ID_RE = re.compile(r"^wave-[a-z0-9-]{1,16}$")

#: Memory-claim band per CLAUDE.md §6 (S82-S99 cumulative).
MEMORY_CLAIM_LOW_USD: float = 1003.0
MEMORY_CLAIM_HIGH_USD: float = 1543.0
MEMORY_CLAIM_PASS_RATIO_LOW: float = 0.5
MEMORY_CLAIM_PASS_RATIO_HIGH: float = 1.5

#: Audit-log filename glob.
AUDIT_LOG_GLOB: str = "audit-log*.jsonl"

#: Fields stripped before computing event sha256 (rotation overlap dedup).
#: ``hmac`` and ``hmac_error`` differ between rotations because they're
#: chained off prior_hmac; ``hook_duration_ms`` is observation-time noise.
_DEDUP_STRIP_FIELDS: Tuple[str, ...] = ("hmac", "hmac_error", "hook_duration_ms")

#: Default per-1k-token pricing (USD). Falls back to these if the
#: pricing doc is unavailable. Numbers are conservative midpoints from
#: Anthropic + OpenAI public pricing as of 2026-05; intent here is
#: *order-of-magnitude correctness*, not pricing engine.
#: PLAN-120 WS-C: refreshed to current Anthropic slugs + rates (per-1k tokens,
#: USD). claude-opus-4-8 = current flagship $5/$25 per MTok (0.005/0.025 per-1k);
#: claude-opus-4-7 RETAINED HISTORICAL ($15/$75) for log replay of pre-4.8
#: sessions; Sonnet 4.6 = $3/$15; Haiku 4.5 = $1/$5 (was 4x underpriced).
#: PLAN-163 T1.5b — ADDITIVE Claude 5 fleet rows (historical rows retained,
#: ADR-142): fable-5 $10/$50; opus-5 $5/$25 (drop-in at the 4.8 rate);
#: opus-5-fast $10/$50 premium row; sonnet-5 $2/$10 INTRO rate through
#: 2026-08-31 (post-intro sticker $3/$15 — bump when the window lapses).
_DEFAULT_PRICING: Dict[str, Dict[str, float]] = {
    "claude-opus-4-8":             {"in": 0.005, "out": 0.025},
    "claude-opus-4-8-fast":       {"in": 0.010, "out": 0.050},
    "claude-fable-5":             {"in": 0.010, "out": 0.050},
    "claude-opus-5":              {"in": 0.005, "out": 0.025},
    "claude-opus-5-fast":         {"in": 0.010, "out": 0.050},
    "claude-sonnet-5":            {"in": 0.002, "out": 0.010},
    "claude-opus-4-7":            {"in": 0.015, "out": 0.075},
    "claude-opus-4":              {"in": 0.015, "out": 0.075},
    "claude-sonnet-4-6":          {"in": 0.003, "out": 0.015},
    "claude-sonnet-4-5":          {"in": 0.003, "out": 0.015},
    "claude-sonnet-4":            {"in": 0.003, "out": 0.015},
    "claude-haiku-4-5-20251001":  {"in": 0.001, "out": 0.005},
    "claude-haiku-4-5":           {"in": 0.001, "out": 0.005},
    "claude-haiku-4":             {"in": 0.001, "out": 0.005},
    "gpt-5":             {"in": 0.005,  "out": 0.020},
    "gpt-5-codex":       {"in": 0.005,  "out": 0.020},
    "gpt-5-mini":        {"in": 0.0005, "out": 0.002},
    "o3":                {"in": 0.015,  "out": 0.060},
    "o4-mini":           {"in": 0.001,  "out": 0.004},
}


# ---------------------------------------------------------------------------
# --since parser
# ---------------------------------------------------------------------------


def parse_since(expr: str) -> timedelta:
    """Parse ``Nm`` / ``Nh`` / ``Nd`` into a timedelta. Raises ValueError."""
    m = _SINCE_RE.match(expr.strip().lower())
    if not m:
        raise ValueError(
            f"bad --since value: {expr!r} (expected Nm / Nh / Nd, e.g. 30d)"
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
    """Parse ISO8601 audit-log timestamp; returns None on miss."""
    if not isinstance(ts, str):
        return None
    normalized = ts.replace("Z", "+0000")
    try:
        return datetime.strptime(normalized, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return None


#: Fractional-seconds tolerant variant (PLAN-178 W1.2). Native transcript
#: lines stamp ``2026-08-11T14:48:12.648Z``; the audit-log stamps whole
#: seconds. Ordering uses the raw ISO string (lexicographic == chronological
#: for same-zone ISO-8601); PARSING for the ``--since`` cutoff strips the
#: fraction first, then reuses ``_parse_ts``.
_TS_FRACTION_RE = re.compile(r"\.\d+(?=Z|[+-]\d{2}:?\d{2}$)")


def _parse_ts_any(ts: Any) -> Optional[datetime]:
    """``_parse_ts`` that also accepts fractional-second ISO stamps."""
    if not isinstance(ts, str):
        return None
    return _parse_ts(_TS_FRACTION_RE.sub("", ts))


# ---------------------------------------------------------------------------
# Audit-log discovery
# ---------------------------------------------------------------------------


def default_audit_dir() -> Path:
    """Return the canonical audit-log directory.

    Honors ``CEO_AUDIT_LOG_DIR`` env override (used by tests). Otherwise
    defaults to ``~/.claude/projects/<native-slug>/``.
    """
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    home = os.environ.get("HOME") or str(Path.home())
    return _rp.runtime_state_dir()


def discover_logs(audit_dir: Optional[Path] = None) -> List[Path]:
    """Return all ``audit-log*.jsonl`` files in the audit dir, sorted.

    Ordering: ``audit-log.jsonl`` (the active log) is read LAST so that
    when an event is duplicated across rotation boundary the *backup*
    version wins (it's the immutable, GPG-friendly historical record).
    Backups are sorted lexicographically (which equals chronological
    for the ``audit-log-YYYY-MM-N.jsonl`` rotation convention).
    """
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


# ---------------------------------------------------------------------------
# Event canonicalization + dedup
# ---------------------------------------------------------------------------


def canonical_event_sha256(event: Dict[str, Any]) -> str:
    """Compute sha256 over the canonical form of an event.

    Strips ``_DEDUP_STRIP_FIELDS`` (hmac/hmac_error/hook_duration_ms)
    so that the *same logical event* mirrored across a rotation
    boundary canonicalizes identically.

    Returns a 64-char hex digest.
    """
    canonical = {k: v for k, v in event.items() if k not in _DEDUP_STRIP_FIELDS}
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def iter_unique_events(
    log_paths: Iterable[Path],
    seen: Optional[Set[str]] = None,
) -> Iterator[Dict[str, Any]]:
    """Yield deduplicated events across multiple log files.

    Tolerates malformed JSON lines (silently skipped — matches
    ``audit_emit.iter_events`` behavior for forward compatibility).
    """
    if seen is None:
        seen = set()
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
                    digest = canonical_event_sha256(event)
                    if digest in seen:
                        continue
                    seen.add(digest)
                    yield event
        except OSError:
            continue


# ---------------------------------------------------------------------------
# plan_id inference
# ---------------------------------------------------------------------------


def _safe_plan_id(value: Any) -> Optional[str]:
    """Return value if it matches PLAN-NNN, else None (Sec MF-3 boundary)."""
    if not isinstance(value, str):
        return None
    if _PLAN_ID_RE.match(value):
        return value
    return None


def build_plan_attribution(
    events: List[Dict[str, Any]],
) -> Dict[int, Optional[str]]:
    """Build event-index → plan_id attribution map.

    Algorithm (best-effort, in order):
      1. If event has an explicit ``plan_id`` field matching PLAN-NNN,
         that wins.
      2. Else: find the most recent preceding ``plan_status_transition``
         event in the same ``session_id`` whose ``to_status`` (or
         ``status``) is ``executing``; attribute to that plan.
      3. Else: None (display as ``(unknown)``).

    The events list must be sorted by timestamp ascending. The map is
    keyed by *index in the supplied list* so callers can re-zip without
    holding a second copy.
    """
    attribution: Dict[int, Optional[str]] = {}
    # session_id → currently-executing plan_id
    session_executing: Dict[str, str] = {}

    for idx, ev in enumerate(events):
        action = ev.get("action") or ""
        session_id = ev.get("session_id") or ""

        # Update executing context from plan_status_transition events.
        if action == "plan_status_transition":
            to_status = (
                ev.get("to_status")
                or ev.get("status")
                or ev.get("new_status")
                or ""
            )
            pid = _safe_plan_id(ev.get("plan_id"))
            if pid and to_status == "executing":
                session_executing[session_id] = pid
            elif pid and to_status in ("done", "abandoned", "blocked"):
                # Plan no longer executing — clear if it matches.
                if session_executing.get(session_id) == pid:
                    session_executing.pop(session_id, None)

        # Explicit field wins.
        explicit = _safe_plan_id(ev.get("plan_id"))
        if explicit:
            attribution[idx] = explicit
            continue

        # Inferred from session executing context.
        inferred = session_executing.get(session_id)
        if inferred:
            attribution[idx] = inferred
        else:
            attribution[idx] = None

    return attribution


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


#: PLAN-163 W2 P2a — event-date-aware rows (per-1k twin of the tables in
#: audit-telemetry.py / ceo-cost.py): an event is priced by its OWN ``ts``,
#: never by "today" and never by mutating the global row. Sonnet 5: $2/$10
#: per MTok intro through 2026-08-31 (inclusive), $3/$15 sticker after.
_DATED_PRICING: Dict[str, Tuple[str, Dict[str, float], Dict[str, float]]] = {
    "claude-sonnet-5": (
        "2026-08-31",
        {"in": 0.002, "out": 0.010},
        {"in": 0.003, "out": 0.015},
    ),
}


def compute_cost_usd(
    model: Optional[str],
    tokens_in: int,
    tokens_out: int,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
    ts: Optional[str] = None,
) -> Optional[float]:
    """Compute USD cost from model + token counts; None on unknown model.

    P2a: when ``ts`` (the event's own ISO-8601 timestamp) is given and the
    model has a dated row, the rate is resolved against that date
    (``ts[:10]`` lexicographic compare — no parse). A caller-supplied
    custom row for the model always wins over the built-in dated row; a
    missing ``ts`` falls back to the static row (pre-P2a behaviour).
    """
    if pricing is None:
        pricing = _DEFAULT_PRICING
    if not isinstance(model, str) or not model:
        return None
    key = model.lower()
    row = pricing.get(key)
    dated = _DATED_PRICING.get(key)
    if (
        dated is not None
        and isinstance(ts, str)
        and len(ts) >= 10
        and row == _DEFAULT_PRICING.get(key)
    ):
        cutoff, through, after = dated
        row = through if ts[:10] <= cutoff else after
    if not row:
        return None
    cost = (tokens_in / 1000.0) * row.get("in", 0.0)
    cost += (tokens_out / 1000.0) * row.get("out", 0.0)
    return round(cost, 6)


# ---------------------------------------------------------------------------
# PLAN-178 W1.2-3 — model-id normalization (alias → canonical pricing key)
#
# The native corpus carries a MIXED model vocabulary (probe §1.3: bare
# aliases ``opus``/``sonnet``/``fable``/``haiku``, full ids, a ``[1m]``
# packaging suffix, and 262/416 metas with NO model at all). Resolution
# REUSES the repo's existing registry surfaces — ``optimizer/
# model_normalize.py`` (``normalize_model_name`` + its ``_RAW_ALIASES``
# closed alias map) and the ``_DEFAULT_PRICING`` table above — and
# deliberately does NOT introduce a second local alias table. A bare
# family alias is resolved ONLY when the existing registry contains
# exactly one canonical id for that family (today: ``fable`` →
# ``claude-fable-5``); an ambiguous family (``opus`` spans 4-7/4-8/5/…)
# stays UNRESOLVED — we never guess a version (the load-bearing
# invariant of ``model_normalize.py``: never collapse two versions).
# Unresolved / unpriced models are reported as cost ``TBD``, never $0.
# ---------------------------------------------------------------------------


#: The ``[1m]`` context-window packaging suffix the harness appends to a
#: live model id (probe §1.3: ``claude-fable-5[1m]``). A packaging tag,
#: not a version — stripped generically before alias lookup.
_ONE_M_SUFFIX_RE = re.compile(r"\[1m\]$")

#: A bare family alias (``opus`` / ``sonnet`` / ``fable`` / ``haiku`` …):
#: a single lowercase token with no version component.
_BARE_FAMILY_RE = re.compile(r"^[a-z][a-z0-9]*$")

#: Family extractor over canonical Claude pricing keys
#: (``claude-<family>-…`` → ``<family>``).
_CLAUDE_FAMILY_RE = re.compile(r"^claude-([a-z]+)-")


def _load_normalize_model_name():
    """Load ``normalize_model_name`` from the repo's EXISTING registry
    module ``optimizer/model_normalize.py`` (PLAN-133 B2) — REUSE, never
    a second table. Tries the deterministic sibling file first (works
    when this script is loaded by path, as the test suite does), then a
    plain package import. Fail-open on infra: returns None when neither
    route works; ``_normalize_model_id`` then degrades to case/
    whitespace/``[1m]`` handling + registry-derived family folding.
    """
    candidate = Path(__file__).resolve().parent / "optimizer" / "model_normalize.py"
    try:
        if candidate.is_file():
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "_budget_summary_model_normalize", str(candidate)
            )
            if spec is not None and spec.loader is not None:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                fn = getattr(mod, "normalize_model_name", None)
                if callable(fn):
                    return fn
    except Exception:
        pass
    try:
        from optimizer.model_normalize import normalize_model_name as fn2  # type: ignore

        if callable(fn2):
            return fn2
    except Exception:
        pass
    return None


#: Resolved once at import; None ⇒ degraded (but never crashing) mode.
_NORMALIZE_MODEL_NAME = _load_normalize_model_name()


def _family_candidates(
    family: str,
    pricing: Dict[str, Dict[str, float]],
) -> Set[str]:
    """Canonical ids in the EXISTING pricing registry whose family segment
    equals ``family`` (date-stamped variants folded through the reused
    normalizer so ``claude-haiku-4-5-20251001`` and ``claude-haiku-4-5``
    count as ONE candidate, not two)."""
    out: Set[str] = set()
    for key in pricing:
        m = _CLAUDE_FAMILY_RE.match(key)
        if not m or m.group(1) != family:
            continue
        canon = key
        if _NORMALIZE_MODEL_NAME is not None:
            try:
                folded = _NORMALIZE_MODEL_NAME(key)
                if folded:
                    canon = folded
            except Exception:
                pass
        out.add(canon)
    return out


def _normalize_model_id(
    model: Any,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
) -> Optional[str]:
    """Resolve a raw model string to a canonical model id (W1.2-3).

    Pipeline (all lookups against EXISTING registry surfaces):
      1. coerce/strip/lower; empty → None.
      2. strip a trailing ``[1m]`` packaging suffix (generic — the
         ``model_normalize`` alias map only carries the 4-8 row).
      3. fold aliases via the reused ``normalize_model_name``
         (``optimizer/model_normalize.py``): date stamps, bare
         family+version (``opus-5`` → ``claude-opus-5``),
         ``anthropic/`` prefix, case/whitespace.
      4. exact hit in the pricing registry → resolved.
      5. bare family alias (``fable``): resolved ONLY when the registry
         holds exactly one canonical id for that family; ambiguous
         families (``opus``/``sonnet``/``haiku``) → None — never guess
         a version.
      6. a specific-but-unpriced id passes through unchanged so reports
         can NAME the model that lacks a pricing row (cost stays TBD).

    Returns the canonical id, or None when the input is empty or an
    ambiguous alias. A None result (or a resolved id with no pricing
    row) MUST surface as ``TBD`` in cost columns — never as $0.
    """
    if pricing is None:
        pricing = _DEFAULT_PRICING
    if not isinstance(model, str):
        return None
    m = model.strip().lower()
    if not m:
        return None
    m = _ONE_M_SUFFIX_RE.sub("", m)
    if not m:
        return None
    if _NORMALIZE_MODEL_NAME is not None:
        try:
            folded = _NORMALIZE_MODEL_NAME(m)
            if folded:
                m = folded
        except Exception:
            pass
    if m in pricing:
        return m
    if _BARE_FAMILY_RE.match(m):
        candidates = _family_candidates(m, pricing)
        if len(candidates) == 1:
            return next(iter(candidates))
        return None
    return m


# ---------------------------------------------------------------------------
# Rollup
# ---------------------------------------------------------------------------


#: Audit actions that contribute tokens to the rollup.
_TOKEN_BEARING_ACTIONS: Tuple[str, ...] = (
    "agent_spawn",        # Claude sub-agent dispatches
    "pair_rail_case",     # Codex MCP cross-LLM gate (post-wire)
    "pair_rail_promotion",  # Phase 4 promotion gate runs
)


def rollup(
    *,
    audit_dir: Optional[Path] = None,
    plan_filter: Optional[str] = None,
    since: Optional[timedelta] = None,
    by_wave: bool = False,
    now: Optional[datetime] = None,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """Compute the cumulative rollup.

    Returns a JSON-serializable dict. See module docstring for output
    shape.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = (now - since) if since is not None else None

    log_paths = discover_logs(audit_dir)
    # Materialize so we can do two passes (attribution + rollup).
    all_events: List[Dict[str, Any]] = list(iter_unique_events(log_paths))
    # Sort ascending by ts (stable on equal ts).
    all_events.sort(key=lambda e: (e.get("ts") or "", e.get("action") or ""))

    attribution = build_plan_attribution(all_events)

    tot_in = 0
    tot_out = 0
    tot_total = 0
    tot_cost = 0.0
    cost_known = False
    spawn_count = 0
    codex_event_count = 0
    unknown_plan_count = 0

    per_plan: Dict[str, Dict[str, Any]] = {}
    per_session: Dict[str, Dict[str, Any]] = {}
    per_wave: Dict[str, Dict[str, Any]] = {}

    for idx, ev in enumerate(all_events):
        action = ev.get("action") or ""
        if action not in _TOKEN_BEARING_ACTIONS:
            continue

        ts = _parse_ts(ev.get("ts"))
        if cutoff is not None and ts is not None and ts < cutoff:
            continue

        # plan_id attribution
        attributed = attribution.get(idx)
        if plan_filter:
            if attributed != plan_filter:
                continue
        plan_label = attributed or "(unknown)"
        if attributed is None:
            unknown_plan_count += 1

        # Tokens — None coerced to 0
        t_in_raw = ev.get("tokens_in")
        t_out_raw = ev.get("tokens_out")
        t_total_raw = ev.get("tokens_total")
        t_in = int(t_in_raw) if isinstance(t_in_raw, (int, float)) and t_in_raw else 0
        t_out = int(t_out_raw) if isinstance(t_out_raw, (int, float)) and t_out_raw else 0
        t_total = int(t_total_raw) if isinstance(t_total_raw, (int, float)) and t_total_raw else 0

        spawn_count += 1
        if action == "pair_rail_case":
            codex_event_count += 1

        tot_in += t_in
        tot_out += t_out
        tot_total += t_total or (t_in + t_out)

        model = ev.get("model") or ev.get("agent_model") or ""
        if isinstance(model, str) and not model and action == "pair_rail_case":
            # Codex events default to gpt-5-codex when model not annotated.
            model = "gpt-5-codex"
        cost = compute_cost_usd(model if isinstance(model, str) else None,
                                t_in, t_out, pricing=pricing,
                                ts=ev.get("ts"))
        if cost is not None:
            cost_known = True
            tot_cost += cost

        # Per-plan
        prow = per_plan.setdefault(plan_label, {
            "plan_id": plan_label,
            "event_count": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "tokens_total": 0,
            "cost_usd": 0.0,
            "cost_known": False,
        })
        prow["event_count"] += 1
        prow["tokens_in"] += t_in
        prow["tokens_out"] += t_out
        prow["tokens_total"] += t_total or (t_in + t_out)
        if cost is not None:
            prow["cost_usd"] = round(prow["cost_usd"] + cost, 6)
            prow["cost_known"] = True

        # Per-session
        sid = ev.get("session_id") or "(unknown)"
        srow = per_session.setdefault(sid, {
            "session_id": sid,
            "event_count": 0,
            "tokens_total": 0,
            "cost_usd": 0.0,
        })
        srow["event_count"] += 1
        srow["tokens_total"] += t_total or (t_in + t_out)
        if cost is not None:
            srow["cost_usd"] = round(srow["cost_usd"] + cost, 6)

        # Per-wave (optional aggregation)
        if by_wave:
            wave = _extract_wave_id(ev)
            if wave:
                wrow = per_wave.setdefault(wave, {
                    "wave": wave,
                    "event_count": 0,
                    "tokens_total": 0,
                    "cost_usd": 0.0,
                })
                wrow["event_count"] += 1
                wrow["tokens_total"] += t_total or (t_in + t_out)
                if cost is not None:
                    wrow["cost_usd"] = round(wrow["cost_usd"] + cost, 6)

    result: Dict[str, Any] = {
        "audit_dir": str(audit_dir or default_audit_dir()),
        "log_files_read": [p.name for p in log_paths],
        "plan_filter": plan_filter,
        "since": None,  # filled by caller who knows the expr
        "total_events": spawn_count,
        "codex_event_count": codex_event_count,
        "unknown_plan_count": unknown_plan_count,
        "total_tokens_in": tot_in,
        "total_tokens_out": tot_out,
        "total_tokens": tot_total,
        "total_cost_usd": round(tot_cost, 6) if cost_known else None,
        "cost_source": "default-pricing-table" if cost_known else "unknown",
        "per_plan": sorted(per_plan.values(), key=lambda r: r["plan_id"]),
        "per_session": sorted(per_session.values(), key=lambda r: r["session_id"]),
    }
    if by_wave:
        result["per_wave"] = sorted(per_wave.values(), key=lambda r: r["wave"])

    return result


# ---------------------------------------------------------------------------
# PLAN-133 C4 — benchmark co-report (harbor-style row)
#
# Default-OFF behavioral surface, gated by the ``--benchmarks`` flag (and the
# ``CEO_BUDGET_BENCHMARKS=1`` env opt-in). When OFF, the rollup output is
# byte-for-byte unchanged. When ON, a ``benchmarks`` block is appended that
# co-reports **cost + compute + turns alongside pass-rate** per skill so a
# benchmark is never read as a bare scalar — the same harbor-style row the
# ``audit-query benchmarks`` reader emits (PLAN-133 C4). $0, read-only,
# derives only from fields already on the ``benchmark_run`` event.
# ---------------------------------------------------------------------------


def _bench_cost_usd(r: Dict[str, Any]) -> float:
    """Per-run benchmark cost in USD. Prefers int-encoded
    ``cost_usd_cents`` (÷100); falls back to a legacy float ``cost_usd``."""
    cents = r.get("cost_usd_cents")
    if cents is not None:
        try:
            return int(cents) / 100.0
        except (TypeError, ValueError):
            return 0.0
    try:
        return float(r.get("cost_usd") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bench_duration_s(r: Dict[str, Any]) -> float:
    """Per-run wall-clock (the harbor 'compute' column) in seconds.
    Prefers int-encoded ``duration_ms`` (÷1000); falls back to legacy
    float ``duration_s``."""
    ms = r.get("duration_ms")
    if ms is not None:
        try:
            return int(ms) / 1000.0
        except (TypeError, ValueError):
            return 0.0
    try:
        return float(r.get("duration_s") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bench_pass_rate(r: Dict[str, Any]) -> float:
    """Per-run pass-rate. Prefers int-encoded ``pass_rate_bps`` (÷1000);
    falls back to legacy float ``pass_rate``."""
    bps = r.get("pass_rate_bps")
    if bps is not None:
        try:
            return int(bps) / 1000.0
        except (TypeError, ValueError):
            return 0.0
    try:
        return float(r.get("pass_rate") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bench_turns(r: Dict[str, Any]) -> int:
    """Per-run scenario count (the harbor 'turns' column). Tolerant."""
    try:
        return int(r.get("pass_count") or 0) + int(r.get("fail_count") or 0)
    except (TypeError, ValueError):
        return 0


def benchmark_rollup(
    *,
    audit_dir: Optional[Path] = None,
    since: Optional[timedelta] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Co-report cost + compute + turns alongside pass-rate per benchmark
    skill (PLAN-133 C4, harbor-style row). Read-only; fail-open on infra.

    Returns a JSON-serializable dict with a per-skill list. Each row carries
    the latest pass-rate plus the cumulative + latest cost/compute/turns so
    an operator sees both the marginal and trend cost of a benchmark.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = (now - since) if since is not None else None

    log_paths = discover_logs(audit_dir)
    by_skill: Dict[str, List[Dict[str, Any]]] = {}
    try:
        for ev in iter_unique_events(log_paths):
            if ev.get("action") != "benchmark_run":
                continue
            ts = _parse_ts(ev.get("ts"))
            if cutoff is not None and ts is not None and ts < cutoff:
                continue
            skill = str(ev.get("skill") or "?")
            by_skill.setdefault(skill, []).append(ev)
    except Exception:
        # fail-open-on-infra: a malformed log never crashes the rollup.
        by_skill = {}

    rows: List[Dict[str, Any]] = []
    tot_cost = 0.0
    tot_compute = 0.0
    tot_turns = 0
    for skill in sorted(by_skill.keys()):
        runs = sorted(by_skill[skill], key=lambda r: r.get("ts") or "")
        latest = runs[-1]
        s_cost = sum(_bench_cost_usd(r) for r in runs)
        s_compute = sum(_bench_duration_s(r) for r in runs)
        s_turns = sum(_bench_turns(r) for r in runs)
        tot_cost += s_cost
        tot_compute += s_compute
        tot_turns += s_turns
        rows.append({
            "skill": skill,
            "runs": len(runs),
            "latest_pass_rate": round(_bench_pass_rate(latest), 3),
            "latest_cost_usd": round(_bench_cost_usd(latest), 6),
            "total_cost_usd": round(s_cost, 6),
            "latest_compute_s": round(_bench_duration_s(latest), 3),
            "total_compute_s": round(s_compute, 3),
            "latest_turns": _bench_turns(latest),
            "total_turns": s_turns,
            "latest_ts": latest.get("ts"),
        })
    return {
        "per_skill": rows,
        "total_cost_usd": round(tot_cost, 6),
        "total_compute_s": round(tot_compute, 3),
        "total_turns": tot_turns,
        "skill_count": len(rows),
    }


def _extract_wave_id(event: Dict[str, Any]) -> Optional[str]:
    """Extract a wave-id from an event if present.

    Heuristic: check ``wave_id``, ``wave``, then scan
    ``desc_preview``/``description`` for a ``wave-X`` substring.
    """
    for key in ("wave_id", "wave"):
        v = event.get(key)
        if isinstance(v, str) and _WAVE_ID_RE.match(v):
            return v
    for key in ("desc_preview", "description", "task_description"):
        v = event.get(key)
        if isinstance(v, str):
            m = re.search(r"\b(wave-[a-z0-9-]{1,16})\b", v)
            if m and _WAVE_ID_RE.match(m.group(1)):
                return m.group(1)
    return None


# ---------------------------------------------------------------------------
# PLAN-178 W1.2-2 — native-source cross-check (audit-log × harness corpus)
#
# Default-OFF behavioral surface, gated by the ``--native`` flag (and the
# ``CEO_BUDGET_NATIVE=1`` env opt-in) — same pattern as the C4 benchmark
# block: when OFF, output is byte-for-byte unchanged. When ON, a
# ``native_cross_check`` block joins the audit-log ``agent_spawn`` ledger
# against the harness-native transcript corpus:
#
#     ~/.claude/projects/<cwd-slug>/<SESSION-UUID>/subagents/agent-a*.jsonl
#     ~/.claude/projects/<cwd-slug>/<SESSION-UUID>/subagents/workflows/
#         wf_*/agent-a*.jsonl        (journal.jsonl EXCLUDED — no meta)
#
# Join key (probe §handoff): ``(session_id, agentType~subagent_type,
# ordinal-by-timestamp)`` — the audit-log has no agentId and the native
# meta has no desc_hash, so within each (session, type) group both sides
# are sorted by timestamp and zipped pairwise. UNMATCHED residue on BOTH
# sides is ALWAYS reported (own section + count): silencing it would
# produce a falsely-low divergence. Rail category comes from the PATH
# shape (``workflows/wf_*/`` ⇒ workflow), never from ``taskKind`` — the
# field cannot distinguish the rails (probe §3 blocker #1).
#
# Doctrine: **cross-check, not authority-swap** — the audit-log rollup
# above remains the sole authority; this block is additive evidence and
# degrades (dormant) to nothing when the corpus is absent. Cache-token
# columns are reported token-only (no invented cache pricing); cost is
# computed over input+output, and a spawn whose model cannot be resolved
# to a priced id is reported as cost TBD — never $0.
# ---------------------------------------------------------------------------


def default_native_root() -> Path:
    """Root of the harness-native transcript corpus for THIS project.

    Honors ``CEO_NATIVE_USAGE_DIR`` env override (used by tests).
    Otherwise ``~/.claude/projects/<cwd-slug>/`` where ``<cwd-slug>`` is
    the absolute project path (``$CLAUDE_PROJECT_DIR``, else cwd) with
    ``/`` replaced by ``-`` (probe §1.1).
    """
    env_dir = os.environ.get("CEO_NATIVE_USAGE_DIR")
    if env_dir:
        return Path(env_dir)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    slug = _rp.project_slug(project_dir)  # PLAN-182 W3 (S321): slug via resolvedor unico, nunca re-derivado
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / slug


def _native_transcript_paths(
    native_root: Optional[Path],
) -> List[Tuple[Path, str, str]]:
    """Discover native agent transcripts under ``native_root``.

    Returns ``(path, rail, session_id)`` triples. Rail is derived from
    the PATH shape (probe §3 blocker: the corpus has no field for it):
    ``*/subagents/agent-a*.jsonl`` ⇒ ``task``;
    ``*/subagents/workflows/wf_*/agent-a*.jsonl`` ⇒ ``workflow``.
    ``journal.jsonl`` never matches (``agent-a*`` prefix). The
    SESSION-UUID is the first path component under the root.
    """
    out: List[Tuple[Path, str, str]] = []
    if native_root is None or not native_root.is_dir():
        return out
    root = str(native_root)
    task_glob = os.path.join(root, "*", "subagents", "agent-a*.jsonl")
    wf_glob = os.path.join(
        root, "*", "subagents", "workflows", "wf_*", "agent-a*.jsonl"
    )
    for pattern, rail in ((task_glob, "task"), (wf_glob, "workflow")):
        for raw in sorted(glob.glob(pattern)):
            p = Path(raw)
            try:
                session_id = p.relative_to(native_root).parts[0]
            except (ValueError, IndexError):
                session_id = "(unknown)"
            out.append((p, rail, session_id))
    return out


#: Usage keys summed per transcript (probe §handoff item 4). Cache columns
#: are reported token-only — no cache pricing row exists in the registry
#: and we never invent one.
_NATIVE_USAGE_KEYS: Tuple[str, ...] = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


def _read_native_spawn(
    transcript: Path,
    rail: str,
    session_id: str,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
    counters: Optional[Dict[str, int]] = None,
) -> Optional[Dict[str, Any]]:
    """Read ONE native spawn (transcript + tolerant meta pairing).

    Tolerant by doctrine (probe §handoff item 3): a missing meta, a
    malformed/truncated line (live session appending), or a missing
    field degrades the record — it never raises. Model precedence:
    ``meta.model`` first, else the first ``message.model`` seen in the
    transcript (the workflow-path metas carry NO model at all).
    """
    stem = transcript.name[: -len(".jsonl")]
    meta_path = transcript.with_name(stem + ".meta.json")
    agent_type = "(unknown)"
    meta_model: Optional[str] = None
    meta_description: Optional[str] = None
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = None
        if isinstance(meta, dict):
            # Hard fingerprint invariants (substrate-watch cc_native_usage,
            # 416/416 measured; codex S306 r3 P2 cure — same sonda as the
            # standalone puller): a meta that parses but lost either field
            # is schema drift, counted so native_cross_check can degrade.
            if "agentType" not in meta or "spawnDepth" not in meta:
                if counters is not None:
                    counters["meta_invariant_missing"] = (
                        counters.get("meta_invariant_missing", 0) + 1
                    )
            at = meta.get("agentType")
            if isinstance(at, str) and at.strip():
                agent_type = at.strip()
            mm = meta.get("model")
            if isinstance(mm, str) and mm.strip():
                meta_model = mm.strip()
            md = meta.get("description")
            if isinstance(md, str) and md:
                meta_description = md

    start_ts: Optional[str] = None
    transcript_model: Optional[str] = None
    sums = {k: 0 for k in _NATIVE_USAGE_KEYS}
    cache_5m = 0                      # nested usage.cache_creation split
    cache_1h = 0                      # (codex S306 r3 P2 cure — 1h TTL @2.0x)
    usage_events = 0
    try:
        with transcript.open("r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(rec, dict):
                    continue
                ts = rec.get("timestamp")
                if start_ts is None and isinstance(ts, str) and ts:
                    start_ts = ts
                msg = rec.get("message")
                if not isinstance(msg, dict):
                    continue
                if transcript_model is None:
                    m = msg.get("model")
                    if isinstance(m, str) and m.strip():
                        transcript_model = m.strip()
                usage = msg.get("usage")
                if not isinstance(usage, dict):
                    continue
                # Fingerprint drift sonda (codex S306 r2 P2 cure): a usage
                # dict with NEITHER core key is schema drift — counted so
                # native_cross_check can degrade to audit-only, never summed
                # as a zero-token event.
                if ("input_tokens" not in usage) and ("output_tokens" not in usage):
                    if counters is not None:
                        counters["usage_missing_core_keys"] = (
                            counters.get("usage_missing_core_keys", 0) + 1
                        )
                    continue
                bearing = False
                for key in _NATIVE_USAGE_KEYS:
                    v = usage.get(key)
                    if isinstance(v, (int, float)):
                        sums[key] += int(v)
                        if key in ("input_tokens", "output_tokens"):
                            bearing = True
                cc = usage.get("cache_creation")
                if isinstance(cc, dict):
                    v5 = cc.get("ephemeral_5m_input_tokens")
                    v1 = cc.get("ephemeral_1h_input_tokens")
                    if isinstance(v5, (int, float)):
                        cache_5m += int(v5)
                    if isinstance(v1, (int, float)):
                        cache_1h += int(v1)
                if bearing:
                    usage_events += 1
    except OSError:
        # codex S306 P2 cure: an unreadable transcript must NOT degrade to a
        # zero-token record with a "known" $0.00 cost — it corrupts totals
        # AND the ordinal join. Skip the spawn, count it observably.
        if counters is not None:
            counters["transcripts_unreadable"] = (
                counters.get("transcripts_unreadable", 0) + 1
            )
        sys.stderr.write(
            "budget-summary: unreadable native transcript — spawn skipped: "
            "%s\n" % transcript
        )
        return None

    model_raw = meta_model or transcript_model
    model_id = _normalize_model_id(model_raw, pricing=pricing)
    t_in = sums["input_tokens"]
    t_out = sums["output_tokens"]
    # Cache classes are BILLABLE (docs/provider-pricing.md: read @0.10x
    # input, write @1.25x on the 5m TTL and @2.00x on the 1h TTL). When the
    # transcript carries the nested ``usage.cache_creation`` split, each
    # tier gets its own multiplier (codex S306 r3 P2 cure); writes NOT
    # attributed by the split assume 5m, the API default. Priced as
    # input-token EQUIVALENTS so compute_cost_usd's full row/dated-row
    # resolution is reused instead of a second rate table (codex S306 r1 P1
    # cure: pricing only fresh in/out understated the native total ~10x).
    c_total = sums["cache_creation_input_tokens"]
    c_1h = min(cache_1h, c_total)
    c_5m = min(cache_5m, c_total - c_1h)
    c_rest = c_total - c_1h - c_5m    # unattributed -> 5m assumption
    cache_equiv_in = int(
        0.10 * sums["cache_read_input_tokens"]
        + 1.25 * (c_5m + c_rest)
        + 2.00 * c_1h
    )
    cost = compute_cost_usd(
        model_id, t_in + cache_equiv_in, t_out, pricing=pricing, ts=start_ts
    )
    return {
        "session_id": session_id,
        "rail": rail,
        "agent_type": agent_type,
        "description": meta_description,
        "transcript": transcript.name,
        "start_ts": start_ts,
        "usage_events": usage_events,
        "tokens_in": t_in,
        "tokens_out": t_out,
        "cache_creation_tokens": sums["cache_creation_input_tokens"],
        "cache_read_tokens": sums["cache_read_input_tokens"],
        "model_raw": model_raw,
        "model_id": model_id,
        "cost_usd": cost,
        "cost_tbd": cost is None,
    }


def collect_native_spawns(
    native_root: Optional[Path] = None,
    *,
    cutoff: Optional[datetime] = None,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
    counters: Optional[Dict[str, int]] = None,
) -> List[Dict[str, Any]]:
    """Collect all native spawn records under ``native_root``.

    ``cutoff`` mirrors the rollup's ``--since`` semantics: a spawn whose
    start timestamp parses AND precedes the cutoff is excluded; a spawn
    with no parseable timestamp is kept (visibility over silence).
    """
    spawns: List[Dict[str, Any]] = []
    for path, rail, session_id in _native_transcript_paths(native_root):
        rec = _read_native_spawn(
            path, rail, session_id, pricing=pricing, counters=counters
        )
        if rec is None:               # unreadable transcript — counted, skipped
            continue
        if cutoff is not None:
            parsed = _parse_ts_any(rec.get("start_ts"))
            if parsed is not None and parsed < cutoff:
                continue
        spawns.append(rec)
    return spawns


def _collect_audit_spawn_rows(
    log_paths: Iterable[Path],
    cutoff: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Audit-log side of the join: one row per ``agent_spawn`` event.

    Token fields are None-PRESERVING (not coerced to 0): a null stays
    null so the report can say "no number on the audit side" instead of
    fabricating a 0 that would fake a divergence.
    """

    def _opt_int(v: Any) -> Optional[int]:
        if isinstance(v, bool):
            return None
        if isinstance(v, (int, float)):
            return int(v)
        return None

    rows: List[Dict[str, Any]] = []
    for ev in iter_unique_events(log_paths):
        if (ev.get("action") or "") != "agent_spawn":
            continue
        ts_parsed = _parse_ts(ev.get("ts"))
        if cutoff is not None and ts_parsed is not None and ts_parsed < cutoff:
            continue
        subagent_type = ev.get("subagent_type")
        desc_hash = ev.get("desc_hash")
        rows.append({
            "session_id": ev.get("session_id") or "(unknown)",
            "agent_type": (
                subagent_type.strip()
                if isinstance(subagent_type, str) and subagent_type.strip()
                else "(unknown)"
            ),
            "desc_hash": (
                desc_hash if isinstance(desc_hash, str) and desc_hash else None
            ),
            "ts": ev.get("ts"),
            "model": ev.get("model"),
            "tokens_in": _opt_int(ev.get("tokens_in")),
            "tokens_out": _opt_int(ev.get("tokens_out")),
            "tokens_total": _opt_int(ev.get("tokens_total")),
        })
    return rows


def _audit_total_tokens(row: Dict[str, Any]) -> Optional[int]:
    """Comparable audit-side token total, or None when the ledger has no
    number for this spawn (the current-rotation reality: all null)."""
    total = row.get("tokens_total")
    if isinstance(total, int):
        return total
    t_in = row.get("tokens_in")
    t_out = row.get("tokens_out")
    if isinstance(t_in, int) and isinstance(t_out, int):
        return t_in + t_out
    return None


def native_cross_check(
    *,
    audit_dir: Optional[Path] = None,
    native_root: Optional[Path] = None,
    since: Optional[timedelta] = None,
    now: Optional[datetime] = None,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """Join the audit-log spawn ledger against the native corpus (W1.2-2).

    Join key: ``(session_id, agent_type)`` with agent_type =
    audit ``subagent_type`` ≈ native meta ``agentType`` (case-folded);
    within each group both sides sort by timestamp and zip by ordinal.
    Matched pairs, plus UNMATCHED residue from BOTH sides, are all
    returned — nothing is silenced. Read-only; fail-open on infra
    (a broken corpus degrades to a dormant block with a note, never a
    crash — the audit-log rollup is unaffected either way).
    """
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = (now - since) if since is not None else None
    root = native_root if native_root is not None else default_native_root()

    doctrine = (
        "cross-check, not authority-swap: the native source NEVER "
        "silently replaces the audit-log rollup"
    )

    infra_note: Optional[str] = None
    read_counters: Dict[str, int] = {}
    try:
        transcript_count = len(_native_transcript_paths(root))
        native = collect_native_spawns(
            root, cutoff=cutoff, pricing=pricing, counters=read_counters
        )
    except Exception as exc:  # fail-open on infra (CLAUDE.md §4)
        transcript_count = 0
        native = []
        infra_note = (
            f"native collection failed ({type(exc).__name__}) — degraded to "
            f"audit-log only"
        )

    # Audit side is read BEFORE any early return (codex S306 r5 P2 cure): a
    # dormant/drifted native source must still report ACCURATE audit counts —
    # hard-coded zeros would tell JSON consumers the audit ledger is empty
    # when only the native side is missing.
    audit_rows = _collect_audit_spawn_rows(discover_logs(audit_dir), cutoff)

    # Path-shape sonda (codex S306 r3 P2 cure — parity with the puller): a
    # walk sweep seeing MORE agent transcripts than the two known globs
    # matched means the harness moved the layout. Report DRIFT, never
    # ordinary dormancy or a zero total.
    try:
        walk_seen = sum(
            1 for p in root.rglob("agent-a*.jsonl") if "subagents" in p.parts
        )
    except OSError:
        walk_seen = transcript_count
    if walk_seen > transcript_count:
        return {
            "doctrine": doctrine,
            "native_root": str(root),
            "dormant": True,
            "degraded": "schema-drift",
            "drift": {"path_shape_unmatched": walk_seen - transcript_count},
            "native_spawn_count": 0,
            "audit_spawn_count": len(audit_rows),
            "unmatched_audit_count": len(audit_rows),
            "note": (
                "native path shape drifted (%d transcript(s) outside the "
                "known globs) — cross-check degraded to audit-log only"
                % (walk_seen - transcript_count)
            ),
        }

    if transcript_count == 0:
        result: Dict[str, Any] = {
            "doctrine": doctrine,
            "native_root": str(root),
            "dormant": True,
            "native_spawn_count": 0,
            "audit_spawn_count": len(audit_rows),
            "matched_count": 0,
            "comparable_pair_count": 0,
            "unmatched_native_count": 0,
            "unmatched_audit_count": len(audit_rows),
            "note": (
                infra_note
                or "no native transcripts found — audit-log rollup is the "
                   "sole source (dormant, by design)"
            ),
        }
        return result

    # Drift gate on the integrated reader (codex S306 r2 P2 cure — same
    # fingerprint sonda as the puller): usage dicts whose core token keys
    # vanished mean the harness schema moved; publishing zero/partial totals
    # would present drift as genuine zero usage. Degrade to audit-only.
    drift_hits = {
        k: read_counters.get(k, 0)
        for k in ("usage_missing_core_keys", "meta_invariant_missing")
        if read_counters.get(k, 0) > 0
    }
    if drift_hits:
        return {
            "doctrine": doctrine,
            "native_root": str(root),
            "dormant": True,
            "degraded": "schema-drift",
            "drift": dict(read_counters),
            "native_spawn_count": 0,
            "audit_spawn_count": len(audit_rows),
            "unmatched_audit_count": len(audit_rows),
            "note": (
                "native schema drifted (%s) — cross-check degraded to "
                "audit-log only"
                % ", ".join(f"{k}={v}" for k, v in sorted(drift_hits.items()))
            ),
        }

    def _key(session_id: Any, agent_type: Any) -> Tuple[str, str]:
        return (
            str(session_id or ""),
            str(agent_type or "").strip().lower(),
        )

    # Pass 0 — EXACT join (codex S306 r2 P1 cure): native ``meta.description``
    # hashes (sha256, same function as audit_log's hash_description) to the
    # audit row's ``desc_hash``. This survives the shape where a teammate's
    # native agentType is its NAME while the audit row says
    # ``general-purpose`` — the (session, type) grouping alone under-matches.
    audit_by_hash: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for row in audit_rows:
        h = row.get("desc_hash")
        if isinstance(h, str) and h:
            audit_by_hash.setdefault(
                (str(row["session_id"] or ""), h), []
            ).append(row)
    for group in audit_by_hash.values():
        group.sort(key=lambda r: r.get("ts") or "")
    exact_pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    consumed_audit: Set[int] = set()
    remaining_native: List[Dict[str, Any]] = []
    # Duplicate-description groups pair oldest-to-oldest on BOTH sides
    # (codex S306 r4 P2 cure): the audit hash groups are ts-sorted above, so
    # native candidates must be consumed in start_ts order too — glob order
    # would associate the wrong token totals within the duplicate group.
    for rec in sorted(native, key=lambda r: r.get("start_ts") or ""):
        desc = rec.get("description")
        if isinstance(desc, str) and desc:
            hkey = (
                str(rec["session_id"] or ""),
                hashlib.sha256(
                    desc.encode("utf-8", errors="replace")
                ).hexdigest(),
            )
            group = audit_by_hash.get(hkey)
            if group:
                aud = group.pop(0)
                consumed_audit.add(id(aud))
                exact_pairs.append((rec, aud))
                continue
        remaining_native.append(rec)
    remaining_audit = [r for r in audit_rows if id(r) not in consumed_audit]

    native_by: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for rec in remaining_native:
        native_by.setdefault(_key(rec["session_id"], rec["agent_type"]), []).append(rec)
    audit_by: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for row in remaining_audit:
        audit_by.setdefault(_key(row["session_id"], row["agent_type"]), []).append(row)

    for group in native_by.values():
        group.sort(key=lambda r: r.get("start_ts") or "")
    for group in audit_by.values():
        group.sort(key=lambda r: r.get("ts") or "")

    matched: List[Dict[str, Any]] = []
    unmatched_native: List[Dict[str, Any]] = []
    unmatched_audit: List[Dict[str, Any]] = []
    divergences_by_rail: Dict[str, List[float]] = {"task": [], "workflow": []}

    def _emit_pair(nat: Dict[str, Any], aud: Dict[str, Any],
                   ordinal: Optional[int], join: str) -> None:
        nat_total = int(nat["tokens_in"]) + int(nat["tokens_out"])
        aud_total = _audit_total_tokens(aud)
        comparable = aud_total is not None
        divergence_pct: Optional[float] = None
        if comparable:
            base = aud_total if aud_total else 1
            divergence_pct = round(
                abs(nat_total - aud_total) * 100.0 / base, 2
            )
            divergences_by_rail.setdefault(nat["rail"], []).append(
                divergence_pct
            )
        matched.append({
            "session_id": str(nat["session_id"] or ""),
            "agent_type": str(nat["agent_type"] or "").strip().lower(),
            "ordinal": ordinal,
            "join": join,
            "native_rail": nat["rail"],
            "native_start_ts": nat["start_ts"],
            "native_tokens_in": nat["tokens_in"],
            "native_tokens_out": nat["tokens_out"],
            "native_cache_creation_tokens": nat["cache_creation_tokens"],
            "native_cache_read_tokens": nat["cache_read_tokens"],
            "native_model_raw": nat["model_raw"],
            "native_model_id": nat["model_id"],
            "native_cost_usd": nat["cost_usd"],
            "native_cost_tbd": nat["cost_tbd"],
            "audit_ts": aud["ts"],
            "audit_model": aud["model"],
            "audit_tokens_in": aud["tokens_in"],
            "audit_tokens_out": aud["tokens_out"],
            "audit_tokens_total": aud["tokens_total"],
            "comparable": comparable,
            "divergence_pct": divergence_pct,
        })

    for nat, aud in exact_pairs:
        _emit_pair(nat, aud, None, "desc_hash")

    for key in sorted(set(native_by) | set(audit_by)):
        n_group = native_by.get(key, [])
        a_group = audit_by.get(key, [])
        pair_n = min(len(n_group), len(a_group))
        for i in range(pair_n):
            _emit_pair(n_group[i], a_group[i], i, "ordinal")
        for i in range(pair_n, len(n_group)):
            rec = dict(n_group[i])
            rec["ordinal"] = i
            unmatched_native.append(rec)
        for i in range(pair_n, len(a_group)):
            row = dict(a_group[i])
            row["ordinal"] = i
            unmatched_audit.append(row)

    tok = {
        "in": sum(int(r["tokens_in"]) for r in native),
        "out": sum(int(r["tokens_out"]) for r in native),
        "cache_creation": sum(int(r["cache_creation_tokens"]) for r in native),
        "cache_read": sum(int(r["cache_read_tokens"]) for r in native),
    }
    priced = [r for r in native if r["cost_usd"] is not None]
    tbd_spawns = len(native) - len(priced)
    native_cost = round(sum(float(r["cost_usd"]) for r in priced), 6) if priced else None

    max_div: Dict[str, Optional[float]] = {}
    for rail in ("task", "workflow"):
        vals = divergences_by_rail.get(rail) or []
        max_div[rail] = max(vals) if vals else None

    comparable_pairs = sum(1 for m in matched if m["comparable"])

    result = {
        "doctrine": doctrine,
        "native_root": str(root),
        "dormant": False,
        "native_spawn_count": len(native),
        "native_task_spawns": sum(1 for r in native if r["rail"] == "task"),
        "native_workflow_spawns": sum(
            1 for r in native if r["rail"] == "workflow"
        ),
        "native_usage_event_count": sum(int(r["usage_events"]) for r in native),
        "native_transcripts_unreadable": read_counters.get(
            "transcripts_unreadable", 0
        ),
        "audit_spawn_count": len(audit_rows),
        "matched_count": len(matched),
        "comparable_pair_count": comparable_pairs,
        "unmatched_native_count": len(unmatched_native),
        "unmatched_audit_count": len(unmatched_audit),
        "native_tokens": tok,
        "native_cost_usd": native_cost,
        "native_cost_tbd_spawns": tbd_spawns,
        "native_cost_note": (
            "spawns without a resolvable/priced model are cost TBD — they "
            "are NEVER priced as $0 and are excluded from native_cost_usd"
        ),
        "max_divergence_pct_by_rail": max_div,
        "matched": matched,
        "unmatched_native": unmatched_native,
        "unmatched_audit": unmatched_audit,
    }
    if infra_note:
        result["note"] = infra_note
    return result


# ---------------------------------------------------------------------------
# Memory-claim validator
# ---------------------------------------------------------------------------


def validate_memory_claim(
    total_cost_usd: Optional[float],
    low: float = MEMORY_CLAIM_LOW_USD,
    high: float = MEMORY_CLAIM_HIGH_USD,
    ratio_low: float = MEMORY_CLAIM_PASS_RATIO_LOW,
    ratio_high: float = MEMORY_CLAIM_PASS_RATIO_HIGH,
) -> Dict[str, Any]:
    """Check the rollup against the CLAUDE.md S82-S99 memory claim band.

    Returns a structured verdict:
      - ``status``: ``"pass"`` (within band), ``"warn"`` (outside
        [ratio_low, ratio_high] multiplied band) or ``"unknown"``
        (no cost computed).
      - ``band_low_usd`` / ``band_high_usd`` / ``observed_usd`` /
        ``ratio_to_band_low`` / ``ratio_to_band_high``.

    Methodology: the memory claim is itself a *range* ($1003-1543); we
    pass when the observed cost is anywhere inside, warn when outside
    the [0.5*low, 1.5*high] enclosing band. This wide gate accepts
    pricing-table drift while still flagging obvious bugs.
    """
    if total_cost_usd is None:
        return {
            "status": "unknown",
            "band_low_usd": low,
            "band_high_usd": high,
            "observed_usd": None,
            "ratio_to_band_low": None,
            "ratio_to_band_high": None,
            "message": "No cost computed; pricing table likely missed all models.",
        }
    enclosing_low = low * ratio_low
    enclosing_high = high * ratio_high
    if low <= total_cost_usd <= high:
        status = "pass"
        message = (
            f"Observed ${total_cost_usd:.2f} within memory-claim "
            f"band [${low:.2f}, ${high:.2f}]."
        )
    elif enclosing_low <= total_cost_usd <= enclosing_high:
        status = "pass"
        message = (
            f"Observed ${total_cost_usd:.2f} within widened band "
            f"[${enclosing_low:.2f}, ${enclosing_high:.2f}] "
            f"(memory claim ${low:.2f}-${high:.2f})."
        )
    else:
        status = "warn"
        message = (
            f"Observed ${total_cost_usd:.2f} OUTSIDE widened band "
            f"[${enclosing_low:.2f}, ${enclosing_high:.2f}] "
            f"(memory claim ${low:.2f}-${high:.2f}). "
            f"Likely token-tracking gap OR pricing drift."
        )
    return {
        "status": status,
        "band_low_usd": low,
        "band_high_usd": high,
        "observed_usd": total_cost_usd,
        "ratio_to_band_low": round(total_cost_usd / low, 4) if low else None,
        "ratio_to_band_high": round(total_cost_usd / high, 4) if high else None,
        "message": message,
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def _fmt_tokens(n: int) -> str:
    return f"{n:>14,}"


def _format_native_block(native: Dict[str, Any]) -> List[str]:
    """Human rendering of the W1.2 native cross-check block.

    UNMATCHED residue from BOTH sides always appears — aggregated by
    (session, rail, agent_type) so every unmatched spawn is represented
    — each section headed by its COUNT. Full per-spawn detail lives in
    the ``--json`` output.
    """
    lines: List[str] = []
    lines.append("")
    lines.append(
        "Native cross-check (PLAN-178 W1.2 — cross-check, not authority-swap):"
    )
    lines.append(f"  Native root     : {native.get('native_root')}")
    if native.get("dormant"):
        lines.append(f"  Status          : DORMANT — {native.get('note')}")
        return lines
    lines.append(
        f"  Native spawns   : {native['native_spawn_count']:,} "
        f"(task={native['native_task_spawns']:,}, "
        f"workflow={native['native_workflow_spawns']:,})"
    )
    lines.append(
        f"  Audit spawns    : {native['audit_spawn_count']:,} "
        f"(agent_spawn events in scope)"
    )
    lines.append(
        f"  Matched pairs   : {native['matched_count']:,} "
        f"(token-comparable: {native['comparable_pair_count']:,})"
    )
    tok = native.get("native_tokens") or {}
    lines.append(
        f"  Native tokens   : in={tok.get('in', 0):,} out={tok.get('out', 0):,} "
        f"cache_creation={tok.get('cache_creation', 0):,} "
        f"cache_read={tok.get('cache_read', 0):,}"
    )
    cost = native.get("native_cost_usd")
    tbd = int(native.get("native_cost_tbd_spawns") or 0)
    if cost is None and tbd:
        cost_col = f"TBD ({tbd:,} spawns without resolvable model/price)"
    elif tbd:
        cost_col = (
            f"${cost:,.4f} + TBD ({tbd:,} spawns without resolvable "
            f"model/price)"
        )
    elif cost is None:
        cost_col = "-"
    else:
        cost_col = f"${cost:,.4f}"
    lines.append(f"  Native cost     : {cost_col}")
    lines.append(
        "                    (cache priced as input-equivalents: read @0.10x,"
        " write @1.25x — 5m-TTL assumption, docs/provider-pricing.md)"
    )
    unreadable = int(native.get("native_transcripts_unreadable", 0) or 0)
    if unreadable:
        lines.append(
            f"  Skipped         : {unreadable} unreadable native transcript(s)"
            " excluded from totals and matching"
        )
    max_div = native.get("max_divergence_pct_by_rail") or {}
    div_cols = []
    for rail in ("task", "workflow"):
        v = max_div.get(rail)
        div_cols.append(f"{rail}={v:.2f}%" if v is not None else f"{rail}=-")
    div_note = ""
    if native["comparable_pair_count"] == 0:
        div_note = (
            " (no comparable pairs: audit-log spawn tokens are null in scope)"
        )
    lines.append(f"  Max divergence  : {' '.join(div_cols)}{div_note}")

    def _grouped(rows: List[Dict[str, Any]], with_rail: bool) -> List[str]:
        counts: Dict[Tuple[str, ...], int] = {}
        for r in rows:
            sess = str(r.get("session_id") or "(unknown)")[:8]
            if with_rail:
                gkey = (sess, str(r.get("rail") or "?"), str(r.get("agent_type") or "?"))
            else:
                gkey = (sess, str(r.get("agent_type") or "?"))
            counts[gkey] = counts.get(gkey, 0) + 1
        out = []
        for gkey in sorted(counts):
            if with_rail:
                out.append(
                    f"    {gkey[0]:<8}  {gkey[1]:<8}  {gkey[2]:<28}  "
                    f"x{counts[gkey]}"
                )
            else:
                out.append(f"    {gkey[0]:<8}  {gkey[1]:<38}  x{counts[gkey]}")
        return out

    un_nat = native.get("unmatched_native") or []
    lines.append(
        f"  UNMATCHED — native side (no audit-log counterpart): "
        f"{native['unmatched_native_count']:,}"
    )
    if un_nat:
        lines.extend(_grouped(un_nat, with_rail=True))
    else:
        lines.append("    (none)")
    un_aud = native.get("unmatched_audit") or []
    lines.append(
        f"  UNMATCHED — audit-log side (no native counterpart): "
        f"{native['unmatched_audit_count']:,}"
    )
    if un_aud:
        lines.extend(_grouped(un_aud, with_rail=False))
    else:
        lines.append("    (none)")
    lines.append(
        "  NOTE: the native source never replaces the audit-log totals "
        "above; the residue is shown in full because silencing it would "
        "fake a low divergence."
    )
    return lines


def format_human(data: Dict[str, Any], memory_claim: Optional[Dict[str, Any]] = None) -> str:
    """Render the rollup as a human-readable text block."""
    lines: List[str] = []
    scope = data.get("plan_filter") or "(all plans)"
    since = data.get("since") or "(all time)"
    lines.append(f"FinOps summary — scope={scope} since={since}")
    lines.append("-" * 70)
    lines.append(f"Audit dir       : {data.get('audit_dir')}")
    files = data.get("log_files_read") or []
    lines.append(f"Logs read       : {len(files)} file(s)")
    for f in files:
        lines.append(f"                  - {f}")
    lines.append(f"Events          : {data['total_events']:>14,}")
    lines.append(f"Codex events    : {data['codex_event_count']:>14,}")
    lines.append(f"Unknown plan_id : {data['unknown_plan_count']:>14,}")
    lines.append(f"Tokens in       : {_fmt_tokens(data['total_tokens_in'])}")
    lines.append(f"Tokens out      : {_fmt_tokens(data['total_tokens_out'])}")
    lines.append(f"Tokens total    : {_fmt_tokens(data['total_tokens'])}")
    cost = data.get("total_cost_usd")
    src = data.get("cost_source") or "unknown"
    if cost is None:
        lines.append(f"Cost (USD)      : -              (source={src})")
    else:
        lines.append(f"Cost (USD)      : ${cost:>13,.4f} (source={src})")

    per_plan = data.get("per_plan") or []
    if per_plan and not data.get("plan_filter"):
        lines.append("")
        lines.append("Per plan:")
        lines.append(
            f"  {'plan_id':<14}  {'events':>7}  {'tokens_total':>14}  "
            f"{'cost_usd':>12}"
        )
        for row in per_plan:
            cost_col = (
                f"${row['cost_usd']:.4f}" if row.get("cost_known") else "-"
            )
            lines.append(
                f"  {row['plan_id']:<14}  {row['event_count']:>7,}  "
                f"{row['tokens_total']:>14,}  {cost_col:>12}"
            )

    per_wave = data.get("per_wave")
    if per_wave:
        lines.append("")
        lines.append("Per wave:")
        lines.append(
            f"  {'wave':<14}  {'events':>7}  {'tokens_total':>14}  "
            f"{'cost_usd':>12}"
        )
        for row in per_wave:
            cost_col = f"${row['cost_usd']:.4f}" if row['cost_usd'] else "-"
            lines.append(
                f"  {row['wave']:<14}  {row['event_count']:>7,}  "
                f"{row['tokens_total']:>14,}  {cost_col:>12}"
            )

    # PLAN-133 C4 — harbor-style benchmark co-report (only when --benchmarks).
    benchmarks = data.get("benchmarks")
    if benchmarks is not None:
        rows = benchmarks.get("per_skill") or []
        lines.append("")
        lines.append("Benchmarks (harbor-style — pass-rate never read alone):")
        if not rows:
            lines.append("  (no benchmark_run events in scope)")
        else:
            lines.append(
                f"  {'skill':<24}  {'runs':>4}  {'pass_rate':>9}  "
                f"{'cost_usd':>10}  {'compute_s':>10}  {'turns':>7}"
            )
            for row in rows:
                lines.append(
                    f"  {str(row['skill'])[:24]:<24}  {row['runs']:>4}  "
                    f"{row['latest_pass_rate']:>9.3f}  "
                    f"${row['total_cost_usd']:>9.4f}  "
                    f"{row['total_compute_s']:>10.1f}  "
                    f"{row['total_turns']:>7,}"
                )
            lines.append(
                f"  {'TOTAL':<24}  {'':>4}  {'':>9}  "
                f"${benchmarks['total_cost_usd']:>9.4f}  "
                f"{benchmarks['total_compute_s']:>10.1f}  "
                f"{benchmarks['total_turns']:>7,}"
            )

    # PLAN-178 W1.2 — native cross-check (only when --native / env opt-in).
    native = data.get("native_cross_check")
    if native is not None:
        lines.extend(_format_native_block(native))

    if memory_claim is not None:
        lines.append("")
        lines.append("Memory-claim validation:")
        lines.append(f"  status  : {memory_claim['status']}")
        lines.append(f"  message : {memory_claim['message']}")

    return "\n".join(lines)


def format_json(data: Dict[str, Any], memory_claim: Optional[Dict[str, Any]] = None) -> str:
    payload = dict(data)
    if memory_claim is not None:
        payload["memory_claim_validation"] = memory_claim
    return json.dumps(payload, indent=2, sort_keys=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="budget-summary",
        description=(
            "FinOps rollup across all audit-log rotations "
            "(PLAN-083 Wave 0b sub-0.8)."
        ),
    )
    sub = p.add_subparsers(dest="subcommand")

    sp = sub.add_parser("summary", help="Print cumulative summary.")
    sp.add_argument("--since", metavar="EXPR", default=None,
                    help="Time window (Nm/Nh/Nd, e.g. 30d).")
    sp.add_argument("--plan-id", metavar="PLAN-NNN", default=None,
                    help="Limit rollup to a single plan_id.")
    sp.add_argument("--by-wave", action="store_true",
                    help="Include per-wave aggregates.")
    sp.add_argument("--json", action="store_true",
                    help="Emit JSON (default: human table).")
    sp.add_argument("--validate-memory-claim", action="store_true",
                    help="Cross-check rollup against CLAUDE.md memory claim band.")
    sp.add_argument("--audit-dir", metavar="PATH", default=None,
                    help="Override audit-log directory.")
    # PLAN-133 C4 — default-OFF harbor-style benchmark co-report.
    sp.add_argument("--benchmarks", action="store_true",
                    help=(
                        "Append a harbor-style benchmark co-report "
                        "(cost + compute + turns alongside pass-rate per "
                        "skill). Default-OFF; also enabled by "
                        "CEO_BUDGET_BENCHMARKS=1 (PLAN-133 C4)."
                    ))
    # PLAN-178 W1.2 — default-OFF native-source cross-check.
    sp.add_argument("--native", action="store_true",
                    help=(
                        "Append the native-source cross-check: audit-log "
                        "agent_spawn ledger joined against the harness "
                        "transcript corpus under ~/.claude/projects/"
                        "<cwd-slug>/. Cross-check, not authority-swap; "
                        "UNMATCHED residue on both sides is always shown. "
                        "Default-OFF; also enabled by CEO_BUDGET_NATIVE=1 "
                        "(PLAN-178 W1.2)."
                    ))
    sp.add_argument("--native-root", metavar="PATH", default=None,
                    help=(
                        "Override the native transcript root (default: "
                        "~/.claude/projects/<cwd-slug>; env override "
                        "CEO_NATIVE_USAGE_DIR)."
                    ))
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 2

    if args.subcommand is None:
        # Default to "summary" when invoked bare.
        args.subcommand = "summary"
        args.since = None
        args.plan_id = None
        args.by_wave = False
        args.json = False
        args.validate_memory_claim = False
        args.audit_dir = None
        args.benchmarks = False
        args.native = False
        args.native_root = None

    if args.subcommand != "summary":
        sys.stderr.write(f"budget-summary: unknown subcommand {args.subcommand!r}\n")
        return 2

    since_delta: Optional[timedelta] = None
    if args.since:
        try:
            since_delta = parse_since(args.since)
        except ValueError as e:
            sys.stderr.write(f"budget-summary: {e}\n")
            return 2

    if args.plan_id and not _PLAN_ID_RE.match(args.plan_id):
        sys.stderr.write(
            f"budget-summary: --plan-id must look like PLAN-NNN "
            f"(got {args.plan_id!r})\n"
        )
        return 2

    audit_dir = Path(args.audit_dir) if args.audit_dir else None

    data = rollup(
        audit_dir=audit_dir,
        plan_filter=args.plan_id,
        since=since_delta,
        by_wave=args.by_wave,
    )
    data["since"] = args.since

    # PLAN-133 C4 — default-OFF benchmark co-report. Enabled by --benchmarks
    # or CEO_BUDGET_BENCHMARKS=1. When OFF, output is byte-for-byte unchanged.
    benchmarks_on = bool(getattr(args, "benchmarks", False)) or (
        os.environ.get("CEO_BUDGET_BENCHMARKS", "") == "1"
    )
    if benchmarks_on:
        data["benchmarks"] = benchmark_rollup(
            audit_dir=audit_dir,
            since=since_delta,
        )

    # PLAN-178 W1.2 — default-OFF native cross-check. Enabled by --native or
    # CEO_BUDGET_NATIVE=1. When OFF, output is byte-for-byte unchanged (and
    # a dormant corpus degrades to a one-line dormant note, never a crash).
    # Note: the cross-check is session-scoped; --plan-id does NOT filter it
    # (the native corpus carries no plan_id field — probe §handoff item 6).
    native_on = bool(getattr(args, "native", False)) or (
        os.environ.get("CEO_BUDGET_NATIVE", "") == "1"
    )
    # Kill-switch (W1.2-5b, env-inventory.json): dominates the opt-in.
    if native_on and os.environ.get("CEO_NATIVE_COST_DISABLE", "") == "1":
        native_on = False
        sys.stderr.write(
            "budget-summary: native cross-check disabled by "
            "CEO_NATIVE_COST_DISABLE=1\n"
        )
    # codex S306 P2 cure: the native source carries no plan field (probe
    # §handoff item 6), so under --plan-id an unscoped cross-check would put
    # every plan's native activity inside a plan-scoped report. Suppress it.
    if native_on and getattr(args, "plan_id", None):
        native_on = False
        sys.stderr.write(
            "budget-summary: native cross-check suppressed under --plan-id "
            "(native source has no plan field; run without --plan-id to "
            "see it)\n"
        )
    if native_on:
        native_root = (
            Path(args.native_root)
            if getattr(args, "native_root", None)
            else None
        )
        data["native_cross_check"] = native_cross_check(
            audit_dir=audit_dir,
            native_root=native_root,
            since=since_delta,
        )

    memory_claim: Optional[Dict[str, Any]] = None
    if args.validate_memory_claim:
        memory_claim = validate_memory_claim(data.get("total_cost_usd"))

    if args.json:
        print(format_json(data, memory_claim))
    else:
        print(format_human(data, memory_claim))
    return 0


if __name__ == "__main__":
    sys.exit(main())
