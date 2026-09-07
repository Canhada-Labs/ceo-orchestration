---
id: PLAN-186-FOLLOWUP-census-runtime
title: "Censo papel->modelo derivado do RUNTIME, nao de fingerprint sobre texto-fonte"
status: draft
created: 2026-09-04
owner: CEO
depends_on: [PLAN-186]
parent: PLAN-186
level: L2
budget_tokens: 300-500k (import + isolamento de gate + fronteira importavel/prosa DECLARADA; sem orcamento de cerimonia ate o censo apontar donos canonicos)
budget_sessions: 2-3
context_risk: medium
external_wait: "nenhum para o desenho e o piloto do importador; se o censo resultante apontar dono(s) canonico(s) para virar leitor, a wave subsequente (nao esta) espera assinatura GPG do Owner"
eta_calendar: "mesmo-dia a D+1 para o desenho + piloto; a wave de conversao (se houver) fica FORA deste plano"
tags: [routing, census, runtime, followup, us5]
---

# PLAN-186-FOLLOWUP-census-runtime — censo papel->modelo pelo RUNTIME

> **Lineage (PLAN-SCHEMA §1.4 — "parent shipped with explicit deferred AC
> items").** O AC-12 do PLAN-186 (censo mecanico das superficies de
> roteamento papel->modelo, US5) ficou **◐** na S345: a rodada 8 do pair-rail
> sobre `us5-census-v5` disparou a regra de parada PRE-REGISTRADA (>= 3 P1
> NOVOS no scanner) e o pack **NAO e assinavel** como fecho do AC. Este
> followup e o veiculo ratificado para a recomendacao que a rodada mediu —
> ele NAO reabre o AC-12 nem redefine seu texto; herda o escopo que
> `ARCHITECTURE-NOTE-S344.md` (`PLAN-186/w0/us5-census-v5/`) registrou.
> **Nota de proveniencia:** `us5-census-v5` — o script
> `census-role-model-routes.py`, seu relatorio "COMPLETE" e `STATE.md` —
> e um PACK AINDA NAO LANDADO (vive fora do repo, sem cerimonia; o proprio
> `ARCHITECTURE-NOTE-S344.md` §5 diz que ele "nao e assinavel"). O UNICO
> artefato do censo hoje TRACKED no repo e
> `.claude/plans/PLAN-186/w0/us5-routing-surfaces-census-S340.md` — e esse
> relatorio se autodeclara **INCOMPLETO** (linha 230). Este followup cita o
> pack como a FONTE da medicao e da recomendacao (§1, §4), nunca como algo
> ja publicado no repo.

## Tese

