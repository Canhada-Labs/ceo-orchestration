# wave-s329-E — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`). O binding é o `Patch-sha256` (land por PATCH, sem
> `MANIFEST-*`). O bloco `Scope:` é **DERIVADO** por
> `PLAN-183/w5-ceremony/finalize_patch.py` a partir de `git apply --numstat` —
> nunca escrito à mão. O `Anchor-SHA` é preenchido pelo `OWNER-S329-E-SIGN.sh`
> com `git rev-parse HEAD` no momento da assinatura; o `OWNER-S329-E-LAND.sh`
> aborta no G1 se não casar. Reescrever um byte deste arquivo depois de assinar
> invalida o `.asc`.

Plans: PLAN-169
Wave: wave-s329-E (cura do achado S328 sobre `scripts/upgrade.sh`: o roster de hooks que o upgrade registra passa a ser DERIVADO de `templates/settings/settings.base.json`, em vez de uma segunda cópia literal de 6 registros mantida dentro do upgrader)
Patch: .claude/plans/PLAN-169/s329-ceremony-E/E.patch
Patch-sha256: dfe1866b2a07c4a447e694bf1c7939fdc871c02a84fef6d3594083174c5ebec1
Patch-base: 7d0fb25e49a0a4cacc4d04cd29b2b0b481de5508
Anchor-SHA: TO-FILL-AT-SIGN
Data: TO-FILL-AT-SIGN

## O que esta wave entrega

**Dois arquivos canônicos** (`scripts/upgrade.sh`, `.github/workflows/smoke-install.yml`)
e **três não-canônicos** que viajam no mesmo patch porque são a vigilância dos
dois primeiros: os testes e o registro de desenho. O oráculo `--is-canonical`
responde `1` para os dois primeiros e `0` para os três últimos; todos os cinco
entram por esta cerimônia porque o patch é atômico — um teste que landasse
depois da cura seria uma janela em que a classe não tem guarda.

1. **`scripts/upgrade.sh`** (canônico, +366 / −94) —
   `_merge_lifecycle_hooks_into_settings` deixa de carregar um roster LITERAL de
   6 registros dentro do programa `jq` (mais os mesmos 6 repetidos em prosa para
   o `--dry-run`) e passa a REDUZIR `$SOURCE_DIR/templates/settings/settings.base.json`,
   o template do checkout que EXECUTA o upgrade — a mesma resolução que
   `_migrate_settings_baseline` já usa. O template enumera **47** registros; o
   merge derivado entrega os 47. O achado de origem
   (`PLAN-179/s328-ceremony-D/FINDING-upgrade-lifecycle-hooks-S328.md`, rail
   codex rodada 3 do pacote D) é o registro **`PreToolUse` /
   `check_ledger_checkpoint.py`**, que nenhum upgrade jamais registrou.

   A semântica muda de RE-CANONICALIZAÇÃO para ADITIVA: ausente ⇒ appenda o
   bloco do template; presente ⇒ **preserva byte-idêntico**. Isso não é
   preferência de estilo — medido, **5 das 6 cópias literais já divergiam do
   template** (todas no `_comment`), então o upgrade pré-cura *estragava* um
   adopter que o `install.sh` tinha deixado correto.

2. **`.github/workflows/smoke-install.yml`** (canônico, +61 / −1) — o e2e novo
   entra nas DUAS listas de `paths:` (`push` e `pull_request`) e ganha um step
   no molde do vizinho `test-upgrade-historical-adopter.sh`, e o
   `timeout-minutes` do job vai de 83 para 126 (composto sobre o +15 do PLAN-185 W1+W2, que landou antes — DESIGN-E §10). `scripts/tests/*.sh` roda SÓ
   neste workflow, e o próprio arquivo escreve a regra: *unwired = no test*.
   Sem estas linhas a cura entraria sem vigilância — foi achado do pair-rail
   (rodada 1, P2) e era a **OQ-E4** do desenho.

3. **`scripts/tests/test-upgrade-lifecycle-hooks-derived.sh`** (não-canônico,
   +783) — e2e com install e upgrade REAIS, **51 asserções**. Carrega o
   **RED control** (`E.3`: o upgrader pré-cura de `git HEAD` contra o MESMO
   fixture deixa `check_ledger_checkpoint.py` desregistrado) e o **controle
   POSITIVO** (`E.4`: um hook sintético inexistente em `upgrade.sh`, plantado só
   no template de uma cópia da árvore-fonte, é registrado).

4. **`.claude/scripts/tests/test_upgrade_lifecycle_hooks_derived.py`**
   (não-canônico, +914) — **49** testes de unidade que dirigem a FUNÇÃO extraída
   por âncora do `upgrade.sh` shipado (não o programa `jq` isolado: o único
   defeito real desta wave morava no wrapper). Contém o guard anti-rot
   `TestNoSecondRoster::test_the_function_names_no_hook_filenames` — **vermelho
   se qualquer nome de hook voltar a aparecer dentro da função**. É a regra que
   impede a classe de renascer.

