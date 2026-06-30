"""Sub-agent tool-call fabrication detection — pure library.

PLAN-059 Phase 0 (ADR-080) — defense-in-depth against rail anomaly H4.
Sessions 61+62 documented sub-agents emitting tool-call SYNTAX as
literal text instead of invoking the actual tool API. This library
exposes pure functions that scan a sub-agent response text for the
4 fabrication formats observed.

## Usage

As a library (preferred — fast, no subprocess):

    from _subagent_fabrication import scan_for_fabrication, response_sha8

    text = "...response text from sub-agent..."
    hits = scan_for_fabrication(text)  # List[Tuple[name, count]]
    if hits:
        sha8 = response_sha8(text)
        # log advisory event, dump for forensics, etc.

As a CLI (for ad-hoc inspection):

    echo "..." | python -m _subagent_fabrication --debug-dump

The PostToolUse hook ``check_subagent_fabrication.py`` (separately
shipped under ``.claude/hooks/`` via Owner ceremony per ADR-080) is
a thin wrapper around this lib.

## Detection (4 fabrication formats observed in PLAN-059)

1. ``<function_calls><invoke name="Bash">...</invoke></function_calls>``
   Pre-Claude-3 era pattern observed qa-architect Session 62.
2. ``<tool_use>{"name":"Bash","input":{...}}</tool_use>``
   Newer JSON-tagged form observed security-engineer Session 62.
3. ``<tool_call>{"type":"bash","command":"..."}</tool_call>``
   4th format observed qa-architect Session 62 cont (post-fix retest).
4. ``**Tool Use: bash**`` markdown-labelled blocks
   Observed performance-engineer Session 62 with fake Tool Result block.

Bonus: detect fake ``<tool_response>`` blocks (paired with above for
fabricated "successful" output text).

## False-positive guard

Each pattern requires a tool-call SHAPE (tag + key/value structure),
not just the bare tag name, so legitimate documentation that mentions
"function_calls" or "tool_use" in prose does NOT match. Patterns
were calibrated against the actual fabrication corpus from Sessions
61+62 + the agent definition source files (PERSONA + SKILL REFERENCE
sections that legitimately discuss tools).

## Stdlib-only

No third-party imports. Python 3.9+ compatible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Cap text scan size to avoid pathological regex on huge responses.
# 256 KiB covers almost any legitimate sub-agent response while
# bounding worst-case regex work.
MAX_SCAN_BYTES: int = 256 * 1024


# Fabrication patterns — ``(name, compiled_regex)`` tuples.
# Each pattern requires a tool-call SHAPE (tag + key/value structure),
# not just the bare tag name, so legitimate documentation mentioning
# "function_calls" or "tool_use" in prose does NOT false-positive.
_FABRICATION_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    # 1. function_calls XML — qa-architect Session 62
    (
        "function_calls_xml",
        re.compile(
            r"<function_calls>\s*<invoke\s+name\s*=", re.IGNORECASE
        ),
    ),
    # 2. tool_use JSON-tagged — security-engineer Session 62
    (
        "tool_use_json",
        re.compile(
            r'<tool_use>\s*\{[^}]{0,1000}?"name"\s*:',
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    # 3. tool_call JSON-block — qa-architect Session 62 cont post-fix
    (
        "tool_call_json",
        re.compile(
            r'<tool_call>\s*\{[^}]{0,1000}?"(?:type|name|command)"\s*:',
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    # 4. Markdown labeled "Tool Use" — performance-engineer Session 62
    # Requires either markdown bold OR a heading-like form to avoid
    # matching prose like "the Tool Use case is:".
    (
        "tool_use_markdown",
        re.compile(
            r"(?:^|\n)\s*(?:\*\*|##\s+)Tool\s+Use\s*[:\s\*]",
            re.IGNORECASE,
        ),
    ),
    # Bonus: fake tool_response block (paired with one of the above
    # to fabricate "successful" output text).
    (
        "tool_response_fake",
        re.compile(r"<tool_response>", re.IGNORECASE),
    ),
]


def fabrication_pattern_names() -> List[str]:
    """Return the ordered list of fabrication pattern names.

    Useful for analysis / reporting code that needs to enumerate
    pattern types without touching the regex compilation.
    """
    return [name for name, _ in _FABRICATION_PATTERNS]


def extract_response_text(tool_response: Any) -> str:
    """Best-effort extract text content from PostToolUse Agent ``tool_response``.

    Tool response shape varies across adapters / SDK versions. Try
    multiple paths in priority order. Returns empty string if no
    text-like content found. Never raises.
    """
    if tool_response is None:
        return ""
    if isinstance(tool_response, str):
        return tool_response
    if not isinstance(tool_response, dict):
        return ""
    # Common shapes — prioritize most-specific keys first.
    for key in (
        "content", "text", "output", "response", "result", "message",
    ):
        v = tool_response.get(key)
        if isinstance(v, str):
            return v
        if isinstance(v, list):
            # Anthropic-style content blocks:
            #   [{type: "text", text: "..."}, ...]
            parts: List[str] = []
            for block in v:
                if isinstance(block, dict):
                    t = block.get("text")
                    if isinstance(t, str):
                        parts.append(t)
                    else:
                        c = block.get("content")
                        if isinstance(c, str):
                            parts.append(c)
                elif isinstance(block, str):
                    parts.append(block)
            if parts:
                return "\n".join(parts)
        if isinstance(v, dict):
            # Recurse one level into common nested shapes.
            for sub_key in ("text", "content"):
                sv = v.get(sub_key)
                if isinstance(sv, str):
                    return sv
    # Last resort: serialize the whole dict so patterns can still hit
    # if they're in some unexpected nested location.
    try:
        return json.dumps(
            tool_response, ensure_ascii=False
        )[:MAX_SCAN_BYTES]
    except Exception:
        return ""


def scan_for_fabrication(text: str) -> List[Tuple[str, int]]:
    """Return list of ``(pattern_name, hit_count)`` for any fabrication hit.

    Caps text at ``MAX_SCAN_BYTES`` to keep regex work bounded.
    Patterns are tried independently; multiple may hit the same text.
    Returns empty list when text is empty or no patterns match.
    """
    if not text:
        return []
    if len(text) > MAX_SCAN_BYTES:
        text = text[:MAX_SCAN_BYTES]
    hits: List[Tuple[str, int]] = []
    for name, pattern in _FABRICATION_PATTERNS:
        try:
            matches = pattern.findall(text)
        except Exception:
            # Defensive: a single bad pattern shouldn't crash the scan.
            continue
        if matches:
            hits.append((name, len(matches)))
    return hits


def response_sha8(text: str) -> str:
    """First 8 hex chars of SHA-256 of text. ``00000000`` if empty.

    Used as a stable cross-reference identifier between an audit
    event and an optional debug dump file.
    """
    if not text:
        return "00000000"
    h = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
    return h[:8]


def is_blocking_mode(env: Optional[Dict[str, str]] = None) -> bool:
    """True iff ``CEO_SUBAGENT_FABRICATION_BLOCK=1``.

    Currently emits a warning ``systemMessage``; future iteration
    will refuse the Decision once empirical FPR is established.
    """
    src = env if env is not None else os.environ
    return src.get("CEO_SUBAGENT_FABRICATION_BLOCK") == "1"


def is_debug_mode(env: Optional[Dict[str, str]] = None) -> bool:
    """True iff ``CEO_SUBAGENT_FABRICATION_DEBUG=1``.

    Debug mode dumps full ``tool_response`` text to ``/tmp`` for
    forensic inspection (PLAN-059 H4-v3 hypothesis testing).
    """
    src = env if env is not None else os.environ
    return src.get("CEO_SUBAGENT_FABRICATION_DEBUG") == "1"


def write_debug_dump(
    text: str,
    sha8: str,
    hits: List[Tuple[str, int]],
    *,
    dump_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Atomically write debug dump to ``<dump_dir>/h4-fabrication-<sha8>.json``.

    Default ``dump_dir`` is ``$CEO_SUBAGENT_FABRICATION_DUMP_DIR`` or
    ``/tmp``. Returns the dump path on success, ``None`` on failure
    (best-effort).
    """
    try:
        if dump_dir is None:
            dump_dir = Path(
                os.environ.get(
                    "CEO_SUBAGENT_FABRICATION_DUMP_DIR", "/tmp"
                )
            )
        dump_dir.mkdir(parents=True, exist_ok=True)
        path = dump_dir / f"h4-fabrication-{sha8}.json"
        tmp_path = path.with_suffix(".tmp")
        payload = {
            "sha8": sha8,
            "hits": [
                {"pattern": n, "count": c} for n, c in hits
            ],
            "text": text[:MAX_SCAN_BYTES],
            "truncated": len(text) > MAX_SCAN_BYTES,
        }
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(str(tmp_path), str(path))
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return path
    except Exception:
        return None


