# PLAN-186 W0 — AC-13: detector permanente de roteamento no ar (S361)

> **Entrega.** O invariante «modelo SERVIDO == modelo DECLARADO no sítio» passa
> a ser **avaliado e impresso a cada execução** do instrumento de custo
> (`.claude/scripts/ceo-cost-transcripts.py`; por herança, o bloco de
> transcripts de `ceo-cost.py` e de `budget-summary.py`), mais o **2.º predicado
> de piso VETO** que o AC-10 nomeou para quem fechasse o AC-13. Só dados de
> runtime — nenhuma leitura de texto de script. Pack LIVRE: oráculo
> `--is-canonical` = 0 nos 5 paths. Base `48f03b3a1b88`; o patch aplica limpo
> também em `092377af02b6` (HEAD de `main` quando a bateria rodou).

## 1. O que entra

| path | oráculo | o que muda |
|---|---|---|
| `.claude/scripts/ceo-cost-transcripts.py` | 0 | `routing_invariant()` + helpers, `transcript_rollup()['routing']`, `collect()['routing']`, `render_block()`, JSON/humano do CLI, `--assert-routing`; seção do docstring com o contrato e os critérios de morte |
| `.claude/scripts/tests/test_ceo_cost_transcripts.py` | 0 | 80 testes novos (fixtures sintéticas; zero rede, zero transcript real) |
| `.claude/scripts/tests/test_ceo_cost_integration.py` | 0 | 5 testes novos: o veredito chega aos DOIS chamadores (e um texto forjado não o forja neles) e NÃO ao `--source audit` (que segue byte-idêntico ao congelado) |
| `docs/cost-of-operation.md` | 0 | subseção «The routing invariant» |
| `.claude/plans/PLAN-186/w0/ac13-routing-invariant-S361.md` | 0 | este relatório |

Nenhum env var novo (o `env-inventory` não se move), nenhum hook, nenhum
arquivo canônico. O plano NÃO é editado por este patch: a linha do AC-13 e a
nota datada ficam para o CEO (§8).

## 2. Como o texto do AC foi lido (decisões, com a evidência)

O AC-13 diz só «modelo SERVIDO por label == modelo DECLARADO no sítio». A nota
do AC-10 (`ac10-below-floor-v4`) já registrava que o texto é ambíguo entre
alias e id e nomeava o requisito: **normalização declarada MAIS um 2.º
predicado de piso**. As quatro leituras abaixo seguem esse requisito.

1. **DECLARADO = a chave `model` do sidecar `agent-<id>.meta.json`** — o que a
   chamada realmente passou, já avaliado (variável, template, ternário). Não
   se lê o texto do script: a lição «instrumento que prevê código por TEXTO não
   converge» (memória S347; o pack anterior `ac13-routing-drift-v5` levou 35
   rodadas de rail em torno de uma gramática de fonte) é a razão de este
   detector não ter nenhuma. Ausente ou `inherit` = nenhuma
   afirmação no sítio: contado (`undeclared`), nunca violação.
2. **SERVIDO = `message.model` do transcript pareado**, lido pelo MESMO
   `scan_files()`/`dedup()` do relatório de custo (uma só grafia; um chunk de
   streaming com modelo divergente resolve para o chunk terminal, como no
   custo). `<synthetic>` (pseudo-modelo do harness, 0 tokens) é ignorado.
   Auto-relato do agente nunca conta (S340: `claude-opus-5[1m]` × `claude-opus-5`).
3. **LABEL = o `description` do sidecar** (é o `label:` do `agent()` do
   Workflow e o `description` do spawn nativo); sem `description`, o `name`; sem
   ele, o id do agente. O invariante é por SPAWN; o label identifica o sítio.
4. **Alias → FAMÍLIA, não alias → id.** `opus|sonnet|haiku|fable` casam por
   família (`claude-<família>-…`, derivada das tabelas de frota, nunca
   redigitada); id completo casa EXATO (sufixo de data `-YYYYMMDD` tolerado).
   **Decisão de julgamento do builder, a reverter se o CEO preferir:** uma tabela
   alias→id fixa foi recusada porque o corpus real mostra o MESMO `sonnet`
   servido por dois ids no mesmo harness (`claude-sonnet-5` ×86 e
   `claude-sonnet-5-5` ×17) e o MESMO `opus` por `claude-opus-5` ×692 e
   `claude-opus-5-5` ×3 — uma tabela dá vermelho no dia em que o substrato
   re-aponta o alias e verde sobre o furo que importa. Os pares alias→servido
   observados são IMPRESSOS (`alias_resolutions`), nunca julgados. Para
   apertar: trocar a comparação por conjunto de ids aceitos por alias, ao custo
   de uma cerimônia a cada geração.
