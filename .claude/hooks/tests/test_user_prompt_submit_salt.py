"""Tests for UserPromptSubmit prompt_sha salt integration (Round-23).

Validates that ``UserPromptSubmit.decide`` invokes
``_lib.injection_salt.get_instance_salt`` and prepends the result to
the prompt before hashing — closing the correlation-oracle attack at
``prompt_sha256`` per PLAN-058 Round-23 / ADR-079.

Distinct from the existing ``test_user_prompt_submit.py`` suite which
mocks ``_emit_prompt_submitted`` with literal kwargs and does not
exercise the computed hash. Here we capture the kwargs passed to the
emitter and assert hash properties.

## Coverage matrix

| # | Property                                              | Test                                              |
|---|-------------------------------------------------------|---------------------------------------------------|
| 1 | Hash differs between two installations (different salts) | test_hash_differs_across_installations         |
| 2 | Hash is stable within one installation               | test_hash_stable_within_installation              |
| 3 | Salted hash differs from unsalted SHA-256 prefix     | test_salted_hash_differs_from_unsalted            |
| 4 | Fail-open: salt module exception → emit still fires  | test_emit_succeeds_when_salt_module_raises        |
"""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


def _import_user_prompt_submit():
    """Reimport hook fresh so module state (including any cached salt) resets.

    The ``_lib`` *package* object is NOT removed from sys.modules.  Removing
    it wipes submodule attributes (e.g. ``audit_emit``) from the
    package object, breaking ``unittest.mock.patch("_lib.audit_emit.emit_*")``
    for any test that runs after this helper.

    Instead we evict only ``_lib.injection_salt`` (forcing a fresh import with
    a reset ``_CACHED_SALT``) and also delete the stale ``injection_salt``
    attribute from the ``_lib`` package so the next ``from _lib import
    injection_salt`` actually re-executes the module code rather than
    returning the cached module object whose ``_CACHED_SALT`` still holds
    the old HOME's salt.
    """
    sys.modules.pop("_lib.injection_salt", None)
    # Also drop the attribute from the _lib package object; otherwise
    # ``from _lib import injection_salt`` returns the cached object even
    # after the sys.modules eviction above.
    _lib_pkg = sys.modules.get("_lib")
    if _lib_pkg is not None:
        try:
            delattr(_lib_pkg, "injection_salt")
        except AttributeError:
            pass
    sys.modules.pop("UserPromptSubmit", None)
    import UserPromptSubmit  # type: ignore
    return UserPromptSubmit


class _IsolatedHomeMixin(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._fake_home = Path(self._tmp.name)
        self._home_patch = mock.patch.dict(
            os.environ, {"HOME": str(self._fake_home)}, clear=False
        )
        self._home_patch.start()
        self.ups = _import_user_prompt_submit()

    def tearDown(self) -> None:
        self._home_patch.stop()
        self._tmp.cleanup()

    def _capture_prompt_sha(self, prompt: str) -> str:
        """Run decide() and return the prompt_sha kwarg passed to the emitter."""
        captured: dict = {}

        def _spy(*, session_id, prompt_len, prompt_sha, redact_hits,
                 injection_counts, repo_root):
            captured["prompt_sha"] = prompt_sha
            captured["prompt_len"] = prompt_len

        with mock.patch.object(self.ups, "_emit_prompt_submitted", _spy):
            self.ups.decide(
                prompt=prompt,
                repo_root=Path("/tmp"),
                session_id="test-session",
            )
        return captured["prompt_sha"]


class TestSaltedHashCorrectness(_IsolatedHomeMixin):

    def test_hash_differs_across_installations(self) -> None:
        prompt = "what is the meaning of life?"
        sha_a = self._capture_prompt_sha(prompt)

        # Tear down + bring up a fresh isolated HOME (new salt)
        self._home_patch.stop()
        with tempfile.TemporaryDirectory() as tmp_b:
            with mock.patch.dict(
                os.environ, {"HOME": str(tmp_b)}, clear=False
            ):
                ups_b = _import_user_prompt_submit()
                captured_b: dict = {}

                def _spy_b(*, session_id, prompt_len, prompt_sha, redact_hits,
                           injection_counts, repo_root):
                    captured_b["prompt_sha"] = prompt_sha

                with mock.patch.object(ups_b, "_emit_prompt_submitted", _spy_b):
                    ups_b.decide(
                        prompt=prompt,
                        repo_root=Path("/tmp"),
                        session_id="test-session",
                    )
                sha_b = captured_b["prompt_sha"]

        # Restore the original HOME patch for tearDown
        self._home_patch = mock.patch.dict(
            os.environ, {"HOME": str(self._fake_home)}, clear=False
        )
        self._home_patch.start()

        self.assertNotEqual(
            sha_a, sha_b,
            "same prompt across two installations must hash differently"
        )

    def test_hash_stable_within_installation(self) -> None:
        prompt = "ship the framework already"
        sha_first = self._capture_prompt_sha(prompt)
        # Reload the module — salt cache is rebuilt from disk
        self.ups = _import_user_prompt_submit()
        sha_second = self._capture_prompt_sha(prompt)
        self.assertEqual(
            sha_first, sha_second,
            "same prompt within one installation must hash identically"
        )

    def test_salted_hash_differs_from_unsalted(self) -> None:
        prompt = "the audit was a phantom rejection"
        salted = self._capture_prompt_sha(prompt)
        unsalted = hashlib.sha256(
            prompt.encode("utf-8", errors="replace")
        ).hexdigest()[:16]
        self.assertNotEqual(
            salted, unsalted,
            "salted hash must differ from the pre-fix unsalted SHA-256 prefix"
        )


class TestFailOpen(_IsolatedHomeMixin):

    def test_emit_succeeds_when_salt_module_raises(self) -> None:
        """If `injection_salt.get_instance_salt` raises, decide() must
        still emit and return a hash — fail-open availability invariant.
        """
        captured: dict = {}

        def _spy(*, session_id, prompt_len, prompt_sha, redact_hits,
                 injection_counts, repo_root):
            captured["prompt_sha"] = prompt_sha
            captured["called"] = True

        # Patch get_instance_salt to raise. The hook's inner try/except
        # must catch this and fall back to b"" salt.
        from _lib import injection_salt as _salt_mod
        with mock.patch.object(
            _salt_mod, "get_instance_salt",
            side_effect=RuntimeError("simulated salt failure"),
        ):
            with mock.patch.object(self.ups, "_emit_prompt_submitted", _spy):
                self.ups.decide(
                    prompt="any prompt",
                    repo_root=Path("/tmp"),
                    session_id="test-session",
                )

        self.assertTrue(
            captured.get("called"),
            "emit must still fire when salt module raises (fail-open)"
        )
        # Hash must equal the unsalted form (b"" prefix == no salt)
        expected_unsalted = hashlib.sha256(
            "any prompt".encode("utf-8", errors="replace")
        ).hexdigest()[:16]
        self.assertEqual(
            captured["prompt_sha"], expected_unsalted,
            "fail-open path must produce the unsalted hash (b'' salt)"
        )


if __name__ == "__main__":
    unittest.main()
