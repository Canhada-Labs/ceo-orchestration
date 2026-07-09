---
id: SP-031
skill_slug: blockchain-security-audit
archetype: smart-contract-auditor
proposed_at: 2026-07-07T06:07:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: 68
diff_size_removed: 0
sha256_of_diff: null
sha256_of_staged: 6b1ff063fec023e3b3748bb75df255da11309f1a5fb3373757fa367677758006
claims_declared: false
status: shadow
approved_by: AE9B236FDAF0462874060C6BCFCFACF00335DC74
applied_at: 2026-07-09T11:33:28Z
promoted_at: null
shadow_mode: true
proposal_type: adapt-merge-enrichment
after_wave_c: false
contains_code: true
upstream_sources:
  - affaan-m/ecc@81af4076 skills/nodejs-keccak256/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/fintech/skills/blockchain-security-audit/
---

# SP-031 — skill patch proposal (Wave G ADAPT merge)

**Target:** `.claude/skills/domains/fintech/skills/blockchain-security-audit/SKILL.md`
**Archetype:** smart-contract-auditor (sign-off delegated to security-engineer)
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (1 upstream skill folded into an
existing catalog skill; no new skill file; catalog count unchanged)

## Rationale

Wave G materialized-merge **row 10**: fold `affaan-m/ecc@81af4076`
`skills/nodejs-keccak256/` (matrix quality **q4**) into `blockchain-security-audit`
— the real footgun that **NIST SHA3-256 ≠ Ethereum Keccak-256** (the pre-standard
padding differs), demonstrated with executable proof. Additive; staged file is
535 lines vs. the 492-line live skill (net +43 lines).

## Provenance note

Clean-room ADAPT (upstream informed scope; prose original, zero ECC strings).
Provenance in the root `NOTICE` Wave G section
(`affaan-m/ecc@81af4076 skills/nodejs-keccak256/`, MIT) + `inspired_by:`
frontmatter. Carries upstream content → rides the **import gate** plus
`/skill-review`.

**Contains executable code (`contains_code: true`).** The merge includes a
runnable proof fence (SHA3-256 vs Keccak-256 hash divergence). This triggers the
`CEO_SKILL_PATCH_ALLOW_CODE=1` human-review route — the reviewer must confirm the
snippet is a self-contained demonstrator (no network, no upstream fetch/exec) and
import-gate check (d) (ported-script safety) is clean. `scan-injection.py` over
all staged Wave G files (2026-07-07): no non-zero exit; enforcing checks at the
ceremony.

Rollback-safe: promote replaces exactly one file (SKILL.md).

## Patch source (staged tree, sha256-pinned)

`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/fintech/skills/blockchain-security-audit/`:

| sha256 | file |
|---|---|
| `0f5a91f905447e711b371f13909e51864eb2e8414df2ccc6d226aff4fffe7c7f` | `SKILL.md` (merged, 560L) |

## Proposed diff (summary — the full diff is NOT embedded)

```
git diff --no-index .claude/skills/domains/fintech/skills/blockchain-security-audit/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/fintech/skills/blockchain-security-audit/SKILL.md
```

## Landing mechanics (wake-up ceremony — /skill-review + import gate)

1. **Import gate + /skill-review** — `check-imported-skill.py --skill <staged
   SKILL.md> --notice NOTICE`; confirm check (d) ported-script safety is clean for
   the proof fence. Human review ON TOP with `CEO_SKILL_PATCH_ALLOW_CODE=1`
   consciously set. Verify the sha256 pin.
2. **Approve (shadow apply)** — copy staged SKILL.md →
   `.../blockchain-security-audit/SKILL.md.shadow.md`; set `status: shadow`,
   `applied_at`, `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c)** — live SKILL.md keeps serving;
   `skill-health.py` telemetry is the regression signal.
4. **Promote** — `mv SKILL.md.shadow.md SKILL.md` under the SKILL.md sentinel gate;
   replace `SP-NNN` in the merged changelog with `SP-031`; set `status: promoted`,
   `promoted_at`.

## Honest residuals

- Ships an executable proof fence — the human-review code route is mandatory,
  not optional.
- `scan_injection_pass: true` = advisory exit-0, not a full injection audit.
- +43 lines paid per activation (not a Wave C pilot); small, acceptable for q4.


> **Contagens finais S262 (pós-review, autoritativas):** staged = 560 linhas; diff vs live = +68/−0; frontmatter diff_size_added/removed sincronizados. Rail de integridade = pin sha256_of_staged, re-pinado após cada fix.
