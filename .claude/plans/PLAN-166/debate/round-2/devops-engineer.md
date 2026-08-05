---
round: 2
archetype: DevOps & Platform Engineer
skill: devops-ci-cd
agent_persona: null
generated_at: 2026-08-05T00:00:00Z
---

## Verdict

ADJUST — aceito a rejeição do `workflow_call` (a justificativa de blast
radius se confirma contra o código, embora por uma contagem diferente da
que o consensus me atribuiu) e confirmo que meus must-fix 2-5 do round 1
foram fechados no texto novo. Sobra UM must-fix real, pequeno e específico:
o AC-2 tal como escrito testa "nenhum run" como bloqueio imediato, o que
contradiz a própria distinção de três estados que o OQ-1 v2 declara
("not-yet-created" deveria dar retry, não reject).

## Summary (≤ 3 bullets)

- (i) Verifiquei a alegação "29 steps pinados exact por `RELEASE.md:19` ×
  `verify-counts.sh`" contra o código — é FATO, confirmado
  (`verify-counts.sh:171-172,360-361` faz `grep -c '      - name:'
  release.yml` == contagem declarada em `RELEASE.md:19`). Aceito a
  rejeição do `workflow_call`, mas corrijo a contagem de "~6 pins": a
  citação a "R-DEVOPS4/5" no consensus está parcialmente errada — R-DEVOPS5
  era sobre a opção (b) morta (mover publish pra `release.yml`), NUNCA se
  aplicaria ao `workflow_call`; o custo real de pins ficaria do lado de
  `release.yml`/`WaveB5ReleaseYmlTest` (3 testes que checam steps que
  migrariam para o arquivo reusável), não do lado de `npm-publish.yml`.
- (ii) Must-fix 2 (skip por-site no laço) e must-fix 3 (módulo importável
  com `--today` obrigatório) fecham EXATAMENTE como pedi — texto quase
  idêntico em §OQ-2 v2. Must-fix 4 (cobertura pinada nova) fecha adaptado
  a (a′) — corretamente sem necessidade de tocar `WorkflowHygieneTest`
  (não há arquivo novo). Must-fix 5 (`:19`/`:268`) fecha e o plano ainda
  achou MAIS duas ocorrências (`:388`, `:395`) que nem eu tinha visto.
- (iii) A mecânica GHA de §OQ-1 v2 é sólida — `needs:`, `environment`,
  exclusão de RC e timeout 35min verificam corretamente contra o arquivo
  atual — com uma inconsistência real entre a prosa dos "três estados" e
  a lista de controles plantados do AC-2 (ver Must-fix único abaixo).

## Risks

- **R-DEVOPS2-R2 — MEDIUM (residual do round 1, não novo).** A prosa do
  OQ-1 v2 declara os três estados (`not-yet-created` / `running` /
  `concluded`) corretamente — mas o AC-2, ao listar os controles
  plantados, lista **"nenhum run"** simplesmente como um caso que "TÊM de
  bloquear", sem distinguir "ainda não registrado (retry)" de "orçamento
  de tempo esgotado sem nunca aparecer (reject)". Se a implementação seguir
  o AC ao pé da letra, um teste unitário que alimenta a função de decisão
  com uma resposta JSON vazia (`[]`) na PRIMEIRA chamada esperaria REJECT
  — exatamente o comportamento que a prosa dos três estados diz que NÃO
  deve acontecer (retry, não reject, no primeiro poll vazio). Ver Must-fix.
- **R-DEVOPS6 — LOW (novo, implementação).** O texto não diz em qual nível
  (job vs workflow) o `permissions: {contents: read, actions: read}` do
  `await-release-gate` deve ser declarado. `npm-publish.yml` tem
  `permissions:` hoje só no nível de WORKFLOW (`contents: read`,
  `id-token: write`, linhas 50-52). Se a implementação simplesmente
  ACRESCENTAR `actions: read` a esse bloco top-level em vez de dar ao
  `await-release-gate` seu PRÓPRIO bloco `permissions:` no nível do job,
  o job `publish` (que não precisa de `actions: read`) herda a permissão
  desnecessariamente — não é um buraco de segurança (GITHUB_TOKEN
  read-scoped já é baixo risco), mas é menos-privilégio descuidado e some
  na revisão de diff se não for nomeado explicitamente. Mitigação:
  `permissions:` do novo job DEVE ser um bloco job-level próprio, não uma
  expansão do bloco de workflow.
