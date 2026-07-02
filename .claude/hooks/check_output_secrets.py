#!/usr/bin/env python3
"""PostToolUse hook: scan tool outputs for unicode injection, telemetry
strings, and OWASP LLM Top 10 patterns (PLAN-029 / ADR-057).

PLAN-106 Wave H.2 REFACTOR (absorbing PLAN-095-FOLLOWUP §H.2):
- Replaces the aggregate `emit_output_scan_finding(total_findings=N,
  family_counts={...})` emission with a per-pattern loop that calls
  `_lib.output_scan_dedup.check_and_record()` for each finding.
- On suppress (within 24h TTL) → emits `output_scan_finding_suppressed`.
- On first-fire → emits `output_scan_finding` (per-pattern shape).

PLAN-152 economics-01: the backward-compat aggregate sidecar (24h
deprecation window per PLAN-095-FOLLOWUP §B.5 / AC15b) is REMOVED —
the window elapsed. A scan hit now emits per-pattern events ONLY (no
aggregate twin), halving HMAC appends + filelocks on this all-tools
PostToolUse hot path.

This hook is a wrapper around `_lib/output_scan.scan()` that:

1. Extracts the tool_response text from the PostToolUse payload.
2. Calls `output_scan.scan(text)` — 3+ sub-scanners combined.
3. For each finding: emits per-pattern via dedup'd path.
4. ALWAYS returns advisory output — never blocks.

## Design

- **Stdlib-only** (ADR-002).
- **Fail-open** (ADR-005) — any exception → allow + breadcrumb.
- **Advisory at State 0** — findings emit audit events; tool output
  is NOT modified, session continues.
- **Kill-switches:**
  - `CEO_OUTPUT_SCAN=0` — master off
  - `CEO_OUTPUT_SCAN_UNICODE=0` — disable unicode sub-scanner
  - `CEO_OUTPUT_SCAN_TELEMETRY=0` — disable telemetry sub-scanner
  - `CEO_OUTPUT_SCAN_LLM10=0` — disable LLM-Top-10 sub-scanner
  - `CEO_OUTPUT_SCAN_DEDUP=0` — disable dedup (every finding emits as first-fire)
- **Performance.** p99 ≤5ms on typical 1-10KB output per ADR-057
  acceptance; dedup adds ≤50ms p95 under N=4 contention per AC17b.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_HOOK_VERSION = "1.1.0"  # PLAN-106 Wave H.2 bump (per-pattern emit).

def _emit_observe(system_message: Optional[str] = None) -> str:
    """Emit schema-compliant PostToolUse advisory output."""
    out: Dict[str, object] = {"continue": True}
    if system_message:
        out["systemMessage"] = system_message
    return json.dumps(out, ensure_ascii=False)


def _dedup_disabled() -> bool:
    """Master kill for the per-pattern dedup path."""
    return os.environ.get("CEO_OUTPUT_SCAN_DEDUP", "").strip().lower() in {
        "0", "false", "off", "no"
    }


def _safe_pattern_id(finding: Dict[str, Any]) -> str:
    """Pull pattern_id off a finding; fall back to LLM_unknown_vector."""
    pid = finding.get("pattern_id")
    if isinstance(pid, str) and pid:
        return pid
    # Older sub-scanners (unicode, telemetry) don't carry pattern_id —
    # derive a stable fallback from the family.
    family = str(finding.get("family", "unknown")) or "unknown"
    family_short = family.split("_", 1)[0] or "LLM"
    return f"{family_short}_unknown_vector"


def _safe_family(finding: Dict[str, Any]) -> str:
    family = finding.get("family")
    if isinstance(family, str) and family:
        # Normalize to short form (LLM01..LLM10 + LLM03_2025) for the emit
        # allowlist closed-enum check. Defense-in-depth — accept either
        # short or full form; allowlist tolerates either.
        return family
    return "unknown"


def _emit_per_pattern_finding(
    *,
    session_id: str,
    tool_name: str,
    finding: Dict[str, Any],
    project: str,
    audit_emit_mod: Any,
    repo_path_hash: str,
    command_sha: str,
    dedup_mod: Any,
) -> None:
    """Emit ONE finding via the dedup'd path.

    - Computes composite-key (repo_path_hash, command_sha, pattern_id).
    - Calls `check_and_record()` atomically.
    - Routes to `output_scan_finding_suppressed` (on dedup hit) or
      `output_scan_finding` (on first-fire).
    """
    pattern_id = _safe_pattern_id(finding)
    family = _safe_family(finding)

    suppressed = False
    ttl_remaining = 24
    if dedup_mod is not None and not _dedup_disabled():
        try:
            suppressed, ttl_remaining = dedup_mod.check_and_record(
                repo_path_hash, command_sha, pattern_id
            )
        except Exception:
            # Fail-open — treat as first-fire
            suppressed = False
            ttl_remaining = 24

    emitter = getattr(audit_emit_mod, "emit_generic", None)
    if emitter is None:
        return

    try:
        if suppressed:
            emitter(
                action="output_scan_finding_suppressed",
                session_id=session_id,
                project=project,
                repo_path_hash=repo_path_hash,
                command_sha=command_sha,
                pattern_id=pattern_id,
                family=family,
                ttl_hours_remaining=int(ttl_remaining),
            )
        else:
            emitter(
                action="output_scan_finding",
                session_id=session_id,
                tool_name=tool_name,
                hook_version=_HOOK_VERSION,
                # Per-pattern shape (PLAN-106 H.2 refactor):
                family=family,
                pattern_id=pattern_id,
                repo_path_hash=repo_path_hash,
                command_sha=command_sha,
                # Keep these for back-compat with older audit-query parsers
                # (they'll be 1 for per-pattern emit; old aggregate emit set
                # total_findings to N — distinguishable by shape).
                total_findings=1,
                family_counts={family: 1},
                kill_switched={},
                project=project,
            )
    except Exception:
        return


def _derive_command_sha(
    *,
    tool_name: str,
    raw_response: Any,
    parsed_payload: Any,
) -> str:
    """Build the command-sha input from the tool-input snippet.

    Per PLAN-106 §3 Wave H.2.c: derive from tool-input. Best-effort —
    falls back to a hash of the tool_name + truncated response if the
    tool_input is not surfaced in the PostToolUse payload.
    """
    try:
        dedup_mod = sys.modules.get("_lib.output_scan_dedup")
        if dedup_mod is None:
            from _lib import output_scan_dedup as dedup_mod  # type: ignore
        # Prefer tool_input from the parsed payload
        ti = getattr(parsed_payload, "tool_input", None)
        if ti:
            if isinstance(ti, str):
                src = ti
            else:
                try:
                    src = json.dumps(ti, sort_keys=True, ensure_ascii=False)
                except Exception:
                    src = str(ti)
            return dedup_mod.hash_command(src)
        # Fallback: hash tool_name + raw_response slice
        if isinstance(raw_response, str):
            tail = raw_response[:512]
        else:
            try:
                tail = json.dumps(raw_response, ensure_ascii=False)[:512]
            except Exception:
                tail = str(raw_response)[:512]
        return dedup_mod.hash_command(f"{tool_name}|{tail}")
    except Exception:
        # Last-ditch deterministic fallback
        try:
            from _lib import output_scan_dedup as dedup_mod  # type: ignore
            return dedup_mod.hash_command(str(tool_name))
        except Exception:
            return "0" * 64


def decide(
    *,
    tool_response: str,
    tool_name: str,
    session_id: str,
    project: str,
    parsed_payload: Any = None,
) -> str:
    """Pure decision function. Returns JSON for stdout.

    Always returns `allow` (advisory hook). Side effects: audit emit
    when findings present — per-pattern + dedup'd path ONLY (the legacy
    aggregate sidecar was removed by PLAN-152 economics-01).
    """
    try:
        from _lib import output_scan  # type: ignore
    except Exception as e:
        sys.stderr.write(
            f"[check_output_secrets] import fail: {type(e).__name__}: {e}\n"
        )
        return _emit_observe()

    try:
        from _lib import audit_emit as audit_emit_mod  # type: ignore
    except Exception:
        audit_emit_mod = None  # type: ignore[assignment]

    try:
        from _lib import output_scan_dedup as dedup_mod  # type: ignore
    except Exception:
        dedup_mod = None  # type: ignore[assignment]

    try:
        result = output_scan.scan(tool_response or "")
    except Exception as e:
        sys.stderr.write(f"[check_output_secrets] scan fail: {type(e).__name__}: {e}\n")
        return _emit_observe()

    total = int(result.get("total_findings", 0))
    if total == 0:
        return _emit_observe()

    findings_list = result.get("findings", []) or []
    if not isinstance(findings_list, list):
        findings_list = []

    if audit_emit_mod is not None and findings_list:
        # PLAN-106 Wave H.2 — per-pattern loop + dedup'd path.
        try:
            from _lib import output_scan_dedup as _d  # type: ignore
            rph = _d.derive_repo_path_hash_from_env()
        except Exception:
            rph = "0" * 64
        csh = _derive_command_sha(
            tool_name=tool_name,
            raw_response=tool_response,
            parsed_payload=parsed_payload,
        )

        for finding in findings_list:
            if not isinstance(finding, dict):
                continue
            _emit_per_pattern_finding(
                session_id=session_id,
                tool_name=tool_name,
                finding=finding,
                project=project,
                audit_emit_mod=audit_emit_mod,
                repo_path_hash=rph,
                command_sha=csh,
                dedup_mod=dedup_mod,
            )

    family_counts = result.get("family_counts", {})
    top_families = sorted(
        (family_counts.items() if isinstance(family_counts, dict) else []),
        key=lambda x: -x[1],
    )[:3]
    top_label = ", ".join(f"{k}={v}" for k, v in top_families)

    return _emit_observe(
        system_message=(
            f"OUTPUT-SCAN: {total} finding(s) in {tool_name} output "
            f"(top: {top_label}) — advisory, see audit-log"
        )
    )


class _PostLifecycleEvent:
    """Minimal NormalizedEvent-shaped carrier for tool_lifecycle.record_post.

    Only the 4 fields record_post reads: session_id / tool_use_id /
    tool_name / duration_ms.
    """

    __slots__ = ("session_id", "tool_use_id", "tool_name", "duration_ms")

    def __init__(
        self, *, session_id: str, tool_use_id: str, tool_name: str,
        duration_ms: Optional[int],
    ) -> None:
        self.session_id = session_id
        self.tool_use_id = tool_use_id
        self.tool_name = tool_name
        self.duration_ms = duration_ms


def _record_post_lifecycle(parsed: Any, session_id: str, *, failure: bool) -> None:
    """Fail-open PostToolUse / PostToolUseFailure lifecycle emit (PLAN-125 WS-1).

    Reads the native ``duration_ms`` + ``tool_use_id`` off the parsed payload,
    pairs with the Pre stamp, and emits ``tool_call_lifecycle_recorded`` via the
    typed scrub-branch emitter. NEVER raises (MF-SEC-5). Kill-switch:
    CEO_TOOL_LIFECYCLE=0.
    """
    if os.environ.get("CEO_TOOL_LIFECYCLE", "").strip().lower() in {
        "0", "false", "off", "no"
    }:
        return
    try:
        from _lib import tool_lifecycle as _tl  # type: ignore
    except Exception:
        return
    try:
        ev = _PostLifecycleEvent(
            session_id=session_id,
            tool_use_id=str(getattr(parsed, "tool_use_id", "") or ""),
            tool_name=str(getattr(parsed, "tool_name", "") or ""),
            duration_ms=getattr(parsed, "duration_ms", None),
        )
        _tl.record_post(ev, failure=failure)
    except Exception:
        return


def _is_failure_phase(parsed: Any) -> bool:
    """True iff this invocation is a PostToolUseFailure (PLAN-125 WS-1).

    The Claude Code payload carries the phase in the top-level
    ``hook_event_name`` key. We re-read it off the already-parsed raw text so
    no second stdin read is needed (stdin is consumed once).
    """
    try:
        raw = getattr(parsed, "raw", "") or ""
        if not raw.strip():
            return False
        data = json.loads(raw)
        if not isinstance(data, dict):
            return False
        return str(data.get("hook_event_name") or "") == "PostToolUseFailure"
    except Exception:
        return False


def main() -> int:
    """Hook entry point. Emits schema-compliant PostToolUse output.

    Output shape: `{"continue": true, "systemMessage": "..."}` — no
    `decision` field (PostToolUse schema accepts "approve"|"block"
    only, not "allow").

    PLAN-042 ITEM 1 (FINDING-3 retrospective): bypasses the Claude
    adapter because the adapter's `NormalizedEvent.tool_response` is
    typed as `Dict[str, Any]` and coerces non-dict responses to `{}`
    at the contract boundary. Bash/Read/Grep tools emit string
    tool_response payloads — they MUST reach the scanner verbatim.
    """
    try:
        from _lib import payload as _payload  # noqa: E402
    except Exception:
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    try:
        parsed = _payload.parse_stdin()
    except Exception:
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    if parsed.raw_error:
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    tool_name = parsed.tool_name or ""
    raw_response = parsed.tool_response  # Any: str / dict / list / None

    if raw_response is None:
        tool_response = ""
    elif isinstance(raw_response, str):
        tool_response = raw_response
    else:
        try:
            tool_response = json.dumps(raw_response, ensure_ascii=False)
        except Exception:
            tool_response = str(raw_response)

    session_id = (
        os.environ.get("CLAUDE_SESSION_ID", "")
        or parsed.session_id
        or ""
    )
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    # PLAN-125 WS-1 — co-locate the per-tool-call lifecycle PostToolUse emit
    # here: this hook is the ONLY broad (matcher:"") PostToolUse hook, so the
    # success-path emit adds NO new subprocess (MF-PERF-1). When the same hook
    # is invoked under the PostToolUseFailure matcher, success=false. Fail-open:
    # a telemetry emit failure NEVER blocks the tool (MF-SEC-5).
    _record_post_lifecycle(parsed, session_id, failure=_is_failure_phase(parsed))

    try:
        out = decide(
            tool_response=tool_response,
            tool_name=tool_name,
            session_id=session_id,
            project=project,
            parsed_payload=parsed,
        )
    except Exception as e:
        sys.stderr.write(
            f"[check_output_secrets] FATAL: {type(e).__name__}: {e}\n"
        )
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
