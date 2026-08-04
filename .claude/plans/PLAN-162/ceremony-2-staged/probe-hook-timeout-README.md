# probe-hook-timeout-210s — README

Sonda do gate BLOQUEANTE do ADR-110-AMEND-2 §6 (bullet 1). Responde a
pergunta que segura a cerimônia: **o harness do Claude Code honra um hook
PreToolUse registrado com `"timeout": 210`, ou mata o hook antes num teto
não documentado?**

Por que isso bloqueia a cerimônia: se o teto real for menor que 210 s, o
harness mata `check_pair_rail.py` ANTES do cap interno de 180 s — e um
hook morto **não emite `pair_rail_case` nenhum**. Isso é fail-open SEM
EVENTO: invisível ao instrumento da taxa de censura no numerador E no
denominador — estritamente pior que o case F de hoje. Subir o deadline
sem esta prova seria assinar exatamente essa classe de bug.

## Custo e como rodar

- **Custo:** ~4–5 min de wall clock (o tratamento sozinho bloqueia
  ~200 s), 3 chamadas headless `claude -p` com modelo `haiku`
  (centavos). Não roda nada contra a árvore do repo — workspace 100 %
  em `/tmp`, camadas de config neutralizadas.
- **NÃO execute de dentro de uma sessão governada sem ack do CEO** — a
  sonda sobe sessões vivas do harness.
- Comando (uma linha, paste-safe):

```
# a partir da raiz do repo:
bash .claude/plans/PLAN-162/ceremony-2-staged/probe-hook-timeout-210s.sh
```

Knobs (env, todos opcionais):

| Var | Default | Uso |
|---|---|---|
| `PROBE_MODEL` | `haiku` | Modelo das 3 chamadas `-p`. Se o haiku recusar rodar o Bash, tente `sonnet`. |
| `PROBE_TREATMENT_SLEEP_S` | `200` | Duração do bloqueio do tratamento (caso B). |
| `PROBE_REGISTERED_TIMEOUT_S` | `210` | Timeout registrado nos casos A e B. |
| `PROBE_KEEP_HOME` | `0` | `1` = mantém o `$HOME` real (só se o caso A falhar por auth — ver troubleshooting). |
| `PROBE_CLAUDE_BIN` | (PATH) | Caminho explícito do binário `claude`. |

## Desenho: 3 casos, controles ANTES do tratamento

A ordem é A → C → B: os dois controles são baratos e rodam antes dos
200 s pagos do tratamento. **Um controle que não falha quando deveria é o
único sinal de que a sonda está morta** — por isso o controle negativo é
inegociável (memória: `feedback-probe-needs-neutral-user-layer`).

| Caso | Hook dorme | Timeout registrado | Deve acontecer | O que prova |
|---|---|---|---|---|
| **A** (controle positivo) | 5 s | 210 | Hook COMPLETA (`start` + `end`) | Hooks disparam e completam sob as camadas neutras; markers funcionam |
| **C** (controle negativo) | 20 s | 10 | Harness MATA (`start` sem `end`; heartbeat para ~10 s) | O mecanismo de kill existe E o heartbeat consegue OBSERVAR um kill |
| **B** (tratamento) | 200 s | 210 | — é a pergunta | `end` presente = harness honrou ≥200 s sob 210; só `start` = matou cedo, e o delta mede o teto real |

O hook dummy escreve `start` (epoch), heartbeat de 1 Hz (`hb`, um epoch
por linha), e `end` (epoch) + `{}` schema-compliant ao terminar. Se
morto, o último heartbeat ≈ instante do kill → **teto = last(hb) −
start**, com granularidade de ~1 s (suficiente para distinguir 210 de
120/150/60). Cada caso também pede ao modelo que rode
`date +%s > case_X.tool_ran` — isso desambigua "hook não disparou" de
"modelo nem chamou Bash".

### Neutralização (obrigatória nesta máquina)

O `~/.claude/settings.json` do Owner tem `Bash(*)`/Edit/Write globais e
`defaultMode: auto` — qualquer sonda que herde isso mede a config dele,
não o harness. A sonda aponta `CLAUDE_CONFIG_DIR` (e `HOME`, salvo
`PROBE_KEEP_HOME=1`) para um workspace fresco em `/tmp`, e registra o
hook dummy **na própria camada de usuário neutra** — o que também evita o
prompt de trust de hooks de projeto. O diretório de projeto usado é vazio.

