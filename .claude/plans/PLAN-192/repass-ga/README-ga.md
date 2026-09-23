<!-- Material do kit de corte do GA v1.4.1 (PLAN-192). Este arquivo é rastreado ANTES do
     candidato e não muda no commit do veredito: o guard de delta o recusaria por nome. -->

# Re-pass do GA v1.4.1 (promoção da rc.1) — escopo, o que fica de fora e critério de parada

## 0. O GA em relação à rc.1

- **Árvore.** O GA promove a `v1.4.1-rc.1` depois do hold ADR-103 de 24 h (o G0 do
  `OWNER-GA-CUT.sh` confere o `publishedAt` do pre-release). A rodada 3 do re-pass da rc.1 revisou
  o candidato `7602fbe4` e deu `GO-WITH-CONDITIONS` nas três partes; o veredito assinado está em
  `51bd2345`, o commit da tag. Depois daquele candidato mudaram só o envelope assinado da rc.1
  (`.claude/governance/pair-rail-verdict-v1.4.1-rc.1.md`), `CLAUDE.md` e arquivos de planos
  numerados (`.claude/plans/PLAN-<N>*`, de qualquer plano). Nenhum desses caminhos está numa
  pathspec das três partes.
- **Controles mecânicos disso.** Entre a tag da rc.1 e o candidato revisado, o `OWNER-GA-CUT.sh`
  recusa o corte se mudar qualquer caminho fora de `CLAUDE.md` e de `.claude/plans/PLAN-<N>*` (no
  G0, contra o HEAD, e de novo no passo 5, contra o candidato); sobre o candidato entra só o
  commit do veredito do GA (envelope, fields e evidência), e o passo 2 recusa um bump que não
  seja no-op antes de qualquer push. O runner confere, por parte, se algum arquivo da pathspec
  mudou entre o candidato que a rc.1 revisou e o do GA (`git diff --quiet` entre os dois
  commits) e põe o resultado no prompt da parte e na PROVENANCE.
- **Adopters do GA.** Além de quem sobe por `upgrade.sh`, o GA publica o pacote npm, e o
  `npx ceo-orchestration` roda o mesmo `install.sh`: numa instalação nova o hook chega
  registrado pelo template de settings quando é o `install.sh` que cria o
  `.claude/settings.json` (condição 3, reescrita para o GA).
- **O que o GA acrescenta ao que fica FORA (§4):** o envelope assinado da rc.1, material de
  release. O `install.sh` e o `upgrade.sh` não copiam `.claude/governance/` para o alvo; o pacote
  npm empacota `.claude/` com as exclusões do passo «Stage bundle» do `npm-publish.yml`, que não
  excluem `.claude/governance/`. `CLAUDE.md` e os planos numerados já estavam fora.
- **Achados.** Nada foi curado entre a rc.1 e o GA: da tag da rc.1 ao candidato revisado, main
  recebeu só `CLAUDE.md` e planos numerados, fora de toda pathspec. Segue aberto tudo o que a
  rc.1 declarou aberto — nas seções A a D das condições, que seguem no GA, e, dos três vereditos
  da rodada 3 da rc.1 (`repass-rc1/verdict-rc1-{1,2,3}.txt`, pinados pelo envelope assinado
  dela), os achados sob «NEW FINDINGS (annex)» e os P2 —, nenhum curado por mudança de código ou
  de texto; um P2 que dependia de a tag do GA ainda não existir perde o objeto com o próprio GA.
  Os P1 desse anexo NÃO estão no «Known-open» do `CHANGELOG.md` `[1.4.1]`, que é o texto do
  candidato da rc.1 e segue datada de 2026-09-18. Nenhuma versão é prometida para a cura deles,
  nem para a do anexo P1 da v1.4.0: em 2026-09-18 ela foi re-alvejada para a 1.4.2 (o que a
  entrada `[1.4.1]` do CHANGELOG e a anotação assinada da tag dizem), e em 2026-09-22 o Owner fez
  da 1.4.2 uma release expressa que não a leva e a re-declara aberta (condição 1). A promessa do
  envelope da rc.1 — o do GA diria, item a item, o que foi curado — tem a mesma resposta para
  cada item que a rc.1 declarou aberto: nenhum foi curado entre a rc.1 e o GA (cabeçalho das
  condições). Achado depois do re-pass da rc.1 e declarado no GA (seção E, condição 23): o hook
  grava uma cópia do arquivo que um `scriptPath` nomeia antes da decisão de permissão do
  harness; a cura está alvejada para a 1.4.2.
