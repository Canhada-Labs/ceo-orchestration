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
import re
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

    def run_gate(
        self,
        command: str = 'git commit -m "feat: work"',
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        event = {"tool_name": "Bash", "tool_input": {"command": command}}
        if session_id is not None:
            event["session_id"] = session_id
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
        stderr = io.StringIO()
        with mock.patch.dict(os.environ, {HOOK.ENFORCE_ENV: "1"}), \
                mock.patch.object(sys, "stderr", stderr):
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

    @unittest.skipUnless(_GIT, "git not available")
    def test_pathspec_from_file_is_a_commit_selector(self) -> None:
        """Pair-rail do main, rodada 3, P2 — o registro FALSO que isto fecha.

        `--pathspec-from-file` FORNECE os paths do commit. Consumi-la como
        opcao de valor comum deixava `inv.pathspecs` vazio, entao
        `_committed_paths()` devolvia o conjunto staged INTEIRO: um LEDGER.md
        staged mas EXCLUIDO pelo arquivo geraria `ledger_updated` para um
        commit que nao o conteria. A resposta certa e a que o modulo ja da
        para pathspec explicito: `unparseable`.
        """
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        for command in (
            'git commit --pathspec-from-file=paths.txt -m "feat: work"',
            'git commit --pathspec-from-file paths.txt -m "feat: work"',
        ):
            with self.subTest(command=command):
                self.recorder.calls = []
                self.run_gate(command)
                self.assertEqual(
                    self._only_skip()["reason"], "unparseable",
                    "o commit e dirigido por um arquivo de pathspec e mesmo "
                    "assim foi classificado pelo conjunto staged: %s" % command,
                )
                self.assertEqual(self.events(HOOK.ACTION_RECORDED), [])

    def test_unbalanced_quote_is_unparseable(self) -> None:
        self.run_gate('git commit -m "unterminated')
        self.assertEqual(self._only_skip()["reason"], "unparseable")

    @unittest.skipUnless(_GIT, "git not available")
    def test_value_bearing_options_do_not_become_pathspecs(self) -> None:
        """Pair-rail round 1, P2 — the bias this closes.

        ``--author``/``--date``/``--file`` take their value as a SEPARATE
        token. Skipping only the option name left the VALUE to be read as a
        pathspec, and an explicit pathspec makes the hook report
        ``unparseable`` — so an ordinary ``git commit --author X -m msg``
        vanished from the OBSERVED universe as a skip, biasing the very
        window this rail exists to measure.
        """
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        for command in (
            'git commit --author "A U Thor <a@b.invalid>" -m "feat: work"',
            'git commit --date "2026-08-25T00:00:00Z" -m "feat: work"',
            'git commit --cleanup verbatim -m "feat: work"',
        ):
            with self.subTest(command=command):
                self.recorder.calls = []
                self.run_gate(command)
                reasons = [e.get("reason") for e in self.events(HOOK.ACTION_SKIPPED)]
                self.assertNotIn(
                    "unparseable", reasons,
                    "the option VALUE was read as a pathspec: %s" % command,
                )
                self.assertEqual(len(self.events(HOOK.ACTION_RECORDED)), 1)

    @unittest.skipUnless(_GIT, "git not available")
    def test_equals_form_of_a_value_option_still_works(self) -> None:
        """``--author=X`` is ONE token; the generic ``--`` branch already
        skipped it. Consuming a second token for it would eat a real
        pathspec — the opposite error."""
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        self.run_gate('git commit --author="A <a@b.invalid>" -m "feat: work"')
        self.assertEqual(len(self.events(HOOK.ACTION_RECORDED)), 1)

    @unittest.skipUnless(_GIT, "git not available")
    def test_a_real_pathspec_is_still_unparseable(self) -> None:
        """Control in the other direction: consuming option values must not
        make the hook blind to an ACTUAL explicit pathspec."""
        self.init_repo()
        self.stage(".claude/plans/PLAN-900/notes.md")
        self.run_gate(
            'git commit --author "A <a@b.invalid>" -m "x" '
            '-- .claude/plans/PLAN-900/notes.md'
        )
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

class TestRepoRootIsTheGitTopLevel(LedgerCheckpointTestBase):
    """Pair-rail round 2, P1 — the event's ``cwd`` is not the repo root.

    A ``CwdChanged`` into a subdirectory used to make every filesystem lookup
    point at that subdirectory while git kept answering ROOT-relative. Result:
    AC-scoped commits skipped, an existing ledger reported absent, and the
    observation state written into a nested un-gitignored directory.
    """

    @unittest.skipUnless(_GIT, "git not available")
    def test_commit_from_a_subdirectory_is_still_in_scope(self) -> None:
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        subdir = self.project_dir / "src" / "deep"
        subdir.mkdir(parents=True, exist_ok=True)

        event = {"tool_name": "Bash",
                 "tool_input": {"command": 'git commit -m "feat: work"'}}
        HOOK.gate(event, cwd=str(subdir))

        recorded = self.events(HOOK.ACTION_RECORDED)
        self.assertEqual(
            len(recorded), 1,
            "a commit observed from a subdirectory produced no recorded "
            "event — the scope derivation followed cwd instead of the git "
            "top level: %r" % (self.events(),),
        )
        # The discriminating value: `ledger_missing` means the ledger was
        # FOUND on disk and simply not updated by this commit.
        # `ledger_absent_from_plan` is the BUG's signature — it is what you
        # get when the lookup happened under the subdirectory.
        self.assertEqual(
            recorded[0]["outcome"], "ledger_missing",
            "the existing ledger was not found — the lookup used the "
            "subdirectory instead of the repo root",
        )

    @unittest.skipUnless(_GIT, "git not available")
    def test_ledger_staged_from_a_subdirectory_reads_as_updated(self) -> None:
        self.init_repo()
        self.stage(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        subdir = self.project_dir / "src" / "deep"
        subdir.mkdir(parents=True, exist_ok=True)

        event = {"tool_name": "Bash",
                 "tool_input": {"command": 'git commit -m "feat: work"'}}
        HOOK.gate(event, cwd=str(subdir))

        recorded = self.events(HOOK.ACTION_RECORDED)
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["outcome"], "ledger_updated")

    @unittest.skipUnless(_GIT, "git not available")
    def test_state_is_written_at_the_top_level_not_under_the_subdir(self) -> None:
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        subdir = self.project_dir / "src" / "deep"
        subdir.mkdir(parents=True, exist_ok=True)

        event = {"tool_name": "Bash",
                 "tool_input": {"command": 'git commit -m "feat: work"'}}
        HOOK.gate(event, cwd=str(subdir))

        self.assertFalse(
            (subdir / ".claude" / "state").exists(),
            "observation state fragmented into a nested directory",
        )
        self.assertTrue((self.project_dir / ".claude" / "state").exists())


class TestEnvPrefixedCommitsAreSeen(LedgerCheckpointTestBase):
    """Pair-rail round 2, P2 — `GIT_EDITOR=true git commit` is ordinary shell.

    An assignment or a thin wrapper before ``git`` used to clear the command
    position, so the ``git`` after it was never recognised. The commit then
    got NEITHER an advisory NOR a skip event — it disappeared from the
    observed universe, which is the one outcome this rail must never produce
    for a real commit.
    """

    @unittest.skipUnless(_GIT, "git not available")
    def test_assignment_and_wrapper_prefixes_still_trigger(self) -> None:
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        for command in (
            'GIT_EDITOR=true git commit -m "feat: work"',
            'FOO=1 BAR=2 git commit -m "feat: work"',
            'env FOO=1 git commit -m "feat: work"',
            # Pair-rail do main, rodada 2: consumir so o NOME do wrapper
            # deixava a OPCAO dele limpar a posicao de comando.
            'env -i FOO=1 git commit -m "feat: work"',
            'env -u LESS git commit -m "feat: work"',
            'command -- git commit -m "feat: work"',
            'stdbuf -oL git commit -m "feat: work"',
            'nohup git commit -m "feat: work"',
        ):
            with self.subTest(command=command):
                self.recorder.calls = []
                self.run_gate(command)
                self.assertEqual(
                    len(self.events(HOOK.ACTION_RECORDED)), 1,
                    "the commit vanished from the observed universe: %s"
                    % command,
                )

    def test_an_assignment_alone_is_still_silent(self) -> None:
        """Control in the other direction: an assignment that is NOT followed
        by a git commit must stay silent, as every non-commit Bash call does."""
        out = self.run_gate('GIT_EDITOR=true echo hello')
        self.assertEqual(out, {})
        self.assertEqual(self.events(), [])


class TestDeathCriterionAgreesWithTheADR(TestEnvContext):
    """Pair-rail round 1, P2 — code and doctrine must name the SAME number.

    Base is ``TestEnvContext`` and not ``unittest.TestCase`` even though
    this class touches no environment: `check-test-env-hygiene.py` flags a
    bare ``TestCase`` under `.claude/hooks/tests/` as a `bare-testcase`
    violation and exits 1, and the land script runs that checker in V6d.
    Found by pair-rail round 3 — the cure for one rail finding introduced
    a blocker of its own, which is why the rail runs again after a cure.

    `LEDGER_OMISSION_DEATH_THRESHOLD_PCT` read 30 while ADR-195 §3.2 M1 read
    33. A measured omission rate in (30, 33] therefore produced OPPOSITE
    keep/remove verdicts depending on which authority the report quoted —
    and the previous test only asserted 0 < value < 100, which both numbers
    satisfy. A range check cannot catch a disagreement; only reading the
    other authority can.
    """

    def _adr_text(self) -> str:
        canonical = _repo_root / ".claude" / "adr" / "ADR-195-work-boundary-persistence.md"
        staged = (
            _repo_root / ".claude" / "plans" / "PLAN-179" / "staged-w24"
            / ".claude" / "adr" / "ADR-195-work-boundary-persistence.md"
        )
        for path in (canonical, staged):
            try:
                if path.is_file():
                    return path.read_text(encoding="utf-8")
            except OSError:
                continue
        self.fail(
            "ADR-195 found in neither the canonical tree (%s) nor the staged "
            "pack (%s) — the death criterion has no doctrine to agree with"
            % (canonical, staged)
        )

    def test_threshold_matches_adr_195_m1(self) -> None:
        text = self._adr_text()
        matches = re.findall(r"M1 — omiss[^\n]*?>\s*(\d+)\s*%", text)
        self.assertEqual(
            len(matches), 1,
            "expected exactly one M1 threshold statement in ADR-195 §3.2, "
            "found %d — the parser or the ADR changed shape" % len(matches),
        )
        self.assertEqual(
            int(matches[0]), HOOK.LEDGER_OMISSION_DEATH_THRESHOLD_PCT,
            "ADR-195 M1 says %s%% and the code says %s%% — a rate between "
            "them decides the ledger's life differently depending on which "
            "one the report quotes"
            % (matches[0], HOOK.LEDGER_OMISSION_DEATH_THRESHOLD_PCT),
        )

    def test_threshold_is_a_sane_percentage(self) -> None:
        value = HOOK.LEDGER_OMISSION_DEATH_THRESHOLD_PCT
        self.assertIsInstance(value, int)
        self.assertGreater(value, 0)
        self.assertLess(value, 100)


class TestSessionIdentityOnEvents(LedgerCheckpointTestBase):
    """Pair-rail round 1, P1 — the window is counted in SESSIONS.

    The advisory window this rail declares is ">= 20 sessions". A row with
    no ``session_id`` cannot be counted into a session nor partitioned by
    project, so emitting the window's telemetry without those fields would
    repeat the very session-coupling failure PLAN-179 exists to cure. Both
    allowlists already admit the two fields; only the caller was missing.
    """

    @unittest.skipUnless(_GIT, "git not available")
    def test_recorded_carries_the_session_id(self) -> None:
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        self.run_gate(session_id="sess-abc123")
        recorded = self.events(HOOK.ACTION_RECORDED)
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["session_id"], "sess-abc123")
        # `project` is deliberately NOT on the wire: this rail forbids paths
        # (test_no_ledger_content_reaches_the_audit_wire), and since PLAN-182
        # W1 the audit dir + HMAC key are already per project, so rows are
        # partitioned by LOCATION. See the note on `_IDENTITY` in the hook.
        self.assertNotIn("project", recorded[0])

    @unittest.skipUnless(_GIT, "git not available")
    def test_skipped_carries_the_session_id(self) -> None:
        self.init_repo()
        self.stage("src/unrelated.py")
        self.run_gate(session_id="sess-xyz789")
        skipped = self.events(HOOK.ACTION_SKIPPED)
        self.assertGreaterEqual(len(skipped), 1)
        self.assertEqual(skipped[0]["session_id"], "sess-xyz789")

    @unittest.skipUnless(_GIT, "git not available")
    def test_absent_session_id_is_empty_never_missing(self) -> None:
        """No id in the hook event is a KNOWN empty, not an absent field:
        a consumer counting sessions must be able to tell 'no id' from
        'field never emitted'."""
        self.init_repo()
        self.stage("src/unrelated.py")
        self.run_gate()
        skipped = self.events(HOOK.ACTION_SKIPPED)
        self.assertGreaterEqual(len(skipped), 1)
        self.assertIn("session_id", skipped[0])
        self.assertEqual(skipped[0]["session_id"], "")

    @unittest.skipUnless(_GIT, "git not available")
    def test_session_id_reaching_the_chain_is_bounded(self) -> None:
        """The id lands in an HMAC-chained record. Unbounded free text from
        hook input has no business there: identifier characters only, and
        hard-capped."""
        self.init_repo()
        self.stage("src/unrelated.py")
        self.run_gate(session_id="a/../b " + ("z" * 200) + "\n<script>")
        skipped = self.events(HOOK.ACTION_SKIPPED)
        got = skipped[0]["session_id"]
        self.assertLessEqual(len(got), HOOK._SESSION_ID_MAX)
        self.assertTrue(set(got) <= HOOK._SESSION_ID_OK, got[:40])
        self.assertNotIn("/", got)
        self.assertNotIn("<", got)

    def test_identity_is_captured_before_the_master_kill_returns(self) -> None:
        """`_set_identity` runs FIRST in `gate`, so a later emitter added
        above the kill-switch branch cannot inherit a stale id from the
        previous invocation."""
        source = _HOOK_SOURCE
        gate_at = source.index("def gate(")
        body = source[gate_at:]
        set_at = body.index("_set_identity(event)")
        kill_at = body.index("MASTER_KILL_ENV")
        self.assertLess(
            set_at, kill_at,
            "_set_identity must precede the master-kill early return",
        )


