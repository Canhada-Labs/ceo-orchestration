---
plan: PLAN-160
round: 1
type: architect-sentinel
segment: CANONICAL-HARDENING
---

# PLAN-160 canonical-edit hardening — Owner sentinel

Anchor-SHA: 8c7877aa581a69f274b6debce23f415cdb410254

Approved-By: @Canhada-Labs (Owner GPG — signed inline by the ceremony)
Approved-At: 2026-07-17

## Scope

Canonical paths this sentinel authorizes (touched − scope MUST be ∅ for the
non-count-surface files; the CLAUDE.md + doc count-bumps are UNGUARDED and
ride the same commit):

Scope:
  - .claude/hooks/check_canonical_edit.py
  - .claude/adr/ADR-164-canonical-multicandidate-and-failclosed.md
  - .claude/adr/ADR-165-canonical-shared-predicate-dual-anchor.md

## What is authorized

The S276 council-finding hardening of the canonical-edit gate
(`check_canonical_edit.py`, a `_KERNEL_PATHS` entry), verified in PLAN-160
Wave 1 (failing-first repros) and reviewed in Wave 2 (codex pair-rail
round-2 APPROVE + security-engineer VETO→resolved):

- **Finding A** (HIGH gate-bypass): most-restrictive-wins multi-candidate
  scan, emit-once, `_find_sentinels` hoisted+lazy+guarded, candidate cap 512
  fail-closed, per-candidate/scan fault fail-CLOSED via `_forced_out`
  bypassing `decide()`. **ADR-164.**
- **Finding C** (MED fail-open): `decide()` resolve fault on a
  confirmed-canonical path now fail-CLOSED (`canonical_edit_hook_fault`),
  matching PLAN-045 F-01-07. **ADR-164.**
- **Finding D** (MED path bypass): `_is_canonical` dual-anchor
  (CWD + repo_root, most-restrictive) via single-source
  `_repo_rels`/`_canonical_rel`, made TOTAL (`except Exception`) so a
  symlink-loop `RuntimeError` cannot fail-open the multi-candidate scan.
  Shared predicate → also the `--is-canonical` CLI oracle. **ADR-165.**

Findings B, E, F: reviewed / no-action (B = comment-only; E/F = documented
Layer boundary / infra fail-open — see the plan).

## Kernel override

`check_canonical_edit.py` is a `_KERNEL_PATHS` entry:
`CEO_KERNEL_OVERRIDE=PLAN-160-CANONICAL-HARDENING` + `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`
are exported by the ceremony for this apply only and unset after (ADR-031).

## Evidence anchored by this signature

- Wave-1 repros: `.claude/hooks/tests/test_canonical_edit_council_findings.py`
  — HEAD 9 passed / 5 skipped / 5 xfailed; `--runxfail` fails exactly the 5
  repros; STAGED (PLAN160_HOOK_PATH) 19 passed.
- Clean-clone mirror (staged overlaid on canonical): full `.claude/hooks/tests/`
  suite green, zero regressions.
- Pair-rail: codex round-2 APPROVE (no findings); security-engineer
  round-2 (VETO resolved).
- Behavioral oracle probe (ceremony preflight): the staged bytes actually
  block a `{granted, ungranted}` multi-candidate smuggle — a signature is
  refused unless the A-fix is present in the bytes.
