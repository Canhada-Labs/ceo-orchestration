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

PLAN-161 W2 C5 (pair-rail liveness telemetry) extends the check with a
second `stop_review` sub-rail + activity-conditioning on the `pair_rail`
row; the pre-existing single-rail GREEN assertions below were updated to
assert the pair_rail ROW status (overall now aggregates worst-of BOTH rows,
and stop_review stays yellow "no signal" until a Stop review runs — L4):

- stop_review mapping: clean/findings → healthy (green when failopen==0);
  skipped_failopen → failopen (red alone, yellow mixed — the :1779 rule);
  detected_only → NEUTRAL (visible in counts, never green-contributing,
  never failopen); forged out-of-enum outcome → unclassified (never green);
- pair_rail activity-conditioning on ``pair_rail_review_expected`` with
  INVOCATION-ID-EXACT pairing (codex r1 F2 → r2 F2 → r4 F2, terminal
  fix r5 F2): the producer mints one 16-hex ``review_id`` per entered
  review and stamps it on BOTH that review's expected emit and its own
  ``pair_rail_case``, so a specific expected pairs ONLY with its own
  case. Zero expected + zero outcomes → vacuous green; any EXPECTED
  ``review_id`` with no matching TERMINAL case (``pair_rail_case`` ONLY —
  the same producer's completion signal; ``pair_rail_codex_unavailable``
  is NOT terminal because codex_invoke.py also emits it, so an unrelated
  outage must never consume a terminal count and mask a missing case) →
  RED escalation (S254 class), including CROSS-SESSION (healthy outcome
  from session B never masks expected-but-missing from session A),
  PARTIAL-DEATH (one early healthy outcome never masks later dead
  invocations in the SAME session — a true zero-case deficit), the
  r4 F2 INTERLEAVING (an OLD completed case for file X never offsets a
  LATER expected for file Y), and the r5 F2 SAME-FILE INTERLEAVING (an
  old completed case for the SAME (session, file) — a different
  review_id — never offsets a later dead expected; (session, file-hash)
  BUCKET COUNTING balanced them 1:1 and false-greened the row, which is
  why counting was replaced by id correlation). Id-less ("" review_id)
  legacy events fall back to the r4 bucket-count heuristic applied to
  the "" subset only; outcomes present with no deficit → the
  original ladder. r3 F2 correction: a MID-REVIEW OUTAGE is NOT a
  deficit — Case F still emits `pair_rail_case` (check_pair_rail.py
  `_decide_with_matrix` Case-F arm) carrying the same review_id, so the
  outage invocation pairs expected==case and is laddered by its
  failopen bucket; a deficit means the hook died BETWEEN the expected
  emit and the case emit (zero pair_rail_case for that invocation).

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

    def test_stop_review_registered_in_classifier_registry(self):
        # PLAN-161 C5 — the Stop-hook cross-review gets its OWN sub-rail
        # row (sub-rails split, not merged — r2 F3).
        rails = [rail for rail, _ in _mod.FAILOPEN_RAIL_CLASSIFIERS]
        self.assertIn("stop_review", rails)


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
    # PLAN-161 C5: overall now aggregates worst-of BOTH rows (pair_rail +
    # stop_review), and stop_review stays yellow "no signal" until a Stop
    # review runs — so these pin the pair_rail ROW status green instead of
    # the overall verdict.

    def test_healthy_case_a_is_green(self):
        status, summary, detail = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_case", "case": "A"},
        ])
        self.assertEqual(detail["rails"]["pair_rail"]["status"], "green")
        self.assertIn("1 healthy", summary)
        # overall stays yellow: stop_review has no signal yet (L4 timing)
        self.assertEqual(status, "yellow")

    def test_case_b_block_is_healthy(self):
        # A Codex BLOCK is the strongest liveness proof.
        _, _, detail = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_case", "case": "B"},
        ])
        self.assertEqual(detail["rails"]["pair_rail"]["status"], "green")
        self.assertEqual(detail["rails"]["pair_rail"]["healthy"], 1)

    def test_review_passed_label_is_healthy(self):
        _, _, detail = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_review_passed"},
        ])
        self.assertEqual(detail["rails"]["pair_rail"]["status"], "green")

    def test_both_rows_healthy_is_overall_green(self):
        # PLAN-161 C5 L4 criterion: overall green requires BOTH rows —
        # reachable in a normal post-land week (a healthy Stop review +
        # either pair-rail outcomes or a vacuous pair_rail window).
        status, _, detail = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_case", "case": "A"},
            {"ts": _iso_utc(2), "action": "codex_review_verdict",
             "outcome": "clean"},
        ])
        self.assertEqual(status, "green")
        self.assertEqual(detail["rails"]["pair_rail"]["status"], "green")
        self.assertEqual(detail["rails"]["stop_review"]["status"], "green")

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
        _, _, detail = _mod.check_failopen_rail_liveness_7d()
        # PLAN-161 C5: pin the pair_rail ROW (overall aggregates stop_review)
        self.assertEqual(detail["rails"]["pair_rail"]["status"], "green")

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
            _, _, detail = self._run_with_events([
                {"ts": _iso_utc(240), "action": "pair_rail_case", "case": "A"},
            ])
        # PLAN-161 C5: pin the pair_rail ROW (overall aggregates stop_review)
        self.assertEqual(detail["rails"]["pair_rail"]["status"], "green")

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
# PLAN-161 W2 C5 — stop_review sub-rail (codex_review_verdict mapping)
# ---------------------------------------------------------------------------


