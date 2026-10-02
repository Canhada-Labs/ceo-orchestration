"""Tests for audit_spool_state.py (PLAN-194 W2 / ADR-055-AMEND-4 §4.8, §6.3, G3).

Selectors: ``-k flux`` (H1) and ``-k spool_residue`` (names, H2, H3, G3). Every
tree is a disposable tmp dir; dead PIDs are numbers no kernel hands out
(>= 2.1e9, past every pid_max), the live one is this process. The CLI test runs
the script under a Python audit hook that fails on ANY write-mode open or
filesystem mutation, so "read-only" is asserted, not assumed.
"""

from __future__ import annotations

import glob
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "audit_spool_state.py"
AMEND4 = ".claude/plans/PLAN-194/debate/round-2/ADR-055-AMEND-4-draft.md"
if str(REPO_ROOT / ".claude" / "hooks") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

_spec = importlib.util.spec_from_file_location("audit_spool_state", SCRIPT)
ss = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ss)

DEAD = 2_100_000_000
NS = 10 ** 9
# Runs a script with argv[1:], exiting 97 on any write-mode open or mutation.
RO_WRAPPER = r"""
import os, runpy, sys
sys.dont_write_bytecode = True
W = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
MUT = {"os.remove", "os.rename", "os.rmdir", "os.mkdir", "os.chmod", "os.chown", "os.utime",
       "os.truncate", "os.link", "os.symlink", "os.chflags", "os.setxattr", "os.removexattr",
       "shutil.rmtree", "shutil.move", "shutil.copyfile"}
bad = []
def hook(ev, a):
    if ev == "open" and isinstance(a[2], int) and a[2] & W:
        bad.append((ev, str(a[0])))
    elif ev in MUT:
        bad.append((ev, repr(a)[:200]))
sys.addaudithook(hook)
sys.argv = sys.argv[1:]
try:
    runpy.run_path(sys.argv[0], run_name="__main__")
    code = 0
except SystemExit as e:
    code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
if bad:
    sys.stderr.write("READ-ONLY VIOLATION %r\n" % bad)
    code = 97
sys.stderr.write("ro-events-checked\n")
sys.exit(code)
"""


