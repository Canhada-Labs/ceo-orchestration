---
round: 1
archetype: DevOps Engineer
skill: devops-ci-cd
agent_persona: DevOps & Platform Engineer (Principal)
generated_at: 2026-09-02T16:20:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- O plano acerta o diagnóstico (herança de modelo, não política) e acerta a ordem da W4
  (Validate como prova do padrão antes do Smoke). A pré-condição que ele escreveu para
  matrizar — «nenhum estado partilhado via `GITHUB_ENV`/artifacts» — está **satisfeita e é
  a pergunta errada**: `grep` nos dois workflows dá ZERO ocorrências de `GITHUB_ENV`,
  `GITHUB_OUTPUT`, `upload-artifact`, `download-artifact` e `actions/cache` (o único `id:`
  é `docs_freshness`, em `validate.yml:1054`). O estado partilhado real é outro: toolchain
  instalado no meio do job, estado do `.git` do workspace (tags + unshallow), semântica de
  `fail-fast`, e o NOME do job como nome de check.
- A alavanca de CI é real, mas o corte de −43 %/−55 % é medido na grandeza errada e o
  risco de falso-verde é maior do que o plano registra. Três classes silenciosas: matriz
  nasce `fail-fast: true` (reverte os 17 `if: always()` do Smoke), o split pode perder um
  dos dois passes de pytest (`not serial` / `serial`) sem ficar vermelho, e a ordem
  `fetch tags` → `deepen` → e2e é fail-closed por um guard que precisa viajar para CADA leg.
- A sonda de concorrência não sustenta a conclusão que a proposta já registrou na OQ-4.
  n=1 por N contra um AC que exige 3/3, detector de `429` sem controle positivo, tarefa de
  output ~zero, e a pergunta do Owner (dois terminais) explicitamente não testada. E o
  canal entre terminais não tem hook nenhum hoje — nem prova de que seja hookável.

## Risks

- **R-DEV1 — CRITICAL — `strategy: matrix` nasce com `fail-fast: true`.**
  `smoke-install.yml` carrega **17** `if: always()` (contei; o relatório 04 diz «8 dos
  steps» — número velho). Eles existem porque um step vermelho fazia os posteriores virarem
  `skipped` (lição §9.8/PLAN-183). Matrizar com o default CANCELA os legs irmãos ao primeiro
  vermelho, e leg cancelado reporta `cancelled` — a assinatura que este repo já confundiu
  com estouro de timeout num step inocente. A cura vira o achado.
  *Mitigação:* `fail-fast: false` explícito em toda matriz nova (as duas matrizes existentes
  em `validate.yml:1577` e `1612` já fazem isso — copiar o padrão da casa), mais um gate de
  FORMA no `validate.yml` que parseia os workflows e reprova qualquer `strategy.matrix` sem
  `fail-fast: false`.

- **R-DEV2 — HIGH — nome de job é nome de check, e a regra server-side não está em git.**
  O job é `validate:` com `name: Governance, health, contamination, shellcheck`
  (`validate.yml:29-30`), e esse literal aparece como check requerido em
  `docs/BRANCH-PROTECTION.md:104` e em `templates/docs/BRANCH-PROTECTION.md:44` — o template
  é ENTREGUE a adopters pela rota de entrega do PLAN-183 D1/D3. Splitar o job renomeia ou
  multiplica checks. Se a proteção server-side for ativada (Path A) apontando para um nome
  que sumiu, o PR fica pendente para sempre ou o gate desaparece em silêncio; e reverter o
  YAML não desfaz configuração server-side — esse botão de rollback não existe.
  *Mitigação:* o job base preserva `name:` byte a byte e os jobs novos entram AO LADO; os
  DOIS BRANCH-PROTECTION são atualizados no MESMO patch; a lista de checks requeridos passa
  a viver num arquivo versionado que o `docs-as-code freshness` já sabe cobrar.

- **R-DEV3 — HIGH — o split pode perder metade da suíte e ficar verde.**
  Cada suíte roda em DOIS passes: `pytest ... -n auto -m 'not serial'` e depois
  `pytest ... -m 'serial'` (`validate.yml:454-462`, `539-551`, e idem nas duas matrizes).
  Copiar um pass e esquecer o outro é uma edição de uma linha que não produz vermelho
  nenhum. O próprio relatório 04 diz que «nenhum teste de matriz correta existe».
  *Mitigação:* baseline versionado do conjunto de node-ids (`pytest --collect-only -q` por
  raiz) e um gate que compara a UNIÃO dos jobs novos contra o baseline do monolito.
  Verificação por CONJUNTO, não por `grep` — a lição C3 do PLAN-183 é exatamente que uma
  rota apontando para fonte errada-mas-existente manteve 10 testes verdes.