Um instrumento construido para o AC-12 (`census-role-model-routes.py`,
pack `us5-census-v5`, NAO landado — ver nota de proveniencia acima) decide
o CONTEXTO de uma rota lendo o texto-fonte com heuristicas por linha — indentacao, chave mais
proxima a esquerda, cabecalho de secao, rotulo de bloco. Cada gramatica nova
em que uma rota pode estar escrita (cerca de til, cerca de quatro crases,
predicado multilinha, mapa compacto, cadeia `elif`, tupla transposta) e uma
classe NOVA de cegueira, e o espaco dessas gramaticas nao e enumeravel:
fechar seis abre a setima — medido em oito rodadas sem queda sustentada
(tabela abaixo). A mesma forma ja apareceu no PLAN-179 r22 (canal fecha por
REMOCAO, nao por enumeracao) e no proprio AC-17 deste plano (escopo por
EXCLUSAO). A saida proposta e trocar o QUE o instrumento le, nao mais uma
heuristica: para os donos que ja sao codigo Python importavel
(`task-route.py`, `_lib/escalation_signals.py`, `tier_policy_cli/_types.py`
e `_constants.py`, `hooks/audit_log.py`, `detectors/*.py`), IMPORTAR o
modulo e PERGUNTAR a ele quais rotas expoe — a rota vira o VALOR devolvido
por uma chamada ou constante, e o contexto vira o argumento que a
seleciona, nao a coluna em que o texto foi escrito. Donos que sao DADOS
(`templates/.claude/tier-policy.json`, `routing-matrix.yaml`, frontmatter de
`agents/*.md`) ja se leem sem heuristica de contexto. Uma TERCEIRA classe
sao donos que sao SCRIPT DE SHELL (`.claude/scripts/inject-agent-context.sh`,
as atribuicoes `MODEL_HINT=`): **nao e um bloco DE DADOS** — MEDIDO no land
deste pack, o valor sai de FLUXO DE CONTROLE (um `case` sobre
`$DETECTED_SKILL` — SKILL detectada, nao slug de arquetipo) e o que ele
produz e um ALIAS DE TIER (`opus`/`sonnet`), nunca um `model_id`; o heredoc
`MODEL_HINT_HEADER` apenas INTERPOLA a variavel, logo uma regex ancorada NELE
devolve o template, jamais um mapa. Nao sao codigo Python importavel, mas
tambem nao precisam da heuristica de coluna que o instrumento atual usa sobre
prosa livre. O QUE se le, porem, MUDOU no piloto W0, e a frase
anterior descrevia a versao SUPERADA: uma regex ancorada as
ATRIBUICOES `MODEL_HINT=` associa a atribuicao ao padrao, mas NUNCA
prova que ela EXECUTA (braco morto, braco anterior que casa antes
sem atribuir, `set -e` que aborta o script). O censo por runtime
PERGUNTA ao dono: o bloco `case "$DETECTED_SKILL" in` ... `esac` e
EXECUTADO verbatim e INTEIRO, em confinamento (interpretador por
caminho absoluto, ambiente zerado, `PATH` vazio, cwd descartavel,
timeout), sob as opcoes de shell que o proprio arquivo declara, uma
vez por ALTERNATIVA LITERAL, e o vinculo publicado e o que aquela
execucao PRODUZ, lido por canal emoldurado com nonce. A regex
ancorada as atribuicoes e ADVISORY e o censo nao a consulta: a
guarda de cobertura que ele EXECUTA e uma varredura por SUBSTRING
(linha com o literal `MODEL_HINT=` fora do `case` ou dentro do
heredoc e recusa NOMEADA). Derivar
QUAIS sondas rodar ainda LE a gramatica do `case`, e por isso a
promessa desta superficie e ESTREITA e esta DITA assim nos bytes
entregues: nas QUATRO direcoes que o pair-rail r4 mediu (braco
compacto, aspas no padrao, curinga, opcoes de shell) a guarda de
cobertura e fail-CLOSED — forma nao modelada vira VERMELHO
NOMEADO; FORA dela ficam, por construcao e por MEDIDA (r6, ambos
reproduzidos por plant), a DELIMITACAO de bracos que dividem a
MESMA linha e a ALCANCABILIDADE do bloco (`case` sob `if false`,
em funcao nunca chamada, ou depois de um `exit`). A linha
`MODEL_HINT` da tabela e, portanto, publicada como OBSERVACAO
explicitamente NAO-EXAUSTIVA (coluna «cobertura»), nunca como
vinculo do keyspace inteiro; os dois itens estao NOMEADOS na §4-b
com a sua rota de cura.

**As quatro superficies NAO falam a mesma UNIDADE — e essa, nao o formato, e
a divisao que o censo por runtime tem de respeitar.** MEDIDO no land deste
pack: `MODEL_HINT` e `routing-matrix.yaml` (chave `coder_model`) carregam
ALIAS DE TIER (`opus`/`sonnet`); `VETO_HARDCODE` e os pins de `agents/*.md`
carregam `model_id` (ex.: `claude-fable-5`). Dai a REGRA GERAL, valida para
toda superficie e nao para uma delas: **valor em alias so entra na tabela
depois de um passo DECLARADO de resolucao alias->`model_id`; a ausencia desse
passo e VERMELHO, nunca um mapa inventado.** O mesmo vale para qualquer junção
de chaves que nao sejam papeis (o `case` do `MODEL_HINT` indexa por SKILL):
sem um passo skill->papel DECLARADO, a linha nao entra. Donos que sao PROSA NORMATIVA (`SUPPORT.md`, `VERSIONING.md`,
`SPEC/v1`, `docs/`) ficam como o
unico resto legitimo do reconhecimento textual, porque a prosa E o artefato
— e e exatamente ali que mora o residual UNBOUND que a §3 abaixo usa como
controle discriminante. Uma rota derivada do runtime muda quando o
COMPORTAMENTO muda (o invariante que o AC-12 quer); uma rota derivada da
forma do texto muda quando a forma muda, e por isso cada gramatica nova
custa uma rodada de rail inteira.

## 1. A serie medida (copiada de `ARCHITECTURE-NOTE-S344.md` §1 — us5-census-v5)

| rodada | achados reais | curados | P1 no scanner |
|---|---|---|---|
| r1 | 5 | 4 (+1 refutado) | 2 |
| r2 | 6 | 5 (+1 FN8 declarado) | 2 |
| r3 | 4 | 4 | 2 |
| r4 | 23 | 23 | 4 |
| r5 | 5 | 5 | 2 |
| r6 | 10 | 0 (parada declarada) | 4 |
| r7 | 7 (5 do rail + 2 minhas) | 7 | 3 |
| r8 | 9 | 0 (parada) | **4** |

