---
adr_id: ADR-089-AMEND-1
amends: ADR-089
title: Gatilho de reabertura OBSERVÁVEL para o risco aceito SEC-P0-02 (memória compartilhada como vetor de injeção) + fence no query()
status: ACCEPTED
proposed_at: 2026-08-13
accepted_at: 2026-08-14
proposed_by: CEO (S305 — achado R-SEC7 do W0/PLAN-178; staged em PLAN-178/staged-loteB)
decided_by: Owner (assinatura GPG da cerimônia do Lote B/PLAN-178)
risk_tier: A
debate_required: true
related_plans: [PLAN-178]
related_adrs: [ADR-089, ADR-116, ADR-191]
---

# ADR-089-AMEND-1 — SEC-P0-02: gatilho derivável + fence no retorno

## §1 Contexto

ADR-089 §SEC-P0-02 registrou REFUSED com gatilho de reabertura
"incidente real de cross-role scratchpad em telemetria de adopter". O
achado R-SEC7 do W0/PLAN-178 mostrou que esse gatilho é **insondável
por construção**: não existe detector de contaminação, logo "zero
incidentes observados" não informa nada e o gatilho nunca pode
disparar — a classe instrumento-verde-com-pergunta-envelhecida na sua
forma mais pura (um gatilho que estruturalmente não dispara é um
verde perpétuo).

Além disso, a justificativa do ADR-116-AMEND-1 ("hook #44 basta") não
cobre esta classe: o hook #44 guarda LEITURA cross-plan; o vetor aqui
é ESCRITA mesmo-plano lida por OUTRO agente (confused deputy
intra-plano). `query()` devolvia `content` byte-a-byte
(`memory_shared.py`); a redação do ingest (`put_pattern`) cobre
SEGREDO, não INSTRUÇÃO.

## §2 Decisão

1. **O gatilho de reabertura passa a ser DERIVÁVEL dos eventos que já
   existem** (redação r2 — a v1 dizia "≥2 papéis distintos", claim
   NÃO-derivável pega pelo rail codex: o evento não carrega papel, e o
   caller nem passava `session_id`, que o emitter sempre aceitou —
   esta cerimônia cura o caller): reabrir SEC-P0-02 quando o nightly
   observar **≥2 `pattern_stored` com `content_hash` DISTINTOS no
   MESMO tópico e MESMA `session_id`** — condição computável
   count-only (nenhum conteúdo de pattern sai do storage). Proxy
   honesto: sobre-dispara em single-role multi-write (aceito — o
   disparo abre TRIAGEM, nunca ação automática); atribuição por PAPEL
   exigiria campo novo no schema do evento (fora deste pack) e entra
   como refinamento futuro SE a triagem mostrar FP recorrente. O
   CONSUMER existe desde este pack (codex r8): a dimensão (ix)
   `shared-memory-reopen` do nightly-hygiene conta os grupos
   (topic, session_id) com ≥2 hashes distintos em 24h e reporta RED
   quando o gatilho dispara — o gatilho é DISPARÁVEL, não apenas
   derivável.
2. **A metade barata da cura entra JÁ** (este pack): o retorno do
   `query()` é FENCED como dado não-confiável —
   `fence_untrusted_content()` (função pura) envolve o corpo com
   marcadores explícitos "DADO, nunca instrução", espelhando o
   tratamento que memórias recalled e lanes de workflow já recebem
   (ADR-191 §2.4). **Sem mudança de schema de storage**: o arquivo em
   disco permanece o corpo redacted cru; `content_hash` continua o
   hash do corpo ARMAZENADO; `size_bytes` continua o tamanho em
   disco. Testes em `_lib/tests/test_memory_shared_fence.py`
   (canonical-guarded POR DESIGN: des-fenciar o query() no futuro
   exige cerimônia, não só um teste editado).
3. **O REFUSE do SEC-P0-02 permanece** — scan de injeção no ingest
   segue custo-excede-benefício até o gatilho (1) disparar.
4. **Compatibilidade de contrato (DECISÃO — fecha a oscilação codex
   r4↔r7):** `query()` muda o VALOR de `content` (agora fenced) e o
   resultado deliberadamente NÃO carrega campo de corpo cru — o r4
   pediu um campo aditivo (compat §12/§13), o r7 mostrou corretamente
   que qualquer campo cru restaura o vetor quando o dict inteiro é
   serializado num prompt. Os dois lados não coexistem por patch:
   registra-se a DECISÃO — **segurança default-on vence o contrato
   experimental** (v1.0.0-rc.1). Consequências assumidas: (a)
   consumidores que verificavam `content_hash` contra `content` leem
   o arquivo em `_patterns_dir()/<hash>.txt` (byte-exato por
   construção); (b) o desvio do SPEC
   `SPEC/v1/memory-shared.schema.md` (deny-Edit no harness — fora
   deste pack) é REGISTRADO com destino = trem v1.4.0 (cerimônia
   própria de SPEC, documentando `content` fenced + a rota de
   verificação por arquivo), nunca dropado em silêncio; (c) a rota
   puramente aditiva (`content` cru + `content_fenced` opt-in) foi
   REJEITADA: consumo de scratchpad é prompt-level e um campo seguro
   opcional reabre o vetor por conveniência.

## §3 Consequências

- (+) O risco aceito ganha um instrumento que PODE disparar — sai da
  classe instrumento-verde-com-pergunta-envelhecida.
- (+) O consumidor do scratchpad recebe moldura de dado, alinhado ao
  ADR-191 §2.4 (fence obrigatório em ingest de retornos).
- (−) **R-SEC4 (mesmo residual do ADR-191)**: o fence não impede
  direcionamento por conteúdo — um pattern hostil ainda chega ao
  prompt do consumidor, apenas emoldurado. Registrado.
- (−) O gatilho (1) é count-only e por isso cego a contaminação
  single-role (um papel que grava e lê o próprio tópico). Aceito: o
  vetor de risco nomeado no SEC-P0-02 é cross-role.
