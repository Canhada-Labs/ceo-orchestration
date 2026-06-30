"""PLAN-043 Phase 3 — Apply recommendations (promote-auto / demote-signed).

Consumes ``Recommendation`` records from :mod:`learn` and drives the
actual policy mutation:

- **promote-auto** — writes ``.claude/agents/<slug>.md`` ``model:`` via
  atomic ``os.replace()``; appends sigchain entry; emits
  ``tier_policy_promote_applied`` audit event.
- **promote + cost-gated** — downgrades to Owner-signature-required
  (C-P0-4 3-way gate).
- **demote** — emits ``tier_policy_demote_requested`` with CLI
  instructions + drafts ADR-052 amendment scaffold; NO frontmatter
  write.
- **adopter override** — skip + emit
  ``tier_policy_adopter_override_respected``.
- **VETO floor defense-in-depth** — independent literal + module-load
  SHA256 assertion (C-P0-3).

All mutation happens under the ``.claude/tier-policy.json.lock``
filelock for the full read-compute-write-sigchain transaction (C-P0-2).

Fail-open (ADR-005) on any unrecoverable error: return ``ApplyResult``
with ``outcome="failed"``; caller falls back to static ADR-052 dispatch.

stdlib-only (ADR-002). Python >= 3.9.
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
from typing import Any, Dict, List, Optional, Tuple

try:
    from ._constants import _compute_canonical_sha256
    from ._types import (
        Assignment,
        CANONICAL_5_AGENTS,
        Recommendation,
        SigchainEntry,
        TierPolicyRecord,
        VALID_MODEL_IDS,
    )
    from ._agent_frontmatter import (
        detect_adopter_override,
        parse_model_field,
    )
except ImportError:  # pragma: no cover — direct-script execution
    from _constants import _compute_canonical_sha256  # type: ignore[no-redef]
    from _types import (  # type: ignore[no-redef]
        Assignment,
        CANONICAL_5_AGENTS,
        Recommendation,
        SigchainEntry,
        TierPolicyRecord,
        VALID_MODEL_IDS,
    )
    from _agent_frontmatter import (  # type: ignore[no-redef]
        detect_adopter_override,
        parse_model_field,
    )


# ---------------------------------------------------------------------
# VETO_HARDCODE_APPLY — INDEPENDENT literal (C-P0-3 defense in depth).
#
# NOT imported from _constants.py. Verified at module load against the
# frozen SHA256 anchor. Tampering learn.py's VETO_HARDCODE leaves this
# literal untouched → apply.py still rejects VETO-role writes.
#
# Regenerate the frozen hex ONLY when VETO_HARDCODE intentionally
# changes via Owner-signed ADR amendment.
# ---------------------------------------------------------------------

VETO_HARDCODE_APPLY: Dict[str, str] = {
    "code-reviewer": "claude-fable-5",
    "security-engineer": "claude-fable-5",
}

FROZEN_SHA256_HEX_LITERAL: str = (
    # Canonical JSON of {"code-reviewer": "claude-fable-5",
    #                    "security-engineer": "claude-fable-5"}
    # computed via _constants._compute_canonical_sha256 (ADR-149 bump;
    # regen command in PLAN-134/staged/kernel/APPLY-NOTES.md).
    "0419e4fcf81e5a1be05d1b67cf3502a2888edc4ea9c3c45bd84ba51bdf348298"
)


def _assert_apply_veto_integrity() -> None:
    """Module-load assertion: VETO_HARDCODE_APPLY matches frozen anchor.

    Raise AssertionError → import fails → caller must catch and emit
    ``tier_policy_rejected`` with reason ``veto_integrity_violation``
    before falling back to static ADR-052 dispatch.
    """
    actual = _compute_canonical_sha256(VETO_HARDCODE_APPLY)
    if actual != FROZEN_SHA256_HEX_LITERAL:
        raise AssertionError(
            "VETO_HARDCODE_APPLY byte-identity violation: "
            "expected sha256={exp} got sha256={got}".format(
                exp=FROZEN_SHA256_HEX_LITERAL, got=actual
            )
        )


_assert_apply_veto_integrity()


# ---------------------------------------------------------------------
# Constants + pricing (ADR-052 table)
# ---------------------------------------------------------------------

# Approximate $/1M-tokens blended (tokens_in + tokens_out average).
# Matches ADR-052 §Pricing; conservative upper bound for cost gate.
_PRICING_USD_PER_MTOKEN: Dict[str, float] = {
    "claude-haiku-4-5-20251001": 1.0,
    "claude-sonnet-4-6": 3.5,
    "claude-opus-4-8": 15.0,
}

DEFAULT_COST_GATE_USD: float = 20.0  # CEO_TIER_POLICY_MAX_PROMOTE_DELTA_USD
DEFAULT_COST_WINDOW_DAYS: int = 30

SENTINEL_DEFAULT_PATH = (
    "~/.ceo-orchestration/tier-policy/.enabled"
)

ENV_ENABLE = "CEO_TIER_POLICY_ENABLE"
ENV_DRY_RUN = "CEO_TIER_POLICY_DRY_RUN"
ENV_CI = "CEO_TIER_POLICY_CI"
ENV_MAX_PROMOTE_DELTA = "CEO_TIER_POLICY_MAX_PROMOTE_DELTA_USD"
ENV_SENTINEL_PATH = "CEO_TIER_POLICY_SENTINEL_PATH"
ENV_AUDIT_LOG_PATH = "CEO_AUDIT_LOG_PATH"


# Audit event actions (staged — NOT yet in _KNOWN_ACTIONS; Owner kernel
# batch applies post-ship; emit_generic fail-open drops until then).
ACTION_DERIVED = "tier_policy_derived"
ACTION_PROMOTE_APPLIED = "tier_policy_promote_applied"
ACTION_DEMOTE_REQUESTED = "tier_policy_demote_requested"
ACTION_REJECTED = "tier_policy_rejected"
ACTION_HMAC_VERIFY_FAILED = "tier_policy_hmac_verify_failed"
ACTION_ADOPTER_OVERRIDE_RESPECTED = (
    "tier_policy_adopter_override_respected"
)
ACTION_KILLSWITCH_TRIGGERED = "tier_policy_killswitch_triggered"
ACTION_DRY_RUN_COMPLETE = "tier_policy_dry_run_complete"
ACTION_PROMOTE_COST_GATED = "tier_policy_promote_cost_gated"


# ---------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------

@dataclass
class ApplyOutcome:
    """Per-recommendation apply outcome."""
    agent_slug: str
    outcome: str  # applied|cost_gated|demote_requested|adopter_override|
                  # skipped|veto_rejected|error
    from_tier: str
    to_tier: str
    detail: Optional[str] = None


@dataclass
class ApplyResult:
    """Overall apply() result."""
    outcome: str  # success|killswitch|lock_timeout|veto_integrity|error
    outcomes: List[ApplyOutcome] = field(default_factory=list)
    sigchain_entries_appended: int = 0
    policy_written: bool = False
    reason: Optional[str] = None


# ---------------------------------------------------------------------
# Kill-switch check
# ---------------------------------------------------------------------

def _kill_switch_active(sentinel_path: Optional[Path]) -> Tuple[bool, str]:
    """Return ``(allowed, reason)`` tuple.

    Gate is two-factor: env flag ``CEO_TIER_POLICY_ENABLE=1`` AND
    sentinel file present. In CI, ``CEO_TIER_POLICY_CI=1`` substitutes
    for the sentinel (fork-safety enforced at workflow level).

    ``CEO_SOTA_DISABLE=1`` overrides both.
    """
    if os.environ.get("CEO_SOTA_DISABLE", "") == "1":
        return False, "sota_disable_set"
    if os.environ.get(ENV_ENABLE, "0") != "1":
        return False, "enable_flag_off"
    # CI path.
    if os.environ.get(ENV_CI, "0") == "1":
        return True, "ci_mode"
    # Sentinel path.
    if sentinel_path is None:
        sentinel_path = Path(
            os.environ.get(ENV_SENTINEL_PATH)
            or os.path.expanduser(SENTINEL_DEFAULT_PATH)
        )
    if not sentinel_path.exists():
        return False, "sentinel_absent"
    try:
        if sentinel_path.is_symlink():
            return False, "sentinel_is_symlink"
        st = sentinel_path.stat()
    except OSError:
        return False, "sentinel_stat_error"
    if st.st_uid != os.getuid():
        return False, "sentinel_wrong_owner"
    if st.st_mode & 0o077 != 0:
        return False, "sentinel_wrong_perms"
    return True, "ok"


# ---------------------------------------------------------------------
# Cost gate (C-P0-4)
# ---------------------------------------------------------------------

def _get_float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _project_monthly_cost_delta(
    agent_slug: str,
    from_tier: str,
    to_tier: str,
    audit_log_path: Optional[Path] = None,
    *,
    now: Optional[datetime] = None,
    window_days: int = DEFAULT_COST_WINDOW_DAYS,
) -> Optional[float]:
    """Project USD/month cost delta of promoting this agent.

    Reads audit-log.jsonl for ``agent_spawn`` / ``live_adapter_call_*``
    events within ``window_days`` that mention the agent slug; sums
    token usage; multiplies by per-model pricing delta; projects to
    1 month (rescaled).

    Returns None if delta cannot be computed (no data, file unreadable,
    unknown tier IDs) — caller treats as fail-closed → signature
    required.
    """
    if from_tier not in _PRICING_USD_PER_MTOKEN:
        return None
    if to_tier not in _PRICING_USD_PER_MTOKEN:
        return None
    per_mtoken_delta = (
        _PRICING_USD_PER_MTOKEN[to_tier]
        - _PRICING_USD_PER_MTOKEN[from_tier]
    )
    if per_mtoken_delta <= 0:
        return 0.0
    if now is None:
        now = datetime.now(timezone.utc)
    if audit_log_path is None:
        override = os.environ.get(ENV_AUDIT_LOG_PATH)
        if override:
            audit_log_path = Path(override)
        else:
            home = os.environ.get("HOME") or str(Path.home())
            audit_log_path = (
                Path(home)
                / ".claude" / "projects" / "ceo-orchestration"
                / "audit-log.jsonl"
            )
    if not audit_log_path.exists():
        return None

    cutoff = now - timedelta(days=window_days)
    total_tokens = 0
    matched = False
    try:
        with audit_log_path.open("r", encoding="utf-8") as f:
            for raw in f:
                stripped = raw.strip()
                if not stripped:
                    continue
                try:
                    entry = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if not isinstance(entry, dict):
                    continue
                ts = entry.get("ts")
                if not isinstance(ts, str):
                    continue
                try:
                    entry_dt = datetime.strptime(
                        ts, "%Y-%m-%dT%H:%M:%SZ"
                    ).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                if entry_dt < cutoff:
                    continue
                # Look for agent_slug in a few places (best-effort).
                agent = entry.get("agent") or entry.get("agent_slug")
                if agent != agent_slug:
                    continue
                tokens_total = entry.get("tokens_total")
                if isinstance(tokens_total, (int, float)):
                    total_tokens += int(tokens_total)
                    matched = True
                    continue
                t_in = entry.get("tokens_in")
                t_out = entry.get("tokens_out")
                if isinstance(t_in, (int, float)) and isinstance(
                    t_out, (int, float)
                ):
                    total_tokens += int(t_in) + int(t_out)
                    matched = True
    except OSError:
        return None
    if not matched:
        return None
    # Tokens in window_days → scale to 30 days if different.
    if window_days != 30 and window_days > 0:
        total_tokens = int(total_tokens * 30.0 / window_days)
    delta_usd = total_tokens * per_mtoken_delta / 1_000_000.0
    return round(delta_usd, 4)


# ---------------------------------------------------------------------
# Audit emit (staged actions; fail-open until kernel batch applies)
# ---------------------------------------------------------------------

def _emit(action: str, **kwargs) -> None:
    """Best-effort audit event emission via ``_lib.audit_emit.emit_generic``.

    Unknown-action entries fail-open drop (breadcrumb); this is the
    design per PLAN-041 precedent until Owner applies the kernel batch
    registering these 9 new actions in ``_KNOWN_ACTIONS``.
    """
    try:
        try:
            from _lib import audit_emit as _ae  # type: ignore[import]
        except (ImportError, ValueError):
            import importlib.util
            repo_root = Path(__file__).resolve().parent.parent.parent
            spec_path = (
                repo_root / "hooks" / "_lib" / "audit_emit.py"
            )
            if not spec_path.exists():
                return
            spec = importlib.util.spec_from_file_location(
                "_audit_emit_external", str(spec_path)
            )
            if spec is None or spec.loader is None:
                return
            _ae = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_ae)  # type: ignore[attr-defined]
        _ae.emit_generic(action, **kwargs)
    except Exception:  # pragma: no cover — fail-open
        return


# ---------------------------------------------------------------------
# Frontmatter write
# ---------------------------------------------------------------------

_MODEL_LINE_RE = re.compile(
    r"^(?P<lead>\s*)(?P<key>model:)(?P<rest>.*)$"
)


def _write_agent_frontmatter(
    agent_path: Path,
    new_model: str,
    *,
    sentinel_path: Optional[Path] = None,
) -> bool:
    """Atomically rewrite ``model:`` line in agent frontmatter.

    **Belt-and-suspenders kill-switch** (C-P1-4): re-checks the
    two-factor kill before the write. Library-import bypass of
    ``apply()``-level check is caught here.

    Returns True on successful write; False on any error. Fail-open
    error → caller treats as skipped.
    """
    if new_model not in VALID_MODEL_IDS:
        return False
    # Belt-and-suspenders kill-switch re-check.
    allowed, _reason = _kill_switch_active(sentinel_path)
    if not allowed:
        return False
    try:
        original = agent_path.read_text(encoding="utf-8")
    except OSError:
        return False
    lines = original.splitlines(keepends=True)
    in_front = False
    seen_fence = False
    model_line_idx: Optional[int] = None
    for idx, line in enumerate(lines):
        stripped = line.rstrip("\r\n").strip()
        if stripped == "---":
            if not seen_fence:
                seen_fence = True
                in_front = True
                continue
            else:
                break
        if in_front and _MODEL_LINE_RE.match(line):
            model_line_idx = idx
            break
    if model_line_idx is None:
        return False
    match = _MODEL_LINE_RE.match(lines[model_line_idx])
    if match is None:
        return False
    new_line = "{lead}{key} {model}\n".format(
        lead=match.group("lead"),
        key=match.group("key"),
        model=new_model,
    )
    lines[model_line_idx] = new_line
    tmp_path = agent_path.with_name(
        agent_path.name + ".tmp.{pid}".format(pid=os.getpid())
    )
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            f.writelines(lines)
        os.replace(str(tmp_path), str(agent_path))
    except OSError:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        return False
    return True


# ---------------------------------------------------------------------
# Sigchain append
# ---------------------------------------------------------------------

def _append_sigchain_entry(
    sigchain_path: Path,
    *,
    agent_slug: str,
    from_tier: str,
    to_tier: str,
    action: str,
    author: str,
    sp_chain_id: str,
    evidence_hmac: str,
    prior_hash: str,
    chain_length: int,
    prior_commit_sha: str,
    hmac_hex: Optional[str] = None,
) -> bool:
    """Append a sigchain entry atomically. HMAC fill is caller-side.

    Opens in append mode; one line per entry (JSONL). Does NOT compute
    the HMAC itself — caller (cli.py owner-sign) signs via
    ``_lib/audit_hmac.compute_entry_hmac`` with the tier-policy key.
    For apply-path (promote-auto), the framework-signed key is used;
    this helper is called only from within the filelock-protected
    transaction.
    """
    entry: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "author": author,
        "sp_chain_id": sp_chain_id,
        "action": action,
        "agent_slug": agent_slug,
        "from_tier": from_tier,
        "to_tier": to_tier,
        "evidence_hmac": evidence_hmac,
        "prior_hash": prior_hash,
        "chain_length": chain_length,
        "prior_commit_sha": prior_commit_sha,
    }
    if hmac_hex is not None:
        entry["hmac"] = hmac_hex
    try:
        sigchain_path.parent.mkdir(parents=True, exist_ok=True)
        with sigchain_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError:
        return False
    return True


# ---------------------------------------------------------------------
# Policy artifact rewrite
# ---------------------------------------------------------------------

def _serialize_policy(policy: TierPolicyRecord) -> Dict[str, Any]:
    """Convert TierPolicyRecord → JSON-friendly dict."""
    assignments: Dict[str, Dict[str, Any]] = {}
    for slug, a in policy.assignments.items():
        entry: Dict[str, Any] = {
            "tier": a.tier,
            "locked_by": a.locked_by,
        }
        if a.evidence is None:
            entry["evidence"] = None
        else:
            entry["evidence"] = {
                "n": a.evidence.n,
                "gap_pp": a.evidence.gap_pp,
                "last_updated": a.evidence.last_updated,
                "runs_considered": a.evidence.runs_considered,
                "tournament_report_hmacs": list(
                    a.evidence.tournament_report_hmacs
                ),
            }
        assignments[slug] = entry
    return {
        "schema_version": policy.schema_version,
        "generated_at": policy.generated_at,
        "baseline_from": policy.baseline_from,
        "assignments": assignments,
        "hmac_anchor": policy.hmac_anchor,
        "sigchain_tip_length": policy.sigchain_tip_length,
        "last_change_by_role": dict(policy.last_change_by_role),
    }


def _write_policy_artifact(
    policy_path: Path,
    policy: TierPolicyRecord,
) -> bool:
    """Atomically rewrite tier-policy.json with updated record."""
    serialized = _serialize_policy(policy)
    tmp = policy_path.with_name(
        policy_path.name + ".tmp.{pid}".format(pid=os.getpid())
    )
    try:
        policy_path.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(str(tmp), str(policy_path))
    except OSError:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return False
    return True


# ---------------------------------------------------------------------
# ADR amendment scaffold emitter
# ---------------------------------------------------------------------

_ALLOWED_ROLE_RE = re.compile(r"^[a-z][a-z0-9\-]{0,63}$")


def _emit_adr_amendment_scaffold(
    agent_slug: str,
    from_tier: str,
    to_tier: str,
    evidence: Dict[str, Any],
    scaffold_dir: Path,
) -> Optional[Path]:
    """Emit draft ADR-NNN stub for demote into ``adr-drafts/``.

    Enforces:
    - role allowlist via regex (F-SEC-P1-1)
    - NNN monotonic via directory walk
    - ``html.escape`` on evidence values (defense against injection in
      downstream renderers)

    Returns path written or None on failure.
    """
    if not _ALLOWED_ROLE_RE.match(agent_slug):
        return None
    if agent_slug not in CANONICAL_5_AGENTS:
        return None
    try:
        scaffold_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    # Find next NNN.
    existing_nnns = set()
    for p in scaffold_dir.iterdir():
        m = re.match(r"ADR-(\d{3})-tier-demotion-", p.name)
        if m:
            existing_nnns.add(int(m.group(1)))
    # Start at 100 to avoid collision with canonical ADRs 000-099.
    nnn = 100
    while nnn in existing_nnns:
        nnn += 1
    slug_clean = agent_slug
    out_path = scaffold_dir / "ADR-{:03d}-tier-demotion-{}.md".format(
        nnn, slug_clean
    )
    import html
    body_lines = [
        "---",
        "id: ADR-{:03d}".format(nnn),
        "title: Tier demotion for {}".format(html.escape(agent_slug)),
        "status: DRAFT",
        "date: " + datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "related_adrs: [ADR-052, ADR-064]",
        "related_plans: [PLAN-043]",
        "---",
        "",
        "# ADR-{:03d} — Tier demotion for {}".format(nnn, agent_slug),
        "",
        "## Proposal",
        "",
        "Demote `{}` from `{}` to `{}`.".format(
            html.escape(agent_slug),
            html.escape(from_tier),
            html.escape(to_tier),
        ),
        "",
        "## Evidence",
        "",
        "- n (min per cell): {}".format(int(evidence.get("n", 0))),
        "- gap_pp (min across cells): {:.2f}".format(
            float(evidence.get("gap_pp", 0.0))
        ),
        "- runs considered: {}".format(
            int(evidence.get("runs_considered", 0))
        ),
        "",
        "## Owner review required",
        "",
        "This is a DRAFT scaffold emitted by tier_policy_cli.apply when a ",
        "demote recommendation fires. Owner must:",
        "",
        "1. Review tournament evidence via",
        "   `ceo-tier-policy show --derivation <id>`.",
        "2. Promote this draft to canonical `.claude/adr/` after ",
        "   signing `ceo-tier-policy owner-sign`.",
        "3. Flip status DRAFT → PROPOSED → ACCEPTED.",
        "",
    ]
    try:
        out_path.write_text("\n".join(body_lines), encoding="utf-8")
    except OSError:
        return None
    return out_path


# ---------------------------------------------------------------------
# Main apply() entrypoint
# ---------------------------------------------------------------------

def _load_filelock_classes() -> Tuple[Any, Any]:
    """Late-import FileLock / FileLockTimeout via package or spec path.

    Returns ``(FileLock, FileLockTimeout)`` tuple. Raises ImportError
    if neither import route works.
    """
    try:
        from _lib.filelock import FileLock, FileLockTimeout  # type: ignore
        return FileLock, FileLockTimeout
    except ImportError:
        pass

    import importlib.util
    repo_root = Path(__file__).resolve().parent.parent.parent
    spec_path = repo_root / "hooks" / "_lib" / "filelock.py"
    spec = importlib.util.spec_from_file_location(
        "_filelock_ext", str(spec_path)
    )
    if spec is None or spec.loader is None:
        raise ImportError("filelock not available")
    flmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(flmod)  # type: ignore[attr-defined]
    return flmod.FileLock, flmod.FileLockTimeout  # type: ignore[attr-defined]


def _emit_killswitch(
    sentinel_path: Optional[Path], abort_phase: str
) -> None:
    """Emit ACTION_KILLSWITCH_TRIGGERED with standard envelope."""
    _emit(
        ACTION_KILLSWITCH_TRIGGERED,
        env_flag=os.environ.get(ENV_ENABLE, "0"),
        sentinel_present=(
            sentinel_path.exists() if sentinel_path else False
        ),
        abort_phase=abort_phase,
    )


def _run_locked_batch(
    recommendations: List[Recommendation],
    policy: TierPolicyRecord,
    result: ApplyResult,
    *,
    agents_dir: Path,
    baseline_agents_dir: Path,
    policy_path: Path,
    sigchain_path: Path,
    sentinel_path: Optional[Path],
    cost_gate_usd: float,
    adr_scaffold_dir: Path,
    audit_log_path: Optional[Path],
    effective_dry_run: bool,
    now: datetime,
) -> Optional[ApplyResult]:
    """Execute the inside-lock body of apply().

    Returns an override ApplyResult if the kill-switch trips inside
    the lock (C-P0-2); otherwise mutates ``result`` in place and
    returns None.
    """
    allowed2, reason2 = _kill_switch_active(sentinel_path)
    if not allowed2 and not effective_dry_run:
        _emit_killswitch(sentinel_path, "inside_lock")
        return ApplyResult(outcome="killswitch", reason=reason2)

    policy_mutated = False
    for rec in recommendations:
        outcome = _process_single_rec(
            rec, policy, agents_dir,
            baseline_agents_dir,
            sigchain_path, adr_scaffold_dir,
            cost_gate_usd=cost_gate_usd,
            audit_log_path=audit_log_path,
            sentinel_path=sentinel_path,
            dry_run=effective_dry_run,
            now=now,
        )
        result.outcomes.append(outcome)
        if outcome.outcome == "applied":
            result.sigchain_entries_appended += 1
            policy.last_change_by_role[outcome.agent_slug] = (
                now.strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            new_assignment = policy.assignments.get(outcome.agent_slug)
            if new_assignment is not None:
                new_assignment.tier = outcome.to_tier
            policy_mutated = True

    if policy_mutated and not effective_dry_run:
        policy.sigchain_tip_length += result.sigchain_entries_appended
        ok = _write_policy_artifact(policy_path, policy)
        result.policy_written = ok
        if not ok:
            result.outcome = "error"
            result.reason = "policy_artifact_write_failed"

    if effective_dry_run:
        _emit(ACTION_DRY_RUN_COMPLETE)

    return None


def apply(
    recommendations: List[Recommendation],
    policy: TierPolicyRecord,
    *,
    agents_dir: Path,
    baseline_agents_dir: Path,
    policy_path: Path,
    sigchain_path: Path,
    lock_path: Optional[Path] = None,
    sentinel_path: Optional[Path] = None,
    cost_gate_usd: Optional[float] = None,
    adr_scaffold_dir: Optional[Path] = None,
    audit_log_path: Optional[Path] = None,
    dry_run: bool = False,
    now: Optional[datetime] = None,
) -> ApplyResult:
    """Apply recommendations under filelock; emit audit events.

    Args:
        recommendations: From :func:`learn.learn`.
        policy: Current :class:`TierPolicyRecord` (loaded via
            :func:`loader.load_policy`).
        agents_dir: Path to ``.claude/agents/`` (where frontmatter
            lives).
        baseline_agents_dir: Framework baseline (for adopter-override
            diff-detect).
        policy_path: ``.claude/tier-policy.json``.
        sigchain_path: ``.claude/tier-policy.json.sigchain``.
        lock_path: Override for ``.claude/tier-policy.json.lock``.
        sentinel_path: Override for kill-switch sentinel.
        cost_gate_usd: Override for promote cost-envelope threshold.
        adr_scaffold_dir: Override for ADR draft emitter (defaults to
            ``.claude/plans/PLAN-043/adr-drafts/``).
        audit_log_path: Override for audit log (token aggregation).
        dry_run: If True, compute outcomes but do NOT write frontmatter
            or sigchain; emit ``tier_policy_dry_run_complete``.
        now: UTC datetime for cost-window + cooldown-timestamp math.

    Returns:
        :class:`ApplyResult` with per-recommendation outcomes.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    allowed, reason = _kill_switch_active(sentinel_path)
    dry_run_env = os.environ.get(ENV_DRY_RUN, "0") == "1"
    effective_dry_run = dry_run or dry_run_env

    if not allowed and not effective_dry_run:
        _emit_killswitch(sentinel_path, "apply_entry")
        return ApplyResult(outcome="killswitch", reason=reason)

    if cost_gate_usd is None:
        cost_gate_usd = _get_float_env(
            ENV_MAX_PROMOTE_DELTA, DEFAULT_COST_GATE_USD
        )
    if lock_path is None:
        lock_path = policy_path.with_name(policy_path.name + ".lock")
    if adr_scaffold_dir is None:
        adr_scaffold_dir = (
            Path(".claude") / "plans" / "PLAN-043" / "adr-drafts"
        )

    try:
        FileLock, FileLockTimeout = _load_filelock_classes()
    except Exception:
        return ApplyResult(
            outcome="error", reason="filelock_unavailable"
        )

    result = ApplyResult(outcome="success")
    try:
        with FileLock(str(lock_path), timeout=5.0):
            override = _run_locked_batch(
                recommendations, policy, result,
                agents_dir=agents_dir,
                baseline_agents_dir=baseline_agents_dir,
                policy_path=policy_path,
                sigchain_path=sigchain_path,
                sentinel_path=sentinel_path,
                cost_gate_usd=cost_gate_usd,
                adr_scaffold_dir=adr_scaffold_dir,
                audit_log_path=audit_log_path,
                effective_dry_run=effective_dry_run,
                now=now,
            )
            if override is not None:
                return override
    except FileLockTimeout:
        return ApplyResult(
            outcome="lock_timeout", reason="filelock_contested"
        )
    except Exception as e:  # pragma: no cover — fail-open
        return ApplyResult(
            outcome="error",
            reason="unexpected: {}".format(type(e).__name__),
        )

    return result


