# wave-fn04-approved — sentinel da cura FN-04 (PLAN-193 W4b)

> Assinatura e land em um passo: `bash .claude/plans/PLAN-193/wave-fn04/OWNER-FN04-SIGN.sh`
> (confere as pré-condições e o último registro do rail, aplica o patch, confere que os bytes
> aplicados são os revisados, roda a bateria — gates de corpus e as suítes do `pytest.ini` com a
> divisão de marcadores do CI —, preenche Anchor-SHA, Patch-sha256, Rail-Record-sha256 e Data, assina
> com a chave do allowlist de signatários, stageia o conjunto EXATO e commita; `--dry-run` ensaia sem
> assinar nem commitar). Push é decisão sua.

Plan: PLAN-193
Wave: W4b — cura do FN-04 (ledger de Workflow: bytes de scriptPath antes da decisão de permissão)
Patch: .claude/plans/PLAN-193/wave-fn04/fn04.patch
Patch-sha256: TO-FILL-BY-SIGN
Rail-Record-sha256: TO-FILL-BY-SIGN
Anchor-SHA: TO-FILL-BY-SIGN
Data: TO-FILL-BY-SIGN

## Ratificação (Owner)

- Condição 23 do envelope do GA v1.4.1 (`.claude/plans/PLAN-192/repass-ga/CONDITIONS-ga.md`,
  seção E): «a cura está alvejada para a 1.4.2, em cerimônia canônica».
- PLAN-193, item W4b: «o PreToolUse do Workflow não persiste bytes de `scriptPath` antes da decisão
  de permissão (confinar ao projeto e/ou gravar só o hash; cerimônia canônica em `launch_ledger.py` +
  `check_workflow_launch.py`), com controle vermelho do canário S357; sequencial DEPOIS da opção B
  (mesmos arquivos de teste)».
- Pedido do Owner (S357, 2026-09-24, verbatim): «finaliza tudo e tenha certeza que vai funcionar pra
  nao ficar vai e volta, que eu assino e faco o script rodar de manha, so ensaia antes e deixa pronto».

## O que esta cerimônia entrega, e nada além

A classe, pela forma: um hook que roda antes da decisão de permissão do harness e grava os bytes de
um caminho que o harness pode negar. Esta cerimônia cura o caso que a condição 23 descreve — o
ledger do hook do `Workflow` — e nenhum outro hook da classe (ver o residual). A cura escolhida é a
do item W4b, «gravar só o hash», com o snapshot movido para depois da decisão:

- No PreToolUse da tool `Workflow`, `check_workflow_launch.py` (por `_lib/launch_ledger.py`) deixa de
  gravar os bytes do arquivo que `tool_input.scriptPath` nomeia. O manifesto registra o caminho, o
  `sha256` e o tamanho (o `sha256` também na linha do índice), com `script_snapshot: null` e, quando
  o arquivo foi lido, `script_snapshot_why: awaiting_post_tool_use`.
  O texto de um `script` inline — campo da própria chamada, não um caminho — segue com snapshot no
  PreToolUse, como antes.
- O snapshot de um `scriptPath` lido antes do despacho (registro com hash) passa a ser tirado no
  PostToolUse, e só quando o vínculo é por `tool_use_id` (o PostToolUse da mesma chamada) e a
  resposta reporta o id como o run lançado (o rótulo `Run ID:` ou uma chave `runId`/`run_id` no
  topo da resposta; um id solto no texto não serve). O arquivo é relido pelo mesmo leitor
  limitado, relativo ao `cwd` gravado antes do despacho, e os bytes viram `<launch_id>.script` só
  quando o `sha256` deles é o gravado antes do despacho; nos outros casos de um registro com hash,
  nada é gravado e `script_snapshot_why` diz o motivo. Um `scriptPath` ilegível antes do despacho
  segue como antes: sem hash, sem snapshot, sem leitura depois. O vínculo heurístico (sem
  `tool_use_id`) e o `bind` manual não tiram snapshot e não leem arquivo algum além dos registros
  do próprio ledger (índice e manifestos); só o vínculo por `tool_use_id` lê — o arquivo que
  `scriptPath` nomeia, para tirar o snapshot, e a cópia do harness que a resposta nomeia, só para
  compará-la com o snapshot que o registro tem.
