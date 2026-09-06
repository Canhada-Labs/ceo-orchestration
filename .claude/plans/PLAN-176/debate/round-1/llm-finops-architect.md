---
round: 1
archetype: LLM FinOps Architect
skill: llm-routing-and-finops
agent_persona: LLM FinOps Architect (Principal, advisory — NO VETO)
generated_at: 2026-09-06T04:10:00Z
---

## Verdict

ADJUST — 7 blocking items.

## Summary (≤ 3 bullets)

- O **split T/P é sólido e verificável por construção**: rodei o oráculo e ele
  concorda com o desenho (`.claude/governance/*.json` = canônico `1`,
  `.claude/data/*.json` = livre `0`). Essa é a melhor decisão do plano e eu não
  a mexeria. Mas o plano **não tem AC para a W0** — a wave que é dependência
  dura de todas as outras não tem definição de "pronto".
- O **envelope de custo é ficção**: `budget_tokens: 300-550k` para 4-5 sessões
  = 110k/sessão, contra **1,49 × 10⁷ tokens faturáveis (ex-cache-read) por
  sessão** medidos agora — erro de **136×** (5.611× em tokens brutos). Não há
  `budget_usd_estimate` num plano que custará ~$1.700-2.100 API-equivalente, e
  a própria linha 10 se contradiz na aritmética (150+100+100 = **350**k, não
  300k).
- Três colisões mecânicas fecham waves inteiras: **"Amendment 2" já existe**
  em ADR-149:209; a W1 quer automatizar um instrumento cujo código declara
  "**Owner-run by design — the nightly agent stays no-network**"; e o AC da W2
  nomeia o instrumento errado como controle positivo.

## Risks

### R-FIN1 — P1 — o `budget_tokens` está 136× abaixo do medido e a linha se contradiz

`PLAN-176-model-currency-refresh.md:10-11` declara `budget_tokens: 300-550k`
com `budget_sessions: 4-5`. Duas falhas independentes:

**(a) Aritmética interna.** A mesma linha 10 detalha `W0 150-250k; W1 100-150k;
W2-W3 100-150k`. Soma: **350-550k**. O piso declarado (300k) não é derivável do
próprio detalhamento.

**(b) Unidade e ordem de grandeza.** Medido agora, janela 7 d, instrumento do
repo (`<ROOT>/.claude/scripts/ceo-cost-transcripts.py --since 7d --by session`,
87 arquivos de assento + 1.373 de subagente, 52.940 registros após dedup):

| grandeza (7 d) | valor | por sessão (n=25) |
|---|---:|---:|
| tokens brutos | 15.430.818.278 | 6,17 × 10⁸ |
| tokens ex-cache-read | 373.514.521 | 1,49 × 10⁷ |
| USD API-equivalente | $10.745,27 | mediana $161,55 / média $429,81 / p90 $1.490,48 |

Teto do plano por sessão = 550k/5 = **110k**. Contra a classe faturável o erro é
de **136×**; contra tokens brutos, **5.611×**. Controle independente com a
constante do próprio repo: o piso de re-pagamento de gate-boot é **F ≈ 97.292
tokens** numa fronteira de compactação (`CLAUDE.md` §5). Ou seja, **o teto
inteiro de uma sessão do plano paga UM gate-boot e sobram ~13k para todo o
trabalho** — um plano L3 com debate, cerimônia de ADR e egress não cabe nisso.

Não há `budget_usd_estimate` nem `tier_mix_estimate` no frontmatter (linhas
1-15). Pela minha AC-1 de skill isso é BLOCKED por si só: é um número sem
unidade, sem fonte e sem spread — e o spread medido é grande (mediana $161 →
p90 $1.490, **9,2×**), então reportar um intervalo único engana.

**Mitigação:** declarar `budget_tokens_raw` e `budget_tokens_billable`
separadamente, derivados do instrumento e não de memória;
`budget_usd_estimate: 1700-2100`; `tier_mix_estimate` em **dois blocos**
(assento e subagente — na medição de 7 d o subagente é **$8.541,03 de
$10.745,27 = 79,5 %**, então um mix só de assento descreve 20 % da conta).

### R-FIN2 — P1 — "Amendment 2" já está tomado: ADR-149:209 landou com esse número