Oito rodadas, 69 achados reais, 48 curados, nenhuma queda sustentada na
coluna da direita — o numero que decide. Dois dos quatro P1 da r8 (F1, F4)
sao lacunas DENTRO de curas escritas na rodada imediatamente anterior; a
doutrina deste repo ja nomeia essa forma: cura que gera o achado seguinte
pede troca de ARQUITETURA, nao mais uma cura.

## 2. Por que o texto-fonte nao fecha: o controle discriminante

O refutador da lane provou por EXPERIMENTO — nao por leitura — que remover
o sufixo `[1m]` de `SUPPORT.md:88` deixa a linha do dono BYTE-IDENTICA
(3 bound / 2 unbound / 0 nearmiss, mesmos papeis, `bindfp 61df1c65a9810de1`)
e o `--check` continua em rc 0, mesmo apos a cura D2 (que fecha o caso
LIGADO, pondo o sufixo servido DENTRO do token). `SUPPORT.md:88` fica
UNBOUND, e a linha de bloco do censo comprime o espaco NEGATIVO (o que o
instrumento viu e recusou) em cinco campos: tres contagens, a lista de
papeis e um digest dos sitios LIGADOS apenas — nenhum deles se move quando
um candidato NAO-ligado troca de token. Um instrumento derivado do runtime
nao tem esse espaco negativo para comprimir: ele nao "ve e recusa" texto,
ele pergunta ao modulo quais rotas existem. **`SUPPORT.md:88` e o CONTROLE
DISCRIMINANTE deste followup** — qualquer desenho de censo-por-runtime deve
ser medido contra ele antes de ser aceito como avanco.

## 3. Acceptance criteria (falsificaveis)

