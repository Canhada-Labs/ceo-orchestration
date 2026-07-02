"""PLAN-152 security-01 — `_python-hook.sh` interpreter-cache trust gate.

The shim caches the resolved interpreter path under
``${TMPDIR}/ceo-pyhook-$(id -u)/resolved-py-<PATH-sig>`` and, on a cache
hit, EXECs the cached path. Pre-PLAN-152 the read had no ownership /
symlink verification (TOCTOU: a rogue cache under a shared /tmp could
plant an attacker-chosen interpreter), and a symlinked cache DIR would
redirect the cache WRITE to an attacker-chosen location.

Positive + negative coverage per the Wave A Check line (debate C4):

- negative: a SYMLINKED cache file / cache dir is rejected (falls back
  to the probe; the planted fake interpreter never runs; nothing is
  written through a symlinked dir);
- positive: a legitimate owner-created regular cache file is still
  accepted (no over-block — the cached interpreter IS used).

Foreign-owned (other-uid) rejection cannot be simulated without root;
the ownership comparison shares the code path exercised by the symlink
cases (`_cache_dir_trusted` / `_cache_file_trusted`).
"""
from __future__ import annotations

import hashlib
import os
import stat
import subprocess
import sys
from pathlib import Path

from _lib.testing import TestEnvContext  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SHIM = REPO_ROOT / ".claude" / "hooks" / "_python-hook.sh"

# A benign payload for a real, fast hook: check_plan_edit.py ignores
# non-plan paths and emits {} — enough to force the shim to EXEC the
# resolved interpreter.
_BENIGN_STDIN = '{"tool_name":"Edit","tool_input":{"file_path":"/tmp/nonplan.txt"}}'
_REAL_HOOK = "check_plan_edit.py"
# A hook name that does NOT exist: the shim resolves + caches the
# interpreter, then prints `hook not found` + {} WITHOUT exec'ing it —
# used to exercise the cache-WRITE path in isolation.
_BOGUS_HOOK = "definitely_not_a_hook_plan152.py"

_FAKE_SENTINEL = "FAKE-INTERPRETER-RAN"
_WRAPPER_SENTINEL = "CACHE-WRAPPER-USED"