- **R-DEV4 — HIGH — o estado partilhado do `validate` é o TOOLCHAIN, não `GITHUB_ENV`.**
  `Set up Python for hook tests` fixa **3.12** e `Install pytest + PyYAML + pytest-xdist`
  rodam em `validate.yml:443-451` — ou seja, os ~40 steps anteriores usam o `python3`
  default do runner e só os três blocos caros veem o 3.12 com deps. Um split que não
  replicar setup + `pip install` roda o bloco caro noutra versão de Python: verde, com
  cobertura diferente da que o gate afirma ter.
  *Mitigação:* cada job novo declara a MESMA versão e o MESMO `pip install`; e o
  `echo "Python version: ..."` que já existe vira ASSERT (falha se não for 3.12).

- **R-DEV5 — HIGH — a sonda de concorrência não sustenta «sem rate limit até 14».**
  Cinco furos, todos verificáveis no próprio `w0/concurrency-probe-S339.md`: (a) n=1 por
  célula, contra o AC-2 do plano que exige 3/3; (b) o detector de `429` não tem controle
  positivo — «0 erros» é ausência de sinal num instrumento que ninguém viu morder, e a
  doutrina do repo é que ausência de resultado não é prova; (c) a tarefa é três comandos
  Bash com output ~zero, enquanto o limite de assinatura é por tokens/minuto, não por
  contagem de agentes — o pior caso (builder com output longo) está fora da amostra;
  (d) a subida de 5 s para 11 s é confundida entre fila do cap local, latência de API sob
  carga e backoff interno silencioso: as três desenham a mesma curva; (e) dois workflows em
  terminais distintos — a pergunta 3 do Owner — está listado como NÃO testado nas próprias
  limitações da sonda, mas a proposta já registra a OQ-4 como respondida.
  *Mitigação:* 3 repetições por N, controle positivo do detector, uma célula de output alto,
  e uma célula de dois terminais × N. Até lá a OQ-4 fica ABERTA no texto da proposta.

- **R-DEV6 — MEDIUM-HIGH — a matriz do Validate roda em runner PAGO com teto já apertado.**
  `Ceo` é larger runner 8-core pago por budget de org. Num `push`, o Validate já sobe SETE
  VMs `Ceo` — `validate`, `integration-tests`, `formal-verification-mutation-harness`,
  `hook-tests-dual-rail` (2) e `hook-tests-python-matrix` (2 no `push`, por causa do corte
  A0 do PLAN-184) — mais o `coverage.yml`, que também é `Ceo`. A W4 leva a dez. O corte A0
  existe para caber num teto diário declarado; a W4 come essa folga. E o modo de falha por
  budget estourado não é degradação: TODOS os workflows, inclusive `ubuntu-latest`, falham
  em 2-3 s com zero steps, o que se parece com bug de código.
  *Mitigação:* a W4 publica o delta de runner-minutos MEDIDO antes do flip e o land é gated
  contra o teto do PLAN-184. Jobs novos só vão para `Ceo` se o `-n auto` justificar; o gate
  de perf continua onde está.

- **R-DEV7 — MEDIUM — matrizar o Smoke joga fora o ledger de medição do `timeout-minutes`.**
  `smoke-install.yml:196-296` são cem linhas de derivação aditiva do 126 — cada bump com a
  medida que o produziu, o fator de runner e a margem anti-flake. É a memória institucional
  do repo sobre dimensionamento. Quinze legs precisam de quinze timeouts; copiar 126 em cada
  um piora a classe «`cancelled` num step inocente» em vez de curá-la.
  *Mitigação:* mapear cada leg ao seu tempo medido no run 33582381725 (os deltas por step
  estão no relatório 04) e dimensionar por leg com a mesma margem; preservar o bloco de
  comentários como ledger, não apagá-lo na reescrita.

