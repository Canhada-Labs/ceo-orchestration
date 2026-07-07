"""S127 cadence-amendment — tests for 24h + 7d persona-coverage checks.

Covers the Codex R2 thread `019e33a3` AMEND `PHASE-1+2-WITH-(c)` verdict:

  AMEND #1 — empty-window → green (matches no-data-green pattern of other
             17 Tier-S checks)
  AMEND #2 — 4×4 matrix demoted to permanent observability (max-yellow,
             never red, never gate-failing — RED authority moves to Phase 2
             demand ledger)
  AMEND #4 — input normalization: case-insensitive role match across
             `archetype` / `persona` / `subagent_type` /
             `dispatch_archetype_hint` fields

  Phase 1 scope-(b): audit-emit kernel allowlist amendment deferred to
                     Owner ceremony (the `_emit_persona_coverage` helper
                     emits only the 3 fields already in the allowlist;
                     `window_hours` / `events_with_target_archetype` /
                     `eligible_demand_events` surface only in the result
                     dict + summary).

Doctrine record: `.claude/plans/PLAN-093-FOLLOWUP-cadence-amendment.md`.

PLAN-112-FOLLOWUP-persona-routing-wire W4 (F-5.4-tasktype-pollution-2c9f0d77):
  `_score_persona_coverage` now only counts events whose `action` is a
  genuine persona-dispatch action (`persona_coverage_synthesized` +
  `persona_demand_*`). Unrelated emitters (e.g. `model_routing_advised`
  carrying `archetype=security-engineer` + `task_type=frontmatter`) no
  longer pollute the cell-count / events_with_target denominator. The
  fixtures below were migrated from the placeholder `action: agent_spawn`
  to the canonical `persona_coverage_synthesized` action accordingly
  (agent_spawn never actually carried a `task_type`/coverage signal —
  it was a fixture shorthand pre-dating the genuine emitter).
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
from typing import List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import importlib  # noqa: E402

ceo_boot = importlib.import_module("ceo-boot".replace("-", "_")) \
    if False else None  # placeholder; we use direct file-load below

# ceo-boot.py has a hyphen; importlib can't load via dotted path, use spec.
import importlib.util  # noqa: E402
_CEO_BOOT_PY = _SCRIPTS_DIR / "ceo-boot.py"
_spec = importlib.util.spec_from_file_location("ceo_boot_under_test",
                                                _CEO_BOOT_PY)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_offset(hours_ago: float) -> str:
    return (datetime.now(timezone.utc)
            - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


# Canonical persona-dispatch action used by the coverage fixtures. This is
# the genuine action `_emit_persona_coverage_synthesized` emits at the
# spawn-hook allow-path (SPEC/v1/audit-log.schema.md:319) and carries both
# `archetype` and `task_type` — the only fields the scorer reads.
_COVERAGE_ACTION = "persona_coverage_synthesized"


class _AuditLogContext:
    """Redirects the audit-log to a tmpdir for the duration of a test.

    Patches both `AUDIT_LOG_DEFAULT` and the `_iter_audit_events_since`
    function in the loaded ceo-boot module so the persona-coverage
    helpers read from our fixture instead of the real audit-log.
    """

    def __init__(self, events: List[dict]) -> None:
        self.events = events
        self._tmpdir: Optional[tempfile.TemporaryDirectory] = None
        self._saved_default: Optional[Path] = None

    def __enter__(self) -> Path:
        self._tmpdir = tempfile.TemporaryDirectory(prefix="ceo-boot-cadence-")
        tmpdir = Path(self._tmpdir.name)
        log = tmpdir / "audit-log.jsonl"
        with log.open("w", encoding="utf-8") as f:
            for ev in self.events:
                f.write(json.dumps(ev) + "\n")
        self._saved_default = _mod.AUDIT_LOG_DEFAULT
        _mod.AUDIT_LOG_DEFAULT = log
        return log

    def __exit__(self, *exc) -> None:
        if self._saved_default is not None:
            _mod.AUDIT_LOG_DEFAULT = self._saved_default
        if self._tmpdir is not None:
            self._tmpdir.cleanup()


class TestPersonaCoverageEmptyGreen(unittest.TestCase):
    """AMEND #1: empty window → green, matches no-data-green pattern."""

    def test_24h_empty_audit_log_returns_green(self) -> None:
        with _AuditLogContext([]):
            status, summary, detail = _mod.check_ceo_boot_persona_coverage_score()
        self.assertEqual(status, "green", f"expected green; got {status}: {summary}")
        self.assertIn("no VETO-floor dispatches", summary)
        self.assertIn("24h", summary)
        self.assertEqual(detail["events_with_target_archetype"], 0)
        self.assertEqual(detail["cells_covered"], 0)
        self.assertEqual(detail["window_hours"], 24)
        self.assertEqual(detail["eligible_demand_events"], 0)

    def test_7d_empty_audit_log_returns_green(self) -> None:
        # PLAN-104 Phase 2 rebaseline (Codex iter-1 P0 #6): the 19th
        # check now uses the demand-driven semantic. Empty audit-log
        # has no persona_demand_opened entries -> "no eligible persona
        # demand in 168h". Kill-switch CEO_PERSONA_DEMAND_LEDGER_DISABLED=1
        # restores the pre-PLAN-104 observability-only message.
        with _AuditLogContext([]):
            status, summary, detail = _mod.check_persona_atrophy_7d()
        self.assertEqual(status, "green")
        self.assertIn("no eligible persona demand in 168h", summary)
        self.assertEqual(detail["window_hours"], 168)
        self.assertEqual(detail["eligible_demand_events"], 0)

    def test_24h_only_nontarget_archetypes_returns_green(self) -> None:
        """Even with events present, if NONE match the 4 VETO-floor personas,
        return green (events_with_target_archetype == 0)."""
        events = [
            {"ts": _iso_offset(2.0), "action": _COVERAGE_ACTION,
             "archetype": "Explore", "task_type": "review"},
            {"ts": _iso_offset(4.0), "action": _COVERAGE_ACTION,
             "archetype": "general-purpose", "task_type": "test"},
            {"ts": _iso_offset(6.0), "action": _COVERAGE_ACTION,
             "archetype": "explore", "task_type": "vet"},
        ]
        with _AuditLogContext(events):
            status, summary, detail = _mod.check_ceo_boot_persona_coverage_score()
        self.assertEqual(status, "green")
        self.assertEqual(detail["events_with_target_archetype"], 0)


