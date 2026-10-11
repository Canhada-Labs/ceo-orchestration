# w7a-approved — sentinel do pacote de CÓDIGO da W7a do PLAN-183 (fixtures do replay do gate do harness num caminho entregue; canônico `.claude/hooks/check_harness_config.py`)

Plan: PLAN-183
Wave: W7a, pacote de CÓDIGO — as 3 fixtures do replay de `.claude/hooks/tests/fixtures/harness-config/replay/` para `.claude/hooks/_lib/harness_replay/` (A1, P1 dos adopters)
Dados: .claude/plans/PLAN-183/w7a/sign.tsv
Molde: .claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh
Patch-sha256: TO-FILL-BY-SIGN
Rail-Record-sha256: TO-FILL-BY-SIGN
Anchor-SHA: TO-FILL-BY-SIGN
Data: TO-FILL-BY-SIGN

## Ratificação (Owner)

- PLAN-183, seção «W7a — fixtures num caminho entregue (forma 1)» (`PLAN-183-adopter-fitness.md`): a tabela
  de 9 caminhos, dividida em 8+1 — este pacote leva os 8 de código; a emenda do ADR-158 é OUTRO pacote, com rail
  e GPG próprios, derivado depois de o rail deste convergir (C1 do debate).
- Debate L3 das ondas W7 (`PLAN-183/debate/w7-round-1/consensus.md`): W7a PROCEED, `design-coherent`, sem
  VETO, condições C1 a C10; o `approved.md` das cinco ondas foi ratificado pelo Owner em 2026-10-02
  (`PLAN-183/debate/w7-round-2/approved.md`), com a W7a no trem da v1.4.3.
- Decisões do Owner de 2026-10-01 aplicadas ao pacote: OQ-12 — a pasta de dados
  `.claude/hooks/_lib/harness_replay/`, SEM `__init__.py`; o marcador de runtime recodificado (sem chave
  dupla); o patch por delete + add explícitos, sem rename.
- Tamanho: 8 caminhos, 456 linhas (+366 −90), 1 canônico (`.claude/hooks/check_harness_config.py`), que NÃO
  é kernel. O teto do modelo de operação v2 é 400 linhas; o prompt da conferência r3y do rail registra
  «Acumulado do pacote 0a953ece..94483a01 = 456 linhas (Owner aceitou o excesso)».
- Molde: este pacote é assinado pelo molde sign-min (S363). Ao assinar este texto, o Owner ratifica para este
  pacote duas decisões do CEO sobre o molde: o controle vermelho fica fora do SIGN, como registro do construtor
  que o rail reproduz (seção abaixo), e a rodada de rail do texto e dos dados é única, com no máximo uma
  conferência de anexo.

## O que esta cerimônia entrega, e nada além

- `.claude/hooks/_lib/harness_replay/` (pasta nova, de dados, sem `__init__.py`) com as 3 fixtures do replay,
  CRIADAS: `agent_spawn_named_no_skill_content.json` e `bash_safety_destructive.json` com os mesmos bytes das
  de origem; `canonical_edit_unauthorized.json` com o marcador de runtime novo `@HARNESS_REPLAY_PROJECT_DIR@`
  (só a linha 9 muda).
- As 3 fixtures de origem em `.claude/hooks/tests/fixtures/harness-config/replay/`, REMOVIDAS (a pasta fica
  vazia e sai da árvore, como o `git apply` a deixa).