- **Kit.** `run-ga-repass.sh`, `CONDITIONS-ga.md`, este README, `gen-envelope-ga.py`,
  `OWNER-GA-CUT.sh` e `test-ga-kit.sh` são DERIVADOS do kit da rc.1 por `derive-ga-kit-141.py`
  (âncoras exatas, fontes pinadas por sha256; `--check` compara o disco com a derivação). O que
  muda: a moldura GA do prompt e a conferência com a rc.1; nas condições, o cabeçalho, a condição
  1 (a lista errada dos arquivos citados que mudam deu lugar à classe deles, conferida pelo
  derivador; e a cura do anexo da v1.4.0 sem versão prometida), a condição 3 (instalação nova),
  as referências re-ancoradas (na rc.1 quando falam do passado, no escopo do GA quando falam do
  escopo), a seção C e a seção E (condição 23, sondada no código pelo derivador); `--stable` com bump no-op
  obrigatório; no G0, o kit commitado, o hold, o congelamento, o Scope assinado da tag, o limite
  do `CLAUDE.md` e as retomadas; `--g0-only`; espera de CI de até 150 min; aviso de carga e da
  sonda GPG antes dos preflights; publish REAL no npm com o Release em draft até o registry
  confirmar; `tool_versions.claude_code` medido no passo 9 (`claude --version`), não digitado.
  A lista exaustiva são as âncoras do derivador.
- **Re-pass antes da cerimônia.** O CEO pode rodar o runner antes do `OWNER-GA-CUT.sh`: com o CI
  verde no HEAD == `origin/main`, `git rev-parse HEAD > .claude/plans/PLAN-192/repass-ga/CANDIDATE.sha`
  e depois `bash .claude/plans/PLAN-192/repass-ga/run-ga-repass.sh`. O passo 5 mantém esse
  `CANDIDATE.sha` byte a byte quando ele aponta o mesmo commit, e o passo 6 reconhece a evidência
  completa e não re-roda.
- **Critério de parada (proposto por este kit, fixado ANTES da 1.ª rodada do GA):** `NO-GO` só por
  condição declarada FALSA ou por P0. Toda tentativa, completa ou parcial, é arquivada FORA do
  repositório, num diretório novo em `$HOME/.ceo-ga-archive/`: o G0 recusa arquivo não rastreado
  no plano fora da evidência deste corte, e o runner recusa rodar sobre evidência anterior. Vão para lá os
  arquivos NÃO rastreados de `repass-ga/` (`git status --porcelain --untracked-files=all --
  .claude/plans/PLAN-192/repass-ga/`), menos o `CANDIDATE.sha`, que fica (copie-o); o runner, as
  condições, este README e o `.gitignore` são rastreados e ficam. O diretório arquivado é
  commitado no plano no closeout, depois do corte (nunca durante o freeze) e sem o `.cut-state`.
  Uma `NO-GO` (a linha `VERDICT: NO-GO` em algum veredito) ⇒ parar, arquivar em
  `repass-ga-<data>-NOGO-r1/`, mover junto o `.cut-state` (ignorado pelo git; sem ele a próxima
  tentativa recomeça do passo 1, e com ele o G0 recusa um HEAD que não seja o candidato gravado) e
  levar ao Owner. Não há 2.ª rodada do GA por conta própria. Sem `NO-GO` e com parte sem veredito
  — morte por capacidade do modelo (a PROVENANCE diz) ou por infraestrutura (rede, `npx`, `git`,
  `gpg`; o runner morto antes do codex, com ou sem PROVENANCE) — não é rodada: arquive do mesmo
  jeito, com o sufixo `-capacidade` ou `-infra`, mantenha o `CANDIDATE.sha` e o `.cut-state` e
  re-rode o `OWNER-GA-CUT.sh` (ele retoma do passo 6).
