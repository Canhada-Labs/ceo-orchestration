---
id: ADR-120
title: PII core promotion — pii-data-flow + consent-lifecycle + dpo-reporting (renamed from ADR-111)
status: ACCEPTED
accepted_at: 2026-05-12
accepted_by: "Owner (post-Codex-Pair-Rail-iter-5-ACCEPT 2026-05-12; threads 019e1d07..019e1d22)"
proposed_at: 2026-05-12
proposed_by: CEO (PLAN-085 Wave 0; rename target per ADR-117 collision-rename policy)
original_id: ADR-111
original_decided: 2026-05-09
renamed_at: 2026-05-12
renamed_via: PLAN-085 Wave 0 (this ADR) + PLAN-085 Wave B.1 (file rename ceremony)
rename_driver: F-A-SEC-0001-7a82c1de (PLAN-084 R-006 audit-integrity P0)
related_plans: [PLAN-080, PLAN-082, PLAN-085]
related_adrs: [ADR-009, ADR-052, ADR-093, ADR-111, ADR-117]
supersedes:
  - rename_source: ADR-111-pii-core-promotion (ID 111; same scope; renamed via ADR-117 doctrine)
superseded_by: []
tags: [governance, pii, lgpd, skills-tier, canonical, renamed-from-adr-111]
authorization: PLAN-085 Wave 0 atomic ADR ceremony (`OWNER-CEREMONY-PLAN-085-WAVE-0.sh`); PLAN-085 Wave B.1 file-rename ceremony completes the migration
---

# ADR-120 — PII core promotion (renamed from ADR-111-pii-core-promotion)

## §1. Status

PROPOSED at draft time (PLAN-085 Wave 0). Flips to ACCEPTED at the
atomic Wave 0 ceremony commit. The **content of this ADR is identical
in substance** to the original `ADR-111-pii-core-promotion.md`
(decided 2026-05-09 via PLAN-080 Phase 0a Owner GPG sentinel
ceremony). The rename is mechanical only — the decision, drivers,
alternatives, acceptance criteria, and rollback plan are unchanged.

The original `ADR-111-pii-core-promotion.md` file is **scheduled for
removal in PLAN-085 Wave B.1** (`git rm` + cross-reference grep
update); between Wave 0 ceremony commit and Wave B.1 ceremony commit
there is a transient state where BOTH ADRs exist on disk under
different IDs but covering the same scope. This is intentional and
documented; Wave B.1 atomic commit closes the transient state.

## §2. Context

(Identical to original ADR-111-pii-core-promotion §2 — preserved
verbatim for rename-target completeness.)

The framework currently ships one PII baseline at `core/compliance-lgpd`.
Five PII-required domains (legal, healthcare, hr, finance-accounting,
real-estate-finance) inherit it; the V3 helper in
`.claude/scripts/validate-skill-frontmatter.py:469-478` enforces this
single-skill inherit rule via `_has_inherits_lgpd()`.

Three deeper PII skills exist but live in a different tier:

| Skill | Current path | Lines |
|---|---|---|
| `pii-data-flow` | `.claude/skills/domains/lgpd-heavy-saas/skills/pii-data-flow/SKILL.md` | 152 |
| `consent-lifecycle` | `.claude/skills/domains/lgpd-heavy-saas/skills/consent-lifecycle/SKILL.md` | 135 |
| `dpo-reporting` | `.claude/skills/domains/lgpd-heavy-saas/skills/dpo-reporting/SKILL.md` | 173 |

These three skills are tier-scoped to `domains/lgpd-heavy-saas`. As a
consequence, the 13 SKILL.md files across the 5 PII-required domains
each declare `inherits: core/compliance-lgpd` only — they cannot
mechanically inherit from a peer domain without manual duplication or
symlinks (both rejected; see §5).

**Driver finding:** Sec R-SEC-2 (PLAN-080 R1 debate, 3/3 REJECT)
surfaced this as a governance gap: "PII domains inherit
`core/compliance-lgpd`" was stated as correct — empirically false,
because the 3 richer PII skills are unreachable from outside
`lgpd-heavy-saas`. PLAN-080 R2 finding M2-Sec-2 + Codex MCP iter-1
finding M2-CDX-1 (5 root SKILL.md → 13 actual `skills/*/SKILL.md`)
refined the scope. This ADR formalises the governance decision.

