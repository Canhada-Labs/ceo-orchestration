"""Posture-toggle token parsing and expansion helpers."""
from __future__ import annotations

_E4_PREFIX_RUNNER_FLAGS = {
    # man 1 env (darwin): -C altwd, -P altpath, -S string, -u name
    "env": (
        frozenset({"-u", "--unset", "-C", "--chdir", "-P", "-S", "--split-string"}),
        frozenset({"-0", "--null", "-i", "--ignore-environment", "-v", "--debug"}),
    ),
    # man 8 sudo (darwin). `-h` is BOTH `--help` and `--host host`; recorded
    # as value-bearing because only the `-h host command` form can carry a
    # command word at all (bare `sudo -h` runs nothing to guard).
    "sudo": (
        frozenset({
            "-C", "--close-from", "-D", "--chdir", "-g", "--group", "-h", "--host",
            "-p", "--prompt", "-R", "--chroot", "-T", "--command-timeout",
            "-U", "--other-user", "-u", "--user", "-r", "--role", "-t", "--type",
        }),
        frozenset({
            "-A", "--askpass", "-B", "--bell", "-b", "--background",
            "-E", "--preserve-env", "-e", "--edit", "-H", "--set-home",
            "-i", "--login", "-K", "--remove-timestamp", "-k", "--reset-timestamp",
            "-l", "--list", "-N", "--no-update", "-n", "--non-interactive",
            "-P", "--preserve-groups", "-S", "--stdin", "-s", "--shell",
            "-V", "--version", "-v", "--validate", "--help",
        }),
    ),
    # OpenBSD doas(1) synopsis: doas [-Lns] [-a style] [-C config] [-u user]
    "doas": (
        frozenset({"-a", "-C", "-u"}),
        frozenset({"-L", "-n", "-s"}),
    ),
    # GNU coreutils timeout: -k/--kill-after DURATION, -s/--signal SIGNAL.
    # The DURATION positional is consumed by `_E4_DURATION_RE` in the walk.
    "timeout": (
        frozenset({"-k", "--kill-after", "-s", "--signal"}),
        frozenset({"--preserve-status", "--foreground", "-v", "--verbose"}),
    ),
    # man 1 nice (darwin): nice [-n increment] utility
    "nice": (
        frozenset({"-n", "--adjustment"}),
        frozenset(),
    ),
    # util-linux ionice: -c class, -n classdata, -p PID, -P PGID, -u UID, -t
    "ionice": (
        frozenset({"-c", "--class", "-n", "--classdata", "-p", "--pid",
                   "-P", "--pgid", "-u", "--uid"}),
        frozenset({"-t", "--ignore"}),
    ),
    # man 1 xargs (darwin) + GNU. GNU's `-e[eof]` / `-i[repl]` take their
    # argument ATTACHED only, so they are boolean in separate-token terms.
    "xargs": (
        frozenset({"-E", "-I", "-J", "-L", "-n", "-P", "-R", "-S", "-s",
                   "-a", "--arg-file", "-d", "--delimiter", "--max-args",
                   "--max-procs", "--max-chars", "--max-lines", "--replace"}),
        frozenset({"-0", "--null", "-o", "--open-tty", "-p", "--interactive",
                   "-r", "--no-run-if-empty", "-t", "--verbose", "-x", "--exit",
                   "-e", "-i"}),
    ),
    # man 1 stdbuf (darwin): -e/-i/-o bufdef
    "stdbuf": (
        frozenset({"-i", "--input", "-o", "--output", "-e", "--error"}),
        frozenset(),
    ),
    # BSD time [-al] [-h] [-p] [-o file]; GNU time adds -f/--format FORMAT.
    "time": (
        frozenset({"-o", "--output", "-f", "--format"}),
        frozenset({"-a", "--append", "-l", "-h", "-p", "--portability",
                   "-v", "--verbose"}),
    ),
    # bash builtin: exec [-cl] [-a name] command
    "exec": (
        frozenset({"-a"}),
        frozenset({"-c", "-l"}),
    ),
    # POSIX/bash builtin: command [-pVv] command
    "command": (frozenset(), frozenset({"-p", "-v", "-V"})),
    # util-linux setsid [-c] [-f] [-w]
    "setsid": (frozenset(), frozenset({"-c", "--ctty", "-f", "--fork",
                                       "-w", "--wait"})),
    # No flags of their own (GNU nohup accepts only --help/--version).
    "nohup": (frozenset(), frozenset({"--help", "--version"})),
    "nocorrect": (frozenset(), frozenset()),
    # --- macOS launchers, codex S292 r5 ---------------------------------
    # Every row below is read off THIS machine's man page and then confirmed
    # by RUNNING the form against a dummy script. The tables are not optional
    # decoration: without them every flag classifies as unknown, the walk's
    # fail-closed `ambiguous` step keeps the command-word position open one
    # token too long, and a READER behind a value-bearing flag false-positives
    # (`caffeinate -t 60 cat <toggle>` would deny — measured before the row
    # was added).
    #
    # man 1 xcrun. macOS spells long options with ONE dash as well as two, and
    # `_e4_classify_prefix_flag` now matches those exactly — `xcrun -sdk
    # macosx python3 dummy.py` was RUN here and executed.
    "xcrun": (
        frozenset({"--sdk", "-sdk", "--toolchain", "-toolchain"}),
        frozenset({"-v", "--verbose", "-n", "--no-cache", "-k", "--kill-cache",
                   "-l", "--log", "-f", "--find", "-r", "--run",
                   "--show-sdk-path", "--show-sdk-version"}),
    ),
    # man 1 arch: arch [-32] [-64] [[-arch_name | -arch arch_name]...] [-c]
    #             [-d envname]... [-e envname=value]... [-h] prog [args ...]
    # The `-arch_name` forms are the architecture names the same man page
    # lists (i386, x86_64, x86_64h, arm64, arm64e) — boolean selectors, not
    # value-bearing. `arch -x86_64 python3 dummy.py` was RUN here.
    "arch": (
        frozenset({"-arch", "-d", "-e"}),
        frozenset({"-32", "-64", "-c", "-h",
                   "-i386", "-x86_64", "-x86_64h", "-arm64", "-arm64e"}),
    ),
    # man 8 caffeinate: caffeinate [-disu] [-t timeout] [-w pid] [utility ...]
    "caffeinate": (
        frozenset({"-t", "-w"}),
        frozenset({"-d", "-i", "-s", "-u"}),
    ),
    # man 1 script: script [-aeFkqr] [-t time] [file [command ...]]
    #               script -p [-deq] [-T fmt] [file]
    # NOTE the shape: script's FIRST positional is the typescript FILE, not
    # the command. So `script out.txt ./<toggle> on` still slips the
    # direct-exec rule (the filename settles as the command word). The
    # interpreter form `script -q /dev/null python3 <toggle>` is caught by
    # the structural hop, which is the form that matters.
    "script": (
        frozenset({"-t", "-T"}),
        frozenset({"-a", "-e", "-F", "-k", "-q", "-r", "-p", "-d"}),
    ),
    # man 1 sandbox-exec: sandbox-exec [-f profile-file] [-n profile-name]
    #                     [-p profile-string] [-D key=value ...] command [args]
    "sandbox-exec": (
        frozenset({"-f", "-n", "-p", "-D"}),
        frozenset(),
    ),
}

