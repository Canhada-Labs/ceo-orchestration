---
id: PLAN-171-FOLLOWUP-read-provenance
parent: PLAN-171
title: Manifesto de proveniência de leituras — observation log local (W2 do PLAN-171)
status: draft
created: 2026-10-10
owner: CEO
depends_on: [PLAN-171]
level: L3
tags: [governance, audit, provenance, followup]
---

## Context

O PLAN-171 fechou na W0 em 2026-10-10. A W2 dele não foi iniciada e vem para
cá. Escopo copiado do pai (§2 W2, §4, §6):

- Estender o audit HMAC (PostToolUse em Read/Grep/Glob/WebFetch) para registrar
  digests e paths do que cada agente LEU, num **sidecar encadeado**. A cadeia
  principal não cresce: o perf-gate p99 e o histórico float-em-HMAC proíbem.
- Anexar o manifesto aos artefatos decisórios (verditos de debate e de council,
  packs).
- No `/council`, validar o prompt egresso contra o manifesto. A
  allowlist-por-proveniência é CAMADA ADICIONAL sobre a blocklist-por-classe do
  ADR-114; a blocklist nunca sai (Codex r1: camada, não troca).
- Limite de fronteira, declarado e não vendido como cobertura: leituras de lanes
  fora do harness (`codex exec`) são INVISÍVEIS.

Ideia importada do «observation log» do cloudflare-os (PLAN-171 §1). Nenhum
código importado.

## Goal

Cada artefato decisório carrega o manifesto do que foi lido para produzi-lo, sem
pagar o p95 do PostToolUse acima do teto do perf-gate vigente.

## Items

### W1 — piloto em sidecar  [P1]  (canônico: hooks; cerimônia + rail por item)
- Sidecar encadeado com kill numérico: overhead p95 do PostToolUse acima do teto
  do perf-gate ⇒ redesenho. A medição imprime os seus inputs (lição S285).
- É o item de maior valor e de maior risco de perf do plano pai (§4).

### W2 — anexo aos artefatos e camada do `/council`  [P2]
- Só depois do piloto verde.

## Decisão do Owner (2026-10-12)

Resposta do Owner à pergunta do CEO com seis itens (AskUserQuestion, S363,
~12:50Z): «Aceito as 6 (Recommended)». O item deste plano dizia: «registro do
que cada agente leu (read-provenance): fila da 1.4.4».

- O plano entra na fila da 1.4.4. O `status` continua `draft`; esta decisão
  não responde a OQ-1 (custo).

## Open questions

- **OQ-1.** O custo fica a firmar no refinamento. A síntese de fechamento da
  S363 estima 1,2–2,2 M tokens em 6–10 sessões para todo o resto do PLAN-171,
  sem divisão por item.

## Success criteria

- [ ] Piloto em sidecar medido, com o p95 do PostToolUse abaixo do teto do perf-gate.
  Check: a medição do piloto, com inputs impressos
- [ ] `/council` valida o prompt egresso contra o manifesto, e a blocklist do ADR-114 continua ativa.
  Check: teste com controle positivo das duas camadas
