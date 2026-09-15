---
id: PLAN-189
title: Cure quality and rail instrumentation
status: draft
created: 2026-09-15
owner: CEO
depends_on: []
---

## Context

Cerimônias de 6, 11, 12 e 27 rodadas consumindo dezenas de horas do Owner. Três
hipóteses foram levantadas e **todas as três morreram contra dados**, nesta ordem:

1. «O rail produz ruído» — REFUTADA. Classe temática de achado não é taxa de
   falso positivo, e 32,2% do censo estava em «não-classificado» (5,9% ou 38,1%,
   conforme a reclassificação).
2. «Teto mecânico de 3 rodadas» — REFUTADA pela medição do próprio corpus: a
   validade dos achados NÃO decai com a rodada (r1-r3 93%, r4-r7 93%, r8+ 91%;
   178 marcas REAL/VERIFICADO contra 13 REFUTADO/PUSHBACK). Um teto cortaria
   achados majoritariamente válidos.
3. «Parada quando não há P0/P1 novo» — REFUTADA: «nenhum NOVO» permite encerrar
   com bloqueio ANTIGO aberto, e uma rodada sem detecção não demonstra ausência
   de defeito. Além disso a série que a sustentava tinha erro — a r27 registra
   APPROVE, e a menção a P1 ali é retrospectiva, contada indevidamente como
   achado novo.

A verificação no histórico (lane Codex, com comparação de patches) encontrou a
causa real, e são DUAS, coexistindo:

- **Cura por enumeração.** `_sanitize_memory_basename` é BYTE-IDÊNTICA entre o
  candidato da r6 e o da r15: o P1 «tardio» já existia. A r22 declara ser a
  QUINTA rodada da mesma classe (espaços, hífens, concatenação, limites) e só
  então REMOVE a superfície. A cura fechava o exemplo citado e deixava a classe
  aberta; o revisor achava a variante seguinte.
- **Regressão por cura.** A cura do P2 da r9 introduziu `-m`; o P1 da r26
  denuncia a união dos diffs dos pais causada por esse comportamento. E o teste
  criado na r9 continuava VERDE — um exemplo coberto não cobre a classe.

O `CLAUDE.md` já registra a lição desta mesma cerimônia — «enumerar não fecha
canal instruction-adjacent, remover fecha» — como fato histórico. Nunca virou
regra de processo, e por isso seguimos pagando por ela.

Evidência externa em `reference-rail-configuration-evidence-s352`; o erro de
método que originou tudo em `feedback-thematic-class-is-not-false-positive`.

## Goal

Cortar as rodadas pela QUALIDADE DA CURA, não relaxando a revisão — e instrumentar
o trilho para que a próxima decisão sobre ele use dado em vez de contagem de texto.

## Thesis

Nenhuma das curas aqui reduz detecção: não há teto, não há filtro, não há
severidade que dispense revisão. As três propostas que faziam isso morreram.

O que sobra ataca a causa medida: se a cura fecha a CLASSE em vez do exemplo, a
variante seguinte não existe para ser achada; se a cura carrega controle
proporcional ao RISCO da alteração, a regressão que ela introduz é pega no mesmo
pacote em vez de duas rodadas depois.

Consequência prática: **o maior valor deste plano entra sem código**, na próxima
cerimônia. W1 e W2 existem para tornar a regra durável e verificável.

## Items

### W0 — Regra de classe  [P0] — vale a partir da próxima cerimônia

- CAN edit: `PROTOCOL.md` (canônico ⇒ cerimônia assinada), `.claude/plans/PLAN-189/`
- Regra: quando um achado da mesma CLASSE reaparece pela segunda vez numa
  cerimônia, a cura seguinte **não pode ser outro exemplo**. Ou remove a
  superfície, ou declara por escrito por que não é possível e registra aceitação
  de risco nomeada.
- O registro da rodada passa a nomear a CLASSE de cada achado, não só o caso.
- AC: a regra está em `PROTOCOL.md`; um registro de rodada com segunda ocorrência
  da mesma classe sem cura estrutural nem aceitação declarada é violação visível.

### W1 — Controle proporcional ao risco da alteração  [P0]

- CAN edit: `PROTOCOL.md`, `.claude/plans/PLAN-189/`
- Toda cura carrega controle calibrado pelo **risco da alteração**, não pelo
  rótulo do achado — curas de P2 incluídas, porque foi uma delas que introduziu
  o P1 da r26.
- O controle falha pela **violação da propriedade**, não por import quebrado,
  fixture ausente ou função inexistente. Para texto entregue (envelope, docs), o
  controle é uma comparação verificável entre declaração e comportamento, não um
  grep pela frase nova.
- AC: precedentes dos dois lados citados no texto da regra (r5 — a suíte pegou 14
  falhas de uma cura que mutilou funções vizinhas; r26 — teste verde sobre
  cenário errado).

### W2 — Telemetria do trilho  [P1]