`.claude/plans/PLAN-176/adr-149-amendment2-draft.md:1` intitula-se
"ADR-149 — Amendment 2 (DRAFT): Trust vs Preference", e o runbook
(`PLAN-176-...:128`) manda "cerimônia do ADR-149-A2" **antes** da W0. Mas no
HEAD: `.claude/adr/ADR-149-model-id-allowlist.md:209` já é
`## Amendment 2 (S338 — Fable 5.1 joins the working set...)`, e
`ADR-149:92` referencia "ADR-149 Amendment 2, S338 2026-09-01" de dentro do
bloco `AVAILABLE_MODELS_WORKING_SET`. O draft do PLAN-176 é de 2026-08-11 e
envelheceu: a cerimônia como escrita produziria **duas Amendment 2**.

**Mitigação:** renumerar o draft para **Amendment 3** e re-verificar suas
premissas contra o HEAD (o draft cita `_VALID_MODELS` como bug vivo — ele não
existe mais em `.claude/hooks/_lib/adapters/`; único hit é
`.claude/plans/PLAN-142/staging/codex_cli_shape.py:92`, um arquivo de staging).

### R-FIN3 — P1 — a W1 automatiza um instrumento que o código declara Owner-run e no-network

`PLAN-176-...:63-70` diz que a W1 "APENAS estende `check-substrate-watch.py`
com o probe upstream faltante" e a roda como rotina cloud semanal
(`:106-108`, RemoteTrigger). O instrumento no HEAD declara o oposto, duas
vezes: `.claude/scripts/check-substrate-watch.py:10-11` — "no-network under
ADR-136-AMEND-1; the doc fetch costs no model tokens but is the one network
action, so it is **Owner-run by design**"; e `:284` — "This is **Owner-run by
design** — the nightly agent stays no-network".

O plano **não nomeia ADR-136-AMEND-1 em lugar nenhum** (grep no arquivo: zero
hits). A W1 não é uma extensão: é a revogação de uma invariante de confinamento
existente, feita por edição de um arquivo que — verificado com o oráculo —
**não é canônico**:

```
$ python3 .claude/hooks/check_canonical_edit.py --is-canonical .claude/scripts/check-substrate-watch.py
.claude/scripts/check-substrate-watch.py    0
```

**Mitigação:** a mudança de postura no-network → network é uma decisão de ADR
própria (emenda a ADR-136-AMEND-1), não um efeito colateral de wave. Ou a W1
usa um fetcher NOVO em path canônico e deixa o substrate-watch intacto.

### R-FIN4 — P1 — a W0, dependência dura de tudo, não tem AC

`:104-115` (§3b "Pronto-para-execução") define ACs para W1, W2 e W3. **W0 não
aparece.** E `:117-120` diz "W1-W3 só abrem com o W0 DESTE plano landado". A
condição de abertura de três waves é um estado sem critério de aceite: qualquer
coisa que exista em disco satisfaz "landado".

Pior: a propriedade central do plano — "a cerimônia não é contornada porque a
superfície cerimonial é outra" (`:80-82`) — é exatamente o que um AC de W0
deveria provar com **controle positivo e negativo**, e não existe.

**Mitigação:** AC-W0 com as duas pernas, executáveis:
(i) NEGATIVO — um patch que toca só `.claude/data/models-preference.json` landa
sem sentinel (oráculo devolve `0`); (ii) POSITIVO — um patch que toca
`.claude/governance/models-registry.json` é BLOQUEADO pelo `check_canonical_edit`
(oráculo devolve `1`). Verifiquei que a topologia sustenta os dois:

```
.claude/governance/models-registry.json    1
.claude/data/models-preference.json        0
.claude/hooks/_lib/model_registry.py       1
.claude/hooks/check-model-literals.py      1
```

### R-FIN5 — P1 — o AC da W2 nomeia o instrumento errado; o Check não pode ficar vermelho

`:110-113`: "AC: o lint `check-model-literals` fica VERMELHO se o PR tocar campo
T — positive control do próprio guard-rail". Mas `check-model-literals` é
definido em `:46-48` como lint de **literais de modelo no código**, com
grandfather-ledger e ratchet. Um PR que edita um campo dentro do JSON da camada
T **não introduz literal novo em código** — o lint fica verde por construção.

O guard que o plano de fato descreve para esse caso é outro: `:93` "PR tocando o
arquivo T/schema ⇒ vermelho fail-closed no CI". Duas seções nomeiam instrumentos
diferentes para o mesmo controle positivo, e o AC — que é o que a cerimônia
verifica — nomeia o que não pode disparar.

