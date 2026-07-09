---
id: SP-022
skill_slug: testing-strategy
archetype: qa-architect
proposed_at: 2026-07-07T05:30:00Z
source_lessons:
  - plan-153-wave-c-progressive-disclosure-pilot
scan_injection_pass: true
diff_size_added: 44
diff_size_removed: 924
sha256_of_diff: 4a2bbb3fe074603ca28826a8ce50cb3fc1531ec51b71444b5280a58a1fd5d520
claims_declared: false
status: shadow
approved_by: AE9B236FDAF0462874060C6BCFCFACF00335DC74
applied_at: 2026-07-08T22:48:10Z
promoted_at: null
shadow_mode: true
proposal_type: progressive-disclosure-restructure
patch_source: .claude/plans/PLAN-153/staged/wave-C/.claude/skills/core/testing-strategy/
---

# SP-022 — skill patch proposal

**Target:** `.claude/skills/core/testing-strategy/SKILL.md`
**Archetype:** qa-architect
**Kind:** PLAN-153 Wave C progressive-disclosure pilot #1 (staged-tree
restructure — slim loader SKILL.md + `references/*.md`, 100% content
preserved)

## Rationale

PLAN-153 Wave C item 1 designated `testing-strategy` as progressive-
disclosure pilot #1. `context-budget.py` (Wave C telemetry tool) ranks it
savings opportunity #1: 1026 lines, ~8193 est tokens always paid per
activation; the staged loader is 144 lines (~1150 est tokens) — potential
saving ~8043 est tokens per activation. The restructure extracts the ten
topic bodies into `references/*.md` and leaves a loader SKILL.md whose
frontmatter (`name`, `description`, `activation_triggers`, smart-loading
fields) is UNCHANGED, so catalog discovery and machine triggers are
unaffected; each section is replaced by a pointer table entry telling the
agent which reference file to Read on demand.

**Content preservation proof (mechanical, run 2026-07-07):** all 44
`##`/`###` headings of the live SKILL.md appear verbatim in the staged
tree; all 574 normalized non-heading content lines of the live SKILL.md
appear verbatim in the staged tree (0 lost). Zero content loss — the
saving is activation-time only.

## Provenance note

Hand-authored under PLAN-153 Wave C (ratified debate; staging discipline
per plan §Wave C). `skill-patch-propose.py` was NOT usable as generator:
its conservative appender only emits append-only diffs (cap 200 lines,
`.claude/scripts/skill-patch-propose.py:82` `_DIFF_SIZE_CAP`), and this
restructure is 42+/924− plus 10 NEW `references/*.md` files. The moved
content contains fenced code blocks inherited VERBATIM from the live
SKILL.md (the `CEO_SKILL_PATCH_ALLOW_CODE=1` human-review route applies —
no new executable content is introduced; every fence already exists in
the promoted live skill). All 11 staged files pass `scan-injection.py`
(clean, 2026-07-07) and the propose-time Unicode/bidi/homoglyph checks.

Rollback-safe: promote replaces exactly one file (SKILL.md) and adds
inert `references/*.md`; reverting restores the prior SKILL.md and
removes the references directory. No other file is touched.

## Patch source (staged tree, sha256-pinned)

Source of truth = the staged tree at
`.claude/plans/PLAN-153/staged/wave-C/.claude/skills/core/testing-strategy/`:

