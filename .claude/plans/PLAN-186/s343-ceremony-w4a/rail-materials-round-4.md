# wave-s343-w4a — rail de MATERIAIS rodada 4 (fechamento, S343 2026-09-04)

Rail-Verdict: APPROVE

Re-execução dos gates do pacote sobre a árvore de harness com os materiais
FINAIS commitados (incluindo as curas dos rails r4 e r5 e as contagens
reconciliadas).

```
check-ceremony-script.py                        rc=0  (blocking_unwaived = 0)
git ls-files --stage .claude/plans/PLAN-186/    → 100644 em TODOS os artefatos
bash -n            : 5/5 OK        shellcheck -S warning : 5/5 OK
py_compile         : apply-w4a-validate-deletion.py OK
bijeção `_expect`  : 39 chaves; 0 órfãs nos DOIS sentidos
git apply --check  : o patch aplica na árvore de harness E na árvore VIVA
harness            : 27/0/0 em DUAS execuções consecutivas (runs 4 e 5)
```

## O que mudou desde a r3, e por que a rodada se repete

As curas dos rails r4 e r5 tocaram o **derivador** (E5 e E7) e, por
consequência, o patch e quatro documentos. Material curado no vivo é invisível
à sombra que o rail revisou — por isso a árvore foi re-sincronizada e
re-commitada antes desta rodada, e o harness rodou de novo sobre os bytes
resultantes.

## Reconciliação de contagem que esta rodada pegou

A citação «11 hunks» valia para `git diff -U0`; o patch gerado com contexto
default tem **10** (dois vizinhos se fundem). Citar um número sem dizer sob
qual contexto é a mesma imprecisão que os rails r4/r5 acharam na prosa — os
três documentos agora dizem os DOIS.

## O que segue fora do alcance de qualquer rodada

- O `Validate` e o `Smoke Install` do CI: só rodam depois do push.
- O ramo `covered` do G7: só é exercitável contra a config viva do GitHub.
- A perna GPG: exercitada apenas pelo land real do Owner.
- As 3 corridas de medição: são o `OWNER-S343-W4A-MEASURE.sh`, depois do land.
