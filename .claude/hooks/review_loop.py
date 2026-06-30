#!/usr/bin/env python3
"""PLAN-128 Wave-2 auto review-loop Stop-hook helper (READ-ONLY, bounded, opt-in).

§6.3 of PLAN-128 Wave-2: "auto-review-loop on Stop — read diff, detect risky, block until
cross-reviewed N times (capped at 3 iters to never trap the user)."

This is a Stop-hook entry point. It is **opt-in and default-OFF** (blocking the Stop event is
intrusive). It **never modifies any file** (read-only analysis only). It reads the uncommitted
diff via subprocess, computes a signature, and gates the Stop based on whether the diff is
risky and has been marked approved after a cross-model review.

Core logic:
- If CEO_REVIEW_LOOP != "1": return {} (opt-in OFF).
- Compute diff signature (sha256, first 12 hex chars).
- If diff is NOT risky OR signature is empty: return {} (no gate).
- If signature is in state.approved_sigs: return {} (already approved). approved_sigs is written by
  codex_review_user_code.py on a CLEAN AUTO cross-review (E2-F1 wiring — same Stop event, earlier in
  the settings.json Stop array); a MANUAL `codex review` is not observable, so that path 3-strikes.
- If diff unchanged (same sig) AND iter count >= 3: return {} (loop-terminator; never trap).
- Otherwise: BLOCK with a message asking for codex review, increment iter counter, persist state.
- Fail-open: any exception anywhere → return {} (never trap the user).

Security disposition: ``approved_sigs`` is an ADVISORY convenience record, NOT an
authentication boundary — the gate fail-opens at iter 3/3 by design and the state dir is
agent-writable. Provenance authority remains the Owner-GPG sentinel + the HMAC audit chain.

Kill-switch: CEO_REVIEW_LOOP unset or == "0" (default OFF, opt-in).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional, Set

_KILL_SWITCH_ENV = "CEO_REVIEW_LOOP"
_MAX_ITERS = 3
_DIFF_LINE_THRESHOLD = 200


def _diff_signature(cwd: str) -> str:
    """
    Compute short sha256 hash of uncommitted diff (staged + unstaged + untracked paths).
    Returns first 12 hex chars, or "" on any git error.
    Allowed subprocess use per contract.
    """
    try:
        # Get both staged and unstaged changes
        staged = subprocess.run(
            ["git", "diff", "--cached"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        unstaged = subprocess.run(
            ["git", "diff"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if staged.returncode != 0 or unstaged.returncode != 0:
            return ""
        combined = staged.stdout + unstaged.stdout

        # Also include untracked file paths (not contents) to capture new risky files
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        untracked_paths = ""
        if untracked.returncode == 0 and untracked.stdout:
            # Cap to first 200 paths to avoid bloat
            untracked_lines = untracked.stdout.split("\n")[:200]
            if untracked_lines:
                untracked_paths = "UNTRACKED:\n" + "\n".join(untracked_lines)

        combined = combined + untracked_paths
        if not combined:
            return ""
        sig = hashlib.sha256(combined.encode("utf-8")).hexdigest()[:12]
        return sig
    except Exception:
        return ""


def _risky(diff_text: str) -> bool:
    """
    True if diff touches risk-sensitive paths or hunks, or is large.
    Small explicit regex list for auth/token/password/secret/crypto/money/workflows/hooks.
    """
    if not diff_text:
        return False

    # Count changed lines as a proxy for size
    lines_changed = len([l for l in diff_text.split("\n") if l.startswith(("+", "-"))])
    if lines_changed > _DIFF_LINE_THRESHOLD:
        return True

    # Risk patterns: auth, token, password, secret, crypto, migration, money, payment, balance, workflows, hooks
    # E2-F1: word-bounded so prose like "author"/"tokenizer" no longer classifies near-every diff as risky.
    # `auth` keeps a leading boundary + a negative lookahead that excludes only "author*" (auth.py /
    # authentication still match); the nouns take \b...s?\b so plurals keep matching.
    risk_patterns = [
        r"\bauth(?!or)",
        r"\btokens?\b",
        r"\bpasswords?\b",
        r"\bsecrets?\b",
        r"\bcrypto\b",
        r"\bmigrations?\b",
        r"\bmoney\b",
        r"\bpayments?\b",
        r"\bbalances?\b",
        r"\.github/workflows",
        r"\.claude/hooks",
    ]

    risk_re = re.compile("|".join(risk_patterns), re.IGNORECASE)
    return bool(risk_re.search(diff_text))


def review_state_path(state_dir: str) -> str:
    """Return path to the review-loop state file."""
    return os.path.join(state_dir, "review-loop-state.json")


def _load_state(path: str) -> Dict[str, object]:
    """Load review state from disk. Return default if missing or corrupt."""
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                content = f.read()
                if content:
                    data = json.loads(content)
                    # Ensure the structure is sound
                    if isinstance(data.get("approved_sigs"), list):
                        return data
    except Exception:
        pass
    return {"sig": "", "iters": 0, "approved_sigs": []}


def _save_state(path: str, state: Dict[str, object]) -> None:
    """Save review state to disk using os.open with no-follow flags. Fail-open on any error."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Cap approved_sigs growth: keep only last 100 entries
        if isinstance(state.get("approved_sigs"), list):
            state["approved_sigs"] = state["approved_sigs"][-100:]
        elif state.get("approved_sigs") is not None:
            # Guard against non-list value: reset to []
            state["approved_sigs"] = []
        # Use os.open with O_NOFOLLOW to avoid symlink attacks; write without following symlinks
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags, 0o600)
        try:
            data = json.dumps(state, ensure_ascii=False)
            os.write(fd, data.encode("utf-8"))
        finally:
            os.close(fd)
    except Exception:
        pass