def _reject_veto_floor(rec: Recommendation) -> ApplyOutcome:
    """Emit ACTION_REJECTED for VETO_HARDCODE_APPLY defense-in-depth hit."""
    _emit(
        ACTION_REJECTED,
        agent_slug=rec.agent_slug,
        rejection_reason="veto_floor",
    )
    return ApplyOutcome(
        agent_slug=rec.agent_slug,
        outcome="veto_rejected",
        from_tier=rec.current_tier,
        to_tier=rec.recommended_tier,
        detail="defense_in_depth",
    )


def _reject_hold(rec: Recommendation) -> ApplyOutcome:
    """Emit ACTION_REJECTED for hold action (no mutation)."""
    _emit(
        ACTION_REJECTED,
        agent_slug=rec.agent_slug,
        rejection_reason=rec.rejection_reason or "hold",
    )
    return ApplyOutcome(
        agent_slug=rec.agent_slug,
        outcome="skipped",
        from_tier=rec.current_tier,
        to_tier=rec.current_tier,
        detail=rec.rejection_reason,
    )


def _check_adopter_override(
    rec: Recommendation,
    agents_dir: Path,
    baseline_agents_dir: Path,
) -> Optional[ApplyOutcome]:
    """Return override ApplyOutcome if adopter diverged from baseline, else None."""
    adopter_path = agents_dir / "{}.md".format(rec.agent_slug)
    baseline_path = baseline_agents_dir / "{}.md".format(rec.agent_slug)
    if not (adopter_path.exists() and baseline_path.exists()):
        return None
    if not detect_adopter_override(adopter_path, baseline_path):
        return None
    _emit(
        ACTION_ADOPTER_OVERRIDE_RESPECTED,
        agent_slug=rec.agent_slug,
        adopter_model=parse_model_field(adopter_path),
        policy_recommended_model=rec.recommended_tier,
    )
    return ApplyOutcome(
        agent_slug=rec.agent_slug,
        outcome="adopter_override",
        from_tier=rec.current_tier,
        to_tier=rec.recommended_tier,
    )


