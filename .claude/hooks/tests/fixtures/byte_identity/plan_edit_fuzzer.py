"""Deterministic fuzzer for plan-edit byte-identity — PLAN-014 A.5.

Emits ≥500 synthetic Edit tool-call events with pre-resolved
``_derived_plan`` blocks, distributed across:

    non-plan files (scope-guard pass)     100
    plan, non-status changes               80
    legal transitions                      60
    illegal transitions                    60
    missing required fields                80
    corrupt frontmatter (derived fails)    60
    edge cases (unicode, large, empty)     60
                                          ----
                                          500

Each event is a dict ready to feed to the harness — ``_derived_plan``
is pre-computed so the POLICY path reaches a deterministic decision
regardless of filesystem state, and the Python path (via the harness's
primitive re-invocation) reaches the same decision.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List

_LEGAL = ["draft", "reviewed", "executing", "done", "abandoned", "refused"]
_ILLEGAL_VALUES = ["finished", "started", "in-progress", "closed", "TODO",
                   "draft ", " reviewed", "foo", "null", "", "EXECUTING"]
_PATHS_PLAN = [
    ".claude/plans/PLAN-001-evolution.md",
    ".claude/plans/PLAN-099-test.md",
    ".claude/plans/PLAN-100-feature.md",
    ".claude/plans/PLAN-200-sample.md",
    ".claude/plans/PLAN-314-pi-plan.md",
    ".claude/plans/PLAN-777-lucky.md",
]
_PATHS_NON_PLAN = [
    "src/index.ts", "src/app.py", "README.md", "docs/guide.md",
    ".claude/skills/core/testing-strategy/SKILL.md", "CHANGELOG.md",
    ".claude/plans/PLAN-SCHEMA.md",   # plan dir, but not a NNN-slug file
    ".claude/plans/README.md",
    ".claude/plans/archive/old.md",   # archive subdir
    ".github/CODEOWNERS",
    "package.json", "tests/test_x.py",
]


def _plan_id_from_path(path: str) -> str:
    # Matches _lib/policy_preprocessors._PLAN_ID_RE
    import re
    m = re.search(r"(PLAN-\d{3})-[a-z0-9-]+\.md$", path)
    return m.group(1) if m else ""


def _default_derived() -> Dict[str, Any]:
    return {
        "is_plan_file": False,
        "plan_id": "",
        "old_status": "",
        "new_status": "",
        "status_changed": False,
        "transition_legal": True,
        "new_status_legal": True,
        "reviewed_at_present": False,
        "completed_at_present": False,
        "related_commits_nonempty": False,
        "abandonment_reason_present": False,
        # Session 75 F7 — refused_adr field tracking. When status=refused,
        # the YAML policy + Python check_plan_edit both require these to
        # avoid byte-identity drift.
        "refused_adr_present": False,
        "refused_adr_well_formed": False,
        # Session 76 audit-v3 (DIM-11) — ADR-092 enforcement field tracking.
        # When transitioning to refused, refused_at is required.
        # When reopening (done -> executing), reopen_via + reopen_trigger
        # + body section `## Reopen criteria` are all required.
        "refused_at_present": False,
        "reopen_via_present": False,
        "reopen_via_well_formed": False,
        "reopen_trigger_present": False,
        "reopen_criteria_section_present": False,
        "transition_reason_key": "",
    }


_ALLOWED_TRANSITIONS = {
    "draft": {"reviewed", "abandoned", "refused"},
    "reviewed": {"executing", "abandoned", "refused"},
    "executing": {"done", "abandoned", "refused"},
    # done is reopen-able when plan body declares `reopen_via:` ADR
    # reference (audit-v2 ADR-092 honest-deferral framework). Wave C-bis
    # alignment with check_plan_edit.py + _lib/policy_preprocessors.py.
    "done": {"executing"},
    "abandoned": set(),  # terminal
    "refused": set(),  # terminal — must cite refused_adr
}


def _event(file_path: str, derived: Dict[str, Any],
           old_string: str = "", new_string: str = "",
           replace_all: bool = False) -> Dict[str, Any]:
    ev = {
        "tool": "Edit",
        "tool_input": {"file_path": file_path},
        "_derived_plan": derived,
    }
    if old_string:
        ev["tool_input"]["old_string"] = old_string
    if new_string:
        ev["tool_input"]["new_string"] = new_string
    if replace_all:
        ev["tool_input"]["replace_all"] = True
    return ev


# ---------------------------------------------------------------------------
# Buckets
# ---------------------------------------------------------------------------


def _bucket_non_plan(rng: random.Random, count: int) -> List[Dict[str, Any]]:
    out = []
    for _ in range(count):
        out.append(_event(rng.choice(_PATHS_NON_PLAN), _default_derived()))
    return out


def _bucket_plan_no_status_change(rng: random.Random, count: int) -> List[Dict[str, Any]]:
    out = []
    for _ in range(count):
        p = rng.choice(_PATHS_PLAN)
        d = _default_derived()
        d["is_plan_file"] = True
        d["plan_id"] = _plan_id_from_path(p)
        d["old_status"] = rng.choice(_LEGAL)
        d["new_status"] = d["old_status"]
        d["status_changed"] = False
        out.append(_event(p, d))
    return out


def _bucket_legal_transitions(rng: random.Random, count: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    legal_pairs = [(src, dst) for src, dsts in _ALLOWED_TRANSITIONS.items()
                   for dst in dsts]
    for _ in range(count):
        p = rng.choice(_PATHS_PLAN)
        src, dst = rng.choice(legal_pairs)
        d = _default_derived()
        d["is_plan_file"] = True
        d["plan_id"] = _plan_id_from_path(p)
        d["old_status"] = src
        d["new_status"] = dst
        d["status_changed"] = True
        d["transition_legal"] = True
        d["new_status_legal"] = True
        # Fill in required fields to make it ALLOW
        if dst == "reviewed":
            d["reviewed_at_present"] = True
        elif dst == "done":
            d["completed_at_present"] = True
            d["related_commits_nonempty"] = True
        elif dst == "abandoned":
            d["abandonment_reason_present"] = True
        elif dst == "refused":
            # Session 75 F7 — refused needs cited refused_adr (well-formed).
            # Session 76 audit-v3 — refused also needs refused_at per ADR-092.
            d["refused_adr_present"] = True
            d["refused_adr_well_formed"] = True
            d["refused_at_present"] = True
        elif src == "done" and dst == "executing":
            # Session 76 audit-v3 — `done -> executing` reopen needs the
            # full ADR-092 set: reopen_via (well-formed) + reopen_trigger
            # + body section `## Reopen criteria`.
            d["reopen_via_present"] = True
            d["reopen_via_well_formed"] = True
            d["reopen_trigger_present"] = True
            d["reopen_criteria_section_present"] = True
        out.append(_event(p, d))
    return out


def _bucket_illegal_transitions(rng: random.Random, count: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    illegal_pairs = []
    for src in _LEGAL:
        allowed = _ALLOWED_TRANSITIONS.get(src, set()) | {src}
        for dst in _LEGAL:
            if dst not in allowed:
                illegal_pairs.append((src, dst))
    for _ in range(count):
        p = rng.choice(_PATHS_PLAN)
        src, dst = rng.choice(illegal_pairs)
        d = _default_derived()
        d["is_plan_file"] = True
        d["plan_id"] = _plan_id_from_path(p)
        d["old_status"] = src
        d["new_status"] = dst
        d["status_changed"] = True
        d["transition_legal"] = False
        d["new_status_legal"] = True
        d["transition_reason_key"] = "illegal_transition"
        out.append(_event(p, d))
    return out


def _bucket_missing_required(rng: random.Random, count: int) -> List[Dict[str, Any]]:
    """→reviewed without reviewed_at / →done without completed_at /
    →done without related_commits / →abandoned without reason section."""
    out = []
    for _ in range(count):
        p = rng.choice(_PATHS_PLAN)
        which = rng.randint(0, 5)  # Session 75 F7: extended to 6 cases
        d = _default_derived()
        d["is_plan_file"] = True
        d["plan_id"] = _plan_id_from_path(p)
        d["status_changed"] = True
        d["transition_legal"] = True
        d["new_status_legal"] = True
        if which == 0:
            d["old_status"] = "draft"
            d["new_status"] = "reviewed"
            d["reviewed_at_present"] = False
            d["transition_reason_key"] = "missing_reviewed_at"
        elif which == 1:
            d["old_status"] = "executing"
            d["new_status"] = "done"
            d["completed_at_present"] = False
            d["related_commits_nonempty"] = False
            d["transition_reason_key"] = "missing_completed_at"
        elif which == 2:
            d["old_status"] = "executing"
            d["new_status"] = "done"
            d["completed_at_present"] = True
            d["related_commits_nonempty"] = False
            d["transition_reason_key"] = "missing_related_commits"
        elif which == 3:
            d["old_status"] = rng.choice(["draft", "reviewed", "executing"])
            d["new_status"] = "abandoned"
            d["abandonment_reason_present"] = False
            d["transition_reason_key"] = "missing_abandonment_reason"
        elif which == 4:
            # Session 75 F7 — refused without refused_adr field.
            d["old_status"] = rng.choice(["draft", "reviewed", "executing"])
            d["new_status"] = "refused"
            d["refused_adr_present"] = False
            d["refused_adr_well_formed"] = False
            d["transition_reason_key"] = "missing_refused_adr"
        else:
            # Session 75 F7 — refused with malformed refused_adr.
            d["old_status"] = rng.choice(["draft", "reviewed", "executing"])
            d["new_status"] = "refused"
            d["refused_adr_present"] = True
            d["refused_adr_well_formed"] = False
            d["transition_reason_key"] = "malformed_refused_adr"
        out.append(_event(p, d))
    return out


def _bucket_illegal_status_value(rng: random.Random, count: int) -> List[Dict[str, Any]]:
    """New status is not a legal enum value."""
    out = []
    for _ in range(count):
        p = rng.choice(_PATHS_PLAN)
        d = _default_derived()
        d["is_plan_file"] = True
        d["plan_id"] = _plan_id_from_path(p)
        d["old_status"] = rng.choice(_LEGAL)
        new = rng.choice(_ILLEGAL_VALUES)
        d["new_status"] = new
        d["status_changed"] = d["old_status"] != new
        d["new_status_legal"] = False
        d["transition_legal"] = False
        d["transition_reason_key"] = "illegal_status_value"
        if not d["status_changed"]:
            # Force-change by swapping old_status so status_changed holds
            d["old_status"] = "draft" if new != "draft" else "reviewed"
            d["status_changed"] = True
        out.append(_event(p, d))
    return out


def _bucket_edge(rng: random.Random, count: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for _ in range(count):
        kind = rng.randint(0, 5)
        d = _default_derived()
        if kind == 0:
            # Unicode plan identifier — should still match pattern / fail
            out.append(_event(".claude/plans/PLAN-999-café.md", d))
        elif kind == 1:
            # Large file_path
            out.append(_event("a/" * 300 + "README.md", d))
        elif kind == 2:
            # Empty file_path
            out.append(_event("", d))
        elif kind == 3:
            # Wrong extension
            out.append(_event(".claude/plans/PLAN-001-x.txt", d))
        elif kind == 4:
            # Plan with corrupt old_status (non-legal)
            p = rng.choice(_PATHS_PLAN)
            d["is_plan_file"] = True
            d["plan_id"] = _plan_id_from_path(p)
            d["old_status"] = "garbled-old"
            d["new_status"] = "reviewed"
            d["status_changed"] = True
            d["transition_legal"] = True  # preprocessor allows when old corrupt
            d["new_status_legal"] = True
            d["reviewed_at_present"] = True
            out.append(_event(p, d))
        else:
            # Plan with no status change (just body edit)
            p = rng.choice(_PATHS_PLAN)
            d["is_plan_file"] = True
            d["plan_id"] = _plan_id_from_path(p)
            d["old_status"] = "executing"
            d["new_status"] = "executing"
            d["status_changed"] = False
            out.append(_event(p, d))
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate(n: int = 500, seed: int = 42) -> List[Dict[str, Any]]:
    """Return ``n`` Edit tool-call events with pre-resolved derived state.

    Default distribution (n=500):

        non_plan                  100
        plan_no_status_change      80
        legal_transitions          60
        illegal_transitions        60
        missing_required           80
        illegal_status_value       60
        edge                       60
                                  ----
                                  500
    """
    rng = random.Random(seed)
    buckets = [
        _bucket_non_plan(rng, 100),
        _bucket_plan_no_status_change(rng, 80),
        _bucket_legal_transitions(rng, 60),
        _bucket_illegal_transitions(rng, 60),
        _bucket_missing_required(rng, 80),
        _bucket_illegal_status_value(rng, 60),
        _bucket_edge(rng, 60),
    ]
    flat: List[Dict[str, Any]] = []
    for b in buckets:
        flat.extend(b)
    # Pad deterministically if asked for more.
    while len(flat) < n:
        flat.append(_event(rng.choice(_PATHS_NON_PLAN), _default_derived()))
    return flat[:n]


__all__ = ["generate"]