- CAN edit: `.claude/hooks/` (o emissor de `codex_review_verdict`), SPEC
- Hoje o gancho dispara e não registra nada útil: `outcome` é constante em 100%
  dos 68 eventos, `tokens_total` é 0 em TODAS as 7.550 linhas do log, o
  identificador é único por evento (não agrupa rodadas) e o campo de duração é um
  timestamp.
- Campos mínimos, só o que seria usado numa decisão: identidade (cerimônia,
  rodada, hash do artefato revisado + base); protocolo (versão da política,
  modelo revisor, hash do prompt); execução (início, fim, veredito efetivo,
  referência à saída bruta preservada); achado (identidade persistente, primeira
  ocorrência, severidade original E decidida, disposição); cura (achados que a
  motivaram, versões antes/depois, referência ao controle); **tempo humano ativo,
  separado do tempo de espera**.
- AC: um evento por rodada agrupa corretamente as rodadas de uma cerimônia;
  valor desconhecido é AUSENTE, nunca zero.

### W3 — Salvaguarda contra edição do relato  [P1]

- CAN edit: `PROTOCOL.md`, `.claude/plans/PLAN-189/`
- A saída original do revisor é preservada e ligada ao hash revisado. Severidade
  ORIGINAL e severidade DECIDIDA são campos distintos. Aceitar excepcionalmente
  um P1 é registrado como **aceitação de risco P1**, nunca como conversão para P2.
- Fechamento exige **zero bloqueios pertinentes pendentes** — incluindo os
  antigos. «Nenhum novo» não é critério.
- AC: divergência de severidade entre revisor e autor é decidida pelo Owner e
  registrada, sem nova rodada automática só sobre o rótulo.

## O que este plano NÃO faz (declarado)

- Nenhum teto de rodadas. Nenhum filtro de promoção. Nenhuma isenção de revisão
  por classe temática. As três foram refutadas por dados e não voltam sem
  evidência nova.
- Não mede recall nem custo de filtro — não é preciso, porque nada aqui filtra.

## Open questions

- **OQ-1.** W0 e W3 tocam `PROTOCOL.md`, que é canônico ⇒ cerimônia assinada.
  Entram numa assinatura só ou W0 primeiro (é o que corta horas) e W3 depois?
- **OQ-2.** «Mesma classe» precisa de definição operável. Proposta: mesma
  propriedade violada OU mesma superfície de entrada, julgado pelo autor e
  registrado. Basta, ou o Owner quer critério mais estrito?
- **OQ-3.** W2 mexe em emissor de auditoria (hook). Vale o custo agora, ou
  esperamos W0/W1 mostrarem efeito primeiro?

**Respostas do Owner (2026-09-15 (S353, 20:5x BRT; Owner presente; AskUserQuestion; rótulos VERBATIM); registro em `PLAN-186/debate/owner-decisions-S353.md`):**

- OQ-1 — «W0 primeiro, sozinha (Recomendado)». W3 fica para uma assinatura posterior.
- OQ-2 — «Propriedade OU superfície, julgado pelo autor (Recomendado)». Mesma
  propriedade violada OU mesma superfície de entrada; quem cura julga e escreve a
  classe no registro da rodada.
- OQ-3 — «Fazer agora junto» (contra a recomendação). Leitura do CEO: a W2 entra no
  programa agora e viaja com a W1 na assinatura seguinte à da W0 (a OQ-1 fixa a
  W0 sozinha); se o Owner quiser a W2 na assinatura da W0, é decisão nova.

## How to continue

> Ler `.claude/plans/PLAN-189-cure-quality-and-rail-instrumentation.md`, a
> memória `feedback-thematic-class-is-not-false-positive` e
> `reference-rail-configuration-evidence-s352`. Responder OQ-1..OQ-3. W0 e W1
> valem na PRÓXIMA cerimônia mesmo antes da cerimônia assinada — a regra pode ser
> seguida antes de estar escrita no arquivo canônico.

## Success criteria

- [ ] W0: regra de classe em `PROTOCOL.md`, com a classe nomeada nos registros
- [ ] W1: controle por risco da alteração, com os dois precedentes citados
- [ ] W2: um evento por rodada que agrupa a cerimônia; desconhecido ≠ zero
- [ ] W3: severidade original vs decidida separadas; fechamento por zero pendentes
- [ ] Nenhuma regra deste plano reduz detecção — verificável lendo as quatro

## Regra de parada (pré-registrada)

Sinal de sucesso, em 2-3 cerimônias: **queda no número de rodadas que repetem a
mesma classe**. Menos rodadas, sozinho, NÃO é sinal de sucesso — pode ser
ocultação. Sinal de fracasso: bloqueio reproduzível no candidato que teria sido
liberado, rebaixamento de severidade sem evidência, ou aceitação de risco que
ninguém revisita.

Se as quatro waves não fecharem em duas sessões, entrega-se W0+W1 (que já cortam
horas) e o resto vira follow-up. Discussão sobre a redação deste plano não é
trabalho.
