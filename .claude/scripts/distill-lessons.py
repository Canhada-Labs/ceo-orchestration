#!/usr/bin/env python3
"""distill-lessons.py — offline metadata-rail distiller (PLAN-154 item 2).

Walks the OPT-IN observe store (``<audit_dir>/tool-lifecycle/*.observe.jsonl``
— the per-session files written ONLY when ``CEO_LEARNING_OBSERVE=1``, via
``_lib.tool_lifecycle.observation_store_path``) behind a persisted delta
cursor, aggregates the CLOSED-ENUM fields into a bounded statistics digest,
asks a pinned haiku-tier model to propose lesson candidates, and writes
survivors as PENDING candidates via ``lessons.add_candidate`` (the fail-CLOSED
promotion boundary, PLAN-154 A4).

## Kill-switch coupling (A12 — the certifying invariant)

The read surface is the OPT-IN observe store, NEVER the ALWAYS-ON
``tool_call_lifecycle_recorded`` audit action. ``tool_lifecycle.record_post``
emits that audit action on every completed tool call regardless of the
opt-in, but it writes the ``*.observe.jsonl`` store ONLY when
``CEO_LEARNING_OBSERVE=1``. So a session that never opted in produces NO
store file and contributes ZERO observations here — the distiller cannot
mint a candidate from an un-opted-in session (A12 zero-delta/kill-switch
contract). Keying on the always-on audit action instead would break that
contract (the Codex pair-rail S265 P2#4 defect this read-surface repoint
closes).

## v1 read surface (A4 — any widening is its own reviewed change)

The ONLY fields ever consumed from an observation event are:

- ``tool_name_enum``   — validated against the PLAN-125 closed enum
  (``_lib.tool_lifecycle.to_tool_name_enum`` idempotence check)
- ``duration_bucket``  — validated against ``DURATION_BUCKETS``
- ``success``          — must be a bool
- ``orphan``           — must be a bool

Any event failing validation is DROPPED before aggregation (fail-CLOSED on
input). No free-text field ever reaches the model prompt: the prompt is
built exclusively from closed enum values + integer counts, so the read
surface is injection-inert by construction (ADR-160).

## Cadence + economics

- **Owner-invoked or nightly-hygiene piggyback ONLY** — this script is
  never wired to a hook, boot step, or per-session trigger.
- Persisted delta cursor: ``<audit_dir>/learning-distiller/cursor.json``
  (0600, atomic write) stores per-observe-store byte offsets (keyed by the
  ``<session>.observe.jsonl`` basename); each run consumes only new bytes
  (bounded to 5 MiB per file per run).
- Hard per-run input-token ceiling (default 8000 estimated tokens,
  ``--max-input-tokens``): exceeded → refuse BEFORE any model spend.
- Model pinned EXPLICITLY haiku-tier (``claude-haiku-4-5-20251001``),
  override via ``CEO_LEARNING_DISTILL_MODEL`` (NOT routed through
  ``model_routing.py``). Pricing row: ``docs/provider-pricing.md``.
- Token usage is emitted as a ``distiller_run_completed`` audit event
  (``tokens_in`` / ``tokens_out``) so ``/agent-budget`` shows the
  distiller as its own line item.

## Hermetic CI contract

``--from-fixture <path>`` supplies a RECORDED model output (first-class
contract) — CI never calls a live model. Fixture schema::

    {"model": "...", "tokens_in": int, "tokens_out": int, "output": "..."}

## Fail-CLOSED posture (PLAN-152 C4 / PLAN-154 A4)

- Enum-validation surface unavailable  → refuse (exit 3)
- Injection scanner unavailable        → refuse before model spend (exit 5)
- ``lessons.add_candidate`` missing    → refuse (exit 2)
- Model output unparseable/over-schema → NO candidate written, cursor NOT
  advanced, breadcrumb on stderr + run event (exit 4)
- Token ceiling exceeded               → refuse, cursor NOT advanced (exit 6)
- Model invocation failure             → nothing written (exit 7)
- Scan HIT on a proposed candidate     → rejected pre-candidate (never
  reaches ``add_candidate``); survivors may still be written.

Audit-emit failures are the ONLY fail-open edge (house posture).

## Kill switches

- ``CEO_SOTA_DISABLE=1``            → no-op exit 0 (master precedence)
- ``CEO_LEARNING_DISTILL_MODEL``    → model override (default pinned above)

Stdlib-only. Python >= 3.9.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Make _lib importable — this script lives in .claude/scripts/, _lib lives
# in .claude/hooks/_lib/ (same pattern as lessons.py).
_HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_SCRIPTS_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Constants (closed vocabularies + bounds)
# ---------------------------------------------------------------------------

#: Pinned haiku-tier default (PLAN-154 item 2 — explicit pin, NOT routed via
#: model_routing.py). Override: CEO_LEARNING_DISTILL_MODEL.
DEFAULT_DISTILL_MODEL = "claude-haiku-4-5-20251001"
_MODEL_ENV = "CEO_LEARNING_DISTILL_MODEL"

#: Hard per-run input-token ceiling (estimated at ~4 chars/token).
DEFAULT_MAX_INPUT_TOKENS = 8000
_CHARS_PER_TOKEN = 4

#: Closed trigger vocabulary for distilled candidates (constraint 3 —
#: "trigger -> advisory-text from a constrained vocabulary").
DISTILL_TRIGGER_VOCAB = frozenset({
    "repeat_tool_failure",
    "slow_tool_pattern",
    "orphan_tool_calls",
})

#: Bounded candidate schema (A5-aligned: no backticks, no newlines, <=200).
MAX_ADVISORY_CHARS = 200
MAX_SCOPE_TAGS = 8
MAX_CANDIDATES_PER_RUN = 5
_TAG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
_CANDIDATE_REQUIRED_KEYS = frozenset({"trigger", "advisory_text", "scope_tags"})

#: The OPT-IN observe store this distiller reads (v1 read surface). The store
#: lives in the ``tool-lifecycle/`` subdir of the audit dir and is written
#: ONLY when ``CEO_LEARNING_OBSERVE=1`` (``tool_lifecycle.observation_store_path``).
#: Reading THIS store — never the always-on ``tool_call_lifecycle_recorded``
#: audit action — is what honors the A12 kill-switch: a session that never
#: opted in produces NO store file, hence zero distiller input (Codex S265 P2#4).
_OBSERVE_STORE_SUBDIR = "tool-lifecycle"
_OBSERVE_STORE_GLOB = "*.observe.jsonl"

#: Per-file new-bytes bound per run (backlog picked up on the next run).
_MAX_NEW_BYTES_PER_FILE = 5 * 1024 * 1024

#: Cursor-key hygiene: only per-session observe-store basenames are tracked
#: (``<safe_session>.observe.jsonl``). ``_safe_session_component`` yields only
#: ``[A-Za-z0-9._-]`` and caps length, so a traversal key never matches.
_CURSOR_KEY_RE = re.compile(r"^[A-Za-z0-9._-]+\.observe\.jsonl$")

#: Run outcome closed enum (mirrored in the distiller_run_completed event).
OUTCOMES = frozenset({
    "ok",
    "no_new_events",
    "schema_reject",
    "scan_unavailable",
    "token_ceiling",
    "model_error",
    "store_unavailable",
    "input_surface_unavailable",
})


class DistillModelError(RuntimeError):
    """Live model invocation failed (subprocess / envelope parse)."""


@dataclass
class DistillResult:
    """Outcome of one distiller run (feeds the audit run event)."""

    outcome: str = "ok"
    model_id: str = ""
    fixture_mode: bool = False
    events_consumed: int = 0
    observations_rejected: int = 0
    candidates_proposed: int = 0
    candidates_written: int = 0
    candidates_quarantined: int = 0
    rejected_pre_candidate: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cursor_advanced: bool = False
    detail: str = ""
    written_ids: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Fail-closed dependency resolution
# ---------------------------------------------------------------------------


def _load_enum_surface() -> Optional[Tuple[Callable[[Any], str], Tuple[str, ...]]]:
    """Return (to_tool_name_enum, DURATION_BUCKETS) or None.

    The distiller validates every observation against the SAME closed enums
    the rail pins (single source of truth — no fourth enum copy). If the
    surface is unavailable the distiller REFUSES to run (fail-closed: it
    cannot validate its input boundary).
    """
    try:
        from _lib.tool_lifecycle import DURATION_BUCKETS, to_tool_name_enum
        return to_tool_name_enum, tuple(DURATION_BUCKETS)
    except Exception:
        return None


def _load_scanner() -> Optional[Callable[[str], Any]]:
    """Load scan-injection.py's ``scan_text`` — None on ANY failure.

    Unlike the advisory lesson-write scan (fail-open), the distiller sits at
    the promotion boundary: a None return makes the run REFUSE before any
    model spend (A4 fail-closed).
    """
    try:
        import importlib.util as _iutil
        spec = _iutil.spec_from_file_location(
            "scan_injection_for_distiller",
            _SCRIPTS_DIR / "scan-injection.py",
        )
        if spec is None or spec.loader is None:
            return None
        mod = _iutil.module_from_spec(spec)
        # Register BEFORE exec: py3.9 dataclasses resolve
        # sys.modules[cls.__module__] during class creation and exec_module
        # on an unregistered module AttributeErrors otherwise.
        sys.modules["scan_injection_for_distiller"] = mod
        spec.loader.exec_module(mod)
        scan_text = getattr(mod, "scan_text", None)
        if not callable(scan_text):
            return None
        return scan_text
    except Exception:
        return None


def _resolve_add_candidate() -> Optional[Callable[..., Tuple[str, str]]]:
    """Resolve ``lessons.add_candidate`` (wave-0 interface contract).

    Returns None when the lessons module or the function is unavailable —
    the caller refuses the run (exit 2). There is NO fallback write path:
    every candidate write goes through the fail-closed promotion boundary
    inside lessons.py (A4).
    """
    try:
        if str(_SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(_SCRIPTS_DIR))
        import lessons as _lessons  # noqa: WPS433
        fn = getattr(_lessons, "add_candidate", None)
        if not callable(fn):
            return None
        return fn
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Audit-dir + cursor (per-file byte offsets; 0600 atomic writes)
# ---------------------------------------------------------------------------


def resolve_audit_dir() -> Path:
    """Mirror the house audit-dir resolution (tool_lifecycle/budget-summary)."""
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration"


def _state_dir(audit_dir: Path) -> Path:
    return audit_dir / "learning-distiller"


def _cursor_path(audit_dir: Path) -> Path:
    return _state_dir(audit_dir) / "cursor.json"


def load_cursor(audit_dir: Path) -> Dict[str, int]:
    """Load per-file byte offsets. Malformed/missing → empty (re-scan)."""
    path = _cursor_path(audit_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    files = data.get("files")
    if not isinstance(files, dict):
        return {}
    out: Dict[str, int] = {}
    for name, offset in files.items():
        if not isinstance(name, str) or not _CURSOR_KEY_RE.match(name):
            continue
        try:
            off = int(offset)
        except (TypeError, ValueError):
            continue
        if off >= 0:
            out[name] = off
    return out


def save_cursor(
    audit_dir: Path,
    offsets: Dict[str, int],
    *,
    now_fn: Callable[[], float] = time.time,
) -> bool:
    """Atomic 0600 cursor write (tool_lifecycle per-session-file pattern)."""
    try:
        sdir = _state_dir(audit_dir)
        sdir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(sdir, 0o700)
        except OSError:
            pass
        payload = json.dumps(
            {
                "schema": 1,
                "last_run_at": datetime.fromtimestamp(
                    now_fn(), tz=timezone.utc
                ).isoformat(),
                "files": {k: int(v) for k, v in sorted(offsets.items())},
            },
            indent=2,
            sort_keys=True,
        ) + "\n"
        tmp = _cursor_path(audit_dir).with_suffix(".json.tmp")
        fd = os.open(str(tmp), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            os.write(fd, payload.encode("utf-8"))
        finally:
            os.close(fd)
        os.replace(str(tmp), str(_cursor_path(audit_dir)))
        return True
    except OSError:
        return False


def _discover_stores(audit_dir: Path) -> List[Path]:
    """All ``*.observe.jsonl`` opt-in observe stores under ``tool-lifecycle/``.

    Sorted by name for deterministic cursor bookkeeping. Each per-session
    store is independent — there is no active/backup rotation like the audit
    log — and a session that never set ``CEO_LEARNING_OBSERVE=1`` has no file
    here at all, so it contributes nothing to the distiller (A12).
    """
    store_dir = audit_dir / _OBSERVE_STORE_SUBDIR
    if not store_dir.is_dir():
        return []
    return sorted(store_dir.glob(_OBSERVE_STORE_GLOB))


# ---------------------------------------------------------------------------
# Observation read + closed-enum sanitization (fail-closed on input)
# ---------------------------------------------------------------------------


def sanitize_observation(
    event: Dict[str, Any],
    to_enum: Callable[[Any], str],
    buckets: Tuple[str, ...],
) -> Optional[Dict[str, Any]]:
    """Extract the v1 closed-enum read surface; None on ANY violation.

    ``to_enum`` is idempotent on valid enum values — a smuggled free-text
    ``tool_name_enum`` maps to ``"other"`` (!= original) and is rejected.
    Extra event fields are NEVER read (metadata-only, A2).
    """
    tool_name = event.get("tool_name_enum")
    bucket = event.get("duration_bucket")
    success = event.get("success")
    orphan = event.get("orphan")
    if not isinstance(tool_name, str) or to_enum(tool_name) != tool_name:
        return None
    if not isinstance(bucket, str) or bucket not in buckets:
        return None
    if not isinstance(success, bool) or not isinstance(orphan, bool):
        return None
    return {
        "tool_name_enum": tool_name,
        "duration_bucket": bucket,
        "success": success,
        "orphan": orphan,
    }


def read_new_observations(
    audit_dir: Path,
    cursor: Dict[str, int],
    to_enum: Callable[[Any], str],
    buckets: Tuple[str, ...],
) -> Tuple[List[Dict[str, Any]], Dict[str, int], int]:
    """Read observations from the opt-in observe stores past the cursor.

    Returns ``(observations, new_offsets, rejected_count)``. Only complete
    lines are consumed (a partial trailing line stays behind the cursor). A
    shrunk file (pruning/rotation reuse) resets that store's offset to 0.

    Every store line is an observation row written by the observe rail's
    closed-schema coercer (``_lib.tool_lifecycle._append_observation``), so
    there is NO always-on ``action`` filter here — the read surface IS the
    opt-in store. Each line is still independently re-validated against the
    closed enums (``sanitize_observation``, fail-CLOSED on input): a tampered
    or corrupt row is dropped, never trusted.
    """
    observations: List[Dict[str, Any]] = []
    rejected = 0
    new_offsets: Dict[str, int] = dict(cursor)

    for log_path in _discover_stores(audit_dir):
        name = log_path.name
        offset = cursor.get(name, 0)
        try:
            size = log_path.stat().st_size
        except OSError:
            continue
        if offset > size:
            offset = 0  # rotation reuse — re-read from start
        if offset == size:
            new_offsets[name] = offset
            continue
        try:
            with open(log_path, "rb") as fh:
                fh.seek(offset)
                chunk = fh.read(_MAX_NEW_BYTES_PER_FILE)
        except OSError:
            continue
        # Only consume up to the last complete newline.
        last_nl = chunk.rfind(b"\n")
        if last_nl < 0:
            new_offsets[name] = offset
            continue
        consumed = chunk[: last_nl + 1]
        new_offsets[name] = offset + len(consumed)
        for raw_line in consumed.split(b"\n"):
            if not raw_line.strip():
                continue
            try:
                event = json.loads(raw_line.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if not isinstance(event, dict):
                continue
            obs = sanitize_observation(event, to_enum, buckets)
            if obs is None:
                rejected += 1
                continue
            observations.append(obs)
    return observations, new_offsets, rejected


# ---------------------------------------------------------------------------
# Aggregation + prompt (deterministic, closed-enum-only content)
# ---------------------------------------------------------------------------


def aggregate(observations: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Aggregate observations into a per-tool digest (deterministic)."""
    digest: Dict[str, Dict[str, Any]] = {}
    for obs in observations:
        row = digest.setdefault(
            obs["tool_name_enum"],
            {"total": 0, "failures": 0, "orphans": 0, "buckets": {}},
        )
        row["total"] += 1
        if not obs["success"]:
            row["failures"] += 1
        if obs["orphan"]:
            row["orphans"] += 1
        b = row["buckets"]
        b[obs["duration_bucket"]] = b.get(obs["duration_bucket"], 0) + 1
    return digest


