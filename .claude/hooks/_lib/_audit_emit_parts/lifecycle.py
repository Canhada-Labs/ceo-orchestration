"""Lifecycle.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('emit_pair_rail_review_expected', 'emit_directory_added_recorded', 'emit_notification_lifecycle', 'emit_night_mode_toggled')

# QDSAA-FUNCAO-LONGA: Preserve the existing event schema and its field coercion together during relocation.
def emit_pair_rail_review_expected(
    *,
    session_id: str,
    tool_name: str = "unknown",
    file_path_hash_prefix: str = "",
    review_id: str = "",
    timeout_ms: int = 0,
    project: str = "",
) -> None:
    """Emit pair_rail_review_expected (PLAN-161 W2 C5 / CF-9 denominator).

    Fired by `check_pair_rail.py:_decide()` at the point a canonical-edit
    Codex review is definitely ENTERED — only after the kill-switch,
    non-write-tool, not-L3+ and sentinel-bypass arms have all returned. It is
    the durable session-correlated DENOMINATOR for the /ceo-boot `pair_rail`
    activity-conditioned liveness row: a window session with
    expected-but-no-outcome is the S254 dead-rail class and must escalate,
    and a healthy outcome from session B must never mask session A
    (`session_id` is therefore an explicit required kwarg — the hook threads
    the Stop/PreToolUse event's own session id, not a default).

    r5 F2 + r6 F2: `review_id` (EXACTLY 16 lowercase hex or exactly "";
    the RAW value is validated BEFORE any bounding — off-shape incl.
    oversize is DROPPED to "", never truncated, so two distinct off-shape
    ids sharing a 16-hex prefix can never alias to one pairing key) is
    the PER-INVOCATION correlation key — minted by
    `check_pair_rail.py:_decide()` at review entry (`os.urandom(8).hex()`)
    and identical on this emit and the same invocation's `pair_rail_case`.
    It is what makes the /ceo-boot pairing invocation-EXACT: counting
    (even the r4 (session, file-hash) BUCKET counting) fundamentally
    cannot pair a specific expected with its OWN case — an old completed
    case for the SAME (session, file) offset a later dead expected 1:1.
    An expected `review_id` with no matching `pair_rail_case` in-window is
    an outstanding (dead) review -> RED.

    r4 F2 (retained as legacy fallback + harmless secondary key):
    `file_path_hash_prefix` (the SAME 16-hex SHA-256 path-prefix
    token `pair_rail_case` carries, computed by the hook with the same
    helper; bounded shape `[0-9a-f]{0,16}`, off-shape COERCED to "") keys
    the /ceo-boot expected/terminal pairing per (session, file-hash)
    BUCKET for id-less (pre-land / fail-open no-id) events only.

    ADR-110-AMEND-2 §1.6: `timeout_ms` is the EFFECTIVE post-clamp codex
    budget the paired review ran under, as INTEGER MILLISECONDS (bounded
    `[0, 6_000_000]`, off-shape COERCED to 0 = "unknown budget"). It is
    NOT float seconds: `canonical_json` forbids floats in HMAC-covered
    fields, and the failure is not benign — the spool writer drops the
    WHOLE event with only an `audit-log.errors` breadcrumb, which for
    these two actions would manufacture the very /ceo-boot liveness
    deficit they exist to measure. Same encoding + rationale as
    `dispatcher_route.wall_clock_ms`; divide by 1000 to recover seconds.
    Its purpose is §4(i): before it existed, a session exporting
    `CEO_PAIR_RAIL_TIMEOUT_S=5` produced a case F byte-indistinguishable
    from a genuine Codex outage — the quiet knob was stealthier than the
    documented kill-switch.

    Deny-by-default: the ONLY caller fields are `session_id` + the
    closed-enum `tool_name` (off-enum COERCED to "unknown") + the bounded
    `file_path_hash_prefix` + the bounded `review_id` + the bounded
    integer `timeout_ms`. Raw file paths and
    content bodies are NEVER persisted. Fail-open per audit_emit contract.
    NEVER routes through _EMIT_GENERIC_PASSTHROUGH.
    """
    safe_tool = (
        tool_name
        if tool_name in _PAIR_RAIL_REVIEW_EXPECTED_TOOL_ENUM
        else "unknown"
    )
    _raw_prefix = (file_path_hash_prefix or "")[:16]
    safe_prefix = (
        _raw_prefix
        if (isinstance(_raw_prefix, str)
            and _PAIR_RAIL_FILE_HASH_PREFIX_RE.fullmatch(_raw_prefix))
        else ""
    )
    # r6 F2 — validate the RAW value (no [:16] truncate-before-validate:
    # truncation collapsed distinct oversize ids to one 16-hex key).
    _raw_rid = review_id if isinstance(review_id, str) else ""
    safe_rid = (
        _raw_rid if _PAIR_RAIL_REVIEW_ID_RE.fullmatch(_raw_rid) else ""
    )
    raw_event: Dict[str, Any] = {
        "action": "pair_rail_review_expected",
        "session_id": session_id,
        "project": project,
        "tool_name": safe_tool,
        "file_path_hash_prefix": safe_prefix,
        "review_id": safe_rid,
        # ADR-110-AMEND-2 §1.6 — bounded integer ms, never float seconds.
        "timeout_ms": _coerce_pair_rail_timeout_ms(timeout_ms),
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _PAIR_RAIL_REVIEW_EXPECTED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"pair_rail_review_expected dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_directory_added_recorded(
    *,
    source: str,
    directory_hash_prefix: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit directory_added_recorded (PLAN-163 T3.1 / ADR-183).

    Fired by `check_directory_added.py` (the DirectoryAdded observer, CC
    2.1.220) once per workspace root the harness adds mid-session. The
    event is NOTIFICATION-ONLY on 2.1.220 — permission/sandbox already
    include the directory BEFORE the hook dispatches — so this row is the
    POST-FACTO forensic record that the session's read+write surface grew
    (the auditability half the harness does not provide).

    Sec MF-3 field-safety rationale (why each field is safe to sign):

      source                 — CLOSED enum {slash_command,
                               register_repo_root, session_start_snapshot,
                               other}; an unrecognized value is COERCED to
                               "other" and NEVER echoed. The wire carries
                               the first two; `session_start_snapshot` is
                               reserved for the --add-dir-at-LAUNCH blind
                               spot (the launch flag never fires the
                               event — a SessionStart roots snapshot is
                               the only producer that can cover it).
      directory_hash_prefix  — exact 12-lowercase-hex sha256 prefix of
                               the ABSOLUTE path, or ""; a hash prefix
                               identifies recurrence without disclosing
                               the path (LLM06 side-channel guard — same
                               12-hex token class as
                               message_sha256_prefix, and the exact
                               length the producer's _hash_prefix()
                               computes). RAW value validated; off-shape
                               incl. oversize is DROPPED to "", never
                               truncated.
      session_id / project   — baseline correlation scalars, envelope-
                               allowed on every action.

    DENIED on the wire: the raw `directory` path (or any substring of
    it), cwd, transcript_path — a directory path can carry usernames,
    client names, or project identity. Deny-by-default allowlist
    `_DIRECTORY_ADDED_RECORDED_ALLOWLIST` enforced; fail-open per
    audit_emit contract (exceptions swallowed by _write_event). NEVER
    routes through _EMIT_GENERIC_PASSTHROUGH.
    """
    safe_source = (
        source
        if isinstance(source, str) and source in _DIRECTORY_ADDED_SOURCE_ENUM
        else "other"
    )
    _raw_prefix = (
        directory_hash_prefix if isinstance(directory_hash_prefix, str) else ""
    )
    safe_prefix = (
        _raw_prefix
        if _DIRECTORY_ADDED_HASH_PREFIX_RE.fullmatch(_raw_prefix)
        else ""
    )
    raw_event: Dict[str, Any] = {
        "action": "directory_added_recorded",
        "session_id": session_id,
        "project": project,
        "source": safe_source,
        "directory_hash_prefix": safe_prefix,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _DIRECTORY_ADDED_RECORDED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"directory_added_recorded dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


def emit_notification_lifecycle(
    *,
    notification_type: str,
    has_title: bool = False,
    message_sha256_prefix: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit notification_lifecycle (PLAN-163 T3.2 / ADR-183).

    Fired by `check_notification.py` (pure observer on the CC 2.1.220
    Notification event) once per notification the harness surfaces —
    the durable record of the agent-attention lifecycle
    (needs-input / completed / permission-request) that /ceo-boot
    liveness telemetry can pivot without a transcript.

    Sec MF-3 field-safety rationale (why each field is safe to sign):

      notification_type      — CLOSED vocabulary {agent_needs_input,
                               agent_completed, permission_request,
                               other}. The harness enum is OPEN (any
                               string can arrive on the wire), so an
                               unrecognized value is COERCED to "other"
                               and NEVER echoed — the raw type string
                               could otherwise smuggle free text into
                               the signed chain.
      has_title              — strict bool (presence signal only; the
                               title TEXT never leaves the process).
      message_sha256_prefix  — exact 12-lowercase-hex sha256 prefix of
                               the message body, or "" (absent/empty
                               message). A hash prefix supports
                               recurrence/dedupe analysis without
                               disclosing content. RAW value validated;
                               off-shape incl. oversize is DROPPED to
                               "", never truncated.
      session_id / project   — baseline correlation scalars, envelope-
                               allowed on every action.

    DENIED on the wire: `message` and `title` TEXT in any form — a
    notification message can quote tool output, file paths, or secrets
    (no-value-echo, S172 doctrine). Deny-by-default allowlist
    `_NOTIFICATION_LIFECYCLE_ALLOWLIST` enforced; fail-open per
    audit_emit contract (exceptions swallowed by _write_event). NEVER
    routes through _EMIT_GENERIC_PASSTHROUGH.
    """
    safe_type = (
        notification_type
        if isinstance(notification_type, str)
        and notification_type in _NOTIFICATION_TYPE_ENUM
        else "other"
    )
    _raw_msg_prefix = (
        message_sha256_prefix
        if isinstance(message_sha256_prefix, str)
        else ""
    )
    safe_msg_prefix = (
        _raw_msg_prefix
        if _NOTIFICATION_MSG_SHA256_PREFIX_RE.fullmatch(_raw_msg_prefix)
        else ""
    )
    raw_event: Dict[str, Any] = {
        "action": "notification_lifecycle",
        "session_id": session_id,
        "project": project,
        "notification_type": safe_type,
        "has_title": bool(has_title),
        "message_sha256_prefix": safe_msg_prefix,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _NOTIFICATION_LIFECYCLE_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"notification_lifecycle dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )


# QDSAA-FUNCAO-LONGA: Preserve the existing event schema and its field coercion together during relocation.
def emit_night_mode_toggled(
    *,
    mode: str,
    result: str,
    previous_mode: str = "absent",
    hostname_hash: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit night_mode_toggled (PLAN-165 P2; ADR per PLAN-165 T1.6).

    Fired by `.claude/scripts/night-mode.py` — the SINGLE writer of the
    per-machine autonomy-posture overlay `.claude/settings.local.json`
    (the PLAN-165 P1 deny rule closes the tool Edit/Write path to it) —
    once per `on` / `off` invocation, whether applied, idempotent-noop,
    refused, or failed. This row is the forensic record PLAN-165 AC-7
    requires: without it a posture flip between sessions is invisible to
    the HMAC chain (the overlay is NOT in _CANONICAL_GUARDS, so no
    PostToolUse observer covers it — v1's claim that one did was false).

    Sec MF-3 field-safety rationale (why each field is safe to sign):

      mode           — CLOSED enum {acceptEdits, manual, absent, other};
                       the posture the invocation wrote (on ->
                       acceptEdits; off -> manual, or absent when the
                       key was removed). An unrecognized value is
                       COERCED to "other" and NEVER echoed.
      previous_mode  — same CLOSED enum; the snapshotted posture the
                       write replaced ("absent" when the overlay had no
                       defaultMode key).
      result         — CLOSED enum {applied, noop, refused, failed,
                       other}; invocation outcome (refused covers the
                       CI guard and the malformed-input fail-closed
                       exit).
      hostname_hash  — exact 12-lowercase-hex sha256 prefix of the
                       machine hostname, or ""; identifies per-machine
                       recurrence without disclosing the hostname
                       (LLM06 side-channel guard — same 12-hex token
                       class as directory_hash_prefix). RAW value
                       validated; off-shape incl. oversize is DROPPED
                       to "", never truncated.
      session_id / project — baseline correlation scalars, envelope-
                       allowed on every action.

    DENIED on the wire: the overlay PATH, the settings file CONTENT
    (before or after), the marker content, the RAW hostname — settings
    JSON and paths can carry usernames, allowlists, and project
    identity. Deny-by-default allowlist `_NIGHT_MODE_TOGGLED_ALLOWLIST`
    enforced; fail-open per audit_emit contract (exceptions swallowed by
    _write_event). NEVER routes through _EMIT_GENERIC_PASSTHROUGH.
    """
    safe_mode = (
        mode
        if isinstance(mode, str) and mode in _NIGHT_MODE_MODE_ENUM
        else "other"
    )
    safe_prev = (
        previous_mode
        if isinstance(previous_mode, str)
        and previous_mode in _NIGHT_MODE_MODE_ENUM
        else "other"
    )
    safe_result = (
        result
        if isinstance(result, str) and result in _NIGHT_MODE_RESULT_ENUM
        else "other"
    )
    _raw_hh = hostname_hash if isinstance(hostname_hash, str) else ""
    safe_hh = (
        _raw_hh
        if _NIGHT_MODE_HOSTNAME_HASH_RE.fullmatch(_raw_hh)
        else ""
    )
    raw_event: Dict[str, Any] = {
        "action": "night_mode_toggled",
        "session_id": session_id,
        "project": project,
        "mode": safe_mode,
        "previous_mode": safe_prev,
        "result": safe_result,
        "hostname_hash": safe_hh,
    }
    cleaned, dropped = _scrub_ceo_boot_event(
        raw_event, _NIGHT_MODE_TOGGLED_ALLOWLIST
    )
    _write_event(cleaned)
    if dropped:  # pragma: no cover — impossible from the typed wrapper
        _breadcrumb(
            f"night_mode_toggled dropped forbidden field(s): "
            f"{sorted(dropped)[:10]}"
        )
