# Como o orquestrador deve funcionar — síntese S339

**Data:** 2026-09-02 · **Sessão:** S339 · **Autor:** VP Engineering (skill `architecture-decisions`)
**Insumos:** os cinco relatórios de `docs/research/s339-orchestrator-study/` (`01-academia.md`,
`02-claude-api.md`, `03-claude-code-substrate.md`, `04-parallelism.md`, `05-finops-routing.md`),
mais cinco fatos verificados pelo CEO nesta sessão (F1–F5, §2).

> **Nota de moeda:** todo dólar neste documento é **API-equivalente**, um proxy de magnitude
> relativa entre modelos. O Owner opera por **assinatura** (janela de 5 h + semanal), não por
> fatura de API. A decisão do assento é, portanto, uma decisão de **quota** — e quota se mede,
> não se deriva de preço (05 §3.2, §Limites 2).

---

## 1. Resumo executivo

A política proposta, em uma linha por papel (detalhe e justificativa em §6):

| papel | modelo | effort |
|---|---|---|
| assento CEO / sessão | `claude-fable-5-1` | `high` |
| sessão que lança night-run | `claude-fable-5-1` | `high` |
| VETO (5 arquétipos) | `claude-fable-5-1` (hoje `claude-fable-5`) | `max` |
| refutador adversarial não-VETO | `claude-opus-5` | `xhigh` |
| síntese de debate / REDUCE | `claude-fable-5-1` | `max` |
| builder canônico / KERNEL | `claude-opus-5` | `max` |
| builder livre / derivação / docs | `claude-sonnet-5` | `high` |
| pesquisa / leitura / censo | `claude-sonnet-5` (Haiku só com evidência de torneio) | `high` |

As três decisões que cabem ao Owner:

1. **Assento.** Autorizar o A/B de 7 dias (§6.3) antes de escolher entre Fable 5.1 e Opus 5. Em dólar os dois empatam (Δ 5,5 %, 05 §1.4); em quota não há número oficial (05 §3.2).
2. **Pins VETO.** Migrar os 5 arquétipos de `claude-fable-5` para `claude-fable-5-1` — camada T, Owner-signed. O `code-reviewer` roda no rail nativo, então o pin dele **vale** e paga o cache read mais caro da frota (§2, F2).
3. **Builders mecânicos em Sonnet 5.** Ratificar o roteamento (camada P na execução, doutrina em ADR-052/144) com o critério de morte já escrito: dois P1 consecutivos que o refutador não pegue ⇒ reverter (05 §5.4).

---

## 2. Fatos medidos

