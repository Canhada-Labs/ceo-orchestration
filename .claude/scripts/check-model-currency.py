#!/usr/bin/env python3
"""check-model-currency.py — PLAN-176 W0a: OFFLINE model-currency detector.

Answers ONE question without touching the network: *has a model identifier
appeared on some surface of this repository that the Owner-signed authority
does not cover?*

Authorities (read, never written):
  A1  ``.claude/adr/ADR-149-model-id-allowlist.md`` — the two machine-parseable
      blocks ``VETO_FLOOR_ALLOWED`` and ``AVAILABLE_MODELS_WORKING_SET``.
  A2  ``.claude/hooks/_lib/codex_cli_shape.py`` — ``_VALID_MODELS``, the
      reviewer-model name allowlist for the OpenAI family.

Surfaces (compared against the authority of their own vendor family):
  S1  ``.claude/scripts/cost-table.yaml``        — the ``models:`` keys.
  S2  ``.claude/scripts/model-deprecations.json``— every ``replacement``.
  S3  ``.claude/settings.json``                  — ``model``,
      ``availableModels`` (order is normative per ADR-149 A1.1) and
      ``fallbackModel``.

Every divergence is a NAMED finding — model id, surface, authority, vendor
lane, kind — never a raw diff.

Lanes. One lane per vendor family. A lane is ACTIVE iff it has at least one
member in the ADR-149 working set AND at least one priced row in the cost
table. A vendor without a priced row is INERT by construction (fail-closed:
never a lane that reports empty). Measured at authorship: exactly one active
lane, ``anthropic``.

Exit codes (execution is separated from finding, per the W0a AC):
  0 — ran, no finding (or, with --expected-reds, the observed red set equals
      the expected one)
  1 — ran, at least one finding (or, with --expected-reds, the sets differ)
  2 — the detector broke: unreadable/ambiguous authority, unmodelled vendor
      family, incomplete state file, zero active lanes (K-8)

NO NETWORK. This module imports no networking primitive, directly or
transitively; the guarantee is proven by a RUNTIME oracle in
``.claude/scripts/tests/test_check_model_currency.py`` (a name grep is blind
to ``from _lib import model_feed_fetch``), whose declared blind spot is that
it proves the code paths the test exercises, not the whole file.

Stdlib only. Written for Python >= 3.9 per ADR-002 (no PEP 604 runtime
unions, no ``match``).
"""
from __future__ import annotations

import argparse
import ast
import datetime as _dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: Vendor family -> (id prefixes, authority name). A model id matching no
#: family is a FAIL-CLOSED break: "shape not modelled => fail-open" is the
#: class this repository already paid for (PLAN-185 W0).
_FAMILIES: Tuple[Tuple[str, Tuple[str, ...], str], ...] = (
    ("anthropic", ("claude-",), "ADR-149:AVAILABLE_MODELS_WORKING_SET"),
    ("openai", ("gpt-", "o3", "o4"), "codex_cli_shape:_VALID_MODELS"),
)

#: Death criteria of PLAN-176 §4, each bound to the state field that serves
#: it AND to its enforcement class. The AC is named
#: ``..._seven_death_criteria`` because §4 carried seven when the check was
#: written; debate round 2 added K-8 and K-9. All NINE are bound here — the
#: seven are served a fortiori.
#:
#: Columns: (name, field, threshold, enforcement, gated_on_cadence).
#: ``fail_closed`` criteria are the ones §4 spells "qualquer ocorrência" — they
#: are evaluated ALWAYS, and a breach exits 2. ``report_only`` criteria exit 1.
#: ``gated_on_cadence`` criteria count cycles or wall clock, so they are not
#: evaluated until ``cadence_started`` is true (the routine is wired in W3b):
#: reporting them before that would be an answer invented from no data.
_DEATH_CRITERIA: Tuple[Tuple[str, str, str, str, bool], ...] = (
    ("K-1", "false_positives.count", "> 2 in 8 cycles => auto-open off",
     "report_only", True),
    ("K-2", "trust_layer_touches", "any occurrence => red fail-closed in CI",
     "fail_closed", False),
    ("K-3", "upstream.age_hours", "older than 4 cycles or 96 h => report only",
     "report_only", True),
    ("K-4", "schema_break", "feed schema changed => fail-closed",
     "fail_closed", False),
    ("K-5", "false_negative_probe.last_cycle", "every 4 cycles, outside lanes",
     "report_only", True),
    ("K-6", "lanes", "3 consecutive lane failures => lane off",
     "report_only", True),
    ("K-7", "phase2_auto_merge_enabled", "phase 2 only with its own ADR",
     "fail_closed", False),
    ("K-8", "@active_lane_count", "zero active lanes => red, never green-empty",
     "fail_closed", False),
    ("K-9", "@state_age_hours", "newest cycle older than 96 h => routine dead",
     "report_only", True),
)

