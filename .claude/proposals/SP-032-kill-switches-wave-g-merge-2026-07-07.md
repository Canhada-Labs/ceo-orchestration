---
id: SP-032
skill_slug: kill-switches
archetype: trading-risk-engineer
proposed_at: 2026-07-07T06:08:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: 84
diff_size_removed: 0
sha256_of_diff: 4370917d345a1d88f65255132948aab8c27bf4a0581582f3d4a023818b9a8e23
sha256_of_staged: 7d2febcefe518b39a4ea01494737ec15114c6ed74e05ac473da8f0a749b8eecd
claims_declared: false
status: promoted
approved_by: AE9B236FDAF0462874060C6BCFCFACF00335DC74
applied_at: 2026-07-09T11:33:28Z
promoted_at: 2026-07-09T15:49:44Z
shadow_mode: false
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
| `2c78314618e48f928a02e6e45b30f1a9528de045d526256622d4798658ffb197` | `SKILL.md` (merged, 212L) |

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


> **Contagens finais S262 (pós-review, autoritativas):** staged = 212 linhas; diff vs live = +84/−0; frontmatter diff_size_added/removed sincronizados. Rail de integridade = pin sha256_of_staged, re-pinado após cada fix.

> **Soak waiver S263 (2026-07-09):** 7-day parallel-shadow window waived by explicit Owner decision (single-user dogfood; pre-authorized skip semantics of --promote --force-recover). SP-026/SP-034 (AFTER-C) excluded — they keep the full soak.
