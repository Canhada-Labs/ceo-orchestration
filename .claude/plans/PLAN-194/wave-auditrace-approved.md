# wave-auditrace-approved — sentinel da cura da corrida no gravador do agent_spawn (PLAN-194)

> Assinatura e land em um passo: `bash .claude/plans/PLAN-194/w-auditrace/OWNER-AUDITRACE-SIGN.sh`
> (confere as pré-condições e o último registro do rail, aplica o patch,
> confere que os bytes aplicados são os revisados, roda a bateria — gates de corpus, os dois arquivos
> de teste da cura e as suítes do `pytest.ini` com a divisão de marcadores do CI —, preenche
> Anchor-SHA, Patch-sha256, Rail-Record-sha256 e Data, assina com a chave do allowlist de
> signatários, stageia o conjunto EXATO e commita; `--dry-run` ensaia sem assinar nem commitar).
> Push é decisão sua.
> Sessão dedicada (regra U-3 do PLAN-169): esta cerimônia arma o override de kernel; não a encadeie
> com outra no mesmo shell. O SIGN recusa rodar se `CEO_KERNEL_OVERRIDE` ou
> `CEO_KERNEL_OVERRIDE_ACK` já vierem do ambiente.

Plan: PLAN-194
Wave: unidade 4 de «Unidades que ganharam dono» — cura da corrida no gravador do `agent_spawn` (risco 11)
Patch: .claude/plans/PLAN-194/w-auditrace/auditrace.patch
Patch-sha256: c864ff693b1b57cc7e664342030355aa1e9a190b9c5bcb9f9b1997879876b21b
Rail-Record-sha256: 1f5b96d6ca2a3889d2a3095264962bf74fb6b9cf3acec4254610a45e85de4f5b
Anchor-SHA: 70a1292e67d6a64de4df6627bdcb2fb8b4ebc2fa
Data: 2026-10-02

## Ratificação (Owner)

- Condição 67 do envelope assinado da v1.4.0-rc.1, repetida no da v1.4.0
  (`.claude/governance/pair-rail-verdict-v1.4.0.md`): «`append_entry` lê o predecessor e calcula o
  HMAC FORA do lock».
- PLAN-194, risco 11 e unidade 4 de «Unidades que ganharam dono» (S361): «ler o elo anterior e
  calcular o HMAC DENTRO da trava, com teste de N gravadores em paralelo e controle vermelho no
  código atual».
- Debate do PLAN-194, rodada 1, Security Engineer, must-fix MF-W2-1
  (`.claude/plans/PLAN-194/debate/round-1/security-engineer.md`): a cura move chave, elo anterior e
  HMAC para dentro do `with FileLock(...)`, DEPOIS do `rotate_if_needed`, com teste de N gravadores
  `agent_spawn` em paralelo com escritores `audit_emit`, vermelho no código atual e `verify_chain()`
  íntegro; deve landar antes do SIGN da W2.
- Mesmo debate, QA Architect, must-fix 8 (`.claude/plans/PLAN-194/debate/round-1/qa-architect.md`):
  controle de barreira vermelho no HEAD e verde depois, censo por AST de `read_prev_hmac()` dentro de
  `with FileLock(`, com módulo sintético como controle positivo, e a docstring do
  `test_two_writer_chain.py` atualizada.

## O que esta cerimônia entrega, e nada além

O caso, pela forma: um gravador da cadeia HMAC que lê o elo anterior fora da trava sob a qual
anexa. Esta cerimônia cura o único gravador com essa forma no censo do risco 11 — `append_entry`, em
`.claude/hooks/audit_log.py`, o gravador das linhas `agent_spawn` do hook PostToolUse:

- `append_entry` passa a obter a chave (`get_or_create_key()`), ler o elo anterior
  (`read_prev_hmac()`, o arquivo `audit-log.last-hmac`), calcular o HMAC da linha, serializá-la,
  anexá-la ao log e atualizar `audit-log.last-hmac` dentro de UMA mesma trava do log (`FileLock` no
  arquivo `audit-log.lock`), depois do `rotate_if_needed`. É a trava sob a qual
  `_lib/audit_emit._write_event` e a drenagem do spool já leem o elo anterior e anexam. Antes, a
  chave, o elo e o HMAC eram obtidos ANTES da trava: um gravador que anexasse entre a leitura e a
  trava (outro `agent_spawn` em paralelo ou um evento do `audit_emit`) deixava a linha encadeada num
  elo velho, e `verify_chain()` acusava `hmac_mismatch` sem que ninguém tivesse adulterado nada. Da
  sequência da cadeia, só a importação do módulo `_lib.audit_hmac` fica fora da trava.
