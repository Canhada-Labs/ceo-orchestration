"""PLAN-112-FOLLOWUP-hmac-tamper-fix Wave C regression test.

Synthesizes the Phase 4↔Phase 5 spool-drain rotation race condition that
produced F-7.7 STATUS_TAMPER on production audit-log.jsonl. With Wave B.1
producer fix (Phase 4 hoist of `_rotate_if_needed_safe`), this test must
PASS. If the fix is reverted, this test should FAIL.

The race scenario:
- Spool has N entries pending drain
- Canonical log is just under rotation threshold
- Drain Phase 4 reads tail (capturing pre-rotation prev_hmac)
- Drain Phase 5 detects rotation + appends batch_lines to NEW empty file
- Pre-fix bug: batch_lines carry stale prev_hmac → verifier fails at line 1
- Post-fix (Wave B.1): Phase 4 hoist detects rotation early → batch
  computed against post-rotation chain → verifier passes

Reference: PLAN-112 F-7.7 (C10 + D3 confirmed); forensic baseline at
`.claude/plans/PLAN-112-FOLLOWUP-hmac-tamper-fix/forensics/baseline.md`.
"""
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_HOOKS = Path(__file__).resolve().parent.parent
if str(_REPO_HOOKS) not in sys.path:
    sys.path.insert(0, str(_REPO_HOOKS))

from _lib import audit_emit, audit_hmac  # noqa: E402


