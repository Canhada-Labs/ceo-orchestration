---
id: SP-024
skill_slug: frontend-performance-optimization
archetype: frontend-performance-engineer
proposed_at: 2026-07-07T06:00:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: null
diff_size_removed: null
sha256_of_diff: null
sha256_of_staged: 40caca77c266e0bcad0fb95a45276d2046ab1e4c695ea897b3866e6205333d96
claims_declared: false
status: draft
approved_by: null
applied_at: null
promoted_at: null
shadow_mode: true
proposal_type: adapt-merge-enrichment
after_wave_c: false
upstream_sources:
  - affaan-m/ecc@81af4076 skills/react-performance/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/frontend/frontend-performance-optimization/
---

# SP-024 — skill patch proposal (Wave G ADAPT merge)

**Target:** `.claude/skills/frontend/frontend-performance-optimization/SKILL.md`
**Archetype:** frontend-performance-engineer
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (1 upstream skill folded into
an existing catalog skill; no new skill file; catalog count unchanged)

## Rationale

Wave G materialized-merge **row 1** (`wave-g-materialized-list.md`): fold the
prioritized React performance ruleset from `affaan-m/ecc@81af4076`
`skills/react-performance/` (matrix quality **q5**) into our existing
`frontend-performance-optimization` skill. The upstream contributes 70+
severity-ordered React render/reconciliation/bundle rules that our skill did not
carry; the merge is **additive** — net-new sections + activation bullets folded
in house voice, no pre-existing content rewritten. Staged file is 357 lines vs.
the 228-line live skill (net +129 lines of merged material).

## Provenance note

Clean-room ADAPT: the upstream skill informed scope and rule ordering; the prose,
examples, and activation surface are original work in this framework's voice
(the marketing-style "strip upstream refs" discipline applies — zero ECC strings
in the merged body). Provenance is recorded two ways, per the Wave G contract:
(1) a row in the root `NOTICE` "PENDING CEREMONY LANDING — Wave G" section naming
`affaan-m/ecc@81af4076 skills/react-performance/` + MIT license; (2) an
`inspired_by:`-style frontmatter row in the merged SKILL.md.

Because the merge carries upstream-derived content, it rides the **import gate**
(`check-imported-skill.py`) IN ADDITION to `/skill-review` (plan §Wave G: "All
merges ride SP-NNN + `/skill-review` + import gate"). `scan-injection.py` was run
over every staged Wave G file (2026-07-07) with **no non-zero exit**; the
enforcing injection-corpus + provenance checks are the ceremony precondition
(Landing mechanics step 1), not an author-time attestation.

Rollback-safe: promote replaces exactly one file (SKILL.md); reverting restores
the prior SKILL.md. No references directory is added by this row.

## Patch source (staged tree, sha256-pinned)

Source of truth = the staged tree at
`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/frontend/frontend-performance-optimization/`:

| sha256 | file |
|---|---|
| `40caca77c266e0bcad0fb95a45276d2046ab1e4c695ea897b3866e6205333d96` | `SKILL.md` (merged, 357L) |

## Proposed diff (summary — the full diff is NOT embedded)

The merge is additive; regenerate and review the unified diff against the live
skill with:

```
git diff --no-index .claude/skills/frontend/frontend-performance-optimization/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-G/.claude/skills/frontend/frontend-performance-optimization/SKILL.md
```

Not embedded as a ```diff fence: `skill-patch-apply.py` refuses any diff with
removal lines by contract, and a whole-file replacement is not expressible as an
append-only patch. Landing is the Owner ceremony below.

## Landing mechanics (wake-up ceremony — /skill-review + import gate)

1. **Import gate + /skill-review.** Run
   `check-imported-skill.py --skill <staged SKILL.md> --notice NOTICE` (expect the
   provenance check to resolve against the Wave G NOTICE row) and the human
   `/skill-review` line-by-line pass ON TOP of the mechanical gate. Verify the
   sha256 pin above before anything else.
2. **Approve (shadow apply).** After review + detached GPG signature on this file
   (`.claude/skill-patch-signers.txt`), copy the staged SKILL.md to
   `.claude/skills/frontend/frontend-performance-optimization/SKILL.md.shadow.md`.
   Update frontmatter `status: shadow`, `applied_at`, `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c).** The live SKILL.md keeps serving
   activations for the soak window while the shadow sits beside it;
   `skill-health.py` telemetry (invocations + failure-proxy for
   `frontend-performance-optimization`) is the regression signal.
4. **Promote.** After the soak window, `mv SKILL.md.shadow.md SKILL.md` under the
   SKILL.md sentinel gate (`check_skill_patch_sentinel.py` requires this SP on
   disk), replace the `SP-NNN` placeholder in the merged changelog with `SP-024`,
   and set `status: promoted`, `promoted_at`.

## Honest residuals

- No diff-line counts are pinned in frontmatter (whole-file replacement, not an
  append patch); the reproduction command above is the review instrument.
- `scan_injection_pass: true` records an exit-0 run of the advisory scanner, not
  a full adversarial injection audit — the import gate at ceremony is enforcing.
- Activation-time cost rises with the merged content; `frontend-performance-optimization`
  is not a Wave C progressive-disclosure pilot, so the +129 lines are paid per
  activation. Acceptable for a q5 enrichment; revisit if it becomes a budget top-3.
