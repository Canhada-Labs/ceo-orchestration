<!-- Material do kit de corte do GA v1.4.2 (PLAN-193). Este arquivo é rastreado ANTES do
     candidato e não muda no commit do veredito: o guard de delta o recusaria por nome. -->

# Re-pass do GA v1.4.2 (promoção da rc.1) — escopo, o que fica de fora e critério de parada

## 0. O GA em relação à rc.1

- **Árvore.** O GA promove a `v1.4.2-rc.1` depois do hold ADR-103 de 24 h: o pre-release foi
  publicado em `2026-09-29T03:32:20Z` e o hold acaba em `2026-09-30T03:32:20Z` (o G0 do
  `OWNER-GA-CUT.sh` confere o `publishedAt`). A rodada 1 do re-pass da rc.1 revisou o candidato
  `9b5b1b40` (o commit do bump, `release: v1.4.2`) e deu `GO-WITH-CONDITIONS` nas quatro partes; o
  veredito assinado está em `9a486d29`, o commit da tag. Depois daquele candidato mudaram só o
  envelope assinado da rc.1 (`.claude/governance/pair-rail-verdict-v1.4.2-rc.1.md`), `CLAUDE.md` e
  arquivos de planos numerados (`.claude/plans/PLAN-<N>*`: os fields e a evidência da rc.1, os
  LEDGERs, o `.tag-push-epoch` da rc.1 e o kit do GA). Nenhum desses caminhos está numa pathspec
  das quatro partes: nenhuma das quatro pathspecs muda entre `9b5b1b40` e `b20f8a6c` (o closeout
  da rc.1), e todo caminho que muda entre eles cai numa classe da §4.
- **O que o re-pass do GA revisa.** As mesmas quatro partes, com as mesmas pathspecs (§2), sobre a
  faixa `v1.4.1..candidato`: a base segue a tag `v1.4.1`, e o candidato é o HEAD de `origin/main`
  no momento do corte (ou do pré-run, abaixo), gravado em `CANDIDATE.sha`. Antes de montar qualquer
  payload, o runner recusa pelo nome uma base que não seja o commit contra o qual a rc.1 fez o
  diff, um candidato que não descenda do da rc.1, um caminho mudado desde o candidato da rc.1 fora
  de `CLAUDE.md`, dos planos numerados e do envelope da rc.1, e — por parte, com `git diff --quiet`
  entre os dois commits — uma pathspec que mudou; o prompt de cada parte diz ao revisor que o diff
  dela é, em conteúdo, o que a rc.1 revisou. A sonda do GA confere a mesma igualdade (§9).
- **Controles mecânicos da promoção.** Entre a tag da rc.1 e o candidato, o `OWNER-GA-CUT.sh`
  recusa o corte se mudar qualquer caminho fora de `CLAUDE.md` e de `.claude/plans/PLAN-<N>*` (no
  G0, contra o HEAD, e de novo no passo 5, contra o candidato); sobre o candidato entra só o commit
  do veredito do GA (envelope, fields e evidência); e o passo 2 recusa, antes de qualquer push, um
  `bump --stable` que não seja no-op — `.claude/.framework-version` e `npm/package.json` dizem
  `1.4.2` desde o bump da rc.1.
- **Adopters do GA.** Além de quem sobe por `upgrade.sh --pin v1.4.2` e de quem instala de um
  checkout da tag pelo `install.sh`, o GA publica no npm — a rc não publica: o `npm-publish.yml`
  pula as tags com `-rc.` —, e o `npx ceo-orchestration` roda o mesmo `install.sh`: o pacote é um
  shim que o chama (`npm/bin/ceo-orch-init.js`). Em 2026-09-29 o `latest` do npm era `1.4.1`; o
  publish do GA (`npm publish` sem `--tag`) o leva a `1.4.2`.
