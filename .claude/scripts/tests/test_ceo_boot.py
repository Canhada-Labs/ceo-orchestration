"""test_ceo_boot.py — PLAN-065 Phase 3 production tests for ceo-boot.py.

Coverage map (subset of PLAN-065 §4.3.6 floor 102; this MVP delivers ~30 of
the 102 covering the critical paths. Remaining 72 deferred to PLAN-067
v1.13.0 + bundled with Phase 6 mutation harness):

- Per-check happy-path discovery (15 Tier-S checks present in registry)
- Dispatcher timeout-fallback + ceo_boot_check_skipped emit
- Format outputs --short / --verbose / --json structural shape
- Idempotency contract (back-to-back deterministic mod timestamps)
- Audit emit ceo_boot_emitted whitelist contract (deferred to v1.12.0 ceremony)
- Recommendations engine: deterministic ordering + cap at 5 + sanitization
- --cached mode: cache-hit / cache-miss paths
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import time
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

# TestEnvContext (S79 hygiene lesson — every test uses isolated env)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "ceo-boot.py"


def _load_module():
    """Load ceo-boot.py as importable module."""
    spec = importlib.util.spec_from_file_location("ceo_boot", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ceo_boot"] = mod
    spec.loader.exec_module(mod)
    return mod


# Loaded once for the suite
_mod = _load_module()


class TestRegistry(TestEnvContext):
    """Tier-S check registry presence + naming."""

    def test_registry_has_21_tier_s_checks(self):
        # PLAN-091 Wave A.1: bumped 15 → 16 (tier_policy_misrouting_24h).
        # PLAN-093 Wave C.2 / C.5: bumped 16 → 17 → 18 (cache_discipline_alerted,
        # ceo_boot_persona_coverage_score).
        # S127 cadence-amendment: bumped 18 → 19 (persona_atrophy_7d companion
        # at 168h cadence, Codex R2 `019e33a3` AMEND).
        # PLAN-106 Wave F: 20 Tier-S checks (was 19; added confidence_gate_drift_7d).
        # PLAN-135 W1 S3: 21 Tier-S checks (added settings_tamper_tripwires).
        self.assertEqual(len(_mod.TIER_S_CHECKS), 23)  # PLAN-153 Wave E: +2 (failopen_rail_liveness_7d, harness_config_gate)

    def test_tier_policy_misrouting_check_present(self):
        # PLAN-091 Wave A.1: 16th Tier-S check registered.
        names = [name for name, _ in _mod.TIER_S_CHECKS]
        self.assertIn("tier_policy_misrouting_24h", names)

    def test_registry_names_unique(self):
        names = [name for name, _ in _mod.TIER_S_CHECKS]
        self.assertEqual(len(names), len(set(names)))

    def test_registry_callables_defined(self):
        for name, fn in _mod.TIER_S_CHECKS:
            self.assertTrue(callable(fn), f"{name} not callable")

    def test_per_check_timeout_default_1s(self):
        # Codex S82 P0 #1 fix: was 0.5s (insufficient for governance_validate ~1.78s);
        # now 1.0 default + per-check overrides dict for slower subprocess-bound checks.
        self.assertEqual(_mod.PER_CHECK_TIMEOUT_S, 1.0)

    def test_per_check_timeout_overrides_governance_fast_2s(self):
        # PLAN-082 Codex Item A: governance_validate now dispatches the fast
        # --json profile (~40-200ms warm). 2.0s ceiling preserved for
        # cold-start bash + python3 spawn variance on adopter machines.
        self.assertGreaterEqual(
            _mod.PER_CHECK_TIMEOUT_OVERRIDES_S.get("governance_validate", 0), 1.5
        )
        self.assertLessEqual(
            _mod.PER_CHECK_TIMEOUT_OVERRIDES_S.get("governance_validate", 99), 2.5
        )

    def test_hook_live_smoke_in_registry(self):
        # PLAN-082 Codex Item D: hook_test_baseline replaced with hook_live_smoke.
        names = [name for name, _ in _mod.TIER_S_CHECKS]
        self.assertIn("hook_live_smoke", names)
        self.assertNotIn("hook_test_baseline", names)

    def test_sentinel_cutoff_epoch_2026_04_22(self):
        # Codex S82 P2 fix: cutoff = 2026-04-22 00:00:00 UTC = 1776816000
        # (was 1776297600 = 2026-04-16, off by 6 days)
        self.assertEqual(_mod.SENTINEL_CUTOFF_EPOCH, 1776816000)

    def test_aggregate_timeout_5s(self):
        self.assertEqual(_mod.AGGREGATE_TIMEOUT_S, 5.0)


class TestDispatcher(TestEnvContext):
    """Dispatcher contract: parallel + timeout fallback + emit."""

    def test_dispatch_returns_check_results(self):
        results = _mod.dispatch_parallel()
        # PLAN-106 Wave F: 20 Tier-S checks (was 19; added confidence_gate_drift_7d).
        # PLAN-135 W1 S3: 21 Tier-S checks (added settings_tamper_tripwires).
        self.assertEqual(len(results), 23)  # PLAN-153 Wave E: +2 (failopen_rail_liveness_7d, harness_config_gate)
        for r in results:
            self.assertIsInstance(r, _mod.CheckResult)
            self.assertIn(r.status, ("green", "yellow", "red", "timeout", "error"))

    def test_dispatch_records_durations(self):
        results = _mod.dispatch_parallel()
        for r in results:
            # Allow up to PER_CHECK_TIMEOUT_S * 1000 + small slack
            self.assertGreaterEqual(r.duration_ms, 0.0)
            self.assertLess(r.duration_ms, 5500.0)  # aggregate cap with margin

    def test_dispatch_fits_aggregate_budget(self):
        t0 = time.perf_counter()
        _mod.dispatch_parallel()
        elapsed = time.perf_counter() - t0
        # 5s aggregate + 1s slack for CI cold-start
        self.assertLess(elapsed, 6.0)

    def test_aggregate_timeout_renders_timeout_status(self):
        """Codex S82 P0 #2 fix: per-check timeout was fictional (sequential
        as_completed iteration). Now uses aggregate budget; checks that
        exceed AGGREGATE_TIMEOUT_S are marked timeout.

        Slow check exceeding 5s aggregate MUST get status='timeout'.
        Annotation 'slow' (not timeout) for green checks under aggregate
        but over per-check soft ceiling.
        """
        def slow_check():
            time.sleep(6.0)  # exceeds 5s aggregate
            return ("green", "should not appear", None)

        original_registry = list(_mod.TIER_S_CHECKS)
        try:
            _mod.TIER_S_CHECKS.clear()
            _mod.TIER_S_CHECKS.extend([("slow_check", slow_check)])
            results = _mod.dispatch_parallel()
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].status, "timeout")
            self.assertIn("AGG_TIMEOUT", results[0].summary)
        finally:
            _mod.TIER_S_CHECKS.clear()
            _mod.TIER_S_CHECKS.extend(original_registry)

    def test_results_returned_in_registry_order(self):
        """Codex S82 post-patch fix: results must be in TIER_S_CHECKS
        registry order (CR-N7 deterministic), not completion order."""
        results = _mod.dispatch_parallel()
        registry_names = [name for name, _ in _mod.TIER_S_CHECKS]
        result_names = [r.name for r in results]
        self.assertEqual(result_names, registry_names)


class TestSkillUnknownGhostFilter(TestEnvContext):
    """S86 follow-up: harness ghost-events (empty PostToolUse on Agent calls
    with no payload) must NOT inflate skill_unknown_ratio denominator.

    Ghost signature = ALL FOUR: desc_preview=='' AND rail is None AND
    has_profile is False AND desc_hash==SHA256(b'').
    """

    EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_is_ghost_all_four_match(self):
        ev = {
            "action": "agent_spawn",
            "desc_preview": "",
            "rail": None,
            "has_profile": False,
            "desc_hash": self.EMPTY_SHA,
        }
        self.assertTrue(_mod._is_ghost_spawn_event(ev))

    def test_is_ghost_legitimate_dispatch_not_filtered(self):
        # Real near-empty dispatch must NOT match — even with empty desc, if
        # rail is set OR has_profile is True OR desc_hash differs, it's real.
        for variant in [
            {"desc_preview": "", "rail": "claude", "has_profile": False,
             "desc_hash": self.EMPTY_SHA},
            {"desc_preview": "", "rail": None, "has_profile": True,
             "desc_hash": self.EMPTY_SHA},
            {"desc_preview": "real desc", "rail": None, "has_profile": False,
             "desc_hash": "0123456789abcdef" * 4},
            {"desc_preview": "", "rail": None, "has_profile": False,
             "desc_hash": "different_hash"},
        ]:
            self.assertFalse(_mod._is_ghost_spawn_event(variant), repr(variant))

    def test_skill_unknown_excludes_ghosts(self):
        # Inject events into iterator via monkey-patch.
        original = _mod._iter_audit_events_since
        def fake_iter(_h):
            yield {
                "action": "agent_spawn", "desc_preview": "", "rail": None,
                "has_profile": False, "desc_hash": self.EMPTY_SHA,
                "skill": "unknown",
            }
            yield {
                "action": "agent_spawn", "desc_preview": "real", "rail": "claude",
                "has_profile": True, "desc_hash": "abc",
                "skill": "security-and-auth",
            }
            yield {
                "action": "agent_spawn", "desc_preview": "real2", "rail": "claude",
                "has_profile": True, "desc_hash": "def",
                "skill": "unknown",
            }
        _mod._iter_audit_events_since = fake_iter
        try:
            status, summary, detail = _mod.check_skill_unknown_ratio()
            self.assertEqual(detail["total"], 2)        # ghost excluded
            self.assertEqual(detail["unknown"], 1)
            self.assertEqual(detail["ghosts_skipped"], 1)
            self.assertIn("1/2", summary)
        finally:
            _mod._iter_audit_events_since = original

    def test_skill_unknown_excludes_first_party_builtins(self):
        # S200: first-party Claude Code built-in agent types (claude,
        # claude-code-guide, statusline-setup) have no .claude/agents anchor
        # and so legitimately carry skill=unknown. They must NOT inflate the
        # ratio — only custom (skill-anchored) archetypes count as a gap.
        original = _mod._iter_audit_events_since

        def fake_iter(_h):
            for builtin in ("claude", "claude-code-guide", "statusline-setup"):
                yield {
                    "action": "agent_spawn", "desc_preview": "builtin",
                    "rail": None, "has_profile": False, "desc_hash": "x",
                    "skill": "unknown",
                    "subagent_type": builtin, "archetype": builtin,
                }
            # one real custom-archetype spawn carrying a skill — the denominator
            yield {
                "action": "agent_spawn", "desc_preview": "real", "rail": "claude",
                "has_profile": True, "desc_hash": "y", "skill": "security-and-auth",
                "subagent_type": "security-engineer", "archetype": "security-engineer",
            }

        _mod._iter_audit_events_since = fake_iter
        try:
            status, summary, detail = _mod.check_skill_unknown_ratio()
            self.assertEqual(detail["total"], 1)               # only the custom one
            self.assertEqual(detail["unknown"], 0)
            self.assertEqual(detail["skill_less_by_design"], 3)
            self.assertEqual(status, "green")
        finally:
            _mod._iter_audit_events_since = original


class TestGovernanceProbeFilter(TestEnvContext):
    """S239: governance self-test probes (`_probe_*` archetypes) are synthetic
    skill-less / zero-cache spawns. A single S237 A3 hook-parity probe pinned
    BOTH skill_unknown_ratio and cache_discipline_alerted to red on an idle
    window. They must be filtered from both detectors as test pollution.
    """

    def _probe_event(self, **over):
        ev = {
            "action": "agent_spawn",
            "archetype": "_probe_missing_skill",
            "subagent_type": "_probe_missing_skill",
            "skill": "unknown",
            "desc_preview": "A3 hook-parity probe",
            "rail": None,
            "has_profile": False,
            "desc_hash": "31ae39c5",
            "cache_coverage_bps": 0,
        }
        ev.update(over)
        return ev

    def test_is_test_pollution_matches_probe_archetype(self):
        self.assertTrue(_mod._is_test_pollution_event(self._probe_event()))
        # also matched via subagent_type alone
        self.assertTrue(
            _mod._is_test_pollution_event(
                {"action": "agent_spawn", "subagent_type": "_probe_canonical_edit"}
            )
        )

    def test_is_test_pollution_preserves_legacy_discriminant(self):
        self.assertTrue(_mod._is_test_pollution_event({"test": "bench"}))
        self.assertTrue(_mod._is_test_pollution_event({"test": "warmup"}))

    def test_is_test_pollution_real_dispatch_not_matched(self):
        # A real custom-archetype spawn must NOT be treated as pollution.
        self.assertFalse(
            _mod._is_test_pollution_event(
                {"action": "agent_spawn", "archetype": "security-engineer",
                 "subagent_type": "security-engineer", "skill": "security-and-auth"}
            )
        )

    def test_unregistered_probe_prefix_not_pollution(self):
        # Codex S239 P2: closed set, not prefix — a skill-less dispatch that
        # merely names itself `_probe_*` must NOT evade the governance detector.
        for spoof in ("_probe_evil", "_probe_", "_probe_real_dispatch"):
            self.assertFalse(
                _mod._is_test_pollution_event(
                    {"action": "agent_spawn", "archetype": spoof,
                     "subagent_type": spoof, "skill": "unknown"}
                ),
                spoof,
            )
        # All three REGISTERED probes are still recognized.
        for real in _mod._PROBE_ARCHETYPES:
            self.assertTrue(
                _mod._is_test_pollution_event({"archetype": real}), real
            )

    def test_skill_unknown_excludes_probe_only_window(self):
        original = _mod._iter_audit_events_since

        def fake_iter(_h):
            yield self._probe_event()

        _mod._iter_audit_events_since = fake_iter
        try:
            status, summary, detail = _mod.check_skill_unknown_ratio()
            self.assertEqual(detail["total"], 0)       # probe excluded → no gap
            self.assertEqual(detail["unknown"], 0)
            self.assertEqual(detail["test_pollution_skipped"], 1)
            self.assertEqual(status, "green")
        finally:
            _mod._iter_audit_events_since = original

    def test_cache_discipline_excludes_probe_only_window(self):
        original = _mod._iter_audit_events_since

        def fake_iter(hours=24.0):
            # ONLY a probe carrying cache_coverage_bps=0 — must not pin red.
            yield self._probe_event()

        _mod._iter_audit_events_since = fake_iter
        try:
            status, summary, detail = _mod.check_cache_discipline_alerted()
            self.assertEqual(status, "green")
            self.assertEqual(detail["samples"], 0)
            self.assertIn("no cache_coverage datapoints", summary)
        finally:
            _mod._iter_audit_events_since = original

    def test_cache_discipline_real_low_coverage_still_red(self):
        # Guard against over-broadening: a REAL agent_spawn with low coverage
        # must still trip the gate (probe filter must not mask genuine signal).
        original = _mod._iter_audit_events_since

        def fake_iter(hours=24.0):
            yield {"action": "agent_spawn", "archetype": "security-engineer",
                   "cache_coverage_bps": 1000}  # 0.10 < 0.70

        _mod._iter_audit_events_since = fake_iter
        try:
            status, summary, detail = _mod.check_cache_discipline_alerted()
            self.assertEqual(status, "red")
            self.assertEqual(detail["samples"], 1)
        finally:
            _mod._iter_audit_events_since = original


class TestSanitization(TestEnvContext):
    """Sec MF-4 input sanitization contract."""

    def test_sanitize_length_bound_200(self):
        long = "A" * 500
        out = _mod._sanitize_for_recs(long)
        self.assertLessEqual(len(out), 200)

    def test_sanitize_strips_html_brackets(self):
        out = _mod._sanitize_for_recs("hello <script>evil</script>")
        self.assertNotIn("<", out)
        self.assertNotIn(">", out)

    def test_sanitize_strips_backticks(self):
        out = _mod._sanitize_for_recs("hello `code`")
        self.assertNotIn("`", out)

    def test_sanitize_strips_markdown_link_url(self):
        out = _mod._sanitize_for_recs("see [text](http://evil.com)")
        self.assertNotIn("evil.com", out)
        self.assertIn("text", out)

    def test_sanitize_passthrough_safe(self):
        safe = "PLAN-073 Phase 3 ready"
        out = _mod._sanitize_for_recs(safe)
        self.assertEqual(out, safe)

    def test_sanitize_non_str_coerces(self):
        out = _mod._sanitize_for_recs(12345)  # type: ignore[arg-type]
        self.assertEqual(out, "12345")


class TestRecommendationsEngine(TestEnvContext):
    """Phase 3-D rule-based prioritizer."""

    def _ck(self, name, status, summary, detail=None):
        return _mod.CheckResult(name, status, summary, 10.0, detail)

    def test_empty_results_zero_recs(self):
        recs = _mod._make_recommendations([])
        self.assertEqual(recs, [])

    def test_all_green_zero_recs(self):
        results = [self._ck(name, "green", "ok") for name, _ in _mod.TIER_S_CHECKS]
        recs = _mod._make_recommendations(results)
        self.assertEqual(recs, [])

    def test_owner_sentinels_pending_surfaces(self):
        results = [
            self._ck("sentinels_pending_gpg", "yellow", "3 pending",
                     ["s1.md", "s2.md", "s3.md"]),
        ]
        recs = _mod._make_recommendations(results)
        self.assertEqual(len(recs), 1)
        self.assertIn("sentinel", recs[0].lower())
        self.assertIn("3", recs[0])

    def test_stranded_executing_surfaces(self):
        results = [
            self._ck("plans_stranded_executing", "red", "2 stranded",
                     ["PLAN-A", "PLAN-B"]),
        ]
        recs = _mod._make_recommendations(results)
        self.assertEqual(len(recs), 1)
        self.assertIn("stranded", recs[0].lower())

    def test_recs_capped_at_5(self):
        # Build inputs that would yield >5 recommendations
        results = [
            self._ck("sentinels_pending_gpg", "yellow", "1", ["s.md"]),
            self._ck("plans_stranded_executing", "red", "1", ["P"]),
            self._ck("skill_unknown_ratio", "red", "100%"),
            self._ck("audit_v3_backlog", "yellow", "1", ["X"]),
            self._ck("adrs_stale_proposed", "yellow", "1", ["ADR-X"]),
        ]
        recs = _mod._make_recommendations(results)
        self.assertLessEqual(len(recs), 5)

    def test_recs_deterministic_ordering(self):
        """CR-N7: --json must be stable across runs (lex-sort by category)."""
        results = [
            self._ck("adrs_stale_proposed", "yellow", "1", ["ADR-X"]),
            self._ck("sentinels_pending_gpg", "yellow", "1", ["s.md"]),
            self._ck("plans_stranded_executing", "red", "1", ["P"]),
        ]
        recs1 = _mod._make_recommendations(results)
        recs2 = _mod._make_recommendations(results)
        self.assertEqual(recs1, recs2)
        # Sentinel should be #1 (sort key 01-owner-sentinels)
        self.assertIn("sentinel", recs1[0].lower())

    def test_recs_sanitized(self):
        """Disk-sourced strings get sanitized before rendering."""
        evil = "PLAN-X<script>alert(1)</script>"
        results = [
            self._ck("plans_stranded_executing", "red", "1", [evil]),
        ]
        recs = _mod._make_recommendations(results)
        self.assertEqual(len(recs), 1)
        self.assertNotIn("<script>", recs[0])
        self.assertNotIn("</script>", recs[0])


class TestRenderer(TestEnvContext):
    """Output format contracts."""

    def _ck(self, name, status, summary, detail=None):
        return _mod.CheckResult(name, status, summary, 10.0, detail)

    def test_render_default_table(self):
        results = [self._ck(name, "green", "ok") for name, _ in _mod.TIER_S_CHECKS]
        out = _mod.render_digest(results, short=False)
        self.assertIn("| Check | Status |", out)
        self.assertIn("plans_executing", out)

    def test_render_short_counts(self):
        results = [self._ck(name, "green", "ok") for name, _ in _mod.TIER_S_CHECKS]
        out = _mod.render_digest(results, short=True)
        # PLAN-135 W1 S3: 21 Tier-S checks.
        self.assertIn("23 green", out)  # PLAN-153 Wave E: 23 Tier-S checks
        self.assertNotIn("| Check |", out)

    def test_render_short_surfaces_non_green(self):
        results = [
            self._ck("plans_executing", "red", "broken"),
            self._ck("audit_log_freshness", "green", "ok"),
        ]
        out = _mod.render_digest(results, short=True)
        self.assertIn("plans_executing: red", out)
        self.assertNotIn("audit_log_freshness: green", out)


class TestAuditLogFreshnessErrorsSidecar(TestEnvContext):
    """F-6.3 (PLAN-113 W7-OPS) — check_audit_log_freshness surfaces errors sidecar."""

    def setUp(self):
        super().setUp()
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self._tmpdir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()
        super().tearDown()

    def _write_audit_log(self) -> Path:
        p = _mod.AUDIT_LOG_DEFAULT.parent
        # Redirect AUDIT_LOG_DEFAULT to our tmp dir for this test.
        audit = self._tmpdir / "audit-log.jsonl"
        audit.write_text('{"action":"test"}\n')
        return audit

    def test_no_errors_sidecar_returns_green_when_fresh(self):
        """No errors sidecar → status governed by age alone."""
        audit = self._tmpdir / "audit-log.jsonl"
        audit.write_text("x")
        # Patch AUDIT_LOG_DEFAULT to point at our temp file.
        original = _mod.AUDIT_LOG_DEFAULT
        _mod.AUDIT_LOG_DEFAULT = audit
        os.environ["CEO_AUDIT_LOG_ERR"] = str(self._tmpdir / "audit-log.errors")
        try:
            status, summary, detail = _mod.check_audit_log_freshness()
        finally:
            _mod.AUDIT_LOG_DEFAULT = original
            os.environ.pop("CEO_AUDIT_LOG_ERR", None)
        self.assertIn(status, ("green", "yellow"))
        self.assertFalse(detail["errors_present"])
        self.assertEqual(detail["errors_line_count"], 0)

    def test_nonempty_errors_sidecar_returns_yellow(self):
        """Non-empty audit-log.errors → yellow regardless of audit-log age."""
        audit = self._tmpdir / "audit-log.jsonl"
        audit.write_text("x")
        errors = self._tmpdir / "audit-log.errors"
        errors.write_text("2026-05-25T00:00:00Z audit_emit: spool_writer FAIL\n" * 100)
        original = _mod.AUDIT_LOG_DEFAULT
        _mod.AUDIT_LOG_DEFAULT = audit
        os.environ["CEO_AUDIT_LOG_ERR"] = str(errors)
        try:
            status, summary, detail = _mod.check_audit_log_freshness()
        finally:
            _mod.AUDIT_LOG_DEFAULT = original
            os.environ.pop("CEO_AUDIT_LOG_ERR", None)
        self.assertEqual(status, "yellow")
        self.assertTrue(detail["errors_present"])
        self.assertEqual(detail["errors_line_count"], 100)
        self.assertIn("audit-log.errors", summary)

    def test_empty_errors_sidecar_does_not_trigger_yellow(self):
        """Zero-byte errors sidecar is treated as absent."""
        audit = self._tmpdir / "audit-log.jsonl"
        audit.write_text("x")
        errors = self._tmpdir / "audit-log.errors"
        errors.write_text("")  # empty
        original = _mod.AUDIT_LOG_DEFAULT
        _mod.AUDIT_LOG_DEFAULT = audit
        os.environ["CEO_AUDIT_LOG_ERR"] = str(errors)
        try:
            status, summary, detail = _mod.check_audit_log_freshness()
        finally:
            _mod.AUDIT_LOG_DEFAULT = original
            os.environ.pop("CEO_AUDIT_LOG_ERR", None)
        self.assertFalse(detail["errors_present"])

    def test_missing_audit_log_returns_yellow(self):
        """Missing audit-log.jsonl → yellow (original behavior preserved)."""
        original = _mod.AUDIT_LOG_DEFAULT
        _mod.AUDIT_LOG_DEFAULT = self._tmpdir / "nonexistent-audit-log.jsonl"
        try:
            status, summary, detail = _mod.check_audit_log_freshness()
        finally:
            _mod.AUDIT_LOG_DEFAULT = original
        self.assertEqual(status, "yellow")
        self.assertIn("missing", summary)

    def test_detail_always_contains_expected_keys(self):
        """detail dict always has errors_present + errors_line_count."""
        audit = self._tmpdir / "audit-log.jsonl"
        audit.write_text("x")
        original = _mod.AUDIT_LOG_DEFAULT
        _mod.AUDIT_LOG_DEFAULT = audit
        os.environ["CEO_AUDIT_LOG_ERR"] = str(self._tmpdir / "no-such.errors")
        try:
            _status, _summary, detail = _mod.check_audit_log_freshness()
        finally:
            _mod.AUDIT_LOG_DEFAULT = original
            os.environ.pop("CEO_AUDIT_LOG_ERR", None)
        self.assertIn("errors_present", detail)
        self.assertIn("errors_line_count", detail)
        self.assertIn("age_hours", detail)
        self.assertIn("size_mb", detail)


class TestMainCLI(TestEnvContext):
    """Top-level main() integration."""

    def test_main_short_returns_zero(self):
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = _mod.main(["--short"])
        self.assertEqual(rc, 0)
        # Codex S82 P1 fix: --short defaults cached path; output may show
        # "--cached HIT" or "/ceo-boot digest" depending on cache state.
        output = out.getvalue()
        self.assertTrue(
            "/ceo-boot digest" in output or "--cached" in output,
            f"Expected digest or cached output, got: {output[:200]}",
        )

    def test_main_json_emits_parseable(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = _mod.main(["--json"])
        self.assertEqual(rc, 0)
        # Output: digest JSON + trailing newline
        body = out.getvalue().strip()
        # First brace marks the JSON object
        idx = body.find("{")
        self.assertGreaterEqual(idx, 0)
        payload = json.loads(body[idx:])
        self.assertIn("elapsed_ms", payload)
        self.assertIn("gate_pass", payload)
        self.assertIn("checks_total", payload)
        self.assertIn("results", payload)
        # PLAN-135 W1 S3: 21 Tier-S checks.
        self.assertEqual(len(payload["results"]), 23)  # PLAN-153 Wave E


if __name__ == "__main__":
    unittest.main()