#: Wall-clock ceiling shared by K-3 and K-9 (PLAN-176 §4).
_STALE_HOURS = 96.0

_ADR_BLOCKS = ("VETO_FLOOR_ALLOWED", "AVAILABLE_MODELS_WORKING_SET")
_FENCE_RE = re.compile(r"^```python\n(.*?)^```", re.S | re.M)
_COST_MODEL_RE = re.compile(r"^  ([A-Za-z0-9][A-Za-z0-9._-]*):\s*$")


class DetectorBroke(Exception):
    """Raised for every fail-closed condition (exit >= 2)."""


# --------------------------------------------------------------------------
# Authority readers
# --------------------------------------------------------------------------

def _string_elements(node: ast.AST) -> List[str]:
    """Return the str constants of a Set/Tuple/List literal, incl. frozenset()."""
    if isinstance(node, ast.Call):
        if not node.args:
            raise DetectorBroke("authority literal: empty call")
        node = node.args[0]
    elts = getattr(node, "elts", None)
    if elts is None:
        raise DetectorBroke("authority literal is not a set/tuple/list")
    out = []
    for elt in elts:
        if not isinstance(elt, ast.Constant) or not isinstance(elt.value, str):
            raise DetectorBroke("authority literal holds a non-string element")
        out.append(elt.value)
    return out


def _assign_target(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    if (isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)):
        return node.targets[0].id
    return None


def read_adr_blocks(adr_path: Path) -> Dict[str, List[str]]:
    """Parse the two machine-parseable ADR-149 blocks out of ```python fences.

    Ambiguity is fail-closed: a name defined by more than one fence means the
    ADR grew a second table, which is exactly the K-4 "reader broke" case.
    """
    try:
        text = adr_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DetectorBroke("cannot read ADR authority %s: %s" % (adr_path, exc))
    seen = {}  # type: Dict[str, List[List[str]]]
    for fence in _FENCE_RE.findall(text):
        try:
            tree = ast.parse(fence)
        except SyntaxError:
            continue
        for node in tree.body:
            name = _assign_target(node)
            if name in _ADR_BLOCKS:
                seen.setdefault(name, []).append(_string_elements(node.value))
    for name in _ADR_BLOCKS:
        blocks = seen.get(name, [])
        if len(blocks) != 1:
            raise DetectorBroke(
                "ADR block %s: expected exactly 1 definition, found %d in %s"
                % (name, len(blocks), adr_path))
    return {name: seen[name][0] for name in _ADR_BLOCKS}


