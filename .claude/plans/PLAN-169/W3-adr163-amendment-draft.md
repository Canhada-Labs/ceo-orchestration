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
3. **Em CI/carga: a MEDIANA FICA — reavaliada e MANTIDA com evidência
   ao vivo.** A tentativa p95-on-CI flakou no PRIMEIRO run real
   (validate run 31288404989: p95=6,31 ms vs mediana=3,83 ms contra
   budget de 5 ms): runner compartilhado carregado desloca a
   DISTRIBUIÇÃO INTEIRA (~6× a mediana local), então qualquer percentil
   de cauda real precifica o runner, não o código. A mediana é estável
   sob esse deslocamento e ainda pega a regressão ~8× que o probe
   existe para pegar. Local/quieto: p99 estrito inalterado. Budgets
   inalterados.

**Consequência.** O switch median-on-CI (PLAN-112-FOLLOWUP) sai de
"intuição de flake" para DECISÃO COM EVIDÊNCIA (o run acima). Qualquer
novo probe percentil nasce com: N que satisfaz a pré-condição, índices
derivados, mediana em ambiente de carga compartilhada e percentil real
apenas em ambiente controlado.
