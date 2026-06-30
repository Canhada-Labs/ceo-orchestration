# ADR-060 — Curated skill import pipeline (SP-NNN chain)

**Status:** ACCEPTED
**Date:** 2026-04-19 (drafted) / 2026-04-20 (ACCEPTED by Owner)
**Proposer plan:** PLAN-033 (Wave B, Sprint 27)
**Supersedes:** none
**Superseded by:** none

## Context

The framework ships 48 skills today (19 core + 8 frontend + 21 domain).
Competitor ecosystems (antigravity-awesome-skills, awesome-plugins)
publish 183-631 curated skills each. The breadth gap is real.

**Quality discipline cannot regress.** PLAN-026 audit finding 08
inspected `antigravity-awesome-skills` (1423 marketing → 631 indexed
real) and estimated only 24-29% would pass the framework's rubric
(≥512 non-ws bytes + valid frontmatter + checklist). Wholesale import
is noise; curated subset is value.

This ADR defines the **pipeline** — not the set of skills imported.
The pipeline runs offline (Owner-driven), gates every candidate behind
a mechanical rubric + a per-skill SP-NNN signed chain, and ships
attribution (license + upstream) as frontmatter + `NOTICE.md`.

## Decision drivers

- **Breadth without dilution:** 15-40 curated skills vs 631 noisy.
- **Attribution is non-negotiable:** each imported skill is covered by
  an upstream license (CC BY 4.0 / MIT / Apache-2.0 / …). The MIT
  License requires retention of copyright notice; CC BY 4.0 requires
  attribution + license URL. We satisfy both via frontmatter fields +
  `NOTICE.md`.
- **Per-skill Owner review:** offensive-security skills are
  disproportionately represented in some upstreams (jailbreak
  tutorials, malware primers). The rubric carries a narrow deny-list
  as a first-pass filter; Owner still reviews every candidate before
  SP-NNN signing.
- **SP-NNN chain reuse:** the framework already gates canonical
  SKILL.md edits behind SP-NNN (ADR-031). We reuse that infrastructure
  for external imports — no new signing surface.

## Options considered

### Option A — Two-tool pipeline (CHOSEN)

1. `.claude/scripts/skill-import-rubric.py` — validator
   (7 rules: filename, non-ws size, frontmatter, headings, checklist,
   forbidden-keywords, UTF-8 cleanliness).
2. `.claude/scripts/import-skill.py` — wrapper that consumes the
   validator, injects provenance frontmatter (source / license /
   sp_chain / owner_sha256 / imported_at / imported_by), and writes
   to `.claude/skills/domains/community/skills/<slug>/SKILL.md`.
3. `community/` as the target domain so imports are siloed from core /
   frontend / vertical-domain skills.
4. `NOTICE.md` append-only attribution ledger under
   `.claude/skills/domains/community/`.

**Pros:**
- stdlib-only (Python + no deps).
- Validator is a dry-run safety net that fails LOUD on rubric
  violations.
- Per-import SP-NNN chain is enforced by wrapper parameter + commit
  discipline.
- Rubric is parametrized; easy to extend per Owner without shipping
  new deny-list logic.
- Tests: 84 (56 rubric + 28 import) covering every rule + edge case.

**Cons:**
- Adding 15-40 SKILL.md files puts them under the canonical-edit
  sentinel post-commit. They cannot be edited without SP-NNN — this
  matches how `core/` + `frontend/` already work, but means upstream
  updates require a new SP-NNN chain even for bugfixes.

### Option B — Mirror + patch model

Import the upstream repo as a git submodule and keep local patches
separately.

**Pros:**
- Easier to track upstream updates.

**Cons:**
- Submodule trust boundary expands (entire upstream history in our
  repo).
- Harder to enforce per-skill rubric gate — the validator runs
  post-hoc vs pre-commit.
- Attribution harder to audit (one giant license file vs per-skill
  frontmatter).

**Rejected.**

### Option C — Fetch at install time

Install script downloads skills from upstream at adopter install
time.

**Pros:**
- Zero extra bytes in the framework repo.

**Cons:**
- Upstream compromise becomes an adopter compromise.
- Offline installs break.
- Adopter has no local audit surface.

**Rejected.**

## Decision

**Option A.** Two-tool pipeline with `community/` as the target domain.

## Decision (extension) — two paths under ADR-060

