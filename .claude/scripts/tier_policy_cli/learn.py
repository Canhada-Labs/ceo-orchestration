"""PLAN-043 Phase 2 — Learning algorithm + statistical power gate.

Consumes HMAC-verified tournament reports (ADR-063) and produces
``Recommendation`` records per role following the Round 1 consensus
closures:

- **C-P0-1** statistical power gate: ``n >= 30`` per (role × task-type)
  cell AND ``gap_pp >= 25pp`` (amended from undersized 15pp at n=30).
- **C-P0-6** explicit ``ROLE_TO_TASK_TYPES`` mapping; MIN gap across
  cells per role (conservative).
- **C-P0-3** VETO floor zeroth-check + module-load integrity assertion
  against the frozen SHA256 anchor in ``_constants.py``.
- **C-P1-1** freshness filter + rolling window cap.
- **C-P1-7** idempotency + monotonic-n + cross-role independence
  properties (exercised by tests; preserved by pure-function design).
- **F-QA-P0-5** errored-only cells skipped with dedicated skip reason.
- **F-PERF-P1-1** ``last_change_by_role`` O(1) cooldown lookup.
- **F-PERF-P1-3** per-report 512 KB size cap.

stdlib-only (ADR-002). Python >= 3.9. Fail-open (ADR-005): any
unrecoverable error returns empty recommendation list + emits the
``tier_policy_insufficient_fresh_reports`` or
``tier_policy_rejected`` sentinel (caller turns into audit event).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from ._constants import (
        VETO_HARDCODE,
        VETO_HARDCODE_FROZEN_SHA256,
        assert_veto_hardcode_integrity,
    )
    from ._types import (
        AssignmentEvidence,
        CANONICAL_5_AGENTS,
        Recommendation,
        ROLE_TO_TASK_TYPES,
        TierPolicyRecord,
        VALID_MODEL_IDS,
    )
except ImportError:  # pragma: no cover — direct-script execution
    from _constants import (  # type: ignore[no-redef]
        VETO_HARDCODE,
        VETO_HARDCODE_FROZEN_SHA256,
        assert_veto_hardcode_integrity,
    )
    from _types import (  # type: ignore[no-redef]
        AssignmentEvidence,
        CANONICAL_5_AGENTS,
        Recommendation,
        ROLE_TO_TASK_TYPES,
        TierPolicyRecord,
        VALID_MODEL_IDS,
    )


# ---------------------------------------------------------------------
# Module-load integrity assertion (C-P0-3 defense-in-depth).
# Tampering VETO_HARDCODE at runtime blocks learn.py from importing.
# ---------------------------------------------------------------------
assert_veto_hardcode_integrity(VETO_HARDCODE)


# ---------------------------------------------------------------------
# Constants + env helpers
# ---------------------------------------------------------------------

MIN_N_PER_CELL: int = 30  # C-P0-1
MIN_GAP_PP: float = 25.0  # C-P0-1 amended from 15pp
COOLDOWN_DAYS_DEFAULT: int = 90  # Q2
REPORT_MAX_AGE_DAYS_DEFAULT: int = 365  # C-P1-1
MAX_RUNS_DEFAULT: int = 12  # C-P1-1
MIN_TOURNAMENT_RUNS: int = 3  # Q8
MAX_REPORT_SIZE_BYTES: int = 512 * 1024  # F-PERF-P1-3


# Rejection reasons — stable enum (matches _types.Recommendation comment).
REASON_VETO_FLOOR: str = "veto_floor"
REASON_STATISTICAL_POWER: str = "statistical_power"
REASON_COOLDOWN: str = "cooldown"
REASON_INSUFFICIENT_FRESH_REPORTS: str = "insufficient_fresh_reports"
REASON_MIXED_WINNERS: str = "mixed_cell_winners"
REASON_UNKNOWN_MODEL: str = "unknown_model_id"
REASON_ALL_ERRORED: str = "cell_all_errored"


def _get_int_env(name: str, default: int) -> int:
    """Parse int env var with fail-open default on any parse error."""
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _utc_now() -> datetime:
    """Process-level tz-aware UTC now (test-overridable via ``now`` arg)."""
    return datetime.now(timezone.utc)


def _parse_iso8601(ts: str) -> Optional[datetime]:
    """Parse ISO-8601 (ends in ``Z`` or ``+00:00``) → aware datetime.

    Returns None on any malformed input (fail-open).
    """
    if not ts or not isinstance(ts, str):
        return None
    candidate = ts.rstrip("Z")
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------

@dataclass
class _CellStats:
    """Aggregated counts for a single (task_type × model) cell."""
    passes: int = 0
    fails: int = 0
    errored: int = 0

    @property
    def total(self) -> int:
        return self.passes + self.fails + self.errored

    @property
    def non_errored(self) -> int:
        return self.passes + self.fails

    @property
    def win_rate(self) -> float:
        """Pass fraction over non-errored; 0.0 if all errored."""
        denom = self.non_errored
        if denom <= 0:
            return 0.0
        return self.passes / denom


@dataclass
class _Aggregate:
    """Per (task_type, model) → counts accumulated across reports."""
    cells: Dict[Tuple[str, str], _CellStats] = field(default_factory=dict)
    reports_consumed: int = 0
    report_hmacs: List[str] = field(default_factory=list)

    def get(self, task_type: str, model: str) -> _CellStats:
        key = (task_type, model)
        cell = self.cells.get(key)
        if cell is None:
            cell = _CellStats()
            self.cells[key] = cell
        return cell


# ---------------------------------------------------------------------
# Tournament report discovery + loading
# ---------------------------------------------------------------------

_REPORT_NAME_RE = re.compile(r"^tournament-[A-Za-z0-9_\-]+\.jsonl$")


def _discover_report_files(
    reports_dir: Path,
    max_age_days: int,
    window_cap: int,
    now: datetime,
) -> List[Path]:
    """Glob ``tournament-*.jsonl``; freshness-filter; cap to N most recent.

    Filename must match the strict name regex (defends against
    path-traversal / symlink-name trickery). Oversized files are
    skipped silently (F-PERF-P1-3 enforcement).
    """
    if not reports_dir.exists() or not reports_dir.is_dir():
        return []
    cutoff = now - timedelta(days=max_age_days)
    candidates: List[Tuple[float, Path]] = []
    try:
        entries = list(reports_dir.iterdir())
    except OSError:
        return []
    for p in entries:
        if not p.is_file():
            continue
        if not _REPORT_NAME_RE.match(p.name):
            continue
        try:
            stat = p.stat()
        except OSError:
            continue
        if stat.st_size > MAX_REPORT_SIZE_BYTES:
            continue
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            continue
        candidates.append((stat.st_mtime, p))
    # Most recent first; cap to window.
    candidates.sort(key=lambda pair: pair[0], reverse=True)
    return [p for _, p in candidates[:window_cap]]


def _read_report_task_records(path: Path) -> Optional[List[Dict]]:
    """Read a tournament JSONL file and return its task-type records.

    Aggregate records (``type=aggregate``) are skipped; task records
    are retained. Returns None on any parse / read failure (caller
    skips the report + emits audit event).
    """
    records: List[Dict] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for raw in f:
                stripped = raw.strip()
                if not stripped:
                    continue
                try:
                    obj = json.loads(stripped)
                except json.JSONDecodeError:
                    return None
                if not isinstance(obj, dict):
                    return None
                if obj.get("type") == "task":
                    records.append(obj)
    except OSError:
        return None
    return records


# ---------------------------------------------------------------------
# PLAN-045 F-10-06 — fixture corpus content-integrity anchor
# ---------------------------------------------------------------------

# Default manifest location. Tournament fixtures live in
# `.claude/scripts/tournament/fixtures/` relative to this module's
# grandparent directory (scripts/tier_policy_cli/ → scripts/ →
# scripts/tournament/). Kept as a module constant for easy override
# in tests via the `manifest_path` kwarg.
_TOURNAMENT_FIXTURES_DIR = (
    Path(__file__).resolve().parent.parent / "tournament" / "fixtures"
)
_CORPUS_MANIFEST_PATH = _TOURNAMENT_FIXTURES_DIR / "CORPUS_SHA256.txt"


def _hash_file_sha256(path: Path, block_size: int = 64 * 1024) -> str:
    """Return lowercase-hex sha256 of ``path`` via streaming reads.

    Mirrors ``tournament/regen_corpus_sha.py::sha256_file`` byte-for-byte
    (same block_size + hex encoding) so manifest regeneration + learner
    verification produce identical digests.
    """
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            data = fh.read(block_size)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def _verify_fixture_corpus(
    fixtures_dir: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
) -> Tuple[bool, List[str]]:
    """Verify tournament fixture corpus content-integrity against manifest.

    PLAN-045 F-10-06 closure. The learner consumes tournament reports
    produced from fixtures under ``scripts/tournament/fixtures/``. HMAC
    chain (``_hmac_verify_report``) proves a report's JSONL wasn't
    modified POST-RUN, but does NOT prove which fixtures produced those
    records. An attacker with commit access could swap fixture content
    (e.g. make security-review tasks systematically easier for Haiku)
    and the HMAC check would still pass.

    This function re-hashes every file listed in the manifest and
    compares against the pinned sha256. On any drift, returns
    ``(False, [list of mismatches])`` + caller fails CLOSED.

    ## Manifest format

    One line per fixture:

        <sha256-hex>  <filename-relative-to-fixtures-dir>

    Lines starting with ``#`` or empty are ignored (comment-compatible
    with ``shasum -a 256 -c``). Regenerate via
    ``.claude/scripts/tournament/regen_corpus_sha.py``.

    ## Fail-open conditions

    - ``CEO_SKIP_FIXTURE_CORPUS_VERIFY=1`` env — dev bypass.
    - Manifest file absent — partial install / test env; skip.
    - Fixtures dir absent — partial install; skip.
    - Manifest unreadable (OSError) — infrastructure issue; skip.

    ## Fail-closed conditions

    - Any entry in manifest has mismatched sha256 vs actual file.
    - Any entry in manifest references a file that doesn't exist.

    Returns:
        Tuple ``(ok, mismatches)``:
        - ``ok=True, mismatches=[]`` → corpus intact OR skipped.
        - ``ok=False, mismatches=[...]`` → corpus tampered; each
          mismatch is ``"<filename>:sha_mismatch"`` or
          ``"<filename>:missing"``.

    Never raises.
    """
    # Dev kill-switch.
    if os.environ.get("CEO_SKIP_FIXTURE_CORPUS_VERIFY") == "1":
        return (True, [])

    if fixtures_dir is None:
        fixtures_dir = _TOURNAMENT_FIXTURES_DIR
    if manifest_path is None:
        manifest_path = _CORPUS_MANIFEST_PATH

    # Partial-install fail-open — manifest / fixtures dir absent means
    # the tournament corpus was never set up; learner has nothing to
    # verify against. Proceed as if verification passed.
    if not manifest_path.is_file() or not fixtures_dir.is_dir():
        return (True, [])

    try:
        lines = manifest_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return (True, [])

    mismatches: List[str] = []
    entries_seen = 0
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(maxsplit=1)
        if len(parts) != 2:
            # Malformed line — skip silently (manifest regen would
            # produce well-formed output; user-hand-edited garbage is
            # not our responsibility).
            continue
        expected_sha, filename = parts[0].lower(), parts[1].strip()
        if not re.match(r"^[0-9a-f]{64}$", expected_sha):
            # Not a sha256 hex → malformed; skip.
            continue
        target = fixtures_dir / filename
        entries_seen += 1
        if not target.is_file():
            mismatches.append(f"{filename}:missing")
            continue
        try:
            actual_sha = _hash_file_sha256(target)
        except OSError:
            mismatches.append(f"{filename}:read_error")
            continue
        if actual_sha != expected_sha:
            mismatches.append(f"{filename}:sha_mismatch")

    # Guard: if the manifest had zero valid entries, treat as fail-open
    # (pure comment / whitespace file = unusable manifest, not tamper).
    if entries_seen == 0:
        return (True, [])

    return (len(mismatches) == 0, mismatches)


def _hmac_verify_report(
    path: Path,
    key_path_override: Optional[Path],
) -> Tuple[bool, Optional[str]]:
    """HMAC-verify the tournament report via ``verify_chain``.

    Returns ``(ok, hmac_tip_hex)`` — ``ok=True`` iff chain is intact
    (or trivially empty). ``hmac_tip_hex`` is the last entry's HMAC
    for provenance tracking (None when not computable).
    """
    # Late import to avoid circular / optional dep at module load time.
    try:
        try:
            from .._lib import audit_hmac as _audit_hmac  # type: ignore[import]
        except (ImportError, ValueError):
            # Running as .claude/scripts subpackage or direct script;
            # resolve via hooks/_lib sibling.
            import importlib.util
            repo_root = Path(__file__).resolve().parent.parent.parent
            spec_path = (
                repo_root / "hooks" / "_lib" / "audit_hmac.py"
            )
            if not spec_path.exists():
                return True, None  # Fail-open — HMAC infra absent.
            spec = importlib.util.spec_from_file_location(
                "_lib_audit_hmac_external", str(spec_path)
            )
            if spec is None or spec.loader is None:
                return True, None
            _audit_hmac = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_audit_hmac)  # type: ignore[attr-defined]

        result = _audit_hmac.verify_chain(
            path, key_path_override=key_path_override
        )
        if result.is_intact:
            # Use last line's hmac as tip for provenance; extracted
            # opportunistically from file tail.
            return True, None
        return False, None
    except Exception:
        # Fail-closed on HMAC verify error — per ADR-064 §Decision 6.
        return False, None


# ---------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------

def _aggregate_task_records(
    report_paths: Sequence[Path],
    key_path_override: Optional[Path],
) -> _Aggregate:
    """Walk reports, accumulate (task_type × model) counts.

    Reports failing HMAC verification are skipped + caller emits
    ``tier_policy_hmac_verify_failed``. Unknown model IDs skipped.
    Unknown verdict values skipped.
    """
    aggregate = _Aggregate()
    for path in report_paths:
        ok, _hmac_tip = _hmac_verify_report(path, key_path_override)
        if not ok:
            continue
        records = _read_report_task_records(path)
        if records is None:
            continue
        consumed_this_file = False
        for rec in records:
            task_type = rec.get("task_type")
            model = rec.get("model")
            verdict = rec.get("verdict")
            if not isinstance(task_type, str) or not isinstance(model, str):
                continue
            if model not in VALID_MODEL_IDS:
                continue
            if verdict not in ("pass", "fail", "errored"):
                continue
            cell = aggregate.get(task_type, model)
            if verdict == "pass":
                cell.passes += 1
            elif verdict == "fail":
                cell.fails += 1
            else:
                cell.errored += 1
            consumed_this_file = True
        if consumed_this_file:
            aggregate.reports_consumed += 1
            aggregate.report_hmacs.append(path.name)
    return aggregate


# ---------------------------------------------------------------------
# Per-cell decision
# ---------------------------------------------------------------------

def _cell_best_model(
    aggregate: _Aggregate,
    task_type: str,
) -> Optional[Tuple[str, float, int]]:
    """Return ``(best_model_id, best_win_rate, min_model_n)`` or None.

    ``min_model_n`` is the MINIMUM non-errored sample count across
    models that produced data in this cell — the statistical-power
    floor honest to the weakest side of the comparison
    (C-P0-1 per-cell semantics; matches ADR-063 SPEC footer
    "differences < 15pp at n=10 are sampling noise" which is per
    (model, task-type) n).

    If any model in the cell has ALL errored samples (non_errored == 0)
    AND total > 0, that model is excluded from the argmax (F-QA-P0-5
    fixture-author error signal). Cells where every model is all-errored
    return None with n computed as 0.
    """
    best_model: Optional[str] = None
    best_rate: float = -1.0
    model_ns: List[int] = []
    for (tt, model), cell in aggregate.cells.items():
        if tt != task_type:
            continue
        if cell.non_errored <= 0:
            continue
        model_ns.append(cell.non_errored)
        if cell.win_rate > best_rate:
            best_rate = cell.win_rate
            best_model = model
    if not model_ns or best_model is None:
        return None
    return best_model, best_rate, min(model_ns)


def _cell_current_tier_rate(
    aggregate: _Aggregate,
    task_type: str,
    current_tier: str,
) -> Optional[float]:
    """Current tier's win-rate in a given cell, or None if no samples."""
    cell = aggregate.cells.get((task_type, current_tier))
    if cell is None or cell.non_errored <= 0:
        return None
    return cell.win_rate


