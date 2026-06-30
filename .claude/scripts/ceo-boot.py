#!/usr/bin/env python3
"""ceo-boot.py — PLAN-065 Phase 3 production session-boot autopilot.

Single command at session start that consolidates governance reads + state
digest + recommendations. Per PLAN-065 §4.3 acceptance:

- 15 Tier-S checks dispatched parallel via ThreadPoolExecutor (stdlib)
- Per-check timeout 500 ms; aggregate wall-clock budget 5 s
- ``--short`` defaults to cached mode (≤2 s budget; cache-hit ≤200 ms)
- ``--json`` emits machine-readable digest
- Idempotent (back-to-back identical mod timestamps + transient failures)
- Recommendations engine (rule-based; ≤5 items)
- Audit emit hasattr-guarded — works pre + post canonical ceremony

Stdlib only. Python 3.9+.

Run from repo root:

    python3 .claude/scripts/ceo-boot.py             # full digest
    python3 .claude/scripts/ceo-boot.py --short     # cached top-line
    python3 .claude/scripts/ceo-boot.py --json      # machine output
    python3 .claude/scripts/ceo-boot.py --bench     # bench harness

Slash command: ``/ceo-boot`` (see ``.claude/commands/ceo-boot.md``).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import resource
import subprocess
import sys
import time
import tracemalloc
import unicodedata
from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError as FuturesTimeout,
    as_completed,
)
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]


# PLAN-087 Wave C.4 — module-level plan-glob cache.
# Populated lazily on first call to _get_plan_paths(); subsequent calls
# within the same /ceo-boot subprocess return the cached sorted list.
# Process-scoped (no TTL); each /ceo-boot invocation is a fresh subprocess
# so the cache cannot go stale within a single invocation.
_PLAN_GLOB_CACHE: Optional[List[Path]] = None


def _get_plan_paths() -> List[Path]:
    """Return sorted PLAN-*.md paths, using a module-level cache."""
    global _PLAN_GLOB_CACHE
    if _PLAN_GLOB_CACHE is None:
        _PLAN_GLOB_CACHE = sorted(
            (REPO_ROOT / ".claude" / "plans").glob("PLAN-*.md")
        )
    return _PLAN_GLOB_CACHE


def _reset_plan_glob_cache() -> None:
    """Test helper: clear the cache so a subsequent _get_plan_paths re-globs."""
    global _PLAN_GLOB_CACHE
    _PLAN_GLOB_CACHE = None
AUDIT_LOG_DEFAULT = (
    Path.home() / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"
)
# Legacy single-file cache (kept for backward compat with S82 MVP).
CACHE_FILE_DEFAULT = (
    Path.home() / ".claude" / "projects" / "ceo-orchestration" / "cache" / "ceo-boot-digest.json"
)
# PLAN-065 §4.3.2 real cache directory — keyed by (HEAD + audit-log mtime + size).
# Default lives under project state dir so it is excluded from git via
# ~/.claude/projects layout (parity with audit-log.jsonl). Override via env
# CEO_BOOT_CACHE_DIR for tests.
CACHE_DIR_DEFAULT = (
    Path.home() / ".claude" / "projects" / "ceo-orchestration" / "state" / "ceo-boot-cache"
)
CACHE_TTL_S = 3600.0          # 1 hour
CACHE_FILE_SIZE_CAP_BYTES = 100 * 1024     # 100 KB per cache file
CACHE_DIR_SIZE_CAP_BYTES = 10 * 1024 * 1024  # 10 MB total → LRU eviction
CACHE_HIT_BUDGET_MS = 200.0   # ≤200 ms wall-clock budget for cache hit


def _cache_dir() -> Path:
    """Resolve cache dir at call time so test env overrides are honored."""
    override = os.environ.get("CEO_BOOT_CACHE_DIR")
    if override:
        return Path(override)
    return CACHE_DIR_DEFAULT

# ---- Per-check + aggregate budgets ------------------------------------------
# Default per-check budget. Most checks are file-walks completing in <300ms;
# subprocess-bound checks need longer (overrides below). Aggregate is the hard
# cap for the whole boot.
PER_CHECK_TIMEOUT_S = 1.0
AGGREGATE_TIMEOUT_S = 5.0
MAX_WORKERS = 8

# Per-check overrides — PLAN-082 Codex Item A: governance_validate now
# dispatches `validate-governance.sh --fast --json` (~40 ms typical).
# Previous full-walk path required 2.5 s ceiling; fast profile fits the
# default 1.0 s easily, but we keep a small explicit ceiling for cold-start
# bash + python3 spawn variance on adopter machines.
PER_CHECK_TIMEOUT_OVERRIDES_S: Dict[str, float] = {
    "governance_validate": 2.0,        # fast --json profile (~40-200 ms warm)
    "plans_executing": 1.5,            # full plan tree walk
    "plans_reviewed_pending": 1.5,
    "plans_stranded_executing": 2.0,   # plan walk + git log subprocess
    "plans_draft": 1.5,
    "audit_v3_backlog": 1.5,
    "dispatch_count_24h": 1.5,         # streaming audit-log read
    "skill_unknown_ratio": 1.5,        # streaming audit-log read
    "cost_24h_usd": 1.5,
    "sentinels_pending_gpg": 1.0,
    # PLAN-106 Wave F.3 — EXPLICIT 200 ms override per perf R1 P1 fold.
    # Empirical scan time on 2.3 MB log is ~9-54 ms (200-300k json.loads/sec
    # at ~11.5k events); 200 ms gives ~4-9× headroom. Without explicit
    # override the check would inherit the 1.0 s default and a future
    # log-growth regression wouldn't trip an alarm until 1000 ms.
    "confidence_gate_drift_7d": 0.2,
}

# ---- Sentinel mtime cutoff (Codex S82 P2 fix) ------------------------------
# Sentinels signed before this date are pre-enforcement-era legacy and don't
# require GPG sign now. Without cutoff, scanning all historical produces
# eternal noise (30+ pending every boot).
# 2026-04-22 = first ceremony with mandatory GPG enforcement (S81 ceremony-generator).
SENTINEL_CUTOFF_EPOCH = 1776816000  # 2026-04-22 00:00:00 UTC (Codex S82 P2 fix: was 1776297600 = 2026-04-16, off by 6d)

# ---- Sanitization for recommendations engine inputs (Sec MF-4) ------------
# audit_emit telemetry (`ceo_boot_emitted` / `ceo_boot_check_skipped` actions)
# was DEFERRED to PLAN-065 Phase 7.A v1.12.0 ceremony pre-S82. Phase 2 wire
# (this file): we now CALL the typed wrappers but guard with hasattr() so
# the script keeps working pre-canonical-merge. After ceremony lands the
# kernel ceremony for `_KNOWN_ACTIONS` add + 2 emit functions, this guard
# becomes a no-op false-branch. Field allowlist (Sec MF-3) is enforced
# ON THE EMIT SIDE in `_lib/audit_emit.py` — this caller passes only the
# allowlisted fields and never raises on emit failure.
_HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
try:
    from _lib import injection_patterns as _injection_patterns  # type: ignore
except Exception:  # noqa: BLE001
    _injection_patterns = None

# Fail-soft import: pre-canonical-ceremony, audit_emit module loads but
# the new symbols may not exist yet. Use hasattr() at call site.
try:
    from _lib import audit_emit as _audit_emit  # type: ignore
except Exception:  # noqa: BLE001
    _audit_emit = None  # type: ignore[assignment]

# PLAN-135 W1 S3 — settings/env tamper tripwires. The shared resolver
# `_lib/effective_config.py` (built ONCE for the three consumers S3 / W2 H2
# / W5 O11 per the debate round-1 shared-module rule) captures its trusted
# env surface (`IMPORT_TIME_ENV_SNAPSHOT`: ANTHROPIC_* + *DANGEROUSLY*
# keys) at ITS import time. Importing it HERE — at the top of ceo-boot,
# before any check dispatch — anchors that snapshot as early as the
# `trusted_env` import-time pattern allows for this script
# (check_bash_safety.py precedent: a late-set value injected by a
# sub-agent/subprocess after this anchor cannot dodge the scan).
# Fail-soft: a missing module (pre-W1 ceremony / partial install) degrades
# the `settings_tamper_tripwires` Tier-S check to yellow, never crashes boot.
try:
    from _lib import effective_config as _effective_config  # type: ignore
except Exception:  # noqa: BLE001
    _effective_config = None  # type: ignore[assignment]

# Frozen copy of the import-time env snapshot (defense-in-depth: a later
# mutation of the module attribute cannot alter what the check scans).
try:
    _TAMPER_ENV_SNAPSHOT: Dict[str, str] = (
        dict(_effective_config.IMPORT_TIME_ENV_SNAPSHOT)
        if _effective_config is not None
        else {}
    )
except Exception:  # noqa: BLE001
    _TAMPER_ENV_SNAPSHOT = {}


def _sanitize_for_recs(s: str) -> str:
    """Sanitize a disk-sourced string before recommendation rendering (Sec MF-4).

    Pipeline (deterministic, applied in order):

    1. Coerce non-str → str.
    2. Strip NUL bytes (defense vs. accidental binary in audit-log).
    3. NFKC normalize (PLAN-065 Sec MF-4 — collapse homoglyph escapes:
       fullwidth, ligatures, mathematical alphanumerics).
    4. Length-bound to 200 chars (post-NFKC; NFKC may expand a few code
       points but bound applies to final rendered string).
    5. injection_patterns scan; substitute [REDACTED-INJECTION-PATTERN] on hit.
    6. Strip HTML angle brackets + markdown link URL + backticks (defensive
       belt-and-suspenders if patterns library missed a variant).
    """
    if not isinstance(s, str):
        s = str(s)
    # NUL strip pre-NFKC (NFKC preserves NUL otherwise)
    s = s.replace("\x00", "")
    # NFKC homoglyph collapse — must run BEFORE length bound + scan so that
    # fullwidth/ligature variants are normalized to their ASCII canonicals
    # before the pattern scan (otherwise scanner misses them).
    try:
        s = unicodedata.normalize("NFKC", s)
    except (TypeError, ValueError):
        pass
    s = s[:200]
    if _injection_patterns is not None:
        try:
            # Codex S82 P0 #3 (post-patch v2): scan_harness_mimicry returns
            # ScanResult dataclass (.matched bool), NOT iterable. Previous
            # `if hits:` was always truthy → over-redaction of clean strings.
            # Now check .matched attr; fall back to scan_text alias signature.
            scan_fn = (
                getattr(_injection_patterns, "scan_harness_mimicry", None)
                or getattr(_injection_patterns, "scan_text", None)
            )
            if callable(scan_fn):
                result = scan_fn(s)
                # ScanResult has .matched (bool); legacy iterable returns truthy non-empty
                matched = getattr(result, "matched", None)
                if matched is None:
                    matched = bool(result)  # legacy iterable contract
                if matched:
                    return "[REDACTED-INJECTION-PATTERN]"
        except Exception:  # noqa: BLE001
            pass
    # Strip HTML angle brackets + markdown link syntax + backticks (defensive)
    s = re.sub(r"[<>`]", "", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    return s


# ---- Result dataclass-lite -------------------------------------------------
class CheckResult:
    __slots__ = ("name", "status", "summary", "duration_ms", "detail")

    def __init__(self, name: str, status: str, summary: str, duration_ms: float, detail: Any = None):
        self.name = name
        self.status = status  # green/yellow/red/timeout/error
        self.summary = summary
        self.duration_ms = duration_ms
        self.detail = detail


# ---- 15 Tier-S checks (PoC implementations) -------------------------------

def check_plans_executing() -> Tuple[str, str, Any]:
    plans = _get_plan_paths()
    executing: List[str] = []
    for p in plans:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not m:
            continue
        if re.search(r"^status:\s*executing\s*$", m.group(1), re.MULTILINE):
            executing.append(p.stem)
    status = "yellow" if executing else "green"
    return status, f"{len(executing)} executing", executing


def check_plans_reviewed_pending() -> Tuple[str, str, Any]:
    plans = _get_plan_paths()
    reviewed: List[str] = []
    for p in plans:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not m:
            continue
        if re.search(r"^status:\s*reviewed\s*$", m.group(1), re.MULTILINE):
            reviewed.append(p.stem)
    return ("yellow" if reviewed else "green", f"{len(reviewed)} reviewed", reviewed)


def check_plans_stranded_executing() -> Tuple[str, str, Any]:
    # Subprocess: git log --since=24h --name-only
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "log", "--since=24 hours ago", "--name-only", "--pretty=format:"],
            capture_output=True, text=True, timeout=2.0,
        )
        touched = {line.strip() for line in proc.stdout.splitlines() if line.strip()}
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "yellow", "git unavailable", None
    # Cross-ref against executing plans
    executing_status, _, executing_list = check_plans_executing()
    stranded = [
        plan for plan in executing_list
        if not any(plan in t for t in touched)
    ]
    return ("red" if stranded else "green", f"{len(stranded)} stranded", stranded)


def check_plans_draft() -> Tuple[str, str, Any]:
    plans = _get_plan_paths()
    draft: List[str] = []
    for p in plans:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not m:
            continue
        if re.search(r"^status:\s*draft\s*$", m.group(1), re.MULTILINE):
            draft.append(p.stem)
    return "green", f"{len(draft)} draft", draft


def check_audit_log_freshness() -> Tuple[str, str, Any]:
    """Check audit-log freshness + surface errors sidecar signals.

    F-6.3 (PLAN-113 W7-OPS): also inspects audit-log.errors sidecar so
    that spool_writer FAIL-CLOSED floods become visible at boot time.
    The errors sidecar is resolved via CEO_AUDIT_LOG_ERR env var if set,
    otherwise defaults to audit-log.errors sibling of AUDIT_LOG_DEFAULT.
    Fail-open on any OSError — never blocks boot.
    """
    try:
        st = AUDIT_LOG_DEFAULT.stat()
    except OSError:
        return "yellow", "audit-log missing", None
    age_s = time.time() - st.st_mtime
    age_h = age_s / 3600.0
    size_mb = st.st_size / (1024 * 1024)

    # F-6.3: inspect audit-log.errors sidecar for write failures.
    errors_path_raw = os.environ.get("CEO_AUDIT_LOG_ERR", "")
    if errors_path_raw:
        errors_path = Path(errors_path_raw)
    else:
        errors_path = AUDIT_LOG_DEFAULT.parent / "audit-log.errors"

    errors_present = False
    errors_line_count = 0
    try:
        if errors_path.is_file():
            errors_st = errors_path.stat()
            if errors_st.st_size > 0:
                errors_present = True
                # Count lines without reading the full file into memory.
                with errors_path.open("rb") as ef:
                    errors_line_count = sum(1 for _ in ef)
    except OSError:
        pass  # fail-open

    detail: Dict[str, Any] = {
        "age_hours": age_h,
        "size_mb": size_mb,
        "errors_present": errors_present,
        "errors_line_count": errors_line_count,
    }
    if errors_present:
        status = "yellow"
        summary = (
            f"{age_h:.1f}h old, {size_mb:.1f} MB "
            f"[audit-log.errors: {errors_line_count} lines]"
        )
    else:
        status = "green" if age_h < 24 else "yellow"
        summary = f"{age_h:.1f}h old, {size_mb:.1f} MB"
    return status, summary, detail


def _iter_audit_events_since(hours: float = 24.0):
    """PoC streaming iterator — single-pass discipline."""
    if not AUDIT_LOG_DEFAULT.exists():
        return
    cutoff = time.time() - hours * 3600
    with AUDIT_LOG_DEFAULT.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = ev.get("ts") or ev.get("timestamp")
            if not ts:
                continue
            # Best-effort epoch parse
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if dt.timestamp() < cutoff:
                    continue
            except (ValueError, TypeError):
                continue
            yield ev


def check_dispatch_count_24h() -> Tuple[str, str, Any]:
    n = sum(
        1 for ev in _iter_audit_events_since(24)
        if ev.get("action") == "agent_spawn" and not _is_test_pollution_event(ev)
    )
    return "green", f"{n} dispatches/24h", n


# SHA256 of empty string — fingerprint for harness ghost-events that fire
# PostToolUse on Agent calls with no real payload (ToolSearch probes, canceled
# spawns, harness-internal invocations). S86 follow-up: these polluted the
# skill_unknown_ratio detector by inflating denominator with non-dispatches.
_EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

# S127 follow-up: PLAN-094 / PLAN-094-FOLLOWUP perf benchmarks + drain warmup
# fixtures emit synthetic `action=agent_spawn` events into the canonical
# audit-log via `audit_emit_dispatch.emit_generic` (e.g. wave-d-compound-
# benchmark-full.py:73). They carry a literal `test` discriminant — filter
# them from spawn-attribution detectors so the ratio reflects real CEO
# dispatches. Patch B (test redirection via TestEnvContext) is the proper
# fix; this hygiene patch stops the detector from mis-classifying.
_TEST_DISCRIMINANTS = ("bench", "warmup", "probe")

# S239: governance self-test probes — the `_probe_*` archetypes in the agent
# registry (`_probe_missing_skill`, `_probe_canonical_edit`, `_probe_architect`)
# are synthetic spawns whose entire purpose is to exercise the spawn / canonical
# hooks. They are skill-less by design and do zero real LLM work, yet they emit a
# genuine `action=agent_spawn` row that carries NO `test` discriminant — so the
# `test in _TEST_DISCRIMINANTS` line below misses them. Counting such a probe as a
# governance gap (skill=unknown) or a cache-coverage failure (cache_coverage_bps=0)
# is the exact false-positive class these filters exist to prevent: a single S237
# A3 hook-parity probe pinned BOTH skill_unknown_ratio and cache_discipline_alerted
# to red on an otherwise-idle window. A CLOSED SET of the three registered probe
# archetypes — not a `_probe_` PREFIX match — keeps this advisory detector from
# being side-stepped by a real skill-less dispatch that merely names itself
# `_probe_*` (the prefix would have excluded `_probe_anything`). These are the
# only `_probe_*` archetypes in the agent registry (Codex S239 review, P2).
_PROBE_ARCHETYPES = frozenset({
    "_probe_missing_skill",
    "_probe_canonical_edit",
    "_probe_architect",
})


def _is_test_pollution_event(ev: Dict[str, Any]) -> bool:
    if ev.get("test") in _TEST_DISCRIMINANTS:
        return True
    for key in ("archetype", "subagent_type"):
        if ev.get(key) in _PROBE_ARCHETYPES:
            return True
    return False


def _is_ghost_spawn_event(ev: Dict[str, Any]) -> bool:
    """True iff the agent_spawn event is a harness ghost-event (no real payload).

    All four conditions must hold simultaneously to avoid false-positives on
    legitimate near-empty dispatches: empty desc, no rail attribution, no
    profile marker, and SHA-of-empty-string desc_hash.
    """
    return (
        ev.get("desc_preview") == ""
        and ev.get("rail") is None
        and ev.get("has_profile") is False
        and ev.get("desc_hash") == _EMPTY_SHA256
    )


def check_skill_unknown_ratio() -> Tuple[str, str, Any]:
    """Detect spawns that should have SKILL injection but didn't.

    S94 follow-up: excludes intentionally skill-less archetypes —
    `general-purpose` subagent dispatches via the mitigated rail
    (ADR-082) by design have no SKILL.md anchor. They broker cross-
    LLM gate calls and similar utility work; counting them as FPs
    inflates the ratio to 100% during healthy Codex MCP sessions
    and trains the operator to ignore the channel.

    A spawn counts as "skill missing" ONLY when its `archetype` is
    a custom (non-general-purpose) one AND `skill` is unknown/empty.
    That is the original PLAN-020 ADR-051 governance gap the
    detector was built for.
    """
    total = 0
    unknown = 0
    ghosts_skipped = 0
    skill_less_by_design = 0
    test_pollution_skipped = 0
    for ev in _iter_audit_events_since(24):
        if ev.get("action") != "agent_spawn":
            continue
        if _is_test_pollution_event(ev):
            test_pollution_skipped += 1
            continue
        if _is_ghost_spawn_event(ev):
            ghosts_skipped += 1
            continue
        # Skill-less by design: general-purpose archetype dispatches
        # (mitigated rail per ADR-082) AND built-in subagent types like
        # Explore/Plan/claude-code-guide that have no .claude/agents/<name>.md
        # and so cannot carry a `Loads <skill> skill via reference` phrase
        # (drift-detector contract per S143 lesson). Adding them to
        # _ARCHETYPE_TO_SKILL would violate the contract — exclude here instead.
        # S200: claude/claude-code-guide/statusline-setup are first-party
        # Claude Code built-ins (no .claude/agents anchor); counting them as a
        # governance gap is a false positive — exactly the FP class this filter
        # exists to prevent (else healthy claude-code-guide use trains the
        # operator to ignore the channel).
        _SKILL_LESS_BUILTINS = {
            "general-purpose", "Explore", "Plan",
            "claude", "claude-code-guide", "statusline-setup",
        }
        if (
            ev.get("subagent_type") in _SKILL_LESS_BUILTINS
            and ev.get("archetype") in _SKILL_LESS_BUILTINS
        ):
            skill_less_by_design += 1
            continue
        total += 1
        if ev.get("skill") in (None, "unknown", ""):
            unknown += 1
    if total == 0:
        msg = (
            "no custom-archetype spawns "
            "({s} general-purpose, {g} ghosts, {t} test-pollution)".format(
                s=skill_less_by_design, g=ghosts_skipped, t=test_pollution_skipped,
            )
        )
        return "green", msg, {
            "unknown": 0, "total": 0,
            "ghosts_skipped": ghosts_skipped,
            "skill_less_by_design": skill_less_by_design,
            "test_pollution_skipped": test_pollution_skipped,
        }
    ratio = unknown / total
    status = "red" if ratio > 0.10 else "yellow" if ratio > 0 else "green"
    return status, f"{unknown}/{total} = {ratio:.0%}", {
        "unknown": unknown, "total": total,
        "ghosts_skipped": ghosts_skipped,
        "skill_less_by_design": skill_less_by_design,
        "test_pollution_skipped": test_pollution_skipped,
    }


def check_governance_validate() -> Tuple[str, str, Any]:
    """PLAN-082 Codex Item A: dispatch fast-profile validator.

    Calls `validate-governance.sh --fast --json` (delegates to
    `validate_governance_fast.py`) with a 1.8 s timeout. Parses JSON
    output; `rc != 0` is the red truth signal (NOT `stdout.count("ERROR")`
    — Codex 6th-option catch: the full validator emits `FAIL:` in some
    sections without printing literal "ERROR", which underclassified
    failures as yellow).
    """
    script = REPO_ROOT / ".claude" / "scripts" / "validate-governance.sh"
    if not script.exists():
        return "yellow", "validate-governance missing", None
    try:
        proc = subprocess.run(
            ["bash", str(script), "--fast", "--json"],
            capture_output=True, text=True, timeout=1.8, cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        return "red", "validate timeout (fast)", None
    rc = proc.returncode
    try:
        payload = json.loads(proc.stdout) if proc.stdout else {}
    except (json.JSONDecodeError, ValueError):
        payload = {}
    errors = payload.get("errors", []) if isinstance(payload, dict) else []
    warnings = payload.get("warnings", []) if isinstance(payload, dict) else []
    n_err = len(errors) if isinstance(errors, list) else 0
    n_warn = len(warnings) if isinstance(warnings, list) else 0
    # rc != 0 is the red truth (Codex 6th-option catch).
    if rc != 0:
        status = "red"
        summary = f"fast fail: {n_err} error(s)"
    elif n_warn:
        status = "yellow"
        summary = f"fast pass, {n_warn} warn(s)"
    else:
        status = "green"
        summary = "fast pass"
    return status, summary, {"rc": rc, "errors": n_err, "warnings": n_warn, "profile": "fast"}


def check_hook_live_smoke() -> Tuple[str, str, Any]:
    """PLAN-082 Codex Item D replacement for hook_test_baseline.

    Drops the broken `.claude/cache/hook-tests.json` baseline (never
    populated; required pytest 12 s — not boot-budget feasible). Per
    Codex 6th-option: replace with a cheap live hook smoke — parse
    settings.json + verify referenced hook files exist + executable +
    `py_compile` cleanly. Stdlib only, no pytest.

    Test provenance (last full pytest pass) moves to Tier-A
    (`tier_a_hook_test_baseline_age` — separate check).
    """
    import py_compile

    settings = REPO_ROOT / ".claude" / "settings.json"
    if not settings.exists():
        return "yellow", "settings.json missing", None
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return "red", f"settings.json parse: {exc.__class__.__name__}", None

    hooks_table = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks_table, dict):
        return "yellow", "no hooks table", None

    shim_re = re.compile(r"_python-hook\.sh[\"']?\s+[\"']?([A-Za-z0-9_./-]+\.py)")
    direct_re = re.compile(r"\.claude/hooks/[A-Za-z0-9_./-]+\.py")
    seen: List[str] = []
    seen_set: set = set()
    for hook_list in hooks_table.values():
        if not isinstance(hook_list, list):
            continue
        for entry in hook_list:
            if not isinstance(entry, dict):
                continue
            inner = entry.get("hooks") if isinstance(entry.get("hooks"), list) else []
            for cmd_obj in inner:
                if not isinstance(cmd_obj, dict):
                    continue
                cmd_str = cmd_obj.get("command", "")
                if not isinstance(cmd_str, str):
                    continue
                refs: List[str] = []
                refs.extend(direct_re.findall(cmd_str))
                refs.extend(shim_re.findall(cmd_str))
                for raw in refs:
                    s = re.sub(r"^\$\{?CLAUDE_PROJECT_DIR\}?/", "", raw)
                    if "/" not in s:
                        s = f".claude/hooks/{s}"
                    if s not in seen_set:
                        seen_set.add(s)
                        seen.append(s)

    failures: List[str] = []
    checked = 0
    for rel in seen:
        path = REPO_ROOT / rel
        if not path.is_file():
            failures.append(f"missing:{rel}")
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except (py_compile.PyCompileError, OSError):
            failures.append(f"compile_fail:{rel}")
            continue
        checked += 1

    if failures:
        return "red", f"{len(failures)}/{len(seen)} hook(s) broken", {
            "failures": failures[:10],  # bound for sanitization
            "checked": checked,
            "total": len(seen),
        }
    if checked == 0:
        return "yellow", "no hooks discovered", {"checked": 0, "total": 0}
    return "green", f"{checked} hook(s) smoke-pass", {"checked": checked, "total": len(seen)}


# Backward-compat alias — some external callers / tests may still import the
# old name. Live smoke is a strict improvement (no cache dependency, faster).
check_hook_test_baseline = check_hook_live_smoke


def check_audit_v3_backlog() -> Tuple[str, str, Any]:
    # PoC: count plans with audit_v3_* tags still open
    plans = _get_plan_paths()
    backlog: List[str] = []
    for p in plans:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not m:
            continue
        front = m.group(1)
        if "audit_v3" in front and not re.search(r"^status:\s*done\s*$", front, re.MULTILINE):
            backlog.append(p.stem)
    return ("yellow" if backlog else "green", f"{len(backlog)} open", backlog)


def check_sentinels_pending_gpg() -> Tuple[str, str, Any]:
    """Count GPG-pending sentinels post-cutoff.

    Codex S82 P2 fix: previous impl scanned ALL historical sentinels with no
    date cutoff → 30+ pending entries every boot from PLAN-030/031/039 round-1
    pre-enforcement era. Now applies SENTINEL_CUTOFF_EPOCH (2026-04-22) to
    skip legacy. Also Codex S82 P2 sorted glob for CR-N7 stable ordering.
    """
    pending: List[str] = []
    plans_dir = REPO_ROOT / ".claude" / "plans"
    for approved in sorted(plans_dir.glob("PLAN-*/architect/round-*/approved.md")):
        try:
            mtime = approved.stat().st_mtime
        except OSError:
            continue
        if mtime < SENTINEL_CUTOFF_EPOCH:
            continue  # pre-enforcement legacy
        if not (approved.parent / "approved.md.asc").exists():
            pending.append(str(approved.relative_to(REPO_ROOT)))
    return ("yellow" if pending else "green", f"{len(pending)} pending", pending)


def check_rc_hold_aged() -> Tuple[str, str, Any]:
    release_md = REPO_ROOT / "RELEASE.md"
    rc_hold = REPO_ROOT / "RC-HOLD.md"
    target = release_md if release_md.exists() else rc_hold if rc_hold.exists() else None
    if target is None:
        return "green", "no rc-hold doc", None
    text = target.read_text(encoding="utf-8", errors="replace")
    # PoC: count rc-hold-waiver entries (real impl would parse dates)
    n = len(re.findall(r"rc-hold-waiver", text))
    return ("yellow" if n else "green", f"{n} rc-hold-waiver entries", n)


# E7-F5 (PLAN-120-FOLLOWUP): real daily-USD burn-rate thresholds.
# Previously this check returned "green" unconditionally (Potemkin stub) — it
# tallied cost_usd over 24h but never compared it against a budget, so a
# runaway burn never surfaced at boot. We now apply a yellow/red ceiling.
# Both bounds are env-overridable (adopter sessions differ wildly in cost);
# defaults are calibrated to a typical heavy CEO session. Fail-OPEN: any
# parse/lookup error degrades to the default ceiling, never raises, and an
# empty/zero-cost log stays green (the steady-state).
_COST_YELLOW_USD_DEFAULT = 50.0
_COST_RED_USD_DEFAULT = 150.0


def _cost_threshold(env_var: str, default: float) -> float:
    """Read a positive float ceiling from env; fall back to default fail-open."""
    raw = os.environ.get(env_var, "")
    if not raw:
        return default
    try:
        val = float(raw.strip())
    except (TypeError, ValueError):
        return default
    # Reject non-finite / non-positive overrides (would defeat the gate).
    if val != val or val == float("inf") or val <= 0:
        return default
    return val


def check_cost_24h_usd() -> Tuple[str, str, Any]:
    """Sum cost_usd over 24h and gate against env-overridable USD ceilings.

    yellow at CEO_BOOT_COST_YELLOW_USD (default $50/24h); red at
    CEO_BOOT_COST_RED_USD (default $150/24h). Fail-open: no cost datapoints
    or unreadable log => green. Thresholds are advisory burn-rate alerts
    (ADR-064 50/80/95% doctrine), never a hard block.
    """
    total = 0.0
    samples = 0
    for ev in _iter_audit_events_since(24):
        c = ev.get("cost_usd")
        if isinstance(c, (int, float)) and not isinstance(c, bool):
            total += float(c)
            samples += 1
    yellow = _cost_threshold("CEO_BOOT_COST_YELLOW_USD", _COST_YELLOW_USD_DEFAULT)
    red = _cost_threshold("CEO_BOOT_COST_RED_USD", _COST_RED_USD_DEFAULT)
    # Guard against an inverted override (yellow >= red): keep red as the
    # higher bound so the status ladder stays monotonic.
    if yellow >= red:
        yellow = min(yellow, red)
    if samples == 0:
        status = "green"
    elif total >= red:
        status = "red"
    elif total >= yellow:
        status = "yellow"
    else:
        status = "green"
    return status, f"${total:.2f}/24h", {
        "total_usd": round(total, 4),
        "samples": samples,
        "yellow_usd": yellow,
        "red_usd": red,
    }


def check_active_plan_burn_ratio() -> Tuple[str, str, Any]:
    # PoC: find first executing plan, parse budget_tokens, sum tokens from log
    _, _, executing = check_plans_executing()
    if not executing:
        return "green", "no active plan", None
    plan_id = executing[0].split("-")[0] + "-" + executing[0].split("-")[1] if executing else None
    if not plan_id:
        return "green", "no plan id", None
    plan_path = REPO_ROOT / ".claude" / "plans" / f"{executing[0]}.md"
    try:
        text = plan_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "yellow", "plan unreadable", None
    m = re.search(r"^budget_tokens:\s*(.+?)$", text, re.MULTILINE)
    if not m:
        return "yellow", "no budget_tokens", None
    return "green", f"budget {m.group(1).strip()}", {"plan": plan_id, "budget_raw": m.group(1).strip()}


def check_adrs_stale_proposed() -> Tuple[str, str, Any]:
    adrs = sorted((REPO_ROOT / ".claude" / "adr").glob("ADR-*.md"))
    proposed_old: List[str] = []
    now = time.time()
    for a in adrs:
        try:
            text = a.read_text(encoding="utf-8", errors="replace")
            mtime = a.stat().st_mtime
        except OSError:
            continue
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not m:
            continue
        if re.search(r"^status:\s*proposed\s*$", m.group(1), re.MULTILINE):
            age_d = (now - mtime) / 86400
            if age_d > 30:
                proposed_old.append(a.stem)
    return ("yellow" if proposed_old else "green", f"{len(proposed_old)} proposed >30d", proposed_old)


# ---- 10 Tier-A checks (--verbose mode; PLAN-065 §4.3.3) ------------------
# Selection rationale (each picked for high signal-to-cost ratio + non-overlap
# with Tier-S; see PLAN-065 §4.3.3):
#   tier_a_debate_transcripts     — debate hygiene (Round-1 archetype output)
#   tier_a_lessons_30d            — lesson velocity (memory growth pulse)
#   tier_a_spec_version_drift     — VERSION ↔ SPEC/v*/VERSION mismatch
#   tier_a_npm_version_match      — package.json vs VERSION mismatch
#   tier_a_waivers_count          — waivers/*.md aggregate (rc-hold + cosmetic)
#   tier_a_adrs_recent_status     — ADR-098..104 reservation slots tracking
#   tier_a_cache_hit_rate_24h     — ceo-boot-emitted cache_hit ratio (self-loop)
#   tier_a_hook_test_baseline_age — last-cached hook-test baseline age (S81 cache)
#   tier_a_sentinel_signers_tracked — .claude/state/sentinel-signers.txt git-tracked?
#   tier_a_gitignore_state_excluded — .gitignore covers state/ dir?


def check_tier_a_debate_transcripts() -> Tuple[str, str, Any]:
    """Count debate transcripts produced in last 24h (forensic hygiene)."""
    debate_root = REPO_ROOT / ".claude" / "plans"
    n = 0
    cutoff = time.time() - 86400
    for transcript in debate_root.rglob("debate/*/round-*.md"):
        try:
            if transcript.stat().st_mtime >= cutoff:
                n += 1
        except OSError:
            continue
    # Status green regardless — informational. Yellow if zero AND there is an
    # executing plan (suggests work without debate trail).
    _, _, executing = check_plans_executing()
    if n == 0 and executing:
        return "yellow", f"0 transcripts/24h ({len(executing)} executing)", n
    return "green", f"{n} transcripts/24h", n


def check_tier_a_lessons_30d() -> Tuple[str, str, Any]:
    """Count lessons added in memory dir over 30d (informational)."""
    # Derive the Claude Code project slug from the project dir (absolute path
    # with "/" -> "-") instead of hard-coding the meta-repo's slug, so this
    # resolves correctly in any install. (Previously hard-coded the Owner's
    # absolute home path, which broke for every other install and tripped the
    # contamination guard.)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    slug = str(Path(project_dir).resolve()).replace("/", "-")
    mem_dir = Path.home() / ".claude" / "projects" / slug / "memory"
    if not mem_dir.exists():
        return "green", "memory dir absent", 0
    cutoff = time.time() - 30 * 86400
    n = 0
    for f in mem_dir.glob("*.md"):
        try:
            if f.stat().st_mtime >= cutoff:
                n += 1
        except OSError:
            continue
    return "green", f"{n} lessons/30d", n


def check_tier_a_spec_version_drift() -> Tuple[str, str, Any]:
    """VERSION file vs latest SPEC/v*/VERSION agreement (informational)."""
    version_file = REPO_ROOT / "VERSION"
    if not version_file.exists():
        return "yellow", "VERSION missing", None
    try:
        repo_v = version_file.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return "yellow", "VERSION unreadable", None
    spec_root = REPO_ROOT / "SPEC"
    if not spec_root.exists():
        return "green", f"repo {repo_v}, no SPEC dir", repo_v
    spec_versions = sorted(p.name for p in spec_root.iterdir() if p.is_dir() and p.name.startswith("v"))
    if not spec_versions:
        return "green", f"repo {repo_v}, no SPEC versions", repo_v
    return "green", f"repo {repo_v}, spec {','.join(spec_versions[-2:])}", {
        "repo_version": repo_v, "spec_versions": spec_versions,
    }


def check_tier_a_npm_version_match() -> Tuple[str, str, Any]:
    """package.json version vs VERSION file (Codex S79 P1 finding)."""
    version_file = REPO_ROOT / "VERSION"
    pkg_file = REPO_ROOT / "package.json"
    if not version_file.exists() or not pkg_file.exists():
        return "green", "no npm artifacts", None
    try:
        repo_v = version_file.read_text(encoding="utf-8", errors="replace").strip()
        pkg = json.loads(pkg_file.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return "yellow", "parse error", None
    pkg_v = pkg.get("version", "")
    if pkg_v == repo_v:
        return "green", f"match {repo_v}", {"version": repo_v}
    return "red", f"drift: VERSION={repo_v} package.json={pkg_v}", {
        "repo_version": repo_v, "pkg_version": pkg_v,
    }


def check_tier_a_waivers_count() -> Tuple[str, str, Any]:
    """Aggregate waivers/*.md count (rc-hold + cosmetic + audit)."""
    waivers_dir = REPO_ROOT / "waivers"
    if not waivers_dir.exists():
        return "green", "no waivers dir", 0
    waivers = list(waivers_dir.glob("*.md"))
    n = len(waivers)
    status = "yellow" if n > 5 else "green"
    return status, f"{n} waivers", n


def check_tier_a_adrs_recent_status() -> Tuple[str, str, Any]:
    """ADR-098..104 status tracker (PLAN-065 reserved slots — drift detector)."""
    adr_dir = REPO_ROOT / ".claude" / "adr"
    statuses: Dict[str, str] = {}
    for adr_num in range(98, 105):
        matches = list(adr_dir.glob(f"ADR-{adr_num:03d}-*.md"))
        if not matches:
            statuses[f"ADR-{adr_num:03d}"] = "missing"
            continue
        try:
            text = matches[0].read_text(encoding="utf-8", errors="replace")
        except OSError:
            statuses[f"ADR-{adr_num:03d}"] = "unreadable"
            continue
        m = re.search(r"^status:\s*([a-zA-Z\-]+)\s*$", text, re.MULTILINE)
        statuses[f"ADR-{adr_num:03d}"] = m.group(1).lower() if m else "unknown"
    accepted = sum(1 for v in statuses.values() if v == "accepted")
    return "green", f"{accepted}/{len(statuses)} accepted", statuses


def check_tier_a_cache_hit_rate_24h() -> Tuple[str, str, Any]:
    """ceo_boot_emitted cache_hit ratio over 24h (self-observation)."""
    total = 0
    hits = 0
    for ev in _iter_audit_events_since(24):
        if ev.get("action") != "ceo_boot_emitted":
            continue
        total += 1
        if ev.get("cache_hit"):
            hits += 1
    if total == 0:
        return "green", "no boots/24h", 0
    ratio = hits / total
    return "green", f"{hits}/{total} = {ratio:.0%} cache-hit", {
        "hits": hits, "total": total, "ratio": ratio,
    }


def check_tier_a_hook_test_baseline_age() -> Tuple[str, str, Any]:
    """Age of cached hook-test baseline file (S81 cache convention)."""
    cache = REPO_ROOT / ".claude" / "cache" / "hook-tests.json"
    if not cache.exists():
        return "yellow", "no cached baseline", None
    try:
        st = cache.stat()
    except OSError:
        return "yellow", "stat failed", None
    age_h = (time.time() - st.st_mtime) / 3600.0
    status = "green" if age_h < 168 else "yellow"  # 7d window
    return status, f"{age_h:.1f}h old", {"age_hours": age_h}


def check_tier_a_sentinel_signers_tracked() -> Tuple[str, str, Any]:
    """sentinel-signers.txt presence + git-tracked status."""
    candidates = [
        REPO_ROOT / ".claude" / "state" / "sentinel-signers.txt",
        REPO_ROOT / "sentinel-signers.txt",
    ]
    found: Optional[Path] = None
    for c in candidates:
        if c.exists():
            found = c
            break
    if found is None:
        return "yellow", "sentinel-signers.txt missing", None
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch", str(found.relative_to(REPO_ROOT))],
            capture_output=True, text=True, timeout=1.5,
        )
        tracked = (proc.returncode == 0)
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        return "yellow", "git unavailable", None
    return ("green" if tracked else "yellow",
            f"present, tracked={tracked}",
            {"path": str(found.relative_to(REPO_ROOT)), "tracked": tracked})


def check_tier_a_gitignore_state_excluded() -> Tuple[str, str, Any]:
    """.gitignore covers state/ dir (LRU cache + sentinels safety)."""
    gi = REPO_ROOT / ".gitignore"
    if not gi.exists():
        return "yellow", ".gitignore missing", None
    try:
        text = gi.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "yellow", ".gitignore unreadable", None
    # Match leading patterns: state/, .claude/state/, /state, etc.
    has_state = bool(re.search(r"(?m)^\s*\.?/?(?:\.claude/)?state/", text))
    return ("green" if has_state else "yellow",
            f"state/ excluded={has_state}",
            {"covered": has_state})


# ---- Registry --------------------------------------------------------------


def check_tier_policy_misrouting_24h() -> Tuple[str, str, Any]:
    """16th Tier-S check — delegates to standalone hook module (PLAN-091 W2.1).

    Lazy-imports ``.claude/hooks/check_tier_policy_misrouting_24h.py`` so
    that the standalone module can also be invoked as a CLI smoke-test
    (``python3 .claude/hooks/check_tier_policy_misrouting_24h.py``).
    Any import-time failure surfaces as a `yellow` status (fail-soft
    Tier-S contract); the dispatcher's outer try/except still wraps the
    inner call for additional defense-in-depth.
    """
    try:
        hooks_dir = REPO_ROOT / ".claude" / "hooks"
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from check_tier_policy_misrouting_24h import (  # type: ignore
            check_tier_policy_misrouting_24h as _impl,
        )
        return _impl()
    except Exception as exc:  # noqa: BLE001 (Tier-S fail-soft floor)
        return "yellow", f"tier_policy_misrouting import error: {exc}", None


def check_cache_discipline_alerted() -> Tuple[str, str, Any]:
    """17th Tier-S check — prompt-cache coverage detection (PLAN-093 Wave C.2).

    Surfaces ``cache_discipline_alerted`` when prompt-cache coverage falls
    below 0.7 over the last 24h of audit-log events. Detection is heuristic:
    any audit row (``agent_spawn`` action) carrying a ``cache_coverage_bps``
    numeric field is averaged; rows without the field are ignored. Absent
    any datapoints, status is green with a "no data" summary (fail-soft
    Tier-S contract).

    Field alignment (F-5-5.1-0624274e fix): audit_log.py emits the
    cache-coverage metric derived from usage_metadata cache_read /
    (cache_read + cache_creation + uncached); older code read the
    non-existent ``cache_hit_rate`` field, causing the gate to always
    return green/"no data". This fix aligns the reader to the emitted field.
    PLAN-118 WS-E (S181): the emitted field is now ``cache_coverage_bps``
    (integer basis-points); this reader reads it (÷10000) and falls back to
    the legacy ``cache_coverage`` float for events emitted before the fix.

    Emits ``cache_discipline_alerted`` via ``emit_generic`` on yellow/red
    so downstream analytics can correlate with /ceo-boot runs. Action
    name is registered at ``audit_emit.py:440`` (PLAN-088 canonical).
    """
    threshold = 0.70
    try:
        rates: List[float] = []
        for ev in _iter_audit_events_since(hours=24.0):
            # S239: skip synthetic governance-probe / benchmark spawns — they
            # carry cache_coverage_bps=0 by construction (no real cached LLM
            # call), so a probe-only 24h window would pin this gate to red (FP).
            if _is_test_pollution_event(ev):
                continue
            # PLAN-118 WS-E (S181): primary field is now ``cache_coverage_bps``
            # (integer basis-points, ratio × 10000) — the legacy float
            # ``cache_coverage`` was dropped because it broke the HMAC chain.
            # Read bps first, fall back to the legacy float for events emitted
            # before the fix (the 24h window straddles the transition; without
            # the fallback this Tier-S gate would go silently dead again —
            # the exact F-5-5.1-0624274e failure mode this check exists to avoid).
            v_bps = ev.get("cache_coverage_bps")
            if isinstance(v_bps, int) and not isinstance(v_bps, bool) and 0 <= v_bps <= 10000:
                rates.append(v_bps / 10000.0)
                continue
            # F-5-5.1-0624274e: legacy float field (pre-PLAN-118 events).
            v = ev.get("cache_coverage")
            if isinstance(v, (int, float)) and not isinstance(v, bool) and 0.0 <= float(v) <= 1.0:
                rates.append(float(v))
        if not rates:
            return "green", "no cache_coverage datapoints", {"samples": 0}
        avg = sum(rates) / len(rates)
        if avg < threshold:
            try:
                if _audit_emit is not None and hasattr(
                    _audit_emit, "emit_cache_discipline_alerted"
                ):
                    _audit_emit.emit_cache_discipline_alerted(
                        hit_rate_basis_points=max(
                            0, min(1000, int(round(avg * 1000)))
                        ),
                        floor_basis_points=max(
                            0, min(1000, int(round(threshold * 1000)))
                        ),
                        session_count_24h=len(rates),
                        below_floor=True,
                        opted_out=False,
                    )
            except Exception:  # noqa: BLE001 (Tier-S fail-soft)
                pass
            return "red", f"cache_coverage {avg:.2f} < {threshold}", {
                "avg_rate": avg,
                "samples": len(rates),
            }
        return "green", f"cache_coverage {avg:.2f} ok", {
            "avg_rate": avg,
            "samples": len(rates),
        }
    except Exception as exc:  # noqa: BLE001 (Tier-S fail-soft)
        return "yellow", f"cache_discipline_alerted error: {exc}", None


# PLAN-093 Wave C.5/C.6 canonical persona × task matrix.
#
# S127 cadence-amendment (Codex R2 thread `019e33a3` AMEND verdict
# `PHASE-1+2-WITH-(c)`): the 4×4 matrix is demoted from gate-eligible to
# permanent observability. RED authority moves to a future event-driven
# demand ledger (`PLAN-104-persona-demand-ledger`); see
# `PLAN-093-FOLLOWUP-cadence-amendment.md` for the full doctrine record.
_VETO_FLOOR_PERSONAS = (
    "code-reviewer", "security-engineer", "qa-architect",
    "threat-detection-engineer",
)
_PERSONA_TASK_TYPES = ("review", "vet", "test", "detect")
_VETO_FLOOR_PERSONAS_LOWER = frozenset(p.lower() for p in _VETO_FLOOR_PERSONAS)

# PLAN-112-FOLLOWUP-persona-routing-wire W4 — F-5.4-tasktype-pollution.
# `_score_persona_coverage` previously counted task_type from ANY audit
# event whose archetype matched a VETO-floor persona. Unrelated emitters
# (notably `model_routing_advised`, which carries archetype + a bogus
# task_type like `frontmatter`/`M`) inflated the denominator + skewed cells.
# Restrict contributing events to the GENUINE persona-dispatch actions:
#   - `persona_coverage_synthesized` (SPEC/v1/audit-log.schema.md:319 —
#     carries `archetype` + `task_type`, the only fields the scorer reads)
#   - `persona_demand_*` (the persona-demand ledger family; PLAN-104)
# NOTE: `persona_dispatch` does NOT exist and must not be referenced.
_PERSONA_DISPATCH_ACTION_PREFIXES = ("persona_demand_",)
_PERSONA_DISPATCH_ACTIONS = frozenset({"persona_coverage_synthesized"})


def _is_persona_dispatch_event(ev: Dict[str, Any]) -> bool:
    """True iff `ev` is a genuine persona-dispatch event (F-5.4 filter).

    Defensive: a missing/non-str `action` -> False (excluded).
    """
    action = ev.get("action")
    if not isinstance(action, str):
        return False
    if action in _PERSONA_DISPATCH_ACTIONS:
        return True
    return any(action.startswith(p) for p in _PERSONA_DISPATCH_ACTION_PREFIXES)


def _normalize_persona_role(ev: Dict[str, Any]) -> str:
    """Case-folded canonical role extracted from any audit_log emission surface.

    PLAN-093 Wave C.5 originally read only ``archetype`` / ``persona``. Codex
    R2 thread `019e33a3` AMEND #4: audit-log events emitted from
    ``audit_log.py`` carry the role on ``subagent_type`` (canonical) and
    ``dispatch_archetype_hint`` (resolved-from-prompt) — narrow read missed
    those surfaces. First non-empty match wins, case-folded.
    """
    for field in ("archetype", "persona", "subagent_type",
                  "dispatch_archetype_hint"):
        val = ev.get(field)
        if isinstance(val, str) and val.strip():
            return val.strip().lower()
    return ""


def _score_persona_coverage(hours: float) -> Dict[str, int]:
    """Compute 4×4 persona × task coverage over a rolling audit-log window.

    Returns canonical metrics dict suitable for both the 24h session-smoke
    check and the 7d trend check. Phase 1 (S127): `eligible_demand_events`
    is unconditionally 0 — that signal is produced by the demand ledger
    scheduled for Phase 2 (`PLAN-104-persona-demand-ledger`).
    """
    canonical_by_lower = {p.lower(): p for p in _VETO_FLOOR_PERSONAS}
    seen: Dict[str, set] = {p: set() for p in _VETO_FLOOR_PERSONAS}
    events_with_target = 0
    for ev in _iter_audit_events_since(hours=hours):
        # PLAN-112-FOLLOWUP-persona-routing-wire W4 — F-5.4 task_type
        # pollution fix. Only genuine persona-dispatch events contribute to
        # coverage; unrelated emitters carrying a VETO-floor archetype +
        # a bogus task_type are excluded entirely.
        if not _is_persona_dispatch_event(ev):
            continue
        role = _normalize_persona_role(ev)
        if role not in _VETO_FLOOR_PERSONAS_LOWER:
            continue
        events_with_target += 1
        task_type = ev.get("task_type") or ev.get("phase") or ""
        if not isinstance(task_type, str) or not task_type:
            continue
        task_lower = task_type.lower()
        for t in _PERSONA_TASK_TYPES:
            if t in task_lower:
                seen[canonical_by_lower[role]].add(t)
                break
    cells_covered = sum(len(v) for v in seen.values())
    total_cells = len(_VETO_FLOOR_PERSONAS) * len(_PERSONA_TASK_TYPES)
    score_pct = (cells_covered / total_cells * 100.0) if total_cells else 0.0
    return {
        "cells_covered": cells_covered,
        "total_cells": total_cells,
        "events_with_target_archetype": events_with_target,
        "score_x100": int(round(score_pct * 100)),
    }


def _persona_coverage_status(
    metrics: Dict[str, int],
    *,
    window_hours: int,
) -> Tuple[str, str]:
    """Decide status + summary for a persona-coverage check window.

    Phase 1 (S127) semantic — pure observability, never red:

      ``events_with_target_archetype == 0`` → green "no VETO-floor
      dispatches in <h>h" (mirrors demand-driven empty-green pattern of
      the other 17 Tier-S checks — Codex R2 AMEND #1).

      ``events_with_target_archetype > 0`` → yellow "M/16 cells covered
      in <h>h" (matrix demoted to max-yellow forever per Codex R2 AMEND
      #2 — RED authority reserved for Phase 2 demand-driven gate).
    """
    events_target = metrics["events_with_target_archetype"]
    cells = metrics["cells_covered"]
    total = metrics["total_cells"]
    if events_target == 0:
        return "green", f"no VETO-floor dispatches in {window_hours}h"
    return "yellow", f"{cells}/{total} cells covered in {window_hours}h"


def _emit_persona_coverage(
    metrics: Dict[str, int],
    *,
    window_hours: int,
) -> None:
    """Emit ``ceo_boot_persona_coverage_score`` audit event (shared by 24h+7d).

    S127 Phase 1 scope-(b) — emits only the 3 fields already in the kernel
    allowlist (`score_x100`, `cells_covered`, `total_cells`). The new fields
    (`window_hours`, `events_with_target_archetype`, `eligible_demand_events`)
    surface in the /ceo-boot result dict + summary text but are NOT persisted
    in the audit-log under Phase 1. Deferring the
    ``_CEO_BOOT_PERSONA_COVERAGE_ALLOWLIST`` kernel amendment to an Owner
    ceremony — bundle with the Phase 2 demand-ledger ship (which needs more
    kernel surface anyway), avoiding two separate kernel-override events.

    The `window_hours` value is consumed by `_persona_coverage_status` for
    the summary string; downstream audit-log consumers reconstructing
    cadence from emitted events would need to infer it (or wait for
    Phase 2 ship).
    """
    del window_hours  # See docstring; not emitted under Phase 1 scope-(b).
    try:
        if _audit_emit is not None and hasattr(_audit_emit, "emit_generic"):
            # score_x100 is integer basis-points (0-10000); floats break
            # canonical JSON HMAC chain — Codex S123 iter-2 P1.
            _audit_emit.emit_generic(
                "ceo_boot_persona_coverage_score",
                score_x100=metrics["score_x100"],
                cells_covered=metrics["cells_covered"],
                total_cells=metrics["total_cells"],
            )
    except Exception:  # noqa: BLE001 (Tier-S fail-soft)
        pass


def check_ceo_boot_persona_coverage_score() -> Tuple[str, str, Any]:
    """18th Tier-S check — persona × task coverage at 24h cadence (session-smoke).

    Originally PLAN-093 Wave C.5/C.6 AC10 — sourced 24h of audit-log and
    scored a 4×4 matrix with `<50% red` thresholds. S127 cadence-amendment
    (Codex R2 thread `019e33a3` AMEND `PHASE-1+2-WITH-(c)`): demoted to
    permanent observability. Never red, never gate-failing. RED authority
    moves to `PLAN-104-persona-demand-ledger` (Phase 2 event-driven gate).

    Companion: `check_persona_atrophy_7d` at 168h cadence for trend signal.

    Emits ``ceo_boot_persona_coverage_score`` with `window_hours=24` and
    `eligible_demand_events=0` (PLAN-104 demand ledger live; observability-only here per AC4).
    """
    try:
        metrics = _score_persona_coverage(hours=24.0)
    except Exception as exc:  # noqa: BLE001 (Tier-S fail-soft)
        return "yellow", f"persona_coverage error: {exc}", None
    status, summary = _persona_coverage_status(metrics, window_hours=24)
    _emit_persona_coverage(metrics, window_hours=24)
    return status, summary, {
        **metrics,
        "window_hours": 24,
        "eligible_demand_events": 0,
    }


def check_persona_atrophy_7d() -> Tuple[str, str, Any]:
    """19th Tier-S check — demand-normalized persona-atrophy at 168h.

    PLAN-104 Wave D activated the demand-driven RED branch (S134 Codex R2
    thread `019e37e3` ACCEPT). Set-algebra in
    `persona_demand_resolver.atrophy_7d_status` (Codex iter-1 P0 #2 +
    iter-2 P1 #1 folds — adds defense-in-depth effective_unmet
    computation inline):

      satisfied         = opened & matched
      unmet_recorded    = (opened & unmet) - matched - waived
      effective_unmet   = opened where opened_ts + 24h < now AND
                          no terminal AND no in-window dispatch-match
      unmet_total       = unmet_recorded | (effective_unmet - waived)
      waived            = (opened & waived) - matched
      still_open        = opened where window NOT expired and no terminal
      eligible_settled  = satisfied | unmet_total | waived

      not opened           -> green "no eligible persona demand in 168h"
      not eligible_settled -> green "<N> demand(s) still inside window"
      not unmet_total      -> green "<S>/<E> demands matched (<W> waived)"
      else                 -> red   "<U> persona demand(s) unmet in 168h ..."

    Side-effect: this check runs scan + waive-emit + resolve before
    computing status (Codex iter-1 P0 #1). Ordering per Codex iter-2
    P1 #2: scan -> emit_opened -> emit_waives_for_scanned -> resolve
    -> emit_resolutions (waive precedes unmet emit).

    Kill-switch CEO_PERSONA_DEMAND_LEDGER_DISABLED=1 reverts to
    pre-PLAN-104 observability-only semantic (max-yellow). The 18th check
    `check_ceo_boot_persona_coverage_score` stays observability-only
    forever per S127 AMEND option-(c).
    """
    if os.environ.get("CEO_PERSONA_DEMAND_LEDGER_DISABLED") == "1":
        try:
            metrics = _score_persona_coverage(hours=168.0)
        except Exception as exc:  # noqa: BLE001
            return "yellow", f"persona_atrophy_7d error: {exc}", None
        status, summary = _persona_coverage_status(metrics, window_hours=168)
        _emit_persona_coverage(metrics, window_hours=168)
        return status, summary, {
            **metrics,
            "window_hours": 168,
            "eligible_demand_events": 0,
        }

    try:
        import importlib.util
        scripts_dir = Path(__file__).resolve().parent
        spec_path = scripts_dir / "persona_demand_resolver.py"
        spec = importlib.util.spec_from_file_location(
            "persona_demand_resolver", spec_path,
        )
        if spec is None or spec.loader is None:
            raise ImportError("resolver spec load failed")
        resolver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(resolver)
        scan_spec = importlib.util.spec_from_file_location(
            "persona_demand_scan", scripts_dir / "persona_demand_scan.py",
        )
        if scan_spec is None or scan_spec.loader is None:
            raise ImportError("scan spec load failed")
        scanner = importlib.util.module_from_spec(scan_spec)
        scan_spec.loader.exec_module(scanner)
    except Exception as exc:  # noqa: BLE001
        return "yellow", f"persona_atrophy_7d module import error: {exc}", None

    # Codex iter-1 P0 #1 fold: actually run scan + waive-emit + resolve
    # before computing status. Without this the 19th check only reads
    # ledger state that nothing ever populates -> never reaches RED in
    # real use. Each step is best-effort; any IO error is swallowed and
    # the status path's defense-in-depth expiry computation still works.
    #
    # Codex iter-2 P1 #2 fold: waives MUST fire BEFORE emit_resolutions.
    # Codex iter-4 P1 #1 fold: detect_all() is called ONCE here and
    # both scoped operations re-use it (avoids git-subprocess duplication).
    # Order:
    #   1. detect_all() -> full candidate set with target_ref cleartext
    #   2. emit_opened() dedups via audit-log
    #   3. emit_waives_for_scanned(all_candidates) scoped to commits
    #   4. resolve() / emit_resolutions() catches non-waived expired demands
    repo_root = Path(__file__).resolve().parents[2]
    all_candidates: List = []
    try:
        all_candidates = scanner.detect_all(repo_root)
        # Local dedup against audit-log (avoids 2nd git subprocess pass).
        already = scanner._existing_demand_ids(
            AUDIT_LOG_DEFAULT, scanner.SCAN_HORIZON_HOURS,
        )
        new_only = [ev for ev in all_candidates if ev.demand_id not in already]
        scanner.emit_opened(new_only)
    except Exception:  # noqa: BLE001 (Tier-S fail-soft)
        pass
    try:
        resolver.emit_waives_for_scanned(all_candidates, AUDIT_LOG_DEFAULT, repo_root)
    except Exception:  # noqa: BLE001
        pass
    try:
        summary_resolve = resolver.resolve(AUDIT_LOG_DEFAULT)
        resolver.emit_resolutions(summary_resolve)
    except Exception:  # noqa: BLE001
        pass

    try:
        status, summary, demand_metrics = resolver.atrophy_7d_status(AUDIT_LOG_DEFAULT)
    except Exception as exc:  # noqa: BLE001
        return "yellow", f"persona_atrophy_7d resolver error: {exc}", None

    try:
        score_metrics = _score_persona_coverage(hours=168.0)
        _emit_persona_coverage(score_metrics, window_hours=168)
    except Exception:  # noqa: BLE001
        score_metrics = {"score_x100": 0, "cells_covered": 0, "total_cells": 16}

    return status, summary, {
        **score_metrics,
        **demand_metrics,
        "window_hours": 168,
    }


def check_confidence_gate_drift_7d() -> Tuple[str, str, Any]:
    """PLAN-106 Wave F.2 — 20th Tier-S check.

    Detects HIGH_CONFIDENCE_BLOCK classes whose 7d FPR > 2% per
    ADR-019-AMEND-1 §6. Wraps the side-effect-free `detect_drift_7d`
    function from `.claude/scripts/check-confidence-gate-drift.py`
    (refactored per Wave F.1).

    Status mapping:
        - drift NOT detected, valid config + log → green
        - drift NOT detected, missing config/log → green (fail-OPEN
          per ADR-095 doctrine — no calendar gates, but also no
          spurious RED on fresh installs)
        - drift detected → yellow (advisory; auto-demote is the
          underlying script's responsibility, not the ceo-boot check)
        - exception → yellow with error message
    """
    try:
        import importlib.util
        scripts_dir = Path(__file__).resolve().parent
        spec = importlib.util.spec_from_file_location(
            "check_confidence_gate_drift",
            scripts_dir / "check-confidence-gate-drift.py",
        )
        if spec is None or spec.loader is None:
            return "yellow", "drift detector module spec load failed", None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as exc:  # noqa: BLE001 (Tier-S fail-soft)
        return "yellow", f"drift detector import error: {exc}", None

    try:
        drift, summary, detail = mod.detect_drift_7d()
    except Exception as exc:  # noqa: BLE001
        return "yellow", f"detect_drift_7d error: {exc}", None

    if not drift:
        return "green", summary, detail
    return "yellow", summary, detail


def _emit_settings_tamper_detected_safe(findings: List[Dict[str, str]]) -> None:
    """Emit ONE closed-enum ``settings_tamper_detected`` event per class.

    PLAN-135 W1 S3. Field contract (Sec MF-3, enforced emit-side by
    ``_SETTINGS_TAMPER_DETECTED_ALLOWLIST`` in ``_lib/audit_emit.py``):

      tamper_class  — closed enum (the 5 ``effective_config.TAMPER_*``
                      members; off-enum values are COERCED emit-side)
      layer         — closed enum (user/project/local/managed/env/disk;
                      first layer seen for the class)
      finding_count — int, clamped 0..99

    The finding DETAIL string is NEVER emitted — it can carry endpoint
    URLs, model ids, helper paths or flag values (mcp_routing.py
    breadcrumb precedent +
    [[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).

    Fail-open contract: pre-ceremony (action not yet in ``_KNOWN_ACTIONS``)
    writes a stderr breadcrumb instead of emitting; any emit failure is
    swallowed. NEVER raises, NEVER blocks boot.
    """
    if _audit_emit is None or not findings:
        return
    try:
        emit_fn = getattr(_audit_emit, "emit_generic", None)
        if not callable(emit_fn):
            return
        known = getattr(_audit_emit, "_KNOWN_ACTIONS", None)
        if known is not None and "settings_tamper_detected" not in known:
            sys.stderr.write(
                "[ceo-boot] 'settings_tamper_detected' not in _KNOWN_ACTIONS; "
                "emit dropped until the PLAN-135 W1 kernel ceremony lands.\n"
            )
            return
        by_class: Dict[str, Dict[str, Any]] = {}
        for f in findings:
            if not isinstance(f, dict):
                continue
            klass = str(f.get("class", ""))[:64]
            if not klass:
                continue
            slot = by_class.setdefault(
                klass, {"layer": str(f.get("layer", ""))[:16], "count": 0}
            )
            slot["count"] += 1
        for klass in sorted(by_class):  # deterministic order (CR-N7)
            slot = by_class[klass]
            emit_fn(
                "settings_tamper_detected",
                session_id=_ceo_boot_session_id(),
                tamper_class=klass,
                layer=slot["layer"],
                finding_count=max(0, min(99, int(slot["count"]))),
            )
    except Exception:  # noqa: BLE001 — advisory fail-open
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            import traceback
            traceback.print_exc(file=sys.stderr)


def check_settings_tamper_tripwires() -> Tuple[str, str, Any]:
    """PLAN-135 W1 S3 — 21st Tier-S check: settings/env tamper tripwires.

    Scans the RESOLVED multi-layer settings (user / project / local /
    managed — including the gitignored, sentinel-blind
    ``settings.local.json``) plus the import-time env snapshot for the
    five tamper classes of THREAT-MODEL-WORKSHEET.md §2, via the shared
    ``_lib/effective_config`` module:

      (a) ``disableAllHooks`` truthy in ANY settings layer
      (b) ``ANTHROPIC_MODEL`` / ``ANTHROPIC_DEFAULT_*`` /
          ``ANTHROPIC_SMALL_FAST_MODEL`` remap outside the ADR-149
          allowlist (skipped fail-open when the allowlist is unreadable)
      (c) ``ANTHROPIC_BASE_URL`` / ``ANTHROPIC_AUTH_TOKEN`` /
          ``apiKeyHelper`` endpoint remap (model substitution AND
          transcript egress outside check (b) entirely)
      (d) ``permissions.defaultMode: bypassPermissions`` or
          dangerously-skip flags in any layer (nullifies the S2 floor)
      (e) effective hook count == registered count (registered-but-
          missing-on-disk census; a missing hook fails open = allow)

    Env reads come EXCLUSIVELY from the module-import-time snapshot
    (``_TAMPER_ENV_SNAPSHOT``, trusted_env pattern) — never live
    ``os.environ``. Settings reads come from the RESOLVED multi-layer
    config (``effective_config.resolve_settings``).

    Status mapping (ADVISORY — /ceo-boot never blocks the session):

      findings present           → red    (rail integrity is suspect)
      no findings, layer errors  → yellow (a corrupt PRESENT layer is
                                   itself an anomaly worth eyes)
      no findings, clean         → green
      module missing / internal  → yellow (advisory fail-open +
                                   stderr breadcrumb, never crash)

    Side-effect: one closed-enum ``settings_tamper_detected`` audit emit
    per detected class via ``_emit_settings_tamper_detected_safe``
    (``_KNOWN_ACTIONS``-guarded pre-ceremony).
    """
    if _effective_config is None:
        sys.stderr.write(
            "[ceo-boot] effective_config unavailable — settings tamper "
            "tripwires inactive (fail-open).\n"
        )
        return (
            "yellow",
            "effective_config unavailable — tamper tripwires inactive",
            None,
        )
    try:
        resolved = _effective_config.resolve_settings(REPO_ROOT)
        findings = _effective_config.classify_tampering(
            resolved, _TAMPER_ENV_SNAPSHOT
        )
        _emit_settings_tamper_detected_safe(findings)
        if findings:
            classes = sorted({
                str(f.get("class", ""))
                for f in findings
                if isinstance(f, dict) and f.get("class")
            })
            # Summary carries ONLY closed-enum class names (never the
            # finding detail — it can embed env values / endpoints).
            return (
                "red",
                f"{len(findings)} tamper finding(s): "
                f"{','.join(classes)[:160]}",
                findings,
            )
        errors = resolved.get("errors") or []
        if errors:
            return (
                "yellow",
                f"no tamper indicators; {len(errors)} unparseable "
                f"settings layer(s)",
                {"errors": [str(e)[:160] for e in errors[:4]]},
            )
        registered: set = set()
        for layer in resolved.get("layers", []):
            if isinstance(layer, dict) and layer.get("name") in (
                "project", "local",
            ):
                registered.update(
                    _effective_config.registered_hook_basenames(
                        layer.get("data") or {}
                    )
                )
        effective = _effective_config.count_effective_hooks(REPO_ROOT)
        return (
            "green",
            f"no tamper indicators ({effective}/{len(registered)} "
            f"registered hooks effective)",
            {"registered": len(registered), "effective_on_disk": effective},
        )
    except Exception as exc:  # noqa: BLE001 (Tier-S fail-soft floor)
        return "yellow", f"tamper tripwires error: {type(exc).__name__}", None


TIER_S_CHECKS: List[Tuple[str, Callable[[], Tuple[str, str, Any]]]] = [
    ("plans_executing", check_plans_executing),
    ("plans_reviewed_pending", check_plans_reviewed_pending),
    ("plans_stranded_executing", check_plans_stranded_executing),
    ("plans_draft", check_plans_draft),
    ("audit_log_freshness", check_audit_log_freshness),
    ("dispatch_count_24h", check_dispatch_count_24h),
    ("skill_unknown_ratio", check_skill_unknown_ratio),
    ("governance_validate", check_governance_validate),
    # PLAN-082 Codex Item D: `hook_test_baseline` renamed to `hook_live_smoke`
    # — the check now performs a live hook smoke (settings.json parse + file
    # existence + py_compile) rather than reading a pytest-baseline cache that
    # was never populated. Old function symbol preserved as alias for tests.
    ("hook_live_smoke", check_hook_live_smoke),
    ("audit_v3_backlog", check_audit_v3_backlog),
    ("sentinels_pending_gpg", check_sentinels_pending_gpg),
    ("rc_hold_aged", check_rc_hold_aged),
    ("cost_24h_usd", check_cost_24h_usd),
    ("active_plan_burn_ratio", check_active_plan_burn_ratio),
    ("adrs_stale_proposed", check_adrs_stale_proposed),
    # PLAN-091 Wave A.1 — 16th Tier-S check. Delegates to standalone hook
    # module `.claude/hooks/check_tier_policy_misrouting_24h.py` per the
    # PLAN-088 §AC11 18-check target.
    ("tier_policy_misrouting_24h", check_tier_policy_misrouting_24h),
    # PLAN-093 Wave C.2 — 17th Tier-S check: prompt-cache hit-rate
    # detection emitting `cache_discipline_alerted` on threshold breach.
    ("cache_discipline_alerted", check_cache_discipline_alerted),
    # PLAN-093 Wave C.5/C.6 — 18th Tier-S check: 4-persona × 4-task coverage
    # matrix at 24h cadence (session-smoke). S127 cadence-amendment (Codex R2
    # `019e33a3` AMEND): demoted to permanent observability, never red.
    ("ceo_boot_persona_coverage_score", check_ceo_boot_persona_coverage_score),
    # S127 cadence-amendment — 19th Tier-S check: same matrix at 168h cadence
    # (trend / chronic-atrophy signal). Phase 1: observability-only, never red.
    # Phase 2 (PLAN-104-persona-demand-ledger): RED authority activated once
    # `eligible_demand_events` is populated from the demand ledger.
    ("persona_atrophy_7d", check_persona_atrophy_7d),
    # PLAN-106 Wave F.2 — 20th Tier-S check. Wires the standalone
    # `.claude/scripts/check-confidence-gate-drift.py` module's
    # `detect_drift_7d()` importable into the parallel registry per
    # ADR-019-AMEND-1 §6 (7d rolling FPR > 2% advisory). Read-only;
    # the underlying script's `--emit` flag remains the canonical
    # emission surface for `confidence_gate_fp_drift_detected`.
    ("confidence_gate_drift_7d", check_confidence_gate_drift_7d),
    # PLAN-135 W1 S3 — 21st Tier-S check: settings/env tamper tripwires
    # over the RESOLVED multi-layer settings (shared _lib/effective_config;
    # user/project/local/managed incl. the sentinel-blind
    # settings.local.json) + the import-time env snapshot (trusted_env
    # pattern). Classes (a)-(e) per THREAT-MODEL-WORKSHEET.md §2; closed-
    # enum `settings_tamper_detected` emit per class. ADVISORY fail-open:
    # infra error → yellow + stderr breadcrumb, never crashes, never blocks.
    ("settings_tamper_tripwires", check_settings_tamper_tripwires),
]

assert len(TIER_S_CHECKS) == 21, f"Expected 21 Tier-S checks, got {len(TIER_S_CHECKS)}"


TIER_A_CHECKS: List[Tuple[str, Callable[[], Tuple[str, str, Any]]]] = [
    ("tier_a_debate_transcripts", check_tier_a_debate_transcripts),
    ("tier_a_lessons_30d", check_tier_a_lessons_30d),
    ("tier_a_spec_version_drift", check_tier_a_spec_version_drift),
    ("tier_a_npm_version_match", check_tier_a_npm_version_match),
    ("tier_a_waivers_count", check_tier_a_waivers_count),
    ("tier_a_adrs_recent_status", check_tier_a_adrs_recent_status),
    ("tier_a_cache_hit_rate_24h", check_tier_a_cache_hit_rate_24h),
    ("tier_a_hook_test_baseline_age", check_tier_a_hook_test_baseline_age),
    ("tier_a_sentinel_signers_tracked", check_tier_a_sentinel_signers_tracked),
    ("tier_a_gitignore_state_excluded", check_tier_a_gitignore_state_excluded),
]

assert len(TIER_A_CHECKS) == 10, f"Expected 10 Tier-A checks, got {len(TIER_A_CHECKS)}"


# Verbose-mode aggregate budget: extends Tier-S 5s window to 10s when
# Tier-A is dispatched alongside (PLAN-065 §4.3.3).
AGGREGATE_TIMEOUT_VERBOSE_S = 10.0


# ---- Dispatcher ------------------------------------------------------------

def _wrap_check(name: str, fn: Callable[[], Tuple[str, str, Any]]) -> CheckResult:
    t0 = time.perf_counter()
    try:
        status, summary, detail = fn()
        dur = (time.perf_counter() - t0) * 1000
        return CheckResult(name, status, summary, dur, detail)
    except Exception as e:  # noqa: BLE001 (PoC fail-soft)
        dur = (time.perf_counter() - t0) * 1000
        return CheckResult(name, "error", f"{type(e).__name__}: {e}", dur, None)


def dispatch_parallel(
    *,
    include_tier_a: bool = False,
    aggregate_timeout_s: Optional[float] = None,
) -> List[CheckResult]:
    """Dispatch Tier-S (and optionally Tier-A) checks in parallel via as_completed.

    Codex S82 P0 #2 fix: previous impl iterated future_to_name.items() and
    called fut.result(timeout=PER_CHECK_TIMEOUT_S) sequentially — so the
    500ms started counting when each future was *observed*, not when it
    started running. Timeouts cascaded and the per-check budget was
    fictional under load. New impl uses as_completed() with the AGGREGATE
    budget; per-check budget becomes a soft annotation (subprocess timeouts
    inside each check enforce real CPU/IO ceilings, e.g. governance_validate
    has subprocess timeout=4.0).

    Tier-A extension (PLAN-065 §4.3.3): when ``include_tier_a=True``,
    dispatcher also enqueues TIER_A_CHECKS and the aggregate budget
    defaults to AGGREGATE_TIMEOUT_VERBOSE_S (10s).

    Pool lifecycle (per PLAN-087 A.6 / `F-A-CR-D0012` P2): the
    ``ThreadPoolExecutor`` is NOT used as a context manager because
    ``with`` exit calls ``shutdown(wait=True)`` which blocks on
    long-running futures past the aggregate timeout. The explicit
    ``shutdown(wait=False, cancel_futures=True)`` in the ``finally``
    block releases the pool immediately and cancels any futures that
    have not yet started; in-flight futures continue to run on their
    daemon threads but their results are dropped (the aggregate
    timeout has already produced their `AGG_TIMEOUT` rows). Python
    3.9+ ``cancel_futures`` parameter required; the project min
    Python is 3.9 per ADR-002.
    """
    registry: List[Tuple[str, Callable[[], Tuple[str, str, Any]]]] = list(TIER_S_CHECKS)
    if include_tier_a:
        registry = registry + list(TIER_A_CHECKS)
    if aggregate_timeout_s is None:
        aggregate_timeout_s = (
            AGGREGATE_TIMEOUT_VERBOSE_S if include_tier_a else AGGREGATE_TIMEOUT_S
        )

    results_by_name: Dict[str, CheckResult] = {}
    pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    try:
        future_to_name = {
            pool.submit(_wrap_check, name, fn): name for name, fn in registry
        }
        try:
            for fut in as_completed(future_to_name, timeout=aggregate_timeout_s):
                name = future_to_name[fut]
                try:
                    res = fut.result()  # already done, instant
                except Exception as e:  # noqa: BLE001
                    res = CheckResult(name, "error", f"{type(e).__name__}: {e}", 0.0, None)
                # Soft per-check ceiling: annotate slow but green checks.
                budget_s = PER_CHECK_TIMEOUT_OVERRIDES_S.get(name, PER_CHECK_TIMEOUT_S)
                if res.duration_ms > budget_s * 1000 and res.status == "green":
                    res.summary = (
                        f"{res.summary} (slow {res.duration_ms:.0f}ms > "
                        f"budget {int(budget_s * 1000)}ms)"
                    )
                results_by_name[name] = res
        except FuturesTimeout:
            pass  # aggregate exceeded — handled below

        # Mark non-completed as aggregate-timeout (Codex P0 #2: explicit, not silent)
        for fut, name in future_to_name.items():
            if name not in results_by_name:
                ms = int(aggregate_timeout_s * 1000)
                results_by_name[name] = CheckResult(
                    name, "timeout",
                    f"AGG_TIMEOUT (>{ms}ms aggregate)",
                    aggregate_timeout_s * 1000, None,
                )
                _emit_ceo_boot_check_skipped_safe(
                    check_name=name,
                    timeout_ms=ms,
                )
    finally:
        # See docstring "Pool lifecycle" — non-blocking shutdown is
        # required to honor the aggregate timeout.
        pool.shutdown(wait=False, cancel_futures=True)

    # Codex S82 post-patch fix: emit results in registry order for CR-N7
    # stability across runs (was completion-order, non-deterministic).
    return [results_by_name[name] for name, _ in registry if name in results_by_name]


# ---- Cached path (PLAN-065 §4.3.2 real per-key cache) -------------------

def _cache_key_raw() -> str:
    """Compose raw cache key string from (HEAD + audit-log mtime + size).

    Per Codex S82 P1 #5 the sub-second precision is NOT required; we use
    integer seconds + size-in-bytes which together provide collision-safe
    invalidation when the audit-log is appended.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=1.0,
        )
        head = proc.stdout.strip() or "nogit"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        head = "nogit"
    try:
        st = AUDIT_LOG_DEFAULT.stat()
        mtime = int(st.st_mtime)
        size = int(st.st_size)
    except OSError:
        mtime, size = 0, 0
    return f"{head}:{mtime}:{size}"


def _cache_key() -> str:
    """SHA-256 short-hash of raw cache key (filename-safe + bounded length)."""
    raw = _cache_key_raw()
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:32]


def _cache_path_for_key(key: str) -> Path:
    """Resolve cache file path for a given key under the active cache dir."""
    return _cache_dir() / f"{key}.json"


def cache_lru_evict() -> None:
    """LRU-evict oldest cache files when dir size exceeds CACHE_DIR_SIZE_CAP_BYTES.

    Fail-open: any OSError silently breadcrumbs to stderr and returns.
    Atime-aware where supported; mtime fallback (atime is updated by reads
    on most filesystems but POSIX `relatime` may suppress it).
    """
    cdir = _cache_dir()
    if not cdir.exists():
        return
    try:
        entries: List[Tuple[float, int, Path]] = []
        total = 0
        for f in cdir.glob("*.json"):
            try:
                st = f.stat()
            except OSError:
                continue
            entries.append((st.st_atime, st.st_size, f))
            total += st.st_size
        if total <= CACHE_DIR_SIZE_CAP_BYTES:
            return
        # Evict oldest-first until under cap.
        entries.sort(key=lambda e: e[0])
        for atime, size, path in entries:
            if total <= CACHE_DIR_SIZE_CAP_BYTES:
                break
            try:
                path.unlink()
                total -= size
            except OSError:
                continue
    except OSError as e:
        sys.stderr.write(f"# ceo-boot cache LRU evict failed: {type(e).__name__}\n")


def cached_load() -> Tuple[bool, Any]:
    """Per-key cache load. Returns (hit, payload).

    Hit semantics: cache file exists for current key, mtime within TTL,
    file size within cap, JSON parses cleanly. Otherwise miss (fail-open).
    Atime is touched on hit (LRU signal).
    """
    key = _cache_key()
    path = _cache_path_for_key(key)
    if not path.exists():
        return False, None
    try:
        st = path.stat()
        if st.st_size > CACHE_FILE_SIZE_CAP_BYTES:
            return False, None  # corrupt / oversized — treat as miss
        if (time.time() - st.st_mtime) > CACHE_TTL_S:
            return False, None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, None
    # Defense-in-depth: validate cache_key matches (mtime alone could
    # collide if filesystem is restored from backup).
    if data.get("cache_key") != key:
        return False, None
    # Touch atime for LRU signal (best-effort; ignore filesystem refusal).
    try:
        os.utime(path, None)
    except OSError:
        pass
    return True, data


def cached_store(results: List[CheckResult]) -> None:
    """Write digest to per-key cache. Atomic (temp + rename); fail-open.

    Codex S82 P1 fix: previous impl had unguarded mkdir + write_text;
    permission/lock/filesystem errors aborted boot post-checks pre-output.
    Now wraps all I/O in try/except; on failure emits stderr breadcrumb
    and returns silently (cache miss next boot, main path unaffected).

    Schema parity: payload includes gate_pass / checks_total / checks_failed
    / recommendations / results — identical shape to the live --json output
    so adopters get the same payload from cache-hit and fresh dispatch.
    """
    cdir = _cache_dir()
    key = _cache_key()
    target = _cache_path_for_key(key)
    try:
        cdir.mkdir(parents=True, exist_ok=True)
        failed = sum(1 for r in results if r.status in ("red", "error", "timeout"))
        gate_pass = (failed == 0)
        payload = {
            "cache_key": key,
            "ts": time.time(),
            "gate_pass": gate_pass,
            "checks_total": len(results),
            "checks_failed": failed,
            "recommendations": _make_recommendations(results),
            "results": [
                {"name": r.name, "status": r.status, "summary": r.summary, "duration_ms": r.duration_ms}
                for r in results
            ],
        }
        body = json.dumps(payload)
        if len(body.encode("utf-8")) > CACHE_FILE_SIZE_CAP_BYTES:
            # Drop the recommendations + heavy detail to fit the cap.
            payload["recommendations"] = []
            body = json.dumps(payload)
        # Atomic write: temp file + rename.
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(body, encoding="utf-8")
        os.replace(tmp, target)
        # Best-effort LRU eviction (post-write, never blocks).
        cache_lru_evict()
    except (OSError, PermissionError, json.JSONDecodeError) as e:
        sys.stderr.write(f"# ceo-boot cache-store failed (fail-open): {type(e).__name__}\n")


# ---- Recommendations engine (PLAN-065 §4.3 Phase 3-D) ---------------------

def _make_recommendations(results: List[CheckResult]) -> List[str]:
    """Rule-based prioritizer ≤5 actionable items (Sec MF-4 sanitized).

    Deterministic ordering (CR-N7): lex-sort by category prefix so ``--json``
    is stable across runs.
    """
    recs: List[Tuple[str, str]] = []  # (sort_key, formatted)
    by_name: Dict[str, CheckResult] = {r.name: r for r in results}

    # Codex S82 P1 fix: recs engine ignored timeout/error checks. Since those
    # flip gate_pass=False, they MUST surface as top-priority recommendations.
    #
    # Codex CDX-W5-iter3-P1 closure: the original `_NAMED_RULES` skip
    # was over-engineered defense against duplicate emit — but the named
    # rule branches below only fire on `status in {yellow, red}`. A named
    # check that times out (status "timeout"/"error") therefore matched
    # NEITHER branch, producing a silent gap where gate_pass=False but
    # zero recommendation surfaced. We now emit the 00-* row for every
    # failing check; the named branches can never co-fire (their `status`
    # gate is incompatible with timeout/error), so dedup is moot.
    failing = sorted(
        (r for r in results if r.status in ("timeout", "error")),
        key=lambda r: r.name,
    )
    for r in failing[:3]:  # cap at 3 to leave room for named rules
        recs.append((
            f"00-{r.name}-{r.status}",  # sort BEFORE 01-owner-sentinels
            f"Check '{r.name}' {r.status}: {_sanitize_for_recs(r.summary)} "
            f"(blocks gate_pass)",
        ))

    # PLAN-135 W1 S3 — settings/env tamper tripwires (rail integrity).
    # Sort key "005-*" lands AFTER the 00-* gate-blockers and BEFORE
    # 01-owner-sentinels (lexicographic: "00-" < "005" < "01-"): a fired
    # tripwire means every other signal on this digest may already be
    # produced by a disarmed/redirected rail. Only closed-enum class
    # names reach the rendered text (finding detail can embed env values).
    tamper = by_name.get("settings_tamper_tripwires")
    if tamper and tamper.status == "red" and tamper.detail:
        items = tamper.detail if isinstance(tamper.detail, list) else []
        classes = sorted({
            str(f.get("class", ""))
            for f in items
            if isinstance(f, dict) and f.get("class")
        })
        if classes:
            preview = _sanitize_for_recs(", ".join(classes[:3]))
            recs.append((
                "005-settings-tamper",
                f"Settings/env tamper tripwire(s) fired ({len(items)}): "
                f"{preview}{'...' if len(classes) > 3 else ''} — inspect "
                f"settings layers + env before trusting this session",
            ))

    # Owner-pending GPG sentinels — highest priority (HARD blocker for ceremony)
    sent = by_name.get("sentinels_pending_gpg")
    if sent and sent.status == "yellow" and sent.detail:
        items = sent.detail if isinstance(sent.detail, list) else []
        if items:
            preview = _sanitize_for_recs(", ".join(items[:3]))
            recs.append((
                "01-owner-sentinels",
                f"Owner GPG sign pending: {len(items)} sentinels ({preview}{'...' if len(items) > 3 else ''})",
            ))

    # Stranded executing plans (no commits in 24h)
    stranded = by_name.get("plans_stranded_executing")
    if stranded and stranded.status == "red" and stranded.detail:
        items = stranded.detail if isinstance(stranded.detail, list) else []
        if items:
            preview = _sanitize_for_recs(", ".join(items[:3]))
            recs.append((
                "02-stranded-plans",
                f"Stranded executing plans (>24h no commits): {preview}",
            ))

    # Skill-unknown ratio > threshold
    skill = by_name.get("skill_unknown_ratio")
    if skill and skill.status == "red":
        recs.append((
            "03-skill-unknown",
            f"Spawn dispatch skill=unknown ratio elevated: {_sanitize_for_recs(skill.summary)}",
        ))

    # Audit-v3 backlog open
    av3 = by_name.get("audit_v3_backlog")
    if av3 and av3.status == "yellow" and av3.detail:
        items = av3.detail if isinstance(av3.detail, list) else []
        if items:
            preview = _sanitize_for_recs(", ".join(items[:3]))
            recs.append((
                "04-audit-v3-backlog",
                f"Audit-v3 backlog open ({len(items)}): {preview}",
            ))

    # ADRs stale-proposed >30d
    adrs = by_name.get("adrs_stale_proposed")
    if adrs and adrs.status == "yellow" and adrs.detail:
        items = adrs.detail if isinstance(adrs.detail, list) else []
        if items:
            preview = _sanitize_for_recs(", ".join(items[:3]))
            recs.append((
                "05-adrs-stale",
                f"ADRs PROPOSED >30d ({len(items)}): {preview} — promote or retract",
            ))

    # Sort by deterministic key (CR-N7) and cap at 5
    recs.sort(key=lambda x: x[0])
    return [text for _, text in recs[:5]]


# PLAN-078 Wave 5 — severity-aware view of the recommendations engine.
# Mirrors `_make_recommendations` ordering exactly (same sort key + ≤5 cap)
# but exposes the (sort_key, text, severity) triple so the marker emitter
# can filter by severity≥medium without re-classifying. Severity buckets
# track the rule rank assigned in `_make_recommendations`:
#
#   00-* (timeout/error gate-blockers) → high
#   005-settings-tamper                → high (PLAN-135 W1 S3 rail integrity)
#   01-owner-sentinels                 → high
#   02-stranded-plans                  → high
#   03-skill-unknown                   → medium
#   04-audit-v3-backlog                → medium
#   05-adrs-stale                      → low
#
# Anything else (future rules) defaults to "low" — caller policy is to
# only emit markers for medium/high, so unknown future rules are silent
# until the mapping is updated. Codex CDX-P1-04 closure: this helper is
# deterministic + side-effect-free; the marker emitter consumes the
# triple and never mutates `_make_recommendations` output.
def _recommendations_with_severity(
    results: List[CheckResult],
) -> List[Tuple[str, str, str]]:
    """Return (sort_key, text, severity) triples mirroring _make_recommendations.

    Re-runs the rule pipeline (cheap — already O(N) over results) so this
    helper is safe to call after `_make_recommendations` without ordering
    drift. Severity is derived from the sort_key prefix (deterministic).
    """
    recs: List[Tuple[str, str]] = []
    by_name: Dict[str, CheckResult] = {r.name: r for r in results}

    # Mirror `_make_recommendations` exactly (Codex CDX-W5-iter3-P1):
    # named-rule skip removed because timeout/error never overlaps with
    # the yellow/red gates of the named branches.
    failing = sorted(
        (r for r in results if r.status in ("timeout", "error")),
        key=lambda r: r.name,
    )
    for r in failing[:3]:
        recs.append((
            f"00-{r.name}-{r.status}",
            f"Check '{r.name}' {r.status}: {_sanitize_for_recs(r.summary)} "
            f"(blocks gate_pass)",
        ))

    # PLAN-135 W1 S3 — mirror of the _make_recommendations tamper rule
    # (same sort key + same text so the two pipelines never drift).
    tamper = by_name.get("settings_tamper_tripwires")
    if tamper and tamper.status == "red" and tamper.detail:
        items = tamper.detail if isinstance(tamper.detail, list) else []
        classes = sorted({
            str(f.get("class", ""))
            for f in items
            if isinstance(f, dict) and f.get("class")
        })
        if classes:
            preview = _sanitize_for_recs(", ".join(classes[:3]))
            recs.append((
                "005-settings-tamper",
                f"Settings/env tamper tripwire(s) fired ({len(items)}): "
                f"{preview}{'...' if len(classes) > 3 else ''} — inspect "
                f"settings layers + env before trusting this session",
            ))

    sent = by_name.get("sentinels_pending_gpg")
    if sent and sent.status == "yellow" and sent.detail:
        items = sent.detail if isinstance(sent.detail, list) else []
        if items:
            preview = _sanitize_for_recs(", ".join(items[:3]))
            recs.append((
                "01-owner-sentinels",
                f"Owner GPG sign pending: {len(items)} sentinels ({preview}{'...' if len(items) > 3 else ''})",
            ))

    stranded = by_name.get("plans_stranded_executing")
    if stranded and stranded.status == "red" and stranded.detail:
        items = stranded.detail if isinstance(stranded.detail, list) else []
        if items:
            preview = _sanitize_for_recs(", ".join(items[:3]))
            recs.append((
                "02-stranded-plans",
                f"Stranded executing plans (>24h no commits): {preview}",
            ))

    skill = by_name.get("skill_unknown_ratio")
    if skill and skill.status == "red":
        recs.append((
            "03-skill-unknown",
            f"Spawn dispatch skill=unknown ratio elevated: {_sanitize_for_recs(skill.summary)}",
        ))

    av3 = by_name.get("audit_v3_backlog")
    if av3 and av3.status == "yellow" and av3.detail:
        items = av3.detail if isinstance(av3.detail, list) else []
        if items:
            preview = _sanitize_for_recs(", ".join(items[:3]))
            recs.append((
                "04-audit-v3-backlog",
                f"Audit-v3 backlog open ({len(items)}): {preview}",
            ))

    adrs = by_name.get("adrs_stale_proposed")
    if adrs and adrs.status == "yellow" and adrs.detail:
        items = adrs.detail if isinstance(adrs.detail, list) else []
        if items:
            preview = _sanitize_for_recs(", ".join(items[:3]))
            recs.append((
                "05-adrs-stale",
                f"ADRs PROPOSED >30d ({len(items)}): {preview} — promote or retract",
            ))

    recs.sort(key=lambda x: x[0])
    triples: List[Tuple[str, str, str]] = []
    for sort_key, text in recs[:5]:
        if sort_key.startswith("00-") or sort_key in (
            "005-settings-tamper",  # PLAN-135 W1 S3 — rail-integrity = high
            "01-owner-sentinels", "02-stranded-plans"
        ):
            severity = "high"
        elif sort_key in ("03-skill-unknown", "04-audit-v3-backlog"):
            severity = "medium"
        elif sort_key == "05-adrs-stale":
            severity = "low"
        else:  # pragma: no cover — defensive default for future rules
            severity = "low"
        triples.append((sort_key, text, severity))
    return triples


# ---- Renderer ---------------------------------------------------------------

def render_digest(results: List[CheckResult], short: bool = False) -> str:
    lines = ["", "## /ceo-boot digest", ""]
    if short:
        red = sum(1 for r in results if r.status == "red")
        yellow = sum(1 for r in results if r.status == "yellow")
        timeout = sum(1 for r in results if r.status == "timeout")
        error = sum(1 for r in results if r.status == "error")
        green = sum(1 for r in results if r.status == "green")
        lines.append(
            f"- {green} green / {yellow} yellow / {red} red / "
            f"{timeout} timeout / {error} error"
        )
        # Surface non-green checks one-line for situational awareness
        for r in results:
            if r.status != "green":
                lines.append(f"  - {r.name}: {r.status} — {r.summary}")
    else:
        lines.append("| Check | Status | Summary | Duration ms |")
        lines.append("|---|---|---|---|")
        for r in results:
            lines.append(f"| {r.name} | {r.status} | {r.summary} | {r.duration_ms:.0f} |")

    # Recommendations engine output
    recs = _make_recommendations(results)
    if recs:
        lines.append("")
        lines.append("### Recommendations")
        for i, rec in enumerate(recs, 1):
            lines.append(f"{i}. {rec}")

    lines.append("")
    return "\n".join(lines)


# ---- Bench harness ---------------------------------------------------------

def _percentile(xs: List[float], p: float) -> float:
    """Stdlib percentile via sorted index. p in [0,100]. Empty → 0.0.

    Spec (PLAN-065 §4.3 + S82 brief): use ``sorted(arr)[int(0.95 * len(arr))]``
    style indexing — NOT numpy. With small N the index can hit an off-by-one
    near the upper bound; we use ``int(round((len(s)-1) * p/100))`` which is
    monotonic-correct for both N=5 and N=10.
    """
    if not xs:
        return 0.0
    s = sorted(xs)
    k = int(round((len(s) - 1) * p / 100.0))
    return s[k]


def _rss_kb_current() -> float:
    """Return current process RSS in KiB.

    Codex S82 P1 fix: ``resource.getrusage(RUSAGE_SELF).ru_maxrss`` returns
    BYTES on macOS but KiB on Linux. We normalize to KiB by detecting the
    platform. This is high-water mark for the process; deltas across runs
    are still meaningful as long as the platform's unit is consistent.
    """
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        # macOS: bytes → KiB
        return rss / 1024.0
    # Linux + most BSDs: already KiB
    return float(rss)


def bench(n_runs: int = 5, *, include_tier_a: bool = False) -> Dict[str, Any]:
    """Run the dispatcher N times. Report p50/p95 wall-clock, per-iter RSS, deltas.

    Output schema includes the legacy fields (``wall_clock_ms`` map, per-check
    p50/p95, tracemalloc current/peak) PLUS the PLAN-065 §4.3 spec fields
    (per-iter ``iterations`` list with ``iter``, ``duration_ms``, ``rss_kb``
    + summary dict with ``p50_ms``, ``p95_ms``, ``min_ms``, ``max_ms``,
    ``rss_delta_kb``).
    """
    wall_clocks: List[float] = []
    rss_per_iter: List[float] = []
    iterations: List[Dict[str, Any]] = []
    registry = list(TIER_S_CHECKS) + (list(TIER_A_CHECKS) if include_tier_a else [])
    per_check_durations: Dict[str, List[float]] = {name: [] for name, _ in registry}

    rss_before = _rss_kb_current()
    tracemalloc.start()
    snap_before = tracemalloc.take_snapshot()
    for i in range(n_runs):
        t0 = time.perf_counter()
        results = dispatch_parallel(include_tier_a=include_tier_a)
        wc = (time.perf_counter() - t0) * 1000
        rss_now = _rss_kb_current()
        wall_clocks.append(wc)
        rss_per_iter.append(rss_now)
        iterations.append({
            "iter": i + 1,
            "duration_ms": round(wc, 2),
            "rss_kb": round(rss_now, 2),
        })
        for r in results:
            per_check_durations.setdefault(r.name, []).append(r.duration_ms)
    snap_after = tracemalloc.take_snapshot()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_after = _rss_kb_current()

    diff_stats = snap_after.compare_to(snap_before, "filename")
    py_delta_kb = sum(stat.size_diff for stat in diff_stats) / 1024.0

    return {
        "n_runs": n_runs,
        "include_tier_a": include_tier_a,
        "iterations": iterations,
        "wall_clock_ms": {
            "p50": _percentile(wall_clocks, 50),
            "p95": _percentile(wall_clocks, 95),
            "min": min(wall_clocks) if wall_clocks else 0.0,
            "max": max(wall_clocks) if wall_clocks else 0.0,
        },
        "summary": {
            "p50_ms": round(_percentile(wall_clocks, 50), 2),
            "p95_ms": round(_percentile(wall_clocks, 95), 2),
            "min_ms": round(min(wall_clocks), 2) if wall_clocks else 0.0,
            "max_ms": round(max(wall_clocks), 2) if wall_clocks else 0.0,
            "rss_delta_kb": round(rss_after - rss_before, 2),
        },
        "per_check_p95_ms": {name: _percentile(durs, 95) for name, durs in per_check_durations.items()},
        "per_check_p50_ms": {name: _percentile(durs, 50) for name, durs in per_check_durations.items()},
        "memory_python_delta_kb": round(py_delta_kb, 2),
        "tracemalloc_peak_kb": round(peak / 1024.0, 2),
        "tracemalloc_current_kb": round(current / 1024.0, 2),
    }


def render_bench_markdown(report: Dict[str, Any]) -> str:
    """Render bench report as a markdown table (PLAN-065 §4.3 spec).

    Header columns: iter # | duration_ms | RSS_kb. Summary row appended
    with p50/p95/min/max/RSS_delta. Returns the rendered string (caller
    writes to stdout).
    """
    lines = ["", "## /ceo-boot --bench", ""]
    lines.append(f"N={report['n_runs']}  include_tier_a={report.get('include_tier_a', False)}")
    lines.append("")
    lines.append("| iter | duration_ms | RSS_kb |")
    lines.append("|---|---|---|")
    for it in report.get("iterations", []):
        lines.append(f"| {it['iter']} | {it['duration_ms']:.1f} | {it['rss_kb']:.1f} |")
    s = report.get("summary", {})
    lines.append(
        f"| **summary** | p50={s.get('p50_ms', 0):.1f} / p95={s.get('p95_ms', 0):.1f}"
        f" / min={s.get('min_ms', 0):.1f} / max={s.get('max_ms', 0):.1f}"
        f" | rss_delta={s.get('rss_delta_kb', 0):.1f} |"
    )
    lines.append("")
    return "\n".join(lines)


# === PLAN-065 Phase 2 audit_emit wire =====================================
# Reality-Ledger fixture #4 closure (declared-but-not-wired). Pre-S82,
# ceo-boot.py shipped emit comments only. Phase 2 wires the actual call.
# Sec MF-3 field allowlist enforced ON THE EMIT SIDE (_lib/audit_emit.py).
# Caller passes only allowlisted fields; never raises on emit failure.
# Pre-canonical-ceremony the symbol is missing → hasattr() guard short-
# circuits silently (advisory log to stderr only when CEO_BOOT_DEBUG=1).


def _ceo_boot_session_id() -> str:
    """Derive session id from harness env or a stable fallback.

    Defense-in-depth: never raises. The session_id is used as a forensic
    correlator across the 15 Tier-S checks; it does NOT need to be
    cryptographically unique.
    """
    sid = os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("CEO_SESSION_ID")
    if sid:
        return sid[:64]  # bound length defense-in-depth
    # Fallback: parent shell PID + start of audit-log mtime. Stable
    # within a session, advisory across sessions.
    try:
        return f"pid-{os.getppid()}-{int(AUDIT_LOG_DEFAULT.stat().st_mtime)}"
    except OSError:
        return f"pid-{os.getppid()}"


def _emit_ceo_boot_emitted_safe(
    *,
    gate_pass: bool,
    duration_ms: int,
    checks_total: int,
    checks_failed: int,
    cache_hit: bool = False,
) -> None:
    """Wire-up to audit_emit.emit_ceo_boot_emitted. Fail-open contract.

    Pre-canonical-ceremony: hasattr() returns False, function is a no-op.
    Post-ceremony: emits the telemetry event with Sec MF-3 field allowlist
    enforced on the emit side.
    """
    if _audit_emit is None:
        return
    fn = getattr(_audit_emit, "emit_ceo_boot_emitted", None)
    if not callable(fn):
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            sys.stderr.write(
                "# ceo-boot: audit_emit.emit_ceo_boot_emitted not registered "
                "(canonical ceremony pending v1.12.0)\n"
            )
        return
    try:
        fn(
            session_id=_ceo_boot_session_id(),
            gate_pass=bool(gate_pass),
            duration_ms=int(duration_ms),
            checks_total=int(checks_total),
            checks_failed=int(checks_failed),
            cache_hit=bool(cache_hit),
        )
    except Exception:  # noqa: BLE001 — fail-open per audit_emit contract
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            import traceback
            traceback.print_exc(file=sys.stderr)


def _emit_ceo_boot_check_skipped_safe(
    *,
    check_name: str,
    timeout_ms: int,
) -> None:
    """Wire-up to audit_emit.emit_ceo_boot_check_skipped. Fail-open contract."""
    if _audit_emit is None:
        return
    fn = getattr(_audit_emit, "emit_ceo_boot_check_skipped", None)
    if not callable(fn):
        return
    try:
        fn(
            session_id=_ceo_boot_session_id(),
            check_name=check_name,
            timeout_ms=int(timeout_ms),
        )
    except Exception:  # noqa: BLE001 — fail-open
        pass


# === END PLAN-065 Phase 2 audit_emit wire =================================


# === PLAN-078 Wave 5 — TaskCreate-candidate marker emit + dedup ============
# Layer A of the Wave 5 closure (per PLAN-078 §4 + Codex CDX-UNIQUE-02 +
# CDX-P0-03 + CDX-P1-04 + Perf PERF-P1-03). Writes a structured stdout
# marker block per top-3 high/medium recommendation when gate_pass=False,
# dedup'd by 12-hex subject_hash via a 24h TTL state file under
# `_lib/filelock`. The Claude orchestrator running /ceo-boot reads the
# marker blocks and invokes TaskCreate; this script never touches the
# TaskCreate harness primitive directly. Audit emit goes through
# `audit_emit.emit_ceo_boot_task_candidate_emitted` (hasattr-guarded
# pre-canonical-ceremony per the W5 staging→canonical model).

# Default state path lives under the same project state dir as the cache
# (parity with audit-log.jsonl). Override `CEO_BOOT_TASK_STATE_PATH` for
# tests. Format: {"entries": [{"subject_hash": "...", "ts": <epoch>}, ...]}
# bounded to 256 entries (LRU evict on overflow).
TASK_EMIT_STATE_PATH_DEFAULT = (
    Path.home()
    / ".claude" / "projects" / "ceo-orchestration"
    / "state" / "ceo-boot-tasks-emitted.json"
)
TASK_EMIT_TTL_S = 24 * 60 * 60          # 24h dedup window
TASK_EMIT_TOP_N = 3                     # emit at most 3 markers per boot
TASK_EMIT_STATE_MAX_ENTRIES = 256       # bounded state size


def _task_emit_state_path() -> Path:
    """Resolve dedup state-file path at call time (env override-aware)."""
    override = os.environ.get("CEO_BOOT_TASK_STATE_PATH")
    if override:
        return Path(override)
    return TASK_EMIT_STATE_PATH_DEFAULT


def _subject_hash(subject: str) -> str:
    """Return a 12-hex-char prefix of sha256(subject) for dedup bookkeeping.

    The full subject text is NEVER persisted (Sec MF-3); the hash is the
    only stable identifier shared between the audit event and the state
    file. NFKC-normalize first so homoglyph variants collapse to the
    same dedup key (parity with `_sanitize_for_recs`).
    """
    safe = subject if isinstance(subject, str) else str(subject)
    try:
        safe = unicodedata.normalize("NFKC", safe)
    except (TypeError, ValueError):  # pragma: no cover — defensive
        pass
    digest = hashlib.sha256(safe.encode("utf-8", errors="replace")).hexdigest()
    return digest[:12]


def _load_task_emit_state(path: Path) -> Dict[str, Any]:
    """Load dedup state, prune entries older than TASK_EMIT_TTL_S.

    Fail-open: corrupt JSON / unreadable file → returns empty state. The
    caller persists the pruned state on next write so corruption is
    self-healing across boots.

    Codex CDX-W5-P1-04 closure: drop entries with non-finite timestamps
    (NaN / inf) and entries with timestamps in the future (NTP jump
    backward, deliberate clock skew). The TTL window is `[0, TTL)` —
    age must be a finite non-negative number strictly less than the
    TTL bound.
    """
    if not path.exists():
        return {"entries": []}
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return {"entries": []}
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return {"entries": []}
    now = time.time()
    pruned: List[Dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        ts = entry.get("ts")
        sh = entry.get("subject_hash")
        if not isinstance(sh, str) or not isinstance(ts, (int, float)):
            continue
        # Reject NaN / inf — float comparison NaN!=NaN always; inf age
        # would otherwise be retained as TTL-current.
        ts_f = float(ts)
        if ts_f != ts_f or ts_f in (float("inf"), float("-inf")):
            continue
        age = now - ts_f
        if 0 <= age < TASK_EMIT_TTL_S:
            pruned.append({"subject_hash": sh[:12], "ts": ts_f})
    # Bound state size — LRU keep most-recent.
    if len(pruned) > TASK_EMIT_STATE_MAX_ENTRIES:
        pruned.sort(key=lambda e: e["ts"], reverse=True)
        pruned = pruned[:TASK_EMIT_STATE_MAX_ENTRIES]
    return {"entries": pruned}


def _save_task_emit_state(path: Path, state: Dict[str, Any]) -> None:
    """Persist state atomically via temp-file + rename. Fail-open.

    Codex CDX-W5-P1-03 closure: `os.replace` is atomic but not
    crash-durable on macOS — if the box loses power between the rename
    and the buffer flush, the dedup record is lost. We `fsync(tmp_fd)`
    before the rename and best-effort `fsync` the parent directory after.
    Both fsyncs are wrapped — fsync failure must NOT block the user
    session (the dedup is advisory; over-emitting once on crash is
    acceptable, lost-update is not).
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(state, separators=(",", ":")).encode("utf-8")
    try:
        # Write + fsync the data file before atomic rename.
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            os.write(fd, payload)
            try:
                os.fsync(fd)
            except OSError:  # pragma: no cover — fsync best-effort
                pass
        finally:
            os.close(fd)
        os.replace(str(tmp), str(path))
        # Best-effort fsync of the parent directory so the rename
        # itself is durable. POSIX-only; NotImplementedError on win.
        try:
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            except OSError:  # pragma: no cover
                pass
            finally:
                os.close(dir_fd)
        except OSError:  # pragma: no cover — directory fsync optional
            pass
    except OSError:
        # Best-effort cleanup of the tmp file
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:  # pragma: no cover
            pass


def _is_subject_recent(state: Dict[str, Any], subject_hash: str) -> bool:
    """Return True if `subject_hash` is in state within TTL (already pruned by load)."""
    for entry in state.get("entries", []):
        if isinstance(entry, dict) and entry.get("subject_hash") == subject_hash:
            return True
    return False


# Codex CDX-W5-P1-05 closure: collapse interior whitespace in a marker
# subject so the `Subject:` line stays single-line. `_sanitize_for_recs`
# strips angle brackets + backticks but preserves `\n` / `\t` / multi-
# space, which can ambiguate the `<!-- /TASKCREATE-CANDIDATE -->`
# closing marker if a recommendation summary contains a literal newline.
# Bound to 200 chars (parity with `_sanitize_for_recs` length cap).
def _collapse_marker_subject(text: str) -> str:
    """Single-line, length-bounded subject for `Subject:` marker line.

    Python `re.sub(r"\\s+", " ", ...)` on a `str` matches Unicode
    whitespace (NBSP / em-space / narrow NBSP / line-tab / vertical-tab /
    form-feed in addition to ASCII), so the collapse is locale-safe.
    """
    if not isinstance(text, str):
        text = str(text)
    # Replace ALL whitespace runs (Unicode-aware) with a single space.
    text = re.sub(r"\s+", " ", text).strip()
    return text[:200]


def _emit_task_candidate_safe(
    *,
    rank: int,
    severity: str,
    subject_hash: str,
    awaiting_confirm: bool = False,
) -> None:
    """Wire-up to audit_emit.emit_ceo_boot_task_candidate_emitted. Fail-open.

    Pre-canonical-ceremony: hasattr() returns False, function is a no-op.
    Post-ceremony: emits the telemetry event with Sec MF-3 field allowlist
    enforced on the emit side (subject text NEVER leaves this script).
    """
    if _audit_emit is None:
        return
    fn = getattr(_audit_emit, "emit_ceo_boot_task_candidate_emitted", None)
    if not callable(fn):
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            sys.stderr.write(
                "# ceo-boot: audit_emit.emit_ceo_boot_task_candidate_emitted "
                "not registered (canonical ceremony pending)\n"
            )
        return
    try:
        fn(
            session_id=_ceo_boot_session_id(),
            rank=int(rank),
            severity=str(severity),
            subject_hash=str(subject_hash),
            awaiting_confirm=bool(awaiting_confirm),
        )
    except Exception:  # noqa: BLE001 — fail-open per audit_emit contract
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            import traceback
            traceback.print_exc(file=sys.stderr)


def _emit_task_candidate_markers(
    results: List[CheckResult],
    *,
    gate_pass: bool,
    short: bool,
    cached: bool,
) -> List[Dict[str, Any]]:
    """Write `<!-- TASKCREATE-CANDIDATE -->` blocks to stdout for top-3 recs.

    Layer A of PLAN-078 Wave 5. Bypass paths (return [] without emit):
        * `gate_pass` is True (no actionable failure)
        * `short` mode (≤2s budget — skip per Perf table)
        * `cached` mode (handled by uncached path on next non-cached boot)
        * Env `CEO_BOOT_AUTO_TASK=0` (operator opt-out)
        * No medium/high recommendations after dedup

    Returns the list of marker payloads emitted (used by tests + future
    JSON renderer). Each payload carries `rank`, `severity`,
    `subject_hash`, `subject` (not persisted — only stdout), and
    `awaiting_confirm`.

    Sec MF-3 closure: `subject` text passes through `_sanitize_for_recs`
    (already applied by `_recommendations_with_severity` callee) before
    rendering; only the 12-hex `subject_hash` is persisted to the
    audit-log + dedup state. Raw stderr / check detail NEVER appears in
    the marker block.
    """
    if gate_pass:
        return []
    if short or cached:
        return []
    if os.environ.get("CEO_BOOT_AUTO_TASK") == "0":
        return []

    triples = _recommendations_with_severity(results)
    # Codex CDX-W5-P1-01 closure: do NOT pre-slice to TASK_EMIT_TOP_N
    # before dedup. Iterate the full medium+/high actionable list and
    # break only after we've emitted TOP_N markers — otherwise three
    # already-deduped subjects at the head of the list would silently
    # block any 4th candidate from ever surfacing.
    actionable = [(t, s) for (_, t, s) in triples if s in ("medium", "high")]
    if not actionable:
        return []

    state_path = _task_emit_state_path()
    lock_path = state_path.with_suffix(state_path.suffix + ".lock")

    # Acquire filelock for read-modify-write of dedup state. Codex
    # CDX-W5-P1-02 closure: on FileLockTimeout we still emit markers
    # (fail-open — better to over-task once than silently drop) but we
    # do NOT persist the new state. Persisting unlocked state can
    # clobber a sibling process that just acquired the lock and wrote
    # different entries (lost-update). Operator pays the price of one
    # duplicate marker on the next boot in exchange for not corrupting
    # the audit-bookkeeping channel.
    #
    # Codex CDX-W5-iter3-P1 closure: any exception during lock acquisition
    # (OSError on bad path, PermissionError, NotImplementedError on
    # non-POSIX, etc.) used to fall through the OUTER except and silently
    # suppress every marker. We now narrow the lock-acquire try/except to
    # just lock setup; the marker-emit loop runs unconditionally with
    # `lock_acquired = False` if anything went wrong.
    emitted: List[Dict[str, Any]] = []
    rank = 0
    lock_acquired = False
    state: Dict[str, Any] = {"entries": []}
    lock_ctx = None

    # --- Phase 1: try to acquire the lock + load state ---
    try:
        try:
            from _lib.filelock import FileLock, FileLockTimeout
        except Exception:  # noqa: BLE001 — pre-canonical or import-broken
            FileLock = None  # type: ignore[assignment]
            FileLockTimeout = Exception  # type: ignore[assignment]

        if FileLock is None:
            # No filelock available (pre-canonical / non-POSIX). Read
            # state opportunistically; allow persistence (best-effort).
            state = _load_task_emit_state(state_path)
            lock_acquired = True  # treat as "owned" for save semantics
        else:
            try:
                lock_ctx = FileLock(str(lock_path), timeout=2.5)
                lock_ctx.__enter__()
                state = _load_task_emit_state(state_path)
                lock_acquired = True
            except FileLockTimeout:
                # Lock contended — emit unlocked, skip persist.
                state = _load_task_emit_state(state_path)
                lock_ctx = None
                lock_acquired = False
            except Exception:  # noqa: BLE001 — invalid path, perm err, etc.
                # Any other error during lock acquisition — emit
                # unlocked, skip persist. Empty state means we may
                # over-emit (no dedup), but that's better than silent
                # suppression.
                state = {"entries": []}
                lock_ctx = None
                lock_acquired = False
                if os.environ.get("CEO_BOOT_DEBUG") == "1":
                    import traceback
                    traceback.print_exc(file=sys.stderr)
    except Exception:  # noqa: BLE001 — never let phase-1 abort markers
        state = {"entries": []}
        lock_ctx = None
        lock_acquired = False
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            import traceback
            traceback.print_exc(file=sys.stderr)

    # --- Phase 2: emit markers + persist (always runs, even after
    # phase-1 failure). Wrapped in its own try/except so any state-file
    # bug NEVER blocks the user session. ---
    try:
        now = time.time()
        for text, severity in actionable:
            # Codex CDX-W5-P1-05 closure: collapse interior whitespace
            # so the `Subject:` line stays single-line — newlines in a
            # recommendation summary would otherwise ambiguate the
            # closing marker for the orchestrator parser.
            safe_subject = _collapse_marker_subject(text)
            # Codex CDX-W5-iter2-P1 closure: hash the COLLAPSED subject
            # (the bytes the orchestrator actually parses + re-hashes
            # for dedup against the live task list). Hashing the raw
            # pre-collapse text would break the contract documented in
            # `commands/ceo-boot.md:Step 4.5` where the orchestrator
            # computes `sha256(NFKC(visible Subject))[:12]`.
            sh = _subject_hash(safe_subject)
            if _is_subject_recent(state, sh):
                continue
            rank += 1
            payload = {
                "rank": rank,
                "severity": severity,
                "subject_hash": sh,
                "subject": safe_subject,
                "awaiting_confirm": False,
            }
            sys.stdout.write(
                f"\n<!-- TASKCREATE-CANDIDATE rank={rank} "
                f"severity={severity} awaiting_confirm=false -->\n"
            )
            sys.stdout.write(f"Subject: {safe_subject}\n")
            sys.stdout.write("<!-- /TASKCREATE-CANDIDATE -->\n")
            state["entries"].append({"subject_hash": sh, "ts": now})
            emitted.append(payload)
            _emit_task_candidate_safe(
                rank=rank,
                severity=severity,
                subject_hash=sh,
                awaiting_confirm=False,
            )
            if rank >= TASK_EMIT_TOP_N:
                break
        # Codex CDX-W5-iter3 P2: keep state size bound after the post-load
        # append (load trims to MAX_ENTRIES, but we just added up to TOP_N
        # entries on top — re-cap before save so persisted state never
        # exceeds the documented MAX). LRU keep most-recent.
        entries = state.get("entries", [])
        if isinstance(entries, list) and len(entries) > TASK_EMIT_STATE_MAX_ENTRIES:
            entries.sort(key=lambda e: e.get("ts", 0), reverse=True)
            state["entries"] = entries[:TASK_EMIT_STATE_MAX_ENTRIES]
        if emitted and lock_acquired:
            _save_task_emit_state(state_path, state)
    except Exception:  # noqa: BLE001 — fail-open: a state-file bug must
        # NEVER block the user session
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            import traceback
            traceback.print_exc(file=sys.stderr)
    finally:
        if lock_ctx is not None:
            try:
                lock_ctx.__exit__(None, None, None)
            except Exception:  # pragma: no cover — fail-open
                pass
    return emitted


# === END PLAN-078 Wave 5 marker emit + dedup ===============================


# ---- Main ------------------------------------------------------------------

# === PLAN-134 W4 — Morning Ledger renderer ================================
# Renders the proposal-queue ledger (sign / don't sign / why, founder
# language) as an extra default-mode section — same pattern as the Wave 5
# TASKCREATE markers: NOT a Tier-S check (the registry is pinned at 20),
# never affects gate_pass, fail-open on any error. Fast mode only
# (manifest-level Merkle re-derivation); byte-level verification belongs to
# morning-ceremony.py. Kill switch: CEO_BOOT_LEDGER=0.
def _render_morning_ledger_safe() -> str:
    if os.environ.get("CEO_BOOT_LEDGER", "1") == "0":
        return ""
    try:
        import importlib.util as _ilu
        _ml_path = Path(__file__).resolve().parent / "morning_ledger.py"
        if not _ml_path.is_file():
            return ""
        _ml = sys.modules.get("morning_ledger")
        if _ml is None:
            _spec = _ilu.spec_from_file_location("morning_ledger", _ml_path)
            _ml = _ilu.module_from_spec(_spec)
            # py3.9 dataclasses + `from __future__ import annotations`
            # resolve field types via sys.modules[cls.__module__] — the
            # module MUST be registered before exec_module.
            sys.modules["morning_ledger"] = _ml
            _spec.loader.exec_module(_ml)  # type: ignore[union-attr]
        if not _ml.pending_bundles():
            return ""
        rendered = _ml.render_ledger(deep=False)
        # Defense-in-depth: ledger text is disk-sourced — pass each line
        # through the same sanitizer the recommendations use (Sec MF-4).
        safe_lines = [_sanitize_for_recs(ln) if ln.strip() else ln for ln in rendered.splitlines()]
        return "\n" + "\n".join(safe_lines) + "\n"
    except Exception:  # noqa: BLE001 — advisory section, never block boot
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            import traceback
            traceback.print_exc(file=sys.stderr)
        return ""


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="ceo-boot session-boot autopilot")
    parser.add_argument("--short", action="store_true", help="terse output (≤15 lines target)")
    parser.add_argument("--cached", action="store_true", help="prefer cache-hit (≤200ms budget)")
    parser.add_argument("--bench", action="store_true", help="run N=5 bench harness (markdown table)")
    parser.add_argument("--bench-n", type=int, default=5, help="bench N runs (default 5)")
    parser.add_argument("--bench-json", action="store_true", help="emit bench report as JSON instead of markdown")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON digest")
    parser.add_argument("--verbose", action="store_true", help="include 10 Tier-A checks (~10s budget)")
    args = parser.parse_args(argv)

    # Codex S82 P1 fix: --short defaults to cached path per spec
    # (.claude/commands/ceo-boot.md:12 "--short defaults cached mode").
    # Was running full dispatch ignoring cache.
    if args.short and not args.cached:
        args.cached = True

    if args.bench:
        report = bench(args.bench_n, include_tier_a=args.verbose)
        if args.bench_json or args.json:
            sys.stdout.write(json.dumps(report, indent=2))
            sys.stdout.write("\n")
        else:
            sys.stdout.write(render_bench_markdown(report))
        return 0

    t0 = time.perf_counter()

    if args.cached:
        hit, payload = cached_load()
        elapsed = (time.perf_counter() - t0) * 1000
        if hit:
            if args.json:
                sys.stdout.write(json.dumps(payload, indent=2))
            else:
                sys.stdout.write(f"\n## /ceo-boot --cached HIT ({elapsed:.0f} ms)\n")
                for r in payload["results"]:
                    sys.stdout.write(f"- {r['name']}: {r['status']} — {r['summary']}\n")
            # PLAN-065 Phase 2 wire — cache-hit path. Replay the cached
            # gate_pass/checks_total summary so adopter telemetry counts
            # cached invocations (Reality-Ledger fixture #4 closure).
            cached_failed = sum(
                1 for r in payload.get("results", [])
                if r.get("status") in ("red", "error", "timeout")
            )
            cached_total = len(payload.get("results", []))
            _emit_ceo_boot_emitted_safe(
                gate_pass=(cached_failed == 0),
                duration_ms=int(elapsed),
                checks_total=cached_total,
                checks_failed=cached_failed,
                cache_hit=True,
            )
            return 0
        else:
            sys.stderr.write(f"# cache-miss ({elapsed:.0f} ms) — falling back to full digest\n")

    results = dispatch_parallel(include_tier_a=args.verbose)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    cached_store(results)

    # Aggregate gate semantics: gate_pass = no red/error/timeout
    failed = sum(1 for r in results if r.status in ("red", "error", "timeout"))
    gate_pass = (failed == 0)

    if args.json:
        out = {
            "elapsed_ms": elapsed_ms,
            "gate_pass": gate_pass,
            "checks_total": len(results),
            "checks_failed": failed,
            "recommendations": _make_recommendations(results),
            "results": [
                {"name": r.name, "status": r.status, "summary": r.summary, "duration_ms": r.duration_ms}
                for r in results
            ],
        }
        sys.stdout.write(json.dumps(out, indent=2))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_digest(results, short=args.short))
        sys.stdout.write(f"\nWall-clock: {elapsed_ms:.0f} ms (gate_pass={gate_pass}, failed={failed}/{len(results)})\n")
        # PLAN-134 W4 — Morning Ledger section (default full mode only;
        # --short keeps its 5-line budget). Empty string when queue is
        # empty, module missing, or CEO_BOOT_LEDGER=0.
        if not args.short:
            sys.stdout.write(_render_morning_ledger_safe())

    # PLAN-078 Wave 5 — TaskCreate-candidate markers. Bypass paths handled
    # inside `_emit_task_candidate_markers`: gate_pass=True, --short,
    # --cached, env CEO_BOOT_AUTO_TASK=0, no medium+/high recs after
    # 24h-TTL dedup. Markers go to stdout (parsed by Claude orchestrator
    # running /ceo-boot per `commands/ceo-boot.md` workflow). Audit emit
    # of `ceo_boot_task_candidate_emitted` is invoked per-marker via
    # `_emit_task_candidate_safe` (hasattr-guarded pre-canonical-ceremony).
    # JSON mode skips marker emit so machine consumers see only the JSON
    # payload; switch to default markdown mode to surface markers.
    if not args.json:
        _emit_task_candidate_markers(
            results,
            gate_pass=gate_pass,
            short=args.short,
            cached=args.cached,
        )

    # PLAN-065 Phase 2 wire — uncached path. Emits gate_pass + counts
    # only (Sec MF-3 field allowlist denies tokens/cost/paths/prompt/SKILL/env).
    _emit_ceo_boot_emitted_safe(
        gate_pass=gate_pass,
        duration_ms=int(elapsed_ms),
        checks_total=len(results),
        checks_failed=failed,
        cache_hit=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
