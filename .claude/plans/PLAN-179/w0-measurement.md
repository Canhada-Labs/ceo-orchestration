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
- **Fechou-se UMA fronteira, não a decomposição pedida (§F.3).** A separação
  `cache_read` (68.980, prefixo que sobrevive) vs `cache_creation` (43.656)
  está MEDIDA e fecha ao token. Ela não separa *system prompt* de *tool
  defs*: os 68.980 permanecem um bloco opaco, e a AC desta secção continua
  `estimativa declarada, fonte ausente`.

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
| `S` (sumário) | **15.346** | `compactMetadata.postTokens` (§F.1) | 1 |

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

- **`S` já NÃO é uma diferença: é `15.346`, medido** por
  `compactMetadata.postTokens` (§F.1). O `≈ 14.600` desta tabela era uma
  subtracção entre sessões diferentes e errava por −746 (−4,9 %).
- **Toda a linha de `T` abaixo de 998.043 é contrafactual.** Nenhuma foi
  observada; são a fórmula avaliada no `F+S` medido. A forma da curva é
  robusta (é aritmética); os pontos não são observações.
- **`T` tem n = 1** (§C.5).
- **A decomposição de `F`** permanece `estimativa declarada, fonte ausente`
  (§B).

---

## Secção F — custo de gate-boot RE-PAGO por compactação (MEDIDO)

### Veredito: **MEDIDO** — e o número documentado no repo (`~44.786`) está REFUTADO nos DOIS sentidos

Este é o sub-item que faltava ao checkbox `[P2][US2]`. A fonte é NOVA e este
relatório não a havia aberto: o próprio harness grava um bloco
`compactMetadata` no transcript, na linha do marcador de fronteira.
Instrumento rastreado em `PLAN-179/w0/gateboot_repay.py` — read-only, sem
rede, nunca escreve na cadeia HMAC nem em qualquer log.

### F.1 — A fonte que faltava: `compactMetadata`

```
python3 .claude/plans/PLAN-179/w0/gateboot_repay.py
```

Bloco lido (transcript `1916b9c8-…`, **linha 8329**), verbatim:

```
subtype=compact_boundary  trigger=auto
  preTokens=999089  postTokens=15346
  cumulativeDroppedTokens=983743  durationMs=126877
```

Duas consequências para §C/§E:

- **`S` deixa de ser uma subtracção.** `postTokens = 15.346` é MEDIDO pelo
  harness. O `S ≈ 14.600` de §C.4 fica **superseded**; erro do método antigo:
  −746 (−4,9 %).
- **`T` ganha uma segunda leitura independente:** `preTokens = 999.089` contra
  os `998.043` do último `usage` pré-fronteira (§C.2). Delta **+1.046
  (0,10 %)** — é a diferença de contabilidade harness↔`usage`, e é a barra de
  erro honesta de qualquer identidade construída com as duas fontes.

### F.2 — O piso re-pago na fronteira: **97.292 tokens**

`floor = TOTAL_IN(1.º turno pós-fronteira) − postTokens = 112.638 − 15.346`
= **97.292**.

Controlo: o `F` medido a frio no primeiro turno **desta mesma sessão** é
**97.097** (§C.4). Duas rotas independentes para a mesma grandeza,
divergência **+195 tokens = 0,20 %**. É essa concordância que autoriza a
identidade de F.3 — não é raciocínio, é o resíduo medido.

### F.3 — A decomposição por CLASSE DE TARIFA (o que "re-pago" custa)

| Parcela | Tokens | Classe |
|---|---:|---|
| prefixo que SOBREVIVEU à fronteira | **68.980** | `cache_read` |
| piso RE-CRIADO (não-sumário) | **28.310** | `cache_creation` |
| sumário da compactação (`postTokens`) | **15.346** | `cache_creation` |
| `input_tokens` | **2** | base |
| **total do 1.º turno pós-fronteira** | **112.638** | — |

`68.980 + 43.656 + 2 = 112.638` fecha ao token; `43.656 − 15.346 = 28.310`
isola o piso do sumário.

Os `68.980` não são um número solto: é o valor de `cache_read` **mais
frequente de toda a sessão (20 ocorrências)**, de 2026-08-14T17:40 até
**depois** da fronteira. O prefixo do framework atravessou a compactação sem
reescrita.