- O validador do manifesto lido de volta (`manifest_problem`) aceita um registro de `scriptPath` com
  hash e sem snapshot; quando um registro com hash (script inline, ou `scriptPath` lido antes do
  despacho) nomeia um snapshot, os bytes seguem conferidos contra o hash. Um registro sem hash —
  `scriptPath` ilegível antes do despacho, workflow nomeado ou sem script — segue como antes: o
  validador não confere o snapshot que ele nomeie, e a comparação de script dele é inconclusiva. Num
  registro de `scriptPath` sem snapshot, nenhum byte gravado reproduz o hash gravado antes do
  despacho, e a comparação de script do guard de retomada é inconclusiva, como a de um script
  ilegível: nunca `match`, nunca advisory nem bloqueio de script, também sob
  `CEO_WORKFLOW_SCRIPT_GUARD=enforce`. A comparação de `args` não muda: `args` diferentes seguem
  bloqueados sob vínculo forte. As demais regras do guard não mudam.
- `ceo-launches.py relaunch` de um registro de `scriptPath` com hash e sem snapshot sai rc 7: os
  `args` exatos, o `sha256` gravado e o estado do arquivo original contra ele são impressos, e nada
  é impresso como script exato; `relaunch --out` recusa nomeando o motivo e não cria arquivo. O
  registro de um `scriptPath` ilegível antes do despacho segue com a saída de antes (rc 7, «not
  recorded at launch»).
- Testes: o canário S357 (um arquivo com conteúdo único, dentro e fora do projeto, nomeado por
  `scriptPath` numa chamada cujo PostToolUse não vem — a chamada negada) e os vizinhos da classe
  (vínculo heurístico, nenhuma leitura nos vínculos heurístico e manual — também num registro que
  já tem snapshot —, arquivo trocado ou ilegível entre as duas leituras, id sem rótulo, `cwd` da
  chamada, `relaunch`/`--out` com e sem snapshot, guard sobre registro sem snapshot). Os testes do
  canário falham com o código anterior a este patch (evidência em `red-control.txt`; prova por
  mutação em `mutation.txt`, os dois neste diretório).
- `docs/workflow-recovery.md`: o que é gravado e quando, o validador, o rito do `relaunch` sem
  snapshot e os limites declarados abaixo.

Não mudam: as registrações do hook, o `CEO_WORKFLOW_LEDGER=0` (desliga o hook inteiro), a versão do
esquema do manifesto (`ceo.workflow-launch/v2`; o campo `script_snapshot_why` é acrescentado) e as
contagens do `verify-counts.sh` (nenhum hook, módulo `_lib`, registração ou arquivo novo de código).

## Residual declarado (pela forma)

- O PreToolUse ainda ABRE e LÊ, antes da decisão de permissão, o arquivo que `scriptPath` nomeia (o
  mesmo leitor limitado a arquivo regular de até 8 MiB), para calcular `sha256` e tamanho, e grava os
  dois no manifesto (o `sha256` também na linha do índice) com ou sem a permissão concedida depois: quem lê o
  diretório de estado pode testar um palpite do conteúdo contra o hash; numa retomada, o resultado
  do guard depende desses bytes.
- O snapshot do PostToolUse relê o CAMINHO; não é cópia do que o harness executou. Se o que o
  caminho resolve muda entre a leitura do PreToolUse, a checagem do harness e a leitura do
  PostToolUse, o snapshot pode conter bytes diferentes dos que o harness checou — sempre bytes cujo
  `sha256` é o gravado antes do despacho.
- A cura depende de o harness disparar o PostToolUse com o `tool_use_id` da chamada e o id rotulado
  só para uma chamada que ele permitiu e executou.
- Snapshots que versões anteriores deste hook gravaram no PreToolUse ficam em `launches/`: esta
  cerimônia não remove nenhum, e, enquanto um deles existir, `relaunch` do registro que o nomeia
  segue imprimindo o caminho dele como o script da chamada exata, e `relaunch --out` segue
  copiando-o para um arquivo novo; apagar um deles faz o registro que o nomeia reprovar na checagem
  de integridade (inconclusivo para o guard, rc 7 no `relaunch`).
