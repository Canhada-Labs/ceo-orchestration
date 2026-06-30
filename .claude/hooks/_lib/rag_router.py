"""rag_router.py — PLAN-097 Wave C / ADR-062-AMEND-1 / ADR-128 §6.

Routing layer that decides whether to dispatch retrieval queries to the
LightRAG C2 sidecar OR fall through to CAG retrieval. The framework
core invokes `route_query()` and respects the returned decision
(`AUTO_WIRE`, `SKIP_SIDECAR_DOWN`, `KILL_SWITCH`, `PROFILE_INELIGIBLE`).

Stdlib-only (ADR-002). Fail-degraded (ADR-005, ADR-062 §Invariants
bullet 3): any error in predicate evaluation falls through to CAG
retrieval without raising.

Kill-switch precedence (ADR-062-AMEND-1 §kill-switch precedence):
  1. CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED=0 → KILL_SWITCH
  2. CEO_RAG_SIDECAR=0 (legacy alias) → KILL_SWITCH
  3. profile=LARGE AND sidecar_socket_present AND health-probe-OK → AUTO_WIRE
  4. otherwise → PROFILE_INELIGIBLE or SKIP_SIDECAR_DOWN

Canonical destination at ceremony: .claude/hooks/_lib/rag_router.py

## PLAN-113 W6 dead-code disposition (F-11.3)

As of PLAN-120-FOLLOWUP (S186), `route_query()` IS wired in production by
`skill-retrieve.py::_rag_retrieve` (opt-in, default-OFF) — LOAD-BEARING but
TELEMETRY-ONLY, not dead code (the audit's E3-F9 "zero callers" was stale). Per the PLAN-113 C2 doctrine,
a dispositioned-dead **security-relevant** path is NOT deleted on the dead
signal alone; it must be verified to FAIL CLOSED while dead. The default
posture (no `repo-profile.yaml`, no kill-switch enabled, no sidecar socket)
resolves to PROFILE_INELIGIBLE / SKIP_SIDECAR_DOWN — never AUTO_WIRE — so the
retrieval path stays inert and cannot dispatch to the sidecar without explicit
opt-in. Regression coverage: `_lib/tests/test_rag_dead_code_disposition.py`.
Re-wiring RAG into production is OUT OF SCOPE for W6 (tracked separately as
PLAN-097-FOLLOWUP-rag-router-wireup). Do not delete; do not auto-wire.
"""
from __future__ import annotations

import json
import os
import re
import socket
from pathlib import Path
from typing import Optional, Tuple

# Routing decision sentinels.
AUTO_WIRE = "auto_wire"
SKIP_SIDECAR_DOWN = "skip_sidecar_down"
KILL_SWITCH = "kill_switch"
PROFILE_INELIGIBLE = "profile_ineligible"

# Default Unix socket path for the C2 sidecar (per ADR-062 §Architecture).
_DEFAULT_SOCKET_PATH = "~/.ceo-orchestration/rag/sidecar.sock"
_DEFAULT_HEALTH_TIMEOUT_S = 2.0  # ADR-062 §Kill-switches CEO_RAG_QUERY_TIMEOUT_MS

# Repo-profile yaml path (relative to repo root).
_REPO_PROFILE_REL = ".claude/repo-profile.yaml"

# LARGE threshold per PLAN-097 Wave C.1 — LoC ≥ 200,000.
_LARGE_LOC_THRESHOLD = 200_000


def _kill_switch_set() -> Optional[str]:
    """Return the env-var name whose value is "0" if any kill-switch is set,
    None otherwise. Class kill-switch takes precedence over legacy alias.
    """
    if os.environ.get("CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED") == "0":
        return "CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED"
    if os.environ.get("CEO_RAG_SIDECAR") == "0":
        return "CEO_RAG_SIDECAR"
    return None


def _repo_profile_size(repo_root: Path) -> Optional[str]:
    """Return profile size class (SMALL/MEDIUM/LARGE) from repo-profile.yaml.

    Returns None if profile not detected OR `size_class` field absent.
    Backward-compat: pre-PLAN-097-Wave-C profiles MAY lack `size_class`
    field (only risk_class). In that case we cannot evaluate LARGE
    predicate and return None.
    """
    profile_path = repo_root / _REPO_PROFILE_REL
    if not profile_path.is_file():
        return None
    try:
        text = profile_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = re.search(r'^size_class:\s*"([^"]+)"\s*$', text, re.MULTILINE)
    if m:
        size = m.group(1).strip().upper()
        if size in ("SMALL", "MEDIUM", "LARGE"):
            return size
    return None


def _sidecar_socket_path() -> Path:
    """Resolve the C2 sidecar Unix-socket path (env override OR default).

    Canonical env var: CEO_RAG_SIDECAR_SOCKET.  The router is the decision
    authority, so this is the single source of truth for the socket path.
    The bridge module reads the SAME canonical var (with CEO_RAG_SOCKET as a
    back-compat alias) to eliminate the router↔bridge socket-path mismatch
    that silently caused AUTO_WIRE decisions to fall back to tf-idf.
    """
    raw = os.environ.get("CEO_RAG_SIDECAR_SOCKET") or _DEFAULT_SOCKET_PATH
    return Path(os.path.expanduser(raw))


def _sidecar_socket_present() -> bool:
    """True iff the sidecar socket file exists. Symlink-safe."""
    p = _sidecar_socket_path()
    try:
        return p.exists() and p.is_socket()
    except OSError:
        return False


