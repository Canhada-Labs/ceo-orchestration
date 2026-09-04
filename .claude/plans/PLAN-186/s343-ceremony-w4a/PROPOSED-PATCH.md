# PROPOSED — wave-s343-w4a (PLAN-186 W4a)

> Este é o registro DA REVISÃO: ele aponta para o patch EXATO que o rail leu e
> que o Owner assina. O `Patch-sha256` abaixo é conferido pelo P1 do SIGN
> contra o sha do arquivo e contra o do sentinel — três lugares, um número.

Status: PROPOSED
Plans: PLAN-186
Wave: wave-s343-w4a
Patch: .claude/plans/PLAN-186/s343-ceremony-w4a/W4A.patch
Patch-sha256: 35e26cdc47e606d12eca45a267d6c147a3ed8f381693a25782f3f823066f6db3
Patch-base: 76578f33eaa25a373643a96d7df908ebd3082408
Sentinel: .claude/plans/PLAN-186/wave-s343-w4a-approved.md

## Escopo

2 paths, os DOIS canônicos, 10 hunks no patch (11 sob `git diff -U0`),
`83 insertions(+), 40 deletions(-)`:

| path | canônico | kernel | o que muda |
|---|---|---|---|
| `.github/workflows/validate.yml` | sim | **sim** | E2/E3 os dois steps deletados; E4 declaração da perda aceita no `env:` da matriz; E1+E6..E11 os SETE comentários que citavam os steps deletados, reconciliados |
| `.github/workflows/smoke-install.yml` | sim | não | E5 `timeout-minutes: 126 -> 150` + bloco novo de derivação MEDIDA (o ledger aditivo fica) |

Zero `.py`, zero `.sh`, zero membros do manifesto ADR-192.

## O que a revisão precisa olhar

1. **A deleção é autorizada por COBERTURA, e a cobertura é re-derivada** —
   não citada. O V5 do LAND roda `pytest --collect-only` nas três raízes e
   compara CONJUNTOS de node-ids (sha256 da lista ordenada) em dois recortes
   (todos e `-m 'serial'`). Se a união dos dois steps deixar de ser a matriz,
   o land aborta.
2. **O delta de ambiente é DUPLO e os dois lados são perdas ACEITAS**, uma
   delas escrita no próprio arquivo (E4). Ver a tabela do sentinel.
3. **O bump do timeout troca a CONCLUSÃO e preserva a HISTÓRIA.** O V6b
   verifica as duas coisas: o bloco novo existe E as duas linhas-marco do
   ledger aditivo continuam lá.
4. **O que NÃO entra:** split de jobs, `fail-fast`, composite action,
   required checks. O último é um residual NOMEADO no sentinel — a decisão é
   do Owner.

## Rodadas de rail

Ver `rail-round-*.md` neste diretório (patch) e `rail-materials-round-*.md`
(materiais). O SIGN exige que o ÚLTIMO `rail-round-N.md` traga
`Rail-Verdict: APPROVE` — igualdade exata, sem qualificador.
