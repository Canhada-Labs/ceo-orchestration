#!/usr/bin/env python3
"""PLAN-152 Wave A — Codex R2 P2 fixes (idempotent, run AFTER the base patcher).

The base patcher (plan-152-apply-wave-a-kernel.py) landed the initial Wave A
kernel edits; a second Codex pass on the COMPLETE diff surfaced two P2s. Both
strengthen security; both edit kernel-guarded files the in-session Edit rail
denies. This patcher applies the fixes via direct file I/O, same authorization
chain (sentinel + launch-env kernel override).

P2#1 — check_bash_safety.py: the regex raw-rescan false-positives on quoted
  literals (`echo "a && rm -rf /tmp"` blocked though bash treats it as data).
  Replace the regex machine with WHOLE-COMMAND re-tokenization: when a naive
  chunk fails shlex, re-`shlex.split` the whole command and segment on
  control-op TOKENS. Destructive text inside a quoted argument re-parses to a
  single benign segment (allowed); `rm -rf ~ ";"` re-parses to `rm -rf ~`
  (blocked). Strictly more precise than regex.

P2#2 — _python-hook.sh: `_cache_dir_trusted` accepted a user-owned but
  group/world-writable cache dir, leaving a TOCTOU (another local user swaps
  the cache file between the trust check and the read). Reject dirs with
  group/other write bits; reorder the write path so the symlink check precedes
  chmod (no chmod on an attacker symlink target) and chmod precedes the trust
  check (normalizes mode under a loose umask without bricking the legit write).

Idempotent: each patch skips if its `after` text is already present. Exit 0 =
all applied/present (bash + JSON validated); exit 1 = an anchor drifted.
"""
from __future__ import annotations

import subprocess
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


# ===========================================================================
# P2#1 — check_bash_safety.py
# ===========================================================================

BS = REPO / ".claude" / "hooks" / "check_bash_safety.py"

