# Lane 03 — Auditoria do coletor de tokens (`ceo-cost-transcripts.py`)

**Data:** 2026-09-17 (v2, após REJECT do revisor cruzado com 6 pontos — todos incorporados) · **Sessão:** S354 · **Autor:** CEO (Fable 5.1) · **Status:** concluída — coletor APTO
**Substrato:** Claude Code CLI 2.1.274, macOS; coletor em `.claude/scripts/ceo-cost-transcripts.py` no
HEAD `efe4c609`; transcripts em `~/.claude/projects/<slug>/`.
**Janelas (ABSOLUTAS, reproduzíveis):** comparação `2026-09-03T00:00:00Z → 2026-09-17T12:00:00Z`
(limite superior NO PASSADO — ver §3 sobre corpus estável); cruzamento com o `/stats`
`2026-07-28T00:00:00Z → 2026-09-15T23:59:59Z` (o intervalo que o cache local do `/stats` declara).
**Instrumento:** `tools/audit_collector.py` (stdlib, Python ≥ 3.9) — re-derivação INDEPENDENTE: não
importa o coletor, varre TODOS os `.jsonl`, aceita vários diretórios de projeto, calcula três variantes
de dedup, usa tabela de preços própria, classifica escritas grandes, mede prefixo inicial e pico de
contexto por subagente, e reproduz a regra do `/stats` (`--raw-by-location --stats-cache`). Onde espelha
uma escolha do coletor (aceitação de registro, normalização da escrita de cache, máximo por campo,
sufixo de modelo), o docstring nomeia a regra — uma divergência é atribuível a UMA regra.

---

## 1. Perguntas que a auditoria responde

1. **Cobertura** — há transcripts com `message.usage` que os dois padrões do coletor não veem?
2. **Dedup** — a regra «máximo por campo entre linhas com o mesmo `message.id`» é correta?
3. **Preços** — o USD sai da tabela do repo + multiplicadores DOCUMENTADOS, sem constante inventada?
4. **`/stats`** — o que o cache local do `/stats` conta, e como se relaciona com o coletor?
5. **Escritas grandes** — quanto do custo é escrita de cache acima do limiar, e de que tipo?
6. **Composição** — há dupla contagem entre diretórios (arquivo, slug antigo, clones)?
7. **Unidades** — o «tokens» que o runner de Workflow reporta é consumo acumulado?

## 2. Achados

### A. Cobertura — sem furo
4.605 `.jsonl` sob o projeto: 98 casam `<session>.jsonl` (assento), 1.638 casam
`*/subagents/**/agent-*.jsonl` (subagentes, inclusive `subagents/workflows/<wf>/…`), 2.869 ficam FORA dos
padrões (`subagents/journal.jsonl`, `audit-log.jsonl` do estado do framework, fixtures dentro de clones de
cerimônia). **Nenhum arquivo fora dos padrões carrega registro `assistant` com `usage` na janela.**
Sidechain no topo: 0. Sem `timestamp`: 0. Sem `message.id`: 0. Registros com `usage` sem
`input_tokens` nem `output_tokens` (que o coletor descarta): 0.

### B. Dedup — o máximo por campo é o correto
| medida (janela estável) | valor |
|---|---|
| chaves únicas (`message.id`) | 64.445 |
| chaves com mais de uma linha | 39.6 mil |
| chaves cujas linhas trazem `usage` DIFERENTE | 6.573 (16,6 % das duplicadas) |
| output total, «primeira linha vence» | 11,13 mi |
| output total, «última linha» = «máximo por campo» | 18,95 mi |
| input, cache read, cache write nas três variantes | idênticos |

«Primeiro vence» subcontaria o output em **41 %**; a regra do coletor (máximo por campo, com metadados
da linha de maior output) reproduz o valor terminal. Só `output_tokens` varia entre linhas do mesmo
`message.id`.

### C. Preços e igualdade — demonstradas em corpus estável, tabela completa, todos os campos
Comparação por modelo em **turnos, input, output, cache read, escrita 5 min, escrita 1 h e USD**
(delta absoluto e relativo, sem arredondar), com a tabela do auditor cobrindo os 8 modelos presentes
(inclusive `claude-sonnet-4-6`; só `<synthetic>` fica sem preço, com 0 tokens):

| modelo | Δ turnos | Δ input | Δ output | Δ cache read | Δ w5m | Δ w1h | Δ USD |
|---|---|---|---|---|---|---|---|
| todos os 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0,0000 (0,00000 %) |