ADR-060 originally governed **direct import preserved verbatim** of curated skills via
SP-NNN chain. Round 1 debate on PLAN-074 (2026-05-03) surfaced a second use case:
**creative authoring inspired by external prior art** with incompatible upstream voice.
Both paths share the same governance backbone (mechanical validator + Owner-signed
ceremony + canonical-guard discipline) but differ in artifact ratio.

This extension is an amendment; ADR-060 status remains **ACCEPTED**. It subsumes the
earlier proposed ADR-104 (forensic record:
`.claude/plans/PLAN-074/staging/ADR-104-bulk-creative-authoring-strategy-SUBSUMED.md`)
per Round 1 consensus ADJ-A1 and ADR-093 §per-plan-cap moratorium (no new ADR-104
slot created).

### Path 1 — Direct import (existing — unchanged)

The existing pipeline shipped under PLAN-033 Wave B. Mechanism:

- Validator: `.claude/scripts/skill-import-rubric.py` (7 rules — keep as-is)
- Wrapper: `.claude/scripts/import-skill.py` (keep as-is)
- Frontmatter: `source:` + `license:` + `sp_chain:` + `imported_at:` + `imported_sha:` + `imported_by:`
- Tier default: `domains/community/`
- Voice: upstream voice preserved
- Copy ratio: ~100% with frontmatter wrapper
- Ceremony: per-skill SP-NNN chain
- Use case: imports from curated catalogs (e.g. `sickn33/antigravity-awesome-skills`)

### Path 2 — Creative authoring inspired by prior art (NEW — added by Round 1 consensus)

For the case where ground-up rewriting is required because upstream voice is incompatible
with framework conventions OR the corpus is too large for per-skill SP-NNN ceremonies
(>50 skills).

#### Authoring policy

**Each new SKILL.md / agent / playbook doc MUST be authored ground-up in the
framework's house voice. Verbatim copy from external prior art is forbidden, even
with attribution.**

The only structural elements that may carry over with light adaptation:
- Severity / classification scales (SEV1-4, OWASP severity, etc.) when they are
  industry-standard conventions
- Code sample shapes (e.g. STRIDE table headers, JWT validation skeleton) when they
  are conventions
- Numerical thresholds when they are defensible primitives

