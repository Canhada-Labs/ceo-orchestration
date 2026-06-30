#!/usr/bin/env python3
"""PLAN-045 P0-09 (b) — Artifact Paradox advisory SubagentStop hook.

SubagentStop observer that scans the returning sub-agent's output
for **confidence markers** (phrases like "all done", "tests green",
"perfect", "no issues") that indicate potential Artifact Paradox
fluency bias. When N+ markers appear in a short window, emit an
advisory `systemMessage` + `fluency_nudge` audit event so the CEO
applies extra scrutiny rubric (PROTOCOL.md §Artifact Paradox,
pitfall LLM-001 committed Session 42).

## Threshold design

- Short output (< 500 chars): >= 2 markers → nudge
- Medium output (500-5000 chars): >= 4 markers → nudge
- Long output (> 5000 chars): >= 8 markers → nudge

Scales linearly so verbose agents that happen to say "all good"
multiple times as idiomatic filler don't trip on every task.

## Kill-switch

`CEO_FLUENCY_NUDGE=0` short-circuits the fluency scan (allow + no scan).
`CEO_SUBAGENT_LIFECYCLE=0` disables the H3 lifecycle observation below.
With BOTH set to 0 the hook short-circuits before reading stdin.

## PLAN-135 W2 H3 — per-agent lifecycle bracket (SubagentStop half)

This hook ALSO consumes the SubagentStop payload's `agent_transcript_path`
+ the sidecar written by `check_subagent_start.py` to emit ONE
`subagent_lifecycle_observed` audit event per returning agent:

- **wall-time**: stop instant minus the sidecar `start_ts` recorded at
  SubagentStart (sidecar entry is CONSUMED — popped on read);
  `wall_source="unknown"` when the start was never recorded.
- **token bracket**: closed-enum bucket over the SUM of
  `input_tokens + output_tokens + cache_creation_input_tokens +
  cache_read_input_tokens` across the agent transcript's assistant
  messages (the S227 `modelUsage` forensic reconstruction, live).
  RAW token counts are NEVER persisted — bracket only.
- **claim bracket**: closed-enum bucket over the confidence-marker count
  this hook already computes for the Artifact Paradox nudge.

Feeds the persona-ledger via its existing mechanism (stateless audit-log
scan, PLAN-104): the emit carries the persona archetype in `agent_type`,
giving the ledger per-agent completion evidence next to `agent_spawn`.

Transcript-path hardening: `agent_transcript_path` is harness-supplied
but treated as untrusted — it is only read when its realpath is a
`*.jsonl` regular file under `$HOME/.claude` (or under the explicit
`CEO_SUBAGENT_TRANSCRIPT_ROOT` test override); parse is line-bounded
(bytes + lines + wall budget) and only integer usage fields are read.
Observer-only; never blocks; fail-open §5.

## Rationale

Anthropic fluency research + PLAN-034 adversarial-reviewer audit show
polished AI outputs trigger ~5.2 pp less scrutiny for missing context
compared to rough drafts. Same-LLM reviewers inherit the bias — a
polished critique from a sub-agent can signal "done" even when the
review itself missed gaps. This hook surfaces the bias trigger to
the CEO in real time, before the CEO rubber-stamps based on fluency.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Make the local `_lib` importable (matches the pattern of existing hooks).
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

# PLAN-050 Phase 3 C8 — redact-before-emit defense-in-depth.
# Import guarded: if _lib.redact is unavailable during partial rollout
# the hook remains functional with identity redact (fail-open).
try:
    from _lib import redact as _redact  # noqa: E402
    _REDACT_AVAILABLE = True
except Exception:  # pragma: no cover
    _redact = None  # type: ignore[assignment]
    _REDACT_AVAILABLE = False

# PLAN-135 W2 H3 — best-effort sidecar lock (see check_subagent_start.py).
# Import-guarded: lock unavailability degrades to lockless atomic
# tmp+rename (advisory data — never blocks).
try:
    from _lib.filelock import FileLock, FileLockTimeout  # noqa: E402
    _FILELOCK_AVAILABLE = True
except Exception:  # pragma: no cover
    FileLock = None  # type: ignore[assignment]
    FileLockTimeout = Exception  # type: ignore[assignment, misc]
    _FILELOCK_AVAILABLE = False


# --- BEGIN sidecar helpers (PARITY block — mirrored in check_subagent_start.py)
_SIDECAR_FILENAME = "subagent-lifecycle.json"
_SIDECAR_LOCK_FILENAME = "subagent-lifecycle.json.lock"
_SIDECAR_TTL_S = 24 * 3600       # orphaned-start retention
_SIDECAR_MAX_ENTRIES = 512       # hard cap (newest win)
_LOCK_TIMEOUT_S = 0.5            # never stall a spawn on the sidecar


def _state_dir() -> Path:
    """Sidecar directory (output_scan_dedup.py resolution precedent)."""
    override = os.environ.get("CEO_SUBAGENT_LIFECYCLE_STATE_DIR")
    if override:
        return Path(override)
    audit_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if audit_dir:
        return Path(audit_dir)
    home = os.environ.get("HOME") or "/tmp"
    return Path(home) / ".claude" / "projects" / "ceo-orchestration" / "state"


def _sidecar_path() -> Path:
    return _state_dir() / _SIDECAR_FILENAME


def _sidecar_lock_path() -> Path:
    return _state_dir() / _SIDECAR_LOCK_FILENAME


def _agent_key(agent_id: str) -> str:
    """Opaque sidecar key — raw agent_id never lands on disk."""
    return hashlib.sha256(
        agent_id.encode("utf-8", errors="replace")
    ).hexdigest()[:16]


def _load_sidecar(path: Path) -> Dict[str, Any]:
    """Read the sidecar. Returns empty state on any I/O / parse error."""
    if not path.is_file():
        return {"entries": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"entries": {}}
    if not isinstance(data, dict) or not isinstance(data.get("entries"), dict):
        return {"entries": {}}
    return data


def _save_sidecar(path: Path, state: Dict[str, Any]) -> bool:
    """Atomic write via temp-file + rename. Best-effort; never raises."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp.%d" % os.getpid())
        tmp.write_text(
            json.dumps(state, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(str(tmp), str(path))
        return True
    except Exception:
        return False


def _prune_entries(entries: Dict[str, Any], now: float) -> Dict[str, Any]:
    """Drop entries past TTL; keep at most _SIDECAR_MAX_ENTRIES newest."""
    fresh: Dict[str, Any] = {}
    for key, val in entries.items():
        if not isinstance(val, dict):
            continue
        try:
            start_ts = float(val.get("start_ts", 0))
        except (TypeError, ValueError):
            continue
        if now - start_ts <= _SIDECAR_TTL_S:
            fresh[key] = val
    if len(fresh) > _SIDECAR_MAX_ENTRIES:
        ordered = sorted(
            fresh.items(),
            key=lambda kv: float(kv[1].get("start_ts", 0)),
            reverse=True,
        )
        fresh = dict(ordered[:_SIDECAR_MAX_ENTRIES])
    return fresh
# --- END sidecar helpers (PARITY block)


def _lifecycle_breadcrumb(msg: str) -> None:
    sys.stderr.write("# check_fluency_nudge[H3]: %s\n" % msg[:160])


# ---------------------------------------------------------------------------
# PLAN-135 W2 H3 — per-agent lifecycle bracket (SubagentStop half).
#
# Closed-enum buckets — RAW counts NEVER persisted (the bucket is the audit
# signal; the raw wall-time / token sum stays forensic-private, mirroring the
# S227 modelUsage reconstruction). Bucket vocabulary mirrors audit_emit's
# _SUBAGENT_LIFECYCLE_BUCKETS ({none, low, medium, high, very_high, unknown}).
# ---------------------------------------------------------------------------

# Persona-ledger archetypes (the 4 VETO-floor personas, PLAN-093 Wave C.5 +
# PLAN-104 persona-demand). Mirrors audit_emit._SUBAGENT_LIFECYCLE_ARCHETYPES.
# A spawn's free-text agent_type is normalized to one of these (or "other");
# "unknown" is reserved for the no-sidecar-start case.
_ARCHETYPE_TOKENS = frozenset({
    "code-reviewer", "security-engineer", "qa-architect",
    "threat-detection-engineer",
})

# Transcript-parse bounds (untrusted harness-supplied path; observer-only).
_TRANSCRIPT_MAX_BYTES = 8 * 1024 * 1024   # 8 MiB hard read ceiling
_TRANSCRIPT_MAX_LINES = 20_000            # line ceiling
_TRANSCRIPT_WALL_BUDGET_S = 1.5           # never stall the stop on a big file


def _normalize_archetype(agent_type: str) -> str:
    """Map a free-text spawn agent_type to a closed persona archetype token.

    Returns one of `_ARCHETYPE_TOKENS` or "other". The match is on a
    lowercased, hyphen-normalized form so "Security Engineer",
    "security_engineer" and "security-engineer" all map to the same token.
    Anything unrecognized → "other" (never echoed raw — S172 doctrine).
    """
    if not agent_type:
        return "other"
    norm = agent_type.strip().lower().replace("_", "-").replace(" ", "-")
    if norm in _ARCHETYPE_TOKENS:
        return norm
    # Substring fallback for verbose labels ("senior security engineer").
    for tok in _ARCHETYPE_TOKENS:
        if tok in norm:
            return tok
    return "other"


def _wall_bucket(seconds: Optional[float]) -> str:
    """Coarse wall-time bucket (closed enum). None → 'unknown'."""
    if seconds is None:
        return "unknown"
    try:
        s = float(seconds)
    except (TypeError, ValueError):
        return "unknown"
    if s < 0:
        return "unknown"
    if s < 5:
        return "none"          # sub-5s — effectively instant
    if s < 30:
        return "low"
    if s < 120:
        return "medium"
    if s < 600:
        return "high"
    return "very_high"


def _token_bucket(total_tokens: Optional[int]) -> str:
    """Coarse token-sum bucket (closed enum). None → 'unknown'."""
    if total_tokens is None:
        return "unknown"
    try:
        t = int(total_tokens)
    except (TypeError, ValueError):
        return "unknown"
    if t < 0:
        return "unknown"
    if t == 0:
        return "none"
    if t < 10_000:
        return "low"
    if t < 100_000:
        return "medium"
    if t < 1_000_000:
        return "high"
    return "very_high"


def _claim_bucket(marker_count: int) -> str:
    """Coarse confidence-marker (claim) bucket (closed enum)."""
    try:
        c = int(marker_count)
    except (TypeError, ValueError):
        return "unknown"
    if c <= 0:
        return "none"
    if c < 3:
        return "low"
    if c < 6:
        return "medium"
    if c < 12:
        return "high"
    return "very_high"


def _transcript_root() -> Path:
    """Allowed root for transcript reads (untrusted-path containment).

    Default `$HOME/.claude`; an explicit `CEO_SUBAGENT_TRANSCRIPT_ROOT`
    override is used for test isolation. The transcript is read ONLY when its
    realpath is a `*.jsonl` regular file UNDER this root — a harness-supplied
    path pointing at `/etc/passwd` or a symlink-escape is refused.
    """
    override = os.environ.get("CEO_SUBAGENT_TRANSCRIPT_ROOT")
    if override:
        return Path(override).resolve()
    home = os.environ.get("HOME") or "/tmp"
    return (Path(home) / ".claude").resolve()


def _transcript_path_ok(raw_path: str) -> Optional[Path]:
    """Validate the harness-supplied agent_transcript_path. None if unsafe.

    Containment rules (defense-in-depth — the path is untrusted input):
    - non-empty string;
    - realpath is a regular file (not a dir / socket / device);
    - suffix is `.jsonl` (the documented agent-transcript format);
    - realpath is UNDER `_transcript_root()` (symlink-escape refused via
      resolve() on both sides).
    """
    if not raw_path or not isinstance(raw_path, str):
        return None
    try:
        candidate = Path(raw_path).resolve()
    except Exception:
        return None
    if candidate.suffix != ".jsonl":
        return None
    try:
        if not candidate.is_file():
            return None
    except Exception:
        return None
    root = _transcript_root()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _sum_transcript_tokens(path: Path) -> Optional[int]:
    """Sum usage tokens across an agent transcript (.jsonl). None on failure.

    The S227 `modelUsage` reconstruction, live: sums
    `input_tokens + output_tokens + cache_creation_input_tokens +
    cache_read_input_tokens` over every assistant message's `usage` object.
    Bounded by bytes + lines + wall budget; ONLY integer usage fields are
    read (no prompt/content/tool text is touched). Returns the integer sum or
    None when nothing parseable was found (→ token_bucket "unknown").
    """
    deadline = time.monotonic() + _TRANSCRIPT_WALL_BUDGET_S
    total = 0
    saw_usage = False
    bytes_read = 0
    lines_read = 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                lines_read += 1
                bytes_read += len(line)
                if lines_read > _TRANSCRIPT_MAX_LINES:
                    break
                if bytes_read > _TRANSCRIPT_MAX_BYTES:
                    break
                if time.monotonic() > deadline:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if not isinstance(rec, dict):
                    continue
                # Usage can be nested under message.usage (Anthropic
                # stream-json transcript) or a top-level usage object.
                usage = None
                msg = rec.get("message")
                if isinstance(msg, dict) and isinstance(msg.get("usage"), dict):
                    usage = msg["usage"]
                elif isinstance(rec.get("usage"), dict):
                    usage = rec["usage"]
                if usage is None:
                    continue
                for field in (
                    "input_tokens", "output_tokens",
                    "cache_creation_input_tokens", "cache_read_input_tokens",
                ):
                    val = usage.get(field)
                    if isinstance(val, bool):
                        continue  # bool is an int subclass — reject
                    if isinstance(val, int) and val >= 0:
                        total += val
                        saw_usage = True
    except Exception:
        return None
    return total if saw_usage else None


def _consume_start_entry(agent_id: str, now: float) -> Optional[Dict[str, Any]]:
    """Pop (read + delete) this agent's SubagentStart sidecar entry.

    Lock-guarded best-effort. Returns the entry dict (with `start_ts` +
    `agent_type`) or None when the start was never recorded (orphaned start /
    kill-switch at spawn / crashed agent) — the caller then emits
    `wall_source="unknown"`. The pop keeps the sidecar from accumulating a
    consumed start (matched bracket = removed).
    """
    key = _agent_key(agent_id)
    popped: Dict[str, Any] = {}

    def _pop() -> None:
        nonlocal popped
        state = _load_sidecar(_sidecar_path())
        entries = _prune_entries(state.get("entries", {}), now)
        entry = entries.pop(key, None)
        if isinstance(entry, dict):
            popped = entry
            state["entries"] = entries
            if not _save_sidecar(_sidecar_path(), state):
                _lifecycle_breadcrumb("sidecar rewrite-after-pop failed (fail-open)")

    if _FILELOCK_AVAILABLE and FileLock is not None:
        try:
            with FileLock(_sidecar_lock_path(), timeout=_LOCK_TIMEOUT_S):
                _pop()
            return popped or None
        except FileLockTimeout:
            _lifecycle_breadcrumb("sidecar lock timeout — lockless best-effort pop")
        except Exception as exc:
            _lifecycle_breadcrumb("sidecar lock error (%s) — lockless pop" % str(exc)[:60])
    _pop()
    return popped or None


def _observe_lifecycle(event: Dict[str, Any], marker_count: int) -> None:
    """Emit ONE subagent_lifecycle_observed per returning agent. Fail-open.

    Consumes the SubagentStart sidecar (wall-time bracket + archetype) + the
    harness-supplied `agent_transcript_path` (token bracket) + the
    confidence-marker count this hook already computed (claim bracket). RAW
    counts are NEVER persisted — only the closed-enum brackets. Observer-only;
    never blocks; any error degrades to a breadcrumb.
    """
    if os.environ.get("CEO_SUBAGENT_LIFECYCLE") == "0":
        return
    try:
        now = time.time()
        agent_id = ""
        for k in ("agent_id", "agentId"):
            v = event.get(k)
            if isinstance(v, str) and v:
                agent_id = v
                break

        # 1. Wall-time bracket + archetype from the SubagentStart sidecar.
        wall_seconds: Optional[float] = None
        wall_source = "unknown"
        archetype = "unknown"
        if agent_id:
            entry = _consume_start_entry(agent_id, now)
            if entry is not None:
                try:
                    start_ts = float(entry.get("start_ts", 0))
                    if start_ts > 0 and now >= start_ts:
                        wall_seconds = now - start_ts
                        wall_source = "bracketed"
                except (TypeError, ValueError):
                    pass
                stype = entry.get("agent_type")
                if isinstance(stype, str):
                    archetype = _normalize_archetype(stype)
        # Fall back to a spawn-type on the stop payload itself if the sidecar
        # had no archetype (archetype still "unknown" only when neither source
        # supplied one — keeps the persona-ledger signal when start was lost).
        if archetype == "unknown":
            for k in ("agent_type", "agentType", "subagent_type"):
                v = event.get(k)
                if isinstance(v, str) and v:
                    archetype = _normalize_archetype(v)
                    break

        # 2. Token bracket from agent_transcript_path (S227 reconstruction).
        token_total: Optional[int] = None
        tpath_raw = ""
        for k in ("agent_transcript_path", "agentTranscriptPath", "transcript_path"):
            v = event.get(k)
            if isinstance(v, str) and v:
                tpath_raw = v
                break
        if tpath_raw:
            safe = _transcript_path_ok(tpath_raw)
            if safe is not None:
                token_total = _sum_transcript_tokens(safe)
            else:
                _lifecycle_breadcrumb("agent_transcript_path failed containment — token bracket unknown")

        # 3. Emit (typed wrapper — closed-enum brackets only).
        session_id = ""
        sv = event.get("session_id") or event.get("sessionId")
        if isinstance(sv, str):
            session_id = sv
        try:
            from _lib import audit_emit  # noqa: E402
            audit_emit.emit_subagent_lifecycle_observed(
                agent_archetype=archetype,
                wall_bucket=_wall_bucket(wall_seconds),
                wall_source=wall_source,
                token_bucket=_token_bucket(token_total),
                claim_bucket=_claim_bucket(marker_count),
                session_id=session_id,
                project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
            )
        except Exception:
            return
    except Exception as exc:  # pragma: no cover — belt-and-suspenders
        _lifecycle_breadcrumb("fail-open (observe): %s" % str(exc)[:120])


def _redact_safe(text: str) -> str:
    """Pass ``text`` through secret-redaction; fail-open on any error.

    Hook is SubagentStop — the subagent's output can contain API keys
    or credentials. Even though confidence markers are word-bounded
    Latin idioms that cannot structurally contain secrets, belt-and-
    suspenders: redact before scan AND redact matched snippets before
    emit/systemMessage. C8 normative (PLAN-050 Round 1 §C8).
    """
    if not _REDACT_AVAILABLE or _redact is None:
        return text
    try:
        return _redact.redact_secrets(text, max_chars=len(text) + 1)
    except Exception:
        return text


# ---------------------------------------------------------------------------
# Confidence-marker patterns.
#
# Word-bounded to avoid matching "all done-ness" style partial hits. The
# list is conservative — only phrases that empirically correlate with
# Artifact Paradox fluency bias per PROTOCOL.md §Artifact Paradox +
# PLAN-034 adversarial-reviewer audit + pitfall LLM-001.
#
# ASCII-bounded by design — we don't want to over-trigger on i18n noise,
# only on Latin confidence idioms. Unicode homoglyphs (e.g. Cyrillic "а"
# in "аll done") will NOT match, which is intentional.
# ---------------------------------------------------------------------------
_MARKER_PATTERNS: List[re.Pattern[str]] = [
    # "all done" / "all good" / "all green"
    re.compile(r"\ball\s+(?:done|good|green|clear|set|passing)\b", re.IGNORECASE),
    # "tests? (are )?(all )?green/passing"
    re.compile(r"\btests?\s+(?:are\s+)?(?:all\s+)?(?:green|passing)\b", re.IGNORECASE),
    # "perfect" / "perfectly"
    re.compile(r"\b(?:perfect|perfectly)\b", re.IGNORECASE),
    # "no issues" / "no problems" / "no errors" / "no regressions"
    re.compile(r"\bno\s+(?:issues?|problems?|errors?|regressions?|bugs?)\b", re.IGNORECASE),
    # "looks good" / "looks fine" / "LGTM"
    re.compile(r"\b(?:looks\s+(?:good|fine|great)|LGTM|lgtm)\b"),
    # "completed successfully" / "successfully completed"
    re.compile(r"\b(?:completed\s+successfully|successfully\s+(?:completed|shipped|landed))\b", re.IGNORECASE),
    # "ready to ship" / "ready for review"
    re.compile(r"\bready\s+(?:to\s+ship|for\s+review|to\s+merge|to\s+commit)\b", re.IGNORECASE),
    # "fully covered" / "100% coverage"
    re.compile(r"\bfully\s+(?:covered|tested|implemented)\b", re.IGNORECASE),
    # "clean diff" / "clean commit"
    re.compile(r"\bclean\s+(?:diff|commit|build|run|state)\b", re.IGNORECASE),
    # "implemented as specified" / "exactly as specified"
    re.compile(r"\b(?:implemented|done|delivered)\s+(?:as\s+(?:specified|requested)|exactly)\b", re.IGNORECASE),
]


# Output length cap for the scan — anything beyond gets the tail-scan only.
# This prevents pathological runtime on multi-megabyte outputs (unlikely
# in practice, but bounded defensive programming).
_MAX_SCAN_BYTES = 200_000  # 200 KiB


def _threshold_for_length(length: int) -> int:
    """Adaptive marker threshold based on output length."""
    if length < 500:
        return 2
    if length < 5000:
        return 4
    return 8


def _count_markers(text: str) -> Tuple[int, List[str]]:
    """Return (total_hits, list_of_matching_markers). Never raises.

    PLAN-050 Phase 3 C8 — redaction is applied to the per-match ``found``
    snippets after scanning (see `_redact_safe` in `_emit_fluency_nudge_audit`
    and `main`), NOT to the full scanned text. A 200 KiB pre-scan redact
    would break the <1s SLA on 500 KiB adversarial inputs (~5s measured).
    Confidence markers are word-bounded Latin idioms so regex `findall`
    structurally cannot capture secret tokens — redact on matched is a
    defense-in-depth layer for future regex changes, not a live filter.
    """
    if not text:
        return 0, []
    # Cap the scanned region for very-large outputs. We scan both ends
    # so opening + closing "all done" patterns still catch even in
    # multi-megabyte payloads.
    if len(text) > _MAX_SCAN_BYTES:
        half = _MAX_SCAN_BYTES // 2
        text = text[:half] + "\n" + text[-half:]
    found: List[str] = []
    count = 0
    for pat in _MARKER_PATTERNS:
        matches = pat.findall(text)
        if matches:
            count += len(matches)
            # Record the first match snippet for the systemMessage.
            for m in matches[:3]:
                # findall returns either str or tuple-of-groups
                if isinstance(m, tuple):
                    m = next((x for x in m if x), "")
                if m and m.lower() not in [f.lower() for f in found]:
                    found.append(m)
    return count, found[:5]


def _emit_allow(system_message: Optional[str] = None) -> str:
    # Allow: emit empty dict or just {"systemMessage": ...} for advisory
    # banners. Top-level {"decision":"allow"} fails Claude Code hook schema.
    out: Dict[str, object] = {}
    if system_message:
        out["systemMessage"] = system_message
    return json.dumps(out, ensure_ascii=False)


def _emit_fluency_nudge_audit(
    *,
    marker_count: int,
    threshold: int,
    matched: List[str],
    output_length: int,
    session_id: str,
) -> None:
    """Best-effort audit emit. Never raises."""
    # PLAN-050 Phase 3 C8 — defense-in-depth redact on matched snippets
    # before emit. Markers are already word-bounded Latin idioms so this
    # is a no-op on the happy path; guards against any future regex
    # change that might capture broader spans.
    matched_safe = [_redact_safe(m) for m in matched]
    try:
        from _lib import audit_emit  # noqa: E402
        audit_emit.emit_generic(
            action="fluency_nudge",
            session_id=session_id,
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
            marker_count=marker_count,
            threshold_crossed=threshold,
            markers_matched=matched_safe,
            output_length=output_length,
        )
    except Exception:
        return


def main() -> int:
    """Hook entrypoint. Reads SubagentStop payload from stdin; emits allow + optional advisory nudge.

    PLAN-135 W2 H3: ALSO emits ONE per-agent ``subagent_lifecycle_observed``
    bracket (independent of the fluency threshold) by consuming the
    SubagentStart sidecar + the harness ``agent_transcript_path``. Both halves
    are observer-only + fail-open; an error in either NEVER blocks and NEVER
    suppresses the other.
    """
    fluency_off = os.environ.get("CEO_FLUENCY_NUDGE") == "0"
    lifecycle_off = os.environ.get("CEO_SUBAGENT_LIFECYCLE") == "0"
    # With BOTH halves disabled there is nothing to do — short-circuit before
    # reading stdin (the cheapest possible path).
    if fluency_off and lifecycle_off:
        sys.stdout.write(_emit_allow() + "\n")
        return 0
    # Read SubagentStop payload. Graceful fail-open on parse error.
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw else {}
        if not isinstance(event, dict):
            raise ValueError("hook input is not a JSON object")
    except Exception:
        sys.stdout.write(_emit_allow() + "\n")
        return 0
    # SubagentStop delivers the sub-agent's output inside `tool_response`
    # or `response`/`transcript`. Name varies per Claude Code version;
    # try a few shapes.
    text = ""
    for key in ("tool_response", "response", "transcript", "output"):
        val = event.get(key)
        if isinstance(val, str):
            text = val
            break
        if isinstance(val, dict):
            inner = val.get("content") or val.get("text") or ""
            if isinstance(inner, str):
                text = inner
                break
    # Marker count drives BOTH the claim bracket (H3) and the fluency nudge.
    # Compute once; empty text → 0 markers.
    count, matched = _count_markers(text) if text else (0, [])

    # H3 — per-agent lifecycle bracket. Runs on EVERY SubagentStop (even when
    # the fluency nudge does not trigger). Self-gates on CEO_SUBAGENT_LIFECYCLE;
    # observer-only + fail-open (never blocks, never raises out).
    if not lifecycle_off:
        _observe_lifecycle(event, count)

    # Fluency-nudge half (the original behavior). Self-gated.
    if fluency_off or not text:
        sys.stdout.write(_emit_allow() + "\n")
        return 0
    length = len(text)
    threshold = _threshold_for_length(length)
    if count < threshold:
        sys.stdout.write(_emit_allow() + "\n")
        return 0
    # Nudge.
    session_id = event.get("session_id") or ""
    _emit_fluency_nudge_audit(
        marker_count=count,
        threshold=threshold,
        matched=matched,
        output_length=length,
        session_id=session_id,
    )
    # PLAN-050 Phase 3 C8 — redact matched snippets before systemMessage
    # so any rare regex edge case that captures broader context cannot
    # leak secrets back to the CEO transcript.
    matched_safe_msg = [_redact_safe(m) for m in matched]
    msg = (
        "ARTIFACT-PARADOX-NUDGE: sub-agent output contains "
        f"{count} confidence markers (threshold={threshold} for "
        f"length={length}). Markers: {', '.join(repr(m) for m in matched_safe_msg)}. "
        "Per PROTOCOL.md §Artifact Paradox + pitfall LLM-001, treat "
        "'all done, tests green' as a RED FLAG for unreviewed gaps — "
        "review as if junior engineer's work; focus on what's absent; "
        "verify against code (not confidence)."
    )
    sys.stdout.write(_emit_allow(system_message=msg) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
