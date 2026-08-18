"""Unit tests for the PLAN-179 W2 US6 work-boundary ledger checkpoint hook.

What these tests hold down, in the order the plan argues for them:

1. **ADVISORY, never blocks.** No code path returns ``permissionDecision``
   at all — not ``deny``, not ``ask``. Asserted structurally (the whole
   output object) AND statically (the module source has no ``deny`` arm),
   because "it happens not to block in the cases I wrote" is not the claim.
2. **The trigger derives from PATHS** — a plan-dir path and an AC-listed
   path both fire; an unrelated path does not. Plus the r1-C6 guard as a
   STATIC assertion: the module must not mention ``resolve_plan_id``, the
   function whose session-coupling is the root cause PLAN-179 exists to fix.
3. **Skips are visible with a CLOSED-ENUM reason** — every reason the hook
   can emit is checked for membership in ``_SKIP_REASONS``, and the specific
   out-of-scope / hotfix / exploratory / opt-out / unparseable / kill-switch
   routes are each exercised.
4. **Kill switches** — ``CEO_LEDGER_CHECKPOINT=0`` still MEASURES the skip;
   ``CEO_SOTA_DISABLE=1`` is fully silent (the declared "instrument off").
5. **Honest degradation** — with the W2 ceremony unlanded (the actions are
   not in ``_KNOWN_ACTIONS``) the hook is LOUD: stderr, an advisory line and
   a ``systemMessage`` naming what is missing, instead of a silent telemetry
   hole in the window that decides the ledger's life.

Isolation: ``TestEnvContext`` (never the real ``$HOME`` / project dir). The
git-backed cases build a throwaway repo inside the per-test tmp tree.

Module resolution is CANONICAL-FIRST via ``_pick``: post-ceremony the live
``.claude/hooks/check_ledger_checkpoint.py`` carries the marker and wins;
pre-ceremony the staged source under ``PLAN-179/staged-w24/`` is used. One
file, two positions, no drifting second copy.
"""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

_THIS = Path(__file__).resolve()
_repo_root = None
for _parent in _THIS.parents:
    if (_parent / ".claude" / "hooks" / "_lib").is_dir() and (
        _parent / ".claude" / "plans"
    ).is_dir():
        _repo_root = _parent
        break
assert _repo_root is not None, "could not locate repo root from test path"

