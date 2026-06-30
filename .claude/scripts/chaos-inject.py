#!/usr/bin/env python3
"""Chaos injection utility — produces hook failure modes for chaos tests.

PLAN-011 Phase 10 (ADR-037). Generates a wrapper script that replaces
one of the framework's active hooks with a deterministically-broken
version. The caller (a chaos test in `tests/chaos/`) then invokes the
hook via the framework's normal subprocess path and asserts the
fail-open contract holds.

## Weaponization lockdown (3 AND gates per ADR-037 §Decision §1)

This script can theoretically be pointed at a real audit log and used
to DOS the framework. To prevent abuse outside test context, it
refuses to run unless ALL THREE gates are open at entry:

1. `CEO_CHAOS_ALLOWED=1` is set in the environment.
2. The parent process command line contains the substring `pytest`.
   Detection:
     - Linux: read `/proc/<ppid>/cmdline` (NUL-delimited argv).
     - macOS: subprocess `ps -o command= -p <ppid>`.
     - Fallback: any platform without either → exit 2.
3. `os.getcwd()` contains the substring `"tests/chaos/"`.

ONE false gate → exit 2 with ERROR. All three open → proceed.

## Usage (from inside a chaos test)

    python3 .claude/scripts/chaos-inject.py \
        --hook check_agent_spawn \
        --mode exit99 \
        --output /tmp/chaos/wrapper.py

The script writes a single-file Python wrapper that implements the
chosen failure mode when invoked. The test then:

1. Copies the wrapper into place of the real hook binary
   (or adjusts $PATH to point to it).
2. Invokes the framework's PreToolUse/PostToolUse path.
3. Asserts the observable output (`{"decision":"allow"}` or
   breadcrumb to audit-log.errors).

## Failure modes

| Mode             | Behaviour                                       |
|------------------|-------------------------------------------------|
| `exit1`          | exit 1, empty stdout                            |
| `exit99`         | exit 99, empty stdout                           |
| `garbage_stdout` | exit 0, stdout="not-json-<random>"              |
| `stderr_spam`    | exit 0, stdout valid, stderr 100 lines noise    |
| `timeout`        | sleeps `timeout_seconds+1` then exits 0         |

## Exit codes

| Code | Meaning                                           |
|------|---------------------------------------------------|
| 0    | Wrapper generated successfully                    |
| 2    | Gate failed OR I/O error OR unknown mode/hook     |
| 3    | Argparse error (unknown --hook name, bad --mode)  |

Advisory: exit 0 is the only "success". Any non-zero exit is failure.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

# Known active hooks — mirrors hook-profiler.py ALL_HOOKS.
ALL_HOOKS: List[str] = [
    "check_agent_spawn",
    "audit_log",
    "check_bash_safety",
    "check_plan_edit",
    "check_read_injection",
    "check_canonical_edit",
]

# Known chaos modes.
ALL_MODES: List[str] = [
    "exit1",
    "exit99",
    "garbage_stdout",
    "stderr_spam",
    "timeout",
]

# Exit code contract.
EXIT_OK = 0
EXIT_GATE_FAIL = 2
EXIT_ARGS_FAIL = 3


# -----------------------------------------------------------------------------
# 3-gate lockdown
# -----------------------------------------------------------------------------


def _gate_env_flag(env: Optional[dict] = None) -> Tuple[bool, str]:
    """Gate 1: CEO_CHAOS_ALLOWED=1."""
    src = env if env is not None else os.environ
    value = (src.get("CEO_CHAOS_ALLOWED") or "").strip()
    if value == "1":
        return (True, "")
    return (False, "CEO_CHAOS_ALLOWED is not '1'")


def _read_parent_cmdline_linux(ppid: int) -> Optional[str]:
    """Read /proc/<ppid>/cmdline on Linux. Returns None on any failure."""
    try:
        raw = Path(f"/proc/{ppid}/cmdline").read_bytes()
    except (OSError, FileNotFoundError):
        return None
    # cmdline is NUL-separated argv. Join with spaces for a substring check.
    try:
        return raw.replace(b"\x00", b" ").decode("utf-8", errors="replace")
    except Exception:  # pragma: no cover - defensive
        return None


def _read_parent_cmdline_ps(ppid: int) -> Optional[str]:
    """Run `ps -o command= -p <ppid>`. Returns None on any failure.

    Works on macOS and as a cross-platform fallback. The `command=`
    format removes the header and returns just the command line.
    """
    try:
        r = subprocess.run(
            ["ps", "-o", "command=", "-p", str(ppid)],
            capture_output=True,
            text=True,
            timeout=2.0,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    out = (r.stdout or "").strip()
    return out or None


def _gate_parent_is_pytest(ppid: Optional[int] = None) -> Tuple[bool, str]:
    """Gate 2: parent process command-line contains 'pytest'.

    Platform-aware:
    - Linux: /proc/<ppid>/cmdline (fast, no subprocess).
    - Others (macOS, BSD): `ps -o command= -p <ppid>`.
    - Both fail → gate fails closed.
    """
    if ppid is None:
        ppid = os.getppid()

    cmdline: Optional[str] = None
    if sys.platform.startswith("linux"):
        cmdline = _read_parent_cmdline_linux(ppid)
        if cmdline is None:
            # Fallback to ps if /proc is unreadable.
            cmdline = _read_parent_cmdline_ps(ppid)
    else:
        cmdline = _read_parent_cmdline_ps(ppid)

    if cmdline is None:
        return (False, f"could not read parent cmdline (ppid={ppid})")

    if "pytest" in cmdline:
        return (True, "")
    return (False, f"parent cmdline does not contain 'pytest': {cmdline[:120]!r}")


def _gate_cwd_is_chaos(cwd: Optional[str] = None) -> Tuple[bool, str]:
    """Gate 3: cwd contains 'tests/chaos/' substring."""
    if cwd is None:
        cwd = os.getcwd()
    # Normalise separators so Windows-style paths would match too,
    # though ADR-037 scopes to POSIX.
    normalised = cwd.replace("\\", "/")
    if "tests/chaos/" in normalised or normalised.endswith("tests/chaos"):
        return (True, "")
    return (False, f"cwd does not contain 'tests/chaos/': {cwd}")


def check_all_gates(
    env: Optional[dict] = None,
    ppid: Optional[int] = None,
    cwd: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """Evaluate all three gates. Returns (all_open, list_of_failure_reasons).

    Each gate is evaluated independently so unit tests can assert
    precisely which gate closed.
    """
    reasons: List[str] = []
    ok1, r1 = _gate_env_flag(env=env)
    if not ok1:
        reasons.append(f"GATE-1 (env): {r1}")
    ok2, r2 = _gate_parent_is_pytest(ppid=ppid)
    if not ok2:
        reasons.append(f"GATE-2 (parent): {r2}")
    ok3, r3 = _gate_cwd_is_chaos(cwd=cwd)
    if not ok3:
        reasons.append(f"GATE-3 (cwd): {r3}")
    return (ok1 and ok2 and ok3, reasons)


# -----------------------------------------------------------------------------
# Wrapper-script generation
# -----------------------------------------------------------------------------


def _wrapper_source(hook_name: str, mode: str, timeout_seconds: float) -> str:
    """Return the Python source for a chaos-wrapper script.

    The wrapper is a STANDALONE script with no dependencies on _lib —
    a chaos test drops it into place (or sets PATH) and the framework
    invokes it as if it were the real hook. The failure mode determines
    the wrapper's behaviour on invocation.
    """
    # IMPORTANT: wrapper is NOT a template — it's a hand-written
    # self-contained Python script. It reads stdin (if any) and then
    # emits the chosen failure mode. It must NEVER import from _lib
    # because the whole point is to simulate what happens when a hook
    # is broken (e.g. a syntax error in _lib won't help here).

    if mode == "exit1":
        body = (
            "    # Mode: exit1 — fail-open contract requires the FRAMEWORK\n"
            "    # (not this wrapper) to emit allow when we exit non-zero.\n"
            "    sys.exit(1)\n"
        )
    elif mode == "exit99":
        body = (
            "    # Mode: exit99\n"
            "    sys.exit(99)\n"
        )
    elif mode == "garbage_stdout":
        body = (
            "    # Mode: garbage_stdout — emits non-JSON then exits 0.\n"
            "    sys.stdout.write('not-json-' + str(os.getpid()) + '\\n')\n"
            "    sys.stdout.flush()\n"
            "    sys.exit(0)\n"
        )
    elif mode == "stderr_spam":
        body = (
            "    # Mode: stderr_spam — emits valid allow + 100 stderr lines.\n"
            "    sys.stdout.write('{\"decision\":\"allow\"}\\n')\n"
            "    sys.stdout.flush()\n"
            "    for i in range(100):\n"
            "        sys.stderr.write(f'[chaos] spam line {i}\\n')\n"
            "    sys.stderr.flush()\n"
            "    sys.exit(0)\n"
        )
    elif mode == "timeout":
        body = (
            "    # Mode: timeout — sleeps past the caller's timeout budget.\n"
            "    # The framework runs hooks with a 5s timeout by default; we\n"
            "    # sleep 6s to force a SIGTERM from the parent.\n"
            f"    time.sleep({timeout_seconds!r})\n"
            "    sys.exit(0)\n"
        )
    else:  # pragma: no cover - arg parsing catches this
        raise ValueError(f"unknown mode: {mode}")

    return (
        "#!/usr/bin/env python3\n"
        f"# Auto-generated chaos wrapper for hook {hook_name!r}, mode {mode!r}.\n"
        "# DO NOT EDIT. Regenerate via `chaos-inject.py`.\n"
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "import os\n"
        "import sys\n"
        "import time\n"
        "\n"
        "\n"
        "def main() -> None:\n"
        "    # Drain stdin (hooks always read stdin even when failing).\n"
        "    try:\n"
        "        sys.stdin.read()\n"
        "    except Exception:\n"
        "        pass\n"
        f"{body}"
        "\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    )


def generate_wrapper(
    hook_name: str,
    mode: str,
    output_path: Path,
    timeout_seconds: float = 6.0,
) -> None:
    """Write a chaos wrapper script to `output_path`.

    Caller must ensure gates are open before calling — this function
    does NOT re-check gates (separation of concerns: CLI entry point
    enforces gates; this helper is pure I/O).
    """
    if hook_name not in ALL_HOOKS:
        raise ValueError(f"unknown hook {hook_name!r}; must be one of {ALL_HOOKS}")
    if mode not in ALL_MODES:
        raise ValueError(f"unknown mode {mode!r}; must be one of {ALL_MODES}")

    source = _wrapper_source(hook_name, mode, timeout_seconds)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(source, encoding="utf-8")
    try:
        output_path.chmod(0o700)
    except OSError:
        pass


# -----------------------------------------------------------------------------
# Breadcrumb emission
# -----------------------------------------------------------------------------


def _emit_breadcrumb(hook_name: str, mode: str, invocations: int) -> None:
    """Write a single `chaos_injected` line to stderr.

    Useful to trace (during a chaos test) that the injection actually
    fired. Stderr, not stdout, to avoid polluting the decision channel.
    """
    record = {
        "event": "chaos_injected",
        "hook": hook_name,
        "mode": mode,
        "invocations": invocations,
        "ts": int(time.time()),
    }
    try:
        sys.stderr.write(json.dumps(record, separators=(",", ":")) + "\n")
        sys.stderr.flush()
    except Exception:  # pragma: no cover
        pass


# -----------------------------------------------------------------------------
# CLI entry point
# -----------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chaos-inject",
        description=(
            "Generate a chaos-wrapper script for a hook. "
            "Runs only inside chaos tests (3-gate lockdown — see ADR-037)."
        ),
    )
    p.add_argument(
        "--hook",
        required=True,
        choices=ALL_HOOKS,
        help="Target hook slug (must be one of the 6 active hooks).",
    )
    p.add_argument(
        "--mode",
        required=True,
        choices=ALL_MODES,
        help="Failure mode to inject.",
    )
    p.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path to write the generated wrapper script.",
    )
    p.add_argument(
        "--invocations",
        type=int,
        default=1,
        help="Advisory count of expected invocations (breadcrumb metadata only).",
    )
    p.add_argument(
        "--timeout-seconds",
        type=float,
        default=6.0,
        help="For mode=timeout: sleep duration. Default 6.0 (> framework 5s budget).",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Enforces 3-gate lockdown THEN delegates to generator.

    Returns an exit code (0 / 2 / 3). Does not raise.
    """
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # argparse raises SystemExit with code 2 on bad args — remap to 3.
        if isinstance(e.code, int) and e.code != 0:
            return EXIT_ARGS_FAIL
        return EXIT_ARGS_FAIL

    # 3-gate lockdown. We call check_all_gates to get all failures at
    # once so the test author sees every failing gate, not just the
    # first one.
    all_open, reasons = check_all_gates()
    if not all_open:
        sys.stderr.write("ERROR: chaos-inject.py lockdown engaged.\n")
        for r in reasons:
            sys.stderr.write(f"  {r}\n")
        sys.stderr.write(
            "chaos-inject.py must only run inside chaos tests with "
            "CEO_CHAOS_ALLOWED=1 + pytest parent + tests/chaos/ cwd.\n"
            "See ADR-037 for the lockdown contract.\n"
        )
        return EXIT_GATE_FAIL

    try:
        generate_wrapper(
            hook_name=args.hook,
            mode=args.mode,
            output_path=args.output,
            timeout_seconds=args.timeout_seconds,
        )
    except ValueError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        return EXIT_ARGS_FAIL
    except OSError as e:
        sys.stderr.write(f"ERROR: I/O failure: {e}\n")
        return EXIT_GATE_FAIL

    _emit_breadcrumb(args.hook, args.mode, args.invocations)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
