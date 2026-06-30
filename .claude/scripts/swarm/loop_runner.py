"""PLAN-017 Phase 1 — individual-loop runner wrapper.

Scaffold. A ``LoopRunner`` represents a single autonomous-optimization
loop: accepts a goal + benchmark command + budget, iterates
(try→measure→keep/revert), emits ``LoopState`` snapshots the coordinator
consumes.

The actual benchmark subprocess invocation + worktree checkout +
replay-session integration are deferred to PLAN-017 follow-up
sprints — they require ADR-049a isolation decision + policy-engine
wiring. This scaffold captures the control-flow contract so tests can
exercise the invariants without depending on a real benchmark.
"""

from __future__ import annotations

import os as _os_top
from dataclasses import dataclass, field
from pathlib import Path as _Path
from typing import Callable, List, Optional

from .coordinator import LoopState


# Metric-direction enum. Extended if needed; keep as plain strings
# (no Enum) to stay consistent with stdlib dataclass serialization.
DIRECTION_MINIMIZE = "minimize"
DIRECTION_MAXIMIZE = "maximize"
_VALID_DIRECTIONS = {DIRECTION_MINIMIZE, DIRECTION_MAXIMIZE}


# ---------------------------------------------------------------------------
# PLAN-102-FOLLOWUP / ADR-133 §Part 1 §6 — Layer 3+4 gate wiring
# ---------------------------------------------------------------------------

import re as _re_plan102fu

# 6 internal gate reasons collapse to 4 emit reasons (security H1 fold
# from S144 R1 debate; full detail kept ONLY in IterationResult.error,
# never persisted to the audit log).
_EMIT_REASON_COLLAPSE = {
    "sentinel_absent": "layer_3_unavailable",
    "sentinel_bad_signature": "layer_3_unavailable",
    "stdlib_gpg_unavailable": "layer_3_unavailable",
    "env_flag_unset": "layer_4_unset",
    "env_flag_not_1": "layer_4_unset",
    "gate_disabled": "kill_switch",
}


def _collapse_reason_for_emit(reason: str) -> str:
    return _EMIT_REASON_COLLAPSE.get(reason, "unknown")


# LLM06 hygiene (Tier-C, Codex iter-4 P2-C): producer-boundary loop_id
# validation. Charset RE restricts to safe chars only; rejects path
# separators, shell metachars, quotes, whitespace, control bytes, and
# unicode. Length cap = 64. Invalid loop_id → fail-open drop (no emit;
# no exception) per ADR-010 fail-open doctrine.
_LOOP_ID_RE = _re_plan102fu.compile(r"^[A-Za-z0-9_-]+$")


def _emit_swarm_layer_3_4_blocked(
    *, class_tier: str, reason_code: str, loop_id: str,
) -> None:
    """Thin wrapper — kernel action `swarm_layer_3_4_blocked` registered
    in audit_emit.py via kernel-override (PLAN-102-FOLLOWUP Wave B).

    No public typed helper in audit_emit per S141 P1 #3 — emit_generic +
    Sec MF-3 scrub keeps `_EXPECTED_PUBLIC_SYMBOLS` stable (PLAN-101 /
    PLAN-102 / PLAN-106 precedent).

    LLM06 producer-boundary hygiene (Tier-C, Codex iter-4 P2-C):
    - reject empty loop_id
    - reject loop_id > 64 chars
    - reject loop_id not matching `^[A-Za-z0-9_-]+$`
    - invalid loop_id → fail-open drop (no emit; no exception) per ADR-010
    """
    if not loop_id or len(loop_id) > 64 or not _LOOP_ID_RE.match(loop_id):
        return  # fail-open drop per ADR-010
    try:
        from _lib import audit_emit  # type: ignore[import-not-found]
    except ImportError:
        return  # fail-open per PLAN-091-FOLLOWUP S116 doctrine
    try:
        audit_emit.emit_generic(  # type: ignore[attr-defined]
            "swarm_layer_3_4_blocked",
            class_tier=class_tier,
            reason_code=reason_code,
            loop_id=loop_id,
        )
    except Exception:
        # fail-open — never block step() on audit infra failure.
        return