**Forbidden carry-over:**
- Identity / personality prose (mantras, vibes, war stories)
- Anti-pattern lists verbatim (must be rewritten in our own words)
- Section structure cargo-cult (every skill conforms to OUR exemplar template, not
  upstream's)
- Marketing language ("expert in X", emojis, hype tone)

#### Frontmatter attribution

Each authored skill carries:

```yaml
---
name: <our-slug>
description: <our description in framework voice >=50 chars>
owner: <our archetype>
inspired_by:
  - source: <upstream-org>/<upstream-repo>/<original-path>@<full-40-hex-sha>
    license: <SPDX-id, e.g. MIT>
    relationship: structural_inspiration   # one of: structural_inspiration | partial_reuse | topic_only | deliverable_template | severity_scale | convention | pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: <YYYY-MM-DD>
---
```

**Note:** `authored_by` and `authored_at` are per-entry fields inside each `inspired_by`
entry -- NOT top-level frontmatter keys. This allows multiple inspirations from different
upstreams to carry different authoring dates.

The `inspired_by:` list MAY contain multiple entries when a skill is a synthesis
(plural attribution is intellectually honest).

#### Mechanical drop policy (Round 1 ADJ-B2 upgrade -- verifiable, not subjective)

A new skill is **dropped** (not shipped) if any of:

1. Body < 1 KB after rewrite
2. Description < 50 chars OR generic ("expert in X") after 3 attempts to specify
3. Verbatim or near-verbatim text from upstream source detected by:
   - **(3a)** >=12 consecutive words match against upstream body, OR
   - **(3b)** Any H2 section's content SHA matches upstream H2 SHA via structural
     fingerprint
4. Conflict with framework governance discovered (CEO competitor, VETO bypass, etc.)
5. Reviewer agent (Code Reviewer Pass 2 per ADR-058) flags the rewrite as low-quality
   and 3 attempts have not resolved

Drops logged to `.claude/plans/PLAN-NNN/drops.md` with: source path, drop reason,
attempts, decision_rationale.

**Tooling:** `scripts/check-creative-rewrite.py` (advisory CLI, ships in PLAN-074 Wave 0).
Implements (3a) word-window match + (3b) per-H2 SHA fingerprint compare against archived
upstream tree.

#### Quality bar (uniform with existing exemplars -- Round 1 ADJ-G2)

New SKILL.md MUST follow the structure of framework exemplars
(`core/code-review-checklist/SKILL.md`, `core/security-and-auth/SKILL.md`,
`core/chaos-and-resilience/SKILL.md`):

1. YAML frontmatter (per attribution policy above) + valid `name:` + `description:` >=50 chars
2. H1 = skill display name
3. First H2 = "Fail-Fast Rule" / "Critical Invariant" / opening discipline statement
   (when applicable to security-/correctness-adjacent skills) OR explicit waiver field
   `no_fail_fast: <reason>`
4. Subsequent H2s structure the content; >=3 H2 sections total
5. Code samples use CORRECT vs WRONG framing where relevant
6. Tables for severity / classification / matrices
7. Anti-Patterns section explicit
8. Cross-Validation / Adversarial Framing section when the skill is review-adjacent
9. References section linking to relevant ADRs / PLANs / cross-skills

**Validator:** `scripts/lint-skills.py` (ships in PLAN-074 Wave 0). Run in CI on every PR
touching `.claude/skills/**/SKILL.md`.

#### Ceremony cadence

Path 2 batches canonical-edit ceremonies per **wave** (groups of related skills) rather
than per-skill:

- Wave-batched ceremony scope <=15 paths per Owner GPG (Round 1 ADJ-C3 cap)
- Sentinel artifact: `.claude/plans/PLAN-NNN/architect/wave-<N>/approved.md.asc`
- Each wave includes: SKILL.md authoring + ROUTING TABLE updates + dispatch regen
- Per-wave Pass-1 + Pass-2 review per ADR-058 mandatory before ceremony (Round 1 ADJ-B1)

This avoids the per-skill SP-NNN ceremony overhead (>50 skills x per-skill ceremony is
infeasible) while preserving the canonical-guard discipline (no bulk-bypass -- every
SKILL.md edit still goes through `check_canonical_edit.py`).

#### Frontmatter validator (Round 1 ADJ-B4, Codex P1-01 + P1-02 hardening)

`validate-governance.sh` extension (ships PLAN-074 Wave 0):

- If `inspired_by:` present, each entry MUST have these per-entry keys:
  `source:`, `license:`, `relationship:`, `authored_by:`, `authored_at:`
- `authored_by:` and `authored_at:` MUST be inside each entry (NOT top-level frontmatter)
- `relationship:` MUST be one of the 7-value allowlist:
    - `structural_inspiration` -- overall structure / section layout borrowed
    - `partial_reuse` -- small code samples or tables reused with adaptation
    - `topic_only` -- topic/domain acknowledged; no structural carry-over
    - `deliverable_template` -- output format / deliverable template adapted
    - `severity_scale` -- severity/classification scale (industry-standard, e.g. SEV1-4)
    - `convention` -- single conventional primitive (header format, token, etc.)
    - `pattern_reference` -- architectural/design pattern referenced by name only
- SHA pin in `source:` field MUST be a valid 40-hex git SHA
- `source:` path portion (between 2nd `/` and `@`) MUST exist in the upstream archive
  index (generated from `.claude/architect/<archive>.tar.zst`); missing path -> ERROR
- License MUST be in SPDX list and compatible with framework license
- `check-skill-health.sh` extension: stale `inspired_by:` SHA pins flagged advisory (WARN)

A SKILL.md without ANY of `inspired_by:` (Path 2) OR `source:` (Path 1) OR
`authored_by: ceo-orchestration framework` inside an `inspired_by` entry (originally
authored, no upstream debt) fails the validator.

#### Playbook docs lint rule (Round 1 ADJ-F2, Codex P2-02 strict hardening)

NEXUS playbook docs under `docs/playbooks/` MUST carry frontmatter:

```yaml
---
type: playbook
runtime_mechanism: false
---
```

`validate-governance.sh` adds rule: any file under `docs/playbooks/` where
`runtime_mechanism:` key is **absent** OR set to `true` is a lint violation (ERROR).
Key must be present and explicitly `false` -- absence is not implicit `false`.
Rationale: NEXUS playbooks are **docs-only** -- no link-from-runtime allowed. Elevating
a playbook to a runtime mechanism requires an explicit ADR amendment (forces deliberate
Owner decision rather than accidental wiring). Enforced in CI.

#### PII inheritance (Round 1 ADJ-C4)

Every PII-touching domain SKILL.md MUST include in frontmatter:

```yaml
inherits:
  - core/compliance-lgpd
pii_handling: required
```

PII-touching domains under PLAN-074 scope: `legal/`, `healthcare/`, `hr/`,
`real-estate-finance/loan-officer`, `finance-accounting/bookkeeper`. Validator
extension (Wave 0) enforces this on PII-domain skills.

#### Provenance archival (Round 1 ADJ-C2)

For Path 2 imports, the upstream tree at the SHA pin MUST be archived to
`.claude/architect/<upstream-org>-<upstream-repo>-archive-<short-sha>.tar.zst` with
hash record at `.claude/architect/<upstream-org>-<upstream-repo>-archive-<short-sha>.sha256`.
Anti-takedown insurance + license-change preservation.

#### Upstream content scan (Round 1 ADJ-C1)

For Path 2 imports, before any creative authoring begins, the archived upstream tree
MUST be content-scanned for prompt-injection patterns per ADR-077
(webfetch-injection-incident) + ADR-083 (mcp-injection-scanner) detection patterns.
Findings logged to `.claude/plans/PLAN-NNN/upstream-injection-scan.md`. Any
HIGH-severity finding triggers per-skill review during creative authoring (skip skills
with embedded injection vectors).

### Distinction matrix (Path 1 vs Path 2)

| Dimension | Path 1 (curated import) | Path 2 (creative authoring) |
|---|---|---|
| Operation | Direct file copy + frontmatter retrofit | Ground-up authoring inspired by source |
| Attribution | `source:` + `sp_chain:` + `imported_sha:` (provenance of bytes) | `inspired_by:` (acknowledgment of debt) |
| Tier default | `domains/community/` | Any tier (creative work fits where the content fits) |
| Voice | Upstream voice preserved | Framework house voice |
| Copy ratio | ~100% with frontmatter wrapper | <12 consecutive words match max |
| Use case | Curated catalogs (sickn33/antigravity-awesome-skills) | Repos with incompatible voice / bulk corpora (msitarzewski/agency-agents) |
| Ceremony | Per-skill SP-NNN chain | Per-wave batched (<=15 paths/wave) |
| Validator | `skill-import-rubric.py` (7 rules) | `lint-skills.py` + `check-creative-rewrite.py` |
| Frontmatter validator | (existing rules) | `inspired_by:` schema check via `validate-governance.sh` |

Both paths preserved. PLAN-074 uses Path 2; existing community/ tier skills used Path 1.


## Threat model

- **T1: Supply-chain injection via compromised upstream.** Mitigated:
  (a) validator's R6 keyword deny-list + R7 bidi / zero-width / BOM
  check catches common adversarial payloads; (b) per-skill SP-NNN
  signed chain requires Owner review + signature — not an automated
  pull.
- **T2: License compliance drift.** Mitigated: `license:` + `source:`
  frontmatter injected by wrapper; `NOTICE.md` ledger append-only.
  Audit via `grep -r 'license:' .claude/skills/domains/community/`.
- **T3: Silent upstream updates.** Accepted residual: imports are
  snapshots at import time. Upstream updates require a new SP-NNN
  chain. Adopters who want automatic upstream sync can fork + wire
  their own pull cadence (not framework default).
- **T4: Offensive-skill slip-through.** Mitigated two ways: (a)
  validator R6 deny-list catches common patterns; (b) Owner reviews
  each skill pre-sign. Residual: a novel-phrasing offensive skill
  could pass R6 + Owner review. Acceptable — we're not the last line
  of defense (GitHub ToS, Anthropic usage policy are upstream checks).
- **T5: Attribution stripping.** Mitigated: wrapper refuses to import
  a skill without `--license`. Even `--skip-rubric` does not bypass
  the `license` injection.

## Consequences

**Positive:**
- Breadth path unlocked: 48 → ~63-88 skills (adopter-gated).
- Mechanical rubric means adopters reuse the same pipeline for their
  own corpus, not just `antigravity-awesome-skills`.
- 84 tests anchor the pipeline's correctness.

**Negative:**
- Extra operational surface: `community/` domain + NOTICE.md +
  per-skill SP-NNN. Owner must track each import's attribution +
  license.
- Import-time cost: per-skill Owner review (~1-3 min) × 15-40 skills
  = ~30-120 min of one-time Owner work per initial batch.

**Neutral:**
- The pipeline ships in Wave B; actual bulk import is Owner-gated and
  happens in a separate physical-shell session.

## Blast radius

**Moderate.** Two new scripts (~480 LoC Python), new `community/`
domain dir, `NOTICE.md` attribution ledger, staged `team-personas.md`
stub. No hook changes, no SPEC changes, no existing-skill changes.
Once bulk import happens, `team.md` + `SKILL MAP` + ROUTING TABLE
need amendments — those land through SP-NNN chain per ADR-031.

## Reversibility

**High.** If the community domain ever proves noisy:

1. Delete `.claude/skills/domains/community/` (all imports +
   NOTICE.md).
2. Delete the two scripts + their tests.
3. ADR-060 status becomes SUPERSEDED.

Imports are snapshots — nothing flows back to upstream. No external
state to unwind.

## Kill-switch

`CEO_ANTIGRAVITY_SYNC=0` (environment) — pipeline inactive. The
validator + wrapper don't check this env var themselves (they're
CLI-invoked, Owner-driven); instead, Owner docs this env in the
community domain NOTICE.md + `OWNER-CLOSEOUT-ACTIONS.md` as the
"stop all future imports" signal. Existing imports remain in place.

