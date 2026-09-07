---
round: 3
archetype: DevOps Engineer
skill: devops-ci-cd
agent_persona: DevOps & Platform Engineer (Principal)
generated_at: 2026-09-07T00:40:00Z
---

## Verdict

ADJUST — **2 bloqueantes** (P1-1, P1-2).

## Summary (≤ 3 bullets)

- **O censo do §Riscos é VERDADEIRO e ESTÁVEL.** Reproduzi-o em clone limpo
  (`git clone --local` para `<SP>`, `git checkout a6629d0`,
  `python3 .claude/scripts/check-ceremony-script.py --json`): `discovered_total`
  **109**, `discovered_tracked` **109**, sob `.claude/plans/**` **108**, com
  BLOCKING **42**, isentos **42**, R8 **28/28**, `floor` **41**,
  `waivers_active` **44**, `blocking_unwaived` **0** — e os MESMOS dez números
  no HEAD de hoje (`45877e4`). Também conferem: oráculo (`ceremony-lint.yml` 1,
  `smoke-install.yml` 1, `gate-scripts-manifest.txt` 1, os três do toolkit/lint
  0), `_KERNEL_PATHS` = **110** com `validate.yml` em `:144`, 48 `OWNER-*` e 33
  com `sentinel-signers`, modos 41/7, manifesto ADR-192 = 9, sha256 do
  instrumento = `d2234bd…181062`, `PLAN-174:4-5` e `:125-126`,
  `portfolio-review-S348:136-137` e `:174`, `PLAN-SCHEMA:441` e `:462-470`.
  Os 15 must-fix do round 2 que caem na minha superfície estão FECHADOS.
- **O que NÃO fecha é do meu domínio: dois gates que o plano promete e que não
  podem ficar vermelhos pela razão declarada.** O «rc 1 do
  `shellcheck-ceremony`» não existe (o passo é `continue-on-error` e o comando
  termina em `|| true`), e a W0a reescreve o PREDICADO de um checador sem levar
  no patch a suíte que a CI coleta desse checador.
- **Custo:** a OQ-9 escolhe entre três opções e omite a que já está paga — o
  `ownership-nightly.yml` roda o MESMO `shasum -c` por cron, sem `paths:`. O
  quarto sítio compra LATÊNCIA (PR vs. ~24 h), não visibilidade; e o AC-6, ao
  pinar o JSON de waivers, transforma um append de waiver em bloqueio de
  release.

## Risks

- **P1-1 — BLOQUEANTE — o `rc 1` do job `shellcheck-ceremony` é falso no HEAD, e
  o AC-1 lista como «Falha» um evento que a CI não consegue produzir.**
  O plano (§Approach, decisão (a)) afirma: «um `.py` nesse conjunto sai como
  `SC1071` e o passo devolve rc 1 (medido no HEAD)», e conclui que «o relatório
  advisory passaria a nascer com erro permanente». Medido em
  `<ROOT>/.github/workflows/ceremony-lint.yml`: o step tem
  `continue-on-error: true` (`:75`), o corpo abre com `set -uo pipefail` (`:77`
  — sem `-e`) e a chamada termina em `|| true` (`:81-82`); o último comando do
  step é o bloco que escreve o `$GITHUB_STEP_SUMMARY` (`:84-89`). Dois
  mecanismos INDEPENDENTES garantem step verde, e o comentário `:72` declara o
  job ADVISORY por desenho («o gate BLOCKING é o job ceremony-lint»). A DECISÃO
  (filtrar `.sh` antes do `shellcheck`) continua certa — SC1071 é ruído real —,
  mas a justificativa é uma afirmação sobre BYTES que o HEAD desmente, e o
  AC-1 a promove a critério: «Falha = … o job `shellcheck-ceremony` recebendo
  um `.py` no conjunto do `--list`». Esse critério nunca fica vermelho sozinho.
  *Mitigação:* reescrever a razão como «ruído SC1071 num relatório advisory» e,
  se o evento tiver de ser falsificável, nomear o instrumento (asserção sobre o
  conjunto devolvido pelo `--list`, não sobre o rc do step). Nota de precisão:
  há TRÊS consumidores do `--list` no HEAD — `:51` (resumo), `:78` (shellcheck)
  e o gate sem argumento em `:39` —; o plano nomeia um.

- **P1-2 — BLOQUEANTE — a W0a reescreve o predicado de descoberta e o escopo da
  R8 de `check-ceremony-script.py` sem levar no patch a suíte que a CI coleta
  desse arquivo.** `<ROOT>/.claude/scripts/tests/test_check_ceremony_script.py`
  (198 linhas) exercita exatamente as duas superfícies que a W0 muda: o
  harness `make_repo` (`:34-42`) planta o fixture sob
  `<tmp>/.claude/plans/PLAN-999` e roda `--root <tmp> --floor 1`, e
  `test_r8_exec_bit_under_plans_is_blocking` (`:104-109`) afirma a R8 na forma
  ANTIGA. `pytest.ini:38-46` lista `.claude/scripts/tests` em `testpaths`, logo
  essa suíte é bateria de CI. O `file assignment` da W0a (§Items) tem CINCO
  paths e não a inclui. Consequência mecânica: o predicado NOVO (`.sh` **e**
  `.py` por diretório sob o toolkit root) e a R8 alargada nascem **sem um único
  teste na bateria que a CI roda** — os cinco controles vermelhos que os
  provariam são W0b e, pela OQ-9, ainda não têm executor. É a classe «a red gate
  nobody runs» aplicada ao GATE, não ao script guardado.
  *Mitigação:* a suíte entra no file assignment da W0a (5 → 6 paths, ainda
  dentro do teto de 8) com dois casos novos — descoberta de um `.py` sob o
  toolkit root e R8 sobre um arquivo `100755` FORA de `.claude/plans/` —, e o
  plano recontar os paths como já promete fazer.

