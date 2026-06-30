"""Ephemeral GPG keyring helper for skill-patch-apply tests (L5).

Each `GpgKeyringFixture` instantiation creates a short-lived GPG home
directory under ``tempfile.mkdtemp()``, generates a throwaway RSA-3072
key pair, and exposes ``sign()`` / ``verify()`` helpers. Teardown
removes the directory.

This file is imported via its filename (``gpg-keyring-fixture.py``) by
tests that need to simulate detached-signature verification without
polluting the developer's real keyring. It is NOT a module in the
traditional sense — we load it via ``importlib.util`` to bypass the
kebab-case filename.

Usage
-----

    from pathlib import Path
    import importlib.util

    _spec = importlib.util.spec_from_file_location(
        "gpg_keyring_fixture",
        Path(__file__).parent / "fixtures" / "gpg-keyring-fixture.py",
    )
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)

    with _mod.GpgKeyringFixture() as kr:
        sig_path = kr.sign(proposal_path)
        ok, fpr = kr.verify(proposal_path, sig_path)

Skipping when gpg is missing
----------------------------

If ``gpg`` isn't on PATH, ``GpgKeyringFixture.__init__`` raises
``GpgUnavailable``. Tests should catch it and call ``self.skipTest(...)``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple


class GpgUnavailable(RuntimeError):
    """Raised when no usable ``gpg`` binary is on PATH."""


class GpgKeyringFixture:
    """Short-lived GPG keyring with one test key.

    Context manager — enters create + generate, exits remove.
    """

    def __init__(self, *, passphrase: str = "") -> None:
        gpg = shutil.which("gpg") or shutil.which("gpg2")
        if not gpg:
            raise GpgUnavailable("gpg binary not found on PATH")
        self._gpg = gpg
        self.passphrase = passphrase
        self.gnupg_home: Optional[Path] = None
        self.fingerprint: str = ""
        self.keyid: str = ""

    # ---- context protocol -------------------------------------------------

    def __enter__(self) -> "GpgKeyringFixture":
        self.gnupg_home = Path(tempfile.mkdtemp(prefix="ceo-gpg-test-"))
        # GNUPGHOME must be 0700 for GPG 2.x not to complain.
        os.chmod(self.gnupg_home, 0o700)
        self._generate_key()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.gnupg_home and self.gnupg_home.exists():
            # Stop the gpg-agent for this dir (GPG 2.x spawns one).
            try:
                subprocess.run(
                    [self._gpg, "--homedir", str(self.gnupg_home),
                     "--batch", "--no-tty",
                     "--quick-kill"],
                    capture_output=True, timeout=5,
                )
            except Exception:
                pass
            shutil.rmtree(self.gnupg_home, ignore_errors=True)

    # ---- helpers ----------------------------------------------------------

    def _env(self) -> dict:
        env = dict(os.environ)
        env["GNUPGHOME"] = str(self.gnupg_home)
        return env

    def _generate_key(self) -> None:
        """Generate a throwaway RSA-3072 key with no passphrase."""
        # Use --quick-generate-key for speed.
        # GPG 2.x accepts batch generation via --gen-key --batch with a
        # parameter file; we use --quick-generate-key for simplicity.
        uid = "CEO Test Signer <test@ceo-orch.invalid>"
        # Passphrase empty → need --pinentry-mode loopback + --passphrase ""
        cmd = [
            self._gpg,
            "--homedir", str(self.gnupg_home),
            "--batch", "--no-tty",
            "--pinentry-mode", "loopback",
            "--passphrase", self.passphrase,
            "--quick-generate-key", uid,
            "rsa3072", "sign", "0",
        ]
        proc = subprocess.run(
            cmd, env=self._env(), capture_output=True, text=True, timeout=45,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"gpg --quick-generate-key failed: {proc.stderr[:400]}"
            )
        self._load_fingerprint()

    def _load_fingerprint(self) -> None:
        proc = subprocess.run(
            [self._gpg, "--homedir", str(self.gnupg_home),
             "--batch", "--with-colons",
             "--list-keys"],
            env=self._env(), capture_output=True, text=True, timeout=10,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"gpg --list-keys failed: {proc.stderr[:200]}")
        # Lines: "pub:...", "fpr::...:<fingerprint>:...", "uid:..."
        for line in proc.stdout.splitlines():
            if line.startswith("fpr:"):
                parts = line.split(":")
                if len(parts) > 9 and parts[9]:
                    self.fingerprint = parts[9]
                    break
            if line.startswith("pub:"):
                parts = line.split(":")
                if len(parts) > 4:
                    self.keyid = parts[4]

    # ---- public API -------------------------------------------------------

    def sign(self, target: Path) -> Path:
        """Produce a detached signature ``<target>.asc``. Returns the path."""
        target = Path(target)
        sig_path = Path(str(target) + ".asc")
        cmd = [
            self._gpg,
            "--homedir", str(self.gnupg_home),
            "--batch", "--no-tty",
            "--pinentry-mode", "loopback",
            "--passphrase", self.passphrase,
            "--armor",
            "--output", str(sig_path),
            "--detach-sign", str(target),
        ]
        if sig_path.exists():
            sig_path.unlink()
        proc = subprocess.run(
            cmd, env=self._env(), capture_output=True, text=True, timeout=15,
        )
        if proc.returncode != 0 or not sig_path.is_file():
            raise RuntimeError(
                f"gpg --detach-sign failed: {proc.stderr[:400]}"
            )
        return sig_path

    def verify(self, target: Path, signature: Path) -> Tuple[bool, str]:
        """Verify the detached signature; return (ok, fingerprint)."""
        cmd = [
            self._gpg,
            "--homedir", str(self.gnupg_home),
            "--batch", "--no-tty",
            "--status-fd", "1",
            "--verify", str(signature), str(target),
        ]
        proc = subprocess.run(
            cmd, env=self._env(), capture_output=True, text=True, timeout=15,
        )
        if proc.returncode != 0:
            return False, ""
        fpr = ""
        good = False
        for line in proc.stdout.splitlines():
            if line.startswith("[GNUPG:] GOODSIG"):
                good = True
            elif line.startswith("[GNUPG:] VALIDSIG"):
                parts = line.split()
                if len(parts) >= 3:
                    fpr = parts[2]
        return good, fpr

    def corrupt_signature(self, sig_path: Path) -> None:
        """Mutate a signature file to make it invalid.

        We append an innocuous newline before the armor END marker; this
        does not parse as valid OpenPGP armor.
        """
        sig_path = Path(sig_path)
        text = sig_path.read_text(encoding="utf-8")
        # Flip one base64 char in the middle to corrupt the signature.
        mid = len(text) // 2
        ch = text[mid]
        replacement = "A" if ch != "A" else "B"
        corrupted = text[:mid] + replacement + text[mid + 1 :]
        sig_path.write_text(corrupted, encoding="utf-8")
