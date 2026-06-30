"""PLAN-043 — Single source-of-truth for security-critical constants.

Per Round 1 debate convergent closure C-P0-3 (VETO floor defense-in-
depth structural), VETO_HARDCODE is defined here and imported by
``learn.py`` at gate entry. A SEPARATE independent literal
``VETO_HARDCODE_APPLY`` is defined inside ``apply.py`` (NOT imported
from this module) to provide structural defense-in-depth: even if an
attacker edits learn.py to set VETO_HARDCODE = {}, apply.py's
independent literal + module-load-time SHA256 byte-identity assertion
blocks the demote before any frontmatter write.

The frozen SHA256 anchor ``VETO_HARDCODE_FROZEN_SHA256`` is computed
over a canonical JSON encoding of the single-source dict and asserted
at module-load in ``learn.py`` + used to verify ``VETO_HARDCODE_APPLY``
byte-identity in ``apply.py``'s own assertion.

This pattern makes VETO floor tampering require simultaneous compromise
of BOTH learn.py AND apply.py literals AND the frozen SHA256 constant —
a much higher bar than editing a single Python line.

See ADR-064 DRAFT §Amended Decision 2.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict

try:
    from typing import Final
except ImportError:  # Python < 3.8 fallback
    Final = None  # type: ignore[assignment,misc]


# VETO-floor roles + their pinned model IDs. These roles hold merge /
# auth VETO authority per ADR-052 §Decision; any demote recommendation
# touching these roles MUST be rejected at gate entry with
# ``tier_policy_rejected/rejection_reason=veto_floor`` audit event.
#
# Canonical keys = 5-canonical-5 agent slugs (as used in
# ``.claude/agents/<slug>.md``). Values = full Anthropic model IDs
# per ADR-052 canonical form (C-P0-9 full-model-ID-throughout closure).
VETO_HARDCODE: "Final[Dict[str, str]]" = {
    "code-reviewer": "claude-fable-5",
    "security-engineer": "claude-fable-5",
}


def _compute_canonical_sha256(d: Dict[str, str]) -> str:
    """Canonical JSON encoding + SHA256 for byte-identity assertion.

    Uses sorted keys + compact separators matching
    ``_lib.canonical_json`` policy so the hash is stable across
    Python versions / platforms.
    """
    encoded = json.dumps(
        d, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


# Frozen SHA256 anchor — used by ``learn.py`` at module load + by
# ``apply.py`` to verify its INDEPENDENT literal matches. Regenerate
# this constant when VETO_HARDCODE intentionally changes (Owner-signed
# ADR amendment).
VETO_HARDCODE_FROZEN_SHA256: str = _compute_canonical_sha256(VETO_HARDCODE)


def assert_veto_hardcode_integrity(
    candidate: Dict[str, str],
    *,
    frozen_sha256: str = VETO_HARDCODE_FROZEN_SHA256,
) -> None:
    """Raise AssertionError if ``candidate`` diverges from frozen anchor.

    Used by learn.py + apply.py at module load to detect tamper. The
    frozen_sha256 parameter allows apply.py to pass its own frozen
    constant (defense in depth — apply.py does NOT trust
    learn.py's import).

    :raises AssertionError: on mismatch (module load fails fast; caller
        MUST catch + abort with audit event).
    """
    actual = _compute_canonical_sha256(candidate)
    if actual != frozen_sha256:
        raise AssertionError(
            "VETO_HARDCODE byte-identity violation: "
            "expected sha256={exp} got sha256={got}".format(
                exp=frozen_sha256, got=actual
            )
        )
