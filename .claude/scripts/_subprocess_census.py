"""AST inventory of direct subprocess test calls, with a content-based ratchet.

This is a static census, not proof of control-flow coverage: it recognises
imports/aliases, local command assignments and assertions in the same lexical
scope. Dynamic dispatch and timeout values hidden inside **kwargs require
manual inspection. Existing findings are debt, never an exemption for new sites.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional


TEST_ROOTS = (
    ".claude/hooks/tests", ".claude/scripts/tests", ".claude/scripts/swarm/tests",
    "scripts/tests", "tests", "templates/oidc-proxy/tests",
)
KINDS = ("python-rc", "timeout-group")
SCOPE_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
GROUP_HELPER = ".claude/scripts/tests/_subprocess_helpers.py"


class Finding(NamedTuple):
    kind: str
    path: str
    scope: str
    line: int
    fingerprint: str

    @property
    def key(self) -> str:
        return f"{self.path}::{self.scope}::{self.fingerprint}"


def _nodes(scope: ast.AST) -> Iterable[ast.AST]:
    """Walk this scope only; a sibling's assertions cannot discharge its debt."""
    yield scope
    for child in ast.iter_child_nodes(scope):
        if not isinstance(child, SCOPE_TYPES):
            yield from _nodes(child)


def _scopes(tree: ast.AST, prefix: str = "<module>") -> Iterable[tuple]:
    yield prefix, tree
    for node in _nodes(tree):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, SCOPE_TYPES):
                yield from _scopes(child, f"{prefix}.{child.name}")


def _imports(nodes: Iterable[ast.AST], inherited: dict) -> dict:
    result = dict(inherited)
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                result[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                result[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return result


def _name(node: ast.AST, aliases: dict) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        return f"{_name(node.value, aliases)}.{node.attr}"
    return ""


def _assignments(nodes: list) -> list:
    result = []
    for node in nodes:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if isinstance(target, (ast.Name, ast.Attribute)):
                result.append((target, node.value, node.lineno))
    return result


def _python_command(node: Optional[ast.AST], aliases: dict, assignments: list, seen: tuple = ()) -> bool:
    if node is None:
        return False
    for part in ast.walk(node):
        if _name(part, aliases) == "sys.executable":
            return True
        if isinstance(part, ast.Name) and part.id not in seen:
            candidates = [
                (value, line) for target, value, line in assignments
                if isinstance(target, ast.Name) and target.id == part.id and line < part.lineno
            ]
            if candidates:
                value, _ = max(candidates, key=lambda item: item[1])
                if _python_command(value, aliases, assignments, seen + (part.id,)):
                    return True
    return False


def _result_name(call: ast.Call, parents: dict, aliases: dict) -> str:
    parent = parents.get(call)
    if isinstance(parent, ast.Assign) and len(parent.targets) == 1:
        return _name(parent.targets[0], aliases)
    if isinstance(parent, ast.AnnAssign):
        return _name(parent.target, aliases)
    if isinstance(parent, ast.withitem) and parent.optional_vars is not None:
        return _name(parent.optional_vars, aliases)
    return ""


def _assertions(nodes: list) -> Iterable[ast.AST]:
    for node in nodes:
        if isinstance(node, ast.Assert):
            yield node.test
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr.startswith("assert"):
                for arg in node.args:
                    yield arg


def _checks_rc(call: ast.Call, nodes: list, parents: dict, aliases: dict, assignments: list) -> bool:
    result = _result_name(call, parents, aliases)
    reassigned = [
        line for target, _, line in assignments
        if result and _name(target, aliases) == result and line > call.lineno
    ]
    end = min(reassigned, default=float("inf"))
    for assertion in _assertions(nodes):
        for part in ast.walk(assertion):
            if not isinstance(part, ast.Attribute) or part.attr != "returncode":
                continue
            if part.value is call:
                return True
            if result and call.lineno <= part.lineno < end and _name(part.value, aliases) == result:
                return True
    return False


def _classify(call: ast.Call, nodes: list, parents: dict, aliases: dict, assignments: list) -> list:
    name = _name(call.func, aliases)
    subprocess_call = name in ("subprocess.run", "subprocess.Popen")
    kinds = []
    if subprocess_call:
        command = call.args[0] if call.args else next((k.value for k in call.keywords if k.arg == "args"), None)
        if _python_command(command, aliases, assignments) and not _checks_rc(call, nodes, parents, aliases, assignments):
            kinds.append("python-rc")
    communicate = isinstance(call.func, ast.Attribute) and call.func.attr == "communicate"
    timeout = any(k.arg == "timeout" for k in call.keywords) or (communicate and len(call.args) >= 2)
    if timeout and (subprocess_call or communicate):
        kinds.append("timeout-group")
    return kinds


def scan_source(source: str, path: str = "test_example.py") -> List[Finding]:
    tree = ast.parse(source, filename=path)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    module_aliases = _imports(_nodes(tree), {})
    findings = []
    for scope, body in _scopes(tree):
        nodes = list(_nodes(body))
        aliases = _imports(nodes, module_aliases)
        assignments = _assignments(nodes)
        occurrences: Dict[str, int] = {}
        for call in (n for n in nodes if isinstance(n, ast.Call)):
            kinds = _classify(call, nodes, parents, aliases, assignments)
            if not kinds:
                continue
            digest = hashlib.sha256(ast.dump(call, include_attributes=False).encode()).hexdigest()[:20]
            occurrences[digest] = occurrences.get(digest, 0) + 1
            fingerprint = f"{digest}:{occurrences[digest]}"
            for kind in kinds:
                findings.append(Finding(kind, path, scope, call.lineno, fingerprint))
    return findings


def _walk_error(error: OSError) -> None:
    raise error


def scan_tree(root: Path) -> List[Finding]:
    result = []
    for relative in TEST_ROOTS:
        start = root / relative
        if not start.exists():
            continue
        for directory, folders, names in os.walk(start, onerror=_walk_error):
            folders[:] = sorted(name for name in folders if name != "__pycache__")
            for name in sorted(names):
                if not name.endswith(".py"):
                    continue
                path = Path(directory) / name
                relative_path = path.relative_to(root).as_posix()
                # Only the implementation that owns session creation and
                # cleanup is exempt. Imported test helpers remain in scope.
                if relative_path == GROUP_HELPER:
                    continue
                if path.is_symlink():
                    raise ValueError(f"symlink test source: {path.relative_to(root)}")
                result.extend(scan_source(path.read_text(encoding="utf-8"), relative_path))
    return sorted(result)


def baseline_rows(findings: Iterable[Finding]) -> dict:
    """Group by source file; row keys survive line-only edits, not new calls."""
    rows: Dict[str, dict] = {kind: {} for kind in KINDS}
    for finding in findings:
        rows[finding.kind].setdefault(finding.path, []).append(f"{finding.scope}::{finding.fingerprint}")
    return rows


def new_findings(findings: Iterable[Finding], baseline: dict) -> List[Finding]:
    return [
        finding for finding in findings
        if f"{finding.scope}::{finding.fingerprint}" not in baseline.get(finding.kind, {}).get(finding.path, [])
    ]


def load_baseline(path: Path) -> dict:
    baseline = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(baseline, dict) or set(baseline) != set(KINDS):
        raise ValueError("baseline must contain both census kinds")
    for paths in baseline.values():
        if not isinstance(paths, dict):
            raise ValueError("baseline kind must map paths to site lists")
        for sites in paths.values():
            if not isinstance(sites, list) or any(not isinstance(site, str) for site in sites):
                raise ValueError("baseline sites must be strings")
    return baseline
