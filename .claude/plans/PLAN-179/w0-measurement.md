# PLAN-179 W0 — Relatório de medição (`F`, `T`, censo)

> **Status:** W0 parcial. Secções A, C, D e E têm valor MEDIDO. Secção B
> permanece DEGRADADA por decisão explícita (emenda 8.6). A sonda de canal
> (W0-1, `probe_postcompact_channel.py`) **não** faz parte deste relatório e
> continua aberta.
>
> **Data da medição:** 2026-08-18. **Escopo:** read-only. Nenhuma chamada de
> API paga foi feita; nenhum hook vivo foi executado contra o audit log real.
>
> **Regra desta página:** toda medida imprime o comando que a produziu
> ([[feedback-measurement-must-list-its-inputs]]). Onde não há fonte, a AC
> degrada por escrito — nunca por omissão.

---

## Sumário executivo (o que mudou de premissa)

Três números do plano estavam errados. A **direcção** das três conclusões de
§2.1 sobrevive; os **valores absolutos** não.

| Quantidade | Plano §2.1 (estimado) | Medido (W0) | Razão |
|---|---:|---:|---|
| `F` (piso re-pago) | 45.000–55.000 | **97.097 / 98.636** | ≈ 2,0× |
| `F + S` (piso pós-compactação) | ~60.000 | **112.638** | ≈ 1,9× |
| `T` (limiar de auto-compact) | 150k (default suposto da API) | **998.043** | ≈ 6,7× |
| Piso de thrashing (`T ≈ F+S`) | ~60.000 | **≈ 112.638** | ≈ 1,9× |
| η no ponto de operação real | não calculado | **88,7 %** | — |

A causa da divergência de `T` é única e simples: a tabela η de §2.1 foi
construída para uma janela de **200k**. A sessão medida corre em **1M**
(`model_id=claude-opus-5[1m]`). Consequências em §E.

---

## Secção A — metade DISCO de `F` (medida)

### Comando

```
python3 .claude/scripts/context-budget.py --json
```

Executado de `/Users/joaocanhada/canhada-labs/ceo-orchestration`, exit `0`.

### Saída bruta

A saída completa tem **3.976 linhas / 129.614 bytes**; o bloco `top_candidates`
(um objecto por skill, 165 entradas) está **ELIDIDO** aqui por volume. O que
está colado abaixo é literal e não editado. Integridade da saída completa:

```
sha256(saída completa) = 066a0a4e78bc3a4a4898db321e2e2f1cdd70336c0d6c37b2ca8e8af7e4216590
```

```json
{
  "schema": "context-budget.v1",
  "repo_root": "/Users/joaocanhada/canhada-labs/ceo-orchestration",
  "heuristic": "1 token ~= 4 chars (ESTIMATE, not the Anthropic tokenizer)",
  "grand_total_est_tokens": 834547,
  "categories": [
    {
      "category": "claude_md",
      "file_count": 1,
      "total_lines": 107,
      "est_tokens": 3478
    },
    {
      "category": "protocol",
      "file_count": 1,
      "total_lines": 597,
      "est_tokens": 6703
    },
    {
      "category": "team",
      "file_count": 2,
      "total_lines": 1034,
      "est_tokens": 14698
    },
    {
      "category": "core_skill",
      "file_count": 1,
      "total_lines": 735,
      "est_tokens": 15768
    },
    {
      "category": "agents",
      "file_count": 13,
      "total_lines": 1972,
      "est_tokens": 23131
    },
    {
      "category": "skills",
      "file_count": 165,
      "total_lines": 62977,
      "est_tokens": 735769
    },
    {
      "category": "commands",
      "file_count": 27,
      "total_lines": 3365,
      "est_tokens": 35000
    },
    {
      "category": "mcp",
      "file_count": 0,
      "server_count": 0,
      "servers": [],
      "sources": [],
      "over_subscribed": false,
      "threshold_servers": 5
    }
  ],
  "top_candidates": [ /* 165 entradas — ELIDIDO, ver sha256 acima */ ]
}
```

### Leitura

