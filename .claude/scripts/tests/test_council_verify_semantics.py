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
4. Vendor transports (PLAN-161 C2/C3, superseding the universal pipe
   fold) — ONE redaction chokepoint, TWO transports: the codex lane
   keeps the ``redactor | vendor-cli`` pipe fold under ``set -o
   pipefail`` but the CLI is WATCHDOG-WRAPPED with a mechanical
   scope-aware wall-clock budget (180s + 2s/file, cap 600s); the grok
   lane — grok 0.2.93 ``-p`` takes its prompt as a CLI argument and
   cannot read stdin — writes the redactor's stdout to a 0600 artifact
   (rename-into-place) and passes grok a FIXED pointer argv. Either
   way a skipped/failed redaction cannot yield a sendable prompt, and
   no ``--outgoing`` invocation exists outside the sanctioned shapes.
5. F7 scope threading — the workflow reads ``args.scope`` and threads it
   into lane briefs + the return value (it always did: the S270 defect
   is at the INVOCATION layer), and the ``/council`` command template
   binds ``$ARGUMENTS`` into ``args.scope`` explicitly, mandatory-scope,
   fail-loud on a missing scope (the actual F7 fix).
6. Grok attestation enforcement (PLAN-161 W2, codex r1 F3/F4) — a
   status-ok grok lane without a 64-lowercase-hex ``artifact_sha256``
   is DEMOTED to unavailable before quorum/verdict, and the
   fixture-only ``ARTIFACT_KEEP_DIR`` env redirect is gone from the
   compose snippet (stale sweep + trap cleanup kept).
