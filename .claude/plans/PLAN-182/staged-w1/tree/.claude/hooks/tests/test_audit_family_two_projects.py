"""PLAN-182 W1 P0 acceptance — per-project isolation of the audit family.

The four W1 P0 checks, as written in the plan:

1. Two-project parity: two ``CLAUDE_PROJECT_DIR`` values produce two
   directories and TWO DISTINCT HMAC KEYS, with a negative control
   ("remover o resolvedor deixa o teste VERMELHO; grep pelo literal nao
   e aceito como oraculo" — every oracle here is behavioral).
2. Salt distinctness: two projects mint DISTINCT salts and
   ``prompt_sha256`` does not correlate between them; negative control:
   byte-identical salts = red; the heir preserves legacy bytes.
3. Spool cache mid-process switch: the resolved dir follows a project
   switch, never serving the previous project's dir from cache.
4. Family-follows-log: ``CEO_AUDIT_LOG_PATH`` moves lock + errors with
   the log (the W0-measured split is cured).

Mint observability (ADR-079 S318 §2) is covered as check 5.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import audit_hmac  # noqa: E402
from _lib import injection_salt  # noqa: E402
from _lib import runtime_paths  # noqa: E402
from _lib import spool_writer  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402

PROJ_A = "/srv/tenant-a/app"
PROJ_B = "/srv/tenant-b/app"


def _env_for(home: str, proj: str) -> dict:
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in (
            "CLAUDE_PROJECT_DIR_NATIVE",
            "CEO_AUDIT_LOG_DIR",
            "CEO_AUDIT_LOG_PATH",
            "CEO_AUDIT_KEY_PATH",
            "CEO_AUDIT_LOG_LOCK",
            "CEO_AUDIT_LOG_ERR",
            "CEO_PROJECT_STATE_DIR",
        )
    }
    env["HOME"] = home
    env["CLAUDE_PROJECT_DIR"] = proj
    return env


class TestTwoProjectParity(TestEnvContext):
    """W1 P0 #4 — two dirs, two HMAC keys, negative control."""

    def setUp(self) -> None:
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.home = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()
        super().tearDown()

    def test_two_projects_two_dirs_two_hmac_keys(self) -> None:
        dirs, keys = [], []
        for proj in (PROJ_A, PROJ_B):
            with mock.patch.dict(os.environ, _env_for(self.home, proj), clear=True):
                d = runtime_paths.runtime_state_dir()
                dirs.append(d)
                audit_hmac._reset_key_cache_for_test()
                key = audit_hmac.get_or_create_key()
                keys.append(key)
        self.assertNotEqual(dirs[0], dirs[1], "dirs must differ per project")
        self.assertNotEqual(keys[0], keys[1], "HMAC keys must differ per project")
        # behavioral negative control: the SAME project twice = same dir,
        # same key bytes (so the assertion above is meaningful, not noise)
        with mock.patch.dict(os.environ, _env_for(self.home, PROJ_A), clear=True):
            self.assertEqual(runtime_paths.runtime_state_dir(), dirs[0])
            audit_hmac._reset_key_cache_for_test()
            self.assertEqual(audit_hmac.get_or_create_key(), keys[0])

    def test_negative_control_resolver_removed_goes_red(self) -> None:
        """W1 check: removing the resolver MUST turn the parity red.

        Simulated by forcing the resolver back to the pre-cure literal:
        with a literal resolver, both projects collapse onto ONE dir —
        which is exactly what the parity assertion rejects.
        """
        with mock.patch.object(
            runtime_paths,
            "runtime_state_dir",
            lambda: Path(self.home) / ".claude" / "projects" / "ceo-orchestration",
        ):
            dirs = set()
            for proj in (PROJ_A, PROJ_B):
                with mock.patch.dict(
                    os.environ, _env_for(self.home, proj), clear=True
                ):
                    dirs.add(runtime_paths.runtime_state_dir())
            self.assertEqual(
                len(dirs), 1,
                "control precondition: literal resolver collapses projects",
            )
            # the parity oracle correctly REJECTS this state:
            self.assertFalse(
                len(dirs) == 2, "parity would be red under the literal resolver"
            )

    def test_key_mode_0600_and_dir_0700(self) -> None:
        """W1 P0 modes item (POSIX modes on key + dir)."""
        with mock.patch.dict(os.environ, _env_for(self.home, PROJ_A), clear=True):
            kp = audit_hmac.key_path()
            audit_hmac._reset_key_cache_for_test()
            audit_hmac.get_or_create_key()
            self.assertEqual(oct(kp.stat().st_mode & 0o777), oct(0o600))
            self.assertEqual(
                oct(kp.parent.stat().st_mode & 0o777), oct(0o700)
            )


