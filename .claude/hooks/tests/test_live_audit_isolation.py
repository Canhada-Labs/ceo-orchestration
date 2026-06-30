"""PLAN-119 WS-E — regression tests for the suite-wide audit-dir isolation.

These assert the durable-fix invariants directly (qa RC-2 — path-level compare,
no I/O race as the primary signal):

- E1: the PRODUCTION audit-dir resolver does not resolve to the live dir during
  a test (it resolves under the per-session isolation tmpdir).
- A1: a *subprocess* that even UNSETS ``CEO_AUDIT_LOG_DIR`` still cannot write to
  the real live log, because ``HOME`` is redirected (the byte-count of the real
  live log is unchanged). Deterministic; NOT a nested child-pytest (qa RC-3).
- A3: ``CEO_TEST_HARNESS=1`` is present for collected tests AND exported to
  subprocess children.
- A4: ``allow_live_audit_dir`` is registered in ``pytest.ini`` (so
  ``--strict-markers`` does not red CI if a future test legitimately uses it).

Note: this file intentionally does NOT apply the escape-hatch marker decorator,
so the WS-E grep gate (which counts decorator usages) stays at zero.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

_HOOKS_DIR = str(Path(__file__).resolve().parent.parent)  # .claude/hooks
_REPO_ROOT = Path(__file__).resolve().parents[3]
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

from _lib import audit_emit  # noqa: E402
from _lib import test_isolation  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402

_MARKER_NAME = "allow_live_audit_dir"


def test_session_redirect_path_invariant():
    """E1 — the production resolver must NOT resolve to the live audit dir."""
    snapshot = os.environ.get(test_isolation.LIVE_LOG_SNAPSHOT_VAR)
    assert snapshot, (
        "the session isolation fixture must have captured the live-log snapshot "
        "(CEO_AUDIT_LIVE_LOG_PATH_SNAPSHOT) — is the autouse fixture registered?"
    )
    resolved_dir = Path(audit_emit._audit_dir()).resolve()
    live_dir = Path(snapshot).resolve().parent
    assert resolved_dir != live_dir, (
        "audit dir resolves to the LIVE dir during a test — isolation breached"
    )


def test_session_redirect_targets_a_tmp_tree():
    """E1 (corollary) — the redirected audit dir lives under the session
    isolation tmpdir, not the real HOME tree."""
    resolved_dir = str(Path(audit_emit._audit_dir()).resolve())
    assert "ceo-suite-isolation-" in resolved_dir, (
        f"expected the audit dir under the session isolation tmpdir; got "
        f"{resolved_dir!r}"
    )


def test_subprocess_write_event_cannot_reach_live_even_with_carriers_unset():
    """A1 (airtight) — a child that UNSETS CEO_AUDIT_LOG_DIR and ALL the per-file
    audit overrides STILL cannot write to the live log, because the session
    fixture redirected HOME: the resolver falls back to the redirected HOME's
    .claude/ tree (non-live), never the real ~/.claude. The real live log is
    byte-identical before/after. This is the Codex-required structural proof of
    the HOME-fallback guarantee; deterministic, NOT a nested child-pytest."""
    snapshot = os.environ.get(test_isolation.LIVE_LOG_SNAPSHOT_VAR)
    assert snapshot, "missing live-log snapshot — session fixture not active"
    live_log = Path(snapshot)
    before = live_log.read_bytes() if live_log.exists() else b""

    child_env = dict(os.environ)  # carries the redirected HOME=<isolated tmp>
    # Drop EVERY audit path carrier so the child must fall back to HOME.
    for var in ("CEO_AUDIT_LOG_DIR", "CEO_AUDIT_LOG_PATH", "CEO_AUDIT_LOG_ERR",
                "CEO_AUDIT_LOG_LOCK", "CEO_AUDIT_KEY_PATH",
                "CEO_AUDIT_LAST_HMAC_PATH", "CEO_AUDIT_CHAIN_LENGTH_PATH",
                "CEO_PROJECT_STATE_DIR"):
        child_env.pop(var, None)
    code = (
        "import sys\n"
        f"sys.path.insert(0, {_HOOKS_DIR!r})\n"
        "from _lib import audit_emit\n"
        "audit_emit._write_event({'action': 'ceo_boot_emitted'})\n"
        "print('CHILD_AUDIT_DIR=' + str(audit_emit._audit_dir().resolve()))\n"
    )
    res = subprocess.run(
        [sys.executable, "-c", code],
        env=child_env, capture_output=True, text=True,
    )
    assert res.returncode == 0, f"child failed: {res.stderr}"
    child_dir_lines = [
        ln for ln in res.stdout.splitlines() if ln.startswith("CHILD_AUDIT_DIR=")
    ]
    assert child_dir_lines, f"child did not report its audit dir; stdout={res.stdout!r}"
    child_dir = Path(child_dir_lines[0].split("=", 1)[1]).resolve()
    assert child_dir != live_log.resolve().parent, (
        "child resolved the LIVE audit dir with carriers unset — HOME redirect "
        "failed (the airtight fallback guarantee is breached)"
    )
    # the child resolved under the redirected HOME tmp tree
    redirected_home = Path(os.environ["HOME"]).resolve()
    assert str(child_dir).startswith(str(redirected_home)), (
        f"child dir {child_dir} is not under the redirected HOME {redirected_home}"
    )
    after = live_log.read_bytes() if live_log.exists() else b""
    assert after == before, (
        "the real live audit-log was modified by a subprocess emit — isolation "
        "breached"
    )


def test_ceo_test_harness_present_and_exported():
    """A3 — CEO_TEST_HARNESS=1 present in os.environ + exported to children."""
    assert os.environ.get("CEO_TEST_HARNESS") == "1"
    res = subprocess.run(
        [sys.executable, "-c", "import os; print(os.environ.get('CEO_TEST_HARNESS',''))"],
        env=dict(os.environ), capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == "1", "CEO_TEST_HARNESS not exported to subprocess"


def test_escape_hatch_marker_registered_in_pytest_ini():
    """A4 — the escape-hatch marker is registered (kept registered so
    --strict-markers accepts a future legitimate use)."""
    ini = (_REPO_ROOT / "pytest.ini").read_text(encoding="utf-8")
    assert f"{_MARKER_NAME}:" in ini, (
        f"{_MARKER_NAME} must be registered in pytest.ini [pytest] markers"
    )


def test_carrier_set_single_source_complete():
    """The carrier enumeration is the single source of truth (WS-C reuses it).
    Guard against a future edit that drops a known audit-location carrier."""
    carriers = set(test_isolation.ALL_AUDIT_CARRIERS)
    # HOME is deliberately NOT a redirected carrier (it only breaks subprocess
    # tooling — see _lib/test_isolation.py). CEO_AUDIT_LOG_DIR is the primary
    # anchor; the per-file sidecars must be CLEARED so they default off it.
    for required in ("CEO_AUDIT_LOG_DIR", "CEO_PROJECT_STATE_DIR",
                     "CEO_AUDIT_KEY_PATH", "CEO_AUDIT_LAST_HMAC_PATH",
                     "CEO_AUDIT_CHAIN_LENGTH_PATH"):
        assert required in carriers, f"{required} dropped from the carrier set"


class TestSubprocessEnvIsolation(TestEnvContext):
    """PLAN-119 WS-C — TestEnvContext.subprocess_env() isolates spawned children."""

    def _child(self, body: str, env: dict):
        code = f"import sys\nsys.path.insert(0, {_HOOKS_DIR!r})\n" + body
        return subprocess.run(
            [sys.executable, "-c", code], env=env, capture_output=True, text=True
        )

    def test_child_writes_to_isolated_dir_not_live(self):
        """C2 — a child spawned with subprocess_env() writes to THIS test's
        isolated audit dir; the real live log is byte-identical."""
        snapshot = os.environ.get(test_isolation.LIVE_LOG_SNAPSHOT_VAR)
        live_log = Path(snapshot) if snapshot else None
        before = live_log.read_bytes() if (live_log and live_log.exists()) else b""

        env = self.subprocess_env()
        res = self._child(
            "from _lib import audit_emit\n"
            "audit_emit._write_event({'action': 'ceo_boot_emitted'})\n"
            "print('DIR=' + str(audit_emit._audit_dir().resolve()))\n",
            env,
        )
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        dir_lines = [ln for ln in res.stdout.splitlines() if ln.startswith("DIR=")]
        self.assertTrue(dir_lines, msg=f"no DIR line; stdout={res.stdout!r}")
        child_dir = Path(dir_lines[0].split("=", 1)[1]).resolve()
        self.assertEqual(child_dir, self.audit_dir.resolve())
        self.assertTrue((self.audit_dir / "audit-log.jsonl").exists(),
                        "child emit did not land in the isolated dir")
        if live_log is not None:
            after = live_log.read_bytes() if live_log.exists() else b""
            self.assertEqual(after, before, "live log mutated by isolated child")

    def test_partial_override_rejected(self):
        """C3 — subprocess_env() rejects a partial override that leaves an audit
        path carrier pointing outside the isolated tmp tree."""
        outside = "/tmp/p119-not-the-test-tree/audit-log.jsonl"
        with self.assertRaises(ValueError):
            self.subprocess_env(CEO_AUDIT_LOG_PATH=outside)

    def test_home_override_to_live_rejected(self):
        """C3 (Codex P1) — overriding HOME outside the test tmp tree is rejected,
        even when CEO_AUDIT_LOG_DIR is emptied (else the fallback resolves the
        real ~/.claude). The default (no override) HOME is under the tmp tree."""
        # default: HOME is redirected under the per-test tmp → accepted.
        env = self.subprocess_env()
        self.assertTrue(
            str(Path(env["HOME"]).resolve()).startswith(
                str(Path(self._tmp_root).resolve())))
        # emptying the primary anchor AND pointing HOME at a live path → rejected.
        with self.assertRaises(ValueError):
            self.subprocess_env(CEO_AUDIT_LOG_DIR="", HOME="/etc")
        with self.assertRaises(ValueError):
            self.subprocess_env(HOME="/var/root")

    def test_child_reads_genesis_prev_hmac(self):
        """C4 — a child spawned with subprocess_env() reads the GENESIS
        prev_hmac (fresh isolated chain), never the live chain tail."""
        env = self.subprocess_env()
        res = self._child(
            "from _lib import audit_hmac\n"
            "print('PREV=' + audit_hmac.read_prev_hmac().hex())\n",
            env,
        )
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        prev_lines = [ln for ln in res.stdout.splitlines() if ln.startswith("PREV=")]
        self.assertTrue(prev_lines, msg=f"no PREV line; stdout={res.stdout!r}")
        prev_hex = prev_lines[0].split("=", 1)[1]
        self.assertEqual(prev_hex, "00" * 32,
                         msg=f"child did not read GENESIS prev_hmac; got {prev_hex}")


class TestWsD1OriginStamp(TestEnvContext):
    """PLAN-119 WS-D1 — spool write-time origin stamp + drain-time quarantine."""

    SYNC_MODE_DEFAULT = False  # async — exercise the spool + drain path

    # NOTE: env is manipulated ONLY via ``mock.patch.dict`` (auto-restores, incl.
    # on exception; no raw ``os.environ`` mutation in test source — keeps the
    # test-env-hygiene gate green). The production reads use truthiness, so ``""``
    # reads as "unset" for CEO_TEST_HARNESS / PYTEST_CURRENT_TEST / the snapshot.

    def test_origin_stamp_reflects_test_signal(self):
        from _lib import spool_writer
        with mock.patch.dict(os.environ, {"CEO_TEST_HARNESS": "1"}):
            self.assertEqual(spool_writer._origin_for_new_spool(), "test")
        with mock.patch.dict(
            os.environ, {"CEO_TEST_HARNESS": "", "PYTEST_CURRENT_TEST": ""}
        ):
            self.assertEqual(spool_writer._origin_for_new_spool(), "live")

    def test_should_quarantine_gating(self):
        from _lib import spool_writer

        class _F:
            pass

        f = _F()
        live = self.audit_dir / "audit-log.jsonl"
        with mock.patch.dict(os.environ, {spool_writer._LIVE_LOG_SNAPSHOT_VAR: str(live)}):
            f.header = {"_origin": "test"}
            self.assertTrue(spool_writer._should_quarantine_test_origin(f, live))
            # dest != live snapshot (redirected tmp) → drains normally there.
            f.header = {"_origin": "test"}
            self.assertFalse(spool_writer._should_quarantine_test_origin(
                f, self.audit_dir / "elsewhere" / "audit-log.jsonl"))
            # _origin:"live" → never quarantined.
            f.header = {"_origin": "live"}
            self.assertFalse(spool_writer._should_quarantine_test_origin(f, live))
            # legacy no-_origin → defaults live → never quarantined.
            f.header = {}
            self.assertFalse(spool_writer._should_quarantine_test_origin(f, live))
        # snapshot absent ("" reads as absent) → fail-safe: NO quarantine.
        with mock.patch.dict(os.environ, {spool_writer._LIVE_LOG_SNAPSHOT_VAR: ""}):
            f.header = {"_origin": "test"}
            self.assertFalse(spool_writer._should_quarantine_test_origin(f, live))

    def test_test_origin_spool_refused_at_live_drain(self):
        """D1-AC1 — a _origin:"test" spool at a drain whose canonical dest IS
        the live chain does NOT append to the live log (byte-identical)."""
        from _lib import spool_writer
        canonical = self.audit_dir / "audit-log.jsonl"
        before = canonical.read_bytes() if canonical.exists() else b""
        with mock.patch.dict(os.environ, {
            "CEO_TEST_HARNESS": "1",
            spool_writer._LIVE_LOG_SNAPSHOT_VAR: str(canonical),  # dest==live
        }):
            spool_writer.spool_append({"action": "agent_spawn", "marker": "d1ac1"})
            stats = spool_writer.drain_now(force=True)
        after = canonical.read_bytes() if canonical.exists() else b""
        self.assertEqual(after, before,
                         "test-origin spool leaked into the live-dest log")
        self.assertGreaterEqual(stats.test_origin_quarantined, 1)

    def test_test_origin_spool_drains_to_redirected_dest(self):
        """D1-AC4 — a _origin:"test" spool whose canonical dest is NOT the live
        snapshot drains NORMALLY there (isolated drain-behavior tests work)."""
        from _lib import spool_writer
        canonical = self.audit_dir / "audit-log.jsonl"
        with mock.patch.dict(os.environ, {
            "CEO_TEST_HARNESS": "1",
            spool_writer._LIVE_LOG_SNAPSHOT_VAR: str(
                self.audit_dir / "elsewhere" / "audit-log.jsonl"),  # dest != live
        }):
            spool_writer.spool_append({"action": "agent_spawn", "marker": "d1ac4"})
            stats = spool_writer.drain_now(force=True)
        self.assertEqual(stats.test_origin_quarantined, 0)
        self.assertGreaterEqual(stats.appended, 1)
        self.assertIn("d1ac4", canonical.read_text() if canonical.exists() else "")


class TestWsD2ImportClosure(TestEnvContext):
    """PLAN-119 WS-D2 — import-time stale-copy closure.

    The recurring ``unknown action 'output_scan_finding_suppressed'`` breadcrumb
    is emitted ONLY by a STALE pre-PLAN-106 ``audit_emit.py`` loaded onto
    ``sys.path`` — the canonical producer HAS the action so it never reaches the
    unknown-action branch. The durable closure is import-time + source: archived
    stale copies (``_lib_archived/``) hard-raise on import (PLAN-118 AC-B6,
    extended by the S179 sandbox→archived renames); the destination of any
    residual stale-producer breadcrumb is redirected by WS-A. These tests codify
    the protection as a PLAN-119 gate.
    """

    def test_canonical_audit_emit_has_the_recurring_action(self):
        """Root-cause proof: the canonical producer KNOWS the action, so the
        breadcrumb can only come from a stale copy — never the canonical lib."""
        self.assertIn("output_scan_finding_suppressed", audit_emit._KNOWN_ACTIONS)

    def test_archived_lib_raises_on_import(self):
        """D2-AC1 — an archived stale ``_lib_archived/`` package hard-raises on
        import (PLAN-118 AC-B6 mechanism), so a stale ``audit_emit`` under it can
        never be imported. Subprocess-isolated (PLAN-118 AC-C0 pattern)."""
        root = self._tmp_root / "archived-probe"
        pkg = root / "_lib_archived"
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "__init__.py").write_text(
            'raise ImportError("archived stale _lib copy — import forbidden (PLAN-118)")\n',
            encoding="utf-8",
        )
        (pkg / "audit_emit.py").write_text("X = 1\n", encoding="utf-8")
        code = (
            "import sys\n"
            f"sys.path.insert(0, {str(root)!r})\n"
            "try:\n"
            "    import _lib_archived.audit_emit  # noqa\n"
            "    print('IMPORTED')\n"
            "except ImportError:\n"
            "    print('RAISED')\n"
        )
        res = subprocess.run([sys.executable, "-c", code], env=dict(os.environ),
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertIn("RAISED", res.stdout,
                      msg=f"archived _lib did not hard-raise; stdout={res.stdout!r}")

    def test_active_staged_audit_emit_still_imports(self):
        """D2-AC4 — the ACTIVE PLAN-078 staging fixture, deliberately loaded as a
        ``_lib.audit_emit`` shadow by test_check_agent_spawn, still imports
        (the closure is scoped to archived/sandbox copies, NOT active staging)."""
        import importlib.util
        staged = (_REPO_ROOT / ".claude" / "plans" / "PLAN-078" / "staging"
                  / "wave-1" / "audit_emit.py")
        if not staged.is_file():
            self.skipTest("PLAN-078 staging fixture absent")
        spec = importlib.util.spec_from_file_location("_staged_probe_audit_emit", staged)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # must NOT raise
        self.assertTrue(hasattr(mod, "_KNOWN_ACTIONS"))