class ShimCacheTrustTest(TestEnvContext):
    def setUp(self):  # noqa: D102
        super().setUp()
        # PATH must offer the coreutils the shim needs (id/stat/shasum or
        # sha256sum) plus a resolvable python3* ≥3.9 for the probe branch.
        self.env_path = ":".join(
            [str(Path(sys.executable).parent), "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
        )
        self.tmp = self.home_dir / "shimtmp"
        self.tmp.mkdir()
        self.cache_dir = self.tmp / f"ceo-pyhook-{os.getuid()}"
        # Replicates the shim's `_path_hash` (sha256 of $PATH, first 16
        # hex chars — shasum -a 256 / sha256sum agree on the digest).
        self.path_sig = hashlib.sha256(self.env_path.encode()).hexdigest()[:16]
        self.cache_file = self.cache_dir / f"resolved-py-{self.path_sig}"

    def _run_shim(self, hook_name: str) -> "subprocess.CompletedProcess":
        env = {
            "PATH": self.env_path,
            "TMPDIR": str(self.tmp),
            "HOME": str(self.home_dir),
            "CLAUDE_PROJECT_DIR": str(self.project_dir),
        }
        return subprocess.run(
            ["bash", str(SHIM), hook_name],
            input=_BENIGN_STDIN,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

    def _write_fake_interpreter(self) -> Path:
        fake = self.tmp / "fakepy"
        fake.write_text(f"#!/bin/bash\necho {_FAKE_SENTINEL}\nexit 0\n", encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return fake

    def _write_wrapper_interpreter(self) -> Path:
        wrapper = self.tmp / "wrapperpy"
        wrapper.write_text(
            "#!/bin/bash\n"
            f"echo {_WRAPPER_SENTINEL} >&2\n"
            f'exec "{sys.executable}" "$@"\n',
            encoding="utf-8",
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
        return wrapper

    # ---- negative: symlinked cache FILE is rejected ----

    def test_symlinked_cache_file_rejected(self):
        fake = self._write_fake_interpreter()
        self.cache_dir.mkdir(mode=0o700)
        evil = self.tmp / "evil-cache-content"
        evil.write_text(f"{fake}\n", encoding="utf-8")
        self.cache_file.symlink_to(evil)

        proc = self._run_shim(_REAL_HOOK)

        self.assertNotIn(_FAKE_SENTINEL, proc.stdout + proc.stderr)
        self.assertIn("{}", proc.stdout)  # real interpreter ran the hook
        self.assertEqual(proc.returncode, 0)

    # ---- negative: symlinked cache DIR is rejected (read AND write) ----

    def test_symlinked_cache_dir_rejected_read_and_write(self):
        fake = self._write_fake_interpreter()
        target = self.tmp / "attacker-target-dir"
        target.mkdir(mode=0o700)
        (target / f"resolved-py-{self.path_sig}").write_text(
            f"{fake}\n", encoding="utf-8"
        )
        self.cache_dir.symlink_to(target)

        proc = self._run_shim(_REAL_HOOK)

        # Read side: the planted interpreter is ignored (pre-fix it would
        # be EXEC'd for the real hook and print the sentinel); the shim
        # falls back to the probe and a real python runs the hook.
        self.assertNotIn(_FAKE_SENTINEL, proc.stdout + proc.stderr)
        self.assertIn("{}", proc.stdout)
        # Write side: the probe result is NOT cached through the symlink —
        # the only file in the attacker dir is the one planted above.
        self.assertEqual(
            [p.name for p in target.iterdir()],
            [f"resolved-py-{self.path_sig}"],
        )
        # And the planted content was not overwritten by the probe result.
        self.assertIn(
            str(fake), (target / f"resolved-py-{self.path_sig}").read_text(encoding="utf-8")
        )

    # ---- negative: user-owned but group/world-writable dir is rejected ----

    def test_group_world_writable_cache_dir_rejected(self):
        """PLAN-152 security-01 P2 (Codex R2): a user-owned but 0777 cache
        dir lets another local user swap the cache file between the trust
        check and the read (TOCTOU). The dir-mode gate must reject it, so
        the planted interpreter never runs."""
        wrapper = self._write_wrapper_interpreter()
        self.cache_dir.mkdir(mode=0o777)
        os.chmod(self.cache_dir, 0o777)  # defeat umask
        self.cache_file.write_text(f"{wrapper}\n", encoding="utf-8")

        proc = self._run_shim(_REAL_HOOK)

        # Cache NOT trusted → probe path → the wrapper's sentinel is absent.
        self.assertNotIn(_WRAPPER_SENTINEL, proc.stderr)
        self.assertIn("{}", proc.stdout)
        self.assertEqual(proc.returncode, 0)

    # ---- positive: legitimate owner cache is still accepted ----

    def test_legitimate_cache_still_used(self):
        wrapper = self._write_wrapper_interpreter()
        self.cache_dir.mkdir(mode=0o700)
        self.cache_file.write_text(f"{wrapper}\n", encoding="utf-8")

        proc = self._run_shim(_REAL_HOOK)

        self.assertIn(_WRAPPER_SENTINEL, proc.stderr)  # cache WAS used
        self.assertIn("{}", proc.stdout)
        self.assertEqual(proc.returncode, 0)

    # ---- positive: cold start writes a cache the gates accept ----

    def test_cold_start_probe_populates_trusted_cache(self):
        proc = self._run_shim(_BOGUS_HOOK)
        self.assertIn("{}", proc.stdout)
        self.assertTrue(self.cache_file.is_file())
        self.assertFalse(self.cache_file.is_symlink())
        self.assertEqual(self.cache_file.stat().st_uid, os.getuid())