class TestStopReviewSubRail(TestEnvContext):
    def _run_with_events(self, events: List[Dict[str, Any]]):
        log = self.audit_dir / "audit-log.jsonl"
        _write_events(log, events)
        _AuditLogPatch(self, log)
        return _mod.check_failopen_rail_liveness_7d()

    @staticmethod
    def _crv(outcome: str, hours_ago: float = 1.0,
             session_id: str = "") -> Dict[str, Any]:
        return {"ts": _iso_utc(hours_ago), "action": "codex_review_verdict",
                "outcome": outcome, "session_id": session_id}

    def test_clean_is_healthy_green_row(self):
        _, _, detail = self._run_with_events([self._crv("clean")])
        row = detail["rails"]["stop_review"]
        self.assertEqual(row["status"], "green")
        self.assertEqual(row["healthy"], 1)

    def test_findings_is_healthy_green_row(self):
        # A parsed findings verdict proves the review RAN — health, not red.
        _, _, detail = self._run_with_events([self._crv("findings")])
        self.assertEqual(detail["rails"]["stop_review"]["status"], "green")

    def test_skipped_failopen_only_is_red(self):
        status, summary, detail = self._run_with_events([
            self._crv("skipped_failopen"),
            self._crv("skipped_failopen", 2.0),
        ])
        self.assertEqual(status, "red")
        row = detail["rails"]["stop_review"]
        self.assertEqual(row["status"], "red")
        self.assertEqual(row["failopen"], 2)
        self.assertIn("fail-opened on ALL 2", summary)

    def test_mixture_stays_yellow(self):
        # The :1779 mixed-window rule: healthy+failopen is NOT green — and
        # per L4 that is the check working, not a C5 failure.
        status, _, detail = self._run_with_events([
            self._crv("clean"),
            self._crv("skipped_failopen", 2.0),
        ])
        self.assertEqual(detail["rails"]["stop_review"]["status"], "yellow")
        self.assertEqual(status, "yellow")

    def test_detected_only_is_neutral_never_green(self):
        # r3 F3: a nudged-but-never-run review is neither health nor
        # failopen — visible in counts, never green-contributing.
        _, _, detail = self._run_with_events([
            self._crv("detected_only"),
            self._crv("detected_only", 2.0),
        ])
        row = detail["rails"]["stop_review"]
        self.assertEqual(row["status"], "yellow")
        self.assertEqual(row["neutral"], 2)
        self.assertEqual(row["healthy"], 0)
        self.assertEqual(row["failopen"], 0)

    def test_detected_only_never_blocks_green(self):
        # neutral + healthy → green (neutral is not failopen)
        _, _, detail = self._run_with_events([
            self._crv("detected_only"),
            self._crv("clean", 2.0),
        ])
        self.assertEqual(detail["rails"]["stop_review"]["status"], "green")

    def test_detected_only_never_contributes_failopen_red(self):
        # neutral + failopen → red comes from the failopen alone ("ALL 1")
        _, summary, detail = self._run_with_events([
            self._crv("detected_only"),
            self._crv("skipped_failopen", 2.0),
        ])
        self.assertEqual(detail["rails"]["stop_review"]["status"], "red")
        self.assertIn("fail-opened on ALL 1", summary)

    def test_forged_outcome_is_unclassified_never_green(self):
        # Hand-forged log line (the typed emitter coerces off-enum to
        # skipped_failopen; only a forged line can carry junk).
        _, _, detail = self._run_with_events([self._crv("banana")])
        row = detail["rails"]["stop_review"]
        self.assertEqual(row["status"], "yellow")
        self.assertEqual(row["unclassified"], 1)

    def test_no_signal_stays_yellow(self):
        # stop_review is NOT activity-conditioned: silence stays yellow
        # until the first post-land Stop review of a risky diff (L4).
        _, summary, detail = self._run_with_events([])
        self.assertEqual(detail["rails"]["stop_review"]["status"], "yellow")
        self.assertIn("no signal", summary)

    def test_stop_review_healthy_does_not_mask_pair_rail_red(self):
        # Sub-rails split (r2 F3): a healthy Stop review must never mask a
        # silent/failing canonical pair-rail.
        status, _, detail = self._run_with_events([
            self._crv("clean"),
            {"ts": _iso_utc(1), "action": "pair_rail_case", "case": "F"},
        ])
        self.assertEqual(detail["rails"]["stop_review"]["status"], "green")
        self.assertEqual(detail["rails"]["pair_rail"]["status"], "red")
        self.assertEqual(status, "red")


