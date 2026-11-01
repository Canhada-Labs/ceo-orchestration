"""Fact-gate state, storage, and enforcement declarations."""
from __future__ import annotations

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
    value) else ``$HOME/.claude/projects/<native-slug>``."""
    import os as _os
    env_dir = _os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    home = _os.environ.get("HOME") or str(Path.home())
    return _rp_state_dir()


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
