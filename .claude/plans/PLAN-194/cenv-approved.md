# cenv-approved — sentinel do pacote cenv: o evento `cost_envelope_capped` volta a ser gravado (canônico `.claude/hooks/check_cost_envelope.py`)

Plan: PLAN-194
Wave: cenv — item W1 de `PLAN-171-FOLLOWUP-cost-envelope-emit` (o `action` duplicado no `emit_generic` de `.claude/hooks/check_cost_envelope.py`)
Dados: .claude/plans/PLAN-194/cenv/sign.tsv
Molde: .claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh
Patch: .claude/plans/PLAN-194/cenv/cenv.patch
Control: .claude/plans/PLAN-194/cenv/red-control.txt
Patch-sha256: TO-FILL-BY-SIGN
Rail-Record-sha256: TO-FILL-BY-SIGN
Anchor-SHA: TO-FILL-BY-SIGN
Data: TO-FILL-BY-SIGN

## Ratificação (Owner)

- Ao assinar este texto, o Owner aprova o `cenv.patch` (sha256 em `Patch-sha256`) sobre o `Anchor-SHA`,
  aplicado e conferido pelo molde citado em `Molde:` com os dados citados em `Dados:`.
- O item é `.claude/plans/PLAN-171-FOLLOWUP-cost-envelope-emit.md` (status `draft`, criado em
  2026-10-10), W1 «land do pacote em curso» [P1], canônico por cerimônia GPG. O mesmo arquivo põe a
  condição: o pacote entra no lote de assinaturas só se o rail convergir em até 2 rodadas; senão, vai
  para a 1.4.4. A rodada 1 do rail convergiu (seção «Rail»).
- Ordem: decisão do Owner em 2026-10-09 (~15:45Z, S363; registro da sessão, fora do repositório) —
  assinaturas em dois conjuntos, «Lote A primeiro […]; Lote B depois = W7a + emenda ADR-158 +
  cost_envelope + U2-D». Este pacote é o `cost_envelope` do Lote B.
- Molde: a troca do SIGN próprio do pacote pelo molde «SIGN mínimo» é decisão do Owner (S363). Duas
  regras aplicadas aqui são decisões do CEO de 2026-10-11 (~13:35Z), com a ratificação do Owner
  pendente na data deste texto: o controle vermelho fica FORA do SIGN, como registro reproduzido pelo
  rail (seção «Controle vermelho (registro)»), e o pacote tem rodada única de rail e, no máximo, uma
  conferência de anexo. A assinatura deste texto as ratifica para este pacote.

## O que esta cerimônia entrega, e nada além

- Tamanho: 3 caminhos, +209 −8 linhas, 1 canônico (`.claude/hooks/check_cost_envelope.py`). Nenhum
  dos 3 caminhos está em `_KERNEL_PATHS` (`.claude/hooks/check_arbitration_kernel.py`).
- `.claude/hooks/check_cost_envelope.py`, `_safe_emit_capped`: sai a linha `action="cost_envelope_capped",`
  da chamada `emit_generic("cost_envelope_capped", …)`. A assinatura é `emit_generic(action: str,
  **kwargs)` (`.claude/hooks/_lib/audit_emit.py`): o `action` chegava duas vezes, a vinculação dos
  argumentos levantava `TypeError` antes de o `emit_generic` rodar, e o `except Exception` fail-open do
  hook o engolia — a única marca era uma linha no stderr do hook. O bloqueio já acontecia; o evento nunca
  entrava no log. Nada mais muda no hook (1 linha a menos).
- `.claude/hooks/tests/test_check_cost_envelope_emit.py` (NOVO, 100644): roda o hook como subprocesso,
  alimentado por um payload PreToolUse, com o emissor REAL gravando no diretório de auditoria isolado do
  teste (`TestEnvContext`), e afirma: um despacho permitido não grava linha `cost_envelope_capped`; um
  despacho bloqueado grava exatamente uma, com a janela, a classe, o teto, o contador, o `session_id` do
  payload e o `project`; a linha tem `hmac` e o `verify_chain` do log isolado está íntegro; nenhuma chave
  do lado do chamador (`project_path`, `user_id`, `user`, `command`) está na linha, nem o id do usuário
  nem o texto do comando na linha crua; nenhuma linha `dropped forbidden field` no `.errors`; nenhuma
  exceção engolida no stderr do hook.
