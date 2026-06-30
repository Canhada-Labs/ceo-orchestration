"""STAGED — PLAN-048 Phase 2 — escalation_signals library.

**This file MUST NOT land at `.claude/hooks/_lib/escalation_signals.py`
without an Owner-signed canonical-edit sentinel.** `_lib/*.py` is
canonical-guarded (see `.claude/hooks/check_canonical_edit.py` line 112
in the `_CANONICAL_GUARDS` list).

Path on intended promote:
    .claude/hooks/_lib/escalation_signals.py

Sentinel scope block to include at promote ceremony::

    Scope: .claude/hooks/_lib/escalation_signals.py
    Round: NN
    Approved-By: @Canhada-Labs <fpr>

---

**Rationale for library extraction** — the detection logic currently
lives in `.claude/scripts/ceo-escalation-detector.py` (non-canonical,
standalone). Moving the 6 detectors into `_lib/` enables:

1. Reuse from a future Stop / SessionEnd hook (runtime re-dispatch
   mechanism; plan §Phase 2 lines 118-125).
2. Cleaner integration with `audit_emit.emit_escalation_*` emitters
   (requires `_KNOWN_ACTIONS` registry extension — see
   ``audit_emit_action_registry_patch.md`` in this directory).
3. Unified import path across CLI + hook + test surface.

Until the Owner ceremony lands, the standalone detector remains the
authoritative implementation. This staged copy MUST stay
bit-equivalent with the standalone module's detector functions.

---

**Promote checklist (Owner-side, at sentinel ceremony):**

- [ ] Diff-verify this file against the 6 `detect_*` functions in
      `.claude/scripts/ceo-escalation-detector.py` — they must be
      byte-equivalent modulo import paths.
- [ ] Move file to `.claude/hooks/_lib/escalation_signals.py`.
- [ ] Amend `.claude/hooks/_lib/__init__.py` to export the module (if
      the project convention requires explicit re-export).
- [ ] Patch `.claude/scripts/ceo-escalation-detector.py` to import
      from `_lib.escalation_signals` instead of inlining (optional
      follow-up; standalone must keep working for offline adopters).
- [ ] Run kernel batch (Owner CEO_KERNEL_OVERRIDE) registering
      `escalation_*` actions in `_lib/audit_emit.py::_KNOWN_ACTIONS`
      (see ``audit_emit_action_registry_patch.md``).
- [ ] Full test suite green; add `.claude/hooks/tests/
      test_escalation_signals.py` (mirror of the 55 script tests).

---
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# E1-F8 COVERAGE-GAP NOTE (PLAN-134 W0): this set covers only 2 of the
# 5 VETO_FLOOR_ROLES — the 3 Wave-1c roles (incident-commander,
# identity-trust-architect, threat-detection-engineer) are NOT watched
# by detect_veto_non_opus. Acknowledged drift; widening coverage is a
# SEPARATE Owner decision and is deliberately NOT folded into the
# ADR-149 model-allowlist batch.
_VETO_ROLES = frozenset({"code-reviewer", "security-engineer"})
# ADR-149: floor-tier model FAMILIES (top tier). Same allowlist
# semantics as agent_frontmatter.VETO_FLOOR_ALLOWED, expressed as
# prefixes because audit events can carry suffixed IDs (e.g. "[1m]").
_FLOOR_TIER_PREFIXES = ("claude-opus-", "claude-fable-")
_OPUS_PREFIX = _FLOOR_TIER_PREFIXES[0]  # legacy name, kept for back-compat
_GATE_1_FILES = ("CLAUDE.md", "PROTOCOL.md")
_SHORTCUT_PHRASES = (
    "i'll just",
    "quick fix",
    "skip debate",
    "trust me",
    "let me just",
    "one-liner",
    "no need to test",
)
_L3_PLUS_LEVELS = frozenset({"L3", "L3+", "L4", "L4+", "L5"})


def _event_ts(r: Dict[str, Any]) -> str:
    return str(r.get("ts") or r.get("timestamp") or "")


def _extract_plan_level(plan_md_path: Path) -> Optional[str]:
    if not plan_md_path.is_file():
        return None
    try:
        with plan_md_path.open("r", encoding="utf-8") as fh:
            in_front = False
            for ln in fh:
                if ln.strip() == "---":
                    if not in_front:
                        in_front = True
                        continue
                    break
                if in_front:
                    m = re.match(r"^\s*level\s*:\s*(.+?)\s*$", ln)
                    if m:
                        return m.group(1).strip().strip("'\"")
    except OSError:
        return None
    return None


def _lookup_plan_level(plan_id: str, plans_dir: Path) -> Optional[str]:
    if not plans_dir.is_dir():
        return None
    for candidate in sorted(plans_dir.glob(f"{plan_id}-*.md")):
        lvl = _extract_plan_level(candidate)
        if lvl:
            return lvl
    return None


def _is_floor_tier(model: str) -> bool:
    """ADR-149: True when ``model`` belongs to a floor-tier family."""
    return bool(model) and model.lower().startswith(_FLOOR_TIER_PREFIXES)


# Legacy alias — existing callers/tests import _is_opus by name.
_is_opus = _is_floor_tier


def detect_gate_skip(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Signal 1 — Gate 1-3 reading skipped."""
    if not events:
        return []
    head = events[:15]
    triggered_work = False
    read_protocol = False
    first_work_ts = ""
    for e in head:
        act = e.get("action") or ""
        if act in {"agent_spawn", "plan_transition", "canonical_edit_blocked"}:
            triggered_work = True
            if not first_work_ts:
                first_work_ts = _event_ts(e)
        files_hint = e.get("files_read") or e.get("read_paths") or []
        if isinstance(files_hint, str):
            files_hint = [files_hint]
        for fh in files_hint:
            for gf in _GATE_1_FILES:
                if gf in str(fh):
                    read_protocol = True
                    break
    if triggered_work and not read_protocol:
        return [
            {
                "signal": "gate_skip",
                "severity": "high",
                "ts": first_work_ts,
                "details": {
                    "hint": (
                        "first 15 events show work (spawn/plan_transition) "
                        "but no Gate-1 read of CLAUDE.md/PROTOCOL.md captured"
                    ),
                    "head_actions": [e.get("action") for e in head],
                },
            }
        ]
    return []


