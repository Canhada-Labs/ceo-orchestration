# w5b-approved — sentinel da W5b do PLAN-194 (a instalação `--ceremony user` grava `permissions.defaultMode` "manual"; canônico `scripts/install.sh`)

Plan: PLAN-194
Wave: W5b — `scripts/install.sh`: a instalação `--ceremony user` grava `permissions.defaultMode` "manual" junto da deny-baseline (OQ-7, Q9)
Dados: .claude/plans/PLAN-194/w5b/sign.tsv
Molde: .claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh
Patch: .claude/plans/PLAN-194/w5b/w5b.patch
Patch-sha256: TO-FILL-BY-SIGN
Rail-Record-sha256: TO-FILL-BY-SIGN
Anchor-SHA: TO-FILL-BY-SIGN
Data: TO-FILL-BY-SIGN

## Ratificação (Owner)

- PLAN-194, item W5b (`PLAN-194-maintenance-train-v1-4-3.md`): «W5b — `defaultMode` na instalação
  `--ceremony user` (OQ-7, RESPONDIDA em 2026-10-01, Q9: gravar `"manual"`).» O item nomeia os 3 caminhos
  de código e teste (`scripts/install.sh`, `scripts/tests/test-install-deny-baseline.sh` e o baseline do
  censo de escrita do instalador, regenerado no MESMO patch) e o Check `bash
  scripts/tests/test-install-deny-baseline.sh`. O 4.º caminho, `docs/deny-baseline.md` (oráculo 0), entrou
  pela condição P2 da rodada 1 do rail (abaixo).
- OQ-7, respondida pelo Owner na S361 (Q9, 2026-10-01): «gravar `manual`; a W5b destrava.»
- Ordem de assinatura da S363: W4 → U2-A → U2-B → W5b (a W6.2 saiu para a 1.4.4). A W5b landa antes da
  W1a/W1b e da W8 do PLAN-183, que tocam o mesmo `install.sh` e o mesmo baseline (mapa de colisões do
  PLAN-194).
- Tamanho: 4 caminhos, 279 linhas (+196 −83), 1 canônico (`scripts/install.sh`), que NÃO é kernel: nenhum
  dos 4 caminhos está em `_KERNEL_PATHS` (`.claude/hooks/check_arbitration_kernel.py`).

## O que esta cerimônia entrega, e nada além

- `scripts/install.sh`, seção 6a (`apply_deny_baseline`): o MESMO merge da deny-baseline grava
  `permissions.defaultMode` = `DEFAULT_MODE_BASELINE` ("manual") quando o `settings.json` que ESTA
  execução produziu não tem a chave — no `jq`, `has("defaultMode")` (presença, não valor); no `python3`,
  `setdefault`. As mensagens MERGED, dry-run, WARNING e SKIP passam a nomear o `defaultMode`. Por caso:
  - `--ceremony user`: o template `templates/settings/settings.user.json` exclui o bloco `permissions`
    (`:66-67`), e a instalação passa a gravar `permissions.deny` (as 20 entradas da baseline) E
    `permissions.defaultMode: "manual"`. Antes do patch, só o `deny` (medido pelo construtor sobre
    `0a953ece`, instalação descartável: chaves de `permissions` = `['deny']`, 20 entradas);
  - instalação do mantenedor: o template `settings.base.json` já traz `"defaultMode": "manual"` (`:649`) e
    ele fica como está (perna F/maintainer do teste);
  - `settings.json` pré-existente: nunca é tocado (o skip `SETTINGS_PRE_EXISTING`, inalterado; a perna H
    planta `"acceptEdits"` e confere o arquivo byte a byte idêntico depois da instalação `user`).
- O `scripts/upgrade.sh` NÃO muda. Ele já gravava a chave num adopter sem ela:
  `_migrate_settings_baseline` (`upgrade.sh:3594`), linha `permissions.defaultMode` (`:3881-3890`, «SET
  (absent -> new baseline)»), sem portão de cerimônia — medido pelo construtor (upgrade sobre uma
  instalação `user` sem a chave: rc 0, resultado "manual") e conferido pelas duas lanes Claude da rodada
  1. O buraco era só a instalação nova. O teste lê o valor esperado do `upgrade.sh
  --print-settings-baselines` (campo `new` da linha `permissions.defaultMode`), nunca de um literal:
  instalação e upgrade não divergem sem a perna F ficar vermelha.
