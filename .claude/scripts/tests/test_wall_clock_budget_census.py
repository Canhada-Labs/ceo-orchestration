"""Ratchet inventory for direct, absolute wall-clock assertions.

The parser follows simple ``time`` aliases and values assigned from them. It
covers pytest ``assert`` and unittest comparison methods in the configured
``testpaths`` only. It intentionally does not follow calls or arbitrary data
flow across functions; those need a separate semantic test.
"""
from __future__ import annotations

import ast
import configparser
import fnmatch
from pathlib import Path
from typing import Iterable, Set

import pytest


_REPO = Path(__file__).resolve().parents[3]
_METHODS = {"perf_counter", "monotonic", "time"}
_UNITTEST = {"assertLess", "assertLessEqual", "assertGreater", "assertGreaterEqual"}
_BASELINE = (
    '.claude/hooks/_lib/tests/test_goap_planner.py::TestCycleDetection::test_cyclic_actions_terminate',
    '.claude/hooks/_lib/tests/test_goap_planner.py::TestLatency::test_planner_latency_below_target',
    '.claude/hooks/tests/test_adversary_rules_live.py::LiveRegexBudgetTests::test_catastrophic_regex_fails_open_within_budget_and_continues',
    '.claude/hooks/tests/test_audit_log_phase1.py::TestSecHardening::test_redos_adversarial_no_explosion',
    '.claude/hooks/tests/test_check_canonical_edit_markers.py::CheckCanonicalEditMarkersTest::test_redos_64kb_no_match_under_100ms',
    '.claude/hooks/tests/test_check_canonical_edit_markers.py::CheckCanonicalEditMarkersTest::test_redos_large_match_under_100ms',
    '.claude/hooks/tests/test_check_fluency_nudge.py::IntegrationMainTests::test_large_output_over_100kb_does_not_hang',
    '.claude/hooks/tests/test_check_mcp_response.py::CheckMcpResponseSmokeTest::test_completes_under_5s_budget',
    '.claude/hooks/tests/test_check_protocol_semver_cascade_synccascade.py::TestSyncCascade::test_deadline_respected_marks_indeterminate_and_returns_fast',
    '.claude/hooks/tests/test_check_protocol_semver_cascade_synccascade.py::TestSyncCascade::test_within_budget_completes_under_two_seconds',
    '.claude/hooks/tests/test_codex_egress_redact.py::TestPerformanceBudget::test_32kb_redact_under_500ms',
    '.claude/hooks/tests/test_filelock.py::TestFileLock::test_timeout_raises_when_contended',
    '.claude/hooks/tests/test_lifecycle_edge_cases.py::TestLargePayloads::test_output_scan_1mb_completes',
    '.claude/hooks/tests/test_lifecycle_edge_cases.py::TestLargePayloads::test_pathological_regex_input',
    '.claude/hooks/tests/test_lifecycle_edge_cases.py::TestLargePayloads::test_prompt_submit_1mb_completes',
    '.claude/hooks/tests/test_otel_bounded_exporter.py::TestFlush::test_flush_respects_timeout',
    '.claude/hooks/tests/test_otel_queue.py::TestBlockPolicy::test_block_succeeds_when_drained_in_time',
    '.claude/hooks/tests/test_otel_queue.py::TestBlockPolicy::test_block_times_out',
    '.claude/hooks/tests/test_output_scan.py::PLAN050Phase3PerfBudgetTests::test_100kb_clean_text_under_500ms',
    '.claude/hooks/tests/test_policy_redos_guards.py::TestEmptyValues::test_regex_empty_pattern_loads_or_rejects_cleanly',
    '.claude/hooks/tests/test_rag_bridge.py::TestDeadCache::test_dead_short_circuits_next_calls',
    '.claude/hooks/tests/test_rag_bridge.py::TestFailOpen10::test_fail_open_timeout',
    '.claude/hooks/tests/test_redact_redos.py::TestRedactPreviewEntrypoint::test_preview_truncates_input_before_regex',
    '.claude/hooks/tests/test_redact_redos.py::TestRedactReDoSAdversarial::test_kv_value_overlong_secrets_bounded_by_input_cap',
    '.claude/hooks/tests/test_secret_patterns.py::test_scan_completes_under_500ms_on_100kb_no_match',
    '.claude/hooks/tests/test_secret_patterns.py::test_scan_completes_under_budget_on_normal_text',
    '.claude/hooks/tests/test_session_end_memory_delta.py::TestSpecSurface::test_compact_restart_second_start_does_not_shrink_window',
    '.claude/hooks/tests/test_skill_unknown_ratio_path_d.py::SkillUnknownPathDTests::test_adversarial_1mib_skill_near_miss_redos_bound',
    '.claude/hooks/tests/test_user_prompt_submit.py::TestUserPromptSubmitReDoS::test_catastrophic_input_completes_under_200ms',
    '.claude/scripts/optimizer/tests/test_codex_phase_gate.py::test_redos_adversarial_summary_fast',
    '.claude/scripts/optimizer/tests/test_codex_phase_gate.py::test_redos_adversarial_thread_id_fast',
    '.claude/scripts/optimizer/tests/test_codex_phase_gate.py::test_review_phase_with_adversarial_codex_text_fast',
    '.claude/scripts/swarm/tests/test_coordinator_production_integration.py::test_coordinator_halt_triggers_real_escalated_kill_outcome',
    '.claude/scripts/swarm/tests/test_coordinator_tick.py::test_tick_wall_clock_ceiling_halts',
    '.claude/scripts/swarm/tests/test_kill_switch.py::test_cb_8_wall_clock_triggers_halt_when_elapsed',
    '.claude/scripts/swarm/tests/test_loop_runner_sentinel_revocation_slo.py::TestSentinelRevocationSLO::test_revocation_propagates_under_slo',
    '.claude/scripts/swarm/tests/test_parent_death_integration.py::test_child_killed_on_parent_sigkill',
    '.claude/scripts/swarm/tests/test_process_group.py::test_escalated_kill_tier1_escalates_to_sigkill_when_hanging',
    '.claude/scripts/swarm/tests/test_process_group.py::test_escalated_kill_tier2_immediate_sigkill',
    '.claude/scripts/swarm/tests/test_process_group_reap.py::test_escalated_kill_tier1_cooperative_under_200ms',
    '.claude/scripts/swarm/tests/test_process_group_reap.py::test_escalated_kill_tier2_post_kill_reap',
    '.claude/scripts/swarm/tests/test_process_group_reap.py::test_wait_for_death_detects_child_exit_under_50ms_poll',
    '.claude/scripts/swarm/tests/test_process_group_reap.py::test_wait_for_death_returns_false_for_live_pid_on_timeout',
    '.claude/scripts/tests/test_audit_query.py::TestStreamingPerformance::test_100k_by_skill_streams_under_budget',
    '.claude/scripts/tests/test_audit_query.py::TestStreamingPerformance::test_100k_search_streams_under_budget',
    '.claude/scripts/tests/test_audit_query.py::TestStreamingPerformance::test_100k_streamable_does_not_materialize_in_main',
    '.claude/scripts/tests/test_audit_query.py::TestStreamingPerformance::test_100k_summary_streams_under_budget',
    '.claude/scripts/tests/test_backup_audit.py::TestFilelockContention::test_backup_waits_for_writer_lock',
    '.claude/scripts/tests/test_ceo_boot.py::TestDispatcher::test_dispatch_fits_aggregate_budget',
    '.claude/scripts/tests/test_ceo_boot_enhanced.py::TestVerboseMode::test_dispatch_verbose_budget_10s',
    '.claude/scripts/tests/test_check_contamination_personal_path.py::RailRound21CuresTheR13Architecture::test_a_long_separator_run_is_no_longer_quadratic',
    '.claude/scripts/tests/test_check_contamination_personal_path.py::RailRound22MechanismCures::test_the_row_parser_is_not_quadratic',
    '.claude/scripts/tests/test_drift_wire.py::DriftDetectorWireTests::test_mock_clock_over_budget',
    '.claude/scripts/tests/test_drift_wire.py::DriftDetectorWireTests::test_mock_clock_under_budget',
    '.claude/scripts/tests/test_extract_skill.py::TestSecurityHardening::test_sec_redos_long_input_no_match',
    '.claude/scripts/tests/test_extract_skill.py::TestSecurityHardening::test_sec_redos_pathological_alternation',
    '.claude/scripts/tests/test_fan_plan_parser.py::TestFanPlanRedos::test_pathological_line_is_linear',
    '.claude/scripts/tests/test_skill_patch_shadow_race.py::ShadowApplyConcurrencyTest::test_different_skills_apply_concurrently',
    '.claude/scripts/tests/test_skill_patch_shadow_race.py::ShadowApplyConcurrencyTest::test_lock_released_on_normal_exit',
    '.claude/scripts/tests/test_upgrade_settings_migration.py::TestClaudeCodeFloor::test_a_hanging_cli_is_stopped_and_the_run_goes_on',
    '.claude/scripts/tournament/tests/test_tournament_e2e_smoke.py::TestE2ESmoke::test_full_pipeline_under_10s',
    'tests/chaos/test_audit_disk_full.py::test_audit_emit_swallows_enospc',
    'tests/chaos/test_audit_disk_full.py::test_otel_exporter_stops_adding_pressure',
    'tests/chaos/test_live_adapter_failure_injection.py::test_mode_slow_body_read_timeout',
    'tests/chaos/test_live_breaker.py::test_breaker_fails_fast_under_50ms_when_open',
    'tests/load/test_governance_100_parallel.py::test_all_hooks_racing_on_shared_audit_log',
    'tests/load/test_governance_100_parallel.py::test_hook_100_parallel_no_deadlock',
)


