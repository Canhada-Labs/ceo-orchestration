#!/usr/bin/env python3
"""Governance Hook: parallel-writer worktree-isolation enforcement (PLAN-125 WS-2).

Registered in `.claude/settings.json` under `hooks.PreToolUse` with matcher
`Bash|Edit|Write|MultiEdit`. Runs via the `_python-hook.sh` shim. Enforces the
ADR-049a AMEND-1 rule:

    When parallel-writer mode is ACTIVE (the writer self-sets the opt-in env),
    a background/parallel writer NEVER operates on the shared main checkout —
    every write MUST land inside the writer's assigned dedicated worktree, else
    it is DENIED (fail-CLOSED).

## Scope frame (MF-4 — anti-vanity, BINDING)

This is **infrastructure for non-conflicting parallel reads/reviews** (fan-out
reviewers — the pattern we already use). PLAN-123 E2 closed the speed thesis
(S201). This hook makes, and asserts, **NO throughput / speed claim.** It exists
to stop the *accidental* S191 worktree-bleed (a background agent's worktree/rsync
wrote AND reverted canonical files in the shared main checkout — see
`feedback_background_agent_worktree_bleeds_into_main_checkout.md`).

## Activation contract (default-OFF — MF-SEC-6)

The hook is **INERT** unless the writer self-identifies via two env vars it sets
in its own process environment:

- `CEO_PARALLEL_WRITER=1`         — declares "I am a parallel/background writer."
- `CEO_ASSIGNED_WORKTREE=<abs>`   — the dedicated worktree slot it `acquire()`d
                                    from `_worktree_pool` (an absolute path).

The owner / normal session simply never sets `CEO_PARALLEL_WRITER`, so the rule
is inert for it (one env lookup → allow). This is the same already-validated
idiom S191's fix used (`CEO_WS3_APPLY_OK=1`, set only by the ceremony). The hook
does NOT try to *detect* background-ness from the process tree (that would need
IPC / a daemon — MF-FIN-4 verdict: FEASIBLE with neither); the writer announces
itself.

## Decision (when ACTIVE — UNCONDITIONAL + fail-CLOSED)

1. If `CEO_ASSIGNED_WORKTREE` is unset/empty → DENY all writes (a parallel
   writer with no assigned slot must not write anywhere).
2. Resolve the write's effective target path(s) at the PreToolUse decision
   point — NO TOCTOU (MF-SEC-6): we resolve cwd from the hook process's own
   `os.getcwd()` (the writer's real cwd at invocation — the stdin payload
   carries no `cwd` field) and parse any later `cd` / `git -C` out of a Bash
   command rather than trusting the process cwd alone.
3. DENY (fail-CLOSED) iff any resolved target is inside the shared main checkout
   (`CLAUDE_PROJECT_DIR` / repo root) and NOT inside the assigned worktree.
4. For Bash, any command we cannot parse confidently, or that uses an
   indirection we cannot follow (`bash -c`, `eval`, `xargs`, `find -exec`,
   interpreter `-c` bodies) → DENY (fail-CLOSED while active).

## Argv-git discipline (MF-SEC-7)

argv-array git (the substrate already does this — `_worktree_pool._run_git`)
closes *shell* injection but NOT *option* injection: a ref/path beginning with
`-` is still parsed as a git flag. Any attacker-influenceable ref/path the hook
validates MUST be preceded by a `--` end-of-options separator AND pass an
allowlist regex `^[A-Za-z0-9._/-]+$` (reject a leading `-`, reject `..`). See
`require_end_of_options` / `is_safe_ref_path`.

## Known residual (cooperative-model boundary — Codex pair-rail R3)

This hook detects writes into the main checkout via RECOGNIZED shapes: shell
redirects (`>`/`>>`/`tee`/`dd`/`sed -i`), the common file mutators
(`cp`/`mv`/`rsync`/`install`/`ln`/`touch`/`mkdir`/`rmdir`/`rm`, incl.
`-t`/`--target-directory`), `git` write subcommands, and a `cd`/`git -C` that
retargets into main. `$VAR`/`~` are expanded from the resolved env first, and a
residual `$`/backtick fails CLOSED. It does NOT decode the write semantics of an
ARBITRARY unknown program — e.g. `python build.py --out "$CLAUDE_PROJECT_DIR/x"`
writes into main via a flag the hook cannot know is a destination. Statically
distinguishing a write-arg from a read-arg for an arbitrary command is not
possible, and denying every main-referencing arg would also break legitimate
READS from main (reads are not the bleed). This residual is the boundary of the
COOPERATIVE / accidental-bleed model: the stronger guarantee (a writer that
physically cannot touch main — read-only bind-mount / separate FS namespace) is
ADR-049b, deliberately out of scope here.

## Fail-direction contract

- Fail-CLOSED on the actual writer-in-main-checkout condition (the safety
  surface) and on unparseable Bash while active.
- Fail-OPEN ONLY on an infra/parse error of the HOOK ITSELF (a bug in this hook
  must NEVER block the user session — same doctrine as every other governance
  hook). On any unexpected exception in `main()`, allow + log breadcrumb.

## Output contract

Writes a single-line JSON decision to stdout via the Adapter Layer:

    {}                                       (allow)
    {"decision":"block","reason":"BLOCKED: ..."}

Exit code is 0 in both cases — Claude Code reads the decision from stdout.

Stdlib-only, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import os
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

# Make the _lib package importable — hooks live in .claude/hooks/ and
# _lib is a sibling package.
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import contract as _contract  # noqa: E402
from _lib.adapters import claude as _claude_adapter  # noqa: E402


# ---------------------------------------------------------------------------
# Activation contract (MF-SEC-6)
# ---------------------------------------------------------------------------

PARALLEL_WRITER_ENV = "CEO_PARALLEL_WRITER"
ASSIGNED_WORKTREE_ENV = "CEO_ASSIGNED_WORKTREE"

# Write-capable tools this hook governs. `Read`/`Glob`/`Grep` etc. are
# non-mutating and never reach this hook (matcher is narrowed in settings.json
# to the write set), but we re-assert here defensively.
_WRITE_TOOLS = frozenset({"Edit", "Write", "MultiEdit"})


def is_active(env: Optional[dict] = None) -> bool:
    """True iff parallel-writer mode is active (opt-in env set to "1")."""
    src = env if env is not None else os.environ
    return (src.get(PARALLEL_WRITER_ENV) or "").strip() == "1"


# ---------------------------------------------------------------------------
# Argv-git discipline (MF-SEC-7)
# ---------------------------------------------------------------------------

# Allowlist for attacker-influenceable git refs/paths: alnum + dot/slash/dash/
# underscore only. A leading `-` is rejected (option injection) and `..` is
# rejected (path traversal) by the explicit guards in `is_safe_ref_path`.
_REF_PATH_ALLOWLIST_RE = re.compile(r"^[A-Za-z0-9._/-]+$")


def is_safe_ref_path(value: str) -> bool:
    """True iff `value` is a safe git ref/path (MF-SEC-7).

    Rejects: empty, a leading ``-`` (option injection), any ``..`` segment
    (path traversal), and anything outside the allowlist regex. Pure function.
    """
    if not value:
        return False
    if value.startswith("-"):
        return False
    if ".." in value:
        return False
    return bool(_REF_PATH_ALLOWLIST_RE.match(value))


def require_end_of_options(argv: List[str]) -> bool:
    """True iff a `--` end-of-options separator is present in `argv`.

    The substrate's git invocations must place attacker-influenceable refs/paths
    AFTER a ``--`` so git never parses a leading-dash value as a flag (MF-SEC-7).
    A helper for the AMEND-1 contract + the WS-2 tests; the hook's Bash branch
    treats a git write-shape lacking ``--`` before a dash-leading token as
    fail-CLOSED.
    """
    return "--" in argv


# ---------------------------------------------------------------------------
# Path containment (MF-SEC-6 — resolve at the decision point, no TOCTOU)
# ---------------------------------------------------------------------------


# Shell variable references we can expand from the resolved env (the common
# cooperative pattern `cd "$CLAUDE_PROJECT_DIR"` / `rsync … "$CLAUDE_PROJECT_DIR/"`
# — Codex pair-rail P0). Anything still carrying a `$` / backtick AFTER expansion
# is an unresolved var / command substitution → unresolvable → fail-CLOSED.
_SHELL_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")


def _expand_token(token: str, env: dict) -> str:
    """Expand ``$VAR`` / ``${VAR}`` (from `env`) and a leading ``~`` in `token`.

    Unknown vars are left literal so their residual ``$`` makes the token
    fail-CLOSED at resolution (we must never silently treat an unresolved var
    as a benign relative path). Pure function.
    """
    def _repl(m: "re.Match") -> str:
        name = m.group(1) or m.group(2)
        return env.get(name, m.group(0))

    out = _SHELL_VAR_RE.sub(_repl, token)
    if out == "~":
        out = env.get("HOME") or out
    elif out.startswith("~/"):
        home = env.get("HOME") or ""
        if home:
            out = home + out[1:]
    return out


def _resolve(
    path_str: str, base_cwd: Path, env: Optional[dict] = None
) -> Optional[Path]:
    """Resolve `path_str` against `base_cwd`, collapsing `..`/symlinks.

    Expands known ``$VAR`` / ``~`` from `env` FIRST (MF-SEC-6 / Codex P0: a
    `cd "$CLAUDE_PROJECT_DIR"` or a redirect into `"$CLAUDE_PROJECT_DIR/f"` must
    resolve to the real main checkout, not the literal token). Returns the
    resolved absolute Path, or None if it cannot be resolved — including when an
    unresolved shell var / command substitution (`$` / backtick) remains after
    expansion (treated as fail-CLOSED by the caller while active). Mirrors the
    `check_canonical_edit._is_canonical` resolution idiom.
    """
    src = env if env is not None else os.environ
    s = path_str.strip()
    # Strip one layer of surrounding quotes (the redirect regex can keep them;
    # shlex already removes quotes from argv tokens).
    if len(s) >= 2 and s[0] in "\"'" and s[-1] == s[0]:
        s = s[1:-1]
    expanded = _expand_token(s, dict(src))
    if "$" in expanded or "`" in expanded:
        # Unresolved var / command substitution → cannot prove containment.
        return None
    try:
        p = Path(expanded)
        if not p.is_absolute():
            p = base_cwd / p
        return p.resolve()
    except (ValueError, OSError, RuntimeError):
        return None


def _is_inside(child: Path, parent: Path) -> bool:
    """True iff `child` is `parent` or is nested under it (resolved)."""
    try:
        child_r = child.resolve()
        parent_r = parent.resolve()
    except (OSError, RuntimeError):
        return False
    if child_r == parent_r:
        return True
    try:
        child_r.relative_to(parent_r)
        return True
    except ValueError:
        return False


def violates_boundary(
    target: Path, main_checkout: Path, assigned_worktree: Path
) -> bool:
    """True iff `target` is inside the shared main checkout and NOT inside the
    assigned worktree → a boundary violation (DENY, fail-CLOSED).

    A write that lands inside the assigned worktree is allowed even if the
    worktree itself happens to be nested under the main checkout path: the
    explicit assigned-worktree containment takes precedence. (Pool slots live
    under ``<repo>/.claude/swarm-worktrees/loop-<i>`` — a sibling subtree — so
    the precedence is what keeps a legitimate slot write from being denied.)
    """
    if _is_inside(target, assigned_worktree):
        return False
    return _is_inside(target, main_checkout)


# ---------------------------------------------------------------------------
# Bash command analysis (MF-SEC-6 — defeat a later cd / git -C, no TOCTOU)
# ---------------------------------------------------------------------------

# Indirections we cannot statically follow → fail-CLOSED while active.
_OPAQUE_TOKENS = frozenset({"eval", "xargs", "source", "."})
# Interpreters whose `-c <body>` runs an opaque inline program.
_INLINE_INTERPRETERS = frozenset({
    "bash", "sh", "zsh", "dash", "ksh",
    "python", "python3", "perl", "ruby", "node",
})

# Bash write-shape operators / commands that produce a filesystem mutation
# whose target path we must containment-check.
_WRITE_REDIRECTS = (">", ">>")

# File-mutating commands where only the DESTINATION (last non-flag token) is a
# write target — a source argument inside the main checkout is a legal read.
_DEST_LAST_WRITERS = frozenset({"cp", "mv", "rsync", "install", "ln"})
# File-mutating commands where EVERY non-flag token is a write/delete target.
_ALL_ARG_WRITERS = frozenset({"touch", "mkdir", "rmdir", "rm", "unlink"})


@dataclass
class BashVerdict:
    """Result of analysing a Bash command under active parallel-writer mode."""

    deny: bool
    reason: Optional[str] = None


def _split_subcommands(command: str) -> List[str]:
    """Split on top-level shell control operators (&&, ||, ;, |).

    Naive (quote-blind) split mirroring `check_bash_safety._SUBCOMMAND_SPLIT_RE`;
    over-split chunks fail `shlex.split` and are handled fail-CLOSED upstream.
    """
    return [c for c in re.split(r"\s*(?:&&|\|\||[;|])\s*", command) if c.strip()]


def analyze_bash(
    command: str, main_checkout: Path, base_cwd: Path, assigned_worktree: Path,
    env: Optional[dict] = None,
) -> BashVerdict:
    """Analyse a Bash command for a write that lands in the shared main checkout.

    Fail-CLOSED (deny) while parallel-writer mode is active on:
      * an unparseable command (unbalanced quotes etc.);
      * an opaque indirection we cannot follow (`eval`, `xargs`, interpreter
        `-c <body>`, `bash -c`, etc.);
      * a resolved write target / `cd` / `git -C` path that is inside the main
        checkout and outside the assigned worktree;
      * a git write-shape carrying an attacker-influenceable ref/path that
        fails the `--` + allowlist discipline (MF-SEC-7).

    The `cd` tracking is the TOCTOU defense (MF-SEC-6): a command like
    `cd /shared/main && echo x > f` is denied because the `cd` moves the
    effective cwd into the main checkout BEFORE the write resolves.
    """
    if not command.strip():
        return BashVerdict(deny=False)

    effective_cwd = base_cwd
    for sub in _split_subcommands(command):
        try:
            tokens = shlex.split(sub)
        except ValueError:
            # Unbalanced quotes / unparseable → fail-CLOSED while active.
            return BashVerdict(
                deny=True,
                reason=("unparseable Bash subcommand while parallel-writer "
                        "mode active"),
            )
        if not tokens:
            continue

        head = Path(tokens[0]).name or tokens[0]

        # Opaque indirection we cannot statically follow → fail-CLOSED.
        if head in _OPAQUE_TOKENS:
            return BashVerdict(
                deny=True,
                reason=(f"opaque indirection '{head}' cannot be verified while "
                        "parallel-writer mode active"),
            )
        if head in _INLINE_INTERPRETERS and "-c" in tokens:
            return BashVerdict(
                deny=True,
                reason=(f"interpreter '{head} -c <body>' inline program cannot "
                        "be verified while parallel-writer mode active"),
            )

        # Track `cd <dir>` / `pushd <dir>` — moves the effective cwd (TOCTOU).
        if head in ("cd", "pushd") and len(tokens) >= 2 and not tokens[1].startswith("-"):
            moved = _resolve(tokens[1], effective_cwd, env)
            if moved is None:
                return BashVerdict(
                    deny=True,
                    reason="unresolvable 'cd' target while parallel-writer mode active",
                )
            effective_cwd = moved
            # A cd INTO the main checkout (outside the slot) is itself a setup
            # for a bleed write — deny eagerly (fail-CLOSED).
            if violates_boundary(moved, main_checkout, assigned_worktree):
                return BashVerdict(
                    deny=True,
                    reason=(f"'cd' into shared main checkout ({moved}) while a "
                            "parallel writer is assigned a dedicated worktree"),
                )

        # git -C <path> / --git-dir / --work-tree retargets the tree (TOCTOU).
        if head == "git":
            verdict = _check_git_subcommand(
                tokens, main_checkout, effective_cwd, assigned_worktree, env
            )
            if verdict.deny:
                return verdict

        # Redirection write-shape: `> path` / `>> path`, `tee path`,
        # `sed -i ... path`, `dd of=path`.
        verdict = _check_write_targets(
            tokens, sub, main_checkout, effective_cwd, assigned_worktree, env
        )
        if verdict.deny:
            return verdict

    return BashVerdict(deny=False)


def _check_git_subcommand(
    tokens: List[str], main_checkout: Path, cwd: Path, assigned_worktree: Path,
    env: Optional[dict] = None,
) -> BashVerdict:
    """Validate a `git ...` invocation's retarget flags + ref/path discipline."""
    i = 1
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        # `git -C <path>` retargets the working dir.
        if tok == "-C" and i + 1 < n:
            retargeted = _resolve(tokens[i + 1], cwd, env)
            if retargeted is None or violates_boundary(
                retargeted, main_checkout, assigned_worktree
            ):
                return BashVerdict(
                    deny=True,
                    reason=("'git -C' retargets the shared main checkout while a "
                            "parallel writer is assigned a dedicated worktree"),
                )
            i += 2
            continue
        # `--git-dir=`/`--work-tree=` (and space-separated forms) retarget too.
        for flag in ("--git-dir", "--work-tree"):
            val = None
            if tok == flag and i + 1 < n:
                val = tokens[i + 1]
            elif tok.startswith(flag + "="):
                val = tok.split("=", 1)[1]
            if val is not None:
                retargeted = _resolve(val, cwd, env)
                if retargeted is None or violates_boundary(
                    retargeted, main_checkout, assigned_worktree
                ):
                    return BashVerdict(
                        deny=True,
                        reason=(f"'git {flag}' retargets the shared main checkout "
                                "while a parallel writer is assigned a worktree"),
                    )
        i += 1

    # MF-SEC-7 ref/path discipline — scoped to WRITE subcommands only (Codex R3
    # P1): a read-only subcommand (grep/log/diff/show/…) takes a pattern /
    # pathspec that cannot escape the worktree as a WRITE, so applying the strict
    # allowlist there falsely denies e.g. `git grep -- 'TODO item'`.
    if _git_subcommand(tokens) in _GIT_WRITE_SUBCMDS:
        # Any dash-leading ref/path argument must be protected by a `--`
        # end-of-options separator (option injection).
        if not require_end_of_options(tokens):
            for tok in tokens[1:]:
                if tok.startswith("-") and not _looks_like_git_flag(tok):
                    return BashVerdict(
                        deny=True,
                        reason=("git ref/path with a leading '-' must follow a "
                                "'--' end-of-options separator (MF-SEC-7 option "
                                "injection)"),
                    )
        # Tokens AFTER a `--` separator are unambiguously attacker-influenceable
        # refs/paths (never a flag value), so they MUST pass the allowlist regex
        # `^[A-Za-z0-9._/-]+$` (also rejects a leading '-' and any '..').
        if "--" in tokens:
            sep = tokens.index("--")
            for tok in tokens[sep + 1:]:
                if not is_safe_ref_path(tok):
                    return BashVerdict(
                        deny=True,
                        reason=("git ref/path after '--' fails the MF-SEC-7 "
                                "allowlist (leading '-', '..', or out-of-allowlist "
                                "character) while parallel-writer mode active"),
                    )
        # A `..` traversal anywhere else (no `--`, or a pre-`--` pathspec) is
        # also unsafe — reject it (the containment check covers absolute escapes;
        # this closes a relative `..` escape that resolves outside the slot).
        for tok in tokens[1:]:
            if tok == "--" or tok.startswith("-"):
                continue
            if ".." in tok:
                return BashVerdict(
                    deny=True,
                    reason=("git ref/path contains a '..' traversal segment "
                            "(MF-SEC-7) while parallel-writer mode active"),
                )
    return BashVerdict(deny=False)


