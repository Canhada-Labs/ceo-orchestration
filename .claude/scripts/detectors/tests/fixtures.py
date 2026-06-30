"""PLAN-047 Phase 1 — shared test fixtures for detectors.

Hand-crafted event dicts conforming to AUDIT-LOG-SCHEMA.md §2.
No external corpus consulted (clean-room per Phase 0 declaration).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


_BASE_TS = datetime(2026, 4, 21, 10, 0, 0, tzinfo=timezone.utc)


def _hash(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def make_event(
    *,
    offset_minutes: float = 0.0,
    action: str = "agent_spawn",
    session_id: str = "sess-1",
    subagent_type: str = "general-purpose",
    skill: str = "unknown",
    desc_seed: str = "task-a",
    has_profile: bool = True,
    has_file_assignment: bool = True,
    prompt_len_bucket: str = "<4096",
    response_kind: str = "object",
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    tokens_total: Optional[int] = None,
    model: Optional[str] = "claude-opus-4-7",
    rail: Optional[str] = "native",
    hook_duration_ms: int = 3,
    cache_coverage: Optional[float] = None,
    usage_metadata: Optional[Dict[str, Any]] = None,
    tool: str = "Agent",
    project: str = "/Users/owner/ceo-orchestration",
) -> Dict[str, Any]:
    ts = (_BASE_TS + timedelta(minutes=offset_minutes)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    return {
        "ts": ts,
        "action": action,
        "session_id": session_id,
        "project": project,
        "tool": tool,
        "subagent_type": subagent_type,
        "desc_preview": desc_seed,
        "desc_hash": _hash(desc_seed),
        "skill": skill,
        "has_profile": has_profile,
        "has_file_assignment": has_file_assignment,
        "prompt_len_bucket": prompt_len_bucket,
        "response_kind": response_kind,
        "hook_duration_ms": hook_duration_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_total": tokens_total,
        "usage_metadata": usage_metadata,
        "cache_coverage": cache_coverage,
        "rail": rail,
        "model": model,
    }


def write_log(tmp_path: Path, events: List[Dict[str, Any]]) -> Path:
    """Serialize ``events`` as JSONL and return the path."""
    path = tmp_path / "audit-log.jsonl"
    path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )
    return path


# --------------------------------------------------------------------------
# retry_churn fixtures
# --------------------------------------------------------------------------

def events_positive_retry_churn() -> List[Dict[str, Any]]:
    """3 spawns same (session, subagent, skill) within 30min, same bucket."""
    return [
        make_event(
            offset_minutes=0,
            session_id="sess-R",
            subagent_type="code-reviewer",
            skill="code-review-checklist",
            desc_seed="retry-a",
            prompt_len_bucket="<4096",
        ),
        make_event(
            offset_minutes=10,
            session_id="sess-R",
            subagent_type="code-reviewer",
            skill="code-review-checklist",
            desc_seed="retry-b",
            prompt_len_bucket="<4096",
        ),
        make_event(
            offset_minutes=25,
            session_id="sess-R",
            subagent_type="code-reviewer",
            skill="code-review-checklist",
            desc_seed="retry-c",
            prompt_len_bucket="<4096",
        ),
    ]


def events_negative_retry_churn_too_few() -> List[Dict[str, Any]]:
    """Only 2 spawns — below threshold."""
    return events_positive_retry_churn()[:2]


def events_negative_retry_churn_different_subagent() -> List[Dict[str, Any]]:
    """3 spawns same session/skill but different subagent_type each."""
    base = events_positive_retry_churn()
    base[0]["subagent_type"] = "code-reviewer"
    base[1]["subagent_type"] = "qa-architect"
    base[2]["subagent_type"] = "security-engineer"
    return base


def events_negative_retry_churn_over_window() -> List[Dict[str, Any]]:
    """3 spawns but last one 45min after first — out of window."""
    base = events_positive_retry_churn()
    base[2] = make_event(
        offset_minutes=45,
        session_id="sess-R",
        subagent_type="code-reviewer",
        skill="code-review-checklist",
        desc_seed="retry-c",
        prompt_len_bucket="<4096",
    )
    return base


def events_negative_retry_churn_different_bucket() -> List[Dict[str, Any]]:
    """3 spawns but prompt_len_bucket varies."""
    base = events_positive_retry_churn()
    base[0]["prompt_len_bucket"] = "<256"
    base[1]["prompt_len_bucket"] = "<16384"
    base[2]["prompt_len_bucket"] = "<65536"
    return base


# --------------------------------------------------------------------------
# tool_cascade fixtures
# --------------------------------------------------------------------------

def events_positive_tool_cascade() -> List[Dict[str, Any]]:
    """5 consecutive spawns same session, object response, tokens_out<500."""
    return [
        make_event(
            offset_minutes=float(idx),
            session_id="sess-TC",
            subagent_type="Explore",
            tokens_out=100 + idx * 50,
            response_kind="object",
            desc_seed=f"cascade-{idx}",
        )
        for idx in range(5)
    ]


def events_negative_tool_cascade_too_few() -> List[Dict[str, Any]]:
    return events_positive_tool_cascade()[:4]


def events_negative_tool_cascade_multi_session() -> List[Dict[str, Any]]:
    base = events_positive_tool_cascade()
    base[2]["session_id"] = "sess-OTHER"
    base[3]["session_id"] = "sess-OTHER"
    return base


def events_negative_tool_cascade_large_tokens() -> List[Dict[str, Any]]:
    base = events_positive_tool_cascade()
    for event in base:
        event["tokens_out"] = 2000
    return base


def events_negative_tool_cascade_non_object() -> List[Dict[str, Any]]:
    base = events_positive_tool_cascade()
    for event in base:
        event["response_kind"] = "text"
    return base


# --------------------------------------------------------------------------
# looping fixtures
# --------------------------------------------------------------------------

def events_positive_looping() -> List[Dict[str, Any]]:
    """3 spawns same subagent, has_file_assignment=True, similar desc_hash.

    We seed with strings that hash to the same first-8-hex-char prefix by
    brute-forcing seeds — but simpler: we use desc_seed "loop-core" thrice
    with tiny time offsets so the desc_hash is identical across all three.
    """
    return [
        make_event(
            offset_minutes=0,
            subagent_type="qa-architect",
            has_file_assignment=True,
            desc_seed="loop-core",
        ),
        make_event(
            offset_minutes=5,
            subagent_type="qa-architect",
            has_file_assignment=True,
            desc_seed="loop-core",
        ),
        make_event(
            offset_minutes=15,
            subagent_type="qa-architect",
            has_file_assignment=True,
            desc_seed="loop-core",
        ),
    ]


def events_negative_looping_too_few() -> List[Dict[str, Any]]:
    return events_positive_looping()[:2]


def events_negative_looping_different_subagent() -> List[Dict[str, Any]]:
    base = events_positive_looping()
    base[2]["subagent_type"] = "Explore"
    return base


def events_negative_looping_no_file_assignment() -> List[Dict[str, Any]]:
    base = events_positive_looping()
    for event in base:
        event["has_file_assignment"] = False
    return base


def events_negative_looping_different_desc() -> List[Dict[str, Any]]:
    """3 spawns but each has a distinct desc_seed → different desc_hash prefixes."""
    return [
        make_event(
            offset_minutes=0,
            subagent_type="qa-architect",
            has_file_assignment=True,
            desc_seed="alpha-task",
        ),
        make_event(
            offset_minutes=5,
            subagent_type="qa-architect",
            has_file_assignment=True,
            desc_seed="beta-task",
        ),
        make_event(
            offset_minutes=15,
            subagent_type="qa-architect",
            has_file_assignment=True,
            desc_seed="gamma-task",
        ),
    ]


# --------------------------------------------------------------------------
# wasteful_thinking fixtures
# --------------------------------------------------------------------------

def events_positive_wasteful_thinking() -> List[Dict[str, Any]]:
    """Opus + short bucket + non-VETO subagent (Explore / general-purpose)."""
    return [
        make_event(
            model="claude-opus-4-7",
            prompt_len_bucket="<256",
            subagent_type="Explore",
            desc_seed="wt-a",
        ),
        make_event(
            model="claude-opus-4-7",
            prompt_len_bucket="<1024",
            subagent_type="general-purpose",
            offset_minutes=5,
            desc_seed="wt-b",
        ),
    ]


def events_negative_wasteful_thinking_large_bucket() -> List[Dict[str, Any]]:
    base = events_positive_wasteful_thinking()
    for event in base:
        event["prompt_len_bucket"] = "<16384"
    return base


def events_negative_wasteful_thinking_veto_subagent() -> List[Dict[str, Any]]:
    base = events_positive_wasteful_thinking()
    base[0]["subagent_type"] = "code-reviewer"
    base[1]["subagent_type"] = "security-engineer"
    return base


def events_negative_wasteful_thinking_non_opus() -> List[Dict[str, Any]]:
    base = events_positive_wasteful_thinking()
    for event in base:
        event["model"] = "claude-sonnet-4-6"
    return base


def events_negative_wasteful_thinking_haiku() -> List[Dict[str, Any]]:
    base = events_positive_wasteful_thinking()
    for event in base:
        event["model"] = "claude-haiku-4-5"
    return base


# --------------------------------------------------------------------------
# weak_model fixtures
# --------------------------------------------------------------------------

def events_positive_weak_model() -> List[Dict[str, Any]]:
    """Haiku on VETO role (code-reviewer / security-engineer)."""
    return [
        make_event(
            model="claude-haiku-4-5",
            subagent_type="code-reviewer",
            desc_seed="wm-a",
        ),
        make_event(
            model="claude-haiku-4-5",
            subagent_type="security-engineer",
            offset_minutes=10,
            desc_seed="wm-b",
        ),
    ]


def events_negative_weak_model_opus_on_veto() -> List[Dict[str, Any]]:
    base = events_positive_weak_model()
    for event in base:
        event["model"] = "claude-opus-4-7"
    return base


def events_negative_weak_model_haiku_on_non_veto() -> List[Dict[str, Any]]:
    base = events_positive_weak_model()
    base[0]["subagent_type"] = "Explore"
    base[1]["subagent_type"] = "general-purpose"
    return base


def events_negative_weak_model_sonnet_on_veto() -> List[Dict[str, Any]]:
    base = events_positive_weak_model()
    for event in base:
        event["model"] = "claude-sonnet-4-6"
    return base


def events_negative_weak_model_null_model() -> List[Dict[str, Any]]:
    base = events_positive_weak_model()
    for event in base:
        event["model"] = None
    return base


# --------------------------------------------------------------------------
# overpowered fixtures
# --------------------------------------------------------------------------

def events_positive_overpowered() -> List[Dict[str, Any]]:
    """Opus/Sonnet on devops with short bucket."""
    return [
        make_event(
            model="claude-opus-4-7",
            subagent_type="devops",
            prompt_len_bucket="<256",
            desc_seed="op-a",
        ),
        make_event(
            model="claude-sonnet-4-6",
            subagent_type="devops",
            prompt_len_bucket="<1024",
            offset_minutes=5,
            desc_seed="op-b",
        ),
    ]


def events_negative_overpowered_haiku() -> List[Dict[str, Any]]:
    base = events_positive_overpowered()
    for event in base:
        event["model"] = "claude-haiku-4-5"
    return base


def events_negative_overpowered_non_devops() -> List[Dict[str, Any]]:
    base = events_positive_overpowered()
    base[0]["subagent_type"] = "Explore"
    base[1]["subagent_type"] = "general-purpose"
    return base


def events_negative_overpowered_large_bucket() -> List[Dict[str, Any]]:
    base = events_positive_overpowered()
    for event in base:
        event["prompt_len_bucket"] = "<16384"
    return base


def events_negative_overpowered_null_model() -> List[Dict[str, Any]]:
    base = events_positive_overpowered()
    for event in base:
        event["model"] = None
    return base
