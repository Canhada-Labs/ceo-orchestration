"""Extracted ceo-boot declarations executed by the facade."""
from __future__ import annotations

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
    _rp.runtime_state_dir() / "audit-log.jsonl"
)
# Legacy single-file cache (kept for backward compat with S82 MVP).
CACHE_FILE_DEFAULT = (
    _rp.runtime_state_dir() / "cache" / "ceo-boot-digest.json"
)
# PLAN-065 §4.3.2 real cache directory — keyed by (HEAD + audit-log mtime + size).
# Default lives under project state dir so it is excluded from git via
# ~/.claude/projects layout (parity with audit-log.jsonl). Override via env
# CEO_BOOT_CACHE_DIR for tests.
CACHE_DIR_DEFAULT = (
    _rp.runtime_state_dir() / "state" / "ceo-boot-cache"
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

# S361 (PLAN-194 L2-d) — the ONE time budget of `scheduled_workflows_red`.
# Until S360 three constants described the same budget (3.5 s gh timeout,
# 3.8 s check deadline, 4.0 s soft override) and drifted apart; now the
# soft override below, the check's own deadline and every per-workflow gh
# call derive from this value (see _sched_red_budget_s).
SCHED_RED_BUDGET_S = 4.0

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
    # PLAN-153 Wave E item 2 — streaming audit-log read over a 7d window
    # (same class as dispatch_count_24h / skill_unknown_ratio).
    "failopen_rail_liveness_7d": 1.5,
    # PLAN-153 Wave E item 1 wire — subprocess-bound (python3 spawn of the
    # E1 gate; subprocess timeout 2.5s default, see
    # _harness_config_gate_timeout_s).
    "harness_config_gate": 3.0,
    # S292 — network-bound (S361: one gh call per scheduled workflow, in
    # parallel, all inside the single SCHED_RED_BUDGET_S).
    "scheduled_workflows_red": SCHED_RED_BUDGET_S,
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


# PLAN-165 NF-07 (2026-08-03) — every character Python's own
# `str.splitlines()` treats as a line boundary, plus TAB. Written as ESCAPES
# on purpose: a literal U+2028 in the source is invisible.
_RECS_LINE_BREAKS = "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029\t"
_RECS_ONE_LINE_TABLE = {ord(ch): " " for ch in _RECS_LINE_BREAKS}


def _sanitize_for_recs(s: str) -> str:
    """Sanitize a disk-sourced string before recommendation rendering (Sec MF-4).

    Pipeline (deterministic, applied in order):

    1. Coerce non-str → str.
    2. Strip NUL bytes (defense vs. accidental binary in audit-log).
    3. NFKC normalize (PLAN-065 Sec MF-4 — collapse homoglyph escapes:
       fullwidth, ligatures, mathematical alphanumerics).
    4. Collapse every line-boundary character (and TAB) to a single space
       (PLAN-165 NF-07, 2026-08-03). Recommendations render one per line
       (``f"{i}. {rec}"``), so a rec carrying a newline became TWO digest
       lines — the second one arbitrary text in the surface the Owner reads
       at boot. Verified end to end: a planted night-mode marker field
       produced a forged ``- [OK] night-mode: DISARMED, posture is the
       ratified manual`` line directly under the true line saying the
       opposite. This step is deliberately INSIDE the shared sanitizer, not
       at the night-mode call site: EVERY rec consumer echoes disk-sourced
       text (check summaries, audit-log classes, stale-plan names), so the
       fix belongs where they all pass. Runs BEFORE the bound (the bound
       must apply to the final string) and BEFORE the scan (a pattern split
       across a line break becomes visible to the scanner).
    5. Length-bound to 200 chars (post-NFKC; NFKC may expand a few code
       points but bound applies to final rendered string).
    6. injection_patterns scan; substitute [REDACTED-INJECTION-PATTERN] on hit.
    7. Strip HTML angle brackets + markdown link URL + backticks (defensive
       belt-and-suspenders if patterns library missed a variant).

    Note this is a COLLAPSE, not a rejection: recs are advisory text and the
    boot digest must never be blocked by unexpected input (fail-open on
    infrastructure). Callers that need fail-CLOSED rejection of a line break
    do it on the RAW text before calling here — see
    `_validate_boot_lesson`'s bounded-vocabulary gate (A5).
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
    # NF-07 (2026-08-03): line-break collapse — post-NFKC, pre-bound,
    # pre-scan (see step 4 of the docstring pipeline).
    s = s.translate(_RECS_ONE_LINE_TABLE)
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
    # Subprocess: git log --since=24h --name-only + subjects.
    # S314: o stem completo era um proxy que perdia atividade real —
    # commits que tocam so `.claude/plans/PLAN-NNN/...` (o diretorio de
    # artefatos) ou que carregam o id no subject nao continham o stem, e
    # um plano ativissimo (cerimonia GPG 20h antes) saia como stranded.
    # O casamento agora aceita tambem o prefixo `PLAN-NNN` contra paths
    # E contra subjects de commit (`--pretty=format:%s`).
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "log", "--since=24 hours ago", "--name-only", "--pretty=format:%s"],
            capture_output=True, text=True, timeout=2.0,
        )
        touched = {line.strip() for line in proc.stdout.splitlines() if line.strip()}
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "yellow", "git unavailable", None
    # Cross-ref against executing plans
    executing_status, _, executing_list = check_plans_executing()

    def _saw_activity(plan: str) -> bool:
        m = re.match(r"^(PLAN-\d{3})(?!\d)", plan)
        prefix = m.group(1) if m else plan
        return any(plan in t or prefix in t for t in touched)

    # S361 (PLAN-194 L2-g): a plan with no commit in 24 h that DECLARES what it
    # is waiting for (`external_wait`, or the `## Blockers` leaf of
    # PLAN-SCHEMA §12) is waiting, not stranded — it was red on every boot.
    # Detail stays the list of STRANDED stems (the recommendations contract).
    by_stem = {p.stem: p for p in _get_plan_paths()}
    stranded: List[str] = []
    waiting: List[str] = []
    for plan in executing_list:
        if _saw_activity(plan):
            continue
        (waiting if _plan_declares_wait(by_stem.get(plan)) else stranded).append(plan)
    note = (
        f"; {len(waiting)} waiting on a declared wait "
        f"(external_wait / ## Blockers): {', '.join(waiting)}"
        if waiting else ""
    )
    summary = _sanitize_for_recs(f"{len(stranded)} stranded{note}")[:200]
    if stranded:
        return "red", summary, stranded
    return ("yellow" if waiting else "green"), summary, stranded


# Values that DECLARE no wait. Anything else counts as a declared wait; a
# misread therefore keeps the plan red (the pre-S361 behaviour), never hides it.
_NO_WAIT_TOKENS = frozenset({
    "", "none", "nenhum", "nenhuma", "nada", "n/a", "na", "null", "~", "-",
    "—", "no", "não", "nao", "[]",
})


def _declares_wait(value: str) -> bool:
    """True when one `external_wait` value / Blockers line names a wait."""
    v = value.strip()
    # A quoted YAML scalar ends at its closing quote; anything after it (a
    # `# comment`) is not part of the value. Unquoted: drop a trailing
    # ` # comment` (YAML needs the space before `#`).
    quoted = re.match(r"""^(["'])(.*?)\1""", v)
    v = quoted.group(2) if quoted else re.sub(r"\s+#.*$", "", v)
    v = re.sub(r"^[-*+]\s+", "", v.strip())
    # A Markdown leaf label (`**Leaf:** none`, `**Leaf**: none`, `Leaf: none`)
    # names the field, not the wait — judge the value after it.
    v = re.sub(r"^\*\*[^*]{1,40}\*\*\s*:?\s*", "", v)
    v = re.sub(r"^[^\W\d_][\w -]{0,30}:\s+", "", v)
    v = v.strip().strip("\"'").strip()
    first = re.split(r"[\s,;:.()]+", v.lower(), maxsplit=1)[0] if v else ""
    return first not in _NO_WAIT_TOKENS


def _plan_declares_wait(path: Optional[Path]) -> bool:
    """`external_wait` (frontmatter) or a `## Blockers` body section declares
    a wait (PLAN-SCHEMA §3 / §12). Unreadable plan ⇒ False (stays red)."""
    if path is None:
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if fm:
        lines = fm.group(1).splitlines()
        for i, line in enumerate(lines):
            m = re.match(r"^external_wait\s*:\s*(.*)$", line)
            if not m:
                continue
            rest = m.group(1).strip()
            if rest and rest not in ("|", ">", "|-", ">-"):
                if rest.startswith("[") and rest.endswith("]"):
                    values = rest[1:-1].split(",")
                else:
                    values = [rest]
            else:  # block list / block scalar on the following lines
                values = []
                for nxt in lines[i + 1:]:
                    if nxt.strip() and not (nxt[:1].isspace() or nxt.startswith("-")):
                        break
                    values.append(nxt)
            if any(_declares_wait(v) for v in values if v.strip()):
                return True
            break
    body = text[fm.end():] if fm else text
    in_fence = False
    in_section = False
    for line in body.splitlines():
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            continue
        if in_fence and not in_section:
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading and not in_fence:
            if in_section and len(heading.group(1)) <= 2:
                break
            if len(heading.group(1)) == 2 and re.match(
                r"(?i)blockers\b", heading.group(2).strip()
            ):
                in_section = True
            continue
        if in_section and line.strip() and _declares_wait(line):
            return True
    return False


# CEO-INFORMATIONAL-ONLY: contador de drafts sem limiar de acao (PLAN-178 C3)
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
        # rail r14: cascata da familia — com CEO_AUDIT_LOG_PATH setado os
        # escritores poem o breadcrumb ao lado do log MOVIDO; ler do
        # default perderia exatamente esses erros.
        _lp = os.environ.get("CEO_AUDIT_LOG_PATH")
        if _lp:
            try:
                errors_path = Path(_lp).resolve().parent / "audit-log.errors"
            except OSError:
                errors_path = AUDIT_LOG_DEFAULT.parent / "audit-log.errors"
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


# CEO-INFORMATIONAL-ONLY: pulso de despachos/24h, sem limiar (PLAN-178 C3)
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
    # Re-pass rc.4 t3 (P1): RETIRED with the same rationale as the S303
    # harness-probe exemption — every condition here is ABSENCE, and
    # desc_hash == SHA256("") corroborates nothing (it derives from the
    # same empty caller-controlled description). A real markerless spawn
    # with an empty description — e.g. one a fail-open PreToolUse hook
    # admitted — matched all four and was deleted from the denominator.
    # Ghost-shaped rows COUNT until the emitter can stamp provenance the
    # caller cannot forge.
    return False