def _test_roots(repo) -> Iterable[Path]:
    config = configparser.ConfigParser(interpolation=None)
    config.read(repo / "pytest.ini", encoding="utf-8")
    for line in config["pytest"]["testpaths"].splitlines():
        value = line.strip()
        if value:
            yield repo / value


def _time_aliases(tree: ast.AST) -> Set[str]:
    aliases = {"time"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            aliases.update(alias.asname or alias.name for alias in node.names if alias.name == "time")
        if isinstance(node, ast.ImportFrom) and node.module == "time":
            aliases.update(alias.asname or alias.name for alias in node.names if alias.name in _METHODS)
    return aliases


def _is_clock_call(node: ast.AST, aliases: Set[str]) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Name):
        return node.func.id in aliases
    return (
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in aliases
        and node.func.attr in _METHODS
    )


def _depends_on_clock(node: ast.AST, values: Set[str], aliases: Set[str]) -> bool:
    return any(
        _is_clock_call(part, aliases) or isinstance(part, ast.Name) and part.id in values
        for part in ast.walk(node)
    )


def _clock_values(test: ast.AST, aliases: Set[str]) -> Set[str]:
    values = set()
    changed = True
    while changed:
        changed = False
        for node in ast.walk(test):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                continue
            if not _depends_on_clock(node.value, values, aliases):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id not in values:
                    values.add(target.id)
                    changed = True
    return values


