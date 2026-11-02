"""PLAN-194 item 16: observe descendant death, including an exited shell leader."""
from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path
from unittest import mock

from _lib.testing import TestEnvContext
from _subprocess_census import baseline_rows, load_baseline, new_findings, scan_source, scan_tree
from _subprocess_helpers import run_in_process_group

ROOT = Path(__file__).resolve().parents[3]
BASELINE = ROOT / ".claude/scripts/subprocess-test-baseline.json"


def _running(pid):
    result = run_in_process_group(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True, timeout=5)
    return result.returncode == 0 and result.stdout.strip() and not result.stdout.lstrip().startswith("Z")


class SubprocessTimeoutContract(TestEnvContext):
    def test_fu144_timeout_kills_descendants_even_after_shell_exit(self):
        for tail in ("wait", "exit 0"):
            with self.subTest(tail=tail):
                pid_file = self.project_dir / "pids"
                pid_file.unlink(missing_ok=True)
                script = 'sleep 60 & child=$!; printf "%s %s\\n" "$$" "$child" > "$1"; ' + tail
                pids = []
                try:
                    with self.assertRaises(subprocess.TimeoutExpired):
                        run_in_process_group(["bash", "-c", script, "probe", str(pid_file)],
                                             capture_output=True, text=True, timeout=1)
                    pids = [int(value) for value in pid_file.read_text().split()]
                    deadline = time.monotonic() + 5
                    while any(_running(pid) for pid in pids) and time.monotonic() < deadline:
                        time.sleep(0.02)
                    self.assertFalse(any(_running(pid) for pid in pids), f"surviving process: {pids}")
                finally:
                    if pid_file.exists():
                        pids = [int(value) for value in pid_file.read_text().split()]
                    for pid in pids:
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass

    def test_fu144_group_output_and_check_contract(self):
        result = run_in_process_group(["bash", "-c", "cat; printf diagnostic >&2; exit 3"],
                                      input="payload", capture_output=True, text=True, timeout=5)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (3, "payload", "diagnostic"))
        with self.assertRaises(subprocess.CalledProcessError) as error:
            run_in_process_group(["bash", "-c", "exit 3"], check=True, timeout=5)
        self.assertEqual(error.exception.returncode, 3)

    def test_fu144_session_override_is_rejected_before_launch(self):
        for option in ({"start_new_session": False}, {"preexec_fn": os.setsid}):
            with self.subTest(option=option):
                with mock.patch("_subprocess_helpers.subprocess.Popen") as launch:
                    with self.assertRaisesRegex(ValueError, "owns process-session"):
                        run_in_process_group(["bash", "-c", "exit"], timeout=5, **option)
                    launch.assert_not_called()

    def test_fu144_timeout_census_includes_aliases_and_communicate(self):
        source = """import subprocess as sp
from subprocess import run as launch
def raw():
    sp.run(['bash'], timeout=3)
    launch(['bash'], timeout=3, start_new_session=True)
    p = sp.Popen(['bash'])
    p.communicate(timeout=3)
    p.communicate(None, 3)
def safe():
    run_in_process_group(['bash'], timeout=3)
"""
        rows = scan_source(source)
        self.assertEqual([(r.kind, r.line) for r in rows], [("timeout-group", line) for line in (4, 5, 7, 8)])

    def test_fu144_timeout_ratchet_rejects_replacement_site(self):
        source = "import subprocess\nsubprocess.run(['bash', 'old.sh'], timeout=3)\n"
        baseline = baseline_rows(scan_source(source))
        self.assertEqual(new_findings(scan_source("\n" + source), baseline), [])
        self.assertEqual(len(new_findings(scan_source(source.replace("old.sh", "new.sh")), baseline)), 1)

    def test_fu144_installer_has_no_direct_timeout_sites(self):
        path = ROOT / ".claude/scripts/tests/test_install_sh_placeholders.py"
        self.assertEqual(scan_source(path.read_text(encoding="utf-8"), path.name), [])

    def test_fu144_repository_timeout_ratchet(self):
        rows = [r for r in scan_tree(ROOT) if r.kind == "timeout-group"]
        self.assertEqual(new_findings(rows, load_baseline(BASELINE)), [])
