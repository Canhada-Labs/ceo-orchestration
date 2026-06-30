---
id: ADR-073
title: SemVer bump criteria for Sprint 32 closeout — v1.9.0 / v1.10.0 / v2.0.0 decision
status: ACCEPTED
created: 2026-04-22
accepted_at: 2026-04-24
accepted_via: Round-19 sentinel (84a4977 promote) + applied at Phase 8 v1.10.0 tag decision + PLAN-058 Round-23 frontmatter flip (F-CR-02 residual closure)
proposed_by: CEO + VP Engineering (PLAN-051 Phase 2.5)
related_plans: [PLAN-051]
related_adrs: [ADR-070, ADR-071, ADR-007]
blast_radius: L3-wide (irreversible tag push semantics, npm registry impact)
supersedes: none
superseded_by: none
gates_phase: PLAN-051 Phase 8
enforcement_commit: 84a4977
---

# ADR-073 — SemVer bump criteria for Sprint 32 closeout

## Context

PLAN-051 Phase 8 produces a final tag for the sprint. Three candidate
versions are on the table:
- **v1.9.0** — minor bump (no breaking changes)
- **v1.10.0** — minor bump if accumulated changes warrant
- **v2.0.0** — major bump (breaking change shipped)

The decision drivers are mechanical (per SemVer 2.0.0 spec) but
non-trivial because Phase 3 (audit_emit split — B1) may or may not
ship a breaking refactor depending on approach selection in ADR-070
+ Phase 3 execution.

PLAN-051 §Phase 1 also intentionally already pushes `v1.9.0` GA tag at
Phase 1 conclusion (independent of Phase 8) — so Phase 8 ALSO tags
either v1.9.1 (patch on v1.9.0) or v1.10.0 / v2.0.0 (post-Phase-3+
features merged).

## Options considered

### v1.9.0 — Phase 1 GA tag (committed)

Per Phase 1 A3, this tag is signed + pushed BEFORE Phase 3 executes.
It captures:
- VERSION/npm align (3-minor-drift fix)
- Grandfather.yaml warnings burn-down
- All PLAN-050 closure (Sprint 31 done)
- Pre-Sprint-32 governance state

This is non-negotiable in Phase 1; ADR-073 only governs the **Phase 8
closeout tag** decision.

### Option A — v2.0.0 (if B1 ships breaking refactor)

**Trigger:** Phase 3 ships `audit_emit_pkg/` canonical AND monolith
`audit_emit.py` deleted (atomic swap successful).

**Justification per SemVer:**
- Public import path changes (`from _lib.audit_emit import X` may
  remain a shim, OR may require `from _lib.audit_emit_pkg.core import X`
  per chosen approach in ADR-070)
- ADR-070 Approach 3 explicitly listed as "breaking change"
- ADR-070 Approaches 1 & 2 may also break IF behavioral redaction or
  any consumer-facing API changes

### Option B — v1.10.0 (minor bump, no breaking)

**Trigger:** Phase 3 ships `audit_emit_pkg/` AND ADR-070 Approach 1 or
2 selected AND no public-API breakage AND backward-compat shim
preserved.

**Justification per SemVer:**
- New features added (package layout, mutation budget 12→40, kill-
  switch layers 4+6, conftest discovery, benchmark publication)
- No existing consumer breaks
- Minor bump appropriate

### Option C — v1.9.1 (patch bump)

**Trigger:** Phase 3 refused via ADR-070 + Phase 7 refused via ADR-072
+ all other Phases ship without breaking changes.

**Justification per SemVer:**
- Only fixes (mutation budget, kill-switch wiring, benchmark publication)
- No new public APIs
- No breaking changes
- Patch bump appropriate

## Decision

**Conditional decision:** version selected at Phase 8 closeout based on
Phase 3 outcome:

```
IF B1 (audit_emit split) shipped:
  IF chosen ADR-070 approach is breaking (Approach 3 OR explicit
  breakage in 1/2):
    → v2.0.0
  ELSE:
    → v1.10.0
ELIF B1 refused (ADR-070 refused):
  → v1.9.1
```

## Decision drivers

1. **SemVer 2.0.0 strict compliance.** No marketing-driven SemVer
   inflation; bump category derives from change category.