Superfície Gate 1+2 em disco = `claude_md` + `protocol` + `team` +
`core_skill` = **40.647** tokens estimados. Confere com o valor de
`research-S309.md §3` citado em §2.1 do plano (40.116) a menos de 1,5 % — a
diferença é drift de conteúdo entre S309 e hoje, não erro de método.

**Limite declarado do instrumento (do próprio JSON, campo `heuristic`):**
`1 token ~= 4 chars (ESTIMATE, not the Anthropic tokenizer)`. Este número é
uma estimativa de caracteres, não uma contagem de tokens. É por isso que a
Secção C não o usa como `F`.

---

## Secção B — metade NÃO-DISCO de `F` (system prompt + definições de ferramenta)

### Veredito: **AC DEGRADADA** — `estimativa declarada, fonte ausente`

A emenda **8.6** exige que a metade de `F` que `context-budget.py` não mede
tenha **fonte NOMEADA** (usage de uma chamada de API real) e, sem ela, que a
AC degrade explicitamente para **`estimativa declarada, fonte ausente`**. É o
que se regista aqui, com uma precisão que a emenda não podia antecipar:

- **O TOTAL de `F` deixou de ser estimativa.** A Secção C mede-o com o
  tokenizer da própria Anthropic, a partir dos blocos `usage` que o harness já
  grava em disco no transcript da sessão. Não houve chamada paga: a chamada já
  tinha sido feita e paga em 2026-08-14/2026-08-16, e o que se lê é o registo
  dela. Esta é uma **fonte nomeada**, e para o agregado a AC **não** degrada.
- **A DECOMPOSIÇÃO continua sem fonte.** O bloco `usage` devolve um único
  inteiro para todo o prompt. Ele não separa *system prompt* de *definições de
  ferramenta* de *CLAUDE.md* de *índice de memória*. Para essa separação —
  que é o que a AC pede à letra — a medição é **`estimativa declarada, fonte
  ausente`**.

### A estimativa declarada (e o que ela vale)

Por diferença entre o `F` medido (§C) e a metade-disco medida (§A):

```
F_boot medido            ≈ 97.097 (2026-08-14) / 98.636 (2026-08-18)
Gate 1+2 em disco (est.) =  40.647
resto                    ≈ 56.450 – 57.989
```

Esse "resto" — system prompt + definições de ferramenta + índice de memória +
listagem de skills + primeira mensagem do utilizador — é **maior que a metade
que sabemos medir**. O plano assumia o contrário (`F` total 45–55k implicava
um resto de 5–15k). **Advertência forte:** o número acima é uma subtracção
entre uma contagem real e uma estimativa chars/4 de um conjunto de ficheiros
que, no primeiro turno, o modelo pode ainda nem ter lido (Gate 1+2 acontece
DEPOIS do primeiro turno). Serve para dizer *"o resto é grande"*; não serve
para orçamentar nenhuma das suas parcelas.

### O que fecharia a AC

Por ordem de custo:

1. **`/context`** (comando nativo do harness), se expuser a decomposição por
   categoria — custo zero, fonte nomeada, fecha a AC inteira. **Não verificado
   neste relatório.** É o primeiro passo a tentar.
2. **`POST /v1/messages/count_tokens`** com o mesmo `system` + `tools` e uma
   mensagem vazia: devolve exactamente a soma system+tools. É barato mas é uma
   chamada de API — fora do mandato read-only desta wave.
3. Diferença controlada entre dois `usage` de primeiro turno com e sem
   `--setting-sources ""` — isola a contribuição do framework sem isolar
   system vs tools. Meia-medida; só se (1) e (2) falharem.

---

## Secção C — `T` (limiar de auto-compact) e `F` real

### Veredito: **MEDIDO**, por duas séries independentes que concordam

A evidência **sobreviveu**. Não foi preciso degradar esta AC.

### C.1 — Sidecar de statusline (a série de percentagem)

O campo existe: `context_pct_bps` (`statusline_sidecar_write`, SPEC v2.44 —
*"context-window used %, integer basis-points 0..10000"*, produtor
`.claude/scripts/statusline-ceo.py`).

