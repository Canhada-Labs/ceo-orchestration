"""F1 smoke — codex_egress_redact.py CLI fail-CLOSED contract (PLAN-156-FOLLOWUP W1).

Proves BOTH acceptance paths of debate C4, by running the CLI as a
SUBPROCESS with the LITERAL `council-audit.js:145` command string
(`python3 <path> --outgoing`, never `python3 -m`):

  1. Happy path — a planted secret on stdin comes back REDACTED on
     stdout, exit 0.
  2. Induced failure — undecodable stdin, and env/monkeypatched import
     breakage (a poisoned `argparse` on PYTHONPATH) → exit NONZERO and
     stdout EMPTY. The input is NEVER echoed on any error path (VETO
     line).

Plus: an AST guard that the library `redact()` body is untouched by the
F1 diff (single-pass invariant preserved — mirrors
`TestSinglePassInvariant`), and a sandbox-canonical-layout test that
proves the EXACT post-ceremony invocation shape (dirname import-shim
branch, no PYTHONPATH) pre-ceremony.

Target selection (ceremony flip):
  * env `CEO_FU_STAGED_ROOT` SET  → run the STAGED copy under that root
    (empty value → default `.claude/plans/PLAN-156-FOLLOWUP/staged/root`).
    The staged tree carries ONLY the changed file, so the real sibling
    `_lib` is supplied via PYTHONPATH for the direct-run tests.
  * env UNSET → POST-CEREMONY mode: run the canonical
    `.claude/hooks/_lib/codex_egress_redact.py` with NO PYTHONPATH
    (self-sufficiency proof). If the canonical file is still byte-
    identical to the recorded pre-fix base (`.basepin` sha256 match),
    the suite SKIPS loudly — that is the pre-ceremony state, not a
    landed-but-broken state (a landed file always differs from base).

stdlib-only, Python >=3.9. Uses TestEnvContext for env isolation.

This file is STAGED (mirror lives at `.claude/scripts/tests/
test_redactor_cli_matrix.py` for 3.9-3.12 matrix coverage, debate C7);
the ceremony lands it at `.claude/hooks/_lib/tests/test_redactor_cli.py`.
"""

from __future__ import annotations

import ast
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional


def _find_repo_root(start: Path) -> Path:
    """Walk up from ``start`` to the first dir containing ``.git``.

    Location-independent: this file runs from the staged tree
    (pre-ceremony) AND from ``.claude/hooks/_lib/tests/`` (post-ceremony);
    the staged tree has no ``.git``, so the walk lands on the real root
    in both cases.
    """
    cur = start
    while True:
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            raise RuntimeError("repo root (.git) not found above %s" % start)
        cur = cur.parent


_REPO_ROOT = _find_repo_root(Path(__file__).resolve())
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
_REAL_LIB_DIR = _HOOKS_DIR / "_lib"

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_STAGED_ROOT_ENV = "CEO_FU_STAGED_ROOT"
_DEFAULT_STAGED_ROOT = ".claude/plans/PLAN-156-FOLLOWUP/staged/root"
_CANONICAL_REL = ".claude/hooks/_lib/codex_egress_redact.py"

# Captured at MODULE IMPORT time: TestEnvContext snapshots/strips env in
# setUp, so reading inside a test method would race the isolation.
_STAGED_MODE_RAW: Optional[str] = os.environ.get(_STAGED_ROOT_ENV)


def _target_rel_path() -> str:
    """Repo-relative path of the CLI under test (ceremony flip point)."""
    if _STAGED_MODE_RAW is None:
        return _CANONICAL_REL  # POST-CEREMONY mode
    root = _STAGED_MODE_RAW.strip() or _DEFAULT_STAGED_ROOT
    return root.rstrip("/") + "/" + _CANONICAL_REL


_TARGET_REL = _target_rel_path()
_TARGET_ABS = _REPO_ROOT / _TARGET_REL

#: The LITERAL invocation shape from council-audit.js:145 — in
#: POST-CEREMONY mode this string is exactly
#: `python3 .claude/hooks/_lib/codex_egress_redact.py --outgoing`.
_LITERAL_CMD = "python3 " + _TARGET_REL + " --outgoing"

# Planted fake AWS access key (family `aws_access_key`,
# regex \bAKIA[0-9A-Z]{16}\b). Built by CONCATENATION so no contiguous
# secret-shaped literal exists in this file or in any command line
# (the secret-in-command bash gate is fail-CLOSED by design).
_PLANTED_SECRET = "AKIA" + "ABCDEFGHIJ" + "KLMNOP"
_REDACTION_LABEL = "[REDACTED:aws_access_key]"


