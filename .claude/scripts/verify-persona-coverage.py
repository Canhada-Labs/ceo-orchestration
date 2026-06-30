#!/usr/bin/env python3
"""verify-persona-coverage.py — PLAN-088 W5.1 dual-mode persona coverage verifier.

Per AC1-AC4 closure contract (CI mode default, Live mode optional).
Mechanically verifiable per PLAN-088 §10.

Two modes resolving the audit-log circular dependency (R8):

  --fixture-path tests/fixtures/persona-scenario-suite.yaml   (CI mode)
  --from-audit-log                                            (Live mode)

CI mode reads a static fixture and validates the harness correctness.
Live mode reads audit-log emit-action stream and computes the actual
observed cell state per persona.

Persona threshold (per ADR-118 §2.1):
  vibecoder      >= 12/13  (92.3%)
  junior_dev     >= 11/13  (84.6%)
  skeptical_cto  >= 11/13  (84.6%)
  team_member    >= 11/13  (84.6%)

Stdlib-only. Python >= 3.9. NO third-party deps.

Exit codes:
  0  — all 4 personas (or selected persona via --persona) meet threshold
  1  — at least one threshold FAIL
  2  — fixture/threshold file missing or malformed
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_DEFAULT_FIXTURE = "tests/fixtures/persona-scenario-suite.yaml"
_DEFAULT_THRESHOLDS = ".claude/scripts/fixtures/persona-coverage-expected-thresholds.yaml"

# Live mode (PLAN-088 R8 / PLAN-136 F2) — audit-log default path. Producers:
#   persona_demand_opened   (PLAN-104 Wave A) — expected_persona, demand_event_type
#   persona_demand_matched  (PLAN-104 Wave A) — expected_persona, demand_event_type
# A (persona, demand_event_type) cell is observed:
#   AUTO   if at least one matched demand exists for the cell
#   SEMI   if a demand was opened but never matched
#   MANUAL otherwise (no live signal)
_DEFAULT_AUDIT_LOG = "~/.claude/projects/ceo-orchestration/audit-log.jsonl"
_LIVE_PERSONA_ACTIONS = ("persona_demand_opened", "persona_demand_matched")


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _parse_yaml_basic(text: str) -> Dict[str, Any]:
    """Minimal stdlib YAML parser for the fixture/threshold subset we need.

    Handles:
      - top-level keys with mapping or list values
      - 2-space-indented nested mappings (1 level)
      - 4-space-indented nested mappings (2 levels)
      - quoted/unquoted scalar values
      - list values like `axes: [B.1, B.2, ...]` (one-line inline)
      - block sequences "  - item"

    NOT a full YAML parser; deliberately scoped to the two fixture
    shapes consumed by this verifier.
    """
    out: Dict[str, Any] = {}
    stack: List[Tuple[int, Dict[str, Any]]] = [(0, out)]  # (indent, dict)
    inline_list_re = re.compile(r"^([A-Za-z0-9_.\-]+)\s*:\s*\[\s*(.*?)\s*\]\s*$")
    kv_re = re.compile(r"^([A-Za-z0-9_.\-]+)\s*:\s*(.*)$")

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        # Pop stack to current indent level
        while stack and stack[-1][0] > indent:
            stack.pop()
        parent_indent, parent = stack[-1]

        # block sequence "  - value"
        if stripped.startswith("- "):
            val = stripped[2:].strip()
            # parent must be a list; if it's not, convert it to list
            # find the most recent key in grandparent — too fragile;
            # for our fixture shapes we don't need block sequences
            # under a mapping nested deeper. Skip.
            continue

        # inline list
        m_list = inline_list_re.match(stripped)
        if m_list is not None:
            key = m_list.group(1)
            body = m_list.group(2).strip()
            items = [_unquote(s.strip()) for s in body.split(",") if s.strip()]
            parent[key] = items
            continue

        # plain key:value
        m_kv = kv_re.match(stripped)
        if m_kv is None:
            continue
        key = m_kv.group(1)
        val = m_kv.group(2).strip()
        if not val:
            # mapping continues with deeper indent
            new_dict: Dict[str, Any] = {}
            parent[key] = new_dict
            stack.append((indent + 2, new_dict))
        else:
            parent[key] = _coerce(val)
    return out


def _unquote(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def _coerce(s: str) -> Any:
    # Strip trailing inline comment (e.g. "11  # 84.6% floor")
    s = re.sub(r"\s+#.*$", "", s).strip()
    s_u = _unquote(s)
    # integer
    if re.match(r"^-?\d+$", s_u):
        try:
            return int(s_u)
        except ValueError:
            return s_u
    # float
    if re.match(r"^-?\d+\.\d+$", s_u):
        try:
            return float(s_u)
        except ValueError:
            return s_u
    # bool
    low = s_u.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    return s_u


def _load_fixture(fixture_path: Path) -> Optional[Dict[str, Any]]:
    if not fixture_path.exists():
        _err("FAIL: fixture not found: %s" % fixture_path)
        return None
    try:
        text = fixture_path.read_text(encoding="utf-8")
    except OSError as exc:
        _err("FAIL: cannot read fixture %s: %s" % (fixture_path, exc))
        return None
    parsed = _parse_yaml_basic(text)
    if "personas" not in parsed or "axes" not in parsed:
        _err("FAIL: fixture missing required keys (axes, personas)")
        return None
    return parsed


def _load_thresholds(thresholds_path: Path) -> Optional[Dict[str, Any]]:
    if not thresholds_path.exists():
        _err("FAIL: thresholds not found: %s" % thresholds_path)
        return None
    try:
        text = thresholds_path.read_text(encoding="utf-8")
    except OSError as exc:
        _err("FAIL: cannot read thresholds %s: %s" % (thresholds_path, exc))
        return None
    parsed = _parse_yaml_basic(text)
    if "thresholds" not in parsed:
        _err("FAIL: thresholds file missing top-level 'thresholds' key")
        return None
    return parsed


def _count_auto_semi(persona_cells: Dict[str, str]) -> Tuple[int, int]:
    """Return (auto_count, semi_count). MANUAL not counted."""
    auto = sum(1 for v in persona_cells.values() if str(v).upper() == "AUTO")
    semi = sum(1 for v in persona_cells.values() if str(v).upper() == "SEMI")
    return auto, semi


def verify_persona(
    fixture: Dict[str, Any],
    thresholds: Dict[str, Any],
    persona: str,
) -> Tuple[bool, str]:
    """Verify a single persona meets threshold. Returns (pass, summary)."""
    personas_map = fixture.get("personas", {})
    if persona not in personas_map:
        return False, "persona %r not in fixture" % persona
    cells = personas_map[persona]
    if not isinstance(cells, dict):
        return False, "persona %r cells not a mapping" % persona

    auto, semi = _count_auto_semi(cells)
    total = auto + semi
    total_axes = len(cells)

    thr_map = thresholds.get("thresholds", {})
    persona_thr = thr_map.get(persona, {})
    min_auto_semi = int(persona_thr.get("min_auto_semi", 0))
    target_pct = persona_thr.get("target_pct", 0.0)

    passed = total >= min_auto_semi
    summary = (
        "%s: AUTO=%d SEMI=%d total=%d/%d (target>=%d / %.1f%%) -> %s"
        % (persona, auto, semi, total, total_axes, min_auto_semi,
           target_pct, "PASS" if passed else "FAIL")
    )
    return passed, summary


def verify_all(
    fixture_path: Path,
    thresholds_path: Path,
    selected_persona: Optional[str] = None,
) -> int:
    fixture = _load_fixture(fixture_path)
    if fixture is None:
        return 2
    thresholds = _load_thresholds(thresholds_path)
    if thresholds is None:
        return 2

    personas_map = fixture.get("personas", {})
    if not isinstance(personas_map, dict):
        _err("FAIL: fixture 'personas' is not a mapping")
        return 2
    personas: List[str] = sorted(personas_map.keys())
    if selected_persona is not None:
        if selected_persona not in personas:
            _err("FAIL: --persona=%s not in fixture (have: %s)"
                 % (selected_persona, personas))
            return 2
        personas = [selected_persona]

    failures: List[str] = []
    for p in personas:
        passed, summary = verify_persona(fixture, thresholds, p)
        print(summary)
        if not passed:
            failures.append(p)

    if failures:
        _err("verify-persona-coverage.py: FAIL (%d/%d persona(s) below threshold)"
             % (len(failures), len(personas)))
        return 1
    print("verify-persona-coverage.py: PASS (all %d persona(s) meet threshold)"
          % len(personas))
    return 0


def _canonical_axes_and_personas(
    fixture_path: Path,
    thresholds: Optional[Dict[str, Any]],
) -> Tuple[List[str], List[str]]:
    """Resolve the canonical (axes, personas) the live matrix MUST cover.

    The 4-persona / N-axis contract is defined by the fixture (``axes``)
    and the thresholds file (``thresholds`` keys). Live mode seeds its
    matrix from these so that personas/cells NEVER observed in the
    audit-log are still scored (as all-MANUAL) instead of silently
    dropped — otherwise a partial log would FALSE-PASS by omission.

    Either source may be missing/malformed; we degrade gracefully and
    return whatever canonical names we can recover (possibly empty).
    """
    canonical_axes: List[str] = []
    fixture = _load_fixture(fixture_path)
    if fixture is not None:
        axes_val = fixture.get("axes")
        if isinstance(axes_val, list) and axes_val:
            canonical_axes = [str(a) for a in axes_val]
        else:
            # The fixture's `axes:` may be a YAML block-sequence the basic
            # parser does not surface as a list; derive the canonical axis set
            # from the union of persona-row cell keys (the same source
            # verify_persona counts), preserving first-seen order. Without this
            # the live matrix would seed zero axes and a partial log could
            # FALSE-PASS by omission (Codex R1/R2 P1).
            seen_axes: Dict[str, None] = {}
            personas_map = fixture.get("personas", {})
            if isinstance(personas_map, dict):
                for cells in personas_map.values():
                    if isinstance(cells, dict):
                        for axis in cells.keys():
                            seen_axes.setdefault(str(axis), None)
            canonical_axes = list(seen_axes.keys())

    canonical_personas: List[str] = []
    if thresholds is not None:
        thr_map = thresholds.get("thresholds", {})
        if isinstance(thr_map, dict):
            canonical_personas = [str(p) for p in thr_map.keys()]

    return canonical_axes, canonical_personas


def _aggregate_live_observed_state(
    audit_log_path: Path,
    canonical_axes: Optional[List[str]] = None,
    canonical_personas: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Read the audit-log and aggregate persona demand events into the
    SAME observed-state shape that ``verify_all`` / ``verify_persona``
    consume: ``{"axes": [...], "personas": {persona: {cell: STATE}}}``.

    Returns None when the audit-log is missing or carries no persona
    demand events (caller falls back to fixture mode).

    Conservative parsing: each line is a standalone JSON object; a
    malformed line is skipped (the audit-log is append-only JSONL but a
    truncated tail write must not crash the verifier — fail-open).

    ``canonical_axes`` / ``canonical_personas`` seed the matrix so that
    cells/personas absent from the live stream are still scored as
    MANUAL (never dropped). Without seeding, a log covering 1 persona /
    12 cells would FALSE-PASS the 4-persona contract by omission.
    """
    if not audit_log_path.exists():
        return None
    try:
        text = audit_log_path.read_text(encoding="utf-8")
    except OSError as exc:
        _err("WARN: cannot read audit-log %s: %s" % (audit_log_path, exc))
        return None

    # (persona, cell) -> {"opened": bool, "matched": bool}
    observed: Dict[str, Dict[str, Dict[str, bool]]] = {}
    cells_seen: Dict[str, None] = {}  # ordered set of cell keys
    any_event = False

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(evt, dict):
            continue
        action = evt.get("action")
        if action not in _LIVE_PERSONA_ACTIONS:
            continue
        persona = str(evt.get("expected_persona", "")).strip()
        cell = str(evt.get("demand_event_type", "")).strip()
        if not persona or not cell:
            continue
        any_event = True
        cells_seen.setdefault(cell, None)
        per_persona = observed.setdefault(persona, {})
        cell_state = per_persona.setdefault(cell, {"opened": False, "matched": False})
        if action == "persona_demand_opened":
            cell_state["opened"] = True
        elif action == "persona_demand_matched":
            cell_state["matched"] = True

    if not any_event:
        return None

    # Seed the canonical matrix: every canonical axis is a column and
    # every canonical persona is a row, in addition to anything observed
    # in the log. Absent (persona, axis) cells fill as MANUAL below.
    axes_seed = list(canonical_axes) if canonical_axes else []
    axes: List[str] = list(axes_seed)
    for cell in cells_seen.keys():
        if cell not in axes:
            axes.append(cell)

    persona_seed = list(canonical_personas) if canonical_personas else []
    persona_names: List[str] = list(persona_seed)
    for persona in observed.keys():
        if persona not in persona_names:
            persona_names.append(persona)

    personas_out: Dict[str, Dict[str, str]] = {}
    for persona in persona_names:
        cells = observed.get(persona, {})
        row: Dict[str, str] = {}
        for cell in axes:
            st = cells.get(cell)
            if st is None:
                row[cell] = "MANUAL"
            elif st["matched"]:
                row[cell] = "AUTO"
            elif st["opened"]:
                row[cell] = "SEMI"
            else:
                row[cell] = "MANUAL"
        personas_out[persona] = row

    return {"axes": axes, "personas": personas_out}


