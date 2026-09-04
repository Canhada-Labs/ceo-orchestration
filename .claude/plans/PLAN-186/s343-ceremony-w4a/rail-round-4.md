# wave-s343-w4a — rail codex rodada 4 (patch, prompt com 4 fatos dados, S343 2026-09-04)

Rail-Verdict: CHANGES-REQUESTED (2 P3 REAIS, os dois em texto que EU escrevi)

Comando: `codex exec review` em modo PROMPT, dando como GIVEN os quatro fatos
que as rodadas anteriores já estabeleceram (sentinel na árvore viva por
construção; a janela de required-check já sob o gate G7, com o 404 MEDIDO; a
cura dos comentários órfãos; a igualdade de node-ids), e pedindo
explicitamente qualquer coisa ALÉM deles. Saída bruta: `evidence/rail-r4-raw.txt`.

## O que o codex confirmou

«No YAML, actionlint, indentation, or CI-runtime defect was found; actionlint
and the workflow assertion suites pass. The two findings are non-blocking
inaccuracies in comments, and the timeout block does not make a future
duration or speedup prediction.»

E, ao contrário da r3, **não** reabriu o required-check: com o 404 medido no
prompt, o item saiu de pauta.

## [P3] Remove the stale PyYAML requirement — REAL, e MEDIDO antes de curar

O banner novo (E7) afirmava que os steps posteriores precisam de
«pytest/PyYAML». Medição própria, sobre a árvore pós-patch:

| pergunta | resposta medida |
|---|---|
| steps depois do install | **25** |
| desses, quantos rodam `pytest` | **3** (teeth da PLAN-155 W6, raízes tests-01, npm packlist) |
| raízes de teste posteriores que importam `yaml` | **0** |
| `import yaml` diretos no job | 2, e os DOIS rodam ANTES do install |

Ou seja: **pytest** é necessário (verificado), **PyYAML** não tem consumidor
posterior conhecido. A cura NÃO é remover o `pip install` — isso seria mudança
funcional fora do escopo, e `tools/migrate-peers-yaml.py` (step posterior) não
foi auditado. O comentário passa a afirmar só o que foi medido e **FLAGA** o
resto: «NOT verified by this wave… Dropping it is a functional change, so it
is FLAGGED here, not guessed at.»

## [P3] Avoid treating cross-commit timings as runner-only variance — REAL

«These samples share the same workflow definition but not the same executed
workload: for example, `826688f` changed `scripts/tests/smoke-install.sh`,
while `ba15c71` changed `scripts/doctor.sh` and
`scripts/tests/test-installer-write-safety-e2e.sh`, all invoked by this job.»

**Aceito integralmente, e é o achado mais importante das quatro rodadas.** Eu
escrevi «um spread de 26 % sobre a MESMA lista de steps» e concluí que «a
variação de runner domina» — uma ATRIBUIÇÃO DE CAUSA que as sete amostras não
sustentam. É a mesma classe que esta wave existe para curar, cometida por mim
no texto da cura.

A cura reescreve a conclusão: as amostras estabelecem a **FAIXA observada**, o
dimensionamento é sobre o **MÁXIMO observado**, e a atribuição ao runner fica
explicitamente NÃO estabelecida («would need repeated runs at ONE sha, which
nobody has done»). O precedente da S327 continua citado — mas rotulado como
precedente, não como evidência sobre estes sete números.

E a mesma frase foi corrigida no sentinel, no `DESIGN`, no `EVIDENCE` e na
mensagem de commit: consertar a tabela e deixar as CONCLUSÕES erradas é a
classe `feedback-reconcile-the-conclusions-not-just-the-table` — a mesma que o
E1/E6..E11 acabou de fechar no YAML.

## Estado

Derivador em 11 edições (E5 e E7 reescritas). Patch re-gerado:
`0d76a1c89ece0853…`. `actionlint` rc=0, 7 jobs / `validate` 48 steps, `smoke`
timeout 150, menções à matriz = 8. A rodada **r5** revisa a superfície
re-derivada — porque «rodada limpa prova a SUPERFÍCIE revisada, não o
entregável», e as duas curas são texto NOVO que ninguém revisou ainda.