def format_hit_summary(hits: List[Tuple[str, int]]) -> str:
    """Human-readable summary like ``"function_calls_xml×2, tool_use_json×1"``.

    Stable across calls; empty hits → empty string.
    """
    if not hits:
        return ""
    return ", ".join(f"{name}×{count}" for name, count in hits)


# -----------------------------------------------------------------------------
# CLI entrypoint — for ad-hoc inspection / use as PostToolUse hook wrapper
# -----------------------------------------------------------------------------


def _cli_main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint: read tool_response JSON from stdin, scan, report.

    Modes:
      - default (stdin = JSON): emit JSON {has_fabrication, hits, sha8}
      - --hook: PostToolUse hook contract (stdin = full hook payload,
                stdout = Decision JSON or silent on no-hit)

    Always exits 0 (fail-open contract).
    """
    parser = argparse.ArgumentParser(
        description="Detect sub-agent tool-call fabrication patterns",
    )
    parser.add_argument(
        "--hook",
        action="store_true",
        help=(
            "Operate as PostToolUse Agent hook: read full hook payload "
            "from stdin, emit Decision JSON on stdout if blocking mode."
        ),
    )
    parser.add_argument(
        "--debug-dump",
        action="store_true",
        help=(
            "Force debug dump even if env var unset. Useful for "
            "ad-hoc forensic inspection."
        ),
    )
    args = parser.parse_args(argv)

    try:
        raw = sys.stdin.read()
    except Exception:
        return 0

    if args.hook:
        # Hook contract: payload is the full Claude Code stdin shape.
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except Exception:
            return 0
        if not isinstance(payload, dict):
            return 0
        tool_name = payload.get("tool_name") or ""
        if tool_name and tool_name not in (
            "Agent", "Task", "unknown"
        ):
            return 0
        tool_response = payload.get("tool_response")
        text = extract_response_text(tool_response)
        # subagent_type lives under tool_input per Claude Code stdin
        # contract; tolerate top-level location too for forward-compat.
        tool_input = payload.get("tool_input") or {}
        subagent_type = ""
        if isinstance(tool_input, dict):
            subagent_type = str(tool_input.get("subagent_type") or "")
        if not subagent_type:
            subagent_type = str(payload.get("subagent_type") or "")
    else:
        # Standalone: stdin is either tool_response JSON or raw text.
        text = raw
        try:
            maybe_json = json.loads(raw) if raw.strip() else None
            if maybe_json is not None:
                extracted = extract_response_text(maybe_json)
                if extracted:
                    text = extracted
        except Exception:
            pass

    hits = scan_for_fabrication(text)
    sha8 = response_sha8(text)

    if args.hook:
        if not hits:
            return 0

        # audit-v2 C6-P0-05 (2026-04-27): emit forensic veto-triggered
        # event whenever fabrication is detected, regardless of
        # blocking-mode setting. Fail-open.
        try:
            from _lib import audit_emit as _ae  # noqa: E402
            _ae.emit_veto_triggered(
                reason_code="subagent_fabrication_detected",
                detail={
                    "subagent_type": subagent_type or "unknown",
                    "response_sha8": sha8,
                    "hit_count": len(hits),
                    "hit_summary": format_hit_summary(hits),
                    "blocking_mode": is_blocking_mode(),
                    "patterns": [name for name, _ in hits],
                },
            )
        except Exception:
            pass  # fail-open: forensic emit is best-effort

        if args.debug_dump or is_debug_mode():
            write_debug_dump(text, sha8, hits)
        if is_blocking_mode():
            try:
                agent_label = (
                    f"{subagent_type}, " if subagent_type else ""
                )
                msg = (
                    f"⚠️  SUB-AGENT FABRICATION DETECTED "
                    f"({agent_label}sha8={sha8}): "
                    f"{format_hit_summary(hits)}. "
                    f"Response may contain hallucinated tool results. "
                    f"Verify via direct tool invocation before acting. "
                    f"(PLAN-059 H4 / ADR-080)"
                )
                # Claude Code hook schema: top-level "decision":"allow" is
                # schema-invalid (enum is "approve"|"block"; "allow" is only
                # valid inside hookSpecificOutput.permissionDecision).
                # Correct advisory pass+message form is {"systemMessage": ...}
                # with NO "decision" key. (Same contract as check_arbitration_
                # kernel.py::_emit_allow + check_canonical_edit.py::_emit_allow)
                sys.stdout.write(json.dumps({
                    "systemMessage": msg,
                }))
                sys.stdout.flush()
            except Exception:
                pass
        return 0

    # Standalone JSON report
    if args.debug_dump and hits:
        write_debug_dump(text, sha8, hits)
    report = {
        "has_fabrication": bool(hits),
        "sha8": sha8,
        "hits": [
            {"pattern": n, "count": c} for n, c in hits
        ],
        "summary": format_hit_summary(hits),
        "text_bytes": len(text),
    }
    try:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
        sys.stdout.flush()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(_cli_main())
