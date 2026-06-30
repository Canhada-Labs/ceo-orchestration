#!/usr/bin/env python3
"""token-estimator — pre-task token + wallclock + USD estimator + CLI log-derived
wallclock reporting.

PLAN-083 Wave 0a sub-agent 0.2 deliverable. Stdlib-only. Python 3.9+.

Two sub-commands:

    estimate <plan-id|--input-file FILE>
        Read a plan markdown (looked up under `.claude/plans/` by PLAN-NNN)
        or arbitrary file, extract sub-agent dispatch table(s) from §5.* /
        `Est tokens` columns, and emit a structured estimate covering
        per-wave + cumulative + parallelization-ceiling-adjusted wallclock
        + USD. Cost table loaded from cost-table.yaml; stale tables raise
        a stderr warning per Perf P1-1.

    wallclock --plan-id PLAN-NNN
        Read the audit log for `wallclock_milestone` / `wallclock_milestone_started`
        events with matching `plan_id`, compute elapsed time per wave +
        total. Replaces the deferred SSE dashboard (PLAN-083 §4) with
        CLI-derived reporting per AC7 measurement protocol.

Cost-table integration: `cost_table_valid_until` field per Perf P1-1
(R1 outcome). After expiry, estimator falls back to last-known rates +
emits stderr warning. Refresh procedure documented in `notes.md`.

Token-to-wallclock conversion: linear factor `seconds_per_ktok` from
cost-table (default 4.0s/ktok, empirical median S96-S105 sub-agent
dispatches). Wallclock_paralelizado = sum(per_sub_agent_wallclock) /
min(num_sub_agents, max_parallel).

Exit codes::

    0 — success (includes empty wallclock result + post-expiry warning)
    1 — bad CLI args / unparseable plan / missing input
    2 — cost-table missing or unparseable

Sec P1 / Sec MF-3 alignment: all paths read-only; outputs to stdout/stderr
only; no shell-out; YAML mini-parser rejects anchors/aliases/flow-style.
Log-derived strings (plan_id, wave) are validated via regex allowlist
before display (defers full _lib/redact.py to canonical integration —
see `notes.md` §Sanitization deferment).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants + allowlist regexes
# ---------------------------------------------------------------------------

_PLAN_ID_RE = re.compile(r"^PLAN-\d{3,}$")
_WAVE_TOKEN_RE = re.compile(r"^[a-zA-Z0-9_.-]{1,64}$")
_EST_TOKENS_HEADER_RE = re.compile(r"\|\s*Est\s+tokens\s*\|", re.IGNORECASE)
# Match cell values like "90k", "1.3-2M", "70k", "n/a", "0".
_TOKEN_VALUE_RE = re.compile(
    r"(?P<lo>\d+(?:\.\d+)?)\s*(?:-\s*(?P<hi>\d+(?:\.\d+)?))?\s*(?P<unit>[kKmM])?\s*$"
)
_SUB_AGENT_ID_RE = re.compile(r"^\s*\|\s*(?P<id>[0-9]+(?:\.[0-9a-z]+)?)\s*\|")
_WAVE_HEADER_RE = re.compile(
    r"^###\s+§(?P<num>\S+)\s+Wave\s+(?P<wave>[^\n]+)$", re.MULTILINE
)

_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MiB plan-file ceiling


# ---------------------------------------------------------------------------
# Mini YAML parser (stdlib-only). Rejects anchors / aliases / flow-style.
# ---------------------------------------------------------------------------


class CostTableError(Exception):
    """Raised when cost-table is missing, malformed, or rejected."""


def _parse_cost_table_yaml(text: str) -> Dict[str, Any]:
    """Parse the cost-table.yaml mini-subset. Stdlib-only.

    Supports: top-level scalars, two-level nested dicts (`models:` +
    `parallel_ceiling:`). Rejects flow-style (`{`, `[`), anchors (`&`),
    aliases (`*`), and document markers (`---`).
    """
    result: Dict[str, Any] = {}
    current_section: Optional[str] = None
    current_key: Optional[str] = None

    for raw_lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        # Reject unsafe syntax explicitly.
        stripped = line.lstrip()
        if stripped.startswith("---") or stripped.startswith("..."):
            raise CostTableError(
                f"line {raw_lineno}: document markers not supported"
            )
        if any(stripped.startswith(c) for c in ("&", "*", "{", "[", "?")):
            raise CostTableError(
                f"line {raw_lineno}: anchor/alias/flow-style rejected"
            )

        indent = len(line) - len(stripped)

        if indent == 0:
            current_section = None
            current_key = None
            if ":" not in stripped:
                raise CostTableError(f"line {raw_lineno}: expected `key: value`")
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if not value:
                # Section header (dict follows)
                result[key] = {}
                current_section = key
            else:
                result[key] = _coerce_scalar(value)
        elif indent == 2:
            if current_section is None:
                raise CostTableError(
                    f"line {raw_lineno}: nested entry with no parent section"
                )
            if ":" not in stripped:
                raise CostTableError(f"line {raw_lineno}: expected `key: value`")
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if not value:
                result[current_section][key] = {}
                current_key = key
            else:
                result[current_section][key] = _coerce_scalar(value)
                current_key = None
        elif indent == 4:
            if current_section is None or current_key is None:
                raise CostTableError(
                    f"line {raw_lineno}: 4-space indent with no parent dict"
                )
            if ":" not in stripped:
                raise CostTableError(f"line {raw_lineno}: expected `key: value`")
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            # Strip inline `# comment` from scalar values (mini-parser only).
            if " #" in value:
                value = value.split(" #", 1)[0].strip()
            result[current_section][current_key][key] = _coerce_scalar(value)
        else:
            raise CostTableError(
                f"line {raw_lineno}: unsupported indent depth ({indent} spaces)"
            )

    return result


def _coerce_scalar(raw: str) -> Any:
    """Coerce a YAML scalar token to Python (bool / int / float / date / str)."""
    value = raw.strip()
    # Strip surrounding quotes.
    if len(value) >= 2 and (
        (value[0] == '"' and value[-1] == '"')
        or (value[0] == "'" and value[-1] == "'")
    ):
        return value[1:-1]
    # Bool.
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    # ISO date YYYY-MM-DD (must come before int to avoid misparse).
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    # Int.
    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            pass
    # Float.
    if re.fullmatch(r"-?\d+\.\d+", value):
        try:
            return float(value)
        except ValueError:
            pass
    return value


def load_cost_table(path: Optional[Path] = None) -> Dict[str, Any]:
    """Read + parse cost-table.yaml. Default location: sibling of this script."""
    if path is None:
        path = Path(__file__).resolve().parent / "cost-table.yaml"
    if not path.is_file():
        raise CostTableError(f"cost-table not found at {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CostTableError(f"cannot read cost-table {path}: {exc}") from exc
    table = _parse_cost_table_yaml(text)
    # Minimal sanity check.
    for required in ("models", "default_model", "blended_input_share",
                     "blended_output_share", "seconds_per_ktok",
                     "cost_table_valid_until"):
        if required not in table:
            raise CostTableError(
                f"cost-table missing required field `{required}`"
            )
    return table


def check_cost_table_staleness(
    table: Dict[str, Any],
    today: Optional[date] = None,
) -> Tuple[bool, str]:
    """Return (is_stale, message). Message is empty when not stale.

    Stale means today > cost_table_valid_until. Stderr warning emitted
    by the CLI wrapper; library function is pure.
    """
    if today is None:
        today = date.today()
    valid_until = table.get("cost_table_valid_until")
    if not isinstance(valid_until, date):
        return (
            True,
            "cost_table_valid_until is not a parseable date; treating as stale",
        )
    if today > valid_until:
        days_over = (today - valid_until).days
        return (
            True,
            f"cost-table expired {days_over} day(s) ago (valid_until={valid_until.isoformat()}); "
            "falling back to last-known rates — refresh per notes.md procedure",
        )
    return (False, "")


# ---------------------------------------------------------------------------
# Token-cell parsing
# ---------------------------------------------------------------------------


def parse_token_cell(cell: str) -> Optional[Tuple[float, float]]:
    """Parse an `Est tokens` cell like `90k`, `1.3-2M`, `70k`, `n/a`.

    Returns (low, high) in **absolute tokens** (not k or M). Returns None
    for unparseable or `n/a`.
    """
    if not cell:
        return None
    s = cell.strip().lower()
    if not s or s in ("n/a", "na", "-", "tbd", "0"):
        return None
    m = _TOKEN_VALUE_RE.fullmatch(s)
    if not m:
        return None
    lo = float(m.group("lo"))
    hi = float(m.group("hi")) if m.group("hi") else lo
    unit = (m.group("unit") or "").lower()
    multiplier = {"": 1.0, "k": 1_000.0, "m": 1_000_000.0}.get(unit, 1.0)
    return (lo * multiplier, hi * multiplier)


def _validate_plan_id(raw: str) -> str:
    """Allowlist-validate a plan_id string (defends against log-derived input)."""
    if not isinstance(raw, str) or not _PLAN_ID_RE.fullmatch(raw):
        raise ValueError(f"invalid plan_id: {raw!r} (expected PLAN-NNN)")
    return raw


def _validate_wave_token(raw: str) -> str:
    if not isinstance(raw, str) or not _WAVE_TOKEN_RE.fullmatch(raw):
        # Coerce to safe placeholder rather than raise — log-derived strings.
        return "unknown"
    return raw


# ---------------------------------------------------------------------------
# Plan markdown parsing
# ---------------------------------------------------------------------------


def resolve_plan_path(plan_id_or_file: str, repo_root: Optional[Path] = None) -> Path:
    """Resolve a plan ID (`PLAN-083`) or file path to an absolute Path.

    Look-up order for PLAN-NNN:
      1. `<repo_root>/.claude/plans/PLAN-NNN-*.md` (glob first match)
      2. `<repo_root>/.claude/plans/PLAN-NNN.md`
    """
    if "/" in plan_id_or_file or plan_id_or_file.endswith(".md"):
        p = Path(plan_id_or_file)
        if not p.is_absolute():
            p = (repo_root or Path.cwd()) / p
        return p

    plan_id = _validate_plan_id(plan_id_or_file)
    root = repo_root or _detect_repo_root()
    plans_dir = root / ".claude" / "plans"
    matches = sorted(plans_dir.glob(f"{plan_id}-*.md"))
    if matches:
        return matches[0]
    direct = plans_dir / f"{plan_id}.md"
    if direct.is_file():
        return direct
    raise FileNotFoundError(f"no plan file matches {plan_id} under {plans_dir}")


def _detect_repo_root() -> Path:
    """Walk up from CWD looking for `.claude/` directory."""
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        return Path(env_root)
    cur = Path.cwd().resolve()
    for candidate in [cur] + list(cur.parents):
        if (candidate / ".claude").is_dir():
            return candidate
    return cur


def parse_plan_estimates(plan_path: Path) -> Dict[str, Any]:
    """Extract sub-agent dispatch tables from a plan markdown.

    Returns::

        {
          "plan_path": "<abs path>",
          "waves": [
            {
              "wave": "0a — Velocity primitives",
              "sub_agents": [
                {"id": "0.1", "tokens_low": 80000, "tokens_high": 80000},
                ...
              ],
              "tokens_low": 510000,
              "tokens_high": 510000,
            },
            ...
          ],
          "total_sub_agents": 22,
          "total_tokens_low": 1500000,
          "total_tokens_high": 2000000,
        }

    Algorithm: scan for `### §X Wave Y` headers. Within each section,
    find tables with an `Est tokens` column header. Each matching row
    yields one sub-agent estimate. Cells that fail `parse_token_cell`
    are skipped (no inflation of estimate from missing data).
    """
    if not plan_path.is_file():
        raise FileNotFoundError(plan_path)
    if plan_path.stat().st_size > _MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"plan file exceeds {_MAX_FILE_SIZE_BYTES}-byte ceiling: {plan_path}"
        )
    text = plan_path.read_text(encoding="utf-8")

    # Split into wave sections. If no wave headers, treat whole doc as one wave.
    wave_positions: List[Tuple[int, str]] = []
    for m in _WAVE_HEADER_RE.finditer(text):
        label = f"§{m.group('num')} Wave {m.group('wave').strip()}"
        wave_positions.append((m.start(), label))

    if not wave_positions:
        wave_sections = [("(whole document)", text)]
    else:
        wave_sections = []
        for idx, (pos, label) in enumerate(wave_positions):
            end = wave_positions[idx + 1][0] if idx + 1 < len(wave_positions) else len(text)
            wave_sections.append((label, text[pos:end]))

    waves_out: List[Dict[str, Any]] = []
    total_sub_agents = 0
    total_low = 0.0
    total_high = 0.0

    for wave_label, section in wave_sections:
        wave_sub_agents = _extract_sub_agents_from_section(section)
        if not wave_sub_agents:
            continue
        wave_low = sum(sa["tokens_low"] for sa in wave_sub_agents)
        wave_high = sum(sa["tokens_high"] for sa in wave_sub_agents)
        waves_out.append({
            "wave": wave_label,
            "sub_agents": wave_sub_agents,
            "tokens_low": int(wave_low),
            "tokens_high": int(wave_high),
        })
        total_sub_agents += len(wave_sub_agents)
        total_low += wave_low
        total_high += wave_high

    return {
        "plan_path": str(plan_path),
        "waves": waves_out,
        "total_sub_agents": total_sub_agents,
        "total_tokens_low": int(total_low),
        "total_tokens_high": int(total_high),
    }


def _extract_sub_agents_from_section(section: str) -> List[Dict[str, Any]]:
    """Find tables with `Est tokens` column + extract sub-agent rows."""
    out: List[Dict[str, Any]] = []
    lines = section.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        if _EST_TOKENS_HEADER_RE.search(line):
            header_cells = [c.strip() for c in line.strip("|").split("|")]
            try:
                est_col = next(
                    idx for idx, c in enumerate(header_cells)
                    if c.lower().startswith("est tokens")
                )
            except StopIteration:
                i += 1
                continue
            # Skip the separator line (|---|---|...).
            j = i + 2
            while j < len(lines):
                row = lines[j]
                if not row.startswith("|"):
                    break
                cells = [c.strip() for c in row.strip("|").split("|")]
                if len(cells) <= est_col:
                    j += 1
                    continue
                sub_id_match = _SUB_AGENT_ID_RE.match(row)
                token_range = parse_token_cell(cells[est_col])
                if token_range is None:
                    j += 1
                    continue
                lo, hi = token_range
                out.append({
                    "id": sub_id_match.group("id") if sub_id_match else cells[0],
                    "tokens_low": int(lo),
                    "tokens_high": int(hi),
                })
                j += 1
            i = j
        else:
            i += 1

    return out


# ---------------------------------------------------------------------------
# Estimation computation
# ---------------------------------------------------------------------------


def compute_estimate(
    parsed: Dict[str, Any],
    table: Dict[str, Any],
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute USD + wallclock estimates from parsed plan + cost table.

    Returns a structured dict ready for JSON serialization or human print.
    """
    model = model or table["default_model"]
    if model not in table["models"]:
        raise ValueError(
            f"unknown model `{model}`; known: {sorted(table['models'].keys())}"
        )
    rates = table["models"][model]
    blended_in = float(table.get("blended_input_share", 0.80))
    blended_out = float(table.get("blended_output_share", 0.20))
    # Allow env override for empirical re-tuning (S82-S105 audit calibration).
    env_blend = os.environ.get("CEO_TOKEN_ESTIMATOR_BLENDED_RATIO")
    if env_blend:
        try:
            blended_in = float(env_blend)
            blended_out = 1.0 - blended_in
        except ValueError:
            pass

    seconds_per_ktok = float(table.get("seconds_per_ktok", 4.0))
    env_secs = os.environ.get("CEO_TOKEN_ESTIMATOR_SECONDS_PER_KTOK")
    if env_secs:
        try:
            seconds_per_ktok = float(env_secs)
        except ValueError:
            pass

    parallel_block = table.get("parallel_ceiling") or {}
    max_parallel = int(parallel_block.get("max_parallel", 6))

    per_wave: List[Dict[str, Any]] = []
    for wave in parsed["waves"]:
        n_sub = len(wave["sub_agents"])
        effective_workers = max(1, min(n_sub, max_parallel))
        # Wallclock_paralelizado: sequential wallclock / fan-out factor.
        seq_seconds_low = (wave["tokens_low"] / 1000.0) * seconds_per_ktok
        seq_seconds_high = (wave["tokens_high"] / 1000.0) * seconds_per_ktok
        par_seconds_low = seq_seconds_low / effective_workers
        par_seconds_high = seq_seconds_high / effective_workers

        usd_low = _usd_for_tokens(wave["tokens_low"], rates, blended_in, blended_out)
        usd_high = _usd_for_tokens(wave["tokens_high"], rates, blended_in, blended_out)

        per_wave.append({
            "wave": wave["wave"],
            "sub_agents": n_sub,
            "tokens_low": wave["tokens_low"],
            "tokens_high": wave["tokens_high"],
            "wallclock_sequential_seconds_low": round(seq_seconds_low, 1),
            "wallclock_sequential_seconds_high": round(seq_seconds_high, 1),
            "wallclock_paralelizado_seconds_low": round(par_seconds_low, 1),
            "wallclock_paralelizado_seconds_high": round(par_seconds_high, 1),
            "effective_workers": effective_workers,
            "usd_low": round(usd_low, 4),
            "usd_high": round(usd_high, 4),
        })

    total_par_low = sum(w["wallclock_paralelizado_seconds_low"] for w in per_wave)
    total_par_high = sum(w["wallclock_paralelizado_seconds_high"] for w in per_wave)
    total_usd_low = sum(w["usd_low"] for w in per_wave)
    total_usd_high = sum(w["usd_high"] for w in per_wave)

    return {
        "plan_path": parsed["plan_path"],
        "model": model,
        "total_sub_agents": parsed["total_sub_agents"],
        "total_tokens_low": parsed["total_tokens_low"],
        "total_tokens_high": parsed["total_tokens_high"],
        "total_usd_low": round(total_usd_low, 4),
        "total_usd_high": round(total_usd_high, 4),
        "total_wallclock_paralelizado_seconds_low": round(total_par_low, 1),
        "total_wallclock_paralelizado_seconds_high": round(total_par_high, 1),
        "max_parallel": max_parallel,
        "seconds_per_ktok": seconds_per_ktok,
        "blended_input_share": blended_in,
        "cost_table_valid_until": (
            table["cost_table_valid_until"].isoformat()
            if isinstance(table["cost_table_valid_until"], date)
            else str(table["cost_table_valid_until"])
        ),
        "per_wave": per_wave,
    }


