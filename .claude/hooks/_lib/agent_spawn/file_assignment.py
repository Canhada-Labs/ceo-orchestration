"""Spawn tool scope, depth and file-assignment enforcement.

Bound to the public hook namespace by this package at import time.
"""
from __future__ import annotations

_OVERLAP_LOOKBACK_S = 600          # 10-minute concurrency window

__all__ = (
    '_OVERLAP_LOOKBACK_S',
    '_fa_suffix_has_authority',
    '_fa_list_line_allowed',
    '_parse_tool_allowlist',
    '_requested_tools',
    '_check_tool_scope',
    '_spawn_depth',
    '_classify_file_assignment',
    '_parse_file_assignment',
    '_path_hash',
    '_recent_file_assignments',
    '_enforce_spawn_rails',
    '_emit_tool_scope_violation',
    '_emit_depth_or_overlap',
    '_emit_file_assignment_recorded',
)


def _fa_suffix_has_authority(suffix: str) -> bool:
    """True when the prose suffix carries a bare authority word."""
    for tok in suffix.split():
        if "/" in tok or "." in tok:
            continue  # path-like token — filename parts are not authority
        if tok.strip(";:,()[]{}'\"!?-").lower() in _FA_AUTHORITY_WORDS:
            return True
    return False



def _fa_list_line_allowed(line: str) -> bool:
    """Closed whitelist for list lines inside a FILE ASSIGNMENT block.

    Anchored semantics (codex r33+r34 P1): a PROSE form may not smuggle
    ANY edit grant in its suffix — `- MAY read docs; MUST edit x` and
    `- If you need permission: CAN edit: x` are tainted, not laundered.
    Each prose prefix consumes its own `edit` (when it has one); any
    FURTHER `edit` word after the matched prefix rejects the line.
    """
    if _FA_ALLOWED_GRANT_LINE_RE.match(line):
        return True
    m = _FA_ALLOWED_PROSE_LINE_RE.match(line)
    if m:
        return not _fa_suffix_has_authority(line[m.end():])
    return False



def _parse_tool_allowlist(prompt: str) -> Optional[frozenset]:
    """Return the declared lowercase tool allow-list, or None if no
    `## TOOL ALLOW-LIST` block is present (= unrestricted, back-compat).

    Pure. Never raises. Bounded to the block between its header and the next
    `##` heading. Only KNOWN tool names are retained; unknown tokens dropped
    (so a typo cannot create a phantom allow-list that blocks everything).
    """
    if not prompt:
        return None
    sanitized = _strip_fenced_and_comments(prompt)
    m = _TOOL_ALLOWLIST_HEADER_RE.search(sanitized)
    if m is None:
        return None
    block_start = m.end()
    nxt = _NEXT_H2_RE.search(sanitized, block_start)
    block = sanitized[block_start: nxt.start() if nxt else len(sanitized)]
    allowed = set()
    for bm in _TOOL_BULLET_RE.finditer(block):
        for tok in bm.group(1).replace(",", " ").split():
            t = tok.strip().lower()
            if t in _KNOWN_TOOL_NAMES:
                allowed.add(t)
    # An empty-but-present block = "deny all known tools" (intentional).
    return frozenset(allowed)



def _requested_tools(prompt: str) -> frozenset:
    """Heuristic set of KNOWN tools this spawn appears to request.

    First-hit per family, bounded scan. Conservative (high-signal verbs only).
    Pure; never raises.
    """
    if not prompt:
        return frozenset()
    text = _strip_fenced_and_comments(prompt)[:_TOOL_SCAN_WINDOW].lower()
    out = set()
    for tool, hints in _TOOL_REQUEST_HINTS:
        if any(h in text for h in hints):
            out.add(tool)
    return frozenset(out)



def _check_tool_scope(
    prompt: str,
) -> Optional[Tuple[str, str]]:
    """Rail 1. Return (reason_code, detail) if a requested tool is OUTSIDE
    the declared allow-list, else None.

    `detail` NEVER contains a path or the raw prompt — only the offending
    tool NAME(s) (a closed-enum-safe value) + counts. No-value-echo safe.
    """
    allow = _parse_tool_allowlist(prompt)
    if allow is None:
        return None  # no declared scope -> unrestricted (back-compat)
    requested = _requested_tools(prompt)
    out_of_scope = sorted(requested - allow)
    if not out_of_scope:
        return None
    return (
        "spawn_tool_out_of_scope",
        f"tools={','.join(out_of_scope)} declared={len(allow)}",
    )



