#!/usr/bin/env python3
"""Registry of skills + archetypes as machine-readable manifests.

PLAN-004 Phase 2. Turns the skill + archetype inventory from implicit
(prose in team.md + loose frontmatter) into an explicit, enumerable
in-memory dict parsed from the existing artifacts. No side-car YAML
files required — the frontmatter in each SKILL.md + the archetype
tables in team.md are the source of truth.

## Why a registry?

- `check_agent_spawn.py` today matches archetype names via substring
  scan of team.md. A typo'd archetype passes silently. Registry lookup
  gives "unknown archetype" as a veto reason.
- Phase 4 Hook Adapter Layer needs a stable archetype list to validate
  against NormalizedEvent.archetype.
- Phase 8 squads need machine-readable composition (which skills,
  which archetypes).
- Dashboard + audit-query need archetype/skill existence checks to
  separate "typo" from "removed".

## Usage

    # CLI
    python3 .claude/scripts/registry.py --list
    python3 .claude/scripts/registry.py --list-skills
    python3 .claude/scripts/registry.py --list-archetypes
    python3 .claude/scripts/registry.py --get-skill security-and-auth
    python3 .claude/scripts/registry.py --validate       # exit 0 / 1

    # Library
    from registry import load_registry
    reg = load_registry(repo_root=Path("."))
    reg.skills              # {skill_id: SkillEntry}
    reg.archetypes          # {archetype_slug: ArchetypeEntry}

## Stdlib only

No PyYAML dependency. The minimal frontmatter parser here handles the
`name:`, `description:`, `owner:`, `secondary_owner:` fields we need.
Multi-line descriptions (YAML folded scalars) are supported.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Iterator, List, Optional


# -----------------------------------------------------------------------------
# Frontmatter parser (stdlib-only, minimal)
# -----------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> Dict[str, str]:
    """Parse a YAML-like frontmatter block. Returns flat string values.

    Supports:
    - `key: value` on a single line
    - `key: value\\n  continuation line` (folded scalar) — joined with space
    - Leading `---` and trailing `---` delimiters

    Limitations:
    - No list parsing (`-` items) — we don't need them here
    - No nested dicts
    - No quoted-string escaping beyond strip()

    If no frontmatter block is found, returns empty dict (fail-open).
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}

    block = m.group(1)
    result: Dict[str, str] = {}
    current_key: Optional[str] = None

    for line in block.splitlines():
        if not line.strip():
            current_key = None
            continue

        # Continuation line (indented)
        if line.startswith(" ") or line.startswith("\t"):
            if current_key:
                result[current_key] = (result[current_key] + " " + line.strip()).strip()
            continue

        # Key: value
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            result[key] = value
            # Keep current_key so indented continuations fold into this value
            current_key = key
        else:
            current_key = None

    return result


# -----------------------------------------------------------------------------
# Data classes
# -----------------------------------------------------------------------------


@dataclass
class SkillEntry:
    """Minimal skill manifest (derived from frontmatter)."""

    id: str
    tier: str  # "core" | "frontend" | "domain:<name>"
    name: str
    description: str
    owner: str
    secondary_owner: str
    path: str  # repo-relative path to SKILL.md

    def to_dict(self) -> Dict[str, str]:
        """Return a plain-dict view for JSON serialization."""
        return asdict(self)


@dataclass
class ArchetypeEntry:
    """Minimal archetype manifest (parsed from team.md tables)."""

    slug: str  # kebab-case slug (e.g. "vp-engineering")
    title: str  # human title (e.g. "VP Engineering")
    tier: str  # "backend" | "frontend" | "staff"
    primary_skill: str  # skill id (or empty if not declared)
    source_file: str  # which team file declared it

    def to_dict(self) -> Dict[str, str]:
        """Return a plain-dict view for JSON serialization."""
        return asdict(self)


@dataclass
class Registry:
    """Collected skills + archetypes."""

    skills: Dict[str, SkillEntry] = field(default_factory=dict)
    archetypes: Dict[str, ArchetypeEntry] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def summary(self) -> Dict[str, int]:
        """Return counts keyed by tier, plus totals and error count."""
        by_tier: Dict[str, int] = {}
        for s in self.skills.values():
            by_tier[s.tier] = by_tier.get(s.tier, 0) + 1
        return {
            "skills_total": len(self.skills),
            "archetypes_total": len(self.archetypes),
            "errors": len(self.errors),
            **{f"skills_{k.replace(':', '_')}": v for k, v in by_tier.items()},
        }


# -----------------------------------------------------------------------------
# Skill walker
# -----------------------------------------------------------------------------