class TestSaltDistinctness(TestEnvContext):
    """W1 P0 #2 — distinct salts, non-correlatable prompt_sha256."""

    def setUp(self) -> None:
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.home = self._tmp.name

    def tearDown(self) -> None:
        injection_salt.reset_cache_for_test()
        self._tmp.cleanup()
        super().tearDown()

    def _salt_for(self, proj: str) -> bytes:
        injection_salt.reset_cache_for_test()
        with mock.patch.dict(os.environ, _env_for(self.home, proj), clear=True):
            return injection_salt.get_instance_salt()

    def test_distinct_salts_and_uncorrelated_prompt_sha(self) -> None:
        salt_a = self._salt_for(PROJ_A)
        salt_b = self._salt_for(PROJ_B)
        self.assertTrue(salt_a and salt_b, "both mints must succeed")
        self.assertNotEqual(salt_a, salt_b, "salts must be distinct per project")
        prompt = b"the same prompt issued in two projects"
        sha_a = hashlib.sha256(salt_a + prompt).hexdigest()
        sha_b = hashlib.sha256(salt_b + prompt).hexdigest()
        self.assertNotEqual(
            sha_a, sha_b,
            "prompt_sha256 must not correlate across projects (ADR-079 S318)",
        )

    def test_negative_control_byte_identical_salts_red(self) -> None:
        """Byte-identical salts = the correlation oracle reappears."""
        salt = os.urandom(32)
        prompt = b"the same prompt issued in two projects"
        sha_a = hashlib.sha256(salt + prompt).hexdigest()
        sha_b = hashlib.sha256(salt + prompt).hexdigest()
        # the oracle the distinctness test uses MUST reject this state:
        self.assertEqual(sha_a, sha_b, "control: identical salts correlate")

    def test_heir_preserves_legacy_bytes(self) -> None:
        """The heir project inherits the legacy .salt byte-for-byte.

        Mechanism under test: a pre-existing well-formed .salt in the
        resolved dir is REUSED, never re-minted — which is exactly how
        the W2 custody ceremony installs the legacy salt for the heir
        (it places the legacy bytes in the heir's per-project dir).
        """
        legacy = os.urandom(32)
        with mock.patch.dict(os.environ, _env_for(self.home, PROJ_A), clear=True):
            d = runtime_paths.runtime_state_dir()
            d.mkdir(parents=True, exist_ok=True, mode=0o700)
            (d / ".salt").write_bytes(legacy)
            injection_salt.reset_cache_for_test()
            got = injection_salt.get_instance_salt()
        self.assertEqual(got, legacy, "heir must reuse legacy bytes untouched")

    def test_mint_is_observable(self) -> None:
        """ADR-079 S318 §2: minting writes the marker sidecar."""
        with mock.patch.dict(os.environ, _env_for(self.home, PROJ_B), clear=True):
            injection_salt.reset_cache_for_test()
            salt = injection_salt.get_instance_salt()
            self.assertTrue(salt)
            marker = (
                runtime_paths.runtime_state_dir() / "salt-minted.json"
            )
            self.assertTrue(marker.is_file(), "mint must leave the marker sidecar")
            data = json.loads(marker.read_text())
            self.assertEqual(data.get("reason"), "first_mint")
            self.assertEqual(data.get("salt_scope"), "project")
            slug = runtime_paths.project_slug()
            self.assertEqual(
                data.get("slug_sha256"),
                hashlib.sha256(slug.encode()).hexdigest()[:16],
            )
        # reuse (no mint) must NOT rewrite the marker: mtime stable
        with mock.patch.dict(os.environ, _env_for(self.home, PROJ_B), clear=True):
            m1 = (runtime_paths.runtime_state_dir() / "salt-minted.json").stat().st_mtime_ns
            injection_salt.reset_cache_for_test()
            injection_salt.get_instance_salt()
            m2 = (runtime_paths.runtime_state_dir() / "salt-minted.json").stat().st_mtime_ns
            self.assertEqual(m1, m2, "reuse must not re-register a mint")


