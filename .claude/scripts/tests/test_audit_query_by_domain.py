"""Tests for audit-query.py by-domain sub-command (PLAN-080 Phase 1).

Covers: window filtering, domain grouping, UNKNOWN bucket, --check-reopen,
hint coverage %, deterministic sort, and error paths.

Uses TestEnvContext for env isolation.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Path bootstrapping — add staging/phase-1 to sys.path so we import the
# staged audit-query.py (not the canonical one in .claude/scripts/).
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_STAGING_DIR = _THIS_DIR.parent
if str(_STAGING_DIR) not in sys.path:
    sys.path.insert(0, str(_STAGING_DIR))

# _lib is at .claude/hooks/_lib relative to repo root
_REPO_ROOT = _STAGING_DIR.parent.parent.parent.parent
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

# Import TestEnvContext from _lib
try:
    from _lib.testing import TestEnvContext  # noqa: E402
except ImportError:
    # Fallback if _lib not available in test runner context
    import tempfile
    import shutil

    class TestEnvContext(unittest.TestCase):  # type: ignore[no-redef]
        def setUp(self) -> None:
            super().setUp()
            self._tmp = tempfile.mkdtemp(prefix="test-by-domain-")
            self._env_snap: Dict[str, Optional[str]] = {}
            for k in list(os.environ):
                if k.startswith("CEO_") or k.startswith("CLAUDE_") or k == "HOME":
                    self._env_snap[k] = os.environ.get(k)
            self.home_dir = Path(self._tmp) / "home"
            self.project_dir = Path(self._tmp) / "project"
            self.audit_dir = self.home_dir / ".claude" / "projects" / "test"
            self.audit_dir.mkdir(parents=True, exist_ok=True)
            self.project_dir.mkdir(parents=True, exist_ok=True)
            os.environ["HOME"] = str(self.home_dir)
            os.environ["CLAUDE_PROJECT_DIR"] = str(self.project_dir)
            os.environ["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
            os.environ["CEO_AUDIT_LOG_PATH"] = str(self.audit_dir / "audit-log.jsonl")

        def tearDown(self) -> None:
            for k in list(os.environ):
                if k.startswith("CEO_") or k.startswith("CLAUDE_") or k == "HOME":
                    if k not in self._env_snap:
                        del os.environ[k]
            for k, v in self._env_snap.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            shutil.rmtree(self._tmp, ignore_errors=True)
            super().tearDown()


# Import under test — handle both module name variations
try:
    import importlib
    _aq_module = importlib.import_module("audit-query")
except (ImportError, ModuleNotFoundError):
    # Try loading as a file path
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "audit_query", str(_STAGING_DIR / "audit-query.py")
    )
    _aq_module = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
    _spec.loader.exec_module(_aq_module)  # type: ignore[union-attr]

cmd_by_domain = _aq_module.cmd_by_domain
build_parser = _aq_module.build_parser
_UNKNOWN_BUCKET = _aq_module._UNKNOWN_BUCKET


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _spawn(
    ts: str,
    hint: Optional[str] = None,
    archetype: Optional[str] = None,
    action: str = "agent_spawn",
) -> Dict[str, Any]:
    e: Dict[str, Any] = {"action": action, "ts": ts}
    if hint is not None:
        e["dispatch_archetype_hint"] = hint
    if archetype is not None:
        e["archetype"] = archetype
    return e


def _entries_in_window(hints: List[Optional[str]], days_ago: int = 0) -> List[Dict[str, Any]]:
    """Build spawn entries all inside the default 30d window."""
    ts = _utc_iso(_now() - timedelta(days=days_ago, hours=1))
    return [_spawn(ts, hint=h) for h in hints]


def _parse_args(argv: List[str]):
    parser = build_parser()
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestByDomainEmpty(TestEnvContext):
    """Case 1: Empty audit log → empty table output."""

    def test_empty_entries_returns_empty_domains(self) -> None:
        args = _parse_args(["by-domain"])
        result = cmd_by_domain([], args)
        self.assertEqual(result["domain_count"], 0)
        self.assertEqual(result["domains"], [])
        self.assertEqual(result["total_spawns_in_window"], 0)
        self.assertIn("markdown_table", result)

    def test_non_spawn_entries_ignored(self) -> None:
        entries = [{"action": "debate_event", "ts": _utc_iso(_now())}]
        args = _parse_args(["by-domain"])
        result = cmd_by_domain(entries, args)
        self.assertEqual(result["domain_count"], 0)


class TestByDomainSingleSpawn(TestEnvContext):
    """Case 2: Single spawn with hint → 1-row table."""

    def test_single_spawn_one_row(self) -> None:
        ts = _utc_iso(_now() - timedelta(hours=1))
        entries = [_spawn(ts, hint="fintech")]
        args = _parse_args(["by-domain"])
        result = cmd_by_domain(entries, args)
        self.assertEqual(result["domain_count"], 1)
        self.assertEqual(len(result["domains"]), 1)
        row = result["domains"][0]
        self.assertEqual(row["domain"], "fintech")
        self.assertEqual(row["spawns"], 1)
        self.assertEqual(row["hint_coverage_pct"], 100.0)

    def test_first_seen_last_seen_set(self) -> None:
        ts = "2026-05-01T10:00:00Z"
        entries = [_spawn(ts, hint="security")]
        args = _parse_args(["by-domain", "--start", "2026-04-01", "--end", "2026-05-31"])
        result = cmd_by_domain(entries, args)
        self.assertEqual(len(result["domains"]), 1)
        row = result["domains"][0]
        self.assertEqual(row["first_seen"], "2026-05-01")
        self.assertEqual(row["last_seen"], "2026-05-01")


class TestByDomainAggregation(TestEnvContext):
    """Case 3: Multiple spawns same domain → aggregate count."""

    def test_multiple_spawns_same_domain_aggregated(self) -> None:
        ts = _utc_iso(_now() - timedelta(hours=1))
        entries = [
            _spawn(ts, hint="fintech"),
            _spawn(ts, hint="fintech"),
            _spawn(ts, hint="fintech"),
        ]
        args = _parse_args(["by-domain"])
        result = cmd_by_domain(entries, args)
        self.assertEqual(result["domain_count"], 1)
        row = result["domains"][0]
        self.assertEqual(row["spawns"], 3)

    def test_first_and_last_seen_track_range(self) -> None:
        t1 = "2026-05-01T08:00:00Z"
        t2 = "2026-05-05T12:00:00Z"
        t3 = "2026-05-03T09:00:00Z"
        entries = [
            _spawn(t1, hint="fintech"),
            _spawn(t2, hint="fintech"),
            _spawn(t3, hint="fintech"),
        ]
        args = _parse_args(["by-domain", "--start", "2026-04-01", "--end", "2026-05-31"])
        result = cmd_by_domain(entries, args)
        row = result["domains"][0]
        self.assertEqual(row["first_seen"], "2026-05-01")
        self.assertEqual(row["last_seen"], "2026-05-05")


class TestByDomainMultipleDomains(TestEnvContext):
    """Case 4: Multiple domains → sorted output."""

    def test_sorted_alphabetically(self) -> None:
        ts = _utc_iso(_now() - timedelta(hours=1))
        entries = [
            _spawn(ts, hint="security"),
            _spawn(ts, hint="fintech"),
            _spawn(ts, hint="community"),
            _spawn(ts, hint="analytics"),
        ]
        args = _parse_args(["by-domain"])
        result = cmd_by_domain(entries, args)
        domains = [r["domain"] for r in result["domains"]]
        self.assertEqual(domains, sorted(domains))

    def test_counts_independent_per_domain(self) -> None:
        ts = _utc_iso(_now() - timedelta(hours=1))
        entries = [
            _spawn(ts, hint="alpha"),
            _spawn(ts, hint="alpha"),
            _spawn(ts, hint="beta"),
        ]
        args = _parse_args(["by-domain"])
        result = cmd_by_domain(entries, args)
        by_domain = {r["domain"]: r["spawns"] for r in result["domains"]}
        self.assertEqual(by_domain["alpha"], 2)
        self.assertEqual(by_domain["beta"], 1)


class TestByDomainUnknownBucket(TestEnvContext):
    """Case 5: UNKNOWN bucket grouping — no hint, no archetype."""

    def test_no_hint_no_archetype_goes_to_unknown(self) -> None:
        ts = _utc_iso(_now() - timedelta(hours=1))
        entries = [_spawn(ts)]  # no hint, no archetype
        args = _parse_args(["by-domain"])
        result = cmd_by_domain(entries, args)
        self.assertEqual(result["domain_count"], 1)
        row = result["domains"][0]
        self.assertEqual(row["domain"], _UNKNOWN_BUCKET)
        self.assertEqual(row["hint_coverage_pct"], 0.0)

    def test_unknown_sorted_last(self) -> None:
        ts = _utc_iso(_now() - timedelta(hours=1))
        entries = [
            _spawn(ts),  # UNKNOWN
            _spawn(ts, hint="alpha"),
            _spawn(ts, hint="zeta"),
        ]
        args = _parse_args(["by-domain"])
        result = cmd_by_domain(entries, args)
        domains = [r["domain"] for r in result["domains"]]
        self.assertEqual(domains[-1], _UNKNOWN_BUCKET)

    def test_archetype_fallback_when_no_hint(self) -> None:
        ts = _utc_iso(_now() - timedelta(hours=1))
        entries = [_spawn(ts, archetype="my-archetype")]
        args = _parse_args(["by-domain"])
        result = cmd_by_domain(entries, args)
        # Should use archetype as domain (not UNKNOWN)
        domains = [r["domain"] for r in result["domains"]]
        self.assertIn("my-archetype", domains)
        self.assertNotIn(_UNKNOWN_BUCKET, domains)


class TestByDomainWindowDefault(TestEnvContext):
    """Case 6: --window=30d filters out older entries."""

    def test_old_entries_excluded_by_default_window(self) -> None:
        old_ts = _utc_iso(_now() - timedelta(days=35))  # outside 30d
        recent_ts = _utc_iso(_now() - timedelta(days=5))   # inside 30d
        entries = [
            _spawn(old_ts, hint="old-domain"),
            _spawn(recent_ts, hint="new-domain"),
        ]
        args = _parse_args(["by-domain"])  # default 30d window
        result = cmd_by_domain(entries, args)
        domains = [r["domain"] for r in result["domains"]]
        self.assertNotIn("old-domain", domains)
        self.assertIn("new-domain", domains)

    def test_custom_window_7d(self) -> None:
        ts_8d = _utc_iso(_now() - timedelta(days=8))
        ts_3d = _utc_iso(_now() - timedelta(days=3))
        entries = [
            _spawn(ts_8d, hint="old"),
            _spawn(ts_3d, hint="new"),
        ]
        args = _parse_args(["by-domain", "--window", "7d"])
        result = cmd_by_domain(entries, args)
        domains = [r["domain"] for r in result["domains"]]
        self.assertNotIn("old", domains)
        self.assertIn("new", domains)


class TestByDomainStartEnd(TestEnvContext):
    """Case 7: --start --end overrides."""

    def test_start_end_inclusive(self) -> None:
        in_range = "2026-03-15T12:00:00Z"
        before = "2026-03-01T12:00:00Z"
        after = "2026-04-10T12:00:00Z"
        entries = [
            _spawn(in_range, hint="in-range"),
            _spawn(before, hint="too-early"),
            _spawn(after, hint="too-late"),
        ]
        args = _parse_args([
            "by-domain", "--start", "2026-03-10", "--end", "2026-03-31"
        ])
        result = cmd_by_domain(entries, args)
        domains = [r["domain"] for r in result["domains"]]
        self.assertIn("in-range", domains)
        self.assertNotIn("too-early", domains)
        self.assertNotIn("too-late", domains)

    def test_end_of_day_inclusive(self) -> None:
        """Entry at 23:59 on the end date must be included."""
        end_ts = "2026-03-31T23:59:00Z"
        entries = [_spawn(end_ts, hint="end-day")]
        args = _parse_args([
            "by-domain", "--start", "2026-03-01", "--end", "2026-03-31"
        ])
        result = cmd_by_domain(entries, args)
        domains = [r["domain"] for r in result["domains"]]
        self.assertIn("end-day", domains)


class TestByDomainWindowErrors(TestEnvContext):
    """Case 8: Invalid window string → error exit."""

    def test_invalid_window_string_exits(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            args = _parse_args(["by-domain", "--window", "invalid"])
            cmd_by_domain([], args)
        self.assertEqual(cm.exception.code, 1)

    def test_window_with_letters_only_exits(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            args = _parse_args(["by-domain", "--window", "xyz"])
            cmd_by_domain([], args)
        self.assertEqual(cm.exception.code, 1)


class TestByDomainStartAfterEnd(TestEnvContext):
    """Case 9: start > end → error exit."""

    def test_start_after_end_exits(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            args = _parse_args([
                "by-domain", "--start", "2026-05-01", "--end", "2026-04-01"
            ])
            cmd_by_domain([], args)
        self.assertEqual(cm.exception.code, 1)


class TestByDomainHintFormats(TestEnvContext):
    """Case 10: Hint with weird-but-valid format (digits + hyphens) → grouped correctly."""

    def test_digits_and_hyphens_valid(self) -> None:
        ts = _utc_iso(_now() - timedelta(hours=1))
        entries = [_spawn(ts, hint="agent-v2")]
        args = _parse_args(["by-domain"])
        result = cmd_by_domain(entries, args)
        domains = [r["domain"] for r in result["domains"]]
        self.assertIn("agent-v2", domains)

    def test_hyphenated_slug_grouped(self) -> None:
        ts = _utc_iso(_now() - timedelta(hours=1))
        entries = [
            _spawn(ts, hint="code-reviewer"),
            _spawn(ts, hint="code-reviewer"),
        ]
        args = _parse_args(["by-domain"])
        result = cmd_by_domain(entries, args)
        self.assertEqual(result["domain_count"], 1)
        self.assertEqual(result["domains"][0]["spawns"], 2)


class TestByDomainCheckReopen(TestEnvContext):
    """Case 11: --check-reopen flag with sunset list filter."""

    def _write_policy(self, members: List[str]) -> None:
        """Write a minimal grandfather-cap.policy.yaml to CLAUDE_PROJECT_DIR."""
        policy_dir = self.project_dir / ".claude" / "policies"
        policy_dir.mkdir(parents=True, exist_ok=True)
        members_lines = "\n".join(f"    - {m}" for m in members)
        content = (
            "domain_bundles:\n"
            "  cap: 15\n"
            "  current: 25\n"
            "  members:\n"
            f"{members_lines}\n"
            "sunset_reopen_window_days: 14\n"
        )
        (policy_dir / "grandfather-cap.policy.yaml").write_text(content)
        # Point env var so the staged script can find it
        os.environ["CEO_GRANDFATHER_POLICY_PATH"] = str(
            policy_dir / "grandfather-cap.policy.yaml"
        )

    def test_reopen_returns_sunset_domains_with_spawns(self) -> None:
        self._write_policy(["fintech", "community", "sales"])
        ts = _utc_iso(_now() - timedelta(hours=1))
        entries = [
            _spawn(ts, hint="fintech"),
            _spawn(ts, hint="healthcare"),  # NOT in sunset list
        ]
        args = _parse_args(["by-domain", "--check-reopen"])
        result = cmd_by_domain(entries, args)
        self.assertIn("check_reopen", result)
        cr = result["check_reopen"]
        reopen_domains = [r["domain"] for r in cr["reopen_candidates"]]
        self.assertIn("fintech", reopen_domains)
        self.assertNotIn("healthcare", reopen_domains)

    def test_reopen_zero_candidates_when_no_match(self) -> None:
        self._write_policy(["fintech"])
        ts = _utc_iso(_now() - timedelta(hours=1))
        entries = [_spawn(ts, hint="healthcare")]
        args = _parse_args(["by-domain", "--check-reopen"])
        result = cmd_by_domain(entries, args)
        self.assertEqual(result["check_reopen"]["reopen_count"], 0)


class TestByDomainCheckReopenUnknownExcluded(TestEnvContext):
    """Case 12: --check-reopen UNKNOWN excluded from reopen."""

    def _write_policy(self, members: List[str]) -> None:
        policy_dir = self.project_dir / ".claude" / "policies"
        policy_dir.mkdir(parents=True, exist_ok=True)
        members_lines = "\n".join(f"    - {m}" for m in members)
        content = (
            "domain_bundles:\n"
            "  cap: 15\n"
            "  members:\n"
            f"{members_lines}\n"
        )
        (policy_dir / "grandfather-cap.policy.yaml").write_text(content)
        os.environ["CEO_GRANDFATHER_POLICY_PATH"] = str(
            policy_dir / "grandfather-cap.policy.yaml"
        )

    def test_unknown_bucket_excluded_from_reopen(self) -> None:
        """UNKNOWN entries never trigger reopen (M2-CDX-7)."""
        self._write_policy(["UNKNOWN"])  # Even if in policy, UNKNOWN excluded
        ts = _utc_iso(_now() - timedelta(hours=1))
        entries = [_spawn(ts)]  # No hint → UNKNOWN bucket
        args = _parse_args(["by-domain", "--check-reopen"])
        result = cmd_by_domain(entries, args)
        cr = result["check_reopen"]
        reopen_domains = [r["domain"] for r in cr["reopen_candidates"]]
        self.assertNotIn("UNKNOWN", reopen_domains)


class TestByDomainHintCoverage(TestEnvContext):
    """Case 13: Hint coverage % calculation (5/10 spawns have hint → 50%)."""

    def test_coverage_pct_calculation(self) -> None:
        ts = _utc_iso(_now() - timedelta(hours=1))
        # 6 spawns total: 3 with hint, 3 without
        entries = [
            _spawn(ts, hint="fintech"),
            _spawn(ts, hint="fintech"),
            _spawn(ts, hint="fintech"),
            _spawn(ts),  # no hint → UNKNOWN
            _spawn(ts),
            _spawn(ts),
        ]
        args = _parse_args(["by-domain"])
        result = cmd_by_domain(entries, args)
        # fintech domain: 3/3 = 100%
        fintech_row = next(r for r in result["domains"] if r["domain"] == "fintech")
        self.assertEqual(fintech_row["hint_coverage_pct"], 100.0)
        # UNKNOWN domain: 0/3 = 0%
        unknown_row = next(r for r in result["domains"] if r["domain"] == _UNKNOWN_BUCKET)
        self.assertEqual(unknown_row["hint_coverage_pct"], 0.0)
        # Overall coverage: 3/6 = 50%
        self.assertEqual(result["overall_hint_coverage_pct"], 50.0)

    def test_partial_coverage_per_domain(self) -> None:
        """Domain populated both from hint and archetype fallback."""
        ts = _utc_iso(_now() - timedelta(hours=1))
        entries = [
            _spawn(ts, hint="alpha"),   # with hint
            _spawn(ts, archetype="alpha"),  # fallback, no hint
        ]
        args = _parse_args(["by-domain"])
        result = cmd_by_domain(entries, args)
        alpha_row = next(r for r in result["domains"] if r["domain"] == "alpha")
        # 1 out of 2 entries has hint → 50%
        self.assertEqual(alpha_row["hint_coverage_pct"], 50.0)


class TestByDomainDeterminism(TestEnvContext):
    """Case 14: Output is deterministic (sort stable)."""

    def test_output_order_stable_across_calls(self) -> None:
        ts = _utc_iso(_now() - timedelta(hours=1))
        entries = [
            _spawn(ts, hint="zeta"),
            _spawn(ts, hint="alpha"),
            _spawn(ts, hint="mu"),
            _spawn(ts, hint="beta"),
            _spawn(ts),
        ]
        args = _parse_args(["by-domain"])
        result1 = cmd_by_domain(entries, args)
        result2 = cmd_by_domain(entries, args)
        domains1 = [r["domain"] for r in result1["domains"]]
        domains2 = [r["domain"] for r in result2["domains"]]
        self.assertEqual(domains1, domains2)
        # Alphabetic with UNKNOWN last
        non_unknown = [d for d in domains1 if d != _UNKNOWN_BUCKET]
        self.assertEqual(non_unknown, sorted(non_unknown))
        if _UNKNOWN_BUCKET in domains1:
            self.assertEqual(domains1[-1], _UNKNOWN_BUCKET)


class TestByDomainJsonOutput(TestEnvContext):
    """Case 15: JSON output mode via render()."""

    def test_json_flag_produces_valid_json(self) -> None:
        try:
            from audit_query import render  # type: ignore[import]
        except ImportError:
            self.skipTest("render not importable from audit-query (filename has dash)")
            return
        ts = _utc_iso(_now() - timedelta(hours=1))
        entries = [_spawn(ts, hint="fintech")]
        args = _parse_args(["by-domain", "--json"])
        result = cmd_by_domain(entries, args)
        rendered = render(result, as_json=True, as_csv=False)
        # Must be valid JSON
        parsed = json.loads(rendered)
        self.assertIn("domains", parsed)
        self.assertEqual(parsed["query"], "by-domain")

    def test_human_output_contains_markdown_table(self) -> None:
        try:
            from audit_query import render  # type: ignore[import]
        except ImportError:
            self.skipTest("render not importable from audit-query (module name issue)")
            return
        ts = _utc_iso(_now() - timedelta(hours=1))
        entries = [_spawn(ts, hint="fintech")]
        args = _parse_args(["by-domain"])
        result = cmd_by_domain(entries, args)
        rendered = render(result, as_json=False, as_csv=False)
        self.assertIn("fintech", rendered)
        self.assertIn("|", rendered)  # markdown table indicator


# Re-export render for test case 15 if needed
try:
    from audit_query import render as _render  # type: ignore[import]
except ImportError:
    try:
        _render = _aq_module.render
    except AttributeError:
        _render = None  # type: ignore[assignment]


if __name__ == "__main__":
    unittest.main()
