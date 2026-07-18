# ADR-164 — Canonical-edit gate: most-restrictive multi-candidate policy + fail-closed resolve

- **Status:** accepted
- **Date:** 2026-07-17
- **Plan:** PLAN-160 (findings A + C)
- **Blast radius:** L3 (kernel security gate; `.claude/hooks/check_canonical_edit.py` — a `_KERNEL_PATHS` entry)
- **Debate:** PLAN-160 round-1 (3 critics — security[opus]/qa/arch, 3× ADJUST → consensus PROCEED) — `.claude/plans/PLAN-160/debate/round-1/consensus.md`
- **Council origin:** S276 Wave-4 live-fire (`wf_cd40731f-205`), findings A + C, CEO-verified against real lines

## Context

The canonical-edit guard (`check_canonical_edit.py`) is Layer L1 of the
defense-in-depth stack (see the CEO skill §Enforcement layers). Two of the
four S276 council findings against it are genuine gate defects, both
CEO-verified grounded and confirmed by the Wave-1 failing-first repros:

**Finding A — multi-candidate gate bypass (HIGH).** `main()` processes an
event that can carry multiple target paths (an `mcp__*` tool call, or a
codex `apply_patch` surfacing several files via `apply_patch_paths`). The
historical Layer-A scan **broke at the FIRST canonical candidate** and
called `decide()` exactly once on that path:

```python
for candidate in candidate_paths:
    if _is_canonical(candidate, repo_root):
        file_path = candidate
        break          # <-- gated only the FIRST canonical path
```

A multi-file event whose first canonical candidate is **sentinel-granted**
therefore let every LATER canonical candidate **ride through ungated** — a
granted `.claude/team.md` edit could smuggle an unsigned
`.claude/frontend-team.md` edit in the same event. Convergent finding
(Claude + Codex lanes independently). Reachability confirmed: the `"path"`
list branch of `_extract_mcp_target_paths` yields one candidate per list
item, and any `mcp__*` tool name routes the event through the multi-candidate
scan. The Wave-1 repro drives `main()` end-to-end through the subprocess
harness and asserts the ungranted edit is allowed on HEAD.

**Finding C — fail-open resolve on a confirmed-canonical path (MED).** After
`_is_canonical` confirmed a path canonical, `decide()` resolved it
repo-relative for sentinel matching inside a `try/except` that returned
`_emit_allow()` on `ValueError`/`OSError` — **fail-OPEN on a
governance-protected path**, contradicting the PLAN-045 F-01-07 fail-CLOSED
contract. Round-1 debate (CF1) re-diagnosed C precisely: it is **not**
coupled to finding D as first triaged; it is a **dead `except`** in
same-process terms (the identical resolve inside `_is_canonical` would raise
first, returning non-canonical), reachable only via a same-process TOCTOU
between the two resolves.

## Decision

**A — most-restrictive-wins across ALL canonical candidates, emit-once.**
The Layer-A scan evaluates **every** candidate (up to a cap) and selects the
**offending** candidate (canonical AND ungranted) if any exists;
`decide()` is still invoked **exactly once** — on the offender (→ block
naming it) or, if none, the first canonical candidate (→ sentinel allow +
persona-coverage emit). This preserves emit-once (calling `decide()`
per-candidate would double-fire `_emit_persona_coverage_synthesized`) while
making ANY ungranted canonical candidate block the whole event. Specifics
(all from debate consensus):

- A **pure grant predicate** (`_candidate_is_granted`) classifies each
  candidate with **no side effects**; the once-per-event emit stays in
  `decide()`.
- `_find_sentinels` is **hoisted out of the loop** (O(N·M) → O(N+M) sentinel
  reads); the candidate count is **capped at 512** with a **fail-CLOSED
  over-cap block** (an event carrying more candidates than we will classify
  cannot be cleared — blocking beats truncating the scan and risking an
  unexamined offender).
- A per-candidate classification exception is **fail-CLOSED** (the candidate
  becomes the offender), never the historical `except: continue` that
  skipped past an unclassifiable candidate on a guarded event (VETO trigger
  V-A).
- The block reason **names the offending candidate**, not
  `candidate_paths[0]`.
