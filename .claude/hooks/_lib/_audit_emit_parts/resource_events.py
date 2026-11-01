"""Resource events.

Internal declarations exported by the audit_emit compatibility facade.
"""

from __future__ import annotations

__all__ = ('emit_skill_patch_applied', 'emit_squad_imported', 'emit_state_store_pruned', 'emit_lesson_outcome_undone')

def emit_skill_patch_applied(
    proposal_id: str,
    skill_slug: str,
    commit_sha: str,
    signer_fingerprint: str = "",
    shadow_mode: bool = False,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a skill_patch_applied event (Sprint 11 Phase 4, ADR-031).

    Fired by ``skill-patch-apply.py`` when a proposal is merged via
    signed Owner approval. ``shadow_mode=True`` during the 7-day shadow
    period per CR1; ``False`` after promotion to real SKILL.md.
    """
    event: Dict[str, Any] = {
        "action": "skill_patch_applied",
        "proposal_id": proposal_id,
        "skill_slug": skill_slug,
        "commit_sha": commit_sha,
        "signer_fingerprint": signer_fingerprint,
        "shadow_mode": bool(shadow_mode),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_squad_imported(
    squad_name: str,
    manifest_sha256: str,
    signer_fingerprint: str = "",
    source: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a squad_imported event (Sprint 11 Phase 12, CR2).

    Fired by ``squad-import.py`` after signature verification passes.
    ``source`` is the pin-allowlist entry (e.g.
    ``"github.com/acme/squad-edtech@v1"``).
    """
    event: Dict[str, Any] = {
        "action": "squad_imported",
        "squad_name": squad_name,
        "manifest_sha256": manifest_sha256,
        "signer_fingerprint": signer_fingerprint,
        "source": source,
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_state_store_pruned(
    store_name: str,
    plan_id_hash: str,
    keys_pruned_count: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a state_store prune event (Sprint 11 Phase 0, ADR-027).

    Emitted by ``SqliteStateStore.prune_expired()`` (TTL sweep) and
    ``clear_plan()`` (plan rollback). A single event covers a batch.
    """
    event: Dict[str, Any] = {
        "action": "state_store_pruned",
        "store_name": store_name,
        "plan_id_hash": plan_id_hash,
        "keys_pruned_count": int(keys_pruned_count),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)


def emit_lesson_outcome_undone(
    lesson_id: str,
    archetype: str,
    consumer: str,
    undone_kind: str,
    hit_count: int = 0,
    miss_count: int = 0,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit a lesson_outcome_undone event (PLAN-009 P3.3, schema v2.3).

    Admin-facing escape hatch for reversing a bad attribution. Emitted
    by `lessons.undo_outcome()` after the decrement is persisted.

    ``undone_kind`` is "hit" or "miss" — which counter was decremented.
    """
    event: Dict[str, Any] = {
        "action": "lesson_outcome_undone",
        "lesson_id": lesson_id,
        "archetype": archetype,
        "consumer": consumer,
        "undone_kind": undone_kind,
        "hit_count": int(hit_count),
        "miss_count": int(miss_count),
        "session_id": session_id,
        "project": project,
    }
    _write_event(event)
