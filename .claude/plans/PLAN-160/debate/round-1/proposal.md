---
plan: PLAN-160
round: 1
created_at: 2026-07-17
---

# PLAN-160 round-1 proposal — check_canonical_edit.py council-findings hardening

Full plan: `.claude/plans/PLAN-160-canonical-edit-council-findings.md`.

## Thesis

The S276 Wave-4 council live-fire (run `wf_cd40731f-205`, scope
`check_canonical_edit.py`) closed 2-lane DEGRADED but with a CLEAN verification
cascade (`verify_failed=0`) and surfaced 4 candidate defects in the
canonical-edit security gate (A/C/B/D). The CEO independently re-read the cited
code for all four — each claim is grounded in real lines, but each carries an
exploitability caveat. This plan VERIFIES each (failing-first repro) and FIXES
only the ones that reproduce, landing via kernel ceremony.

These are ADVISORY council findings. A council verdict authorizes nothing. Wave
1 is the independent verification the council cannot itself provide.

## The four findings (CEO-verified grounded)

- **A — HIGH, gate-bypass.** `main()` L1367-1374 `break`s at the FIRST
  `_is_canonical` candidate and calls `decide()` ONCE (L1377). A multi-file MCP
  `apply_patch` with a sentinel-GRANTED canonical path ordered before an
  UNGRANTED canonical path lets the 2nd ride through ungated. Convergent
  (claude+codex independently). Reachability hinges on the MCP adapter emitting
  multi-file `apply_patch_paths`.
- **C — MED, fail-open on canonical path.** `decide()` L1136-1139: after
  `_is_canonical`→True (L1131), the repo-relative resolve (L1137) is wrapped in
  `except (ValueError, OSError): return _emit_allow()` — fail-OPEN on a
  confirmed-canonical path, contradicting F-01-07 fail-CLOSED. Reachability
  coupled to D: `_is_canonical` (L691) does the SAME resolve and only returns
  True if it succeeded, so L1137 raising requires a DIVERGENCE (TOCTOU or the D
  CWD-mismatch).
- **B — LOW, revocation staleness (bounded).** `_compute_sentinel_cache_key`
  L827-840 hashes only sentinel bytes+stat+target_rel — omits
  `.asc`/allowlist/registry; comment (L802-803) falsely claims `.asc` coverage.
  BUT the cache is module-scope and each hook is a FRESH subprocess
  (`hook-profiler.py:178`), so "process death" ≈ one invocation (ms). Blast
  radius likely negligible → maybe comment-fix only.
- **D — MED, path-resolution bypass.** `_is_canonical` L689-694:
  `Path(path_str).resolve()` is CWD-anchored but compared via
  `relative_to(repo_root)` where `repo_root = CLAUDE_PROJECT_DIR or cwd`; a
  RELATIVE canonical path when `CWD != CLAUDE_PROJECT_DIR` raises → `return
  False` → non-canonical → allowed. Exploitability needs the harness to pass a
  relative path with CWD divergence.

E (envelope `parse_error → allow`) and F (`apply_patch` blobs unparsed) are OUT
of scope — E is a documented infra-class fail-open (CLAUDE.md §4, correct); F is
a documented Layer-A/B boundary. Recorded no-action.

## Decisions proposed

1. **Verification-first.** No fix lands without a repro that FAILS on current
   HEAD and PASSES after. A finding whose repro Wave 1 cannot build is
   dispositioned not-reachable / accepted-boundary, recorded, not fixed.
2. **Fix-A shape:** iterate `decide()` over EVERY canonical candidate,
   most-restrictive-wins (ANY ungranted canonical path blocks the event);
   preserve the single-candidate fast path outcome-identically.
3. **Fix-C:** the `except` on a confirmed-canonical path fails-CLOSED
   (`canonical_edit_hook_fault`), matching F-01-07 — even if Wave 1 proves it
   unreachable (cheap defense-in-depth).
4. **Fix-D:** anchor `path_str` resolution to `repo_root`, not CWD.
5. **Fix-B:** minimally fix the false comment; add allowlist/`.asc` to the key
   only if Wave 1 finds a same-process re-entrancy window.
6. **Kernel ceremony** to land (check_canonical_edit.py is `_KERNEL_PATHS`);
   ADR for any fail-open/closed contract change (C) or policy change (A).

## Open questions

- **OQ1** — Fix-A: iterate-all-candidates vs a cheaper any-ungranted-canonical
  short-circuit. CEO default: iterate, most-restrictive-wins.
- **OQ2** — If Wave 1 proves C/D unreachable, harden anyway (defense-in-depth)
  or annotate-and-leave? CEO default: harden C (cheap, contract-correct);
  annotate D if truly unreachable.

## Critique focus requested

Each critic: is the verification-first sequencing right? Is fix-A's
most-restrictive-wins shape correct and complete (any ordering / candidate-set
edge cases it misses)? Does fixing C to fail-closed risk bricking benign
sessions (the reason the fail-open exists)? Is B worth any code change given the
subprocess-lifetime bound, or is the comment-fix the honest disposition? Any
finding mis-severity'd, and anything UNSEEN — a fifth defect class in the same
gate, or a way a fix regresses an existing guarantee?
