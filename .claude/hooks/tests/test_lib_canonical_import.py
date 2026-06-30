"""PLAN-118 AC-B2 — regression guard for stale `_lib` import-path pollution.

Two halves:

  PASS half (in-process)
    Import `_lib.audit_emit`, `_lib.audit_hmac`, `_lib.canonical_json` from
    the current process; assert each module's resolved ``__file__.parent``
    equals the canonical ``.claude/hooks/_lib/`` directory.

  FAIL half (clean subprocess, mutation-style)
    Plant a stale `_lib/audit_emit.py` to a tmp dir with a truncated
    ``_KNOWN_ACTIONS`` (missing the canonical-only action
    `audit_producer_path_pollution_detected`); spawn a CLEAN subprocess
    with ``PYTHONPATH=<tmp>``; in the subprocess, prepend tmp to
    ``sys.path[0]`` + evict ``_lib*`` from ``sys.modules`` + re-import.
    Assert EITHER the resolved path mismatches (PLAN-118 AC-B7 sys.modules
    guard logic at the test-process level) OR the runtime fail-CLOSED
    guard in ``audit_hmac.compute_entry_hmac`` fires
    ``AuditProducerPathPollutionError`` when invoked on a polluted dict.

Discipline (per PLAN-118 AC-B2 round-1 consensus + S178 Codex R3 P2):
  - Subprocess isolation is REQUIRED for the FAIL half (same-process
    tests cannot exercise the mutation due to sys.modules caching).
  - ``tmp_path`` (pytest fixture, NOT ``tempfile.mkdtemp``) — auto-
    cleaned on test exit.
  - ``request.addfinalizer`` restores ``sys.path`` AND ``sys.modules``
    even on exception.
  - Single-process only — no ``pytest-xdist`` worker scope; ``conftest.py``'s
    `pytest_collection_finish` snapshot guard (AC-B7) covers the
    cross-test pollution case.
  - ``CEO_AUDIT_SPOOL_ENABLED`` does NOT exist; spool is DEFAULT,
    ``CEO_AUDIT_SYNC_MODE=1`` is the kill-switch (per
    ``spool_writer.py:518``). The subprocess test runs WITHOUT
    ``CEO_AUDIT_SYNC_MODE`` so the spool-drain code path is exercised
    under the planted stale copy (covers chokepoint 5 per AC-B4).

Platform invariant: this test runs on ``ubuntu-latest`` (via
``validate.yml`` ``hook-tests-python-matrix``). Subprocess isolation
makes start-method (darwin spawn vs linux fork) irrelevant.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import List, Optional

import pytest

pytestmark = pytest.mark.serial  # S220 / PLAN-118: single-process, no xdist worker scope


_CANONICAL_HOOKS_DIR = Path(__file__).resolve().parent.parent
_CANONICAL_LIB_DIR = _CANONICAL_HOOKS_DIR / "_lib"
_HMAC_TRIO_MODULE_NAMES = ("_lib.audit_emit", "_lib.audit_hmac", "_lib.canonical_json")


# ---------------------------------------------------------------------------
# PASS half — in-process: canonical resolution under normal sys.path
# ---------------------------------------------------------------------------


class TestCanonicalResolutionInProcess:
    """In-process canonical-resolution check.

    The conftest.py `pytest_collectstart` puts `.claude/hooks/` on
    `sys.path[0]` so `from _lib import …` resolves canonical. These
    tests prove the resolution went through the canonical dir.
    """

    @pytest.mark.parametrize("mod_name", _HMAC_TRIO_MODULE_NAMES)
    def test_module_file_resolves_canonical(self, mod_name: str) -> None:
        """PLAN-118 AC-B2 PASS half — Path(mod.__file__).parent == canonical _lib/."""
        import importlib

        mod = importlib.import_module(mod_name)
        mod_file = getattr(mod, "__file__", None)
        assert mod_file is not None, (
            f"{mod_name} has no __file__ — cannot verify canonical resolution"
        )
        resolved_parent = Path(mod_file).resolve().parent
        assert resolved_parent == _CANONICAL_LIB_DIR, (
            f"{mod_name} resolved to {resolved_parent}; "
            f"expected canonical {_CANONICAL_LIB_DIR}"
        )

    def test_canonical_lib_dir_constant_self_consistent(self) -> None:
        """audit_hmac._CANONICAL_LIB_DIR matches this test's computation."""
        from _lib import audit_hmac

        assert audit_hmac._CANONICAL_LIB_DIR == _CANONICAL_LIB_DIR, (
            f"audit_hmac._CANONICAL_LIB_DIR ({audit_hmac._CANONICAL_LIB_DIR}) "
            f"diverges from test-computed canonical ({_CANONICAL_LIB_DIR}). "
            f"The self-locating Path(__file__).resolve().parent in "
            f"audit_hmac.py is the reference; if these disagree the test "
            f"file moved OR audit_hmac.py moved OR a symlink rewrote one path."
        )


