---
id: PLAN-183-FOLLOWUP-delivered-gate-default-path-census
parent: PLAN-183
title: "Censo POR FORMA: componente entregue que lê por padrão um caminho que o instalador exclui"
status: draft
created: 2026-10-02
owner: CEO
depends_on: [PLAN-183]
level: L3
budget_tokens: "200-400k (estimado em 2026-10-02, S362, sem medição: desenho com debate L3 curto + instrumento + ligação ao CI; reestimar na abertura. Referência de custo: a W5-b, 100-160k por onda canônica; o instrumento é a parte incerta, e o censo do PLAN-185 consumiu 3 arquiteturas de regra e 7 levas de rail)"
budget_sessions: 2-3
context_risk: medium
external_wait: "assinatura GPG do Owner SÓ para a ligação ao CI (item FU-C4: `validate.yml` é canônico); o desenho e o instrumento são do CEO"
eta_calendar: "mesmo-dia a D+1 para o desenho e o instrumento; a ligação ao CI espera o Owner, sem data. Posição: fila depois da W7b e, pelo PLAN-SCHEMA §1.4, só em `executing` com o PLAN-183 `done` (depois da W10)"
tags: [adopter, install, delivery, census, followup, w7, classe]
---

# PLAN-183-FOLLOWUP-delivered-gate-default-path-census — censo POR FORMA da classe «componente entregue lê por padrão caminho excluído»

