#!/usr/bin/env python3
"""plan-tokens.py — Auto-generate budget_tokens estimates from a plan's §4 phase table.

PLAN-065 §4.2 — Token Estimator (renamed from plan-token-estimator.py per CR-S5).

Uses ADR-081 §Cost reference table to classify each phase row:
  - file edits (small/large)
  - hook overhead
  - archetype overhead
  - debate round overhead
  - CEO orchestration overhead

Output modes:
  --format markdown  — human table per phase + total (default)
  --format json      — machine-readable, lex-sorted by phase_id (CR-N7)
  --inject           — writes budget_tokens: directly into plan frontmatter (idempotent)
  --emit             — emit token_estimate_emitted audit action (no-op if not registered)

Safety:
  --cap-input 2MiB (default) — reject plans larger than 2 MiB (Sec NTH-3)

Usage:
    python3 plan-tokens.py <plan_path> [--format markdown|json] [--inject] [--emit]
    python3 plan-tokens.py <plan_path> --cap-input 2097152

Exit codes:
    0 — OK
    1 — plan not found or parse error
    2 — input exceeds size cap (Sec NTH-3)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CAP_INPUT_BYTES: int = 2 * 1024 * 1024  # 2 MiB default

# ADR-081 §Cost reference table — parsed ONCE at module import (Perf Unseen-3)
# Format: list of (pattern, tokens_in_low, tokens_in_high, tokens_out_low, tokens_out_high)
# Source: ADR-081 cost reference table (updated 2026-04-25)

_ADR_081_COST_TABLE: List[Dict[str, Any]] = [
    {
        "operation": "read_file",
        "tokens_in_low": 1000,
        "tokens_in_high": 3000,
        "tokens_out_low": 0,
        "tokens_out_high": 0,
    },
    {
        "operation": "edit_small",
        "tokens_in_low": 1000,
        "tokens_in_high": 2000,
        "tokens_out_low": 1000,
        "tokens_out_high": 2000,
    },
    {
        "operation": "edit_large",
        "tokens_in_low": 5000,
        "tokens_in_high": 10000,
        "tokens_out_low": 5000,
        "tokens_out_high": 10000,
    },
    {
        "operation": "test_run",
        "tokens_in_low": 5000,
        "tokens_in_high": 10000,
        "tokens_out_low": 2000,
        "tokens_out_high": 5000,
    },
    {
        "operation": "commit_push",
        "tokens_in_low": 2000,
        "tokens_in_high": 2000,
        "tokens_out_low": 1000,
        "tokens_out_high": 1000,
    },
    {
        "operation": "agent_dispatch",
        "tokens_in_low": 2000,
        "tokens_in_high": 5000,
        "tokens_out_low": 1000,
        "tokens_out_high": 3000,
    },
    {
        "operation": "sentinel_ceremony",
        "tokens_in_low": 15000,
        "tokens_in_high": 25000,
        "tokens_out_low": 5000,
        "tokens_out_high": 10000,
    },
    {
        "operation": "adr_draft",
        "tokens_in_low": 15000,
        "tokens_in_high": 25000,
        "tokens_out_low": 10000,
        "tokens_out_high": 15000,
    },
    {
        "operation": "plan_draft",
        "tokens_in_low": 20000,
        "tokens_in_high": 30000,
        "tokens_out_low": 15000,
        "tokens_out_high": 20000,
    },
    {
        "operation": "closeout",
        "tokens_in_low": 30000,
        "tokens_in_high": 50000,
        "tokens_out_low": 20000,
        "tokens_out_high": 30000,
    },
    {
        "operation": "validate_governance",
        "tokens_in_low": 1000,
        "tokens_in_high": 1000,
        "tokens_out_low": 500,
        "tokens_out_high": 500,
    },
    {
        "operation": "debate_round",
        "tokens_in_low": 80000,
        "tokens_in_high": 150000,
        "tokens_out_low": 40000,
        "tokens_out_high": 80000,
    },
    {
        "operation": "ceo_orchestration",
        "tokens_in_low": 20000,
        "tokens_in_high": 50000,
        "tokens_out_low": 10000,
        "tokens_out_high": 25000,
    },
]

# Build a lookup dict at module import — fail-CLOSED if anything is wrong
try:
    _COST_LOOKUP: Dict[str, Dict[str, Any]] = {
        row["operation"]: row for row in _ADR_081_COST_TABLE
    }
except Exception as _e:  # pragma: no cover
    raise RuntimeError(
        f"plan-tokens: Failed to pre-compute ADR-081 cost table at import: {_e}"
    ) from _e

# Pricing (Opus 4.8, 2026-06) — $ per 1M tokens.
# Verified against ceo-cost.py _DEFAULT_PRICING (claude-opus-4-8 $5/$25).
# ADR-142 bump: was Opus 4.7 $15/$75; current default-CEO model is Opus 4.8.
_PRICE_INPUT_PER_M: float = 5.0
_PRICE_OUTPUT_PER_M: float = 25.0


# ---------------------------------------------------------------------------
# Phase table parsing
# ---------------------------------------------------------------------------

# Matches markdown table rows:  | col1 | col2 | ... |
_TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
# Matches a separator row like  | --- | :---: | ---: |
_SEPARATOR_ROW_RE = re.compile(r"^\s*\|[\s\-:|]+\|\s*$")

# Phase ID patterns we look for in the first column
# E.g. "0", "1", "2", "4-B", "4-C", "7", "Debate overhead", "CEO orchestration"
_PHASE_ID_RE = re.compile(r"^[\w\-\.]+(?:\s+\w+)*$", re.IGNORECASE)

# Key patterns in phase row "Goal" or "Files touched" column to infer cost class
_DEBATE_KEYWORDS = re.compile(
    r"\bdebate\b|\bround\b|\bdebate round\b|\bspawn\b.*\barchetypes?\b",
    re.IGNORECASE,
)
_CANONICAL_KEYWORDS = re.compile(
    r"\bcanonical\b|\bsentinel\b|\bgpg\b|\bkernel\b",
    re.IGNORECASE,
)
_HOOK_KEYWORDS = re.compile(
    r"\bhook\b|\bpreToolUse\b|\bPostToolUse\b|\baudit_log\b|\bcheck_\w+\.py\b",
    re.IGNORECASE,
)
_LARGE_FILE_KEYWORDS = re.compile(
    r"\bnew script\b|\bnew command\b|\bnew lib\b|\b\d{3,}\s+LoC\b|"
    r"\bnew.*\.py\b|\bnew hook\b|\bnew module\b",
    re.IGNORECASE,
)
_BASELINE_KEYWORDS = re.compile(
    r"\bbaseline\b|\bmeasure\b|\breport only\b|\bno edit\b|\bdoc only\b",
    re.IGNORECASE,
)
_RELEASE_KEYWORDS = re.compile(
    r"\brelease\b|\btag\b|\bchangelog\b|\bversion\b",
    re.IGNORECASE,
)
_TEST_KEYWORDS = re.compile(
    r"\btest\b|\bpytest\b|\bmutation\b|\bconformance\b|\bsmoke\b",
    re.IGNORECASE,
)

# Column header names we expect (Phase, Goal, Files, Canonical, Tokens, etc.)
_PHASE_COL_NAMES = {"phase", "id", "#"}
_GOAL_COL_NAMES = {"goal", "description", "desc", "objective"}
_FILES_COL_NAMES = {"files", "files touched", "deliverable", "deliverables"}
_TOKENS_COL_NAMES = {"tokens", "tokens (in/out)", "token cost", "budget"}
_CANONICAL_COL_NAMES = {"canonical", "kernel", "guard"}


def _parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    """Extract simple YAML frontmatter (key: value pairs) and body.

    Returns (frontmatter_dict, body_text). Supports only flat key: value
    (no nested YAML). Fails silently (returns empty dict) on malformed YAML.
    The body is the text after the closing ---.
    """
    if not text.startswith("---"):
        return {}, text

    lines = text.split("\n")
    end_idx = -1
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        return {}, text

    fm: Dict[str, str] = {}
    for line in lines[1:end_idx]:
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip()
            if k:
                fm[k] = v

    body = "\n".join(lines[end_idx + 1 :])
    return fm, body


def _find_phase_table(body: str) -> Optional[str]:
    """Extract the §4 phase table from the plan body.

    Looks for the first markdown table after a '## §4' or '## 4.' heading
    (case-insensitive). Returns the raw table lines as a single string,
    or None if not found.
    """
    # Find the §4 section heading
    section_start = -1
    for i, line in enumerate(body.splitlines()):
        stripped = line.strip()
        if re.match(r"^#+\s+§?4[\.\s]", stripped, re.IGNORECASE):
            section_start = i
            break

    if section_start == -1:
        return None

    lines = body.splitlines()
    table_lines: List[str] = []
    in_table = False

    for line in lines[section_start:]:
        stripped = line.strip()
        # Start capturing on first table line
        if stripped.startswith("|"):
            in_table = True
            table_lines.append(line)
        elif in_table:
            # Table ends when we hit a non-pipe line (blank or text)
            if stripped and not stripped.startswith("|"):
                break
            elif not stripped:
                # Blank line may end the table
                break

    if not table_lines:
        return None

    return "\n".join(table_lines)


def _split_row(row: str) -> List[str]:
    """Split a markdown table row into cells (strip whitespace)."""
    parts = row.strip().strip("|").split("|")
    return [p.strip() for p in parts]


def _detect_column_indices(header_cells: List[str]) -> Dict[str, int]:
    """Map semantic column names to cell indices from header row."""
    mapping: Dict[str, int] = {}
    for i, cell in enumerate(header_cells):
        lower = cell.lower().strip()
        if lower in _PHASE_COL_NAMES:
            mapping.setdefault("phase", i)
        if lower in _GOAL_COL_NAMES:
            mapping.setdefault("goal", i)
        if lower in _FILES_COL_NAMES:
            mapping.setdefault("files", i)
        if lower in _TOKENS_COL_NAMES:
            mapping.setdefault("tokens", i)
        if lower in _CANONICAL_COL_NAMES:
            mapping.setdefault("canonical", i)
    # Always default phase to 0 if not found
    mapping.setdefault("phase", 0)
    return mapping


def parse_phase_table(
    table_text: str,
) -> List[Dict[str, str]]:
    """Parse a markdown phase table into a list of row dicts.

    Each dict has at least: phase_id, goal, files, canonical, tokens_hint.
    Missing columns default to empty string.
    """
    lines = [l for l in table_text.splitlines() if l.strip()]
    if not lines:
        return []

    rows: List[Dict[str, str]] = []
    col_map: Dict[str, int] = {}
    header_parsed = False

    for line in lines:
        if not line.strip().startswith("|"):
            continue
        cells = _split_row(line)
        if not cells:
            continue

        # Check if separator row
        if all(re.match(r"^[-:\s]+$", c) for c in cells if c):
            continue

        if not header_parsed:
            col_map = _detect_column_indices(cells)
            header_parsed = True
            continue

        phase_idx = col_map.get("phase", 0)
        goal_idx = col_map.get("goal", 1)
        files_idx = col_map.get("files", 2)
        tokens_idx = col_map.get("tokens", -1)
        canonical_idx = col_map.get("canonical", -1)

        def safe_get(idx: int) -> str:
            if idx < 0 or idx >= len(cells):
                return ""
            return cells[idx]

        phase_id = safe_get(phase_idx)
        if not phase_id or not phase_id.replace("-", "").replace(".", "").replace(" ", "").replace("*", ""):
            continue

        rows.append(
            {
                "phase_id": phase_id,
                "goal": safe_get(goal_idx),
                "files": safe_get(files_idx),
                "tokens_hint": safe_get(tokens_idx),
                "canonical": safe_get(canonical_idx),
            }
        )

    return rows


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

def _parse_token_range(hint: str) -> Optional[Tuple[int, int]]:
    """Try to parse an explicit token range hint like '~80k / ~50k' or '30k/10k'.

    Returns (input_tokens, output_tokens) or None if not parseable.
    """
    if not hint:
        return None
    # Look for pattern like ~80k / ~50k or 80k/50k or 80000/50000
    m = re.search(
        r"[~]?\s*(\d+(?:\.\d+)?)\s*[kK]?\s*(?:input)?\s*[/,]\s*[~]?\s*(\d+(?:\.\d+)?)\s*[kK]?",
        hint,
    )
    if not m:
        return None
    try:
        raw_in = float(m.group(1))
        raw_out = float(m.group(2))
        # Determine if these are k-scale or absolute
        # If the full match contains 'k' or 'K', multiply by 1000
        full_match = m.group(0)
        if re.search(r"[kK]", full_match):
            raw_in *= 1000
            raw_out *= 1000
        return (int(raw_in), int(raw_out))
    except (ValueError, IndexError):
        return None


def _classify_phase(row: Dict[str, str]) -> Dict[str, Any]:
    """Estimate token cost for a single phase row.

    Classification priority:
    1. If tokens_hint is parseable → use it directly
    2. Infer from keywords in goal + files + canonical fields
    3. Default to small-edit cost

    Returns dict with: phase_id, input_low, input_high, output_low, output_high,
                       operations (list of classified operation types)
    """
    phase_id = row["phase_id"]
    goal = row.get("goal", "")
    files = row.get("files", "")
    tokens_hint = row.get("tokens_hint", "")
    canonical = row.get("canonical", "")

    combined = f"{goal} {files} {canonical}".lower()

    # Try explicit hint first
    explicit = _parse_token_range(tokens_hint)
    if explicit is not None:
        inp, out = explicit
        return {
            "phase_id": phase_id,
            "input_low": int(inp * 0.8),
            "input_high": int(inp * 1.2),
            "output_low": int(out * 0.8),
            "output_high": int(out * 1.2),
            "operations": ["hint_parsed"],
            "source": "hint",
        }

    operations: List[str] = []
    in_low = 0
    in_high = 0
    out_low = 0
    out_high = 0

    def add_op(op: str) -> None:
        nonlocal in_low, in_high, out_low, out_high
        entry = _COST_LOOKUP.get(op)
        if entry is None:
            return  # unknown op, skip
        operations.append(op)
        in_low += entry["tokens_in_low"]
        in_high += entry["tokens_in_high"]
        out_low += entry["tokens_out_low"]
        out_high += entry["tokens_out_high"]

    # Special cases by phase_id pattern
    phase_lower = phase_id.lower().strip("*")

    if re.search(r"debate|orchestrat", phase_lower):
        add_op("debate_round")
        add_op("ceo_orchestration")
        return {
            "phase_id": phase_id,
            "input_low": in_low,
            "input_high": in_high,
            "output_low": out_low,
            "output_high": out_high,
            "operations": operations,
            "source": "keyword_phase",
        }

    if re.search(r"ceo\s+orchestr", combined):
        add_op("ceo_orchestration")
        return {
            "phase_id": phase_id,
            "input_low": in_low,
            "input_high": in_high,
            "output_low": out_low,
            "output_high": out_high,
            "operations": operations,
            "source": "keyword_combined",
        }

    # CEO orchestration row
    if "ceo orchestration" in combined or "ceo_orchestration" in combined:
        add_op("ceo_orchestration")
        return {
            "phase_id": phase_id,
            "input_low": in_low,
            "input_high": in_high,
            "output_low": out_low,
            "output_high": out_high,
            "operations": operations,
            "source": "ceo_orchestration",
        }

    # Baseline / report only
    if _BASELINE_KEYWORDS.search(combined):
        add_op("read_file")
        add_op("read_file")
        add_op("ceo_orchestration")
        return {
            "phase_id": phase_id,
            "input_low": in_low,
            "input_high": in_high,
            "output_low": out_low,
            "output_high": out_high,
            "operations": operations,
            "source": "baseline",
        }

    # Debate overhead
    if _DEBATE_KEYWORDS.search(combined):
        add_op("debate_round")

    # Canonical / sentinel / kernel ceremony
    if _CANONICAL_KEYWORDS.search(canonical) or _CANONICAL_KEYWORDS.search(files):
        add_op("sentinel_ceremony")

    # Hook work
    if _HOOK_KEYWORDS.search(combined):
        add_op("edit_large")

    # New large files / scripts
    if _LARGE_FILE_KEYWORDS.search(combined):
        add_op("edit_large")
    else:
        add_op("edit_small")

    # Test work
    if _TEST_KEYWORDS.search(combined):
        add_op("test_run")

    # Release phase
    if _RELEASE_KEYWORDS.search(combined):
        add_op("closeout")
        add_op("commit_push")

    # Always add a read + commit
    add_op("read_file")
    add_op("commit_push")

    # Ensure we have at least something
    if not operations:
        add_op("edit_small")

    return {
        "phase_id": phase_id,
        "input_low": in_low,
        "input_high": in_high,
        "output_low": out_low,
        "output_high": out_high,
        "operations": operations,
        "source": "keyword_body",
    }


def estimate_plan(rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Run estimation for all phase rows. Returns list of estimate dicts."""
    return [_classify_phase(row) for row in rows]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _usd(in_tokens: int, out_tokens: int) -> float:
    return (in_tokens * _PRICE_INPUT_PER_M + out_tokens * _PRICE_OUTPUT_PER_M) / 1_000_000