## §3. Decision

(Identical to original ADR-111-pii-core-promotion §3 — preserved
verbatim.)

Promote the 3 skills from `domains/lgpd-heavy-saas/skills/` to `core/`
via the PLAN-080 Phase 0a ceremony:

1. **Create** `.claude/skills/core/pii-data-flow/SKILL.md` (copy of source; content unchanged).
2. **Create** `.claude/skills/core/consent-lifecycle/SKILL.md` (copy of source; content unchanged).
3. **Create** `.claude/skills/core/dpo-reporting/SKILL.md` (copy of source; content unchanged).
4. **Delete** the 3 `domains/lgpd-heavy-saas/skills/` shells (no double-source).
5. **Rewrite V3 helper** `_has_inherits_lgpd → _has_inherits_pii_core()` to validate a
   4-skill set: `core/compliance-lgpd` + `core/pii-data-flow` + `core/consent-lifecycle` +
   `core/dpo-reporting`.
6. **Update** all 13 PII-required domain `skills/*/SKILL.md` files: change
   `inherits: core/compliance-lgpd` to `inherits: [core/compliance-lgpd, core/pii-data-flow,
   core/consent-lifecycle, core/dpo-reporting]`.

Core skills carry no `tier:` declaration — the `core/` path is itself
the tier signal (existing convention across all 21 current core
skills).

## §4. Consequences

(Identical to original ADR-111-pii-core-promotion §4.)

**Positive:**

- 13 PII-required SKILL.md files gain mechanically-enforceable 4-skill
  PII inheritance; V3 helper emits ERROR (not WARN) on non-compliance.
- Removes the tier-scope dead-letter.
- Aligns with ADR-009 squad-bundle 5-artifact contract.
- `domains/lgpd-heavy-saas/team-personas.md` simplifies post-promotion.
- `edtech/skills/student-data-privacy/SKILL.md` edge-case corrected.

**Negative:**

- 3 NEW canonical paths added to `_CANONICAL_GUARDS`.
- 3 canonical paths deleted from `domains/lgpd-heavy-saas/skills/*/SKILL.md`.
- Phase 0a ceremony scope approximately 28 canonical paths.
- Adopters with `inherits: domain:lgpd-heavy-saas/pii-data-flow`
  references need a bump (current codebase grep: zero such references).

**Mechanical:**

- V3 helper rewrite at `.claude/scripts/validate-skill-frontmatter.py:469-478`.
- 48 NEW tests (25 helper-level + 13 real-file integration + 10
  `validate_v3()` branch coverage).
- 13 PII-domain SKILL.md `inherits:` scalar → YAML list form.

## §5. Alternatives considered

(Identical to original ADR-111-pii-core-promotion §5.)

**(a)** Symlinks `lgpd-heavy-saas/skills/` → `core/` for 5 PII domains
— REJECTED (`install.sh` template-copy path; symlink target signature
ambiguity).

**(b)** Keep in `lgpd-heavy-saas/` + cross-tier inherit override —
REJECTED (5× rule explosion; brittle at framework upgrade boundaries).

**(c)** Promote to a NEW tier `compliance/` — REJECTED (3 skills do not
justify a new directory partition).

**(d)** NO-OP — REJECTED (13× maintenance surface + drift risk).

**Decision: promote to existing `core/` tier.**

## §6. Acceptance criteria (PLAN-080 §4 Phase 0a)

(Identical to original ADR-111-pii-core-promotion §6.)

1. 3 PII skills present under `.claude/skills/core/` and mechanically inheritable.
2. `lgpd-heavy-saas/skills/` shells removed — no double-source.
3. `lgpd-heavy-saas/team-personas.md` updated post-promotion.
4. `edtech/skills/student-data-privacy/SKILL.md` lines 174-175 updated to `core/` paths.
5. All 13 current PII-required domain `skills/*/SKILL.md` files carry
   the 4-skill `inherits:` list.
