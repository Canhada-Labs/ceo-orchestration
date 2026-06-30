"""PLAN-104 Wave C — persona-waive trailer/annotation parser.

Stdlib only. Parses two waive surface forms from commit messages:

  Git trailer (preferred, RFC 5322 trailer syntax + lowercased token):
    Persona-Waive: security-engineer:generated-or-vendored

  In-body annotation (legacy / inline):
    [persona-waive: code-reviewer reason=docs-only]

Both forms accept a closed enum for `reason`:
  - docs-only
  - generated-or-vendored
  - emergency-hotfix
  - explicit-skip

Free-text reasons are REJECTED (parse returns no record). NFKC-normalized
input; case-insensitive token match. One waive per (persona,
demand_event_type) suppresses the unmet emit; multiple waives are
de-duplicated by the caller via the demand_id surface.

PLAN-104 §2.5 (S134 R2 Q5 fold — `automation-tested` removed as too gameable).
"""

from __future__ import annotations

import re
import unicodedata
from typing import List, NamedTuple, Optional

WAIVE_REASONS = frozenset({
    "docs-only",
    "generated-or-vendored",
    "emergency-hotfix",
    "explicit-skip",
})

WAIVE_PERSONAS = frozenset({
    "code-reviewer",
    "security-engineer",
    "qa-architect",
    "threat-detection-engineer",
})


class Waive(NamedTuple):
    """Parsed waive record. Frozen, hashable, comparable for dedup."""

    persona: str
    reason: str
    source: str  # "trailer" | "annotation"


_TRAILER_RE = re.compile(
    r"^\s*Persona-Waive\s*:\s*(?P<persona>[A-Za-z][A-Za-z0-9_-]*)"
    r"\s*:\s*(?P<reason>[A-Za-z][A-Za-z0-9_-]*)\s*$",
    re.IGNORECASE,
)

_ANNOTATION_RE = re.compile(
    r"\[\s*persona-waive\s*:\s*(?P<persona>[A-Za-z][A-Za-z0-9_-]*)"
    r"\s+reason\s*=\s*(?P<reason>[A-Za-z][A-Za-z0-9_-]*)\s*\]",
    re.IGNORECASE,
)


def _normalize(token: Optional[str]) -> str:
    if not token:
        return ""
    return unicodedata.normalize("NFKC", token).strip().lower()


def _validate(persona: str, reason: str) -> bool:
    return persona in WAIVE_PERSONAS and reason in WAIVE_REASONS


def parse_commit_message(message: str) -> List[Waive]:
    """Return all valid waives found in a commit message.

    Accepts both trailer + annotation forms; de-duplicates exact matches.
    Invalid (free-text reason or unknown persona) entries silently dropped.
    """
    if not message:
        return []

    text = unicodedata.normalize("NFKC", message)
    found: List[Waive] = []
    seen: set = set()

    for line in text.splitlines():
        m = _TRAILER_RE.match(line)
        if m:
            persona = _normalize(m.group("persona"))
            reason = _normalize(m.group("reason"))
            if _validate(persona, reason):
                key = (persona, reason, "trailer")
                if key not in seen:
                    seen.add(key)
                    found.append(Waive(persona, reason, "trailer"))

    for m in _ANNOTATION_RE.finditer(text):
        persona = _normalize(m.group("persona"))
        reason = _normalize(m.group("reason"))
        if _validate(persona, reason):
            key = (persona, reason, "annotation")
            if key not in seen:
                seen.add(key)
                found.append(Waive(persona, reason, "annotation"))

    return found


def waives_by_persona(message: str) -> dict:
    """Group waives by persona for resolver lookup. Last reason wins."""
    out: dict = {}
    for w in parse_commit_message(message):
        out[w.persona] = w.reason
    return out


__all__ = [
    "WAIVE_REASONS",
    "WAIVE_PERSONAS",
    "Waive",
    "parse_commit_message",
    "waives_by_persona",
]
