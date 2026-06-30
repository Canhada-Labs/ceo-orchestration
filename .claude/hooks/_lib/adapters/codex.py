"""Codex MCP hook adapter — PLAN-081 Phase 1-full (R1 5/5 ADJUST PROCEED).

This adapter completes the SPEC v1 hook adapter ABI for the Codex MCP
provider, mirroring ``claude.py``. While Codex is not the host emitter
of PreToolUse / PostToolUse events (Claude Code is the host), the
adapter is registered in ``ADAPTER_REGISTRY`` for symbolic parity:

- Future routing / observability surfaces can reference ``"codex"`` the
  same way they reference ``"claude"``.
- The Pair-Rail dispatcher (PLAN-081 Phase 2) routes coder vs reviewer
  via this adapter's identity.
- Tooling (``audit-query.py by-provider``) can pivot on the adapter
  name without provider-specific shims.

The adapter ALSO provides Codex-specific helpers consumed by the
Pair-Rail subsystem:

- ``_classify_prompt_complexity(prompt) -> Literal["simple","audit"]``
  drives the 75s-vs-240s timeout split per R1 C7 (PLAN-081 §3 Phase 1
  exit criteria item 4).
- ``parse_verdict(stdout: str) -> dict`` parses Codex CLI JSON output
  into a normalized verdict envelope used by ``check_pair_rail.py``.
- ``make_invoke_command(prompt, model, sandbox_mode, timeout_s)``
  builds the argv vector for ``scripts/codex_invoke.py`` subprocess
  invocation. The argv shape is pinned by SPEC v1 mcp-server.schema.md.

Wire shape: when Claude Code emits a PostToolUse event for an
``mcp__codex__codex`` or ``mcp__codex__codex-reply`` tool call, the
``tool_response`` field carries the Codex MCP server's JSON response.
``read_post_event`` parses that envelope and surfaces the Codex stdout
as ``raw_payload['codex_stdout']`` for downstream consumers.

ABI compliance: SPEC/v1/adapters.schema.md §3. fail-open invariant
preserved — any parse error returns ``NormalizedEvent(parse_error=...)``;
adapter NEVER raises to the hook caller. Credential hygiene §4.1
honored — the adapter reads no API keys; ``OPENAI_API_KEY`` is consumed
by the host (Codex MCP server), not by this adapter.
"""

from __future__ import annotations

import json
import re
import sys
from typing import IO, Any, Dict, List, Optional, Tuple

from .. import contract as _contract
from .. import payload as _payload

# ---------------------------------------------------------------------------
# Module-level constants per SPEC/v1/adapters.schema.md §2
# ---------------------------------------------------------------------------

#: SemVer for the adapter implementation. Bump per SPEC §2.1.
ADAPTER_VERSION: str = "1.0.0-rc.1"

#: Provider capabilities per SPEC §2.2.
CAPABILITIES: Dict[str, Any] = {
    "streaming_tool_use": False,
    "json_mode": "advisory",
    "function_calling": True,
    "system_prompt_slot": True,
}

#: Audit-emit field allowlist per Sec MF-3. ``audit_emit.py`` consumers
#: of this adapter MUST whitelist ONLY these fields when persisting
#: cross-LLM dispatch records.
AUDIT_EMIT_KEYS: Tuple[str, ...] = (
    "agent_provider",
    "pair_id",
    "wall_clock_s",
    "retry_at_timeout_s",
    "verdict",
    "rubric_violation_id",
    "severity",
    "codex_cli_version",
)

# ---------------------------------------------------------------------------
# Timeout classifier (R1 C7) — Phase 0A SPIKE-VERDICT empirical baseline
# ---------------------------------------------------------------------------
#
# Phase 0A measurement (PLAN-075 SPIKE-VERDICT.md U3): N=20 simple
# prompts → median 6.82s, p99 ~22s. R1 C7 codifies the classifier:
# simple ≤75s deadline; audit-class ≤240s deadline + 1 retry. The
# 75s ceiling absorbs p99 + headroom; 240s covers full schema-walk
# audits per R1 C7 + S-Sec-1 single-pass redactor scope.

