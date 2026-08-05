---
round: 1
archetype: Principal Security Engineer
skill: security-and-auth
agent_persona: Principal Security Engineer (core team.md ICs — VETO em auth/token/input-handling per ADR-052)
generated_at: 2026-08-05T00:00:00Z
---

## Verdict

**ADJUST** — a direção do plano está certa, mas o mecanismo do F1 como
está escrito (`AC-2` + `W1.1`: "conclusão SUCCESS do `release.yml` para o
MESMO SHA da tag") é **contornável por construção**, e eu exerço VETO
escopado sobre esse bind específico (não sobre o plano).

## Summary (≤ 3 bullets)

- O plano fecha 6 achados do re-pass NO-GO antes do GA via rc.2 + novo
  hold. Verifiquei os 6 contra a árvore: **nenhum é falso** — F1
  (`npm-publish.yml:41-45` e `release.yml:3-6` disparam ambos em
  `push: tags: v*`, sem `needs:` nem `workflow_run:` entre eles — grep
  por `workflow_run` em `.github/workflows/` não retorna nada), F2
  (4 stamps com `date.today()` em `release-v1-2-0.sh:347-364`), F3
  (`_framework_target_entries()` em `scripts/_framework_manifest_set.sh:94-124`
  não lista `SPEC/v1` nem `VERSION`; `install.sh:1310,1325` entrega),
  F4 (`test_install_baseline_manifest.sh:117-120`, tautologia admitida no
  comentário), F5 (`README.pt-BR.md:53-54,60` = 55/44/46/~12.000 vs
  57/46/48/~13.000; ausente do `DOCS` em `verify-counts.sh:281-283`),
  F6 (driver:3,37 dizem v1.2.0; :290 diz "SIX version sites" com 11 na
  tabela `SITES`; :515 atribui o publish npm ao `release.yml`).
- **Forte:** agrupar tudo numa cerimônia única, exigir controle positivo
  em gate novo, e reconhecer que o risco do F1 é assimétrico (erra para
  "não publica"). O plano acerta na assimetria e acerta em não mover o
  publish sem verificar o trusted-publisher primeiro.
- **Fraco:** o F1 é especificado por um bind (SHA) que, combinado com a
  decisão do OQ-2, vira um bypass; o F3 é especificado num arquivo que
  não controla entrega; e o F4 pede "derivação independente" sem dizer
  que a fonte tautológica é a mesma função que os dois caminhos já
  compartilham.

## Risks

**R-SEC1 — CRITICAL — o bind por SHA do AC-2 é auto-anulável pelo OQ-2.**
Se o OQ-2 for resolvido como (a) (no-op TOTAL — que é o que eu recomendo,
ver R-SEC5), então `bump --stable` não cria commit e **a tag GA aponta
para o MESMO commit da `v1.3.0-rc.1`** (a convenção de RC já garante que
`VERSION` não muda entre RC e GA — `release.yml:38-53`). Um poll que
aceita "existe run verde do `release.yml` para este `head_sha`" encontra
o run **da rc.1**, que: (i) fez short-circuit do gate de 24h
(`release.yml:238-241` — "RC tags short-circuit"), e (ii) validou um
verdito preso a `release_tag: v1.3.0-rc.1` (`release.yml:696`
`--release-tag "${GITHUB_REF_NAME}"`). Resultado: publica-se o GA com a
prova do RC, e o gate específico do GA nunca rodou.
*Mitigação:* o bind tem de ser **conjunto** — `head_sha == $GITHUB_SHA`
**E** `head_branch == $GITHUB_REF_NAME` (nome da tag) **E**
`event == push` **E** o run ser do `release.yml`. SHA sozinho não
distingue RC de GA; nome da tag sozinho não sobrevive a `git tag -d` +
re-tag noutro SHA. Os dois juntos fecham as duas classes.

**R-SEC2 — HIGH — conclusão de RUN não é prova de que o gate rodou.**
`release.yml:15` tem `if: vars.CEO_SOTA_DISABLE != '1'` no job
`release-gate`; `publish-release` tem `needs: release-gate`. Com a
variável de repositório em `1`, **os dois jobs são pulados e o run não
fica vermelho** — um poll que lê a conclusão do RUN aceita isso como
prova. Ou seja: uma variável de repositório vira interruptor de publish
sem gate. (Sob a opção (b), `needs:` faz o publish ser pulado junto —
fail-closed. Sob a opção (a) mal escrita, é fail-open.)
*Mitigação:* o poll consulta `/repos/{o}/{r}/actions/runs/{id}/jobs` e
exige `conclusion == "success"` **no job chamado `release-gate`**,
rejeitando explicitamente `skipped` e `null`. Nunca a conclusão do run.

**R-SEC3 — HIGH — o commit extra do F2 é invisível ao step 15.**
A defesa de replay do pair-rail recomputa `inputs_hash` só sobre os 20
caminhos de `.claude/governance/pair-rail-inputs-hash-manifest.txt`.
Listei o manifesto inteiro: são hooks, dispatcher, policies, governance
`*.txt`, `run-promotion-gate.py`, `validate-pair-rail-verdict.py` e
`SPEC/v1/audit-log.schema.md`. **Nenhum** dos 4 arquivos que o bump
re-data (`npm/README.md`, `SBOM.md`, `SECURITY.md`, `VERSIONING.md`)
está lá, nem `VERSION`, nem `CHANGELOG.md`. Logo o commit pós-preflight
do F2 passa o step 15 sem ruído: o verdito revisou uma árvore, a tag
assina outra, e o mecanismo desenhado para detectar exatamente isso é
cego para o delta. Isso é mais forte do que o verdito afirma (ele para
em "não validado por CI"; o CI *roda* na árvore da tag depois do push —
o que quebra é o **acoplamento verdito↔árvore**).
*Mitigação:* resolver o F2 (no-op real) fecha a causa. Adicionalmente, o
AC-1 deve provar o invariante em vez do sintoma: **`git rev-parse HEAD`
imediatamente antes e depois de `bump --stable` em D+1 tem de ser
idêntico** — não basta "o teste passa".

**R-SEC4 — MEDIUM — o F3 é um drift de contrato fail-CLOSED, e o dano
real é operacional.** Confirmei a direção do drift: o SPEC v1.2
instalado diz que `CEO_SENTINEL_UNLOCK` + `..._ACK` "short-circuit a
verificação GPG", ponto final; as +21 linhas desta release
(`git diff --stat v1.2.0..HEAD -- SPEC/`) **acrescentam** a exigência de
prova de proveniência (ADR-119 Invariant 5 / PLAN-162 W2: Form A
`CEO_SESSION_ANCHOR_SHA` ou Form B `CEO_SENTINEL_UNLOCK_SHA256`, com
"neither value present → no grant"). O hook v1.3 é **mais restritivo**
que o contrato v1.2 — não há escalação de privilégio; há um adopter
bloqueado no meio de uma cerimônia com uma documentação que diz que ele
não deveria estar. A janela de ataque não é a máquina: é o operador que
conclui "o hook está quebrado" e desarma o guard inteiro. Verifiquei
também que nada lê `SPEC/v1` em runtime (as ocorrências em
`.claude/hooks/**` são comentários/docstrings), então não existe
superfície onde o contrato stale **valide** algo que o hook rejeita —
respondendo diretamente à pergunta da minha lente: não, o fix não deixa
essa superfície, porque ela nunca existiu; o SPEC é contrato humano.
*Mitigação:* manter o F3 como P0 pelo motivo certo (recuperabilidade e
honestidade do contrato publicado), não por privilege escalation — e o
`INSTALL.md` do F6 passa a ser parte do mesmo fix, não um P2 separado.

**R-SEC5 — MEDIUM — o OQ-2 (b) introduz um filtro que decide o que conta
como mudança.** Comparar "o diff ignorando os stamps" exige um filtro que
roda **imediatamente antes de uma tag assinada**. Se ele over-matcha, ele
engole silenciosamente um diff real na janela mais cara do processo. A
opção (a) é estritamente mais estreita: "árvore já em `TARGET_BASE` →
não reescreve stamp de data".
*Mitigação:* escolher (a). Ver a justificativa completa no OQ-2 abaixo.

**R-SEC6 — MEDIUM — o gate novo do F1 herda o problema "sem ponto de
prova antes do GA".** `npm-publish.yml:65` exclui tags `-rc.` do workflow
INTEIRO. Um gate adicionado dentro desse workflow **não roda na rc.2** —
o primeiro exercício ao vivo é o GA, exatamente a patologia que o
`oidc-failure-playbook.md:2-11` documenta para o próprio OIDC ("no
earlier proof point ... by design").
*Mitigação:* ver Must-fix 3 — separar em dois jobs e deixar o job de
espera rodar também em RC (sem `environment`, sem publish).

**R-SEC7 — LOW/MEDIUM — orçamento de tempo e permissão.** O job de
publish tem `timeout-minutes: 8` (`npm-publish.yml:68`) enquanto o
`release-gate` tem `timeout-minutes: 20` mais fila. Um poll dentro do
mesmo job estoura o teto e falha — fail-closed, mas queima um ciclo de
release e uma aprovação manual do `production-npm`. E `permissions:`
(`:50-52`) hoje é `contents: read` + `id-token: write`; o poll precisa de
`actions: read`, que deve ser adicionado **no job de espera apenas**.

## Must-fix (blocking)

1. **[VETO escopado] Reescrever o AC-2 e o W1.1 para especificar o bind
   completo.** Como está — "conclusão SUCCESS do `release.yml` para o
   MESMO SHA da tag" — o critério é satisfazível por uma implementação
   contornável (R-SEC1 + R-SEC2). O AC-2 tem de exigir, textualmente:
   run do workflow `release.yml`, `event == push`,
   `head_branch == <nome da tag GA>`, `head_sha == <SHA da tag>`, e
   **job `release-gate` com `conclusion == "success"`** (nunca a
   conclusão do run; `skipped`/`null` = bloqueio). Levanto o VETO quando
   o AC-2 disser isso. Justificativa de autoridade: ADR-052 me dá VETO em
   mudanças de trust/auth, e o acoplamento publish↔gate é o controle de
   supply-chain que decide o que vai para o registry público.
2. **Resolver o OQ-1 como (a′), não (a) nem (b): dois jobs no MESMO
   arquivo.** A evidência in-repo sobre o que o npmjs.com amarra é
   explícita e eu a verifiquei:
   `.claude/plans/PLAN-158/oidc-failure-playbook.md:18` —
   `Canhada-Labs/ceo-orchestration` + **`npm-publish.yml` (o NOME DO
   ARQUIVO, não o display name)** + `environment: production-npm`;
   corroborada em `npm-publish.yml:279-284` e em
   `PLAN-158/debate/round-1/staff-security-engineer.md:205-206`.
   Portanto a opção (b) troca um campo do registro que **não é
   verificável a partir do repositório, não é coberto por nenhum gate de
   CI, e cuja falha só aparece no GA** (E403/E404 —
   `oidc-failure-playbook.md:20`). Estrutura correta:
   - job `await-release-gate` — sem `environment`, `permissions:
     contents: read` + `actions: read`, timeout próprio (≥ 30 min);
   - job `publish` — `needs: await-release-gate`, mantém
     `environment: production-npm`, `id-token: write`, e mantém
     **verbatim** o `if: "!contains(github.ref, '-rc.')"`.
   O binding OIDC é (repo, arquivo do workflow, environment); nenhum dos
   três muda, e o acoplamento vira uma aresta `needs:` (fail-closed por
   construção) em vez de uma asserção que pode ser mal escrita. Residual
   honesto: eu não consigo ler o console do npmjs.com daqui — a
   afirmação acima é o registro do repositório, e o Owner deve confirmar
   os três campos antes de landar.
3. **O job de espera tem de rodar em tags RC.** Mover a exclusão de RC
   para o job `publish` (mantendo o texto idêntico) e deixar
   `await-release-gate` sem `if:`, para que a rc.2 exercite o gate ao
   vivo contra um run real do `release.yml` sem publicar nada. Isso é o
   único jeito de o AC-2 ter um controle positivo *vivo* antes do GA
   (R-SEC6).
4. **Fortalecer, não relocar, os pins de posture de RC.**
   `test_release_workflow_asserts.py` tem
   `test_rc_exclusion_present`, `test_rc_exclusion_precedes_publish_command`
   e `test_rc_exclusion_survives_wave_b` — eles existem para impedir
   exatamente a edição do item 3. Se a exclusão mudar de lugar sem que os
   testes mudem de forma **deliberada e mais forte** (asserção: "o job
   que executa `npm publish` carrega a exclusão de RC"), o PLAN-013
   anti-goal #3 fica desprotegido enquanto os testes continuam verdes.
   Um teste que passa depois de relaxado não é evidência.
5. **O controle positivo do AC-2 é unitário + vivo, e o unitário é
   obrigatório.** A função de decisão do poll deve ser um script Python
   stdlib que recebe o JSON de runs/jobs por stdin/arquivo, para ser
   testável sem rede. Casos plantados que **têm de** bloquear: (i) job
   `release-gate` `skipped`; (ii) run com `head_sha` certo mas
   `head_branch` da rc; (iii) `head_branch` certo mas `head_sha` de outro
   commit (cenário tag deletada + re-tag); (iv) `conclusion: failure`;
   (v) nenhum run; (vi) JSON malformado. O (vi) é **fail-CLOSED por
   contrato de matcher de segurança** (precedente `check_bash_safety.py`,
   PLAN-152 debate C4) — o que não se consegue parsear não vira permissão.
6. **O fix do F3 toca TRÊS listas, não uma.** O plano diz "`SPEC/v1` +
   `VERSION` viram superfícies de upgrade em `_framework_manifest_set.sh`".
   Verifiquei: `upgrade.sh` **sourcea** esse arquivo (`:105-108`) mas não
   chama nenhuma das funções de enumeração — grep por
   `_framework_target_entries|_framework_manifest_files|_fms_` em
   `upgrade.sh` volta vazio. A entrega é a sequência escrita à mão de
   `backup_and_replace` (`:2325-2350`); a enumeração só alimenta
   `_write_baseline_manifest` (`upgrade.sh:2474`, bookkeeping). Editar só
   o `_framework_manifest_set.sh` **não faz o upgrade entregar nada** —
   muda a contabilidade e deixa o bug. O fix precisa de: (a)
   `backup_and_replace "SPEC/v1"` + `"VERSION"` em `upgrade.sh`, (b) as
   duas entradas em `_framework_target_entries()`, (c) a lista de refresh
   do `INSTALL.md` (que é a parte canonical do F6 — mesma cerimônia).
7. **O F3 tem de respeitar a cerimônia (resposta ao OQ-3).**
   `install.sh:1310` e `:1325` entregam `SPEC/v1` e `VERSION` **apenas
   quando `CEREMONY != "user"`**; `upgrade.sh` não tem uma única
   referência a `CEREMONY`. Uma entrega incondicional no upgrade
   **promove** um install `--ceremony user` a maintainer, criando na
   árvore do adopter arquivos que o install dele deliberadamente omitiu —
   expansão de superfície silenciosa, no caminho de menos escrutínio. O
   `.install-state.json` já grava a cerimônia (`install.sh:2286`), e o
   upgrade já lê esse arquivo para replay de `--profile/--stack`
   (`:640-712`). O patch tem de ler a cerimônia gravada e pular as duas
   superfícies em installs `user` — com o mesmo fallback fail-open que o
   replay já usa quando o estado está ausente/ilegível (pré-Wave-B).

## Nice-to-have (advisory)

1. Registrar os três campos do trusted publisher num arquivo versionado
   (ex.: `.claude/governance/npm-trusted-publisher.txt`) e assertar no
   `test_release_workflow_asserts.py` que o nome do arquivo de workflow e
   o nome do environment batem com o que o `npm-publish.yml` realmente
   usa. Não prova o console, mas transforma "erro invisível até o GA" em
   "erro visível no CI" para metade das causas de E403.
2. Adicionar `.claude/governance/pair-rail-inputs-hash-manifest.txt` a
   um teste que falha se um arquivo tocado pelo `bump` entrar na lista
   sem revisão — a interação R-SEC3 é sutil e vai ser reintroduzida.
3. `CEO_SOTA_DISABLE` e `CEO_PAIR_RAIL_VERDICT_OPTIONAL` são dois
   interruptores de gate que vivem em variáveis de repositório, fora do
   log de auditoria e fora do git. Um ADR curto declarando-os
   "break-glass, exigem registro" custa pouco e fecha uma classe.
4. F5: ao adicionar `README.pt-BR.md` ao `DOCS`, checar também que os
   rótulos em português não colidem com os matchers em inglês já
   existentes (o `verify-counts.sh` varre `DOCS` inteiro para algumas
   famílias — ex. `:370`, "README/INSTALL lack the literal, so scanning
   all DOCS is safe" deixa de ser verdade quando o pt-BR entra).

## Unseen by the original plan

1. **Em árvore de adopter, `SPEC/v1` e `VERSION` estão fora da
   contabilidade de integridade — não só do upgrade.** Como
   `_framework_target_entries()` não os lista, `_write_baseline_manifest`
   não grava hash deles em `.claude/.install-manifest.sha256`, e o
   `doctor.sh` (varredura de órfãos, `:598-642`) enumera a partir da
   mesma função. Consequência: **adulterar o `SPEC/v1` de um adopter é
   invisível para a própria ferramenta de detecção de drift do
   framework** — e `SPEC/v1/*.md` é canonical-guarded no repo
   (`check_canonical_edit.py:180-181`), ou seja, o framework protege esse
   contrato em casa e não o inventaria na casa do adopter. Isso é um
   achado à parte do F3, e o fix (Must-fix 6b) o fecha de graça — mas só
   se o item (b) entrar, o que reforça por que (a) sozinho não basta.
2. **O F4 é o controle que teria pego o F3 — e é o controle que protege
   todo guard FUTURO.** A entrega do upgrade é uma sequência escrita à
   mão; se um dia um hook sair dessa lista, adopters que atualizam ficam
   com o hook ANTIGO e nenhum teste acusa. Isso é rebaixamento silencioso
   de guard via caminho de atualização — classe de supply-chain, não de
   qualidade. O plano trata o F4 como P1 "teste tautológico"; na minha
   lente ele é o controle de integridade do canal de distribuição e
   merece a mesma cerimônia que o F1.
3. **A "derivação independente" do OQ-4 pode renascer tautológica.** Se o
   fix for "derivar os dois conjuntos da mesma função de enumeração por
   dois caminhos", volta-se ao mesmo lugar — a enumeração é uma
   TERCEIRA lista que nenhum dos dois caminhos de entrega consome. O
   único teste que fecha isso compara **árvores resultantes**: instalar
   em fixture A, instalar-versão-antiga + upgrade em fixture B, e
   comparar o conjunto de arquivos framework-owned. Controle positivo:
   remover uma linha `backup_and_replace` do `upgrade.sh` numa cópia e
   exigir FALHA. E o teste tem de rodar **por modo de cerimônia**
   (maintainer e user), senão a divergência by-design do
   `--ceremony user` vira ruído que alguém vai silenciar com uma
   allowlist — e allowlist é onde gates morrem.
4. **A promoção RC→GA sobre o mesmo commit é uma propriedade nova do
   processo, e ninguém a declarou.** Se o OQ-2 for (a), `v1.3.0-rc.1` e
   `v1.3.0` apontam para o mesmo SHA. Isso é bom (a árvore revisada é a
   árvore publicada) mas muda a semântica de qualquer coisa que
   identifique release por SHA — o gate do F1 (R-SEC1), a leitura do
   `parent_sha` do verdito, e a interpretação forense do audit log. Vale
   uma linha explícita no `release-checklist.md`: "no caminho feliz, a
   tag GA e a última RC apontam para o mesmo commit; qualquer divergência
   é um sinal de que algo foi tocado durante o hold".
5. **O `already_published` guard é o último recurso de idempotência e ele
   é anterior ao gate proposto.** Hoje ele roda como step
   (`npm-publish.yml:257-274`) dentro do job com `environment`. Se o gate
   novo virar um job anterior, a ordem passa a ser: espera → aprovação →
   checagem de registry → publish. Isso é o correto (não gastar aprovação
   antes de saber que o gate passou), mas confirma que a aprovação manual
   **não** é o primeiro obstáculo depois da mudança — vale dizer isso no
   plano para ninguém "otimizar" a ordem de volta.

## What I would NOT change

- **A assimetria de risco declarada no plano** ("errar aqui falha para
  não-publica, não para publica-sem-gate"). Está certa e é o argumento
  que sustenta preferir a opção conservadora no F1. Não trocar por
  urgência de release.
- **Manter `environment: production-npm` e a exclusão de tags RC.** São
  dois controles independentes (aprovação humana e posture de RC), com
  história ratificada (PLAN-013 anti-goals #3/#16; PLAN-153 Wave B item
  5f fechou a ideia de dist-tag `next`). O gate novo é **aditivo** — não
  substitui nenhum dos dois.
- **Não mover o publish para o `release.yml`** enquanto o registro do
  trusted publisher não for reconfigurado e confirmado pelo Owner. O
  ganho de elegância não paga o risco de um campo invisível ao CI.
- **Agrupar todos os patches canônicos numa cerimônia única.** Cada
  cerimônia extra é uma janela de assinatura a mais; agrupar é a decisão
  de segurança certa, não só de custo.
- **A disciplina de rodar o re-pass até APPROVE, nunca até "achei o
  suficiente"**, e o contrato "gate novo nasce com controle positivo".
  Os dois são precisamente o que impediu este NO-GO de virar um GA.
- **Tratar o F2 como P1 e não P0.** O dano do F2 é acoplamento
  verdito↔árvore (R-SEC3), sério mas contido pelo fato de o CI rodar na
  árvore da tag após o push. A severidade do plano está calibrada.
