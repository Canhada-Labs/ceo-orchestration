"""Tests for `_lib.injection_salt` (PLAN-058 Round-23).

Verifies the per-installation salt module that backs the
``UserPromptSubmit.prompt_sha`` identifier-privacy hardening.

## Coverage matrix

| # | Property                                              | Test                                              |
|---|-------------------------------------------------------|---------------------------------------------------|
| 1 | First call generates salt + persists to disk          | test_first_call_generates_and_persists            |
| 2 | File mode is 0o600 after first call                   | test_persisted_salt_file_mode_is_0o600            |
| 3 | Subsequent calls return cached bytes (no disk I/O)    | test_subsequent_calls_use_cache                   |
| 4 | Salt is exactly 32 bytes                              | test_salt_is_32_bytes                             |
| 5 | Two fresh installations produce different salts       | test_independent_installations_produce_different_salts |
| 6 | Pre-existing well-formed salt file is reused          | test_existing_salt_file_is_reused                 |
| 7 | Corrupt salt (wrong size) triggers regeneration       | test_corrupt_size_triggers_regeneration           |
| 8 | Fail-open: returns b"" when dir cannot be created     | test_fail_open_when_dir_unwritable                |
| 9 | Fail-open: returns b"" when file cannot be written    | test_fail_open_when_file_unwritable               |
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Iterator
from unittest import mock


_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


def _import_module():
    """Reimport injection_salt fresh to reset module cache."""
    if "_lib.injection_salt" in sys.modules:
        del sys.modules["_lib.injection_salt"]
    from _lib import injection_salt  # type: ignore
    return injection_salt


class _IsolatedHomeMixin(unittest.TestCase):
    """Temp HOME + pinned CLAUDE_PROJECT_DIR (PLAN-182 W1 contract).

    The salt unit is the PROJECT (ADR-079 S318 amendment): the file
    lives under the per-project native-slug dir resolved by
    ``_lib/runtime_paths``, no longer under the bare literal. Pinning
    ``CLAUDE_PROJECT_DIR`` keeps the resolved dir independent of the
    test runner's cwd; clearing ``CLAUDE_PROJECT_DIR_NATIVE`` keeps the
    default arm under test.
    """

    _PROJECT_DIR = "/srv/salt-fixture-project"

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._fake_home = Path(self._tmp.name)
        # rail r13: estes testes exercitam o BRACO DEFAULT do resolvedor.
        # Desde a cura de family-atomicity (P1-5) o `.salt` acompanha os
        # overrides de familia — e o conftest da suite SEMPRE seta
        # CEO_AUDIT_LOG_DIR para isolar o audit, o que mandaria o salt
        # para la. Remove-los aqui e o que mantem este arquivo medindo o
        # default; a cobertura do braco COM override esta em
        # test_salt_follows_audit_family_override.
        _FAMILY_OVERRIDES = (
            "CLAUDE_PROJECT_DIR_NATIVE", "CEO_AUDIT_LOG_DIR",
            "CEO_AUDIT_LOG_PATH",
        )
        env = {k: v for k, v in os.environ.items()
               if k not in _FAMILY_OVERRIDES}
        env["HOME"] = str(self._fake_home)
        env["CLAUDE_PROJECT_DIR"] = self._PROJECT_DIR
        self._home_patch = mock.patch.dict(os.environ, env, clear=True)
        self._home_patch.start()
        self.salt_mod = _import_module()
        self.salt_mod.reset_cache_for_test()

    def tearDown(self) -> None:
        self.salt_mod.reset_cache_for_test()
        self._home_patch.stop()
        self._tmp.cleanup()

    def _expected_salt_path(self) -> Path:
        slug = self._PROJECT_DIR.replace("/", "-")
        return (
            self._fake_home
            / ".claude"
            / "projects"
            / slug
            / ".salt"
        )


class TestSaltGeneration(_IsolatedHomeMixin):

    def test_first_call_generates_and_persists(self) -> None:
        path = self._expected_salt_path()
        self.assertFalse(path.exists(), "salt file should not exist pre-call")

        salt = self.salt_mod.get_instance_salt()

        self.assertEqual(len(salt), 32, "salt must be 32 bytes")
        self.assertTrue(path.exists(), "salt file must be persisted")
        self.assertEqual(path.read_bytes(), salt, "on-disk bytes match returned")

    def test_persisted_salt_file_mode_is_0o600(self) -> None:
        self.salt_mod.get_instance_salt()
        path = self._expected_salt_path()
        mode = path.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600, f"salt file mode should be 0o600, got 0o{mode:o}")

    def test_salt_is_32_bytes(self) -> None:
        salt = self.salt_mod.get_instance_salt()
        self.assertEqual(len(salt), 32)

    def test_independent_installations_produce_different_salts(self) -> None:
        # First installation
        salt_a = self.salt_mod.get_instance_salt()

        # rail r13 P2-7: a segunda "instalacao" era montada com
        # clear=False DEPOIS de parar o patch do setUp — qualquer
        # CLAUDE_PROJECT_DIR_NATIVE ambiente voltava a valer e vencia o
        # resolvedor, deixando o teste criar .salt/marker no dir de
        # estado REAL. Agora o ambiente da 2a instalacao e construido a
        # partir do MESMO env minimo do setUp (clear=True), sem depender
        # de parar o patch.
        self.salt_mod.reset_cache_for_test()
        with tempfile.TemporaryDirectory() as tmp_b:
            env_b = {k: v for k, v in os.environ.items()
                     if k not in ("CLAUDE_PROJECT_DIR_NATIVE",
                                  "CEO_AUDIT_LOG_DIR", "CEO_AUDIT_LOG_PATH")}
            env_b["HOME"] = str(tmp_b)
            env_b["CLAUDE_PROJECT_DIR"] = self._PROJECT_DIR
            with mock.patch.dict(os.environ, env_b, clear=True):
                self.salt_mod.reset_cache_for_test()
                salt_b = self.salt_mod.get_instance_salt()

        self.assertNotEqual(
            salt_a, salt_b,
            "two fresh installations must produce different salts"
        )


class TestSaltFollowsAuditFamily(_IsolatedHomeMixin):
    """rail r13 P1-5 — family-atomicity: o `.salt` mora com o LOG.

    Deixa-lo no dir do slug enquanto log/key/lock/errors se mudam por
    override contradiz o ADR-001 S318 item 3 e faria custodia/backup do
    dir efetivo PERDEREM o salt.
    """

    def test_salt_follows_audit_family_override(self) -> None:
        moved = self._fake_home / "moved-family"
        moved.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env["CEO_AUDIT_LOG_DIR"] = str(moved)
        with mock.patch.dict(os.environ, env, clear=True):
            self.salt_mod.reset_cache_for_test()
            salt = self.salt_mod.get_instance_salt()
            self.assertEqual(len(salt), 32)
            self.assertEqual(
                self.salt_mod._salt_path().parent.resolve(),
                moved.resolve(),
                "o .salt tem de acompanhar o dir da familia")
        # controle: sem override, volta para o dir do projeto
        self.salt_mod.reset_cache_for_test()
        self.assertEqual(
            self.salt_mod._salt_path(), self._expected_salt_path())


class TestSaltCaching(_IsolatedHomeMixin):

    def test_subsequent_calls_use_cache(self) -> None:
        salt_first = self.salt_mod.get_instance_salt()

        # Delete the on-disk file: cached value must still be returned
        path = self._expected_salt_path()
        path.unlink()
        self.assertFalse(path.exists())

        salt_second = self.salt_mod.get_instance_salt()
        self.assertEqual(
            salt_first, salt_second,
            "cached salt must be returned even if file is deleted"
        )
        self.assertFalse(
            path.exists(),
            "cache hit must NOT touch the filesystem"
        )

    def test_existing_salt_file_is_reused(self) -> None:
        # Pre-create a valid salt file
        path = self._expected_salt_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        prepared = b"\xaa" * 32
        path.write_bytes(prepared)

        salt = self.salt_mod.get_instance_salt()
        self.assertEqual(salt, prepared, "pre-existing salt must be reused")


class TestSaltCorruption(_IsolatedHomeMixin):

    def test_corrupt_size_triggers_regeneration(self) -> None:
        # Pre-create a corrupt (wrong-size) salt file
        path = self._expected_salt_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"too-short")
        self.assertEqual(len(path.read_bytes()), 9)

        salt = self.salt_mod.get_instance_salt()

        self.assertEqual(len(salt), 32, "regenerated salt must be 32 bytes")
        self.assertEqual(
            path.read_bytes(), salt,
            "regenerated salt must overwrite corrupt file"
        )


class TestFailOpen(_IsolatedHomeMixin):

    def test_fail_open_when_dir_unwritable(self) -> None:
        # Force mkdir to raise OSError
        with mock.patch(
            "pathlib.Path.mkdir", side_effect=OSError("perm denied")
        ):
            salt = self.salt_mod.get_instance_salt()
        self.assertEqual(salt, b"", "must return empty bytes on dir failure")

    def test_fail_open_when_file_unwritable(self) -> None:
        # Allow mkdir to succeed but force the salt WRITE to fail.
        #
        # rc.1 re-pass part 6 C2 — this used to patch `pathlib.Path.write_bytes`,
        # which is the seam the pre-cure code wrote through. The cure writes via
        # `os.open` + `os.fdopen`, so that patch stopped reaching the write path
        # and this test passed while asserting nothing: it was handed a real
        # 32-byte salt and `assertEqual(salt, b"")` failed loudly, which is the
        # only reason the staleness was visible at all. Injecting at `os.open`
        # keeps the fault where the code actually writes.
        path = self._expected_salt_path()
        # First ensure parent exists so the test isolates the write failure
        path.parent.mkdir(parents=True, exist_ok=True)
        _real_open = os.open

        def _fail_on_salt(target, *args, **kwargs):
            if str(target) == str(path):
                raise OSError("disk full")
            return _real_open(target, *args, **kwargs)

        with mock.patch("os.open", side_effect=_fail_on_salt):
            salt = self.salt_mod.get_instance_salt()
        self.assertEqual(salt, b"", "must return empty bytes on write failure")
        self.assertFalse(path.exists(), "a failed mint must leave no salt file")


class TestFirstMintIsExclusive(_IsolatedHomeMixin):
    """rc.1 re-pass part 6 C2 — exactly one process mints; losers re-read.

    Pre-cure, `_generate_and_persist` wrote with `path.write_bytes`, which
    truncates: concurrent first-minters each generated a salt, each cached its
    OWN value, and the file on disk kept whichever write landed last. The
    re-pass measured 5 of 5 rounds with 6 of 6 processes holding distinct
    salts and 5 of them orphaned from the persisted file — every
    `prompt_sha256` those five emitted is irreproducible.
    """

    def test_loser_returns_the_winners_salt_and_registers_no_mint(self) -> None:
        path = self._expected_salt_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        winner = bytes(range(32))
        path.write_bytes(winner)

        # The loser's view of the world: `_read_existing` answered None (it ran
        # before the winner's write landed), so it walks into the mint branch
        # and meets EEXIST there. Patching the reader for ONE call reproduces
        # that interleaving without threads.
        real_read = self.salt_mod._read_existing
        calls = {"n": 0}

        def _first_call_sees_nothing(target):
            calls["n"] += 1
            if calls["n"] == 1:
                return None
            return real_read(target)

        with mock.patch.object(
            self.salt_mod, "_read_existing", side_effect=_first_call_sees_nothing
        ):
            salt = self.salt_mod.get_instance_salt()

        self.assertEqual(
            salt, winner,
            "the loser must return the WINNER's salt, not the one it generated",
        )
        self.assertEqual(
            path.read_bytes(), winner,
            "the loser must not have truncated the winner's file",
        )
        marker = path.parent / "salt-minted.json"
        self.assertFalse(
            marker.exists(),
            "the loser minted nothing and must write no mint marker",
        )

    def test_exclusive_create_is_the_mechanism(self) -> None:
        """The election is O_EXCL, asserted at the syscall, not inferred."""
        path = self._expected_salt_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        seen = []
        _real_open = os.open

        def _record(target, *args, **kwargs):
            if str(target) == str(path) and args:
                seen.append(args[0])
            return _real_open(target, *args, **kwargs)

        with mock.patch("os.open", side_effect=_record):
            salt = self.salt_mod.get_instance_salt()
        self.assertEqual(len(salt), 32)
        self.assertTrue(seen, "the salt was not created through os.open")
        self.assertTrue(
            seen[0] & os.O_EXCL,
            "first mint opened without O_EXCL — two processes can both win",
        )
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        if nofollow:
            self.assertTrue(
                seen[0] & nofollow,
                "first mint opened without O_NOFOLLOW",
            )

    def test_malformed_preexisting_salt_is_still_replaced(self) -> None:
        """O_EXCL must not break the deliberate rotation path."""
        path = self._expected_salt_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"too-short")
        salt = self.salt_mod.get_instance_salt()
        self.assertEqual(len(salt), 32)
        self.assertEqual(path.read_bytes(), salt)
        marker = path.parent / "salt-minted.json"
        self.assertTrue(marker.exists(), "a rotation must still be observable")
        self.assertEqual(
            json.loads(marker.read_text(encoding="utf-8"))["reason"], "other",
            "replacing a malformed salt is a rotation, never a first mint",
        )


class TestMintMarkerDoesNotFollowSymlinks(_IsolatedHomeMixin):
    """rc.1 re-pass part 6 C3 — the marker write refuses a symlinked path.

    Reproduced pre-cure: a symlink planted at `salt-minted.json` had its
    target OUTSIDE the state tree truncated, replaced by the marker JSON, and
    its mode dropped to 0600 through the link.
    """

    def test_symlinked_marker_leaves_the_target_untouched(self) -> None:
        path = self._expected_salt_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        outside = Path(self._tmp.name) / "outside-the-state-tree.txt"
        outside.write_text("ADOPTER BYTES\n", encoding="utf-8")
        before = outside.read_text(encoding="utf-8")
        marker = path.parent / "salt-minted.json"
        marker.symlink_to(outside)
        self.assertTrue(marker.is_symlink(), "fixture: no symlink planted")

        salt = self.salt_mod.get_instance_salt()

        # Salt availability is invariant (ADR-005): the refusal is fail-open.
        self.assertEqual(len(salt), 32, "the marker refusal must not cost the salt")
        self.assertEqual(
            outside.read_text(encoding="utf-8"), before,
            "the symlink target was written through — C3 reproduces",
        )
        self.assertTrue(marker.is_symlink(), "the link itself must be left alone")

    def test_marker_is_written_normally_when_no_link_is_present(self) -> None:
        """Control: without this the refusal test passes on a dead writer."""
        path = self._expected_salt_path()
        salt = self.salt_mod.get_instance_salt()
        self.assertEqual(len(salt), 32)
        marker = path.parent / "salt-minted.json"
        self.assertTrue(marker.exists(), "the marker is not being written at all")
        self.assertFalse(marker.is_symlink())
        body = json.loads(marker.read_text(encoding="utf-8"))
        self.assertEqual(body["reason"], "first_mint")
        # No temporary file survives the atomic replace.
        leftovers = [
            q.name for q in path.parent.iterdir()
            if q.name.startswith(".salt-minted.json.")
        ]
        self.assertEqual(leftovers, [], "an atomic write left a temp file behind")


if __name__ == "__main__":
    unittest.main()
