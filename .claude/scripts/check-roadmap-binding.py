#!/usr/bin/env python3
"""check-roadmap-binding.py — PLAN-105 Wave B.4 advisory validator.

Verifies every `maps_to_roadmap_items:` ID in every .claude/plans/PLAN-*.md
frontmatter resolves to a row in:

  .claude/plans/PLAN-084/canonical/PLAN-084-evolution-roadmap.md (F-A-* rows)
  OR
  .claude/plans/PLAN-084/canonical/PLAN-084-findings-master.{md,jsonl} (F-* IDs)

Operating modes:
  default (advisory) — Report unresolved IDs to stderr, exit 0. Matches
                       PLAN-105 §Wave B.4 "advisory-only at PLAN-105 ship".
  --strict           — Exit 1 if ANY unresolved IDs found (future CI gate).

Exit:
  0 — clean OR advisory (default mode with unresolved IDs reported)
  1 — strict mode + unresolved IDs found
  2 — infrastructure error (missing canonical sources)

Promotion to default --strict deferred to a follow-up plan after 30d
clean passes.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Set, Tuple


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    cand = here.parent
    while cand != cand.parent:
        if (cand / ".claude").is_dir():
            return cand
        cand = cand.parent
    return Path.cwd()


_REPO = _repo_root()
_ROADMAP = _REPO / ".claude/plans/PLAN-084/canonical/PLAN-084-evolution-roadmap.md"
_FINDINGS_MD = _REPO / ".claude/plans/PLAN-084/canonical/PLAN-084-findings-master.md"
_FINDINGS_JSONL = _REPO / ".claude/plans/PLAN-084/canonical/PLAN-084-findings-master.jsonl"

# Match F-A-* or F-B-* / F-X-NAMESPACE-NNNN style IDs.
_ID_RE = re.compile(r"\bF-[A-Z]-[A-Z0-9-]+\b")
_RNNN_RE = re.compile(r"\bR-\d{3}\b")  # legacy roadmap R-NNN IDs


def _load_canonical_ids() -> Set[str]:
    ids: Set[str] = set()
    for path in (_ROADMAP, _FINDINGS_MD):
        if path.exists():
            text = path.read_text(encoding="utf-8")
            ids.update(_ID_RE.findall(text))
            ids.update(_RNNN_RE.findall(text))
    if _FINDINGS_JSONL.exists():
        for line in _FINDINGS_JSONL.read_text(encoding="utf-8").splitlines():
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                fid = obj.get("id") or obj.get("finding_id")
                if isinstance(fid, str):
                    ids.add(fid)
    return ids


def _extract_plan_ids(plan_path: Path) -> List[str]:
    src = plan_path.read_text(encoding="utf-8")
    # PLAN-105 R2 P2 fold — line-anchored frontmatter parse (split on
    # `\n---\n` between leading frontmatter delimiters only).
    if not src.startswith("---"):
        return []
    end_marker = "\n---"
    rest = src[3:]
    end_idx = rest.find(end_marker)
    if end_idx < 0:
        return []
    fm = rest[:end_idx]
    out: List[str] = []
    in_block = False
    for line in fm.splitlines():
        stripped = line.strip()
        if stripped.startswith("maps_to_roadmap_items:"):
            in_block = True
            # Inline list?
            tail = stripped[len("maps_to_roadmap_items:"):].strip()
            if tail.startswith("[") and tail.endswith("]"):
                inner = tail[1:-1].strip()
                if inner:
                    for item in inner.split(","):
                        item = item.strip().strip('"').strip("'")
                        if item:
                            out.append(item)
                in_block = False
            continue
        if in_block:
            if line and not (line.startswith(" ") or line.startswith("\t")):
                # Left the block (key at column 0).
                in_block = False
                continue
            s = line.strip()
            if s.startswith("#") or not s:
                continue
            if s.startswith("- "):
                token = s[2:].strip()
                # Strip trailing comment.
                hash_idx = token.find("#")
                if hash_idx >= 0:
                    token = token[:hash_idx].strip()
                token = token.strip('"').strip("'")
                if token:
                    out.append(token)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="check-roadmap-binding",
        description="PLAN-105 Wave B.4 advisory validator for maps_to_roadmap_items binding."
    )
    p.add_argument("--strict", action="store_true",
                   help="Exit 1 on unresolved IDs (future CI-blocking mode).")
    args = p.parse_args(argv)
    canonical = _load_canonical_ids()
    if not canonical:
        print(
            "ERROR: no canonical IDs loaded from "
            f"{_ROADMAP} / {_FINDINGS_MD} / {_FINDINGS_JSONL}",
            file=sys.stderr,
        )
        return 2
    plans_dir = _REPO / ".claude/plans"
    unresolved: List[Tuple[str, str]] = []
    examined = 0
    for plan_file in sorted(plans_dir.glob("PLAN-*.md")):
        try:
            ids = _extract_plan_ids(plan_file)
        except Exception as exc:
            print(f"WARN: failed to parse {plan_file.name}: {exc}", file=sys.stderr)
            continue
        examined += 1
        for plan_id in ids:
            if plan_id not in canonical:
                unresolved.append((plan_file.name, plan_id))
    if unresolved:
        mode = "STRICT" if args.strict else "ADVISORY"
        print(f"check-roadmap-binding [{mode}]: {len(unresolved)} unresolved ID(s) "
              f"across {examined} plan file(s):", file=sys.stderr)
        for plan_name, plan_id in unresolved:
            print(f"  {plan_name}: {plan_id}", file=sys.stderr)
        if args.strict:
            return 1
        # Advisory mode — report to stderr, exit 0 per AC14.
        print(f"check-roadmap-binding: advisory — {len(unresolved)} unresolved "
              f"(see stderr). Exit 0 per PLAN-105 §Wave B.4 advisory-only.")
        return 0
    print(f"check-roadmap-binding: OK — examined {examined} plan file(s), "
          f"all maps_to_roadmap_items IDs resolved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
