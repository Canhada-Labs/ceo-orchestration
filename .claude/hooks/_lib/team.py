"""

Port of the `NAMES_REGEX` extraction block in `check-agent-spawn.sh`:

    NAMES=$(grep -hoE '\*\*[A-ZÀ-Ý][a-zà-ÿ]{2,}\*\*' "${TEAM_FILES[@]}" \
            | sed 's/\*\*//g' | sort -u | paste -sd'|' -)

Convention: persona names are tagged with markdown bold emphasis
(`**Name**`) wherever they appear in:

- `.claude/team.md`
- `.claude/frontend-team.md`
- `.claude/skills/domains/*/team-personas.md`
- `.claude/skills/domains/*/frontend-team-personas.md`

This module walks those files and returns a compiled regex that matches
any of the discovered names as a whole word (case-insensitive). Callers
use it to decide whether an Agent description names a team member.

## Safety properties

- Tolerates missing team files (returns `None`, meaning "no detection").
- Tolerates unreadable files (logs to stderr, skips).
- Case-insensitive by default.
- Names are escaped via `re.escape()` before joining — no regex injection.
- Supports accented characters (Latin-1 supplement).

## Subprocess model (PLAN-025 F-perf-005)

Every hook invocation runs in a fresh subprocess — there is NO
in-process cache across invocations of functions in this module.
``load_names()`` re-reads + re-parses team.md on every spawn-gate
evaluation. For typical frameworks with <100 team members this is
~1-3ms; if a future adopter approaches 1000+ team members, either
memoize on disk via audit_emit._memoize_path pattern + SHA of the
source files, or warm the cache at session start, or inline the
names into settings.json with SHA-pin.

This is documented so future adopters do not assume load_names()
has process-level caching semantics.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Pattern


# Bold-emphasis pattern: **Name** where Name starts with an uppercase letter
# (including accented uppercase) followed by ≥ 2 lowercase letters.
# Avoids matching **NEVER** or **API** (all-caps headings).
_NAME_EXTRACT = re.compile(
    r"\*\*([A-ZÀ-Ý][a-zà-ÿ]{2,})\*\*",
)


def default_team_files(project_dir) -> List[Path]:
    """Return the conventional list of team files for a project dir.

    Includes non-existent files — callers filter. This keeps the lookup
    deterministic and testable.
    """
    root = Path(project_dir)
    files: List[Path] = [
        root / ".claude" / "team.md",
        root / ".claude" / "frontend-team.md",
    ]
    # Domain personas — glob pattern
    domains_dir = root / ".claude" / "skills" / "domains"
    if domains_dir.is_dir():
        for domain in sorted(domains_dir.iterdir()):
            if not domain.is_dir():
                continue
            files.append(domain / "team-personas.md")
            files.append(domain / "frontend-team-personas.md")
    return files


def extract_names(files: Iterable[Path]) -> List[str]:
    """Extract bolded names from the given files.

    Returns a sorted, deduplicated list. Missing or unreadable files are
    silently skipped (with a stderr breadcrumb for debugging).
    """
    found: set = set()
    for f in files:
        try:
            if not f.is_file():
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            # Best-effort — log to stderr but don't fail
            print(f"[_lib.team] WARN: cannot read {f}: {e}", file=sys.stderr)
            continue
        for match in _NAME_EXTRACT.finditer(text):
            found.add(match.group(1))
    return sorted(found)


def build_names_regex(names: Iterable[str]) -> Optional[Pattern[str]]:
    """Compile a case-insensitive whole-word regex matching any of the names.

    Returns None if the name list is empty — callers interpret None as
    "no detection possible" and fall back to persona-header detection.

    Names are escaped via `re.escape()` before joining, so any regex
    metacharacter in a persona name (hypothetical — names are alpha)
    is treated literally.
    """
    unique = sorted({n for n in names if n})
    if not unique:
        return None
    escaped = [re.escape(n) for n in unique]
    pattern = r"\b(?:" + "|".join(escaped) + r")\b"
    return re.compile(pattern, flags=re.IGNORECASE)


def load_names(project_dir) -> Optional[Pattern[str]]:
    """Convenience: the full extraction pipeline from a project dir.

    Returns a compiled regex or None. Designed to be called once per hook
    invocation.
    """
    files = default_team_files(project_dir)
    names = extract_names(files)
    return build_names_regex(names)