def _spawn_depth(prompt: str, env: Dict[str, str]) -> int:
    """Best-effort current spawn depth. 0 = top-level CEO spawn.

    Two independent signals, max() wins (fail-toward-detection):
      - `## SUBAGENT-CONTEXT depth=N` marker in the prompt (CEO-injected when
        delegating to a sub-agent that may itself coordinate).
      - `CEO_SPAWN_DEPTH` env breadcrumb (harness/CEO-set).
    Pure-ish (reads env dict only). Never raises.
    """
    depth = 0
    try:
        m = _SUBAGENT_DEPTH_MARKER_RE.search(prompt or "")
        if m:
            depth = max(depth, int(m.group(1)))
    except Exception:  # pragma: no cover - fail-open
        pass
    try:
        raw = (env.get("CEO_SPAWN_DEPTH") or "").strip()
        if raw.isdigit():
            depth = max(depth, int(raw))
    except Exception:  # pragma: no cover - fail-open
        pass
    return depth



def _classify_file_assignment(prompt: str) -> Tuple[str, frozenset]:
    """Classify the spawn's `## FILE ASSIGNMENT` declaration (PLAN-178 C1).

    Returns ``(state, concrete_paths)`` with ``state`` in a closed enum:

    - ``"absent"``      — no `## FILE ASSIGNMENT` header in the sanitized
      prompt (fenced/comment content never counts — same masking rule as
      every other block parser in this hook).
    - ``"concrete"``    — >=1 concrete `CAN edit:` path AND zero dropped
      tokens (codex r15 P1: `safe.py, src/**` must NOT classify concrete —
      the agent still READS the wildcard grant while telemetry records
      only the concrete path; any dropped token taints the whole
      declaration to unparseable).
    - ``"readonly"``    — explicit `CAN edit: NONE-READ-ONLY` and no
      concrete path. Case-insensitive token match; conformant.
    - ``"unparseable"`` — header(s) present but no concrete path and no
      explicit read-only token (wildcard-only / placeholder-only / empty
      block). Named rejection under enforce (ADR-191 §1, B nice-4).

    ALL `## FILE ASSIGNMENT` blocks in the prompt are aggregated (codex
    r2 P1, Lote B): the canonical generator emits an unconditional block
    and documented caller flows (/spawn, /debate) APPEND their own
    concrete block afterwards — reading only the first block would hide
    the writer's paths from overlap telemetry AND enforcement. Union of
    concrete paths wins over a read-only declaration in any block.

    Pure. Never raises. Bounded to _OVERLAP_MAX_PATHS.
    """
    if not prompt:
        return ("absent", frozenset())
    # CommonMark-correct fence mask FIRST (raw prompt), THEN the shared
    # comment/fence stripper — order matters: the shared toggle-masker
    # mis-parses length/type-mismatched fences (codex r35 P1).
    sanitized = _FA_FENCE_RE.sub("", prompt)
    sanitized = _strip_fenced_and_comments(sanitized)
    # Unclosed HTML comment extends to EOF (codex r39 P2): the shared
    # stripper removes only CLOSED <!-- --> pairs — an unclosed opener
    # would leave commented-out content visible to this classifier.
    _oc = sanitized.find("<!--")
    if _oc != -1 and "-->" not in sanitized[_oc:]:
        sanitized = sanitized[:_oc]
    headers = list(_FILE_ASSIGNMENT_HEADER_RE.finditer(sanitized))
    # Block bound recognizes 0-3-space-indented H2 too (codex r33 P2) —
    # otherwise an indented `## TASK` leaves task bullets INSIDE the
    # assignment parser. Local to this classifier.
    _fa_next_h2 = re.compile(r"^[ ]{0,3}##[ \t]", flags=re.MULTILINE)
    if not headers:
        return ("absent", frozenset())
    paths = set()
    readonly_declared = False
    invalid_seen = False
    for m in headers:
        block_start = m.end()
        nxt = _fa_next_h2.search(sanitized, block_start)
        block = sanitized[
            block_start: nxt.start() if nxt else len(sanitized)
        ]
        block_had_line = False
        for list_line in _FA_LIST_LINE_RE.finditer(block):
            if not _fa_list_line_allowed(list_line.group(0)):
                # Structural rule (codex r25→r32): an unrecognized list
                # line inside the block is authority/instruction the
                # parser did not validate — taint, whatever its phrasing.
                invalid_seen = True
        for lm in _CAN_EDIT_LINE_RE.finditer(block):
            block_had_line = True
            for raw in lm.group(1).split(","):
                p = raw.strip().strip("`").strip()
                if not p:
                    continue
                if p.lower() == _FA_READONLY_TOKEN:
                    # Explicit read-only form — never a concrete path,
                    # never a hashable overlap participant (guaranteed by
                    # this branch running BEFORE the concrete-path add).
                    readonly_declared = True
                    continue
                # Drop placeholders + wildcards (cannot prove a clobber).
                # Angle brackets included (codex r1 P2): a scaffold literal
                # like `CAN edit: <concrete paths>` must classify
                # unparseable, not concrete — especially since the hook's
                # own block message shows that exact scaffold string.
                # Every drop marks the declaration TAINTED (codex r14 P1):
                # an earlier NONE-READ-ONLY must not hide a later wildcard
                # grant the agent still READS in its prompt.
                # ALL glob/expansion syntax rejected ANYWHERE in the
                # token (codex r19 P1): `src/?.py`, `src/[ab].py` and
                # `src/{a,b}.py` are multi-file grants the agent reads
                # while telemetry hashes only literal tokens (brace forms
                # additionally split into bogus comma paths upstream).
                if any(ch in p for ch in "*?[]{}<>") or p.lower() in (
                    "none", "n/a", "tbd",
                ):
                    invalid_seen = True
                    continue
                # Codex r9 P2: filesystem paths cannot carry NUL/control
                # chars — a crafted value could otherwise classify as
                # concrete AND hash into the domain-separated read-only
                # telemetry marker (which is NUL-framed precisely so real
                # paths can never reach it). Reject, do not sanitize.
                # Broad prose ("all files", "any path") and shell-
                # expansion forms ("$HOME/...") are NOT concrete paths
                # (codex r31 P1): a concrete grant in this grammar has no
                # spaces and no `$` — declared in ADR-191 §2.1.
                if any(ch.isspace() for ch in p) or "$" in p:
                    invalid_seen = True
                    continue
                # Unicode line/paragraph separators included (codex r28
                # P1): U+0085 NEL, U+2028 LS, U+2029 PS present injected
                # prompt STRUCTURE to the agent while hashing as one path
                # — and CEO_UNICODE_HARDBLOCK may be unset.
                if any(
                    ord(ch) < 32
                    or ch in ("\x7f", "\u0085", "\u2028", "\u2029")
                    for ch in p
                ):
                    invalid_seen = True
                    continue
                # Normalize: strip a leading ./, collapse; POSIX paths are
                # case-sensitive so keep case, normalize separators only.
                p = p.lstrip("./").replace("\\", "/")
                if not p:
                    # Codex r3 P1: `...` / `./` normalize to "" — an empty
                    # "path" must never make the declaration concrete (it
                    # would record path_count=1 and hide a would-block
                    # input from the advisory window).
                    invalid_seen = True
                    continue
                # Cap STORED paths without stopping the scan (codex r16
                # P1). Exceeding the cap TAINTS the declaration (codex r31
                # P2): silently dropping path 65+ would hide granted
                # authority from the overlap guard — an assignment that
                # large is a partition smell anyway.
                if len(paths) < _OVERLAP_MAX_PATHS:
                    paths.add(p)
                else:
                    invalid_seen = True
        if not block_had_line:
            # Codex r23 P1: an appended block with ZERO parseable
            # `CAN edit:` lines (`- MAY edit: ...`, misspellings, empty)
            # is a write grant the agent READS but the parser never saw —
            # it must taint the declaration, not vanish behind an earlier
            # read-only block.
            invalid_seen = True
    if paths and not invalid_seen:
        return ("concrete", frozenset(paths))
    if readonly_declared and not paths and not invalid_seen:
        return ("readonly", frozenset())
    # ANY dropped token taints the WHOLE declaration (codex r14+r15 P1):
    # a readonly token or a valid path must not launder a wildcard/
    # placeholder/control-char grant past the enforce gate — the agent
    # still READ that grant in its prompt. Mixed declarations classify
    # unparseable; concrete paths are still returned for overlap
    # telemetry (recording them costs nothing and keeps the collision
    # detector informed even on a tainted spawn).
    return ("unparseable", frozenset(paths))



