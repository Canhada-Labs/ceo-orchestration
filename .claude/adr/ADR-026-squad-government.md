# ADR-026: Squad government + Agent Architect dogfood v2 outcome

## Status: ACCEPTED (2026-04-14)

## Context

PLAN-010 Phase 7b authorized the creation of a fourth domain squad
(`government`) covering federal / state / local public-sector software,
operating under three statutorily-distinct regimes:

1. **Section 508 + WCAG 2.1 AA** — procurement-block surface
   (failing Section 508 disqualifies a vendor bid in federal
   procurement and increasingly state/local).
2. **FOIA + state sunshine laws** — records lifecycle, retention,
   redaction audit trails, SLA clock discipline, requester-identity
   confidentiality.
3. **Public procurement integrity (FAR / DFARS + state analogs)** —
   bid confidentiality until award, contractor debarment vetting,
   conflict-of-interest declarations, award-rationale documentation.

This ADR documents two things, mirroring ADR-025 (edtech, Phase 7a):

1. The squad bundle itself.
2. The **second** dogfood outcome of the Agent Architect meta-agent.
   ADR-025 captured the first run (edtech). PLAN-010 debate K7 set
   a ≤1-day-per-squad time budget; the second run is the check on
   whether the methodology produces compounding returns or
   per-squad-flat effort.

## Decision Drivers

- **Validate methodology repeatability.** A first run looking good
  can be beginner's luck or brief-quality luck. A second run on a
  distinct domain is the credibility check.
- **Keep VETO discipline tight.** Three regulatory regimes → three
  VETO holders, each statutorily distinct. Consolidating them
  (e.g. one "Government Compliance Engineer") would blur three
  different audit lenses into one reviewer fatigue surface.
- **Make the squad installable today.** `install.sh --profile
  core,frontend,government` must work without code changes
  (per ADR-009 §installation).
- **Address Sprint 11 ADR-025 open questions opportunistically.** The
  government squad inherits two of ADR-025's ambiguities (VETO
  declaration style; reference-squad vs install-squad dependency).
  Using the same pattern here keeps the drift small until Sprint 11
  formalizes.

## Decision

**Adopt the government squad** with the following canonical artifacts:

```
.claude/skills/domains/government/
├── team-personas.md               # 5 personas; 3 VETO holders (508, FOIA, procurement)
├── pitfalls.yaml                  # 21 pitfalls (GOV-001..GOV-021)
├── task-chains.yaml               # 2 chains (publish-rfp, foia-respond)
├── examples/PLAN-EXAMPLE.md       # citizen-services portal example
└── skills/
    ├── accessibility-section-508/SKILL.md
    ├── foia-and-records/SKILL.md
    └── public-procurement/SKILL.md
```

### Skill count delta

Phase 7a closed with 45 skills. Phase 7b adds 3:

- 45 → **48** skills after Phase 7b

(Phase 8 closeout will regenerate the inventory in
`.claude/skills/core/ceo-orchestration/SKILL.md`; not done here.)

### Squad count delta

- 4 domain squads → **5** (fintech, lgpd-heavy-saas, trading-hft,
  edtech, government)

### VETO holders rationale

| Persona | Scope | Why this slice |
|---|---|---|
| Linh Abernathy (Government A11y Engineer) | Section 508 pre-merge checklist; procurement-block surface | 508 non-compliance is a legal bid-disqualification in federal procurement and increasingly state/local. Consequences are categorically different from design-taste a11y reviews — VETO-weight is statutory. |
| Yewande Crossland (FOIA Compliance Officer) | Records lifecycle, retention, redaction, requester-identity confidentiality, SLA machinery | FOIA / public-records exposure is a distinct regulatory regime with its own statute (5 USC §552 + state equivalents). Records engineering errors (hard-delete, render-layer redaction) are silently-fatal until discovery — catch them at merge time or explain at deposition. |
| Senator Rafael Hoelzle (Procurement Integrity Officer) | Bid confidentiality, debarment vetting, COI, award rationale, audit trail | Procurement integrity (FAR/DFARS) is governed by a separate statute (41 USC §2101-2107 Procurement Integrity Act + 18 USC §208 COI) with a distinct enforcement surface (bid protests at GAO or state equivalent). A sustained protest can rescind awards. Requires its own reviewer lens. |