# ---------------------------------------------------------------------------
# PLAN-113 Phase C R1 — B.4/B.5 circuit-breaker wiring
# ---------------------------------------------------------------------------
# The SwarmCircuitBreaker detectors (swarm_circuit_breaker.py) were implemented
# with tests but had zero production callers — FAIL-OPEN finding C2.  This
# block wires them into the only active dispatch path: _gate_step_check().
#
# Invariants:
#   (a) Default-OFF: when CEO_SWARM != "1" the check is never reached
#       (same early-return guard as Layer 3+4 gate above).
#   (b) Fail-CLOSED on breaker import/call error *within the gated path*:
#       deny the dispatch, breadcrumb to stderr. This is gated-dispatch
#       fail-closed — NOT the session-level hook (which stays fail-open
#       per PLAN-091-FOLLOWUP S116 doctrine).
#   (c) When breaker is disabled (CEO_EXECUTION_CONTEXT_HOOKS_DISABLE=1),
#       both detectors return False by design — gate is strict no-op.
#
# Audit actions emitted (registered in _KNOWN_ACTIONS via PLAN-102 Wave A):
#   swarm_runaway_suspected  — B.4 reverse-tripwire fires
#   swarm_paused_owner_absent — B.5 weekend-burn fires


def _resolve_breaker_audit_log_path() -> "_Path":
    """Mirror audit_emit._log_path() logic so breaker reads the live log.

    Env-overridable (CEO_AUDIT_LOG_PATH / CEO_AUDIT_LOG_DIR) for test
    isolation.  Stdlib only.
    """
    env_path = _os_top.environ.get("CEO_AUDIT_LOG_PATH")
    if env_path:
        return _Path(env_path)
    env_dir = _os_top.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return _Path(env_dir) / "audit-log.jsonl"
    # Default: matches audit_emit._audit_dir() → ~/.claude/projects/ceo-orchestration/
    home = _os_top.environ.get("HOME") or str(_Path.home())
    return _Path(home) / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"


def _emit_swarm_runaway_suspected(
    *, iteration_count_24h: int, threshold: int, triggering_class: str,
) -> None:
    """Emit `swarm_runaway_suspected` — B.4 reverse-tripwire audit action.

    Fields drawn strictly from _SWARM_RUNAWAY_SUSPECTED_ALLOWLIST:
    iteration_count_24h, threshold, triggering_class.
    Fail-open on any infra error (breadcrumb only).
    """
    try:
        from _lib import audit_emit  # type: ignore[import-not-found]
    except ImportError:
        return
    try:
        audit_emit.emit_generic(  # type: ignore[attr-defined]
            "swarm_runaway_suspected",
            iteration_count_24h=iteration_count_24h,
            threshold=threshold,
            triggering_class=triggering_class,
        )
    except Exception:
        return


def _emit_swarm_paused_owner_absent(
    *, loop_duration_hours: int, swarm_pid: int,
) -> None:
    """Emit `swarm_paused_owner_absent` — B.5 weekend-burn audit action.

    Fields drawn strictly from _SWARM_PAUSED_OWNER_ABSENT_ALLOWLIST:
    loop_duration_hours (bucketed to int hours, >=1h minimum to avoid
    wallclock side-channel per allowlist doctrine), swarm_pid.
    last_owner_read_iso omitted — breaker API returns bool only;
    the timestamp is private to the detector internals.
    Fail-open on any infra error (breadcrumb only).
    """
    try:
        from _lib import audit_emit  # type: ignore[import-not-found]
    except ImportError:
        return
    try:
        audit_emit.emit_generic(  # type: ignore[attr-defined]
            "swarm_paused_owner_absent",
            loop_duration_hours=max(1, loop_duration_hours),
            swarm_pid=swarm_pid,
        )
    except Exception:
        return


