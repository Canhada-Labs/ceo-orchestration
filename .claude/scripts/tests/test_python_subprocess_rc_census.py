"""PLAN-194 item 9: Python exit contracts and a ratchet over direct call sites."""
from __future__ import annotations

import json
import signal
from pathlib import Path

from _lib.testing import TestEnvContext
from _subprocess_census import baseline_rows, load_baseline, new_findings, scan_source, scan_tree
from _subprocess_helpers import run_python

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / ".claude/scripts/check-subprocess-tests.py"
BASELINE = ROOT / ".claude/scripts/subprocess-test-baseline.json"


class PythonSubprocessContract(TestEnvContext):
    def test_fu144_checks_returncode_in_every_mode(self):
        for mode in ("exit", "drain"):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(AssertionError, "returncode=7, expected=0"):
                    run_python(["-c", "import sys; print(sys.argv[1]); sys.exit(7)", mode])

    def test_fu144_fatal_stderr_is_never_expected_success(self):
        for text in (True, False):
            with self.subTest(text=text):
                with self.assertRaisesRegex(AssertionError, "Python fatal error"):
                    run_python(
                        ["-c", "import sys; sys.stderr.write('Fatal Python error: probe'); sys.exit(7)"],
                        expected_returncode=7, text=text,
                    )

    def test_fu144_expected_signal_and_output_remain_observable(self):
        result = run_python(["-c", "import sys; print('payload'); sys.stderr.write('diagnostic'); sys.exit(3)"],
                            expected_returncode=3)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (3, "payload\n", "diagnostic"))
        result = run_python(["-c", "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"],
                            expected_returncode=-signal.SIGTERM)
        self.assertEqual(result.returncode, -signal.SIGTERM)

    def test_fu144_census_aliases_and_command_bindings(self):
        source = """import subprocess as sp
from sys import executable as python
from subprocess import Popen as launch
def missing():
    cmd = [python, '-c', 'pass']
    result = sp.run(cmd)
    print(result.returncode)
def popen():
    with launch([python, '-c', 'pass']) as process:
        process.communicate()
def checked():
    result = sp.run([python, '-c', 'pass'])
    assert result.returncode == 0
def unrelated():
    assert result.returncode == 0
"""
        rows = scan_source(source)
        self.assertEqual([(r.kind, r.scope) for r in rows], [
            ("python-rc", "<module>.missing"), ("python-rc", "<module>.popen"),
        ])

    def test_fu144_rc_assertions_bind_to_the_actual_result(self):
        source = """import subprocess, sys
class Tests:
    def direct(self):
        self.assertEqual(subprocess.run([sys.executable]).returncode, 0)
    def checked(self):
        with subprocess.Popen([sys.executable]) as p:
            p.communicate()
            self.assertEqual(p.returncode, 0)
    def replaced(self):
        result = subprocess.run([sys.executable])
        result = subprocess.run(['echo', 'ok'])
        assert result.returncode == 0
    def stale(self):
        assert result.returncode == 0
        result = subprocess.run([sys.executable])
"""
        self.assertEqual([r.scope for r in scan_source(source)], ["<module>.Tests.replaced", "<module>.Tests.stale"])

    def test_fu144_ratchet_tracks_sites_not_total_or_line_numbers(self):
        source = "import subprocess, sys\ndef test_case():\n    subprocess.run([sys.executable, '-c', 'pass'])\n"
        rows = scan_source(source)
        baseline = baseline_rows(rows)
        self.assertEqual(new_findings(scan_source("\n\n" + source), baseline), [])
        self.assertEqual(new_findings([], baseline), [])
        self.assertEqual(len(new_findings(scan_source(source.replace("'pass'", "'print(1)'")), baseline)), 1)
        duplicate = source + "    subprocess.run([sys.executable, '-c', 'pass'])\n"
        self.assertEqual(len(new_findings(scan_source(duplicate), baseline)), 1)

    def test_fu144_repository_python_rc_ratchet(self):
        rows = [r for r in scan_tree(ROOT) if r.kind == "python-rc"]
        additions = new_findings(rows, load_baseline(BASELINE))
        self.assertEqual(additions, [], additions)

    def test_fu144_census_includes_imported_helpers(self):
        tests = self.project_dir / ".claude/scripts/tests"
        tests.mkdir(parents=True)
        source = "import sys, subprocess\nsubprocess.run([sys.executable], timeout=1)\n"
        (tests / "_imported_cases.py").write_text(source, encoding="utf-8")
        (tests / "_subprocess_helpers.py").write_text(source, encoding="utf-8")
        rows = scan_tree(self.project_dir)
        self.assertEqual([r.kind for r in rows], ["python-rc", "timeout-group"])
        self.assertEqual({r.path for r in rows}, {".claude/scripts/tests/_imported_cases.py"})

    def test_fu144_cli_fails_closed_on_unparseable_test(self):
        tests = self.project_dir / ".claude/scripts/tests"
        tests.mkdir(parents=True)
        (tests / "test_broken.py").write_text("def broken(:", encoding="utf-8")
        result = run_python([str(SCRIPT), "--root", str(self.project_dir)], expected_returncode=2)
        self.assertIn("SyntaxError", result.stderr)
        self.assertNotIn("0 new sites", result.stdout)

    def test_fu144_cli_emits_and_rejects_new_sites(self):
        tests = self.project_dir / ".claude/scripts/tests"
        tests.mkdir(parents=True)
        (tests / "test_new.py").write_text("import sys, subprocess\nsubprocess.run([sys.executable])\n", encoding="utf-8")
        result = run_python([str(SCRIPT), "--root", str(self.project_dir), "--list"], expected_returncode=1)
        rows = json.loads(result.stdout)
        self.assertEqual([(r["kind"], r["line"]) for r in rows], [("python-rc", 2)])
        self.assertIn("NEW python-rc", result.stderr)