```
python3 - <<'PY'
import json
for line in open('/Users/joaocanhada/.claude/projects/ceo-orchestration/audit-log-2026-08-8.jsonl',
                 encoding='utf-8', errors='replace'):
    if 'context_pct_bps' not in line: continue
    ev = json.loads(line)
    ts = str(ev.get('ts',''))
    if ts.startswith('2026-08-16T09:') or ts.startswith('2026-08-16T08:5'):
        print(ts, ev.get('action'), ev.get('context_pct_bps'), ev.get('session_id','')[:8])
PY
```

Saída (8 linhas na janela):

```
2026-08-16T08:50:55Z statusline_sidecar_write  9300 1916b9c8
2026-08-16T08:55:55Z statusline_sidecar_write  9400 1916b9c8
2026-08-16T09:24:11Z statusline_sidecar_write  9500 1916b9c8
2026-08-16T09:29:19Z statusline_sidecar_write  9800 1916b9c8
2026-08-16T09:34:25Z statusline_sidecar_write 10000 1916b9c8   <- compactação
2026-08-16T09:39:32Z statusline_sidecar_write  1300 1916b9c8   <- piso
2026-08-16T09:44:41Z statusline_sidecar_write  1400 1916b9c8
2026-08-16T09:49:55Z statusline_sidecar_write  1500 1916b9c8
```

O auto-compact disparou a **100,00 %** da janela e o contexto caiu para
**13 %**. Sozinha, esta série dá a FORMA mas não o DENOMINADOR: o sidecar não
grava o tamanho da janela (`statusline-snapshot.json` tem `context_pct` e
`exceeds_200k_tokens`, nunca `context_window_size`).

### C.2 — `usage` do transcript (a série absoluta, tokenizer da Anthropic)

```
python3 - <<'PY'
import json, os
P = os.path.expanduser('~/.claude/projects/'
    '-Users-joaocanhada-canhada-labs-ceo-orchestration/'
    '1916b9c8-0ae5-43db-b462-179c4c6cfd18.jsonl')
rows = []
for line in open(P, encoding='utf-8', errors='replace'):
    if '"usage"' not in line: continue
    ev = json.loads(line); m = ev.get('message')
    if isinstance(m, dict) and isinstance(m.get('usage'), dict):
        u = m['usage']
        tot = (int(u.get('input_tokens') or 0)
               + int(u.get('cache_read_input_tokens') or 0)
               + int(u.get('cache_creation_input_tokens') or 0))
        rows.append((str(ev.get('timestamp','')), tot))
rows.sort()
print('primeiro turno :', rows[0])
print('ultimo pre-boundary :', [r for r in rows if r[0] < '2026-08-16T09:36:29'][-1])
print('primeiro pos-boundary:', [r for r in rows if r[0] > '2026-08-16T09:36:29'][0])
PY
```

Saída:

```
primeiro turno        : ('2026-08-14T17:18:24.034Z',  97097)
ultimo pre-boundary   : ('2026-08-16T09:34:05.847Z', 998043)
primeiro pos-boundary : ('2026-08-16T09:36:46.798Z', 112638)
```

Marcador de fronteira lido do mesmo transcript:
`('2026-08-16T09:36:29.454Z', 'system', 'compact_boundary')`.

### C.3 — As duas séries fecham uma na outra

| Instante | sidecar (bps → %) | transcript (`TOTAL_IN`) | `TOTAL_IN` / 1.000.000 |
|---|---:|---:|---:|
| 09:24:11 | 9500 → 95,0 % | 951.815 | 95,2 % |
| 09:29:19 | 9800 → 98,0 % | 980.237 | **98,0 %** |
| 09:34:25 | 10000 → 100,0 % | 998.043 (09:34:05) | 99,8 % |
| 09:39:32 | 1300 → 13,0 % | 112.638 (09:36:46) | 11,3 % |

O denominador é **1.000.000**, confirmado por concordância exacta em
09:29:19 (98,0 % vs 98,0 %). O modelo da sessão é `claude-opus-5[1m]`
(`statusline-snapshot.json`, campo `model_display: "Opus 5 (1M context)"`).

### C.4 — Valores fixados

