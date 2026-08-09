---
id: PLAN-166
title: Release-hold findings closure — v1.3.0 GA via rc.2
status: executing
created: 2026-08-05
reviewed_at: 2026-08-05
owner: CEO
depends_on: [PLAN-162, PLAN-165]
budget_tokens: 90-140k
budget_sessions: 3-4
context_risk: medium
external_wait: ADR-103 hold reinicia no corte da rc.2 (24h)
tags: [release, ci, upgrade, governance, canonical]
---

# PLAN-166 — Release-hold findings closure (v1.3.0 GA via rc.2)

> **v2.1 (2026-08-05).** v1 passou pelo round 1 (3× ADJUST, 1 VETO
> escopado): fix de F3 destrutivo, AC-2 contornável, classificação
> canonical errada. v2 aplicou o consensus r1; o round 2 verificou o
> TEXTO e devolveu 3× ADJUST com correções textuais (VETO r1 LEVANTADO
> por verificação literal; VETO novo escopado ao marcador, fechado pela
> Forma A nesta v2.1). Consensus: `debate/round-1/consensus.md` +
> `debate/round-2/consensus.md`.
>
> **Ratificação (2026-08-05, AskUserQuestion):** Owner selecionou
> "Ratificar reviewed (Recomendado)" — "Frontmatter vira status: reviewed
> com reviewed_at hoje. […] A cerimônia W1 continua exigindo sua
> assinatura GPG — reviewed não libera execução canônica." `reviewed`
> ratifica o PLANO; execução de W1 fica atrás da cerimônia e ship atrás
> da cascata V0-V3.

## Context

O re-pass ADR-103 do codex contra `v1.3.0-rc.1` (S294, 05/08) voltou
**NO-GO** com 6 findings — todos verificados manualmente contra o código
antes de aceitos, e re-verificados independentemente pelos 3 críticos do
debate (nenhum refutado). O Owner decidiu em chat: **corrigir todos os 6
antes do GA**, o que implica rc.2 + novo hold de 24h, já que F1/F3/F4
mudam superfícies congeladas na rc.1.

Evidência: `PLAN-166/repass-r1/` (MANIFEST.sha256 verificado).
- inputs_hash: `c89acd4af3686145c8a085283b1976836f46f252185283efee8ae0be8adc95c9`
- paths_manifest_sha: `5b89f472ed1f6d75e25d5e3d0042c56bd973b5f46b7b123b993d619a398c618e`
- codex: 0.144.6 / gpt-5.6-sol / read-only / pin ADR-182 `80a3933d…` verificado

## Findings (verificação própria + debate)

| # | Sev | Superfície | Guardada? | Novo na 1.3? |
|---|---|---|---|---|
| F1 | P0 | `npm-publish.yml` não observa `release-gate` (ambos em `push: tags: v*`; única barreira = environment `production-npm`) + claim falsa de publish no driver em DUAS ocorrências (`:19` e `:515`) | workflow ✅ canonical; driver livre | Não (v1.2.0 shipou assim) |
| F2 | P1 | `bump --stable` NÃO-idempotente em D+1: 4 stamps `last-reviewed:` re-datam com `date.today()` mesmo sem mudança de versão → índice sujo → commit pós-preflight que `tag()` assina sem CI. O commit extra é INVISÍVEL ao step 15 (nenhum dos 4 arquivos está no `pair-rail-inputs-hash-manifest.txt`) | livre | **Sim** — o hold GARANTE o cenário |
| F3 | P0 | Upgrade v1.2→v1.3 não entrega `SPEC/v1` (o contrato mudou +21 linhas NESTA release — trust boundary do unlock). A entrega real do upgrade é a sequência manual de `backup_and_replace`, NÃO a enumeração FMS; e `SPEC/v1` está fora do inventário de integridade do adopter inteiro (baseline manifest + doctor.sh cegos) | ✅ canonical (upgrade.sh, install.sh, manifest-set) | Estrutura pré-existente, dano novo |
| F4 | P1 | Gate de paridade install/upgrade morto DUAS vezes: tautológico (compara `_framework_target_entries()` consigo mesma — admitido em comentário) E não executado por workflow nenhum (5ª instância da classe "gate vermelho invisível") | **livre** (`scripts/tests/**` não é guardado) | Não |
| F5 | P1 | Contagens stale em 3 docs JÁ VIGIADOS (`npm/README.md:60,123`, `docs/FAQ.md:109` = ~12.000 vs ~13.000) + 6 ocorrências em 5 linhas do `README.pt-BR.md` (fora de DOCS). A forma `~N.000` não casa regra nenhuma e a regra `tests` é FLOOR — estar em DOCS não basta | livre | Sim |
| F6 | P2 | O NOME do driver (`release-v1-2-0.sh` conduzindo 1.3.0) é a raiz da classe; strings v1.2.0 no help (`:3,:37`), "six sites" em QUATRO ocorrências (`:268,:290,:388,:395` — 11 sites reais), claim falsa de publish em `:19`+`:515`, `INSTALL.md:627` migração obsoleta | **livre** (INSTALL.md não é guardado; driver livre) | Sim |

## Decisões (OQs resolvidas pelo consensus round 1)

### OQ-1 — F1 = (a′): await-job com bind conjuntivo, dentro do `npm-publish.yml`

- Job novo `await-release-gate`: SEM `environment`, SEM exclusão de RC
  (roda na rc.2 = controle positivo vivo), `permissions: {contents: read,
  actions: read}`, `timeout-minutes: 35`, e **`GH_TOKEN:
  ${{ github.token }}` no env do job** — `permissions:` sozinho NÃO
  autentica o `gh` CLI em runner hosted; sem o token, todo run (RC e GA)
  morre em erro de auth → BLOCK (fail-closed quebrando a release
  inteira). Pinado por assert estrutural junto com o `needs:`.
- Função de decisão = script Python stdlib (testável sem rede, recebe o
  JSON por stdin/arquivo) com **semântica de PONTO explícita** — retorna
  um de três resultados por avaliação: **GRANT** somente com TODAS as
  condições (run do workflow `release.yml`, `event == push`,
  `head_branch == <nome da tag>`, `head_sha == GITHUB_SHA`, e **job
  `release-gate` com `conclusion == "success"`** — nunca a conclusão do
  run: `CEO_SOTA_DISABLE=1` pula jobs sem avermelhar); **WAIT** para
  `not-yet-created` (workflows disparam do mesmo push sem ordem;
  ausência ≠ falha ≠ permissão), para **run presente mas job
  `release-gate` ainda não materializado no endpoint de jobs** (r9:
  consistência eventual da API — sem esse estado, "BLOCK em mismatch"
  produz falso bloqueio imediato na corrida rc.2/GA) e para
  `running`/`conclusion: null` dentro do prazo. **Semântica de candidato
  (r14): a lista de runs do head-SHA contém runs NÃO-relacionados —
  inclusive o run do PRÓPRIO `npm-publish` — que são IGNORADOS, nunca
  BLOCK; "mismatch" se refere ao CANDIDATO exato
  (workflow+tag+SHA+event), e só um candidato exato failed/skipped
  bloqueia** — senão toda release perde a corrida contra a própria
  presença na lista. **BLOCK** em mismatch do candidato,
  `skipped`/`failure`, JSON malformado, erro de API e **deadline
  estourado em qualquer estado não-GRANT** (fail-CLOSED — verificação de
  INPUT, ADR-186).
