"""Posture-toggle scanning and command decision helpers."""
from __future__ import annotations

_E4_EXPANSION_RE = re.compile(
    r"\$\([^)]*\)"                  # $(...)   command substitution
    r"|\$\{[^}]*\}"                 # ${...}   parameter expansion
    r"|\$'(?:[^'\\]|\\.)*'"         # $'...'   ANSI-C quoting
    r"|\$\"(?:[^\"\\]|\\.)*\""      # $"..."   locale translation
    r"|`[^`]*`"                     # `...`    legacy substitution
    r"|\$[A-Za-z_][A-Za-z0-9_]*"    # $NAME
    r"|\$[0-9@*#?$!-]"              # $1 $@ $* $# $? $$ $! $-
    r"|\$"                          # a bare `$`
)
# ORDER MATTERS: the quoting forms must precede the bare `\$` alternative,
# or `$'\x2d'` matches as a lone `$` and the rest survives as literal text.
#
# `$'...'` was NOT in the codex finding — it was found by adversarially
# probing this fix, and verified by EXECUTION before being treated as real:
# `python3 .claude/scripts/night$'\x2d'mode.py on` printed `TOGGLE RAN` on
# this platform. Bash decodes `\x2d` to `-`, so the token is the canonical
# path; `shlex` (which does not implement ANSI-C quoting) hands the walk a
# literal `night$-mode.py`, which matches nothing. Both quoting forms are
# the same class as `${X}` — text the SHELL assembles — so they belong in
# the same regex rather than in a rule of their own.
#
# The alternatives tolerate an escaped delimiter (`$'it\'s'`) on purpose: a
# `[^']*` that stopped early would leave a stray quote in the skeleton, and
# an unbalanced quote makes pass 2 unparseable — which returns ALLOW. That
# is the one direction a skeleton bug must not fail in.


def _e4_expansion_replacement(m):  # noqa: ANN001
    """What a single expansion becomes in the skeleton.

    `*` for anything whose value is decided at RUN time — that is the honest
    statement of what the hook knows.

    But the two QUOTING forms are not run-time values: `$'\\x2d'` and
    `$"-"` are static text sitting in the command, and their content is
    fully determined right here. Wildcarding them would throw that away and
    land below the glob literal floor: `python3 .claude/scripts/$'night-mode.py'`
    would skeletonise to `.claude/scripts/*` and be ALLOWED, even though
    nothing about it is uncertain. So they are DECODED instead — the
    skeleton keeps the text bash will actually use, and the literal rules
    match it exactly.

    Decoding failure falls back to `*`: less precise, but it widens the
    match rather than dropping it, which is the direction a matcher may
    fail in.
    """
    tok = m.group(0)
    if tok.startswith("$'"):
        body = tok[2:-1]
        try:
            # `unicode_escape` covers the ANSI-C escapes that matter for a
            # path: \xNN, \NNN octal, \\, \n, \t. Bash's set is larger
            # (\uNNNN, \cX); anything it cannot decode falls back to `*`.
            decoded = body.encode("utf-8", "surrogateescape").decode("unicode_escape")
        except (UnicodeDecodeError, UnicodeEncodeError):
            return "*"
        return _e4_skeleton_safe(decoded)
    if tok.startswith('$"'):
        return _e4_skeleton_safe(tok[2:-1])   # locale translation — identity
    return "*"


