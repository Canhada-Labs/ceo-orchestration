"""ADR-136-AMEND-2 §4.2 — fan-in rendezvous PLANNER (no real apply).

When the un-scaffolded coordinator (ADR-136-AMEND-2 §4.5) fans write-path
work out across N child worktrees, the parallel edits MUST rendezvous
(fan-in) back into the live tree through *exactly one* path: a single
**sequential integration lane** that still traverses the unchanged
Owner-GPG sentinel (``check_canonical_edit.py``) and the ``/debate``-VETO
hard-block (``PROTOCOL.md:331-346``) for any canonical/KERNEL diff. No
parallel child may shortcut this lane (§4.2 HARD).

This module is the *planner* for that lane. It is deliberately
**inert**:

  * :func:`collect_worktree_diffs` reads the worktree pool's busy slots
    and renders a read-only descriptor per child diff (it computes a
    ``git diff`` summary against the pool's base HEAD — it never writes,
    resets, or applies anything).
  * :func:`build_integration_plan` orders those descriptors into ONE
    deterministic sequential lane and returns an :class:`IntegrationPlan`
    whose **terminal step is a HARD STOP** at the Owner-GPG + VETO
    boundary. The plan *describes* what WOULD be applied; calling it
    applies nothing. Any diff touching a canonical/KERNEL path is
    flagged ``requires_owner_ceremony=True`` so the lane stops for the
    Owner GPG ceremony rather than auto-applying.

Why a planner and not an applier: the actual fan-in apply is a
canonical/ceremony surface (it mutates the live tree + rides the
Owner-GPG sentinel). Per ADR-136-AMEND-2 §4.2 + the framework's
RECOMMENDER-only posture, this code may only *plan* — the apply is an
Owner ceremony. The planner therefore never raises on the happy path,
never spawns a process, and produces a fail-safe (Owner-gated) plan.

Dependency reuse: per-child audit context comes from
:mod:`._child_isolation` (``child_audit_env``) — this module does NOT
redefine it. Worktree slots come from :mod:`._worktree_pool`.

stdlib-only · Python >= 3.9 · pure/deterministic · no network.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

from ._child_isolation import child_audit_env

# Imported for type/contract clarity; the pool object is duck-typed at
# the call boundary (we only read ``busy_slots`` / ``base_repo``), so a
# test double need not subclass it.
from ._worktree_pool import WorktreePool  # noqa: F401  (documented contract)


# ----------------------------------------------------------------------
# Canonical / KERNEL detection (advisory mirror)
# ----------------------------------------------------------------------
# This planner is a NON-canonical module, so it does NOT import the
# KERNEL hook (``check_canonical_edit.py``) — coupling a non-canonical
# script to KERNEL internals would be backwards. Instead it carries a
# conservative, self-contained mirror of the canonical guard surface.
#
# Posture is FAIL-SAFE-TOWARDS-CEREMONY: when in doubt we FLAG a path as
# requiring the Owner ceremony rather than waving it through. The real,
# authoritative gate remains the unchanged Owner-GPG sentinel at apply
# time (§4.2); this flag only routes a diff into the ceremony lane early
# so the planner never proposes an auto-apply for a guarded path.
#
# The prefix set mirrors ``check_canonical_edit._CANONICAL_PREFIXES``:
# any repo-relative path whose first segment is NOT one of these cannot
# match a canonical guard. KERNEL paths (``.claude/hooks/**``) are a
# subset of ``.claude`` and are covered by the glob suffixes below.
_CANONICAL_PREFIXES = frozenset(
    {".claude", ".github", "scripts", "SPEC", "PROTOCOL.md"}
)

# Suffix/segment globs that mark a canonical or KERNEL surface. Mirrors
# the load-bearing entries of ``check_canonical_edit._CANONICAL_GUARDS``.
# Kept intentionally broad (fail-safe): a false-positive only routes a
# diff into the Owner ceremony, which is always allowed; a false-negative
# would be the dangerous direction, so we err wide.
_CANONICAL_GLOBS = (
    ".claude/hooks/**",            # KERNEL + all governance hooks + _lib
    ".claude/agents/**",           # sub-agent persona/model floors
    ".claude/adr/**",              # architectural record
    ".claude/policies/**",         # policy-as-code
    ".claude/dispatcher/**",       # pair-rail dispatcher surface
    ".claude/governance/**",       # pair-rail governance pins
    ".claude/skills/**/SKILL.md",  # skill definitions (any tier)
    ".claude/team.md",
    ".claude/frontend-team.md",
    ".claude/pitfalls-catalog.yaml",
    ".claude/settings.json",
    ".claude/tier-policy.json",
    ".claude/tier-policy.json.sigchain",
    ".github/workflows/**",        # CI / release gates
    ".github/CODEOWNERS",
    "SPEC/**",                     # published compliance contract
    "scripts/install.sh",
    "scripts/install-npm.sh",
    "scripts/upgrade.sh",
    "PROTOCOL.md",                 # root governance doc
    # PLAN-dir canonical surfaces (mirror check_canonical_edit.py:200-231):
    # spec.md is injected into sub-agent prompts (PLAN-042 FINDING-14 / ADR-058);
    # corpus/locked + canonical/ are Owner-sentinel-guarded. Omitting these was a
    # fail-UNSAFE false-negative (PLAN-122 Phase-A adversarial review P1).
    ".claude/plans/PLAN-*/spec.md",
    ".claude/plans/PLAN-*/corpus/locked/MANIFEST.md",
    ".claude/plans/PLAN-*/corpus/locked/**/*.py",
    ".claude/plans/PLAN-*/corpus/locked/**/*.js",
    ".claude/plans/PLAN-*/canonical/*",
)


def _norm_rel(path_str: str) -> str:
    """Normalise a (possibly OS-native) repo-relative path to '/'-style.

    Leading ``./`` and any ``os.sep`` are normalised so glob matching is
    platform-independent and stable.
    """
    rel = path_str.replace(os.sep, "/").lstrip("/")
    while rel.startswith("./"):
        rel = rel[2:]
    return rel


def _match_glob(rel_str: str, pattern: str) -> bool:
    """Segment-wise glob: ``*`` = one segment, ``**`` = zero-or-more.

    Mirrors ``check_canonical_edit._match_segments`` semantics (per-
    segment fnmatch + ``**`` zero-or-more) without importing the KERNEL.
    """
    return _match_segments(rel_str.split("/"), pattern.split("/"))


def _match_segments(p_parts: Sequence[str], pat_parts: Sequence[str]) -> bool:
    import fnmatch

    if not pat_parts:
        return not p_parts
    head, rest = pat_parts[0], pat_parts[1:]
    if head == "**":
        # zero-or-more segments
        for i in range(len(p_parts) + 1):
            if _match_segments(p_parts[i:], rest):
                return True
        return False
    if not p_parts:
        return False
    if not fnmatch.fnmatch(p_parts[0], head):
        return False
    return _match_segments(p_parts[1:], rest)


def is_canonical_path(path_str: str) -> bool:
    """True if ``path_str`` (repo-relative) is a canonical/KERNEL surface.

    Conservative mirror of the Owner-GPG sentinel's guard list. Used only
    to FLAG a diff for the Owner ceremony lane — the authoritative gate is
    the unchanged ``check_canonical_edit.py`` at apply time. Never raises:
    a malformed path simply returns ``False`` (the real sentinel still
    runs downstream).
    """
    rel = _norm_rel(path_str)
    if not rel:
        return False
    first_seg = rel.split("/", 1)[0]
    if first_seg not in _CANONICAL_PREFIXES:
        return False
    for pattern in _CANONICAL_GLOBS:
        if _match_glob(rel, pattern):
            return True
    return False


# ----------------------------------------------------------------------
# Diff descriptors
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class WorktreeDiff:
    """A read-only descriptor of one child worktree's pending diff.

    ``loop_id``      — the child loop holding the worktree slot.
    ``worktree``     — absolute worktree path (the pool slot).
    ``files``        — sorted list of repo-relative changed paths.
    ``touches_canonical`` — True if ANY changed file is a canonical/
                      KERNEL surface (routes the diff to the Owner lane).
    ``audit_dir``    — the per-child ``CEO_AUDIT_LOG_DIR`` derived via
                      ``_child_isolation.child_audit_env`` (so the lane
                      can reference each child's isolated audit context
                      without re-deriving it).

    Frozen + field-ordered for deterministic ordering/serialisation.
    """

    loop_id: str
    worktree: str
    files: List[str] = field(default_factory=list)
    touches_canonical: bool = False
    audit_dir: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "loop_id": self.loop_id,
            "worktree": self.worktree,
            "files": list(self.files),
            "touches_canonical": self.touches_canonical,
            "audit_dir": self.audit_dir,
        }


# Default base ref for the diff summary. Children are detached at HEAD by
# the pool (``_add_worktree`` adds ``--detach … HEAD``), so a diff vs HEAD
# captures the child's uncommitted + committed work in the worktree.
_DEFAULT_BASE_REF = "HEAD"


def _changed_files_in_worktree(
    worktree: Path,
    base_ref: str,
    *,
    _runner=None,
) -> List[str]:
    """Return sorted repo-relative changed paths in ``worktree`` (read-only).

    Uses ``git diff --name-only`` (working tree + index vs ``base_ref``)
    plus untracked files via ``--others``. This NEVER mutates the
    worktree. On any git error it returns ``[]`` (fail-open: an empty
    diff simply contributes no step to the lane — the real apply gate
    still runs downstream). ``_runner`` is an injection seam for tests so
    no real subprocess is required.
    """
    run = _runner if _runner is not None else _run_git_readonly
    out: "set[str]" = set()
    try:
        tracked = run(
            worktree,
            ["diff", "--name-only", base_ref],
        )
        for line in (tracked or "").splitlines():
            line = line.strip()
            if line:
                out.add(_norm_rel(line))
        # Untracked files the child created but did not stage.
        others = run(
            worktree,
            ["ls-files", "--others", "--exclude-standard"],
        )
        for line in (others or "").splitlines():
            line = line.strip()
            if line:
                out.add(_norm_rel(line))
    except Exception:
        # Fail-open: a planner must never blow up the session on a git
        # hiccup. An empty/partial diff is conservative (the Owner gate
        # still runs at real apply time).
        return sorted(out)
    return sorted(out)


def _run_git_readonly(worktree: Path, args: List[str]) -> str:
    """Run a read-only ``git`` command in ``worktree``; return stdout text.

    Only ever invoked with read-only subcommands (``diff``/``ls-files``).
    Returns ``""`` on non-zero rc instead of raising (fail-open).
    """
    cmd = ["git", "-C", str(worktree), *args]
    r = subprocess.run(  # noqa: S603 — fixed argv, no shell, read-only git
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        return ""
    return r.stdout or ""


def collect_worktree_diffs(
    pool,
    *,
    base_env: Optional[Mapping[str, str]] = None,
    base_ref: str = _DEFAULT_BASE_REF,
    _runner=None,
) -> List[WorktreeDiff]:
    """Collect read-only diff descriptors for every busy slot in ``pool``.

    Reads ``pool.busy_slots()`` (loop_id -> worktree Path) and, for each,
    computes the changed-file set (read-only ``git diff``) + the per-child
    audit dir (via ``_child_isolation.child_audit_env``). Slots are
    enumerated in deterministic ``loop_id`` order so a plan built from the
    result is reproducible.

    This function NEVER applies, resets, or stages anything — it only
    reads. An empty / un-initialised pool yields ``[]``.

    Args:
      pool: a :class:`._worktree_pool.WorktreePool` (or any object
        exposing ``busy_slots() -> Mapping[str, Path]``). Duck-typed so a
        lightweight test double works.
      base_env: parent environment used to derive each child's isolated
        ``CEO_AUDIT_LOG_DIR`` (defaults to ``os.environ``). Read-only —
        never mutated (``child_audit_env`` copies it).
      base_ref: git ref the per-child diff is computed against
        (default ``HEAD`` — children are detached at HEAD by the pool).
      _runner: test seam — a ``(worktree, args) -> stdout`` callable that
        replaces real ``git`` invocation.
    """
    env: Mapping[str, str] = base_env if base_env is not None else os.environ

    # Read busy slots; tolerate a pool that is not initialised / exposes
    # no slots. ``busy_slots`` raises only if the pool contract changes —
    # fail-open to an empty plan rather than crash the planner.
    try:
        busy = pool.busy_slots()
    except Exception:
        return []
    if not busy:
        return []

    diffs: List[WorktreeDiff] = []
    # Deterministic order: sort by loop_id. Two children never share a
    # slot, so loop_id is a total order.
    for slot_index, loop_id in enumerate(sorted(busy.keys())):
        worktree_path = Path(busy[loop_id])
        files = _changed_files_in_worktree(
            worktree_path, base_ref, _runner=_runner
        )
        touches_canonical = any(is_canonical_path(f) for f in files)
        # Per-child isolated audit dir (reuse the prior-wave helper; do
        # NOT redefine it). Slot index = stable per-child slot number.
        child_env = child_audit_env(env, slot_index)
        audit_dir = child_env.get("CEO_AUDIT_LOG_DIR")
        diffs.append(
            WorktreeDiff(
                loop_id=loop_id,
                worktree=str(worktree_path),
                files=files,
                touches_canonical=touches_canonical,
                audit_dir=audit_dir,
            )
        )
    return diffs


# ----------------------------------------------------------------------
# Integration plan
# ----------------------------------------------------------------------
# Step kinds. The plan is a sequence of these; only the planner emits
# them and only an Owner ceremony consumes them. NONE of them apply.
STEP_INTEGRATE = "integrate"          # a child diff staged into the lane
STEP_OWNER_CEREMONY = "owner_ceremony"  # canonical diff → Owner-GPG gate
STEP_HARD_STOP = "hard_stop"          # terminal Owner-GPG + VETO boundary

# Terminal-step reason — the lane stops here; the apply is an Owner
# ceremony through the unchanged sentinel + /debate-VETO (ADR-136-AMEND-2
# §4.2). This planner emits the stop; it does not cross it.
HARD_STOP_REASON = (
    "owner_gpg_sentinel_and_debate_veto_boundary"
)


@dataclass(frozen=True)
class IntegrationStep:
    """One ordered step in the sequential integration lane (describe-only).

    ``kind``        — one of STEP_INTEGRATE / STEP_OWNER_CEREMONY /
                      STEP_HARD_STOP.
    ``order``       — 0-based position in the single sequential lane.
    ``loop_id``     — owning child (None for the terminal hard-stop).
    ``worktree``    — child worktree path (None for the terminal stop).
    ``files``       — repo-relative files this step WOULD touch.
    ``requires_owner_ceremony`` — True for canonical/KERNEL diffs and for
                      the terminal stop; the lane MUST pass through the
                      Owner-GPG sentinel + /debate-VETO for these.
    ``applies``     — ALWAYS False. The planner describes; it never
                      applies. Present as an explicit, asserted invariant.
    ``note``        — human-readable description of the boundary.
    """

    kind: str
    order: int
    loop_id: Optional[str] = None
    worktree: Optional[str] = None
    files: List[str] = field(default_factory=list)
    requires_owner_ceremony: bool = False
    applies: bool = False  # invariant: a planner step NEVER applies
    note: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "kind": self.kind,
            "order": self.order,
            "loop_id": self.loop_id,
            "worktree": self.worktree,
            "files": list(self.files),
            "requires_owner_ceremony": self.requires_owner_ceremony,
            "applies": self.applies,
            "note": self.note,
        }


@dataclass(frozen=True)
class IntegrationPlan:
    """A described (NOT applied) single-sequential-lane fan-in plan.

    ``steps``        — ordered integration steps; the LAST step is always
                       the ``STEP_HARD_STOP`` terminal boundary.
    ``requires_owner_ceremony`` — True if ANY child diff touches a
                       canonical/KERNEL path (the whole lane then funnels
                       through the Owner-GPG ceremony).
    ``applied``      — ALWAYS False. This object is a description; nothing
                       has been or will be applied by constructing it.

    Invariants (asserted at construction):
      * exactly one terminal ``STEP_HARD_STOP`` and it is LAST;
      * ``applied`` is False and every step's ``applies`` is False;
      * step ``order`` values are a contiguous 0..N-1 sequence (one
        sequential lane — no parallelism).
    """

    steps: List[IntegrationStep] = field(default_factory=list)
    requires_owner_ceremony: bool = False
    applied: bool = False  # invariant: a plan is never self-applying

    def __post_init__(self) -> None:
        # Defensive invariants — a malformed plan is a programming error,
        # not a runtime user fault, so these assert rather than fail-open.
        if not self.steps:
            return
        assert self.applied is False, "IntegrationPlan must never be self-applied"
        # Terminal step must be the single hard stop, and it must be LAST.
        last = self.steps[-1]
        assert last.kind == STEP_HARD_STOP, (
            "terminal step must be the Owner-GPG/VETO hard stop"
        )
        assert (
            sum(1 for s in self.steps if s.kind == STEP_HARD_STOP) == 1
        ), "exactly one terminal hard-stop step is allowed"
        # No step may claim it applies.
        assert all(not s.applies for s in self.steps), (
            "no integration step may apply (planner is describe-only)"
        )
        # Contiguous single-lane ordering.
        assert [s.order for s in self.steps] == list(range(len(self.steps))), (
            "steps must form one contiguous sequential lane"
        )

    @property
    def terminal_step(self) -> Optional[IntegrationStep]:
        """The single terminal HARD-STOP boundary (None for empty plan)."""
        if not self.steps:
            return None
        return self.steps[-1]

    def to_dict(self) -> Dict[str, object]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "requires_owner_ceremony": self.requires_owner_ceremony,
            "applied": self.applied,
        }


def build_integration_plan(
    diffs: Sequence[WorktreeDiff],
) -> IntegrationPlan:
    """Order ``diffs`` into ONE sequential lane terminating at a HARD STOP.

    ADR-136-AMEND-2 §4.2: fan-in is the ONLY path back to the live tree;
    all diffs rendezvous and would be applied *sequentially* through the
    unchanged Owner-GPG sentinel + ``/debate``-VETO. This function returns
    the *description* of that lane. It applies NOTHING.

    Ordering (deterministic): non-canonical diffs first (they can stage
    without the Owner ceremony), then canonical/KERNEL diffs (each marked
    ``requires_owner_ceremony``), each group sorted by ``loop_id``. The
    lane always ends with the single ``STEP_HARD_STOP`` terminal boundary
    — the Owner-GPG sentinel + ``/debate``-VETO gate — which this planner
    emits but never crosses.

    An empty ``diffs`` yields an empty plan (no steps, no terminal stop —
    there is nothing to integrate).
    """
    if not diffs:
        return IntegrationPlan(steps=[], requires_owner_ceremony=False)

    # Stable, deterministic order: canonical-touching diffs sort LAST so
    # the lane stages the cheap (non-ceremony) diffs before funnelling the
    # guarded ones into the Owner gate. Within each group, sort by
    # loop_id for reproducibility. (False < True, so non-canonical first.)
    ordered = sorted(
        diffs,
        key=lambda d: (d.touches_canonical, d.loop_id),
    )

    steps: List[IntegrationStep] = []
    any_canonical = False
    for i, d in enumerate(ordered):
        if d.touches_canonical:
            any_canonical = True
            kind = STEP_OWNER_CEREMONY
            note = (
                "canonical/KERNEL diff — MUST pass the Owner-GPG sentinel "
                "(check_canonical_edit.py) + /debate-VETO before apply"
            )
        else:
            kind = STEP_INTEGRATE
            note = "non-canonical diff — staged into the sequential lane"
        steps.append(
            IntegrationStep(
                kind=kind,
                order=i,
                loop_id=d.loop_id,
                worktree=d.worktree,
                files=list(d.files),
                requires_owner_ceremony=d.touches_canonical,
                applies=False,
                note=note,
            )
        )

    # Terminal HARD STOP — the Owner-GPG + VETO boundary. The planner
    # describes the lane up to here and STOPS; the apply is an Owner
    # ceremony, never performed by this code.
    steps.append(
        IntegrationStep(
            kind=STEP_HARD_STOP,
            order=len(steps),
            loop_id=None,
            worktree=None,
            files=[],
            requires_owner_ceremony=True,
            applies=False,
            note=(
                "HARD STOP at the Owner-GPG sentinel + /debate-VETO boundary "
                "(ADR-136-AMEND-2 §4.2): the planner describes what WOULD be "
                "applied; the apply is an Owner ceremony. reason="
                + HARD_STOP_REASON
            ),
        )
    )

    return IntegrationPlan(
        steps=steps,
        requires_owner_ceremony=any_canonical,
        applied=False,
    )
