# PROPOSED-PATCH — wave-fable51 (S338, cerimônia `adopt-fable-5.1`)

Patch: `WFABLE51.patch` (derivado da sombra `shadow-fable51` pelo
`finalize-fable51.sh`; base declarada em `BASE-SHA.txt`; o CONTEÚDO da sombra
é a saída de `apply-fable51-edits.py` sobre HEAD — 55 edições, 30 paths).
Patch-sha256: eb46ef0a42a272bdb8bf7677c89b28a4a6928052d73a534d6dbac9da45e1ca67

## Por path (30)

| path | oráculo | o que muda |
|---|---|---|
| `.claude/adr/ADR-149-model-id-allowlist.md` | CANÔNICO | `claude-fable-5-1` APPENDED AT END no `AVAILABLE_MODELS_WORKING_SET` + **Amendment 2** (fatos da doc oficial incl. cache 0.025×, decisão rota c, o que não decide, FU Sonnet 5) |
| `.claude/settings.json` | CANÔNICO (KERNEL) | `availableModels` 6→7 (gerado do ADR); `model`/`fallbackModel` intactos |
| `templates/settings/settings.base.json` | CANÔNICO | idem |
| `.claude/governance/gate-scripts-manifest.txt` | CANÔNICO | sha do membro `validate-governance.sh` re-derivado (ADR-192) |
| `scripts/upgrade.sh` | CANÔNICO | `availableModels.superseded` (lista de 6 de v1.2.0/v1.3.0) + `new` de 7 + ramo `matched SUPERSEDED shipped baseline` na política de 3 estados |
| `.claude/scripts/validate-governance.sh` | livre (membro ADR-192) | case-arm do lint `model:` + mensagem + comentário |
| `.claude/scripts/tier_policy_cli/_types.py` | livre | `VALID_MODEL_IDS` 6→7 + Literal `MODEL_ID` |
| `.claude/scripts/tier_policy_cli/learn.py` | livre | `_tier_rank`: 5.1 = 7 (acima do Fable 5) — rail r1 P1 |
| `.claude/scripts/tier_policy_cli/tests/test_types.py` | livre | `len == 7` + `assertIn` |
| `.claude/scripts/tier_policy_cli/tests/test_learn_mutation.py` | livre | paridade allowlist↔ladder + rank/direction do 5.1 |
| `scripts/local/smoke-install-parity.sh` | livre | `ALLOWED_MODELS` + `EXPECTED_AVAILABLE` |
| `.claude/scripts/cost-table.yaml` | livre | linha `claude-fable-5-1` 10/50 (source: overview; cache 0.025× anotado) |
| `.claude/scripts/audit-telemetry.py` | livre | `_PRICING_PER_MTOK` += 5.1 |
| `.claude/scripts/budget-summary.py` | livre | `_DEFAULT_PRICING` += 5.1; multiplicador de cache-read POR MODELO (0.025× no 5.1) — rail r1 P2; fallback do `meta.model` ambíguo para o `message.model` do transcript — rail r2 P2 |
| `.claude/scripts/ceo-cost.py` | livre | `_DEFAULT_PRICING` += 5.1 |
| `.claude/scripts/value-dashboard.py` | livre | `_DEFAULT_PRICING` += 5.1 |
| `.claude/scripts/success-receipt.py` | livre | `_DEFAULT_PRICING` era pré-gen-5: ganha a frota corrente (fable-5-1, fable-5, opus-5, opus-5-fast, sonnet-5, opus-4-8, opus-4-8-fast, sonnet-4-6, haiku-4-5) nas taxas per-1k do budget-summary; históricas retidas — rail r3 P1 |
| `.claude/scripts/build-canonical-models.py` | livre | `price_for`: prefixo só resolve pin DATADO (`-YYYYMMDD`); minor 5.1 = UNKNOWN, nunca o row do 5 — rail r2 P2 |
| `.claude/scripts/detectors/overpowered.py` | livre | `_LARGE_MODELS` += 5.1 |
| `.claude/scripts/detectors/wasteful_thinking.py` | livre | `_TARGET_MODELS` += 5.1 |
| `.claude/scripts/optimizer/model_normalize.py` | livre | alias `fable-5-1` → `claude-fable-5-1` |
| `.claude/scripts/tests/test_model_fleet_presence.py` | livre | `_NEW_FLEET` + rates + detectors + `test_fable51_row` + multiplicador de cache + alias bare ambíguo + spawn nativo sintético + `TestSuccessReceiptFleetPresence` (recibo misto) |
| `.claude/scripts/tests/test_generate_available_models.py` | livre | `WORKING_SET` + fixture `AMENDED_ADR` |
| `.claude/scripts/tests/test_a4_pricing_doctrine.py` | livre | `_EXPECTED_RATES` += 5.1 |
| `.claude/scripts/tests/test_build_canonical_models.py` | livre | `test_minor_version_does_not_collapse_onto_base_row` (amostra + arquivo shipado) |
| `.claude/scripts/tests/test_upgrade_settings_migration.py` | livre | classe `TestSupersededShippedBaseline` (6 testes) |
| `.claude/hooks/tests/test_adr149_validator_parity.py` | livre | o id novo presente E ÚLTIMO no working set |
| `docs/CEO-MODEL-ROUTING.md` | livre | literal do working set + nota S338 |
| `docs/cost-of-operation.md` | livre | linha da tabela de preços |
| `docs/provider-pricing.md` | livre | linha nas 3 tabelas (primária = registro de preços) + exceção 0.025× no parágrafo da tabela de cache; a coluna «long-context premium» do 5.1 cita a evidência DOCUMENTAL (pricing page §Long context, 4.6+ = 1M a preço padrão) e declara que a sonda viva não foi re-rodada — rail r4 P2 |