# `python3 -m <module>` normally has NO script operand (`-m pytest path.py`
# runs pytest ON the path — a read, not an execution). These modules are the
# exception: they execute the path they are given.
_E4_MODULE_PATH_RUNNERS = frozenset({"runpy"})

# Commands that create a SECOND LIVE ENTRY POINT to a file (codex S292 r2 P1).
#
# The rest of this matcher recognises tokens whose SPELLING resolves to the
# guarded path. A link defeats spelling by construction: after
# `ln -s .claude/scripts/night-mode.py /tmp/nm`, `python3 /tmp/nm on` names
# nothing recognisable — and it RUNS the toggle, because the script's
# `REPO_ROOT = Path(__file__).resolve().parents[2]` follows the link back into
# this repository (measured on this platform: `result=applied`, the overlay
# was written).
#
# The EXECUTION half of that bypass is NOT closable here and is deliberately
# not attempted: deciding whether `/tmp/nm` is the toggle requires resolving
# an attacker-supplied path on EVERY Bash command, which means an FS syscall
# inside the hook's latency budget, a `RuntimeError` on a symlink loop (the
# exact fail-open class the S277 pair-rail found in this repo), and a TOCTOU
# window in which the alias is created after the check. That half is closed
# in the script itself by the self-path guard, which needs no matcher at all.
# What a string matcher CAN see is the alias being created; this closes that.
#
# LINKS ONLY — `cp` is deliberately absent. A copy is a SNAPSHOT, not a second
# entry point: the self-path guard refuses to run any file that is not AT the
# canonical path of the repository it resolves into, so the copy is inert.
# Blocking `cp` would cost two real workflows for no security — backing the
# file up before editing it, and `install.sh`/`upgrade.sh` copying the toggle
# into an ADOPTER repo's own `.claude/scripts/night-mode.py`, where it is
# legitimately that repo's toggle.
_E4_LINK_RUNNERS = frozenset({"ln"})