def _relative_ratio(node: ast.AST, values: Set[str], aliases: Set[str]) -> bool:
    return (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Div)
        and _depends_on_clock(node.left, values, aliases)
        and _depends_on_clock(node.right, values, aliases)
    )


def _comparison_is_absolute(left: ast.AST, right: ast.AST, values: Set[str], aliases: Set[str]) -> bool:
    left_clock = _depends_on_clock(left, values, aliases)
    right_clock = _depends_on_clock(right, values, aliases)
    if left_clock == right_clock:
        return False
    clock_side = left if left_clock else right
    return not _relative_ratio(clock_side, values, aliases)


def _has_absolute_clock_assertion(test: ast.AST, aliases: Set[str]) -> bool:
    values = _clock_values(test, aliases)
    # Ratios stored in a variable are dimensionless too, not absolute durations.
    for node in ast.walk(test):
        if isinstance(node, ast.Assign) and _relative_ratio(node.value, values, aliases):
            values.difference_update(target.id for target in node.targets if isinstance(target, ast.Name))
    for node in ast.walk(test):
        if isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare):
            operands = [node.test.left] + node.test.comparators
            if any(_comparison_is_absolute(a, b, values, aliases) for a, b in zip(operands, operands[1:])):
                return True
        if not isinstance(node, ast.Call) or len(node.args) < 2:
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr in _UNITTEST:
            if _comparison_is_absolute(node.args[0], node.args[1], values, aliases):
                return True
    return False