Total da janela estável: 64.445 turnos, US$ 12.546,77 pelos dois instrumentos. Multiplicadores usados
pelo auditor (independentes do coletor): leitura 0,10 × input; **`claude-fable-5-1` 0,025 × input =
US$ 0,25/MTok**, valor que a referência oficial da API lista para o modelo (a leitura barata chegou com o
5.1; Fable 5 lê a 0,10); escrita 5 min 1,25 ×; escrita 1 h 2,0 ×. **Consequência para a lane de
roteamento (hipótese a testar, dólar API — não quota):** a leitura de cache do Fable 5.1 custa METADE da
do Opus 5 (0,25 vs 0,50); escrita e output custam o dobro; para o perfil medido dos subagentes (75 %
leitura, 23 % escrita, 2 % output), Fable 5.1 sairia ≈ 12 % mais barato mantidos os volumes.

### D. `/stats` — regra exata, reproduzida dentro do auditor
`audit_collector.py --project-dir ~/.claude/projects/*/ --raw-by-location --stats-cache ~/.claude/stats-cache.json`
sobre os 3.156 diretórios, janela do cache:

| modelo | `/stats` cache read | topo / stats | (topo + `subagents/agent-*` 1.º nível) / stats | tudo (dedup NÃO) / stats | output (topo + 1.º nível) / stats |
|---|---|---|---|---|---|
| claude-fable-5 | 17,81 bi | 0,963 | **1,000** | 1,705 | **1,000** |
| claude-fable-5-1 | 10,81 bi | 0,947 | **1,000** | 1,644 | **1,000** |
| claude-opus-5 | 24,80 bi | 0,382 | **1,000** | 4,526 | **1,000** |
| claude-sonnet-5 | 0,49 bi | 0,004 | **1,000** | 1,507 | **1,000** |
| opus 4.8 · haiku 4.5 · sonnet 4.6 | — | — | **1,000** | — | **1,000** |

**Regra:** `modelUsage` do `/stats` = soma SEM dedup dos `<session>.jsonl` mais os
`<session>/subagents/agent-*.jsonl` de PRIMEIRO nível; **exclui os agentes da Workflow tool**
(`subagents/workflows/<wf>/…`). São dois vieses em sentidos opostos — duplicação das linhas de streaming
(o topo bruto é 2,06× o topo deduplicado nesta máquina) e omissão dos agentes de Workflow — logo o
`/stats` **não é piso nem teto garantido**: sobre ou subconta conforme o perfil. NESTA máquina e NESTA
janela (28/07 → 15/09) o líquido foi subcontagem: `/stats` 56,80 bi contra **88,31 bi deduplicados**
(assento 18,21 + subagentes 70,11 = 79 %); Opus 5 = 62,8 bi = 71 % dos tokens reais (44,8 % no `/stats`).
Custo API-equivalente da máquina na mesma janela, pela tabela do repo: ≈ US$ 76 mil em 50 dias. Estes
números NÃO substituem os 57,5 bi da ordem de trabalho (outro intervalo, até 16/09): a comparação vale
só janela contra janela.

### E. Escritas grandes — 17,4 % do custo, decompostas
Turno com escrita de cache > 100k tokens (um sufixo incremental mede 5–10k). O limiar é heurística; o
que o torna interpretável é a classificação pelo turno vizinho: **inicial** (1.º registro do transcript),
**reescrita** (cache read caiu abaixo de 20 % do turno anterior: prefixo perdido — expiração OU
invalidação) e **crescimento** (cache read continuou: conteúdo NOVO volumoso, p.ex. saída grande de
ferramenta). Janela estável, este repo:

| papel | tipo | turnos | tokens escritos | custo API-eq | % do custo dos 14 d |
|---|---|---|---|---|---|
| subagentes (TTL 5 min, Opus 5) | reescrita | 442 | 155,2 mi | ≈ US$ 970 | 7,7 % |
| subagentes | crescimento | 322 | 85,8 mi | ≈ US$ 536 | 4,3 % |
| subagentes | inicial | 58 | 8,9 mi | ≈ US$ 55 | 0,4 % |
| assento (TTL 1 h, Fable 5.1) | reescrita | 32 | 16,6 mi | ≈ US$ 332 | 2,6 % |
| assento | crescimento | 24 | 12,1 mi | ≈ US$ 242 | 1,9 % |
| assento | inicial | 18 | 2,2 mi | ≈ US$ 45 | 0,4 % |
| **total** | | **896** | **280,8 mi** | **≈ US$ 2.180** | **17,4 %** |

**Expectativa corrigida para `subagentPromptCacheTtl` 5 min → 1 h (subagentes, Opus 5, 14 d):** toda
escrita passa de 1,25 × para 2,0 × o preço-base (+US$ 3,75/M). Escritas que continuam existindo
(incrementais 142,5 mi + crescimento 85,8 mi + iniciais 8,9 mi = 237,1 mi) custam **+≈ US$ 889**. As
reescritas (155,2 mi): se TODAS forem expiração, deixam de ser escritas (−US$ 970) e viram leituras
(+US$ 78) — saldo do cenário **≈ −US$ 3, isto é, zero**; se forem invalidação, continuam escritas ao
preço novo (+US$ 582) — saldo **+≈ US$ 1.471**. Conclusão: **o TTL de 1 h não economiza neste perfil em
nenhum cenário; só encarece.** A alavanca é a CAUSA das reescritas e do crescimento (o que invalida o
prefixo; saídas de ferramenta volumosas), não o TTL. O item 3 do plano (README §3) passa a testar causas.

