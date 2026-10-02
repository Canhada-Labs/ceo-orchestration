# w3b1-approved — sentinel da metade canônica da W3b.1 (PLAN-194)

> Assinatura e land em um passo: `bash .claude/plans/PLAN-194/w3b1/OWNER-W3B1-SIGN.sh`
> (confere as pré-condições, a cópia staged do arquivo canônico, o controle vermelho no HEAD e o
> último registro do rail, aplica o patch, confere que os bytes aplicados são os revisados, roda a
> bateria — as três passadas duras do pacote, os gates de corpus e as suítes do `pytest.ini` com a
> divisão de marcadores do CI —, preenche Anchor-SHA, Patch-sha256, Rail-Record-sha256 e Data no
> sentinel do HEAD, assina com a chave do allowlist de signatários, stageia o conjunto EXATO e
> commita; `--dry-run` ensaia sem assinar nem commitar). Push é decisão sua.

Plan: PLAN-194
Wave: W3b.1 e W3b.2 — metade canônica (ids da OpenAI que se aposentam, fora de `_VALID_MODELS`)
Patch: .claude/plans/PLAN-194/w3b1/w3b1.patch
Patch-sha256: 7dccad8354cc4fe0b59abf545893f6e923f19d07a08c7c5bbedad7cbe1f09773
Rail-Record-sha256: 6101d5727241db5426d2b8614a82f7659956ca1fd09713613adc6acd0da24a30
Anchor-SHA: 65cd50d7df6868ea66e9320d1e355c1f907c3748
Data: 2026-10-02

## Ratificação (Owner)

- PLAN-194, W3b, objetivo: «a lista `_VALID_MODELS` (`codex_cli_shape.py:97-105`) não aceita ids que
  aposentam». W3b.1: «remover da lista os ids que o instrumento CURADO marca; ajustar os testes».
  W3b.2: «`check-model-currency.py` com o conjunto de vermelhos esperado atualizado conscientemente».
  Controle do plano: `check-model-deprecations.py --check --today 2026-10-13` sai 1 antes e 0 depois.
- Decisão do Owner S361, Q8 (PLAN-194, «Decisões do Owner — S361»): «A W3b ocupa a vaga e landa ANTES
  da W3 (as duas tocam `codex_cli_shape.py`)».
- Base da ENTRADA dos três ids novos: o PLAN-176 §8 inventaria que «`_VALID_MODELS` rejeita o
  substituto recomendado pelo próprio registro de descontinuações»; o ledger nomeia um alvo só,
  `gpt-5.6-sol`; a página de deprecações da OpenAI dá `gpt-5.6-sol`, `gpt-5.6-terra` e
  `gpt-5.6-luna` como substitutos (`PLAN-194/LEDGER.md`, seção W3b.3). Pôr também `-terra` e `-luna`
  na tupla é escolha do builder, ratificada por esta assinatura; o repositório registra uso do `-sol`
  pelo Codex em rodadas de rail anteriores e do `-luna` numa sonda de caracterização (PLAN-156, S269,
  Codex 0.144.1), e nenhuma sonda própria do `-terra`.
- Divisão do pacote (teto do modelo de operação: 400 linhas e 8 caminhos por pacote): o escopo
  inteiro tinha 10 caminhos. A metade livre landou antes, como item livre (o commit «fix(PLAN-194
  W3b.1, metade livre)»), em 4 caminhos: o rótulo de telemetria `DEFAULT_CODEX_MODEL` de
  `optimizer/codex_phase_gate.py`, o exemplo de uso do docstring de `codex_invoke.py`, o teste do
  phase-gate e o `test_check_model_deprecations.py` (mapa de dívida de 14 para 11). Esta cerimônia
  toca 7 caminhos, 1 canônico; o `test_check_model_deprecations.py` está nas duas metades.

## O que esta cerimônia entrega, e nada além

