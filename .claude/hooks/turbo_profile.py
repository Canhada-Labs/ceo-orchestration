"""turbo_profile — zero-config opt-out for PLAN-128 Wave-2 acceleration.

Module: PLAN-128 §5 Zero-config + opt-out + Wave-2 zero-config first-run.
This module provides the master on/off switch (is_turbo_off), status visibility
(accelerators_status, whats_on_line), and first-run tracking for the turbo
acceleration layer. All functions fail-open: on any exception, they return the
safe default (e.g., is_turbo_off→False = accelerators stay ON, unless they
fail on FS read in which case we log a breadcrumb and do NOT raise).
"""

from __future__ import annotations

import os
import stat
import sys
from typing import Dict, Optional


def is_turbo_off(project_dir: str) -> bool:
    """Return True if turbo acceleration is explicitly disabled.

    Turbo is off if:
      - os.environ.get("CEO_TURBO") == "0", OR
      - a file exists at <project_dir>/.claude/turbo-off

    SECURITY: only check existence of the literal basename "turbo-off"
    directly under <project_dir>/.claude/ — never follow a path from env
    into os.path.join with attacker data; never read the file's contents
    (presence only). Reject symlinked markers (existence-leak P1).

    FAIL-OPEN: on any exception, return False (turbo stays ON, safe for
    advisory layer).
    """
    try:
        # Check CEO_TURBO=0 master switch
        if os.environ.get("CEO_TURBO") == "0":
            return True

        # Check for turbo-off file: safe path construction
        # Only use project_dir (from caller, trusted) + literal ".claude/turbo-off"
        turbo_off_path = os.path.join(project_dir, ".claude", "turbo-off")

        # Verify the path is as expected before stat (defense in depth)
        # Structural check: basename must be "turbo-off" and parent dirname must be ".claude"
        if os.path.basename(turbo_off_path) != "turbo-off" or os.path.basename(os.path.dirname(turbo_off_path)) != ".claude":
            # Path construction failed or was injected; fail-open
            return False

        # Atomic lstat check: does NOT follow symlinks; symlinks report S_ISLNK, not S_ISREG
        # This prevents TOCTOU (islink/isfile sequence) and symlink-following attacks
        try:
            st = os.lstat(turbo_off_path)
        except OSError:
            return False
        return stat.S_ISREG(st.st_mode)
    except Exception:
        # Any FS error, type error, etc.: fail-open (turbo stays ON)
        return False


def accelerators_status(project_dir: str, env: Optional[dict] = None) -> Dict[str, str]:
    """Return the status of each accelerator as an ordered dict.

    Keys: "verify", "codex_review", "adequacy", "subagent_model", "master"

    If is_turbo_off(project_dir) is True, all accelerators report "off"
    and master reports "OFF (turbo-off)".

    Otherwise:
      - verify: "on" or "off" (off iff CEO_VERIFY_AFTER_EDIT == "0")
      - codex_review: "off" | "auto" | "advise"
        - "off" iff CEO_CODEX_USER_REVIEW == "0"
        - "auto" iff CEO_CODEX_USER_REVIEW_AUTO == "1"
        - else "advise" (default)
      - adequacy: "on" or "off" (on iff CEO_ADEQUACY_GATE == "1")
      - subagent_model: value of CLAUDE_CODE_SUBAGENT_MODEL env, or "default"
      - master: "on" or "OFF (turbo-off)"

    FAIL-OPEN: on any exception, return an all-off status dict.
    """
    try:
        if env is None:
            env = os.environ

        # Check master switch first
        if is_turbo_off(project_dir):
            return {
                "verify": "off",
                "codex_review": "off",
                "adequacy": "off",
                "subagent_model": "off",
                "master": "OFF (turbo-off)",
            }

        # Compute each accelerator status
        verify_status = "off" if env.get("CEO_VERIFY_AFTER_EDIT") == "0" else "on"

        # codex_review: "off" > "auto" > "advise"
        if env.get("CEO_CODEX_USER_REVIEW") == "0":
            codex_status = "off"
        elif env.get("CEO_CODEX_USER_REVIEW_AUTO") == "1":
            codex_status = "auto"
        else:
            codex_status = "advise"

        adequacy_status = "on" if env.get("CEO_ADEQUACY_GATE") == "1" else "off"
        subagent_model = env.get("CLAUDE_CODE_SUBAGENT_MODEL", "default")

        return {
            "verify": verify_status,
            "codex_review": codex_status,
            "adequacy": adequacy_status,
            "subagent_model": subagent_model,
            "master": "on",
        }
    except Exception:
        # Fail-open: return all-off
        return {
            "verify": "off",
            "codex_review": "off",
            "adequacy": "off",
            "subagent_model": "off",
            "master": "off",
        }