- `scripts/tests/test-install-deny-baseline.sh`: pernas novas F (`user`: escrito pelo ramo `jq`;
  mantenedor: o do template mantido), G (`user` com o `jq` escondido: escrito pelo ramo `python3`) e H
  (pré-existente com `"acceptEdits"`: byte a byte idêntico); as pernas A a E ficam como estavam.
- `.claude/scripts/data/installer-write-safety-baseline.txt`: regenerado com
  `check-installer-write-safety.py --write-baseline` no mesmo patch (regra do ratchet do PLAN-185): 704 →
  704 entradas; trocam só as impressões digitais dos 2 sítios editados (o `jq` e o `python3` do merge, os
  dois já «write-candidate desguardado» no baseline) e números de linha (as 7 linhas do
  `install-accelerators.sh` já estavam defasadas antes do patch). Conferido pela lente r-w5b-a da rodada 1:
  205 desguardados e 499 indeterminados antes e depois.
- `docs/deny-baseline.md`, seção «How an adopter opts out»: um parágrafo sobre o opt-out (abaixo).

## O opt-out e o que ele deixa de gravar

- `CEO_INSTALL_SKIP_DENY_BASELINE=1` pula o merge INTEIRO — a deny-baseline e o `defaultMode` (um merge,
  uma chave de desligar). A linha do instalador diz «SKIP: deny baseline + permissions.defaultMode
  (CEO_INSTALL_SKIP_DENY_BASELINE=1)». Uma instalação `--ceremony user` com o opt-out sai SEM bloco
  `permissions`. O mesmo vale quando o instalador não acha nem `jq` nem `python3` (WARNING, nada gravado)
  e quando o merge falha (WARNING, arquivo intocado).
- Sem `defaultMode` em nenhuma fonte de settings, o Claude Code 2.1.295 pode abrir a sessão em auto. No
  binário (sha256 `0116ee2e0a513900b633d9951367f18747686478e2b462805b8c31609f047f70`; busca de bytes do
  MAT-W5B em 2026-10-09, que reproduziu os offsets do construtor): o campo
  `permission_mode_from_default_fallback` está em 187383022 e a descrição dele («@internal True when
  current_permission_mode is auto because no settings source configured a mode and the gated auto default
  applied») começa em 187383085 — o 187383255 que o relatório do construtor citava é o trecho «auto mode
  is now the default», DENTRO da descrição (P3 do Codex na rodada 1, corrigido na mensagem de `210baa0b`);
  a escolha `_="auto",L=!0` está em 190134699; a condição de sessão interativa é a cláusula
  `(!n.isNonInteractiveSession||Yv()||k("tengu_moss_anchor",!0))`, que começa em 190134483, com o
  `k("tengu_moss_anchor",!0)` em 190134518. Outras condições que a mensagem de `210baa0b` cita
  (`disableAutoMode` diferente de "disable", o killswitch `tengu_auto_mode_config`, a flag
  `tengu_harbor_willow` ou a configuração da conta, sem taint HIPAA nem veredito pendente) foram
  conferidas pela lente r-w5b-b na rodada 2; a lista não se declara completa (o doc diz «among other
  conditions»), e nada disso é contrato documentado do Claude Code.
- A frase do `docs/deny-baseline.md` sobre o binário foi corrigida no anexo `01f94c78`: dizia «and the
  session is interactive», como condição necessária (P3 da lente r-w5b-b na rodada 2); diz agora «and
  either the session is interactive or a server-side flag that is on by default waives that». Com a flag
  no padrão (pela leitura do construtor no anexo, o segundo argumento de `k` é o valor padrão, `true`), a
  interatividade deixa de ser exigida: uma sessão não interativa (`claude -p`) também pode cair no auto. O
  parágrafo termina com «If you opt out, set `permissions.defaultMode` yourself.»

## Controle vermelho (registro)

Registro do construtor dos materiais (MAT-W5B), em `.claude/plans/PLAN-194/w5b/red-control.txt`. O SIGN
não o executa nem o lê; o rail do pacote o reproduz sobre as pré-imagens, que o SIGN confere pelos blobs
das linhas `index` do patch.

