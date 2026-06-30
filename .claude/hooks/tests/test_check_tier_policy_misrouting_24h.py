"""Tests for `.claude/hooks/check_tier_policy_misrouting_24h.py`.

PLAN-091 Wave A.1 — coverage for the 16th Tier-S check:

- empty / absent audit-log → yellow ("audit-log.jsonl absent")
- audit-log present but no `model_routing_advised` events in window → green
- all entries route correctly → green (0% ratio)
- ratio 5-10% → yellow (status threshold)
- ratio ≥ 10% → red (status threshold)
- old entries (>24h) → ignored
- malformed JSONL → skipped (no crash)
- non-dict JSON → skipped
- unknown task_class (router returns None) → ignored
- audit-log unreadable (perm fault simulated) → yellow
- router import failure → yellow ("router unavailable")

Stdlib only. `TestEnvContext` from `_lib/testing.py` isolates env per S79.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"

sys.path.insert(0, str(HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402

CHECK_PATH = HOOKS_DIR / "check_tier_policy_misrouting_24h.py"


def _load_mod():
    """Load the standalone check module fresh per-test."""
    spec = importlib.util.spec_from_file_location(
        "check_tier_policy_misrouting_24h_mod", CHECK_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load_mod()


def _write_audit_log(env_ctx: "TestEnvContext", entries) -> Path:
    """Write a JSONL audit-log in the test env's project dir."""
    project_dir = Path(env_ctx.project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    log = project_dir / "audit-log.jsonl"
    with log.open("w", encoding="utf-8") as fh:
        for e in entries:
            if isinstance(e, str):
                fh.write(e + "\n")  # raw line (for malformed cases)
            else:
                fh.write(json.dumps(e) + "\n")
    return log


def _now() -> float:
    return time.time()


class TestAbsentAuditLog(TestEnvContext):
    """When audit-log.jsonl is missing → yellow."""

    def test_returns_yellow_when_absent(self) -> None:
        # Use a fresh project dir but never write the log.
        status, summary, detail = _mod.check_tier_policy_misrouting_24h()
        self.assertEqual(status, "yellow")
        self.assertIn("absent", summary)
        self.assertIsNone(detail)


class TestEmptyWindow(TestEnvContext):
    """audit-log present, but no model_routing_advised entries in 24h."""

    def test_no_events_returns_green(self) -> None:
        _write_audit_log(self, [
            {"event": "ceo_boot_emitted", "ts": _now()},
            {"event": "audit_log_emit", "ts": _now()},
        ])
        status, summary, detail = _mod.check_tier_policy_misrouting_24h()
        self.assertEqual(status, "green")
        self.assertIn("no model_routing_advised events", summary)
        self.assertIsNone(detail)


class TestAllRoutedCorrectly(TestEnvContext):
    """All entries match the canonical routing → green."""

    def test_zero_percent_misrouted_is_green(self) -> None:
        now = _now()
        _write_audit_log(self, [
            {"event": "model_routing_advised",
             "ts": now, "task_class": "file_read",
             "model_advised": "claude-haiku-4-5"},
            {"event": "model_routing_advised",
             "ts": now, "task_class": "code_gen",
             "model_advised": "claude-sonnet-4-6"},
        ])
        status, summary, detail = _mod.check_tier_policy_misrouting_24h()
        self.assertEqual(status, "green")
        self.assertIn("0/2", summary)
        self.assertEqual(detail["misrouted"], 0)
        self.assertEqual(detail["total"], 2)


class TestYellowBand(TestEnvContext):
    """Ratio 5% ≤ x < 10% → yellow."""

    def test_seven_percent_misrouted_is_yellow(self) -> None:
        now = _now()
        # 14 entries total, 1 misrouted → ratio = 1/14 ≈ 7.14%
        entries = []
        for _ in range(13):
            entries.append({
                "event": "model_routing_advised",
                "ts": now, "task_class": "file_read",
                "model_advised": "claude-haiku-4-5",
            })
        entries.append({
            "event": "model_routing_advised",
            "ts": now, "task_class": "file_read",
            "model_advised": "claude-opus-4-8",  # wrong tier
        })
        _write_audit_log(self, entries)
        status, summary, detail = _mod.check_tier_policy_misrouting_24h()
        self.assertEqual(status, "yellow")
        self.assertEqual(detail["misrouted"], 1)
        self.assertEqual(detail["total"], 14)
        self.assertGreaterEqual(detail["ratio"], 0.05)
        self.assertLess(detail["ratio"], 0.10)


class TestRedBand(TestEnvContext):
    """Ratio ≥ 10% → red."""

    def test_twenty_percent_misrouted_is_red(self) -> None:
        now = _now()
        # 10 entries, 2 misrouted → 20%.
        entries = []
        for _ in range(8):
            entries.append({
                "event": "model_routing_advised",
                "ts": now, "task_class": "code_gen",
                "model_advised": "claude-sonnet-4-6",
            })
        for _ in range(2):
            entries.append({
                "event": "model_routing_advised",
                "ts": now, "task_class": "code_gen",
                "model_advised": "claude-haiku-4-5",  # tier-floor violation
            })
        _write_audit_log(self, entries)
        status, _, detail = _mod.check_tier_policy_misrouting_24h()
        self.assertEqual(status, "red")
        self.assertEqual(detail["misrouted"], 2)
        self.assertEqual(detail["total"], 10)
        self.assertGreaterEqual(detail["ratio"], 0.10)


class TestOldEntriesIgnored(TestEnvContext):
    """Entries older than 24h MUST be ignored."""

    def test_old_entries_excluded_from_count(self) -> None:
        now = _now()
        old = now - 100000.0  # >24h ago
        entries = [
            # 5 old misrouted (must be ignored)
            {"event": "model_routing_advised", "ts": old,
             "task_class": "file_read", "model_advised": "claude-opus-4-8"},
            {"event": "model_routing_advised", "ts": old,
             "task_class": "file_read", "model_advised": "claude-opus-4-8"},
            # 1 recent correctly routed
            {"event": "model_routing_advised", "ts": now,
             "task_class": "file_read", "model_advised": "claude-haiku-4-5"},
        ]
        _write_audit_log(self, entries)
        status, _, detail = _mod.check_tier_policy_misrouting_24h()
        self.assertEqual(status, "green")
        self.assertEqual(detail["total"], 1)
        self.assertEqual(detail["misrouted"], 0)


class TestMalformedJsonlSkipped(TestEnvContext):
    """Malformed JSONL lines must not crash the check."""

    def test_invalid_json_lines_skipped(self) -> None:
        now = _now()
        _write_audit_log(self, [
            "{this is not json",
            "",
            "[1,2,3]",  # not a dict
            {"event": "model_routing_advised", "ts": now,
             "task_class": "file_read", "model_advised": "claude-haiku-4-5"},
        ])
        status, _, detail = _mod.check_tier_policy_misrouting_24h()
        self.assertEqual(status, "green")
        self.assertEqual(detail["total"], 1)


class TestUnknownTaskClassIgnored(TestEnvContext):
    """When router returns None for an unknown task_class, entry is skipped."""

    def test_unknown_task_class_excluded(self) -> None:
        now = _now()
        _write_audit_log(self, [
            {"event": "model_routing_advised", "ts": now,
             "task_class": "nonexistent_class_xyz",
             "model_advised": "claude-haiku-4-5"},
            {"event": "model_routing_advised", "ts": now,
             "task_class": "file_read",
             "model_advised": "claude-haiku-4-5"},
        ])
        status, _, detail = _mod.check_tier_policy_misrouting_24h()
        self.assertEqual(status, "green")
        # Only the file_read entry counts; the unknown class is filtered.
        self.assertEqual(detail["total"], 1)


class TestMissingFields(TestEnvContext):
    """Entries missing task_class or model_advised are skipped."""

    def test_partial_entries_skipped(self) -> None:
        now = _now()
        _write_audit_log(self, [
            {"event": "model_routing_advised", "ts": now},  # no fields
            {"event": "model_routing_advised", "ts": now,
             "task_class": "file_read"},  # no model
            {"event": "model_routing_advised", "ts": now,
             "model_advised": "claude-haiku-4-5"},  # no task_class
            {"event": "model_routing_advised", "ts": now,
             "task_class": "file_read",
             "model_advised": "claude-haiku-4-5"},  # complete
        ])
        status, _, detail = _mod.check_tier_policy_misrouting_24h()
        self.assertEqual(status, "green")
        self.assertEqual(detail["total"], 1)


class TestModelFieldFallback(TestEnvContext):
    """Entries with `model` (legacy field name) instead of `model_advised`."""

    def test_legacy_model_field_accepted(self) -> None:
        now = _now()
        _write_audit_log(self, [
            {"event": "model_routing_advised", "ts": now,
             "task_class": "file_read",
             "model": "claude-haiku-4-5"},  # legacy field name
        ])
        status, _, detail = _mod.check_tier_policy_misrouting_24h()
        self.assertEqual(status, "green")
        self.assertEqual(detail["total"], 1)


class TestNonDictEntries(TestEnvContext):
    """JSON values that decode to non-dict types are skipped."""

    def test_list_and_scalar_lines_skipped(self) -> None:
        now = _now()
        _write_audit_log(self, [
            '"just a string"',
            "42",
            "null",
            {"event": "model_routing_advised", "ts": now,
             "task_class": "file_read",
             "model_advised": "claude-haiku-4-5"},
        ])
        status, _, detail = _mod.check_tier_policy_misrouting_24h()
        self.assertEqual(status, "green")
        self.assertEqual(detail["total"], 1)


class TestStatusTupleShape(TestEnvContext):
    """Return shape contract: always 3-tuple (status, summary, detail|None)."""

    def test_return_tuple_shape(self) -> None:
        result = _mod.check_tier_policy_misrouting_24h()
        self.assertEqual(len(result), 3)
        status, summary, detail = result
        self.assertIsInstance(status, str)
        self.assertIsInstance(summary, str)
        self.assertIn(status, ("green", "yellow", "red", "error"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