def _e4_skeleton_safe(decoded):  # noqa: ANN001
    """Keep a decoded quoting form from inventing a WORD BOUNDARY.

    Codex S292 r5-B, found while re-probing the r5 fix against the existing
    negative controls. `echo ok$'\\n'python3 <toggle> on` is ONE argument to
    `echo` in bash — the newline is data inside a quoting form, and no
    command starts at `python3`. Decoding it literally put a real newline in
    the skeleton, `shlex` split there, and `python3` appeared as a
    free-standing token. The old walk never noticed (everything after
    `echo` was ignored); the r5 interpreter hop reads those tokens, so the
    artefact surfaced as a false positive on a control that exists to pin
    exactly this property.

    The skeleton is a model of what the SHELL produces. Bash keeps the word
    together, so the model must too: every whitespace character in the
    decoded text becomes `?`, one glob character for one character. Length
    is preserved, so the glob literal floor still applies, and `?` matches
    whatever bash would have put there — the widening direction.

    Consequence, recorded rather than hidden: `python3 .claude/scripts/night$'\\n'mode.py`
    now skeletonises to `night?mode.py` and is DENIED, though bash would name
    a file with a newline in it, not the toggle. A fail-closed over-block on
    a shape no real workflow writes, versus a token boundary the shell never
    makes — this is the safe side to be wrong on.
    """
    if not decoded:
        return decoded
    return "".join("?" if _c.isspace() else _c for _c in decoded)


def _e4_globify_expansions(text):  # noqa: ANN001
    """Replace every shell expansion with a `*` wildcard.

    CODEX S292 REVIEW ROUND 3 (P1 — expansion-built toggle paths). The
    execution-position check recognised LITERAL paths, and variables whose
    ASSIGNED value was already the complete toggle path. It did not recognise
    a token the shell ASSEMBLES into the toggle path at expansion time:

        X=; python3 .claude/scripts/night${X}-mode.py on

    returned ALLOW. Bash expands `${X}` to the empty string, runs the
    canonical file, and the script's self-path guard accepts it because it IS
    the canonical file.

    A hook cannot evaluate expansions, so the answer is fail-CLOSED on the
    SHAPE (CLAUDE.md §"fail-closed on input"; precedent: the `_e3`
    whole-command parse gate, PLAN-152 debate C4). `*` is the right stand-in
    because it is exactly the claim being made — "the shell may put ANY text
    here" — and it lands the question in the glob machinery the matcher
    already has, LITERAL FLOOR included. That floor is load-bearing in the
    OTHER direction: `python3 $SCRIPT` skeletonises to `python3 *`, which
    names every script in the tree and so names none of them, and stays
    ALLOWED. Without it this rule would deny most variable-driven interpreter
    calls in the repo — a fail-closed gate turned into a lockout.

    Runs collapse (`$A$B` -> `*`), because `**` is not a stronger claim than
    `*` and `fnmatch` would only pay for it.
    """
    out = _E4_EXPANSION_RE.sub(_e4_expansion_replacement, text)
    while "**" in out:
        out = out.replace("**", "*")
    return out


# Appended to a deny raised on the EXPANSION SKELETON rather than on the text
# the operator typed. Without it the message quotes a token (`night*-mode.py`)
# that appears nowhere in their command — an accurate deny that reads like a
# bug. The `!` rail and the `night-mode` name stay in the base message, so the
# recovery route survives the suffix.
_E4_EXPANSION_NOTE = (
    " [matched on the EXPANSION SKELETON: the token carries a shell expansion, "
    "and with the expansion replaced by a wildcard it still names the toggle — "
    "so the shell can resolve it there. A hook cannot evaluate expansions, so "
    "this shape is refused rather than guessed at.]"
)


# Appended to a deny raised on a token whose BRACES the shell rewrites before
# anything runs. Same problem `_E4_EXPANSION_NOTE` solves and the same shape of
# answer: without it the message quotes `.claude/scripts/night-mode.p{y..y}`,
# which is not a path anyone can `ls`, and the operator has no way to see that
# the guard read it exactly as bash does.
_E4_BRACE_NOTE = (
    " [BRACE EXPANSION: the shell rewrites this token into its expanded words "
    "BEFORE running anything, and one of those words IS the guarded path — so "
    "this command runs the toggle even though the toggle is not spelled in it.]"
)

# The budget twin. Distinct wording because the claim is genuinely weaker: the
# guard did not find the toggle, it ran out of enumeration budget and refused
# to guess (CLAUDE.md §"fail-closed on input").
_E4_BRACE_BUDGET_NOTE = (
    " [BRACE EXPANSION: this token expands to more words than the guard "
    "enumerates, so whether one of them is the guarded path cannot be decided "
    "here — the shape is refused rather than guessed at. Spell the path you "
    "actually mean and the command is judged on its merits.]"
)