def build_prompt(digest: Dict[str, Dict[str, Any]]) -> str:
    """Render the model prompt from the digest.

    Every character of variable content derives from closed enum values and
    integer counts — injection-inert by construction (ADR-160 / A2).
    """
    lines = [
        "You are an offline telemetry distiller for a development-tool",
        "governance framework. Below is an aggregated, metadata-only digest",
        "of tool-call lifecycle telemetry (closed enums and counts only).",
        "",
        "Propose at most "
        + str(MAX_CANDIDATES_PER_RUN)
        + " operational lesson candidates that a human reviewer will",
        "approve or reject later. Only propose a candidate when the digest",
        "shows a clear, recurring pattern.",
        "",
        "## Digest",
        "",
    ]
    for tool in sorted(digest):
        row = digest[tool]
        bucket_txt = ", ".join(
            "{0}={1}".format(k, row["buckets"][k]) for k in sorted(row["buckets"])
        )
        lines.append(
            "- {0}: total={1} failures={2} orphans={3} durations[{4}]".format(
                tool, row["total"], row["failures"], row["orphans"], bucket_txt
            )
        )
    lines += [
        "",
        "## Output contract (STRICT)",
        "",
        "Return ONLY a raw JSON object (no markdown fences, no prose):",
        '{"candidates": [{"trigger": "...", "advisory_text": "...",'
        ' "scope_tags": ["..."]}]}',
        "",
        "- trigger MUST be one of: " + ", ".join(sorted(DISTILL_TRIGGER_VOCAB)),
        "- advisory_text: single line, max "
        + str(MAX_ADVISORY_CHARS)
        + " characters, plain text, no backticks, no newlines",
        "- scope_tags: 1-" + str(MAX_SCOPE_TAGS)
        + " lowercase tags matching [a-z0-9][a-z0-9_-]*",
        '- If nothing meets the bar, return {"candidates": []}',
    ]
    return "\n".join(lines)


