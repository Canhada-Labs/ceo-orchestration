"""PLAN-085 Wave B.3 — audit_log.append_entry HMAC chain coverage.

6 cases on the inline HMAC computation of append_entry (the SEQUENTIAL
two-writer chain gap, T0-line-168 transition_violation):

  1. test_append_entry_writes_hmac_field
  2. test_consecutive_entries_chain_correctly
  3. test_disabled_hmac_yields_null_field
  4. test_agent_spawn_action_carries_hmac
  5. test_append_entry_preserves_f0106_symlink_defense
  6. test_hmac_error_recorded_on_subsystem_failure

PLAN-194 (S361) cures the CONCURRENT case (rc.1 condition 67): key, read, HMAC,
append and sidecar share ONE FileLock after the rotation (+ marker). Pinned by: AST
census, read-to-append window, lock timeout, rotation, N processes on a barrier.
"""

from __future__ import annotations

import ast
import importlib
import json
import multiprocessing
import os
import random
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib.testing import TestEnvContext  # noqa: E402


def _race_writer(kind, worker_id, iterations, expected_log, barrier):
    """Child (spawn): one writer kind; exit 3 unless the log is the sandbox's."""
    if os.environ.get("CEO_AUDIT_LOG_PATH") != expected_log:
        sys.exit(3)
    import audit_log
    from _lib import audit_emit
    paths = audit_log.audit_paths()
    if str(paths["log"]) != expected_log or str(audit_emit._log_path()) != expected_log:
        sys.exit(3)
    rng = random.Random(worker_id)
    barrier.wait(60)  # every writer + the parent released at once
    for i in range(iterations):
        if kind == "spawn":
            audit_log.append_entry({"action": "agent_spawn", "session_id": "race-spawn-%d" % worker_id},
                                   paths=paths, threshold_bytes=10 ** 9)
        else:
            audit_emit.emit_debate_event(plan_id="PLAN-RACE", round_num=i + 1, phase="start",
                                         agent="race-emit", session_id="race-emit-%d" % worker_id)
        if kind == "emit" and i % 3 == 2 and os.environ.get("CEO_AUDIT_SYNC_MODE", "") != "1":
            from _lib import spool_writer  # spool: forced drain, like a hook process at exit
            spool_writer.drain_now(force=True)
        time.sleep(rng.uniform(0.0, 0.004))


def _foreign_emitter(ready, go, locking, appended, expected_log):
    """Child (spawn): once released, append ONE sync audit_emit line."""
    if os.environ.get("CEO_AUDIT_LOG_PATH") != expected_log:
        sys.exit(3)
    from _lib import audit_emit
    ready.set()
    go.wait(60)
    locking.set()  # about to take the log lock inside emit_debate_event
    audit_emit.emit_debate_event(plan_id="PLAN-RACE", round_num=1, phase="start",
                                 agent="foreign", session_id="foreign")
    appended.set()


def _unlocked_prev_reads(source: str):
    """(reads, unlocked lines) of read_prev_hmac() in a module that names a write primitive in
    any form; locked = lexically in a `with FileLock(` block that calls write_last_hmac."""
    defs = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)

    def name(f):
        return f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")

    def calls(node, skip_defs):
        for child in ast.iter_child_nodes(node):
            if skip_defs and isinstance(child, defs):
                continue
            if isinstance(child, ast.Call):
                yield child
            yield from calls(child, skip_defs)

    def ref(n):  # every way a module can name a primitive
        if isinstance(n, ast.ImportFrom):
            return " ".join(a.name for a in n.names)
        v = getattr(n, "value", None) if isinstance(n, ast.Constant) else None
        return name(n) if isinstance(n, (ast.Attribute, ast.Name)) else (v if isinstance(v, str) else "")

    tree = ast.parse(source)
    every, nodes = list(calls(tree, False)), list(ast.walk(tree))
    if not any(w in ref(n).split() for n in nodes for w in ("compute_entry_hmac", "write_last_hmac")):
        return 0, []
    locked = set()
    for w in ast.walk(tree):
        if isinstance(w, (ast.With, ast.AsyncWith)) and any(
                isinstance(i.context_expr, ast.Call) and name(i.context_expr.func) == "FileLock"
                for i in w.items):
            inner = [c for s in w.body if not isinstance(s, defs) for c in calls(s, True)]
            if any(name(c.func) == "write_last_hmac" for c in inner):
                locked.update(id(c) for c in inner)
    reads = [c for c in every if name(c.func) == "read_prev_hmac"]
    funcs = {id(c.func) for c in every}  # alias / import / getattr string hides a read: fail-closed
    odd = [n.lineno for n in nodes if "read_prev_hmac" in ref(n).split() and id(n) not in funcs]
    return len(reads), sorted([c.lineno for c in reads if id(c) not in locked] + odd)


