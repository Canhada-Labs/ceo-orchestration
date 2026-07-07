#!/usr/bin/env python3
"""gen-command-skill-hook-map.py — derived COMMAND -> SKILL -> HOOK map.

PLAN-153 Wave C item 6. Generates ``docs/COMMAND-SKILL-HOOK-MAP.md`` from
three committed on-disk sources (nothing else — no audit log, no network,
no env reads):

    1. ``.claude/commands/*.md``          — slash-command definitions
    2. ``.claude/skills/**/SKILL.md``     — skill catalog (core/frontend/domains)
    3. ``.claude/settings.json``          — governance hook registrations

Relationships emitted (each one a *textual declaration derivable on disk*,
never a runtime trace — the doc states this honestly):

    command -> skill    slug of a cataloged skill appears in the command body
                        (backticked token or ``.claude/skills/...`` path segment)
    command -> script   ``.claude/scripts/*.py|sh`` path appears in the body
    event   -> hook     registration rows parsed from settings.json ``hooks``
    surface -> hook     a registered hook's source under ``.claude/hooks/``
                        contains ``.claude/skills``/``SKILL.md`` (skill surface)
                        or ``.claude/commands`` (command surface)

Determinism contract (build-plugin.py B6 / skill-inventory pattern):
sorted output, registration order preserved only where it is semantic
(hook chain order within an event), no timestamps, no environment reads.
Injection surface: table cells carry only identifier-class tokens (slugs,
filenames, matchers) — free prose from scanned files (descriptions, hook
``_comment`` fields) is deliberately NOT embedded.

Usage:
  python3 .claude/scripts/gen-command-skill-hook-map.py            # emit to stdout
  python3 .claude/scripts/gen-command-skill-hook-map.py --write    # (re)write docs/COMMAND-SKILL-HOOK-MAP.md
  python3 .claude/scripts/gen-command-skill-hook-map.py --check    # regen to temp + diff committed; exit 1 on drift

Stdlib-only, Python >= 3.9.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

DOC_REL = "docs/COMMAND-SKILL-HOOK-MAP.md"
SELF_REL = ".claude/scripts/gen-command-skill-hook-map.py"

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_BACKTICK_TOKEN_RE = re.compile(r"`([A-Za-z0-9][A-Za-z0-9_-]*)`")
_SKILL_PATH_RE = re.compile(r"\.claude/skills/[A-Za-z0-9_./-]+")
_SCRIPT_PATH_RE = re.compile(r"\.claude/scripts/[A-Za-z0-9_./-]+\.(?:py|sh)")
_HOOK_FILE_RE = re.compile(r"([A-Za-z0-9_./$\{\}-]+\.(?:py|sh))")


def default_repo() -> Path:
    """Repo root = two levels up from .claude/scripts/<this file>."""
    return Path(__file__).resolve().parents[2]


def _split_frontmatter(text: str) -> Tuple[str, str]:
    """Return (frontmatter, body); frontmatter is '' when absent."""
    m = _FM_RE.match(text)
    if not m:
        return "", text
    return m.group(1), text[m.end():]


# --------------------------------------------------------------------------
# Source 2 — skill catalog
# --------------------------------------------------------------------------

def iter_skill_dirs(repo: Path) -> List[Tuple[str, Path]]:
    """(tier, dir) for every SKILL.md-bearing skill dir — mirrors the
    iteration contract of scripts/build-plugin.py::iter_skills."""
    out: List[Tuple[str, Path]] = []
    for d in sorted((repo / ".claude/skills/core").glob("*/")):
        if (d / "SKILL.md").is_file():
            out.append(("core", d))
    for d in sorted((repo / ".claude/skills/frontend").glob("*/")):
        if (d / "SKILL.md").is_file():
            out.append(("frontend", d))
    for dom in sorted((repo / ".claude/skills/domains").glob("*/")):
        sk = dom / "skills"
        if not sk.is_dir():
            continue
        for d in sorted(sk.glob("*/")):
            if (d / "SKILL.md").is_file():
                out.append(("domain:" + dom.name, d))
    return out


def load_skill_catalog(repo: Path) -> List[Dict[str, object]]:
    """[{slug, tier, triggers}] — triggers = # of activation_triggers items."""
    catalog: List[Dict[str, object]] = []
    for tier, d in iter_skill_dirs(repo):
        try:
            fm, _ = _split_frontmatter(
                (d / "SKILL.md").read_text(encoding="utf-8", errors="replace"))
        except OSError:
            fm = ""
        catalog.append({"slug": d.name, "tier": tier,
                        "triggers": _count_triggers(fm)})
    return catalog