#: Hard timeout deadline for "simple" prompts (single-fact lookups,
#: yes/no rubrics, per-line code review).
DEFAULT_TIMEOUT_SIMPLE_S: int = 75

#: Hard timeout deadline for "audit-class" prompts (multi-file review,
#: SPEC traversal, schema walk). Includes 1 retry budget.
DEFAULT_TIMEOUT_AUDIT_S: int = 240

#: Audit-class trigger keywords. Presence of ANY token causes the
#: classifier to return ``"audit"``. Tokens chosen empirically from
#: PLAN-075 + PLAN-077 archetype prompt corpus (R1 C7 codifies).
_AUDIT_CLASS_KEYWORDS: Tuple[str, ...] = (
    "audit",
    "review the entire",
    "review all",
    "every test",
    "check every",
    "schema walk",
    "compliance",
    "spec",
    "p0",
    "round 2",
    "consensus",
    "deep review",
    "exhaustive",
)


def _classify_prompt_complexity(prompt: str) -> str:
    """Classify a prompt as ``"simple"`` or ``"audit"`` per R1 C7.

    Args:
        prompt: the user-or-dispatcher-supplied prompt text.

    Returns:
        ``"simple"`` if no audit-class keyword matches AND prompt
        ≤512 chars. Otherwise ``"audit"``.

    The classifier is intentionally simple — case-insensitive
    substring match + length heuristic. Sophistication (LLM-judged
    classification) was rejected per R1 (would create circular
    dependency: classifier consumes Codex; Codex consumes classifier).

    NEVER raises. Empty / None / non-str inputs map to ``"simple"``
    (fail-permissive — the worse outcome of a mis-classified audit
    prompt is hitting the 75s deadline + 1 retry, which still fits
    under 240s).
    """
    if not prompt or not isinstance(prompt, str):
        return "simple"
    if len(prompt) > 512:
        return "audit"
    lowered = prompt.lower()
    for kw in _AUDIT_CLASS_KEYWORDS:
        if kw in lowered:
            return "audit"
    return "simple"


def _resolve_timeout_s(prompt: str) -> int:
    """Resolve the timeout deadline for a given prompt.

    Wrapper over ``_classify_prompt_complexity`` returning the
    corresponding ``DEFAULT_TIMEOUT_*_S`` value. Used by
    ``scripts/codex_invoke.py`` and ``check_pair_rail.py`` so the
    routing logic lives ONLY here.
    """
    if _classify_prompt_complexity(prompt) == "audit":
        return DEFAULT_TIMEOUT_AUDIT_S
    return DEFAULT_TIMEOUT_SIMPLE_S


# ---------------------------------------------------------------------------
# Hook ABI per SPEC §3 (read_event / read_post_event / write_decision /
# emit_decision)
# ---------------------------------------------------------------------------