class TestKillSwitches(LedgerCheckpointTestBase):

    @unittest.skipUnless(_GIT, "git not available")
    def test_rail_kill_switch_still_measures_the_skip(self) -> None:
        """`CEO_LEDGER_CHECKPOINT=0` stops the ADVICE, not the measurement —
        "the rail was off" is itself a fact the window needs."""
        self.init_repo()
        self.write_project_file(".claude/plans/PLAN-900/LEDGER.md", "# L\n")
        self.stage(".claude/plans/PLAN-900/notes.md")
        with mock.patch.dict(os.environ, {HOOK.KILL_SWITCH_ENV: "0"}):
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
        with mock.patch.dict(os.environ, {HOOK.MASTER_KILL_ENV: "1"}):
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
        with mock.patch.dict(os.environ, {HOOK.MASTER_KILL_ENV: "1",
                                          HOOK.ENFORCE_ENV: "1"}):
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


# ---------------------------------------------------------------------------
# W2 ceremony — the audit registration itself (staged-w24 pack)
#
# These are the POSITIVE CONTROLS for the canonical half of the wave: they are
# RED against the pre-ceremony `audit_emit.py` (the actions are not in
# `_KNOWN_ACTIONS`, so `emit_generic` breadcrumbs and writes nothing) and GREEN
# against the pack copy. They assert three separate things, because the three
# fail independently:
#   (a) the action is REGISTERED and is NOT in `_EMIT_GENERIC_PASSTHROUGH`
#       (registration without a scrub branch is the ghost-action leak class);
#   (b) a non-allowlisted field is DROPPED without taking the event with it
#       (a scrub that killed the whole row would blind the window);
#   (c) an off-enum / wrong-TYPE value is COERCED to the safe sentinel and
#       never echoed (the direct-emit_generic-caller path, S172 doctrine).
# ---------------------------------------------------------------------------