class TestPersonaCoverageMaxYellow(unittest.TestCase):
    """AMEND #2: matrix demoted to permanent observability — never red."""

    def test_24h_with_target_persona_returns_yellow_never_red(self) -> None:
        events = [
            {"ts": _iso_offset(1.0), "action": _COVERAGE_ACTION,
             "archetype": "code-reviewer", "task_type": "review"},
        ]
        with _AuditLogContext(events):
            status, summary, detail = _mod.check_ceo_boot_persona_coverage_score()
        self.assertEqual(status, "yellow", f"expected yellow; got {status}")
        self.assertIn("cells covered", summary)
        self.assertEqual(detail["events_with_target_archetype"], 1)
        self.assertEqual(detail["cells_covered"], 1)
        self.assertEqual(detail["total_cells"], 16)

    def test_24h_zero_coverage_with_signal_still_yellow_not_red(self) -> None:
        """A persona dispatched but with task_type not matching any of the 4
        canonical task substrings — observability surfaces the gap as yellow.
        Pre-S127 this would have been red (0/16=0% < 50%)."""
        events = [
            {"ts": _iso_offset(1.0), "action": _COVERAGE_ACTION,
             "archetype": "qa-architect", "task_type": ""},
            {"ts": _iso_offset(2.0), "action": _COVERAGE_ACTION,
             "archetype": "security-engineer", "task_type": "deploy"},
        ]
        with _AuditLogContext(events):
            status, summary, detail = _mod.check_ceo_boot_persona_coverage_score()
        self.assertEqual(status, "yellow",
                         f"max-yellow demotion broken: got {status}")
        self.assertEqual(detail["cells_covered"], 0)
        self.assertEqual(detail["events_with_target_archetype"], 2)

    def test_24h_full_coverage_stays_yellow_under_phase_1(self) -> None:
        """Even 16/16 cells covered remains yellow under Phase 1 observability
        semantic. Pre-S127 this would have been green (≥75%); the demotion
        intentionally collapses ALL non-empty cases to yellow so the channel
        cannot signal pass/fail until Phase 2 demand-driven gate ships."""
        events = []
        for persona in ("code-reviewer", "security-engineer",
                        "qa-architect", "threat-detection-engineer"):
            for task in ("review", "vet", "test", "detect"):
                events.append({
                    "ts": _iso_offset(1.0),
                    "action": _COVERAGE_ACTION,
                    "archetype": persona,
                    "task_type": task,
                })
        with _AuditLogContext(events):
            status, summary, detail = _mod.check_ceo_boot_persona_coverage_score()
        self.assertEqual(status, "yellow",
                         "matrix demoted to observability — full coverage is "
                         "still yellow under Phase 1 (RED authority reserved "
                         "for Phase 2 demand ledger)")
        self.assertEqual(detail["cells_covered"], 16)
        self.assertEqual(detail["total_cells"], 16)