def render_markdown(estimates: List[Dict[str, Any]]) -> str:
    """Render a human-readable markdown table of estimates."""
    lines: List[str] = []
    lines.append("# plan-tokens estimate")
    lines.append("")
    lines.append(
        "| Phase | Input (low) | Input (high) | Output (low) | Output (high) | USD (mid) |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|")

    total_in_low = 0
    total_in_high = 0
    total_out_low = 0
    total_out_high = 0

    for est in estimates:
        phase_id = est["phase_id"]
        il = est["input_low"]
        ih = est["input_high"]
        ol = est["output_low"]
        oh = est["output_high"]
        mid_in = (il + ih) // 2
        mid_out = (ol + oh) // 2
        usd = _usd(mid_in, mid_out)
        lines.append(
            f"| {phase_id} | {il:,} | {ih:,} | {ol:,} | {oh:,} | ${usd:.2f} |"
        )
        total_in_low += il
        total_in_high += ih
        total_out_low += ol
        total_out_high += oh

    mid_in_total = (total_in_low + total_in_high) // 2
    mid_out_total = (total_out_low + total_out_high) // 2
    total_usd = _usd(mid_in_total, mid_out_total)
    lines.append(
        f"| **TOTAL** | **{total_in_low:,}** | **{total_in_high:,}** | "
        f"**{total_out_low:,}** | **{total_out_high:,}** | **${total_usd:.2f}** |"
    )
    lines.append("")
    lines.append(
        f"**Budget summary:** ~{total_in_low // 1000}k–{total_in_high // 1000}k input "
        f"/ ~{total_out_low // 1000}k–{total_out_high // 1000}k output "
        f"/ ~${total_usd:.0f} USD (Opus 4.8 mid estimate)"
    )
    return "\n".join(lines) + "\n"