- **O que o GA acrescenta ao que fica FORA (§4).** Na classe `.claude/governance/**`, o envelope
  assinado da rc.1, material de release: nem o `install.sh` nem o `upgrade.sh` copiam
  `.claude/governance/` para o alvo; o pacote npm empacota `.claude/` sem excluí-lo (passo «Stage
  bundle» do `npm-publish.yml`), e o `install.sh` que o shim roda também não o copia. Na classe
  `.claude/plans/**`, os fields e a evidência da rc.1, os LEDGERs, o `.tag-push-epoch` da rc.1 e o
  kit do GA; na classe `CLAUDE.md`, o closeout da rc.1. As três classes já estavam na
  `out_of_scope_pathspec` do runner da rc.1, que o do GA mantém.
- **Achados.** Nada foi curado entre a rc.1 e o GA: da tag da rc.1 ao candidato, `main` recebeu só
  `CLAUDE.md` e planos numerados, fora de toda pathspec. Segue aberto tudo o que a rc.1 declarou
  aberto — a dívida carregada das condições 1 e 2, que seguem no GA — e, dos quatro vereditos da
  rodada 1 da rc.1 (`repass-rc1/verdict-rc1-{1,2,3,4}.txt`, pinados pelo MANIFEST cujo sha256 o
  envelope assinado dela carrega), os três P1 sob «NEW FINDINGS (annex)» — dois na parte 3, um na
  parte 4 — e os P2. As condições do GA os declaram ABERTOS, pela forma, numa seção que o GA
  acrescenta, sem prometer versão para a cura deles. Um P2 da parte 1 que dependia de a tag do GA
  ainda não existir (um exemplo de documentação que pede `--pin v1.4.2` durante o hold) perde o
  objeto com o próprio GA.
- **Kit.** `run-ga-repass.sh`, `probe-conditions-ga.py`, `CONDITIONS-ga.md`, este README, o
  `.gitignore`, `gen-envelope-ga.py`, `OWNER-GA-CUT.sh` e `test-ga-kit.sh` são DERIVADOS do kit
  que cortou a rc.1 (as saídas de `derive-kit-142.py`) por `derive-ga-kit-142.py` — âncoras
  exatas, fontes pinadas por sha256, `--check` compara o disco com a derivação —, com as
  transformações rc → GA que `PLAN-192/derive-ga-kit-141.py` aplicou na v1.4.1. O que muda, por
  classe: a moldura GA do prompt e a conferência por parte com o candidato da rc.1; nas condições,
  o cabeçalho, os adopters do GA, as referências re-ancoradas (na rc.1 quando falam do passado, no
  escopo do GA quando falam do escopo) e a seção com o anexo assinado da rc.1; na sonda, as
  conferências da promoção; `--stable` com bump no-op obrigatório; no G0, o hold e o
  congelamento; publish REAL no npm com o Release em draft até o registry confirmar; a edição do
  Release por uma rotina que, num erro de transporte do `gh`, relê o estado antes de re-tentar (a
  parada do passo 18 do GA v1.4.1); e a morte pelo limite de uso da CONTA Codex separada da
  capacidade do modelo. A lista exaustiva são as âncoras do derivador.
- **Re-pass antes da cerimônia (pré-run).** O CEO pode rodar o runner antes do
  `OWNER-GA-CUT.sh`, ainda durante o hold. Pré-condições: o kit do GA commitado e pushado (o runner
  roda a sonda de dentro do worktree do candidato, e o G0 exige o kit commitado e idêntico ao
  HEAD), o CI verde no HEAD e HEAD == `origin/main` (o runner recusa outro candidato). Então
  `git rev-parse HEAD > .claude/plans/PLAN-193/repass-ga/CANDIDATE.sha` e, em segundo plano, com a
  saída num log FORA do repositório,
  `GA_CODEX_JOBS=4 bash .claude/plans/PLAN-193/repass-ga/run-ga-repass.sh` (as quatro partes
  correm juntas; cada uma leva ~10–45 min). O passo 5 mantém esse `CANDIDATE.sha` byte a byte
  quando ele aponta o mesmo commit, e o passo 6 reconhece a evidência completa e não re-roda.
  Depois do pré-run nada landa em `main` até o corte: um commit novo muda o candidato do passo 5,
  e a evidência do pré-run deixa de servir (o runner recusa rodar sobre ela; arquive-a, abaixo). O
  log fica fora porque o passo 15 recusa arquivo não rastreado, e o `.gitignore` de `repass-ga/`
  cobre só os arquivos de trabalho do runner.
