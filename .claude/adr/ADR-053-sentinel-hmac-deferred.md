# ADR-053: Sentinel HMAC deferred — SHA-256 + CODEOWNERS sufficient under current threat model

**Status:** ACCEPTED
**Date:** 2026-04-18 (Session 33 Phase D; PLAN-025 Batch A)
**Deciders:** CEO, Principal Security Engineer, VP Operations
**Blast radius:** L2 (documented decision; zero code changes required)
**Supersedes:** none
**Superseded by:** none
**Depends on:** ADR-010 (canonical-edit sentinel), ADR-051 (skill-by-reference
trust boundary), ADR-031 (self-improving skills / SP-NNN chain)

## Context

PLAN-024 Wave A (12-agent audit, 2026-04-18) surfaced F-sec-007 as a
P2 finding: the canonical-edit sentinel and skill-reference sentinel
both rely on **SHA-256 content hashing** without an HMAC over the hash
itself, so a Tier-2 insider with write access to the sentinel file can
forge a valid sentinel by:

1. Reading the target file (SKILL.md, canonical hook file).
2. Computing its SHA-256.
3. Writing the hash into the sentinel's `Hash:` line.

The attacker gains nothing they couldn't already gain — they already
have write access to the sentinel path, which is CODEOWNERS-gated —
but the audit observer would record `reference_postread_hash_match` as
green when ideally it should register a key-based authenticity failure.

F-sec-007 asked: should we promote the sentinel scheme to HMAC-SHA256
(keyed MAC) so the sentinel line carries a cryptographic commitment
only the Owner's secret key can produce?

This ADR documents the **deferral** decision: we are **NOT** shipping
sentinel HMAC in v1.6.0. The current SHA-256 + CODEOWNERS + branch
protection + Owner-signed commit chain is accepted as sufficient under
the threat model PLAN-025 ships with. This decision is revisited when
the framework gains external adopters whose Owner-workstation threat
level differs from the current internal-dogfood posture.

## Decision drivers

1. **Threat model reality:** the attacker who can forge an HMAC would
   already possess the Owner's private key. At Tier 2 (insider with
   GPG + workstation access), CODEOWNERS + GPG-signed commits are the
   authority chain, not the sentinel hash. The sentinel is evidence,
   not enforcement — `check_canonical_edit.py` blocks on sentinel
   absence, not on hash forgery detection.
2. **Observer pattern adequacy:** `check_skill_reference_read.py`
   (PostToolUse observer) emits `veto_triggered` + forensic breadcrumb
   on mismatch. Even if a forged sentinel slips through, the audit
   record shows the mismatch at read time. Detection, not prevention,
   is the sentinel's role under ADR-051 §Residual trust.
3. **Key distribution cost:** introducing an HMAC key creates a new
   trust root (the key itself) with its own rotation, storage, and
   provisioning problems. For a single-Owner project, the Owner's
   GPG key already performs this role for commits. Duplicating it at
   sentinel level doubles the rotation surface without adding defense
   against the Tier-2 threat that justifies HMAC in the first place.
4. **Dual-path defense-in-depth:** `check_canonical_edit.py` (sentinel
   guard) and `check_arbitration_kernel.py` (hard-deny kernel guard)
   both cover the same paths. An attacker forging a sentinel still has
   to pass the arbitration-kernel's `CEO_KERNEL_OVERRIDE` audit trail.
   The sentinel is layer 1; the kernel override is layer 2. HMAC on
   layer 1 is optimization, not a new primitive.
5. **Adopter readiness:** PLAN-022 (SECURITY.md + threat-model.md) and
   PLAN-024 P0 batch (F-chaos-002 fail-closed arbitration) already
   raise the baseline. Sentinel HMAC is a refinement that would
   benefit from real-world adopter pressure to shape the key
   distribution model, not from speculative pre-adopter design.

## Options considered

### Option A — Ship HMAC-SHA256 in v1.6.0 (REJECTED)

**Scope:** Introduce an HMAC key (stored in
`~/.config/ceo-orchestration/sentinel-hmac.key`, 0o600 perms,
git-ignored). All sentinels carry a new `HMAC:` line. Hooks validate
both Hash: and HMAC: lines.

**Pros:**
- Cryptographic authenticity on sentinel; Tier-2 attacker without
  key cannot forge.
- Brings sentinel up to industry defensive baseline (GitHub's own
  tag-signing uses GPG; sentinel HMAC matches).

**Cons:**
- New secret (HMAC key) to provision, rotate, store. Adopter
  onboarding complicates: where does the key live? How does CI get
  it? Shared-workstation multi-developer repos have no obvious
  answer.
- Zero marginal defense against Tier-2 threat (attacker with
  workstation access likely can read `~/.config/` anyway).
- Adds failure mode: forgotten key during rotation = all sentinels
  appear invalid = governance lockup. Needs recovery procedure ADR.
- 2-4h implementation + 1-2h docs + 30min threat-model refresh.
  Budget better spent on adopter-facing work (PLAN-025 other batches).

**Verdict:** Does not pay for its cost under the current threat model.
Good idea to revisit when adopter threat posture is known.

