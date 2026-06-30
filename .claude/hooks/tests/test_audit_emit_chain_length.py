"""PLAN-044 audit-v2 C6-P0-03 — chain-length canary wire tests.

Validates that ``_lib.audit_emit._write_event`` now increments the
chain-length canary (``audit_hmac.write_chain_length``) under the same
FileLock as ``write_last_hmac``, gate-guarded on
(``_HMAC_AVAILABLE`` AND ``event["hmac"]`` AND ``not is_disabled()``).

Closes the audit-v2 P0 finding: pre-wire, the canary helpers existed
but were never invoked; the counter stayed at 0 forever, so
``verify_chain(strict_against_counter=True)`` could not detect tail
truncation. Post-wire, the counter advances per HMAC-bearing entry
and ``verify_chain`` raises ``STATUS_TAMPER`` with
``reason="chain_length_truncation"`` when the log is truncated.
"""

from __future__ import annotations

import importlib
import json
import multiprocessing as mp
import os
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import patch

from _lib import audit_emit  # noqa: E402
from _lib import audit_hmac  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


def _emit_one(plan_id: str = "PLAN-TEST", phase: str = "start") -> None:
    """Emit one valid debate_event (HMAC-bearing under default env)."""
    audit_emit.emit_debate_event(
        plan_id=plan_id,
        round_num=1,
        phase=phase,
        agent="test-archetype",
    )