def _resolve_tier(skill_md_path: Path, repo_root: Path) -> str:
    """Determine the tier from the path under .claude/skills/."""
    rel = skill_md_path.relative_to(repo_root)
    parts = rel.parts
    # parts[0]=.claude, parts[1]=skills, parts[2]=<tier-bucket>
    if len(parts) < 5 or parts[0] != ".claude" or parts[1] != "skills":
        return "unknown"
    bucket = parts[2]
    if bucket in {"core", "frontend"}:
        return bucket
    if bucket == "domains" and len(parts) >= 6:
        # .claude/skills/domains/<domain>/skills/<skill>/SKILL.md
        return f"domain:{parts[3]}"
    return "unknown"


def _iter_skill_md(repo_root: Path) -> Iterator[Path]:
    """Yield SKILL.md paths under .claude/skills/."""
    skills_root = repo_root / ".claude" / "skills"
    if not skills_root.is_dir():
        return
    # Core + frontend
    for tier_dir in ("core", "frontend"):
        root = skills_root / tier_dir
        if root.is_dir():
            for skill_dir in sorted(root.iterdir()):
                f = skill_dir / "SKILL.md"
                if f.is_file():
                    yield f
    # Domains
    domains_root = skills_root / "domains"
    if domains_root.is_dir():
        for domain_dir in sorted(domains_root.iterdir()):
            sk_root = domain_dir / "skills"
            if sk_root.is_dir():
                for skill_dir in sorted(sk_root.iterdir()):
                    f = skill_dir / "SKILL.md"
                    if f.is_file():
                        yield f


def load_skills(repo_root: Path) -> Dict[str, SkillEntry]:
    """Walk .claude/skills/ and parse each SKILL.md frontmatter."""
    skills: Dict[str, SkillEntry] = {}
    for skill_md in _iter_skill_md(repo_root):
        try:
            text = skill_md.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = _parse_frontmatter(text)
        # Canonical skill id = directory name (stable slug). Frontend skills
        # sometimes have display names in `name:` ("Code Quality & TypeScript");
        # the directory (`code-quality-and-typescript`) is the stable identifier.
        skill_id = skill_md.parent.name
        name = fm.get("name") or skill_id
        tier = _resolve_tier(skill_md, repo_root)
        entry = SkillEntry(
            id=skill_id,
            tier=tier,
            name=name,
            description=fm.get("description", ""),
            owner=fm.get("owner", ""),
            secondary_owner=fm.get("secondary_owner", ""),
            path=str(skill_md.relative_to(repo_root)),
        )
        # Collision — same skill name across tiers: prefix with tier
        if skill_id in skills:
            alt_id = f"{tier}:{skill_id}"
            entry.id = alt_id
            skills[alt_id] = entry
        else:
            skills[skill_id] = entry
    return skills


# -----------------------------------------------------------------------------
# Archetype parser (team.md + frontend-team.md + domain personas)
# -----------------------------------------------------------------------------


# Rows like `| **VP Engineering** | `architecture-decisions` | `incremental-refactoring` |`
# The PRIMARY skill is the FIRST backticked token after the bold title,
# regardless of how many `|` columns separate it from the title. The old
# pattern `\|(.+?)\|\s*`(...)`` greedily skipped to the LAST `|`-then-backtick
# on the row and so captured the SECONDARY skill (W6 F-11.14). We now consume
# any non-backtick run after the title's column boundary and stop at the FIRST
# backtick — capture group 2 is the primary skill id.
_ARCHETYPE_ROW_RE = re.compile(
    r"^\|\s*\*\*([^|*]+?)\*\*[^|`\n]*\|[^`\n]*?`([a-z0-9\-]+)`",
    re.MULTILINE,
)


def _slugify(title: str) -> str:
    s = title.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def load_archetypes(repo_root: Path) -> Dict[str, ArchetypeEntry]:
    """Parse archetype tables from team files.

    Recognizes rows of shape:
        | **Archetype Title** | ... | `skill-id` | ...

    Robust to column count variations; only the FIRST backticked token
    on a row is taken as the primary skill id.
    """
    archetypes: Dict[str, ArchetypeEntry] = {}
    claude_dir = repo_root / ".claude"
    files_to_scan: List[Path] = []
    for candidate in (claude_dir / "team.md", claude_dir / "frontend-team.md"):
        if candidate.is_file():
            files_to_scan.append(candidate)
    domains = claude_dir / "skills" / "domains"
    if domains.is_dir():
        for dom in sorted(domains.iterdir()):
            for fname in ("team-personas.md", "frontend-team-personas.md"):
                f = dom / fname
                if f.is_file():
                    files_to_scan.append(f)

    for path in files_to_scan:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = str(path.relative_to(repo_root))
        for m in _ARCHETYPE_ROW_RE.finditer(text):
            title = m.group(1).strip()
            skill = m.group(2).strip()  # group 2 = FIRST backtick = primary skill
            if not title or title.lower() in {"role", "archetype"}:
                continue
            slug = _slugify(title)
            # Tier heuristic from file name
            if "frontend" in rel:
                tier = "frontend"
            elif "domains/" in rel:
                tier = "domain"
            else:
                tier = "backend"
            # First declaration wins; later files do not overwrite canonical
            if slug not in archetypes:
                archetypes[slug] = ArchetypeEntry(
                    slug=slug,
                    title=title,
                    tier=tier,
                    primary_skill=skill,
                    source_file=rel,
                )
    return archetypes


