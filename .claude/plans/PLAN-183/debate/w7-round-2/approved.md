---
plan: PLAN-183
debate: w7
rounds_completed: 2
final_verdict: "PROCEED (W7a, W7b, W8, W9a, W9b, W10)"
synthesized_at: 2026-10-02T15:00:00Z
synthesized_by: CEO
ratified_by: Owner (S361, 2026-10-02, por múltipla escolha no terminal)
debate_record:
  - .claude/plans/PLAN-183/debate/w7-round-1/consensus.md
  - .claude/plans/PLAN-183/debate/w7-round-2/consensus.md
  - .claude/plans/PLAN-183/debate/w7-round-3/red-team.md
---

# PLAN-183 — debate L3 das ondas W7a a W10 — artefato terminal (DEBATE-SCHEMA §6)

## Ratificação do Owner (2026-10-02)

Resposta do Owner, por múltipla escolha, registrada literalmente: «(i) ação auditada + ratificar
(Recomendado)» — o aviso do P4 na W9a grava uma ação auditada na cadeia (cerimônia `audit_emit`; +1 sessão,
~100–160k tokens), e o veredito das cinco ondas fica ratificado. O Owner também designou o CEO como dono do
achado pré-existente do modo AUTO do `codex_review_user_code` (arquivo não rastreado enviado sem redação,
inclusive via symlink): a cura entra antes do SIGN da W9b (condição C32 da rodada 1).

Colocação no corte, decidida pelo Owner na mesma data: a W7a vai na v1.4.3; a W7b vai na v1.4.4 (resposta «W7b
na 1.4.4 (Recomendado)» — colide com o leque de ADR e com o manifesto do corte). W8, W9a, W9b e W10 seguem a
fila do plano.

## Veredito final por onda

| Onda | Rodada | Veredito | VETO |
|---|---|---|---|
| W7a — gate entregue lê só o que é entregue | 1 | PROCEED 3/3 | não levantado |
| W7b — um predicado de «repo-fonte» | 2 | PROCEED 3/3, Red Team sobreviveu | retirado para R2-1 = (a); volta no rail se o `check-rule-invariants.py` ficar fora do manifesto ADR-192 no mesmo pacote, ou se alguma falha pular a checagem sem linha FAIL nomeada |
| W8 — higiene do upgrade | 1 | PROCEED | condicional: os destinos novos passam por `_wbm_dst_refuses` |
| W9a / W9b — hooks caros | 1 | PROCEED, dividida | condicional na W9a: resolvido pela decisão (i) do Owner |
| W10 — validador de skills | 1 | PROCEED | não levantado |

## Arco das rodadas

- **Rodada 1:** proposta com 23 perguntas e 12 lacunas; 3 críticas; a revisão do Codex sobre a proposta achou
  5 P1 e 2 P2, todos mapeados em ajustes; consenso com 38 condições e 24 ajustes; a afirmação falsa do A1
  (`PLAN-183:2130`) corrigida. W7b foi para a rodada 2.
- **Rodada 2 (só W7b):** 3/3 PROCEED; R2-1 = (a), o predicado em `check-rule-invariants.py` dentro do manifesto
  ADR-192; R2-2 contrato de token no stdout com rc 0; R2-3 raiz explícita; R2-4 matriz E1–E4. Convergência em
  N ≤ 2 acionou o Red Team (§12.3): o consenso sobreviveu, com RT-1 a RT-10. Condições C39–C61 e 18 ajustes.

## Deltas finais do plano

- Ajustes da rodada 1 em `e8ac8aba` e da rodada 2 em `f49bb6e7`, no `PLAN-183-adopter-fitness.md`, ambos com a
  revisão cruzada do Codex.

## Lições para o processo de debate

- A síntese perdeu metade de condições compostas na rodada 1 (4 P1 do Codex, mais 12 achadas por varredura de
  classe): toda síntese compara cada condição com a frase de origem antes de ser revisada.
- O gatilho do Red Team por Jaccard não dispara no layout `w7-round-N/`, nem quando uma crítica escreve riscos
  em parágrafo; a regra que funcionou foi rodar o Red Team quando há convergência, sem depender do gatilho.
- Uma medição citada pelo Red Team (árvore de testes da `v1.1.0`) estava errada e foi pega pela revisão
  cruzada: medição decisiva de qualquer crítico, inclusive do Red Team, é reconferida antes de entrar no consenso.
