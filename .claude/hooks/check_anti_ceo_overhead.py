#!/usr/bin/env python3
"""PreToolUse hook: detect + advise on CEO-overhead anti-patterns.

PLAN-083 Wave 0a sub-agent 0.5 deliverable. Enforces the Owner velocity
thesis (pinned memory ``feedback_owner_velocity_thesis.md``): if the CEO
is doing work that a sub-agent (Sonnet/Haiku) would do equally well,
dispatch is mandatory.

## What this hook does

Watches CEO tool calls (Read / Edit / Write / Bash with grep|find) and
maintains a sliding 5-minute window of recent events in a state file at
``~/.claude/projects/<proj>/state/ceo-overhead-window.json``. When the
window crosses a bounded predicate threshold, the hook emits an
``anti_ceo_overhead_block`` audit event AND returns a
``systemMessage`` recommending sub-agent dispatch.

**Detection is BLOCKING** (decision: block) when an anti-pattern fires,
UNLESS the override env var ``CEO_OVERHEAD_ACK=1`` is set or the daily
emit budget has been exhausted (≥20/day -> degrade to allow + advisory
systemMessage; never silent).

## Bounded predicates (R1 P0-3 + TDE P0-4)

Predicates are intentionally narrow to keep FPR ≤5% (Sec MF-7 target):

P1. **Sequential SKILL.md reads**: ≥3 Read events targeting
    ``.claude/skills/**/SKILL.md`` (distinct files) within 5min.
    Recommendation: dispatch one ``general-purpose`` sub-agent to
    read+synthesize.

P2. **Unrelated file edits**: ≥3 Edit/Write events on files whose
    canonical parent directories have no shared 2-level prefix, within
    5min. Recommendation: split into N=count parallel sub-agents.

P3. **Schema/config serial authoring**: ≥2 Edit/Write events on
    ``.json|.yaml|.yml|.schema.json|.toml`` files within 5min where
    file paths are unrelated (no shared 2-level prefix).
    Recommendation: dispatch one sub-agent per config artifact.

P4. **Independent grep/find spam**: ≥4 Bash invocations whose command
    starts with ``grep|find|rg|ag`` (token-0 match) within 5min, on
    distinct query strings (jaccard similarity on tokens <0.5).
    Recommendation: dispatch one ``research`` sub-agent.

P5. **Cross-module test authoring**: ≥3 Write events on files matching
    ``**/test_*.py|**/*.test.{ts,tsx,js,jsx}`` whose canonical parent
    directories differ, within 5min.
    Recommendation: split into N parallel test-author sub-agents.

## Fail-OPEN on infra (Sec P1)

ANY infrastructure error (parse failure, state-file corruption, lock
timeout, missing dir, exception in predicate, audit emit failure) ->
log a stderr breadcrumb + emit ``{"decision":"allow"}``. The Owner
session is NEVER blocked by a hook bug.

## Emit budget ≤20/day (TDE P0-4)

Past 20 ``anti_ceo_overhead_block`` audit events in a rolling 24h
window, the hook **suppresses both the block decision and the audit
emit** for that anti-pattern firing — it still surfaces a
``systemMessage`` advisory so the Owner is informed, but tool action
proceeds (degrade gracefully, never silent).

## Override (Sec P1)

``CEO_OVERHEAD_ACK=1`` short-circuits to allow + emits a separate
``anti_ceo_overhead_override_used`` audit event so override usage is
forensically traceable.

## Output contract

Single-line JSON to stdout:

    {"decision":"allow"}
    {"decision":"allow","systemMessage":"⚠ anti-CEO-overhead ..."}
    {"decision":"block","reason":"GOVERNANCE: anti-CEO-overhead ..."}

Exit code is always 0 — Claude Code reads the decision from stdout.

## Performance budget (Perf P0-3)

p95 latency ≤50ms on the 1000-call bench (see
``bench/before-after.md``). Achieved via:

- single state-file read+write per invocation (no scanning audit log)
- ``bisect`` for window pruning in O(log n)
- ``FileLock`` with 100ms timeout (degrades to no-op on contention)
- pure-stdlib (no imports cost beyond json/os/time/bisect)
"""

