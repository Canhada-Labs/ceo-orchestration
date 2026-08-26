# Pair-rail — PACOTE A, rodada 4 (S328, 2026-08-25) — a rodada do artefato assinado

**Comando:** `codex exec review --uncommitted` na árvore-sombra, agora com os
**4** paths do pacote — o `CLAUDE.md` entrou depois da decisão do CEO (rota 1
sobre o achado 1 das rodadas 1–3).
**Artefato:** `<scratchpad>/pkgA-rail-4.txt` · **rc:** 0 · **duração:** ~13 min.

## Resultado: rodada LIMPA — zero achados

O artefato inteiro tem **161 bytes** e é só o sumário. Verbatim:

> "The exact-line continuity check is correct and preserves existing behavior.
> Bash syntax, the 127-case targeted shell suite, and repository claim checks
> all pass."

**Não há seção `Full review comments:`.** Nas rodadas 1, 2 e 3 essa seção
existia e listava os P1/P2; aqui ela não é emitida — é assim que este
instrumento representa uma rodada sem achados.

### Sobre o token literal `VERDICT: APPROVE`

Ele **não aparece** — e não aparece em nenhuma das quatro rodadas, porque
`codex exec review` não emite esse token: o formato dele é *sumário + (quando
há) a lista de comentários*. Registro isso explicitamente para não fabricar um
veredito que a ferramenta nunca produziu. O que se pode afirmar com base no
artefato, e só isso:

- `rc = 0`;
- **zero** achados de qualquer severidade (P0/P1/P2), contra 3, 2 e 2 nas
  rodadas anteriores;
- uma afirmação POSITIVA e específica sobre o objeto revisado — "the
  exact-line continuity check is **correct** and preserves existing behavior" —
  não um silêncio.

Isto não é "aprovado por silêncio": é uma rodada com saída, com conteúdo, e sem
achado. O contraste com as três rodadas anteriores do MESMO instrumento sobre a
MESMA árvore é o que dá sentido ao resultado.

## O que fechou entre a rodada 3 e a 4

| achado | rodadas 1–3 | rodada 4 |
|---|---|---|
| `CLAUDE.md:102` contradiz o ADR promovido | P1 aberto em 3 rodadas | **CURADO** — a linha entrou no patch (rota 1, decisão do CEO) |
| "falta sentinel assinado" | P1 em 3 rodadas (PUSHBACK) | **não reaparece** |
| nightly futuro como evidência colhida | P2 na rodada 1 | ausente desde a 2 |

O sumiço do achado do sentinel na rodada 4 não muda a análise das rodadas
anteriores: ele continua sendo um limite do alvo (a sombra não contém o pacote
de cerimônia), e o gate que responde de verdade continua sendo o **G5** do LAND.
Registro a ausência como observação, não como refutação retroativa.

## Verificação de que a sombra não sofreu efeito colateral nesta rodada

Diferente da rodada 3 — onde o rail rodou `check-threat-model-freshness.py` e
sujou `docs/threat-model.md` — a rodada 4 deixou a sombra com **exatamente** os
4 paths do pacote:

```
 M .claude/adr/ADR-194-delivery-route-resolution.md
 M CLAUDE.md
 M scripts/install.sh
 M scripts/tests/test-manifest-delivery-route.sh
```

## Patch re-finalizado DEPOIS desta rodada

Ordem deliberada: a rodada 4 revisou a sombra, e só então o `finalize_patch.py`
gerou o patch a partir dela. O artefato assinado é, byte a byte, o conteúdo
revisado.

| campo | valor |
|---|---|
| `sha256(A.patch)` | `dc048da4be3a9713e3cd3797b03d18387aedc0cfe1ecdde4e85fabf16656dfe3` |
| tamanho | 32.238 bytes |
| `Patch-base` / `BASE-SHA.txt` | `560dad00ff8fba81584208014e04bbe8572bb83e` (= HEAD vivo) |
| Scope derivado | 4 paths (2 canônicos, 0 membros do manifesto ADR-192) |
| `git apply --check` no vivo | rc 0 |
| `CLAUDE.md` no `--numstat` | `1 1` — uma inserção, uma remoção |

**Gate de tamanho, medido e não presumido:**
`bash .claude/scripts/validate-governance.sh` COMPLETO na sombra — rc 0, 22
gates, **0 erros**, e o gate específico imprime
`OK: CLAUDE.md is 32152 bytes (limit 40000)`. O `--fast` não checa esse limite;
por isso a condição do CEO era rodar o completo, e foi o completo que rodou.
