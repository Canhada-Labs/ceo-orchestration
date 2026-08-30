# PROPOSED-PATCH — wave-s330-F (PLAN-169 OQ-E5): o perfil `user` é DERIVADO da base

Patch: `.claude/plans/PLAN-169/s330-ceremony-F/F.patch`
Patch-sha256: TO-FILL-AT-FINALIZE
Base: ver `BASE-SHA.txt` (o `finalize_patch.py` recusa uma sombra cuja base não
seja o HEAD vivo, e grava o mesmo sha no `Patch-base:` do sentinel)

---

## 1. O quê

Vinte arquivos, **quatro** deles canônicos.

| path | +/− | canônico? | papel |
|---|---|---|---|
| `templates/settings/settings.user.json` | +346 / −5 | **sim** | o entregável: deixa de ser cópia manual e passa a ser derivado da base pelo spec da chave `_derivation`. Roster **20 → 30** registrações (29 basenames) |
| `.claude/adr/ADR-197-user-profile-derivation.md` | +187 / −0 | **sim** | a decisão registrada (ADR novo, não AMEND — §6 da classificação) |
| `.claude/adr/README.md` | +30 / −3 | **sim** | índice de ADRs REGENERADO. Estava congelado em 170 com 198 no disco — 27 das linhas não são desta wave (FU-F-ADRGATE) |
| `.github/workflows/validate.yml` | +38 / −0 | **sim** | OQ-F3: step `User-template derivation (regen+diff)` |
| `.claude/scripts/gen-settings-user-template.py` | +904 / −0 | não | o gerador: `--check` / `--write` / `--json` / `--spec`. rc 1 = drift, rc 2 = INFRA |
| `.claude/scripts/tests/test_gen_settings_user_template.py` | +1255 / −0 | não | 73 casos, 9 classes. Inclui o guard invertido do FU-F-ACCEL e os guards da rodada 1 do rail |
| `.claude/scripts/tests/fixtures/settings.user.pre-F.json` | +267 / −0 | não | o template de `1c34eb5` congelado — o CONTROLE VERMELHO contra a própria afirmação do `_comment` antigo |
| `.claude/scripts/tests/test_install_user_skips_governance_hooks.py` | +36 / −13 | não | a cura do bloqueador §4b: a lista de hooks de governança passa a ser derivada DO SPEC, com guard anti-vacuidade |
| `scripts/build-plugin.py` | +49 / −45 | não | FU-F-ACCEL: a tabela paralela some; a composição vira função pura |
| `.claude/plans/PLAN-169/s330-ceremony-F/DESIGN-F.md` | +697 / −0 | não | o registro de desenho (§3 achados, §4b bloqueador, §5 follow-ups, §7 a reconciliação S331, §7.6 o pair-rail) |
| `CLAUDE.md` | +1 / −1 | não | **só o numeral** de ADRs (197 → 198). `check-claude-md-claims.py` roda no `validate.yml` |
| `CHANGELOG.md`, `README.md`, `README.pt-BR.md`, `docs/{ARCHITECTURE,README,CTO-GUIDE,GUIA-COMPLETO,FAQ}.md`, `npm/README.md` | +13 / −13 | não | as 15 citações de contagem de ADR que o `verify-counts.sh` cobra |

> Os números de linha acima são os da sombra no momento em que este registro foi
> escrito. O `finalize-F.sh` re-deriva o patch contra o HEAD vivo, e o
> `EXPECTED_PATCH_PATHS` do `EXPECTED-BASELINE.txt` é o conjunto que o G4 do
> LAND compara — é ele, não esta tabela, que decide.

Os dezesseis não-canônicos viajam no MESMO patch de propósito. Um gerador que
landasse sem o gate seria uma janela sem vigilância; um ADR que landasse sem as
contagens deixaria o `Validate` vermelho no próprio commit do land.

## 2. Por quê

O `_comment` do template afirmava duas coisas que **nenhum gate lia**: que a
remoção era de "exatamente 10" hooks, e que cada registro retido era
byte-idêntico ao da base nos campos de comportamento.

Medido na classificação por mérito (`4f4df3a`):

* **26 basenames** — não 10 — na base e ausentes do template;
* dos 10 nomeados, **só 5** sustentam o critério declarado, e **2** não
  pertencem à lista por leitura nenhuma;
* dos 16 restantes, **13 já faltavam na v1.0.0**;
* **duas** divergências de matcher/registro que o comentário dizia não existir;
* `PLAN-122 WS-4`, a proveniência citada, **não existe em ref git nenhum**.

Um numeral em prosa JSON não é vigiado por regra alguma. A cura não é corrigir a
cópia — é fazer a subtração virar DADO com leitores, a mesma forma do ADR-194
(rota de entrega) e do ADR-196 (confinamento de escrita).

## 3. O que foi medido

| gate | resultado |
|---|---|
| `gen --check` | rc 0 no artefato; rc 1 com diff sob **um byte** alterado; rc 2 sem a chave `_derivation` |
| suíte da cerimônia (7 arquivos) | **225 passed / 2 skipped** |
| guard do plugin (`-k PluginHooks`) | 7 passed; **controle positivo** replantando o ACCEL ⇒ 3 vermelhos nomeando o ofensor |
| guards da rodada 1 do rail | 7 passed; **controle vermelho** com o validador pré-cura ⇒ 4 vermelhos |
| plugin composto | 30 registrações, **0 triplos duplicados** (eram 4), spec não vaza |
| `verify-counts.sh` | rc 0 |
| `check-claude-md-claims.py` | rc 0 |
| `validate-governance.sh` | 0 erros |
| `check-installer-write-safety.py` | rc 0 (sem regeneração: o censo varre `.sh`) |
| `actionlint` | verde |

## 4. O que fica aberto

* **FU-F-ADRGATE** — `check-adr-chain.py` e `generate-adr-index.py` não rodam em
  CI. Achado desta wave; wave própria.
* **OQ-F2 / OQ-F4 / OQ-F5** — mantidas como o writer as recomendou.
* **ADR-197 entra como `PROPOSED`** — o flip é cerimônia própria.
