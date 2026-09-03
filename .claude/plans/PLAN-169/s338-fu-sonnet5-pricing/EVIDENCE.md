# EVIDENCE — pack `sonnet5-pricing-fu` (S338, 2026-09-01)

Repo: `/Users/joaocanhada/canhada-labs/ceo-orchestration`. Live tree NEVER
touched by this agent (no git add/commit/reset/stash/checkout; only
`worktree add/remove`, `rev-parse`, `status`, `log`, `diff` read-only). HEAD
moved twice during the work by orchestrator/Owner commits: `dc72bf1` ->
`6160578` (S337 package) -> `f0e98de` (fable51 ceremony materials).
`git diff --name-only dc72bf1 f0e98de` intersects NEITHER this pack's 10 paths
NOR the fable51 touched paths (both intersections empty), so the derived diff
is byte-identical on all three bases.

Final shadow worktree (scratch, disposable, LEFT IN PLACE):
`/private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/f52979b1-4c83-4346-9217-5f07d8d51bde/scratchpad/shadow-sonnet5fu`
= HEAD `f0e98de` + fable51 (shadow-only commit `cede667` "shadow: fable51 base")
+ this pack applied as uncommitted changes.

Pack dir: `/Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-169/s338-fu-sonnet5-pricing/`
(`apply-sonnet5-pricing-fu.py`, `DESIGN-SONNET5-FU-S338.md`, `EVIDENCE.md`,
`rail-round-{1,2,3}.md`, `codex-r{1,2,3}.txt`). Untracked in the live tree; the
orchestrator commits.

## Base (HEAD + fable51) — commands (final derivation)

```
git -C <REPO> worktree remove --force <SHADOW>                 # iterate: always from a clean tree
git -C <REPO> worktree add --detach <SHADOW> HEAD               # HEAD = f0e98de at the final run
python3 <REPO>/.claude/plans/PLAN-169/s338-ceremony-fable51/apply-fable51-edits.py --root <SHADOW>
    -> "apply-fable51-edits: 55 edicao(oes) aplicadas em 30 path(s)"
git -C <SHADOW> -c user.name=shadow -c user.email=shadow@example.invalid commit -q -am "shadow: fable51 base"
    -> cede667 (detached; lives only in the worktree)
shasum -a 256 apply-fable51-edits.py -> c1bb92068f409b6257325b6108129e410dcb10a423c2ac51ab36d252bdf228f4
shasum -a 256 apply-sonnet5-pricing-fu.py -> e63144f82b116a214e6a6777b1fb42aa4a5225629f01285eeb8dc9e750634248
```
Note: the fable51 script is iterated by its own pack (an earlier shadow of this
session saw 29 paths, the final one 30); every anchor of this pack matched on
every version seen. A future fable51 change that moves an anchor makes this
script REFUSE by name (nothing written) — re-derive then.

## Derivation — anchors, apply, double-application guard

```
python3 <PACK>/apply-sonnet5-pricing-fu.py --root <SHADOW> --check-only
    -> "21 edit(s) applicable in 10 path(s); nothing written"   (rc 0)
python3 <PACK>/apply-sonnet5-pricing-fu.py --root <SHADOW>
    -> "21 edit(s) applied in 10 path(s)"                        (rc 0)
python3 <PACK>/apply-sonnet5-pricing-fu.py --root <SHADOW> --check-only   (second time, v1 run)
    -> "REFUSED" (rc 1): 17 of the 21 anchors report 0x; the 4 ADDITIVE anchors (fleet import block, fleet opus48 block, cost-of-operation Gen-5 line, build_cm test anchor) remain 1x by construction — for those, idempotency rests on the MARKER check (refusal verified: tree hash unchanged) [P3 do refutador, S338]
git -C <SHADOW> diff --stat -> 10 files changed, 235 insertions(+), 115 deletions(-)
```
(v1 of the script — 19 edits / 8 paths — was the tree rail rounds 1-2 reviewed;
v2 adds the round-2 cures: the `_MM_TIERS` sonnet-5 tier + 2 tests, and the
routing-cell supersession note.)

## Canonicality oracle (live-tree oracle, every touched path + the script)

```
python3 .claude/hooks/check_canonical_edit.py --is-canonical <path>   -> all "\t0" (FREE)
.claude/scripts/audit-telemetry.py  .claude/scripts/ceo-cost.py  .claude/scripts/budget-summary.py
.claude/scripts/value-dashboard.py  .claude/scripts/cost-table.yaml  .claude/scripts/build-canonical-models.py
.claude/scripts/tests/test_model_fleet_presence.py  .claude/scripts/tests/test_build_canonical_models.py
docs/cost-of-operation.md  docs/CEO-MODEL-ROUTING.md
(docs/provider-pricing.md 0 — checked, NOT touched)
.claude/plans/PLAN-169/s338-fu-sonnet5-pricing/apply-sonnet5-pricing-fu.py 0
```
No SIGN/LAND material required.

