# Squad-Bundle Templates — Authoring Guide

This directory contains templates for authoring ADR-009-compliant squad
bundles for grandfather domains. Each template uses `{{TOKEN}}` mustache-style
placeholders that adopters replace via `sed` substitution.

---

## ADR-009-Compliant Exemplars

When in doubt, read these four exemplars before authoring any new bundle.
They represent the canonical pattern this framework enforces.

| Exemplar domain | team-personas.md | pitfalls.yaml | task-chains.yaml | examples/ |
|---|---|---|---|---|
| edtech | `.claude/skills/domains/edtech/team-personas.md` | `.claude/skills/domains/edtech/pitfalls.yaml` | `.claude/skills/domains/edtech/task-chains.yaml` | `.claude/skills/domains/edtech/examples/` |
| government | `.claude/skills/domains/government/team-personas.md` | `.claude/skills/domains/government/pitfalls.yaml` | `.claude/skills/domains/government/task-chains.yaml` | `.claude/skills/domains/government/examples/` |
| lgpd-heavy-saas | `.claude/skills/domains/lgpd-heavy-saas/team-personas.md` | `.claude/skills/domains/lgpd-heavy-saas/pitfalls.yaml` | `.claude/skills/domains/lgpd-heavy-saas/task-chains.yaml` | `.claude/skills/domains/lgpd-heavy-saas/examples/` |
| trading-hft | `.claude/skills/domains/trading-hft/team-personas.md` | `.claude/skills/domains/trading-hft/pitfalls.yaml` | `.claude/skills/domains/trading-hft/task-chains.yaml` | `.claude/skills/domains/trading-hft/examples/` |

**Why these 4 specifically:** they are the only ADR-009-compliant bundles
empirically (5/5 artifacts present). Other domains may exist in
`.claude/skills/domains/` with partial bundles (3-4 of 5 artifacts) — those
are not authoritative reference shapes for this template.

---

## Token Substitution Conventions

All template files use `{{TOKEN}}` placeholders (mustache-style, uppercase,
underscores). Adopters replace these via `sed -i` or equivalent:

```bash
# Example substitution for a new "devrel" domain bundle:
DOMAIN_SLUG="devrel"
DOMAIN_LABEL="DevRel"
DOMAIN_PREFIX="DEVREL"

sed \
  -e "s/{{DOMAIN_SLUG}}/${DOMAIN_SLUG}/g" \
  -e "s/{{DOMAIN_LABEL}}/${DOMAIN_LABEL}/g" \
  -e "s/{{DOMAIN_PREFIX}}/${DOMAIN_PREFIX}/g" \
  team-personas.md.template > team-personas.md
```

### Required tokens (must be replaced in every new domain)

| Token | Description | Example |
|---|---|---|
| `{{DOMAIN_SLUG}}` | kebab-case directory name | `devrel` |
| `{{DOMAIN_LABEL}}` | Human-readable label for H1 titles | `DevRel` |
| `{{DOMAIN_PREFIX}}` | UPPER-case pitfall ID prefix | `DEVREL` |
| `{{DOMAIN_DESCRIPTION}}` | Brief domain description for blockquote | `developer relations and community growth` |
| `{{PRIMARY_REGULATIONS}}` | Applicable regulatory surface | `GDPR + CCPA + platform ToS` |
| `{{VETO_PERSONA_1}}` | Name of first VETO persona | `Adaeze Okonkwo` |
| `{{VETO_ROLE_1}}` | Role title of first VETO persona | `Community Trust Engineer` |
| `{{VETO_SCOPE_1}}` | What this persona vetoes | `Any change to public API contracts or rate-limit policies` |

### Persona token pattern

For each persona slot 1–5, fill:
- `{{PERSONA_N_NAME}}` — Fictional full name (not a real person)
- `{{PERSONA_N_TITLE}}` — Title shown in the H3 heading
- `{{PERSONA_N_ROLE}}` — Role in the table
- `{{PRIMARY_SKILL_N}}` — Primary skill reference (matches a SKILL.md path)
- `{{SECONDARY_SKILL_N}}` — Secondary skill reference
- `{{PERSONA_N_BACKGROUND}}` — 2-3 sentence career background
- `{{PERSONA_N_FOCUS}}` — Technical areas of concern
- `{{PERSONA_N_RED_FLAGS}}` — 2-3 warning phrases
- `{{PERSONA_N_ANTI_PATTERNS}}` — 2-4 bad implementation patterns
- `{{PERSONA_N_MANTRA}}` — Opinionated single-sentence rule

### Pitfall token pattern

For each pitfall slot NNN:
- `{{RULE_NNN}}` — Imperative rule statement. Start with "NEVER" or an
  affirmative obligation. Be specific enough to be actionable.
- `{{WHEN_NNN}}` — One sentence describing the trigger context.
- `{{AGENTS_NNN}}` — Comma-separated list of persona names from team-personas.md.

### Task-chain token pattern

For each chain:
- `{{CHAIN_N_SLUG}}` — kebab-case suffix for the id
- `{{CHAIN_N_TITLE}}` — Human-readable chain title
- `{{CHAIN_N_WHEN_TO_USE}}` — 2-5 sentences describing trigger and scope
- `{{CHAIN_N_STEP_M_OWNER}}` — Persona name + role
- `{{CHAIN_N_STEP_M_ACTION}}` — Imperative action sentence