- **Codex, no terminal que roda o runner.** (a) O `codex` global na versão que o manifesto ADR-182
  pina — `0.156.1` nesta release; confira com `codex --version`. Com ele o runner usa o binário
  global, com o payload verificado contra o manifesto antes de executar; outra versão global faz o
  runner cair no `npx`, num cache próprio e com rede (§7). Não suba o codex global antes do corte:
  o re-pin para `0.158.0` fica para depois do GA (LEDGER do PLAN-193). (b) `unset OPENAI_API_KEY`
  nesse terminal: o re-pass autentica o codex pela CONTA (o login em `~/.codex/auth.json`); com
  a chave no ambiente o G0 do corte avisa, e o passo 6, se tiver de rodar o re-pass, para
  pedindo Enter. (c) Cota folgada na conta Codex: as quatro partes
  gastam cota da conta. Numa tentativa do pré-run do GA v1.4.1 (2026-09-25), duas das três partes
  morreram pelo LIMITE DE USO DA CONTA (não pela capacidade do modelo), sem veredito; o re-pass
  que serviu ao corte do GA v1.4.1 foi outro, de 2026-09-28 (LEDGER do PLAN-192). O runner do GA
  separa as duas mortes: a do limite da conta não é re-tentada e sai nomeada, com a hora de reset
  quando o codex a imprime.
- **Critério de parada do GA (proposto por este kit, fixado ANTES da 1.ª rodada do GA): rodada
  final com anexo.** `NO-GO` só por P0 ou por condição declarada FALSA contra o código; um P1 não
  declarado vai para «NEW FINDINGS (annex)» e entra no material assinado. É uma rodada: uma `NO-GO`
  (a linha `VERDICT: NO-GO` em algum veredito) ⇒ parar, arquivar a tentativa e levar ao Owner; não
  há 2.ª rodada do GA por conta própria. Uma condição FALSA contra o código não chega ao codex: a
  sonda a recusa no G0, no passo 5 e no runner, e também vai ao Owner.
- **Arquivo das tentativas, FORA do repositório.** Toda tentativa, completa ou parcial, vai para
  um diretório NOVO em `$HOME/.ceo-ga-archive/`: o G0 recusa arquivo não rastreado no plano fora da
  evidência deste corte, e o runner recusa rodar sobre evidência anterior. Vão para lá os arquivos
  NÃO rastreados de `repass-ga/` (`git status --porcelain --untracked-files=all --
  .claude/plans/PLAN-193/repass-ga/`), menos o `CANDIDATE.sha`, que fica (copie-o); o runner, a
  sonda, as condições, este README e o `.gitignore` são rastreados e ficam. Uma `NO-GO` vai para
  `repass-ga-<data>-NOGO-r1/`, com o `.cut-state` junto (ignorado pelo git; sem ele a próxima
  tentativa recomeça do passo 1). Sem `NO-GO` e com parte sem veredito, a tentativa morta não é
  rodada: `-capacidade/` (capacidade do modelo que sobrou das re-tentativas do runner; a
  PROVENANCE diz), `-cota/` (o limite de uso da conta Codex; a nova tentativa espera a hora de
  reset, e o Owner decide quando) ou `-infra/` (rede, `npx`, `git`, `gpg`, a sonda sem medida; o
  runner morto antes do codex) — mantenha o `CANDIDATE.sha` e o `.cut-state` e re-rode (o
  `OWNER-GA-CUT.sh` retoma do passo 6; no pré-run, o próprio runner). Em 2026-09-29
  `$HOME/.ceo-ga-archive/` já guardava a tentativa morta do GA v1.4.1 (PLAN-192): o closeout deste
  corte leva ao PLAN-193 só os diretórios deste corte.