- Em `.claude/hooks/_lib/codex_cli_shape.py`, a tupla `_VALID_MODELS` — a lista de nomes aceitos para um
  `--model` EXPLÍCITO — perde `gpt-5`, `gpt-5-mini`, `gpt-5-codex`, `o3`, `o3-mini` e `o4-mini` e ganha
  `gpt-5.6-sol`, `gpt-5.6-terra` e `gpt-5.6-luna`; `gpt-5.5` fica. Cada id que sai tem linha no
  `.claude/scripts/model-deprecations.json` (`gpt-5-codex`: desligado em 2026-07-23; `o3-mini` e
  `o4-mini`: desligamento em 2026-10-23; `gpt-5`, `gpt-5-mini` e `o3`: em 2026-12-11). O `gpt-5.5` não tem
  linha: não aparece na página de deprecações da OpenAI (fonte e leitura no `PLAN-194/LEDGER.md`,
  seção W3b.3).
- O argv padrão do rail não muda: `DEFAULT_MODEL` segue `None` e o `--model` segue omitido nos dois
  modos (`verdict` e `verdict+usage`); o rail responde com o modelo do config do Codex do usuário
  (hoje `gpt-6-astra`, pelo `~/.codex/config.toml`), como antes. Nenhum chamador de produção do
  repositório passa `--model` explícito (o `check_pair_rail.py` chama `build_verdict_argv` sem modelo; o
  `--model` do `codex_invoke.py` tem padrão `None`). Um id que saiu, pedido explicitamente, levanta
  `UnknownCodexModel` no construtor do argv, antes de chegar à API; pelo `codex_invoke.py`, a exceção
  vira veredito ADVISORY com `parse_error` que a nomeia e sai rc 1.
- Comentários do módulo: a narrativa do PLAN-142 D5 e a docstring de `UnknownCodexModel` deixam de
  citar ids desligados, sem mudar o que contam; o comentário `#:` da tupla passa a descrever os membros
  novos; um parágrafo novo diz a regra (id que o ledger aposenta não fica na tupla) e que um teste a
  cobra, sem nomeá-lo (o teste é a classe `TestAllowlistAgainstDeprecationLedger` de
  `test_codex_cli_shape.py`).
- Testes: `test_codex_cli_shape.py` ganha a classe `TestAllowlistAgainstDeprecationLedger` — a tupla
  não cruza com nenhum `model_id` ou alias do ledger; os seis ids que saíram são desconhecidos altos;
  a família `gpt-5.6-*` é aceita e emitida; o padrão segue sem `--model`. Três dos quatro testes dela
  reprovam sobre a tupla anterior; o do padrão passa nas duas, por desenho. O override explícito dos
  testes existentes passa a `gpt-5.6-sol`: de `o3` em `test_codex_cli_shape.py` e
  `test_codex_adapter.py`, e de `gpt-5-codex` em `tests/unit/test_codex_token_telemetry.py` (o teste da
  ordem redação → argv do ADR-114, que segue provando a mesma ordem).
- `test_check_model_deprecations.py`: o mapa de dívida declarada `W3B1_DECLARED_DEBT` fica vazio (os 11
  acertos que restavam em `codex_cli_shape.py`), e `check-model-deprecations.py --check --today
  2026-10-13` sai 0 na árvore (saía 1).
- W3b.2: em `.claude/data/model-currency-expected-reds.txt` sai o `gpt-5.6-sol`, o vermelho que vinha da
  tupla não cobrir o alvo de migração do ledger; o conjunto esperado vai de 7 para 6 de propósito, e a
  causa da redução fica escrita no próprio arquivo. `test_check_model_currency.py` acompanha (7 → 6).

## Residual declarado (pela forma)

- A tupla é uma lista de NOMES, não uma garantia de disponibilidade: um id que fica (inclusive os da
  família `gpt-5.6-*`) pode não ser servido por uma dada conta, ou por um Codex CLI anterior ao 0.143
  (a versão em que a família 5.6 entra como primeira classe, pela pesquisa S266 do PLAN-156; num
  adopter o pin do CLI resolve como infraestrutura, aberto); nesse
  caso a chamada explícita segue virando erro e ADVISORY (fail-open), como antes.
  `CODEX_CLI_TARGET_VERSION` segue `0.139.0`, constante informativa e desatualizada (PLAN-176 §8), fora
  deste pacote.
- O cruzamento com o ledger só enxerga o que o ledger tem: a página da OpenAI lista ids que o ledger não
  carrega (backlog declarado no `PLAN-194/LEDGER.md`, seção W3b.3); um id que se aposente sem linha no
  ledger não deixa o teste novo vermelho.
