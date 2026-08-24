"""S326 — collection-time audit isolation guard (anti-rot for a measured leak).

pytest never runs fixtures under ``--collect-only``. The suite-wide audit-dir
redirect (``_lib/test_isolation._ceo_audit_isolation_session``) is a session
fixture, while the conftest's IMPORT-time work only pops
``CLAUDE_PROJECT_DIR_NATIVE``. So a test module that reaches an audit emitter
at import time writes to the fallback ``$HOME/.claude/projects/<slug>`` — the
LIVE HMAC chain — on every collect, and the whole-dir override carrier cannot
redirect it (it was popped one step earlier).

Measured 2026-08-24 (S326 boot): ``test_policy_mutations._POLICY_BASELINES``
replayed the 82-row policy corpus at import → 124 signed, unattributable
(``session_id=''``) events per ``pytest --collect-only``; ``verify-counts.sh``
ran that collect before every commit → 19 runs / 2,356 links in 12 h = 79% of
the live segment. The S321 cure (``9de4efc``) only ever covered fixture time.

Two guards, ONE mechanism (a green negative is meaningful only because the
positive control proves the detector can go red):

- ``test_collecting_hook_legs_writes_no_audit_lines`` (always) and
  ``test_collecting_all_testpaths_writes_no_audit_lines`` (where PyYAML is
  importable; skips visibly elsewhere) — NEGATIVE, the class: collecting the
  testpaths under a throwaway HOME (no audit carriers, no harness signals —
  the exact shape ``verify-counts.sh`` runs in) writes ZERO audit-log lines
  under that HOME.
- ``test_positive_control_import_time_emitter_is_seen`` — the instrument: a
  synthetic module that calls the policy engine at import, collected the same
  way, DOES write lines under the throwaway HOME.

Both spawn a child pytest on purpose: collection-time import IS the mechanism
under test, and it cannot be reproduced in-process (the session fixture has
already run here).
"""
from __future__ import annotations

import os
import shutil
import site
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

_HOOKS_DIR = Path(__file__).resolve().parent.parent  # .claude/hooks
_REPO_ROOT = _HOOKS_DIR.parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import test_isolation  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402

_BASH_POLICY = _REPO_ROOT / ".claude" / "policies" / "bash-safety.policy.yaml"
_BASH_FIXTURES = (
    _REPO_ROOT / ".claude" / "policies" / "fixtures" / "bash-safety.fixtures.jsonl"
)
# Anti-vacuity floor for the negative guard: the configured testpaths collect
# far more than this; a child that silently collected nothing (pytest missing,
# import storm, wrong cwd) must NOT pass as "zero lines written".
_MIN_COLLECTED = 1000


def _audit_log_lines(home: Path) -> Dict[str, int]:
    """Every ``audit-log*.jsonl`` under ``home`` → line count (empty = none)."""
    out: Dict[str, int] = {}
    for p in home.rglob("audit-log*.jsonl"):
        with open(p, encoding="utf-8", errors="replace") as fh:
            out[str(p.relative_to(home))] = sum(1 for _ in fh)
    return out


