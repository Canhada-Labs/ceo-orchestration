"""Tests for check-audit-real-loss.py (PLAN-194 W2 / ADR-055-AMEND-4 §8.2 G6, G7).

Selectors: ``-k loss_verifier`` (G6) and ``-k would_log_count`` (G7). Every tree
is a disposable tmp dir. The G7 positive control drives the REAL producers: the
``audit_log.append_entry`` lock-timeout breadcrumb and ``spool_writer``'s stamp.
"""

from __future__ import annotations

import contextlib
import importlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "check-audit-real-loss.py"
for _p in (REPO_ROOT / ".claude" / "hooks", REPO_ROOT / ".claude" / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from _lib.testing import TestEnvContext  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rl = _load("check_audit_real_loss", SCRIPT)
ss = rl.ss
_shared = _load("_audit_spool_state_tests", Path(__file__).resolve().parent / "test_audit_spool_state.py")
RO_WRAPPER, _Tree, _Vanishing = _shared.RO_WRAPPER, _shared._Tree, _shared._Vanishing
_StreamOnly = _shared._StreamOnly
PID = 2_100_000_000


def _rid() -> str:
    return uuid.uuid4().hex


class TestLossVerifierG6(_Tree):
    def journal(self, envs, name: str = "audit-pending.%d.journal" % PID) -> None:
        self.touch(name, "".join(json.dumps(e) + "\n" for e in envs).encode())

    def commit(self, rid, age_s: float = 60.0, op: str = "commit"):
        return {"record_id": rid, "op": op, "wall_ns": self.now_ns - int(age_s * 1e9)}

    def g6(self, since_age_s: float = 3600.0):
        fam, st = ss.ReadOnlyDir(self.fam), ss.ReadOnlyDir(self.state)
        try:
            return rl.g6(fam, st, self.now_ns - int(since_age_s * 1e9))
        finally:
            fam.close()
            st.close()

    def test_loss_verifier_removed_canonical_line_is_loss_quarantine_and_spool_are_not(self) -> None:
        a, b, c = _rid(), _rid(), _rid()
        self.journal([self.commit(a, op="begin"), self.commit(a), self.commit(b), self.commit(c)])
        self.log([{"record_id": a, "_drain_epoch": "0a1b2c3d"}, {"record_id": b}])
        rep = self.g6()
        self.assertEqual((rep["commits"], rep["lost"], rep["lost_record_ids"]), (3, 1, [c]))
        self.touch("audit-spool.%d.malformed.0a1b2c3d" % PID, b'{"record_id":"%s", BROKEN\n' % c.encode())
        rep = self.g6()
        self.assertEqual((rep["lost"], rep["quarantined"], rep["pending"]), (0, 1, 0))
        os.rename(str(self.state / ("audit-spool.%d.malformed.0a1b2c3d" % PID)),
                  str(self.state / ("audit-spool.%d.jsonl" % PID)))
        rep = self.g6()
        self.assertEqual((rep["lost"], rep["quarantined"], rep["pending"]), (0, 0, 1))

    def test_loss_verifier_window_aggregate_rotated_and_top_level_only(self) -> None:
        old, agg, rot, nested, ok = _rid(), _rid(), _rid(), _rid(), _rid()
        self.journal([self.commit(old, age_s=7200), self.commit(nested), self.commit(ok)])
        self.journal([self.commit(agg)], name="audit-pending.journal")
        self.touch("audit-pending.%d.journal" % (PID + 1), b"not json\n")
        self.journal([self.commit(rot)], name="audit-pending.%d.journal" % (PID + 2))
        self.log([{"record_id": ok}, {"action": "x", "payload": {"record_id": nested}}])
        self.log([{"record_id": rot}], "audit-log-2026-10-3.jsonl")
        rep = self.g6()
        self.assertEqual(rep["commits"], 4)  # old is before since
        self.assertEqual(sorted(rep["lost_record_ids"]), sorted([agg, nested]))
        self.assertEqual(rep["journal_malformed_lines"], 1)

    def test_loss_verifier_second_pass_rechecks_a_record_in_transit(self) -> None:
        rid = _rid()
        self.journal([self.commit(rid)])
        empty = {"pending": set(), "quarantined": set(), "logged": set(), "unstable": set()}
        landed = dict(empty, logged={rid})
        with mock.patch.object(rl, "snapshot", side_effect=[empty, landed]) as snap:
            rep = self.g6()
        self.assertEqual((rep["lost"], snap.call_count), (0, 2))
        with mock.patch.object(rl, "snapshot", side_effect=[empty, empty]):
            self.assertEqual(self.g6()["lost"], 1)

    def test_loss_verifier_a_rename_target_the_listing_missed_is_never_lost(self) -> None:
        rid = _rid()
        self.journal([self.commit(rid)])
        hidden = self.touch("audit-spool.%d.draining.0a1b2c3d" % PID,
                            json.dumps({"record_id": rid}).encode() + b"\n")

        class _ReaddirMiss(ss.ReadOnlyDir):
            calls = 0

            def names(self):  # call 1 = journals; then (listing, re-listing) per pass
                _ReaddirMiss.calls += 1
                out = super().names()
                return [n for n in out if n != hidden.name] if self.calls % 2 == 0 else out

        fam, st = ss.ReadOnlyDir(self.fam), _ReaddirMiss(self.state)
        try:
            rep = rl.g6(fam, st, self.now_ns - 3600 * 10 ** 9)
        finally:
            fam.close()
            st.close()
        self.assertEqual((rep["lost"], rep["inconclusive"], rep["unresolved"], rep["stable_passes"]),
                         (0, True, 1, 0))
        self.assertEqual((rep["passes"], rep["last_unstable"]), (rl.MAX_PASSES, [hidden.name]))

    def test_loss_verifier_archive_vanishing_mid_scan_never_counts_as_absence(self) -> None:
        rid = _rid()
        self.journal([self.commit(rid)])
        self.log([{"record_id": _rid()}])
        self.log([{"record_id": rid}], "audit-log-2026-10-3.jsonl")
        fam, st = _Vanishing(self.fam, ["audit-log-2026-10-3.jsonl"], times=2), ss.ReadOnlyDir(self.state)
        try:
            rep = rl.g6(fam, st, self.now_ns - 3600 * 10 ** 9)
        finally:
            fam.close()
            st.close()
        self.assertEqual((rep["lost"], rep["inconclusive"], rep["passes"], rep["stable_passes"]),
                         (0, False, 3, 1))

    def test_loss_verifier_truncated_commit_raises_attention_not_the_exit(self) -> None:
        ok = _rid()
        self.journal([self.commit(ok)])
        self.touch("audit-pending.%d.journal" % (PID + 1),
                   json.dumps(self.commit(_rid())).encode()[:-9])  # cut mid-envelope, no newline
        self.log([{"record_id": ok}])
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(self.home_dir),
               "CLAUDE_PROJECT_DIR_NATIVE": str(self.fam)}
        out = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(out):
            rc = rl.main(["--g6", "--since", "2026-10-01T00:00:00Z"])
        rep = json.loads(out.getvalue())
        self.assertEqual((rc, rep["g6"]["lost"], rep["g6"]["journal_malformed_lines"]), (0, 0, 1))
        self.assertEqual(rep["attention"], ["g6_journal_malformed_lines"])

    def test_loss_verifier_streams_lines_and_never_reads_a_whole_file(self) -> None:
        a, b = _rid(), _rid()
        self.journal([self.commit(a), self.commit(b)])
        self.touch("audit-spool.%d.malformed.0a1b2c3d" % PID, b'{"record_id":"%s", BROKEN\n' % b.encode())
        self.log([{"record_id": _rid()}, {"record_id": a}])
        _StreamOnly.opened = 0
        fam, st = _StreamOnly(self.fam), _StreamOnly(self.state)
        try:
            rep = rl.g6(fam, st, self.now_ns - 3600 * 10 ** 9)
        finally:
            fam.close()
            st.close()
        self.assertEqual((rep["lost"], rep["quarantined"], rep["commits"]), (0, 1, 2))
        self.assertGreaterEqual(_StreamOnly.opened, 3)  # journal + quarantine + log

    def test_loss_verifier_inconclusive_exits_2_and_a_real_red_wins(self) -> None:
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(self.home_dir),
               "CLAUDE_PROJECT_DIR_NATIVE": str(self.fam)}
        argv = ["--since", "2026-10-02T00:00:00Z"]
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(rl, "g6", return_value={"lost": 0, "inconclusive": True}):
            self.assertEqual(rl.main(argv), 2)
            with mock.patch.object(rl, "g7", return_value={"G7": 1}):
                self.assertEqual(rl.main(argv), 1)

    def test_loss_verifier_cli_exit_codes_under_read_only_audit_hook(self) -> None:
        rid = _rid()
        self.journal([self.commit(rid)])
        self.log([{"record_id": _rid()}])
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.home_dir),
               "CLAUDE_PROJECT_DIR_NATIVE": str(self.fam), "PYTHONDONTWRITEBYTECODE": "1"}
        since = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        argv = [sys.executable, "-c", RO_WRAPPER, str(SCRIPT), "--since", since]
        res = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(res.returncode, 1, msg=res.stderr)
        self.assertIn("ro-events-checked", res.stderr)
        out = json.loads(res.stdout)
        self.assertEqual((out["g6"]["lost_record_ids"], out["g7"]["G7"]), ([rid], 0))
        res = subprocess.run(argv[:-1] + ["2026-10-02T03:40:00"], env=env, capture_output=True,
                             text=True, timeout=120)
        self.assertEqual((res.returncode, res.stdout), (2, ""), msg=res.stderr)