def _e4_runner_family(name):  # noqa: ANN001
    """'python' | 'shell' | None for a normalised command name.

    ``name`` must arrive CASE-FOLDED. Found while re-probing the codex P1-A
    fix on this repo's own platform: folding the PATH but not the COMMAND
    NAME closes half the class, because PATH lookup is case-insensitive on
    APFS too — `PYTHON3 .claude/scripts/night-mode.py on`,
    `/usr/bin/PYTHON3 …` and `ENV -u FOO python3 …` all execute (verified by
    running them), and all three were ALLOWED by the half-folded matcher.
    """
    if _E4_PYTHON_RE.match(name):
        return "python"
    if name in _E4_SHELL_RUNNERS:
        return "shell"
    return None


# Substitution openers. `$(…)` tokenizes as `$` + `(` under this hook's
# punctuation_chars, and `` ` `` is its own token.
_E4_SUBST_OPENERS = frozenset({"$", "`"})
_E4_SUBST_CLOSERS = frozenset({")", "`"})


def _e4_substitution_body_names_toggle(tokens, start):  # noqa: ANN001
    """True if a command SUBSTITUTION starting at ``start`` names the toggle.

    `python3 $(echo .claude/scripts/night-mode.py) on` runs the toggle, but
    the substitution's value is not knowable statically: the walk saw `echo`
    settle as a command word and the path became its argument → ALLOW
    (verified executing before this was added).

    Same conjunctive shape the matcher already uses for `$S` variable
    indirection — the substitution must sit in an EXECUTION position (a
    command word, or an interpreter's script operand) AND the toggle must
    appear inside it. That keeps the read forms allowed: in
    `X=$(cat <toggle>)` and `echo $(cat <toggle>)` the substitution is not
    in an execution position, so this helper is never called for them.
    """
    k = start
    n = len(tokens)
    if k < n and tokens[k] == "$":
        k += 1                              # `$` `(` …
    if k >= n or tokens[k] not in ("(", "`"):
        return False
    k += 1
    depth = 1
    while k < n and depth > 0:
        t = tokens[k]
        if t == "(":
            depth += 1
        elif t in _E4_SUBST_CLOSERS:
            depth -= 1
            if depth == 0:
                break
        elif _e4_is_toggle_path(t):
            return True
        k += 1
    return False


