<!-- Material do kit de corte da v1.4.2-rc.1 (PLAN-193). Este arquivo é rastreado ANTES do
     candidato e não muda no commit do veredito: o guard de delta o recusaria por nome. -->

# Re-pass do candidato v1.4.2-rc.1 — escopo, o que fica de fora e critério de parada

## 1. O que é esta release

Release EXPRESSA sobre o GA v1.4.1 (PLAN-193): Claude Opus 5.5 como modelo de sessão fixado (o
Opus 5 segue no conjunto de trabalho e como fallback), a política de esforço (instalação nova em
`xhigh`; quem sobe do pin `claude-opus-5` sem esforço definido fica em `high`), o Claude Code
2.1.280 como mínimo, o
adapter live com a lista FECHADA de legados, a cura do FN-04 (o ledger do hook da tool `Workflow`
não grava mais os bytes de um `scriptPath` antes da decisão de permissão — o caso da condição 23
do GA v1.4.1; a classe dela segue declarada, não provada esgotada), a publicação do `relaunch --out`
por `link` sem substituir, o re-pin do Codex 0.156.1 e três CLIs novas. O candidato é o commit do
bump, sobre os lands da manhã (a ordem está no LEDGER do PLAN-193).

Nenhum tamanho é digitado aqui: a sonda das condições (`--sizes`) projeta cada parte com as
funções do PRÓPRIO runner — pathspec, rótulo, cobertura e cabeçalho do prompt — e recusa, no G0
do `OWNER-RC1-CUT.sh`, no passo 5 e no runner, uma parte acima de `MAX_RAW_BYTES - 16 KiB`
(o teto do redator é 262.144 bytes sobre o INPUT; o runner recusa a partir de 262.000).

## 2. As quatro partes, na ordem de risco para o adopter

| parte | o que é | por que nesta ordem |
|---|---|---|
| 1 | `templates/**`, `.claude/settings.json`, `.claude/agents/**`, `scripts/**` fora de `scripts/local/` e `scripts/tests/`, `.claude/hooks/_lib/agent_frontmatter.py`, `.claude/hooks/_lib/effective_config.py`, `.claude/scripts/env-inventory.json`, o texto de release (`CHANGELOG.md`, `INSTALL.md`, `SUPPORT.md`, `README*.md`, `npm/**`) e os sítios de versão do bump | é o que decide com que modelo, esforço e hooks a sessão do adopter abre, e por onde a instalação e o upgrade chegam lá |
| 2 | `.claude/hooks/**` fora dos testes e dos dois arquivos da parte 1 (o adapter live, o `audit_log`, o hook da tool `Workflow` e o ledger, e a camada de isolamento da suíte pytest, `_lib/test_isolation.py`), `.claude/scripts/ceo-launches.py` e `docs/workflow-recovery.md` | é o código que RODA na sessão do adopter, e a recuperação que a mensagem de bloqueio nomeia; a camada de isolamento vai junto por estar sob `.claude/hooks/` (o Eixo 4 dela põe um `claude` FALSO no PATH da suíte) |
| 3 | `.claude/scripts/**` fora dos testes, de `local/`, de `data/` e dos arquivos das outras partes; `.claude/commands/**`, `.claude/skills/**` e `docs/**` fora de `docs/research/` e dos docs das partes 2 e 4 | ferramentas, comandos e documentação: a maior parte roda quando o operador a chama, e algumas rodam também chamadas por um hook ou pelo CI entregue ao adopter; nenhum destes arquivos é hook, instalação, upgrade ou settings (partes 1 e 2) |
| 4 | `.claude/scripts/re-pin-codex.py`, `docs/adopter-new-model-fast-access.md` e `docs/substrate-adopt-2026-09.md` | o gerador do pack de re-pin do Codex e os dois docs da adoção de substrato e de modelo novo; separados da parte 3 pelo tamanho |

### O manifesto de cada parte é DERIVADO, nunca uma lista fixa

A pathspec acima é a INTENÇÃO; `paths-rc1-N.manifest.txt` é derivado dela contra o candidato no
momento do run (`git diff --name-only --no-renames v1.4.1..candidato -- <pathspec>`, com as
exclusões da própria pathspec). Os sítios de versão só mudam no commit do bump, que é o candidato:
uma lista medida antes esqueceria exatamente eles. As partes são disjuntas, e todo caminho da
faixa fora delas cai numa classe da §4 — a sonda confere as duas coisas com as funções do runner
(`part_pathspec` e `out_of_scope_pathspec`).