class TestPersonaCoverageInputNormalization(unittest.TestCase):
    """AMEND #4: case-insensitive role match across all 4 emission surfaces."""

    def test_role_extracted_from_subagent_type_field(self) -> None:
        events = [
            {"ts": _iso_offset(1.0), "action": _COVERAGE_ACTION,
             "subagent_type": "code-reviewer", "task_type": "review"},
        ]
        with _AuditLogContext(events):
            status, _, detail = _mod.check_ceo_boot_persona_coverage_score()
        self.assertEqual(detail["events_with_target_archetype"], 1)
        self.assertEqual(detail["cells_covered"], 1)

    def test_role_extracted_from_dispatch_archetype_hint(self) -> None:
        events = [
            {"ts": _iso_offset(1.0), "action": _COVERAGE_ACTION,
             "dispatch_archetype_hint": "security-engineer",
             "task_type": "vet"},
        ]
        with _AuditLogContext(events):
            _, _, detail = _mod.check_ceo_boot_persona_coverage_score()
        self.assertEqual(detail["events_with_target_archetype"], 1)
        self.assertEqual(detail["cells_covered"], 1)

    def test_role_match_is_case_insensitive(self) -> None:
        events = [
            {"ts": _iso_offset(1.0), "action": _COVERAGE_ACTION,
             "archetype": "CODE-REVIEWER", "task_type": "Review"},
            {"ts": _iso_offset(2.0), "action": _COVERAGE_ACTION,
             "archetype": "Qa-Architect", "task_type": "TEST"},
        ]
        with _AuditLogContext(events):
            _, _, detail = _mod.check_ceo_boot_persona_coverage_score()
        self.assertEqual(detail["events_with_target_archetype"], 2)
        self.assertEqual(detail["cells_covered"], 2)

    def test_field_priority_archetype_wins_over_subagent_type(self) -> None:
        """When multiple role fields are present, `_normalize_persona_role`
        prefers `archetype` first (per audit_log.py canonical emit order)."""
        events = [
            {"ts": _iso_offset(1.0), "action": _COVERAGE_ACTION,
             "archetype": "code-reviewer",
             "subagent_type": "security-engineer",  # ignored
             "task_type": "review"},
        ]
        with _AuditLogContext(events):
            _, _, detail = _mod.check_ceo_boot_persona_coverage_score()
        self.assertEqual(detail["events_with_target_archetype"], 1)
        # Cell counted for code-reviewer/review, not security-engineer/review.
        self.assertEqual(detail["cells_covered"], 1)