| # | fato | valor | fonte |
|---|---|---|---|
| 1 | Custo 30 d (2026-08-03→09-02), API-equivalente | **$11.001,49** pelo instrumento `ceo-cost-transcripts.py` (W0 S339, após a cura do dedup progressivo apontada pelo Codex: 65,6 % dos `message.id` de subagente têm `output_tokens` crescente e o first-write-wins descartava o snapshot final). O relatório 05 dizia $11.137,97 — delta −1,2 %, dentro do AC-1 | W0 `instrument-S339.md` §3; 05 §1.3 |
| 2 | Custo por dia ativo / mediana por sessão | $384,07 · dia · $108,75 mediana · $658,38 sessão mais cara | 05 §1.3 |
| 3 | Referência pública Anthropic | ~$13/dia, $150–250/mês por dev — o repo opera **~13× fora** desse envelope | 05 §P1-3 |
| 4 | Mix de tokens | **cache read = 96,8 % dos tokens e 61,0 % do custo**; cache write 3,0 %/31,0 %; output 0,21 %/7,9 %; input fresco 0,01 % | 05 §1.4 |
| 5 | Preço de cache read (a variável que decide a fatura) | haiku $0,10 · sonnet-5 $0,20 · **fable-5-1 $0,25** · sonnet-4-6 $0,30 · **opus-5 $0,50** · **fable-5 $1,00** por MTok | 05 §1.4 |
| 6 | Trocar Fable 5.1 → Opus 5 no perfil medido | economiza **5,5 %**, não 50 % — o sticker sugere 2×, a carga entrega 1,06× | 05 §1.4 |
| 7 | Night-run S338 — assento vs fan-out | assento $457,27 + 7 agentes $223,50 = **$680,77**. **O assento custa 2× o fan-out que despacha** | 05 §2.2 |
| 8 | Night-run S338 — políticas alternativas | A tudo Fable 5.1 $223,50 · B tudo Opus 5 $191,74 (−14,2 %) · C misto $136,62 (−38,9 %) | 05 §2.2 |
| 9 | Herança de modelo | `CLAUDE_CODE_SUBAGENT_MODEL: "inherit"` + **10 sítios reais de `agent()` sem `model:`** (17 ocorrências textuais, 7 em comentários — corrigido pela W1 S339) nos 4 workflows + 3 no molde do night-run + **0 `subagent_type`** nos scripts locais ⇒ tudo herda o assento | 05 §P0-2, §4.3 |
| 10 | Override de modelo é honrado (F1) | spawns com `model: sonnet` serviram `claude-sonnet-5`, com `model: opus` serviram `claude-opus-5` (transcripts desta sessão). `opts.model` do Workflow honrado desde 2.1.237 (probe `wf_9ddadaab-12f`, n=2) | CEO S339; 03 §3 |
| 11 | Pin de arquétipo não governa custo | o `model` do dispatcher vence o pin; `llm-finops-architect.md:6` diz `claude-sonnet-4-6` e o agente rodou `claude-opus-5 / xhigh` | 05 §P1-1 |
| 12 | **Exceção do rail nativo (F2)** | o rail MITIGADO despacha como `general-purpose` e ignora o pin (ADR-082:131-132). O `code-reviewer` é **o único arquétipo que segue no rail nativo** (ADR-082:93-94, 147-148) — logo seu pin `claude-fable-5` (`code-reviewer.md:6`) **se aplica** e paga **$1,00/MTok de cache read: 4× o 5.1 e 2× o Opus 5** | verificado S339; 05 §1.4 |
| 13 | Instrumento de FinOps cego | `ceo-cost.py --since 30d` = **$0.00**; audit log tem **4 tokens de input e 8 de output em 61.066 eventos**; `budget-summary.py` diz `Tokens in 4 / out 8 / total 646.597` na mesma saída | 05 §P0-1 |
| 14 | `totalTokens` do Workflow é contexto, não fatura | os "2,28 M tokens" do S338 são a soma dos **picos de contexto**; o faturável sem cache read é 13.394.635 e o bruto 226.678.514 — subestima por 2 ordens de grandeza | 05 §P1-2 |
| 15 | Effort move só 7,9 % do custo | `max` $1.810 (Fable) + $1.032 (Opus 5); baixar a frota de `max` para `high` tem teto de **~$400/mês** contra $4.664 de trocar `fable-5` por `fable-5-1` | 05 §1.5, §P2-1 |
| 16 | CI — Validate | **~23m27s** ponta a ponta; 6 jobs paralelos; o job `validate` sozinho leva 22m22s, com 3 steps concentrando 19m31s (**87 %**) | 04 §(b) |
| 17 | CI — Smoke Install | **~87m50s**, 1 job, ~26 steps seriais; os 2 maiores steps somam 50m20s (**57 %**) | 04 §(b) |
| 18 | LAND V-block | bash linear, sem `&`/`wait`; o item caro é `verify-counts` (~3 min declarado) e domina sozinho | 04 §(a) |
| 19 | Night-run S338 — wall clock | 2h29m02s totais; **um agente consome 2h05m56s = 84 %** — e é o único que **não fechou** (`status=partial`, sem rodada limpa) | 04 §(d) |
| 20 | Quota — o que é OFICIAL (F4) | janela de 5 h; limite semanal compartilhado entre modelos; limite **por família** (bater Opus ≠ bater Sonnet); Fable capado em **50 % do limite semanal**; Fable "consome os limites mais rápido"; TTL de cache 1 h em assinatura; extended thinking não desliga em Fable | 05 §3.1 |
| 21 | Quota — o que **não** é oficial | **não existe multiplicador Fable-vs-Opus publicado.** Qualquer razão numérica seria estimativa | 05 §3.2 |

---

## 3. O que perdemos de evolução

### 3.1 API Claude — as 5 lacunas (02 §(a))

| # | lacuna | por que importa aqui |
|---|---|---|
| 1 | **Refusal fallback** (`fallbacks:"default"`) | o adapter já **detecta** recusa (`model_refusal_observed`, `claude.py:957`) e não se recupera dela. Night-run autônoma sob Fable 5.1 para no meio |
| 2 | **Advisor tool** para o caso de **custo**, não de VETO | `SOTA-GAP-MAP.md:70,92` já a nomeia como "marquee cost-quality lever" não testada. A proibição de governança (`HONEST-LIMITATIONS.md:112`) vale para VETO, não para triagem barata |
| 3 | **Effort por mensagem** (`mid-conversation-output-config-2026-07-01`) | trocar effort hoje é top-level e invalida o cache. O repo já mediu esse re-pay: **F ≈ 97k tokens** |
| 4 | **Cache 1h TTL** no adapter | `budget-summary.py` já modela o multiplicador por modelo; o adapter só grava `ephemeral` 5 min |
| 5 | **`thinking.display:"updates"`** | substitui o header datado `interleaved-thinking-2025-05-14` e dá visibilidade em turnos longos |

**O que NÃO se aplica ao harness** (02 §(b)): Managed Agents inteiro (o perímetro de hooks local
não atravessa um container hospedado; multiagent compartilha filesystem e quebra FILE ASSIGNMENT
por construção), o Claude Agent SDK (produto diferente — este repo já roda dentro do Claude Code),
e todas as features de request (fast mode, task budgets, tool search, structured outputs, context
editing, Batches, cache) que só existem no adapter opcional sob `CEO_LIVE_CLAUDE=1`, nunca no fluxo
default do CEO e dos subagentes nativos.

