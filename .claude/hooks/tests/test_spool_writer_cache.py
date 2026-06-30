"""PLAN-111 Wave A — unit tests for spool_writer _state_dir + _project_dir_from_env
cache memoization.

Tests AC-A6 (5 sub-cases incl. dual-variable mutation per debate CF-5),
AC-A6a (permission-error retry per Codex iter-2 P0 #3), AC-A7a-chain
(verify_chain.is_intact via _lib.audit_hmac per Codex iter-2 P1 #1 + debate
SA-K1), AC-A7a-shape (output-shape regression per debate SA-K1 split).

Will land at .claude/hooks/tests/test_spool_writer_cache.py once
Owner GPG-signs PLAN-111/architect/round-1/approved.md.asc.
"""
from __future__ import annotations

import json
import os
import pytest
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from _lib import spool_writer
from _lib.testing import TestEnvContext


class TestStateDirCacheInvalidation(TestEnvContext):
    """AC-A6 — cache invalidation across env-tuple changes."""

    def setUp(self) -> None:
        super().setUp()
        spool_writer._reset_caches_for_test()

    def test_a_cache_hit_returns_same_path(self) -> None:
        """AC-A6 (a): cache HIT returns the same Path instance."""
        p1 = spool_writer._state_dir()
        p2 = spool_writer._state_dir()
        self.assertIs(p1, p2, "cache HIT must return same Path instance")

    def test_b_ceo_audit_log_dir_change_invalidates(self) -> None:
        """AC-A6 (b): CEO_AUDIT_LOG_DIR mutation invalidates cache."""
        p1 = spool_writer._state_dir()
        new_dir = self._tmp_root / "new-audit-dir"
        new_dir.mkdir(parents=True, exist_ok=True)
        os.environ["CEO_AUDIT_LOG_DIR"] = str(new_dir)
        p2 = spool_writer._state_dir()
        self.assertIsNot(p1, p2, "different CEO_AUDIT_LOG_DIR must miss cache")
        self.assertEqual(p2, new_dir / "state",
                         "new path must reflect new CEO_AUDIT_LOG_DIR")

    def test_c_home_change_invalidates(self) -> None:
        """AC-A6 (c): HOME mutation invalidates cache (no CEO_AUDIT_LOG_DIR)."""
        del os.environ["CEO_AUDIT_LOG_DIR"]
        spool_writer._reset_caches_for_test()
        new_home = self._tmp_root / "new-home"
        new_home.mkdir(parents=True, exist_ok=True)
        os.environ["HOME"] = str(self.home_dir)
        p1 = spool_writer._state_dir()
        os.environ["HOME"] = str(new_home)
        p2 = spool_writer._state_dir()
        self.assertIsNot(p1, p2, "different HOME must miss cache")
        self.assertIn(str(new_home), str(p2),
                      "new path must derive from new HOME")

    def test_d_explicit_reset_clears(self) -> None:
        """AC-A6 (d): _reset_caches_for_test() clears the cache."""
        p1 = spool_writer._state_dir()
        spool_writer._reset_caches_for_test()
        p2 = spool_writer._state_dir()
        self.assertIsNot(p1, p2,
                         "explicit reset followed by re-resolve must not be cache HIT")
        self.assertEqual(p1, p2,
                         "same env-tuple post-reset must resolve to equal path")

    def test_e_dual_variable_mutation_kills_tuple_reversal(self) -> None:
        """AC-A6 (e) (debate CF-5 / qa M2): dual-variable test kills the
        mutant that keys cache on (HOME, CEO_AUDIT_LOG_DIR) reversed.

        Set both CEO_AUDIT_LOG_DIR=/tmp/dirA AND HOME=/tmp/homeA, prime
        cache. Change ONLY CEO_AUDIT_LOG_DIR=/tmp/dirB (keep HOME=/tmp/homeA).
        Assert cache MISS and returned Path reflects dirB (NOT dirA, NOT homeA).
        """
        dir_a = self._tmp_root / "dirA"
        dir_a.mkdir(parents=True, exist_ok=True)
        home_a = self._tmp_root / "homeA"
        home_a.mkdir(parents=True, exist_ok=True)
        os.environ["CEO_AUDIT_LOG_DIR"] = str(dir_a)
        os.environ["HOME"] = str(home_a)
        spool_writer._reset_caches_for_test()
        p1 = spool_writer._state_dir()
        self.assertEqual(p1, dir_a / "state",
                         "primed cache path must reflect dirA")

        # Mutate ONLY CEO_AUDIT_LOG_DIR; keep HOME=homeA
        dir_b = self._tmp_root / "dirB"
        dir_b.mkdir(parents=True, exist_ok=True)
        os.environ["CEO_AUDIT_LOG_DIR"] = str(dir_b)
        p2 = spool_writer._state_dir()
        self.assertEqual(p2, dir_b / "state",
                         "new path must reflect dirB (NOT dirA, NOT homeA)")
        self.assertNotEqual(p2, dir_a / "state",
                            "cache must NOT return stale dirA path")