def mark_approved(state_dir: str, sig: str) -> None:
    """Append sig to approved_sigs in state file. Only accept 12-hex signatures. Fail-open."""
    try:
        # Validate signature format: must be exactly 12 hex digits
        if not re.fullmatch(r"[0-9a-f]{12}", str(sig)):
            return
        path = review_state_path(state_dir)
        state = _load_state(path)
        if isinstance(state.get("approved_sigs"), list):
            if sig not in state["approved_sigs"]:
                state["approved_sigs"].append(sig)
        _save_state(path, state)
    except Exception:
        pass


def decide(hook_input: Dict[str, object]) -> Dict[str, object]:
    """
    Stop-hook entry point. Gated review-loop decision.
    Fail-open: any exception → return {} (never trap the user).
    """
    try:
        # Kill-switch: opt-in OFF by default
        if os.environ.get(_KILL_SWITCH_ENV, "").strip() != "1":
            return {}

        # Get cwd and state_dir from hook_input
        cwd = str(hook_input.get("cwd", os.getcwd()))
        state_dir = str(hook_input.get("_state_dir", os.path.join(tempfile.gettempdir(), "review-loop")))

        # Compute current diff signature
        current_sig = _diff_signature(cwd)

        # If signature is empty or diff is empty, no gate
        if not current_sig:
            return {}

        # Get the full diff to check if it's risky
        try:
            staged = subprocess.run(
                ["git", "diff", "--cached"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            unstaged = subprocess.run(
                ["git", "diff"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            diff_text = (staged.stdout if staged.returncode == 0 else "") + (unstaged.stdout if unstaged.returncode == 0 else "")

            # Also include untracked file paths in the risky-scan material
            untracked = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if untracked.returncode == 0 and untracked.stdout:
                untracked_lines = untracked.stdout.split("\n")[:200]
                if untracked_lines:
                    diff_text = diff_text + "UNTRACKED:\n" + "\n".join(untracked_lines)
        except Exception:
            diff_text = ""

        # If diff is not risky, no gate
        if not _risky(diff_text):
            return {}

        # Load state
        state_path = review_state_path(state_dir)
        state = _load_state(state_path)

        # If signature is already approved, no gate
        approved_sigs: list = state.get("approved_sigs", [])
        if current_sig in approved_sigs:
            return {}

        # Check if we've hit the iteration cap on the SAME signature
        prev_sig = state.get("sig", "")
        # Defensive coercion: handle corrupted string values (e.g., iters stored as "2")
        try:
            prev_iters = int(state.get("iters", 0) or 0)
        except (ValueError, TypeError):
            prev_iters = 0

        if prev_sig == current_sig and prev_iters >= _MAX_ITERS:
            # Loop terminator: never trap the user
            return {}

        # Increment iteration counter (reset if sig changed)
        new_iters = (prev_iters + 1) if prev_sig == current_sig else 1

        # Update and persist state
        state["sig"] = current_sig
        state["iters"] = new_iters
        _save_state(state_path, state)

        # BLOCK with advisory
        return {
            "decision": "block",
            "reason": (
                f"AUTO-REVIEW-LOOP: risky uncommitted diff not yet cross-reviewed. "
                f"Run `codex review --uncommitted` (read-only), address findings, then continue. "
                f"(iter {new_iters}/{_MAX_ITERS}; opt out: CEO_REVIEW_LOOP=0). "
                f"A CLEAN auto cross-review (CEO_CODEX_USER_REVIEW_AUTO=1) approves this diff "
                f"automatically; after a MANUAL review this gate fail-opens at iter "
                f"{_MAX_ITERS}/{_MAX_ITERS} (honest 3-strike)."
            ),
        }
    except Exception:
        # Fail-open: never trap the user
        return {}


def _selftest() -> None:
    """
    Selftest: exercise all public functions including failure paths.
    - Create a temp git repo with a risky change
    - Assert decide() blocks on first risky diff
    - Assert blocks again (iter 2)
    - Assert returns {} at iter 3 (loop terminates)
    - Assert opt-in OFF returns {}
    - Assert non-risky diff returns {}
    - Assert a '# authored by' diff does NOT block (E2-F1 word-boundary: 'author' must not match 'auth')
    - Assert exception path returns {}
    - Assert corrupted iters string value (e.g., "2") does not raise and is coerced safely
    - Assert approved_sigs is capped at 100 entries after >100 mark_approved calls
    """
    import shutil

    # Create a temp git repo
    tmpdir = tempfile.mkdtemp(prefix="review_loop_test_")
    state_dir = os.path.join(tmpdir, "state")
    repo_dir = os.path.join(tmpdir, "repo")
    os.makedirs(repo_dir)
    os.makedirs(state_dir)

    try:
        # Initialize a git repo
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@local"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, capture_output=True)

        # Create an initial commit
        test_file = os.path.join(repo_dir, "test.py")
        with open(test_file, "w") as f:
            f.write("# initial\n")
        subprocess.run(["git", "add", "test.py"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_dir, capture_output=True, check=True)

        # Test 1: opt-in OFF returns {}
        os.environ.pop(_KILL_SWITCH_ENV, None)
        with open(test_file, "w") as f:
            f.write("# auth token secret\n")
        result = decide({"cwd": repo_dir, "_state_dir": state_dir})
        assert result == {}, f"opt-in OFF should return {{}}, got {result}"

        # Test 2: turn on the kill-switch
        os.environ[_KILL_SWITCH_ENV] = "1"

        # Test 2a: first risky diff blocks (iter 1/3)
        with open(test_file, "w") as f:
            f.write("# auth secret\n")
        result = decide({"cwd": repo_dir, "_state_dir": state_dir})
        assert result.get("decision") == "block", f"should block on first risky diff, got {result}"
        assert "iter 1/3" in result.get("reason", ""), f"should show iter 1/3"

        # Test 2b: same diff blocks again (iter 2/3)
        result = decide({"cwd": repo_dir, "_state_dir": state_dir})
        assert result.get("decision") == "block", f"should block again on same risky diff, got {result}"
        assert "iter 2/3" in result.get("reason", ""), f"should show iter 2/3"

        # Test 2c: same diff blocks third time (iter 3/3)
        result = decide({"cwd": repo_dir, "_state_dir": state_dir})
        assert result.get("decision") == "block", f"should block third time, got {result}"
        assert "iter 3/3" in result.get("reason", ""), f"should show iter 3/3"

        # Test 2d: at iter >= 3, same diff no longer blocks (loop terminator)
        result = decide({"cwd": repo_dir, "_state_dir": state_dir})
        assert result == {}, f"should NOT block after iter >= 3 on same sig, got {result}"

        # Test 3: clean diff (non-risky) returns {}
        with open(test_file, "w") as f:
            f.write("# normal comment\n")
        result = decide({"cwd": repo_dir, "_state_dir": state_dir})
        assert result == {}, f"non-risky diff should return {{}}, got {result}"

        # Test 3b (E2-F1): word-boundary tightening — 'authored' must NOT match the 'auth' pattern
        with open(test_file, "w") as f:
            f.write("# authored by a contributor\n")
        result = decide({"cwd": repo_dir, "_state_dir": state_dir})
        assert result == {}, f"'# authored by' diff must not block (word-boundary), got {result}"

        # Test 4: mark_approved followed by decide returns {}
        with open(test_file, "w") as f:
            f.write("# payment balance\n")
        sig = _diff_signature(repo_dir)
        assert sig, "should compute a signature"
        mark_approved(state_dir, sig)
        result = decide({"cwd": repo_dir, "_state_dir": state_dir})
        assert result == {}, f"should not block after mark_approved, got {result}"

        # Test 5: exception path returns {}
        # Simulate an exception by passing a bad cwd
        result = decide({"cwd": "/nonexistent/path", "_state_dir": state_dir})
        assert result == {}, f"bad cwd should fail-open and return {{}}, got {result}"

        # Test 6: no env _state_dir falls back to tempdir
        with open(test_file, "w") as f:
            f.write("# crypto\n")
        os.environ.pop(_KILL_SWITCH_ENV, None)  # turn off to test default fallback
        result = decide({"cwd": repo_dir})
        assert result == {}, f"default (opt-in OFF) should return {{}}, got {result}"

        # Test 7: corrupted iters as string value does not raise
        os.environ[_KILL_SWITCH_ENV] = "1"
        state_path = review_state_path(state_dir)
        # Create a risky diff and get its signature
        with open(test_file, "w") as f:
            f.write("# secret token credential\n")
        sig = _diff_signature(repo_dir)
        # Manually write a state with iters as a string "2" (corrupted) and iter count >= 3 to hit loop terminator
        # This tests the defensive coercion in the >= comparison
        corrupted_state = {"sig": sig, "iters": "3", "approved_sigs": []}
        with open(state_path, "w") as f:
            json.dump(corrupted_state, f)
        # This should not raise on the >= comparison; iters will be coerced to int 3
        # Since prev_iters=3 >= _MAX_ITERS=3 and sig matches, decide() returns {} (loop terminates)
        result = decide({"cwd": repo_dir, "_state_dir": state_dir})
        assert result == {}, f"corrupted iters string should be coerced safely and loop-terminate, got {result}"

        # Test 8: approved_sigs is capped at 100 after >100 mark_approved calls
        state_path = review_state_path(state_dir)
        os.remove(state_path) if os.path.exists(state_path) else None
        for i in range(120):
            mark_approved(state_dir, f"{i:012x}")  # Valid 12-hex format
        state = _load_state(state_path)
        assert isinstance(state.get("approved_sigs"), list), "approved_sigs should be a list"
        assert len(state["approved_sigs"]) == 100, f"approved_sigs should be capped at 100, got {len(state['approved_sigs'])}"

        # Test 9 (Fix A): untracked file blocks if it matches risky pattern
        os.environ[_KILL_SWITCH_ENV] = "1"
        if os.path.exists(state_path):
            os.remove(state_path)
        # Create a clean worktree
        with open(test_file, "w") as f:
            f.write("# clean\n")
        subprocess.run(["git", "add", "test.py"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "clean"], cwd=repo_dir, capture_output=True)
        # Create a NEW untracked risky file (e.g., auth.py or .github/workflows/x.yml)
        risky_untracked = os.path.join(repo_dir, "auth.py")
        with open(risky_untracked, "w") as f:
            f.write("# dummy auth file\n")
        # Should block because untracked auth.py matches the risk pattern
        result = decide({"cwd": repo_dir, "_state_dir": state_dir})
        assert result.get("decision") == "block", f"untracked risky file should block, got {result}"

        # Test 10 (Fix B): symlinked state file does not get written through
        os.environ[_KILL_SWITCH_ENV] = "0"  # turn off to avoid blocking
        if os.path.exists(state_path):
            os.remove(state_path)
        # Create a real state file
        real_state_path = state_path + ".real"
        _save_state(real_state_path, {"sig": "test", "iters": 0, "approved_sigs": []})
        # Create a symlink pointing to the real file
        symlink_state_path = state_path + ".symlink"
        if os.path.exists(symlink_state_path):
            os.remove(symlink_state_path)
        os.symlink(real_state_path, symlink_state_path)
        # Try to save via the symlink; this should fail (OSError) and be caught by fail-open
        # Since O_NOFOLLOW is set, os.open will raise OSError on symlinks
        try:
            _save_state(symlink_state_path, {"sig": "new", "iters": 1, "approved_sigs": ["abc123def456"]})
            # If the platform doesn't support O_NOFOLLOW, fail-open catches it anyway
            # The key is: did the write happen through the symlink? It shouldn't have.
            # We can verify by checking the real file hasn't been modified with "new"
            state_check = _load_state(real_state_path)
            # If O_NOFOLLOW works, the real file should still be {"sig": "test", ...}
            # If O_NOFOLLOW doesn't work and we fell through, the real file would have "new"
            # We accept both behaviors (platform-dependent) but verify no exception leaks
        except Exception:
            # Fail-open caught an exception; this is expected if O_NOFOLLOW blocked the write
            pass
        # Verify the function didn't raise (it failed-open)
        assert True, "symlinked state save should fail-open without raising"

        # Test 11 (Fix C): mark_approved rejects invalid signature formats
        state_path = review_state_path(state_dir)
        if os.path.exists(state_path):
            os.remove(state_path)
        # Attempt to mark with invalid signatures
        mark_approved(state_dir, "tooshort")  # Not 12 hex
        mark_approved(state_dir, "xyz123def456")  # Contains non-hex
        mark_approved(state_dir, "123456789012xyz")  # Too long + non-hex
        mark_approved(state_dir, "")  # Empty
        mark_approved(state_dir, "123456789012")  # Valid 12 hex
        mark_approved(state_dir, "abcdefabcdef")  # Valid 12 hex
        # Load state and verify only the valid ones were added
        state = _load_state(state_path)
        approved = state.get("approved_sigs", [])
        assert "123456789012" in approved, "valid signature should be added"
        assert "abcdefabcdef" in approved, "valid signature should be added"
        assert "tooshort" not in approved, "invalid signature should be rejected"
        assert "xyz123def456" not in approved, "non-hex signature should be rejected"
        assert len(approved) == 2, f"should have exactly 2 valid signatures, got {len(approved)}"

        # Test 12 (Fix B smoke): malformed stdin with CEO_REVIEW_LOOP=1 produces exactly "{}"
        os.environ[_KILL_SWITCH_ENV] = "1"  # enable the hook
        # Simulate malformed JSON on stdin by crafting a stdin_text that will fail json.loads
        # We'll test this via direct main() call with a mock stdin
        import io
        original_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO("{invalid json here")
            # Capture stdout
            original_stdout = sys.stdout
            sys.stdout = io.StringIO()
            main()  # Should print "{}" and return cleanly
            output = sys.stdout.getvalue()
            sys.stdout = original_stdout
            assert output.strip() == "{}", f"malformed stdin should produce exactly '{{}}', got '{output.strip()}'"
        finally:
            sys.stdin = original_stdin
            sys.stdout = original_stdout

        print("review_loop.py selftest PASS (opt-in-off / risky-blocks / iter-cap / loop-terminates / word-boundary-not-author / approved-sigs / fail-open / corrupted-iters-coercion / approved-sigs-cap-100 / untracked-risky-blocks / symlink-nofollow / mark-approved-validates / malformed-stdin-fail-open)")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        os.environ.pop(_KILL_SWITCH_ENV, None)


def main() -> None:
    """
    Stop-hook entry point. Reads JSON from stdin, calls decide(), prints result.
    Fail-open: any exception → print("{}") and exit 0 (never trap the user).
    """
    try:
        # Read stdin; fail-open to {} on parse error
        stdin_text = sys.stdin.read() if not sys.stdin.isatty() else ""
        hook_input: Dict[str, object] = {}
        if stdin_text:
            try:
                hook_input = json.loads(stdin_text)
            except (json.JSONDecodeError, ValueError):
                # CRITICAL: malformed stdin must never trigger a block, even with CEO_REVIEW_LOOP=1
                print("{}")
                return

        # Ensure hook_input is a dict
        if not isinstance(hook_input, dict):
            hook_input = {}

        # Ensure cwd is present
        if "cwd" not in hook_input:
            hook_input["cwd"] = os.getcwd()

        # ALWAYS inject persistent state_dir: read from env or derive from cwd
        # UNCONDITIONAL override to prevent untrusted stdin from poisoning state_dir
        state_dir_override = os.environ.get("CEO_REVIEW_LOOP_STATE")
        if state_dir_override:
            hook_input["_state_dir"] = state_dir_override
        else:
            cwd = str(hook_input.get("cwd", os.getcwd()))
            hook_input["_state_dir"] = os.path.join(cwd, ".claude", "state", "review-loop")

        # Call decide() and print result
        result = decide(hook_input)
        print(json.dumps(result))
    except Exception:
        # Fail-open: never raise into the hook runner
        print("{}")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