- [ ] **AC-F1** Tabela papel->modelo derivada do RUNTIME (importar os modulos
      donos e perguntar quais rotas expoem, nao fingerprint de texto), cobrindo
      as QUATRO superficies que a nota S340 do AC-12 nomeia — citadas aqui
      VERBATIM byte-a-byte da propria nota (`PLAN-186-orchestrator-operating-model.md`,
      nota S340 do AC-12): «as 4 superfícies nomeadas (pins de
      `agents/*.md`, `MODEL_HINT`, `routing-matrix.yaml`, `VETO_HARDCODE`)
      são «dona local» em formatos incompatíveis». Leia-se ao pe da letra: a
      nota classifica SUPERFICIES — estas quatro, com UM rotulo, «dona local» —
      e NAO publica nenhum conjunto de papeis. O lado direito das comparacoes
      abaixo e, portanto, so essa LISTA DE QUATRO; nada mais e lembrado dela.
      **A MESMA nota REABRE o escopo — e a citacao acima parava
      exatamente onde ela o faz.** O resto do mesmo bullet, tambem
      VERBATIM da nota (so as quebras de linha sao deste plano):
      «REABERTO pelo rail (codex r3, P1): há donos VIVOS a mais —
      `set-quality-profile.sh:157-169` (hardcoda pares papel/modelo e
      os escreve nos `agents/*.md`), `task-route.py:504-555`, o
      fallback papel→modelo do audit log, e (r4) o baseline ADR-052 do
      tier-policy (`tier_policy_cli/_types.py:202-237`, usado por
      `loader.py:111-113,423-460` quando `.claude/tier-policy.json`
      falta — já diverge do pin: devops = Haiku lá, Sonnet no
      `agents/`) e, achados pelo r6, `templates/.claude/tier-policy.json`
      (dono ENTREGUE a todo adopter pelo `install.sh`, que faz o loader
      bypassar o fallback de `_types.py`) e `_ADR_052_ROLE_TO_MODEL`
      (`.claude/hooks/audit_log.py:922-954`, 20 chaves). O r6 também
      RETIROU uma atribuição FALSA: `task-route.py` lê o
      `VETO_HARDCODE` HOMÔNIMO de `_lib.tier_policy._constants`
      (`role -> FrozenSet[task_type]`), não o de `tier_policy_cli`
      (`role -> model_id`) — não é leitor desta superfície. O AC fecha
      quando o censo os incluir, com o conjunto DERIVADO e não
      lembrado.»
      **Por isso esta caixa continua DESMARCADA.** A W0 entregue e o
      PILOTO DO METODO sobre as quatro superficies originais — ela
      prova que perguntar ao dono (import, parser do dono, execucao
      confinada) substitui o fingerprint de texto, e mede onde o
      metodo ainda nao fecha (a unica superficie SEM API de dono).
      A W1 estende o censo aos donos REABERTOS pela nota, e e nela
      que a caixa fecha. Escopo EXPLICITO da W1, cada dono com a sua
      classe e o leitor que o alcanca:
      1. `set-quality-profile.sh:157-169` — dono SCRIPT-SHELL (hardcoda
         pares papel/modelo e os ESCREVE nos `agents/*.md`): mesma
         arquitetura de EXECUCAO CONFINADA do `MODEL_HINT`; bloco que
         nao caiba no confinamento declarado e RECUSA NOMEADA, nunca
         leitura de coluna.
      2. `task-route.py:504-555` — dono PYTHON-IMPORTAVEL: import do
         modulo e pergunta ao que ele expoe. A errata do r6 acima e
         parte do Check: publica-se o que o import devolve, jamais a
         atribuicao que a propria nota RETIROU.
      3. fallback papel->modelo do audit log, localizado pelo r6 em
         `_ADR_052_ROLE_TO_MODEL` (`.claude/hooks/audit_log.py:922-954`,
         20 chaves) — dono PYTHON-IMPORTAVEL: import. Se o fallback do
         r3 e a constante do r6 forem o MESMO dono, a W1 publica UMA
         linha — identidade PROVADA pelo import, nunca lembrada.
      4. baseline ADR-052 do tier-policy (`tier_policy_cli/_types.py:
         202-237`, consumido por `loader.py` quando
         `.claude/tier-policy.json` falta) — dono PYTHON-IMPORTAVEL:
         import. A nota ja MEDE divergencia com o pin (`devops` =
         Haiku la, Sonnet no `agents/`): a W1 publica as duas linhas,
         nunca uma reconciliada.
      5. `templates/.claude/tier-policy.json` — dono DADO, ENTREGUE a
         todo adopter pelo `install.sh`: lido pelo carregador do
         proprio tier-policy (parser do dono), nunca por regex.
      Os Checks (a) e (b) abaixo valem COMO ESTAO para as quatro do
      piloto e sao ESTENDIDOS POR DONO na W1 — cada dono IMPORTAVEL
      pelo Check (a) (import + comparacao par a par com a linha da
      tabela), cada dono DADO ou SCRIPT pelo Check (b) (parser ou
      carregador do proprio dono; execucao confinada quando o valor
      sai de fluxo de controle). Perder um dono da lista reprova o AC
      do mesmo modo que perder uma das quatro superficies.
      As quatro se dividem em TRES classes de dono (Tese acima): `VETO_HARDCODE`
      e codigo Python IMPORTAVEL (`.claude/scripts/tier_policy_cli/_constants.py`);
      `routing-matrix.yaml` (`.claude/dispatcher/routing-matrix.yaml`) e DADO
      puro **mas com valor em ALIAS** (`coder_model: opus` / `coder_model:
      sonnet`), logo cai na mesma regra de resolucao que o `MODEL_HINT`;
      pins de `agents/*.md` sao DADO (frontmatter, um arquivo por papel
      — ex.: `.claude/agents/code-reviewer.md`); `MODEL_HINT` NAO e um bloco
      DE DADOS — sao ATRIBUICOES em fluxo de controle num script de shell
      (`.claude/scripts/inject-agent-context.sh`) que rendem um ALIAS DE TIER
      (`opus`/`sonnet`), nao um `model_id` — nao importavel, mas tambem sem
      heuristica de coluna sobre prosa.
      Check (a) — dono IMPORTAVEL, UM comando, rodado de `.claude/scripts/`:
      `python3 -c "import tier_policy_cli._constants as c;
      print(sorted(c.VETO_HARDCODE.items()))"`. VERDE quando esse import
      devolve um mapa papel->model_id NAO VAZIO **e** a linha `VETO_HARDCODE`
      da tabela do runtime tem EXATAMENTE esses pares. VERMELHO em tres
      formas nomeadas: o import falha; o mapa vem vazio; um par esta num lado
      e falta no outro. O modo de falha que este Check guarda e a REGRESSAO
      para fingerprint — uma linha derivada do TEXTO diverge do valor
      importado assim que a forma do texto muda sem o comportamento mudar.
      Check (b) — donos DADO / SCRIPT, UM DONO POR SUPERFICIE, sem
      heuristica de coluna. (i) `routing-matrix.yaml`: o parser do
      PROPRIO dono em runtime (`routing-matrix-loader.py`, stdlib) e a
      verdade; `yaml.safe_load` roda so como CROSS-CHECK quando PyYAML
      existe e a divergencia entre os dois e VERMELHO. (ii)
      `agents/*.md`: o parser de frontmatter do repo, um arquivo por
      papel, CHAVEADO PELO SLUG DO ARQUIVO (e assim que o runtime
      resolve papel); nenhum `*.md` some em silencio. (iii)
      `MODEL_HINT`: o bloco `case` INTEIRO de `inject-agent-context.sh`
      e EXECUTADO verbatim em confinamento (interpretador absoluto, env
      zerado, `PATH` vazio, cwd descartavel, timeout), sob as opcoes de
      shell do proprio arquivo, UMA VEZ POR ALTERNATIVA LITERAL, e o
      vinculo publicado e o que aquela execucao produz, lido por canal
      emoldurado com nonce — associar a atribuicao ao padrao nunca
      provou que ela EXECUTA, e reconstruir o `case` braco a braco nao
      preservava nem o primeiro-que-casa nem as alternativas; a regex
      ancorada as ATRIBUICOES `MODEL_HINT=` (e NUNCA ao heredoc
      `MODEL_HINT_HEADER`, que so interpola a variavel e devolveria o
      template) e ADVISORY: o censo nao a consulta, e a cobertura
      que ele executa e a varredura por SUBSTRING. Os donos
      DADO respondem pela sua API PUBLICA de runtime
      (`load_routing_matrix`, `parse_agent_file`), nao so pelo parser
      de texto: uma matriz que o runtime REJEITA e um arquivo de agente
      em SYMLINK sao VERMELHOS nomeados.
      VERDE quando os TRES parsers devolvem valor **e** a tabela tem UMA
      linha por superficie, as tres rotuladas «dona local» como a nota as
      rotula; e TODA superficie de valor em ALIAS (aqui `MODEL_HINT` **e**
      `routing-matrix.yaml`) so entra na tabela pelo passo de resolucao
      alias->`model_id` DECLARADO da Tese — a sua ausencia e VERMELHO em
      QUALQUER dona, nunca um mapa inventado, e uma tabela que misture alias
      com `model_id` reprova mesmo com as quatro linhas presentes.
      VERMELHO, nomeado POR DONO, quando um parser nao acha o
      bloco/chave, quando uma superficie some da tabela, ou quando a tabela
      rotula uma delas de outro modo. (a) e (b) juntos sao a cobertura
      MINIMA — as quatro superficies, quatro linhas: perder uma reprova o AC.