from _lib import audit_emit  # noqa: E402


class _LedgerAuditBase(TestEnvContext):
    """Isolated $HOME + audit log; reads back what actually hit the wire."""

    def events(self, action: str) -> List[Dict[str, Any]]:
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        out = []  # type: List[Dict[str, Any]]
        for line in log.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                event = json.loads(line)
                if event.get("action") == action:
                    out.append(event)
        return out

    def one(self, action: str) -> Dict[str, Any]:
        found = self.events(action)
        self.assertEqual(
            len(found), 1,
            "expected exactly 1 %s event, got %d" % (action, len(found)),
        )
        return found[0]


class TestLedgerCheckpointActionsAreRegistered(_LedgerAuditBase):
    def test_registered_and_not_passthrough(self) -> None:
        for action in (HOOK.ACTION_RECORDED, HOOK.ACTION_SKIPPED):
            self.assertIn(
                action, audit_emit._KNOWN_ACTIONS,
                "%s must be registered by the W2 ceremony" % action,
            )
            self.assertNotIn(
                action, audit_emit._EMIT_GENERIC_PASSTHROUGH,
                "%s must keep its dedicated deny-by-default scrub branch — "
                "passthrough would hand a direct caller the whole field "
                "namespace" % action,
            )

    def test_known_actions_count_is_the_measured_330(self) -> None:
        # 327 measured live at 560dad0; +3 by this ceremony (Owner decision
        # 2026-08-25: ledger_checkpoint_recorded + ledger_checkpoint_skipped
        # + ledger_entry_rejected).
        self.assertEqual(len(audit_emit._KNOWN_ACTIONS), 330)


