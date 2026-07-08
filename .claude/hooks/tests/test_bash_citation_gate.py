"""Tests for PLAN-153 Wave E item 5 / ADR-175 half 1 — the destructive-Bash
CITATION GATE in check_bash_safety.py.

COUPLING NOTE: this is a STAGED test (PLAN-153 Wave E staging discipline —
tests asserting staged-only behavior live in the staged mirror until the
ceremony lands both files). It loads the citation-gate check_bash_safety.py
CANONICAL-FIRST (post-apply tree), falling back to the staged SOURCE copy at
.claude/plans/PLAN-153/staged/wave-E/ (pre-ceremony live tree) — the same
dual-context pattern as tests/test_check_bash_safety_h5_rewrite.py. The
`_lib` package is always the canonical one (no staged _lib exists for this
unit).

Contract under test (PLAN-153 §Wave E item 5; ADR-175):
  * A DESTRUCTIVE command (rm -rf / git reset --hard / git push --force)
    may carry a verbatim citation of the justifying instruction via the
    leading env-assignment channel
    ``CEO_DESTRUCTIVE_CITE='<source>:<verbatim text>'``.
  * Verified citation => ALLOW + ``destructive_citation_accepted`` recorded
    into the HMAC chain with ``cited_instruction_data`` passed through
    ``redact_secrets`` (DATA field).
  * FAIL-CLOSED: citation absent / malformed / transcript unreadable /
    text mismatched => BLOCK (this file ships the REQUIRED
    transcript-read-failure fixture asserting BLOCK).
  * Fail-open is permitted ONLY on the audit-emit side.
  * The gate keys off Decision.destructive — canonical-path / credential /
    git-bypass blocks are NEVER citation-unlockable.
  * Pilot flag CEO_DESTRUCTIVE_CITATION_GATE (default-OFF, trusted_env
    snapshot); with the flag off the legacy hard BLOCK is byte-identical.
  * Precondition hardening: leading NAME=VALUE assignments and the ``env``
    runner no longer de-classify destructive commands (the citation channel
    must never weaken the classifier it gates).

INERT TEST DATA (Wave E doctrine 5): every command string, transcript line
and pattern-shaped token in this file is fixture DATA replayed against the
gate's decision functions — nothing here is executed as a shell command,
and the ``ghp_``-shaped marker below is a synthetic redaction probe, not a
real credential.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
import unittest.mock as mock
from pathlib import Path

# --- Locate repo root + pick the citation-gate hook source (canonical-first,
# staged fallback — see module docstring). ---
_THIS = Path(__file__).resolve()
_repo_root = None
for _parent in _THIS.parents:
    if (_parent / ".claude" / "hooks" / "_lib").is_dir() and (
        _parent / ".claude" / "plans"
    ).is_dir():
        _repo_root = _parent
        break
assert _repo_root is not None, "could not locate repo root from test path"
_LIVE_HOOKS = _repo_root / ".claude" / "hooks"
_CANONICAL_CBS = _LIVE_HOOKS / "check_bash_safety.py"
_STAGED_CBS = (
    _repo_root
    / ".claude" / "plans" / "PLAN-153" / "staged" / "wave-E"
    / ".claude" / "hooks" / "check_bash_safety.py"
)
# The citation-gate marker distinguishing a post-apply canonical copy from a
# pre-apply live one.
_CITE_MARKER = "def _apply_destructive_citation_gate"


def _pick(canonical: Path, staged: Path, marker: str) -> Path:
    """Prefer the canonical copy IF it already carries the citation-gate
    marker (applied tree); else the staged SOURCE copy (pre-ceremony tree).
    Raise if neither carries it — a genuine misconfiguration to surface."""
    try:
        if canonical.is_file() and marker in canonical.read_text(encoding="utf-8"):
            return canonical
    except OSError:
        pass
    if staged.is_file() and marker in staged.read_text(encoding="utf-8"):
        return staged
    raise FileNotFoundError(
        "citation-gate source not found in canonical (%s) or staged (%s); "
        "marker=%r" % (canonical, staged, marker)
    )


if str(_LIVE_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIVE_HOOKS))  # canonical _lib package

from _lib.testing import TestEnvContext  # noqa: E402
from _lib.redact import redact_secrets  # noqa: E402


def _load_cbs():
    """Load the citation-gate check_bash_safety module under a private name.
    Any sys.path entry the module inserts for its own (staged) directory is
    removed afterwards so a later `import check_bash_safety` elsewhere in
    the same pytest session cannot resolve to the staged tree."""
    src = _pick(_CANONICAL_CBS, _STAGED_CBS, _CITE_MARKER)
    spec = importlib.util.spec_from_file_location(
        "staged_check_bash_safety_citation", str(src)
    )
    mod = importlib.util.module_from_spec(spec)
    # Register BEFORE exec so @dataclass introspection works on py3.9.
    sys.modules["staged_check_bash_safety_citation"] = mod
    staged_dir = str(src.parent)
    was_absent = staged_dir not in sys.path
    try:
        spec.loader.exec_module(mod)
    finally:
        if (
            was_absent
            and staged_dir != str(_LIVE_HOOKS)
            and staged_dir in sys.path
        ):
            sys.path.remove(staged_dir)
    return mod


cbs = _load_cbs()

_GATE_FLAG = "CEO_DESTRUCTIVE_CITATION_GATE"

# ---------------------------------------------------------------------------
# INERT TEST DATA — fixture strings only, never executed.
# ---------------------------------------------------------------------------
_CITED = "please remove the scratch directory at /tmp/scratch-e5 entirely"
_CMD_CITED = (
    "CEO_DESTRUCTIVE_CITE='transcript:%s' rm -rf /tmp/scratch-e5" % _CITED
)
_CMD_PLAIN_DESTRUCTIVE = "rm -rf /tmp/scratch-e5"
# Pattern-shaped synthetic token for the redaction probe (matches the
# _lib.redact ghp_ GitHub-PAT pattern; 30 filler chars, not a credential).
_FAKE_PAT = "ghp_" + "x" * 30


class _GateTestBase(TestEnvContext):
    """TestEnvContext + citation-gate pilot flag armed via the trusted_env
    snapshot dict (mock.patch.dict — restored on tearDown; never a direct
    os.environ write, per the env-hygiene gate)."""

    GATE_ON = True

    def setUp(self):
        super().setUp()
        if self.GATE_ON:
            self._gate_patch = mock.patch.dict(
                cbs._trusted_env.ORIGINAL_CEO_ENV, {_GATE_FLAG: "1"}
            )
        else:
            # clear=True guarantees the flag is ABSENT regardless of the
            # developer shell that launched pytest.
            self._gate_patch = mock.patch.dict(
                cbs._trusted_env.ORIGINAL_CEO_ENV, {}, clear=True
            )
        self._gate_patch.start()

    def tearDown(self):
        self._gate_patch.stop()
        super().tearDown()

    # -- helpers ----------------------------------------------------------

    def _write_transcript(self, text: str, name: str = "session.jsonl") -> Path:
        """Materialize an isolated session transcript (JSONL) under the
        sandboxed $HOME/.claude tree (the gate's path constraint)."""
        tdir = self.home_dir / ".claude" / "projects" / "test-e5"
        tdir.mkdir(parents=True, exist_ok=True)
        tp = tdir / name
        line = json.dumps(
            {"type": "user", "message": {"role": "user", "content": text}}
        )
        tp.write_text(line + "\n", encoding="utf-8")
        return tp

    def _run_main(self, command: str, transcript_path: str = "") -> dict:
        """Drive cbs.main() end-to-end via stdin/stdout capture. Returns the
        parsed stdout decision JSON."""
        payload = {
            "session_id": "s-e5",
            "tool_name": "Bash",
            "tool_input": {"command": command},
        }
        if transcript_path:
            payload["transcript_path"] = transcript_path
        stdin = io.StringIO(json.dumps(payload))
        stdout = io.StringIO()
        with mock.patch.object(sys, "stdin", stdin), mock.patch.object(
            sys, "stdout", stdout
        ):
            rc = cbs.main()
        self.assertEqual(rc, 0)
        out = stdout.getvalue().strip()
        self.assertTrue(out, "hook must emit exactly one JSON line")
        return json.loads(out.splitlines()[-1])

    def _audit_events(self, reason_code=None):
        log = self.audit_dir / "audit-log.jsonl"
        if not log.exists():
            return []
        events = []
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if reason_code is None or ev.get("reason_code") == reason_code:
                events.append(ev)
        return events


# ---------------------------------------------------------------------------
# Classifier hardening — the citation channel must never DE-classify.
# ---------------------------------------------------------------------------
class TestEnvAssignmentNormalization(TestEnvContext):
    """Leading NAME=VALUE assignments + the `env` runner no longer bypass the
    destructive matchers (positive controls for the ADR-175 precondition)."""

    def test_blocks_assignment_prefixed_rm_rf(self):
        d = cbs.decide_command("FOO=1 rm -rf /tmp/x")
        self.assertFalse(d.allow)
        self.assertTrue(d.destructive)

    def test_blocks_env_runner_prefixed_rm_rf(self):
        d = cbs.decide_command("env FOO=1 rm -rf /tmp/x")
        self.assertFalse(d.allow)
        self.assertTrue(d.destructive)

    def test_blocks_assignment_then_sudo(self):
        d = cbs.decide_command("FOO=1 sudo rm -rf /tmp/x")
        self.assertFalse(d.allow)

    def test_citation_prefix_still_classifies_destructive(self):
        d = cbs.decide_command(_CMD_CITED)
        self.assertFalse(d.allow)  # decide_command is gate-free (pure)
        self.assertTrue(d.destructive)

    def test_blocks_assignment_prefixed_git_reset_hard(self):
        d = cbs.decide_command("GIT_PAGER=cat git reset --hard HEAD")
        self.assertFalse(d.allow)
        self.assertTrue(d.destructive)

    def test_allows_make_with_var_argument(self):
        # Assignment AFTER the command word is an argument, not env.
        self.assertTrue(cbs.decide_command("make FOO=1 all").allow)

    def test_allows_bare_env_listing(self):
        self.assertTrue(cbs.decide_command("env").allow)

    def test_allows_pure_assignment(self):
        self.assertTrue(cbs.decide_command("FOO=bar").allow)

    def test_rawscan_path_carries_destructive_tag(self):
        # Quoted-metachar defeat of the naive splitter (PLAN-152 class) must
        # stay citation-gatable => destructive=True on the rawscan return.
        d = cbs.decide_command('rm -rf /tmp/x ";"')
        self.assertFalse(d.allow)
        self.assertTrue(d.destructive)

    def test_canonical_block_is_not_destructive_class(self):
        # Wave E.3 canonical interceptor block => destructive=False (the
        # citation gate must never key on it).
        d = cbs.decide_command("tee .claude/settings.json")
        self.assertFalse(d.allow)
        self.assertIn("GOVERNANCE", d.reason)
        self.assertFalse(d.destructive)


# ---------------------------------------------------------------------------
# Citation extraction (pure).
# ---------------------------------------------------------------------------
class TestCitationExtraction(TestEnvContext):
    def test_absent_without_assignment(self):
        self.assertEqual(
            cbs._extract_destructive_citation(_CMD_PLAIN_DESTRUCTIVE),
            ("absent", "", ""),
        )

    def test_absent_when_assignment_after_command_word(self):
        # Shell semantics: only the LEADING assignment run is environment.
        status, _, _ = cbs._extract_destructive_citation(
            "rm CEO_DESTRUCTIVE_CITE=transcript:%s -rf /tmp/x" % ("y" * 20)
        )
        self.assertEqual(status, "absent")

    def test_absent_on_unparseable_command(self):
        status, _, _ = cbs._extract_destructive_citation(
            "CEO_DESTRUCTIVE_CITE='transcript:unterminated rm -rf /tmp/x"
        )
        self.assertEqual(status, "absent")

    def test_ok_splits_on_first_colon_only(self):
        status, source, cited = cbs._extract_destructive_citation(
            "CEO_DESTRUCTIVE_CITE='transcript:remove dir: /tmp/x now please' "
            "rm -rf /tmp/x"
        )
        self.assertEqual(status, "ok")
        self.assertEqual(source, "transcript")
        self.assertEqual(cited, "remove dir: /tmp/x now please")

    def test_ok_plan_source(self):
        status, source, cited = cbs._extract_destructive_citation(
            "CEO_DESTRUCTIVE_CITE='PLAN-042:delete the legacy fixture tree' "
            "rm -rf /tmp/x"
        )
        self.assertEqual((status, source), ("ok", "PLAN-042"))
        self.assertEqual(cited, "delete the legacy fixture tree")

    def test_malformed_without_separator(self):
        status, detail, _ = cbs._extract_destructive_citation(
            "CEO_DESTRUCTIVE_CITE=notexthereatall rm -rf /tmp/x"
        )
        self.assertEqual(status, "malformed")
        self.assertIn(":", detail)

    def test_malformed_unknown_source(self):
        status, detail, _ = cbs._extract_destructive_citation(
            "CEO_DESTRUCTIVE_CITE='notes:whatever text here ok' rm -rf /tmp/x"
        )
        self.assertEqual(status, "malformed")
        self.assertIn("notes", detail)

    def test_malformed_short_text(self):
        status, detail, _ = cbs._extract_destructive_citation(
            "CEO_DESTRUCTIVE_CITE='transcript:short' rm -rf /tmp/x"
        )
        self.assertEqual(status, "malformed")
        self.assertIn("16", detail)


# ---------------------------------------------------------------------------
# Pilot-flag plumbing (trusted_env snapshot, default-OFF).
# ---------------------------------------------------------------------------
class TestGateFlagPlumbing(TestEnvContext):
    def test_default_off_when_flag_absent(self):
        with mock.patch.dict(cbs._trusted_env.ORIGINAL_CEO_ENV, {}, clear=True):
            self.assertFalse(cbs._destructive_citation_gate_enabled())

    def test_enabled_only_on_literal_1(self):
        with mock.patch.dict(
            cbs._trusted_env.ORIGINAL_CEO_ENV, {_GATE_FLAG: "1"}
        ):
            self.assertTrue(cbs._destructive_citation_gate_enabled())
        with mock.patch.dict(
            cbs._trusted_env.ORIGINAL_CEO_ENV, {_GATE_FLAG: "0"}
        ):
            self.assertFalse(cbs._destructive_citation_gate_enabled())
        with mock.patch.dict(
            cbs._trusted_env.ORIGINAL_CEO_ENV, {_GATE_FLAG: "yes"}
        ):
            self.assertFalse(cbs._destructive_citation_gate_enabled())


class TestGateDefaultOffBehavior(_GateTestBase):
    """Flag OFF (guaranteed absent): a VALID citation changes nothing — the
    legacy hard BLOCK ships, and the channel is not a bypass."""

    GATE_ON = False

    def test_valid_citation_still_blocked_when_gate_off(self):
        tp = self._write_transcript(_CITED)
        out = self._run_main(_CMD_CITED, transcript_path=str(tp))
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("BLOCKED", out.get("reason", ""))
        # No citation-gate vocabulary leaks into the legacy block.
        self.assertNotIn("CITATION GATE", out.get("reason", ""))


# ---------------------------------------------------------------------------
# Gate ON — end-to-end through main() (stdin payload → stdout decision).
# ---------------------------------------------------------------------------
class TestCitationGateEndToEnd(_GateTestBase):
    GATE_ON = True

    # -- happy path --------------------------------------------------------

    def test_happy_path_transcript_citation_allows_and_records(self):
        tp = self._write_transcript(_CITED)
        out = self._run_main(_CMD_CITED, transcript_path=str(tp))
        self.assertEqual(out, {})  # allow shape
        accepted = self._audit_events("destructive_citation_accepted")
        self.assertEqual(len(accepted), 1)
        ev = accepted[0]
        self.assertEqual(ev.get("action"), "veto_triggered")
        self.assertEqual(ev.get("gate_outcome"), "allowed_with_citation")
        self.assertEqual(ev.get("cite_source_class"), "transcript")
        self.assertEqual(
            ev.get("cited_instruction_data"),
            redact_secrets(_CITED, max_chars=cbs._CITE_AUDIT_PREVIEW_CHARS),
        )

    def test_happy_path_json_escaped_transcript_content(self):
        # An instruction containing double quotes is stored JSON-escaped in
        # the transcript; the escaped needle must still verify.
        cited = 'wipe the "scratch-e5" build directory now please'
        tp = self._write_transcript(cited)
        cmd = 'CEO_DESTRUCTIVE_CITE=\'transcript:%s\' rm -rf /tmp/scratch-e5' % cited
        out = self._run_main(cmd, transcript_path=str(tp))
        self.assertEqual(out, {})

    # -- fail-closed directions ---------------------------------------------

    def test_citation_mismatch_blocks(self):
        tp = self._write_transcript("a completely different instruction line")
        out = self._run_main(_CMD_CITED, transcript_path=str(tp))
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("could not be verified", out.get("reason", ""))
        self.assertTrue(self._audit_events("destructive_citation_verify_failed"))
        self.assertFalse(self._audit_events("destructive_citation_accepted"))

    def test_transcript_missing_file_blocks(self):
        ghost = self.home_dir / ".claude" / "projects" / "none" / "gone.jsonl"
        out = self._run_main(_CMD_CITED, transcript_path=str(ghost))
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("could not be verified", out.get("reason", ""))

    def test_transcript_read_failure_blocks(self):
        """REQUIRED fixture (PLAN-153 item 5): an unreadable transcript is a
        fail-CLOSED BLOCK, never an allow. The read failure is injected at
        the bounded-read seam so the test is deterministic under any uid."""
        tp = self._write_transcript(_CITED)
        with mock.patch.object(
            cbs, "_cite_bounded_tail_read", side_effect=OSError("simulated I/O error")
        ):
            out = self._run_main(_CMD_CITED, transcript_path=str(tp))
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("could not be verified", out.get("reason", ""))
        self.assertIn("read failed", out.get("reason", ""))
        self.assertTrue(self._audit_events("destructive_citation_verify_failed"))

    def test_transcript_outside_home_claude_blocks(self):
        # A payload pointing at an arbitrary attacker-plantable file (outside
        # ~/.claude/) must fail verification even if the text matches.
        outside = self.project_dir / "planted.jsonl"
        outside.write_text(
            json.dumps({"content": _CITED}) + "\n", encoding="utf-8"
        )
        out = self._run_main(_CMD_CITED, transcript_path=str(outside))
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("outside", out.get("reason", ""))

    def test_no_transcript_path_in_payload_blocks(self):
        out = self._run_main(_CMD_CITED)  # payload without transcript_path
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("transcript_path", out.get("reason", ""))

    def test_missing_citation_blocks_with_hint(self):
        tp = self._write_transcript(_CITED)
        out = self._run_main(_CMD_PLAIN_DESTRUCTIVE, transcript_path=str(tp))
        self.assertEqual(out.get("decision"), "block")
        reason = out.get("reason", "")
        self.assertIn("BLOCKED", reason)          # legacy destructive reason
        self.assertIn("CITATION GATE", reason)    # actionable how-to-cite
        self.assertIn("CEO_DESTRUCTIVE_CITE", reason)

    def test_malformed_citation_blocks(self):
        tp = self._write_transcript(_CITED)
        cmd = "CEO_DESTRUCTIVE_CITE='transcript:short' rm -rf /tmp/scratch-e5"
        out = self._run_main(cmd, transcript_path=str(tp))
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("malformed", out.get("reason", ""))

    # -- scope guard ---------------------------------------------------------

    def test_citation_never_unlocks_canonical_path_block(self):
        tp = self._write_transcript(_CITED)
        cmd = (
            "CEO_DESTRUCTIVE_CITE='transcript:%s' tee .claude/settings.json"
            % _CITED
        )
        out = self._run_main(cmd, transcript_path=str(tp))
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("GOVERNANCE", out.get("reason", ""))
        self.assertFalse(self._audit_events("destructive_citation_accepted"))


# ---------------------------------------------------------------------------
# Plan-file citations.
# ---------------------------------------------------------------------------
class TestPlanCitation(_GateTestBase):
    GATE_ON = True

    _PLAN_TEXT = "Wave X item: delete the legacy fixture tree under /tmp/x"

    def _write_plan(self):
        plans = self.project_dir / ".claude" / "plans"
        plans.mkdir(parents=True, exist_ok=True)
        # INERT fixture plan file (DATA).
        (plans / "PLAN-042-inert-fixture.md").write_text(
            "# PLAN-042 (test fixture)\n\n%s\n" % self._PLAN_TEXT,
            encoding="utf-8",
        )

    def test_plan_citation_rejected_even_when_text_matches(self):
        # Codex pair-rail P2 (S261 landing): a plan file is NOT a trusted
        # citation source — an agent can plant the line and cite it. Even a
        # VERBATIM match against a real plan file must BLOCK; only the session
        # transcript is a trusted source.
        self._write_plan()
        cmd = (
            "CEO_DESTRUCTIVE_CITE='PLAN-042:%s' rm -rf /tmp/x" % self._PLAN_TEXT
        )
        out = self._run_main(cmd)
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("not a trusted source", out.get("reason", ""))
        # And no acceptance event was emitted.
        self.assertEqual(self._audit_events("destructive_citation_accepted"), [])

    def test_plan_citation_no_matching_file_blocks(self):
        cmd = (
            "CEO_DESTRUCTIVE_CITE='PLAN-042:%s' rm -rf /tmp/x" % self._PLAN_TEXT
        )
        out = self._run_main(cmd)
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("not a trusted source", out.get("reason", ""))

    def test_plan_citation_mismatch_blocks(self):
        # Codex pair-rail P2 (S261): plan citations are never a trusted source,
        # so a mismatch blocks for the same reason a match does — the plan
        # branch is fail-CLOSED before any text comparison.
        self._write_plan()
        cmd = (
            "CEO_DESTRUCTIVE_CITE='PLAN-042:this text is not in the plan at "
            "all' rm -rf /tmp/x"
        )
        out = self._run_main(cmd)
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("not a trusted source", out.get("reason", ""))


# ---------------------------------------------------------------------------
# Audit-side: redaction of the cited text before it enters the chain.
# ---------------------------------------------------------------------------
class TestAcceptedEmitRedaction(TestEnvContext):
    def test_cited_text_is_redacted_before_chain_write(self):
        cited = "rotate then remove the key %s and delete /tmp/x" % _FAKE_PAT
        cbs._emit_destructive_citation_accepted("transcript", "transcript", cited)
        log = self.audit_dir / "audit-log.jsonl"
        self.assertTrue(log.exists(), "accepted emit must reach the chain")
        raw = log.read_text(encoding="utf-8")
        self.assertNotIn(_FAKE_PAT, raw)  # no secret bytes in the chain
        ev = json.loads(raw.strip().splitlines()[-1])
        self.assertEqual(ev.get("reason_code"), "destructive_citation_accepted")
        self.assertIn("[GITHUB_PAT]", ev.get("cited_instruction_data", ""))

    def test_emit_failure_is_fail_open(self):
        # An audit-emit crash must never raise into the decision path.
        with mock.patch.object(
            cbs._audit_emit, "emit_generic", side_effect=RuntimeError("boom")
        ):
            cbs._emit_destructive_citation_accepted(
                "transcript", "transcript", _CITED
            )  # must not raise
        with mock.patch.object(
            cbs._audit_emit, "emit_veto_triggered", side_effect=RuntimeError("boom")
        ):
            cbs._emit_destructive_citation_rejected("detail")  # must not raise


if __name__ == "__main__":
    unittest.main()
