# wave-s343-w4a — rail de MATERIAIS rodada 1 (gates + lint, S343 2026-09-03/04)

Rail-Verdict: CHANGES-REQUESTED (1 BLOCKING real: exec-bit no índice)

Instrumento: os gates que o próprio pacote declara, executados sobre uma
árvore de harness (`git clone --local` do HEAD vivo) com os 14 materiais
COMMITADOS — a única árvore em que a pergunta «o pack em HEAD está correto?»
tem sentido (lição T-S329-2).

## Achado 1 — `[R8/BLOCKING] exec-bit no índice git (modo 100755)` — REAL

```
python3 .claude/scripts/check-ceremony-script.py        rc=1
  blocking_unwaived = 4
  [R8/BLOCKING] .claude/plans/PLAN-186/OWNER-S343-W4A-LAND.sh:0
  [R8/BLOCKING] .claude/plans/PLAN-186/OWNER-S343-W4A-SIGN.sh:0
  [R8/BLOCKING] .claude/plans/PLAN-186/s343-ceremony-w4a/finalize-w4a.sh:0
  [R8/BLOCKING] .claude/plans/PLAN-186/s343-ceremony-w4a/test-ceremony-scripts-w4a.sh:0
```

**O V9a do PRÓPRIO LAND teria abortado** (`check-ceremony-script.py` diferente
de 0). Causa: um `chmod +x` na montagem do pacote. Os scripts do molde
(`PLAN-169/OWNER-S338-*`, `s338-ceremony-fable51/*`) são `100644` no índice —
verificado com `git ls-files --stage`, não lembrado.

**Cura nos DOIS lados** (CLAUDE.md §4: `git update-index --chmod=-x` sozinho
não gruda — um `git add -A` posterior re-adiciona o modo do filesystem):
`chmod -x` nos 6 artefatos + `git add` de novo.

**Controle positivo, em bytes:**
- antes: `rc=1`, `blocking_unwaived=4`;
- depois: `rc=0`, e `git ls-files --stage` devolve `100644` nos seis.

## Achado 2 — comentário que começa com a palavra reservada do linter — REAL

Ao escrever o G7, uma linha de comentário passou a começar com
`# shellcheck\`` (citando o `name:` do job). O `shellcheck` a lê como DIRETIVA
malformada e derruba o lint do arquivo INTEIRO (`SC1073`/`SC1072`), não só a
linha. Curado reescrevendo o comentário; o próprio comentário registra a
armadilha. Controle: `shellcheck -S warning` vermelho antes, verde depois.

## O que passou nesta rodada

```
bash -n            : 5/5 scripts OK
shellcheck -S warning : 5/5 scripts OK
py_compile         : apply-w4a-validate-deletion.py OK  (py3.9: sem PEP 604, sem match)
bijeção `_expect`  : 38 chaves; 0 lidas-e-não-declaradas; 0 declaradas-e-não-lidas
                     (o censo inclui o MEASURE — deixá-lo de fora faria as
                      chaves que só ele consome parecerem órfãs)
slug de unlock     : `PLAN-186-wave-s343-w4a` casa `^PLAN-[0-9]{3}-[a-z0-9-]+$`
                     (T20g: uma maiúscula derrubaria o G5 inteiro em silêncio)
kernel             : `.github/workflows/validate.yml` ∈ `_KERNEL_PATHS`, medido
                     ao vivo; o par reason/ack satisfaz `_override_granted()`
```