class _Tree(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        self.fam = self._tmp_root / "fam"
        self.state = self.fam / "state"
        self.state.mkdir(parents=True, mode=0o700)
        self.now_ns = time.time_ns()

    def touch(self, name: str, data: bytes = b"", age_s: float = 0.0) -> Path:
        p = self.state / name
        p.write_bytes(data)
        t = (self.now_ns - int(age_s * NS)) / NS
        os.utime(p, (t, t))
        return p

    def log(self, entries, name: str = "audit-log.jsonl") -> Path:
        p = self.fam / name
        p.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
        return p

    def era(self, pid, age_s: float = 60.0, **extra):
        e = {"_drain_epoch": "0a1b2c3d", "pid": pid, "wall_ns": self.now_ns - int(age_s * NS)}
        e.update(extra)
        return e

    def flux(self, since_age_s: float = 3600.0, **kw):
        fam, st = ss.ReadOnlyDir(self.fam), ss.ReadOnlyDir(self.state)
        try:
            return ss.flux(fam, st, self.now_ns - int(since_age_s * NS), self.now_ns + NS,
                           kw.pop("d_min", 200), 0.01, **kw)
        finally:
            fam.close()
            st.close()

    def residue(self, **kw):
        st = ss.ReadOnlyDir(self.state)
        try:
            return ss.residue(st, self.now_ns, 24.0, 1000, 100000, **kw)
        finally:
            st.close()


class TestSpoolResidueNames(TestEnvContext):
    def test_spool_residue_regex_block_is_the_amendment_text(self) -> None:
        block = "\n".join(ln for ln in SCRIPT.read_text(encoding="utf-8").splitlines()
                          if ln.startswith("RE_"))
        self.assertEqual(block.count("\n"), 4)
        docs = glob.glob(str(REPO_ROOT / ".claude/adr/ADR-055-AMEND-4*.md")) + [str(REPO_ROOT / AMEND4)]
        texts = [Path(d).read_text(encoding="utf-8") for d in docs if Path(d).is_file()]
        self.assertTrue(any(block in t for t in texts), msg="RE_* drifted from ADR-055-AMEND-4 §4.8")

    def test_spool_residue_fullmatch_ascii_names(self) -> None:
        good = {"audit-spool.1.jsonl.lock": ("spool_lock", 1),
                "audit-pending.4294967295.journal": ("journal", 4294967295),
                "audit-pending.77.journal.lock": ("journal_lock", 77),
                "audit-spool.9.draining.0a1b2c3d": ("draining", 9),
                "audit-spool.12.jsonl": ("active_spool", 12)}
        for name, want in good.items():
            self.assertEqual(ss.classify(name), want, msg=name)
        for name in ("audit-pending.0123.journal", "audit-pending.12a.journal",
                     "audit-pending.1_0.journal", "audit-pending.+1.journal",
                     "audit-pending.١٢.journal", "audit-pending.1.journal\n",
                     "audit-pending.12345678901.journal", "audit-pending.journal",
                     "audit-pending.journal.aggregation.lock", "audit-spool.1.draining.0A1B2C3D",
                     "audit-spool.1.malformed.0a1b2c3d", "audit-pending.1.journal.compact.tmp",
                     "x-audit-spool.1.jsonl", "subagent-lifecycle.json.lock"):
            self.assertEqual(ss.classify(name), (None, None), msg=repr(name))

    def test_spool_residue_pid_liveness_and_iso(self) -> None:
        self.assertTrue(ss.pid_alive(os.getpid()))
        self.assertFalse(ss.pid_alive(DEAD))
        self.assertFalse(ss.pid_alive(9999999999))  # 10 digits: overflows pid_t
        a = ss.parse_iso_utc("2026-10-02T03:40:00Z")
        self.assertEqual(a, ss.parse_iso_utc("2026-10-02T00:40:00-03:00"))
        for bad in ("2026-10-02T03:40:00", "<LAND>", ""):
            with self.assertRaises(ValueError):
                ss.parse_iso_utc(bad)


class TestFluxH1(_Tree):
    def test_flux_positive_control_200_dead_pids_with_0_byte_journals(self) -> None:
        self.log([self.era(DEAD + i) for i in range(200)])
        for i in range(200):
            self.touch("audit-pending.%d.journal" % (DEAD + i))
        rep = self.flux()
        self.assertEqual((rep["D"], rep["F"], rep["red"]), (200, 1.0, True))

    def test_flux_green_when_no_journal_is_left_behind(self) -> None:
        self.log([self.era(DEAD + i) for i in range(200)])
        rep = self.flux()
        self.assertEqual((rep["D"], rep["F"], rep["red"]), (200, 0.0, False))
        self.assertEqual(rep["cells"]["dead_no_journal"], 200)

    def test_flux_below_d_min_is_red_even_with_f_zero(self) -> None:
        self.log([self.era(DEAD + i) for i in range(199)])
        rep = self.flux()
        self.assertEqual((rep["D"], rep["F"], rep["red"]), (199, 0.0, True))

    def test_flux_window_era_and_cells(self) -> None:
        live = os.getpid()
        self.log([self.era(DEAD + 1), self.era(DEAD + 1), self.era(DEAD + 2), self.era(DEAD + 3),
                  self.era(DEAD + 4), self.era(live), self.era(DEAD + 5, age_s=7200),
                  {"action": "agent_spawn", "pid": DEAD + 6, "wall_ns": self.now_ns},
                  self.era(True), self.era(DEAD + 7, wall_ns=str(self.now_ns))])
        self.touch("audit-pending.%d.journal" % (DEAD + 1))
        self.touch("audit-pending.%d.journal" % (DEAD + 2), b'{"op":"commit"}\n')
        self.touch("audit-pending.%d.journal" % (DEAD + 3), age_s=7200)
        self.touch("audit-pending.%d.journal" % live)
        self.touch("audit-pending.%d.journal" % (DEAD + 5))
        rep = self.flux(d_min=1)
        self.assertEqual(rep["D"], 5)  # DEAD+1..+4 and live; the rest are outside/not spool-era
        self.assertEqual(rep["cells"], {"alive": 1, "dead_zero_in_window": 1,
                                        "dead_zero_before_window": 1, "dead_with_content": 1,
                                        "dead_no_journal": 1})
        self.assertAlmostEqual(rep["F"], 0.2)

    def test_flux_reads_rotated_archives_listed_after_the_log(self) -> None:
        self.log([self.era(DEAD + 1)])
        self.log([self.era(DEAD + 2)], "audit-log-2026-10-3.jsonl")
        old = self.log([self.era(DEAD + 3)], "audit-log-2026-09.jsonl")
        t = (self.now_ns - 3 * 3600 * NS) / NS
        os.utime(old, (t, t))  # appended before since - 1 h: never read
        rep = self.flux(d_min=1)
        self.assertEqual((rep["D"], rep["logs"]["files_read"]), (2, 2))

    def test_flux_cli_red_under_read_only_audit_hook_and_refusal(self) -> None:
        self.log([self.era(DEAD + i) for i in range(200)])
        for i in range(200):
            self.touch("audit-pending.%d.journal" % (DEAD + i))
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.home_dir),
               "CLAUDE_PROJECT_DIR_NATIVE": str(self.fam), "PYTHONDONTWRITEBYTECODE": "1"}
        argv = [sys.executable, "-c", RO_WRAPPER, str(SCRIPT), "--flux", "--d-min", "200"]
        res = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(res.returncode, 1, msg=res.stderr)
        self.assertIn("ro-events-checked", res.stderr)
        self.assertEqual((json.loads(res.stdout)["D"], json.loads(res.stdout)["F"]), (200, 1.0))
        env["CEO_AUDIT_LOG_DIR"] = str(self.fam)
        res = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual((res.returncode, res.stdout), (2, ""), msg=res.stderr)


