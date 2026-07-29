# PLAN-163 T4.3 — Depth probes (OQ3: pin CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1)

- **Data:** 2026-07-28 (S284 probe thread)
- **Substrato:** Claude Code 2.1.220, binário bun-compilado Mach-O arm64 em
  `/Users/joaocanhada/.local/share/claude/versions/2.1.220` (249–257 MB, JS embutido)
- **Protocolo:** red-first; 3 sessões filhas `claude -p --model haiku` (cap 6), cwd em scratch
  FORA do repo, settings mínimo próprio por cwd (sem hooks do repo herdados)
- **Artefatos brutos:** `<scratchpad>/depth-probe/{pinned,unpinned,hookcov}/out.jsonl` (stream-json
  completo), `hookcov/hook-log.txt` (session-scoped; não persistem entre sessões)

**Verdict resumido:** `env-verbatim=sim; negação=funciona; hook-depth2=cobre`

---

## (i) ENV VERBATIM (classe S218) — **SIM, verbatim no binário**

`grep -obaE 'CLAUDE_CODE_MAX_SUBAGENT[A-Z_]*'` sobre o binário 2.1.220:

| byte offset | string | contexto |
|---|---|---|
| 73757296 | `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | tabela de strings (bloco de nomes de env vars) |
| 196576886 | idem | mensagem de erro do cap (ver abaixo) |
| 226161618 | idem | registry de env vars minificado: `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH:()=>ruh` (vizinho de `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION:()=>tuh` e `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS:()=>euh`) |
| 230685714 | idem | **getter do cap** (função `bee`, ver abaixo) |
| 234669027 | idem | **enforcement site** (throw, ver abaixo) |

Variantes próximas confirmadas verbatim: `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION`,
`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`.

**Semântica extraída do bundle (offset 230685714, getter):**

```js
function bee(){let e=Z.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH;if(e!==void 0)return e;
  if(Ous===null){ ... r=t(pt_,aHu); Ous=... r>=1?r:aHu } return Ous}