class TestCollectOnlyAuditIsolation(TestEnvContext):
    """S326 — nothing that runs at collection time may reach the live chain."""

    def _throwaway_home(self) -> Path:
        home = Path(tempfile.mkdtemp(prefix="s326-home-"))
        self.addCleanup(shutil.rmtree, str(home), True)
        return home

    def _production_shape_env(self, home: Path) -> Dict[str, str]:
        """The env ``verify-counts.sh`` runs its collect in: no audit carriers,
        no test-harness signals, HOME = the throwaway tree. PYTHONUSERBASE is
        re-exported to the REAL user site so the child can import pytest
        (HOME redirect alone loses the user site — measured)."""
        drop = set(test_isolation.ALL_AUDIT_CARRIERS)
        drop.update(test_isolation.WHOLE_DIR_OVERRIDE_CARRIERS)
        drop.update((
            test_isolation.TEST_HARNESS_VAR,
            test_isolation.SYNC_MODE_VAR,
            test_isolation.LIVE_LOG_SNAPSHOT_VAR,
            "PYTEST_ADDOPTS",
        ))
        env = {
            k: v for k, v in os.environ.items()
            if k not in drop and not k.startswith("PYTEST_")
        }
        env["HOME"] = str(home)
        # TestEnvContext sandboxes CLAUDE_PROJECT_DIR; the collect must see the
        # real repo (that is where verify-counts.sh runs it).
        env["CLAUDE_PROJECT_DIR"] = str(_REPO_ROOT)
        env["PYTHONUSERBASE"] = os.environ.get("PYTHONUSERBASE") or site.getuserbase()
        return env

    def _collect(self, args: List[str], env: Dict[str, str], cwd: Path):
        return subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q",
             "-p", "no:cacheprovider", *args],
            cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=600,
        )

    def _assert_collect_writes_nothing(self, args, label: str, min_collected: int) -> None:
        """Collect ``args`` in production shape and assert (a) the child collected
        cleanly, (b) enough was collected for the negative to mean anything,
        (c) no audit-log line exists under the throwaway HOME."""
        home = self._throwaway_home()
        res = self._collect(list(args), self._production_shape_env(home), _REPO_ROOT)
        tail = "\n".join(res.stdout.splitlines()[-3:])
        self.assertEqual(res.returncode, 0, msg=f"{label}: child collect failed:\n{res.stderr[-800:]}\n{tail}")
        collected = 0
        for tok in tail.replace(",", " ").split():
            if tok.isdigit():
                collected = int(tok)
                break
        self.assertGreaterEqual(collected, min_collected,
                                msg=f"{label}: vacuous collect ({collected}): {tail!r}")
        lines = _audit_log_lines(home)
        self.assertEqual(lines, {}, msg=(
            f"{label}: collection-time code reached the audit emitter — these lines "
            f"would have landed in the LIVE chain on a real run: {lines}"
        ))

    def test_collecting_hook_legs_writes_no_audit_lines(self):
        """NEGATIVE (the class), leg A — ``.claude/hooks/tests`` (where the S326
        emitter lived) + ``.claude/hooks/_lib/tests``. Needs nothing beyond
        pytest, so it runs in EVERY CI job, including the hook-only one."""
        self._assert_collect_writes_nothing(
            [".claude/hooks/tests", ".claude/hooks/_lib/tests"], "hook legs", _MIN_COLLECTED)

    def test_collecting_all_testpaths_writes_no_audit_lines(self):
        """NEGATIVE (the class), leg B — ALL configured testpaths, i.e. exactly
        the collect ``verify-counts.sh`` runs. ``.claude/scripts/tests`` reaches
        a PyYAML-requiring script at import (``SystemExit(2)`` ⇒ pytest
        INTERNALERROR without PyYAML) and the hook-only CI job installs no
        PyYAML — so this leg runs where PyYAML is importable and SKIPS, visibly,
        where it is not (S326 fix-forward: the first CI run reported that
        dependency gap as a red guard)."""
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML not importable here: the full-testpaths leg needs it at collection")
        self._assert_collect_writes_nothing([], "all testpaths", _MIN_COLLECTED)

    def test_positive_control_import_time_emitter_is_seen(self):
        """POSITIVE CONTROL (the instrument): a module that calls
        ``policy.decide()`` at import — the exact mechanism of the S326 emitter —
        collected in the same production shape, DOES leave audit-log lines
        under the throwaway HOME."""
        home = self._throwaway_home()
        probe_dir = Path(tempfile.mkdtemp(prefix="s326-probe-"))
        self.addCleanup(shutil.rmtree, str(probe_dir), True)
        first_row = _BASH_FIXTURES.read_text(encoding="utf-8").splitlines()[0]
        (probe_dir / "test_s326_probe.py").write_text(
            "import json, sys\n"
            f"sys.path.insert(0, {str(_HOOKS_DIR)!r})\n"
            "from _lib import policy as _policy\n"
            f"_pol = _policy.load({str(_BASH_POLICY)!r})\n"
            f"_pol.decide(json.loads({first_row!r})['input'])  # import-time, on purpose\n"
            "\n\ndef test_probe():\n    assert True\n",
            encoding="utf-8",
        )
        res = self._collect(
            [f"--rootdir={probe_dir}", str(probe_dir / "test_s326_probe.py")],
            self._production_shape_env(home), probe_dir,
        )
        self.assertEqual(res.returncode, 0, msg=f"probe collect failed:\n{res.stderr[-800:]}")
        lines = _audit_log_lines(home)
        self.assertTrue(lines and sum(lines.values()) >= 1, msg=(
            "positive control is DEAD: an import-time policy.decide() left no "
            f"audit-log line under the throwaway HOME (found: {lines}); the "
            "negative guard above cannot be trusted"
        ))

    def test_collection_window_tree_is_removed_at_exit(self):
        """pair-rail r2 P2 — the throwaway tree must not outlive the process:
        atexit is LIFO, so the cleanup has to be registered BEFORE audit_emit
        registers the spool drain (else the drain re-creates the tree after
        rmtree). Measured on the pre-cure tree: +1 leaked dir per collect."""
        # The child gets a TMPDIR this test OWNS: under xdist another worker
        # may be spawning its own collect at the same time, and counting the
        # shared system tempdir reported that sibling as a "leak".
        home = self._throwaway_home()
        child_tmp = Path(tempfile.mkdtemp(prefix="s326-child-tmp-"))
        self.addCleanup(shutil.rmtree, str(child_tmp), True)
        env = self._production_shape_env(home)
        env["TMPDIR"] = str(child_tmp)
        # Anti-vacuity: the child interpreter really resolves its tempdir to
        # OUR directory (else an empty glob below would pass trivially).
        probe = subprocess.run(
            [sys.executable, "-c", "import tempfile; print(tempfile.gettempdir())"],
            env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(Path(probe.stdout.strip()).resolve(), child_tmp.resolve())
        res = self._collect([".claude/hooks/tests/test_runtime_paths.py"], env, _REPO_ROOT)
        self.assertEqual(res.returncode, 0, msg=res.stderr[-800:])
        leaked = sorted(p.name for p in child_tmp.glob(test_isolation.COLLECT_WINDOW_PREFIX + "*"))
        self.assertEqual(leaked, [], msg="collection-window tree(s) leaked: %s" % leaked)


class TestCollectionWindowRedirect(TestEnvContext):
    """S326 structural cure — ``_lib/test_isolation`` Axis 3, asserted in-process.
    These fail on a tree WITHOUT the cure (the attributes do not exist), which
    is how a partial land shows up."""

    def test_live_snapshot_was_captured_before_any_redirect(self):
        snap = getattr(test_isolation, "IMPORT_TIME_LIVE_LOG_SNAPSHOT", None)
        self.assertIsInstance(snap, str, "no import-time live-log snapshot")
        self.assertNotIn(getattr(test_isolation, "COLLECT_WINDOW_PREFIX", "ceo-collect-isolation-"), snap)
        self.assertNotIn("ceo-suite-isolation-", snap)
        # The contract is "absolute path outside isolation trees" — never a
        # basename: a suite launched under a documented CEO_AUDIT_LOG_PATH
        # (any file name) captures THAT path at import (pair-rail r7 P2).
        self.assertTrue(os.path.isabs(snap), snap)

    def test_collection_window_dir_exists_with_the_prefix(self):
        d = getattr(test_isolation, "COLLECT_WINDOW_DIR", None)
        self.assertIsNotNone(d, "Axis 3 did not create a collection-window tree")
        self.assertTrue(Path(d).is_dir(), d)
        self.assertTrue(Path(d).name.startswith(test_isolation.COLLECT_WINDOW_PREFIX), d)

    def test_published_snapshot_var_is_the_import_time_value(self):
        self.assertEqual(
            os.environ.get(test_isolation.LIVE_LOG_SNAPSHOT_VAR),
            test_isolation.IMPORT_TIME_LIVE_LOG_SNAPSHOT,
        )

    def test_child_process_preserves_the_inherited_snapshot(self):
        """pair-rail r1 P1 — an xdist worker inherits the true snapshot AND a
        CEO_AUDIT_LOG_DIR already pointed at the parent's collection tree. Import
        in that shape must keep the inherited truth, not re-resolve it."""
        fake_collect = self._tmp_root / (test_isolation.COLLECT_WINDOW_PREFIX + "parent") / "audit"
        fake_collect.mkdir(parents=True)
        true_snapshot = str(self._tmp_root / "true-home" / ".claude" / "projects" / "-x" / "audit-log.jsonl")
        env = self.subprocess_env()
        env["CEO_AUDIT_LOG_DIR"] = str(fake_collect)
        env[test_isolation.LIVE_LOG_SNAPSHOT_VAR] = true_snapshot
        code = (
            "import sys\n"
            f"sys.path.insert(0, {str(_HOOKS_DIR)!r})\n"
            "from _lib import test_isolation as ti\n"
            "print('SNAP=' + str(ti.IMPORT_TIME_LIVE_LOG_SNAPSHOT))\n"
        )
        res = subprocess.run([sys.executable, "-c", code], env=env,
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, msg=res.stderr[-800:])
        snap = [ln for ln in res.stdout.splitlines() if ln.startswith("SNAP=")]
        self.assertTrue(snap, msg=res.stdout)
        self.assertEqual(snap[0][len("SNAP="):], true_snapshot)

    def test_custom_basename_snapshot_is_preserved(self):
        """pair-rail r6 P2 — a supported CEO_AUDIT_LOG_PATH override may name
        the live log differently; an inherited absolute .jsonl outside any
        isolation tree is truth and must be kept, whatever its basename."""
        fake_collect = self._tmp_root / (test_isolation.COLLECT_WINDOW_PREFIX + "parent") / "audit"
        fake_collect.mkdir(parents=True)
        custom = str(self._tmp_root / "true-home" / "srv" / "audit" / "current.log")
        env = self.subprocess_env()
        env["CEO_AUDIT_LOG_DIR"] = str(fake_collect)
        env[test_isolation.LIVE_LOG_SNAPSHOT_VAR] = custom
        code = (
            "import sys\n"
            f"sys.path.insert(0, {str(_HOOKS_DIR)!r})\n"
            "from _lib import test_isolation as ti\n"
            "print('SNAP=' + str(ti.IMPORT_TIME_LIVE_LOG_SNAPSHOT))\n"
        )
        res = subprocess.run([sys.executable, "-c", code], env=env,
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, msg=res.stderr[-800:])
        snap = [ln for ln in res.stdout.splitlines() if ln.startswith("SNAP=")][0][len("SNAP="):]
        self.assertEqual(snap, custom)

    def test_stale_inherited_snapshot_inside_an_isolation_tree_is_ignored(self):
        """The inherited value is trusted only when well-formed: a path inside a
        collection/suite isolation tree is re-resolved, never adopted."""
        fake_collect = self._tmp_root / (test_isolation.COLLECT_WINDOW_PREFIX + "parent") / "audit"
        fake_collect.mkdir(parents=True)
        env = self.subprocess_env()
        env["CEO_AUDIT_LOG_DIR"] = str(fake_collect)
        env[test_isolation.LIVE_LOG_SNAPSHOT_VAR] = str(fake_collect / "audit-log.jsonl")
        code = (
            "import sys\n"
            f"sys.path.insert(0, {str(_HOOKS_DIR)!r})\n"
            "from _lib import test_isolation as ti\n"
            "print('SNAP=' + str(ti.IMPORT_TIME_LIVE_LOG_SNAPSHOT))\n"
        )
        res = subprocess.run([sys.executable, "-c", code], env=env,
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, msg=res.stderr[-800:])
        snap = [ln for ln in res.stdout.splitlines() if ln.startswith("SNAP=")][0][len("SNAP="):]
        # realpath on BOTH sides: on macOS mkdtemp lives under /var/... and the
        # resolver returns /private/var/..., so a plain string compare passes
        # vacuously (pair-rail r2 P1 caught exactly that).
        self.assertNotEqual(os.path.realpath(snap),
                            os.path.realpath(str(fake_collect / "audit-log.jsonl")))
        self.assertNotIn(test_isolation.COLLECT_WINDOW_PREFIX, snap)