def _e4_glob_names_toggle(cand_folded):  # noqa: ANN001
    """True if the case-folded ``cand_folded`` is a GLOB spelling of the toggle.

    Basename-level, and only for patterns carrying at least
    `_E4_GLOB_MIN_LITERALS` non-metacharacters — see the constant's note for
    why the generic `*.py` is deliberately NOT a spelling of the toggle.
    """
    if not any(c in cand_folded for c in _E4_GLOB_META):
        return False
    pat = _e3_basename(cand_folded)
    if sum(1 for ch in pat if ch not in "*?[]!") < _E4_GLOB_MIN_LITERALS:
        return False
    import fnmatch as _fn

    for base in _E4_TOGGLE_BASENAMES_FOLDED:
        try:
            if _fn.fnmatchcase(base, pat):
                return True
        except Exception:      # pragma: no cover — malformed bracket class
            continue
    return False


def _e4_brace_match(text, open_idx):  # noqa: ANN001
    """Index of the `}` closing the `{` at ``open_idx``, or -1 if unbalanced.

    `${…}` needs no special case: its `{` and `}` increment and decrement the
    same depth counter, so a parameter expansion nested inside a brace group
    balances out instead of stealing the closer. What DOES need a special
    case is starting ON a `${` — that is the caller's job
    (`_e4_first_expandable_group`).
    """
    depth = 0
    i = open_idx
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\\":
            i += 2              # a backslash-escaped brace is literal to bash
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _e4_split_top_level_commas(body):  # noqa: ANN001
    """Split a brace body on its TOP-LEVEL commas.

    Nested groups keep their commas (`{a,{b,c}}` splits into `a` and `{b,c}`,
    and the inner group is expanded on the next pass over the rebuilt word).
    """
    parts = []
    cur = []
    depth = 0
    i = 0
    n = len(body)
    while i < n:
        ch = body[i]
        if ch == "\\" and i + 1 < n:
            cur.append(ch)
            cur.append(body[i + 1])
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    parts.append("".join(cur))
    return parts


def _e4_group_alternatives(body):  # noqa: ANN001
    """The words a `{…}` body expands to, or None if bash leaves it LITERAL.

    None is a real answer, not a failure: bash does NOT expand a group with
    no top-level comma and no range (`night{weird}mode.py` stays exactly as
    typed), so returning None makes the literal rules judge the token as
    written — which is precisely what the shell will hand the kernel.

    Alternatives are capped at one past `_E4_BRACE_MAX_WORDS` so a range like
    `{1..9999999}` is never materialised; the caller's word budget then sees
    the overflow and fails closed.
    """
    parts = _e4_split_top_level_commas(body)
    if len(parts) > 1:
        return parts[:_E4_BRACE_MAX_WORDS + 1]
    for pattern, render in ((_E4_BRACE_INT_RANGE_RE, str),
                            (_E4_BRACE_CHR_RANGE_RE, chr)):
        m = pattern.match(body)
        if not m:
            continue
        lo, hi = m.group(1), m.group(2)
        lo, hi = (int(lo), int(hi)) if render is str else (ord(lo), ord(hi))
        step = 1 if hi >= lo else -1
        span = min(abs(hi - lo) + 1, _E4_BRACE_MAX_WORDS + 1)
        return [render(lo + step * k) for k in range(span)]
    return None


def _e4_first_expandable_group(text):  # noqa: ANN001
    """`(open, close)` of the first brace group bash would EXPAND, or (-1, -1).

    Skips `${…}` (parameter expansion — a different rule owns it, and pass 2's
    skeleton has already replaced it by the time it matters) and skips groups
    bash treats as literal, continuing INTO them: `{a{b,c}}` expands to
    `{ab} {ac}` in bash, so the inner group must still be found.
    """
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "{" and not (i and text[i - 1] == "$"):
            j = _e4_brace_match(text, i)
            if j > i and _e4_group_alternatives(text[i + 1:j]) is not None:
                return i, j
        i += 1
    return -1, -1