# git global options that consume a following value token (skipped when
# locating the subcommand verb).
_GIT_GLOBAL_OPTS_WITH_VALUE = frozenset({
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
})
# git subcommands that WRITE / mutate refs or the working tree. The MF-SEC-7
# ref/path discipline (require `--`, post-`--` allowlist, `..` reject) is scoped
# to these: a read-only subcommand (grep/log/diff/show/…) takes a
# pattern/pathspec that cannot escape the worktree as a WRITE, so applying the
# strict allowlist there is a false positive (e.g. `git grep -- 'TODO item'`).
_GIT_WRITE_SUBCMDS = frozenset({
    "checkout", "switch", "restore", "add", "rm", "mv", "reset", "clean",
    "apply", "stash", "commit", "merge", "rebase", "cherry-pick", "revert",
    "am", "pull", "fetch", "clone", "init", "worktree", "push", "branch", "tag",
})


def _git_subcommand(tokens: List[str]) -> str:
    """Return the git subcommand verb, skipping global options. '' if none."""
    i = 1
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok in _GIT_GLOBAL_OPTS_WITH_VALUE:
            i += 2
            continue
        if tok.startswith("-"):
            i += 1
            continue
        return tok
    return ""


def _looks_like_git_flag(tok: str) -> bool:
    """Heuristic: a conventional git option needing no `--` guard.

    Accepts ONLY a single-char short flag (``-x``, optionally bundled like
    ``-xv``) or a proper long option (``--name`` / ``--name=val``). It
    deliberately REJECTS a single-dash *multi-letter* token (``-evilref``):
    that shape is not a standard git option and is exactly the
    attacker-influenceable ref/path MF-SEC-7 requires a ``--`` separator for.
    Used only to distinguish a genuine flag from such a smuggled ref/path.
    """
    if tok.startswith("--"):
        return bool(re.match(r"^--[A-Za-z][A-Za-z0-9-]*(=.*)?$", tok))
    # Single-dash: only short flags (one letter, optionally bundled short
    # flags). `-evilref` looks like a bundle but conventional short flags are
    # rare beyond a few letters; require ALL chars to be letters AND treat any
    # token longer than a small bundle as a smuggled ref → needs `--`.
    return bool(re.match(r"^-[A-Za-z]{1,3}$", tok))


