"""Mechanically extracted canonical-edit declarations."""
from __future__ import annotations

def _validated_tool_name(tool_name) -> str:
    """Closed-enum / shape validation for an event-derived tool name."""
    raw = tool_name.strip() if isinstance(tool_name, str) else ""
    if raw in _EDIT_CLASS_TOOLS:
        return raw
    if _MCP_TOOL_NAME_RE.match(raw):
        return raw
    return _BLOCKED_TOOL_UNKNOWN


def _blocked_tool_field() -> str:
    """The validated ``blocked_tool`` value for this invocation."""
    return _validated_tool_name(_CURRENT_TOOL_NAME)


def _emit_allow(system_message: Optional[str] = None) -> str:
    # Claude Code hook schema: top-level "allow" is NOT valid.
    # Emit empty {} or {"systemMessage": ...}.
    out: dict = {}
    if system_message:
        out["systemMessage"] = system_message
    return json.dumps(out, ensure_ascii=False)


def _emit_persona_coverage_synthesized(rel_path: str) -> None:
    """PLAN-106 Wave C — emit persona_coverage_synthesized at sentinel-approved
    canonical-edit allow path.

    Attribution policy:
      archetype = env CEO_ACTIVE_ARCHETYPE if in closed-enum, else
                  "code-reviewer" (canonical-edit sentinel chain is
                  the code-review surface per ADR-010).
      task_type = "review" (sentinel approval is a review act).
      cell_id   = sha256[:8](archetype + ":" + task_type)
      source    = "canonical_edit"

    Best-effort; fail-open on any exception. Bypass via
    ``CEO_PERSONA_COVERAGE_EMIT=0``.
    """
    env = os.environ
    if (env.get("CEO_PERSONA_COVERAGE_EMIT") or "").strip() == "0":
        return
    try:
        import hashlib as _hl
        import unicodedata as _uc
        from _lib import audit_emit as _audit_emit_pc  # noqa: E402

        # Closed enum check (mirrors audit_emit:_PERSONA_COVERAGE_ARCHETYPES).
        archetypes_ok = {
            "code-reviewer", "security-engineer", "qa-architect",
            "threat-detection-engineer",
        }
        raw = (env.get("CEO_ACTIVE_ARCHETYPE") or "").strip().lower()
        # NFKC fold to defeat full-width injection in env var
        raw = _uc.normalize("NFKC", raw)
        archetype = raw if raw in archetypes_ok else "code-reviewer"
        task_type = "review"
        cell_input = f"{archetype}:{task_type}".encode("utf-8")
        cell_id = _hl.sha256(cell_input).hexdigest()[:8]

        _audit_emit_pc.emit_generic(
            "persona_coverage_synthesized",
            archetype=archetype,
            task_type=task_type,
            cell_id=cell_id,
            source="canonical_edit",
        )
    except Exception:  # noqa: BLE001 — fail-open, never block edit
        return


def _emit_block(reason: str) -> str:
    return json.dumps(
        {"decision": "block", "reason": reason}, ensure_ascii=False
    )


def _scan_skill_content_unicode(content: str, *, surface: str, env=None):
    """PLAN-133 A2 — pure invisible-unicode guard for SKILL.md content.

    ``surface`` is the closed-enum origin ("skill_write" | "skill_read"). Default-OFF;
    emits invisible_unicode_blocked on both advisory + enforced paths. Returns a
    block-reason string when enforced AND a detection fires, else None. Fail-open.
    """
    try:
        from _lib import spec_context_sanitizer as _scs  # noqa: E402
    except Exception:  # pragma: no cover - fail-open
        return None
    try:
        if not content:
            return None
        src_env = env if env is not None else os.environ
        if (src_env.get("CEO_SOTA_DISABLE") or "").strip() == "1":
            enforce = False
        else:
            enforce = (src_env.get("CEO_UNICODE_HARDBLOCK") or "").strip() == "1"
            # Prefer the trusted_env snapshot when available (mirror A1/§5b).
            try:
                from _lib import trusted_env as _te  # noqa: E402
                _snap = _te.get_trusted("CEO_UNICODE_HARDBLOCK")
                if _snap is not None:
                    enforce = (_snap or "").strip() == "1"
            except Exception:  # pragma: no cover
                pass

        result = _scs.sanitize(content)
        count = _scs.invisible_unicode_count(result)
        if count <= 0:
            return None
        unicode_class = _scs.classify_invisible_unicode(result)

        try:
            from _lib import audit_emit as _ae  # noqa: E402
            _ae.emit_generic(
                "invisible_unicode_blocked",
                surface=surface,
                unicode_class=unicode_class,
                char_count=int(count),
                enforced=1 if enforce else 0,
            )
        except Exception:  # pragma: no cover - fail-open
            pass

        if not enforce:
            return None
        return (
            "CANONICAL-EDIT-BLOCKED: invisible_unicode_blocked: this SKILL.md "
            f"content contains {count} invisible/smuggling character(s) "
            f"(class={unicode_class}). Skill content is loaded into the model as "
            "trusted instructions; hidden control/bidi/Tag-block characters are "
            "rejected fail-CLOSED. Remove them. To run advisory-only, unset "
            "CEO_UNICODE_HARDBLOCK."
        )
    except Exception:  # pragma: no cover - fail-open invariant
        return None


def _staged_content(event) -> Optional[str]:
    """PLAN-133 A2 — best-effort extraction of the NEW SKILL.md content from a
    staged Edit/Write/MultiEdit ``tool_input``.

    At PreToolUse the new content is in the tool_input, NOT yet on disk. Reads the
    standard adapter keys (Write ``content``; Edit ``new_string``; MultiEdit
    ``edits[].new_string`` concatenated). Returns None when nothing can be extracted
    (fail-OPEN — the caller then never blocks). Never raises.
    """
    try:
        tool_input = getattr(event, "tool_input", None) or {}
        if not isinstance(tool_input, dict):
            return None
        # Write tool — full file content.
        content = tool_input.get("content")
        if isinstance(content, str) and content:
            return content
        # Edit tool — single replacement string.
        new_string = tool_input.get("new_string")
        if isinstance(new_string, str) and new_string:
            return new_string
        # MultiEdit tool — concatenate per-edit new strings.
        edits = tool_input.get("edits")
        if isinstance(edits, list):
            parts: List[str] = []
            for ed in edits:
                if isinstance(ed, dict):
                    ns = ed.get("new_string")
                    if isinstance(ns, str) and ns:
                        parts.append(ns)
            if parts:
                return "\n".join(parts)
    except Exception:  # pragma: no cover - fail-open
        return None
    return None

__all__ = ['_validated_tool_name', '_blocked_tool_field', '_emit_allow', '_emit_persona_coverage_synthesized', '_emit_block', '_scan_skill_content_unicode', '_staged_content']
