<!-- Material do kit de corte da v1.4.3-rc.1 (PLAN-194). Este arquivo é rastreado ANTES do
     candidato e não muda no commit do veredito: o guard de delta o recusaria por nome. -->

# Re-pass do candidato v1.4.3-rc.1 — escopo, o que fica de fora e critério de parada

## 1. O que é esta release

Release de MANUTENÇÃO sobre o GA v1.4.2 (PLAN-194). O texto de release do candidato — o
`CHANGELOG.md` [1.4.3], com o Known-open, e o texto da tag — diz o que entra, e este kit o segue
pela forma: o gate de configuração do harness do `/ceo-boot` curado na cerimônia padrão (as
fixtures do replay num diretório que a instalação recebe); o gravador do `agent_spawn` sob uma
trava só, que aposenta a condição 67 da `v1.4.0-rc.1`; o `defaultMode` `manual` numa instalação
nova com `--ceremony user`; o bloqueio do envelope de custo gravado no log de auditoria; os nomes
de modelo do Codex e o ledger de deprecações; as correções de `audit-query.py`, `/status`,
`/ceo-boot` e `check-substrate-drift.py`; os verificadores só-leitura da auditoria; o re-pin do
Codex 0.160.0 (cerimônia própria); a prova do toolchain do npm nas tags `-rc.` (um job que nunca
publica); a rota de CI do próprio framework; as notas da verificação formal (o TLC); e as
demais mudanças que o `CHANGELOG.md` [1.4.3] lista como arquivos que chegam às instalações
(«Changed — other files that reach installs»), entre elas o `fsync` único no primeiro evento do
`_lib/spool_writer.py`, que chegou por um merge de pull request. O candidato é o commit do bump,
sobre os lands do trem (a ordem está no LEDGER do PLAN-194).

O plano do PLAN-194, o LEDGER dele e o backlog da 1.4.4 registram para onde foram os itens que
saíram do trem, entre eles: a cura do spool de auditoria e o estresse que a provaria (que o
`CHANGELOG.md` [1.4.3] declara não entregues); a adoção do Sonnet 5.5 e do Haiku 5.5; a
re-medição paga no Claude Code (W5.0) e o restante da W5a, que vão para a 1.4.4 (decisão
S365-1) — a primeira parte da W5a, os textos do `ultracode` e do esforço com data e substrato,
landou em `9770b5a4` e está no `CHANGELOG.md` [1.4.3]; a W6.2 e a documentação da W6; a emenda
W7ad; e o PLAN-195. A verificação formal canônica (W8 do plano) fica para depois do GA; o TLC
já roda nos três modelos, advisory, pelo merge de pull request cujo workflow uma cerimônia
assinada ratificou depois, pelos bytes.

Nenhum tamanho é digitado aqui: a sonda das condições (`--sizes`) projeta cada parte com as
funções do PRÓPRIO runner — pathspec, rótulo, cobertura e cabeçalho do prompt — e recusa, no G0
do `OWNER-RC1-CUT.sh`, no passo 5 e no runner, uma parte acima de `MAX_RAW_BYTES - 16 KiB`
(o teto do redator é 262.144 bytes sobre o INPUT; o runner recusa a partir de 262.000).

## 2. As quatro partes, na ordem de risco para o adopter

