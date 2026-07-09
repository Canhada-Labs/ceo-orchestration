---
id: SP-034
skill_slug: security-and-auth
archetype: security-engineer
proposed_at: 2026-07-07T06:10:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: null
diff_size_removed: null
sha256_of_diff: 69d05b6a09860857771550b2b510f4bcb0e618d1c1972b73c97178393ab57c57
sha256_of_staged: 4f55e3d1ae4669c42e831de8c231f19046e130fe3de1b49ace987b74af1bd66c
claims_declared: false
status: promoted
approved_by: AE9B236FDAF0462874060C6BCFCFACF00335DC74
applied_at: 2026-07-09T16:32:58Z
promoted_at: 2026-07-09T22:07:19Z
shadow_mode: false
proposal_type: adapt-merge-enrichment
after_wave_c: true
depends_on: SP-023
veto_floor_skill: true
upstream_sources:
  - affaan-m/ecc@81af4076 skills/security-review/
  - affaan-m/ecc@81af4076 skills/security-bounty-hunter/
patch_source: .claude/plans/PLAN-153/staged/wave-G/security-and-auth.SKILL.md.patch
---

# SP-034 — skill patch proposal (Wave G ADAPT merge — 2 sources, AFTER-C, VETO-floor)

**Target:** `.claude/skills/core/security-and-auth/SKILL.md`
**Archetype:** security-engineer
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (TWO upstream skills folded;
net-new `references/*.md`; catalog count unchanged). **AFTER-C: applies on top of
the SP-023 Wave-C loader — SP-023 must be PROMOTED first. This is a `/debate`
VETO-floor reviewer skill — extra soak care.**

## ⚠ AFTER-C ordering (debate A NTH-4) — hard precondition

The merge is a unified diff (`security-and-auth.SKILL.md.patch`) whose hunks are
anchored to the **SP-023 Wave-C loader** (its diff header literally names
`.claude/plans/PLAN-153/staged/wave-C/.claude/skills/core/security-and-auth/SKILL.md`
as the `---` side). **Do not dispatch until SP-023 is promoted.** Applying it
against the current live pre-Wave-C SKILL.md will not land.

> **Coupled fix (from SP-023 §Fix-before-apply):** SP-023's staged loader has a
> changelog line that mis-cites `SP-022`; it must read `SP-023`. Because this
> Wave-G patch stacks on that loader, apply SP-023's one-word fix and re-pin
> SP-023 before this patch's hunks are validated.

## Rationale

Wave G materialized-merge **rows 16 and 17**:

- **row 16 — security-review** (q4): a dense FAIL/PASS web/TS checklist plus a
  cloud annex → `references/cloud-and-ci-cd-security.md` (IAM least-privilege,
  cloud secrets + rotation, network posture, CI/CD pipeline with OIDC + scanning
  gates + signed commits/tags, edge/CDN, backup/recovery, consolidated pre-deploy
  gate).
- **row 17 — security-bounty-hunter** (q4): an exploitable/payable lens with a
  low-signal skip list → `references/vulnerability-hunting.md` (reachability-first
  triage, in-scope CWE table, skip list, hunt workflow, report quality gate;
  pairs with the existing `proof-of-exploitability.md`).

