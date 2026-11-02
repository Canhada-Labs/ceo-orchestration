from __future__ import annotations

import re

__all__ = ('_consult_model_routing_mode', '_MCP_ARCHETYPE_TASK_CLASS_HINTS', '_PROMOTION_ARCHETYPE_HINTS', '_emit_mcp_routing_advisory', '_emit_promotion_advisory', '_emit_advisory_safe', '_PERSONA_HEADER_RE', '_SKILL_CONTENT_MARKER', '_SKILL_CONTENT_MIN_BYTES', '_SKILL_CONTENT_MARKER_RE', '_NEXT_H2_RE', '_CODE_FENCE_RE', '_HTML_COMMENT_RE', '_SPEC_CONTEXT_HEADER_RE', '_sanitize_spec_context_advisory', '_enforce_spec_context_unicode', '_unicode_hardblock_enforced', '_emit_spawn_confidence_advisory')

# ---------------------------------------------------------------------------
# PLAN-112-FOLLOWUP-persona-routing-wire W1+W2+W3 — god-mode matrix consult.
# ---------------------------------------------------------------------------
# Consult ALL THREE persona_routing APIs (AC1):
# `get_mode(archetype, "AUTO-05")` (recorded mode label) +
# `is_enforcing(archetype, "AUTO-05")` (authoritative effective-enforcing
# boolean that drives `decision`) + `is_killswitch_active()` (records the
# kill-switch state) and EMIT the resulting mode as forensic telemetry
# (`model_routing_enforced`). This closes the F-1.2 dead-policy (the
# AUTO-05 enforcing cell was never read at runtime).
#
# W3 — DEFERRED BLOCK + FLIP DOCTRINE:
#   The actual model-tier BLOCK is DEFERRED. A "model mismatch -> block"
#   predicate needs the dispatched/requested model, but the Agent hook
#   payload exposes only description/prompt/subagent_type/run_in_background
#   (SPEC/v1/hook-io.schema.md). `metadata.get("model")` (read in
#   `_read_archetype_model_frontmatter`) is the AGENT FRONTMATTER model, NOT
#   a spawn-requested model. With no requested-model input, a block would be
#   theater. When the harness exposes the dispatched model to PreToolUse, the
#   violation predicate becomes a 1-liner: fm_model present AND requested
#   present AND differing.
#   The future enable of that block is governed by OBSERVED-VIOLATION VOLUME
#   + a false-positive-rate threshold, NOT by elapsed calendar days
#   (ADR-095 / [[feedback-no-calendar-gates-ai-workflow]]). Recorded here as
#   the flip doctrine for a future ADR-118-AMEND-2.
#
# SECURITY INVARIANTS:
#   - Mode is read off the AUTHORITATIVE `subagent_type`-derived archetype
#     ONLY — NEVER the prompt-regex archetype (attacker-controllable; a
#     spoofed archetype must not flip the recorded mode). CWE-400/spoofing.
#   - Fail-OPEN: import/get_mode failure -> emit `model_routing_eval_error`
#     and return; NEVER raise in the hook hot path (CLAUDE.md §5).
#   - Kill-switch precedence: get_mode() already demotes an enforcing cell
#     to advisory under `CEO_GODMODE_ENFORCING=0`; we record the demoted
#     mode (advisory) so the audit reflects effective policy.
def _consult_model_routing_mode(
    *,
    description: str,
    prompt: str,
    subagent_type: str,
    env: Optional[Dict[str, str]] = None,
    project_dir: Optional[str] = None,
) -> None:
    """Consult the god-mode routing matrix + emit forensic telemetry.

    CONSULT + AUDIT ONLY. NEVER blocks, NEVER mutates tool_input, NEVER
    raises. Consults all THREE persona_routing APIs (AC1): `get_mode`
    (recorded mode label), `is_enforcing` (authoritative effective-
    enforcing boolean that drives `decision`), and `is_killswitch_active`.
    Emits `model_routing_enforced` (mode/recommended_model/
    killswitch_armed/decision) on success, `model_routing_eval_error`
    (decision=eval_error) on any infra failure (fail-open).
    """
    try:
        src_env = env if env is not None else os.environ
        if not _AUDIT_EMIT_AVAILABLE:
            return  # nothing to audit against; consult is observability-only

        # AUTHORITATIVE source ONLY — subagent_type. A prompt-regex archetype
        # is attacker-controllable and must not flip the recorded mode.
        archetype = (subagent_type or "").strip().lower()
        if not archetype:
            return  # no authoritative archetype -> no mode to record

        session_id = src_env.get("CLAUDE_SESSION_ID", "") or ""
        proj = project_dir or src_env.get("CLAUDE_PROJECT_DIR") or os.getcwd()

        # Fail-OPEN guard around the matrix consult.
        try:
            if _persona_routing is None:
                raise RuntimeError("persona_routing import unavailable")
            # NEVER read _PRIMITIVE_DEFAULT_MODE directly — get_mode /
            # is_enforcing honor the kill-switch demotion internally.
            # All THREE persona_routing APIs are consulted (AC1):
            #   - get_mode      -> the effective (possibly demoted) mode label
            #                      recorded verbatim in the emit
            #   - is_enforcing  -> the AUTHORITATIVE effective-enforcing boolean
            #                      that drives `decision` (kill-switch already
            #                      folded in: returns False when demoted)
            #   - is_killswitch_active -> records whether the kill-switch armed
            mode = _persona_routing.get_mode(archetype, "AUTO-05")
            is_enforcing = bool(
                _persona_routing.is_enforcing(archetype, "AUTO-05")
            )
            killswitch_armed = bool(_persona_routing.is_killswitch_active())
        except Exception:  # noqa: BLE001 — fail-open per CLAUDE.md §5
            try:
                _audit_emit.emit_generic(
                    "model_routing_eval_error",
                    archetype=archetype[:64],
                    reason_code="persona_routing_eval_failed",
                    decision="eval_error",
                    session_id=session_id,
                    project=str(proj)[:256],
                )
            except Exception:  # noqa: BLE001
                pass
            return

        # recommended_model: best-effort authoritative agent-frontmatter
        # model for this archetype (NOT a spawn-requested model). "" when
        # absent. Reuses the cached frontmatter reader.
        recommended_model = ""
        try:
            agents_dir = Path(proj) / ".claude" / "agents"
            fm_model, _conf = _read_archetype_model_frontmatter(
                archetype, agents_dir
            )
            recommended_model = (fm_model or "")[:64]
        except Exception:  # noqa: BLE001 — telemetry enrichment is optional
            recommended_model = ""

        # decision enum: enforce_telemetry | advisory | eval_error.
        # NO `block` value — block deferred (§2.4). Derived from the
        # AUTHORITATIVE is_enforcing() boolean (NOT a re-derivation from
        # the `mode` string), so the kill-switch demotion already folded
        # into is_enforcing() drives the decision. `mode` (possibly
        # demoted to "advisory" by get_mode) is still recorded verbatim.
        decision = "enforce_telemetry" if is_enforcing else "advisory"

        try:
            _audit_emit.emit_generic(
                "model_routing_enforced",
                archetype=archetype[:64],
                mode=str(mode)[:16],
                recommended_model=recommended_model,
                killswitch_armed=killswitch_armed,
                decision=decision,
                session_id=session_id,
                project=str(proj)[:256],
            )
        except Exception:  # noqa: BLE001 — fail-open
            return
    except Exception:  # pragma: no cover — fail-open invariant
        return