> **Lineage (PLAN-SCHEMA §1.4 — "parent shipped with explicit deferred AC
> items").** Este followup existe porque a **C10** do consenso do debate W7
> (`.claude/plans/PLAN-183/debate/w7-round-1/consensus.md`, condição 10)
> exige, ANTES do SIGN da W7a, «dois FU com dono e posição»: o censo POR
> FORMA desta classe (2.ª ocorrência, A1-F4/F5) e a unificação das cópias do
> predicado de entrega (irmão: `PLAN-183-FOLLOWUP-delivery-predicate-unification.md`).
> A condição pede a EXISTÊNCIA dos dois com dono e posição; **implementar
> este censo não é pré-requisito do SIGN da W7a** e fica fora do caminho
> crítico da v1.4.3. Este rascunho NÃO reabre a W7a nem redefine o texto dela.

## O defeito de classe

Um componente que o framework ENTREGA ao adopter (hook, script, módulo de
`_lib/`) lê, por padrão, um caminho que o instalador EXCLUI do que entrega.
No repo-fonte o caminho existe, e por isso nenhum teste do framework
percebe; no adopter ele não existe, e o componente sai vermelho, degrada ou
cala.

A instância que a W7a cura: `check_harness_config.py` lia por padrão
`REPLAY_FIXTURES_REL = ".claude/hooks/tests/fixtures/harness-config/replay"`
(ver «W7» no `PLAN-183-adopter-fitness.md`), caminho que
`_framework_path_excluded` (`scripts/_framework_manifest_set.sh:95-107`)
exclui por inteiro (`.claude/hooks/tests`). A W7a move as fixtures para
`.claude/hooks/_lib/harness_replay/` e acrescenta a asserção estrutural de
ENTREGA (C5) **para esse gate**. O que a W7a não faz, e declara no ADR-158
pela FORMA sem enumerar sítios, é perguntar o mesmo a todos os outros
componentes entregues. Cura da CLASSE, não do exemplo (`CLAUDE.md` §4, S352:
2.ª ocorrência pede cura estrutural): este followup é essa pergunta feita
por um instrumento, não por leitura.

## Lista de partida (lida em disco, NÃO medida no adopter)

Achados da revisão de QA do debate (2026-10-02), relidos no HEAD `97a78fce`
(números de linha conferidos; ver o resto no `qa-architect.md` da rodada 1,
«Unseen by the original plan», item 5). **Consequência no adopter não
medida**: cada sítio precisa, antes de contar como achado, da prova de que
é ENTREGUE (cobertura por `_framework_target_entries` e não exclusão por
`_framework_path_excluded`, por chamada REAL ao bash).

| sítio | o que lê por padrão |
|---|---|
| `.claude/scripts/hook-profiler.py:39,115` | `FIXTURES_DIR = HOOKS_DIR / "tests" / "fixtures" / "hooks"` e `in.json` de cada hook |
| `.claude/scripts/ceo-diagnose.py:296` | roda `pytest .claude/hooks/tests` |
| `.claude/scripts/check-test-env-hygiene.py:58-59` | `_DEFAULT_SCAN_ROOTS` com `.claude/hooks/tests` e `.claude/scripts/tests` |

A lista é de PARTIDA, não exaustiva: a razão de ser deste followup é que
ninguém a esgota lendo.

## Desenho (restrições herdadas, não opções)

- **O predicado é chamado, nunca copiado.** «Entregue» = coberto por uma
  entrada de `_framework_target_entries` e não excluído por
  `_framework_path_excluded`, por chamada REAL ao bash (C5 do consenso). Um
  instrumento que copia o `case` do predicado seria mais uma cópia, a classe
  do followup irmão.
- **Desenho antes da regra.** O censo de escrita do PLAN-185 parou por
  anti-padrão 6 («forma não modelada ⇒ fail-open») depois de 3 arquiteturas
  de regra e 7 levas de rail, e hoje vive como RATCHET fail-closed com
  pontos cegos declarados (`OQ-W0-STOP`; ver
  `PLAN-185-FOLLOWUP-doctor-confinement.md`, item FU-1). Este censo herda a
  lição: começa pelo desenho (que FORMAS de «caminho padrão» ele modela e
  quais declara como ponto cego, pelo nome), nunca pela regra.
- **Critério de parada PRÉ-REGISTRADO na abertura** (mesmo critério da
  tentativa anterior): fail-open na mesma classe em 2 rodadas CONSECUTIVAS
  de rail ⇒ o censo vira relatório consultivo com os pontos cegos
  declarados, e nenhuma 4.ª arquitetura abre sem desenho novo.
- **Controle vermelho e positivo.** O instrumento, rodado sobre a árvore
  PRÉ-W7a (qualquer commit anterior ao land da W7a; o HEAD `97a78fce` serve),
  TEM de acusar o `check_harness_config.py`; sobre a árvore pós-W7a, NÃO. Um
  caso por forma modelada, e um por forma não modelada afirmando que o
  instrumento a DECLARA como ponto cego em vez de calar.

## Items

- [ ] `[P2][FU-C1]` Desenho do censo, com debate L3 curto: definição de
      «entregue», lista fechada das FORMAS de caminho padrão modeladas
      (constante de módulo, default de argparse, `Path` composto a partir de
      `__file__`/raiz do repositório, literal em argv de subprocesso) e das
      NÃO modeladas, saída (relatório + ratchet com baseline), regra de
      parada.
      Check: o documento de desenho existe em
      `.claude/plans/PLAN-183-FOLLOWUP-delivered-gate-default-path-census/`
      com as duas listas e a regra de parada, e o commit do desenho não toca
      nenhum `.py` (`git diff --name-only <commit>^ <commit>` sem `.py`).
- [ ] `[P2][FU-C2]` Prova de entrega e consequência dos sítios da lista de
      partida, medidas num alvo instalado do zero em tmp (`TestEnvContext`
      quando em pytest; nunca o `$HOME` real).
      Check: tabela sítio × entregue (rc EXATO da chamada ao bash) ×
      consequência observada no alvo, registrada na pasta do followup; um
      sítio sem medição não conta como achado nem como falso positivo.
- [ ] `[P2][FU-C3]` Instrumento stdlib (Python ≥ 3.9) que, dado o conjunto
      entregue derivado da chamada real ao bash, lista por FORMA os
      componentes cujo caminho padrão cai no excluído; modo `--check` contra
      baseline; ruído e pontos cegos declarados na própria saída.
      Check: `python3 -m pytest <teste do instrumento> -q` verde, com o
      controle VERMELHO (árvore pré-W7a acusa `check_harness_config.py`), o
      POSITIVO (árvore pós-W7a não acusa) e um caso por forma não modelada.
- [ ] `[P3][FU-C4]` Ligar o instrumento ao CI como ratchet fail-closed em
      `.github/workflows/validate.yml` (arquivo canônico, oráculo 1 em
      2026-10-02 ⇒ cerimônia com rail e GPG do Owner), SÓ depois de o
      instrumento convergir em rail. Se virar membro de gate, avaliar a
      entrada no manifesto ADR-192 no MESMO pacote (precedente: C39 da W7b).
      Check: a CI falha quando se planta um componente entregue lendo por
      padrão `.claude/hooks/tests/...` e passa na árvore limpa.
- [ ] `[P3][FU-C5]` O residual que a W7a e a W7b declaram no ADR «pela FORMA,
      sem enumerar sítios» passa a apontar para este instrumento e para os
      pontos cegos que ele declarou.
      Check: none (doc-only)

## Fronteiras

- **Não é a unificação das cópias do predicado**
  (`PLAN-183-FOLLOWUP-delivery-predicate-unification.md`): lá se muda QUEM
  decide o que é excluído; aqui se pergunta QUEM LÊ o que foi excluído. Os
  dois são independentes e podem andar em qualquer ordem; a asserção de
  PRESENÇA no packlist do `npm-publish.yml` (C8) é outro item e vem antes da
  unificação.
- **Não reabre o ADR-158 nem a W7a.** Se o censo achar outro gate entregue
  com a mesma premissa, a cura dele é onda própria, com o rail dela.
- **Posição e dono.** Dono: CEO. Fila: depois da W7b. Pelo PLAN-SCHEMA §1.4
  este followup só entra em `executing` quando o PLAN-183 estiver `done`; se
  o Owner quiser antecipar, é exceção explícita dele, registrada aqui.
  Nenhum item deste rascunho está implementado.
