# Pair-rail — wave-s328-B, rodada 3

Comando: `codex exec review --uncommitted` na árvore-sombra
`<scratchpad>/shadow-163`, agora rebasada no **HEAD vivo `560dad0`** (o refresh
do passo 3 da cerimônia; as modificações viajaram sem conflito, `numstat`
idêntico antes e depois). Saída em `pkgB-rail-3.txt`. `codex-cli 0.147.0`,
rc 0, saída não-vazia.

**Veredito da rodada:** REJECT — 1 × P1, 2 × P2.

---

## P2-A — «Use a strict admissibility bound for K» (`ADR-163:466-469`)

**O achado que pagou a rodada.** Claim: quando `K_e` é igual à cota superior
admitida, o controle positivo do pior caso tem
`hook_p50 = baseline_p50_e + 150 = K_e × ref_p50`; a regra relativa aceita
igualdade, então o controle **passa** em vez de dar `real_regression`.

**Verificação — VERDADEIRA, e é erro de FRONTEIRA no critério de decisão.**
Lido nos dois lados:

| sítio | forma | aceita igualdade? |
|---|---|---|
| `profile-opus-4-7.py:629` | `rel_ok = hook_p50 <= k_e * ref_p50` | **sim** |
| `profile-opus-4-7.py:697` | rejeita `K` que *excede* `admissibility_max_K` | **sim** (admite `K == cota`) |
| ADR-163:467 (antes da cura) | `K_e <= (baseline_p50_e + 150) / max(ref_p50)` | **sim** |

Com os três aceitando igualdade, em `K_e = cota` exatamente e
`ref_p50 = max(ref_p50)`, o plant de +150 ms dá
`baseline+150 <= baseline+150` ⇒ `rel_ok` VERDADEIRO ⇒ o controle **passa**.
A garantia que a emenda declarava — «o controle positivo de +150 ms ainda
reprova na PIOR referência observada» — é falsa exatamente nesse ponto. E não é
um ponto qualquer: é o ponto que a fórmula seleciona quando o intervalo é
apertado. Uma cota não-estrita torna o argumento de admissibilidade
**decorativo**.

**Cura, na sombra (texto canônico).** A cota passa a ser `<` estrito, com um
sub-item que (a) explica por que a estritez não é cosmética, e (b) **nomeia a
divergência com o código**: hoje `profile-opus-4-7.py` admite `K == cota` e
compara com `<=`; ou a checagem da cota vira `K >= cota ⇒ rejeita`, ou a
comparação vira estrita — **uma das duas, não as duas**, senão o intervalo
fecha duas vezes.

**O que NÃO foi feito, e por quê.** O código não foi tocado.
`profile-opus-4-7.py` é **não-canônico** e está fora do meu FILE ASSIGNMENT;
além disso o sítio é de **fase 2 apenas** — nenhum `K` se aplica em fase 1, que
é o que este pacote embarca, então nenhuma execução alcança o ramo enquanto
isto estiver no `main`. Registro explícito: **não-canônico — o CEO cura no
main**, por commit comum. A emenda deixa isso escrito como **pré-condição
NOMEADA do pacote da fase 2**: embarcar fase 2 com `<=` dos dois lados
restauraria exatamente o buraco que esta rodada fechou. O
`wave-s328-B-approved.md` foi reconciliado com um residual declarado no mesmo
sentido.

## P1-1 (3ª repetição) — flags do profiler

Idêntico às rodadas 1 e 2, agora com o revisor lendo `560dad0`. Confirmado de
novo em disco: o `HEAD` vivo ainda não carrega a metade não-canônica (o
profiler curado e o teste do gate seguem como modificação de árvore de
trabalho, `+794/−17`). A sombra rebasada herda a ausência.

Cura inalterada e MECÂNICA: o gate `G-PRE` do `OWNER-S328-B-LAND.sh` — e agora
também do `OWNER-S328-B-SIGN.sh` e do `finalize-B.sh` — lê de
`git show HEAD:`, exige as 4 flags e o arquivo de teste, e **aborta nomeando**.
O `SIGN` checa antes de assinar de propósito: commitar o profiler DEPOIS da
assinatura moveria o HEAD e invalidaria o `Anchor-SHA`. O harness
`test-ceremony-scripts-B.sh` tem o caso **T8**, que remove a flag **em commit**
(não na árvore) e exige o land vermelho com a razão nomeada.

## P2-B (repetido) — OQ-7..OQ-12

Idêntico ao P2-4 da rodada 1, agora citando `PLAN-169:1309-1379` como a região
que define apenas OQ-1..OQ-6. Mesma medição, mesma causa, mesma cura: as
OQ-7..OQ-12 existem no checkout vivo (7 ocorrências) e não em `HEAD`; o
`G-PRE` exige ≥ 6 em `git show HEAD:` e aborta nomeando.

---

## Balanço

| # | severidade | veredito | ação |
|---|---|---|---|
| P2-A | P2 | **verdadeira — erro de fronteira real** | cota `<=` → `<` na ADR + divergência do código NOMEADA como pré-condição da fase 2; residual no sentinel |
| P1-1 | P1 | verdadeira sobre a árvore lida, estruturalmente inevitável nela | G-PRE em SIGN + LAND + finalize; caso T8 no harness |
| P2-B | P2 | idem | mesma cura |

Nenhum achado de conteúdo novo além do P2-A. O padrão das três rodadas é
consistente: o rail está encontrando defeitos de **texto que afirma
propriedades do código** — primeiro o auto-cap que «removia» o rótulo errado
(rodada 1), agora a cota que «preservava» a detecção. Ambos eram falsos, e
ambos só apareceram porque o revisor leu o código que o texto descrevia.