- **O que segue (§1–§8) é o texto da rc.1**, mantido porque descreve o mesmo escopo e a mesma
  medição; os nomes de arquivo do kit são os do GA. Onde ele fala de «rodada N» ou de «este
  re-pass» no passado, é o re-pass da rc.1; o critério de parada da §5 é o da rc.1 (o do GA é o
  de cima).

## 1. O que é esta release, medido

Patch FORA DE ORDEM sobre o GA v1.4.0 (tag `23b79dda` → commit `f9db82ec`, 2026-09-15). Medido em
2026-09-18 sobre `v1.4.0..737814a5` (antes da relmeta e do bump): 101 arquivos, dos quais 58 em
`.claude/plans/` e 6 em `docs/research/`; os outros 37 são o que o re-pass da rc.1 dividia entre «dentro»
e «fora». Os três diffs das partes abaixo têm 54 / 34 / 82 KB a `-U1`, muito abaixo do teto do redator
(262.144 bytes sobre o INPUT); o bump acrescenta 12 arquivos de uma linha à parte 2.

Depois dessa medição landou a correção da cifra aproximada de testes nos docs (`~15,400` → `~16,200`;
o `verify-counts` completo do preflight acusava drift: 16.231 coletados, fora da banda de ±5 %). Ela
toca 9 arquivos de uma ou duas linhas; `docs/FAQ.md` e `docs/WHAT-WE-ARE.md` entraram na parte 2 por
causa dela, e `CLAUDE.md` segue fora (§4).

**Rodada 2.** A rodada 1 (candidato `9e9840b2`, o commit do bump) devolveu `NO-GO` nas três partes por
cinco condições declaradas falsas contra o código — 7, 10, 12, 14 e 15 —, sem P0. Está arquivada em
`.claude/plans/PLAN-192/repass-rc1-20260918-NOGO-r1/`, com a triagem em `record.md`. O candidato da
rodada 2 corrige TEXTO e nenhum código: as condições, o `CHANGELOG.md`, os dois docs de operador e este
README. Os achados de código da rodada 1 seguem abertos e declarados (seção D das condições).

**Rodada 3.** A rodada 2 (candidato `3ed81cf6`) devolveu `GO-WITH-CONDITIONS` nas partes 1 e 3 e `NO-GO`
na parte 2, por UMA frase da condição 14 repetida no `### Fixed` do CHANGELOG: a limpeza do
`relaunch --out` era descrita como «só o inode que esta chamada criou», e ela é um `lstat` seguido de
um `unlink` — dois passos, não uma operação atômica. Está arquivada em
`.claude/plans/PLAN-192/repass-rc1-20260918-NOGO-r2/`. O candidato da rodada 3 corrige de novo só
TEXTO; a cura estrutural do `relaunch --out` fica para depois desta release, por decisão do Owner.

## 2. As três partes, na ordem de risco para o adopter

