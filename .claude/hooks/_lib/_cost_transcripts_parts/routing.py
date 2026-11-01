"""Extracted cost-transcripts implementation: routing."""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

def routing_invariant(
    project_dir: Any,
    cutoff: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Assert, over the spawn sidecars + transcripts under `project_dir`,
    that served == declared and that VETO archetypes were served inside the
    floor. Pure read; returns the verdict as JSON-safe data."""
    project_dir = Path(project_dir)
    root_real = os.path.realpath(str(project_dir))
    floor = _floor_source()
    families = known_families(floor)
    veto_roles = floor[0] if floor else frozenset()
    veto_allowed = floor[1] if floor else frozenset()

    counts: Dict[str, int] = {
        "sidecars": 0,
        "declared": 0,
        "undeclared": 0,
        "unclassified": 0,
        "compared_spawns": 0,
        "declared_compared": 0,
        "floor_checked": 0,
        "no_served": 0,
        "out_of_window": 0,
        "unreadable_sidecars": 0,
        "refused_paths": 0,
        "incomplete_reads": 0,
        "served_unresolved": 0,
        "synthetic_turns_ignored": 0,
        "chunk_model_splits": 0,
        "chunk_terminal_unprovable": 0,
    }
    violations: List[Dict[str, Any]] = []
    alias_resolutions: Dict[str, Dict[str, int]] = {}
    unclassified_samples: List[str] = []

    def gates_the_window(transcript: str) -> bool:
        """A sidecar the check cannot trust (unreadable, refused, or a
        declaration it cannot classify) may gate THIS window only if its
        spawn has a turn in it. A stale one from outside the window is
        counted where it belongs and never reaches the verdict."""
        if not os.path.exists(transcript):
            counts["no_served"] += 1
            return False
        if not _inside(transcript, root_real):
            return True
        where = _placement(transcript, project_dir, cutoff, until)
        if where == "out":
            counts["out_of_window"] += 1
            return False
        if where == "none":
            counts["no_served"] += 1
            return False
        return True

    for sc in _discover_sidecars(project_dir):
        counts["sidecars"] += 1
        transcript = sc[: -len(".meta.json")] + ".jsonl"
        sidecar_inside = _inside(sc, root_real)
        side = _read_sidecar(sc) if sidecar_inside else None
        if side is None:
            if gates_the_window(transcript):
                counts["unreadable_sidecars" if sidecar_inside else "refused_paths"] += 1
            continue
        kind, declared = classify_declared(side.get("model"), families)
        archetype = _archetype(side)
        is_veto = archetype in veto_roles
        if kind == "none":
            counts["undeclared"] += 1
        elif kind == "unclassified":
            if not gates_the_window(transcript):
                continue
            counts["unclassified"] += 1
            if len(unclassified_samples) < 5:
                unclassified_samples.append(_safe_text(declared, 40))
        else:
            counts["declared"] += 1
        needs_served = kind in ("alias", "id") or is_veto
        if not needs_served:
            continue

        if not os.path.exists(transcript):
            counts["no_served"] += 1
            continue
        if not _inside(transcript, root_real):
            counts["refused_paths"] += 1
            continue
        served = _served_models(transcript, project_dir, cutoff, until, counts)
        if served is None:
            counts["out_of_window"] += 1
            continue
        if not served:
            counts["no_served"] += 1
            continue

        # ONE count per spawn that reached a comparison, whatever number of
        # predicates it fed (a declared VETO spawn feeds both).
        counts["compared_spawns"] += 1
        kinds: List[str] = []
        if kind in ("alias", "id"):
            counts["declared_compared"] += 1
            ok = [m for m in served if declaration_matches(kind, declared, m)]
            if not ok:
                kinds.append("MISMATCH")
            elif len(ok) != len(served):
                kinds.append("MIXED")
            if kind == "alias":
                bucket = alias_resolutions.setdefault(declared, {})
                for m in served:
                    shown = _safe_text(m)
                    bucket[shown] = bucket.get(shown, 0) + 1
        if is_veto:
            counts["floor_checked"] += 1
            if any(m not in veto_allowed for m in served):
                kinds.append("FLOOR_BREACH")
        if kinds:
            rel = os.path.relpath(sc, str(project_dir))
            violations.append(
                {
                    "label": _label(side, sc),
                    "rail": "workflow" if "workflows" in Path(rel).parts else "native",
                    "archetype": _safe_text(archetype),
                    "declared": declared if kind in ("alias", "id") else "",
                    "kinds": kinds,
                    "served": dict(
                        sorted((_safe_text(m), n) for m, n in served.items())
                    ),
                    "sidecar": _safe_text(rel, 300),
                }
            )

    incomplete: List[str] = []
    for key, text in (
        ("unclassified", "unclassified declaration(s)"),
        ("unreadable_sidecars", "unreadable sidecar(s)"),
        ("refused_paths", "path(s) refused (symlink or outside the corpus)"),
        ("incomplete_reads", "transcript line(s) torn, undated or unreadable"),
        ("served_unresolved", "served turn(s) without a model id"),
        (
            "chunk_terminal_unprovable",
            "message group(s) whose chunks disagree about the model and whose "
            "terminal chunk cannot be proven (a chunk without usage)",
        ),
    ):
        if counts[key]:
            incomplete.append("%d %s" % (counts[key], text))
    if floor is None:
        incomplete.append("VETO floor source unreadable (floor predicate not evaluated)")

    comparable = counts["compared_spawns"]
    if violations:
        verdict = "RED"
        by_kind: Dict[str, int] = {}
        for v in violations:
            for k in v["kinds"]:
                by_kind[k] = by_kind.get(k, 0) + 1
        reason = "%d spawn(s) violate the invariant (%s) of %d compared" % (
            len(violations),
            ", ".join("%d %s" % (n, k) for k, n in sorted(by_kind.items())),
            comparable,
        )
    elif incomplete:
        verdict = "INCONCLUSIVE"
        reason = "the check is incomplete: " + "; ".join(incomplete)
    elif comparable == 0:
        verdict = "VACUOUS"
        reason = (
            "nothing was compared: no spawn with a declared model (or VETO "
            "archetype) and a served model in the window"
        )
    else:
        verdict = "GREEN"
        reason = (
            "%d spawn(s) compared: %d declared spawn(s) served == declared, "
            "%d VETO spawn(s) served inside the floor"
            % (comparable, counts["declared_compared"], counts["floor_checked"])
        )

    return {
        "verdict": verdict,
        "reason": reason,
        "counts": counts,
        "violations": violations[:200],
        "violations_omitted": max(0, len(violations) - 200),
        "alias_resolutions": {
            a: dict(sorted(r.items())) for a, r in sorted(alias_resolutions.items())
        },
        "unclassified_samples": unclassified_samples,
        "floor": (
            {"roles": sorted(veto_roles), "allowed": sorted(veto_allowed)}
            if floor
            else None
        ),
        "prereg": ROUTING_PREREG_POINTER,
    }


def routing_invariant_safe(
    project_dir: Any,
    cutoff: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> Dict[str, Any]:
    """`routing_invariant()` that can never break the cost report AND can
    never turn its own failure into a pass: an internal error is an
    INCONCLUSIVE verdict that names the exception class."""
    try:
        return routing_invariant(project_dir, cutoff=cutoff, until=until)
    except Exception as exc:  # pragma: no cover - fail-soft envelope
        return {
            "verdict": "INCONCLUSIVE",
            "reason": "routing check failed: %s" % type(exc).__name__,
            "counts": {},
            "violations": [],
            "violations_omitted": 0,
            "alias_resolutions": {},
            "unclassified_samples": [],
            "floor": None,
            "prereg": ROUTING_PREREG_POINTER,
        }


def routing_rc(routing: Dict[str, Any]) -> int:
    """`--assert-routing` exit code for a verdict."""
    verdict = routing.get("verdict")
    if verdict == "GREEN":
        return ROUTING_RC_GREEN
    if verdict == "RED":
        return ROUTING_RC_RED
    return ROUTING_RC_NOT_PROVEN


def _routing_lines(routing: Optional[Dict[str, Any]], limit: int = 20) -> List[str]:
    """The routing verdict as report lines (ASCII), shared by every
    renderer so the CLI and the two callers' blocks cannot disagree."""
    if not routing:
        return []
    c = routing.get("counts") or {}
    out: List[str] = [
        "ROUTING INVARIANT (PLAN-186 AC-13): %s - %s"
        % (routing.get("verdict"), routing.get("reason"))
    ]
    out.append(
        "  sidecars=%d declared=%d undeclared=%d unclassified=%d | compared=%d "
        "(declared=%d floor=%d) | no_served=%d out_of_window=%d "
        "synthetic_turns_ignored=%d chunk_model_splits=%d "
        "chunk_terminal_unprovable=%d"
        % (
            c.get("sidecars", 0),
            c.get("declared", 0),
            c.get("undeclared", 0),
            c.get("unclassified", 0),
            c.get("compared_spawns", 0),
            c.get("declared_compared", 0),
            c.get("floor_checked", 0),
            c.get("no_served", 0),
            c.get("out_of_window", 0),
            c.get("synthetic_turns_ignored", 0),
            c.get("chunk_model_splits", 0),
            c.get("chunk_terminal_unprovable", 0),
        )
    )
    viol = routing.get("violations") or []
    for v in viol[:limit]:
        out.append(
            "  VIOLATION [%s] %s label=%r archetype=%s declared=%s served=%s"
            % (
                "+".join(v.get("kinds", [])),
                v.get("rail"),
                v.get("label"),
                v.get("archetype") or "-",
                v.get("declared") or "-",
                ",".join(
                    "%s x%d" % (m, n) for m, n in sorted((v.get("served") or {}).items())
                ),
            )
        )
    hidden = max(0, len(viol) - limit) + int(routing.get("violations_omitted") or 0)
    if hidden:
        out.append("  ... (+%d violation(s) omitted; --json lists them)" % hidden)
    res = routing.get("alias_resolutions") or {}
    if res:
        out.append(
            "  alias -> served (observed, informational, never judged): "
            + "; ".join(
                "%s: %s"
                % (a, ", ".join("%s x%d" % (m, n) for m, n in sorted(r.items())))
                for a, r in sorted(res.items())
            )
        )
    return out


# ---------------------------------------------------------------------------
# Programmatic API (PLAN-186 W0, AC-1b)
# ---------------------------------------------------------------------------
#
# `ceo-cost.py` and `budget-summary.py` consume THIS surface, never the
# CLI's stdout. Everything below the `transcript_rollup` line exists so
# the two callers share one root resolver, one collector and one
# renderer — a second grafia of any of them is the exact shape of the
# D1-D4 defect class (CLAUDE.md §5).

#: Env override for the transcripts corpus root. Flag > env > the shared
#: `_lib.runtime_paths` resolver. Tests MUST set this (or pass the flag):
#: nothing here may read the real ~/.claude/projects/<slug> corpus.
