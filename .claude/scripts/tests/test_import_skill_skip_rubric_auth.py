"""PLAN-045 Wave 1 F-01-08 — import-skill --skip-rubric auth integration.

Exercises the full GPG-detached-signature + allowlist flow using the
shared ``gpg-keyring-fixture.py`` throwaway keyring (no Owner key
required). Complements the mock-based unit tests in
``test_import_skill.py`` by covering the _verify_skip_rubric_authorization
code path end-to-end.

Skipped when ``gpg`` is not on PATH.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_IMPORT_SKILL = _REPO_ROOT / ".claude" / "scripts" / "import-skill.py"
_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"

# Load import-skill.py as a module (kebab-case name).
_spec = importlib.util.spec_from_file_location(
    "import_skill_runtime", _IMPORT_SKILL
)
_imp = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_imp)

# Load gpg-keyring-fixture.py via importlib (kebab-case).
_gspec = importlib.util.spec_from_file_location(
    "gpg_keyring_fixture",
    _FIXTURE_DIR / "gpg-keyring-fixture.py",
)
_gmod = importlib.util.module_from_spec(_gspec)
assert _gspec.loader is not None
_gspec.loader.exec_module(_gmod)


_MINIMAL_SKILL = """\
---
name: auth-test
description: fixture skill for --skip-rubric auth test
---

# Auth Test

Body with enough words to pass minimum length checks if we ran them. """ + ("word " * 100) + "\n"


class TestSkipRubricAuth(unittest.TestCase):
    """Integration tests for ``--skip-rubric`` Owner authorization."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)
        try:
            self._keyring = _gmod.GpgKeyringFixture().__enter__()
        except _gmod.GpgUnavailable:
            self.skipTest("gpg binary not available on PATH")
        self.addCleanup(self._keyring.__exit__, None, None, None)
        os.environ["GNUPGHOME"] = str(self._keyring.gnupg_home)
        self.addCleanup(
            lambda: os.environ.pop("GNUPGHOME", None)
        )

        # Source SKILL.md
        self.src_dir = self.tmpdir / "src"
        self.src_dir.mkdir()
        self.src = self.src_dir / "SKILL.md"
        self.src.write_text(_MINIMAL_SKILL, encoding="utf-8")

        # Signer allowlist with the throwaway fpr.
        self.allowlist = self.tmpdir / "signers.txt"
        self.allowlist.write_text(
            f"# test fixture\n{self._keyring.fingerprint}\n"
        )

        # Target dir override via monkey-patch.
        self.fake_target = self.tmpdir / "out" / "SKILL.md"
        self._orig_target = _imp.target_path
        _imp.target_path = lambda d, s: self.fake_target

    def tearDown(self) -> None:
        _imp.target_path = self._orig_target
        self._tmp.cleanup()

    def _sign(self, path: Path) -> Path:
        """Return the detached .asc signature path."""
        return self._keyring.sign(path)

    def test_end_to_end_real_gpg_signed_import(self) -> None:
        sig = self._sign(self.src)
        result = _imp.run_import(
            source=self.src,
            domain="community",
            slug="auth-ok",
            upstream="org/repo@v1",
            license_spdx="CC-BY-4.0",
            sp_nnn="SP-AUTH",
            owner_sha256="c" * 64,
            skip_rubric=True,
            signature_path=sig,
            signer_allowlist=self.allowlist,
        )
        self.assertEqual(result, self.fake_target)
        self.assertTrue(self.fake_target.is_file())
        # Frontmatter must record the signer fpr for forensics.
        text = self.fake_target.read_text(encoding="utf-8")
        self.assertIn("skip_rubric_signer_fpr:", text)
        self.assertIn(self._keyring.fingerprint, text)

    def test_signature_for_wrong_file_fails(self) -> None:
        # Sign a DIFFERENT file — signature won't match our source.
        other = self.tmpdir / "other.md"
        other.write_text("other content")
        wrong_sig = self._sign(other)
        with self.assertRaises(ValueError) as cm:
            _imp.run_import(
                source=self.src,
                domain="community",
                slug="auth-wrong",
                upstream="org/repo@v1",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-AUTH",
                owner_sha256="c" * 64,
                skip_rubric=True,
                signature_path=wrong_sig,
                signer_allowlist=self.allowlist,
            )
        self.assertIn("verification failed", str(cm.exception))

    def test_fpr_not_in_allowlist_fails(self) -> None:
        sig = self._sign(self.src)
        # Allowlist that does NOT contain the keyring fpr.
        other_allowlist = self.tmpdir / "other-signers.txt"
        other_allowlist.write_text(
            "# empty of our key\n"
            "0123456789ABCDEF0123456789ABCDEF01234567\n"
        )
        with self.assertRaises(ValueError) as cm:
            _imp.run_import(
                source=self.src,
                domain="community",
                slug="auth-notallow",
                upstream="org/repo@v1",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-AUTH",
                owner_sha256="c" * 64,
                skip_rubric=True,
                signature_path=sig,
                signer_allowlist=other_allowlist,
            )
        self.assertIn("fpr_not_in_allowlist", str(cm.exception))

    def test_empty_allowlist_fails(self) -> None:
        sig = self._sign(self.src)
        empty_allowlist = self.tmpdir / "empty-signers.txt"
        empty_allowlist.write_text("# only comments\n")
        with self.assertRaises(ValueError) as cm:
            _imp.run_import(
                source=self.src,
                domain="community",
                slug="auth-empty",
                upstream="org/repo@v1",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-AUTH",
                owner_sha256="c" * 64,
                skip_rubric=True,
                signature_path=sig,
                signer_allowlist=empty_allowlist,
            )
        self.assertIn("allowlist_empty", str(cm.exception))

    def test_default_asc_sibling_is_used(self) -> None:
        # No signature_path kwarg → defaults to <source>.asc sibling.
        sig = self._sign(self.src)
        # sig is already at <source>.asc (sign() returns that path).
        result = _imp.run_import(
            source=self.src,
            domain="community",
            slug="auth-default-sibling",
            upstream="org/repo@v1",
            license_spdx="CC-BY-4.0",
            sp_nnn="SP-AUTH",
            owner_sha256="c" * 64,
            skip_rubric=True,
            signer_allowlist=self.allowlist,
        )
        self.assertTrue(result.is_file())


if __name__ == "__main__":
    unittest.main()
