---
id: SP-029
skill_slug: code-review-checklist
archetype: staff-code-reviewer
proposed_at: 2026-07-07T06:05:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: null
diff_size_removed: null
sha256_of_diff: null
sha256_of_staged: dc68ef6f7ffdee187385510c677559d0930ba381363ca79ae12bdd4302161425
claims_declared: false
status: draft
approved_by: null
applied_at: null
promoted_at: null
shadow_mode: true
proposal_type: adapt-merge-enrichment
after_wave_c: false
upstream_sources:
  - affaan-m/ecc@81af4076 skills/search-first/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/code-review-checklist/
---

# SP-029 — skill patch proposal (Wave G ADAPT merge)

**Target:** `.claude/skills/core/code-review-checklist/SKILL.md`
**Archetype:** staff-code-reviewer
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (1 upstream skill folded into an
existing catalog skill; no new skill file; catalog count unchanged)

## Rationale

Wave G materialized-merge **row 8**: fold `affaan-m/ecc@81af4076`
`skills/search-first/` (matrix quality **q4**) into `code-review-checklist` — an
anti-NIH **adopt / extend / build** decision matrix (search for existing
solutions before writing new code). Additive; staged file is 749 lines vs. the
675-line live skill (net +74 lines).

## ⚠ DELTA flag (from the materialized list — carry into review)

The matrix overlap for `search-first` is **`none`** — no existing skill was
auto-matched. Target `core/code-review-checklist` is assigned by the
**plan/debate**, not the matrix. Verified present on disk. The reviewer should
confirm the anti-NIH matrix fits the review-checklist frame (it gates "should this
code exist at all", a legitimate review dimension) and is not better homed in a
build/architecture skill.

## Provenance note

Clean-room ADAPT (upstream informed scope; prose original, zero ECC strings).
Provenance in the root `NOTICE` Wave G section
(`affaan-m/ecc@81af4076 skills/search-first/`, MIT) + `inspired_by:` frontmatter.
Carries upstream content → rides the **import gate** plus `/skill-review`.
`scan-injection.py` over all staged Wave G files (2026-07-07): no non-zero exit;
enforcing checks at the ceremony.

Rollback-safe: promote replaces exactly one file (SKILL.md).

## Patch source (staged tree, sha256-pinned)

`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/code-review-checklist/`:

| sha256 | file |
|---|---|
| `dc68ef6f7ffdee187385510c677559d0930ba381363ca79ae12bdd4302161425` | `SKILL.md` (merged, 749L) |

## Proposed diff (summary — the full diff is NOT embedded)

```
git diff --no-index .claude/skills/core/code-review-checklist/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/code-review-checklist/SKILL.md
```

## Landing mechanics (wake-up ceremony — /skill-review + import gate)

1. **Import gate + /skill-review** — `check-imported-skill.py --skill <staged
   SKILL.md> --notice NOTICE`, then human review ON TOP; resolve the DELTA flag
   (plan-directed target). Verify the sha256 pin.
2. **Approve (shadow apply)** — copy staged SKILL.md →
   `.claude/skills/core/code-review-checklist/SKILL.md.shadow.md`; set `status:
   shadow`, `applied_at`, `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c)** — live SKILL.md keeps serving;
   `skill-health.py` telemetry is the regression signal.
4. **Promote** — `mv SKILL.md.shadow.md SKILL.md` under the SKILL.md sentinel gate;
   replace `SP-NNN` in the merged changelog with `SP-029`; set `status: promoted`,
   `promoted_at`.

## Honest residuals

- DELTA (target is plan-directed, matrix overlap `none`) is recorded so the
  reviewer inherits the assignment rationale.
- `scan_injection_pass: true` = advisory exit-0, not a full injection audit.
- +74 lines paid per activation (not a Wave C pilot); acceptable for q4.