- [x] **AC-F2** O caso `SUPPORT.md:88` (§2 acima) serve como CONTROLE
      DISCRIMINANTE: o desenho declara, por escrito, se um censo-por-runtime
      cobre esse residual (porque `SUPPORT.md` normalmente e PROSA e ficaria
      fora do escopo importavel) ou se ele continua fora do escopo do
      runtime e permanece como fingerprint de texto para a fronteira
      normativa — nas duas leituras a resposta e MEDIDA, nunca assumida.
      Check: teste que planta a mesma mutacao do refutador (remover `[1m]`
      de `SUPPORT.md:88`) e afirma o comportamento declarado (RED se a
      declaracao disser "cobre" e o teste ficar verde; GREEN se a
      declaracao disser "fora do escopo do runtime" e citar a razao).
- [x] **AC-F3** Regra de parada PRE-REGISTRADA para este followup, escrita
      ANTES da primeira rodada de rail sobre o piloto: um numero de P1 e a
      classe que os torna "mesma pergunta, gramatica nova" (o padrao que
      disparou a r6 e a r8 do `us5-census-v5`) — se disparar, o followup
      registra a nao-convergencia e NAO abre outra rodada sem decisao do
      CEO.
      Check: leitura humana da secao "Regra de parada" deste plano antes do
      primeiro `codex exec review`; nenhum script — decisao de processo, nao
      de codigo.

## Regra de parada (deste followup, escrita ANTES de qualquer piloto de codigo)

Mesmo criterio que disparou nas rodadas 6 e 8 de `us5-census-v5`, herdado
por desenho: **>= 3 achados P1 NOVOS na mesma classe** ("mesma pergunta,
gramatica nova" — um caso que o desenho por-runtime deveria cobrir e nao
cobre, ou um novo residual UNBOUND que se comporta como o de `SUPPORT.md:88`)
em UMA rodada de pair-rail sobre o piloto. Se disparar: nenhuma rodada
seguinte abre sem decisao do CEO; a nao-convergencia e registrada por
escrito (molde: `ARCHITECTURE-NOTE-S344.md`), nunca silenciada por mais uma
cura.