def _e4_brace_words(token):  # noqa: ANN001
    """Yield every word ``token`` brace-expands to.

    ITERATIVE (an explicit stack, not recursion): the depth of this walk is
    the number of brace groups in the token, which is attacker-controlled, and
    a `RecursionError` inside a security matcher is a crash — i.e. a fail-OPEN
    — not a deny.

    Bash's left-to-right ORDER is not reproduced, and does not need to be: the
    caller asks a membership question ("is the toggle among these"), never a
    positional one.
    """
    stack = [token]
    while stack:
        cur = stack.pop()
        i, j = _e4_first_expandable_group(cur)
        if i < 0:
            yield cur
            continue
        prefix, body, suffix = cur[:i], cur[i + 1:j], cur[j + 1:]
        for alt in reversed(_e4_group_alternatives(body)):
            stack.append(prefix + alt + suffix)


def _e4_brace_names_toggle(path):  # noqa: ANN001
    """`(matched, undecidable)` for a token carrying a brace expansion.

    `matched`     — some word this token expands to names the toggle.
    `undecidable` — the token blew a budget, so the guard stopped enumerating.
                    Callers treat this as a match (fail-CLOSED), and the deny
                    message says which of the two it was rather than claiming
                    a spelling the operator never wrote.
    """
    if len(path) > _E4_BRACE_MAX_TOKEN:
        return False, True
    seen = 0
    for word in _e4_brace_words(path):
        seen += 1
        if seen > _E4_BRACE_MAX_WORDS:
            return False, True
        if _e4_plain_names_toggle(word):
            return True, False
    return False, False


def _e4_plain_names_toggle(path):  # noqa: ANN001
    """True if ``path`` names the toggle AS SPELLED (no brace expansion).

    Matches the repo-relative spelling, any absolute/relative path ending in
    it (`./…`, `/abs/repo/…`, `a/../…` — normalised string-only, no
    filesystem hit), and — because callers only ever pass EXECUTION-position
    operands — the bare basename, which closes the otherwise free
    `cd .claude/scripts && python3 night-mode.py on` spelling that no
    path-prefix rule can see.

    Comparison is CASE-FOLDED (codex S292 P1-A; see `_E4_TOGGLE_PATHS_FOLDED`)
    and glob-aware, because the property is "this token resolves to the
    guarded script", not "this token is spelled like it". Callers pass
    EXECUTION-position operands only, so widening here cannot touch reads.
    """
    if not path:
        return False
    import os as _os

    cand = _os.path.normpath(path).lower()
    for target in _E4_TOGGLE_PATHS_FOLDED:
        if cand == target or cand.endswith("/" + target):
            return True
    if _e3_basename(cand) in _E4_TOGGLE_BASENAMES_FOLDED:
        return True
    return _e4_glob_names_toggle(cand)


def _e4_is_toggle_path(path):  # noqa: ANN001
    """True if ``path`` names a posture-toggle script — spelled OR expanded.

    Two questions, cheapest first: does the token name the toggle as written,
    and (only if it carries a `{`) does any word bash expands it into.

    Reads are untouched by the widening for the same structural reason the
    earlier rounds relied on: every caller passes an EXECUTION-POSITION
    operand. `cat {a,b}.txt` and `cat .claude/scripts/{night-mode,other}.py`
    never reach here, because `cat` settles as a command word and its
    arguments are not inspected at all.
    """
    if not path:
        return False
    if _e4_plain_names_toggle(path):
        return True
    if "{" not in path:
        return False
    matched, undecidable = _e4_brace_names_toggle(path)
    return matched or undecidable


