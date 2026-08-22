---
plan: PLAN-184
round: 1
rounds_synthesized: [round-1]
agents_considered: [Critic-A, Critic-B]
synthesized_at: 2026-08-21
synthesized_by: CEO
verdict: ADJUST_PROCEED
plan_status_after: draft (o flip para `reviewed` e do Owner)
---

# PLAN-184 — sintese do debate, round 1

> **Metodo.** As criticas chegaram anonimizadas (`Critic-A` / `Critic-B`,
> personas removidas — DEBATE-SCHEMA §13.2). Toda claim abaixo foi
> reverificada contra o disco antes de entrar aqui; onde a critica errou,
> o pushback esta registrado com o comando que o sustenta. Nenhum numero
> nesta sintese veio de memoria.
>
> **⚠️ Limitacao declarada do INPUT desta sintese (nao e achado do
> debate — e um fato sobre o material que chegou ao sintetizador).**
> O payload de criticas recebido carregava **dois** rotulos, `Critic-A`
> (8 itens) e `Critic-B` (8 itens), e **terminou TRUNCADO no meio do
> ultimo item do `Critic-B`** — a frase corta em *"E \"re-run\" e"* e o
> array JSON nunca fecha. Consequencias, declaradas em vez de
> silenciadas: (i) o item P2 final do `Critic-B` foi sintetizado **so
> ate onde era legivel**, e a parte faltante foi **reconstruida por
> verificacao independente contra o disco** (`grep workflow_dispatch`,
> `coverage.yml:18`), nao por adivinhacao do texto cortado — ele
> convergiu com o P2 do `Critic-A`, e e o achado **C1**; (ii) **se
> houve um terceiro critico a montante, ele NAO chegou aqui.** Uma
> sintese que reivindicasse cobertura completa sobre input truncado
> seria exatamente a classe que este repo caca (*instrumento verde cuja
> pergunta envelheceu*), entao o escopo real fica escrito: **esta
> sintese cobre 16 itens de 2 rotulos, um deles parcial.**

## Veredito

**ADJUST_PROCEED.** Seis achados P0 sobreviveram a verificacao. **Nenhum
deles e sem cura obvia** — todos foram curados no corpo do plano nesta
rodada, e por isso o veredito nao e BLOCK. O que muda de status e o
*peso* do numero que autoriza o plano: a manchete de economia passa a
`NAO-DERIVADA` ate a reconciliacao da nova W0-US5.

O que **nao** mudou, e e a razao de o plano seguir vivo: a direcao. Que
77,7% do custo do runner pago cai em commits que nao tocam codigo e um
fato da atribuicao por bucket da medicao, e ele sobrevive nas **duas**
bases de custo (US$ 194 na base medida, US$ 153 na base da tabela por-job
— A1 continua sendo o termo dominante em qualquer leitura).

O plano permanece `status: draft`. O flip para `reviewed` e do Owner, e
depende das 5 novas Open questions (OQ-6..OQ-10).

---

## Achados por severidade

### P0

| # | Achado | Critico(s) | Estado |
|---|---|---|---|
| C5a | Tres bases de tempo sem regra de normalizacao (21d medido / "/mes" projetado / 7d confirmado). O gate ">20% reabre" do AC-6 dispara pelas UNIDADES. | A | **CONFIRMADO** |
| S2 | A manchete US$ 194 nao e reproduzivel a partir da tabela por-job do proprio plano; sobram 1.884,6 min entre os dois buckets. | A | **CONFIRMADO** |
| S1 | W0-US3 e insatisfazivel sob a restricao read-only que a propria W0 declara — gate circular. | A | **CONFIRMADO** |
| S5 | A prova de inercia (b) nao detecta o modo de falha que a §4 nomeou: o detector e de EXISTENCIA, mutacao de conteudo deixa verde. | B | **CONFIRMADO (probe ao vivo)** |
| C2b | A classe MISTA (67/239 = 28% dos commits da janela) nao e exercitada por nenhum AC. | B | **CONFIRMADO (com correcao de enquadramento)** |
| C3b | Interacao `paths` x `concurrency`: na Rota B, push so-docs cancela o run pesado em voo do push de codigo anterior. | B | **CONFIRMADO (fatos locais)** |