sys.path.insert(0, str(_repo_root / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

_CANONICAL = _repo_root / ".claude" / "hooks" / "check_ledger_checkpoint.py"
_STAGED = (
    _repo_root / ".claude" / "plans" / "PLAN-179" / "staged-w24"
    / ".claude" / "hooks" / "check_ledger_checkpoint.py"
)
_MARKER = "LEDGER_OMISSION_DEATH_THRESHOLD_PCT"


def _pick(canonical: Path, staged: Path, marker: str) -> Path:
    """Canonical if it exists AND carries the marker, else the staged source.

    Raises when neither has it — a genuine misconfiguration to surface, not
    something to skip past silently.
    """
    try:
        if canonical.is_file() and marker in canonical.read_text(encoding="utf-8"):
            return canonical
    except OSError:
        pass
    if staged.is_file() and marker in staged.read_text(encoding="utf-8"):
        return staged
    raise FileNotFoundError(
        "check_ledger_checkpoint not found in canonical (%s) or staged (%s); "
        "marker=%r" % (canonical, staged, marker)
    )


_HOOK_PATH = _pick(_CANONICAL, _STAGED, _MARKER)
_HOOK_SOURCE = _HOOK_PATH.read_text(encoding="utf-8")


def _load_hook():
    spec = importlib.util.spec_from_file_location(
        "check_ledger_checkpoint_under_test", _HOOK_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HOOK = _load_hook()

_GIT = shutil.which("git")


class _EmitRecorder(object):
    """Stand-in for ``_lib.audit_emit`` that RECORDS instead of writing.

    Carries a ``_KNOWN_ACTIONS`` set so the registered path can be exercised
    before the W2 ceremony registers the real actions. ``known=None``
    reproduces the pre-ceremony reality (actions absent).
    """

    def __init__(self, known: Optional[set] = None) -> None:
        if known is not None:
            self._KNOWN_ACTIONS = known
        self.calls = []  # type: List[Dict[str, Any]]

    def emit_generic(self, action: str, **fields: Any) -> None:
        payload = {"action": action}
        payload.update(fields)
        self.calls.append(payload)


class LedgerCheckpointTestBase(TestEnvContext):
    """Shared fixture: an isolated git repo + a plan tree inside it."""

    def setUp(self) -> None:
        super().setUp()
        self.recorder = _EmitRecorder(
            known={HOOK.ACTION_RECORDED, HOOK.ACTION_SKIPPED}
        )
        self._patches = [
            mock.patch.object(HOOK, "_audit_emit", self.recorder),
            mock.patch.object(HOOK, "_AUDIT_EMIT_AVAILABLE", True),
        ]
        for patcher in self._patches:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in reversed(self._patches):
            patcher.stop()
        super().tearDown()

    # -- helpers ----------------------------------------------------------

    def git(self, *args: str) -> None:
        assert _GIT is not None
        subprocess.run(
            [_GIT] + list(args),
            cwd=str(self.project_dir),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def init_repo(self) -> None:
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.git("config", "commit.gpgsign", "false")
        self.write_project_file("README.md", "seed\n")
        self.git("add", "README.md")
        self.git("commit", "-q", "-m", "seed")

    def stage(self, relative: str, content: str = "x\n") -> None:
        self.write_project_file(relative, content)
        self.git("add", "--", relative)

    def run_gate(self, command: str = 'git commit -m "feat: work"') -> Dict[str, Any]:
        event = {"tool_name": "Bash", "tool_input": {"command": command}}
        return HOOK.gate(event, cwd=str(self.project_dir))

    def events(self, action: Optional[str] = None) -> List[Dict[str, Any]]:
        if action is None:
            return list(self.recorder.calls)
        return [c for c in self.recorder.calls if c.get("action") == action]

    def assert_never_blocks(self, out: Dict[str, Any]) -> None:
        """The single invariant this rail must never violate."""
        self.assertNotIn("permissionDecision", json.dumps(out))
        self.assertNotIn("decision", out)
        self.assertNotEqual(out.get("continue"), False)
        specific = out.get("hookSpecificOutput") or {}
        self.assertNotIn("permissionDecision", specific)
        self.assertNotIn("permissionDecisionReason", specific)


# --------------------------------------------------------------------------
# 1. Advisory — never blocks
# --------------------------------------------------------------------------

class TestAdvisoryNeverBlocks(LedgerCheckpointTestBase):

    def test_module_has_no_deny_arm_at_all(self) -> None:
        """Static: the deny branch must not exist yet (enforce is a FUTURE
        ceremony). A test over sampled inputs cannot prove absence."""
        self.assertNotIn('"deny"', _HOOK_SOURCE)
        self.assertNotIn("'deny'", _HOOK_SOURCE)
        self.assertNotIn("permissionDecision\": \"ask\"", _HOOK_SOURCE)
        self.assertFalse(HOOK.ENFORCE_FLIP_IMPLEMENTED)

    @unittest.skipUnless(_GIT, "git not available")
    def test_missing_ledger_advises_but_does_not_block(self) -> None:
        self.init_repo()
        self.write_project_file(
            ".claude/plans/PLAN-900/LEDGER.md", "# LEDGER\n\n- current unit\n"
        )
        self.stage(".claude/plans/PLAN-900/notes.md")
        out = self.run_gate()
        self.assert_never_blocks(out)
        self.assertIn("ADVISORY", out["hookSpecificOutput"]["additionalContext"])
        recorded = self.events(HOOK.ACTION_RECORDED)
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["outcome"], "ledger_missing")
        # The would-block column the future flip ceremony has to table.
        self.assertEqual(recorded[0]["would_block"], 1)

    @unittest.skipUnless(_GIT, "git not available")
    def test_enforce_env_set_today_still_does_not_block(self) -> None:
        """The flip env exists; the flip does not. Setting it is LOUD but
        changes no decision — the window is still open."""
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# LEDGER\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        os.environ[HOOK.ENFORCE_ENV] = "1"
        stderr = io.StringIO()
        with mock.patch.object(sys, "stderr", stderr):
            out = self.run_gate()
        self.assert_never_blocks(out)
        self.assertIn("enforce flip is NOT implemented", stderr.getvalue())

    @unittest.skipUnless(_GIT, "git not available")
    def test_ledger_updated_is_silent_in_the_session(self) -> None:
        """A commit that DOES carry the checkpoint gets no advisory noise —
        only the audit event the window counts."""
        self.init_repo()
        self.stage(".claude/plans/PLAN-900/LEDGER.md", "# LEDGER\n\n- unit U1\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        out = self.run_gate()
        self.assertEqual(out, {})
        recorded = self.events(HOOK.ACTION_RECORDED)
        self.assertEqual(recorded[0]["outcome"], "ledger_updated")
        self.assertEqual(recorded[0]["would_block"], 0)

    def test_main_fails_open_on_garbage_stdin(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO("not json")), \
                mock.patch.object(sys, "stdout", stdout), \
                mock.patch.object(sys, "stderr", stderr):
            HOOK.main()
        self.assertEqual(stdout.getvalue().strip(), "{}")

    def test_non_bash_tool_is_ignored(self) -> None:
        out = HOOK.gate(
            {"tool_name": "Edit", "tool_input": {"file_path": "x"}},
            cwd=str(self.project_dir),
        )
        self.assertEqual(out, {})
        self.assertEqual(self.events(), [])


# --------------------------------------------------------------------------
# 2. The trigger derives from PATHS (emenda r1-C6)
# --------------------------------------------------------------------------

class TestTriggerDerivesFromPaths(LedgerCheckpointTestBase):

    def test_module_never_calls_resolve_plan_id(self) -> None:
        """r1-C6, as an AST-level guard. ``resolve_plan_id`` needs a
        ``plan_transition`` from the same session (~0 per real session,
        S309): routing the trigger through it would re-inherit in W2 the
        exact root cause PLAN-179 exists to cure.

        Checked over NAMES, ATTRIBUTES, IMPORTS and exact STRING CONSTANTS
        (the ``getattr`` back door), not over raw source — the module
        docstring is required to NAME the ban, and a grep-level test would
        make documenting it impossible.
        """
        tree = ast.parse(_HOOK_SOURCE)
        names = set()  # type: set
        imports = set()  # type: set
        constants = set()  # type: set
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module or "")
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                constants.add(node.value)
        self.assertNotIn("resolve_plan_id", names)
        self.assertNotIn("resolve_plan_id", imports)
        self.assertNotIn("resolve_plan_id", constants)
        self.assertEqual([m for m in imports if "scratchpad" in m], [])
        # ...and the ban is DOCUMENTED, so it is not silently reversed later.
        self.assertIn("resolve_plan_id", ast.get_docstring(tree) or "")

    @unittest.skipUnless(_GIT, "git not available")
    def test_fires_on_plan_directory_path(self) -> None:
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/floor.md")
        self.run_gate()
        recorded = self.events(HOOK.ACTION_RECORDED)
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["plan_id"], "PLAN-900")
        self.assertEqual(recorded[0]["scope_source"], "plan_dir")
        self.assertEqual(recorded[0]["in_scope_path_count"], 1)

    @unittest.skipUnless(_GIT, "git not available")
    def test_fires_on_path_listed_in_a_plan_ac(self) -> None:
        """Scope rule (b): a path named by an AC ``[P?][USn][path]`` line."""
        self.init_repo()
        self.write_project_file(
            ".claude/plans/PLAN-901-some-slug.md",
            "# PLAN-901\n\n"
            "- [ ] `[P1][US6][.claude/hooks/some_new_hook.py]`\n"
            "      A unit of work.\n",
        )
        self.write_project_file(".claude/plans/PLAN-901/LEDGER.md", "# L\n")
        self.stage(".claude/hooks/some_new_hook.py")
        self.run_gate()
        recorded = self.events(HOOK.ACTION_RECORDED)
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["plan_id"], "PLAN-901")
        self.assertEqual(recorded[0]["scope_source"], "plan_ac")

    @unittest.skipUnless(_GIT, "git not available")
    def test_does_not_fire_out_of_scope(self) -> None:
        self.init_repo()
        self.stage("src/unrelated.py", "print(1)\n")
        out = self.run_gate()
        self.assertEqual(out, {})
        self.assertEqual(self.events(HOOK.ACTION_RECORDED), [])
        skipped = self.events(HOOK.ACTION_SKIPPED)
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0]["reason"], "out_of_scope_paths")

    def test_derive_scope_is_deterministic_on_ties(self) -> None:
        """Two plans, one path each: the lowest plan id wins, always."""
        root = self.project_dir
        (root / ".claude" / "plans").mkdir(parents=True, exist_ok=True)
        plan_id, source, in_scope = HOOK.derive_scope(
            [
                ".claude/plans/PLAN-902/a.md",
                ".claude/plans/PLAN-901/b.md",
            ],
            root,
            deadline=HOOK.time.monotonic() + 5,
        )
        self.assertEqual(plan_id, "PLAN-901")
        self.assertEqual(source, "plan_dir")
        self.assertEqual(in_scope, [".claude/plans/PLAN-901/b.md"])

    def test_plan_file_only_commit_is_a_declared_false_negative(self) -> None:
        """The plan text names ``PLAN-NNN/**`` and AC paths — the plan FILE
        itself is deliberately NOT a third rule. Pinned so widening it is a
        named amendment, never a silent edit."""
        plan_id, _source, _paths = HOOK.derive_scope(
            [".claude/plans/PLAN-179-context-continuity-durable-state.md"],
            self.project_dir,
            deadline=HOOK.time.monotonic() + 5,
        )
        self.assertIsNone(plan_id)