class SpoolDrainRotationRaceRegressionTest(unittest.TestCase):
    """Regression for F-7.7 — the spool-drain rotation race that produced
    STATUS_TAMPER on production audit-log.jsonl prior to Wave B.1 fix."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="plan-112-followup-race-")
        self.audit_dir = Path(self.tmpdir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self._prev_audit_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
        self._prev_audit_path = os.environ.get("CEO_AUDIT_LOG_PATH")
        self._prev_rotate = os.environ.get("CEO_AUDIT_LOG_ROTATE_BYTES")
        self._prev_sync = os.environ.get("CEO_AUDIT_SYNC_MODE")
        # Set BOTH env vars: CEO_AUDIT_LOG_DIR controls audit_emit._log_path;
        # CEO_AUDIT_LOG_PATH controls audit_hmac._audit_dir_from_env.
        # Without both, sidecars (manifest/last-hmac/chain-length) end up
        # at the user's HOME audit-dir (pre-existing env contract divergence).
        os.environ["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.audit_dir / "audit-log.jsonl")
        # Force sync mode so rotation is testable deterministically without
        # waiting for spool flush. This validates the sync emit path's
        # rotation handling (which is the path that calls
        # _emit_chain_reset_marker_under_lock from audit_emit.py:1167).
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        # Full-suite isolation guard: a prior test in the same process may
        # have replaced sys.modules["_lib.audit_emit"]/["_lib.audit_hmac"]
        # with a different object (e.g. a re-import under a divergent sys.path),
        # so the module-level `audit_emit`/`audit_hmac` bound at import time is
        # no longer `is` the object in sys.modules — importlib.reload() then
        # raises "module ... not in sys.modules". Rebind the globals to the
        # current sys.modules objects (import_module returns exactly those),
        # then reload in place so they honor the env vars set above.
        global audit_emit, audit_hmac
        audit_hmac = importlib.reload(importlib.import_module("_lib.audit_hmac"))
        audit_emit = importlib.reload(importlib.import_module("_lib.audit_emit"))

    def tearDown(self):
        if self._prev_audit_dir is not None:
            os.environ["CEO_AUDIT_LOG_DIR"] = self._prev_audit_dir
        else:
            os.environ.pop("CEO_AUDIT_LOG_DIR", None)
        if self._prev_audit_path is not None:
            os.environ["CEO_AUDIT_LOG_PATH"] = self._prev_audit_path
        else:
            os.environ.pop("CEO_AUDIT_LOG_PATH", None)
        if self._prev_rotate is not None:
            os.environ["CEO_AUDIT_LOG_ROTATE_BYTES"] = self._prev_rotate
        else:
            os.environ.pop("CEO_AUDIT_LOG_ROTATE_BYTES", None)
        if self._prev_sync is not None:
            os.environ["CEO_AUDIT_SYNC_MODE"] = self._prev_sync
        else:
            os.environ.pop("CEO_AUDIT_SYNC_MODE", None)
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _emit(self, **payload):
        """Emit a plan_transition event (small payload, deterministic)."""
        i = payload.get("i", 0)
        audit_emit.emit_plan_transition(
            plan_id="TEST-RACE",
            from_status="draft",
            to_status="reviewed",
            file_path=".claude/plans/TEST-{}.md".format(i),
            session_id="test-race",
            project="test",
        )

    def test_rotation_race_chain_intact_post_fix(self):
        """The producer hoist (Wave B.1 + B.3) prevents F-7.7 STATUS_TAMPER
        across rotation boundaries.

        Triggers rotation by setting a low byte threshold + emitting enough
        events that the canonical log crosses it. Post-fix behavior:
        - Active log post-rotation contains chain_reset_marker (line 1) +
          subsequent emit (line 2)
        - Verifier walks the active log + returns EXIT_INTACT
        - Rotation manifest sidecar present + line 1 is chain_reset_marker
        """
        os.environ["CEO_AUDIT_LOG_ROTATE_BYTES"] = "300"
        importlib.reload(audit_emit)

        # Emit several events to trigger rotation
        for i in range(5):
            self._emit(i=i)

        log_path = audit_emit._log_path()
        self.assertTrue(log_path.exists(), "audit-log.jsonl missing")

        # At least 1 archive must exist (rotation fired)
        archives = list(self.audit_dir.glob("audit-log-*.jsonl"))
        self.assertGreaterEqual(
            len(archives), 1,
            f"expected >=1 archive post-rotation, got "
            f"{[p.name for p in archives]}",
        )

        # Manifest sidecar must exist (Wave B.3 marker contract)
        manifest_path = self.audit_dir / audit_hmac.ROTATION_MANIFEST_FILENAME
        self.assertTrue(
            manifest_path.exists(),
            f"rotation manifest sidecar missing at {manifest_path}",
        )
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest["marker_line_count"], 1)

        # Line 1 of active log MUST be chain_reset_marker
        with log_path.open(encoding="utf-8") as f:
            line_1 = json.loads(f.readline())
        self.assertEqual(
            line_1.get("action"),
            "chain_reset_marker",
            f"line 1 of post-rotation log must be chain_reset_marker per "
            f"ADR-055-AMEND-2; got {line_1.get('action')}",
        )

        # Verifier on the post-rotation active log MUST return EXIT_INTACT.
        # This is the F-7.7 regression assertion — pre-fix, this fails
        # at line 1 with hmac_mismatch.
        result = audit_hmac.verify_chain(log_path)
        self.assertEqual(
            result.status, audit_hmac.STATUS_INTACT,
            f"audit chain post-rotation must verify intact (F-7.7 regression); "
            f"got status={result.status}",
        )

    def test_rotation_marker_carries_previous_archive_last_hmac(self):
        """The chain_reset_marker's previous_archive_last_hmac field carries
        forensic continuity from the rotated archive — sanity check that
        the marker helper read_tail logic works."""
        os.environ["CEO_AUDIT_LOG_ROTATE_BYTES"] = "300"
        importlib.reload(audit_emit)

        for i in range(5):
            self._emit(i=i)

        log_path = audit_emit._log_path()
        with log_path.open(encoding="utf-8") as f:
            line_1 = json.loads(f.readline())

        # Marker MUST have previous_archive_path + previous_archive_last_hmac
        self.assertIn("previous_archive_path", line_1)
        self.assertIn("previous_archive_last_hmac", line_1)
        # last_hmac is best-effort — empty is allowed if archive tail
        # unreadable, but for a clean archive it should be a 64-char hex
        prev_hmac = line_1["previous_archive_last_hmac"]
        if prev_hmac:
            self.assertEqual(
                len(prev_hmac), 64,
                "previous_archive_last_hmac should be 64 hex chars if present",
            )

    def test_no_marker_when_no_rotation(self):
        """First-install case: emit without crossing threshold → no rotation
        → no marker → no manifest. Legacy mode (backwards compat)."""
        os.environ["CEO_AUDIT_LOG_ROTATE_BYTES"] = "10000000"  # 10MB, no rotation
        importlib.reload(audit_emit)

        for i in range(3):
            self._emit(i=i)

        log_path = audit_emit._log_path()
        self.assertTrue(log_path.exists())

        # No archive should exist
        archives = list(self.audit_dir.glob("audit-log-*.jsonl"))
        self.assertEqual(len(archives), 0, f"no rotation expected, got archives {archives}")

        # No manifest should exist (backwards-compat: first-install logs)
        manifest_path = self.audit_dir / audit_hmac.ROTATION_MANIFEST_FILENAME
        self.assertFalse(
            manifest_path.exists(),
            "no manifest expected for first-install (no-rotation) log",
        )

        # Line 1 is NOT chain_reset_marker — it's the first emit
        with log_path.open(encoding="utf-8") as f:
            line_1 = json.loads(f.readline())
        self.assertNotEqual(
            line_1.get("action"), "chain_reset_marker",
            "first-install line 1 must NOT be chain_reset_marker",
        )

        # Verifier intact in legacy mode (no manifest = no marker enforcement)
        result = audit_hmac.verify_chain(log_path)
        self.assertEqual(
            result.status, audit_hmac.STATUS_INTACT,
            f"first-install log must verify intact in legacy mode; got "
            f"status={result.status}",
        )


class SpoolDrainPathRotationRaceTest(unittest.TestCase):
    """AC13/AC14 spool-drain-path race regression — exercises the EXACT
    code path where F-7.7 occurred (NOT the sync emit path).

    The bug: spool_writer._phase4_compute_batch_lines() reads prev_hmac
    from canonical log tail BEFORE Phase 5 _phase5_append_canonical()
    detects rotation. Without Wave B.1 hoist, batch_lines computed against
    pre-rotation chain land in post-rotation file → STATUS_TAMPER line 1.

    With Wave B.1 hoist (Phase 4 probes rotation BEFORE reading tail),
    the batch is correctly chained against the new file's genesis state
    (or marker, per Wave B.3).

    This test does NOT set CEO_AUDIT_SYNC_MODE — it forces drain_now()
    explicitly to exercise the spool path.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="plan-112-followup-spool-race-")
        self.audit_dir = Path(self.tmpdir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self._prev_audit_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
        self._prev_audit_path = os.environ.get("CEO_AUDIT_LOG_PATH")
        self._prev_rotate = os.environ.get("CEO_AUDIT_LOG_ROTATE_BYTES")
        self._prev_sync = os.environ.get("CEO_AUDIT_SYNC_MODE")
        self._prev_state = os.environ.get("CEO_PROJECT_STATE_DIR")
        os.environ["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.audit_dir / "audit-log.jsonl")
        os.environ["CEO_PROJECT_STATE_DIR"] = str(self.audit_dir)
        # NO sync mode — exercise the SPOOL path
        os.environ.pop("CEO_AUDIT_SYNC_MODE", None)
        # Reload to pick up env
        importlib.reload(audit_hmac)
        importlib.reload(audit_emit)
        from _lib import spool_writer
        importlib.reload(spool_writer)
        spool_writer._reset_caches_for_test()
        self._spool_writer = spool_writer

    def tearDown(self):
        for k, v in [
            ("CEO_AUDIT_LOG_DIR", self._prev_audit_dir),
            ("CEO_AUDIT_LOG_PATH", self._prev_audit_path),
            ("CEO_AUDIT_LOG_ROTATE_BYTES", self._prev_rotate),
            ("CEO_AUDIT_SYNC_MODE", self._prev_sync),
            ("CEO_PROJECT_STATE_DIR", self._prev_state),
        ]:
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_spool_drain_across_rotation_boundary_chain_intact(self):
        """AC13/AC14 regression: spool drain Phase 4↔Phase 5 race.

        DETERMINISTIC reproducer (Codex R5 P0 fold): pre-populate the
        canonical log via sync emits ABOVE the eventual rotation threshold,
        THEN lower threshold, THEN spool + drain. This guarantees Phase 4's
        rotation probe (Wave B.1 hoist) sees an over-threshold log + must
        rotate before reading tail.

        Pre-Wave-B.1: STATUS_TAMPER at line 1 of new file (F-7.7).
        Post-Wave-B.1: STATUS_INTACT (Phase 4 hoist anchors batch against
        post-rotation chain via chain_reset_marker per Wave B.3).
        """
        # Step 1: pre-populate canonical log to MODERATE size (HIGH threshold)
        # so we can lower threshold below pre_size + spool a SMALL batch
        # that won't cause Phase 5 re-rotation (avoids double-rotation
        # cascade that masks the regression).
        os.environ["CEO_AUDIT_LOG_ROTATE_BYTES"] = "100000"  # 100KB
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"  # bypass spool for populate
        importlib.reload(audit_emit)

        # 6 sync emits ~ 2000-3000 bytes total
        for i in range(6):
            audit_emit.emit_plan_transition(
                plan_id=f"PRE-{i}",
                from_status="draft",
                to_status="reviewed",
                file_path=f".claude/plans/PRE-{i}.md",
                session_id="spool-race-pre-populate",
                project="test",
            )

        log_path = audit_emit._log_path()
        self.assertTrue(log_path.exists(), "pre-populate failed")
        pre_size = log_path.stat().st_size
        self.assertGreater(pre_size, 1500, "pre-populated log too small")

        # Step 2: set threshold ABOVE post-rotation worst case (marker ~500B
        # + small batch ~500B = ~1000B) but BELOW pre_size to force rotation.
        # threshold = pre_size + 100 would be wrong (above). We want
        # pre_size > threshold > expected_post_rotation_size.
        target_threshold = max(1000, pre_size - 500)
        os.environ["CEO_AUDIT_LOG_ROTATE_BYTES"] = str(target_threshold)
        os.environ.pop("CEO_AUDIT_SYNC_MODE", None)
        importlib.reload(audit_emit)
        importlib.reload(self._spool_writer)
        self._spool_writer._reset_caches_for_test()

        # Step 3: spool ONE entry via spool_append (NOT sync emit)
        # Single small entry keeps Phase 5 from re-rotating after Phase 4.
        for i in range(1):
            entry = {
                "action": "plan_transition",
                "plan_id": f"SPOOL-{i}",
                "from_status": "draft",
                "to_status": "reviewed",
                "editor_tool": "Edit",
                "file_path": f".claude/plans/SPOOL-{i}.md",
                "transition_legal": True,
                "session_id": "spool-race-test",
                "project": "test",
                "event_schema": "v2",
                "ts": "2026-05-21T12:00:00Z",
                "tokens_in": None,
                "tokens_out": None,
                "tokens_total": None,
            }
            self._spool_writer.spool_append(entry)

        # Step 4: force drain — Phase 4 probes rotation (log is above threshold;
        # rotation MUST fire). Phase 4 hoist (Wave B.1) ensures the batch is
        # computed against post-rotation chain via chain_reset_marker.
        stats = self._spool_writer.drain_now(force=True)

        # ASSERT rotation fired (this is the deterministic gate)
        archives = list(self.audit_dir.glob("audit-log-*.jsonl"))
        self.assertGreaterEqual(
            len(archives), 1,
            f"rotation MUST have fired (pre_size={pre_size}, threshold=500). "
            f"Archives: {[a.name for a in archives]}",
        )

        # ASSERT manifest sidecar exists (Wave B.3 contract)
        manifest_path = self.audit_dir / audit_hmac.ROTATION_MANIFEST_FILENAME
        self.assertTrue(
            manifest_path.exists(),
            "rotation manifest sidecar MUST exist post-spool-drain rotation "
            "per ADR-055-AMEND-2",
        )

        # ASSERT line 1 of new log is chain_reset_marker
        self.assertTrue(log_path.exists(), "fresh log missing post-rotation")
        with log_path.open(encoding="utf-8") as f:
            line_1 = json.loads(f.readline())
        self.assertEqual(
            line_1.get("action"),
            "chain_reset_marker",
            f"line 1 MUST be chain_reset_marker (Wave B.3 contract); "
            f"got action={line_1.get('action')}",
        )

        # ASSERT verifier intact — THE F-7.7 REGRESSION CANARY
        # Pre-Wave-B.1 hoist: this would fail at STATUS_TAMPER line 1
        # Post-fix: STATUS_INTACT
        result = audit_hmac.verify_chain(log_path)
        self.assertEqual(
            result.status,
            audit_hmac.STATUS_INTACT,
            f"F-7.7 REGRESSION DETECTED: spool drain crossed rotation but "
            f"verifier reports tamper. status={result.status}. "
            f"Wave B.1 Phase 4 rotation probe hoist may have been reverted.",
        )


if __name__ == "__main__":
    unittest.main()
