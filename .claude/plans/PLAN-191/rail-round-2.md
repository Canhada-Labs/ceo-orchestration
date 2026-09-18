# PLAN-191 — rail round 2 (FINAL) (Codex GPT-6 Astra, `codex review --uncommitted`, 2026-09-18)

**Sujeito revisado:** diff não commitado após as curas da r1 — `PLAN-191-…md` (inclui as quatro
edições do braço Haiku-sinais/`$.model.classify` que a r1 não viu), `PLAN-191/rail-round-1.md` e
`CLAUDE.md` §5. Saída bruta no scratchpad da sessão (`codex-review-plan191-r2.out`, 255 KB).

**Veredito:** `REJECT — the experimental decision rules can produce biased labels, approve an inferior
external lane, and miss genuine pruning savings. Read-only freshness and count checks passed.`
Três P2, nenhum P0/P1. **Os cinco P2 da r1 não reapareceram.**

**Regra de parada aplicada (pré-registrada na r1; origem S349 «rodada final com anexo»):** NO-GO só por
condição FALSA ou P0; achado novo P1/P2 = ANEXO. Esta é a rodada FINAL — não há r3. As três curas
abaixo foram aplicadas ao plano como anexo e **não foram re-revisadas por outro fornecedor**
(resíduo declarado).

| # | achado (Codex) | classe | cura (anexo) |
|---|---|---|---|
| 1 | Referência cega: maioria 3-1 (3 lanes Claude + Codex) aceita um erro correlacionado das lanes Claude sem adjudicação — preserva a falha da C9 e pode enviesar a referência a favor do baseline Haiku | juízes correlacionados contados como independentes | as 3 lanes Claude = UM voto de família; Codex = outro; rótulo só com concordância entre fornecedores; discordância ⇒ Owner |
| 2 | Gate de promoção compara Jev só com SetFit/Haiku (censo) e SBERT (recidiva): regex e busca lexical, medidos na mesma wave, ficam fora do máximo — a regra pode promover uma lane externa mais fraca que um baseline sem egresso já existente (ex.: lexical 90 %, SBERT 80 %, Jev 84 %) | máximo incompleto | `B` = melhor entre TODOS os baselines sem egresso medidos (regex, SetFit, lexical, Haiku-sinais; recidiva: lexical, SBERT); `Δ` e `T` contra `B`; Regra de parada espelhada |
| 3 | W4 gated em F, mas `gateboot_repay.py:127` computa F como o primeiro input pós-compactação menos os tokens do resumo — histórico e resumo podem encolher muito com F inalterado; o gate seria cego ao ganho | métrica cega ao efeito | SUCESSO = tokens processados −20 % OU compactações/sessão −30 %, ambos com re-execuções ≤ +10 %; F vira diagnóstico |

**Verificação própria do fato de instrumento (achado 3):** ver a leitura de `gateboot_repay.py:118-136`
registrada na sessão S355 — a definição de F citada pelo Codex foi conferida antes de mudar o gate.

**Estado ao fim do rail:** plano `draft`, sem commit, pronto para as 4 OQs do Owner. Toda cura de r1
e r2 é texto de pré-registro; nenhum item de código, nenhum canônico tocado.