- Rotação feita por este gravador: quando o `rotate_if_needed` (dentro da trava, como antes)
  renomeia o log, o gravador chama `_lib.audit_emit._emit_chain_reset_marker_under_lock` — o mesmo
  auxiliar que o `audit_emit` e a drenagem do spool chamam nas rotações deles — antes de ler o elo:
  a linha 1 do log novo é o `chain_reset_marker` ancorado na gênese, o
  `audit-log.rotation-manifest.json` é gravado, `audit-log.last-hmac` passa a ser o HMAC do marcador
  e a linha do `agent_spawn` encadeia nele (requisito de produtor do ADR-055-AMEND-2). Antes, a linha
  1 do log novo era o próprio `agent_spawn`, com o HMAC calculado sobre o elo do arquivo antigo. Com
  a cadeia desligada (`CEO_AUDIT_HMAC_DISABLE=1`), nenhum marcador é gravado, como no `audit_emit`.
- Quando o auxiliar NÃO grava o marcador — devolve `None` ou levanta —, a linha do `agent_spawn` é
  gravada sem HMAC (`hmac` nulo; `hmac_error` = `chain_reset_marker_missing`, campo fora do HMAC), com
  um breadcrumb, e `audit-log.last-hmac` fica como o auxiliar o deixou. Motivo, no caso em que o
  anexo do marcador falha: o auxiliar já gravou em `audit-log.last-hmac` o HMAC do marcador e devolve
  `None` sem restaurar o sidecar nem o manifesto; assinar a linha ali a encadearia num marcador que
  não está no disco. O comportamento dos verificadores diante dessa linha é o anterior; esta
  cerimônia não o altera.
- O fail-open segue: o estouro da trava (`FileLockTimeout`, 2,5 s) descarta a linha com um
  breadcrumb em `audit-log.errors`, sem bloquear a sessão e sem mexer em `audit-log.last-hmac` (o
  breadcrumb mostra a linha sem o HMAC, que só existe dentro da trava); um erro ao obter a chave ou
  ao calcular o HMAC grava a linha com `hmac` nulo e a classe do erro em `hmac_error` (campo
  excluído do HMAC por desenho), como antes; uma falha do marcador segue o item acima.
- Nenhum arquivo de trava é criado, renomeado ou apagado por esta cerimônia: o gravador usa o
  mesmo `audit-log.lock` de antes.
- Testes, em `.claude/hooks/tests/test_two_writer_chain.py`:
  - um censo por AST: em todo módulo de produção sob `.claude/hooks`, `.claude/scripts` e `scripts`
    (fora de diretórios `tests` e do próprio `_lib/audit_hmac.py`) que grava a cadeia — que NOMEIA
    `compute_entry_hmac` ou `write_last_hmac` de qualquer forma: chamada, atributo, nome, `import` ou
    texto literal igual ao nome —, toda chamada a `read_prev_hmac()` fica lexicamente dentro de um
    bloco `with FileLock(...)` que também chama `write_last_hmac` pelo nome, fora de função aninhada;
    o censo exige achar ao menos 2 leituras (anti-vácuo) e tem controle positivo em módulos
    sintéticos (leitura antes da trava; leitura e gravação do elo em dois blocos de trava distintos;
    leitura por apelido; leitura por `getattr` com o nome em texto; primitivas de escrita só por
    apelido; a forma correta). Um módulo que não nomeia nenhuma primitiva de escrita — o que só lê o
    elo para um instantâneo — fica fora do censo;
  - a janela leitura→anexo (classe marcada `serial`): logo depois de `append_entry` ler o elo, um
    gravador síncrono do `audit_emit`, em outro processo, é solto; quando ele sinaliza que vai tomar a
    trava, ganha 1,0 s para anexar (o prazo de trava dele é 2,5 s); a linha dele tem de entrar DEPOIS
    da linha do `agent_spawn`, com a cadeia íntegra;
  - o estouro da trava, a rotação feita pelo gravador (com e sem cadeia) e a falha do anexo do
    marcador DEPOIS de o auxiliar gravar `audit-log.last-hmac` (a linha do `agent_spawn` sai sem HMAC;
    o sidecar e o manifesto ficam como o auxiliar os deixou);
  - a corrida entre processos — 4 gravadores de `agent_spawn` e 2 do `audit_emit`, no modo síncrono e
    no modo spool (o padrão de produção; cada emissor faz uma drenagem forçada a cada 3 emissões, como
    um processo de hook ao sair, além das oportunistas), soltos por uma barreira, com `verify_chain()`
    íntegro sobre todas as linhas e a contagem conferida. Contra o falso verde, o TIPO de gravador
    tem de alternar e voltar no log (`agent_spawn` → `debate_event` → `agent_spawn`, ou o inverso: ao
    menos 2 trocas de tipo); um controle negativo prova que blocos segregados (todos de um tipo e
    depois todos do outro) reprovam essa guarda. Na contagem, uma linha descartada por estouro de
    trava (o breadcrumb de `append_entry` ou o arquivo de fallback do `audit_emit` síncrono) é contada
    como o descarte documentado do fail-open, nunca confundida com a corrida.