def _usd_for_tokens(
    total_tokens: float,
    rates: Dict[str, Any],
    share_in: float,
    share_out: float,
) -> float:
    tokens_in = total_tokens * share_in
    tokens_out = total_tokens * share_out
    return (
        (tokens_in / 1_000_000.0) * float(rates["input_per_mtok"])
        + (tokens_out / 1_000_000.0) * float(rates["output_per_mtok"])
    )


# ---------------------------------------------------------------------------
# Audit-log wallclock reporting
# ---------------------------------------------------------------------------


def default_audit_log_path() -> Path:
    """Match ceo-cost.py resolution order (env > project-slug > legacy)."""
    explicit = os.environ.get("CEO_AUDIT_LOG_PATH")
    if explicit:
        return Path(explicit)
    audit_dir_env = os.environ.get("CEO_AUDIT_LOG_DIR")
    if audit_dir_env:
        return Path(audit_dir_env) / "audit-log.jsonl"
    home = Path(os.environ.get("HOME") or str(Path.home()))
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        try:
            abs_path = Path(project_dir).resolve()
            slug = "-" + str(abs_path).lstrip("/").replace("/", "-")
            scoped = home / ".claude" / "projects" / slug / "audit-log.jsonl"
            if scoped.exists() or scoped.parent.is_dir():
                return scoped
        except OSError:
            pass
    return home / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"