- **Closeout, depois do corte (nunca durante o freeze).** Entram no plano os diretórios arquivados
  deste corte (sem o `.cut-state`) e o `repass-ga/.tag-push-epoch` que o passo 16 grava (o piso do
  passo 19): o git não o ignora, e até o closeout o G0 de um corte seguinte o recusa pelo nome,
  com a rota.
- **O que segue (§1–§9) é o texto da rc.1**, mantido porque descreve o mesmo escopo e a mesma
  medição, com os nomes de arquivo do kit do GA. Onde ele fala do candidato, do bump, da base ou
  da primeira revisão cruzada, está re-ancorado na rc.1; o que o GA acrescenta está nas §3, §4, §6
  e §9; a §7 diz a ordem real da verificação na rota do `npx` (o pacote resolvido roda uma vez
  antes do oráculo), que o texto da rc.1 dizia «antes de executar» nas duas rotas; e o critério
  de parada da §5 é o da rc.1 (o do GA é o de cima).

## 1. O que é esta release

Release EXPRESSA sobre o GA v1.4.1 (PLAN-193): Claude Opus 5.5 como modelo de sessão fixado (o
Opus 5 segue no conjunto de trabalho e como fallback), a política de esforço (instalação nova em
`xhigh`; quem sobe do pin `claude-opus-5` sem esforço definido fica em `high`), o Claude Code
2.1.280 como mínimo, o
adapter live com a lista FECHADA de legados, a cura do FN-04 (o ledger do hook da tool `Workflow`
não grava mais os bytes de um `scriptPath` antes da decisão de permissão — o caso da condição 23
do GA v1.4.1; a classe dela segue declarada, não provada esgotada), a publicação do `relaunch --out`
por `link` sem substituir, o re-pin do Codex 0.156.1 e três CLIs novas. O candidato da rc.1 foi o
commit do bump (`release: v1.4.2`, `9b5b1b40`), sobre os lands da esteira da S357 (a ordem
está no LEDGER do PLAN-193); o GA revisa o mesmo conteúdo nas quatro partes (§0).

Nenhum tamanho é digitado aqui: a sonda das condições (`--sizes`) projeta cada parte com as
funções do PRÓPRIO runner — pathspec, rótulo, cobertura e cabeçalho do prompt — e recusa, no G0
do `OWNER-GA-CUT.sh`, no passo 5 e no runner, uma parte acima de `MAX_RAW_BYTES - 16 KiB`
(o teto do redator é 262.144 bytes sobre o INPUT; o runner recusa a partir de 262.000).

## 2. As quatro partes, na ordem de risco para o adopter

| parte | o que é | por que nesta ordem |
|---|---|---|
| 1 | `templates/**`, `.claude/settings.json`, `.claude/agents/**`, `scripts/**` fora de `scripts/local/` e `scripts/tests/`, `.claude/hooks/_lib/agent_frontmatter.py`, `.claude/hooks/_lib/effective_config.py`, `.claude/scripts/env-inventory.json`, o texto de release (`CHANGELOG.md`, `INSTALL.md`, `SUPPORT.md`, `README*.md`, `npm/**`) e os sítios de versão do bump | é o que decide com que modelo, esforço e hooks a sessão do adopter abre, e por onde a instalação e o upgrade chegam lá |
| 2 | `.claude/hooks/**` fora dos testes e dos dois arquivos da parte 1 (o adapter live, o `audit_log`, o hook da tool `Workflow` e o ledger, e a camada de isolamento da suíte pytest, `_lib/test_isolation.py`), `.claude/scripts/ceo-launches.py` e `docs/workflow-recovery.md` | é o código que RODA na sessão do adopter, e a recuperação que a mensagem de bloqueio nomeia; a camada de isolamento vai junto por estar sob `.claude/hooks/` (o Eixo 4 dela põe um `claude` FALSO no PATH da suíte) |
| 3 | `.claude/scripts/**` fora dos testes, de `local/`, de `data/` e dos arquivos das outras partes; `.claude/commands/**`, `.claude/skills/**` e `docs/**` fora de `docs/research/` e dos docs das partes 2 e 4 | ferramentas, comandos e documentação: a maior parte roda quando o operador a chama, e algumas rodam também chamadas por um hook ou pelo CI entregue ao adopter; nenhum destes arquivos é hook, instalação, upgrade ou settings (partes 1 e 2) |
| 4 | `.claude/scripts/re-pin-codex.py`, `docs/adopter-new-model-fast-access.md` e `docs/substrate-adopt-2026-09.md` | o gerador do pack de re-pin do Codex e os dois docs da adoção de substrato e de modelo novo; separados da parte 3 pelo tamanho |