| parte | o que é | por que nesta ordem |
|---|---|---|
| 1 | `.claude/hooks/check_workflow_launch.py` + `.claude/hooks/_lib/launch_ledger.py` | é o código que RODA na sessão do adopter, antes e depois de toda chamada da tool `Workflow`, e é o único que pode BLOQUEAR |
| 2 | `.claude/settings.json`, `templates/settings/**`, `scripts/build-plugin.py`, `.claude/scripts/env-inventory.json`, `CHANGELOG.md`, `INSTALL.md`, `README.md`, `README.pt-BR.md`, `npm/**`, os sítios de versão do bump (`VERSION`, `.claude/.framework-version`, `.claude-plugin/**`, `pyproject.toml`, `SBOM.md`, `SECURITY.md`, `VERSIONING.md`, `docs/ARCHITECTURE.md`) e os docs de inventário (`docs/COMMAND-SKILL-HOOK-MAP.md`, `docs/CTO-GUIDE.md`, `docs/GUIA-COMPLETO.md`, `docs/README.md`, `docs/FAQ.md`, `docs/WHAT-WE-ARE.md`) | é por onde o hook CHEGA (ou não chega) registrado, e é onde a release afirma coisas ao adopter |
| 3 | `.claude/scripts/ceo-launches.py`, `approval_gate.py`, `test_refs.py`, `mutant_sandbox.py`, `worktree_lock.py`, `phase_checkpoint.py`, `docs/workflow-recovery.md`, `docs/approval-gate.md` | são chamadas por vontade do operador; nenhuma roda sozinha |

### O manifesto de cada parte é DERIVADO, nunca uma lista fixa

A pathspec acima é a INTENÇÃO; `paths-ga-N.manifest.txt` é derivado dela contra o candidato no momento
do run (`git diff --name-only v1.4.0..candidato -- <pathspec>`). Os sítios de versão mudaram no
commit do bump da rc.1 (`9e9840b2`), dentro de `v1.4.0..candidato`; no GA o bump é no-op (passo 2
do `OWNER-GA-CUT.sh`) e não há commit de bump. Derivar contra o candidato pega o que uma lista
medida antes esqueceria.

## 3. Cobertura anterior, citada dentro do próprio prompt

- Partes 1 e 3 (`ceo-launches.py`): PLAN-190 W1 — debate r1 (3 críticos, consenso PROCEED) e SEIS
  rodadas de pair-rail, as cinco primeiras `NO-GO` com cura de classe a cada uma; a r6 foi a rodada
  final, sem P0; assinado pelo Owner em `075beed9`. O P2 da r6 sobre `relaunch --out` é a W1.1, curada
  neste delta com prova por mutação.
- Parte 2: a registração nos templates viajou no mesmo patch assinado da W1; os sítios de versão são
  escritos pelo `release.sh bump` e não têm rail próprio.
- Parte 3, as cinco CLIs de W2/W3: landaram LIVRES, com testes e SEM rodada de pair-rail. **A rodada 1
  do re-pass da rc.1 foi a primeira revisão cruzada delas** e achou pelo menos um P1 ou P2 em cada uma das
  cinco — abertos, listados no `CHANGELOG.md` `[1.4.1]` e nos vereditos arquivados.

## 4. O que fica FORA, e por quê

| fora | motivo |
|---|---|
| `.claude/hooks/tests/**`, `.claude/scripts/tests/**`, `tests/**` (inclui as fixtures) | não são entregues a adopters; são o oráculo, e o oráculo roda no CI do candidato |
| `.claude/plans/**`, `docs/research/**` | registro de trabalho; não são entregues |
| `CLAUDE.md` | contrato de operação DESTE repositório; o adopter recebe `templates/CLAUDE.md`, que não mudou |
| `.claude/governance/codex-cli-pin.txt` e `codex-cli-pin-manifest.json` | re-pin do codex sob cerimônia assinada própria (`PLAN-189/codex-pin*/`); `.claude/governance/` não é entregue a adopters |
| `.claude/scripts/local/release.sh`, `.claude/governance/gate-scripts-manifest.txt`, `.claude/scripts/tests/test_release_bump_sites.py` | a relmeta-141, sob cerimônia assinada própria (`PLAN-192/relmeta/`); engenharia de release. O manifesto e o teste não são entregues. O `release.sh` É entregue, só pelo `upgrade.sh` (ele enumera `.claude/scripts/` recursivamente e o predicado de exclusão não exclui `.claude/scripts/local/`; a instalação fresca copia só o nível de cima) — a rodada 1 corrigiu esta linha, que dizia «não entregue» |

