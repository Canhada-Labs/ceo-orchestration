"""Posture-toggle matcher tables and rule declarations."""
from __future__ import annotations

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

        if cmd in _E3_INTERPRETER_C_FLAGS:
            flags = _E3_INTERPRETER_C_FLAGS[cmd]
            for j in range(i + 1, n - 1):
                if tokens[j] in flags:
                    body = tokens[j + 1]
                    hit = _scan_blob(body)
                    if hit is not None:
                        return (
                            f"GOVERNANCE: bash {tok!r} -c/-e body references "
                            f"canonical path {hit!r}. The guard cannot prove "
                            "read vs write: use Read/cat/grep for reading, "
                            "or Edit/Write with sentinel for edits."
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
                for _follow in _e3_segment_positionals(tokens, i + 1):
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


# -----------------------------------------------------------------------------
# PLAN-165 NF-08 — posture-toggle INVOCATION guard (round-3 security review)
# -----------------------------------------------------------------------------
#
# `_e3_check_canonical_path_write` above matches WRITE shapes only. A canonical
# path sitting in the SCRIPT position of an interpreter is not one of them, so
#
#     python3 .claude/scripts/night-mode.py on
#     ./.claude/scripts/night-mode.py on
#
# both returned ALLOW while three signed comments (check_canonical_edit.py's
# `_CANONICAL_GUARDS` note, settings.json's `_night_mode_deny_surface_comment`,
# and the round-3 sentinel) claimed the model rail could not invoke the toggle.
# Listing the writer in `_CANONICAL_GUARDS` protects the FILE; this matcher
# protects the ACTION.
#
# Property being PURSUED — Owner ratification OQ1-redo (2026-08-03): arming or
# disarming the autonomy posture is a HUMAN action (the `!` prefix or a
# terminal). This matcher raises the cost of the model rail doing it; it does
# NOT close the boundary, and saying otherwise would be a false claim on a
# signed surface (codex S292 r8 P1). Static parsing of bash is incomplete by
# construction: a RENAMED INTERPRETER (`./zz-interp <toggle> on`) passes both
# this matcher and the script's self-path guard — measured, see
# nf08-invocation-guard-NOTES.md §7 residual 5. The perimeter that actually
# holds is the CURRENT session's defaultMode + Bash allowlist; this rail is
# defence-in-depth plus the pedagogical message pointing at `!`.
#
# DIVISION OF LABOUR with `_e3` (asserted from both sides by
# `.claude/hooks/tests/test_bash_posture_toggle_invocation.py`):
#   • `_e3` blob-scan → INDIRECT bodies (`bash -c '…'`, `eval`, `xargs`,
#     `find -exec`) already deny, because the toggle path is a literal
#     `_CANONICAL_GUARDS` entry. Those keep the older canonical message.
#   • `_e4` (here)    → DIRECT argv forms: the path as the command word, or as
#     the operand an interpreter/prefix runner would execute, plus the
#     CREATION of an executable alias (`ln`, see `_E4_LINK_RUNNERS`).
#   • `night-mode.py`'s own SELF-PATH GUARD → execution through an alias that
#     already exists. A matcher sees spellings; an alias exists precisely to
#     have a different one, so this layer is the boundary and the two above
#     are the early signal. See the r2 note at the end of this comment.
#
# Scope note: this denies EVERY invocation, `status` included. Carving out a
# read-only subcommand would key a PERMISSIVE branch off argv parsing — the
# exact shape the fail-closed doctrine rejects — and the recovery route (`!`)
# is always available, so a blanket deny strands nobody.
#
# CODEX S292 REVIEW (two P1 bypasses of the FIRST implementation, both fixed
# below and pinned red-first in the test file):
#   P1-A  a raw-substring pre-filter returned ALLOW before shlex ever ran, so
#         any spelling the SHELL normalises escaped: `night"-"mode.py`,
#         `night''-mode.py`, `night\-mode.py`, and — on APFS — `NIGHT-MODE.PY`.
#         Fix: no pre-filter (always tokenize), and compare CASE-FOLDED.
#         Folded in beyond the finding: glob spellings (`night-mod?.py`).
#   P1-B  a value-bearing flag on a prefix runner (`env -u FOO python3 …`,
#         `sudo -u root python3 …`) had its VALUE read as the command word,
#         and the scan stopped there — the interpreter and the script that
#         followed were never examined. Fix: resolve the whole runner chain
#         with a per-runner flag table, and treat an UNKNOWN flag as
#         ambiguous (fail-closed) rather than as boolean.
# Both were found on the model's own draft, by the cross-vendor pair rail.
#
# CODEX S292 REVIEW ROUND 2 (P1 — executable ALIASES). The fixed matcher still
# recognised only SPELLINGS, so `ln -s .claude/scripts/night-mode.py /tmp/nm &&
# python3 /tmp/nm on` armed the posture: `ln` reads the toggle (not a write, so
# `_e3` allows it), and at execution time nothing but `/tmp/nm` is on the
# command line. Measured on this platform before fixing — the alias printed
# `result=applied` and wrote `defaultMode: acceptEdits`. Re-probing widened the
# class beyond the finding: a RENAMED COPY inside the repo
# (`cp …/night-mode.py .claude/scripts/nm2.py && python3 .claude/scripts/nm2.py
# on`) armed it too, and no `ln` rule would have caught that one.
#
# The fix is therefore split by what each layer can actually know:
#   • HERE — deny creating a link that names the toggle (`_E4_LINK_RUNNERS`).
#     Cheap, string-only, and the earliest signal. NOT sufficient: the alias
#     can also arrive from a previous session, a `git checkout`, `os.symlink`,
#     `tar -x`, or the operator's own hand.
#   • IN THE SCRIPT — `night-mode.py` refuses to run unless the file it was
#     invoked as IS the canonical `<repo>/.claude/scripts/night-mode.py`. That
#     covers both members of the class, holds however the alias was made, and
#     holds even if this hook never runs.
# Doing the execution half here was considered and REJECTED: it would require
# resolving an attacker-supplied path on every Bash command (FS syscall in the
# hook budget, `RuntimeError` on a symlink loop — the fail-open class the S277
# pair rail found in this repo's own draft — and a TOCTOU window).

# The governance surface. One entry today; the frozenset is the seam for any
# future posture writer (add the path here AND to `_CANONICAL_GUARDS` — the
# coherence test in test_bash_posture_toggle_invocation.py fails otherwise).
_E4_POSTURE_TOGGLE_SCRIPTS = frozenset({".claude/scripts/night-mode.py"})
_E4_TOGGLE_BASENAMES = frozenset(
    _e3_basename(_p) for _p in _E4_POSTURE_TOGGLE_SCRIPTS
)

# Case-folded twins. Codex S292 P1-A: on a case-INSENSITIVE filesystem — APFS,
# this repo's default platform — `.claude/scripts/NIGHT-MODE.PY` IS the toggle,
# and an exact-case comparison waved it through. Same defect class, same fix,
# and deliberately the same spelling as the write rail's
# `PLAN162_FIX_CASEFOLD`: `str.lower`, NOT `str.casefold`, because casefold
# expands 'ß'→'ss' and changes token LENGTH (which changes what a glob
# matches). The exploited class is ASCII case variance, which `lower()` covers
# exactly, and folding can only ever ADD matches, never remove one.
#
# On a case-SENSITIVE filesystem this over-classifies (`NIGHT-MODE.PY` is a
# different file there, and running it would be denied). That is the safe
# direction — a false deny costs one `!`-prefixed retry; a false allow is a
# silent bypass of a rail three signed comments claim is closed.
_E4_TOGGLE_PATHS_FOLDED = frozenset(_p.lower() for _p in _E4_POSTURE_TOGGLE_SCRIPTS)
_E4_TOGGLE_BASENAMES_FOLDED = frozenset(_b.lower() for _b in _E4_TOGGLE_BASENAMES)

# Glob spellings — the third way to name the file without spelling it
# (`night-mod?.py`, `night-*.py`). Not in the codex finding; folded in because
# it is the same class as the concatenation bypass and would have been the
# obvious next probe. Bounded by a LITERAL-CHARACTER FLOOR: a pattern must
# carry at least this many non-metacharacters to count as a spelling of the
# toggle. `night-mod?.py` (12 literals) does; the generic `*.py` (3) does not
# — denying THAT would break ordinary `python3 *.py` use for no gain, since
# the shell only resolves it to the toggle from inside `.claude/scripts`.
_E4_GLOB_META = "*?["
_E4_GLOB_MIN_LITERALS = 4

# BRACE EXPANSION — the fourth way to name the file without spelling it
# (codex S292 review round 4, P1). Measured on this platform BEFORE fixing
# (GNU bash 3.2.57, arm64-apple-darwin25), every one of these ran the toggle
# while the matcher returned ALLOW:
#
#   python3 .claude/scripts/{night-mode,other}.py on   -> 2 words, argv[1] is the toggle
#   python3 .claude/scripts/night-mode{,}.py on        -> 2 identical words
#   python3 .claude/scripts/night{-,x}mode.py on       -> toggle + a decoy
#   python3 .claude/scripts/night-mode.p{y..y} on      -> ONE word: the canonical path
#
# The last one is the strongest and was NOT in the finding: a RANGE whose
# endpoints are equal expands to a SINGLE word, so the command line bash
# executes is byte-identical to the literal deny case — `argv` included
# (`TOGGLE RAN argv=['.claude/scripts/night-mode.py', 'on']`). There is no
# residue of the bypass at run time at all.
#
# Handled by EXPANDING, not by wildcarding. Brace expansion is STATIC text —
# the shell derives it from the command alone, with no run-time value
# involved — so the same reasoning that DECODES `$'\x2d'` rather than
# globbing it applies here, and more sharply: replacing `{night-mode,other}`
# with `*` would skeletonise to `.claude/scripts/*.py`, land under
# `_E4_GLOB_MIN_LITERALS`, and ALLOW. Precision is not a luxury here, it is
# the only thing that works.
#
# Two budgets, because expansion is a cross-product and an execution-position
# token is never legitimately enormous:
#   • _E4_BRACE_MAX_WORDS — words enumerated per token before the guard stops
#     and reports "cannot decide" (fail-CLOSED: the token is DENIED). Sized so
#     that real large-but-sane braces (`bash deploy.sh {srv001..srv300}`)
#     expand EXACTLY and stay allowed; only a deliberate bomb reaches it.
#   • _E4_BRACE_MAX_TOKEN — characters in the token, which bounds the memory
#     the expander can be made to hold (each pending word is ~len(token)).
_E4_BRACE_MAX_WORDS = 4096
_E4_BRACE_MAX_TOKEN = 4096

# `{A..B}` and `{A..B..STEP}` sequence expressions. The STEP is parsed and
# then IGNORED on purpose: honouring it would SHRINK the set (`{1..9..3}` is
# 1,4,7), and a matcher that considers fewer words than the shell produces is
# the one direction this must not fail in. Ignoring it yields a superset.
#
# Zero-padded integer ranges (`{01..03}` -> 01 02 03 in bash) are generated
# UNPADDED here. That under-approximates a shape no path spelling of the
# toggle can use — the guarded basename carries no digits — and is recorded
# rather than fixed so the next reader does not mistake it for an oversight.
_E4_BRACE_INT_RANGE_RE = re.compile(r"^(-?[0-9]+)\.\.(-?[0-9]+)(?:\.\.-?[0-9]+)?$")
_E4_BRACE_CHR_RANGE_RE = re.compile(r"^([A-Za-z])\.\.([A-Za-z])(?:\.\.-?[0-9]+)?$")

# Interpreters that take a FILE to execute. `python`, `python3`, `python3.12`.
_E4_PYTHON_RE = re.compile(r"^python[0-9]*(\.[0-9]+)*$")
_E4_SHELL_RUNNERS = frozenset({"bash", "sh", "zsh", "ksh", "dash"})

# Commands that RUN another command: strip them and keep looking. `timeout 5 …`
# / `nice -n 10 …` carry a numeric operand before the real command word, which
# the duration/flag skip below consumes.
#
# THIS LIST IS THE SECONDARY RAIL (codex S292 r5 P1). It has now failed three
# times in three review rounds — `env`/`sudo` (r2), brace spellings (r4),
# `xcrun` (r5) — which is the S291 lesson arriving on schedule: a closed set
# written from memory errs in BOTH directions, and this one errs toward ALLOW,
# the direction that is a silent bypass. Measured on this machine, all four
# launchers that exist here EXECUTE their operand and NONE of them was in the
# set: `xcrun python3 x.py`, `xcrun ./x.py`, `arch -x86_64 python3 x.py`,
# `caffeinate python3 x.py`, `script -q /dev/null python3 x.py` — every one
# printed the dummy's output.
#
# The PRIMARY rail is now structural and needs no names at all: `_e4_scan`
# keeps testing every remaining token of a segment for INTERPRETER family, so
# `<anything> python3 <toggle>` is denied whether or not `<anything>` is
# listed here. See the INTERPRETER HOP note in the walk.
#
# What the list still buys — and why it is extended rather than deleted — is
# the DIRECT-EXEC position: `xcrun ./<toggle> on` names no interpreter, and
# the toggle ships mode 100755, so it runs. Distinguishing that from
# `cat <toggle>` is structurally impossible (the shell executes the FIRST word
# in both; only the launcher's own semantics differ), so covering it requires
# naming launchers. Each addition below is justified from THIS machine's man
# page and confirmed by running it; launchers whose binaries are absent here
# (`unbuffer`, `proxychains4`, `taskset`, `firejail`, `parallel`, `flock`,
# `torify`, `systemd-run`, `strace`, …) are deliberately NOT added from
# memory — an invented flag table false-positives on readers, and the
# structural rail already covers their interpreter form.
_E4_PREFIX_RUNNERS = frozenset({
    "exec", "command", "nohup", "env", "sudo", "doas", "nocorrect",
    "setsid", "stdbuf", "xargs", "time", "timeout", "nice", "ionice",
    # macOS launchers, measured present + executing on this platform.
    "xcrun", "arch", "caffeinate", "script", "sandbox-exec",
})
_E4_DURATION_RE = re.compile(r"^[0-9]+(\.[0-9]+)?[smhd]?$")

# Runner flags that consume the NEXT token as their value, so it is not
# mistaken for the script operand (`python3 -X importtime script.py`).
_E4_RUNNER_VALUE_FLAGS = frozenset({
    "-W", "-X", "--check-hash-based-pycs",      # python
    "-o", "+o", "--rcfile", "--init-file",      # POSIX shells
})

# ---------------------------------------------------------------------------
# PREFIX-RUNNER flag table — codex S292 P1-B.
# ---------------------------------------------------------------------------
# The first implementation skipped any token starting with `-` and then took
# the first non-flag token as the command word. For a VALUE-BEARING flag that
# token is the flag's VALUE, not a command:
#
#     env  -u FOO  python3 .claude/scripts/night-mode.py on
#              ^^^ read as the command word → the rest was never examined
#     sudo -u root python3 .claude/scripts/night-mode.py on
#
# Both returned ALLOW. The scan must resolve the whole runner chain.
#
# DERIVATION (the S291 lesson: a closed set written from memory errs in BOTH
# directions, so each entry below names its authority):
#   env, xargs, stdbuf, nice  → this machine's man pages, `man 1 <cmd>`
#   sudo                      → this machine's `man 8 sudo` option list
#   timeout, ionice, setsid   → GNU coreutils / util-linux documented
#   doas, time                → synopsis (binaries absent on darwin, so the
#                               man page could not be read here — flagged in
#                               the NOTES as the weakest rows)
#
# BOTH error directions are covered, which is why the table carries the
# BOOLEAN flags too rather than only the value-bearing ones:
#   • a value flag recorded as unknown → the value is examined as a command
#     word AND the scan continues one token further (see `ambiguous` in the
#     walk) → still denied, no bypass;
#   • a boolean flag recorded as value-bearing → the real command word is
#     skipped, and the token after it (the script) is examined at command-word
#     position → still denied, but `sudo -E cat <toggle>` would false-positive.
#     That is why `-E`/`-n`/`-s`/... are listed explicitly.
# An UNKNOWN flag is therefore FAIL-CLOSED-ambiguous, never silently boolean.
