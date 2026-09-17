---
plan: PLAN-190
round: 1
created_at: 2026-09-17
proposal: "W1 — ledger de lançamento de Workflow + guard de retomada"
materials:
  - .claude/plans/PLAN-190-autonomous-execution-recoverable.md
  - .claude/plans/PLAN-190/w1/p190-w1.patch
  - .claude/plans/PLAN-190/w1/add-workflow-hook-registration.py
  - docs/research/s354-token-consumption-study/03-collector-audit.md
---

# PLAN-190 — debate round 1 — proposta: W1

Plano completo: `.claude/plans/PLAN-190-autonomous-execution-recoverable.md`. Esta proposta destila a
W1, a primeira wave canônica. Patch já provado numa sombra descartável (branch `p190-w1`,
`.claude/plans/PLAN-190/w1/p190-w1.patch`, 1.223 linhas, 9 paths, 5 canônicos): 23 testes verdes,
template `user` regenerado e conferido, 95 referências de hook executáveis, diffs de settings só com
adições.

## Tese

O trabalho pago em execuções autônomas de Workflow se perde porque NADA observa o lançamento: o
harness persiste os `args` só quando o run termina, nunca o hash do script nem a revisão do código; a
chave do cache de resultados do runner é `(prompt, opts)` de cada `agent()`; logo um prompt editado
em voo ou um `args` reconstruído de memória re-executa fases concluídas. Medido num consumidor (S354):
**15,5 % das fases iniciadas sem resultado; 16 % dos starts são reexecuções**; um incidente de 17
fatias reimplementadas por edição de prompt e outro de 11 regressões por args de memória; com args
exatos, 12/12 retomadas na fase certa. A W1 fecha essa classe tornando o lançamento e a retomada
RECUPERÁVEIS e VERIFICÁVEIS antes do despacho.

## Escopo (declarado na v1 como 9 paths; o patch real tem 22 — ver consensus.md ajuste 6: 5 canônicos +
tests/CLI/doc + 10 bumps de contagem + pinos de paridade + mapa gerado + inventário de env + CHANGELOG)

| path | canônico | o quê |
|---|---|---|
| `.claude/hooks/_lib/launch_ledger.py` | C | manifesto por lançamento: script sha256 (inline ou `scriptPath` lido do disco), `args` literal canônico (ausente ≠ `null`), `resumeFromRunId`, revisão git do `cwd`, `session_id`/`tool_use_id`; escrita atômica 0600 + índice `launches.jsonl` sob `FileLock`; `compare()` por hash + chaves de `args`; `decide_pre`/`decide_post` |
| `.claude/hooks/check_workflow_launch.py` | C | PreToolUse/PostToolUse na tool `Workflow`; fail-open; kill `CEO_WORKFLOW_LEDGER=0`; sem evento de auditoria (registro de ação é cerimônia do dono do audit) |
| `.claude/settings.json` + `templates/settings/settings.base.json` + `settings.user.json` (derivado) | C | 2 registrações (`matcher: "Workflow"`), via derivador idempotente `add-workflow-hook-registration.py` |
| `.claude/scripts/ceo-launches.py` | livre | `list · show · relaunch · check · bind · report` |
| `.claude/hooks/tests/test_check_workflow_launch.py` (13 e2e) + `tests/unit/test_launch_ledger.py` (10) | livre | ver §Testes |
| `docs/workflow-recovery.md` | livre | rito de recuperação, limites declarados |

## Decisões tomadas (a criticar)

1. **Persistir ANTES do despacho, no hook, não no script do consumidor.** O script JS do consumidor
   não vê a chamada da tool; o hook vê `tool_input` inteiro. Registro independente do ciclo de vida do
   harness (morte de processo/reboot não perde o registro).
2. **Guard = bloqueio só no caso demonstrado**: `resumeFromRunId` com hash de script ou `args`
   diferentes do manifesto VINCULADO ao run. Sem manifesto ⇒ advisory. Rota: `relaunch` imprime a
   chamada exata; `CEO_WORKFLOW_RESUME_FORCE=1` libera e fica registrado. Fail-open em infraestrutura
   (não é matcher de segurança).