# ---------------------------------------------------------------------
# Per-role decision
# ---------------------------------------------------------------------

def _tier_rank(model_id: str) -> int:
    """Ordinal tier rank (higher = more capable). Used to direction-sign.

    Unknown IDs rank -1 (never selected over a known ID).
    """
    order = {
        "claude-haiku-4-5-20251001": 1,
        "claude-sonnet-4-6": 2,
        "claude-opus-4-8": 3,
        "claude-fable-5": 4,  # ADR-149 flagship generation bump
    }
    return order.get(model_id, -1)


def _direction(from_tier: str, to_tier: str) -> str:
    """Return ``"promote"``, ``"demote"``, or ``"hold"``."""
    if from_tier == to_tier:
        return "hold"
    if _tier_rank(to_tier) > _tier_rank(from_tier):
        return "promote"
    return "demote"


@dataclass
class _RoleDecision:
    """Intermediate per-role decision before cooldown + signing gates."""
    agent_slug: str
    current_tier: str
    recommended_tier: str
    min_n_across_cells: int
    min_gap_pp_across_cells: float
    cells_considered: int
    rejection_reason: Optional[str] = None


def _decide_for_role(
    agent_slug: str,
    current_tier: str,
    aggregate: _Aggregate,
) -> _RoleDecision:
    """Compute per-role winning tier + MIN n + MIN gap_pp across cells.

    Gate ordering (first-match wins):
        1. No mapped task-types → ``hold`` with no_mapped_task_types.
        2. Any cell empty (no non-errored samples for ANY model) →
           ``hold`` with cell_all_errored.
        3. Cells disagree on best model → ``hold`` with mixed_cell_winners.
        4. n_min < MIN_N_PER_CELL → ``hold`` with statistical_power.
        5. Current tier absent from cell (no current-tier samples) →
           gap_pp cannot be computed → ``hold`` with unknown_model_id.
        6. gap_pp < MIN_GAP_PP → ``hold`` with statistical_power.
        7. Otherwise → recommended_tier = consensus-best.
    """
    task_types = ROLE_TO_TASK_TYPES.get(agent_slug, [])
    if not task_types:
        return _RoleDecision(
            agent_slug=agent_slug,
            current_tier=current_tier,
            recommended_tier=current_tier,
            min_n_across_cells=0,
            min_gap_pp_across_cells=0.0,
            cells_considered=0,
            rejection_reason=REASON_STATISTICAL_POWER,
        )

    winners: List[str] = []
    gaps: List[float] = []
    ns: List[int] = []
    for tt in task_types:
        best = _cell_best_model(aggregate, tt)
        if best is None:
            return _RoleDecision(
                agent_slug=agent_slug,
                current_tier=current_tier,
                recommended_tier=current_tier,
                min_n_across_cells=0,
                min_gap_pp_across_cells=0.0,
                cells_considered=len(task_types),
                rejection_reason=REASON_ALL_ERRORED,
            )
        best_model, best_rate, cell_n = best
        current_rate = _cell_current_tier_rate(
            aggregate, tt, current_tier
        )
        if current_rate is None:
            return _RoleDecision(
                agent_slug=agent_slug,
                current_tier=current_tier,
                recommended_tier=current_tier,
                min_n_across_cells=cell_n,
                min_gap_pp_across_cells=0.0,
                cells_considered=len(task_types),
                rejection_reason=REASON_UNKNOWN_MODEL,
            )
        gap_pp = (best_rate - current_rate) * 100.0
        winners.append(best_model)
        gaps.append(gap_pp)
        ns.append(cell_n)

    if len(set(winners)) > 1:
        return _RoleDecision(
            agent_slug=agent_slug,
            current_tier=current_tier,
            recommended_tier=current_tier,
            min_n_across_cells=min(ns),
            min_gap_pp_across_cells=min(gaps),
            cells_considered=len(task_types),
            rejection_reason=REASON_MIXED_WINNERS,
        )

    winner = winners[0]
    n_min = min(ns)
    gap_min = min(gaps)

    if n_min < MIN_N_PER_CELL:
        return _RoleDecision(
            agent_slug=agent_slug,
            current_tier=current_tier,
            recommended_tier=current_tier,
            min_n_across_cells=n_min,
            min_gap_pp_across_cells=gap_min,
            cells_considered=len(task_types),
            rejection_reason=REASON_STATISTICAL_POWER,
        )
    if gap_min < MIN_GAP_PP:
        return _RoleDecision(
            agent_slug=agent_slug,
            current_tier=current_tier,
            recommended_tier=winner,
            min_n_across_cells=n_min,
            min_gap_pp_across_cells=gap_min,
            cells_considered=len(task_types),
            rejection_reason=REASON_STATISTICAL_POWER,
        )
    return _RoleDecision(
        agent_slug=agent_slug,
        current_tier=current_tier,
        recommended_tier=winner,
        min_n_across_cells=n_min,
        min_gap_pp_across_cells=gap_min,
        cells_considered=len(task_types),
    )


