---
id: PLAN-183-FOLLOWUP-delivery-predicate-unification
parent: PLAN-183
title: "Unificação das cópias do predicado de entrega (o que o instalador exclui)"
status: draft
created: 2026-10-02
owner: CEO
depends_on: [PLAN-183]
level: L3
budget_tokens: "150-300k (estimado em 2026-10-02, S362, sem medição: medição da matriz + desenho com debate L3 curto + 3 pacotes canônicos pelo modelo v2, cada um com rail e GPG; reestimar na abertura. Referência de custo: a W5-b, 100-160k por onda canônica)"
budget_sessions: 2-3
context_risk: medium
external_wait: "assinatura GPG do Owner em cada pacote canônico (`upgrade.sh`, `_framework_manifest_set.sh`, `install-npm.sh`, `npm-publish.yml`); a medição e o desenho são do CEO"
eta_calendar: "multi-sessão; cada pacote canônico espera o Owner, sem data. Posição: fila depois da W7b e depois da asserção de presença do `npm-publish.yml` (C8); pelo PLAN-SCHEMA §1.4, só em `executing` com o PLAN-183 `done` (depois da W10)"
tags: [adopter, install, delivery, predicate, npm, plugin, followup, w7, classe]
---

# PLAN-183-FOLLOWUP-delivery-predicate-unification — unificar as cópias do predicado de entrega

