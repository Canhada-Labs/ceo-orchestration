"""Tests for the free half of PLAN-190 W2: ``mutant_sandbox.py``,
``worktree_lock.py`` and ``phase_checkpoint.py``.

Properties proven (the order's validation list):
* a mutant never touches the implementation tree, even when the run is
  interrupted (timeout) — the tree is byte-identical and the sandbox is gone;
* a recorded verification is reused (``query``) for the same (rev, mutant, cmd)
  and NOT for another revision;
* two writers on the same worktree: the second is refused; a stale holder can
  be stolen, a fresh one cannot;
* a phase resumed at the same revision skips the recorded steps; at another
  revision it skips none.
Everything runs in temp git repos; neutral fixtures only."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO = Path(__file__).resolve()
while not (_REPO / ".claude").is_dir() or not (_REPO / "VERSION").is_file():
    if _REPO.parent == _REPO:
        raise RuntimeError("repo root not found")
    _REPO = _REPO.parent
sys.path.insert(0, str(_REPO / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

SCRIPTS = _REPO / ".claude" / "scripts"
MUT = SCRIPTS / "mutant_sandbox.py"
LOCK = SCRIPTS / "worktree_lock.py"
CKPT = SCRIPTS / "phase_checkpoint.py"


def _sh(args, cwd=None, timeout=120):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=cwd, timeout=timeout)


def _git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True)


def _mk_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    (repo / "m.py").write_text("def f():\n    return 2\n", encoding="utf-8")
    (repo / "check.py").write_text("import sys\nfrom m import f\nsys.exit(0 if f() == 2 else 1)\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    return repo


def _mutant(root: Path, name: str, old: str, new: str) -> Path:
    p = root / name
    p.write_text("--- a/m.py\n+++ b/m.py\n@@ -1,2 +1,2 @@\n def f():\n-    return %s\n+    return %s\n" % (old, new), encoding="utf-8")
    return p


class MutantSandbox(TestEnvContext):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.repo = _mk_repo(self.root)
        self.ledger = self.root / "mutants.jsonl"
        self.scratch = self.root / "scratch"
        self.cmd = "%s check.py" % sys.executable

    def _run(self, mutant, cmd=None, timeout="120"):
        return _sh([str(MUT), "run", "--repo", str(self.repo), "--mutant", str(mutant), "--cmd", cmd or self.cmd, "--ledger", str(self.ledger), "--timeout", timeout, "--scratch-root", str(self.scratch)])

    def test_killed_mutant_and_tree_untouched(self):
        m = _mutant(self.root, "m1.diff", "2", "3")
        before = (self.repo / "m.py").read_bytes()
        r = self._run(m)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)  # 0 = killed
        self.assertIn("KILLED", r.stdout)
        self.assertEqual((self.repo / "m.py").read_bytes(), before)
        self.assertEqual(_git(self.repo, "status", "--porcelain").stdout, "")
        self.assertEqual([p for p in self.scratch.glob("mut-*")], [], "sandbox must be removed")

    def test_survived_mutant_is_reported_as_such(self):
        m = _mutant(self.root, "m2.diff", "2", "2 + 0")
        r = self._run(m)
        self.assertEqual(r.returncode, 1)  # 1 = survived
        self.assertIn("SURVIVED", r.stdout)

    def test_interrupted_run_leaves_no_sandbox_and_no_mutation(self):
        m = _mutant(self.root, "m3.diff", "2", "3")
        slow = "%s -c \"import time; time.sleep(30)\"" % sys.executable
        r = self._run(m, cmd=slow, timeout="1")
        self.assertEqual(r.returncode, 2)  # error (timeout)
        self.assertIn("timed out", r.stdout)
        self.assertEqual(_git(self.repo, "status", "--porcelain").stdout, "")
        self.assertEqual([p for p in self.scratch.glob("mut-*")], [])
        recs = [json.loads(ln) for ln in self.ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(recs[-1]["outcome"], "error")

    def test_query_reuses_recorded_verification_only_for_same_rev(self):
        m = _mutant(self.root, "m4.diff", "2", "3")
        self.assertEqual(self._run(m).returncode, 0)
        q = _sh([str(MUT), "query", "--repo", str(self.repo), "--mutant", str(m), "--cmd", self.cmd, "--ledger", str(self.ledger)])
        self.assertEqual(q.returncode, 0, q.stdout + q.stderr)
        self.assertEqual(json.loads(q.stdout)["outcome"], "killed")
        (self.repo / "note.txt").write_text("x", encoding="utf-8")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "moved")
        q2 = _sh([str(MUT), "query", "--repo", str(self.repo), "--mutant", str(m), "--cmd", self.cmd, "--ledger", str(self.ledger)])
        self.assertEqual(q2.returncode, 4, "a new revision must not reuse the old verification")

    def test_non_applying_mutant_is_error_not_silent(self):
        m = _mutant(self.root, "m5.diff", "99", "3")
        r = self._run(m)
        self.assertEqual(r.returncode, 2)
        self.assertIn("does not apply", r.stdout)


class WorktreeLock(TestEnvContext):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.wt = Path(self._tmp.name) / "wt"
        self.wt.mkdir()

    def _lock(self, *args):
        return _sh([str(LOCK), *args])

    def test_second_writer_is_refused_and_same_owner_refreshes(self):
        self.assertEqual(self._lock("acquire", "--worktree", str(self.wt), "--owner", "agent-A").returncode, 0)
        r = self._lock("acquire", "--worktree", str(self.wt), "--owner", "agent-B")
        self.assertEqual(r.returncode, 3)
        self.assertIn("HELD by agent-A", r.stderr)
        self.assertEqual(self._lock("acquire", "--worktree", str(self.wt), "--owner", "agent-A").returncode, 0)
        st = json.loads(self._lock("status", "--worktree", str(self.wt)).stdout)
        self.assertEqual(st["held_by"], "agent-A")
        self.assertFalse(st["stale"])

    def test_release_only_by_owner_unless_forced(self):
        self._lock("acquire", "--worktree", str(self.wt), "--owner", "agent-A")
        self.assertEqual(self._lock("release", "--worktree", str(self.wt), "--owner", "agent-B").returncode, 3)
        self.assertEqual(self._lock("release", "--worktree", str(self.wt), "--owner", "agent-B", "--force").returncode, 0)
        self.assertIn("FREE", self._lock("status", "--worktree", str(self.wt)).stdout)
        log = (self.wt / ".claude" / "state" / "writer.lock.log").read_text(encoding="utf-8")
        self.assertIn("force-released", log)

    def test_steal_only_when_stale(self):
        self._lock("acquire", "--worktree", str(self.wt), "--owner", "agent-A", "--ttl-minutes", "30")
        self.assertEqual(self._lock("steal", "--worktree", str(self.wt), "--owner", "agent-B", "--stale-minutes", "10").returncode, 3)
        p = self.wt / ".claude" / "state" / "writer.lock"
        lock = json.loads(p.read_text(encoding="utf-8"))
        old = datetime.now(timezone.utc) - timedelta(minutes=45)
        lock["heartbeat"] = old.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        p.write_text(json.dumps(lock), encoding="utf-8")
        self.assertTrue(json.loads(self._lock("status", "--worktree", str(self.wt)).stdout)["stale"])
        r = self._lock("steal", "--worktree", str(self.wt), "--owner", "agent-B", "--stale-minutes", "10")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(self._lock("status", "--worktree", str(self.wt)).stdout)["held_by"], "agent-B")


class PhaseCheckpoint(TestEnvContext):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ledger = Path(self._tmp.name) / "ckpt.jsonl"

    def _c(self, *args):
        return _sh([str(CKPT), *args, "--ledger", str(self.ledger)])

    def test_resume_skips_recorded_steps_at_same_rev_only(self):
        for k in range(3):
            self.assertEqual(self._c("mark", "--run", "wf_1", "--phase", "cetico", "--step", "mut-%d" % k, "--rev", "aaa111", "--evidence", "killed").returncode, 0)
        self.assertEqual(self._c("mark", "--run", "wf_1", "--phase", "cetico", "--step", "mut-1", "--rev", "aaa111").returncode, 0)  # idempotent
        st = json.loads(self._c("status", "--run", "wf_1", "--phase", "cetico", "--rev", "aaa111", "--json").stdout)
        self.assertEqual([s["step"] for s in st["done_steps"]], ["mut-0", "mut-1", "mut-2"])
        self.assertFalse(st["phase_complete"])
        other = self._c("status", "--run", "wf_1", "--phase", "cetico", "--rev", "bbb222", "--json")
        self.assertEqual(other.returncode, 4)
        self.assertEqual(json.loads(other.stdout)["done_steps"], [])
        self.assertEqual(json.loads(other.stdout)["stale_steps_other_rev"], 3)

    def test_phase_done_marker_is_revision_bound(self):
        self._c("done", "--run", "wf_2", "--phase", "gate", "--rev", "ccc333")
        self.assertTrue(json.loads(self._c("status", "--run", "wf_2", "--phase", "gate", "--rev", "ccc333", "--json").stdout)["phase_complete"])
        self.assertFalse(json.loads(self._c("status", "--run", "wf_2", "--phase", "gate", "--rev", "ddd444", "--json").stdout)["phase_complete"])
        time.sleep(0.01)
        lines = self.ledger.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1, "append-only: one record")
