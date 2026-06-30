#!/usr/bin/env python3
"""CLAUDE_ENV_FILE persistence allowlist (PLAN-135 W2 H8).

The Setup-hook self-verification path (and any SessionStart `CLAUDE_ENV_FILE`
export) MUST persist only an EXPLICIT INCLUDE-LIST of `CEO_*` keys across
sessions. This module is the single source of truth for that list.

WHY AN INCLUDE-LIST (not a denylist)
------------------------------------
A denylist of "dangerous" vars is fail-OPEN: the moment a new
override/escape-hatch/kill-switch var is added anywhere in the repo and the
denylist author forgets to extend it, that var leaks into cross-session
persistence — exactly the S185/S197 stale-override class
([[feedback-stale-kernel-override-silently-permits-canonical-edits]] /
[[feedback-stale-kernel-override-silently-permits-canonical-edits]]: a
`CEO_KERNEL_OVERRIDE` / `CEO_GIT_BYPASS_ALLOW{,_ACK}` left armed in a file
silently keeps a bypass on forever). An include-list is fail-CLOSED: an
unrecognised `CEO_*` var is NEVER persisted. New escape hatches default to
non-persistent; only a deliberate edit here can ever add a key.

WHAT IS ALLOWED
---------------
Stable, non-policy IDENTITY / PROJECT-DESCRIPTOR values whose persistence
cannot weaken any governance rail: project/app name, domain, stack labels,
owner identity descriptors. These are the values an installer/`/onboard`
legitimately wants stable across sessions. None of them gates, disables,
bypasses, overrides, acks, enforces, or toggles a hook, a kill-switch, a
credential, an endpoint, or a model.

WHAT IS EXCLUDED (by construction — every override/escape-hatch class)
----------------------------------------------------------------------
- Kernel/canonical overrides ........ CEO_KERNEL_OVERRIDE{,_ACK,_REASON,_BACKUP},
                                      CEO_CANONICAL_GUARD_DISABLE,
                                      CEO_BASH_CANONICAL_BYPASS*
- Git/commit bypass escape hatches .. CEO_GIT_BYPASS_ALLOW{,_ACK},
                                      CEO_ALLOW_NO_VERIFY, CEO_TRUST_BYPASS
- Turbo / quiet bypass .............. CEO_TURBO, CEO_QUIET_MODE_BYPASS, CEO_QUIET_BYPASS_*
- Enforcement toggles ............... CEO_*_ENFORCE, CEO_*_ENFORCING,
                                      CEO_ENV_GUARD_ENFORCE, CEO_GODMODE_ENFORCING
- Kill-switches / disables .......... CEO_*_DISABLE, CEO_HOOKS_DISABLE,
                                      CEO_SKIP_HOOKS, CEO_AUDIT_HMAC_DISABLE, …
- Credential / endpoint remaps ...... CEO_*_KEY, CEO_*_TOKEN, CEO_*_URL,
                                      CEO_*_ENDPOINT, CEO_OWNER_GPG_KEY, …
- Confirmation / ACK suppressors .... CEO_*_ACK, CEO_CONFIRM_SKIP,
                                      CEO_CONFIDENCE_AUTO_CONFIRM, CEO_*_SKIP

The exclusion is GUARANTEED by membership, not by pattern: a var is persisted
iff it is literally in ``ENV_PERSIST_ALLOWLIST``. The regression test
(``test_env_persist_allowlist.py``) additionally PROVES, by grepping the live
repo for the override/escape-hatch/kill-switch families, that not one of them
ever slipped into the allowlist.

This module is stdlib-only, Python >= 3.9, side-effect-free (pure data + a
filter function). It performs NO I/O and reads NO environment.
"""
from __future__ import annotations

from typing import Dict, Mapping, Optional


# ---------------------------------------------------------------------------
# THE ALLOWLIST. Explicit include-list. Every entry is a stable, non-policy
# identity/project-descriptor value. Adding a key here is a deliberate,
# reviewed act — and the regression test will reject any key matching an
# override/escape-hatch/enforcement/kill-switch family.
#
# CASE-SENSITIVE exact match (POSIX env var names are case-sensitive).
# ---------------------------------------------------------------------------
ENV_PERSIST_ALLOWLIST = frozenset({
    # --- project / app identity (descriptive labels, never policy) ---
    "CEO_PROJECT_NAME",     # human project name (e.g. "acme-spread-analysis")
    "CEO_APP_NAME",         # app/product display name
    "CEO_DOMAIN",           # installed domain profile label (e.g. "fintech")
    "CEO_STACK",            # backend stack label (e.g. "node") — descriptor, not a toggle
    "CEO_FRONTEND_STACK",   # frontend stack label — descriptor, not a toggle
    # --- owner identity descriptors (non-secret; the GPG *key/fingerprint*
    #     and any *_TOKEN/_KEY are EXCLUDED — only the human-name label) ---
    "CEO_OWNER",            # owner display name
    "CEO_FOUNDER_NAME",     # founder/owner display name
    "CEO_CITY",             # operator locale descriptor
    "CEO_COUNTRY",          # operator locale descriptor
})


# Families whose names imply they MUST NEVER be persisted. Used as a
# defence-in-depth guard inside ``filter_persistable`` (so even a future
# accidental allowlist edit is caught at runtime), AND mirrored by the
# regression test's grep-derived exclusion proof. Substring match,
# case-sensitive, applied to the bare key.
#
# NOTE: this is NOT the persistence mechanism (membership in the allowlist
# is). It is a redundant fail-closed tripwire: if a key is somehow BOTH in
# the allowlist AND matches a forbidden family, the family wins and the key
# is dropped. The regression test asserts the allowlist and these families
# are disjoint, so in correct states this guard never fires — but it makes a
# mis-edit non-exploitable rather than merely test-failing.
_FORBIDDEN_KEY_SUBSTRINGS = (
    "OVERRIDE",
    "BYPASS",
    "DISABLE",
    "ENFORC",     # ENFORCE / ENFORCING / ENFORCEMENT
    "_ACK",
    "ALLOW",      # CEO_GIT_BYPASS_ALLOW, CEO_ALLOW_NO_VERIFY, CEO_MCP_ALLOW_*
    "TURBO",
    "_KILL",
    "SKIP",
    "_KEY",       # credentials
    "_TOKEN",     # credentials
    "_SECRET",
    "_URL",       # endpoint remap
    "ENDPOINT",
    "GODMODE",
    "DANGEROUS",
    "NO_VERIFY",
)


def _is_forbidden_family(key: str) -> bool:
    """True if a key name matches a never-persist family (defence-in-depth)."""
    return any(token in key for token in _FORBIDDEN_KEY_SUBSTRINGS)


def is_persistable(key: str) -> bool:
    """A key may be persisted iff it is explicitly allowlisted AND does not
    match a forbidden family. Fail-closed: anything unknown returns False."""
    if not isinstance(key, str):
        return False
    if key not in ENV_PERSIST_ALLOWLIST:
        return False
    # Redundant tripwire — a correct allowlist never trips this (test-proven
    # disjoint), but a future mis-edit is rendered non-exploitable.
    if _is_forbidden_family(key):
        return False
    return True


def filter_persistable(env: Optional[Mapping[str, str]]) -> Dict[str, str]:
    """Return ONLY the persistable subset of ``env`` (an env-like mapping),
    preserving string values. Non-string values are dropped. Pure function;
    never reads ``os.environ`` itself — the caller passes the snapshot."""
    out: Dict[str, str] = {}
    if not env:
        return out
    for key, value in env.items():
        if is_persistable(key) and isinstance(value, str):
            out[key] = value
    return out