| sha256 | file |
|---|---|
| `a915dc36785cbfe8154c36689142f06991cae936e52c82f27d188a00874640fd` | `SKILL.md` (loader, 144L) |
| `9317903142429fb868fb5649ad4e1de351bf131609c5ba9ee7e618f5465abecb` | `references/chaos-testing.md` |
| `0adbaff2d50b2a4b49a7897fb4f74c746321ac9339ecf6795bb686a8c05b4758` | `references/ci-integration.md` |
| `2ff46706e4b0cb96aaa72ffe4d292f323ab28840ba13edbc0c413e2ed08e7780` | `references/database-testing.md` |
| `2a9458f3a25dfe1a19d54b192146be79d748d6e22a06265dba0f521d3df857c1` | `references/domain-math-and-property-based.md` |
| `46e47b020e0b3923fde3ecb0ec8405c24e3e615597bc02b0d0c93c74f68ed475` | `references/e2e-multiprocess.md` |
| `0a54c5cfc814866cbdea86e9ddfe70cd88f539bf6bcf1a649f13ab902609ee43` | `references/integration-testing.md` |
| `bb707cc3a2f629ff2cdb55b9178b829029b7ed539ffb9324da565920bc999731` | `references/module-test-matrices.md` |
| `e23f7fc1916fb9213a5e68a847f1be975d7460f7bc663ed3b27394ef4a91684d` | `references/route-testing.md` |
| `5ba1dc73581bc188754f948829c6bcfce3826d8e7510a21d4c0bd28b15262890` | `references/test-quality-and-mutation.md` |
| `267bb63abbf34267dd83230f75aece4302d44f7e7232cdeb909fb80f0392bcc9` | `references/vitest-patterns.md` |

## Proposed diff (summary — the full diff is NOT embedded)

The SKILL.md unified diff is 44 added / 924 removed lines; regenerate and
verify against `sha256_of_diff` in the frontmatter with:

```
git diff --no-index .claude/skills/core/testing-strategy/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-C/.claude/skills/core/testing-strategy/SKILL.md \
  > /tmp/sp-022.patch && shasum -a 256 /tmp/sp-022.patch
```

It is deliberately not embedded as a ```diff fence: `skill-patch-apply.py`
refuses any diff containing removal lines by contract
(`.claude/scripts/skill-patch-apply.py:461-464` returns None on a `-`
line), so an embedded fence would invite an apply path that structurally
cannot succeed. See Landing mechanics.

## Landing mechanics (wake-up ceremony — /skill-review governance)

This proposal rides `/skill-review` for governance (GPG-signed approval
against `.claude/skill-patch-signers.txt`, 7-day soak semantics, audit
events) but the mechanical apply is an Owner ceremony because the
automated apply path cannot express a restructure:

1. **Approve (shadow apply):** after `/skill-review` review + detached
   GPG signature on this file, the Owner copies the staged loader to
   `.claude/skills/core/testing-strategy/SKILL.md.shadow.md` (overwriting
   the stale SP-015-era shadow currently on disk) and lands the 10
   `references/*.md` files directly (they are NOT canonical-guarded —
   `check_canonical_edit.py:117-122` guards only `SKILL.md` — and are
   inert until the loader points at them). Verify every sha256 pin above
   before copying. Update frontmatter `status: shadow`, `applied_at`,
   `approved_by`.
2. **Soak — parallel-shadow, NOT skip (OQ3=c):** these pilots restructure
   EXISTING promoted skills, so the ratified soak posture is
   parallel-shadow: live SKILL.md keeps serving activations for the soak
   window while the shadow file exists side by side; `skill-health.py`
   telemetry over the window is the regression signal (invocations +
   failure-proxy for `testing-strategy` must not degrade).
3. **Promote:** after the soak window, `mv SKILL.md.shadow.md SKILL.md`
   under the SKILL.md sentinel gate (`check_skill_patch_sentinel.py`
   requires this SP on disk) and update frontmatter `status: promoted`,
   `promoted_at`.

## Honest residuals

- The content-preservation proof is normalized-line containment (headings
  + stripped non-heading lines), not byte identity; ordering inside
  reference files was reviewed by the Wave C author, not machine-proven.
- Est-token figures are the 4-chars-per-token heuristic of
  `context-budget.py`, not the Anthropic tokenizer.
- Activation-time saving is realized only if agents actually Read
  references on demand; `check_skill_reference_read.py` +
  `skill-health.py` discovery telemetry are the post-promote check.
