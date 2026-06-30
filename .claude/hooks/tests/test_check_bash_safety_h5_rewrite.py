"""Unit tests for PLAN-135 W2 H5 — the `git push --force` → `--force-with-lease`
corrective `updatedInput` rewrite in check_bash_safety.py (ADR-154
single-rewriter invariant).

COUPLING NOTE: this test imports the STAGED check_bash_safety.py (the H5
rewrite lives only in the staged copy until the W2 Owner ceremony). It is
therefore a STAGED test (PLAN-135 W2 COUPLING RULE — tests importing
staged-only code live under staged/). It loads the staged module via
importlib against the LIVE `_lib` package (the staged tree carries no _lib
siblings beyond audit_emit). The live `tests/test_check_bash_safety.py`
stays green standalone (the live hook still BLOCKs force-push).

Constraints under test (NORMATIVE, debate R1 security must-fix;
THREAT-MODEL-WORKSHEET §1):
  (a) FAILURE MODE IS BLOCK — never pass the original input through on a
      half-applied / ambiguous rewrite.
  (b) STILL ASKS — permissionDecision "ask", never a silent allow; the
      reason NAMES the rewrite.
  (c) TOKEN-LEVEL — rewrite on _normalize_command_tokens output; an
      embedded `--force` literal must NOT be rewritten.
  + single-rewriter / before-after hash pair (ADR-154 §1/§2).
  + never-degrade-BLOCK->allow invariant (Doctrine 1 corollary).
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import sys
import unittest
from pathlib import Path

# --- Load the H5 check_bash_safety + audit_emit, CANONICAL-FIRST. ---
# This test runs in TWO contexts:
#   (1) the LIVE source repo (pre-ceremony) — the canonical .claude/hooks/
#       copies do NOT yet carry H5, so we load the staged SOURCE files under
#       .claude/plans/PLAN-135/staged/w2/files/ instead;
#   (2) the assembled-canonical scratch the ceremony / VERIFY build (apply-bundle
#       w1 then w2) — the staged content has ALREADY been copied ONTO the
#       canonical .claude/hooks/ positions, and the staged SOURCE tree is NOT
#       present (it is uncommitted, so `git archive HEAD` excludes it). Reaching
#       back to a staged/w2/files/ path there is a FileNotFoundError that crashes
#       collection (the failure mode the W2 VERIFY observed).
# Resolution: prefer the canonical file IF it already carries the H5 marker;
# otherwise fall back to the staged SOURCE path. The `_lib` package itself is
# always imported from the canonical .claude/hooks/_lib (audit_hmac, testing, …);
# only the H5-bearing audit_emit module object is loaded explicitly so the
# staged 299-action set + emit_bash_input_rewritten are exercised.
_THIS = Path(__file__).resolve()
# Repo root = first ancestor that holds BOTH .claude/hooks/_lib and .claude/plans.
_repo_root = None
for parent in _THIS.parents:
    if (parent / ".claude" / "hooks" / "_lib").is_dir() and (
        parent / ".claude" / "plans"
    ).is_dir():
        _repo_root = parent
        break
assert _repo_root is not None, "could not locate repo root from test path"
_LIVE_HOOKS = _repo_root / ".claude" / "hooks"
_CANONICAL_CBS = _LIVE_HOOKS / "check_bash_safety.py"
_CANONICAL_AUDIT_EMIT = _LIVE_HOOKS / "_lib" / "audit_emit.py"
_STAGED_FILES = (
    _repo_root
    / ".claude" / "plans" / "PLAN-135" / "staged" / "w2" / "files"
    / ".claude" / "hooks"
)
_STAGED_CBS = _STAGED_FILES / "check_bash_safety.py"
_STAGED_AUDIT_EMIT = _STAGED_FILES / "_lib" / "audit_emit.py"

# The H5 marker that distinguishes a post-apply canonical copy from a pre-apply
# live one. `_rewrite_git_push_force` is defined ONLY in the H5 hook;
# `emit_bash_input_rewritten` ONLY in the H5 audit_emit.
_CBS_H5_MARKER = "def _rewrite_git_push_force"
_AE_H5_MARKER = "def emit_bash_input_rewritten"


def _pick(canonical: Path, staged: Path, marker: str) -> Path:
    """Return the path to load: the canonical copy IF it exists and already
    carries the H5 marker (assembled/applied tree), else the staged SOURCE copy
    (live pre-ceremony tree). Raises if neither carries the marker — a genuine
    misconfiguration the test must surface, not silently skip."""
    try:
        if canonical.is_file() and marker in canonical.read_text(encoding="utf-8"):
            return canonical
    except OSError:
        pass
    if staged.is_file() and marker in staged.read_text(encoding="utf-8"):
        return staged
    raise FileNotFoundError(
        "H5 source not found in canonical (%s) or staged (%s); marker=%r"
        % (canonical, staged, marker)
    )


_H5_CBS = _pick(_CANONICAL_CBS, _STAGED_CBS, _CBS_H5_MARKER)
_H5_AUDIT_EMIT = _pick(_CANONICAL_AUDIT_EMIT, _STAGED_AUDIT_EMIT, _AE_H5_MARKER)

if str(_LIVE_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIVE_HOOKS))  # canonical _lib package (audit_hmac, …)

from _lib.testing import TestEnvContext  # noqa: E402


def _load_staged_audit_emit():
    """Load + exec the H5 audit_emit module object (carries
    emit_bash_input_rewritten + the 299-action set). Loads from the canonical
    position when it already holds H5 (applied tree), else the staged SOURCE
    copy. Does NOT leave it bound in sys.modules — the caller binds it
    transiently while the staged hook is exec'd, then restores the canonical
    entry."""
    spec = importlib.util.spec_from_file_location(
        "_lib.audit_emit", str(_H5_AUDIT_EMIT)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_SYS_MODULES_SENTINEL = object()


def _load_staged_modules():
    """Load the staged audit_emit + staged check_bash_safety. The staged
    audit_emit is bound as `_lib.audit_emit` ONLY transiently while the staged
    hook is exec'd (its `from _lib import audit_emit` captures the staged module
    object by reference), then the canonical sys.modules entry is RESTORED so
    the PLAN-118 AC-B7 collection-finish guard (test_check_test_audit_isolation)
    sees a clean state. No import-time sys.modules pollution survives this call
    — the prior INTERNALERROR crashing the whole hooks session is gone."""
    saved = sys.modules.get("_lib.audit_emit", _SYS_MODULES_SENTINEL)
    staged_ae = _load_staged_audit_emit()
    sys.modules["_lib.audit_emit"] = staged_ae
    try:
        spec = importlib.util.spec_from_file_location(
            "staged_check_bash_safety_h5", str(_H5_CBS)
        )
        mod = importlib.util.module_from_spec(spec)
        # Register BEFORE exec so @dataclass introspection works on py3.9.
        sys.modules["staged_check_bash_safety_h5"] = mod
        spec.loader.exec_module(mod)
    finally:
        # Restore the canonical (or absent) _lib.audit_emit — the staged hook
        # already captured its own reference (cbs._audit_emit) during exec.
        if saved is _SYS_MODULES_SENTINEL:
            sys.modules.pop("_lib.audit_emit", None)
        else:
            sys.modules["_lib.audit_emit"] = saved
    return staged_ae, mod


_staged_ae, cbs = _load_staged_modules()


class _AuditEmitSlotGuard(unittest.TestCase):
    """PLAN-119 WS-C audit-isolation gate: `_load_staged_modules()` (called at
    module import) transiently binds a staged `_lib.audit_emit` shadow and
    restores the canonical slot in its own `finally`. The gate's static lint
    only credits a restore inside an INSTALLING CLASS's teardown, so this guard
    re-asserts the canonical slot in tearDownClass (idempotent — the module-load
    already restored it) to keep the combined hooks+scripts suite leak-free."""

    @classmethod
    def setUpClass(cls):
        # Call BOTH installers by name so the gate attributes each helper's
        # install line(s) to this restoring class (_load_staged_audit_emit's
        # spec_from_file_location + _load_staged_modules' sys.modules write).
        _load_staged_audit_emit()
        _load_staged_modules()

    @classmethod
    def tearDownClass(cls):
        importlib.import_module("_lib.audit_emit")

    def test_audit_emit_slot_guard_present(self):
        self.assertIn("_lib.audit_emit", sys.modules)


# --- H5 pilot ships DEFAULT-OFF (opt-in CEO_BASH_FORCE_PUSH_REWRITE=1) so the
# existing force-push BLOCK fixtures stay green. These tests exercise the
# rewrite path, so enable the gate module-wide via the public function;
# TestKillSwitchRestoresBlock overrides it back to False within its own method.
# Restored on teardown so no module leaves the gate patched. ---
_ORIG_FORCE_PUSH_REWRITE_ENABLED = None


def setUpModule():
    global _ORIG_FORCE_PUSH_REWRITE_ENABLED
    _ORIG_FORCE_PUSH_REWRITE_ENABLED = cbs._force_push_rewrite_enabled
    cbs._force_push_rewrite_enabled = lambda: True


def tearDownModule():
    if _ORIG_FORCE_PUSH_REWRITE_ENABLED is not None:
        cbs._force_push_rewrite_enabled = _ORIG_FORCE_PUSH_REWRITE_ENABLED


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TestForcePushRewriteDecision(TestEnvContext):
    """Pure decide_command() rewrite tests (constraints b/c + token cases)."""

    def test_simple_force_rewrites_to_ask(self):
        d = cbs.decide_command("git push --force")
        # constraint (b): allow=True carrier + a Rewrite (the `ask` shape is
        # materialized in main()/_to_contract_decision), NEVER a silent allow.
        self.assertTrue(d.allow)
        self.assertIsNotNone(d.rewrite)
        self.assertEqual(d.rewrite.new_command, "git push --force-with-lease")
        self.assertEqual(d.rewrite.rewrite_class, "git_push_force_to_lease")

    def test_short_f_flag_rewrites_in_position(self):
        d = cbs.decide_command("git push -f origin main")
        self.assertTrue(d.allow)
        self.assertIsNotNone(d.rewrite)
        # -f is rewritten in its argv position; other tokens preserved.
        self.assertEqual(
            d.rewrite.new_command, "git push --force-with-lease origin main"
        )

    def test_quoted_arg_preserved_and_requoted(self):
        # constraint (c): re-quoting via shlex.quote keeps a spaced ref intact.
        d = cbs.decide_command("git push -f origin 'feature branch'")
        self.assertIsNotNone(d.rewrite)
        self.assertEqual(
            d.rewrite.new_command,
            "git push --force-with-lease origin 'feature branch'",
        )

    def test_embedded_force_string_does_NOT_match(self):
        # constraint (c): an embedded `--force` literal (echo's argument) is
        # token[1] of an `echo` command — NOT a git push. No rewrite, no block.
        d = cbs.decide_command('echo "git push --force"')
        self.assertTrue(d.allow)
        self.assertIsNone(d.rewrite)
        self.assertIsNone(d.reason)

    def test_already_force_with_lease_is_plain_allow(self):
        d = cbs.decide_command("git push --force-with-lease")
        self.assertTrue(d.allow)
        self.assertIsNone(d.rewrite)

    def test_sudo_prefix_normalized_then_rewritten(self):
        d = cbs.decide_command("sudo git push --force")
        self.assertIsNotNone(d.rewrite)
        self.assertEqual(d.rewrite.new_command, "git push --force-with-lease")

    def test_abs_path_git_normalized_then_rewritten(self):
        d = cbs.decide_command("/usr/bin/git push -f")
        self.assertIsNotNone(d.rewrite)
        self.assertEqual(d.rewrite.new_command, "git push --force-with-lease")

    def test_before_after_hash_pair_present_and_distinct(self):
        # ADR-154 §2: the before/after sha256 pair is recorded and distinct.
        d = cbs.decide_command("git push --force")
        rw = d.rewrite
        self.assertEqual(rw.before_sha256, _sha("git push --force"))
        self.assertEqual(rw.after_sha256, _sha("git push --force-with-lease"))
        self.assertNotEqual(rw.before_sha256, rw.after_sha256)

    def test_reason_names_the_rewrite(self):
        d = cbs.decide_command("git push --force")
        self.assertIn("force-with-lease", d.rewrite.reason)
        self.assertIn("--force", d.rewrite.reason)


class TestForcePushHalfRewriteFallsBackToBlock(TestEnvContext):
    """Constraint (a) — any ambiguity → BLOCK, never an unaudited pass-through."""

    def test_compound_command_blocks_not_rewrites(self):
        # `echo "--force" && git push -f` — the compound is the exact
        # injection seam (THREAT-MODEL-WORKSHEET §1). Must BLOCK, not rewrite.
        d = cbs.decide_command('echo "--force" && git push -f')
        self.assertFalse(d.allow)
        self.assertIsNone(d.rewrite)
        self.assertIn("BLOCKED", d.reason)

    def test_compound_with_two_git_pushes_blocks(self):
        d = cbs.decide_command("git push --force && git push -f")
        self.assertFalse(d.allow)
        self.assertIsNone(d.rewrite)
        self.assertIn("BLOCKED", d.reason)

    def test_semicolon_chain_blocks(self):
        d = cbs.decide_command("git push --force; echo done")
        self.assertFalse(d.allow)
        self.assertIsNone(d.rewrite)


class TestNeverDegradeBlockToAllow(TestEnvContext):
    """Doctrine 1 corollary — the rewrite NEVER turns an existing BLOCK into a
    silent allow, and OTHER destructive BLOCKs are unaffected by H5."""

    def test_rm_rf_still_blocks(self):
        d = cbs.decide_command("rm -rf /tmp/x")
        self.assertFalse(d.allow)
        self.assertIsNone(d.rewrite)

    def test_git_reset_hard_still_blocks(self):
        d = cbs.decide_command("git reset --hard")
        self.assertFalse(d.allow)
        self.assertIsNone(d.rewrite)

    def test_force_push_is_never_a_silent_allow(self):
        # The force-push decision is EITHER a rewrite-ask (allow+rewrite) OR a
        # BLOCK — it is NEVER allow=True with rewrite=None (a silent allow).
        for cmd in (
            "git push --force",
            "git push -f",
            'echo "--force" && git push -f',
            "git push --force && true",
        ):
            d = cbs.decide_command(cmd)
            silent_allow = d.allow and d.rewrite is None
            self.assertFalse(
                silent_allow, f"{cmd!r} degraded to a SILENT ALLOW"
            )


class TestKillSwitchRestoresBlock(TestEnvContext):
    """CEO_BASH_FORCE_PUSH_REWRITE=0 restores the legacy BLOCK (read from the
    import-time trusted_env snapshot)."""

    def test_killswitch_off_blocks(self):
        # Force the gate off by monkeypatching the snapshot-reader helper.
        orig = cbs._force_push_rewrite_enabled
        cbs._force_push_rewrite_enabled = lambda: False
        try:
            d = cbs.decide_command("git push --force")
            self.assertFalse(d.allow)
            self.assertIsNone(d.rewrite)
            self.assertIn("BLOCKED", d.reason)
        finally:
            cbs._force_push_rewrite_enabled = orig


class TestContractTranslationAskShape(TestEnvContext):
    """_to_contract_decision builds the `ask` + updatedInput vendor shape and
    preserves the original tool_input keys (constraint (c) — change only the
    command)."""

    def test_ask_shape_via_adapter(self):
        d = cbs.decide_command("git push --force")
        tool_input = {"command": "git push --force", "description": "deploy"}
        cd = cbs._to_contract_decision(d, tool_input)
        out = json.loads(cbs._claude_adapter.write_decision(cd))
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        self.assertEqual(hso["permissionDecision"], "ask")
        self.assertIn("force-with-lease", hso["permissionDecisionReason"])
        self.assertEqual(
            hso["updatedInput"]["command"], "git push --force-with-lease"
        )
        # original non-command keys preserved verbatim
        self.assertEqual(hso["updatedInput"]["description"], "deploy")
        # NEVER a top-level block/approve decision on the rewrite path
        self.assertNotIn("decision", out)

    def test_block_translation_unchanged(self):
        d = cbs.decide_command("rm -rf /tmp/x")
        cd = cbs._to_contract_decision(d, {"command": "rm -rf /tmp/x"})
        out = json.loads(cbs._claude_adapter.write_decision(cd))
        self.assertEqual(out["decision"], "block")
        self.assertNotIn("hookSpecificOutput", out)


class TestMainEntrypointAsk(TestEnvContext):
    """End-to-end main(): stdin → stdout `ask` shape + bash_input_rewritten
    audit emit fires with the before/after hash pair."""

    def _run_main(self, stdin_text):
        old_in, old_out = sys.stdin, sys.stdout
        sys.stdin = io.StringIO(stdin_text)
        sys.stdout = io.StringIO()
        try:
            rc = cbs.main()
        finally:
            out = sys.stdout.getvalue()
            sys.stdin, sys.stdout = old_in, old_out
        self.assertEqual(rc, 0)
        return json.loads(out.strip())

    def test_main_force_push_emits_ask_with_updated_input(self):
        payload = json.dumps({
            "session_id": "s1",
            "tool_name": "Bash",
            "tool_input": {"command": "git push --force origin main"},
        })
        out = self._run_main(payload)
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["permissionDecision"], "ask")
        self.assertEqual(
            hso["updatedInput"]["command"],
            "git push --force-with-lease origin main",
        )

    def test_main_emits_bash_input_rewritten_hash_pair(self):
        # Capture the audit emit: patch the typed wrapper on the live
        # audit_emit module the staged hook bound at import.
        captured = {}
        ae = cbs._audit_emit
        self.assertIsNotNone(ae, "audit_emit must be importable for this test")
        orig = ae.emit_bash_input_rewritten

        def _spy(**kw):
            captured.update(kw)

        ae.emit_bash_input_rewritten = _spy
        try:
            payload = json.dumps({
                "session_id": "s1",
                "tool_name": "Bash",
                "tool_input": {"command": "git push --force"},
            })
            self._run_main(payload)
        finally:
            ae.emit_bash_input_rewritten = orig
        self.assertEqual(captured.get("rewrite_class"), "git_push_force_to_lease")
        self.assertEqual(captured.get("before_sha256"), _sha("git push --force"))
        self.assertEqual(
            captured.get("after_sha256"), _sha("git push --force-with-lease")
        )
        # The command bytes must NOT be among the emitted kwargs.
        self.assertNotIn("command", captured)
        self.assertNotIn("new_command", captured)

    def test_main_compound_still_blocks(self):
        payload = json.dumps({
            "session_id": "s1",
            "tool_name": "Bash",
            "tool_input": {"command": 'echo "--force" && git push -f'},
        })
        out = self._run_main(payload)
        self.assertEqual(out["decision"], "block")
        self.assertNotIn("hookSpecificOutput", out)


class TestRewriteBuilderUnit(TestEnvContext):
    """_rewrite_git_push_force direct unit cases."""

    def test_none_for_non_push(self):
        self.assertIsNone(cbs._rewrite_git_push_force("git status"))

    def test_none_for_empty(self):
        self.assertIsNone(cbs._rewrite_git_push_force(""))

    def test_none_for_unparseable(self):
        # unbalanced quote → _tokenize returns [] → None (fail-safe).
        self.assertIsNone(cbs._rewrite_git_push_force('git push "--force'))

    def test_sha256_hex_helper_returns_64_hex(self):
        digest = cbs._sha256_hex("x")
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, _sha("x"))


if __name__ == "__main__":
    unittest.main()