5. **2.º predicado (AC-10, rail r2 P1):** spawn cujo arquétipo
   (`customAgentType`, senão `agentType`) está em `VETO_FLOOR_ROLES` tem de ter
   sido servido DENTRO de `VETO_FLOOR_ALLOWED` — MEMBRESIA, nunca prefixo de
   família —, declarado ou não. Os dois conjuntos são IMPORTADOS de
   `_lib.agent_frontmatter` (fonte assinada) na chamada, nunca copiados: cobre
   os 5 papéis (o `detect_veto_non_opus` post-hoc cobre 2 de 5 e testa
   prefixo). Declarado == servido é CEGO ao piso (`model: sonnet` servido como
   Sonnet casa consigo mesmo e é violação): por isso é um predicado à parte,
   não corolário do primeiro.

## 3. Veredito e códigos de saída

Do pior ao melhor: `RED` (violação: `MISMATCH` = nenhum turno servido no
declarado; `MIXED` = parte dos turnos; `FLOOR_BREACH`), `INCONCLUSIVE` (algo
que o check não conseguiu ler ou classificar, NOMEADO: declaração não
classificada, sidecar ilegível/grande demais, caminho recusado por symlink ou
fora do corpus, linha de transcript rasgada/sem data, turno servido sem id de
modelo, fonte do piso ilegível), `VACUOUS` (nada foi comparado — GREEN vácuo é
recusado), `GREEN`. A precedência é a ordem: violação nunca é mascarada por
leitura incompleta.

O exit code do CLI segue 0 (um achado de roteamento não quebra o relatório de
custo); `--assert-routing` o torna portão: **0 GREEN, 1 RED, 3 não provado**
(rc 2 segue sendo erro de argumento). O veredito é avaliado e impresso em TODA
execução, nos três caminhos: CLI humano, `--json` e os blocos dos dois
chamadores. Todo texto que vem de sidecar ou transcript (label, arquétipo, id
servido) é higienizado antes de imprimir — caractere não imprimível vira `?` —,
para que um label com quebra de linha não forje uma linha de veredito nem
dirija o terminal.

## 4. Controle vermelho → verde

**Pares sintéticos** (`RoutingInvariantControlsTests`): declarado `sonnet` e
servido `claude-opus-5-5` ⇒ RED/`MISMATCH`; declarado `sonnet` e servido
`claude-sonnet-5-5` ⇒ GREEN; o mesmo corpus vira de GREEN para RED exatamente
quando o spawn ruim entra. O dado da S361 (`sonnet` → `claude-sonnet-5-5`;
sem `model:` → `claude-opus-5-5`) é um teste: GREEN, com o spawn sem `model:`
contado como `undeclared`.

**Mutações do detector** (34 mutações aplicadas uma a uma ao código, suítes
`test_ceo_cost_transcripts.py` + `test_ceo_cost_integration.py` com `-k Routing or routing`
rodadas em cada; TODAS morrem — nenhuma sobrevive):

| mutação | testes que a matam |
|---|---|
| M1 alias always matches | 24 |
| M2 floor predicate removed | 6 |
| M3 no dedup (raw chunks) | 6 |
| M4 vacuous counted as green | 4 |
| M5 unknown alias read as no-claim | 7 |
| M6 path confinement removed | 1 |
| M7 exact id becomes prefix | 2 |
| M8 synthetic not ignored | 2 |
| M9 RED masked by inconclusive | 3 |
| M10 incomplete ignored | 23 |
| M11 floor by family prefix | 1 |
| M12 MIXED not flagged | 5 |
| M13 window ignored | 1 |
| M14 customAgentType ignored | 1 |
| M15 assert-routing rc always 0 | 1 |
| M16 routing not in render_block | 5 |
| M17 untrusted text printed raw | 7 |
| M18 transcript model printed raw | 5 |
| M19 session id printed raw | 4 |
| M20 routing reader drops usage-less turns | 13 |
| M21 dedup tie keeps the FIRST chunk | 5 |
| M22 unclassified counted before the window | 3 |
| M23 unreadable sidecar ignores the window | 3 |
| M24 message-less assistant turn not counted | 5 |
| M25 unplaceable spawn read as out of window | 1 |
| M26 chunk splits not counted | 4 |
| M27 usage-less turn dropped at the door | 11 |
| M28 unprovable terminal group not flagged | 9 |
| M29 every chunk assumed to carry usage | 9 |
| M30 unreadable record counted before the window (served) | 2 |
| M31 stamped record outside the window still counts | 2 |
| M32 placement ignores an in-window unreadable record | 1 |
| M33 unreadable record without timestamp read as outside | 1 |
| M34 unprovable group still feeds the comparison | 4 |