# PLAN-091 Wave A.4 (W3.1) — archetype → mcp_routing task_class heuristic.
#
# Maps the spawn's archetype to one of the 4 task_class strings declared in
# `_lib/mcp_routing._ROUTING_TABLE`. mcp_routing.resolve() emits its own
# `mcp_route_advised` advisory (PLAN-086 Wave D) — the spawn-hook wire only
# needs to trigger the resolver at the right callsite. NO mapping fallthrough
# = NO emit (advisory-only; avoid noise on every spawn).
_MCP_ARCHETYPE_TASK_CLASS_HINTS: Tuple[Tuple[Tuple[str, ...], str], ...] = (
    # ORDER MATTERS — first match wins. More-specific archetype slugs
    # (finops/seo/crypto) come BEFORE the bare "architect" pattern so
    # composite slugs like "llm-finops-architect" or "crypto-research-
    # analyst" route to the more specific MCP server bundle.
    (("finops", "cost", "budget"), "finops"),
    (("seo", "ahrefs", "similarweb"), "seo_research"),
    (("crypto", "lunarcrush", "blockchain"), "crypto_research"),
    (("architect", "arch-"), "arch"),
)


# PLAN-091 Wave A.5 (W3.3) — archetype-hint patterns triggering a
# `specialization_promoted` advisory when subagent_type == general-purpose.
# Match is FIRST-HIT, not exhaustive — keeps emit volume bounded. Hints
# are lowercase substring matches on (description + prompt).
_PROMOTION_ARCHETYPE_HINTS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("performance-engineer",
     ("latency", "p95", "p99", "profile", "memory leak", "throughput",
      "gc tuning", "hot path")),
    ("security-engineer",
     ("jwt", "oauth", "authentication", "vulnerability", "owasp",
      "xss", "sql injection", "csrf", "rate limiting")),
    ("qa-architect",
     ("test strategy", "mutation testing", "flake", "regression",
      "property-based", "fuzz", "contract test")),
    ("code-reviewer",
     ("merge gate", "code review", "veto", "review checklist")),
    ("incident-commander",
     ("incident commander", "severity classification", "all-clear",
      "paging policy", "post-incident review")),
    ("identity-trust-architect",
     ("token rotation", "session lifecycle", "rbac", "abac",
      "service-to-service trust", "mtls")),
    ("threat-detection-engineer",
     ("mitre att&ck", "siem rule", "detection rule", "alert deduplication",
      "purple team", "threat hunting")),
    ("devops",
     ("github actions", "sha-pin", "ci/cd pipeline", "rollback strategy",
      "secret rotation")),
)