### F. Composição — sem dupla contagem
Dos 3.156 diretórios em `~/.claude/projects/`, 17 têm turnos na janela; 5 são projetos reais, o resto
sondas de teste. Os diretórios do slug antigo e do arquivo pré-W1 deste framework têm 0 turnos na janela
e 0 subagentes; os ~3.000 diretórios de experimentos de benchmark não têm transcripts.

### G. Unidades — o «tokens» do runner não é consumo
Por subagente deste repo (janela estável): **prefixo inicial** (1.º turno: input + cache) n=909,
p50 = **92k**, p90 = 156k, máx 162k; **pico de contexto** (maior turno) n=754, p50 = **196k**, p90 = 435k,
máx 931k; soma dos picos = 178,9 mi contra **15,68 bi de cache read acumulado — razão 88×**. O total que
o runner de Workflow reporta por run (centenas de milhares) é da ordem da SOMA DOS PICOS dos agentes que
executaram, como o S339 já apontara — não do consumo acumulado. Estimativas por hora feitas nessa unidade
não convertem em consumo sem o coletor. Uma sonda isolada tampouco define o prefixo de «qualquer agente»:
a distribuição acima é a medida; ela muda com o `CLAUDE.md`, a skill inline e o spec de cada consumidor
(no repo consumidor do incidente, mesma janela do incidente: p50 = 154k, p90 = 166k — README M12).

### H. `<synthetic>`
364 turnos com modelo `<synthetic>` e 0 tokens — mensagens sintéticas do harness; US$ 0 sem preço
inventado. Correto.

## 3. Divergências, limites e o que mudou da v1 para a v2
- **Corpus instável explicava a divergência da v1.** A sessão em curso ESCREVE no próprio transcript
  entre a rodada do coletor e a do auditor; com `--until` no futuro, o auditor via turnos que o coletor
  não vira (+1, depois +14 turnos de `claude-fable-5-1`). Com `--until 2026-09-17T12:00:00Z` (antes das
  rodadas) os oito modelos batem em zero em todos os campos. Regra: comparação só com limite superior no
  passado.
- **v1 não comparava `input_tokens`** e arredondava o USD a 2 casas — corrigido (§C).
- **v1 previa «≈ 0» para TTL 1 h sob invalidação** — errado: sob invalidação o custo SOBE 60 % nas
  escritas; e escrita evitada vira leitura paga. Corrigido (§E).
- **v1 chamava toda escrita > 100k de «reescrita do prefixo inteiro»** — agora é «escrita acima do
  limiar», com a decomposição inicial / reescrita / crescimento (§E).
- **v1 chamava o `/stats` de «piso»** — são dois vieses opostos; «piso» só vale para esta máquina e esta
  janela, e a reprodução da regra agora vive no auditor (§D).
- **Limites que ficam:** a classificação por vizinho não separa expiração de invalidação dentro de
  «reescrita»; quota não é medida aqui (fonte nativa: `rate_limits.{five_hour,seven_day}` da statusline,
  já lida por `statusline-ceo.py`); a regra do `/stats` foi verificada em UMA máquina (razão 1,000 nos 7
  modelos) — repetir em outra antes de generalizar.

## 4. Veredito
O coletor `ceo-cost-transcripts.py` é **APTO** como instrumento do estudo: cobertura completa, dedup
correto, preços reproduzíveis a partir de fontes documentadas, igualdade exata em corpus estável. O
`/stats` não serve para totais nem para mix quando há Workflow; toda claim de volume deste estudo cita o
coletor, com janela absoluta.

## 5. Reprodução
```
# coletor, janela absoluta com limite superior no PASSADO, JSON
python3 .claude/scripts/ceo-cost-transcripts.py --since-at 2026-09-03T00:00:00Z \
  --until 2026-09-17T12:00:00Z --json > /tmp/collector.json

# auditoria independente + comparação por modelo (todos os campos)
python3 docs/research/s354-token-consumption-study/tools/audit_collector.py \
  --project-dir ~/.claude/projects/<slug> --since-at 2026-09-03T00:00:00Z \
  --until 2026-09-17T12:00:00Z --compare /tmp/collector.json

# regra do /stats, máquina inteira, janela declarada pelo cache
python3 docs/research/s354-token-consumption-study/tools/audit_collector.py \
  --project-dir ~/.claude/projects/*/ --since-at 2026-07-28T00:00:00Z \
  --until 2026-09-15T23:59:59Z --raw-by-location --stats-cache ~/.claude/stats-cache.json
```
