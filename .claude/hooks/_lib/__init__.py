"""Shared Python hook library for ceo-orchestration.

This package is imported by the single-file hooks in the parent directory
(`check_agent_spawn.py`, `audit_log.py`). Each hook inserts its parent dir
on `sys.path` before importing from `_lib`:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from _lib import payload, redact, filelock, team

The package is deliberately stdlib-only so hooks have zero install cost.
Python minimum is 3.9 (the macOS system Python) — see `_python-hook.sh`
shim in A.4 for version resolution.

Modules:
- payload.py    — parse Claude Code PreToolUse/PostToolUse stdin JSON
- redact.py     — regex-based secret redaction + SHA-256 hashing
- filelock.py   — fcntl.flock context manager with timeout + stale detection
- team.py       — extract team member names from team.md / domain personas
- testing.py    — TestEnvContext base class for isolated unit tests
"""

from __future__ import annotations

__all__ = ["payload", "redact", "filelock", "team", "testing"]