def detect_canonical_edit_block(
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Signal 2 — canonical-edit sentinel violations."""
    out: List[Dict[str, Any]] = []
    for e in events:
        act = e.get("action") or ""
        rk = e.get("response_kind") or ""
        if (
            act in {"canonical_edit_blocked", "check_canonical_edit_block"}
            or rk == "block_canonical_edit"
        ):
            out.append(
                {
                    "signal": "canonical_edit_block",
                    "severity": "high",
                    "ts": _event_ts(e),
                    "details": {
                        "action": act,
                        "response_kind": rk,
                        "path": e.get("path") or e.get("tool_file_path"),
                    },
                }
            )
    return out


def detect_debate_skip_l3(
    events: List[Dict[str, Any]],
    plans_dir: Path,
) -> List[Dict[str, Any]]:
    """Signal 3 — L3+ plan dispatched execution spawns before any debate."""
    if not events:
        return []
    debate_by_plan: Dict[str, str] = {}
    first_exec_by_plan: Dict[str, str] = {}
    for e in events:
        pid = (e.get("plan_id") or "").strip()
        if not pid:
            continue
        act = e.get("action") or ""
        ts = _event_ts(e)
        if act == "debate_event" and pid not in debate_by_plan:
            debate_by_plan[pid] = ts
        if act in {"agent_spawn", "plan_transition"} and pid not in first_exec_by_plan:
            first_exec_by_plan[pid] = ts
    out: List[Dict[str, Any]] = []
    for pid, exec_ts in first_exec_by_plan.items():
        level = _lookup_plan_level(pid, plans_dir)
        if level not in _L3_PLUS_LEVELS:
            continue
        debate_ts = debate_by_plan.get(pid)
        if not debate_ts or debate_ts > exec_ts:
            out.append(
                {
                    "signal": "debate_skip_l3",
                    "severity": "high",
                    "ts": exec_ts,
                    "details": {
                        "plan_id": pid,
                        "level": level,
                        "first_exec_ts": exec_ts,
                        "debate_ts": debate_ts,
                    },
                }
            )
    return out


def detect_strike_counter(
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Signal 4 — 3-strike counter trigger."""
    count = 0
    out: List[Dict[str, Any]] = []
    for e in events:
        if (e.get("action") or "") == "strike_recorded":
            count += 1
            if count >= 3:
                out.append(
                    {
                        "signal": "strike_counter",
                        "severity": "high",
                        "ts": _event_ts(e),
                        "details": {
                            "cumulative_strikes": count,
                            "agent": e.get("agent") or e.get("subagent_type"),
                        },
                    }
                )
                break
    return out


def detect_veto_non_opus(
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Signal 5 — VETO-role spawn with non-Opus model."""
    out: List[Dict[str, Any]] = []
    for e in events:
        if (e.get("action") or "") != "agent_spawn":
            continue
        role = (
            e.get("subagent_type")
            or e.get("agent_type")
            or e.get("agent")
            or ""
        )
        if role not in _VETO_ROLES:
            continue
        model = e.get("model") or e.get("model_id") or ""
        if not _is_floor_tier(model):
            out.append(
                {
                    "signal": "veto_non_opus",
                    "severity": "high",
                    "ts": _event_ts(e),
                    "details": {
                        "role": role,
                        "model": model or "<unset>",
                        "expected_prefix": "|".join(_FLOOR_TIER_PREFIXES),
                    },
                }
            )
    return out


def detect_shortcut_language(
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Signal 6 — advisory pattern match on prompt/output text."""
    out: List[Dict[str, Any]] = []
    for e in events:
        act = e.get("action") or ""
        if act not in {"prompt_submitted", "output_scan_finding"}:
            continue
        blob = " ".join(
            str(e.get(k) or "")
            for k in ("preview", "text_preview", "prompt_preview", "content_preview")
        ).lower()
        if not blob:
            continue
        hits = [p for p in _SHORTCUT_PHRASES if p in blob]
        if hits:
            out.append(
                {
                    "signal": "shortcut_language",
                    "severity": "low",
                    "ts": _event_ts(e),
                    "details": {
                        "phrases": hits,
                        "source_action": act,
                    },
                }
            )
    return out


DETECTORS = (
    detect_gate_skip,
    detect_canonical_edit_block,
    detect_debate_skip_l3,
    detect_strike_counter,
    detect_veto_non_opus,
    detect_shortcut_language,
)
