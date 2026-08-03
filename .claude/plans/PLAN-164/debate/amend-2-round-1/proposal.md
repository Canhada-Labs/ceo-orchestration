---
plan: PLAN-164 (amendment continuation — ADR-110-AMEND-2)
round: 1
created_at: 2026-08-03
proposer: CEO
---

# ADR-110-AMEND-2 — proposta: recalibração upward 120/150 → 180/210

> Contexto normativo: `ADR-110-AMEND-1-rail-timeout-contract.md` §3 agenda
> esta recalibração quando ≥10 casos saudáveis acumularem pós-uplift, e
> exige que qualquer mudança seja NOVA EMENDA via cerimônia, com o número
> decidido pelo protocolo C5 (medição executada, não inferida) + debate.
> Este debate é essa exigência.

## Medição (executada 2026-08-03, query normativa do §3)

Fonte: UNIÃO dos logs rotacionados `audit-log-2026-0*.jsonl` + o vivo
(`~/.claude/projects/ceo-orchestration/`). Join `(session_id, review_id)`
entre `pair_rail_review_expected` e `pair_rail_case`.

- **n = 14 casos saudáveis** (A:10, B:4) — gatilho ≥10 ATENDIDO.
- Latências (s), ordenadas:
  33, 41, 44, 48, 49, 55, 61, 70, 71, 79, 95, 115, 115, **120.0**
- mediana 65.5s | máx observado **120.0s** (= o budget interno!) |
  p95 interpolado 121.2s (> budget; extrapolação acima do máximo, n=14)
- **3 case-F no período** — a distribuição é censurada à direita: review
  mais lento que 120s vira F e NUNCA entra no conjunto saudável, então
  este p95 só pode SUBESTIMAR o verdadeiro.

Nota de método que a emenda deve registrar: a query literal do AMEND-1 §3
aponta para UM arquivo `LOG`; após a rotação mensal ela devolve n=0 (a
sessão de hoje reproduziu isso ao vivo). A emenda corrige a query normativa
para varrer a união rotacionados+vivo.

## Regra de decisão do §3 aplicada

"upward escalation if p95 approaches the internal budget" — p95 ≈ 121s
não só se aproxima: EMPATA/EXCEDE o budget de 120s, com máximo observado
cravado no teto e censura à direita comprovada (3 F's). A escalada upward
é mandatória pelos próprios critérios do ADR.

## Proposta

- **Interno `CEO_PAIR_RAIL_TIMEOUT_S`: 120 → 180.** Mesma razão de folga
  do AMEND-1 (~1.5× o p95 medido: 1.5×121 ≈ 182 → 180 arredondado à
  convenção). Os mesmos 3 literais de `check_pair_rail.py` (default
  string, parse-error fallback, clamp-reset). Clamp bound `>600` intocado.
- **Registro no harness: 150 → 210** (kernel `.claude/settings.json` +
  `templates/settings/settings.base.json`, paridade). Mantém o invariante
  TESTADO `registration >= internal + 30`
  (`test_pair_rail_timeout_invariant.py` passa sem edição — o teste
  verifica a desigualdade, não literais).
- **statusMessage** atualizado ("may take up to ~3 min") nos dois espelhos.
- **Query normativa do §3 corrigida** (união rotacionados+vivo) — a única
  mudança de TEXTO herdada do AMEND-1.

## Custos declarados (a emenda os registra)

- Edit canônico não-sentinelado que dispara review vivo agora segura a
  sessão por até ~180s (vs 120s). Mitigação inalterada: statusMessage +
  o fluxo desejado continua sendo staged+cerimônia para trabalho pesado.
- Um review que hoje viraria case-F em 121-180s passa a COMPLETAR — mais
  gasto Codex recorrente, que é exatamente o gasto que o rail existe para
  fazer (a era 30s nunca pagava verdict nenhum).

## Alternativas que proponho rejeitar

- **(a) 150/180** — folga de 29s sobre o máximo OBSERVADO (120), mas a
  censura diz que o verdadeiro p95 está ACIMA de 121; 150 arrisca repetir
  o ciclo near-miss→F que motivou o AMEND-1 (custo de re-emenda: outra
  cerimônia inteira).
- **(b) Sem teto novo, só knob por env** — o AMEND-1 §4(i) já registrou
  env-knob como residual universal de fail-open; institucionalizá-lo como
  mecanismo de calibração inverte o contrato (decisão vira estado
  per-máquina invisível).
- **(c) Esperar mais amostras** — a censura à direita garante que amostras
  saudáveis futuras NÃO revelam a cauda (F's não entram); esperar não
  melhora a estimativa, só acumula F's.

## Perguntas ao debate

- **AQ1**: 180/210 vs 150/180 — algum critério que eu não pesei?
- **AQ2**: a correção da query (união de logs) basta como texto, ou o §3
  deve exigir um SCRIPT versionado (ex.
  `.claude/scripts/local/pair-rail-latency.py`) para matar a classe
  "query normativa aponta para arquivo que rotacionou"?
- **AQ3**: o statusMessage de ~3 min muda a UX de espera — alguma
  implicação de timeout do PRÓPRIO harness (o hook registrado a 210s fica
  abaixo de algum teto duro do Claude Code?) que precise de sonda antes
  da cerimônia?
