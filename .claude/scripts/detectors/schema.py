"""PLAN-047 Phase 1 — detector output schema.

`Finding` dataclass + JSONL emitter + shared event iterator.
Stdlib-only (ADR-002). All detectors consume a `Path` to an
audit-log JSONL and return `List[Finding]`.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class Finding:
    """One ghost-token-waste finding emitted by a detector."""

    detector: str
    severity: str = "warning"
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""
    audit_spans: List[str] = field(default_factory=list)
    estimated_wasted_tokens: int = 0

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


def emit_findings(
    findings: List[Finding],
    output_path: Optional[str] = None,
) -> None:
    """Emit findings as JSONL.

    If ``output_path`` is provided, append to that file. Otherwise
    print each finding to stdout. Caller owns path lifecycle;
    this function does not rotate or truncate.
    """
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            for finding in findings:
                handle.write(finding.to_json_line() + "\n")
    else:
        for finding in findings:
            print(finding.to_json_line())


def iter_events(log_path: Path) -> Iterable[Dict[str, Any]]:
    """Yield one event dict per JSONL line, skipping blanks + bad JSON.

    Returns an empty generator if ``log_path`` does not exist — detectors
    fail-open on missing log (caller can still report zero findings
    without crashing).
    """
    if not log_path.exists():
        return
    with open(log_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def parse_ts(event: Dict[str, Any]) -> Optional[datetime]:
    """Parse the ``ts`` field to timezone-aware UTC datetime.

    Returns ``None`` if the field is missing or malformed.
    Accepts both trailing ``Z`` (as emitted by audit_log.py) and
    explicit ``+00:00`` offsets.
    """
    raw = event.get("ts")
    if not isinstance(raw, str) or not raw:
        return None
    normalized = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def is_agent_spawn(event: Dict[str, Any]) -> bool:
    """True if ``event`` represents an ``Agent`` tool spawn."""
    return event.get("action") == "agent_spawn"
