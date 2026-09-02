# PLAN-186 W0 — instrumento de custo por transcripts (S339)

> **Task:** construir `ceo-cost-transcripts.py`, um instrumento que mede
> gasto real lendo `message.usage` dos transcripts nativos do harness
> (`~/.claude/projects/<slug>/*.jsonl` + `.../<session>/subagents/**/
> agent-*.jsonl`), porque `ceo-cost.py` e `budget-summary.py` reportam
> `$0.00`/30d — o audit log HMAC não carrega tokens (P0-1 do relatório
> `docs/research/s339-orchestrator-study/05-finops-routing.md`).
> **Status:** entregue. Entrega inicial: AC-1 (delta ≤ 2 % vs
> $11.137,97) **não batia** (−5,60 %) com uma causa isolada e
> quantificada (§4). **Follow-up (cross-model review, mesma sessão):**
> um P1 real no `dedup()` do próprio instrumento foi confirmado no
> corpus vivo e corrigido — **AC-1 agora bate: −1,22 %** (`--since 30d`)
> e **−0,23 %** (janela idêntica à do relatório). Ver §2-3 para o
> achado/correção e §4 para o residual que sobra depois dela.

## 1. Entregáveis

| arquivo | papel |
|---|---|
| `.claude/scripts/ceo-cost-transcripts.py` | CLI, stdlib-only, Python ≥ 3.9 |
| `.claude/scripts/tests/test_ceo_cost_transcripts.py` | 23 testes pytest, `TestEnvContext`-isolados |
| `.claude/plans/PLAN-186/w0/instrument-S339.md` | este relatório |

## 2. P1 do cross-model review (Codex, V2) — CONFIRMADO e CORRIGIDO

**Claim revisada:** `dedup()` era first-write-wins; para mensagens cujo
`usage` é PROGRESSIVO sob o mesmo `message.id` (snapshot interino de
`output_tokens` cresce a cada linha de bloco de conteúdo até um valor
final), o snapshot completo era descartado e o custo — sobretudo de
subagentes — ficava subestimado.

### 2.1 Verificação no corpus vivo (só leitura)

| tree | grupos `message.id` com >1 linha | grupos com `usage` divergente | direção |
|---|---:|---:|---|
| assento (top-level, 65 arquivos) | 14.893 únicos | **0** | — |
| subagente (679 arquivos) | 16.070 grupos multi-linha (21.414 únicos) | **14.054 (65,6 %)** | `output_tokens` cresce em ordem de arquivo em **100 %** dos casos divergentes (0 contraexemplos); `input_tokens` constante em 100 % dos grupos; campos de cache divergem em só 4/16.070; `model` diverge em 3/21.414 (harness resolvendo o modelo do 1º chunk streaming, negligenciável) |

Claim **verdadeira e maior do que a descrição inicial** (65,6 % dos
grupos multi-linha de subagente afetados, não um caso pontual).
Exemplo real do corpus (`agent-ab2-gate-canonical-writer-...jsonl`,
`msg_011CePuerk1T4vtgMJdoeksH`): `output_tokens` passa de `1` para
`389` ao longo das linhas do mesmo `message.id`, `input_tokens` e
`cache_creation_input_tokens` idênticos nas duas.

### 2.2 Correção

`dedup()` deixou de ser first-write-wins e passou a agrupar por chave e
tomar o **máximo por campo** (`input_tokens`, `output_tokens`,
`cache_read_tokens`, `cache_write_5m`, `cache_write_1h`) entre todas as
linhas de um grupo — exato para o padrão dominante de crescimento
monotônico, e seguro para o resíduo de 4 grupos onde outro campo também
varia (um máximo por campo nunca fica ABAIXO de qualquer snapshot
observado, o defeito que ele substitui). Metadado (`model`, `effort`,
`session_id`, `role`) vem da linha com maior `output_tokens` (snapshot
terminal); o timestamp do registro combinado é o MENOR do grupo (início
do turno — mesmo valor que um dedup ingênuo já reportava para `--by
day`).

### 2.3 Teste novo (controle positivo)