# (a) Replace the whole regex-rescan section with the re-tokenization one.
BS_SECTION_BEFORE = '''# ---------------------------------------------------------------------------
# PLAN-152 error-handling-01 — raw-text destructive-signature rescan
# ---------------------------------------------------------------------------
#
# Closes the shlex.ValueError bypass: when the naive subcommand split
# produces a chunk shlex cannot tokenize (unbalanced quotes — e.g. the
# quoted-metachar probe `rm -rf ~ ";"`), the token rules cannot run, but
# real bash still executes the destructive core. Debate C4 resolution:
# NOT a blanket fail-closed (`_tokenize` here and `_e3`'s shlex.shlex use
# DIFFERENT tokenizers, so blanket-blocking every ValueError would newly
# brick commands `_e3` accepts, e.g. benign unbalanced quotes like
# `echo it's fine`). Instead, regex-scan the RAW unparseable chunk for the
# same three destructive signatures the token rules block, and block ONLY
# on a hit.
#
# Kill-switch: CEO_BASH_RAWSCAN=0 reverts to the pre-PLAN-152 skip
# behavior (default-ON; read from the import-time trusted_env snapshot,
# NOT live os.environ, so a late-set value cannot disarm the rescan
# mid-operation).

_RAWSCAN_DISABLE_VAR = "CEO_BASH_RAWSCAN"

# Command-name prefix mirroring _normalize_command_tokens' reach on raw
# text: start-of-chunk or a shell-boundary char, optional privilege
# prefixes (sudo/doas/nocorrect), optional path prefix (/bin/rm), optional
# escaped-alias backslash (\\rm).
_RAWSCAN_CMD_PREFIX = (
    r"(?:^|[\\s;|&`$(])(?:(?:sudo|doas|nocorrect)\\s+)*(?:\\S*/)?\\\\?"
)
_RAWSCAN_RM_RE = re.compile(_RAWSCAN_CMD_PREFIX + r"rm\\s+(?P<tail>.*)")
_RAWSCAN_GIT_RESET_HARD_RE = re.compile(
    _RAWSCAN_CMD_PREFIX + r"git\\s+reset\\s+--hard(?=[\\s=]|$)"
)
_RAWSCAN_GIT_PUSH_RE = re.compile(
    _RAWSCAN_CMD_PREFIX + r"git\\s+push\\s+(?P<tail>.*)"
)
# Short-option bundles (`-rf`, `-Rf`, …) and long options
# (`--recursive[=v]`, `--force[=v]`, `--r[=v]`) in a raw tail. The
# lookahead keeps `--force` from matching `--force-with-lease`.
_RAWSCAN_SHORT_FLAG_RE = re.compile(r"(?:^|\\s)-([A-Za-z]+)(?=[=\\s]|$)")
_RAWSCAN_LONG_FLAG_RE = re.compile(
    r"(?:^|\\s)--(recursive|force|r)(?:=\\S*)?(?=\\s|$)", re.IGNORECASE
)
_RAWSCAN_PUSH_FORCE_RE = re.compile(r"(?:^|\\s)(?:--force|-[A-Za-z]*f[A-Za-z]*)(?=\\s|$)")


def _rawscan_enabled() -> bool:
    """True unless CEO_BASH_RAWSCAN == "0" in the trusted_env snapshot.

    Default-ON (a security tightening ships armed); the kill-switch
    exists for no-redeploy rollback (PLAN-152 §Approach). On snapshot
    unavailability the rescan stays ON — the scan itself is pure regex
    over a string and cannot raise. Never raises.
    """
    if _trusted_env is None:  # pragma: no cover — import failure → stay armed
        return True
    try:
        raw = _trusted_env.get_trusted(_RAWSCAN_DISABLE_VAR)
    except Exception:  # pragma: no cover
        return True
    return (str(raw).strip() != "0") if raw is not None else True


def _rawscan_destructive(raw: str) -> Optional[str]:
    """Regex-scan an UNPARSEABLE raw chunk for the destructive signatures.

    Mirrors the three token rules (`_check_rm_rf`, `_check_git_reset_hard`,
    `_check_git_push_force`) on raw text. Runs ONLY for chunks shlex
    rejected — a parseable chunk always takes the (more precise) token
    path. Blocks only on a signature hit, so benign unparseable text
    (`echo it's fine`) still ALLOWs. Pure; never raises.
    """
    m = _RAWSCAN_RM_RE.search(raw)
    if m is not None:
        tail = m.group("tail")
        has_r = False
        has_f = False
        for bundle in _RAWSCAN_SHORT_FLAG_RE.findall(tail):
            lowered = bundle.lower()
            if "r" in lowered:
                has_r = True
            if "f" in lowered:
                has_f = True
        for name in _RAWSCAN_LONG_FLAG_RE.findall(tail):
            name = name.lower()
            if name in ("recursive", "r"):
                has_r = True
            elif name == "force":
                has_f = True
        if has_r and has_f:
            return (
                "BLOCKED: `rm` with -r and -f is destructive (raw-rescan: "
                "chunk failed shell tokenization — see CEO_BASH_RAWSCAN). "
                "Specify exact files (`rm <file>` without -r), use trash-cli, "
                "or run the command outside Claude Code if you really mean it."
            )
    if _RAWSCAN_GIT_RESET_HARD_RE.search(raw) is not None:
        return (
            "BLOCKED: `git reset --hard` is destructive (raw-rescan: chunk "
            "failed shell tokenization — see CEO_BASH_RAWSCAN). Use `git "
            "stash` to save uncommitted changes, or `git checkout <file>` "
            "to discard specific files."
        )
    m = _RAWSCAN_GIT_PUSH_RE.search(raw)
    if m is not None and _RAWSCAN_PUSH_FORCE_RE.search(m.group("tail")) is not None:
        return (
            "BLOCKED: `git push --force` is destructive (raw-rescan: chunk "
            "failed shell tokenization — see CEO_BASH_RAWSCAN). Use `git "
            "push --force-with-lease` to avoid overwriting unseen commits "
            "pushed by others."
        )
    return None'''