### O manifesto de cada parte é DERIVADO, nunca uma lista fixa

A pathspec acima é a INTENÇÃO; `paths-ga-N.manifest.txt` é derivado dela contra o candidato no
momento do run (`git diff --name-only --no-renames v1.4.1..candidato -- <pathspec>`, com as
exclusões da própria pathspec). Os sítios de versão mudaram no commit do bump da
rc.1 (`9b5b1b40`), dentro de `v1.4.1..candidato`; no GA o bump é no-op (passo 2 do
`OWNER-GA-CUT.sh`) e não há commit de bump. Derivar contra o candidato pega o que uma lista
medida antes esqueceria. As partes são disjuntas, e todo caminho da
faixa fora delas cai numa classe da §4 — a sonda confere as duas coisas com as funções do runner
(`part_pathspec` e `out_of_scope_pathspec`).

## 3. Cobertura anterior, citada dentro do próprio prompt

- Parte 1: a wave-opus55 (ADR-149 Amendment 3 — pin, lista de modelos, esforço, migração de
  settings do `upgrade.sh` com a rotina única do comando de re-execução, e o piso de versão do
  Claude Code) landou sob cerimônia assinada pelo Owner, com rail codex próprio sobre o patch
  inteiro dela. Os demais arquivos landaram livres, com testes; a rodada 1 do re-pass da rc.1 foi
  a primeira revisão cruzada deles numa release. Os sítios de versão são escritos pelo
  `release.sh bump` e não têm rail próprio.
- Parte 2: o hook e o ledger vêm da PLAN-190 W1 (seis rodadas de pair-rail) e dos re-pass da
  v1.4.1-rc.1 e do GA v1.4.1; a cura do FN-04 landou sob cerimônia assinada, com rail codex
  próprio; a mudança do adapter, a do `audit_log` e o Eixo 4 do `_lib/test_isolation.py` landaram
  na cerimônia assinada da wave-opus55, com rail codex próprio sobre o patch inteiro dela; a
  publicação do `relaunch --out` landou livre, com testes (o `ceo-launches.py` e o
  `docs/workflow-recovery.md` mudam também no patch do FN-04).
- Parte 3: os arquivos que o patch da wave-opus55 muda landaram naquela cerimônia assinada (rail
  codex próprio sobre o patch inteiro dela); os demais landaram livres, com testes; a rodada 1
  do re-pass da rc.1 foi a primeira revisão cruzada deles numa release.
- Parte 4: landou livre (o gerador com testes); a rodada 1 do re-pass da rc.1 foi a primeira
  revisão cruzada dela numa release.
- No GA, as quatro partes: a rodada 1 do re-pass da rc.1, sobre este mesmo conteúdo (§0), deu
  `GO-WITH-CONDITIONS` em cada uma — sem P1 novo nas partes 1 e 2, dois na parte 3 e um na
  parte 4, no anexo assinado dela.

## 4. O que fica FORA, e por quê