- Em `.claude/hooks/tests/test_audit_log.py`, o teste de rotação passa a esperar o marcador como linha
  1 e a cadeia do log novo íntegra.
- Controle vermelho: sobre o código anterior, 7 testes reprovam — o censo nomeia a leitura fora da
  trava em `audit_log.py`, a janela vê a linha estranha entrar no meio, os da corrida acusam
  `hmac_mismatch` numa linha `agent_spawn`, os dois de rotação não acham o marcador e o da falha do
  marcador acha a linha assinada (`w-auditrace/red-control.txt`). O da falha do marcador também
  reprova sobre a pós-imagem da rodada 1 do rail (a linha encadeada no marcador ausente).

## Kernel

`.claude/hooks/audit_log.py` está em `_KERNEL_PATHS` (`.claude/hooks/check_arbitration_kernel.py:217`).
O hook de kernel barra as ferramentas de edição (Edit, Write, MultiEdit) e não vê um `git apply`; o
SIGN aplica por `git apply` e segue o molde de
kernel (W3-K do PLAN-169, menor escopo; 179fu do PLAN-179, par validado vivo): no P0, recusa rodar com
o override já no ambiente e confere, pelas funções do próprio hook (`_is_kernel_path` e
`_override_granted`), que o caminho é kernel e que o par que vai exportar satisfaz o contrato; arma
`CEO_KERNEL_OVERRIDE` (reason-SLUG `PLAN-194.wave-auditrace.sentinel-wave-auditrace-approved`) e
`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` só em volta de cada `git apply` (aplicar e, no desfazer, reverter)
e desarma logo depois. Se o caminho deixar de ser kernel, o SIGN reprova (esta seção ficaria falsa).

## Residual declarado (pela forma)

- Estouro da trava sob saturação: com a chave, o elo, o HMAC e a serialização dentro da trava, a
  seção crítica ficou maior. Medido (`w-auditrace/lockstress-S361.txt`, máquina compartilhada, duas
  medições): até 48 gravadores em paralelo com até 30 anexos seguidos cada, nenhum descarte, antes e
  depois; na saturação sintética de 32 gravadores × 150 anexos seguidos, a cura descartou pelo estouro
  da trava 29 de 57.600 linhas (0,05%) com a pós-imagem da rodada 2 (blob `f66cb3d8`; a final,
  `4af77462`, só muda uma docstring) e 51 de 48.000 (0,11%) com a da rodada 1, e a pré-imagem nenhuma — mas a pré-imagem quebrou a cadeia em todas as repetições. O instrumento usa só gravadores `append_entry` e não modela a produção, em que
  as drenagens forçadas do spool também disputam a trava: em produção a pré-imagem JÁ descartou linhas
  `agent_spawn` por estouro da trava — o `audit-log.errors` vivo deste repositório tinha 3
  breadcrumbs `would-log` de `agent_spawn` (2026-10-01T23:48:41Z, 2026-10-02T00:44:25Z e
  00:52:00Z) ao lado de 32.721 `drain canonical lock timeout`, contados em 2026-10-02T04:54Z. O prazo
  de 2,5 s não muda aqui. O descarte é o caminho fail-open documentado e perde o
  registro (fica só o breadcrumb); o `audit_emit` manda o mesmo estouro para o arquivo de fallback e o
  `append_entry` não — assimetria anterior a esta cerimônia, que fica para decisão (W2 /
  ADR-055-AMEND-4).