def _emit_mcp_routing_advisory(
    *,
    description: str,
    prompt: str,
    subagent_type: str,
    env: Optional[Dict[str, str]] = None,
) -> None:
    """PLAN-091 Wave A.4 (W3.1) — emit `mcp_route_advised` for this spawn.

    Derives task_class from the spawn's archetype via the
    ``_MCP_ARCHETYPE_TASK_CLASS_HINTS`` table, then delegates to
    ``_lib/mcp_routing.resolve()`` which performs its own emit (per
    PLAN-086 Wave D). Bypass: ``CEO_MCP_ROUTING_HOOK=0`` (parallel to
    PLAN-078 model-routing bypass; per-server kill switches live inside
    mcp_routing.resolve()).

    NEVER raises. Advisory-only — never mutates tool_input, never blocks.
    """
    try:
        src_env = env if env is not None else os.environ
        if (src_env.get("CEO_MCP_ROUTING_HOOK") or "").strip() == "0":
            return
        archetype = _extract_archetype_from_payload(
            description or "", prompt or "", subagent_type or ""
        )
        if not archetype:
            return
        archetype_lc = archetype.lower()
        task_class: Optional[str] = None
        for hints, mapped in _MCP_ARCHETYPE_TASK_CLASS_HINTS:
            if any(h in archetype_lc for h in hints):
                task_class = mapped
                break
        if task_class is None:
            return  # no mapping; emit volume stays bounded
        try:
            from _lib import mcp_routing as _mcpr  # type: ignore
            _mcpr.resolve(task_class)  # resolver fires advisory emit
        except Exception:  # pragma: no cover - fail-open
            return
    except Exception:  # pragma: no cover - fail-open
        return


