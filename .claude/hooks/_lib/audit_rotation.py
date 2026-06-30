"""Shared audit-log rotation primitive (PLAN-045 Wave 2 P0-08).

Extracted from ``.claude/hooks/audit_log.py::rotate_if_needed`` so both
write paths — ``audit_log.py::append_entry`` (PostToolUse Agent events)
and ``_lib.audit_emit._write_event`` (typed v2 events: tier_policy,
tournament, debate, rag, etc.) — can call the same primitive and
guarantee parity.

Closes PLAN-044 F-13-02: ``_write_event`` previously had zero rotation
logic, so a burst of v2 events could grow ``audit-log.jsonl`` past the
10 MB cap without triggering rotation. Now both paths invoke
``rotate_if_needed`` under their own lock, reset the HMAC chain
(``reset_chain_on_rotation``), and the next write re-initializes at
genesis.

## Contract

``rotate_if_needed(log_path, threshold_bytes, month_slug)`` must be
called WITH the caller's FileLock held. Returns the rotated-to Path
on success or None if:
- log_path doesn't exist (nothing to rotate)
- size <= threshold (doesn't need rotation)
- rotation rename fails (OSError)
- 1000+ collision retries exhausted (pathological; bails silently)

On successful rotation the caller SHOULD:
1. Call ``_lib.audit_hmac.reset_chain_on_rotation()`` to clear the
   chain-length + last-hmac sidecars. The new file starts at
   genesis.
2. Proceed with appending the current entry to the now-empty
   ``log_path``.

## Stdlib-only (ADR-002)

Uses ``os``, ``pathlib``. No third-party deps. Callers provide the
month slug (``audit_log.now_month_slug()`` or any equivalent) to
avoid coupling this primitive to a clock helper.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def rotate_if_needed(
    log_path: Path,
    threshold_bytes: int,
    month_slug: str,
    *,
    max_collisions: int = 1000,
) -> Optional[Path]:
    """Rename log_path to a monthly rotated file if it exceeds threshold.

    MUST be called UNDER the caller's audit-log FileLock.

    Args:
        log_path: Path to the active log file.
        threshold_bytes: Rotate when size exceeds this. Typical: 10 MiB.
        month_slug: YYYY-MM string for the rotated filename (caller
            passes ``now_month_slug()`` or equivalent).
        max_collisions: Safety valve — maximum suffix counter before
            giving up (default 1000). Reached only if a flood of
            rotations happens within the same month.

    Returns:
        The rotated path on success; None if no rotation was performed
        or the rename failed.

    Fail-open contract: returns None on any OSError. Caller continues
    with append to the existing (over-threshold) log.
    """
    try:
        if not log_path.is_file():
            return None
        size = log_path.stat().st_size
        if size <= threshold_bytes:
            return None
    except OSError:
        return None

    base = log_path.parent / f"{log_path.stem}-{month_slug}.jsonl"
    candidate = base
    counter = 1
    while candidate.exists():
        candidate = (
            log_path.parent
            / f"{log_path.stem}-{month_slug}-{counter}.jsonl"
        )
        counter += 1
        if counter > max_collisions:
            return None

    try:
        # os.replace handles cross-device filesystems (macOS bind-mounts,
        # Linux overlay FS) where os.rename raises EXDEV.
        os.replace(str(log_path), str(candidate))
    except OSError:
        return None
    return candidate
