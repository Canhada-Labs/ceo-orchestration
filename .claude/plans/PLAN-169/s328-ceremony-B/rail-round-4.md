# Pair-rail — wave-s328-B, rodada 4

Comando: `codex exec review --uncommitted` na árvore-sombra
`<scratchpad>/shadow-163` (base `560dad0`), saída em `pkgB-rail-4.txt`.
`codex-cli 0.147.0`, rc 0, saída não-vazia.

**Veredito da rodada:** REJECT — 2 × P1, 1 × P2. **Zero achados de conteúdo.**

---

## O que MUDOU: o P2-A da rodada 3 FECHOU

O erro de fronteira da cota de admissibilidade — o achado que pagou a rodada 3
— **não voltou**. A cura foi a estritez (`K_e <= …` → `K_e < …`) mais o
sub-item que nomeia a divergência com o código como pré-condição da fase 2.
É o segundo achado de conteúdo curado e confirmado por rodada seguinte (o
primeiro foi o P1-2 da rodada 1, sobre o auto-cap).

## Os três achados desta rodada, todos da mesma forma

| # | achado | rodada em que apareceu antes |
|---|---|---|
| P1-1 | flags do profiler não implementadas (`validate.yml:1272-1273`) | 1, 2, 3 |
| P1-3 | sentinel assinado ausente para o ADR-144 (`ADR-144:114`) | 1 |
| P2-B | OQ-7..OQ-12 inexistentes (`ADR-163:575`) | 1, 3 |

Os três dizem a mesma coisa: **o revisor vê metade do quadro.** A sombra
contém o patch canônico e mais nada — não contém a metade não-canônica (que
vive em `HEAD` depois do commit comum do CEO) nem os materiais de cerimônia
(que vivem no checkout vivo, fora do patch por construção).

Nenhum dos três é curável por edição da sombra:

- **P1-1** — curá-lo na sombra significaria mover ~800 linhas de código
  não-canônico para dentro de um patch assinável. É exatamente o desenho que a
  síntese dos três críticos rejeitou (`canonical_diff_minimal`: «validate.yml
  ONLY, 3 functional lines»).
- **P1-3** — o sentinel É este pacote. Pedir que ele esteja dentro da sombra é
  pedir que a autorização viaje dentro do objeto que ela autoriza.
- **P2-B** — as OQ-7..OQ-12 vivem no `PLAN-169`, que não é arquivo canônico e
  entra no mesmo commit comum do CEO.

## Curas (todas MECÂNICAS, todas fora do alcance do revisor)

- `G-PRE` no **SIGN**, no **LAND** e no **finalize-B.sh**: lê `git show HEAD:`,
  exige as 4 flags do profiler, o arquivo de teste do gate, e ≥ 6 referências a
  OQ-7..OQ-12. Aborta **nomeando** o que falta e qual commit resolve.
- **G5** do LAND: `_sentinel_grants_path` — a MESMA função do hook — prova path
  a path que o sentinel assinado concede cada path canônico tocado. Assinatura
  válida que concede zero paths não autoriza nada (lição S318).
- **T8** do harness: remove a flag do profiler **em commit** e exige o land
  vermelho com a razão nomeada. Controle POSITIVO do `G-PRE`.

## Balanço

| # | severidade | veredito | ação |
|---|---|---|---|
| P1-1 | P1 | verdadeira sobre a árvore lida; incurável NELA | G-PRE ×3 + T8 |
| P1-3 | P1 | descreve a pré-condição da própria cerimônia | pushback; G5 responde |
| P2-B | P2 | verdadeira sobre a árvore lida; incurável NELA | G-PRE |

Nenhuma edição na sombra nesta rodada.