### 3.2 Substrato 2.1.258 (03)

O ledger `substrate-watch.json` responde `status: current` para 8 componentes, mas `last_seen` de
`claude_code` é **2.1.198 (2026-07-01), 60 versões atrás**, e cada linha do `--check` mostra
`installed=(not probed)`. É a classe "instrumento verde cuja pergunta envelheceu": ele comparou o
ledger consigo mesmo (03 §1).

As **5 sondas** que valem rodar (03 §5):

1. **Cura textual dos 2 sítios «INERT»** — `PLAN-178:402-403` (AC-3) e `eval-baseline-n20.js:3,284,547` ainda afirmam que `opts.model` do Workflow é inerte. F1 e ADR-144 (emenda S328) refutam. O mecanismo de subprocess do `eval-baseline-n20.js` continua correto **por desenho**; só o texto está errado.
2. **`TeammateIdle` / `TaskCompleted` são hook events REAIS hoje** — `team.md:520-527` os trata como hipotéticos. O mecanismo existe; falta a decisão de adoção.
3. **`PreModelSwitch` / `PostModelSwitch`** (novos em 2.1.251) — superfície de **tamper de tier**: um `/model` ou `/fast` no meio de uma cerimônia troca o modelo sem nenhum rail perceber.
4. **Hooks 31 → 33.** A doc oficial lista **33** hook events; a última medição comportamental (probe `wf_d7af49d9`, 2.1.237) viu **31**; `.claude/settings.json` religa **15**. Os outros 18 — incluindo os quatro acima — não têm nenhum hook, logo zero visibilidade de audit log. Isso dispara o próprio gatilho de drift do ADR-191 §4.
5. **`CLAUDE_CODE_PROJECT_DIR_NAME`** (2.1.234) — mesma classe de carrier de nome de diretório que motivou a `wave-cli`; pode estar fora de `WHOLE_DIR_OVERRIDE_CARRIERS`.

As **3 que ficam fora** (03 §"Três que devem continuar fora"): Agent Teams como topologia (ainda
recebendo fixes de comportamento básico até 2.1.251 — resposta final não chegando ao líder,
teammate preso em tmux); rotinas cloud `/schedule` (tiram a sessão do TTY/GPG que toda cerimônia
assume); nesting além de depth 1 (decisão FLAT deliberada, harvest item H11).

Achado colateral com efeito de custo: **2.1.247 removeu o "Default teammate model" do `/config` —
teammates agora usam o modelo do líder**, o que é a mesma armadilha de herança do fato 9, agora
embutida no substrato.

### 3.3 Academia — top 5 (01 §Top 5)

| # | achado | rótulo |
|---|---|---|
| 1 | **Dependência sequencial no Step 0** (Kim et al., arXiv:2512.08296): multi-agente vai de **+80,8 %** em tarefa decomponível a **−70,0 %** em planejamento sequencial | **[LACUNA]** — o Step 0 decide por sobreposição de arquivos, não por dependência lógica |
| 2 | **MAST** (arXiv:2503.13657) e **auto-correção falha sem feedback externo** (arXiv:2310.01798) fundamentam V0–V3 e ADR-186 | **[JÁ ADOTADO]**, mas afirmado sem citação no `PROTOCOL.md` |
| 3 | **Effort máximo não é dominante** (arXiv:2604.10739 + platô de 2505.20522): em budget alto o modelo pode abandonar um raciocínio correto | **[LACUNA]** — o skill `effort` trata effort como dial monotônico |
| 4 | Roteamento por **regra** e não por classificador aprendido (RouteLLM, arXiv:2406.18665) | **[JÁ ADOTADO]** como escolha deliberada — auditabilidade acima de otimização marginal; falta dizer isso |
| 5 | **Cascata de confiança barata→cara** (FrugalGPT 2305.05176; 2605.06350) para L1–L2 | **[LACUNA]**, valor incerto até medir |
| — | **Verificador único poda caminhos corretos** (arXiv:2502.00271): com muitos candidatos o verificador passa a performar **pior** que amostragem simples | **[CONTRADIZ]** parcialmente o V2 como "único portão de verdade" — ver §4 |

---

## 4. Diagnóstico do orquestrador atual — cinco erros de forma

**4.1 Herança silenciosa é a política de fato.** Nenhum dos 10 sítios reais de `agent()` (17 ocorrências textuais, 7 em comentários — W1 S339) passa `model:`,
não há um único `subagent_type` nos scripts locais, e `CLAUDE_CODE_SUBAGENT_MODEL: "inherit"` fecha
o caso (05 §4.3). O resultado: a política de roteamento do repo é "o que o assento estiver rodando".
Isso não é uma decisão errada — é a **ausência** de decisão, tomada 10 vezes por omissão.

