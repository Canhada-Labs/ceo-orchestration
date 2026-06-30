"""Chaos — SIGTERM during `skill-patch-apply` mid-write (PLAN-012 Phase 3 D4).

Gated by CEO_CHAOS_ALLOWED=1 per ADR-037. Launches apply with a
2-second pause pinned between `.partial` write + rename, delivers
SIGTERM during that window, and asserts the signal handler renamed
`.partial` → `.quarantine` (no corrupt `.shadow.md`). Next apply
refuses until `--force-recover`, which succeeds.
"""

from __future__ import annotations

import importlib.util
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("CEO_CHAOS_ALLOWED") != "1",
    reason="gated by CEO_CHAOS_ALLOWED=1 per ADR-037",
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_APPLY = _REPO_ROOT / ".claude" / "scripts" / "skill-patch-apply.py"
_FIXTURE_DIR = _REPO_ROOT / ".claude" / "scripts" / "tests" / "fixtures"
_spec = importlib.util.spec_from_file_location(
    "gpg_keyring_fixture", _FIXTURE_DIR / "gpg-keyring-fixture.py",
)
_gpg_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_gpg_mod)


def _proposal_body(skill_slug: str, pid: str) -> str:
    return textwrap.dedent(f"""\
        ---
        id: {pid}
        skill_slug: {skill_slug}
        archetype: staff-backend
        proposed_at: 2026-04-14T10:00:00Z
        source_lessons:
          - l-chaos-001
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
        +- chaos-test lesson appended to {skill_slug}
        ```
        """)


class ShadowApplyKillTest(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        try:
            self._kr = _gpg_mod.GpgKeyringFixture().__enter__()
        except _gpg_mod.GpgUnavailable:
            self.skipTest("gpg binary not on PATH")
        self.addCleanup(self._kr.__exit__, None, None, None)
        os.environ["GNUPGHOME"] = str(self._kr.gnupg_home)

        hooks_lib = self.project_dir / ".claude" / "hooks" / "_lib"
        hooks_lib.mkdir(parents=True, exist_ok=True)
        src = _REPO_ROOT / ".claude" / "hooks" / "_lib"
        for n in ("__init__.py", "filelock.py"):
            (hooks_lib / n).write_text(
                (src / n).read_text(encoding="utf-8"), encoding="utf-8"
            )
        (self.project_dir / ".claude" / "hooks" / "__init__.py").write_text(
            "", encoding="utf-8"
        )

        self.skill_slug = "chaos-skill"
        skill_dir = self.project_dir / ".claude" / "skills" / "core" / self.skill_slug
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("# Chaos\n\nBody.\n", encoding="utf-8")
        self.shadow = skill_dir / "SKILL.md.shadow.md"

        p_dir = self.project_dir / ".claude" / "proposals"
        p_dir.mkdir(parents=True, exist_ok=True)
        self.pid = "SP-001"
        self.proposal = p_dir / f"{self.pid}-chaos.md"
        self.proposal.write_text(
            _proposal_body(self.skill_slug, self.pid), encoding="utf-8"
        )
        self.sig = self._kr.sign(self.proposal)

    def _env(self):
        e = os.environ.copy()
        e["CLAUDE_PROJECT_DIR"] = str(self.project_dir)
        e["GNUPGHOME"] = str(self._kr.gnupg_home)
        return e

    def _launch_slow_apply(self, delay_secs: float = 2.0):
        wrapper = textwrap.dedent(f"""
            import importlib.util, os, sys, time
            spec = importlib.util.spec_from_file_location('m', {str(_APPLY)!r})
            m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
            def _slow(shadow_path, content):
                partial = m._partial_path_for(shadow_path)
                m._INFLIGHT_PARTIAL = partial
                try:
                    with partial.open('w', encoding='utf-8') as f:
                        f.write(content)
                        try: f.flush(); os.fsync(f.fileno())
                        except Exception: pass
                    time.sleep({delay_secs})
                    os.replace(partial, shadow_path)
                finally:
                    m._INFLIGHT_PARTIAL = None
            m._atomic_shadow_write = _slow
            sys.exit(m.main([
                '--proposal', {self.pid!r},
                '--signature', {str(self.sig)!r},
                '--confirm', {f'I have read {self.pid}'!r},
            ]))
        """).strip()
        return subprocess.Popen(
            [sys.executable, "-c", wrapper], env=self._env(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    # ---- tests ----

    def test_sigterm_midwrite_quarantines_partial(self):
        """SIGTERM during write → `.quarantine` present, shadow absent."""
        proc = self._launch_slow_apply(2.0)
        time.sleep(1.0)  # slip past GPG verify into the sleep window
        proc.send_signal(signal.SIGTERM)
        rc = proc.wait(timeout=10)
        stderr = (proc.stderr.read() or b"").decode("utf-8", "replace")

        self.assertFalse(self.shadow.exists(), msg=stderr)
        q = self.shadow.with_name(self.shadow.name + ".quarantine")
        p = self.shadow.with_name(self.shadow.name + ".partial")
        self.assertTrue(q.exists(), msg=f"no quarantine; stderr={stderr!r}")
        self.assertFalse(p.exists())
        self.assertEqual(rc, 128 + int(signal.SIGTERM))

    def test_quarantine_preserves_partial_content_for_forensics(self):
        """Quarantined file keeps the content that was being written."""
        proc = self._launch_slow_apply(2.0)
        time.sleep(1.0)
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=10)
        q = self.shadow.with_name(self.shadow.name + ".quarantine")
        self.assertTrue(q.is_file())
        self.assertIn(
            "chaos-test lesson appended to chaos-skill",
            q.read_text(encoding="utf-8"),
        )

    def test_next_apply_refuses_then_force_recover_succeeds(self):
        """After quarantine: next apply rc=6; `--force-recover` rc=0."""
        proc = self._launch_slow_apply(2.0)
        time.sleep(1.0)
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=10)

        cmd = [sys.executable, str(_APPLY),
               "--proposal", self.pid,
               "--signature", str(self.sig),
               "--confirm", f"I have read {self.pid}"]
        second = subprocess.run(cmd, capture_output=True, text=True,
                                env=self._env(), timeout=30)
        self.assertEqual(second.returncode, 6, msg=second.stderr)
        self.assertIn("quarantine", second.stderr.lower())

        rec = subprocess.run(cmd + ["--force-recover"], capture_output=True,
                             text=True, env=self._env(), timeout=15)
        self.assertEqual(rec.returncode, 0, msg=rec.stderr)
        self.assertFalse(
            self.shadow.with_name(self.shadow.name + ".quarantine").exists()
        )


if __name__ == "__main__":  # pragma: no cover
    import unittest
    unittest.main()