def _circuit_breaker_step_check(runner: "LoopRunner") -> "Optional[IterationResult]":
    """Check B.4/B.5 circuit breakers AFTER Layer 3+4 gate passes.

    Returns a synthetic gate-block IterationResult (status=killed) if
    either breaker fires. Returns None when both pass (no-op — caller
    continues normally).

    Fail-CLOSED contract (within the already-gated autonomous-loop path):
    if the circuit-breaker import fails OR raises unexpectedly, deny the
    dispatch conservatively and write a breadcrumb to stderr.  This is
    appropriate because we are already inside the Layer 3+4 entitlement
    boundary — a breaker infra error is suspicious, not routine.

    When CEO_EXECUTION_CONTEXT_HOOKS_DISABLE=1, both
    SwarmCircuitBreaker detectors return False by design, so this
    function becomes a strict no-op (passes through).
    """
    import sys as _sys
    audit_log = _resolve_breaker_audit_log_path()
    try:
        try:
            from .._lib.swarm_circuit_breaker import SwarmCircuitBreaker  # type: ignore
        except Exception:
            from _lib.swarm_circuit_breaker import SwarmCircuitBreaker  # type: ignore
    except Exception as exc:
        # Fail-CLOSED: breaker module unavailable inside the gated path.
        _sys.stderr.write(
            f"loop_runner._circuit_breaker_step_check: breaker import "
            f"failed ({type(exc).__name__}: {exc}); blocking dispatch "
            f"(fail-closed within gated path)\n"
        )
        runner.state.status = "killed"
        return IterationResult(
            metric=float("nan"),
            tokens_delta=0,
            kept=False,
            error="circuit_breaker_import_failed",
        )

    # B.4 reverse-tripwire — >1000 swarm_iteration events in 24h without
    # any session_start event in the same window.
    try:
        reverse_fires = SwarmCircuitBreaker.should_pause_reverse_tripwire(
            audit_log,
            threshold=1000,
            window_hours=24,
        )
    except Exception as exc:
        _sys.stderr.write(
            f"loop_runner._circuit_breaker_step_check: "
            f"should_pause_reverse_tripwire raised "
            f"{type(exc).__name__}: {exc}; blocking dispatch (fail-closed)\n"
        )
        runner.state.status = "killed"
        return IterationResult(
            metric=float("nan"),
            tokens_delta=0,
            kept=False,
            error="circuit_breaker_b4_error",
        )

    if reverse_fires:
        _emit_swarm_runaway_suspected(
            iteration_count_24h=1001,  # sentinel: known-exceeded (≥threshold+1)
            threshold=1000,
            triggering_class=runner.class_tier,
        )
        runner.state.status = "killed"
        return IterationResult(
            metric=float("nan"),
            tokens_delta=0,
            kept=False,
            error="circuit_breaker_b4_runaway",
        )

    # B.5 weekend-burn — swarm running >12h without a session_start event.
    try:
        weekend_fires = SwarmCircuitBreaker.should_pause_weekend_burn(
            audit_log,
            max_hours=12,
        )
    except Exception as exc:
        _sys.stderr.write(
            f"loop_runner._circuit_breaker_step_check: "
            f"should_pause_weekend_burn raised "
            f"{type(exc).__name__}: {exc}; blocking dispatch (fail-closed)\n"
        )
        runner.state.status = "killed"
        return IterationResult(
            metric=float("nan"),
            tokens_delta=0,
            kept=False,
            error="circuit_breaker_b5_error",
        )

    if weekend_fires:
        _emit_swarm_paused_owner_absent(
            loop_duration_hours=13,  # sentinel: known-exceeded (>max_hours)
            swarm_pid=_os_top.getpid(),
        )
        runner.state.status = "killed"
        return IterationResult(
            metric=float("nan"),
            tokens_delta=0,
            kept=False,
            error="circuit_breaker_b5_weekend_burn",
        )

    return None  # both breakers passed — allow dispatch


def _gate_step_check(runner: "LoopRunner") -> Optional["IterationResult"]:
    """Return synthetic gate-block IterationResult or None when gate allows.

    PLAN-102-FOLLOWUP S145 Codex triage thread 019e42fc Fix #1:
    Layer 3+4 gate ONLY enforces when Layer-1 swarm is actually ON
    (CEO_SWARM=1 AND CEO_AUTONOMOUS_LOOPS_DISABLE!=1). Outside autonomous-
    loop context (ordinary test/script callers of LoopRunner), early-
    return None preserves pre-existing iterate() behavior — prevents
    cross-contamination of pre-existing test_loop_runner.py tests that
    instantiate LoopRunner without the autonomous-loop env-frame.

    Imports `is_class_enabled` lazily so test stubs may monkeypatch the
    `swarm_enable_gate` module without import-time coupling. Fail-open on
    import error (PLAN-091-FOLLOWUP S116) — treat as ALLOW to preserve
    "never block session on audit infra" doctrine.

    PLAN-113 Phase C R1: after Layer 3+4 passes, circuit breaker check
    is invoked (_circuit_breaker_step_check). Fail-CLOSED within the
    gated path (breaker import failure → deny dispatch, breadcrumb).
    """
    import os
    if os.environ.get("CEO_SWARM") != "1":
        return None  # Not in autonomous-loop context → bypass gate (ADR-126)
    if os.environ.get("CEO_AUTONOMOUS_LOOPS_DISABLE") == "1":
        return None  # Layer-1 kill-switch → bypass gate (defense-in-depth)
    try:
        from .._lib.swarm_enable_gate import is_class_enabled  # type: ignore
    except Exception:
        try:
            # Alternate import path (when scripts/swarm is on sys.path directly).
            from _lib.swarm_enable_gate import is_class_enabled  # type: ignore
        except Exception:
            return None  # fail-open: gate primitive unavailable → allow
    try:
        enabled, reason = is_class_enabled(runner.class_tier)
    except Exception:
        return None  # fail-open per ADR-010
    if not enabled:
        emit_reason = _collapse_reason_for_emit(reason)
        _emit_swarm_layer_3_4_blocked(
            class_tier=runner.class_tier,
            reason_code=emit_reason,
            loop_id=runner.loop_id,
        )
        runner.state.status = "killed"   # existing enum value (coordinator.py:70)
        return IterationResult(
            metric=float("nan"),
            tokens_delta=0,
            kept=False,
            # Full detail in error (local to caller, NOT in audit emit).
            error=f"layer_3_4_{reason}",
        )
    # Layer 3+4 passed — now run circuit breaker (B.4 + B.5).
    # Fail-CLOSED within the gated path (breaker error → deny dispatch).
    return _circuit_breaker_step_check(runner)


