"""Git hook-bypass guard tokenizer + decision function (PLAN-124 WS-1).

Blocks git invocations that disable the project's git hooks — the
`--no-verify` family, inline / config-write / env-channel / `--config-env`
`core.hooksPath` overrides, and `--git-dir` / `-C` / alias smuggling +
`bash -c` / `eval` shell-wrapper evasion — consumed by the PreToolUse
`check_bash_safety.py` hook.

## Why (PLAN-124 WS-1, debate K2 / MF-A — honest framing)

This is **defense-in-depth + adopter protection + git hygiene**, NOT a
moat-hole fix for *this* repo (our pre-commit governance is a Claude Code
PreToolUse hook that fires regardless of `--no-verify` / `core.hooksPath`).
The crown-jewel framing is retracted (MF-A). Adopter repos that DO rely on
git-native hooks are the real beneficiary.

## Original idea attribution (MIT)

The `--no-verify` tokenizer idea is credited to `affaan-m/ECC`
`scripts/hooks/block-no-verify.js` (MIT). This is a clean-room stdlib-Python
re-implementation that **exceeds** ECC: ECC covers the 6 subcommands +
inline `-c core.hooksPath`; we additionally cover the
`GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_<n>`/`GIT_CONFIG_VALUE_<n>` env channel,
the `--config-env=core.hooksPath=<envvar>` channel, `git config` *writes*
to `core.hooksPath` (the split attack), `--git-dir` / `-C` / alias abuse
(MF-C / MF-D), and bounded `bash -c` / `eval` shell-wrapper recursion.

## Design contract

- Pure tokenizer + pure decision function (`scan_command`) — no I/O, no
  audit emit, trivially unit-testable in isolation. The hook
  (`check_bash_safety.py`) owns the emit + the dual-auth side-effect path.
- **Quote-aware tokenization (DEFECT-4 root-cause fix):** the command is
  tokenized ONCE with ``shlex.shlex(posix=True, punctuation_chars=True)``
  + ``whitespace_split=True``. That respects single/double quotes AND emits
  the shell control operators ``; && || | &`` as their own tokens, so a
  commit message that literally contains ``--no-verify`` or ``;`` is never
  misread as a flag / a chain split. The token stream is then split on
  those operator tokens into independent sub-commands; each sub-command's
  token list is analyzed in isolation. When walking a git sub-command's
  args we SKIP the value consumed by option-with-argument flags
  (``-m``/``--message``, ``-F``/``--file``, ``commit -C <commit>``, and the
  global ``-c``/``-C``/``--git-dir`` value tokens) so an option *value*
  cannot be misread as a bypass flag.
- **Parse-failure fail-mode (MF-L):** an unparseable command (e.g. an
  unmatched quote) that *clearly invokes git* is treated as a potential
  bypass → fail-CLOSED BLOCK, but bounded so a tokenizer/infra bug cannot
  brick the session: a command that does NOT clearly invoke git passes
  through untouched (returns None).
- **Chaining (MF-F):** a trigger in ANY chained git invocation blocks; a
  trigger in a PRIOR non-git command is ignored.
- **Shell-wrapper recursion (DEFECT-1, BOUNDED):** if a sub-command's first
  token is an explicit shell wrapper (`bash`/`sh`/`zsh`/`dash`/`ksh`)
  followed by `-c <body>`, OR is `eval <body>`, the body string is
  RECURSIVELY scanned with the same scanner — bounded by a max recursion
  depth of 3 and a total byte cap to defeat pathological input.

## Accepted boundary (NOT an oversight)

`bash -c` / `eval` ARE now handled (DEFECT-1). Command substitution
``$(git commit --no-verify ...)``, backticks, and subshell groups
``(...)`` remain an ACCEPTED host-hook boundary — the SAME boundary the
pre-existing destructive matchers in check_bash_safety.py share (e.g.
``$(rm -rf /)`` also passes the rm matcher today). Closing it would hold
WS-1 to a higher bar than the Tier-1 hook it extends; if ever fixed it must
be done ONCE at the tokenizer level for all matchers, not here.

This module returns a closed ``flag_class`` enum token (never command
bytes) so the caller can emit ``git_hook_bypass_blocked`` with no leak
(MF-G).
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Closed flag_class enum (MF-G). The ONLY caller-supplied audit field. The
# emitter in audit_emit.py re-validates membership; anything else is rejected.
# ---------------------------------------------------------------------------
FLAG_CLASS_NO_VERIFY_COMMIT = "no_verify_commit"
FLAG_CLASS_NO_VERIFY_OTHER = "no_verify_other_subcmd"
FLAG_CLASS_HOOKSPATH_INLINE = "hookspath_inline"
FLAG_CLASS_HOOKSPATH_CONFIG_WRITE = "hookspath_config_write"
FLAG_CLASS_GIT_CONFIG_ENV_CHANNEL = "git_config_env_channel"
FLAG_CLASS_GIT_DIR_REDIRECT = "git_dir_redirect"
FLAG_CLASS_ALIAS_ABUSE = "alias_abuse"
FLAG_CLASS_PARSE_FAILURE = "parse_failure"
FLAG_CLASS_ESCAPE_HATCH = "escape_hatch_used"

#: Closed set of flag_class tokens. Mirrored in audit_emit.py.
GIT_BYPASS_FLAG_CLASSES = frozenset({
    FLAG_CLASS_NO_VERIFY_COMMIT,
    FLAG_CLASS_NO_VERIFY_OTHER,
    FLAG_CLASS_HOOKSPATH_INLINE,
    FLAG_CLASS_HOOKSPATH_CONFIG_WRITE,
    FLAG_CLASS_GIT_CONFIG_ENV_CHANNEL,
    FLAG_CLASS_GIT_DIR_REDIRECT,
    FLAG_CLASS_ALIAS_ABUSE,
    FLAG_CLASS_PARSE_FAILURE,
    FLAG_CLASS_ESCAPE_HATCH,
})

# Subcommands on which `--no-verify` bypasses hooks (MF-C — ECC's 6).
_NO_VERIFY_SUBCOMMANDS = frozenset({
    "commit", "push", "merge", "cherry-pick", "rebase", "am",
})

# Privilege-escalation prefixes stripped before the git-name check (mirrors
# check_bash_safety._normalize_command_tokens, kept local to avoid coupling).
_PRIVILEGE_PREFIXES = frozenset({"sudo", "doas", "nocorrect", "env", "command"})

# git "global" options that take a value as the NEXT token (so the parser can
# skip the value when scanning for the subcommand). These appear BEFORE the
# subcommand. `-c` and `-C` and `--git-dir`/`--work-tree`/`--namespace` etc.
# `--config-env` ALSO takes a NEXT-token value (`--config-env core.hooksPath=ENV`
# split form) — handled explicitly in the scanners so it is not silently
# skipped here.
_GIT_GLOBAL_VALUE_OPTS_NEXT = frozenset({
    "-c", "-C", "--git-dir", "--work-tree", "--namespace",
    "--exec-path", "--super-prefix", "--config-env",
})

# Option flags on the `commit` subcommand that consume the FOLLOWING token as
# their value (so the value is not misread as a bypass flag — DEFECT-4).
# `-C`/`-c` on commit reuse a commit/message; `-m`/`-F` take a message/file.
_COMMIT_VALUE_OPTS_NEXT = frozenset({
    "-m", "--message", "-F", "--file", "-C", "--reuse-message",
    "-c", "--reedit-message", "--fixup", "--squash", "--author",
    "--date", "-t", "--template",
})

# Generic NEXT-token-value flags for the other no-verify subcommands. Kept
# conservative — only the message/file family that could plausibly carry a
# literal `--no-verify`/`-n` string. (Over-skipping is safe: the real
# `--no-verify`/`-n` flag never appears as one of these flags' VALUE.)
_GENERIC_VALUE_OPTS_NEXT = frozenset({
    "-m", "--message", "-F", "--file",
})

# Explicit shell wrappers whose `-c <body>` is recursively scanned (DEFECT-1).
_SHELL_WRAPPERS = frozenset({"bash", "sh", "zsh", "dash", "ksh"})

# Bounded recursion guards for shell-wrapper bodies (DEFECT-1).
_MAX_WRAPPER_DEPTH = 3
_WRAPPER_BODY_CAP_BYTES = 16 * 1024

# Cheap "does this chunk clearly invoke git?" probe used for the bounded
# fail-CLOSED parse-failure mode (MF-L). Matches a leading (optionally
# privilege-prefixed / path-qualified / backslash-escaped) `git` word. We use
# this ONLY when shlex parse fails, so a non-git unparseable command (e.g. an
# awk one-liner with an unbalanced quote) passes through untouched.
_LOOKS_LIKE_GIT_RE = re.compile(
    r"""^\s*
        (?:(?:sudo|doas|nocorrect|env|command)\s+)*   # optional privilege prefixes
        \\?                                            # optional alias-escape backslash
        (?:[^\s'";|&]*/)?                              # optional path prefix (/usr/bin/)
        git(?:\.exe)?                                  # the git binary
        (?:\s|$)                                       # word boundary
    """,
    re.VERBOSE,
)

# Naive (quote-UNAWARE) operator split used ONLY for the bounded fail-CLOSED
# fallback when the quote-aware tokenizer raises on the whole string. It lets
# us preserve the per-chunk MF-L granularity (a clean git chunk + a later
# non-git unparseable chunk must still ALLOW). Matches &&, ||, ;, |, &, newline.
_NAIVE_SPLIT_RE = re.compile(r"\s*(?:&&|\|\||[;|&\n])\s*")

# Shell control operators emitted as standalone tokens by the punctuation_chars
# tokenizer that SEPARATE independent sub-commands. (`>`/`>>`/`(`/`)` are also
# emitted standalone but do NOT separate sub-commands — they stay inside the
# chunk, harmless to the git scanner.)
_OPERATOR_TOKENS = frozenset({";", "&&", "||", "|", "&", "\n"})

# core.hooksPath detection — case-insensitive on the config KEY only.
_HOOKSPATH_KEY = "core.hookspath"


@dataclass
class GitBypassMatch:
    """Result of a git hook-bypass scan.

    ``flag_class`` is a member of :data:`GIT_BYPASS_FLAG_CLASSES`.
    ``reason`` is an operator-facing remediation string (safe to display;
    never contains a secret because the matched VALUE is never interpolated).
    """

    flag_class: str
    reason: str


def _tokenize(command: str) -> List[str]:
    """Quote-aware tokenize via shlex with punctuation_chars (DEFECT-4).

    Emits shell control operators ``; && || | &`` as their own tokens while
    respecting single/double quotes. Raises ``ValueError`` on an unparseable
    command (e.g. unmatched quote) — the caller decides the fail-mode.
    """
    lex = shlex.shlex(command, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    return list(lex)


def _split_on_operators(tokens: List[str]) -> List[List[str]]:
    """Split a flat token stream into sub-command token lists on operators."""
    chunks: List[List[str]] = []
    current: List[str] = []
    for tok in tokens:
        if tok in _OPERATOR_TOKENS:
            if current:
                chunks.append(current)
                current = []
            continue
        current.append(tok)
    if current:
        chunks.append(current)
    return chunks


def _strip_privilege_prefixes(tokens: List[str]) -> List[str]:
    """Drop leading sudo/doas/env/command prefixes + their owned flags.

    Returns a NEW list. Mirrors check_bash_safety normalization closely
    enough for the git-name check; `env` additionally consumes leading
    ``VAR=value`` assignment tokens (so `env GIT_CONFIG_COUNT=1 git ...`
    reaches `git`). The consumed `env` assignments are still scanned for the
    env-channel attack at the command-string level (see scan_command).
    """
    working = list(tokens)
    while working and working[0] in _PRIVILEGE_PREFIXES:
        head = working.pop(0)
        if head == "env":
            # env consumes leading VAR=value assignments + a possible -i / -u.
            while working and ("=" in working[0] or working[0] in ("-i", "-u", "--")):
                tok = working.pop(0)
                if tok == "-u" and working:  # -u NAME
                    working.pop(0)
            continue
        # sudo/doas/nocorrect/command: consume their own -flags.
        while working and working[0].startswith("-"):
            flag = working.pop(0)
            if flag in ("-u", "--user") and working and not working[0].startswith("-"):
                working.pop(0)
    return working


def _git_basename(tok: str) -> str:
    """Normalize a command token to its basename, stripping a leading ``\\``."""
    first = tok.lstrip("\\") if tok.startswith("\\") else tok
    base = Path(first).name if first else first
    return (base or first).lower()


def _is_git_invocation(tokens: List[str]) -> bool:
    """True iff the (privilege-stripped) first token is the git binary."""
    if not tokens:
        return False
    base = _git_basename(tokens[0])
    return base in ("git", "git.exe")


def _check_inline_c_hookspath(value: str) -> bool:
    """True iff a `-c <value>` sets core.hooksPath (`core.hooksPath=...`)."""
    # `-c core.hooksPath=/x` → value == "core.hooksPath=/x". The KEY half is
    # case-insensitive in git; the value half is irrelevant (any set = bypass).
    key = value.split("=", 1)[0].strip().lower()
    return key == _HOOKSPATH_KEY


def _config_env_sets_hookspath(value: str) -> bool:
    """True iff a `--config-env` VALUE sets core.hooksPath (DEFECT-2).

    `--config-env=core.hooksPath=ENVVAR` → value == "core.hooksPath=ENVVAR";
    the split form `--config-env core.hooksPath=ENVVAR` passes the same value
    half. Only the KEY (left of the first `=`) matters; it is case-insensitive.
    """
    key = value.split("=", 1)[0].strip().lower()
    return key == _HOOKSPATH_KEY


def _check_alias_smuggle(value: str) -> bool:
    """True iff a `-c alias.<x>=<body>` body smuggles a bypass.

    Generalized (R3-DEFECT): the alias body is scanned for ANY EMBEDDED git
    bypass invocation, not just a leading one — a shell-function alias such as
    ``!f() { git commit -n "$@"; }; f`` hides the ``git commit -n`` inside the
    function body, which a leading-only scan misses. We:

      1. fast-path on a bare ``core.hooksPath`` / ``hookspath`` reference
         anywhere in the body (covers a bare ``config core.hooksPath`` alias
         that has no ``git`` word at all);
      2. otherwise branch on git's alias-expansion model (R4-DEFECT):
         - body STARTS WITH ``!`` → it is a SHELL command; run the embedded-
           invocation scan over the whole body (R3): at EVERY position where a
           git invocation begins, run the real scanners; embedded
           ``bash -c``/``sh -c``/``eval`` wrappers are recursed (bounded).
         - body does NOT start with ``!`` → git IMPLICITLY prepends ``git``, so
           the body is a git subcommand; scan ``["git"] + body_tokens`` with
           the real scanners (treat it as ``git <body>``).

    Reuses the same quote-aware tokenizer + left-to-right getopt cluster logic
    as the direct path, so an innocuous alias body (``commit``, ``status``,
    ``log --oneline``, ``commit -mn`` = message "n", ``push -n`` = dry-run)
    still ALLOWs.
    """
    key = value.split("=", 1)[0].strip().lower()
    if not key.startswith("alias."):
        return False
    body = value.split("=", 1)[1] if "=" in value else ""
    # R5-DEFECT: NO blanket `core.hooksPath`/`hookspath` substring fast-path —
    # it over-blocked legit aliases that merely MENTION the text (a commit
    # MESSAGE literal, or a `config --get core.hooksPath` READ). Detection is
    # entirely token-accurate via _alias_body_has_bypass:
    #   - a `config core.hooksPath <val>` WRITE blocks (_scan_git_config_write);
    #   - a `config --get core.hooksPath` / `--list` READ passes;
    #   - a `-c core.hooksPath=...` inline override blocks
    #     (_scan_inline_c_and_alias).
    # A bare shell `config core.hooksPath` (no `git`, no `!`-git) is NOT a git
    # invocation and is correctly NOT flagged.
    return _alias_body_has_bypass(body, depth=0)


def _alias_body_has_bypass(body: str, depth: int) -> bool:
    """True iff an alias body is a bypass, per git's alias-expansion model.

    Branches on the leading ``!`` (R4-DEFECT):
      - ``!``-prefixed → shell command → embedded-invocation scan (R3);
      - otherwise → git-IMPLIED subcommand → scan ``["git"] + body_tokens``.

    Token-accurate (no message false-positives); reuses the quote-aware
    tokenizer + getopt cluster logic.
    """
    if depth >= _MAX_WRAPPER_DEPTH:
        return False
    text = body.strip()
    if not text:
        return False
    if text.startswith("!"):
        # Shell command: scan the whole body for embedded git invocations.
        shell_text = text[1:].strip()
        if not shell_text:
            return False
        try:
            toks = _tokenize(shell_text)
        except ValueError:
            # Fail-CLOSED (S1): we are already inside an alias body, so this is
            # unambiguously a git-intent context (the leading `!` embeds a shell
            # command that runs WITHIN git's alias expansion). A tokenize failure
            # means a git-bearing command we could not lex — treat the
            # unparseable alias body as a bypass, mirroring the top-level
            # naive-fallback fail-CLOSE (_scan_with_naive_fallback).
            return True
        for chunk in _split_on_operators(toks):
            if _chunk_has_embedded_git_bypass(chunk, depth):
                return True
        return False
    # Non-`!`: git implicitly prepends `git`. Scan `git <body>` with the real
    # scanners (the FIRST chunk only — a git alias body is a single subcommand;
    # operators are not part of a non-shell git-subcommand alias).
    try:
        toks = _tokenize(text)
    except ValueError:
        # Fail-CLOSED (S1): the non-`!` alias body is git-IMPLIED (git prepends
        # `git`), so this is unambiguously a git command. A tokenize failure is a
        # git invocation we could not lex — treat the unparseable alias body as a
        # bypass, mirroring the top-level naive-fallback fail-CLOSE.
        return True
    chunks = _split_on_operators(toks)
    body_tokens = chunks[0] if chunks else []
    if not body_tokens:
        return False
    # Non-`!` git-implied subcommand: run the SAME complete detector set the
    # direct path runs (R6 unification — no hand-picked subset).
    git_toks = ["git"] + body_tokens
    return _scan_git_invocation(git_toks) is not None


def _chunk_has_embedded_git_bypass(chunk: List[str], depth: int) -> bool:
    """Scan ONE alias-body chunk for an embedded git bypass at any position.

    Runs the SAME complete per-invocation detector set as the direct path
    (R6 unification via _scan_git_invocation), so any scanner that protects a
    top-level `git ...` also protects every embedded alias invocation.
    """
    n = len(chunk)
    for i in range(n):
        slice_toks = chunk[i:]
        # Embedded shell-wrapper (sh -c / bash -c / eval) — recurse on body.
        first = _git_basename(slice_toks[0]) if slice_toks else ""
        if first in _SHELL_WRAPPERS or first == "eval":
            if _scan_shell_wrapper(slice_toks, depth) is not None:
                return True
            continue
        # A privilege-prefixed or bare git invocation starting here.
        git_toks = _strip_privilege_prefixes(slice_toks)
        if not _is_git_invocation(git_toks):
            continue
        if _scan_git_invocation(git_toks) is not None:
            return True
    return False


def _scan_git_config_write(tokens: List[str]) -> Optional[GitBypassMatch]:
    """Detect `git config ... core.hooksPath <value>` writes (split attack).

    A READ (`git config --get core.hooksPath`) is harmless and must pass —
    only a WRITE (a key + a value, or `--unset`/`--add`/`--replace-all`)
    bypasses. Heuristic: the subcommand is `config`, core.hooksPath appears
    as a key token, and it is not a pure read (`--get*`/`--list`/`-l`).
    """
    # tokens here begin at the git binary; find the subcommand.
    sub_idx = _subcommand_index(tokens)
    if sub_idx is None or tokens[sub_idx] != "config":
        return None
    rest = tokens[sub_idx + 1:]
    low_rest = [t.lower() for t in rest]
    if _HOOKSPATH_KEY not in low_rest:
        return None
    # Pure-read forms pass.
    read_only_flags = {"--get", "--get-all", "--get-regexp", "--list", "-l",
                       "--get-urlmatch"}
    if any(f in low_rest for f in read_only_flags):
        # A read of core.hooksPath. Still allow even if --unset absent.
        # But guard: an explicit write flag alongside a read flag → treat as
        # write (defensive).
        write_flags = {"--unset", "--unset-all", "--add", "--replace-all"}
        if not any(f in low_rest for f in write_flags):
            return None
    # Determine the position of the key; a value token after it (not a flag)
    # OR a write flag → it's a write.
    key_pos = low_rest.index(_HOOKSPATH_KEY)
    has_value_after = any(
        not t.startswith("-") for t in rest[key_pos + 1:]
    )
    write_flags = {"--unset", "--unset-all", "--add", "--replace-all"}
    is_unset = any(f in low_rest for f in write_flags)
    if has_value_after or is_unset:
        return GitBypassMatch(
            flag_class=FLAG_CLASS_HOOKSPATH_CONFIG_WRITE,
            reason=(
                "BLOCKED: `git config ... core.hooksPath` writes the hooks path "
                "(disables project git hooks — the split-attack bypass). "
                "Do not relocate core.hooksPath; fix the underlying issue, or "
                "use the audited dual-auth escape hatch (CEO_GIT_BYPASS_ALLOW)."
            ),
        )
    return None


def _subcommand_index(tokens: List[str]) -> Optional[int]:
    """Index of the git subcommand token, skipping global options + values.

    ``tokens`` begins at the git binary (tokens[0] == git). Global options
    that take a NEXT-token value (`-c`, `-C`, `--git-dir`, `--config-env`, …)
    consume that value; `--opt=value` forms consume nothing extra; boolean
    globals (`-p`, `--paginate`, `--no-pager`, `--bare`, …) are skipped. The
    first token that is not an option and not a consumed value is the
    subcommand.
    """
    i = 1
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if not tok.startswith("-"):
            return i
        # `--opt=value` consumes nothing extra.
        if "=" in tok:
            i += 1
            continue
        # NEXT-token value options consume the following token.
        if tok in _GIT_GLOBAL_VALUE_OPTS_NEXT:
            i += 2
            continue
        # Boolean global option.
        i += 1
    return None


def _scan_git_dir_redirect(tokens: List[str]) -> Optional[GitBypassMatch]:
    """Detect `--git-dir=` / `-C <dir>` redirection used to dodge hooks.

    `-C <dir>` and `--git-dir=<dir>` retarget the repo; combined with a
    write subcommand this can run against a repo with no hooks. We flag the
    redirect ONLY when paired with a hook-bearing write subcommand
    (commit/push/merge/cherry-pick/rebase/am) — a plain `git -C ../x status`
    is a legitimate read and MUST pass (MF-F regression fixture).
    """
    has_redirect = False
    i = 1
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if not tok.startswith("-"):
            break  # reached the subcommand
        if tok in ("-C", "--git-dir") and i + 1 < n:
            has_redirect = True
            i += 2
            continue
        if tok.lower().startswith("--git-dir="):
            has_redirect = True
            i += 1
            continue
        # `--opt=value` consumes nothing extra; NEXT-token globals consume one.
        if "=" in tok:
            i += 1
            continue
        if tok in _GIT_GLOBAL_VALUE_OPTS_NEXT:
            i += 2
            continue
        i += 1
    if not has_redirect:
        return None
    sub_idx = _subcommand_index(tokens)
    if sub_idx is None:
        return None
    if tokens[sub_idx] in _NO_VERIFY_SUBCOMMANDS:
        return GitBypassMatch(
            flag_class=FLAG_CLASS_GIT_DIR_REDIRECT,
            reason=(
                "BLOCKED: a `-C <dir>` / `--git-dir=<dir>` repo redirect paired "
                "with a hook-bearing write subcommand can run against a repo "
                "with no hooks (bypass). Run the write in the intended repo, or "
                "use the audited dual-auth escape hatch (CEO_GIT_BYPASS_ALLOW)."
            ),
        )
    return None


# Value-taking short option LETTERS on `git commit` (getopt semantics): when
# one of these appears in a short cluster, the REMAINDER of that token is its
# glued value (R2-DEFECT-2). `m`/`F`/`C`/`c`/`t` take a required arg; `S`/`u`
# are treated conservatively as value-taking (optional-arg → glued value form).
_COMMIT_VALUE_TAKING_SHORT = frozenset("mFCctSu")


def _has_short_no_verify(flag: str) -> bool:
    """True iff a commit short cluster requests --no-verify (`-n`) per getopt.

    The cluster is parsed LEFT-TO-RIGHT (getopt semantics): when a value-taking
    option letter (``_COMMIT_VALUE_TAKING_SHORT``) is reached, the REMAINDER of
    the token is that option's glued value and is NOT scanned for further flag
    letters. So `n` counts as --no-verify ONLY if it appears in the cluster
    BEFORE any value-taking option (R2-DEFECT-2).

    Examples (commit):
      -n / -nm / -nmclean / -anm  → True  (n before any value-taking opt)
      -mn / -mnope / -mclean / -Fnotes / -Cnoverify / -amn → False
        (the `n` is part of, or consumed by, a glued value)
    """
    if not flag.startswith("-") or flag.startswith("--"):
        return False
    body = flag[1:]
    for ch in body:
        if ch == "n":
            return True
        if ch in _COMMIT_VALUE_TAKING_SHORT:
            # This letter consumes the rest of the cluster as its glued value;
            # stop scanning — any `n` after it is value bytes, not a flag.
            return False
    return False


def _scan_no_verify(tokens: List[str]) -> Optional[GitBypassMatch]:
    """Detect `--no-verify` / commit-only `-n` on the 6 subcommands (MF-B/C).

    Skips the VALUE consumed by option-with-argument flags (`-m`/`-F`/…) so a
    commit message that literally contains `--no-verify` or `-n` is never
    misread as a flag (DEFECT-4). Stops at the `--` end-of-options separator.
    """
    sub_idx = _subcommand_index(tokens)
    if sub_idx is None:
        return None
    subcmd = tokens[sub_idx]
    if subcmd not in _NO_VERIFY_SUBCOMMANDS:
        return None
    args = tokens[sub_idx + 1:]
    value_opts = _COMMIT_VALUE_OPTS_NEXT if subcmd == "commit" else _GENERIC_VALUE_OPTS_NEXT
    i = 0
    n = len(args)
    while i < n:
        tok = args[i]
        # git's end-of-options separator: everything after a bare `--` is a
        # pathspec / literal arg, NOT a flag. A file literally named
        # `--no-verify` passed as `git commit -m msg -- --no-verify` is a
        # legitimate commit (hooks still run) and MUST NOT be over-blocked.
        if tok == "--":
            break
        # Option-with-argument: skip the flag AND the value it consumes, so
        # the value is never inspected as a flag.
        if tok in value_opts:
            i += 2
            continue
        if tok == "--no-verify":
            return _no_verify_match(subcmd)
        # `-n` (and combined bundles) count as --no-verify ONLY for commit.
        # For push, `-n` == --dry-run and MUST pass (MF-B).
        if subcmd == "commit" and _has_short_no_verify(tok):
            return _no_verify_match(subcmd)
        i += 1
    return None


def _no_verify_match(subcmd: str) -> GitBypassMatch:
    if subcmd == "commit":
        cls = FLAG_CLASS_NO_VERIFY_COMMIT
    else:
        cls = FLAG_CLASS_NO_VERIFY_OTHER
    return GitBypassMatch(
        flag_class=cls,
        reason=(
            "BLOCKED: `git " + subcmd + "` with --no-verify (or commit -n) "
            "skips the project's git hooks. Fix what the hook reports instead "
            "of bypassing it, or use the audited dual-auth escape hatch "
            "(CEO_GIT_BYPASS_ALLOW + _ACK=I-ACCEPT + ticket)."
        ),
    )


def _scan_inline_c_and_alias(tokens: List[str]) -> Optional[GitBypassMatch]:
    """Detect inline `-c core.hooksPath=`, `-c alias.X=<bypass>`, and the
    `--config-env=core.hooksPath=ENV` / `--config-env core.hooksPath=ENV`
    channel (DEFECT-2) among the pre-subcommand globals."""
    i = 1
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok == "--":
            break  # git end-of-options separator: nothing past here is a flag
        if not tok.startswith("-"):
            break  # reached subcommand
        # --- DEFECT-2: --config-env channel -------------------------------
        if tok == "--config-env" and i + 1 < n:
            if _config_env_sets_hookspath(tokens[i + 1]):
                return _hookspath_inline_match()
            i += 2
            continue
        if tok.startswith("--config-env=") and len(tok) > len("--config-env="):
            if _config_env_sets_hookspath(tok[len("--config-env="):]):
                return _hookspath_inline_match()
            i += 1
            continue
        # --- inline -c <key=value> ----------------------------------------
        value: Optional[str] = None
        if tok == "-c" and i + 1 < n:
            value = tokens[i + 1]
            i += 2
        elif tok.startswith("-c") and len(tok) > 2 and "=" in tok:
            # `-ccore.hooksPath=x` (glued short form, rare but valid).
            value = tok[2:]
            i += 1
        elif "=" in tok:
            i += 1
            continue
        elif tok in _GIT_GLOBAL_VALUE_OPTS_NEXT:
            i += 2
            continue
        else:
            i += 1
            continue
        if value is None:
            continue
        if _check_inline_c_hookspath(value):
            return _hookspath_inline_match()
        if _check_alias_smuggle(value):
            return GitBypassMatch(
                flag_class=FLAG_CLASS_ALIAS_ABUSE,
                reason=(
                    "BLOCKED: an inline `-c alias.<name>=...` definition smuggles "
                    "a hook bypass (--no-verify / commit -n / core.hooksPath) "
                    "into an alias. Remove it, or use the audited dual-auth "
                    "escape hatch."
                ),
            )
    return None


def _hookspath_inline_match() -> GitBypassMatch:
    return GitBypassMatch(
        flag_class=FLAG_CLASS_HOOKSPATH_INLINE,
        reason=(
            "BLOCKED: an inline `-c core.hooksPath=...` / "
            "`--config-env=core.hooksPath=...` override relocates the git "
            "hooks path (disables project hooks). Remove the override, or use "
            "the audited dual-auth escape hatch (CEO_GIT_BYPASS_ALLOW)."
        ),
    )


# Env-channel detection (MF-D). git reads GIT_CONFIG_COUNT=N then
# GIT_CONFIG_KEY_<i> / GIT_CONFIG_VALUE_<i> for i in 0..N-1. If any KEY is
# core.hooksPath, hooks are bypassed without a -c flag. Inline `VAR=value git`
# assignments and `export VAR=value` both set it. We scan at the command-string
# level (the assignments may be consumed as the `env`/inline prefix).
_GIT_CONFIG_KEY_RE = re.compile(r"^GIT_CONFIG_KEY_\d+$")


def _scan_env_channel(assignments: List[Tuple[str, str]]) -> Optional[GitBypassMatch]:
    """Detect a `GIT_CONFIG_KEY_<n>=core.hooksPath` assignment (env channel).

    ``assignments`` is the list of (NAME, VALUE) inline/exported env pairs in
    the chunk. A KEY var whose value is core.hooksPath (case-insensitive) is a
    bypass regardless of GIT_CONFIG_COUNT (defensive — we flag the intent).
    """
    for name, value in assignments:
        if _GIT_CONFIG_KEY_RE.match(name):
            if value.strip().lower() == _HOOKSPATH_KEY:
                return GitBypassMatch(
                    flag_class=FLAG_CLASS_GIT_CONFIG_ENV_CHANNEL,
                    reason=(
                        "BLOCKED: the GIT_CONFIG_COUNT/GIT_CONFIG_KEY_n env "
                        "channel sets core.hooksPath (disables project git "
                        "hooks without a -c flag). Remove the env override, or "
                        "use the audited dual-auth escape hatch."
                    ),
                )
    return None


# Match `NAME=value` and `export NAME=value` assignment tokens.
_ASSIGNMENT_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def _extract_assignments(tokens: List[str]) -> List[Tuple[str, str]]:
    """Collect inline `NAME=value` (+ `export NAME=value`) pairs in a chunk."""
    out: List[Tuple[str, str]] = []
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok == "export" and i + 1 < n:
            m = _ASSIGNMENT_RE.match(tokens[i + 1])
            if m:
                out.append((m.group(1), m.group(2)))
            i += 2
            continue
        m = _ASSIGNMENT_RE.match(tok)
        if m:
            out.append((m.group(1), m.group(2)))
        i += 1
    return out


def _scan_shell_wrapper(tokens: List[str], depth: int) -> Optional[GitBypassMatch]:
    """Recursively scan a `bash -c <body>` / `eval <body>` wrapper (DEFECT-1).

    Bounded: max recursion depth ``_MAX_WRAPPER_DEPTH`` and a per-body byte
    cap ``_WRAPPER_BODY_CAP_BYTES``. Returns a match found in the body, or
    None.

    R2-DEFECT-1 — the recursion cap fails CLOSED, not OPEN: when a STILL-
    RECOGNIZED shell/eval wrapper carrying a body is reached AT or BEYOND the
    cap, we BLOCK with ``flag_class=parse_failure`` (we refuse to recurse
    deeper but must not silently allow a deeply-nested bypass). Does NOT
    handle `$(...)` / backticks (accepted boundary).
    """
    if not tokens:
        return None
    first = _git_basename(tokens[0])
    body: Optional[str] = None
    if first in _SHELL_WRAPPERS:
        # find `-c <body>` (the first -c; ignore other shell flags).
        i = 1
        n = len(tokens)
        while i < n:
            if tokens[i] == "-c" and i + 1 < n:
                body = tokens[i + 1]
                break
            i += 1
    elif first == "eval":
        # eval joins all following tokens into a single command string.
        rest = tokens[1:]
        if rest:
            body = " ".join(rest)
    if body is None:
        return None
    # A recognized wrapper-with-body. If we are already at/beyond the cap,
    # fail CLOSED rather than recurse (R2-DEFECT-1).
    if depth >= _MAX_WRAPPER_DEPTH:
        return GitBypassMatch(
            flag_class=FLAG_CLASS_PARSE_FAILURE,
            reason=(
                "BLOCKED: shell-wrapper recursion limit exceeded (a "
                "`bash -c`/`eval` nest deeper than the bounded scan depth) — "
                "treated as a potential hook bypass (fail-CLOSED). Flatten the "
                "command, or use the audited dual-auth escape hatch "
                "(CEO_GIT_BYPASS_ALLOW)."
            ),
        )
    if len(body) > _WRAPPER_BODY_CAP_BYTES:
        body = body[:_WRAPPER_BODY_CAP_BYTES]
    return _scan_command_inner(body, depth + 1)


# ---------------------------------------------------------------------------
# Single, canonical per-git-invocation detector set (R6-DEFECT — unification).
# ---------------------------------------------------------------------------
# Ordered tuple of every per-invocation `_scan_*` detector. There is exactly
# ONE such list in the module so the DIRECT path and BOTH alias-body paths
# (`!`-shell embedded + non-`!` git-implied) run the identical set: a detector
# that protects a top-level `git ...` command automatically protects the alias
# path too. This closes the R3/R4/R6 class of "alias path ran a hand-picked
# subset of scanners" divergences once and for all.
#
# NOTE: the env-channel scan (`_scan_env_channel`) and shell-wrapper recursion
# (`_scan_shell_wrapper`) are NOT in this list — they operate on the FULL chunk
# (assignments / wrapper bodies) BEFORE a git invocation is isolated, so they
# are invoked by the chunk-level callers, not per git-token-slice.
_GIT_INVOCATION_SCANNERS = (
    _scan_inline_c_and_alias,   # inline -c core.hooksPath / --config-env / alias
    _scan_git_config_write,     # git config core.hooksPath <val> (write)
    _scan_git_dir_redirect,     # -C <dir> / --git-dir=<dir> + write subcommand
    _scan_no_verify,            # --no-verify / commit -n family
)


def _scan_git_invocation(git_tokens: List[str]) -> Optional[GitBypassMatch]:
    """Run the COMPLETE per-invocation detector set on a git-token slice.

    ``git_tokens`` begins at the git binary (tokens[0] == git). Returns the
    first matching :class:`GitBypassMatch`, or None. This is the single source
    of truth for "is THIS git invocation a hook bypass?" — shared verbatim by
    the direct path and every alias-body path (R6 unification).
    """
    for scanner in _GIT_INVOCATION_SCANNERS:
        hit = scanner(git_tokens)
        if hit is not None:
            return hit
    return None


def _scan_chunk(chunk_tokens: List[str], depth: int) -> Tuple[Optional[GitBypassMatch], bool]:
    """Scan ONE sub-command's token list.

    Returns ``(match_or_None, _unused_parse_flag)``. The parse-failure signal
    is handled at the top level (around the single tokenize call), so the
    second element is always False here.
    """
    if not chunk_tokens:
        return None, False

    # Env-channel attack: inline/exported assignments BEFORE git (or via env).
    assignments = _extract_assignments(chunk_tokens)
    env_hit = _scan_env_channel(assignments)
    if env_hit is not None:
        return env_hit, False

    git_tokens = _strip_privilege_prefixes(chunk_tokens)

    # DEFECT-1: shell-wrapper recursion (bash/sh/... -c <body>, eval <body>).
    wrapper_hit = _scan_shell_wrapper(git_tokens, depth)
    if wrapper_hit is not None:
        return wrapper_hit, False

    if not _is_git_invocation(git_tokens):
        return None, False

    # Order: inline -c / alias / --config-env, env already done, config-write,
    # redirect, then --no-verify. First match wins. (Same set as the alias
    # paths — R6 unification via _scan_git_invocation.)
    hit = _scan_git_invocation(git_tokens)
    return (hit, False) if hit is not None else (None, False)


def _scan_command_inner(command: str, depth: int) -> Optional[GitBypassMatch]:
    """Core scan: quote-aware tokenize once, split on operators, scan chunks.

    Recursion-aware (``depth`` propagated into shell-wrapper bodies). The
    parse-failure fail-CLOSED (MF-L) is applied at THIS level: if the single
    tokenize raises AND the raw string clearly invokes git, return
    parse_failure; otherwise pass through (None).
    """
    if not command or not command.strip():
        return None
    try:
        tokens = _tokenize(command)
    except ValueError:
        # Whole-string tokenize failed (e.g. an unmatched quote somewhere).
        # Fall back to a quote-UNAWARE operator split so we keep per-chunk
        # MF-L granularity: a clean git chunk still scans, a failing git chunk
        # fails-CLOSED, a failing NON-git chunk is skipped (bounded).
        return _scan_with_naive_fallback(command, depth)
    if not tokens:
        return None
    for chunk_tokens in _split_on_operators(tokens):
        match, _pf = _scan_chunk(chunk_tokens, depth)
        if match is not None:
            return match
    return None


def _scan_with_naive_fallback(command: str, depth: int) -> Optional[GitBypassMatch]:
    """Bounded fail-CLOSED fallback when the quote-aware tokenize raised.

    Splits the raw string naively on shell operators, re-tokenizes each chunk
    independently, scans clean chunks, and fails-CLOSED only for a chunk that
    BOTH fails to lex AND clearly invokes git (MF-L). A clean git chunk paired
    with a later non-git unparseable chunk therefore still ALLOWs.
    """
    parse_failed_git = False
    for raw_chunk in _NAIVE_SPLIT_RE.split(command):
        if not raw_chunk or not raw_chunk.strip():
            continue
        try:
            chunk_tokens = _tokenize(raw_chunk)
        except ValueError:
            if _LOOKS_LIKE_GIT_RE.search(raw_chunk):
                parse_failed_git = True
            continue
        # A clean chunk may still split further (the naive split is operator-
        # aware but not quote-aware); split its token stream too.
        for sub_tokens in _split_on_operators(chunk_tokens):
            match, _pf = _scan_chunk(sub_tokens, depth)
            if match is not None:
                return match
    if parse_failed_git:
        return GitBypassMatch(
            flag_class=FLAG_CLASS_PARSE_FAILURE,
            reason=(
                "BLOCKED: a git command could not be parsed (unbalanced "
                "quotes or malformed argv) and is treated as a potential "
                "hook bypass (fail-CLOSED). Re-quote and retry, or use the "
                "audited dual-auth escape hatch (CEO_GIT_BYPASS_ALLOW)."
            ),
        )
    return None


def scan_command(command: str) -> Optional[GitBypassMatch]:
    """Pure decision function: scan a raw Bash command for git hook bypasses.

    Returns a :class:`GitBypassMatch` (block) or ``None`` (allow). No I/O.
    The dual-auth escape hatch and audit emit live in the consuming hook —
    this function is purely the detector.

    Tokenization (DEFECT-4): the command is tokenized ONCE with a quote-aware
    shlex (punctuation_chars) so quoted commit-message bodies never reach the
    flag rules and quoted shell operators never split a chain.

    Chaining (MF-F): the token stream is split on top-level shell operators; a
    trigger in ANY chained git invocation blocks.

    Shell-wrappers (DEFECT-1): `bash -c <body>` / `eval <body>` bodies are
    recursively scanned (bounded). `$(...)`/backticks remain an accepted
    boundary.

    Parse-failure (MF-L): if a command that clearly invokes git fails to
    tokenize, we fail-CLOSED with ``flag_class=parse_failure``. A non-git
    unparseable command passes through untouched (bounded).
    """
    return _scan_command_inner(command, depth=0)


__all__ = [
    "GitBypassMatch",
    "scan_command",
    "GIT_BYPASS_FLAG_CLASSES",
    "FLAG_CLASS_NO_VERIFY_COMMIT",
    "FLAG_CLASS_NO_VERIFY_OTHER",
    "FLAG_CLASS_HOOKSPATH_INLINE",
    "FLAG_CLASS_HOOKSPATH_CONFIG_WRITE",
    "FLAG_CLASS_GIT_CONFIG_ENV_CHANNEL",
    "FLAG_CLASS_GIT_DIR_REDIRECT",
    "FLAG_CLASS_ALIAS_ABUSE",
    "FLAG_CLASS_PARSE_FAILURE",
    "FLAG_CLASS_ESCAPE_HATCH",
]
