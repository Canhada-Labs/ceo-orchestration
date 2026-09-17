#!/usr/bin/env python3
"""test_refs.py — normalise test references to canonical pytest node ids (PLAN-190 W3).

Why
---
A consumer's pipeline produced nine false "PROVAS-INCOMPLETAS" because the
implementer listed FUNCTION NAMES under ``testes_novos`` while the matcher
compared FILE PATHS. The order (2026-09-17): "Padronizar enumerações e
referências de testes; nomes ambíguos não devem ser aceitos silenciosamente."

What it accepts (one reference per line / argument)
---------------------------------------------------
* a file path: ``tests/unit/test_x.py``                      → every test node in it
* a node id:  ``tests/unit/test_x.py::test_a`` or ``::Cls::test_a``
* a bare function: ``test_a`` — resolved by scanning the tree; AMBIGUOUS if it
  is defined in more than one file (rc 3, candidates listed), NOT FOUND if none
* ``Cls.test_a`` / ``Cls::test_a`` — a method inside a class

Resolution is static (``ast``), never executes tests. Output is a JSON object
``{"resolved": {ref: [nodeid, ...]}, "errors": [{"ref", "kind", "candidates"}]}``.

Commands::

    test_refs.py normalize --repo . REF [REF ...]        rc 0 all resolved · rc 3 any error
    test_refs.py match --repo . --declared FILE --proved FILE
        compares two reference lists AFTER normalisation; prints missing / extra
        node ids; rc 0 when every declared test is proved · rc 3 otherwise

Stdlib only, Python >= 3.9. Read-only.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

TEST_FILE_GLOBS = ("**/test_*.py", "**/*_test.py")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def _iter_test_files(repo: Path) -> List[Path]:
    out: List[Path] = []
    for pattern in TEST_FILE_GLOBS:
        for p in repo.glob(pattern):
            if any(part in SKIP_DIRS for part in p.relative_to(repo).parts):
                continue
            out.append(p)
    return sorted(set(out))


def _nodes_in_file(path: Path) -> List[Tuple[Optional[str], str]]:
    """(class_name or None, function_name) for every test function/method."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []
    nodes: List[Tuple[Optional[str], str]] = []
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"):
            nodes.append((None, n.name))
        elif isinstance(n, ast.ClassDef) and n.name.startswith("Test"):
            for m in n.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name.startswith("test"):
                    nodes.append((n.name, m.name))
        elif isinstance(n, ast.ClassDef):
            # unittest.TestCase subclasses without the Test prefix still hold tests
            for m in n.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name.startswith("test"):
                    nodes.append((n.name, m.name))
    return nodes


class Index:
    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.by_file: Dict[str, List[str]] = {}
        self.by_func: Dict[str, List[str]] = {}
        for f in _iter_test_files(repo):
            rel = f.relative_to(repo).as_posix()
            ids: List[str] = []
            for cls, fn in _nodes_in_file(f):
                nid = "%s::%s::%s" % (rel, cls, fn) if cls else "%s::%s" % (rel, fn)
                ids.append(nid)
                self.by_func.setdefault(fn, []).append(nid)
                if cls:
                    self.by_func.setdefault("%s.%s" % (cls, fn), []).append(nid)
                    self.by_func.setdefault("%s::%s" % (cls, fn), []).append(nid)
            self.by_file[rel] = ids

    def resolve(self, ref: str) -> Tuple[List[str], Optional[Dict[str, object]]]:
        ref = ref.strip()
        if not ref:
            return [], {"ref": ref, "kind": "empty", "candidates": []}
        if "::" in ref and ("/" in ref.split("::", 1)[0] or ref.split("::", 1)[0].endswith(".py")):
            path, rest = ref.split("::", 1)
            rel = Path(path).as_posix()
            ids = self.by_file.get(rel)
            if ids is None:
                return [], {"ref": ref, "kind": "file-not-found", "candidates": []}
            exact = [i for i in ids if i == "%s::%s" % (rel, rest)]
            if exact:
                return exact, None
            tail = [i for i in ids if i.endswith("::" + rest.split("::")[-1])]
            if len(tail) == 1:
                return tail, None
            return [], {"ref": ref, "kind": "node-not-found" if not tail else "ambiguous", "candidates": tail}
        if ref.endswith(".py") or "/" in ref:
            rel = Path(ref).as_posix()
            ids = self.by_file.get(rel)
            if ids is None:
                return [], {"ref": ref, "kind": "file-not-found", "candidates": []}
            if not ids:
                return [], {"ref": ref, "kind": "file-has-no-tests", "candidates": []}
            return list(ids), None
        cands = self.by_func.get(ref, [])
        if not cands:
            return [], {"ref": ref, "kind": "not-found", "candidates": []}
        if len(set(cands)) > 1:
            return [], {"ref": ref, "kind": "ambiguous", "candidates": sorted(set(cands))}
        return [cands[0]], None


def normalize(repo: Path, refs: List[str]) -> Dict[str, object]:
    idx = Index(repo)
    resolved: Dict[str, List[str]] = {}
    errors: List[Dict[str, object]] = []
    for r in refs:
        ids, err = idx.resolve(r)
        if err:
            errors.append(err)
        else:
            resolved[r] = ids
    return {"resolved": resolved, "errors": errors}


def _read_refs(path: str) -> List[str]:
    p = Path(path).expanduser()
    text = p.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        data = json.loads(text)
        return [str(x) for x in data]
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("normalize")
    p.add_argument("--repo", default=".")
    p.add_argument("refs", nargs="+")
    q = sub.add_parser("match")
    q.add_argument("--repo", default=".")
    q.add_argument("--declared", required=True, help="file: one ref per line, or a JSON list")
    q.add_argument("--proved", required=True, help="file: one ref per line, or a JSON list")
    args = ap.parse_args(argv)
    repo = Path(os.path.expanduser(args.repo)).resolve()
    if args.cmd == "normalize":
        out = normalize(repo, args.refs)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 3 if out["errors"] else 0
    declared = normalize(repo, _read_refs(args.declared))
    proved = normalize(repo, _read_refs(args.proved))
    d_ids = {i for ids in declared["resolved"].values() for i in ids}  # type: ignore[union-attr]
    p_ids = {i for ids in proved["resolved"].values() for i in ids}  # type: ignore[union-attr]
    out = {
        "declared_errors": declared["errors"],
        "proved_errors": proved["errors"],
        "missing_proof": sorted(d_ids - p_ids),
        "proved_but_not_declared": sorted(p_ids - d_ids),
        "declared": len(d_ids),
        "proved": len(p_ids),
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    ok = not out["missing_proof"] and not declared["errors"] and not proved["errors"]
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