class TestStateDirCacheRetryOnFailure(TestEnvContext):
    """AC-A6a (Codex iter-2 P0 #3) — cache MUST NOT store Path on mkdir failure."""

    def setUp(self) -> None:
        super().setUp()
        spool_writer._reset_caches_for_test()

    def test_mkdir_failure_does_not_cache_then_retry_succeeds(self) -> None:
        """Patch Path.mkdir to raise OSError once; verify next call retries.

        Sequence:
          1. Patch Path.mkdir to raise PermissionError.
          2. Call _state_dir() -> mkdir fails -> path NOT cached.
          3. Unpatch.
          4. Call _state_dir() -> mkdir succeeds -> path cached.
          5. Verify _STATE_DIR_CACHE is now populated.
        """
        # Step 1+2: patched mkdir raises
        original_mkdir = Path.mkdir
        call_count = [0]

        def _patched_mkdir(self_p, *args, **kwargs):
            call_count[0] += 1
            raise PermissionError(f"simulated failure #{call_count[0]}")

        with patch.object(Path, "mkdir", _patched_mkdir):
            spool_writer._state_dir()  # mkdir fails, no breadcrumb raise
            self.assertIsNone(
                spool_writer._STATE_DIR_CACHE,
                "cache must NOT store Path when mkdir fails",
            )

        # Step 4+5: unpatched, retry succeeds
        p = spool_writer._state_dir()
        self.assertIsNotNone(
            spool_writer._STATE_DIR_CACHE,
            "cache MUST store Path after successful mkdir on retry",
        )
        self.assertIsNotNone(p, "retry must return a real Path")


class TestStateDirPermissionReAssertion(TestEnvContext):
    """SA-K10 / security R-SE3 — cache MISS must validate state/ via lstat
    + uid + mode 0o700; on mismatch raise PermissionError (fail-CLOSED per
    Codex R2 P0 fix; detection-without-rejection was fake-security).
    """

    def setUp(self) -> None:
        super().setUp()
        spool_writer._reset_caches_for_test()

    def test_symlink_at_state_dir_raises_and_blocks_writes(self) -> None:
        """state/ as symlink → raises PermissionError → no spool/journal/
        lock files created under the attacker-controlled target (Codex R2 P0)."""
        # Create state/ as a symlink pointing somewhere else (attacker-controlled)
        target_dir = self._tmp_root / "evil-target"
        target_dir.mkdir(parents=True, exist_ok=True)
        state_path = self.audit_dir / "state"
        if state_path.exists():
            if state_path.is_dir() and not state_path.is_symlink():
                shutil.rmtree(state_path)
            else:
                state_path.unlink()
        state_path.symlink_to(target_dir, target_is_directory=True)

        # _state_dir() MUST raise PermissionError (fail-CLOSED)
        with self.assertRaises(PermissionError) as cm:
            spool_writer._state_dir()
        self.assertIn("is_symlink", str(cm.exception))

        # Cache must NOT contain the symlink path
        self.assertIsNone(
            spool_writer._STATE_DIR_CACHE,
            "symlink at state/ must NOT be cached",
        )

        # Verify NO files were created in the attacker-controlled target
        # by the failed _state_dir() call. (The target may contain test-
        # fixture pre-existing entries; we just verify it's empty.)
        target_entries = list(target_dir.iterdir())
        self.assertEqual(
            target_entries, [],
            f"attacker target should be empty; got: {target_entries}"
        )