var aHu=3, pt_="tengu_hazel_trellis"
```

- Env var **sobrepõe** tudo; sem env var o default vem do feature-gate remoto
  `tengu_hazel_trellis` com fallback hardcoded **3**.
- **Enforcement (offset 234669027):** `m=HI(l.agentContext); g=bee(); if(m>=g) throw ...` com
  telemetria `pe("subagent_launch","subagent_depth_cap")` e mensagem literal:
  `Subagent nesting limit reached (depth ${m} of ${g}). Complete this task directly using your
  tools instead of spawning another agent. If the user explicitly requested deeper nesting, ask
  them to raise CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH.`
- Semântica do valor: `m` = profundidade do agente CHAMADOR (main=0). **Pin=1 ⇒ main pode
  spawnar (0<1); agente depth-1 não pode (1>=1).** Exatamente o contrato do OQ3.
- Rail secundário no mesmo site: `subagent_nested_teammate` ("Teammates cannot spawn other
  teammates — the team roster is flat").

## (ii) PROBE DE NEGAÇÃO — **funciona (differential red/green limpo)**

Mesmo prompt nas duas pernas ("Spawne um subagente (Task tool) cuja única tarefa é spawnar
OUTRO subagente que responde ok. Reporte o que aconteceu no nível 2..."), `--model haiku`,
`--output-format stream-json`, cwd scratch isolado; env var checada `unset` no shell pai antes
(perna unpinned rodou com `env -u` explícito).

| | pinned (`=1`) | unpinned (default 3) |
|---|---|---|
| Spawn nível-1 (main→sub) | PERMITIDO (`task_started a10508283210c0b15`) | PERMITIDO (`task_started a0ab3183f835aa939`) |
| Tool de spawn no roster do depth-1 | **AUSENTE** — sub rodou `ToolSearch "select:Agent"` → `"No matching deferred tools found"` | **PRESENTE** — sub invocou `Agent` diretamente |
| Spawn nível-2 (sub→sub) | **NEGADO** (nunca chegou a invocar: ferramenta removida do roster) | **PERMITIDO** — `Async agent launched successfully`, task nível-2 `a588907f3ab193d4b` completou |
| String `Subagent nesting limit reached` no stream | 0 ocorrências | 0 ocorrências |
| exit code | 0 | 0 |

**Mecanismo observado sob pin=1:** a negação se manifesta como **remoção do tool de spawn do
roster do agente depth-1** (nem via ToolSearch ele aparece) — o throw `subagent_depth_cap` do
item (i) fica como backstop, não foi o rail exercido. Consequência prática p/ T5: transcripts
sob o pin NÃO conterão a mensagem "nesting limit reached" no caso comum; o sinal observável é o
sub sem `Agent`/`Task` no roster.

**Nota de substrato (2.1.220):** o tool de spawn chama-se **`Agent`** no wire (o alias `Task`
segue aceito em matchers de hook — ver (iii)); nível-2 unpinned foi lançado como **async agent**
(`background_tasks_changed`), não como Task bloqueante.

## (iii) HOOK-COVERAGE depth-2 — **COBRE (PreToolUse dispara para tool calls do subagente)**

Setup: settings próprio no scratch com hooks PreToolUse `matcher: "Task"` + `matcher: "Bash"`
→ `hook.sh` appenda `tool_name\tsession_id\tcmd` num log. Sessão `claude -p --model haiku`
instruída a NÃO usar Bash no nível principal e spawnar um subagente que roda `echo ok`.

Log (2 linhas, 0 erros em `hook-err.txt`):

```
Agent  session=f4ca1a5d-...  cmd=        subagent_type=general-purpose   <- spawn do main (depth-0)
Bash   session=f4ca1a5d-...  cmd=echo ok subagent_type=                  <- Bash DO SUBAGENTE (depth-1)
```

Cross-check no stream-json: o único `tool_use: Bash` tem `parent_tool_use_id` setado (contexto
SUB); o main só emitiu `tool_use: Agent`. Resultado final: "ok".

Classificação: **cobertura completa na cadeia de 2 níveis** — PreToolUse dispara para tool
calls de agentes depth>=1, com o MESMO `session_id` da sessão principal (hooks do repo enxergam
subagentes; o pin não cria zona cega de governança no nível que continua permitido).

Bônus substrato: matcher `"Task"` casou com o tool renomeado `"Agent"` (aliasing de compat) —
o wiring atual do repo já lista ambos (`.claude/settings.json:298` `Agent|...|Task`), sem gap.

## (iv) REGRESSÃO dos 3 instrumentos Workflow sob o pin — **PENDING (item do pack; exige pin aplicado no repo)**

Não rodado nesta probe (pré-condição: GATE-PIN aplica `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`
no env do repo). Desenho do teste:

1. **Pré-condição provada, não assumida:** positive control comportamental ANTES dos
   instrumentos — no repo pinado, uma sessão-sonda spawna sub que tenta spawn nível-2; asserta
   negação (roster sem `Agent`/`Task` OU mensagem `subagent_depth_cap`). Fixture-green ≠
   enforcement ([[feedback-livefire-catches-what-fixtures-miss]]).
2. **Instrumentos** (todos orquestram em breadth no depth-1 — hipótese: pin=1 não os afeta):
   - `audit-fanout` (escopo smoke 1 subtree): 8 finders + refuters + synthesis todos spawnam
     (contagem de shards == baseline unpinned), 0 tentativas de spawn depth-2 no transcript.
   - `nightly-hygiene`: 8 dimensões + synthesis completam; relatório retornado íntegro.
   - `council-audit` (escopo mínimo, lanes claude-only se custo importar): lanes + verify
     completam; quorum não degrada por causa do pin.
3. **Oráculos por instrumento:** (a) exit/verdict do instrumento == baseline; (b) contagem de
   agentes spawnados (audit-log HMAC / task_started events) == baseline; (c) grep transcript
   por `Subagent nesting limit reached` e por ToolSearch-miss de `Agent` — deve ser 0 nos
   fluxos normais (qualquer hit = o instrumento dependia de nesting ⇒ regressão, ajustar antes
   do GATE-V2); (d) hook-coverage do repo segue disparando para os subs (amostra no audit log).
4. **Red-first:** rodar o canário do passo 1 também SEM o pin (deve PERMITIR) para provar que o
   oráculo distingue os dois estados.

---

## Custo / conformidade

- Sessões filhas: **3 de 6** (pinned, unpinned, hookcov) — todas `--model haiku`, ~10 k tokens
  cada, <90 s cada; runtime total da probe << cap 20 min.
- Nenhum path canônico tocado; escrita apenas neste arquivo + scratchpad.

---

## ADENDO — replicação independente (2º probe thread, mesmo dia, rig distinto)

Um segundo probe thread executou (i)–(iii) de forma independente, com rig diferente, ANTES de
ler este artefato. **Todos os verdicts replicam** (`env-verbatim=sim; negação=funciona;
hook-depth2=cobre`) — n=2 de confirmação empírica. Evidência bruta:
`<scratchpad>/depth-probe/{out_pinned2.txt,out_unpinned3.txt,out_hookcov.txt,hooklog.jsonl,prompt2s*.txt,probe-settings.json,pin-settings.json,pincheck.sh}`.

Diferenças de rig (fortalecem a prova por diversidade):
- **(ii)** pin aplicado em DOIS rails simultâneos — prefixo env na invocação **e** bloco
  `{"env": {...: "1"}}` via `--settings` — com confirmação IN-SESSION (`pincheck.sh` reporta só
  `PIN-SET-1`/`PIN-NOT-1`). Depth-1 auto-reportou o roster: pinned `TOOLS-HAS-TASK: no` +
  `TOOLS-HAS-AGENT: no` → `SKIPPED-NO-TOOL`; unpinned `TOOLS-HAS-AGENT: yes` →
  `NESTED-OUTCOME: SUCCEEDED ok`. Mesmo mecanismo: **remoção de tool do roster**, zero
  ocorrências da mensagem de nesting-limit.
- **(iii)** hook único `matcher: "*"` logando o stdin JSON integral: 2 fires, MESMO
  `session_id`; a call do subagente (`Bash echo ok`) carrega as chaves extras **`agent_id` +
  `agent_type`** ausentes na call depth-0 — segundo discriminador de origem além do
  `parent_tool_use_id` do stream-json (útil para o censo de profundidade do desenho (iv) sem
  parsear o stream).

Gotchas de harness adicionais (classe substrate-drift, relevantes p/ T5/pack e futuras probes):
1. **`CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`** presente no env do harness força permission mode
   `default` no `claude -p` filho e neutraliza `--dangerously-skip-permissions` (aviso no
   stderr do filho) — declarar `--allowedTools` explicitamente.
2. **`CLAUDE_CONFIG_DIR` fresco não herda auth** (login por config-dir; Keychain não
   compartilha) → `Not logged in`. Isolamento viável: cwd scratch + `--settings` próprio +
   user-global verificado sem hooks.
3. **`--allowedTools` é variádico** e engole o prompt posicional — usar valor único
   com vírgulas e prompt via stdin.
4. Subagente pode ser lançado em **background** e a sessão `-p` encerrar antes do resultado —
   probes devem instruir foreground/wait explicitamente.
- Custo do adendo: 6 sessões filhas com consumo API (cap 6/6 deste thread; 3 prompt-v1 +
  2 sharpened + 1 retry foreground); 5 tentativas extras falharam pré-API (2 auth, 3 parse de
  flag) com custo zero.