def _apply_promote(
    rec: Recommendation,
    policy: TierPolicyRecord,
    agents_dir: Path,
    sigchain_path: Path,
    *,
    cost_gate_usd: float,
    audit_log_path: Optional[Path],
    sentinel_path: Optional[Path],
    dry_run: bool,
    now: datetime,
) -> ApplyOutcome:
    """Apply a promote rec under the 3-way cost gate (C-P0-4)."""
    delta = _project_monthly_cost_delta(
        rec.agent_slug,
        rec.current_tier,
        rec.recommended_tier,
        audit_log_path=audit_log_path,
        now=now,
    )
    if delta is None or delta > cost_gate_usd:
        # Convert floats to int cents: canonical_json forbids floats in
        # HMAC-covered fields; old projected_delta_usd + threshold_usd (float)
        # caused CanonicalJsonError + dropped events on every gated promote.
        projected_cents = (
            int(round(delta * 100)) if delta is not None else None
        )
        threshold_cents = int(round(cost_gate_usd * 100))
        _emit(
            ACTION_PROMOTE_COST_GATED,
            agent_slug=rec.agent_slug,
            from_tier=rec.current_tier,
            to_tier=rec.recommended_tier,
            projected_delta_usd_cents=projected_cents,
            threshold_usd_cents=threshold_cents,
        )
        _emit(
            ACTION_DEMOTE_REQUESTED,
            agent_slug=rec.agent_slug,
            from_tier=rec.current_tier,
            to_tier=rec.recommended_tier,
            owner_sign_cli=_owner_sign_cli(rec),
        )
        return ApplyOutcome(
            agent_slug=rec.agent_slug,
            outcome="cost_gated",
            from_tier=rec.current_tier,
            to_tier=rec.recommended_tier,
            detail="delta={}".format(delta),
        )

    if dry_run:
        return ApplyOutcome(
            agent_slug=rec.agent_slug,
            outcome="skipped",
            from_tier=rec.current_tier,
            to_tier=rec.recommended_tier,
            detail="dry_run",
        )

    adopter_path = agents_dir / "{}.md".format(rec.agent_slug)
    written = _write_agent_frontmatter(
        adopter_path, rec.recommended_tier,
        sentinel_path=sentinel_path,
    )
    if not written:
        return ApplyOutcome(
            agent_slug=rec.agent_slug,
            outcome="error",
            from_tier=rec.current_tier,
            to_tier=rec.recommended_tier,
            detail="frontmatter_write_failed",
        )
    prior_tip = policy.sigchain_tip_length
    _append_sigchain_entry(
        sigchain_path,
        agent_slug=rec.agent_slug,
        from_tier=rec.current_tier,
        to_tier=rec.recommended_tier,
        action="promote",
        author="framework-auto",
        sp_chain_id="SP-AUTO-{:08x}".format(prior_tip + 1),
        evidence_hmac=(
            rec.evidence.tournament_report_hmacs[0]
            if rec.evidence.tournament_report_hmacs
            else "0" * 64
        ),
        prior_hash="0" * 64,  # cli.py verify walks chain
        chain_length=prior_tip + 1,
        prior_commit_sha=_git_head_sha() or "0" * 40,
    )
    _emit(
        ACTION_PROMOTE_APPLIED,
        agent_slug=rec.agent_slug,
        from_tier=rec.current_tier,
        to_tier=rec.recommended_tier,
        evidence_hmac=(
            rec.evidence.tournament_report_hmacs[0]
            if rec.evidence.tournament_report_hmacs
            else None
        ),
    )
    return ApplyOutcome(
        agent_slug=rec.agent_slug,
        outcome="applied",
        from_tier=rec.current_tier,
        to_tier=rec.recommended_tier,
    )