3. **Vínculo run ↔ manifesto no PostToolUse** por `tool_use_id` (exato), fallback «último não
   vinculado da sessão»; extração do `wf_<hex8>[-<hex>]` por forma; `bind` manual na CLI cobre
   mudança de forma da resposta.
4. **`args` literal, não normalizado semanticamente**: chave ausente é `<absent>`; `null` é `null`;
   ordem de chaves não importa (JSON canônico). Diff nomeia chaves de topo (hashes curtos dos valores,
   nunca o conteúdo) — o motivo de bloqueio vai ao modelo, então NÃO carrega valores de `args`.
5. **Nenhum evento de auditoria nesta wave**: `_KNOWN_ACTIONS` + SPEC são cerimônia do dono do audit;
   o ledger é o registro. Follow-up nomeado.
6. **Distribuição pelo mecanismo existente**: hook chega pela enumeração de `.claude/hooks/` no
   manifesto; registração pelo template base (o `user` deriva por subtração e NÃO exclui este hook:
   é proteção do operador, com rota advisory/kill).
7. **Contagens citadas em docs** (hooks 59→60, `_lib` 71→72) entram no mesmo pacote (verify-counts
   é gate de corpus).

## Testes (na sombra: 23/23)

e2e (subprocesso, stdin JSON → stdout decisão, `TestEnvContext`): manifesto antes do despacho com
args literais; ausente ≠ null; `scriptPath` hasheado do disco; retomada idêntica ⇒ `match`; script
diferente ⇒ block nomeando `script.sha256`; args diferentes ⇒ block nomeando SÓ as chaves que mudaram;
`FORCE` registra `mismatch_forced` e libera; sem manifesto ⇒ `no_manifest`; PostToolUse vincula pelo
`tool_use_id` mesmo com lançamento mais antigo pendente; tool não-Workflow ⇒ `{}`; stdin malformado ⇒
`{}` rc 0; kill-switch. Unit: três registros distintos para ausente/null/vazio; canônico independe da
ordem; inline vence path; path ilegível registrado sem exceção; extração de run id; diff de chaves;
roundtrip índice/bind; `decide_pre` bloqueia só em mismatch e registra TODA chamada; último não
vinculado prefere a sessão.

## Limitações declaradas

- Vê a chamada da tool `Workflow`, não os `agent()` internos; não impede o harness de re-chavear o
  cache — impede o OPERADOR de retomar sobre entradas diferentes sem saber.
- Sem checkpoint dentro de `agent()` (limite do runner; W2 dá o checkpoint por fase em arquivo).
- Forma do run id por regex; resposta de outra versão da CLI ⇒ `bind` manual.
- Identidade da CLI não está no evento; não registrada.

## Perguntas abertas para os críticos

- OQ-1: o motivo do bloqueio é texto que o modelo lê — nomes de chaves de `args` são conteúdo do
  operador; há vetor de injeção aceitável? (hashes de valores, nunca valores; chaves truncadas a 8.)
- OQ-2: `latest_unbound_launch` como fallback do vínculo pode vincular ao manifesto errado quando
  dois lançamentos da mesma sessão ficam sem resposta; aceitar (manual `bind` corrige) ou exigir
  `tool_use_id`?
- OQ-3: o guard deve também comparar a REVISÃO do código (`code.head`)? Hoje só registra: retomar sobre
  código diferente é legítimo (WIP commitado) — mas «prompt idêntico com arquivos modificados não torna
  um resultado antigo válido» (ordem do Owner) aponta para W2 (checkpoint vinculado à revisão), não
  para bloqueio aqui.
- OQ-4: enforce por padrão (bloqueio) ou janela advisory primeiro, como FILE ASSIGNMENT (ADR-191)?
  Proposta: enforce — o caso bloqueado é exatamente o incidente medido e tem rota.

## Doutrina de estimativa (ADR-081)
Estimativas de esforço em tokens+sessões; prazo humano SÓ para `external_wait`; qualquer «semanas de
trabalho» de fonte externa é convertido antes de consolidar.