## Follow-up

- First batch target: 15-25 skills (3 anchor + 12-22 by rubric) per
  PLAN-033 Phase 3. Bulk import happens in Owner physical-shell.
- After first batch: `team.md` amendment (ROUTING TABLE + SKILL MAP)
  via SP-NNN chain.
- Quarterly cadence: Owner re-runs validator against upstream to
  detect any skill that no longer passes the rubric (e.g. upstream
  removed the checklist section).
- Add `--dry-run` mode to `import-skill.py` if adopters ask for a
  plan preview.

## Enforcement commit

`a87fd7ce7b60` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)

Path 2 amendment enforcement commit: _pending_ (filled at PLAN-074 Wave 0 GPG ceremony).

## Consequences (Path 2 additions -- supplement to SS Consequences above)

### Positive (Path 2)

- Voice consistency across the framework
- No copy-paste debt at scale
- Quality filter built-in (drop happens during rewrite)
- Same-LLM bias partially mitigated by fresh authoring pass
- Coexists with Path 1 -- adopters choose path per import

### Negative (Path 2)

- Higher compute cost per skill (2-3x direct import cost)
- Subjective drop calls (mitigated by mechanical fingerprint test ADJ-B2 + 3-attempt cap)
- Wave-batched ceremony increases scope-block risk (mitigated by ADJ-C3 <=15 paths cap)
- Reviewer agent burden (Pass-2 per skill) -- preserved cost discipline via Sonnet-default
  + Opus-VETO-floor