**Resposta ao sub-item, em uma linha:** por compactação o piso re-pago é de
**97.292 tokens de OCUPAÇÃO de contexto**, dos quais **28.310 à tarifa de
`cache_creation`** e **68.980 à tarifa de `cache_read`**.

### F.4 — Os dois sentidos em que `~44.786` está refutado

| Grandeza | Medido | vs `~44.786` |
|---|---:|---|
| piso re-pago (ocupação de contexto) | **97.292** | folclore **2,17× PEQUENO** |
| piso re-criado (tarifa cheia) | **28.310** | folclore **1,58× GRANDE** |

**Armadilha nomeada.** O `cache_creation` da fronteira é **43.656** — a 2,5 %
do número folclórico (`(44.786−43.656)/44.786`). Quem "confirmar" o
`~44.786` contra esse campo confirma a grandeza ERRADA: `43.656` inclui os
15.346 tokens do sumário, que não são gate-boot nenhum. A coincidência é
numérica, não semântica.

### F.5 — Censo comportamental: o Gate 1+2 NÃO foi re-executado

Se o custo fosse "o modelo relê o Gate 1+2 depois de compactar", apareceria
como chamadas de ferramenta. Censo de TODO o transcript (15.446 linhas; 992
turnos pré-fronteira, 804 pós):

```
Read de PROTOCOL.md / .claude/team.md / .claude/frontend-team.md /
        ceo-orchestration/SKILL.md ......... 0 ocorrências (PRÉ e PÓS)
ferramenta Skill ........................... 0 ocorrências em toda a sessão
PÓS-fronteira, único gate re-lido .......... Read MEMORY.md, 3.584 chars (~896 est tok)
PÓS-fronteira, Bash citando gate paths ..... 5.572 chars (~1.393 est tok; quase todo um git diff)
                                             TETO SUPERIOR ~2.289 est tok
```

Leitura: dos ~47,7k que o folclore chama de "gate-boot" (§F.6), a metade
CONDICIONAL (`PROTOCOL.md` + `team.md` + `frontend-team.md` + core `SKILL.md`
≈ **37.169** est tok — `6.703+14.698+15.768`) foi re-paga **zero** vezes. O
que é re-pago sem condição é só a parte auto-injectada — `CLAUDE.md` +
índice de memória.

### F.6 — O folclore re-derivado com o instrumento DELE, hoje

```
python3 .claude/scripts/context-budget.py --json     # exit 0
wc -c ~/.claude/projects/<slug-deste-projecto>/memory/MEMORY.md
```

| Categoria | est. tokens (medido agora) | §A (2026-08-18) |
|---|---:|---:|
| `claude_md` | **5.176** | 3.478 |
| `protocol` | 6.703 | 6.703 |
| `team` (2 ficheiros) | 14.698 | 14.698 |
| `core_skill` | 15.768 | 15.768 |
| **Gate 1+2 em disco** | **42.345** | 40.647 |
| `MEMORY.md` (índice, 21.596 chars) | **5.399** | 4.413 |
| **total "gate-boot" folclórico** | **47.744** | 45.060 |

Os `44.786` documentados ⇒ drift de **+6,6 %** contra o mesmo instrumento
hoje. O `CLAUDE.md` sozinho cresceu **+48,8 %** (3.478 → 5.176) em cinco dias.

**Aviso de instabilidade, medido nesta própria madrugada.** Este `MEMORY.md`
foi lido duas vezes por esta unidade com **~21 minutos** de intervalo (várias
unidades autónomas em fan-out simultâneo, cada uma podendo tocar memória no
fecho): primeira leitura 21.205 chars (5.301 est tok), segunda 21.596 chars
(5.399 est tok) — **+391 chars (+1,8 %) sem nenhuma acção desta unidade**. O
"índice de memória" não é constante para efeitos desta tabela: é ele próprio
um alvo em movimento na mesma janela em que se mede o resto. Por isso a
tabela regista o instante, não finge um valor fixo.

### F.7 — `F` não é constante — e a série completa é maior e mais dispersa do que a citação anterior desta secção usava

