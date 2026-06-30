#!/usr/bin/env python3
"""admin-invite.py — Generate an onboarding pack for a new team member.

PLAN-010 Phase 6 (Security Engineer). Safe defaults:

- Default output directory is ``~/ceo-onboarding-packs/pack-<slug>/`` (NOT
  the current working directory — debate C13). This avoids accidentally
  dropping onboarding artifacts inside a git repo.
- Output files are scanned to ensure NO environment-variable-shaped
  secrets leak through. ``admin-invite`` only copies static docs, but the
  test suite enforces the invariant by scanning every generated file for
  any uppercase shell-variable name that matches the environment.
- Exit codes: 0 ok, 1 refuse (dir exists), 2 usage.

Stdlib only, Python 3.9+.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
FOR_EMPLOYEES_PATH = REPO_ROOT / "docs" / "FOR-EMPLOYEES.md"
FIRST_SESSION_PATH = REPO_ROOT / "examples" / "first-session.md"

CHECKLIST_CONTENT = """# First-session checklist

Follow these steps on your very first Claude Code session with the
ceo-orchestration framework already installed.

- [ ] Open Claude Code inside the target project directory (`claude`).
- [ ] Send the activation prompt: **"Ativa o protocolo CEO."**
- [ ] Verify the CEO confirms Gate 1 / Gate 2 / Gate 3 pass.
- [ ] Read `CLAUDE.md` and replace any remaining `{{PROJECT_NAME}}` /
      `{{OWNER_NAME}}` placeholders in your project.
- [ ] Ask for a tiny feature ("adiciona rate-limit no endpoint X") so
      the CEO drafts a PLAN and (if L3+) opens a `/debate`.
- [ ] Confirm at session end that a plan file was created under
      `.claude/plans/PLAN-<NNN>-*.md`.
- [ ] Read `docs/FOR-EMPLOYEES.md` (included in this pack) for the
      ground rules: veto gates, spawn protocol, conditional gates.
- [ ] Skim `docs/GLOSSARY.md` in the framework repo for terminology.

For the full end-to-end narrative walkthrough, see
`examples/first-session.md` in the ceo-orchestration repository.
"""

MEMORY_SEED_CONTENT = """# Memory seed — personalize me

> These are templates for `~/.claude/projects/<project-slug>/memory/`.
> Edit each file, then drop it into the memory directory. The CEO will
> auto-load them on session start.

## user_role.md

```
# User: <your role>

- Name: <your name>
- Role: <Owner / Senior Engineer / PM / etc.>
- Language: <PT-BR / EN / other>
- Trusts CEO to run the protocol autonomously: <yes/no>
- Prefers detail level: <high / balanced / terse>
```

## feedback_preferences.md

```
# Feedback preferences

- I prefer reasoning-first explanations before code changes: <yes/no>
- Show diffs inline vs. in files: <inline / files>
- Stop at each L3+ decision for explicit approval: <yes/no>
- Debate round count default: <1 / 2 / 3>
```

Save each file as its own `.md` inside your memory directory, then add
a line to the `MEMORY.md` index so auto-load finds it.
"""


def _slugify(name: str) -> str:
    """Make a filesystem-safe slug from a (possibly Unicode) name."""
    # Replace anything that isn't alphanumeric/underscore/dash with "-",
    # then collapse runs of "-" and strip leading/trailing dashes.
    cleaned = re.sub(r"[^\w\-]+", "-", name, flags=re.UNICODE)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-").lower()
    return cleaned or "invite"


def _default_out_dir(name: str) -> Path:
    slug = _slugify(name)
    return Path.home() / "ceo-onboarding-packs" / f"pack-{slug}"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_pack(name: str, out_dir: Path, force: bool = False) -> List[Path]:
    """Build the onboarding pack. Returns list of created files.

    Raises FileExistsError if ``out_dir`` exists and is non-empty and
    force is False.
    """
    if out_dir.exists() and any(out_dir.iterdir()) and not force:
        raise FileExistsError(str(out_dir))

    if out_dir.exists() and force:
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    created: List[Path] = []

    # 1. Copy FOR-EMPLOYEES.md if present; otherwise ship a stub so the
    # pack is still useful in test environments.
    target_fe = out_dir / "FOR-EMPLOYEES.md"
    if FOR_EMPLOYEES_PATH.exists():
        shutil.copy2(FOR_EMPLOYEES_PATH, target_fe)
    else:
        target_fe.write_text(
            "# FOR-EMPLOYEES (stub)\n\nSource doc not found at build time.\n",
            encoding="utf-8",
        )
    created.append(target_fe)

    # 2. Checklist
    checklist = out_dir / "first-session-checklist.md"
    _write(checklist, CHECKLIST_CONTENT)
    created.append(checklist)

    # 3. Memory seed template
    seed = out_dir / "memory-seed.md"
    _write(seed, MEMORY_SEED_CONTENT)
    created.append(seed)

    # 4. README welcome
    readme = out_dir / "README.md"
    _write(
        readme,
        "# Welcome, {}\n\nThis onboarding pack was generated for you.\n\n"
        "Start with `first-session-checklist.md`, then read "
        "`FOR-EMPLOYEES.md`.\n".format(name),
    )
    created.append(readme)

    return created


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — generate an admin invitation envelope."""
    parser = argparse.ArgumentParser(
        prog="admin-invite",
        description="Generate an onboarding pack for a new team member.",
    )
    parser.add_argument("--name", required=True, help="Invitee name (Unicode ok).")
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Output directory. Default: ~/ceo-onboarding-packs/pack-<slug>/",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite if out-dir exists and is non-empty.",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0

    name = args.name
    out_dir = Path(args.out_dir).expanduser() if args.out_dir else _default_out_dir(name)

    try:
        created = build_pack(name, out_dir, force=args.force)
    except FileExistsError as exc:
        sys.stderr.write(
            f"error: output directory exists and is non-empty: {exc}\n"
            f"       re-run with --force to overwrite.\n"
        )
        return 1

    sys.stdout.write(f"pack: {out_dir}\nfiles: {len(created)}\n")
    for p in created:
        sys.stdout.write(f"  - {p.name}\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