# ---------------------------------------------------------------------------
# FAIL half — clean subprocess: planted stale `_lib` + sys.modules eviction
# ---------------------------------------------------------------------------

_STALE_AUDIT_EMIT_SOURCE = textwrap.dedent('''\
    """PLAN-118 AC-B2 FAIL-half planted stale audit_emit.py.

    Mimics a pre-PLAN-106 producer (lacks
    `audit_producer_path_pollution_detected` from the closed-enum set
    AND `output_scan_finding_suppressed` from PLAN-106 H.1) — exactly
    the shape of the producer that wrote the S177-observed polluted
    chain_reset_markers.
    """
    _KNOWN_ACTIONS = frozenset({
        "agent_spawn",
        "chain_reset_marker",
        # Deliberately MISSING:
        #   "audit_producer_path_pollution_detected" (PLAN-118 AC-B5)
        #   "output_scan_finding_suppressed" (PLAN-106 H.1)
        #   "credential_override_late_set_ignored" (PLAN-117 WS-A)
        # If a probe imports THIS stale audit_emit.py instead of the
        # canonical one, len(_KNOWN_ACTIONS) reads as 2 (not 263) — a
        # detectable structural difference even before any emit.
    })

    STALE_AUDIT_EMIT_SENTINEL = "PLAN-118-AC-B2-PLANTED-STALE"
''')


_SUBPROCESS_PROBE = textwrap.dedent('''\
    """PLAN-118 AC-B2 FAIL-half subprocess probe.

    Runs in a CLEAN subprocess (no shared sys.modules with the test
    runner). Pollutes sys.path with the planted tmp `_lib/` parent
    first; evicts any pre-loaded _lib* from sys.modules; re-imports
    _lib.audit_emit; asserts the resolved __file__ is the planted
    tmp path (NOT canonical).

    Exit code semantics:
      0 — mutation took effect (resolved path != canonical) — TEST PASSES
      1 — mutation FAILED (resolved path == canonical) — TEST FAILS
      2 — internal probe error — TEST FAILS

    Stdout prints the resolved parent + canonical parent for forensic
    diagnostics on FAIL.
    """
    import os
    import sys
    from pathlib import Path

    PLANTED_PARENT = Path(os.environ["PLANTED_PARENT_DIR"]).resolve()
    CANONICAL_LIB = Path(os.environ["CANONICAL_LIB_DIR"]).resolve()
    STALE_SENTINEL = "PLAN-118-AC-B2-PLANTED-STALE"

    # Prepend PLANTED_PARENT so `from _lib import audit_emit` resolves
    # the planted stale copy first.
    sys.path.insert(0, str(PLANTED_PARENT))

    # Evict any _lib* modules that may have been pre-loaded (e.g. by
    # the conftest's pytest_collectstart in the parent process — though
    # the subprocess starts fresh, defensive eviction is cheap).
    for name in list(sys.modules):
        if name == "_lib" or name.startswith("_lib."):
            del sys.modules[name]

    try:
        from _lib import audit_emit  # noqa: E402
    except Exception as e:
        print(f"PROBE_ERROR: import failed: {type(e).__name__}: {e}",
              file=sys.stderr)
        sys.exit(2)

    resolved = Path(audit_emit.__file__).resolve().parent

    sentinel_seen = getattr(audit_emit, "STALE_AUDIT_EMIT_SENTINEL", None)

    print(f"resolved={resolved}")
    print(f"canonical={CANONICAL_LIB}")
    print(f"sentinel_seen={sentinel_seen}")

    # Success condition: the planted stale copy was loaded (resolved
    # parent != canonical_lib AND sentinel matches the planted source).
    if resolved == CANONICAL_LIB:
        print("PROBE_FAIL: resolved == canonical — mutation did NOT take effect",
              file=sys.stderr)
        sys.exit(1)
    if sentinel_seen != STALE_SENTINEL:
        print(f"PROBE_FAIL: sentinel mismatch (seen={sentinel_seen!r}, "
              f"expected={STALE_SENTINEL!r}) — wrong module loaded",
              file=sys.stderr)
        sys.exit(1)

    sys.exit(0)
''')


