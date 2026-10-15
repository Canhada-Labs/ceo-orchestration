"""Check that parallel execution cannot turn missing or failed tests green."""
from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("historical_parallel", Path(__file__).with_name("historical-parallel.py"))
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class HistoricalParallelTests(unittest.TestCase):
    def result(self, text, exit_code=0):
        return subprocess.CompletedProcess([], exit_code, text)

    def test_rejects_incomplete_and_incoherent_results(self):
        valid = "  ok   H.1\nRESULT: 1 passed, 0 failed\nHISTORICAL-GROUP: core\n"
        self.assertEqual(adapter.checked_result("core", self.result(valid)), (1, 0))
        for text, code in [(valid, 9), (valid + valid, 0),
                           (valid.replace("core", "pin"), 0),
                           (valid.replace("1 passed", "2 passed"), 0),
                           ("  ok   H.1\n", 0)]:
            with self.subTest(text=text, code=code), self.assertRaises(ValueError):
                adapter.checked_result("core", self.result(text, code))

    def test_failure_is_preserved(self):
        failed = "  FAIL H.1\nRESULT: 0 passed, 1 failed\nHISTORICAL-GROUP: core\n"
        self.assertEqual(adapter.checked_result("core", self.result(failed, 1)), (0, 1))
        with self.assertRaises(ValueError):
            adapter.checked_result("core", self.result(failed, 0))

    def test_all_groups_execute_once_and_missing_assertions_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp) / "fixture.sh"
            # The two fake groups split the adapter's own total, so the
            # complete inventory passes and losing either group cannot.
            first = adapter.EXPECTED_ASSERTIONS // 2
            script = '''#!/bin/bash
if [ "$1" = --list-groups ]; then printf 'first\nsecond\n'; exit; fi
printf '%s\n' "$2" >> "$(dirname "$0")/executed"
case "$2" in first) n=@FIRST@;; *) n=@SECOND@;; esac
for ((i=0;i<n;i++)); do echo '  ok   H.test'; done
echo "RESULT: $n passed, 0 failed"
echo "HISTORICAL-GROUP: $2"
'''.replace("@FIRST@", str(first)).replace("@SECOND@", str(adapter.EXPECTED_ASSERTIONS - first))
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

    def test_real_harness_lists_the_c9_groups(self):
        # The fake harness above splits whatever total the adapter holds, so
        # dropping a group and lowering the total in one line would stay green
        # there. The C9 legs (PLAN-183) are named here, from the real inventory.
        harness = Path(__file__).with_name("test-upgrade-historical-adopter.sh")
        listed = subprocess.run(["bash", str(harness), "--list-groups"],
                                check=True, capture_output=True, text=True, timeout=30)
        groups = listed.stdout.splitlines()
        for group in ("harness-upgrade", "harness-fresh", "harness-red"):
            self.assertIn(group, groups)


if __name__ == "__main__":
    unittest.main()