| fora | motivo |
|---|---|
| testes, fixtures e harnesses de teste (`**/tests/**`) | não são entregues como produto; são o oráculo, e o oráculo roda no CI do candidato. Nesta faixa, entre eles os harnesses shell que nomeiam um instalador, que ganham o bloco `harness-claude-stub` da wave-opus55 (uma função `claude` exportada que responde `--version` com o piso do `scripts/install.sh` do próprio checkout) |
| `.claude/plans/**`, `docs/research/**` | registro de trabalho; não são entregues |
| `CLAUDE.md` | contrato de operação DESTE repositório; o adopter recebe `templates/CLAUDE.md` (parte 1, se mudar) |
| `.claude/governance/**` | nesta faixa: os dois arquivos de pin do Codex (re-pin 0.156.1, cerimônia assinada própria em `PLAN-193/codex-pin-0156/`) e o manifesto ADR-192 dos gates (muda com os gates que as cerimônias tocam); no GA, também o envelope assinado da rc.1 (`pair-rail-verdict-v1.4.2-rc.1.md`), material de release que o `install.sh` e o `upgrade.sh` não copiam para o alvo (§0) |
| `.claude/scripts/local/**` | nesta faixa, só o `release.sh`, que muda na relmeta-142, cerimônia assinada própria: o bloco por-release e o probe de assinatura do `preflight` (o `gpg` com `--yes`); o `upgrade.sh` o entrega a adopters (a condição 15 do envelope do GA v1.4.1 o declara, com a divergência instalação × upgrade aberta); engenharia de release |
| `.claude/adr/**` | texto de decisão; a Amendment 3 da ADR-149 viaja na cerimônia da wave-opus55, e a ADR-149 é a fonte das listas de modelos que `generate-available-models.py --check` confere contra os settings |
| `.claude/data/**`, `.claude/scripts/data/**` | dados de oráculo (reds esperados, baseline do censo do instalador) |
| `scripts/local/**` | harness de smoke do mantenedor; nesta faixa, só o `smoke-install-parity.sh`, que ganha o mesmo bloco `harness-claude-stub` |

## 5. Critério de parada da rc.1 (histórico — o do GA está na §0)

O texto abaixo é o critério que valeu para o re-pass da rc.1. O do GA, fixado antes da 1.ª
rodada do GA, está na §0: uma rodada, a final, e uma `NO-GO` volta ao Owner.

- `NO-GO` só por condição declarada FALSA contra o código ou por P0. Um P1 não declarado vai para
  «NEW FINDINGS (annex)» e entra no material assinado.
- No máximo DUAS rodadas de re-pass. Se a 2.ª ainda der `NO-GO`, PARAR e levar as duas ao Owner.
  Não há 3.ª rodada por conta própria. Bastou uma: a rodada 1 deu `GO-WITH-CONDITIONS` nas
  quatro partes.
- Uma condição FALSA contra o código não chega ao codex: a sonda a recusa no G0, no passo 5 e no
  runner. A cura é no código ou no texto (`derive-kit-142.py`), com um candidato novo.
- Uma parte morta por capacidade do modelo (sem veredito, com a assinatura do servidor no
  transcript) NÃO é uma rodada: o runner a re-tenta até 2 vezes e a PROVENANCE declara quantas
  mortes houve. Um runner morto por infraestrutura também não é rodada.
- Toda tentativa, completa ou parcial, é preservada — e FORA do repositório: o G0 recusa arquivo
  não rastreado no plano fora da evidência deste corte, e o runner recusa rodar sobre evidência
  anterior. Na rc.1 a rota era um diretório novo em
  `$HOME/.ceo-rc1-archive/` (`repass-rc1-<data>-NOGO-rN/`, ou `-capacidade/` / `-infra/`), com o
  `.cut-state` junto só no NO-GO. No GA vale a §0 (`$HOME/.ceo-ga-archive/`).
- O passo 16 da rc.1 gravou `repass-rc1/.tag-push-epoch` (o piso do passo 19), que o git não
  ignora; ele entrou no plano no closeout da rc.1 (`b20f8a6c`). O do GA segue a §0.

## 6. As condições declaradas

`CONDITIONS-ga.md`, neste diretório. Elas viajam em TODAS as partes como DADO para o revisor, e o
snapshot bruto que ele viu (`CONDITIONS-ga.reviewed.md`) é o que entra nos fields assinados —
mudar uma vírgula depois da revisão exige novo re-pass. A dívida carregada (o anexo P1 da v1.4.0
e o que o GA v1.4.1 declarou aberto) está re-declarada nas condições 1 e 2. No GA, o anexo
assinado da rc.1 (os três P1 e os P2 dos vereditos dela) está declarado ABERTO, pela forma,
numa seção que o GA acrescenta às condições da rc.1.

