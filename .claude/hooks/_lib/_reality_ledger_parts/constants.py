"""Shared detector constants."""

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

SCHEMA_VERSION = "reality-ledger-finding.v1"

DEFAULT_DETECTOR_TIMEOUT_MS = 120000  # PLAN-107 S145 raised 5000->15000ms; PLAN-112-FOLLOWUP S158 raised 15000->120000ms — the AST-walk of the further-grown hooks+scripts tree now takes ~50s isolated and ~60s under full-suite load (measured), exceeding the old 15s cap consistently. 120s gives ~2x CI-hardware margin. Advisory detector; the cap only bounds completion. Honest accommodation of codebase growth, not a logic change.
SUITE_LATENCY_BUDGET_S = 30.0  # informational p95 budget per spec

# Severities (ordering matters for filtering)
_SEVERITIES = ("low", "medium", "high")
_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}

# Detector registry — slug -> human label + default severity
DETECTOR_REGISTRY: Dict[str, Dict[str, Any]] = {
    "runtime_read_missing": {"severity": "medium"},
    "installable_claim_drift": {"severity": "high"},
    "model_assignment_divergence": {"severity": "medium"},
    "enforcement_commit_unpopulated": {"severity": "low"},
    "audit_action_phantom": {"severity": "medium"},
    # PLAN-078 Wave 2 — estimate-drift detector. Severity is computed
    # per-finding by drift factor (low <1.5×, medium 1.5-2×, high >2×);
    # registry value is the default fallback when severity is unset.
    "estimate_drift": {"severity": "medium"},
}

# Anti-self-referential exclusion globs (post Round 1 R-SEC3).
SELF_EXCLUDE_BASENAMES = frozenset({
    "task-route.py",
    "reality-ledger.py",
})
SELF_EXCLUDE_PATH_FRAGMENTS = (
    "owner-ceremony/archive/",
    "/owner-ceremony/archive/",
    # PLAN-112-FOLLOWUP S158 — exclude plan `staging/` dirs from the scan.
    # They hold DRAFT mirrors of production code/docs (ready-to-apply
    # packages), NOT production claims, and the ~30 staging `.md` files
    # were inflating the `.md` detectors' scan (md_roots includes `.claude`)
    # past the detector timeout. Drafts must not be scanned as reality.
    "/staging/",
    "/_reality_ledger_parts/",
)

# Audit emission allowlist (Sec MF-3 contract; extended in Phase 5 KERNEL).
_REALITY_LEDGER_FINDING_ALLOWLIST: FrozenSet[str] = frozenset({
    "action", "ts", "detector", "severity",
    # confidence_bps: int basis-points (0..1000); replaces old float "confidence"
    # which caused CanonicalJsonError in the HMAC-covered canonical_json encoder.
    "confidence_bps",
    "claim_source_sha256", "finding_count_in_run",
})

# Markdown-only field set (MUST be excluded from JSON/JSONL).
_MARKDOWN_ONLY_FIELDS: FrozenSet[str] = frozenset({"claim_source_path"})

# Env-var prefix convention enforced by detector #1: only names matching
# this prefix family are surfaced as documented env-vars. Avoids the
# combinatorial false-positive set of every UPPER_SNAKE backtick token in
# planning docs (`_KNOWN_ACTIONS`, `VETO_HARDCODE`, `STDOUT`, etc).
_ENV_PREFIX_RE = re.compile(
    r"^("
    r"CEO_|CLAUDE_|ANTHROPIC_|"
    r"GITHUB_|GH_|"
    r"OTEL_|OTEL_EXPORTER_|"
    r"NPM_|"
    r"AWS_|GCP_|GOOGLE_|"
    r"DATABASE_|DB_|"
    r"OPENAI_|"
    r"COVERALLS_|CODECOV_|"
    r"SENTRY_|"
    r"PYTHONPATH$|PATH$|HOME$"
    r")"
)

# Doc-side regex: env var names appearing as `$VAR`, `VAR=value`, or
# inside backticks. Min 5 chars (e.g. `CEO_X`) to prevent matching the
# bare prefix `CEO_` (4 chars). Convention floor `_ENV_PREFIX_RE`
# additionally requires at least 1 char after the prefix underscore.
# Body of the env-var name: starts upper, ≥4 chars, ends in a non-underscore.
# Prevents `ANTHROPIC_` (trailing underscore = a prefix mention, not a name).
_ENV_NAME_BODY = r"[A-Z][A-Z0-9_]{2,62}[A-Z0-9]"
_BACKTICK_ENV_RE = re.compile(r"`(" + _ENV_NAME_BODY + r")`")
_SHELL_ASSIGN_RE = re.compile(r"\b(" + _ENV_NAME_BODY + r")=[^\s]")
_DOLLAR_VAR_RE = re.compile(r"\$(" + _ENV_NAME_BODY + r")\b")

# ADR Status field forms supported.
_ADR_STATUS_RE = re.compile(
    r"^(?:>\s*)?\*{0,2}Status:?\*{0,2}\s*[:\-]?\s*(.+?)\s*$",
    re.MULTILINE,
)
# Many ADRs use "**Status:** ACCEPTED ..." or "> **Status:** ..."
_ADR_ENFORCEMENT_HEADER_RE = re.compile(
    r"^##\s+Enforcement\s+commit\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_ENFORCEMENT_SHA_RE = re.compile(r"`([0-9a-f]{7,40})`")
_ENFORCEMENT_PLACEHOLDER_RE = re.compile(
    r"\((?:populated\s+on\s+flip|pending|TBD|to\s+be\s+populated|_pending_)",
    re.IGNORECASE,
)

# Detector #6 — emit_<action> regex inside python source.
_EMIT_CALL_RE = re.compile(
    r"\bemit_generic\s*\(\s*action\s*=\s*[\"']([a-z][a-z0-9_]*)[\"']"
)
_EMIT_NAMED_RE = re.compile(
    r"\baudit_emit\s*\.\s*emit_([a-z][a-z0-9_]*)\s*\("
)


# ---------------------------------------------------------------------------
# File walking utilities (deterministic, exclusion-aware)
# ---------------------------------------------------------------------------


__all__ = ['SCHEMA_VERSION', 'DEFAULT_DETECTOR_TIMEOUT_MS', 'SUITE_LATENCY_BUDGET_S', '_SEVERITIES', '_SEVERITY_ORDER', 'DETECTOR_REGISTRY', 'SELF_EXCLUDE_BASENAMES', 'SELF_EXCLUDE_PATH_FRAGMENTS', '_REALITY_LEDGER_FINDING_ALLOWLIST', '_MARKDOWN_ONLY_FIELDS', '_ENV_PREFIX_RE', '_ENV_NAME_BODY', '_BACKTICK_ENV_RE', '_SHELL_ASSIGN_RE', '_DOLLAR_VAR_RE', '_ADR_STATUS_RE', '_ADR_ENFORCEMENT_HEADER_RE', '_ENFORCEMENT_SHA_RE', '_ENFORCEMENT_PLACEHOLDER_RE', '_EMIT_CALL_RE', '_EMIT_NAMED_RE']