## 4. Residuais herdados de `us5-census-v5` (8, verbatim de `BUILDER-CLAIM-S344.json` campo `residuals`)

Este followup HERDA os oito itens abaixo; nenhum deles fecha por si so
neste plano — eles definem o piso que o desenho do runtime tem de igualar
ou superar antes de qualquer wave de conversao.

1. "NOT SIGNABLE as the close of AC-12. Rail round 8 returned 4 P1 in the
   scanner, all uncured, and the stop rule fired: ARCHITECTURE-NOTE-S344.md
   is the residual the CEO turns into a FOLLOWUP plan item."
2. "F9 [P2] is an INTERNAL contradiction of the shipped report: :496 says CI
   runs --check and :780-782 says it does not, and no workflow invokes it.
   That alone blocks a signature."
3. "D2 is only PARTLY cured, and the lane refuter's experiment is the half
   that stays open (verified by me against the CURED pack,
   verify-refuter-r1.txt): the served suffix now lives INSIDE the token, so
   a BOUND route pinned to a `[1m]` variant moves the digest — but
   SUPPORT.md:88 is UNBOUND, and a block row carries three COUNTS, the role
   list and a digest of BOUND sites only. An unbound candidate changing its
   token moves none of those five fields: row byte-identical (3/2/0, bindfp
   61df1c65a9810de1) and --check rc 0, exactly as the refuter measured
   pre-cure. Not cured: the round-8 stop rule forbids further cures."
4. "F1 [P1] B6-transposed sites lose `col` (a gap inside this round's D1
   cure); F4 [P1] an if/elif/elif chain keeps only the opening `if` (a gap
   inside this round's D4 cure); F2 [P1] compact same-line nested routes
   keep only the NEAREST key as context; F3 [P1] a parenthesized multi-line
   `if` predicate is labelled by its opener alone."
5. "F5-F8 [P2/P3]: duplicate working-set declarations are UNIONED instead
   of refused; the role-vocabulary derivation does not apply the scanner's
   own exclusion predicate; the default listing omits Site.detail for
   UNBOUND; --strict outside --emit-block is silently ignored."
6. "D7 [P2] DECLARED and uncured since round 6: map-key harvesting scans RAW
   text, so a fully COMMENTED-OUT map can promote a dead slug to a
   vocabulary role."
7. "FN8 stays DECLARED and uncured in the report: a normative line keyed by
   a TASK CLASS or a TIER, not a role, stays UNBOUND."
8. "The TEXT/EVIDENCE arm was ABORTED BY ME in round 7 (the tree changed
   under it while it read; kept as codex-r7-text-ABORTED-tree-moved.txt) and
   did not run at all in rounds 5, 6 and 8: two large codex sessions at once
   die on this machine, measured in round 5 and unchanged."

## 4-b. Residuais NOMEADOS deste W0 (pair-rail r6)

Os dois foram MEDIDOS e REPRODUZIDOS por plant em copia descartavel
(tabela byte-identica, rc 0).

Os dois itens abaixo ficam FORA do que a guarda de cobertura do
`MODEL_HINT` responde. Eles NAO sao formas a mais para uma proxima
rodada modelar: sao perguntas que a extracao de um TRECHO nao
responde por construcao. Estao ditos nos BYTES entregues (docstring
do modulo, itens (v) e (vi)) e a linha da tabela e publicada como
OBSERVACAO NAO-EXAUSTIVA na coluna «cobertura».

1. **Dois bracos na MESMA linha** (`a) ... ;; escondido) ... ;;`).
   A gramatica de `;;` do `bash` permite varios bracos por linha; uma
   particao «linha do padrao … terminador» nao os separa e a rota
   escondida sai da tabela em SILENCIO. Fechar por regra pediria um
   PARSER de shell, nao outro regex.
2. **Alcancabilidade do bloco.** Com o bloco extraido e executado com
   fidelidade perfeita, o vinculo publicado ainda pode ser um que o
   dono real NUNCA executa (`case` sob `if false; then … fi`, dentro
   de funcao nunca chamada, ou depois de um `exit`).

**Rota de cura (uma, para os dois):** dar um DONO ao `MODEL_HINT` —
uma funcao shell com contrato (`model_hint_for_skill <skill>`) ou um
dado (TSV/YAML) que o script consome — e entao perguntar a ele como
este censo ja faz nas outras tres superficies. E edicao CANONICA em
`.claude/scripts/inject-agent-context.sh`, logo cerimonia GPG e wave
propria: e a opcao (3) da §5 de `ARCHITECTURE-NOTE-S347.md`, fora do
alcance deste pack LIVRE.

