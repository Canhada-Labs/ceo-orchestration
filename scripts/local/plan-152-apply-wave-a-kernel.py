#!/usr/bin/env python3
"""PLAN-152 Wave A — idempotent ceremony patcher for the 3 kernel files.

Owner-run (via `!` in the Claude Code prompt or an external terminal),
per the PLAN-093 precedent (scripts/local/plan-093-apply-kernel-edits.py):
the in-session Edit rail is denied for these targets (`permissions.deny`
on settings.json; auto-mode self-modification classifier on the two hook
files). The Owner-signed sentinel
`.claude/plans/PLAN-152/architect/round-1/approved.md(.asc)` (Scope:
.claude/settings.json, .claude/hooks/check_bash_safety.py,
.claude/hooks/_python-hook.sh) plus the launch-env kernel override
(CEO_KERNEL_OVERRIDE=PLAN-152-v1-0-1-hardening) are the audit trail; the
Owner executing this script IS the user-intent step the auto-mode
classifier asked for.

Patches (each idempotent — skipped if the new text is already present):

  1. governance-01 — .claude/settings.json:201: fix the check_pair_rail.py
     PreToolUse registration to basename + "$CLAUDE_PROJECT_DIR" shim
     invocation (the old doubled-path form fail-opens: `hook not found`
     + `{}` since v1.0.0).
  2. error-handling-01 (wiring) — check_bash_safety.py decide_command:
     route shlex-parse-failure chunks through the raw-text destructive-
     signature rescan (the rescan helpers already landed in-session).
  3. security-01 (read gate) — _python-hook.sh: require dir+file trust
     (ownership, no symlinks) before reading the interpreter cache.
  4. security-01 (write gate) — _python-hook.sh: never write the cache
     through a symlinked / foreign-owned cache dir.

Exit 0 = all patches applied or already present (validated); exit 1 = an
anchor was not found (file drifted — re-run the CEO session to rebuild).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent


class EditError(Exception):
    pass


def _patch(path: Path, before: str, after: str) -> str:
    text = path.read_text(encoding="utf-8")
    if after in text:
        return "skipped (already applied)"
    if text.count(before) != 1:
        raise EditError(
            f"{path}: expected exactly 1 anchor occurrence, found {text.count(before)}"
        )
    path.write_text(text.replace(before, after, 1), encoding="utf-8")
    return "applied"


# ---------------------------------------------------------------------------
# 1. governance-01 — .claude/settings.json
# ---------------------------------------------------------------------------

def patch_settings() -> str:
    p = REPO / ".claude" / "settings.json"
    before = '"command": "bash .claude/hooks/_python-hook.sh .claude/hooks/check_pair_rail.py",'
    after = '"command": "bash \\"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\\" check_pair_rail.py",'
    result = _patch(p, before, after)
    json.loads(p.read_text(encoding="utf-8"))  # must still parse
    return result


# ---------------------------------------------------------------------------
# 2. error-handling-01 wiring — .claude/hooks/check_bash_safety.py
# ---------------------------------------------------------------------------

BS_BEFORE = """    for subcommand in _split_subcommands(command):
        tokens = _tokenize(subcommand)
        if not tokens:
            continue
"""

BS_AFTER = """    for subcommand in _split_subcommands(command):
        tokens = _tokenize(subcommand)
        if tokens is None:
            # PLAN-152 error-handling-01 (debate C4): shlex rejected the
            # chunk (unbalanced quotes — often the naive splitter mangling
            # a quoted metachar, e.g. `rm -rf ~ ";"`). The token rules
            # cannot run, but real bash may still execute the destructive
            # core — rescan the RAW chunk and block only on a signature
            # hit. CEO_BASH_RAWSCAN=0 reverts to the legacy skip.
            if _rawscan_enabled():
                reason = _rawscan_destructive(subcommand)
                if reason:
                    return Decision(allow=False, reason=reason)
            continue
        if not tokens:
            continue
"""


def patch_bash_safety() -> str:
    return _patch(REPO / ".claude" / "hooks" / "check_bash_safety.py", BS_BEFORE, BS_AFTER)


# ---------------------------------------------------------------------------
# 3+4. security-01 gates — .claude/hooks/_python-hook.sh
# ---------------------------------------------------------------------------

SH_READ_BEFORE = """# ---- Cache lookup (fast path) ----
FOUND_PY=""
_CACHE_DIR="$(_cache_dir)"
_PATH_SIG="$(_path_hash 2>/dev/null || echo "nohash")"
_CACHE_FILE="${_CACHE_DIR}/resolved-py-${_PATH_SIG}"

# Honour CEO_PYHOOK_NO_CACHE=1 to force re-probe (useful for testing
# the fallback path or after installing a new interpreter mid-session).
if [ "${CEO_PYHOOK_NO_CACHE:-0}" != "1" ] && [ -r "$_CACHE_FILE" ]; then
"""

SH_READ_AFTER = """# ---- Cache lookup (fast path) ----
FOUND_PY=""
_CUR_UID="$(id -u)"
_CACHE_DIR="$(_cache_dir)"
_PATH_SIG="$(_path_hash 2>/dev/null || echo "nohash")"
_CACHE_FILE="${_CACHE_DIR}/resolved-py-${_PATH_SIG}"

# Honour CEO_PYHOOK_NO_CACHE=1 to force re-probe (useful for testing
# the fallback path or after installing a new interpreter mid-session).
# PLAN-152 security-01: the dir + file trust gates (ownership, no
# symlinks) run BEFORE the read — an untrusted cache is a cache MISS.
if [ "${CEO_PYHOOK_NO_CACHE:-0}" != "1" ] && _cache_dir_trusted \\
    && _cache_file_trusted && [ -r "$_CACHE_FILE" ]; then
"""

SH_WRITE_BEFORE = """    if mkdir -p "$_CACHE_DIR" 2>/dev/null && chmod 0700 "$_CACHE_DIR" 2>/dev/null; then
"""

SH_WRITE_AFTER = """    # PLAN-152 security-01: never write through a symlinked or foreign-
    # owned cache dir (symlink-redirect write primitive).
    if mkdir -p "$_CACHE_DIR" 2>/dev/null && _cache_dir_trusted \\
        && chmod 0700 "$_CACHE_DIR" 2>/dev/null; then
"""


def patch_shim_read() -> str:
    return _patch(REPO / ".claude" / "hooks" / "_python-hook.sh", SH_READ_BEFORE, SH_READ_AFTER)


def patch_shim_write() -> str:
    return _patch(REPO / ".claude" / "hooks" / "_python-hook.sh", SH_WRITE_BEFORE, SH_WRITE_AFTER)


def main() -> int:
    steps = (
        ("governance-01 settings.json registration", patch_settings),
        ("error-handling-01 decide_command rawscan wiring", patch_bash_safety),
        ("security-01 shim cache READ trust gate", patch_shim_read),
        ("security-01 shim cache WRITE trust gate", patch_shim_write),
    )
    failures = 0
    for label, fn in steps:
        try:
            print(f"{label}: {fn()}")
        except EditError as exc:
            failures += 1
            print(f"{label}: FAILED — {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
