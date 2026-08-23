"""Assemble a staged ceremony pack: prune caches, emit BASELINE/MANIFEST, classify.

Usage: python3 assemble_pack.py <pack-dir-relative-to-repo-root>

BASELINE.sha256 = sha256 of the LIVE file for every staged path that already
exists live (the anti-stale gate compares these at land time).
MANIFEST.sha256 = sha256 of every staged file (pack integrity).
Also prints NEW vs MODIFIED vs IDENTICAL — an IDENTICAL staged file is dead
weight in the pack and is reported loudly, never silently shipped.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
from pathlib import Path


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: assemble_pack.py <pack-dir>", file=sys.stderr)
        return 2
    root = Path.cwd()
    pack = root / sys.argv[1]
    if not pack.is_dir():
        print("no such pack dir: %s" % pack, file=sys.stderr)
        return 2

    # 1. prune build caches — they must never enter a signed manifest
    pruned = 0
    for d in sorted(pack.rglob("__pycache__"), reverse=True):
        shutil.rmtree(d, ignore_errors=True)
        pruned += 1
    for f in list(pack.rglob("*.pyc")) + list(pack.rglob(".DS_Store")):
        f.unlink(missing_ok=True)
        pruned += 1

    # PACKMAP: a pack file may land at a DIFFERENT repo path. One reason only,
    # and it is explicit: settings.json denies Edit(SPEC/**) and that glob
    # matches any path containing a SPEC/ segment — including a staged copy.
    # The deny is correct (the SPEC is written by the signed ceremony alone),
    # so the pack artifact carries a flat name and its destination lives here.
    packmap = {}
    mapfile = pack / "PACKMAP.txt"
    if mapfile.is_file():
        for raw in mapfile.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or " -> " not in line:
                continue
            src, dst = line.split(" -> ", 1)
            packmap[src.strip()] = dst.strip()

    # 2. enumerate payload files (everything except the manifests themselves)
    # Pack-only DOCS never land: they describe how to assemble the pack and
    # have no repo destination. Without this skip they are classified NEW at
    # the REPO ROOT and G5 of the land script cp's them there, inside the
    # SIGNED sentinel Scope. staged-w01 never exposed the class because its
    # five root files (CHANGELOG/CLAUDE/INSTALL/README/README.pt-BR) are
    # legitimate root destinations; staged-w24's two are not.
    skip = {"BASELINE.sha256", "MANIFEST.sha256", "PACKMAP.txt"}
    _PACK_DOC_SUFFIXES = ("-COMO-MONTAR.md", "-NOTE.md")
    files = sorted(
        p for p in pack.rglob("*")
        if p.is_file() and p.name not in skip
        and not p.name.endswith(_PACK_DOC_SUFFIXES)
    )
    if not files:
        print("pack is empty", file=sys.stderr)
        return 2

    # A destination claimed by a PACKMAP entry belongs to that entry alone. A
    # second pack file landing on the same path is a leftover (typically the
    # byte-identical base copy an implementer made before hitting a deny) and
    # is EXCLUDED from the manifest — the manifest is the authority for what
    # lands, so exclusion is the safe direction. Reported, never silent.
    mapped_dests = set(packmap.values())
    shadowed = [
        p for p in files
        if p.relative_to(pack).as_posix() not in packmap
        and p.relative_to(pack).as_posix() in mapped_dests
    ]
    files = [p for p in files if p not in shadowed]

    baseline, manifest = [], []
    new, modified, identical = [], [], []
    for p in files:
        rel = p.relative_to(pack).as_posix()
        h_staged = sha(p)
        manifest.append("%s  %s" % (h_staged, rel))
        dest = packmap.get(rel, rel)
        live = root / dest
        if live.is_file():
            h_live = sha(live)
            baseline.append("%s  %s" % (h_live, dest))
            (identical if h_live == h_staged else modified).append(dest)
        else:
            new.append(dest)

    (pack / "BASELINE.sha256").write_text("\n".join(baseline) + "\n")
    (pack / "MANIFEST.sha256").write_text("\n".join(manifest) + "\n")

    print("pack: %s" % sys.argv[1])
    print("pruned cache entries: %d" % pruned)
    print("MANIFEST entries: %d   BASELINE entries: %d" % (len(manifest), len(baseline)))
    print("\nNEW (absent live) — %d:" % len(new))
    for r in new:
        print("  + %s" % r)
    if shadowed:
        print("\nEXCLUDED (destination owned by a PACKMAP entry) — %d:" % len(shadowed))
        for p in shadowed:
            print("  x %s" % p.relative_to(pack).as_posix())
    print("\nMODIFIED — %d:" % len(modified))
    for r in modified:
        print("  M %s" % r)
    if identical:
        print("\n!! IDENTICAL to live — %d (DEAD WEIGHT: drop from the pack or the"
              " edit never happened):" % len(identical))
        for r in identical:
            print("  = %s" % r)
    return 1 if identical else 0


if __name__ == "__main__":
    raise SystemExit(main())