def _parse_file_assignment(prompt: str) -> frozenset:
    """Return the set of concrete `CAN edit:` paths declared in the spawn's
    `## FILE ASSIGNMENT` block. Empty set if none.

    Back-compat thin wrapper over :func:`_classify_file_assignment` (the
    single scanner since PLAN-178 C1 — one grammar, two consumers).
    """
    return _classify_file_assignment(prompt)[1]



def _path_hash(p: str) -> str:
    """12-hex sha256 prefix of a path. The ONLY path representation that
    enters the audit log (no raw path body ever persists — Sec MF-3)."""
    return hashlib.sha256(p.encode("utf-8", "replace")).hexdigest()[:12]



def _recent_file_assignments(
    env: Dict[str, str],
    session_id: str,
    max_age_s: int = _OVERLAP_LOOKBACK_S,
) -> frozenset:
    """Tail the audit log for `CAN edit:` path-HASHES emitted by OTHER spawns
    in this session within the window. Returns a set of 12-hex path hashes.

    Reads only `spawn_file_assignment_recorded` advisory rows (emitted at the
    allow-path of a prior spawn — see 4d). Bounded tail. Never raises; returns
    empty set on any error (fail-open -> no overlap detected -> allow).
    """
    try:
        log_path = _audit_log_path()
        if log_path is None or not log_path.exists():
            return frozenset()
        import json as _json
        import time as _time
        with log_path.open("r", encoding="utf-8") as f:
            try:
                f.seek(0, 2)
                size = f.tell()
                read_back = min(size, _OVERLAP_TAIL_LINES * 2048)
                start = max(0, size - read_back)
                f.seek(start, 0)
                if start > 0:
                    f.readline()
                tail = f.readlines()
            except OSError:
                tail = f.readlines()[-_OVERLAP_TAIL_LINES:]
        now = _time.time()
        seen = set()
        for line in reversed(tail):
            try:
                ev = _json.loads(line)
            except Exception:
                continue
            if ev.get("action") != "spawn_file_assignment_recorded":
                continue
            if session_id and ev.get("session_id") != session_id:
                continue
            ts_f = _parse_event_ts(ev.get("ts"))
            if ts_f is None or (now - ts_f) > max_age_s:
                continue
            ph = ev.get("path_hashes")
            if isinstance(ph, str):
                for h in ph.split(","):
                    h = h.strip()
                    if h:
                        seen.add(h)
        return frozenset(seen)
    except Exception:  # pragma: no cover - fail-open
        return frozenset()