7. TMPDIR pinning (PLAN-161 W2 fix-round-2, codex r2 F12) — the grok
   compose mkdtemp and the start-of-run stale sweep are pinned to the
   explicit fixed ``/tmp`` base; the TMPDIR-honoring ``mktemp -d -t``
   form and the dirname-derived sweep base are gone (an inherited
   TMPDIR could relocate the artifact into the repo tree and aim the
   sweep's recursive delete at repo directories).
8. Vendor canonicalization (PLAN-161 W2 fix-round-2, codex r2 F13) —
   every lane object's ``vendor`` field is overwritten with its
   canonical ``REQUESTED_VENDORS`` position before any downstream
   consumer reads it, so a lane cannot impersonate another vendor.
9. Scope shell-quoting (PLAN-161 W2 fix-round-3, codex r3 F3) — the
   operator-controlled scope crosses into shell SOURCE (the codex
   lane's ``git ls-files`` budget arg) ONLY through the POSIX
   shell-quote helper ``shq`` (single-quote wrap, embedded quotes as
   the close-escape-reopen sequence); the raw single-quoted
   interpolation — through which a quote-bearing scope could inject
   commands into the redactor/vendor pipeline block — is gone. The
   behavioral twin is test-council-fixture.mjs scenario K.

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


_GROK_BEGIN = "# --- GROK-ARTIFACT-COMPOSE BEGIN ---"
_GROK_END = "# --- GROK-ARTIFACT-COMPOSE END ---"


class TestVendorTransports(TestEnvContext):
    """PLAN-161 C2/C3 — ONE redaction chokepoint, vendor-specific transports.

    codex: redactor stdout pipes into the WATCHDOG-WRAPPED codex CLI
    (mechanical scope-aware wall-clock budget). grok: grok 0.2.93 ``-p``
    takes its prompt as a CLI argument and cannot read stdin, so redactor
    stdout becomes a 0600 artifact + fixed pointer argv. The behavioral
    money-oracle for the grok compose block is
    ``scripts/tests/test-council-grok-artifact.sh``; these are the
    CI-load-bearing structural twins.
    """

    def setUp(self) -> None:
        super().setUp()
        self.src = _workflow_text()
        i = self.src.find(_GROK_BEGIN)
        j = self.src.find(_GROK_END)
        self.assertGreater(i, -1, "grok compose BEGIN marker missing")
        self.assertGreater(j, i, "grok compose END marker missing/misordered")
        self.block = self.src[i + len(_GROK_BEGIN):j]

    def test_codex_pipe_fold_into_wrapped_cli(self) -> None:
        # The codex lane KEEPS the pipe fold — redactor stdout feeds the
        # vendor CLI stdin directly — but the CLI is watchdog-wrapped in
        # BOTH wrapper branches (timeout/gtimeout probe + python3 fallback).
        self.assertIn("set -o pipefail", self.src)
        self.assertRegex(
            self.src,
            r'codex_egress_redact\.py --outgoing \| "\$TOUT" -k 10 "\$BUDGET_S" \$\{cli\}')
        self.assertRegex(
            self.src, r"codex_egress_redact\.py --outgoing \| python3 -c '")

    def test_old_universal_unwrapped_pipe_removed(self) -> None:
        # `--outgoing | ${cli}` (unwrapped) is GONE: unwrapped codex is
        # unbounded burn; a grok stdin pipe transmits zero bytes (rc=2).
        self.assertNotRegex(
            self.src, r"codex_egress_redact\.py --outgoing \| \$\{cli\}")

    def test_two_step_send_removed(self) -> None:
        self.assertNotIn("Feed the REDACTED brief to:", self.src)

    def test_grok_markers_exactly_once(self) -> None:
        self.assertEqual(self.src.count(_GROK_BEGIN), 1)
        self.assertEqual(self.src.count(_GROK_END), 1)

    def test_grok_artifact_shape(self) -> None:
        self.assertIn("umask 077", self.block)
        self.assertIn("mktemp -d /tmp/ceo-council-grok.", self.block)
        self.assertIn("--outgoing > $ART_DIR/brief.tmp", self.block)
        self.assertIn("chmod 600 $ART_DIR/brief.tmp", self.block)
        self.assertIn("mv $ART_DIR/brief.tmp $ART_DIR/brief.txt", self.block)
        self.assertIn("trap 'rm -rf \"$ART_DIR\"' EXIT", self.block)

    def test_mkdtemp_and_sweep_pinned_to_fixed_tmp_base(self) -> None:
        # PLAN-161 W2 fix-round-2 (codex r2 F12): ``mktemp -d -t`` honors
        # an inherited TMPDIR — pointed inside the repo it relocates the
        # redacted artifact INTO the repo tree AND aims the stale sweep's
        # recursive delete at repo directories. Both the mkdtemp and the
        # sweep must use the explicit fixed /tmp base (TMPDIR-immune); the
        # old dirname-of-ART_DIR sweep base must be gone.
        self.assertNotIn("mktemp -d -t", self.block)
        self.assertIn(
            "find /tmp -maxdepth 1 -type d -name 'ceo-council-grok.*'",
            self.block)
        self.assertNotIn('dirname "$ART_DIR"', self.block)

    def test_grok_argv_is_fixed_pointer_only(self) -> None:
        # $BRIEF appears in the compose block ONLY on the redactor line;
        # the grok cli receives a fixed pointer containing brief.txt; no
        # dollar-paren cat of the artifact; nothing is piped into the cli
        # (grok -p cannot read stdin — there must be nothing to pipe).
        self.assertEqual(self.block.count("$BRIEF"), 1)
        self.assertNotIn("$(cat", self.block)
        self.assertRegex(self.block, r'\$\{cli\} "[^"]*brief\.txt[^"]*"')
        self.assertNotRegex(self.block, r"\| \$\{cli\}")

    def test_no_stray_outgoing_invocations(self) -> None:
        # Zero unredacted egress paths: every `--outgoing` invocation in
        # the workflow feeds one of the sanctioned transports — the two
        # wrapped codex pipelines or the grok artifact redirect.
        tails = re.findall(
            r"codex_egress_redact\.py --outgoing(.{0,30})", self.src)
        self.assertEqual(len(tails), 3)
        for t in tails:
            self.assertTrue(
                t.startswith(' | "$TOUT"')
                or t.startswith(" | python3 -c")
                or t.startswith(" > $ART_DIR/brief.tmp"),
                "stray --outgoing tail: %r" % t)

    def test_codex_budget_is_mechanical_and_capped(self) -> None:
        # Scope-aware bounded growth with a HARD cap (cost-DoS control),
        # computed from the RESOLVED scope size — never the brief length.
        self.assertIn("BUDGET_S=$(( 180 + 2 * N ))", self.src)
        self.assertRegex(
            self.src, r'\[ "\$BUDGET_S" -gt 600 \] && BUDGET_S=600')
        self.assertIn("git ls-files", self.src)
        # Portable watchdog: probe timeout, else gtimeout, else python3
        # stdlib (process-group spawn, SIGTERM -> grace -> SIGKILL,
        # DISTINCT timeout exit status); no python3 => lane unavailable.
        self.assertIn("command -v timeout", self.src)
        self.assertIn("command -v gtimeout", self.src)
        self.assertIn("preexec_fn=os.setsid", self.src)
        self.assertIn("signal.SIGTERM", self.src)
        self.assertIn("signal.SIGKILL", self.src)
        self.assertIn("sys.exit(124)", self.src)
        self.assertIn("no watchdog runtime", self.src)

    def test_lane_schema_carries_artifact_sha256(self) -> None:
        # PLAN-161 C2 attestation: the lane JSON carries the sha256 of
        # the redacted artifact handed to grok, threaded into the run
        # report's lanes mapping.
        self.assertRegex(
            self.src, r"artifact_sha256:\s*\{\s*type:\s*'string'\s*\}")
        self.assertIn("artifact_sha256=$SUM", self.src)
        self.assertRegex(self.src, r"lanes:\s*\{[\s\S]*?artifact_sha256")


class TestGrokAttestationEnforcement(TestEnvContext):
    """PLAN-161 W2 (codex r1 F3/F4) — attestation enforced, keep-dir hook gone.

    F3: a grok lane claiming status "ok" without a well-formed
    artifact_sha256 (64 lowercase hex) is mechanically DEMOTED to
    "unavailable" BEFORE quorum/verdict computation — an unattested
    artifact transport (ADR-114) never counts toward CLEAN. The
    behavioral twin is test-council-fixture.mjs scenario H.
    F4: the fixture-only ARTIFACT_KEEP_DIR env redirect is REMOVED from
    the compose snippet — an inherited env var could point artifact
    writes anywhere (repo tree included) and leave brief.txt uncleaned.
    """

    def setUp(self) -> None:
        super().setUp()
        self.src = _workflow_text()

    def test_demotion_gate_present_and_shaped(self) -> None:
        self.assertIn("const SHA256_HEX = /^[0-9a-f]{64}$/", self.src)
        self.assertIn("missing/malformed artifact attestation", self.src)

    def test_demotion_runs_before_quorum_computation(self) -> None:
        gate = self.src.index("const SHA256_HEX")
        quorum = self.src.index("const availableLanes")
        self.assertLess(
            gate, quorum,
            "demotion gate must run BEFORE quorum computation")

    def test_demoted_lane_reports_no_findings(self) -> None:
        # The demoted-lane literal ships findings: [] — the unattested
        # lane's findings are discarded, never merged.
        m = re.search(
            r"missing/malformed artifact attestation[\s\S]*?findings:\s*\[\]",
            self.src)
        self.assertIsNotNone(m, "demoted lane must carry findings: []")

    def test_artifact_keep_dir_hook_removed(self) -> None:
        self.assertNotIn("ARTIFACT_KEEP_DIR", self.src)

    def test_stale_sweep_and_trap_cleanup_kept(self) -> None:
        # F4 removes ONLY the keep-dir redirect: the start-of-run stale
        # sweep and the trap-EXIT cleanup of the mkdtemp dir must remain.
        self.assertIn("-name 'ceo-council-grok.*'", self.src)
        self.assertIn("trap 'rm -rf \"$ART_DIR\"' EXIT", self.src)


class TestVendorCanonicalization(TestEnvContext):
    """PLAN-161 W2 fix-round-2 (codex r2 F13) — lane identity write-back.

    The attestation gate always identified grok by REQUESTED_VENDORS
    position, but it returned the ORIGINAL model-written lane object, and
    every downstream consumer (finding attribution at ``f.vendor``,
    availability/unavailable accounting, disagreement math, the
    ``lanes.artifact_sha256`` attestation map) reads ``lane.vendor`` — so
    a lane could impersonate another vendor by lying in its own JSON. The
    fix writes the canonical requested-position identity back onto every
    surviving lane object. Behavioral twin:
    test-council-fixture.mjs scenario J.
    """

    def setUp(self) -> None:
        super().setUp()
        self.src = _workflow_text()

    def test_canonical_vendor_write_back_present(self) -> None:
        self.assertIn("const requested = REQUESTED_VENDORS[i]", self.src)
        self.assertIn("{ ...l, vendor: requested }", self.src)

    def test_write_back_precedes_downstream_consumers(self) -> None:
        # The canonicalizing map must run before quorum/attribution.
        self.assertLess(
            self.src.index("{ ...l, vendor: requested }"),
            self.src.index("const availableLanes"),
            "vendor canonicalization must run BEFORE lane consumers")


class TestScopeShellQuoting(TestEnvContext):
    """PLAN-161 W2 fix-round-3 (codex r3 F3) — scope shell-quoted into shell source.

    The codex-lane budget block interpolates the operator-controlled
    SCOPE into shell source (``git ls-files -- <scope>``). Interpolated
    raw inside single quotes, a scope containing a single quote breaks
    out of the quoting and injects commands into the very block that
    runs the redactor/vendor pipeline — defeating the read-only +
    redacted-egress guarantees. The fix routes the scope through the
    POSIX shell-quote helper ``shq`` so it always renders as exactly
    ONE inert argv token. Behavioral twins: test-council-fixture.mjs
    scenario K (renders the real prompt with a quote-bearing scope and
    string-compares the budget line) and scenario K2 (codex r4 F3:
    ``bash -n`` parses the rendered block, EXECUTES the rendered budget
    line in a tmp sandbox asserting the injected marker is ABSENT, and
    counter-proves RED-on-unfixed by executing the raw pre-fix
    interpolation and asserting the marker DOES appear).
    """

    # The exact helper bytes in the workflow source:
    #   const shq = (s) => "'" + String(s).replace(/'/g, "'\\''") + "'"
    _SHQ_LINE = (
        "const shq = (s) => \"'\" + String(s).replace(/'/g, \"'\\\\''\") + \"'\""
    )

    def setUp(self) -> None:
        super().setUp()
        self.src = _workflow_text()

    def test_shq_helper_present_and_posix_shaped(self) -> None:
        # Single-quote wrap + close-escape-reopen replacement, byte-exact —
        # a weakened helper (e.g. quote-stripping) must go RED.
        self.assertIn(self._SHQ_LINE, self.src)

    def test_ls_files_scope_arg_routed_through_shq(self) -> None:
        self.assertIn(
            "git ls-files -- ${shq(SCOPE)} 2>/dev/null", self.src)

    def test_raw_single_quoted_scope_interpolation_gone(self) -> None:
        # The pre-fix injection surface: SCOPE interpolated raw inside
        # single quotes anywhere in the workflow. RED against the
        # pre-fix file by construction.
        self.assertNotIn("'${SCOPE}'", self.src)


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
