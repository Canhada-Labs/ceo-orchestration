#!/usr/bin/env python3
"""derive-p189-w0.py — derivator of the PLAN-189 W0 pack (cure-the-class rule).

Produces the full-file payloads the SIGN ceremony copies onto the canonical
tree, from ONE source of truth each:

  PROTOCOL.md.new                  = <root>/PROTOCOL.md with payloads/protocol-section.md
                                     inserted before the unique anchor "## 3-Strike policy"
  ADR-140-AMEND-1-cure-the-class.md.new  (authored payload, copied verbatim)

Modes:
  --check-only   verify the anchor is unique in <root>/PROTOCOL.md, the section is
                 not already present, and (if payloads/BASE.sha256 exists) that
                 <root>/PROTOCOL.md still has the recorded base digest. Exit 0/2.
  --write        regenerate payloads/PROTOCOL.md.new and payloads/BASE.sha256.
  --apply        apply the three payloads INTO <root> (PROTOCOL.md, the ADR file,
                 and regenerate .claude/adr/README.md via the repo generator).
                 Refuses by name when the section is already present.

<root> defaults to the repo root that contains this script. stdlib only, py3.9.
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PAYLOADS = HERE / "payloads"
ANCHOR = "\n---\n\n## 3-Strike policy\n"
SECTION_HEAD = "## Cure discipline — cure the class, not the example"
ADR_NAME = "ADR-140-AMEND-1-cure-the-class.md"

# Docs that cite the ADR count (verify-counts.sh gate: 5 exact table cells +
# the prose/comment mentions that would otherwise contradict them). One new
# ADR file ⇒ 198 → 199. Census taken 2026-09-15 on cdc6a51: (path, expected
# number of lines that carry the OLD count next to an ADR mention). --check-only
# refuses when the census no longer matches — the docs drifted, re-census.
ADR_COUNT_OLD, ADR_COUNT_NEW = "198", "199"
# (path, expected lines, line-selector regex). The default selector is any line
# that mentions ADRs; CHANGELOG.md gets a NARROW selector — only the live-count
# header line (rule changelog/header) moves, never the historical release notes
# of v1.4.0 at lines 376/383, which correctly say 198 for that tag.
_ADR_LINE = r"adr|architecture decision"
COUNT_SITES = (
    ("README.md", 2, _ADR_LINE),
    ("README.pt-BR.md", 2, _ADR_LINE),
    ("npm/README.md", 2, _ADR_LINE),
    ("docs/ARCHITECTURE.md", 2, _ADR_LINE),
    ("docs/README.md", 1, _ADR_LINE),
    ("docs/CTO-GUIDE.md", 2, _ADR_LINE),
    ("docs/FAQ.md", 1, _ADR_LINE),
    ("docs/GUIA-COMPLETO.md", 2, _ADR_LINE),
    ("CHANGELOG.md", 1, r"^> v1\.4\.0: .*\bADRs\b"),
)
_OLD_TOKEN = re.compile(r"(?<!\d)" + ADR_COUNT_OLD + r"(?!\d)")


def _bump_lines(text: str, selector: str):
    """Return (new_text, n_lines_changed): OLD→NEW only on lines the selector picks."""
    sel = re.compile(selector, re.IGNORECASE)
    out, n = [], 0
    for line in text.splitlines(keepends=True):
        if sel.search(line) and _OLD_TOKEN.search(line):
            line = _OLD_TOKEN.sub(ADR_COUNT_NEW, line)
            n += 1
        out.append(line)
    return "".join(out), n


def _check_sites(root: pathlib.Path) -> list:
    """Every site must carry EXACTLY the censused number of old-count lines."""
    errs = []
    for rel, want, selector in COUNT_SITES:
        p = root / rel
        if not p.is_file():
            errs.append("missing count site: " + rel)
            continue
        _, n = _bump_lines(p.read_text(encoding="utf-8"), selector)
        if n != want:
            errs.append("count site drifted: %s has %d old-count ADR line(s), census says %d" % (rel, n, want))
    return errs


def _sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _derive(protocol_text: str, section: str) -> str:
    if protocol_text.count(ANCHOR) != 1:
        raise SystemExit("REFUSE: anchor '## 3-Strike policy' is not unique in PROTOCOL.md")
    if SECTION_HEAD in protocol_text:
        raise SystemExit("REFUSE: the Cure discipline section is already present (second apply?)")
    block = "\n---\n\n" + section.rstrip("\n") + "\n"
    return protocol_text.replace(ANCHOR, block + ANCHOR, 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(HERE.parents[3]))
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-only", action="store_true")
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    root = pathlib.Path(a.root).resolve()
    proto = root / "PROTOCOL.md"
    section_p = PAYLOADS / "protocol-section.md"
    adr_src = PAYLOADS / (ADR_NAME + ".new")
    base_p = PAYLOADS / "BASE.sha256"
    for p in (proto, section_p, adr_src):
        if not p.is_file():
            print("REFUSE: missing", p)
            return 2
    text = proto.read_text(encoding="utf-8")
    section = section_p.read_text(encoding="utf-8")

    if a.check_only:
        try:
            _derive(text, section)
        except SystemExit as e:
            print(e)
            return 2
        if base_p.is_file():
            want = base_p.read_text().split()[0]
            have = _sha(proto)
            if want != have:
                print("REFUSE: PROTOCOL.md base drifted: recorded", want[:12], "live", have[:12])
                return 2
        errs = _check_sites(root)
        if errs:
            for e in errs:
                print("REFUSE:", e)
            return 2
        print("OK: anchor unique, section absent, %d count sites match the census%s"
              % (len(COUNT_SITES), ", base matches" if base_p.is_file() else " (no BASE recorded yet)"))
        return 0

    try:
        out = _derive(text, section)
    except SystemExit as e:  # every REFUSE exits 2, in every mode (docstring contract)
        print(e)
        return 2

    if a.write:
        (PAYLOADS / "PROTOCOL.md.new").write_text(out, encoding="utf-8")
        base_p.write_text(_sha(proto) + "  PROTOCOL.md\n")
        print("wrote PROTOCOL.md.new (", len(out.splitlines()), "lines ) and BASE.sha256", _sha(proto)[:12])
        return 0

    # --apply
    adr_dst = root / ".claude" / "adr" / ADR_NAME
    if adr_dst.exists():
        print("REFUSE: ADR already present:", adr_dst)
        return 2
    errs = _check_sites(root)
    if errs:
        for e in errs:
            print("REFUSE:", e)
        return 2
    # every REFUSE above fires BEFORE the first write — nothing is half-applied
    proto.write_text(out, encoding="utf-8")
    adr_dst.write_bytes(adr_src.read_bytes())
    for rel, want, selector in COUNT_SITES:
        p = root / rel
        new_text, n = _bump_lines(p.read_text(encoding="utf-8"), selector)
        assert n == want, rel  # already verified by _check_sites
        p.write_text(new_text, encoding="utf-8")
    gen = root / ".claude" / "scripts" / "generate-adr-index.py"
    r = subprocess.run([sys.executable, str(gen), "--write"], cwd=str(root), capture_output=True, text=True)
    if r.returncode != 0:
        print("REFUSE: generate-adr-index --write failed:", r.stdout[-400:], r.stderr[-400:])
        return 2
    print("applied: PROTOCOL.md, .claude/adr/" + ADR_NAME + ", .claude/adr/README.md (regenerated), "
          + "%d doc count sites %s->%s" % (len(COUNT_SITES), ADR_COUNT_OLD, ADR_COUNT_NEW))
    return 0


if __name__ == "__main__":
    sys.exit(main())
