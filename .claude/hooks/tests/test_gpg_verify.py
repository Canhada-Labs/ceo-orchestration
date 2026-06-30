"""PLAN-045 Wave 1 — _lib.gpg_verify unit tests.

Covers:
- `normalise_fpr`: case normalisation, whitespace strip, validation.
- `load_allowlist`: missing / not-file / symlink / empty / malformed.
- `verify_detached`: symlink reject, missing binary, gpg failure
  modes, GOODSIG/VALIDSIG parsing, allowlist enforcement.
- Integration with real gpg via monkeypatched subprocess.run — covers
  every failure-mode string without requiring Owner's keyring.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

_HOOKS = Path(__file__).resolve().parent.parent

from _lib import gpg_verify  # noqa: E402
from _lib.gpg_verify import (  # noqa: E402
    load_allowlist,
    normalise_fpr,
    verify_detached,
)


_VALID_FPR = "0000000000000000000000000000000000000000"
_OTHER_FPR = "0123456789ABCDEF0123456789ABCDEF01234567"


# --------------------------------------------------------------------------
# normalise_fpr
# --------------------------------------------------------------------------


class TestNormaliseFpr(unittest.TestCase):
    def test_valid_uppercase_40_hex(self) -> None:
        self.assertEqual(normalise_fpr(_VALID_FPR), _VALID_FPR)

    def test_valid_lowercase_uppercased(self) -> None:
        self.assertEqual(
            normalise_fpr(_VALID_FPR.lower()), _VALID_FPR
        )

    def test_mixed_case_uppercased(self) -> None:
        s = _VALID_FPR[:20].lower() + _VALID_FPR[20:]
        self.assertEqual(normalise_fpr(s), _VALID_FPR)

    def test_with_inner_whitespace_stripped(self) -> None:
        with_spaces = "0000 0000 0000 0000 0000 0000 0000 0000 0000 0000"
        self.assertEqual(normalise_fpr(with_spaces), _VALID_FPR)

    def test_with_leading_trailing_whitespace(self) -> None:
        self.assertEqual(
            normalise_fpr(f"  {_VALID_FPR}\n"), _VALID_FPR
        )

    def test_too_short(self) -> None:
        self.assertEqual(normalise_fpr(_VALID_FPR[:-1]), "")

    def test_too_long(self) -> None:
        self.assertEqual(normalise_fpr(_VALID_FPR + "A"), "")

    def test_non_hex_character(self) -> None:
        s = _VALID_FPR[:-1] + "Z"
        self.assertEqual(normalise_fpr(s), "")

    def test_empty(self) -> None:
        self.assertEqual(normalise_fpr(""), "")

    def test_only_whitespace(self) -> None:
        self.assertEqual(normalise_fpr("   \n\t  "), "")


# --------------------------------------------------------------------------
# load_allowlist
# --------------------------------------------------------------------------


class TestLoadAllowlist(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_missing_file(self) -> None:
        fprs, err = load_allowlist(self.tmpdir / "nope.txt")
        self.assertEqual(fprs, set())
        self.assertEqual(err, "allowlist_missing")

    def test_path_is_directory(self) -> None:
        fprs, err = load_allowlist(self.tmpdir)
        # Being a directory returns not_file (tmpdir.exists() == True).
        self.assertEqual(err, "allowlist_not_file")
        self.assertEqual(fprs, set())

    def test_symlink_leaf(self) -> None:
        real = self.tmpdir / "real.txt"
        real.write_text(_VALID_FPR + "\n")
        link = self.tmpdir / "link.txt"
        link.symlink_to(real)
        fprs, err = load_allowlist(link)
        self.assertEqual(err, "allowlist_symlink_rejected")
        self.assertEqual(fprs, set())

    def test_parent_symlink_rejected(self) -> None:
        real_dir = self.tmpdir / "real_parent"
        real_dir.mkdir()
        real_file = real_dir / "file.txt"
        real_file.write_text(_VALID_FPR + "\n")
        link_dir = self.tmpdir / "link_parent"
        link_dir.symlink_to(real_dir)
        fprs, err = load_allowlist(link_dir / "file.txt")
        self.assertEqual(err, "allowlist_symlink_rejected")
        self.assertEqual(fprs, set())

    def test_empty_file(self) -> None:
        p = self.tmpdir / "empty.txt"
        p.write_text("")
        fprs, err = load_allowlist(p)
        self.assertEqual(err, "allowlist_empty")
        self.assertEqual(fprs, set())

    def test_only_comments_and_blanks(self) -> None:
        p = self.tmpdir / "comments.txt"
        p.write_text("# a comment\n\n   \n# another\n")
        fprs, err = load_allowlist(p)
        self.assertEqual(err, "allowlist_empty")
        self.assertEqual(fprs, set())

    def test_single_fpr(self) -> None:
        p = self.tmpdir / "allowlist.txt"
        p.write_text(f"# owner\n{_VALID_FPR}\n")
        fprs, err = load_allowlist(p)
        self.assertIsNone(err)
        self.assertEqual(fprs, {_VALID_FPR})

    def test_multiple_fprs(self) -> None:
        p = self.tmpdir / "allowlist.txt"
        p.write_text(f"{_VALID_FPR}\n{_OTHER_FPR}\n")
        fprs, err = load_allowlist(p)
        self.assertIsNone(err)
        self.assertEqual(fprs, {_VALID_FPR, _OTHER_FPR})

    def test_inline_trailing_comment_stripped(self) -> None:
        p = self.tmpdir / "allowlist.txt"
        p.write_text(f"{_VALID_FPR}  # Owner 2026\n")
        fprs, err = load_allowlist(p)
        self.assertIsNone(err)
        self.assertEqual(fprs, {_VALID_FPR})

    def test_lowercase_fpr_normalised(self) -> None:
        p = self.tmpdir / "allowlist.txt"
        p.write_text(_VALID_FPR.lower() + "\n")
        fprs, err = load_allowlist(p)
        self.assertIsNone(err)
        self.assertEqual(fprs, {_VALID_FPR})

    def test_malformed_line_silently_skipped(self) -> None:
        p = self.tmpdir / "allowlist.txt"
        p.write_text(f"NOT-A-FPR\n{_VALID_FPR}\nAnotherBad\n")
        fprs, err = load_allowlist(p)
        self.assertIsNone(err)
        self.assertEqual(fprs, {_VALID_FPR})

    def test_duplicate_fprs_deduped(self) -> None:
        p = self.tmpdir / "allowlist.txt"
        p.write_text(f"{_VALID_FPR}\n{_VALID_FPR}\n{_VALID_FPR.lower()}\n")
        fprs, err = load_allowlist(p)
        self.assertIsNone(err)
        self.assertEqual(fprs, {_VALID_FPR})


# --------------------------------------------------------------------------
# verify_detached — mocked subprocess.run
# --------------------------------------------------------------------------


def _make_status_fd(good: bool, fpr: str = "") -> str:
    """Synthesize a realistic gpg --status-fd=1 output."""
    lines: List[str] = []
    if good:
        lines.append(f"[GNUPG:] GOODSIG ABCD1234 Test Key")
        if fpr:
            lines.append(f"[GNUPG:] VALIDSIG {fpr} 2026-04-20 0 4 0 22 10 01 {fpr}")
    else:
        lines.append("[GNUPG:] BADSIG ABCD1234 Test Key")
    return "\n".join(lines) + "\n"


class _FakeProc:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestVerifyDetached(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)
        self.signed = self.tmpdir / "signed.md"
        self.signed.write_text("body")
        self.sig = self.tmpdir / "signed.md.asc"
        self.sig.write_text("-----BEGIN PGP SIGNATURE-----\nfake\n-----END PGP SIGNATURE-----\n")
        self.allowlist = self.tmpdir / "allowlist.txt"
        self.allowlist.write_text(_VALID_FPR + "\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # --- Basic file-existence / symlink ----------------------------------

    def test_signature_missing(self) -> None:
        ok, fpr, reason = verify_detached(
            self.signed,
            self.tmpdir / "nope.asc",
            allowlist_path=self.allowlist,
            gpg_bin="/usr/bin/true",
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "signature_file_missing")

    def test_signed_missing(self) -> None:
        ok, fpr, reason = verify_detached(
            self.tmpdir / "nope.md",
            self.sig,
            allowlist_path=self.allowlist,
            gpg_bin="/usr/bin/true",
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "signed_file_missing")

    def test_signature_symlink_rejected(self) -> None:
        real = self.tmpdir / "real.asc"
        real.write_text("sig")
        link = self.tmpdir / "link.asc"
        link.symlink_to(real)
        ok, fpr, reason = verify_detached(
            self.signed,
            link,
            allowlist_path=self.allowlist,
            gpg_bin="/usr/bin/true",
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "signature_file_symlink")

    def test_signed_symlink_rejected(self) -> None:
        real = self.tmpdir / "real.md"
        real.write_text("body")
        link = self.tmpdir / "link.md"
        link.symlink_to(real)
        ok, fpr, reason = verify_detached(
            link,
            self.sig,
            allowlist_path=self.allowlist,
            gpg_bin="/usr/bin/true",
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "signed_file_symlink")

    # --- Allowlist resolution --------------------------------------------

    def test_no_allowlist_provided(self) -> None:
        ok, fpr, reason = verify_detached(
            self.signed,
            self.sig,
            allowlist_path=None,
            allowlist_fprs=None,
            gpg_bin="/usr/bin/true",
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "no_allowlist_provided")

    def test_allowlist_fprs_empty_iterable(self) -> None:
        ok, fpr, reason = verify_detached(
            self.signed,
            self.sig,
            allowlist_fprs=[],
            gpg_bin="/usr/bin/true",
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "allowlist_empty")

    def test_allowlist_fprs_only_invalid(self) -> None:
        ok, fpr, reason = verify_detached(
            self.signed,
            self.sig,
            allowlist_fprs=["not-a-fpr", "also-bad"],
            gpg_bin="/usr/bin/true",
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "allowlist_empty")

    def test_allowlist_missing_file(self) -> None:
        ok, fpr, reason = verify_detached(
            self.signed,
            self.sig,
            allowlist_path=self.tmpdir / "does-not-exist.txt",
            gpg_bin="/usr/bin/true",
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "allowlist_missing")

    # --- GPG subprocess failure modes ------------------------------------

    def test_gpg_missing_binary(self) -> None:
        with mock.patch.object(gpg_verify.shutil, "which", return_value=None):
            ok, fpr, reason = verify_detached(
                self.signed,
                self.sig,
                allowlist_path=self.allowlist,
                gpg_bin=None,
            )
        self.assertFalse(ok)
        self.assertEqual(reason, "gpg_missing")

    def test_gpg_returncode_nonzero(self) -> None:
        with mock.patch.object(
            gpg_verify.subprocess,
            "run",
            return_value=_FakeProc(2, "", "bad signature"),
        ):
            ok, fpr, reason = verify_detached(
                self.signed,
                self.sig,
                allowlist_path=self.allowlist,
                gpg_bin="/usr/bin/gpg",
            )
        self.assertFalse(ok)
        self.assertEqual(reason, "gpg_returncode_2")

    def test_gpg_timeout(self) -> None:
        def _raise_timeout(*args: Any, **kwargs: Any) -> Any:
            raise subprocess.TimeoutExpired(cmd="gpg", timeout=1)

        with mock.patch.object(
            gpg_verify.subprocess, "run", side_effect=_raise_timeout
        ):
            ok, fpr, reason = verify_detached(
                self.signed,
                self.sig,
                allowlist_path=self.allowlist,
                gpg_bin="/usr/bin/gpg",
            )
        self.assertFalse(ok)
        self.assertEqual(reason, "gpg_timeout")

    def test_gpg_os_error(self) -> None:
        def _raise_oserror(*args: Any, **kwargs: Any) -> Any:
            raise PermissionError("denied")

        with mock.patch.object(
            gpg_verify.subprocess, "run", side_effect=_raise_oserror
        ):
            ok, fpr, reason = verify_detached(
                self.signed,
                self.sig,
                allowlist_path=self.allowlist,
                gpg_bin="/usr/bin/gpg",
            )
        self.assertFalse(ok)
        self.assertEqual(reason, "gpg_os_error:PermissionError")

    def test_no_goodsig(self) -> None:
        with mock.patch.object(
            gpg_verify.subprocess,
            "run",
            return_value=_FakeProc(0, _make_status_fd(False), ""),
        ):
            ok, fpr, reason = verify_detached(
                self.signed,
                self.sig,
                allowlist_path=self.allowlist,
                gpg_bin="/usr/bin/gpg",
            )
        self.assertFalse(ok)
        self.assertEqual(reason, "no_goodsig")

    def test_good_but_no_validsig(self) -> None:
        # GOODSIG without VALIDSIG → no_validsig_fpr
        stdout = "[GNUPG:] GOODSIG ABCD1234 Test Key\n"
        with mock.patch.object(
            gpg_verify.subprocess,
            "run",
            return_value=_FakeProc(0, stdout, ""),
        ):
            ok, fpr, reason = verify_detached(
                self.signed,
                self.sig,
                allowlist_path=self.allowlist,
                gpg_bin="/usr/bin/gpg",
            )
        self.assertFalse(ok)
        self.assertEqual(reason, "no_validsig_fpr")

    def test_validsig_malformed_fpr(self) -> None:
        # GOODSIG + VALIDSIG but fpr is non-hex
        stdout = (
            "[GNUPG:] GOODSIG ABCD1234 Test Key\n"
            "[GNUPG:] VALIDSIG NOTAVALIDFPR 2026-04-20\n"
        )
        with mock.patch.object(
            gpg_verify.subprocess,
            "run",
            return_value=_FakeProc(0, stdout, ""),
        ):
            ok, fpr, reason = verify_detached(
                self.signed,
                self.sig,
                allowlist_path=self.allowlist,
                gpg_bin="/usr/bin/gpg",
            )
        self.assertFalse(ok)
        self.assertEqual(reason, "no_validsig_fpr")

    def test_good_sig_fpr_not_in_allowlist(self) -> None:
        # fpr verified but not in allowlist → fpr_not_in_allowlist
        with mock.patch.object(
            gpg_verify.subprocess,
            "run",
            return_value=_FakeProc(0, _make_status_fd(True, _OTHER_FPR), ""),
        ):
            ok, fpr, reason = verify_detached(
                self.signed,
                self.sig,
                allowlist_path=self.allowlist,
                gpg_bin="/usr/bin/gpg",
            )
        self.assertFalse(ok)
        self.assertEqual(reason, "fpr_not_in_allowlist")

    def test_good_sig_fpr_in_allowlist(self) -> None:
        with mock.patch.object(
            gpg_verify.subprocess,
            "run",
            return_value=_FakeProc(0, _make_status_fd(True, _VALID_FPR), ""),
        ):
            ok, fpr, reason = verify_detached(
                self.signed,
                self.sig,
                allowlist_path=self.allowlist,
                gpg_bin="/usr/bin/gpg",
            )
        self.assertTrue(ok)
        self.assertEqual(fpr, _VALID_FPR)
        self.assertEqual(reason, "")

    def test_accepts_lowercase_validsig_fpr(self) -> None:
        # Real gpg always uppercases, but canonicalise via normalise_fpr.
        with mock.patch.object(
            gpg_verify.subprocess,
            "run",
            return_value=_FakeProc(
                0, _make_status_fd(True, _VALID_FPR.lower()), ""
            ),
        ):
            ok, fpr, reason = verify_detached(
                self.signed,
                self.sig,
                allowlist_path=self.allowlist,
                gpg_bin="/usr/bin/gpg",
            )
        self.assertTrue(ok)
        self.assertEqual(fpr, _VALID_FPR)

    def test_allowlist_fprs_iterable_success(self) -> None:
        with mock.patch.object(
            gpg_verify.subprocess,
            "run",
            return_value=_FakeProc(0, _make_status_fd(True, _VALID_FPR), ""),
        ):
            ok, fpr, reason = verify_detached(
                self.signed,
                self.sig,
                allowlist_fprs=[_VALID_FPR],
                gpg_bin="/usr/bin/gpg",
            )
        self.assertTrue(ok)
        self.assertEqual(fpr, _VALID_FPR)

    def test_empty_allowlist_file_rejected_even_with_goodsig(self) -> None:
        empty = self.tmpdir / "empty.txt"
        empty.write_text("# only comments\n")
        with mock.patch.object(
            gpg_verify.subprocess,
            "run",
            return_value=_FakeProc(0, _make_status_fd(True, _VALID_FPR), ""),
        ):
            ok, fpr, reason = verify_detached(
                self.signed,
                self.sig,
                allowlist_path=empty,
                gpg_bin="/usr/bin/gpg",
            )
        self.assertFalse(ok)
        self.assertEqual(reason, "allowlist_empty")

    # --- Subprocess invocation shape -------------------------------------

    def test_subprocess_invoked_with_status_fd(self) -> None:
        """Smoke test: ensure we invoke gpg with --status-fd=1 --verify."""
        captured: Dict[str, Any] = {}

        def _capture(cmd: List[str], **kwargs: Any) -> Any:
            captured["cmd"] = cmd
            captured["timeout"] = kwargs.get("timeout")
            return _FakeProc(0, _make_status_fd(True, _VALID_FPR), "")

        with mock.patch.object(gpg_verify.subprocess, "run", side_effect=_capture):
            verify_detached(
                self.signed,
                self.sig,
                allowlist_fprs=[_VALID_FPR],
                gpg_bin="/usr/bin/gpg",
                timeout=7.5,
            )
        self.assertEqual(captured["cmd"][0], "/usr/bin/gpg")
        self.assertIn("--batch", captured["cmd"])
        self.assertIn("--status-fd", captured["cmd"])
        self.assertIn("--verify", captured["cmd"])
        self.assertEqual(captured["timeout"], 7.5)

    # --- Real-gpg integration (if Owner's keyring is available) ----------
    # A round-trip sign+verify against a real key adds a layer that
    # catches regressions the mocked tests can't (e.g. status-fd format
    # drift across gpg versions). We skip cleanly when gpg is absent
    # OR the Owner's fpr isn't in the local keyring.

    @unittest.skipIf(
        os.environ.get("CEO_GPG_INTEGRATION") != "1",
        "CEO_GPG_INTEGRATION=1 to run real-gpg round-trip",
    )
    def test_real_gpg_roundtrip(self) -> None:  # pragma: no cover
        import shutil as _shutil
        gpg = _shutil.which("gpg") or _shutil.which("gpg2")
        if not gpg:
            self.skipTest("no gpg binary")
        # Probe Owner's key in local keyring.
        probe = subprocess.run(
            [gpg, "--list-secret-keys", _VALID_FPR],
            capture_output=True, text=True,
        )
        if probe.returncode != 0:
            self.skipTest(f"Owner fpr not in keyring")
        msg = self.tmpdir / "msg.md"
        msg.write_text("real-roundtrip-body")
        sig = self.tmpdir / "msg.md.asc"
        try:
            sign = subprocess.run(
                [gpg, "--batch", "--pinentry-mode", "error",
                 "--armor", "--detach-sign",
                 "--local-user", _VALID_FPR, "--output", str(sig), str(msg)],
                capture_output=True, text=True, timeout=10,
            )
        except subprocess.TimeoutExpired:
            self.skipTest("gpg sign timed out (gpg-agent locked)")
        if sign.returncode != 0:
            self.skipTest(f"gpg sign failed (likely passphrase): {sign.stderr[:100]}")
        ok, fpr, reason = verify_detached(
            msg, sig,
            allowlist_fprs=[_VALID_FPR],
            gpg_bin=gpg,
        )
        self.assertTrue(ok, f"expected ok, got reason={reason}")
        self.assertEqual(fpr, _VALID_FPR)


if __name__ == "__main__":
    unittest.main()