class TestPersonaCoverageTaskTypePollutionFilter(unittest.TestCase):
    """PLAN-112-FOLLOWUP-persona-routing-wire W4 — F-5.4-tasktype-pollution.

    The scorer must only count events whose `action` is a genuine
    persona-dispatch action. Unrelated emitters that happen to carry a
    VETO-floor archetype AND a `task_type` (e.g. `model_routing_advised`
    with `archetype=security-engineer`, `task_type=frontmatter`) must NOT
    contribute to either the cell-count or the events_with_target
    denominator.
    """

    def test_score_persona_coverage_filters_non_persona_task_type(self) -> None:
        events = [
            # GENUINE persona-dispatch — counted (1 cell: security-engineer/vet).
            {"ts": _iso_offset(1.0), "action": "persona_coverage_synthesized",
             "archetype": "security-engineer", "task_type": "vet"},
            # POLLUTION: model_routing_advised emits archetype + a bogus
            # task_type (`frontmatter` / classify-class `M`). Pre-W4 this
            # inflated events_with_target and could flip cells. Post-W4 it is
            # excluded by the action-name allowlist.
            {"ts": _iso_offset(2.0), "action": "model_routing_advised",
             "archetype": "security-engineer", "task_type": "frontmatter"},
            {"ts": _iso_offset(3.0), "action": "model_routing_advised",
             "archetype": "code-reviewer", "task_type": "review"},
            {"ts": _iso_offset(4.0), "action": "model_routing_advised",
             "archetype": "qa-architect", "task_type": "test"},
            # Another genuine surface: persona_demand_matched carries
            # expected/actual persona but NO archetype/task_type the scorer
            # reads — it is in the allowlist so it counts toward
            # events_with_target only if it carries a recognizable role field;
            # here it does not, so it is a no-op (documents the allowlist
            # admits the action without crashing).
            {"ts": _iso_offset(5.0), "action": "persona_demand_matched",
             "expected_persona": "code-reviewer",
             "actual_persona": "code-reviewer"},
            # Pure noise action with a VETO-floor archetype + task_type —
            # excluded (this is the canonical F-5.4 pollution shape).
            {"ts": _iso_offset(6.0), "action": "agent_spawn",
             "archetype": "code-reviewer", "task_type": "review"},
        ]
        with _AuditLogContext(events):
            _, _, detail = _mod.check_ceo_boot_persona_coverage_score()
        # ONLY the persona_coverage_synthesized event contributes:
        #   security-engineer/vet -> 1 cell, 1 event_with_target.
        self.assertEqual(
            detail["events_with_target_archetype"], 1,
            "non-persona-dispatch events must be excluded from the "
            "events_with_target denominator (F-5.4-tasktype-pollution)",
        )
        self.assertEqual(
            detail["cells_covered"], 1,
            "only persona_coverage_synthesized/persona_demand_* events may "
            "contribute task_type cells",
        )

    def test_persona_demand_actions_are_admitted_by_filter(self) -> None:
        """A persona_demand_* event carrying a recognizable role + task_type
        IS counted (the allowlist admits the whole persona_demand_ family).
        Uses `archetype`/`task_type` (the fields the scorer reads) to prove
        admission rather than the production demand-event field shape."""
        events = [
            {"ts": _iso_offset(1.0), "action": "persona_demand_opened",
             "archetype": "qa-architect", "task_type": "test"},
        ]
        with _AuditLogContext(events):
            _, _, detail = _mod.check_ceo_boot_persona_coverage_score()
        self.assertEqual(detail["events_with_target_archetype"], 1)
        self.assertEqual(detail["cells_covered"], 1)


class TestPersonaCoverageEmitsCorrectFields(unittest.TestCase):
    """Phase 1 scope-(b): emit only the 3 kernel-allowlisted fields."""

    def test_emit_payload_only_3_legacy_fields(self) -> None:
        """The audit-emit call carries score_x100 / cells_covered /
        total_cells. New fields (window_hours / events_with_target_archetype
        / eligible_demand_events) are NOT persisted under Phase 1 — they
        live in the result dict only, awaiting the Owner ceremony for the
        kernel allowlist amendment."""
        captured: dict = {}

        class _StubEmit:
            def emit_generic(self, action, **kwargs):
                captured["action"] = action
                captured["kwargs"] = kwargs

        saved = _mod._audit_emit
        _mod._audit_emit = _StubEmit()
        try:
            events = [
                {"ts": _iso_offset(1.0), "action": _COVERAGE_ACTION,
                 "archetype": "qa-architect", "task_type": "test"},
            ]
            with _AuditLogContext(events):
                _mod.check_ceo_boot_persona_coverage_score()
        finally:
            _mod._audit_emit = saved

        self.assertEqual(captured.get("action"),
                         "ceo_boot_persona_coverage_score")
        # Phase 1 scope-(b): no new fields emitted.
        kwargs = captured.get("kwargs", {})
        self.assertIn("score_x100", kwargs)
        self.assertIn("cells_covered", kwargs)
        self.assertIn("total_cells", kwargs)
        self.assertNotIn("window_hours", kwargs,
                         "Phase 1 scope-(b): kernel allowlist amendment "
                         "deferred — window_hours must NOT be emitted")
        self.assertNotIn("events_with_target_archetype", kwargs)
        self.assertNotIn("eligible_demand_events", kwargs)


class TestTierSChecksRegistry(unittest.TestCase):
    """The 19th Tier-S check is wired into TIER_S_CHECKS."""

    def test_persona_atrophy_7d_in_registry(self) -> None:
        names = [name for name, _ in _mod.TIER_S_CHECKS]
        self.assertIn("persona_atrophy_7d", names)
        self.assertIn("ceo_boot_persona_coverage_score", names)

    def test_tier_s_checks_count_is_21(self) -> None:
        self.assertEqual(len(_mod.TIER_S_CHECKS), 23)  # PLAN-153 Wave E (+failopen_rail_liveness_7d, harness_config_gate)


if __name__ == "__main__":
    unittest.main()
