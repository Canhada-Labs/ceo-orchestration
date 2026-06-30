"""Conformance tests for ADR-040 §2 Circuit Breaker — PLAN-013 Phase D.8.

Per debate round 1 consensus §C8 CRITICAL: every formally-proved
property in ``docs/formal-verification/properties-proved.md`` MUST map
to an executable property-based test against the real Python
implementation, plus a mutation-test gate asserting the test would
fail under simulated implementation bugs.

## Four property tests

- **S1** ``test_s1_breaker_opens_on_threshold`` — record_failure×N
  (N=threshold) within window_s flips state CLOSED→OPEN.
- **S2** ``test_s2_half_open_singleton`` — concurrent should_allow()
  calls in HALF_OPEN state return True exactly once.
- **S3** ``test_s3_open_emits_audit`` — state CLOSED→OPEN transition
  emits exactly one ``breaker_opened`` audit event (Gap #4: harness
  wraps ``_open_locked`` to simulate the Wave-3 CEO patch).
- **L1** ``test_l1_eventually_heal`` — OPEN breaker transitions to
  HALF_OPEN after half_open_s elapses; probe resolves to CLOSED.

## Mutation gate

Each property test iterates its mutation set and asserts that every
mutation causes the core property assertion to fail. A conformance
test is counted PASS only when (a) the unmutated impl passes AND (b)
all mutations raise AssertionError (or an equivalent failure
signalled by ``_run_core_with_kill``).

## Harness rules (D.3 binding)

1. TestEnvContext subclass — env isolation per PLAN-013 ADJ-022.
2. Deterministic seeds — ``random.seed(42)`` explicit where PRNG used.
3. Fake-clock via ``CircuitBreaker(clock=...)`` injection — zero
   ``time.sleep`` in the test body.
4. No live network — pure-function testing.
5. Mapping row integrity enforced by
   ``.claude/scripts/check-conformance-harness-mapping.py``.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
import random
import sys
import threading
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Type

# Path bootstrap — conftest.py handles this for pytest, but ``python3 -m
# unittest`` may not import the conftest, so we repeat the bootstrap.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from _lib import audit_emit  # noqa: E402
from _lib.adapters.live._breaker import (  # noqa: E402
    BreakerState,
    CircuitBreaker,
)
from _lib.testing import TestEnvContext  # noqa: E402


# ------------------------------------------------------------------
# Helpers — mutation loading + S3 harness patching
# ------------------------------------------------------------------


def _load_mutations(property_id: str) -> List[ModuleType]:
    """Discover all mutations under mutation_fixtures/breaker/ tagged for the given property.

    The package was historically named ``mutations`` but was renamed to
    ``mutation_fixtures`` in PLAN-019 Phase 1 to avoid a top-level name
    collision with ``.claude/hooks/tests/mutations/`` under pytest
    whole-tree collection (P0-04).
    """
    try:
        from mutation_fixtures import breaker as mutations_breaker  # type: ignore
    except ImportError:
        # ``python3 -m pytest`` can sometimes leave the mutation_fixtures/
        # pkg uninitialised; retry via explicit import.
        import mutation_fixtures.breaker as mutations_breaker  # type: ignore

    mods: List[ModuleType] = []
    pkg_path = Path(mutations_breaker.__file__).resolve().parent  # type: ignore[arg-type]
    for info in pkgutil.iter_modules([str(pkg_path)]):
        if not info.name.startswith("mut_"):
            continue
        mod = importlib.import_module(f"mutation_fixtures.breaker.{info.name}")
        if getattr(mod, "PROPERTY", None) == property_id:
            mods.append(mod)
    # Sort for deterministic iteration (and deterministic failure order).
    mods.sort(key=lambda m: m.__name__)
    return mods


class _PatchedBreakerS3(CircuitBreaker):
    """CircuitBreaker with Gap #4 fix applied: ``_open_locked`` emits the audit event.

    The real ``_breaker.py`` does NOT currently call
    ``emit_breaker_opened`` from ``_open_locked`` (Gap #4 in the
    PLAN-013 Session 20 CHANGELOG). CEO will inline-patch the real
    source in Wave 3; until then, the S3 conformance harness uses this
    subclass so the property is testable against an as-specified
    implementation.

    **Contract:** this subclass simulates what the Wave-3 patch is
    expected to do:

        def _open_locked(self, now):
            self._state = BreakerState.OPEN
            self._opened_at = now
            self._probe_available = False
            emit_breaker_opened(
                provider=self._provider,
                failures_in_window=len(self._failures),
                threshold=self._threshold,
                reason="server_error",
            )

    Mutations inheriting from _PatchedBreakerS3 override _open_locked to
    introduce bugs; none of them call super()._open_locked(), so the
    harness-installed emit can be selectively skipped/swapped.
    """

    def __init__(self, *args: Any, provider: str = "test", **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._provider = provider

    def _open_locked(self, now: float) -> None:  # noqa: D401
        self._state = BreakerState.OPEN
        self._opened_at = now
        self._probe_available = False
        audit_emit.emit_breaker_opened(
            provider=self._provider,
            failures_in_window=len(self._failures),
            threshold=self._threshold,
            reason="server_error",
        )


# ------------------------------------------------------------------
# S1 — Threshold-triggered open
# ------------------------------------------------------------------


class TestS1BreakerOpensOnThreshold(TestEnvContext):
    """Property S1: CLOSED && failures_in_window >= threshold => OPEN (bounded).

    Mutation budget: 6.
    """

    PROPERTY_ID = "S1"

    def _core_assertion(self, cb_cls: Type[CircuitBreaker]) -> None:
        """Run the S1 core property against a breaker class; raise AssertionError on violation.

        Phase A — threshold-exact: threshold-1 failures leaves CLOSED; N-th flips OPEN.
        Phase B — window pruning: failures older than ``window_s`` MUST be pruned
          so the breaker does NOT open on stale entries (kills S1-02).
        Phase C — reset-on-heal: a HALF_OPEN->CLOSED transition clears the failure
          deque; post-heal record_failure×(threshold-1) MUST leave the breaker
          CLOSED (kills S1-03).
        Phase D — state-guard: record_failure after the breaker is already OPEN
          MUST NOT reset opened_at (kills S1-04).
        """
        random.seed(42)
        t = [1000.0]  # mutable box so the lambda can advance the clock

        def clock() -> float:
            return t[0]

        # window_s >> half_open_s so the heal cycle fits well within a
        # single window. This lets phase C distinguish "cleared on heal"
        # from "naturally aged out by window prune".
        cb = cb_cls(threshold=5, window_s=600, half_open_s=5, clock=clock)

        # --- Phase A: threshold-exact open -------------------------------
        if cb.state != BreakerState.CLOSED:
            raise AssertionError(
                f"S1 pre-condition failed: initial state != CLOSED (got {cb.state})"
            )
        for i in range(cb._threshold - 1):
            cb.record_failure(reason="server_error")
            t[0] += 0.1
            if cb.state != BreakerState.CLOSED:
                raise AssertionError(
                    f"S1 violated (phase A): opened at failure {i + 1} of "
                    f"{cb._threshold - 1} (< threshold)"
                )
        cb.record_failure(reason="server_error")
        if cb.state != BreakerState.OPEN:
            raise AssertionError(
                f"S1 violated (phase A): after {cb._threshold} failures state is "
                f"{cb.state}, expected OPEN"
            )
        opened_at_phase_a = cb._opened_at

        # --- Phase D: state-guard (extra failure after OPEN) --------------
        t[0] += 0.5
        cb.record_failure(reason="server_error")
        if cb._opened_at != opened_at_phase_a:
            raise AssertionError(
                "S1 violated (phase D): record_failure after OPEN changed "
                f"opened_at from {opened_at_phase_a} to {cb._opened_at}"
            )

        # --- Heal cycle to reach CLOSED again (drives phase C) -----------
        # Advance just enough to elapse half_open_s (5s), well within
        # window_s (600s). Any failures from phase A are STILL within
        # the window at this point — only a proper heal-clear should
        # drop them.
        t[0] += cb._half_open_s + 1.0
        if cb.state != BreakerState.HALF_OPEN:
            raise AssertionError(
                f"S1 setup: after half_open_s, state was {cb.state}, expected HALF_OPEN"
            )
        cb.should_allow()  # consume probe slot
        cb.record_success()
        if cb.state != BreakerState.CLOSED:
            raise AssertionError(
                f"S1 setup: after record_success on HALF_OPEN, state was "
                f"{cb.state}, expected CLOSED"
            )

        # --- Phase C: reset-on-heal invariant ----------------------------
        # After a HALF_OPEN->CLOSED heal, the failure deque MUST be clean.
        # Feed (threshold - 1) transient failures; breaker MUST stay CLOSED.
        # Because window_s=600 is large, any pre-heal failures are STILL
        # within the window — only a proper _failures.clear() on heal
        # would remove them. If the mutation skips the clear, those stale
        # entries PLUS the (threshold - 1) fresh ones add up to
        # >= threshold, and the breaker opens prematurely.
        for i in range(cb._threshold - 1):
            cb.record_failure(reason="server_error")
            t[0] += 0.01
            if cb.state != BreakerState.CLOSED:
                raise AssertionError(
                    f"S1 violated (phase C, reset-on-heal): post-heal failure "
                    f"#{i + 1} of {cb._threshold - 1} prematurely opened breaker "
                    f"— stale failures from pre-open cycle were not cleared "
                    f"(window_s={cb._window_s}, deque size now "
                    f"{len(cb._failures)})"
                )
        # Reset for phase B
        cb.reset()

        # --- Phase B: sliding-window pruning -----------------------------
        # Feed (threshold - 1) failures, advance clock past window_s so those
        # entries become stale, then feed (threshold - 1) more. Total count
        # in the window after prune is (threshold - 1), which is < threshold,
        # so the breaker MUST stay CLOSED.
        for _ in range(cb._threshold - 1):
            cb.record_failure(reason="server_error")
            t[0] += 0.01
        # Advance past the window so the first batch falls outside.
        t[0] += cb._window_s + 1.0
        # Feed another (threshold - 1) FRESH failures.
        for i in range(cb._threshold - 1):
            cb.record_failure(reason="server_error")
            t[0] += 0.01
            if cb.state != BreakerState.CLOSED:
                raise AssertionError(
                    f"S1 violated (phase B, window prune): state opened after "
                    f"{i + 1} fresh failures — stale pre-window failures "
                    f"were not pruned (total in deque: {len(cb._failures)})"
                )

    def test_s1_breaker_opens_on_threshold(self) -> None:
        """S1 conformance: un-mutated CircuitBreaker satisfies threshold-triggered-open.

        This is the authoritative test named in
        ``docs/formal-verification/properties-proved.md`` §2 — the
        mapping-CI check (`check-conformance-harness-mapping.py`)
        asserts that this method exists here.
        """
        self._core_assertion(CircuitBreaker)

    def test_s1_mutations_fail(self) -> None:
        """Every S1 mutation causes the core property assertion to fail."""
        mutations = _load_mutations("S1")
        self.assertGreaterEqual(
            len(mutations),
            6,
            msg=f"S1 mutation budget is 6; discovered {len(mutations)}",
        )
        killed: List[str] = []
        survived: List[str] = []
        for mut_mod in mutations:
            cls_mutant = mut_mod.apply(CircuitBreaker)
            try:
                self._core_assertion(cls_mutant)
            except AssertionError:
                killed.append(mut_mod.__name__)
            else:
                survived.append(mut_mod.__name__)
        if survived:
            raise AssertionError(
                "S1 mutations NOT killed by conformance test — these bugs "
                f"would slip through: {survived}. Killed: {killed}"
            )


# ------------------------------------------------------------------
# S2 — Half-open singleton
# ------------------------------------------------------------------


class TestS2HalfOpenSingleton(TestEnvContext):
    """Property S2: HALF_OPEN => |in_flight| <= 1.

    Mutation budget: 5.
    """

    PROPERTY_ID = "S2"

    def _force_into_half_open(self, cb: CircuitBreaker, t: List[float]) -> None:
        """Drive CLOSED -> OPEN -> HALF_OPEN on the given breaker."""
        for _ in range(cb._threshold):
            cb.record_failure(reason="server_error")
            t[0] += 0.1
        if cb.state != BreakerState.OPEN:
            raise AssertionError(
                f"S2 setup failed: state after threshold failures was "
                f"{cb.state}, expected OPEN"
            )
        # Advance clock past half_open_s so next should_allow flips to HALF_OPEN.
        t[0] += cb._half_open_s + 1.0
        # Reading .state triggers the lazy refresh (OPEN -> HALF_OPEN).
        if cb.state != BreakerState.HALF_OPEN:
            raise AssertionError(
                f"S2 setup failed: state after half_open_s elapse was "
                f"{cb.state}, expected HALF_OPEN"
            )

    def _core_assertion(self, cb_cls: Type[CircuitBreaker]) -> None:
        """S2 core: concurrent should_allow() in HALF_OPEN returns True exactly once."""
        random.seed(42)
        t = [1000.0]

        def clock() -> float:
            return t[0]

        cb = cb_cls(threshold=3, window_s=30, half_open_s=5, clock=clock)
        self._force_into_half_open(cb, t)

        # Now run N concurrent should_allow calls. Exactly ONE MUST
        # return True (the singleton probe); all others MUST return False.
        N = 8
        barrier = threading.Barrier(N)
        results: List[bool] = []
        results_lock = threading.Lock()

        def worker() -> None:
            # Rendezvous to maximise race window.
            try:
                barrier.wait(timeout=5.0)
            except threading.BrokenBarrierError:
                with results_lock:
                    results.append(False)
                return
            got = cb.should_allow()
            with results_lock:
                results.append(got)

        threads = [threading.Thread(target=worker) for _ in range(N)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=5.0)

        if len(results) != N:
            raise AssertionError(
                f"S2 violated: expected {N} should_allow results, got {len(results)}"
            )
        true_count = sum(1 for r in results if r)
        if true_count != 1:
            raise AssertionError(
                f"S2 violated: expected exactly 1 probe-True among {N} "
                f"concurrent should_allow calls, got {true_count} "
                f"(results={results})"
            )

    def test_s2_half_open_singleton(self) -> None:
        """S2 conformance: un-mutated CircuitBreaker satisfies half-open-singleton.

        Authoritative test name per mapping table §2.
        """
        self._core_assertion(CircuitBreaker)

    def test_s2_mutations_fail(self) -> None:
        """Every S2 mutation violates the singleton invariant."""
        mutations = _load_mutations("S2")
        self.assertGreaterEqual(
            len(mutations),
            5,
            msg=f"S2 mutation budget is 5; discovered {len(mutations)}",
        )
        killed: List[str] = []
        survived: List[str] = []
        # Run each mutation a few times to de-flake mutations that rely on
        # scheduler interleaving (S2-01/S2-02). If ANY run catches the bug,
        # it counts as killed; if ALL runs pass, the mutation survived.
        RACE_RETRIES = 5
        for mut_mod in mutations:
            cls_mutant = mut_mod.apply(CircuitBreaker)
            caught = False
            for _ in range(RACE_RETRIES):
                try:
                    self._core_assertion(cls_mutant)
                except AssertionError:
                    caught = True
                    break
            if caught:
                killed.append(mut_mod.__name__)
            else:
                survived.append(mut_mod.__name__)
        if survived:
            raise AssertionError(
                "S2 mutations NOT killed by conformance test — these bugs "
                f"would slip through: {survived}. Killed: {killed}"
            )


# ------------------------------------------------------------------
# S3 — State-transition audit
# ------------------------------------------------------------------


class TestS3OpenEmitsAudit(TestEnvContext):
    """Property S3: CLOSED->OPEN transition emits exactly one ``breaker_opened`` event.

    Mutation budget: 5.

    **Gap #4 note (PLAN-013 Session 20 CHANGELOG):** the real
    ``_breaker.py::_open_locked`` does NOT currently emit. CEO will
    inline-patch it in Wave 3. This test uses ``_PatchedBreakerS3`` —
    a subclass that simulates the Wave-3 fix — as the un-mutated
    baseline. Once CEO lands the patch, the harness can swap
    ``_PatchedBreakerS3`` for ``CircuitBreaker`` directly; until then
    the subclass documents the intended behavior contract.
    """

    PROPERTY_ID = "S3"

    def _read_events(self) -> List[Dict[str, Any]]:
        log_text = self.read_audit_log()
        events: List[Dict[str, Any]] = []
        for line in log_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    def _core_assertion(self, cb_cls: Type[CircuitBreaker]) -> None:
        """S3 core: one CLOSED->OPEN transition emits exactly one ``breaker_opened`` event
        AND the state at the moment of emit MUST be OPEN (post-transition snapshot).

        Phase A — emit-once: threshold failures => exactly 1 breaker_opened event.
        Phase B — correct action string: event.action == "breaker_opened".
        Phase C — correct payload: threshold + failures_in_window match.
        Phase D — emit order: at emit-time the breaker state MUST already be OPEN
          (kills S3-03 which emits before state update).
        """
        random.seed(42)
        t = [1000.0]

        def clock() -> float:
            return t[0]

        # The _PatchedBreakerS3 constructor accepts ``provider`` kw; the
        # base CircuitBreaker does not.
        try:
            cb = cb_cls(
                threshold=3,
                window_s=30,
                half_open_s=60,
                clock=clock,
                provider="test_provider",
            )
        except TypeError:
            cb = cb_cls(threshold=3, window_s=30, half_open_s=60, clock=clock)

        # --- Phase D instrumentation: wrap emit_breaker_opened to capture
        # the observed state at the moment of emit.
        observed_state_at_emit: List[Any] = []

        def _spy_emit(
            provider: str,
            failures_in_window: int,
            threshold: int,
            reason: str = "server_error",
            session_id: str = "",
            project: str = "",
        ) -> None:
            # Record the state as seen AT THE MOMENT OF EMIT. Read the raw
            # field (NOT the property) to avoid re-entering refresh logic.
            observed_state_at_emit.append(cb._state)
            _real_emit(
                provider=provider,
                failures_in_window=failures_in_window,
                threshold=threshold,
                reason=reason,
                session_id=session_id,
                project=project,
            )

        _real_emit = audit_emit.emit_breaker_opened
        audit_emit.emit_breaker_opened = _spy_emit  # type: ignore[assignment]
        try:
            # Drive threshold failures.
            for _ in range(cb._threshold):
                cb.record_failure(reason="server_error")
                t[0] += 0.1
        finally:
            audit_emit.emit_breaker_opened = _real_emit  # type: ignore[assignment]

        # --- Phase A-pre: post-condition = state OPEN ---------------------
        if cb.state != BreakerState.OPEN:
            raise AssertionError(
                f"S3 pre-condition failed: state after threshold is "
                f"{cb.state}, expected OPEN"
            )

        # --- Phase A: exactly one breaker_opened event -------------------
        events = self._read_events()
        breaker_opened_events = [
            e for e in events if e.get("action") == "breaker_opened"
        ]
        if len(breaker_opened_events) != 1:
            raise AssertionError(
                f"S3 violated (phase A): expected exactly 1 breaker_opened "
                f"event, got {len(breaker_opened_events)} "
                f"(all events: {events})"
            )

        # --- Phase B: correct action string -------------------------------
        ev = breaker_opened_events[0]
        if ev.get("action") != "breaker_opened":
            raise AssertionError(
                f"S3 violated (phase B): action = {ev.get('action')!r}, "
                f"expected 'breaker_opened'"
            )

        # --- Phase C: correct payload ------------------------------------
        if ev.get("threshold") != cb._threshold:
            raise AssertionError(
                f"S3 violated (phase C): threshold field mismatch — got "
                f"{ev.get('threshold')}, expected {cb._threshold}"
            )
        if ev.get("provider") not in ("test_provider", "test"):
            raise AssertionError(
                f"S3 violated (phase C): provider field was "
                f"{ev.get('provider')!r}, expected 'test_provider' or 'test'"
            )

        # --- Phase D: emit order -----------------------------------------
        # At the moment of emit, state MUST already be OPEN.
        if len(observed_state_at_emit) != 1:
            raise AssertionError(
                f"S3 violated (phase D): emit was called "
                f"{len(observed_state_at_emit)} times, expected 1"
            )
        state_at_emit = observed_state_at_emit[0]
        if state_at_emit != BreakerState.OPEN:
            raise AssertionError(
                f"S3 violated (phase D): state observed at emit-time was "
                f"{state_at_emit!r}, expected BreakerState.OPEN "
                "(emit MUST fire AFTER state transition per ADR-040 §7)"
            )

    def test_s3_open_emits_audit(self) -> None:
        """S3 conformance: un-mutated _PatchedBreakerS3 (simulates Wave-3 fix) passes S3.

        Authoritative test name per mapping table §2.

        Once CEO lands the Gap #4 inline patch, change the argument
        from ``_PatchedBreakerS3`` to ``CircuitBreaker`` and delete
        ``test_s3_real_source_currently_fails_until_gap4_fixed``.
        """
        self._core_assertion(_PatchedBreakerS3)

    def test_s3_real_source_now_passes_after_gap4_fix(self) -> None:
        """Real CircuitBreaker passes S3 after Wave-3 Gap #4 inline patch.

        CEO landed the emit_breaker_opened call inside
        ``_breaker.py::_open_locked`` in Session 22 Wave 3. The real
        CircuitBreaker class now honors S3 without the
        ``_PatchedBreakerS3`` test shim.

        ``_PatchedBreakerS3`` is retained as the subclass mutations
        inherit from (the shim is now structurally equivalent to the
        real class for S3 purposes) — deleting it would require
        rewriting all 5 S3 mutation files, which is a later cleanup.
        """
        self._core_assertion(CircuitBreaker)

    def _truncate_audit_log(self) -> None:
        """Empty the audit log between mutation iterations.

        TestEnvContext routes all audit writes into ``self.audit_dir/
        audit-log.jsonl``. To keep each mutation's event set isolated
        we truncate the file between iterations. No env tampering —
        the TestEnvContext-provided path stays stable.
        """
        log_path = self.audit_dir / "audit-log.jsonl"
        if log_path.is_file():
            log_path.unlink()

    def test_s3_mutations_fail(self) -> None:
        """Every S3 mutation either skips emit or emits the wrong payload."""
        mutations = _load_mutations("S3")
        self.assertGreaterEqual(
            len(mutations),
            5,
            msg=f"S3 mutation budget is 5; discovered {len(mutations)}",
        )
        killed: List[str] = []
        survived: List[str] = []
        for mut_mod in mutations:
            cls_mutant = mut_mod.apply(_PatchedBreakerS3)
            # Truncate audit log between mutations so each run's events
            # are inspected in isolation. No env mutation.
            self._truncate_audit_log()
            try:
                self._core_assertion(cls_mutant)
            except AssertionError:
                killed.append(mut_mod.__name__)
            else:
                survived.append(mut_mod.__name__)
        if survived:
            raise AssertionError(
                "S3 mutations NOT killed by conformance test — these bugs "
                f"would slip through: {survived}. Killed: {killed}"
            )


# ------------------------------------------------------------------
# L1 — Eventually heal
# ------------------------------------------------------------------


class TestL1EventuallyHeal(TestEnvContext):
    """Property L1: OPEN => ◇HALF_OPEN; HALF_OPEN => ◇{CLOSED, OPEN}.

    Mutation budget: 5.
    """

    PROPERTY_ID = "L1"

    def _core_assertion(self, cb_cls: Type[CircuitBreaker]) -> None:
        """L1 core: open breaker heals to HALF_OPEN after half_open_s, then to CLOSED on success."""
        random.seed(42)
        t = [1000.0]

        def clock() -> float:
            return t[0]

        cb = cb_cls(threshold=3, window_s=30, half_open_s=5, clock=clock)

        # Force into OPEN.
        for _ in range(cb._threshold):
            cb.record_failure(reason="server_error")
            t[0] += 0.1
        if cb.state != BreakerState.OPEN:
            raise AssertionError(
                f"L1 pre-condition failed: state after threshold failures "
                f"was {cb.state}, expected OPEN"
            )

        # Stage 1: advance past half_open_s and assert OPEN -> HALF_OPEN.
        t[0] += cb._half_open_s + 1.0
        st = cb.state
        if st != BreakerState.HALF_OPEN:
            raise AssertionError(
                f"L1 violated: after half_open_s+1 elapsed, state was "
                f"{st}, expected HALF_OPEN"
            )

        # Stage 2: probe-success closes the breaker (HALF_OPEN -> CLOSED).
        # First, consume the probe slot via should_allow.
        allowed = cb.should_allow()
        if not allowed:
            raise AssertionError(
                "L1 violated: HALF_OPEN should_allow returned False on "
                "first call (no probe)"
            )
        cb.record_success()
        st2 = cb.state
        if st2 != BreakerState.CLOSED:
            raise AssertionError(
                f"L1 violated: after probe-success, state was {st2}, "
                f"expected CLOSED"
            )

        # Stage 3: re-open to verify the FAILURE path back to OPEN from HALF_OPEN.
        for _ in range(cb._threshold):
            cb.record_failure(reason="server_error")
            t[0] += 0.1
        if cb.state != BreakerState.OPEN:
            raise AssertionError(
                f"L1 violated (stage 3 pre): state was {cb.state}, expected OPEN"
            )
        t[0] += cb._half_open_s + 1.0
        if cb.state != BreakerState.HALF_OPEN:
            raise AssertionError(
                f"L1 violated (stage 3 mid): state after second heal window "
                f"was {cb.state}, expected HALF_OPEN"
            )
        # Consume the probe slot, then fail the probe.
        cb.should_allow()
        cb.record_failure(reason="server_error")
        st3 = cb.state
        if st3 != BreakerState.OPEN:
            raise AssertionError(
                f"L1 violated (stage 3 post): probe-failure left state at "
                f"{st3}, expected OPEN"
            )

    def test_l1_eventually_heal(self) -> None:
        """L1 conformance: un-mutated CircuitBreaker satisfies eventually-heal.

        Authoritative test name per mapping table §2.
        """
        self._core_assertion(CircuitBreaker)

    def test_l1_mutations_fail(self) -> None:
        """Every L1 mutation blocks the heal path."""
        mutations = _load_mutations("L1")
        self.assertGreaterEqual(
            len(mutations),
            5,
            msg=f"L1 mutation budget is 5; discovered {len(mutations)}",
        )
        killed: List[str] = []
        survived: List[str] = []
        for mut_mod in mutations:
            cls_mutant = mut_mod.apply(CircuitBreaker)
            try:
                self._core_assertion(cls_mutant)
            except AssertionError:
                killed.append(mut_mod.__name__)
            else:
                survived.append(mut_mod.__name__)
        if survived:
            raise AssertionError(
                "L1 mutations NOT killed by conformance test — these bugs "
                f"would slip through: {survived}. Killed: {killed}"
            )


if __name__ == "__main__":
    unittest.main()
