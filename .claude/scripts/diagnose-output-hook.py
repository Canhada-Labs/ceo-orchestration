#!/usr/bin/env python3
"""Print an isolated subprocess profile, including audit drains at exit.

Diagnostic only: this never replaces the independent N=200 latency gate.
Uses the gate's exact paired lifecycle payloads, with observe off and on.
"""
from __future__ import annotations

import atexit
import cProfile
import importlib.util
import os
from pathlib import Path
import pstats
import runpy
import subprocess
import sys
import time
import shutil
import tempfile


# Location carriers from _lib.test_isolation.  This runtime script cannot
# import that pytest-only module, so keep the production copy explicit and
# pin parity in test_diagnose_output_hook.py.  HOME is included because it is
# the resolver fallback; CLAUDE_PROJECT_DIR_NATIVE wins every other carrier.
_CHILD_LOCATION_CARRIERS = (
    "HOME", "CEO_AUDIT_LOG_DIR", "CEO_PROJECT_STATE_DIR",
    "CEO_AUDIT_LOG_PATH", "CEO_AUDIT_LOG_ERR", "CEO_AUDIT_LOG_LOCK",
    "CEO_AUDIT_KEY_PATH", "CEO_AUDIT_LAST_HMAC_PATH",
    "CEO_AUDIT_CHAIN_LENGTH_PATH", "CEO_AUDIT_LOG_FALLBACK_PATH",
    "CEO_AUDIT_LOG_ROTATE_BYTES", "CEO_AUDIT_HMAC_DISABLE",
    "CLAUDE_PROJECT_DIR_NATIVE",
)


def _isolated_child_env(base: dict, tmp: str, root: Path) -> dict:
    """Build a child environment whose audit family lives below ``tmp``."""
    env = dict(base)
    for key in _CHILD_LOCATION_CARRIERS:
        env.pop(key, None)
    env.update(
        HOME=tmp,
        CEO_AUDIT_LOG_DIR=str(Path(tmp) / "audit"),
        CEO_PROJECT_STATE_DIR=str(Path(tmp) / "state"),
        CLAUDE_PROJECT_DIR=str(root),
    )
    return env


def _iterations(argv: list) -> int:
    """Read the optional diagnostic sample count without changing its default."""
    if not argv:
        return 201
    if len(argv) == 2 and argv[0] == "--iterations":
        try:
            count = int(argv[1])
        except ValueError:
            count = 0
        if count > 0:
            return count
    raise SystemExit("usage: diagnose-output-hook.py [--iterations POSITIVE]")


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    hook = root / ".claude/hooks/check_output_secrets.py"
    if len(sys.argv) == 3 and sys.argv[1] == "--child":
        profile = cProfile.Profile()
        # Registered first => saved after the hook's own exit handlers.
        def save() -> None:
            profile.disable()
            profile.dump_stats(sys.argv[2])
        atexit.register(save)
        profile.enable()
        runpy.run_path(str(hook), run_name="__main__")
        return

    spec = importlib.util.spec_from_file_location(
        "latency_gate", root / ".claude/scripts/profile-opus-4-7.py"
    )
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    iterations = _iterations(sys.argv[1:])
    for observe in ("", "1"):
        with tempfile.TemporaryDirectory(prefix="ceo-profile-diagnostic-") as tmp:
            env = _isolated_child_env(os.environ, tmp, root)
            for key in ("CLAUDE_SESSION_ID",
                        "CEO_LEARNING_OBSERVE", "CEO_TOOL_LIFECYCLE", "CEO_SOTA_DISABLE",
                        "CEO_ANTI_OVERHEAD"):
                env.pop(key, None)
            for key in ("CEO_MODEL_ROUTING", "CEO_PROMOTION_HEURISTIC",
                        "CEO_COOKBOOK_ADVISOR_ENABLED", "CEO_SPEC_CTX_SANITIZER_ENABLED",
                        "CEO_SPAWN_CONFIDENCE_ENABLED"):
                env[key] = "0"
            if observe:
                env["CEO_LEARNING_OBSERVE"] = observe
            stats_path = str(Path(tmp) / "hook.prof")
            samples = []
            worst_ms = -1.0
            worst_path = str(Path(tmp) / "worst.prof")
            for i in range(iterations):
                tool_id = "diagnostic-%d" % i
                subprocess.run(
                    [sys.executable, str(hook.with_name("check_anti_ceo_overhead.py"))],
                    input=gate._latency_pre_payload(tool_id), env=env,
                    cwd=root, capture_output=True, timeout=10, check=True,
                )
                started = time.perf_counter()
                subprocess.run(
                    [sys.executable, str(Path(__file__).resolve()), "--child", stats_path],
                    input=gate._latency_post_payload(tool_id), env=env,
                    cwd=root, capture_output=True, timeout=10, check=True,
                )
                elapsed_ms = (time.perf_counter() - started) * 1000
                stats = pstats.Stats(stats_path)
                fsync_ms = sum(v[2] for k, v in stats.stats.items() if "posix.fsync" in k[2]) * 1000
                samples.append((elapsed_ms, fsync_ms))
                if elapsed_ms > worst_ms:
                    worst_ms = elapsed_ms
                    shutil.copyfile(stats_path, worst_path)
            print("DIAGNOSTIC wall/fsync ms (1 cold then %d warm):" % (iterations - 1), samples)
            print("OUTPUT HOOK DIAGNOSTIC observe=%s (separate from gate)" % (observe or "unset"))
            pstats.Stats(worst_path).strip_dirs().sort_stats("cumulative").print_stats(25)
            pstats.Stats(worst_path).strip_dirs().sort_stats("tottime").print_stats(15)


if __name__ == "__main__":
    main()