def _enforce_spawn_rails(
    *,
    prompt: str,
    is_named_spawn: bool,
    env: Dict[str, str],
    session_id: str,
) -> Optional[Tuple[str, str]]:
    """PLAN-133 E3 rails + PLAN-178 C1 FILE ASSIGNMENT grammar. Returns
    (reason_code, detail) when a rail is in ENFORCING mode (its flag=1)
    AND fires; else None.

    In ADVISORY mode (flag unset/0) each rail still EMITS its closed-enum
    event with enforced=0 (measure-first) and returns None (allow).

    NEVER raises. Each rail independently flagged (CEO_SPAWN_TOOL_SCOPE /
    CEO_SPAWN_DEPTH_GUARD / CEO_SPAWN_OVERLAP_GUARD /
    CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED); CEO_SOTA_DISABLE=1 forces
    advisory for ALL of them — that master kill is the named, tested
    recovery route for the grammar gate (ADR-186 pattern).
    """
    try:
        master_off = (env.get("CEO_SOTA_DISABLE") or "").strip() == "1"

        def _flag(name: str) -> bool:
            if master_off:
                return False
            return (env.get(name) or "").strip() == "1"

        # --- Rail 1: tool scope (applies to ANY spawn that declares a list) -
        scope_hit = _check_tool_scope(prompt)
        if scope_hit is not None:
            code, detail = scope_hit
            enforced = _flag("CEO_SPAWN_TOOL_SCOPE")
            _emit_tool_scope_violation(detail=detail, enforced=enforced)
            if enforced:
                return (code, detail)

        # Rails 2 + 3 only matter for NAMED spawns (a generic research task
        # neither recurses into named delegation nor partitions files).
        if is_named_spawn:
            # --- Rail 2: depth fence ---------------------------------------
            depth = _spawn_depth(prompt, env)
            if depth >= 1:
                enforced = _flag("CEO_SPAWN_DEPTH_GUARD")
                _emit_depth_or_overlap(
                    rail="depth", enforced=enforced, count=depth,
                )
                if enforced:
                    return (
                        "spawn_depth_over_one",
                        f"depth={depth}",
                    )

            # --- Rail 3: FILE ASSIGNMENT (grammar + overlap) ---------------
            # PLAN-178 C1 / ADR-191: the block is part of the spawn
            # acceptance contract. EVERY named spawn records an event now —
            # path_count=0 on absent/readonly/unparseable — so omission is
            # visible to the advisory window AND the session's collision
            # detector no longer goes blind on it (R-SEC1 cure; the old emit
            # lived inside the concrete-paths branch only). Absent/
            # unparseable block ONLY under CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED
            # =1 (measure-first flip, same doctrine as C5); CEO_SOTA_DISABLE
            # =1 forces advisory — the TESTED recovery route (ADR-186
            # pattern).
            fa_state, mine = _classify_file_assignment(prompt)
            # Overlap intersection runs for ANY declared concrete path —
            # including a TAINTED declaration's paths (codex r16 P1: with
            # only the overlap guard armed, `owned.py, src/**` must still
            # trip the clash on owned.py; the grammar gate may be advisory
            # in that window). BRANCH ON STATE for the grammar gate itself
            # (codex r15 P1: never on `mine`).
            my_hashes = {_path_hash(p) for p in mine} if mine else set()
            if my_hashes:
                others = _recent_file_assignments(env, session_id)
                clobber = my_hashes & others
                if clobber:
                    enforced = _flag("CEO_SPAWN_OVERLAP_GUARD")
                    _emit_depth_or_overlap(
                        rail="overlap", enforced=enforced, count=len(clobber),
                    )
                    if enforced:
                        return (
                            "spawn_file_assignment_overlap",
                            f"overlap_count={len(clobber)}",
                        )
            if fa_state in ("absent", "unparseable"):
                enforced = _flag("CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED")
                if enforced:
                    # No reservation for a spawn that never dispatches
                    # (codex r16 P2): recording hashes here would leave a
                    # 10-minute phantom that falsely rejects the corrected
                    # RETRY under the overlap guard. The block itself is
                    # the audit trail (veto_triggered carries the code).
                    return (
                        (
                            "spawn_file_assignment_missing"
                            if fa_state == "absent"
                            else "spawn_file_assignment_unparseable"
                        ),
                        "fa_state=%s" % fa_state,
                    )
            # Advisory record for every DISPATCHING named spawn.
            # Telemetry discriminator (allowlist-safe — no new fields):
            # concrete records its hashes with the real count; readonly
            # records the NUL-framed constant marker; absent records an
            # empty set; a tainted-but-advisory declaration records its
            # concrete hashes. Everything except concrete records
            # path_count=0 — the would-block signal the AC-2b advisory
            # window counts.
            if fa_state == "concrete":
                _emit_file_assignment_recorded(my_hashes, session_id)
            else:
                marker = (
                    {_path_hash("\x00fa-readonly-marker\x00")}
                    if fa_state == "readonly" else my_hashes
                )
                _emit_file_assignment_recorded(
                    marker, session_id, path_count=0,
                )
        return None
    except Exception:  # pragma: no cover - fail-open invariant
        return None



