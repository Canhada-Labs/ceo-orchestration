---
id: SP-026
skill_slug: testing-strategy
archetype: qa-architect
proposed_at: 2026-07-07T06:02:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: null
diff_size_removed: null
sha256_of_diff: 23b8dfcc034e787762887f7bc65ee07059017f536975196d56c3e5afd97a14bd
sha256_of_staged: 87820ab038e8ebf659aefd6c2a6b9c5a9b7a6330c5334c4dd08330f9b8221715
claims_declared: false
status: promoted
approved_by: AE9B236FDAF0462874060C6BCFCFACF00335DC74
applied_at: 2026-07-09T16:32:58Z
promoted_at: 2026-07-09T22:07:19Z
shadow_mode: false
proposal_type: adapt-merge-enrichment
after_wave_c: true
depends_on: SP-022
upstream_sources:
  - affaan-m/ecc@81af4076 skills/react-testing/
  - affaan-m/ecc@81af4076 skills/tdd-workflow/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/testing-strategy/
---

# SP-026 — skill patch proposal (Wave G ADAPT merge — 2 sources, AFTER-C)

**Target:** `.claude/skills/core/testing-strategy/SKILL.md`
**Archetype:** qa-architect
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (TWO upstream skills folded;
net-new `references/*.md`; catalog count unchanged). **AFTER-C: applies on top of
the SP-022 Wave-C loader — SP-022 must be PROMOTED first.**

## ⚠ AFTER-C ordering (debate A NTH-4) — hard precondition