class TestSpoolResidue(_Tree):
    def test_spool_residue_h2_1001_zero_byte_journals_is_red(self) -> None:
        for i in range(1000):
            self.touch("audit-pending.%d.journal" % (DEAD + i))
        self.touch("audit-pending.%d.journal" % (DEAD + 5000), b"{}\n")
        rep = self.residue()
        self.assertEqual((rep["H2"], rep["red"]), (1000, False))
        self.touch("audit-pending.%d.journal" % (DEAD + 1000))
        rep = self.residue()
        self.assertEqual((rep["H2"], rep["red"], rep["counts"]["journal_content"]), (1001, True, 1))

    def test_spool_residue_h3_counts_locks_by_name_only(self) -> None:
        self.touch("audit-spool.%d.jsonl.lock" % DEAD)
        os.symlink("/nonexistent", str(self.state / ("audit-pending.%d.journal.lock" % DEAD)))
        self.touch("audit-pending.journal.aggregation.lock")
        rep = self.residue()
        self.assertEqual((rep["H3"], rep["recommend_w2_6"], rep["red"]), (2, False, False))

    def test_spool_residue_g3_draining_and_dead_orphan_older_than_24h(self) -> None:
        self.touch("audit-spool.%d.draining.0a1b2c3d" % DEAD, b"x\n", age_s=23 * 3600)
        self.touch("audit-spool.%d.jsonl" % (DEAD + 1), b"x\n", age_s=25 * 3600)
        self.touch("audit-spool.%d.jsonl" % (DEAD + 2), b"", age_s=25 * 3600)
        self.touch("audit-spool.%d.jsonl" % os.getpid(), b"x\n", age_s=25 * 3600)
        rep = self.residue()
        self.assertEqual((rep["G3"], rep["red"]), (["audit-spool.%d.jsonl" % (DEAD + 1)], True))
        self.assertEqual(rep["counts"]["orphan_spool_with_content"], 1)
        self.touch("audit-spool.%d.jsonl" % (DEAD + 1), b"x\n", age_s=60)
        self.touch("audit-spool.%d.draining.0a1b2c3d" % DEAD, b"x\n", age_s=25 * 3600)
        self.assertEqual(self.residue()["G3"], ["audit-spool.%d.draining.0a1b2c3d" % DEAD])
