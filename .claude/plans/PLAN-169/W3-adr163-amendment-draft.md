# Draft — emenda ADR-163 (decisão do W2.2; texto para o pack W3)

> Status: DRAFT para inclusão no pack canônico W3 (ADRs são superfície
> canônica — cerimônia). A implementação já landou no W2.2 (superfície
> livre de teste); esta emenda REGISTRA a decisão de gate.

## Amendment: p95-on-CI substitui median-on-CI nos probes de teste (N=200)

**Contexto.** O ADR-163 fixou N=200 + pré-condição de colapso no gate de
CI do profiler. Os probes de TESTE da mesma família
(`test_case_a_p99_under_5ms`, N=100;
`test_emit_pair_end_to_end_loop_p95_within_budget`, N_TRIALS=20)
ficaram fora do passe original: o primeiro gateava a MEDIANA em CI
(porque o p99 de N=100 flakava com um spike — S297: 5.25 ms/5 ms), o
segundo tinha os índices p95/p99 COLAPSADOS (`int(19*.95) ==
int(19*.99) == 18`), a classe exata que o ADR nomeia.

**Decisão (PLAN-169 W2.2).**
1. N=200 no probe Case-A e N_TRIALS=40 no probe end-to-end; índices
   SEMPRE derivados da constante pela truncação nearest-rank do
   `_pct_of_sorted` (`int((n-1)*p/100)`) — nunca hardcoded.
2. A pré-condição de colapso do ADR-163 (`i95 != i99`) é ASSERTADA
   dentro do teste, antes do loop medido — um edit futuro que abaixe N
   não recria o gate colapsado em silêncio.
3. **Em CI/carga (`GITHUB_ACTIONS`/`CI`/`CEO_FINISH_CEREMONY`): gate no
   p95 REAL, não mais na mediana.** Racional: com N=200 o p95 ignora as
   10 maiores amostras — um punhado de spikes de scheduler não flaka,
   enquanto uma regressão real de latência o move. A mediana escondia
   degradação de cauda inteira; o p95 é o compromisso que o N maior
   compra. Local/quieto: p99 estrito inalterado. Budgets inalterados.

**Consequência.** O switch median-on-CI (PLAN-112-FOLLOWUP) fica
historicamente registrado e SUBSTITUÍDO. Qualquer novo probe percentil
nasce com: N que satisfaz a pré-condição, índices derivados, e gate em
percentil real (nunca mediana) quando N ≥ 200.
