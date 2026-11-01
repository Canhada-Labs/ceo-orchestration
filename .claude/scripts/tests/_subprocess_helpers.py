"""Bounded subprocesses for tests (PLAN-194 follow-ups 9 and 16).

The swarm helper resolves a live PID's group and falls back to killing that
PID. Here the shell may already have exited while a grandchild holds a pipe;
keep the PGID created at launch instead. Never use preexec_fn in test threads.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
from typing import Any, Optional, Sequence


def _kill_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _reap_after_failure(process: subprocess.Popen) -> None:
    _kill_group(process)
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        # A child that deliberately escaped our session is outside this
        # contract. Do not wait indefinitely on a pipe it inherited.
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()
        process.wait(timeout=5)


def run_in_process_group(
    args: Sequence[str], *, timeout: float, input: Any = None,
    capture_output: bool = False, check: bool = False, **kwargs: Any,
) -> subprocess.CompletedProcess:
    """Like run(), but kill the entire owned POSIX group before reaping on error.

    Descendants must stay in the created session. TimeoutExpired is propagated;
    it cannot become an apparently successful result. Output modes match run().
    """
    if os.name != "posix":
        raise NotImplementedError("process-group tests require POSIX")
    if "preexec_fn" in kwargs or "start_new_session" in kwargs:
        raise ValueError("the helper owns process-session creation")
    if input is not None:
        if kwargs.get("stdin") is not None:
            raise ValueError("stdin and input arguments may not both be used")
        kwargs["stdin"] = subprocess.PIPE
    if capture_output:
        if kwargs.get("stdout") is not None or kwargs.get("stderr") is not None:
            raise ValueError("capture_output cannot be combined with stdout/stderr")
        kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process = subprocess.Popen(args, start_new_session=True, **kwargs)
    try:
        stdout, stderr = process.communicate(input, timeout=timeout)
    except BaseException:
        _reap_after_failure(process)
        raise
    result = subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
    if check:
        result.check_returncode()
    return result


def run_python(
    args: Sequence[str], *, expected_returncode: int = 0,
    timeout: float = 30, cwd: Optional[str] = None,
    env: Optional[dict] = None, text: bool = True,
) -> subprocess.CompletedProcess:
    """Every Python mode checks its exit status AND captured fatal-error output."""
    result = run_in_process_group(
        [sys.executable, *args], timeout=timeout, cwd=cwd, env=env,
        capture_output=True, text=text,
    )
    fatal = "Fatal Python error" if text else b"Fatal Python error"
    if fatal in result.stderr:
        raise AssertionError(f"Python fatal error: {result.stderr!r}")
    if result.returncode != expected_returncode:
        raise AssertionError(
            f"Python returncode={result.returncode}, expected={expected_returncode}; "
            f"stdout={result.stdout!r}; stderr={result.stderr!r}"
        )
    return result