def render_json(estimates: List[Dict[str, Any]]) -> str:
    """Render deterministic JSON output, lex-sorted by phase_id (CR-N7)."""
    sorted_ests = sorted(estimates, key=lambda e: e["phase_id"])
    total_in_low = sum(e["input_low"] for e in sorted_ests)
    total_in_high = sum(e["input_high"] for e in sorted_ests)
    total_out_low = sum(e["output_low"] for e in sorted_ests)
    total_out_high = sum(e["output_high"] for e in sorted_ests)
    mid_in = (total_in_low + total_in_high) // 2
    mid_out = (total_out_low + total_out_high) // 2

    payload: Dict[str, Any] = {
        "phases": sorted_ests,
        "total": {
            "input_tokens_low": total_in_low,
            "input_tokens_high": total_in_high,
            "output_tokens_low": total_out_low,
            "output_tokens_high": total_out_high,
            "input_tokens": mid_in,
            "output_tokens": mid_out,
            "usd_mid": round(_usd(mid_in, mid_out), 2),
        },
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# --inject mode (idempotent frontmatter injection)
# ---------------------------------------------------------------------------

def _build_budget_value(estimates: List[Dict[str, Any]]) -> str:
    """Build the budget_tokens frontmatter string from estimates."""
    total_in_low = sum(e["input_low"] for e in estimates)
    total_in_high = sum(e["input_high"] for e in estimates)
    total_out_low = sum(e["output_low"] for e in estimates)
    total_out_high = sum(e["output_high"] for e in estimates)
    mid_in = (total_in_low + total_in_high) // 2
    mid_out = (total_out_low + total_out_high) // 2
    total_low = total_in_low + total_out_low
    total_high = total_in_high + total_out_high

    def _k(n: int) -> str:
        if n >= 1_000_000:
            return f"{n / 1_000_000:.2g}M"
        return f"{n // 1000}k"

    return f"{_k(total_low)}-{_k(total_high)} ({_k(mid_in)} in / {_k(mid_out)} out)"


def inject_frontmatter(plan_text: str, estimates: List[Dict[str, Any]]) -> str:
    """Write budget_tokens: into plan frontmatter. Idempotent (CR-N6).

    Cases handled:
    1. Empty frontmatter (no ---) → prepend minimal frontmatter block
    2. budget_tokens: already present → replace existing value
    3. Malformed YAML (--- block present but broken) → add after first ---
    4. Multi-key frontmatter → find and replace budget_tokens key

    Returns updated plan text.
    """
    value = _build_budget_value(estimates)
    new_line = f"budget_tokens: {value}"

    # Case 1: No frontmatter at all
    if not plan_text.startswith("---"):
        return f"---\n{new_line}\n---\n\n{plan_text}"

    lines = plan_text.split("\n")
    # Find closing ---
    close_idx = -1
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            close_idx = i
            break

    if close_idx == -1:
        # Malformed: has opening --- but no closing ---. Insert after first line.
        lines.insert(1, new_line)
        return "\n".join(lines)

    # Check if budget_tokens already present in frontmatter
    for i in range(1, close_idx):
        if lines[i].startswith("budget_tokens:"):
            lines[i] = new_line
            return "\n".join(lines)

    # Not present: insert before closing ---
    lines.insert(close_idx, new_line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# --emit mode
# ---------------------------------------------------------------------------

def _try_emit(plan_path: Path, estimates: List[Dict[str, Any]]) -> None:
    """Emit token_estimate_emitted action if registered in _KNOWN_ACTIONS.

    No-op (with stderr note) for v1.12.1 — the `token_estimate_emitted`
    action is NOT yet registered in `_KNOWN_ACTIONS`. Wiring is deferred
    to v1.13.0 / PLAN-067 (token-economy extensions). Per PLAN-065 §4.2
    spec: "If kernel ceremony not run in v1.12.0, `--emit` flag is a
    no-op stub that logs to stderr only."

    The actual emit call is intentionally absent so that
    `check-audit-registry-coverage.py` does not detect an orphan
    `emit_token_estimate_emitted()` call site (would block PR via
    test_session_76_audit_v3_findings + test_check_audit_registry_coverage).
    Re-introduce after v1.13.0 kernel ceremony adds the action +
    typed wrapper to audit_emit.
    """
    sys.stderr.write(
        "[plan-tokens] --emit: token_estimate_emitted not registered "
        "in _KNOWN_ACTIONS (deferred to v1.13.0 / PLAN-067); --emit is "
        "a no-op stub in v1.12.1.\n"
    )
    # Reference plan_path + estimates so static analyzers see them used:
    _ = plan_path, estimates
    return


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="plan-tokens",
        description=(
            "Auto-generate budget_tokens estimates from a plan's §4 phase table. "
            "(PLAN-065 §4.2 / ADR-081)"
        ),
    )
    ap.add_argument("plan", type=Path, help="Path to the plan markdown file.")
    ap.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format: 'markdown' (default) or 'json' (lex-sorted by phase_id).",
    )
    ap.add_argument(
        "--inject",
        action="store_true",
        help="Write budget_tokens: into plan frontmatter (idempotent).",
    )
    ap.add_argument(
        "--emit",
        action="store_true",
        help="Emit token_estimate_emitted audit action (no-op if action not registered).",
    )
    ap.add_argument(
        "--cap-input",
        type=int,
        default=_CAP_INPUT_BYTES,
        metavar="BYTES",
        help=f"Reject plans larger than N bytes (default {_CAP_INPUT_BYTES} = 2 MiB, Sec NTH-3).",
    )
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    plan_path: Path = args.plan

    if not plan_path.is_file():
        sys.stderr.write(f"error: plan not found: {plan_path}\n")
        return 1

    # Size cap (Sec NTH-3)
    plan_bytes = plan_path.stat().st_size
    if plan_bytes > args.cap_input:
        sys.stderr.write(
            f"error: input exceeds {args.cap_input} byte cap "
            f"({plan_bytes} bytes in {plan_path})\n"
        )
        return 2

    try:
        plan_text = plan_path.read_text(encoding="utf-8")
    except OSError as e:
        sys.stderr.write(f"error: cannot read {plan_path}: {e}\n")
        return 1

    _fm, body = _parse_frontmatter(plan_text)
    table_text = _find_phase_table(body)

    if table_text is None:
        sys.stderr.write(
            f"error: no §4 phase table found in {plan_path}\n"
        )
        return 1

    rows = parse_phase_table(table_text)
    if not rows:
        sys.stderr.write(
            f"error: phase table found but no rows parsed in {plan_path}\n"
        )
        return 1

    estimates = estimate_plan(rows)

    # --inject mode
    if args.inject:
        updated = inject_frontmatter(plan_text, estimates)
        plan_path.write_text(updated, encoding="utf-8")
        sys.stderr.write(
            f"[plan-tokens] injected budget_tokens into {plan_path}\n"
        )

    # --emit mode
    if args.emit:
        _try_emit(plan_path, estimates)

    # Output
    if args.format == "json":
        sys.stdout.write(render_json(estimates))
    else:
        sys.stdout.write(render_markdown(estimates))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
