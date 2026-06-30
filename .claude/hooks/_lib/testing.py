"""Test helpers — TestEnvContext base class + fixture utilities.

Every test file in `.claude/hooks/tests/` subclasses `TestEnvContext` so
that each test runs in an isolated environment:

- A fresh temporary directory for CLAUDE_PROJECT_DIR
- A fresh temporary directory for HOME
- Env vars starting with CEO_ are snapshotted + restored
- sys.path is snapshotted + restored
- Working directory is snapshotted + restored

This closes the Q2 gap identified by debate round 1 (QA HIGH): Sprint 1
tests leaked state through env vars. The hook modules must never see
real $HOME or real $CLAUDE_PROJECT_DIR during unit tests.

## Usage

    from _lib.testing import TestEnvContext

    class TestMyHook(TestEnvContext):
        def test_something(self):
            self.write_file("team.md", "**Alice** works here")
            # self.project_dir, self.home_dir, self.audit_dir are set up
            ...

## Fixture loading

`load_fixture(name)` reads a JSON fixture from the `fixtures/` subdir of
the test file's package. Used for sample hook payloads.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Optional


class TestEnvContext(unittest.TestCase):
    """Base test case that isolates env, HOME, CLAUDE_PROJECT_DIR, sys.path.

    Subclasses that override setUp/tearDown MUST call super().

    ## CEO_AUDIT_SYNC_MODE default (PLAN-107 Wave A.1)

    Since PLAN-094 v1.27.0, ``audit_emit`` defaults to **async-spool** writes
    (events buffered in a background spool writer thread). Tests that read
    the audit log buffer immediately after triggering an emit would race
    the spool drain and see stale state. The kill-switch
    ``CEO_AUDIT_SYNC_MODE=1`` reverts to pre-Wave-A synchronous
    fsync-per-call semantics (see ``_lib/spool_writer.py:348``).

    Lesson [[feedback-test-set-ceo-audit-sync-mode]] (S141) established
    that every emit-read test needs sync mode on. PLAN-107 Wave A.1
    promotes this to a TestEnvContext default — subclasses that genuinely
    exercise the async path (e.g. ``test_audit_emit_async_flush``) opt out
    by setting class attribute ``SYNC_MODE_DEFAULT = False`` and managing
    the env var themselves.
    """

    # Class-level opt-out for the rare tests that genuinely exercise the
    # async spool path. Subclass and set False to disable the default.
    SYNC_MODE_DEFAULT: bool = True

    # PLAN-106-FOLLOWUP Wave A.2 — agent-binding fixture opt-in.
    # Subclasses that exercise dispatch paths through VETO_FLOOR_ROLES
    # populate this with the agent names to materialize inside
    # self.project_dir's sandboxed `.claude/agents/` dir. Default is
    # empty list — backwards-compatible no-op for existing subclasses.
    AGENT_BINDINGS_TO_MATERIALIZE: list = []

    # Attributes populated in setUp
    project_dir: Path
    home_dir: Path
    audit_dir: Path

    _env_snapshot: Dict[str, Optional[str]]
    _cwd_snapshot: str
    _syspath_snapshot: list
    _tmp_root: Path

    def setUp(self) -> None:
        """Snapshot environment + build an isolated per-test tmp tree.

        Captures all env vars matching ``CEO_*``, ``CLAUDE_*``, and
        ``HOME`` into ``self._env_snapshot`` so ``tearDown`` can restore
        them exactly. Creates a temp directory with ``home/`` +
        ``project/`` + ``audit-dir/`` subtrees and points the hook's env
        vars (``HOME``, ``CLAUDE_PROJECT_DIR``, ``CEO_AUDIT_LOG_*``) at
        the isolated tree. Subclass tests can then exercise hook logic
        without touching the real user profile.
        """
        super().setUp()
        # Snapshot env vars we care about so tearDown can restore them.
        # We snapshot a broad set: HOME, CLAUDE_*, CEO_*, and PYTHON*.
        self._env_snapshot = {}
        for key in list(os.environ.keys()):
            if (
                key.startswith("CEO_")
                or key.startswith("CLAUDE_")
                or key == "HOME"
            ):
                self._env_snapshot[key] = os.environ.get(key)

        # PLAN-107 Wave A.1: parent-shell env-leak prevention.
        # Snapshot above preserves restore semantics, but the test must
        # start with a CLEAN env or parent-shell CEO_KERNEL_OVERRIDE /
        # CEO_QUIET_MODE / CEO_BUDGET_GUARD_* will leak into the test
        # subject's behavior. Strip the most disruptive overrides while
        # the test runs; tearDown restores from the snapshot.
        for key in list(os.environ.keys()):
            if (
                key.startswith("CEO_KERNEL_OVERRIDE")
                or key.startswith("CEO_BUDGET_GUARD_")
                or key.startswith("CEO_PRUNE_")
                or key == "CEO_QUIET_MODE"
                or key == "CEO_OVERHEAD_ACK"
                or key == "CEO_SKIP_REAL_REGISTRY_SMOKE"
                or key == "CEO_SOTA_DISABLE"
            ):
                del os.environ[key]

        # Snapshot cwd + sys.path
        self._cwd_snapshot = os.getcwd()
        self._syspath_snapshot = list(sys.path)

        # Build an isolated temp tree:
        #   <tmp_root>/
        #       home/
        #           .claude/projects/test/
        #               (audit-log.jsonl lives here)
        #       project/
        #           .claude/
        #               team.md, frontend-team.md, skills/, ...
        self._tmp_root = Path(tempfile.mkdtemp(prefix="ceo-hook-test-"))
        self.home_dir = self._tmp_root / "home"
        self.project_dir = self._tmp_root / "project"
        self.audit_dir = self.home_dir / ".claude" / "projects" / "test"

        (self.project_dir / ".claude").mkdir(parents=True, exist_ok=True)
        self.audit_dir.mkdir(parents=True, exist_ok=True)

        # Point the hook env at the isolated tree
        os.environ["HOME"] = str(self.home_dir)
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.project_dir)
        os.environ["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.audit_dir / "audit-log.jsonl")
        os.environ["CEO_AUDIT_LOG_ERR"] = str(self.audit_dir / "audit-log.errors")
        os.environ["CEO_AUDIT_LOG_LOCK"] = str(self.audit_dir / "audit-log.lock")

        # PLAN-107 Wave A.1 — sync-mode default for emit-read tests.
        # Async-spool was the v1.27.0 default; tests need sync to see emits.
        if self.SYNC_MODE_DEFAULT:
            os.environ["CEO_AUDIT_SYNC_MODE"] = "1"

        # PLAN-111 Wave A.5 — invalidate spool_writer state-dir cache
        # on test setup (env-tuple may have rotated since last test).
        try:
            from _lib import spool_writer as _spool_writer
            _spool_writer._reset_caches_for_test()
        except Exception:
            pass  # fail-open; cache invalidation is hygiene, not correctness


        # PLAN-106-FOLLOWUP Wave A.2 — materialize agent bindings for
        # subclasses that opt in via AGENT_BINDINGS_TO_MATERIALIZE.
        # See `.claude/hooks/tests/_agent_fixture.py` for the helper.
        if self.AGENT_BINDINGS_TO_MATERIALIZE:
            # Lazy import keeps this module's import surface stable.
            from tests._agent_fixture import materialize_agent_binding  # noqa: E402
            for _name in self.AGENT_BINDINGS_TO_MATERIALIZE:
                materialize_agent_binding(
                    self.project_dir, _name, tmp_root=self._tmp_root,
                )

    def tearDown(self) -> None:
        """Restore env + cwd + sys.path + remove the per-test tmp tree.

        Two-step env restoration:

        1. Remove any ``CEO_*``/``CLAUDE_*``/``HOME`` env var NOT present
           in ``self._env_snapshot`` (tests may have added new ones).
        2. Restore the snapshotted values (delete if value was ``None``
           indicating originally-unset, otherwise set to recorded value).

        Also chdir back to the original cwd and restore ``sys.path`` so
        test-local imports don't leak between cases.
        """

        # PLAN-111 Wave A.5 — invalidate spool_writer state-dir cache
        # on test teardown (env restored so cache will resolve to a
        # potentially-now-deleted tmpdir).
        try:
            from _lib import spool_writer as _spool_writer
            _spool_writer._reset_caches_for_test()
        except Exception:
            pass
        # Restore env
        # 1. Remove any env vars we may have set that weren't in the snapshot
        for key in list(os.environ.keys()):
            if (
                key.startswith("CEO_")
                or key.startswith("CLAUDE_")
                or key == "HOME"
            ):
                if key not in self._env_snapshot:
                    del os.environ[key]
        # 2. Restore snapshotted values
        for key, value in self._env_snapshot.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        # Restore cwd + sys.path
        try:
            os.chdir(self._cwd_snapshot)
        except OSError:
            pass
        sys.path[:] = self._syspath_snapshot

        # Clean the temp dir
        shutil.rmtree(self._tmp_root, ignore_errors=True)

        super().tearDown()

    # ---- helpers ----------------------------------------------------------

    def write_project_file(self, relative: str, content: str) -> Path:
        """Write a file under self.project_dir, creating parents as needed."""
        target = self.project_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def write_audit_file(self, relative: str, content: str) -> Path:
        """Write a file under self.audit_dir (the isolated audit dir)."""
        target = self.audit_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def read_audit_log(self) -> str:
        """Read the audit log contents (empty string if missing)."""
        log_path = self.audit_dir / "audit-log.jsonl"
        if not log_path.is_file():
            return ""
        return log_path.read_text(encoding="utf-8")

    def read_audit_errors(self) -> str:
        """Read the audit errors breadcrumb file."""
        err_path = self.audit_dir / "audit-log.errors"
        if not err_path.is_file():
            return ""
        return err_path.read_text(encoding="utf-8")

    # ---- PLAN-119 WS-C — isolated subprocess/multiprocessing env -------------

    def subprocess_env(self, **overrides: str) -> Dict[str, str]:
        """Return an env dict for spawning a hook subprocess/child that is
        isolated to THIS test's audit dir.

        Built from the SAME shared carrier-set enumeration as the WS-A session
        redirect (``_lib.test_isolation``), so a spawned child can never resolve
        the LIVE ``~/.claude`` audit dir. ``CEO_AUDIT_LOG_DIR`` is pinned to this
        test's ``audit_dir``; the per-file path overrides are CLEARED so they
        default off it; ``CEO_AUDIT_SYNC_MODE=1`` is pinned so the child writes
        synchronously and the parent can read its emits deterministically
        (S168 [[feedback-worker-must-pin-sync-mode-not-inherit]] — forkserver/
        spawn children may not inherit a mutated ``os.environ``).

        ``**overrides`` lets a caller add/replace vars, but any override that
        would leave an audit *path* carrier pointing OUTSIDE this test's tmp tree
        is REJECTED (C3 — defeats the attacker-style partial override where only
        ``CEO_AUDIT_LOG_DIR`` is isolated while ``CEO_AUDIT_LOG_PATH`` is left at
        the live file).
        """
        from _lib import test_isolation  # local import: keep module import light

        env: Dict[str, str] = dict(os.environ)
        # Redirect the child's HOME under THIS test's tmp tree too, so the
        # audit-dir FALLBACK (reached if CEO_AUDIT_LOG_DIR is ever emptied) is
        # non-live (Codex pair-rail P1 — HOME is an audit carrier again).
        env["HOME"] = str(self.home_dir)
        env["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        env["CEO_PROJECT_STATE_DIR"] = str(self.audit_dir / "state")
        env[test_isolation.TEST_HARNESS_VAR] = "1"
        env[test_isolation.SYNC_MODE_VAR] = "1"
        # Clear the per-file path overrides so they default off CEO_AUDIT_LOG_DIR.
        for key in test_isolation.AUDIT_CLEAR_CARRIERS:
            env.pop(key, None)
        # Apply caller overrides.
        for key, value in overrides.items():
            env[str(key)] = str(value)
        # C3: reject any audit PATH carrier (INCLUDING HOME — the fallback anchor)
        # pointing outside this test's tmp tree. HOME is validated so an override
        # like ``subprocess_env(CEO_AUDIT_LOG_DIR="", HOME="<real>")`` cannot
        # re-open the fallback-to-live path (Codex pair-rail P1).
        tmp_root = str(Path(self._tmp_root).resolve())
        path_carriers = ("HOME", "CEO_AUDIT_LOG_DIR", "CEO_PROJECT_STATE_DIR") + tuple(
            c for c in test_isolation.AUDIT_CLEAR_CARRIERS if c.endswith("_PATH")
            or c.endswith("_DIR") or c.endswith("_ERR") or c.endswith("_LOCK")
        )
        for carrier in path_carriers:
            val = env.get(carrier)
            if not val:
                continue
            try:
                resolved = str(Path(val).resolve())
            except (OSError, ValueError):
                raise ValueError(
                    f"subprocess_env: carrier {carrier} has an unresolvable "
                    f"path override"
                )
            if not (resolved == tmp_root or resolved.startswith(tmp_root + os.sep)):
                raise ValueError(
                    f"subprocess_env: carrier {carrier} would point a child "
                    f"OUTSIDE this test's isolated tmp tree (partial-override "
                    f"live-pollution vector rejected per PLAN-119 WS-C C3)"
                )
        # The primary anchor must survive overrides: if a caller emptied
        # CEO_AUDIT_LOG_DIR, the child relies solely on the (validated-safe) HOME
        # fallback — which the loop above already proved is under tmp_root.
        return env


def load_fixture(fixture_name: str, *, package_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load a JSON fixture from the caller's `fixtures/` subdir.

    Args:
        fixture_name: Basename of the fixture file (with or without .json).
        package_dir: The directory containing the `fixtures/` subdir.
            If None, uses the directory of this `testing.py` module's
            parent (i.e. `.claude/hooks/tests/`).

    Returns:
        The parsed JSON as a dict.
    """
    if not fixture_name.endswith(".json"):
        fixture_name = fixture_name + ".json"
    if package_dir is None:
        # Default: .claude/hooks/tests/fixtures/
        package_dir = Path(__file__).resolve().parent.parent / "tests"
    fixture_path = package_dir / "fixtures" / fixture_name
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)
