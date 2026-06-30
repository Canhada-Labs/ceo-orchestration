#!/usr/bin/env python3
"""check-skill-activation-mode.py — PLAN-110 Wave H advisory CI script.

Scans .claude/skills/**/SKILL.md and emits warning if any skill is missing
`activation_mode:` in frontmatter. Fail-OPEN: exit 0 even on warnings.
Stdlib-only.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILLS_ROOT = REPO / ".claude/skills"

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_ACT_RE = re.compile(r"^activation_mode:\s*(\S+)", re.MULTILINE)


def main() -> int:
    missing = []
    for skill in SKILLS_ROOT.glob("**/SKILL.md"):
        text = skill.read_text(encoding="utf-8", errors="replace")
        m = _FM_RE.search(text)
        if not m:
            continue
        fm = m.group(1)
        if not _ACT_RE.search(fm):
            missing.append(skill.relative_to(REPO))
    if missing:
        print("[advisory] skills missing activation_mode:")
        for p in missing:
            print(f"  - {p}")
        print(f"[advisory] {len(missing)} skill(s) need activation_mode in frontmatter")
        print("[advisory] non-blocking; exit 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
