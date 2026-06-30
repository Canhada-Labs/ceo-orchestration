#!/usr/bin/env python3
"""PLAN-104 Wave D — persona-demand match resolver + 19th-check RED logic.

Stateless audit-log scanner. Joins open `persona_demand_opened` events
to dispatch events (`agent_spawn`) within the match window, emitting:

  - persona_demand_matched   when an `agent_spawn` of expected_persona
                              fires after demand_opened in the same window
  - persona_demand_unmet     when window expires with no matching dispatch
                              and no waive (idempotent — emitted exactly once)
  - persona_demand_waived    when commit-message waive parses successfully
                              within the window (emitted by ceremony/ceo-boot,
                              not by this resolver — included here for set-algebra)

PLAN-104 sec 2.2 (state machine) + sec 2.4 (19th-check RED).

Strict-match: actual_persona == expected_persona (S134 R2 Q4 fold).
No peer substitution.

Window: 24h uniform (S134 R2 Q3 fold).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, NamedTuple, Optional, Set, Tuple

DEFAULT_AUDIT_LOG = Path(
    os.environ.get(
        "CEO_AUDIT_LOG_DIR",
        str(Path.home() / ".claude" / "projects" / "ceo-orchestration"),
    )
) / "audit-log.jsonl"

MATCH_WINDOW_HOURS = 24
TREND_WINDOW_HOURS = 168

# PLAN-132 / ADR-145 — cross-model Codex review as a recognized satisfaction
# modality for code-reviewer demands ONLY. This is a single hard-coded literal
# guard (NOT a config toggle) so widening the relaxation to any other persona
# requires a code change + a fresh ADR (R3 doctrine-creep closure).
_CODEX_MODALITY_PERSONA = "code-reviewer"
# Only review-shaped Codex emit sources that carry branch-binding satisfy a
# demand. `phase_gate` (a per-plan-phase review from check_pair_rail) is
# EXCLUDED — it belongs to a different workflow and carries no branch binding.
_CODEX_REVIEW_SOURCES_THAT_SATISFY = frozenset({"adhoc_mcp", "user_code_auto"})


class DemandRecord(NamedTuple):
    demand_id: str
    demand_event_type: str
    expected_persona: str
    target_ref_hash: str
    opened_ts: float


def _parse_ts(ev: Dict[str, Any]) -> Optional[float]:
    ts = ev.get("ts") or ev.get("timestamp")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, AttributeError):
        return None


def _iter_events_since(audit_log: Path, hours: int) -> Iterator[Dict[str, Any]]:
    if not audit_log.exists():
        return
    cutoff = time.time() - hours * 3600
    try:
        with audit_log.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts_epoch = _parse_ts(ev)
                if ts_epoch is None or ts_epoch < cutoff:
                    continue
                yield ev
    except OSError:
        return


def _index_demands(events: List[Dict[str, Any]]) -> Tuple[Dict[str, DemandRecord], Set[str], Set[str], Set[str]]:
    """Return (opened_by_id, matched_ids, unmet_ids, waived_ids)."""
    opened: Dict[str, DemandRecord] = {}
    matched: Set[str] = set()
    unmet: Set[str] = set()
    waived: Set[str] = set()
    for ev in events:
        action = ev.get("action")
        did = ev.get("demand_id")
        if not did:
            continue
        if action == "persona_demand_opened":
            ts_epoch = _parse_ts(ev) or 0.0
            opened[did] = DemandRecord(
                demand_id=did,
                demand_event_type=ev.get("demand_event_type", ""),
                expected_persona=ev.get("expected_persona", ""),
                target_ref_hash=ev.get("target_ref_hash", ""),
                opened_ts=ts_epoch,
            )
        elif action == "persona_demand_matched":
            matched.add(did)
        elif action == "persona_demand_unmet":
            unmet.add(did)
        elif action == "persona_demand_waived":
            waived.add(did)
    return opened, matched, unmet, waived


def _index_dispatches(events: List[Dict[str, Any]]) -> List[Tuple[float, str]]:
    """Return (ts_epoch, persona) for agent_spawn events. Sorted ascending."""
    out: List[Tuple[float, str]] = []
    for ev in events:
        if ev.get("action") != "agent_spawn":
            continue
        ts_epoch = _parse_ts(ev)
        if ts_epoch is None:
            continue
        persona = (
            ev.get("subagent_type")
            or ev.get("archetype")
            or ev.get("agent_type")
            or ""
        )
        if persona:
            out.append((ts_epoch, persona))
    out.sort()
    return out


def _index_codex_reviews(events: List[Dict[str, Any]]) -> List[Tuple[float, str]]:
    """Return (ts_epoch, target_ref_hash) for branch-bound codex_review_invoked
    events eligible to satisfy a code-reviewer demand. Sorted ascending.

    PLAN-132 / ADR-145. A codex review qualifies ONLY when it is:
      - from a review-shaped source in `_CODEX_REVIEW_SOURCES_THAT_SATISFY`
        (excludes `phase_gate`, which is a different workflow), AND
      - carries a NON-EMPTY 12-hex `target_ref_hash` (branch-binding).

    The empty / missing `target_ref_hash` case is FAIL-CLOSED: a review the
    emitter could not bind to a branch (detached HEAD, trunk, unresolved)
    cannot satisfy any demand. This is what stops the R1 cross-branch hole —
    a review event with no branch can never equal a demand's target_ref_hash.
    Legacy codex_review_invoked events (no review_source/target_ref_hash) are
    therefore inert here, exactly as intended.
    """
    out: List[Tuple[float, str]] = []
    for ev in events:
        if ev.get("action") != "codex_review_invoked":
            continue
        if ev.get("review_source") not in _CODEX_REVIEW_SOURCES_THAT_SATISFY:
            continue
        trh = ev.get("target_ref_hash") or ""
        if not trh:
            continue  # fail-closed: no branch binding -> cannot satisfy
        ts_epoch = _parse_ts(ev)
        if ts_epoch is None:
            continue
        out.append((ts_epoch, trh))
    out.sort()
    return out


def _codex_review_hit(
    rec: "DemandRecord",
    codex_reviews: List[Tuple[float, str]],
) -> Optional[float]:
    """Return the ts of the first in-window, branch-bound Codex review that
    satisfies `rec`, or None. code-reviewer demands ONLY (literal guard).

    Branch-binding: the review's target_ref_hash MUST equal the demand's
    target_ref_hash (R1 closure). Window semantics are IDENTICAL to the
    native agent_spawn path (opened_ts .. opened_ts + 24h) so the two
    satisfaction modalities behave the same w.r.t. timing.
    """
    if rec.expected_persona != _CODEX_MODALITY_PERSONA:
        return None
    if not rec.target_ref_hash:
        return None  # demand itself has no branch binding -> cannot match
    window_start = rec.opened_ts
    window_end = rec.opened_ts + MATCH_WINDOW_HOURS * 3600
    for r_ts, r_hash in codex_reviews:
        if r_ts < window_start:
            continue
        if r_ts > window_end:
            break
        if r_hash == rec.target_ref_hash:
            return r_ts
    return None


def resolve(audit_log: Path = DEFAULT_AUDIT_LOG) -> Dict[str, Any]:
    """Compute per-demand terminal state + emit catch-up events.

    Returns a summary dict consumed by the 19th check and by tests.
    Emits `persona_demand_matched` for any demand whose dispatch is
    in-window and no terminal event seen yet. Emits
    `persona_demand_unmet` for any demand whose window expired with
    no match and no waive.

    Kill-switch CEO_PERSONA_DEMAND_LEDGER_DISABLED=1 returns an empty
    summary (no scan, no emit) — defense-in-depth on top of the
    scanner-side guard.
    """
    if os.environ.get("CEO_PERSONA_DEMAND_LEDGER_DISABLED") == "1":
        return {
            "opened": {}, "matched": set(), "unmet": set(), "waived": set(),
            "new_matches": [], "new_unmet": [], "dispatches_count": 0,
        }
    events = list(_iter_events_since(audit_log, TREND_WINDOW_HOURS))
    opened, matched, unmet, waived = _index_demands(events)
    dispatches = _index_dispatches(events)
    codex_reviews = _index_codex_reviews(events)

    # (rec, ts, actual_persona, match_modality)
    new_matches: List[Tuple[DemandRecord, float, str, str]] = []
    new_unmet: List[DemandRecord] = []

    now = time.time()
    window_s = MATCH_WINDOW_HOURS * 3600

    for did, rec in opened.items():
        if did in matched or did in unmet or did in waived:
            continue
        # Find first dispatch of expected persona within window.
        window_start = rec.opened_ts
        window_end = rec.opened_ts + window_s
        dispatch_hit: Optional[Tuple[float, str]] = None
        for d_ts, d_persona in dispatches:
            if d_ts < window_start:
                continue
            if d_ts > window_end:
                break
            if d_persona == rec.expected_persona:
                dispatch_hit = (d_ts, d_persona)
                break
        if dispatch_hit is not None:
            new_matches.append((rec, dispatch_hit[0], dispatch_hit[1], "native_spawn"))
            continue
        # PLAN-132 / ADR-145 — code-reviewer demands may ALSO be satisfied by a
        # branch-bound, in-window cross-model Codex review (other 3 demand types
        # stay strict native-spawn match via the literal guard in _codex_review_hit).
        codex_ts = _codex_review_hit(rec, codex_reviews)
        if codex_ts is not None:
            new_matches.append((rec, codex_ts, _CODEX_MODALITY_PERSONA, "codex_review"))
            continue
        if now > window_end:
            new_unmet.append(rec)

    return {
        "opened": opened,
        "matched": matched,
        "unmet": unmet,
        "waived": waived,
        "new_matches": new_matches,
        "new_unmet": new_unmet,
        "dispatches_count": len(dispatches),
    }


def emit_resolutions(summary: Dict[str, Any], session_id: str = "") -> Tuple[int, int]:
    """Emit catch-up _matched + _unmet events. Returns (matched_n, unmet_n).

    Hasattr-guarded — adopter installs pre-ceremony see no emit.
    """
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks" / "_lib"))
        import audit_emit as _ae
    except Exception:
        return (0, 0)
    matched_n = 0
    unmet_n = 0
    fn_matched = getattr(_ae, "emit_persona_demand_matched", None)
    fn_unmet = getattr(_ae, "emit_persona_demand_unmet", None)
    if fn_matched is not None:
        for rec, d_ts, actual_persona, modality in summary.get("new_matches", []):
            try:
                latency_ms = int(max(0, (d_ts - rec.opened_ts) * 1000))
                # PLAN-132 — match_modality co-ships with audit_emit in the same
                # GPG ceremony, so the kwarg is always accepted post-ship. If a
                # mismatched (pre-PLAN-132) audit_emit is ever loaded, the TypeError
                # is swallowed below (fail-soft -> reverts to the prior false-RED,
                # never a crash).
                fn_matched(
                    demand_id=rec.demand_id,
                    demand_event_type=rec.demand_event_type,
                    expected_persona=rec.expected_persona,
                    actual_persona=actual_persona,
                    latency_ms=latency_ms,
                    match_modality=modality,
                    session_id=session_id,
                    project="ceo-orchestration",
                )
                matched_n += 1
            except Exception:
                continue
    if fn_unmet is not None:
        for rec in summary.get("new_unmet", []):
            try:
                window_expired_at = datetime.fromtimestamp(
                    rec.opened_ts + MATCH_WINDOW_HOURS * 3600,
                    tz=timezone.utc,
                ).isoformat().replace("+00:00", "Z")
                fn_unmet(
                    demand_id=rec.demand_id,
                    demand_event_type=rec.demand_event_type,
                    expected_persona=rec.expected_persona,
                    target_ref_hash=rec.target_ref_hash,
                    window_expired_at=window_expired_at,
                    session_id=session_id,
                    project="ceo-orchestration",
                )
                unmet_n += 1
            except Exception:
                continue
    return (matched_n, unmet_n)


def atrophy_7d_status(audit_log: Path = DEFAULT_AUDIT_LOG) -> Tuple[str, str, Dict[str, int]]:
    """19th-check RED logic. Returns (status, summary, metrics).

    Set-algebra per PLAN-104 sec 2.4 (S134 R2 P0 #4 + Codex iter-1 P0 #2 fold):

      satisfied        = opened & matched
      unmet_recorded   = (opened & unmet) - matched - waived
      waived_eff       = (opened & waived) - matched
      effective_unmet  = opened where opened_ts + 24h < now AND no terminal AND no dispatch-match
                         (defense-in-depth: status path computes expiry even
                         when resolver catch-up emit hasn't fired yet)
      still_open       = opened where opened_ts + 24h >= now AND no terminal
      eligible_settled = satisfied | unmet_total | waived_eff

      not opened           -> green "no eligible persona demand in 168h"
      not eligible_settled -> green "<N> demand(s) still inside window"
      not unmet_total      -> green "<S>/<E> demands matched (<W> waived)"
      else                 -> red   "<U> persona demand(s) unmet in 168h ..."

    Codex iter-1 P0 #2 fold: previously the status only counted unmet from
    the recorded `persona_demand_unmet` events. If `resolve()`/catch-up
    emit was not invoked (e.g. resolver disabled mid-session), every
    opened-no-terminal would be "still_open" forever and RED never
    triggers. Now status computes effective expiry inline.
    """
    events = list(_iter_events_since(audit_log, TREND_WINDOW_HOURS))
    opened, matched, unmet, waived = _index_demands(events)
    dispatches = _index_dispatches(events)
    codex_reviews = _index_codex_reviews(events)
    opened_set = set(opened.keys())

    # Compute effective_unmet inline (defense-in-depth, doesn't require
    # the resolver catch-up emit to have run).
    now = time.time()
    window_s = MATCH_WINDOW_HOURS * 3600
    effective_unmet: Set[str] = set()
    effective_still_open: Set[str] = set()

    for did, rec in opened.items():
        if did in matched or did in unmet or did in waived:
            continue
        window_end = rec.opened_ts + window_s
        # Did an in-window dispatch of expected persona happen?
        dispatch_hit = False
        for d_ts, d_persona in dispatches:
            if d_ts < rec.opened_ts:
                continue
            if d_ts > window_end:
                break
            if d_persona == rec.expected_persona:
                dispatch_hit = True
                break
        # PLAN-132 / ADR-145 — a branch-bound, in-window Codex review also
        # satisfies a code-reviewer demand (literal-guarded inside
        # _codex_review_hit; other 3 demand types stay strict native match).
        if not dispatch_hit and _codex_review_hit(rec, codex_reviews) is not None:
            dispatch_hit = True
        if dispatch_hit:
            # Treat as effectively satisfied (catch-up emit will record matched).
            matched = matched | {did}
            continue
        if now > window_end:
            effective_unmet.add(did)
        else:
            effective_still_open.add(did)

    satisfied = opened_set & matched
    unmet_recorded = (opened_set & unmet) - matched - waived
    waived_eff = (opened_set & waived) - matched
    unmet_total = unmet_recorded | (effective_unmet - waived)
    eligible_settled = satisfied | unmet_total | waived_eff

    metrics = {
        "opened": len(opened_set),
        "satisfied": len(satisfied),
        "unmet": len(unmet_total),
        "waived": len(waived_eff),
        "still_open": len(effective_still_open),
        "eligible_settled": len(eligible_settled),
        "eligible_demand_events": len(eligible_settled),
    }

    if not opened_set:
        return "green", "no eligible persona demand in 168h", metrics
    if not eligible_settled:
        return "green", f"{len(effective_still_open)} demand(s) still inside window", metrics
    if not unmet_total:
        return (
            "green",
            f"{len(satisfied)}/{len(eligible_settled)} demands matched ({len(waived_eff)} waived)",
            metrics,
        )
    return (
        "red",
        (
            f"{len(unmet_total)} persona demand(s) unmet in 168h "
            f"(satisfied={len(satisfied)}, waived={len(waived_eff)}, "
            f"still_open={len(effective_still_open)})"
        ),
        metrics,
    )


def emit_waives_for_scanned(
    scanned: "List[Any]",
    audit_log: Path,
    repo_root: Path,
    session_id: str = "",
) -> int:
    """Scan commit messages for persona-waive trailers; emit _waived
    scoped to the SPECIFIC demands the waiving commit touches.

    Codex iter-2 P0 #1 fold: a waive must be spatially scoped to the
    waiving commit's changed paths (or, for branch_ahead, the waiving
    commit's branch). Otherwise an old waive could mute new demands —
    a bypass vector. We accept the `scanned` list (raw DemandEvent
    records with target_ref still in cleartext) so we can match
    target_ref against `git show --name-only <commit>`.

    Algorithm:
      For each waive trailer in commit C with persona P + reason R:
        - Get changed paths in C via `git show --name-only C`
        - For each scanned demand D with expected_persona == P:
            - file-edit demands: emit _waived(D) iff D.target_ref in changed_paths
            - branch_ahead demands: emit _waived(D) iff C is reachable from
              the demand's branch (i.e. `git merge-base --is-ancestor C branch`)
        - Dedup by demand_id only (Codex iter-2 P1 #3 fold)

    Returns count of _waived events emitted.

    Hasattr-guarded — adopter installs pre-ceremony see no emit.
    """
    if os.environ.get("CEO_PERSONA_DEMAND_LEDGER_DISABLED") == "1":
        return 0
    # NOTE: empty `scanned` no longer short-circuits (Codex iter-3 P0).
    # Waive may apply to demands not in the current scan if a waive
    # commit was added after the demand was opened. `all_candidates`
    # is recomputed via `persona_demand_scan.detect_all()` below.
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import persona_waive_parser as wp
    except Exception:
        return 0
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks" / "_lib"))
        import audit_emit as _ae
    except Exception:
        return 0
    fn = getattr(_ae, "emit_persona_demand_waived", None)
    if fn is None:
        return 0

    # Codex iter-3 P0 + iter-4 P1 #1 fold: prefer the caller's
    # already-detected full candidate set (passed as `scanned`) over
    # re-running detect_all(). If `scanned` was the dedup'd subset (or
    # empty), fall back to a fresh detect_all() to ensure waive coverage
    # of already-opened demands. ceo-boot.py is updated to pass
    # detect_all() output directly so this branch is rarely taken.
    if scanned:
        all_candidates = list(scanned)
    else:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import persona_demand_scan as _ds
            all_candidates = _ds.detect_all(repo_root)
        except Exception:
            all_candidates = []

    # Filter out demands that already have a terminal event in audit-log.
    events = list(_iter_events_since(audit_log, TREND_WINDOW_HOURS))
    _, matched, unmet, waived = _index_demands(events)
    active_by_persona: Dict[str, List["Any"]] = {}
    for d in all_candidates:
        if d.demand_id in matched or d.demand_id in unmet or d.demand_id in waived:
            continue
        active_by_persona.setdefault(d.expected_persona, []).append(d)

    if not active_by_persona:
        return 0

    import subprocess
    try:
        log_out = subprocess.check_output(
            ["git", "log", f"--since={TREND_WINDOW_HOURS}h",
             "--pretty=format:__SHA__%H%n%B%n__END_COMMIT__"],
            cwd=str(repo_root), stderr=subprocess.DEVNULL, text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 0

    n = 0
    seen_waived_ids: Set[str] = set()  # Codex iter-2 P1 #3: dedup by demand_id only
    cur_sha = ""
    cur_msg_lines: List[str] = []
    for line in log_out.splitlines():
        if line.startswith("__SHA__"):
            cur_sha = line[len("__SHA__"):].strip()
            cur_msg_lines = []
            continue
        if line == "__END_COMMIT__":
            msg = "\n".join(cur_msg_lines)
            waives = wp.parse_commit_message(msg)
            if waives and cur_sha:
                try:
                    paths_out = subprocess.check_output(
                        ["git", "show", "--name-only", "--pretty=format:", cur_sha],
                        cwd=str(repo_root), stderr=subprocess.DEVNULL, text=True,
                    )
                    changed_paths = {p.strip() for p in paths_out.splitlines() if p.strip()}
                except (subprocess.CalledProcessError, FileNotFoundError):
                    changed_paths = set()

                for waive in waives:
                    candidates = active_by_persona.get(waive.persona, [])
                    for d in candidates:
                        if d.demand_id in seen_waived_ids:
                            continue
                        # Match scoping: file-edit demands by changed_paths,
                        # branch_ahead by branch reachability.
                        target_ref = d.target_ref
                        is_match = False
                        if d.demand_event_type == "branch_ahead":
                            branch = target_ref[len("branch:"):] if target_ref.startswith("branch:") else target_ref
                            # Codex iter-3 P1 fold: a waive on `main`
                            # (an ancestor of every branch) must NOT
                            # waive arbitrary branch_ahead demands.
                            # Require the waive commit to be in the
                            # ahead range: ancestor of branch AND NOT
                            # ancestor of origin/main (i.e. on the
                            # branch's side of the divergence).
                            try:
                                rc_branch = subprocess.run(
                                    ["git", "merge-base", "--is-ancestor", cur_sha, branch],
                                    cwd=str(repo_root),
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                ).returncode
                                rc_main = subprocess.run(
                                    ["git", "merge-base", "--is-ancestor", cur_sha, "origin/main"],
                                    cwd=str(repo_root),
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                ).returncode
                                if rc_main != 0:
                                    # Fall back to local main when no origin
                                    rc_main = subprocess.run(
                                        ["git", "merge-base", "--is-ancestor", cur_sha, "main"],
                                        cwd=str(repo_root),
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    ).returncode
                                # Match: on branch AND not on main trunk.
                                is_match = (rc_branch == 0 and rc_main != 0)
                            except Exception:
                                is_match = False
                        else:
                            # File-edit demand: target_ref is a file path
                            is_match = target_ref in changed_paths
                        if not is_match:
                            continue
                        seen_waived_ids.add(d.demand_id)
                        try:
                            fn(
                                demand_id=d.demand_id,
                                demand_event_type=d.demand_event_type,
                                expected_persona=waive.persona,
                                waive_reason=waive.reason,
                                session_id=session_id,
                                project="ceo-orchestration",
                            )
                            n += 1
                        except Exception:
                            continue
            cur_sha = ""
            continue
        cur_msg_lines.append(line)
    return n


# Back-compat alias for any caller from iter-1.
def scan_and_emit_waives(audit_log: Path, repo_root: Path, session_id: str = "") -> int:
    """Deprecated thin wrapper — runs scanner.scan() to recover target_refs
    and delegates to emit_waives_for_scanned (Codex iter-2 P0 #1 scoping).
    """
    if os.environ.get("CEO_PERSONA_DEMAND_LEDGER_DISABLED") == "1":
        return 0
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import persona_demand_scan as ds
    except Exception:
        return 0
    scanned = ds.scan(repo_root, audit_log)
    return emit_waives_for_scanned(scanned, audit_log, repo_root, session_id)


def main() -> int:
    parser = argparse.ArgumentParser(description="persona-demand resolver + 19th-check status")
    parser.add_argument("--audit-log", default=str(DEFAULT_AUDIT_LOG))
    parser.add_argument("--mode", choices=["resolve", "status"], default="status")
    parser.add_argument("--no-emit", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    audit = Path(args.audit_log).resolve()
    if args.mode == "resolve":
        summary = resolve(audit)
        if not args.no_emit:
            m, u = emit_resolutions(summary)
            print(f"# matched={m} unmet={u}", file=sys.stderr)
        if args.json:
            out = {
                "new_matches": len(summary["new_matches"]),
                "new_unmet": len(summary["new_unmet"]),
                "dispatches_count": summary["dispatches_count"],
                "opened_total": len(summary["opened"]),
            }
            print(json.dumps(out))
    else:
        status, msg, metrics = atrophy_7d_status(audit)
        if args.json:
            print(json.dumps({"status": status, "summary": msg, "metrics": metrics}))
        else:
            print(f"{status}: {msg}")
            print(f"  {metrics}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