class TestStateDirModeSelfHeal(TestEnvContext):
    """PLAN-113 W4-SEC — _state_dir() SA-K10 self-heal.

    A pre-existing state/ dir at a mode != 0o700 (commonly 0o755 from an
    older code path; exist_ok=True does NOT relax perms) previously
    fail-CLOSED on every call, dropping the audit event + flooding the
    spool. The self-heal chmods 0o700 + re-validates, then PROCEEDS.
    Symlink / wrong-owner cases MUST still fail-CLOSED (never
    chmod-and-trust an attacker-controlled or other-owned dir).
    """

    def setUp(self) -> None:
        super().setUp()
        spool_writer._reset_caches_for_test()

    def test_a_preexisting_0755_dir_self_heals_and_writes(self) -> None:
        """(a) pre-existing state/ at 0o755 → healed to 0o700 + event written."""
        import stat as _stat_mod

        # Create state/ at the WRONG mode (0o755) BEFORE _state_dir runs.
        state_path = self.audit_dir / "state"
        if state_path.exists():
            shutil.rmtree(state_path)
        state_path.mkdir(parents=True, exist_ok=True)
        os.chmod(str(state_path), 0o755)
        self.assertEqual(
            os.lstat(str(state_path)).st_mode & 0o777, 0o755,
            "fixture must start at 0o755",
        )

        # _state_dir() must NOT raise — it self-heals + caches.
        d = spool_writer._state_dir()
        self.assertEqual(d, state_path)
        self.assertEqual(
            os.lstat(str(d)).st_mode & 0o777, 0o700,
            "state/ must be chmod-healed to 0o700",
        )
        self.assertIsNotNone(
            spool_writer._STATE_DIR_CACHE,
            "healed state/ must be cached",
        )
        self.assertFalse(
            _stat_mod.S_ISLNK(os.lstat(str(d)).st_mode),
            "healed dir must not be a symlink",
        )

        # End-to-end: a spool_append now lands an event (no flood / no drop).
        spool_writer.spool_append({"action": "selfheal_probe", "x": 1})
        self.assertTrue(
            spool_writer.last_append_succeeded(),
            "append must succeed after state/ self-heal",
        )
        spool_p = spool_writer._spool_path(os.getpid())
        self.assertTrue(spool_p.exists(), "spool file must exist post-append")
        body = spool_p.read_text(encoding="utf-8")
        self.assertIn("selfheal_probe", body)

    def test_b_symlink_still_fails_closed_no_chmod(self) -> None:
        """(b) state/ as a symlink → still fail-CLOSED; chmod-and-trust NEVER
        applied to a symlink (attacker-controlled target untouched)."""
        target_dir = self._tmp_root / "evil-target-selfheal"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_mode_before = os.lstat(str(target_dir)).st_mode & 0o777

        state_path = self.audit_dir / "state"
        if state_path.exists():
            if state_path.is_dir() and not state_path.is_symlink():
                shutil.rmtree(state_path)
            else:
                state_path.unlink()
        state_path.symlink_to(target_dir, target_is_directory=True)

        with self.assertRaises(PermissionError) as cm:
            spool_writer._state_dir()
        self.assertIn("is_symlink", str(cm.exception))

        # The symlink target must be untouched (no chmod of the symlink's
        # destination) and the symlink must NOT be cached.
        self.assertEqual(
            os.lstat(str(target_dir)).st_mode & 0o777, target_mode_before,
            "self-heal must NOT chmod a symlink's target",
        )
        self.assertIsNone(
            spool_writer._STATE_DIR_CACHE,
            "symlink at state/ must NOT be cached",
        )

    def test_c_other_owner_still_fails_closed_no_chmod(self) -> None:
        """(c) state/ owned by a DIFFERENT uid → still fail-CLOSED; the
        self-heal chmod is NEVER attempted on an other-owned dir.

        Simulated by monkeypatching os.lstat to report a foreign uid and a
        0o755 mode, and asserting os.chmod is never called.
        """
        state_path = self.audit_dir / "state"
        if state_path.exists():
            shutil.rmtree(state_path)
        # Real dir at 0o700 so mkdir(exist_ok) succeeds; lstat is faked.
        state_path.mkdir(parents=True, exist_ok=True)
        os.chmod(str(state_path), 0o700)

        foreign_uid = os.getuid() + 12345

        class _FakeStat:
            # A regular directory (S_IFDIR) at mode 0o755 owned by foreign uid.
            st_mode = 0o040755
            st_uid = foreign_uid

        real_lstat = os.lstat
        target_str = str(state_path)
        chmod_calls = []

        def _fake_lstat(path, *a, **kw):
            if str(path) == target_str:
                return _FakeStat()
            return real_lstat(path, *a, **kw)

        real_chmod = os.chmod

        def _spy_chmod(path, mode, *a, **kw):
            chmod_calls.append((str(path), mode))
            return real_chmod(path, mode, *a, **kw)

        with patch.object(os, "lstat", _fake_lstat), \
                patch.object(os, "chmod", _spy_chmod):
            with self.assertRaises(PermissionError) as cm:
                spool_writer._state_dir()
        self.assertIn("uid_mismatch", str(cm.exception))

        # The self-heal chmod must NOT have been attempted on the
        # other-owned state/ dir.
        self.assertNotIn(
            target_str, [c[0] for c in chmod_calls],
            "self-heal must NOT chmod an other-owned state/ dir",
        )
        self.assertIsNone(
            spool_writer._STATE_DIR_CACHE,
            "other-owned state/ must NOT be cached",
        )

    def test_d_chmod_failure_keeps_fail_closed(self) -> None:
        """A mode-mismatch where the self-heal fchmod itself fails (OSError)
        must keep the SA-K10 fail-CLOSED (no cache, raises).

        PLAN-113 Codex B3 P2: the self-heal is now fd-based
        (os.open(O_NOFOLLOW|O_DIRECTORY) + os.fchmod), so the failure is
        simulated by making os.fchmod raise (the path-based os.chmod is no
        longer on the heal path)."""
        state_path = self.audit_dir / "state"
        if state_path.exists():
            shutil.rmtree(state_path)
        state_path.mkdir(parents=True, exist_ok=True)
        os.chmod(str(state_path), 0o755)

        def _failing_fchmod(fd, mode, *a, **kw):
            raise PermissionError("simulated fchmod failure")

        with patch.object(os, "fchmod", _failing_fchmod):
            with self.assertRaises(PermissionError) as cm:
                spool_writer._state_dir()
        # Either the chmod's own error or the subsequent mode_mismatch
        # re-assertion — both are fail-CLOSED PermissionErrors.
        self.assertIsInstance(cm.exception, PermissionError)
        self.assertIsNone(
            spool_writer._STATE_DIR_CACHE,
            "unhealed mode-mismatch state/ must NOT be cached",
        )


