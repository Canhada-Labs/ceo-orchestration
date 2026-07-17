---
plan: PLAN-160
round: 1
archetype: vp-engineering
role: architecture-coherence critic
verdict: ADJUST
created_at: 2026-07-17
---

# PLAN-160 round-1 critique — VP Engineering (architecture coherence)

> Scope of this review: structure, sequencing, scope discipline, and design-fit
> of the four fixes — not the security merits (that is the security-VETO seat).
> All file/line cites are `.claude/hooks/check_canonical_edit.py` unless noted.
> Note: the `architecture-decisions` SKILL.md read was blocked mid-session by the
> anti-CEO-overhead predicate; I applied the framework's own ADR convention
> (CLAUDE.md §4: an ADR for every cross-cutting choice that changes a documented
> contract) rather than the skill's fuller checklist. The judgment below stands
> on the code I did read (all four cited sites + the Layer-A comment + the F5
> `--is-canonical` oracle).

## Verdict

**ADJUST.** The plan's spine is architecturally correct — verify-first, kernel
edit last, most-restrictive-wins for A, C+D co-verified. I found no REJECT-level
flaw. But three coherence gaps must be closed before Wave 2, and one is a genuine
UNSEEN with cross-consumer blast radius the plan does not mention:

1. **Fix-D changes a SHARED predicate (`_is_canonical`) with three consumers**,
   one of which (the F5 `--is-canonical` oracle) documents an anchoring
   invariant Fix-D silently rewrites — yet the plan calls for an ADR on A and C
   but **not D**. D has the widest blast radius of the four. (Must-fix #1, Unseen.)
2. **W2 "FIX" and W3 "ceremony" are not cleanly separable** — the file is
   `_KERNEL_PATHS`, so it cannot be edited outside the sentinel; W2 cannot
   independently green a fix on a file it is not allowed to write. The plan's
   linear wave list obscures where the edit legally happens. (Must-fix #2.)
3. **Fix-A re-runs `_find_sentinels` per candidate** — the plan's OQ1 dismisses
   perf citing "tiny event count," conflating event-count with candidate-count;
   each canonical candidate triggers a fresh filesystem sentinel scan. (Must-fix
   #3 — cheap refactor.)

## Summary

The plan verifies then fixes four council findings (A/C/B/D) in one kernel file,
landing via one GPG ceremony. Wave sequencing (W0 debate → W1 failing-first repro
→ W2 fix-confirmed-only → W3 kernel ceremony → W4 closeout) is textbook risk
posture: the highest-blast-radius act (touching a live security gate) is last and
gated on reproducible defects, with a preflight behavioral oracle that fails
unless the staged bytes carry the A-fix (the "never sign a claim the bytes don't
hold" lesson, plan L112-113). Bundling A/C/D is coherent — they live in one
decision path (`main()` → `decide()` → `_is_canonical`) and C+D are causally
coupled through the same double-resolve seam, so splitting them would mean three
kernel ceremonies on one file (higher aggregate risk). Fix-A's placement in
`main()` and its most-restrictive-wins shape fit the existing Layer-A/`decide()`
separation and are a real robustness gain (order-independence). The gaps are
about the *edges* of that spine, not the spine.

## Risks

- **R1 (HIGH) — shared-predicate drift.** `_is_canonical` (L683) is called by
  the edit-time guard (`decide()` L1131, `main()` L1370/L1390) AND by the F5
  oracle `_cli_is_canonical` (L1281), which shell pre-push review gates depend
  on. Fix-D changes how relative paths anchor. The oracle docstring L1258-1260
  asserts "oracle and hook can never disagree on anchoring" and L1264-1266 treats
  "returns False for paths outside the repo root" as the oracle's *own semantics*.
  Fix-D alters what "outside the repo root" means for a relative path → it either
  (a) breaks that documented invariant if applied to only one resolve site, or
  (b) is correct but leaves the docstring a NEW false comment — the exact
  finding-B drift class the plan is here to fix.
- **R2 (MED) — fixing D could WIDEN C.** C is reachable only when the two
  resolves diverge — `_is_canonical`'s resolve at L691 vs `decide()`'s at L1137.
  If Fix-D re-anchors L691 but not L1137, the two resolve sites diverge *more*,
  enlarging C's window rather than closing it. C and D must be co-designed to use
  identical anchoring at every resolve site, or the fix is self-defeating.
- **R3 (MED) — W2 cannot green what it cannot edit.** Wave 2's check ("repros
  now PASS; full `.claude/hooks/tests/` green") requires the fix bytes to be
  live, but `check_canonical_edit.py` is canonical-guarded; the only legal way to
  apply the edit is under the W3 sentinel (STAGED mode). So W2's green is
  actually produced by W3's dry-run. The wave boundary is fictional unless the
  plan states the fix is developed against a scratch clone and validated inside
  the ceremony envelope (ties to the S274 staged/-gitignored lesson).
- **R4 (LOW) — Fix-A per-candidate exception semantics unspecified.** The current
  single `decide()` call is wrapped by the fail-CLOSED-on-canonical handler
  (L1376-1406). Iterating `decide()` over N candidates leaves undefined what a
  *fault* on candidate k does to the whole event. Silent per-candidate `continue`
  would re-introduce a bypass under the fix meant to close one.
- **R5 (LOW) — W4 re-audit blocked on an out-of-scope plan.** The optional
  `/council` re-run (L119-121) depends on the sibling grok-arg-contract fix to
  reach 3-lane. As written it reads like an actionable checkbox in THIS plan; it
  is a deferral.

## Must-fix

1. **Add an ADR for Fix-D, and update the oracle contract note in the same
   patch.** D changes a shared predicate with a documented invariant
   (L1258-1260) and three consumers; it warrants an ADR at least as much as C
   does — the plan currently omits it (plan L114, L154 name only A and C). The
   Wave-3 behavioral preflight oracle MUST exercise the `--is-canonical` CLI path
   (L1231) in addition to the hook path, or a Fix-D regression to the pre-push
   review gates ships unverified. And Fix-D must rewrite the L1258-1266 docstring
   to match new anchoring — do not fix finding B's false comment while minting a
   new one.
2. **State where the kernel edit legally happens.** Make explicit that W2
   authors + repro-greens the fix against a scratch clone (or the ceremony's
   STAGED working tree), and that the file's only compliant mutation is under the
   W3 sentinel. Otherwise W2/W3 read as two independent waves when they are one
   envelope. Reference the tracked-hash-manifest requirement for staged inputs.
3. **Co-anchor C and D at a single resolve site.** Specify that Fix-C and Fix-D
   change *every* resolve of the target (L691 in `_is_canonical`, L1137 in
   `decide()`) to the identical `repo_root`-anchored form — ideally by resolving
   once and threading the result, so there is no second resolve to diverge (see
   Nice-to-have #1). Anchoring only one site can make C worse (R2).
4. **Define Fix-A's per-candidate fault policy.** Specify: a *block* on any
   canonical candidate blocks the whole event; a *fault* (`decide()` raises) on
   any *canonical* candidate fails CLOSED for the whole event, matching the
   existing L1379-1384 contract — never a bare `continue` that drops a candidate.

## Nice-to-have

- **Single-resolve refactor closes C structurally (stronger than fail-closing a
  dead `except`).** `decide()` today resolves the path twice — `_is_canonical`
  at L1131→L691, then again at L1137. That double-resolve IS C's divergence
  surface. Have `_is_canonical` return the computed rel (or have `decide()` reuse
  one resolve), and C disappears by construction — no second resolve, nothing to
  diverge, no `except` to argue about. This is a cleaner fix than the proposal's
  "make the L1138 except fail-closed" (which leaves a provably-dead branch).
- **Hoist sentinel discovery out of the Fix-A loop.** Refactor `decide()` to
  accept an optional precomputed sentinel list so `main()` calls
  `_find_sentinels(repo_root)` (L1141) ONCE per event, not once per canonical
  candidate. Keeps most-restrictive-wins O(candidates) in cheap glob checks
  rather than O(candidates) filesystem scans.
- **Gate B's inclusion on staying comment-only.** If Wave 1 confirms B is
  comment-precision (the near-certain outcome given module-scope cache +
  fresh-subprocess-per-invocation, L798-799), keep it as a trivial rider in this
  ceremony. If Wave 1 somehow finds a same-process re-entrancy window requiring a
  *cache-key change*, that is a different risk class (cache correctness, not
  decision-path) and should split to its own plan rather than ride the kernel
  ceremony.

## Unseen

**The F5 `--is-canonical` oracle that landed in this same file last ceremony
(PLAN-156-FOLLOWUP) is a hidden Fix-D consumer, and its correctness argument
inverts under the fix.** `_cli_is_canonical` (L1231-1288) is the
single-source-of-truth classifier the grok/codex pre-push review gates call
(L1235-1238) so they don't re-implement the guard glob in bash. It shares
`_is_canonical` (L1281). Today, a relative canonical path with `CWD !=
CLAUDE_PROJECT_DIR` resolves outside repo_root → `_is_canonical` returns False →
oracle reports `0` (non-canonical) → the pre-push gate does NOT force review.
That is the same false-negative as finding D, but on the *review-gating*
surface, not the edit-gating surface. So D is not one bypass — it is two, in two
consumers, from one predicate. The good news: Fix-D closes BOTH consistently, and
the oracle already treats over-triggering as its safe direction (L1261-1263), so
the review-gate side of Fix-D is strictly safe. The trap: (a) the plan scopes D
as a localized `main()`/`decide()` concern and never mentions the oracle, so the
Wave-3 oracle-must-carry-the-fix preflight will only assert the hook path unless
told otherwise; and (b) the oracle's own docstring becomes false the instant
Fix-D lands. Both are captured in Must-fix #1. Secondary unseen: Fix-A makes the
multi-candidate gate *order-independent* (currently the first-canonical `break`
at L1372 is order-dependent) — that is a correctness property worth asserting
directly in the A regression test (feed the SAME candidate set in both orders,
assert identical block), because an order-dependent security gate is a latent
non-determinism the current tests would not catch.

## What I would NOT change

- **Wave order.** Kernel edit last, gated on W1 repros, with a bytes-carry-the-fix
  preflight oracle (L110-113) — correct and non-negotiable. Do not compress.
- **Fix-A in `main()`, not the MCP adapter.** Candidate enumeration
  (`apply_patch_paths` L1348, `_extract_mcp_target_paths` L359) already lives in
  `main()`; `decide()` is the pure per-path decision. Multi-candidate *policy* is
  a Layer-A concern, and non-MCP multi-file events (`apply_patch_paths` under any
  tool, L1347-1350) also need it — pushing it into the adapter would wrong-place
  it and miss the non-MCP path. Keep it where the plan puts it.
- **Most-restrictive-wins over the cheaper short-circuit (OQ1).** It composes
  monotonically with the sentinel-grant model (each canonical candidate checked
  independently; any ungranted → block) and it makes the code finally match its
  own comment (L1362 already claims "most restrictive policy" — the code was the
  liar). Endorse the CEO default.
- **Bundling A/C/D in one plan + one ceremony.** One decision path, one test
  file, one kernel touch. Splitting would multiply kernel ceremonies on the same
  file — more aggregate risk, not less.
- **E/F excluded; siblings (grok arg-contract, perf-gate D3) kept out.** Correct
  scope discipline: E is a documented infra fail-open (CLAUDE.md §4), F is a
  Layer-A/B boundary note (L341-343), and recording both as reviewed/no-action in
  W0 (plan L70-71) forecloses re-litigation. The siblings are real but orthogonal
  (a cache/egress concern and a CI-timing concern) — noting them so they are not
  lost (plan L134-147) is exactly right.