def read_valid_override_ids(shape_path: Path) -> List[str]:
    """Parse ``_VALID_MODELS`` from codex_cli_shape.py WITHOUT importing it."""
    try:
        tree = ast.parse(shape_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as exc:
        raise DetectorBroke("cannot read %s: %s" % (shape_path, exc))
    for node in ast.walk(tree):
        if _assign_target(node) == "_VALID_MODELS":
            return _string_elements(node.value)
    raise DetectorBroke("_VALID_MODELS not found in %s" % shape_path)


# --------------------------------------------------------------------------
# Surface readers
# --------------------------------------------------------------------------

def read_priced_ids(cost_table: Path) -> List[str]:
    """Read the ``models:`` keys of the mini-YAML cost table."""
    try:
        lines = cost_table.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DetectorBroke("cannot read cost table %s: %s" % (cost_table, exc))
    out, inside = [], False
    for line in lines:
        if re.match(r"^models:\s*$", line):
            inside = True
            continue
        if inside and re.match(r"^\S", line):
            inside = False
        if inside:
            hit = _COST_MODEL_RE.match(line)
            if hit:
                out.append(hit.group(1))
    if not out:
        raise DetectorBroke("cost table %s has no models: rows" % cost_table)
    return out


def read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DetectorBroke("cannot read %s %s: %s" % (label, path, exc))


def family_of(model_id: str) -> Tuple[str, str]:
    """Return (lane, authority_name) for a model id, or fail closed."""
    for lane, prefixes, authority in _FAMILIES:
        if model_id.startswith(prefixes):
            return lane, authority
    raise DetectorBroke(
        "unmodelled vendor family for model id %r — refusing to classify"
        % model_id)


# --------------------------------------------------------------------------
# The scan
# --------------------------------------------------------------------------

def _finding(model_id, surface, authority, kind, lane, active, detail):
    # type: (str, str, str, str, str, bool, str) -> Dict[str, Any]
    return {
        "model_id": model_id, "surface": surface, "authority": authority,
        "kind": kind, "lane": lane, "lane_active": active, "detail": detail,
    }


def _paths(root: Path, args: argparse.Namespace) -> Dict[str, Path]:
    def pick(flag, *parts):
        # type: (Optional[str], str) -> Path
        return Path(flag) if flag else root.joinpath(*parts)
    return {
        "adr": pick(args.adr, ".claude", "adr", "ADR-149-model-id-allowlist.md"),
        "shape": pick(args.codex_shape, ".claude", "hooks", "_lib",
                      "codex_cli_shape.py"),
        "cost": pick(args.cost_table, ".claude", "scripts", "cost-table.yaml"),
        "deps": pick(args.deprecations, ".claude", "scripts",
                     "model-deprecations.json"),
        "settings": pick(args.settings, ".claude", "settings.json"),
    }


def scan(root: Path, args: argparse.Namespace) -> Dict[str, Any]:
    """Run the offline comparison and return the report dict."""
    paths = _paths(root, args)
    blocks = read_adr_blocks(paths["adr"])
    working_set = blocks["AVAILABLE_MODELS_WORKING_SET"]
    valid_override = read_valid_override_ids(paths["shape"])
    priced = read_priced_ids(paths["cost"])
    authority_for = {
        "anthropic": (working_set, "ADR-149:AVAILABLE_MODELS_WORKING_SET"),
        "openai": (valid_override, "codex_cli_shape:_VALID_MODELS"),
    }

    lanes = {}  # type: Dict[str, Dict[str, Any]]
    for lane, _prefixes, _auth in _FAMILIES:
        members = [m for m in working_set if family_of(m)[0] == lane]
        rows = [p for p in priced if family_of(p)[0] == lane]
        lanes[lane] = {
            "active": bool(members) and bool(rows),
            "working_set_members": len(members),
            "priced_rows": len(rows),
        }
    active_lanes = sorted(n for n, v in lanes.items() if v["active"])
    if not active_lanes:
        raise DetectorBroke(
            "K-8: zero active lanes — refusing to report green-empty")

    findings = []  # type: List[Dict[str, Any]]
    for model_id in priced:
        lane, authority = family_of(model_id)
        if model_id not in working_set:
            findings.append(_finding(
                model_id, "cost-table.yaml", authority,
                "priced_outside_working_set", lane, lanes[lane]["active"],
                "priced row with no seat in the signed working set"))
    for model_id in working_set:
        if model_id not in priced:
            lane, authority = family_of(model_id)
            findings.append(_finding(
                model_id, "cost-table.yaml", authority,
                "working_set_without_price", lane, lanes[lane]["active"],
                "signed by the ADR but unknown to every other surface"))

    ledger = read_json(paths["deps"], "deprecation ledger")
    # Aggregate per replacement: the ledger names the same migration target
    # from many rows, and N identical findings is noise, not evidence.
    recommenders = {}  # type: Dict[str, List[str]]
    for entry in ledger.get("models", []):
        model_id = entry.get("replacement")
        if model_id:
            recommenders.setdefault(model_id, []).append(
                entry.get("model_id", "<unnamed>"))
    for model_id in sorted(recommenders):
        lane, authority = family_of(model_id)
        if model_id not in authority_for[lane][0]:
            sources = sorted(recommenders[model_id])
            findings.append(_finding(
                model_id, "model-deprecations.json", authority,
                "replacement_outside_authority", lane, lanes[lane]["active"],
                "migration target of %d deprecation rows (%s) not covered"
                % (len(sources), ", ".join(sources[:3]))))

    settings = read_json(paths["settings"], "settings")
    available = settings.get("availableModels")
    if available != list(working_set):
        findings.append(_finding(
            "<availableModels>", "settings.json",
            "ADR-149:AVAILABLE_MODELS_WORKING_SET",
            "settings_available_models_drift", "anthropic", True,
            "generated mirror diverges from the ADR (order is normative)"))
    for key in ("model",):
        value = settings.get(key)
        if value and value not in working_set:
            lane, authority = family_of(value)
            findings.append(_finding(
                value, "settings.json", authority,
                "settings_value_outside_working_set", lane,
                lanes[lane]["active"], "settings key %r" % key))
    for value in settings.get("fallbackModel") or []:
        if value not in working_set:
            lane, authority = family_of(value)
            findings.append(_finding(
                value, "settings.json", authority,
                "settings_value_outside_working_set", lane,
                lanes[lane]["active"], "fallbackModel member"))

    red_ids = sorted({f["model_id"] for f in findings})
    return {
        "schema": 1,
        "authorities": {
            "veto_floor": blocks["VETO_FLOOR_ALLOWED"],
            "working_set": working_set,
            "valid_override_ids": valid_override,
        },
        "lanes": lanes,
        "active_lanes": active_lanes,
        "findings": sorted(
            findings, key=lambda f: (f["surface"], f["model_id"], f["kind"])),
        "red_ids": red_ids,
    }


# --------------------------------------------------------------------------
# Expected-red gate (the ownership-expected-reds.txt mould)
# --------------------------------------------------------------------------

def read_expected_reds(path: Path) -> List[str]:
    """One model id per line; ``#`` comments carry the cause of each line."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DetectorBroke("cannot read expected-reds %s: %s" % (path, exc))
    out = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        out.append(stripped)
    if len(out) != len(set(out)):
        raise DetectorBroke("expected-reds %s has duplicate ids" % path)
    return sorted(out)


def compare_reds(observed: Sequence[str], expected: Sequence[str]):
    # type: (...) -> Tuple[List[str], List[str]]
    """Return (unexpected, missing). ANY difference — shrinkage included."""
    return (sorted(set(observed) - set(expected)),
            sorted(set(expected) - set(observed)))


# --------------------------------------------------------------------------
# State file + death criteria
# --------------------------------------------------------------------------

def _resolve_field(state: Dict[str, Any], dotted: str) -> Any:
    node = state  # type: Any
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(dotted)
        node = node[part]
    return node


def _state_age_hours(state: Dict[str, Any], now: _dt.datetime) -> float:
    raw = state.get("ts")
    if not isinstance(raw, str):
        raise DetectorBroke("state field 'ts' is missing or not a string")
    try:
        stamp = _dt.datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise DetectorBroke("state field 'ts' is not ISO-Z: %s" % exc)
    return round((now - stamp).total_seconds() / 3600.0, 2)


def _criterion_breached(name: str, value: Any, state: Dict[str, Any]) -> bool:
    """Apply the §4 threshold of ONE criterion. No default-true, no silence."""
    if name == "K-1":
        return isinstance(value, int) and value > 2
    if name in ("K-2",):
        return bool(value)
    if name == "K-3":
        stale = value is not None and float(value) > _STALE_HOURS
        upstream = state.get("upstream") or {}
        cycles = upstream.get("age_cycles")
        return bool(stale or (cycles is not None and int(cycles) > 4)
                    or (upstream.get("present") and not upstream.get("complete")))
    if name in ("K-4", "K-7"):
        return bool(value)
    if name == "K-5":
        return (state.get("false_negative_probe") or {}).get("passed") is False
    if name == "K-6":
        return any(int((lane or {}).get("consecutive_failures", 0)) >= 3
                   for lane in (value or {}).values())
    if name == "K-8":
        return int(value) < 1
    if name == "K-9":
        return float(value) > _STALE_HOURS
    raise DetectorBroke("no threshold rule for death criterion %s" % name)


def state_report(state: Dict[str, Any], report: Dict[str, Any],
                 now: _dt.datetime) -> Dict[str, Any]:
    """Serve AND EVALUATE every death criterion of §4 from the state file.

    A criterion whose field is absent is FAIL-CLOSED (DetectorBroke): an
    unreadable criterion is an unanswered one, never a silent green. A
    criterion whose threshold is crossed is reported ``breached`` — the
    verdict says what was MEASURED, never merely that a field exists.
    """
    derived = {
        "@active_lane_count": len(report["active_lanes"]),
        "@state_age_hours": _state_age_hours(state, now),
    }
    started = bool(state.get("cadence_started"))
    criteria = []
    for name, field, threshold, enforcement, gated in _DEATH_CRITERIA:
        if field.startswith("@"):
            value = derived[field]
        else:
            try:
                value = _resolve_field(state, field)
            except KeyError:
                raise DetectorBroke(
                    "death criterion %s has no field %r in the state file"
                    % (name, field))
        if gated and not started:
            verdict = "not_yet_wired"
        else:
            verdict = ("breached" if _criterion_breached(name, value, state)
                       else "ok")
        criteria.append({
            "criterion": name, "field": field, "threshold": threshold,
            "enforcement": enforcement, "value": value, "verdict": verdict,
        })
    return {
        "schema": 1, "state": state, "derived": derived,
        "cadence_started": started, "criteria": criteria,
    }


def state_exit_code(payload: Dict[str, Any]) -> int:
    """2 if any fail-closed criterion is breached, 1 if any other is, else 0."""
    worst = 0
    for entry in payload["criteria"]:
        if entry["verdict"] != "breached":
            continue
        worst = max(worst, 2 if entry["enforcement"] == "fail_closed" else 1)
    return worst


def record_cycle(state_path: Path, report: Dict[str, Any],
                 now: _dt.datetime) -> Dict[str, Any]:
    """Advance the tracked cycle counter and rewrite the state file."""
    state = read_json(state_path, "state file")
    state["cycle"] = int(state.get("cycle", 0)) + 1
    state["ts"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    lanes = {}
    for name, info in report["lanes"].items():
        previous = (state.get("lanes") or {}).get(name) or {}
        streak = int(previous.get("consecutive_failures", 0))
        # Per-LANE result and streak. Deriving them from the GLOBAL finding
        # list flipped an inert lane to "finding" for someone else's finding,
        # and froze the K-6 counter at its seed value forever.
        mine = [f for f in report["findings"] if f["lane"] == name]
        if not info["active"]:
            result = "inert"
        elif mine:
            result = "finding"
            streak += 1
        else:
            result = "clean"
            streak = 0
        lanes[name] = {
            "active": info["active"], "result": result,
            "consecutive_failures": streak,
        }
    state["lanes"] = lanes
    state_path.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return state


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _render_human(report: Dict[str, Any]) -> str:
    out = ["active lanes: %s" % ", ".join(report["active_lanes"])]
    for finding in report["findings"]:
        out.append(
            "FINDING %s | id=%s | surface=%s | authority=%s | lane=%s%s | %s"
            % (finding["kind"], finding["model_id"], finding["surface"],
               finding["authority"], finding["lane"],
               "" if finding["lane_active"] else " (INERT)", finding["detail"]))
    out.append("RED-IDS: %d" % len(report["red_ids"]))
    return "\n".join(out)


def _print_red_set_diff(report: Dict[str, Any]) -> None:
    gate = report.get("expected_reds")
    if not gate:
        return
    for model_id in gate["unexpected"]:
        print("RED-SET UNEXPECTED: %s" % model_id, file=sys.stderr)
    for model_id in gate["missing"]:
        print("RED-SET MISSING (shrinkage is a reason to STOP): %s"
              % model_id, file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline model-currency detector (PLAN-176 W0a).")
    parser.add_argument("--root", default=None, help="repo root override")
    parser.add_argument("--adr", default=None)
    parser.add_argument("--codex-shape", default=None)
    parser.add_argument("--cost-table", default=None)
    parser.add_argument("--deprecations", default=None)
    parser.add_argument("--settings", default=None)
    parser.add_argument("--state-file", default=None)
    parser.add_argument("--expected-reds", default=None,
                        help="gate the observed red set against this file")
    parser.add_argument("--state", action="store_true",
                        help="serve the death criteria from the state file")
    parser.add_argument("--record-cycle", action="store_true",
                        help="advance the cycle counter in the state file")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--now", default=None,
                        help="ISO-Z instant override (tests)")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve() if args.root else _REPO_ROOT
    # naive UTC without datetime.utcnow(): it is deprecated on 3.12+ and the
    # evidence battery runs pytest under -W error.
    now = (_dt.datetime.strptime(args.now, "%Y-%m-%dT%H:%M:%SZ") if args.now
           else _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None))
    state_path = (Path(args.state_file) if args.state_file
                  else root / ".claude" / "data" / "model-currency-state.json")
    try:
        report = scan(root, args)
        if args.record_cycle:
            report["state"] = record_cycle(state_path, report, now)

        # Flag composition keeps the MOST SEVERE code. Returning early from
        # one branch silences the other — fail-open by composition, in a
        # repository whose input rule is fail-closed.
        gate_rc = None
        if args.expected_reds:
            expected = read_expected_reds(Path(args.expected_reds))
            unexpected, missing = compare_reds(report["red_ids"], expected)
            report["expected_reds"] = {
                "expected": expected, "unexpected": unexpected,
                "missing": missing,
            }
            gate_rc = 1 if (unexpected or missing) else 0

        if args.state:
            payload = state_report(
                read_json(state_path, "state file"), report, now)
            if args.expected_reds:
                payload["expected_reds"] = report["expected_reds"]
            print(json.dumps(payload, indent=2, sort_keys=True) if args.json
                  else "\n".join(
                      "%s %s = %r [%s/%s]"
                      % (c["criterion"], c["field"], c["value"],
                         c["verdict"], c["enforcement"])
                      for c in payload["criteria"]))
            state_rc = state_exit_code(payload)
            for entry in payload["criteria"]:
                if entry["verdict"] == "breached":
                    print("DEATH-CRITERION BREACHED (%s): %s %s = %r"
                          % (entry["enforcement"], entry["criterion"],
                             entry["field"], entry["value"]), file=sys.stderr)
            _print_red_set_diff(report)
            return max(state_rc, gate_rc or 0)

        print(json.dumps(report, indent=2, sort_keys=True) if args.json
              else _render_human(report))
        if gate_rc is not None:
            _print_red_set_diff(report)
            return gate_rc
        return 1 if report["findings"] else 0
    except DetectorBroke as exc:
        print("DETECTOR-BROKE: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