The loader delta bumps `version: 1.0.0 → 1.1.0`, adds two `## When to Activate`
bullets, two pointer rows (explicitly flagged **Wave-G enrichment; NOT part of the
verbatim Wave-C split** so the SP-023 line-for-line claim stays scoped), two
`inspired_by:` provenance rows, and two `## Anti-Patterns` rows. No pre-existing
content is rewritten. The loader keeps veto-relevant decision rules inline
(consistent with SP-023's VETO-floor design).

## Provenance note

Clean-room ADAPT for both sources (upstream informed scope; prose original, zero
ECC strings). Provenance recorded as **two** rows in the root `NOTICE` Wave G
section plus the two `inspired_by:` frontmatter rows the patch adds. Carries
upstream content → rides the **import gate** plus `/skill-review`.
`scan-injection.py` over all staged Wave G files (2026-07-07): no non-zero exit;
enforcing checks at the ceremony.

Rollback-safe: promote replaces exactly one file (SKILL.md) and adds two inert
`references/*.md`; reverting restores the SP-023 loader and removes the two new
references. The live skill's `benchmarks/` directory is untouched.

## Patch source (staged tree, sha256-pinned)

Patch at the wave-G root; references under the skill's `references/`:

| sha256 | file |
|---|---|
| `4f55e3d1ae4669c42e831de8c231f19046e130fe3de1b49ace987b74af1bd66c` | `security-and-auth.SKILL.md.patch` (loader delta, 97L — applies on SP-023 core) |
| `a1b644f7f9a19e062802f083808b011bc110397d852681c463877992ecfa3869` | `.claude/skills/core/security-and-auth/references/cloud-and-ci-cd-security.md` (134L, net-new) |
| `3ae618269dd381ad793bbe1c737ba9f28bf1c2887f50c6dd78486de477b533fd` | `.claude/skills/core/security-and-auth/references/vulnerability-hunting.md` (113L, net-new) |

## Proposed diff

The loader delta IS the pinned unified diff (`security-and-auth.SKILL.md.patch`,
sha above; it doubles as `sha256_of_diff` and the sentinel `CEO_SKILL_PATCH_SHA`).
It contains removal lines, so apply via `git apply` under the SKILL.md sentinel
(not `skill-patch-apply.py`). Verify against the post-SP-023 loader:

```
# after SP-023 is promoted (and its SP-022→SP-023 changelog fix applied):
git apply --check .claude/plans/PLAN-153/staged/wave-G/security-and-auth.SKILL.md.patch
```

## Landing mechanics (wake-up ceremony — /skill-review + import gate, AFTER SP-023)

0. **Precondition:** SP-023 promoted (post-Wave-C loader live) AND its
   SP-022→SP-023 changelog fix applied. If not, STOP.
1. **Import gate + /skill-review** — run `check-imported-skill.py` over the merged
   loader + the two new references; human review ON TOP. Verify all three sha256
   pins.
2. **Approve (shadow apply)** — after review + detached GPG signature, `git
   apply` the patch to the live (post-SP-023) SKILL.md into `SKILL.md.shadow.md`;
   land the two `references/*.md` directly (not canonical-guarded, inert until the
   loader points at them). Set `status: shadow`, `applied_at`, `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c).** `security-and-auth` is a
   `/debate` VETO-floor reviewer — pay explicit attention to VETO-floor sessions in
   the window; `skill-health.py` invocations + failure-proxy must not degrade. A
   degraded soak window is grounds to reject promote.
4. **Promote** — `mv SKILL.md.shadow.md SKILL.md` under the SKILL.md sentinel gate
   (`CEO_SKILL_PATCH_SHA` = the patch sha); replace `SP-NNN` in the merged
   changelog with `SP-034`; set `status: promoted`, `promoted_at`.

## Honest residuals

- Hard dependency on SP-023 promotion AND SP-023's own changelog fix; two coupled
  preconditions, both recorded above.
- VETO-floor behavioral risk: an enrichment that pushes reviewers to Read a
  reference could, if mis-worded, dilute inline floor rules — the loader keeps
  floor rules inline and the parallel-shadow soak is the explicit guard.
- `scan_injection_pass: true` = advisory exit-0, not a full injection audit; the
  bounty-hunter material describes attack patterns and needs the same
  documented-example-vs-payload review judgement as SP-032.

> **Aplicação manual S263 (2026-07-09):** o patch pinado original não aplica
> no loader promovido (hunks com contexto stale — o loader recebeu os fixes
> do pair-rail S262 depois que o patch foi autorado). O shadow foi construído
> por aplicação manual reconciliada, revisada linha-a-linha (reviewer
> after-c-review + Codex), preservando os fixes S262 e normalizando
> enum/sha da cerimônia. **O conteúdo assinado é o shadow + references nos
> shas abaixo** (o pin antigo do patch fica como registro histórico):
>
> - `50cd673fddd5b3ea5168c1132bb8ef14871181d7931bc1ff40f3f6af94b99a80` — `.claude/skills/core/security-and-auth/SKILL.md.shadow.md`
> - `802a4b4b09594737d05ecedb02862ddf68cd2a0c04c1b70016c294b255f3ecdc` — `.claude/skills/core/security-and-auth/references/cloud-and-ci-cd-security.md`
> - `182b6dc3319dedf375ad220ae8ce9e792f694067ef394469084648b9683efeed` — `.claude/skills/core/security-and-auth/references/vulnerability-hunting.md`
> **Adjudicação S263 (pair-rail):** o Codex round-2 sugeriu remover até os PONTEIROS de proveniência ('recorded in the parent inspired_by frontmatter'). REJEITADO pelo CEO: ponteiro sem identidade upstream, padrão endossado pelo reviewer humano e idêntico ao precedente landado CI-verde da Wave G (ddf2b17). Zero imperativos upstream restantes (confirmado pelo mesmo round).

> **Soak waiver S264 (2026-07-09):** the remaining parallel-shadow window (>= 2026-07-14 per S263) waived by explicit Owner decision, ratified in-session via AskUserQuestion and logged verbatim in PLAN-153 OQ4. Same pre-authorized skip semantics as S263 (--promote --force-recover). Pre-waiver audit sweep of the soak window (applied_at 2026-07-09T16:32Z onward) found zero adverse signal touching this shadow.