`ProgressiveUsageDedupTests` (3 casos) — fixture com 3 linhas do mesmo
`message.id` (`output_tokens` 4 → 92 → 182, `input_tokens`/cache
constantes, o formato exato citado na revisão): confirma que o registro
combinado usa `output_tokens=182` (nunca `4`), calcula o custo exato
esperado usando esse valor terminal, e mostra por comparação direta que
o custo antigo (first-write-wins) subestimaria. Mais um teste cobrindo
mistura de grupo progressivo + registro singular no mesmo lote.

### 2.4 Verificação mecânica pós-correção

```
python3 -m py_compile .claude/scripts/ceo-cost-transcripts.py         # OK
python3 -m pytest .claude/scripts/tests/test_ceo_cost_transcripts.py -q
  23 passed in 0.35s
python3 .claude/scripts/check-test-env-hygiene.py
  OK: test-env hygiene clean (337 flagged files, all allowlisted)
python3 -m pytest --collect-only -q .claude/scripts/tests/test_ceo_cost_transcripts.py
  23 tests collected in 0.20s
```

## 3. Resultado pós-correção — AC-1 agora bate

| medição | total 30 d | delta vs $11.137,97 |
|---|---:|---:|
| **antes da correção** (`--since 30d`) | $10.514,21 | −5,60 % |
| **depois da correção** (`--since 30d`, agora) | **$11.001,49** | **−1,22 %** ✅ ≤ 2 % |
| depois da correção, janela fixa idêntica à do relatório (`2026-08-03T00:00Z` → agora) | **$11.164,04** | **−0,23 %** ✅ |

A correção sozinha explicou a maior parte do gap original: subagente
subiu de $2.987,60 para **$3.469,01** (+16,1 %; `output_tokens` de
subagente foi de ~2,67 M para ~19,19 M tokens — a subestimativa era
grande, não cosmética) e assento subiu de $7.526,61 para **$7.532,69**
(mudança pequena — confirma que o defeito era quase todo em subagente,
onde 65,6 % dos grupos multi-linha existem, contra 0 % no assento).

### 3.1 Por modelo (30 d, `--since 30d`, pós-correção)

| modelo | turnos | USD |
|---|---:|---:|
| `claude-fable-5` | 10.580 | $6.259,60 |
| `claude-opus-5` | 19.630 | $4.271,73 |
| `claude-fable-5-1` | 582 | $304,52 |
| `claude-opus-4-8` | 169 | $104,86 |
| `claude-sonnet-5` | 830 | $53,38 |
| `claude-sonnet-4-6` | 129 | $7,33 |
| `claude-haiku-4-5-20251001` | 2 | $0,07 |
| `<synthetic>` (não resolvido, sempre 0 token) | 149 | $0,00 |

## 4. Residual que sobra (não é a mesma causa, ainda presente, não corrigível no código)

A causa isolada na entrega inicial — a chave de dedup do relatório 05
(`requestId, apiBlockIndex, message.id`) falhar especificamente nos
poucos arquivos mais novos que carregam `apiBlockIndex` — **continua
verdadeira e é independente do P1 desta seção**: este instrumento nunca
usou `apiBlockIndex` na própria chave (só `message.id`, com fallback
`requestId+uuid`), então a correção do §2 não muda esse comportamento.
Medido de novo, janela fixa (`2026-08-03T00:00Z`), assento:

| modelo | turnos (relatório → aqui) | USD (relatório → aqui) |
|---|---|---|
| `claude-fable-5` | 8.248 → **8.248** | $5.562,24 → **$5.562,24** (idêntico) |
| `claude-opus-5` | 4.968 → **4.968** | $1.685,08 → **$1.684,96** |
| `claude-opus-4-8` | 169 → **169** | $104,88 → **$104,86** |
| `claude-fable-5-1` | 660 → **295** | $562,60 → **$231,93** |