**Mitigação:** o AC-W2 nomeia o path-guard do CI (e o oráculo
`--is-canonical` como segunda perna), não o lint de literais.

### R-FIN6 — P1 — o AC da W1 pode passar com a novidade da W1 inteiramente ausente

`:106-109`: "AC: relatório lista os 3 CLIs com {instalado, pin, upstream}". Mas
o escopo declarado da W1 (`:63-65`) é "feeds de **MODELOS** dos vendors
(Anthropic/OpenAI/xAI/Google) — o que o substrate-watch NÃO faz". O AC mede
apenas os 3 CLIs, que é justamente a parte que o substrate-watch **já faz**.
Um relatório de CLIs produzido pelo instrumento existente satisfaz o AC com
zero linhas de feed de modelo. É um AC que não pode ficar vermelho pela razão
de existir da wave.

Colateral: 4 vendors no escopo × 3 CLIs no AC. **Google não tem CLI neste repo,
não é membro de `AVAILABLE_MODELS_WORKING_SET` (ADR-149:82-98) e não tem linha
em `.claude/scripts/cost-table.yaml`** (grep `gemini|google`: zero hits). Uma
lane que ingere um id sem preço é pior que inútil: o instrumento de custo
**reporta $0 e avisa**, mas o número entra nos relatórios — a saída de hoje já
carrega `AVISO: 1 modelo(s) nao resolvido(s) na tabela de precos, 297 turnos,
custo reportado como $0`.

**Mitigação:** AC-W1 exige ≥1 lançamento de MODELO detectado por vendor ativo,
e a lista de vendors ativos = interseção {tem membro em ADR-149} ∩ {tem linha em
`cost-table.yaml`}. Google entra só com as duas.

### R-FIN7 — P1 — a W0 excede o teto do modelo de operação v2 (≤ 8 paths)

Paths mínimos da W0, derivados de `:56-62`: (1) `models-registry.json`,
(2) `models-preference.json`, (3) `_lib/model_registry.py`,
(4) `check-model-literals.py`, (5) ledger de grandfather, (6) o oráculo
`replacements ⊆ valid_override_ids`, (7) wire no `.github/workflows/validate.yml`
(canônico: oráculo `1`), (8) teste do resolver, (9) teste do lint, (10) teste
do schema, (11) a emenda de ADR-149 (canônico: `1`). **≥ 10 paths, ≥ 5 deles
canônicos** — acima do teto de 8 do modelo v2, e o "teste-mestre" de `:49-50`
(injetar `claude-opus-6` fake) adiciona fixture.

**Mitigação:** W0a = schema T + registry + resolver + testes (canônico, 1
assinatura); W0b = camada P + lint + ratchet + wire de CI. O split também
produz o controle positivo do R-FIN4 de graça: W0b é o land livre que prova que
P não pede cerimônia.

### R-FIN8 — P2 — a rotina semanal tem custo recorrente que nenhum orçamento cobre

`budget_sessions: 4-5` (`:11`) orça a CONSTRUÇÃO. A W1 entrega uma rotina cloud
**semanal permanente** (`:106`) que consome quota da mesma conta — e o repo já
mediu que quota, não dólar, é a moeda que vincula. Não há linha de custo
recorrente (tokens/semana da rotina, nem runner-minutos), nem critério de
revisão desse custo. Um plano de FinOps que entrega um consumidor perpétuo sem
orçá-lo herda o defeito que veio curar.

Além disso `:106-107` cita a rotina irmã como "substrate-watch trig_014Y…" —
**id truncado**, não resolvível a partir do texto do plano.

**Mitigação:** declarar `recurring_budget_tokens_per_week` medido em 1 run
manual (a W1 já exige um run verde — meça nele), e o id completo do trigger.

### R-FIN9 — P2 — os kill criteria não têm denominador nem latência aceitável

`:90-102`. "> 2 falsos-positivos/mês" (`:90-91`) numa rotina **semanal** com 4
lanes: o denominador é ~4 execuções/mês, então o gatilho dispara acima de ~50 %
de FP — um limiar frouxo por acidente de cadência, não por escolha. "3 falhas
consecutivas de um vendor" (`:100`) = **3 semanas** de cegueira antes do
alerta. E "feed stale (mais velho que 30d)" (`:95`) é mais largo que o período
de amostragem, então um feed pode estar 4 ciclos parado e ainda contar como
fresco.