def whats_on_line(project_dir: str, env: Optional[dict] = None) -> str:
    """Return a single <=120-char status line for SessionStart display.

    Format: "⚡ turbo: <status>"

    If turbo is off: "⚡ turbo: OFF (.claude/turbo-off present)" or similar.
    Otherwise: "⚡ turbo: verify=on codex=advise adequacy=off model=inherit  (opt out: .claude/turbo-off or CEO_TURBO=0)"

    FAIL-OPEN: on exception, return a safe generic line.
    """
    try:
        if env is None:
            env = os.environ

        if is_turbo_off(project_dir):
            return "⚡ turbo: OFF (.claude/turbo-off present or CEO_TURBO=0)"

        status = accelerators_status(project_dir, env)

        # Build compact status string
        verify_char = "✓" if status["verify"] == "on" else "-"
        codex_short = status["codex_review"][0] if status["codex_review"] else "-"  # a/d/o
        adequacy_char = "✓" if status["adequacy"] == "on" else "-"
        model_short = status["subagent_model"]

        # Compact form: "⚡ turbo: v✓ c=a a- model=inherit"
        compact = f"⚡ turbo: verify={verify_char} codex={codex_short} adequacy={adequacy_char} model={model_short}"

        # Append hint if short enough
        if len(compact) < 105:
            compact += "  (opt out: .claude/turbo-off or CEO_TURBO=0)"

        return compact[:120]
    except Exception:
        # Fail-open: generic safe line
        return "⚡ turbo: (status unavailable)"


def is_first_run(state_dir: str) -> bool:
    """Return True iff <state_dir>/turbo-initialized marker does NOT exist.

    SECURITY: reject symlinked markers (fail-open to already-initialized).
    Uses atomic lstat to prevent TOCTOU and symlink-following.

    FAIL-OPEN: on exception (e.g., non-string state_dir), return False
    (assume first-run marker already written; do not block).

    On FS errors (PermissionError, ENOTDIR, transient errors), fail-open
    to False (assume already-initialized) rather than True (first-run).
    Only FileNotFoundError specifically indicates first-run.
    """
    try:
        marker_path = os.path.join(state_dir, "turbo-initialized")
        # Atomic lstat check: anything present (file, dir, symlink, etc.) → already initialized
        try:
            os.lstat(marker_path)
            # Something exists at this path; treat as already-initialized
            return False
        except FileNotFoundError:
            # Marker genuinely absent → first run
            return True
        except OSError:
            # Permission denied, ENOTDIR (parent is file), or transient FS error
            # → fail-open to already-initialized (safer than blocking on first-run)
            return False
    except Exception:
        # Fail-open: assume marker exists (already initialized)
        return False


def mark_first_run_done(state_dir: str) -> None:
    """Write a marker file at <state_dir>/turbo-initialized.

    Creates state_dir with os.makedirs(exist_ok=True) if needed.

    SECURITY: refuse to write THROUGH a symlinked state_dir or marker
    (fail-open, return without writing).

    FAIL-OPEN: if the write fails, swallow the exception and return.
    Never raise into the caller.
    """
    try:
        # Refuse to write through a symlinked state_dir
        if os.path.islink(state_dir):
            return

        os.makedirs(state_dir, exist_ok=True)
        marker_path = os.path.join(state_dir, "turbo-initialized")

        # Refuse to write through a symlinked marker
        if os.path.islink(marker_path):
            return

        with open(marker_path, "w") as f:
            f.write("")
    except Exception:
        # Fail-open: swallow the error, do not raise
        pass


def first_run_banner(project_dir: str, env: Optional[dict] = None) -> str:
    """Return a multi-line banner shown ONCE on first run.

    Explains what the accelerators do and how to opt out.
    Includes the whats_on_line status.

    FAIL-OPEN: on exception, return a safe minimal banner.
    """
    try:
        if env is None:
            env = os.environ

        status_line = whats_on_line(project_dir, env)

        banner = f"""{status_line}

Turbo acceleration enabled (new in this session):
  • After-edit verification (pytest, eslint, tsc, …)
  • Smart model routing (cheap → strong by task difficulty)
  • Cross-model review on risky changes (auth, crypto, migrations)
  • Adequacy-gated test checks

To disable:
  1. Set CEO_TURBO=0, or
  2. Create .claude/turbo-off (empty file)

These are advisory; they do not block your edits. Learn more: PLAN-128.
"""
        return banner
    except Exception:
        # Fail-open: minimal safe banner
        return "⚡ turbo: (acceleration available; see PLAN-128 for details)"


