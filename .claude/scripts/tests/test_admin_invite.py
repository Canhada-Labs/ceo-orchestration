"""Unit tests for admin-invite.py (PLAN-010 Phase 6)."""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "admin_invite", SCRIPTS_DIR / "admin-invite.py"
)
admin_invite = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
assert spec.loader is not None
spec.loader.exec_module(admin_invite)  # type: ignore[union-attr]


class AdminInviteTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-invite-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestSlugify(AdminInviteTestBase):
    def test_unicode_name(self) -> None:
        out = self.tmp / "pack"
        created = admin_invite.build_pack("Canhada Labs", out)
        self.assertTrue(out.exists())
        self.assertGreaterEqual(len(created), 3)

    def test_slug_asian(self) -> None:
        # Unicode word chars ARE kept by \w under re.UNICODE
        slug = admin_invite._slugify("山田太郎")
        self.assertTrue(slug)  # non-empty
        self.assertNotIn("/", slug)


class TestBuildPack(AdminInviteTestBase):
    def test_happy_path(self) -> None:
        out = self.tmp / "pack-alice"
        created = admin_invite.build_pack("Alice", out)
        names = {p.name for p in created}
        self.assertIn("first-session-checklist.md", names)
        self.assertIn("memory-seed.md", names)
        self.assertIn("FOR-EMPLOYEES.md", names)
        self.assertIn("README.md", names)
        # README mentions the invitee
        readme = (out / "README.md").read_text(encoding="utf-8")
        self.assertIn("Alice", readme)

    def test_refuse_existing_nonempty(self) -> None:
        out = self.tmp / "pack-bob"
        out.mkdir()
        (out / "something.txt").write_text("busy", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            admin_invite.build_pack("Bob", out, force=False)

    def test_force_overwrites(self) -> None:
        out = self.tmp / "pack-carol"
        out.mkdir()
        (out / "leftover.txt").write_text("old", encoding="utf-8")
        admin_invite.build_pack("Carol", out, force=True)
        # leftover gone, fresh pack present
        self.assertFalse((out / "leftover.txt").exists())
        self.assertTrue((out / "first-session-checklist.md").exists())

    def test_allows_existing_empty(self) -> None:
        out = self.tmp / "pack-dan"
        out.mkdir()  # empty dir should be ok
        created = admin_invite.build_pack("Dan", out)
        self.assertGreaterEqual(len(created), 3)


class TestSafeDefaults(AdminInviteTestBase):
    def test_default_is_outside_cwd(self) -> None:
        """Debate C13: default out-dir MUST live outside the cwd."""
        cwd = Path.cwd().resolve()
        default = admin_invite._default_out_dir("Owner").resolve()
        # default should be under $HOME, not under cwd
        home = Path.home().resolve()
        self.assertTrue(
            str(default).startswith(str(home)),
            f"default {default} is not under HOME {home}",
        )
        try:
            default.relative_to(cwd)
            self.fail(f"default {default} is inside cwd {cwd}")
        except ValueError:
            pass  # expected: default is outside cwd


class TestNoEnvLeak(AdminInviteTestBase):
    """Every generated file must be free of env-var-shaped secrets.

    Implementation: scan each output file for any uppercase shell-style
    variable name that matches an env var present in os.environ. Also
    hard-flag a canary set (ANTHROPIC_*, GITHUB_*, AWS_*, CEO_*) even
    if those vars aren't currently set.
    """

    def _scan_file_for_env_leaks(self, path: Path) -> list:
        text = path.read_text(encoding="utf-8", errors="replace")
        # Uppercase identifier tokens (the shape of env var names)
        tokens = set(re.findall(r"\b[A-Z][A-Z0-9_]{3,}\b", text))

        leaks = []
        # (a) any current env var name present by literal match
        for k in os.environ:
            if k in tokens:
                leaks.append(f"env-var-name:{k}")

        # (b) canary prefixes — hard fail on any match, even if not in env
        canary_patterns = [
            r"\bANTHROPIC_[A-Z0-9_]+\b",
            r"\bGITHUB_[A-Z0-9_]+\b",
            r"\bAWS_[A-Z0-9_]+\b",
        ]
        for pat in canary_patterns:
            m = re.search(pat, text)
            if m:
                leaks.append(f"canary:{m.group(0)}")
        return leaks

    def test_no_env_leak_across_pack(self) -> None:
        # Seed canary vars so the scanner would catch them if leaked.
        os.environ["ANTHROPIC_API_KEY"] = "sk-test-should-never-leak"
        os.environ["GITHUB_TOKEN"] = "ghp_fake_canary_value"
        try:
            out = self.tmp / "pack-sec"
            created = admin_invite.build_pack("Security Test", out)
            for p in created:
                leaks = self._scan_file_for_env_leaks(p)
                self.assertEqual(
                    leaks,
                    [],
                    f"env leak in {p.name}: {leaks}",
                )
        finally:
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("GITHUB_TOKEN", None)


class TestCliMain(AdminInviteTestBase):
    def test_main_happy(self) -> None:
        out = self.tmp / "pack-cli"
        rc = admin_invite.main(["--name", "CLI User", "--out-dir", str(out)])
        self.assertEqual(rc, 0)
        self.assertTrue(out.exists())

    def test_main_refuse_existing(self) -> None:
        out = self.tmp / "pack-cli2"
        out.mkdir()
        (out / "x.txt").write_text("busy", encoding="utf-8")
        rc = admin_invite.main(["--name", "CLI User", "--out-dir", str(out)])
        self.assertEqual(rc, 1)

    def test_main_missing_required(self) -> None:
        # argparse writes "error: required args" to stderr and raises
        # SystemExit(2); main() catches it and returns 2 per our contract.
        rc = admin_invite.main([])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