- The **single-candidate fast path** (every Claude Code Edit/Write —
  `tool_name` not `mcp__*` and exactly one candidate) skips the scan
  entirely and is **byte-identical** to the pre-fix hook.

**C — fail-CLOSED on the confirmed-canonical resolve fault.** The
`except`/miss on a path `_is_canonical` already confirmed canonical now
returns `_emit_block(canonical_edit_hook_fault)`, matching F-01-07. Because
the branch is dead in same-process terms, this is **defense-in-depth at
zero brick risk** — it can only fire under a TOCTOU, and blocking is the
correct direction there. The non-canonical fail-OPEN contract (a hook bug
must not brick benign writes) is preserved: `decide()` still returns
`_emit_allow()` for any path `_is_canonical` classifies non-canonical,
BEFORE the fail-closed branch is reachable.

## Alternatives considered

- **A: cheaper "any ungranted canonical → short-circuit block" without
  iterating decide().** Rejected in favor of the pure-predicate scan +
  single decide(): the event candidate count is tiny, correctness
  (most-restrictive over the full set + emit-once + offender-naming) beats
  the micro-optimization, and the short-circuit still needed a per-candidate
  grant check anyway.
- **A: reorder candidates so a canonical-ungranted sorts first.** Rejected —
  a reorder-only fix is defeated by the both-orders order-independence repro
  (a fix must block in EVERY candidate order).
- **C: leave the dead except as-is (annotate-only).** Rejected: fail-closed
  is cheap, contract-correct (F-01-07), and the forced-branch test proves
  the defense; leaving a fail-OPEN branch on a governance path — even a dead
  one — is a latent regression surface.

## Consequences

- Multi-file MCP / `apply_patch` events are now gated on **every** canonical
  path, not just the first — closes the smuggle vector.
- A pathological event with > 512 candidate paths is blocked (fail-closed);
  no real apply_patch/MCP event approaches this.
- Single-candidate Edit/Write behavior — the overwhelming common case — is
  provably unchanged (byte-identity fuzzer + the `_multi` gate).
- Regression coverage: `.claude/hooks/tests/test_canonical_edit_council_findings.py`
  (A repros + SK4 anti-over-block + order-independence + cache-key
  regression; C forced-branch + behavioral fail-open property).

## Residual risk (pair-rail, accepted)

- **Near-cap all-granted GPG cost (security review low).** An event carrying
  up to 512 DISTINCT validly-signed canonical candidates triggers one
  `_sentinel_grants_path` (cached by `(sentinel, target_rel)`) per candidate;
  a sufficiently large all-granted event could approach the hook timeout and
  be killed → treated as allow. Bounded by the 512 cap and requires 512
  distinct validly-signed+scoped canonical paths in a single event —
  operationally absurd. The over-cap branch itself is fail-CLOSED. Accepted;
  a future mitigation (per-`rel` grant memoization within the scan, or a
  lower cap) is a follow-up, not a blocker.
- **Pre-cap materialization (codex review MED).** The candidate list is
  materialized from the already-parsed event before the cap check; the check
  is O(1) on that list and the expensive classification is bounded by the
  cap. No unbounded allocation beyond the event the harness already parsed.

## Pair-rail record

- Round 1 (codex + security): REJECT/VETO — the first draft's per-candidate
  classification-fault handler routed a raising candidate through `decide()`,
  which re-raised and the outer handler fail-OPENed the whole event (a
  symlink loop makes `Path.resolve()` raise `RuntimeError`, uncaught by the
  draft's `_repo_rels`). Fixed: `_repo_rels` is now TOTAL (`except Exception`)
  and the scan fail-CLOSES via `_forced_out` bypassing `decide()`;
  `_find_sentinels` is lazy + guarded (`_safe_sentinel_count`) so no path
  zero-emits. Regression tests added (symlink-loop both orders, over-cap,
  totality units, in-process sentinel-fault).

## References

- PLAN-045 F-01-07 (fail-CLOSED canonical contract); CLAUDE.md §4
  (fail-open on infra, fail-closed on input).
- Finding D (shared-predicate dual-anchor) is a separate decision — see
  **ADR-165**.