def estimate_tokens(text: str) -> int:
    return (len(text) + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN


# ---------------------------------------------------------------------------
# Model invocation (live + recorded fixture)
# ---------------------------------------------------------------------------


def resolve_model() -> str:
    env = os.environ.get(_MODEL_ENV, "").strip()
    return env if env else DEFAULT_DISTILL_MODEL


def invoke_model_cli(
    prompt: str, model: str, *, timeout_s: float = 180.0
) -> Tuple[str, int, int]:
    """Live path: ``claude -p --output-format json`` subprocess.

    Never exercised by CI (fixture mode is the first-class CI contract).
    Returns ``(output_text, tokens_in, tokens_out)``; raises
    :class:`DistillModelError` on any failure (fail-closed).
    """
    try:
        proc = subprocess.run(
            ["claude", "-p", "--model", model, "--output-format", "json"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise DistillModelError("model subprocess failed: {0}".format(exc))
    if proc.returncode != 0:
        raise DistillModelError(
            "model subprocess exit {0}: {1}".format(
                proc.returncode, (proc.stderr or "")[:200]
            )
        )
    try:
        envelope = json.loads(proc.stdout or "")
    except json.JSONDecodeError:
        raise DistillModelError("model envelope is not valid JSON")
    if not isinstance(envelope, dict):
        raise DistillModelError("model envelope is not an object")
    result_text = envelope.get("result")
    if not isinstance(result_text, str):
        raise DistillModelError("model envelope missing 'result' text")
    usage = envelope.get("usage")
    usage = usage if isinstance(usage, dict) else {}
    try:
        tokens_in = int(usage.get("input_tokens") or 0)
        tokens_out = int(usage.get("output_tokens") or 0)
    except (TypeError, ValueError):
        tokens_in, tokens_out = 0, 0
    return result_text, tokens_in, tokens_out


def load_fixture_output(path: Path) -> Tuple[str, int, int, str]:
    """Load a recorded model output. Raises DistillModelError on violation."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise DistillModelError("fixture unreadable: {0}".format(exc))
    if not isinstance(data, dict) or not isinstance(data.get("output"), str):
        raise DistillModelError("fixture missing string 'output'")
    try:
        tokens_in = int(data.get("tokens_in") or 0)
        tokens_out = int(data.get("tokens_out") or 0)
    except (TypeError, ValueError):
        raise DistillModelError("fixture token counts must be integers")
    if tokens_in < 0 or tokens_out < 0:
        raise DistillModelError("fixture token counts must be >= 0")
    model = data.get("model")
    model = model if isinstance(model, str) else ""
    return data["output"], tokens_in, tokens_out, model


# ---------------------------------------------------------------------------
# Output schema validation (fail-CLOSED) + candidate hygiene
# ---------------------------------------------------------------------------


def _text_has_forbidden_chars(text: str) -> bool:
    """True when text carries newline/backtick/control/format codepoints."""
    for ch in text:
        if ch in ("\n", "\r", "`"):
            return True
        cat = unicodedata.category(ch)
        if cat in ("Cc", "Cf", "Co", "Cs"):
            return True
    return False


def validate_candidate(cand: Any) -> Optional[str]:
    """Return an error reason, or None when the candidate is in-schema."""
    if not isinstance(cand, dict):
        return "candidate is not an object"
    keys = set(cand.keys())
    if keys != _CANDIDATE_REQUIRED_KEYS:
        return "candidate keys out of schema: {0}".format(sorted(keys))
    trigger = cand["trigger"]
    if not isinstance(trigger, str) or trigger not in DISTILL_TRIGGER_VOCAB:
        return "trigger outside closed vocabulary"
    advisory = cand["advisory_text"]
    if not isinstance(advisory, str) or not advisory.strip():
        return "advisory_text missing/empty"
    if len(advisory) > MAX_ADVISORY_CHARS:
        return "advisory_text exceeds {0} chars".format(MAX_ADVISORY_CHARS)
    if _text_has_forbidden_chars(advisory):
        return "advisory_text carries forbidden characters"
    tags = cand["scope_tags"]
    if not isinstance(tags, list) or not (1 <= len(tags) <= MAX_SCOPE_TAGS):
        return "scope_tags must be a list of 1-{0}".format(MAX_SCOPE_TAGS)
    for tag in tags:
        if not isinstance(tag, str) or not _TAG_RE.match(tag):
            return "scope_tag outside bounded vocabulary"
    return None


def validate_model_output(text: str) -> Tuple[Optional[List[Dict[str, Any]]], str]:
    """Strict fail-CLOSED schema validation of the raw model output.

    Returns ``(candidates, "")`` on success or ``(None, reason)`` on ANY
    violation — unparseable or over-schema output writes NOTHING (A4).
    """
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None, "output is not valid JSON"
    if not isinstance(data, dict):
        return None, "output is not a JSON object"
    if set(data.keys()) != {"candidates"}:
        return None, "over-schema top-level keys: {0}".format(sorted(data.keys()))
    candidates = data["candidates"]
    if not isinstance(candidates, list):
        return None, "'candidates' is not a list"
    if len(candidates) > MAX_CANDIDATES_PER_RUN:
        return None, "more than {0} candidates".format(MAX_CANDIDATES_PER_RUN)
    for cand in candidates:
        reason = validate_candidate(cand)
        if reason is not None:
            return None, reason
    return candidates, ""


def scan_candidate_blob(
    cand: Dict[str, Any], scan_fn: Callable[[str], Any]
) -> bool:
    """True when the injection scan HITS (candidate must be rejected).

    Any scanner exception is ALSO treated as a hit (fail-closed at the
    promotion boundary — content the guard cannot parse is blocked).
    """
    blob = " ".join(
        [str(cand.get("trigger", "")), str(cand.get("advisory_text", ""))]
        + [str(t) for t in cand.get("scope_tags", [])]
    )
    try:
        result = scan_fn(blob)
    except Exception:
        return True
    return bool(getattr(result, "matched", False) or getattr(result, "matches", None))


# ---------------------------------------------------------------------------
# Audit emission (fail-open — the only fail-open edge in this script)
# ---------------------------------------------------------------------------


def _emit_run_event(
    result: DistillResult,
    *,
    emit_fn: Optional[Callable[..., None]] = None,
) -> None:
    """Emit ``distiller_run_completed`` (pre-registration = silent no-op).

    Field set is metadata-only: closed outcome enum, booleans, bounded
    model id, integer counters. tokens_in/tokens_out ride the existing
    /agent-budget rollup once the action is registered by the integrator.
    """
    try:
        if emit_fn is None:
            from _lib import audit_emit  # noqa: WPS433
            emit_fn = audit_emit.emit_generic
        emit_fn(
            "distiller_run_completed",
            outcome=result.outcome if result.outcome in OUTCOMES else "ok",
            model_id=result.model_id[:64],
            fixture_mode=bool(result.fixture_mode),
            events_consumed=int(result.events_consumed),
            observations_rejected=int(result.observations_rejected),
            candidates_proposed=int(result.candidates_proposed),
            candidates_written=int(result.candidates_written),
            candidates_quarantined=int(result.candidates_quarantined),
            rejected_pre_candidate=int(result.rejected_pre_candidate),
            tokens_in=int(result.tokens_in),
            tokens_out=int(result.tokens_out),
            cursor_advanced=bool(result.cursor_advanced),
            session_id="",
            project="",
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_distill(
    audit_dir: Path,
    *,
    invoke_fn: Optional[Callable[[str, str], Tuple[str, int, int]]] = None,
    fixture_path: Optional[Path] = None,
    add_candidate_fn: Optional[Callable[..., Tuple[str, str]]] = None,
    scan_fn: Optional[Callable[[str], Any]] = None,
    enum_surface: Optional[Tuple[Callable[[Any], str], Tuple[str, ...]]] = None,
    max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS,
    model: Optional[str] = None,
    now_fn: Callable[[], float] = time.time,
) -> DistillResult:
    """One full distiller pass. See module docstring for the posture map.

    Cursor semantics: the cursor advances ONLY on a fully successful run
    (including a valid empty-candidates run). Schema rejects, token-ceiling
    refusals, model errors and store failures leave the cursor untouched so
    a later run retries the same window.
    """
    result = DistillResult(model_id=model or resolve_model())
    result.fixture_mode = fixture_path is not None

    # -- Fail-closed dependency resolution BEFORE any read/spend ------------
    surface = enum_surface if enum_surface is not None else _load_enum_surface()
    if surface is None:
        result.outcome = "input_surface_unavailable"
        result.detail = "closed-enum validation surface unavailable"
        return result
    to_enum, buckets = surface

    scanner = scan_fn if scan_fn is not None else _load_scanner()
    if scanner is None:
        result.outcome = "scan_unavailable"
        result.detail = "injection scanner unavailable at promotion boundary"
        return result

    add_candidate = (
        add_candidate_fn if add_candidate_fn is not None else _resolve_add_candidate()
    )
    if add_candidate is None:
        result.outcome = "store_unavailable"
        result.detail = "lessons.add_candidate unavailable (no fallback path)"
        return result

    # -- Delta read ----------------------------------------------------------
    cursor = load_cursor(audit_dir)
    observations, new_offsets, rejected = read_new_observations(
        audit_dir, cursor, to_enum, buckets
    )
    result.events_consumed = len(observations)
    result.observations_rejected = rejected
    if not observations:
        result.outcome = "no_new_events"
        # Advance past rejected/foreign lines so hostile junk is not
        # re-scanned forever; offsets only move over fully parsed lines.
        if new_offsets != cursor:
            result.cursor_advanced = save_cursor(
                audit_dir, new_offsets, now_fn=now_fn
            )
        return result

    # -- Bounded prompt + hard token ceiling ---------------------------------
    prompt = build_prompt(aggregate(observations))
    if estimate_tokens(prompt) > max_input_tokens:
        result.outcome = "token_ceiling"
        result.detail = "estimated prompt tokens {0} > ceiling {1}".format(
            estimate_tokens(prompt), max_input_tokens
        )
        return result

    # -- Model invocation -----------------------------------------------------
    try:
        if fixture_path is not None:
            output, tokens_in, tokens_out, fx_model = load_fixture_output(
                fixture_path
            )
            if fx_model:
                result.model_id = fx_model
        else:
            fn = invoke_fn if invoke_fn is not None else invoke_model_cli
            output, tokens_in, tokens_out = fn(prompt, result.model_id)
    except DistillModelError as exc:
        result.outcome = "model_error"
        result.detail = str(exc)
        return result
    result.tokens_in = tokens_in
    result.tokens_out = tokens_out

    # -- Fail-CLOSED output schema validation ---------------------------------
    candidates, reason = validate_model_output(output)
    if candidates is None:
        result.outcome = "schema_reject"
        result.detail = reason
        return result
    result.candidates_proposed = len(candidates)

    # -- Pre-candidate injection scan + promotion boundary --------------------
    for cand in candidates:
        if scan_candidate_blob(cand, scanner):
            result.rejected_pre_candidate += 1
            sys.stderr.write(
                "[distill-lessons] candidate rejected pre-candidate "
                "(injection scan hit)\n"
            )
            continue
        try:
            lesson_id, status = add_candidate(
                trigger=cand["trigger"],
                advisory_text=cand["advisory_text"],
                scope_tags=list(cand["scope_tags"]),
            )
        except ValueError:
            # lessons.add_candidate raises ValueError on a bounded-
            # vocabulary violation — a boundary REJECT of this candidate
            # (defense-in-depth behind our own schema pass), not a store
            # failure. Skip it; survivors may still be written.
            result.rejected_pre_candidate += 1
            sys.stderr.write(
                "[distill-lessons] candidate rejected at the promotion "
                "boundary (bounded-vocabulary violation)\n"
            )
            continue
        except Exception as exc:
            result.outcome = "store_unavailable"
            result.detail = "add_candidate raised: {0}".format(exc)
            return result
        if status == "PENDING":
            result.candidates_written += 1
            result.written_ids.append(str(lesson_id))
        else:
            result.candidates_quarantined += 1

    # -- Advance cursor only on full success ----------------------------------
    result.cursor_advanced = save_cursor(audit_dir, new_offsets, now_fn=now_fn)
    result.outcome = "ok"
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_EXIT_BY_OUTCOME = {
    "ok": 0,
    "no_new_events": 0,
    "store_unavailable": 2,
    "input_surface_unavailable": 3,
    "schema_reject": 4,
    "scan_unavailable": 5,
    "token_ceiling": 6,
    "model_error": 7,
}


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Offline metadata-rail distiller (PLAN-154 item 2). "
            "Owner-invoked or nightly-hygiene piggyback ONLY — never "
            "per-session automatic."
        ),
    )
    parser.add_argument(
        "--from-fixture",
        default=None,
        help="Path to a RECORDED model output (hermetic mode — CI never "
             "calls a live model).",
    )
    parser.add_argument(
        "--audit-dir",
        default=None,
        help="Override the audit dir (default: CEO_AUDIT_LOG_DIR or "
             "~/.claude/projects/ceo-orchestration).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the model id (default: {0}, env {1}).".format(
            DEFAULT_DISTILL_MODEL, _MODEL_ENV
        ),
    )
    parser.add_argument(
        "--max-input-tokens",
        type=int,
        default=DEFAULT_MAX_INPUT_TOKENS,
        help="Hard per-run input-token ceiling (default {0}).".format(
            DEFAULT_MAX_INPUT_TOKENS
        ),
    )
    parser.add_argument(
        "--print-prompt",
        action="store_true",
        help="Print the would-be prompt and exit — no model call, no "
             "candidate writes, no cursor advance.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    if os.environ.get("CEO_SOTA_DISABLE") == "1":
        sys.stderr.write("[distill-lessons] CEO_SOTA_DISABLE=1 — no-op\n")
        return 0

    audit_dir = Path(args.audit_dir) if args.audit_dir else resolve_audit_dir()

    if args.print_prompt:
        surface = _load_enum_surface()
        if surface is None:
            sys.stderr.write(
                "[distill-lessons] enum surface unavailable — refusing\n"
            )
            return 3
        to_enum, buckets = surface
        observations, _, rejected = read_new_observations(
            audit_dir, load_cursor(audit_dir), to_enum, buckets
        )
        print(build_prompt(aggregate(observations)))
        sys.stderr.write(
            "[distill-lessons] print-prompt: {0} observation(s), {1} "
            "rejected; nothing written\n".format(len(observations), rejected)
        )
        return 0

    fixture_path = Path(args.from_fixture) if args.from_fixture else None
    result = run_distill(
        audit_dir,
        fixture_path=fixture_path,
        max_input_tokens=args.max_input_tokens,
        model=args.model,
    )
    _emit_run_event(result)

    sys.stderr.write(
        "[distill-lessons] outcome={0} events={1} rejected_obs={2} "
        "proposed={3} written={4} quarantined={5} rejected_pre={6} "
        "tokens_in={7} tokens_out={8} cursor_advanced={9}{10}\n".format(
            result.outcome,
            result.events_consumed,
            result.observations_rejected,
            result.candidates_proposed,
            result.candidates_written,
            result.candidates_quarantined,
            result.rejected_pre_candidate,
            result.tokens_in,
            result.tokens_out,
            result.cursor_advanced,
            " detail={0}".format(result.detail) if result.detail else "",
        )
    )
    if result.written_ids:
        print(
            "[distill-lessons] PENDING candidate(s) written: "
            + ", ".join(result.written_ids)
        )
        print("Next: review with /lesson-review (nothing self-activates).")
    return _EXIT_BY_OUTCOME.get(result.outcome, 1)


if __name__ == "__main__":
    sys.exit(main())
