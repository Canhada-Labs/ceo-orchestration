---
plan: PLAN-169
round: 4
rounds_synthesized: [round-1, round-2, round-3, round-4]
agents_considered: [vp-engineering, security-engineer, devops-engineer]
verdicts: {Critic-A: ACCEPT, Critic-B: ACCEPT, Critic-C: ACCEPT}
round_verdict: PROCEED
convergence_check:
  tool: debate-converge.py --plan PLAN-169 --round 4
  jaccard: 1.0
  outcome: converged
  prev_risk_count: 10
  curr_risk_count: 10
  red_team_needed: false
synthesized_by: "CEO — síntese com autoria dos críticos VISÍVEL (DESVIO §13.2 registrado: anonymization-map.md criado a posteriori; ver debate/README.md §2 — deferral deliberada escalada ao Owner)"
created_at: 2026-08-08
---

# Consensus round 4 — PLAN-169 (INTERMEDIÁRIO; a triade completa sobre a v2.5 correu no round 5)

## Arco das 4 rodadas

| Round | Vereditos | Jaccard (vs anterior) | O que moveu |
|---|---|---|---|
| 1 | 3× ADJUST | — | 20 decisões de consensus: fronteira canônico/livre (MF-1), W4-C nasce (MF-2), bateria→PLAN-170 (MF-3), quota-resume re-arquitetado (MF-4/5), W4.4 re-escopado pelo disco (MF-6), E.7/E.11 incluídos (MF-7), 12 itens de segurança (R-SEC1-12), 3 de release (D1-D3) |
| 2 | 1× ACCEPT + 2× ADJUST | 0.0 (defeito de instrumento: round-1 do Critic-B sem bullets = zero contribuição SILENCIOSA; resolução punida) → **virou item W2.9 com evidência** | Escopo do W4-C em ARQUIVOS; controle W2.6 transitório; aceite do quota-resume mede o ARM; template constante na injeção; PreToolUse SendMessage incondicional; ordem dos controles do snapshot; isolamento do fleet |
| 3 | 2× ACCEPT + 1× ADJUST | 0.588 (cur ⊂ prev: 10/17, ZERO risco novo — queda 100% resolução) | 2 controles negativos fail-closed na bateria do quota-resume (família E.2) |
| 4 | **3× ACCEPT** | **1.0 — CONVERGED (gate formal met)** | estabilização pura; nenhum texto novo |

## Deltas finais no plano (v2.4)

Registrados no header do plano (v2 → v2.1 → v2.2 → v2.3 → v2.4) e no
§Progress log. O rail codex cross-vendor rodou EM PARALELO ao debate
(r1-r7 até aqui) e seus achados alimentaram as rodadas — os dois
mecanismos acharam classes DIFERENTES (precedente S294 confirmado de
novo): o debate achou fronteiras/arquitetura/segurança de desenho; o
rail achou contrato de repo (no-speed-claim, contaminação), scripts
perigosos e o próprio bypass do gate de convergência desta síntese.

## Riscos duráveis remanescentes (10, estáveis por 2 rodadas)

Conjunto integral nos arquivos round-4/*.md — todos com dono/gate no
próprio plano (execução W1/W4-C, trens W6, instrumento W2.9).

## Lessons para o processo de debate

1. `## Risks` sem bullets = contribuição ZERO silenciosa
   (registered-vacuous no instrumento de convergência) — W2.9(i).
2. A métrica pune resolução: risco curado sai do conjunto e derruba o
   Jaccard; rodada de estabilização é o que prova convergência de
   verdade — W2.9(ii) reporta `resolved` vs `novel` separados.
3. Verificação textual curta (formato fora do schema) quebra o gate
   de máquina — rounds SEMPRE no schema §4, mesmo quando o pedido é
   só "verifique o texto".

## Round verdict

**PROCEED** — `design-coherent`, com o gate formal de convergência
MET (jaccard 1.0), 3× ACCEPT, zero VETO, Red Team não exigido
(convergência em round 4 > 2, §12.3). PROCEED não autoriza shipping:
a cascata de verificação (rail codex até rodada limpa, gates de CI,
cerimônias GPG, trens W6 com hold) autoriza.

## Addendum de segurança pós-r4 (não é um round)

Após esta convergência, o rail codex (r11/r15) trouxe um delta de
DESIGN no quota-resume — descarte da assinatura HMAC (oráculo de
mesmo-UID) → trust model estreitado honesto. Como o delta é de domínio
de Security, ele foi re-avaliado no ROUND 5 (triade completa sobre a
v2.5 executável), verdito de Security = ACCEPT. **Este consensus do
round-4 é INTERMEDIÁRIO** — o artefato terminal do debate é
`round-5/consensus.md` (`status: unresolved`, §12.4, escalado ao
Owner). Round-4 convergiu (jaccard 1.0) sobre a v2.4; a v2.5 executável
foi revisada no round-5.