def verify_all_live(
    audit_log_path: Path,
    thresholds_path: Path,
    fixture_path: Path,
    selected_persona: Optional[str] = None,
) -> int:
    """Live mode entry point (PLAN-136 F2). Aggregate observed persona
    cell-state from the audit-log and run the existing threshold
    verification over the live data. Falls back gracefully to fixture
    mode (with a warning) when the audit-log is absent or carries no
    persona demand events — never crashes on missing live data.
    """
    thresholds = _load_thresholds(thresholds_path)
    if thresholds is None:
        return 2

    # Seed the live matrix from the canonical axes (fixture) + personas
    # (thresholds) so incomplete coverage is scored, not dropped.
    canonical_axes, canonical_personas = _canonical_axes_and_personas(
        fixture_path, thresholds
    )
    observed = _aggregate_live_observed_state(
        audit_log_path,
        canonical_axes=canonical_axes,
        canonical_personas=canonical_personas,
    )
    if observed is None:
        _err(
            "WARN: no live persona demand events in audit-log (%s); "
            "falling back to fixture mode" % audit_log_path
        )
        return verify_all(
            fixture_path, thresholds_path, selected_persona=selected_persona
        )

    personas_map = observed.get("personas", {})
    if not isinstance(personas_map, dict) or not personas_map:
        _err("WARN: live aggregation produced no personas; falling back to fixture")
        return verify_all(
            fixture_path, thresholds_path, selected_persona=selected_persona
        )

    thr_map = thresholds.get("thresholds", {})
    canonical_persona_set = set(thr_map.keys()) if isinstance(thr_map, dict) else set()
    personas: List[str] = sorted(personas_map.keys())
    if selected_persona is not None:
        if selected_persona not in personas:
            if selected_persona in canonical_persona_set:
                # Canonical persona never observed live (and canonical
                # seeding above did not cover it) — score it as an
                # all-MANUAL row so it FAILS the threshold (exit 1):
                # a coverage gap, NOT a config error.
                personas_map[selected_persona] = {
                    axis: "MANUAL" for axis in observed.get("axes", [])
                }
            else:
                # Genuinely unknown persona (not in the threshold
                # contract): this is a config error.
                _err("FAIL: --persona=%s not observed in live audit-log "
                     "and not in threshold contract (have: %s)"
                     % (selected_persona, personas))
                return 2
        personas = [selected_persona]

    print("verify-persona-coverage.py: LIVE mode (audit-log=%s)" % audit_log_path)
    failures: List[str] = []
    for p in personas:
        passed, summary = verify_persona(observed, thresholds, p)
        print(summary)
        if not passed:
            failures.append(p)

    if failures:
        _err("verify-persona-coverage.py: FAIL (%d/%d persona(s) below threshold)"
             % (len(failures), len(personas)))
        return 1
    print("verify-persona-coverage.py: PASS (all %d persona(s) meet threshold)"
          % len(personas))
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "PLAN-088 W5.1 persona coverage verifier. Dual-mode: "
            "CI fixture (default) + Live audit-log."
        )
    )
    p.add_argument("--fixture-path", default=_DEFAULT_FIXTURE,
                   help="Path to persona scenario fixture (CI mode default)")
    p.add_argument("--thresholds-path", default=_DEFAULT_THRESHOLDS,
                   help="Path to expected thresholds YAML")
    p.add_argument("--persona", default=None,
                   help="Verify only one persona "
                        "(vibecoder/junior_dev/skeptical_cto/team_member)")
    p.add_argument("--from-audit-log", action="store_true",
                   help="Live mode: read audit-log persona demand stream "
                        "to compute observed cell state, then verify "
                        "thresholds over the live data (falls back to "
                        "fixture mode if no live events).")
    p.add_argument("--audit-log-path", default=_DEFAULT_AUDIT_LOG,
                   help="Path to audit-log.jsonl for live mode "
                        "(default: %s)" % _DEFAULT_AUDIT_LOG)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    if args.from_audit_log:
        audit_log_path = Path(os.path.expanduser(args.audit_log_path))
        return verify_all_live(
            audit_log_path,
            Path(args.thresholds_path),
            Path(args.fixture_path),
            selected_persona=args.persona,
        )
    return verify_all(
        Path(args.fixture_path),
        Path(args.thresholds_path),
        selected_persona=args.persona,
    )


if __name__ == "__main__":
    sys.exit(main())