## 5. Fronteiras deste followup

- Nao reabre nem redefine o AC-12 do PLAN-186 — a nota S345 no plano-pai e a
  unica edicao la.
- Nao converte donos locais em leitoras: essa e a W-ROTA (AC-17). O texto
  que antecede o AC-17 no plano-pai cita, VERBATIM byte-a-byte (por ANCORA
  DE TEXTO, nunca por numero de linha — linhas envelhecem): «A fonte é o
  AC-17 (escopo por EXCLUSÃO + keyspace = união derivada) e o relatório
  `PLAN-186/w0/us5-routing-surfaces-census-S340.md`, cujo censo COMPLETO a
  wave `us5-census-complete` deriva mecanicamente.» Esse relatorio e o
  PARCIAL da S340 — se autodeclara INCOMPLETO («Errata (rail S340 r3, codex
  P1): este censo está INCOMPLETO.», linha 230 no momento desta escrita,
  numero sujeito a deslocar) — e a wave `us5-census-complete`
  que ele antecipa NUNCA rodou; o pack `us5-census-v5` (nota de
  proveniencia, topo deste plano) tentou ocupar esse papel na S344/S345 e
  NAO e assinavel. SE alguma wave landar antes da W-ROTA, qual relatorio a
  W-ROTA consome e decisao de OUTRA lane, nao deste followup.
- Custo de importar modulos do repo dentro de um gate exige isolamento (o
  PLAN-182 pagou essa licao com a cadeia HMAC) — a fronteira entre
  "superficie importavel" e "prosa normativa" tem de ser DECLARADA aqui com
  a mesma disciplina de exclusao que o AC-17 ja usa para o escopo, antes de
  qualquer piloto tocar codigo.
- Nenhuma wave deste followup e canonica por si (desenho + piloto sao
  leitura); SE o resultado apontar um dono canonico para virar leitor, essa
  conversao herda a mesma exigencia de cerimonia GPG que a W-ROTA ja
  documenta no PLAN-186 (`AGENTS.md:86-103` + oraculo `--is-canonical`).

## Progress log

- 2026-09-04 (S345): plano criado em `draft`, a partir da decisao do CEO
  registrada em `us5-census-v5/ARCHITECTURE-NOTE-S344.md` §5 (item 2).
