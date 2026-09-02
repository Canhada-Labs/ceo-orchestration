#!/usr/bin/env python3
"""PLAN-186 W1 — anchor-exact derivator: make `model:` EXPLICIT in every
`agent()` call site across the 4 canonical Workflow scripts.

STUDY ARTIFACT (PLAN-186 W1, S339) — NOT applied to the live tree by this
session. The patch this script produces is input to a future /debate and
ceremony; it is proven only inside a disposable git worktree (shadow).

Stdlib only, Python >= 3.9 (repo convention — CLAUDE.md Sec.4). No
`from __future__ import annotations` needed (no PEP 604 syntax used), but
included for consistency with the rest of the repo.

Anchors are the EXACT, byte-literal `opts` object text of each `agent()`
call (label + phase + schema) as it exists in the 4 canonical workflow
files at HEAD 8efe09b (2026-09-02, S339). This is a *textual site* count,
not a *runtime dispatch* count: a call site inside a `.map()`/loop (e.g.
audit-fanout's 8-dimension finder loop) is ONE anchor in source and adds
`model:` to every runtime dispatch derived from that site, because the
opts literal is evaluated once per iteration with the SAME model value.

** IMPORTANT DISCREPANCY (see DESIGN-W1-S339.md Sec.1) **
The spawn prompt for this study cites "17 chamadas agent()" split
5/4/4/4 across the 4 files (echoing S339 report Sec.4.1's "Nenhuma das
17 chamadas agent() passa model:"). A direct grep+read of the 4 canonical
files at HEAD 8efe09b finds only 10 textual `agent(assertDispatchable(...))`
call sites (3 + 2 + 3 + 2). This script targets the VERIFIED 10, not the
cited 17 — see DESIGN doc for the reconciliation attempt and the open
question left for the Owner/refuter.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

# Each site: (relative file path, anchor OLD text, anchor NEW text, model id,
# role label used in DESIGN classification, 1-line note).
SITES = [
    (
        ".claude/workflows/audit-fanout.js",
        "{ label: `find:${d.key}`, phase: 'Find', schema: FINDER_SCHEMA }",
        "{ label: `find:${d.key}`, phase: 'Find', schema: FINDER_SCHEMA, model: 'claude-sonnet-5' }",
        "claude-sonnet-5",
        "finder/pesquisa",
        "8-dimension finder loop (DIMENSIONS.length=8) — one anchor covers all 8 runtime dispatches",
    ),
    (
        ".claude/workflows/audit-fanout.js",
        "{ label: `refute:${dim}`, phase: 'Refute', schema: VERDICT_SCHEMA }",
        "{ label: `refute:${dim}`, phase: 'Refute', schema: VERDICT_SCHEMA, model: 'claude-opus-5' }",
        "claude-opus-5",
        "refutador adversarial",
        "per-surviving-dimension refuter loop — adversarial re-check of finder claims",
    ),
    (
        ".claude/workflows/audit-fanout.js",
        "{ label: 'synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA }",
        "{ label: 'synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA, model: 'claude-fable-5-1' }",
        "claude-fable-5-1",
        "sintese/REDUCE",
        "single synthesis agent — merges confirmed/refuted/unverifiable into the report",
    ),
    (
        ".claude/workflows/nightly-hygiene.js",
        "{ label: `hygiene:${d.key}`, phase: 'Sweep', schema: DIM_SCHEMA }",
        "{ label: `hygiene:${d.key}`, phase: 'Sweep', schema: DIM_SCHEMA, model: 'claude-sonnet-5' }",
        "claude-sonnet-5",
        "finder/pesquisa/censo",
        "9-dimension hygiene sweep loop — read-only census agents",
    ),
    (
        ".claude/workflows/nightly-hygiene.js",
        "{ label: 'hygiene:synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA }",
        "{ label: 'hygiene:synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA, model: 'claude-fable-5-1' }",
        "claude-fable-5-1",
        "sintese/REDUCE",
        "single synthesis agent — merges the 9 dimension results into one report",
    ),
    (
        ".claude/workflows/council-audit.js",
        "{ label: `lane:${vendor}`, phase: 'Council', schema: LANE_SCHEMA }",
        "{ label: `lane:${vendor}`, phase: 'Council', schema: LANE_SCHEMA, model: 'claude-sonnet-5' }",
        "claude-sonnet-5",
        "finder/pesquisa [DUVIDA]",
        "per-vendor lane loop — 'claude' lane is in-harness review, codex/grok lanes are thin external-CLI transport wrappers; see DESIGN Sec.2 item 6",
    ),
    (
        ".claude/workflows/council-audit.js",
        "{ label: 'verify', phase: 'Verify', schema: VERDICT_SCHEMA }",
        "{ label: 'verify', phase: 'Verify', schema: VERDICT_SCHEMA, model: 'claude-opus-5' }",
        "claude-opus-5",
        "refutador adversarial",
        "single in-harness adversarial verifier over all lane findings (conditional call)",
    ),
    (
        ".claude/workflows/council-audit.js",
        "{ label: 'reduce', phase: 'Reduce', schema: SYNTH_SCHEMA }",
        "{ label: 'reduce', phase: 'Reduce', schema: SYNTH_SCHEMA, model: 'claude-fable-5-1' }",
        "claude-fable-5-1",
        "sintese/REDUCE",
        "single synthesis agent — cross-vendor verdict + disagreement surface",
    ),
    (
        ".claude/workflows/eval-baseline-n20.js",
        "{ label: `eval:${MODEL}:batch${i + 1}`, phase: 'Eval', schema: BATCH_SCHEMA }",
        "{ label: `eval:${MODEL}:batch${i + 1}`, phase: 'Eval', schema: BATCH_SCHEMA, model: 'claude-sonnet-5' }",
        "claude-sonnet-5",
        "grader/eval mecanico [DUVIDA]",
        "4-batch eval loop — the ORCHESTRATOR agent's own model; the evaluated MODEL runs via `claude -p --model <MODEL>` subprocess (opts.model here is inert-by-design for the eval target, only tiers the wrapper agent's own cost); see DESIGN Sec.2 item 9",
    ),
    (
        ".claude/workflows/eval-baseline-n20.js",
        "{ label: `eval:${MODEL}:reconcile`, phase: 'Reconcile', schema: RECON_SCHEMA }",
        "{ label: `eval:${MODEL}:reconcile`, phase: 'Reconcile', schema: RECON_SCHEMA, model: 'claude-fable-5-1' }",
        "claude-fable-5-1",
        "sintese/REDUCE",
        "single reconciler agent — closes counts across the 4 eval batches",
    ),
]

MODEL_TOKEN_RE_HINT = "model:"  # used only for the "already has model" pre-check


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def list_sites() -> int:
    print(f"{len(SITES)} anchor site(s) declared (see module docstring — this is a VERIFIED count,")
    print("not the 17 cited in the spawn prompt; DESIGN-W1-S339.md Sec.1 reconciles the gap).\n")
    by_model = {}
    for f, old, new, model, role, note in SITES:
        by_model.setdefault(model, 0)
        by_model[model] += 1
        print(f"[{f}] model={model} role={role}")
        print(f"  anchor: {old}")
        print(f"  note:   {note}\n")
    print("Count by model:")
    for m, n in sorted(by_model.items()):
        print(f"  {m}: {n}")
    return 0


def check(root: Path) -> int:
    # Codex P2 (V2 review of this same script): the previous version accepted
    # n_new >= 1 in the "already applied" branch (a duplicated NEW anchor
    # passed silently) and its `elif n_old == 1: pass` branch ignored n_new
    # entirely (a tree carrying BOTH the OLD and the NEW form — drift or a
    # partial/duplicated apply — read as CHECK OK). Reproduced as a live
    # false-green in two disposable shadow worktrees before this fix (see
    # EVIDENCE-S339.md Sec.11). Cure: each site MUST be in EXACTLY ONE of two
    # mutually exclusive states — (n_old=1, n_new=0) pending, or (n_old=0,
    # n_new=1) already-applied. Any other (n_old, n_new) pair — both zero,
    # both nonzero, or either count >1 — is a named CHECK FAILED, never a
    # silent pass.
    errs = []
    applied_sites = []
    pending_sites = []
    files_seen = set()
    for f, old, new, model, role, note in SITES:
        path = root / f
        if not path.exists():
            errs.append(f"MISSING FILE: {f}")
            continue
        files_seen.add(f)
        text = _read(path)
        n_old = text.count(old)
        n_new = text.count(new)
        if n_old == 1 and n_new == 0:
            pending_sites.append(f"{f} :: {old!r}")
        elif n_old == 0 and n_new == 1:
            applied_sites.append(f"{f} :: {new!r}")
        else:
            errs.append(
                f"{f}: anchor in an invalid state (OLD count={n_old}, NEW count={n_new}; "
                f"expected EXACTLY (1,0)=pending XOR (0,1)=already-applied, never both/neither/duplicated) "
                f"— OLD={old!r} NEW={new!r}"
            )
    for a in applied_sites:
        print(f"ALREADY-APPLIED: {a}")
    if errs:
        print(f"CHECK FAILED — {len(errs)} problem(s):")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(f"CHECK OK — {len(SITES)} anchor(s) verified across {len(files_seen)} file(s) "
          f"({len(pending_sites)} pending, {len(applied_sites)} already-applied).")
    return 0


def apply(root: Path) -> int:
    # Refuse double application: if ANY site's NEW form is already present,
    # abort before touching anything (all-or-nothing per file, per Codex
    # r1 P2 style taint-the-whole-declaration discipline used elsewhere in
    # these same workflow files).
    already = []
    for f, old, new, model, role, note in SITES:
        path = root / f
        if not path.exists():
            print(f"APPLY REFUSED — missing file: {f}", file=sys.stderr)
            return 2
        text = _read(path)
        if new in text:
            already.append(f"{f} :: {new!r}")
    if already:
        print("APPLY REFUSED — double-application guard: the following anchor(s) are")
        print("already in their NEW (model-explicit) form:")
        for a in already:
            print(f"  - {a}")
        return 3

    by_file = {}
    for f, old, new, model, role, note in SITES:
        by_file.setdefault(f, []).append((old, new, model))

    edited_files = 0
    total_edits = 0
    for f, edits in by_file.items():
        path = root / f
        text = _read(path)
        file_edits = 0
        for old, new, model in edits:
            n = text.count(old)
            if n != 1:
                print(f"APPLY ABORTED mid-run at {f}: anchor count={n} (expected 1) for {old!r}",
                      file=sys.stderr)
                return 4
            text = text.replace(old, new, 1)
            file_edits += 1
        _write(path, text)
        edited_files += 1
        total_edits += file_edits
        print(f"{f}: {file_edits} edit(s) applied")

    print(f"\n{total_edits} edicoes em {edited_files} arquivos")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="repo root (default: cwd)")
    ap.add_argument("--list-sites", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()

    if sum([args.list_sites, args.check, args.apply]) != 1:
        print("Exactly one of --list-sites | --check | --apply is required.", file=sys.stderr)
        return 64

    if args.list_sites:
        return list_sites()
    if args.check:
        return check(root)
    if args.apply:
        return apply(root)
    return 64


if __name__ == "__main__":
    raise SystemExit(main())
