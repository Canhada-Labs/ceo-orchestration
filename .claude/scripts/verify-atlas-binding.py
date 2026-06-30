#!/usr/bin/env python3
"""verify-atlas-binding.py — PLAN-088 W0.3 ATLAS-bound register verifier.

Asserts every action in the PLAN-088 canonical-13 set is present in
`_lib/audit_emit._KNOWN_ACTIONS`. For each action with a non-null
`atlas_technique` per the W0 canonical-13 table, asserts membership
in `_lib/audit_emit._ATLAS_REGISTRY` mapping to the expected technique
ID. For actions with `atlas_technique: null`, asserts a non-empty
`atlas_rationale` string in the canonical-13 metadata table.

Stdlib-only AST parser (no third-party deps). Fails CI exit 1 on
missing/empty/unmapped action.

Per PLAN-088 §4 Wave 0 + R2 iter-1 C1 fold (P0/TDE-Case-F ATLAS
action-bound) + AC15.6 mechanical lift target.

## Canonical-13 source of truth

The canonical-13 set is INLINED below as `_CANONICAL_13` so the
verifier has zero external dependency on plan-file path resolution.
If the canonical-13 set drifts vs PLAN-088 §1.5 column-1 enumeration,
update both surfaces in the same commit.

## PLAN-095 Wave A.8 (S128) — `--strict-namespace`

The `_ATLAS_REGISTRY` mixes MITRE ATLAS (`AML.T*`) and MITRE ATT&CK
Enterprise (`T1071` / `T1556` / `T1565.001`) technique IDs across the
PLAN-089/090 expansion (R1 TDE P0 fold + R2 Codex iter-1 P1 taxonomy
correction). The `--strict-namespace` flag makes the mix EXPLICIT
rather than implicit: it asserts every unique technique ID in
`_ATLAS_REGISTRY` has a corresponding entry in the inline
`_NAMESPACE_REGISTRY` below mapping to either `atlas` or
`attack-enterprise`. Source of truth INLINED here (mirrors
`_lib/audit_emit._ATLAS_NAMESPACE_REGISTRY` shipped in the same
commit; both surfaces updated together if the namespace mix changes).

## Usage

    python3 .claude/scripts/verify-atlas-binding.py [--quiet] [--strict-namespace]

Exit code 0 = all checks PASS. Exit 1 = failure.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Canonical-13 metadata table from PLAN-088 §4 Wave 0 W0 ATLAS-binding
# table. Frozen at PLAN-088 ship. Format:
# action_name -> (atlas_technique_or_None, atlas_rationale)
_CANONICAL_13: Dict[str, Tuple[Optional[str], str]] = {
    "cache_discipline_alerted":         (None,             "telemetry-only"),
    "first_run_wizard_dispatched":      (None,             "UX trigger"),
    "estimate_calibrator_pipeline_run": (None,             "telemetry-only"),
    "subagent_findings_partial_drop":   ("AML.T0048",      "Governance bypass observation"),
    "anthropic_429_observed":           ("AML.T0029",      "Denial of ML Service signal"),
    "git_index_lock_retry":             (None,             "infra-error"),
    "codex_invoke_dispatched":          ("AML.T0050",      "LLM Plugin Compromise dual-rail"),
    "tier_policy_misrouting_advised":   ("AML.T0048",      "Governance bypass"),
    "model_routing_advised":            (None,             "routing-decision telemetry"),
    "mcp_route_advised":                ("AML.T0050",      "LLM Plugin / supply-chain signal"),
    "cookbook_pattern_advised":         (None,             "UX hint"),
    "pair_rail_phase_advanced":         ("AML.T0050",      "LLM Plugin Compromise dual-rail check"),
    "batch_dispatched":                 (None,             "cost-optimization telemetry"),
}

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AUDIT_EMIT_PATH = _REPO_ROOT / ".claude" / "hooks" / "_lib" / "audit_emit.py"


# PLAN-095 Wave A.8 (S128) — namespace registry for --strict-namespace gate.
# Each of the 11 unique technique IDs currently in `_ATLAS_REGISTRY`
# maps to either `atlas` (MITRE ATLAS LLM-system surface) or
# `attack-enterprise` (MITRE ATT&CK Enterprise OS-level surface).
# When `_ATLAS_REGISTRY` adds a new unique ID, add a matching entry
# here in the same commit OR `--strict-namespace` will FAIL with
# `missing_namespace_for_id` finding.
_NAMESPACE_REGISTRY: Dict[str, str] = {
    "AML.T0024.001": "atlas",
    "AML.T0029":     "atlas",
    "AML.T0048":     "atlas",
    "AML.T0048.004": "atlas",
    "AML.T0049":     "atlas",
    "AML.T0050":     "atlas",
    "AML.T0051":     "atlas",
    "AML.T0054":     "atlas",
    "T1071":         "attack-enterprise",
    "T1556":         "attack-enterprise",
    "T1565.001":     "attack-enterprise",
}
_VALID_NAMESPACES = frozenset({"atlas", "attack-enterprise"})


def _load_audit_emit_registry() -> Tuple[List[str], Dict[str, str]]:
    """Load `_KNOWN_ACTIONS` + `_ATLAS_REGISTRY` from audit_emit module.

    Uses direct import (stdlib-only) rather than AST parsing because
    the registry is built via module-level executable code (literal
    list + dict). AST parse of literal collections is doable but
    fragile vs comment changes; runtime import gets the canonical
    object.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("audit_emit", _AUDIT_EMIT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load audit_emit from {_AUDIT_EMIT_PATH}")
    mod = importlib.util.module_from_spec(spec)
    # Need hooks dir on sys.path for cross-module imports inside audit_emit
    hooks_dir = str(_AUDIT_EMIT_PATH.parent.parent)
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    spec.loader.exec_module(mod)
    known = list(getattr(mod, "_KNOWN_ACTIONS", []))
    atlas = dict(getattr(mod, "_ATLAS_REGISTRY", {}))
    return known, atlas


def _resolve_namespace_registry(
    audit_emit_namespace: Optional[Dict[str, str]],
) -> Tuple[Dict[str, str], List[str]]:
    """PLAN-095 Wave A.8 — resolve effective namespace registry.

    Codex R2 iter-1 P1 closure (S128): the inline `_NAMESPACE_REGISTRY`
    above is a fallback / Phase-1 source. Post-Patch-1c
    (`OWNER-CEREMONY-PLAN-095.sh` Phase B), `audit_emit.py` ships a
    canonical `_ATLAS_NAMESPACE_REGISTRY` that is the runtime source
    of truth. This function prefers the live audit_emit registry when
    present + cross-validates against the inline fallback (drift gate).

    Returns (effective_registry, drift_findings). drift_findings is
    non-empty when audit_emit and inline disagree — caller treats
    as failure surface.
    """
    drift: List[str] = []
    if audit_emit_namespace is None:
        # Pre-ceremony state — only inline source available.
        return _NAMESPACE_REGISTRY, drift
    # Cross-validate: both must agree (key set + per-key values).
    live_keys = set(audit_emit_namespace.keys())
    inline_keys = set(_NAMESPACE_REGISTRY.keys())
    only_in_live = sorted(live_keys - inline_keys)
    only_in_inline = sorted(inline_keys - live_keys)
    for tid in only_in_live:
        drift.append(
            f"  {tid}: drift_inline_missing — audit_emit._ATLAS_NAMESPACE_REGISTRY "
            f"has entry but verify-atlas-binding._NAMESPACE_REGISTRY does not. "
            f"Update inline fallback in same commit."
        )
    for tid in only_in_inline:
        drift.append(
            f"  {tid}: drift_live_missing — verify-atlas-binding._NAMESPACE_REGISTRY "
            f"has entry but audit_emit._ATLAS_NAMESPACE_REGISTRY does not. "
            f"Update kernel registry in same commit."
        )
    for tid in sorted(live_keys & inline_keys):
        if audit_emit_namespace[tid] != _NAMESPACE_REGISTRY[tid]:
            drift.append(
                f"  {tid}: drift_value_mismatch — "
                f"audit_emit={audit_emit_namespace[tid]!r} vs "
                f"inline={_NAMESPACE_REGISTRY[tid]!r}"
            )
    # Use live as effective source when available.
    return audit_emit_namespace, drift


def _load_audit_emit_namespace_registry() -> Optional[Dict[str, str]]:
    """Try to load `_ATLAS_NAMESPACE_REGISTRY` from audit_emit.

    Returns None if the symbol doesn't exist (pre-Patch-1c state).
    """
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "audit_emit_for_ns", _AUDIT_EMIT_PATH
        )
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        hooks_dir = str(_AUDIT_EMIT_PATH.parent.parent)
        if hooks_dir not in sys.path:
            sys.path.insert(0, hooks_dir)
        spec.loader.exec_module(mod)
        live = getattr(mod, "_ATLAS_NAMESPACE_REGISTRY", None)
        if isinstance(live, dict):
            return dict(live)
        return None
    except Exception:
        return None


