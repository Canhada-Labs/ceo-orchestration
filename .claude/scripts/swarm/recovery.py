"""PLAN-017 Phase 3 — recovery + checkpoint + graceful halt plumbing.

Kill-switch expansion per P06 scaffold:
- graceful halt emits ``swarm_killed`` audit-log event + preserves
  worktrees (actual worktree orchestration lands in follow-up)
- ``--resume <swarm_id>`` CLI flag reconstructs state from a JSON
  checkpoint file written on each kill-switch evaluation
- ``SwarmCheckpoint`` dataclass is the on-disk contract

The audit-event emission in this scaffold writes a single-line JSONL
record to a supplied path (default None → no emission). Real wiring
into ``_lib/audit_emit.py`` `emit_generic` + the new
``swarm_*`` action allowlist extension is staged for Owner kernel
batch — the follow-up sprint applies it, which is why this module
stays in the scripts tree (non-canonical) rather than `_lib/`.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .coordinator import LoopState
from .kill_switch import KillSwitchState


CHECKPOINT_SCHEMA_VERSION = 1


@dataclass
class SwarmCheckpoint:
    """On-disk snapshot for ``--resume``.

    Intentionally flat + JSON-serializable. Compatible with audit-log
    v2.7 reader conventions (UTC ISO-8601 timestamps, stringified ids).

    The coordinator writes a checkpoint every N iterations (tunable via
    ``settings.json`` ``autonomous_loops.checkpoint_every``, default
    every iteration for scaffold safety).
    """

    swarm_id: str
    created_at: str  # ISO-8601 UTC
    schema_version: int = CHECKPOINT_SCHEMA_VERSION
    goal: str = ""
    n_loops: int = 0
    budget_tokens: int = 0
    loops: Dict[str, Dict[str, object]] = field(default_factory=dict)
    last_decision: str = "continue"
    last_reasons: List[str] = field(default_factory=list)
    loops_to_kill: List[str] = field(default_factory=list)
    worktrees_preserved: List[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, payload: str) -> "SwarmCheckpoint":
        data = json.loads(payload)
        sv = data.get("schema_version", CHECKPOINT_SCHEMA_VERSION)
        if sv != CHECKPOINT_SCHEMA_VERSION:
            raise ValueError(
                f"checkpoint schema_version {sv!r} unsupported "
                f"(expected {CHECKPOINT_SCHEMA_VERSION})"
            )
        return cls(
            swarm_id=str(data["swarm_id"]),
            created_at=str(data["created_at"]),
            schema_version=int(data["schema_version"]),
            goal=str(data.get("goal", "")),
            n_loops=int(data.get("n_loops", 0)),
            budget_tokens=int(data.get("budget_tokens", 0)),
            loops=dict(data.get("loops") or {}),
            last_decision=str(data.get("last_decision", "continue")),
            last_reasons=list(data.get("last_reasons") or []),
            loops_to_kill=list(data.get("loops_to_kill") or []),
            worktrees_preserved=list(data.get("worktrees_preserved") or []),
        )


def build_checkpoint(
    *,
    swarm_id: str,
    goal: str,
    budget_tokens: int,
    loops: Dict[str, LoopState],
    kill_state: Optional[KillSwitchState] = None,
    worktrees_preserved: Optional[List[str]] = None,
) -> SwarmCheckpoint:
    """Materialize a ``SwarmCheckpoint`` from live coordinator state."""

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )
    ks = kill_state or KillSwitchState()
    return SwarmCheckpoint(
        swarm_id=swarm_id,
        created_at=now,
        goal=goal,
        n_loops=len(loops),
        budget_tokens=budget_tokens,
        loops={lid: state.to_dict() for lid, state in loops.items()},
        last_decision=ks.decision,
        last_reasons=list(ks.reasons),
        loops_to_kill=list(ks.loops_to_kill),
        worktrees_preserved=list(worktrees_preserved or []),
    )


def save_checkpoint(checkpoint: SwarmCheckpoint, path: Path) -> None:
    """Atomic write-via-rename (POSIX guarantee).

    Directory must exist. Writes to ``<path>.tmp-<pid>`` then renames.
    Caller owns ``path.parent`` creation.
    """

    if not path.parent.exists():
        raise FileNotFoundError(f"parent directory missing: {path.parent}")

    # Atomic via NamedTemporaryFile in the same dir + os.replace.
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(checkpoint.to_json())
        tmp.flush()
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def load_checkpoint(path: Path) -> SwarmCheckpoint:
    """Load checkpoint or raise FileNotFoundError / ValueError."""

    if not path.exists():
        raise FileNotFoundError(str(path))
    return SwarmCheckpoint.from_json(path.read_text(encoding="utf-8"))


def emit_swarm_killed_event(
    *,
    swarm_id: str,
    reasons: List[str],
    loops_killed: List[str],
    event_log_path: Optional[Path] = None,
) -> Dict[str, object]:
    """Produce a ``swarm_killed`` audit-log record (scaffold).

    Returns the record as a dict. When ``event_log_path`` is provided
    and the parent directory exists, the record is appended as a JSONL
    line. Real wiring into ``_lib/audit_emit.emit_generic`` waits for
    Owner kernel batch (new ``_KNOWN_ACTIONS`` entries: ``swarm_started``,
    ``swarm_iteration``, ``swarm_halted_budget``, ``swarm_halted_kill``,
    ``swarm_killed``, ``swarm_tournament_selected``).
    """

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )
    record: Dict[str, object] = {
        "action": "swarm_killed",
        "ts": now,
        "swarm_id": swarm_id,
        "reasons": list(reasons),
        "loops_killed": list(loops_killed),
        "source": "scripts/swarm/recovery.py",
    }
    if event_log_path is not None and event_log_path.parent.exists():
        with event_log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record