- Falha do anexo do marcador: o estado que o auxiliar do `_lib/audit_emit.py` deixa —
  `audit-log.last-hmac` com o HMAC de um marcador que não está no disco, e o manifesto presente — não
  muda aqui (o arquivo é canônico e fica fora deste pacote). Esta cerimônia só impede que a linha do
  `agent_spawn` seja assinada sobre ele. A próxima linha assinada por um gravador que lê o
  `audit-log.last-hmac` (o `agent_spawn` seguinte ou o `audit_emit` síncrono) encadeia no marcador
  ausente e o `verify_chain()` acusa a quebra; a drenagem do spool deriva o elo da cauda do log, não do
  sidecar; com o manifesto presente, o `audit-verify-chain.py` exige o marcador como primeira linha
  com HMAC e reprova o arquivo. A falha fica ruidosa, como o próprio auxiliar documenta. O
  `audit_emit._write_event` segue em frente depois do mesmo `None` e assina a sua linha sobre o
  marcador ausente; não muda aqui.
- Linha sem HMAC fora do encadeamento; visível pelo `check-audit-hmac-null.py`.
- Na rotação feita por este gravador, a importação do `_lib.audit_emit` acontece com a trava segura
  (custo não medido) e instala os tratadores de saída do spool: o processo do hook que rotacionou passa
  a fazer uma drenagem forçada ao sair (até 2,5 s de espera de trava). Evento raro (uma vez a cada
  10 MiB de log).
- A exclusão mútua vale entre gravadores que resolvem a MESMA trava para o mesmo log; dois
  processos com ambientes divergentes (`CEO_AUDIT_LOG_LOCK` ou `CEO_AUDIT_LOG_PATH` apontando para
  lugares diferentes para o mesmo log) seguem sem exclusão entre si. Esta cerimônia não muda a
  resolução de caminhos.
- `append_entry` não incrementa o contador `audit-log.chain-length` (o `audit_emit` e a drenagem do
  spool incrementam): o contador fica abaixo do número de elos. `verify_chain(strict_against_counter=True)`
  só acusa quando conta MENOS elos que o contador, então isso não gera falso alarme, mas a detecção de
  truncamento da cauda não conta as linhas `agent_spawn`. Não muda aqui.
- A primeira cunhagem da chave HMAC segue não exclusiva (condição 68 da v1.4.0-rc.1): esta cerimônia
  só passa para dentro da trava a obtenção da chave feita por ESTE gravador; os demais chamadores de
  `get_or_create_key()` não mudam.
- As quebras que a corrida já gravou na cadeia viva e nos arquivos rotacionados continuam lá: esta
  cerimônia não reescreve histórico, e a triagem delas segue a do risco 11 (recomputação contra os
  elos anteriores).
- O auxiliar do marcador cria o log novo com `open("a")`, no modo que o umask der; este gravador
  reaperta o log para `0600` logo depois, como antes. A drenagem do spool, que também rotaciona e
  chama o mesmo auxiliar, não reaperta o log; esta cerimônia não muda o spool.
- Do estresse que o MF-W2-5 pede para a W2, esta cerimônia NÃO cobre: as saídas pelo caminho rápido
  (ainda não existem), o kill -9 no meio de uma drenagem, o reuso de PID, a recuperação de um
  `.draining` órfão e a reconciliação com `truly_lost = 0`. O contador `truly_lost` de
  `JournalReconciliation` (`_lib/spool_writer.py`) não é incrementado por nenhum caminho do código
  atual, então `truly_lost = 0` ainda não mede perda; isso fica para a W2.
- Os gravadores do Codex e do Grok (`CEO_HOOK_ADAPTER=codex|grok`) gravam pelo `audit_emit`, já sob a
  trava; não mudam.
- O censo é LÉXICO e cobre só a leitura do elo pela função `read_prev_hmac()`: a drenagem do spool
  lê o elo anterior da cauda do log (outra função, sob a trava) e fica fora dele. Num módulo que grava
  a cadeia, o censo acusa (em vez de aceitar) as formas que não modela: uma referência a
  `read_prev_hmac` que não seja a própria chamada (apelido, `from … import read_prev_hmac`, texto
  literal igual ao nome, como num `getattr`), uma leitura numa função auxiliar chamada sob a trava,
  uma trava aberta por outro nome (`with lock:`) e um bloco de trava que só grava o elo por apelido.
  Um nome montado em tempo de execução (texto concatenado, `globals()`, `importlib`) não é visto: um
  módulo que só nomeia as primitivas assim fica fora do censo. A trava é reconhecida pelo NOME
  `FileLock`, não pelo caminho: uma leitura do elo sob outra trava (a de um journal, por exemplo) que
  também grave o elo passa no censo. A exclusão do `_lib/audit_hmac.py` é pelo nome do arquivo
  (qualquer `audit_hmac.py` sob as raízes). A ordem leitura→anexo dentro do bloco é provada pela
  janela leitura→anexo só para `append_entry`.