- Job `publish`: ganha `needs: await-release-gate`; mantém VERBATIM
  `environment: production-npm` e `if: "!contains(github.ref, '-rc.')"`.
  Ordem deliberada: a aprovação manual do Owner só aparece DEPOIS do gate
  verde. O guard `already_published` continua no job publish (idempotência
  de último recurso) — não "otimizar" a ordem de volta.
- Rejeitados com evidência (documentar no cabeçalho do workflow):
  `workflow_run` executa o arquivo do branch default (mata a invariante de
  rollback do cabeçalho `:14-18`); mover para `release.yml` quebra o
  binding OIDC por FILENAME (`oidc-failure-playbook.md:18`) e ~6 pins de
  teste; `workflow_call` reusável é refactor candidato PÓS-GA (§Deferred).
- Claim falsa do driver corrigida nas DUAS ocorrências (`:19`, `:515`):
  quem publica é `npm-publish.yml`.

### OQ-2 — F2 = (a): no-op total por "mesma árvore", nunca por diff-mask

- Predicado externo de QUATRO oráculos: `VERSION == TARGET_BASE` E
  `verify-counts` limpo E `build-plugin.py --check` limpo E
  `check-canonical-doc-freshness.py` limpo → `bump` NÃO ESCREVE ARQUIVO
  NENHUM, imprime no-op, retorna 0. O 4º oráculo é obrigatório: é o
  ÚNICO vigia dos stamps de SBOM/SECURITY/VERSIONING (fora de
  `VERSION_SITES`), e sem ele o no-op externo impediria a auto-cura
  in-loop de rodar sobre uma stamp stale. (Seguro congelar a DATA: o
  freshness gate decide pela VERSÃO da stamp, não pela data.)
- Defesa em profundidade no laço: os 4 sites `last-reviewed:` pulam a
  linha inteira quando a versão na stamp já é o alvo (não tocam nem data
  nem versão). Atenção de implementação: os 4 stamps têm DOIS oráculos
  distintos (`npm/README.md` via `VERSION_SITES` do verify-counts;
  SBOM/SECURITY/VERSIONING via freshness gate) — o skip por-site preserva
  os dois.
- O corpo do heredoc vira módulo importável
  (`.claude/scripts/local/_release_bump_sites.py`) com `--today`
  PARÂMETRO OBRIGATÓRIO sem default (memória frozen-evidence) — chamado
  pelo driver com `--today "$(date -I)"` e pelo teste com D e D+1
  explícitos.
- Escotilha `--restamp` para re-revisão real — EXIGE
  `--npm-readme-reviewed` (senão vira o bypass do tripwire que este OQ
  defende) e **EXCLUI o fast-path de no-op** (r14: no cenário normal de
  re-revisão — mesma versão, 4 oráculos limpos — o predicado externo
  retornaria ANTES das substituições e o `--restamp` seria letra morta;
  teste de regressão mesma-versão prova que os stamps MUDAM sob
  `--restamp`).
- Racional: re-datar sem re-revisar é claim falsa em superfície assinada;
  a unidade de `last-reviewed` é a RELEASE (definição do driver `:36-40`).
  (b) escreve-para-restaurar = estado rasgado se cair no meio.
- Fecha a CLASSE, não só o caso: `tag()` ganha gate de ancestralidade.
  Implementação com DOIS erros distintos: falha do fetch → "não consegui
  falar com origin" (escotilha nomeada para offline); merge-base falso →
  "HEAD não é ancestral de origin/main — pushe main e re-rode o
  preflight". NUNCA `;` entre fetch e merge-base (fetch falho + ref stale
  = aprovação falsa). Hoje NADA verifica que a tag aponta para commit de
  main.

### OQ-3 — F3 = SPEC/v1 sim; VERSION da raiz NÃO; marcador novo