@dataclass
class IterationResult:
    """Outcome of one loop iteration (try→measure→keep/revert)."""

    metric: float
    tokens_delta: int
    files_touched: List[str] = field(default_factory=list)
    kept: bool = False
    error: Optional[str] = None


@dataclass
class LoopRunner:
    """Wraps an in-progress loop.

    The ``iterate`` callable is injected at construction time — unit
    tests pass a deterministic stub. In a follow-up sprint this becomes
    the benchmark-subprocess invocation.
    """

    loop_id: str
    goal: str
    max_iterations: int
    max_strikes: int
    budget_tokens: int
    direction: str
    iterate: Callable[[LoopState], IterationResult]
    state: LoopState = field(init=False)
    best_metric: Optional[float] = None
    history: List[IterationResult] = field(default_factory=list)
    # PLAN-102-FOLLOWUP / ADR-133 §Part 1 §6 — Layer 3+4 gate input.
    # Default "vibecoder" matches PLAN-102 lowest-cost class; existing
    # instantiations work without code change (Codex iter-2 P1 fold).
    class_tier: str = "vibecoder"

    def __post_init__(self) -> None:
        if self.direction not in _VALID_DIRECTIONS:
            raise ValueError(
                f"direction must be one of {sorted(_VALID_DIRECTIONS)}; got {self.direction!r}"
            )
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        if self.max_strikes < 1:
            raise ValueError("max_strikes must be >= 1")
        if self.budget_tokens <= 0:
            raise ValueError("budget_tokens must be > 0")
        self.state = LoopState(loop_id=self.loop_id)

    def step(self) -> IterationResult:
        """Run one iteration + update state + return the result.

        Does NOT enforce budget / strike caps — that's the coordinator's
        job (matches the Design Principle #2 invariant: kill-switch
        layers are external, not embedded inside each loop).

        Raises RuntimeError if the loop is not in a runnable status.
        """

        if self.state.status != "running":
            raise RuntimeError(
                f"loop {self.loop_id!r} status is {self.state.status!r}; "
                "cannot step"
            )
        if self.state.iteration >= self.max_iterations:
            self.state.status = "completed"
            return IterationResult(
                metric=float("nan"),
                tokens_delta=0,
                kept=False,
                error="max_iterations_reached",
            )

        # PLAN-102-FOLLOWUP — Layer 3+4 enforcement (defense-in-depth).
        # Gate-block path: emit audit row, mark killed, append synthetic
        # IterationResult to history BEFORE early return (preserves the
        # `self.history.append(result)` invariant at L116 per Codex iter-3 P1).
        # Codex R2 iter-1 P2 #1 fold: removed inert
        # `try: from ._lib_gate import _gate_check_or_none` block — the
        # helper is defined at module scope below, no separate import.
        _gate_blocked = _gate_step_check(self)
        if _gate_blocked is not None:
            self.history.append(_gate_blocked)
            return _gate_blocked

        result = self.iterate(self.state)
        self.state.iteration += 1
        self.state.tokens_consumed += int(result.tokens_delta)
        if result.files_touched:
            # Preserve insertion order while deduplicating.
            seen = set(self.state.files_touched)
            for p in result.files_touched:
                if p not in seen:
                    self.state.files_touched.append(p)
                    seen.add(p)
        if result.error is not None:
            self.state.strikes += 1
            if self.state.strikes >= self.max_strikes:
                self.state.status = "errored"
        elif result.kept:
            self.state.kept_changes += 1
            self._maybe_update_best(result.metric)

        self.history.append(result)
        return result

    def _maybe_update_best(self, metric: float) -> None:
        if metric != metric:  # NaN
            return
        if self.best_metric is None:
            self.best_metric = metric
            return
        if self.direction == DIRECTION_MINIMIZE and metric < self.best_metric:
            self.best_metric = metric
        elif self.direction == DIRECTION_MAXIMIZE and metric > self.best_metric:
            self.best_metric = metric

    def mark_killed(self, reason: str) -> None:
        """External kill — coordinator calls this when kill-switch trips."""

        self.state.status = "killed"
        self.history.append(
            IterationResult(
                metric=float("nan"),
                tokens_delta=0,
                kept=False,
                error=f"killed: {reason}",
            )
        )

    def mark_converged(self) -> None:
        """External convergence — coordinator called ``detect_convergence``."""

        self.state.status = "converged"