def _apply_demote(
    rec: Recommendation,
    adr_scaffold_dir: Path,
) -> ApplyOutcome:
    """Emit demote request + ADR scaffold (no frontmatter mutation)."""
    _emit(
        ACTION_DEMOTE_REQUESTED,
        agent_slug=rec.agent_slug,
        from_tier=rec.current_tier,
        to_tier=rec.recommended_tier,
        owner_sign_cli=_owner_sign_cli(rec),
    )
    _emit_adr_amendment_scaffold(
        rec.agent_slug,
        rec.current_tier,
        rec.recommended_tier,
        {
            "n": rec.evidence.n,
            "gap_pp": rec.evidence.gap_pp,
            "runs_considered": rec.evidence.runs_considered,
        },
        adr_scaffold_dir,
    )
    return ApplyOutcome(
        agent_slug=rec.agent_slug,
        outcome="demote_requested",
        from_tier=rec.current_tier,
        to_tier=rec.recommended_tier,
    )


def _owner_sign_cli(rec: Recommendation) -> str:
    """Canonical Owner-signature CLI string for a rec."""
    return (
        "ceo-tier-policy owner-sign "
        "--agent {a} --from {f} --to {t} "
        "--sp-chain-id SP-NNN-<hex>"
    ).format(
        a=rec.agent_slug,
        f=rec.current_tier,
        t=rec.recommended_tier,
    )