- Medido em 2026-10-09, entre ~20:13Z e ~20:29Z, em macOS (Darwin 27.0.0), bash 3.2 (`/bin/bash`) e
  Python 3.9.6. Base: HEAD `142f01cd7363`, com `scripts/install.sh` no blob pré-imagem
  `46299358f5b6ed0748a20340b42576c0ad3b1e94` (o mesmo de `0a953ece` e o da linha `index` do patch).
- O teste novo (a pós-imagem de `scripts/tests/test-install-deny-baseline.sh`, blob
  `f13c1b5f51e60a4c26834e4821432ea38090db68`) foi materializado SOZINHO num clone descartável do HEAD e
  rodado com `CEO_INSTALL_UNDER_TEST` apontando para o `install.sh` desse clone e HOME descartável: rc 1 em
  962 s, última linha «==> FAIL: install deny-baseline test»; passaram as pernas A a E, F/maintainer e H
  (85 linhas PASS), e o conjunto exato de linhas `::error::` foi:
  - `::error::[F/user] permissions.defaultMode is '<absent>', expected 'manual'`
  - `::error::[G] permissions.defaultMode is '<absent>', expected 'manual'`
- O mesmo teste com o patch inteiro (a árvore de `01f94c78`, no mesmo dia): rc 0 em 1104 s, nenhuma linha
  `::error::`, última linha «==> PASS: deny baseline merged, ordered, deduplicated, opt-out honored,
  exclusions honored, no-jq fallback works, defaultMode written when absent and kept when present».
- F/maintainer e H passam nos dois lados por desenho: são guardas, não controles. O Codex da rodada 2
  reproduziu F e G vermelhos no pai, nas duas rotas, com as instalações em rc 0.

## Bateria própria do pacote (linhas `hard` dos dados)

Os dados (`Dados:`) trazem, em ordem, as passadas duras e os gates específicos que o SIGN anterior deste
pacote rodava; os genéricos estão na lista fixa do molde (bloco comum):

- `bash -n scripts/install.sh`;
- `python3 .claude/scripts/check-installer-write-safety.py` (o censo de escrita do instalador, modo
  checagem);
- `bash scripts/tests/test-install-deny-baseline.sh` (o teste do pacote, pernas A a H, com o patch);
- `python3 .claude/scripts/validate_governance_fast.py`;
- `python3 .claude/scripts/check-time-unit.py docs/deny-baseline.md`,
  `python3 .claude/scripts/check-install-profiles.py`,
  `python3 .claude/scripts/gen-settings-user-template.py --check` e
  `bash scripts/tests/test-manifest-delivery-route.sh` (o oráculo bash que lê o `install.sh` por texto);
- a passada dirigida dos oráculos pytest do `install.sh`, numa linha só, sem `-n`: os que leem o
  `install.sh` por texto (`test_session_76_audit_v3_findings.py`,
  `test_session_77_audit_v3_backlog_findings.py`, `test_check_installer_write_safety.py`,
  `test_install_sh_placeholders.py`, `test_install_sh_self_sha.py`, `test_settings_guard_loadability.py`,
  `test_parity_seed_once_declared.py`, `test_parity_source_resolution.py`,
  `test_check_contamination_personal_path.py`, `test_install_yaml_glob.py`) e os que rodam instalações
  ou upgrades que tocam a superfície do patch (`test_upgrade_settings_migration.py`,
  `test_install_user_skips_governance_hooks.py`, `test_install_user_preserves_existing_repo.py`,
  `test_install_maintainer_unchanged.py`).

O `.claude/scripts/tests/test_gen_settings_user_template.py`, que o SIGN anterior também punha na passada
dirigida, fica só nas passadas do `testpaths`: com o patch, dois testes dele saem SKIP nesta máquina
(`test_no_match_statement`, em Python 3.9, e `test_pending_entries_point_at_an_open_question`, com
`exclude_hooks_pending` vazio), e uma linha `hard` de pytest exige resumo só de aprovados; nas passadas do
`testpaths` um SKIP não reprova.

## Resíduos declarados (pela forma)