from __future__ import annotations

import bisect
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Make _lib importable — hooks/check_anti_ceo_overhead.py + hooks/_lib/.
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib.filelock import FileLock, FileLockTimeout  # noqa: E402
except Exception:  # pragma: no cover — fail-open if _lib unavailable
    FileLock = None  # type: ignore[assignment]
    FileLockTimeout = Exception  # type: ignore[assignment]

try:
    from _lib import audit_emit as _audit_emit  # noqa: E402
    _AUDIT_EMIT_AVAILABLE = True
except Exception:  # pragma: no cover
    _audit_emit = None  # type: ignore[assignment]
    _AUDIT_EMIT_AVAILABLE = False

# PLAN-125 WS-1 — co-locate the cheap per-tool-call PreToolUse lifecycle stamp
# here (this hook already runs PreToolUse on the broad tool set), so we add NO
# new subprocess (MF-PERF-1). The stamp writes ONLY a dedicated per-session
# record file and NEVER emits an audit-chain event (MF-SEC-5 hard KILL).
try:
    from _lib import tool_lifecycle as _tool_lifecycle  # noqa: E402
    _TOOL_LIFECYCLE_AVAILABLE = True
except Exception:  # pragma: no cover
    _tool_lifecycle = None  # type: ignore[assignment]
    _TOOL_LIFECYCLE_AVAILABLE = False


class _PreStampEvent:
    """Minimal NormalizedEvent-shaped carrier for tool_lifecycle.record_pre.

    Only the 3 fields record_pre reads (session_id / tool_use_id / tool_name).
    """

    __slots__ = ("session_id", "tool_use_id", "tool_name")

    def __init__(self, *, session_id: str, tool_use_id: str, tool_name: str) -> None:
        self.session_id = session_id
        self.tool_use_id = tool_use_id
        self.tool_name = tool_name


def _record_pre_lifecycle(payload: Dict[str, Any], session_id: str) -> None:
    """Fail-open PreToolUse lifecycle stamp (PLAN-125 WS-1 / MF-SEC-5).

    NEVER raises, NEVER emits an audit-chain event. A missing tool_use_id is a
    no-op (record_pre returns early). Kill-switch: CEO_TOOL_LIFECYCLE=0.
    """
    if not _TOOL_LIFECYCLE_AVAILABLE or _tool_lifecycle is None:
        return
    if os.environ.get("CEO_TOOL_LIFECYCLE", "").strip().lower() in {
        "0", "false", "off", "no"
    }:
        return
    try:
        ev = _PreStampEvent(
            session_id=session_id,
            tool_use_id=str(payload.get("tool_use_id") or ""),
            tool_name=str(payload.get("tool_name") or ""),
        )
        _tool_lifecycle.record_pre(ev)
    except Exception:
        return


# -----------------------------------------------------------------------------
# Tunables (frozen by design — bounded predicate spec)
# -----------------------------------------------------------------------------

WINDOW_SECONDS = 5 * 60  # 5min sliding window
DAILY_EMIT_BUDGET = 20  # max anti_ceo_overhead_block emits / 24h
EMIT_BUDGET_WINDOW_SECONDS = 24 * 60 * 60
OVERRIDE_ENV_VAR = "CEO_OVERHEAD_ACK"

# Predicate thresholds
P1_SKILL_READ_THRESHOLD = 3        # ≥3 distinct SKILL.md reads / 5min
P2_UNRELATED_EDIT_THRESHOLD = 3    # ≥3 unrelated file edits / 5min
P3_CONFIG_SERIAL_THRESHOLD = 2     # ≥2 config files / 5min
P4_GREP_FIND_THRESHOLD = 4         # ≥4 grep/find / 5min
P5_TEST_AUTHORING_THRESHOLD = 3    # ≥3 cross-module test writes / 5min

