---
plan: PLAN-166
round: 3
rounds_synthesized: [round-1, round-2, round-3]
agents_considered: [vp-engineering, security-engineer, devops-engineer]
decisions_revised_in_plan:
  - "§W2.2/W2.4 — ordem reordenada: verdito-commit → push main → CI verde → preflight → tag (composição r3+r15 recriava a forma do F2)"
  - "§W0.2 — asserts server-side independentes de CEO_PAIR_RAIL_VERDICT_OPTIONAL (step próprio, fail-closed, pós-verify, ordem pinada); conjunto fechado por CONTEÚDO (shasum -c); regra do candidato mais recente"
  - "§W0.3 — censo recitado removido (era ele próprio incorreto); ARCHITECTURE:73,84,85 + métrica test_files; edição de CLAUDE.md agendada para closeout (disciplina Gate-1)"
  - "§W1 — disciplina do kernel-override (token por-cerimônia, slug nomeado, evento no ledger); Scope: gerado da árvore staged; timeout smoke-install 8→~15"
  - "§W1.5/W0.3 — approx imprime inputs (comando, valor, erros de coleta com WARNING); 189 derivado, não digitado"
synthesized_at: 2026-08-05T18:05:00Z
synthesized_by: CEO
---

# Synthesis — PLAN-166 (arco de 3 rounds)

## Arco

- **Round 1** (plano v1): 3× ADJUST + VETO escopado no AC-2. O debate
  derrubou o desenho original em três pontos estruturais: fix de F3
  destrutivo (classe S238), AC-2 auto-anulável (bind por SHA sob OQ-2a),
  classificação canonical errada. Consensus com 10 findings → v2.
- **Round 2** (v2/v2.1): 3× ADJUST. VETO#1 LEVANTADO por verificação
  literal; VETO#2 aberto (marcador sem as proteções de VERSION) e fechado
  pela Forma A na síntese. Correções de texto: trusted-publisher é
  canonical; predicado de 4 oráculos; INSTALL.md:627 devolvido; approx
  com banda declarada; autoria de testes em W0.
- **Interlúdio (rounds 3-17 do rail pré-commit codex):** ~35 achados
  aplicados ao plano, incluindo classes que o debate não pegou (GH_TOKEN;
  fetch-depth:1; --no-replay pulando ceremony; update-checker em loop;
  marcador rastreado v3 — que motivou re-verificação e
  LEVANTADO-CONFIRMADO do VETO#2 com correção honesta do próprio
  registro). O r17 exigiu, corretamente, este round 3 formal
  (jaccard r1→r2 = 0.0; DEBATE-SCHEMA §12.2).
- **Round 3** (texto final): 3× ADJUST, convergência material. Critic-A
  verificou 12 claims factuais novas (todas verdadeiras, incl. 14172
  exatos) e declarou os 17 rounds "cadeia de refinamento, não remendos
  que se anulam" — com UMA exceção que ele mesmo achou (a ordem
  preflight/verdito, R3-VP1). Critic-B abriu VETO#3 (asserts server-side
  herdariam as escotilhas do CEO_PAIR_RAIL_VERDICT_OPTIONAL) e o
  LEVANTOU após a condição (a)(b)(c) aplicada. Critic-C validou as 8
  mecânicas GHA contra código e achou o timeout do smoke-install.
  Todos os must-fix dos três aplicados ao plano.

## Vetos (registro completo)

| VETO | Autor | Aberto | Condição | Estado |
|---|---|---|---|---|
| #1 | Critic-B | r1 (AC-2 bind) | textual | LEVANTADO r2 (verificação literal) |
| #2 | Critic-B | r2 (marcador) | Forma A/B | LEVANTADO r2 → RE-VERIFICADO r3 contra design v3 (tracked) → LEVANTADO-CONFIRMADO |
| #3 | Critic-B | r3 (escotilhas do assert server-side) | (a)(b)(c) | LEVANTADO r3 (verificação literal) |

## Lições para o processo de debate

1. **Debate e rail pré-commit acham classes DIFERENTES.** O debate pegou
   design (destrutividade do F3, bind auto-anulável, blast radius); o
   codex pegou contratos de execução (auth de CLI, fetch-depth,
   flag-interactions, loops de updater) e aritmética de gates. Nenhum
   substitui o outro — a sequência debate→rail→debate-final pagou.
2. **Fixes pontuais compõem errado.** As duas regressões mais sérias do
   processo (assert mesmo-commit r2; ordem preflight/verdito r3+r15)
   nasceram da COMPOSIÇÃO de correções individualmente corretas. O round
   3 formal sobre o texto final existe para isso.
3. **Registro de VETO tem versão.** O design mudou depois do
   levantamento (marcador v3) e o registro ficou órfão — a re-verificação
   pelo AUTOR (não edição do registro pelo CEO) é o protocolo certo, e o
   autor corrigiu o próprio raciocínio duas vezes no caminho.
4. **Listas recitadas erram até quando avisam para não recitar** (o
   "SETE stale" do W0.3 estava errado NA FRASE que mandava derivar do
   gate). Censo = rodar o gate. Sempre.
5. **Convergência formal (jaccard) mede semelhança de texto, não
   acordo.** r1→r2 deu 0.0 porque o round 2 verificava um plano
   reescrito — os críticos concordavam em quase tudo. O gate formal
   ainda assim forçou o round 3, que achou R3-VP1. O gate estava certo
   pelo motivo errado.

## Verdito final

**Material: design-coherent** (3 rounds completos; 3 VETOs abertos e
levantados com condições textuais verificadas; zero contestações
cruzadas pendentes; todos os must-fix aplicados).

**Formal: unresolved-at-cap (DEBATE-SCHEMA §12.4), escalado ao Owner.**
`debate-converge.py` reporta jaccard 0.0 nos dois pares de rounds — e
isso é ESTRUTURAL neste processo, não sinal de desacordo: a métrica mede
semelhança de texto entre críticas, e cada round examinou um plano
REESCRITO (r2 verificou a reescrita do consensus r1; r3 verificou o
texto pós-17-rounds-codex). Críticas sobre textos diferentes não se
parecem, por construção. Rounds adicionais não convergem a métrica —
apenas continuam o refinamento (r19→r20 do rail codex: 4→5 achados,
todos da mesma família de padrões já generalizados no plano). No cap de
3 rounds, o §12.4 manda registrar e escalar: a decisão de encerrar é do
Owner, com o histórico completo (3 rounds de debate + 20 rounds de rail
codex, ~55 achados aplicados, 3 VETOs levantados) como evidência.

**Decisão do Owner (2026-08-05, AskUserQuestion):** selecionou "Encerrar
e commitar (Recomendado)" — "Ratifica o encerramento §12.4. […] Os
achados residuais do rail são da família já generalizada no plano; o
próximo terminal executa W0 com o plano como está. Racional: o rail
continua achando refinamentos legítimos mas ilimitados — o lugar deles
agora é a EXECUÇÃO (os testes e controles positivos que o plano exige),
não mais prosa de plano."

Registro: nem design-coherent nem a decisão do Owner autorizam ship — a
cascata V0-V3 (pair-rail codex + GPG do Owner) autoriza, por tag, em W2.
