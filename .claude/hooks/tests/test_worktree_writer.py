"""PLAN-125 WS-2 (kooky-harvest) — parallel-writer worktree-isolation tests.

Covers the falsifiable WIN gate (§4 / §9 MF-SEC-6/7, MF-QA-C, MF-4):

* enforcement boundary DENIES a `Bash`/`Edit` whose resolved cwd/target is the
  shared main checkout while parallel-writer mode is active (fail-CLOSED);
* the SAME write INSIDE the assigned worktree is ALLOWED;
* git refs/paths PASS after a `--` end-of-options separator + allowlist, and a
  leading `-` / `..` is REJECTED (MF-SEC-7);
* TOCTOU — a Bash command embedding `cd <main> && ...` is denied even with the
  assigned-worktree env set (MF-SEC-6);
* per-PID/slot ISOLATION — two writers with distinct assigned worktrees each
  see only their own slot as allowed;
* mode DEFAULT-OFF — with `CEO_PARALLEL_WRITER` unset, every write is allowed
  (the owner session is untouched);
* fail-CLOSED — active mode with `CEO_ASSIGNED_WORKTREE` unset → deny all;
  unparseable / opaque Bash → deny.

Per MF-QA-C the S191 KILL is framed as "enforcement boundary denies a write
whose resolved cwd/target is outside the assigned worktree." The FULL S191
vector (bg subprocess + rsync) is **integration-level, out of unit scope** —
this file exercises the enforcement *contract*, not the end-to-end bleed.

All tests isolate the audit chain via ``TestEnvContext`` (pins
``CEO_AUDIT_LOG_DIR`` → a per-test temp dir). The hook emits NO audit-chain
event (it is a pure allow/block decision), but the isolation harness still
guards against any incidental write touching the real log.

Stdlib-only, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import check_worktree_writer as cww  # noqa: E402
from _lib import contract as _contract  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


def _event(tool_name: str, *, file_path: str = "", command: str = "") -> _contract.NormalizedEvent:
    """Build a minimal NormalizedEvent for a write tool."""
    tool_input = {}
    if file_path:
        tool_input["file_path"] = file_path
    if command:
        tool_input["command"] = command
    return _contract.NormalizedEvent(
        session_id="sess-test",
        phase="PreToolUse",
        tool_name=tool_name,
        tool_input=tool_input,
        file_path=file_path,
        command=command,
    )


class _WriterBase(TestEnvContext):
    """Builds an isolated main checkout + a sibling assigned worktree slot."""

    def setUp(self) -> None:
        super().setUp()
        # main checkout = the project dir; the pool slot lives under it at
        # .claude/swarm-worktrees/loop-0 (a sibling subtree per the pool's
        # _DEFAULT_POOL_DIR layout).
        self.main_checkout = self.project_dir
        self.slot = self.main_checkout / ".claude" / "swarm-worktrees" / "loop-0"
        self.slot.mkdir(parents=True, exist_ok=True)
        # A second, independent slot for the per-slot isolation test.
        self.slot_b = self.main_checkout / ".claude" / "swarm-worktrees" / "loop-1"
        self.slot_b.mkdir(parents=True, exist_ok=True)

    def _env(
        self,
        *,
        active: bool = True,
        assigned: Optional[Path] = None,
    ) -> dict:
        env = {"CLAUDE_PROJECT_DIR": str(self.main_checkout)}
        if active:
            env["CEO_PARALLEL_WRITER"] = "1"
        if assigned is not None:
            env["CEO_ASSIGNED_WORKTREE"] = str(assigned)
        return env

    def _decide(
        self,
        event: _contract.NormalizedEvent,
        *,
        cwd: Optional[Path] = None,
        env: Optional[dict] = None,
    ) -> _contract.Decision:
        return cww.decide(event, cwd=cwd or self.slot, env=env)


# ---------------------------------------------------------------------------
# 1. Enforcement boundary — DENY a write into the shared main checkout
#    (the S191 bleed regression, framed per MF-QA-C).
# ---------------------------------------------------------------------------


class TestEnforcementBoundary(_WriterBase):
    def test_edit_into_main_checkout_denied(self):
        # An Edit whose target is a canonical file in the shared main checkout
        # while a parallel writer is assigned a dedicated worktree → DENY.
        target = self.main_checkout / "CLAUDE.md"
        ev = _event("Edit", file_path=str(target))
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "write into main checkout must be DENIED")
        self.assertIn("main checkout", (d.reason or "").lower())

    def test_edit_inside_assigned_worktree_allowed(self):
        # The SAME write, but targeting the assigned worktree → ALLOW.
        target = self.slot / "CLAUDE.md"
        ev = _event("Edit", file_path=str(target))
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertTrue(d.allow, "write inside the assigned worktree must be ALLOWED")

    def test_write_relative_path_resolves_against_cwd(self):
        # A relative file_path resolves against the hook process cwd. If cwd is
        # the main checkout, a bare "foo.py" lands in main → DENY.
        ev = _event("Write", file_path="foo.py")
        d = cww.decide(
            ev, cwd=self.main_checkout, env=self._env(assigned=self.slot)
        )
        self.assertFalse(d.allow)

    def test_bash_redirect_into_main_checkout_denied(self):
        # echo x > <main>/file while active → DENY.
        target = self.main_checkout / "leak.txt"
        ev = _event("Bash", command=f"echo pwned > {target}")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "redirect into main checkout must be DENIED")

    def test_bash_redirect_inside_worktree_allowed(self):
        target = self.slot / "ok.txt"
        ev = _event("Bash", command=f"echo ok > {target}")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertTrue(d.allow)

    def test_traversal_escape_from_worktree_denied(self):
        # A ../.. traversal out of the slot back into main → DENY (resolved
        # before the containment test).
        escape = self.slot / ".." / ".." / "escaped.txt"
        ev = _event("Write", file_path=str(escape))
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow)


# ---------------------------------------------------------------------------
# 1b. Common file-mutating commands (Codex pair-rail P0) — cp/mv/rsync/install/
#     ln destinations + touch/mkdir/rmdir/rm targets into the main checkout.
# ---------------------------------------------------------------------------


class TestMutatingCommandTargets(_WriterBase):
    def test_rsync_into_main_denied(self):
        # The literal S191 vector — rsync INTO the shared main checkout.
        ev = _event("Bash", command=f"rsync -a ./out/ {self.main_checkout}/")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "rsync into main checkout must be DENIED")

    def test_cp_into_main_denied(self):
        ev = _event("Bash", command=f"cp build.txt {self.main_checkout}/build.txt")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "cp destination in main must be DENIED")

    def test_cp_from_main_into_worktree_allowed(self):
        # Source inside main is a legal READ; destination is the slot → ALLOW.
        ev = _event("Bash", command=f"cp {self.main_checkout}/seed.txt ./seed.txt")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertTrue(d.allow, "reading FROM main into the slot must be ALLOWED")

    def test_touch_into_main_denied(self):
        ev = _event("Bash", command=f"touch {self.main_checkout}/marker")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow)

    def test_mkdir_into_main_denied(self):
        ev = _event("Bash", command=f"mkdir {self.main_checkout}/newdir")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow)

    def test_rm_into_main_denied(self):
        ev = _event("Bash", command=f"rm -rf {self.main_checkout}/important")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow)

    def test_mv_within_worktree_allowed(self):
        # Both args relative to the slot cwd → destination inside slot → ALLOW.
        ev = _event("Bash", command="mv a.txt b.txt")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertTrue(d.allow, "mv within the assigned slot must be ALLOWED")

    # --- Codex R2 P0: shell $VAR / ~ expansion must resolve to the real path ---

    def test_cd_env_var_into_main_denied(self):
        # The cooperative pattern `cd "$CLAUDE_PROJECT_DIR" && write` must
        # resolve $CLAUDE_PROJECT_DIR to the main checkout → DENY.
        ev = _event("Bash", command="cd $CLAUDE_PROJECT_DIR && echo x > f")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "cd $CLAUDE_PROJECT_DIR must resolve + DENY")

    def test_rsync_env_var_into_main_denied(self):
        ev = _event("Bash", command="rsync -a ./out/ $CLAUDE_PROJECT_DIR/")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "rsync into $CLAUDE_PROJECT_DIR must DENY")

    def test_redirect_braced_env_var_into_main_denied(self):
        ev = _event("Bash", command="echo x > ${CLAUDE_PROJECT_DIR}/leak.txt")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "redirect into ${CLAUDE_PROJECT_DIR} must DENY")

    def test_unresolved_unknown_var_fails_closed(self):
        # An unknown var cannot be expanded → residual `$` → unresolvable →
        # fail-CLOSED (we must never treat it as a benign relative path).
        ev = _event("Bash", command="cp seed.txt $SOME_UNKNOWN_VAR/dst")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "unresolved $VAR write target must fail-CLOSED")

    def test_cp_assigned_worktree_env_var_allowed(self):
        # Expanding the writer's OWN assigned-worktree var → inside slot → ALLOW
        # (proves expansion is not a blanket deny on $VAR).
        ev = _event("Bash", command="cp seed.txt $CEO_ASSIGNED_WORKTREE/dst")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertTrue(d.allow, "write into $CEO_ASSIGNED_WORKTREE must be ALLOWED")

    def test_cp_target_directory_option_into_main_denied(self):
        # Destination encoded in `-t` / `--target-directory=` must be caught.
        for cmd in (
            f"cp -t {self.main_checkout} a.txt",
            f"cp --target-directory={self.main_checkout} a.txt",
        ):
            ev = _event("Bash", command=cmd)
            d = self._decide(ev, env=self._env(assigned=self.slot))
            self.assertFalse(d.allow, f"-t destination in main must DENY: {cmd}")


# ---------------------------------------------------------------------------
# 2. TOCTOU (MF-SEC-6) — a later cd / git -C must not escape the boundary.
# ---------------------------------------------------------------------------


class TestToctou(_WriterBase):
    def test_cd_into_main_then_write_denied(self):
        # cwd is the assigned slot, but the command cd's into main first.
        cmd = f"cd {self.main_checkout} && echo x > f"
        ev = _event("Bash", command=cmd)
        d = self._decide(ev, cwd=self.slot, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "cd into main checkout must be DENIED (TOCTOU)")

    def test_git_dash_C_into_main_denied(self):
        cmd = f"git -C {self.main_checkout} checkout -- somefile"
        ev = _event("Bash", command=cmd)
        d = self._decide(ev, cwd=self.slot, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "git -C into main must be DENIED")

    def test_cd_within_worktree_then_write_allowed(self):
        sub = self.slot / "src"
        sub.mkdir(parents=True, exist_ok=True)
        cmd = f"cd {sub} && echo x > f"
        ev = _event("Bash", command=cmd)
        d = self._decide(ev, cwd=self.slot, env=self._env(assigned=self.slot))
        self.assertTrue(d.allow)

    def test_opaque_indirection_denied(self):
        ev = _event("Bash", command="eval \"$PAYLOAD\"")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "eval cannot be verified → fail-CLOSED")

    def test_inline_interpreter_body_denied(self):
        ev = _event("Bash", command="python3 -c 'open(\"x\",\"w\")'")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "interpreter -c body cannot be verified → deny")

    def test_unparseable_bash_denied(self):
        ev = _event("Bash", command="echo 'unbalanced")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "unparseable command → fail-CLOSED")


# ---------------------------------------------------------------------------
# 3. Argv-git discipline (MF-SEC-7) — `--` separator + allowlist regex.
# ---------------------------------------------------------------------------


class TestArgvGitDiscipline(_WriterBase):
    def test_safe_ref_path_accepts_clean_value(self):
        self.assertTrue(cww.is_safe_ref_path("feature/my-branch"))
        self.assertTrue(cww.is_safe_ref_path("src/pkg/mod.py"))
        self.assertTrue(cww.is_safe_ref_path("v1.2.3"))

    def test_safe_ref_path_rejects_leading_dash(self):
        # Option injection: a ref/path beginning with '-' is parsed as a flag.
        self.assertFalse(cww.is_safe_ref_path("--upload-pack=evil"))
        self.assertFalse(cww.is_safe_ref_path("-rf"))

    def test_safe_ref_path_rejects_traversal(self):
        self.assertFalse(cww.is_safe_ref_path("../../etc/passwd"))
        self.assertFalse(cww.is_safe_ref_path("a/../b"))

    def test_safe_ref_path_rejects_out_of_allowlist(self):
        self.assertFalse(cww.is_safe_ref_path("a b"))      # space
        self.assertFalse(cww.is_safe_ref_path("a;rm -rf"))  # shell metachar
        self.assertFalse(cww.is_safe_ref_path(""))          # empty

    def test_git_path_traversal_token_denied(self):
        # Codex pair-rail P1: a `..` traversal in a git ref/path (even AFTER a
        # `--` separator) must be denied while active (MF-SEC-7).
        ev = _event("Bash", command="git checkout -- ../../etc/passwd")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "git path with '..' traversal must be DENIED")

    def test_git_out_of_allowlist_ref_after_separator_denied(self):
        # Codex R2 P1: tokens AFTER `--` must pass the allowlist regex — a path
        # with a space (out-of-allowlist) is denied (MF-SEC-7 binding requirement).
        ev = _event("Bash", command="git checkout -- 'bad path'")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "out-of-allowlist git ref after '--' must DENY")

    def test_git_clean_ref_after_separator_allowed(self):
        # A clean ref/path after `--` passes the allowlist → not denied by the
        # git discipline (proves the allowlist is not a blanket deny).
        ev = _event("Bash", command="git checkout -- src/pkg/mod.py")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertTrue(d.allow, "clean git ref after '--' must be ALLOWED")

    def test_git_commit_message_with_spaces_allowed(self):
        # A pre-`--` flag value (commit message with spaces) must NOT be falsely
        # denied by the post-`--` allowlist.
        ev = _event("Bash", command="git commit -m 'a message with spaces'")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertTrue(d.allow, "commit message before '--' must be ALLOWED")

    def test_git_grep_pattern_with_spaces_allowed(self):
        # Codex R3 P1: a READ-ONLY git subcommand's pattern after `--` is NOT a
        # write target — the strict allowlist must NOT falsely deny it.
        ev = _event("Bash", command="git grep -- 'TODO item'")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertTrue(d.allow, "git grep pattern after '--' must be ALLOWED")

    def test_git_log_path_traversal_allowed_readonly(self):
        # A read-only subcommand reading via `..` is a READ (cooperative model
        # allows reads); the write-scoped discipline does not apply.
        ev = _event("Bash", command="git log -- ../sibling")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertTrue(d.allow, "read-only git log must not be write-denied")

    def test_require_end_of_options(self):
        self.assertTrue(cww.require_end_of_options(["git", "checkout", "--", "ref"]))
        self.assertFalse(cww.require_end_of_options(["git", "checkout", "ref"]))

    def test_clean_path_after_separator_passes(self):
        # A clean ref/path after `--` passes the allowlist + has the separator.
        argv = ["git", "checkout", "--", "feature/clean-branch"]
        self.assertTrue(cww.require_end_of_options(argv))
        self.assertTrue(cww.is_safe_ref_path(argv[-1]))

    def test_git_dash_leading_ref_without_separator_denied(self):
        # A dash-leading ref with no `--` end-of-options separator → deny.
        ev = _event("Bash", command="git checkout -evilref")
        d = self._decide(ev, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "dash-leading ref without -- must be DENIED")


# ---------------------------------------------------------------------------
# 4. Per-slot ISOLATION — each writer sees only its own assigned worktree.
# ---------------------------------------------------------------------------


class TestPerSlotIsolation(_WriterBase):
    def test_writer_a_cannot_write_into_writer_b_slot(self):
        # Writer A is assigned slot A; a write into slot B is NOT inside A's
        # assigned worktree, but slot B is under the main checkout → DENY.
        target = self.slot_b / "x.txt"
        ev = _event("Write", file_path=str(target))
        d = cww.decide(ev, cwd=self.slot, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "writing into a sibling slot must be DENIED")

    def test_writer_b_allowed_in_its_own_slot(self):
        target = self.slot_b / "x.txt"
        ev = _event("Write", file_path=str(target))
        d = cww.decide(ev, cwd=self.slot_b, env=self._env(assigned=self.slot_b))
        self.assertTrue(d.allow, "writer B may write inside its own slot")

    def test_two_writers_distinct_assignments(self):
        # Same target file under main; only the writer whose slot contains it
        # (none here — it's directly in main) is allowed. Both are denied.
        target = self.main_checkout / "shared.txt"
        ev = _event("Write", file_path=str(target))
        for slot in (self.slot, self.slot_b):
            d = cww.decide(ev, cwd=slot, env=self._env(assigned=slot))
            self.assertFalse(d.allow)


# ---------------------------------------------------------------------------
# 5. Default-OFF + fail-CLOSED activation contract.
# ---------------------------------------------------------------------------


class TestActivationContract(_WriterBase):
    def test_default_off_allows_everything(self):
        # No CEO_PARALLEL_WRITER → the hook is INERT (owner session untouched).
        target = self.main_checkout / "CLAUDE.md"
        for ev in (
            _event("Edit", file_path=str(target)),
            _event("Write", file_path=str(target)),
            _event("Bash", command=f"echo x > {target}"),
            _event("Bash", command="eval $X"),
        ):
            d = cww.decide(ev, cwd=self.main_checkout, env=self._env(active=False))
            self.assertTrue(d.allow, f"default-OFF must allow {ev.tool_name}")

    def test_active_without_assigned_worktree_denies_all(self):
        # CEO_PARALLEL_WRITER=1 but no CEO_ASSIGNED_WORKTREE → deny all writes.
        target = self.slot / "ok.txt"  # even a path that WOULD be fine
        ev = _event("Edit", file_path=str(target))
        d = cww.decide(ev, cwd=self.slot, env=self._env(assigned=None))
        self.assertFalse(d.allow, "active + no assigned slot → DENY all")
        self.assertIn("CEO_ASSIGNED_WORKTREE", d.reason or "")

    def test_active_write_tool_without_file_path_denied(self):
        ev = _event("Edit", file_path="")
        d = cww.decide(ev, cwd=self.slot, env=self._env(assigned=self.slot))
        self.assertFalse(d.allow, "no resolvable file_path while active → DENY")

    def test_is_active_reads_env(self):
        self.assertTrue(cww.is_active({"CEO_PARALLEL_WRITER": "1"}))
        self.assertFalse(cww.is_active({"CEO_PARALLEL_WRITER": "0"}))
        self.assertFalse(cww.is_active({}))

    def test_assigned_equals_main_denies_all(self):
        # Codex pair-rail P1: an assignment that equals the main checkout would
        # void the boundary (every write would look "inside the slot") → must
        # fail-CLOSED deny all while active.
        ev = _event("Edit", file_path=str(self.slot / "ok.txt"))
        env = self._env(assigned=self.main_checkout)
        d = cww.decide(ev, cwd=self.slot, env=env)
        self.assertFalse(d.allow, "assigned == main must DENY all (fail-CLOSED)")
        self.assertIn("distinct", (d.reason or "").lower())

    def test_assigned_parent_of_main_denies_all(self):
        # An assignment that is a PARENT of the main checkout is equally void.
        ev = _event("Edit", file_path=str(self.slot / "ok.txt"))
        env = self._env(assigned=self.main_checkout.parent)
        d = cww.decide(ev, cwd=self.slot, env=env)
        self.assertFalse(d.allow, "assigned ancestor-of-main must DENY all")


# ---------------------------------------------------------------------------
# 6. Fail-OPEN on a hook-internal bug — never block on an infra error.
# ---------------------------------------------------------------------------


class TestFailOpenOnHookBug(_WriterBase):
    def test_decide_with_non_write_tool_allows(self):
        # A tool outside the write set (defensive — shouldn't reach the hook
        # given the matcher) is allowed.
        ev = _event("Read", file_path=str(self.main_checkout / "x"))
        d = cww.decide(ev, cwd=self.main_checkout, env=self._env(assigned=self.slot))
        self.assertTrue(d.allow)


# ---------------------------------------------------------------------------
# 7. main() parse-error fail-direction (Codex pair-rail P1).
# ---------------------------------------------------------------------------


class TestMainParseErrorFailClosed(_WriterBase):
    def _run_main_with_parse_error(self) -> _contract.Decision:
        captured = {}

        def fake_read(phase: str = ""):
            ev = _event("Bash", command="x")
            ev.parse_error = "simulated stdin parse error"
            return ev

        def fake_emit(decision):
            captured["d"] = decision

        orig_read = cww._claude_adapter.read_event
        orig_emit = cww._claude_adapter.emit_decision
        cww._claude_adapter.read_event = fake_read  # type: ignore[assignment]
        cww._claude_adapter.emit_decision = fake_emit  # type: ignore[assignment]
        try:
            cww.main()
        finally:
            cww._claude_adapter.read_event = orig_read  # type: ignore[assignment]
            cww._claude_adapter.emit_decision = orig_emit  # type: ignore[assignment]
        return captured["d"]

    def test_parse_error_blocks_when_active(self):
        os.environ["CEO_PARALLEL_WRITER"] = "1"
        os.environ["CEO_ASSIGNED_WORKTREE"] = str(self.slot)
        d = self._run_main_with_parse_error()
        self.assertFalse(d.allow, "parse error while ACTIVE must fail-CLOSED (block)")

    def test_parse_error_allows_when_inert(self):
        os.environ.pop("CEO_PARALLEL_WRITER", None)
        d = self._run_main_with_parse_error()
        self.assertTrue(d.allow, "parse error in the owner/inert session must fail-OPEN")


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
