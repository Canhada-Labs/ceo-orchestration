"""Decision conversion, audit emitters, and hook entry point."""
from __future__ import annotations

def _emit_env_var_hijack_event(hijack_class: str) -> None:
    """Emit env_var_hijack_blocked(hijack_class). Fail-open (PLAN-133 A1).

    The ONLY caller-supplied field is the closed-enum `hijack_class` — NEVER the
    variable NAME and NEVER the assigned VALUE (the value is the payload surface,
    MF analogous to git_hook_bypass MF-G). session_id / project are read from the
    live env (forensic envelope only; not a grant source). Emitted on BOTH an
    enforced block AND an advisory (default-OFF) detection.
    """
    if _audit_emit is None:
        return
    try:
        import os as _os
        _audit_emit.emit_env_var_hijack_blocked(
            hijack_class=hijack_class,
            session_id=_os.environ.get("CLAUDE_SESSION_ID", ""),
            project=_os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:  # pragma: no cover
        pass


def _emit_egress_destination_event(egress_class: str, destination: str) -> None:
    """Emit egress_destination_detected(egress_class, destination). Fail-open.

    `destination` is ALREADY host-only (egress_taxonomy reduces it); the audit
    emitter re-truncates defensively. The full URL / path / query / inline
    credential is NEVER passed here. When egress_class == 'pair_rail' the caller
    ALSO emits pair_rail_outgoing_redaction_applied (positive proof the outbound
    redactor ran on the sanctioned channel). session_id / project are forensic
    envelope only (not a grant source).
    """
    if _audit_emit is None:
        return
    try:
        import os as _os
        _sid = _os.environ.get("CLAUDE_SESSION_ID", "")
        _proj = _os.environ.get("CLAUDE_PROJECT_DIR", "")
        _audit_emit.emit_egress_destination_detected(
            egress_class=egress_class,
            destination=destination,
            session_id=_sid,
            project=_proj,
        )
        if egress_class == "pair_rail":
            _audit_emit.emit_pair_rail_outgoing_redaction_applied(
                signal="egress_taxonomy",
                family="pair_rail",
                match_count=0,
                bytes_scanned=0,
                callsite="check_bash_safety.egress",
                session_id=_sid,
                project=_proj,
            )
    except Exception:  # pragma: no cover
        pass


def _emit_credential_leak_event(provider: str, redacted: str) -> None:
    """Emit veto_triggered(credential_leak). Fail-open."""
    if _audit_emit is None:
        return
    try:
        _audit_emit.emit_veto_triggered(
            hook="check_bash_safety", reason_code="credential_leak",
            reason_preview=f"bash_credential_leak_blocked provider={provider} match={redacted}",
            blocked_tool="Bash")
    except Exception:  # pragma: no cover
        pass


def _emit_bash_input_rewritten_event(rewrite: "Rewrite") -> None:
    """Emit bash_input_rewritten with the before/after hash PAIR. Fail-open.

    PLAN-135 W2 H5 (mini-ADR-154 §2). The ONLY caller-supplied fields are
    the closed-enum `rewrite_class` and the two 64-hex sha256 hashes — the
    command BYTES (before OR after) are NEVER persisted (a force-push line
    can carry a remote URL with an inline token). The hash pair lets an
    auditor prove the audited command equals the executed command without
    seeing either command. session_id / project are forensic envelope only.
    """
    if _audit_emit is None:
        return
    try:
        import os as _os
        _audit_emit.emit_bash_input_rewritten(
            rewrite_class=rewrite.rewrite_class,
            before_sha256=rewrite.before_sha256,
            after_sha256=rewrite.after_sha256,
            session_id=_os.environ.get("CLAUDE_SESSION_ID", ""),
            project=_os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:  # pragma: no cover
        pass


def _adapter_emit(adapter, decision, event=None) -> None:
    """Emit a neutral ``Decision`` through the resolved host adapter
    (PLAN-155 Wave 1 dispatch seam, debate A1).

    Claude path: the historical two-arg call — byte-identical output
    (``claude.py:emit_decision`` does not take ``event=``). Any other
    resolved adapter (codex host mode, ``_FailClosedAdapter``) receives
    the parsed NormalizedEvent so the egress shape follows the wire that
    produced it (host shape is EXPLICIT-only) and the debate-A2
    coherence override can fire.
    """
    adapter_basename = (getattr(adapter, "__name__", "") or "").rsplit(".", 1)[-1]
    if adapter_basename == "claude":
        adapter.emit_decision(decision)
        return
    adapter.emit_decision(decision, event=event)


def main() -> int:
    """Hook entry point: read stdin via Adapter Layer, decide, write stdout, exit 0.

    PLAN-006 Phase 1 migration (ADR-014). Uses `claude_adapter.read_event()`
    / `emit_decision()` instead of direct `_lib.payload` + `print()`.
    Output is byte-identical to pre-migration (test_hook_byte_fidelity).

    PLAN-155 Wave 1 (debate A1, ratified seam option b): the adapter is
    resolved ONCE per invocation via the shared seam
    ``_lib.adapters.resolve()`` — BEFORE the fail-open try block, so the
    debate-A2 coherence gate inside ``resolve()``
    (explicitly-set-but-unresolvable ``CEO_HOOK_ADAPTER`` → INPUT class
    per PLAN-152 C4 → fail-CLOSED: ``resolve()`` returns a
    ``_FailClosedAdapter`` whose egress ALWAYS denies in BOTH harness
    vocabularies, with a stderr + audit breadcrumb — never a silent
    fallback to the claude adapter) is never swallowed into an allow.
    Under ``CEO_HOOK_ADAPTER`` unset/"claude" the seam returns the claude
    adapter module and downstream behavior is byte-identical.
    """
    _adapter = _adapters.resolve()
    event = None
    try:
        # >>> PLAN-153.E5 / ADR-175 citation-gate BEGIN (stdin buffering)
        # Read stdin ONCE into a buffer, then hand the adapter an equivalent
        # stream. The adapter's NormalizedEvent deliberately drops the raw
        # payload (deny-by-default), but the citation gate needs the
        # top-level `transcript_path` field — parsed here from the SAME
        # bytes the adapter consumes, so the verified path is exactly what
        # the harness sent. Behavior-neutral for every other code path.
        import io as _io
        try:
            _raw_stdin_text = sys.stdin.read()
        except Exception:  # exotic stdin failure → same fail-open as before
            _raw_stdin_text = ""
        event = _adapter.read_event(
            stream=_io.StringIO(_raw_stdin_text), phase="PreToolUse"
        )
        # <<< PLAN-153.E5 / ADR-175 citation-gate END
        if event.parse_error:
            print(
                f"[check_bash_safety] WARN: stdin parse error: {event.parse_error}",
                file=sys.stderr,
            )
            _adapter_emit(_adapter, _contract.allow(), event)
            return 0

        command = event.command or ""
        if not command and isinstance(event.tool_input, dict):
            command = str(event.tool_input.get("command") or "")

        try:
            from _lib import bash_indirect_telemetry as _indirect_telemetry
            for _switch in ("CEO_BASH_INDIRECT_GUARD", "CEO_BASH_INDIRECT_HEURISTICS"):
                if _trusted_env.get_trusted(_switch) == "0":
                    _indirect_telemetry.disabled_once(_switch, event.session_id)
        except Exception:  # audit infrastructure must not change the verdict
            pass

        decision = decide_command(command)
        # PLAN-154 fact gate precedes the PLAN-153 citation pilot for
        # destructive-class blocks. Both see the final decision.
        if not decision.allow and decision.destructive:
            _fact_transcript_path = _extract_transcript_path(_raw_stdin_text)
            decision, _fact_enforce_active = _apply_fact_gate(
                decision, command, _fact_transcript_path
            )
            if (
                not decision.allow
                and decision.destructive
                and not _fact_enforce_active
                and _destructive_citation_gate_enabled()
            ):
                decision = _apply_destructive_citation_gate(
                    decision, command, _fact_transcript_path
                )
        # <<< PLAN-154.F6 fact-gate END
        # <<< PLAN-153.E5 / ADR-175 citation-gate END
        if not decision.allow and decision.reason_code and _audit_emit is not None:
            try:
                _audit_emit.emit_veto_triggered(
                    hook="check_bash_safety", reason_code=decision.reason_code,
                    reason_preview=decision.reason[:200], blocked_tool="Bash",
                )
            except Exception:  # audit infrastructure must remain fail-open
                pass
        # Re-run detector on credential blocks to emit audit event.
        if not decision.allow and decision.reason and "API credential" in decision.reason:
            hit = _check_credential_leak(command)
            if hit is not None:
                _emit_credential_leak_event(hit[0], hit[1])
        # PLAN-124 WS-1 — emit git_hook_bypass_blocked on a block OR an
        # authorized escape-hatch use. Re-scan to recover the closed-enum
        # flag_class (decide_command stays pure / I/O-free). The credential
        # block above takes precedence, so skip if the reason was a credential.
        if not (decision.reason and "API credential" in decision.reason):
            git_hit = _check_git_bypass(command)
            if git_hit is not None:
                _kind, _flag_class, _reason = git_hit
                # block → emit the matched flag_class; escape → escape_hatch_used.
                _emit_git_hook_bypass_event(_flag_class)
        # PLAN-133 A1 — emit env_var_hijack_blocked on ANY detected env-hijack
        # SET (enforced block OR advisory default-OFF detection). Re-scan to
        # recover the closed-enum hijack_class (decide_command stays pure). Only
        # the closed-enum class is persisted — never the var name/value.
        if not (decision.reason and "API credential" in decision.reason):
            env_hit = _check_env_hijack(command)
            if env_hit is not None:
                _hijack_class, _key, _reason = env_hit
                _emit_env_var_hijack_event(_hijack_class)
        # PLAN-133 A3 — emit egress destinations on block or allow.
        if _egress_emit_enabled():
            for _eclass, _edest in _classify_egress(command):
                _emit_egress_destination_event(_eclass, _edest)
        # PLAN-135 W2 H5 — when decide_command chose the corrective rewrite,
        # emit the bash_input_rewritten audit event with the before/after
        # hash PAIR BEFORE emitting the `ask` decision (mini-ADR-154 §2: the
        # audit records that the rail rewrote the input, so the downstream
        # audited command provably equals the executed/asked command). The
        # emit is fail-open (it never gates the decision).
        if decision.rewrite is not None:
            _emit_bash_input_rewritten_event(decision.rewrite)
        _adapter_emit(
            _adapter, _to_contract_decision(decision, event.tool_input), event
        )
        return 0
    except Exception as e:  # pragma: no cover
        print(
            f"[check_bash_safety] FATAL: {e.__class__.__name__}: {e}",
            file=sys.stderr,
        )
        _adapter_emit(_adapter, _contract.allow(), event)
        return 0


if __name__ == "__main__":
    sys.exit(main())
