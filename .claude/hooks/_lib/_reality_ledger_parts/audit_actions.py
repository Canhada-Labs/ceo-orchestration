"""Reality ledger: audit actions."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Tuple

from .constants import *  # shared declaration defaults

def _read_known_actions(audit_emit_path: Path) -> set:
    """Parse `_KNOWN_ACTIONS = { ... }` from audit_emit.py via AST."""
    try:
        source = audit_emit_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(audit_emit_path))
    except (OSError, SyntaxError):
        return set()
    out: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "_KNOWN_ACTIONS":
                    val = node.value
                    if isinstance(val, (ast.Set, ast.List, ast.Tuple)):
                        for elt in val.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                out.add(elt.value)
    if out:
        return out

    # Resolve only the literal roster passed to the facade's imported binder.
    # Target files are parsed as data; none is imported or executed.
    binders = {
        alias.asname or alias.name
        for node in tree.body if isinstance(node, ast.ImportFrom)
        and node.module == "_lib._audit_emit_parts"
        for alias in node.names if alias.name == "install"
    }
    roster = []
    for node in tree.body:
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
            continue
        call = node.value
        if not (isinstance(call.func, ast.Name) and call.func.id in binders
                and len(call.args) >= 2 and isinstance(call.args[1], (ast.Tuple, ast.List))):
            continue
        for item in call.args[1].elts:
            if isinstance(item, ast.Constant) and isinstance(item.value, str) and item.value.isidentifier():
                roster.append(item.value)

    parts = audit_emit_path.parent / "_audit_emit_parts"
    parsed = {}

    def parse_part(name):
        if name not in parsed:
            try:
                parsed[name] = ast.parse((parts / (name + ".py")).read_text(
                    encoding="utf-8", errors="replace"))
            except (OSError, SyntaxError):
                parsed[name] = None
        return parsed[name]

    def resolve(name, symbol, visiting):
        key = (name, symbol)
        if key in visiting:
            return None
        part = parse_part(name)
        if part is None:
            return None
        visiting = visiting | {key}
        for stmt in part.body:
            if isinstance(stmt, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == symbol for target in stmt.targets
            ):
                return evaluate(name, stmt.value, visiting)
            if isinstance(stmt, ast.ImportFrom) and stmt.level == 1 and stmt.module and stmt.module.isidentifier():
                for alias in stmt.names:
                    if (alias.asname or alias.name) == symbol and alias.name.isidentifier():
                        return resolve(stmt.module, alias.name, visiting)
        return None

    def evaluate(name, expr, visiting):
        if isinstance(expr, (ast.Set, ast.List, ast.Tuple)):
            if all(isinstance(item, ast.Constant) and isinstance(item.value, str) for item in expr.elts):
                return {item.value for item in expr.elts}
        elif isinstance(expr, ast.Name):
            return resolve(name, expr.id, visiting)
        elif isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.BitOr):
            left = evaluate(name, expr.left, visiting)
            right = evaluate(name, expr.right, visiting)
            if left is not None and right is not None:
                return left | right
        return None

    for name in roster:
        part = parse_part(name)
        if part is None:
            continue
        exports = resolve(name, "__all__", set())
        if exports is not None and "_KNOWN_ACTIONS" in exports:
            actions = resolve(name, "_KNOWN_ACTIONS", set())
            if actions is not None:
                out.update(actions)
    return out


class _EmitActionFinder(ast.NodeVisitor):
    """Walk AST collecting action= literals from emit_generic(...) Call nodes.

    AST-level avoids false positives in docstrings / regex examples / comments
    that the regex form inevitably catches (Codex precedent: docstring example
    literal `emit_generic(action="name", ...)` got flagged as phantom).
    """

    def __init__(self) -> None:
        # action_name -> list of (lineno,)
        self.actions: Dict[str, List[int]] = {}

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        # Only consider calls whose callee ends in `emit_generic`.
        func = node.func
        callee_chain: List[str] = []
        cur: Any = func
        while isinstance(cur, ast.Attribute):
            callee_chain.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            callee_chain.append(cur.id)
        callee_chain.reverse()
        last = callee_chain[-1] if callee_chain else ""
        if last == "emit_generic":
            # Find action= keyword OR first positional
            action_val: Optional[str] = None
            for kw in node.keywords or []:
                if kw.arg == "action" and isinstance(kw.value, ast.Constant) \
                        and isinstance(kw.value.value, str):
                    action_val = kw.value.value
                    break
            if action_val is None and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    action_val = first.value
            if action_val:
                self.actions.setdefault(action_val, []).append(node.lineno)
        self.generic_visit(node)


def _scan_emitted_actions(py_files: List[Path], *, repo_root: Path) -> Dict[str, List[str]]:
    """Find action names emitted in code via emit_generic(...) — AST-level only.

    Skips files whose path includes `tests/` to avoid catching fixture
    strings / mocked event payloads. Skips files inside `_lib/audit_emit.py`
    itself (its own dispatch table must reference all actions; not a phantom).

    `repo_root` is required because we compute the relative path from the
    *target* root (which may be a fixture root in tests), not the
    framework root. Without this, a fixture under `…/tests/fixtures/…`
    in the framework checkout was always filtered out as "tests/".
    """
    out: Dict[str, List[str]] = {}
    for f in py_files:
        try:
            rel = str(f.resolve().relative_to(repo_root.resolve())).replace(os.sep, "/")
        except (ValueError, OSError):
            rel = _to_repo_rel(f)
        # Exclude tests + audit_emit.py itself
        if "/tests/" in ("/" + rel) or rel.endswith("audit_emit.py"):
            continue
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(f))
        except (OSError, SyntaxError):
            continue
        finder = _EmitActionFinder()
        try:
            finder.visit(tree)
        except Exception:
            continue
        for action, linenos in finder.actions.items():
            for ln in linenos:
                out.setdefault(action, []).append(f"{rel}:{ln}")
    return out


def _legacy_scan_emitted_actions(py_files: List[Path]) -> Dict[str, List[str]]:
    """Backward-compat wrapper used in unit-tests of the original signature."""
    return _scan_emitted_actions(py_files, repo_root=_REPO_ROOT)


def detect_audit_action_phantom(
    *,
    repo_root: Path,
) -> List[Dict[str, Any]]:
    """Detector #6.

    Phantom = action emitted in code but missing from `_KNOWN_ACTIONS`
    (silent drop precedent: Codex S76 `skill_bootstrap_used` regression).
    """
    findings: List[Dict[str, Any]] = []
    audit_emit_path = repo_root / ".claude" / "hooks" / "_lib" / "audit_emit.py"
    if not audit_emit_path.exists():
        return findings

    known = _read_known_actions(audit_emit_path)
    py_roots = [repo_root / ".claude" / "scripts", repo_root / ".claude" / "hooks"]
    py_files = _iter_python_files(py_roots, repo_root=repo_root)
    emitted = _scan_emitted_actions(py_files, repo_root=repo_root)

    # Phantom: emitted but not registered
    phantoms = sorted(set(emitted.keys()) - known)
    for action in phantoms:
        first_loc = emitted[action][0]
        finding = _build_finding(
            detector="audit_action_phantom",
            severity=DETECTOR_REGISTRY["audit_action_phantom"]["severity"],
            confidence=0.99,
            claim_source_path=first_loc,
            expected_evidence=(
                f"action {action!r} present in audit_emit._KNOWN_ACTIONS"
            ),
            actual_evidence=(
                f"emitted in {len(emitted[action])} site(s); not registered"
            ),
            advisory_action=(
                "add action to _KNOWN_ACTIONS via KERNEL ceremony OR rename "
                "the emit call site"
            ),
            extra={"action": action, "emit_sites": emitted[action][:5]},
        )
        findings.append(finding)
    return findings


# ---------------------------------------------------------------------------
# Detector #7 — estimate_drift  (PLAN-078 Wave 2)
# ---------------------------------------------------------------------------
#
# On plans whose `status: done` transition fired, compares the original
# `estimate.compute_hours` + `estimate.owner_physical_min` against the
# observed actuals (commit time-span + GPG-signed-commit count + manual
# override). Finding emitted when |drift_factor| ≥ 1.2 in either axis.
#
# Implementation discipline (Codex re-pass + plan §4.2):
#   - SINGLE batched `git log --pretty=%H,%aI --name-only` (~1 subprocess
#     call, NOT 1-per-plan) — see _git_log_paths().
#   - `created` field preferred over `created_at` (PLAN-SCHEMA §2 use).
#   - actual_owner_physical_min derived from GPG-signed commit count + an
#     optional `actual_owner_physical_min:` plan-frontmatter override
#     (clamped 0..10000; non-int → fail-open warn).
#   - severity bands: low <1.5×, medium 1.5-2×, high >2×.
#   - systematic_bias_direction: emitted ONLY in the run-summary recommend
#     event when N≥5 plans drift same direction.
#   - CSV append at `.claude/scripts/local/calibration-history.csv`
#     (gitignored). Each row keyed by `<plan_id>,<run_iso8601>` so re-runs
#     are idempotent (existing rows are NOT duplicated).
#   - Bypass: `CEO_REALITY_LEDGER_DETECTOR_07=0`.
#
# Output: List of finding dicts (run_detectors aggregator handles render +
# emit). Each finding embeds plan-level deltas in `_extra` for forensics.

_PLAN_FILE_RE = re.compile(r"^PLAN-(\d{3,4})-.*\.md$")
_HOURS_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)")
_SINGLE_NUM_RE = re.compile(r"\d+(?:\.\d+)?")
_ESTIMATE_KEY_RE = re.compile(r"^estimate:\s*$")
_ESTIMATE_INDENT_RE = re.compile(r"^\s+(\w+):\s*(.+?)\s*$")
_TOP_KEY_RE = re.compile(r"^[A-Za-z_]")



__all__ = ['_read_known_actions', '_EmitActionFinder', '_scan_emitted_actions', '_legacy_scan_emitted_actions', 'detect_audit_action_phantom', '_PLAN_FILE_RE', '_HOURS_RANGE_RE', '_SINGLE_NUM_RE', '_ESTIMATE_KEY_RE', '_ESTIMATE_INDENT_RE', '_TOP_KEY_RE']