- A classe não se esgota neste hook: outro hook que rode antes da decisão de permissão e grave no
  diretório de estado do projeto bytes do arquivo que a chamada nomeia — por exemplo, um trecho do
  conteúdo num evento de auditoria — não é tocado por esta cerimônia e segue como está.
- O comentário (`_comment`) da registração deste hook nos arquivos de settings — o do projeto e os
  templates entregues a adopters — segue dizendo que o snapshot do script é gravado antes do
  despacho; esta cerimônia não muda as registrações nem esse texto.
- O PostToolUse não serializa a releitura, a gravação do snapshot e a regravação do manifesto. Dois
  PostToolUse da mesma chamada (o hook registrado duas vezes, por exemplo), com o arquivo mudando
  entre as duas releituras, podem deixar o registro sem nomear o snapshot que um deles gravou
  (`relaunch` rc 7; comparação de script inconclusiva); uma falha ao regravar o manifesto depois de
  gravado o snapshot deixa o run sem vínculo e o snapshot em `launches/` sem registro que o nomeie.
  Nos dois casos o snapshot só tem bytes cujo `sha256` é o gravado antes do despacho.
- Os known-open do ledger que não são desta classe (declarados no GA v1.4.1 e em
  `docs/workflow-recovery.md`) seguem abertos; esta cerimônia não cura nenhum deles.

## Bateria e revisão

- O SIGN aplica o patch e confere que o blob de cada caminho tocado é o `index` pós-imagem do patch
  (os bytes que landam são os revisados) — depois de aplicar, de novo depois da bateria e, no índice,
  depois de stagear; roda os gates de corpus, os dois arquivos de teste do ledger e as suítes do
  `pytest.ini` com a divisão de marcadores do CI (`-n auto -m 'not serial'` e `-m serial`), um
  conjunto maior que o dos jobs do CI. Uma falha é rerrodada ISOLADA com o patch, até 3 vezes;
  passar em alguma é nota (instável). Se falhar nas 3, é rerrodada uma vez num worktree destacado do
  HEAD (a árvore sem o patch): se lá ela também falha (rc 1 do pytest), é nota (pré-existente) e não
  bloqueia; qualquer outro resultado sem o patch — passa, não existe, erro — reprova o SIGN. Um gate
  que reprova com o patch é rodado de novo nesse worktree: se também reprova lá, é nota
  (pré-existente); se passa, reprova o SIGN. O HEAD não pode mudar entre as pré-condições e o commit
  (conferido depois da bateria e antes do commit): o Anchor-SHA é o pai do commit.
- A assinatura é feita com `--local-user` pela chave secreta cuja impressão digital está em
  `.claude/sentinel-signers.txt` e precisa verificar contra esse allowlist (GOODSIG e VALIDSIG);
  senão o SIGN desfaz tudo.
- Rail: codex-cli 0.155.0 — o pinado quando o rail rodou — pelo `npx` (cache próprio), `codex exec
  --sandbox read-only`, sobre o patch e sobre este texto, salvo as mudanças de texto feitas depois da
  rodada 3, declaradas em `rail-round-3.md` (nenhuma muda o patch); registros
  `.claude/plans/PLAN-193/wave-fn04/rail-round-N.md`. Regra de parada
  pré-registrada: no máximo 3 rodadas. O SIGN exige que o registro da última rodada nomeie o sha256
  deste patch com veredito `APPROVE` (a rodada não relatou achado) ou `DECLARED-P2` (só P2, declarados
  no próprio registro), e vincula esse registro por hash (Rail-Record-sha256) a esta assinatura. O rail
  não revisou o script do SIGN; o ensaio dele é o harness `test-ceremony-fn04.sh` (chave GPG
  descartável, clone descartável).

## Scope

- `.claude/hooks/_lib/launch_ledger.py`
- `.claude/hooks/check_workflow_launch.py`
- `.claude/hooks/tests/test_check_workflow_launch.py`
- `.claude/scripts/ceo-launches.py`
- `docs/workflow-recovery.md`