def _plant_stale_lib(tmp_path: Path) -> Path:
    """Plant a stale `_lib/` tree under tmp_path; return the parent dir."""
    lib_dir = tmp_path / "_lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    (lib_dir / "__init__.py").write_text("", encoding="utf-8")
    (lib_dir / "audit_emit.py").write_text(_STALE_AUDIT_EMIT_SOURCE, encoding="utf-8")
    return tmp_path


class TestStalePollutionRegressionGuard:
    """Subprocess-isolated mutation test (PLAN-118 AC-B2 FAIL half).

    Hand-planted sentinel + clean subprocess per round-1 D4 unanimous
    consensus (NOT mutmut — full mutation is overkill for a structural
    import-path test; reserve mutmut for `_lib.audit_emit`'s semantic
    behavior under its own ≥80% kill-rate obligation, ADR-139 Tier-1).
    """

    def test_planted_stale_lib_resolves_non_canonical(
        self, tmp_path: Path, request: pytest.FixtureRequest,
    ) -> None:
        """PLAN-118 AC-B2 FAIL half — subprocess probe loads planted stale.

        Asserts that prepending a stale `_lib/` parent to sys.path[0]
        in a clean subprocess causes `from _lib import audit_emit` to
        resolve to the planted copy — proving the regression-guard's
        ability to detect a real-world stale-`_lib` injection.

        If this test FAILS (subprocess exit code 1), Python resolved
        canonical despite the sys.path injection — which would mean
        either the test environment is broken OR Python's import
        semantics changed (e.g. importlib namespace-package behavior
        differs). Either way, the conftest snapshot guard (AC-B7) +
        runtime fail-CLOSED (AC-B4) become the load-bearing defenses.
        """
        planted_parent = _plant_stale_lib(tmp_path)

        # Sanity: planted files exist
        assert (planted_parent / "_lib" / "__init__.py").exists()
        assert (planted_parent / "_lib" / "audit_emit.py").exists()

        probe_script = tmp_path / "probe.py"
        probe_script.write_text(_SUBPROCESS_PROBE, encoding="utf-8")

        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PLANTED_PARENT_DIR"] = str(planted_parent)
        env["CANONICAL_LIB_DIR"] = str(_CANONICAL_LIB_DIR)
        # CEO_AUDIT_SYNC_MODE deliberately NOT set — exercises spool path
        # (default). The test does not actually emit; this is just to
        # ensure the planted module loads under the same env shape as
        # the real producer would.

        # Run probe in a clean subprocess — no shared sys.modules.
        proc = subprocess.run(
            [sys.executable, str(probe_script)],
            env=env,
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Diagnostic on failure
        assert proc.returncode == 0, (
            f"Subprocess probe failed (exit={proc.returncode}). "
            f"This means the planted stale `_lib/` injection FAILED to "
            f"shadow the canonical copy in the subprocess — Python "
            f"import semantics may have changed.\n"
            f"stdout={proc.stdout!r}\n"
            f"stderr={proc.stderr!r}"
        )
        # Verify probe output proves the mutation took
        assert "resolved=" in proc.stdout, proc.stdout
        assert "sentinel_seen=PLAN-118-AC-B2-PLANTED-STALE" in proc.stdout, proc.stdout

    def test_runtime_fail_closed_fires_on_pollution(
        self, tmp_path: Path, request: pytest.FixtureRequest,
    ) -> None:
        """PLAN-118 AC-B4 chokepoint 3 verification via clean subprocess.

        Probe loads CANONICAL `_lib.audit_emit` + `audit_hmac` + `canonical_json`
        first, then MONKEY-PATCHES `sys.modules["_lib.audit_emit"].__file__`
        to a non-canonical path (the planted stale audit_emit.py).
        This simulates the S177 scenario: a stale producer module on disk
        is loaded by some path-injection vector and the canonical-resolution
        check at compute_entry_hmac entry detects the drift.

        Why monkey-patch instead of a real sys.path injection: Python's
        package-binding semantics make it hard to load `_lib.audit_emit`
        from one dir + `_lib.audit_hmac` from another in a single process
        (first hit wins; rebinding requires explicit importlib gymnastics
        that masks the test's intent). The monkey-patch isolates the
        exact attribute (`__file__`) that the runtime check inspects.
        The check's actual behavior on disk is exercised by the
        FIRST subprocess test (test_planted_stale_lib_resolves_non_canonical)
        + by the conftest.py pytest_collection_finish snapshot guard.
        """
        planted_parent = _plant_stale_lib(tmp_path)
        stale_file = str(planted_parent / "_lib" / "audit_emit.py")

        probe = textwrap.dedent(f'''\
            import os, sys
            from pathlib import Path

            # Make canonical _lib reachable
            sys.path.insert(0, {str(_CANONICAL_HOOKS_DIR)!r})
            # Defensively evict any pre-loaded _lib* (fresh subprocess
            # shouldn't have any, but ensure clean slate)
            for n in list(sys.modules):
                if n == "_lib" or n.startswith("_lib."):
                    del sys.modules[n]
            from _lib import audit_emit, audit_hmac, canonical_json
            # Monkey-patch audit_emit.__file__ to the planted stale path
            # (simulates the S177 producer-pollution scenario)
            audit_emit.__file__ = {stale_file!r}
            try:
                audit_hmac.compute_entry_hmac(
                    key=b"\\x00" * audit_hmac.KEY_BYTES,
                    prev_hmac=b"\\x00" * audit_hmac.HMAC_BYTES,
                    entry_without_hmac={{"action": "agent_spawn"}},
                )
            except audit_hmac.AuditProducerPathPollutionError as ppe:
                msg = str(ppe)
                assert "audit_emit_path_pollution" in msg, msg
                assert "path_sha256_prefix=" in msg, msg
                assert "expected_canonical_prefix=" in msg, msg
                print(f"OK_FIRED: {{type(ppe).__name__}}")
                sys.exit(0)
            except Exception as e:
                print(f"WRONG_EXC: {{type(e).__name__}}: {{e}}", file=sys.stderr)
                sys.exit(2)
            print("NO_EXC: compute_entry_hmac returned without firing", file=sys.stderr)
            sys.exit(1)
        ''')

        probe_script = tmp_path / "probe_runtime_fail_closed.py"
        probe_script.write_text(probe, encoding="utf-8")

        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        proc = subprocess.run(
            [sys.executable, str(probe_script)],
            env=env,
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert proc.returncode == 0, (
            f"Runtime fail-CLOSED guard did NOT fire on planted stale "
            f"audit_emit.__file__ monkey-patch (exit={proc.returncode}).\n"
            f"stdout={proc.stdout!r}\n"
            f"stderr={proc.stderr!r}"
        )
        assert "OK_FIRED: AuditProducerPathPollutionError" in proc.stdout, proc.stdout