# Cap the state window total entries to bound memory + latency
MAX_STATE_ENTRIES = 200

# Patterns
_SKILL_MD_RX = re.compile(r"^|/(\.claude/skills/[^/]+(?:/[^/]+)*?/SKILL\.md)$")
_TEST_FILE_RX = re.compile(
    r"(?:^|/)(?:test_[A-Za-z0-9_]+\.py|[A-Za-z0-9_.-]+\.test\.(?:tsx?|jsx?))$"
)
_CONFIG_FILE_RX = re.compile(
    r"\.(?:json|ya?ml|toml)$"
)
_GREP_FIND_RX = re.compile(r"^\s*(?:grep|find|rg|ag)\b")


# -----------------------------------------------------------------------------
# State store
# -----------------------------------------------------------------------------

def _project_state_dir() -> Path:
    """Return ~/.claude/projects/<proj>/state/, creating if missing.

    Project key derived from CLAUDE_PROJECT_DIR (slug-encoded path).
    Falls back to CWD-derived key if env not set.
    """
    proj_dir = os.environ.get("CLAUDE_PROJECT_DIR") or str(Path.cwd())
    # Mimic Claude Code's project slug: leading '-' + path with '/' -> '-'
    slug = "-" + proj_dir.replace("/", "-")
    base = Path.home() / ".claude" / "projects" / slug / "state"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return base


def _state_path() -> Path:
    return _project_state_dir() / "ceo-overhead-window.json"


def _emit_budget_path() -> Path:
    return _project_state_dir() / "ceo-overhead-emit-budget.json"


def _load_state(path: Path) -> Dict[str, Any]:
    """Load state file. Fail-open empty on any error."""
    if not path.is_file():
        return {"events": []}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or not isinstance(data.get("events"), list):
            return {"events": []}
        return data
    except (OSError, json.JSONDecodeError):
        return {"events": []}


def _save_state(path: Path, state: Dict[str, Any]) -> None:
    """Write state file atomically. Fail-open on any error."""
    try:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False)
        os.replace(str(tmp), str(path))
    except OSError:
        return


def _prune_window(events: List[Dict[str, Any]], now: float) -> List[Dict[str, Any]]:
    """Prune events older than WINDOW_SECONDS via bisect (O(log n)).

    events list is maintained sorted by ts. We rebuild on prune; cap to
    MAX_STATE_ENTRIES to bound disk + memory.
    """
    if not events:
        return events
    # Bisect on the timestamps; assume events sorted by ts ascending
    timestamps = [e.get("ts", 0.0) for e in events]
    cutoff = now - WINDOW_SECONDS
    idx = bisect.bisect_left(timestamps, cutoff)
    pruned = events[idx:]
    if len(pruned) > MAX_STATE_ENTRIES:
        pruned = pruned[-MAX_STATE_ENTRIES:]
    return pruned


def _record_event(state: Dict[str, Any], event: Dict[str, Any], now: float) -> None:
    """Append event to state, keeping events sorted by ts."""
    events = state.setdefault("events", [])
    events.append(event)
    state["events"] = _prune_window(events, now)


# -----------------------------------------------------------------------------
# Emit budget tracking
# -----------------------------------------------------------------------------

def _load_emit_budget(path: Path) -> List[float]:
    """Return list of past anti_ceo_overhead_block emit timestamps (24h)."""
    if not path.is_file():
        return []
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return []
        ts_list = data.get("emit_ts", [])
        if not isinstance(ts_list, list):
            return []
        return [float(t) for t in ts_list if isinstance(t, (int, float))]
    except (OSError, json.JSONDecodeError, ValueError):
        return []


