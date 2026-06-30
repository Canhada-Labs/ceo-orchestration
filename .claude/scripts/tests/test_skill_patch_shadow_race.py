"""Shadow-apply concurrency (PLAN-012 Phase 3 D4 / debate HIGH-3).

Validates `skill-patch-apply.py` filelock + quarantine invariants:
concurrent applies serialize; lock releases cleanly; different skills
parallelize; quarantine blocks next apply; `--force-recover` clears;
lock timeout emits `shadow_concurrent_apply_blocked` breadcrumb.

Requires `gpg` on PATH (tests skip otherwise).
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import textwrap
import threading
import time
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402
from _lib.filelock import FileLock  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_APPLY = _REPO_ROOT / ".claude" / "scripts" / "skill-patch-apply.py"
_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
_spec = importlib.util.spec_from_file_location(
    "gpg_keyring_fixture", _FIXTURE_DIR / "gpg-keyring-fixture.py",
)
_gpg_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_gpg_mod)


def _proposal_body(skill_slug: str, proposal_id: str) -> str:
    return textwrap.dedent(f"""\
        ---
        id: {proposal_id}
        skill_slug: {skill_slug}
        archetype: staff-backend
        proposed_at: 2026-04-14T10:00:00Z
        source_lessons:
          - l-fixture-001
        scan_injection_pass: true
        diff_size_added: 1
        diff_size_removed: 0
        sha256_of_diff: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
        claims_declared: false
        status: draft
        approved_by: null
        applied_at: null
        promoted_at: null
        shadow_mode: true
        ---

        ```diff
        --- a/SKILL.md
        +++ b/SKILL.md
        @@ -3,0 +4,1 @@
        +- race-test lesson appended to {skill_slug}
        ```
        """)


class ShadowApplyConcurrencyTest(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        try:
            self._keyring = _gpg_mod.GpgKeyringFixture().__enter__()
        except _gpg_mod.GpgUnavailable:
            self.skipTest("gpg binary not available on PATH")
        self.addCleanup(self._keyring.__exit__, None, None, None)
        # Restore GNUPGHOME on teardown — the keyring __exit__ rmtree's the dir
        # but never touches the env var, and TestEnvContext doesn't snapshot
        # GNUPGHOME, so it leaks at a deleted dir into later sequential gpg tests.
        self.addCleanup(
            lambda _g=os.environ.get("GNUPGHOME"):
            os.environ.__setitem__("GNUPGHOME", _g) if _g is not None
            else os.environ.pop("GNUPGHOME", None)
        )
        os.environ["GNUPGHOME"] = str(self._keyring.gnupg_home)

        hooks_lib = self.project_dir / ".claude" / "hooks" / "_lib"
        hooks_lib.mkdir(parents=True, exist_ok=True)
        src = _REPO_ROOT / ".claude" / "hooks" / "_lib"
        # PLAN-045 Wave 1 P0-02: skill-patch-apply now imports
        # _lib.gpg_verify; copy it alongside filelock.
        for fname in ("__init__.py", "filelock.py", "gpg_verify.py"):
            (hooks_lib / fname).write_text(
                (src / fname).read_text(encoding="utf-8"), encoding="utf-8"
            )
        (self.project_dir / ".claude" / "hooks" / "__init__.py").write_text(
            "", encoding="utf-8"
        )
        # PLAN-045 Wave 1 P0-02: allowlist with the test-keyring fpr so
        # skill-patch-apply accepts the throwaway signer.
        signers_file = self.project_dir / ".claude" / "skill-patch-signers.txt"
        signers_file.write_text(
            f"# test fixture\n{self._keyring.fingerprint}\n",
            encoding="utf-8",
        )

        self.skill_slug = "race-skill"
        skill_dir = self.project_dir / ".claude" / "skills" / "core" / self.skill_slug
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Race\n\nBody.\n", encoding="utf-8")
        self.shadow_path = skill_dir / "SKILL.md.shadow.md"

        self.proposals_dir = self.project_dir / ".claude" / "proposals"
        self.proposals_dir.mkdir(parents=True, exist_ok=True)
        self.proposal_id = "SP-001"
        self.proposal_path = self.proposals_dir / f"{self.proposal_id}-race.md"
        self.proposal_path.write_text(
            _proposal_body(self.skill_slug, self.proposal_id), encoding="utf-8"
        )
        self.sig_path = self._keyring.sign(self.proposal_path)

    def _apply_cmd(self, *extra):
        return [sys.executable, str(_APPLY),
                "--proposal", self.proposal_id,
                "--signature", str(self.sig_path),
                "--confirm", f"I have read {self.proposal_id}", *extra]

    def _env(self):
        e = os.environ.copy()
        e["CLAUDE_PROJECT_DIR"] = str(self.project_dir)
        e["GNUPGHOME"] = str(self._keyring.gnupg_home)
        return e

    # ---- tests ----

    def test_concurrent_apply_produces_well_formed_shadow(self):
        """Two simultaneous applies serialize; shadow is not corrupt."""
        cmd, env = self._apply_cmd(), self._env()
        results, lk = [], threading.Lock()

        def _run(idx):
            p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
            with lk:
                results.append((idx, p.returncode, p.stderr))

        t1 = threading.Thread(target=_run, args=(1,))
        t2 = threading.Thread(target=_run, args=(2,))
        t1.start(); t2.start(); t1.join(70); t2.join(70)
        self.assertEqual(len(results), 2)

        rcs = sorted(r[1] for r in results)
        self.assertIn(0, rcs, msg=results)
        # Acceptable codes: 0 (success) or 2 (sig invalidated by first's
        # frontmatter mutation). Lock timeout (1) would indicate a bug.
        for r in results:
            self.assertIn(r[1], (0, 2), msg=results)

        self.assertTrue(self.shadow_path.is_file())
        content = self.shadow_path.read_text(encoding="utf-8")
        self.assertIn("race-test lesson appended to race-skill", content)
        self.assertTrue(content.endswith("\n"))
        partial = self.shadow_path.with_name(self.shadow_path.name + ".partial")
        quarantine = self.shadow_path.with_name(self.shadow_path.name + ".quarantine")
        self.assertFalse(partial.exists())
        self.assertFalse(quarantine.exists())

    def test_lock_released_on_normal_exit(self):
        """After successful apply the fcntl lock is released."""
        p = subprocess.run(self._apply_cmd(), capture_output=True, text=True,
                           env=self._env(), timeout=60)
        self.assertEqual(p.returncode, 0, msg=p.stderr)
        lock_file = self.shadow_path.with_name(self.shadow_path.name + ".lock")
        self.assertTrue(lock_file.exists())
        t0 = time.monotonic()
        lk = FileLock(str(lock_file), timeout=1.0); lk.acquire()
        self.assertLess(time.monotonic() - t0, 0.5)
        lk.release()

    def test_different_skills_apply_concurrently(self):
        """Per-skill lock: different skills race independently (no queue)."""
        second_slug = "race-skill-2"
        second_dir = self.project_dir / ".claude" / "skills" / "core" / second_slug
        second_dir.mkdir(parents=True, exist_ok=True)
        (second_dir / "SKILL.md").write_text("# Race 2\n\nBody.\n", encoding="utf-8")
        second_proposal = self.proposals_dir / "SP-002-race.md"
        second_proposal.write_text(
            _proposal_body(second_slug, "SP-002"), encoding="utf-8"
        )
        second_sig = self._keyring.sign(second_proposal)

        def _c(pid, sig):
            return [sys.executable, str(_APPLY),
                    "--proposal", pid, "--signature", str(sig),
                    "--confirm", f"I have read {pid}"]

        t0 = time.monotonic()
        p1 = subprocess.Popen(self._apply_cmd(), env=self._env(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p2 = subprocess.Popen(_c("SP-002", second_sig), env=self._env(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(p1.wait(timeout=60), 0)
        self.assertEqual(p2.wait(timeout=60), 0)
        self.assertLess(time.monotonic() - t0, 25.0)
        self.assertTrue(self.shadow_path.is_file())
        self.assertTrue((second_dir / "SKILL.md.shadow.md").is_file())

    def test_quarantine_blocks_next_apply(self):
        """`.quarantine` sibling present → apply returns 6."""
        q = self.shadow_path.with_name(self.shadow_path.name + ".quarantine")
        q.write_text("forensic\n", encoding="utf-8")
        p = subprocess.run(self._apply_cmd(), capture_output=True, text=True,
                           env=self._env(), timeout=15)
        self.assertEqual(p.returncode, 6, msg=p.stderr)
        self.assertIn("quarantine", p.stderr.lower())
        self.assertFalse(self.shadow_path.exists())

    def test_force_recover_clears_quarantine_and_partial(self):
        """--force-recover removes quarantine + partial then exits 0."""
        q = self.shadow_path.with_name(self.shadow_path.name + ".quarantine")
        pr = self.shadow_path.with_name(self.shadow_path.name + ".partial")
        q.write_text("q\n", encoding="utf-8")
        pr.write_text("p\n", encoding="utf-8")
        r = subprocess.run(self._apply_cmd("--force-recover"),
                           capture_output=True, text=True, env=self._env(), timeout=15)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertFalse(q.exists())
        self.assertFalse(pr.exists())
        # Normal apply then succeeds.
        r2 = subprocess.run(self._apply_cmd(), capture_output=True, text=True,
                            env=self._env(), timeout=30)
        self.assertEqual(r2.returncode, 0, msg=r2.stderr)
        self.assertTrue(self.shadow_path.is_file())

    def test_force_recover_no_quarantine_exits_6(self):
        """--force-recover on clean state is a no-op refusal."""
        p = subprocess.run(self._apply_cmd("--force-recover"),
                           capture_output=True, text=True, env=self._env(), timeout=15)
        self.assertEqual(p.returncode, 6)

    def test_lock_timeout_emits_breadcrumb(self):
        """Peer holds lock > timeout → rc=1 + `shadow_concurrent_apply_blocked`."""
        lock_file = self.shadow_path.with_name(self.shadow_path.name + ".lock")
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lk = FileLock(str(lock_file), timeout=1.0); lk.acquire()
        try:
            wrapper = textwrap.dedent(f"""
                import importlib.util, sys
                spec = importlib.util.spec_from_file_location('m', {str(_APPLY)!r})
                m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
                m._LOCK_TIMEOUT_SECS = 1.0
                sys.exit(m.main([
                    '--proposal', {self.proposal_id!r},
                    '--signature', {str(self.sig_path)!r},
                    '--confirm', {f'I have read {self.proposal_id}'!r},
                ]))
            """).strip()
            p = subprocess.run([sys.executable, "-c", wrapper],
                               capture_output=True, text=True,
                               env=self._env(), timeout=30)
            self.assertEqual(p.returncode, 1, msg=p.stderr)
            self.assertIn("shadow_concurrent_apply_blocked", p.stderr)
            self.assertIn("lock_timeout", p.stderr)
        finally:
            lk.release()


if __name__ == "__main__":
    unittest.main()
