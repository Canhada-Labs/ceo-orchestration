"""Parse plan file frontmatter with a regex-based extractor.

Sprint 3 Item D. Per debate consensus R-VP1: stdlib only, no yaml
dependency. Frontmatter is simple enough (key: value lines, list
values, dates) that regex extraction is more robust than yaml for
our constrained schema.

## What we parse

```yaml
---
id: PLAN-001
title: Short title
status: draft
created: 2026-04-10
owner: CEO
depends_on: []
related_commits: [a1b2c3d, e4f5a6b]
completed_at: 2026-04-12
---
```

## What we don't support

- Nested YAML structures (we don't need them)
- Multi-line values (block scalars)
- YAML anchors / aliases
- Type coercion (all values are strings, lists are lists of strings)

If a plan ever needs those, upgrade to PyYAML and revisit this parser.

## Output

`parse_frontmatter(text) -> Dict[str, Union[str, List[str]]]`

Keys map to strings by default. Keys whose value starts with `[` map
to lists of strings. Keys with empty values map to `""`.

Fail-safe: returns `{}` on any malformed input.
"""

from __future__ import annotations

import re
from typing import Dict, List, Union

# Match the frontmatter block: starts with --- on its own line, ends with
# --- on its own line. Capturing group is the content between.
_FRONTMATTER_RE = re.compile(
    r"^---\s*\n(.*?)\n---\s*(?:\n|$)",
    re.DOTALL,
)

# Match a single key: value line. Indentation is tolerated but not stripped
# from list elements.
_KEY_VALUE_RE = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$",
)

# Match a bullet list continuation: "  - item"
_LIST_ITEM_RE = re.compile(r"^\s+-\s*(.+?)\s*$")

FrontmatterValue = Union[str, List[str]]


def extract_frontmatter_text(content: str) -> str:
    """Return the raw YAML-ish frontmatter text (no --- delimiters).

    Empty string if no frontmatter found.
    """
    if not content:
        return ""
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return ""
    return m.group(1)


def parse_frontmatter(content: str) -> Dict[str, FrontmatterValue]:
    """Parse plan frontmatter into a dict.

    Returns {} on any malformed input. Keys are strings; values are
    strings OR lists of strings (for list-typed fields).

    Supports two list syntaxes:
    1. Inline: `related_commits: [a1b2c3d, e4f5a6b]`
    2. Multi-line:
           related_commits:
             - a1b2c3d
             - e4f5a6b
    """
    text = extract_frontmatter_text(content)
    if not text:
        return {}

    result: Dict[str, FrontmatterValue] = {}
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        m = _KEY_VALUE_RE.match(line)
        if not m:
            i += 1
            continue

        key = m.group(1)
        raw_value = m.group(2)

        if raw_value == "":
            # Possibly a multi-line list
            items: List[str] = []
            j = i + 1
            while j < len(lines):
                sub = _LIST_ITEM_RE.match(lines[j])
                if not sub:
                    break
                items.append(sub.group(1).strip())
                j += 1
            if items:
                result[key] = items
                i = j
                continue
            result[key] = ""
            i += 1
            continue

        if raw_value.startswith("[") and raw_value.endswith("]"):
            inner = raw_value[1:-1].strip()
            if not inner:
                result[key] = []
            else:
                # Split on comma; strip whitespace
                items = [
                    item.strip().strip('"').strip("'")
                    for item in inner.split(",")
                ]
                result[key] = [item for item in items if item]
            i += 1
            continue

        # Strip surrounding quotes if present
        value = raw_value
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        result[key] = value
        i += 1

    return result


def has_abandonment_reason(content: str) -> bool:
    """True if the body contains a `## Abandonment reason` section header."""
    if not content:
        return False
    return bool(
        re.search(
            r"^##\s+Abandonment\s+reason\s*$",
            content,
            re.MULTILINE | re.IGNORECASE,
        )
    )