def _count_triggers(fm: str) -> int:
    """Count list items under the top-level ``activation_triggers:`` key."""
    lines = fm.splitlines()
    n = 0
    in_block = False
    for line in lines:
        if re.match(r"^activation_triggers:\s*$", line):
            in_block = True
            continue
        if in_block:
            if re.match(r"^\s+-\s", line):
                n += 1
            elif re.match(r"^\S", line):
                break
    return n


# --------------------------------------------------------------------------
# Source 1 — commands
# --------------------------------------------------------------------------

def load_commands(repo: Path) -> List[Dict[str, object]]:
    """[{name, skills, scripts}] sorted by command name."""
    slugs = {c["slug"] for c in load_skill_catalog(repo)}
    out: List[Dict[str, object]] = []
    for f in sorted((repo / ".claude/commands").glob("*.md")):
        text = f.read_text(encoding="utf-8", errors="replace")
        _, body = _split_frontmatter(text)
        scripts = {s for s in _SCRIPT_PATH_RE.findall(body)
                   if not s.startswith(".claude/scripts/tests/")}
        out.append({
            "name": f.stem,
            "skills": _skill_refs(body, slugs),
            "scripts": sorted(scripts),
        })
    return out


def _skill_refs(body: str, slugs: "set[str]") -> List[str]:
    """Skill slugs declared in a command body: backticked tokens that match
    a cataloged slug, plus slugs appearing as .claude/skills/ path segments."""
    found = {tok for tok in _BACKTICK_TOKEN_RE.findall(body) if tok in slugs}
    for path in _SKILL_PATH_RE.findall(body):
        for seg in path.split("/"):
            if seg in slugs:
                found.add(seg)
    return sorted(found)


# --------------------------------------------------------------------------
# Source 3 — hook registrations
# --------------------------------------------------------------------------

def load_hook_rows(repo: Path) -> List[Dict[str, object]]:
    """Registration rows from settings.json: [{event, matcher, hook, timeout}].
    Events sorted; within an event, file order is kept (= chain order)."""
    settings = json.loads(
        (repo / ".claude/settings.json").read_text(encoding="utf-8"))
    rows: List[Dict[str, object]] = []
    hooks_obj = settings.get("hooks", {})
    for event in sorted(hooks_obj):
        for entry in hooks_obj[event]:
            matcher = entry.get("matcher", "")
            for hk in entry.get("hooks", []):
                rows.append({
                    "event": event,
                    "matcher": matcher,
                    "hook": _hook_label(hk.get("command", "")),
                    "timeout": hk.get("timeout"),
                })
    return rows


def _hook_label(command: str) -> str:
    """Short label for a hook command: last referenced .py, else last
    file-ish token, else '(inline)' for echo/no-file commands."""
    files = _HOOK_FILE_RE.findall(command)
    pys = [f for f in files if f.endswith(".py")]
    if pys:
        return pys[-1].rsplit("/", 1)[-1]
    if files:
        return files[-1].rsplit("/", 1)[-1]
    return "(inline)"


def surface_guards(repo: Path,
                   rows: Sequence[Dict[str, object]]) -> Dict[str, List[str]]:
    """Which registered hook sources reference each surface.

    Rule (over-approximating, stated in the doc): a hook guards a surface iff
    its source under .claude/hooks/ contains the literal '.claude/skills' or
    'SKILL.md' (skill surface) / '.claude/commands' (command surface)."""
    guards: Dict[str, List[str]] = {"skills": [], "commands": [], "unresolved": []}
    for label in sorted({str(r["hook"]) for r in rows}):
        if label == "(inline)":
            continue
        src = repo / ".claude/hooks" / label
        if not src.is_file():
            guards["unresolved"].append(label)
            continue
        text = src.read_text(encoding="utf-8", errors="replace")
        if ".claude/skills" in text or "SKILL.md" in text:
            guards["skills"].append(label)
        if ".claude/commands" in text:
            guards["commands"].append(label)
    return guards


# --------------------------------------------------------------------------
# Markdown assembly (deterministic — no timestamps)
# --------------------------------------------------------------------------

def _cell(items: Sequence[str], fmt: str = "`{0}`") -> str:
    if not items:
        return "—"
    return ", ".join(fmt.format(i) for i in items)


def _md_escape(text: str) -> str:
    """Escape table-breaking pipes (matchers like Edit|Write|MultiEdit)."""
    return text.replace("|", "\\|")