| parte | o que é | por que nesta ordem |
|---|---|---|
| 1 | `templates/**`, `.claude/settings.json`, `.claude/agents/**`, `scripts/**` fora de `scripts/local/`, `.claude/hooks/_lib/agent_frontmatter.py`, `.claude/hooks/_lib/effective_config.py`, `.claude/scripts/env-inventory.json`, `.github/**` (os workflows de CI e de release, com o job da prova do toolchain da rc), o texto de release (`CHANGELOG.md`, `INSTALL.md`, `SUPPORT.md`, `README*.md`, `npm/**`) e os sítios de versão do bump fora de `docs/` — sempre fora de `**/tests/**` | é o que decide com que modelo, esforço e hooks a sessão do adopter abre, por onde a instalação e o upgrade chegam lá, e o pipeline que publica o pacote que ele instala |
| 2 | `.claude/hooks/**` fora dos testes e dos dois arquivos da parte 1 | é o código que RODA na sessão do adopter (o `audit_log` e a cadeia de auditoria, os adapters, os auxiliares de `_lib/`) |
| 3 | `.claude/scripts/**` fora dos testes, de `local/`, de `data/` e do `env-inventory.json`; `.claude/commands/**` e `.claude/skills/**` | ferramentas e comandos: a maior parte roda quando o operador a chama, e algumas rodam também chamadas por um hook ou pelo CI entregue ao adopter; nenhum destes arquivos é hook, instalação, upgrade ou settings (partes 1 e 2) |
| 4 | `docs/**` fora de `docs/research/`, com os modelos e os scripts de `docs/formal-verification/` e o sítio de versão do bump em `docs/` (`docs/ARCHITECTURE.md`) | a documentação do repositório; separada da parte 3 pelo tamanho |

### O manifesto de cada parte é DERIVADO, nunca uma lista fixa

A pathspec acima é a INTENÇÃO; `paths-rc1-N.manifest.txt` é derivado dela contra o candidato no
momento do run (`git diff --name-only --no-renames v1.4.2..candidato -- <pathspec>`, com as
exclusões da própria pathspec). Os sítios de versão só mudam no commit do bump, que é o candidato:
uma lista medida antes esqueceria exatamente eles. As partes são disjuntas, e todo caminho da
faixa fora delas cai numa classe da §4 — a sonda confere as duas coisas com as funções do runner
(`part_pathspec` e `out_of_scope_pathspec`).

## 3. Cobertura anterior, citada dentro do próprio prompt

Pela forma, sem lista de lands: fora os sítios de versão, cada mudança de uma parte nesta faixa
chegou por um de três caminhos — uma cerimônia assinada pelo Owner, com rail próprio; um merge de
pull request de ramo `codex/…` sem a cerimônia, e desses só os canônicos foram ratificados depois
por sentinel assinado, pelos bytes (os demais não têm assinatura); ou um land livre, com testes.
Esta é a primeira revisão cruzada, numa release, dos que não passaram por rail. A classe dos
merges sem a cerimônia toca as quatro partes, e o `CHANGELOG.md` [1.4.3] a declara no Known-open.
Os sítios de versão (na parte 1 e, em `docs/`, na parte 4) são escritos pelo `release.sh bump` e
não têm rail próprio.

## 4. O que fica FORA, e por quê

Fora do re-pass não quer dizer não entregue: o que chega a um adopter é o que o `install.sh` e o `upgrade.sh` do candidato entregam, e este kit não o afirma classe a classe.

| fora | motivo |
|---|---|
| testes, fixtures e harnesses de teste (`**/tests/**`) | o oráculo, que roda no CI do candidato |
| `.claude/plans/**` | registro de trabalho |
| `docs/research/**` | registro de trabalho |
| `CLAUDE.md` | contrato de operação DESTE repositório |
| `.claude/governance/**` | nesta faixa, no máximo os dois arquivos de pin do Codex (re-pin 0.160.0, cerimônia assinada própria em `PLAN-194/codex-pin-0160/`), o manifesto ADR-192 dos gates (muda com os gates que as cerimônias tocam) e o comentário do publicador confiável do npm (`npm-trusted-publisher.txt`, mudado na cerimônia da W4) |
| `.claude/scripts/local/**` | nesta faixa, no máximo o `release.sh` (o bloco por-release, na cerimônia própria da relmeta); engenharia de release |
| `.claude/adr/**` | texto de decisão |
| `.claude/data/**` | dados de oráculo e de teste, entre eles os reds esperados e o mapa de preferência de modelos (inerte: hoje só um teste o lê) |
| `.claude/scripts/data/**` | dado de oráculo (o baseline do censo do instalador) |
| `scripts/local/**` | harness de smoke do mantenedor |
| `.claude/eval/**` | o harness de avaliação do framework |
| `conftest.py`, `pytest.ini` (da raiz) | a configuração de teste deste repositório (o oráculo) |
| `.gitignore` (da raiz) | higiene deste repositório |