- O `CHANGELOG.md` não muda nesta cerimônia: a aposentadoria da condição 67 nele é um land livre em
  `[Unreleased]`, depois deste, que o corte da W7 converte na entrada da versão.

## Bateria e revisão

- O SIGN aplica o patch e confere que o blob de cada caminho tocado é o `index` pós-imagem do patch
  (os bytes que landam são os revisados) — depois de aplicar, de novo depois da bateria e, no índice,
  depois de stagear; roda os gates de corpus, os dois arquivos de teste da cura (inteiros, inclusive as
  classes marcadas `serial` da janela e da corrida entre processos) e as suítes do `pytest.ini` com a divisão de
  marcadores do CI (`-n auto -m 'not serial'` e `-m serial`) — um superconjunto das suítes dos jobs
  do CI que rodam `.claude/hooks/tests` (`hook-tests-python-matrix` e `hook-tests-dual-rail`); ficam
  fora as raízes `.claude/scripts/{mcp-server,detectors,predict-budget}/tests` e os testes do sidecar
  de hipóteses, o gate Tier-1 de cobertura que inclui o `audit_log.py` (86%), as pernas de
  interpretador e de ambiente do CI que diferem do `python3` de quem roda o SIGN. Qualquer falha de
  um teste dos dois arquivos da cura, em qualquer passada, reprova o SIGN na hora, sem rerun. Uma
  falha de outro teste é rerrodada ISOLADA com o patch, até 3 vezes; passar em alguma é nota
  (instável). Se falhar nas 3, é rerrodada uma vez num worktree destacado do HEAD (a árvore sem o
  patch): se lá ela também falha (rc 1 do pytest), é nota (pré-existente) e não bloqueia; qualquer outro resultado sem
  o patch — passa, não existe, erro — reprova o SIGN. Um gate que reprova com o patch é rodado de
  novo nesse worktree: se também reprova lá, é nota (pré-existente); se passa, reprova o SIGN. O HEAD
  não pode mudar entre as pré-condições e o commit (conferido depois da bateria e antes do commit): o
  Anchor-SHA é o pai do commit. O texto assinado é o deste arquivo no HEAD (`HEAD:<sentinel>`, o que
  o `Rail-Text-sha256` nomeia), preenchido numa cópia fora da árvore, gravado no lugar e conferido
  pelo blob; o SIGN aborta se o arquivo vivo mudar durante a bateria e, depois de stagear, confere
  que o blob do sentinel no índice é o preenchido e reverifica a assinatura sobre o conteúdo do
  índice. Antes de aplicar, o P0 exige commitadas a evidência que este texto cita
  (`red-control.txt`, `lockstress-S361.txt`, `rail-prompt.md`, `test-ceremony-auditrace.sh`) e
  recusa, pelo nome, um patch com cabeçalho estrutural (arquivo novo ou removido, troca de modo,
  rename, cópia ou binário).
- A assinatura é feita com `--local-user` pela chave secreta cuja impressão digital está em
  `.claude/sentinel-signers.txt` e precisa verificar contra esse allowlist (GOODSIG e VALIDSIG);
  senão o SIGN desfaz tudo.
- Rail: a cargo do CEO, pelo codex pinado, `codex exec --sandbox read-only`, sobre o patch e sobre
  este texto (`w-auditrace/rail-prompt.md`); registros `.claude/plans/PLAN-194/w-auditrace/rail-round-N.md`.
  Regra de parada pré-registrada: no máximo 3 rodadas. O SIGN exige que o registro da última rodada
  nomeie o sha256 deste patch (`Rail-Subject-sha256`) e o sha256 deste texto antes de o SIGN
  preencher os quatro campos acima (`Rail-Text-sha256`), com veredito `APPROVE` (a rodada não relatou achado) ou
  `DECLARED-P2` (só P2, declarados no próprio registro), e vincula esse registro por hash
  (Rail-Record-sha256) a esta assinatura. O sujeito do registro é o patch e este texto; o ensaio do
  script do SIGN é o harness `w-auditrace/test-ceremony-auditrace.sh` (chave GPG descartável, clones
  descartáveis).

## Scope

- `.claude/hooks/audit_log.py`
- `.claude/hooks/tests/test_audit_log.py`
- `.claude/hooks/tests/test_two_writer_chain.py`