- `.claude/hooks/tests/test_check_cost_envelope_block.py`: só a docstring — a referência à linha da
  decisão de bloqueio (`check_cost_envelope.py:281` → `:280`, a posição depois da cura) e o parágrafo do
  evento, que passa a apontar o teste novo.

## O que o evento passa a gravar (Sec MF-3)

- A linha leva só os campos da allowlist `_COST_ENVELOPE_CAPPED_ALLOWLIST` (`audit_emit.py`; o
  `emit_generic` filtra o evento por ela): `action`, `ts`, `session_id`, `project`, `event_schema`,
  `tokens_in`, `tokens_out`, `tokens_total`, `hmac`, `hmac_error`, `class_tier`, `window_breached`,
  `cap_cents` e `current_cents`. O hook passa `class_tier`, `window_breached`, `cap_cents`,
  `current_cents`, `session_id` e `project`; o `_write_event` acrescenta `event_schema`, `ts`, os três
  `tokens_*` (nulos) e `hmac`/`hmac_error` — nenhum deles é `project`.
- `project` é um campo por linha que o CHAMADOR preenche: o hook passa `project=` de
  `_resolve_project_path()`, que devolve `CLAUDE_PROJECT_DIR` ou, sem ela, `os.getcwd()`. O campo está na
  allowlist e na tabela de campos do evento (v2.27) em `SPEC/v1/audit-log.schema.md`.

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

## Controle vermelho (registro)

- O registro é `.claude/plans/PLAN-194/cenv/red-control.txt`, medição do construtor dos materiais, não
  do SIGN: o SIGN não o lê nem o executa. O rail do pacote o reproduz sobre as pré-imagens que o SIGN
  confere (o P0 exige que o blob pré-imagem de cada linha `index` do patch seja o do `Anchor-SHA`; o do
  hook é `03ad92380ad8fc95878c1d36a4efb63f4b1c8a0d`).
- Medição: o teste NOVO (blob `8e13237d68bbdb344fa69e70d483c11717c2a126`, a pós-imagem do patch),
  materializado SOZINHO numa cópia da base com o hook no blob pré-imagem, rodado com
  `python3 -m pytest -q -p no:cacheprovider -rfE --tb=short <o teste>`. Em 2026-10-11T04:30:10Z, macOS
  (Darwin 27.0.0), Python 3.9.6, pytest 7.3.0, sobre `61aa7372`: rc 1, «1 failed», o id
  `.claude/hooks/tests/test_check_cost_envelope_emit.py::CostEnvelopeCappedEmitTests::test_capped_dispatch_writes_exactly_one_event`,
  a asserção «exactly one cost_envelope_capped row expected; got 0» e, no stderr do hook,
  `emit_generic cost_envelope_capped exception: TypeError("emit_generic() got multiple values for argument 'action'")`.
  Com o patch inteiro (os 3 blobs pós-imagem): rc 0, «9 passed», nenhuma linha FAILED.
- Reproduzido pelo construtor da migração ao molde em 2026-10-11T19:28Z, na mesma máquina e nas mesmas
  versões, sobre `598b70e5` (o hook no mesmo blob pré-imagem), com `HOME` descartável: o mesmo id, o mesmo
  `TypeError`, rc 1; com o patch, rc 0, «9 passed».

## Bateria do pacote (as linhas `hard` dos dados)

Cada linha roda na ordem, depois de o patch ser aplicado, e tem de sair com rc 0; as de pytest também
terminam com resumo só de aprovados.

1. `python3 .claude/plans/PLAN-194/cenv/sintaxe.py` sobre os 3 caminhos do patch: `ast.parse` dos bytes
   de cada um, sem gravar bytecode (script do pacote, forma 3: o SIGN julga só o rc).
