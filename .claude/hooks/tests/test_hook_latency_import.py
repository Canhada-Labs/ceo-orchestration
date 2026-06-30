"""Deterministic import-cost regression guard for check_agent_spawn.

This test is a companion to test_hook_latency.py but is NOT advisory —
it asserts an **in-process, load-independent** property: that importing
`_lib.adapters` (the hook's adapter dependency) does NOT eagerly pull
in `ssl`, `socket`, or `urllib.request`.

## Why this is hard (not advisory)

test_hook_latency.py carries xfail(strict=False) because wall-clock
subprocess timing is noisy under parallel CI load (4000+ test suite +
forkserver workers exhaust CPU). This test avoids that problem entirely:
it measures which modules are **imported** as a side-effect of importing
`_lib.adapters`, which is deterministic and load-independent.

## Regression being guarded

PLAN-120 WS-J diagnosed: `_lib/adapters/__init__.py` previously imported
`BatchClaudeLiveAdapter` eagerly at module level, which triggered the
`live/__init__.py` → `_transport.py` chain that imports `ssl`, `socket`,
and `urllib.request`. These stdlib modules add ~32ms to every hook
subprocess startup on top of the ~12ms python3 floor (~44ms total
live-pkg tax). The April-2026 check_agent_spawn p99 baseline was 43.9ms;
after the eager live import landed, p99 regressed to ~99ms.

Fix: `_lib/adapters/__init__.py` now defers `BatchClaudeLiveAdapter`
behind a `__getattr__` lazy accessor. This test verifies the fix holds.

## Method

Run in a subprocess that imports `_lib.adapters` and then prints the
names of any `ssl`/`socket`/`urllib.request`/`http.client` modules
found in `sys.modules`. Pass = none of those appear. The subprocess
isolation ensures `sys.modules` state from the test runner (which does
have ssl loaded) doesn't mask a regression.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import pytest

from _lib.testing import TestEnvContext  # noqa: E402

HOOKS_DIR = Path(__file__).resolve().parent.parent

# Modules whose presence in sys.modules after `import _lib.adapters`
# indicates an eager live-transport pull-in (= regression).
_LIVE_TRANSPORT_SENTINELS = (
    "ssl",
    "socket",
    "http",
    "http.client",
    "urllib.request",
    "urllib.error",
)


@unittest.skipUnless(os.name == "posix", "POSIX only (subprocess)")
class TestAdaptersImportCost(TestEnvContext):
    """Deterministic import-cost guard — no xfail, no advisory marker."""

    def test_adapters_import_does_not_pull_ssl_socket(self):
        """Importing _lib.adapters must NOT load ssl/socket/urllib.request.

        This is a hard regression guard for the PLAN-120 WS-J fix:
        _lib/adapters/__init__.py must NOT eagerly import BatchClaudeLiveAdapter
        (which chains through live/__init__.py -> _transport.py -> ssl/socket).

        Methodology: fresh subprocess; import _lib.adapters; print sys.modules keys
        that match the sentinel list; assert the printed list is empty.
        """
        # Probe script: snapshot sys.modules BEFORE importing _lib.adapters, then
        # flag ONLY the sentinels that import newly added. This isolates the
        # import-cost of _lib.adapters from whatever the interpreter pre-loaded
        # at startup (sitecustomize / coverage's subprocess auto-start), so the
        # guard measures the production import — not the measurement harness.
        sentinels_repr = repr(list(_LIVE_TRANSPORT_SENTINELS))
        script = (
            "import sys, json\n"
            "_before = set(sys.modules)\n"
            f"sys.path.insert(0, {str(HOOKS_DIR)!r})\n"
            "import _lib.adapters\n"
            f"sentinels = {sentinels_repr}\n"
            "leaked = sorted(m for m in sys.modules if m not in _before and "
            "any(m == s or m.startswith(s + '.') for s in sentinels))\n"
            "print(json.dumps(leaked))\n"
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = str(HOOKS_DIR)
        # The probe measures the PRODUCTION import cost (hooks never run under
        # coverage). Strip coverage's subprocess auto-start: under `coverage run`
        # the inherited COVERAGE_PROCESS_START makes sitecustomize start coverage
        # in this probe, and coverage's own machinery imports `socket`, which
        # would falsely trip the sentinel (pre-existing CI-red since ~S185).
        for _cov_var in (
            "COVERAGE_PROCESS_START", "COVERAGE_FILE", "COV_CORE_SOURCE",
            "COV_CORE_CONFIG", "COV_CORE_DATAFILE", "COV_CORE_CONTEXT",
        ):
            env.pop(_cov_var, None)
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        self.assertEqual(
            result.returncode, 0,
            f"import probe script failed: {result.stderr[:400]}",
        )
        try:
            leaked = json.loads(result.stdout.strip())
        except Exception as exc:  # noqa: BLE001
            self.fail(
                f"Could not parse probe output {result.stdout!r}: {exc}\n"
                f"stderr: {result.stderr[:400]}"
            )
        self.assertEqual(
            leaked,
            [],
            f"_lib.adapters import eagerly loaded live-transport modules {leaked}. "
            "This adds ~32ms to every hook subprocess invocation. "
            "Root cause: _lib/adapters/__init__.py re-imported BatchClaudeLiveAdapter "
            "at module level. Fix: keep it lazy via __getattr__. "
            "See PLAN-120 WS-J diagnosis.",
        )

    def test_adapters_lazy_accessor_returns_class_on_demand(self):
        """_get_batch_claude_live_adapter() returns the class when called.

        This verifies the lazy accessor itself is functional — importing
        _lib.adapters on demand via __getattr__ still resolves correctly.
        The test only runs if the live adapter package is importable.
        """
        script = (
            "import sys\n"
            f"sys.path.insert(0, {str(HOOKS_DIR)!r})\n"
            "import _lib.adapters as a\n"
            # Access via getattr triggers __getattr__ lazy load
            "cls = getattr(a, 'BatchClaudeLiveAdapter', None)\n"
            "if cls is None:\n"
            "    print('SKIP: live adapter unavailable')\n"
            "    sys.exit(0)\n"
            "assert hasattr(cls, 'call'), f'Expected .call on {cls}'\n"
            "print('OK: BatchClaudeLiveAdapter accessible on demand')\n"
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = str(HOOKS_DIR)
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        self.assertEqual(
            result.returncode, 0,
            f"lazy accessor probe failed: {result.stderr[:400]}",
        )
        self.assertIn(
            result.stdout.strip().split("\n")[-1] if result.stdout.strip() else "",
            (
                "OK: BatchClaudeLiveAdapter accessible on demand",
                "SKIP: live adapter unavailable",
            ),
            f"Unexpected output: {result.stdout!r}",
        )


if __name__ == "__main__":
    unittest.main()