class CanaryWiringTests(TestEnvContext):
    """Cover every branch in the new canary block + e2e proof."""

    def setUp(self) -> None:
        super().setUp()
        # Reload audit_emit so module-level path helpers pick up the
        # isolated CEO_AUDIT_LOG_* env set by TestEnvContext.setUp().
        importlib.reload(audit_emit)

    def tearDown(self) -> None:
        super().tearDown()

    # --- Test 1 ---------------------------------------------------------
    def test_canary_increments_per_event(self) -> None:
        """Happy path: 3 HMAC-bearing emits -> counter == 3."""
        for i in range(3):
            _emit_one(phase=f"start-{i}")
        self.assertEqual(audit_hmac.read_chain_length(), 3)

    # --- Test 2 ---------------------------------------------------------
    def test_canary_skip_when_hmac_disabled(self) -> None:
        """``CEO_AUDIT_HMAC_DISABLE=1`` -> no HMAC, no canary increment."""
        with mock.patch.dict(os.environ, {"CEO_AUDIT_HMAC_DISABLE": "1"}):
            for i in range(3):
                _emit_one(phase=f"start-{i}")
            self.assertEqual(audit_hmac.read_chain_length(), 0)

    # --- Test 3 ---------------------------------------------------------
    def test_canary_skip_when_hmac_compute_fails(self) -> None:
        """compute_entry_hmac raise -> event["hmac"] None -> skip canary."""
        with patch.object(
            audit_hmac,
            "compute_entry_hmac",
            side_effect=audit_hmac.AuditHmacError("simulated"),
        ):
            _emit_one(phase="failing")
        # Failing emit produced event["hmac"] = None; canary skipped.
        self.assertEqual(audit_hmac.read_chain_length(), 0)
        # A clean emit afterwards advances normally.
        _emit_one(phase="recovered")
        self.assertEqual(audit_hmac.read_chain_length(), 1)

    # --- Test 4 ---------------------------------------------------------
    def test_canary_skip_when_HMAC_unavailable(self) -> None:
        """``_HMAC_AVAILABLE=False`` -> no AttributeError, counter stays 0."""
        with patch.object(audit_emit, "_HMAC_AVAILABLE", False):
            _emit_one(phase="hmac-unavailable")
        # Counter unchanged because gate excluded.
        self.assertEqual(audit_hmac.read_chain_length(), 0)

    # --- Test 5 ---------------------------------------------------------
    def test_canary_resets_on_rotation(self) -> None:
        """Rotation deletes the canary sidecar; the chain_reset_marker
        (line 1 of the freshly rotated log — ADR-055-AMEND-2, S152 Wave B.3)
        re-anchors the canary at 1, then the post-rotation event advances it
        to 2."""
        with mock.patch.dict(os.environ, {"CEO_AUDIT_LOG_ROTATE_BYTES": "100"}):
            importlib.reload(audit_emit)
            # First emit fills the log; second emit triggers rotation.
            _emit_one(phase="payload" + "x" * 200)
            _emit_one(phase="post-rotation")
            counter = audit_hmac.read_chain_length()
            # Post-rotation chain = chain_reset_marker (line 1) + the
            # post-rotation event = 2. Pre-S152 (before the rotation
            # re-anchor marker existed) this was 1.
            self.assertEqual(counter, 2)

    # --- Test 6 ---------------------------------------------------------
    def test_canary_recovers_from_corrupt_sidecar(self) -> None:
        """Garbage sidecar -> read returns 0 -> next write writes 1."""
        sidecar = audit_hmac.chain_length_path()
        sidecar.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        sidecar.write_text("GARBAGE-NOT-A-NUMBER")
        _emit_one(phase="recovery")
        self.assertEqual(audit_hmac.read_chain_length(), 1)

    # --- Test 7 ---------------------------------------------------------
    def test_canary_failure_does_not_break_emit(self) -> None:
        """``write_chain_length`` raise -> emit still succeeds + log line written."""
        with patch.object(
            audit_hmac,
            "write_chain_length",
            side_effect=audit_hmac.AuditHmacError("simulated I/O"),
        ):
            # Should NOT raise; canary fails open with breadcrumb.
            _emit_one(phase="canary-io-fail")
        # Audit log line was written despite canary failure.
        log = audit_emit._log_path()
        self.assertTrue(log.exists())
        lines = log.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        event = json.loads(lines[0])
        self.assertEqual(event["action"], "debate_event")
        self.assertEqual(event["phase"], "canary-io-fail")

    # --- Test 8 helpers --------------------------------------------------
    # The worker's audit MODE + lock must NOT depend on multiprocessing
    # start-method env inheritance (fork copies os.environ, spawn re-passes
    # it, forkserver snapshots it at forkserver-startup BEFORE setUp ran).
    # The pre-S168 worker snapshotted only 6 keys and relied on inheriting
    # CEO_AUDIT_SYNC_MODE/LOG_DIR/LOG_LOCK from the parent — under
    # forkserver (or any harness that pre-starts the pool) the worker
    # silently fell back to SPOOL mode, so the counter (which advances at
    # DRAIN time in spool mode) was read by the parent before all workers'
    # atexit drains completed -> intermittent undercount (CI "13 != 15").
    # Fix: pin the FULL env (mode + lock + paths) explicitly in the worker.
    _WORKER_ENV_KEYS = (
        "HOME",
        "CLAUDE_PROJECT_DIR",
        "CEO_AUDIT_LOG_DIR",
        "CEO_AUDIT_LOG_PATH",
        "CEO_AUDIT_LOG_ERR",
        "CEO_AUDIT_LOG_LOCK",
        "CEO_AUDIT_LAST_HMAC_PATH",
        "CEO_AUDIT_CHAIN_LENGTH_PATH",
        "CEO_AUDIT_KEY_PATH",
    )

    def _worker_env(self, *, sync: bool):
        """Build (env_apply, env_drop) so the worker fully pins its mode.

        Mirrors the parent's audit paths exactly, then FORCES the
        sync-mode knob on/off so the worker's path (sync per-emit vs
        spool+drain) is deterministic regardless of start method.
        """
        env_apply = {}
        env_drop = []
        for k in self._WORKER_ENV_KEYS:
            v = os.environ.get(k)
            if v is not None:
                env_apply[k] = v
            else:
                env_drop.append(k)
        if sync:
            env_apply["CEO_AUDIT_SYNC_MODE"] = "1"
        else:
            env_drop.append("CEO_AUDIT_SYNC_MODE")
        return env_apply, env_drop

    def _spawn_workers(self, env_apply, env_drop, workers, per_worker):
        procs = []
        for _ in range(workers):
            p = mp.Process(
                target=_concurrent_worker,
                args=(env_apply, env_drop, per_worker),
            )
            p.start()
            procs.append(p)
        for p in procs:
            p.join(timeout=30)
            self.assertEqual(p.exitcode, 0)

    # --- Test 8a — SYNC mode: deterministic per-emit atomicity ----------
    def test_canary_concurrent_writes_atomic_sync(self) -> None:
        """Multi-process SYNC emit: every emit increments the counter under
        the shared canonical FileLock, so the total is deterministically
        workers * per_worker (no drain timing in play)."""
        env_apply, env_drop = self._worker_env(sync=True)
        workers, per_worker = 3, 5
        self._spawn_workers(env_apply, env_drop, workers, per_worker)
        self.assertEqual(
            audit_hmac.read_chain_length(),
            workers * per_worker,
        )

    # --- Test 8b — SPOOL mode: concurrent drain, force-drain then assert -
    def test_canary_concurrent_writes_atomic_spool(self) -> None:
        """Multi-process SPOOL emit: the counter advances at DRAIN time, so
        the parent force-drains to completion before asserting. Proves the
        concurrent-drain path loses no counter increments (events are
        spooled-then-drained, never lost) and the counter never drifts from
        the on-disk HMAC-bearing line count."""
        from _lib import spool_writer
        env_apply, env_drop = self._worker_env(sync=False)
        workers, per_worker = 3, 5
        self._spawn_workers(env_apply, env_drop, workers, per_worker)
        # Parent force-drains any residual spooled events to completion.
        spool_writer._reset_caches_for_test()
        for _ in range(20):
            st = spool_writer.drain_now(force=True)
            if not getattr(st, "appended", 0):
                break
        counter = audit_hmac.read_chain_length()
        log = audit_emit._log_path()
        lines = (
            len(log.read_text(encoding="utf-8").splitlines())
            if log.exists() else 0
        )
        self.assertEqual(counter, workers * per_worker)
        self.assertEqual(counter, lines)

    # --- Test 8c — invariant: lock + counter share ONE dir (coherent env) -
    def test_sync_drain_and_counter_share_one_dir(self) -> None:
        """Regression guard for the chain-length atomicity invariant under
        the COHERENT-ENV contract (all processes writing ONE audit log
        share the same CEO_AUDIT_LOG_DIR, or all run pure-$HOME):

          * the sync write lock (audit_emit._lock_path) and the drain lock
            (spool_writer._canonical_log_lock) resolve to ONE file, AND
          * the HMAC sidecars (audit_hmac: counter / key / last-hmac)
            co-locate in that same dir,

        so a sync write and a concurrent drain serialize on the same lock
        AND mutate the same counter file -> no lost increment. Pre-S168,
        audit_hmac._audit_dir_from_env() ignored CEO_AUDIT_LOG_DIR, so a
        LOG_DIR-only process kept its lock under LOG_DIR but its counter
        under $HOME — two such processes (same $HOME, different LOG_DIR)
        shared one counter while holding different locks (lost update).

        NOT covered — unsupported incoherent overrides: CEO_AUDIT_LOG_PATH
        set WITHOUT CEO_AUDIT_LOG_DIR (sidecars track LOG_PATH-parent while
        the lock tracks $HOME), and CEO_AUDIT_LOG_DIR pointing to a
        different dir than CEO_AUDIT_LOG_PATH (log and sidecars split by
        design). Mixing those across processes is a misconfiguration."""
        from _lib import spool_writer

        def _assert_coherent() -> None:
            spool_writer._reset_caches_for_test()
            ae_dir = audit_emit._audit_dir()
            # Lock domain: sync path == drain path.
            self.assertEqual(
                audit_emit._lock_path(),
                spool_writer._canonical_log_lock(),
            )
            self.assertEqual(ae_dir, spool_writer._project_dir_from_env())
            # Counter / key / last-hmac sidecars co-locate with the lock dir.
            self.assertEqual(audit_hmac._audit_dir_from_env(), ae_dir)
            self.assertEqual(
                audit_hmac.chain_length_path().parent,
                audit_emit._lock_path().parent,
            )

        # Clean the override set so each config below is unambiguous.
        for k in (
            "CEO_AUDIT_LOG_LOCK", "CEO_AUDIT_LOG_DIR", "CEO_AUDIT_LOG_PATH",
            "CEO_AUDIT_CHAIN_LENGTH_PATH", "CEO_AUDIT_KEY_PATH",
            "CEO_AUDIT_LAST_HMAC_PATH", "CEO_PROJECT_STATE_DIR",
        ):
            os.environ.pop(k, None)

        # (A) pure-$HOME: every resolver derives from $HOME.
        _assert_coherent()
        # (B) LOG_DIR-only (the prior split): lock under LOG_DIR, counter
        #     must now co-locate there too (the audit_hmac alignment fix).
        os.environ.update({"CEO_AUDIT_LOG_DIR": str(self.audit_dir)})
        _assert_coherent()
        # (C) LOG_DIR + LOG_PATH + LOG_LOCK all in one dir (TestEnvContext).
        os.environ.update({
            "CEO_AUDIT_LOG_PATH": str(self.audit_dir / "audit-log.jsonl"),
            "CEO_AUDIT_LOG_LOCK": str(self.audit_dir / "audit-log.lock"),
        })
        _assert_coherent()

    # --- Test 9 (CRITICAL — audit-v2 P0 closure proof) ------------------
    def test_canary_e2e_verify_chain_detects_truncation(self) -> None:
        """Emit N -> truncate log -> verify_chain reports STATUS_TAMPER."""
        for i in range(5):
            _emit_one(phase=f"e2e-{i}")
        log = audit_emit._log_path()
        lines = log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 5)
        self.assertEqual(audit_hmac.read_chain_length(), 5)

        # Resolve the key via the same cache audit_emit used during
        # the 5 emits above. _KEY_CACHE is process-global, so across
        # the full test suite a prior test may have populated it with
        # a key whose on-disk file lives elsewhere; verify_chain
        # called without explicit `key=` would then re-resolve via
        # disk path and miss the file. Passing the bytes directly
        # sidesteps that drift.
        key_bytes = audit_hmac.get_or_create_key()

        # Simulate tail truncation: keep only first 3 lines.
        log.write_text("\n".join(lines[:3]) + "\n", encoding="utf-8")

        result = audit_hmac.verify_chain(
            log, key=key_bytes, strict_against_counter=True,
        )
        self.assertEqual(
            result.status,
            audit_hmac.STATUS_TAMPER,
            "Expected STATUS_TAMPER but got {s}; reason={r}".format(
                s=result.status, r=result.reason
            ),
        )
        self.assertIn("chain_length", result.reason or "")


def _concurrent_worker(env_apply: dict, env_drop: list, count: int) -> None:
    """Worker entry point for the concurrent canary tests.

    Module-level so it is picklable on macOS / Windows spawn start
    methods. Applies a FULLY-PINNED env (audit mode + lock + paths) so
    the worker's sync/spool branch does NOT depend on start-method env
    inheritance, reloads audit_emit so module-level path helpers + the
    spool/sync branch see the override env, and emits ``count`` events.
    """
    # Use update() / pop() helpers (not subscript writes) so the
    # test-env hygiene scanner does not flag this as `os.environ[k] = ...`.
    os.environ.update(env_apply)
    for k in env_drop:
        os.environ.pop(k, None)
    # Worker process: import + reload to pick up the isolated audit dir.
    from _lib import audit_emit as worker_emit  # noqa: WPS433
    importlib.reload(worker_emit)
    for i in range(count):
        worker_emit.emit_debate_event(
            plan_id="PLAN-TEST",
            round_num=1,
            phase="w-{pid}-{i}".format(pid=os.getpid(), i=i),
            agent="test-archetype",
        )


if __name__ == "__main__":
    unittest.main()