A sonda imprime seus INPUTS (versão do claude, modelo, o settings.json
exato de cada caso, paths) — medição sem inputs não é medição. O
workspace é preservado após a corrida para inspeção.

## Interpretação — GO/NO-GO do AMEND-2 §6

| Exit | Veredito impresso | Significado | Decisão |
|---|---|---|---|
| `0` | **HONRA** | A ok, C matou, B completou ~200 s sob registro 210 e RETORNOU | **GO** — §6 bullet 1 satisfeito; a cerimônia pode landar o 180/210 |
| `1` | **NÃO-HONRA** + `TETO REAL MEDIDO ≈ Ns` | A ok, C matou, B foi morto antes de completar | **NO-GO** — "the amendment does not land as written". O par 180/210 volta ao debate e tem de ser re-derivado SOB o teto medido (registro ≤ teto − margem; interno = registro − 30) |
| `2` | INVALID (controle positivo) | Caso A não completou — hooks não disparam / auth / modelo não chamou Bash | Sonda MORTA. Não interprete nada; conserte e re-rode |
| `3` | INVALID (controle negativo) | Caso C não foi morto — o campo `timeout` pode estar INERTE no substrato atual | Sonda MORTA para esta pergunta. Não leia GO daqui; é um achado de substrate-drift por si só — escale ao CEO |
| `4` | erro de ambiente | binário `claude` não achado etc. | Conserte e re-rode |

**Critério GO explícito:** exit `0`, com os três conjuntos de markers
impressos no bloco `MARKERS` batendo com a tabela de casos. Qualquer
outra saída = a cerimônia 2 NÃO inclui os literais 180/210.

### Mapeamento honesto para o texto do §6

- §6 bullet 1 pede "a hook registered at 210 s that blocks for ~185 s
  still RETURNS and still emits `pair_rail_case`". A sonda bloqueia
  **200 s** (mais conservador que 185) e prova que o PROCESSO do hook
  sobrevive até o código pós-bloqueio (o `end` marker é escrito
  exatamente no ponto do fluxo em que `check_pair_rail.py` emitiria seu
  evento). A emissão do evento em si é código do próprio hook, já coberto
  pelos testes dele — o que só a sonda pode provar é que o harness deixa
  o processo chegar lá.
- §6 bullet 2 ("true-orphan count stays 0") **NÃO é coberto por esta
  sonda**: baseline já medido em 0 na registração 150; re-verificar
  PÓS-LAND com `.claude/scripts/local/pair-rail-latency.py` (que imprime
  a contagem de órfãos junto com seus inputs).

### Caveats registrados

- A sonda roda `claude -p` **headless**; o pair-rail dispara em sessões
  interativas. Assume-se que o teto de timeout de hook não difere por
  modo (diferente do gate de `defaultMode`, que sabidamente difere). Se o
  resultado do caso B ficar na margem (kill entre 195 e 210 s), confirme
  interativamente antes de decidir.
- O hook é registrado na camada de usuário (config dir), não na de
  projeto. Assume-se que a camada de registro não muda o tratamento do
  campo `timeout`.
- `sleep 200` em loop de 1 Hz deriva ~1–2 s (fork do `date`); o bloqueio
  real do caso B é ~201–202 s — ainda sob 210 com ~8 s de folga.

## Troubleshooting

- **Caso A INVALID com `tool_ran` AUSENTE** → o modelo não chamou Bash ou
  o startup falhou sob o HOME neutro. Leia `claude_a.out` no workspace;
  se for erro de auth (credencial fora do Keychain), re-rode com
  `PROBE_KEEP_HOME=1` (mantém o HOME real; `CLAUDE_CONFIG_DIR` continua
  neutralizando a config). Se for recusa do modelo, `PROBE_MODEL=sonnet`.
- **Caso A INVALID com `tool_ran` PRESENTE** → o Bash rodou mas o hook
  nunca disparou: problema de registro/camada. Inspecione o
  `settings.json` impresso no bloco de INPUTS do caso.
- **Watchdog matou o claude** (`wall budget exceeded` no log) → o teto do
  runner (A/C: 180 s; B: 360 s) foi atingido — normalmente indica sessão
  pendurada, não veredito. Trate como INVALID do caso.