class TestLossVerifierRealRenames(TestEnvContext):
    """P1 (rail r1): the REAL drain rename (active -> .draining) and the REAL
    quarantine (.draining -> .malformed) land between G6's listing and its read.

    The producers keep per-PROCESS state (journal buffer, header cache, ordinal)
    that an earlier test of the same process can leave behind: ``_reset_caches_for_test``
    drops the state-dir cache, so the project-switch flush never runs, and a
    leftover ``commit`` of that test is flushed into THIS tree (CI run 37079951247:
    4 commits, 3 "lost"). Each case runs with that state emptied and restores it."""

    def _producer_state(self, sw):
        stack = contextlib.ExitStack()
        for cache in (sw._JOURNAL_BUFFER, sw._SPOOL_HEADER_CACHE, sw._ORDINAL_COUNTER):
            stack.enter_context(mock.patch.dict(cache, clear=True))
        stack.enter_context(mock.patch.object(sw, "_FORENSIC_EMIT", None))
        return stack

    def _race(self):
        from _lib import spool_writer as sw
        with self._producer_state(sw):
            sw.spool_append({"action": "g6_race", "session_id": "g6-race"})
            sw._flush_journal_buffer(os.getpid())
            state = sw._state_dir()
            active = "audit-spool.%d.jsonl" % os.getpid()
            moved = []

            class _Racing(ss.ReadOnlyDir):
                def lstat(self, name):  # the barrier: the producer acts after the listing
                    if name == active and not moved:
                        moved.extend(sw._phase2_sweep_and_rename(state, "0a1b2c3d", os.getpid())[0])
                    elif name.endswith(".draining.0a1b2c3d") and len(moved) == 1:
                        sw._quarantine(moved[0], "g6_race_test", "0e0f0a0b")
                        moved.append(None)
                    return super().lstat(name)

            fam, st = ss.ReadOnlyDir(self.audit_dir), _Racing(state)
            try:
                rep = rl.g6(fam, st, time.time_ns() - 3600 * 10 ** 9)
            finally:
                fam.close()
                st.close()
        self.assertEqual(len(moved), 2, msg="both real renames must fire mid-scan")
        self.assertTrue((state / ("audit-spool.%d.malformed.0e0f0a0b" % os.getpid())).is_file())
        self.assertEqual((rep["commits"], rep["lost"], rep["quarantined"], rep["inconclusive"]),
                         (1, 0, 1, False))
        self.assertEqual(rep["passes"], 3)

    def test_loss_verifier_real_drain_and_quarantine_renames_mid_scan(self) -> None:
        self._race()

    def test_loss_verifier_real_renames_after_a_test_that_left_producer_state(self) -> None:
        from _lib import spool_writer as sw
        other = self._tmp_root / "earlier-test-project"
        other.mkdir()
        # Cleared, so the dirt below is EXACTLY one begin/commit pair: 8+ envelopes left
        # by earlier tests would cross _JOURNAL_FLUSH_EVERY and flush it away. Restored
        # on exit: no leftover of OURS leaks on.
        with mock.patch.dict(sw._JOURNAL_BUFFER, clear=True), \
                mock.patch.dict(sw._SPOOL_HEADER_CACHE, clear=True), \
                mock.patch.dict(sw._ORDINAL_COUNTER, clear=True):
            with mock.patch.dict(os.environ, {"CEO_AUDIT_LOG_DIR": str(other)}), \
                    mock.patch.object(sw, "_FORENSIC_EMIT", None):
                sw._reset_caches_for_test()
                sw.spool_append({"action": "leftover", "session_id": "earlier-test"})  # never flushed
            sw._reset_caches_for_test()  # what TestEnvContext.setUp does between two tests
            leftover = [json.loads(b)["op"] for b in sw._JOURNAL_BUFFER.get(os.getpid(), [])]
            self.assertIn("commit", leftover, msg="the dirty state this control needs")
            self._race()


