"""Reality ledger: claims."""

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

def detect_installable_claim_drift(
    *,
    repo_root: Path,
) -> List[Dict[str, Any]]:
    """Detector #2.

    Currently checks `.claude/rag/requirements.lock` — if the file exists
    but contains the marker text "PLACEHOLDER" / "NOT a valid pip install
    target", emit finding. Future: actually invoke `pip install --dry-run`.
    """
    findings: List[Dict[str, Any]] = []
    target = repo_root / ".claude" / "rag" / "requirements.lock"
    if not target.exists():
        return findings
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return findings
    rel = _to_repo_rel(target)
    placeholder_markers = (
        "PLACEHOLDER",
        "NOT a valid pip install target",
        "MUST refuse to run",
    )
    matched = [m for m in placeholder_markers if m in text]
    if matched:
        finding = _build_finding(
            detector="installable_claim_drift",
            severity=DETECTOR_REGISTRY["installable_claim_drift"]["severity"],
            confidence=0.99,
            claim_source_path=f"{rel}:1",
            expected_evidence=(
                f"pip install --require-hashes --no-deps -r {rel} returns 0"
            ),
            actual_evidence=(
                f"requirements.lock is a placeholder; markers found: {matched}"
            ),
            advisory_action=(
                "regenerate via pip-compile per the file's header instructions"
            ),
            extra={"target": rel, "markers": matched},
        )
        findings.append(finding)
    return findings


# ---------------------------------------------------------------------------
# Detector #3 — model_assignment_divergence (advisory v1 — claim-side only)
# ---------------------------------------------------------------------------

_AGENT_FRONTMATTER_MODEL_RE = re.compile(
    r"^model:\s*([a-zA-Z0-9._\-]+)\s*$", re.MULTILINE
)