def _verify_namespace(atlas: Dict[str, str]) -> List[str]:
    """PLAN-095 Wave A.8 — assert each unique technique-ID in
    `_ATLAS_REGISTRY` carries an explicit namespace classification.

    Returns list of human-readable failure strings (empty = PASS).

    Failure modes:
    1. `missing_namespace_for_id` — a technique ID is in `_ATLAS_REGISTRY`
       but absent from the effective namespace registry.
    2. `invalid_namespace_value` — a namespace entry maps to a value
       outside `_VALID_NAMESPACES = {"atlas", "attack-enterprise"}`.
    3. `stale_namespace_entry` — namespace registry references ID
       absent from `_ATLAS_REGISTRY`.
    4. `drift_*` — audit_emit `_ATLAS_NAMESPACE_REGISTRY` (post-Patch-1c)
       and verify-atlas-binding inline `_NAMESPACE_REGISTRY` disagree.
    """
    failures: List[str] = []
    audit_emit_ns = _load_audit_emit_namespace_registry()
    namespace, drift = _resolve_namespace_registry(audit_emit_ns)
    failures.extend(drift)

    unique_ids = sorted({tid for tid in atlas.values()})
    for tid in unique_ids:
        ns = namespace.get(tid)
        if ns is None:
            failures.append(
                f"  {tid}: missing_namespace_for_id — add to "
                f"_NAMESPACE_REGISTRY (and audit_emit._ATLAS_NAMESPACE_REGISTRY) "
                f"with value 'atlas' or 'attack-enterprise'"
            )
        elif ns not in _VALID_NAMESPACES:
            failures.append(
                f"  {tid}: invalid_namespace_value={ns!r} — must be one of "
                f"{sorted(_VALID_NAMESPACES)!r}"
            )
    # Reverse drift: namespace entries for IDs no longer in registry.
    registry_ids = set(atlas.values())
    for tid in sorted(namespace.keys()):
        if tid not in registry_ids:
            failures.append(
                f"  {tid}: stale_namespace_entry — namespace registry "
                f"references ID absent from `_ATLAS_REGISTRY` (remove or "
                f"re-add the binding)"
            )
    return failures