# --------------------------------------------------------------------------
# 3. Skips are VISIBLE, with a closed-enum reason
# --------------------------------------------------------------------------

class TestSkipReasonsAreClosedEnum(LedgerCheckpointTestBase):

    def _only_skip(self) -> Dict[str, Any]:
        skipped = self.events(HOOK.ACTION_SKIPPED)
        self.assertEqual(len(skipped), 1, skipped)
        event = skipped[0]
        # The invariant, on every route: reason is a member of the closed set.
        self.assertIn(event["reason"], HOOK._SKIP_REASONS)
        self.assertIn(event["state_kind"], HOOK._STATE_KINDS)
        self.assertIsInstance(event["commits_since_last_observation"], int)
        self.assertNotIsInstance(
            event["commits_since_last_observation"], bool
        )
        return event

    @unittest.skipUnless(_GIT, "git not available")
    def test_hotfix_marker_is_recorded_not_silent(self) -> None:
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        out = self.run_gate('git commit -m "hotfix: restore the gate"')
        self.assertEqual(out, {})
        self.assertEqual(self._only_skip()["reason"], "hotfix")

    @unittest.skipUnless(_GIT, "git not available")
    def test_exploratory_marker_is_recorded(self) -> None:
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        self.run_gate('git commit -m "wip: trying something"')
        self.assertEqual(self._only_skip()["reason"], "exploratory")

    @unittest.skipUnless(_GIT, "git not available")
    def test_explicit_opt_out_tag_is_its_own_reason(self) -> None:
        """An explicit opt-out must not be confused with a heuristic guess —
        the TP/FP table needs the two apart."""
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        self.run_gate('git commit -m "docs: tidy [skip-ledger]"')
        self.assertEqual(self._only_skip()["reason"], "operator_opt_out")

    @unittest.skipUnless(_GIT, "git not available")
    def test_hotfix_out_of_scope_counts_as_out_of_scope(self) -> None:
        """Ordering guard: the exemption is classified AFTER scope, so the
        hotfix rate is not inflated by commits the rail never wanted."""
        self.init_repo()
        self.stage("src/unrelated.py")
        self.run_gate('git commit -m "hotfix: unrelated"')
        self.assertEqual(self._only_skip()["reason"], "out_of_scope_paths")

    @unittest.skipUnless(_GIT, "git not available")
    def test_foreign_repo_commit_is_unparseable_not_a_guess(self) -> None:
        self.init_repo()
        self.stage(".claude/plans/PLAN-900/notes.md")
        self.run_gate('git -C /somewhere/else commit -m "x"')
        self.assertEqual(self._only_skip()["reason"], "unparseable")

    @unittest.skipUnless(_GIT, "git not available")
    def test_explicit_pathspecs_are_unparseable(self) -> None:
        self.init_repo()
        self.stage(".claude/plans/PLAN-900/notes.md")
        self.run_gate('git commit -m "x" -- .claude/plans/PLAN-900/notes.md')
        self.assertEqual(self._only_skip()["reason"], "unparseable")

    def test_unbalanced_quote_is_unparseable(self) -> None:
        self.run_gate('git commit -m "unterminated')
        self.assertEqual(self._only_skip()["reason"], "unparseable")

    def test_no_repo_is_named_not_swallowed(self) -> None:
        """No git repo under the project dir: the hook says ``no_repo``
        rather than pretending the commit was out of scope."""
        self.run_gate()
        self.assertEqual(self._only_skip()["reason"], "no_repo")

    def test_non_commit_bash_emits_nothing(self) -> None:
        """The ONE deliberate silence: every Bash call reaches this hook, so
        a skip event per `ls` would drown the log the window has to read."""
        out = self.run_gate("ls -la")
        self.assertEqual(out, {})
        self.assertEqual(self.events(), [])

    def test_quoted_mention_of_git_commit_does_not_trigger(self) -> None:
        out = self.run_gate('echo "git commit -m x"')
        self.assertEqual(out, {})
        self.assertEqual(self.events(), [])

    def test_every_skip_reason_in_the_enum_is_reachable_or_named(self) -> None:
        """The closed set is small enough to state; drift in either
        direction is caught here rather than at read time in the report."""
        self.assertEqual(
            set(HOOK._SKIP_REASONS),
            {
                "out_of_scope_paths", "kill_switch", "hotfix", "exploratory",
                "operator_opt_out", "unparseable", "budget_exhausted",
                "no_repo", "other",
            },
        )