2. `python3 -m pytest` do teste novo e do teste de bloqueio (`--tb=short`).
3. `python3 -m pytest` de `.claude/hooks/tests/test_audit_emit.py` e
   `.claude/hooks/tests/test_audit_emit_api_contract.py` (`--tb=short`).
4. `python3 .claude/scripts/check-audit-registry-coverage.py`.
5. `python3 .claude/scripts/validate_governance_fast.py`.
6. `python3 -m pytest --strict-markers` de `.claude/hooks/_lib/tests/test_cost_envelope.py` (o contador
   do envelope) e `.claude/hooks/tests/test_template_dogfood_parity.py` (a exclusão deliberada do hook no
   template), sem `-n`.

O `check-test-env-hygiene.py` e o `validate-governance.sh` são gates fixos do molde (bloco comum).

## Rail

- Rodada 1 (sobre o patch): `codex exec --sandbox read-only` (codex-cli 0.160.0) e 2 refutadores Claude
  (r-cenv-a, Security Engineer; r-cenv-b, Code Reviewer) revisaram `6ccde6b0..3edf44dc` (3 commits de
  sombra da sessão S363, fora do `main`) e deram GO nas três lanes: o Codex «NENHUM ACHADO», as lanes
  Claude com 3 achados P3 distintos — 2 de texto no teste novo e 1 fora do patch (o follow-up do
  `_resolve_project_path`, abaixo).
- Anexo: as curas dos 2 P3 de texto são o commit `c395487e` (sobre `be7bec52`, que é `3edf44dc` por
  patch-id; só comentário e docstring do teste novo). O `cenv.patch` é `git diff --full-index --no-renames
  61aa7372 c395487e` dos 3 caminhos. A conferência do anexo (Codex 0.160.0, `--sandbox read-only`,
  2026-10-11, preflight 06:59:46Z) deu «NENHUM ACHADO» e `VERDICT: GO`, com os 2 arquivos de teste
  «9 passed» numa cópia por `git archive c395487e`.
- Este texto, os dados, o `sintaxe.py` e o registro do controle vermelho são materiais da migração ao
  molde (S363), escritos depois da rodada 1 e do anexo. Eles passam pela rodada única do pacote, cujo
  registro é o citado na chave `rail` dos dados; o SIGN só aceita esse registro com o sha256 do patch,
  o deste texto (com os campos por preencher) e o dos dados, e o veredito `APPROVE` ou `DECLARED-P2`.

## Resíduos declarados (pela forma)

- Follow-up da 1.4.4 (SPEC): a prosa do SPEC que descreve este evento (`SPEC/v1/audit-log.schema.md`)
  diz que caminhos crus de projeto nunca persistem pela linha, e a tabela de campos do mesmo SPEC lista
  `project` entre os campos do evento. `project` é campo da linha; a proibição mira chaves do chamador
  como `project_path`, a que o comentário deny-by-default da allowlist em `audit_emit.py` nomeia. A cura
  é texto canônico do SPEC; esta cerimônia não toca o SPEC.
- Follow-up da 1.4.4 (hook): `_resolve_project_path()` cai em `os.getcwd()` quando `CLAUDE_PROJECT_DIR`
  falta, e o `project` do evento passa a ser o diretório corrente. Pré-existente; esta cerimônia não o
  muda.
- O teste novo herda o resíduo do teste de bloqueio: o contador diário vive num arquivo de estado por data
  UTC e o hook não tem seam de relógio, então os dois despachos do teste precisam cair na mesma data UTC
  (declarado na docstring dos dois testes).
- A linha `hard` 1 é um script do pacote chamado pela forma 3 do molde: o SIGN julga só o rc dele.

## Scope

- `.claude/hooks/check_cost_envelope.py`
- `.claude/hooks/tests/test_check_cost_envelope_block.py`
- `.claude/hooks/tests/test_check_cost_envelope_emit.py`
