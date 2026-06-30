"""turbo_sessionstart.py — PLAN-128 Wave-2 SessionStart glue hook.

A small SessionStart hook that surfaces the turbo "what's on" line + first-run
banner + (opt-in) /ceo-boot nudge, WITHOUT touching the kernel SessionStart.py.

Imports sibling modules (staged to .claude/hooks/ after wiring):
  - turbo_profile: whats_on_line, is_turbo_off, is_first_run, first_run_banner, mark_first_run_done
  - auto_boot: boot_suggestion_context

Behavior:
  1. Read stdin JSON (fail-open {}). Extract project_dir from hook input or env.
  2. Respect turbo master opt-out (is_turbo_off) silently.
  3. Build context lines: start with whats_on_line.
  4. If first run, prepend banner and mark done.
  5. If CEO_AUTO_BOOT=1, append boot suggestion if eligible.
  6. PLAN-135 W2 H6: derive the active plan-id and emit it as
     `hookSpecificOutput.sessionTitle` (Claude Code 2.1.152) so sessions are
     identifiable in the fleet view. Derivation mirrors /ceo-boot's
     `check_plans_executing` (first `status: executing` plan in .claude/plans);
     fail-open / silent when ambiguous (0 or >1 executing) or unreadable — the
     title is then simply not set (NEVER guessed, NEVER an error).
  7. Emit hook output via JSON. FAIL-OPEN on all errors (print "{}" and exit 0).
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional


def _init_sys_path() -> None:
    """Insert current module's directory into sys.path for sibling imports."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)


# PLAN-135 W2 H6: only the canonical PLAN-<NNN> id is allowed to become a session
# title — never an arbitrary disk-sourced string (a stem could otherwise carry a slug
# with control chars; the title is a UI surface, so keep it to the strict, safe form).
_PLAN_ID_RE = re.compile(r"^(PLAN-\d{3})")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_EXECUTING_RE = re.compile(r"^status:\s*executing\s*$", re.MULTILINE)


def _active_plan_id(project_dir: str) -> Optional[str]:
    """Return the active plan-id (e.g. "PLAN-134") for the session title, or None.

    Mirrors /ceo-boot's `check_plans_executing`: scan `.claude/plans/PLAN-*.md`,
    parse the YAML frontmatter, collect those with `status: executing`. Returns the
    id ONLY when exactly one plan is executing — 0 (nothing active) or >1 (ambiguous)
    yields None so the title is left unset. Fully fail-open: any OS / parse error
    returns None, never raises (a SessionStart hook must never wedge the session).
    """
    try:
        plans_dir = os.path.join(project_dir, ".claude", "plans")
        if not os.path.isdir(plans_dir):
            return None
        executing: List[str] = []
        for name in sorted(os.listdir(plans_dir)):
            if not (name.startswith("PLAN-") and name.endswith(".md")):
                continue
            stem_match = _PLAN_ID_RE.match(name)
            if not stem_match:
                continue
            path = os.path.join(plans_dir, name)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    # frontmatter lives at the very top; read a bounded prefix only
                    text = fh.read(4096)
            except OSError:
                continue
            fm = _FRONTMATTER_RE.match(text)
            if fm and _EXECUTING_RE.search(fm.group(1)):
                executing.append(stem_match.group(1))
        if len(executing) == 1:           # exactly one active plan → unambiguous title
            return executing[0]
        return None                       # 0 or >1 → ambiguous, fail-open to no title
    except Exception:
        return None