class TestWouldLogCountG7(TestEnvContext):
    def count(self, since: datetime):
        d = _StreamOnly(self.audit_dir)  # the errors file is streamed too
        try:
            return rl.g7(d, since)
        finally:
            d.close()

    def test_would_log_count_real_append_entry_lock_timeout_is_g7_1(self) -> None:
        audit_log = importlib.import_module("audit_log")
        paths = audit_log.audit_paths()
        self.assertEqual(Path(paths["err"]), self.audit_dir / rl.ERRORS_FILE)
        since = datetime.now(timezone.utc) - timedelta(seconds=5)

        # type-ignore: audit_log is imported by name at run time, so a checker sees no FileLock.
        class _TimesOut(audit_log.FileLock):  # type: ignore[misc, name-defined]
            def __enter__(self):
                raise audit_log.FileLockTimeout("held past 2.5 s (test)")

        self.assertEqual(self.count(since)["G7"], 0)
        with mock.patch.object(audit_log, "FileLock", _TimesOut):
            audit_log.append_entry({"action": "agent_spawn", "session_id": "g7-control"},
                                   paths=paths, threshold_bytes=10 ** 9)
        rep = self.count(since)
        self.assertEqual((rep["G7"], rep["g7_would_log"]), (1, 1))
        self.assertEqual(self.count(since + timedelta(hours=1))["G7"], 0)

    def test_would_log_count_both_stamps_and_starved_are_not_g7(self) -> None:
        from _lib import spool_writer
        # PLAN-194 W2.1: typed text of ADR-055-AMEND-4 §4.3; W2.1 ships the producer and
        # this line then drives it instead of typing the message.
        spool_writer._breadcrumb("drain canonical lock STARVED (exit): canonical log idle > "
                                 "3600s while exit drain timed out on the lock")
        spool_writer._breadcrumb("drain canonical lock STARVED: own spool stale past trigger")
        spool_writer._breadcrumb("drain canonical lock timeout (stale?)")
        spool_writer._breadcrumb("spool append failed: OSError: x")
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(self.audit_dir / rl.ERRORS_FILE, "a", encoding="utf-8") as fh:
            fh.write("[2026-10-01T23:48:41Z] lock timeout (stale?)  would-log={}\n")
            fh.write("[%s] append failed: [Errno 28] No space left  line={}\n" % now)
            fh.write("[%s] lock timeout (stale?)  would-log={\"action\":\"agent_spawn\"}\n" % now)
            fh.write("[2026-13-45T25:00:00Z] append failed: impossible date\n")
            fh.write("%s spool_writer: lock timeout (stale?)  would-log=wrong source\n" % now)
            fh.write("  continuation without a stamp\n")
            fh.write("%s audit_emit: spool_append silent drop; falling back to sync\n" % now)
            fh.write("%s check_budget: drain canonical lock timeout (other writer)\n" % now)
        rep = self.count(datetime.now(timezone.utc) - timedelta(minutes=5))
        self.assertEqual({k: rep[k] for k in ("G7", "g7_would_log", "g7_append_failed",
                                              "g8_starved_exit", "starved_opportunistic",
                                              "g2_canonical_lock_timeout", "unparsed",
                                              "lines_in_window")},
                         {"G7": 2, "g7_would_log": 1, "g7_append_failed": 1, "g8_starved_exit": 1,
                          "starved_opportunistic": 1, "g2_canonical_lock_timeout": 1,
                          "unparsed": 2, "lines_in_window": 9})
        self.assertEqual(self.count(datetime(2026, 10, 1, tzinfo=timezone.utc))["G7"], 3)

    def test_would_log_count_compares_utc_instants_not_text(self) -> None:
        (self.audit_dir / rl.ERRORS_FILE).write_text(
            "[2026-10-02T03:40:00Z] lock timeout (stale?)  would-log={}\n", encoding="utf-8")
        same_instant = ss.parse_iso_utc("2026-10-02T00:40:00-03:00")
        self.assertEqual(self.count(same_instant)["G7"], 1)
        self.assertEqual(self.count(same_instant + timedelta(milliseconds=500))["G7"], 0)