- **R-DEV8 — MEDIUM — a ordem `fetch tags` → `deepen` → e2e é uma dependência FAIL-CLOSED que
  precisa viajar para cada leg.** `Fetch the parity pin tag` lê o pin do próprio teste
  (`--print-pin`) e busca `refs/tags/v*`; `Deepen git history` faz `--unshallow` (503 commits,
  43 MB) e sai 1 se `gens < 2` de `templates/docs/BRANCH-PROTECTION.md`. Sem os dois, o
  classificador reporta `STALE 3` em vez de `STALE 0` — seguro, mas CEGO: nunca entrega bytes
  errados, apenas não enxerga. Um leg de matriz que esqueça o bootstrap nasce raso e verde,
  que é literalmente o defeito S327b de volta. E o custo passa a 15× unshallow, 15× fetch de
  tags, 15× `sudo apt-get` do jq e 15× `setup-python`.
  *Mitigação:* um composite action único (`.github/actions/smoke-bootstrap`) com checkout +
  tags + unshallow + guard `gens>=2` + jq + python, e um gate que asserta que TODO job da
  matriz o usa.

- **R-DEV9 — MEDIUM — `Gate-scripts integrity` (ADR-192) deixaria 14 legs sem verificação.**
  Hoje o `shasum -c` do manifesto roda UMA vez, primeiro, antes de qualquer membro ser
  invocado (`smoke-install.yml:314-327`). Em matriz, se ficar num leg só, os outros executam
  scripts de gate não verificados.
  *Mitigação:* entra no composite bootstrap do R-DEV8; custa segundos.

- **R-DEV10 — HIGH — «rollback com um botão» não existe na W3, e o plano não diz isso.**
  W1 e W4 revertem por `git revert`. W3 é camada T Owner-signed: desfazer o pin dos cinco
  VETO exige uma cerimônia GPG NOVA, com sentinel, rail e assinatura — dias, não um botão.
  *Mitigação:* durante a transição, `VETO_FLOOR_ALLOWED` aceita os DOIS ids
  (`claude-fable-5` e `claude-fable-5-1`), de modo que o rollback vire mudança de settings e
  não violação de piso; e o sentinel da W3 declara verbatim o valor anterior de cada pin.

- **R-DEV11 — HIGH — a W1 propõe um gate bloqueante sem rota de recuperação nomeada.**
  «O dispatcher passa a EXIGIR `model` no spawn (advisory por 30 dias, depois bloqueante)».
  Todo gate bloqueante deste repo tem uma saída nomeada: `CEO_SOTA_DISABLE=1`,
  `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED` (ainda UNSET, janela measure-first),
  `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1`, `CEO_SENTINEL_UNLOCK`. Sem isso, um falso positivo no
  dispatcher trava a sessão sem escape.
  *Mitigação:* nascer como emissão VISÍVEL (`spawn_model_recorded`, com `model=''` na
  omissão), flip por `CEO_SPAWN_MODEL_REQUIRED=1`, e a mesma tabela would-block/TP-FP que o
  PLAN-178 exigiu antes de considerar o flip.

- **R-DEV12 — HIGH — o canal entre terminais não tem cobertura de hook, e a hookabilidade não
  foi provada.** Verifiquei: `SendMessage` e `ListAgents` não aparecem em NENHUM matcher de
  `.claude/settings.json` nem em `.claude/hooks/` fora de testes. O matcher mais largo
  (`check_anti_ceo_overhead`) enumera `Agent|Bash|Edit|Write|MultiEdit|Read|Glob|Grep|WebFetch|WebSearch|NotebookEdit|TodoWrite|Task|mcp__.*` — e não os inclui. Pior: o
  precedente do repo é que nem tudo é interceptável — `agent()` de Workflow NÃO passa pelo
  `check_agent_spawn` (probe `wf_d7af49d9`, `blocked=false`, limite do substrato).
  *Mitigação:* a W5-US3 COMEÇA por uma sonda de interceptação (o PreToolUse dispara para
  `SendMessage`? um payload plantado é bloqueado?) antes de desenhar qualquer rail. Se não
  dispara, a resposta à OQ-5 é «doutrina + emissão voluntária», e isso tem de estar escrito.

- **R-DEV13 — HIGH — depois do PLAN-182 a troca entre terminais é inauditável por
  construção.** A cadeia HMAC é POR PROJETO, com chave e salt próprios. Uma troca entre dois
  repos deixa o evento do emissor num arquivo e o do receptor noutro, assinados por chaves
  diferentes: não existe cadeia que contenha os dois lados, logo «A pediu, B fez» não é
  verificável. Isso é exatamente a superfície onde permission laundering vive — um peer
  fazendo o que foi negado na sessão do outro.
  *Mitigação:* reusar a forma que o repo já tem para o problema idêntico — o
  `fed_correlation_id` da superfície de federação (SPEC v2.27+). Emitir nos DOIS lados
  `peer_message_sent` / `peer_message_received` com `{correlation_id, sender session_id,
  sender project slug, receiver name, sha256 do corpo}` — o HASH, nunca o corpo — e, o campo
  que decide tudo, o VEREDITO local do receptor: `acted | refused-by-policy | ignored`. Sem
  registrar a RECUSA, laundering e cooperação legítima são indistinguíveis no log.

