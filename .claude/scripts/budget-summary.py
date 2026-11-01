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
import importlib.util
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
#: opus-5-fast $10/$50 premium row; sonnet-5 $2/$10 — the launch intro price
#: became the STANDARD price (official pricing page fetched 2026-09-01: the
#: scheduled 2026-09-01 increase to $3/$15 "will not occur"; PLAN-169 S338
#: follow-up).
#: ADR-149 Amendment 3 (S357): claude-opus-5-5 $4/$20 (pricing page fetched
#: 2026-09-22); its 0.05x cache-read rate lives in
#: _CACHE_READ_MULTIPLIER_OVERRIDES below.
_DEFAULT_PRICING: Dict[str, Dict[str, float]] = {
    "claude-opus-4-8":             {"in": 0.005, "out": 0.025},
    "claude-opus-4-8-fast":       {"in": 0.010, "out": 0.050},
    "claude-fable-5":             {"in": 0.010, "out": 0.050},
    "claude-fable-5-1":           {"in": 0.010, "out": 0.050},  # ADR-149 Amendment 2 (S338)
    "claude-opus-5":              {"in": 0.005, "out": 0.025},
    "claude-opus-5-fast":         {"in": 0.010, "out": 0.050},
    "claude-opus-5-5":            {"in": 0.004, "out": 0.020},  # ADR-149 Amendment 3 (S357)
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


#: Fractional-seconds tolerant variant (PLAN-178 W1.2). Native transcript
#: lines stamp ``2026-08-11T14:48:12.648Z``; the audit-log stamps whole
#: seconds. Ordering uses the raw ISO string (lexicographic == chronological
#: for same-zone ISO-8601); PARSING for the ``--since`` cutoff strips the
#: fraction first, then reuses ``_parse_ts``.
_TS_FRACTION_RE = re.compile(r"\.\d+(?=Z|[+-]\d{2}:?\d{2}$)")


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


#: PLAN-163 W2 P2a — event-date-aware rows (per-1k twin of the tables in
#: audit-telemetry.py / ceo-cost.py): an event is priced by its OWN ``ts``,
#: never by "today" and never by mutating the global row. Shape: model ->
#: (cutoff_iso_date, row_through_cutoff_inclusive, row_after).
#: EMPTY since the PLAN-169 S338 follow-up: the Sonnet 5 row ($2/$10 per
#: MTok intro through 2026-08-31, then $3/$15) was retired when the official
#: pricing page (fetched 2026-09-01) made $2/$10 the standard price and
#: cancelled the 2026-09-01 increase — both legs equal the base row. The
#: MECHANISM (the ``ts`` branch of ``compute_cost_usd``) stays;
#: test_model_fleet_presence.py exercises it through a synthetic row.
_DATED_PRICING: Dict[str, Tuple[str, Dict[str, float], Dict[str, float]]] = {}


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


#: Resolved once at import; None ⇒ degraded (but never crashing) mode.
_NORMALIZE_MODEL_NAME = None  # initialized after binding


# ---------------------------------------------------------------------------
# Rollup
# ---------------------------------------------------------------------------


#: Audit actions that contribute tokens to the rollup.
_TOKEN_BEARING_ACTIONS: Tuple[str, ...] = (
    "agent_spawn",        # Claude sub-agent dispatches
    "pair_rail_case",     # Codex MCP cross-LLM gate (post-wire)
    "pair_rail_promotion",  # Phase 4 promotion gate runs
)


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


#: Usage keys summed per transcript (probe §handoff item 4). Cache columns
#: are reported token-only — no cache pricing row exists in the registry
#: and we never invent one.
_NATIVE_USAGE_KEYS: Tuple[str, ...] = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


#: ADR-149 Amendment 2 (S338, codex rail r1 P2): the cache-read multiplier
#: is PER MODEL. The pricing page (fetched 2026-09-01) prices cache hits on
#: Claude Fable 5.1 / Mythos 5.1 at 0.025x the base input price
#: ($0.25/MTok). A flat 0.10x would OVERSTATE Fable 5.1 cache reads 4x.
#: ADR-149 Amendment 3 (S357): Claude Opus 5.5 cache hits are 0.05x its $4
#: base ($0.20/MTok, pricing page fetched 2026-09-22) — a flat 0.10x would
#: overstate them 2x. Every other model of the ADR-149 working set keeps
#: the standard 0.10x; Mythos 5.1 (0.025x on the same page) is outside
#: the working set and carries no entry. Keys are canonical ids.
#: ceo-cost-transcripts.py mirrors this table exactly;
#: test_model_fleet_presence.py binds the two.
_CACHE_READ_MULTIPLIER_DEFAULT: float = 0.10
_CACHE_READ_MULTIPLIER_OVERRIDES: Dict[str, float] = {
    "claude-fable-5-1": 0.025,
    "claude-opus-5-5": 0.05,
}


# ---------------------------------------------------------------------------
# PLAN-186 W0 (AC-1b) — transcripts as the PRIMARY cost source
# ---------------------------------------------------------------------------
#
# The audit log is a GOVERNANCE ledger (agent_spawn rows; tokens_in/out on
# them are best-effort and frequently absent). The real token ledger is the
# harness-native transcript corpus — `message.usage` per assistant turn —
# which `.claude/scripts/ceo-cost-transcripts.py` reads with the full
# input / output / cache-read / cache-write-5m / cache-write-1h split and
# per-model prices. This module consumes that instrument through its
# programmatic API and prints BOTH sources, labelled, side by side.
# `--source audit` restores the pre-PLAN-186 rendering byte-for-byte.
#
# SCOPE NOTE (deliberate, not an oversight): this repo carries THREE
# independent pricing tables — `ceo-cost.py::_DEFAULT_PRICING`, the model
# registry behind `budget-summary.py::compute_cost_usd`, and the
# instrument's `_EMBEDDED_PRICING` / `cost-table.yaml` loader. Unifying them
# is a separate wave. This integration only REUSES what the instrument
# already exposes: the transcripts block is priced by the instrument, the
# audit block by whatever priced it before, and each block says so.
#
# The loader below is the one thing that cannot live in the instrument: its
# filename is hyphenated, so every caller needs its own importlib bootstrap.
# Everything else (root resolution, collection, rendering) is delegated, so
# the two callers cannot drift apart.

_TRANSCRIPTS_MODULE_NAME = "ceo_cost_transcripts"
_TRANSCRIPTS_FILENAME = "ceo-cost-transcripts.py"


#: Resolved ONCE, from the instrument, so the two callers cannot publish a
#: different `--source` domain or a different banner than the block they
#: render. The literals are a fail-soft fallback for a missing instrument
#: (argparse needs a concrete tuple at parser-build time) and are asserted
#: equal to the instrument's in test_ceo_cost_integration.py.
_TX_MODULE = None  # initialized after binding
SOURCE_CHOICES = (
    _TX_MODULE.SOURCE_CHOICES
    if _TX_MODULE is not None
    else ("transcripts", "audit", "both")
)
AUDIT_BANNER = (
    _TX_MODULE.AUDIT_BANNER
    if _TX_MODULE is not None
    else "=== SOURCE: AUDIT LOG (governance ledger -- SECONDARY) ==="
)
ROOT_ENV = (
    _TX_MODULE.ROOT_ENV
    if _TX_MODULE is not None
    else "CEO_COST_TRANSCRIPTS_DIR"
)


#: The audit-path env carriers THIS caller actually obeys.
#: `default_audit_dir()` reads CEO_AUDIT_LOG_DIR and nothing else, so
#: CEO_AUDIT_LOG_PATH does not move budget-summary's ledger and must not
#: be read as a cross-project pin (rail S341 r1 [P2]; measured: audit_dir
#: byte-identical with and without that var). ceo-cost.py honours both
#: carriers and passes none.
_AUDIT_ENV_CARRIERS = ("CEO_AUDIT_LOG_DIR",)


# Rebind extracted functions to this facade's globals: calls between functions
# and dynamically monkeypatched names retain the original module semantics.
from types import FunctionType as _FunctionType
from _lib._budget_summary_parts import (
    audit_events as _audit_events,
    cost_rollup as _cost_rollup,
    benchmark_native as _benchmark_native,
    native_reconciliation as _native_reconciliation,
    presentation_cli as _presentation_cli,
    native_formatting as _native_formatting,
)

for _part in (
    _audit_events, _cost_rollup, _benchmark_native,
    _native_reconciliation, _presentation_cli, _native_formatting,
):
    for _name, _obj in vars(_part).items():
        if isinstance(_obj, _FunctionType) and _obj.__module__ == _part.__name__:
            _bound = _FunctionType(
                _obj.__code__, globals(), _obj.__name__, _obj.__defaults__,
                _obj.__closure__,
            )
            _bound.__kwdefaults__ = _obj.__kwdefaults__
            _bound.__annotations__ = _obj.__annotations__
            _bound.__dict__.update(_obj.__dict__)
            _bound.__qualname__ = _obj.__qualname__
            _bound.__module__ = __name__
            globals()[_name] = _bound

del _part, _name, _obj, _bound
_NORMALIZE_MODEL_NAME = _load_normalize_model_name()
_TX_MODULE = load_transcripts_instrument()
SOURCE_CHOICES = _TX_MODULE.SOURCE_CHOICES if _TX_MODULE is not None else ("transcripts", "audit", "both")
AUDIT_BANNER = _TX_MODULE.AUDIT_BANNER if _TX_MODULE is not None else "=== SOURCE: AUDIT LOG (governance ledger -- SECONDARY) ==="
ROOT_ENV = _TX_MODULE.ROOT_ENV if _TX_MODULE is not None else "CEO_COST_TRANSCRIPTS_DIR"

if __name__ == "__main__":
    sys.exit(main())
