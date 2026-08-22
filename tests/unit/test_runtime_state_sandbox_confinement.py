"""Runtime-state writes MUST stay inside the test sandbox — PLAN-182 W1 follow-up.

Why this file exists
--------------------
PLAN-182 W1 made runtime state resolve per project through the single resolver
``_lib.runtime_paths.runtime_state_dir()``. That resolver honours
``CLAUDE_PROJECT_DIR_NATIVE`` (the ADR-001 whole-directory override) at the
HIGHEST precedence — above the ``HOME`` the suite's isolation layer redirects.

Two enumerations exist to stop a test from resolving live state, and neither was
updated when W1 landed:

* ``_lib/test_isolation.AUDIT_DIR_CARRIERS`` — ``("HOME", "CEO_AUDIT_LOG_DIR",
  "CEO_PROJECT_STATE_DIR")``, documented as *"every env var that can steer WHERE
  an emit / HMAC sidecar / spool / lock / fallback resolves … the enumeration
  lives HERE, exactly once"*.
* the enumerated ``CEO_*`` delete list in ``_lib/testing.TestEnvContext``.

Measured consequence: a pytest run containing a SINGLE ``assert True``, with the
carrier present in the environment, created ``audit-log.lock`` and ``state/`` in
that external directory. The session-scoped isolation fixture materialises the
dirs before any test executes, so the escape needs no cooperation from the test
— four modules (``test_credential_rotation_emit``, ``test_runtime_paths``,
``test_injection_salt``, ``test_audit_family_two_projects``) were writing live
runtime state while reporting green.

What this guard asserts, and how
--------------------------------
The invariant is stated POSITIVELY (nothing lands outside the sandbox) and is
exercised through the REAL mechanism: a child ``pytest`` process is launched with
the carrier in its environment, and the canary directory is inspected afterwards.
Asserting on ``os.environ`` from inside an already-isolated test would only
re-check the isolation layer's bookkeeping, not whether a write escapes.

The child environment is deliberately STRIPPED of the ``CEO_AUDIT_*`` redirects
this parent test inherits from ``TestEnvContext``. Passing them down would point
the child's audit surface at the parent's tmpdir and the canary would come back
empty whether or not the cure exists — a vacuous pass. The child must start as a
developer's shell would, carrying only the carrier under test.

``test_debt_marker_carrier_absent_from_isolation_enumeration`` is deliberate: the
cure currently lives in the repo-root ``conftest.py`` (import time), because the
structural fix belongs in ``_lib/test_isolation.AUDIT_DIR_CARRIERS`` — a
canonical-guarded path that lands through the Owner's signed-edit ceremony. It
asserts on the enumeration itself, so it goes red the day that fix lands, which
is the signal to delete it along with the conftest line. An earlier draft shelled
out to a bare ``python -c`` instead; that bypasses pytest isolation entirely and
would have stayed green forever, promising a signal it could never send.

Discipline: stdlib-only, Python >= 3.9, ``from __future__ import annotations``,
``TestEnvContext`` for env isolation (the repo's hard-fail hygiene gate rejects a
bare ``unittest.TestCase`` under ``tests/``), realpath on BOTH sides of every
path assertion (``/tmp`` is a symlink to ``/private/tmp`` on macOS, so
``startswith`` on raw strings compares formatting, not containment), and a child
module path unique per worker+method so the ``-n auto`` pass cannot race.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib.testing import TestEnvContext  # noqa: E402

_NATIVE_VAR = "CLAUDE_PROJECT_DIR_NATIVE"
# Deliberately NOT prefixed CEO_/CLAUDE_ — those are steering keys the suite
# snapshots and strips, which would leave the control unable to see its target.
_CONTROL_VAR = "CONFINEMENT_CANARY_DIR"


def _real(p) -> str:
    """Realpath as a string — used on BOTH sides of every comparison."""
    return str(Path(p).resolve())


class TestRuntimeStateSandboxConfinement(TestEnvContext):
    """An ambient ``CLAUDE_PROJECT_DIR_NATIVE`` must not redirect suite writes."""

    def setUp(self) -> None:
        super().setUp()
        self._outside = Path(tempfile.mkdtemp(prefix="ceo-outside-canary-"))
        self.addCleanup(shutil.rmtree, self._outside, True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _write_child_test(self, body: str) -> Path:
        """Materialise a child test module inside the repo's test tree.

        It must live under the repo so the child run picks up the real
        ``conftest.py`` chain — that chain is the subject under test.

        The filename carries the xdist worker id AND a uuid: the unit suite
        runs ``-n auto``, and a fixed path would let two workers overwrite and
        unlink the same file while each other's child process is collecting it.
        """
        worker = os.environ.get("PYTEST_XDIST_WORKER", "solo")
        unique = "%s_%s" % (worker, uuid.uuid4().hex[:12])
        target = REPO_ROOT / "tests" / "unit" / ("test_zz_confinement_child_%s.py" % unique)
        target.write_text(textwrap.dedent(body), encoding="utf-8")
        self.addCleanup(lambda: target.unlink(missing_ok=True))
        return target

    def _run_child(self, target: Path) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        # Strip what TestEnvContext injected into THIS process. Handing the
        # parent's audit redirects to the child would confine it for the wrong
        # reason and make the canary assertion vacuous.
        for key in list(env):
            if key.startswith("CEO_AUDIT_") or key == "CEO_PROJECT_STATE_DIR":
                env.pop(key, None)
        env.pop("PYTEST_CURRENT_TEST", None)
        env.pop("PYTEST_XDIST_WORKER", None)
        env[_NATIVE_VAR] = str(self._outside)
        env[_CONTROL_VAR] = str(self._outside)
        return subprocess.run(
            [sys.executable, "-m", "pytest", str(target), "-q", "-p", "no:cacheprovider"],
            capture_output=True, text=True, timeout=300,
            cwd=str(REPO_ROOT), env=env,
        )

    def _canary_entries(self):
        return sorted(p.name for p in self._outside.iterdir())

    def _assert_child_ok(self, proc) -> None:
        self.assertEqual(
            proc.returncode, 0,
            "child pytest run failed:\n%s\n%s"
            % (proc.stdout[-2000:], proc.stderr[-2000:]),
        )

    # ------------------------------------------------------------------
    # The invariant
    # ------------------------------------------------------------------

    def test_ambient_carrier_does_not_redirect_runtime_state(self) -> None:
        """A child run with the carrier set must leave the canary empty.

        The child body is a bare ``assert True`` on purpose: the escape is
        driven by the session-scoped isolation fixture, not by anything the
        test does. Before the cure this failed with ``audit-log.lock`` and
        ``state/`` sitting in the canary.
        """
        proc = self._run_child(self._write_child_test(
            '''
            def test_trivial():
                assert True
            '''
        ))
        self._assert_child_ok(proc)
        self.assertEqual(
            self._canary_entries(), [],
            "ambient %s escaped the suite's isolation — runtime state was "
            "written into %s (entries: %s)"
            % (_NATIVE_VAR, self._outside, self._canary_entries()),
        )

    def test_control_canary_is_reachable_and_writable_by_the_child(self) -> None:
        """Control: the canary CAN receive files from the child process.

        Without this, the empty-canary assertion above would pass just as
        happily if the directory were unwritable, missing, or unreachable from
        the child — a dead assertion proving nothing.
        """
        proc = self._run_child(self._write_child_test(
            '''
            import os
            from pathlib import Path


            def test_write_to_canary():
                dest = Path(os.environ["CONFINEMENT_CANARY_DIR"])
                dest.mkdir(parents=True, exist_ok=True)
                (dest / "control.txt").write_text("x", encoding="utf-8")
            '''
        ))
        self._assert_child_ok(proc)
        self.assertEqual(
            self._canary_entries(), ["control.txt"],
            "canary unreachable from the child — the confinement assertion is "
            "vacuous (entries: %s)" % (self._canary_entries(),),
        )

    def test_debt_marker_carrier_absent_from_isolation_enumeration(self) -> None:
        """Records that the cure is perimetral, and fails when it stops being.

        Confinement currently depends on the repo-root ``conftest.py`` popping
        the carrier at import time. The structural fix is to add it to
        ``_lib.test_isolation.AUDIT_DIR_CARRIERS`` so the isolation layer points
        it at the session tmpdir like every other carrier — a canonical-guarded
        edit that lands through the Owner's signed-edit ceremony.

        Asserting on the enumeration itself is what makes this marker honest: an
        earlier version shelled out to a bare ``python -c``, which bypasses
        pytest isolation entirely and would have kept resolving to the external
        directory forever — green after the fix landed, never signalling
        anything. When this case goes red, delete it together with the conftest
        cure.
        """
        from _lib import test_isolation

        self.assertNotIn(
            _NATIVE_VAR, test_isolation.AUDIT_DIR_CARRIERS,
            "%s is now in AUDIT_DIR_CARRIERS — the structural fix landed. "
            "Remove the import-time pop in conftest.py and delete this case."
            % _NATIVE_VAR,
        )


if __name__ == "__main__":
    unittest.main()
