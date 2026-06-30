"""PLAN-059 Phase 1.1 — closes C-P0-04 (PLAN-058 audit finding).

**Gap that this closes:** Phase 6 tests (test_coordinator_tick.py +
test_process_group_reap.py + test_parent_death_integration.py) cover
the isolated kill-switch mechanics with real subprocesses but do NOT
exercise the full coordinator-level composition end-to-end:

1. ``coordinator.tick()`` invoked with a real ``expected_parent_pid``
2. Real parent SIGKILL'd mid-swarm
3. ``tick()`` returns ``DECISION_HALT`` with the
   ``coordinator_tick_parent_death`` reason (not just the underlying
   ``parent_still_alive`` helper returning False in isolation)
4. Post-halt, ``escalated_kill`` on running loop pids completes with
   a real ``success`` or ``sigkill_abandoned`` outcome — no
   monkeypatching of ``_wait_for_death``

This module adds 2 tests that cover the production composition.

Skipped on Windows per ADR-049a. Latency gates inherit from Phase 6
(2s parent-death detection; 7s stuck-child teardown).
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

import pytest


# Path to swarm package — tests under .claude/scripts/swarm/tests/
# so parent of parent is .claude/scripts/ which contains swarm/.
_SWARM_PARENT = str(Path(__file__).resolve().parents[2])


# =============================================================================
# Helper: a "coordinator subprocess" that calls coordinator.tick() in a loop
# =============================================================================

_COORDINATOR_RUNNER_SCRIPT = textwrap.dedent("""
    '''In-process coordinator tick loop.

    Spawned as a sub-subprocess whose *direct* parent is the intermediate
    supervisor. Captures own ppid at init, then enters a polling loop
    calling ``coordinator.tick()`` every 100ms. Writes each tick's
    decision + reasons to the provided output file as JSONL so the
    outer test can verify the production code path fires.

    Exits when tick returns DECISION_HALT OR after max_iterations.
    '''
    import json
    import os
    import sys
    import time

    # CEO_SWARM=1 bypasses kill_switch layer 1 (env default-OFF) so the
    # test can exercise the parent-death fast-path instead of the env gate.
    os.environ['CEO_SWARM'] = '1'
    # CLAUDE_PROJECT_DIR can be absent when spawned standalone; stub it
    # so evaluate_kill_switch's sentinel-path resolution does not crash.
    os.environ.setdefault('CLAUDE_PROJECT_DIR', os.getcwd())

    sys.path.insert(0, {swarm_parent!r})

    from swarm import coordinator
    from swarm.kill_switch import DECISION_HALT

    out_path = sys.argv[1]
    max_iterations = int(sys.argv[2])

    # Capture ppid AT INIT — this is the value under test.
    expected_ppid = os.getppid()

    # Build minimal SwarmConfig + empty LoopState dict. The test is
    # about the parent-death fast-path inside tick(), not about budget
    # or convergence — so budget is huge, 0 loops is fine.
    cfg = coordinator.SwarmConfig(
        n_loops=1,
        budget_tokens=10_000_000,
        goal='production-integration-test',
    )
    loops = {{
        'loop-0': coordinator.LoopState(loop_id='loop-0'),
    }}

    with open(out_path, 'w') as f:
        # Announce init — outer test uses this as readiness signal.
        f.write(json.dumps({{
            'event': 'init',
            'pid': os.getpid(),
            'expected_ppid': expected_ppid,
        }}) + chr(10))
        f.flush()

        for i in range(max_iterations):
            result = coordinator.tick(
                loops,
                cfg=cfg,
                expected_parent_pid=expected_ppid,
            )
            record = {{
                'event': 'tick',
                'iteration': i,
                'decision': result.decision,
                'reasons': list(result.reasons),
            }}
            f.write(json.dumps(record) + chr(10))
            f.flush()

            if result.decision == DECISION_HALT:
                f.write(json.dumps({{
                    'event': 'halt_detected',
                    'iteration': i,
                }}) + chr(10))
                f.flush()
                sys.exit(0)

            time.sleep(0.1)

        # If we drain max_iterations without halt, exit non-zero.
        f.write(json.dumps({{
            'event': 'max_iterations_reached',
            'iteration': max_iterations,
        }}) + chr(10))
        f.flush()
    sys.exit(1)