6. 5 PII-required domains have placeholder `team-personas.md` citing new `core/` paths.
7. V3 helper rewrite live: `_has_inherits_pii_core()`.
8. 48 V3 tests GREEN.
9. **THIS ADR (ADR-120, renamed from ADR-111-pii-core-promotion)**
   status updated `PROPOSED → ACCEPTED` at PLAN-085 Wave 0 ceremony
   commit (the original ACCEPTED-status decision from 2026-05-09 is
   preserved in substance; the rename re-asserts ACCEPTED under the
   new ID).
10. `validate-governance.sh` PASS; `pytest` GREEN baseline preserved.

## §7. Rollback plan

(Identical to original ADR-111-pii-core-promotion §7. Recovery time:
approximately 10-15 min Owner-physical, single GPG ceremony reversal.)

| Artifact class | Rollback action |
|---|---|
| 3 NEW `core/` files | `git rm .claude/skills/core/{pii-data-flow,consent-lifecycle,dpo-reporting}/SKILL.md` |
| 3 deleted `lgpd-heavy-saas/skills/` files | `git checkout HEAD~1 -- <each path>` |
| 13 PII SKILL.md `inherits:` edits | `git checkout HEAD~1 -- <each path>` |
| V3 helper rewrite | `git checkout HEAD~1 -- .claude/scripts/validate-skill-frontmatter.py` |
| V3 test file | `git rm .claude/scripts/tests/test_validate_skill_v3_pii_core.py` |
| 5 placeholder `team-personas.md` | `git rm` per path |
| **ADR-120 (this file)** | `git rm .claude/adr/ADR-120-pii-core-promotion.md` + `git checkout HEAD~N -- .claude/adr/ADR-111-pii-core-promotion.md` (restore the original); update PLAN-085 frontmatter to remove ADR-120 from `adrs_proposed`. |

Post-rollback: run `validate-governance.sh` + `pytest` to confirm
baseline restored.

## §8. References

(Identical to original ADR-111-pii-core-promotion §8 plus rename-driver
references.)

- PLAN-080 §4 Phase 0a — original decision driver.
- PLAN-080 §6 Q3 — PII core promotion ship-vs-defer (recommendation: ship).
- PLAN-080 §5 sprint table — Phase 0a row.
- PLAN-080 §11 forensic trail — Codex MCP iter-1 M2-CDX-1 path-shape correction.
- PLAN-080 §13 revision log — v2.2 M2-CDX-1 closure entry.
- PLAN-074 §Wave 8 — 5 PII domain SKILL.md authoring.
- ADR-009 — squad-bundle 5-artifact contract.
- ADR-052 — VETO floor archetypes (Compliance Specialist).
- ADR-093 — canonical-guard moratorium retract; kernel-override discipline.
- **ADR-111 (the originally-numbered file `ADR-111-pii-core-promotion.md`)**
  — rename source; will be `git rm`'d in PLAN-085 Wave B.1.
- **ADR-117 (this plan)** — collision-rename policy doctrine that
  authorises this rename.
- PLAN-084 R-006 (F-A-SEC-0001-7a82c1de) — audit-driver finding that
  promoted the rename to TIER-1 roadmap.
- PLAN-085 Wave B.1 — mechanical rename ceremony.
- `.claude/scripts/validate-skill-frontmatter.py:469-478` — V3 helper.
- `.claude/skills/domains/lgpd-heavy-saas/skills/{consent-lifecycle,dpo-reporting,pii-data-flow}/SKILL.md` — 3 source files.

## §9. Forensic trail

(Identical to original ADR-111-pii-core-promotion §9 plus rename
forensics.)

- **Originally drafted:** 2026-05-09 S100 Phase 0a (PLAN-080 v2.5) under
  ID `ADR-111`.
- **R1 driver:** R-SEC-2 (CRITICAL — 3/3 REJECT) — PLAN-080 debate.
- **R2 driver:** M2-Sec-2 (PLAN-080 v2.1 must-fix — closed).
- **Original Codex MCP iter-1 (PLAN-080 v2.5 review):** M2-CDX-1
  path-shape correction (5 → 13 actual files).
- **Original Owner GPG sentinel:** PLAN-080 Phase 0a (commits per the
  Phase 0a ceremony — see PLAN-080 §11).