def _preceremony_skip_reason() -> Optional[str]:
    """Non-None iff POST-CEREMONY mode is selected but F1 has not landed.

    Primary check: canonical sha256 == the `.basepin`-recorded PRE-fix
    base (a landed F1 always changes the canonical bytes, so this cannot
    mask a landed-but-broken state). Clean-clone fallback: `staged/` is
    GITIGNORED (.gitignore:17 — the PLAN-155 staged-gitignored lesson),
    so CI clones carry no basepin; there, decide by the `_cli_main`
    marker. Residual (accepted): a post-land regression that DELETES
    `_cli_main` would skip here rather than fail — that removal needs its
    own canonical ceremony, whose W1 Check
    (`printf 'x' | ... --outgoing`) is the covering gate.
    """
    if _STAGED_MODE_RAW is not None:
        return None
    canonical = _REPO_ROOT / _CANONICAL_REL
    basepin = _REPO_ROOT / (_DEFAULT_STAGED_ROOT + "/" + _CANONICAL_REL + ".basepin")
    if basepin.exists():
        pinned_sha = basepin.read_text(encoding="utf-8").split()[0]
        cur_sha = hashlib.sha256(canonical.read_bytes()).hexdigest()
        if cur_sha == pinned_sha:
            return (
                "pre-ceremony: canonical redactor still matches the recorded "
                "F1 base (.basepin sha256) — set CEO_FU_STAGED_ROOT to test "
                "the staged copy"
            )
        return None
    if "def _cli_main(" not in canonical.read_text(encoding="utf-8"):
        return (
            "pre-ceremony (clean clone, no staged basepin): F1 CLI not yet "
            "landed in the canonical redactor — strict once the ceremony lands"
        )
    return None


def _env_overrides() -> Dict[str, str]:
    """PYTHONPATH override, spread OVER os.environ at every spawn site.

    Staged mode supplies the real `_lib`; post-ceremony mode NEUTRALIZES
    PYTHONPATH (empty string contributes only cwd, never the `_lib` dir —
    the self-sufficiency proof holds even if the parent shell exports one).
    An override rather than a `pop` because the PLAN-119 WS-C
    audit-isolation gate requires the literal `env={**os.environ, ...}`
    spread at the spawn site.
    """
    if _STAGED_MODE_RAW is not None:
        return {"PYTHONPATH": str(_REAL_LIB_DIR)}
    return {"PYTHONPATH": ""}


def _run_cli(
    input_bytes: bytes,
    cmd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
) -> "subprocess.CompletedProcess":
    """Run the CLI as a shell subprocess from the repo root."""
    return subprocess.run(
        cmd if cmd is not None else _LITERAL_CMD,
        shell=True,
        cwd=cwd if cwd is not None else str(_REPO_ROOT),
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, **_env_overrides(), **(env or {})},
        timeout=60,
    )


