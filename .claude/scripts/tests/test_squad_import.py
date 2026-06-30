"""Unit tests for squad-import.py (PLAN-011 Phase 12).

Exercises the full CR2 mitigation matrix:

    - valid signed tarball imports cleanly + emits squad_imported audit
    - unsigned / corrupt signature => exit 2 "signature_invalid"
    - oversized tarball => exit 2 "oversized"
    - not-in-allowlist => exit 2 "not_in_allowlist"
    - revoked manifest SHA => exit 2 "revoked"
    - symlink member => exit 2 "symlink_refused"
    - `..` member => exit 2 "path_traversal"
    - absolute-path member => exit 2 "path_traversal"
    - validate-squad-contract.py failure => exit 3, rollback applied
    - round-trip: export existing squad → import as copy → contract green
    - CEO_SOTA_DISABLE=1 => exit 0 noop
    - sig-before-parse ORDER verified at source-line level
    - emits squad_imported audit event with real manifest_sha256
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from typing import List, Optional, Tuple


SCRIPTS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SCRIPTS_DIR.parent.parent
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))


# ---- Load squad-import.py via importlib (kebab-case filename) ----

_SPEC_IMPORT = importlib.util.spec_from_file_location(
    "squad_import", SCRIPTS_DIR / "squad-import.py"
)
squad_import = importlib.util.module_from_spec(_SPEC_IMPORT)  # type: ignore
assert _SPEC_IMPORT.loader is not None
_SPEC_IMPORT.loader.exec_module(squad_import)  # type: ignore

_SPEC_EXPORT = importlib.util.spec_from_file_location(
    "squad_export", SCRIPTS_DIR / "squad-export.py"
)
squad_export = importlib.util.module_from_spec(_SPEC_EXPORT)  # type: ignore
assert _SPEC_EXPORT.loader is not None
_SPEC_EXPORT.loader.exec_module(squad_export)  # type: ignore

_FIX_SPEC = importlib.util.spec_from_file_location(
    "gpg_keyring_fixture",
    Path(__file__).parent / "fixtures" / "gpg-keyring-fixture.py",
)
gpg_keyring_fixture = importlib.util.module_from_spec(_FIX_SPEC)  # type: ignore
assert _FIX_SPEC is not None and _FIX_SPEC.loader is not None
_FIX_SPEC.loader.exec_module(gpg_keyring_fixture)  # type: ignore


EDTECH_SQUAD = REPO_ROOT / ".claude" / "skills" / "domains" / "edtech"
CORE_SKILLS_DIR = REPO_ROOT / ".claude" / "skills" / "core"


# ---------------------------------------------------------------------------
# Fixture generation helpers
# ---------------------------------------------------------------------------


def _tar_add_bytes(tar: tarfile.TarFile, arcname: str, data: bytes) -> None:
    """Append a regular-file entry with deterministic metadata."""
    info = tarfile.TarInfo(name=arcname)
    info.size = len(data)
    info.mtime = 0
    info.mode = 0o600
    info.type = tarfile.REGTYPE
    tar.addfile(info, io.BytesIO(data))


def _tar_add_symlink(tar: tarfile.TarFile, arcname: str, linkname: str) -> None:
    """Append a symlink member (used by the CR2 attack-member tests)."""
    info = tarfile.TarInfo(name=arcname)
    info.size = 0
    info.mtime = 0
    info.mode = 0o777
    info.type = tarfile.SYMTYPE
    info.linkname = linkname
    tar.addfile(info)


def _tar_add_hardlink(tar: tarfile.TarFile, arcname: str, linkname: str) -> None:
    """Append a hardlink member (used by the CR2 attack-member tests)."""
    info = tarfile.TarInfo(name=arcname)
    info.size = 0
    info.mtime = 0
    info.mode = 0o644
    info.type = tarfile.LNKTYPE
    info.linkname = linkname
    tar.addfile(info)


def _build_manifest_bytes(slug: str, override: Optional[dict]) -> bytes:
    """Build the minimal valid manifest JSON bytes with optional overrides."""
    manifest = {
        "squad_name": slug,
        "version": "1.0.0",
        "created_at": "2026-04-14T00:00:00Z",
        "squad_contract": "v1",
        "files": [],
        "files_sha256": {},
    }
    if override:
        manifest.update(override)
    return (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _add_minimum_valid_squad_members(tar: tarfile.TarFile, slug: str) -> None:
    """Write the ADR-009 minimum squad-contract files into ``tar``.

    Ships team-personas.md (≥2 VETO personas), pitfalls.yaml (12 entries),
    task-chains.yaml (2 entries), and 3 SKILL.md files so the post-
    extraction contract validator passes for happy-path + round-trip tests.
    """
    team_md = (
        "# Team Personas\n\n"
        "## Squad vetoes\n\n"
        "| Persona | VETO scope |\n"
        "|---|---|\n"
        "| **Alice Tester** (Privacy Engineer) | Any privacy change |\n"
        "| **Bob Builder** (Security Engineer) | Any crypto / access-control change |\n\n"
        "### 1. Alice Tester — Privacy Engineer\nBackground.\n\n"
        "### 2. Bob Builder — Security Engineer\nBackground.\n\n"
        "### 3. Carol Checker — QA\nBackground.\n\n"
        "### 4. Dan Dev — Engineer\nBackground.\n\n"
        "### 5. Eve Eng — Engineer\nBackground.\n"
    )
    _tar_add_bytes(tar, f"{slug}/team-personas.md", team_md.encode("utf-8"))

    pitfalls_lines = ["pitfalls:"]
    for i in range(12):
        pitfalls_lines.append(f"  - id: T-{i:03d}")
        pitfalls_lines.append(f"    rule: \"pitfall {i}\"")
        pitfalls_lines.append(f"    whenToUse: \"context\"")
        pitfalls_lines.append(f"    agents: [Alice Tester]")
    pitfalls_bytes = ("\n".join(pitfalls_lines) + "\n").encode("utf-8")
    _tar_add_bytes(tar, f"{slug}/pitfalls.yaml", pitfalls_bytes)

    chains_lines = [
        "task_chains:",
        "  - id: chain-1",
        "    title: \"First\"",
        "    whenToUse: \"test\"",
        "    steps:",
        "      - id: 1",
        "        owner: \"Alice Tester\"",
        "        action: \"do\"",
        "  - id: chain-2",
        "    title: \"Second\"",
        "    whenToUse: \"test\"",
        "    steps:",
        "      - id: 1",
        "        owner: \"Bob Builder\"",
        "        action: \"do\"",
    ]
    _tar_add_bytes(
        tar,
        f"{slug}/task-chains.yaml",
        ("\n".join(chains_lines) + "\n").encode("utf-8"),
    )
    for skill in ("skill-alpha", "skill-beta", "skill-gamma"):
        skill_md = (
            f"---\nname: {skill}\n"
            f"description: test\nowner: Alice Tester\n---\n"
            f"# {skill}\n"
        )
        _tar_add_bytes(
            tar,
            f"{slug}/skills/{skill}/SKILL.md",
            skill_md.encode("utf-8"),
        )


def _add_attack_members(
    tar: tarfile.TarFile,
    symlink_entry: Optional[Tuple[str, str]],
    hardlink_entry: Optional[Tuple[str, str]],
    path_traversal_name: Optional[str],
    absolute_path_name: Optional[str],
    extra_members: Optional[List[Tuple[str, bytes]]],
) -> None:
    """Append the optional attack/extra members used by CR2 negative tests."""
    if symlink_entry is not None:
        _tar_add_symlink(tar, symlink_entry[0], symlink_entry[1])
    if hardlink_entry is not None:
        _tar_add_hardlink(tar, hardlink_entry[0], hardlink_entry[1])
    if path_traversal_name is not None:
        _tar_add_bytes(tar, path_traversal_name, b"pwned")
    if absolute_path_name is not None:
        _tar_add_bytes(tar, absolute_path_name, b"pwned-abs")
    if extra_members:
        for arc, data in extra_members:
            _tar_add_bytes(tar, arc, data)


def _make_unsigned_bytes_tarball(
    slug: str,
    dest: Path,
    *,
    manifest_override: Optional[dict] = None,
    extra_members: Optional[List[Tuple[str, bytes]]] = None,
    skip_manifest: bool = False,
    symlink_entry: Optional[Tuple[str, str]] = None,
    hardlink_entry: Optional[Tuple[str, str]] = None,
    path_traversal_name: Optional[str] = None,
    absolute_path_name: Optional[str] = None,
    minimum_valid_squad: bool = True,
) -> Tuple[Path, bytes]:
    """Build a gzip tarball byte-for-byte controllable. Returns (path, manifest_bytes).

    Orchestrator over :func:`_build_manifest_bytes`,
    :func:`_add_minimum_valid_squad_members`, and
    :func:`_add_attack_members` (PLAN-023 Phase E decomposition —
    behavior preserved byte-identical).
    """
    manifest_bytes = _build_manifest_bytes(slug, manifest_override)
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Use GzipFile with mtime=0 for determinism.
    with open(dest, "wb") as raw:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6
        ) as gz:
            with tarfile.open(mode="w", fileobj=gz) as tar:
                if not skip_manifest:
                    _tar_add_bytes(tar, f"{slug}/manifest.json", manifest_bytes)
                if minimum_valid_squad:
                    _add_minimum_valid_squad_members(tar, slug)
                _add_attack_members(
                    tar,
                    symlink_entry,
                    hardlink_entry,
                    path_traversal_name,
                    absolute_path_name,
                    extra_members,
                )

    return dest, manifest_bytes


def _sign_tarball(kr: "gpg_keyring_fixture.GpgKeyringFixture", tar_path: Path) -> Path:
    """Sign a tarball with the fixture's key → returns the .sig path."""
    sig_path = Path(str(tar_path) + ".sig")
    cmd = [
        "gpg",
        "--homedir", str(kr.gnupg_home),
        "--batch", "--no-tty",
        "--pinentry-mode", "loopback",
        "--passphrase", kr.passphrase,
        "--armor",
        "--output", str(sig_path),
        "--detach-sign", str(tar_path),
    ]
    if sig_path.exists():
        sig_path.unlink()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError(f"fixture sign failed: {proc.stderr[:300]}")
    return sig_path


