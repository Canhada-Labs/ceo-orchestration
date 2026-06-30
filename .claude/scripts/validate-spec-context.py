#!/usr/bin/env python3
"""Validate a spec.md before injecting as ## SPEC CONTEXT (PLAN-042 ITEM 6).

FINDING-14 (Wave A retrospective debate Round 1, security-engineer P1):
`pre-plan-brainstorm` produces a `spec.md` that the CEO injects verbatim
into every sub-agent prompt via `## SPEC CONTEXT` (ADR-058). An
adversary who controls the plan controls the spec — injection payload
in the spec becomes a cross-agent prompt-injection amplifier.

This script runs output_scan on a spec file and exits non-zero if any
LLM01 Prompt Injection family fires. Call it from inject workflows:

    python3 .claude/scripts/validate-spec-context.py \\
        .claude/plans/PLAN-042/spec.md

Exit codes:
    0  — spec is clean, safe to inject
    1  — spec contains injection patterns, ABORT spawn
    2  — usage or I/O error (fail-open: treat as clean)
    3  — output_scan import failure (fail-open)

Kill-switch: `CEO_SPEC_VALIDATION=0` skips validation (dogfood escape
hatch; FPR tuning period). Emits a warning to stderr but exits 0.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parents[1] / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


def _kill_switch() -> bool:
    return os.environ.get("CEO_SPEC_VALIDATION", "").strip().lower() in {
        "0", "false", "off", "no"
    }


_INJECTION_FAMILIES = frozenset({
    "LLM01_prompt_injection",
    "LLM02_insecure_output",
    "LLM10_model_theft",
})


def validate(spec_path: Path) -> int:
    """Validate a `## SPEC CONTEXT` block embedded in a debate/spawn prompt."""
    if _kill_switch():
        print(
            "[validate-spec-context] CEO_SPEC_VALIDATION=0 — skipping scan",
            file=sys.stderr,
        )
        return 0

    try:
        text = spec_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(
            f"[validate-spec-context] WARN read failed: {e} (fail-open)",
            file=sys.stderr,
        )
        return 2

    try:
        from _lib import output_scan  # type: ignore
    except ImportError as e:
        print(
            f"[validate-spec-context] WARN output_scan import: {e} "
            "(fail-open)",
            file=sys.stderr,
        )
        return 3

    try:
        result = output_scan.scan(text)
    except Exception as e:
        print(
            f"[validate-spec-context] WARN scan error: {type(e).__name__}: {e} "
            "(fail-open)",
            file=sys.stderr,
        )
        return 3

    family_counts = result.get("family_counts", {}) or {}
    hits = {
        fam: cnt
        for fam, cnt in family_counts.items()
        if fam in _INJECTION_FAMILIES and int(cnt) > 0
    }
    if hits:
        # Block spawn — ADR-058 injection surface hit.
        print(
            f"[validate-spec-context] BLOCK {spec_path}: "
            f"injection families hit: {hits}. "
            "Spawn MUST NOT include this spec via ## SPEC CONTEXT.",
            file=sys.stderr,
        )
        # Best-effort veto audit emit.
        try:
            from _lib import audit_emit  # type: ignore
            emit = getattr(audit_emit, "emit_veto_triggered", None)
            if emit is not None:
                emit(
                    hook="validate-spec-context",
                    reason_code="spec_injection_detected",
                    reason_preview=(
                        f"spec {spec_path.name} hit {len(hits)} injection "
                        f"families: {sorted(hits.keys())}"
                    ),
                    blocked_tool="Task",
                    project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
                )
        except Exception:
            pass
        return 1

    print(
        f"[validate-spec-context] OK {spec_path} "
        f"(total_findings={result.get('total_findings', 0)}, "
        "no injection families)",
        file=sys.stderr,
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", help="Path to spec.md to validate")
    args = ap.parse_args()
    path = Path(args.spec).resolve()
    if not path.exists() or not path.is_file():
        print(
            f"[validate-spec-context] WARN: spec path missing: {path} "
            "(fail-open)",
            file=sys.stderr,
        )
        return 2
    return validate(path)


if __name__ == "__main__":
    sys.exit(main())