def _emit_header(out: List[str]) -> None:
    out.append("# COMMAND → SKILL → HOOK map")
    out.append("")
    out.append("<!-- GENERATED FILE — do not edit by hand.")
    out.append(f"     Regenerate: python3 {SELF_REL} --write")
    out.append(f"     CI drift gate: python3 {SELF_REL} --check -->")
    out.append("")
    out.append("Derived deterministically (sorted, no timestamps) from three "
               "committed sources:")
    out.append("")
    out.append("1. `.claude/commands/*.md` — slash-command definitions")
    out.append("2. `.claude/skills/**/SKILL.md` — skill catalog "
               "(core / frontend / domains)")
    out.append("3. `.claude/settings.json` — governance hook registrations")
    out.append("")
    out.append("**Scope honesty.** Every edge below is a *textual declaration "
               "derivable on disk*, not a runtime trace: a command "
               "“references” a skill iff the skill's directory slug "
               "appears in the command body (backticked, or as a "
               "`.claude/skills/` path segment). Hook guards are *path-class* "
               "guards — they protect whole file classes uniformly, so "
               "per-skill guard differentiation is not derivable from disk. "
               "This map documents the wiring of the EXISTING catalog and its "
               "discovery surface; it structurally cannot measure greenfield "
               "domains and is not a green-light for adding skills (PLAN-153 "
               "debate A must-fix 4). Cells carry identifier tokens only; "
               "free prose from scanned files is deliberately not embedded.")
    out.append("")


def _emit_commands(out: List[str], commands: Sequence[Dict[str, object]]) -> None:
    out.append("## 1. Commands → skills / scripts (`.claude/commands/*.md`)")
    out.append("")
    out.append("| Command | Skills referenced | Backing scripts referenced |")
    out.append("|---|---|---|")
    for c in commands:
        out.append("| `/{0}` | {1} | {2} |".format(
            c["name"], _cell(list(c["skills"])), _cell(list(c["scripts"]))))
    out.append("")


def _emit_reverse_index(out: List[str], commands: Sequence[Dict[str, object]],
                        catalog: Sequence[Dict[str, object]]) -> None:
    out.append("## 2. Skills referenced by commands (reverse index)")
    out.append("")
    rev: Dict[str, List[str]] = {}
    for c in commands:
        for s in c["skills"]:  # type: ignore[union-attr]
            rev.setdefault(str(s), []).append(str(c["name"]))
    tiers: Dict[str, List[str]] = {}
    for sk in catalog:
        tiers.setdefault(str(sk["slug"]), []).append(str(sk["tier"]))
    out.append("| Skill | Tier(s) | Referenced by |")
    out.append("|---|---|---|")
    for slug in sorted(rev):
        out.append("| `{0}` | {1} | {2} |".format(
            slug, _cell(sorted(tiers.get(slug, [])), "{0}"),
            _cell(sorted(rev[slug]), "`/{0}`")))
    out.append("")
    out.append("Skills with no command edge are cataloged in §5 totals; the "
               "full per-skill inventory lives in the generated block of "
               "`.claude/skills/core/ceo-orchestration/SKILL.md` "
               "(`generate-skill-inventory.sh`) and is not duplicated here.")
    out.append("")


def _emit_hooks(out: List[str], rows: Sequence[Dict[str, object]]) -> None:
    out.append("## 3. Hook registrations (`.claude/settings.json`)")
    out.append("")
    out.append("Events sorted alphabetically; within an event, rows keep "
               "registration order (= runtime chain order).")
    out.append("")
    out.append("| Event | Matcher | Hook | Timeout (s) |")
    out.append("|---|---|---|---|")
    for r in rows:
        matcher = _md_escape(str(r["matcher"])) if r["matcher"] else "(all)"
        timeout = str(r["timeout"]) if r["timeout"] is not None else "—"
        out.append("| {0} | `{1}` | `{2}` | {3} |".format(
            r["event"], matcher, r["hook"], timeout))
    out.append("")


def _emit_surfaces(out: List[str], guards: Dict[str, List[str]]) -> None:
    out.append("## 4. Surface guards (registered-hook source scan)")
    out.append("")
    out.append("Derivation rule: a registered hook guards a surface iff its "
               "source file under `.claude/hooks/` contains the literal "
               "`.claude/skills` / `SKILL.md` (skill surface) or "
               "`.claude/commands` (command surface). This over-approximates "
               "— a textual mention is treated as guard involvement — and it "
               "applies to the whole surface, never to one skill or command.")
    out.append("")
    out.append("| Surface | Guarding hooks (source references the surface) |")
    out.append("|---|---|")
    out.append("| Skill files (`.claude/skills/**`, `SKILL.md`) | {0} |".format(
        _cell(guards["skills"])))
    out.append("| Command files (`.claude/commands/**`) | {0} |".format(
        _cell(guards["commands"])))
    out.append("")
    if guards["unresolved"]:
        out.append("Registered hooks whose source file was NOT found under "
                   "`.claude/hooks/` (unresolved, honest gap): {0}".format(
                       _cell(guards["unresolved"])))
        out.append("")