## References

- PLAN-074 (creative-authoring instance -- implements Path 2 across waves 1-13)
- `.claude/plans/PLAN-074/debate/round-1/consensus.md` (Round 1 origin of this amendment)
- ADR-052 (multi-model dispatch -- VETO floor preserved)
- ADR-058 (brainstorm gate + adversarial framing -- Pass-2 per ADJ-B1)
- ADR-077 (webfetch-injection-incident -- upstream content scan policy)
- ADR-082 (mitigated-rail -- non-VETO archetypes default during execution)
- ADR-083 (mcp-injection-scanner -- scan patterns)
- ADR-093 (refused-adr-moratorium -- SS per-plan-cap respected: this is amendment, not new ADR)
- ADR-095 (calendar-gate-retraction -- no calendar buffer required)
- ADR-096 (vibecoder-only-by-design -- adopter expectations correct)
- ADR-103 (calendar-gate-final-purge -- release.yml RC hold = 24h Codex re-pass mechanical window)

## Reopen criteria (combined for both paths)

This ADR (now covering both paths) reopens if:

- Quality drop rate during a Path 2 instance exceeds 40%
- A class of attribution emerges that does not fit either Path 1 or Path 2 cleanly
- Upstream license-change handling produces an incident
- Mechanical fingerprint test (ADJ-B2) misses a real verbatim violation discovered
  post-ship
