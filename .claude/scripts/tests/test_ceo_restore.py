"""Regression coverage for the FD-25 restore trust boundary."""
from __future__ import annotations

import io
import os
import subprocess
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
RESTORE = REPO_ROOT / ".claude" / "scripts" / "ceo-restore.sh"
BACKUP = REPO_ROOT / ".claude" / "scripts" / "ceo-backup.sh"
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402
from _subprocess_helpers import run_in_process_group  # noqa: E402


def _archive(path: Path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name, content in members.items():
            entry = tarfile.TarInfo(name)
            entry.size = len(content)
            archive.addfile(entry, io.BytesIO(content))


def _run(script: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop("CEO_AUDIT_LOG_DIR", None)
    return run_in_process_group(
        ["bash", str(script), *args], cwd=cwd, env=env, text=True,
        capture_output=True, check=False, timeout=15,
    )


class CeoRestoreFd25Test(TestEnvContext):
    def test_fu144_apply_restores_regular_archive_data(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            destination = root / "destination"
            _archive(bundle, {"audit/audit-log.jsonl": b'{"event":"ok"}\n',
                              "memory/note.txt": b"remember\n"})
            result = _run(RESTORE, str(bundle), "--apply", "--force",
                          "--dest", str(destination), cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((destination / "audit-log.jsonl").read_bytes(), b'{"event":"ok"}\n')
            self.assertEqual((destination / "memory" / "note.txt").read_bytes(), b"remember\n")

    def test_fu144_preview_and_apply_reject_alias_destination_equally(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            _archive(bundle, {"audit/audit-log.jsonl": b"safe\n"})
            alias = str(root) + "/.//target"
            preview = _run(RESTORE, str(bundle), "--dest", alias, cwd=root)
            apply = _run(RESTORE, str(bundle), "--apply", "--force", "--dest", alias, cwd=root)
            self.assertEqual(preview.returncode, 2, preview.stderr)
            self.assertEqual(apply.returncode, 2, apply.stderr)
            self.assertIn("refused destination spelling", preview.stderr)

    def test_fu144_optional_restore_refuses_dangling_claude_link_before_writes(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            destination = root / "destination"
            _archive(bundle, {"audit/audit-log.jsonl": b"safe\n", "plans/a.md": b"plan\n"})
            (root / ".claude").symlink_to(root / "missing")
            result = _run(RESTORE, str(bundle), "--apply", "--force", "--restore-plans",
                          "--dest", str(destination), cwd=root)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(destination.exists())
            self.assertIn("real .claude directory", result.stderr)

    def test_fu144_refuses_symbolic_links_in_archive(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            with tarfile.open(bundle, "w:gz") as archive:
                link = tarfile.TarInfo("memory/escape")
                link.type = tarfile.SYMTYPE
                link.linkname = "../../outside"
                archive.addfile(link)
            result = _run(RESTORE, str(bundle), "--apply", "--force",
                          "--dest", str(root / "destination"), cwd=root)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("member type", result.stderr)

    def test_fu144_refuses_hardlink_and_fifo_before_destination_write(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            for kind in (tarfile.LNKTYPE, tarfile.FIFOTYPE):
                bundle = root / ("member-{0}.tar.gz".format(kind.decode("ascii")))
                with tarfile.open(bundle, "w:gz") as archive:
                    member = tarfile.TarInfo("memory/unsafe")
                    member.type = kind
                    member.linkname = "memory/other"
                    archive.addfile(member)
                destination = root / ("destination-" + kind.decode("ascii"))
                result = _run(RESTORE, str(bundle), "--apply", "--force",
                              "--dest", str(destination), cwd=root)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(destination.exists())
                self.assertIn("member type", result.stderr)

    def test_fu144_archive_alias_for_audit_key_is_rejected_in_both_modes(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            _archive(bundle, {".//audit/audit-key": b"key"})
            preview = _run(RESTORE, str(bundle), "--dest", str(root / "target"), cwd=root)
            apply = _run(RESTORE, str(bundle), "--apply", "--force",
                         "--dest", str(root / "target"), cwd=root)
            self.assertEqual(preview.returncode, 2, preview.stderr)
            self.assertEqual(apply.returncode, 2, apply.stderr)
            self.assertIn("refused path", preview.stderr)

    def test_fu144_regular_audit_secrets_are_rejected_before_preview_or_apply(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            for name in ("audit/audit-key", "audit/.salt"):
                bundle = root / (name.rsplit("/", 1)[-1] + ".tar.gz")
                _archive(bundle, {name: b"secret"})
                preview = _run(RESTORE, str(bundle), "--dest", str(root / "target"), cwd=root)
                apply = _run(RESTORE, str(bundle), "--apply", "--force",
                             "--dest", str(root / "target"), cwd=root)
                self.assertEqual(preview.returncode, 2, preview.stderr)
                self.assertEqual(apply.returncode, 2, apply.stderr)

    def test_fu144_existing_audit_link_cannot_overwrite_live_secret(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            live = root / "live-audit-log"
            destination = root / "destination"
            destination.mkdir()
            live.write_text("live", encoding="utf-8")
            (destination / "audit-log.jsonl").symlink_to(live)
            _archive(bundle, {"audit/audit-log.jsonl": b"backup"})
            result = _run(RESTORE, str(bundle), "--apply", "--force",
                          "--dest", str(destination), cwd=root)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(live.read_text(encoding="utf-8"), "live")
            self.assertIn("symbolic link", result.stderr)

    def test_fu144_existing_target_directory_is_rejected_before_copy(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            destination = root / "destination"
            destination.mkdir()
            (destination / "audit-log.jsonl").mkdir()
            _archive(bundle, {"audit/audit-log.jsonl": b"backup"})
            result = _run(RESTORE, str(bundle), "--apply", "--force",
                          "--dest", str(destination), cwd=root)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("regular file", result.stderr)

    def test_fu144_bad_sha_sidecar_rejects_before_destination_write(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "state.tar.gz"
            destination = root / "destination"
            _archive(bundle, {"audit/audit-log.jsonl": b"backup"})
            bundle.with_name(bundle.name + ".sha256").write_text("bad\n", encoding="utf-8")
            result = _run(RESTORE, str(bundle), "--apply", "--force",
                          "--dest", str(destination), cwd=root)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(destination.exists())
            self.assertIn("SHA256 mismatch", result.stderr)

    def test_fu144_optional_regular_plans_and_metrics_restore(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / ".claude").mkdir()
            bundle = root / "state.tar.gz"
            _archive(bundle, {"agent-metrics.md": b"metrics\n", "plans/one.md": b"plan\n"})
            result = _run(RESTORE, str(bundle), "--apply", "--force", "--restore-plans",
                          "--restore-agent-metrics", "--dest", str(root / "destination"), cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / ".claude" / "agent-metrics.md").read_bytes(), b"metrics\n")
            self.assertEqual((root / ".claude" / "plans" / "one.md").read_bytes(), b"plan\n")

    def test_fu144_backup_does_not_follow_memory_link(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            audit = root / "audit"
            memory = audit / "memory"
            backup_root = root / "backups"
            outside = root / "outside.txt"
            audit.mkdir()
            memory.mkdir()
            outside.write_text("secret", encoding="utf-8")
            (memory / "link").symlink_to(outside)
            (audit / "audit-log.jsonl").write_text("{}\n", encoding="utf-8")
            result = _run(BACKUP, "--audit-dir", str(audit), "--backup-root", str(backup_root),
                          "--project-slug", "sample", cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            tarball = next((backup_root / "sample").glob("*.tar.gz"))
            with tarfile.open(tarball, "r:gz") as archive:
                self.assertNotIn("./memory/link", archive.getnames())

    def test_fu144_backup_round_trip_accepts_its_dot_root(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            audit = root / "audit"
            backup_root = root / "backups"
            audit.mkdir()
            (audit / "audit-log.jsonl").write_text("{}\n", encoding="utf-8")
            backup = _run(BACKUP, "--audit-dir", str(audit), "--backup-root", str(backup_root),
                          "--project-slug", "sample", cwd=root)
            self.assertEqual(backup.returncode, 0, backup.stderr)
            tarball = next((backup_root / "sample").glob("*.tar.gz"))
            restore = _run(RESTORE, str(tarball), "--apply", "--force",
                           "--dest", str(root / "restored"), cwd=root)
            self.assertEqual(restore.returncode, 0, restore.stderr)
            self.assertEqual((root / "restored" / "audit-log.jsonl").read_text(), "{}\n")
