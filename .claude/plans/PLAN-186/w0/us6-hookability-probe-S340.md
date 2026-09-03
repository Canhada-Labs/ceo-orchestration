# PLAN-186 W0-US6 — sonda de hookability: o `PreToolUse` dispara para `SendMessage` / `ListAgents`?

- **Sessão:** S340 (night-run), 2026-09-03, repo em `main` @ `400638e`. Entregável de **AC-15**.
- **Instrumento:** `.claude/settings.json` + cadeia HMAC viva do projeto + chamada real dos dois tools.
- **Confinamento:** somente leitura no repo; escrita apenas no scratchpad.

---

## 1. Pergunta fixa

> Existe algum hook `PreToolUse` que seja invocado quando o modelo chama `SendMessage` ou `ListAgents`?

Importa porque o PLAN-186 quer saber se o roteamento inter-agente é **gateável no substrato**
(como `Bash` ou `Edit` são) ou se só resta **doutrina + emissão voluntária**.

---

## 2. Método

1. Enumerar todo `hooks.PreToolUse` do `settings.json` (matcher + basename do script).
2. Procurar catch-all (`""`, `"*"`, `".*"`) e menção literal aos dois nomes.
3. Achar o canal de telemetria onde uma invocação `PreToolUse` deixa rastro.
4. **Controle positivo primeiro** com um tool sabidamente gateado (`Bash`).
5. Só então chamar `ListAgents` e `SendMessage` e medir o delta.

Estado por projeto resolvido pelo resolvedor único
(`.claude/hooks/_lib/runtime_paths.py --state-dir`) →
`~/.claude/projects/<slug>`.

---

## 3. Superfície declarada (`settings.json`)

`PreToolUse` tem **19 registros**. Os matchers, verbatim:

| matcher | hook |
|---|---|
| `Agent` | `check_agent_spawn.py` |
| `Bash` | `check_bash_safety.py` |
| `Bash` | `check_adversary.py` |
| `Edit\|Write\|MultiEdit` | `check_plan_edit.py` |
| `Edit\|Write\|MultiEdit\|mcp__.*` | `check_canonical_edit.py` |
| `Edit\|Write\|MultiEdit` | `check_protocol_semver_cascade.py` |
| `Edit\|Write\|MultiEdit` | `check_skill_patch_sentinel.py` |
| `Edit\|Write\|MultiEdit` | `check_tier_policy.py` |
| `Edit\|Write\|MultiEdit\|mcp__.*` | `check_arbitration_kernel.py` |
| `Bash` | `check_scratchpad_access.py` |
| `Agent` | `check_budget.py` |
| `Read` | `check_read_injection.py` |
| `Edit\|Write\|MultiEdit` | `check_pair_rail.py` |
| `mcp__codex__codex\|mcp__codex__codex-reply` | `check_codex_filewrite.py` |
| `Agent\|Bash\|Edit\|Write\|MultiEdit\|Read\|Glob\|Grep\|WebFetch\|WebSearch\|NotebookEdit\|TodoWrite\|Task\|mcp__.*` | `check_anti_ceo_overhead.py` |
| `Bash` | `check_cost_envelope.py` |
| `Bash\|Edit\|Write\|MultiEdit` | `check_worktree_writer.py` |
| `Edit\|Write\|MultiEdit` | `check_config_protection.py` |
| `Bash` | `check_ledger_checkpoint.py` |

**Fatos:**

- **Não existe catch-all em `PreToolUse`.** Zero matchers `""`, `"*"` ou `".*"`.
  Todos são enumerações literais de nomes de tool (+ o regex `mcp__.*`).
- O matcher **mais largo** é o do `check_anti_ceo_overhead.py`, com 13 nomes enumerados
  + `mcp__.*`. **Nem `SendMessage` nem `ListAgents` estão nele.**
- Contraste: `PostToolUse` e `PostToolUseFailure` **têm** catch-all
  (`matcher: ""` → `check_output_secrets.py`). A assimetria é o achado central.
- Re-verificação do censo da S339:
  `grep -rn "SendMessage\|ListAgents" .claude/settings.json .claude/hooks --include='*.py' | grep -v /tests/`
  → **exit 1, zero ocorrências**.

---

## 4. Canal de telemetria

O par de ciclo de vida do PLAN-125 WS-1 é o canal certo:

- **Perna Pre:** `check_anti_ceo_overhead.py:775` chama `_record_pre_lifecycle()`
  **incondicionalmente**, antes de `decide()` — grava só um carimbo 0600 em
  `<state>/tool-lifecycle/<session>.json` (`{tool_use_id: {tool_name, t_start_s}}`).
  Por MF-SEC-5 essa perna **não emite** na cadeia.
