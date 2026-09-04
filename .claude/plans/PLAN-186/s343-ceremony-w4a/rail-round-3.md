# wave-s343-w4a — rail codex rodada 3 (patch re-derivado, `--uncommitted`, S343 2026-09-04)

Rail-Verdict: CHANGES-REQUESTED (0 achados NOVOS; reabre o item já curado por gate)

Comando: `codex exec review --uncommitted --skip-git-repo-check
-c sandbox_mode="workspace-write"`, sobre a sombra RE-DERIVADA (11 edições).
Saída bruta: `evidence/rail-r3-raw.txt`.

## O que esta rodada mediu

Rodada **sem** contexto de cerimônia, deliberadamente: a r2 rodou em modo
prompt e curou o que achou; a r3 volta ao `--uncommitted` para ver se a
re-derivação introduziu algo. Resultado:

- **ZERO achados novos.** Nada sobre as 11 edições, nada sobre a re-derivação,
  nada sobre YAML, nada sobre o bloco do timeout.
- **A classe dos comentários órfãos NÃO foi reaberta** — a cura E6..E11
  segurou sob revisão independente.
- Um único item, e é o MESMO da r1: «Require the matrix checks before deleting
  the tests», citando `docs/BRANCH-PROTECTION.md:101-105` e o próprio artefato
  da S340 (`validate-deletion-measure-S340.md#L308-L312`).

## Por que este registro NÃO é APPROVE, e por que a rodada seguinte é

O item é real, já foi aceito na r1 e **já está curado** — mas a cura não cabe
no patch: ela é o **G7** do LAND (config server-side + decisão do Owner), e o
codex, revisando só o diff, não pode vê-la. Registrar APPROVE aqui seria
declarar limpo o que a rodada de fato reportou.

**O fato que decide, e que o codex não tem como observar:** a proteção de
branch do `main` deste repositório responde HOJE
`Branch not protected (HTTP 404)` — não existe status check obrigatório
nenhum, logo o modo de falha «matriz vermelha coexistindo com um required
check verde» **não pode ocorrer hoje**. O G7 mede exatamente isso, classifica
como `unprotected` e deixa o land seguir com a nota verdadeira; se a proteção
for ligada com a configuração documentada, o MESMO gate passa a exigir a
decisão do Owner.

A **r4** repete a revisão com esses quatro fatos dados (sentinel, G7 + o 404
medido, a cura dos comentários, e a igualdade de node-ids), pedindo
explicitamente qualquer coisa ALÉM deles.