- `templates/settings/settings.user.json:67`: a razão da exclusão de `permissions` diz que o `install.sh`
  «constroi a deny-baseline do adopter do zero»; agora ele também grava o `defaultMode`. O arquivo é
  canônico e derivado (`gen-settings-user-template.py --check`); a cura é uma cerimônia que regenere o
  template. Fica defasado até lá.
- O `scripts/tests/test-install-deny-baseline.sh` não roda no CI (`git grep` em `.github/` e no
  `Makefile`: 0 ocorrências). Follow-up: ligá-lo ao `smoke-install.yml`. Até lá, a única prova mecânica de
  que a instalação `user` grava "manual" é este teste, rodado como linha `hard` dos dados deste SIGN e à
  mão; a W1a/W1b do PLAN-183 re-derivam sobre este `install.sh` e devem rodá-lo também.
- Precedência: o "manual" do projeto do adopter vence um `defaultMode` que o desenvolvedor tenha no
  settings de usuário (ordem de mescla usuário < projeto < local < flag < policy, lida no binário pela
  lente r-w5b-b na rodada 1) — a mesma postura do mantenedor. A saída por sessão é a linha de comando ou o
  teclado (`--permission-mode`, shift+tab).
- O acoplamento ao opt-out é decisão de desenho: quem desliga a deny-baseline também fica sem o
  `defaultMode` (a linha SKIP e o doc avisam). Desacoplar pede uma segunda chave
  (`CEO_INSTALL_SKIP_DEFAULT_MODE`, sugestão da lente r-w5b-a) — decisão do Owner, fora deste pacote.
- A preservação, DENTRO do merge, de uma chave presente com valor diferente de "manual" só é exercitável
  por sonda de filtro (o único arquivo que o merge toca é o que o template acabou de produzir): o
  construtor e as duas lanes Claude da rodada 1 sondaram os filtros literais nas duas rotas (presente é
  mantido, ausente vira "manual"). `{"permissions": null}` diverge entre as rotas (o `jq` grava; o
  `python3` falha e cai no WARNING com o arquivo intocado) — classe anterior ao patch no merge da deny,
  alcançável só por template.
- O `mktemp -t` do macOS ignora o `TMPDIR` (medido pelo construtor, pela lente r-w5b-a e de novo na
  migração para o molde): as instalações do teste do pacote caem em `/var/folders/…/T`, não no `TMPDIR`
  que o SIGN dá aos filhos; o `trap` do teste as remove.
- O `.claude/scripts/tests/test_install_sh_placeholders.py` tem teto ABSOLUTO de 120 s por instalação e o
  `tests/integration/test_install_smoke.py`, de 90 s; os dois reprovam sob carga (classe de runner). O
  construtor mediu 92-113 s por instalação no HEAD e 83-91 s com o patch na mesma faixa de carga; o
  MAT-W5B, numa máquina carregada (2026-10-09), viu os dois testes do `test_install_smoke.py` reprovarem
  por `TimeoutExpired` de 90 s com e sem o patch. O primeiro roda na linha `hard` da passada dirigida, que
  não tem repetição; o segundo, nas passadas do `testpaths`, com até 3 repetições isoladas. Um teto
  estourado sob carga reprova o SIGN. Medido no ensaio `--dry-run` da migração (2026-10-11, esta máquina,
  com suítes de outras sessões rodando ao mesmo tempo): 4 testes do `test_install_sh_placeholders.py`
  estouraram os 120 s e a linha `hard` 9 saiu rc 1.

## Revisão do patch (rail)

- Rodadas 1 e 2 do patch: `codex exec --sandbox read-only` (codex-cli 0.160.0) e refutadores Claude;
  registros `.claude/plans/PLAN-194/w5b/rail-round-1.md` e `rail-round-2.md`. A rodada 1 (o Codex e as
  lanes r-w5b-a e r-w5b-b) revisou `0a953ece..b03934b9` (3 caminhos); as curas dela (o parágrafo do
  opt-out no `docs/deny-baseline.md`, as duas mensagens do caminho pré-existente e o offset corrigido)
  estão em `210baa0b`, revisado na rodada 2, e a cura do P3 da lente r-w5b-b na rodada 2 está no anexo
  `01f94c78`, conferido pelo Codex e pela lente r-w5b-b.
