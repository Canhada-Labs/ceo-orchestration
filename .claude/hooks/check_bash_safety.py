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
    # Drop leading privilege prefixes (sudo/doas/nocorrect) and any flags
    # that belong to them.
    while working and working[0] in _PRIVILEGE_PREFIXES:
        working.pop(0)
        # Consume prefix-owned flags: any -flag until we hit a non-flag
        # or run out. For value-taking flags (-u USER / --user=USER),
        # also pop the following non-flag value token.
        while working and working[0].startswith("-"):
            flag = working.pop(0)
            if (flag in ("-u", "--user")
                    and working
                    and not working[0].startswith("-")):
                working.pop(0)  # consume USER arg
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
from _lib.adapters import claude as _claude_adapter  # noqa: E402

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
# which fail to tokenize cleanly under shlex → skipped. Fail-safe.
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


def _tokenize(subcommand: str) -> List[str]:
    """shlex.split with fail-safe: returns [] on parse error.

    Unbalanced quotes, etc. produce an empty token list so the caller
    skips the chunk — fail-safe, not fail-open, because a chunk we
    cannot parse also cannot match a block rule.
    """
    try:
        return shlex.split(subcommand)
    except ValueError:
        return []


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
                return Decision(allow=False, reason=reason)

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


def main() -> int:
    """Hook entry point: read stdin via Adapter Layer, decide, write stdout, exit 0.

    PLAN-006 Phase 1 migration (ADR-014). Uses `claude_adapter.read_event()`
    / `emit_decision()` instead of direct `_lib.payload` + `print()`.
    Output is byte-identical to pre-migration (test_hook_byte_fidelity).
    """
    try:
        event = _claude_adapter.read_event(phase="PreToolUse")
        if event.parse_error:
            print(
                f"[check_bash_safety] WARN: stdin parse error: {event.parse_error}",
                file=sys.stderr,
            )
            _claude_adapter.emit_decision(_contract.allow())
            return 0

        command = event.command or ""
        if not command and isinstance(event.tool_input, dict):
            command = str(event.tool_input.get("command") or "")

        decision = decide_command(command)
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
        _claude_adapter.emit_decision(
            _to_contract_decision(decision, event.tool_input)
        )
        return 0
    except Exception as e:  # pragma: no cover
        print(
            f"[check_bash_safety] FATAL: {e.__class__.__name__}: {e}",
            file=sys.stderr,
        )
        _claude_adapter.emit_decision(_contract.allow())
        return 0


if __name__ == "__main__":
    sys.exit(main())
