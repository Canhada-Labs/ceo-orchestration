"""Contract tests for ``status.py`` -> the CLIs it shells out to (FD-24).

The defect (measured S362): ``status._health_verdict()`` ran
``audit-query.py health --as-json``. That flag does not exist (the real one
is ``--json``), argparse exits rc=2 ("unrecognized arguments"), and the
function's fail-open ``return "UNKNOWN"`` swallowed it -- so ``/status``
reported ``health: UNKNOWN`` on EVERY run, forever, with no signal.

The CLASS is "a caller hard-codes a flag the callee never had", hidden by a
fail-open wrapper. Curing the instance (one string) leaves the class open, so
this file adds a CONTRACT test instead: it walks ``status.py``'s AST, finds
every ``subprocess`` call, and checks every literal ``--flag`` against the
REAL ``--help`` of the program it calls (``audit-query.py <subcmd> --help``,
``gh run list --help``). A flag the callee does not list fails the test with
the file:line of the call.

Anti-vacuous controls (the test must not go green because the extractor saw
nothing):
- the extractor MUST find the ``audit-query.py health`` call by name;
- any ``subprocess`` call shape the extractor cannot model (non-literal argv,
  unknown binary, ``from subprocess import ...``) FAILS rather than passes;
- a synthetic ``--as-json`` argv is run through the same oracle and must be
  flagged, while ``--json`` must pass (positive control independent of
  whatever ``status.py`` currently contains).

Behaviour test: ``_health_verdict()`` is driven against SYNTHETIC audit logs
in a temp dir (``CEO_AUDIT_LOG_PATH``; never the live log, never the real
``$HOME``) and must return the verdict the data implies, not the
fail-open ``UNKNOWN``.

Env-hygiene (check-test-env-hygiene.py): every class subclasses
``TestEnvContext`` and mutates the environment only through ``TestEnvContext``
plumbing / ``unittest.mock.patch.dict`` (never a raw ``os.environ[...] =``).
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

STATUS_PY = REPO_ROOT / ".claude" / "scripts" / "status.py"

# External (non-repo) programs status.py is allowed to call. Anything else is
# "unmodelled": the test fails so a new dependency is added here consciously.
_EXTERNAL_ALLOWED = frozenset({"gh"})
_SUBPROCESS_FUNCS = frozenset({"run", "Popen", "call", "check_call", "check_output"})
_OS_SHELLOUTS = frozenset({"system", "popen"})


class _Interp:
    """Sentinel for ``sys.executable`` in an argv list."""


_INTERP = _Interp()


class _Call(NamedTuple):
    lineno: int
    kind: str  # "repo-script" | "external" | "unmodelled"
    program: str  # absolute script path, binary name, or a reason string
    args: List[Optional[str]]  # literal args after the program; None = dynamic


def _load_status():
    spec = importlib.util.spec_from_file_location("status_under_test", str(STATUS_PY))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# AST extraction of every subprocess call in status.py
# ---------------------------------------------------------------------------

def _eval(node: ast.AST, scopes: List[Dict[str, ast.AST]], roots: Dict[str, Path],
          depth: int = 0) -> Any:
    """Tiny static evaluator: str / Path / ``_INTERP`` / ``None`` (= dynamic)."""
    if depth > 8:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
            and node.value.id == "sys" and node.attr == "executable"):
        return _INTERP
    if isinstance(node, ast.Name):
        if node.id in roots:  # roots win: REPO_ROOT etc. are not statically derivable
            return roots[node.id]
        for scope in scopes:  # innermost function scope first
            if node.id in scope:
                return _eval(scope[node.id], scopes, roots, depth + 1)
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _eval(node.left, scopes, roots, depth + 1)
        right = _eval(node.right, scopes, roots, depth + 1)
        if isinstance(left, Path) and isinstance(right, str):
            return left / right
        return None
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in ("str", "Path") and len(node.args) == 1):
        inner = _eval(node.args[0], scopes, roots, depth + 1)
        if inner is None or inner is _INTERP:
            return None
        return str(inner) if node.func.id == "str" else Path(inner)
    return None


def _is_subprocess_call(node: ast.Call) -> bool:
    f = node.func
    return (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
            and f.value.id == "subprocess" and f.attr in _SUBPROCESS_FUNCS)


def _is_os_shellout(node: ast.Call) -> bool:
    f = node.func
    return (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
            and f.value.id == "os"
            and (f.attr in _OS_SHELLOUTS or f.attr.startswith("exec")
                 or f.attr.startswith("spawn")))


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _classify(node: ast.Call, scopes: List[Dict[str, ast.AST]],
              roots: Dict[str, Path]) -> _Call:
    if not node.args or not isinstance(node.args[0], ast.List):
        return _Call(node.lineno, "unmodelled", "argv is not a list literal", [])
    vals: List[Any] = []
    for el in node.args[0].elts:
        vals.append(None if isinstance(el, ast.Starred)
                    else _eval(el, scopes, roots))
    if vals and vals[0] is _INTERP:
        prog = vals[1] if len(vals) > 1 else None
        rest = vals[2:]
    else:
        prog = vals[0] if vals else None
        rest = vals[1:]
    args = [a if isinstance(a, str) else None for a in rest]
    if isinstance(prog, (str, Path)):
        p = Path(prog)
        if p.is_absolute() and p.is_file() and _inside(p, REPO_ROOT):
            return _Call(node.lineno, "repo-script", str(p), args)
        if isinstance(prog, str) and "/" not in prog and prog in _EXTERNAL_ALLOWED:
            return _Call(node.lineno, "external", prog, args)
        return _Call(node.lineno, "unmodelled", "program %r" % (str(prog),), args)
    return _Call(node.lineno, "unmodelled", "program is not statically resolvable", args)


def _extract_calls(roots: Dict[str, Path]) -> List[_Call]:
    tree = ast.parse(STATUS_PY.read_text(encoding="utf-8"), filename=str(STATUS_PY))
    module_scope: Dict[str, ast.AST] = {}
    for stmt in tree.body:
        if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)):
            module_scope[stmt.targets[0].id] = stmt.value
    calls: List[_Call] = []

    class _Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.stack: List[Dict[str, ast.AST]] = [module_scope]

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            scope: Dict[str, ast.AST] = {}
            for n in ast.walk(node):
                if (isinstance(n, ast.Assign) and len(n.targets) == 1
                        and isinstance(n.targets[0], ast.Name)):
                    scope[n.targets[0].id] = n.value
            self.stack.append(scope)
            self.generic_visit(node)
            self.stack.pop()

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            if node.module == "subprocess":
                calls.append(_Call(node.lineno, "unmodelled",
                                   "`from subprocess import ...` form", []))

        def visit_Call(self, node: ast.Call) -> None:
            if _is_subprocess_call(node):
                calls.append(_classify(node, list(reversed(self.stack)), roots))
            elif _is_os_shellout(node):
                calls.append(_Call(node.lineno, "unmodelled", "os shell-out", []))
            self.generic_visit(node)

    _Visitor().visit(tree)
    return calls


# ---------------------------------------------------------------------------
# The oracle: literal flags vs the callee's REAL --help
# ---------------------------------------------------------------------------

def _split_argv(args: List[Optional[str]]) -> Tuple[List[str], List[str], List[str]]:
    """Split a literal argv tail into (subcommand chain, root flags, leaf flags).

    Flags before the first positional belong to the root parser; the first
    run of positionals is the subcommand chain; flags after it belong to the
    deepest subparser (positionals after that are flag values and ignored).
    """
    root_flags: List[str] = []
    chain: List[str] = []
    leaf_flags: List[str] = []
    state = 0
    for tok in args:
        if tok is None:  # dynamic element: cannot be checked statically
            continue
        is_flag = tok.startswith("-") and len(tok) > 1
        if state == 0:
            if is_flag:
                root_flags.append(tok.split("=", 1)[0])
            else:
                chain.append(tok)
                state = 1
        elif state == 1:
            if is_flag:
                leaf_flags.append(tok.split("=", 1)[0])
                state = 2
            else:
                chain.append(tok)
        elif is_flag:
            leaf_flags.append(tok.split("=", 1)[0])
    return chain, root_flags, leaf_flags


def _has_flag(help_text: str, flag: str) -> bool:
    return re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(flag), help_text) is not None


def _help(base: List[str], chain: List[str]) -> str:
    cmd = base + chain + ["--help"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                          cwd=str(REPO_ROOT))
    if proc.returncode != 0:
        raise AssertionError(
            "cannot resolve the callee's help: %s exited rc=%d: %s"
            % (" ".join(cmd), proc.returncode,
               (proc.stderr or proc.stdout).strip()[:300]))
    return proc.stdout + proc.stderr


def _unknown_flags(base: List[str], args: List[Optional[str]]) -> List[str]:
    """Flags in ``args`` that the callee's real ``--help`` does not list."""
    chain, root_flags, leaf_flags = _split_argv(args)
    root_help = _help(base, [])
    bad = [f for f in root_flags if not _has_flag(root_help, f)]
    if leaf_flags:
        leaf_help = _help(base, chain)
        bad += [f for f in leaf_flags if not _has_flag(leaf_help, f)]
    return bad