def _emit_promotion_advisory(
    *,
    description: str,
    prompt: str,
    subagent_type: str,
    env: Optional[Dict[str, str]] = None,
) -> None:
    """PLAN-091 Wave A.5 (W3.3) — emit `specialization_promoted` when a
    ``general-purpose`` spawn matches a specialist archetype heuristic.

    Advisory ONLY — does NOT auto-spawn the suggested specialist. Records
    the suggestion in audit log so PLAN-094+ can promote SEMI to AUTO once
    confidence is established. Bypass: ``CEO_PROMOTION_HEURISTIC=0``.

    First-hit match wins (bounded emit volume). NEVER raises.
    """
    try:
        src_env = env if env is not None else os.environ
        if (src_env.get("CEO_PROMOTION_HEURISTIC") or "").strip() == "0":
            return
        if (subagent_type or "").strip().lower() != "general-purpose":
            return
        if not _AUDIT_EMIT_AVAILABLE:
            return
        text = ((description or "") + "\n" + (prompt or "")).lower()
        text = text[: 8 * 1024]  # 8KiB cap on hint-scan window
        for suggested, hints in _PROMOTION_ARCHETYPE_HINTS:
            for hint in hints:
                if hint in text:
                    try:
                        # PLAN-088 R2 iter-2 STRICKEN specialization_promoted
                        # as separate action; routed via mcp_route_advised
                        # with signal_source discriminator per audit_emit.py
                        # 5099-5105 contract.
                        _audit_emit.emit_generic(
                            "mcp_route_advised",
                            session_id="",
                            task_class="promotion",
                            suggested_servers=suggested[:64],
                            kill_switch_overrides="",
                            signal_source="specialization_promoted",
                        )
                    except Exception:  # pragma: no cover - fail-open
                        pass
                    return  # first-hit wins
    except Exception:  # pragma: no cover - fail-open
        return


def _emit_advisory_safe(
    *,
    archetype: str,
    task_type: str,
    model_recommended: str,
    confidence: float,
    applied_or_skipped: str,
    override_reason: str,
) -> None:
    """Wrapper around audit_emit.emit_generic for `model_routing_advised`.

    Allowlist enforced by audit_emit dispatcher (defense-in-depth). Caller
    only fills the 6 contract fields; ts/session/project added by emit_generic.

    Codex W1+W2 fix-pack #2: ``confidence`` (float 0..1) is converted at
    emission time to ``confidence_basis_points`` (int 0..1000) — floats
    are forbidden in HMAC-covered fields (canonical_json invariant). The
    in-process API surface still accepts ``confidence: float`` for
    ergonomic continuity; conversion is colocated with the emit call.
    """
    try:
        if not _AUDIT_EMIT_AVAILABLE:
            return
        # Convert float confidence -> int basis-points. NaN / out-of-range
        # collapse to 0 (lower clamp in audit_emit emitter).
        try:
            conf_f = float(confidence)
        except (TypeError, ValueError):
            conf_f = 0.0
        if conf_f != conf_f or conf_f in (float("inf"), float("-inf")):
            conf_f = 0.0
        if conf_f < 0.0:
            conf_f = 0.0
        if conf_f > 1.0:
            conf_f = 1.0
        confidence_bp = int(round(conf_f * 1000.0))
        # Length-bound caller strings (defense-in-depth on adopter drift).
        _audit_emit.emit_generic(
            "model_routing_advised",
            archetype=(archetype or "")[:64],
            task_type=(task_type or "")[:32],
            model_recommended=(model_recommended or "")[:64],
            confidence_basis_points=confidence_bp,
            applied_or_skipped=(applied_or_skipped or "")[:64],
            override_reason=(override_reason or "")[:128],
        )
    except Exception:  # pragma: no cover - fail-open
        return


# Persona header patterns — must appear at the START of a line.
_PERSONA_HEADER_RE = re.compile(
    r"^(?:PERSONA:|## AGENT PROFILE|## PERSONA)",
    flags=re.MULTILINE,
)

# Governance requirement: named spawns must include this literal section.
_SKILL_CONTENT_MARKER = "## SKILL CONTENT"

# PLAN-019 Phase 2B P1-SEC-B — minimum body size (non-whitespace bytes)
# required between `## SKILL CONTENT` and the next `##` heading / EOF for
# the marker to count as a real skill-content section. Rejects empty-body,
# stub-only, or single-line "see file X" shells.
_SKILL_CONTENT_MIN_BYTES = 256

# Regex to find the marker ON ITS OWN LINE (ignoring trailing whitespace).
_SKILL_CONTENT_MARKER_RE = re.compile(
    r"^## SKILL CONTENT[ \t]*$",
    flags=re.MULTILINE,
)