**4.2 Os pins não vencem o dispatcher, exceto num lugar.** O `model:` do frontmatter é lido só por
`validate_veto_floor_models` para checar o **piso de capacidade**; quem despacha com `model`
explícito o sobrescreve em silêncio (05 §P1-1). A camada T governa o teto dos papéis VETO, não o
custo. A exceção é o rail nativo: o `code-reviewer` é o único arquétipo lá, seu pin vale, e é
justamente o modelo mais caro da frota por cache read (§2, F2).

**4.3 O Step 0 pergunta a coisa errada.** Ele decide paralelismo por **sobreposição de arquivos**
("0 arquivos em comum → paralelo"). Kim et al. mostram que a variável que decide é **dependência
sequencial**: uma tarefa em que a saída de um agente alimenta o outro, despachada em paralelo, custa
até −70 % de performance mesmo com zero colisão de path (01 §1.3). A Anthropic diz o mesmo pelo lado
do custo: multi-agente consome ~15× mais tokens e não se justifica em tarefas de alta
interdependência (01 §1.1).

**4.4 Verificador único é uma fragilidade estrutural, não um bug.** O V2 trata o veredito do Codex
como o único portão de verdade LLM, fail-closed. O paper 2502.00271 mostra o mecanismo de risco em
espécie: um verificador imperfeito pode podar todos os caminhos corretos conforme o espaço cresce
(01 §2.3). A resposta correta **já existe e é o V3** — a cerimônia GPG do Owner é o caminho de
recuperação para "o Codex aprovou e errou". O que falta é dizer isso no `PROTOCOL.md`: V3 não é
burocracia, é a mitigação nomeada de um verificador com taxa de erro não-zero.

**4.5 Não há teto de effort.** A doutrina trata effort como dial monotônico. A literatura mostra
platô e reversão (01 §4.2), e a medição mostra que effort move apenas 7,9 % do custo (05 §1.5).
Logo **effort é uma decisão de qualidade, não de custo** — e a variável que deve governá-la não é o
blast radius, é a **incerteza de especificação**. Um builder canônico com derivador anchor-exact
está totalmente especificado. O item do S338 que consumiu 84 % do wall-clock e nunca fechou era um
draft de design sem especificação (04 §(d)). Effort alto pertence ao segundo caso, não ao primeiro.

---

## 5. Paralelização

> Nota (AGENTS.md §0): os tempos desta seção são wall-clock de gates e CI DESTE repo, medidos ou estimados como alvo de AC. Não constituem claim de velocidade do framework — o repo mantém a posição de que não há speedup geral.

Ordenado por ganho sobre risco (04 §Tabela final). Esforço em tokens + sessões (ADR-081).

| # | oportunidade | serial hoje | paralelo | corte | risco | esforço | status |
|---|---|---|---|---|---|---|---|
| 1 | Matrizar o job `validate` em 3 jobs (unit hooks / unit scripts / installer-harness-matrix) | 22m22s, 87 % em 3 steps | ~13 min (bound: `hook-tests-python-matrix 3.12`, 10m39s) | alvo a medir (AC-6) | baixo-médio | 80–150k tokens / 1–2 sessões | **[NOVO]** |
| 2 | Matrizar Smoke Install por step (`strategy: matrix`) | 87m50s, 26 steps | ~35–40 min (bound: historical-adopter, 32m43s) | alvo a medir (AC-6) | médio — reescrita completa, runner-minutos totais sobem, nenhum teste de "matrix correta" existe | 150–300k tokens / 2–3 sessões | **[NOVO]** |
| 3 | Rail patch-track ∥ materials-track (2 `codex exec` concorrentes) | sequencial | latência de espera eliminada | — | baixo — já rodam em árvores fisicamente distintas (sombra vs viva + `git add -N`) | mudança de runbook | **[NOVO]**, já praticado informalmente |
| 4 | Usar `wf_e3144372-b04` como piloto observacional retroativo do E5 (WIP=2) | — | — | — | baixo | 30–50k tokens / 1 sessão | **[JÁ NO PLAN-172]** (E5), gap de instrumentação |
| 5 | Decompor pacotes grandes/incertos antes do fan-out | 1 builder = 84 % do wall-clock | depende da divisibilidade | — | médio-alto — fan-out sem passe de integração degrada em silêncio | arquitetural, não estimável sem caso | **[NOVO]** |
| 6 | Paralelizar o V-block do LAND | ~3–5 min, dominado por `verify-counts` | ganho de dezenas de segundos | — | **alto** — reabre a classe de corrida na cadeia HMAC viva (S326, 19.344 elos não-atribuíveis) e exige re-certificar o `trap/restore` endurecido por 5+ rodadas de rail | — | **NÃO FAZER** |

Pré-condições registradas: (1) confirmar ausência de estado partilhado via `GITHUB_ENV`/artifact
entre os 3 blocos do `validate`; (2) preservar a ordem "fetch do pin + deepen ANTES dos e2e que
precisam de histórico" e replicar checkout+deepen por job; (5) passe de integração obrigatório se os
sub-pacotes compartilharem símbolos.