Do que está fora, só o `release.sh` chega à árvore de um adopter, e nenhum hook, comando, settings,
template, skill ou script de nível de cima entregue o referencia. A divergência instalação × upgrade
sobre `.claude/scripts/local/` é achado aberto da rodada 1.

## 5. Critério de parada da rc.1 (histórico — o do GA está na §0)

O texto abaixo é o critério que valeu para o re-pass da rc.1. O do GA, fixado antes da
1.ª rodada do GA, está na §0: uma rodada, e uma `NO-GO` volta ao Owner.

- `NO-GO` só por condição declarada FALSA contra o código ou por P0. Um P1 não declarado vai para
  «NEW FINDINGS (annex)» e entra no material assinado.
- No máximo DUAS rodadas de re-pass. Se a 2.ª ainda der `NO-GO`, PARAR e levar as duas ao Owner. Não há
  3.ª rodada por conta própria.
- Foi o que aconteceu: a 2.ª deu `NO-GO` numa parte, o CEO parou e levou as duas ao Owner, e o Owner
  decidiu (2026-09-18) por uma 3.ª rodada só de texto. Critério fixado ANTES de ela rodar: é a última
  desta via — outra `NO-GO` ⇒ parar de novo e voltar ao Owner.
- Uma parte morta por capacidade do modelo (sem veredito, com a assinatura do servidor no transcript)
  NÃO é uma rodada: o runner a re-tenta até 2 vezes e a PROVENANCE declara quantas mortes houve.
- Toda tentativa, completa ou parcial, é preservada: o runner recusa rodar por cima de evidência
  anterior. Na rc.1 a tentativa era arquivada como `repass-rc1-<data>-NOGO-rN/`; no GA
  vale a §0 (fora do repositório, em `$HOME/.ceo-ga-archive/`, commitada no closeout).

## 6. As condições declaradas

`CONDITIONS-ga.md`, neste diretório. Elas viajam em TODAS as partes como DADO para o revisor, e o
snapshot bruto que ele viu (`CONDITIONS-ga.reviewed.md`) é o que entra nos fields assinados — mudar
uma vírgula depois da revisão exige novo re-pass. A condição 1 é a decisão do Owner sobre o anexo da
v1.4.0 (PLAN-192 OQ-1).

## 7. Codex pinado, sem tocar na máquina

O runner lê a versão de `.claude/governance/codex-cli-pin-manifest.json` e tem duas rotas: o binário
global, quando ele é a versão pinada; senão `@openai/codex@<versão>` resolvido por `npx` num cache
próprio (`.npx-cache/`, ignorado pelo git). Nas duas o sha256 do payload nativo é verificado contra o
manifesto pelo mesmo oráculo do pair-rail-gate (`check_pair_rail.py --verify-codex-pin`, fail-CLOSED)
antes de qualquer revisão, e um shim vai no início do PATH. A ordem difere entre as rotas: na
global o payload é verificado ANTES de executar; na do npx o pacote resolvido já roda uma vez
(`npx -y <pacote> --version`, para achar a versão e materializar o launcher) antes da
verificação. A PROVENANCE registra a rota usada. O modelo vai por `-m`, lido da tabela raiz de
`~/.codex/config.toml` ou de `CODEX_MODEL`, e a PROVENANCE registra o valor e a origem.

## 8. Onde o candidato entra

O candidato é o HEAD de `origin/main` gravado em `CANDIDATE.sha` depois do CI verde — pelo passo 5 do
`OWNER-GA-CUT.sh`, ou pelo CEO quando ele roda o re-pass antes da cerimônia (o passo 6 reconhece a
evidência completa e não re-roda). Na rodada 1 era o commit do bump (`release: v1.4.1`, `9e9840b2`); nas
rodadas 2 e 3 é o último commit de correção de texto sobre ele. O runner nunca lê o candidato de uma
constante, e o commit do veredito senta DIRETAMENTE sobre o candidato: `parent_sha` == pai do commit
que introduz o veredito.