def main() -> None:
    """
    SessionStart glue hook.

    Reads stdin JSON, builds context from turbo status + boot state,
    emits hook output.

    FAIL-OPEN: on any error, print "{}" and return.
    """
    try:
        # Import sibling modules
        _init_sys_path()
        import turbo_profile  # type: ignore
        import auto_boot  # type: ignore

        # Read stdin JSON
        hook_input: Dict[str, Any] = {}
        try:
            line = sys.stdin.read().strip()
            if line:
                hook_input = json.loads(line)
        except (json.JSONDecodeError, ValueError, EOFError):
            # Fail-open: on stdin JSON parse failure, emit empty response and return
            print(json.dumps({}))
            return

        # Determine project directory
        project_dir = (
            hook_input.get("cwd")
            or os.environ.get("CLAUDE_PROJECT_DIR")
            or os.getcwd()
        )

        # PLAN-135 W2 H6: the active-plan session title is independent of turbo —
        # a session should be identifiable in the fleet view whether or not the
        # turbo banner is on. Derive it once here (fail-open None).
        plan_id = _active_plan_id(project_dir)

        # Check master turbo opt-out
        if turbo_profile.is_turbo_off(project_dir):
            # Turbo is off; suppress the banner/context but STILL set the session
            # title when we have an unambiguous active plan (identification only).
            if plan_id:
                print(json.dumps({
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "sessionTitle": plan_id,
                    }
                }))
            else:
                print(json.dumps({}))
            return

        # Build context lines
        lines: list[str] = []

        # Start with "what's on" line
        lines.append(turbo_profile.whats_on_line(project_dir))

        # If first run, prepend banner and mark done
        state_dir = os.path.join(project_dir, ".claude", "state", "turbo")
        if turbo_profile.is_first_run(state_dir):
            banner = turbo_profile.first_run_banner(project_dir)
            lines.insert(0, banner)
            turbo_profile.mark_first_run_done(state_dir)

        # If CEO_AUTO_BOOT=1, check for boot suggestion
        if os.environ.get("CEO_AUTO_BOOT") == "1":
            boot_state_dir = os.path.join(project_dir, ".claude", "state", "boot")
            boot_ctx = auto_boot.boot_suggestion_context(boot_state_dir)
            if boot_ctx and "hookSpecificOutput" in boot_ctx:
                # Extract additional context from boot suggestion
                boot_context_line = boot_ctx["hookSpecificOutput"].get(
                    "additionalContext", ""
                )
                if boot_context_line:
                    lines.append(boot_context_line)

        # Emit hook output
        hook_specific: Dict[str, Any] = {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(lines),
        }
        # PLAN-135 W2 H6: set the session title to the active PLAN-NNN when
        # unambiguous (Claude Code 2.1.152 `hookSpecificOutput.sessionTitle`).
        if plan_id:
            hook_specific["sessionTitle"] = plan_id
        output = {"hookSpecificOutput": hook_specific}
        print(json.dumps(output))

    except Exception:
        # FAIL-OPEN: on any exception, print empty response
        print(json.dumps({}))