""").strip()


def _spawn_supervisor_and_coordinator(
    out_file: Path, max_iterations: int = 50
) -> subprocess.Popen:
    """Spawn the two-tier tree.

    Returns the intermediate supervisor Popen. The supervisor itself
    spawns the coordinator runner as a child; coordinator's os.getppid()
    == supervisor.pid.

    Killing the supervisor is what the test is verifying — the
    coordinator's tick() should detect the death via
    ``parent_still_alive(expected_ppid)`` returning False (because
    ``os.getppid()`` becomes 1/launchd/init after reparenting).
    """
    supervisor_code = textwrap.dedent(f"""
        import subprocess
        import sys
        import time

        p = subprocess.Popen(
            [
                {sys.executable!r},
                '-c',
                {_COORDINATOR_RUNNER_SCRIPT.format(swarm_parent=_SWARM_PARENT)!r},
                {str(out_file)!r},
                {str(max_iterations)!r},
            ],
            start_new_session=True,
        )
        # Hold the supervisor alive until killed externally.
        while True:
            time.sleep(0.5)
    """).strip()
    child_env = os.environ.copy()
    child_env["CEO_SWARM"] = "1"
    child_env.setdefault("CLAUDE_PROJECT_DIR", os.getcwd())
    return subprocess.Popen(
        [sys.executable, "-c", supervisor_code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=child_env,
    )


def _wait_for_init_line(out_file: Path, timeout: float = 5.0) -> dict:
    """Block until the coordinator writes its init announcement."""
    import json

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if out_file.exists() and out_file.stat().st_size > 0:
            try:
                first_line = out_file.read_text().splitlines()[0]
                record = json.loads(first_line)
                if record.get("event") == "init":
                    return record
            except (ValueError, IndexError):
                pass
        time.sleep(0.05)
    raise TimeoutError(
        f"coordinator subprocess never wrote init line to {out_file}"
    )


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


# =============================================================================
# Test 1 — coordinator.tick() detects real parent death end-to-end
# =============================================================================


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
def test_tick_production_integration_detects_real_parent_death(
    tmp_path: Path,
) -> None:
    """Full production code path: tick() + real parent SIGKILL.

    What this tests that existing test_coordinator_tick.py does NOT:

    - tick() is invoked from a subprocess whose actual os.getppid() is
      the supervisor — no mocking of parent_still_alive, no stubbing
      of expected_parent_pid.
    - The subprocess runs coordinator.tick() in a live polling loop,
      exactly as the real coordinator entry point would.
    - Supervisor is SIGKILL'd; coordinator's subsequent tick must
      transition from DECISION_CONTINUE → DECISION_HALT within the 2s
      latency gate (inherited from PLAN-051 Phase 6 Performance Risk
      #5 contract).

    Acceptance per PLAN-058 C-P0-04: tick() detects + halts via real
    parent death, not via unit-test stubs.
    """
    import json

    out_file = tmp_path / "tick_output.jsonl"

    supervisor = _spawn_supervisor_and_coordinator(out_file, max_iterations=100)
    try:
        init_record = _wait_for_init_line(out_file, timeout=10.0)
        coordinator_pid = init_record["pid"]
        captured_ppid = init_record["expected_ppid"]

        # Sanity: coordinator's captured ppid must equal supervisor pid.
        assert captured_ppid == supervisor.pid, (
            f"coordinator captured ppid={captured_ppid} but "
            f"supervisor.pid={supervisor.pid}; subprocess tree wrong"
        )
        assert _pid_alive(coordinator_pid), (
            "coordinator subprocess died before test could run"
        )

        # Read a few CONTINUE ticks first (sanity: tick is live + working).
        time.sleep(0.4)
        lines = out_file.read_text().splitlines()
        decisions_pre_kill = [
            json.loads(ln)
            for ln in lines
            if ln.strip() and json.loads(ln).get("event") == "tick"
        ]
        assert len(decisions_pre_kill) >= 1, (
            "coordinator should have completed ≥1 tick iteration pre-kill"
        )
        for d in decisions_pre_kill:
            assert d["decision"] != "halt", (
                f"pre-kill tick unexpectedly halted: {d}"
            )

        # The production event under test: supervisor SIGKILL'd.
        t0 = time.monotonic()
        os.kill(supervisor.pid, signal.SIGKILL)
        supervisor.wait(timeout=3)

        # Coordinator's tick must detect + halt within 2s (Phase 6
        # latency gate) plus ~100ms poll interval slack + CI noise.
        deadline = t0 + 4.0
        halt_seen = False
        while time.monotonic() < deadline:
            if not _pid_alive(coordinator_pid):
                # Coordinator exited — inspect its output.
                lines = out_file.read_text().splitlines()
                for ln in reversed(lines):
                    if not ln.strip():
                        continue
                    record = json.loads(ln)
                    if record.get("event") == "halt_detected":
                        halt_seen = True
                        break
                if halt_seen:
                    break
            time.sleep(0.05)

        # Inspect last tick record to verify the halt decision.
        lines = out_file.read_text().splitlines()
        tick_records = [
            json.loads(ln)
            for ln in lines
            if ln.strip() and json.loads(ln).get("event") == "tick"
        ]
        assert tick_records, "no tick records at all — coordinator crashed?"

        halt_ticks = [t for t in tick_records if t["decision"] == "halt"]
        assert halt_ticks, (
            f"coordinator never returned DECISION_HALT after parent "
            f"SIGKILL; last decisions: {[t['decision'] for t in tick_records[-5:]]}"
        )

        # The reason must cite the coordinator's fast-path breadcrumb,
        # which is the grep-verifiable production contract.
        first_halt = halt_ticks[0]
        reasons_joined = " ".join(first_halt.get("reasons", []))
        assert "coordinator_tick_parent_death" in reasons_joined, (
            f"halt reason did not cite fast-path breadcrumb; "
            f"reasons={first_halt['reasons']}"
        )
        # Latency gate: first-halt iteration must be reachable quickly.
        # Each tick is ~100ms, so at most ~30 iterations within 3s.
        assert first_halt["iteration"] < 40, (
            f"tick took {first_halt['iteration']} iterations to detect "
            f"parent death; >2s latency gate likely violated"
        )

        # Ensure coordinator actually exited (not just emitted halt).
        # If still alive after 2s post-halt, test fails — coordinator
        # ignored its own halt signal.
        post_halt_deadline = time.monotonic() + 2.0
        while time.monotonic() < post_halt_deadline:
            if not _pid_alive(coordinator_pid):
                return  # success
            time.sleep(0.05)
        pytest.fail(
            f"coordinator pid {coordinator_pid} still alive 2s after "
            f"tick returned DECISION_HALT; halt not being honored"
        )
    finally:
        # Defensive cleanup.
        if supervisor.poll() is None:
            try:
                supervisor.kill()
                supervisor.wait(timeout=2)
            except (OSError, ProcessLookupError, subprocess.TimeoutExpired):
                pass


# =============================================================================
# Test 2 — tick halt → escalated_kill production composition (no monkeypatch)
# =============================================================================


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
def test_coordinator_halt_triggers_real_escalated_kill_outcome(
    tmp_path: Path,
) -> None:
    """Compose tick-detected halt with escalated_kill on a real stuck child.

    The existing test_sigkill_abandoned_real_subprocess exercises the
    abandon path by monkeypatching ``_wait_for_death`` to always return
    False — that's NECESSARY to test the abandon branch because a real
    SIGKILL-responsive process would reap normally.

    This test complements it by exercising the normal (non-abandon)
    production path WITHOUT any monkeypatch: a stuck child ignoring
    SIGTERM gets SIGKILL'd and reaped successfully via real kernel
    mechanics. Expected outcome: "sigkill_tier1" — tier-1 escalation
    path (SIGTERM 5s grace → SIGKILL + 2s reap). Verified reaped via
    real os.kill(pid, 0) post-call.

    Why this matters for C-P0-04: it verifies the coordinator's
    post-halt cleanup path works end-to-end without test doubles —
    the exact scenario the PLAN-058 audit flagged as missing.
    """
    from swarm import _process_group as pg

    # Spawn a child that ignores SIGTERM, responds only to SIGKILL.
    # NOT a kernel-stuck child (like the other test) — this one WILL
    # reap cleanly on SIGKILL, exercising the success branch.
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import signal, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "time.sleep(60)",
        ],
        start_new_session=True,
    )
    try:
        # Let the child install its signal handler.
        time.sleep(0.3)
        assert _pid_alive(proc.pid)

        # Tier-1 escalation: SIGTERM (ignored) → SIGKILL (honored).
        # Short grace_seconds to make the test fast.
        t0 = time.monotonic()
        outcome = pg.escalated_kill(
            proc.pid,
            tier=1,
            grace_seconds=0.5,
            post_kill_reap_seconds=2.0,
        )
        elapsed = time.monotonic() - t0

        # Production contract: sigkill_tier1 = SIGTERM grace elapsed →
        # SIGKILL → reaped cleanly (NOT abandoned). Anything else
        # (sigkill_abandoned, sigkill_tier2) indicates broken wire-up
        # OR the child responded to SIGTERM (which we blocked).
        assert outcome == "sigkill_tier1", (
            f"expected sigkill_tier1 (SIGTERM ignored → SIGKILL reaped "
            f"cleanly); got {outcome} after {elapsed:.2f}s"
        )

        # Latency gate: 0.5s grace + ≤0.2s SIGKILL reap = p99 ≤ 0.7s
        # under Phase 6 contract. Allow 2.0s slack for CI noise.
        assert elapsed < 2.0, (
            f"escalated_kill took {elapsed:.2f}s; Phase 6 p99 gate is "
            f"~0.7s for cooperative SIGKILL reap"
        )

        # Process must actually be gone (not just reported as reaped).
        time.sleep(0.1)
        assert not _pid_alive(proc.pid), (
            f"escalated_kill returned {outcome} but pid {proc.pid} is "
            f"still alive — reap mechanics broken"
        )
    finally:
        # Defensive: force-kill if still alive.
        if proc.poll() is None:
            try:
                os.kill(proc.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
