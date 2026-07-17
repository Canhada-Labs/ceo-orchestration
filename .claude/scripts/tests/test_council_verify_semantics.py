"""PLAN-156-FOLLOWUP W2 (F2 + F7 + pipe fold) — council verify-semantics invariants.

CI mirror per debate consensus C7: the node fixture harness
(``scripts/tests/test-council-fixture.mjs``) runs in NO CI job, so the
CI-load-bearing assertions live here as stdlib-Python STRUCTURAL checks
over the workflow/command TEXT (the workflow is JS; executing it needs
node, which the pytest matrix does not have — the .mjs stays the local
behavioral harness).

Semantic invariants asserted (consensus C1 / C5-semantics):

1. F2 state SPLIT — ``verify_failed`` (refuter crash/null/omitted key,
   a SYNTHESIZED default) is a distinct state from an EXPLICIT refuter
   ``unverifiable`` judgment. The pre-fix collapsed default
   (``|| { verdict: 'unverifiable' ... }``) must be GONE — this test is
   RED against the pre-fix canonical file by construction.
2. CLEAN condition — CLEAN requires ``lanes >= 3 AND confirmed == 0 AND
   verify_failed == 0``; wholesale refuter failure therefore degrades
   automatically, while a legitimate explicit refute-everything CLEAN
   stays reachable.
3. Report loudness — the ``verify_failed`` count is surfaced in the
   Verdict section instruction, in a top-of-report banner, and in
   ``stats`` / the return value.
4. Pipe fold — the external-lane brief instructs redact-and-send as ONE
   ``redactor | vendor-cli`` pipeline under ``set -o pipefail`` (a
   skipped/failed redaction cannot yield a sendable prompt).
5. F7 scope threading — the workflow reads ``args.scope`` and threads it
   into lane briefs + the return value (it always did: the S270 defect
   is at the INVOCATION layer), and the ``/council`` command template
   binds ``$ARGUMENTS`` into ``args.scope`` explicitly, mandatory-scope,
   fail-loud on a missing scope (the actual F7 fix).

Target resolution (pre- vs post-ceremony): the fixed files are STAGED
under ``.claude/plans/PLAN-156-FOLLOWUP/staged/root/`` until the sentinel
ceremony lands them canonically. Resolution order:

  1. ``$CEO_FU_STAGED_ROOT`` (repo-relative or absolute) if set —
     set it to ``.`` to force the canonical files explicitly;
  2. the default staged root, if it holds the staged workflow;
  3. the repo root (canonical) — post-ceremony mode.

LANDING NOTE (load-bearing): ``staged/`` is GITIGNORED (.gitignore:17),
so the staged copies never reach CI — commit THIS test file in the SAME
ceremony commit that lands the canonical council-audit.js + council.md
fixes (the PLAN-156 SENT-GK-F pattern), never before. Committed earlier,
CI resolves to the unfixed canonical files and goes red by design.
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if not _HOOKS_DIR.is_dir():  # staged layout: walk up to the real repo
    for _cand in Path(__file__).resolve().parents:
        if (_cand / ".git").exists():
            _HOOKS_DIR = _cand / ".claude" / "hooks"
            break
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402
_DEFAULT_STAGED_REL = ".claude/plans/PLAN-156-FOLLOWUP/staged/root"
_WORKFLOW_REL = ".claude/workflows/council-audit.js"
_COMMAND_REL = ".claude/commands/council.md"
_ENV_VAR = "CEO_FU_STAGED_ROOT"


def _resolve_root(repo_root: Optional[Path] = None) -> Path:
    """Resolve the root the council files are read from (staged vs canonical)."""
    repo = repo_root if repo_root is not None else _REPO_ROOT
    env = os.environ.get(_ENV_VAR)
    if env:
        p = Path(env)
        return p if p.is_absolute() else (repo / p)
    staged = repo / _DEFAULT_STAGED_REL
    if (staged / _WORKFLOW_REL).is_file():
        return staged
    return repo


def _workflow_text() -> str:
    return (_resolve_root() / _WORKFLOW_REL).read_text(encoding="utf-8")


def _command_text() -> str:
    return (_resolve_root() / _COMMAND_REL).read_text(encoding="utf-8")


class TestF2StateSplit(TestEnvContext):
    """verify_failed is a crash, unverifiable is a judgment — never the same label."""

    def setUp(self) -> None:
        super().setUp()
        self.src = _workflow_text()

    def test_synthesized_default_is_verify_failed(self) -> None:
        # The missing-verdict branch synthesizes verify_failed, not unverifiable.
        self.assertRegex(self.src, r"verdict:\s*'verify_failed'")
        self.assertIn("refuter crash/null/omitted key", self.src)

    def test_old_collapsed_default_removed(self) -> None:
        # Pre-fix: `verdictByKey[g.key] || { verdict: 'unverifiable', ... }`
        # collapsed refuter-crash into an explicit judgment. RED on the
        # pre-fix canonical file by construction.
        self.assertNotRegex(self.src, r"\|\|\s*\{\s*verdict:\s*'unverifiable'")
        self.assertNotIn("no verifier verdict returned", self.src)

    def test_explicit_unverifiable_judgment_preserved(self) -> None:
        # The refuter can still EXPLICITLY judge unverifiable (schema enum
        # unchanged), and it never emits verify_failed itself — that label
        # is synthesized only.
        self.assertRegex(
            self.src, r"enum:\s*\['confirmed',\s*'refuted',\s*'unverifiable'\]")
        self.assertNotRegex(self.src, r"enum:\s*\[[^\]]*verify_failed")

    def test_refuter_crash_still_lands_on_empty_verdicts(self) -> None:
        # A refuter error/null resolves to {verdicts: []} (never a throw),
        # which flows into the synthesized verify_failed default per group.
        self.assertRegex(self.src, r"catch\(\(\) => \(\{ verdicts: \[\] \}\)\)")
        self.assertRegex(self.src, r"\.then\(\(r\) => r \|\| \{ verdicts: \[\] \}\)")


class TestCleanCondition(TestEnvContext):
    """CLEAN <=> lanes>=3 AND confirmed==0 AND verify_failed==0 (mechanical)."""

    def setUp(self) -> None:
        super().setUp()
        self.src = _workflow_text()
        m = re.search(r"const mechanicalVerdict =[\s\S]*?'DEGRADED'\)", self.src)
        self.assertIsNotNone(m, "mechanicalVerdict expression not found")
        self.block = m.group(0)

    def test_clean_requires_zero_verify_failed(self) -> None:
        self.assertIn("availableLanes.length >= 3", self.block)
        self.assertIn("verifyFailed.length === 0", self.block)

    def test_confirmed_still_wins_as_findings(self) -> None:
        # Split, not rename: confirmed>0 must still yield FINDINGS, so a
        # legitimate refute-everything run (explicit verdicts, confirmed==0,
        # verify_failed==0) keeps CLEAN reachable via the counts branch.
        self.assertIn("'FINDINGS'", self.block)
        self.assertIn("'CLEAN'", self.block)

    def test_verify_failed_groups_are_counted(self) -> None:
        self.assertRegex(
            self.src,
            r"const verifyFailed = verified\.filter\(\(g\) => g\.verdict === 'verify_failed'\)")


class TestReportLoudness(TestEnvContext):
    """The verify_failed COUNT is surfaced prominently, with its reason."""

    def setUp(self) -> None:
        super().setUp()
        self.src = _workflow_text()

    def test_verdict_section_instruction_names_verify_failed(self) -> None:
        self.assertRegex(self.src, r"## Verdict[^\n]*verify_failed")

    def test_top_of_report_banner(self) -> None:
        self.assertIn("VERIFY_FAILED = ${verifyFailed.length}", self.src)
        self.assertIn("NEVER evidence-checked", self.src)

    def test_stats_and_return_value_carry_the_count(self) -> None:
        self.assertIn("verify_failed: verifyFailed.length", self.src)
        self.assertIn("verify_failed_findings: verifyFailed", self.src)


class TestPipeFold(TestEnvContext):
    """Redact-and-send is ONE pipeline under pipefail — never two steps."""

    def setUp(self) -> None:
        super().setUp()
        self.src = _workflow_text()

    def test_single_pipeline_under_pipefail(self) -> None:
        self.assertIn("set -o pipefail", self.src)
        self.assertRegex(
            self.src, r"codex_egress_redact\.py --outgoing \| \$\{cli\}")

    def test_two_step_send_removed(self) -> None:
        self.assertNotIn("Feed the REDACTED brief to:", self.src)

    def test_no_unpiped_outgoing_invocation(self) -> None:
        # Every `--outgoing` redactor invocation in the lane instruction
        # must feed the vendor CLI directly.
        strays = re.findall(
            r"codex_egress_redact\.py --outgoing(?! \| \$\{cli\})", self.src)
        self.assertEqual(strays, [])


class TestF7ScopeThreading(TestEnvContext):
    """Workflow threads args.scope (always did); the COMMAND now binds it."""

    def setUp(self) -> None:
        super().setUp()
        self.src = _workflow_text()
        self.cmd = _command_text()

    def test_workflow_reads_and_threads_scope(self) -> None:
        # The C1 anchors: args.scope read, lane brief carries SCOPE, return
        # value carries scope. These were present pre-fix (F7 is NOT a
        # workflow defect) and must never regress.
        self.assertIn("args.scope", self.src)
        self.assertIn("SCOPE: ${SCOPE}", self.src)
        self.assertRegex(self.src, r"scope:\s*SCOPE")

    def test_command_binds_dollar_arguments(self) -> None:
        # The S270 invocation-layer defect: council.md never referenced
        # $ARGUMENTS, so nothing bound the operator's typed scope to
        # args.scope and the workflow's `.` default widened egress.
        self.assertIn("$ARGUMENTS", self.cmd)
        self.assertIn("parsed from $ARGUMENTS", self.cmd)

    def test_command_scope_is_mandatory_and_fail_loud(self) -> None:
        self.assertIn("MANDATORY", self.cmd)
        self.assertIn("STOP and ask", self.cmd)
        # The untethered placeholder invocation is gone.
        self.assertNotIn('scope: "<scope>"', self.cmd)

    def test_command_pre_echo_and_post_run_assertion(self) -> None:
        self.assertIn("council scope =", self.cmd)
        self.assertIn("Post-run scope assertion", self.cmd)


class TestRootResolution(TestEnvContext):
    """The staged-root parameterization itself (env > default-staged > canonical)."""

    def test_env_override_wins(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.dict(os.environ, {_ENV_VAR: td}):
                self.assertEqual(_resolve_root(), Path(td))

    def test_env_relative_is_repo_relative(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            with mock.patch.dict(os.environ, {_ENV_VAR: "some/staged"}):
                self.assertEqual(_resolve_root(repo), repo / "some/staged")

    def test_default_staged_when_present_else_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            with mock.patch.dict(os.environ):
                os.environ.pop(_ENV_VAR, None)
                # No staged workflow -> canonical (repo root).
                self.assertEqual(_resolve_root(repo), repo)
                # Staged workflow present -> staged root.
                staged_wf = repo / _DEFAULT_STAGED_REL / _WORKFLOW_REL
                staged_wf.parent.mkdir(parents=True)
                staged_wf.write_text("marker", encoding="utf-8")
                self.assertEqual(_resolve_root(repo), repo / _DEFAULT_STAGED_REL)


if __name__ == "__main__":
    unittest.main()