## 5. Critério de parada (proposto por este kit, fixado ANTES da 1.ª rodada)

- `NO-GO` só por condição declarada FALSA contra o código ou por P0. Um P1 não declarado vai para
  «NEW FINDINGS (annex)» e entra no material assinado.
- No máximo DUAS rodadas de re-pass. Se a 2.ª ainda der `NO-GO`, PARAR e levar as duas ao Owner.
  Não há 3.ª rodada por conta própria.
- Uma condição FALSA contra o código não chega ao codex: a sonda a recusa no G0, no passo 5 e no
  runner. A cura é no código ou no texto (`derive-kit-143.py`), com um candidato novo.
- Uma parte morta por capacidade do modelo (sem veredito, com a assinatura do servidor numa linha
  `ERROR:` do próprio codex no fim do transcript) NÃO é uma rodada: o runner a re-tenta até 2
  vezes e a PROVENANCE declara quantas mortes houve. Uma parte morta pelo LIMITE DE USO da CONTA
  Codex também não é rodada: o runner não a re-tenta, não lança parte nova, a PROVENANCE a declara
  (com a hora de reset, quando o codex a imprime) e o passo 6 dá a rota. Um runner morto por
  infraestrutura também não é rodada.
- Toda tentativa, completa ou parcial, é preservada — e FORA do repositório: o G0 recusa arquivo
  não rastreado no plano fora da evidência deste corte, e o runner recusa rodar sobre evidência
  anterior. O passo 6 do `OWNER-RC1-CUT.sh` diz a rota: um diretório novo em
  `$HOME/.ceo-rc1-archive/` (`repass-rc1-<data>-NOGO-rN/`, ou `-capacidade/` / `-cota/` /
  `-infra/`), com o `.cut-state` junto só no NO-GO. O diretório arquivado entra no plano no
  closeout, depois do corte.
- O passo 16 grava `repass-rc1/.tag-push-epoch` (o piso do passo 19), que o git não ignora: ele
  entra no plano no mesmo closeout (como o do corte da v1.4.2-rc.1). Até lá, o G0 de um corte
  seguinte o recusa pelo nome, com a rota.

## 6. As condições declaradas

`CONDITIONS-rc1.md`, neste diretório. Elas viajam em TODAS as partes como DADO para o revisor, e o
snapshot bruto que ele viu (`CONDITIONS-rc1.reviewed.md`) é o que entra nos fields assinados —
mudar uma vírgula depois da revisão exige novo re-pass. A dívida carregada (o anexo P1 da v1.4.0
e o que o GA v1.4.2 declarou aberto) está re-declarada nas condições 1 e 2, cada uma com a
exceção do CASO que esta release declara curado (condições 3 e 4); as condições 5 a 8 dizem o que
muda para o adopter, e as 9 e 10 o escopo.

## 7. Codex pinado, sem tocar na máquina

O runner lê a versão de `.claude/governance/codex-cli-pin-manifest.json` no momento do run (a
0.160.0, depois do re-pin) e tem UMA rota nesta release (decisão D-4 do PLAN-194): o binário
global, quando o oráculo do pair-rail-gate (`check_pair_rail.py --verify-codex-pin`, fail-CLOSED)
confere o sha256 do payload nativo contra o manifesto SEM executá-lo — e só então ele responde a
versão pinada. A rota 2 da v1.4.2 (`npx` num cache próprio) executava o pacote baixado antes de
verificar; aqui ela é recusa nomeada, sem download nem execução, e a recusa diz a rota: o codex
pinado instalado globalmente. Um shim vai no início do PATH. A PROVENANCE registra a rota usada.
O modelo vai por `-m`, lido da tabela raiz de `~/.codex/config.toml` ou de `CODEX_MODEL`, e a
PROVENANCE registra o valor e a origem.