def _e4_brace_note(spelled) -> str:  # noqa: ANN001
    """The brace note a deny on ``spelled`` has earned, or ''.

    Recomputes the expansion. That is deliberate: this runs ONLY on the deny
    path (once, for a command that is about to be refused), and the
    alternative — threading a second return value through eight call sites —
    would widen the blast radius of this patch across the whole walk to save
    microseconds nobody is spending.
    """
    if not spelled or "{" not in spelled:
        return ""
    matched, undecidable = _e4_brace_names_toggle(spelled)
    if matched:
        return _E4_BRACE_NOTE
    if undecidable:
        return _E4_BRACE_BUDGET_NOTE
    return ""


def _e4_deny_reason(spelled, expansion=False) -> str:  # noqa: ANN001
    if expansion:
        return _e4_deny_reason(spelled) + _E4_EXPANSION_NOTE
    return (
        "GOVERNANCE: this bash command INVOKES the night-mode posture toggle "
        f"({spelled!r}). Arming or disarming the autonomy posture is a HUMAN "
        "action (PLAN-165 OQ1-redo, Owner-ratified 2026-08-03) — the model "
        "rail does not run it. Ask the operator to run it themselves with the "
        "`!` prefix (`! python3 .claude/scripts/night-mode.py on|off|status`) "
        "or from a terminal. Reading the file (cat/grep/git) is unaffected."
    ) + _e4_brace_note(spelled)


def _e4_alias_deny_reason(spelled, expansion=False) -> str:  # noqa: ANN001
    """Deny reason for CREATING an executable alias of the toggle.

    Distinct from `_e4_deny_reason` on purpose: nothing was invoked, so a
    message saying "this INVOKES the toggle" would be false, and the operator
    needs to know WHY a plain `ln` was refused. Still names the `!` rail — an
    operator who genuinely wants the convenience link may make it themselves.
    """
    if expansion:
        return _e4_alias_deny_reason(spelled) + _E4_EXPANSION_NOTE
    return (
        "GOVERNANCE: this bash command creates an executable ALIAS of the "
        f"night-mode posture toggle ({spelled!r}). A link is a second live "
        "entry point: running it re-anchors the script in this repository "
        "(`Path(__file__).resolve()` follows the link) and arms the posture "
        "without ever spelling the guarded path. Arming or disarming the "
        "autonomy posture is a HUMAN action (PLAN-165 OQ1-redo, "
        "Owner-ratified 2026-08-03). Ask the operator to run the toggle "
        "themselves with the `!` prefix "
        "(`! python3 .claude/scripts/night-mode.py on|off|status`). Copying "
        "the file (`cp`) is unaffected — a copy is inert, the script refuses "
        "to run from anywhere but its canonical path."
    ) + _e4_brace_note(spelled)


def _e4_check_posture_toggle_invocation(command: str) -> Optional[str]:
    """Return a deny reason if ``command`` RUNS a posture-toggle script.

    Pure (no I/O beyond the module-level regexes); safe to call on every
    command. See the block comment above for the `_e3` division of labour.

    TWO PASSES over the same walk (codex S292 r3 P1 — expansion-built paths):

      1. the LITERAL pass, on the newline-normalised command. Owns every rule
         that reads the text as written, including the `$(…)`-in-execution-
         position rule, whose whole point is that the substitution is visible.
      2. the EXPANSION-SKELETON pass, run ONLY if pass 1 allowed and only when
         the command carries an expansion at all. Every `${X}` / `$(…)` /
         `` `…` `` becomes `*`, and the SAME walk asks whether the shell could
         still land on the toggle there.

    Order is load-bearing in both directions and pinned by
    ``test_expansion_skeleton_does_not_shadow_the_literal_pass``: pass 1 must
    run first so `python3 $(echo <toggle>) on` keeps its precise message (its
    skeleton, `python3 *`, is deliberately allow-shaped), and pass 2 must run
    at all so `python3 .claude/scripts/night${X}-mode.py on` is refused.

    Cost: pass 2 tokenizes a second time, and only for commands containing a
    `$` or a backtick. One shlex pass measured 19-39us against the PLAN-089 §4
    AC8 budget of p95 < 50ms per command — see the note in `_e4_scan`.
    """
    if not command:
        return None

    text = _e4_normalise_command(command)
    reason = _e4_scan(text)
    if reason is not None:
        return reason

    if "$" in text or "`" in text:
        skeleton = _e4_globify_expansions(text)
        if skeleton != text:
            return _e4_scan(skeleton, expansion_pass=True)
    return None