# ---------------------------------------------------------------------------
# PLAN-161 W2 C5 — pair_rail activity-conditioning (pair_rail_review_expected)
# ---------------------------------------------------------------------------


class TestPairRailActivityConditioning(TestEnvContext):
    # r4 F2: production emits carry the SAME 16-hex file-path-hash token
    # on BOTH the expected and the case event (same producer helper), so
    # the fixtures do too. FILE_X / FILE_Y model two distinct edit targets.
    FILE_X = "ab12cd34ef56ab12"
    FILE_Y = "9f8e7d6c5b4a3210"
    # r5 F2: production emits ALSO carry one 16-hex `review_id` per
    # entered review — identical on that review's expected AND its own
    # case (minted via os.urandom(8).hex() in check_pair_rail._decide).
    # R1/R2/R3 model three distinct invocations; "" models a legacy
    # pre-land (id-less) event, which pairs via the r4 bucket fallback.
    R1 = "aa11aa11aa11aa11"
    R2 = "bb22bb22bb22bb22"
    R3 = "cc33cc33cc33cc33"

    def _run_with_events(self, events: List[Dict[str, Any]]):
        log = self.audit_dir / "audit-log.jsonl"
        _write_events(log, events)
        _AuditLogPatch(self, log)
        return _mod.check_failopen_rail_liveness_7d()

    @classmethod
    def _expected(cls, session_id: str = "", hours_ago: float = 1.0,
                  file_hash: Optional[str] = None,
                  review_id: str = "") -> Dict[str, Any]:
        return {"ts": _iso_utc(hours_ago), "action": "pair_rail_review_expected",
                "session_id": session_id, "tool_name": "Edit",
                "file_path_hash_prefix": (
                    cls.FILE_X if file_hash is None else file_hash),
                "review_id": review_id}

    @classmethod
    def _case(cls, case: str, session_id: str = "",
              hours_ago: float = 1.0,
              file_hash: Optional[str] = None,
              review_id: str = "") -> Dict[str, Any]:
        return {"ts": _iso_utc(hours_ago), "action": "pair_rail_case",
                "case": case, "session_id": session_id,
                "file_path_hash_prefix": (
                    cls.FILE_X if file_hash is None else file_hash),
                "review_id": review_id}

    def test_vacuous_green_zero_expected_zero_outcomes(self):
        _, summary, detail = self._run_with_events([])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["status"], "green")
        self.assertEqual(row["expected"], 0)
        self.assertIn("vacuously green", summary)

    def test_expected_without_outcome_escalates_red(self):
        # The GENUINE deficit (S254 class): the review path was ENTERED
        # and ZERO pair_rail_case came back — the hook died / was killed
        # BETWEEN the review-expected emit and the case emit. Flat
        # "silence = yellow" understates it. (An outage is NOT this
        # trace: Case F still emits a pair_rail_case — see
        # test_mid_review_outage_case_f_is_accounted_not_a_deficit.)
        status, summary, detail = self._run_with_events([
            self._expected("sessA", review_id=self.R1),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["status"], "red")
        self.assertEqual(row["expected"], 1)
        self.assertEqual(row["expected_without_outcome_sessions"], 1)
        self.assertEqual(status, "red")
        self.assertIn("missing terminal outcome", summary)

    def test_cross_session_mismatch_still_red(self):
        # A healthy outcome from session B must NEVER mask
        # expected-but-missing from session A (r4 F1).
        status, _, detail = self._run_with_events([
            self._expected("sessA", review_id=self.R1),
            self._expected("sessB", 2.0, review_id=self.R2),
            self._case("A", "sessB", 1.5, review_id=self.R2),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["status"], "red")
        self.assertEqual(row["expected_without_outcome_sessions"], 1)
        self.assertEqual(status, "red")

    def test_expected_with_outcome_same_session_is_todays_semantics(self):
        _, _, detail = self._run_with_events([
            self._expected("sessA", review_id=self.R1),
            self._case("A", "sessA", review_id=self.R1),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["status"], "green")
        self.assertEqual(row["expected_without_outcome_sessions"], 0)

    def test_expected_with_failopen_outcome_is_not_mismatch(self):
        # A fail-open outcome IS an outcome (the rail responded) — the row
        # verdict then comes from the original ladder (red: all fail-open).
        # This is also the canonical single-invocation OUTAGE trace:
        # Case F's `pair_rail_case` pairs the expected — no deficit.
        _, _, detail = self._run_with_events([
            self._expected("sessA", review_id=self.R1),
            self._case("F", "sessA", review_id=self.R1),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["expected_without_outcome_sessions"], 0)
        self.assertEqual(row["status"], "red")  # ladder: fail-opened on ALL

    def test_legacy_outcomes_without_expected_keep_todays_semantics(self):
        # Producers that never emit expected (codex_invoke.py labels, old
        # logs) still classify exactly as before.
        _, _, detail = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_review_passed"},
        ])
        self.assertEqual(detail["rails"]["pair_rail"]["status"], "green")

    def test_empty_session_id_correlates_as_own_bucket(self):
        # "" is itself a correlation bucket: an unattributed expected pairs
        # with an unattributed outcome instead of going blind.
        _, _, detail = self._run_with_events([
            self._expected("", review_id=self.R1),
            self._case("A", "", review_id=self.R1),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["expected_without_outcome_sessions"], 0)
        self.assertEqual(row["status"], "green")

    def test_expected_event_is_not_an_outcome(self):
        # The denominator never enters a bucket: expected alone must not
        # count as healthy/failopen/unclassified.
        _, _, detail = self._run_with_events([
            self._expected("sessA", review_id=self.R1),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["healthy"], 0)
        self.assertEqual(row["failopen"], 0)
        self.assertEqual(row["unclassified"], 0)

    def test_pollution_filtered_expected_does_not_escalate(self):
        # `test` discriminant events are filtered before correlation.
        _, _, detail = self._run_with_events([
            {"ts": _iso_utc(1), "action": "pair_rail_review_expected",
             "session_id": "sessA", "review_id": "dd44dd44dd44dd44",
             "test": "bench"},
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["status"], "green")
        self.assertEqual(row["expected"], 0)

    def test_partial_death_same_session_count_deficit_escalates_red(self):
        # codex r1 F2: one early healthy outcome must NOT mask later dead
        # invocations in the SAME session — expected=3 with only 1
        # terminal outcome is a count deficit → RED escalation. This is a
        # TRUE zero-case deficit (r3 F2): invocations 2 and 3 emitted NO
        # pair_rail_case at all (hook killed between the expected emit
        # and the case emit) — no outage events involved.
        status, summary, detail = self._run_with_events([
            self._expected("sessA", 3.0, review_id=self.R1),
            self._expected("sessA", 2.5, review_id=self.R2),
            self._expected("sessA", 2.0, review_id=self.R3),
            self._case("A", "sessA", 2.8, review_id=self.R1),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["status"], "red")
        self.assertEqual(row["expected"], 3)
        self.assertEqual(row["expected_without_outcome_sessions"], 1)
        self.assertEqual(status, "red")
        self.assertIn("missing terminal outcome", summary)

    def test_mid_review_outage_case_f_is_accounted_not_a_deficit(self):
        # codex r3 F2 (corrects the r2 test, which modeled an IMPOSSIBLE
        # trace): a REAL Codex outage during an ENTERED review is Case F,
        # and check_pair_rail.py `_decide_with_matrix`'s Case-F arm STILL
        # emits `pair_rail_case` (case=F; codex_verdict TIMEOUT/MALFORMED).
        # check_pair_rail's own `pair_rail_codex_unavailable` copy goes to
        # a local sink + stderr only, so the CANONICAL outage trace is
        # exactly expected + case F. The outage session therefore pairs
        # expected==terminal — NO deficit — and the row is laddered by the
        # case buckets (here mixed A+F → yellow partial fail-open), NOT
        # the S254 missing-terminal-outcome RED escalation.
        status, summary, detail = self._run_with_events([
            self._expected("sessA", 3.0, review_id=self.R1),
            self._expected("sessA", 2.0, review_id=self.R2),
            self._case("A", "sessA", 2.5, review_id=self.R1),
            {"ts": _iso_utc(1.5), "action": "pair_rail_case", "case": "F",
             "codex_verdict": "TIMEOUT", "session_id": "sessA",
             "file_path_hash_prefix": self.FILE_X,
             "review_id": self.R2},
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["expected"], 2)
        self.assertEqual(row["expected_without_outcome_sessions"], 0)
        self.assertEqual(row["failopen"], 1)  # outage visible via case=F
        self.assertEqual(row["healthy"], 1)
        self.assertEqual(row["status"], "yellow")  # ladder: partial fail-open
        self.assertNotIn("missing terminal outcome", summary)
        self.assertEqual(status, "yellow")

    def test_unavailable_from_other_rail_never_masks_zero_case_deficit(self):
        # codex r2 F2 regression guard, re-grounded by r3 F2: this trace
        # is NOT what check_pair_rail's outage path emits (that is Case F,
        # above) — it is a hook DEATH (invocation 2 emitted zero
        # pair_rail_case) PLUS an unrelated canonical
        # `pair_rail_codex_unavailable` from codex_invoke.py (a DIFFERENT
        # rail) in the same session. Because that label is NOT terminal,
        # it must not consume a terminal count and mask the genuinely
        # missing `pair_rail_case`: expected=2 with only 1 case → deficit
        # → RED escalation; the unavailable event stays visible in the
        # failopen bucket.
        status, summary, detail = self._run_with_events([
            self._expected("sessA", 3.0, review_id=self.R1),
            self._expected("sessA", 2.0, review_id=self.R2),
            self._case("A", "sessA", 2.5, review_id=self.R1),
            {"ts": _iso_utc(1.5), "action": "pair_rail_codex_unavailable",
             "session_id": "sessA"},
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["expected"], 2)
        self.assertEqual(row["expected_without_outcome_sessions"], 1)
        self.assertEqual(row["failopen"], 1)  # outage still accounted/visible
        self.assertEqual(row["status"], "red")
        self.assertEqual(status, "red")
        self.assertIn("missing terminal outcome", summary)

    def test_old_case_other_file_never_offsets_new_dead_review(self):
        # codex r4 F2 — THE interleaving the flat per-session count
        # false-greened: session S carries an OLDER completed
        # `pair_rail_case` for file X (here with no expected of its own —
        # e.g. a pre-C5 in-window event), then a LATER
        # `pair_rail_review_expected` for file Y whose hook DIED before
        # emitting its case. Aggregate counts balance 1:1 (expected=1,
        # terminal=1) → no deficit → the old healthy case greens the row.
        # Bucketed pairing keeps them apart: bucket (S, hashY) has
        # expected=1 case=0 → deficit → RED; the file-X case sits in its
        # own bucket (S, hashX) where surplus cases never mask anything.
        status, summary, detail = self._run_with_events([
            self._case("A", "sessA", 5.0, self.FILE_X),  # pre-C5: no id
            self._expected("sessA", 1.0, self.FILE_Y, review_id=self.R2),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["expected"], 1)
        self.assertEqual(row["expected_without_outcome_sessions"], 1)
        self.assertEqual(row["status"], "red")
        self.assertEqual(status, "red")
        self.assertIn("missing terminal outcome", summary)

    def test_old_matched_pair_never_offsets_new_dead_review(self):
        # r4 F2 variant with the old case fully MATCHED by its own
        # expected (the normal post-land healthy review of file X):
        # a later dead review of file Y must still escalate — bucket
        # (S, hashX) expected=1 case=1 balanced; bucket (S, hashY)
        # expected=1 case=0 → deficit → RED.
        status, _, detail = self._run_with_events([
            self._expected("sessA", 5.0, self.FILE_X, review_id=self.R1),
            self._case("A", "sessA", 4.5, self.FILE_X, review_id=self.R1),
            self._expected("sessA", 1.0, self.FILE_Y, review_id=self.R2),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["expected"], 2)
        self.assertEqual(row["expected_without_outcome_sessions"], 1)
        self.assertEqual(row["status"], "red")
        self.assertEqual(status, "red")

    def test_same_file_re_review_one_death_is_still_a_deficit(self):
        # r4 F2 boundary: bucketing must NOT weaken same-file detection —
        # two reviews of the SAME file where one dies land in ONE bucket
        # (S, hashX) with expected=2 case=1 → deficit → RED.
        status, _, detail = self._run_with_events([
            self._expected("sessA", 3.0, self.FILE_X, review_id=self.R1),
            self._case("A", "sessA", 2.5, self.FILE_X, review_id=self.R1),
            self._expected("sessA", 1.0, self.FILE_X, review_id=self.R2),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["expected"], 2)
        self.assertEqual(row["expected_without_outcome_sessions"], 1)
        self.assertEqual(row["status"], "red")
        self.assertEqual(status, "red")

    def test_r5_old_same_file_case_never_offsets_new_dead_review(self):
        # codex r5 F2 — THE same-file interleaving that (session,
        # file-hash) BUCKET COUNTING still false-greened: session S,
        # file X. An OLD completed `pair_rail_case` for (S, X) with its
        # own invocation id R1 (no expected of its own in-window — e.g.
        # its expected aged out), THEN a `pair_rail_review_expected` for
        # the SAME (S, X) under a NEW invocation id R2 whose hook DIED
        # before its case emit. The r4 bucket (S, hashX) balances 1:1
        # (expected=1, terminal=1) → counting reports no deficit → the
        # old healthy case greens the row. Invocation-id pairing keeps
        # them apart: R2 is EXPECTED with no matching case → outstanding
        # → RED. Counting fundamentally cannot pair a specific expected
        # with its OWN case; only the correlation id can.
        status, summary, detail = self._run_with_events([
            self._case("A", "sessA", 5.0, self.FILE_X, review_id=self.R1),
            self._expected("sessA", 1.0, self.FILE_X, review_id=self.R2),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["expected"], 1)
        self.assertEqual(row["expected_without_outcome_sessions"], 1)
        self.assertEqual(row["status"], "red")
        self.assertEqual(status, "red")
        self.assertIn("missing terminal outcome", summary)

    def test_r5_idless_old_case_same_file_never_offsets_id_dead_review(self):
        # r5 F2 mixed-era variant: the old completed case is a PRE-LAND
        # (id-less) event for the same (S, X); the later dead expected
        # carries an id (post-land producer). The id-less case sits in
        # the legacy "" bucket subset (surplus terminal — masks nothing);
        # R2 stays outstanding on the exact path → RED.
        status, _, detail = self._run_with_events([
            self._case("A", "sessA", 5.0, self.FILE_X),  # pre-land: no id
            self._expected("sessA", 1.0, self.FILE_X, review_id=self.R2),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["expected"], 1)
        self.assertEqual(row["expected_without_outcome_sessions"], 1)
        self.assertEqual(row["status"], "red")
        self.assertEqual(status, "red")

    def test_advisory_parse_miss_case_pairs_not_a_deficit(self):
        # r6 F1 — an ADVISORY/parse-miss review (codex RAN and ANSWERED
        # but the response parsed to no structured PASS/BLOCK) now emits
        # a terminal `pair_rail_case` (case=F, codex_verdict=ADVISORY)
        # carrying the SAME review_id as its expected, via the
        # `_decide_with_matrix` matrix_case-is-None arm. The pair must
        # NOT register as an S254 deficit (the rail did not die); the
        # row is laddered by the case buckets — here mixed with a
        # healthy Case A → yellow partial fail-open, never the
        # missing-terminal-outcome RED escalation.
        status, summary, detail = self._run_with_events([
            self._expected("sessA", 3.0, review_id=self.R1),
            {"ts": _iso_utc(2.5), "action": "pair_rail_case", "case": "F",
             "codex_verdict": "ADVISORY", "session_id": "sessA",
             "file_path_hash_prefix": self.FILE_X,
             "review_id": self.R1},
            self._expected("sessA", 2.0, review_id=self.R2),
            self._case("A", "sessA", 1.5, review_id=self.R2),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["expected"], 2)
        self.assertEqual(row["expected_without_outcome_sessions"], 0)
        self.assertEqual(row["failopen"], 1)  # advisory visible, non-green
        self.assertEqual(row["healthy"], 1)
        self.assertEqual(row["status"], "yellow")
        self.assertNotIn("missing terminal outcome", summary)
        self.assertEqual(status, "yellow")

    def test_advisory_only_window_is_ladder_red_not_s254_deficit(self):
        # r6 F1 boundary: a window whose ONLY activity is one paired
        # advisory/parse-miss review reds via the BASE ladder
        # ("fail-opened on ALL classified invocations" — TRUE: the rail
        # produced zero effective review coverage, same treatment as
        # the stop_review rail's skipped_failopen), NOT via the S254
        # deficit escalation (FALSE: nothing died — expected pairs its
        # own case by review_id, deficit stays 0).
        status, summary, detail = self._run_with_events([
            self._expected("sessA", review_id=self.R1),
            {"ts": _iso_utc(0.5), "action": "pair_rail_case", "case": "F",
             "codex_verdict": "ADVISORY", "session_id": "sessA",
             "file_path_hash_prefix": self.FILE_X,
             "review_id": self.R1},
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["expected_without_outcome_sessions"], 0)
        self.assertEqual(row["status"], "red")  # ladder, not deficit
        self.assertEqual(status, "red")
        self.assertNotIn("missing terminal outcome", summary)
        self.assertIn("fail-opened on ALL", summary)

    def test_advisory_pair_plus_true_death_still_reds_as_deficit(self):
        # r6 F1 companion: the deficit RED stays reserved for the
        # GENUINE S254 signal. Alongside a correctly paired
        # advisory/parse-miss review (R1), a second review (R2) whose
        # hook died between the expected emit and the case emit (zero
        # pair_rail_case) must still escalate as a deficit — the
        # advisory case can never satisfy R2's expected (different
        # review_id).
        status, summary, detail = self._run_with_events([
            self._expected("sessA", 3.0, review_id=self.R1),
            {"ts": _iso_utc(2.5), "action": "pair_rail_case", "case": "F",
             "codex_verdict": "ADVISORY", "session_id": "sessA",
             "file_path_hash_prefix": self.FILE_X,
             "review_id": self.R1},
            self._expected("sessA", 1.0, review_id=self.R2),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["expected"], 2)
        self.assertEqual(row["expected_without_outcome_sessions"], 1)
        self.assertEqual(row["status"], "red")
        self.assertEqual(status, "red")
        self.assertIn("missing terminal outcome", summary)

    def test_legacy_idless_pair_still_pairs_via_bucket_fallback(self):
        # r5 F2 fallback boundary: a fully PRE-LAND window (both emits
        # id-less) must keep pairing via the r4 (session, file-hash)
        # bucket-count heuristic — no false deficit on legacy events.
        _, _, detail = self._run_with_events([
            self._expected("sessA", 2.0, self.FILE_X),
            self._case("A", "sessA", 1.5, self.FILE_X),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["expected_without_outcome_sessions"], 0)
        self.assertEqual(row["status"], "green")

    def test_off_shape_expected_id_is_legacy_bucket_never_exact_key(self):
        # r6 F2 — the ALIASING probe: session S carries an OLDER
        # COMPLETED pair (expected R1 + case R1), then a NEW dead
        # review whose expected row carries an OFF-SHAPE 32-hex id
        # SHARING R1's 16-hex prefix (the r5 emitters truncated such a
        # value to R1 before validating, so the older terminal offset
        # the new dead review — false green; a forged/version-skewed
        # row can still carry the raw 32-hex). The off-shape id must
        # NEVER act as an exact pairing key: it is coerced to the ""
        # legacy bucket, where (sessA, FILE_X) has expected=1 with
        # terminal=0 (the R1 case pairs on the exact ledger) →
        # deficit → RED.
        status, summary, detail = self._run_with_events([
            self._expected("sessA", 5.0, review_id=self.R1),
            self._case("A", "sessA", 4.5, review_id=self.R1),
            self._expected("sessA", 1.0,
                           review_id=self.R1 + "ff00ff00ff00ff00"),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["expected"], 2)
        self.assertEqual(row["expected_without_outcome_sessions"], 1)
        self.assertEqual(row["status"], "red")
        self.assertEqual(status, "red")
        self.assertIn("missing terminal outcome", summary)

    def test_off_shape_terminal_id_never_offsets_dead_review(self):
        # r6 F2 terminal side: a dead expected under valid id R2 stays
        # RED even when case rows carry off-shape ids for the same
        # (session, file) — "abc" and a 32-hex sharing R2's prefix.
        # Both are coerced to the "" legacy terminal bucket and can
        # never satisfy R2's exact expected (a malformed id is not a
        # unique pairing token).
        status, summary, detail = self._run_with_events([
            self._expected("sessA", 2.0, review_id=self.R2),
            self._case("A", "sessA", 1.5, review_id="abc"),
            self._case("A", "sessA", 1.0, review_id=self.R2 + self.R3),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["expected"], 1)
        self.assertEqual(row["expected_without_outcome_sessions"], 1)
        self.assertEqual(row["status"], "red")
        self.assertEqual(status, "red")
        self.assertIn("missing terminal outcome", summary)

    def test_numeric_review_id_never_acts_as_exact_key(self):
        # r7 F1 — a JSON NUMBER review_id (forged/non-string producer):
        # str(1234567890123456) == "1234567890123456" is 16 chars all in
        # [0-9] (valid hex) and would match ^[0-9a-f]{16}$ if the consumer
        # stringified BEFORE the shape gate. THE codex r7 vector: session S
        # holds an older COMPLETED pair under the STRING id "1234...16"
        # (a legitimate 16-hex key), THEN a NEW dead review whose expected
        # row carries the NUMERIC id 1234567890123456 (no case — the review
        # died). Under the r6 consumer the numeric expected str()-aliases
        # onto the same exact key, so the OLD string terminal offsets the
        # dead numeric review in the (session, id) set → false GREEN. The
        # isinstance(str) gate routes the numeric id to the "" legacy
        # bucket instead, where (sessA, FILE_X) has an unpaired expected →
        # deficit → RED. (No numeric case row: the whole point is the
        # review died and only a STRING terminal exists.)
        numeric = 1234567890123456
        key = "1234567890123456"  # same digits as a STRING key
        status, summary, detail = self._run_with_events([
            self._expected("sessA", 5.0, review_id=key),
            self._case("A", "sessA", 4.5, review_id=key),
            {"ts": _iso_utc(1.0), "action": "pair_rail_review_expected",
             "session_id": "sessA", "tool_name": "Edit",
             "file_path_hash_prefix": self.FILE_X, "review_id": numeric},
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["status"], "red")
        self.assertEqual(status, "red")
        self.assertIn("missing terminal outcome", summary)

    def test_forged_duplicate_off_shape_ids_never_collapse_via_set(self):
        # r6 F2 — RED-first vs the r5 CONSUMER (ungated `_review_id`):
        # with off-shape ids admitted as exact keys, the (session, id)
        # SET collapsed two dead expecteds sharing one forged id into
        # ONE ledger entry, and a single forged terminal carrying the
        # same id offset BOTH → false green. Coerced to the "" legacy
        # bucket they are COUNTED, not set-deduped: expected=2 >
        # terminal=1 → deficit → RED. (With healthy ids this trace is
        # impossible — os.urandom mints one id per invocation — so the
        # gate only ever tightens forged/version-skewed rows.)
        forged = self.R1 + self.R2  # 32-hex — off-shape
        status, summary, detail = self._run_with_events([
            self._expected("sessA", 3.0, review_id=forged),
            self._expected("sessA", 2.0, review_id=forged),
            self._case("A", "sessA", 1.0, review_id=forged),
        ])
        row = detail["rails"]["pair_rail"]
        self.assertEqual(row["expected"], 2)
        self.assertEqual(row["expected_without_outcome_sessions"], 1)
        self.assertEqual(row["status"], "red")
        self.assertEqual(status, "red")
        self.assertIn("missing terminal outcome", summary)


# ---------------------------------------------------------------------------
# PLAN-161 W2 C5 r6 F2 — review_id exact-shape gate at the EMITTERS
# ---------------------------------------------------------------------------


class TestReviewIdEmitterShapeGate(TestEnvContext):
    """r6 F2 — emitters DROP an off-shape review_id (never truncate-then-accept).

    The r5 emitters truncated the value to ``[:16]`` BEFORE validating
    against ``{0,16}``, so an oversize id passed as its first 16 chars:
    two distinct off-shape ids sharing a 16-hex prefix collapsed to ONE
    pairing key on the wire, and an older terminal could offset a later
    dead review (the F2 false-green). RED-first vs r5: these assertions
    fail on truncate-then-accept emitters. ``_write_event`` is patched to
    a capture list — no durable audit row is ever written by this class.
    """

    VALID = "aa11aa11aa11aa11"

    @staticmethod
    def _audit_emit():
        import _lib.audit_emit as ae
        return ae

    def _capture_expected(self, review_id):
        ae = self._audit_emit()
        captured: List[Dict[str, Any]] = []
        with mock.patch.object(ae, "_write_event", captured.append):
            ae.emit_pair_rail_review_expected(
                session_id="sessA", tool_name="Edit", review_id=review_id,
            )
        self.assertEqual(len(captured), 1)
        return captured[0]

    def _capture_case(self, review_id):
        ae = self._audit_emit()
        captured: List[Dict[str, Any]] = []
        with mock.patch.object(ae, "_write_event", captured.append):
            ae.emit_pair_rail_case(
                case="A", claude_verdict="PASS", codex_verdict="PASS",
                tool_name="Edit",
                file_path_hash_prefix="ab12cd34ef56ab12",
                session_id="sessA", review_id=review_id,
            )
        self.assertEqual(len(captured), 1)
        return captured[0]

    def test_expected_emitter_drops_oversize_id_never_truncates(self):
        ev = self._capture_expected(self.VALID + "ff00ff00ff00ff00")
        self.assertEqual(ev["review_id"], "")  # dropped, NOT self.VALID

    def test_expected_emitter_drops_short_partial_and_offcharset(self):
        for bad in ("abc", "aa11aa11aa11aa1", "AA11AA11AA11AA11",
                    "zz11aa11aa11aa11"):
            ev = self._capture_expected(bad)
            self.assertEqual(ev["review_id"], "", bad)

    def test_expected_emitter_passes_exact_16_and_legacy_empty(self):
        for good in (self.VALID, ""):
            ev = self._capture_expected(good)
            self.assertEqual(ev["review_id"], good)

    def test_case_emitter_drops_oversize_id_never_truncates(self):
        ev = self._capture_case(self.VALID + "ff00ff00ff00ff00")
        self.assertEqual(ev["review_id"], "")  # dropped, NOT self.VALID

    def test_case_emitter_drops_short_and_offcharset(self):
        for bad in ("abc", "aa11aa11aa11aa1", "AA11AA11AA11AA11"):
            ev = self._capture_case(bad)
            self.assertEqual(ev["review_id"], "", bad)

    def test_case_emitter_passes_exact_16_and_legacy_empty(self):
        for good in (self.VALID, ""):
            ev = self._capture_case(good)
            self.assertEqual(ev["review_id"], good)

    def test_emit_generic_branch_applies_exact_gate(self):
        # Direct emit_generic callers hit the per-action dispatch-branch
        # re-coercion (raw-value validate, no truncation) — same gate.
        ae = self._audit_emit()
        for action in ("pair_rail_review_expected", "pair_rail_case"):
            captured: List[Dict[str, Any]] = []
            with mock.patch.object(ae, "_write_event", captured.append):
                ae.emit_generic(
                    action, session_id="sessA",
                    review_id=self.VALID + self.VALID,
                )
            self.assertEqual(len(captured), 1)
            self.assertEqual(captured[0]["review_id"], "", action)


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
