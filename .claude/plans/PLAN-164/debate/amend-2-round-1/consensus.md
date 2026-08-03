---
plan: PLAN-164 (ADR-110-AMEND-2)
round: amend-2-round-1
created_at: 2026-08-03
critics: 3
verdicts: [ADJUST, ADJUST, ADJUST]
round_verdict: PROCEED
design_coherent: true
consensus_findings: 5
single_agent_kept: 6
plan_adjustments: 9
---

# ADR-110-AMEND-2 round-1 consensus

> `PROCEED` = `design-coherent` após ajustes. NÃO autoriza shipping — a
> cascata (V1 testes, V2 pair-rail, V3 GPG do Owner) autoriza.

Três lanes, três **ADJUST**. O NÚMERO (180/210) sobreviveu; a
JUSTIFICATIVA e o ESCOPO caíram inteiros. Dois lanes refizeram a medição
de forma independente e ambos acharam o mesmo erro na minha.

## Consensus (2+ lanes)

### C1 — [2/2 lanes que mediram] A medição da proposta estava ERRADA: n=20, não 14

Re-medido pelo CEO em primeira mão (`scratchpad/pair-rail-latency.py`):

| Métrica | Proposta | VERDADE |
|---|---|---|
| n saudáveis | 14 (A:10, B:4) | **20 (A:14, B:6)** |
| mediana | 65.5 s | **75 s** |
| p95 interpolado | 121.2 s (> budget) | **119.8 s — ABAIXO do budget** |
| p95 empírico | — | 115 s |
| case-F joináveis | 3 | **7** (11 outros sem `review_id`, pré-PLAN-161) |
| órfãos verdadeiros | — | **0** |

**Causa raiz:** o glob de união leu 7 dos 8 arquivos. O oitavo
(`audit-log-2026-08-1.jsonl`, mtime 16:26 de hoje) foi criado por uma
rotação NO MEIO desta sessão. A emenda que existe para consertar "query
normativa aponta para arquivo que rotacionou" reproduziu a mesma classe de
bug dentro da própria evidência — numa forma pior: não devolveu `n=0`
(erro visível), devolveu um SUBCONJUNTO cujo p95 sustentava a conclusão
desejada. **Gate que responde com o número errado.**

### C2 — [3/3] O claim "o teste de invariante passa sem edição" é FALSO

`test_pair_rail_timeout_invariant.py` pina `_RATIFIED_INTERNAL_S = 120`
(`:103`) e `_RATIFIED_REGISTRATION_S = 150` (`:104`);
`test_ratified_absolute_values` afirma os literais absolutos em três
sítios. O docstring do próprio teste diz que uma recalibração deliberada
tem de editá-lo no mesmo change. **Um método falha, três asserções.** Os
outros três métodos passam a 180/210 — inclusive o de margem, na
igualdade exata (210 = 180+30).

### C3 — [3/3] A superfície de mudança declarada estava INCOMPLETA

Não são "3 literais + 2 espelhos + statusMessage". São:

1. `check_pair_rail.py` `:1717`, `:1720`, `:1722` **+ o docstring `:51`**
   (4º ponto, que o AMEND-1 §1.1 já listava e eu omiti);
2. `test_pair_rail_timeout_invariant.py` — 2 constantes + narrativa;
3. `.claude/settings.json` `:285-286` + `templates/.../settings.base.json`
   `:98-99` (timeout + statusMessage) **+ os dois `_comment`**
   (kernel `:279`, template `:92`);
4. `CHANGELOG.md:43` carrega "may take 1-2 min" → stale (classe
   doc-freshness que já deixou a rc.2 vermelha);
5. `docs/COMMAND-SKILL-HOOK-MAP.md` — **derivado sob gate duro de CI**,
   precisa REGENERAR, não editar à mão (o item que reprova o CI se
   escapar);
6. ADR novo ⇒ contagem 184→185 no `CLAUDE.md` + superfícies derivadas
   (`check-claude-md-claims.py`, tolerância 0).

Sem isso: `touched − scope ≠ ∅` na cerimônia.

### C4 — [2/3] AQ2 SIM — instrumento versionado, por razão empírica

A query manual falhou NESTA rodada, do jeito pior possível (C1). O script
deve imprimir os INPUTS: arquivos lidos + mtimes, histograma de case, n
joinável, **quantos F foram descartados por falta de `review_id`**,
órfãos, taxa de censura e `ts` de corte. Entregue:
`.claude/scripts/local/pair-rail-latency.py`.

### C5 — [3/3] O número 180 sobrevive — por um argumento MELHOR