def _emit_totals(out: List[str], commands: Sequence[Dict[str, object]],
                 catalog: Sequence[Dict[str, object]],
                 rows: Sequence[Dict[str, object]]) -> None:
    out.append("## 5. Catalog totals")
    out.append("")
    tier_counts: Dict[str, int] = {}
    for sk in catalog:
        tier_counts[str(sk["tier"])] = tier_counts.get(str(sk["tier"]), 0) + 1
    n_domain = sum(v for t, v in tier_counts.items() if t.startswith("domain:"))
    n_domains = sum(1 for t in tier_counts if t.startswith("domain:"))
    with_triggers = sum(1 for sk in catalog if int(sk["triggers"]) > 0)  # type: ignore[arg-type]
    out.append("- Commands: {0}".format(len(commands)))
    out.append("- Skills (SKILL.md-bearing dirs): {0} — core {1}, frontend "
               "{2}, domain {3} (across {4} domains)".format(
                   len(catalog), tier_counts.get("core", 0),
                   tier_counts.get("frontend", 0), n_domain, n_domains))
    out.append("- Skills with >=1 `activation_triggers` entry: {0}".format(
        with_triggers))
    out.append("- Hook registrations: {0} across {1} events ({2} unique hook "
               "labels)".format(
                   len(rows), len({r["event"] for r in rows}),
                   len({r["hook"] for r in rows})))
    out.append("")


def generate(repo: Path) -> str:
    commands = load_commands(repo)
    catalog = load_skill_catalog(repo)
    rows = load_hook_rows(repo)
    guards = surface_guards(repo, rows)
    out: List[str] = []
    _emit_header(out)
    _emit_commands(out, commands)
    _emit_reverse_index(out, commands, catalog)
    _emit_hooks(out, rows)
    _emit_surfaces(out, guards)
    _emit_totals(out, commands, catalog, rows)
    return "\n".join(out).rstrip("\n") + "\n"


# --------------------------------------------------------------------------
# Modes
# --------------------------------------------------------------------------

def write_doc(repo: Path) -> Path:
    doc = repo / DOC_REL
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(generate(repo), encoding="utf-8")
    return doc


def check(repo: Path) -> int:
    """Regen to a temp file + diff vs committed doc. 1 on drift/missing."""
    want = generate(repo)
    with tempfile.TemporaryDirectory(prefix="ceo-cmd-skill-hook-map-") as td:
        tmp = Path(td) / "COMMAND-SKILL-HOOK-MAP.md"
        tmp.write_text(want, encoding="utf-8")
        committed = repo / DOC_REL
        if not committed.is_file():
            print(f"[gen-command-skill-hook-map] DRIFT: {DOC_REL} is missing "
                  "(must be generated + committed)")
            print(f"fix: python3 {SELF_REL} --write  (then commit)")
            return 1
        got = committed.read_text(encoding="utf-8")
        if got != tmp.read_text(encoding="utf-8"):
            print(f"[gen-command-skill-hook-map] DRIFT: {DOC_REL} differs "
                  "from regenerated content")
            sys.stdout.writelines(difflib.unified_diff(
                got.splitlines(keepends=True), want.splitlines(keepends=True),
                fromfile=f"committed/{DOC_REL}", tofile=f"generated/{DOC_REL}"))
            print(f"fix: python3 {SELF_REL} --write  (then commit)")
            return 1
    print(f"[gen-command-skill-hook-map] {DOC_REL} in sync with generator")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Generate/verify the derived COMMAND->SKILL->HOOK map doc.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="regen to temp + diff vs committed doc; "
                           "exit 1 on drift (CI gate)")
    mode.add_argument("--write", action="store_true",
                      help=f"(re)write {DOC_REL}")
    ap.add_argument("--repo", type=Path, default=None,
                    help="repo root override (hermetic tests)")
    args = ap.parse_args(argv)
    repo = (args.repo or default_repo()).resolve()
    if args.check:
        return check(repo)
    if args.write:
        doc = write_doc(repo)
        print(f"[gen-command-skill-hook-map] wrote {doc}")
        return 0
    sys.stdout.write(generate(repo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