- O `w5b.patch` é `git diff --full-index --no-renames 0a953ece 01f94c78` da sombra do pacote (sem rename
  no diff: os bytes são os mesmos sem `--no-renames`). Os blobs pré-imagem das linhas `index` são os dos 4
  caminhos no `main` desde `0a953ece`.
- O registro citado na chave `rail` dos dados, `rail-round-3.md`, é o da rodada única desta migração para
  o molde (texto deste sentinel e dados) e fica preso ao sha256 do patch, ao deste texto com os campos por
  preencher e ao dos dados. O patch não mudou na migração.

<!-- bloco-comum sign-min v1 -->
## O SIGN deste pacote (bloco comum a todos os pacotes do molde sign-min)

Este texto é assinado pelo arquivo citado em `Molde:`, que executa o núcleo `.claude/plans/PLAN-194/sign-min/sign_min.py`, com os dados do arquivo citado em `Dados:`; os três estão no commit `Anchor-SHA`.

**Antes de escrever qualquer coisa no clone**, o SIGN confere, só por leitura, e recusa com o fato medido e rc 1, sem criar nem alterar arquivo na árvore nem no `.git` do clone (inclusive os bytes do `.git/index`):
- a entrada foi chamada por um caminho com «/», o PATH só tem diretórios absolutos, o `python3` está no PATH e o núcleo tem o sha256 informado pelo roteiro;
- o ambiente recebido pelo núcleo só tem nomes da lista do molde ou os 6 nomes que o `python3` do sistema acrescenta;
- o diretório atual é a raiz do clone, com um `.git` próprio;
- no modo real, a entrada padrão é um terminal e `GPG_TTY` é esse terminal;
- `git`, `gpg` e `bash` estão no PATH; o SIGN fixa o caminho absoluto e o sha256 do arquivo de `git` e do de `gpg`, e daí em diante executa `git` e `gpg` só por esses caminhos;
- `core.hooksPath` tem um único valor, `/dev/null`, e `core.fsmonitor` um único valor, falso, ambos vindos do `.git/config` do clone;
- a identidade do commit vem só da configuração do git;
- não há arquivo `*.lock` sob `.git`;
- `HEAD` é `refs/heads/main` e aponta para o mesmo commit que `refs/remotes/origin/main` do clone; esse commit é o `Anchor-SHA`;
- nenhum caminho rastreado tem atributo `filter`;
- `git status` não lista nada, nem arquivo não rastreado ou ignorado;
- cada arquivo rastreado tem na árvore os bytes e o bit de execução do índice, e todo modo do índice é 100644 ou 100755;
- os dados seguem a gramática do molde; o patch só cria, modifica ou remove arquivos, sem renomear, sem mudar modo, sem tocar `.gitattributes` nem o diretório do molde; cada pré-imagem é a do `Anchor-SHA`; e o patch aplica;
- este texto tem os 4 campos por preencher, este bloco igual ao `bloco-comum.md` do molde, e o `Scope` igual aos caminhos do patch;
- a `.asc` deste texto não existe no `Anchor-SHA`;
- o registro do rail citado nos dados traz o sha256 do patch, deste texto com os campos por preencher e dos dados, e o veredito APPROVE ou DECLARED-P2;
- os caminhos canônicos do patch, segundo o oráculo `--is-canonical`, são os declarados nos dados, e nenhum caminho do patch é do kernel;
- `python3` importa `pytest` e `xdist`; o allowlist `.claude/sentinel-signers.txt` do `Anchor-SHA` carrega sem erro e não está vazio; e o gpg tem uma chave secreta dele.

