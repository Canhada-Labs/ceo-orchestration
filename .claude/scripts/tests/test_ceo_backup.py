"""End-to-end tests for ceo-backup.sh + ceo-restore.sh.

Stdlib-only via unittest + subprocess. Builds a fake project tree
plus a fake CEO_AUDIT_LOG_DIR, runs backup + restore round-trip,
asserts content + SHA + rotation pruning behavior.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import unittest
from pathlib import Path
from shlex import quote as shlex_quote


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BACKUP_SH = REPO_ROOT / ".claude" / "scripts" / "ceo-backup.sh"
RESTORE_SH = REPO_ROOT / ".claude" / "scripts" / "ceo-restore.sh"


def _run(cmd, env=None, cwd=None):
    """Run a subprocess, return (rc, stdout, stderr)."""
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
        timeout=30,
    )
    return proc.returncode, proc.stdout, proc.stderr


class CEOBackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-backup-test-")).resolve()
        self.audit_dir = self.tmp / "audit-source"
        self.backup_root = self.tmp / "backups"
        self.audit_dir.mkdir()
        # Seed audit log + memory + agent-metrics
        (self.audit_dir / "audit-log.jsonl").write_text(
            '{"action": "agent_spawn", "ts": "2026-04-18T00:00:00Z"}\n',
            encoding="utf-8",
        )
        (self.audit_dir / "audit-log-2026-03.jsonl").write_text(
            '{"action": "agent_spawn", "ts": "2026-03-15T00:00:00Z"}\n',
            encoding="utf-8",
        )
        mem_dir = self.audit_dir / "memory"
        mem_dir.mkdir()
        (mem_dir / "MEMORY.md").write_text("# memory index\n", encoding="utf-8")
        (mem_dir / "user_test.md").write_text("test memory\n", encoding="utf-8")

        # Adopter root with .claude/agent-metrics.md
        self.adopter_root = self.tmp / "adopter"
        (self.adopter_root / ".claude").mkdir(parents=True)
        (self.adopter_root / ".claude" / "agent-metrics.md").write_text(
            "# metrics\n", encoding="utf-8"
        )

        self.env = os.environ.copy()
        self.env["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        self.env["CEO_BACKUP_ROOT"] = str(self.backup_root)
        self.env["CEO_PROJECT_NAME"] = "test-slug"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dry_run_creates_no_files(self):
        rc, out, err = _run(
            ["bash", str(BACKUP_SH), "--dry-run", "--quiet"],
            env=self.env,
            cwd=self.adopter_root,
        )
        self.assertEqual(rc, 0, f"stderr: {err!r}")
        # No actual backup file
        target_dir = self.backup_root / "test-slug"
        if target_dir.exists():
            self.assertEqual(list(target_dir.iterdir()), [])

    def test_creates_tarball_with_sha(self):
        rc, out, err = _run(
            ["bash", str(BACKUP_SH), "--quiet"],
            env=self.env,
            cwd=self.adopter_root,
        )
        self.assertEqual(rc, 0, f"stderr: {err}")

        tarballs = list((self.backup_root / "test-slug").glob("ceo-backup-*.tar.gz"))
        self.assertEqual(len(tarballs), 1, f"expected 1 tarball, got {tarballs}")
        sha_files = list((self.backup_root / "test-slug").glob("ceo-backup-*.tar.gz.sha256"))
        self.assertEqual(len(sha_files), 1)

    def test_tarball_contents_include_audit_memory_metrics(self):
        rc, out, err = _run(
            ["bash", str(BACKUP_SH), "--quiet"],
            env=self.env,
            cwd=self.adopter_root,
        )
        self.assertEqual(rc, 0, f"stderr: {err}")

        tarballs = list((self.backup_root / "test-slug").glob("ceo-backup-*.tar.gz"))
        with tarfile.open(tarballs[0], "r:gz") as tf:
            names = tf.getnames()

        # Tar names use ./ prefix when created from cd-into-stage
        names_norm = [n.lstrip("./") for n in names]
        self.assertIn("audit/audit-log.jsonl", names_norm)
        self.assertIn("audit/audit-log-2026-03.jsonl", names_norm)
        self.assertIn("memory/MEMORY.md", names_norm)
        self.assertIn("memory/user_test.md", names_norm)
        self.assertIn("agent-metrics.md", names_norm)
        self.assertIn("MANIFEST.txt", names_norm)

    def _extract_count_pipeline(self) -> str:
        """Pull the KEEP_LIST count one-liner out of ceo-backup.sh.

        Keeps the regression test anchored to the *actual* shipped line rather
        than a hand-copied duplicate, so a future revert of the fix is caught.
        """
        line = None
        for raw in BACKUP_SH.read_text(encoding="utf-8").splitlines():
            stripped = raw.strip()
            if stripped.startswith("KEPT_COUNT="):
                line = stripped
                break
        self.assertIsNotNone(line, "could not find KEPT_COUNT= line in ceo-backup.sh")
        return line

    def test_keep_list_count_pipeline_survives_empty_list(self):
        """Regression (Codex P2): the KEEP_LIST count must not abort on an empty
        list under `set -euo pipefail`.

        The buggy pipeline used `grep .`, which exits 1 when KEEP_LIST is empty
        (e.g. a future code path that keeps nothing). Under `set -euo pipefail`
        that non-zero exit propagates and aborts the script *before* the final
        `log "rotation: kept ..."` / `exit 0`. The fix (`awk 'NF'`) exits 0 and
        yields a count of 0. This runs the exact shipped one-liner against an
        empty KEEP_LIST and asserts it exits 0 with a count of 0.
        """
        count_line = self._extract_count_pipeline()
        script = (
            "set -euo pipefail\n"
            'KEEP_LIST=""\n'
            f"{count_line}\n"
            'printf "kept %s\\n" "$KEPT_COUNT"\n'
            'echo "reached-final-exit"\n'
        )
        rc, out, err = _run(["bash", "-c", script])
        self.assertEqual(
            rc, 0,
            f"empty KEEP_LIST aborted the count pipeline (rc={rc}); stderr={err!r}",
        )
        self.assertIn("kept 0", out)
        self.assertIn("reached-final-exit", out)

    def test_keep_list_count_pipeline_dedups_non_empty(self):
        """The fix must preserve retention-count semantics for non-empty lists:
        blank leading line dropped, duplicates collapsed (daily slot + week/month
        rep can list the same backup twice).
        """
        count_line = self._extract_count_pipeline()
        b1 = "ceo-backup-2026-04-18T000000Z.tar.gz"
        b2 = "ceo-backup-2026-04-17T000000Z.tar.gz"
        # Mirrors how the script builds KEEP_LIST: leading blank + a duplicate.
        keep_list = "\n".join(["", b1, b2, b1])
        script = (
            "set -euo pipefail\n"
            f"KEEP_LIST={shlex_quote(keep_list)}\n"
            f"{count_line}\n"
            'printf "%s\\n" "$KEPT_COUNT"\n'
        )
        rc, out, err = _run(["bash", "-c", script])
        self.assertEqual(rc, 0, f"stderr: {err!r}")
        self.assertEqual(out.strip(), "2", f"expected 2 unique kept, got {out!r}")

    def test_includes_plans_with_flag(self):
        # Add plans subdir
        plans = self.adopter_root / ".claude" / "plans"
        plans.mkdir()
        (plans / "PLAN-001-test.md").write_text("---\nid: PLAN-001\n---\n", encoding="utf-8")

        rc, out, err = _run(
            ["bash", str(BACKUP_SH), "--include-plans", "--quiet"],
            env=self.env,
            cwd=self.adopter_root,
        )
        self.assertEqual(rc, 0, f"stderr: {err}")

        tarballs = list((self.backup_root / "test-slug").glob("ceo-backup-*.tar.gz"))
        with tarfile.open(tarballs[0], "r:gz") as tf:
            names = [n.lstrip("./") for n in tf.getnames()]

        self.assertIn("plans/PLAN-001-test.md", names)


class CEORestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-restore-test-")).resolve()
        self.audit_dir = self.tmp / "audit-source"
        self.audit_dir.mkdir()
        (self.audit_dir / "audit-log.jsonl").write_text(
            '{"action": "agent_spawn", "ts": "2026-04-18T00:00:00Z"}\n',
            encoding="utf-8",
        )
        mem_dir = self.audit_dir / "memory"
        mem_dir.mkdir()
        (mem_dir / "MEMORY.md").write_text("# memory\n", encoding="utf-8")

        self.adopter_root = self.tmp / "adopter"
        (self.adopter_root / ".claude").mkdir(parents=True)

        self.backup_root = self.tmp / "backups"

        self.env = os.environ.copy()
        self.env["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        self.env["CEO_BACKUP_ROOT"] = str(self.backup_root)
        self.env["CEO_PROJECT_NAME"] = "test-slug"

        # Create a backup
        rc, _, err = _run(
            ["bash", str(BACKUP_SH), "--quiet"],
            env=self.env,
            cwd=self.adopter_root,
        )
        assert rc == 0, f"backup setup failed: {err}"
        self.tarball = list((self.backup_root / "test-slug").glob("*.tar.gz"))[0]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dry_run_default(self):
        rc, out, err = _run(
            ["bash", str(RESTORE_SH), str(self.tarball)],
            env=self.env,
        )
        # Dry-run prints to stderr (when --quiet not set) — exit 0 + no extraction
        self.assertEqual(rc, 0)

    def test_sha_mismatch_blocks(self):
        # Tamper SHA sidecar
        sha_file = Path(str(self.tarball) + ".sha256")
        sha_file.write_text("0000000000000000000000000000000000000000000000000000000000000000\n", encoding="utf-8")

        rc, out, err = _run(
            ["bash", str(RESTORE_SH), str(self.tarball), "--apply", "--force"],
            env=self.env,
        )
        self.assertEqual(rc, 2, f"expected SHA mismatch fatal, got rc={rc}, stderr={err}")
        self.assertIn("SHA256 mismatch", err)

    def test_round_trip(self):
        # Wipe destination
        dest = self.tmp / "fresh-dest"
        dest.mkdir()

        rc, out, err = _run(
            [
                "bash", str(RESTORE_SH), str(self.tarball),
                "--apply", "--force", "--quiet",
                "--dest", str(dest),
            ],
            env=self.env,
        )
        self.assertEqual(rc, 0, f"stderr: {err}")

        # Verify content restored
        self.assertTrue((dest / "audit-log.jsonl").is_file())
        self.assertTrue((dest / "memory" / "MEMORY.md").is_file())


class CheckUpdatesTests(unittest.TestCase):
    """Tests for check-framework-updates.sh — uses --version-file to avoid CWD walk."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-updates-test-")).resolve()
        self.script = REPO_ROOT / ".claude" / "scripts" / "check-framework-updates.sh"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, version: str, *extra):
        vfile = self.tmp / "VERSION"
        vfile.write_text(version + "\n", encoding="utf-8")
        return _run(
            ["bash", str(self.script), "--version-file", str(vfile), "--quiet", *extra],
        )

    def test_malformed_version_fatal(self):
        rc, _, err = self._run("not-a-version")
        self.assertEqual(rc, 3)
        self.assertIn("malformed", err)

    def test_missing_version_file_fatal(self):
        rc, _, _ = _run([
            "bash", str(self.script),
            "--version-file", str(self.tmp / "no-such-file"),
            "--quiet",
        ])
        self.assertEqual(rc, 3)

    def test_unreachable_upstream_returns_unknown(self):
        # Use an unreachable URL — should NOT page (exit 0)
        rc, _, _ = self._run(
            "1.6.0-rc.1",
            "--upstream", "https://example.invalid/no-such-repo",
        )
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
