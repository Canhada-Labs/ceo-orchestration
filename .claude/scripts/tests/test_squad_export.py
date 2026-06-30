"""Unit tests for squad-export.py (PLAN-011 Phase 12).

Exercises:
    - tarball produced from a real in-repo squad (edtech)
    - manifest.json contains SHA-256 of every file
    - manifest.yaml is also shipped (human mirror)
    - signing produces a detached .sig that gpg --verify accepts
    - CEO_SOTA_DISABLE=1 => exit 0 noop
    - bad slug => exit 2
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Module loaders
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SCRIPTS_DIR.parent.parent

_spec = importlib.util.spec_from_file_location(
    "squad_export", SCRIPTS_DIR / "squad-export.py"
)
squad_export = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
assert _spec.loader is not None
_spec.loader.exec_module(squad_export)  # type: ignore[union-attr]

# Import GpgKeyringFixture from fixtures/gpg-keyring-fixture.py.
_FIX_SPEC = importlib.util.spec_from_file_location(
    "gpg_keyring_fixture",
    Path(__file__).parent / "fixtures" / "gpg-keyring-fixture.py",
)
gpg_keyring_fixture = importlib.util.module_from_spec(_FIX_SPEC)  # type: ignore[arg-type]
assert _FIX_SPEC is not None and _FIX_SPEC.loader is not None
_FIX_SPEC.loader.exec_module(gpg_keyring_fixture)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


EDTECH_SQUAD = REPO_ROOT / ".claude" / "skills" / "domains" / "edtech"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class SquadExportTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="squad-export-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDiscoverFiles(SquadExportTestBase):
    def test_discovers_edtech_files(self) -> None:
        """Real edtech squad yields at least the 3 core files + 3 SKILLs."""
        self.assertTrue(EDTECH_SQUAD.is_dir(), "edtech squad must exist")
        files = squad_export._discover_squad_files(EDTECH_SQUAD)
        names = {p.name for p in files}
        self.assertIn("team-personas.md", names)
        self.assertIn("pitfalls.yaml", names)
        self.assertIn("task-chains.yaml", names)
        skill_mds = [p for p in files if p.name == "SKILL.md"]
        self.assertGreaterEqual(len(skill_mds), 3)

    def test_empty_squad_returns_empty_list(self) -> None:
        empty = self.tmp / "empty-squad"
        empty.mkdir()
        files = squad_export._discover_squad_files(empty)
        self.assertEqual(files, [])


class TestManifestFields(SquadExportTestBase):
    def test_manifest_has_required_fields(self) -> None:
        out = self.tmp / "squad-edtech-v1.tar.gz"
        tar_path, sig_path, manifest_sha = squad_export.export_squad(
            EDTECH_SQUAD, out
        )
        self.assertTrue(tar_path.exists())
        self.assertIsNone(sig_path)
        self.assertEqual(len(manifest_sha), 64)  # hex SHA-256

        # Read the manifest back.
        with tarfile.open(tar_path, "r:gz") as tar:
            manifest_member = tar.getmember("edtech/manifest.json")
            manifest = json.loads(tar.extractfile(manifest_member).read())

        for req in (
            "squad_name", "version", "created_at",
            "squad_contract", "files", "files_sha256",
        ):
            self.assertIn(req, manifest, f"missing required field: {req}")

        self.assertEqual(manifest["squad_name"], "edtech")
        self.assertEqual(manifest["squad_contract"], "v1")
        self.assertEqual(manifest["version"], "1.0.0")

    def test_manifest_sha256_matches_every_file(self) -> None:
        out = self.tmp / "sq.tar.gz"
        squad_export.export_squad(EDTECH_SQUAD, out)
        with tarfile.open(out, "r:gz") as tar:
            manifest_member = tar.getmember("edtech/manifest.json")
            manifest = json.loads(tar.extractfile(manifest_member).read())

            # Every entry in files_sha256 must correspond to a real member
            # whose SHA-256 matches.
            for arcname, expected_hex in manifest["files_sha256"].items():
                member = tar.getmember(arcname)
                data = tar.extractfile(member).read()
                actual_hex = hashlib.sha256(data).hexdigest()
                self.assertEqual(
                    actual_hex, expected_hex,
                    f"SHA mismatch for {arcname}",
                )

    def test_manifest_files_list_sorted(self) -> None:
        out = self.tmp / "sq.tar.gz"
        squad_export.export_squad(EDTECH_SQUAD, out)
        with tarfile.open(out, "r:gz") as tar:
            manifest_member = tar.getmember("edtech/manifest.json")
            manifest = json.loads(tar.extractfile(manifest_member).read())
        self.assertEqual(manifest["files"], sorted(manifest["files"]))


class TestYamlMirror(SquadExportTestBase):
    def test_manifest_yaml_present(self) -> None:
        out = self.tmp / "sq.tar.gz"
        squad_export.export_squad(EDTECH_SQUAD, out)
        with tarfile.open(out, "r:gz") as tar:
            yaml_member = tar.getmember("edtech/manifest.yaml")
            yaml_bytes = tar.extractfile(yaml_member).read()
        # Not parsing YAML (stdlib-only); simple structural assertions.
        text = yaml_bytes.decode("utf-8")
        self.assertIn("squad_name: edtech", text)
        self.assertIn("squad_contract: v1", text)
        self.assertIn("files:", text)
        self.assertIn("files_sha256:", text)


class TestSigning(SquadExportTestBase):
    def test_signed_export_produces_sig(self) -> None:
        try:
            kr_ctx = gpg_keyring_fixture.GpgKeyringFixture()
        except gpg_keyring_fixture.GpgUnavailable:
            self.skipTest("gpg not available")
        with kr_ctx as kr:
            out = self.tmp / "sq.tar.gz"
            tar_path, sig_path, _ = squad_export.export_squad(
                EDTECH_SQUAD,
                out,
                sign_with=kr.fingerprint,
                gnupg_home=kr.gnupg_home,
            )
            self.assertIsNotNone(sig_path)
            self.assertTrue(sig_path.exists())
            self.assertTrue(str(sig_path).endswith(".sig"))

            # The fixture's verify() takes (target, signature) and needs
            # --homedir. We invoke gpg directly with the fixture's GNUPGHOME.
            proc = subprocess.run(
                [
                    "gpg",
                    "--homedir", str(kr.gnupg_home),
                    "--batch", "--no-tty",
                    "--verify", str(sig_path), str(tar_path),
                ],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(
                proc.returncode, 0,
                f"gpg --verify failed: {proc.stderr[:300]}",
            )


class TestSotaDisable(SquadExportTestBase):
    def test_ceo_sota_disable_exits_0_noop(self) -> None:
        out = self.tmp / "must-not-be-created.tar.gz"
        old = os.environ.get("CEO_SOTA_DISABLE")
        os.environ["CEO_SOTA_DISABLE"] = "1"
        try:
            rc = squad_export.main(
                ["--squad", "edtech", "--output", str(out)]
            )
        finally:
            if old is None:
                os.environ.pop("CEO_SOTA_DISABLE", None)
            else:
                os.environ["CEO_SOTA_DISABLE"] = old
        self.assertEqual(rc, 0)
        self.assertFalse(out.exists(), "disable=1 must not write output")


class TestCliMain(SquadExportTestBase):
    def test_main_happy(self) -> None:
        out = self.tmp / "ed.tar.gz"
        rc = squad_export.main(
            ["--squad", "edtech", "--output", str(out),
             "--repo-root", str(REPO_ROOT)]
        )
        self.assertEqual(rc, 0)
        self.assertTrue(out.exists())

    def test_main_missing_squad(self) -> None:
        rc = squad_export.main(
            ["--squad", "nonexistent-squad-xyz",
             "--output", str(self.tmp / "x.tar.gz"),
             "--repo-root", str(REPO_ROOT)]
        )
        self.assertEqual(rc, 2)


class TestMembersAreFiles(SquadExportTestBase):
    def test_no_symlinks_in_export(self) -> None:
        """Exported tarball contains no symlinks or hardlinks."""
        out = self.tmp / "x.tar.gz"
        squad_export.export_squad(EDTECH_SQUAD, out)
        with tarfile.open(out, "r:gz") as tar:
            for m in tar.getmembers():
                self.assertFalse(m.issym(), f"symlink leaked: {m.name}")
                self.assertFalse(m.islnk(), f"hardlink leaked: {m.name}")


class TestDeterminism(SquadExportTestBase):
    def test_mtime_is_zero(self) -> None:
        """Every tar entry has mtime=0 so exports are deterministic."""
        out = self.tmp / "x.tar.gz"
        squad_export.export_squad(EDTECH_SQUAD, out)
        with tarfile.open(out, "r:gz") as tar:
            for m in tar.getmembers():
                self.assertEqual(m.mtime, 0, f"mtime leaked on {m.name}")


if __name__ == "__main__":
    unittest.main()