- **Collision detection:** PLAN-082 (concurrent) shipped a separate
  ADR-111 (`ADR-111-locked-corpus-governance.md`) on 2026-05-09;
  collision went undetected until PLAN-084 audit (2026-05-12).
- **PLAN-084 R-006 finding:** F-A-SEC-0001-7a82c1de (veto case C —
  audit-integrity P0).
- **Rename doctrine:** ADR-117 (collision-rename policy) ACCEPTED at
  PLAN-085 Wave 0 ceremony commit.
- **Rename ceremony:** PLAN-085 Wave B.1 atomic commit performs
  `git rm` on the original file + cross-reference update via grep
  across `.claude/`, `CLAUDE.md`, `MEMORY.md`, plans, skills, docs.

## §10. Rename history

This section is **mandatory** per ADR-117 §5 ("the renamed ADR's body
records the original ID, the rename-driver finding ID, and the
ceremony commit SHA"). Future readers consulting this ADR via wiki-link
or grep can establish provenance from this section alone.

| Field | Value |
|---|---|
| Original ID | ADR-111 (slug `pii-core-promotion`) |
| Original decided date | 2026-05-09 |
| Original ACCEPTED ceremony | PLAN-080 Phase 0a Owner GPG sentinel |
| Original ACCEPTED commit (post-PLAN-080 Phase 0a ship) | (PLAN-080 §11 — see git log for `ADR-111-pii-core-promotion.md` first commit) |
| Collision-trigger | PLAN-082 (concurrent) shipped a separate `ADR-111-locked-corpus-governance.md` on 2026-05-09 |
| Driver finding | F-A-SEC-0001-7a82c1de (PLAN-084 R-006, veto case C audit-integrity P0) |
| Resolution doctrine | ADR-117 (collision-rename policy) |
| Resolution mechanic | ADR-117 §5 Option A — rename later-ACCEPTED ADR (lexicographic tiebreaker: `pii-core-promotion` sorts after `locked-corpus-governance` → renames) |
| New ID | ADR-120 |
| New slug (unchanged) | `pii-core-promotion` |
| Rename ceremony 1 (this ADR's PROPOSED → ACCEPTED) | PLAN-085 Wave 0 atomic commit (SHA pending; recorded in PLAN-085 progress log §11) |
| Rename ceremony 2 (`git rm` of original + cross-ref updates) | PLAN-085 Wave B.1 atomic commit (SHA pending; recorded in PLAN-085 progress log §11) |

The **substantive content** of this ADR — Context, Decision, Decision
drivers, Alternatives, Acceptance criteria, Rollback, References,
Forensic trail — is byte-for-byte preserved from the original
`ADR-111-pii-core-promotion.md`, with the following mechanical
modifications:

1. Frontmatter: `id: ADR-111` → `id: ADR-120`; added `original_id`,
   `original_decided`, `renamed_at`, `renamed_via`, `rename_driver`,
   `tags: [..., renamed-from-adr-111]`; `related_adrs:` augmented with
   ADR-111 (rename source) + ADR-117 (rename doctrine).
2. Title: `# ADR-111 — PII core promotion` → `# ADR-120 — PII core
   promotion (renamed from ADR-111-pii-core-promotion)`.
3. Acceptance criterion §6.9 — wording updated to reflect that the
   ACCEPTED status now re-anchors at the PLAN-085 Wave 0 ceremony
   commit (the original 2026-05-09 ACCEPTED decision remains valid
   in substance).
4. Rollback plan §7 — added a row for ADR-120 rollback (git rm + restore
   original ADR-111 from prior commit; update PLAN-085 frontmatter).
5. References §8 — added ADR-111 (source), ADR-117 (doctrine),
   PLAN-084 R-006, PLAN-085 Wave B.1 entries.
6. Forensic trail §9 — appended collision-detection + rename ceremony
   entries.
7. THIS §10 Rename history section — net-new, ADR-117 §5 mandate.

## §11. Enforcement commit

n/a (documentation-only ADR). The runtime acceptance moment is the
PLAN-085 Wave 0 ceremony commit; the file-rename mechanical execution
is the PLAN-085 Wave B.1 ceremony commit. Both SHAs recorded in
PLAN-085 progress log §11.
