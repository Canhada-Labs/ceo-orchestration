# wave-s343-w4a — rail codex rodada 6 (patch final, S343 2026-09-04)

Rail-Verdict: APPROVE

Comando: `codex exec review` em modo PROMPT, com os SEIS fatos já
estabelecidos dados como GIVEN, e o pedido explícito: ler **cada linha de
comentário que o diff acrescenta** e cada comentário adjacente a uma mudança,
e dizer se alguma afirmação é falsa, não sustentada, auto-contraditória ou uma
atribuição de causa que a evidência não carrega. Saída bruta:
`evidence/rail-r6-raw.txt`.

## Veredito, verbatim

«**No actionable issues found.** The added and adjacent comments are
consistent with the workflow behavior and supplied facts, and actionlint plus
diff validation pass.»

## Por que ESTA rodada é a que fecha

As rodadas 4 e 5 acharam quatro imprecisões, todas em prosa que EU escrevi, e
cada cura gerou a superfície que a rodada seguinte revisou — «rodada limpa
prova a SUPERFÍCIE revisada, não o entregável». A r6 revisou exatamente a
superfície final, com o pedido apontado para o ponto onde as quatro falhas
apareceram (as linhas de comentário acrescentadas), e não achou nada.

## Estado do artefato aprovado

```
patch    : 35e26cdc47e606d12eca45a267d6c147a3ed8f381693a25782f3f823066f6db3
base     : 76578f33eaa25a373643a96d7df908ebd3082408
paths    : 2, os DOIS canônicos (validate.yml é KERNEL)
edições  : 11, com âncora exata e contagem declarada
hunks    : 10 no patch (11 sob `git diff -U0`)
numstat  : 42/1 smoke-install.yml + 41/39 validate.yml
actionlint (flags EXATOS do step da CI) : rc=0
validate : 7 jobs, job `validate` 48 steps (HEAD: 50)
smoke    : 1 job, timeout 150 (HEAD: 126)
menções a hook-tests-python-matrix : 8 (1 definição + 7 comentários)
```

## Série completa (patch)

| rodada | modo | achados |
|---|---|---|
| r1 | `--uncommitted` | 2 P1 — required-check (REAL, virou o G7) + sentinel ausente (estrutural) |
| r2 | prompt + contexto | 1 P2 — CLASSE dos comentários órfãos (REAL, virou E6..E11 + V6c) |
| r3 | `--uncommitted` | 0 NOVOS; reabriu o required-check |
| r4 | prompt + 4 fatos | 2 P3 REAIS — claim de PyYAML e atribuição ao runner |
| r5 | prompt + 5 fatos | 2 P3 REAIS — lede contraditório e npm packlist ≠ pytest |
| **r6** | **prompt + 6 fatos** | **NENHUM** |

Sete achados reais no patch, todos curados no derivador e cada um com o gate
ou o controle positivo correspondente.