def _function_def(path: Path, name: str) -> ast.FunctionDef:
    """Return the top-level FunctionDef ``name`` from ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError("no top-level function %r in %s" % (name, path))


def _count_calls_named(node: ast.AST, name: str) -> int:
    """Count ast.Call nodes whose func is exactly ``name`` (attr or bare)."""
    count = 0
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            func = sub.func
            if isinstance(func, ast.Attribute) and func.attr == name:
                count += 1
            elif isinstance(func, ast.Name) and func.id == name:
                count += 1
    return count


class TestRedactorCliF1(TestEnvContext):
    """F1 CLI contract: literal invocation, fail-CLOSED, never echo."""

    def setUp(self) -> None:
        super().setUp()
        reason = _preceremony_skip_reason()
        if reason:
            self.skipTest(reason)
        self.assertTrue(
            _TARGET_ABS.exists(),
            "CLI under test not found: %s" % _TARGET_ABS,
        )

    # -- happy path -------------------------------------------------------

    def test_happy_path_literal_command_redacts_planted_secret(self):
        """Planted secret in → redacted out; exit 0; benign text preserved."""
        payload = (
            "council lane brief — benign context line\n"
            + _PLANTED_SECRET
            + "\ntrailing benign line\n"
        ).encode("utf-8")
        proc = _run_cli(payload)
        out = proc.stdout.decode("utf-8")
        self.assertEqual(
            proc.returncode,
            0,
            "happy path must exit 0; stderr=%r" % proc.stderr[:500],
        )
        self.assertNotIn(_PLANTED_SECRET, out, "planted secret leaked to stdout")
        self.assertIn(_REDACTION_LABEL, out, "redaction label missing from stdout")
        self.assertIn("trailing benign line", out, "benign text must be preserved")

    def test_empty_stdin_exits_zero_with_empty_stdout(self):
        """Empty in → empty out, exit 0 (library empty-string contract)."""
        proc = _run_cli(b"")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, b"")

    # -- fail-CLOSED paths --------------------------------------------------

    def test_missing_direction_flag_fails_closed(self):
        """No --outgoing → nonzero exit, EMPTY stdout, input never echoed."""
        cmd = _LITERAL_CMD.replace(" --outgoing", "")
        proc = _run_cli(_PLANTED_SECRET.encode("utf-8"), cmd=cmd)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, b"", "stdout must be EMPTY on error")
        self.assertNotIn(_PLANTED_SECRET.encode("utf-8"), proc.stderr)
        self.assertIn(b"--outgoing is required", proc.stderr)

    def test_unknown_flag_fails_closed(self):
        """argparse usage error → nonzero exit, EMPTY stdout."""
        proc = _run_cli(
            _PLANTED_SECRET.encode("utf-8"), cmd=_LITERAL_CMD + " --bogus-flag"
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, b"", "stdout must be EMPTY on error")
        self.assertNotIn(_PLANTED_SECRET.encode("utf-8"), proc.stderr)

    def test_induced_failure_undecodable_stdin_fails_closed(self):
        """Invalid UTF-8 on stdin → exit != 0 AND stdout EMPTY (VETO line)."""
        payload = b"\xff\xfe\xfa" + _PLANTED_SECRET.encode("utf-8")
        proc = _run_cli(payload)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, b"", "stdout must be EMPTY on error")
        # Never echo: the planted secret must not surface on stderr either.
        self.assertNotIn(_PLANTED_SECRET.encode("utf-8"), proc.stderr)
        self.assertIn(b"FATAL", proc.stderr)

    def test_induced_failure_poisoned_import_fails_closed(self):
        """Monkeypatched env breakage (poisoned argparse on PYTHONPATH) →
        exit != 0 AND stdout EMPTY; the planted stdin secret appears NOWHERE.
        """
        with tempfile.TemporaryDirectory(prefix="ceo-f1-poison-") as poison:
            (Path(poison) / "argparse.py").write_text(
                "raise RuntimeError('poisoned-by-f1-smoke')\n", encoding="utf-8"
            )
            existing = _env_overrides().get("PYTHONPATH") or ""
            proc = _run_cli(
                _PLANTED_SECRET.encode("utf-8"),
                env={
                    "PYTHONPATH": (
                        poison if not existing else poison + os.pathsep + existing
                    )
                },
            )
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, b"", "stdout must be EMPTY on error")
        self.assertNotIn(_PLANTED_SECRET.encode("utf-8"), proc.stderr)
        # The controlled fail-CLOSED wrapper fired (exit 3, typed FATAL) —
        # not an interpreter-level crash.
        self.assertEqual(proc.returncode, 3)
        self.assertIn(b"FATAL: RuntimeError", proc.stderr)

    # -- post-ceremony invocation shape, provable pre-ceremony --------------

    def test_sandbox_canonical_layout_literal_command_no_pythonpath(self):
        """The EXACT council-audit.js:145 command string works with the file
        in its canonical layout and NO PYTHONPATH — proves the import shim's
        dirname branch (run-as-file next to its sibling).
        """
        with tempfile.TemporaryDirectory(prefix="ceo-f1-sandbox-") as sandbox:
            lib = Path(sandbox) / ".claude" / "hooks" / "_lib"
            lib.mkdir(parents=True)
            shutil.copy2(str(_REAL_LIB_DIR / "secret_patterns.py"), str(lib))
            shutil.copy2(str(_TARGET_ABS), str(lib / "codex_egress_redact.py"))
            env = {"PYTHONPATH": ""}  # neutralized: only cwd, never real _lib
            proc = _run_cli(
                _PLANTED_SECRET.encode("utf-8"),
                cmd="python3 .claude/hooks/_lib/codex_egress_redact.py --outgoing",
                env=env,
                cwd=sandbox,
            )
        self.assertEqual(
            proc.returncode,
            0,
            "canonical-layout run failed; stderr=%r" % proc.stderr[:500],
        )
        out = proc.stdout.decode("utf-8")
        self.assertNotIn(_PLANTED_SECRET, out)
        self.assertIn(_REDACTION_LABEL, out)

    # -- library redact() untouched (single-pass conformance) ---------------

    def test_redact_function_ast_untouched_and_single_pass(self):
        """The F1 diff must not touch redact(): its AST is identical to the
        canonical file's, and the R1 S-Sec-1 single-pass shape holds
        (exactly ONE scan_and_redact call, ZERO standalone scan calls).
        """
        target_fn = _function_def(_TARGET_ABS, "redact")
        self.assertEqual(_count_calls_named(target_fn, "scan_and_redact"), 1)
        self.assertEqual(_count_calls_named(target_fn, "scan"), 0)
        canonical_fn = _function_def(_REPO_ROOT / _CANONICAL_REL, "redact")
        self.assertEqual(
            ast.dump(target_fn),
            ast.dump(canonical_fn),
            "redact() body diverged from canonical — F1 must not refactor it",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