O que está CERTO e eu não mexeria: os limiares estão **pré-registrados antes do
primeiro número**, e existe controle de falso-NEGATIVO mensal com fixture
(`:97-99`). Isso é raro e é a parte forte da §3.

**Mitigação:** re-expressar cada limiar em unidades de **ciclos da rotina**, não
de calendário (ex.: "> 2 FP em 8 ciclos"; "stale = 2 ciclos sem atualização"),
para que a régua não dependa da cadência escolhida depois.

### R-FIN10 — P2 — ADR-114 não cobre a superfície de egress da W1

`:77-78` oferece "Revisão ADR-114 no debate de abertura" como garantia de
egress. ADR-114 (`.claude/adr/ADR-114-...:33-56`) decide `redact_outgoing()`
cabeado "at ALL Codex / external-LLM egress callsites", com teste AST de
cobertura por callsite. É um mecanismo sobre **prompts enviados a LLMs
externos**. A W1 declara GET-only, sem body, sem query, sem headers (`:73-77`)
— ou seja, o redator de ADR-114 **não tem nada para redigir** e a cobertura é
vacuosa: citar ADR-114 aqui dá conforto sem mecanismo.

E a afirmação "NADA do repo (nem números de versão locais) sai em requisição
alguma" (`:75-76`) é verdadeira para a W1 e **falsa para o par W1+W2**: a W2
abre um PR "carregando o relatório+digests como evidência" (`:83-84`) — conteúdo
derivado do repo indo para o GitHub. As duas frases não se contradizem só
porque estão em waves diferentes; um leitor futuro lê "nada sai" como
propriedade do plano.

**Mitigação:** escopar a frase ("nada do repo sai **para os hosts de vendor**")
e nomear o mecanismo real de egress da W1 — allowlist de host+path compilada,
`Host` fixo, sem redirect, digest sha256 gravado — que o plano já descreve em
`:71-74` e que é o controle certo. ADR-114 sai da lista de garantias.

### R-FIN11 — P2 — os aliases da camada P não existem em nenhuma autoridade viva

`:41-43` fundamenta a camada P em aliases `claude-frontier` e `codex-latest`.
Grep em `.claude/hooks`, `.claude/scripts` e `.claude/adr` (py/json/yaml): **zero
hits para ambos**. ADR-149 §A1.2 (`:130-146`) estabelece que os arrays de
`.claude/settings.json` são **espelhos GERADOS** de dois blocos do ADR e que
`generate-available-models.py --check` fica vermelho em drift. Introduzir um
alias resolvível pela camada P sem ele ser membro do working-set cria uma
segunda autoridade de identidade de modelo — exatamente a classe "duas tabelas
role→model paralelas ... unificação sem dono" que o próprio plano lista como rot
em `:155-156`.

**Mitigação:** o AC do teste-mestre (`:49-50`) passa a exigir que a injeção do
id fake mantenha `generate-available-models.py --check` **verde**, provando que
o registry é derivado de ADR-149 e não concorrente dele.

### R-FIN12 — P3 — o resolver é canônico, então "trocar preferência" custa mais do que o plano sugere

O oráculo devolve `1` para `.claude/hooks/_lib/model_registry.py`. Toda correção
de bug no resolver é cerimônia assinada. O plano vende a camada P como "troca
barata e auditada" (`:139-143`) sem registrar que o **leitor** dessa camada é
caro de mudar. Não é um defeito de desenho — é um custo não declarado que muda
a estimativa de manutenção.

## Must-fix (blocking) — 7

1. **Reescrever o envelope de custo** (R-FIN1): corrigir a aritmética 350-550k,
   declarar unidade (bruto × faturável) derivada do instrumento, adicionar
   `budget_usd_estimate` e `tier_mix_estimate` em dois blocos (assento 20,5 % /
   subagente 79,5 % medidos).
2. **Renumerar o draft para Amendment 3** (R-FIN2) e re-verificar suas premissas
   contra o HEAD antes da cerimônia.
3. **Decidir a postura de rede por ADR** (R-FIN3): a W1 revoga uma invariante
   declarada no código (`Owner-run by design`, `no-network`, ADR-136-AMEND-1) que
   o plano não cita.
4. **Criar ACs para a W0** (R-FIN4) com controle positivo (T bloqueado) e
   negativo (P livre) rodados pelo oráculo `--is-canonical`.