## O que este patch NÃO faz

- Não toca `VETO_FLOOR_ALLOWED` (ADR nem `agent_frontmatter.py`), nem os 6
  `agents/*.md`, nem `_lib/model_routing.py`, nem o enum `MODEL_ID` dos hooks.
- Não flipa o pin `model` (fica `claude-opus-5` nos três espelhos) nem o
  `fallbackModel`.
- Não adiciona row ao `canonical_models.json` (proveniência = Owner fetch de
  models.dev, checksum sobre `models`): o 5.1 fica UNKNOWN lá até o re-fetch.
- Não regenera `installer-write-safety-baseline.txt`: o ratchet sai 0 sobre a
  árvore patchada — as edições de shell não criam sítio de escrita.
- Não corrige o preço do Sonnet 5 (intro virou padrão — FU livre, A2.3).
- Não toca nenhum dos 13 paths do pacote S337 staged na árvore viva (conjuntos
  disjuntos, medido).

## Evidência pré-assinatura (S338, sombra base dc72bf1, pós-r4)

- `generate-available-models.py --check`: `MATCH (7 ids, ADR order preserved)`;
  `gen-settings-user-template.py --check` rc 0; `shasum -a 256 -c` manifesto
  9/9 OK; `upgrade.sh --print-settings-baselines` parseia com `superseded`
  de 1 lista.
- Suíte declarada **351 passed / 2 skipped** (skips pré-existentes);
  `test_budget_summary.py` + `test_success_receipt.py` 78/0 (não-regressão).
- `validate-governance.sh` COMPLETO: `Errors: 0`; `verify-counts.sh` rc 0;
  claims rc 0; hook-map `--check` rc 0; env-hygiene rc 0; ratchet rc 0;
  shellcheck rc 0 nos 3 `.sh`; `py_compile` verde nos 19 `.py`; `build-plugin.py --check` rc 0;
  `check_harness_config.py` rc 0.
- `smoke-install-parity.sh`: `RESULT: PASS` (install real em tmp, 35 s);
  `test-install-upgrade-parity-e2e.sh` (pin v1.2.0): `RESULT: PASS` (2,5 min).
- Reprodutibilidade: `HEAD + apply-fable51-edits.py == sombra` byte a byte
  (30/30) — provada no finalize 4a e no LAND V3.
- Rail codex: r1 (2 P1 + 1 P2), r2 (1 P1 processo + 2 P2), r3 (1 P1 processo +
  1 P1 real: espelho do success-receipt), r4 (1 P1 processo + 1 P2 real:
  coerência doc↔teste A4 sobre a evidência de long-context do 5.1), r5
  APPROVE (só o item de PROCESSO — o sentinel que a cerimônia produz) —
  ver `rail-round-*.md`; a última rodada registrada é a que autoriza.