def _selftest() -> None:
    """Selftest: exercise all public functions, including error paths."""
    import tempfile

    print("turbo_profile selftest starting...")

    # Test 1: is_turbo_off with no markers
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
        result = is_turbo_off(tmpdir)
        assert result is False, f"Expected False (no turbo-off), got {result}"
        print("  ✓ is_turbo_off: no marker → False")

    # Test 2: is_turbo_off with turbo-off file present
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
        turbo_off = os.path.join(tmpdir, ".claude", "turbo-off")
        with open(turbo_off, "w") as f:
            f.write("")
        result = is_turbo_off(tmpdir)
        assert result is True, f"Expected True (turbo-off present), got {result}"
        print("  ✓ is_turbo_off: file present → True")

    # Test 3: is_turbo_off with CEO_TURBO=0
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
        test_env = os.environ.copy()
        test_env["CEO_TURBO"] = "0"
        # Temporarily patch os.environ for the call
        old_environ = os.environ
        try:
            os.environ = test_env
            result = is_turbo_off(tmpdir)
            assert result is True, f"Expected True (CEO_TURBO=0), got {result}"
            print("  ✓ is_turbo_off: CEO_TURBO=0 → True")
        finally:
            os.environ = old_environ

    # Test 4: is_turbo_off with non-string project_dir (error path)
    result = is_turbo_off(None)  # type: ignore
    assert result is False, f"Expected False (fail-open), got {result}"
    print("  ✓ is_turbo_off: non-string → False (fail-open)")

    # Test 5: accelerators_status (turbo on)
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
        test_env = {"CEO_VERIFY_AFTER_EDIT": "1"}
        status = accelerators_status(tmpdir, test_env)
        assert status["master"] == "on", f"Expected master=on, got {status['master']}"
        assert status["verify"] == "on", f"Expected verify=on, got {status['verify']}"
        print("  ✓ accelerators_status: turbo on → master=on")

    # Test 6: accelerators_status (turbo off)
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
        turbo_off = os.path.join(tmpdir, ".claude", "turbo-off")
        with open(turbo_off, "w") as f:
            f.write("")
        test_env = {}
        status = accelerators_status(tmpdir, test_env)
        assert status["master"] == "OFF (turbo-off)", f"Expected master=OFF, got {status['master']}"
        assert status["verify"] == "off", f"Expected verify=off, got {status['verify']}"
        print("  ✓ accelerators_status: turbo off → all off")

    # Test 7: codex_review states
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
        test_env = {"CEO_CODEX_USER_REVIEW": "0"}
        status = accelerators_status(tmpdir, test_env)
        assert status["codex_review"] == "off", f"Expected codex=off, got {status['codex_review']}"

        test_env = {"CEO_CODEX_USER_REVIEW_AUTO": "1"}
        status = accelerators_status(tmpdir, test_env)
        assert status["codex_review"] == "auto", f"Expected codex=auto, got {status['codex_review']}"

        test_env = {}
        status = accelerators_status(tmpdir, test_env)
        assert status["codex_review"] == "advise", f"Expected codex=advise, got {status['codex_review']}"
        print("  ✓ accelerators_status: codex_review states (off/auto/advise)")

    # Test 8: adequacy_gate
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
        test_env = {"CEO_ADEQUACY_GATE": "1"}
        status = accelerators_status(tmpdir, test_env)
        assert status["adequacy"] == "on", f"Expected adequacy=on, got {status['adequacy']}"

        test_env = {}
        status = accelerators_status(tmpdir, test_env)
        assert status["adequacy"] == "off", f"Expected adequacy=off, got {status['adequacy']}"
        print("  ✓ accelerators_status: adequacy states (on/off)")

    # Test 9: subagent_model
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
        test_env = {"CLAUDE_CODE_SUBAGENT_MODEL": "opus"}
        status = accelerators_status(tmpdir, test_env)
        assert status["subagent_model"] == "opus", f"Expected model=opus, got {status['subagent_model']}"

        test_env = {}
        status = accelerators_status(tmpdir, test_env)
        assert status["subagent_model"] == "default", f"Expected model=default, got {status['subagent_model']}"
        print("  ✓ accelerators_status: subagent_model (custom/default)")

    # Test 10: accelerators_status with exception (error path)
    # Force an exception by passing env that will fail when we try to call is_turbo_off
    # Actually, is_turbo_off itself fails-open, so we need a different error path.
    # Pass an env that's not a dict to trigger the .get() error.
    status = accelerators_status("test", "not-a-dict")  # type: ignore
    assert status["master"] == "off", f"Expected master=off (fail-open), got {status['master']}"
    print("  ✓ accelerators_status: exception → fail-open all-off")

    # Test 11: whats_on_line (turbo on)
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
        test_env = {}
        line = whats_on_line(tmpdir, test_env)
        assert "⚡ turbo:" in line, f"Expected turbo emoji line, got {line}"
        assert "opt out" in line.lower(), f"Expected opt-out hint, got {line}"
        assert len(line) <= 120, f"Expected <=120 chars, got {len(line)}"
        print(f"  ✓ whats_on_line (turbo on): {line[:80]}...")

    # Test 12: whats_on_line (turbo off)
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
        turbo_off = os.path.join(tmpdir, ".claude", "turbo-off")
        with open(turbo_off, "w") as f:
            f.write("")
        line = whats_on_line(tmpdir, {})
        assert "OFF" in line, f"Expected OFF, got {line}"
        assert len(line) <= 120, f"Expected <=120 chars, got {len(line)}"
        print(f"  ✓ whats_on_line (turbo off): {line}")

    # Test 13: whats_on_line with exception
    line = whats_on_line(None, None)  # type: ignore
    assert "⚡ turbo:" in line, f"Expected turbo emoji line (fail-open), got {line}"
    print(f"  ✓ whats_on_line: exception → fail-open {line}")

    # Test 14: is_first_run (no marker)
    with tempfile.TemporaryDirectory() as tmpdir:
        result = is_first_run(tmpdir)
        assert result is True, f"Expected True (no marker), got {result}"
        print("  ✓ is_first_run: no marker → True")

    # Test 15: mark_first_run_done and re-check
    with tempfile.TemporaryDirectory() as tmpdir:
        mark_first_run_done(tmpdir)
        result = is_first_run(tmpdir)
        assert result is False, f"Expected False (marker written), got {result}"
        print("  ✓ mark_first_run_done: creates marker, is_first_run detects it")

    # Test 16: mark_first_run_done creates directory
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = os.path.join(tmpdir, "new", "nested", "dir")
        mark_first_run_done(state_dir)
        assert os.path.isdir(state_dir), f"Expected directory created, got {state_dir}"
        marker = os.path.join(state_dir, "turbo-initialized")
        assert os.path.exists(marker), f"Expected marker created, got {marker}"
        print("  ✓ mark_first_run_done: creates nested dirs")

    # Test 17: is_first_run with exception
    result = is_first_run(None)  # type: ignore
    assert result is False, f"Expected False (fail-open), got {result}"
    print("  ✓ is_first_run: exception → False (fail-open)")

    # Test 18: mark_first_run_done with exception (non-string)
    mark_first_run_done(None)  # type: ignore
    # No assertion; just verify it doesn't raise
    print("  ✓ mark_first_run_done: exception → fail-open (no raise)")

    # Test 19: first_run_banner (turbo on)
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
        banner = first_run_banner(tmpdir, {})
        assert "⚡ turbo:" in banner, f"Expected turbo line, got {banner}"
        assert "After-edit verification" in banner, f"Expected accelerator description, got {banner}"
        assert "CEO_TURBO=0" in banner, f"Expected CEO_TURBO=0 hint, got {banner}"
        assert ".claude/turbo-off" in banner, f"Expected turbo-off hint, got {banner}"
        print("  ✓ first_run_banner (turbo on): includes accel descriptions and opt-out")

    # Test 20: first_run_banner (turbo off)
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
        turbo_off = os.path.join(tmpdir, ".claude", "turbo-off")
        with open(turbo_off, "w") as f:
            f.write("")
        banner = first_run_banner(tmpdir, {})
        assert "OFF" in banner, f"Expected OFF, got {banner}"
        print("  ✓ first_run_banner (turbo off): reflects status")

    # Test 21: first_run_banner with exception
    banner = first_run_banner(None, None)  # type: ignore
    assert "⚡ turbo:" in banner, f"Expected turbo line (fail-open), got {banner}"
    print(f"  ✓ first_run_banner: exception → fail-open minimal banner")

    # Test 22: is_turbo_off with symlinked turbo-off marker → False (security, atomic lstat)
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
        # Create a target file and symlink to it
        target = os.path.join(tmpdir, "target-off")
        with open(target, "w") as f:
            f.write("")
        turbo_off = os.path.join(tmpdir, ".claude", "turbo-off")
        os.symlink(target, turbo_off)
        result = is_turbo_off(tmpdir)
        assert result is False, f"Expected False (symlinked marker rejected via lstat), got {result}"
        print("  ✓ is_turbo_off: symlinked turbo-off → False (atomic lstat, no TOCTOU)")

    # Test 23: is_first_run with symlinked marker → False (atomic lstat detects presence)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a target file and symlink to it as marker
        target = os.path.join(tmpdir, "target-init")
        with open(target, "w") as f:
            f.write("")
        marker = os.path.join(tmpdir, "turbo-initialized")
        os.symlink(target, marker)
        result = is_first_run(tmpdir)
        assert result is False, f"Expected False (symlinked marker detected via lstat), got {result}"
        print("  ✓ is_first_run: symlinked marker → False (atomic lstat, detects any presence)")

    # Test 24: mark_first_run_done with symlinked state_dir → does NOT write (security)
    with tempfile.TemporaryDirectory() as tmpdir:
        real_dir = os.path.join(tmpdir, "real-state")
        os.makedirs(real_dir)
        symlink_dir = os.path.join(tmpdir, "symlink-state")
        os.symlink(real_dir, symlink_dir)
        # Call mark_first_run_done on symlinked dir; should refuse to write
        mark_first_run_done(symlink_dir)
        # Verify marker was NOT written to symlink target (and symlink still exists)
        assert os.path.islink(symlink_dir), "Symlink should still exist"
        marker = os.path.join(symlink_dir, "turbo-initialized")
        assert not os.path.exists(marker), f"Expected no marker written through symlink"
        print("  ✓ mark_first_run_done: symlinked state_dir → refuses to write (security)")

    # Test 25: is_turbo_off with regular file (atomic lstat S_ISREG check)
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
        turbo_off = os.path.join(tmpdir, ".claude", "turbo-off")
        with open(turbo_off, "w") as f:
            f.write("some content")
        result = is_turbo_off(tmpdir)
        assert result is True, f"Expected True (regular file detected via lstat), got {result}"
        print("  ✓ is_turbo_off: regular file → True (lstat+S_ISREG atomic)")

    # Test 26: is_turbo_off rejects directory at turbo-off path (lstat S_ISDIR)
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
        turbo_off_dir = os.path.join(tmpdir, ".claude", "turbo-off")
        os.makedirs(turbo_off_dir)  # Create a directory instead of a file
        result = is_turbo_off(tmpdir)
        assert result is False, f"Expected False (directory not accepted), got {result}"
        print("  ✓ is_turbo_off: directory at turbo-off path → False (lstat rejects non-regular)")

    # Test 27: is_first_run with ENOTDIR (parent is a file, not a directory) → False (fail-open)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file where we'd normally have the state_dir
        fake_dir = os.path.join(tmpdir, "not-a-dir")
        with open(fake_dir, "w") as f:
            f.write("")
        # Now try to lstat a child path: <file>/turbo-initialized → ENOTDIR
        fake_state_dir = fake_dir  # This is actually a file, not a directory
        result = is_first_run(fake_state_dir)
        assert result is False, f"Expected False (ENOTDIR → fail-open), got {result}"
        print("  ✓ is_first_run: ENOTDIR (parent is file) → False (fail-open)")

    # Test 28: is_first_run with PermissionError on lstat → False (fail-open)
    # This requires creating a directory and then revoking read permissions.
    # Note: this may not work reliably on all systems (e.g., running as root),
    # so we wrap it in a try to handle platform-specific behavior.
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = os.path.join(tmpdir, "no-access")
            os.makedirs(state_dir)
            marker = os.path.join(state_dir, "turbo-initialized")
            # Remove all permissions from the directory
            os.chmod(state_dir, 0o000)
            try:
                result = is_first_run(state_dir)
                # PermissionError should be caught, returning False (fail-open)
                assert result is False, f"Expected False (PermissionError → fail-open), got {result}"
                print("  ✓ is_first_run: PermissionError → False (fail-open)")
            finally:
                # Restore permissions to clean up
                os.chmod(state_dir, 0o755)
    except PermissionError:
        # Some systems may not allow chmod(0o000) or may raise during the test setup
        print("  ⊘ is_first_run: PermissionError test skipped (platform limitation)")

    print("\nturbo_profile selftest PASS — all 27-28 tests passed")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
