"""STDLIB-ONLY — federation per-method RBAC matrix.

Staged at .claude/plans/PLAN-099-FOLLOWUP/wave-d-staging/scopes.py.
Owner ``git mv`` to ``.claude/hooks/_lib/federation/scopes.py`` at
Phase A2-post of the PLAN-099-FOLLOWUP ceremony (canonical-edit guard
blocks direct writes to federation/, hence the staging convention).

ADR-135-AMEND-1 §2.1: 4-route lock. New routes require ADR-135-AMEND-2
+ PLAN-099-FOLLOWUP-NEXT. The matrix here is the SOLE source of truth
for the dispatcher's gate #4 (method allowlist) + gate #5 (scope
header) + gate #6 (peer scope grant) + gate #10 (destructive-op
Owner-co-sign).

## Surface

- :data:`ROUTE_TO_SCOPE` — frozen (method, path) → scope-name map.
- :func:`route_required_scope` — gate #4 lookup.
- :func:`peer_has_scope` — gate #6 lookup against peer row.
- :func:`validate_scope_header` — gate #5 header match.
- :func:`is_destructive_route` — gate #10 classifier.

ALL functions are pure + total: no I/O, no exceptions raised on bad
input — bogus headers / missing rows / unknown routes return False /
None per ADR-135-AMEND-1 §2.2 fail-CLOSED contract.
"""

from __future__ import annotations

import re
from typing import List, Mapping, Optional


__all__ = [
    "ROUTE_TO_SCOPE",
    "DESTRUCTIVE_SCOPES",
    "route_required_scope",
    "peer_has_scope",
    "validate_scope_header",
    "is_destructive_route",
]


# ADR-135-AMEND-1 §2.1 — locked 4-route table. NEW routes require an
# ADR amend AND a new top-level plan. SOLE source of truth — server
# dispatcher MUST consult `route_required_scope` (no hard-coded paths).
ROUTE_TO_SCOPE: Mapping[tuple, str] = {
    ("POST", "/federation/peer-register"): "peer_register",
    ("POST", "/federation/audit-event"): "audit_event_push",
    ("POST", "/federation/audit-event/batch"): "audit_event_push_batch",
    ("POST", "/federation/peer-revoke"): "peer_revoke",
}


# Destructive ops per ADR-135-AMEND-1 §2.5 (T1485 + T1565). Require
# per-request Owner-co-sign sentinel (gate #10).
DESTRUCTIVE_SCOPES: frozenset = frozenset({
    "peer_register",
    "peer_revoke",
})


# Scope-name charset — alphanumeric + underscore. Strict to prevent
# CR/LF/NUL/path-traversal header smuggling at gate #5.
_SCOPE_NAME_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")


def route_required_scope(method: str, path: str) -> Optional[str]:
    """Return the scope name bound to (method, path), else None.

    Gate #4 (method allowlist) in ADR-135-AMEND-1 §2.2: only routes in
    :data:`ROUTE_TO_SCOPE` pass. None → 405 + ``federation_write_attempt_blocked``.

    Path is EXACT-match — caller MUST strip query + fragment first.
    """
    if not isinstance(method, str) or not isinstance(path, str):
        return None
    key = (method.upper(), path)
    return ROUTE_TO_SCOPE.get(key)


def peer_has_scope(peer_row: Mapping, scope_name: str) -> bool:
    """Return True iff peer_row['scopes'] contains scope_name.

    Gate #6 in ADR-135-AMEND-1 §2.2. Case-sensitive exact match per §2.1.

    Default behaviour: peer rows without ``scopes`` (legacy v1.x) OR
    with ``scopes: []`` (empty) have NO write authority. Read-only is
    the natural-default-OFF position per ADR-135 §Part 7.
    """
    if not isinstance(peer_row, Mapping):
        return False
    if not isinstance(scope_name, str) or not scope_name:
        return False
    scopes = peer_row.get("scopes")
    if not isinstance(scopes, (list, tuple, frozenset, set)):
        return False
    for granted in scopes:
        if isinstance(granted, str) and granted == scope_name:
            return True
    return False


def validate_scope_header(
    headers: Mapping[str, str],
    expected_scope: str,
) -> bool:
    """Return True iff ``X-CEO-Federation-Scope`` header == expected_scope.

    Gate #5 in ADR-135-AMEND-1 §2.2 — defense-in-depth. Even when path
    and peer agree, the request must DECLARE the scope it expects (to
    prevent path-only-check scope widening, e.g. by an HTTP proxy that
    rewrites path prefixes).

    Charset is strict per :data:`_SCOPE_NAME_RE` — refuses CR/LF, NUL,
    path-traversal injection. Lookup is case-INSENSITIVE per HTTP/1.1
    §4.2. Value comparison is case-SENSITIVE per §2.1.
    """
    if not isinstance(expected_scope, str) or not expected_scope:
        return False
    # PLAN-112-FOLLOWUP-federation-wire (PHASE2) — accept BOTH a Mapping
    # AND an ``email.message.Message`` (what BaseHTTPRequestHandler exposes
    # as ``self.headers``). The dispatcher passes ``self.headers`` directly;
    # an HTTPMessage is NOT a collections.abc.Mapping, so the old strict
    # isinstance check rejected EVERY real request at Gate #5 (write-mode
    # was unreachable over a live socket — caught by the mTLS integration
    # test, masked by the dict-based method-level tests). Duck-type on a
    # callable ``items()`` (read-only; safe).
    items_fn = getattr(headers, "items", None)
    if not callable(items_fn):
        return False

    # PLAN-112-FOLLOWUP-federation-wire (PHASE2, Codex AC18 P2) — fail-CLOSED
    # on a DUPLICATED scope header. An HTTPMessage can carry the same header
    # twice; "first wins" is ambiguous HTTP semantics an attacker could use to
    # desync proxy-vs-app scope evaluation. Collect ALL matching values and
    # reject if more than one is present.
    matches: List[str] = []
    for k, v in items_fn():
        if isinstance(k, str) and k.lower() == "x-ceo-federation-scope":
            matches.append(v if isinstance(v, str) else "")
    if len(matches) != 1:
        return False
    presented: Optional[str] = matches[0]

    if presented is None:
        return False

    if not _SCOPE_NAME_RE.match(presented):
        return False

    return presented == expected_scope


def is_destructive_route(method: str, path: str) -> bool:
    """Return True iff (method, path) is destructive per ADR-135-AMEND-1 §2.5.

    Gate #10 — destructive routes (peer_register + peer_revoke)
    require a per-request Owner-co-sign sentinel referenced by
    ``X-CEO-Owner-Sigref`` header. audit_event_push +
    audit_event_push_batch are NOT destructive.

    Unknown routes fail at gate #4 (405) before gate #10 runs; this
    function still returns False for them defensively.
    """
    scope = route_required_scope(method, path)
    if scope is None:
        return False
    return scope in DESTRUCTIVE_SCOPES
