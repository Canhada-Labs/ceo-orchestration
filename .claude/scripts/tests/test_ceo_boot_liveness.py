"""Tests for PLAN-153 Wave E — /ceo-boot fail-open rail liveness + E1 gate wire.

Covers the two new Tier-S checks in ``.claude/scripts/ceo-boot.py``:

``failopen_rail_liveness_7d`` (Wave E item 2, debate B unseen-1 — the S254
lesson: silence from a fail-open security rail is not health):

- registry wiring (name present, 23 checks, timeout override);
- RED when every classified pair-rail invocation in the window fail-opened
  (``pair_rail_case`` case=F and/or the typed ``pair_rail_codex_unavailable``
  label);
- YELLOW partial fail-open (mixed F + A);
- GREEN when healthy reviews exist (case A/B, ``pair_rail_review_passed``);
- YELLOW "no signal" on empty/missing/aged-out log — NEVER green (the live
  S254 dead-registration state produces exactly zero events);
- unclassified (hand-forged out-of-enum case) can never contribute green;
- test-pollution events (``test`` discriminant) are filtered;
- detail structure carries window_hours + per-rail counts.

``harness_config_gate`` (Wave E item 1 wire):

- green "not installed" while ``check_harness_config.py`` is absent (the
  pre-SENT-E-landing state — ceo-boot must stay green);
- subprocess rc=0 → green, rc!=0 → red with sanitized first output line;
- timeout → yellow (skipped, fail-open) + ``ceo_boot_check_skipped`` emit
  attempt via ``_emit_ceo_boot_check_skipped_safe``;
- output sanitization: control chars / oversized lines are bounded.

Recommendations engine: red liveness → "006-failopen-rail" HIGH; red gate →
"007-harness-config" HIGH; mirrored in ``_recommendations_with_severity``.

All gate fixtures written here are INERT TEST DATA — tiny stub scripts that
merely simulate the E1 gate's exit-code contract; no known-bad payloads are
executed.

Env hygiene (PLAN-019 P1-QA-3): every test class subclasses TestEnvContext;
env mutation only via unittest.mock. Stdlib-only, Python >= 3.9. Runs under
pytest AND plain unittest.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "ceo-boot.py"

# Seed sys.path so _lib + hook-side modules resolve (conftest also does
# this, but keep the module self-sufficient if run in isolation).
for _p in (
    str(REPO_ROOT / ".claude" / "hooks"),
    str(REPO_ROOT / ".claude" / "scripts"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _lib.testing import TestEnvContext  # noqa: E402


def _load_module():
    """Load ceo-boot.py under a unique module name (hyphen in filename)."""
    spec = importlib.util.spec_from_file_location("ceo_boot_liveness", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module()

LIVENESS_CHECK = "failopen_rail_liveness_7d"
GATE_CHECK = "harness_config_gate"


def _iso_utc(hours_ago: float = 0.0) -> str:
    dt = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_events(path: Path, events: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")


class _AuditLogPatch:
    """Save/restore AUDIT_LOG_DEFAULT around a test (persona-cadence pattern)."""

    def __init__(self, test: unittest.TestCase, log_path: Path) -> None:
        self._saved = _mod.AUDIT_LOG_DEFAULT
        _mod.AUDIT_LOG_DEFAULT = log_path
        test.addCleanup(self._restore)

    def _restore(self) -> None:
        _mod.AUDIT_LOG_DEFAULT = self._saved


# ---------------------------------------------------------------------------
# Registry wiring
# ---------------------------------------------------------------------------


class TestRegistryWiring(TestEnvContext):
    def test_registry_has_23_checks(self):
        # PLAN-153 Wave E: 21 → 23 (+failopen_rail_liveness_7d,
        # +harness_config_gate).
        self.assertEqual(len(_mod.TIER_S_CHECKS), 23)

    def test_liveness_check_registered(self):
        names = [name for name, _ in _mod.TIER_S_CHECKS]
        self.assertIn(LIVENESS_CHECK, names)

    def test_gate_check_registered(self):
        names = [name for name, _ in _mod.TIER_S_CHECKS]
        self.assertIn(GATE_CHECK, names)

    def test_timeout_overrides_present(self):
        self.assertEqual(
            _mod.PER_CHECK_TIMEOUT_OVERRIDES_S[LIVENESS_CHECK], 1.5
        )
        self.assertEqual(_mod.PER_CHECK_TIMEOUT_OVERRIDES_S[GATE_CHECK], 3.0)

    def test_pair_rail_registered_in_classifier_registry(self):
        rails = [rail for rail, _ in _mod.FAILOPEN_RAIL_CLASSIFIERS]
        self.assertIn("pair_rail", rails)


# ---------------------------------------------------------------------------
# failopen_rail_liveness_7d
# ---------------------------------------------------------------------------


class TestFailopenRailLiveness(TestEnvContext):
    def _run_with_events(
        self, events: List[Dict[str, Any]], *, missing_log: bool = False
    ):
        log = self.audit_dir / "audit-log.jsonl"
        if not missing_log:
            _write_events(log, events)
        _AuditLogPatch(self, log)
        return _mod.check_failopen_rail_liveness_7d()

    # -- RED: fail-opened on every classified invocation ------------------

    def test_all_failopen_case_f_is_red(self):
        status, summary, detail = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_case", "case": "F"},
            {"ts": _iso_utc(2), "action": "pair_rail_case", "case": "F"},
        ])
        self.assertEqual(status, "red")
        self.assertIn("fail-opened on ALL 2", summary)
        self.assertEqual(detail["rails"]["pair_rail"]["failopen"], 2)
        self.assertEqual(detail["rails"]["pair_rail"]["healthy"], 0)

    def test_typed_codex_unavailable_only_is_red(self):
        status, summary, _ = self._run_with_events([
            {"ts": _iso_utc(3), "action": "pair_rail_codex_unavailable"},
        ])
        self.assertEqual(status, "red")
        self.assertIn("fail-opened on ALL 1", summary)

    def test_fatal_failopen_label_counts_as_failopen(self):
        status, _, detail = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_fatal_failopen"},
        ])
        self.assertEqual(status, "red")
        self.assertEqual(detail["rails"]["pair_rail"]["failopen"], 1)

    # -- YELLOW: partial fail-open ----------------------------------------

    def test_mixed_f_and_a_is_yellow_partial(self):
        status, summary, _ = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_case", "case": "F"},
            {"ts": _iso_utc(2), "action": "pair_rail_case", "case": "A"},
        ])
        self.assertEqual(status, "yellow")
        self.assertIn("partial fail-open", summary)

    # -- GREEN: healthy reviews --------------------------------------------

    def test_healthy_case_a_is_green(self):
        status, summary, _ = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_case", "case": "A"},
        ])
        self.assertEqual(status, "green")
        self.assertIn("1 healthy", summary)

    def test_case_b_block_is_healthy(self):
        # A Codex BLOCK is the strongest liveness proof.
        status, _, detail = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_case", "case": "B"},
        ])
        self.assertEqual(status, "green")
        self.assertEqual(detail["rails"]["pair_rail"]["healthy"], 1)

    def test_review_passed_label_is_healthy(self):
        status, _, _ = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_review_passed"},
        ])
        self.assertEqual(status, "green")

    # -- YELLOW: no signal is never green -----------------------------------

    def test_empty_log_is_yellow_no_signal(self):
        status, summary, _ = self._run_with_events([])
        self.assertEqual(status, "yellow")
        self.assertIn("no signal", summary)

    def test_missing_log_is_yellow_no_signal(self):
        status, summary, _ = self._run_with_events([], missing_log=True)
        self.assertEqual(status, "yellow")
        self.assertIn("no signal", summary)

    def test_events_outside_window_are_ignored(self):
        # 240h ago > 168h default window → aged out → no signal.
        status, summary, _ = self._run_with_events([
            {"ts": _iso_utc(240), "action": "pair_rail_case", "case": "F"},
        ])
        self.assertEqual(status, "yellow")
        self.assertIn("no signal", summary)

    def test_unrelated_events_do_not_count(self):
        status, summary, _ = self._run_with_events([
            {"ts": _iso_utc(1), "action": "agent_spawn"},
            {"ts": _iso_utc(1), "action": "policy_evaluated"},
        ])
        self.assertEqual(status, "yellow")
        self.assertIn("no signal", summary)

    # -- unclassified never contributes green -------------------------------

    def test_forged_out_of_enum_case_is_unclassified_yellow(self):
        status, summary, detail = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_case", "case": "Z"},
        ])
        self.assertEqual(status, "yellow")
        self.assertIn("unclassified", summary)
        self.assertEqual(detail["rails"]["pair_rail"]["unclassified"], 1)

    def test_missing_case_field_is_unclassified(self):
        status, _, detail = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_case"},
        ])
        self.assertEqual(status, "yellow")
        self.assertEqual(detail["rails"]["pair_rail"]["unclassified"], 1)

    # -- hygiene -------------------------------------------------------------

    def test_test_pollution_events_filtered(self):
        # `test` discriminant (bench/warmup/probe) must not redden boot.
        status, summary, _ = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_case", "case": "F",
             "test": "bench"},
        ])
        self.assertEqual(status, "yellow")
        self.assertIn("no signal", summary)

    def test_malformed_lines_skipped_without_crash(self):
        log = self.audit_dir / "audit-log.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("w", encoding="utf-8") as f:
            f.write("{not json}\n")
            f.write("\x00\x01binary junk\n")
            f.write(json.dumps(
                {"ts": _iso_utc(1), "action": "pair_rail_case", "case": "A"}
            ) + "\n")
        _AuditLogPatch(self, log)
        status, _, _ = _mod.check_failopen_rail_liveness_7d()
        self.assertEqual(status, "green")

    def test_window_env_override_clamped(self):
        with mock.patch.dict(
            os.environ, {"CEO_FAILOPEN_LIVENESS_WINDOW_H": "999999"}
        ):
            self.assertEqual(_mod._failopen_rail_window_hours(), 2160.0)
        with mock.patch.dict(
            os.environ, {"CEO_FAILOPEN_LIVENESS_WINDOW_H": "not-a-number"}
        ):
            self.assertEqual(
                _mod._failopen_rail_window_hours(),
                _mod.FAILOPEN_RAIL_WINDOW_HOURS_DEFAULT,
            )

    def test_window_env_override_widens_window(self):
        # Event 240h old is out of the 168h default but inside a 400h window.
        with mock.patch.dict(
            os.environ, {"CEO_FAILOPEN_LIVENESS_WINDOW_H": "400"}
        ):
            status, _, _ = self._run_with_events([
                {"ts": _iso_utc(240), "action": "pair_rail_case", "case": "A"},
            ])
        self.assertEqual(status, "green")

    def test_detail_carries_window_and_counts(self):
        _, _, detail = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_case", "case": "F"},
        ])
        self.assertEqual(detail["window_hours"], 168.0)
        rail = detail["rails"]["pair_rail"]
        for key in ("status", "healthy", "failopen", "unclassified"):
            self.assertIn(key, rail)

    def test_summary_is_sanitized_single_line(self):
        _, summary, _ = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_case", "case": "F"},
        ])
        self.assertNotIn("\n", summary)
        self.assertLessEqual(len(summary), 200)


# ---------------------------------------------------------------------------
# harness_config_gate
# ---------------------------------------------------------------------------


class TestHarnessConfigGate(TestEnvContext):
    def _write_gate(self, body: str) -> Path:
        """Write an INERT stub gate script (test data — simulates only the
        exit-code contract of the E1 gate, no real payloads)."""
        gate = Path(self._tmp_root) / "stub_check_harness_config.py"
        gate.write_text(textwrap.dedent(body), encoding="utf-8")
        return gate

    def _run_gate(self, gate_path: Path, extra_env: Optional[Dict[str, str]] = None):
        env = {"CEO_HARNESS_CONFIG_GATE": str(gate_path)}
        if extra_env:
            env.update(extra_env)
        with mock.patch.dict(os.environ, env):
            return _mod.check_harness_config_gate()

    def test_not_installed_is_green(self):
        status, summary, detail = self._run_gate(
            Path(self._tmp_root) / "does-not-exist.py"
        )
        self.assertEqual(status, "green")
        self.assertIn("not installed", summary)
        self.assertEqual(detail, {"installed": False})

    def test_current_tree_default_state_stays_green(self):
        # Pre-SENT-E-landing invariant: while check_harness_config.py is
        # absent from the live tree, boot must stay green. Auto-retires
        # once the E1 ceremony lands the file canonical.
        if _mod.HARNESS_CONFIG_GATE_DEFAULT.is_file():
            self.skipTest("E1 gate landed canonical — default path active")
        status, summary, _ = _mod.check_harness_config_gate()
        self.assertEqual(status, "green")
        self.assertIn("not installed", summary)

    def test_rc_zero_is_green_pass(self):
        gate = self._write_gate(
            """
            import sys
            print("harness-config gate: all registered hooks resolve")
            sys.exit(0)
            """
        )
        status, summary, detail = self._run_gate(gate)
        self.assertEqual(status, "green")
        self.assertEqual(summary, "harness-config gate pass")
        self.assertEqual(detail["rc"], 0)

    def test_nonzero_rc_is_red_with_first_line(self):
        gate = self._write_gate(
            """
            import sys
            print("planted-fixture: shim runtime-unresolvable (inert test data)")
            sys.exit(3)
            """
        )
        status, summary, detail = self._run_gate(gate)
        self.assertEqual(status, "red")
        self.assertIn("rc=3", summary)
        self.assertIn("planted-fixture", summary)
        self.assertEqual(detail["rc"], 3)

    def test_stderr_first_line_used_when_stdout_empty(self):
        gate = self._write_gate(
            """
            import sys
            sys.stderr.write("gate stderr diagnostic\\n")
            sys.exit(1)
            """
        )
        status, summary, _ = self._run_gate(gate)
        self.assertEqual(status, "red")
        self.assertIn("gate stderr diagnostic", summary)

    def test_red_summary_is_sanitized_and_bounded(self):
        gate = self._write_gate(
            """
            import sys
            print("EVIL\\x00" + "A" * 5000)
            sys.exit(2)
            """
        )
        status, summary, _ = self._run_gate(gate)
        self.assertEqual(status, "red")
        self.assertNotIn("\x00", summary)
        self.assertNotIn("\n", summary)
        self.assertLessEqual(len(summary), 200)

    def test_timeout_is_yellow_skipped_and_emits_check_skipped(self):
        gate = self._write_gate(
            """
            import time
            time.sleep(5)
            """
        )
        calls: List[Dict[str, Any]] = []

        def _capture(**kwargs):
            calls.append(kwargs)

        saved = _mod._emit_ceo_boot_check_skipped_safe
        _mod._emit_ceo_boot_check_skipped_safe = _capture
        try:
            status, summary, detail = self._run_gate(
                gate, {"CEO_HARNESS_CONFIG_GATE_TIMEOUT_S": "0.3"}
            )
        finally:
            _mod._emit_ceo_boot_check_skipped_safe = saved
        self.assertEqual(status, "yellow")
        self.assertIn("timeout", summary)
        self.assertTrue(detail.get("timeout"))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["check_name"], GATE_CHECK)
        self.assertEqual(calls[0]["timeout_ms"], 300)

    def test_gate_timeout_env_clamped(self):
        with mock.patch.dict(
            os.environ, {"CEO_HARNESS_CONFIG_GATE_TIMEOUT_S": "9999"}
        ):
            self.assertEqual(_mod._harness_config_gate_timeout_s(), 10.0)
        with mock.patch.dict(
            os.environ, {"CEO_HARNESS_CONFIG_GATE_TIMEOUT_S": "garbage"}
        ):
            self.assertEqual(
                _mod._harness_config_gate_timeout_s(),
                _mod.HARNESS_CONFIG_GATE_TIMEOUT_S_DEFAULT,
            )

    def test_gate_directory_path_is_not_a_file_green(self):
        # A directory at the gate path is "not installed" (is_file() gate).
        gate_dir = Path(self._tmp_root) / "gate-as-dir"
        gate_dir.mkdir()
        status, _, _ = self._run_gate(gate_dir)
        self.assertEqual(status, "green")


# ---------------------------------------------------------------------------
# Recommendations engine (006 / 007 rules, both pipelines)
# ---------------------------------------------------------------------------


class TestRecommendations(TestEnvContext):
    def _ck(self, name: str, status: str, summary: str, detail: Any = None):
        return _mod.CheckResult(name, status, summary, 1.0, detail)

    def test_red_liveness_surfaces_006_high(self):
        results = [
            self._ck(LIVENESS_CHECK, "red",
                     "pair_rail: fail-opened on ALL 4 classified "
                     "invocation(s) in 168h"),
        ]
        recs = _mod._make_recommendations(results)
        self.assertTrue(
            any("Fail-open security rail" in r for r in recs), recs
        )
        triples = _mod._recommendations_with_severity(results)
        match = [t for t in triples if t[0] == "006-failopen-rail"]
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0][2], "high")

    def test_red_gate_surfaces_007_high(self):
        results = [
            self._ck(GATE_CHECK, "red", "harness-config gate FAIL (rc=3)"),
        ]
        recs = _mod._make_recommendations(results)
        self.assertTrue(any("Harness-config gate FAIL" in r for r in recs))
        triples = _mod._recommendations_with_severity(results)
        match = [t for t in triples if t[0] == "007-harness-config"]
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0][2], "high")

    def test_yellow_liveness_no_signal_does_not_fire_006(self):
        # "no signal" is a visibility yellow, not a rec-worthy red.
        results = [
            self._ck(LIVENESS_CHECK, "yellow",
                     "pair_rail: no signal in 168h"),
        ]
        recs = _mod._make_recommendations(results)
        self.assertFalse(any("Fail-open security rail" in r for r in recs))

    def test_pipelines_share_text_for_006(self):
        results = [
            self._ck(LIVENESS_CHECK, "red", "pair_rail: fail-opened"),
        ]
        recs = _mod._make_recommendations(results)
        triples = _mod._recommendations_with_severity(results)
        texts = [t[1] for t in triples if t[0] == "006-failopen-rail"]
        self.assertEqual(len(texts), 1)
        self.assertIn(texts[0], recs)


# ---------------------------------------------------------------------------
# Dispatcher integration (both checks run inside the parallel registry)
# ---------------------------------------------------------------------------


class TestDispatcherIntegration(TestEnvContext):
    def test_dispatch_includes_new_checks_in_order(self):
        results = _mod.dispatch_parallel()
        names = [r.name for r in results]
        self.assertIn(LIVENESS_CHECK, names)
        self.assertIn(GATE_CHECK, names)
        registry_names = [n for n, _ in _mod.TIER_S_CHECKS]
        self.assertEqual(names, [n for n in registry_names if n in names])

    def test_new_checks_never_raise_via_wrapper(self):
        for name in (LIVENESS_CHECK, GATE_CHECK):
            fn = dict(_mod.TIER_S_CHECKS)[name]
            res = _mod._wrap_check(name, fn)
            self.assertIn(
                res.status, ("green", "yellow", "red", "timeout", "error")
            )


if __name__ == "__main__":
    unittest.main()