- `.claude/hooks/check_harness_config.py` (canônico), sobre o blob pré-imagem `4a60dd75…`:
  - `REPLAY_FIXTURES_REL` = `.claude/hooks/_lib/harness_replay`; `FIXTURE_PROJECT_PLACEHOLDER` =
    `@HARNESS_REPLAY_PROJECT_DIR@`, a ÚNICA forma aceita: um «{{» em qualquer chave ou valor parseado de uma
    fixture é achado RED;
  - as três leituras JSON do módulo (settings, fixture, decisão do hook sob teste) recusam NaN e Infinity
    (`parse_constant=_refuse_constant`); a fixture recusa chave duplicada e aninhamento acima de 32; uma
    fixture que não parseia (inclusive UTF-8 inválido e recursão) é RED nomeado, nunca traceback;
  - a decisão do hook sob teste é o stdout INTEIRO, parseado como UM valor JSON (sem `.strip()`): preâmbulo,
    dois objetos, `\x0b`, `\x0c`, NBSP ou U+2028 em volta não certificam o controle;
  - o comentário C3: programa, argv, env e cwd vêm da tabela do gate e de `_replay_env`, nunca da fixture.
- `.claude/hooks/tests/test_check_harness_config.py` (oráculo 0): de 32 para 39 testes, entre eles a pasta
  padrão derivada de `chc.REPLAY_FIXTURES_REL` e o replay vivo sem `fixtures_dir` (C4), a asserção de ENTREGA
  pela chamada real ao bash do predicado do instalador, com rc exato e os controles do caminho antigo e de
  `templates/` (C5), a invariante de consumo da fixture com o controle converso (C3), a recusa de «{{» na
  fixture (C6) e o censo AST das leituras JSON do módulo.
- O patch não toca o ADR-158, o instalador, o `upgrade.sh`, o baseline do PLAN-185 nem `scripts/`.

## Comandos próprios do pacote (as linhas `hard` dos dados, nesta ordem)

1. `bash .claude/plans/PLAN-183/w7a/hard-w7a.sh` (envoltório rastreado, forma 2 do molde), que sai rc 0 só se,
   nesta ordem: o gate no modo do CI no repositório (sem argumentos) sai rc 0 com a última linha «OK:
   harness-config gate green (static=yes, replay=yes, 0 warning(s))»; a perna verde da C7 — instalação do zero
   (`--profile core`) a partir da árvore com o patch, num alvo com `.git` vazio — dá o gate do alvo
   (`--repo-root <alvo> --replay --no-exec-bit`) com rc 0 e «OK: harness-config gate green (static=no,
   replay=yes, 0 warning(s))», e a pasta nova do alvo com exatamente os 3 `.json`, iguais byte a byte aos da
   árvore, sem «{{»; o contrato do `/ceo-boot` (cwd = alvo, sem argumentos) sai rc 0 com a última linha verde;
   a C9 — a árvore do commit `b55084da` (v1.4.2), ancestral do HEAD, instalada do zero — dá o gate do alvo com
   rc 1 e «FAIL: 3 RED finding(s) (0 warning(s))», o `scripts/upgrade.sh` da árvore com o patch sobre esse
   alvo sai rc 0, os 3 `.json` e o hook ficam iguais byte a byte aos da árvore e o gate do alvo sai rc 0 com a
   linha verde do alvo; e o arquivo de teste do gate sai rc 0 com o resumo «39 passed». As instalações, o
   upgrade e os gates rodam sem `CEO_SOTA_DISABLE`, `CLAUDE_PROJECT_DIR` e `CLAUDE_PROJECT_DIR_NATIVE`, com HOME
   próprio dentro do diretório de trabalho do envoltório, criado sob o `TMPDIR` que o SIGN dá à bateria.
2. `python3 .claude/scripts/validate_governance_fast.py`.
3. `python3 -m pytest` sobre `test_check_bash_safety.py`, `test_check_active_hooks_executable.py`,
   `test_check_hook_stdout_schema.py`, `test_build_plugin_idempotency.py` e `test_env_inventory_check.py`, num
   processo só, com resumo só de aprovados.

Os outros quatro arquivos que o SIGN anterior deste pacote rodava numa passada dirigida
(`test_check_harness_config.py`, que o envoltório roda com a contagem exata;
`test_check_bash_safety_canonical_matrix.py`, que termina com 3 xfailed; `test_ceo_boot_liveness.py`, com 1
skipped; e `test_install_sh_placeholders.py`, com teto absoluto de 120 s por instalação) estão no `testpaths` do
`pytest.ini` e entram nas duas passadas do molde, com a repetição isolada dele.

## Controle vermelho (registro)

Medição do construtor, com data e substrato em `.claude/plans/PLAN-183/w7a/red-control.txt`; o SIGN não a
executa. O rail deste pacote a reproduz sobre as pré-imagens que o SIGN confere pelas linhas `index` do patch.

- (a) O teste novo, sozinho, contra o hook pré-imagem: rc 1 com EXATAMENTE os 9 ids listados no registro, em 3
  execuções sobre a árvore de `598b70e5` (2026-10-11, 19:31Z); com o patch inteiro, «39 passed».
- (b) Perna vermelha da C7: o alvo instalado do zero a partir da árvore sem o patch dá o gate com rc 1, 3
  achados RED de replay, os 3 «MISSING» e «FAIL: 3 RED finding(s) (0 warning(s))».
- C6: os dois varrimentos de marcador sobre `<alvo>/.claude` dão os mesmos caminhos (16 e 28 arquivos) no alvo
  sem o patch e no alvo com o patch.
- Registros das Checks do plano, medidos em 2026-10-11 sobre `61aa7372` (mesmas pré-imagens): AC3 (a constante
  de volta ao caminho antigo: 5 testes reprovam); AC4 (a fixture com o marcador antigo no caminho novo: o
  `test_install_sh_all_placeholders_substituted` reprova com esse único achado; com o patch, passa); C8 (o
  canal npm por `install-npm.sh --smoke`, local e sem publicar: os 3 `.json` no tarball e no alvo,
  cmp-idênticos, gate verde no alvo).

## Condições do debate (C1–C10) neste pacote

- C1: só o código; o ADR-158 fica para o pacote seguinte. C2 e o texto de C3 também são do pacote do ADR.
- C3 (controle no teste): `TestReplayConsumptionInvariant`. C4 e C5: os testes acima. C6: o marcador sem
  «{{», o hook só com a forma nova, a pasta nova do alvo sem «{{» no envoltório e os varrimentos com e sem o
  patch no registro. C7: a perna verde e o contrato do `/ceo-boot` no envoltório; a perna vermelha no
  registro. C8: plugin, `harness_replay` fora pelo `ignore_patterns` do `scripts/build-plugin.py`
  (`868231d9`, commit livre, opção (i)); npm, no registro. C9: no envoltório. C10: os dois FU com dono e
  posição, `PLAN-183-FOLLOWUP-delivered-gate-default-path-census.md` e
  `PLAN-183-FOLLOWUP-delivery-predicate-unification.md`, estão em `.claude/plans/` desde antes destes
  materiais (o SIGN não os confere), e os docstrings do hook e do teste citam a pasta nova.

## Rail

- O registro citado em `rail` nos dados traz as rodadas do patch — r1 (`0a953ece..5549a6b3`), r2
  (`..3ee7ef68`), r3 (`..a4cdc545`) e as conferências r3x (`d893285d`) e r3y (`94483a01`), com o Codex 0.160.0
  em `exec --sandbox read-only` e refutadores Claude, verbatim — e a rodada única do molde sobre este texto, os
  dados e o envoltório.
- O `w7a.patch` é `git diff --full-index --no-renames 0a953ece 94483a01` da sombra do pacote (5 commits),
  com patch-id estável `341f0bafd41be57caeabc091a8ee7af3994a0305`; nenhum dos 8 caminhos mudou entre
  `0a953ece` e `598b70e5`.

## Resíduos declarados (pela forma)

- Condição da última conferência do rail do patch (rx-w7a, P3): o censo AST do teste verifica o guard
  `_refuse_constant` pelo NOME, e uma segunda ligação desse nome no módulo passaria por ele (só os testes de
  comportamento a pegam, e só nas 3 leituras existentes). Follow-up nomeado:
  `PLAN-183-FOLLOWUP-json-census-call-binding` — um censo que siga a chamada, não o nome (trem da v1.4.4).
- O censo AST cobre as leituras por `json.load`, `json.loads` e `json.JSONDecoder` do módulo; leitura por
  `__import__`, `importlib` ou `sys.modules` fica fora (declarado pelas lanes do rail).
- Chave duplicada e `1e999` seguem aceitos nas settings e na decisão do hook sob teste, como o `JSON.parse` do
  harness os aceita; nas fixtures, a chave duplicada é recusada.
- Texto que cita o caminho antigo, fora do Scope: `.claude/hooks/tests/fixtures/harness-config/README.md`
  (descreve `replay/` e o marcador antigo) e o comentário do `.github/workflows/validate.yml` (canônico); os
  dois ficam defasados até um commit próprio.
- Plugin: o `build-plugin.py` copia o hook para `dist/` e exclui a pasta de fixtures; o `hooks.json` do
  plugin não registra o gate, e uma execução manual dele num adopter só-plugin segue com os 3 MISSING
  (medido pela lane r-w7a-a na rodada 1).
- npm: a presença dos 3 `.json` no packlist não tem asserção permanente no `npm-publish.yml` (FU (2) de
  «Fora destas ondas» do plano).
- Os adopters seguem com o gate vermelho até um CORTE levar este pacote. As pernas permanentes da C9 no
  `test-upgrade-historical-adopter.sh` landam como commit livre antes da rc.1 da 1.4.3; se não landarem, o
  CHANGELOG do corte declara a cura via upgrade NÃO provada.
- O envoltório é julgado só pelo rc (forma 2 do molde): o SIGN não lê o resumo dele, e quem garante que ele
  sai com rc diferente de 0 quando uma conferência falha é o rail deste pacote.
- O `test_install_sh_placeholders.py` tem teto ABSOLUTO de 120 s por instalação (e o
  `tests/integration/test_install_smoke.py`, de 90 s): numa máquina carregada, uma falha por tempo que se
  repita nas 3 repetições isoladas do molde reprova o SIGN.
- O SIGN anterior deste pacote registrava o tempo do contrato do `/ceo-boot` contra um teto de 2,5 s, só como
  nota; o envoltório não mede tempo.

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

- `.claude/hooks/_lib/harness_replay/agent_spawn_named_no_skill_content.json`
- `.claude/hooks/_lib/harness_replay/bash_safety_destructive.json`
- `.claude/hooks/_lib/harness_replay/canonical_edit_unauthorized.json`
- `.claude/hooks/check_harness_config.py`
- `.claude/hooks/tests/fixtures/harness-config/replay/agent_spawn_named_no_skill_content.json`
- `.claude/hooks/tests/fixtures/harness-config/replay/bash_safety_destructive.json`
- `.claude/hooks/tests/fixtures/harness-config/replay/canonical_edit_unauthorized.json`
- `.claude/hooks/tests/test_check_harness_config.py`