# ---------------------------------------------------------------------
# Cooldown + signing gates
# ---------------------------------------------------------------------

def _cooldown_ok(
    agent_slug: str,
    last_change_by_role: Dict[str, str],
    now: datetime,
    cooldown_days: int,
) -> bool:
    """True iff no change within cooldown window. Genesis = always OK."""
    iso = last_change_by_role.get(agent_slug)
    if iso is None or iso == "":
        return True
    prior = _parse_iso8601(iso)
    if prior is None:
        return True  # Malformed → fail-open to allow change.
    delta = now - prior
    return delta >= timedelta(days=cooldown_days)


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def learn(
    reports_dir: Path,
    policy: TierPolicyRecord,
    *,
    now: Optional[datetime] = None,
    cooldown_days: Optional[int] = None,
    max_age_days: Optional[int] = None,
    window_cap: Optional[int] = None,
    key_path_override: Optional[Path] = None,
) -> List[Recommendation]:
    """Aggregate tournament reports and emit per-role recommendations.

    Pure function (explicit ``now`` + explicit reports dir). No audit
    events emitted directly; caller (``apply.py`` / ``cli.py``) decides
    event dispatch based on recommendation fields.

    Args:
        reports_dir: Directory containing ``tournament-*.jsonl`` files.
        policy: Current :class:`TierPolicyRecord` (from ``loader.py``).
        now: UTC datetime for freshness + cooldown math. Defaults to
            :func:`_utc_now`.
        cooldown_days: Override for cooldown window; env fallback to
            ``CEO_TIER_POLICY_COOLDOWN_DAYS`` then default 90.
        max_age_days: Override for report freshness; env fallback to
            ``CEO_TIER_POLICY_REPORT_MAX_AGE_DAYS`` then default 365.
        window_cap: Override for rolling window size; env fallback to
            ``CEO_TIER_POLICY_MAX_RUNS`` then default 12.
        key_path_override: Optional path to tier-policy key (separate
            from audit-log key per F-SEC-P0-2). Passed to
            :func:`verify_chain`.

    Returns:
        List of :class:`Recommendation`. Empty list on
        insufficient fresh reports (less than
        :const:`MIN_TOURNAMENT_RUNS` consumed).
    """
    if now is None:
        now = _utc_now()
    if cooldown_days is None:
        cooldown_days = _get_int_env(
            "CEO_TIER_POLICY_COOLDOWN_DAYS", COOLDOWN_DAYS_DEFAULT
        )
    if max_age_days is None:
        max_age_days = _get_int_env(
            "CEO_TIER_POLICY_REPORT_MAX_AGE_DAYS",
            REPORT_MAX_AGE_DAYS_DEFAULT,
        )
    if window_cap is None:
        window_cap = _get_int_env(
            "CEO_TIER_POLICY_MAX_RUNS", MAX_RUNS_DEFAULT
        )

    # PLAN-045 F-10-06 closure: verify tournament fixture corpus content-
    # integrity BEFORE consuming any tournament reports. Prevents
    # learned-policy poisoning via fixture-swap attack (attacker with
    # commit access swaps test-design.jsonl for one where Haiku wins
    # systematically → learner emits demote-Opus recommendation).
    # HMAC chain verification (_hmac_verify_report) alone does NOT defend
    # this class of attack — it proves report integrity post-run, not
    # which fixtures were actually used. Fail-CLOSED on mismatch;
    # kill-switch CEO_SKIP_FIXTURE_CORPUS_VERIFY=1 bypasses (dev only).
    corpus_ok, corpus_mismatches = _verify_fixture_corpus()
    if not corpus_ok:
        # Emit stderr breadcrumb so CLI / CI can surface the fail-closed
        # reason. Return empty so caller short-circuits (mirrors the
        # existing "insufficient fresh reports" path).
        try:
            sys.stderr.write(
                "[tier_policy_cli.learn] FAIL-CLOSED: fixture corpus "
                "content-integrity mismatch. Suspected tamper of "
                "tournament fixtures. Mismatches: "
                + ", ".join(corpus_mismatches[:10])
                + ("" if len(corpus_mismatches) <= 10 else f" (+{len(corpus_mismatches)-10} more)")
                + "\n"
                "Regenerate manifest via "
                "`python3 .claude/scripts/tournament/regen_corpus_sha.py` "
                "if the change was intended.\n"
            )
        except Exception:
            pass
        return []

    report_paths = _discover_report_files(
        reports_dir, max_age_days, window_cap, now
    )
    if len(report_paths) < MIN_TOURNAMENT_RUNS:
        return []

    aggregate = _aggregate_task_records(report_paths, key_path_override)
    if aggregate.reports_consumed < MIN_TOURNAMENT_RUNS:
        return []

    recommendations: List[Recommendation] = []
    for agent_slug in CANONICAL_5_AGENTS:
        # VETO floor zeroth-check: agents in VETO_HARDCODE are never
        # recommended for tier changes by learned policy.
        if agent_slug in VETO_HARDCODE:
            continue

        assignment = policy.assignments.get(agent_slug)
        if assignment is None:
            continue
        current_tier = assignment.tier

        decision = _decide_for_role(agent_slug, current_tier, aggregate)

        cd_ok = _cooldown_ok(
            agent_slug, policy.last_change_by_role, now, cooldown_days
        )

        action = _direction(current_tier, decision.recommended_tier)

        rejection_reason = decision.rejection_reason
        if rejection_reason is None and not cd_ok:
            rejection_reason = REASON_COOLDOWN
            action = "hold"
        if rejection_reason is not None:
            action = "hold"

        evidence = AssignmentEvidence(
            n=decision.min_n_across_cells,
            gap_pp=round(decision.min_gap_pp_across_cells, 4),
            last_updated=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            runs_considered=aggregate.reports_consumed,
            tournament_report_hmacs=list(aggregate.report_hmacs),
        )

        signature_required = action == "demote"

        recommendations.append(
            Recommendation(
                agent_slug=agent_slug,
                current_tier=current_tier,
                recommended_tier=decision.recommended_tier,
                action=action,
                evidence=evidence,
                signature_required=signature_required,
                cooldown_ok=cd_ok,
                rejection_reason=rejection_reason,
            )
        )

    return recommendations