- **P2-3 — o AC-6 pina o `ceremony-lint-waivers.json` num manifesto verificado
  por quatro workflows que um PR de waiver nunca dispara: o vermelho chega no
  RELEASE.** Verificado: `ADR-192:49-53` fixa quatro superfícies e elas existem
  — `release.yml:58`, `npm-publish.yml:139`, `ownership-nightly.yml:62`,
  `smoke-install.yml:358` (`shasum -a 256 -c "$M"`, fail-closed). Nenhuma delas
  é disparada por um PR que só acrescenta uma entrada ao JSON (o `paths:` do
  `smoke-install.yml` não o cita; `release.yml` roda em tag; `npm-publish` na
  publicação; a nightly em cron). Com o JSON no manifesto, o append de waiver —
  a rota de escape ROTINEIRA, 44 usos hoje — passa a exigir bump assinado do
  manifesto, e quem descobre o esquecimento é o corte de release. O plano
  descreve o controle (ii) do AC-6 como se o vermelho fosse local.
  *Mitigação:* escrever a consequência (append de waiver = cerimônia assinada,
  sob pena de congelar release/publish) e garantir que o QUARTO sítio da OQ-9
  dispare também nos DOIS arquivos do lint — o plano já exige isso (rail r1 #5),
  falta ligar as duas frases; ou pinar só o checador e cobrir o JSON por outro
  controle.

- **P2-4 — a OQ-9 omite a opção JÁ PAGA, e o §Riscos afirma visibilidade zero
  sem ela.** O plano escreve: «Com esse quarto sítio no lugar, **e só com ele**,
  um toolkit alterado fora de cerimônia fica VISÍVEL». Medido:
  `ownership-nightly.yml:19-24` dispara por `schedule: cron "43 6 * * *"` +
  `workflow_dispatch`, sem `paths:` (o próprio cabeçalho do workflow, `:6-10`,
  registra que «`schedule:` events IGNORE `paths:` filters»), e `:62` roda o
  mesmo `shasum -c` do manifesto. Logo, a partir do AC-6, um toolkit alterado
  fora de cerimônia já fica visível em ≤ 24 h sem sítio novo. O quarto sítio
  compra detecção em TEMPO DE PR — o que é legítimo e provavelmente certo —,
  mas a decisão que o Owner recebe deve ser entre LATÊNCIAS e custos, não entre
  visível e invisível.
  *Mitigação:* acrescentar a opção **(iv) aceitar a detecção nightly, sem sítio
  novo** à lista da OQ-9, com a latência declarada, e corrigir o «e só com ele».

- **P2-5 — os controles de EVENTO do AC-1 não têm instrumento nomeado.** O
  «quarto controle» do AC-1 («um PR que toca SÓ um arquivo do toolkit tem de
  DISPARAR o `ceremony-lint.yml` pelo `paths:` novo») e os TRÊS controles
  positivos do quarto sítio (§Riscos) são asserções sobre o motor de eventos do
  GitHub: sem PR real ou sem um casador local dos globs, o que se prova é que o
  NOME está no YAML — o red flag «prova um NOME e não BYTES». Precedente na
  casa para a forma certa:
  `<ROOT>/.claude/hooks/tests/test_workflows_class_guard.py:1-16` testa o
  PREDICADO de classificação, não a fiação do hook.
  *Mitigação:* nomear o instrumento (um casador de `paths:` × conjunto de
  arquivos alterados, stdlib, na bateria) e quem o roda; ou declarar o controle
  como observação ÚNICA feita no PR da própria W0a, com a evidência anexada.

- **P3-6 — duas armadilhas de implementação que o plano pode fixar em uma
  linha cada.** (i) `discover()` monta as raízes a partir do argumento `root`
  (`check-ceremony-script.py:131`), enquanto `DEFAULT_WAIVERS` usa a
  constante `REPO_ROOT` (`:97-99`): um predicado de toolkit escrito contra
  `REPO_ROOT` fica INVISÍVEL para a suíte inteira, que roda com `--root <tmp>`.
  (ii) `--list` imprime TODOS os descobertos (`:283-289`) mas o gate só conta os
  RASTREADOS (`:321-329`, com o teste `test_untracked_blocking_does_not_gate` em
  `:160-172`): o controle positivo de descoberta do AC-1 (arquivo sem token de
  cerimônia) precisa ser um arquivo STAGED, ou prova listagem sem provar
  bloqueio — e a R8 nem sequer dispara sobre untracked, porque lê o modo do
  índice (`:194`).

## O que falta antes de executar (OQ)

1. **OQ-9** (pré-condição declarada) — acrescentar a opção (iv) do P2-4 antes de
   o Owner escolher; a escolha muda a contagem de paths da W0 e a existência da
   W0c.
2. **OQ-7** (pré-condição declarada) — sem objeção da minha superfície: os dois
   braços produzem leitores diferentes e o plano já escreve os dois.
3. **OQ-6** — a janela «detecção post-hoc» está corretamente escrita; o P2-3
   acrescenta o custo operacional que ela implica para release/publish.
4. **OQ-5** — a raiz `.claude/scripts/ceremony/**` no classificador é
   pré-condição do AC-4 nas DUAS opções, como o plano já diz.
5. OQ-1, OQ-2, OQ-4 e OQ-8 não bloqueiam a W0 pela minha leitura.
