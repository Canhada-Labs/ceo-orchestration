#!/usr/bin/env python3
"""PLAN-152 Wave A — Codex R3 fixes (idempotent; run AFTER codex-fixes.py).

Codex R3 found two deeper defects in the whole-command re-tokenization the
R2 fix introduced, both rooted in `shlex.split` being the wrong tool
(it discards quoting info and does not separate adjacent operators):

  P1 — `true&&rm -rf ~ ';'`: shlex.split yields `['true&&rm', ...]` (the
       glued `&&` is not a separate token), so the destructive `rm` hides
       inside the token `true&&rm` and is ALLOWED though bash runs it.
  P2 — `echo ';' rm -rf /tmp`: the `;` is QUOTED (data), but shlex.split
       strips the quotes and the segmenter treats it as a real separator,
       creating a spurious `rm -rf` segment → false-positive BLOCK.

Fix: replace the shlex.split-then-segment recheck with a QUOTE-AWARE
subcommand splitter that (a) honors single/double quotes + backslash
escapes so a quoted metachar is never a separator, and (b) recognizes
adjacent operators (`&&`/`||`/`;`/`|` need no surrounding whitespace).
Each resulting subcommand has balanced quotes, so the per-subcommand
`shlex.split` + token rules are precise. Verified against a 16-case
adversarial battery (both R3 vectors + `||`/`|` adjacency, quoted-`;`
mixed with a real `;`, escaped quote inside double quotes).

This edits kernel-guarded check_bash_safety.py via direct file I/O under
the same authorization chain (sentinel + launch-env kernel override).

Idempotent: skips if the new marker (`_split_subcommands_quote_aware`) is
present. Exit 0 = applied/present + compiles; exit 1 = anchor drift.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
BS = REPO / ".claude" / "hooks" / "check_bash_safety.py"

# --- (a) replace the section header + _CONTROL_OP_TOKENS + _recheck fn ---

SECTION_BEFORE = '''# ---------------------------------------------------------------------------
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

SECTION_AFTER = '''# ---------------------------------------------------------------------------
# PLAN-152 error-handling-01 — shlex.ValueError bypass close (Codex R3)
# ---------------------------------------------------------------------------
#
# Closes the destructive-command bypass where the NAIVE subcommand split
# (`_split_subcommands`, a quoting-blind regex) breaks inside quotes, so
# `rm -rf ~ ";"` splits into an unbalanced-quote chunk shlex rejects — the
# token rules never see it, yet real bash runs `rm -rf ~` (the quoted `;`
# is a literal argument).
#
# Fix history:
#   R1 (regex rescan of the raw chunk)  — Codex R2 P2#1: false-positived
#     on quoted literals like `echo "a && rm -rf /tmp"`.
#   R2 (`shlex.split` the whole command, segment on control-op TOKENS) —
#     Codex R3: shlex.split neither separates ADJACENT operators
#     (`true&&rm` stays one token → `rm` hides → bypass) NOR preserves
#     quoting (a quoted standalone `;` in `echo ';' rm -rf /tmp` looks
#     like a real separator → false positive).
#   R3 (this) — a QUOTE-AWARE subcommand splitter: it walks the command
#     char-by-char, honoring single/double quotes + backslash escapes (so
#     a quoted metachar is NEVER a separator) and recognizing operators
#     with NO surrounding whitespace. Each subcommand it yields has
#     balanced quotes, so the per-subcommand `shlex.split` + token rules
#     are exact. Blocks `rm -rf ~ ";"`, `true&&rm -rf ~ ';'`,
#     `git pull && rm -rf ~ ";"`; ALLOWs `echo "a && rm -rf /tmp"`,
#     `echo ';' rm -rf /tmp`. Verified against a 16-case adversarial
#     battery.
#
# A genuinely-unbalanced command (no closing quote) yields a subcommand
# that still fails shlex → skipped → ALLOW; bash would syntax-error too,
# and the `_e3` whole-command gate (a DIFFERENT tokenizer) already blocks
# the parse-rejectable class upstream (debate C4's reason this is not a
# blanket fail-closed).
#
# Kill-switch: CEO_BASH_RAWSCAN=0 reverts to the pre-PLAN-152 skip
# behavior (default-ON; read from the import-time trusted_env snapshot,
# NOT live os.environ, so a late-set value cannot disarm it mid-op).

_RAWSCAN_DISABLE_VAR = "CEO_BASH_RAWSCAN"


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


def _split_subcommands_quote_aware(command: str) -> List[str]:
    """Split on UNQUOTED &&, ||, ;, | — honoring single/double quotes and
    backslash escapes; operators need no surrounding whitespace.

    Unlike `_split_subcommands` (a quoting-blind regex) this never splits
    on a metachar inside quotes, and unlike `shlex.split` it separates
    adjacent operators. Returns stripped, non-empty subcommand strings.
    Pure; never raises.
    """
    parts = []  # type: List[str]
    buf = []  # type: List[str]
    i = 0
    n = len(command)
    quote = None  # type: Optional[str]
    while i < n:
        c = command[i]
        if quote is not None:
            # Inside quotes: only the matching quote closes. Inside DOUBLE
            # quotes a backslash escapes the next char (so \\" does not
            # close); inside single quotes nothing escapes.
            if c == "\\\\" and quote == '"' and i + 1 < n:
                buf.append(c)
                buf.append(command[i + 1])
                i += 2
                continue
            buf.append(c)
            if c == quote:
                quote = None
            i += 1
            continue
        if c == "'" or c == '"':
            quote = c
            buf.append(c)
            i += 1
            continue
        if c == "\\\\" and i + 1 < n:
            buf.append(c)
            buf.append(command[i + 1])
            i += 2
            continue
        if c == "&" and i + 1 < n and command[i + 1] == "&":
            parts.append("".join(buf))
            buf = []
            i += 2
            continue
        if c == "|" and i + 1 < n and command[i + 1] == "|":
            parts.append("".join(buf))
            buf = []
            i += 2
            continue
        if c == ";" or c == "|":
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    parts.append("".join(buf))
    return [p for p in (s.strip() for s in parts) if p]


def _recheck_whole_command(command: str) -> Optional[str]:
    """Quote-aware recheck: block on a destructive SUBCOMMAND. Returns a
    block reason or None (allow). Pure; never raises.

    Called ONLY when a naive-split chunk failed to tokenize (see
    `decide_command`). Re-splits the WHOLE command with the quote-aware
    splitter, then runs the token rules on each balanced-quote subcommand.
    """
    for sub in _split_subcommands_quote_aware(command):
        toks = _tokenize(sub)
        if not toks:
            # Still unbalanced (no closing quote) → bash would syntax-
            # error too → skip (fail-safe).
            continue
        for check in (_check_rm_rf, _check_git_reset_hard, _check_git_push_force):
            reason = check(toks)
            if reason:
                # Annotate so audit + user see this came via the quote-
                # aware recheck (a chunk failed the naive tokenize).
                return reason.replace(
                    " is destructive.",
                    " is destructive (re-tokenized: a quoted metachar "
                    "defeated the naive split — see CEO_BASH_RAWSCAN).",
                    1,
                )
    return None'''


def main() -> int:
    text = BS.read_text(encoding="utf-8")
    if "_split_subcommands_quote_aware" in text:
        print("skipped (already applied)")
    elif text.count(SECTION_BEFORE) == 1:
        BS.write_text(text.replace(SECTION_BEFORE, SECTION_AFTER, 1), encoding="utf-8")
        print("applied: quote-aware subcommand recheck (Codex R3)")
    else:
        print(
            f"FAILED — expected 1 anchor occurrence, found {text.count(SECTION_BEFORE)}",
            file=sys.stderr,
        )
        return 1
    r = subprocess.run(["python3", "-c", f"compile(open({str(BS)!r}).read(), {str(BS)!r}, 'exec')"])
    if r.returncode != 0:
        print("POST-CHECK FAILED: check_bash_safety.py does not compile", file=sys.stderr)
        return 1
    print("post-check: check_bash_safety.py compiles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
