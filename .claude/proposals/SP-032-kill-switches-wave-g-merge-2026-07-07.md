---
id: SP-032
skill_slug: kill-switches
archetype: trading-risk-engineer
proposed_at: 2026-07-07T06:08:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: null
diff_size_removed: null
sha256_of_diff: null
sha256_of_staged: 2ecd99f65035c3b72f1549766102e38cf64dc67bca964cc23c45856057cc5729
claims_declared: false
status: draft
approved_by: null
applied_at: null
promoted_at: null
shadow_mode: true
proposal_type: adapt-merge-enrichment
after_wave_c: false
upstream_sources:
  - affaan-m/ecc@81af4076 skills/llm-trading-agent-security/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/trading-hft/skills/kill-switches/
---

# SP-032 — skill patch proposal (Wave G ADAPT merge)

**Target:** `.claude/skills/domains/trading-hft/skills/kill-switches/SKILL.md`
**Archetype:** trading-risk-engineer
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (1 upstream skill folded into an
existing catalog skill; no new skill file; catalog count unchanged)

## Rationale

Wave G materialized-merge **row 11**: fold `affaan-m/ecc@81af4076`
`skills/llm-trading-agent-security/` (matrix quality **q4**) into `kill-switches`
— **prompt injection framed as a financial attack** on an LLM trading agent, with
hard spend limits and mandatory simulation before live execution. Strong
fintech+governance fit (this framework's own trading-readonly posture). Additive;
staged file is 212 lines vs. the 128-line live skill (net +84 lines).

## Provenance note

Clean-room ADAPT (upstream informed scope; prose original, zero ECC strings).
Provenance in the root `NOTICE` Wave G section
(`affaan-m/ecc@81af4076 skills/llm-trading-agent-security/`, MIT) + `inspired_by:`
frontmatter. Carries upstream content → rides the **import gate** plus
`/skill-review`. This skill's subject IS injection-as-attack, so import-gate
check (a) may surface expected pattern hits **as documented examples** — the
reviewer distinguishes documented attack patterns from an actual injection payload
in the skill body. `scan-injection.py` over all staged Wave G files (2026-07-07):
no non-zero exit; enforcing checks at the ceremony.

Rollback-safe: promote replaces exactly one file (SKILL.md).

## Patch source (staged tree, sha256-pinned)

`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/trading-hft/skills/kill-switches/`:

| sha256 | file |
|---|---|
| `2ecd99f65035c3b72f1549766102e38cf64dc67bca964cc23c45856057cc5729` | `SKILL.md` (merged, 212L) |

## Proposed diff (summary — the full diff is NOT embedded)

```
git diff --no-index .claude/skills/domains/trading-hft/skills/kill-switches/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/trading-hft/skills/kill-switches/SKILL.md
```

## Landing mechanics (wake-up ceremony — /skill-review + import gate)

1. **Import gate + /skill-review** — `check-imported-skill.py --skill <staged
   SKILL.md> --notice NOTICE`; when check (a) flags the documented attack-pattern
   examples, confirm they are illustrative, not live payloads. Human review ON
   TOP. Verify the sha256 pin.
2. **Approve (shadow apply)** — copy staged SKILL.md →
   `.../kill-switches/SKILL.md.shadow.md`; set `status: shadow`, `applied_at`,
   `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c)** — live SKILL.md keeps serving;
   `skill-health.py` telemetry is the regression signal.
4. **Promote** — `mv SKILL.md.shadow.md SKILL.md` under the SKILL.md sentinel gate;
   replace `SP-NNN` in the merged changelog with `SP-032`; set `status: promoted`,
   `promoted_at`.

## Honest residuals

- The skill's own subject (injection-as-financial-attack) means the injection
  scanner will predictably match documented examples; this is expected and is a
  review judgement, not an auto-block.
- `scan_injection_pass: true` = advisory exit-0, not a full injection audit.
- +84 lines paid per activation (not a Wave C pilot); acceptable for q4.