5. **`.claude/plans/PLAN-169/s329-ceremony-E/DESIGN-E.md`** (não-canônico) — o
   registro de desenho: o antes/depois por registro, os dois achados medidos
   durante a implementação, as seis questões abertas e a rodada de rail.

## O que esta wave NÃO entrega (e por quê)

- **Não fecha a OQ-E1**, que é decisão do Owner: derivar as 47 entradas move o
  roster do adopter para o template, e quem REMOVEU um hook de propósito o
  recebe de volta a cada upgrade. Hoje o único escape é `--no-settings-merge`,
  que é tudo-ou-nada. A opção conservadora (denylist por nome no `settings.json`
  do adopter) **não** foi implementada: inventaria superfície de configuração
  que ninguém pediu.
- **Não ensina o `doctor.sh` a REPARAR um registro deformado** (OQ-E6). A
  semântica aditiva move o reparo para fora do upgrader, e o `doctor.sh` hoje só
  confere o *timeout* do `check_pair_rail.py`. Não é regressão — o pré-cura só
  re-canonicalizava 6 de 47 — mas é um destino, não um mecanismo existente.
- **Não muda a posição de inserção** (OQ-E2): blocos re-adicionados entram no FIM
  do array do evento, exatamente como o código pré-cura fazia.

## Base de CI esperada após o land

O `smoke-install.yml` passa a executar um e2e a mais, com 51 asserções e dez
upgrades reais. O `timeout-minutes` de 126 é dimensionado no fator 2–3× de runner que
este arquivo já usa, com margem anti-flake; a **primeira execução real** é o
número que deve substituir essa estimativa — re-apertar no p95 observado, nunca
na aritmética (a lição que este arquivo re-aprende: super-dimensionar não custa
nada num run verde, sub-dimensionar reporta como `cancelled` num passo inocente).
Nenhum outro workflow é tocado.

## Autorização de governança

- Achado de origem: `.claude/plans/PLAN-179/s328-ceremony-D/FINDING-upgrade-lifecycle-hooks-S328.md`
  (S328, rail codex rodada 3 do pacote D).
- Unidade **U3** do contrato da night-run S329
  (`.claude/plans/PLAN-185/NIGHT-S329-RUNBOOK.md`), decisão do Owner de
  2026-08-26: ordem `185 → audit_emit → E`.
- Desenho e medições: `.claude/plans/PLAN-169/s329-ceremony-E/DESIGN-E.md`.
- Pair-rail: registros em
  `.claude/plans/PLAN-169/s329-ceremony-E/rail-round-*.md`. O
  `OWNER-S329-E-SIGN.sh` recusa assinar se o registro de MAIOR número não
  carregar `Rail-Verdict: APPROVE`.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs TO-FILL-AT-SIGN
Plans: PLAN-169
Scope:
  - .claude/plans/PLAN-169/s329-ceremony-E/DESIGN-E.md
  - .claude/scripts/tests/test_upgrade_lifecycle_hooks_derived.py
  - .github/workflows/smoke-install.yml
  - scripts/tests/test-upgrade-lifecycle-hooks-derived.sh
  - scripts/upgrade.sh
<!-- END SIGNED SCOPE -->

## Residual declarado

- **A chave de identidade de um bloco SEM `.py` é o comando inteiro.** O único
  bloco assim no template é o `echo` inline do `PostToolUse|Agent`. Um adopter
  que mudou um espaço nesse comando recebe um SEGUNDO bloco. Não há jeito
  honesto de evitar sem normalizar o comando, e normalizar arrisca colidir dois
  blocos distintos. Registrado aqui em vez de escondido.
- **`_up_record_op` dispara mesmo quando o merge é no-op.** A posição é a EXATA
  de hoje (antes do ramo `--dry-run`), preservada de propósito para não mexer no
  oráculo de `test-upgrade-dryrun-identity.sh`. É uma assimetria defensável:
  registra uma operação que pode não escrever.
- **`E.9` compara contra `git HEAD` e vira SKIP depois deste land** — por
  desenho (é medição histórica do §3.1, não invariante). É um verde que muda de
  significado com o tempo, e a classe «instrumento verde cuja PERGUNTA
  envelheceu» é conhecida deste repositório. O mesmo vale para `E.3`, que roda o
  upgrader de `git show HEAD:scripts/upgrade.sh`: depois do land o `HEAD` passa
  a conter a cura e o caso degrada para um SKIP explícito com instrução de
  re-armar.
- **`--slurpfile` exige `jq` ≥ 1.5** (2015). O código já dependia de `jq`; isto
  acrescenta uma FLAG. Medido em `jq-1.7.1`. Se algum adopter alvo puder ter
  `jq` mais velho, o fallback portátil é `jq -s '.[0] as $a | .[1] as $t | …'`.
- **O nome da função ficou estreito** (OQ-E3): `_merge_lifecycle_hooks_into_settings`
  já não registra só hooks de ciclo de vida. Renomear tocaria o call-site e a
  superfície canônica sem comprar nada, e a mesma função aparece em duas cópias
  staged (`PLAN-169/staged-w3/`, `PLAN-180/staged-s313/`) que divergiriam de
  qualquer jeito. Anotado no comentário do código.
