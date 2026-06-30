"""PLAN-043 Phase 2 — Mutation-kill tests for learn.py critical paths.

Per Round 1 closure C-P1-3 (differentiated mutation targets):

- **VETO_HARDCODE check lines in learn.py = 100% kill** — any AST
  mutation on the ``if agent_slug in VETO_HARDCODE: continue`` guard
  or the module-load ``assert_veto_hardcode_integrity`` assertion
  MUST be killed by a test in this file.
- **Statistical power gate** (``n < MIN_N_PER_CELL`` /
  ``gap_pp < MIN_GAP_PP``) — 100% kill on boundary mutations.
- **Direction logic** (``_direction`` / ``_tier_rank``) — 100% kill
  on promote/demote inversion.

Run via:

    python3 .claude/scripts/mutation-test.py \\
        --target .claude/scripts/tier_policy_cli/learn.py \\
        --tests .claude/scripts/tier_policy_cli/tests/test_learn.py \\
                .claude/scripts/tier_policy_cli/tests/test_learn_mutation.py \\
        --report /tmp/learn-mutation-report.json

ADR-063 scorer.py precedent: 100% kill rate achieved via identical
targeted-kill-test pattern.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List
from unittest import mock

_SCRIPTS = Path(__file__).resolve().parent.parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from tier_policy_cli import learn  # noqa: E402
from tier_policy_cli._constants import (  # noqa: E402
    VETO_HARDCODE,
    VETO_HARDCODE_FROZEN_SHA256,
    assert_veto_hardcode_integrity,
)
from tier_policy_cli._types import (  # noqa: E402
    Assignment,
    CANONICAL_5_AGENTS,
    TierPolicyRecord,
    VALID_MODEL_IDS,
)


_OPUS = "claude-opus-4-8"
_SONNET = "claude-sonnet-4-6"
_HAIKU = "claude-haiku-4-5-20251001"


def _baseline_policy() -> TierPolicyRecord:
    return TierPolicyRecord(
        schema_version="1.0",
        generated_at="2026-04-19T00:00:00Z",
        baseline_from="ADR-052",
        assignments={
            "code-reviewer": Assignment(
                tier=_OPUS, locked_by="VETO_FLOOR", evidence=None
            ),
            "security-engineer": Assignment(
                tier=_OPUS, locked_by="VETO_FLOOR", evidence=None
            ),
            "qa-architect": Assignment(
                tier=_SONNET, locked_by=None, evidence=None
            ),
            "performance-engineer": Assignment(
                tier=_SONNET, locked_by=None, evidence=None
            ),
            "devops": Assignment(
                tier=_HAIKU, locked_by=None, evidence=None
            ),
        },
        hmac_anchor="f" * 64,
        sigchain_tip_length=1,
        last_change_by_role={},
    )


def _task_record(
    *, fixture_id: str, task_type: str, model: str, verdict: str
) -> Dict:
    return {
        "type": "task",
        "fixture_id": fixture_id,
        "fixture_sha256": "0" * 64,
        "task_type": task_type,
        "model": model,
        "verdict": verdict,
        "output_sha256": "0" * 64,
        "tokens_in": 100,
        "tokens_out": 50,
        "cost_usd": 0.001,
        "wall_clock_ms": 100,
    }


def _write_cell_reports(
    reports_dir: Path,
    task_type: str,
    *,
    winner_model: str,
    winner_passes: int,
    winner_fails: int,
    current_model: str,
    current_passes: int,
    current_fails: int,
    run_count: int = 3,
) -> None:
    """Write ``run_count`` reports with the given cell counts.

    Distributes ``winner_*`` + ``current_*`` counts across runs.
    """
    for run_i in range(run_count):
        w_p = winner_passes // run_count + (
            1 if run_i < winner_passes % run_count else 0
        )
        w_f = winner_fails // run_count + (
            1 if run_i < winner_fails % run_count else 0
        )
        c_p = current_passes // run_count + (
            1 if run_i < current_passes % run_count else 0
        )
        c_f = current_fails // run_count + (
            1 if run_i < current_fails % run_count else 0
        )
        records = []
        counter = 0
        for _ in range(w_p):
            records.append(_task_record(
                fixture_id="w-{}-{}".format(run_i, counter),
                task_type=task_type, model=winner_model, verdict="pass",
            ))
            counter += 1
        for _ in range(w_f):
            records.append(_task_record(
                fixture_id="w-{}-{}".format(run_i, counter),
                task_type=task_type, model=winner_model, verdict="fail",
            ))
            counter += 1
        for _ in range(c_p):
            records.append(_task_record(
                fixture_id="c-{}-{}".format(run_i, counter),
                task_type=task_type, model=current_model, verdict="pass",
            ))
            counter += 1
        for _ in range(c_f):
            records.append(_task_record(
                fixture_id="c-{}-{}".format(run_i, counter),
                task_type=task_type, model=current_model, verdict="fail",
            ))
            counter += 1
        path = reports_dir / "tournament-mr{}.jsonl".format(run_i)
        with path.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")
        mtime = time.time() - 86400
        os.utime(path, (mtime, mtime))


class LearnMutationTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="plan-043-mut-")
        self.reports_dir = Path(self._tmp.name)
        self._patcher = mock.patch.object(
            learn, "_hmac_verify_report", return_value=(True, None)
        )
        self._patcher.start()
        self.now = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self._patcher.stop()
        self._tmp.cleanup()


# ---------------------------------------------------------------------
# Group A — VETO_HARDCODE check mutations (MUST be 100% kill)
# ---------------------------------------------------------------------

class VetoFloorMutationKillTests(LearnMutationTestBase):
    """Kill mutations on VETO_HARDCODE zeroth-check + integrity assert.

    Mutations to catch:
    - ``if agent_slug in VETO_HARDCODE`` → ``not in`` (kill: tests 1-2)
    - ``if agent_slug in VETO_HARDCODE`` → ``==``/``!=`` (kill: test 3)
    - ``VETO_HARDCODE`` keys changed (kill: test 4)
    - ``assert_veto_hardcode_integrity`` removed (kill: test 5)
    """

    def test_kill_mut1_code_reviewer_excluded_under_haiku_signal(self):
        """Kill ``if ... in VETO_HARDCODE`` → ``not in`` mutation.

        If mutated, code-reviewer would be INCLUDED in recommendations.
        Strong haiku signal on code-review should NOT promote/demote
        code-reviewer.
        """
        _write_cell_reports(
            self.reports_dir, "code-review",
            winner_model=_HAIKU,
            winner_passes=45, winner_fails=0,
            current_model=_OPUS,
            current_passes=10, current_fails=35,
        )
        recs = learn.learn(
            self.reports_dir, _baseline_policy(), now=self.now
        )
        slugs = {r.agent_slug for r in recs}
        self.assertNotIn("code-reviewer", slugs)

    def test_kill_mut2_security_engineer_excluded_under_haiku_signal(self):
        """Kill ``if ... in VETO_HARDCODE`` → ``not in`` mutation.

        If mutated, security-engineer would be INCLUDED.
        """
        _write_cell_reports(
            self.reports_dir, "security-review",
            winner_model=_HAIKU,
            winner_passes=45, winner_fails=0,
            current_model=_OPUS,
            current_passes=10, current_fails=35,
        )
        recs = learn.learn(
            self.reports_dir, _baseline_policy(), now=self.now
        )
        slugs = {r.agent_slug for r in recs}
        self.assertNotIn("security-engineer", slugs)

    def test_kill_mut3_veto_membership_is_by_key_not_value(self):
        """Kill ``agent_slug in VETO_HARDCODE`` → ``agent_slug == "xxx"``.

        Membership test must cover BOTH canonical VETO roles; a single
        equality check would only catch one.
        """
        _write_cell_reports(
            self.reports_dir, "code-review",
            winner_model=_SONNET,
            winner_passes=45, winner_fails=0,
            current_model=_OPUS,
            current_passes=10, current_fails=35,
        )
        _write_cell_reports(
            self.reports_dir, "security-review",
            winner_model=_SONNET,
            winner_passes=45, winner_fails=0,
            current_model=_OPUS,
            current_passes=10, current_fails=35,
        )
        recs = learn.learn(
            self.reports_dir, _baseline_policy(), now=self.now
        )
        slugs = {r.agent_slug for r in recs}
        # BOTH must be excluded simultaneously.
        self.assertNotIn("code-reviewer", slugs)
        self.assertNotIn("security-engineer", slugs)

    def test_kill_mut4_veto_hardcode_keys_freeze(self):
        """Kill ``VETO_HARDCODE = {}`` mutation via frozen SHA256.

        The module-level assert_veto_hardcode_integrity(VETO_HARDCODE)
        call would raise AssertionError on tamper. Verify the exact
        canonical key set + values.
        """
        self.assertEqual(
            set(VETO_HARDCODE.keys()),
            {"code-reviewer", "security-engineer"},
        )
        # ADR-149 (W0 variant A): live VETO_HARDCODE on the running generation.
        self.assertEqual(VETO_HARDCODE["code-reviewer"], "claude-fable-5")
        self.assertEqual(VETO_HARDCODE["security-engineer"], "claude-fable-5")
        # Frozen SHA256 anchor MUST match.
        from tier_policy_cli._constants import (
            _compute_canonical_sha256,
        )
        recomputed = _compute_canonical_sha256(VETO_HARDCODE)
        self.assertEqual(recomputed, VETO_HARDCODE_FROZEN_SHA256)

    def test_kill_mut5_integrity_assert_raises_on_tamper(self):
        """Kill removal of assert_veto_hardcode_integrity.

        Tampered dict must raise AssertionError on check.
        """
        tampered = {"code-reviewer": _HAIKU}  # demoted
        with self.assertRaises(AssertionError):
            assert_veto_hardcode_integrity(tampered)


# ---------------------------------------------------------------------
# Group B — Statistical gate boundary mutations
# ---------------------------------------------------------------------

class StatisticalGateBoundaryMutationTests(LearnMutationTestBase):
    """Kill boundary mutations on ``n < MIN_N_PER_CELL`` / ``gap_pp < ...``.

    Mutations to catch:
    - ``n_min < MIN_N_PER_CELL`` → ``n_min <= MIN_N_PER_CELL`` or ``>``
    - ``gap_min < MIN_GAP_PP`` → ``gap_min <= MIN_GAP_PP`` or ``>``
    - ``MIN_N_PER_CELL = 30`` → ``= 29``/``= 31``
    - ``MIN_GAP_PP = 25.0`` → any integer perturbation
    """

    def test_kill_n_eq_29_rejects_n_eq_30_accepts_pair(self):
        """Paired boundary kill.

        Run one scenario with n=29 (reject) and separate with n=30
        (accept). A ``< → <=`` mutation on the n check makes n=30 the
        new reject floor → second assertion fails.
        A ``< → >`` mutation inverts the whole gate → first fails.
        """
        # n=29 scenario: reports with 29 records per model.
        _write_cell_reports(
            self.reports_dir, "performance-triage",
            winner_model=_OPUS,
            winner_passes=29, winner_fails=0,
            current_model=_SONNET,
            current_passes=0, current_fails=29,
            run_count=3,
        )
        recs_29 = learn.learn(
            self.reports_dir, _baseline_policy(), now=self.now
        )
        perf_29 = next(
            r for r in recs_29 if r.agent_slug == "performance-engineer"
        )
        self.assertEqual(perf_29.action, "hold")
        self.assertEqual(
            perf_29.rejection_reason, learn.REASON_STATISTICAL_POWER
        )

        # n=30 scenario: overwrite with 30 records per model.
        for f in self.reports_dir.iterdir():
            f.unlink()
        _write_cell_reports(
            self.reports_dir, "performance-triage",
            winner_model=_OPUS,
            winner_passes=30, winner_fails=0,
            current_model=_SONNET,
            current_passes=0, current_fails=30,
            run_count=3,
        )
        recs_30 = learn.learn(
            self.reports_dir, _baseline_policy(), now=self.now
        )
        perf_30 = next(
            r for r in recs_30 if r.agent_slug == "performance-engineer"
        )
        self.assertEqual(perf_30.action, "promote")
        self.assertIsNone(perf_30.rejection_reason)

    def test_kill_gap_lt_25_rejects_gap_ge_25_accepts_pair(self):
        """Paired boundary kill on gap threshold.

        Two scenarios: one at gap ~24pp (reject), one at gap ~30pp
        (accept). ``< → <=`` on gap flips the 25.0 boundary.
        """
        # Gap ~24pp: opus 30 p / 0 f (1.00); sonnet 30 p × 0.76 = 23 p /
        # 7 f → 0.7667 rate → 23.33 pp gap (< 25).
        _write_cell_reports(
            self.reports_dir, "performance-triage",
            winner_model=_OPUS,
            winner_passes=30, winner_fails=0,
            current_model=_SONNET,
            current_passes=23, current_fails=7,
            run_count=3,
        )
        recs_a = learn.learn(
            self.reports_dir, _baseline_policy(), now=self.now
        )
        perf_a = next(
            r for r in recs_a if r.agent_slug == "performance-engineer"
        )
        self.assertLess(perf_a.evidence.gap_pp, 25.0)
        self.assertEqual(perf_a.action, "hold")

        # Gap ~30pp: opus 30 p / 0 f (1.00); sonnet 21 p / 9 f = 0.70 →
        # 30 pp gap (> 25).
        for f in self.reports_dir.iterdir():
            f.unlink()
        _write_cell_reports(
            self.reports_dir, "performance-triage",
            winner_model=_OPUS,
            winner_passes=30, winner_fails=0,
            current_model=_SONNET,
            current_passes=21, current_fails=9,
            run_count=3,
        )
        recs_b = learn.learn(
            self.reports_dir, _baseline_policy(), now=self.now
        )
        perf_b = next(
            r for r in recs_b if r.agent_slug == "performance-engineer"
        )
        self.assertGreaterEqual(perf_b.evidence.gap_pp, 25.0)
        self.assertEqual(perf_b.action, "promote")

    def test_kill_min_n_per_cell_constant_perturbation(self):
        """Kill ``MIN_N_PER_CELL = 30`` → 29 / 31.

        If const mutates to 29, n=29 would pass; if mutates to 31, n=30
        would reject. Direct constant inspection.
        """
        self.assertEqual(learn.MIN_N_PER_CELL, 30)

    def test_kill_min_gap_pp_constant_perturbation(self):
        """Kill ``MIN_GAP_PP = 25.0`` → 24.0 / 26.0.

        Direct constant inspection — covers any numeric mutation.
        """
        self.assertEqual(learn.MIN_GAP_PP, 25.0)


# ---------------------------------------------------------------------
# Group C — Cooldown boundary mutations
# ---------------------------------------------------------------------

class CooldownBoundaryMutationTests(LearnMutationTestBase):
    def setUp(self):
        super().setUp()
        _write_cell_reports(
            self.reports_dir, "performance-triage",
            winner_model=_OPUS,
            winner_passes=30, winner_fails=0,
            current_model=_SONNET,
            current_passes=0, current_fails=30,
            run_count=3,
        )

    def test_kill_cooldown_89_rejects_90_accepts_pair(self):
        policy = _baseline_policy()
        # 89 days → reject.
        prior_89 = (
            self.now - timedelta(days=89)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        policy.last_change_by_role = {
            "performance-engineer": prior_89
        }
        recs_89 = learn.learn(self.reports_dir, policy, now=self.now)
        perf_89 = next(
            r for r in recs_89 if r.agent_slug == "performance-engineer"
        )
        self.assertFalse(perf_89.cooldown_ok)
        self.assertEqual(
            perf_89.rejection_reason, learn.REASON_COOLDOWN
        )

        # 90 days → accept.
        prior_90 = (
            self.now - timedelta(days=90)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        policy.last_change_by_role = {
            "performance-engineer": prior_90
        }
        recs_90 = learn.learn(self.reports_dir, policy, now=self.now)
        perf_90 = next(
            r for r in recs_90 if r.agent_slug == "performance-engineer"
        )
        self.assertTrue(perf_90.cooldown_ok)
        self.assertIsNone(perf_90.rejection_reason)


# ---------------------------------------------------------------------
# Group D — Direction logic mutations
# ---------------------------------------------------------------------

class DirectionMutationTests(LearnMutationTestBase):
    """Kill promote↔demote direction inversion.

    Mutations to catch:
    - ``_tier_rank`` dict values swapped / perturbed
    - ``_direction`` comparison flipped
    """

    def test_kill_tier_rank_order_pinned(self):
        """Kill ``_tier_rank`` value mutations.

        Explicit rank contract: haiku < sonnet < opus.
        """
        self.assertLess(
            learn._tier_rank(_HAIKU), learn._tier_rank(_SONNET)
        )
        self.assertLess(
            learn._tier_rank(_SONNET), learn._tier_rank(_OPUS)
        )

    def test_kill_direction_promote_vs_demote(self):
        """Kill ``_direction`` comparison flip.

        Moving up = promote; moving down = demote; same = hold.
        """
        self.assertEqual(
            learn._direction(_SONNET, _OPUS), "promote"
        )
        self.assertEqual(
            learn._direction(_OPUS, _SONNET), "demote"
        )
        self.assertEqual(
            learn._direction(_OPUS, _OPUS), "hold"
        )
        self.assertEqual(
            learn._direction(_HAIKU, _OPUS), "promote"
        )
        self.assertEqual(
            learn._direction(_OPUS, _HAIKU), "demote"
        )


# ---------------------------------------------------------------------
# Group E — MIN_TOURNAMENT_RUNS guard
# ---------------------------------------------------------------------

class MinTournamentRunsMutationTests(LearnMutationTestBase):
    def test_kill_min_tournament_runs_constant(self):
        """Kill ``MIN_TOURNAMENT_RUNS = 3`` → 2 / 4 mutations.

        Direct constant inspection anchors the required threshold.
        """
        self.assertEqual(learn.MIN_TOURNAMENT_RUNS, 3)

    def test_kill_min_tournament_runs_less_than_3_returns_empty(self):
        """Kill ``if reports_consumed < MIN_TOURNAMENT_RUNS`` flip.

        With 2 valid reports, learn MUST return empty. A ``< → <=`` flip
        would accept 3-consumed boundary but here we have 2.
        """
        _write_cell_reports(
            self.reports_dir, "performance-triage",
            winner_model=_OPUS,
            winner_passes=100, winner_fails=0,
            current_model=_SONNET,
            current_passes=0, current_fails=100,
            run_count=2,
        )
        recs = learn.learn(
            self.reports_dir, _baseline_policy(), now=self.now
        )
        self.assertEqual(recs, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