5. **Corrigir o AC da W2** (R-FIN5): nomear o path-guard do CI, não o lint de
   literais.
6. **Corrigir o AC da W1** (R-FIN6): exigir detecção de lançamento de MODELO por
   vendor ativo; definir "vendor ativo" como ADR-149 ∩ `cost-table.yaml`.
7. **Dividir a W0 em W0a/W0b** (R-FIN7): ≥10 paths excede o teto de 8 do modelo
   de operação v2.

## Nice-to-have (advisory)

1. Orçar o custo recorrente da rotina semanal no run manual que a W1 já exige, e
   escrever o id completo do trigger (R-FIN8).
2. Re-expressar os kill criteria em ciclos da rotina, não em calendário (R-FIN9).
3. Trocar ADR-114 pela allowlist compilada como garantia nomeada de egress, e
   escopar a frase "nada do repo sai" (R-FIN10).
4. Exigir `generate-available-models.py --check` verde no teste-mestre (R-FIN11).
5. Registrar que o resolver é canônico (R-FIN12).

## Unseen by the original plan

1. **O split protege o DADO e deixa o ESCRITOR livre.** `models-preference.json`
   é não-canônico por desenho (correto), mas o programa que decide o que vai
   dentro dele — o fetcher, o gerador de PR — mora em `.claude/scripts/`, que o
   oráculo devolve `0`. A fronteira de confiança está no arquivo, não no
   produtor. Quem pode landar um patch livre de script muda o que a camada P
   serve a todo roteamento não-VETO. O plano chama isso de "PR auditado" — que é
   revisão humana, não mecanismo. O controle que fecharia isso já existe no repo
   e não é citado: o **digest sha256 de proveniência** (`:73-74`) poderia ser
   verificado por um gate canônico que recusa qualquer preference-value sem
   proveniência conferida.
2. **Vendor sem linha de preço vira $0 silencioso.** A saída medida hoje já traz
   `AVISO: 1 modelo(s) nao resolvido(s) ... custo reportado como $0`. Uma rotina
   que ingere ids de 4 vendors direto num registry, com `cost-table.yaml` sem
   Google e sem xAI, transforma cada id novo em zero contábil. A entrada no
   registry deveria ser **fail-closed sem linha de preço**.
3. **A conta é 79,5 % subagente.** Medido: assento $2.204,24, subagente
   $8.541,03 (7 d). Toda a doutrina do plano é sobre identidade de modelo; nada
   sobre por onde os $8.541 realmente passam. Um `tier_mix_estimate` só faz
   sentido se enxergar essa perna.
4. **`cache_w5m` do subagente é 310,2 M contra 0 de `cache_w1h`.** O assento usa
   as duas janelas (6,9 M / 41,8 M); o subagente escreve **só** cache de 5 min.
   Se a rotina da W1 e o fan-out do plano forem despachados como subagentes, cada
   spawn re-paga escrita de cache que expira antes do próximo. Isso não é um risco
   do desenho de identidade de modelo — é a variável de custo dominante que o
   plano não modela e que decide se automatizar a rotina economiza ou gasta.

## What I would NOT change

1. **O split T/P.** Verificado pelo oráculo, não por leitura: governance = `1`,
   data = `0`. A cerimônia é preservada por construção, e a fundamentação externa
   do §3c (`:135-143`) é honesta ao marcar-se como advisory.
2. **Fase 2 (auto-merge) fora, gated em ADR** (`:84`, `:102`). É a recusa certa.
3. **O controle de falso-NEGATIVO mensal com fixture** (`:97-99`) — a rotina tem
   de detectar um lançamento conhecido injetado. É a diferença entre um detector
   e um instrumento verde cuja pergunta envelheceu, que é a classe dominante
   deste repo.
4. **GET-only, sem body, sem query, sem headers** (`:75-77`). É a postura de
   egress mais restritiva possível para o objetivo, e a comparação local↔upstream
   em disco é o desenho certo.
5. **Fail-closed em feed malformado/ambíguo e em drift de parser** (`:72`, `:96`)
   — input-parse falha fecha, coerente com a doutrina da casa.
6. **W0 antes de W1** (`:127-129`). Instrumento antes de rede, e a dependência
   dura declarada em `:117-120`. A ordem está certa; falta só o AC que diz quando
   a W0 acabou.