# Regex to find the next `##`-level heading (to bound the body extraction).
_NEXT_H2_RE = re.compile(r"^##[ \t]", flags=re.MULTILINE)

# Code-fence markers (``` or ~~~ with optional language tag).
_CODE_FENCE_RE = re.compile(r"^(?:```|~~~)", flags=re.MULTILINE)

# HTML comment pair — non-greedy across lines.
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", flags=re.DOTALL)

# Regex to extract ## SPEC CONTEXT block content (between its header and next
# ## heading or EOF). Used by _sanitize_spec_context_advisory() below.
_SPEC_CONTEXT_HEADER_RE = re.compile(
    r"^##[ \t]+SPEC[ \t]+CONTEXT[ \t]*$",
    flags=re.MULTILINE,
)


def _sanitize_spec_context_advisory(prompt: str, env=None) -> None:
    """PLAN-113 WIRE-DEADMOD / ADR-089 SEC-P0-01 — sanitize ## SPEC CONTEXT
    payload and emit telemetry advisory.

    Extracts the ## SPEC CONTEXT block from the spawn prompt, runs it
    through spec_context_sanitizer.sanitize(), and emits a
    `spec_context_sanitized` audit-emit event so sentinel violations,
    truncation, and control-char counts are observable.

    ADVISORY ONLY — never blocks the spawn. Fail-open on any exception.
    Kill-switch: CEO_SPEC_CTX_SANITIZER_ENABLED=0.
    """
    try:
        if not _SPEC_CTX_SANITIZER_AVAILABLE or not _AUDIT_EMIT_AVAILABLE:
            return
        src_env = env if env is not None else os.environ
        val = (src_env.get("CEO_SPEC_CTX_SANITIZER_ENABLED") or "1").strip()
        if val in ("0", "false", "False", "no", "off"):
            return
        if not prompt:
            return
        # Extract ## SPEC CONTEXT block content
        m = _SPEC_CONTEXT_HEADER_RE.search(prompt)
        if m is None:
            return  # no SPEC CONTEXT block — nothing to sanitize
        block_start = m.end()
        next_h2 = _NEXT_H2_RE.search(prompt, block_start)
        block_end = next_h2.start() if next_h2 else len(prompt)
        spec_payload = prompt[block_start:block_end]

        result = _spec_ctx_sanitizer.sanitize(spec_payload)

        # Emit telemetry (advisory only; sentinel violations logged for CEO)
        try:
            _audit_emit.emit_generic(
                "spec_context_sanitized",
                original_bytes=result.original_bytes,
                cleaned_bytes=result.cleaned_bytes,
                truncated=1 if result.truncated else 0,
                sentinel_violations=len(result.sentinel_violations),
                control_chars_stripped=result.control_chars_stripped,
                bidi_zw_chars_stripped=result.bidi_zw_chars_stripped,
                # PLAN-133 A2 — surface the Tag-block count too (allowlisted in
                # audit_emit §7d). Harmless if the SanitizeResult lacks the field
                # (getattr default 0) so this stays import-order tolerant.
                tag_chars_stripped=getattr(result, "tag_chars_stripped", 0),
                header_escape_count=result.header_escape_count,
            )
        except Exception:  # pragma: no cover - fail-open
            pass
    except Exception:  # pragma: no cover - fail-open
        return