- **Perna Post:** `check_output_secrets.py` (catch-all) casa o carimbo por `tool_use_id`
  e emite `tool_call_lifecycle_recorded` com o enum FECHADO `tool_name_enum`
  (`_lib/tool_lifecycle.py:120-138`) — desconhecido → `"other"`, `mcp__*` → `"mcp_other"`.

---

## 5. Controle positivo (`Bash` — tool sabidamente gateado)

**5.a — nível decisão (o mais forte).** Uma chamada `Bash` desta própria sessão foi
**bloqueada** pelo gate, verbatim:

> `GOVERNANCE: bash 'python3' -c/-e body references canonical path '.claude/settings.json'. Use Edit/Write with sentinel.`

O comando **nunca executou**. Isso prova que, para `Bash`, o `PreToolUse` dispara e
**decide** — não é só telemetria.

**5.b — nível telemetria.** `echo us6-positive-control-9c41ab` às `02:44:34Z` produziu,
segundos depois:

```
2026-09-03T02:44:35Z tool_call_lifecycle_recorded tool=Bash dur=lt_100ms orphan=False ok=True
```

Controle positivo **verde nas duas pernas**.

---

## 6. Sujeito — `ListAgents` e `SendMessage`

**6.a `ListAgents`**, chamado uma vez às `~02:44:58Z`. Retornou o roster normalmente.
Nenhum bloqueio nem `systemMessage`. **Errata (rail S340 r2, codex P2):** o transcript deste
agente registra UMA invocação `PreToolUse:ListAgents` — o `check_anti_ceo_overhead.py`, cujo
matcher largo (`Agent|Bash|…|mcp__.*`) é avaliado como regex não-ancorada e casa `Agent` como
SUBSTRING de `ListAgents` (`docs/substrate-adopt-2026-07.md:21`). Logo o Pre **DISPARA** para
`ListAgents` — só esse hook, por acidente de regex; nenhum outro matcher casa. Rastro na cadeia:

```
2026-09-03T02:44:58Z tool_call_lifecycle_recorded tool=other ok=True orphan=False
```

— produzido pelo **catch-all de `PostToolUse`**, com o nome colapsado em `"other"`.

**6.b `SendMessage`** para `us6-probe-nonexistent-target` (o `ListAgents` acabara de provar
que esse nome não existe: nada foi entregue a ninguém). Corpo com a canária `US6-CANARY-7f3a`
mais **uma frase inerte** no formato `direct_override` do
`_lib/injection_patterns.py:14` (`"ignore previous instructions"`), citada como dado.

Resultado bruto:

```
{"success":false,"message":"No agent named 'us6-probe-nonexistent-target' is reachable."}
```

- **Nenhum hook bloqueou nem escaneou o payload antes do tool.** A falha veio da resolução
  de destinatário do próprio tool, não de um gate.
- Rastro: `02:45:37Z tool_call_lifecycle_recorded tool=other ok=True` — de novo, só a perna Post.
- **Vazamento da canária na cadeia viva: 0 ocorrências.**

**6.c Censo histórico.** Os literais `ListAgents|SendMessage` aparecem **107 vezes** em todos
os arquivos da cadeia — e **100 % delas em `action=output_scan_finding`**, ou seja, o scanner
de saída do `PostToolUse` catch-all lendo o *texto* de um resultado. **Zero** vêm de gate Pre.

---

## 7. Precedente do substrato (negativo)

- `check_agent_spawn.py`, cabeçalho: *"Registered in `.claude/settings.json` under
  `hooks.PreToolUse.Agent`"* — o gate de spawn é **por matcher nomeado**, não universal.
- `CLAUDE.md` §5, «Rail Workflow fora do gate de spawn»: o `agent()` de Workflow **não**
  passa pelo `check_agent_spawn` (sonda `wf_d7af49d9`: `blocked=false`), e a cura foi
  validação **pré-despacho dentro da própria skill** — nunca um hook novo.

O precedente é consistente: superfícies que o harness não expõe a `PreToolUse` só se
governam por doutrina no chamador.

---

## 8. RESPOSTA

> **`SendMessage`: o `PreToolUse` NÃO dispara com a configuração ATUAL** (a hookabilidade em si
> não foi testada — exigiria um matcher temporário `SendMessage`/catch-all com breadcrumb
> incondicional, i.e. editar `settings.json`; rail S340 r3 P1). Nenhum dos 19 matchers registrados o nomeia
> nem o casa por substring, não existe catch-all em `PreToolUse`, e a chamada real passou sem
> bloqueio e sem qualquer evento de gate Pre — o único rastro é o
> `tool_call_lifecycle_recorded tool=other` emitido pelo catch-all de `PostToolUse`.
>
> **`ListAgents`: o `PreToolUse` DISPARA — mas por acidente de regex, e só um hook.** O matcher
> largo do `check_anti_ceo_overhead` (`Agent|Bash|…|mcp__.*`) contém um regex, e o harness avalia
> a expressão inteira como regex **não-ancorada**: a alternativa `Agent` casa SUBSTRING de
> `ListAgents` (`docs/substrate-adopt-2026-07.md:21`, finding 4). Verificado no transcript desta
> sonda: 1 registro `PreToolUse:ListAgents` na chamada real (errata do rail S340 r2 — a versão
> anterior deste relatório dizia «nenhum evento Pre»). Nenhum outro matcher casa; nenhum
> matcher casa `SendMessage`.