This merge is expressed as a patch (`SKILL.md.wave-G.patch`) that applies **on top
of the post-Wave-C core** (SP-022's lean loader + `references/`). Its `@@` hunks
are anchored to the SP-022 loader text (e.g. the "Reference Files — progressive
disclosure (PLAN-153 Wave C)" section), NOT the pre-Wave-C live SKILL.md.
**Do not dispatch this SP until SP-022 is promoted** — applying it against the
current live SKILL.md will fight the restructure and the hunks will not land
cleanly. The staged `SKILL.md.wave-G-proposed` is the fully-merged loader
(post-C + this merge) provided as the shadow source once SP-022 is live.

## Rationale

Wave G materialized-merge **rows 3 and 18**:

- **row 3 — react-testing** (q4): RTL query-priority, MSW network mocking, axe
  a11y, and the unit-vs-E2E boundary — a real gap for the frontend team. Lands as
  `references/react-component-testing.md` + a loader pointer row + activation
  bullet. **(⚠DELTA: the plan prose loosely grouped react-testing under "frontend",
  but the matrix overlap names `core/testing-strategy` and that wins.)**
- **row 18 — tdd-workflow** (q4): a plan-handoff section that treats `*.plan.md`
  as **untrusted input** (anti-injection discipline) plus the RED/GREEN/REFACTOR
  cycle. Lands as `references/tdd-red-green-cycle.md` + a loader pointer row +
  activation bullet.

The loader delta bumps `version: 1.0.0 → 1.1.0`, extends the `description`, adds
two `## When to Activate` bullets, and adds a "Merged-in references (Wave G)"
pointer block. No pre-existing content is rewritten.

## Provenance note

Clean-room ADAPT for both sources (upstream informed scope; prose original, zero
ECC strings). Provenance recorded as **two** rows in the root `NOTICE` Wave G
section (react-testing, tdd-workflow) plus `inspired_by:` frontmatter. Carries
upstream content → rides the **import gate** plus `/skill-review`.
`scan-injection.py` over all staged Wave G files (2026-07-07): no non-zero exit;
enforcing checks at the ceremony.

Rollback-safe: promote replaces exactly one file (SKILL.md) and adds two inert
`references/*.md`; reverting restores the SP-022 loader and removes the two new
references.

## Patch source (staged tree, sha256-pinned)

`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/testing-strategy/`:

| sha256 | file |
|---|---|
| `e56793e0c19938d050d24827bfbb350964eeadcf22f8eb872b9a862caed4e803` | `SKILL.md.wave-G.patch` (loader delta, 96L — applies on SP-022 core) |
| `87820ab038e8ebf659aefd6c2a6b9c5a9b7a6330c5334c4dd08330f9b8221715` | `SKILL.md.wave-G-proposed` (fully-merged loader, 178L — shadow source) |
| `a3ea3cafbf65f6b95c6df5dff6129c212d7b5f670fb71aa52c4af3b56da8d0f3` | `references/react-component-testing.md` (273L, net-new) |
| `1ff1099ed1a5067f212614a27e8fc8c256ff3ba2199ad0df1ea240a346660946` | `references/tdd-red-green-cycle.md` (199L, net-new) |

## Proposed diff

The loader delta IS pinned as a real unified diff (`SKILL.md.wave-G.patch`,
sha above). Its header carries the ADR-031 apply recipe. It contains removal
lines (`-version: 1.0.0`), so `skill-patch-apply.py` cannot apply it (removal-line
contract); apply via `git apply` under the SKILL.md sentinel, or use the
fully-merged `SKILL.md.wave-G-proposed` as a whole-file shadow. Verify against the
post-SP-022 loader:

```
# after SP-022 is promoted:
git apply --check .claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/testing-strategy/SKILL.md.wave-G.patch
```

## Landing mechanics (wake-up ceremony — /skill-review + import gate, AFTER SP-022)

0. **Precondition:** SP-022 promoted (post-Wave-C loader live). If not, STOP.
1. **Import gate + /skill-review** — run `check-imported-skill.py` over the merged
   loader + the two new references; human review ON TOP. Verify all four sha256
   pins.
2. **Approve (shadow apply)** — after review + detached GPG signature, produce the
   shadow either by `git apply`-ing the patch to the live (post-SP-022) SKILL.md
   into `SKILL.md.shadow.md`, or by copying `SKILL.md.wave-G-proposed` →
   `SKILL.md.shadow.md`; land the two `references/*.md` directly (not canonical-
   guarded, inert until the loader points at them). Set `status: shadow`,
   `applied_at`, `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c)** — live SKILL.md keeps serving;
   `skill-health.py` telemetry is the regression signal.
4. **Promote** — `mv SKILL.md.shadow.md SKILL.md` under the SKILL.md sentinel gate
   (set `CEO_SKILL_PATCH_SHA` to this diff's sha); replace `SP-NNN` in the merged
   changelog with `SP-026`; set `status: promoted`, `promoted_at`.

## Honest residuals

- Hard dependency on SP-022 promotion; dispatching early breaks the hunks.
- `scan_injection_pass: true` = advisory exit-0, not a full injection audit — the
  `tdd-workflow` "untrusted `*.plan.md`" section is itself anti-injection content;
  the reviewer confirms it reads as guidance, not a payload.
- The two references are activation-time free until the loader pointer is read on
  demand (progressive disclosure inherited from the SP-022 loader shape).

> **Aplicação manual S263 (2026-07-09):** o patch pinado original não aplica
> no loader promovido (hunks com contexto stale — o loader recebeu os fixes
> do pair-rail S262 depois que o patch foi autorado). O shadow foi construído
> por aplicação manual reconciliada, revisada linha-a-linha (reviewer
> after-c-review + Codex), preservando os fixes S262 e normalizando
> enum/sha da cerimônia. **O conteúdo assinado é o shadow + references nos
> shas abaixo** (o pin antigo do patch fica como registro histórico):
>
> - `d5d9598cc24ffdd37cc270d35f4ffbdd9be2034b110244309a1c785e9300f285` — `.claude/skills/core/testing-strategy/SKILL.md.shadow.md`
> - `49ddcf89e5c1764cc21941ebc922cadbb888957fe96ee516caddcca402ac5deb` — `.claude/skills/core/testing-strategy/references/react-component-testing.md`
> - `16c8377ec8d1101630dd6cb9f2759e9be7bb1d6ef1148f5865f59e8336903670` — `.claude/skills/core/testing-strategy/references/tdd-red-green-cycle.md`
> **Adjudicação S263 (pair-rail):** o Codex round-2 sugeriu remover até os PONTEIROS de proveniência ('recorded in the parent inspired_by frontmatter'). REJEITADO pelo CEO: ponteiro sem identidade upstream, padrão endossado pelo reviewer humano e idêntico ao precedente landado CI-verde da Wave G (ddf2b17). Zero imperativos upstream restantes (confirmado pelo mesmo round).

> **Soak waiver S264 (2026-07-09):** the remaining parallel-shadow window (>= 2026-07-14 per S263) waived by explicit Owner decision, ratified in-session via AskUserQuestion and logged verbatim in PLAN-153 OQ4. Same pre-authorized skip semantics as S263 (--promote --force-recover). Pre-waiver audit sweep of the soak window (applied_at 2026-07-09T16:32Z onward) found zero adverse signal touching this shadow.