class TestLedgerCheckpointEnumParity(_LedgerAuditBase):
    """audit_emit mirrors the producer's enums LITERALLY — this is the guard.

    `audit_emit` deliberately does not import the hook (zero import-time
    dependencies), so the mirrors can drift in silence. A drift narrows a
    legitimate value to the sentinel, which looks exactly like a coercion of
    a hostile value — the failure would be invisible in the log.
    """

    def test_outcome_enum_matches_the_producer(self) -> None:
        self.assertEqual(
            set(HOOK._OUTCOMES), set(audit_emit._LEDGER_CHECKPOINT_OUTCOMES)
        )

    def test_skip_reason_enum_matches_the_producer(self) -> None:
        self.assertEqual(
            set(HOOK._SKIP_REASONS),
            set(audit_emit._LEDGER_CHECKPOINT_SKIP_REASONS),
        )

    def test_scope_source_enum_matches_the_producer(self) -> None:
        self.assertEqual(
            set(HOOK._SCOPE_SOURCES),
            set(audit_emit._LEDGER_CHECKPOINT_SCOPE_SOURCES),
        )

    def test_state_kind_enum_matches_the_producer(self) -> None:
        self.assertEqual(
            set(HOOK._STATE_KINDS),
            set(audit_emit._LEDGER_CHECKPOINT_STATE_KINDS),
        )