def _selftest() -> None:
    """
    Comprehensive selftest:
      1. turbo-off → {}
      2. first-run banner appears once, not again
      3. opt-in auto-boot adds context with injected absent boot state
      4. fail-open on bad stdin → {}
    """
    import tempfile
    import io
    from contextlib import redirect_stdout

    print("turbo_sessionstart selftest starting...")
    test_count = 0
    passed = 0

    try:
        # Test 1: turbo-off → {} (master opt-out respected silently)
        test_count += 1
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
            turbo_off_path = os.path.join(tmpdir, ".claude", "turbo-off")
            with open(turbo_off_path, "w") as f:
                f.write("")

            # Mock stdin with valid JSON
            stdin_data = json.dumps({"cwd": tmpdir})
            old_environ = os.environ.copy()
            try:
                os.environ["CEO_AUTO_BOOT"] = "0"
                sys.stdin = io.StringIO(stdin_data)  # type: ignore
                capture = io.StringIO()
                with redirect_stdout(capture):
                    main()
                output = capture.getvalue().strip()
                result = json.loads(output)
                assert result == {}, f"Expected {{}}, got {result}"
                print("  ✓ Test 1: turbo-off → {}")
                passed += 1
            finally:
                os.environ.clear()
                os.environ.update(old_environ)
                sys.stdin = sys.__stdin__

        # Test 2a: first-run banner appears (fresh state_dir)
        test_count += 1
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)

            stdin_data = json.dumps({"cwd": tmpdir})
            old_environ = os.environ.copy()
            try:
                os.environ["CEO_AUTO_BOOT"] = "0"
                os.environ["CEO_TURBO"] = "1"  # Explicitly enable
                sys.stdin = io.StringIO(stdin_data)  # type: ignore
                capture = io.StringIO()
                with redirect_stdout(capture):
                    main()
                output = capture.getvalue().strip()
                result = json.loads(output)
                assert "hookSpecificOutput" in result
                context = result["hookSpecificOutput"]["additionalContext"]
                assert (
                    "Turbo acceleration enabled" in context
                    or "After-edit verification" in context
                ), f"Expected first-run banner, got {context[:100]}"
                print("  ✓ Test 2a: first-run banner appears")
                passed += 1
            finally:
                os.environ.clear()
                os.environ.update(old_environ)
                sys.stdin = sys.__stdin__

        # Test 2b: banner does not appear on second run (marker exists)
        test_count += 1
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
            # Pre-create the first-run marker
            state_dir = os.path.join(tmpdir, ".claude", "state", "turbo")
            os.makedirs(state_dir, exist_ok=True)
            marker = os.path.join(state_dir, "turbo-initialized")
            with open(marker, "w") as f:
                f.write("")

            stdin_data = json.dumps({"cwd": tmpdir})
            old_environ = os.environ.copy()
            try:
                os.environ["CEO_AUTO_BOOT"] = "0"
                os.environ["CEO_TURBO"] = "1"
                sys.stdin = io.StringIO(stdin_data)  # type: ignore
                capture = io.StringIO()
                with redirect_stdout(capture):
                    main()
                output = capture.getvalue().strip()
                result = json.loads(output)
                assert "hookSpecificOutput" in result
                context = result["hookSpecificOutput"]["additionalContext"]
                # Banner should NOT appear; should start with "⚡ turbo:"
                assert context.startswith(
                    "⚡ turbo:"
                ), f"Expected compact status line, got {context[:80]}"
                assert "Turbo acceleration enabled" not in context
                print("  ✓ Test 2b: banner does NOT appear on second run")
                passed += 1
            finally:
                os.environ.clear()
                os.environ.update(old_environ)
                sys.stdin = sys.__stdin__

        # Test 3: fail-open on stdin JSON parse failure → {}
        test_count += 1
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)

            # Provide invalid JSON
            stdin_data = "{ this is not valid json }"
            old_environ = os.environ.copy()
            try:
                os.environ["CEO_AUTO_BOOT"] = "0"
                os.environ["CEO_TURBO"] = "1"
                sys.stdin = io.StringIO(stdin_data)  # type: ignore
                capture = io.StringIO()
                with redirect_stdout(capture):
                    main()
                output = capture.getvalue().strip()
                result = json.loads(output)
                # Per spec: malformed stdin → emit {} and return (no-op)
                assert result == {}, f"Expected {{}}, got {result}"
                print("  ✓ Test 3: malformed stdin → {}")
                passed += 1
            finally:
                os.environ.clear()
                os.environ.update(old_environ)
                sys.stdin = sys.__stdin__

        # Test 4: CEO_AUTO_BOOT=1 adds boot suggestion (never-booted state)
        test_count += 1
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
            # Ensure boot state dir is empty (never booted)

            stdin_data = json.dumps({"cwd": tmpdir})
            old_environ = os.environ.copy()
            try:
                os.environ["CEO_AUTO_BOOT"] = "1"
                os.environ["CEO_TURBO"] = "1"
                sys.stdin = io.StringIO(stdin_data)  # type: ignore
                capture = io.StringIO()
                with redirect_stdout(capture):
                    main()
                output = capture.getvalue().strip()
                result = json.loads(output)
                assert "hookSpecificOutput" in result
                context = result["hookSpecificOutput"]["additionalContext"]
                assert (
                    "ceo-boot" in context.lower()
                ), f"Expected boot suggestion in {context}"
                print("  ✓ Test 4: CEO_AUTO_BOOT=1 adds boot suggestion")
                passed += 1
            finally:
                os.environ.clear()
                os.environ.update(old_environ)
                sys.stdin = sys.__stdin__

        # Test 5: CEO_AUTO_BOOT unset → no boot suggestion
        test_count += 1
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)

            stdin_data = json.dumps({"cwd": tmpdir})
            old_environ = os.environ.copy()
            try:
                # CEO_AUTO_BOOT unset
                os.environ.pop("CEO_AUTO_BOOT", None)
                os.environ["CEO_TURBO"] = "1"
                sys.stdin = io.StringIO(stdin_data)  # type: ignore
                capture = io.StringIO()
                with redirect_stdout(capture):
                    main()
                output = capture.getvalue().strip()
                result = json.loads(output)
                assert "hookSpecificOutput" in result
                context = result["hookSpecificOutput"]["additionalContext"]
                # Should NOT contain boot suggestion
                assert (
                    "ceo-boot" not in context.lower()
                ), f"Unexpected boot suggestion when opt-in OFF: {context}"
                print("  ✓ Test 5: CEO_AUTO_BOOT unset → no boot suggestion")
                passed += 1
            finally:
                os.environ.clear()
                os.environ.update(old_environ)
                sys.stdin = sys.__stdin__

        # Test 6: H6 sessionTitle — exactly one executing plan → title = PLAN-NNN
        test_count += 1
        with tempfile.TemporaryDirectory() as tmpdir:
            plans = os.path.join(tmpdir, ".claude", "plans")
            os.makedirs(plans, exist_ok=True)
            with open(os.path.join(plans, "PLAN-134-foo.md"), "w") as f:
                f.write("---\nstatus: executing\nbudget_tokens: 1\n---\n# Foo\n")
            with open(os.path.join(plans, "PLAN-099-bar.md"), "w") as f:
                f.write("---\nstatus: done\n---\n# Bar\n")
            stdin_data = json.dumps({"cwd": tmpdir})
            old_environ = os.environ.copy()
            try:
                os.environ["CEO_AUTO_BOOT"] = "0"
                os.environ["CEO_TURBO"] = "1"
                sys.stdin = io.StringIO(stdin_data)  # type: ignore
                capture = io.StringIO()
                with redirect_stdout(capture):
                    main()
                result = json.loads(capture.getvalue().strip())
                hso = result.get("hookSpecificOutput", {})
                assert hso.get("sessionTitle") == "PLAN-134", \
                    f"Expected sessionTitle PLAN-134, got {hso.get('sessionTitle')!r}"
                print("  ✓ Test 6: single executing plan → sessionTitle=PLAN-134")
                passed += 1
            finally:
                os.environ.clear()
                os.environ.update(old_environ)
                sys.stdin = sys.__stdin__

        # Test 7: H6 sessionTitle — zero executing → no title; two executing → ambiguous, no title
        test_count += 1
        with tempfile.TemporaryDirectory() as tmpdir:
            plans = os.path.join(tmpdir, ".claude", "plans")
            os.makedirs(plans, exist_ok=True)
            with open(os.path.join(plans, "PLAN-100-a.md"), "w") as f:
                f.write("---\nstatus: reviewed\n---\n")
            assert _active_plan_id(tmpdir) is None, "zero executing → None"
            with open(os.path.join(plans, "PLAN-101-b.md"), "w") as f:
                f.write("---\nstatus: executing\n---\n")
            assert _active_plan_id(tmpdir) == "PLAN-101", "single executing → that id"
            with open(os.path.join(plans, "PLAN-102-c.md"), "w") as f:
                f.write("---\nstatus: executing\n---\n")
            assert _active_plan_id(tmpdir) is None, "two executing → ambiguous → None"
            # missing plans dir → None (fail-open)
            assert _active_plan_id(os.path.join(tmpdir, "nope")) is None, "no plans dir → None"
            print("  ✓ Test 7: zero/ambiguous executing → no sessionTitle (fail-open)")
            passed += 1

        # Test 8: H6 sessionTitle — turbo-off still sets the title (identification is turbo-independent)
        test_count += 1
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, ".claude"), exist_ok=True)
            plans = os.path.join(tmpdir, ".claude", "plans")
            os.makedirs(plans, exist_ok=True)
            with open(os.path.join(plans, "PLAN-135-z.md"), "w") as f:
                f.write("---\nstatus: executing\n---\n")
            with open(os.path.join(tmpdir, ".claude", "turbo-off"), "w") as f:
                f.write("")
            stdin_data = json.dumps({"cwd": tmpdir})
            old_environ = os.environ.copy()
            try:
                os.environ["CEO_AUTO_BOOT"] = "0"
                sys.stdin = io.StringIO(stdin_data)  # type: ignore
                capture = io.StringIO()
                with redirect_stdout(capture):
                    main()
                result = json.loads(capture.getvalue().strip())
                hso = result.get("hookSpecificOutput", {})
                assert hso.get("sessionTitle") == "PLAN-135", \
                    f"turbo-off must still set title, got {result}"
                assert "additionalContext" not in hso, "turbo-off must NOT emit the banner context"
                print("  ✓ Test 8: turbo-off → sessionTitle set, no banner context")
                passed += 1
            finally:
                os.environ.clear()
                os.environ.update(old_environ)
                sys.stdin = sys.__stdin__

        # Summary
        print(
            f"\nturbo_sessionstart selftest PASS — {passed}/{test_count} tests passed"
        )
        if passed < test_count:
            sys.exit(1)

    except Exception as e:
        print(f"✗ Selftest exception: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