### P1

| # | Achado | Critico(s) | Estado |
|---|---|---|---|
| C2a | O Check da W1 exige so o gatilho `push`; `pull_request` pode sumir no split sem nenhum AC pegar. | A | **CONFIRMADO** |
| C3a | Na Rota C o Check exige `concurrency.group` distinto mas nunca `cancel-in-progress: true` — com o default (`false`), minutos SOBEM nos pushes de codigo. | A | **CONFIRMADO** |
| C4a | Rota C quebra o badge de CI do README e deixa ADR-021/ADR-050 stale; nenhum dos tres e vigiado. | A | **CONFIRMADO** |
| C4b | GOVERNANCE-MAP.md precisa de linha nova e nao e vigiado. | B | **CONFIRMADO, com numero corrigido (ver pushback P2)** |
| S4 | `permissions:` ausente da lista de boilerplate; `integration-tests` e o unico dos 4 sem bloco proprio — herda do nivel do workflow. | A | **CONFIRMADO** |
| S6 | `paths-ignore` tem ZERO precedente in-repo; 11 workflows ja combinam `push:` + `paths:`; 13 gates VIVOS deste repo sao allowlists que a §3 condena. | B | **CONFIRMADO** |
| S7 | Regra de timeout (`medido/timeout <= 0,80`, N=2/N=3) e MAIS FRACA que o metodo que o proprio repo pratica no job analogo. | B | **CONFIRMADO** |
| S8 | Troca de runner pode virar SKIP silencioso; AC-5 aceita "verde" como prova. | B | **CONFIRMADO (classe existe)** |
| S9 | Nada exige que o workflow pesado novo dispare sobre si mesmo; `.github/**` PASSARIA na prova de inercia (b). | B | **CONFIRMADO** |
| S3 | Inventario errado: `validate.yml` tem SETE jobs, nao "5". | A | **CONFIRMADO** |

### P2

| # | Achado | Critico(s) | Estado |
|---|---|---|---|
| C1 | A rota de recuperacao nomeada (`workflow_dispatch` ou re-run) nao funciona em nenhum dos dois ramos. | A + B | **CONFIRMADO, com correcao de enquadramento (pushback P1)** |

---

## Onde 2+ criticos convergiram (o PROTOCOL obriga ajuste)

### C1 — A rota de recuperacao nomeada nao funciona em nenhum dos dois ramos

Os dois criticos chegaram aqui por caminhos diferentes. Verificado:

```
$ grep -n "workflow_dispatch" .github/workflows/validate.yml
(none)
```

- **Ramo C:** um push filtrado nao produz run algum. Nao ha o que
  "re-rodar" — a rota de recuperacao por re-run e vacua por construcao.
