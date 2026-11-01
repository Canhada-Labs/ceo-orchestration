"""Mechanically extracted canonical-edit declarations."""
from __future__ import annotations

def _emit_legacy_decision_json(out: str, adapter, event=None) -> None:
    """Emit a pre-built legacy (Claude-shaped) decision JSON string through
    the resolved host adapter (PLAN-155 Wave 1 dispatch seam, debate A1).

    ``decide()`` returns pre-built JSON strings for the legacy contract.
    Under the default/claude adapter the string is written RAW + newline —
    byte-identical to the pre-seam hook. Under any other host adapter the
    string is parsed back into a neutral ``Decision`` and re-emitted via
    the adapter's ``emit_decision`` WITH the parsed NormalizedEvent
    (host egress shape is EXPLICIT-only: a host-wire event stamps
    ``raw_payload['ceo_host_wire']`` and the codex adapter emits
    ``hookSpecificOutput.permissionDecision``), so a deny reaches the
    host in the shape its wire enforces (a raw Claude-shaped line is
    foreign JSON on the codex wire → silent fail-open → the S254
    dead-gate class).
    """
    adapter_basename = (getattr(adapter, "__name__", "") or "").rsplit(".", 1)[-1]
    if adapter_basename == "claude":
        sys.stdout.write(out + "\n")
        return
    from _lib import contract as _contract  # noqa: PLC0415
    parsed = json.loads(out)
    adapter.emit_decision(
        _contract.Decision(
            allow=(parsed.get("decision") != "block"),
            reason=parsed.get("reason"),
            system_message=parsed.get("systemMessage"),
            message=parsed.get("message"),
        ),
        event=event,
    )


def _adapter_emit(adapter, decision, event=None) -> None:
    """Emit a neutral ``Decision`` through the resolved host adapter.

    Claude path: the historical two-arg call — byte-identical output
    (``claude.py:emit_decision`` does not take ``event=``). Any other
    resolved adapter (codex host mode, ``_FailClosedAdapter``) receives
    the parsed NormalizedEvent so the egress shape follows the wire that
    produced it and the debate-A2 coherence override can fire.
    """
    adapter_basename = (getattr(adapter, "__name__", "") or "").rsplit(".", 1)[-1]
    if adapter_basename == "claude":
        adapter.emit_decision(decision)
        return
    adapter.emit_decision(decision, event=event)


def _cli_is_canonical(args: List[str]) -> int:
    """PLAN-156-FOLLOWUP F5 (debate C2(b)) — read-only canonical-path
    classification ORACLE.

    Single-source-of-truth CLI so shell consumers (the grok/codex pre-push
    review gates) classify paths with the SAME ``_is_canonical`` predicate
    the edit-time guard and the Stop-review recorder use — re-implementing
    the guard glob list in bash IS the drift class F5 fixes.

    Usage:
        python3 check_canonical_edit.py --is-canonical <path>...
        python3 check_canonical_edit.py --is-canonical -   # paths on stdin,
                                                           # one per line
                                                           # (ARG_MAX-safe)

    Output: one line per input path, ``<path>\\t<0|1>`` (1 = canonical),
    in input order. Exit 0 on successful classification of every path.
    Exit 2 when no path argument/stdin is supplied (consumers must treat
    ANY nonzero exit as oracle failure and fall back fail-CLOSED to their
    coarse over-triggering classifier).

    Contract notes:
    - Pure read-only classification. NO hook semantics run in this mode:
      no event parse, no adapter, no sentinel lookup, no emission on the
      hook wire. The hook entry (``main()``) is byte-identical when the
      script is invoked as a hook (argv empty — ``_python-hook.sh`` passes
      no arguments).
    - Repo root resolves exactly like the hook path does
      (``CLAUDE_PROJECT_DIR`` or cwd — see ``main()``), so oracle and hook
      can never disagree on anchoring.
    - Per-path classification fault → that path is reported ``1``
      (canonical). Over-triggering review on an unclassifiable path is the
      safe direction (fail-CLOSED); under-triggering would let an
      unreviewed L3 touch through. ``_is_canonical`` itself already
      returns False for paths outside the repo root — that is the
      oracle's own semantics, not a fault.
    """
    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    paths: List[str] = list(args)
    if paths == ["-"]:
        paths = [ln.rstrip("\n") for ln in sys.stdin.read().splitlines()]
        paths = [p for p in paths if p]
    if not paths:
        sys.stderr.write(
            "usage: check_canonical_edit.py --is-canonical <path>... | -\n"
        )
        return 2
    out_lines: List[str] = []
    for raw in paths:
        try:
            flag = 1 if _is_canonical(raw, repo_root) else 0
        except Exception:
            # Fail-CLOSED per path: unclassifiable → treat as canonical
            # (over-trigger review, never under-trigger).
            flag = 1
        out_lines.append("%s\t%d" % (raw, flag))
    sys.stdout.write("\n".join(out_lines) + "\n")
    return 0