def _process_single_rec(
    rec: Recommendation,
    policy: TierPolicyRecord,
    agents_dir: Path,
    baseline_agents_dir: Path,
    sigchain_path: Path,
    adr_scaffold_dir: Path,
    *,
    cost_gate_usd: float,
    audit_log_path: Optional[Path],
    sentinel_path: Optional[Path],
    dry_run: bool,
    now: datetime,
) -> ApplyOutcome:
    """Apply a single recommendation. See apply() docstring.

    Dispatches to per-action helpers (``_reject_veto_floor``,
    ``_reject_hold``, ``_check_adopter_override``, ``_apply_promote``,
    ``_apply_demote``). Defense-in-depth VETO re-check runs first
    (C-P0-3).
    """
    if rec.agent_slug in VETO_HARDCODE_APPLY:
        return _reject_veto_floor(rec)

    if rec.action == "hold":
        return _reject_hold(rec)

    override = _check_adopter_override(
        rec, agents_dir, baseline_agents_dir
    )
    if override is not None:
        return override

    if rec.action == "promote":
        return _apply_promote(
            rec, policy, agents_dir, sigchain_path,
            cost_gate_usd=cost_gate_usd,
            audit_log_path=audit_log_path,
            sentinel_path=sentinel_path,
            dry_run=dry_run,
            now=now,
        )

    return _apply_demote(rec, adr_scaffold_dir)


def _git_head_sha() -> Optional[str]:
    """Return current git HEAD sha via subprocess, None on failure."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None
    except Exception:
        return None