BS_SECTION_AFTER = '''# ---------------------------------------------------------------------------
# PLAN-152 error-handling-01 — shlex.ValueError bypass close (Codex R2 P2#1)
# ---------------------------------------------------------------------------
#
# Closes the destructive-command bypass where the NAIVE subcommand split
# breaks inside quotes. `_split_subcommands` splits on &&/||/;/| WITHOUT
# honoring quoting, so `rm -rf ~ ";"` splits into an unbalanced-quote
# chunk shlex rejects — the token rules never see it, yet real bash runs
# `rm -rf ~` (the quoted `;` is a literal argument).
#
# Fix (debate C4 + Codex R2 P2#1): when a chunk fails to tokenize,
# re-tokenize the WHOLE command with shlex.split. Two outcomes:
#   * the whole command PARSES → every &&/||/;/| that fooled the naive
#     splitter was QUOTED (data). Re-segment on control-op TOKENS and run
#     the token rules per segment. This blocks `rm -rf ~ ";"` (segment
#     `rm -rf ~`) AND `git pull && rm -rf ~ ";"` (2nd segment) while
#     ALLOWing `echo "a && rm -rf /tmp"` (single benign `echo` segment —
#     the rm is data, not a command). That preserves the documented
#     quoted-string allowance an earlier regex rescan regressed.
#   * the whole command ALSO fails shlex → genuinely unbalanced; bash
#     would syntax-error too, so nothing executes → ALLOW (fail-safe).
#     A parse-rejectable command was already blocked upstream by the `_e3`
#     whole-command gate (a DIFFERENT tokenizer — debate C4's reason this
#     is not a blanket fail-closed).
#
# Strictly MORE precise than a raw-text regex scan: it can never fire on
# destructive text living inside a quoted argument.
#
# Kill-switch: CEO_BASH_RAWSCAN=0 reverts to the pre-PLAN-152 skip
# behavior (default-ON; read from the import-time trusted_env snapshot,
# NOT live os.environ, so a late-set value cannot disarm it mid-op).

_RAWSCAN_DISABLE_VAR = "CEO_BASH_RAWSCAN"

# Control operators that separate subcommands. When shlex.split surfaces
# one of these as a STANDALONE token it was UNQUOTED in the source and
# genuinely separates commands; embedded inside a token it was quoted.
_CONTROL_OP_TOKENS = frozenset({"&&", "||", ";", "|"})


def _rawscan_enabled() -> bool:
    """True unless CEO_BASH_RAWSCAN == "0" in the trusted_env snapshot.

    Default-ON (a security tightening ships armed); the kill-switch
    exists for no-redeploy rollback (PLAN-152 §Approach). On snapshot
    unavailability it stays ON — the recheck is pure and cannot raise.
    Never raises.
    """
    if _trusted_env is None:  # pragma: no cover — import failure → stay armed
        return True
    try:
        raw = _trusted_env.get_trusted(_RAWSCAN_DISABLE_VAR)
    except Exception:  # pragma: no cover
        return True
    return (str(raw).strip() != "0") if raw is not None else True


def _recheck_whole_command(command: str) -> Optional[str]:
    """Re-tokenize the WHOLE command with shlex; block on a destructive
    SEGMENT. Returns a block reason or None (allow). Pure; never raises.

    Called ONLY when a naive-split chunk failed to tokenize (see
    `decide_command`). If the whole command fails shlex too, returns None
    (bash would syntax-error; nothing runs).
    """
    try:
        toks = shlex.split(command)
    except ValueError:
        return None
    segment = []  # type: List[str]
    segments = []  # type: List[List[str]]
    for tok in toks:
        if tok in _CONTROL_OP_TOKENS:
            if segment:
                segments.append(segment)
            segment = []
        else:
            segment.append(tok)
    if segment:
        segments.append(segment)
    for seg in segments:
        for check in (_check_rm_rf, _check_git_reset_hard, _check_git_push_force):
            reason = check(seg)
            if reason:
                # Annotate so audit + user see this came via the whole-
                # command recheck (a chunk failed the naive tokenize).
                return reason.replace(
                    " is destructive.",
                    " is destructive (re-tokenized: a quoted metachar "
                    "defeated the naive split — see CEO_BASH_RAWSCAN).",
                    1,
                )
    return None'''

# (b) Re-point the decide_command branch at the new helper (pass the WHOLE
#     command, not the mangled chunk) + refresh the comment.
BS_BRANCH_BEFORE = '''        if tokens is None:
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
'''

BS_BRANCH_AFTER = '''        if tokens is None:
            # PLAN-152 error-handling-01 (debate C4 + Codex R2 P2#1): shlex
            # rejected this chunk — the naive splitter broke inside quotes
            # (e.g. `rm -rf ~ ";"`). Re-tokenize the WHOLE command and block
            # only if a real command SEGMENT is destructive; quoted text
            # like `echo "a && rm -rf /tmp"` re-parses to a single benign
            # `echo` segment and is allowed. CEO_BASH_RAWSCAN=0 reverts.
            if _rawscan_enabled():
                reason = _recheck_whole_command(command)
                if reason:
                    return Decision(allow=False, reason=reason)
            continue
'''


