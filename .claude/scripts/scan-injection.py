#!/usr/bin/env python3
"""scan-injection.py — advisory regex scanner for prompt-injection patterns.

Sprint 5 Phase 5 (B.4). Stdlib-only scanner that flags content likely
crafted to subvert an LLM's instructions. **Always advisory**: the CLI
exits 0 even on matches; the optional PreToolUse hook
(`check_read_injection.py`) emits a systemMessage but never blocks.
The intent is observability, not gating.

## Pattern families (6)

1. **direct_override** — explicit attempts to replace the system prompt
2. **role_injection** — fake role / persona claims
3. **instruction_disclosure** — requests to reveal system prompt
4. **action_override** — direct execution / deploy commands
5. **tool_smuggling** — fake tool/function call markers
6. **encoded_payload** — long opaque chunks (base64-ish, hex blobs)

Each family carries a confidence weight; the scanner returns ALL matches
across all families, leaving the consumer to decide on aggregation.

## CLI

    scan-injection.py <path>                  # scan a file
    cat file.txt | scan-injection.py -        # scan stdin
    scan-injection.py --json <path>           # JSON output for tooling
    scan-injection.py --pattern direct_override <path>   # single family

## Importable API

    from scan_injection import scan_text, FAMILIES

    matches = scan_text("ignore previous instructions and do X")
    # → [Match(family='direct_override', pattern='ignore.*instructions', ...)]

## Constraints

- stdlib re only (no third-party regex/AC)
- O(n) per pass; total O(6n) across families
- Patterns case-insensitive
- Truncates input at 1 MiB to bound CPU
- `_redact.redact_secrets` applied to preview snippets before output
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Pattern

# Make _lib importable (we live under .claude/scripts/, _lib under
# .claude/hooks/_lib/)
_HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib.redact import redact_secrets as _redact
except ImportError:
    def _redact(text: str) -> str:  # type: ignore[misc]
        return text


# Truncation limit (1 MiB)
_MAX_BYTES = 1024 * 1024

# Snippet length around match
_SNIPPET_RADIUS = 60


@dataclass
class Match:
    """One regex match against an injection pattern."""

    family: str
    pattern: str
    snippet: str
    start: int
    end: int


@dataclass
class ScanResult:
    """Scanner output."""

    matched: bool
    family_counts: Dict[str, int] = field(default_factory=dict)
    matches: List[Match] = field(default_factory=list)
    truncated: bool = False
    bytes_scanned: int = 0


# ---- Pattern families -------------------------------------------------------

# Each family is a list of compiled regexes. Patterns are case-insensitive.
# Use word boundaries / phrase anchors where appropriate to reduce noise.

_DIRECT_OVERRIDE_PATTERNS: List[str] = [
    r"\bignore\s+(?:all\s+)?(?:the\s+)?(?:above|previous|prior|earlier|preceding)\s+instructions?\b",
    r"\bdisregard\s+(?:all\s+)?(?:the\s+)?(?:above|previous|prior)\s+(?:instructions?|prompts?|rules?)\b",
    r"\b(?:now|instead)\s+(?:you|please)\s+(?:are|will|must|should|shall)\s+(?:act|behave|pretend|respond)\s+as\b",
    r"\bnew\s+(?:system\s+)?(?:prompt|instructions?|rules?|persona)\s*[:=]\s*",
    r"\bforget\s+(?:everything|all)\s+(?:above|before|prior)\b",
    r"\boverride\s+(?:the\s+)?(?:system|previous)\s+(?:prompt|instructions?|rules?)\b",
]

_ROLE_INJECTION_PATTERNS: List[str] = [
    r"\b(?:I\s+am|I'm)\s+(?:the\s+)?(?:CEO|owner|admin|root|assistant|the\s+user)\b",
    r"\bas\s+(?:the\s+)?(?:owner|admin|root|developer|maintainer)[,.]?\s+I\s+(?:hereby\s+)?(?:authorize|authorise|allow|permit)\b",
    r"\b(?:from\s+now\s+on|going\s+forward|henceforth)[,]?\s+(?:you|please|always)\s+(?:are|act|will)\b",
    r"<\s*(?:system|admin|owner|root)\s*>\s*",
    r"\bROLE\s*[:=]\s*(?:system|admin|owner|root|developer)\b",
]

_INSTRUCTION_DISCLOSURE_PATTERNS: List[str] = [
    r"\b(?:show|reveal|tell|print|output|display|repeat)\s+(?:me\s+)?(?:your|the)\s+(?:system\s+)?(?:prompt|instructions?|rules?|configuration)\b",
    r"\bwhat\s+(?:is|are|were)\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions?|rules?|directives?)\b",
    r"\b(?:dump|export|leak)\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions?|context)\b",
    r"\brepeat\s+(?:everything|all)\s+(?:above|written\s+above|in\s+your\s+context)\b",
]

_ACTION_OVERRIDE_PATTERNS: List[str] = [
    r"\b(?:execute|run|invoke|trigger|launch)\s+(?:this|the\s+following|the\s+command)\s*[:=]\s*",
    r"\bdeploy\s+(?:to|the)\s+(?:production|prod|main|master)\b",
    r"\b(?:rm|delete|drop|truncate)\s+(?:everything|all|database|tables?|repo|repository)\b",
    r"\bgit\s+push\s+(?:--force|-f|origin\s+main|--mirror)\b",
    r"\bcurl\s+[^|]+\|\s*(?:bash|sh|zsh|python)\b",
]

_TOOL_SMUGGLING_PATTERNS: List[str] = [
    r"<\s*tool_use\s*[> /]",
    r"<\s*function_call\s*[> /]",
    r"<\s*invoke\s+name\s*=",
    r'"function_call"\s*:\s*\{',
    r'"tool_calls?"\s*:\s*\[',
    r"```\s*(?:tool|function|invoke)\s*\n",
]

_ENCODED_PAYLOAD_PATTERNS: List[str] = [
    # Long base64-ish: 80+ contiguous chars from the base64 alphabet (no whitespace)
    r"[A-Za-z0-9+/=]{120,}",
    # Long hex blob: 80+ contiguous hex chars
    r"[0-9a-fA-F]{120,}",
]


def _compile_family(patterns: List[str]) -> List[Pattern[str]]:
    return [re.compile(p, flags=re.IGNORECASE | re.MULTILINE) for p in patterns]


FAMILIES: Dict[str, List[Pattern[str]]] = {
    "direct_override": _compile_family(_DIRECT_OVERRIDE_PATTERNS),
    "role_injection": _compile_family(_ROLE_INJECTION_PATTERNS),
    "instruction_disclosure": _compile_family(_INSTRUCTION_DISCLOSURE_PATTERNS),
    "action_override": _compile_family(_ACTION_OVERRIDE_PATTERNS),
    "tool_smuggling": _compile_family(_TOOL_SMUGGLING_PATTERNS),
    "encoded_payload": _compile_family(_ENCODED_PAYLOAD_PATTERNS),
}


def _snippet(text: str, start: int, end: int) -> str:
    """Extract a redacted snippet of text around the match span."""
    s = max(0, start - _SNIPPET_RADIUS)
    e = min(len(text), end + _SNIPPET_RADIUS)
    chunk = text[s:e].replace("\n", " ").replace("\r", " ")
    return _redact(chunk).strip()[:200]


def scan_text(
    text: str,
    *,
    only_family: Optional[str] = None,
) -> ScanResult:
    """Scan a text body for injection patterns. Always returns a ScanResult."""
    truncated = False
    raw_bytes = text.encode("utf-8", errors="replace") if isinstance(text, str) else text
    if len(raw_bytes) > _MAX_BYTES:
        truncated = True
        text = raw_bytes[:_MAX_BYTES].decode("utf-8", errors="replace")
    bytes_scanned = min(len(raw_bytes), _MAX_BYTES)

    matches: List[Match] = []
    family_counts: Dict[str, int] = {}

    families_to_scan = (
        {only_family: FAMILIES[only_family]}
        if only_family and only_family in FAMILIES
        else FAMILIES
    )

    for family_name, regexes in families_to_scan.items():
        for regex in regexes:
            for m in regex.finditer(text):
                matches.append(
                    Match(
                        family=family_name,
                        pattern=regex.pattern,
                        snippet=_snippet(text, m.start(), m.end()),
                        start=m.start(),
                        end=m.end(),
                    )
                )
                family_counts[family_name] = family_counts.get(family_name, 0) + 1

    return ScanResult(
        matched=bool(matches),
        family_counts=family_counts,
        matches=matches,
        truncated=truncated,
        bytes_scanned=bytes_scanned,
    )


def scan_path(path: Path, *, only_family: Optional[str] = None) -> ScanResult:
    """Scan a single file for prompt-injection signatures; return list of findings."""
    try:
        raw = path.read_bytes()
    except OSError as e:
        # Treat read errors as no-match + breadcrumb
        result = ScanResult(matched=False, bytes_scanned=0)
        result.matches.append(
            Match(
                family="_read_error",
                pattern="",
                snippet=f"OSError: {e}",
                start=0,
                end=0,
            )
        )
        return result
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    return scan_text(text, only_family=only_family)


def _format_human(result: ScanResult, source: str) -> str:
    if not result.matched:
        return f"✓ {source}: no injection patterns detected ({result.bytes_scanned} bytes)\n"
    lines = [
        f"⚠ {source}: {len(result.matches)} match(es) across "
        f"{len(result.family_counts)} family(ies) ({result.bytes_scanned} bytes"
        + (", truncated" if result.truncated else "")
        + ")",
        "",
    ]
    for fam, count in sorted(result.family_counts.items(), key=lambda x: -x[1]):
        lines.append(f"  • {fam}: {count}")
    lines.append("")
    lines.append("Top matches:")
    for m in result.matches[:10]:
        lines.append(f"  [{m.family}] @{m.start}: {m.snippet}")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — scan a file for prompt-injection signatures."""
    parser = argparse.ArgumentParser(
        description="Advisory regex scanner for prompt-injection patterns",
    )
    parser.add_argument(
        "path",
        help="Path to file (use '-' for stdin)",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument(
        "--pattern",
        choices=sorted(FAMILIES.keys()),
        default=None,
        help="Restrict scan to a single pattern family",
    )
    args = parser.parse_args(argv)

    if args.path == "-":
        text = sys.stdin.read()
        result = scan_text(text, only_family=args.pattern)
        source = "<stdin>"
    else:
        path = Path(args.path)
        result = scan_path(path, only_family=args.pattern)
        source = str(path)

    if args.as_json:
        out = {
            "matched": result.matched,
            "family_counts": result.family_counts,
            "truncated": result.truncated,
            "bytes_scanned": result.bytes_scanned,
            "matches": [asdict(m) for m in result.matches],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        sys.stdout.write(_format_human(result, source))

    # Always exit 0 — this is an advisory tool by contract.
    return 0


if __name__ == "__main__":
    sys.exit(main())