- O `gpt-6-*` (o modelo do config do Codex do usuário hoje) não entra nesta cerimônia: a recomendação
  do plano (decisão pendente 5 do Owner) o põe em `_VALID_MODELS` no pacote 2 da W3, junto do argv com
  modelo e esforço fixos.
- O rótulo `codex_model` do evento `codex_review_invoked` (metade livre) é um rótulo fixo, não o modelo
  que respondeu; esta cerimônia não muda isso.
- `CLI_SHAPE_VERSION` segue `1.0.0`: o módulo manda subir a versão quando a superfície de FLAGS muda, e
  ela não muda.
- Fora desta cerimônia: `docs/rotation-log.md` ainda manda o operador rodar `codex exec --model` com um
  id já desligado (prosa, sem chamador); a troca é backlog livre. Também fora: a nota
  `_meta.openai_rows_refreshed` do `.claude/scripts/model-deprecations.json` diz que um alvo por faixa
  (`-terra`/`-luna`) acrescentaria vermelhos ao `check-model-currency.py`; com a família na tupla isso
  deixa de valer (vai junto do refresh do ledger da OpenAI com substitutos por faixa — backlog no
  `PLAN-194/LEDGER.md`, seção W3b.3).
- Pela forma: o texto novo do patch chama de «retired» (no passado) ids que, em 2026-10-02, só se
  aposentam em 2026-10-23 ou 2026-12-11 (só o desligamento de 2026-07-23 já passou). A forma aparece em
  três sítios: o parágrafo novo de `codex_cli_shape.py`, a docstring do teste do adapter
  (`test_codex_adapter.py`, sobre o `o3`) e o parágrafo final de
  `.claude/data/model-currency-expected-reds.txt`. É imprecisão de tempo verbal em comentário e
  docstring, sem efeito no código, mantida porque o patch está congelado desde a rodada 1; cada sítio é
  corrigido na próxima edição do seu arquivo — o módulo no pacote 2 da W3; o teste do adapter e o
  arquivo de vermelhos esperados na próxima onda que tocar cada um (para o de vermelhos esperados, o
  mapa de colisões do plano aponta a W5c).
- Com a base vermelha no `validate-governance`, um detalhe que traga o caminho absoluto da árvore
  difere entre a árvore viva e o worktree da base e reprova por ruído (falha FECHADA): a comparação não
  normaliza caminhos.

## Bateria e revisão

- O SIGN confere, antes de aplicar, que o patch só MODIFICA conteúdo de arquivo existente (cria, remove,
  renomeia, copia ou muda modo ⇒ recusa nomeada), que a cópia staged
  (`w3b1/staged-w3b1/.claude/hooks/_lib/codex_cli_shape.py`) tem o blob da pós-imagem que o patch declara
  para o arquivo canônico e que o controle (`check-model-deprecations.py --check --today 2026-10-13`)
  REPROVA no HEAD (rc 1 com a linha `SUMMARY: breaks=` do próprio script e acertos BREAK+WARN; uma
  exceção, que também sai rc 1, não conta). Aplica o patch e confere que o blob de cada caminho tocado é o `index` pós-imagem do
  patch — depois de aplicar, de novo depois da bateria e, no índice, depois de stagear, junto do estado
  (cada caminho do patch e o sentinel como modificação, a `.asc` como arquivo novo, sem detecção de
  rename) e do modo, que segue o do HEAD e é 100644 para tudo o que entra. A árvore desse índice
  conferido é gravada (`git write-tree`) logo antes do commit; depois dele, a árvore commitada
  (`HEAD^{tree}`) tem de ser ela e o pai, o Anchor-SHA — o que cobre a `.asc`, os modos e todo caminho;
  se um hook mudou o commit, ele é desfeito com `reset --soft` para o Anchor-SHA e o SIGN aborta. A
  pré-imagem pinada exige a metade livre no HEAD.