§C.4 fixa `F` com `n = 2` (97.097 / 98.636). Uma citação anterior desta
mesma unidade usava `n = 13` sem instrumento rastreado. O censo COMPLETO,
agora rastreado em `gateboot_repay.py`, varre os 55 ficheiros `*.jsonl` do
projecto e devolve uma população bem maior:

```
python3 .claude/plans/PLAN-179/w0/gateboot_repay.py | grep -E 'censoring|cold F series'
```
```
cold-F censoring : excluded_no_turns=2 excluded_warm_start=7 excluded_short(<20 turns)=5 included=41
cold F series: n=41 min=84101 max=138552 mean=105392 median=98636 pstdev=16148 spread=54451 (51.7% of mean)
```

**Isto não é "mais ruído" — é uma mudança de regime datável.** Ordenando as
41 sessões por `mtime` do ficheiro há uma fronteira nítida entre
2026-08-14T14:18 e 2026-08-16T10:37 (nenhuma sessão observada no meio):

| População | n | min | max | média | mediana | σ (populacional) | spread |
|---|---:|---:|---:|---:|---:|---:|---:|
| completa (as 41) | 41 | 84.101 | 138.552 | 105.392 | 98.636 | 16.148 | 54.451 (51,7 %) |
| antes de 2026-08-16 | 27 | 84.101 | 138.552 | 111.204 | 116.404 | 17.101 | 54.451 (49,0 %) |
| a partir de 2026-08-16, excl. F.8 | 13 | 88.379 | 98.636 | 93.321 | 93.206 | **3.129** | 10.257 (11,0 %) |

A linha `n=13` **reproduz exactamente** o `n=13`/`σ≈3.129` já citado nesta
secção antes desta revisão — a diferença é que agora se sabe QUE população é
essa (sessões com `mtime ≥ 2026-08-16`, excluindo esta própria sessão de
análise pela razão em F.8) e que ela é um subconjunto de **13 entre 41**, não
"todas as sessões principais do projecto".

Reprodução do corte por data (filtro ad hoc sobre a mesma leitura de
`gateboot_repay.py`; lista ficheiros e `mtime`, não abre conteúdo de sessão):
```
python3 -c "
import glob, os, json, statistics, datetime
PROJ = os.path.expanduser('~/.claude/projects/<slug-deste-projecto>')
CUTOFF = datetime.datetime(2026, 8, 16).timestamp()
vals_pre, vals_post = [], []
for path in glob.glob(os.path.join(PROJ, '*.jsonl')):
    turns = []
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get('isSidechain'):
                continue
            m = ev.get('message')
            if isinstance(m, dict) and isinstance(m.get('usage'), dict):
                turns.append(m['usage'])
    if not turns or int(turns[0].get('cache_read_input_tokens') or 0) or len(turns) < 20:
        continue
    total = sum(int(turns[0].get(k) or 0) for k in
                ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'))
    (vals_pre if os.path.getmtime(path) < CUTOFF else vals_post).append(total)
print('pre', len(vals_pre), statistics.pstdev(vals_pre))
print('post(incl. esta sessão)', len(vals_post), statistics.pstdev(vals_post))
"
```

**Interpretação, sem inventar causa.** A população anterior a 2026-08-16
(n=27) tem média ~19 % mais alta e ~5,5× o desvio-padrão da população recente
(n=13). A mudança é abrupta (zero sessões observadas no intervalo) e afecta
nível E variância ao mesmo tempo — assinatura de uma mudança discreta de
configuração, não de deriva gradual. **Este instrumento não identifica QUAL
mudança**; fica nomeado como pergunta aberta em F.8, não respondido aqui.

**Consequência prática para a leitura "`F` não sobe com o `CLAUDE.md`"**
(F.6): a comparação correcta é DENTRO do regime recente (n=13,
2026-08-16→08-22) — sessões de 2026-08-20 a 2026-08-22 medem 89.359…93.921,
isto é, `F` não subiu quando o `CLAUDE.md` cresceu 48,8 %. Usar a série
completa (n=41) para essa mesma pergunta seria **errado**: misturaria a
mudança de regime de meados de agosto com o crescimento do `CLAUDE.md`, e
atribuiria a UMA causa uma variação que tem pelo menos DUAS.