### Option B — Defer HMAC; document SHA-256 residual (CHOSEN)

**Scope:** Keep the current SHA-256 + CODEOWNERS + GPG-signed commit
chain. Document the sentinel-HMAC residual in
`docs/threat-model.md` §Residual-sentinel-hmac and here (ADR-053).
Cross-reference F-sec-007. Revisit post-v1.6.0 GA based on adopter
feedback.

**Pros:**
- Zero code change; zero regression risk.
- Zero new secret to manage; no key rotation surface added.
- Honest documentation of the residual: adopters see the decision +
  the trade-off + the revisit trigger.
- Frees PLAN-025 budget for higher-impact P1s (observability,
  workflow hardening, 3-profile configurator).

**Cons:**
- Tier-2 insider can still write a valid sentinel. Same as today;
  not a regression.
- Some adopter auditors may flag this as a gap in their SOC2 review.
  Mitigation: `docs/soc2-audit-mapping.md` already notes the
  CODEOWNERS + GPG commit chain as the authority control, not the
  sentinel hash.

**Verdict:** Matches the threat model we have evidence for. Keeps the
option open.

### Option C — HMAC only for skill-reference (PARTIAL REJECTED)

**Scope:** Apply HMAC to ADR-051 skill-reference sentinels only
(they touch external adopter content), keep SHA-256 for
canonical-edit sentinels (they touch Owner-authored content).

**Pros:**
- Narrower scope reduces rotation surface.
- Matches the "expanded trust boundary" argument of ADR-051.

**Cons:**
- Introduces asymmetry between two sentinel types — operational
  confusion (why does this one have HMAC and that one does not?).
- Still requires key provisioning for adopters.
- Half-measure: Tier-2 attacker attacking canonical-edit sentinel
  unaffected, and adopters attacking skill-reference are NOT a Tier-2
  threat in the current adopter landscape (PLAN-015 Phase 1
  install-in-adopter-1 is pre-adopter).

**Verdict:** Best-of-both is no-win under current landscape. Reject
with intent to revisit if asymmetric threat evidence appears.

## Decision

**Option B.** Defer sentinel HMAC to a future ADR. Document the
residual in `docs/threat-model.md` §Residual-sentinel-hmac and here.
Cross-reference F-sec-007 as the finding that prompted the analysis.
Revisit after v1.6.0 GA + at least one external adopter install
surfaces real-world threat data.

## Consequences

### Positive (+)

- No code change, no regression risk, no rotation surface.
- Threat model remains honest (residual documented explicitly).
- PLAN-025 budget preserved for 11 higher-impact batches.
- Clear revisit trigger: first external adopter feedback.

### Negative (-)

- Sentinel authenticity is substring-based (SHA-256 of content) not
  key-based. Tier-2 insider with write access to the sentinel file
  can forge it. Defense layer shifts to CODEOWNERS + GPG-signed
  commits (which was always the primary authority anyway).
- SOC2 auditors familiar with HMAC-based evidence patterns may need
  the companion `docs/soc2-audit-mapping.md` context to accept the
  current model.

### Neutral (~)

- Observer (`check_skill_reference_read.py`) continues emitting
  `veto_triggered` on hash mismatch. Behavior unchanged.
- `check_canonical_edit.py` continues blocking on sentinel absence,
  not on hash forgery. Behavior unchanged.
- `CEO_KERNEL_OVERRIDE` layer 2 remains available for operator
  emergency override. Behavior unchanged.

## Blast radius

**L2** — this is a documentation + decision ADR. No code change. The
only artifacts are:
- This file (`.claude/adr/ADR-053-sentinel-hmac-deferred.md`).
- A new `§Residual-sentinel-hmac` section appended to
  `docs/threat-model.md`.
- Cross-reference update in `SECURITY.md` §Known residuals (already
  present as "No tamper-evident audit-log chain (HMAC deferred)";
  extended naturally by this ADR).

## Revisit trigger

This ADR should be revisited when **any** of:

1. First external adopter (non-dogfood install) deploys the framework
   in production.
2. A security-relevant incident reveals sentinel forgery in the wild.
3. SOC2 Type II audit explicitly requests HMAC-based sentinel evidence.
4. The framework ships a shared-workstation multi-developer mode
   where CODEOWNERS + GPG-signed commits alone are no longer the
   authority anchor.

When revisited, the Owner re-evaluates Options A/B/C with real
threat-intelligence data instead of speculation.

## References

- `ADR-010-canonical-edit-sentinel.md` — the guard this ADR scopes
- `ADR-051-skill-reference-expanded-trust-boundary.md` — the
  expanded trust boundary whose hash scheme this ADR covers
- `ADR-031-self-improving-skills.md` — SP-NNN Owner-signed chain
- `docs/threat-model.md` §RR-9 + §Residual-sentinel-hmac — companion
  residual documentation
- `docs/soc2-audit-mapping.md` — companion SOC2 mapping explaining
  CODEOWNERS + GPG as the primary authority control
- PLAN-024 F-sec-007 — finding that prompted this analysis
- PLAN-025 Batch A — this ADR lands in this batch

## Enforcement commit

`40dae82a19fc` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
