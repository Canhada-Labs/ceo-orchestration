# wave-s343-w4a — rail de MATERIAIS rodada 3 (execução real do finalize, S343 2026-09-04)

Rail-Verdict: APPROVE

## O buraco que esta rodada fechou

O harness clonado do molde exercitava SIGN e LAND, mas **não** o
`finalize-w4a.sh` — e ele é o PRIMEIRO comando que o Owner roda. Um script de
cerimônia nunca executado é uma afirmação, não um instrumento
(`feedback-blockers-expire-verify-before-asking`). Esta rodada o executou de
verdade, contra a árvore de harness com os materiais commitados:

```
CEO_W4A_SHADOW=<sombra> bash .../finalize-w4a.sh --no-commit     rc=0
```

## O que a execução PROVOU

| passo | resultado |
|---|---|
| 0 pré-condições | HEAD em `main`, sombra resolvida, `.asc` ausente |
| 1 EXPECTED × derivador | os 2 paths batem nos dois sentidos |
| 2 guard de drift | nenhum path do pacote derivou entre a base da sombra e o HEAD |
| 3 árvore-sombra + cópia | 2 arquivos copiados, 0 removidos, sem marcador de conflito |
| 4a reprodutibilidade | `HEAD + derivador == sombra`, byte a byte, nos 2 paths |
| 4b topologia | 7 jobs / `validate` 48 steps; `smoke` timeout 150 |
| 4c lint | actionlint + pins de action verdes |
| 4d cobertura | união == matriz por CONJUNTO, nos 2 recortes |
| 4e não-vácuo | 2 steps fora; timeout novo com o ledger aditivo preservado |
| 5 patch/Scope/base | **patch inalterado** (`66219c2b…`) e `Scope` DERIVADO |
| 6 `--no-commit` | nada staged nem commitado, com a razão impressa |

**O achado que mais importa é um NEGATIVO forte:** o patch que o
`finalize_patch.py` gerou é **byte-idêntico** ao que eu havia gerado à mão com
`git diff HEAD --binary` da sombra, e o bloco `Scope:` que ele DERIVOU de
`git apply --numstat` é exatamente os dois paths que o sentinel declarava. Duas
rotas independentes para o mesmo artefato.

`Patch-base` foi re-escrito para o HEAD da árvore em que rodou — que é o
comportamento correto: o commit dos materiais move o HEAD de propósito, e o
SIGN valida ancestralidade + ausência de drift nos paths tocados, não
igualdade.

## Nenhum editor abriu

O `--no-commit` imprimiu os 4 materiais e o próximo comando, e saiu. O fluxo
do Owner (`finalize` → `SIGN` → `LAND --dry-run` → `LAND` → `MEASURE`) não
passa por editor em nenhum ponto.
