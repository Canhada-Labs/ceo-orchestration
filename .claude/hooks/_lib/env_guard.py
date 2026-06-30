#!/usr/bin/env python3
"""Linker/loader/runtime env-hijack denylist (PLAN-133 A1).

A from-scratch stdlib re-implementation of the Goose ``Envs::DISALLOWED_KEYS``
*mechanism* (rite §2 — nothing fetched/run from the aaif-goose fork). A Bash
command that SETS any of these 31 environment variables can hijack the dynamic
linker (``LD_PRELOAD`` / ``DYLD_INSERT_LIBRARIES``), a language runtime's preload
hook (``PYTHONSTARTUP`` / ``NODE_OPTIONS`` / ``BASH_ENV`` / ``PERL5OPT`` …), or
the loader search path — loading attacker code into an otherwise-trusted process.

This module ONLY DETECTS. It returns a closed-enum ``hijack_class`` + an
operator-facing reason that NEVER interpolates the assigned value (the value is
the live-credential / payload surface; see ``env_var_hijack_blocked`` no-value-echo
property test). ``check_bash_safety.decide_command`` consumes the scan and BLOCKS.

Detection surface (3 set-shapes per simple command, chaining-safe):
  1. assignment PREFIX:  ``LD_PRELOAD=/evil.so make``        (env-prefix on a cmd)
  2. ``export`` /``declare``/``typeset``/``local`` NAME=val   (exported into the env)
  3. ``env NAME=val cmd``                                     (env(1) wrapper)
A bare reference (``echo $LD_PRELOAD``) is NOT a set and is allowed.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from typing import List, Optional


# ---------------------------------------------------------------------------
# The 31-key denylist. Re-implemented from first principles (security knowledge),
# grouped by hijack family. Membership is the contract; the grouping is doc-only.
# CASE-SENSITIVE: POSIX env var names are case-sensitive and every key below is
# canonical upper-case; a lower-case homonym is not the loader-honored variable.
# ---------------------------------------------------------------------------
DISALLOWED_ENV_KEYS = frozenset({
    # --- GNU/Linux dynamic linker (ld.so) — 12 ---
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "LD_AUDIT",
    "LD_PROFILE",
    "LD_DEBUG",
    "LD_DEBUG_OUTPUT",
    "LD_ORIGIN_PATH",
    "LD_CONFIG",
    "LD_BIND_NOW",
    "LD_DYNAMIC_WEAK",
    "LD_ASSUME_KERNEL",
    "LD_SHOW_AUXV",
    # --- macOS dyld — 9 ---
    "DYLD_INSERT_LIBRARIES",
    "DYLD_LIBRARY_PATH",
    "DYLD_FRAMEWORK_PATH",
    "DYLD_FALLBACK_LIBRARY_PATH",
    "DYLD_FALLBACK_FRAMEWORK_PATH",
    "DYLD_PRINT_TO_FILE",
    "DYLD_IMAGE_SUFFIX",
    "DYLD_VERSIONED_LIBRARY_PATH",
    "DYLD_ROOT_PATH",
    # --- language-runtime / loader preload hooks — 10 ---
    "PYTHONSTARTUP",
    "PYTHONPATH",
    "PYTHONINSPECT",
    "PERL5OPT",
    "PERL5LIB",
    "RUBYOPT",
    "RUBYLIB",
    "NODE_OPTIONS",
    "BASH_ENV",
    "ENV",  # POSIX sh startup-file hijack
})

# Closed-enum hijack_class tokens. Mirrored as a literal frozenset in
# _lib/audit_emit.py (_ENV_VAR_HIJACK_CLASSES) so audit_emit has no import-time
# dependency on this module; a drift between the two is caught by a dedicated
# test (the two frozensets MUST be equal). A value outside this set is coerced
# to "parse_failure" before emit (defense-in-depth).
HIJACK_CLASS_LINKER_PRELOAD = "linker_preload"      # LD_PRELOAD / DYLD_INSERT_LIBRARIES
HIJACK_CLASS_LINKER_PATH = "linker_path"            # LD_LIBRARY_PATH / DYLD_*_PATH / *LIB
HIJACK_CLASS_RUNTIME_HOOK = "runtime_hook"          # PYTHONSTARTUP/NODE_OPTIONS/BASH_ENV/ENV/…
HIJACK_CLASS_LINKER_OTHER = "linker_other"          # remaining LD_*/DYLD_* diagnostics/tuning
HIJACK_CLASS_PARSE_FAILURE = "parse_failure"        # unparseable command → fail-CLOSED block

ENV_VAR_HIJACK_CLASSES = frozenset({
    HIJACK_CLASS_LINKER_PRELOAD,
    HIJACK_CLASS_LINKER_PATH,
    HIJACK_CLASS_RUNTIME_HOOK,
    HIJACK_CLASS_LINKER_OTHER,
    HIJACK_CLASS_PARSE_FAILURE,
})

# Default-OFF behavioral flag (doctrine #1). When unset/"0", env_guard still
# RUNS but the caller treats it as advisory-only (emit, do not block). When "1",
# the caller BLOCKS. The flag name is the SoT; the caller reads it from the
# import-time trusted_env snapshot (NOT live os.environ) so a late-set value
# can't toggle enforcement mid-process.
ENV_GUARD_ENFORCE_FLAG = "CEO_ENV_GUARD_ENFORCE"

_PRELOAD_KEYS = frozenset({"LD_PRELOAD", "DYLD_INSERT_LIBRARIES"})
_PATH_KEYS = frozenset({
    "LD_LIBRARY_PATH", "LD_ORIGIN_PATH", "LD_CONFIG",
    "DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH",
    "DYLD_FALLBACK_LIBRARY_PATH", "DYLD_FALLBACK_FRAMEWORK_PATH",
    "DYLD_VERSIONED_LIBRARY_PATH", "DYLD_ROOT_PATH",
    "PYTHONPATH", "PERL5LIB", "RUBYLIB",
})
_RUNTIME_KEYS = frozenset({
    "PYTHONSTARTUP", "PYTHONINSPECT", "PERL5OPT", "RUBYOPT",
    "NODE_OPTIONS", "BASH_ENV", "ENV",
})

# Builtins that take NAME=VALUE assignment operands.
_ASSIGN_BUILTINS = frozenset({"export", "declare", "typeset", "local", "readonly"})

# A NAME=VALUE token: a valid shell identifier, then '='. We only need the NAME.
_ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=")

# Naive top-level split on shell control operators (same family as
# check_bash_safety._SUBCOMMAND_SPLIT_RE). Over-splitting inside quotes is safe:
# a chunk that fails shlex.split is skipped (it also can't be an assignment).
_SPLIT_RE = re.compile(r"\s*(?:&&|\|\||[;|])\s*")


def _classify(key: str) -> str:
    """Map a denylisted key to its closed-enum hijack_class."""
    if key in _PRELOAD_KEYS:
        return HIJACK_CLASS_LINKER_PRELOAD
    if key in _PATH_KEYS:
        return HIJACK_CLASS_LINKER_PATH
    if key in _RUNTIME_KEYS:
        return HIJACK_CLASS_RUNTIME_HOOK
    return HIJACK_CLASS_LINKER_OTHER


@dataclass
class EnvHijackMatch:
    """Result of an env-hijack scan.

    ``hijack_class`` is a member of :data:`ENV_VAR_HIJACK_CLASSES`. ``key`` is the
    matched denylist variable NAME (safe to display — a name, never the value).
    ``reason`` is an operator-facing remediation string that NEVER contains the
    assigned VALUE (the value is the payload/credential surface).
    """

    hijack_class: str
    key: str
    reason: str


def _assignment_names(tokens: List[str]) -> List[str]:
    """Yield the env-var NAMES this simple-command token list SETS.

    Three shapes, in order:
      1. leading assignment prefix(es): ``FOO=1 BAR=2 cmd``  → FOO, BAR
      2. ``export``/``declare``/``typeset``/``local``/``readonly`` NAME=val → NAME
      3. ``env`` [opts] NAME=val cmd                                       → NAME

    A bare ``$LD_PRELOAD`` reference yields nothing (not a set).
    """
    names: List[str] = []
    if not tokens:
        return names
    i = 0
    n = len(tokens)
    # (1) leading assignment prefix run.
    while i < n:
        m = _ASSIGN_RE.match(tokens[i])
        if m:
            names.append(m.group(1))
            i += 1
            continue
        break
    if i >= n:
        return names
    head = tokens[i].lstrip("\\").rsplit("/", 1)[-1]
    # (2) assignment builtins — scan operands for NAME=val.
    if head in _ASSIGN_BUILTINS:
        for t in tokens[i + 1:]:
            m = _ASSIGN_RE.match(t)
            if m:
                names.append(m.group(1))
        return names
    # (3) env(1) wrapper — parse env's options with getopt SEMANTICS (not
    # case-by-case), then collect NAME=val operands. Option ARITY is the security
    # contract: the unset flag (`-u`/`--unset`) consumes a var NAME (NOT a set), so
    # if we treated that name as the command operand and stopped, a later
    # denylisted assignment would be hidden. The unset NAME can ride in ANY of:
    #   separated short:  `env -u FOO ...`
    #   attached short:   `env -uFOO ...`
    #   in a CLUSTER:     `env -iu FOO ...`  /  `env -iuFOO ...`  (i=ignore-env, u=unset)
    #   long separated:   `env --unset FOO ...`
    #   long equals:      `env --unset=FOO ...`
    # After consuming the option (and any arg it owns) we KEEP scanning — so no
    # cluster, attached or separated, can hide a later denylisted NAME=val.
    if head == "env":
        names.extend(_env_assignment_names(tokens[i + 1:]))
    return names


# Short env(1) flags that CONSUME an argument, per the macOS/BSD `man env`
# grammar that runs on THIS machine (verified against the installed man page +
# empirical `env -X arg NAME=val printenv NAME` runs — NOT guessed):
#   -C altwd     change to an alternate working dir   (takes an arg)
#   -P altpath   alternate PATH to find the utility   (takes an arg)
#   -S string    split-string into more env args      (takes an arg)
#   -u name      unset a variable                      (takes an arg)
# No-arg short flags on this env are -0, -i, -v (handled by the cluster loop's
# "continue" on any unrecognized char — the SAFE direction: we keep scanning for
# the denylisted assignment rather than over-consuming and hiding it). If a
# with-arg flag's value were mis-read as the command, scanning would STOP and a
# later `LD_PRELOAD=` would slip through — so EVERY arg-taking short flag must be
# listed here. Covering -P/-C closes the `env -P /usr/bin BASH_ENV=…` bypass.
#
# OUT OF SCOPE (by design — this is a default-OFF defense-in-depth guard): GNU
# coreutils env long options that take args (e.g. --block-signal=SIG,
# --chdir=DIR, --split-string=S, --unset=NAME) are a DIFFERENT grammar from the
# BSD env on this host. `--unset`/`--unset=` are still handled (common + the
# security-critical one); other GNU `--long=val` forms are self-contained
# (val rides in the token) so they cannot hide a following assignment, and bare
# GNU `--long val` arg-takers are not covered here.
_ENV_SHORT_OPTS_WITH_ARG = frozenset({"u", "C", "P", "S"})


def _env_assignment_names(rest: List[str]) -> List[str]:
    """Return the NAME=val names set by an ``env`` wrapper's operand list.

    ``rest`` is the token list AFTER the ``env`` command word. Parses leading
    options (short clusters + long forms) honoring arity, then collects every
    ``NAME=val`` operand until the first bare operand (the command env runs).
    Pure; never raises.
    """
    names: List[str] = []
    j = 0
    n = len(rest)
    while j < n:
        t = rest[j]
        if not t:
            j += 1
            continue
        # Bare `-`: on macOS/BSD env(1) a lone dash means ignore-environment
        # (same as -i), NOT the utility — verified: `env - BASH_ENV=/tmp/x
        # printenv` SETS BASH_ENV and drops the inherited env. Treat it as a
        # no-arg flag and KEEP scanning for a following NAME=val (else
        # `env - BASH_ENV=…` would slip through).
        if t == "-":
            j += 1
            continue
        # End-of-options marker: stop treating tokens as flags, but env still
        # accepts `NAME=val` operands after it (`env -- FOO=1 cmd`), so keep
        # scanning assignments rather than breaking outright.
        if t == "--":
            j += 1
            while j < n:
                m = _ASSIGN_RE.match(rest[j])
                if m:
                    names.append(m.group(1))
                    j += 1
                    continue
                break
            break
        # Long options.
        if t.startswith("--"):
            if t == "--unset":
                j += 2  # `--unset NAME` — consume the flag AND the var name
                continue
            if t.startswith("--unset="):
                j += 1  # `--unset=NAME` — self-contained; keep scanning
                continue
            j += 1  # any other long flag (--ignore-environment/--null/…) takes no arg
            continue
        # Short option cluster, e.g. `-i`, `-u`, `-iu`, `-iuFOO`.
        if t.startswith("-") and len(t) > 1:
            body = t[1:]
            consumed_next = False
            k = 0
            blen = len(body)
            while k < blen:
                ch = body[k]
                if ch in _ENV_SHORT_OPTS_WITH_ARG:
                    # This flag takes an arg. If chars follow it IN THIS token,
                    # they ARE the arg (attached form `-uFOO` / `-iuFOO`); the
                    # token is fully consumed. Otherwise the NEXT token is the arg
                    # (separated form `-u FOO` / `-iu FOO`).
                    if k + 1 < blen:
                        pass  # rest of the token is the arg → token done
                    else:
                        consumed_next = True  # next token is the arg
                    break
                k += 1  # no-arg flag char (i/0/v/…) → continue the cluster
            j += 2 if consumed_next else 1
            continue
        # NAME=val assignment operand.
        m = _ASSIGN_RE.match(t)
        if m:
            names.append(m.group(1))
            j += 1
            continue
        # First bare operand = the command env(1) runs; its argv follows. Stop.
        break
    return names


def scan_command(command: str) -> Optional[EnvHijackMatch]:
    """Scan a raw Bash command for a denylisted env-var SET.

    Returns the FIRST :class:`EnvHijackMatch` (deterministic: first sub-command,
    then first matched name in that sub-command) or ``None`` if the command sets
    no denylisted variable. Pure; never raises.

    Fail-CLOSED on a per-chunk parse failure ONLY when the chunk textually
    contains a denylisted key NAME followed by ``=`` — i.e. an attacker can't hide
    a ``LD_PRELOAD=…`` set behind a deliberately-unbalanced quote. A chunk with no
    denylist-key substring that fails to parse is skipped (fail-safe; it can't be
    a denylisted set).
    """
    if not command or not command.strip():
        return None
    for chunk in _SPLIT_RE.split(command):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            tokens = shlex.split(chunk)
        except ValueError:
            # Unparseable chunk — fail-CLOSED iff it textually smuggles a
            # denylisted SET (KEY=) so a broken quote can't hide a hijack.
            for key in DISALLOWED_ENV_KEYS:
                if (key + "=") in chunk:
                    return EnvHijackMatch(
                        hijack_class=HIJACK_CLASS_PARSE_FAILURE,
                        key=key,
                        reason=(
                            "GOVERNANCE: bash command sets a loader/runtime-hijack "
                            "environment variable but failed to parse cleanly "
                            "(fail-CLOSED). Re-quote and remove the env override."
                        ),
                    )
            continue
        for name in _assignment_names(tokens):
            if name in DISALLOWED_ENV_KEYS:
                return EnvHijackMatch(
                    hijack_class=_classify(name),
                    key=name,
                    reason=(
                        f"GOVERNANCE: bash command sets {name!r}, a "
                        "linker/loader/runtime-hijack environment variable that can "
                        "inject attacker code into a trusted process. Remove the "
                        "override; if a library path is genuinely required, set it "
                        "outside Claude Code."
                    ),
                )
    return None