- **Ramo B:** "Re-run all jobs" **reavalia** o `if:` do job e pula de
  novo, a menos que a expressao trate `github.event_name ==
  'workflow_dispatch'`. E a claim (3) da §6 ("filtros de path nao se
  aplicam a `workflow_dispatch`") e **irrelevante** no ramo B, onde o
  gate e o nosso `if:`, nao um filtro de path do substrato.
- Em ambos: `workflow_dispatch` despacha em um **ref** (branch/tag), nao
  num SHA arbitrario. Uma vez que `main` avance, o commit pulado fica
  inalcancavel por dispatch. *(NAO-VERIFICADA por comando — semantica do
  substrato, sem rede nesta sessao; registrada como tal no plano.)*

**Ajuste aplicado:** a unidade de recuperacao da W1 foi reescrita **por
ramo**, com molde in-repo citado (`coverage.yml:18` ja tem
`workflow_dispatch:`), e a limitacao de `ref` foi registrada como texto
obrigatorio no comentario do YAML.

### C2 — O instrumento de aceite mede o polo LEMBRADO, nao a fronteira DERIVADA

Duas manifestacoes da mesma classe — a classe-mae deste repo (*guard
verde porque nao ve o alvo*), agora aplicada ao proprio instrumento de
aceite do plano.

**C2a (gatilho).** `validate.yml:3-6` tem `pull_request:` **sem filtro de
branch** e `push: branches: [main]`. O Check da W1 exigia so o `push`.
AC-1 e AC-2 sao ambos commits (push-shaped). Um split que perca o
`pull_request` passa por todos os ACs. E o defeito de escopo-vazio da §3
aplicado ao aceite — invisivel exatamente porque o F2 mediu **zero** runs
de PR.

**C2b (classe mista).** Censo que rodei:

```
$ git log --since=2026-08-01 --until=2026-08-22 --first-parent main \
    --pretty=format:'@@%H' --name-only   # classificado por prefixo
total 239 {'pure-docs': 152, 'mixed': 67, 'pure-code': 20, 'empty': 0}
```

**67/239 = 28%** dos commits tocam docs **e** codigo no mesmo commit. Um
detector de Rota B com semantica `any()` em vez de `all()` passa em AC-1
(so-hooks) e AC-2 (so-plans) e pula os 4 pesados em 28% dos commits.

**Ajuste aplicado:** Check de **paridade de gatilho DERIVADA** (diff dos
dois blocos `on:`, nao leitura), novo **AC-2b** (commit misto tem de
EXECUTAR os 4 pesados) e novo **AC-9** (PR de teste exerce o gatilho
`pull_request` no workflow novo). A semantica `all()` virou Check
explicito do ramo B.

### C3 — Concorrencia e load-bearing e o plano nao a amarra

Um mesmo fato local (`validate.yml:11-13` = `group: validate-${{
github.ref }}` + `cancel-in-progress: true`; **79/167 = 47%** dos runs
terminaram `cancelled`) produz **consequencias opostas** nas duas rotas,
e a §6 nao citava concorrencia em nenhuma delas.

- **C3a (Rota C, Critic-A):** o Check exigia grupo distinto e nada mais.
  Com o default `cancel-in-progress: false`, todo run pesado superado
  passa a rodar ate o fim — os minutos **sobem** justamente nos pushes de
  codigo, que sao os que o filtro preserva. E a baseline de comparacao do
  AC-6 ja reflete 47% de cancelamento, logo deixa de ser comparavel.
- **C3b (Rota B, Critic-B):** todo push (inclusive so-docs) **ainda cria**
  um run de `validate.yml`, entra no MESMO grupo e **cancela** o run em
  voo do push de codigo anterior — e entao pula os 4 pesados. Os jobs
  pesados do commit de codigo nunca terminam e **nada fica vermelho**.

**Ajuste aplicado:** a interacao entrou nos contras das DUAS rotas na §6,
virou Check da W1 por ramo (`cancel-in-progress: true` no ramo C, grupo
proprio para os 4 pesados no ramo B), e a §2 passou a registrar que a
projecao **pressupoe** cancelamento preservado. A OQ-5 (migrar C→B se
ligarem required checks) agora carrega esse custo por escrito.

### C4 — Superficies derivadas alem do F4: "uma linha, mecanicamente vigiada" era falso

Verificado:

- `README.md:8` — badge de CI aponta para `validate.yml`. Depois da Rota
  C o badge deixa de representar os 4 pesados: **fica verde com o
  workflow pesado vermelho**. E a classe que o plano diz combater
  (*instrumento verde cuja pergunta envelheceu*), agora dentro do plano.
- `.claude/adr/ADR-021-e2e-harness-contract.md:132` afirma que o E2E vive
  em `validate.yml` "with an 8-minute timeout" — a W2 muda ate esse
  numero. `.claude/adr/ADR-050-native-subagents-dual-rail.md:73-74`
  afirma que `validate.yml` adiciona o job `hook-tests-dual-rail`.
- `.github/workflows/GOVERNANCE-MAP.md` precisa de linha nova e nao e
  vigiado por nada.

`verify-counts.sh` so vigia a celula `("workflows","exact",r'^Workflows\b')`
contra `docs/CTO-GUIDE.md:46`. README, ADRs e GOVERNANCE-MAP **nao** sao
cobertos — logo o drift e **silencioso**, nao build vermelho.

**Ajuste aplicado:** a frase "o unico custo novo (F4) e uma linha" foi
substituida por um inventario real (novo **F10**), e um item `[P0]` da W1
exige as quatro emendas **no mesmo commit** do split, com novo **AC-10**.

### C5 — "Medido" com rigor abaixo do que o proprio repo ja pratica

Convergencia tematica, tres manifestacoes:

- **C5a (Critic-A, P0):** tres bases de tempo. Conta rodada:
  `228,95 (21d) -> 327,07 por 30d`; `A1 193,97 (21d) -> 277,10 por 30d`;
  `janela W3 de 7d vs "/mes" = razao 4,29x`; fatura esperada em 7 dias se
  o corte for 224/mes com residual 90/mes = **US$ 21,00**. Comparar
  US$ 21 contra "US$ 224/mes" dispara o gate de 20% pelas unidades, antes
  de qualquer efeito real do corte.
- **S7 (Critic-B, P1):** a regra `medido/timeout <= 0,80` com N=2/N=3 e
  mais fraca que o metodo do job analogo. `smoke-install.yml:150-172`
  registra 5→8→20→25→32, todos "MEASURED, not guessed", todos com o fator
  2-3x — e o comentario `:159-161` diz textualmente que 15 "would sit
  inside the noise band, and the perf-gate N=20 flake (PLAN-159) was
  exactly that mistake". O outro precedente (`validate.yml:1181-1186`)
  dimensiona por **pior caso aritmetico**. N=3 nao produz p95.
- **S8 (Critic-B, P1):** "verde" nao e prova quando o runner muda. A
  suite E2E tem gates de ambiente reais — `test_install_sh_rollback.py:78-80`
  (`shutil.which` → `pytest.skip`), `test_peers_yaml_migration.py:228,424,490,816`
  (`shutil.which("openssl")`), `test_live_adapter_smoke.py:64,66`. Um run
  verde com N skips novos e indistinguivel de um run verde sem nenhum.

**Ajuste aplicado:** base de tempo canonica **US$/dia-calendario**
congelada na W0-US4 (comando + base + formula, nao so o comando); §2
reexpressa em US$/dia; AC-6 reescrito em US$/dia; W2 passa a dimensionar
por **composicao de pior caso** (as TRES invocacoes de pytest do E2E) com
o envelope 2-3x; Check da W2 e AC-5 passam a exigir **delta de `skipped`
= 0 e delta de `passed` = 0** entre o ultimo run em `Ceo` e o primeiro em
`ubuntu-latest`.

---

## Achados de um so critico que mereciam decisao (mantidos)

1. **S1 [P0] — gate circular na W0-US3 (Critic-A).** A W0 declara "wave
   inteiramente read-only sobre `.github/`" (`:407-408`) e a US3 exige
   "duracao real de cada um dos dois jobs em `ubuntu-latest`, de pelo
   menos 2 execucoes" (`:443`). Nao existe caminho para rodar um job em
   `ubuntu-latest` sem alterar `runs-on:` em `validate.yml:1078` e
   `:1139`. A W2 esta gateada (`:492`) por uma medicao que so pode ser
   obtida editando exatamente o que a W0 proibe.
   **Aceito e curado, com mecanismo mais barato que o proposto** — ver
   pushback P4: a rota de PR custa minutos pagos; a rota de **branch**
   custa US$ 0, porque `validate.yml:5-6` e `push: branches: [main]` e um
   push em branch sem PR aberto **nao dispara** `validate.yml`.

2. **S2 [P0] — a manchete nao e derivavel da propria tabela (Critic-A).**
   Contas rodadas (todos os insumos vindos do plano):
   ```
   tabela por-job (§1) soma 80,4 min/run
   167 x 80,4 = 13.426,8  vs 13.428 medido   -> bate no AGREGADO
   106 x 80,4 =  8.522,4  vs 10.407 medido   -> delta +1.884,6
    61 x 80,4 =  4.904,4  vs  2.994 medido   -> delta -1.910,4
   A1 base MEDIDA  (228,95 - 15*106*0,022) = 193,97   <- os "US$ 194"
   A1 base TABELA  (65,4*106*0,022)        = 152,51   <- 21% a menos
   A2 base TABELA  (8,1*167*0,022)         =  29,76   <- os "US$ 30"
   sobreposicao    (8,1*106*0,022)         =  18,89   <- os "US$ 19"
   ```
   **Observacao que nenhum critico fez e que agrava:** o agregado bate
   quase exatamente (13.426,8 vs 13.428) porque `13.428/167 = 80,4` — a
   tabela por-job **e** a media por run, nao uma medicao independente.
   Logo ela nao carrega informacao alguma sobre em qual BUCKET os minutos
   cairam. E isso **falsifica a ressalva da linha 61-63**: se 61 runs de
   codigo tivessem perdido minutos morrendo em `queued`, o agregado
   ficaria **abaixo** de 13.426,8. Ele nao fica. Os deltas sao uma
   **redistribuicao**, nao uma perda — o que sustenta a hipotese de
   Critic-A de erro de CLASSIFICACAO (`1.884,6/80,4 = 23,4 runs`), nao
   dois efeitos independentes.
   **Aceito.** Nova **W0-US5 [P0]** reconcilia antes de qualquer numero
   da §2 ser usado; ate la a manchete e `NAO-DERIVADA` no corpo do plano.

3. **S4 [P1] — `permissions:` ausente do boilerplate (Critic-A).**
   Verificado: `grep -n "permissions:" .github/workflows/validate.yml` →
   `16, 1143, 1187, 1414, 1449, 1514`. `integration-tests` comeca em
   `:1071` e vai de `timeout-minutes: 8` (`:1079`) direto para `steps:` —
   **sem bloco proprio**, herdando `contents: read` do nivel do workflow
   (`:16-17`). Num arquivo novo sem `permissions:`, esse job passa a rodar
   com o escopo DEFAULT do repositorio. Confirmado tambem que nada vigia
   isso: `grep -n permissions .claude/scripts/check-action-sha-drift.py`
   nao retorna nada. **Aceito**, com a alternativa mais robusta adotada:
   dar bloco proprio ao `integration-tests` **antes** do split, para que o
   job nao dependa de heranca ao mudar de arquivo.

4. **S5 [P0] — a prova de inercia (b) nao detecta o modo de falha
   nomeado (Critic-B).** Probe que rodei contra o codigo real
   (`tests/integration/test_threat_model_coverage.py:199-215`,
   `validate_file_ref`):
   ```
   baseline      full: True  bare: True
   apos MUTACAO  full: True  bare: True    <- conteudo destruido, VERDE
   apos RENAME   full: False bare: True    <- fallback startswith salva o bare
   apos DELETE   full: False bare: False
   ```
   O detector e de **existencia**, com fallback de **prefixo**. A prova
   (b) do plano ("mutar um arquivo sob o caminho ... verde ⇒ inerte")
   declararia `.claude/adr/**` INERTE, e a regressao que a §4 foi escrita
   para impedir — referencia morta em `docs/threat-model.md`, que cita 36
   caminhos de ADR — passaria a ser invisivel. **Aceito**: a W0-US2(b)
   agora exige DELETE e RENAME, e o Check exige o **VERMELHO**, nao o
   verde. A armadilha do `startswith` (ADR-045 → ADR-045b passa verde) fica
   escrita como restricao na escolha do alvo.

5. **S6 [P1] — `paths-ignore` nao tem precedente in-repo, e a doutrina da
   §3 indicta o repo em silencio (Critic-B).** Verificado:
   ```
   $ grep -rn "paths-ignore" .github/ templates/     -> (zero)
   files com paths: 13 | com push:+paths: 11
   (actionlint, adapter-live, benchmarks, chaos, formal-verify, mcp-smoke,
    otel-smoke, perf-profile, red-team, smoke-install, translations-drift)
   ```
   O plano chamava `coverage.yml` de "o precedente in-repo" e usava sua
   forma PR-only como a armadilha, quando existem **11** workflows que ja
   fazem `push:` + `paths:` corretamente. **Aceito**: o conjunto de
   precedentes foi trocado, e a §3 agora declara explicitamente o que faz
   com as 13 allowlists vivas — vira **OQ-9**, nao suposicao.

6. **S8 [P1] — SKIP silencioso (Critic-B).** Aceito; ver C5 acima.

7. **S9 [P1] — auto-disparo do workflow novo (Critic-B).** Verificado que
   o precedente citado pelo proprio plano ja faz o oposto:
   `coverage.yml:11-14` lista `.claude/hooks/**`, `.claude/scripts/**` **e
   `.github/workflows/coverage.yml`** (o proprio arquivo) no seu `paths:`.
   Pior: `.github/**` **passaria** na prova de inercia (b) — mutar um YAML
   deixa as quatro suites verdes. Consequencia: uma mudanca que estreite o
   proprio filtro do workflow pesado entra em `main` sem que ele jamais
   rode. **Aceito**: `.github/**` virou exclusao dura no AC-4 ao lado de
   `docs/**`, e o auto-disparo virou Check da W1.

8. **S3 [P1] — inventario de jobs (Critic-A).** Verificado:
   `validate.yml` tem SETE jobs — `:20`, `:1071`, `:1121`, `:1178`,
   `:1410`, `:1445`, `:1505`. Os dois nao citados
   (`opus-4-7-profiler-smoke`, `hook-stdout-schema-oracle`) rodam em
   `ubuntu-latest` e **ficam**. **Aceito**: Reference links corrigido e o
   split passa a declarar explicitamente quem fica.

---

## Pushbacks — onde a critica errou ou exagerou

**P1 — "`if:` estruturalmente morto" (Critic-A, P2) — EXAGERADO; sub-claims
confirmadas.** A expressao em `validate.yml:736-739` tem
`github.event_name == 'push' ||` como **primeiro termo**:

```yaml
        if: |
          github.event_name == 'push' ||
          (github.event_name == 'pull_request' &&
           (contains(github.event.pull_request.changed_files, 'docs/provider-pricing.md') ||
```

Logo o step **roda em todo push** — nao e um `if:` morto, e um `if:` morto
**apenas na perna `pull_request`**. As duas sub-claims, porem, estao
CORRETAS e sao o que interessa: (a) `contains()` sobre
`pull_request.changed_files` nunca casa um caminho *(NAO-VERIFICADA por
comando — `changed_files` e inteiro no payload e semantica do substrato,
sem rede aqui)*; (b) o comentario `:729-731` afirma "Mirrors
adapter-matrix job's inline `contains()` approach" e
`grep -rn "adapter-matrix" .github/workflows/` devolve **so a propria
linha de comentario** — o espelho citado nao existe mais. O achado entrou
na §6 como novo **F11**, com o enquadramento corrigido.

**P2 — "GOVERNANCE-MAP.md hoje 22 linhas de inventario, uma por workflow"
(Critic-B) — NUMERO ERRADO; achado mais forte que o alegado.** Medido:

```
yml files: 22 | MAP rows: 20
in files, NOT in MAP: ['ownership-nightly.yml', 'supply-chain-watch.yml']
```

Sao **20** linhas para **22** workflows: o mapa **ja esta stale por dois**,
e a unica coisa que o menciona e `actionlint.yml`. A Rota C adiciona a
**21a** linha para 23 workflows. Corrigido no plano com o numero real; o
stale pre-existente virou **OQ-10** em vez de suposicao.

**P3 — "O plano modela commit como binario e nunca nomeia a classe mista"
(Critic-B) — ENQUADRAMENTO ERRADO; o achado sobrevive intacto.** A
particao do plano (`:65-66`, "153 so-docs e 83 tocando codigo") **ja
contem** a classe mista dentro de "tocando codigo" — meu censo da
`67 mixed + 20 pure-code = 87` numa janela de 239 commits, contra 83/236
do plano (fronteira de janela diferente). Ou seja: a **economia** do plano
nao esta errada por isso. O que esta errado, e continua errado, e o
**instrumento de aceite**: AC-1 e AC-2 exercitam so os polos puros. O
achado foi mantido em P0 com o enquadramento corrigido.

**P4 — "esse PR tambem dispara os 4 jobs pesados no runner PAGO `Ceo`"
(Critic-A) — IMPRECISO, e existe rota mais barata.** Depois do flip que a
propria medicao exige, apenas **2** dos 4 pesados continuam em `Ceo`
(`hook-tests-dual-rail:1410`, `hook-tests-python-matrix:1445`); os outros
dois estao em `ubuntu-latest` — que e o ponto do PR. Com o job de
governanca, a exposicao paga por run de medicao e
`41,8 + 15,5 + 15,0 = 72,3 min ≈ US$ 1,59`, nao "os 4 pesados".
**E ha rota de US$ 0 que nenhum critico nomeou:** `validate.yml:5-6` e
`push: branches: [main]`, entao um **push em branch, sem PR aberto**, nao
dispara `validate.yml` — um workflow de medicao efemero com `on: push:`
nesse branch entrega as duas duracoes em `ubuntu-latest` (gratuito em repo
publico) sem tocar `validate.yml` e sem queimar minuto pago. Essa e a rota
que a W0-US3 passa a nomear; a rota de PR fica registrada como plano B com
o preco ao lado.

**P5 — "`tests/integration/` tem pelo menos 8 pontos de skip" (Critic-B)
— contagem conflacionada.** Sao **3** call sites de `pytest.skip`
(`test_install_sh_rollback.py:80`, `test_live_adapter_smoke.py:64,66`) e
**6** sondas `shutil.which` que os alimentam (`:78`, `:54`, e
`test_peers_yaml_migration.py:228,424,490,816`). A **classe** e real e o
achado fica; o numero foi substituido pelos sitios exatos no plano.

---

## Ajustes aplicados ao plano (indice — as edicoes vivem no plano)

| § do plano | Ajuste |
|---|---|
| §1 | Nota de reconciliacao: a tabela por-job **e** a media por run (`13.428/167 = 80,4`), logo nao decide bucket; a ressalva de `queued` da `:61-63` e falsificada pelo agregado. |
| §2 | Tudo reexpresso em **US$/dia-calendario**; manchete marcada `NAO-DERIVADA` ate a W0-US5; registro de que a projecao pressupoe cancelamento preservado. |
| §3 | Registro das **13 allowlists vivas** do repo e do fato de `paths-ignore` ter zero precedente in-repo → OQ-9. |
| §4 | O mecanismo do contraexemplo e **existencia**, nao conteudo — com a saida do probe; a prova (b) tem de ser DELETE/RENAME. |
| §5 | Novos **F7** (`permissions` / heranca), **F8** (sete jobs), **F9** (precedentes reais de filtro), **F10** (superficies derivadas), **F11** (`if:` morto na perna PR). |
| §6 | Concorrencia entrou nos contras das DUAS rotas; conjunto de precedentes trocado; recomendacao Rota C **reforcada** com evidencia do proprio arquivo-alvo (F11). |
| §6 claims | Claim (3) reescrita: e irrelevante no ramo B; limitacao `ref`≠SHA registrada. |
| W0 | US2 (delete/rename + Check exige VERMELHO); US3 (mecanismo nomeado, rota US$ 0); US4 (congela base de tempo + formula); **nova US5 [P0]** (reconciliacao por-job x por-bucket). |
| W1 | Checks reescritos: paridade de gatilho derivada, `permissions`, concurrency por ramo, auto-disparo, `all()` no ramo B, superficies derivadas no mesmo commit, recuperacao por ramo. |
| W2 | Timeout por composicao de pior caso (as 3 invocacoes de pytest) com envelope 2-3x; Check de delta de `skipped`/`passed` = 0. |
| W3 | AC-6 em US$/dia; a conversao explicita. |
| ACs | **AC-2b**, **AC-9**, **AC-10** novos; AC-4, AC-5, AC-8 estendidos. |
| OQ | **OQ-6..OQ-10** novas. |
| Reference links | "5 jobs" → sete, com quem fica; precedentes corrigidos. |

---

## O que eu NAO mudaria

Defendido contra "melhoria" que seria regressao:

1. **A doutrina denylist-sobre-allowlist da §3 permanece.** Critic-B tem
   razao que o repo pratica allowlist em 13 lugares, mas isso e um achado
   sobre o **repo**, nao um argumento contra a §3. A direcao de falha da
   denylist continua sendo a correta para um gate cujo default decide se o
   teste roda.
2. **A recomendacao pela Rota C permanece, e sai do debate mais forte.**
   O F11 (um `if:` de deteccao de path que ja falha em silencio, dentro do
   proprio arquivo que a W1 editaria) e evidencia in-repo de que codigo
   nosso nessa superficie erra. E a Rota B acumulou o achado C3b
   (cancelamento cruzado), que a Rota C nao tem.
3. **A recusa de `-n auto` (§7) permanece.** Nenhum critico a atacou, e
   ela e a decisao que impede o plano de virar outro plano.
4. **A honestidade da §9 (residuo declarado) permanece.** E o que impede o
   "71%" de virar claim solta.

---

## Decisoes que o CEO nao resolve sozinho → Open questions

Registradas no plano como **OQ-6..OQ-10**; nenhuma virou suposicao aqui.

1. **OQ-6** — a manchete `NAO-DERIVADA`: a W1 abre com a direcao (robusta
   nas duas bases) ou fica gateada pela reconciliacao da W0-US5?
2. **OQ-7** — ratificar **US$/dia-calendario** como base canonica.
3. **OQ-8** — rota de medicao da W0-US3: branch efemero (US$ 0) ou PR
   (~US$ 1,59/run)?
4. **OQ-9** — as 13 allowlists vivas: risco aceito ou follow-up?
5. **OQ-10** — GOVERNANCE-MAP ja stale por dois: cura dentro do PLAN-184
   W1 ou plano separado?

---

## Round verdict

**PROCEED (ADJUST_PROCEED)** — com os ajustes acima ja incorporados ao
corpo do plano.

Nao e BLOCK porque os seis P0 tem cura obvia e todas foram escritas. Nao e
"pronto" porque duas coisas ficam com o Owner: o flip
`draft` → `reviewed` (regra do repo — o CEO nao promove status) e as cinco
OQ novas, das quais a **OQ-6** e a unica que muda a ordem de execucao.

**Nao recomendo round 2.** Os dois criticos convergiram sem se
contradizer, os achados cairam todos em classes ja nomeadas no repo, e o
proximo instrumento util nao e mais um round do mesmo vendor — e o
pair-rail cross-vendor sobre o plano ajustado (a licao registrada:
*debate revisa o MODELO, rail revisa o TEXTO*; o modelo ja foi revisado
aqui).
