"""ADR-136-AMEND-2 §4.2 — fan-in rendezvous PLANNER tests.

Verifies the planner:
  * orders child diffs deterministically into ONE sequential lane;
  * terminates at a HARD STOP at the Owner-GPG + /debate-VETO boundary
    and applies NOTHING (``applied`` / ``applies`` always False);
  * flags canonical/KERNEL-touching diffs as requiring the Owner ceremony;
  * yields an empty plan for an empty / un-initialised pool.

Pure / deterministic — no real git, no network. A fake pool + an injected
``_runner`` stand in for the worktree pool's subprocess git calls.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .._integration import (
    HARD_STOP_REASON,
    STEP_HARD_STOP,
    STEP_INTEGRATE,
    STEP_OWNER_CEREMONY,
    IntegrationPlan,
    WorktreeDiff,
    build_integration_plan,
    collect_worktree_diffs,
    is_canonical_path,
)


# ======================================================================
# Fakes / fixtures
# ======================================================================
class FakePool:
    """Minimal duck-typed stand-in for WorktreePool.

    Exposes only ``busy_slots()`` (loop_id -> worktree Path), which is
    all ``collect_worktree_diffs`` reads.
    """

    def __init__(self, slots: Dict[str, str]):
        self._slots = {k: Path(v) for k, v in slots.items()}

    def busy_slots(self) -> Dict[str, Path]:
        return dict(self._slots)


def make_runner(file_map: Dict[str, List[str]]):
    """Return a fake ``_runner(worktree, args) -> stdout``.

    ``file_map`` maps a worktree path string -> the list of changed files
    that ``git diff --name-only`` should report. ``ls-files --others``
    returns nothing (no untracked) so the test surface is deterministic.
    """

    def _runner(worktree: Path, args: List[str]) -> str:
        key = str(worktree)
        if args[:2] == ["diff", "--name-only"]:
            return "\n".join(file_map.get(key, []))
        if args[:1] == ["ls-files"]:
            return ""  # no untracked files in these fixtures
        return ""

    return _runner


# ======================================================================
# is_canonical_path — the advisory mirror
# ======================================================================
def test_canonical_paths_flagged() -> None:
    assert is_canonical_path(".claude/hooks/check_canonical_edit.py")
    assert is_canonical_path(".claude/hooks/_lib/audit_emit.py")
    assert is_canonical_path(".claude/adr/ADR-136-foo.md")
    assert is_canonical_path(".claude/agents/code-reviewer.md")
    assert is_canonical_path(".claude/settings.json")
    assert is_canonical_path(".github/workflows/validate.yml")
    assert is_canonical_path("SPEC/v1/schema.md")
    assert is_canonical_path("PROTOCOL.md")
    assert is_canonical_path("scripts/install.sh")
    assert is_canonical_path(".claude/skills/core/foo/SKILL.md")


def test_canonical_plan_dir_paths_flagged() -> None:
    # PLAN-122 Phase-A review P1: the 5 PLAN-dir canonical surfaces that
    # check_canonical_edit.py guards MUST flag for the Owner ceremony lane.
    assert is_canonical_path(".claude/plans/PLAN-122/spec.md")
    assert is_canonical_path(".claude/plans/PLAN-099/corpus/locked/MANIFEST.md")
    assert is_canonical_path(".claude/plans/PLAN-077/corpus/locked/fixtures/case.py")
    assert is_canonical_path(".claude/plans/PLAN-077/corpus/locked/case.py")
    assert is_canonical_path(".claude/plans/PLAN-077/corpus/locked/ui/app.js")
    assert is_canonical_path(".claude/plans/PLAN-044/canonical/wave-b.sh")
    # adjacent non-canonical plan files still must NOT flag
    assert not is_canonical_path(".claude/plans/PLAN-122/notes.md")
    assert not is_canonical_path(".claude/plans/PLAN-122/WS3-SPEC.md")


def test_non_canonical_paths_not_flagged() -> None:
    assert not is_canonical_path("src/app.py")
    assert not is_canonical_path("README.md")
    assert not is_canonical_path(".claude/scripts/swarm/_integration.py")
    assert not is_canonical_path(".claude/plans/PLAN-122/notes.md")
    assert not is_canonical_path("docs/whatever.md")


def test_is_canonical_path_never_raises_on_garbage() -> None:
    # fail-open: malformed input returns False, never raises
    assert is_canonical_path("") is False
    assert is_canonical_path("./") is False
    assert is_canonical_path("///") is False


# ======================================================================
# collect_worktree_diffs
# ======================================================================
def test_collect_empty_pool_yields_no_diffs() -> None:
    pool = FakePool({})
    diffs = collect_worktree_diffs(pool, base_env={}, _runner=make_runner({}))
    assert diffs == []


def test_collect_reads_changed_files_readonly() -> None:
    pool = FakePool({"loop-0": "/wt/0", "loop-1": "/wt/1"})
    runner = make_runner(
        {
            "/wt/0": ["src/a.py", "src/b.py"],
            "/wt/1": ["docs/c.md"],
        }
    )
    diffs = collect_worktree_diffs(pool, base_env={}, _runner=runner)
    by_loop = {d.loop_id: d for d in diffs}
    assert by_loop["loop-0"].files == ["src/a.py", "src/b.py"]
    assert by_loop["loop-1"].files == ["docs/c.md"]
    # none of these touch canonical paths
    assert by_loop["loop-0"].touches_canonical is False
    assert by_loop["loop-1"].touches_canonical is False


def test_collect_flags_canonical_touching_child() -> None:
    pool = FakePool({"loop-0": "/wt/0", "loop-1": "/wt/1"})
    runner = make_runner(
        {
            "/wt/0": ["src/a.py"],
            "/wt/1": ["src/d.py", ".claude/hooks/check_agent_spawn.py"],
        }
    )
    diffs = collect_worktree_diffs(pool, base_env={}, _runner=runner)
    by_loop = {d.loop_id: d for d in diffs}
    assert by_loop["loop-0"].touches_canonical is False
    assert by_loop["loop-1"].touches_canonical is True


def test_collect_is_deterministic_by_loop_id() -> None:
    # Insertion order scrambled — output must still be loop_id sorted.
    pool = FakePool({"loop-2": "/wt/2", "loop-0": "/wt/0", "loop-1": "/wt/1"})
    runner = make_runner({"/wt/0": [], "/wt/1": [], "/wt/2": []})
    diffs = collect_worktree_diffs(pool, base_env={}, _runner=runner)
    assert [d.loop_id for d in diffs] == ["loop-0", "loop-1", "loop-2"]


def test_collect_derives_per_child_audit_dir() -> None:
    # base_env carries a run audit root; each child gets a distinct dir
    # under it (reusing _child_isolation.child_audit_env).
    pool = FakePool({"loop-0": "/wt/0", "loop-1": "/wt/1"})
    runner = make_runner({"/wt/0": [], "/wt/1": []})
    base_env = {"CEO_AUDIT_LOG_DIR": "/run/audit"}
    diffs = collect_worktree_diffs(pool, base_env=base_env, _runner=runner)
    audit_dirs = [d.audit_dir for d in diffs]
    # distinct per child, nested under the run root
    assert audit_dirs[0] != audit_dirs[1]
    assert audit_dirs[0] == str(Path("/run/audit") / "child-0")
    assert audit_dirs[1] == str(Path("/run/audit") / "child-1")


def test_collect_does_not_mutate_base_env() -> None:
    pool = FakePool({"loop-0": "/wt/0"})
    runner = make_runner({"/wt/0": []})
    base_env = {"CEO_AUDIT_LOG_DIR": "/run/audit", "OTHER": "keep"}
    snapshot = dict(base_env)
    collect_worktree_diffs(pool, base_env=base_env, _runner=runner)
    assert base_env == snapshot


def test_collect_fail_open_on_pool_error() -> None:
    class BrokenPool:
        def busy_slots(self):
            raise RuntimeError("boom")

    diffs = collect_worktree_diffs(BrokenPool(), base_env={})
    assert diffs == []


def test_collect_counts_untracked_files() -> None:
    pool = FakePool({"loop-0": "/wt/0"})

    def runner(worktree: Path, args: List[str]) -> str:
        if args[:2] == ["diff", "--name-only"]:
            return "src/a.py"
        if args[:1] == ["ls-files"]:
            return "src/new_untracked.py"
        return ""

    diffs = collect_worktree_diffs(pool, base_env={}, _runner=runner)
    assert diffs[0].files == ["src/a.py", "src/new_untracked.py"]


# ======================================================================
# build_integration_plan — ordering + terminal stop + no apply
# ======================================================================
def _diff(loop_id: str, files: List[str], canonical: bool = False) -> WorktreeDiff:
    return WorktreeDiff(
        loop_id=loop_id,
        worktree="/wt/" + loop_id,
        files=files,
        touches_canonical=canonical,
        audit_dir="/run/audit/child-0",
    )


def test_empty_pool_yields_empty_plan() -> None:
    plan = build_integration_plan([])
    assert isinstance(plan, IntegrationPlan)
    assert plan.steps == []
    assert plan.terminal_step is None
    assert plan.requires_owner_ceremony is False
    assert plan.applied is False


def test_plan_orders_deterministically() -> None:
    # scrambled insertion order -> deterministic lane (non-canonical
    # first, then by loop_id)
    diffs = [
        _diff("loop-2", ["src/c.py"]),
        _diff("loop-0", ["src/a.py"]),
        _diff("loop-1", ["src/b.py"]),
    ]
    plan = build_integration_plan(diffs)
    integrate_steps = [s for s in plan.steps if s.kind == STEP_INTEGRATE]
    assert [s.loop_id for s in integrate_steps] == ["loop-0", "loop-1", "loop-2"]
    # build again with a different insertion order -> identical lane
    plan2 = build_integration_plan(list(reversed(diffs)))
    assert plan.to_dict() == plan2.to_dict()


def test_canonical_diffs_sorted_after_non_canonical() -> None:
    diffs = [
        _diff("loop-0", [".claude/hooks/x.py"], canonical=True),
        _diff("loop-1", ["src/b.py"], canonical=False),
    ]
    plan = build_integration_plan(diffs)
    kinds = [s.kind for s in plan.steps]
    # non-canonical integrate first, then owner_ceremony, then hard_stop
    assert kinds == [STEP_INTEGRATE, STEP_OWNER_CEREMONY, STEP_HARD_STOP]


def test_terminal_step_is_hard_stop_no_apply() -> None:
    diffs = [_diff("loop-0", ["src/a.py"])]
    plan = build_integration_plan(diffs)
    term = plan.terminal_step
    assert term is not None
    assert term.kind == STEP_HARD_STOP
    # the terminal stop is the LAST step
    assert plan.steps[-1] is term
    # it applies NOTHING and routes to the Owner ceremony
    assert term.applies is False
    assert term.requires_owner_ceremony is True
    assert HARD_STOP_REASON in term.note
    # the plan itself is never self-applied
    assert plan.applied is False


def test_no_step_ever_applies() -> None:
    diffs = [
        _diff("loop-0", ["src/a.py"]),
        _diff("loop-1", [".claude/adr/ADR-136-x.md"], canonical=True),
    ]
    plan = build_integration_plan(diffs)
    assert all(s.applies is False for s in plan.steps)
    assert plan.applied is False


def test_canonical_touching_diff_requires_owner_ceremony() -> None:
    diffs = [
        _diff("loop-0", ["src/a.py"], canonical=False),
        _diff("loop-1", [".claude/settings.json"], canonical=True),
    ]
    plan = build_integration_plan(diffs)
    # plan-level flag set because at least one canonical diff present
    assert plan.requires_owner_ceremony is True
    cer = [s for s in plan.steps if s.kind == STEP_OWNER_CEREMONY]
    assert len(cer) == 1
    assert cer[0].loop_id == "loop-1"
    assert cer[0].requires_owner_ceremony is True
    # the non-canonical integrate step does NOT require the ceremony
    integ = [s for s in plan.steps if s.kind == STEP_INTEGRATE]
    assert integ[0].requires_owner_ceremony is False


def test_plan_with_no_canonical_diffs_clear_flag() -> None:
    diffs = [_diff("loop-0", ["src/a.py"]), _diff("loop-1", ["src/b.py"])]
    plan = build_integration_plan(diffs)
    assert plan.requires_owner_ceremony is False
    # still terminates at the hard stop (the Owner ceremony boundary is
    # always present — the lane never auto-applies even clean diffs)
    assert plan.steps[-1].kind == STEP_HARD_STOP


def test_plan_steps_form_one_contiguous_sequential_lane() -> None:
    diffs = [
        _diff("loop-0", ["src/a.py"]),
        _diff("loop-1", [".claude/hooks/y.py"], canonical=True),
        _diff("loop-2", ["src/c.py"]),
    ]
    plan = build_integration_plan(diffs)
    # one lane: orders are 0..N-1 with no gaps/duplicates (no parallelism)
    assert [s.order for s in plan.steps] == list(range(len(plan.steps)))
    # exactly one terminal hard stop
    assert sum(1 for s in plan.steps if s.kind == STEP_HARD_STOP) == 1


# ======================================================================
# end-to-end: collect -> build (no real git, no apply)
# ======================================================================
def test_collect_then_build_end_to_end() -> None:
    pool = FakePool({"loop-0": "/wt/0", "loop-1": "/wt/1"})
    runner = make_runner(
        {
            "/wt/0": ["src/feature.py"],
            "/wt/1": [".claude/hooks/check_agent_spawn.py"],
        }
    )
    diffs = collect_worktree_diffs(
        pool, base_env={"CEO_AUDIT_LOG_DIR": "/run/audit"}, _runner=runner
    )
    plan = build_integration_plan(diffs)
    # one non-canonical integrate + one owner ceremony + one hard stop
    assert [s.kind for s in plan.steps] == [
        STEP_INTEGRATE,
        STEP_OWNER_CEREMONY,
        STEP_HARD_STOP,
    ]
    assert plan.requires_owner_ceremony is True
    # nothing applied anywhere
    assert plan.applied is False
    assert all(not s.applies for s in plan.steps)