def read_event(
    stream: "Optional[IO[str]]" = None,
    phase: str = "PreToolUse",
) -> _contract.NormalizedEvent:
    """Parse a hook payload (Codex MCP context) into a NormalizedEvent.

    Behavior parity with ``claude.py:read_event`` (SPEC §3.1). When
    ``tool_name`` matches ``mcp__codex__codex`` or ``mcp__codex__codex-reply``,
    the Codex stdout is preserved in ``raw_payload['codex_stdout']``
    (PostToolUse only) so ``check_codex_response.py`` can ingress-scan
    it without re-parsing JSON.

    Fail-open: any parse failure returns ``NormalizedEvent(parse_error=...)``.
    NEVER raises to the hook caller (SPEC §4).
    """
    if phase not in ("PreToolUse", "PostToolUse"):
        phase = "PreToolUse"

    if stream is None:
        stream = sys.stdin

    try:
        p = _payload.parse_stdin(stream=stream)
    except Exception as e:  # pragma: no cover (defensive)
        return _contract.NormalizedEvent(
            parse_error=f"[codex] stdin read failed: {type(e).__name__}",
            phase=phase,
        )

    import os as _os

    if p.raw_error:
        return _contract.NormalizedEvent(
            parse_error=f"[codex] {p.raw_error}",
            session_id=p.session_id or "",
            tool_name=p.tool_name or "",
            phase=phase,
            raw_payload={},
        )

    tool_input = p.tool_input if isinstance(p.tool_input, dict) else {}
    tool_response = p.tool_response if isinstance(p.tool_response, dict) else {}

    # Codex-specific: preserve stdout for ingress sanitization
    raw_payload: Dict[str, Any] = {}
    tool_name = p.tool_name or ""
    if (
        phase == "PostToolUse"
        and tool_name in ("mcp__codex__codex", "mcp__codex__codex-reply")
    ):
        # Codex MCP server returns ``{"content": [{"type":"text","text":"..."}]}``
        # We surface the concatenated text as raw_payload['codex_stdout'].
        codex_stdout = _extract_codex_stdout(tool_response)
        if codex_stdout:
            raw_payload["codex_stdout"] = codex_stdout

    return _contract.NormalizedEvent(
        session_id=p.session_id or "",
        project=_os.environ.get("CLAUDE_PROJECT_DIR") or "",
        phase=phase,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_response=tool_response,
        description=p.description or "",
        prompt=p.prompt or "",
        subagent_type=str(tool_input.get("subagent_type") or p.subagent_type or ""),
        file_path=str(tool_input.get("file_path") or ""),
        old_string=str(tool_input.get("old_string") or ""),
        new_string=str(tool_input.get("new_string") or ""),
        replace_all=bool(tool_input.get("replace_all") or False),
        command=str(tool_input.get("command") or ""),
        raw_payload=raw_payload,
    )


def read_post_event(stream: "Optional[IO[str]]" = None) -> _contract.NormalizedEvent:
    """Convenience: PostToolUse parse. SPEC §3.2."""
    return read_event(stream=stream, phase="PostToolUse")


def write_decision(decision: _contract.Decision) -> str:
    """Serialize a Decision to single-line JSON. SPEC §3.3.

    Key ordering matches ``claude.py:write_decision`` (Claude Code is
    the host IDE; output shape MUST match what the host expects).
    """
    out: Dict[str, Any] = {"decision": "allow" if decision.allow else "block"}
    if not decision.allow and decision.reason:
        out["reason"] = decision.reason
    if decision.system_message:
        out["systemMessage"] = decision.system_message
    if decision.message:
        out["message"] = decision.message
    for k, v in decision.extra.items():
        if k not in out:
            out[k] = v
    return json.dumps(out, ensure_ascii=False)


def emit_decision(
    decision: _contract.Decision,
    stream: "Optional[IO[str]]" = None,
) -> None:
    """Convenience: write decision + newline. SPEC §3.4."""
    if stream is None:
        stream = sys.stdout
    stream.write(write_decision(decision) + "\n")


# ---------------------------------------------------------------------------
# Codex MCP response helpers
# ---------------------------------------------------------------------------


