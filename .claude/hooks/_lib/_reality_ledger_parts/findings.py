"""Reality ledger: findings."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Tuple

from .constants import *  # shared declaration defaults

def _to_repo_rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(_REPO_ROOT.resolve())).replace(os.sep, "/")
    except (ValueError, OSError):
        return str(p)


def _sha256_of(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()


def _now_iso8601() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _redact(text: str) -> str:
    """Pass through `_lib.redact.redact_secrets` without truncation.

    Use max_chars=0 to disable preview truncation; rely on caller to
    bound the string length when needed.
    """
    return redact_secrets(text or "", max_chars=0)


def _build_finding(
    *,
    detector: str,
    severity: str,
    confidence: float,
    claim_source_path: str,
    expected_evidence: str,
    actual_evidence: str,
    advisory_action: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construct a finding dict with both render forms baked in.

    `claim_source_path` is included for markdown only; JSON/JSONL
    renderers strip the field per Sec MF-3 contract.
    """
    actual_redacted = _redact(actual_evidence)
    sha = _sha256_of(claim_source_path or "")
    # confidence_bps: integer basis-points (confidence × 1000, clamped 0..1000).
    # canonical_json forbids floats in HMAC-covered fields; the old "confidence"
    # float (0.0-1.0) caused CanonicalJsonError on every reality_ledger_finding
    # emit. Readers recover float via confidence_bps / 1000.
    confidence_bps = max(0, min(1000, int(round(float(confidence) * 1000))))
    return {
        "schema_version": SCHEMA_VERSION,
        "finding_id": str(uuid.uuid4()),
        "detector": detector,
        "severity": severity,
        "confidence_bps": confidence_bps,
        "claim_source_path": claim_source_path,
        "claim_source_sha256": sha,
        "expected_evidence": expected_evidence,
        "actual_evidence_redacted": actual_redacted,
        "first_observed_at": _now_iso8601(),
        "advisory_action": advisory_action,
        "_extra": extra or {},
    }


def _strip_markdown_only(finding: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of finding without markdown-only fields (claim_source_path)."""
    return {k: v for k, v in finding.items() if k not in _MARKDOWN_ONLY_FIELDS}


def render_finding_markdown(finding: Dict[str, Any]) -> str:
    lines: List[str] = []
    # confidence_bps (int 0..1000) — display as float for human readability.
    conf_display = finding.get("confidence_bps", 0) / 1000
    lines.append(f"### {finding['detector']}  ·  severity={finding['severity']}  ·  conf={conf_display:.3f}")
    lines.append("")
    lines.append(f"- claim_source_path: `{finding['claim_source_path']}`")
    lines.append(f"- claim_source_sha256: `{finding['claim_source_sha256']}`")
    lines.append(f"- expected_evidence: `{finding['expected_evidence']}`")
    lines.append(f"- actual_evidence_redacted: `{finding['actual_evidence_redacted']}`")
    lines.append(f"- first_observed_at: `{finding['first_observed_at']}`")
    lines.append(f"- advisory_action: {finding['advisory_action']}")
    lines.append(f"- finding_id: `{finding['finding_id']}`")
    return "\n".join(lines)


def render_findings_markdown(findings: List[Dict[str, Any]]) -> str:
    if not findings:
        return "# reality-ledger — 0 findings\n\nNo divergence detected. (Advisory; never blocks.)"
    counts: Dict[str, int] = {}
    for f in findings:
        counts[f["detector"]] = counts.get(f["detector"], 0) + 1
    lines = [f"# reality-ledger — {len(findings)} finding(s)", ""]
    lines.append("## Summary by detector")
    for det in sorted(counts):
        lines.append(f"- `{det}`: {counts[det]}")
    lines.append("")
    lines.append("## Findings")
    for f in findings:
        lines.append("")
        lines.append(render_finding_markdown(f))
    return "\n".join(lines) + "\n"


def render_findings_json(findings: List[Dict[str, Any]]) -> str:
    """JSON array with markdown-only fields excluded."""
    safe = [_strip_markdown_only(f) for f in findings]
    # also drop _extra (caller-private debug payload) from JSON emission
    for s in safe:
        s.pop("_extra", None)
    return json.dumps(safe, indent=2, sort_keys=True, ensure_ascii=False)


def render_findings_jsonl(findings: List[Dict[str, Any]]) -> str:
    """One JSON object per line, markdown-only fields excluded."""
    out: List[str] = []
    for f in findings:
        s = _strip_markdown_only(f)
        s.pop("_extra", None)
        out.append(json.dumps(s, sort_keys=True, ensure_ascii=False))
    return "\n".join(out) + ("\n" if out else "")


# ---------------------------------------------------------------------------
# Audit emission (hasattr-guarded; advisory-only)
# ---------------------------------------------------------------------------

def _scrub_reality_ledger_event(
    event: Dict[str, Any],
    *,
    allowlist: Optional[FrozenSet[str]] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """Return (kept_event, dropped_keys). Defense-in-depth on allowlist drift."""
    aw = allowlist or _REALITY_LEDGER_FINDING_ALLOWLIST
    kept: Dict[str, Any] = {}
    dropped: List[str] = []
    for k, v in event.items():
        if k in aw:
            kept[k] = v
        else:
            dropped.append(k)
    return kept, dropped


def _try_emit_finding(finding: Dict[str, Any], *, finding_count_in_run: int) -> bool:
    """Best-effort audit emit; never raises. Returns True on success.

    The action `reality_ledger_finding` is registered in Phase 5 KERNEL
    ceremony. Pre-Phase-5 this call no-ops (action not in _KNOWN_ACTIONS).
    """
    try:
        from _lib import audit_emit
    except Exception:
        return False
    payload = {
        "action": "reality_ledger_finding",
        "ts": finding.get("first_observed_at"),
        "detector": finding.get("detector"),
        "severity": finding.get("severity"),
        # confidence_bps is already an int (set in _make_finding); pass through.
        "confidence_bps": finding.get("confidence_bps", 0),
        "claim_source_sha256": finding.get("claim_source_sha256"),
        "finding_count_in_run": finding_count_in_run,
    }
    scrubbed, dropped = _scrub_reality_ledger_event(payload)
    # Prefer typed emitter when registered; fall back to emit_generic.
    try:
        if hasattr(audit_emit, "emit_reality_ledger_finding"):
            getattr(audit_emit, "emit_reality_ledger_finding")(**scrubbed)
            return True
        if hasattr(audit_emit, "emit_generic"):
            audit_emit.emit_generic(**scrubbed)
            # emit_generic silently no-ops on unknown action; treat as best-effort
            return True
    except Exception:
        return False
    return False


# ---------------------------------------------------------------------------
# Detector dispatch
# ---------------------------------------------------------------------------


__all__ = ['_to_repo_rel', '_sha256_of', '_now_iso8601', '_redact', '_build_finding', '_strip_markdown_only', 'render_finding_markdown', 'render_findings_markdown', 'render_findings_json', 'render_findings_jsonl', '_scrub_reality_ledger_event', '_try_emit_finding']