### F.8 — Fronteiras honestas desta secção

- **`n = 1` para tudo o que é POR-COMPACTAÇÃO.** Um único marcador
  `compact_boundary` nos 55 transcripts deste projecto (5 marcadores no
  `$HOME` inteiro por contagem `grep -c`, sem abrir conteúdo de outros
  repositórios — 4 pertencem a OUTRAS árvores de projecto, medem um piso
  DIFERENTE — outro `CLAUDE.md`, outra superfície de gate — e não podem
  elevar o `n` deste repo).
- **`28.310` herda a barra de erro de F.1** (±~1.046 de contabilidade
  harness↔`usage`; o resíduo efectivamente observado foi 195).
- **A causa da mudança de regime de F.7 não foi identificada, só datada** —
  hipótese não verificada: o mecanismo de carregamento diferido de
  ferramentas (o mesmo que serve os `ToolSearch` desta sessão) começando a
  aplicar-se por volta de 2026-08-15/16 explicaria tanto a queda de nível
  como a de variância, mas isso NÃO foi confirmado por este instrumento.
- **A DECOMPOSIÇÃO de §B continua ABERTA.** F.3 mede a fronteira
  `cache_read`/`cache_creation`, não `system prompt` vs `tool defs` vs
  `CLAUDE.md`. Os 68.980 são um bloco opaco.
- **A rota (1) de §B (`/context`) segue NÃO verificada** — varri todos os
  transcripts deste projecto por uma saída de `/context` capturada: **0**.
- **`est_tokens` de F.6 é chars/4**, nunca o tokenizer. Só F.1–F.3 e F.7 vêm
  de `usage`/`compactMetadata`.
- **Esta própria sessão de análise (subagente) foi excluída de TODAS as
  séries `F`** por medir uma população diferente: 105.398 tokens no primeiro
  turno — system prompt de subagente + catálogo de ferramentas diferido +
  listagem de skills, não o arranque de uma sessão principal. Registado para
  que ninguém a some à série depois.

---

## Estado das ACs de saída de W0

| AC de saída (§4 W0 do plano) | Estado |
|---|---|
| (a) veredito do canal escrito e falsificável | **ABERTO** — W0-1, sonda paga, fora deste relatório |
| (b) taxa de `plan_id=unknown` medida, não estimada | **MEDIDA mas VAZIA** — 2/2 eventos `unknown`; N = 1, sem taxa (§D) |
| (c) `F` e `T` com valores medidos e tabela η reescrita | **FEITO** (§C, §E), com a decomposição de `F` degradada (§B) |
| (extra) custo de gate-boot re-pago por compactação | **MEDIDO** (§F) — 97.292 de ocupação; 28.310 a `cache_creation` + 68.980 a `cache_read`; folclore `~44.786` refutado nos dois sentidos |

---

## Anexo — reprodutibilidade

Todos os comandos desta página são read-only e não tocam `$HOME` de teste,
audit log vivo ou rede.

**Estado real da reprodutibilidade, medido em 2026-08-22/23:**

- **§F é reproduzível.** O instrumento está RASTREADO em
  `PLAN-179/w0/gateboot_repay.py` e a fonte (o transcript
  `1916b9c8-….jsonl`, 18 MB) continua em disco.
- **§C.1 e §D já NÃO são reproduzíveis como escritos.** Os 15 ficheiros
  `audit-log*.jsonl` que o censo de §D varreu não estão mais em disco — nem
  no slug antigo (`~/.claude/projects/ceo-orchestration/`, que hoje retém
  apenas `audit-log.jsonl`) nem no slug nativo pós-migração W1/PLAN-182
  (`~/.claude/projects/-Users-…-ceo-orchestration/`, 2 ficheiros). O `N = 1`
  e o `{'unknown': 2}` sobrevivem só como citação verbatim nesta página.
  Qualquer re-execução de um censo de audit-log tem de declarar QUAL
  diretório lê.
- `census_w0.py` e `usage_probe.py` nunca foram copiados para
  `PLAN-179/w0/` e não estão rastreados. Um relatório cujo instrumento
  desaparece não é reproduzível — e este relatório já perdeu dois.
