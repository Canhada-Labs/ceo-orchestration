#!/usr/bin/env python3
"""GOAP A* advisory-only planner (PLAN-098 Wave A.1 / ADR-132).

Plain-English goal -> A* state-space search -> action tree markdown.
NEVER auto-dispatches: output is advisory; Owner must confirm each action
explicitly per the ADR-051 non-delegation invariant + ADR-132 doctrine.

## Design

- **Stdlib only** (heapq, dataclasses, json, hashlib, time, os, sys, re,
  pathlib, typing). AC1 verified by check-stdlib-only.py AST scan.
- **A* tree-search** with frozenset closed-set on state_hash; cycle
  detection via closed-set + edge audit emit (AC2, AC12).
- **Admissible heuristic**: h(s) = sum of (action.tokens_k + 50 *
  action.gpg_events) for the minimum-spanning subset of unsatisfied
  goal predicates. Admissibility: each remaining goal predicate has an
  irreducible action; sum across distinct actions cannot exceed actual
  optimal cost. Property-tested at AC8 (>=200 random pairs).
- **Action library**: loaded from action-cost-baseline.json. Each entry
  is an Action(id, pre, eff, tokens_k, gpg_events, wall_clock_s).
- **Search bounds**: MAX_PLAN_DEPTH=12 / MAX_PLAN_NODES=100 / wall-clock
  5s hard / 2s soft. AC11 latency target p99 <= 800ms cold / 200ms warm.
- **Audit emit**: every explored edge fires goap_edge_explored with
  1-in-N sampling (N=10) when frontier > 50; terminus aggregate fires
  goap_search_summary (AC2).
- **Default posture (E8-F4)**: the planner is **default-ON but
  ADVISORY-ONLY**. `CEO_GOAP_ADVISORY_ENABLED` absent (the default) ==
  enabled, and the C2 sidecar manifest's `explicit_opt_in_required: false`
  reflects this. "ON" here means the planner will *produce advisory output*;
  it NEVER auto-dispatches or executes any action — the Owner must confirm
  each action explicitly (ADR-051 non-delegation invariant + ADR-132).
  This default-ON-but-advisory posture is safe by construction: there is no
  execution path to gate.
- **Kill-switch**: CEO_GOAP_ADVISORY_ENABLED=0 short-circuits the entry
  point with goap_disabled_by_env emit + exit-0 (AC10).
- **Replan**: replan_from(current_state) re-runs A* from a failure
  state; emits goap_replan_triggered; cap MAX_REPLAN_ATTEMPTS=3 ->
  goap_replan_exhausted (AC7).

The planner is callable as a library AND as a CLI for /goap.

## Output contract (CLI)

    $ python3 .claude/scripts/goap-planner.py --goal "ship v1.32.0"
    {"status": "ok", "tree_markdown": "...", "plan_depth": 5, ...}

Or `--format markdown` returns the action tree directly.

Stdlib-only. Python 3.9+ runtime supported.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Constants (AC11, AC4, AC7)
# ---------------------------------------------------------------------------

MAX_PLAN_DEPTH: int = 12
MAX_PLAN_NODES: int = 100
MAX_TREE_SIZE: int = 50
MAX_REPLAN_ATTEMPTS: int = 3
WALL_CLOCK_HARD_S: float = 5.0
WALL_CLOCK_SOFT_S: float = 2.0
AUDIT_SAMPLING_N: int = 10
AUDIT_SAMPLING_FRONTIER_THRESHOLD: int = 50
MAX_GOAL_CHARS: int = 500

_KILL_SWITCH_ENV: str = "CEO_GOAP_ADVISORY_ENABLED"

# Repo-relative path to the cost baseline.
_COST_BASELINE_RELPATH = Path(".claude") / "data" / "goap" / "action-cost-baseline.json"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Action:
    """A single action in the GOAP library.

    Pre/effects are frozensets of predicate strings "key=value".
    Effect "!key" deletes the predicate whose key matches.
    """
    id: str
    pre: FrozenSet[str]
    eff: FrozenSet[str]
    tokens_k: int
    gpg_events: int
    wall_clock_s: int


@dataclass(frozen=True)
class State:
    """Immutable world state — a frozenset of predicate strings.

    state_hash() is stable across Python runs (sha256 over sorted preds).
    """
    predicates: FrozenSet[str]

    def state_hash(self) -> str:
        joined = "\n".join(sorted(self.predicates))
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


@dataclass
class SearchResult:
    """Outcome of an A* search."""
    status: str
    plan: List[Action] = field(default_factory=list)
    explored: int = 0
    cycles_rejected: int = 0
    elapsed_ms: int = 0
    terminus_reason: str = ""


# ---------------------------------------------------------------------------
# Audit emit shim (hasattr-guarded — works pre-canonical-ceremony)
# ---------------------------------------------------------------------------

def _audit_emit(action: str, **fields: Any) -> None:
    """Emit a goap_* audit event via _lib.audit_emit.

    hasattr-guarded so the planner runs in adopter installs that haven't
    applied the PLAN-098 kernel-override ceremony yet. Sec MF-3 caller
    fields whitelisted at the emit_* boundary.
    """
    try:
        here = Path(__file__).resolve()
        cand = here.parent
        while cand != cand.parent:
            if (cand / ".claude" / "hooks" / "_lib").is_dir():
                hooks_path = str(cand / ".claude" / "hooks")
                if hooks_path not in sys.path:
                    sys.path.insert(0, hooks_path)
                break
            cand = cand.parent
        from _lib import audit_emit as _ae  # type: ignore
    except Exception:
        return
    fn = getattr(_ae, f"emit_{action}", None)
    if fn is None or not callable(fn):
        return
    try:
        fn(**fields)
    except Exception:
        return


def _kill_switch_engaged(env: Optional[Dict[str, str]] = None) -> bool:
    src = env if env is not None else os.environ
    return (src.get(_KILL_SWITCH_ENV, "1") or "").strip() == "0"


# ---------------------------------------------------------------------------
# Action library loader (AC14)
# ---------------------------------------------------------------------------

def _repo_root_from_here() -> Path:
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root and Path(env_root).is_dir():
        return Path(env_root)
    here = Path(__file__).resolve()
    cand = here.parent
    while cand != cand.parent:
        if (cand / ".claude").is_dir():
            return cand
        cand = cand.parent
    return Path.cwd()


def load_action_library(
    cost_path: Optional[Path] = None,
) -> Tuple[List[Action], Dict[str, Any]]:
    """Load the action library + cost baseline from disk.

    The baseline JSON maps action_id -> {tokens_k, gpg_events,
    wall_clock_s}. Pre/effects are doctrinal (this module's _ACTION_SCHEMA).
    """
    if cost_path is None:
        cost_path = _repo_root_from_here() / _COST_BASELINE_RELPATH
    with cost_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    costs = raw.get("actions", {})
    actions: List[Action] = []
    for action_id, schema in _ACTION_SCHEMA.items():
        entry = costs.get(action_id, {})
        actions.append(
            Action(
                id=action_id,
                pre=frozenset(schema["pre"]),
                eff=frozenset(schema["eff"]),
                tokens_k=int(entry.get("tokens_k", schema.get("tokens_k_default", 50))),
                gpg_events=int(entry.get("gpg_events", schema.get("gpg_default", 0))),
                wall_clock_s=int(entry.get("wall_clock_s", schema.get("wall_clock_s_default", 60))),
            )
        )
    return actions, raw


# Doctrinal action schema — pre/effects are fixed by ADR-132; costs come
# from the baseline JSON (rebaselined quarterly per AC14).
_ACTION_SCHEMA: Dict[str, Dict[str, Any]] = {
    "spawn_general": {
        "pre": ("plan_status=executing",),
        "eff": ("research_complete=true",),
        "tokens_k_default": 25,
    },
    "spawn_specialist": {
        "pre": ("plan_status=executing", "research_complete=true"),
        "eff": ("specialist_review=passed",),
        "tokens_k_default": 80,
    },
    "spawn_code_reviewer": {
        "pre": ("plan_status=executing",),
        "eff": ("code_review=passed",),
        "tokens_k_default": 60,
    },
    "spawn_security_engineer": {
        "pre": ("plan_status=executing",),
        "eff": ("security_review=passed",),
        "tokens_k_default": 70,
    },
    "spawn_qa_architect": {
        "pre": ("plan_status=executing",),
        "eff": ("qa_review=passed",),
        "tokens_k_default": 65,
    },
    "debate_round_1": {
        "pre": ("plan_status=draft",),
        "eff": ("debate_r1=accepted",),
        "tokens_k_default": 200,
    },
    "debate_round_2_codex": {
        "pre": ("debate_r1=accepted",),
        "eff": ("debate_r2=accepted", "plan_status=reviewed"),
        "tokens_k_default": 350,
    },
    "plan_flip_draft_to_reviewed": {
        "pre": ("debate_r2=accepted",),
        "eff": ("plan_status=reviewed",),
        "tokens_k_default": 5,
        "gpg_default": 0,
    },
    "plan_flip_reviewed_to_executing": {
        "pre": ("plan_status=reviewed",),
        "eff": ("plan_status=executing",),
        "tokens_k_default": 5,
        "gpg_default": 1,
    },
    "plan_flip_executing_to_done": {
        "pre": ("plan_status=executing", "code_review=passed"),
        "eff": ("plan_status=done",),
        "tokens_k_default": 5,
        "gpg_default": 1,
    },
    "adr_propose": {
        "pre": ("plan_status=executing",),
        "eff": ("adr_status=proposed",),
        "tokens_k_default": 30,
    },
    "adr_promote_to_accepted": {
        "pre": ("adr_status=proposed",),
        "eff": ("adr_status=accepted",),
        "tokens_k_default": 10,
        "gpg_default": 1,
    },
    "closeout_session": {
        "pre": ("plan_status=done",),
        "eff": ("session_closed=true",),
        "tokens_k_default": 50,
    },
    "tag_release": {
        "pre": ("plan_status=done", "code_review=passed"),
        "eff": ("tagged=true",),
        "tokens_k_default": 5,
        "gpg_default": 2,
    },
    "owner_ceremony_apply_patches": {
        "pre": ("plan_status=executing",),
        "eff": ("patches_applied=true",),
        "tokens_k_default": 10,
        "gpg_default": 1,
    },
}


# ---------------------------------------------------------------------------
# State transition + applicability
# ---------------------------------------------------------------------------

def _apply_action(state: State, action: Action) -> State:
    preds = set(state.predicates)
    for effect in action.eff:
        if effect.startswith("!"):
            target_key = effect[1:].split("=", 1)[0]
            preds = {p for p in preds if p.split("=", 1)[0] != target_key}
            continue
        if "=" in effect:
            key = effect.split("=", 1)[0]
            preds = {p for p in preds if p.split("=", 1)[0] != key}
        preds.add(effect)
    return State(predicates=frozenset(preds))


def _action_applicable(state: State, action: Action) -> bool:
    return action.pre <= state.predicates


# ---------------------------------------------------------------------------
# Heuristic (AC8 admissibility property)
# ---------------------------------------------------------------------------

def _action_cost(action: Action) -> int:
    """Single-edge cost — tokens + GPG-event-weight.

    GPG events weight at 50k tokens each (irreducible Owner physical
    bottleneck dominates token spend).
    """
    return int(action.tokens_k) + 50 * int(action.gpg_events)


def heuristic(state: State, goal: FrozenSet[str], actions: Sequence[Action]) -> int:
    """Admissible heuristic — sum of minimum costs across unsatisfied goal predicates.

    For each goal predicate not yet in state, find the cheapest action
    whose effects produce it; sum across distinct cheapest actions
    (deduplicated). Admissible: actual optimal cost >= sum of irreducible
    action costs (each unsatisfied predicate needs >= one producer).
    """
    unsatisfied = goal - state.predicates
    if not unsatisfied:
        return 0
    cheapest_per_goal: Dict[str, Action] = {}
    for g in unsatisfied:
        candidates = [a for a in actions if g in a.eff]
        if not candidates:
            return 0
        cheapest_per_goal[g] = min(candidates, key=_action_cost)
    distinct_actions = {a.id: a for a in cheapest_per_goal.values()}
    return sum(_action_cost(a) for a in distinct_actions.values())


# ---------------------------------------------------------------------------
# A* search (AC1, AC2, AC11, AC12)
# ---------------------------------------------------------------------------

def search(
    start: State,
    goal: FrozenSet[str],
    actions: Sequence[Action],
    *,
    max_depth: int = MAX_PLAN_DEPTH,
    max_nodes: int = MAX_PLAN_NODES,
    wall_clock_s: float = WALL_CLOCK_HARD_S,
    audit_session: str = "",
) -> SearchResult:
    """A* search from `start` toward `goal`."""
    started = time.monotonic()
    counter = 0

    initial_h = heuristic(start, goal, actions)
    open_heap: List[Tuple[int, int, int, State, List[Action]]] = []
    heapq.heappush(open_heap, (initial_h, 0, counter, start, []))
    closed: Dict[str, int] = {}
    explored = 0
    cycles_rejected = 0
    depth_cap_hit = False

    while open_heap:
        if (time.monotonic() - started) > wall_clock_s:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            _audit_emit("goap_search_aborted", reason="wall_clock_exceeded",
                        explored=explored, elapsed_ms=elapsed_ms, session_id=audit_session)
            _audit_emit("goap_search_summary", explored=explored,
                        cycles_rejected=cycles_rejected, terminus="timeout",
                        elapsed_ms=elapsed_ms, session_id=audit_session)
            return SearchResult(status="timeout", explored=explored,
                                cycles_rejected=cycles_rejected, elapsed_ms=elapsed_ms,
                                terminus_reason="wall_clock_exceeded")

        if explored >= max_nodes:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            _audit_emit("goap_search_aborted", reason="node_cap_exceeded",
                        explored=explored, elapsed_ms=elapsed_ms, session_id=audit_session)
            _audit_emit("goap_search_summary", explored=explored,
                        cycles_rejected=cycles_rejected, terminus="node_cap",
                        elapsed_ms=elapsed_ms, session_id=audit_session)
            return SearchResult(status="node_cap", explored=explored,
                                cycles_rejected=cycles_rejected, elapsed_ms=elapsed_ms,
                                terminus_reason="node_cap_exceeded")

        f, g, _, state, path = heapq.heappop(open_heap)
        sh = state.state_hash()

        prior = closed.get(sh)
        if prior is not None and prior <= g:
            cycles_rejected += 1
            _audit_emit("goap_cycle_detected", state_hash=sh, explored=explored,
                        session_id=audit_session)
            continue
        closed[sh] = g

        if goal <= state.predicates:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            _audit_emit("goap_search_summary", explored=explored,
                        cycles_rejected=cycles_rejected, terminus="ok",
                        elapsed_ms=elapsed_ms, plan_depth=len(path),
                        session_id=audit_session)
            return SearchResult(status="ok", plan=path, explored=explored,
                                cycles_rejected=cycles_rejected, elapsed_ms=elapsed_ms,
                                terminus_reason="goal_satisfied")

        if len(path) >= max_depth:
            depth_cap_hit = True
            _audit_emit("goap_depth_exceeded", state_hash=sh, depth=len(path),
                        session_id=audit_session)
            continue

        explored += 1
        emit_this_edge = (
            len(open_heap) <= AUDIT_SAMPLING_FRONTIER_THRESHOLD
            or (explored % AUDIT_SAMPLING_N) == 0
        )

        for action in actions:
            if not _action_applicable(state, action):
                continue
            new_state = _apply_action(state, action)
            new_sh = new_state.state_hash()
            if goal <= new_state.predicates or new_sh not in closed:
                cost = _action_cost(action)
                new_g = g + cost
                new_h = heuristic(new_state, goal, actions)
                new_f = new_g + new_h
                counter += 1
                heapq.heappush(open_heap, (new_f, new_g, counter, new_state, path + [action]))
                if emit_this_edge:
                    _audit_emit("goap_edge_explored", from_state_hash=sh,
                                action_id=action.id, cost=cost,
                                frontier_size=len(open_heap),
                                session_id=audit_session)
            else:
                cycles_rejected += 1
                _audit_emit("goap_cycle_detected", state_hash=new_sh,
                            explored=explored, session_id=audit_session)

    elapsed_ms = int((time.monotonic() - started) * 1000)
    terminus = "depth_exceeded" if depth_cap_hit else "no_plan"
    _audit_emit("goap_search_summary", explored=explored,
                cycles_rejected=cycles_rejected, terminus=terminus,
                elapsed_ms=elapsed_ms, session_id=audit_session)
    return SearchResult(status=terminus, explored=explored,
                        cycles_rejected=cycles_rejected, elapsed_ms=elapsed_ms,
                        terminus_reason="frontier_exhausted" if terminus == "no_plan" else "depth_cap_hit")


# ---------------------------------------------------------------------------
# Replan (AC7)
# ---------------------------------------------------------------------------

def replan_from(
    current: State,
    goal: FrozenSet[str],
    actions: Sequence[Action],
    *,
    attempt: int = 1,
    audit_session: str = "",
    plan_id: Optional[str] = None,  # PLAN-105 Wave A.4 — per-plan replan denominator
) -> SearchResult:
    """Re-run A* from a failure state.

    PLAN-105 Wave A.4: optional `plan_id` keyword param propagates to the
    emit_goap_replan_triggered + _exhausted events for per-plan replan
    denominator. Backward-compatible: when omitted, behavior is byte-
    identical to v1.31.0.
    """
    _replan_kwargs = {"session_id": audit_session}
    if plan_id is not None:
        _replan_kwargs["plan_id"] = str(plan_id)[:32]
    if attempt > MAX_REPLAN_ATTEMPTS:
        _audit_emit("goap_replan_exhausted", attempt=attempt, **_replan_kwargs)
        return SearchResult(status="no_plan", terminus_reason="replan_exhausted")
    _audit_emit("goap_replan_triggered", attempt=attempt,
                state_hash=current.state_hash(), **_replan_kwargs)
    return search(current, goal, actions, audit_session=audit_session)


# ---------------------------------------------------------------------------
# Goal parser (AC3, AC13)
# ---------------------------------------------------------------------------

# Deterministic rule-based parser. AC13 declares "uses existing claude.py
# adapter with effort: low; output tokens capped 4096; failures fall
# through to goal-parse-failed advisory return". The framework has no
# wired LLM client in steady state (Tier-A §6b criterion 2 "no token
# spend in steady state"); the parser path below is the deterministic
# fall-through. An LLM extension point can wire to a future LLM adapter
# without changing the public parse_goal() contract.

_GOAL_VERBS: Dict[str, FrozenSet[str]] = {
    "ship": frozenset({"plan_status=done", "tagged=true"}),
    "release": frozenset({"plan_status=done", "tagged=true"}),
    "tag": frozenset({"tagged=true"}),
    "promote": frozenset({"adr_status=accepted"}),
    "execute": frozenset({"plan_status=executing"}),
    "review": frozenset({"plan_status=reviewed"}),
    "close": frozenset({"plan_status=done"}),
    "closeout": frozenset({"session_closed=true"}),
}


def parse_goal(text: str) -> Tuple[FrozenSet[str], str]:
    """Plain-English goal text -> goal predicates + parse status."""
    if not text:
        return frozenset(), "goal-parse-failed"
    if len(text) > MAX_GOAL_CHARS:
        return frozenset(), "goal-too-long"
    lowered = text.strip().lower()
    for verb, preds in _GOAL_VERBS.items():
        if re.search(rf"\b{re.escape(verb)}\b", lowered):
            return preds, "ok"
    return frozenset(), "goal-parse-failed"


# ---------------------------------------------------------------------------
# Tree visualization (AC3, AC4)
# ---------------------------------------------------------------------------

def render_tree_markdown(
    goal_text: str,
    goal: FrozenSet[str],
    plan: Sequence[Action],
    result: SearchResult,
    *,
    advisory_banner: bool = True,
) -> str:
    """Render an action tree as markdown for /goap output.

    Includes pre-conditions + effects per node + path cost annotations.
    Capped at MAX_TREE_SIZE nodes (UX cap).
    """
    lines: List[str] = []
    if advisory_banner:
        lines.append("> **ADVISORY ONLY** — Owner must confirm each action before /architect dispatches.")
        lines.append("> See ADR-132 §Decision + ADR-051 non-delegation invariant.")
        lines.append("")
    lines.append(f"# GOAP plan — `{goal_text[:MAX_GOAL_CHARS]}`")
    lines.append("")
    lines.append(f"- **Status**: `{result.status}`")
    lines.append(f"- **Plan depth**: {len(plan)} action(s)")
    lines.append(f"- **Explored**: {result.explored} node(s)")
    lines.append(f"- **Cycles rejected**: {result.cycles_rejected}")
    lines.append(f"- **Elapsed**: {result.elapsed_ms} ms")
    if result.terminus_reason:
        lines.append(f"- **Terminus**: `{result.terminus_reason}`")
    lines.append("")
    if not plan:
        lines.append("_No actionable plan found._")
        return "\n".join(lines)
    lines.append("## Goal predicates")
    for p in sorted(goal):
        lines.append(f"- `{p}`")
    lines.append("")
    lines.append("## Action path")
    cumulative_cost = 0
    nodes_rendered = 0
    for i, action in enumerate(plan, 1):
        if nodes_rendered >= MAX_TREE_SIZE:
            lines.append(f"_(truncated at {MAX_TREE_SIZE} nodes — depth cap)_")
            break
        cost = _action_cost(action)
        cumulative_cost += cost
        lines.append(f"### {i}. `{action.id}` — cost +{cost}k (cumulative {cumulative_cost}k)")
        lines.append("")
        lines.append("- **Pre-conditions**: " + (
            ", ".join(f"`{p}`" for p in sorted(action.pre)) or "_(none)_"
        ))
        lines.append("- **Effects**: " + (
            ", ".join(f"`{e}`" for e in sorted(action.eff)) or "_(none)_"
        ))
        lines.append(
            f"- **Tokens (k)**: {action.tokens_k}  **GPG events**: {action.gpg_events}  "
            f"**Wall-clock (s)**: {action.wall_clock_s}"
        )
        lines.append("")
        nodes_rendered += 1
    lines.append("## Replan-on-failure")
    lines.append("")
    lines.append(
        f"If any action fails (non-zero exit OR audit `*_failed`), the planner re-runs A* "
        f"from the current state (not restart from goal). Cap: {MAX_REPLAN_ATTEMPTS} attempts."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# PLAN-105 Wave A.5 — Rendered-event helper (in-process emit)
# ---------------------------------------------------------------------------

import hashlib as _hashlib
import unicodedata as _unicodedata


_PLAN_ID_HINT_RE = re.compile(r"\bPLAN-(\d{3})(?:-[A-Za-z0-9-]+)?\b")


def _extract_plan_id_hint(goal_text: str) -> str:
    """Extract PLAN-NNN hint from goal text; return sentinel NO_PLAN_HINT if absent."""
    m = _PLAN_ID_HINT_RE.search(goal_text or "")
    if m:
        return f"PLAN-{m.group(1)}"
    return "NO_PLAN_HINT"


def _extract_goal_verb(goal_text: str) -> str:
    """Match goal text against canonical _GOAL_VERBS; return verb or empty string."""
    lowered = (goal_text or "").strip().lower()
    for verb in _GOAL_VERBS.keys():
        if re.search(rf"\b{re.escape(verb)}\b", lowered):
            return verb
    return ""


def _emit_rendered_event(goal_text: str, plan: Sequence[Action], audit_session: str) -> None:
    """Emit goap_recommendation_rendered via audit_emit (PLAN-105 A.5).

    Goal text body NEVER persisted — only sha256(NFKC(goal_text))[:12]
    (LLM06 side-channel guard; PLAN-105 R2 P0 fold).
    """
    plan_id_hint = _extract_plan_id_hint(goal_text)
    action_ids = [a.id for a in plan][:50]
    action_ids_csv = ",".join(action_ids)
    actions_rendered_count = len(action_ids)
    goal_verb = _extract_goal_verb(goal_text)
    # PLAN-105 R2 P0 #1 fold — NFKC normalize before sha256 per spec.
    normalized = _unicodedata.normalize("NFKC", goal_text or "")
    goal_text_hash = _hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    _audit_emit(
        "goap_recommendation_rendered",
        plan_id=plan_id_hint,
        action_ids_csv=action_ids_csv,
        actions_rendered_count=actions_rendered_count,
        goal_verb=goal_verb,
        goal_text_hash=goal_text_hash,
        session_id=audit_session,
    )


# ---------------------------------------------------------------------------
# Top-level entry point (AC3, AC10)
# ---------------------------------------------------------------------------

def plan_for_goal(
    goal_text: str,
    start: Optional[State] = None,
    *,
    audit_session: str = "",
) -> Dict[str, Any]:
    """Top-level entry — parse goal, load actions, search, render."""
    if _kill_switch_engaged():
        _audit_emit("goap_disabled_by_env", session_id=audit_session)
        return {
            "status": "disabled",
            "tree_markdown": "> GOAP advisory planner is disabled via `CEO_GOAP_ADVISORY_ENABLED=0`.",
            "plan_depth": 0,
            "explored": 0,
        }
    goal, parse_status = parse_goal(goal_text)
    if parse_status != "ok":
        return {
            "status": parse_status,
            "tree_markdown": (
                f"> Goal parse failed (`{parse_status}`) — could not extract goal "
                f"predicates from input. Try one of: ship / promote / execute / "
                f"review / closeout / tag."
            ),
            "plan_depth": 0,
            "explored": 0,
        }
    actions, _baseline = load_action_library()
    if start is None:
        start = State(predicates=frozenset({"plan_status=draft"}))
    result = search(start, goal, actions, audit_session=audit_session)
    tree = render_tree_markdown(goal_text, goal, result.plan, result)
    # PLAN-105 Wave A.5 — emit goap_recommendation_rendered when plan
    # rendered successfully (non-empty plan). Hash-only goal text (LLM06).
    if result.plan:
        _emit_rendered_event(goal_text, result.plan, audit_session)
    return {
        "status": result.status,
        "tree_markdown": tree,
        "plan_depth": len(result.plan),
        "explored": result.explored,
        "cycles_rejected": result.cycles_rejected,
        "elapsed_ms": result.elapsed_ms,
        "terminus_reason": result.terminus_reason,
    }


# ---------------------------------------------------------------------------
# CLI (AC3)
# ---------------------------------------------------------------------------

def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="goap-planner",
        description="PLAN-098 GOAP A* advisory-only planner. Output is ADVISORY — Owner must confirm.",
    )
    p.add_argument("--goal", type=str, required=True, help="Plain-English goal text (<=500 chars).")
    p.add_argument("--format", choices=("json", "markdown"), default="json",
                   help="Output format. Default: json digest with embedded tree_markdown.")
    p.add_argument("--session-id", default="", help="Session correlation ID for audit emit.")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    digest = plan_for_goal(args.goal, audit_session=args.session_id)
    if args.format == "markdown":
        sys.stdout.write(digest.get("tree_markdown", ""))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(json.dumps(digest, separators=(",", ":"), ensure_ascii=False))
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