def _kind_switches(lines) -> int:
    kinds = [ln.get("action") for ln in lines if ln.get("action") in ("agent_spawn", "debate_event")]
    return sum(1 for a, b in zip(kinds, kinds[1:]) if a != b)


def _log_lines(log_path: Path) -> list:
    if not log_path.exists():
        return []
    return [json.loads(ln) for ln in log_path.read_text(encoding="utf-8").splitlines()
            if ln.strip()]


class TestTwoWriterChain(TestEnvContext):
    """B.3 inline HMAC chain coverage tests."""

    def _build_paths(self) -> dict:
        log_file = self.audit_dir / "audit-log.jsonl"
        return {
            "dir": self.audit_dir,
            "log": log_file,
            "lock": str(self.audit_dir / "audit-log.lock"),
            "err": self.audit_dir / "audit-log.errors",
        }

    def _read_lines(self, paths: dict) -> list:
        if not paths["log"].exists():
            return []
        return [
            json.loads(line)
            for line in paths["log"].read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_append_entry_writes_hmac_field(self) -> None:
        """First entry after B.3 must carry hmac (or hmac_error) field."""
        import audit_log
        paths = self._build_paths()
        entry = {"action": "agent_spawn", "ts": "2026-05-12T00:00:00Z"}
        audit_log.append_entry(entry, paths=paths, threshold_bytes=10**9)
        lines = self._read_lines(paths)
        self.assertEqual(len(lines), 1)
        self.assertIn("hmac", lines[0], msg="entry missing hmac field")

    def test_consecutive_entries_chain_correctly(self) -> None:
        """Second entry's HMAC depends on first entry's HMAC (chain)."""
        import audit_log
        paths = self._build_paths()
        audit_log.append_entry(
            {"action": "agent_spawn", "ts": "2026-05-12T00:00:01Z"},
            paths=paths, threshold_bytes=10**9,
        )
        audit_log.append_entry(
            {"action": "agent_spawn", "ts": "2026-05-12T00:00:02Z"},
            paths=paths, threshold_bytes=10**9,
        )
        lines = self._read_lines(paths)
        self.assertEqual(len(lines), 2)
        # Both have hmac set; if HMAC subsystem available, they should differ.
        h1, h2 = lines[0].get("hmac"), lines[1].get("hmac")
        if h1 is not None and h2 is not None:
            self.assertNotEqual(h1, h2, msg="chain not advancing")

    def test_disabled_hmac_yields_null_field(self) -> None:
        """When CEO_AUDIT_HMAC_DISABLE=1 the hmac field is None but present."""
        import audit_log
        os.environ["CEO_AUDIT_HMAC_DISABLE"] = "1"
        try:
            paths = self._build_paths()
            audit_log.append_entry(
                {"action": "agent_spawn", "ts": "2026-05-12T00:00:03Z"},
                paths=paths, threshold_bytes=10**9,
            )
            lines = self._read_lines(paths)
            self.assertEqual(len(lines), 1)
            self.assertIsNone(lines[0].get("hmac"))
        finally:
            os.environ.pop("CEO_AUDIT_HMAC_DISABLE", None)

    def test_agent_spawn_action_carries_hmac(self) -> None:
        """The specific T0-line-168 finding: agent_spawn entries get HMAC."""
        import audit_log
        paths = self._build_paths()
        audit_log.append_entry(
            {"action": "agent_spawn", "session_id": "test"},
            paths=paths, threshold_bytes=10**9,
        )
        lines = self._read_lines(paths)
        self.assertEqual(len(lines), 1)
        # If HMAC subsystem is available, hmac MUST be a hex string,
        # not None — closes the 100% agent_spawn coverage AC.
        try:
            from _lib import audit_hmac
            if not audit_hmac.is_disabled():
                self.assertIsNotNone(
                    lines[0].get("hmac"),
                    msg=(
                        "agent_spawn entry missing HMAC — B.3 chain "
                        "coverage AC not satisfied"
                    ),
                )
        except ImportError:
            self.skipTest("audit_hmac unavailable; B.3 HMAC path inactive")

    def test_append_entry_preserves_f0106_symlink_defense(self) -> None:
        """B.3 inline HMAC must not regress F-01-06 symlink/uid defense."""
        import audit_log
        paths = self._build_paths()
        # Plant a symlink at the log path; F-01-06 must reject the write.
        paths["log"].parent.mkdir(parents=True, exist_ok=True)
        evil_target = self._tmp_root / "evil-target.jsonl"
        evil_target.touch()
        # Pre-create a symlink at the audit log path
        log_path = paths["log"]
        if log_path.exists() or log_path.is_symlink():
            log_path.unlink()
        log_path.symlink_to(evil_target)
        audit_log.append_entry(
            {"action": "agent_spawn"},
            paths=paths, threshold_bytes=10**9,
        )
        # F-01-06 should refuse → evil_target stays empty.
        self.assertEqual(
            evil_target.stat().st_size, 0,
            msg="F-01-06 regression — symlink write was NOT blocked",
        )

    def test_hmac_error_recorded_on_subsystem_failure(self) -> None:
        """If the HMAC subsystem raises, entry has hmac=None + hmac_error set."""
        import audit_log
        paths = self._build_paths()
        # Patch audit_hmac.get_or_create_key to raise.
        from _lib import audit_hmac as _audit_hmac
        original = _audit_hmac.get_or_create_key

        def _boom() -> bytes:
            raise _audit_hmac.AuditHmacError("test-injected failure")

        _audit_hmac.get_or_create_key = _boom  # type: ignore[assignment]
        try:
            audit_log.append_entry(
                {"action": "agent_spawn"},
                paths=paths, threshold_bytes=10**9,
            )
            lines = self._read_lines(paths)
            self.assertEqual(len(lines), 1)
            self.assertIsNone(lines[0].get("hmac"))
            self.assertEqual(
                lines[0].get("hmac_error"),
                "AuditHmacError",
                msg="hmac_error not recorded under injected failure",
            )
        finally:
            _audit_hmac.get_or_create_key = original  # type: ignore[assignment]



class _ChainCase(TestEnvContext):
    def _paths(self) -> dict:
        paths = importlib.import_module("audit_log").audit_paths()
        self.assertEqual(paths["log"], self.audit_dir / "audit-log.jsonl")
        self.assertEqual(Path(paths["lock"]), self.audit_dir / "audit-log.lock")
        return paths

    def _spawn(self, paths: dict, sid: str, threshold: int = 10 ** 9) -> None:
        importlib.import_module("audit_log").append_entry(
            {"action": "agent_spawn", "session_id": sid},
            paths=paths, threshold_bytes=threshold,
        )

    def _assert_intact(self, log_path: Path, expected_count: int) -> None:
        res = importlib.import_module("_lib.audit_hmac").verify_chain(log_path)
        self.assertTrue(res.is_intact, msg="chain broken: %s %s line=%s" % (res.status, res.reason, res.line))
        self.assertEqual(res.verified_count, expected_count)


class TestPrevHmacReadCensus(_ChainCase):
    """Class guard: no chain writer reads the predecessor outside `with FileLock(`."""

    def test_every_chain_writer_reads_the_predecessor_under_the_lock(self) -> None:
        reads, unlocked = 0, []
        for root in (_HOOKS, REPO_ROOT / ".claude" / "scripts", REPO_ROOT / "scripts"):
            for p in sorted(root.rglob("*.py")):
                if {"tests", "__pycache__"} & set(p.parts) or p.name == "audit_hmac.py":
                    continue
                src = p.read_text(encoding="utf-8", errors="replace")
                if "read_prev_hmac" in src:
                    n, bad = _unlocked_prev_reads(src)
                    reads += n
                    unlocked += ["%s:%d" % (p.relative_to(REPO_ROOT).as_posix(), ln) for ln in bad]
        self.assertEqual(unlocked, [])
        self.assertGreaterEqual(reads, 2, msg="vacuous: audit_log + audit_emit expected")

    def test_census_flags_synthetic_unlocked_writers(self) -> None:
        w, lk = "    with FileLock('l'):\n", "def f(h, FileLock):\n"
        for body, want in ((("    p = h.read_prev_hmac()\n" + w + "        h.write_last_hmac(p)\n"), (1, [2])),
                           (w + "        p = h.read_prev_hmac()\n" + w + "        h.write_last_hmac(p)\n", (1, [3])),
                           ("    r = h.read_prev_hmac\n" + w + "        h.write_last_hmac(r())\n", (0, [2])),
                           ("    c, s = h.compute_entry_hmac, h.write_last_hmac\n    p = h.read_prev_hmac()\n"
                            + w + "        s(c(p))\n", (1, [3])),
                           ("    p = getattr(h, 'read_prev_hmac')()\n" + w + "        h.write_last_hmac(p)\n", (0, [2])),
                           (w + "        h.write_last_hmac(h.read_prev_hmac())\n", (1, []))):
            self.assertEqual(_unlocked_prev_reads(lk + body), want)
        a, b = {"action": "agent_spawn"}, {"action": "debate_event"}  # interleave guard controls
        self.assertLess(_kind_switches([a] * 4 + [b] * 2), 2)
        self.assertGreaterEqual(_kind_switches([a, b, a]), 2)


@pytest.mark.serial
class TestReadToAppendWindow(_ChainCase):
    """After the predecessor read a foreign sync audit_emit writer, already at the lock, gets
    1.0 s (its lock budget is 2.5 s): it must land AFTER our line, never in between."""

    def test_no_foreign_append_between_prev_read_and_append(self) -> None:
        from _lib import audit_hmac
        ctx = multiprocessing.get_context("spawn")
        paths = self._paths()
        self._spawn(paths, "seed")
        ready, go, locking, appended = ctx.Event(), ctx.Event(), ctx.Event(), ctx.Event()
        child = ctx.Process(target=_foreign_emitter,
                            args=(ready, go, locking, appended, str(paths["log"])))
        with mock.patch.dict(os.environ, {"CEO_AUDIT_LOG_FALLBACK_PATH": str(self._tmp_root / "fb.log")}):
            child.start()  # the child inherits the sandboxed fallback
        self.assertTrue(ready.wait(60), msg="foreign writer never got ready")
        real_read, during = audit_hmac.read_prev_hmac, []

        def _read_then_release():
            prev = real_read()
            go.set()
            during.append((locking.wait(60), appended.wait(1.0)))
            return prev

        try:
            with mock.patch.object(audit_hmac, "read_prev_hmac", _read_then_release):
                self._spawn(paths, "victim")
        finally:
            go.set()
            child.join(60)
        self.assertEqual(child.exitcode, 0)
        self.assertEqual(during, [(True, False)], msg="(child at the lock, landed in between)")
        lines = _log_lines(paths["log"])
        self.assertEqual([ln.get("session_id") for ln in lines], ["seed", "victim", "foreign"])
        self._assert_intact(paths["log"], 3)


class TestLockTimeoutFailOpen(_ChainCase):
    """Lock timeout: entry dropped with a breadcrumb, chain state untouched."""

    def test_lock_timeout_drops_entry_and_leaves_chain_state(self) -> None:
        audit_log = importlib.import_module("audit_log")
        from _lib import audit_hmac
        paths = self._paths()
        self._spawn(paths, "seed")
        before = audit_hmac.last_hmac_path().read_bytes()

        class _TimesOut(audit_log.FileLock):  # type: ignore[misc, name-defined]
            def __enter__(self):
                raise audit_log.FileLockTimeout("injected by the test")

        with mock.patch.object(audit_log, "FileLock", _TimesOut):
            self._spawn(paths, "dropped")  # returns normally: never blocks
        self.assertEqual([ln.get("session_id") for ln in _log_lines(paths["log"])], ["seed"])
        self.assertEqual(audit_hmac.last_hmac_path().read_bytes(), before)
        self.assertIn('lock timeout (stale?)  would-log={"action":"agent_spawn","session_id":"dropped"',
                      Path(paths["err"]).read_text(encoding="utf-8"))


class TestRotationByThisWriter(_ChainCase):
    """A rotation done inside append_entry follows ADR-055-AMEND-2."""

    def test_rotation_starts_fresh_log_with_marker_and_both_files_verify(self) -> None:
        from _lib import audit_hmac
        paths = self._paths()
        for sid in ("seed-1", "seed-2"):
            self._spawn(paths, sid)
        archived_tail = _log_lines(paths["log"])[-1]["hmac"]
        self._spawn(paths, "after-rotation", threshold=1)  # rotates the 2-line log
        archives = sorted(self.audit_dir.glob("audit-log-*.jsonl"))
        self.assertEqual(len(archives), 1, msg=[p.name for p in archives])
        self._assert_intact(archives[0], 2)
        fresh = _log_lines(paths["log"])
        self.assertEqual([ln.get("action") for ln in fresh], ["chain_reset_marker", "agent_spawn"])
        self.assertEqual(fresh[0].get("previous_archive_last_hmac"), archived_tail)
        self._assert_intact(paths["log"], 2)
        self.assertTrue(audit_hmac.rotation_manifest_path().is_file())

    def test_marker_append_failure_leaves_this_line_unchained(self) -> None:
        from _lib import audit_emit, audit_hmac
        paths, real = self._paths(), audit_emit._emit_chain_reset_marker_under_lock
        self._spawn(paths, "seed")

        class _NoAppend(type(paths["log"])):  # the helper persists last-hmac, then this fails
            def open(self, *a, **k):
                raise OSError("injected marker append failure")

        with mock.patch.object(audit_emit, "_emit_chain_reset_marker_under_lock",
                               lambda log, **kw: real(log=_NoAppend(str(log)), **kw)):
            self._spawn(paths, "after-failed-marker", threshold=1)
        self.assertEqual([(ln.get("hmac"), ln.get("hmac_error")) for ln in _log_lines(paths["log"])],
                         [(None, "chain_reset_marker_missing")])
        self.assertNotEqual(audit_hmac.read_prev_hmac(), audit_hmac.GENESIS_PREV)  # names the absent marker
        self.assertTrue(audit_hmac.rotation_manifest_path().is_file())  # the helper's fail-loud state stays

    def test_rotation_with_chain_disabled_writes_no_marker(self) -> None:
        paths = self._paths()
        with mock.patch.dict(os.environ, {"CEO_AUDIT_HMAC_DISABLE": "1"}):
            self._spawn(paths, "seed")
            self._spawn(paths, "after-rotation", threshold=1)
        self.assertEqual([(ln.get("action"), ln.get("hmac")) for ln in _log_lines(paths["log"])],
                         [("agent_spawn", None)])


@pytest.mark.serial
@unittest.skipUnless(os.name == "posix", "POSIX only (fcntl.flock)")
class TestParallelWritersChain(_ChainCase):
    """agent_spawn vs audit_emit writers (sync; spool + drains) on one log + lock. A lock-timeout
    drop (fail-open) is ACCOUNTED, never taken for the race; both kinds must interleave."""

    SPAWNS, EMITS, ITERATIONS = 4, 2, 12

    def _race(self, sync_mode: bool) -> None:
        ctx = multiprocessing.get_context("spawn")
        paths = self._paths()
        log, fallback = paths["log"], self._tmp_root / "fallback.log"
        importlib.import_module("_lib.audit_hmac").get_or_create_key()  # rc.1 cond. 68: mint once
        env = {"CEO_AUDIT_LOG_FALLBACK_PATH": str(fallback), "CEO_AUDIT_SYNC_MODE": "1"}
        with mock.patch.dict(os.environ, env):
            if not sync_mode:
                os.environ.pop("CEO_AUDIT_SYNC_MODE", None)
            barrier = ctx.Barrier(self.SPAWNS + self.EMITS + 1)
            kinds = ["spawn"] * self.SPAWNS + ["emit"] * self.EMITS
            procs = [ctx.Process(target=_race_writer,
                                 args=(k, w, self.ITERATIONS, str(log), barrier))
                     for w, k in enumerate(kinds)]
            for p in procs:
                p.start()
            try:
                barrier.wait(120)
                [p.join(180) for p in procs]
            finally:
                [p.terminate() for p in procs if p.is_alive()]
            self.assertEqual([p.exitcode for p in procs], [0] * len(procs))
            if not sync_mode:
                from _lib import spool_writer
                spool_writer.drain_now(force=True)
        lines = _log_lines(log)
        errs = Path(paths["err"]).read_text(encoding="utf-8") if Path(paths["err"]).exists() else ""
        dropped = sum(1 for e in errs.splitlines() if "lock timeout (stale?)" in e and "race-spawn-" in e)
        fell_back = sum(1 for e in fallback.read_text(encoding="utf-8").splitlines()
                        if "race-emit-" in e) if fallback.exists() else 0
        count = {k: sum(1 for ln in lines if ln.get("action") == k)
                 for k in ("agent_spawn", "debate_event")}
        self.assertEqual(count["agent_spawn"] + dropped, self.SPAWNS * self.ITERATIONS)
        self.assertEqual(count["debate_event"] + fell_back, self.EMITS * self.ITERATIONS)
        # vacuity guard: the TYPE alternates and comes back (A->B->A), not two blocks
        self.assertGreaterEqual(_kind_switches(lines), 2, msg="writer kinds not interleaved")
        self._assert_intact(log, len(lines))  # THE property

    def test_parallel_spawn_and_sync_emit_writers_keep_the_chain(self) -> None:
        self._race(sync_mode=True)

    def test_parallel_spawn_and_spool_emit_writers_keep_the_chain(self) -> None:
        self._race(sync_mode=False)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