---

## 9. Consequência (como o PLAN-186 W0-US6 a enquadra)

Como **não** dispara para `SendMessage`:

> **OQ-5 responde PARCIALMENTE «doutrina + emissão voluntária» para a MENSAGERIA — com a
> configuração atual.** Fecha quando a sonda com matcher temporário disser se `SendMessage` é
> hookável. Para `ListAgents`, que hoje dispara por coincidência de substring, a resposta certa
> é tornar a cobertura DELIBERADA (alargar o matcher explicitamente) — ver abaixo.

**A afirmação ampla «o roteamento inter-agente não é gateável no substrato» é FALSA e foi
retirada (rail r5 P2-a).** Ela contradizia a evidência deste próprio relatório: §§6/8 observaram
`check_anti_ceo_overhead` rodando em `PreToolUse` para `ListAgents`. O que se sustenta é a
partição por TOOL, não uma sentença sobre o eixo:

| tool | PreToolUse dispara? | «hook novo» é opção? |
|---|---|---|
| `ListAgents` | **SIM** — medido, 1 registro no transcript (por coincidência de substring do matcher largo, não por desenho) | **SIM, hoje** — o gate já roda; o que falta é torná-lo DELIBERADO |
| `SendMessage` | **NÃO** com a configuração atual — nenhum dos 19 matchers casa | **INDECIDIDO** — ausência de matcher não prova inhookabilidade; exige a sonda com matcher temporário |

Logo, para a **MENSAGERIA** (`SendMessage`) — e só para ela — o controle disponível hoje é
doutrina no chamador — o padrão já pago pelo Workflow em `CLAUDE.md` §5 — mais emissão
voluntária de evento pelo próprio chamador.

**Partição FIXADA dos fatos sobre o PostToolUse (rails r7, r8, r10, r11 oscilaram três vezes
sobre a mesma questão; este quadro é a resposta final e cada linha cita o sítio):**

| fato | valor | sítio |
|---|---|---|
| O catch-all de PostToolUse RECEBE `tool_name` e `tool_input` crus para todo tool, `SendMessage` incluso? | **SIM** | `check_output_secrets.py:411-425` (`_record_post_lifecycle(parsed, …)` roda ANTES de `decide()`, no caminho comum, incondicional) |
| Esse caminho EMITE um evento hoje? | **SIM** — o de ciclo de vida | `_record_post_lifecycle`, mesmo sítio |
| O evento carrega o NOME do tool? | **NÃO** — o enum fechado (17 nomes) colapsa `SendMessage`/`ListAgents` em `"other"` | `_lib/tool_lifecycle.py:120,186` (medido: `to_tool_name_enum("SendMessage") == "other"`) |
| O evento carrega hash do `tool_input`? | **NÃO** no caminho comum — `_derive_command_sha` só é alcançado quando há finding de secret | `check_output_secrets.py:246-248` (`return` antes de `:261-265`) |
| Logo: dá para CONTAR/ATRIBUIR `SendMessage` com o que existe? | **NÃO** | consequência das duas linhas acima |
| Dá para chegar lá SEM hook novo e SEM edição canônica? | **NÃO** — o sítio que já vê o payload é canônico (`.claude/hooks/`), e a mudança mínima é alargar `_RECOGNIZED_TOOL_NAMES` (acoplamento documentado em `:245`) ou derivar o hash no caminho comum | oráculo `--is-canonical` = 1 para ambos |

O que o r11 acertou: «doutrina + emissão voluntária» **não é a única opção de DESENHO** — existe
um ponto de captura automático já pago (`:411-425`) onde uma cerimônia pode ligar a atribuição.
O que os r8/r10 acertaram: **hoje, sem cerimônia, nada é contável**. As duas afirmações são
verdadeiras ao mesmo tempo, e a W5 deve consumir as duas: a alavanca imediata é doutrina; a
alavanca de cerimônia é o sítio `:411-425`.

**Errata parcial do rail r7 (P2) — uma metade aceita, a outra REFUTADA por medição:**