- Bateria: `py_compile`; três passadas DURAS, que reprovam o SIGN em qualquer rc ≠ 0 com o patch, sem
  julgamento de pré-existente — o controle acima (com o patch: rc 0, `SUMMARY: breaks=0 warns=0` e
  `LIVE-BREAKS-REMAINING: 0` na última linha; o rc 0 sozinho também é o caminho fail-open do script),
  `check-model-currency.py --expected-reds` e os cinco arquivos de teste do pacote; os gates de corpus
  (o `validate-governance` julgado pela saída inteira — cabeçalho, detalhe de cada violação e contagem,
  fora as linhas de aviso, reconhecidas pelo prefixo com que o próprio script as emite e nunca por
  substring, e fora a linha `Repo:`, com espaços normalizados — com e sem o patch, e uma execução sem o
  resumo `Errors:` reprova); e as suítes do `pytest.ini` (os `testpaths`) com a divisão de marcadores
  do CI (`-n auto -m 'not serial'` e `-m serial`). Essas suítes contêm as três raízes que coletam os
  caminhos do pacote (`.claude/hooks/tests`, `.claude/scripts/tests` e `tests/unit`); o CI roda ainda
  raízes que os `testpaths` não contêm, que a bateria não roda e que não referenciam esses caminhos.
  Nas suítes, uma falha é rerrodada ISOLADA com o patch, até 3 vezes; passar em alguma é nota
  (instável). Se falhar nas 3, é rerrodada uma vez num worktree destacado do HEAD (a árvore sem o
  patch): se lá ela também falha (rc 1 do pytest), é nota (pré-existente) e não bloqueia; qualquer outro
  resultado sem o patch reprova o SIGN. Um gate de corpus (fora o `validate-governance`, julgado pela
  saída inteira) que reprova com o patch é rodado de novo nesse worktree: se também reprova lá, é nota;
  se passa, reprova o SIGN. O HEAD não pode mudar entre as
  pré-condições e o commit: o Anchor-SHA é o pai do commit.
- O texto que se assina é o deste arquivo no HEAD, com os quatro campos preenchidos: o SIGN recusa se o
  arquivo vivo mudar durante a bateria, e depois do stage confere que o blob do índice é o assinado e
  reverifica a assinatura sobre o conteúdo do índice.
- A assinatura é feita com `--local-user` pela chave secreta cuja impressão digital está em
  `.claude/sentinel-signers.txt` e precisa verificar contra esse allowlist (GOODSIG e VALIDSIG); o
  allowlist e a biblioteca de verificação são as do HEAD, lidas no P0; senão o SIGN desfaz o que
  aplicou.
- Rail: `codex exec --sandbox read-only` sobre o patch e sobre este texto, com refutadores Claude na
  mesma rodada; registros `.claude/plans/PLAN-194/w3b1/rail-round-N.md`. Regra de parada pré-registrada:
  no máximo 3 rodadas. O SIGN exige que o registro da última rodada nomeie o sha256 deste patch e o
  sha256 deste texto no HEAD (com os quatro campos por preencher), que a linha Rail-Reviewer-Verdict seja
  a última linha `VERDICT:` da saída verbatim do revisor — lida pela gramática estrita do registro:
  exatamente uma seção `## Saída do revisor` e, nela, exatamente um bloco que abre numa linha igual a
  três crases seguidas de `text` e fecha na próxima linha igual a três crases, lido inteiro (um título
  dentro dele não encerra a seção; uma linha de cerca a mais, inclusive indentada, é recusada); seção
  ou cerca ausente, duplicada, mal formada ou não fechada é recusada com o motivo nomeado —, e
  veredito `APPROVE` (revisor `GO`) ou
  `DECLARED-P2` (revisor `GO` ou `GO-WITH-CONDITIONS`); vincula esse registro por hash
  (Rail-Record-sha256) a esta assinatura. O rail não revisa o script do SIGN; o ensaio dele é o harness
  `test-ceremony-w3b1.sh` (chave GPG descartável, clone descartável).

## Scope

- `.claude/data/model-currency-expected-reds.txt`
- `.claude/hooks/_lib/codex_cli_shape.py`
- `.claude/hooks/tests/test_codex_adapter.py`
- `.claude/hooks/tests/test_codex_cli_shape.py`
- `.claude/scripts/tests/test_check_model_currency.py`
- `.claude/scripts/tests/test_check_model_deprecations.py`
- `tests/unit/test_codex_token_telemetry.py`