Duas notas do 04 que mudam o enquadramento: rodadas **dentro** de uma mesma track de rail são
serialmente obrigatórias por protocolo (cura → re-derivação → revisão), não por limitação de
ferramenta; e o E6 do PLAN-172 (barato antes de caro) **já está implementado** no desenho do V-block
— o corte do `--dry-run` fica deliberadamente depois dos gates baratos e antes dos caros.

---

## 6. Matriz papel × modelo × effort

### 6.1 A matriz

| # | papel | modelo | effort | justificativa | camada | muda vs hoje? |
|---|---|---|---|---|---|---|
| 1 | assento CEO / sessão | `claude-fable-5-1` | `high` | 71 % da fatura e cache read a $0,25/MTok; `max` só move os 7,9 % de output (05 §1.5) | **T** (`settings.json` `model`) | pin declarado é `claude-opus-5`, execução já é Fable por escolha de `/model` do Owner — **não tocar no pin antes do A/B do §6.3**; o vencedor do A/B vira o pin |
| 2 | sessão que lança night-run | `claude-fable-5-1` | `high` | mediu $457 de $681 no S338 — o assento é o alvo, não os agentes (05 §2.2) | **T** | mesma linha 1 |
| 3 | VETO (code-review, security, identity, incident, threat) | `claude-fable-5-1` | `max` | capacidade é o critério do piso, mas o `code-reviewer` roda no rail nativo e paga $1,00/MTok — 4× o 5.1 (F2) | **T** (`agents/*.md` + `VETO_FLOOR_ALLOWED`) | **SIM** — hoje `claude-fable-5`; exige ADR-149 rota (a)/(b) |
| 4 | refutador adversarial não-VETO | `claude-opus-5` | `xhigh` | refutar exige profundidade e **sai da família Fable**, aliviando o teto de 50 % semanal | P | formaliza o que já ocorre por herança |
| 5 | síntese de debate / REDUCE | `claude-fable-5-1` | `max` | agrega N lanes; erro aqui contamina o veredito inteiro | P | explicitar `model:` |
| 6 | builder canônico / KERNEL | `claude-opus-5` | `max` | toca hooks KERNEL sob cerimônia GPG; um defeito custa uma wave | P | explicitar `model:` |
| 7 | builder livre / derivação / docs | `claude-sonnet-5` | `high` | derivação anchor-exact é mecânica e verificável; **−66 %** no perfil S338 (05 §P0-2) | P | **SIM** — hoje herda o assento |
| 8 | pesquisa / leitura / censo | `claude-sonnet-5` | `high` | medido S339: 4 pesquisadores em Sonnet 5 entregaram os relatórios 01–04 com citações verificadas; Haiku ($0,10/MTok) só com evidência de torneio (doutrina ADR-052) | P | **SIM** — hoje herda o assento |

**Regra que governa a coluna effort:** escale por **incerteza de especificação**, não por blast
radius. Tarefa com derivador determinístico e critério de aceite em bytes ⇒ `high`. Tarefa de design
sem forma fechada ⇒ `max`. Isso reconcilia 01 §4.2 (effort máximo não é dominante) com 05 §1.5
(effort é a alavanca financeira mais fraca): como effort quase não custa, o argumento contra `max`
por toda parte é de **qualidade**, não de dinheiro.

**Pré-requisito mecânico das linhas 4 a 8:** `model:` explícito em cada `agent()`. Sem isso,
`CLAUDE_CODE_SUBAGENT_MODEL: "inherit"` anula a matriz inteira (05 §5.1, nota).

### 6.2 Os quatro cenários

Sobre o mesmo perfil de tokens medido em 30 dias; só o modelo muda (05 §5.2).

| cenário | assento | subagentes | custo 30 d | vs real | vs (i) |
|---|---|---|---:|---:|---:|
| real medido | mix histórico | mix | $11.137,97 | — | +36 % |
| **(i) atual** | `fable-5-1` | 100 % `opus-5` | **$8.209,02** | −26 % | — |
| **(ii) hipótese do Owner** | `fable-5-1` orquestra+verifica | 100 % `opus-5` em `max` | **$8.209,02** | −26 % | **0 %** |
| **(iii) alternativa do CEO** | `opus-5` `xhigh` | 80 % `sonnet-5` + 20 % `fable-5-1` | **$6.522,17** | −41 % | **−21 %** |
| **(iv) híbrido** | `fable-5-1` | 80 % `sonnet-5` + 20 % `fable-5-1` | **$6.840,49** | −39 % | −17 % |

**Por que (ii) "formaliza o presente".** O assento já roda Fable e os subagentes já rodam Opus 5 —
não por decisão, mas porque o dispatcher passa `model` e o resto herda. (ii) descreve o estado atual
com precisão e por isso entrega exatamente **$0** de mudança. Não é uma objeção à hipótese: é a
constatação de que ela já venceu, sem nunca ter sido escrita.