def _e4_classify_prefix_flag(tok, value_flags, bool_flags):  # noqa: ANN001
    """Classify a flag token of a PREFIX RUNNER — codex S292 P1-B.

    Returns one of:
      'value'   — consumes the NEXT token (`env -u FOO`, `sudo -u root`)
      'bool'    — stands alone (`sudo -E`, `sudo -En`, `setsid -f`)
      'attached'— carries its value in the same token (`-I{}`, `--user=root`)
      'unknown' — not in the runner's table → AMBIGUOUS, handled fail-closed
                  by the walk (the next token is examined as a command word
                  AND the scan continues past it).
    """
    if tok.startswith("--"):
        base = tok.split("=", 1)[0]
        if "=" in tok:
            return "attached" if (base in value_flags or base in bool_flags) else "unknown"
        if base in value_flags:
            return "value"
        if base in bool_flags:
            return "bool"
        return "unknown"
    body = tok[1:]
    if not body:
        return "unknown"                      # a lone '-'
    # SINGLE-DASH LONG names — `xcrun -sdk macosx`, `arch -x86_64`,
    # `script -T fmt` (codex S292 r5). macOS tools spell long options with one
    # dash, and the short-CLUSTER heuristic below cannot see them: `-sdk`
    # would be tested as the cluster `-s -d -k` and come back unknown, which
    # keeps the command-word position open one token too long and
    # false-positives on `xcrun -sdk macosx cat <toggle>`. Exact match first,
    # so a table row means what it says. A no-op for the single-character
    # rows: an exact hit there is the same answer the length-1 branch gives.
    if tok in value_flags:
        return "value"
    if tok in bool_flags:
        return "bool"
    if "=" in tok:
        head = tok.split("=", 1)[0]
        if head in value_flags or head in bool_flags:
            return "attached"                 # `-sdk=macosx`
    first = "-" + body[0]
    if len(body) == 1:
        if first in value_flags:
            return "value"
        if first in bool_flags:
            return "bool"
        return "unknown"
    if all(("-" + c) in bool_flags for c in body):
        return "bool"                         # short cluster, e.g. `sudo -En`
    if first in value_flags:
        return "attached"                     # `-I{}`, `-n10`, `-oL`
    return "unknown"


def _e4_runner_operands(tokens, start, family):  # noqa: ANN001
    """Operands of a runner that could name a file the runner EXECUTES.

    python family → the script operand only (argv[1] semantics; later
    positionals are the script's own argv, not something python runs, so
    `python3 tool.py .claude/scripts/night-mode.py` is a read).
    shell family  → every segment positional, because a shell also executes
    what reaches it out-of-band: `bash <<EOF … EOF` tokenizes its heredoc body
    into the same segment (`_e3_segment_positionals` skips the redirect clause
    and keeps collecting), and `sh wrapper.sh <path>` hands the path to a
    script the shell is already running.

    Returns [] when the runner is in a BODY form (`-c`) — `_e3`'s blob-scan
    owns that class and denies it with the canonical-path message.
    """
    args = _e3_segment_positionals(tokens, start)
    j = 0
    while j < len(args):
        a = args[j]
        if a == "--":
            rest = args[j + 1:]
            return rest[:1] if family == "python" else rest
        if a == "-c":
            return []
        if a == "-m" and family == "python":
            mod = args[j + 1] if j + 1 < len(args) else None
            if mod in _E4_MODULE_PATH_RUNNERS:
                return args[j + 2:j + 3]
            return []
        if a.startswith("-"):
            j += 2 if (a in _E4_RUNNER_VALUE_FLAGS and j + 1 < len(args)) else 1
            continue
        rest = args[j:]
        return rest[:1] if family == "python" else rest
    return []