# --------------------------------------------------------------------------
# 4. Kill switches
# --------------------------------------------------------------------------

class TestKillSwitches(LedgerCheckpointTestBase):

    @unittest.skipUnless(_GIT, "git not available")
    def test_rail_kill_switch_still_measures_the_skip(self) -> None:
        """`CEO_LEDGER_CHECKPOINT=0` stops the ADVICE, not the measurement —
        "the rail was off" is itself a fact the window needs."""
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        os.environ[HOOK.KILL_SWITCH_ENV] = "0"
        out = self.run_gate()
        self.assertEqual(out, {})
        skipped = self.events(HOOK.ACTION_SKIPPED)
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0]["reason"], "kill_switch")

    @unittest.skipUnless(_GIT, "git not available")
    def test_master_kill_is_completely_silent(self) -> None:
        """`CEO_SOTA_DISABLE=1` is the operator's real off switch: no event,
        no advisory, no state write."""
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        os.environ[HOOK.MASTER_KILL_ENV] = "1"
        out = self.run_gate()
        self.assertEqual(out, {})
        self.assertEqual(self.events(), [])
        self.assertFalse(
            (self.project_dir / ".claude" / "state"
             / "ledger-checkpoint.json").exists()
        )

    @unittest.skipUnless(_GIT, "git not available")
    def test_master_kill_beats_the_enforce_env(self) -> None:
        self.init_repo()
        self.stage(".claude/plans/PLAN-900/notes.md")
        os.environ[HOOK.MASTER_KILL_ENV] = "1"
        os.environ[HOOK.ENFORCE_ENV] = "1"
        self.assertEqual(self.run_gate(), {})
        self.assertEqual(self.events(), [])


