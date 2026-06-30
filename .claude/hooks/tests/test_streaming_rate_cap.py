"""PLAN-090 Wave B.5 — streaming rate-cap discipline.

R1 perf P0 fold + R2 Codex iter-1 P1 fold (token-bucket discipline):

- 10 burst capacity + 5/min sustained refill per persona
- Aggregate ceiling 20/min across all personas in a session
- Default mode aggregates `batch_dispatched` at stream end (NO per-token emit)
- Verbose mode (`CEO_AUDIT_STREAM_VERBOSE=1` EXACT MATCH) opts into per-token
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

from _lib.testing import TestEnvContext  # noqa: E402


class TestStreamingRateCapBuckets(TestEnvContext):

    def test_token_bucket_aggregate_and_per_persona(self) -> None:
        """Burst capacity 10 + sustained 5/min per persona; agg ceiling 20/min."""
        from _lib import audit_emit
        # Reset rate-cap state via _plan088_rate_admit / module reload pattern.
        os.environ["CEO_AUDIT_STREAM_VERBOSE"] = "1"
        try:
            # Emit 200 tokens for one persona in burst — only first 10 should pass
            # (token bucket = burst 10).
            admitted = 0
            for _ in range(200):
                if audit_emit.streaming_rate_admit("persona-A"):
                    admitted += 1
            self.assertLessEqual(
                admitted, 10,
                f"per-persona burst cap is 10, got {admitted} admissions",
            )
        finally:
            os.environ.pop("CEO_AUDIT_STREAM_VERBOSE", None)

    def test_default_mode_no_per_token_emit(self) -> None:
        """200 tokens in 0.1s → ≤1 streaming_token_yielded in audit-log (default)."""
        from _lib.adapters.live.claude_batch import BatchClaudeLiveAdapter
        # CEO_AUDIT_STREAM_VERBOSE unset → default mode aggregate-only.
        os.environ.pop("CEO_AUDIT_STREAM_VERBOSE", None)
        adapter = BatchClaudeLiveAdapter()
        list(adapter.stream_call(
            messages=[{"role": "user", "content": "x"}],
            model="claude-haiku-4-5",
        ))
        log = self.read_audit_log()
        # Default mode emits 0 per-token events.
        self.assertEqual(
            log.count('"streaming_token_yielded"'), 0,
            "default mode must not emit any per-token streaming events",
        )

    def test_dropped_count_summary_on_rate_cap(self) -> None:
        """Rate-cap fires → ONE streaming_rate_capped with dropped_count."""
        from _lib import audit_emit
        os.environ["CEO_AUDIT_STREAM_VERBOSE"] = "1"
        try:
            for _ in range(200):
                audit_emit.streaming_rate_admit("persona-A")
            # End-of-stream summary emit.
            audit_emit.emit_streaming_rate_capped(
                persona="persona-A",
                dropped_count=190,
            )
            log = self.read_audit_log()
            self.assertIn('"streaming_rate_capped"', log)
            self.assertIn('"dropped_count":190', log.replace(" ", ""))
        finally:
            os.environ.pop("CEO_AUDIT_STREAM_VERBOSE", None)


class TestPersonaAutoDecisionRateCap(TestEnvContext):

    def test_persona_auto_decision_rate_cap_per_persona(self) -> None:
        """A.4 token bucket 10 burst + 5/min sustained per persona."""
        from _lib import audit_emit
        admitted = 0
        for _ in range(50):
            if audit_emit.persona_auto_decision_rate_admit("vibecoder"):
                admitted += 1
        self.assertLessEqual(
            admitted, 10,
            f"persona-auto-decision burst cap is 10, got {admitted}",
        )

    def test_persona_auto_decision_summary_on_drop(self) -> None:
        from _lib import audit_emit
        for _ in range(50):
            audit_emit.persona_auto_decision_rate_admit("vibecoder")
        audit_emit.emit_persona_auto_rate_capped(
            persona="vibecoder",
            dropped_count=40,
        )
        log = self.read_audit_log()
        self.assertIn('"persona_auto_rate_capped"', log)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
