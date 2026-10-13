"""Check that parallel execution cannot turn missing or failed tests green."""
from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("replay_parallel", Path(__file__).with_name("replay-parallel.py"))
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class ReplayParallelTests(unittest.TestCase):
    def result(self, text, exit_code=0):
        return subprocess.CompletedProcess([], exit_code, text)

    def test_rejects_incomplete_and_incoherent_results(self):
        valid = "  ok   H.1\n== RESULT: PASS=1 FAIL=0 ==\nREPLAY-GROUP: core\n"
        self.assertEqual(adapter.checked_result("core", self.result(valid)), (1, 0))
        for text, code in [(valid, 9), (valid + valid, 0),
                           (valid.replace("core", "pin"), 0),
                           (valid.replace("PASS=1", "PASS=2"), 0),
                           ("  ok   H.1\n", 0)]:
            with self.subTest(text=text, code=code), self.assertRaises(ValueError):
                adapter.checked_result("core", self.result(text, code))

    def test_failure_is_preserved(self):
        failed = "  FAIL H.1\n== RESULT: PASS=0 FAIL=1 ==\nREPLAY-GROUP: core\n"
        self.assertEqual(adapter.checked_result("core", self.result(failed, 1)), (0, 1))
        with self.assertRaises(ValueError):
            adapter.checked_result("core", self.result(failed, 0))

    def test_all_groups_execute_once_and_missing_assertions_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp) / "fixture.sh"
            script = '''#!/bin/bash
if [ "$1" = --list-groups ]; then printf 'first\nsecond\n'; exit; fi
printf '%s\n' "$2" >> "$(dirname "$0")/executed"
for ((i=0;i<36;i++)); do echo '  ok   H.test'; done
if [ "$2" = first ]; then
  echo '  ok   H.extra'; echo '== RESULT: PASS=37 FAIL=0 =='
else
  echo '== RESULT: PASS=36 FAIL=0 =='
fi
echo "REPLAY-GROUP: $2"
'''
            harness.write_text(script)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(adapter.execute(harness, 2, 10), 0)
            self.assertCountEqual((Path(tmp) / "executed").read_text().splitlines(), ["first", "second"])
            harness.write_text(script.replace('first\nsecond', 'first'))
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
                adapter.execute(harness, 2, 10)

    def test_duplicate_group_inventory_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp) / "fixture.sh"
            harness.write_text("printf 'core\\ncore\\n'\n")
            with self.assertRaises(ValueError):
                adapter.execute(harness, 2, 10)


if __name__ == "__main__":
    unittest.main()