- `SPEC/v1` vira superfície de upgrade nas TRÊS listas: (a) entrega no
  `upgrade.sh` por **rota de refresh FORÇADO** — NÃO o
  `backup_and_replace` genérico: para alvo-diretório com baseline, o
  walk classificado (`upgrade.sh:1253-1290`) PRESERVA/recusa
  customizações do adopter, ou seja, a partir do 2º upgrade um SPEC
  editado seria classificado ADOPTER-CUSTOMIZED e o contrato stale
  voltaria; a semântica declarada ("fork → backup em `.claude.bak/` +
  replace") exige o caminho forçado, com teste partindo de baseline que
  JÁ contém `SPEC/v1` (cenário 2º-upgrade); (b) entrada em
  `_framework_target_entries()` **CONDICIONADA à ceremony efetiva** (r7:
  entrada incondicional faria `write_install_manifest()` num install
  `--ceremony user` — onde SPEC foi PULADO — hashear o `SPEC/v1` próprio
  do adopter como framework-owned, e um `uninstall.sh` posterior poderia
  DELETAR arquivos do adopter cujo hash bate com o manifest; a
  enumeração só inclui o que o framework de fato entregou. **"Entregou"
  = ENTREGA REAL, não só ceremony** (r17): num install maintainer onde o
  destino JÁ tem `SPEC/v1` próprio, `install_one` PULA — condição só de
  ceremony ainda inventariaria o SPEC do adopter como framework-owned e
  o uninstall poderia deletá-lo; a propriedade é condicionada ao ato de
  entrega registrado, com fixture de SPEC pré-existente — fecha também
  a cegueira do baseline manifest e do doctor.sh na árvore do adopter),
  (c) lista de refresh do `INSTALL.md`.
- Gated pela ceremony gravada: `install.sh` só entrega `SPEC/v1`/`VERSION`
  quando `CEREMONY != user` (`:1310/:1325`); o upgrade lê a ceremony de
  `.install-state.json` — **por leitura PRÓPRIA, independente do replay**
  (r9: `--no-replay` seta `REPLAY=0` e pula `_read_install_state_request`
  inteiro, `upgrade.sh:292-295,681-725` — se a ceremony vier só do
  replay, o comando documentado `upgrade.sh --no-replay` trataria um
  install user como maintainer e forçaria SPEC/protocol na raiz do
  adopter; teste user-mode COM `--no-replay` obrigatório) — e PULA as
  superfícies em installs `user`; fail-open se o estado está
  ausente/ilegível (pré-Wave-B). **A entrada `PROTOCOL.md` do FMS ganha
  o MESMO ceremony-gate** (r13: install user pula
  `install_protocol_pointer` (`install.sh:1876`) mas
  `_framework_target_entries()` emite `PROTOCOL.md` incondicionalmente
  (`manifest-set:97`) — o PROTOCOL.md PRÓPRIO do adopter ficaria
  registrado como framework-owned e `uninstall.sh` poderia deletá-lo;
  teste com root file pré-existente obrigatório). **`doctor.sh` entra na
  mesma resolução de ceremony** (r9 P2: `doctor.sh:616-619` chama
  `_framework_manifest_files` sem contexto — com a entrada FMS
  condicional, default maintainer faria o SPEC próprio de um adopter
  user parecer framework-owned/órfão e `--strict-orphans` falharia;
  default user esconderia o SPEC de um maintainer; cobrir os dois modos). Consequências
  nomeadas no INSTALL.md: (i) installs SEM `.install-state.json` são
  tratados como maintainer no upgrade; (ii) a seção de âncora forense
  (`INSTALL.md:593-599` — "cat TARGET/VERSION ... matches the git tag")
  fica FALSA pós-upgrade (o `VERSION` da raiz fica intencionalmente para
  trás) e é reescrita para preferir `.claude/.framework-version` com
  fallback.
- `VERSION` da raiz: **o upgrade NÃO toca.** `install_one` é
  skip-if-exists — num adopter com `VERSION` próprio o framework nunca
  escreveu ali; `backup_and_replace` TOMARIA o arquivo (classe
  S238/ADR-155, "the verified worst case"), e o classificador de baseline
  confirmaria o clobber (armadilha C.5 documentada no próprio
  manifest-set).
- Marcador do framework: `.claude/.framework-version` é um **arquivo
  RASTREADO do repo do framework** (r6 supersede a forma "gerado só no
  destino": um marcador gerado-apenas-no-destino tornava as duas
  proteções da Forma A inalcançáveis no checkout de release — o
  verify-counts pula site ausente e o assert condicionado a existência
  nunca roda; e criava a gambiarra generated-file no FMS). Como arquivo
  rastreado, as proteções da Forma A viram REAIS e incondicionais
  (fecha o VETO r2, fortalecido): (i) o `bump` o escreve como 12º site e
  ele entra em `VERSION_SITES` do `verify-counts.sh` (site sempre
  presente — o gate cruza com `VERSION` em toda release); (ii)
  `release.yml` ganha assert `marcador == VERSION` INCONDICIONAL
  (fail-closed, ao lado dos asserts VERSION↔tag `:55-70`); (iii) entra
  em `_framework_target_entries()` como entrada NORMAL — presente na
  árvore FONTE, a reescrita de baseline (`FMS_HASH_ROOT`,
  `manifest-set:245-249`) o preserva naturalmente, sem special-case;
  inventariado, visível ao doctor. Entrega por **escritas EXPLÍCITAS nos
  dois caminhos** (r7 — a enumeração NÃO entrega, só alimenta os manifest
  writers; a mesma lição das três listas do F3 aplicada ao marcador):
  `install_one ".claude/.framework-version"` no install e o refresh
  explícito no upgrade, ALÉM da entrada FMS (dentro de `.claude/` —
  `--ceremony user` OK pelo guard WS4; some a necessidade do gitignore
  aninhado do r5 — arquivo entregue é commitável como o resto de
  `.claude/`). **REGRA GERAL unificada (r17/r19): TODA entrada
  condicional do FMS — SPEC/v1, PROTOCOL.md E o marcador — deriva do
  REGISTRO DE ENTREGA, nunca de ceremony ou de presença de arquivo:**
  destino que JÁ tinha o path (skip do `install_one`) → fora da
  propriedade framework-owned (senão o baseline hasheia arquivo do
  adopter, o update-checker confia num valor stale e o uninstall pode
  deletá-lo); para o marcador em particular, ou a escrita é
  FORÇADA+validada, ou a entrada FMS só entra após entrega registrada —
  **e todo leitor marker-first consulta o MESMO registro** (r20: num
  destino onde o marcador pré-existia e foi pulado, o update-checker
  lendo-o incondicionalmente reportaria versão obsoleta em loop).
  **Migração para installs v1.2 LEGADOS** (r20 — não existe registro de
  entrega histórico que distinga SPEC instalado pelo framework de SPEC
  do adopter): a ambiguidade se resolve por CONTEÚDO — comparar o
  `SPEC/v1` pré-existente contra os hashes PRISTINE dos SPECs shipados
  (v1.2.0 e anteriores, determinístico): bate com um pristine →
  framework-owned, refresh forçado; não bate → adopter-fork, preserve +
  backup + WARNING nomeado. Os DOIS casos legados viram fixtures.
  **`doctor.sh` resolve dessas MESMAS flags de entrega
  (baseline/delivery record), não da ceremony** (r19 refina o r9: só
  ceremony re-incluiria paths pulados e `--strict-orphans` acusaria os
  arquivos do adopter como órfãos) — fixtures de arquivo pré-existente
  para os três paths. **Nenhum gate do repo do
  framework passa a LÊ-LO como autoridade**:
  `check-canonical-doc-freshness.py` continua lendo `VERSION`; a
  preferência marcador-com-fallback é exclusiva de leitores em árvore de
  ADOPTER — os orientados a SPEC/framework
  (`check_tier_a_spec_version_drift`, advisory) **e o update checker
  `.claude/scripts/check-framework-updates.sh:82-103`** (r8: ele resolve o `VERSION` da
  raiz — pós-upgrade reportaria 1.2.0, sairia `behind-minor` e pediria o
  MESMO upgrade em loop eterno; marker-first com fallback + teste de
  regressão coberto pelo AC-3).
  **`check_tier_a_npm_version_match` NÃO adota o marcador**: em árvore de
  adopter o `package.json` da raiz é o do APP — comparar marcador do
  framework × versão do app seria false-red permanente; esse check mantém
  a semântica VERSION×package.json (ou skip quando VERSION ausente).
- `ADR-155-AMEND-1` registra por que a raiz ficou de fora — senão o
  próximo mantenedor "conserta" a assimetria e reabre a classe.
- Semântica para adopter que editou o SPEC local: fork do contrato, não
  customização → backup em `.claude.bak/<ts>/` + replace. Three-way é
  complexidade sem consumidor; recusar-e-instruir bloquearia todo upgrade
  com release de SPEC.

### OQ-4 — F4 = e2e de árvores resultantes, NO CI, por modo de cerimônia

- Fixture A: `install.sh` corrente. Fixture B: install v1.2.0 (pin) →
  `upgrade.sh` corrente. Comparar conjunto + hashes framework-owned.
  Set-equality de enumerações — mesmo derivadas independentemente — nunca
  alcançaria os sites fora da enumeração (é exatamente como F3 nasceu).
- POR modo de cerimônia (maintainer E user) — senão a divergência
  by-design do `--ceremony user` vira allowlist, e allowlist é onde gates
  morrem. **Pré-requisito descoberto pelo r7:** o fixture user-mode NÃO
  FECHA hoje porque `upgrade.sh` chama `_refresh_protocol_pointer()`
  INCONDICIONALMENTE e cria `PROTOCOL.md` na RAIZ — que um install user
  fresco proíbe (guard WS4). O patch de F3 ceremony-gateia TAMBÉM o
  protocol refresh (mesma leitura de `.install-state.json`); é um bug
  latente adjacente que a comparação de árvores expõe, não um caso de
  allowlist.
- Controle positivo: divergência plantada (remover uma linha
  `backup_and_replace` numa cópia) deixa o **JOB de CI** vermelho — não o
  script local (o teste atual nunca rodou em CI; "passa localmente" foi
  exatamente o buraco).
- Fiação: step novo em `smoke-install.yml`; o teste + `SPEC/v1/**` +
  **`scripts/doctor.sh`** (r11: o patch muda a resolução de ceremony do
  doctor e `scripts/tests/*.sh` NÃO roda na suíte geral — sem o path,
  um PR doctor-only pula a regressão) + **`.claude/.framework-version` e
  `.claude/scripts/check-framework-updates.sh`** (r20: ambos exercitados
  pelo AC-3 — PR tocando só um deles pularia o e2e) entram em AMBAS as
  listas `paths:` (pull_request E push — corrigindo a dessincronização
  já existente entre elas). E a perna histórica precisa
  da TAG: o checkout atual usa `fetch-depth: 1` (`smoke-install.yml:53`)
  — o pin `v1.2.0` não resolve em CI e o gate falharia antes de comparar
  qualquer árvore ("passa no clone local" seria exatamente o buraco).
  Fix no mesmo patch: fetch explícito da tag (ou fixture rastreada).
- A lista fechada "required entries" do C.2 é deletada/derivada no mesmo
  patch (conjunto fechado de memória erra nos dois sentidos).
- Cuidado vermelho-por-design: fixture com `VERSION` pré-existente diverge
  por comportamento CORRETO do install — resolvido porque F3 sai na forma
  OQ-3 (upgrade não toca a raiz; marcador em `.claude/`).

## Waves

### W0 — superfícies livres (L2, sem cerimônia)
1. ✅ Evidência do re-pass landada (`PLAN-166/repass-r1/`).
2. **F2 completo**: módulo `_release_bump_sites.py` (`--today`
   obrigatório; o driver passa a INVOCAR o módulo — a tabela `SITES` tem
   UMA fonte, **e o trap de restauração do `--dry-run` DERIVA seus paths
   do módulo** — r19: a lista de restauração manual não conteria o site
   novo do marcador e o dry-run voltaria a sujar a árvore, a classe
   S273; assert pós-dry-run de index E worktree limpos) + predicado mesma-árvore (4 oráculos) + skip por-site +
   `--restamp` (exige `--npm-readme-reviewed`) + gate de ancestralidade
   em `tag()` + assert de **delta restrito em `tag()` — INCONDICIONAL,
   RC e stable, testado nas duas invocações** (r12: escopar só ao
   `--stable` deixaria a rc.2 embarcar um commit pós-review e virar
   baseline não-revisada do GA): o GA NUNCA aponta para o commit da RC
   (o re-pass do hold TEM de commitar
   `.claude/governance/pair-rail-verdict-<tag>.md` — `release.yml:659`
   valida o verdict POR TAG na árvore taggeada); o assert é
   o delta é ancorado no **PARENT REVISADO do verdito** (r11 — uma regra
   para RC e GA): `git diff <parent_sha-do-verdito>..HEAD --name-only`
   contido na allowlist **ESPECÍFICA DA TAG-ALVO** — exatamente
   `.claude/governance/pair-rail-verdict-<TAG>.md`, os
   `verdict-fields-<TAG>` do plano, e os artefatos de auditoria do
   re-pass desta tag como **conjunto FECHADO com hash pinado no verdito
   assinado** (r14: o wildcard `repass-<N>/**` era um buraco — qualquer
   arquivo enfiado no diretório pós-review passaria o guard, e o step 15
   não cobre artefatos de plano; o verdito lista os nomes exatos +
   MANIFEST.sha256, e o assert rejeita qualquer path extra; o PROVENANCE
   TEM de ser commitado — sem os paths pinados, ou o delta rejeita a
   tag, ou o arquivo fica untracked e o clean-tree recusa). Nomes exatos, NUNCA o wildcard
   `pair-rail-verdict-*.md` (deixaria tocar verditos HISTÓRICOS ou o
   template e passar). Qualquer OUTRO arquivo no delta morre alto — a
   invariante real é "NADA landou depois do que o re-pass revisou, além
   do próprio verdito". Ancorar na "última RC" estava ERRADO nos dois
   sentidos (r10→r11): para o GA por acaso coincide (parent = rc.2), mas
   para a rc.2 rejeitaria os próprios fixes W0/W1 que o re-pass acabou
   de revisar. **E o assert local do driver NÃO basta** (r15): tag
   assinada à mão pelo Owner pula o driver, e o step 15 recomputa o
   inputs_hash só sobre o manifest (que exclui as superfícies de bump de
   propósito) — um commit pós-review em `VERSION`/`npm/package.json`
   passaria; o MESMO assert de delta (diff `parent_sha`→commit-da-tag ⊆
   lista pinada no verdito) entra SERVER-SIDE no `release.yml` — **em
   step PRÓPRIO, SEM `continue-on-error`, INDEPENDENTE de
   `CEO_PAIR_RAIL_VERDICT_OPTIONAL`** (debate r3, VETO escopado: o step
   de validação existente tem duas escotilhas acionadas por essa var —
   `continue-on-error` em `:656` e `--parent-sha ""` em `:690-692`, e o
   validador só binda o campo `if args.parent_sha:` (`:245`); herdar a
   vizinhança seria herdar o interruptor — os asserts novos FALHAM
   FECHADO se a var estiver ligada ou se o `parent_sha` não foi validado
   com bind não-vazio, e rodam DEPOIS do step `Verify tag GPG signature`
   com a ordem verify→verdito→delta→ancestralidade DECLARADA e pinada
   por assert estrutural no padrão WaveB5 de ordem) — **e junto o assert
   de ANCESTRALIDADE** (r17: o delta parent→tag não prova que o parent
   estava em `origin/main`; tag manual pula o gate local — o workflow
   verifica `merge-base --is-ancestor` em origin/main **do parent
   revisado E do próprio `GITHUB_SHA`** (r18: checar só o parent deixa o
   cenário tag-sem-push — verdito V sobre parent P, tag pushada, V nunca
   chega ao main — passar com P ancestral e V órfão)). O conjunto pinado fecha por CONTEÚDO, não só por nome
   (r3-SEC2): o verdito assinado pina o sha256 do `MANIFEST.sha256` e o
   assert roda `shasum -c` além da igualdade de conjunto — controle
   positivo: editar evidência + regravar manifest TEM de falhar. Runs
   múltiplos para o mesmo SHA (delete+re-tag): a função de decisão
   avalia o candidato mais recente por `run_attempt`/`created_at` **E
   exige FRESCURA — `created_at` do candidato posterior ao início do
   próprio run do npm-publish** (r20: no re-tag do mesmo SHA o poll pode
   consultar ANTES do novo run do Release existir, e o success ANTIGO
   seria o "mais recente", liberando mesmo que o run novo falhe; um
   candidato pré-datado ao push desta tag não conta), com fixtures na
   enumeração do AC-2 (r3-SEC6+r20). O driver vira conveniência,
   o workflow é o enforcement. (Trajetória: mesmo-commit r2 → allowlist
   r4 → +provenance r10 → âncora parent_sha r11 → conjunto fechado r14 →
   enforcement server-side r15 — codex pré-commit.)
3. **F5 completo**: corrigir `npm/README.md:60,123`, `docs/FAQ.md:109`,
   as 6 ocorrências do pt-BR, **e os 5 sites vivos achados pelo r5
   pré-commit**: `docs/README.md:83`, `docs/WHAT-WE-ARE.md:56,126`,
   `docs/CTO-GUIDE.md:42,81` — com esses 3 docs ADICIONADOS a `DOCS`.
   **Entrar em `DOCS` ativa TODOS os matchers, não só o novo** (r6): os
   3 docs têm de chegar com TODAS as claims frescas — `docs/README.md`
   sozinho carrega **≥9 métricas stale em ≥12 ocorrências, tabela E
   prosa** (debate r3: a enumeração recitada aqui numa versão anterior
   dizia "sete" e já estava errada — a FONTE do censo é RODAR O GATE
   sobre o doc, nunca uma lista de memória) — senão o verify-counts fica
   red e bloqueia o próprio preflight da rc.2. Refresh completo dos 3 +
   controle positivo por rótulo neles também; **o passe inclui
   `docs/ARCHITECTURE.md:73,84,85`** (r3: `:73` diz "~720 test files" e
   `CLAUDE.md:73` diz "~730" — divergência VIVA entre docs vigiados,
   invisível ao gate; e a prosa de `:85` fica errada quando `:74`
   subir) **e decide a métrica `test_files`**: regra nova com a
   derivação que a própria célula Notes já escreve
   (`git ls-files '*test_*.py' '*_test.py' | wc -l`) — ou omissão
   registrada DELIBERADAMENTE, nunca por silêncio. **A edição de
   `CLAUDE.md:73` respeita a disciplina de cache do Gate-1** (§0 do
   próprio arquivo): agendada para o CLOSEOUT da sessão de W0, não
   mid-session; kind novo `approx` no
   `verify-counts.sh`
   com banda **±5% declarada no texto da regra** (justificativa: o
   collect-count real varia com ruído de coleta por diretórios de plano;
   floor não pega undersell — que é o drift observado) para as formas
   `~N,000 cases`/`~N.000 casos`/`~Nk` — **a regra IMPRIME seus inputs**
   (debate r3: comando de coleta, valor observado e contagem de erros de
   coleta; erros > 0 = WARNING nomeado — banda sem inputs impressos é
   licença de drift, e ±700 casos escondem uma família inteira; a lição
   measurement-must-list-its-inputs aplicada à própria regra nova) —
   **derivada do escopo de coleta DOCUMENTADO** (`make test-collect` / roots do `pytest.ini`), NÃO do
   `pytest .claude/` explícito que o `DERIVED_TESTS` atual usa (r12:
   populações divergem — 14.219 com 22 erros de coleta vs 14.172 limpo
   — o gate rejeitaria doc verdadeiro ou aceitaria stale); e **censo
   COMPLETO de claims numéricas dos 3 docs novos** (r12: entrar em DOCS
   só ativa matchers EXISTENTES — `CTO-GUIDE` tem Test files/Workflows/
   Hooks/`_lib`/`# 171 lines`/`44 hooks` sem métrica nem rótulo que
   case; cada número ganha métrica viva + matcher, ou o claim é
   REMOVIDO do doc); **ativar a `approx` obriga a re-datar TODOS os
   claims da forma nos docs JÁ vigiados** (r13: vivo = 14.172; banda ±5%
   → piso ≈13.463; os `~13k`/`~13,000` de `CLAUDE.md:73`,
   `README.md:60,187` e `docs/ARCHITECTURE.md:74` FALHARIAM a regra
   nova — todos sobem para o valor corrente no mesmo passe, senão o
   preflight da rc.2 fica red); `README.pt-BR.md` em `DOCS` com matchers
   por RÓTULO pt; controle positivo POR RÓTULO; checar colisão de
   rótulos pt/EN.
   > **[nota de execução W0, 2026-08-06]** Divergência DELIBERADA do
   > texto revisado deste item: o plano pina "erros > 0 = WARNING
   > nomeado" para a regra `approx`; a implementação landada trata erros
   > de coleta > 0 como **VIOLATION** (`rule: approx/collect-errors`)
   > sempre que a banda foi de fato aplicada a ≥1 site vigiado na run,
   > mantendo WARNING apenas com a banda já suspensa (`--no-tests` /
   > observed 0). Racional: os dois chamadores automatizados só enxergam
   > o exit code (`validate.yml` roda `--quiet`; o preflight do
   > `release.sh` descarta todo o output em `/dev/null`), então um
   > WARNING ali é estruturalmente invisível — a banda seria aplicada a
   > uma população PARCIAL sem nenhum executor capaz de ver o aviso.
   > Teste: `test_collect_errors_fail_when_band_enforced`. O código não
   > será revertido ao texto do plano; a semântica reforçada segue para
   > ratificação no material de verdito/cerimônia do W1.
4. **F6 completo**: renomear driver → `release.sh`; derivar strings de
   `TARGET_BASE`; APAGAR contagens de comentários; corrigir claim de
   publish em `:19`+`:515`; **a ANOTAÇÃO ASSINADA da tag
   (driver `:473-495`) deixa de carregar Scope/ADRs literais**
   (r14: hoje diz "PLAN-162 / PLAN-165 (ADRs 184 -> 188)" — rc.2 e GA
   carregariam metadados INCOMPLETOS numa superfície assinada; o Scope
   passa a ser parametrizado por release com o conjunto COMPLETO do trem
   v1.3.0 — r16: as tags representam a release inteira do CHANGELOG,
   então "PLAN-162 / PLAN-165 / PLAN-166 (ADRs 184 -> 189)", nunca só o
   plano novo); atualizar `release-checklist.md:93-103`;
   **`INSTALL.md:627` (150→210, ADR-110-AMEND-2) corrigido AQUI em W0**
   (arquivo livre; sem condicional).
5. Teste guardando `pair-rail-inputs-hash-manifest.txt` contra entrada de
   arquivos tocados pelo bump — lista derivada DO módulo
   `_release_bump_sites.py` **mais os dois manifests gerados fora dele**
   (`.claude-plugin/plugin.json` e `marketplace.json`, reescritos por
   `build-plugin.py --write-manifests`, driver `:384-392` — derivar só do
   módulo deixaria o guard cego a eles).
   **Decisão registrada (refuta o P1 do review r3 pré-commit):** a
   exclusão dos arquivos de bump do inputs-manifest é DELIBERADA, não a
   cegueira — incluí-los faria todo bump legítimo mudar o `inputs_hash` e
   quebraria a reprodutibilidade do replay do verdito (a razão de o
   manifest existir). A cegueira do step 15 é fechada por OUTRA via: o
   no-op do F2 elimina o commit D+1 e o assert de delta-restrito do
   `tag --stable` mata qualquer delta fora da allowlist de verdito. O
   teste deste item PINA a exclusão como deliberada (leitura, sem mutação
   do manifest → sem entrada nova no escopo da cerimônia).
6. **Autoria de TODOS os testes livres** (iterar flake com sentinel
   assinado na mão é o modo de falha S285/S286): e2e do F4 (fixtures
   reais, dois modos de ceremony), asserts novos de
   `test_release_workflow_asserts.py`, teste D/D+1 do AC-1, e as
   unidades plantadas do AC-2 — **a lista do AC-2 é a ÚNICA fonte; este
   item deliberadamente NÃO repete a contagem** (divergiu duas vezes,
   r5 e r10, exatamente porque era cópia; incl. o fixture GRANT
   obrigatório). Endereços (o plano que diagnosticou "teste que
   nunca roda" endereça os próprios): testes Python em
   `.claude/scripts/tests/` (rodam via `validate.yml:424` +
   `release.yml:332`); `scripts/tests/*.sh` roda SÓ via
   `smoke-install.yml` (fiação de paths em W1).

### W1 — patches canônicos staged + cerimônia GPG única (L3+)
**Disciplina do kernel-override (debate r3):** o token
`CEO_KERNEL_OVERRIDE` é POR-CERIMÔNIA — nunca exportado em
`settings.local.json` nem em perfil de shell — e o evento de auditoria do
override TEM de aparecer no ledger da cerimônia (mesma prova-ao-vivo do
`night_mode_toggled` da cerimônia 2/S293); editar `release.yml` é
literalmente o vetor "CI gate bypass" que o kernel existe para impedir,
então o privilégio máximo do repo fica armado só pelo tempo da
assinatura.
Superfícies que EXIGEM sentinel (verificadas contra `_CANONICAL_GUARDS`,
agora as 7): `.github/workflows/npm-publish.yml`, `scripts/install.sh`,
`scripts/upgrade.sh`, `scripts/_framework_manifest_set.sh`,
`.github/workflows/smoke-install.yml`,
`.claude/governance/npm-trusted-publisher.txt` (casa
`.claude/governance/*.txt` — o consensus r1 errou ao chamá-lo de livre;
erratum aplicado), e **`.github/workflows/release.yml`** (o assert
Forma A (ii) o edita — e ele é canonical **E** entrada exata de
`_KERNEL_PATHS` em `check_arbitration_kernel.py:134`: além do sentinel,
a cerimônia inclui a rota de kernel-override; 3ª instância nesta mesma
release da classe "o plano edita uma superfície que não listou" —
flagrada pelo codex pré-commit, não pelo debate) + `ADR-155-AMEND-1`.
**Nota (dois conceitos distintos):** a lista acima é o conjunto que exige
sentinel; o bloco `Scope:` do `approved.md` enumera **TODO caminho do
commit da cerimônia** — incluindo ADR, fiação de testes e arquivos livres
que embarcam junto — porque a disciplina de land é `touched−scope=∅`
sobre o commit inteiro.
1. **F1 (a′)**: job `await-release-gate` + função de decisão stdlib +
   `needs:` no publish + nota de cabeçalho (por que workflow_run/call
   foram recusados) + timeout 35min + asserts estruturais novos em
   `test_release_workflow_asserts.py` (padrão WaveB5: `needs:` presente,
   environment no publish, exclusão de RC no publish) — pins de posture
   FORTALECIDOS, não relocados.
2. **F3 (OQ-3)**: três listas + ceremony-gate + marcador +
   `ADR-155-AMEND-1` + leitores atualizados.
3. **F4 (OQ-4)**: teste e2e reescrito + fiação smoke-install + paths
   sincronizados + **`timeout-minutes` do job revisado 8→~15** (debate
   r3: o 8 atual já foi esticado de 5 só para os 2 oráculos existentes,
   e o e2e novo adiciona até 4 ciclos install/upgrade completos — sem o
   bump, flake intermitente sob carga de runner; mesma classe do
   perf-gate N=20).
4. `.claude/governance/npm-trusted-publisher.txt` (repo/filename/
   environment) + assert que **LÊ o arquivo** e compara com o
   `npm-publish.yml` (embutir os valores no teste criaria uma 4ª cópia da
   verdade). Controle positivo: trocar `environment:` numa cópia →
   vermelho.
5. **Contagens derivadas do ADR novo**: criar `ADR-155-AMEND-1` sobe a
   contagem exata de ADRs 188→189 — no MESMO commit da cerimônia,
   atualizar **TODOS os sites que os matchers de ADR do
   `verify-counts.sh` alcançam, derivados do PRÓPRIO gate** (r13: lista
   fixa de 5 já nasceu incompleta — `docs/ARCHITECTURE.md:71` também é
   vigiado, e `docs/README.md`, que W0 põe em `DOCS`, tem de chegar ao
   commit da cerimônia já em 189, não 188; censo = rodar o gate, não
   recitar sites) e o valor no `verify-counts.sh` (tolerance=0; regra da
   casa: regenerar superfícies derivadas antes de pushar; r5+r13).
6. Staged em `PLAN-166/staged/` com MANIFEST.sha256 RASTREADO + `shasum -c`
   fail-closed. Scope do sentinel em DOIS grupos (trem de release /
   upgrade do adopter) para revert parcial sem dividir a cerimônia.
   **O bloco `Scope:` é GERADO mecanicamente de `git status --porcelain`
   da árvore staged** (debate r3: ~20 linhas redigidas de memória são a
   classe closed-sets-must-be-derived aplicada ao artefato ASSINADO —
   e reescrever `approved.md` obriga a re-assinar), com
   `touched−scope=∅` conferido ANTES de pedir a assinatura. Slug do
   kernel-override nomeado no texto da cerimônia:
   `PLAN-166-W1-RELEASE-YML-AWAIT-GATE`. O valor 189 no
   `verify-counts.sh` é o DERIVADO da contagem de ADRs, não constante
   digitada.

### W2 — rc.2 + hold + GA
O verdito é POR TAG e o `release.yml:659` o valida NA ÁRVORE TAGGEADA —
logo a sequência de CADA tag é: re-pass → montar+assinar
`pair-rail-verdict-<tag>.md` (+ verdict-fields) → **commitar** →
**push origin main** (o gate de ancestralidade exige HEAD ∈ origin/main
ANTES da tag) → só então tag → push da tag. (Sequenciamento explicitado
pelo review r3 pré-commit; a rc.1 seguiu exatamente isso — o anchor
`b9ee6c4` É o commit do verdito.)
1. Re-pass codex round 2 contra os fixes (pipeline com snapshot limpo —
   ver nota abaixo; até APPROVE).
2. `bump --rc 2` → **verdito rc.2 assinado+commitado → push origin main
   → CI verde no commit do verdito → preflight `--rc 2`** → tag
   `v1.3.0-rc.2` (Owner) → push da tag → CI verde → GitHub pre-release.
   (Ordem do debate r3: preflight ANTES do commit do verdito validaria
   uma árvore que não é a taggeada — a forma exata do F2 recriada pela
   composição r3+r15; nesta ordem, nenhum commit nasce depois do
   preflight, e o preflight roda sobre EXATAMENTE o commit que será
   taggeado — frase que impede a próxima pessoa de "otimizar" a ordem de
   volta.) A rc.2 exercita o `await-release-gate` ao vivo (sem publish —
   exclusão de RC intacta no job publish).
3. Hold ADR-103 24h. Re-pass final contra a rc.2. **O parent do verdito
   GA TEM de ser o commit da rc.2** (r18: se `origin/main` avançou
   durante o hold, o verdito commitado no main novo bindaria
   `parent_sha` numa árvore que o re-pass final NÃO revisou, e o delta —
   que começa no parent — deixaria rc.2..main passar sem revisão; regra:
   antes de autorar o verdito GA, assert `origin/main == <SHA da rc.2>`;
   main avançou → NÃO há GA, corta-se rc.3 e o hold reinicia — que é a
   doutrina do próprio hold). O verdito GA declara o SHA da RC promovida
   e os asserts server-side exigem `parent_sha == <SHA declarado>`.
4. `bump --stable` (no-op provado) → **verdito GA assinado+commitado →
   push origin main → CI verde → `preflight --stable`** (r15: o hold
   pode ter mudado main/CI; r3 do debate: o preflight roda DEPOIS do
   commit do verdito, sobre o commit exato da tag) → tag `v1.3.0` →
   push da tag → aprovação `production-npm` (APÓS gate verde) → GA.
**Nota de protocolo dos re-passes (r3 pré-commit):** o reviewer sob
`--sandbox read-only` LÊ a árvore viva além do payload redigido — essas
leituras não passam pelo redactor nem entram no `inputs_hash`. Nos
re-passes de W2, invocar de um **snapshot limpo do CANDIDATO** —
worktree DETACHED no SHA candidato para o re-pass PRÉ-tag (r17: a tag
rc.2 ainda não existe nesse momento — exigir worktree da tag era
circular), e worktree da tag apenas no re-pass final pós-rc.2 — árvore
verificada limpa e registrada no PROVENANCE — a claim de cobertura do inputs_hash é sobre o PAYLOAD;
dizer mais que isso seria claim falsa.
5. Nota no checklist: "o delta legítimo entre o PARENT REVISADO pelo
   re-pass e a tag são EXCLUSIVAMENTE os artefatos do verdito desta tag
   (`pair-rail-verdict-<tag>.md` + verdict-fields + a evidência
   `PLAN-166/repass-<N>/**`); qualquer outro arquivo no delta = algo
   landou sem revisão" (espelha EXATAMENTE o assert do W0.2 — r11
   sincronizou os dois textos, que haviam divergido).

## Acceptance criteria

- [x] AC-1 [P0][F2] ✅(W0 f492545: teste D/D+1, HEAD+porcelain+índice; no-op 4-oráculos provado no clone) `bump --stable` em D+1 sobre árvore já no alvo:
      **`git rev-parse HEAD` idêntico antes/depois E
      `git status --porcelain` vazio E índice limpo** (r7: HEAD sozinho
      passa se a implementação escrever/stagear stamps sem commitar — e
      aí `tag()` aborta em árvore suja; o invariante prometido é
      NÃO-ESCRITA, não só não-commit); teste com `--today` D e D+1
      explícitos passa nos dois; e um caso de mudança REAL (versão nova)
      continua escrevendo.
- [x] AC-2 [P0][F1] ✅(W0: bateria completa da enumeração incl. GRANT, null-running, frescura re-tag; GateContext fail-loud) A função de decisão retorna GRANT/WAIT/BLOCK por
      avaliação de ponto; GRANT SÓ com: run de `release.yml` +
      `event==push` + `head_branch==<tag>` + `head_sha==GITHUB_SHA` +
      job `release-gate` `conclusion=="success"`. **Controles plantados
      (unit, sem rede; a ENUMERAÇÃO abaixo é a fonte — sem
      numeral-espelho, que divergiu 4× entre rounds):**
      **Semântica única (r16, alinhada ao §OQ-1): runs NÃO-candidatos
      são IGNORADOS — nunca BLOCK imediato; bloqueia candidato exato
      failed/skipped, deadline, ou input imparseável.**
      GRANT (obrigatório): fixture com candidato exato
      (workflow+push+tag+SHA+job success) TEM de retornar GRANT — sem
      ele, uma implementação sempre-BLOCK passa na bateria inteira.
      NUNCA-GRANT (segurança; esperado = WAIT dentro do prazo, BLOCK só
      no deadline): listas contendo APENAS runs verdes não-candidatos —
      head_branch de rc; head_sha de outro commit; workflow errado com
      release-gate success no mesmo ref; `event == workflow_dispatch`
      com o resto batendo (r12/r14/r16 — cada um prova que run verde
      parecido NÃO libera E NÃO bloqueia falsamente a corrida). BLOCK:
      candidato exato com job skipped; candidato exato com conclusion
      failure; nenhum candidato COM deadline estourado; JSON malformado.
      WAIT: nenhum run dentro do prazo; candidato presente mas job
      `release-gate` ausente do payload, dentro do prazo (r9 —
      consistência eventual); candidato com `conclusion: null` (running)
      dentro do prazo — mata a implementação `!= "failure"`. Asserts estruturais:
      `needs: await-release-gate` no publish; environment e exclusão de
      RC intactos no publish. Declarado o que a rc.2 prova e o que NÃO
      prova: prova o poll ao vivo; a aresta `needs:`+publish só é
      exercida no GA (o `if` de RC pula o publish).
- [ ] AC-3 [P0][F3] Upgrade de fixture v1.2.0-maintainer entrega
      `SPEC/v1` novo + `.claude/.framework-version` correto e NÃO toca
      `VERSION` da raiz; fixture `--ceremony user` NÃO recebe `SPEC/v1`;
      backup em `.claude.bak/` presente quando havia SPEC editado;
      **`check-framework-updates.sh` na fixture pós-upgrade reporta a
      versão NOVA (marker-first) e NÃO pede o mesmo upgrade de novo**
      (r8 — sem isso o updater documentado loopa `behind-minor`).
      **Obrigatório o cenário de 2º upgrade** (r6): fixture cuja baseline
      JÁ contém `SPEC/v1`, com SPEC editado localmente → o refresh
      FORÇADO tem de substituir (com backup) — sem esse fixture, o AC
      passa pela rota genérica no 1º upgrade (baseline sem SPEC →
      fallback sobrescreve) e a rota forçada, que é o requisito, fica
      sem prova exatamente no caso load-bearing.
- [ ] AC-4 [P1][F4] Divergência plantada install≠upgrade deixa o JOB de
      CI vermelho (run real observada) nos DOIS modos de cerimônia.
- [x] AC-5 [P1][F5] ✅(W0: approx±5% com inputs impressos + sweep decimal-k; controles por rótulo pt plantados e vermelhos) Todos os sites `~N.000`/`~N,000`/`~Nk` corrigidos
      (npm/README, FAQ, e TODAS as ocorrências do pt-BR — **censo pelo
      gate, não por numeral recitado**: a contagem "×6" citada em rounds
      anteriores já provou ser ×7 no r19, terceira falha da classe
      numeral-espelho neste plano); kind `approx` implementado no
      `verify-counts.sh` com banda ±5% DECLARADA na regra; controle
      positivo POR RÓTULO no pt-BR (número errado plantado em cada
      rótulo vigiado → falha) + um plantado fora da banda na forma
      `~Nk` → falha.
- [x] AC-6 [P2][F6] ✅(W0: release.sh renomeado; grep de superfícies vivas = 0; anotação parametrizada com o trem completo) Driver renomeado `release.sh`; zero strings v1.2.0 /
      contagens de sites em comentários; claim de publish correta nas 2
      ocorrências; checklist atualizado; **`INSTALL.md:627` descreve
      150→210 (ADR-110-AMEND-2)**; grep de controle sobre superfícies
      VIVAS: `grep -rn 'release-v1-2-0' .github/ RELEASE.md` vazio —
      `PLAN-166/repass-r1/**` e `PLAN-166/debate/**` são evidência
      imutável e FICAM FORA do rename (um sed neles quebraria o
      MANIFEST.sha256).
- [ ] AC-7 rc.2 cortada com `await-release-gate` verde ao vivo; hold
      cumprido; re-pass final GO; GA publicado com aprovação pós-gate.

## Riscos

- **Composto F1+F2 (declarado):** "tag em commit fora de main sem CI"
  (nada verifica ancestralidade hoje) + "publish sem observar gate" =
  caminho único para publicar árvore não revisada. **Proibido adiar F1
  ou F2 para pós-GA.** O gate de ancestralidade em `tag()` e o
  `await-release-gate` fecham as duas pernas.
- **Cegueira do step 15:** o replay do pair-rail não cobre os arquivos
  que o bump toca — o teste do W0.5 impede reintrodução silenciosa.
- **Timeout:** publish tinha 8min vs gate 20min+fila — await-job com
  35min próprios; nota de UX no checklist com a ROTA DE RECUPERAÇÃO:
  re-rodar o job `await-release-gate` depois que o `release-gate` ficar
  verde (o run da tag está pinado à árvore da tag — re-run seguro, sem
  delete/re-tag). E a semântica da aprovação manual pós-gate: é a última
  chance humana, não uma segunda opinião sobre o gate.
- **F1 mexe na vizinhança do OIDC:** o fix (a′) NÃO muda filename nem
  environment; ainda assim, Owner confirma os 3 campos do trusted
  publisher no console npmjs antes de landar
  (`npm-trusted-publisher.txt` registra o esperado).
- **Contenção codex:** outra sessão local usa `codex exec`; rounds podem
  degradar — retry com backoff; nunca aceitar transcript truncado.
- **Orçamento honesto:** 3-4 sessões (cerimônia + rc.2 + hold 24h + GA),
  não 2.

## Deferred

- Refactor `workflow_call` (gate reusável chamado por ambos os
  workflows): candidato pós-GA; elimina o poll por construção ao custo de
  refatorar `release.yml` (29 steps pinados) e 3 testes de
  `WaveB5ReleaseYmlTest`. **Gatilho:** quando `release.yml` for
  refatorado por outro motivo — não como item independente.
- Passe na família "script livre que decide gate de release"
  (`check-canonical-doc-freshness.py`, `verify-counts.sh`) — mesma forma,
  plano próprio.
- ADR break-glass para kill-switches em variáveis de repositório
  (`CEO_SOTA_DISABLE`, `CEO_PAIR_RAIL_VERDICT_OPTIONAL`).
- `check_tier_a_spec_version_drift` vacuoso (ceo-boot) — registrar em
  memória; classe vacuous-check.

## §-final — Estado de fechamento e subsunção (PLAN-169 W0.5, 2026-08-08)

> Escrituração exigida pelo ledger do PLAN-169 (A.5.1–A.5.5, F.8,
> F.14). Este § registra POR QUE AC-3/AC-4 permanecem `[ ]` acima e
> onde cada um foi de fato provado. Convenção: **AC provado no registro
> de execução; checkbox não usado** (mesma convenção ratificada para
> PLAN-167/168 no PLAN-169 W0.8).

**O que já fechou.** W0 fechou na S295; W1 (patches canônicos +
cerimônia GPG) **landou em `9d3f21d`** (2026-08-07, "ceremony(PLAN-166
W1): findings-closure landada"). A única perna viva deste plano é o
**W2 (re-pass → verdito rc.2 → tag → hold 24h → GA v1.3.0)**,
sequenciado como **W6.1 do PLAN-169** (ordem pinada; main congelado do
corte da rc.2 até o GA). O frontmatter `executing` está CORRETO — o
watchdog que classifica este plano como *stranded* está lendo espera
de fila, não abandono.

**AC-3 [P0][F3] — provado por subsunção no PLAN-167/168.** Os 8
cenários exigidos existem e rodam em CI (45/45 pós-168):
`scripts/tests/test-upgrade-spec-ownership.sh:7-19,194-197,247-262,274-282,318-330`,
wiring em `.github/workflows/smoke-install.yml:27,81,128`. O upgrade
de SPEC/marker é decidido pelo `_ownership_verdict()` (PLAN-167, land
`7c0828a`; registro em PLAN-167 §7) e os follow-ups fecharam no
PLAN-168 (`67a4c75` + fix-forward `8a178f5`; registro em
PLAN-168 §W2). O cenário de 2º upgrade (refresh forçado com backup)
está coberto — o e2e INV-4 (`test-protocol-pointer-inv4.sh`) asserta
os BYTES do backup real (PLAN-168 V2-P2).

**AC-4 [P1][F4] — satisfeito COM exceção nomeada.** O e2e de paridade
install≠upgrade + controle positivo rodam nos DOIS modos de cerimônia
(`.github/workflows/smoke-install.yml:240-243,251-259,267-268`). A
exceção: o **2º fator do controle aceita evidência não-causal**
(`smoke-install.yml:206`, achado r6-P2 deste plano) — defeito herdado
pelo **PLAN-169 W2** (cura conhecida: exigir
`positive control: FIRED in every mode` + per-mode verdicts `:1`).
Rota ratificada (PLAN-169 OQ-5): **GA v1.3.0 com exceção nomeada no
release-checklist**; a cura não gateia o trem.

**Ratificação `approx`/collect-errors (F.14) — AGENDADA para a rc.2.**
O W0.3 prometeu ratificar a semântica `approx` (erros de coleta > 0 =
VIOLATION, `rule: approx/collect-errors`) "no material de
verdito/cerimônia do W1" — isso não aconteceu (0 hits no `approved.md`
assinado e no `W1-ceremony-log.md`). Registro aqui + compromisso: a
ratificação entra no **material assinado do verdito rc.2** (próxima
superfície assinada do trem W6.1), não em superfície não-assinada.

**AC-7** segue aberto por construção — é o próprio trem W6.1
(rc.2 + hold + GA).
