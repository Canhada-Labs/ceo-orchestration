#!/usr/bin/env python3
"""PLAN-046 Cluster 1.4 — code-nav sidecar MCP bridge (scaffold).

**Status:** STUB. Runnable stdlib scaffold that exposes the MCP
interface without implementing the Tree-sitter backend. Full
implementation is adopter-driven (see spec).

Inspiration: ``code-review-graph`` + ``token-savior`` tree-sitter
work (clean-room; no code lifted).

Purpose
-------
Semantic code graph served as an MCP sidecar so sub-agents can
navigate the codebase (find definitions, references, callers)
without re-parsing files in every turn.

Two backends:

1. **stdlib fallback** (this scaffold) — regex-based coarse index.
   Accurate enough for Python/TypeScript function and class names;
   no call-graph.
2. **tree-sitter upgrade** (adopter-opt-in) — adopter installs
   ``tree-sitter`` + language grammars and wires them via
   ``CodeNavBackend.tree_sitter``. This scaffold provides the
   interface; the backend body is a TODO marker.

Contract
--------
``CodeNavBridge(project_root: Path, backend: str = "stdlib")``
with three query methods:

- ``find_definition(symbol) -> List[Location]``
- ``find_references(symbol) -> List[Location]``
- ``list_symbols(path) -> List[Symbol]``

All methods are read-only, fail-open (return empty list on error),
and bounded (max 500 hits per query to keep MCP responses small).

MCP protocol
------------
This file is a scaffold, not a live MCP server. The protocol layer
(JSON-RPC over stdio per ADR-062 pattern) is stubbed at
``serve_mcp()`` and exits on the first line with a deprecation
notice pointing adopters at the promotion runbook.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --------------------------------------------------------------------------
# Data classes
# --------------------------------------------------------------------------


@dataclass
class Location:
    path: str
    line: int
    col: int = 0

    def as_dict(self) -> Dict[str, object]:
        return {"path": self.path, "line": self.line, "col": self.col}


@dataclass
class Symbol:
    name: str
    kind: str  # "function" | "class" | "method" | "unknown"
    location: Location

    def as_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "kind": self.kind,
            "location": self.location.as_dict(),
        }


# --------------------------------------------------------------------------
# Stdlib regex backend — coarse but dependency-free
# --------------------------------------------------------------------------

_PY_DEF_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<kind>def|class|async\s+def)\s+(?P<name>[A-Za-z_]\w*)",
    flags=re.MULTILINE,
)
_TS_DEF_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?:export\s+)?"
    r"(?P<kind>function|class|const|let|var|interface|type)\s+"
    r"(?P<name>[A-Za-z_$][\w$]*)",
    flags=re.MULTILINE,
)
_MAX_HITS = 500


def _kind_normalize(raw: str) -> str:
    raw = raw.strip().lower()
    if raw.startswith("async"):
        return "function"
    if raw in {"def", "function"}:
        return "function"
    if raw == "class":
        return "class"
    if raw in {"const", "let", "var"}:
        return "variable"
    if raw == "interface":
        return "interface"
    if raw == "type":
        return "type"
    return "unknown"


def _scan_file_stdlib(path: Path) -> List[Symbol]:
    """Regex scan. Returns up to _MAX_HITS symbols."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    hits: List[Symbol] = []
    for regex in (_PY_DEF_RE, _TS_DEF_RE):
        for match in regex.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            hits.append(Symbol(
                name=match.group("name"),
                kind=_kind_normalize(match.group("kind")),
                location=Location(path=str(path), line=line, col=len(match.group("indent"))),
            ))
            if len(hits) >= _MAX_HITS:
                return hits
    return hits


# --------------------------------------------------------------------------
# Bridge
# --------------------------------------------------------------------------


class CodeNavBridge:
    """Stub bridge exposing the 3 query methods."""

    def __init__(self, project_root: Path, backend: str = "stdlib") -> None:
        self.project_root = project_root.resolve()
        self.backend = backend
        if backend not in {"stdlib", "tree_sitter"}:
            raise ValueError(f"unknown backend: {backend!r}")
        self._cache_scan: Dict[str, List[Symbol]] = {}

    # ---- internals

    def _iter_source_files(self) -> List[Path]:
        """All .py, .ts, .tsx, .js under project_root, capped at 5000."""
        seen: List[Path] = []
        for ext in ("py", "ts", "tsx", "js"):
            for entry in self.project_root.rglob(f"*.{ext}"):
                # Skip obvious build / vendor dirs
                parts = {p.lower() for p in entry.parts}
                if parts & {"node_modules", ".venv", "venv", "__pycache__", "dist", "build"}:
                    continue
                seen.append(entry)
                if len(seen) >= 5000:
                    return seen
        return seen

    def _scan(self, path: Path) -> List[Symbol]:
        key = str(path)
        if key in self._cache_scan:
            return self._cache_scan[key]
        if self.backend == "tree_sitter":
            symbols = self._scan_tree_sitter(path)  # TODO: adopter implements
        else:
            symbols = _scan_file_stdlib(path)
        self._cache_scan[key] = symbols
        return symbols

    def _scan_tree_sitter(self, path: Path) -> List[Symbol]:
        """TODO: adopter-owned.

        Install ``tree-sitter`` + language grammar packages, call the
        parser, walk the AST, emit ``Symbol`` objects. Falls back to
        stdlib if unavailable.
        """
        try:
            import tree_sitter  # type: ignore[import-not-found]  # noqa: F401
        except ImportError:
            return _scan_file_stdlib(path)
        # Placeholder: adopter fills in here.
        return _scan_file_stdlib(path)

    # ---- public API

    def find_definition(self, symbol: str) -> List[Location]:
        if not symbol:
            return []
        out: List[Location] = []
        for src in self._iter_source_files():
            for sym in self._scan(src):
                if sym.name == symbol:
                    out.append(sym.location)
                    if len(out) >= _MAX_HITS:
                        return out
        return out

    def find_references(self, symbol: str) -> List[Location]:
        """Stdlib backend: grep-like scan over source files.

        Tree-sitter backend would use the AST to eliminate false
        positives (e.g. same name used for a local variable).
        """
        if not symbol:
            return []
        pattern = re.compile(r"\b" + re.escape(symbol) + r"\b")
        out: List[Location] = []
        for src in self._iter_source_files():
            try:
                text = src.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                out.append(Location(path=str(src), line=line))
                if len(out) >= _MAX_HITS:
                    return out
        return out

    def list_symbols(self, path: str) -> List[Symbol]:
        try:
            p = (self.project_root / path).resolve()
            p.relative_to(self.project_root)  # bounds check
        except (ValueError, OSError):
            return []
        if not p.is_file():
            return []
        return list(self._scan(p))


# --------------------------------------------------------------------------
# MCP stub
# --------------------------------------------------------------------------


def serve_mcp() -> int:  # pragma: no cover — scaffold only
    """Stub MCP server. Emits a notice and exits."""
    sys.stderr.write(
        "[code_nav_bridge] MCP serving is staged; adopter wiring required. "
        "See `.claude/plans/PLAN-046/staged-code/"
        "cluster-1.4-code-nav-sidecar-spec.md` §MCP handshake for the "
        "stdio protocol framing + promotion runbook.\n"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(serve_mcp())