def _repo_base(script: str) -> List[str]:
    return [sys.executable, script]


class StatusSubprocessContractTest(TestEnvContext):
    """Every literal flag status.py passes to a CLI exists on that CLI."""

    def setUp(self) -> None:
        super().setUp()
        self.mod = _load_status()
        self.roots = {
            "REPO_ROOT": Path(self.mod.REPO_ROOT),
            "SCRIPTS_DIR": Path(self.mod.SCRIPTS_DIR),
            "PLANS_DIR": Path(self.mod.PLANS_DIR),
        }
        self.calls = _extract_calls(self.roots)

    def test_extractor_finds_the_audit_query_health_call(self) -> None:
        # Anti-vacuous control: a rename/refactor that hides the call from the
        # extractor must fail HERE, not leave the contract test trivially green.
        found = [
            c for c in self.calls
            if c.kind == "repo-script"
            and Path(c.program).name == "audit-query.py"
            and "health" in c.args
        ]
        self.assertTrue(
            found,
            "extractor did not see an `audit-query.py health` subprocess call in "
            "status.py (calls seen: %r)" % (self.calls,))

    def test_no_subprocess_call_shape_is_unmodelled(self) -> None:
        bad = ["status.py:%d %s" % (c.lineno, c.program)
               for c in self.calls if c.kind == "unmodelled"]
        self.assertEqual(
            bad, [],
            "status.py has subprocess calls this contract test cannot verify; "
            "extend the extractor / _EXTERNAL_ALLOWED consciously: %r" % (bad,))

    def test_repo_script_calls_only_use_flags_the_target_accepts(self) -> None:
        repo_calls = [c for c in self.calls if c.kind == "repo-script"]
        self.assertTrue(repo_calls, "no repo-script subprocess call extracted")
        problems: List[str] = []
        for c in repo_calls:
            for flag in _unknown_flags(_repo_base(c.program), c.args):
                problems.append(
                    "status.py:%d %s %s -> unknown flag %r (the callee's real "
                    "--help does not list it)"
                    % (c.lineno, Path(c.program).name,
                       " ".join(a for a in c.args if a is not None), flag))
        self.assertEqual(problems, [], "\n".join(problems))

    def test_external_cli_calls_only_use_flags_the_tool_accepts(self) -> None:
        ext = [c for c in self.calls if c.kind == "external"]
        gh = shutil.which("gh")
        if ext and gh is None:
            self.skipTest("gh CLI not installed; external flag contract not checked")
        problems: List[str] = []
        for c in ext:
            for flag in _unknown_flags([gh], c.args):
                problems.append("status.py:%d %s %s -> unknown flag %r"
                                % (c.lineno, c.program,
                                   " ".join(a for a in c.args if a is not None), flag))
        self.assertEqual(problems, [], "\n".join(problems))

    def test_oracle_flags_the_as_json_regression(self) -> None:
        # Positive control for the oracle itself, independent of status.py's
        # current content: the exact FD-24 argv must be flagged, the cure and
        # a plain valid argv must not, a typo must be.
        base = _repo_base(str(REPO_ROOT / ".claude" / "scripts" / "audit-query.py"))
        self.assertEqual(_unknown_flags(base, ["health", "--as-json"]), ["--as-json"])
        self.assertEqual(_unknown_flags(base, ["health", "--json"]), [])
        self.assertEqual(_unknown_flags(base, ["--json", "health"]), [])
        self.assertEqual(_unknown_flags(base, ["health", "--jsno"]), ["--jsno"])


