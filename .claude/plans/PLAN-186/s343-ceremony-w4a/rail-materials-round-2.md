# wave-s343-w4a — rail de MATERIAIS rodada 2 (pós-curas da r1, S343 2026-09-04)

Rail-Verdict: APPROVE

Instrumento: os MESMOS gates da r1, re-executados sobre a árvore de harness
DEPOIS das duas curas (exec-bit; comentário que começava com a palavra
reservada do linter) e do acréscimo do **G7**. Material curado no vivo é
invisível à sombra que o rail revisa — por isso a árvore foi re-sincronizada e
re-commitada antes desta rodada.

## Resultado

```
check-ceremony-script.py                      rc=0   (blocking_unwaived = 0)
git ls-files --stage .claude/plans/PLAN-186/  → 100644 em TODOS os artefatos
bash -n            : 5/5 scripts OK
shellcheck -S warning : 5/5 scripts OK
py_compile         : apply-w4a-validate-deletion.py OK
bijeção `_expect`  : 38 chaves (2 novas do G7); 0 órfãs nos DOIS sentidos
git apply --check  : o W4A.patch aplica na árvore de harness
```

## Varredura de variável não-atribuída (regex própria, split em `;`/`\n`/`&`/`|`)

Quatro dos cinco scripts: NENHUMA. O quinto devolveu dois nomes, os DOIS
verificados à mão e **falsos positivos** — registrados porque «o instrumento
exige o mesmo escrutínio adversarial que o sujeito»:

| nome | sítio | por que é falso positivo |
|---|---|---|
| `NO_COMMIT` | `test-ceremony-scripts-w4a.sh:596` | está DENTRO de um programa `awk` entre aspas simples (`'/if \[ "\$NO_COMMIT" = "1" \]; then/'`) — é texto literal do contrato T20a, que grepa o `finalize-w4a.sh`, não uma variável deste script |
| `_d` | `test-ceremony-scripts-w4a.sh:247` | `( _d="$1"; shift; cd "$_d" ...)` — atribuído no MESMO segmento, dentro de um subshell; a regex exige o nome no início do segmento e o `(` a bloqueia |

## O que esta rodada NÃO cobre

- O `Validate` e o `Smoke Install` do CI: só rodam depois do push.
- O ramo `covered` do G7 (os dois legs já obrigatórios): só é exercitável
  contra a config viva do GitHub, no land real. O ramo que EXIGE o
  reconhecimento tem controle positivo (T25).
- A perna GPG: o modo auto-teste substitui a assinatura por um `.asc`
  sintético; ela é exercitada pelo land real do Owner.
