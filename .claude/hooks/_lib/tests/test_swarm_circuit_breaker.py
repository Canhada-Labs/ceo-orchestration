"""PLAN-102 Wave B — tests for swarm_circuit_breaker primitives.

STAGED for ceremony Phase A1 copy to
`.claude/hooks/_lib/tests/test_swarm_circuit_breaker.py`.

Covers PLAN-102 AC B.4 (reverse-tripwire), B.5 (weekend-burn),
B.6 (recovery latency SLO).

Stdlib only. pytest-compatible. Python >= 3.9.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sys
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if _HERE.name == "PLAN-102":
    _HOOKS = _HERE.parents[1] / ".claude" / "hooks"
elif _HERE.name == "tests":
    _HOOKS = _HERE.parents[1]
else:
    _HOOKS = _HERE.parents[2] / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

_lib_testing = importlib.import_module("_lib.testing")
TestEnvContext = _lib_testing.TestEnvContext

try:
    _scb_mod = importlib.import_module("_lib.swarm_circuit_breaker")
except ImportError:
    _staged = Path(__file__).resolve().parent / "wave-b-swarm-circuit-breaker.py"
    _spec = importlib.util.spec_from_file_location("_staged_swarm_circuit_breaker", _staged)
    _scb_mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_scb_mod)
SwarmCircuitBreaker = _scb_mod.SwarmCircuitBreaker


def _emit(audit_path: Path, events) -> None:
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")


class TestSwarmCircuitBreaker(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        self.audit_path = self.audit_dir / "audit-log.jsonl"

    def test_reverse_tripwire_under_threshold_no_pause(self):
        now = time.time()
        events = [
            {"action": "swarm_iteration", "ts": now - 100}
            for _ in range(50)
        ]
        _emit(self.audit_path, events)
        self.assertFalse(
            SwarmCircuitBreaker.should_pause_reverse_tripwire(
                self.audit_path, threshold=1000, window_hours=24
            )
        )

    def test_reverse_tripwire_over_threshold_with_owner_event_no_pause(self):
        """P1 #2 fold — Owner-physical proxy is `session_start` (real
        action in `_KNOWN_ACTIONS`), not the phantom
        `swarm_owner_physical_event`."""
        now = time.time()
        events = [
            {"action": "swarm_iteration", "ts": now - 100}
            for _ in range(1500)
        ]
        events.append({"action": "session_start", "ts": now - 50})
        _emit(self.audit_path, events)
        self.assertFalse(
            SwarmCircuitBreaker.should_pause_reverse_tripwire(
                self.audit_path, threshold=1000, window_hours=24
            )
        )

    def test_reverse_tripwire_over_threshold_no_owner_event_pause(self):
        now = time.time()
        events = [
            {"action": "swarm_iteration", "ts": now - 100}
            for _ in range(1500)
        ]
        _emit(self.audit_path, events)
        self.assertTrue(
            SwarmCircuitBreaker.should_pause_reverse_tripwire(
                self.audit_path, threshold=1000, window_hours=24
            )
        )

    def test_weekend_burn_under_12h_no_pause(self):
        now = time.time()
        events = [
            {"action": "swarm_started", "ts": now - 3600, "swarm_id": "s1"},
        ]
        _emit(self.audit_path, events)
        self.assertFalse(
            SwarmCircuitBreaker.should_pause_weekend_burn(
                self.audit_path, max_hours=12
            )
        )

    def test_weekend_burn_over_12h_with_owner_read_no_pause(self):
        """P1 #2 fold — `session_start` is the real Owner-physical
        proxy (not phantom `user_message`)."""
        now = time.time()
        events = [
            {"action": "swarm_started", "ts": now - 13 * 3600, "swarm_id": "s1"},
            {"action": "session_start", "ts": now - 1800},
        ]
        _emit(self.audit_path, events)
        self.assertFalse(
            SwarmCircuitBreaker.should_pause_weekend_burn(
                self.audit_path, max_hours=12
            )
        )

    def test_weekend_burn_over_12h_no_owner_read_pause(self):
        now = time.time()
        events = [
            {"action": "swarm_started", "ts": now - 13 * 3600, "swarm_id": "s1"},
        ]
        _emit(self.audit_path, events)
        self.assertTrue(
            SwarmCircuitBreaker.should_pause_weekend_burn(
                self.audit_path, max_hours=12
            )
        )

    def test_recovery_latency_p99_under_60s(self):
        kill_ts = 1000.0
        halts = [kill_ts + 0.5 + i * 0.1 for i in range(50)]
        p99 = SwarmCircuitBreaker.recovery_latency_p99(kill_ts, halts)
        self.assertLess(p99, 60.0)

    def test_recovery_latency_p99_over_60s_fails_slo(self):
        kill_ts = 1000.0
        # 90 fast + 10 super-slow → p99 = the 99th-percentile observation
        # is well into the slow cohort, well above 60s SLO threshold.
        halts = [kill_ts + 0.5 for _ in range(90)]
        halts.extend([kill_ts + 120.0 for _ in range(10)])
        p99 = SwarmCircuitBreaker.recovery_latency_p99(kill_ts, halts)
        self.assertGreater(p99, 60.0)

    def test_malformed_audit_jsonl_skipped_no_crash(self):
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as fh:
            fh.write("{not json\n")
            fh.write("\n")
            fh.write(json.dumps({"action": "swarm_iteration", "ts": time.time()}) + "\n")
            fh.write("garbage line\n")
        # Should not raise
        result = SwarmCircuitBreaker.should_pause_reverse_tripwire(
            self.audit_path, threshold=1000, window_hours=24
        )
        self.assertFalse(result)

    def test_disabled_via_env_flag(self):
        now = time.time()
        events = [
            {"action": "swarm_iteration", "ts": now - 100}
            for _ in range(1500)
        ]
        _emit(self.audit_path, events)
        os.environ["CEO_EXECUTION_CONTEXT_HOOKS_DISABLE"] = "1"
        self.assertFalse(
            SwarmCircuitBreaker.should_pause_reverse_tripwire(
                self.audit_path, threshold=1000, window_hours=24
            )
        )
        self.assertFalse(
            SwarmCircuitBreaker.should_pause_weekend_burn(
                self.audit_path, max_hours=12
            )
        )


class TestISOTimestampParsing(TestEnvContext):
    """PLAN-113 Codex pair-rail P1 — ISO-8601 timestamp parsing regression tests.

    Verifies that swarm detectors fire correctly when the audit-log uses
    ISO-8601 timestamps (the format audit_emit actually writes), not just
    numeric Unix timestamps.
    """

    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        self.audit_path = self.audit_dir / "audit-log.jsonl"

    def _iso(self, offset_seconds: float) -> str:
        """Return an ISO-8601 UTC string ``offset_seconds`` ago."""
        return (
            datetime.now(timezone.utc) - timedelta(seconds=offset_seconds)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

    def test_b4_fires_with_iso_timestamps(self):
        """1001 swarm_iteration ISO events in-window → B.4 should fire."""
        events = [
            {"action": "swarm_iteration", "ts": self._iso(100)}
            for _ in range(1001)
        ]
        _emit(self.audit_path, events)
        self.assertTrue(
            SwarmCircuitBreaker.should_pause_reverse_tripwire(
                self.audit_path, threshold=1000, window_hours=24
            )
        )

    def test_b5_fires_with_iso_timestamps(self):
        """swarm_started 13h ago (ISO), no session_start → B.5 should fire."""
        events = [
            {"action": "swarm_started", "ts": self._iso(13 * 3600), "swarm_id": "iso-s1"},
        ]
        _emit(self.audit_path, events)
        self.assertTrue(
            SwarmCircuitBreaker.should_pause_weekend_burn(
                self.audit_path, max_hours=12
            )
        )

    def test_old_iso_events_not_counted(self):
        """ISO timestamps 48h ago fall outside the 24h window → B.4 should not fire."""
        events = [
            {"action": "swarm_iteration", "ts": self._iso(48 * 3600)}
            for _ in range(1001)
        ]
        _emit(self.audit_path, events)
        self.assertFalse(
            SwarmCircuitBreaker.should_pause_reverse_tripwire(
                self.audit_path, threshold=1000, window_hours=24
            )
        )

    def test_event_ts_numeric_still_works(self):
        """Numeric Unix-seconds timestamps still parse correctly (backcompat)."""
        now = time.time()
        events = [
            {"action": "swarm_iteration", "ts": now - 100}
            for _ in range(1001)
        ]
        _emit(self.audit_path, events)
        self.assertTrue(
            SwarmCircuitBreaker.should_pause_reverse_tripwire(
                self.audit_path, threshold=1000, window_hours=24
            )
        )

    def test_event_ts_wall_ns_fallback(self):
        """wall_ns nanosecond-epoch fallback: in-window event counted for B.4."""
        now_ns = int(time.time() * 1_000_000_000)
        # event has no 'ts', but has wall_ns close to now → in-window
        events = [
            {"action": "swarm_iteration", "wall_ns": now_ns - i * 1_000_000}
            for i in range(1001)
        ]
        _emit(self.audit_path, events)
        self.assertTrue(
            SwarmCircuitBreaker.should_pause_reverse_tripwire(
                self.audit_path, threshold=1000, window_hours=24
            )
        )


if __name__ == "__main__":
    unittest.main()
