"""Reality ledger: environment."""

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

class _EnvVarReadFinder(ast.NodeVisitor):
    """Walk AST collecting env var names actually READ at runtime.

    Recognised forms:
      - os.environ.get('VAR'[, default])
      - os.environ['VAR']
      - os.getenv('VAR'[, default])
      - subprocess.run(env={'VAR': ...})  (treated as USE — call-site sets var
        for child process; not a "read" but proves runtime wiring.)
      - dict-key string literals inside subprocess.run(env={...}) calls.
    """

    def __init__(self) -> None:
        self.read_vars: set = set()

    @staticmethod
    def _arg_str(node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        # os.getenv('VAR') / os.getenv('VAR', default)
        # os.environ.get('VAR')
        func = node.func
        # Resolve attribute chain
        attr_chain: List[str] = []
        cur: Any = func
        while isinstance(cur, ast.Attribute):
            attr_chain.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            attr_chain.append(cur.id)
        attr_chain.reverse()
        chain = ".".join(attr_chain)

        if chain in ("os.getenv", "getenv") and node.args:
            v = self._arg_str(node.args[0])
            if v:
                self.read_vars.add(v)
        elif chain in ("os.environ.get", "environ.get") and node.args:
            v = self._arg_str(node.args[0])
            if v:
                self.read_vars.add(v)
        # subprocess.run(env={...})
        elif chain.endswith("subprocess.run") or chain.endswith(".run") or chain == "run":
            for kw in node.keywords or []:
                if kw.arg == "env" and isinstance(kw.value, ast.Dict):
                    for k in kw.value.keys:
                        v = self._arg_str(k)
                        if v:
                            self.read_vars.add(v)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:  # noqa: N802
        # os.environ['VAR']  -> Subscript(value=Attribute(os.environ), slice=Constant)
        val = node.value
        attr_chain: List[str] = []
        cur: Any = val
        while isinstance(cur, ast.Attribute):
            attr_chain.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            attr_chain.append(cur.id)
        attr_chain.reverse()
        chain = ".".join(attr_chain)
        if chain in ("os.environ", "environ"):
            slc: Any = node.slice
            if isinstance(slc, ast.Constant) and isinstance(slc.value, str):
                self.read_vars.add(slc.value)
        self.generic_visit(node)


def _ast_collect_runtime_env_reads(py_files: List[Path]) -> Dict[str, List[str]]:
    """Returns {VAR_NAME: [posix_path, ...]} of files that actually read it."""
    out: Dict[str, List[str]] = {}
    for f in py_files:
        try:
            source = f.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(f))
        except (OSError, SyntaxError):
            continue
        finder = _EnvVarReadFinder()
        try:
            finder.visit(tree)
        except Exception:
            continue
        for v in finder.read_vars:
            out.setdefault(v, []).append(_to_repo_rel(f))
    return out


def _doc_collect_documented_env_vars(md_files: List[Path]) -> Dict[str, List[str]]:
    """Returns {VAR_NAME: [posix_path:line, ...]} of doc files that mention it.

    Detection forms:
      - backtick-wrapped UPPER_SNAKE token  (`CEO_MODEL_DOWNSHIFT`)
      - shell assignment                    (CEO_MODEL_DOWNSHIFT=1)
      - dollar-sign reference               ($CEO_MODEL_DOWNSHIFT)

    Only names matching `_ENV_PREFIX_RE` survive — this is the explicit
    "convention floor" that prevents the planning-doc false positives
    (`_KNOWN_ACTIONS`, `VETO_HARDCODE`, `STDOUT`, etc.).
    """
    out: Dict[str, List[str]] = {}
    regexes = (_BACKTICK_ENV_RE, _SHELL_ASSIGN_RE, _DOLLAR_VAR_RE)
    for f in md_files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for rgx in regexes:
                for m in rgx.finditer(line):
                    v = m.group(1)
                    if _ENV_PREFIX_RE.match(v) and _is_plausible_env_var(v):
                        out.setdefault(v, []).append(f"{_to_repo_rel(f)}:{lineno}")
    return out


def _is_plausible_env_var(name: str) -> bool:
    """Filter common false positives (file extensions, Python keywords, etc.).

    Heuristics:
      - must start with letter, contain underscore OR be ≥6 chars
      - exclude common all-caps tokens that are not env vars (HTTP, JSON, etc.)
    """
    if not name:
        return False
    if len(name) < 4:
        return False
    if "_" not in name and len(name) < 6:
        return False
    EXCLUDE = {
        "HTTP", "HTTPS", "JSON", "YAML", "TOML", "MARKDOWN", "TODO", "FIXME",
        "NOTE", "WARNING", "ERROR", "INFO", "DEBUG", "TRACE",
        "README", "CLAUDE", "VERSION", "CHANGELOG", "PROTOCOL", "PYTHON",
        "ASCII", "UTF", "UNICODE", "REGEX", "GOTCHA", "OPTIONAL", "REQUIRED",
        "EXAMPLE", "CRITICAL", "MANDATORY", "ALL_CAPS", "UPPER_CASE",
        "GLOBAL", "LOCAL", "STATIC", "DYNAMIC", "PUBLIC", "PRIVATE",
        "TRUE", "FALSE", "NONE", "NULL", "UNDEFINED",
    }
    if name in EXCLUDE:
        return False
    return True


def detect_runtime_read_missing(
    *,
    repo_root: Path,
    explicit_env_vars: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Detector #1.

    For each env var documented in a .md under `docs/` or `.claude/`,
    AST-scan `.claude/scripts` + `.claude/hooks` for runtime reads.
    Variables documented but NEVER actually read → finding.
    """
    findings: List[Dict[str, Any]] = []

    md_roots = [repo_root / "docs", repo_root / ".claude"]
    py_roots = [repo_root / ".claude" / "scripts", repo_root / ".claude" / "hooks"]
    md_files = _iter_md_files(md_roots, repo_root=repo_root)
    py_files = _iter_python_files(py_roots, repo_root=repo_root)

    documented = _doc_collect_documented_env_vars(md_files)
    runtime = _ast_collect_runtime_env_reads(py_files)

    if explicit_env_vars:
        documented = {v: documented.get(v, []) for v in explicit_env_vars}

    runtime_vars = set(runtime.keys())

    for var, doc_locations in sorted(documented.items()):
        if not doc_locations:
            continue
        if var in runtime_vars:
            continue
        # Cosmetic mentions only; no AST-level read
        first_loc = doc_locations[0]
        evidence = (
            f"0 enforcement reads; {len(doc_locations)} cosmetic mention(s) filtered"
        )
        finding = _build_finding(
            detector="runtime_read_missing",
            severity=DETECTOR_REGISTRY["runtime_read_missing"]["severity"],
            confidence=0.95,
            claim_source_path=first_loc,
            expected_evidence=(
                f"ast_scan_for_env_var('{var}', "
                "target_dirs=['.claude/scripts','.claude/hooks'], "
                "exclude=['task-route.py','reality-ledger.py',"
                "'owner-ceremony/archive/**'])"
            ),
            actual_evidence=evidence,
            advisory_action="either wire the runtime read or amend the doc",
            extra={"env_var": var, "doc_locations": doc_locations[:5]},
        )
        findings.append(finding)
    return findings


# ---------------------------------------------------------------------------
# Detector #2 — installable_claim_drift
# ---------------------------------------------------------------------------


__all__ = ['_EnvVarReadFinder', '_ast_collect_runtime_env_reads', '_doc_collect_documented_env_vars', '_is_plausible_env_var', 'detect_runtime_read_missing']