def _extract_codex_stdout(tool_response: Dict[str, Any]) -> str:
    """Extract concatenated text from a Codex MCP response.

    Codex MCP server response shape:

        {
          "content": [
            {"type": "text", "text": "..."},
            ...
          ]
        }

    Returns the concatenated ``text`` fields. Empty string on any
    parse miss (fail-open).
    """
    if not isinstance(tool_response, dict):
        return ""
    content = tool_response.get("content")
    if not isinstance(content, list):
        return ""
    chunks: List[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            txt = item.get("text")
            if isinstance(txt, str):
                chunks.append(txt)
    return "\n".join(chunks)


# ---------------------------------------------------------------------------
# Verdict parser — Codex CLI JSON output → normalized envelope
# ---------------------------------------------------------------------------

#: Verdict values per ADR-106 / ADR-108 (Pair-Rail asymmetric VETO).
_VALID_VERDICTS: Tuple[str, ...] = ("PASS", "ADVISORY", "BLOCK")


# PLAN-086 Wave A.6 (Sec-1 fold) — strict-JSON size cap (256 KB).
_STRICT_JSON_SIZE_CAP_BYTES = 256 * 1024


def _read_structured_verdict_object(content: Optional[str]) -> Dict[str, Any]:
    """Parse ONE structured verdict object from last-message content.

    PLAN-142 D1: the 0.139 last-message output file (written by the CLI-shape
    helper's ``-o`` flag — owned in ``_lib/codex_cli_shape.py``, NOT here)
    holds ONLY the final agent message: exactly ONE JSON object. NOT the
    event-stream stdout, NOT whole stdout. This is the single chokepoint
    where the untrusted object becomes a trusted, normalized dict, shared by
    ``parse_verdict`` (fail-OPEN) and ``parse_verdict_strict``
    (fail-CLOSED-to-ADVISORY).

    INPUT is the ALREADY-REDACTED last-message content. Redaction is the
    CALLER's job (the live rail redacts the full byte-string before calling;
    the promotion path redacts in codex_invoke.py) — this helper does NOT
    itself redact, keeping redaction at the single egress callsite (ADR-114).

    Returns a dict ALWAYS containing:
      - ``ok``       (bool)          — True iff a valid, schema-shaped verdict.
      - ``verdict``  (Optional[str]) — the raw verdict string IF present.
      - ``findings`` (List[Dict])    — normalized findings (empty on miss).
      - ``summary``  (str)
      - ``error``    (Optional[str]) — short, payload-free reason on failure.

    NEVER raises. NEVER returns or logs the raw object contents in ``error``
    (payload-free), so a malformed-but-secret-bearing message cannot leak via
    the error string.
    """
    if not content or not isinstance(content, str):
        return {"ok": False, "verdict": None, "findings": [], "summary": "",
                "error": "[codex] empty last-message content"}

    # Size cap (trust-boundary DoS guard). errors="replace" so an undecodable
    # tail cannot raise here.
    if len(content.encode("utf-8", errors="replace")) > _STRICT_JSON_SIZE_CAP_BYTES:
        return {"ok": False, "verdict": None, "findings": [], "summary": "",
                "error": "[codex] last-message exceeds 256 KB cap"}

    cleaned = _strip_codex_envelope(content)
    if not cleaned:
        return {"ok": False, "verdict": None, "findings": [], "summary": "",
                "error": "[codex] last-message empty after envelope strip"}

    # The SINGLE json.loads of ONE object (not a line stream).
    try:
        obj = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as e:
        lineno = getattr(e, "lineno", "?")
        return {"ok": False, "verdict": None, "findings": [], "summary": "",
                "error": "[codex] last-message JSON decode at line {0}".format(lineno)}

    if not isinstance(obj, dict):
        return {"ok": False, "verdict": None, "findings": [], "summary": "",
                "error": "[codex] last-message top-level not a JSON object"}

    # Trust-boundary (PLAN-142 V2 cross-model fold): require the FULL schema
    # shape — verdict in _VALID_VERDICTS AND findings is a list AND summary is
    # a str — for ok=True. A partial/mistyped object (e.g. {"verdict":"PASS"}
    # with missing findings/summary) is schema-nonconforming and must NOT be
    # trusted as a clean verdict; it degrades to the caller's miss policy
    # (fail-CLOSED-to-ADVISORY on the strict rail). When the CLI-enforced output
    # schema is applied the generator guarantees all three; this guards the
    # no-schema paths (codex_invoke / the rail's schema-file-creation fallback).
    verdict = obj.get("verdict")
    findings_raw = obj.get("findings")
    summary = obj.get("summary")

    findings: List[Dict[str, Any]] = []
    findings_is_list = isinstance(findings_raw, list)
    if findings_is_list:
        for fitem in findings_raw:
            if isinstance(fitem, dict):
                findings.append(_normalize_finding(fitem))

    if (verdict not in _VALID_VERDICTS
            or not findings_is_list
            or not isinstance(summary, str)):
        return {"ok": False,
                "verdict": verdict if isinstance(verdict, str) else None,
                "findings": findings,
                "summary": summary if isinstance(summary, str) else "",
                "error": "[codex] last-message not schema-conforming (verdict/findings/summary)"}

    return {"ok": True, "verdict": verdict, "findings": findings,
            "summary": summary, "error": None}


def parse_verdict_strict(last_message: str) -> Dict[str, Any]:
    """Strict verdict parse for the LIVE pair-rail consume path (PLAN-142).

    ``last_message`` is the ALREADY-REDACTED content of the codex-cli 0.139
    last-message output file — exactly one JSON object (the final agent
    message). fail-CLOSED-to-ADVISORY: on ANY miss (empty / oversize /
    non-JSON / non-object / bad verdict) returns a normalized ADVISORY
    envelope with ``parse_error`` set — it NEVER raises and NEVER returns
    PASS/BLOCK on a malformed response (forged free-text 'PASS' with no
    structured verdict -> ADVISORY, satisfying R-SEC-2).

    DELIBERATE behavior change from the pre-PLAN-142 raising version (which
    targeted the removed whole-stdout strict path the live rail never
    actually called). The old typed exceptions (CodexResponseTooLarge /
    CodexJsonInvalid) are NO LONGER RAISED here; they remain defined in
    ``_lib/exceptions.py`` for other references.

    Returns a dict ALWAYS containing ``verdict`` (str in _VALID_VERDICTS),
    ``findings`` (List[Dict]), ``summary`` (str), ``parse_error``
    (Optional[str]). NEVER raises.
    """
    result = _read_structured_verdict_object(last_message)
    if result["ok"]:
        return {"verdict": result["verdict"], "findings": result["findings"],
                "summary": result["summary"], "parse_error": None}
    # fail-CLOSED-to-ADVISORY: any miss -> ADVISORY, never PASS/BLOCK, no raise.
    return {"verdict": "ADVISORY", "findings": result.get("findings", []),
            "summary": result.get("summary", ""),
            "parse_error": result.get("error") or "[codex] strict verdict unavailable"}


def parse_verdict(last_message: str) -> Dict[str, Any]:
    """Parse the Codex 0.139 last-message object into a verdict envelope.

    ADR-106 fail-OPEN: parse miss coerces ``verdict`` to ``"ADVISORY"``
    (Codex is advisory by default; never blocks on a parse miss).
    ``last_message`` is the ALREADY-REDACTED content of the last-message
    output file (exactly one JSON object), NOT raw stdout, NOT a line stream.

    CONTRACT CHANGE (PLAN-142): this now reads ONE structured object (the
    last-message content), NOT whole-stdout. The sole production caller
    ``scripts/codex_invoke.py`` is migrated this ceremony to pass the
    last-message file content.

    Returns a dict ALWAYS containing ``verdict`` (str — coerced to
    ``"ADVISORY"`` on miss), ``findings`` (List[Dict], possibly empty),
    ``summary`` (str), ``parse_error`` (Optional[str]). NEVER raises.
    """
    result = _read_structured_verdict_object(last_message)
    if result["ok"]:
        return {"verdict": result["verdict"], "findings": result["findings"],
                "summary": result["summary"], "parse_error": None}
    # fail-OPEN coercion per ADR-106. Preserve findings/summary if the object
    # parsed but the verdict was absent/invalid; surface a payload-free reason.
    return {"verdict": "ADVISORY", "findings": result.get("findings", []),
            "summary": result.get("summary", ""),
            "parse_error": result.get("error") or "[codex] verdict unavailable; coerced to ADVISORY"}


_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_MD_FENCE_RE = re.compile(r"^```(?:json)?\s*\n", re.MULTILINE)
_MD_FENCE_END_RE = re.compile(r"\n```\s*$", re.MULTILINE)


def _strip_codex_envelope(stdout: str) -> str:
    """Strip ANSI / markdown fence wrappers around Codex JSON output."""
    s = _ANSI_ESCAPE_RE.sub("", stdout)
    s = _MD_FENCE_RE.sub("", s)
    s = _MD_FENCE_END_RE.sub("", s)
    return s.strip()


def _normalize_finding(item: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce a raw finding dict to the normalized shape."""
    severity = item.get("severity")
    if severity not in ("P0", "P1"):
        severity = "P1"  # default conservative
    return {
        "rubric_violation_id": str(item.get("rubric_violation_id") or "RV-UNKNOWN"),
        "severity": severity,
        "file": str(item.get("file") or ""),
        "line": int(item.get("line") or 0) if str(item.get("line") or "").isdigit() else 0,
        "rationale": str(item.get("rationale") or ""),
    }


# ---------------------------------------------------------------------------
# Token-usage extraction — NON-kernel promotion path ONLY.
# ---------------------------------------------------------------------------
#
# PLAN-142 §3 (R-VP-A / R-OPS-3 / R-SEC-5): the live rail DROPS usage
# telemetry (no consumer, last-message file only). ONLY the promotion path
# requests the per-line event stream and wants token counts. On codex-cli
# 0.139 that stream is JSONL on stdout (one JSON object per line) — so a
# single whole-stdout json.loads gives "Extra data line 2". This reads the
# stream PER LINE (try/except each line) and takes the LAST event carrying
# usage/token-count fields. Parse counts ONLY (no token *text* per Sec MF-3).
# Fail-open: absence → all-zeros, never an error (usage must never block a
# dispatch decision).
# ---------------------------------------------------------------------------


def parse_usage_from_codex_stdout(stdout: str) -> Dict[str, Any]:
    """Extract token counts + model from a codex-cli 0.139 JSONL event stream.

    PLAN-142 §3 rewrite. ``stdout`` is the raw per-line event stream (JSONL:
    one JSON object per line). Iterates line-by-line (try/except each line so
    a single malformed line can't abort the scan), and takes the LAST line
    that carries usage / token-count fields. Used ONLY by the non-kernel
    promotion path (codex_invoke.py / run-promotion-gate.py) — the live rail
    consciously DROPS usage (R-SEC-5).

    Returns a dict ALWAYS containing ``tokens_in`` (int >=0), ``tokens_out``
    (int >=0), ``tokens_total`` (int >=0), ``model`` (str), ``parse_error``
    (Optional[str]). Degrades to all-zeros on absence. NEVER raises.
    """
    fallback: Dict[str, Any] = {
        "tokens_in": 0,
        "tokens_out": 0,
        "tokens_total": 0,
        "model": "",
        "parse_error": None,
    }
    if not stdout or not isinstance(stdout, str):
        fallback["parse_error"] = "[codex] empty stdout"
        return fallback

    def _coerce_int(v: Any) -> int:
        try:
            n = int(v)
        except (TypeError, ValueError):
            return 0
        return max(0, n)

    def _usage_from_obj(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return a usage dict from one event, or None if it carries none.

        Accepts several 0.139 event shapes defensively: a nested ``usage``
        object (input_tokens/output_tokens/total_tokens, or the OpenAI-ish
        prompt_tokens/completion_tokens), a token-count-typed event, or flat
        token integers at top level. Model id, if present, captured too.
        """
        if not isinstance(obj, dict):
            return None
        usage = obj.get("usage")
        src: Optional[Dict[str, Any]] = None
        if isinstance(usage, dict):
            src = usage
        elif any(
            k in obj
            for k in (
                "input_tokens", "output_tokens", "total_tokens",
                "prompt_tokens", "completion_tokens",
            )
        ):
            src = obj
        if src is None:
            return None
        tin = _coerce_int(src.get("input_tokens") or src.get("prompt_tokens"))
        tout = _coerce_int(src.get("output_tokens") or src.get("completion_tokens"))
        ttot = _coerce_int(src.get("total_tokens"))
        model = obj.get("model")
        if not isinstance(model, str):
            model = ""
        return {"tokens_in": tin, "tokens_out": tout, "tokens_total": ttot, "model": model}

    last_usage: Optional[Dict[str, Any]] = None
    last_model: str = ""
    saw_any_json_line = False

    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Strip ANSI defensively (a stray color code shouldn't break json.loads).
        line = _ANSI_ESCAPE_RE.sub("", line)
        try:
            ev = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            # Tolerate non-JSON lines (banners, progress) — skip, don't abort.
            continue
        if not isinstance(ev, dict):
            continue
        saw_any_json_line = True
        ev_model = ev.get("model")
        if isinstance(ev_model, str) and ev_model:
            last_model = ev_model
        u = _usage_from_obj(ev)
        if u is not None:
            last_usage = u  # keep the LAST usage-bearing event

    if last_usage is None:
        fallback["model"] = last_model
        if not saw_any_json_line:
            fallback["parse_error"] = "[codex] no JSON lines in event stream"
        return fallback

    model = last_usage.get("model") or last_model or ""
    return {
        "tokens_in": last_usage["tokens_in"],
        "tokens_out": last_usage["tokens_out"],
        "tokens_total": last_usage["tokens_total"],
        "model": model,
        "parse_error": None,
    }


# ---------------------------------------------------------------------------
# Invocation helpers — delegating wrappers over the non-kernel CLI-shape
# module (PLAN-142 D2).
# ---------------------------------------------------------------------------
#
# ALL argv construction, the reviewer model-id catalog, the sandbox enum,
# and the dead-flag migration live in ``_lib/codex_cli_shape.py`` (NON-kernel).
# The kernel keeps ONLY these thin wrappers so existing import sites
# (``codex.make_invoke_command(...)``) keep working while this kernel file
# holds ZERO CLI literals (§3 grep gate → the NEXT codex-cli bump is a
# non-kernel edit). The reviewer-output verdict on 0.139 is read from the
# helper-built last-message output file (a structured object), not stdout.


def make_invoke_command(
    prompt: str,
    model: Optional[str] = None,
    sandbox_mode: Optional[str] = None,
    timeout_s: Optional[int] = None,
    output_last_message_path: Optional[str] = None,
    output_schema_path: Optional[str] = None,
    json_events: bool = False,
    resume_thread_id: Optional[str] = None,
) -> List[str]:
    """DELEGATING wrapper over ``_lib.codex_cli_shape.make_invoke_command``.

    PLAN-142 D2: all CLI-shape (flags, model ids, dead-flag migration) lives
    in the non-kernel helper. This kernel wrapper exists ONLY to preserve the
    import site while keeping zero CLI literals in the kernel.

    Contract notes:
      - ``output_last_message_path`` is REQUIRED by the helper (the 0.139
        verdict is read from this file); passing None raises ValueError there.
      - ``model=None`` lets the helper apply ``DEFAULT_MODEL`` + LOUD
        unknown-model coercion. ``sandbox_mode=None`` maps to the helper's
        conservative default.
      - ``timeout_s`` is accepted for signature compatibility but is NOT a CLI
        flag — the caller applies it to ``subprocess.run(timeout=...)``.
      - ``json_events`` adds the per-line event stream (promotion path usage).
      - ``resume_thread_id`` truthy raises NotImplementedError (the resume
        flag was removed on 0.139; PLAN-142 does not reimplement it).

    Raises ValueError on empty prompt / missing output path (delegated),
    UnknownCodexModel on a bad model, NotImplementedError on resume.
    """
    from .. import codex_cli_shape as _shape  # non-kernel; lazy import
    return _shape.make_invoke_command(
        prompt,
        output_last_message_path=output_last_message_path,
        model=model,
        sandbox_mode=sandbox_mode,
        timeout_s=timeout_s,
        output_schema_path=output_schema_path,
        json_events=json_events,
        resume_thread_id=resume_thread_id,
    )


# ---------------------------------------------------------------------------
# Egress redaction wrapper (delegates to _lib/codex_egress_redact.py)
# ---------------------------------------------------------------------------


def compute_redaction_inputs(text: str) -> str:
    """Apply egress redaction to Codex output text.

    Thin wrapper over ``_lib.codex_egress_redact.redact()`` so callers
    can use the adapter as the single import surface. The redactor
    enforces R1 S-Sec-1 single-pass invariant — see that module for
    the actual ``scan_and_redact()`` call.

    Returns the redacted text. NEVER raises.
    """
    try:
        from .. import codex_egress_redact as _redact
        return _redact.redact(text)
    except Exception:
        # PLAN-085 Wave B.4 — fail-CLOSED inversion (F-A-SEC-0006-cf7d6abd).
        # Previous fail-OPEN behavior returned raw text on redactor import
        # failure; spec invariant is the egress path MUST NEVER pass raw.
        # Best-effort audit breadcrumb (advisory, may itself fail). NEVER
        # carry the failed prompt body — explicit `raise ... from None`
        # breaks the implicit __cause__ chain that would leak it.
        try:
            from .. import audit_emit as _audit_emit
            emit = getattr(_audit_emit, "emit_generic", None)
            if emit is not None:
                emit("codex_redact_import_failure")
        except Exception:
            pass
        from ..exceptions import RedactorImportFailed
        raise RedactorImportFailed(
            "Codex egress redactor module unavailable; fail-CLOSED per "
            "PLAN-085 Wave B.4 / ADR-114 §AC9 invariant."
        ) from None


# ---------------------------------------------------------------------------
# PLAN-085 Wave D.2 — defensive redact-then-invoke wrapper (ADR-114 §AC9).
# ---------------------------------------------------------------------------


def make_invoke_command_redacted(
    prompt: str,
    model: Optional[str] = None,
    sandbox_mode: Optional[str] = None,
    timeout_s: Optional[int] = None,
    output_last_message_path: Optional[str] = None,
    output_schema_path: Optional[str] = None,
    json_events: bool = False,
) -> List[str]:
    """Apply outgoing redaction (ADR-114) BEFORE building the argv.

    Defensive wrapper for callers that want adapter-level egress redaction
    symmetry (ADR-114 §AC9). Redaction (a trust-boundary concern) stays in
    THIS kernel file; only the argv construction delegates to the non-kernel
    CLI-shape helper via ``make_invoke_command`` (so the kernel holds no CLI
    literal). The redactor invocation appears BEFORE ``make_invoke_command``
    in source order so the AST-based test ``TestCodexEgressCallsiteCoverage``
    recognizes this function as a covered egress callsite.

    Fail-open contract: if the redactor module fails to import we fall back
    to the unredacted prompt rather than blocking. (The live rail's
    fail-CLOSED egress path lives in ``check_pair_rail.py``, not here; this
    orphan wrapper preserves its historical fail-OPEN behavior.)
    """
    try:
        from .. import codex_egress_redact as _redact
        prompt = _redact.redact_outgoing(prompt)
    except Exception:  # pragma: no cover (defensive — redactor is fail-open)
        pass
    return make_invoke_command(
        prompt,
        model=model,
        sandbox_mode=sandbox_mode,
        timeout_s=timeout_s,
        output_last_message_path=output_last_message_path,
        output_schema_path=output_schema_path,
        json_events=json_events,
    )