2. **Adopter contract preservation.** v1.9.0 → v2.0.0 forces adopters
   to read CHANGELOG before upgrade (npm/pip semver constraint
   convention). Forcing this on a non-breaking change erodes adopter
   trust.

3. **Marketing alignment.** v2.0.0 is reserved for the milestone where
   "audit cycle" (PLAN-052) ships if Owner pursues it post-Sprint-32.
   This ADR does NOT pre-commit Phase 8 to v2.0.0.

4. **Tag immutability.** Once pushed, npm registry semantics make tags
   irreversible (yanking is a serious action). Decision rule must be
   defensible at tag time.

5. **Breaking-change definition** (per SemVer 2.0.0):
   - Any public API import path change
   - Any public API signature change (parameters, return type, raises)
   - Any documented behavior change that consumers depend on
   - Removal of any public symbol
   - File-format change (audit-log JSONL schema, ADR frontmatter, etc.)

   NOT breaking changes:
   - Internal refactor preserved by shim
   - Bug fix that aligns behavior to documentation
   - Performance improvement (faster path, same semantics)
   - Test additions
   - New public API alongside existing one

## Consequences

### v1.9.1 path (Option C)
- Lowest blast radius
- Conservative messaging: "patch release, no new features"
- Frame Sprint 32 as "drainage of governance + observability" rather
  than capability expansion
- Best fit if Phase 3 refused

### v1.10.0 path (Option B)
- Moderate blast radius
- Honest: features added, no breakage
- Ships mutation budget + kill-switch + benchmarks under minor bump
- Best fit if Phase 3 ships non-breaking

### v2.0.0 path (Option A)
- Largest blast radius
- Adopter migration burden (read CHANGELOG, possibly refactor imports)
- Justifies §6.1 "single-file audit_emit.py invariant SUNSET" + new
  package boundary
- Requires `docs/security/v2.0-posture-delta.md` per Security S14
- Requires `docs/MIGRATION-v1-to-v2.md` per adopter clarity

## Blast radius

**L3-wide.** Touches:
- `VERSION` (single file edit at Phase 8)
- `npm/package.json` (version field)
- `SPEC/v1/README.md` (status line)
- `CHANGELOG.md` (closeout entry per CLAUDE.md ritual)
- Tag push to origin (irreversible per npm registry semantics)
- release.yml workflow (signed tag + SBOM + sigstore + GPG verify)
- Adopter installations (manual upgrade if v2.0.0)

## Dual co-sign (PLAN-051 §3.1)

- **VP Engineering:** ✅ co-author (SemVer compliance per skill
  §Versioning Discipline)
- **Principal Security Engineer:** ✅ reviewed (signed tag mandatory
  per Security Risk #5; SBOM mandatory; v2.0.0 requires security-
  posture delta doc per Security S14)
- **Principal Performance Engineer:** N/A (no perf gate on tag itself;
  tagging operation is constant-time)
- **Principal QA Architect:** ✅ reviewed (suite-composition table
  must be met per §5 Acceptance regardless of bump category)

## Lifecycle

- **PROPOSED-STAGED** (this commit) — Phase 2.5 draft
- **PROPOSED canonical** — round-18 promote
- **ACCEPTED** — Phase 8 closeout selects version per decision rule
  above; ADR amended with `chosen_version: v1.9.1|v1.10.0|v2.0.0` +
  rationale referencing Phase 3 outcome
- **SUPERSEDED** if Owner overrides SemVer-correctness rule for
  marketing reasons (would require explicit ratification + new ADR)

## References

- ADR-070 (audit_emit package layout — gates Phase 3 outcome → bump
  determination)
- ADR-007 (release candidate / GA policy precedent)
- ADR-071 (benchmark methodology — Phase 5 outcome may add to feature
  list under v1.10.0 / v2.0.0)
- SemVer 2.0.0 spec: https://semver.org/spec/v2.0.0.html
- PLAN-051 §Phase 8 (closeout phase that consumes this ADR)
- npm publishConfig in `npm/package.json` (provenance: true, public
  access — both supply-chain hardening per Security S10)

## Enforcement commit

**Enforcement commit:** to be populated post-Phase-8-execute with the
commit SHA of the VERSION/package.json bump that produces the chosen
tag. Pre-Phase-8, enforcement is the conditional rule above; any
deviation requires Owner ratification + new ADR.
