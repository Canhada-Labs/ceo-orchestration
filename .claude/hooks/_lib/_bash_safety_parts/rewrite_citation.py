"""Force-push rewrite and destructive citation checks."""
from __future__ import annotations

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
