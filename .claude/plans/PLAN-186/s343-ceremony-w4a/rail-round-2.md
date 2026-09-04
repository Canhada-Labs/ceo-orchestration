# wave-s343-w4a — rail codex rodada 2 (patch, prompt-only com contexto, S343 2026-09-04)

Rail-Verdict: CHANGES-REQUESTED (1 P2 real: a CLASSE dos comentários órfãos)

Comando: `codex exec review --skip-git-repo-check -c sandbox_mode="workspace-write"`
com PROMPT (nunca `--uncommitted` junto: as duas formas são XOR). O prompt deu
o contexto que a r1 não tinha — que o sentinel vive na árvore viva por
construção, e que a janela de required-check já virou o gate G7 — para que o
item estrutural não consumisse a rodada
(`feedback-codex-review-prompt-only-context`). Saída bruta:
`evidence/rail-r2-raw.txt` (396 011 bytes).

## O que o codex CONFIRMOU, verbatim

«The deleted test commands are functionally covered by the matrix with
equivalent paths, markers, flags, working directory, and default Claude
adapter behavior, and both YAML files pass structural validation. The smoke
timeout block records measurements rather than predicting speed or duration…»

As três perguntas centrais da wave foram respondidas por um segundo modelo,
sobre a árvore: cobertura equivalente (incluindo markers, flags, working
directory e o comportamento do adapter default), YAML estruturalmente válido,
e o bloco do timeout **sem** previsão de velocidade ou duração.

## [P2] Retarget stale coverage comments after deleting the steps — REAL

«This retargets only one coverage note. The deletion leaves several false
comments: lines 397-400 reference a nonexistent script-test step below, lines
438-441 retain an orphan banner claiming the full hook suite follows, and
lines 479, 531, 1000-1001, and 1111 still refer to directory collection or
two-pass pytest steps "above".»

**Aceito, e os seis sítios foram verificados um a um no arquivo pós-patch.**
Esta é a classe que o E1 abriu e não fechou: o E1 curou UM comentário e o
arquivo tinha SETE. «Rail acha a CLASSE, censo MECÂNICO a fecha.»

**Cura:** as edições **E6..E11** no derivador (5 → 11 edições), cada uma com
âncora exata e contagem declarada. Censo mecânico sobre o arquivo pós-patch:

| literal | HEAD | pós-patch |
|---|---|---|
| `ALREADY collected by "Run Python script unit tests" below` | 1 | 0 |
| `step below runs the whole` | 1 | 0 |
| `is dir-collected above` | 1 | 0 |
| `` `serial` split above `` | 1 | 0 |
| `directory pins in the pytest steps` | 2 | 0 |
| `Step: Python hook unit tests` | 1 | 0 |
| `hook-tests-python-matrix` (contrapositivo) | 2 | **8** |

**Gate:** o **V6c** do LAND roda esse censo nas DUAS pernas — ausência dos
literais velhos E presença do nome do job novo, contada contra
`EXPECTED_MATRIX_JOB_MENTIONS`. Só a perna de ausência passaria com os
comentários APAGADOS em vez de reescritos.

**Controle positivo:** o censo rodado contra HEAD acusa 7 sobras em 6 literais
e `mencoes=2`; contra a sombra, 0 sobras e `mencoes=8`. E o **T26** do harness
planta `EXPECTED_MATRIX_JOB_MENTIONS=42` e exige o vermelho nomeado.

## Achado de bônus, encontrado ao curar (auto-revisão)

A primeira redação da pós-condição declarava `hook-tests-python-matrix` × **7**
— esqueceu a linha que DEFINE o job. Foi a própria pós-condição do derivador
que reprovou (`RECUSA: … aparece 8 vez(es), esperado 7`), o que também expôs
que um refuse pós-escrita deixava a árvore mutada. O derivador ganhou
**rollback transacional**: guarda o conteúdo original e o restaura quando uma
pós-condição reprova.