def _emit_tool_scope_violation(*, detail: str, enforced: bool) -> None:
    """Emit `spawn_tool_scope_violation` (closed-enum). No-value-echo:
    `detail` carries only tool NAMES + counts (no path / prompt body)."""
    try:
        if not _AUDIT_EMIT_AVAILABLE:
            return
        _audit_emit.emit_generic(
            "spawn_tool_scope_violation",
            rail="tool_scope",
            enforced=1 if enforced else 0,
            detail=(detail or "")[:96],
        )
    except Exception:  # pragma: no cover - fail-open
        return



def _emit_depth_or_overlap(*, rail: str, enforced: bool, count: int) -> None:
    """Emit `spawn_depth_or_overlap_blocked` (closed-enum). `rail` is a
    closed enum (depth|overlap); `count` is a bounded int. No path / prompt."""
    try:
        if not _AUDIT_EMIT_AVAILABLE:
            return
        _audit_emit.emit_generic(
            "spawn_depth_or_overlap_blocked",
            rail=(rail if rail in ("depth", "overlap") else "other"),
            enforced=1 if enforced else 0,
            count=count,
        )
    except Exception:  # pragma: no cover - fail-open
        return



def _emit_file_assignment_recorded(
    path_hashes: set,
    session_id: str,
    path_count: Optional[int] = None,
) -> None:
    """Advisory: record THIS spawn's CAN-edit path HASHES so a later
    concurrent spawn can detect an overlap. Only 12-hex hashes persist.

    ``path_count`` override (PLAN-178 C1): the readonly-declaration path
    records the constant token hash for telemetry attribution but MUST
    report path_count=0 — it declares zero writable paths. Default keeps
    the historical len() semantics for concrete assignments.
    """
    try:
        if not _AUDIT_EMIT_AVAILABLE:
            return
        joined = ",".join(sorted(path_hashes))[:512]
        _audit_emit.emit_generic(
            "spawn_file_assignment_recorded",
            session_id=(session_id or "")[:64],
            path_hashes=joined,
            path_count=(
                min(len(path_hashes), 99)
                if path_count is None else max(0, min(int(path_count), 99))
            ),
        )
    except Exception:  # pragma: no cover - fail-open
        return
