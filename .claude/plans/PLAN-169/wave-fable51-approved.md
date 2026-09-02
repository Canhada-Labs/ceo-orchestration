# wave-fable51 — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`). O binding é o `Patch-sha256` (land por PATCH, sem
> `MANIFEST-*`). O bloco `Scope:` é **DERIVADO** por
> `PLAN-183/w5-ceremony/finalize_patch.py` a partir de `git apply --numstat` —
> nunca escrito à mão. O `Anchor-SHA` é preenchido pelo
> `OWNER-S338-FABLE51-SIGN.sh` no momento da assinatura; o
> `OWNER-S338-FABLE51-LAND.sh` aborta no G1 se não casar. Reescrever um byte
> deste arquivo depois de assinar invalida o `.asc`.

Plans: PLAN-169
Wave: wave-fable51 (PLAN-169 — cerimônia `adopt-fable-5.1`, ratificada pelo Owner na abertura da S338 por AskUserQuestion: **rota (c) de três** — `claude-fable-5-1` entra SÓ no `AVAILABLE_MODELS_WORKING_SET` do ADR-149 (Amendment 2), no FIM; VETO floor, fallback chain e o pin `model` dos três espelhos ficam INALTERADOS. Os espelhos independentes que `test_adr149_validator_parity.py` amarra por igualdade de conjunto viajam no mesmo patch, e o `upgrade.sh` ganha a lista `superseded` para que os adopters v1.2.0/v1.3.0 — que shiparam a lista de 6 ids — recebam o sétimo id em vez de serem lidos como ADOPTER-CUSTOMIZED)
Patch: .claude/plans/PLAN-169/s338-ceremony-fable51/WFABLE51.patch
Patch-sha256: eb46ef0a42a272bdb8bf7677c89b28a4a6928052d73a534d6dbac9da45e1ca67
Patch-base: 6160578c0518db43cba6804996ee58fe2427e229
Anchor-SHA: 6325f850de8deefc4aa62bc7487a2c6f1c7c2929
Data: 2026-09-02

## O que esta wave entrega

**Cinco arquivos canônicos** e **vinte e cinco livres** que só são verdadeiros
juntos — todos DERIVADOS de um único material versionado,
`s338-ceremony-fable51/apply-fable51-edits.py` (55 edições com âncora exata
e contagem declarada; o LAND prova `HEAD + script == patch` byte a byte):

1. **`.claude/adr/ADR-149-model-id-allowlist.md`** (canônico — a FONTE):
   `claude-fable-5-1` APPENDED AT END no `AVAILABLE_MODELS_WORKING_SET`
   (regra de ordem da A1.1) + **Amendment 2** registrando os fatos da doc
   oficial (id dateless, $10/$50, 1M ctx, cache hits 0.025× = $0.25/MTok
   pela página de pricing), a decisão (rota c), o que NÃO decide (floor,
   routing, pin) e o FU do Sonnet 5 (intro virou padrão).
2. **`.claude/settings.json`** (canônico, KERNEL) e
   **`templates/settings/settings.base.json`** (canônico): `availableModels`
   regenerado do ADR — `generate-available-models.py --check` responde
   `MATCH (7 ids, ADR order preserved)`; `model` e `fallbackModel` intactos.
   O `settings.user.json` NÃO muda: a `_derivation` exclui `availableModels`
   por desenho (`gen-settings-user-template.py --check` rc 0).
3. **`.claude/scripts/validate-governance.sh`** (livre, MEMBRO do manifesto
   ADR-192) — case-arm do lint de `model:` ganha o id; o sha do membro é
   re-derivado em **`.claude/governance/gate-scripts-manifest.txt`**
   (canônico) no MESMO patch (lição S326; `shasum -a 256 -c` rc 0).
4. **`.claude/scripts/tier_policy_cli/_types.py`** (`VALID_MODEL_IDS` 6→7)
   e **`scripts/local/smoke-install-parity.sh`** (`ALLOWED_MODELS` +
   `EXPECTED_AVAILABLE`) — os outros dois espelhos independentes que a
   paridade exige por igualdade de conjunto.
