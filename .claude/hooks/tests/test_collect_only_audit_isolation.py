"""S326 — collection-time audit isolation guard (anti-rot for a measured leak).

pytest never runs fixtures under ``--collect-only``. The suite-wide audit-dir
redirect (``_lib/test_isolation._ceo_audit_isolation_session``) is a session
fixture, while the conftest's IMPORT-time work only pops
``CLAUDE_PROJECT_DIR_NATIVE``. So a test module that reaches an audit emitter
at import time writes to the fallback ``$HOME/.claude/projects/<slug>`` — the
LIVE HMAC chain — on every collect, and the whole-dir override carrier cannot
redirect it (it was popped one step earlier).

Measured 2026-08-24 (S326 boot): ``test_policy_mutations._POLICY_BASELINES``
replayed the 82-row policy corpus at import → 124 signed, unattributable
(``session_id=''``) events per ``pytest --collect-only``; ``verify-counts.sh``
ran that collect before every commit → 19 runs / 2,356 links in 12 h = 79% of
the live segment. The S321 cure (``9de4efc``) only ever covered fixture time.

Two guards, ONE mechanism (a green negative is meaningful only because the
positive control proves the detector can go red):

- ``test_collecting_the_suite_writes_no_audit_lines`` — NEGATIVE, the class:
  collecting the configured testpaths under a throwaway HOME (no audit
  carriers, no harness signals — the exact shape ``verify-counts.sh`` runs in)
  writes ZERO audit-log lines under that HOME.
- ``test_positive_control_import_time_emitter_is_seen`` — the instrument: a
  synthetic module that calls the policy engine at import, collected the same
  way, DOES write lines under the throwaway HOME.

Both spawn a child pytest on purpose: collection-time import IS the mechanism
under test, and it cannot be reproduced in-process (the session fixture has
already run here).
"""
from __future__ import annotations

import os
import shutil
import site
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

_HOOKS_DIR = Path(__file__).resolve().parent.parent  # .claude/hooks
_REPO_ROOT = _HOOKS_DIR.parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import test_isolation  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402

_BASH_POLICY = _REPO_ROOT / ".claude" / "policies" / "bash-safety.policy.yaml"
_BASH_FIXTURES = (
    _REPO_ROOT / ".claude" / "policies" / "fixtures" / "bash-safety.fixtures.jsonl"
)
# Anti-vacuity floor for the negative guard: the configured testpaths collect
# far more than this; a child that silently collected nothing (pytest missing,
# import storm, wrong cwd) must NOT pass as "zero lines written".
_MIN_COLLECTED = 1000


def _audit_log_lines(home: Path) -> Dict[str, int]:
    """Every ``audit-log*.jsonl`` under ``home`` → line count (empty = none)."""
    out: Dict[str, int] = {}
    for p in home.rglob("audit-log*.jsonl"):
        with open(p, encoding="utf-8", errors="replace") as fh:
            out[str(p.relative_to(home))] = sum(1 for _ in fh)
    return out


class TestCollectOnlyAuditIsolation(TestEnvContext):
    """S326 — nothing that runs at collection time may reach the live chain."""

    def _throwaway_home(self) -> Path:
        home = Path(tempfile.mkdtemp(prefix="s326-home-"))
        self.addCleanup(shutil.rmtree, str(home), True)
        return home

    def _production_shape_env(self, home: Path) -> Dict[str, str]:
        """The env ``verify-counts.sh`` runs its collect in: no audit carriers,
        no test-harness signals, HOME = the throwaway tree. PYTHONUSERBASE is
        re-exported to the REAL user site so the child can import pytest
        (HOME redirect alone loses the user site — measured)."""
        drop = set(test_isolation.ALL_AUDIT_CARRIERS)
        drop.update(test_isolation.WHOLE_DIR_OVERRIDE_CARRIERS)
        drop.update((
            test_isolation.TEST_HARNESS_VAR,
            test_isolation.SYNC_MODE_VAR,
            test_isolation.LIVE_LOG_SNAPSHOT_VAR,
            "PYTEST_ADDOPTS",
        ))
        env = {
            k: v for k, v in os.environ.items()
            if k not in drop and not k.startswith("PYTEST_")
        }
        env["HOME"] = str(home)
        # TestEnvContext sandboxes CLAUDE_PROJECT_DIR; the collect must see the
        # real repo (that is where verify-counts.sh runs it).
        env["CLAUDE_PROJECT_DIR"] = str(_REPO_ROOT)
        env["PYTHONUSERBASE"] = os.environ.get("PYTHONUSERBASE") or site.getuserbase()
        return env

    def _collect(self, args: List[str], env: Dict[str, str], cwd: Path):
        return subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q",
             "-p", "no:cacheprovider", *args],
            cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=600,
        )

    def test_collecting_the_suite_writes_no_audit_lines(self):
        """NEGATIVE (the class): ``pytest --collect-only`` over the configured
        testpaths, in production shape, leaves the throwaway HOME free of any
        audit-log line. Anti-vacuity: the child must have collected ≥1000."""
        home = self._throwaway_home()
        res = self._collect([], self._production_shape_env(home), _REPO_ROOT)
        tail = "\n".join(res.stdout.splitlines()[-3:])
        self.assertEqual(res.returncode, 0, msg=f"child collect failed:\n{res.stderr[-800:]}\n{tail}")
        collected = 0
        for tok in tail.replace(",", " ").split():
            if tok.isdigit():
                collected = int(tok)
                break
        self.assertGreaterEqual(collected, _MIN_COLLECTED,
                                msg=f"vacuous collect ({collected}): {tail!r}")
        lines = _audit_log_lines(home)
        self.assertEqual(lines, {}, msg=(
            "collection-time code reached the audit emitter — these lines would "
            f"have landed in the LIVE chain on a real run: {lines}"
        ))

    def test_positive_control_import_time_emitter_is_seen(self):
        """POSITIVE CONTROL (the instrument): a module that calls
        ``policy.decide()`` at import — the exact mechanism of the S326 emitter —
        collected in the same production shape, DOES leave audit-log lines
        under the throwaway HOME."""
        home = self._throwaway_home()
        probe_dir = Path(tempfile.mkdtemp(prefix="s326-probe-"))
        self.addCleanup(shutil.rmtree, str(probe_dir), True)
        first_row = _BASH_FIXTURES.read_text(encoding="utf-8").splitlines()[0]
        (probe_dir / "test_s326_probe.py").write_text(
            "import json, sys\n"
            f"sys.path.insert(0, {str(_HOOKS_DIR)!r})\n"
            "from _lib import policy as _policy\n"
            f"_pol = _policy.load({str(_BASH_POLICY)!r})\n"
            f"_pol.decide(json.loads({first_row!r})['input'])  # import-time, on purpose\n"
            "\n\ndef test_probe():\n    assert True\n",
            encoding="utf-8",
        )
        res = self._collect(
            [f"--rootdir={probe_dir}", str(probe_dir / "test_s326_probe.py")],
            self._production_shape_env(home), probe_dir,
        )
        self.assertEqual(res.returncode, 0, msg=f"probe collect failed:\n{res.stderr[-800:]}")
        lines = _audit_log_lines(home)
        self.assertTrue(lines and sum(lines.values()) >= 1, msg=(
            "positive control is DEAD: an import-time policy.decide() left no "
            f"audit-log line under the throwaway HOME (found: {lines}); the "
            "negative guard above cannot be trusted"
        ))
