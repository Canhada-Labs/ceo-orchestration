# NOTICE — `.claude/skills/domains/community/`

> **Purpose:** attribution ledger for curated external skills imported
> into this domain under the PLAN-033 pipeline.
> **Lifecycle:** each import appends one row (automated by
> `.claude/scripts/import-skill.py --notice`). Rows are append-only;
> deletion requires a new SP-NNN chain.

## Domain posture

The `community` domain is opt-in adopter space for externally-curated
skills. Each skill passes:

1. `skill-import-rubric.py` — quality gate (≥512 non-ws bytes,
   frontmatter valid, checklist present, no forbidden keywords, no
   bidi / zero-width / BOM).
2. Owner-signed SP-NNN chain — per-skill review captured in
   frontmatter field `sp_chain: SP-NNN` + `owner_sha256: <hex>`.
3. License attribution — `source:` + `license:` frontmatter fields
   AND a row in this file.

## License attribution roster

_No skills imported yet — this domain is seeded by PLAN-033 Phase 2
tooling; bulk import is Owner-gated (see
`.claude/plans/PLAN-033/OWNER-CLOSEOUT-ACTIONS.md`)._

Format of future rows:

```
- `community/skills/<slug>/SKILL.md` — imported from `<upstream>`
  under `<license-spdx>` via `<SP-NNN>` on `<ISO-timestamp>`
```

## Upstreams considered for initial batch (Sprint 27)

- `sickn33/antigravity-awesome-skills` — 631 indexed skills;
  ~150-180 pass the rubric per PLAN-026 finding 08. The actual
  PLAN-033 Phase 3 imports (advanced-evaluation, agent-evaluation,
  agentic-actions-auditor below) were taken from this upstream at
  branch `@main`. Earlier PLAN-026 audit notes and `team.md` §Domain
  `community` occasionally refer to the `nextlevelbuilder/`
  namespace — those were either forks or early rename mis-citations
  and have been corrected in PLAN-045 F-11-04 closure.
- Other AI-collaboration ecosystems — case-by-case per Owner.

## Known forbidden content (first-pass filter)

- Phishing campaign / credential harvesting tutorials
- Malware / exploit-kit development walkthroughs
- Jailbreak-Claude / jailbreak-GPT guides
- Ransomware tutorials
- Authentication-bypass "how-to"s

These first-pass filters do NOT exempt the Owner from per-skill review;
they're a triage convenience only.

## Cross-references

- `PLAN-033` — plan defining the pipeline.
- `ADR-060` — architectural decision record (canonical promotion
  pending Owner sentinel).
- `.claude/scripts/skill-import-rubric.py` — quality validator.
- `.claude/scripts/import-skill.py` — provenance + SP-NNN wrapper.
- `docs/MECHANISM-SELECTION.md` §4 — why a "skill" is the right
  mechanism here.
- `PROTOCOL.md` §Spawn Protocol — skills are loaded into spawn prompts
  via Format A / Format B (ADR-051).

## Kill-switch

`CEO_ANTIGRAVITY_SYNC=0` (environment) — community-domain imports
inactive until unset + Owner re-authorizes the SP chain.
- `community/skills/advanced-evaluation/SKILL.md` — imported from `sickn33/antigravity-awesome-skills@main` under `MIT` via `SP-000-OWNER-AUTH-2026-04-20` on 2026-04-20T09:09:55Z
- `community/skills/agent-evaluation/SKILL.md` — imported from `sickn33/antigravity-awesome-skills@main` under `MIT` via `SP-000-OWNER-AUTH-2026-04-20` on 2026-04-20T09:09:55Z
- `community/skills/agentic-actions-auditor/SKILL.md` — imported from `sickn33/antigravity-awesome-skills@main` under `MIT` via `SP-000-OWNER-AUTH-2026-04-20` on 2026-04-20T09:09:55Z

### PLAN-045 Wave-7 — 2026-04-21

Retrofitted `imported_sha:` frontmatter on 3 community-tier SKILL.md
files per F-11-03. Upstream pinning previously carried only in this
ledger; now redundantly encoded in the skill frontmatter itself.
Applied under Owner canonical sentinel.