- **R-DEVOPS7 — LOW (novo, UX de operador).** `timeout-minutes: 35` no
  job é o teto duro do GitHub (mata o job com a mensagem genérica "the job
  running on the runner has exceeded the maximum execution time"). O
  script de decisão deveria ter um orçamento de polling PRÓPRIO e menor
  (ex.: 30min) que produza uma mensagem `::error::` acionável ("gate não
  concluiu dentro do orçamento — ver run de release.yml para SHA X") ANTES
  de bater no teto do GitHub — senão o Owner vê só o timeout genérico e
  precisa investigar do zero qual dos dois workflows travou.

## Must-fix (blocking)

1. **AC-2 — separar o controle plantado "nenhum run" em dois casos
   distintos, coerentes com a prosa dos três estados.** (a) "run ainda não
   registrado" (resposta vazia/404 na primeira consulta, ou dentro do
   orçamento de retry) → a função de decisão retorna PENDING/retry, não
   REJECT — e o teste unitário correspondente precisa provar que uma
   SEGUNDA chamada com o run já presente e `conclusion: success` libera
   normalmente (senão o "retry" nunca é exercitado, só declarado em
   prosa). (b) "run nunca apareceu e o orçamento de tempo se esgotou" →
   aí sim REJECT/fail-closed. Sem essa distinção testada, a implementação
   mais óbvia (e a mais fácil de escrever primeiro) é tratar QUALQUER
   resposta vazia como bloqueio imediato — o que reabriria exatamente a
   race que o design já identificou corretamente na prosa (dois workflows
   disparando do mesmo push sem ordem garantida) e faria a rc.2 falhar
   por corrida na maioria das vezes, não por gate vermelho de verdade.
   Custo: uma linha a mais na lista de controles do AC-2 + um teste
   unitário de duas chamadas sequenciais (sem rede, mock de duas
   respostas). Pequeno e mecânico — não deveria adiar W1.

## Nice-to-have (advisory)

1. `permissions: {contents: read, actions: read}` do `await-release-gate`
   como bloco `permissions:` NO NÍVEL DO JOB, não expansão do bloco
   workflow-level (R-DEVOPS6) — nomear isso explicitamente no patch
   staged evita que vire uma escolha implícita de quem implementa.
2. Orçamento de polling interno menor que o `timeout-minutes: 35` do job,
   com mensagem `::error::` acionável antes do teto do GitHub matar o job
   (R-DEVOPS7).
3. Já que `test_all_action_uses_are_sha_pinned` escaneia o texto INTEIRO
   do arquivo (não por job), qualquer `uses: actions/checkout@...` que o
   `await-release-gate` precise adicionar (se a função de decisão morar
   num arquivo do repo em vez de inline) já fica coberto automaticamente
   por esse teste existente — vale citar isso no patch como prova de que
   a superfície nova NÃO é "unwatched" por essa dimensão específica, sem
   precisar adicionar nada.

## Unseen by the original plan

Nenhum achado novo de superfície nesta rodada — o texto v2 já absorveu
tudo que eu tinha de concreto no round 1 (inclusive achou duas ocorrências
de "six sites" que eu não tinha visto, `:388`/`:395`). O único item novo
é a inconsistência AC-2-vs-prosa-dos-três-estados acima, que é uma
lacuna de TESTE, não de superfície.

## What I would NOT change

- **A decisão de rejeitar `workflow_call` para este trem.** Confirmei a
  contagem "29 steps" contra `verify-counts.sh`/`RELEASE.md:19` — é real,
  e ainda que minha citação original (R-DEVOPS4/5) tenha sido usada de
  forma imprecisa na justificativa (R-DEVOPS5 nunca se aplicaria ao
  `workflow_call` — só à opção (b) morta), o custo real do lado de
  `release.yml` (3 testes de `WaveB5ReleaseYmlTest` reapontando para um
  arquivo novo + o count pinado) chega a uma ordem de grandeza parecida
  por um caminho diferente. Trocar a arquitetura de CI do release DURANTE
  um hold que um NO-GO já atrasou, quando (a′) fecha a mesma garantia de
  segurança tocando um arquivo só, é a escolha certa agora. Mantenho o
  registro em §Deferred como está — não promoveria de volta.
- **A ordem `already_published` DEPOIS de `needs: await-release-gate`,
  "não otimizar a ordem de volta".** Correto: mover o check de já-publicado
  para ANTES do gate (pra "economizar tempo") reabriria um caminho onde
  convencer o registry-check a dizer "já publicado" pula o gate inteiro —
  a ordem atual é right-by-construction.
- **O gate de ancestralidade em `tag()` como defesa independente do
  `preflight()`.** Ainda que `preflight()` já verifique `HEAD ==
  origin/main` com igualdade exata (mais forte que "is-ancestor"), o gate
  em `tag()` é uma segunda checagem barata no momento da assinatura —
  correto como defesa em profundidade para o caso em que tempo passou
  entre as fases (o hold de 24h é exatamente esse caso). Não removeria.
- **rc.2 como controle positivo vivo do `await-release-gate` (job roda em
  RC, publish continua bloqueado por RC).** É a resposta certa ao "no
  earlier proof point" que o próprio `oidc-failure-playbook.md` documenta
  como patologia da posture atual — não trocaria por um teste só de
  fixture.