## POSITIVE CONTROL — rewritten tests vs UNCURED sources (RED)

Clean shadow at the fable51 base (HEAD f0e98de), then ONLY the two test files:
```
python3 <PACK>/apply-sonnet5-pricing-fu.py --root <SHADOW> \
   --only .claude/scripts/tests/test_model_fleet_presence.py --only .claude/scripts/tests/test_build_canonical_models.py
    -> "8 edit(s) applied in 2 path(s)"
cd <SHADOW> && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
   .claude/scripts/tests/test_model_fleet_presence.py .claude/scripts/tests/test_build_canonical_models.py
    -> 7 failed, 60 passed
FAILED test_model_fleet_presence.py::TestAuditTelemetryFleetPresence::test_sonnet5_has_no_dated_row
FAILED test_model_fleet_presence.py::TestAuditTelemetryFleetPresence::test_sonnet5_standard_rate_on_both_sides_of_2026_09_01   (18.00 != 12.00 at ts=2026-09-01)
FAILED test_model_fleet_presence.py::TestCeoCostFleetPresence::test_sonnet5_standard_rate_on_both_sides_of_2026_09_01           (3.00 leg after the cutoff)
FAILED test_model_fleet_presence.py::TestBudgetSummaryFleetPresence::test_sonnet5_standard_rate_on_both_sides_of_2026_09_01     (0.018 != 0.012 at ts=2026-09-01)
FAILED test_model_fleet_presence.py::TestCostTableFleetPresence::test_sonnet5_row_standard_rate                                 (table still 3.00/15.00)
FAILED test_build_canonical_models.py::TestReconcile::test_mm_tier_sonnet5_is_standard_2_10_and_generic_sonnet_kept            (generic $3/$15 tuple returned)
FAILED test_build_canonical_models.py::TestReconcile::test_reconcile_sonnet5_row_at_standard_rate_is_clean                      (7 findings: 5 tier + 2 cost-table)
```
The 4 synthetic-mechanism tests PASS on the uncured base by design (they
exercise the mechanism, which exists on both sides); the 7 cure tests turn.
(The v1 control on base dc72bf1 with the first test file only: 5 failed /
25 passed — same five.) The shadow was then REMOVED and re-created clean before
the full application — no hand edit ever touched it.

## BATTERY (final tree, AFTER the last edit; every command re-run on it)

```
cd <SHADOW>
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  .claude/scripts/tests/test_model_fleet_presence.py .claude/scripts/tests/test_a4_pricing_doctrine.py .claude/scripts/tests/test_budget_summary.py
    -> 86 passed                                (test_model_fleet_presence alone: 34 tests on the final tree — fable51 base 32, HEAD 24 [P3 do refutador, S338])

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  .claude/scripts/tests/test_audit_telemetry.py .claude/scripts/tests/test_ceo_cost.py .claude/scripts/tests/test_ceo_cost_stream.py \
  .claude/scripts/tests/test_ceo_info.py .claude/scripts/tests/test_token_estimator.py .claude/scripts/tests/test_value_dashboard.py \
  .claude/scripts/tests/test_build_canonical_models.py tests/unit/test_value_dashboard_emit.py \
  .claude/hooks/tests/test_tier_policy_sonnet5_routing_pin.py .claude/hooks/tests/test_audit_emit.py \
  .claude/hooks/tests/test_audit_emit_coverage.py .claude/hooks/tests/test_session_end_memory_delta.py
    -> 499 passed, 1 xfailed                    (every other test file that imports/reads a touched module — grep of the tests dirs; was 497 before the 2 new tests)

python3 .claude/scripts/rate-card-calibrate.py --check
    -> "clean — all 5 ratified rates match cost-table.yaml + provider-pricing.md"   rc 0
python3 .claude/scripts/check-test-env-hygiene.py
    -> "OK: test-env hygiene clean (337 flagged files, all allowlisted)."          rc 0
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile audit-telemetry.py ceo-cost.py budget-summary.py value-dashboard.py \
  build-canonical-models.py test_model_fleet_presence.py test_build_canonical_models.py            -> rc 0
python3 .claude/scripts/build-canonical-models.py --reconcile   (advisory CLI on the shipped canonical file)
    -> only PRE-EXISTING divergences (12, across claude-opus-4-8-fast / -4-7-fast / -4-6-fast; no sonnet-5 row exists there); output hash IDENTICAL live vs final, so untouched by this pack [P3 do refutador, S338]
```
Behavioural checks (not grep): `rate-card-calibrate.parse_cost_table(cost-table.yaml)["claude-sonnet-5"]`
-> `{'input_per_mtok': 2.0, 'output_per_mtok': 10.0}`; `token-estimator.py check-pricing-staleness --json`
-> `{"stale": false, "valid_until": "2026-09-13"}`; `ceo-info.py --verify-models` (static)
-> `yellow | rate-card gap for allowlist member(s): ['claude-opus-5']` (identical before/after — pre-existing, unrelated).
Residual `$3/$15` mentions on the touched surfaces after the patch: only Sonnet 4.6 rows
(correct at $3/$15) and the notes this pack itself writes ("will not occur" / "superseded").