def _node_id(path: Path, parents: Iterable[ast.AST], node: ast.AST, repo: Path) -> str:
    classes = [parent.name for parent in parents if isinstance(parent, ast.ClassDef)]
    suffix = "::".join(classes + [node.name])
    return "%s::%s" % (path.relative_to(repo), suffix)


def _census(repo=_REPO) -> Set[str]:
    found = set()
    config = configparser.ConfigParser(interpolation=None)
    config.read(repo / "pytest.ini", encoding="utf-8")
    excluded = config["pytest"].get("norecursedirs", "*.egg .* _darcs build CVS dist node_modules venv").split()
    for root in _test_roots(repo):
        for path in root.rglob("test_*.py"):
            if any(fnmatch.fnmatch(part, pattern) for part in path.relative_to(root).parts[:-1] for pattern in excluded):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            aliases = _time_aliases(tree)
            stack = []

            def visit(node):
                stack.append(node)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                    if _has_absolute_clock_assertion(node, aliases):
                        found.add(_node_id(path, stack[:-1], node, repo))
                for child in ast.iter_child_nodes(node):
                    visit(child)
                stack.pop()

            visit(tree)
    return found


def test_absolute_wall_clock_budget_inventory_is_a_ratchet() -> None:
    found = _census()
    baseline = list(_BASELINE)
    assert baseline == sorted(set(baseline))
    assert found == set(baseline), {"new": sorted(found - set(baseline)), "removed": sorted(set(baseline) - found)}


def test_census_handles_aliases_comparisons_and_relative_reference() -> None:
    prefix = "import time as clock\nfrom time import monotonic as now\ndef test_a():\n"
    setup = " x = now() - 1\n ref = clock.perf_counter() - 1\n"
    for body, expected in (
        (" assert x / 1000 < 5\n", True),
        (" self.assertLess(x, 5)\n", True),
        (" assert ref < x < 5\n", True),
        (" assert x / ref < 5\n", False),
        (" self.assertLess(x, ref)\n", False),
        (" ratio = x / ref\n assert ratio < 5\n", False),
        (" assert len([]) < 5\n", False),
    ):
        tree = ast.parse(prefix + setup + body)
        assert _has_absolute_clock_assertion(tree.body[-1], _time_aliases(tree)) == expected, body
    tree = ast.parse(prefix + " assert now() < 5\n")
    assert _has_absolute_clock_assertion(tree.body[-1], _time_aliases(tree))


def test_census_distinguishes_classes_and_ignores_uncollected_trees(tmp_path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests\nnorecursedirs = shadows\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    source = "import time\nclass %s:\n def test_same(self):\n  x = time.monotonic()\n  assert x < 5\n"
    (tmp_path / "tests/test_budget.py").write_text(source % "TestA" + source % "TestB", encoding="utf-8")
    (tmp_path / "tests/shadows").mkdir()
    (tmp_path / "tests/shadows/test_copy.py").write_text(source % "TestShadow", encoding="utf-8")
    (tmp_path / "test_outside.py").write_text(source % "TestOutside", encoding="utf-8")
    assert _census(tmp_path) == {"tests/test_budget.py::TestA::test_same", "tests/test_budget.py::TestB::test_same"}


def test_census_refuses_unparseable_test_in_declared_scope(tmp_path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_broken.py").write_text("def broken(\n", encoding="utf-8")
    with pytest.raises(SyntaxError):
        _census(tmp_path)