> **Lineage (PLAN-SCHEMA §1.4 — "parent shipped with explicit deferred AC
> items").** A **C10** do consenso do debate W7
> (`.claude/plans/PLAN-183/debate/w7-round-1/consensus.md`, condição 10)
> exige, ANTES do SIGN da W7a, dois FU com dono e posição. Este é o segundo
> (o primeiro, o censo POR FORMA, é
> `PLAN-183-FOLLOWUP-delivered-gate-default-path-census.md`). A condição
> pede a EXISTÊNCIA com dono e posição; **implementar a unificação não é
> pré-requisito do SIGN da W7a** e fica fora do caminho crítico da v1.4.3.
> Este rascunho NÃO reabre a W7a nem redefine o texto dela.

## O defeito de classe

«O que é interno do framework e não vai ao adopter» está codificado em mais
de um lugar, e os lugares divergem. O predicado de `install.sh`/`upgrade.sh`
é UM só (`_framework_path_excluded`, na biblioteca
`scripts/_framework_manifest_set.sh`, que os dois chamam), mas **«UM
predicado» vale só para install e upgrade**: os canais de empacotamento e o
purge mantêm cópias à mão (achado da revisão de QA e de DevOps do debate,
2026-10-02; A1-F4).

Sítios, relidos no HEAD `97a78fce` (a lista é de partida, não exaustiva):

| # | sítio | o que codifica |
|---|---|---|
| 1 | `scripts/_framework_manifest_set.sh:95-107` | `_framework_path_excluded()`, o predicado único de install e upgrade |
| 2 | `.github/workflows/npm-publish.yml:317-331` | `RSYNC_EXCLUDES` do canal npm (publicação) |
| 3 | `.github/workflows/npm-publish.yml:398` | o gate do packlist: regex que afirma só a AUSÊNCIA de `tests`/`fixtures`/`eval`/`red-team-corpus`/`plans/PLAN-N`/`testing.py`/`test_isolation.py`, nunca a PRESENÇA de algo |
| 4 | `scripts/install-npm.sh:116-130` | `RSYNC_EXCLUDES` do staging local do canal npm |
| 5 | `scripts/build-plugin.py:342-345` | `ignore_patterns` do canal plugin (a C8 do consenso decidiu, em 2026-10-02, opção (i): acrescentar `harness_replay` aqui, por commit livre; é mais uma entrada à mão, que esta unificação absorve) |
| 6 | `scripts/npm-rebuild.sh:64-66` | `RSYNC_FLAGS` do espelho `npm/`: exclui só caches, nada de `tests`/`fixtures`; o espelho não prova o canal (C8) |
| 7 | `scripts/upgrade.sh:4241-4242` | o purge: `_pm_trees` e `_pm_files` repetem a lista à mão (A1-F4, P3) |

**«Unificar» NÃO quer dizer «uma lista idêntica».** Lendo os sítios 1 a 4, os
canais já divergem POR DESENHO: o canal npm exclui `**/fixtures/` em
qualquer profundidade, mas reinclui `.claude/policies/fixtures/` e
`templates/oidc-proxy/tests/` (o install entrega o bundle de políticas com
as fixtures dele, PLAN-014 A.8); exclui `.claude/eval/`, o corpus de
red-team e os planos, que o predicado do install nem menciona. Unificar é
ter UMA fonte de decisão com os **deltas por canal declarados**, de modo
que a divergência que sobrar seja a escolhida, nunca a acidental.

## Desenho (restrições herdadas, não opções)

- **Uma decisão, não uma cascata** (molde: o `_ownership_verdict()` do
  PLAN-167 e o leitor único de rotas `scripts/delivery-routes.tsv`, com três
  leitores, do PLAN-183 W5). Dois formatos a debater: (a) o predicado bash
  vira a fonte e os demais o chamam ou dele derivam a lista; (b) uma tabela
  de dados lida por todos, inclusive pelo bash. A escolha é o item FU-U2.
- **Nenhum consumidor decide localmente.** O anti-padrão a evitar é o que o
  `CLAUDE.md` §4 descreve para a posse: adicionar um ramo que decide a
  exclusão no próprio consumidor reabre a classe que esta unificação fecha.
- **Pacotes pequenos (modelo v2):** ≤ 400 linhas e ≤ 8 paths por pacote
  canônico, WIP ≤ 3 canônicos. Quatro dos paths são canônicos (oráculo 1
  em 2026-10-02: `scripts/upgrade.sh`, `scripts/_framework_manifest_set.sh`,
  `scripts/install-npm.sh`, `.github/workflows/npm-publish.yml`); o
  `scripts/build-plugin.py` e o `scripts/npm-rebuild.sh` dão oráculo 0.
- **Baseline do PLAN-185.** Qualquer wave que toque `scripts/` regenera o
  baseline do censo de escrita
  (`.claude/scripts/data/installer-write-safety-baseline.txt`) no MESMO
  patch (`CLAUDE.md` §5, PLAN-185).
- **Ordem com a asserção de presença (C8).** A asserção permanente de
  PRESENÇA dos arquivos entregues no packlist do `npm-publish.yml` (FU (2) de
  «Fora destas ondas» do `PLAN-183-adopter-fitness.md`) entra ANTES: é o
  controle que denuncia regressão quando os sítios 2 a 4 passarem a derivar
  do predicado único. O gate de hoje (sítio 3) só vê o que SOBRA, não o que
  FALTA.

## Items

- [ ] `[P2][FU-U1]` Medir antes de desenhar: matriz arquivo × canal sobre a
      árvore real (`git ls-files` como universo), um veredito por mecanismo
      REAL (o predicado bash por chamada, os dois `RSYNC_EXCLUDES` por
      `rsync -n`, a lista de cópia do `build-plugin.py`, o purge), com os
      desacordos classificados «por desenho» ou «acidente». Sem edição de
      código neste item.
      Check: a matriz e a contagem de desacordos existem em
      `.claude/plans/PLAN-183-FOLLOWUP-delivery-predicate-unification/` e o
      commit que as registra não toca arquivo fora dessa pasta
      (`git diff --name-only <commit>^ <commit>`).
- [ ] `[P2][FU-U2]` Desenho da fonte única com os deltas por canal
      declarados, em debate L3 curto; escolhe entre (a) e (b) acima e
      pré-registra a divisão em pacotes e a regra de parada.
      Check: o documento de desenho existe na pasta do followup com a
      escolha, a lista dos deltas por canal (todos classificados «por
      desenho» no FU-U1) e a regra de parada; o commit do desenho não toca
      script nem workflow.
- [ ] `[P1][FU-U3]` Converter o purge do `upgrade.sh` (sítio 7) para o
      predicado único; regenera o baseline do PLAN-185 no mesmo patch.
      Check: `bash scripts/tests/test-upgrade-historical-adopter.sh` verde e
      o purge produz o MESMO conjunto PURGED/KEPT de antes (derivado por
      hash) sobre a árvore da matriz do FU-U1; controle VERMELHO = uma
      entrada plantada à mão fora do predicado faz o censo-teste reprovar.
- [ ] `[P1][FU-U4]` Converter os sítios 2 a 4 (canal npm) para a fonte única.
      Depende da asserção de PRESENÇA (C8) já landada.
      Check: a matriz do FU-U1 re-rodada depois do patch: só os desacordos
      «acidente» desaparecem e os «por desenho» ficam byte-iguais; o gate do
      packlist e a asserção de presença seguem verdes sobre um
      `npm pack --dry-run --json` do HEAD curado.
- [ ] `[P2][FU-U5]` Converter o canal plugin (sítio 5) e decidir o destino do
      `npm-rebuild.sh` (sítio 6): converter, ou declarar que o espelho `npm/`
      não é canal de entrega.
      Check: a matriz do FU-U1 re-rodada mostra o plugin sem entrada de
      exclusão à mão; o `dist/` do plugin, regenerado por
      `python3 scripts/build-plugin.py` (nunca à mão), não carrega
      `harness_replay`.
- [ ] `[P2][FU-U6]` Teste-censo permanente «nenhum arquivo re-deriva a lista
      de exclusão» (padrão do C12 da W7b: uma implementação, censo no teste).
      Check: `python3 -m pytest <teste-censo> -q` verde na árvore limpa e
      VERMELHO quando se planta uma cópia à mão da lista em arquivo novo.

## Fronteiras

- **Não absorve o A1-F5** (install e upgrade divergem em
  `.claude/scripts/`: o upgrade entrega subárvores com ~158 arquivos de teste
  que o install nunca entrega). Ele tem bullet próprio em «Fora destas
  ondas» («onda própria depois da W8»). Os dois tocam `install.sh`,
  `upgrade.sh` e `_framework_manifest_set.sh`: em fila, nunca em paralelo.
- **Não é o censo POR FORMA**
  (`PLAN-183-FOLLOWUP-delivered-gate-default-path-census.md`): lá se pergunta
  QUEM LÊ o que foi excluído; aqui, QUEM DECIDE o que é excluído. Independentes.
- **Não implementa a asserção de PRESENÇA do packlist (C8).** Ela é item
  próprio, anterior a este, em fila depois do LAND da W4 do PLAN-194, que
  reescreve o mesmo `npm-publish.yml`.
- **Posição e dono.** Dono: CEO. Fila: depois da W7b e da asserção de
  presença. Pelo PLAN-SCHEMA §1.4 só entra em `executing` quando o PLAN-183
  estiver `done`; se o Owner quiser antecipar, é exceção explícita dele,
  registrada aqui. Nenhum item deste rascunho está implementado.