5. **`scripts/upgrade.sh`** (canônico): `_T54_BASELINES_JSON.availableModels`
   ganha `"superseded": [[a lista de 6 ids de v1.2.0/v1.3.0]]` e `"new"` de 7;
   a política de 3 estados ganha o ramo `matched SUPERSEDED shipped
   baseline -> new baseline` (byte-exato, ordem incluída — array
   reordenado segue PRESERVED). Sem isto nenhum adopter v1.2.0/v1.3.0
   receberia o 7º id — em SILÊNCIO: a parity e2e classifica `settings.json`
   como divergência ACEITA («keys, not bytes») e a CI não pegaria.
6. **Custo/telemetria** (livres — a classe T1.5 «modelo da frota precificado
   a $0 em silêncio»): `cost-table.yaml`, `audit-telemetry.py`,
   `budget-summary.py`, `ceo-cost.py`, `value-dashboard.py` ganham a linha
   `claude-fable-5-1` a $10/$50; `detectors/overpowered.py` e
   `wasteful_thinking.py` enxergam o 5.1 como modelo grande;
   `optimizer/model_normalize.py` ganha o alias `fable-5-1` (minor distinto,
   nunca dobrado em `fable-5`). **Cache-read RESOLVIDO na página oficial de
   pricing (2026-09-01): Fable 5.1 = 0.025× do input = $0.25/MTok**, o ÚNICO
   modelo fora do 0.1× — `budget-summary.py` (a única superfície que
   precifica cache-read) ganha um multiplicador POR MODELO (rail r1 P2) e,
   quando o `meta.model` é o alias bare `fable` (agora AMBÍGUO com dois ids
   Fable), cai para o `message.model` exato do transcript em vez de TBD
   (rail r2 P2); `build-canonical-models.py` deixa de colapsar uma versão
   MINOR no row da base pelo prefixo — só pins DATADOS resolvem, o 5.1 fica
   UNKNOWN (flag, nunca palpite) até o Owner re-fetchar a tabela (rail r2 P2).
   `success-receipt.py` — o espelho de preço dos RECIBOS era pré-gen-5 (sem
   fable-5, opus-5, sonnet-5 nem opus-4-8): em sessão mista o total numérico
   descartava em silêncio todo gasto da frota corrente; ganha as linhas da
   frota nas taxas do budget-summary + guarda de presença (rail r3 P1).
7. **Tier-policy** (livre, rail r1 P1): `tier_policy_cli/learn.py`
   `_tier_rank` ranqueia o 5.1 acima do Fable 5 — sem isso um id admitido
   em `VALID_MODEL_IDS` ranqueava -1 e uma saída dele assinaria `promote`,
   passando pelo gate de demote assinado; teste de PARIDADE allowlist↔ladder
   fecha a classe para o próximo append.
8. **Testes** (livres): `test_model_fleet_presence.py` (frota + rates +
   detectors + linha do cost-table + multiplicador de cache + spawn nativo
   sintético com meta `fable`), `test_generate_available_models.py`
   (working set + fixture), `test_a4_pricing_doctrine.py`,
   `tier_policy_cli/tests/test_types.py` (6→7), `test_learn_mutation.py`
   (rank + paridade), `test_build_canonical_models.py` (minor ≠ pin datado),
   `test_adr149_validator_parity.py` (o id tem de ser o ÚLTIMO) e
   `test_upgrade_settings_migration.py` (classe `TestSupersededShippedBaseline`:
   literal congelado da lista de 6, migração nomeada, reordenado = PRESERVED,
   2ª rodada no-op, não-vácuo).
9. **Docs** (livres): `CEO-MODEL-ROUTING.md` (literal do working set + nota
   S338), `cost-of-operation.md` (linha), `provider-pricing.md` (3 tabelas —
   a primária é consumida pelo registro de preços — + a exceção 0.025× no
   parágrafo da tabela de cache).

## Kernel