**Onde está o delta entre (iii) e (iv).** Mover o assento de Fable 5.1 para Opus 5 rende **−$318**,
saldo magro de duas forças que quase se cancelam: o cache read **encarece** (+$1.555, $0,25→$0,50)
enquanto cache write e output **baratejam** pela metade (−$1.401 e −$470). Mover 80 % dos subagentes
para Sonnet 5 rende **−$1.369**. A alavanca de dólar está nos subagentes mecânicos, não no assento.

### 6.3 [DIVERGÊNCIA] assento-Fable vs assento-Opus — como resolver

O CEO defendia (iii); o relatório 05 recomenda (iv). Em dólar a diferença entre os dois é
$318/mês — **4,6 % do cenário**, dentro da margem da hipótese de split 80/20 que sustenta ambos
(05 §Limites 4: um split 50/50 moveria os dois em ~$450/mês). **O dólar não distingue.**

A moeda que distingue é a quota, e ela não tem número oficial (F4, 05 §3.2). Portanto: **não decidir
por média nem por argumento — medir.**

**Desenho (05 §5.4).** Sete dias, alternância diária. Braço A (dias 1-3-5-7): assento em
`claude-fable-5-1`. Braço B (dias 2-4-6): assento em `claude-opus-5`. Subagentes idênticos nos dois
braços (Sonnet 5 mecânico, Opus 5 refutação) para não confundir efeitos.
**Métrica primária:** minutos de trabalho útil por janela de 5 h antes do primeiro bloqueio.
**Instrumento:** `/usage` no fim de cada janela + o agregador de transcripts + contagem de eventos
`session limit`/`Opus limit`/`Sonnet limit`.

| observação | decisão |
|---|---|
| Braço B (Opus) entrega **≥ 20 %** mais minutos úteis | adotar **(iii)** — o assento sai de Fable; +$318/mês aceito |
| Diferença **< 10 %** em qualquer direção | adotar **(iv)** — a quota não distingue; fica o assento mais barato em API |
| Braço A (Fable) entrega **≥ 20 %** mais minutos úteis | manter assento Fable; a hipótese de pressão de quota está refutada e a investigação vira **contexto longo**, não modelo |
| **< 4 janelas** de 5 h completas em qualquer braço | **experimento inválido** — não decidir, repetir |
| Qualquer braço atinge o teto de **50 % semanal de Fable** antes do dia 7 | registrar dia e percentual — é o número que a Anthropic não publica, e passa a ser a evidência principal |

---

## 7. Plano de adoção por retorno

| # | item | ganho | camada | esforço | depende de |
|---|---|---|---|---|---|
| 1 | `model:` explícito nos **10 sítios reais de `agent()`** dos 4 workflows + nas 3 do molde de night-run; builders mecânicos em Sonnet 5 | **−$1.369/mês**; encerra a herança silenciosa | **livre** (P) | 40–80k tokens / 1 sessão | ratificação da decisão 3 (§1) |
| 2 | **`ceo-cost.py` derivar de `message.usage`** dos transcripts em vez do audit log | $0 de economia e o item mais importante: sem ele nada acima é falsificável | **livre** (P) | 60–120k tokens / 1 sessão | — |
| 3 | Cura dos **2 sítios «INERT»** (`PLAN-178:402-403`, `eval-baseline-n20.js:3,284,547`) | fecha a maior discrepância entre doutrina escrita e substrato medido | **canônico** (carona em cerimônia que já toque os arquivos) | 5–10k tokens | OQ-11 já decidida |
| 4 | **Migrar os 5 pins VETO** `claude-fable-5` → `claude-fable-5-1` | fecha o cache read de $1,00/MTok no `code-reviewer`, o único no rail nativo | **camada T Owner-signed** | 80–150k tokens / 1–2 sessões | ADR-149 rota (a)/(b) + amendment |
| 5 | **Matrizar o job `validate`** em 3 jobs | wall-clock do Validate: baseline 22m22s → bound ~13 min, a medir (AC-6) | livre (workflow) | 80–150k tokens / 1–2 sessões | confirmar ausência de estado partilhado |
| 6 | **Checagem de dependência sequencial no Step 0** | evita a classe de −70 % (Kim et al.) | **precisa ADR + debate L3+** (muda o Spawn Protocol) | 60–100k tokens / 1 sessão | — |
| 7 | **Teto de effort documentado** no skill `effort` + a regra "escala por incerteza de especificação" | evita `max` por reflexo; 01 §4.2 | livre (doc) | 15–30k tokens | — |
| 8 | **Sondas do substrato**: `TeammateIdle`/`TaskCompleted`, `PreModelSwitch`/`PostModelSwitch`, re-probe de hooks 31→33, `--probe-installed` do substrate-watch, `CLAUDE_CODE_PROJECT_DIR_NAME` | fecha a cegueira de 18 de 33 hook events e o tamper de tier | livre (sondas) → **ADR** se algum for religado | 60–120k tokens / 1–2 sessões | — |
| 9 | **Matrizar Smoke Install** por step | wall-clock do Smoke: baseline 87m50s → bound ~35–40 min, a medir (AC-6) | livre (workflow) | 150–300k tokens / 2–3 sessões | item 5 primeiro, como prova do padrão |
| 10 | **Citar MAST, 2310.01798 e 2502.00271** no `PROTOCOL.md` (fundamento de V0–V3, do "nunca auto-aprovar" e da razão de existir do V3) | rastreabilidade da doutrina | canônico (`PROTOCOL.md`) | 20–40k tokens | — |
| 11 | **Rail dual-track em paralelo** (patch ∥ materiais) | latência de uma rodada por cerimônia | livre (runbook) | trivial | — |
| 12 | Lacunas da API no adapter opcional: refusal fallback, cache 1h TTL, `thinking.display:"updates"`, effort por mensagem | resiliência e observabilidade de night-run | livre (adapter) | 100–200k tokens / 1–2 sessões | só sob `CEO_LIVE_CLAUDE=1` |