def _sidecar_health_probe(timeout_s: float = _DEFAULT_HEALTH_TIMEOUT_S) -> bool:
    """Probe sidecar Unix socket — connect + close. Fail-degraded on any error."""
    p = _sidecar_socket_path()
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout_s)
        sock.connect(str(p))
        sock.close()
        return True
    except (OSError, socket.timeout):
        return False


def evaluate_predicate(repo_root: Path, skip_health_probe: bool = False) -> Tuple[str, str]:
    """Evaluate the routing predicate. Returns (decision, reason).

    decision: one of AUTO_WIRE / SKIP_SIDECAR_DOWN / KILL_SWITCH / PROFILE_INELIGIBLE
    reason: short string for audit emit `reason` field
    """
    ks = _kill_switch_set()
    if ks is not None:
        return KILL_SWITCH, f"env:{ks}=0"
    size = _repo_profile_size(repo_root)
    if size != "LARGE":
        return PROFILE_INELIGIBLE, f"profile={size or 'absent'}"
    if not _sidecar_socket_present():
        return SKIP_SIDECAR_DOWN, "socket-missing"
    if skip_health_probe:
        return AUTO_WIRE, "predicate-true-probe-skipped"
    if not _sidecar_health_probe():
        return SKIP_SIDECAR_DOWN, "health-probe-failed"
    return AUTO_WIRE, "predicate-true"


def route_query(
    repo_root: Optional[Path] = None,
    query_class: str = "semantic",
    skip_health_probe: Optional[bool] = None,
) -> Tuple[str, str]:
    """Public entry — evaluate predicate, emit audit, return decision.

    Args:
        repo_root: repo root path (defaults to cwd).
        query_class: one of `semantic` / `timeline` / `get_observations`.
        skip_health_probe: override health-probe (None = read env CEO_RAG_HEALTH_PROBE).

    Returns:
        (decision, reason) — caller honors decision and falls through to CAG
        when decision != AUTO_WIRE.
    """
    if repo_root is None:
        repo_root = Path.cwd()
    if skip_health_probe is None:
        skip_health_probe = os.environ.get("CEO_RAG_HEALTH_PROBE") == "0"
    decision, reason = evaluate_predicate(repo_root, skip_health_probe=skip_health_probe)
    _emit_routing_audit(decision, reason, query_class)
    return decision, reason


def _emit_routing_audit(decision: str, reason: str, query_class: str) -> None:
    """Emit the appropriate audit event per decision. Fail-open."""
    try:
        from _lib import audit_emit
    except Exception:
        return
    try:
        if decision == AUTO_WIRE:
            if hasattr(audit_emit, "emit_rag_query_routed"):
                audit_emit.emit_rag_query_routed(
                    query_class=query_class,
                    result="dispatched",
                    latency_ms_p50=None,
                )
        elif decision == SKIP_SIDECAR_DOWN:
            if hasattr(audit_emit, "emit_rag_auto_wire_skipped_sidecar_down"):
                audit_emit.emit_rag_auto_wire_skipped_sidecar_down(reason=reason)
        elif decision in (KILL_SWITCH, PROFILE_INELIGIBLE):
            pass
    except Exception:
        return


# AC10 / AC11 thresholds (ADR-062-AMEND-1 §Risks, PLAN-097 §6b).
# Demotion is observability-only — events fire; actual routing demotion
# requires Owner intervention (set kill-switch).  Auto-demote is out of
# scope per ADR-062-AMEND-1 §Implementation.
_FALSE_LARGE_THRESHOLD_X100 = 100  # 1% false-LARGE rate
_HIT_RATE_FLOOR_X100 = 6000  # 60% minimum hit-rate


def emit_cascade_quality(
    chunks_requested: int,
    chunks_returned: int,
    repo_profile_size: str,
    window_days: int = 7,
) -> None:
    """Emit demotion signals at the real cascade decision points.

    Called after a RAG retrieval completes in AUTO_WIRE posture.  Two
    quality signals are evaluated:

    AC10 — false-LARGE demotion:
        If the repo profile says LARGE but zero chunks were returned the
        retrieval was vacuous — the LARGE classification may be false.
        Fires ``rag_false_large_demoted`` (observability-only per
        ADR-062-AMEND-1).

    AC11 — hit-rate degradation:
        hit_rate_x100 = (chunks_returned / chunks_requested) × 10000.
        When the ratio falls below ``_HIT_RATE_FLOOR_X100`` (60%),
        fires ``rag_hit_rate_degraded``.

    Both events are best-effort (fail-open on any exception).
    """
    try:
        from _lib import audit_emit
    except Exception:
        return
    try:
        # AC10 — false-LARGE: profile=LARGE but zero results returned
        if repo_profile_size == "LARGE" and chunks_requested > 0 and chunks_returned == 0:
            if hasattr(audit_emit, "emit_rag_false_large_demoted"):
                audit_emit.emit_rag_false_large_demoted(
                    false_large_rate_x100=_FALSE_LARGE_THRESHOLD_X100,
                    window_days=window_days,
                )

        # AC11 — hit-rate degradation
        if chunks_requested > 0:
            hit_rate_x100 = int((chunks_returned / chunks_requested) * 10000)
            if hit_rate_x100 < _HIT_RATE_FLOOR_X100:
                if hasattr(audit_emit, "emit_rag_hit_rate_degraded"):
                    audit_emit.emit_rag_hit_rate_degraded(
                        hit_rate_x100=hit_rate_x100,
                        window_days=window_days,
                    )
    except Exception:
        return