def _extract_target_dir_option(tokens: List[str]) -> Optional[str]:
    """Return the destination from a `-t DIR` / `--target-directory[=]DIR`
    option (cp/mv/install encode the destination there, evading the last-token
    rule — Codex pair-rail P1). None if absent.
    """
    i = 1
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok in ("-t", "--target-directory") and i + 1 < n:
            return tokens[i + 1]
        if tok.startswith("--target-directory="):
            return tok.split("=", 1)[1]
        # bundled short form `-t/dst` / `-tDIR`
        if tok.startswith("-t") and not tok.startswith("--") and len(tok) > 2:
            return tok[2:]
        i += 1
    return None


def _check_write_targets(
    tokens: List[str], raw_sub: str, main_checkout: Path, cwd: Path,
    assigned_worktree: Path, env: Optional[dict] = None,
) -> BashVerdict:
    """Resolve concrete write targets in a subcommand + containment-check them.

    Recognizes: ``>``/``>>`` redirects, ``tee <path>``, ``sed -i ... <path>``,
    ``dd of=<path>``. Any target resolving into the shared main checkout (and
    outside the assigned worktree) → DENY.
    """
    targets: List[str] = []

    # Redirections: scan the RAW subcommand string for `>`/`>>` then the next
    # token. shlex strips the operator, so use a light regex on the raw text.
    for m in re.finditer(r">>?\s*([^\s;|&<>]+)", raw_sub):
        targets.append(m.group(1))

    head = Path(tokens[0]).name or tokens[0]
    if head == "tee":
        for tok in tokens[1:]:
            if not tok.startswith("-"):
                targets.append(tok)
    elif head == "dd":
        for tok in tokens:
            if tok.startswith("of="):
                targets.append(tok.split("=", 1)[1])
    elif head == "sed" and any(t == "-i" or t.startswith("-i") for t in tokens[1:]):
        # sed -i edits its file argument(s) in place — the last non-flag tokens.
        for tok in tokens[1:]:
            if not tok.startswith("-") and tok != "-i":
                # The expression itself is a non-flag token too; we cannot
                # cheaply distinguish it, so we resolve every candidate and let
                # containment decide (a sed expression rarely resolves into the
                # repo). Conservative: include it.
                targets.append(tok)
    # Common file-mutating commands whose explicit destination/target args are
    # the realistic ACCIDENTAL-bleed shape (the S191 vector was an rsync INTO
    # the shared main checkout — Codex pair-rail P0). For cp/mv/rsync/install/ln
    # only the DESTINATION (last non-flag token) is a write: a SOURCE inside the
    # main checkout is a legal READ and must NOT be denied. For
    # touch/mkdir/rmdir/rm/unlink every non-flag token is a target.
    # (Cooperative threat model — ADR-049a §scope: a malicious writer using
    # computed / obfuscated destination paths is ADR-049b, out of scope; an
    # unrecognized command run from inside the worktree writes relative to its
    # cwd, which the cd/effective-cwd tracking already keeps inside the slot.)
    elif head in _DEST_LAST_WRITERS:
        tdir = _extract_target_dir_option(tokens)
        if tdir is not None:
            # `-t DIR`/`--target-directory=DIR`: the option IS the destination;
            # all positional args are sources (legal reads).
            targets.append(tdir)
        else:
            non_flag = [t for t in tokens[1:] if not t.startswith("-")]
            if non_flag:
                targets.append(non_flag[-1])  # destination is the last positional
    elif head in _ALL_ARG_WRITERS:
        for tok in tokens[1:]:
            if not tok.startswith("-"):
                targets.append(tok)

    for t in targets:
        resolved = _resolve(t, cwd, env)
        if resolved is None:
            # Cannot resolve a concrete write target while active → fail-CLOSED.
            return BashVerdict(
                deny=True,
                reason=("unresolvable write target while parallel-writer mode "
                        "active"),
            )
        if violates_boundary(resolved, main_checkout, assigned_worktree):
            return BashVerdict(
                deny=True,
                reason=(f"write target inside the shared main checkout ({resolved}) "
                        "— a parallel writer must write inside its assigned "
                        "worktree (ADR-049a AMEND-1)"),
            )
    return BashVerdict(deny=False)