The 4th persona (Darius Okonkwo, Public Records Engineer, IC) is
consultative — the implementation coordinator between the three
VETO holders. The 5th (Captain Mireille Abernathy, Government
Cybersecurity Engineer) is advisory on FedRAMP/FISMA-scoped changes;
explicitly non-VETO because security scoping depends on the agency
authorization boundary, which is agency-specific and not uniformly
gate-worthy.

The "Senator" and "Captain" titles are character nicknames with
non-governmental origin stories (state senate procurement-reform
commission, ex-military cyber unit), disambiguated in the persona
bios to avoid implying actual political office or military rank
claims. The Abernathy surname shared between two personas is
flagged in-text as coincidental — per ADR-009 fictional-composite
rules, no real person is referenced.

## Dogfood outcome v2 (Agent Architect methodology)

### Was this run faster than Phase 7a?

**Yes, substantially.** Phase 7a (edtech) took ~1 session turn of
model work plus methodology self-discovery (narrow-scope VETO,
cross-squad reference, pitfall-floor mismatch). Phase 7b (government)
inherited all of those calibrations from ADR-025 and proceeded
directly to domain-content drafting.

Concrete deltas vs Phase 7a:

- **Zero methodology-level decisions re-opened.** VETO-declaration
  style (table-header form) copied from edtech. Pitfall floor
  (≥12, raised by PLAN-010 C4) respected from the start — no
  mid-draft refactor. Cross-squad reference convention ("read,
  don't install" per ADR-025 §3) reused for government-references-lgpd.
- **Domain-content drafting was the bottleneck, not file-shape
  drafting.** The structural templates (YAML schemas, SKILL
  frontmatter, persona table headers) were re-used without
  modification. Effort concentrated on the Section 508 checklist,
  FOIA exemption table, and procurement lifecycle diagram — the
  irreducible domain knowledge.
- **Validator pass on first attempt.** Phase 7a needed a heuristic
  tuning pass on `validate-squad-contract.py` to accept both
  VETO-declaration styles (table-row vs heading-annotation). Phase
  7b used the table-row form exclusively and the existing validator
  passed without modification.
- **Fewer judgment calls.** The three VETO holders mapped cleanly
  to the three regulatory regimes; no ambiguity akin to "should the
  Analytics VETO be narrowly scoped to fairness-only?" from edtech.

### Time budget

**Goal** (debate K7): ≤1 day per squad.
**Actual (Phase 7a):** ~1 session turn + methodology emergence.
**Actual (Phase 7b):** ~1 session turn, direct.

Trajectory suggests the methodology is in fact compounding: each
subsequent squad should cost approximately the domain-content
drafting time alone (~30 minutes of focused writing per skill for
a pre-identified 3-skill squad), which is why the K7 budget is
trivially met once the framework has ≥1 prior squad as a template.

### What DID NOT get easier in v2

- **Domain-content quality.** Section 508 checklist fidelity,
  FOIA exemption specificity, and procurement COI machinery all
  required domain-specific accuracy that the methodology cannot
  produce. A less domain-literate drafter would produce thinner
  material even following the exact same template.
- **Persona authenticity.** Fictional-composite personas still
  need backgrounds, mantras, and red-flag vocabularies that feel
  lived-in. This is writing craft, not template-filling. Quality
  here depends on drafter taste, not methodology maturity.
- **Cross-squad reference accuracy.** The government squad
  references `lgpd-heavy-saas` for `pii-data-flow`. Verifying that
  the referenced skill actually exists and covers the expected
  surface remains manual.

### Unchanged from ADR-025 — still open for Sprint 11

1. **Pitfall floor bump** from 10 → 12 universally across squads
   (ADR-009 amendment). Both edtech (18 pitfalls) and government
   (21 pitfalls) already exceed; codifying would eliminate
   confusion for future-squad drafters.
2. **Standardize VETO declaration style** — pick table-row form
   (ADR-009 amendment). Both new squads used table-row; the
   drift-risk noted in ADR-025 has not yet materialized but will
   on the next squad if unchecked.
3. **Formalize cross-squad reference dependencies.** Add a
   `references:` frontmatter key on squad manifests so reader can
   find pre-requisite reading without install-time dependency
   pulling.
4. **Update `.claude/skills/core/agent-architect/SKILL.md`** to
   codify the Phase 7a + 7b learnings: narrow-scope VETO pattern,
   cross-squad reference convention, pitfall-floor 12, table-row
   VETO declaration style.

### New for Phase 7b — Sprint 11 candidates

5. **"Advisory persona with near-VETO weight" pattern.** Captain
   Abernathy (Cybersecurity) is non-VETO but practically blocks
   FedRAMP-scoped changes. ADR-009 currently treats VETO as binary;
   a `scoped-conditional-veto` tier for "VETO within boundary X"
   would reduce the hack of "non-VETO in theory, VETO in practice."
6. **Squad-level recursion check.** Government shares scope
   adjacencies with lgpd-heavy-saas (privacy) and core
   accessibility-and-wcag (a11y). The `check_agent_spawn.py` recursion
   guard handles persona-level loops; a squad-level equivalent
   ("don't spawn agents from two squads whose VETOes overlap
   without explicit merge protocol") would prevent a future
   deadlock.

## Consequences

### Positive

- Framework adopts its 5th domain squad on the established ADR-009
  contract, with a clean first-attempt validator pass.
- Three statutorily-distinct regulatory regimes (508, FOIA, FAR)
  now have named homes with independent VETO authority.
- Dogfood v2 confirms the Agent Architect methodology compounds:
  the second squad cost less than the first in methodology work,
  concentrating effort on domain content.
- `validate-squad-contract.py` required ZERO modifications — first
  programmatic signal that the contract is stable enough for
  outside adoption (ADR-009 v1 is defensible as drafted).

### Negative

- Skill count grows 45 → 48. Continues the bloat concern from
  Sprint 4 Growth feedback; counter-argument: these skills cover
  novel statutory surfaces not handled by core/fintech/lgpd/edtech
  and carry clear VETO justifications.
- Government work often requires FedRAMP / FISMA / StateRAMP
  overlays that the current squad (non-VETO Cybersecurity persona)
  only advises on. A follow-up squad or ADR-009 amendment may be
  needed if adopters hit FedRAMP ATO boundaries in practice.
- Sprint 11 open questions accumulate (6 total now, 4 inherited +
  2 new). Deferral discipline continues but pressure to formalize
  ADR-009 v2 is building.

### Neutral

- install.sh requires no change (ADR-009 §installation already
  supports arbitrary profile names).
- registry.py discovers the new skills automatically.
- `scripts/status.py` will surface a skill count of 48 after Phase 8
  inventory regen.

## Blast Radius

- `.claude/skills/domains/government/` (NEW subtree, 8 files)
- `.claude/adr/ADR-026-squad-government.md` (this file)
- `.claude/plans/PLAN-010/architect/round-1/approved.md` (sentinel
  scope extended — edtech scope unchanged, government appended)

**Reversibility:** HIGH — delete the government subtree; no other
file references it by hard-coded path. The validator, sentinel,
and existing 4 squads are unaffected.

## References

- ADR-009 (squad bundle contract — base)
- ADR-010 (canonical-edit sentinel — enforcement used for both
  edtech and government adoption)
- ADR-025 (squad edtech + dogfood v1)
- PLAN-010 Phase 7b (government squad assignment)
- PLAN-010 debate C4 (≥12 pitfalls; programmatic validator)
- PLAN-010 debate K7 (≤1 day per squad time budget)
- `.claude/skills/core/agent-architect/SKILL.md`
- `.claude/skills/domains/edtech/` (reference squad v1)
- Revised Section 508 standards (36 CFR Part 1194)
- 5 USC §552 (Federal FOIA)
- Federal Acquisition Regulation (48 CFR Chapter 1)
- 41 USC §2101-2107 (Procurement Integrity Act)
- DOJ ADA Title II final rule on web/mobile accessibility (2024)

## Enforcement commit

`dd1813bbf370` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
