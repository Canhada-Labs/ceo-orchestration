---
plan: PLAN-194
rounds_completed: 3
final_verdict: "PROCEED (W5c, W2); W3 ADIADA pelo Owner — VETO de Segurança segue LEVANTADO até a decisão 3 escrita"
synthesized_at: 2026-10-02T15:00:00Z
synthesized_by: CEO
ratified_by: Owner (S361, 2026-10-02, por múltipla escolha no terminal)
debate_record:
  - .claude/plans/PLAN-194/debate/round-1/consensus.md
  - .claude/plans/PLAN-194/debate/round-2/consensus.md
  - .claude/plans/PLAN-194/debate/round-3/consensus.md
---

# PLAN-194 — debate L3 único — artefato terminal (DEBATE-SCHEMA §6)

## Ratificação do Owner (2026-10-02)

Respostas do Owner, por múltipla escolha, registradas literalmente:

- **Decisões 4, 5 e 6 e o debate:** «Aceitar em bloco (Recomendado)» — (4) a W3 landa SEM sentinela de
  qualidade, declarada (R-2); (5) o rail deste repositório fixa `gpt-6-astra` + `xhigh` no argv, e nos adopters
  é opt-in; (6) a aceitação automática do pin grava evento na cadeia HMAC; e o veredito do debate fica
  ratificado.
- **Decisão 2 (W2.6):** «Aceitar a recomendação (Recomendado)» — pré-condição = sessões DESTE projeto fechadas;
  PID vivo ⇒ pula a família; mtime < 10 min ⇒ recusa; spool ativo ou `.draining.*` com PID vivo ⇒ recusa;
  manutenção recorrente quando o `/ceo-boot` acusar ≥ 100 mil travas; a 1.ª roda assim que a W2 landar.
- **Decisão 1 (vaga da cura da condição 67):** superada — a cura landou assinada em `65cd50d7`.
- **Decisão 3 (empacotamento do verificador de assinatura):** NÃO tomada. O Owner escolheu «Re-pin manual
  agora», como 1.ª tarefa do próximo terminal (plano B da W3, ADR-182 §5). Pelo consenso da rodada 3, o VETO
  de Segurança da W3 só sai com a decisão 3 escrita como ramo (ii) ou (i); portanto a W3 NÃO está liberada
  para execução e fica adiada até essa decisão.
- **Ritmo do trem:** «4 canônicos; 8→12 agentes (Recomendado)».

## Veredito final por onda

| Onda | Rodada | Veredito | VETO |
|---|---|---|---|
| W5c — adoção do Sonnet 5.5 | 1 | PROCEED | não levantado |
| W2 — estado da auditoria | 2 | PROCEED | retirado sob MF-R2-W2-1..4; a cura da condição 67 já landou (`65cd50d7`) |
| W3 — pin automático do Codex | 3 | PROCEED 3/3 no desenho; **adiada pelo Owner** | **segue LEVANTADO até a decisão 3 escrita**; «confiança no registro» ⇒ ESCALATE |

## Arco das três rodadas

- **Rodada 1:** 21 consensus findings e 48 ajustes; W5c PROCEED; W2 e W3 RUN-ANOTHER-ROUND (VETO levantado nas
  duas).
- **Rodada 2:** 13 consensus findings e 52 ajustes; W2 PROCEED (VETO retirado com condições); W3
  RUN-ANOTHER-ROUND. A medição W0.6 mostrou que o comando de assinaturas do npm não prova procedência e que a
  biblioteca `sigstore` com política de identidade prova.
- **Rodada 3:** 7 consensus findings e 23 condições de execução; W3 PROCEED 3/3, com o VETO retirado só sob a
  decisão 3.

## Deltas finais do plano

- Ajustes 1–17 no `PLAN-194-maintenance-train-v1-4-3.md` e 18–32 no rascunho
  `debate/round-3/ADR-182-AMEND-1-draft.md`, landados em `f829b29a` (com a revisão cruzada do Codex).
- Exceção (5) da «Regra de WIP» (pacote 1a com 9 paths no ramo (ii)): segue PROPOSTA, porque é ratificada
  junto da decisão 3, que não foi tomada.
- A escolha do re-pin manual exige ajuste de texto na W3 (a condição 21 do consenso r3 — ensaio só-verificação
  contra a 0.156.1 — passa a mirar a versão recém-pinada) quando a W3 for retomada.

## Lições para o processo de debate

As cinco lições da §6 do `consensus.md` da rodada 3 valem como registradas lá: medir antes de debater o
mecanismo; o rascunho do ADR prevalece e o plano cita, não repete; lint de Checks verdes por construção;
anonimização imperfeita declarada; autodeclaração do instrumento só vale com o instrumento protegido. Mais
uma, desta ratificação: uma decisão do Owner que destrava um VETO pode ser substituída por um plano B; o
`approved.md` registra a onda como ADIADA, nunca como liberada.