- **R-DEV14 — MEDIUM — a matriz papel × modelo não cobre quem escreve o YAML da W4.**
  `.github/workflows/**` é «livre» no sentido de cerimônia, então cai na linha «builder
  livre / docs» em Sonnet 5. Mas os defeitos desta wave são semânticos e mudos:
  `fail-fast` default, nome de check, um pass de pytest a menos. Um refutador só pega isso
  se souber a semântica do Actions — não é uma revisão de texto.
  *Mitigação:* `.github/workflows/**` entra explicitamente na linha «builder canônico»
  (Opus 5, `max`) mesmo sem cerimônia GPG; `actionlint` e
  `check-action-sha-drift.py --offline`, que já rodam no `validate`, seguem como rede — e os
  jobs novos precisam do MESMO SHA pinado de `actions/checkout` e `actions/setup-python`,
  senão o gate C12 reprova.

- **R-DEV15 — LOW-MEDIUM — o AC-6 mede a grandeza errada.** «Validate ≤ 14 min» derivado do
  maior job ignora provisionamento: hoje o run inteiro leva 23m27s contra 22m22s do maior
  job, ~65 s de overhead com sete VMs `Ceo`. Larger runners sobem VMs sob demanda e a UI do
  próprio GitHub avisa que mudanças levam de 30 a 60 min para propagar; com dez VMs esse
  delta cresce e não aparece na soma dos jobs.
  *Mitigação:* AC-6 medido em `startedAt`→`completedAt` do RUN, em 3 runs verdes, e no
  mesmo evento (`push`) — a matriz de Python difere entre `push` e `pull_request`.

## Must-fix (blocking)

1. `fail-fast: false` explícito em toda matriz nova, mais um gate de forma no `validate.yml`
   que reprova `strategy.matrix` sem ele. (R-DEV1)
2. Teste de «matriz correta» ANTES do flip: baseline versionado de node-ids por
   `--collect-only` e comparação da UNIÃO dos jobs novos contra o baseline do monolito,
   cobrindo os dois passes `not serial` / `serial`. (R-DEV3)
3. Composite action de bootstrap para o Smoke — checkout, fetch do pin e das tags,
   `--unshallow` com o guard `gens>=2`, `Gate-scripts integrity`, jq e setup-python — com
   gate que asserta que TODO leg da matriz o usa. (R-DEV8, R-DEV9)
4. O job base do Validate preserva `name: Governance, health, contamination, shellcheck`
   byte a byte; `docs/BRANCH-PROTECTION.md` e `templates/docs/BRANCH-PROTECTION.md` são
   atualizados no MESMO patch, e a lista de checks requeridos passa a ser versionada. (R-DEV2)
5. Cada job novo do Validate replica `setup-python 3.12` e o `pip install` de
   pytest/PyYAML/pytest-xdist, com assert de versão no step. (R-DEV4)
6. A W4 não landa sem o delta de runner-minutos MEDIDO e comparado ao teto diário que o
   PLAN-184 A0 estabeleceu. (R-DEV6)
7. O enforce da W1 nasce com rota de recuperação nomeada (`CEO_SPAWN_MODEL_REQUIRED`, UNSET
   por padrão) e janela measure-first com tabela would-block/TP-FP. (R-DEV11)
8. A W3 mantém os DOIS ids aceitos no piso de VETO durante a transição, para que o rollback
   seja mudança de settings e não uma segunda cerimônia GPG. (R-DEV10)
9. AC-2 cumprido antes de qualquer citação do teto: 3 repetições por N, controle positivo do
   detector de `429`, uma célula de output alto e uma de dois terminais. Até lá a OQ-4 volta
   a ABERTA no texto da proposta. (R-DEV5)
10. A W5-US3 começa por sonda de interceptação de `SendMessage`/`ListAgents`; o desenho do
    rail só existe depois de saber se o PreToolUse dispara. (R-DEV12)
11. O evento de coordenação carrega correlation id emitido nos DOIS projetos, hash do corpo
    em vez do corpo, e o veredito local do receptor incluindo `refused-by-policy`. (R-DEV13)

## Nice-to-have (advisory)

