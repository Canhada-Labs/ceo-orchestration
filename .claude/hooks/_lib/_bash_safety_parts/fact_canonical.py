"""Fact-gate continuation and canonical-path checks."""
from __future__ import annotations

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