def detect_model_assignment_divergence(
    *,
    repo_root: Path,
    audit_log_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Detector #3.

    v1 implementation collects claimed `model:` from agent frontmatter and
    compares against optional audit-log observation when an `audit_log_path`
    is provided. When the audit log is absent (sandbox / fresh checkout),
    the detector returns []. Production deployment passes
    `~/.claude/projects/.../audit-log.jsonl` via CLI flag.

    Phase 2 v1.14.0 ships the claim-collection + diff scaffold;
    full 30d observation rollup is wired in Phase 4 advisory CI.
    """
    findings: List[Dict[str, Any]] = []
    agents_dir = repo_root / ".claude" / "agents"
    if not agents_dir.exists():
        return findings

    claimed: Dict[str, str] = {}
    paths: Dict[str, str] = {}
    for f in sorted(agents_dir.rglob("*.md")):
        if _is_excluded(f, repo_root=repo_root):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = _AGENT_FRONTMATTER_MODEL_RE.search(text)
        if not m:
            continue
        slug = f.stem
        claimed[slug] = m.group(1)
        paths[slug] = _to_repo_rel(f)

    if not audit_log_path or not audit_log_path.exists():
        return findings

    observed: Dict[str, Dict[str, int]] = {}
    try:
        with audit_log_path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                if ev.get("action") != "agent_spawn":
                    continue
                role = ev.get("subagent_type") or ev.get("role") or ""
                model = ev.get("model") or ""
                if not role or not model:
                    continue
                observed.setdefault(role, {}).setdefault(model, 0)
                observed[role][model] += 1
    except OSError:
        return findings

    for role, claim_model in sorted(claimed.items()):
        bucket = observed.get(role)
        if not bucket:
            continue
        majority = max(bucket.items(), key=lambda kv: kv[1])
        if majority[0] != claim_model:
            finding = _build_finding(
                detector="model_assignment_divergence",
                severity=DETECTOR_REGISTRY["model_assignment_divergence"]["severity"],
                confidence=0.85,
                claim_source_path=paths.get(role, ""),
                expected_evidence=(
                    f"claim model={claim_model} matches observed-majority "
                    "in last 30d audit-log"
                ),
                actual_evidence=(
                    f"observed majority={majority[0]} (n={majority[1]}); "
                    f"claim={claim_model}"
                ),
                advisory_action=(
                    "either update agent frontmatter or investigate routing"
                ),
                extra={"role": role, "claim": claim_model,
                       "observed": majority[0], "n": majority[1]},
            )
            findings.append(finding)
    return findings


# ---------------------------------------------------------------------------
# Detector #4 — enforcement_commit_unpopulated
# ---------------------------------------------------------------------------

def detect_enforcement_commit_unpopulated(
    *,
    repo_root: Path,
) -> List[Dict[str, Any]]:
    """Detector #4.

    For every ADR with Status containing 'ACCEPTED' (case-insensitive),
    look for an `## Enforcement commit` section that contains either no
    SHA reference or a placeholder string ('(populated on flip)' etc.).
    """
    findings: List[Dict[str, Any]] = []
    adr_dir = repo_root / ".claude" / "adr"
    if not adr_dir.exists():
        return findings
    for f in sorted(adr_dir.glob("ADR-*.md")):
        if _is_excluded(f, repo_root=repo_root):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Find Status line (first match wins)
        status_match = _ADR_STATUS_RE.search(text)
        if not status_match:
            continue
        status_value = status_match.group(1).strip()
        if "ACCEPTED" not in status_value.upper():
            continue
        # Skip SUPERSEDED / RETRACTED / REJECTED
        if any(k in status_value.upper() for k in ("SUPERSEDED", "RETRACTED", "REJECTED")):
            continue

        header_match = _ADR_ENFORCEMENT_HEADER_RE.search(text)
        if not header_match:
            # Section absent on an ACCEPTED ADR is itself a finding.
            rel = _to_repo_rel(f)
            findings.append(_build_finding(
                detector="enforcement_commit_unpopulated",
                severity=DETECTOR_REGISTRY["enforcement_commit_unpopulated"]["severity"],
                confidence=0.95,
                claim_source_path=f"{rel}:1",
                expected_evidence=(
                    "## Enforcement commit section with backtick-wrapped SHA"
                ),
                actual_evidence="section absent",
                advisory_action="add Enforcement commit section + SHA",
                extra={"adr": f.name, "status": status_value},
            ))
            continue

        # Capture body until next H2 or EOF
        start = header_match.end()
        next_h2 = re.search(r"^##\s+", text[start:], re.MULTILINE)
        body_end = start + next_h2.start() if next_h2 else len(text)
        body = text[start:body_end]
        body_lineno = text[:header_match.start()].count("\n") + 1
        sha_match = _ENFORCEMENT_SHA_RE.search(body)
        placeholder_match = _ENFORCEMENT_PLACEHOLDER_RE.search(body)

        unpopulated = False
        reason = ""
        if not sha_match:
            unpopulated = True
            reason = "no SHA reference"
        elif placeholder_match:
            # Has a SHA pattern AND a placeholder marker — placeholder wins
            unpopulated = True
            reason = f"placeholder marker: {placeholder_match.group(0)!r}"

        # ADR-067 ground truth: text contains "(populated on flip"
        if not sha_match and not placeholder_match:
            # Maybe still empty (whitespace only)
            if not body.strip():
                unpopulated = True
                reason = "empty body"

        if unpopulated:
            rel = _to_repo_rel(f)
            findings.append(_build_finding(
                detector="enforcement_commit_unpopulated",
                severity=DETECTOR_REGISTRY["enforcement_commit_unpopulated"]["severity"],
                confidence=0.97,
                claim_source_path=f"{rel}:{body_lineno}",
                expected_evidence=(
                    "## Enforcement commit body contains backtick-wrapped SHA "
                    "(7-40 hex chars) + no placeholder markers"
                ),
                actual_evidence=reason,
                advisory_action=(
                    "populate enforcement_commit with the SHA where the "
                    "decision was wired"
                ),
                extra={"adr": f.name, "status": status_value},
            ))
    return findings


# ---------------------------------------------------------------------------
# Detector #6 — audit_action_phantom
# ---------------------------------------------------------------------------


__all__ = ['detect_installable_claim_drift', '_AGENT_FRONTMATTER_MODEL_RE', 'detect_model_assignment_divergence', 'detect_enforcement_commit_unpopulated']