def _parse_iso_ts(ts: Any) -> Optional[datetime]:
    if not isinstance(ts, str) or not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def read_wallclock_milestones(
    plan_id: str,
    log_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Read audit log + extract wallclock_milestone events for a plan_id.

    Recognized actions (per PLAN-083 §6 AC7 + §7.5):
      - `wallclock_milestone_started` — plan start sentinel
      - `wallclock_milestone` — per-wave boundary
      - `wallclock_milestone_finished` — plan end (also matches v1.17.0
        tag push event if surfaced via audit)

    Returns::

        {
          "plan_id": "PLAN-083",
          "log_path": "<abs path>",
          "started_at": "<iso>" or None,
          "finished_at": "<iso>" or None,
          "elapsed_seconds": <float> or None,
          "milestones": [
            {"wave": "0a", "ts": "<iso>", "elapsed_since_start_seconds": <float>},
            ...
          ],
          "per_wave": [
            {"wave": "0a", "started_at": "<iso>", "ended_at": "<iso>",
             "elapsed_seconds": <float>},
            ...
          ],
          "warnings": [<str>, ...],
        }

    Missing log → empty milestones + warning; never raises on absent file.
    """
    plan_id = _validate_plan_id(plan_id)
    if log_path is None:
        log_path = default_audit_log_path()

    warnings: List[str] = []
    if not log_path.is_file():
        warnings.append(f"audit log not found at {log_path}")
        return {
            "plan_id": plan_id,
            "log_path": str(log_path),
            "started_at": None,
            "finished_at": None,
            "elapsed_seconds": None,
            "milestones": [],
            "per_wave": [],
            "warnings": warnings,
        }

    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    milestones: List[Tuple[datetime, str]] = []  # (ts, wave_label)

    try:
        with log_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                action = entry.get("action")
                if action not in (
                    "wallclock_milestone",
                    "wallclock_milestone_started",
                    "wallclock_milestone_finished",
                ):
                    continue
                if entry.get("plan_id") != plan_id:
                    continue
                ts = _parse_iso_ts(entry.get("ts"))
                if ts is None:
                    continue
                if action == "wallclock_milestone_started":
                    if started_at is None or ts < started_at:
                        started_at = ts
                elif action == "wallclock_milestone_finished":
                    if finished_at is None or ts > finished_at:
                        finished_at = ts
                else:  # wallclock_milestone
                    wave_raw = entry.get("wave") or entry.get("milestone") or "unknown"
                    wave = _validate_wave_token(str(wave_raw))
                    milestones.append((ts, wave))
    except OSError as exc:
        warnings.append(f"failed to read audit log {log_path}: {exc}")

    milestones.sort(key=lambda pair: pair[0])

    milestone_dicts: List[Dict[str, Any]] = []
    for ts, wave in milestones:
        elapsed = (ts - started_at).total_seconds() if started_at else None
        milestone_dicts.append({
            "wave": wave,
            "ts": ts.isoformat(),
            "elapsed_since_start_seconds": (
                round(elapsed, 1) if elapsed is not None else None
            ),
        })

    # Per-wave intervals: pair consecutive milestones to derive wave duration.
    per_wave: List[Dict[str, Any]] = []
    prev_ts = started_at
    prev_label = "start"
    for ts, wave in milestones:
        if prev_ts is not None:
            per_wave.append({
                "wave": wave,
                "started_at": prev_ts.isoformat(),
                "ended_at": ts.isoformat(),
                "elapsed_seconds": round((ts - prev_ts).total_seconds(), 1),
                "previous_label": prev_label,
            })
        prev_ts = ts
        prev_label = wave

    elapsed_total: Optional[float] = None
    if started_at and finished_at:
        elapsed_total = (finished_at - started_at).total_seconds()
    elif started_at and milestones:
        elapsed_total = (milestones[-1][0] - started_at).total_seconds()

    return {
        "plan_id": plan_id,
        "log_path": str(log_path),
        "started_at": started_at.isoformat() if started_at else None,
        "finished_at": finished_at.isoformat() if finished_at else None,
        "elapsed_seconds": round(elapsed_total, 1) if elapsed_total is not None else None,
        "milestones": milestone_dicts,
        "per_wave": per_wave,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Human + JSON formatting
# ---------------------------------------------------------------------------


def format_estimate_human(est: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"plan: {est['plan_path']}")
    lines.append(f"model: {est['model']}  (cost-table valid until {est['cost_table_valid_until']})")
    lines.append(
        f"total sub-agents: {est['total_sub_agents']}  "
        f"max parallel: {est['max_parallel']}  "
        f"seconds/ktok: {est['seconds_per_ktok']}"
    )
    lines.append(
        f"total tokens: {est['total_tokens_low']:,} - {est['total_tokens_high']:,}"
    )
    lines.append(
        f"total USD: ${est['total_usd_low']:.2f} - ${est['total_usd_high']:.2f}"
    )
    lines.append(
        f"total wallclock paralelizado: "
        f"{_fmt_seconds(est['total_wallclock_paralelizado_seconds_low'])} - "
        f"{_fmt_seconds(est['total_wallclock_paralelizado_seconds_high'])}"
    )
    lines.append("")
    lines.append("per-wave:")
    for w in est["per_wave"]:
        lines.append(
            f"  - {w['wave']}: {w['sub_agents']} sub-agents, "
            f"{w['tokens_low']:,}-{w['tokens_high']:,} tokens, "
            f"${w['usd_low']:.2f}-${w['usd_high']:.2f}, "
            f"par {_fmt_seconds(w['wallclock_paralelizado_seconds_low'])}-"
            f"{_fmt_seconds(w['wallclock_paralelizado_seconds_high'])} "
            f"(effective workers {w['effective_workers']})"
        )
    return "\n".join(lines)


def format_wallclock_human(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"plan: {report['plan_id']}")
    lines.append(f"log:  {report['log_path']}")
    lines.append(f"started_at:  {report['started_at']}")
    lines.append(f"finished_at: {report['finished_at']}")
    if report["elapsed_seconds"] is not None:
        lines.append(f"elapsed: {_fmt_seconds(report['elapsed_seconds'])}")
    else:
        lines.append("elapsed: (no start/finish events)")
    lines.append("")
    lines.append(f"milestones ({len(report['milestones'])}):")
    for m in report["milestones"]:
        elapsed = m.get("elapsed_since_start_seconds")
        elapsed_str = _fmt_seconds(elapsed) if elapsed is not None else "n/a"
        lines.append(f"  {m['ts']}  wave={m['wave']}  +{elapsed_str}")
    if report["per_wave"]:
        lines.append("")
        lines.append("per-wave intervals:")
        for w in report["per_wave"]:
            lines.append(
                f"  - {w.get('previous_label', '?')} -> {w['wave']}: "
                f"{_fmt_seconds(w['elapsed_seconds'])}"
            )
    for warn in report.get("warnings", []):
        lines.append(f"warning: {warn}")
    return "\n".join(lines)


def _fmt_seconds(seconds: Optional[float]) -> str:
    if seconds is None:
        return "n/a"
    seconds = float(seconds)
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.2f}h"


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="token-estimator",
        description=(
            "Pre-task token + wallclock + USD estimator + audit-log-derived "
            "wallclock reporting. PLAN-083 Wave 0a sub-0.2."
        ),
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("estimate", help="Estimate tokens/USD/wallclock for a plan")
    pe.add_argument("plan_id", nargs="?", help="PLAN-NNN identifier")
    pe.add_argument("--input-file", help="Explicit path to a plan-format markdown file")
    pe.add_argument("--model", help="Override default model (e.g. claude-opus-4-8)")
    pe.add_argument("--cost-table", help="Override cost-table.yaml path")
    pe.add_argument("--json", action="store_true", help="Emit machine JSON")

    pw = sub.add_parser("wallclock", help="Report log-derived wallclock per wave + total")
    pw.add_argument("--plan-id", required=True, help="PLAN-NNN identifier")
    pw.add_argument("--log-path", help="Override audit-log.jsonl path")
    pw.add_argument("--json", action="store_true", help="Emit machine JSON")

    pc = sub.add_parser("check-pricing-staleness",
                        help="Exit non-zero if cost-table is past valid_until")
    pc.add_argument("--cost-table", help="Override cost-table.yaml path")
    pc.add_argument("--json", action="store_true", help="Emit machine JSON")

    return p


def cmd_estimate(args: argparse.Namespace) -> int:
    if not args.plan_id and not args.input_file:
        print("error: estimate requires PLAN-NNN or --input-file FILE", file=sys.stderr)
        return 1

    try:
        table_path = Path(args.cost_table) if args.cost_table else None
        table = load_cost_table(table_path)
    except CostTableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    stale, msg = check_cost_table_staleness(table)
    if stale:
        print(f"warning: {msg}", file=sys.stderr)

    if args.input_file:
        plan_path = Path(args.input_file).resolve()
    else:
        try:
            plan_path = resolve_plan_path(args.plan_id)
        except (FileNotFoundError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    try:
        parsed = parse_plan_estimates(plan_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        est = compute_estimate(parsed, table, model=args.model)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(est, indent=2, default=str))
    else:
        print(format_estimate_human(est))
    return 0


def cmd_wallclock(args: argparse.Namespace) -> int:
    try:
        report = read_wallclock_milestones(
            args.plan_id,
            Path(args.log_path) if args.log_path else None,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(format_wallclock_human(report))
    return 0


def cmd_check_pricing_staleness(args: argparse.Namespace) -> int:
    try:
        table_path = Path(args.cost_table) if args.cost_table else None
        table = load_cost_table(table_path)
    except CostTableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    stale, msg = check_cost_table_staleness(table)
    payload = {
        "stale": stale,
        "valid_until": (
            table["cost_table_valid_until"].isoformat()
            if isinstance(table["cost_table_valid_until"], date)
            else str(table["cost_table_valid_until"])
        ),
        "message": msg,
    }
    if args.json:
        print(json.dumps(payload, default=str))
    else:
        if stale:
            print(f"STALE: {msg}")
        else:
            print(f"OK: cost-table valid until {payload['valid_until']}")
    return 1 if stale else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "estimate":
        return cmd_estimate(args)
    if args.cmd == "wallclock":
        return cmd_wallclock(args)
    if args.cmd == "check-pricing-staleness":
        return cmd_check_pricing_staleness(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