Já entregue e fora da lista: o land de `wave-fable51` (`ab56e76`, F3) — o item de maior retorno
isolado do estudo, **−$4.664/mês** ao tirar o assento de `claude-fable-5` (05 §P2-1).

---

## 8. Riscos e o que NÃO fazer

- **Agent Teams fica fora.** O mecanismo existe (`TeammateIdle`/`TaskCompleted` são hooks reais), mas a feature ainda recebia fixes de comportamento básico em 2.1.251, e 2.1.247 removeu o controle de modelo do teammate — que agora herda o líder, reintroduzindo a armadilha do fato 9. A doc oficial ainda registra ~7× mais tokens em plan mode (05 §3.1).
- **Não paralelizar o V-block do LAND.** Ganho de dezenas de segundos contra reabrir a corrida na cadeia HMAC viva e re-certificar um `trap/restore` endurecido por 5+ rodadas de rail (04 §(a)).
- **Não confiar em `used_pct` do sidecar** como prova de exaustão — mediu 35 % no instante de uma recusa `session limit` (`CLAUDE.md` §5). O A/B do §6.3 usa minutos úteis por janela, não percentual.
- **Não confiar em `totalTokens` do Workflow como custo** — é soma de picos de contexto, erra por 2 ordens de grandeza (05 §P1-2).
- **Verificação não é `grep`.** Uma rota apontando para fonte errada-mas-existente manteve 10 testes verdes (`CLAUDE.md` §5). Qualquer censo de `model:` nos `agent()` tem de ser provado no campo `model` da **resposta servida**, não na presença do literal.
- **Não decompor pacotes por reflexo.** A oportunidade 5 do §5 e o achado 1 do §3.3 apontam em direções opostas quando a tarefa é sequencial: decompor uma tarefa com dependência sequencial é exatamente o caso de −70 %.
- **Advisor tool nunca satisfaz VETO.** Adotá-lo para triagem barata (item 12) não muda a hierarquia de evidência; ele fica estritamente abaixo do pair-rail.
- **`fable-5-1` não é `fable-5`.** O multiplicador de cache read 0,025× vale só para o 5.1. Escrever o id errado num pin custa 4× (05 §P2-1).

---

## 9. Divergências entre relatórios e como foram resolvidas

| # | divergência | resolução | regra usada |
|---|---|---|---|
| 1 | **Assento Fable (05, cenário iv) vs assento Opus (posição prévia do CEO, cenário iii)** | Não resolver por argumento: o A/B de 7 dias do §6.3 decide, com critério de morte pré-registrado | Onde as duas moedas discordam e uma delas não tem número oficial, mede-se — média entre posições não é evidência |
| 2 | **`opts.model` do Workflow: INERTE (PLAN-134 W0a, PLAN-178 AC-3, `eval-baseline-n20.js`) vs HONRADO (03 §3, ADR-144 emenda, F1)** | HONRADO. A claim antiga está envelhecida em 2 sítios, nomeados no item 3 do §7 | Medição comportamental recente (probe `wf_9ddadaab-12f` + os spawns desta sessão) vence doutrina escrita |
| 3 | **Pin de arquétipo não governa modelo (05 §P1-1) vs o pin do `code-reviewer` vale (F2)** | Ambos verdadeiros, em rails distintos: o rail mitigado despacha como `general-purpose` e ignora o pin; o `code-reviewer` é o único no rail nativo, onde o pin se aplica | Afirmação sobre mecanismo vale no escopo do mecanismo; ler o ADR que define o rail (ADR-082:93-94, 131-132) antes de generalizar |
| 4 | **Decompor pacotes grandes (04 §(d)) vs decompor tarefa sequencial custa −70 % (01 §1.3)** | Decompor só quando as sub-tarefas são logicamente independentes; a checagem de dependência sequencial (item 6 do §7) é a pré-condição do item 5 do §5 | Uma otimização de escalonamento não pode preceder o teste de aplicabilidade que a literatura já quantificou |
| 5 | **V2 como único portão de verdade (`PROTOCOL.md`) vs verificador único poda caminhos corretos (01 §2.3)** | A doutrina está certa e a mitigação já existe: o V3 é o caminho de recuperação. Falta escrever a razão (item 10 do §7) | Quando a literatura descreve um risco que o desenho já mitiga, o débito é de documentação, não de arquitetura |
| 6 | **Effort como dial de custo (05 §1.5: só 7,9 % da fatura) vs effort como dial de qualidade não-monotônico (01 §4.2)** | Convergem: effort é decisão de qualidade, e a variável de escala é incerteza de especificação (§6.1) | Dois relatórios que descartam a mesma justificativa (custo) apontam para o mesmo critério substituto |
| 7 | **Advisor rejeitado (`HONEST-LIMITATIONS.md:112`) vs nomeado como alavanca (`SOTA-GAP-MAP.md:70,92`)** | Ambos corretos em escopos diferentes: proibido como VETO, legítimo como triagem barata abaixo do rail | A proibição vale sobre a função reivindicada, não sobre a ferramenta |
| 8 | **`substrate-watch` diz `current` (03 §1) vs 60 versões de drift** | `current` é verdade sobre o ledger, não sobre o binário instalado — instrumento verde com pergunta envelhecida | Um instrumento só responde a pergunta que ele de fato faz; `--probe-installed` é a pergunta certa |