# --------------------------------------------------------------------------
# 5. Censored universe + observation state
# --------------------------------------------------------------------------

class TestCensoredUniverseCounter(LedgerCheckpointTestBase):

    @unittest.skipUnless(_GIT, "git not available")
    def test_first_observation_is_fresh_and_zero_is_structural(self) -> None:
        self.init_repo()
        self.stage("src/x.py")
        self.run_gate()
        event = self.events(HOOK.ACTION_SKIPPED)[0]
        self.assertEqual(event["state_kind"], "fresh")
        self.assertEqual(event["commits_since_last_observation"], 0)

    @unittest.skipUnless(_GIT, "git not available")
    def test_commits_made_outside_the_hook_are_counted_next_time(self) -> None:
        """The Owner's ``!`` commits never reach the hook. The delta against
        the previous anchor is how the window learns its own blind spot."""
        self.init_repo()
        self.stage("src/x.py")
        self.run_gate()                      # anchor
        # Three commits land WITHOUT passing through the hook.
        for i in range(3):
            self.write_project_file("src/x%d.py" % i, "y\n")
            self.git("add", "-A")
            self.git("commit", "-q", "-m", "outside %d" % i)
        self.recorder.calls = []
        self.stage("src/z.py")
        self.run_gate()
        event = self.events(HOOK.ACTION_SKIPPED)[0]
        self.assertEqual(event["state_kind"], "resumed")
        self.assertEqual(event["commits_since_last_observation"], 3)

    def test_counter_is_int_and_clamped(self) -> None:
        self.assertEqual(HOOK._clamp_count(1000), 99)
        self.assertEqual(HOOK._clamp_count(-5), 0)
        self.assertEqual(HOOK._clamp_count(True), 0)
        self.assertEqual(HOOK._clamp_count("7"), 7)
        self.assertIsInstance(HOOK._clamp_count(3.9), int)