def _e4_scan(command, expansion_pass=False):  # noqa: ANN001
    """One tokenize-and-walk over ``command``. See the orchestrator above.

    ``expansion_pass`` only changes the deny MESSAGE (and suppresses the
    unparseable-input branch, which pass 1 has already adjudicated) — the
    rules themselves are identical, which is the point: a skeleton is
    judged by the same execution-position discipline as real text, so a
    READ stays a read.
    """
    if not command:
        return None

    # NO raw-substring pre-filter (codex S292 P1-A). The first implementation
    # short-circuited on `basename in command`, which the SHELL defeats for
    # free: `night"-"mode.py`, `night''-mode.py`, `night\-mode.py` and
    # `NIGHT-MODE.PY` all name the real file while the raw string does not
    # contain the literal basename — every one returned ALLOW. Only the
    # TOKENIZED, normalised form can answer "does this run the toggle", so
    # the matcher now always tokenizes.
    #
    # Cost, measured on this repo (CPython 3.9.6, darwin): one `shlex` pass is
    # 19-39us on a `decide_command` that already spends 76-188us — and the
    # governing budget is the PLAN-089 §4 AC8 hook gate of p95 < 50ms per
    # command (test_check_bash_safety_canonical_matrix.py). The added pass is
    # ~0.06% of that budget, against a hook whose wall time is dominated by
    # process spawn. `_e3` above already tokenizes unconditionally with the
    # identical shlex configuration; sharing one memoized tokenizer between
    # the two would make the marginal cost ~zero, and was NOT done here on
    # purpose — it would put `_e3`'s whole matcher inside this patch's blast
    # radius for 25us that the budget does not need.
    try:
        _lx = shlex.shlex(command, posix=True, punctuation_chars="();<>|&`")
        _lx.whitespace_split = True
        tokens = list(_lx)
    except ValueError:
        # INPUT-parse failure → fail-CLOSED, but only for a command that
        # plausibly names the toggle (PLAN-152 debate C4). The gate is the
        # QUOTE/ESCAPE-STRIPPED, case-folded raw string: a broken command
        # cannot be walked, so this is the widest sound test available, and
        # it is the one shape where the raw scan is not defeatable by
        # concatenation. Commands that do NOT name the toggle return None so
        # they keep `_e3`'s own fail-closed parse message instead of a
        # confusing night-mode reason.
        #
        # NOT on the expansion pass: pass 1 saw the operator's real text and
        # already decided whether it parses. A skeleton that fails to parse
        # where the original did is an artefact of `*` substitution, not an
        # unparseable command, and denying on it would report a shape the
        # operator never wrote.
        if expansion_pass:
            return None
        flat = command.lower()
        for _ch in (chr(39), chr(34), "\\"):
            flat = flat.replace(_ch, "")
        if any(b in flat for b in _E4_TOGGLE_BASENAMES_FOLDED):
            return _e4_deny_reason("unparseable command naming the toggle")
        return None

    n = len(tokens)
    i = 0
    at_cmd_word = True      # index 0, and every token after a TERMINATOR
    chain_runner = None     # the prefix runner (exec/env/sudo/timeout/...) whose
                            # flags we are currently parsing. Flags and numeric
                            # operands before the real command word
                            # (`timeout 5 python3 …`, `nice -n 10 python3 …`)
                            # are part of the PREFIX, not of a new command.
    ambiguous = False       # the previous token was a flag the runner's table
                            # does not carry, so the NEXT token might be its
                            # value rather than the command word. Fail-closed:
                            # examine it as a command word AND keep scanning
                            # one position further (codex S292 P1-B).
    assigned_toggle = False  # a shell variable in THIS command holds the toggle
                             # path (`S=.claude/scripts/night-mode.py; …`). shlex
                             # does not expand `$S`, so the structural rules below
                             # cannot see through it. Used ONLY in conjunction
                             # with an execution position — `S=…; cat $S` stays
                             # ALLOWED, because reading is not invoking.
    while i < n:
        tok = tokens[i]
        if tok in _E3_TERMINATORS:
            at_cmd_word = True
            chain_runner = None
            ambiguous = False
            i += 1
            continue
        if tok in _E3_REDIRECTS:
            i += 2          # skip the redirect operator + its target
            continue
        if not at_cmd_word:
            # INTERPRETER HOP — the STRUCTURAL rail (codex S292 r5 P1).
            #
            # `xcrun python3 <toggle> on` was ALLOWED because `xcrun` is not
            # in `_E4_PREFIX_RUNNERS`, so the walk stopped at it and never
            # looked at `python3` again. Measured on this machine: it RUNS,
            # and the script's own NF-08b self-path guard PASSES for it (the
            # file executed is the canonical one), so this matcher is the
            # ONLY rail for the shape. `arch`, `caffeinate` and `script`
            # behaved identically, and the list had failed the same way twice
            # before (r2 `env`/`sudo`, r4 braces).
            #
            # So stop asking WHO launches and ask WHAT is launched: after an
            # unrecognised command word, keep testing every remaining token
            # of the segment for INTERPRETER family. The launcher's name
            # stops mattering — `<anything> python3 <toggle>` is denied.
            #
            # ONLY the family rule fires here, never the direct-exec, `$S` or
            # substitution rules. That is the line between an invocation and a
            # read: `cat <toggle>` and `xcrun <toggle>` are the SAME shape to
            # a string matcher (the shell runs the first word in both; only
            # the launcher's semantics differ), so applying the direct-exec
            # rule at hopped positions would deny every read of the file.
            # Direct exec through a launcher is covered — for the launchers
            # that could be measured — by `_E4_PREFIX_RUNNERS` instead.
            #
            # FALSE POSITIVE, accepted and bounded: an interpreter NAME used
            # as data in the same command as the toggle now denies, e.g.
            # `grep -n python3 <toggle>`. It cannot be told apart from
            # `xcrun python3 <toggle>` without knowing each command's
            # semantics. It costs one rewrite (`cat <toggle> | grep python3`),
            # it only ever fires on a command that already names the toggle,
            # and the deny message says what to do — while the other error
            # direction is a silent bypass of a rail three signed comments
            # claim is closed (CLAUDE.md §4: fail-CLOSED on matcher input).
            hop_family = _e4_runner_family(_e3_cmd_name(tok).lower())
            if hop_family is not None:
                hit = _e4_interpreter_deny(
                    tokens, i, hop_family, assigned_toggle, expansion_pass)
                if hit is not None:
                    return hit
            i += 1
            continue
        if _ENV_ASSIGNMENT_RE.match(tok):
            if _e4_is_toggle_path(tok.split("=", 1)[1]):
                assigned_toggle = True
            i += 1          # leading NAME=VALUE — the command word is still ahead
            continue
        if chain_runner is not None and tok.startswith("-"):
            # Resolve the runner chain instead of stopping at the first
            # non-flag token: `env -u FOO python3 <toggle>` used to read FOO
            # as the command word and never look at python3 again.
            _vals, _bools = _E4_PREFIX_RUNNER_FLAGS.get(
                chain_runner, (frozenset(), frozenset()))
            kind = _e4_classify_prefix_flag(tok, _vals, _bools)
            if kind == "value" and i + 1 < n:
                i += 2      # the next token is this flag's VALUE, not a command
                continue
            ambiguous = kind == "unknown"
            i += 1
            continue
        if chain_runner is not None and _E4_DURATION_RE.match(tok):
            i += 1          # `timeout 5 …` / `nice 10 …` — a prefix operand
            continue
        # CASE-FOLDED, for the same reason the PATH is (see
        # `_e4_runner_family`): PATH lookup is case-insensitive on APFS, so
        # `PYTHON3`/`SUDO`/`ENV` name the real binaries.
        name = _e3_cmd_name(tok).lower()
        if name in _E4_PREFIX_RUNNERS:
            chain_runner = name
            ambiguous = False
            i += 1
            continue
        if _e4_is_toggle_path(tok):
            return _e4_deny_reason(tok, expansion_pass)  # direct exec: `./…/night-mode.py on`
        if assigned_toggle and "$" in tok:
            return _e4_deny_reason(tok, expansion_pass)  # `S=…; $S on`
        if tok in _E4_SUBST_OPENERS and _e4_substitution_body_names_toggle(tokens, i):
            # `$(echo …/night-mode.py) on` — substitution IN COMMAND POSITION.
            return _e4_deny_reason(tok, expansion_pass)
        if name in _E4_LINK_RUNNERS:
            # `ln [-s] <toggle> <alias>` — creating a second entry point.
            # BOTH operand positions matter: source (the bypass) and target
            # (replacing the toggle with a link, which `_e3` also denies as a
            # write). Flags cannot match `_e4_is_toggle_path`, so the segment
            # positionals are scanned as-is; no flag table is needed.
            for operand in _e3_segment_positionals(tokens, i + 1):
                if _e4_is_toggle_path(operand):
                    return _e4_alias_deny_reason(operand, expansion_pass)
                if assigned_toggle and "$" in operand:
                    return _e4_alias_deny_reason(operand, expansion_pass)  # `S=…; ln -s $S X`
            at_cmd_word = False
            chain_runner = None
            i += 1
            continue
        family = _e4_runner_family(name)
        if family is not None:
            hit = _e4_interpreter_deny(
                tokens, i, family, assigned_toggle, expansion_pass)
            if hit is not None:
                return hit
            at_cmd_word = False
            chain_runner = None
            i += 1
            continue
        if ambiguous:
            # This token followed a flag the table does not know, so it may
            # be that flag's VALUE and the command word may still be ahead.
            # One unknown flag buys exactly one extra candidate position —
            # enough to catch `env --frobnicate VAL python3 <toggle>` without
            # walking off into the settled command's own arguments (which is
            # what would false-positive on `sudo -u root cat <toggle>`).
            ambiguous = False
            i += 1
            continue
        at_cmd_word = False
        chain_runner = None
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

    # PLAN-165 NF-08 — posture-toggle INVOCATION guard (OQ1-redo). Not
    # `destructive=True`: this block is a governance boundary, not a
    # destructive-command class, so the ADR-175 citation gate must never be
    # able to release it.
    toggle_reason = _e4_check_posture_toggle_invocation(command)
    if toggle_reason is not None:
        return Decision(allow=False, reason=toggle_reason)

    # PLAN-133 A1 — optional env-hijack denylist; pure decision.
    if _env_guard_enforced():
        env_hit = _check_env_hijack(command)
        if env_hit is not None:
            _hijack_class, _key, reason = env_hit
            return Decision(allow=False, reason=reason)

    # PLAN-124 WS-1 — git bypass guard runs before destructive checks.
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

    from _lib import bash_indirect_guard as _indirect_guard
    try:
        _indirect_switch = _trusted_env.get_trusted("CEO_BASH_INDIRECT_GUARD")
        _heuristic_switch = _trusted_env.get_trusted("CEO_BASH_INDIRECT_HEURISTICS")
    except Exception:  # no trusted snapshot -> safety default ON
        _indirect_switch = None
        _heuristic_switch = None
    indirect_hit = None if _indirect_switch == "0" else _indirect_guard.scan(
        command, heuristics=_heuristic_switch != "0"
    )
    if indirect_hit is not None:
        _is_destructive = indirect_hit.reason_code != "bash_computed_canonical_target"
        return Decision(allow=False, reason=indirect_hit.reason,
                        destructive=_is_destructive, reason_code=indirect_hit.reason_code)
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