def _e4_interpreter_deny(tokens, i, family, assigned_toggle, expansion_pass):  # noqa: ANN001
    """Deny reason if the interpreter at index ``i`` would EXECUTE the toggle.

    Factored out of the walk (codex S292 r5) because it now has TWO callers
    that must stay byte-identical in behaviour: the command-word branch, and
    the INTERPRETER HOP that runs after an unknown launcher settles. A
    divergence between them is exactly the shape this review round found —
    one position enforcing a rule the other does not.
    """
    operands = _e4_runner_operands(tokens, i + 1, family)
    for operand in operands:
        if _e4_is_toggle_path(operand):
            return _e4_deny_reason(operand, expansion_pass)
        if assigned_toggle and "$" in operand:
            return _e4_deny_reason(operand, expansion_pass)  # `S=…; python3 $S on`
    # `python3 $(echo …/night-mode.py) on` — the script operand IS a
    # substitution, so `_e3_segment_positionals` stopped at `(`/`` ` `` and
    # returned nothing (or just the bare `$`) to inspect.
    if (not operands or operands[0] in _E4_SUBST_OPENERS) and \
            _e4_substitution_body_names_toggle(tokens, i + 1):
        return _e4_deny_reason("command substitution naming the toggle", expansion_pass)
    return None


# Inserted between a line's two halves when an UNQUOTED newline is rewritten
# as the command separator Bash treats it as. SPACE-PADDED on purpose: shlex
# returns a RUN of punctuation characters as ONE token, so a bare `;` appended
# to `&&` would tokenize as `'&&;'` — a token in no terminator set, which is
# how a "fix" here could quietly LOSE a boundary it meant to add.
_E4_NEWLINE_SEPARATOR = " ; "


def _e4_normalise_command(command):  # noqa: ANN001
    """Rewrite the two Bash line constructs `shlex` does not model.

    CODEX S292 REVIEW ROUND 3 (P1 — newline is a command separator):

      • an UNQUOTED NEWLINE separates commands exactly like `;`. `shlex`
        classifies it as WHITESPACE, and the walk resets `at_cmd_word` only
        on `_E3_TERMINATORS`, so a second LINE was flattened into the first
        command's argument list and its command word was never examined:
        `echo ok\\npython3 <toggle> on` returned ALLOW while Bash ran the
        toggle. Rewritten to `_E4_NEWLINE_SEPARATOR`.

      • `\\<newline>` is a LINE CONTINUATION that Bash REMOVES. shlex's escape
        handling instead yields a literal-newline WORD, which settled as a
        bogus command word and pushed the real script operand into a
        non-command position — so `python3 \\<NL> <toggle> on` was ALLOWED
        too. Found while probing the finding; same normalisation closes it.

    QUOTE-AWARE, which is the whole reason this is a scanner and not a
    `str.replace`: a newline inside quotes is literal DATA in Bash (`git
    commit -m "subject\\n\\nbody"`), and turning it into a separator would
    manufacture command words out of prose — operator DoS on a hook that
    runs on EVERY Bash command. Single quotes suppress escapes entirely;
    double quotes keep `\\<newline>` as a continuation, as Bash does.

    An escaped BACKSLASH is consumed as a pair, so `echo 'a\\\\'` followed by
    a newline keeps its line boundary instead of having it eaten.

    Returns ``command`` UNCHANGED when it carries no newline — the common
    case, and an identity rather than a re-render (asserted by
    ``test_newline_normalisation_is_quote_aware``).
    """
    if "\n" not in command:
        return command
    out = []
    quote = None
    i = 0
    n = len(command)
    while i < n:
        ch = command[i]
        if quote == "'":
            out.append(ch)              # single quotes: everything literal
            if ch == "'":
                quote = None
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            nxt = command[i + 1]
            if nxt == "\n":
                i += 2                  # line continuation — Bash drops both
                continue
            if nxt == "\r" and i + 2 < n and command[i + 2] == "\n":
                i += 3                  # CRLF continuation
                continue
            out.append(ch)
            out.append(nxt)             # keep `\\`, `\"`, `\$`, `\-` intact
            i += 2
            continue
        if ch == "'" and quote is None:
            quote = "'"
        elif ch == '"':
            quote = None if quote == '"' else '"'
        elif ch == "\n" and quote is None:
            out.append(_E4_NEWLINE_SEPARATOR)
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


# Shell EXPANSIONS, longest form first. Anything a `$` or a backtick can turn
# into text at run time — the hook cannot evaluate any of it.