# ---------------------------------------------------------------------------
# Decision (shared by Edit/Write/MultiEdit + Bash branches)
# ---------------------------------------------------------------------------


def decide(
    event: "_contract.NormalizedEvent",
    *,
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
) -> _contract.Decision:
    """Return the allow/block Decision for a write event under WS-2.

    Pure-ish: `cwd` defaults to `os.getcwd()` and `env`/`CLAUDE_PROJECT_DIR`
    default to the process env (injectable for tests). The hook is INERT (allow)
    unless parallel-writer mode is active.
    """
    src = env if env is not None else os.environ

    # Default-OFF (MF-SEC-6): inert unless the writer self-identifies.
    if not is_active(src):
        return _contract.allow()

    # ACTIVE — UNCONDITIONAL + fail-CLOSED from here.
    assigned_raw = (src.get(ASSIGNED_WORKTREE_ENV) or "").strip()
    if not assigned_raw:
        # A parallel writer with no assigned slot must not write anywhere.
        return _contract.block(
            "BLOCKED: parallel-writer mode active but no CEO_ASSIGNED_WORKTREE "
            "is set — a parallel writer must operate inside a dedicated worktree "
            "(ADR-049a AMEND-1). Set CEO_ASSIGNED_WORKTREE to the acquired pool "
            "slot, or unset CEO_PARALLEL_WRITER for the owner session."
        )

    base_cwd = cwd if cwd is not None else Path(os.getcwd())
    main_checkout = Path(src.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    assigned_worktree = Path(assigned_raw)

    # P1 (Codex pair-rail): the assigned worktree MUST be a real dedicated slot
    # — distinct from, and not a parent/ancestor of, the shared main checkout.
    # Otherwise the assigned-worktree containment precedence in
    # violates_boundary() would neutralize the boundary entirely (every
    # main-checkout write would look "inside the slot"). Fail-CLOSED on a bad /
    # missing-distinctness assignment while active.
    if _is_inside(main_checkout, assigned_worktree):
        return _contract.block(
            "BLOCKED: CEO_ASSIGNED_WORKTREE must be a dedicated worktree "
            "distinct from (and not a parent of) the shared main checkout — the "
            "current assignment equals or contains the main checkout, which "
            "would void the isolation boundary (ADR-049a AMEND-1, fail-CLOSED)."
        )

    tool = event.tool_name or ""

    if tool in _WRITE_TOOLS:
        file_path = event.file_path or str(
            (event.tool_input or {}).get("file_path") or ""
        )
        if not file_path:
            # A write tool with no resolvable target while active → fail-CLOSED.
            return _contract.block(
                "BLOCKED: parallel-writer write with no resolvable file_path "
                "while parallel-writer mode active (ADR-049a AMEND-1)."
            )
        resolved = _resolve(file_path, base_cwd, src)
        if resolved is None:
            return _contract.block(
                "BLOCKED: unresolvable write path while parallel-writer mode "
                "active (ADR-049a AMEND-1)."
            )
        if violates_boundary(resolved, main_checkout, assigned_worktree):
            return _contract.block(
                f"BLOCKED: {tool} target '{resolved}' is inside the shared main "
                "checkout — a parallel writer must write inside its assigned "
                f"worktree '{assigned_worktree}' (ADR-049a AMEND-1, S191 bleed "
                "regression)."
            )
        return _contract.allow()

    if tool == "Bash":
        command = event.command or str((event.tool_input or {}).get("command") or "")
        verdict = analyze_bash(command, main_checkout, base_cwd, assigned_worktree, src)
        if verdict.deny:
            return _contract.block(
                f"BLOCKED: {verdict.reason} (ADR-049a AMEND-1, S191 bleed "
                "regression)."
            )
        return _contract.allow()

    # A tool outside the write set (should not reach here given the matcher) →
    # allow; this hook governs writes only.
    return _contract.allow()


def main() -> int:
    """Hook entry point: read stdin via Adapter Layer, decide, write stdout.

    Fail-OPEN on any infra/parse error of the hook itself (a hook bug must NEVER
    block the user session); fail-CLOSED on the actual writer-in-main-checkout
    condition inside :func:`decide`.
    """
    try:
        event = _claude_adapter.read_event(phase="PreToolUse")
        if event.parse_error:
            print(
                f"[check_worktree_writer] WARN: stdin parse error: "
                f"{event.parse_error}",
                file=sys.stderr,
            )
            # P1 (Codex pair-rail): while parallel-writer mode is ACTIVE a parse
            # error means we cannot prove the write lands inside the assigned
            # worktree → fail-CLOSED (block). For the owner/inert session a hook
            # parse issue must never block (fail-OPEN doctrine).
            if is_active():
                _claude_adapter.emit_decision(_contract.block(
                    "BLOCKED: stdin parse error while parallel-writer mode active "
                    "— cannot prove the write target is inside the assigned "
                    "worktree (fail-CLOSED, ADR-049a AMEND-1)."
                ))
                return 0
            _claude_adapter.emit_decision(_contract.allow())
            return 0
        decision = decide(event)
        _claude_adapter.emit_decision(decision)
        return 0
    except Exception as e:  # pragma: no cover — fail-open on hook bug
        print(
            f"[check_worktree_writer] FATAL: {e.__class__.__name__}: {e}",
            file=sys.stderr,
        )
        _claude_adapter.emit_decision(_contract.allow())
        return 0


if __name__ == "__main__":
    sys.exit(main())