class HealthVerdictBehaviourTest(TestEnvContext):
    """``_health_verdict()`` reports what the audit data says, not UNKNOWN."""

    def setUp(self) -> None:
        super().setUp()
        self.mod = _load_status()
        # TestEnvContext already points CEO_AUDIT_LOG_PATH at this synthetic path.
        self.log = self.audit_dir / "audit-log.jsonl"

    def _write(self, entries: List[Dict[str, Any]]) -> None:
        with open(self.log, "w", encoding="utf-8") as fh:
            for e in entries:
                fh.write(json.dumps(e) + "\n")

    @staticmethod
    def _spawns(n: int, skill: str) -> List[Dict[str, Any]]:
        return [{"ts": "2026-10-02T00:00:%02dZ" % i, "action": "agent_spawn",
                 "skill": skill, "has_profile": True, "has_file_assignment": True}
                for i in range(n)]

    def test_pass_verdict_from_compliant_synthetic_log(self) -> None:
        self._write(self._spawns(10, "public-api-design"))
        self.assertEqual(self.mod._health_verdict(), "PASS")

    def test_fail_verdict_from_noncompliant_synthetic_log(self) -> None:
        self._write(self._spawns(10, "unknown"))
        self.assertEqual(self.mod._health_verdict(), "FAIL")

    def test_no_data_verdict_from_empty_log(self) -> None:
        self._write([])
        self.assertEqual(self.mod._health_verdict(), "NO_DATA")

    def test_unknown_stays_the_fail_open_answer_when_the_script_is_missing(self) -> None:
        # The fail-open contract is deliberate and must survive the fix.
        with tempfile.TemporaryDirectory(prefix="fd24-noscripts-") as empty:
            with mock.patch.object(self.mod, "SCRIPTS_DIR", Path(empty)):
                self.assertEqual(self.mod._health_verdict(), "UNKNOWN")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
