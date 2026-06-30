#!/usr/bin/env python3
"""PLAN-047 Phase 3 — /audit-tokens CLI.

Runs the 6 ghost-token detectors shipped in Phase 1 over an
audit-log window, aggregates findings, and emits a markdown report
(default) or a JSONL stream. stdlib-only (ADR-002).

Usage:
    python3 audit-tokens.py [--window DAYS] [--format markdown|json]
                           [--output PATH] [--log PATH]
                           [--top-per-detector N]

Defaults:
    --window 30
    --format markdown
    --output (stdout)
    --log ~/.claude/projects/ceo-orchestration/audit-log.jsonl
    --top-per-detector 20

Exit codes:
    0 — ran to completion (findings or no findings both OK)
    2 — invalid argument (argparse)
    3 — log path not readable
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---- Package import via sys.path (ADR-002 stdlib; no setup.py) -------------
_SCRIPTS_DIR = Path(__file__).resolve().parent
_DETECTORS_PKG_PARENT = _SCRIPTS_DIR
if str(_DETECTORS_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_DETECTORS_PKG_PARENT))

from detectors import (  # noqa: E402  (sys.path extended above)
    looping,
    overpowered,
    retry_churn,
    schema,
    tool_cascade,
    wasteful_thinking,
    weak_model,
)


_DEFAULT_LOG = (
    Path(os.environ.get("HOME") or str(Path.home()))
    / ".claude"
    / "projects"
    / "ceo-orchestration"
    / "audit-log.jsonl"
)

_ALL_DETECTORS = [
    retry_churn,
    tool_cascade,
    looping,
    wasteful_thinking,
    weak_model,
    overpowered,
]

_DEFAULT_TOP_PER_DETECTOR = 20


def run_all(log_path: Path) -> List[schema.Finding]:
    """Run every detector over ``log_path`` and return all findings.

    Each detector is invoked with ``detect(log_path)`` using its own
    defaults. Per-detector exceptions are caught (fail-open contract) so
    one buggy detector cannot suppress the rest of the report.
    """
    findings: List[schema.Finding] = []
    for mod in _ALL_DETECTORS:
        try:
            out = mod.detect(log_path)
        except Exception as exc:  # pragma: no cover — defensive
            sys.stderr.write(
                f"[audit-tokens] WARN: {mod.__name__} detect failed: {exc}\n"
            )
            continue
        if out:
            findings.extend(out)
    return findings


def _finding_ts(finding: schema.Finding) -> Optional[datetime]:
    """Best-effort extract a UTC ts from finding.evidence for window filter.

    Falls back to None when evidence holds no parseable timestamp — callers
    treat None as "unknown" (include) so the window filter never silently
    drops findings missing metadata.
    """
    for key in ("first_seen", "last_seen", "ts", "first_ts", "last_ts"):
        raw = finding.evidence.get(key)
        if not raw:
            continue
        if isinstance(raw, datetime):
            return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
        if isinstance(raw, (int, float)):
            try:
                return datetime.fromtimestamp(float(raw), tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                continue
        if not isinstance(raw, str):
            continue
        normalized = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
        try:
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            continue
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


def filter_window(
    findings: List[schema.Finding], window_days: int, *, now: Optional[datetime] = None
) -> List[schema.Finding]:
    """Return findings whose evidence ts is within ``window_days`` of now.

    Findings with no parseable ts are kept (unknown > drop). A
    non-positive window disables the filter entirely.
    """
    if window_days <= 0:
        return list(findings)
    reference = now if now is not None else datetime.now(timezone.utc)
    cutoff = reference - timedelta(days=window_days)
    kept: List[schema.Finding] = []
    for f in findings:
        ts = _finding_ts(f)
        if ts is None or ts >= cutoff:
            kept.append(f)
    return kept


def group_by_detector(
    findings: List[schema.Finding],
) -> List[Tuple[str, List[schema.Finding]]]:
    """Stable alphabetical grouping by detector name."""
    by_det: Dict[str, List[schema.Finding]] = {}
    for f in findings:
        by_det.setdefault(f.detector, []).append(f)
    return sorted(by_det.items())


def render_markdown(
    findings: List[schema.Finding],
    *,
    window_days: int,
    log_path: Path,
    top_per_detector: int,
    now: Optional[datetime] = None,
) -> str:
    """Format findings as a human-readable markdown report."""
    reference = now if now is not None else datetime.now(timezone.utc)
    out: List[str] = []
    out.append("# /audit-tokens report")
    out.append("")
    out.append(f"- Generated: `{reference.isoformat()}`")
    out.append(f"- Window: last {window_days} day(s)")
    out.append(f"- Source: `{log_path}`")
    out.append(f"- Total findings: **{len(findings)}**")
    wasted_total = sum(f.estimated_wasted_tokens for f in findings)
    out.append(f"- Estimated wasted tokens (sum): **{wasted_total}**")
    out.append("")

    if not findings:
        out.append("_No findings in window. Either dispatch is clean or "
                   "the detectors need more telemetry (post-PLAN-020 "
                   "streaming)._")
        return "\n".join(out) + "\n"

    for detector_name, group in group_by_detector(findings):
        out.append(f"## {detector_name} ({len(group)} findings)")
        out.append("")
        # Severity tally
        sev_counts: Dict[str, int] = {}
        for f in group:
            sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1
        tally = ", ".join(f"{k}={v}" for k, v in sorted(sev_counts.items()))
        out.append(f"_Severity: {tally}_")
        out.append("")
        for f in group[:top_per_detector]:
            evidence_preview = ", ".join(
                f"{k}={v}" for k, v in list(f.evidence.items())[:4]
            )
            out.append(
                f"- **[{f.severity}]** {f.recommendation} "
                f"— `{evidence_preview}`"
            )
        if len(group) > top_per_detector:
            out.append(
                f"- _... {len(group) - top_per_detector} more "
                f"(see JSON output for the full list)_"
            )
        out.append("")

    return "\n".join(out) + "\n"


def render_jsonl(findings: List[schema.Finding]) -> str:
    """One JSON object per finding, newline-separated (no trailing newline)."""
    return "\n".join(f.to_json_line() for f in findings)


def render_json_summary(
    findings: List[schema.Finding],
    *,
    window_days: int,
    log_path: Path,
    now: Optional[datetime] = None,
) -> str:
    """Single JSON object with header + findings array. Useful for programs."""
    reference = now if now is not None else datetime.now(timezone.utc)
    payload = {
        "generated_at": reference.isoformat(),
        "window_days": window_days,
        "log_path": str(log_path),
        "total_findings": len(findings),
        "estimated_wasted_tokens": sum(
            f.estimated_wasted_tokens for f in findings
        ),
        "findings": [asdict(f) for f in findings],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="audit-tokens",
        description=(
            "Aggregate PLAN-047 ghost-token detectors over an audit-log "
            "window."
        ),
    )
    ap.add_argument(
        "--window",
        type=int,
        default=30,
        help="Days lookback (0 = no window filter; default 30)",
    )
    ap.add_argument(
        "--format",
        choices=["markdown", "jsonl", "json", "stub"],
        default="markdown",
        help=(
            "Output format: 'markdown' human report, 'jsonl' one finding "
            "per line, 'json' summary object with findings array, 'stub' "
            "counts-only audit_tokens_emitted event via _lib.audit_emit "
            "(SEC-P0-04 / ADR-080 — used by SessionEnd subprocess invocation)."
        ),
    )
    ap.add_argument(
        "--content-ban",
        choices=["off", "strict"],
        default="off",
        help=(
            "Enforce SEC-P0-04 counts-only allowlist on emitted events. "
            "'strict' = call emit_audit_tokens_emitted (which scrubs "
            "forbidden keys + emits audit_tokens_key_dropped breadcrumb "
            "if any drift detected). 'off' (default) = legacy behavior."
        ),
    )
    ap.add_argument(
        "--session-id",
        type=str,
        default="",
        help=(
            "Session ID for audit_tokens_emitted event. When invoked "
            "from SessionEnd, the hook passes the active session ID."
        ),
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write to file instead of stdout.",
    )
    ap.add_argument(
        "--log",
        type=Path,
        default=_DEFAULT_LOG,
        help=f"Audit log path (default {_DEFAULT_LOG})",
    )
    ap.add_argument(
        "--top-per-detector",
        type=int,
        default=_DEFAULT_TOP_PER_DETECTOR,
        help=(
            "Markdown only: cap top-N findings listed per detector "
            f"(default {_DEFAULT_TOP_PER_DETECTOR})"
        ),
    )
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    log_path: Path = args.log
    if not log_path.exists():
        # Fail-open: empty report, exit 0, so CI smoke never blocks on a
        # fresh adopter repo that has no audit-log yet.
        sys.stderr.write(
            f"[audit-tokens] NOTE: log not found at {log_path} — "
            f"emitting empty report.\n"
        )
        findings: List[schema.Finding] = []
    else:
        findings = run_all(log_path)

    findings = filter_window(findings, args.window)

    if args.format == "markdown":
        content = render_markdown(
            findings,
            window_days=args.window,
            log_path=log_path,
            top_per_detector=args.top_per_detector,
        )
    elif args.format == "json":
        content = render_json_summary(
            findings, window_days=args.window, log_path=log_path
        ) + "\n"
    elif args.format == "stub":
        # SEC-P0-04 / ADR-080 — counts-only stub emission via _lib.audit_emit.
        # Emits a single audit_tokens_emitted event (allowlist-scrubbed
        # by emit_audit_tokens_emitted helper). Stdout is intentionally
        # minimal so SessionEnd subprocess capture doesn't blow up.
        content = _emit_stub_event(
            log_path=log_path,
            findings=findings,
            window_days=args.window,
            session_id=args.session_id,
            content_ban=args.content_ban,
        )
    else:  # jsonl
        content = render_jsonl(findings)
        if content and not content.endswith("\n"):
            content += "\n"

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        sys.stderr.write(
            f"[audit-tokens] wrote {args.output} "
            f"({len(findings)} finding(s))\n"
        )
    else:
        sys.stdout.write(content)
    return 0


def _emit_stub_event(
    *,
    log_path: Path,
    findings: List[schema.Finding],
    window_days: int,
    session_id: str,
    content_ban: str,
) -> str:
    """SEC-P0-04 / ADR-080 stub emission path.

    Computes counts from log + findings, calls emit_audit_tokens_emitted
    via _lib.audit_emit (which applies allowlist scrub + emits
    audit_tokens_key_dropped breadcrumb on drift). Stdout return is a
    one-line confirmation suitable for subprocess capture.

    content_ban=='strict' is currently semantically equivalent to
    emit_audit_tokens_emitted's default behavior (allowlist always
    enforced by the emitter). The flag is reserved for future
    expansion (e.g. a future 'lenient' mode that warns instead of
    strips).
    """
    import time as _time

    t0 = _time.monotonic()

    # Make _lib importable from .claude/hooks/_lib.
    # The script lives at .claude/scripts/audit-tokens.py; its repo root
    # is two parents up. log_path is unrelated (typically lives under
    # ~/.claude/projects/), so don't derive from it.
    hooks_dir: Optional[Path] = None
    script_root = Path(__file__).resolve().parent.parent.parent
    candidate = script_root / ".claude" / "hooks"
    if candidate.is_dir():
        hooks_dir = candidate
    if hooks_dir is None:
        cpd = os.environ.get("CLAUDE_PROJECT_DIR")
        if cpd:
            candidate = Path(cpd) / ".claude" / "hooks"
            if candidate.is_dir():
                hooks_dir = candidate
    if hooks_dir and str(hooks_dir) not in sys.path:
        sys.path.insert(0, str(hooks_dir))

    try:
        from _lib import audit_emit as _ae  # type: ignore[import-not-found]
    except ImportError as e:
        # Fail-open: emit nothing, return error line
        return f"[audit-tokens stub] _lib.audit_emit unavailable: {e}\n"

    # Compute stub metrics from audit log + findings
    events_scanned, tokens_in_total, tokens_out_total, tier_dist = (
        _scan_log_counts(log_path)
    )
    detector_findings_count: Dict[str, int] = {}
    for f in findings:
        detector_findings_count[f.detector] = (
            detector_findings_count.get(f.detector, 0) + 1
        )

    # Cost estimate: rough per-tier formula. Not exact pricing — informational only.
    # Anthropic prices per 1M tokens (approximate, 2026): opus ~$15 in / $75 out;
    # sonnet ~$3 in / $15 out; haiku ~$0.80 in / $4 out. Use blended average $5/M
    # for input + $25/M for output as a rough estimator.
    cost_cents = int(
        (tokens_in_total * 5 + tokens_out_total * 25) / 1_000_000 * 100
    )

    elapsed_ms = int((_time.monotonic() - t0) * 1000)

    project = os.environ.get("CLAUDE_PROJECT_DIR") or ""
    try:
        _ae.emit_audit_tokens_emitted(
            session_id=session_id,
            window_seconds=window_days * 86400,
            events_scanned=events_scanned,
            tokens_in_total=tokens_in_total,
            tokens_out_total=tokens_out_total,
            cost_cents=cost_cents,
            tier_id_distribution=tier_dist,
            detector_findings_count=detector_findings_count,
            hook_duration_ms=elapsed_ms,
            project=project,
        )
    except Exception as e:  # pragma: no cover — defensive
        return f"[audit-tokens stub] emit failed: {type(e).__name__}: {e}\n"

    return (
        f"[audit-tokens stub] emitted (events={events_scanned}, "
        f"tokens_in={tokens_in_total}, tokens_out={tokens_out_total}, "
        f"cost_cents={cost_cents}, findings={len(findings)}, "
        f"elapsed_ms={elapsed_ms}, content_ban={content_ban})\n"
    )


def _scan_log_counts(log_path: Path) -> Tuple[int, int, int, Dict[str, int]]:
    """Scan audit log and return (events, tin, tout, tier_distribution).

    Bounded by audit log file size; fails-open on any read error.
    Tier distribution counts model field per agent_spawn entry.
    """
    if not log_path.is_file():
        return (0, 0, 0, {})
    events_scanned = 0
    tokens_in_total = 0
    tokens_out_total = 0
    tier_dist: Dict[str, int] = {}
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events_scanned += 1
                try:
                    obj = json.loads(line)
                except (ValueError, json.JSONDecodeError):
                    continue
                if not isinstance(obj, dict):
                    continue
                tin = obj.get("tokens_in") or 0
                tout = obj.get("tokens_out") or 0
                if isinstance(tin, (int, float)):
                    tokens_in_total += int(tin)
                if isinstance(tout, (int, float)):
                    tokens_out_total += int(tout)
                model = obj.get("model")
                if isinstance(model, str) and model:
                    tier_dist[model] = tier_dist.get(model, 0) + 1
    except OSError:
        pass
    return (events_scanned, tokens_in_total, tokens_out_total, tier_dist)


if __name__ == "__main__":
    raise SystemExit(main())


# ---- Helpers re-exported for unit tests -----------------------------------
# (The tests import these names directly from the module.)
Finding = schema.Finding  # type: ignore[assignment]
