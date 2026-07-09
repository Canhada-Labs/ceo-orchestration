---
id: SP-036
skill_slug: design-system-and-components
archetype: design-technologist
proposed_at: 2026-07-07T06:12:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: 88
diff_size_removed: 0
sha256_of_diff: 4dac22e30d0a648e8b1d273681398e0374f7aec0edbe2de272c9b49a13c54034
sha256_of_staged: c7c38baddd971eb5e78308aa971a7d33ae034c6f0bc9b6d7e6392e9466322d88
claims_declared: false
status: promoted
approved_by: AE9B236FDAF0462874060C6BCFCFACF00335DC74
applied_at: 2026-07-09T11:33:29Z
promoted_at: 2026-07-09T15:49:44Z
shadow_mode: false
proposal_type: adapt-merge-enrichment
after_wave_c: false
cross_wave_flag: true
upstream_sources:
  - affaan-m/ecc@81af4076 skills/motion-foundations/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/frontend/design-system-and-components/
---

# SP-036 — skill patch proposal (Wave G ADAPT merge)

**Target:** `.claude/skills/frontend/design-system-and-components/SKILL.md`
**Archetype:** design-technologist
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (1 upstream skill folded into an
existing catalog skill + 1 net-new reference; no new skill file; catalog count
unchanged)

## Rationale

Wave G materialized-merge **row 20** (the second of the two clean q5 `+7`
selections): fold `affaan-m/ecc@81af4076` `skills/motion-foundations/` (matrix
quality **q5**) into `design-system-and-components` — the motion base (duration/
easing tokens, spring config, reduced-motion a11y, SSR-safety) aligned to this
skill's existing token governance. Lands as `reference/motion-tokens.md` + loader
pointer. Additive; staged loader is 234 lines vs. the 155-line live skill (net +79
lines) plus a 137-line reference.

## ⚠ CROSS-WAVE flag (from the materialized list — reconciliation rule)

The matrix verdict for `motion-foundations` is **ADAPT** (merge here), but
PLAN-153 Wave D **batch-2** prose groups a "motion trio" (foundations / patterns /
advanced) as candidate *new* skills. The matrix is ground truth
(patterns=ADOPT, advanced=ADOPT, **foundations=ADAPT**, ui=SKIP), so foundations
belongs in Wave G. **Reconciliation rule (carry into review):** if Wave D pulls
`motion-foundations` forward as a *new* skill, **drop this SP (SP-036)** and
promote the next eligible distinct-target q4 (`customer-billing-ops →
core/monetization-and-billing`), updating the 72/25 deferred arithmetic. Confirm
Wave D batch-2 did NOT pull it forward before landing this SP.

## Provenance note

Clean-room ADAPT (upstream informed scope; prose original, zero ECC strings).
Provenance in the root `NOTICE` Wave G section
(`affaan-m/ecc@81af4076 skills/motion-foundations/`, MIT) + `inspired_by:`
frontmatter. Carries upstream content → rides the **import gate** plus
`/skill-review`. `scan-injection.py` over all staged Wave G files (2026-07-07):
no non-zero exit; enforcing checks at the ceremony.

Rollback-safe: promote replaces exactly one file (SKILL.md) and adds one inert
`reference/motion-tokens.md`; reverting restores the prior SKILL.md and removes
the reference.

## Patch source (staged tree, sha256-pinned)

`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/frontend/design-system-and-components/`:

| sha256 | file |
|---|---|
| `76e69cd5e2175c53eb36b1da9a8e8fd56e8afa80026356faa489da59c4661013` | `SKILL.md` (merged loader, 243L) |
| `5b8d86d7ca34dd29e727c37d2ab44c0ea9d0f6c2cf45a2b3ff1e7894a4a417e6` | `reference/motion-tokens.md` (243L, net-new) |

Note: this skill uses a singular `reference/` directory (not `references/`) —
match the live layout when landing.

## Proposed diff (summary — the full diff is NOT embedded)

```
git diff --no-index .claude/skills/frontend/design-system-and-components/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-G/.claude/skills/frontend/design-system-and-components/SKILL.md
```

## Landing mechanics (wake-up ceremony — /skill-review + import gate)

1. **Precondition:** confirm the CROSS-WAVE reconciliation (Wave D batch-2 did not
   promote `motion-foundations` as a new skill). If it did, drop this SP.
2. **Import gate + /skill-review** — `check-imported-skill.py --skill <staged
   SKILL.md> --notice NOTICE`, then human review ON TOP. Verify both sha256 pins.
3. **Approve (shadow apply)** — copy staged SKILL.md →
   `.../design-system-and-components/SKILL.md.shadow.md`; land
   `reference/motion-tokens.md` directly (inert until the loader points at it). Set
   `status: shadow`, `applied_at`, `approved_by`.
4. **Soak — parallel-shadow, NOT skip (OQ3=c)** — live SKILL.md keeps serving;
   `skill-health.py` telemetry is the regression signal.
5. **Promote** — `mv SKILL.md.shadow.md SKILL.md` under the SKILL.md sentinel gate;
   replace `SP-NNN` in the merged changelog with `SP-036`; set `status: promoted`,
   `promoted_at`.

## Honest residuals

- CROSS-WAVE coupling with Wave D batch-2 is a real ordering hazard, recorded as a
  hard reconciliation rule rather than an assumption.
- `scan_injection_pass: true` = advisory exit-0, not a full injection audit.
- The reference is activation-time free until its pointer is read on demand.


> **Contagens finais S262 (pós-review, autoritativas):** staged = 243 linhas; diff vs live = +88/−0; frontmatter diff_size_added/removed sincronizados. Rail de integridade = pin sha256_of_staged, re-pinado após cada fix.

> **Soak waiver S263 (2026-07-09):** 7-day parallel-shadow window waived by explicit Owner decision (single-user dogfood; pre-authorized skip semantics of --promote --force-recover). SP-026/SP-034 (AFTER-C) excluded — they keep the full soak.
