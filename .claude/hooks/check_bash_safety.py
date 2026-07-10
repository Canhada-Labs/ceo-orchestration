#!/usr/bin/env python3
"""Governance Hook: parser-aware block of destructive Bash commands.

Registered in `.claude/settings.json` under `hooks.PreToolUse.Bash`.
Runs via the `_python-hook.sh` shim. Replaces 5 substring-matching
`Bash(...)` `if:` rules that bit us twice during Sprint 2 execution:

- `echo "git reset --hard"` inside a string → falsely blocked
- A compound command containing `rm -rf` inside quotes → falsely blocked

## Root cause of the old rules

Claude Code's `if: "Bash(rm -rf*)"` does substring/prefix matching on
the raw command string. It has no parser awareness: quoted strings
match, subcommands can't be targeted individually, and the rule language
has no way to express "only when the first token is `rm`".

## Fix: shlex-based parser

This hook:

1. Reads `tool_input.command` from the hook stdin JSON.
2. Splits the command on top-level shell control operators (`&&`, `||`,
   `;`, `|`) via a naive regex. (The split over-splits inside quotes,
   but `shlex.split` on each piece fails closed on unbalanced quotes
   and the chunk is skipped — a safe failure mode.)
3. For each subcommand, uses `shlex.split()` to tokenize. Crucially,
   shlex strips quoting BEFORE the rules see the tokens, so
   `echo "rm -rf foo"` tokenizes to `['echo', 'rm -rf foo']` and the
   first token is `echo`, not `rm`.
4. Applies three rules per subcommand:
   - `rm` with both `-r` and `-f` (catches `-rf`, `-fr`, `-Rf`, `-r -f`)
   - `git reset --hard` (exact first 3 tokens)
   - `git push --force` or `git push -f` — but NOT `--force-with-lease`
5. Any match → block with a concrete remediation.
6. Any error → fail-open (allow), log breadcrumb to stderr.

## Output contract

Writes a single-line JSON decision to stdout:

    {}                                      # allow
    {"decision":"block","reason":"BLOCKED: ..."}

PLAN-135 W2 H5 adds a THIRD shape — a corrective `updatedInput` rewrite
for the `git push --force`/`-f` pilot pattern (single subcommand only):

    {"hookSpecificOutput":{"hookEventName":"PreToolUse",
      "permissionDecision":"ask",
      "permissionDecisionReason":"REWRITTEN ... --force-with-lease ...",
      "updatedInput":{"command":"git push --force-with-lease"}}}

The rewrite NEVER degrades a BLOCK into a silent allow: it always emits
`ask` (the permission prompt is retained, constraint (b)), and any
ambiguity / compound command falls back to the legacy BLOCK
(constraint (a)). Exit code is 0 in every case — Claude Code reads the
decision from stdout, not the exit code.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# PLAN-019 P0-01 / P0-02 — destructive-command bypass hardening
# ---------------------------------------------------------------------------
#
# Two coordinated fixes to the destructive-command matchers below:
#
#   P0-01: recognize long-option spellings of destructive flags.
#     Old: `rm --recursive --force dir` ALLOWED (flag-char scan skipped
#          any token starting with "--").
#     New: long options `--recursive`, `-r`, `--force` (and `--x=value`
#          forms) are parsed with exact-name matching.
#
#   P0-02: strip privilege-escalation prefixes and absolute/escaped paths
#     before the literal-equality check on ``tokens[0]``.
#     Old: `sudo rm -rf /`, `/bin/rm -rf /`, and `\rm -rf /` all ALLOWED
#          because ``tokens[0] != "rm"`` in each case.
#     New: we normalize ``tokens`` via :func:`_normalize_command_tokens`
#          so each matcher sees the effective command basename.
#
# These live in this file (not _lib) because they're intimately tied to
# the Bash-safety policy: adopters should never grep _lib for
# "destructive".


_PRIVILEGE_PREFIXES = frozenset({"sudo", "doas", "nocorrect"})

# >>> PLAN-153.E5 / ADR-175 citation-gate BEGIN (env-assignment normalization)
# A leading shell env assignment (`FOO=1 rm -rf /`, `env FOO=1 rm -rf /`)
# defeated the tokens[0] literal-equality check in every destructive matcher
# (same bypass class P0-02 closed for sudo/absolute-path spellings). Closing
# it here is a precondition for the citation gate: the gate's own structured
# channel is a leading `CEO_DESTRUCTIVE_CITE=...` assignment, which must make
# the command MORE scrutinized, never less. `env` is folded into the
# privilege-prefix strip (its value-taking flags -u/-C/--chdir/--unset are
# consumed like sudo's -u USER).
_ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_PRIVILEGE_PREFIXES = frozenset({"sudo", "doas", "nocorrect", "env"})
_PREFIX_VALUE_FLAGS = ("-u", "--user", "-C", "--chdir", "--unset")
# <<< PLAN-153.E5 / ADR-175 citation-gate END


def _normalize_command_tokens(tokens: List[str]) -> List[str]:
    """Strip privilege-escalation prefixes + normalize the command token.

    Behavior (see P0-02 above):

    - Drops leading ``sudo`` / ``doas`` / ``nocorrect`` tokens AND the
      flags that belong to them (``-u USER``, ``--user=USER``, ``-i``,
      ``-s``, ``-k``, ``-n``, ``-E``, etc.). Heuristic: after the prefix,
      any token starting with ``-`` is consumed as a prefix-flag; a known
      value-taking flag (``-u`` / ``--user``) additionally consumes the
      following non-flag token as its argument.
    - Replaces ``tokens[0]`` with its basename (``/bin/rm`` → ``rm``,
      ``./rm`` → ``rm``) after stripping a single leading backslash
      (shell alias-escape: ``\\rm`` → ``rm``).
    - PLAN-153.E5 / ADR-175: additionally drops leading shell env
      assignments (``NAME=VALUE``) and the ``env`` prefix runner, so
      ``FOO=1 rm -rf /`` / ``env FOO=1 rm -rf /`` / the citation channel
      ``CEO_DESTRUCTIVE_CITE='…' rm -rf /`` all reach the same matcher
      decision as a bare ``rm -rf /``.

    Returns a NEW list; never mutates ``tokens``. Empty input returns
    the input unchanged. Pure function (no I/O).

    Examples
    --------
    >>> _normalize_command_tokens(["sudo", "rm", "-rf", "/"])
    ['rm', '-rf', '/']
    >>> _normalize_command_tokens(["/bin/rm", "-rf", "/tmp"])
    ['rm', '-rf', '/tmp']
    >>> _normalize_command_tokens(["\\\\rm", "-rf", "/tmp"])
    ['rm', '-rf', '/tmp']
    >>> _normalize_command_tokens(["sudo", "-u", "root", "rm", "-rf", "/"])
    ['rm', '-rf', '/']
    >>> _normalize_command_tokens(["doas", "rm", "-rf", "/"])
    ['rm', '-rf', '/']
    >>> _normalize_command_tokens([])
    []
    """
    if not tokens:
        return tokens
    working = list(tokens)
    # Drop leading privilege prefixes (sudo/doas/nocorrect/env) and any flags
    # that belong to them.
    # >>> PLAN-153.E5 / ADR-175 citation-gate BEGIN (strip-loop restructure)
    # Interleaved fixed-point loop: leading NAME=VALUE env assignments and
    # privilege/env prefixes may alternate (`FOO=1 sudo rm …`,
    # `sudo env FOO=1 rm …`, `CEO_DESTRUCTIVE_CITE='…' rm …`) — keep
    # stripping until the first real command token. Pure; never raises.
    while working:
        if _ENV_ASSIGNMENT_RE.match(working[0]):
            working.pop(0)  # leading shell env assignment (NAME=VALUE)
            continue
        if working[0] in _PRIVILEGE_PREFIXES:
            working.pop(0)
            # Consume prefix-owned flags: any -flag until we hit a non-flag
            # or run out. For value-taking flags (-u USER / --user=USER /
            # env's -C DIR / --chdir DIR / --unset NAME), also pop the
            # following non-flag value token.
            while working and working[0].startswith("-"):
                flag = working.pop(0)
                if (flag in _PREFIX_VALUE_FLAGS
                        and working
                        and not working[0].startswith("-")):
                    working.pop(0)  # consume the flag's value arg
            continue
        break
    # <<< PLAN-153.E5 / ADR-175 citation-gate END
    if not working:
        return working
    first = working[0]
    # Strip leading backslash (alias-escape: ``\rm`` ≡ ``rm``).
    if first.startswith("\\"):
        first = first.lstrip("\\")
    # Basename ("/bin/rm" → "rm", "./rm" → "rm"). Path.name is empty for
    # pure-slash strings; fall back to the pre-basename value so a weird
    # path like "/" doesn't crash downstream matchers.
    basename = Path(first).name if first else first
    working[0] = basename or first
    return working

# Make the _lib package importable — hooks live in .claude/hooks/ and
# _lib is a sibling package.
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import contract as _contract  # noqa: E402
from _lib import credentials as _credentials  # noqa: E402
from _lib import git_bypass as _git_bypass  # noqa: E402
from _lib import adapters as _adapters  # noqa: E402

# PLAN-155 Wave 1 (debate A1): dispatch migrated to the shared seam
# ``_adapters.resolve()`` (resolved once per invocation in ``main()``).
# The direct claude-adapter import below is RETAINED solely as a
# back-compat alias for existing in-process tests that call
# ``check_bash_safety._claude_adapter.write_decision`` directly
# (test_check_bash_safety_h5_rewrite.py); no dispatch path uses it.
# Remove when that test migrates to the seam-era surface.
from _lib.adapters import claude as _claude_adapter  # noqa: E402,F401

try:  # noqa: E402
    from _lib import audit_emit as _audit_emit  # noqa: E402
except Exception:  # pragma: no cover
    _audit_emit = None  # type: ignore

try:  # noqa: E402
    from _lib import trusted_env as _trusted_env  # noqa: E402
except Exception:  # pragma: no cover
    _trusted_env = None  # type: ignore

try:  # noqa: E402
    from _lib import env_guard as _env_guard  # noqa: E402
except Exception:  # pragma: no cover
    _env_guard = None  # type: ignore

try:  # noqa: E402
    from _lib import egress_taxonomy as _egress_taxonomy  # noqa: E402
except Exception:  # pragma: no cover
    _egress_taxonomy = None  # type: ignore

# PLAN-124 WS-1 — git hook-bypass guard dual-auth escape hatch (MF-E).
# Reuses the proven canonical-edit dual-auth pattern
# (check_canonical_edit.py:701-705, ADR-040-AMEND-2 §Layer-1): a non-empty
# reason/ticket env var + the literal `_ACK == "I-ACCEPT"` + a ticket regex.
# CRITICAL: both vars are read from the IMPORT-TIME trusted_env snapshot
# (`_lib.trusted_env.get_trusted`), NEVER live os.environ, so a late-set
# (post-anchor) value injected by a sub-agent / subprocess cannot grant the
# bypass. Both names begin with `CEO_` so they are captured by the snapshot.
_GIT_BYPASS_ALLOW_VAR = "CEO_GIT_BYPASS_ALLOW"
_GIT_BYPASS_ALLOW_ACK_VAR = "CEO_GIT_BYPASS_ALLOW_ACK"
_GIT_BYPASS_TICKET_RE = re.compile(
    r"^(ADR-\d{3,4}|PLAN-\d{3})-[a-z0-9-]{3,100}$"
)


# Split on top-level &&, ||, ;, | — shell control operators.
# NOTE: this is a NAIVE split that ignores quoting. A command like
# `echo "a && b"` will be over-split into `echo "a` and `b"`, both of
# which fail to tokenize cleanly under shlex. PLAN-152 error-handling-01:
# such chunks are NOT silently skipped anymore — they fall through to the
# raw-text destructive-signature rescan (`_rawscan_destructive`), because
# real bash still executes the destructive core of e.g. `rm -rf ~ ";"`
# even though the mangled chunk defeats the token rules.
_SUBCOMMAND_SPLIT_RE = re.compile(r"\s*(?:&&|\|\||[;|])\s*")


@dataclass
class Rewrite:
    """A corrective `updatedInput` rewrite (PLAN-135 W2 H5).

    Carries the new command string + the before/after sha256 hashes used
    for the audit event (`bash_input_rewritten`) and a closed-enum
    `rewrite_class`. Built ONLY by :func:`_rewrite_git_push_force` and
    ONLY for the single-subcommand `git push --force`/`-f` pilot pattern.
    The single-rewriter invariant (mini-ADR-154) is structural here: at
    most ONE Rewrite is ever attached to a Decision, and the hook never
    chains a second rewrite within the same tool-call.
    """

    new_command: str
    before_sha256: str
    after_sha256: str
    rewrite_class: str  # closed enum (audit) — only "git_push_force_to_lease"
    reason: str  # human-readable; NAMES the rewrite for the permission prompt


@dataclass
class Decision:
    """Typed result of the safety check.

    A Decision is one of three shapes:
      * allow  (allow=True, rewrite=None)               → empty `{}`
      * block  (allow=False, reason=...)                → block JSON
      * rewrite-ask (allow=True, rewrite=Rewrite(...))  → permissionDecision
        `ask` + `updatedInput` (constraint (b): the rewritten command STILL
        goes through the permission prompt; the prompt text NAMES the
        rewrite). The rewrite-ask shape is materialized in `main()` (it
        needs the adapter vendor channel), NOT in `to_json()`.
    """

    allow: bool
    reason: Optional[str] = None
    rewrite: Optional["Rewrite"] = None
    # >>> PLAN-153.E5 / ADR-175 citation-gate BEGIN (destructive tag)
    # True ONLY when the block came from one of the three destructive-command
    # matchers (rm -rf / git reset --hard / git push --force), including the
    # quote-aware rawscan recheck path. The citation gate keys off this tag —
    # NEVER off reason-string matching — so canonical-path, credential-leak,
    # git-bypass and env-hijack blocks can never be unlocked by a citation.
    destructive: bool = False
    # <<< PLAN-153.E5 / ADR-175 citation-gate END

    def to_json(self) -> str:
        # Allow: emit empty JSON object — Claude Code hook schema rejects
        # top-level {"decision":"allow"} (enum is "approve"|"block"; "allow"
        # is only valid inside hookSpecificOutput.permissionDecision).
        # NOTE: to_json() is the BLOCK/ALLOW serializer only; the rewrite-ask
        # shape (updatedInput) is emitted by main() via the adapter `extra`
        # channel and never round-trips through here.
        if self.allow:
            return json.dumps({}, ensure_ascii=False)
        return json.dumps(
            {"decision": "block", "reason": self.reason or ""},
            ensure_ascii=False,
        )


def _split_subcommands(command: str) -> List[str]:
    """Split on &&, ||, ;, |. Empty/whitespace chunks are dropped."""
    if not command or not command.strip():
        return []
    parts = _SUBCOMMAND_SPLIT_RE.split(command)
    return [p for p in (s.strip() for s in parts) if p]


def _tokenize(subcommand: str) -> Optional[List[str]]:
    """shlex.split; returns None on parse error (unbalanced quotes, etc.).

    A parse failure is fail-OPEN for the token rules, NOT fail-safe: bash
    itself may still execute the destructive core of a chunk the naive
    subcommand splitter mangled (e.g. `rm -rf ~ ";"` splits into an
    unbalanced-quote chunk that shlex rejects, while real bash runs
    `rm -rf ~ ';'`). Callers must treat None as "unscanned", not "clean" —
    `decide_command` routes None through the raw-text destructive-signature
    rescan (`_rawscan_destructive`, PLAN-152 error-handling-01 / debate C4).
    """
    try:
        return shlex.split(subcommand)
    except ValueError:
        return None


def _check_rm_rf(tokens: List[str]) -> Optional[str]:
    """Return a block reason if tokens match `rm` with -r AND -f.

    Post PLAN-019 P0-01 + P0-02:

    - Privilege prefixes (``sudo``/``doas``/``nocorrect``) + their flags
      are stripped via :func:`_normalize_command_tokens`.
    - Absolute-path invocations (``/bin/rm``) and escaped-alias
      invocations (``\\rm``) are normalized to ``rm`` by the same helper.
    - Long options ``--recursive``, ``-r`` (alias), ``--force`` and their
      ``=value`` forms are detected alongside the original short-form
      character scan (``-rf``, ``-fr``, ``-Rf``, etc.).
    """
    tokens = _normalize_command_tokens(tokens)
    if not tokens or tokens[0] != "rm":
        return None
    has_r = False
    has_f = False
    for t in tokens[1:]:
        if not t.startswith("-"):
            continue  # positional argument
        if t.startswith("--"):
            # Long option: match exact names (+ optional =value tail).
            # The ``=value`` form on ``--recursive``/``--force`` is NON-
            # STANDARD for POSIX ``rm`` (which treats both as boolean
            # flags). Security-first interpretation: if someone types
            # ``--recursive=<value>`` they are almost certainly probing
            # the parser; treat the equals-form on destructive flags as
            # implying BOTH ``-r`` and ``-f`` (defensive fail-closed).
            # See PLAN-019 P0-01 live-verification vector
            # ``rm --recursive=true /tmp``.
            has_eq = "=" in t
            name = t[2:].split("=", 1)[0].lower()
            if name in ("recursive", "r"):
                has_r = True
                if has_eq:
                    has_f = True
            elif name == "force":
                has_f = True
                if has_eq:
                    has_r = True
            if has_r and has_f:
                break
            continue
        body = t[1:]  # strip single leading dash
        # Case-insensitive match catches -Rf, -rF, etc.
        lowered = body.lower()
        if "r" in lowered:
            has_r = True
        if "f" in lowered:
            has_f = True
        if has_r and has_f:
            break
    if has_r and has_f:
        return (
            "BLOCKED: `rm` with -r and -f is destructive. "
            "Specify exact files (`rm <file>` without -r), use trash-cli, "
            "or run the command outside Claude Code if you really mean it."
        )
    return None


def _check_git_reset_hard(tokens: List[str]) -> Optional[str]:
    """Return a block reason if tokens start with `git reset --hard`.

    Post PLAN-019 P0-02: tokens are normalized (``sudo git …``,
    ``/usr/bin/git …``, ``\\git …`` all reach the same decision).
    """
    tokens = _normalize_command_tokens(tokens)
    if (
        len(tokens) >= 3
        and tokens[0] == "git"
        and tokens[1] == "reset"
        and tokens[2] == "--hard"
    ):
        return (
            "BLOCKED: `git reset --hard` is destructive. "
            "Use `git stash` to save uncommitted changes, or "
            "`git checkout <file>` to discard specific files."
        )
    return None


def _check_git_push_force(tokens: List[str]) -> Optional[str]:
    """Return a block reason if tokens are a `git push --force` / `-f`.

    Does NOT block `--force-with-lease`, which is the safe alternative.

    Post PLAN-019 P0-02: tokens are normalized (``sudo git …``,
    ``/usr/bin/git …``, ``\\git …`` all reach the same decision).
    """
    tokens = _normalize_command_tokens(tokens)
    if len(tokens) < 3 or tokens[0] != "git" or tokens[1] != "push":
        return None
    for t in tokens[2:]:
        if t == "--force" or t == "-f":
            return (
                "BLOCKED: `git push --force` is destructive. "
                "Use `git push --force-with-lease` to avoid overwriting "
                "unseen commits pushed by others."
            )
    return None


# ---------------------------------------------------------------------------
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
            # quotes a backslash escapes the next char (so \" does not
            # close); inside single quotes nothing escapes.
            if c == "\\" and quote == '"' and i + 1 < n:
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
        if c == "\\" and i + 1 < n:
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
    return None


# ---------------------------------------------------------------------------
# PLAN-135 W2 H5 — corrective `updatedInput` rewrite (mini-ADR-154)
# ---------------------------------------------------------------------------
#
# PILOT: exactly ONE pattern — a single-subcommand `git push --force`/`-f`
# is REWRITTEN to `git push --force-with-lease` and surfaced as a
# permission-prompt (`ask`) carrying the new command via `updatedInput`,
# instead of a hard BLOCK. Constraints (NORMATIVE, debate R1 security
# must-fix; THREAT-MODEL-WORKSHEET §1; Doctrine 1 corollary):
#
#   (a) FAILURE MODE IS BLOCK. The rewrite must NEVER pass the original
#       `--force` input through on a half-applied / ambiguous rewrite. If
#       reconstruction is anything but trivially safe (compound command,
#       both flags present, an unparseable chunk, a token that does not
#       round-trip), `_rewrite_git_push_force` returns None and the caller
#       falls back to the existing BLOCK. (`fail-open §5` covers
#       hook-INFRA crashes — NOT rewrite errors.)
#   (b) STILL ASKS. The rewritten command goes through the permission
#       prompt (`permissionDecision: "ask"`), never a silent allow — a
#       bare `--force-with-lease` after a `git fetch` is ≈ a force-push,
#       so a human stays in the loop. `permissionDecisionReason` NAMES the
#       rewrite.
#   (c) TOKEN-LEVEL. The rewrite operates on the SAME normalized token
#       list the detector uses (`_normalize_command_tokens`), never a
#       string-level `.replace()` against the raw command (that is an
#       injection seam — `echo "--force" && git push -f` would mis-rewrite
#       the echo'd literal). The new command is reassembled from tokens
#       via `shlex.quote`, so quoting is re-applied safely.
#
# The single-rewriter invariant (mini-ADR-154 §1): at most ONE rewriting
# hook per tool-call; this is the only one. Downstream hooks (and the
# audit log) see the POST-rewrite input. A before/after sha256 hash PAIR
# is recorded in the `bash_input_rewritten` audit event so the audited
# command provably equals the executed command.
#
# Opt-in flag: CEO_BASH_FORCE_PUSH_REWRITE=1 ENABLES the rewrite. PILOT,
# DEFAULT-OFF (W2 H5 — until its ceremony + Codex round close): the legacy
# force-push BLOCK stays the shipped behavior, so the existing byte-identity
# fixture corpus is unchanged. Read from the import-time trusted_env snapshot
# (NOT live os.environ) so a late-set value cannot toggle the rewriter mid-op.

_FORCE_PUSH_REWRITE_DISABLE_VAR = "CEO_BASH_FORCE_PUSH_REWRITE"
_FORCE_PUSH_REWRITE_CLASS = "git_push_force_to_lease"


def _force_push_rewrite_enabled() -> bool:
    """True iff the H5 force-push→lease rewrite is enabled (PILOT, default-OFF).

    Enabled ONLY when CEO_BASH_FORCE_PUSH_REWRITE == "1" in the import-time
    trusted_env snapshot (NOT live os.environ — a late-set value cannot toggle
    the rewriter mid-op). Default-OFF restores the legacy force-push BLOCK as
    the shipped behavior (existing byte-identity fixtures unchanged); the
    rewrite is an opt-in pilot. When the snapshot is unavailable the rewrite
    stays DISABLED (fail to the legacy BLOCK — the most conservative state).
    Pure; never raises.
    """
    if _trusted_env is None:  # pragma: no cover — import failure → default-OFF (block)
        return False
    try:
        raw = _trusted_env.get_trusted(_FORCE_PUSH_REWRITE_DISABLE_VAR)
    except Exception:  # pragma: no cover
        return False
    if raw is None:
        return False
    return str(raw).strip() == "1"


def _sha256_hex(text: str) -> str:
    """sha256 hex digest of ``text`` (utf-8). Pure; never raises."""
    return hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()


def _rewrite_git_push_force(command: str) -> Optional[Rewrite]:
    """Build a `git push --force-with-lease` rewrite, or None to fall back.

    Returns a :class:`Rewrite` ONLY for the pilot pattern — a command that
    is a SINGLE subcommand (no `&&`/`||`/`;`/`|`), whose normalized tokens
    are exactly ``git push ...`` carrying ``--force``/``-f`` (and NOT
    already ``--force-with-lease``). Anything else → None (caller BLOCKs;
    constraint (a)). The new command is rebuilt token-by-token from the
    normalized list and re-quoted with ``shlex.quote`` (constraint (c)),
    so a quoted/embedded ``--force`` literal in a different argv position
    can never be rewritten.

    Pure function (no I/O). The before/after hashes let the audit event
    prove audited-cmd == executed-cmd (mini-ADR-154 §2).
    """
    if not command or not command.strip():
        return None
    # Constraint (a)+(c): a COMPOUND command (multiple subcommands) is NOT
    # rewritten — reassembling a multi-subcommand line from a flat token
    # view is exactly the injection seam THREAT-MODEL-WORKSHEET §1 names
    # (`echo "--force" && git push -f`). Fall back to BLOCK.
    subcommands = _split_subcommands(command)
    if len(subcommands) != 1:
        return None
    raw_tokens = _tokenize(subcommands[0])
    if not raw_tokens:
        return None  # unparseable → BLOCK (fail-safe)
    tokens = _normalize_command_tokens(raw_tokens)
    if len(tokens) < 3 or tokens[0] != "git" or tokens[1] != "push":
        return None
    # The token-list view is the SAME the detector saw. Rewrite EXACTLY the
    # destructive flag tokens; leave every other token byte-for-byte. If a
    # `--force-with-lease` is already present we do not touch it.
    has_force_flag = False
    new_tokens: List[str] = []
    for t in tokens:
        if t == "--force" or t == "-f":
            has_force_flag = True
            new_tokens.append("--force-with-lease")
        else:
            new_tokens.append(t)
    if not has_force_flag:
        return None  # nothing to rewrite (e.g. already --force-with-lease)
    # Reassemble with shlex.quote so the rewrite is shell-safe (constraint
    # (c) — re-quoting closes the round-trip seam). The normalization
    # already basenamed token[0] and stripped any sudo/escape prefix, which
    # is the SAME effective command the rail audited and the user intended;
    # the pilot deliberately does not try to preserve a `/usr/bin/git`
    # absolute path (it would re-open the path-normalization question).
    new_command = " ".join(shlex.quote(tok) for tok in new_tokens)
    before = _sha256_hex(command)
    after = _sha256_hex(new_command)
    # Defense-in-depth: if the rewrite somehow did not change the command
    # (impossible given has_force_flag, but the audit invariant must hold),
    # fall back to BLOCK rather than emit a no-op `ask` (constraint (a)).
    if after == before or new_command == command:  # pragma: no cover
        return None
    reason = (
        "REWRITTEN (asks before running): `git push --force` → "
        "`git push --force-with-lease`. The original `--force` overwrites "
        "remote commits unconditionally; `--force-with-lease` refuses if "
        "the remote advanced since your last fetch. Review the rewritten "
        "command and approve to proceed, or reject to cancel. "
        f"Rewritten command: {new_command}"
    )
    return Rewrite(
        new_command=new_command,
        before_sha256=before,
        after_sha256=after,
        rewrite_class=_FORCE_PUSH_REWRITE_CLASS,
        reason=reason,
    )


def _git_bypass_escape_hatch_active() -> bool:
    """True iff the proven dual-auth git-bypass escape hatch is set (MF-E).

    Reads BOTH env vars from the import-time trusted_env snapshot (NOT live
    os.environ): a value set AFTER process trust-anchor is ignored. Requires:

      - ``CEO_GIT_BYPASS_ALLOW``       — non-empty, matches the ticket regex
        (``ADR-NNN[N]-slug`` | ``PLAN-NNN-slug``)
      - ``CEO_GIT_BYPASS_ALLOW_ACK``   — exactly ``I-ACCEPT``

    Off-path (missing / wrong ACK / bad ticket) → False → the bypass stays
    BLOCKED. Pure function (snapshot read only); never raises.
    """
    if _trusted_env is None:  # pragma: no cover — import failure fail-CLOSED
        return False
    try:
        reason = (_trusted_env.get_trusted(_GIT_BYPASS_ALLOW_VAR) or "").strip()
        ack = (_trusted_env.get_trusted(_GIT_BYPASS_ALLOW_ACK_VAR) or "").strip()
    except Exception:  # pragma: no cover
        return False
    return bool(
        reason
        and ack == "I-ACCEPT"
        and _GIT_BYPASS_TICKET_RE.match(reason)
    )


def _env_guard_enforced() -> bool:
    """True iff CEO_ENV_GUARD_ENFORCE=='1' in the import-time trusted_env snapshot.

    Default-OFF (PLAN-133 A1 doctrine #1): when unset/anything-but-"1" the
    env-hijack scan is advisory (emit, do NOT block). Read from the snapshot
    (NOT live os.environ) so a late-set value can't toggle enforcement mid-op.
    Pure; never raises.
    """
    if _trusted_env is None or _env_guard is None:  # pragma: no cover
        return False
    try:
        return (
            _trusted_env.get_trusted(_env_guard.ENV_GUARD_ENFORCE_FLAG) or ""
        ).strip() == "1"
    except Exception:  # pragma: no cover
        return False


def _check_env_hijack(command: str) -> "Optional[tuple]":
    """Scan for a denylisted env-var SET (PLAN-133 A1).

    Returns ``(hijack_class, key, reason)`` on a match, else ``None``. Pure;
    fail-OPEN on infra (a scan exception → None, no block, no emit) per the hook
    contract. The block/allow decision (default-OFF) is the caller's; this returns
    the match so both the emit and the decision can use it.
    """
    if _env_guard is None:
        return None
    try:
        m = _env_guard.scan_command(command)
    except Exception as e:  # pragma: no cover — fail-OPEN on infra
        print(
            f"[check_bash_safety] env-hijack scan failure; failing OPEN: "
            f"{e.__class__.__name__}",
            file=sys.stderr,
        )
        return None
    if m is None:
        return None
    return (m.hijack_class, m.key, m.reason)


def _egress_emit_enabled() -> bool:
    """True iff CEO_EGRESS_TAXONOMY_EMIT=='1' in the trusted_env snapshot.

    Default-OFF (PLAN-133 A3 doctrine #1): the egress breadcrumb is suppressed
    during the measure-first window unless the flag is set. Read from the
    import-time snapshot (NOT live os.environ). A3 NEVER blocks regardless of this
    flag — it only gates the advisory emit. Pure; never raises.
    """
    if _trusted_env is None or _egress_taxonomy is None:  # pragma: no cover
        return False
    try:
        return (
            _trusted_env.get_trusted(
                _egress_taxonomy.EGRESS_TAXONOMY_EMIT_FLAG
            ) or ""
        ).strip() == "1"
    except Exception:  # pragma: no cover
        return False


def _classify_egress(command):  # noqa: ANN001
    """Classify ALL egress destinations in `command` (PLAN-133 A3).

    Returns a list of (egress_class, destination) tuples (possibly empty). Pure;
    fail-OPEN on infra (a scan exception -> [], no emit) per the hook contract.
    """
    if _egress_taxonomy is None:
        return []
    try:
        return [
            (m.egress_class, m.destination)
            for m in _egress_taxonomy.classify_command(command)
        ]
    except Exception as e:  # pragma: no cover — fail-OPEN on infra
        print(
            f"[check_bash_safety] egress classify failure; failing OPEN: "
            f"{e.__class__.__name__}",
            file=sys.stderr,
        )
        return []


def _check_git_bypass(command: str) -> "Optional[tuple]":
    """Scan for git hook-bypass vectors (PLAN-124 WS-1).

    Returns ``(decision_kind, flag_class)`` where ``decision_kind`` is one of:

      - ``"block"`` — a bypass was detected and is NOT authorized; the second
        element is the matched closed-enum ``flag_class`` and the reason is
        rebuilt by the caller / re-scan. (We return the reason via a 3-tuple.)
      - ``"escape"`` — a bypass was detected but the dual-auth escape hatch is
        active (MF-E); the caller ALLOWs and emits ``escape_hatch_used``.

    Returns ``None`` when no bypass is detected (allow, no emit).

    Tuple shape: ``(kind, flag_class, reason)``. Pure function — no I/O beyond
    the trusted_env snapshot read; never raises (fail-OPEN on infra error per
    the hook contract, EXCEPT the tokenizer's own bounded fail-CLOSED
    parse_failure which is a deliberate BLOCK, MF-L).
    """
    try:
        match = _git_bypass.scan_command(command)
    except Exception as e:  # pragma: no cover — tokenizer infra bug → fail-OPEN
        print(
            f"[check_bash_safety] git-bypass scan failure; failing OPEN: "
            f"{e.__class__.__name__}",
            file=sys.stderr,
        )
        return None
    if match is None:
        return None
    if _git_bypass_escape_hatch_active():
        return ("escape", _git_bypass.FLAG_CLASS_ESCAPE_HATCH, match.reason)
    return ("block", match.flag_class, match.reason)


def _check_credential_leak(command: str) -> Optional[tuple]:
    """Sprint 12 / CRITICAL-2 (ADR-040): scan raw command for live keys.
    Fail-CLOSED on exception (intentional break from hook's fail-open)."""
    if not command:
        return None
    try:
        for provider, match, _off in _credentials.detect_keys(command):
            if _credentials.is_likely_real_key(match, command):
                return provider, _credentials.redacted_display(provider, match)
        return None
    except Exception as e:
        print(f"[check_bash_safety] credential-scan failure; failing closed: "
              f"{e.__class__.__name__}", file=sys.stderr)
        return "unknown", "unknown:****"


# >>> PLAN-153.E5 / ADR-175 citation-gate BEGIN (gate implementation)
# -----------------------------------------------------------------------------
# PLAN-153 Wave E item 5 / ADR-175 half 1 — destructive-Bash CITATION GATE
# -----------------------------------------------------------------------------
#
# When a command classifies as DESTRUCTIVE (rm -rf / git reset --hard /
# git push --force — Decision.destructive == True), the operator may supply
# a CITATION: the instruction that justifies the destructive op, quoted
# VERBATIM, via a leading shell env-assignment on the command itself:
#
#     CEO_DESTRUCTIVE_CITE='transcript:<verbatim instruction text>' rm -rf build/
#     CEO_DESTRUCTIVE_CITE='PLAN-153:<verbatim plan text>'          rm -rf build/
#
# Channel rationale: the assignment travels INSIDE `tool_input.command` — the
# one field this PreToolUse hook actually receives and can verify against the
# stdin payload (a separate env var would be invisible to the payload; a
# transcript-adjacent side file would be writable by the same actor issuing
# the command). `_normalize_command_tokens` strips leading assignments, so
# the citation prefix can never DE-classify the command (see the env-
# assignment normalization block above).
#
# VERIFICATION (bounded read):
#   * source `transcript` → the `transcript_path` field of the hook's OWN
#     stdin payload (Claude Code supplies it on every hook event). Hardening:
#     the resolved path must live under ~/.claude/ and end in `.jsonl` —
#     a payload pointing anywhere else fails verification (fail-CLOSED).
#     The cited text must appear verbatim (raw or JSON-escaped, since
#     transcripts are JSONL) within the LAST `_CITE_READ_CAP_BYTES` of the
#     file (recent instructions live at the tail; text beyond the bound
#     simply fails verification — the fail-closed direction).
#   * source `PLAN-NNN` → `$CLAUDE_PROJECT_DIR/.claude/plans/PLAN-NNN-*.md`
#     (PLAN-SCHEMA naming), same bounded read.
#
# FAIL-CLOSED (mirrors the `_e3` whole-command parse gate + the
# `_check_credential_leak` precedent, PLAN-152 debate C4): citation absent /
# malformed / too short / transcript unreadable / cited text not found ⇒ the
# destructive op stays BLOCKED with an actionable reason. Fail-OPEN is
# permitted ONLY on the audit-emit side (an emit failure never flips the
# decision).
#
# ACCEPTED citations are recorded into the HMAC audit chain via
# `_lib.audit_emit.emit_generic("veto_triggered", ...)` (a passthrough-
# registered action; a NEW action name would require touching
# `_lib/audit_emit.py`'s _KNOWN_ACTIONS, outside this unit's scope — the
# `reason_code=destructive_citation_accepted` + `gate_outcome` fields
# disambiguate, following the git_hook_bypass_blocked/escape_hatch_used
# precedent of recording the AUTHORIZED path under the guard's action). The
# cited text passes `_lib.redact.redact_secrets` and lands in the
# `cited_instruction_data` field — the `_data` suffix marks it as inert DATA
# (quoted evidence), never instructions.
#
# SCOPE GUARD: the gate keys off `Decision.destructive` ONLY. Canonical-path
# writes, credential leaks, git hook-bypass and env-hijack blocks are NOT
# citation-gatable — no citation unlocks those.
#
# Pilot flag: CEO_DESTRUCTIVE_CITATION_GATE == "1" ENABLES the gate
# (default-OFF, mirroring the H5 force-push-rewrite pilot: a change that adds
# an allow path to a hard block ships opt-in until its ceremony + Codex round
# close). Read from the import-time trusted_env snapshot, NOT live os.environ.

_DESTRUCTIVE_CITE_GATE_VAR = "CEO_DESTRUCTIVE_CITATION_GATE"
_DESTRUCTIVE_CITE_VAR = "CEO_DESTRUCTIVE_CITE"
_CITE_MIN_CHARS = 16                    # a real instruction, not a token
_CITE_READ_CAP_BYTES = 4 * 1024 * 1024  # bounded tail read (4 MiB)
_CITE_AUDIT_PREVIEW_CHARS = 400         # cap on cited text entering the chain
_CITE_PLAN_SOURCE_RE = re.compile(r"^PLAN-\d{3}$")
_CITE_MAX_PLAN_FILES = 5                # bound the glob fan-out


def _destructive_citation_gate_enabled() -> bool:
    """True iff CEO_DESTRUCTIVE_CITATION_GATE == "1" in the trusted_env
    snapshot (default-OFF pilot). Snapshot unavailability ⇒ DISABLED (the
    most conservative state: the legacy hard BLOCK). Pure; never raises."""
    if _trusted_env is None:  # pragma: no cover — import failure → default-OFF
        return False
    try:
        raw = _trusted_env.get_trusted(_DESTRUCTIVE_CITE_GATE_VAR)
    except Exception:  # pragma: no cover
        return False
    return (str(raw).strip() == "1") if raw is not None else False


def _extract_destructive_citation(command: str) -> "tuple":
    """Extract the CEO_DESTRUCTIVE_CITE citation from the command's leading
    env-assignment prefix.

    Returns a 3-tuple ``(status, source, cited_text)``:
      * ``("absent", "", "")``     — no citation assignment in the prefix
        (also the outcome when the whole command fails shlex — an
        unparseable command cannot carry a verifiable citation, and the
        caller's fail-closed handling keeps the op blocked).
      * ``("malformed", detail, "")`` — assignment present but not of shape
        ``<source>:<verbatim text>`` with source ``transcript`` | ``PLAN-NNN``
        and text >= _CITE_MIN_CHARS.
      * ``("ok", source, cited_text)`` — well-formed citation.

    Only the LEADING assignment run is scanned (shell semantics: assignments
    after the first command word are arguments, not environment). Pure;
    never raises.
    """
    if not command or not command.strip():
        return ("absent", "", "")
    try:
        tokens = shlex.split(command)
    except ValueError:
        return ("absent", "", "")
    value = None  # type: Optional[str]
    for tok in tokens:
        if not _ENV_ASSIGNMENT_RE.match(tok):
            break  # first non-assignment token ends the env prefix run
        name, _, rest = tok.partition("=")
        if name == _DESTRUCTIVE_CITE_VAR:
            value = rest
            break
    if value is None:
        return ("absent", "", "")
    source, sep, cited = value.partition(":")
    if not sep:
        return (
            "malformed",
            "missing ':' separator (expected '<source>:<verbatim text>')",
            "",
        )
    source = source.strip()
    if source != "transcript" and not _CITE_PLAN_SOURCE_RE.match(source):
        return (
            "malformed",
            "unknown source %r (expected 'transcript' or 'PLAN-NNN')" % source,
            "",
        )
    if len(cited) < _CITE_MIN_CHARS:
        return (
            "malformed",
            "cited text under %d chars — quote the justifying instruction "
            "verbatim, not a fragment" % _CITE_MIN_CHARS,
            "",
        )
    return ("ok", source, cited)


def _cite_bounded_tail_read(path: "Path") -> str:
    """Read at most the LAST _CITE_READ_CAP_BYTES of ``path`` as utf-8
    (errors=replace). Raises OSError family on unreadable paths — the
    CALLER converts that to a fail-CLOSED block."""
    import os as _os
    size = _os.path.getsize(str(path))
    with open(str(path), "rb") as fh:
        if size > _CITE_READ_CAP_BYTES:
            fh.seek(size - _CITE_READ_CAP_BYTES)
        data = fh.read(_CITE_READ_CAP_BYTES)
    return data.decode("utf-8", "replace")


def _cite_needles(cited_text: str) -> "List[str]":
    """The raw cited text + its JSON-escaped form (transcripts are JSONL, so
    an instruction containing quotes/newlines is stored escaped)."""
    needles = [cited_text]
    try:
        escaped = json.dumps(cited_text, ensure_ascii=False)[1:-1]
        if escaped != cited_text:
            needles.append(escaped)
    except Exception:  # pragma: no cover — dumps on str cannot realistically fail
        pass
    return needles


def _verify_destructive_citation(
    source: str,
    cited_text: str,
    transcript_path: str,
) -> "tuple":
    """Verify ``cited_text`` appears verbatim in the source it points at.

    Returns ``(ok, detail, source_class)`` where ``source_class`` is the
    closed enum ``"transcript"`` | ``"plan"`` (for the audit record) and
    ``detail`` is an actionable failure description on ``ok == False``.

    FAIL-CLOSED BY CONSTRUCTION: every unexpected exception is caught and
    converted to ``(False, ...)`` — content the gate cannot verify is
    blocked, never waved through (the `_e3` / C4 precedent).
    """
    import os as _os
    try:
        if source == "transcript":
            if not transcript_path:
                return (
                    False,
                    "hook payload carried no transcript_path (cannot verify "
                    "a 'transcript:' citation in this session)",
                    "transcript",
                )
            real = _os.path.realpath(transcript_path)
            claude_root = _os.path.realpath(
                _os.path.join(_os.path.expanduser("~"), ".claude")
            )
            if not real.startswith(claude_root + _os.sep):
                return (
                    False,
                    "transcript_path resolves outside ~/.claude/ "
                    "(refusing to verify against an arbitrary file)",
                    "transcript",
                )
            if not real.endswith(".jsonl"):
                return (
                    False,
                    "transcript_path is not a .jsonl session transcript",
                    "transcript",
                )
            if not _os.path.isfile(real):
                return (
                    False,
                    "transcript file does not exist or is not a regular file",
                    "transcript",
                )
            content = _cite_bounded_tail_read(Path(real))
            for needle in _cite_needles(cited_text):
                if needle in content:
                    return (True, "", "transcript")
            return (
                False,
                "cited text not found in the session transcript (last %d "
                "bytes searched) — the citation must be VERBATIM"
                % _CITE_READ_CAP_BYTES,
                "transcript",
            )
        # PLAN-NNN source. Codex pair-rail P2 (S261 landing): a plan file is
        # NOT a trusted citation source. Any agent can plant a line in a draft
        # `.claude/plans/PLAN-NNN-*.md` and then cite it to flip a destructive
        # command from BLOCK to ALLOW. Per the repo's fail-CLOSED rule for
        # security matchers, only the session TRANSCRIPT (append-only, written
        # by the harness, not plantable by the agent) is a trusted source for
        # authorizing a destructive op. Plan citations are rejected — cite the
        # instruction via the session transcript instead. (A future signed-
        # sentinel citation channel could reinstate a trusted file source.)
        return (
            False,
            "plan-file citations are not a trusted source (an agent can plant "
            "a line in a draft plan) — cite the authorizing instruction via "
            "the session transcript instead",
            "plan",
        )
    except Exception as e:
        # FAIL-CLOSED: unreadable source == unverifiable citation == block.
        return (
            False,
            "citation source read failed (%s) — cannot verify, so the op "
            "stays blocked" % e.__class__.__name__,
            "transcript" if source == "transcript" else "plan",
        )


def _emit_destructive_citation_accepted(
    source_class: str, source: str, cited_text: str
) -> None:
    """Record the ACCEPTED citation into the HMAC audit chain. Fail-open
    (an emit failure never flips the allow) — but NEVER writes the cited
    text unredacted: if the redactor is unavailable the text is withheld."""
    if _audit_emit is None:
        return
    try:
        try:
            from _lib.redact import redact_secrets as _redact_secrets
            cited_data = _redact_secrets(
                cited_text, max_chars=_CITE_AUDIT_PREVIEW_CHARS
            )
        except Exception:
            cited_data = "[REDACTION-UNAVAILABLE: cited text withheld]"
        import os as _os
        _audit_emit.emit_generic(
            "veto_triggered",
            hook="check_bash_safety",
            reason_code="destructive_citation_accepted",
            reason_preview=(
                "destructive Bash ALLOWED via verified citation "
                "(source=%s); see cited_instruction_data" % source_class
            ),
            blocked_tool="Bash",
            gate_outcome="allowed_with_citation",
            cite_source_class=source_class,
            cite_source_label=source[:80],
            # DATA field (ADR-175): quoted evidence of the justifying
            # instruction — redacted, truncated, inert. Never instructions.
            cited_instruction_data=cited_data,
            session_id=_os.environ.get("CLAUDE_SESSION_ID", ""),
            project=_os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:  # pragma: no cover — fail-open on emit only
        pass


def _emit_destructive_citation_rejected(detail: str) -> None:
    """Record a citation verify-failure (the op was BLOCKED). Metadata only —
    the cited bytes are NOT persisted on the reject path. Fail-open."""
    if _audit_emit is None:
        return
    try:
        _audit_emit.emit_veto_triggered(
            hook="check_bash_safety",
            reason_code="destructive_citation_verify_failed",
            reason_preview=detail[:200],
            blocked_tool="Bash",
        )
    except Exception:  # pragma: no cover — fail-open on emit only
        pass


def _extract_transcript_path(raw_stdin_text: str) -> str:
    """Best-effort read of the top-level `transcript_path` field from the
    hook's raw stdin payload (the adapter's NormalizedEvent deliberately
    drops it — deny-by-default raw_payload — so we parse the buffered raw
    text ourselves). Returns "" on any parse issue; a missing path only
    ever FAILS a 'transcript:' citation (fail-closed), never allows."""
    try:
        data = json.loads(raw_stdin_text)
        if isinstance(data, dict):
            tp = data.get("transcript_path")
            if isinstance(tp, str):
                return tp
    except Exception:
        pass
    return ""


def _apply_destructive_citation_gate(
    decision: "Decision", command: str, transcript_path: str
) -> "Decision":
    """Apply the ADR-175 citation gate to a DESTRUCTIVE block decision.

    Called from main() ONLY when the gate is enabled AND
    ``decision.destructive`` is True. Outcomes:

      * citation absent    → BLOCK (original reason + how-to-cite hint)
      * citation malformed → BLOCK (actionable shape error)
      * verify failure     → BLOCK (fail-CLOSED; actionable reason)
      * verified           → ALLOW + `destructive_citation_accepted`
                             recorded into the HMAC chain (emit fail-open)

    This function performs bounded file I/O — it lives on the main() side,
    NOT in decide_command (which stays pure).
    """
    status, source_or_detail, cited = _extract_destructive_citation(command)
    if status == "absent":
        return Decision(
            allow=False,
            reason=(decision.reason or "") + (
                "\nCITATION GATE (ADR-175): destructive Bash additionally "
                "requires a verbatim citation of the instruction that "
                "justifies it. Re-run as: "
                "CEO_DESTRUCTIVE_CITE='transcript:<verbatim instruction "
                "text>' <command>  (or 'PLAN-NNN:<verbatim plan text>'). "
                "The cited text (>= %d chars) must appear VERBATIM in the "
                "cited source or the op stays blocked." % _CITE_MIN_CHARS
            ),
            destructive=True,
        )
    if status == "malformed":
        _emit_destructive_citation_rejected("malformed: " + source_or_detail)
        return Decision(
            allow=False,
            reason=(
                "BLOCKED (citation gate, fail-CLOSED): the "
                "CEO_DESTRUCTIVE_CITE citation is malformed — %s. Expected "
                "CEO_DESTRUCTIVE_CITE='<source>:<verbatim text>' with "
                "source 'transcript' or 'PLAN-NNN'. The destructive op "
                "stays blocked." % source_or_detail
            ),
            destructive=True,
        )
    ok, detail, source_class = _verify_destructive_citation(
        source_or_detail, cited, transcript_path
    )
    if not ok:
        _emit_destructive_citation_rejected(detail)
        return Decision(
            allow=False,
            reason=(
                "BLOCKED (citation gate, fail-CLOSED): destructive Bash "
                "citation could not be verified — %s. Content the gate "
                "cannot verify is blocked, not waved through (mirror of "
                "the Wave E.3 parse gate). Fix the citation so the quoted "
                "text appears VERBATIM in the cited source, or drop the "
                "destructive command." % detail
            ),
            destructive=True,
        )
    _emit_destructive_citation_accepted(source_class, source_or_detail, cited)
    return Decision(allow=True)
# <<< PLAN-153.E5 / ADR-175 citation-gate END


# >>> PLAN-154.F6 / ADR-160 fact-gate BEGIN (deny-once ADVISORY->ENFORCE)
# -----------------------------------------------------------------------------
# PLAN-154 item 6 / ADR-160 — fact-forcing DENY-ONCE gate on the Wave-E
# citation gate (ADVISORY -> ENFORCE path)
# -----------------------------------------------------------------------------
#
# The Wave-E citation gate above (ADR-175) is a per-command allow path.
# PLAN-154 item 6 layers the FACT-FORCING ritual on top of it:
#
#   * ENFORCE mode: a DESTRUCTIVE command (Decision.destructive == True) is
#     denied ONCE per session per exact command. The deny-once state binds to
#     ``sha256(normalized command)`` (normalization strips ONLY the
#     ``CEO_DESTRUCTIVE_CITE`` assignment, so the cited retry hashes equal to
#     the original attempt). A RETRY releases ONLY on an exact-hash match AND
#     a verified citation (``_verify_destructive_citation`` — the fail-CLOSED
#     ADR-175 verifier: transcript-only source, bounded tail read, every
#     exception => BLOCK). A first attempt NEVER releases, even with a valid
#     citation — release is defined only for retries of a previously-denied
#     exact hash (the temporal fact-forcing property). While ENFORCE is
#     active the ADR-175 pilot gate is SKIPPED (deny-once is the strict
#     superset; the pilot's first-attempt allow path must not undercut it).
#   * SHADOW mode (the default — "default ADVISORY" per PLAN-154 A8): the
#     decision is returned UNTOUCHED (byte-identical legacy behavior,
#     including the ADR-175 pilot if armed). The gate only (a) records the
#     deny-once state it WOULD have used, (b) emits the shadow telemetry the
#     ADR-160 numeric flip criteria are measured from (FP < 2% over >= 50
#     gate-candidate events + >= 14 calendar days + zero integrity flags —
#     the criteria live in ADR-160; this code emits the events, it never
#     evaluates the criteria), and (c) prints ONE human-facing stderr
#     advisory line, routed through ``_lib.advisory_dampen`` (PLAN-154
#     item 5 — the single wired dampening consumer; block reasons are
#     EXEMPT and never routed there).
#
# FLIP GOVERNANCE (A8): the ADVISORY->ENFORCE flip is SETTINGS-BACKED —
# ``env.CEO_FACT_GATE_ENFORCE == "1"`` in the layered settings files
# (user < project < local < managed, read via `_lib.effective_config`'s
# layer readers — the house settings-read pattern). The ENV VAR of the same
# name is an EMERGENCY OFF only (``CEO_FACT_GATE_ENFORCE=0`` in the
# trusted_env snapshot forces advisory; the env var can NEVER enable).
# ``CEO_SOTA_DISABLE=1`` is the master kill (gate fully off, zero
# filesystem delta). Every observed activation CHANGE emits the
# ``fact_gate_activation_changed`` HMAC governance event (detection is
# lazy — hooks are per-invocation processes, so the last observed state is
# persisted in the session state file and compared on the next
# already-matched destructive command).
#
# FAIL POSTURE (PLAN-152 C4): release-side citation verification is
# fail-CLOSED (inherited from `_verify_destructive_citation`); state-file
# unavailability degrades toward MORE blocking in ENFORCE (no readable
# prior record => no release), and toward byte-identical legacy behavior
# in SHADOW; an INFRASTRUCTURE exception anywhere in the gate returns the
# incoming decision unchanged (which on this path is already a BLOCK).
# Fail-open is permitted ONLY on the audit-emit side.
#
# PROFILE GUARD: every function below is reachable ONLY from the
# already-matched destructive-block path in main() (`not decision.allow and
# decision.destructive`) — never the common path. Citation verification
# I/O additionally runs only when a well-formed citation AND a prior
# deny record both exist. No new top-level imports (os/time/effective_config/
# advisory_dampen/filelock are all lazy).
#
# STATE: per-session 0600 JSON file (tool_lifecycle.py pattern) at
# ``<audit_dir>/fact-gate/<sanitized session_id>.json`` — expires with the
# session (never consulted across sessions), atomic replace, best-effort
# lock, bounded record count.

_FACT_GATE_ENFORCE_VAR = "CEO_FACT_GATE_ENFORCE"
_FACT_GATE_SHADOW_VAR = "CEO_FACT_GATE_SHADOW"
_FACT_GATE_MASTER_KILL_VAR = "CEO_SOTA_DISABLE"
_FACT_GATE_STATE_SUBDIR = "fact-gate"
_FACT_GATE_MAX_RECORDS = 64        # per-session deny-once hash bound
_FACT_GATE_LOCK_TIMEOUT_S = 0.2    # MaybeLock budget (tool_lifecycle value)


def _fact_gate_shadow_enabled() -> bool:
    """SHADOW telemetry switch — default ON (shadow IS the gate's advisory
    default per PLAN-154 A8; the flip criteria need dogfood telemetry).
    ``CEO_FACT_GATE_SHADOW=0`` is the emergency off; ``CEO_SOTA_DISABLE=1``
    is the master kill. Read from the import-time trusted_env snapshot.
    Snapshot unavailability => ON (shadow never blocks; `_rawscan_enabled`
    precedent). Never raises."""
    if _trusted_env is None:  # pragma: no cover — import failure → stay on
        return True
    try:
        if str(_trusted_env.get_trusted(_FACT_GATE_MASTER_KILL_VAR) or "").strip() == "1":
            return False
        raw = _trusted_env.get_trusted(_FACT_GATE_SHADOW_VAR)
    except Exception:  # pragma: no cover
        return True
    return (str(raw).strip() != "0") if raw is not None else True


def _fact_gate_settings_value() -> "Optional[str]":
    """Read ``env.CEO_FACT_GATE_ENFORCE`` from the layered settings files
    via `_lib.effective_config`'s layer readers (`_layer_paths` +
    `_read_json_layer` — the resolver never raises per layer). Last-defined
    layer wins in LAYER_MERGE_ORDER (user, project, local, managed), i.e.
    managed carries the highest precedence. Returns the raw string value or
    None. INFRASTRUCTURE failure (import/paths) => None => the gate stays
    in its default-advisory state — a settings-read failure can never flip
    a new deny surface ON. Never raises."""
    try:
        from _lib import effective_config as _effective_config
        import os as _os
        project_dir = Path(
            _os.environ.get("CLAUDE_PROJECT_DIR") or _os.getcwd()
        )
        value = None  # type: Optional[str]
        for _name, _path in _effective_config._layer_paths(project_dir):
            layer = _effective_config._read_json_layer(_name, _path)
            data = layer.get("data") if isinstance(layer, dict) else None
            env_block = data.get("env") if isinstance(data, dict) else None
            if isinstance(env_block, dict) and _FACT_GATE_ENFORCE_VAR in env_block:
                value = str(env_block[_FACT_GATE_ENFORCE_VAR])
        return value
    except Exception:
        return None


def _fact_gate_enforce_state() -> "tuple":
    """Resolve the effective ENFORCE state. Returns ``(enabled, source)``
    with source a closed enum:

      * ``sota_master_off``   — CEO_SOTA_DISABLE=1 (master kill)
      * ``env_emergency_off`` — env CEO_FACT_GATE_ENFORCE=0 overrides an
                                otherwise-armed settings flip
      * ``settings``          — settings-backed ``env.CEO_FACT_GATE_ENFORCE
                                == "1"`` (the ONLY enable channel)
      * ``default_advisory``  — nothing armed (shadow)

    The env var can never ENABLE (settings-backed flip, A8). trusted_env
    unavailability => default advisory (a new deny surface must not arm on
    a degraded trust anchor). Never raises."""
    if _trusted_env is None:  # pragma: no cover — degraded anchor → advisory
        return (False, "default_advisory")
    try:
        if str(_trusted_env.get_trusted(_FACT_GATE_MASTER_KILL_VAR) or "").strip() == "1":
            return (False, "sota_master_off")
        env_raw = _trusted_env.get_trusted(_FACT_GATE_ENFORCE_VAR)
        if env_raw is not None and str(env_raw).strip() == "0":
            return (False, "env_emergency_off")
    except Exception:  # pragma: no cover
        return (False, "default_advisory")
    if _fact_gate_settings_value() == "1":
        return (True, "settings")
    return (False, "default_advisory")


def _fact_gate_normalize(command: str) -> "Optional[str]":
    """Normalize ``command`` for deny-once hashing.

    shlex-tokenize, then drop ONLY ``CEO_DESTRUCTIVE_CITE=...`` assignments
    from the LEADING env-assignment run (shell semantics: assignments after
    the first command word are arguments) and re-join with ``shlex.quote``.
    This makes the cited retry hash-equal to the original attempt while any
    OTHER textual change (different path, extra flag, different env prefix)
    produces a different hash — the "exact-hash match" release contract.

    Returns None for empty/unparseable commands: an unparseable command
    cannot bind a stable hash, so in ENFORCE it can never be released
    (fail-CLOSED — it stays on the legacy BLOCK; it also cannot carry a
    verifiable citation per `_extract_destructive_citation`). Pure."""
    if not command or not command.strip():
        return None
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if not tokens:
        return None
    out = []  # type: List[str]
    in_prefix = True
    for tok in tokens:
        if in_prefix and _ENV_ASSIGNMENT_RE.match(tok):
            name, _, _rest = tok.partition("=")
            if name == _DESTRUCTIVE_CITE_VAR:
                continue  # strip ONLY the citation channel assignment
            out.append(tok)
            continue
        in_prefix = False
        out.append(tok)
    if not out:
        return None
    return " ".join(shlex.quote(t) for t in out)


def _fact_gate_state_dir() -> "Path":
    """Per-process state base dir (tool_lifecycle `_audit_dir` pattern):
    ``CEO_AUDIT_LOG_DIR`` (live env — swarm children inherit a per-slot
    value) else ``$HOME/.claude/projects/ceo-orchestration``."""
    import os as _os
    env_dir = _os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    home = _os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration"


def _fact_gate_safe_session(session_id: str) -> str:
    """Sanitize a session_id into a single safe path component
    (tool_lifecycle `_safe_session_component` clone — traversal defense on
    an attacker-influenceable id)."""
    sid = (session_id or "").strip()
    if not sid:
        return "_nosession"
    out = "".join(
        c if (c.isalnum() or c in ("-", "_", ".")) else "_" for c in sid
    )
    if set(out) <= {"."}:
        return "_nosession"
    return out[:200]


def _fact_gate_state_path(session_id: str) -> "Path":
    return (
        _fact_gate_state_dir()
        / _FACT_GATE_STATE_SUBDIR
        / (_fact_gate_safe_session(session_id) + ".json")
    )


def _fact_gate_load(state_path: "Path") -> "Dict":
    """Load the per-session state map. Fail-open empty on any error —
    in ENFORCE an unreadable state means "no prior record" => the command
    is denied once more (degrades toward MORE blocking, never less)."""
    try:
        if not state_path.is_file():
            return {}
        with state_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    recs = data.get("records")
    if not isinstance(recs, dict):
        data["records"] = {}
    else:
        data["records"] = {
            k: v for k, v in recs.items() if isinstance(v, dict)
        }
    if not isinstance(data.get("flags"), dict):
        data["flags"] = {}
    return data


def _fact_gate_save(state_path: "Path", state: "Dict") -> None:
    """Atomic 0600 write (tool_lifecycle `_save_records` pattern).
    Fail-open: a write failure never blocks the tool decision path."""
    import os as _os
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError:
        pass
    tmp = state_path.with_suffix(state_path.suffix + ".tmp")
    try:
        fd = _os.open(str(tmp), _os.O_CREAT | _os.O_WRONLY | _os.O_TRUNC, 0o600)
        with _os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False)
        _os.replace(str(tmp), str(state_path))
        try:
            _os.chmod(str(state_path), 0o600)
        except OSError:
            pass
    except OSError:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


class _FactGateLock:
    """Best-effort FileLock wrapper (tool_lifecycle `_MaybeLock` clone).
    Lock hold is O(1); on unavailability/timeout we proceed — worst case a
    benign last-writer-wins on the tiny state file, never a blocked tool."""

    def __init__(self, state_path: "Path", timeout: float = _FACT_GATE_LOCK_TIMEOUT_S) -> None:
        self._lock = None
        try:
            from _lib.filelock import FileLock as _FileLock
            try:
                state_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            except OSError:
                pass
            self._lock = _FileLock(
                str(state_path) + ".lock", timeout=timeout
            )
        except Exception:
            self._lock = None

    def __enter__(self) -> "_FactGateLock":
        if self._lock is not None:
            try:
                self._lock.acquire()
            except Exception:
                self._lock = None  # proceed without the lock (best-effort)
        return self

    def __exit__(self, *exc) -> None:
        if self._lock is not None:
            try:
                self._lock.release()
            except Exception:
                pass


def _fact_gate_evict(records: "Dict") -> None:
    """Bound the per-session record map (evict oldest by first_denied_s so
    a new command can always earn a releasable record)."""
    while len(records) > _FACT_GATE_MAX_RECORDS:
        try:
            oldest = min(
                records.items(),
                key=lambda kv: (
                    kv[1].get("first_denied_s", 0.0)
                    if isinstance(kv[1], dict)
                    else 0.0
                ),
            )[0]
        except ValueError:  # pragma: no cover — empty map cannot exceed bound
            return
        records.pop(oldest, None)


def _fact_gate_emit(
    reason_code: str,
    *,
    gate_outcome: str,
    command_sha256: str,
    cite_status: str,
    prior_deny: bool,
    mode: str,
    source_class: str = "",
    cited_text: "Optional[str]" = None,
) -> None:
    """Record a fact-gate outcome into the HMAC chain via the passthrough-
    registered ``veto_triggered`` action (the destructive_citation_accepted
    precedent — reason_code/gate_outcome disambiguate; no new action needed
    for the shadow/enforce telemetry). METADATA ONLY on the wire: closed
    enums + booleans + the command sha256 hash; the command BYTES are never
    persisted. ``cited_text`` (release path only) passes redact_secrets and
    lands in the ``_data``-suffixed inert-evidence field, ADR-175 style.
    Fail-open (an emit failure never flips the decision)."""
    if _audit_emit is None:
        return
    try:
        import os as _os
        kwargs = dict(
            hook="check_bash_safety",
            reason_code=reason_code,
            reason_preview=(
                "fact gate %s (mode=%s, cite=%s)"
                % (gate_outcome, mode, cite_status)
            ),
            blocked_tool="Bash",
            gate_outcome=gate_outcome,
            fact_gate_mode=mode,
            command_sha256=command_sha256,
            cite_status=cite_status,
            prior_deny=bool(prior_deny),
            session_id=_os.environ.get("CLAUDE_SESSION_ID", ""),
            project=_os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
        if source_class:
            kwargs["cite_source_class"] = source_class
        if cited_text is not None:
            try:
                from _lib.redact import redact_secrets as _redact_secrets
                kwargs["cited_instruction_data"] = _redact_secrets(
                    cited_text, max_chars=_CITE_AUDIT_PREVIEW_CHARS
                )
            except Exception:
                kwargs["cited_instruction_data"] = (
                    "[REDACTION-UNAVAILABLE: cited text withheld]"
                )
        _audit_emit.emit_generic("veto_triggered", **kwargs)
    except Exception:  # pragma: no cover — fail-open on emit only
        pass


def _emit_fact_gate_activation_changed(enabled: bool, source: str) -> None:
    """HMAC governance event on every observed ADVISORY<->ENFORCE flip (A8).
    NEW action ``fact_gate_activation_changed`` — emitted via emit_generic,
    which is a silent no-op breadcrumb until the integrator lands the
    4-file action registration (the sanctioned pre-registration posture).
    Fail-open."""
    if _audit_emit is None:
        return
    try:
        import os as _os
        _audit_emit.emit_generic(
            "fact_gate_activation_changed",
            hook="check_bash_safety",
            enabled=bool(enabled),
            source=source,
            session_id=_os.environ.get("CLAUDE_SESSION_ID", ""),
            project=_os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:  # pragma: no cover — fail-open on emit only
        pass


def _emit_learning_rail_disabled(rail: str, switch: str) -> None:
    """A12 disabled-this-session breadcrumb (once per session — the caller
    gates on the persisted flag). NEW action ``learning_rail_disabled``
    (pre-registration no-op until the integrator lands it). Fail-open."""
    if _audit_emit is None:
        return
    try:
        import os as _os
        _audit_emit.emit_generic(
            "learning_rail_disabled",
            hook="check_bash_safety",
            rail=rail,
            switch=switch,
            session_id=_os.environ.get("CLAUDE_SESSION_ID", ""),
            project=_os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:  # pragma: no cover — fail-open on emit only
        pass


def _fact_gate_shadow_advisory(
    command_sha256: str, would: str, session_id: str
) -> None:
    """Human-facing stderr PROSE for a shadow observation — the ONE wired
    consumer of `_lib.advisory_dampen` (PLAN-154 item 5). This channel is
    ADVISORY ONLY: block reasons are exempt from dampening by name and are
    NEVER routed here. Dampening failure of any kind falls open to the FULL
    text (legibility is never lost). Never raises."""
    verb = "released" if would == "release" else "denied"
    text = (
        "[check_bash_safety] FACT-GATE shadow advisory: this destructive "
        "command [sha256 %s] would be %s under ENFORCE (deny-once; retry "
        "the exact command with CEO_DESTRUCTIVE_CITE='transcript:<verbatim "
        "instruction>' to release). Decision unchanged in shadow; telemetry "
        "recorded (veto_triggered/fact_gate_shadow_*); flip criteria live "
        "in ADR-160." % (command_sha256[:16], verb)
    )
    out = text
    try:
        from _lib import advisory_dampen as _advisory_dampen
        result = _advisory_dampen.dampen(
            advisory_id="fact_gate_shadow:%s:%s" % (would, command_sha256[:16]),
            text=text,
            decision="advisory",
            session_id=session_id,
        )
        out = result.text
    except Exception:
        out = text  # fail-open to FULL text
    try:
        print(out, file=sys.stderr)
    except Exception:  # pragma: no cover
        pass


def _fact_gate_deny_reason(
    original_reason: "Optional[str]",
    command_sha256: str,
    cite_status: str,
    detail: str,
) -> str:
    """The ENFORCE deny message. States the EXACT citation format that
    unlocks retry (item 6d). Deliberately contains NO ordinal and NO
    timestamp so the block reason is byte-identical at N=1 vs N=100 for
    identical input (A10 CI positive control); the appended citation-problem
    detail is deterministic for a given input."""
    base = (original_reason or "") + (
        "\nFACT GATE (PLAN-154 item 6, deny-once ENFORCE): destructive Bash "
        "is denied once per session per exact command; only a RETRY of the "
        "exact same command releases, and only with a verified citation. "
        "Retry EXACTLY as:\n"
        "  CEO_DESTRUCTIVE_CITE='transcript:<verbatim instruction text, "
        ">=%d chars>' <the same command unchanged>\n"
        "The cited text must appear VERBATIM in the current session "
        "transcript (fail-CLOSED: an unverifiable citation stays blocked). "
        "Emergency off: CEO_FACT_GATE_ENFORCE=0. "
        "[command sha256: %s]" % (_CITE_MIN_CHARS, command_sha256[:16])
    )
    if cite_status == "malformed":
        base += "\nCitation problem (malformed): %s" % detail
    elif cite_status == "verify_failed":
        base += (
            "\nCitation problem (verification failed, fail-CLOSED): %s"
            % detail
        )
    return base


def _apply_fact_gate(
    decision: "Decision",
    command: str,
    transcript_path: str,
    now_fn=None,
) -> "tuple":
    """Apply the PLAN-154 deny-once fact gate to a DESTRUCTIVE block.

    Called from main() ONLY on the already-matched rare path
    (``not decision.allow and decision.destructive``). Returns
    ``(decision, enforce_active)`` — when ``enforce_active`` is True the
    caller must SKIP the ADR-175 pilot gate (deny-once owns the outcome).

    ``now_fn`` is the injectable clock seam (A9; wall clock only as the
    default) — timestamps are used solely for record eviction ordering.

    INFRASTRUCTURE exceptions return the incoming decision unchanged
    (which on this path is already a BLOCK) with ``enforce_active=False``;
    the INPUT side (citation verification) stays fail-CLOSED inside
    `_verify_destructive_citation`.
    """
    try:
        enforce_enabled, source = _fact_gate_enforce_state()
        shadow_enabled = _fact_gate_shadow_enabled()
        if not enforce_enabled and not shadow_enabled:
            return (decision, False)  # structurally off — zero delta
        import os as _os
        import time as _time
        now = (now_fn or _time.time)()
        session_id = _os.environ.get("CLAUDE_SESSION_ID", "")
        state_path = _fact_gate_state_path(session_id)

        emit_activation = None  # type: Optional[bool]
        emit_disabled_breadcrumb = False
        cite_status = "absent"
        source_class = ""
        verify_detail = ""
        prior = False
        command_sha = ""

        with _FactGateLock(state_path):
            state = _fact_gate_load(state_path)
            records = state.setdefault("records", {})
            flags = state.setdefault("flags", {})

            # (e) lazy activation-change detection → governance event.
            last = state.get("enforce_state")
            last_enabled = bool(last.get("enabled")) if isinstance(last, dict) else False
            if last_enabled != enforce_enabled:
                emit_activation = enforce_enabled
            state["enforce_state"] = {"enabled": enforce_enabled, "source": source}

            # (A12) once-per-session disabled breadcrumb: an explicit env
            # emergency-off suppressed an otherwise-armed enforce flip.
            if (
                not enforce_enabled
                and source == "env_emergency_off"
                and not flags.get("disabled_breadcrumb")
            ):
                emit_disabled_breadcrumb = True
                flags["disabled_breadcrumb"] = True

            normalized = _fact_gate_normalize(command)
            if normalized is None:
                # Unparseable command: no stable hash → never releasable
                # (fail-CLOSED). Persist the observed enforce state only.
                _fact_gate_save(state_path, state)
                if emit_activation is not None:
                    _emit_fact_gate_activation_changed(emit_activation, source)
                if emit_disabled_breadcrumb:
                    _emit_learning_rail_disabled("fact_gate", _FACT_GATE_ENFORCE_VAR)
                return (decision, enforce_enabled)

            command_sha = hashlib.sha256(
                normalized.encode("utf-8")
            ).hexdigest()
            prior = command_sha in records

            status, src_or_detail, cited = _extract_destructive_citation(command)
            if status in ("absent", "malformed"):
                cite_status = status
                verify_detail = src_or_detail
            else:
                cite_status = "unverified"
                # Verification I/O runs ONLY when release is possible:
                # well-formed citation AND a prior deny record (item 6c).
                if prior:
                    ok, verify_detail, source_class = _verify_destructive_citation(
                        src_or_detail, cited, transcript_path
                    )
                    cite_status = "verified" if ok else "verify_failed"

            if enforce_enabled and cite_status == "verified":
                rec = records.get(command_sha)
                if not isinstance(rec, dict):  # pragma: no cover — prior implies dict
                    rec = {"first_denied_s": now, "denials": 0}
                rec["released"] = True
                rec["releases"] = int(rec.get("releases", 0)) + 1
                records[command_sha] = rec
                _fact_gate_save(state_path, state)
            elif enforce_enabled or cite_status != "verified":
                # Deny (enforce) or would-deny (shadow): record the hash so
                # an exact retry can release / be measured.
                rec = records.get(command_sha)
                if not isinstance(rec, dict):
                    rec = {"first_denied_s": now, "denials": 0, "released": False}
                rec["denials"] = int(rec.get("denials", 0)) + 1
                records[command_sha] = rec
                _fact_gate_evict(records)
                _fact_gate_save(state_path, state)
            else:
                # shadow would-release: state unchanged beyond enforce_state.
                _fact_gate_save(state_path, state)

        # --- emits + decision shaping happen OUTSIDE the lock ---------
        if emit_activation is not None:
            _emit_fact_gate_activation_changed(emit_activation, source)
        if emit_disabled_breadcrumb:
            _emit_learning_rail_disabled("fact_gate", _FACT_GATE_ENFORCE_VAR)

        if enforce_enabled:
            if cite_status == "verified":
                _fact_gate_emit(
                    "fact_gate_released",
                    gate_outcome="allowed_with_fact_gate_release",
                    command_sha256=command_sha,
                    cite_status=cite_status,
                    prior_deny=True,
                    mode="enforce",
                    source_class=source_class,
                    cited_text=cited,
                )
                return (Decision(allow=True), True)
            _fact_gate_emit(
                "fact_gate_denied",
                gate_outcome="blocked_deny_once",
                command_sha256=command_sha,
                cite_status=cite_status,
                prior_deny=prior,
                mode="enforce",
                source_class=source_class,
            )
            return (
                Decision(
                    allow=False,
                    reason=_fact_gate_deny_reason(
                        decision.reason, command_sha, cite_status, verify_detail
                    ),
                    destructive=True,
                ),
                True,
            )

        # SHADOW: decision untouched; telemetry + dampened advisory only.
        would = "release" if cite_status == "verified" else "deny"
        _fact_gate_emit(
            "fact_gate_shadow_release" if would == "release" else "fact_gate_shadow_deny",
            gate_outcome=(
                "shadow_would_release" if would == "release" else "shadow_would_deny"
            ),
            command_sha256=command_sha,
            cite_status=cite_status,
            prior_deny=prior,
            mode="shadow",
            source_class=source_class,
        )
        _fact_gate_shadow_advisory(command_sha, would, session_id)
        return (decision, False)
    except Exception as e:
        # INFRASTRUCTURE fail-open: never crash the hook; the incoming
        # decision (a BLOCK on this path) stands unchanged.
        try:
            print(
                "[check_bash_safety] WARN: fact gate infrastructure error: %s"
                % e.__class__.__name__,
                file=sys.stderr,
            )
        except Exception:  # pragma: no cover
            pass
        return (decision, False)
# <<< PLAN-154.F6 / ADR-160 fact-gate END


# -----------------------------------------------------------------------------
# PLAN-085 Wave E.3 — canonical-path Bash interceptor (heuristic v1)
# PLAN-089 Wave B  — canonical-path Bash interceptor (matrix v2, +6 matchers)
# -----------------------------------------------------------------------------

# Write-shape operators (regex token patterns) the interceptor scans for.
# v1 is intentionally conservative; full robust parsing is deferred to
# PLAN-089 long-term per evolution roadmap.
_E3_WRITE_OPERATORS = (
    ">", ">>",                       # shell redirect
    "tee", "tee-a",                  # tee + tee -a
)

# Operator tokens that take the NEXT argv as the target path.
_E3_NEXT_ARG_OPERATORS = frozenset({">", ">>", "tee"})

# Commands whose token-N argv is the target path (sed -i ...).
_E3_SED_INPLACE_RE = re.compile(r"^-i")  # match -i, -i.bak, -iE, etc.


# PLAN-089 Wave B — additional matchers for matrix v2.
#
# Each entry maps a "command first token" to a *path-extractor* callable
# that returns the list of candidate file paths from the remaining
# tokens. Returning [] means "command not matched; let other checks
# decide". The function is given the LIST of tokens (already
# shlex-split) starting from the command name itself.

# Languages with -c / -e bodies that may contain literal canonical paths.
# We do NOT execute the body — we substring-scan for any guard pattern.
_E3_INTERPRETER_C_FLAGS = {
    "python": ("-c",),
    "python3": ("-c",),
    "ruby":   ("-e", "-rb"),
    "node":   ("-e", "--eval"),
    "perl":   ("-e", "-E"),
}

# Interpreters whose "-i" / "-i inplace" flag implies in-place edit
# of the LAST positional path argument.
_E3_INPLACE_INTERPRETERS = {"perl", "ruby", "awk"}

# 1:1 file-mover / copy / truncator commands. The destination is the
# SEGMENT-LOCAL last positional (+ any -t/--target-directory value), NOT the
# global tokens[-1] — see _e3_segment_positionals / _e3_filemover_targets.
# (`dd of=PATH` handled separately as kv form; `touch` handled as all-args.)
# File operations split by which operands are WRITES (S207/Codex 019e90de):
#   COPY  — source is read-only; only the DEST landing path is a write.
#   MOVE  — DEST landing path is a write AND the SOURCE is removed/renamed
#           (a canonical source is destroyed) → both are canonical mutations.
#   DESTROY — every operand is a write/destroy target (rm/truncate).
_E3_COPY_CMDS = frozenset({"cp", "install", "rsync", "ditto", "ln"})
_E3_MOVE_CMDS = frozenset({"mv"})
_E3_DESTROY_CMDS = frozenset({"rm", "truncate"})
# Back-compat alias kept for any external reference (the union of all three).
_E3_FILE_MOVER_LAST_ARG = _E3_COPY_CMDS | _E3_MOVE_CMDS | _E3_DESTROY_CMDS

# Command TERMINATORS — end the current simple command's operand list. A
# last-arg matcher (cp/mv/sed -i/...) MUST resolve its target relative to the
# CURRENT command segment, not the global tokens[-1] (`cp evil x && true`).
# Includes `(` `)` `` ` `` so a `$(cp … canonical)` body is its own segment.
_E3_TERMINATORS = frozenset({"&&", "||", ";", ";;", "|", "|&", "&", "(", ")", "`"})

# Redirection operators. Bash permits redirections ANYWHERE in a simple command,
# so a redirect clause (operator + its target) is SKIPPED while the command keeps
# collecting operands AFTER it — else `cp src < /dev/null .claude/hooks/x` hides
# the dest behind the redirect (Codex 019e90de R2#1). Read-only: < << <<<.
_E3_REDIRECTS = frozenset({
    "<", "<<", "<<<", ">", ">>", ">|", "<>",
    "1>", "1>>", "2>", "2>>", "&>", "&>>",
    ">&", "<&",                 # fd-dup (`2>&1`, `0<&3`) — skip so the fd target
                                # ('1'/'3') doesn't poison operand parsing (R3#1).
})

# Redirects whose TARGET is itself a WRITE (a canonical target there is a write).
# `<>` opens read/write (can create/truncate); `>&FILE` (csh-style) redirects
# stdout+stderr to a file, so a canonical target there is a write too (R3#1).
# A fd-dup `2>&1` has a DIGIT target → not canonical → correctly not blocked.
_E3_WRITE_REDIRECTS = frozenset({">", ">>", ">|", "<>", "1>", "1>>", "2>", "2>>", "&>", "&>>", ">&"})

# Back-compat alias (the union) for any external reference.
_E3_BOUNDARY_TOKENS = _E3_TERMINATORS | _E3_REDIRECTS

# tee flags that take NO separate value (--output-error carries =MODE attached);
# every remaining file operand is a write target. Codex 019e90de R2#3.
_E3_TEE_FLAG_PREFIXES = ("-a", "--append", "-i", "--ignore-interrupts", "-p", "--output-error")

# Commands where EVERY positional in the segment is a create/modify target
# (no source/dest split): `touch` creates or updates each path it is given.
_E3_ALL_ARGS_TARGET = frozenset({"touch"})
# touch flags that CONSUME the next token as a value (a read/reference, NOT a
# target) — so `touch -r CANONICAL /tmp/out` does not false-positive on the ref.
_E3_TOUCH_VALUE_FLAGS = frozenset({"-r", "--reference", "-d", "--date", "-t", "--time"})


def _e3_cmd_name(tok):  # noqa: ANN001
    """Normalise a command token to its bare name: '/bin/cp'->'cp', '\\\\cp'->'cp',
    so absolute/escaped command paths can't bypass the matchers (Codex 019e90de #4)."""
    return tok.lstrip("\\").rsplit("/", 1)[-1]


def _e3_segment_positionals(tokens, start):  # noqa: ANN001
    """Positional operands of the command beginning at index ``start`` (its first
    argument). Stops at the next command TERMINATOR; SKIPS redirect clauses
    (operator + target, and an optional leading fd digit) so operands that follow
    a mid-command redirect are still collected. Chaining-safe."""
    out = []
    k = start
    n = len(tokens)
    while k < n:
        t = tokens[k]
        if t in _E3_TERMINATORS:
            break
        if t in _E3_REDIRECTS:
            k += 2                       # skip redirect operator + its target
            continue
        if t in ("1", "2") and k + 1 < n and tokens[k + 1] in _E3_REDIRECTS:
            k += 3                       # skip fd-prefix + redirect + target
            continue
        out.append(t)
        k += 1
    return out


def _e3_basename(p):  # noqa: ANN001
    return p.rstrip("/").rsplit("/", 1)[-1]


def _e3_filemover_landing_paths(args):  # noqa: ANN001
    """All paths a cp/mv/install/rsync/ln/truncate/rm/ditto command could WRITE,
    from its segment-local positional args. Handles the three destination shapes:
      • explicit DEST file       (`cp s .claude/hooks/x.py`)        -> DEST
      • DEST directory           (`cp s .claude/hooks/`)            -> DEST/basename(s)
      • -t/--target-directory DIR (`cp -t .claude/hooks s`)         -> DIR/basename(s)
    Sources are read-only, so a canonical SOURCE with a non-canonical DEST stays
    allowed (`cp .claude/hooks/x.py /tmp/bak` -> only /tmp/... is a landing path)."""
    flags_dir = []
    j = 0
    while j < len(args):
        a = args[j]
        if a == "-t" and j + 1 < len(args):
            flags_dir.append(args[j + 1]); j += 2; continue
        if a.startswith("--target-directory="):
            flags_dir.append(a.split("=", 1)[1]); j += 1; continue
        if a == "--target-directory" and j + 1 < len(args):
            flags_dir.append(args[j + 1]); j += 2; continue
        j += 1
    positionals = [a for a in args if not a.startswith("-")]
    out = []
    if flags_dir:
        for d in flags_dir:
            dd = d.rstrip("/")
            out.append(d)
            for s in positionals:                 # every positional is a SOURCE here
                out.append(dd + "/" + _e3_basename(s))
    elif positionals:
        dest = positionals[-1]
        out.append(dest)                          # explicit DEST file
        dd = dest.rstrip("/")
        for s in positionals[:-1]:                # SRC... landing inside DEST-as-dir
            out.append(dd + "/" + _e3_basename(s))
    return out

# Commands that wrap a sub-Bash via `-c`. We treat the next argument as
# an *unparsed body* and substring-scan against the guard set; the body
# is NOT re-shlex-split for deep evaluation because each layer of
# expansion is a new attack surface — a single canonical-path substring
# match is already a strong signal.
_E3_SHELL_C_INTERPRETERS = {"bash", "sh", "zsh", "ksh", "dash"}

# `eval` / `xargs` indirection — body is the next token.
_E3_INDIRECTION_VERBS = {"xargs", "eval", "find"}
# R2 Codex iter-1 Q3 fold (2026-05-13): `find` added for row 19
# `find -name 'CLAUDE.md' -exec sed -i ... {} +`. Indirection block below
# walks ALL subsequent tokens for `find` (variable -name/-exec positions);
# eval/xargs keep single-next-token scan.

# ReDoS / pathological-input cap for body scan.
_E3_BODY_CAP_BYTES = 16 * 1024


def _e3_check_canonical_path_write(command: str) -> Optional[str]:
    """Return a deny reason string if ``command`` writes to a canonical
    governance path; None otherwise.

    Heuristic v1 — uses ``shlex.split`` for tokenization. Fail-CLOSED
    on parse failure (returns a deny reason, not None) per R1 Sec-2.

    Cross-references target paths against ``check_canonical_edit._CANONICAL_GUARDS``
    via a delayed import to avoid circular dependency at module load.

    Detection set:
      - ``> path`` / ``>> path``                  (shell redirect)
      - ``tee path`` / ``tee -a path``            (tee write)
      - ``sed -i ... path``                       (in-place edit)
      - ``cat > path`` / ``cat >> path``          (cat redirect)
      - ``git checkout <ref> -- path``            (checkout-overwrite)
    """
    import shlex
    try:
        # punctuation_chars=True isolates the shell operators ( ) ; < > | & even
        # when written ADJACENT to a path (`x.py&&echo`, `printf x>file`, `$(cp …)`),
        # grouping runs into single tokens (&&, ||, ;;, |&, &>). This closes the
        # attached-operator + command-substitution bypasses (S207/Codex 019e90de).
        _lx = shlex.shlex(command, posix=True, punctuation_chars="();<>|&`")
        _lx.whitespace_split = True
        tokens = list(_lx)
    except ValueError as exc:
        # PLAN-085 Wave E.3 R1 Sec-2 — fail-CLOSED on parse failure.
        try:
            if _audit_emit is not None:
                _audit_emit.emit_veto_triggered(
                    hook="check_bash_safety",
                    reason_code="bash_parse_failed_fail_closed",
                    reason_preview=f"shlex parse failure: {exc!s}"[:200],
                    blocked_tool="Bash",
                )
        except Exception:  # pragma: no cover
            pass
        return (
            "GOVERNANCE: bash command failed shlex.split parse "
            "(fail-CLOSED per Wave E.3). Re-quote tokens and retry."
        )

    if not tokens:
        return None

    # Resolve canonical guards via delayed import.
    try:
        sys.path_hooks  # cheap shim to ensure sys is imported
        from check_canonical_edit import _CANONICAL_GUARDS, _fnmatch_segments
    except Exception:  # pragma: no cover
        return None  # fail-OPEN ON dependency failure (defense layer issue)

    import os as _os

    def _is_canonical(path: str) -> bool:
        # Candidate forms to test against the (repo-root-relative) guard globs.
        cands = [path[2:] if path.startswith("./") else path]
        # An ABSOLUTE path under the project root bypasses a relative-only match
        # (`cp evil /abs/repo/.claude/hooks/x.py`) — normalise it to repo-relative
        # (string-only normpath, no filesystem hit; collapses ./ and ..). S207 fix.
        if path.startswith("/"):
            root = _os.path.normpath(_os.environ.get("CLAUDE_PROJECT_DIR") or _os.getcwd())
            norm = _os.path.normpath(path)
            if norm.startswith(root + _os.sep):
                cands.append(norm[len(root) + 1:])
        for cand in cands:
            for pattern in _CANONICAL_GUARDS:
                try:
                    if _fnmatch_segments(cand, pattern):
                        return True
                except Exception:
                    continue
        return False

    # Scan tokens for write-shape operators and check target paths.
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        cmd = _e3_cmd_name(tok)   # normalised command name (/bin/cp -> cp, \cp -> cp)
        # write redirect (> >> >| <> 1> 1>> 2> 2>> &> &>>) — next token is target.
        if tok in _E3_WRITE_REDIRECTS:
            if i + 1 < n and _is_canonical(tokens[i + 1]):
                return (
                    f"GOVERNANCE: bash command writes to canonical path "
                    f"{tokens[i + 1]!r} via {tok!r}. Use Edit/Write tool "
                    "(sentinel-gated) instead. Wave E.3 interceptor."
                )
        # `tee [flags] file...` — tee writes EVERY file operand. Consume flags
        # (-a/--append/-i/--ignore-interrupts/-p/--output-error[=MODE]), honor --.
        if cmd == "tee":
            seen_ddash = False
            for a in _e3_segment_positionals(tokens, i + 1):
                if not seen_ddash:
                    if a == "--":
                        seen_ddash = True; continue
                    if a == "-" or a.startswith(_E3_TEE_FLAG_PREFIXES):
                        continue
                if _is_canonical(a):
                    return (
                        f"GOVERNANCE: bash 'tee' writes canonical path "
                        f"{a!r}. Use Edit/Write with sentinel. Wave E.3."
                    )
        # `sed -i <expr> path...` — targets are the segment-local positionals
        # after the script expr (chaining-safe; not global tokens[-1]).
        if cmd == "sed" and i + 1 < n and _E3_SED_INPLACE_RE.match(tokens[i + 1]):
            seg = _e3_segment_positionals(tokens, i + 1)
            positionals = [a for a in seg if not a.startswith("-")]
            for cand in positionals[1:]:   # positionals[0] = the sed script expr
                if _is_canonical(cand):
                    return (
                        f"GOVERNANCE: bash 'sed -i' to canonical path "
                        f"{cand!r} blocked. Wave E.3 interceptor."
                    )
        # `git checkout <ref> -- <path>` — token after `--` is target (segment-bounded).
        if cmd == "git" and i + 2 < n and tokens[i + 1] == "checkout":
            seg = _e3_segment_positionals(tokens, i)   # includes 'git'
            for k in range(len(seg) - 1):
                if seg[k] == "--" and _is_canonical(seg[k + 1]):
                    return (
                        f"GOVERNANCE: bash 'git checkout ... -- {seg[k + 1]!r}' "
                        "overwrites canonical path. Use sentinel ceremony."
                    )
        # ---- PLAN-089 Wave B additions ---------------------------------

        # Helper — scan an unparsed body string for any canonical path.
        # Two-pass: (a) shlex-tokenize and check each token (catches
        # whitespace-delimited paths) and (b) substring-scan against the
        # **literal** _CANONICAL_GUARDS entries (no globs) to catch paths
        # embedded inside punctuation-laden interpreter syntax such as
        # ``open('PROTOCOL.md','w')`` where shlex glues
        # ``'PROTOCOL.md','w'`` together into a single token.
        # False-positive risk is bounded by the guard list — each entry
        # is a fully-qualified governance path; ``README.md`` is NOT a
        # guard literal so a body containing the bare string
        # ``README.md`` does NOT trigger.
        def _scan_blob(blob):  # noqa: ANN001
            if not blob:
                return None
            if len(blob) > _E3_BODY_CAP_BYTES:
                # Pathological input — fail-CLOSED.
                return blob[:200]
            # (a) shlex tokenize + canonical-check each token.
            try:
                inner = shlex.split(blob, posix=True)
            except ValueError:
                # Malformed inner body — fail-CLOSED.
                return blob[:200]
            for sub in inner:
                if _is_canonical(sub):
                    return sub
            # (b) substring scan for literal guard entries.
            # Cheap O(L * len(blob)) where L = ~18 literals; bounded
            # by _E3_BODY_CAP_BYTES.
            try:
                from check_canonical_edit import _CANONICAL_GUARDS
            except Exception:
                return None
            for pattern in _CANONICAL_GUARDS:
                if not any(c in pattern for c in "*?["):
                    if pattern in blob:
                        return pattern
            return None

        # 1) Interpreter -c / -e body scan (python/ruby/node/perl).
        if cmd in _E3_INTERPRETER_C_FLAGS:
            flags = _E3_INTERPRETER_C_FLAGS[cmd]
            for j in range(i + 1, n - 1):
                if tokens[j] in flags:
                    body = tokens[j + 1]
                    hit = _scan_blob(body)
                    if hit is not None:
                        return (
                            f"GOVERNANCE: bash {tok!r} -c/-e body references "
                            f"canonical path {hit!r}. Use Edit/Write with "
                            "sentinel."
                        )
                    break

        # 2) Interpreter -i / -i inplace (perl/ruby/awk) — last positional
        #    argument is the target path.
        if cmd in _E3_INPLACE_INTERPRETERS:
            seg = _e3_segment_positionals(tokens, i + 1)
            has_inplace = any(
                (t == "-i" or t.startswith("-i.") or t == "inplace") for t in seg
            )
            positionals = [a for a in seg if not a.startswith("-")]
            if has_inplace and positionals and _is_canonical(positionals[-1]):
                return (
                    f"GOVERNANCE: bash {tok!r} -i inplace edit on canonical "
                    f"path {positionals[-1]!r}. Use Edit/Write with sentinel."
                )

        # 3) cp/install/rsync/ditto/ln (COPY) + mv (MOVE) — the WRITE target is the
        #    segment-local landing path(s), NOT the global tokens[-1] (chaining-safe).
        #    mv ALSO removes its SOURCE, so a canonical source is a mutation too.
        if cmd in _E3_COPY_CMDS or cmd in _E3_MOVE_CMDS:
            args = _e3_segment_positionals(tokens, i + 1)
            checks = list(_e3_filemover_landing_paths(args))
            if cmd in _E3_MOVE_CMDS:
                checks += [a for a in args if not a.startswith("-")]   # sources are removed
            for dest in checks:
                if _is_canonical(dest):
                    return (
                        f"GOVERNANCE: bash {tok!r} writes/mutates canonical path "
                        f"{dest!r}. Use Edit/Write with sentinel."
                    )
        # 3b) rm / truncate (DESTROY) — every operand is a destroy target.
        if cmd in _E3_DESTROY_CMDS:
            for a in _e3_segment_positionals(tokens, i + 1):
                if not a.startswith("-") and _is_canonical(a):
                    return (
                        f"GOVERNANCE: bash {tok!r} destroys canonical path "
                        f"{a!r}. Use Edit/Write with sentinel."
                    )
        # 3c) touch — every operand is a create/modify target, EXCEPT values of
        #     reference/date/time flags (-r/-d/-t) which are reads, not targets.
        if cmd in _E3_ALL_ARGS_TARGET:
            seg = _e3_segment_positionals(tokens, i + 1)
            k = 0
            while k < len(seg):
                a = seg[k]
                if a in _E3_TOUCH_VALUE_FLAGS:
                    k += 2; continue                      # skip flag + its value (a read)
                if a.startswith(("--reference=", "--date=", "--time=")) or a.startswith("-"):
                    k += 1; continue
                if _is_canonical(a):
                    return (
                        f"GOVERNANCE: bash {tok!r} creates/modifies canonical "
                        f"path {a!r}. Use Edit/Write with sentinel."
                    )
                k += 1

        # 4) dd of=PATH — kv form (segment-bounded).
        if cmd == "dd":
            for t in _e3_segment_positionals(tokens, i + 1):
                if t.startswith("of=") and _is_canonical(t[3:]):
                    return (
                        f"GOVERNANCE: bash 'dd of={t[3:]}' writes canonical "
                        "path. Use Edit/Write with sentinel."
                    )

        # 5) Shell-in-shell — bash/sh/zsh/ksh/dash -c '<body>'.
        if cmd in _E3_SHELL_C_INTERPRETERS:
            for j in range(i + 1, n - 1):
                if tokens[j] == "-c":
                    body = tokens[j + 1]
                    hit = _scan_blob(body)
                    if hit is not None:
                        return (
                            f"GOVERNANCE: bash {tok!r} -c body references "
                            f"canonical path {hit!r}. Re-tokenization "
                            "indirection denied."
                        )
                    break

        # 6) eval / xargs / find body indirection — substring-scan
        # follow-on token(s) for any canonical path reference.
        # R2 Codex iter-1 Q3 fold: `find` scans ALL subsequent tokens
        # (because find -exec / -name positions are variable); eval/xargs
        # keep single-next-token scan.
        if cmd in _E3_INDIRECTION_VERBS and i + 1 < n:
            if cmd == "find":
                for _follow in tokens[i + 1:]:
                    hit = _scan_blob(_follow)
                    if hit is not None:
                        return (
                            f"GOVERNANCE: bash 'find' invocation references "
                            f"canonical path {hit!r}. -exec sed/-i edit denied. "
                            "Use direct Edit/Write."
                        )
            else:
                body = tokens[i + 1]
                hit = _scan_blob(body)
                if hit is not None:
                    return (
                        f"GOVERNANCE: bash {tok!r} indirection references "
                        f"canonical path {hit!r}. Use direct Edit/Write."
                    )

        i += 1
    return None


def decide_command(command: str) -> Decision:
    """Pure decision function — no I/O, trivially unit-testable.

    Args:
        command: The raw `tool_input.command` string.

    Returns:
        Decision(allow=True) if no rule matches.
        Decision(allow=False, reason=...) on first rule match.
    """
    if not command or not command.strip():
        return Decision(allow=True)

    # Credential scan runs BEFORE tokenization — quoted keys must match.
    cred_hit = _check_credential_leak(command)
    if cred_hit is not None:
        return Decision(allow=False, reason=(
            "GOVERNANCE: bash command contains what appears to be a live "
            f"API credential. Redact before executing. Pattern: {cred_hit[1]}. "
            "Export via env var (never inline)."))

    # PLAN-085 Wave E.3 — canonical-path write interceptor (heuristic v1).
    canonical_reason = _e3_check_canonical_path_write(command)
    if canonical_reason is not None:
        return Decision(allow=False, reason=canonical_reason)

    # PLAN-133 A1 — linker/loader/runtime env-hijack denylist. Runs BEFORE the
    # destructive matchers (a higher-severity class). Default-OFF: only BLOCKS
    # when CEO_ENV_GUARD_ENFORCE=='1'; otherwise advisory (the emit still fires
    # in main()). decide_command stays pure (no emit here).
    if _env_guard_enforced():
        env_hit = _check_env_hijack(command)
        if env_hit is not None:
            _hijack_class, _key, reason = env_hit
            return Decision(allow=False, reason=reason)

    # PLAN-124 WS-1 — git hook-bypass guard (runs BEFORE the destructive
    # matchers; an authorized escape-hatch use ALLOWs, an unauthorized bypass
    # BLOCKs, and the bounded parse_failure is a deliberate fail-CLOSED).
    git_bypass_hit = _check_git_bypass(command)
    if git_bypass_hit is not None:
        kind, _flag_class, reason = git_bypass_hit
        if kind == "block":
            return Decision(allow=False, reason=reason)
        # kind == "escape": dual-auth authorized → ALLOW (emit handled in main).

    for subcommand in _split_subcommands(command):
        tokens = _tokenize(subcommand)
        if tokens is None:
            # PLAN-152 error-handling-01 (debate C4 + Codex R2 P2#1): shlex
            # rejected this chunk — the naive splitter broke inside quotes
            # (e.g. `rm -rf ~ ";"`). Re-tokenize the WHOLE command and block
            # only if a real command SEGMENT is destructive; quoted text
            # like `echo "a && rm -rf /tmp"` re-parses to a single benign
            # `echo` segment and is allowed. CEO_BASH_RAWSCAN=0 reverts.
            if _rawscan_enabled():
                reason = _recheck_whole_command(command)
                if reason:
                    # PLAN-153.E5 / ADR-175: destructive=True — rawscan hits
                    # are the same destructive class, so they are citation-
                    # gatable (main() applies the gate off this tag).
                    return Decision(allow=False, reason=reason, destructive=True)
            continue
        if not tokens:
            continue
        for check in (
            _check_rm_rf,
            _check_git_reset_hard,
            _check_git_push_force,
        ):
            reason = check(tokens)
            if reason:
                # PLAN-135 W2 H5 — corrective rewrite for the force-push
                # pattern ONLY. When the rewrite is enabled AND the command
                # is the trivially-safe single-subcommand `git push --force`
                # pilot pattern, REWRITE → `--force-with-lease` and surface
                # an `ask` (constraint (b)) carrying the new command via
                # updatedInput, instead of a hard BLOCK. Any failure to
                # build a clean rewrite (compound command, ambiguity, etc.)
                # falls through to the existing BLOCK (constraint (a): the
                # corrective rewrite NEVER degrades a BLOCK into a silent
                # allow — Doctrine 1 corollary). All OTHER block reasons
                # (rm -rf, git reset --hard) are unaffected.
                if check is _check_git_push_force and _force_push_rewrite_enabled():
                    rewrite = _rewrite_git_push_force(command)
                    if rewrite is not None:
                        # allow=True is the contract-layer carrier; main()
                        # translates the attached Rewrite into the `ask` +
                        # updatedInput vendor shape. The permission prompt is
                        # ALWAYS retained — this is never a silent allow.
                        return Decision(allow=True, rewrite=rewrite)
                # PLAN-153.E5 / ADR-175: destructive=True marks this block as
                # citation-gatable (main() applies the gate off this tag).
                return Decision(allow=False, reason=reason, destructive=True)

    return Decision(allow=True)


def _to_contract_decision(
    d: "Decision",
    tool_input: "Optional[Dict]" = None,
) -> _contract.Decision:
    """Translate local Decision → adapter-layer contract.Decision.

    PLAN-135 W2 H5: when the Decision carries a :class:`Rewrite`, build the
    Claude Code PreToolUse `ask` + `updatedInput` vendor shape via the
    neutral contract `extra` channel (the claude adapter merges `extra`
    into the top-level JSON). The output is:

        {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": "<names the rewrite>",
            "updatedInput": {<original tool_input>, "command": "<rewritten>"}
        }}

    The ORIGINAL tool_input keys are preserved and only `command` is
    overridden (constraint (c) — we change the command, nothing else). If
    `tool_input` is not a dict, `updatedInput` carries just the rewritten
    command (the executor reads `command`).
    """
    if d.rewrite is not None:
        rw = d.rewrite
        updated_input: Dict[str, object] = {}
        if isinstance(tool_input, dict):
            updated_input.update(tool_input)
        updated_input["command"] = rw.new_command
        dec = _contract.allow()
        dec.extra["hookSpecificOutput"] = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": rw.reason,
            "updatedInput": updated_input,
        }
        return dec
    if d.allow:
        return _contract.allow()
    return _contract.block(d.reason or "")


def _emit_git_hook_bypass_event(flag_class: str) -> None:
    """Emit git_hook_bypass_blocked(flag_class). Fail-open (PLAN-124 WS-1).

    The ONLY field is the closed-enum flag_class — NEVER the command bytes
    (MF-G). Emitted on BOTH an unauthorized block AND an authorized
    escape-hatch use (flag_class=escape_hatch_used). session_id / project are
    read from the live env (forensic envelope only; not a grant source).
    """
    if _audit_emit is None:
        return
    try:
        import os as _os
        _audit_emit.emit_git_hook_bypass_blocked(
            flag_class=flag_class,
            session_id=_os.environ.get("CLAUDE_SESSION_ID", ""),
            project=_os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:  # pragma: no cover
        pass


def _emit_env_var_hijack_event(hijack_class: str) -> None:
    """Emit env_var_hijack_blocked(hijack_class). Fail-open (PLAN-133 A1).

    The ONLY caller-supplied field is the closed-enum `hijack_class` — NEVER the
    variable NAME and NEVER the assigned VALUE (the value is the payload surface,
    MF analogous to git_hook_bypass MF-G). session_id / project are read from the
    live env (forensic envelope only; not a grant source). Emitted on BOTH an
    enforced block AND an advisory (default-OFF) detection.
    """
    if _audit_emit is None:
        return
    try:
        import os as _os
        _audit_emit.emit_env_var_hijack_blocked(
            hijack_class=hijack_class,
            session_id=_os.environ.get("CLAUDE_SESSION_ID", ""),
            project=_os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:  # pragma: no cover
        pass


def _emit_egress_destination_event(egress_class: str, destination: str) -> None:
    """Emit egress_destination_detected(egress_class, destination). Fail-open.

    `destination` is ALREADY host-only (egress_taxonomy reduces it); the audit
    emitter re-truncates defensively. The full URL / path / query / inline
    credential is NEVER passed here. When egress_class == 'pair_rail' the caller
    ALSO emits pair_rail_outgoing_redaction_applied (positive proof the outbound
    redactor ran on the sanctioned channel). session_id / project are forensic
    envelope only (not a grant source).
    """
    if _audit_emit is None:
        return
    try:
        import os as _os
        _sid = _os.environ.get("CLAUDE_SESSION_ID", "")
        _proj = _os.environ.get("CLAUDE_PROJECT_DIR", "")
        _audit_emit.emit_egress_destination_detected(
            egress_class=egress_class,
            destination=destination,
            session_id=_sid,
            project=_proj,
        )
        if egress_class == "pair_rail":
            _audit_emit.emit_pair_rail_outgoing_redaction_applied(
                signal="egress_taxonomy",
                family="pair_rail",
                match_count=0,
                bytes_scanned=0,
                callsite="check_bash_safety.egress",
                session_id=_sid,
                project=_proj,
            )
    except Exception:  # pragma: no cover
        pass


def _emit_credential_leak_event(provider: str, redacted: str) -> None:
    """Emit veto_triggered(credential_leak). Fail-open."""
    if _audit_emit is None:
        return
    try:
        _audit_emit.emit_veto_triggered(
            hook="check_bash_safety", reason_code="credential_leak",
            reason_preview=f"bash_credential_leak_blocked provider={provider} match={redacted}",
            blocked_tool="Bash")
    except Exception:  # pragma: no cover
        pass


def _emit_bash_input_rewritten_event(rewrite: "Rewrite") -> None:
    """Emit bash_input_rewritten with the before/after hash PAIR. Fail-open.

    PLAN-135 W2 H5 (mini-ADR-154 §2). The ONLY caller-supplied fields are
    the closed-enum `rewrite_class` and the two 64-hex sha256 hashes — the
    command BYTES (before OR after) are NEVER persisted (a force-push line
    can carry a remote URL with an inline token). The hash pair lets an
    auditor prove the audited command equals the executed command without
    seeing either command. session_id / project are forensic envelope only.
    """
    if _audit_emit is None:
        return
    try:
        import os as _os
        _audit_emit.emit_bash_input_rewritten(
            rewrite_class=rewrite.rewrite_class,
            before_sha256=rewrite.before_sha256,
            after_sha256=rewrite.after_sha256,
            session_id=_os.environ.get("CLAUDE_SESSION_ID", ""),
            project=_os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:  # pragma: no cover
        pass


def _adapter_emit(adapter, decision, event=None) -> None:
    """Emit a neutral ``Decision`` through the resolved host adapter
    (PLAN-155 Wave 1 dispatch seam, debate A1).

    Claude path: the historical two-arg call — byte-identical output
    (``claude.py:emit_decision`` does not take ``event=``). Any other
    resolved adapter (codex host mode, ``_FailClosedAdapter``) receives
    the parsed NormalizedEvent so the egress shape follows the wire that
    produced it (host shape is EXPLICIT-only) and the debate-A2
    coherence override can fire.
    """
    adapter_basename = (getattr(adapter, "__name__", "") or "").rsplit(".", 1)[-1]
    if adapter_basename == "claude":
        adapter.emit_decision(decision)
        return
    adapter.emit_decision(decision, event=event)


def main() -> int:
    """Hook entry point: read stdin via Adapter Layer, decide, write stdout, exit 0.

    PLAN-006 Phase 1 migration (ADR-014). Uses `claude_adapter.read_event()`
    / `emit_decision()` instead of direct `_lib.payload` + `print()`.
    Output is byte-identical to pre-migration (test_hook_byte_fidelity).

    PLAN-155 Wave 1 (debate A1, ratified seam option b): the adapter is
    resolved ONCE per invocation via the shared seam
    ``_lib.adapters.resolve()`` — BEFORE the fail-open try block, so the
    debate-A2 coherence gate inside ``resolve()``
    (explicitly-set-but-unresolvable ``CEO_HOOK_ADAPTER`` → INPUT class
    per PLAN-152 C4 → fail-CLOSED: ``resolve()`` returns a
    ``_FailClosedAdapter`` whose egress ALWAYS denies in BOTH harness
    vocabularies, with a stderr + audit breadcrumb — never a silent
    fallback to the claude adapter) is never swallowed into an allow.
    Under ``CEO_HOOK_ADAPTER`` unset/"claude" the seam returns the claude
    adapter module and downstream behavior is byte-identical.
    """
    _adapter = _adapters.resolve()
    event = None
    try:
        # >>> PLAN-153.E5 / ADR-175 citation-gate BEGIN (stdin buffering)
        # Read stdin ONCE into a buffer, then hand the adapter an equivalent
        # stream. The adapter's NormalizedEvent deliberately drops the raw
        # payload (deny-by-default), but the citation gate needs the
        # top-level `transcript_path` field — parsed here from the SAME
        # bytes the adapter consumes, so the verified path is exactly what
        # the harness sent. Behavior-neutral for every other code path.
        import io as _io
        try:
            _raw_stdin_text = sys.stdin.read()
        except Exception:  # exotic stdin failure → same fail-open as before
            _raw_stdin_text = ""
        event = _adapter.read_event(
            stream=_io.StringIO(_raw_stdin_text), phase="PreToolUse"
        )
        # <<< PLAN-153.E5 / ADR-175 citation-gate END
        if event.parse_error:
            print(
                f"[check_bash_safety] WARN: stdin parse error: {event.parse_error}",
                file=sys.stderr,
            )
            _adapter_emit(_adapter, _contract.allow(), event)
            return 0

        command = event.command or ""
        if not command and isinstance(event.tool_input, dict):
            command = str(event.tool_input.get("command") or "")

        decision = decide_command(command)
        # >>> PLAN-153.E5 / ADR-175 citation-gate BEGIN (gate application)
        # Applied ONLY to destructive-class blocks (Decision.destructive) and
        # ONLY when the pilot flag is armed. Verified citation → ALLOW +
        # HMAC-chain record; absent/malformed/unverifiable → BLOCK
        # (fail-CLOSED). Runs BEFORE the emit tail so downstream emits see
        # the final decision.
        # >>> PLAN-154.F6 fact-gate BEGIN (deny-once application)
        # The PLAN-154 deny-once fact gate runs FIRST on the same rare
        # already-matched path. SHADOW (default): decision untouched,
        # telemetry only — the ADR-175 pilot below then behaves exactly as
        # before. ENFORCE (settings-backed flip): the fact gate owns the
        # outcome (deny-once / exact-hash cited release) and the pilot is
        # SKIPPED — its first-attempt allow path must not undercut the
        # deny-once ritual.
        if not decision.allow and decision.destructive:
            _fact_transcript_path = _extract_transcript_path(_raw_stdin_text)
            decision, _fact_enforce_active = _apply_fact_gate(
                decision, command, _fact_transcript_path
            )
            if (
                not decision.allow
                and decision.destructive
                and not _fact_enforce_active
                and _destructive_citation_gate_enabled()
            ):
                decision = _apply_destructive_citation_gate(
                    decision, command, _fact_transcript_path
                )
        # <<< PLAN-154.F6 fact-gate END
        # <<< PLAN-153.E5 / ADR-175 citation-gate END
        # Re-run detector on credential blocks to emit audit event.
        if not decision.allow and decision.reason and "API credential" in decision.reason:
            hit = _check_credential_leak(command)
            if hit is not None:
                _emit_credential_leak_event(hit[0], hit[1])
        # PLAN-124 WS-1 — emit git_hook_bypass_blocked on a block OR an
        # authorized escape-hatch use. Re-scan to recover the closed-enum
        # flag_class (decide_command stays pure / I/O-free). The credential
        # block above takes precedence, so skip if the reason was a credential.
        if not (decision.reason and "API credential" in decision.reason):
            git_hit = _check_git_bypass(command)
            if git_hit is not None:
                _kind, _flag_class, _reason = git_hit
                # block → emit the matched flag_class; escape → escape_hatch_used.
                _emit_git_hook_bypass_event(_flag_class)
        # PLAN-133 A1 — emit env_var_hijack_blocked on ANY detected env-hijack
        # SET (enforced block OR advisory default-OFF detection). Re-scan to
        # recover the closed-enum hijack_class (decide_command stays pure). Only
        # the closed-enum class is persisted — never the var name/value.
        if not (decision.reason and "API credential" in decision.reason):
            env_hit = _check_env_hijack(command)
            if env_hit is not None:
                _hijack_class, _key, _reason = env_hit
                _emit_env_var_hijack_event(_hijack_class)
        # PLAN-133 A3 — egress-destination taxonomy. Classify EVERY command
        # (block OR allow — this emit tail runs on all paths) and emit one
        # egress_destination_detected per distinct (class, host). Default-OFF
        # via CEO_EGRESS_TAXONOMY_EMIT (advisory; A3 never blocks). The
        # destructive/credential/git-bypass blocks above do NOT gate this emit,
        # so a destructive+egress compound still records the egress.
        if _egress_emit_enabled():
            for _eclass, _edest in _classify_egress(command):
                _emit_egress_destination_event(_eclass, _edest)
        # PLAN-135 W2 H5 — when decide_command chose the corrective rewrite,
        # emit the bash_input_rewritten audit event with the before/after
        # hash PAIR BEFORE emitting the `ask` decision (mini-ADR-154 §2: the
        # audit records that the rail rewrote the input, so the downstream
        # audited command provably equals the executed/asked command). The
        # emit is fail-open (it never gates the decision).
        if decision.rewrite is not None:
            _emit_bash_input_rewritten_event(decision.rewrite)
        _adapter_emit(
            _adapter, _to_contract_decision(decision, event.tool_input), event
        )
        return 0
    except Exception as e:  # pragma: no cover
        print(
            f"[check_bash_safety] FATAL: {e.__class__.__name__}: {e}",
            file=sys.stderr,
        )
        _adapter_emit(_adapter, _contract.allow(), event)
        return 0


if __name__ == "__main__":
    sys.exit(main())
