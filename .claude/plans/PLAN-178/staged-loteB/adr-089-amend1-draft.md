# ADR-089-AMEND-1 (DRAFT — formaliza via cerimônia do Lote B/PLAN-178)

## Title
Gatilho de reabertura OBSERVÁVEL para o risco aceito SEC-P0-02
(memória compartilhada como vetor de injeção) + fence no query()

## Status
DRAFT (proposto S305)

## Context
ADR-089 §SEC-P0-02 REFUSED com gatilho "incidente real de cross-role
scratchpad em telemetria de adopter". Achado do W0/PLAN-178 (R-SEC7):
o gatilho é INSONDÁVEL por construção — não existe detector de
contaminação, logo "zero incidentes observados" não informa nada e o
gatilho nunca pode disparar. Além disso a justificativa do
ADR-116-AMEND-1 ("hook #44 basta") não cobre esta classe: o hook
guarda LEITURA cross-plan; o vetor é ESCRITA mesmo-plano lida por
outro agente. `query()` devolve `content` byte-a-byte
(memory_shared.py:360-455); a redação do ingest cobre segredo, não
instrução.

## Decision
1. O gatilho de reabertura passa a ser DERIVÁVEL dos eventos que já
   existem (`emit_pattern_stored`/`emit_pattern_queried`): reabrir
   quando ≥2 papéis distintos gravarem no MESMO tópico dentro de uma
   janela de sessão (condição computável no nightly; count-only).
2. A metade barata da cura entra já: o retorno do `query()` é FENCED
   como dado não-confiável (marcador explícito; sem mudança de schema
   de storage; teste em `_lib/tests/`).
3. O REFUSE do SEC-P0-02 permanece — scan de injeção no ingest segue
   custo-excede-benefício até o gatilho (1) disparar.

## Consequences
- (+) O risco aceito ganha um instrumento que PODE disparar — sai da
  classe instrumento-verde-com-pergunta-envelhecida.
- (+) Consumidor do scratchpad recebe moldura de dado, alinhado ao
  ADR-191 §4.
- (−) O fence não impede direcionamento por conteúdo (mesma
  limitação R-SEC4); registrado.