| Símbolo | Valor medido | Fonte | n |
|---|---:|---|---:|
| `T` (limiar auto-compact) | **998.043** (≈ 99,8 % de 1M) | `usage`, último turno pré-fronteira | 1 |
| `F` (piso a frio, sessão nova) | **97.097** / **98.636** | `usage`, primeiro turno de 2 sessões (2026-08-14, 2026-08-18) | 2 |
| `F + S` (piso pós-compactação) | **112.638** | `usage`, primeiro turno pós-fronteira | 1 |
| `S` (sumário), por diferença | **≈ 14.600** | `112.638 − 98.000` | — |

Decomposição de cache no primeiro turno pós-compactação:
`cache_read=68.980` + `cache_creation=43.656` + `input=2`. O prefixo que
sobreviveu à fronteira sem reescrita são 68.980 tokens; 43.656 são material
novo (o sumário e o que mudou de posição). **Isto é uma inferência sobre
contabilidade de cache, não uma medição de "system prompt + tool defs"** — e
é exactamente por isso que a Secção B fica degradada.

### C.5 — Fronteiras honestas desta secção

- **`T` tem n = 1.** Um único auto-compact observado. Que ele ocorra a 99,8 %
  é consistente com "o harness compacta ao tecto", mas um segundo evento pode
  revelar histerese. **Não há limiar configurado** em
  `.claude/settings.json` nem em `~/.claude/settings.json` (grep por
  `compact`/`trigger`: só os comentários dos hooks `PreCompact`/`PostCompact`),
  logo o valor observado é o default do harness, não uma escolha deste repo.
- **`F` foi medido em 1M.** Numa janela de 200k o sumário `S` seria mais
  pequeno; `F` (system prompt + tools + CLAUDE.md + memória) não tem razão
  para mudar, mas isso é raciocínio, não medida.
- **`statusline-snapshot.json` é partilhado entre projectos** — observado a
  ser reescrito com `project_dir` de outros repositórios durante esta sessão.
  As medições de C.1 vêm de eventos de audit **com `session_id`**, que são
  imunes a essa partilha; o ficheiro de snapshot em si não é fonte fiável
  para nenhuma medição retrospectiva. Registado como achado lateral.

---

## Secção D — censo read-only do par ADR-153

### Comando

```
python3 <scratchpad>/census_w0.py
```

(varre `~/.claude/projects/ceo-orchestration/audit-log*.jsonl` — activo **e**
todos os arquivos rodados; o log activo rodou em 2026-08-18T13:45Z, portanto
um varrimento de ficheiro único subconta. Script preservado em
`PLAN-179/w0/census_w0.py` quando esta wave landar.)

### Saída

```
files_scanned=15
  - audit-log-2026-07-5.jsonl      - audit-log-2026-08-6.jsonl
  - audit-log-2026-08-1.jsonl      - audit-log-2026-08-7.jsonl
  - audit-log-2026-08-10.jsonl     - audit-log-2026-08-8.jsonl
  - audit-log-2026-08-11.jsonl     - audit-log-2026-08-9.jsonl
  - audit-log-2026-08-12.jsonl     - audit-log-2026-08.jsonl
  - audit-log-2026-08-2.jsonl      - audit-log.jsonl
  - audit-log-2026-08-3.jsonl
  - audit-log-2026-08-4.jsonl
  - audit-log-2026-08-5.jsonl
lines_scanned=230634
total_matching_events=2

per ISO week:
  2026-W33  snapshot=1  reinjected=1

distributions:
  plan_id           {'unknown': 2}
  trigger           {'auto': 1}
  snapshot_outcome  {'scratchpad_unavailable': 1}
  snapshot_found    {'False': 1}
  pointer_count     {'1': 1}

raw matching events (verbatim, decision fields only):
  [audit-log-2026-08-8.jsonl] {"action": "compaction_continuity_snapshot", "chain_length": 11179,
      "plan_id": "unknown", "snapshot_outcome": "scratchpad_unavailable",
      "trigger": "auto", "ts": "2026-08-16T09:34:22Z"}
  [audit-log-2026-08-8.jsonl] {"action": "compaction_context_reinjected", "plan_id": "unknown",
      "pointer_count": 1, "snapshot_age_s": 0, "snapshot_found": false,
      "ts": "2026-08-16T09:36:29Z"}
```

### Leitura — **N = 1**