## 7. Codex pinado, sem tocar na máquina

O runner lê a versão de `.claude/governance/codex-cli-pin-manifest.json` no momento do run (a
0.156.1, depois do re-pin) e tem duas rotas: o binário global, quando ele é a versão pinada;
senão `@openai/codex@<versão>` resolvido por `npx` num cache próprio (`.npx-cache/`, ignorado pelo
git). Nas duas o sha256 do payload nativo é verificado contra o manifesto pelo mesmo oráculo do
pair-rail-gate (`check_pair_rail.py --verify-codex-pin`, fail-CLOSED) antes de qualquer revisão,
e um shim vai no início do PATH. A ordem difere entre as rotas: na global o payload é verificado
ANTES de executar; na do npx o pacote resolvido já roda uma vez (`npx -y <pacote> --version`, para
achar a versão e materializar o launcher) antes da verificação. A PROVENANCE registra a rota usada.
O modelo vai por `-m`, lido da tabela raiz de `~/.codex/config.toml` ou de `CODEX_MODEL`, e a
PROVENANCE registra o valor e a origem.

## 8. A base e o candidato

A base é a tag `v1.4.1`, o GA anterior (tag assinada em 2026-09-28): o runner e o G0 a RESOLVEM
(tag anotada; assinatura verificada, com o signatário em `.claude/sentinel-signers.txt`; o mesmo
objeto no remoto; ancestral do candidato) e recusam pelo nome quando ela não existe. O candidato
é o HEAD de `origin/main` gravado em `CANDIDATE.sha` depois do CI verde — pelo passo 5 do
`OWNER-GA-CUT.sh`, ou pelo CEO quando ele roda o re-pass antes da cerimônia (§0; o passo 6
reconhece a evidência completa e não re-roda). Na rc.1 era o commit do bump (`release: v1.4.2`,
`9b5b1b40`); no GA o bump é no-op e não há commit de bump: o candidato é o HEAD de um `main` que,
desde a tag da rc.1, só recebeu `CLAUDE.md` e planos numerados (§0). O runner nunca lê o
candidato de uma constante, e o commit do veredito senta DIRETAMENTE sobre o candidato:
`parent_sha` == pai do commit que introduz o veredito.

## 9. A sonda das condições

`probe-conditions-ga.py` confere cada afirmação sobre código das condições contra um commit:
arquivos e textos pelo conteúdo do commit (`git show`), comportamentos rodando o código do
checkout — o hook da tool `Workflow` num PreToolUse e num PostToolUse com um `scriptPath`
canário (condição 3), a publicação do `relaunch --out` num diretório temporário (condição 4), o
passo de migração de settings do `upgrade.sh` sobre os settings que o template `base` da v1.4.1
entregou, com e sem o opt-in, e sobre um `settings.json` ilegível (condição 6), o piso do Claude
Code com um `claude` FALSO no PATH, e sem nenhum (condição 7), e a classificação do adapter
(condição 8). No GA ela confere também a promoção: cada parte com a mesma árvore do candidato da
rc.1, o envelope assinado da rc.1 no commit, as formas dos P1 do anexo da rc.1 ainda presentes
(as condições os declaram abertos: uma forma que sumiu tornaria a condição falsa), o
`npm-publish.yml` publicando só as tags sem `-rc.`, o shim do npm rodando o `install.sh` e a
versão `1.4.2` em `.claude/.framework-version` e `npm/package.json`. Roda no G0 (contra o HEAD), no
passo 5 e no runner (contra o candidato), e a saída do runner entra no MANIFEST (`probe-ga.txt`).
`GA_PROBE_REPORT_ONLY=1` existe só para o harness: o corte e o runner seguem, a PROVENANCE declara
a sonda vermelha e o gerador do envelope recusa essa evidência.