**Depois disso, nesta ordem**, o SIGN: cria um diretório temporário sob `/tmp` para os logs; aplica o patch ao índice e à árvore; confere que o índice difere do `Anchor-SHA` exatamente nas linhas `index` do patch (caminhos, modos e blobs) e que cada arquivo rastreado tem na árvore os bytes e o bit de execução do índice; roda cada comando `hard` dos dados, que tem de sair com rc 0 e, quando é `python3 -m pytest`, terminar com um resumo só de testes aprovados; roda o pytest sobre as raízes do `testpaths` do `pytest.ini`, nas duas passadas da divisão de marcadores do CI (`not serial` com `-n auto`, e `serial`), conta erro de coleta como falha, repete isolado até 3 vezes cada teste que falhou numa passada e conta como falha o que não terminou, em nenhuma repetição, com resumo só de aprovados; roda os gates de corpus (check-test-env-hygiene, env-inventory-check, check-active-hooks-executable, check-contamination, build-plugin --check, gen-command-skill-hook-map --check, check-docs-freshness, check-docs-drift, verify-counts --no-tests, check-claude-md-claims, check-ceremony-script, check-staleness e validate-governance), cada um com rc 0, sobre a árvore com o patch e com este texto ainda com os campos por preencher; os comandos `hard`, o pytest e os gates recebem um `GNUPGHOME` vazio, um `TMPDIR` com o caminho real, sem link simbólico, de um diretório da bateria criado dentro do diretório temporário, e nenhum `GPG_TTY`, cada um roda num grupo de processos próprio, e o SIGN falha se esse grupo ainda tem processo vivo 10 s depois de o comando terminar; confere de novo que a configuração efetiva do git é a lida no início, que `HEAD`, `refs/heads/main` e `refs/remotes/origin/main` são os lidos no início, que nenhum caminho rastreado tem atributo `filter`, o índice e a árvore, e que `git` e `gpg` resolvem no PATH para os mesmos caminhos, com o mesmo sha256 do início; preenche os 4 campos; assina este texto com a chave escolhida e verifica a assinatura com o `gpg_verify` e o allowlist lidos do `Anchor-SHA` antes da bateria, executando o `gpg` pelo caminho fixado; grava este texto e a `.asc` no índice pelos bytes assinados, sem filtro, e confere o índice e a árvore; faz um `git commit` sem editor, sem hooks e sem assinatura do git; e confere o commit. Depois da assinatura, o SIGN não inicia nenhum programa lido da árvore com o patch; um descendente da bateria que tenha saído do próprio grupo de processos não é conferido e pode continuar rodando.

**O que o SIGN entrega, e só com rc 0:** um commit em `refs/heads/main` deste clone cujo único pai é o `Anchor-SHA`, que difere dele exatamente nos caminhos do patch (com os blobs e modos das linhas `index`), neste texto e na `.asc`, com os bytes assinados; a `.asc` lida desse commit verifica com a mesma chave; autor e committer são a identidade conferida. Com qualquer outro rc, o SIGN não afirma nada: cada linha impressa antes vale só para o passo que ela relata.

**Requisitos** (o que o SIGN precisa encontrar; ele não diz de onde vêm):
- o bash começa com o ambiente montado por `env -i`: sem `BASH_ENV`, sem `ENV` e sem função importada;
- nenhum processo além do SIGN e dos comandos que ele inicia escreve no clone nem no diretório temporário durante a execução;
- a configuração efetiva do git no clone, no início, não define programa que o git execute além do que o SIGN confere acima;
- `/tmp` gravável; no PATH, `git`, `gpg`, `bash` e `python3`;
- nada troca, durante a execução, o que o `git` e o `gpg` carregam ou executam (bibliotecas, o programa para o qual um executável delega, o gpg-agent e o pinentry): o SIGN confere só o sha256 dos dois executáveis;
- no modo real, a chave do allowlist utilizável pelo gpg, com pinentry no terminal, o gpg-agent iniciado sem a senha em cache e a senha não guardada no chaveiro do sistema;
- um `HOME` gravável pelos testes da bateria.

**Publicação:** o Owner publica o commit no `main` do origin, sem force, pelo roteiro; o SIGN não faz push nem fetch.

**Fora do estado esperado:** o SIGN não diagnostica execução anterior, não desfaz e não apaga nada; recusa ou falha com o fato medido, e o clone e o diretório temporário ficam como estiverem. Depois que o núcleo restaura a disposição padrão dos sinais (nas suas primeiras instruções), um sinal INT, PIPE, TERM ou KILL encerra o SIGN sem linha nova dele.
<!-- fim do bloco-comum -->

## Scope

- `scripts/install.sh`
- `scripts/tests/test-install-deny-baseline.sh`
- `.claude/scripts/data/installer-write-safety-baseline.txt`
- `docs/deny-baseline.md`
