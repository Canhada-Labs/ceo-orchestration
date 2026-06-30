"""PLAN-099-FOLLOWUP Wave D — federation write-endpoint handlers package.

Staged at .claude/plans/PLAN-099-FOLLOWUP/wave-d-staging/handlers/.
Owner ``git mv`` to ``.claude/hooks/_lib/federation/handlers/`` at
Phase A2-post.

Each handler module implements ONE write endpoint per the 4-route
table in ADR-135-AMEND-1 §2.1. The server's route dispatcher calls
the handler's ``handle(peer_row, headers, body)`` function AFTER all
11 gates have passed (gates #1-10 enforced by the dispatcher;
gate #11 is the handler itself).

STDLIB-ONLY per ADR-126 §Part 6 — no ``cryptography`` package. Atomic
writes use same-directory tmpfile + fsync + os.rename (Wave B Codex
P0 lesson — cross-FS mv risk).

WAVE-F-PENDING — all federation_* audit emit calls go through the
:func:`_safe_emit` shim. The kernel-override ``PLAN-099-FOLLOWUP-WAVE-F
-AUDIT-EMIT-EXTENSION`` registers them at Wave F.2 (net +19 actions
post-PLAN-110 baseline 235 → 254).
"""

from __future__ import annotations

__all__ = [
    "peer_register",
    "audit_event_push",
    "audit_event_batch",
    "peer_revoke",
]