# --------------------------------------------------------------------------
# 6. Ledger content rules: size ceiling + named verifier
# --------------------------------------------------------------------------

class TestLedgerContentRules(LedgerCheckpointTestBase):

    def test_death_criterion_and_window_are_named_constants(self) -> None:
        self.assertIsInstance(HOOK.LEDGER_OMISSION_DEATH_THRESHOLD_PCT, int)
        self.assertTrue(0 < HOOK.LEDGER_OMISSION_DEATH_THRESHOLD_PCT < 100)
        self.assertEqual(HOOK.ADVISORY_WINDOW_MIN_DAYS, 30)
        self.assertEqual(HOOK.ADVISORY_WINDOW_MIN_SESSIONS, 20)
        self.assertEqual(
            HOOK.LEDGER_MAX_BYTES,
            HOOK.LEDGER_MAX_TOKENS * HOOK.LEDGER_BYTES_PER_TOKEN,
        )

    @unittest.skipUnless(_GIT, "git not available")
    def test_oversized_ledger_advises_archiving(self) -> None:
        self.init_repo()
        big = "- fact %d\n" % 0
        self.stage(
            ".claude/plans/PLAN-900/LEDGER.md",
            "# L\n" + big * (HOOK.LEDGER_MAX_BYTES // len(big) + 10),
        )
        out = self.run_gate()
        self.assert_never_blocks(out)
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("LEDGER-ARCHIVE.md", context)
        recorded = self.events(HOOK.ACTION_RECORDED)[0]
        self.assertEqual(recorded["over_ceiling"], 1)
        self.assertGreater(recorded["ledger_size_bucket_kib"], 0)

    def test_ac_claim_without_a_verifier_is_counted(self) -> None:
        text = (
            "- AC-3 satisfied\n"
            "- AC-4 satisfied (verifier: `bash gate.sh` exit=0)\n"
            "- US6 landed\n"
            "  verifier: `pytest -q tests/x.py` exit=0\n"
            "- an ordinary note with no claim\n"
        )
        self.assertEqual(HOOK.count_unverified_ac_claims(text), 1)

    @unittest.skipUnless(_GIT, "git not available")
    def test_unverified_claim_reaches_the_advisory_and_the_wire(self) -> None:
        self.init_repo()
        self.stage(
            ".claude/plans/PLAN-900/LEDGER.md",
            "# L\n\n- AC-1 satisfied\n- AC-2 satisfied\n",
        )
        out = self.run_gate()
        self.assert_never_blocks(out)
        self.assertIn(
            "verifier", out["hookSpecificOutput"]["additionalContext"]
        )
        self.assertEqual(
            self.events(HOOK.ACTION_RECORDED)[0]["unverified_ac_claim_count"], 2
        )

    @unittest.skipUnless(_GIT, "git not available")
    def test_no_ledger_content_reaches_the_audit_wire(self) -> None:
        """Repo is PUBLIC: the wire carries closed enums + ints + ids only."""
        self.init_repo()
        secret = "CANARY-LEDGER-BODY-SHOULD-NEVER-TRAVEL"
        self.stage(".claude/plans/PLAN-900/LEDGER.md", "# L\n\n- %s\n" % secret)
        self.run_gate('git commit -m "feat: %s"' % secret)
        blob = json.dumps(self.events())
        self.assertNotIn(secret, blob)
        for event in self.events():
            for key, value in event.items():
                if key == "action":
                    continue
                self.assertNotIn("/", str(value), (key, value))


# --------------------------------------------------------------------------
# 7. Honest degradation when the W2 ceremony has not landed
# --------------------------------------------------------------------------

class TestHonestDegradation(LedgerCheckpointTestBase):

    @unittest.skipUnless(_GIT, "git not available")
    def test_unregistered_action_is_loud_on_three_channels(self) -> None:
        """audit_emit.py is canonical and lands with the W2 ceremony. Until
        then the emit is dropped — and a silent drop would corrupt the very
        number the window exists to produce."""
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        unregistered = _EmitRecorder(known={"some_other_action"})
        stderr = io.StringIO()
        with mock.patch.object(HOOK, "_audit_emit", unregistered), \
                mock.patch.object(sys, "stderr", stderr):
            out = self.run_gate()
        self.assert_never_blocks(out)
        self.assertEqual(unregistered.calls, [])          # nothing emitted
        self.assertIn("NOT registered", stderr.getvalue())  # 1. stderr
        self.assertIn("audit_emit.py", stderr.getvalue())
        self.assertIn(
            "INSTRUMENT DEFECT",
            out["hookSpecificOutput"]["additionalContext"],               # 2.
        )
        self.assertIn("unregistered", out["systemMessage"])               # 3.

    @unittest.skipUnless(_GIT, "git not available")
    def test_audit_emit_unavailable_is_loud_and_still_advisory(self) -> None:
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        stderr = io.StringIO()
        with mock.patch.object(HOOK, "_AUDIT_EMIT_AVAILABLE", False), \
                mock.patch.object(sys, "stderr", stderr):
            out = self.run_gate()
        self.assert_never_blocks(out)
        self.assertIn("audit_emit unavailable", stderr.getvalue())
        self.assertIn("unavailable", out["systemMessage"])

    @unittest.skipUnless(_GIT, "git not available")
    def test_git_failure_fails_open_without_an_exception(self) -> None:
        self.init_repo()
        self.stage(".claude/plans/PLAN-900/notes.md")
        with mock.patch.object(HOOK, "_git", return_value=None):
            out = self.run_gate()
        self.assertEqual(out, {})
        self.assertEqual(self._skip_reason(), "no_repo")

    def _skip_reason(self) -> str:
        skipped = self.events(HOOK.ACTION_SKIPPED)
        self.assertEqual(len(skipped), 1)
        return skipped[0]["reason"]


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