---

## 10. Fontes

**Relatórios sintetizados (todos de 2026-09-02):**
`docs/research/s339-orchestrator-study/01-academia.md` ·
`02-claude-api.md` · `03-claude-code-substrate.md` ·
`04-parallelism.md` · `05-finops-routing.md`

**Verificado nesta síntese:** `.claude/agents/code-reviewer.md:6` (`model: claude-fable-5`,
`veto_floor: true`) e `.claude/adr/ADR-082-l7c-mitigation-default-on.md:93-94,131-132,147-148`
(o `code-reviewer` é o único arquétipo no rail nativo; `general-purpose` herda o modelo do CEO).

**Academia (01):** arXiv [2503.13657](https://arxiv.org/abs/2503.13657) (MAST) ·
[2512.08296](https://arxiv.org/abs/2512.08296) (Kim et al.) ·
[2310.01798](https://arxiv.org/abs/2310.01798) ·
[2502.00271](https://arxiv.org/abs/2502.00271) ·
[2305.05176](https://arxiv.org/abs/2305.05176) (FrugalGPT) ·
[2406.18665](https://arxiv.org/abs/2406.18665) (RouteLLM) ·
[2407.21787](https://arxiv.org/abs/2407.21787) ·
[2604.10739](https://arxiv.org/html/2604.10739v1) · [2505.20522](https://arxiv.org/abs/2505.20522) ·
[2410.21819](https://arxiv.org/abs/2410.21819) · [2604.23178](https://arxiv.org/pdf/2604.23178) ·
[2605.06350](https://arxiv.org/pdf/2605.06350) · [2608.25992](https://arxiv.org/abs/2608.25992) ·
[2506.13752](https://arxiv.org/abs/2506.13752) **[NÃO VERIFICADA** quanto à aplicabilidade via API
Anthropic**]** · [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) (Anthropic, jun/2025)

**Substrato (03):** `CHANGELOG.md` do `anthropics/claude-code` (2 fetches, janelas 2.1.220–2.1.231 e
2.1.232–2.1.258) · `https://code.claude.com/docs/en/hooks` (33 hook events) ·
`https://code.claude.com/docs/en/changelog` · `Skill(workflow-authoring)` ·
ADR-144 (emenda S328, probe `wf_9ddadaab-12f`) · `.claude/scripts/substrate-watch.json` ·
data de introdução de Agent Teams em ~2.1.32 **[NÃO VERIFICADA** — agregadores de terceiros**]**

**Quota e preço (05), acessadas em 2026-09-02:** `code.claude.com/docs/en/costs` ·
`support.claude.com/en/articles/15424964` (teto de 50 % semanal para Fable) ·
`support.claude.com/en/articles/11049741` (janela de 5 h) ·
`support.claude.com/en/articles/9797557` · `support.claude.com/en/articles/14552983` ·
`platform.claude.com/docs/en/api/rate-limits` · `support.claude.com/en/articles/11145838`.
Preço do Sonnet 5 a **$2/$10**: verificado na tabela «Current Models» da skill oficial `claude-api`
do Claude Code 2.1.258 (cache 2026-06-24) e na página de pricing lida na S338 —
`cost-table.yaml` ainda diz $3/$15; o pack `sonnet5-pricing-fu` (`e47bf5d`) está pendente de aplicação.

**Paralelismo (04):** `gh run view 33582381725` (Smoke Install, SHA `f0e98de3`, 87m50s) ·
`gh run view 33627209709` (Validate, SHA `ab56e76`, ~23m27s) · `.github/workflows/{smoke-install,validate}.yml` ·
os dois `OWNER-S338-*-LAND.sh` · `journal.jsonl` e `agent-*.{meta.json,jsonl}` de `wf_e3144372-b04`
(timeline por `mtime`, **não** por timestamp de evento) · `.claude/plans/PLAN-172-honest-speed-e0b-e5-e6.md`