def _save_emit_budget(path: Path, ts_list: List[float]) -> None:
    try:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump({"emit_ts": ts_list}, fh, ensure_ascii=False)
        os.replace(str(tmp), str(path))
    except OSError:
        return


def _check_emit_budget(now: float) -> Tuple[bool, int]:
    """Check + maybe increment emit budget.

    Returns (budget_available, count_in_24h_window).

    If budget_available is True, the caller may emit + the count is now
    incremented. If False, the caller MUST NOT emit (degrade to advisory).
    """
    path = _emit_budget_path()
    ts_list = _load_emit_budget(path)
    cutoff = now - EMIT_BUDGET_WINDOW_SECONDS
    # Prune past-24h emit timestamps
    ts_list = [t for t in ts_list if t >= cutoff]
    count_in_window = len(ts_list)
    if count_in_window >= DAILY_EMIT_BUDGET:
        # Save pruned list back (no increment)
        _save_emit_budget(path, ts_list)
        return False, count_in_window
    ts_list.append(now)
    _save_emit_budget(path, ts_list)
    return True, count_in_window + 1


# -----------------------------------------------------------------------------
# Event classification
# -----------------------------------------------------------------------------

def _classify_event(tool_name: str, tool_input: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Classify a tool event for the sliding window.

    Returns a dict with classification tags or None if the event is
    irrelevant (won't affect any predicate).

    Classification tags (mutually compatible):
      - kind: "read_skill" / "edit_unrelated" / "write_config" /
              "bash_search" / "write_test"
      - file_path / cmd_prefix: minimal forensic key (no content)
      - parent_2: 2-level parent dir for shared-prefix tests
    """
    tn = (tool_name or "").strip()
    if tn == "Read":
        fp = (tool_input.get("file_path") or "").strip()
        if not fp:
            return None
        if _is_skill_md(fp):
            return {
                "kind": "read_skill",
                "file_path": fp,
                "parent_2": _parent_2(fp),
            }
        return None
    if tn in ("Edit", "Write", "MultiEdit"):
        fp = (tool_input.get("file_path") or "").strip()
        if not fp:
            return None
        ev: Dict[str, Any] = {
            "file_path": fp,
            "parent_2": _parent_2(fp),
        }
        # Config + test annotations are non-exclusive; pick most-specific
        if _CONFIG_FILE_RX.search(fp):
            ev["kind"] = "write_config"
            return ev
        if _TEST_FILE_RX.search(fp):
            ev["kind"] = "write_test"
            return ev
        ev["kind"] = "edit_unrelated"
        return ev
    if tn == "Bash":
        cmd = (tool_input.get("command") or "").strip()
        if not cmd:
            return None
        if _GREP_FIND_RX.match(cmd):
            return {
                "kind": "bash_search",
                "cmd_prefix": cmd.split(None, 1)[0] if cmd else "",
                "tokens": _tokenize_cmd(cmd),
            }
        return None
    return None


def _is_skill_md(file_path: str) -> bool:
    """True if path is a SKILL.md under .claude/skills/**."""
    p = file_path.replace("\\", "/")
    if not p.endswith("/SKILL.md"):
        return False
    return ".claude/skills/" in p


def _parent_2(file_path: str) -> str:
    """Return the first two NON-EMPTY path components (canonical-ish key).

    Used to group "shared parent dir" — files with the same 2-level
    parent are considered RELATED (do NOT count as unrelated).
    Leading "/" is stripped so absolute and relative paths normalize.
    Files with fewer than 2 components return their parent dir or "".

    Examples:
      "/repo/src/foo/bar.py" -> "repo/src"
      "/repo/docs/api/x.md"  -> "repo/docs"
      "src/foo/bar.py"       -> "src/foo"
      "README.md"            -> ""
    """
    p = file_path.replace("\\", "/")
    parts = [s for s in p.split("/") if s]
    if len(parts) >= 3:
        return "/".join(parts[:2])
    if len(parts) == 2:
        # File at top-2 level: parent_2 is the single dir
        return parts[0]
    return ""


def _tokenize_cmd(cmd: str) -> List[str]:
    """Tokenize a bash command for jaccard similarity (lowercase, alnum)."""
    raw = cmd.lower().split()
    out = []
    for tok in raw:
        # Drop flags and quoted parts; keep alnum slugs ≥3 chars
        stripped = re.sub(r"[^a-z0-9_]+", " ", tok).split()
        for s in stripped:
            if len(s) >= 3:
                out.append(s)
    return out[:20]  # cap


def _jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# -----------------------------------------------------------------------------
# Predicate evaluation
# -----------------------------------------------------------------------------

def _eval_predicates(events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Evaluate bounded predicates against the windowed events.

    Returns the first predicate that fires (priority P1>P2>P3>P4>P5)
    as a dict ``{anti_pattern_id, count_in_window, override_recommended_subagent_type}``,
    or None if no anti-pattern detected.
    """
    if not events:
        return None

    # P1: ≥3 distinct SKILL.md reads
    skill_reads = [e for e in events if e.get("kind") == "read_skill"]
    distinct_skill_files = {e.get("file_path") for e in skill_reads if e.get("file_path")}
    if len(distinct_skill_files) >= P1_SKILL_READ_THRESHOLD:
        return {
            "anti_pattern_id": "P1_sequential_skill_reads",
            "count_in_window": len(distinct_skill_files),
            "override_recommended_subagent_type": "general-purpose",
        }

    # P2: ≥3 unrelated file edits (parent_2 distinct count)
    edits = [e for e in events if e.get("kind") == "edit_unrelated"]
    if len(edits) >= P2_UNRELATED_EDIT_THRESHOLD:
        parents = {e.get("parent_2") for e in edits if e.get("parent_2")}
        if len(parents) >= P2_UNRELATED_EDIT_THRESHOLD:
            return {
                "anti_pattern_id": "P2_unrelated_file_edits",
                "count_in_window": len(parents),
                "override_recommended_subagent_type": "general-purpose",
            }

    # P3: ≥2 schema/config files unrelated
    configs = [e for e in events if e.get("kind") == "write_config"]
    if len(configs) >= P3_CONFIG_SERIAL_THRESHOLD:
        parents = {e.get("parent_2") for e in configs if e.get("parent_2")}
        if len(parents) >= P3_CONFIG_SERIAL_THRESHOLD:
            return {
                "anti_pattern_id": "P3_config_serial_authoring",
                "count_in_window": len(parents),
                "override_recommended_subagent_type": "general-purpose",
            }

    # P4: ≥4 independent grep/find on distinct queries
    searches = [e for e in events if e.get("kind") == "bash_search"]
    if len(searches) >= P4_GREP_FIND_THRESHOLD:
        # Count distinct queries (jaccard <0.5 in pairwise check)
        distinct_groups: List[List[str]] = []
        for s in searches:
            toks = s.get("tokens", []) or []
            if not toks:
                continue
            attached = False
            for g in distinct_groups:
                if _jaccard(toks, g) >= 0.5:
                    attached = True
                    break
            if not attached:
                distinct_groups.append(toks)
        if len(distinct_groups) >= P4_GREP_FIND_THRESHOLD:
            return {
                "anti_pattern_id": "P4_independent_grep_find_spam",
                "count_in_window": len(distinct_groups),
                "override_recommended_subagent_type": "research",
            }

    # P5: ≥3 cross-module test writes
    tests = [e for e in events if e.get("kind") == "write_test"]
    if len(tests) >= P5_TEST_AUTHORING_THRESHOLD:
        parents = {e.get("parent_2") for e in tests if e.get("parent_2")}
        if len(parents) >= P5_TEST_AUTHORING_THRESHOLD:
            return {
                "anti_pattern_id": "P5_cross_module_test_authoring",
                "count_in_window": len(parents),
                "override_recommended_subagent_type": "general-purpose",
            }

    return None


# -----------------------------------------------------------------------------
# Audit emission (Sec MF-3 whitelist enforced)
# -----------------------------------------------------------------------------

def _safe_emit_block(
    *,
    anti_pattern_id: str,
    count_in_window: int,
    override_recommended_subagent_type: str,
    session_id: str,
) -> None:
    """Emit anti_ceo_overhead_block via emit_generic. Best-effort."""
    if not _AUDIT_EMIT_AVAILABLE:
        return
    try:
        _audit_emit.emit_generic(
            "anti_ceo_overhead_block",
            session_id=session_id,
            anti_pattern_id=anti_pattern_id,
            count_in_window=int(count_in_window),
            override_recommended_subagent_type=override_recommended_subagent_type,
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
        )
    except Exception:
        return


def _safe_emit_override(
    *,
    anti_pattern_id: str,
    session_id: str,
) -> None:
    """Emit anti_ceo_overhead_override_used."""
    if not _AUDIT_EMIT_AVAILABLE:
        return
    try:
        _audit_emit.emit_generic(
            "anti_ceo_overhead_override_used",
            session_id=session_id,
            anti_pattern_id=anti_pattern_id,
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
        )
    except Exception:
        return


# -----------------------------------------------------------------------------
# Decision API (pure, test-friendly)
# -----------------------------------------------------------------------------

def decide(
    *,
    tool_name: str,
    tool_input: Dict[str, Any],
    state: Dict[str, Any],
    now: float,
    override_env: bool = False,
    budget_available: bool = True,
) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]]]:
    """Pure decision function.

    Args:
        tool_name: Claude Code tool name (Read/Edit/Write/Bash/MultiEdit).
        tool_input: tool_input dict from the PreToolUse payload.
        state: window state dict (will be mutated — append + prune).
        now: current unix timestamp (float).
        override_env: True if CEO_OVERHEAD_ACK=1.
        budget_available: True if daily emit budget has headroom.

    Returns:
        Tuple of:
          - decision dict ({"decision": "allow"|"block", optional
            "reason" / "systemMessage"})
          - updated state dict
          - hit predicate result dict (or None) — caller emits audit
    """
    classified = _classify_event(tool_name, tool_input)
    if classified is None:
        return {}, state, None  # schema-compliant allow
    classified["ts"] = now
    _record_event(state, classified, now)
    hit = _eval_predicates(state["events"])
    if hit is None:
        return {}, state, None  # schema-compliant allow

    # Build advisory message
    msg = (
        "⚠ anti-CEO-overhead: predicate "
        f"{hit['anti_pattern_id']} fired "
        f"(count_in_window={hit['count_in_window']}). "
        f"Consider dispatching a '{hit['override_recommended_subagent_type']}' "
        f"sub-agent. Set CEO_OVERHEAD_ACK=1 to ack + proceed."
    )

    if override_env:
        # Allow with audit advisory message — override usage is logged
        # by caller via _safe_emit_override.
        return {"systemMessage": msg + " [override acked]"}, state, hit

    if not budget_available:
        # Degrade gracefully: emit advisory but DO NOT block, DO NOT
        # emit audit (caller respects this).
        return {"systemMessage": msg + " [emit budget exhausted]"}, state, None

    reason = f"GOVERNANCE: anti-CEO-overhead {hit['anti_pattern_id']} fired. {msg}"
    return {"decision": "block", "reason": reason}, state, hit


# -----------------------------------------------------------------------------
# main() — wired to PreToolUse contract
# -----------------------------------------------------------------------------

def _read_stdin_json() -> Optional[Dict[str, Any]]:
    try:
        raw = sys.stdin.read()
    except Exception:
        return None
    if not raw or not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _emit_decision(decision: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(decision, ensure_ascii=False) + "\n")


def _breadcrumb(msg: str) -> None:
    try:
        sys.stderr.write(f"[check_anti_ceo_overhead] {msg}\n")
    except Exception:
        pass


def main() -> int:
    """Entrypoint. Fail-OPEN on every infrastructure error."""
    # 1. Fast kill-switch — let adopters disable globally.
    if os.environ.get("CEO_ANTI_OVERHEAD") == "0":
        _emit_decision({})  # schema-compliant allow
        return 0

    # 2. Parse payload.
    try:
        payload = _read_stdin_json()
    except Exception as e:
        _breadcrumb(f"stdin parse exception: {e}")
        _emit_decision({})  # schema-compliant allow
        return 0
    if payload is None:
        _emit_decision({})  # schema-compliant allow
        return 0

    tool_name = (payload.get("tool_name") or "").strip()
    tool_input = payload.get("tool_input") or {}
    session_id = (payload.get("session_id") or "").strip()

    # PLAN-125 WS-1 — cheap PreToolUse lifecycle stamp for EVERY tool call
    # (fires regardless of the overhead predicates below, and regardless of
    # whether tool_input is a dict). Fail-open + emits no audit-chain event.
    _record_pre_lifecycle(payload, session_id)

    if not isinstance(tool_input, dict):
        _emit_decision({})  # schema-compliant allow
        return 0

    override = os.environ.get(OVERRIDE_ENV_VAR) == "1"

    # 3. State + lock (fail-open on any IO).
    now = time.time()
    state_path = _state_path()
    lock_path = state_path.with_suffix(".json.lock")

    lock_ctx = None
    if FileLock is not None:
        try:
            lock_ctx = FileLock(lock_path, timeout=0.1, poll_interval=0.02)
            lock_ctx.acquire()
        except Exception:
            # Lock timeout / fail — proceed without lock (best-effort).
            lock_ctx = None

    try:
        state = _load_state(state_path)

        # 4. Pre-check emit budget so decide() knows whether to degrade.
        budget_available, _count = _check_emit_budget_dry(now)
        # If override is set, budget is irrelevant (no emit budgeted for
        # block path). We still record override usage below.

        try:
            decision, state, hit = decide(
                tool_name=tool_name,
                tool_input=tool_input,
                state=state,
                now=now,
                override_env=override,
                budget_available=budget_available,
            )
        except Exception as e:
            _breadcrumb(f"decide() exception: {e}")
            _emit_decision({})  # schema-compliant allow
            return 0

        # 5. Persist state (fail-open).
        try:
            _save_state(state_path, state)
        except Exception as e:
            _breadcrumb(f"save_state exception: {e}")

        # 6. Audit emit (after decision is computed).
        if hit is not None:
            if override:
                _safe_emit_override(
                    anti_pattern_id=hit["anti_pattern_id"],
                    session_id=session_id,
                )
            elif decision.get("decision") == "block":
                # Commit budget increment now (block is being emitted).
                _check_emit_budget(now)
                _safe_emit_block(
                    anti_pattern_id=hit["anti_pattern_id"],
                    count_in_window=hit["count_in_window"],
                    override_recommended_subagent_type=hit["override_recommended_subagent_type"],
                    session_id=session_id,
                )

        _emit_decision(decision)
        return 0
    finally:
        if lock_ctx is not None:
            try:
                lock_ctx.release()
            except Exception:
                pass


def _check_emit_budget_dry(now: float) -> Tuple[bool, int]:
    """Read-only budget check (does NOT increment).

    The block-path increment happens in main() after the decision is
    final — so we must dry-read here to inform decide() whether to
    degrade to advisory-only.
    """
    path = _emit_budget_path()
    ts_list = _load_emit_budget(path)
    cutoff = now - EMIT_BUDGET_WINDOW_SECONDS
    ts_list = [t for t in ts_list if t >= cutoff]
    return len(ts_list) < DAILY_EMIT_BUDGET, len(ts_list)


if __name__ == "__main__":
    sys.exit(main())