# PLAN-135-FOLLOWUP-2 (S234): this class reloads audit_emit + verifies the GLOBAL
# HMAC chain, which is xdist-fragile when a module-reload polluter (e.g.
# test_audit_emit_chain_length) lands on the same worker. It had been passing on
# xdist-distribution luck; adding the FOLLOWUP-2 W5 tests shifted the distribution
# and exposed the latent R-QA1 isolation gap already documented in setUp(). Pin it
# serial so it runs in the dedicated single-process pass (CI runs `-m serial`).
@pytest.mark.serial
class TestSpoolWriterSemanticEquivalence(TestEnvContext):
    """AC-A7a-chain + AC-A7a-shape (debate SA-K1) — semantic-equivalence
    contract: HMAC chain integrity preserved + output-shape preserved
    (excluding non-deterministic fields).
    """

    SYNC_MODE_DEFAULT = True  # need sync for deterministic single-trial line counts

    def setUp(self) -> None:
        super().setUp()
        spool_writer._reset_caches_for_test()
        # Defensive: clear CEO_AUDIT_HMAC_DISABLE which some prior tests
        # in the full suite leave set (debate qa-architect R-QA1 isolation
        # gap). Without this, verify_chain returns key_missing because
        # emit short-circuits HMAC computation when disabled.
        os.environ.pop("CEO_AUDIT_HMAC_DISABLE", None)
        # Defensive: re-import audit_emit fresh because
        # test_audit_emit_chain_length.py:97 calls importlib.reload(audit_emit)
        # which leaves the module cache in an inconsistent state for full-suite
        # runs (debate qa-architect R-QA1). Force a fresh module reference
        # so this test uses a fully-initialized _HMAC_AVAILABLE + _audit_hmac.
        import importlib as _il
        from _lib import audit_emit as _ae
        _il.reload(_ae)

    def _emit_n_events(self, n: int) -> None:
        # Use the freshly-reloaded module to avoid stale state.
        import importlib as _il
        from _lib import audit_emit as _ae
        _il.reload(_ae)
        """Emit n claim_emitted events using the public API."""
        from _lib import audit_emit
        for i in range(n):
            audit_emit.emit_claim_emitted(
                claim_id=f"path_exists:{i:012x}",
                claim_type="path_exists",
                severity="info",
                verifier_kind="path_exists",
                payload_hash=f"{i:012x}",
                kind_supported=True,
                line_num=i,
            )

    def test_chain_intact_after_emits(self) -> None:
        """AC-A7a-chain: verify_chain(path).is_intact is True after 50 emits."""
        import importlib
        from _lib import audit_hmac, audit_emit
        importlib.reload(audit_hmac)
        importlib.reload(audit_emit)
        # Force reset of caches after reload
        spool_writer._reset_caches_for_test()
        self._emit_n_events(50)
        log_path = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        self.assertTrue(log_path.exists(), "audit log must exist post-emit")
        # Re-import for the post-emit verify call
        from _lib import audit_hmac as ah_fresh
        result = ah_fresh.verify_chain(log_path)
        # Surface diagnostics if it fails (debate qa-architect R-QA1)
        if not result.is_intact:
            key = audit_hmac.key_path()
            print(f"DIAG: key_path={key} exists={key.exists()}")
            print(f"DIAG: _HMAC_AVAILABLE={audit_emit._HMAC_AVAILABLE}")
            print(f"DIAG: is_disabled={audit_hmac.is_disabled()}")
            with log_path.open() as f:
                first = f.readline()
            print(f"DIAG: first_event_first_120chars={first[:120]}")
        self.assertTrue(
            result.is_intact,
            f"HMAC chain must verify post-Wave-A; got status={result}"
        )

    def test_output_shape_field_set_excludes_nondeterministic(self) -> None:
        """AC-A7a-shape: every JSONL line has expected domain fields;
        excluding {wall_ns, record_id, spool_uuid, _drain_epoch, ts,
        ordinal_within_file} is allowed cross-run variation."""
        self._emit_n_events(10)
        log_path = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        excluded = {"wall_ns", "record_id", "spool_uuid", "_drain_epoch",
                    "ts", "ordinal_within_file"}
        required_domain_fields = {
            "action", "claim_id", "claim_type", "severity",
            "verifier_kind", "payload_hash", "kind_supported",
        }
        with log_path.open() as f:
            for line in f:
                event = json.loads(line)
                # Every domain field present
                for field in required_domain_fields:
                    self.assertIn(field, event,
                                  f"required domain field {field!r} missing")
                # Excluded fields may or may not be present; shape diff
                # against pre-Wave-A is in AC-A7a-shape semantic equivalence
                # (run in Wave C verification, not here).


if __name__ == "__main__":
    unittest.main()