(Driver e saída em `mutation-run.txt` no checkpoint do builder; reproduzível
copiando o `.py` original, trocando um trecho e rodando `-k Routing`.)

### 4.1 Revisão cruzada (Codex 0.156.1, só leitura): rodada 1 (4 achados), rodada 2 (2) e rodada 3 (1, anexo), todos reproduzidos e curados

**Rodada 1.**

Cada cura tem controle vermelho→verde: os testes novos rodados sobre o código
ANTERIOR à cura ficam vermelhos (14 de 17 — os 3 que passam são guardas de
comportamento preservado) e verdes sobre o código curado (`red-run-old-module.txt`
no checkpoint); e cada cura tem suas mutações (M18–M27) mortas.

| achado | cura |
|---|---|
| **P1-1** veredito forjável no relatório COMPLETO: o id de modelo e o `sessionId` de um transcript ainda saíam crus na tabela de custo e no aviso de modelo não resolvido (só as linhas novas eram higienizadas) | todo texto de transcript (`model`, `sessionId`, `effort`) é higienizado NA ENTRADA, em `_extract_record`, uma vez; os quatro renderers (tabela do CLI, JSON, blocos de `ceo-cost.py` e `budget-summary.py`) herdam, e um print novo não tem como esquecer. Teste: lê o STDOUT inteiro do CLI em três cortes, o JSON, o `render_block` e os dois chamadores |
| **P1-2** turno divergente com `usage: null` dava GREEN: o leitor de custo o descarta sem contar e o detector dependia dele | o modelo servido é fato do TURNO, não da conta: a leitura de roteamento levanta a exigência de `usage` (`usage_optional`) — turno com `usage` nulo, ausente ou vazio é lido; registro de assistant sem objeto `message` é contado (`unreadable_assistant`) e vira INCONCLUSIVE. O leitor de custo não muda (teste: o total de custo continua sem o turno) |
| **P2-1** empate de `output_tokens` entre chunks: vencia o primeiro (`max` guarda o primeiro máximo), logo a ordem do arquivo decidia entre RED e GREEN por acidente | o desempate do `dedup()` é o chunk TERMINAL — o posterior no arquivo — (vale também para o metadado do custo); teste nas duas ordens, no `dedup()` e no veredito. Um contador informativo `chunk_model_splits` torna visível a mensagem cujos chunks discordam do modelo (nunca muda o veredito) |
| **P2-2** declaração fora da janela contaminava o portão: `unclassified` era contado antes do filtro de janela | a janela decide PRIMEIRO: sidecar ilegível, recusado ou com declaração não classificável só gateia a janela se o spawn tem turno nela; o de fora é contado como `out_of_window`; sem transcript nada foi servido (`no_served`); leitura rasgada que impede provar a posição segue fail-closed |

**Rodada 2.** O residual que a rodada 1 declarava (um chunk SEM `usage` que
divide o `message.id` com chunk COM `usage` perdia no desempate) **deixou de
existir**: o Codex o reproduziu como GREEN sem prova de roteamento e ele passou a
ser INCONCLUSIVE nomeado.