def verify(quiet: bool = False, strict_namespace: bool = False) -> int:
    """Verify canonical-13 ATLAS binding. Returns exit code (0 = PASS).

    If `strict_namespace=True`, additionally asserts every unique
    technique-ID in `_ATLAS_REGISTRY` has a corresponding entry in
    `_NAMESPACE_REGISTRY` per PLAN-095 Wave A.8 + AC9.
    """
    try:
        known, atlas = _load_audit_emit_registry()
    except Exception as exc:
        print(f"FAIL: cannot load audit_emit registry — {exc}", file=sys.stderr)
        return 1

    failures: List[str] = []

    for action, (expected_technique, expected_rationale) in _CANONICAL_13.items():
        # Check 1: action must be in _KNOWN_ACTIONS
        if action not in known:
            failures.append(
                f"  {action}: NOT in _KNOWN_ACTIONS (register the action)"
            )
            continue

        # Check 2: if expected_technique non-null, must be in _ATLAS_REGISTRY
        if expected_technique is not None:
            actual = atlas.get(action)
            if actual is None:
                failures.append(
                    f"  {action}: expected atlas_technique={expected_technique} "
                    f"but absent from _ATLAS_REGISTRY"
                )
            elif actual != expected_technique:
                failures.append(
                    f"  {action}: expected atlas_technique={expected_technique} "
                    f"but found {actual} in _ATLAS_REGISTRY"
                )
        # Check 3: if expected_technique null, rationale must be non-empty
        else:
            if not expected_rationale or not expected_rationale.strip():
                failures.append(
                    f"  {action}: atlas_technique=null requires non-empty "
                    f"atlas_rationale (canonical-13 table is incomplete)"
                )

    if strict_namespace:
        failures.extend(_verify_namespace(atlas))

    if failures:
        gate_name = "canonical-13" + (" + namespace" if strict_namespace else "")
        print(
            f"verify-atlas-binding.py: FAIL "
            f"({len(failures)} {gate_name} failure(s))",
            file=sys.stderr,
        )
        for f in failures:
            print(f, file=sys.stderr)
        return 1

    if not quiet:
        gate_summary = (
            f"all {len(_CANONICAL_13)} canonical-13 actions bound"
            + (
                f" + {len({tid for tid in atlas.values()})} unique IDs "
                f"namespace-classified"
                if strict_namespace
                else ""
            )
        )
        print(f"verify-atlas-binding.py: PASS ({gate_summary})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--quiet", action="store_true", help="suppress PASS output")
    parser.add_argument(
        "--strict-namespace",
        action="store_true",
        help=(
            "PLAN-095 Wave A.8 — assert every unique technique-ID in "
            "_ATLAS_REGISTRY has a namespace classification (atlas | "
            "attack-enterprise) in _NAMESPACE_REGISTRY. Catches silent "
            "drift when new bindings are added without declaring namespace."
        ),
    )
    args = parser.parse_args()
    return verify(quiet=args.quiet, strict_namespace=args.strict_namespace)


if __name__ == "__main__":
    sys.exit(main())