class TestLedgerCheckpointRecordedScrub(_LedgerAuditBase):
    ACTION = "ledger_checkpoint_recorded"

    def _emit_legit(self, **overrides: Any) -> None:
        fields = {
            "outcome": "ledger_missing",
            "plan_id": "PLAN-179",
            "scope_source": "plan_dir",
            "in_scope_path_count": 3,
            "ledger_size_bucket_kib": 7,
            "over_ceiling": 0,
            "unverified_ac_claim_count": 2,
            "commits_since_last_observation": 5,
            "state_kind": "fresh",
            "would_block": 1,
        }
        fields.update(overrides)
        audit_emit.emit_generic(self.ACTION, **fields)

    def test_every_declared_producer_field_survives(self) -> None:
        self._emit_legit()
        event = self.one(self.ACTION)
        self.assertEqual(event["outcome"], "ledger_missing")
        self.assertEqual(event["plan_id"], "PLAN-179")
        self.assertEqual(event["scope_source"], "plan_dir")
        self.assertEqual(event["in_scope_path_count"], 3)
        self.assertEqual(event["ledger_size_bucket_kib"], 7)
        self.assertEqual(event["unverified_ac_claim_count"], 2)
        self.assertEqual(event["commits_since_last_observation"], 5)
        self.assertEqual(event["state_kind"], "fresh")
        self.assertEqual(event["would_block"], 1)

    def test_smuggled_fields_are_dropped_and_the_event_survives(self) -> None:
        """(b) — the scrub drops the FIELD, never the row."""
        self._emit_legit(
            commit_message="fix: leak me",
            committed_paths=["/Users/someone/secret/path.md"],
            ledger_body="# LEDGER\nverbatim transcript",
            repo_root="/Users/someone/canhada-labs",
        )
        event = self.one(self.ACTION)
        for forbidden in (
            "commit_message", "committed_paths", "ledger_body", "repo_root"
        ):
            self.assertNotIn(
                forbidden, event,
                "%s reached the signed chain — the allowlist is not "
                "deny-by-default" % forbidden,
            )
        # ...and the legitimate payload is intact, so the drop is surgical.
        self.assertEqual(event["outcome"], "ledger_missing")
        self.assertEqual(event["plan_id"], "PLAN-179")

    def test_off_enum_values_are_coerced_never_echoed(self) -> None:
        """(c) — the direct emit_generic-caller path."""
        self._emit_legit(
            outcome="i-made-this-up",
            scope_source="../../etc/passwd",
            state_kind="whatever",
            plan_id="../../../etc/passwd",
        )
        event = self.one(self.ACTION)
        self.assertEqual(event["outcome"], "other")
        self.assertEqual(event["scope_source"], "other")
        self.assertEqual(event["state_kind"], "unavailable")
        self.assertEqual(event["plan_id"], "unknown")
        blob = json.dumps(event)
        self.assertNotIn("i-made-this-up", blob)
        self.assertNotIn("etc/passwd", blob)

    def test_int_fields_are_type_strict_and_clamped(self) -> None:
        """A float would be refused by canonical_json and drop the WHOLE row."""
        self._emit_legit(
            in_scope_path_count=3.5,
            ledger_size_bucket_kib=True,
            unverified_ac_claim_count=-4,
            commits_since_last_observation=10 ** 6,
            over_ceiling="1",
            would_block=[1],
        )
        event = self.one(self.ACTION)
        self.assertEqual(event["in_scope_path_count"], 0)
        self.assertEqual(event["ledger_size_bucket_kib"], 0)
        self.assertEqual(event["unverified_ac_claim_count"], 0)
        self.assertEqual(event["commits_since_last_observation"], 99)
        self.assertEqual(event["over_ceiling"], 0)
        self.assertEqual(event["would_block"], 0)
        for key in (
            "in_scope_path_count", "ledger_size_bucket_kib",
            "unverified_ac_claim_count", "commits_since_last_observation",
            "over_ceiling", "would_block",
        ):
            self.assertIsInstance(event[key], int)
            self.assertNotIsInstance(event[key], bool)

    def test_unhashable_value_does_not_raise_through_emit_generic(self) -> None:
        """`x in frozenset` raises TypeError on an unhashable x — the guard
        is the isinstance check that runs FIRST (rail finding B / H4)."""
        self._emit_legit(outcome=["not", "hashable"], scope_source={"a": 1})
        event = self.one(self.ACTION)
        self.assertEqual(event["outcome"], "other")
        self.assertEqual(event["scope_source"], "other")


class TestLedgerCheckpointSkippedScrub(_LedgerAuditBase):
    ACTION = "ledger_checkpoint_skipped"

    def test_legit_fields_survive_and_smuggled_ones_do_not(self) -> None:
        audit_emit.emit_generic(
            self.ACTION,
            reason="hotfix",
            plan_id="PLAN-183",
            commits_since_last_observation=2,
            state_kind="resumed",
            would_block=0,
            commit_message="hotfix: rotate the prod key AKIAI...",
        )
        event = self.one(self.ACTION)
        self.assertEqual(event["reason"], "hotfix")
        self.assertEqual(event["plan_id"], "PLAN-183")
        self.assertEqual(event["commits_since_last_observation"], 2)
        self.assertEqual(event["state_kind"], "resumed")
        self.assertNotIn("commit_message", event)
        self.assertNotIn("AKIAI", json.dumps(event))

    def test_off_enum_reason_is_coerced(self) -> None:
        audit_emit.emit_generic(
            self.ACTION, reason="because-i-said-so", plan_id="PLAN-179",
        )
        event = self.one(self.ACTION)
        self.assertEqual(event["reason"], "other")
        self.assertNotIn("because-i-said-so", json.dumps(event))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