---

## Bundle Completeness (ADR-009)

A complete squad bundle requires all 5 artifacts:

| Artifact | Canonical? | Min content |
|---|---|---|
| `team-personas.md` | **YES** — sentinel required | 3 VETO personas + 2 non-VETO personas; VETO table; escalation section |
| `pitfalls.yaml` | **YES** — sentinel required | ≥12 pitfall entries; ≥4 thematic sections |
| `task-chains.yaml` | NO | ≥2 chains; each with ≥6 steps + verification block |
| `examples/*.md` | NO | ≥1 example scenario using the domain's personas + pitfall refs |
| README or SKILL.md | varies by domain | Exists at `skills/<domain-slug>/SKILL.md` if domain has skills |

### Canonical vs. non-canonical

**Canonical files** (`team-personas.md`, `pitfalls.yaml`) are protected by
`check_canonical_edit.py`. Any modification requires a GPG-signed sentinel
at `.claude/plans/PLAN-<NNN>/architect/round-<N>/approved.md` with:

- The canonical paths listed under the `Scope:` block (between
  `<!-- BEGIN SIGNED SCOPE -->` and `<!-- END SIGNED SCOPE -->`)
- `Approved-By: @<owner-handle> <REASON-SLUG>`

**Kernel-override (`CEO_KERNEL_OVERRIDE` + `CEO_KERNEL_OVERRIDE_ACK`)** is
NOT required for ordinary `team-personas.md` / `pitfalls.yaml` edits — those
are sentinel-only. Kernel-override applies ONLY to paths in `_KERNEL_PATHS`
HARD-DENY list (e.g., `_lib/audit_emit.py`, `_lib/contract.py`,
`check_canonical_edit.py` itself, `.claude/policies/*.yaml` since
v1.13.0). See `.claude/hooks/check_arbitration_kernel.py` for the
authoritative kernel-paths list.

**Non-canonical files** (`task-chains.yaml`, `examples/`, `README.md`)
do NOT require a sentinel. They can be iterated freely during a session.

---

## Required CI Gates

### V3 helper PII inheritance check

Any domain whose name contains a PII-regulatory signal (legal, healthcare,
hr, finance-accounting, real-estate-finance) MUST verify that the domain's
SKILL.md inherits from at least one of:
- `core/pii-data-flow`
- `core/consent-lifecycle`
- `core/compliance-lgpd`

This is enforced by the Phase 0a V3 helper tests in:
`.claude/plans/PLAN-080/staging/phase-0a/tests/`

### scan-injection-strict.sh gate

`task-chains.yaml` and `examples/*.md` MUST pass:

```bash
.claude/scripts/scan-injection-strict.sh <file>
```

This is the fail-on-match wrapper around `scan-injection.py`. The advisory
`scan-injection.py` exits 0 always and is NOT sufficient for CI gating.
`scan-injection-strict.sh` exits non-zero when `matched=true`, making it
suitable as an ERROR-tier rule in `validate-governance.sh`.

Note: `team-personas.md` and `pitfalls.yaml` are also scanned but their
content is more tightly controlled via the canonical edit guard.

### Variance kill-switch (PLAN-080 Phase 0b)

After authoring the N=3 pilot bundles (sales + legal + devrel), compute:

```
stdev(effort_hours) / mean(effort_hours)
```

If this coefficient of variation exceeds **50%**, BLOCK Phase 2 entry and
require Owner re-scope. Record per-domain effort in:
`.claude/plans/PLAN-080/staging/phase-0b/calibration.md`

---

## How to Consume These Templates

1. Create the new domain directory:
   ```bash
   mkdir -p .claude/skills/domains/<domain-slug>/examples
   ```

2. Copy templates:
   ```bash
   cp templates/team-personas.md.template .claude/skills/domains/<domain-slug>/team-personas.md
   cp templates/pitfalls.yaml.template .claude/skills/domains/<domain-slug>/pitfalls.yaml
   cp templates/task-chains.yaml.template .claude/skills/domains/<domain-slug>/task-chains.yaml
   cp templates/examples/template-example.md.template \
      .claude/skills/domains/<domain-slug>/examples/PLAN-EXAMPLE.md
   ```

3. Replace all tokens via sed (or author manually):
   ```bash
   sed -i "s/{{DOMAIN_SLUG}}/<domain-slug>/g" \
     .claude/skills/domains/<domain-slug>/team-personas.md \
     .claude/skills/domains/<domain-slug>/pitfalls.yaml \
     .claude/skills/domains/<domain-slug>/task-chains.yaml \
     .claude/skills/domains/<domain-slug>/examples/PLAN-EXAMPLE.md
   ```

4. Fill in the domain-specific content (rules, personas, steps).

5. Run CI gates:
   ```bash
   .claude/scripts/scan-injection-strict.sh \
     .claude/skills/domains/<domain-slug>/task-chains.yaml
   .claude/scripts/scan-injection-strict.sh \
     .claude/skills/domains/<domain-slug>/examples/PLAN-EXAMPLE.md
   .claude/scripts/validate-governance.sh
   ```

6. Author a GPG sentinel for the canonical files (team-personas.md,
   pitfalls.yaml) and run the Phase 0b ceremony script.