| achado | cura |
|---|---|
| **P1** `code-reviewer` declarado `claude-fable-5`; chunks do mesmo `message.id` com Fable (`output_tokens=7`) e depois Sonnet com `usage: null`: o chunk sem `usage` recebia zero tokens, perdia no `dedup()` e o resultado era GREEN, rc 0 (com o `usage` preenchido saía RED/MISMATCH/FLOOR_BREACH) | um `message.id` cujos chunks divergem em MODELO e em que algum chunk não tem `output_tokens` (`usage` nulo, ausente ou parcial) não tem terminal elegível por informação completa: conta em `chunk_terminal_unprovable` e o veredito é INCONCLUSIVE, com a razão nomeada — nunca GREEN. Chunk sem `usage` que CONCORDA no modelo não é divergência; divergência com todos os chunks completos segue só informativa (`chunk_model_splits`). `UsageRecord` ganhou `has_usage`; o leitor de CUSTO não muda. Testes nas duas ordens (o chunk sem `usage` depois e antes), com o `usage` preenchido (RED), com `usage` parcial, e RED que vence o INCONCLUSIVE |
| **P2** registro `message: null` de 20/08 numa janela que começa em 25/09 dava INCONCLUSIVE (rc 3, `out_of_window=0`): o contador subia antes de o timestamp ser consultado — também com `--until` e, via a posição do spawn, com sidecar ilegível ou declaração não classificada | o registro ilegível agora carrega o próprio timestamp (`unreadable_assistant_ts`); o que tem timestamp VÁLIDO fora da janela sai antes de contar como incompletude; só entra o que não tem posição temporal (linha rasgada, sem timestamp) ou o que está DENTRO da janela. A posição do spawn (`_placement`) usa a mesma regra: registro ilegível com timestamp fora vira «turno existente, fora» (`out_of_window`), com timestamp dentro vira «dentro»; sem posição segue fail-closed. Testes: antes do início, depois do `--until`, dentro (ainda gateia), sem timestamp (gateia), e spawn velho com declaração não classificada e sidecar ilegível |

**Rodada 3 (anexo, mudança mínima).** O Codex confirmou as curas da rodada 2
(janela temporal, `_placement`, custo) e reproduziu que a afirmação «terminal não
comprovável ⇒ INCONCLUSIVE» ainda era falsa: o grupo marcado
`chunk_terminal_unprovable` continuava alimentando violações — um `code-reviewer`
declarado Fable, um `message.id`, Sonnet (`output_tokens=7`) → Fable (`usage: null`)
dava RED/MISMATCH/FLOOR_BREACH, e com o `usage` final preenchido dava GREEN. Cura: um
grupo não comprovável é EXCLUÍDO da comparação (o terminal que o `dedup()` elegeria
é um palpite), então não gera violação nem atesta roteamento, e entra só como
INCONCLUSIVE nomeado; um RED só vence o INCONCLUSIVE quando vem de OUTRO grupo com
terminal comprovado. Testes: o contraexemplo do Codex nas duas ordens (Sonnet→Fable
sem `usage` e Fable sem `usage`→Sonnet: INCONCLUSIVE, zero violações, nenhum spawn
«comparado»), o contraste com `usage` completo (terminal eleito, GREEN), um spawn
com um grupo comprovado violador ao lado de um grupo incerto (RED só pelo grupo
comprovado, `served` sem os modelos do incerto) e o grupo incerto que não atesta um
spawn. Mutações M28 e M34 as matam.

## 5. Medição no corpus REAL (agregado; só leitura; 2026-10-02)

Rodado pelo instrumento sobre o corpus local de transcripts (1.950 sidecars no instante da medição; o corpus vivo cresce a cada spawn),
janela inteira (`--since 36500d`) e janela de 30 d. Só contagens; nenhum
conteúdo de transcript foi lido além de `message.model`/`timestamp`.

| medida | janela inteira | 30 d |
|---|---:|---:|
| spawns com `model:` declarado | 1.091 | 1.091 |
| declarados COMPARADOS (servido lido) | 887 | 823 |
| spawns comparados, distintos (um declarado VETO conta 1) | 888 | 824 |
| arquétipo VETO checado no piso | 18 | 18 |
| sem servido (sem transcript / só `<synthetic>`) | 204 | 204 |
| fora da janela | 0 | 64 |
| **MISMATCH** (nenhum turno no declarado) | **0** | **0** |
| MIXED | 3 | 3 |
| FLOOR_BREACH | 4 | 4 |
| INCONCLUSIVE (não classificado/ilegível) | 0 | 0 |

Leituras:

- **Zero `MISMATCH` em 887 spawns comparados**: nesta máquina, em todas as
  builds medidas, `model:` rodou como declarado. O K-B1 NÃO disparou.
