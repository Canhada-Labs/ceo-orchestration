---
plan: PLAN-160
round: 1
created_at: 2026-07-17
round_verdict: PROCEED
critics: 3
verdicts: [ADJUST, ADJUST, ADJUST]
veto_exercised: false
consensus_adjustments: 8
---

# PLAN-160 round-1 consensus

Three critics (anonymized Critic-A/B/C; map in `anonymization-map.md`) all
returned **ADJUST** — no REJECT, no VETO exercised. The plan's spine
(verify-first, risky kernel edit LAST, fix only what reproduces, most-
restrictive-wins for A, E/F out of scope, sibling follow-ups kept out) is
endorsed by all three and is NOT changed. The adjustments below are
mechanical refinements to the fix SHAPES and the verification METHOD — none
sink the plan. Verdict: **PROCEED** (design-coherent; recorded per PLAN-134 W1
— this does NOT authorize shipping, only the verification cascade does).

## Consensus findings (2+ critics)

- **CF1 — the C↔D coupling in the plan is MIS-DIAGNOSED (Critic-A + Critic-B, load-bearing).**
  The plan says C is reachable only via D's divergence. WRONG: a relative-path /
  CWD-divergent input makes `_is_canonical` return **False** (D's mechanism) →
  `decide()` early-returns allow at L1132 → **never reaches C's `except` at
  L1137**. C and D are mutually exclusive on that input. C is a **provably dead
  `except`** absent a same-process **TOCTOU** (symlink-component race between the
  two identical pure resolves). Verifying C via the D path = a **vacuous "dead by
  accident" disposition**. → C's Wave-1 instrument is a **deadness property test
  (passes) + a white-box forced-branch test** (monkeypatch the resolve to raise,
  assert `block`/`canonical_edit_hook_fault`), NOT a failing-first repro.
- **CF2 — Fix-A must NOT call `decide()` per candidate (Critic-A + Critic-B).**
  `decide()` is not pure — the allow branch fires `_emit_persona_coverage_synthesized`
  (L1146). Iterating it N times amplifies audit/telemetry and skews persona
  coverage. → Factor a **pure grant predicate**; emit allow/block/coverage
  **once** per event.
- **CF3 — Fix-A loop `except Exception: continue` (L1373-74) is a 5th fail-open
  (Critic-A U1 + Critic-B U1).** A candidate that raises during classification is
  silently dropped from gating — same fail-open class as A, one layer down. →
  Fix-A must treat a per-candidate classification exception as **fail-CLOSED
  (block)** per CLAUDE.md §4.
- **CF4 — Fix-A block reason must name the OFFENDING candidate, not
  `candidate_paths[0]` (Critic-A + Critic-B).** `main()` pins `file_path =
  candidate_paths[0]` (L1358) for the veto emit (L1408+); blocking on
  candidate[k>0] while the audit names candidate[0] is a misleading forensic
  record on the gate's own block path.
- **CF5 — B is a characterization test that PASSES on HEAD, not a failing-first
  repro (Critic-A + Critic-B).** Both independently confirmed B is **not
  exploitable** (distinct `target_rel` per candidate → distinct cache key L838;
  `CEO_SENTINEL_UNLOCK` env bypass L891; process-per-invocation lifetime).
  Mandatory minimum = fix the false "`.asc`-covered" comment (a lying security
  comment is itself a hazard); key-hardening is optional defense-in-depth.

## Single-critic insights KEPT

- **SK1 (Critic-C, load-bearing UNSEEN) — Fix-D touches a SHARED predicate.**
  `_is_canonical` has THREE consumers, incl. the F5 `--is-canonical` oracle
  (`_cli_is_canonical` L1231) that landed in THIS file last ceremony and that the
  grok/codex pre-push gates depend on. Fix-D silently rewrites the oracle's
  documented anchoring invariant (L1258-60) → a new false comment (the finding-B
  drift class). → **D needs its own ADR** (widest blast radius; the plan omitted
  it), and the Wave-3 preflight must exercise the **`--is-canonical` CLI path**,
  not only the hook path.
- **SK2 (Critic-B U2) — the repro-suite can encode the bug as the oracle.**
  `_LayerABase._decide` (`test_check_canonical_edit_mcp.py:67-86`) re-implements
  the buggy loop **including the `break` at :81** — an A-repro built on it passes
  before AND after a fix (highest false-confidence vector). → The A-repro MUST
  drive `main()` end-to-end via the subprocess `_invoke` harness
  (`test_check_canonical_edit.py:30-56` + `CEO_SENTINEL_UNLOCK`); NEVER
  `_LayerABase._decide`.
- **SK3 (Critic-B Must-fix 2) — the A-repro needs disambiguating controls.**
  Assert single-candidate `{granted}`→allow AND `{ungranted}`→block, and BOTH
  orderings of `{granted, ungranted}`, so the multi-candidate allow is
  unambiguously the bypass (not a mis-configured override) and the fix is proven
  order-invariant.
- **SK4 (Critic-B U4 + Critic-A) — most-restrictive-wins must NOT become
  "one sentinel covers all".** `{grantedByS1, grantedByS2}` (each path its own
  sentinel) → **allow**. Missing test risks over-blocking legit multi-file
  ceremonies — a bricking regression invisible in a single-sentinel A-repro.
- **SK5 (Critic-A U3 + Critic-B R6) — Fix-A perf: hoist sentinel discovery.**
  Naive iterate re-runs `_find_sentinels` (glob + GPG) per candidate (cache
  misses on distinct `target_rel`) → O(N·M), can trip the perf-gate / timeout →
  infra fail-open. Cap candidate count; hoist `_find_sentinels` out of the loop.
- **SK6 (Critic-A D-refinement) — anchor BOTH repo_root AND cwd most-
  restrictively for D**, rather than betting on repo_root (a writing adapter that
  resolves relative against CWD would else be missed the other direction).
- **SK7 (Critic-C) — W2 and W3 are not separable.** `check_canonical_edit.py` is
  `_KERNEL_PATHS` → editable only under the W3 sentinel; W2 cannot "green a fix"
  on a file it cannot write. Re-frame: W2 = fix authored in staged tree +
  repros green in STAGED mode; W3 = the ceremony that lands it.
- **SK8 (Critic-A U4) — SKILL.md invisible-unicode guard keys on single
  `file_path` (L1421-22)**; a multi-file event with SKILL.md as candidate[k>0]
  evades it. Adjacent to A; record as a follow-on check (not necessarily this
  plan's Wave 2 — scope call in Wave 0 execution).

## Single-critic insights REJECTED / DEFERRED

- Critic-A U2 (`_extract_mcp_target_paths` extracted-set ⊇ write-set oracle) —
  **DEFERRED**: this is the finding-F residual (Layer-A parses only declared
  paths). Record as A's explicit residual in the plan; a full extracted⊇actual
  oracle is its own scoped effort, not PLAN-160.

## Plan adjustments applied (index — actual edits in the plan file)

1. Rewrite finding-C disposition: dead-`except` via TOCTOU, not D-coupling;
   instrument = deadness property test + forced-branch test (CF1).
2. Fix-A shape: pure predicate + emit-once (CF2); per-candidate fail-CLOSED
   (CF3); block names offending candidate (CF4); hoist `_find_sentinels` + cap
   candidates (SK5).
3. Split Wave-1 acceptance per finding-instrument: A/D = failing-first repro; B
   = characterization (passes HEAD); C = deadness property + forced-branch (CF5,
   CF1).
4. A-repro: pin to subprocess `_invoke` harness, forbid `_LayerABase._decide`;
   add single-candidate controls + both orderings (SK2, SK3).
5. Add SK4 all-independently-granted test (anti-over-block) + fix-A×B
   cross-candidate cache-leak regression.
6. D: own ADR + Wave-3 preflight exercises `--is-canonical` CLI oracle; anchor
   both repo_root and cwd; absolute-path regression twin (SK1, SK6).
7. Re-frame W2/W3 as staged-author + ceremony-land (not separable) (SK7).
8. Record F residual on A + SK8 SKILL.md multi-candidate note as Wave-0 scope
   items.

## Round verdict

**PROCEED.** All three ADJUST verdicts converge; adjustments are concrete and
mechanical (no design conflict, no tie to break). No round 2 needed. Plan moves
to `status: reviewed` after the adjustments land + the V2 Codex pair-rail cross-
model review runs on the uncommitted diff (per the Stop-hook advisory). Security
VETO is NOT exercised but its three triggers (V-A per-candidate fail-open, V-C
dead-except-left-allow, V-F-coupling residual-unrecorded) are folded into
Must-fix items 2/1/8 — Wave 2 lands green against them or the VETO attaches.