## 3. Cobertura anterior, citada dentro do próprio prompt

- Parte 1: a wave-opus55 (ADR-149 Amendment 3 — pin, lista de modelos, esforço, migração de
  settings do `upgrade.sh` com a rotina única do comando de re-execução, e o piso de versão do
  Claude Code) landou sob cerimônia assinada pelo Owner, com rail codex próprio sobre o patch
  inteiro dela. Os demais arquivos landaram livres, com testes; esta é a primeira revisão cruzada
  deles numa release. Os sítios de versão são escritos pelo `release.sh bump` e não têm rail
  próprio.
- Parte 2: o hook e o ledger vêm da PLAN-190 W1 (seis rodadas de pair-rail) e dos re-pass da
  v1.4.1-rc.1 e do GA v1.4.1; a cura do FN-04 landou sob cerimônia assinada, com rail codex
  próprio; a mudança do adapter, a do `audit_log` e o Eixo 4 do `_lib/test_isolation.py` landaram
  na cerimônia assinada da wave-opus55, com rail codex próprio sobre o patch inteiro dela; a
  publicação do `relaunch --out` landou livre, com testes (o `ceo-launches.py` e o
  `docs/workflow-recovery.md` mudam também no patch do FN-04).
- Parte 3: os arquivos que o patch da wave-opus55 muda landaram naquela cerimônia assinada (rail
  codex próprio sobre o patch inteiro dela); os demais landaram livres, com testes; esta é a
  primeira revisão cruzada deles numa release.
- Parte 4: landou livre (o gerador com testes); esta é a primeira revisão cruzada dela numa
  release.

## 4. O que fica FORA, e por quê

| fora | motivo |
|---|---|
| testes, fixtures e harnesses de teste (`**/tests/**`) | não são entregues como produto; são o oráculo, e o oráculo roda no CI do candidato. Nesta faixa, entre eles os harnesses shell que nomeiam um instalador, que ganham o bloco `harness-claude-stub` da wave-opus55 (uma função `claude` exportada que responde `--version` com o piso do `scripts/install.sh` do próprio checkout) |
| `.claude/plans/**`, `docs/research/**` | registro de trabalho; não são entregues |
| `CLAUDE.md` | contrato de operação DESTE repositório; o adopter recebe `templates/CLAUDE.md` (parte 1, se mudar) |
| `.claude/governance/**` | nesta faixa: os dois arquivos de pin do Codex (re-pin 0.156.1, cerimônia assinada própria em `PLAN-193/codex-pin-0156/`) e o manifesto ADR-192 dos gates (muda com os gates que as cerimônias tocam) |
| `.claude/scripts/local/**` | nesta faixa, só o `release.sh`, que muda na relmeta-142, cerimônia assinada própria: o bloco por-release e o probe de assinatura do `preflight` (o `gpg` com `--yes`); o `upgrade.sh` o entrega a adopters (a condição 15 do envelope do GA v1.4.1 o declara, com a divergência instalação × upgrade aberta); engenharia de release |
| `.claude/adr/**` | texto de decisão; a Amendment 3 da ADR-149 viaja na cerimônia da wave-opus55, e a ADR-149 é a fonte das listas de modelos que `generate-available-models.py --check` confere contra os settings |
| `.claude/data/**`, `.claude/scripts/data/**` | dados de oráculo (reds esperados, baseline do censo do instalador) |
| `scripts/local/**` | harness de smoke do mantenedor; nesta faixa, só o `smoke-install-parity.sh`, que ganha o mesmo bloco `harness-claude-stub` |

## 5. Critério de parada (proposto por este kit, fixado ANTES da 1.ª rodada)

- `NO-GO` só por condição declarada FALSA contra o código ou por P0. Um P1 não declarado vai para
  «NEW FINDINGS (annex)» e entra no material assinado.
- No máximo DUAS rodadas de re-pass. Se a 2.ª ainda der `NO-GO`, PARAR e levar as duas ao Owner.
  Não há 3.ª rodada por conta própria.
- Uma condição FALSA contra o código não chega ao codex: a sonda a recusa no G0, no passo 5 e no
  runner. A cura é no código ou no texto (`derive-kit-142.py`), com um candidato novo.