`claude-fable-5-1` no assento segue abaixo do relatório (mecanismo:
100 % do uso desse modelo em arquivos de assento mora nos 2 arquivos
mais novos do corpus, os únicos com `apiBlockIndex` — ver a análise
completa, com a reconstrução que valida a 0,41 % do valor publicado, no
histórico deste arquivo antes desta revisão / disponível via `git log
-p` quando commitado). Esse resíduo de assento (~$330 abaixo) é
compensado no total pelo subagente agora capturando ~$360 A MAIS do que
o relatório original (a correção do §2 recupera tokens de output que
NEM o relatório 05 nem a entrega inicial deste instrumento contavam) —
é essa combinação, não um match exato componente a componente, que
produz o −0,23 % da linha 3 da tabela em §3. Registrado com honestidade:
o total bate; a composição por modelo não bate em todos os componentes,
e os dois resíduos têm sinais opostos por coincidência de magnitude,
não porque se cancelam por construção.

**Implicação para o relatório 05 (fora do escopo desta W0):** a tabela
§2.1 do relatório ("Papéis e consumo por agente" do night-run S338)
deriva de transcripts que têm AMBOS os defeitos agora identificados
(chave com `apiBlockIndex` E dedup first-write-wins sobre `usage`
progressivo) — os números absolutos ali (ex. "$223,50 de subagentes")
não devem ser citados sem re-derivação. Fica registrado para quem
revisitar PLAN-183/roteamento de custo.

## 5. Contrato de preço (documentado, nunca inventado em silêncio)

Padrão: tabela EMBUTIDA (`_EMBEDDED_PRICING`, relatório 05 §1.4) com uma
correção ratificada sobreposta quando `--pricing` usa o caminho padrão
(`cost-table.yaml`, que ainda tem Sonnet 5 a $3/$15 pré-intro — commit
`e47bf5d`): `claude-sonnet-5` reprecificado para $2/$10 (ratificado
2026-09-01). Um `--pricing` explícito é respeitado como está, sem
correção. Multiplicadores de cache (0,10× leitura padrão / 0,025× Fable
5.1 / 1,25× escrita 5m / 2,00× escrita 1h) são constantes estruturais
de `docs/provider-pricing.md`, nunca derivadas do YAML (que não tem
colunas de cache). Um modelo não resolvido na tabela ativa nunca é
descartado nem custa $0 por omissão silenciosa — é isolado em
`unresolved_models` com seus totais de token, reportado tanto no modo
humano quanto no `--json`. Único caso observado no corpus vivo:
`<synthetic>` (placeholders de erro de API — rate limit/auth — sempre
0 tokens, então $0 é o valor correto, não um chute).

## 6. Desempenho

Corpus vivo real: **640 MB / 738 arquivos `.jsonl`** (não os `~9 MB` do
briefing original, que descrevia o audit log — um corpus diferente).
`--since 30d` completo: 409k linhas lidas, 78,9k candidatas (pré-filtro
por substring bytes evita `json.loads` nas ~330k linhas de
tool-result/user), **~3,0-3,4 s**. O agrupamento para dedup por máximo
(§2.2) não mudou a ordem de grandeza do tempo de execução.

## 7. Limitações declaradas

1. `--by role` não é "papel" no sentido builder/refutador/design do
   relatório §2.1 (heurística de texto de prompt, fora de escopo
   mecânico) — é a separação estrutural assento/subagente.
2. Preço é lista de API, não fatura de assinatura — mede magnitude
   relativa entre modelos, não o valor cobrado (mesma ressalva do
   relatório 05, Limite #2).
3. Este instrumento é read-only e não foi integrado a `ceo-cost.py`
   nem a `budget-summary.py` (fora do FILE ASSIGNMENT desta W0) — o
   item 3 da sequência recomendada no relatório 05 §5.3 ("trocar
   `ceo-cost.py` para derivar de `message.usage`") permanece aberto.
4. O residual do §4 (`claude-fable-5-1` no assento) não é um bug deste
   instrumento — é uma característica do relatório de referência que
   este instrumento não reproduz de propósito.

## 8. Comando de referência

```
python3 .claude/scripts/ceo-cost-transcripts.py --since 30d --by role
python3 .claude/scripts/ceo-cost-transcripts.py --since 30d --by model --json
```