- 2026-09-05 (S347, W0): instrumento de censo POR RUNTIME entregue em
  `PLAN-186-FOLLOWUP-census-runtime/w0/census_runtime.py` + bateria em
  `.claude/scripts/tests/test_census_runtime.py`. **AC-F1 SEGUE
  ABERTO**: a MESMA nota S340 que nomeia as quatro superficies REABRE
  o escopo e nomeia >= 5 donos VIVOS a mais (citacao completa e lista
  por classe dentro do proprio AC-F1); esta W0 e o PILOTO DO METODO
  sobre as quatro originais e a caixa fecha na W1, que estende os
  Checks (a) e (b) dono a dono. O piloto entrega quatro
  superficies, quatro linhas, TRES classes de dono — `VETO_HARDCODE`
  IMPORTADO, `routing-matrix.yaml` e `agents/*.md` por parser real,
  `MODEL_HINT` NAO por leitura: o bloco `case "$DETECTED_SKILL" in` ...
  `esac` do dono e EXECUTADO **VERBATIM e INTEIRO**, em confinamento
  (`/bin/bash --noprofile --norc` por caminho absoluto, env zerado
  exceto `DETECTED_SKILL`, `PATH` VAZIO, cwd temporaria descartavel,
  timeout 20 s), sob as MESMAS opcoes de shell que o arquivo declara
  (`set -euo pipefail`, derivada do proprio arquivo), UMA VEZ POR
  ALTERNATIVA LITERAL de cada braco, e o vinculo e lido por um canal
  EMOLDURADO com nonce. Assim o primeiro-braco-que-casa decide como no
  runtime, alternativas do MESMO braco que rendam valores diferentes
  sao publicadas SEPARADAMENTE, a saida comum do bloco nao se passa
  pelo valor, e um comando que aborta o script real tambem aborta a
  sonda — quatro defeitos REAIS de pair-rail (r2 P1; r3 P1, P1, P2, P2)
  que a leitura estatica e depois a reconstrucao braco-a-braco davam
  por vinculados. Nao produzir vinculo e VERMELHO
  (`hint_probe_yields_no_value` / `hint_probe_no_binding`). A
  cobertura desta superficie e uma varredura por SUBSTRING, e nao
  um regex: uma linha com o literal `MODEL_HINT=` tem de estar no
  bloco `case` e fora do heredoc `MODEL_HINT_HEADER` (controle
  positivo: atribuicao plantada no heredoc e recusada por
  `hint_matched_heredoc`); o matcher ancorado as atribuicoes e
  ADVISORY e o censo nao o consulta. Bloco com `$(`, crase, `>`, `<`, `&` ou
  `|&` e RECUSADO POR NOME e nunca executado — lista enumeravel, logo
  cortesia: a defesa e o confinamento. Os donos DADO sao alcancados
  pela API PUBLICA do runtime (`load_routing_matrix`, que VALIDA, e
  `parse_agent_file`, que RECUSA symlink), nao so pelos seus parsers
  de texto. Nenhum `*.md` de
  `.claude/agents/` some em silencio: a saida DECLARADA pelo gerador do
  repo (`generate-dispatch.DISPATCH_PATH`) aparece como
  `<sem-pin: tabela de despacho gerada>`. Passo de resolucao
  alias->model_id
  DECLARADO como RS-1 (ADR-149 `AVAILABLE_MODELS_WORKING_SET` pelo
  parser do proprio repo x `_infer_tier`); RS-1 devolve o CONJUNTO
  declarado porque o repo NAO declara pin unico — reduzi-lo a singleton
  seria o mapa inventado que a Tese proibe (residual nomeado). As
  quatro direcoes fail-OPEN que o pair-rail r4 mediu nesta superficie
  fecharam fail-CLOSED, cada uma com o seu controle plantado: braco
  COMPACTO de uma linha e sondado, e o span do `case` e verificado
  por PARTICAO e nao por contagem de terminadores: linha de CODIGO
  numa lacuna entre os corpos reconhecidos e
  `hint_arm_coverage_incomplete`, e o que a particao nao delimita
  esta DITO como fora da cobertura no item (v) do docstring;
  alternativa com ASPAS e recusada
  (`hint_pattern_probe_underivable`), porque o dono as remove ao casar
  e a sonda literal cairia noutro braco; o braco curinga publica a
  limitacao NO ROTULO (`*[sonda sintetica; nao generaliza]`) — uma
  sonda sintetica e OBSERVACAO, nunca vinculo de todo o keyspace; e as
  opcoes de shell aceitam comentario inline, com declaracao `set -…`
  existente e nao interpretavel virando VERMELHO
  (`hint_shell_options_uninterpretable`), alem do vinculo passar a ser
  validado EXATO, sem aparo de espacos. O que NAO fecha por
  instrumento, e esta DITO no docstring do modulo: enquanto esta
  superficie nao tiver uma API de dono a quem PERGUNTAR (as outras
  tres tem), derivar QUAIS sondas rodar continua sendo leitura de
  gramatica — a razao pela qual a regra de parada deste followup
  disparou na r4 e a decisao de seguir foi do CEO. AC-F2
  [x]: a leitura DECLARADA e «fora do escopo do runtime» — `SUPPORT.md`
  e prosa normativa, nenhum modulo e dono dela, o censo nunca a le; o
  teste planta a mutacao do refutador (remove `[1m]` de `SUPPORT.md:88`)
  e mede tabela byte-identica + rc 0. AC-F3 [x]: regra de parada escrita
  no topo de `rail-round-1.md` ANTES do primeiro `codex exec review`.
  **S348 (decisao do CEO, opcao (2)):** a promessa da superficie
  `MODEL_HINT` foi ESTREITADA nos dois lugares entregues — o
  docstring do modulo passa a declarar o que a guarda de cobertura
  NAO responde (bracos que dividem a MESMA linha; alcancabilidade do
  bloco) e a linha da tabela e publicada com a coluna «cobertura» =
  OBSERVACAO NAO-EXAUSTIVA, fail-CLOSED (uma linha sem a marca, ou
  uma `MODEL_HINT` que se declare resposta do dono, e
  `coverage_marker_missing`). Os dois achados P1 da r6 estao
  NOMEADOS na §4-b com a rota de cura unica (dar um DONO ao
  `MODEL_HINT` — edicao canonica, wave propria).
  Status permanece `draft`: PLAN-SCHEMA §Lifecycle constraints — um
  followup nao entra em `executing` enquanto o pai nao chega a `done`, e
  o PLAN-186 esta `executing`.