Resíduo, da forma que o Known-open do `CHANGELOG.md` [1.4.3] declara para o pin (ele não cobre o
lançador): o shim executa o `codex` global do PATH — no layout do npm, o lançador `codex.js` do
pacote —, e o oráculo hasheia o payload nativo que resolve a partir desse lançador, não o
lançador. É um resíduo de mesmo UID, e a cura não é desta release (condição 5).

## 8. A base e o candidato

A base é a tag `v1.4.2` (o GA, cortado em 2026-09-30): o runner e o G0 a RESOLVEM (tag anotada;
assinatura verificada, com o signatário em `.claude/sentinel-signers.txt`; o mesmo objeto no
remoto; ancestral do candidato) e recusam pelo nome quando ela não existe. O candidato é o HEAD de
`origin/main` gravado em `CANDIDATE.sha` depois do CI verde — o commit do bump (`release: v1.4.3`),
pelo passo 5 do `OWNER-RC1-CUT.sh`, ou pelo CEO quando ele roda o re-pass antes da cerimônia (o
passo 6 reconhece a evidência completa e não re-roda). O runner nunca lê o candidato de uma
constante, e o commit do veredito senta DIRETAMENTE sobre o candidato: `parent_sha` == pai do
commit que introduz o veredito.

## 9. A sonda das condições

`probe-conditions-rc1.py` confere cada afirmação sobre código das condições contra um commit,
pelo conteúdo do commit (`git show`) e, onde a afirmação é de comportamento, rodando o código do
candidato num diretório temporário: a dívida carregada pelos envelopes assinados da v1.4.2 e
pelos vereditos que eles pinam (condições 1 e 2); o CASO da condição 67 pela AST do gravador e o
texto do CHANGELOG (condições 1 e 3); o P2 da parte 3 do GA pelo cenário reproduzido (condições 2
e 4); o pin do Codex e a rota única do runner (condição 5); o job da prova do toolchain da rc e a
paridade de toolchain com o publish (condição 6); o exemplo de `--pin` do `INSTALL.md` contra o
`VERSION`, o `upgrade.sh` sem a tag e o adapter intacto (condições 7 e 8); a partição, com as
funções do próprio runner, e o tamanho de cada parte (condição 9); o escopo fora (condição 10);
e, no cabeçalho, a árvore, o npm e a ausência da marca
do conteúdo provisório do K1. Toda condição numerada tem ao menos uma verificação: o derivador
recusa uma condição sem id que não esteja na lista declarada só-texto (hoje vazia). Roda no G0
(contra o HEAD), no passo 5 e no runner (contra o candidato), e a saída do runner entra no
MANIFEST (`probe-rc1.txt`), com a linha MAPA que diz que ids conferem cada condição.
`RC1_PROBE_REPORT_ONLY=1` existe só para o harness: o corte e o runner seguem, a PROVENANCE
declara a sonda vermelha e o gerador do envelope recusa essa evidência.

## 10. Limites conhecidos deste kit

- O CI do candidato: o `wait_ci_green` do corte consulta os runs PELO COMMIT, com todos os
  eventos (agendados inclusive), até um teto de 200 runs por consulta. Entre os runs que a
  consulta devolve, ele recusa pelo nome um run vermelho e espera os pendentes até o teto de
  tempo (recusando pelo nome se não terminarem); e recusa pelo nome a consulta que volta no
  teto, porque ela não prova que não há vermelho nem pendente fora da janela. O preflight do
  `release.sh` (arquivo do manifesto ADR-192, cujo sha256 a relmeta re-pinou; o preflight não
  mudou nesta faixa) confere o CI do HEAD numa janela dos runs mais recentes do repositório,
  filtrada depois pelo commit: um vermelho do mesmo commit mais antigo que a janela não aparece
  ali. O kit não muda o `release.sh`.