O par ADR-153 disparou **uma única vez** em toda a história retida do log
(230.634 linhas; primeiro evento retido `2026-07-11T00:44:16Z`, último
`2026-08-18T18:31:35Z`). Uma única semana ISO tem observações; todas as
outras têm zero.

> **Nota sobre os dois totais de linhas.** O censo principal conta 230.634
> linhas e o censo lateral de `plan_transition` conta 230.638. Não é
> inconsistência: o log é **vivo** e cresceu 4 linhas entre as duas
> execuções (esta própria sessão emite eventos). Qualquer re-execução
> devolverá um total ainda maior; o que tem de se manter estável são as
> **contagens de eventos**, não o denominador de linhas.

> **Uma TAXA não é mensurável a partir de uma única observação.** A AC de saída
> de W0 pede "N de compactações/semana" e a resposta honesta é: **N = 1, e não
> há taxa**. Não há denominador de semanas-de-exposição fiável (o hook está
> registado desde S242, mas os logs anteriores a 2026-07-11 foram rodados para
> fora da retenção), não há variância, e um intervalo de confiança sobre n = 1
> seria decoração. Qualquer dimensionamento de W1 C2 (TTL, teto do GC) que
> dependa de "N por semana" **está a dimensionar sobre uma amostra de um**.
> Registado como tal, não contornado.

O que a amostra de um **suporta** é a afirmação qualitativa, porque é
categórica e não estatística: nas 100 % das compactações observadas,
`plan_id` foi `unknown` e o snapshot não foi escrito. Isso basta para o
diagnóstico E1/E2; não basta para dimensionar um GC.

### Censo lateral — `plan_transition`

```
python3 - <<'PY'  # (no dir ~/.claude/projects/ceo-orchestration)
import glob, json, collections, os
tot = 0; lines = 0; per = collections.Counter()
for p in sorted(glob.glob('audit-log*.jsonl')):
    n = 0
    for line in open(p, encoding='utf-8', errors='replace'):
        lines += 1
        if 'plan_transition' in line:
            try: ev = json.loads(line)
            except Exception: continue
            if ev.get('action') == 'plan_transition': n += 1; tot += 1
    if n: per[os.path.basename(p)] = n
print('lines_scanned', lines); print('plan_transition_total', tot); print(dict(per))
PY
```

```
lines_scanned 230638
plan_transition_total 49
{'audit-log-2026-07-5.jsonl': 14, 'audit-log-2026-08-1.jsonl': 1,
 'audit-log-2026-08-10.jsonl': 3, 'audit-log-2026-08-2.jsonl': 1,
 'audit-log-2026-08-5.jsonl': 3, 'audit-log-2026-08-6.jsonl': 3,
 'audit-log-2026-08-7.jsonl': 2, 'audit-log-2026-08-8.jsonl': 2,
 'audit-log-2026-08-9.jsonl': 1, 'audit-log-2026-08.jsonl': 9,
 'audit-log.jsonl': 10}
```

**49 eventos em 230.638 linhas = 0,021 %.** O plano §1 E2 registou "2 em
12.515" — censo de ficheiro único, no momento S309, hoje irreprodutível
(esse log rodou). A **direcção** confirma-se com folga (o evento é
rariíssimo, e estava ausente da sessão que compactou, daí `plan_id=unknown`);
o **número** de E2 deve ser citado com o seu escopo, nunca como constante do
repo. Corrigido também no ADR-153 §AMEND-1.2.

---

## Secção E — a tabela η reescrita

A AC de saída de W0 pede que a tabela η de §2.1 seja "reescrita com os valores
medidos ou explicitamente confirmada". Ela é **reescrita**, e o resultado
inverte a urgência do problema sem inverter o diagnóstico.

`η = (T − F − S) / T`, com **`F + S = 112.638` medido** (§C.4).

| `T` (limiar) | η (medido) | η (§2.1, estimado) | Leitura |
|---|---:|---:|---|
| **998.043 — ponto de operação REAL** | **88,7 %** | (ausente da tabela) | **saudável** |
| 500.000 | 77,5 % | — | saudável |
| 200.000 | 43,7 % | ~67 % @184k | medíocre |
| 150.000 (default suposto da API) | 24,9 % | 60 % | mau |
| 120.000 (topo da faixa CWL) | 6,1 % | 42 % | **thrashing** |
| **112.638 — piso de thrashing** | **0 %** | (o plano punha-o em ~60k) | **loop: nunca progride** |
| 100.000 | < 0 | 40 % | **impossível** |
| 80.000 (piso da faixa CWL) | < 0 | 25 % | **impossível** |
| 50.000 (mínimo da API) | < 0 | < 0 | **impossível** |

