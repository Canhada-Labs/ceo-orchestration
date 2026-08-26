# Pair-rail — PACOTE A, rodada 3 (S328, 2026-08-25) — última do patch de 3 paths

> **Nota escrita DEPOIS:** esta era para ser a rodada final, e teria sido se o
> escopo não mudasse. O CEO decidiu a rota 1 sobre o achado 1 (incluir
> `CLAUDE.md` no patch), o escopo foi a 4 paths, e a **rodada 4** revisou esse
> conteúdo — ela é a rodada do artefato que o Owner assina. O critério de
> parada declarado abaixo continua válido para o que ele mediu: o patch de 3
> paths.

**Comando:** `codex exec review --uncommitted` na árvore-sombra já **re-baseada
no HEAD vivo `560dad0`** — isto é, sobre exatamente os bytes que o `A.patch`
carrega (`sha256 056e5ce3…`).
**Artefato:** `<scratchpad>/pkgA-rail-3.txt` · **rc:** 0 · **duração:** ~14 min.
**Veredito literal:** REJECT implícito — 2 achados (2× P1), sem
`VERDICT: APPROVE`.

## Resultado: os MESMOS dois P1, nenhuma classe nova

| # | achado | 1ª aparição | disposição |
|---|---|---|---|
| 1 | `CLAUDE.md:102` contradiz o ADR promovido | rodada 1 | REAL, **ESCALADO** ao CEO (fora do FILE ASSIGNMENT) |
| 2 | "falta sentinel assinado para os edits guardados" | rodada 1 | **PUSHBACK** estrutural (o rail lê a sombra) |

O P2 da rodada 1 (nightly futuro registrado como evidência colhida) continua
ausente — a cura segurou por duas rodadas.

`scripts/install.sh` e `scripts/tests/test-manifest-delivery-route.sh`
atravessaram **três** rodadas sem um único apontamento. O discriminante
line-exact e o par `S.17` / `S.17-control` são a parte do pacote que o rail
mais leu (ele abriu `install.sh:2688-2732`, `upgrade.sh:4700-4785` e o teste
inteiro) e sobre a qual nada teve a dizer.

Na rodada 3 o rail também formulou o achado 1 com mais precisão do que eu
tinha: ele cita `CLAUDE.md:10-17` (o Gate 1 obrigatório) para explicar **por
que** a contradição importa — não é documentação desatualizada, é governança
contraditória entregue **no boot** de toda sessão. Essa formulação está
incorporada no relato ao CEO.

---

## Critério de parada — cumprido como declarado ANTES da rodada

O critério estava escrito em `rail-round-2.md` antes desta rodada existir:
*"nenhuma classe nova de achado, e toda pendência com disposição escrita"*.
A rodada 3 satisfaz os dois, sobre o conteúdo **final** do patch. Paro em 3.

Insistir numa 4ª rodada re-derivaria os mesmos dois — e a lição registrada
neste repositório é que classe que se repete pede **mudança de alvo**, não mais
rodadas. Dos dois remanescentes: um é insolúvel no alvo (a sombra não pode
conter o pacote de cerimônia, por construção) e o outro é uma decisão que não
me pertence.

---

## Achado colateral do INSTRUMENTO (não é do patch, mas afeta a manhã)

Ao investigar o estado da sombra depois da rodada 3, encontrei uma modificação
que **não era minha**:

```
 M docs/threat-model.md      # **Status:** accepted -> stale
```

**Primeira hipótese, REFUTADA por controle:** suspeitei do
`check-canonical-doc-freshness.py --help`, que o rail rodou minutos antes.
Medido num clone limpo — `--help` sai rc 0 e o sha256 do
`docs/threat-model.md` fica **idêntico** (`44be302b…` antes e depois). A
hipótese estava errada e o controle disse isso.

**Causa real, medida:** o rail rodou
`python3 .claude/scripts/check-threat-model-freshness.py`, e o script
**escreve**. A saída dele, verbatim:

```
STALE: 194 new ADR(s) since 2026-06-12 (threshold=2): ...
STATUS FLIPPED: accepted -> stale in threat-model.md
```

O comportamento é **por desenho** — o próprio docstring do script anuncia
`1 — STALE: >=2 new in-scope ADRs without review; status flipped`. Não é
defeito deste pacote nem daquele script.

**Mas é um risco operacional para a manhã, e ele é reprodutível hoje.**
Num clone limpo do HEAD vivo `560dad0`, uma única invocação do script sai
`rc=1` e deixa a árvore **suja num path rastreado**
(`44be302b…` → `4017fd86…`). O `P0` do `OWNER-S328-A-SIGN.sh` aborta com
"modificações RASTREADAS na árvore" diante de qualquer modificação rastreada —
então **quem rodar esse checker no checkout vivo antes da assinatura derruba a
cerimônia**, e a mensagem de abort vai falar de um arquivo que ninguém editou.

Recuperação, se acontecer: `git checkout -- docs/threat-model.md` e repetir o
passo. Relatado ao CEO junto com o achado 1.

Ação tomada aqui: `git checkout -- docs/threat-model.md` na sombra. Verificado
depois — a sombra volta a mostrar **exatamente** os 3 arquivos do pacote, e o
`sha256` do `A.patch` continua `056e5ce3…` (o patch fora gerado antes da
rodada 3, então nunca carregou o arquivo; medido por `grep -c threat-model`
= 0).

---

## Estado final verificado

| verificação | resultado |
|---|---|
| `git -C <sombra> status --short` | exatamente os 3 paths do pacote |
| `shasum -a 256 A.patch` | `056e5ce35d7cdc5503aba24ce0a1a7d388338d0d06329d4d509e90f07dcecc74` |
| `Patch-sha256` no sentinel | idêntico |
| `Patch-base` no sentinel / `BASE-SHA.txt` | `560dad00ff8fba81584208014e04bbe8572bb83e` (= HEAD vivo) |
| `git apply --check A.patch` no checkout vivo | rc 0 |
| `docs/threat-model.md` no checkout VIVO | limpo |