Sem p95 interpolado e sem extrapolar acima do máximo. Por contagem:
**25.9 % (7/27) das reviews pós-uplift levam ≥120 s** ⟹ p95 verdadeiro
≥120 s por contagem ⟹ 1.5× ⟹ **≥180**. 180 é o PISO da convenção
existente, não a escolha generosa, e é estimator-robusto (1.5×119.8 =
179.6; 1.5×115 = 172.5; ambos arredondam para 180). Refuta (a) 150/180
rigorosamente: 150 < 180 ≤ 1.5×p95.

## Single-lane MANTIDO

- **S1 — A grandeza medida ⊋ a grandeza capada.** `review_expected` é
  emitido ANTES de `_invoke_codex_review`; pin ADR-182 (sha256 do payload),
  build de prompt, redação ADR-114 e `mkdtemp` rodam antes do
  `subprocess.run(timeout=…)`; readback/parse/redação depois. Um caso
  SAUDÁVEL a 120.0 s teve subprocess estritamente <120 s. A métrica não
  separa "completou na fronteira" de "morreu na fronteira".
- **S2 — A taxa de fail-open (25.9 %) é o número que a proposta nunca
  declarou.** É o único que dimensiona o controle.
- **S3 — §4(i) fica PIOR sob 180 sem um campo.** Nenhum evento registra o
  budget efetivo ⟹ `CEO_PAIR_RAIL_TIMEOUT_S=5` produz case-F
  indistinguível de outage do Codex, enquanto o kill-switch oficial
  (`CEO_PAIR_RAIL_DISABLE=1`) emite evento próprio e ruidoso. **O knob sem
  piso é hoje o bypass mais furtivo que o kill-switch oficial** — e subir
  o custo de UX do caminho honesto aumenta a pressão para usá-lo. Fix
  mínimo: emitir `timeout_s` pós-clamp no evento. Não conflita com o item
  2 deferido do AMEND-1 (não muda semântica do knob, não impõe piso).
- **S4 — AQ3 é GATE, não UX.** `_python-hook.sh` não impõe timeout; se o
  harness tiver teto <210 s, ele mata o hook ANTES do cap interno e um
  hook morto **não emite `pair_rail_case` nenhum** — fail-open SEM evento,
  invisível ao instrumento em numerador e denominador. Pior que o case-F
  atual. Baseline falsificável medido: **0 órfãos** hoje a 150 s. Critério
  de aceite em §6 da emenda.
- **S5 — Trocar a métrica de gatilho para TAXA DE CENSURA.** p95 de
  amostra censurada é estruturalmente inestimável (o próprio argumento (c)
  da proposta). Taxa de censura é observável sob qualquer budget.
  Adotado: reabrir se exceder 5 % em n≥20.
- **S6 — Congelar o `ts` de corte** no texto (o dataset se move enquanto é
  medido: 4 dos F são de hoje, gerados pela sessão que mede).

## Ajustes aplicados na emenda

1. §2 reescrito com n=20 / mediana 75 / p95 119.8 (**abaixo** do budget) /
   p95 empírico 115; cutoff congelado em `2026-08-03T19:16:53Z`.
2. Argumento trocado para CONTAGEM (25.9 % ≥120 s); removidos
   "EMPATA/EXCEDE" e "mandatória" na forma antiga.
3. §2.2 novo: o que a medição NÃO estabelece (S1, suficiência de 180).
4. §1 escopo corrigido: 4 literais + docstring + teste + 2 `_comment` +
   CHANGELOG + COMMAND-SKILL-HOOK-MAP regenerado + contagem de ADR.
5. §3: gatilho p95 RETIRADO, substituído por taxa de censura >5 % em n≥20;
   query vira `.claude/scripts/local/pair-rail-latency.py`.
6. §4(i): reescrito com o achado do bypass furtivo + `timeout_s` no evento.
7. §6 novo: sonda de teto do harness como gate BLOQUEANTE pré-cerimônia.
8. §7: custo declarado inclui a pressão de incentivo sobre o knob.
9. Taxa de fail-open (25.9 %) declarada explicitamente no texto.

## Round verdict

**PROCEED.** Nenhum VETO; a decisão (180/210) sobreviveu a duas
re-medições independentes que derrubaram a justificativa original. O
debate fez exatamente o que devia: matou um argumento elástico e o
substituiu por um argumento de contagem que qualquer terceiro reproduz.

**Nota de método, para o registro:** a proposta do CEO citou um número
errado porque leu 7 de 8 arquivos. Os dois lanes que refizeram a conta
acharam o erro. Se este debate não tivesse rodado, a cerimônia teria
landado uma emenda cuja §2 não reproduz — e o próximo revisor cross-vendor
a derrubaria, junto com a legitimidade da assinatura.