def _write_allowlist(settings_path: Path, entries: List[str]) -> None:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps({"squad_allowlist": entries}, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Base harness
# ---------------------------------------------------------------------------


class SquadImportTestBase(unittest.TestCase):
    def setUp(self) -> None:
        # PLAN-107 Wave A.4: force sync mode for emit-read tests
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        self.tmp = Path(tempfile.mkdtemp(prefix="squad-import-test-"))
        self.dest_root = self.tmp / "domains"
        self.dest_root.mkdir()
        self.settings_path = self.tmp / "settings.json"
        self.revocations_path = self.tmp / "squad-revocations.jsonl"
        # Default to empty allowlist + no revocations.
        _write_allowlist(self.settings_path, [])
        self.revocations_path.write_text(
            "# test ledger\n", encoding="utf-8"
        )
        # Also isolate audit log.
        self.audit_dir = self.tmp / "audit"
        self.audit_dir.mkdir()
        self._env_snapshot = {
            k: os.environ.get(k)
            for k in (
                "CEO_AUDIT_LOG_DIR",
                "CEO_AUDIT_LOG_PATH",
                "CEO_AUDIT_LOG_ERR",
                "CEO_AUDIT_LOG_LOCK",
                "CEO_SOTA_DISABLE",
                "CEO_AUDIT_SYNC_MODE",
                "HOME",
            )
        }
        os.environ["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.audit_dir / "audit-log.jsonl")
        os.environ["CEO_AUDIT_LOG_ERR"] = str(self.audit_dir / "audit-log.errors")
        os.environ["CEO_AUDIT_LOG_LOCK"] = str(self.audit_dir / "audit-log.lock")
        # Do NOT override HOME — the subprocess validate-squad-contract.py
        # needs to find PyYAML in the user's site-packages (resolved via
        # HOME). Audit-log isolation is handled by the CEO_AUDIT_LOG_*
        # env overrides above.
        os.environ.pop("CEO_SOTA_DISABLE", None)

        # Keyring fixture: try to set up once; skip tests if gpg missing.
        try:
            self._kr_ctx = gpg_keyring_fixture.GpgKeyringFixture()
            self.kr = self._kr_ctx.__enter__()
        except gpg_keyring_fixture.GpgUnavailable:
            self.kr = None  # type: ignore

    def tearDown(self) -> None:
        if getattr(self, "kr", None) is not None:
            try:
                self._kr_ctx.__exit__(None, None, None)
            except Exception:
                pass
        # Restore env.
        for k, v in self._env_snapshot.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _skip_without_gpg(self) -> None:
        if self.kr is None:
            self.skipTest("gpg not available on PATH")

    def _read_audit(self) -> str:
        p = self.audit_dir / "audit-log.jsonl"
        return p.read_text(encoding="utf-8") if p.is_file() else ""


# ---------------------------------------------------------------------------
# Tests — happy paths
# ---------------------------------------------------------------------------


class TestHappyPath(SquadImportTestBase):
    def test_valid_signed_tarball_imports_cleanly(self) -> None:
        self._skip_without_gpg()
        tar_path = self.tmp / "sq.tar.gz"
        _make_unsigned_bytes_tarball("testsquad", tar_path)
        sig = _sign_tarball(self.kr, tar_path)
        _write_allowlist(self.settings_path, ["example.com/testsquad@v1"])

        slug, mh, fpr = squad_import.import_squad(
            tar_path, sig, "example.com/testsquad@v1",
            dest_root=self.dest_root,
            settings_path=self.settings_path,
            revocations_path=self.revocations_path,
            keyring_home=self.kr.gnupg_home,
        )
        self.assertEqual(slug, "testsquad")
        self.assertEqual(len(mh), 64)
        self.assertTrue(fpr)
        self.assertTrue((self.dest_root / "testsquad").is_dir())


class TestAuditEmitted(SquadImportTestBase):
    def test_emits_squad_imported(self) -> None:
        self._skip_without_gpg()
        tar_path = self.tmp / "sq.tar.gz"
        _make_unsigned_bytes_tarball("auditsquad", tar_path)
        sig = _sign_tarball(self.kr, tar_path)
        _write_allowlist(self.settings_path, ["example.com/auditsquad@v1"])

        rc = squad_import.main([
            "--tarball", str(tar_path),
            "--signature", str(sig),
            "--source", "example.com/auditsquad@v1",
            "--dest-root", str(self.dest_root),
            "--settings", str(self.settings_path),
            "--revocations", str(self.revocations_path),
            "--gnupg-home", str(self.kr.gnupg_home),
        ])
        self.assertEqual(rc, 0)
        audit_text = self._read_audit()
        self.assertIn("squad_imported", audit_text)
        # Parse the JSONL and assert shape.
        events = [json.loads(l) for l in audit_text.splitlines() if l.strip()]
        squad_events = [e for e in events if e.get("action") == "squad_imported"]
        self.assertGreaterEqual(len(squad_events), 1)
        evt = squad_events[-1]
        self.assertEqual(evt["squad_name"], "auditsquad")
        self.assertEqual(evt["source"], "example.com/auditsquad@v1")
        self.assertEqual(len(evt["manifest_sha256"]), 64)
        self.assertTrue(evt["signer_fingerprint"])


# ---------------------------------------------------------------------------
# Tests — signature failures
# ---------------------------------------------------------------------------


class TestSignatureInvalid(SquadImportTestBase):
    def test_unsigned_rejected(self) -> None:
        self._skip_without_gpg()
        tar_path = self.tmp / "sq.tar.gz"
        _make_unsigned_bytes_tarball("sqnosig", tar_path)
        missing_sig = self.tmp / "sq.tar.gz.sig"  # never created
        _write_allowlist(self.settings_path, ["example.com/sqnosig@v1"])
        with self.assertRaises(squad_import.ValidationError) as cm:
            squad_import.import_squad(
                tar_path, missing_sig, "example.com/sqnosig@v1",
                dest_root=self.dest_root,
                settings_path=self.settings_path,
                revocations_path=self.revocations_path,
                keyring_home=self.kr.gnupg_home,
            )
        self.assertEqual(cm.exception.reason_code, "signature_invalid")

    def test_corrupted_signature_rejected(self) -> None:
        self._skip_without_gpg()
        tar_path = self.tmp / "sq.tar.gz"
        _make_unsigned_bytes_tarball("sqc", tar_path)
        sig = _sign_tarball(self.kr, tar_path)
        self.kr.corrupt_signature(sig)
        _write_allowlist(self.settings_path, ["example.com/sqc@v1"])
        with self.assertRaises(squad_import.ValidationError) as cm:
            squad_import.import_squad(
                tar_path, sig, "example.com/sqc@v1",
                dest_root=self.dest_root,
                settings_path=self.settings_path,
                revocations_path=self.revocations_path,
                keyring_home=self.kr.gnupg_home,
            )
        self.assertEqual(cm.exception.reason_code, "signature_invalid")

    def test_signature_invalid_exit_2(self) -> None:
        """CLI exit code for signature failure is 2."""
        self._skip_without_gpg()
        tar_path = self.tmp / "sq.tar.gz"
        _make_unsigned_bytes_tarball("sqex", tar_path)
        missing_sig = self.tmp / "sq.tar.gz.sig"
        _write_allowlist(self.settings_path, ["example.com/sqex@v1"])

        rc = squad_import.main([
            "--tarball", str(tar_path),
            "--signature", str(missing_sig),
            "--source", "example.com/sqex@v1",
            "--dest-root", str(self.dest_root),
            "--settings", str(self.settings_path),
            "--revocations", str(self.revocations_path),
            "--gnupg-home", str(self.kr.gnupg_home),
        ])
        self.assertEqual(rc, 2)
        # And no filesystem mutation.
        self.assertFalse((self.dest_root / "sqex").exists())

    def test_signature_does_not_match_tarball(self) -> None:
        """Swap in a signature from a DIFFERENT tarball → reject."""
        self._skip_without_gpg()
        tar_a = self.tmp / "a.tar.gz"
        tar_b = self.tmp / "b.tar.gz"
        _make_unsigned_bytes_tarball("a", tar_a, manifest_override={"squad_name": "a"})
        _make_unsigned_bytes_tarball("b", tar_b, manifest_override={"squad_name": "b"})
        sig_for_a = _sign_tarball(self.kr, tar_a)
        _write_allowlist(self.settings_path, ["example.com/b@v1"])

        # Sign for A, but try to import B using that signature.
        with self.assertRaises(squad_import.ValidationError) as cm:
            squad_import.import_squad(
                tar_b, sig_for_a, "example.com/b@v1",
                dest_root=self.dest_root,
                settings_path=self.settings_path,
                revocations_path=self.revocations_path,
                keyring_home=self.kr.gnupg_home,
            )
        self.assertEqual(cm.exception.reason_code, "signature_invalid")


# ---------------------------------------------------------------------------
# Tests — oversized
# ---------------------------------------------------------------------------


class TestOversized(SquadImportTestBase):
    def test_oversized_rejected(self) -> None:
        self._skip_without_gpg()
        # Craft a tarball with a big payload — 10 MiB.
        tar_path = self.tmp / "big.tar.gz"
        big = b"x" * (1 * 1024 * 1024)  # 1 MiB raw; compressed much smaller
        # Pad to 6 MiB compressed by adding random bytes (incompressible).
        # Simpler: write a raw file > 5 MiB after gzip by using random bytes.
        random_padding = os.urandom(6 * 1024 * 1024)
        _make_unsigned_bytes_tarball(
            "bigsquad",
            tar_path,
            extra_members=[(f"bigsquad/pad.bin", random_padding)],
        )
        # Make sure the tarball is actually > 5 MiB on disk.
        size = tar_path.stat().st_size
        self.assertGreater(size, 5 * 1024 * 1024, f"need >5MiB, got {size}")

        sig = _sign_tarball(self.kr, tar_path)
        _write_allowlist(self.settings_path, ["example.com/bigsquad@v1"])
        with self.assertRaises(squad_import.ValidationError) as cm:
            squad_import.import_squad(
                tar_path, sig, "example.com/bigsquad@v1",
                dest_root=self.dest_root,
                settings_path=self.settings_path,
                revocations_path=self.revocations_path,
                keyring_home=self.kr.gnupg_home,
            )
        self.assertEqual(cm.exception.reason_code, "oversized")

    def test_custom_max_bytes(self) -> None:
        """A tarball > max_bytes is rejected regardless of the default cap.

        The custom cap is set well below the minimal squad tarball size
        (~850 bytes) to exercise the knob.
        """
        self._skip_without_gpg()
        tar_path = self.tmp / "tiny.tar.gz"
        _make_unsigned_bytes_tarball("tinysquad", tar_path)
        sig = _sign_tarball(self.kr, tar_path)
        _write_allowlist(self.settings_path, ["example.com/tinysquad@v1"])
        with self.assertRaises(squad_import.ValidationError) as cm:
            squad_import.import_squad(
                tar_path, sig, "example.com/tinysquad@v1",
                dest_root=self.dest_root,
                settings_path=self.settings_path,
                revocations_path=self.revocations_path,
                keyring_home=self.kr.gnupg_home,
                max_bytes=256,
            )
        self.assertEqual(cm.exception.reason_code, "oversized")


# ---------------------------------------------------------------------------
# Tests — allowlist
# ---------------------------------------------------------------------------


class TestAllowlist(SquadImportTestBase):
    def test_not_in_allowlist_exit_2(self) -> None:
        self._skip_without_gpg()
        tar_path = self.tmp / "sq.tar.gz"
        _make_unsigned_bytes_tarball("allowsquad", tar_path)
        sig = _sign_tarball(self.kr, tar_path)
        # Allowlist is empty by default.
        with self.assertRaises(squad_import.ValidationError) as cm:
            squad_import.import_squad(
                tar_path, sig, "example.com/allowsquad@v1",
                dest_root=self.dest_root,
                settings_path=self.settings_path,
                revocations_path=self.revocations_path,
                keyring_home=self.kr.gnupg_home,
            )
        self.assertEqual(cm.exception.reason_code, "not_in_allowlist")

    def test_empty_default_refuses_everything(self) -> None:
        """If settings.json has no squad_allowlist key, refuse."""
        self._skip_without_gpg()
        # Overwrite settings with no allowlist key.
        self.settings_path.write_text(
            json.dumps({"other_key": "value"}), encoding="utf-8"
        )
        tar_path = self.tmp / "sq.tar.gz"
        _make_unsigned_bytes_tarball("defaultsquad", tar_path)
        sig = _sign_tarball(self.kr, tar_path)
        with self.assertRaises(squad_import.ValidationError) as cm:
            squad_import.import_squad(
                tar_path, sig, "example.com/defaultsquad@v1",
                dest_root=self.dest_root,
                settings_path=self.settings_path,
                revocations_path=self.revocations_path,
                keyring_home=self.kr.gnupg_home,
            )
        self.assertEqual(cm.exception.reason_code, "not_in_allowlist")


# ---------------------------------------------------------------------------
# Tests — revocation
# ---------------------------------------------------------------------------


class TestRevocation(SquadImportTestBase):
    def test_revoked_exit_2(self) -> None:
        self._skip_without_gpg()
        tar_path = self.tmp / "sq.tar.gz"
        # We need to know the manifest SHA to seed the ledger. Build the
        # tarball, read the manifest bytes back, hash them, write the
        # ledger entry, then try to import.
        _, manifest_bytes = _make_unsigned_bytes_tarball("revoked", tar_path)
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
        sig = _sign_tarball(self.kr, tar_path)
        _write_allowlist(self.settings_path, ["example.com/revoked@v1"])
        self.revocations_path.write_text(
            "# ledger\n"
            + json.dumps({
                "squad_name": "revoked",
                "manifest_sha256": manifest_sha,
                "revoked_at": "2026-04-14T00:00:00Z",
            })
            + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(squad_import.ValidationError) as cm:
            squad_import.import_squad(
                tar_path, sig, "example.com/revoked@v1",
                dest_root=self.dest_root,
                settings_path=self.settings_path,
                revocations_path=self.revocations_path,
                keyring_home=self.kr.gnupg_home,
            )
        self.assertEqual(cm.exception.reason_code, "revoked")


# ---------------------------------------------------------------------------
# Tests — path traversal / symlinks
# ---------------------------------------------------------------------------


class TestSymlinkRefused(SquadImportTestBase):
    def test_symlink_member_refused(self) -> None:
        self._skip_without_gpg()
        tar_path = self.tmp / "sq.tar.gz"
        _make_unsigned_bytes_tarball(
            "symsquad",
            tar_path,
            symlink_entry=("symsquad/link", "/etc/passwd"),
        )
        sig = _sign_tarball(self.kr, tar_path)
        _write_allowlist(self.settings_path, ["example.com/symsquad@v1"])
        with self.assertRaises(squad_import.ValidationError) as cm:
            squad_import.import_squad(
                tar_path, sig, "example.com/symsquad@v1",
                dest_root=self.dest_root,
                settings_path=self.settings_path,
                revocations_path=self.revocations_path,
                keyring_home=self.kr.gnupg_home,
            )
        self.assertEqual(cm.exception.reason_code, "symlink_refused")
        # No filesystem mutation.
        self.assertFalse((self.dest_root / "symsquad").exists())

    def test_hardlink_member_refused(self) -> None:
        self._skip_without_gpg()
        tar_path = self.tmp / "sq.tar.gz"
        _make_unsigned_bytes_tarball(
            "hardsquad",
            tar_path,
            hardlink_entry=("hardsquad/hardlink", "hardsquad/team-personas.md"),
        )
        sig = _sign_tarball(self.kr, tar_path)
        _write_allowlist(self.settings_path, ["example.com/hardsquad@v1"])
        with self.assertRaises(squad_import.ValidationError) as cm:
            squad_import.import_squad(
                tar_path, sig, "example.com/hardsquad@v1",
                dest_root=self.dest_root,
                settings_path=self.settings_path,
                revocations_path=self.revocations_path,
                keyring_home=self.kr.gnupg_home,
            )
        self.assertEqual(cm.exception.reason_code, "symlink_refused")


class TestPathTraversalRefused(SquadImportTestBase):
    def test_dotdot_member_refused(self) -> None:
        self._skip_without_gpg()
        tar_path = self.tmp / "sq.tar.gz"
        _make_unsigned_bytes_tarball(
            "pathsquad",
            tar_path,
            path_traversal_name="pathsquad/../../../etc/passwd",
        )
        sig = _sign_tarball(self.kr, tar_path)
        _write_allowlist(self.settings_path, ["example.com/pathsquad@v1"])
        with self.assertRaises(squad_import.ValidationError) as cm:
            squad_import.import_squad(
                tar_path, sig, "example.com/pathsquad@v1",
                dest_root=self.dest_root,
                settings_path=self.settings_path,
                revocations_path=self.revocations_path,
                keyring_home=self.kr.gnupg_home,
            )
        self.assertEqual(cm.exception.reason_code, "path_traversal")

    def test_absolute_path_member_refused(self) -> None:
        self._skip_without_gpg()
        tar_path = self.tmp / "sq.tar.gz"
        _make_unsigned_bytes_tarball(
            "abssquad",
            tar_path,
            absolute_path_name="/etc/malicious",
        )
        sig = _sign_tarball(self.kr, tar_path)
        _write_allowlist(self.settings_path, ["example.com/abssquad@v1"])
        with self.assertRaises(squad_import.ValidationError) as cm:
            squad_import.import_squad(
                tar_path, sig, "example.com/abssquad@v1",
                dest_root=self.dest_root,
                settings_path=self.settings_path,
                revocations_path=self.revocations_path,
                keyring_home=self.kr.gnupg_home,
            )
        self.assertEqual(cm.exception.reason_code, "path_traversal")


# ---------------------------------------------------------------------------
# Tests — validator rollback
# ---------------------------------------------------------------------------


class TestContractFailRollback(SquadImportTestBase):
    def test_contract_fail_triggers_rollback(self) -> None:
        """A tarball whose extracted tree fails the contract validator
        rolls back. Exit code 3 from CLI."""
        self._skip_without_gpg()
        # Build a tarball with ONLY the manifest — fails contract (no
        # team-personas.md, no pitfalls.yaml, etc.).
        tar_path = self.tmp / "sq.tar.gz"
        _make_unsigned_bytes_tarball(
            "brokensquad",
            tar_path,
            minimum_valid_squad=False,
        )
        sig = _sign_tarball(self.kr, tar_path)
        _write_allowlist(self.settings_path, ["example.com/brokensquad@v1"])

        rc = squad_import.main([
            "--tarball", str(tar_path),
            "--signature", str(sig),
            "--source", "example.com/brokensquad@v1",
            "--dest-root", str(self.dest_root),
            "--settings", str(self.settings_path),
            "--revocations", str(self.revocations_path),
            "--gnupg-home", str(self.kr.gnupg_home),
        ])
        self.assertEqual(rc, 3)
        # Rollback: no artifact left on disk.
        self.assertFalse(
            (self.dest_root / "brokensquad").exists(),
            "rollback must remove the partial install",
        )


# ---------------------------------------------------------------------------
# Tests — round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip(SquadImportTestBase):
    def test_edtech_export_then_import_copy(self) -> None:
        """Export real edtech → rename to edtech-copy → import → contract passes."""
        self._skip_without_gpg()
        # 1. Copy the edtech squad into a tmp location under a different slug
        # (so we don't collide with the in-repo edtech).
        copy_slug = "edtech-copy"
        staging = self.tmp / "staging"
        staging.mkdir()
        copy_dir = staging / copy_slug
        shutil.copytree(EDTECH_SQUAD, copy_dir)

        # 2. Export it.
        out_tar = self.tmp / f"squad-{copy_slug}-v1.tar.gz"
        squad_export.export_squad(copy_dir, out_tar)

        # 3. Sign.
        sig = _sign_tarball(self.kr, out_tar)

        # 4. Configure allowlist and import into self.dest_root.
        _write_allowlist(self.settings_path, [f"example.com/{copy_slug}@v1"])

        slug, mh, fpr = squad_import.import_squad(
            out_tar, sig, f"example.com/{copy_slug}@v1",
            dest_root=self.dest_root,
            settings_path=self.settings_path,
            revocations_path=self.revocations_path,
            keyring_home=self.kr.gnupg_home,
            core_skills_dir=CORE_SKILLS_DIR,
        )
        self.assertEqual(slug, copy_slug)
        self.assertTrue((self.dest_root / copy_slug / "team-personas.md").is_file())
        self.assertTrue((self.dest_root / copy_slug / "pitfalls.yaml").is_file())

        # 5. Final validator sanity check out-of-band.
        vres = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / ".claude" / "scripts" / "validate-squad-contract.py"),
                "--squad", str(self.dest_root / copy_slug),
                "--core-skills", str(CORE_SKILLS_DIR),
            ],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(
            vres.returncode, 0,
            f"contract validator failed post-import: {vres.stderr[:400]}",
        )


# ---------------------------------------------------------------------------
# Tests — kill-switch
# ---------------------------------------------------------------------------


class TestSotaDisable(SquadImportTestBase):
    def test_ceo_sota_disable_exits_0_noop(self) -> None:
        # No need for gpg: the kill-switch fires BEFORE any gpg work.
        tar_path = self.tmp / "sq.tar.gz"
        # Doesn't matter if it's valid — must not be opened.
        tar_path.write_bytes(b"not even a tarball")
        os.environ["CEO_SOTA_DISABLE"] = "1"
        try:
            rc = squad_import.main([
                "--tarball", str(tar_path),
                "--signature", str(self.tmp / "missing.sig"),
                "--source", "example.com/disabled@v1",
            ])
        finally:
            os.environ.pop("CEO_SOTA_DISABLE", None)
        self.assertEqual(rc, 0)
        # No side effects.
        self.assertFalse(any(self.dest_root.iterdir()))


# ---------------------------------------------------------------------------
# Tests — sig-before-parse ORDER assertion (source inspection)
# ---------------------------------------------------------------------------


class TestSigBeforeParseOrder(unittest.TestCase):
    def test_gpg_verify_precedes_tarfile_open_in_source(self) -> None:
        """Static assertion: in squad-import.py, the line invoking gpg
        verify appears BEFORE the line that calls tarfile.open().

        This is the sig-before-parse contract (CR2). A refactor that
        shuffles the order must update this test AND ADR-039 mitigation
        table line references.
        """
        src = (SCRIPTS_DIR / "squad-import.py").read_text(encoding="utf-8")
        lines = src.splitlines()

        # Find the line inside import_squad() that actually invokes
        # _gpg_verify (i.e. the call site, not the def).
        verify_call_lineno = None
        tarfile_open_lineno = None
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if verify_call_lineno is None and stripped.startswith(
                "sig_ok, signer_fpr, gpg_stderr = _gpg_verify("
            ):
                verify_call_lineno = idx
            if (
                tarfile_open_lineno is None
                and "tarfile.open(" in stripped
                and not stripped.startswith("#")
            ):
                tarfile_open_lineno = idx
            if verify_call_lineno and tarfile_open_lineno:
                break

        self.assertIsNotNone(
            verify_call_lineno,
            "could not find _gpg_verify() call site in squad-import.py",
        )
        self.assertIsNotNone(
            tarfile_open_lineno,
            "could not find tarfile.open() call site in squad-import.py",
        )
        self.assertLess(
            verify_call_lineno,
            tarfile_open_lineno,
            f"sig-before-parse violated: gpg --verify at line "
            f"{verify_call_lineno} is AFTER tarfile.open at line "
            f"{tarfile_open_lineno}",
        )


if __name__ == "__main__":
    unittest.main()