1. Timeouts por leg derivados dos deltas medidos no run 33582381725, preservando o bloco de
   comentários do `smoke-install.yml` como ledger de medição.
2. AC-6 medido no nível do RUN e no mesmo evento, não na soma ou no maior job.
3. `.github/workflows/**` roteado para builder canônico (Opus 5, `max`) na matriz da W1.
4. Registrar mecanicamente qual braço do A/B esteve ativo em cada janela de 5 h — sem isso a
   W2 não é reconstruível depois, e a alternância é feita à mão em `settings.local.json`.
5. Manter os filtros de path `push` e `pull_request` idênticos e NÃO introduzir filtro por
   leg: o comentário «KEEP IDENTICAL» documenta um buraco já pago uma vez.
6. Repetir no plano da W4 que o gate de perf (`opus-4-7-profiler-smoke`) permanece em
   `ubuntu-latest` — os budgets p95/p99 são calibrados para 2 cores.
7. Rail dual-track (patch ∥ materiais) do item 11 do §7: concordo, é baixo risco, mas as duas
   tracks precisam de árvores fisicamente distintas e de commit antes da rodada seguinte.

## Unseen by the original plan

1. `fail-fast: true` é o DEFAULT de `strategy.matrix` e reverte, sozinho, a doutrina dos 17
   `if: always()` do Smoke.
2. Nome de job é nome de check requerido, está documentado em dois arquivos e um deles é
   ENTREGUE a adopters; e configuração server-side não volta com `git revert`.
3. O padrão de dois passes `not serial` / `serial` é o ponto exato onde o split perde
   cobertura sem ficar vermelho.
4. O estado partilhado do `validate` não é `GITHUB_ENV` (que não existe no arquivo): é o
   toolchain instalado no meio do job e o estado do `.git` do workspace.
5. Depois do PLAN-182, coordenação entre terminais é inauditável por construção — cadeias
   por projeto, chaves distintas, nenhum correlator. O plano pede «evento de auditoria» sem
   notar que ele cai em duas cadeias que não se falam.
6. Nada garante que `SendMessage` seja interceptável; o precedente do Workflow diz o
   contrário para um canal análogo.
7. O `Gate-scripts integrity` do ADR-192 hoje protege o job inteiro por rodar primeiro; em
   matriz ele protege um leg só, salvo replicação explícita.
8. Rollback da W3 não é um botão — é outra cerimônia GPG.
9. As cem linhas de derivação do `timeout-minutes: 126` são conhecimento medido que uma
   reescrita por matriz apaga.
10. A W4 cria um papel novo — autor de YAML de CI — que a matriz papel × modelo não endereça.
11. Budget de Actions estourado derruba TODOS os workflows com zero steps em 2-3 s, inclusive
    os de `ubuntu-latest`; a W4 aumenta a exposição a uma falha de infra que se parece com
    bug de código.
12. Números do relatório 04 já envelheceram (diz 8 `if: always()`; hoje são 17) — a W4 deve
    re-medir antes de citar.

## What I would NOT change

1. **Não paralelizar o V-block do LAND.** Concordo integralmente e acrescento um motivo: o
   `trap`/`restore` foi endurecido por 5+ rodadas de rail sobre a ordem sequencial, e o ganho
   é de dezenas de segundos contra a reabertura da classe de corrida na cadeia HMAC viva.
2. **Validate antes de Smoke na W4.** Provar o padrão no workflow que já pratica seis jobs
   paralelos, e só então reescrever o de 26 steps, é a sequência certa.
3. **`concurrency: cancel-in-progress: true` nos dois workflows.** Manter como está.
4. **Os filtros de path duplicados do Smoke com o comentário «KEEP IDENTICAL».** A duplicação
   é deliberada e o comentário explica o buraco que ela fecha.
5. **O gate de perf em `ubuntu-latest`.** Não roteie para `Ceo`.
6. **Não decidir o assento por dólar — medir.** A diferença de US$ 318/mês está dentro da
   margem da própria hipótese de split; a moeda que distingue é quota e ela não tem número
   publicado. Mesma disciplina que peço para o CI.
7. **Os dois passes de pytest e o `-n auto`.** O split serial existe por causa de testes de
   wall-clock; manter a forma, replicá-la, nunca simplificá-la na reescrita.
8. **Fail-open em infraestrutura, fail-closed em input.** Nada nesta wave deve virar exceção
   a essa regra — em particular, o rail de coordenação entre terminais observa antes de
   bloquear.