- Uma parte morta por capacidade do modelo (sem veredito, com a assinatura do servidor no
  transcript) NÃO é uma rodada: o runner a re-tenta até 2 vezes e a PROVENANCE declara quantas
  mortes houve. Um runner morto por infraestrutura também não é rodada.
- Toda tentativa, completa ou parcial, é preservada — e FORA do repositório: o G0 recusa arquivo
  não rastreado no plano fora da evidência deste corte, e o runner recusa rodar sobre evidência
  anterior. O passo 6 do `OWNER-RC1-CUT.sh` diz a rota: um diretório novo em
  `$HOME/.ceo-rc1-archive/` (`repass-rc1-<data>-NOGO-rN/`, ou `-capacidade/` / `-infra/`), com o
  `.cut-state` junto só no NO-GO. O diretório arquivado entra no plano no closeout, depois do corte.
- O passo 16 grava `repass-rc1/.tag-push-epoch` (o piso do passo 19), que o git não ignora: ele
  entra no plano no mesmo closeout (como o do corte da v1.4.1-rc.1). Até lá, o G0 de um corte
  seguinte o recusa pelo nome, com a rota.

## 6. As condições declaradas

`CONDITIONS-rc1.md`, neste diretório. Elas viajam em TODAS as partes como DADO para o revisor, e o
snapshot bruto que ele viu (`CONDITIONS-rc1.reviewed.md`) é o que entra nos fields assinados —
mudar uma vírgula depois da revisão exige novo re-pass. A dívida carregada (o anexo P1 da v1.4.0
e o que o GA v1.4.1 declarou aberto) está re-declarada nas condições 1 e 2.

## 7. Codex pinado, sem tocar na máquina

O runner lê a versão de `.claude/governance/codex-cli-pin-manifest.json` no momento do run (a
0.156.1, depois do re-pin) e tem duas rotas: o binário global, quando ele é a versão pinada;
senão `@openai/codex@<versão>` resolvido por `npx` num cache próprio (`.npx-cache/`, ignorado pelo
git). Nas duas o sha256 do payload nativo é verificado contra o manifesto pelo mesmo oráculo do
pair-rail-gate (`check_pair_rail.py --verify-codex-pin`, fail-CLOSED) ANTES de executar, e um
shim vai no início do PATH. A PROVENANCE registra a rota usada. O modelo vai por `-m`, lido da
tabela raiz de `~/.codex/config.toml` ou de `CODEX_MODEL`, e a PROVENANCE registra o valor e a
origem.

## 8. A base e o candidato

A base é a tag `v1.4.1`, cortada na mesma manhã: o runner e o G0 a RESOLVEM (tag anotada;
assinatura verificada, com o signatário em `.claude/sentinel-signers.txt`; o mesmo objeto no
remoto; ancestral do candidato) e recusam pelo nome quando ela não existe. O candidato é o HEAD de
`origin/main` gravado em `CANDIDATE.sha` depois do CI verde — o commit do bump (`release: v1.4.2`),
pelo passo 5 do `OWNER-RC1-CUT.sh`, ou pelo CEO quando ele roda o re-pass antes da cerimônia (o
passo 6 reconhece a evidência completa e não re-roda). O runner nunca lê o candidato de uma
constante, e o commit do veredito senta DIRETAMENTE sobre o candidato: `parent_sha` == pai do
commit que introduz o veredito.

## 9. A sonda das condições

`probe-conditions-rc1.py` confere cada afirmação sobre código das condições contra um commit:
arquivos e textos pelo conteúdo do commit (`git show`), comportamentos rodando o código do
checkout — o hook da tool `Workflow` num PreToolUse e num PostToolUse com um `scriptPath`
canário (condição 3), a publicação do `relaunch --out` num diretório temporário (condição 4), o
passo de migração de settings do `upgrade.sh` sobre os settings que o template `base` da v1.4.1
entregou, com e sem o opt-in, e sobre um `settings.json` ilegível (condição 6), o piso do Claude
Code com um `claude` FALSO no PATH, e sem nenhum (condição 7), e a classificação do adapter
(condição 8). Roda no G0 (contra o HEAD), no passo 5 e no runner
(contra o candidato), e a saída do runner entra no MANIFEST (`probe-rc1.txt`). `RC1_PROBE_REPORT_ONLY=1`
existe só para o harness: o corte e o runner seguem, a PROVENANCE declara a sonda vermelha e o
gerador do envelope recusa essa evidência.