# -----------------------------------------------------------------------------
# Loader + validator
# -----------------------------------------------------------------------------


def load_registry(repo_root: Path) -> Registry:
    """Build the full registry."""
    reg = Registry()
    reg.skills = load_skills(repo_root)
    reg.archetypes = load_archetypes(repo_root)

    # Cross-validation: every archetype's primary_skill should exist
    skill_ids = set(reg.skills.keys())
    skill_names = {s.name for s in reg.skills.values()}
    for a in reg.archetypes.values():
        if a.primary_skill and a.primary_skill not in skill_ids and a.primary_skill not in skill_names:
            reg.errors.append(
                f"archetype '{a.slug}' references unknown skill '{a.primary_skill}' "
                f"(declared in {a.source_file})"
            )
    return reg


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def _cli(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="ceo-orchestration skill + archetype registry",
    )
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--list", action="store_true", help="print all skills + archetypes (summary)")
    g.add_argument("--list-skills", action="store_true")
    g.add_argument("--list-archetypes", action="store_true")
    g.add_argument("--get-skill", metavar="ID", help="print one skill as JSON")
    g.add_argument("--get-archetype", metavar="SLUG", help="print one archetype as JSON")
    g.add_argument("--validate", action="store_true", help="exit 1 if any registry error")
    g.add_argument("--summary", action="store_true", help="print counts only")
    parser.add_argument("--repo-root", default=".", help="project root (default: cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    repo = Path(args.repo_root).resolve()
    reg = load_registry(repo)

    if args.validate:
        if reg.errors:
            for e in reg.errors:
                print(f"ERROR: {e}", file=sys.stderr)
            return 1
        print(f"OK: {len(reg.skills)} skills, {len(reg.archetypes)} archetypes, 0 errors")
        return 0

    if args.summary:
        print(json.dumps(reg.summary(), indent=2))
        return 0

    if args.get_skill:
        s = reg.skills.get(args.get_skill)
        if not s:
            print(f"unknown skill: {args.get_skill}", file=sys.stderr)
            return 1
        print(json.dumps(s.to_dict(), indent=2))
        return 0

    if args.get_archetype:
        a = reg.archetypes.get(args.get_archetype)
        if not a:
            print(f"unknown archetype: {args.get_archetype}", file=sys.stderr)
            return 1
        print(json.dumps(a.to_dict(), indent=2))
        return 0

    if args.list_skills:
        if args.json:
            print(json.dumps([s.to_dict() for s in reg.skills.values()], indent=2))
        else:
            for s in sorted(reg.skills.values(), key=lambda x: (x.tier, x.id)):
                print(f"  [{s.tier:20s}] {s.id}")
        return 0

    if args.list_archetypes:
        if args.json:
            print(json.dumps([a.to_dict() for a in reg.archetypes.values()], indent=2))
        else:
            for a in sorted(reg.archetypes.values(), key=lambda x: (x.tier, x.slug)):
                print(f"  [{a.tier:10s}] {a.slug:40s} → {a.primary_skill}")
        return 0

    # Default --list: summary + both lists
    summary = reg.summary()
    print(f"# ceo-orchestration registry ({repo})")
    print(f"# Skills: {summary['skills_total']} | Archetypes: {summary['archetypes_total']} | Errors: {summary['errors']}")
    print()
    print("## Skills")
    for s in sorted(reg.skills.values(), key=lambda x: (x.tier, x.id)):
        print(f"  [{s.tier:20s}] {s.id}")
    print()
    print("## Archetypes")
    for a in sorted(reg.archetypes.values(), key=lambda x: (x.tier, x.slug)):
        print(f"  [{a.tier:10s}] {a.slug:40s} → {a.primary_skill}")
    if reg.errors:
        print()
        print("## Errors")
        for e in reg.errors:
            print(f"  ! {e}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