### As três conclusões de §2.1, re-avaliadas

1. **"O piso de thrashing deste framework é `T ≈ 60k`"** →
   **número REFUTADO, conclusão REFORÇADA.** O piso medido é **112.638**, ≈1,9×
   o estimado. O mínimo permitido pela API (`trigger.value = 50000`) não está
   apenas abaixo dele — está a **menos de metade**. A afirmação "este repo
   estruturalmente não pode usar compactação agressiva" fica mais forte, não
   mais fraca.
2. **"A faixa 80k–120k rende aqui apenas η de 25–42 %"** →
   **REFUTADO por ser optimista demais.** Medido: 120k rende **6,1 %** e 80k é
   **impossível** (η negativo — a compactação não liberta espaço suficiente
   para caber o próprio piso). A faixa "óptima da literatura" não é medíocre
   neste repo; é **inutilizável**.
3. **"A alavanca é `F`, não `T`"** → **CONFIRMADO e reforçado.** `F` é o dobro
   do que se julgava, e a metade que não sabemos medir (§B) é a maior das
   duas. O ganho continua a depender do PLAN-175, como §5 do plano já
   declarava.

### A conclusão NOVA, que o plano não tinha

**Com a janela de 1M, o ponto de operação real tem η = 88,7 % e não há
problema de eficiência de ciclo.** A curva má de §2.1 é real, mas este repo
não está sobre ela — está no topo saudável dela. Duas consequências de
desenho:

- **Não baixar o limiar de compactação neste repo, em circunstância nenhuma.**
  Qualquer `trigger.value` configurável (máximo 50.000 … abaixo do piso de
  112.638) transforma um η de 88,7 % num loop que não progride. O
  **progress guard** de W0/US2b deixa de ser optimização e passa a ser
  proteção contra um footgun de configuração; e agora tem um piso honesto para
  citar: `F + S = 112.638`.
- **A urgência de `F` é condicional ao tamanho da janela.** Num modelo de
  200k-classe o mesmo framework opera a η ≈ 43,7 % e perto de thrashing. A
  poda do PLAN-175 é opcional em 1M e **crítica** em 200k. O plano tratava-a
  como incondicional; passa a ter um gatilho nomeado.

### O que continua estimado nesta tabela

- **`S ≈ 14.600` é uma diferença, não uma medição** (`F+S` medido menos `F`
  medido em sessão diferente). Um segundo auto-compact fixá-lo-ia.
- **Toda a linha de `T` abaixo de 998.043 é contrafactual.** Nenhuma foi
  observada; são a fórmula avaliada no `F+S` medido. A forma da curva é
  robusta (é aritmética); os pontos não são observações.
- **`T` tem n = 1** (§C.5).
- **A decomposição de `F`** permanece `estimativa declarada, fonte ausente`
  (§B).

---

## Estado das ACs de saída de W0

| AC de saída (§4 W0 do plano) | Estado |
|---|---|
| (a) veredito do canal escrito e falsificável | **ABERTO** — W0-1, sonda paga, fora deste relatório |
| (b) taxa de `plan_id=unknown` medida, não estimada | **MEDIDA mas VAZIA** — 2/2 eventos `unknown`; N = 1, sem taxa (§D) |
| (c) `F` e `T` com valores medidos e tabela η reescrita | **FEITO** (§C, §E), com a decomposição de `F` degradada (§B) |

---

## Anexo — reprodutibilidade

Todos os comandos desta página são read-only e não tocam `$HOME` de teste,
audit log vivo ou rede. Os dois scripts auxiliares (`census_w0.py`,
`usage_probe.py`) vivem no scratchpad da sessão de medição e devem ser
copiados para `PLAN-179/w0/` no land desta wave — um relatório cujo
instrumento desaparece não é reproduzível.