## PAIR-RAIL (codex exec review --uncommitted, from inside the shadow)

| round | tree | verdict | findings | tree sha before/after |
|---|---|---|---|---|
| r1 | dc72bf1 + fable51 + pack v1 | APPROVE | 0 (no `Full review comments` block) | `3f706c14…` = `3f706c14…` TREE-INTACT |
| r2 | same tree (confirmation) | CHANGES-REQUESTED | 2 P2, both REAL: `_MM_TIERS` generic sonnet tier $3/$15 (latent, cured: sonnet-5 tier + 2 tests); pointer to the dated `substrate-adopt-2026-08.md` (cured in the routing cell; record untouched per brief) | `3f706c14…` = `3f706c14…` TREE-INTACT |
| r3 | f0e98de + fable51 + pack v2 (re-derived) | APPROVE | 0 (no `Full review comments` block) | `4b7e59ed…` = `4b7e59ed…` TREE-INTACT |

Raw outputs: `codex-r1.txt` [saída bruta, NÃO versionada — scratchpad S338 `codex-logs/s338-fu-sonnet5-pricing/`] (5.816 lines), `codex-r2.txt` [saída bruta, NÃO versionada — scratchpad S338 `codex-logs/s338-fu-sonnet5-pricing/`] (9.809), `codex-r3.txt` [saída bruta, NÃO versionada — scratchpad S338 `codex-logs/s338-fu-sonnet5-pricing/`]
(5.906); records: `rail-round-{1,2,3}.md`. Last verdict: **APPROVE** (r3).

## Aplicado — S340 (2026-09-02)

Aplicado na ÁRVORE VIVA pelo orquestrador da noite S340, sobre a base
HEAD `400638e` (a wave `wave-fable51` — dependência de âncora deste pack —
landou como `ab56e76`; `400638e` é o closeout do estudo do PLAN-186 que
veio depois e não toca nenhum dos 10 paths). Árvore limpa antes de aplicar
(`git status --porcelain` vazio).

### As duas mensagens do `--check` (verbatim)

Antes (rc 0):

```
apply-sonnet5-pricing-fu: 21 edit(s) applicable in 10 path(s); nothing written
```

Aplicação (rc 0): `21 edit(s) applied in 10 path(s)` — os 10 paths da
tabela de sítios, e `git status --short` listou EXATAMENTE esses 10.

Depois, segundo `--check` (rc **1**, guarda de dupla aplicação — o mesmo
comportamento já documentado acima para o shadow):

```
apply-sonnet5-pricing-fu: REFUSED
  - <17 âncoras> anchor found 0x, expected 1 — ...
  - <os 10 paths> already contains 'PLAN-169 S338 follow-up' — tree already patched?
```

Os 4 sítios ADITIVOS permanecem 1x por construção; para eles a
idempotência repousa no marcador — e o marcador disparou nos 10 paths.

### Bateria (na árvore final, DEPOIS da última edição)

```
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  .claude/scripts/tests/test_model_fleet_presence.py .claude/scripts/tests/test_a4_pricing_doctrine.py \
  .claude/scripts/tests/test_budget_summary.py .claude/scripts/tests/test_build_canonical_models.py
    -> 119 passed                                                   rc 0

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider <15 arquivos consumidores>
  (adapters/live/test_cost.py, test_audit_emit.py, test_audit_emit_coverage.py,
   test_session_end_memory_delta.py, test_tier_policy_sonnet5_routing_pin.py,
   test_audit_telemetry.py, test_ceo_cost.py, test_ceo_cost_stream.py,
   test_ceo_cost_transcripts.py, test_ceo_info.py, test_rate_card_calibrate.py,
   test_success_receipt.py, test_token_estimator.py, test_value_dashboard.py,
   tests/unit/test_value_dashboard_emit.py)
    -> 555 passed, 1 xfailed (pré-existente)                        rc 0

python3 .claude/scripts/rate-card-calibrate.py --check
    -> "clean — all 5 ratified rates match cost-table.yaml + provider-pricing.md"   rc 0
python3 .claude/scripts/budget-summary.py                                            rc 0
python3 -m py_compile <os 7 .py tocados>                                             rc 0
python3 .claude/scripts/validate_governance_fast.py -> errors 0 / warnings 0         rc 0
```

O conjunto dos 15 consumidores foi DERIVADO por censo (`grep -rl` dos
nomes de módulo e de `cost-table` em `.claude/scripts/tests/`,
`.claude/hooks/tests/` e `tests/`), não recordado — o mesmo método da
derivação original, re-executado nesta base.

Gates de corpus sobre a árvore STAGED e rodadas de pair-rail desta
aplicação: ver o corpo do commit desta entrega. rail: see the commit body.
