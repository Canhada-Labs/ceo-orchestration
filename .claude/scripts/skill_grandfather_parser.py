#!/usr/bin/env python3
"""Stdlib-only parser for .claude/skill-governance-grandfather.yaml.

The YAML schema is intentionally minimal (flat list of {skill, reason,
justification} dicts) so we can parse it without a third-party YAML
library. This preserves the stdlib-only invariant (CLAUDE.md §Critical
Rules) and keeps the parser trivially reviewable.

Public API:
  parse_grandfather_file(path) -> List[GrandfatherEntry]
  is_grandfathered(skill_name, path=DEFAULT_PATH) -> bool
  get_reason(skill_name, path=DEFAULT_PATH) -> Optional[str]
  validate_registry(entries) -> List[str] of error messages

The 3 allowed reason categories are enum-validated on parse; unknown
categories return a validation error rather than a silent pass.

Consumers:
  - .claude/scripts/validate-governance.sh (via grep-then-parse)
  - .claude/scripts/tests/test_skill_grandfather_parser.py
  - Future: PLAN-052 audit cycle may consume this for findings
    tagging (grandfathered skill vs orphan skill).

PLAN-051 Phase 1 A1 (Opção 2). Commit 2026-04-22 Session 57.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Keep in sync with .claude/skill-governance-grandfather.yaml header.
VALID_REASONS = frozenset({
    "meta-skill-adjacent",
    "slash-command-only",
    "community-import",
})

# Hard cap per file header (lifecycle rule).
MAX_GRANDFATHERED_ENTRIES = 10

DEFAULT_PATH = Path(".claude/skill-governance-grandfather.yaml")


class GrandfatherEntry:
    """One entry in the grandfather registry."""

    __slots__ = ("skill", "reason", "justification")

    def __init__(self, skill: str, reason: str, justification: str) -> None:
        self.skill = skill
        self.reason = reason
        self.justification = justification

    def __repr__(self) -> str:  # pragma: no cover — trivial debug
        return f"GrandfatherEntry(skill={self.skill!r}, reason={self.reason!r})"

    def to_dict(self) -> Dict[str, str]:
        return {
            "skill": self.skill,
            "reason": self.reason,
            "justification": self.justification,
        }


_SKILL_RE = re.compile(r"^\s*-\s*skill:\s*(\S+)\s*$")
_REASON_RE = re.compile(r"^\s*reason:\s*(\S+)\s*$")
# Justification may be quoted or bare. We accept both.
_JUSTIFICATION_RE = re.compile(r'^\s*justification:\s*"?(.*?)"?\s*$')


def parse_grandfather_file(
    path: Optional[Path] = None,
) -> List[GrandfatherEntry]:
    """Parse the grandfather YAML. Returns list of GrandfatherEntry.

    Raises FileNotFoundError if the file is missing.
    Raises ValueError on malformed schema (sequence invariant violated).

    Note: no third-party YAML parser. We rely on the known shape:
      grandfathered:
        - skill: <slug>
          reason: <category>
          justification: "<text>"

    The parser skips comments (# ...), blank lines, and the top-level
    `grandfathered:` mapping key. Anything else between entries is an
    error.
    """
    if path is None:
        path = DEFAULT_PATH
    path = Path(path)

    text = path.read_text(encoding="utf-8")

    entries: List[GrandfatherEntry] = []
    current_skill: Optional[str] = None
    current_reason: Optional[str] = None
    current_justification: Optional[str] = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        # Strip inline `# comment` so trailing comments don't break matches.
        if "#" in line:
            # Only strip if the `#` is preceded by whitespace (true comment),
            # not when embedded in a string value.
            hash_idx = line.find("#")
            if hash_idx == 0 or line[hash_idx - 1] in (" ", "\t"):
                line = line[:hash_idx].rstrip()
        # Skip comments + blank lines + the root key.
        if not line or line.lstrip().startswith("#"):
            continue
        if line.strip() == "grandfathered:":
            continue

        # Skip top-level scalar metadata (PLAN-080 Phase 1b deprecation
        # stub adds `deprecated: true`, `superseded_by: ...`, etc.). Any
        # column-0 `key: value` line that isn't the `grandfathered:`
        # structure marker is metadata and tolerated.
        if line[:1] not in (" ", "\t", "-") and ":" in line and not line.endswith(":"):
            continue

        m_skill = _SKILL_RE.match(line)
        if m_skill:
            # Flush previous entry if complete.
            if current_skill is not None:
                if current_reason is None or current_justification is None:
                    raise ValueError(
                        f"incomplete entry for skill '{current_skill}' — "
                        f"missing reason or justification"
                    )
                entries.append(
                    GrandfatherEntry(
                        current_skill, current_reason, current_justification
                    )
                )
            current_skill = m_skill.group(1)
            current_reason = None
            current_justification = None
            continue

        m_reason = _REASON_RE.match(line)
        if m_reason:
            if current_skill is None:
                raise ValueError(
                    f"'reason' encountered before any 'skill' key: {line!r}"
                )
            current_reason = m_reason.group(1)
            continue

        m_just = _JUSTIFICATION_RE.match(line)
        if m_just:
            if current_skill is None:
                raise ValueError(
                    f"'justification' encountered before any 'skill' key: "
                    f"{line!r}"
                )
            current_justification = m_just.group(1)
            continue

        # Anything else is a schema violation.
        raise ValueError(f"unrecognized line in grandfather file: {line!r}")

    # Flush final entry.
    if current_skill is not None:
        if current_reason is None or current_justification is None:
            raise ValueError(
                f"incomplete entry for skill '{current_skill}' — "
                f"missing reason or justification"
            )
        entries.append(
            GrandfatherEntry(
                current_skill, current_reason, current_justification
            )
        )

    return entries


def validate_registry(entries: List[GrandfatherEntry]) -> List[str]:
    """Validate a parsed registry. Returns list of error messages
    (empty list = valid).
    """
    errors: List[str] = []

    # Cap check.
    if len(entries) > MAX_GRANDFATHERED_ENTRIES:
        errors.append(
            f"registry has {len(entries)} entries; cap is "
            f"{MAX_GRANDFATHERED_ENTRIES} (file header rule). Exceeding "
            f"requires ADR + debate."
        )

    # Uniqueness check on skill names.
    seen: Dict[str, int] = {}
    for idx, entry in enumerate(entries):
        if entry.skill in seen:
            errors.append(
                f"duplicate skill '{entry.skill}' at entries "
                f"{seen[entry.skill]} and {idx}"
            )
        else:
            seen[entry.skill] = idx

    # Reason enum check.
    for entry in entries:
        if entry.reason not in VALID_REASONS:
            errors.append(
                f"skill '{entry.skill}' has unknown reason "
                f"'{entry.reason}' (valid: "
                f"{sorted(VALID_REASONS)})"
            )

    # Justification non-empty check.
    for entry in entries:
        if not entry.justification.strip():
            errors.append(
                f"skill '{entry.skill}' has empty justification"
            )

    return errors


def is_grandfathered(
    skill_name: str, path: Optional[Path] = None
) -> bool:
    """Return True if skill_name is in the grandfather registry."""
    try:
        entries = parse_grandfather_file(path)
    except FileNotFoundError:
        return False
    return any(e.skill == skill_name for e in entries)


def get_reason(
    skill_name: str, path: Optional[Path] = None
) -> Optional[str]:
    """Return the grandfather reason for a skill, or None if not found."""
    try:
        entries = parse_grandfather_file(path)
    except FileNotFoundError:
        return None
    for e in entries:
        if e.skill == skill_name:
            return e.reason
    return None


def list_grandfathered_skills(
    path: Optional[Path] = None,
) -> List[str]:
    """Return list of grandfathered skill names for shell consumers."""
    try:
        entries = parse_grandfather_file(path)
    except FileNotFoundError:
        return []
    return [e.skill for e in entries]


def _main() -> int:
    """CLI entry point. Emits `skill:reason` pairs one-per-line on stdout
    for shell consumers. Exit 0 if registry is valid, exit 1 on schema
    errors, exit 2 on file missing.
    """
    import sys

    path = DEFAULT_PATH
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])

    try:
        entries = parse_grandfather_file(path)
    except FileNotFoundError:
        print(f"grandfather file not found: {path}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"parse error: {e}", file=sys.stderr)
        return 1

    errors = validate_registry(entries)
    if errors:
        for err in errors:
            print(f"validation error: {err}", file=sys.stderr)
        return 1

    for entry in entries:
        print(f"{entry.skill}:{entry.reason}")
    return 0


if __name__ == "__main__":
    import sys as _sys

    _sys.exit(_main())