- **Os 4 `FLOOR_BREACH` SÃO os 4 spawns de sonda below-floor do AC-10
  (S343)**: 2 pelo rail Workflow (`agent-af1621b0e2266543e`, `sonnet`; e
  `agent-a7ef0363d48a1bd99`, `haiku` — os dois ids estão em
  `us4-inherit-vs-pin-S340.md` §Célula below-floor) e 2 pelo `Agent` tool
  (rotulados «AC-10 below-floor probe …»). O detector acha, sozinho e sem
  lista de exceção, exatamente o conjunto que o plano documenta — controle
  positivo em dado real, com verdade de campo independente. Eles ficam RED
  enquanto estiverem na janela (verdadeiros positivos; K-A3 não os conta
  como ruído).
- Os 3 `MIXED` são spawns declarados `claude-opus-5-5` (2) e `claude-fable-5`
  (1) em que uma minoria de turnos (5, 2 e 6) foi servida por
  `claude-opus-4-8`: consistente com fallback do harness. O detector reporta o
  FATO (modelo servido ≠ declarado em parte dos turnos), não a causa.
- `chunk_model_splits` (contador informativo) = 1 no corpus medido: uma mensagem
  cujos chunks discordam do modelo; não entra no veredito.
- **Achado colateral, fora do escopo e NÃO curado aqui:** o relatório de custo
  imprime `claude-sonnet-5-5` como modelo «não resolvido na tabela de preços»
  (1.282 turnos a US$ 0 na janela de 30 d); o `_EMBEDDED_PRICING`/`cost-table.yaml` não tem a
  linha, então o gasto de Sonnet 5.5 está SUBCONTADO no corpus medido. Curar é
  emenda do ADR-149 + linha de preço + `test_model_fleet_presence` — wave
  própria.
- Custo do detector: ~3 s sobre ~1.950 sidecars (a varredura de custo da mesma
  janela leva ~6 s).

## 6. Critério de morte pré-registrado (fonte: docstring do módulo)

Fixado ANTES da primeira rodada real; mudar um número é emenda de plano, nunca
edição de passagem; um teste (`RoutingPreRegistrationTests`) quebra se um
critério for apagado ou suavizado.

- **K-A — o detector morre (reconstruir ou aposentar; nunca ajustar em volta):**
  K-A1 o par de controle sintético deixa de dar RED/GREEN em qualquer CI;
  K-A2 execução com ≥ 20 sidecars e `declared == 0` numa janela em que o
  operador SABE que houve spawn com `model:` ⇒ o esquema do sidecar derivou, o
  detector está cego até ser refeito (os contadores `sidecars`/`declared`/
  `undeclared` saem em toda execução para isto ser verificável); K-A3 três
  violações DISTINTAS (3 sidecars) julgadas FALSO POSITIVO por escrito ⇒ o
  predicado que disparou é re-escopado por ADR ou apagado (verdadeiro positivo
  — sonda deliberada, fallback real — não é ruído; não existe lista de
  supressão, por desenho).
- **K-B — o que o RED significa (a alavanca, não o detector):** K-B1 um
  `MISMATCH` num sítio que declara `model:`, REPRODUZIDO por UM spawn de
  controle com a mesma declaração na mesma build ⇒ `model:` não roteia naquela
  build: os sítios explícitos da W1/AC-3a ficam inertes ali, a medição do
  ADR-144 ganha emenda e a premissa «rotear builders por `model:`» fica
  suspensa até uma build cujo controle passe; K-B2 um `FLOOR_BREACH` zera o
  relógio do fim da transição da W3 («1 wave completa sem violação de piso
  registrada pelo detector permanente»).

## 7. Residuais declarados (o que este detector NÃO afirma)

1. **O assento** (sessão principal) não tem sidecar: seu modelo é o pin do
   `settings.json`, fora do alcance.
2. **O trilho MITIGADO** (`general-purpose` com persona injetada): o sidecar
   registra `general-purpose`, não o arquétipo; um VETO despachado assim roda
   no modelo herdado sem que o predicado de piso o veja. É a lacuna que o
   AC-10 já nomeia; o 2.º predicado só cobre quem o sidecar identifica.
3. **Spawn que não declara `model:`** não afirma nada (`undeclared`); se o
   harness deixasse de gravar `model` no sidecar, o spawn viraria `undeclared`
   em silêncio — é o K-A2 (cegueira), verificável pelos contadores.
4. **A família é o piso da afirmação sobre alias**: `sonnet` servido por um
   Sonnet mais antigo passa. O que o detector pega é a classe do K2 (o
   substrato ignora `model:` e herda o assento) e o piso VETO por membresia.
