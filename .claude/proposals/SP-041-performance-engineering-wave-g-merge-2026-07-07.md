---
id: SP-041
skill_slug: performance-engineering
archetype: performance-engineer
proposed_at: 2026-07-07T07:35:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: 90
diff_size_removed: 0
sha256_of_diff: null
sha256_of_staged: 9373ddff5b1e5ccc23010ad8e64979b228ae85606b2d5b0d07554052a34c39f1
claims_declared: false
status: draft
approved_by: null
applied_at: null
promoted_at: null
shadow_mode: true
proposal_type: adapt-merge-enrichment
after_wave_c: false
upstream_sources:
  - affaan-m/ecc@81af4076 skills/benchmark-optimization-loop/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/performance-engineering/
---

# SP-041 — skill patch proposal (Wave G ADAPT merge)

**Target:** `.claude/skills/core/performance-engineering/SKILL.md`
**Archetype:** performance-engineer
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (1 upstream skill folded into
an existing catalog skill; no new skill file; catalog count unchanged)

## Rationale

Wave G materialized-merge **row 23** (`wave-g-materialized-list.md`): fold the
benchmark-optimization-loop discipline from `affaan-m/ecc@81af4076`
`skills/benchmark-optimization-loop/` into our existing `performance-engineering`
skill. The live skill has a `## Profiling Checklist` that covers making *one*
measured change ("change ONE thing, measure again"), but no discipline for
scaling that to "make it 20x faster" / "try 50 variants" without becoming an
unbounded, unfalsifiable search. The upstream contributes exactly that: a
required baseline (operation + correctness gate + metric + baseline + search
budget), a bounded measured loop, a variant ledger, recursive-search stopping
conditions, and a promotion gate. The merge is **additive**: one net-new
`## Bounded Optimization Loop` section (inserted after `## Profiling Checklist`,
before `## Anti-Patterns`), an `inspired_by:` frontmatter key (the live file had
none), and a `## Changelog` entry; no pre-existing content rewritten. Staged
file is 309 lines vs. the 219-line live skill (net +90 lines, 0 removed).

## Provenance note

Clean-room ADAPT: the upstream skill informed scope and structure; the prose is
original work in this framework's voice and is deliberately woven into our own
existing material — the loop ties back to the Fail-Fast Rule, the metric-choice
step cites our own "RSS is not heap; p50 is not p99" anti-pattern, and the
baseline step cites our "never trust warm-up logs" pitfall. The added loop is
runtime-agnostic on purpose, which also strengthens the skill's existing
Node.js-portability caveat. Zero upstream/ECC strings in the merged body.
Provenance is recorded two ways, per the Wave G contract: (1) a row in the root
`NOTICE` "PENDING CEREMONY LANDING — PLAN-153 Wave G" section naming
`affaan-m/ecc@81af4076 skills/benchmark-optimization-loop/` + MIT license; (2) an
`inspired_by:` frontmatter entry (`relationship: content_adaptation`) in the
merged SKILL.md.

Because the merge carries upstream-derived content, it rides the **import gate**
(`check-imported-skill.py`) IN ADDITION to `/skill-review` (plan §Wave G: "All
merges ride SP-NNN + `/skill-review` + import gate"). `scan-injection.py` was run
over the staged file (2026-07-07) with **exit 0, no injection patterns detected**;
the enforcing injection-corpus + provenance + attestation checks are the ceremony
precondition (Landing mechanics step 1), not an author-time attestation.

Rollback-safe: promote replaces exactly one file (SKILL.md); reverting restores
the prior SKILL.md. No references directory is added by this row.

## Patch source (staged tree, sha256-pinned)

Source of truth = the staged tree at
`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/performance-engineering/`:

| sha256 | file |
|---|---|
| `9373ddff5b1e5ccc23010ad8e64979b228ae85606b2d5b0d07554052a34c39f1` | `SKILL.md` (merged, 309L) |

## Proposed diff (summary — the full diff is NOT embedded)

The merge is additive (verified: `git diff --no-index` shows +90, 0 removals);
regenerate and review the unified diff against the live skill with:

```
git diff --no-index .claude/skills/core/performance-engineering/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/performance-engineering/SKILL.md
```

Not embedded as a ```diff fence: `skill-patch-apply.py` refuses any diff with
removal lines by contract, and landing is a whole-file replacement (`mv
SKILL.md.shadow.md SKILL.md`), not an append-only patch. Landing is the Owner
ceremony below.

## Landing mechanics (wake-up ceremony — /skill-review + import gate)

1. **Import gate + /skill-review.** Run
   `check-imported-skill.py --skill <staged SKILL.md> --notice NOTICE` (expect the
   provenance check to resolve against the Wave G NOTICE row) and the human
   `/skill-review` line-by-line pass ON TOP of the mechanical gate. Verify the
   sha256 pin above before anything else.
2. **Approve (shadow apply).** After review + detached GPG signature on this file
   (`.claude/skill-patch-signers.txt`), copy the staged SKILL.md to
   `.claude/skills/core/performance-engineering/SKILL.md.shadow.md`. Update
   frontmatter `status: shadow`, `applied_at`, `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c).** The live SKILL.md keeps serving
   activations for the soak window while the shadow sits beside it;
   `skill-health.py` telemetry (invocations + failure-proxy for
   `performance-engineering`) is the regression signal.
4. **Promote.** After the soak window, `mv SKILL.md.shadow.md SKILL.md` under the
   SKILL.md sentinel gate (`check_skill_patch_sentinel.py` requires this SP on
   disk), replace the `SP-041` placeholder in the merged changelog if needed, and
   set `status: promoted`, `promoted_at`.

## Honest residuals

- `diff_size_added: 90 / diff_size_removed: 0` are the verified insertion/removal
  counts vs. the live skill; `sha256_of_diff` stays null (no standalone diff
  artifact is pinned — the reproduction command above is the review instrument).
- `scan_injection_pass: true` records an exit-0 run of the advisory scanner, not
  a full adversarial injection audit — the import gate at ceremony is enforcing.
- The merged loop is intentionally runtime-agnostic; it does not add Node.js
  budgets or numbers, so the existing §Performance Budgets snapshots and the
  portability caveat are untouched and still apply.
