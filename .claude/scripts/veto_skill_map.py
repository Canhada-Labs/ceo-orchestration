#!/usr/bin/env python3
"""PLAN-183 W3 P0 — DERIVED map of VETO-bearing skills.

No skill is enumerated in this file. The set is derived, on every call,
from the organograms — the governance authority for who holds a VETO:

  .claude/team.md                                     (backend archetypes)
  .claude/frontend-team.md                            (frontend archetypes)
  .claude/skills/domains/*/team-personas.md           (installed domains)
  .claude/skills/domains/*/frontend-team-personas.md  (installed domains)

Why NOT a ``veto: true`` field in each SKILL.md frontmatter: that surface
is canonical (``check_canonical_edit.py`` guards
``.claude/skills/**/SKILL.md``) and gated behind SP-NNN + a 7-day soak,
so the derivation and its lint could not land in one commit. This module
is NOT canonical, so both halves ship together.

Two relations are joined, because the VETO status and the persona->skill
binding are frequently NOT on the same line:

  R1-direct  a skill slug in a backticked cell ON the VETO table row
             (``.claude/team.md:93``, ``:277``,
              ``.claude/frontend-team.md:164``)
  R1-join    a persona named on the VETO line, resolved through R2
             (``fintech/frontend-team-personas.md:372`` says
              "**Mei tem VETO** em qualquer codigo que exiba precos" with
              no slug at all; the Mei -> ``financial-display`` binding
              lives at ``:96`` and ``:359``, lines WITHOUT the word VETO)

Direct slug extraction is restricted to markdown TABLE ROWS. Prose lines
contribute only through the persona join. That asymmetry is deliberate
and measured: ``.claude/team.md:832`` is a prose line that contains both
the word VETO and the backticked tokens ``tsc`` / ``mypy`` / ``go vet``,
which are toolchain names, not skills. A parser that read slugs out of
prose over-derives; one that ignores prose entirely under-derives (it
would lose Mei). Both directions are guarded in
``.claude/scripts/tests/test_veto_skill_map.py``.

Conservative by construction: over-inclusion PROTECTS a skill from
demotion, under-inclusion silently demotes a skill a VETO holder depends
on. When the two error directions are not symmetric, prefer the safe one.

Stdlib-only. Python >= 3.9.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

_VETO = re.compile(r"\bVETO\b")

# Lines that mention VETO in order to DENY it. One match suppresses the
# whole line. Measured census: exactly 2 lines in the shipped organograms
# (``.claude/team.md:210`` and ``:552``, the LLM FinOps Architect —
# "Advisory, NO VETO per ADR-052 amendment").
_NEGATIONS = (
    re.compile(r"\bNO[\s-]+VETO\b", re.IGNORECASE),
    re.compile(r"\bsem\s+VETO\b", re.IGNORECASE),
    re.compile(r"\bwithout\s+VETO\b", re.IGNORECASE),
)

_BACKTICKED = re.compile(r"`([^`\n]+)`")
_BOLD = re.compile(r"\*\*([^*\n]+)\*\*")
_SLUG_OK = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_LIST_LEAD = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\*{0,2}([A-Z][A-Za-z]+)\b")
_NAME_WORD = re.compile(r"^[A-Z][A-Za-z]+$")

ORGANOGRAM_BASENAMES = ("team-personas.md", "frontend-team-personas.md")


def organogram_paths(repo_root: Path) -> List[Path]:
    """Every organogram present in ``repo_root``, in a stable order.

    An adopter install carries only the domains it chose, so the domain
    globs are expected to return a variable set — never a fixed count.
    """
    out: List[Path] = []
    for rel in (".claude/team.md", ".claude/frontend-team.md"):
        candidate = repo_root / rel
        if candidate.is_file():
            out.append(candidate)
    domains = repo_root / ".claude" / "skills" / "domains"
    if domains.is_dir():
        for basename in ORGANOGRAM_BASENAMES:
            out.extend(sorted(domains.glob("*/" + basename)))
    return out


def _is_table_row(line: str) -> bool:
    return line.lstrip().startswith("|")


def is_veto_line(line: str) -> bool:
    """True when the line ASSERTS a VETO (negations suppress it)."""
    if not _VETO.search(line):
        return False
    return not any(pattern.search(line) for pattern in _NEGATIONS)


def slugs_in_row(line: str) -> Set[str]:
    """Skill slugs from backticked cells of a markdown table row.

    Rejects paths and filenames (a ``.`` anywhere — ``.claude/team.md:30``
    backticks a full path on a line that also says VETO), multi-word
    values (``go vet``), and anything that is not a lowercase slug. For a
    value carrying a tier prefix (``core/pii-data-flow``) the last segment
    is kept, which is the spelling the skill inventory indexes by.
    """
    found: Set[str] = set()
    if not _is_table_row(line):
        return found
    for raw in _BACKTICKED.findall(line):
        value = raw.strip()
        if not value or "." in value or " " in value:
            continue
        value = value.rsplit("/", 1)[-1]
        if _SLUG_OK.match(value):
            found.add(value)
    return found


def personas_in(line: str) -> Set[str]:
    """Persona names cited on a line, as join keys.

    A key is a SINGLE capitalized word — an individual's name. Role words
    are deliberately not keys: joining on the first word of a multi-word
    title made ``**Staff Code Reviewer**`` (``.claude/team.md:93``) and
    ``**Principal Incident Commander**`` (``:207``) collide with every
    other Staff/Principal row and pulled 20+ unrelated skills into the
    set — measured, before this narrowing. Same for a bare ``CEO`` cell,
    which appears in every reporting row.

    Both spellings of the same persona are reached: ``**Mei**`` on the
    binding row (``fintech/frontend-team-personas.md:359``) and
    ``**Mei tem VETO**`` — the bold span swallowing the predicate — on the
    governance line (``:372``), via the list-lead capture.
    """
    keys: Set[str] = set()
    for span in _BOLD.findall(line):
        span = span.strip()
        if _NAME_WORD.match(span):
            keys.add(span)
    lead = _LIST_LEAD.match(line)
    if lead:
        keys.add(lead.group(1))
    return keys


def _persona_skill_relation(lines: List[str]) -> Dict[str, Set[str]]:
    """R2: persona name -> skills, from the table rows of ONE file.

    Scoped per file on purpose: persona first names are short and collide
    across domains, and each organogram is self-contained.
    """
    relation: Dict[str, Set[str]] = {}
    for line in lines:
        if not _is_table_row(line):
            continue
        slugs = slugs_in_row(line)
        if not slugs:
            continue
        for key in personas_in(line):
            relation.setdefault(key, set()).update(slugs)
    return relation


def derive_veto_skills(
    repo_root: Path,
) -> Tuple[Set[str], Dict[str, List[str]]]:
    """Return ``(veto_slugs, anchors)``.

    ``anchors[slug]`` is the list of ``path:line`` sites that put the slug
    in the set — the audit trail that makes the derivation reviewable and
    lets the lint assert that no entry is memory-resident.
    """
    found: Set[str] = set()
    anchors: Dict[str, List[str]] = {}
    for path in organogram_paths(repo_root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        relation = _persona_skill_relation(lines)
        try:
            label = str(path.relative_to(repo_root))
        except ValueError:
            label = str(path)
        for number, line in enumerate(lines, start=1):
            if not is_veto_line(line):
                continue
            hits = set(slugs_in_row(line))
            if not hits:
                # The persona join is the FALLBACK, not an addition. Where
                # the VETO row already names its own skills, joining every
                # persona cited on it drags in the implementers' unrelated
                # skills: ``fintech/team-personas.md:198`` reads "**Luna** +
                # **Viktor** VETO" — the VETO is Viktor's, and joining Luna
                # pulled ai-llm-orchestration, public-api-design and
                # incremental-refactoring from ``:142``/``:200`` (measured).
                # Restricting the join to slug-less lines keeps exactly the
                # case that needs it: prose governance rules such as
                # ``fintech/frontend-team-personas.md:372``.
                for persona in personas_in(line):
                    hits |= relation.get(persona, set())
            for slug in hits:
                found.add(slug)
                anchors.setdefault(slug, []).append(
                    "{0}:{1}".format(label, number)
                )
    return found, anchors


def bind_to_inventory(
    veto: Set[str], inventory: List[Dict[str, Any]]
) -> Tuple[Set[str], Set[str]]:
    """Split a derived set into ``(bound, orphans)``.

    ``bound`` = slugs with a match in the skill inventory's ``name`` or
    ``dir_name``; ``orphans`` = the rest. An orphan is either an
    organogram naming a skill that is not installed (legitimate for an
    adopter that took a subset of domains) or parser noise. Only the
    consumer can tell the two apart, so this function classifies and does
    not judge.
    """
    keys: Set[str] = set()
    for skill in inventory:
        keys.add(str(skill["name"]))
        keys.add(str(skill["dir_name"]))
    bound = {slug for slug in veto if slug in keys}
    return bound, set(veto) - bound