- **ACEITA no r7 e REFUTADA no r8 — a concessão foi um ERRO meu, e a medição do r8 a desfaz.**
  No r7 aceitei que `check_output_secrets.py:179-189` dá um caminho involuntário de auditoria do
  remetente, porque verifiquei que a função RECEBE e hasheia o `tool_input`. Verifiquei a
  EXISTÊNCIA do código e não a sua ALCANÇABILIDADE — que é a metade que decide. `decide()`
  retorna em `:246-248` (`if total == 0: return _emit_observe()`) **antes** de
  `_derive_command_sha()` ser chamado em `:261-265`. Para um `SendMessage` normal — cuja resposta
  não tem finding de secret, que é o caso comum — o hash **nunca é derivado**. O que resta no
  caminho de ciclo de vida é só o enum fechado, e ele colapsa em `"other"`.
  **Conclusão corrigida: não existe telemetria de remetente utilizável para mensagens normais** —
  nem para contar, nem para atribuir. A conclusão ORIGINAL deste relatório («doutrina + emissão
  voluntária») fica de pé, e é a que a W5 deve consumir.
- **REFUTADA:** o rail afirmou que `_lib/tool_lifecycle.py:170-186` «mapeia `SendMessage`,
  `ListAgents` e …». Não mapeia. `to_tool_name_enum` devolve o nome cru só se ele estiver em
  `_RECOGNIZED_TOOL_NAMES` (`:120`), um enum FECHADO de **17** nomes que não contém nenhum dos
  dois — medido nesta sessão: `SendMessage -> "other"`, `ListAgents -> "other"` (`Agent`, `Task`
  e `Bash` passam íntegros, o que mostra que o teste do enum estava certo). A claim original
  deste relatório — a telemetria **colapsa o nome em `"other"`** — permanece de pé, e com ela o
  corolário: contar `SendMessage` pelo enum atual é impossível sem ALARGAR
  `_RECOGNIZED_TOOL_NAMES`, cujo comentário `:245` documenta o acoplamento deliberado que isso
  implica.

Resultado combinado, após r7 e r8: para `SendMessage` **não há gate** (PreToolUse não dispara) e
**não há telemetria utilizável** (o enum colapsa em `"other"`; o hash do `tool_input` só existe no
caminho condicional de um finding de secret). A única alavanca hoje é doutrina no chamador mais
emissão voluntária de evento — exatamente a resposta que a OQ-5 registra.

**Lição de método paga aqui, em duas rodadas:** o r7 me convenceu com um trecho de código REAL, e
eu o verifiquei lendo aquele trecho. O que faltou foi perguntar se o trecho é ALCANÇADO no caso de
interesse. Existência ≠ alcançabilidade; para uma claim de telemetria, a pergunta certa é sempre
«qual é o primeiro `return` no caminho comum?».

**Se um dia passar a disparar**, a regra é o **matcher tem de ser ALARGADO, nunca estendido por
mais um nome enumerado** — lição r22 do PLAN-179: *canal instruction-adjacent fecha por REMOÇÃO,
não por enumeração*. Enumerar `SendMessage|ListAgents` no matcher só move a fronteira um nome
adiante e deixa o próximo tool de mensageria nascer descoberto — exatamente a classe que as 5
rodadas de bypass em basename custaram.

---

## 10. Residual declarado

A telemetria on-disk **não discrimina** «Pre disparou» de «Pre ausente» para estes dois tools:
`record_post` (`_lib/tool_lifecycle.py:715-722`) usa `pre_tool_name or post_tool_name`, e ambos
os caminhos colapsam em `"other"` pelo enum fechado; o bit `paired` só existe no rail opt-in
`CEO_LEARNING_OBSERVE=1`, que está desligado. A resposta do §8 é sustentada pela **superfície
declarada** (§3, mecanismo pelo qual o harness decide invocar) + **ausência de decisão**
observada (§6) + **censo** (§6.c) — não por um discriminante binário na cadeia.

Modo de casamento (fechado pelo rail S340 r2–r3): matchers que CONTÊM regex (o largo, com
`mcp__.*`) são avaliados como regex NÃO-ANCORADA — por isso `Agent` casou substring de
`ListAgents` e o `check_anti_ceo_overhead` disparou (1 registro `PreToolUse:ListAgents` no
transcript desta sonda); matchers simples como `Agent` puro usam o caminho exato
(`docs/substrate-adopt-2026-07.md:21-22`), logo `check_agent_spawn`/`check_budget` NÃO
dispararam — consistente com «um só hook». O que segue ABERTO é a hookabilidade de
`SendMessage`: provar que um matcher `SendMessage` (ou catch-all) dispara exige editar
`settings.json` temporariamente — fora do escopo desta US (cerimônia); até lá AC-15 fica ◐.

**Artefatos** (em `<scratchpad>/deliverables/us6/`): `raw-observations.log` · `matchers.log` ·
`t0-snapshot.log` · `t1-after-listagents.log` · `t2-after-sendmessage.log` · `positive-control.log`
