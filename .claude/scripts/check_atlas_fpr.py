#!/usr/bin/env python3
"""check_atlas_fpr.py — FPR + TPR gate for ATLAS mappings & detection families.

PLAN-085 Wave G.1a (heuristic mode) + PLAN-095 Wave B.4.1 (S128 refresh).

## What changed in PLAN-095 Wave B.4.1

1. **Live registry import.** The inline `_ATLAS_REGISTRY` (5 entries
   from G.1a v1.19.0) was a frozen heuristic shim. With G.1b shipped
   (PLAN-085) and the registry expanded to 19/11 (PLAN-088/089/090),
   the shim was perpetually stale. PLAN-095 Wave B.4.1 replaces the
   shim with a live `importlib.util` load of
   `.claude/hooks/_lib/audit_emit._ATLAS_REGISTRY` (same pattern as
   `verify-atlas-binding.py`).
2. **`--pattern-class <STRING>` filter.** Restricts FPR/TPR computation
   to a single OWASP family (e.g. `LLM03_2025_supply_chain`). Required
   for PLAN-095 Wave B AC8 + ADR-049 detection-as-code per-family gate.
3. **`--min-tpr <FLOAT>` positive-fixture gate.** Asserts true-positive
   rate ≥ floor (default 0.80). Rejects "tune-after-deploy" anti-pattern
   per SKILL §Detection-as-Code.
4. **Strict empty-corpus guard.** Empty directory or zero events =
   exit 2 with stderr message (was vacuous PASS exit 0). PLAN-095
   AC17 — empty corpus = denominator-zero footgun.

## Usage

    python3 .claude/scripts/check_atlas_fpr.py --help
    # Legacy mode (all ATLAS bindings, FPR only):
    python3 .claude/scripts/check_atlas_fpr.py \
        --corpus tests/fixtures/red-team-corpus/ \
        --threshold 0.15
    # Per-family mode (PLAN-095 Wave B):
    python3 .claude/scripts/check_atlas_fpr.py \
        --pattern-class LLM03_2025_supply_chain \
        --corpus tests/fixtures/red-team-corpus/ \
        --threshold 0.15 \
        --min-tpr 0.80

## Exit codes

* 0 — FPR ≤ threshold AND TPR ≥ min-tpr for ALL gated mappings (PASS)
* 1 — at least one mapping exceeded FPR threshold OR fell below TPR floor (FAIL)
* 2 — usage error / corpus missing / corpus empty / malformed input

## Corpus expectations

Recursively walks ``--corpus`` for ``*.ndjson`` files. Each line is
one JSON event with at least:

    {
      "action":     "<one of _ATLAS_REGISTRY actions or other>",
      "family":     "<optional — detection family for --pattern-class>",
      "attack":     true | false,
      ...
    }

Events without an ``attack`` label are skipped (not counted toward
FPR's denominator). If the corpus directory does not exist or
contains zero events, the script exits 2 (denominator-zero guard).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


_REPO_ROOT = Path(__file__).resolve().parents[2]
_AUDIT_EMIT_PATH = _REPO_ROOT / ".claude" / "hooks" / "_lib" / "audit_emit.py"
_OUTPUT_SCAN_PATH = _REPO_ROOT / ".claude" / "hooks" / "_lib" / "output_scan.py"


def _load_atlas_registry() -> Dict[str, str]:
    """PLAN-095 Wave B.4.1 — live load `_ATLAS_REGISTRY` from audit_emit.

    Mirrors `verify-atlas-binding.py::_load_audit_emit_registry()`. The
    inline shim is gone; this is the only source.
    """
    spec = importlib.util.spec_from_file_location(
        "audit_emit_for_fpr", _AUDIT_EMIT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"failed to load audit_emit from {_AUDIT_EMIT_PATH}"
        )
    mod = importlib.util.module_from_spec(spec)
    hooks_dir = str(_AUDIT_EMIT_PATH.parent.parent)
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    spec.loader.exec_module(mod)
    return dict(getattr(mod, "_ATLAS_REGISTRY", {}))


def _load_output_scan_module():
    """PLAN-095 Wave B.4.1 + iter-2 P0 — live load `_lib/output_scan`
    for `--scan-payload-preview` runtime mode.

    Returns module instance with `scan_llm_top_10` + `_LLM_PATTERN_GROUPS`
    attributes. Raises on load failure (caller decides exit code).
    """
    spec = importlib.util.spec_from_file_location(
        "output_scan_for_fpr", _OUTPUT_SCAN_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"failed to load output_scan from {_OUTPUT_SCAN_PATH}"
        )
    mod = importlib.util.module_from_spec(spec)
    hooks_dir = str(_OUTPUT_SCAN_PATH.parent.parent)
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    spec.loader.exec_module(mod)
    return mod


def _compute_runtime_fpr_tpr(
    events: List[Dict[str, object]],
    pattern_class: str,
    output_scan_mod,
) -> Dict[str, float]:
    """PLAN-095 Wave B.4.1 + iter-2 P0 — REAL runtime FPR/TPR by executing
    `output_scan.scan_llm_top_10` against each event's payload_preview.

    Returns single-pattern result dict: {fp, tn, tp, fn, fpr, tpr,
    neg_denom, pos_denom}. Single-key keyed by `pattern_class`.

    Codex R2 iter-2 P0 closure: the legacy `_compute_fpr_tpr` action-key
    heuristic is vacuous against output-scan corpus (corpus events use
    `action=output_scan_finding`, which doesn't intersect
    `_ATLAS_REGISTRY` keys → FPR=0 always). This runtime mode actually
    fires the regex against the corpus payloads and measures real
    detection performance.
    """
    fp = 0
    tn = 0
    tp = 0
    fn = 0

    for ev in events:
        attack = ev.get("attack")
        if not isinstance(attack, bool):
            continue
        payload = ev.get("payload_preview")
        if not isinstance(payload, str):
            # Without a payload_preview we can't exercise the regex.
            # Treat as not-evaluable (skip — doesn't affect FPR/TPR).
            continue
        try:
            findings = output_scan_mod.scan_llm_top_10(payload)
        except Exception:
            # Fail-open per scan_llm_top_10 contract; treat as not-fires.
            findings = []
        fires = any(
            isinstance(f, dict) and f.get("family") == pattern_class
            for f in findings
        )
        if attack:
            if fires:
                tp += 1
            else:
                fn += 1
        else:
            if fires:
                fp += 1
            else:
                tn += 1

    neg_denom = fp + tn
    pos_denom = tp + fn
    fpr = (fp / neg_denom) if neg_denom > 0 else 0.0
    tpr = (tp / pos_denom) if pos_denom > 0 else 0.0
    return {
        "fp": float(fp),
        "tn": float(tn),
        "tp": float(tp),
        "fn": float(fn),
        "fpr": fpr,
        "tpr": tpr,
        "neg_denom": float(neg_denom),
        "pos_denom": float(pos_denom),
    }


def _print_runtime_report(
    pattern_class: str,
    result: Dict[str, float],
    threshold: float,
    min_tpr: Optional[float],
    *,
    stream: Optional[object] = None,
) -> bool:
    """Print runtime-mode report; return True iff PASS gates."""
    if stream is None:
        stream = sys.stdout
    header_parts = [
        f"RUNTIME MODE (scan_payload_preview)",
        f"family={pattern_class}",
        f"threshold={threshold:.4f}",
    ]
    if min_tpr is not None:
        header_parts.append(f"min_tpr={min_tpr:.4f}")
    print(f"[check_atlas_fpr] {' '.join(header_parts)}", file=stream)
    verdicts: List[str] = []
    if result["fpr"] > threshold:
        verdicts.append(f"FAIL_FPR(fpr={result['fpr']:.4f}>{threshold:.4f})")
    # S128 R2 iter-3 P0 — denominator-zero TPR guard.
    if min_tpr is not None:
        if result["pos_denom"] == 0:
            verdicts.append(
                f"FAIL_NO_POSITIVES(min_tpr={min_tpr:.4f} but pos_denom=0; "
                f"corpus needs attack=true events tagged with "
                f"family={pattern_class})"
            )
        elif result["tpr"] < min_tpr:
            verdicts.append(
                f"FAIL_TPR(tpr={result['tpr']:.4f}<{min_tpr:.4f})"
            )
    if not verdicts:
        verdicts.append("PASS")
    verdict = ",".join(verdicts)
    print(
        f"  [{verdict}] {pattern_class}: "
        f"FP={int(result['fp'])} TN={int(result['tn'])} "
        f"TP={int(result['tp'])} FN={int(result['fn'])} "
        f"FPR={result['fpr']:.4f} TPR={result['tpr']:.4f}",
        file=stream,
    )
    return all(v.startswith("PASS") for v in verdicts)


def _iter_ndjson(path: Path) -> List[Dict[str, object]]:
    """Read one NDJSON file; skip blank lines; raise on malformed JSON."""
    events: List[Dict[str, object]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(
                    f"[check_atlas_fpr] {path}:{lineno} malformed JSON: "
                    f"{exc}"
                )
    return events


def _collect_corpus_events(corpus_dir: Path) -> List[Dict[str, object]]:
    """Walk ``corpus_dir`` recursively for ``*.ndjson`` files."""
    events: List[Dict[str, object]] = []
    for ndjson_path in sorted(corpus_dir.rglob("*.ndjson")):
        events.extend(_iter_ndjson(ndjson_path))
    return events


def _filter_by_pattern_class(
    events: List[Dict[str, object]],
    pattern_class: Optional[str],
) -> List[Dict[str, object]]:
    """PLAN-095 Wave B.4.1 — filter events by `family` field.

    When `pattern_class` is None, returns events unchanged (legacy mode).
    Otherwise keeps only events whose `family` field == pattern_class.
    Events lacking `family` are dropped under filter mode (they can't
    contribute to per-family FPR/TPR).
    """
    if pattern_class is None:
        return events
    return [
        ev for ev in events
        if isinstance(ev.get("family"), str)
        and ev.get("family") == pattern_class
    ]


def _classify_atlas_via_registry(
    action: object,
    registry: Dict[str, str],
) -> Optional[str]:
    """Heuristic — registry lookup by action name."""
    if not isinstance(action, str):
        return None
    return registry.get(action)


def _compute_fpr_tpr(
    events: List[Dict[str, object]],
    registry: Dict[str, str],
    pattern_class: Optional[str],
) -> Dict[str, Dict[str, float]]:
    """Compute per-mapping {fp, tn, tp, fn, fpr, tpr} from labeled events.

    Heuristic-mode semantics (PLAN-085 G.1a contract; preserved here):

    - **TP** = event where `ev_action == action` AND `attack=true`
      (the action correctly fired on a labeled positive).
    - **FP** = event where `ev_action == action` AND `attack=false`
      (the action incorrectly fired on a labeled negative).
    - **TN** = event where `ev_action != action` AND `attack=false`
      (the action correctly stayed silent on a negative).
    - **FN** = `0` always (heuristic limit). The action-keyed corpus
      does not carry an independent "ground truth that the action
      should have fired" signal — every positive event already
      asserts its target action via the `ev_action` field, so there
      is no missed-detection signal to count.

    Consequence: `pos_denom = TP`, `TPR = 1.0` whenever `TP > 0`.
    `--min-tpr` gate functions as "at least one labeled positive event
    matched this action" rather than a true recall measure. For real
    recall measurement, ship a separate ground-truth corpus + harness
    (deferred to FOLLOWUP per ADR-049 §detection-as-code roadmap).

    Cross-action FN counting was an earlier prototype that conflated
    "different attack class" with "missed detection" and produced
    spurious gate failures; removed S128 PLAN-095 Wave B.4.1.
    """
    actions_in_scope = sorted(registry.keys())
    fp: Dict[str, int] = {a: 0 for a in actions_in_scope}
    tn: Dict[str, int] = {a: 0 for a in actions_in_scope}
    tp: Dict[str, int] = {a: 0 for a in actions_in_scope}
    fn: Dict[str, int] = {a: 0 for a in actions_in_scope}

    for ev in events:
        attack = ev.get("attack")
        if not isinstance(attack, bool):
            continue
        ev_action = ev.get("action")
        for action in actions_in_scope:
            is_event_action = (ev_action == action)
            if attack:
                if is_event_action:
                    tp[action] += 1
                # No cross-action FN — heuristic-mode limitation
                # (see docstring).
            else:
                if is_event_action:
                    fp[action] += 1
                else:
                    tn[action] += 1

    out: Dict[str, Dict[str, float]] = {}
    for action in actions_in_scope:
        neg_denom = fp[action] + tn[action]
        pos_denom = tp[action] + fn[action]
        fpr = (fp[action] / neg_denom) if neg_denom > 0 else 0.0
        tpr = (tp[action] / pos_denom) if pos_denom > 0 else 0.0
        out[action] = {
            "fp": float(fp[action]),
            "tn": float(tn[action]),
            "tp": float(tp[action]),
            "fn": float(fn[action]),
            "fpr": fpr,
            "tpr": tpr,
            "neg_denom": float(neg_denom),
            "pos_denom": float(pos_denom),
        }
    return out


def _print_report(
    results: Dict[str, Dict[str, float]],
    registry: Dict[str, str],
    threshold: float,
    min_tpr: Optional[float],
    pattern_class: Optional[str],
    *,
    stream: Optional[object] = None,
) -> bool:
    """Print one line per mapping; return True iff ALL within gates."""
    if stream is None:
        stream = sys.stdout
    all_pass = True
    header_parts = [
        f"threshold={threshold:.4f}",
        f"mappings={len(registry)}",
    ]
    if min_tpr is not None:
        header_parts.append(f"min_tpr={min_tpr:.4f}")
    if pattern_class is not None:
        header_parts.append(f"pattern_class={pattern_class}")
    print(f"[check_atlas_fpr] {' '.join(header_parts)}", file=stream)
    for action in sorted(registry.keys()):
        atlas_id = registry[action]
        m = results[action]
        verdicts: List[str] = []
        # FPR gate.
        if m["fpr"] > threshold:
            verdicts.append(f"FAIL_FPR(fpr={m['fpr']:.4f}>{threshold:.4f})")
            all_pass = False
        # TPR gate (only enforced when min_tpr set AND positive events exist).
        if min_tpr is not None and m["pos_denom"] > 0:
            if m["tpr"] < min_tpr:
                verdicts.append(
                    f"FAIL_TPR(tpr={m['tpr']:.4f}<{min_tpr:.4f})"
                )
                all_pass = False
        if not verdicts:
            verdicts.append("PASS")
        verdict = ",".join(verdicts)
        print(
            f"  [{verdict}] {action} ({atlas_id}): "
            f"FP={int(m['fp'])} TN={int(m['tn'])} "
            f"TP={int(m['tp'])} FN={int(m['fn'])} "
            f"FPR={m['fpr']:.4f} TPR={m['tpr']:.4f}",
            file=stream,
        )
    return all_pass


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="check_atlas_fpr.py",
        description=(
            "Compute false-positive AND true-positive rates for ATLAS "
            "mappings against a labeled red-team corpus. PLAN-085 G.1a "
            "heuristic mode + PLAN-095 Wave B.4.1 live registry + "
            "--pattern-class + --min-tpr + strict empty-corpus guard."
        ),
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        required=True,
        help="Directory containing labeled red-team .ndjson events.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.15,
        help="Per-mapping FPR ceiling (default 0.15 = 15%%).",
    )
    parser.add_argument(
        "--min-tpr",
        type=float,
        default=None,
        help=(
            "PLAN-095 Wave B.4.1 — per-mapping TPR floor "
            "(default disabled; pass 0.80 for AC8 detection gate)."
        ),
    )
    parser.add_argument(
        "--pattern-class",
        type=str,
        default=None,
        help=(
            "PLAN-095 Wave B.4.1 — restrict FPR/TPR computation to "
            "events whose `family` field equals this value "
            "(e.g. LLM03_2025_supply_chain)."
        ),
    )
    parser.add_argument(
        "--scan-payload-preview",
        action="store_true",
        default=False,
        help=(
            "PLAN-095 R2 iter-2 P0 — RUNTIME MODE: actually execute "
            "_lib/output_scan.scan_llm_top_10 against each event's "
            "payload_preview and measure real FPR/TPR per family hit. "
            "Requires --pattern-class. The legacy metadata heuristic "
            "is vacuous against output-scan corpora (corpus events "
            "carry action=output_scan_finding which doesn't intersect "
            "_ATLAS_REGISTRY keys); runtime mode actually fires the "
            "regex and gates the rule's empirical behavior."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)

    if not (0.0 <= args.threshold <= 1.0):
        print(
            f"[check_atlas_fpr] error: --threshold {args.threshold} "
            f"outside [0.0, 1.0]",
            file=sys.stderr,
        )
        return 2
    if args.min_tpr is not None and not (0.0 <= args.min_tpr <= 1.0):
        print(
            f"[check_atlas_fpr] error: --min-tpr {args.min_tpr} "
            f"outside [0.0, 1.0]",
            file=sys.stderr,
        )
        return 2

    corpus_dir: Path = args.corpus
    if not corpus_dir.exists():
        print(
            f"[check_atlas_fpr] corpus directory not found: "
            f"{corpus_dir}\n"
            f"Hint: populate `tests/fixtures/red-team-corpus/` with "
            f"`*.ndjson` events carrying `attack: true|false` labels.",
            file=sys.stderr,
        )
        return 2
    if not corpus_dir.is_dir():
        print(
            f"[check_atlas_fpr] --corpus {corpus_dir} is not a "
            f"directory.",
            file=sys.stderr,
        )
        return 2

    events = _collect_corpus_events(corpus_dir)
    filtered = _filter_by_pattern_class(events, args.pattern_class)

    # PLAN-095 Wave B.4.1 / AC17 — strict empty-corpus guard.
    # Reject vacuous PASS that S125 lesson identified as a footgun.
    if not events:
        print(
            f"[check_atlas_fpr] corpus {corpus_dir} contained zero "
            f"NDJSON events — denominator-zero guard exit 2. "
            f"Populate with ≥1 labeled event before running gate.",
            file=sys.stderr,
        )
        return 2
    if args.pattern_class is not None and not filtered:
        print(
            f"[check_atlas_fpr] corpus had {len(events)} event(s) but "
            f"ZERO matched --pattern-class={args.pattern_class}. "
            f"Either the family is not yet labeled in corpus OR the "
            f"pattern-class string mismatches. Exit 2.",
            file=sys.stderr,
        )
        return 2

    # PLAN-095 R2 iter-2 P0 — runtime mode (real regex execution).
    if args.scan_payload_preview:
        if args.pattern_class is None:
            print(
                "[check_atlas_fpr] error: --scan-payload-preview requires "
                "--pattern-class to identify which family regex to exercise.",
                file=sys.stderr,
            )
            return 2
        try:
            output_scan_mod = _load_output_scan_module()
        except Exception as exc:
            print(
                f"[check_atlas_fpr] error: failed to load output_scan "
                f"module: {exc}",
                file=sys.stderr,
            )
            return 2
        groups = getattr(output_scan_mod, "_LLM_PATTERN_GROUPS", {})
        if args.pattern_class not in groups:
            print(
                f"[check_atlas_fpr] error: pattern-class "
                f"{args.pattern_class!r} not registered in "
                f"_lib/output_scan.py::_LLM_PATTERN_GROUPS. "
                f"Apply kernel patches first (e.g. PLAN-095 ceremony "
                f"Phase B for LLM03_2025_supply_chain).",
                file=sys.stderr,
            )
            return 2
        runtime_result = _compute_runtime_fpr_tpr(
            filtered, args.pattern_class, output_scan_mod
        )
        runtime_pass = _print_runtime_report(
            args.pattern_class,
            runtime_result,
            args.threshold,
            args.min_tpr,
        )
        return 0 if runtime_pass else 1

    try:
        registry = _load_atlas_registry()
    except Exception as exc:
        print(
            f"[check_atlas_fpr] error: failed to load _ATLAS_REGISTRY "
            f"— {exc}",
            file=sys.stderr,
        )
        return 2

    results = _compute_fpr_tpr(filtered, registry, args.pattern_class)
    all_pass = _print_report(
        results,
        registry,
        args.threshold,
        args.min_tpr,
        args.pattern_class,
    )
    return 0 if all_pass else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