def _enforce_spec_context_unicode(prompt: str, env=None):
    """PLAN-133 A2 — fail-CLOSED invisible-unicode guard on the spawn prompt.

    Scans the WHOLE spawn prompt (not just the ## SPEC CONTEXT block — an attacker
    can smuggle Tag-block/bidi chars anywhere in the named-spawn body) for invisible
    /smuggling unicode (control / bidi / zero-width / U+E0000-E007F Tag-block).

    Default-OFF (doctrine #1): the BLOCK fires only when CEO_UNICODE_HARDBLOCK=='1'
    in the import-time trusted_env snapshot. Otherwise advisory — the breadcrumb is
    emitted with enforced=0 (measure-first) and None is returned (no block).

    Returns a block-reason string when enforced AND a detection fires, else None.
    Fail-OPEN on any infra exception (never blocks the session on a scanner bug).
    Master kill: CEO_SOTA_DISABLE=1 forces advisory.
    """
    try:
        if not _SPEC_CTX_SANITIZER_AVAILABLE:
            return None
        src_env = env if env is not None else os.environ
        if not prompt:
            return None
        # Default-OFF flag, read from the trusted_env snapshot when available so a
        # late-set value can't toggle enforcement mid-process. Master kill wins.
        if (src_env.get("CEO_SOTA_DISABLE") or "").strip() == "1":
            enforce = False
        else:
            enforce = _unicode_hardblock_enforced(src_env)

        result = _spec_ctx_sanitizer.sanitize(prompt)
        count = _spec_ctx_sanitizer.invisible_unicode_count(result)
        if count <= 0:
            return None  # clean — nothing to do

        unicode_class = _spec_ctx_sanitizer.classify_invisible_unicode(result)

        # Emit the closed-enum breadcrumb on BOTH advisory and enforced paths
        # (the denominator must be real from day one — no 0/0/0 trap).
        if _AUDIT_EMIT_AVAILABLE:
            try:
                _audit_emit.emit_generic(
                    "invisible_unicode_blocked",
                    surface="spawn",
                    unicode_class=unicode_class,
                    char_count=int(count),
                    enforced=1 if enforce else 0,
                )
            except Exception:  # pragma: no cover - fail-open
                pass

        if not enforce:
            return None  # advisory only

        return (
            "GOVERNANCE: invisible_unicode_blocked: the spawn prompt contains "
            f"{count} invisible/smuggling character(s) (class={unicode_class}: "
            "control / bidi / zero-width / Unicode-Tags-block). These are "
            "removed by the sanitizer and rejected fail-CLOSED before review. "
            "Remove the hidden characters and re-spawn. To run advisory-only, "
            "unset CEO_UNICODE_HARDBLOCK."
        )
    except Exception:  # pragma: no cover - fail-open invariant
        return None


def _unicode_hardblock_enforced(src_env) -> bool:
    """True iff CEO_UNICODE_HARDBLOCK=='1' (PLAN-133 A2). Prefers the trusted_env
    snapshot; falls back to the passed env dict. Pure; never raises."""
    try:
        from _lib import trusted_env as _te  # noqa: E402
        val = _te.get_trusted("CEO_UNICODE_HARDBLOCK")
        if val is not None:
            return (val or "").strip() == "1"
    except Exception:  # pragma: no cover
        pass
    return (src_env.get("CEO_UNICODE_HARDBLOCK") or "").strip() == "1"


def _emit_spawn_confidence_advisory(
    *,
    action_type: str,
    is_named_spawn: bool,
    env=None,
) -> None:
    """PLAN-113 WIRE-DEADMOD — confidence_labels (PLAN-083 Wave 1.10).

    Classifies the spawn as an action and emits `spawn_confidence_advisory`
    so recommender / receipt formatter surfaces have a hook-level confidence
    signal for governance dashboards.

    ADVISORY ONLY — never blocks. Fail-open on any exception.
    Kill-switch: CEO_SPAWN_CONFIDENCE_ENABLED=0.
    """
    try:
        if not _CONFIDENCE_LABELS_AVAILABLE or not _AUDIT_EMIT_AVAILABLE:
            return
        src_env = env if env is not None else os.environ
        val = (src_env.get("CEO_SPAWN_CONFIDENCE_ENABLED") or "1").strip()
        if val in ("0", "false", "False", "no", "off"):
            return

        ctx = {"canonical": False}
        conf = _confidence_labels.classify(action_type, ctx)
        marker = _confidence_labels.as_emoji_free_marker(conf)

        try:
            _audit_emit.emit_generic(
                "spawn_confidence_advisory",
                action_type=(action_type or "")[:32],
                confidence_level=(conf.level or "")[:32],
                confidence_marker=(marker or "")[:32],
                reason_code=(conf.reason_code or "")[:64],
                is_named_spawn=1 if is_named_spawn else 0,
            )
        except Exception:  # pragma: no cover - fail-open
            pass
    except Exception:  # pragma: no cover - fail-open
        return