5. **Se o `model:` de um sítio é o CERTO para a tarefa** é o AC-3a/W1 (tabela
   §2b), não este detector.
6. **«Permanente» significa avaliado em toda execução do instrumento**, não
   agendado: nenhum workflow/cron/CI roda o instrumento sozinho neste patch.
   Ligá-lo a um portão (`--assert-routing` no `nightly-hygiene`, p.ex.) é
   decisão separada e barata; o código já devolve rc 1/3 para isso.
7. Em janela que inclua spawns antigos de sonda (as 4 do AC-10), o veredito é
   RED por desenho até eles saírem da janela.

## 8. Linha para o PLAN-186 (CEO)

Marcar **`- [ ] AC-13 (W0) …` (linha 199) → `[x]`** com a nota datada
`— ✅ S361 (2026-10-02): …` apontando este relatório. Texto sugerido, curto:

> detector de roteamento no ar landado no instrumento de custo
> (`ceo-cost-transcripts.py`): servido (`message.model`) == declarado (`model`
> do sidecar) por spawn, alias por família e id exato, mais o 2.º predicado de
> piso VETO por membresia em `VETO_FLOOR_ALLOWED` (o requisito que a nota do
> AC-10 nomeou); veredito RED/INCONCLUSIVE/VACUOUS/GREEN avaliado e impresso em
> toda execução, `--assert-routing` como portão (0/1/3); critério de morte
> K-A1..K-B2 pré-registrado no docstring e pinado por teste. Controle: par
> sintético vermelho→verde e 34/34 mutações mortas; no corpus real, 0 MISMATCH
> em 887 spawns comparados e os 4 FLOOR_BREACH são exatamente as 4 sondas
> below-floor do AC-10. Residuais: trilho mitigado e assento fora do alcance;
> ligar a um portão agendado é decisão separada. Relatório:
> `PLAN-186/w0/ac13-routing-invariant-S361.md`.

Efeito colateral para o AC-10: a «perna (iii) post-hoc» do piso deixa de ser só
`detect_veto_non_opus` — este detector cobre os 5 papéis, por membresia, nos
DOIS rails (ele lê transcript, não telemetria `agent_spawn`, logo não herda a
cobertura NULA do rail Workflow).

## 9. Verificação

Bateria do CI (`pytest .claude/hooks/tests/ .claude/scripts/tests/
.claude/scripts/optimizer/tests/`, `PYTHONPATH=.`, passe paralelo
`-n auto -m 'not serial'` e passe `-m serial`), rodada em clones descartáveis
do MESMO commit de `main`, uma árvore sem o patch (linha de base) e uma com o
patch final (depois das curas das três rodadas da revisão cruzada). Conjunto exato de falhas:
**∅ nos dois passes, nas duas árvores.** Os números absolutos de cada passe
ficam em `suites-result.txt` no checkpoint do builder (eles se movem a cada
commit de `main`, então não são citados aqui); o que este patch acrescenta é
exatamente **+85 testes** (80 em `test_ceo_cost_transcripts.py`, 5 em
`test_ceo_cost_integration.py`): 84 no passe paralelo e 1 no serial.

No passe serial o par xfailed/xpassed oscila com a carga da máquina: é o
orçamento advisory de relógio
`test_tool_lifecycle_observe::test_observe_write_path_under_2ms_p99` (xfail não
estrito), alheio ao patch e confirmado isolado nas duas árvores — não é falha.
Uma rodada ANTERIOR do patch, com a máquina carregada por outros builders (load
12–26), teve 4 falhas de testes lentos alheios ao patch (`test_ceo_diagnose`,
`test_check_installer_write_safety` ×2, `test_census_runtime`) que passaram
isoladas e na rodada seguinte — a classe de flake de orçamento de tempo
absoluto já registrada no CLAUDE.md §5.

Gates de corpus sobre a árvore STAGED (`git add -A` antes, nenhuma edição
depois), todos rc 0: `check-test-env-hygiene`, `check-claude-md-claims`,
`verify-counts.sh` completo (sem drift), `validate-governance.sh` COMPLETO
(`Errors: 0`; `Warnings: 65`, igual à linha de base), `check_contamination`,
`check-staleness` (10 achados, igual à linha de base). Oráculo
`--is-canonical` = 0 nos 5 paths.