def main() -> int:
    """Hook entry point.

    PLAN162_FIX_1 / PLAN162_FIX_9 wrapper: arms the per-invocation
    wall-clock deadline (consensus C2/C3/S8) around the real entry point
    and clears BOTH pieces of invocation-scoped module state in a
    ``finally``. Without the reset, a module-scope deadline (or a stale
    tool name) armed by one in-process invocation would leak into the
    next caller in the same process — the test suite drives ``decide()``
    and ``main()`` in-process, and an expired leftover deadline would
    fail those closed for no reason at all.
    """
    global _CURRENT_TOOL_NAME
    if _COMPONENT_IMPORT_ERROR is not None:
        print("check_canonical_edit: component import unavailable (" +
              _COMPONENT_IMPORT_ERROR + ")", file=sys.stderr)
        print(_emit_allow())
        return 0
    _start_wall_budget()
    try:
        return _main_guarded()
    finally:
        _reset_wall_budget()
        _CURRENT_TOOL_NAME = ""


def _main_guarded() -> int:
    """Hook entry point.

    PLAN-006 Phase 1 migration (ADR-014): uses Adapter Layer
    `read_event()` / `emit_decision()`. Byte-identical output.

    PLAN-155 Wave 1 (debate A1, ratified seam option b): the adapter is
    resolved ONCE per invocation through the shared seam
    ``_lib.adapters.resolve()``. Under ``CEO_HOOK_ADAPTER`` unset/"claude"
    the seam returns the claude adapter module and every downstream byte
    is identical to the pre-seam hook (the regression bar). The debate-A2
    coherence gate (explicitly-set-but-unresolvable ``CEO_HOOK_ADAPTER``
    → INPUT class per PLAN-152 C4) lives INSIDE ``resolve()``, which
    fails CLOSED by returning a ``_FailClosedAdapter`` whose egress
    ALWAYS denies in BOTH harness vocabularies (top-level
    ``decision: block`` + ``hookSpecificOutput.permissionDecision:
    deny``) with a stderr + audit breadcrumb — never a silent fallback
    to the claude adapter. Non-claude adapters additionally receive the
    parsed event at egress (``_adapter_emit``) so the host wire shape
    and the coherence override are event-driven, never latched.
    """
    from _lib import adapters as _adapters  # noqa: E402
    from _lib import contract as _contract  # noqa: E402

    _adapter = _adapters.resolve()

    try:
        event = _adapter.read_event(phase="PreToolUse")
    except Exception:
        _adapter.emit_decision(_contract.allow())
        return 0

    if event.parse_error:
        # PLAN162_FIX_5B (finding #5b, consensus C4). HEAD emitted a bare
        # ALLOW here. ``parse_error`` is, by name and by construction, the
        # signal that the PAYLOAD did not parse — INPUT, not
        # infrastructure — and CLAUDE.md §4 is literal about that split:
        # fail-open on INFRASTRUCTURE, fail-CLOSED on INPUT. The sibling
        # kernel hook already implements this exact form; THIS hook was
        # the drift.
        #
        # The council justified the old posture by citing "the ADR-010
        # fail-open contract". That citation is FALSE: ADR-010 contains
        # zero occurrences of any failure-posture text. The only such text
        # is this hook's own module docstring, so citing it as the ADR
        # that authorizes it is circular.
        #
        # 5a (``read_event`` RAISING, above) stays fail-OPEN — that IS a
        # genuine infrastructure failure, and the kernel sibling is
        # fail-open identically there.
        _emit_legacy_decision_json(
            _emit_block(
                reason=(
                    "CANONICAL-EDIT-BLOCKED: canonical_edit_payload_parse_error "
                    "— the PreToolUse payload could not be parsed, so this "
                    "edit-class event cannot be proven non-canonical. "
                    "Security-matcher INPUT failure → fail-closed "
                    "(CLAUDE.md §4; PLAN-162 finding #5b). Re-issue the tool "
                    "call with a well-formed payload."
                )
            ),
            _adapter,
            event,
        )
        return 0

    # PLAN-065 Layer A (S81-tris gap closure, 2026-05-04):
    # When tool_name is mcp__*, the adapter's `event.file_path` field
    # may be empty (custom MCP tools don't use the standard
    # Edit/Write/MultiEdit `file_path` key). Inspect tool_input directly
    # for write-shape parameters and resolve all candidate paths.
    # Each candidate is gated independently; if ANY candidate is
    # canonical without sentinel coverage, block.
    tool_name = (event.tool_name or "").strip()
    # PLAN162_FIX_9 — publish the EVENT's tool name (validated at read
    # time, not here) for the four audit sites that record ``blocked_tool``.
    global _CURRENT_TOOL_NAME
    _CURRENT_TOOL_NAME = tool_name
    candidate_paths: List[str] = []
    if event.file_path:
        candidate_paths.append(event.file_path)
    if tool_name.startswith("mcp__"):
        candidate_paths.extend(
            _extract_mcp_target_paths(event.tool_input or {})
        )
    # PLAN-155 Wave 1 (S265 pair-rail P1#3): a codex apply_patch can touch
    # MULTIPLE files; the host adapter surfaces every path (incl. rename
    # targets) as tool_input['apply_patch_paths']. Gate them ALL — a
    # benign first op must not smuggle a later op into a guarded path.
    # Absent under Claude Code (key never present → byte-identical).
    if isinstance(event.tool_input, dict):
        for _pp in event.tool_input.get("apply_patch_paths") or []:
            if isinstance(_pp, str) and _pp and _pp not in candidate_paths:
                candidate_paths.append(_pp)

    if not candidate_paths:
        _adapter_emit(_adapter, _contract.allow(), event)
        return 0

    # Use the first canonical path for legacy file_path-keyed downstream
    # logic, but iterate all candidates for canonical detection.
    file_path = candidate_paths[0]

    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())

    # Layer A: gate a multi-candidate event using the MOST RESTRICTIVE
    # canonical candidate. Historically mcp__*-only; PLAN-155 extends the
    # scan to any multi-candidate event (apply_patch multi-file, S265
    # P1#3). Single-candidate events (every Claude Code Edit/Write) skip
    # this block entirely — byte-identical fast path.
    #
    # PLAN160_FIX_A (finding A — multi-candidate gate bypass): the prior
    # loop ``break``-ed at the FIRST canonical candidate and gated ONLY
    # that path via decide(). A multi-file MCP event whose first canonical
    # candidate was sentinel-GRANTED let every LATER canonical candidate
    # ride through UNGATED. The fix scans ALL candidates and selects the
    # OFFENDING candidate (canonical + ungranted) if any —
    # most-restrictive-wins — so decide() is still invoked at most ONCE
    # (emit-once: decide() fires _emit_persona_coverage_synthesized on the
    # allow path; a per-candidate decide() would double-emit).
    #
    # ``_forced_out``: a pre-built decision that BYPASSES decide(). Set for
    # the two fail-CLOSED cases that must NOT be re-routed through decide()
    # — over-cap, and any scan fault (classification OR sentinel discovery).
    # Routing a classification-fault candidate through decide() would
    # re-raise inside decide(), and the outer handler below would then
    # fail-classify it as non-canonical and ALLOW (the V-A hole the codex
    # pair-rail REJECTed). ``_find_sentinels`` is loaded LAZILY, only once a
    # canonical candidate is seen, and the whole scan is wrapped so a
    # sentinel-discovery fault fail-CLOSES with an emit instead of
    # propagating out of main() (zero-emit hole).
    _multi = tool_name.startswith("mcp__") or len(candidate_paths) > 1
    _forced_out = None
    if _multi:
        try:
            if len(candidate_paths) > _PLAN160_MAX_CANDIDATES:
                # Fail-CLOSED: more candidates than we will classify —
                # cannot prove every canonical candidate is granted, so
                # block the whole event rather than truncate the scan and
                # risk an unexamined offender beyond the cap.
                _forced_out = _emit_block(
                    reason=(
                        "CANONICAL-EDIT-BLOCKED: canonical_edit_hook_fault — "
                        f"multi-candidate event carries {len(candidate_paths)} "
                        f"paths (> cap {_PLAN160_MAX_CANDIDATES}); cannot clear "
                        "all — fail-closed. PLAN-160 finding A."
                    )
                )
            else:
                sentinels = None  # lazy: only load once a canonical candidate exists
                first_canonical = None
                offender = None
                for candidate in candidate_paths:
                    # PLAN162_FIX_1 (C2) — the second sentinel-loop site.
                    # Fail-CLOSED on an elapsed budget: a multi-candidate
                    # event we could not finish clearing is exactly the
                    # event that must not ride through.
                    if _wall_budget_expired():
                        _forced_out = _emit_block(
                            reason=_WALL_DEADLINE_BLOCK_REASON
                        )
                        break
                    if not _is_canonical(candidate, repo_root):
                        continue
                    if first_canonical is None:
                        first_canonical = candidate
                    if sentinels is None:
                        sentinels = _find_sentinels(repo_root)
                    if not _candidate_is_granted(candidate, repo_root, sentinels):
                        offender = candidate
                        break
                # decide() runs ONCE: on the offender (→ block naming it) if
                # any, else the first canonical candidate (→ sentinel allow +
                # persona coverage), else candidate_paths[0] (non-canonical →
                # allow).
                file_path = offender or first_canonical or file_path
        except Exception as _scan_exc:
            # Classification OR sentinel-discovery fault on a MULTI-candidate
            # event → fail-CLOSED with an emit. We are on a multi-file event
            # we could not fully clear; a re-route through decide() would
            # re-raise on the unclassifiable path and the outer handler would
            # ALLOW it (V-A). Blocking here is the only safe outcome.
            print(
                f"[check_canonical_edit] SCAN FAULT: "
                f"{type(_scan_exc).__name__}: {_scan_exc}",
                file=sys.stderr,
            )
            _forced_out = _emit_block(
                reason=(
                    "CANONICAL-EDIT-BLOCKED: canonical_edit_hook_fault — "
                    f"multi-candidate scan fault ({type(_scan_exc).__name__}); "
                    "fail-closed. PLAN-160 finding A."
                )
            )

    if _forced_out is not None:
        # Pre-built fail-closed decision (over-cap or scan fault). Emit
        # through the same legacy seam + best-effort veto audit as a normal
        # block, BYPASSING decide() — routing a scan-fault path through
        # decide() would re-raise and the outer handler would fail-OPEN
        # (the V-A hole the codex pair-rail REJECTed).
        _fparsed = json.loads(_forced_out)
        if _fparsed.get("decision") == "block":
            # Forensic breadcrumb only. On over-cap / scan-fault the specific
            # offending candidate is unknown or unreachable, so we record the
            # event's FIRST candidate (not necessarily the offender); the
            # fail-CLOSED decision itself is correct regardless.
            _audit_block(
                candidate_paths[0] if candidate_paths else file_path,
                _safe_sentinel_count(repo_root),
                reason_code=_block_reason_code(_fparsed.get("reason", "")),
            )
        _emit_legacy_decision_json(_forced_out, _adapter, event)
        return 0

    # Single-candidate hot path (and the all-canonical-granted multi path)
    # reaches decide() here. SECURITY INVARIANT: this call is NOT wrapped by
    # the multi-candidate fail-CLOSED scan above, so its safety relies on
    # ``_is_canonical`` / ``_repo_rels`` being TOTAL (never raising on str
    # input — guaranteed by their broad ``except Exception``, PLAN160_FIX_D,
    # and fenced by the totality unit tests). If a future refactor
    # reintroduces a raise in classification, the outer handler below
    # re-classifies and could fail-OPEN a single-candidate canonical edit —
    # keep the totality tests as the regression fence.
    try:
        out = decide(file_path=file_path, repo_root=repo_root)
    except Exception as e:
        # PLAN-045 Wave 1 F-01-07: fail-CLOSED for canonical paths.
        # Previously any exception fell through to allow; now an edit
        # targeting a confirmed canonical path blocks with
        # ``canonical_edit_hook_fault``. Non-canonical edits keep the
        # fail-open contract so a hook bug doesn't brick the session
        # on benign writes.
        print(
            f"[check_canonical_edit] FATAL: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        try:
            is_canonical = _is_canonical(file_path, repo_root)
        except Exception:
            is_canonical = False
        if is_canonical:
            _emit_legacy_decision_json(
                _emit_block(
                    reason=(
                        "CANONICAL-EDIT-BLOCKED: hook fault on canonical "
                        f"path; {type(e).__name__}: {e}. PLAN-045 F-01-07."
                    )
                ),
                _adapter,
                event,
            )
            return 0
        _adapter_emit(_adapter, _contract.allow(), event)
        return 0

    # On block, emit veto event (best-effort)
    parsed = json.loads(out)
    if parsed.get("decision") == "block":
        try:
            rel = str(Path(file_path).resolve().relative_to(repo_root.resolve())).replace(os.sep, "/")
        except Exception:
            rel = file_path
        _audit_block(
            rel,
            _safe_sentinel_count(repo_root),
            reason_code=_block_reason_code(parsed.get("reason", "")),
        )

    # PLAN-163 T3.1 — session-roots write-guard (DirectoryAdded consumer).
    # Runs AFTER the existing project-relative checks and ONLY on a
    # would-allow event, so it never relaxes the sentinel gate — it can
    # only ADD a deny. Checks EVERY candidate path of the event (the
    # multi-candidate list built above), by absolute realpath, against the
    # session-registered roots in .claude/state/session-roots.json.
    if parsed.get("decision") != "block":
        try:
            _sr_sid = (
                (getattr(event, "session_id", "") or "").strip()
                or (os.environ.get("CLAUDE_SESSION_ID") or "").strip()
            )
            _sr_reason = _session_roots_guard(
                candidate_paths, repo_root, _sr_sid
            )
        except Exception as _sr_exc:
            # An unexpected raise here is a hook bug (INFRA) → fail-open
            # with a breadcrumb; every INPUT-shaped failure inside the
            # guard already returns a deny VALUE instead of raising.
            print(
                "[check_canonical_edit] session-roots guard fault: "
                f"{type(_sr_exc).__name__}: {_sr_exc}",
                file=sys.stderr,
            )
            _sr_reason = None
        if _sr_reason is not None:
            _audit_session_root_block(
                candidate_paths[0] if candidate_paths else file_path
            )
            _emit_legacy_decision_json(
                _emit_block(_sr_reason), _adapter, event
            )
            return 0

    # PLAN-133 A2 — invisible-unicode guard at SKILL.md authoring. Only on a
    # would-allow canonical SKILL.md edit (so we never relax the sentinel gate;
    # we can only ADD a fail-CLOSED block). Reads the staged tool_input content,
    # not disk. Default-OFF (CEO_UNICODE_HARDBLOCK=1). Fail-open.
    if parsed.get("decision") != "block" and (
        file_path.endswith("/SKILL.md") or file_path.endswith("SKILL.md")
    ):
        try:
            new_content = getattr(event, "new_content", None) or _staged_content(event)
        except Exception:  # pragma: no cover - fail-open
            new_content = None
        if new_content:
            _uni = _scan_skill_content_unicode(
                new_content, surface="skill_write"
            )
            if _uni is not None:
                _adapter_emit(_adapter, _contract.block(_uni), event)
                return 0

    # `decide()` returns pre-built JSON strings for the legacy contract;
    # under the default/claude adapter the seam helper writes it directly
    # + newline (byte identity preserved); other host adapters re-shape it
    # on the parsed event's wire.
    _emit_legacy_decision_json(out, _adapter, event)
    return 0

__all__ = ['_emit_legacy_decision_json', '_adapter_emit', '_cli_is_canonical', 'main', '_main_guarded']
