"""Token normalization, destructive checks, and decision models."""
from __future__ import annotations

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
2. Legacy split/token rules run first; PLAN-195 adds one bounded, additive
   scanner of shell command positions and nested shell bodies.
4. Applies three rules per subcommand:
   - `rm` with both `-r` and `-f` (catches `-rf`, `-fr`, `-Rf`, `-r -f`)
   - `git reset --hard` (exact first 3 tokens)
   - `git push --force` or `git push -f` — but NOT `--force-with-lease`
5. Any match → block with a concrete remediation; infrastructure errors
   still fail-open.

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
# These declarations remain part of the Bash-safety policy. The hook facade
# loads them from this installable library module and preserves their public
# and private names for callers and tests.


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
try:
    from _lib import runtime_paths as _rp  # noqa: E402  # PLAN-182 W1 single resolver
except Exception:  # pragma: no cover — partial upgrade: hook stays FAIL-OPEN (rail r1 P1-4)
    _rp = None  # type: ignore[assignment]


def _rp_state_dir():
    """Resolver com fallback de partial-upgrade (arquivo novo ausente).

    Fail-open: o hook NUNCA crasha por falta do resolvedor; degrada ao
    comportamento legado com aviso em stderr.
    """
    if _rp is not None:
        return _rp.runtime_state_dir()
    import sys as _s
    _s.stderr.write("# hook: _lib/runtime_paths ausente — fallback legado (partial upgrade)\n")
    from pathlib import Path as _P
    import os as _o
    _h = _o.environ.get("HOME") or str(_P.home())
    return _P(_h) / ".claude" / "projects" / "ceo-orchestration"  # rp-allow: partial-upgrade-fallback

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
    # Destructive-command class, including PLAN-195's indirect forms. Citation
    # gating uses the tag, never reason-string matching.
    destructive: bool = False
    reason_code: Optional[str] = None
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