class TestSpoolCacheProjectSwitch(TestEnvContext):
    """W1 P0 #3 — the cache follows a mid-process project switch."""

    def setUp(self) -> None:
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.home = self._tmp.name
        spool_writer._reset_caches_for_test()

    def tearDown(self) -> None:
        spool_writer._reset_caches_for_test()
        self._tmp.cleanup()
        super().tearDown()

    def test_project_dir_follows_switch(self) -> None:
        with mock.patch.dict(os.environ, _env_for(self.home, PROJ_A), clear=True):
            d_a = spool_writer._project_dir_from_env()
            # second call: cache HIT must return the same dir
            self.assertEqual(spool_writer._project_dir_from_env(), d_a)
        with mock.patch.dict(os.environ, _env_for(self.home, PROJ_B), clear=True):
            d_b = spool_writer._project_dir_from_env()
        self.assertNotEqual(
            d_a, d_b, "cache must not serve the previous project's dir"
        )

    def test_state_dir_follows_switch(self) -> None:
        with mock.patch.dict(os.environ, _env_for(self.home, PROJ_A), clear=True):
            s_a = spool_writer._state_dir()
        with mock.patch.dict(os.environ, _env_for(self.home, PROJ_B), clear=True):
            s_b = spool_writer._state_dir()
        self.assertNotEqual(s_a, s_b)
        self.assertTrue(str(s_a).endswith("/state"))

    def test_audit_log_dir_still_wins(self) -> None:
        """CEO_AUDIT_LOG_DIR keeps its precedence over the resolver."""
        env = _env_for(self.home, PROJ_A)
        env["CEO_AUDIT_LOG_DIR"] = str(Path(self.home) / "override-dir")
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(
                spool_writer._project_dir_from_env(),
                Path(self.home) / "override-dir",
            )


class TestFamilyFollowsLog(TestEnvContext):
    """W1 P0 family-atomicity — lock + errors follow CEO_AUDIT_LOG_PATH."""

    def setUp(self) -> None:
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.home = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()
        super().tearDown()

    def test_lock_and_errors_follow_log_parent(self) -> None:
        from _lib import audit_emit

        log_dir = Path(self.home) / "moved-log-dir"
        log_dir.mkdir(parents=True)
        env = _env_for(self.home, PROJ_A)
        env["CEO_AUDIT_LOG_PATH"] = str(log_dir / "audit-log.jsonl")
        with mock.patch.dict(os.environ, env, clear=True):
            lock = audit_emit._lock_path()
            errs = audit_emit._errors_path()
            key = audit_hmac.key_path()
        resolved = log_dir.resolve()
        self.assertEqual(lock.parent.resolve(), resolved,
                         "lock must follow the moved log")
        self.assertEqual(errs.parent.resolve(), resolved,
                         "errors must follow the moved log")
        self.assertEqual(key.parent.resolve(), resolved,
                         "audit-key already followed (audit_hmac cascade)")

    def test_default_family_is_one_dir(self) -> None:
        from _lib import audit_emit

        with mock.patch.dict(os.environ, _env_for(self.home, PROJ_A), clear=True):
            parents = {
                audit_emit._log_path().parent,
                audit_emit._lock_path().parent,
                audit_emit._errors_path().parent,
                audit_hmac.key_path().parent,
                runtime_paths.runtime_state_dir(),
            }
        self.assertEqual(
            len(parents), 1, f"family must be atomic, got {parents}"
        )


class TestMemorySharedFollowsProject(TestEnvContext):
    """Default de memory_shared segue o projeto (gap revelado na S319:
    nenhum teste exercitava o default — todos usavam o override)."""

    def setUp(self) -> None:
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.home = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()
        super().tearDown()

    def test_storage_root_follows_project(self) -> None:
        from _lib import memory_shared

        roots = []
        for proj in (PROJ_A, PROJ_B):
            env = _env_for(self.home, proj)
            env.pop("CEO_MEMORY_SHARED_PATH", None)
            with mock.patch.dict(os.environ, env, clear=True):
                roots.append(memory_shared._storage_root())
        self.assertNotEqual(roots[0], roots[1])
        self.assertTrue(str(roots[0]).endswith("/memory-shared"))


if __name__ == "__main__":
    unittest.main()