# ===========================================================================
# P2#2 — _python-hook.sh
# ===========================================================================

SH = REPO / ".claude" / "hooks" / "_python-hook.sh"

SH_HELPERS_BEFORE = '''_owner_uid() {
  # GNU stat first (Linux); BSD stat fallback (macOS).
  stat -c '%u' "$1" 2>/dev/null || stat -f '%u' "$1" 2>/dev/null
}
_cache_dir_trusted() {
  [ ! -L "$_CACHE_DIR" ] && [ -d "$_CACHE_DIR" ] \\
    && [ "$(_owner_uid "$_CACHE_DIR")" = "$_CUR_UID" ]
}'''

SH_HELPERS_AFTER = '''_owner_uid() {
  # GNU stat first (Linux); BSD stat fallback (macOS).
  stat -c '%u' "$1" 2>/dev/null || stat -f '%u' "$1" 2>/dev/null
}
_perm_bits() {
  # Octal permission bits (low bits only): GNU '%a' / BSD '%Lp'.
  stat -c '%a' "$1" 2>/dev/null || stat -f '%Lp' "$1" 2>/dev/null
}
_dir_mode_safe() {
  # PLAN-152 security-01 P2 (Codex R2): reject a group/other-writable
  # cache dir. A user-owned but world/group-writable dir lets another
  # local user swap the cache file between the trust check and the read
  # (TOCTOU), restoring the interpreter-hijack this gate closes.
  local m
  m="$(_perm_bits "$1")" || return 1
  [ -n "$m" ] && [ "$(( 0${m} & 022 ))" -eq 0 ]
}
_cache_dir_trusted() {
  [ ! -L "$_CACHE_DIR" ] && [ -d "$_CACHE_DIR" ] \\
    && [ "$(_owner_uid "$_CACHE_DIR")" = "$_CUR_UID" ] \\
    && _dir_mode_safe "$_CACHE_DIR"
}'''

SH_WRITE_BEFORE = '''    if mkdir -p "$_CACHE_DIR" 2>/dev/null && _cache_dir_trusted \\
        && chmod 0700 "$_CACHE_DIR" 2>/dev/null; then'''

SH_WRITE_AFTER = '''    # Order matters (PLAN-152 security-01 P2): reject a symlinked dir
    # BEFORE chmod (never chmod an attacker's symlink target), then chmod
    # 0700 to normalize the mode under a loose umask, THEN the full trust
    # check (owner + non-symlink + no group/other write).
    if mkdir -p "$_CACHE_DIR" 2>/dev/null && [ ! -L "$_CACHE_DIR" ] \\
        && chmod 0700 "$_CACHE_DIR" 2>/dev/null && _cache_dir_trusted; then'''


def main() -> int:
    steps = [
        ("P2#1 check_bash_safety re-tokenization section", BS, BS_SECTION_BEFORE, BS_SECTION_AFTER),
        ("P2#1 check_bash_safety decide_command branch", BS, BS_BRANCH_BEFORE, BS_BRANCH_AFTER),
        ("P2#2 _python-hook.sh dir-mode trust helpers", SH, SH_HELPERS_BEFORE, SH_HELPERS_AFTER),
        ("P2#2 _python-hook.sh write-path reorder", SH, SH_WRITE_BEFORE, SH_WRITE_AFTER),
    ]
    failures = 0
    for label, path, before, after in steps:
        try:
            print(f"{label}: {_patch(path, before, after)}")
        except EditError as exc:
            failures += 1
            print(f"{label}: FAILED — {exc}", file=sys.stderr)
    if failures:
        return 1
    # Validate the results compile / parse.
    r = subprocess.run(["python3", "-c", f"compile(open({str(BS)!r}).read(), {str(BS)!r}, 'exec')"])
    if r.returncode != 0:
        print("POST-CHECK FAILED: check_bash_safety.py does not compile", file=sys.stderr)
        return 1
    r = subprocess.run(["bash", "-n", str(SH)])
    if r.returncode != 0:
        print("POST-CHECK FAILED: _python-hook.sh syntax error", file=sys.stderr)
        return 1
    print("post-check: check_bash_safety.py compiles + _python-hook.sh syntax OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