`.claude/settings.json` ∈ `_KERNEL_PATHS`. O LAND arma
`CEO_KERNEL_OVERRIDE` ele mesmo, no menor escopo (export antes do apply,
unset após o commit, backstop no trap), com o par reason-SLUG + `I-ACCEPT`
validado VIVO contra o contrato do hook — mecanismo idêntico ao 183batch
(`b7dad83`), ao 179close (`bc82651`) e ao adrgate (`cfab980`).

## Residuais declarados

- O **pin `model` NÃO muda** (rota c). Para trabalhar em 5.1 como default
  NESTA máquina o Owner põe `"model": "claude-fable-5-1"` em
  `.claude/settings.local.json` (camada de maior precedência; o `--check`
  do gerador resolve o overlay). Flipar o pin dos três espelhos é decisão
  própria (custo default do adopter ×2; migração do pin no upgrade;
  `EXPECTED_PIN` do dogfood-parity).
- **Rotas (a)/(b)** — 5.1 no `VETO_FLOOR_ALLOWED`, com ou sem migrar os 6
  `agents/*.md` — seguem abertas como amendment futuro.
- `_lib/model_routing.py` (debate/arch em `claude-opus-5`) e o enum
  `MODEL_ID` do tier-policy dos hooks NÃO mudam por desenho (A2.3).
- A parity e2e completa (install v1.2.0 → upgrade) roda no `Smoke Install`
  da CI e PASSOU na sombra (2,5 min) — mas ela classifica `settings.json`
  como divergência ACEITA («keys, not bytes»): NÃO teria pego a ausência do
  7º id; a prova do ramo `superseded` é a suíte de migração (LAND V2). O LAND
  roda o `smoke-install-parity.sh` (~35 s).
- **FOLLOW-UP livre, fora desta wave (achado da mesma consulta):** a página
  de pricing diz que o intro do Sonnet 5 ($2/$10) virou o preço PADRÃO — as
  `_DATED_PRICING` (audit-telemetry, ceo-cost, budget-summary), o sticker do
  `cost-table.yaml` e `docs/cost-of-operation.md` superestimam Sonnet 5 em
  50 % desde 2026-09-01. E `canonical_models.json` tem `valid_until`
  2026-09-01 (STALE advisory a partir de amanhã; um re-fetch de models.dev
  traz o row do 5.1).

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Plans: PLAN-169
Scope:
  - .claude/adr/ADR-149-model-id-allowlist.md
  - .claude/governance/gate-scripts-manifest.txt
  - .claude/hooks/tests/test_adr149_validator_parity.py
  - .claude/scripts/audit-telemetry.py
  - .claude/scripts/budget-summary.py
  - .claude/scripts/build-canonical-models.py
  - .claude/scripts/ceo-cost.py
  - .claude/scripts/cost-table.yaml
  - .claude/scripts/detectors/overpowered.py
  - .claude/scripts/detectors/wasteful_thinking.py
  - .claude/scripts/optimizer/model_normalize.py
  - .claude/scripts/success-receipt.py
  - .claude/scripts/tests/test_a4_pricing_doctrine.py
  - .claude/scripts/tests/test_build_canonical_models.py
  - .claude/scripts/tests/test_generate_available_models.py
  - .claude/scripts/tests/test_model_fleet_presence.py
  - .claude/scripts/tests/test_upgrade_settings_migration.py
  - .claude/scripts/tier_policy_cli/_types.py
  - .claude/scripts/tier_policy_cli/learn.py
  - .claude/scripts/tier_policy_cli/tests/test_learn_mutation.py
  - .claude/scripts/tier_policy_cli/tests/test_types.py
  - .claude/scripts/validate-governance.sh
  - .claude/scripts/value-dashboard.py
  - .claude/settings.json
  - docs/CEO-MODEL-ROUTING.md
  - docs/cost-of-operation.md
  - docs/provider-pricing.md
  - scripts/local/smoke-install-parity.sh
  - scripts/upgrade.sh
  - templates/settings/settings.base.json
<!-- END SIGNED SCOPE -->
