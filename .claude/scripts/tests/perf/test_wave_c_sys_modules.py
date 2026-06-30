"""PLAN-087 Wave C.2 microbench — ``check_read_injection`` sys.modules early-exit.

Baseline: ``importlib.util.spec_from_file_location`` + ``module_from_spec``
+ ``exec_module`` invoked on every Read hook call (pre-fix).

Post-fix: ``sys.modules.get("scan_injection_mod")`` early-exit skips
the import machinery when the module is already loaded.

ADVISORY MODE per perf-engineer Tier-3 ranking (handoff §10.2):

The hook normally runs as a subprocess (one process per Read tool
call); sys.modules resets between subprocess invocations and the
import is paid every time. The cache only materializes savings for
in-process callers (tests, library users). This test runs in-process
and measures the in-process path; the real-world subprocess
end-to-end timing benefit is approximately zero.

Methodology:

* ``timeit.repeat(number=200, repeat=30)`` — N=30 samples.
* Threshold ``0.80`` retained for documentation but the test runs in
  ``advisory=True`` mode — a miss prints the report without raising,
  so the CI gate stays green while we document the in-process delta.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from perf_utils import measure_relative, report_and_assert  # noqa: E402


_SCAN_SOURCE = '''
def scan_path(p):
    class _R:
        matched = False
    return _R()
'''


class WaveC2SysModulesEarlyExitMicrobench(unittest.TestCase):
    """In-process measurement of the sys.modules cache benefit."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._scan_path = Path(self._tmpdir.name) / "scan-injection.py"
        self._scan_path.write_text(_SCAN_SOURCE, encoding="utf-8")
        # Clear any prior fixture-state.
        sys.modules.pop("wave_c2_synthetic_mod", None)

    def tearDown(self) -> None:
        sys.modules.pop("wave_c2_synthetic_mod", None)
        self._tmpdir.cleanup()

    def test_p99_post_le_80pct_baseline_advisory(self) -> None:
        scan_path = self._scan_path

        def baseline() -> None:
            # Pre-fix: full import machinery every call.
            sys.modules.pop("wave_c2_synthetic_mod", None)
            spec = importlib.util.spec_from_file_location(
                "wave_c2_synthetic_mod", scan_path
            )
            mod = importlib.util.module_from_spec(spec)
            sys.modules["wave_c2_synthetic_mod"] = mod
            spec.loader.exec_module(mod)

        # Seed cache once for the post run.
        spec = importlib.util.spec_from_file_location(
            "wave_c2_synthetic_mod", scan_path
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["wave_c2_synthetic_mod"] = mod
        spec.loader.exec_module(mod)

        def post() -> None:
            # Post-fix: cache hit short-circuits the import machinery.
            mod_ref = sys.modules.get("wave_c2_synthetic_mod")
            if mod_ref is None:  # pragma: no cover (always hit in this test)
                spec_local = importlib.util.spec_from_file_location(
                    "wave_c2_synthetic_mod", scan_path
                )
                mod_ref = importlib.util.module_from_spec(spec_local)
                sys.modules["wave_c2_synthetic_mod"] = mod_ref
                spec_local.loader.exec_module(mod_ref)

        p50_b, p99_b, p50_p, p99_p = measure_relative(
            baseline, post, number=200, repeat=30
        )
        report = report_and_assert(
            "C.2-sys-modules-early-exit", p50_b, p99_b, p50_p, p99_p,
            threshold=0.80, advisory=True,
        )
        print(report)
        # No assertion on raw threshold; advisory output only.


if __name__ == "__main__":
    unittest.main()
