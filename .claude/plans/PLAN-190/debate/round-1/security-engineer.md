---
round: 1
archetype: Security Engineer
skill: security-and-auth
agent_persona: Principal Security Engineer (auth/crypto VETO holder)
generated_at: 2026-09-17
subject: PLAN-190 W1 — ledger de lançamento de Workflow + guard de retomada
materials_read: proposal.md · PLAN-190-autonomous-execution-recoverable.md · w1/p190-w1.patch (1.223 linhas) · w1/add-workflow-hook-registration.py · docs/research/s354-token-consumption-study/03-collector-audit.md · referência de autoria de Workflow (skill workflow-authoring, §Resume)
---

## Verdict

ADJUST

## Summary

- A W1 grava, ANTES do despacho, hash do script + `args` literais + revisão e recusa retomar sobre entradas diferentes. Superfícies certas (hook Pre/Post, lib, CLI) e a decisão mais valiosa do patch é o registro literal (ausente ≠ `null` ≠ `{}`).
- Forte: fail-open só em infraestrutura; manifesto atômico 0600; nenhum VALOR de `args` no motivo; kill-switch; predicado reutilizável na CLI; e2e como o harness invoca; distribuição pelos mecanismos existentes.
- Fraco: o predicado de bloqueio é mais LARGO que a classe demonstrada (o substrato sanciona retomar sobre script editado — só o prefixo alterado re-executa); o motivo ao modelo reabre o canal de NOMES que o PLAN-179 fechou; o fallback de vínculo só dispara quando é garantidamente errado; o manifesto pode não existir antes do despacho (git antes da escrita num hook de 5 s); e o patch não passa dois gates de corpus da própria bateria de land.

## Risks

- **R-SEC1 · HIGH** — Motivo de bloqueio lido pelo modelo com nomes de chaves de `args` sem sanitização e `resumeFromRunId` sem validação, interpolados num comando sugerido (patch:348-357). Mitigação: motivo counts-only + ids validados (Must-fix 1).
- **R-SEC2 · HIGH** — Bloqueio por hash de script contradiz o contrato do runner (editar o script e retomar é o rito documentado); o override é variável do PROCESSO, logo um falso bloqueio em sessão viva só tem rota reiniciando a sessão ⇒ o operador desliga o ledger e a classe volta. Mitigação: braço `script` advisory e medido, braço `args` enforce (Must-fix 2).
- **R-SEC3 · MEDIUM** — Vínculo por «último não vinculado» liga o run ao manifesto errado ⇒ `match` FALSO na retomada seguinte (garantia invertida) ou bloqueio falso (patch:388-393). Mitigação: Must-fix 3.
- **R-SEC4 · MEDIUM** — `git rev-parse` (3 s) + `git status` (5 s) correm ANTES de `write_manifest` num hook registrado com `timeout: 5`; no timeout o harness cancela e segue: o registro some em silêncio em repo grande com cache fria pós-reboot — o cenário do incidente. Mitigação: Must-fix 4.
- **R-SEC5 · MEDIUM** — `relaunch` não é exato para script inline (só hash) nem para `scriptPath` alterado; o plano prometia capturar o path persistido da resposta e o patch não captura. Mitigação: Must-fix 6.
- **R-SEC6 · MEDIUM** — O override (`mismatch_forced`) fica só num arquivo 0600 fora da cadeia HMAC: bypass de guard sem tamper-evidence. Mitigação: follow-up nomeado com gatilho (Nice 11); até lá `report` lista os forçados.
- **R-SEC7 · LOW** — `scriptPath` arbitrário é lido do disco (patch:153-162): oráculo hash+tamanho de qualquer arquivo legível e TOCTOU entre o hash e a leitura do harness. Mesmo UID — fora da fronteira declarada (CLAUDE.md §5). Mitigação: declarar na doc; sem cura na W1.
- **R-SEC8 · LOW** — `args` literais podem conter segredos; `show`/`relaunch` os imprimem e o texto vai ao transcript. Mitigação: Nice 7.

## Must-fix

1. **OQ-1 — motivo counts-only e ids validados.** Evidência: patch:348-357 (`d["key"]` e `run_id` entram via `%s`, inclusive dentro do comando `relaunch %s`); patch:215/225 (`resumeFromRunId` aceito como qualquer string não vazia); patch:831-839 (`bind` aceita `run_id` arbitrário — a porta pela qual um id maligno ganha manifesto vinculado e chega ao motivo); proposal:89 diz «chaves truncadas a 8», mas patch:349 trunca a LISTA de diffs, não o comprimento das chaves. Precedente: doutrina r22 do PLAN-179 — canal instruction-adjacent fecha por REMOÇÃO, não por enumeração (`SessionEnd.py:1069-1070`, `check_postcompact_reinject.py:517`, CLAUDE.md §5). Cura: (a) só é retomada se `_RUN_ID_RE.fullmatch(resumeFromRunId)`; senão registrar `resume_from_run_id_invalid` e seguir advisory; `cmd_bind` valida igual; (b) `format_block_reason` = id validado + `launch_id` (gerado pelo ledger) + contagens («script hash differs: yes/no; args top-level keys differing: N») + comandos fixos; NENHUM nome de chave — os nomes ficam em `guard.diff` no manifesto e saem por `ceo-launches.py show`; (c) o e2e de patch:639-645 vira controle NEGATIVO (chave `IGNORE PREVIOUS INSTRUCTIONS` nos args ⇒ ausente do motivo) + asserção dos nomes no manifesto em disco. ≈ 15k tokens.

2. **OQ-4 — dois braços, e alinhar o texto do plano.** Evidência: a referência de autoria do substrato (§Resume) diz que se retoma «after a pause, kill, or script edit» e que só o prefixo inalterado de `agent()` vem do cache — editar o script e retomar é o rito documentado; a perda só existe quando a PRIMEIRA chamada alterada é cedo, o que o hook não vê (patch:337-345 compara o hash inteiro). O override é variável de ambiente do processo (patch:374): o modelo não a define e o operador precisa reiniciar a sessão. O plano pré-registrou janela advisory para o guard (plan:232-233) e a proposta pula (proposal:50-51, 97-98) — o material assinado se contradiz. Cura: braço `args` (literal, ausente↔presente) BLOQUEIA por padrão — não há retomada legítima com `args` diferentes, até um timestamp passado por `args` tem de repetir para o cache; braço `script.sha256` ADVISORY por padrão — `additionalContext` counts-only no molde de `check_ledger_checkpoint.py:1175-1179`, manifesto `mismatch_advised`, `report` imprime a tabela would-block; `CEO_WORKFLOW_RESUME_STRICT=1` liga o bloqueio do braço script; flip por cerimônia após ≥ 20 sessões ou 30 d (`external_wait`); regra de parada do plano reescrita para esse braço. ≈ 20k tokens.

3. **OQ-2 — fallback só sem `tool_use_id`, e nunca entre sessões.** Evidência: patch:388-393 dispara o fallback também quando há `tool_use_id` e nenhum manifesto casa — i.e. exatamente quando o lançamento correto NÃO foi registrado, logo o vínculo é garantidamente errado; patch:293-299 com `session_id` None casa QUALQUER sessão; patch:1207-1213 consagra isso. `tool_use_id` existe neste harness (lido por `check_output_secrets.py`, `_lib/tool_lifecycle.py`, `_lib/adapters/claude.py`). Cura: com `tool_use_id` presente e sem manifesto ⇒ NÃO vincular; gravar `{"kind":"orphan","run_id":…,"tool_use_id":…,"session_id":…}` (o run id fica recuperável para `bind`); fallback «último não vinculado» só sem `tool_use_id` E com `session_id` igual (nunca None); linha `bind` ganha `by: tool_use_id|latest_unbound|manual` para `report` contar; teste do fallback reescrito. ≈ 10k tokens.

4. **Manifesto ANTES do despacho, de verdade.** Evidência: patch:363 (`build_manifest`) roda git com timeouts 3 s (patch:174) + 5 s (patch:177) antes de `write_manifest` (patch:379); registração `timeout: 5` (patch:892); SC W1 «100 % dos lançamentos com manifesto ANTES do despacho» (plan:220-221). Cura: `write_manifest` primeiro com `code: {"head": null, "dirty": null, "status": "pending"}`; git com 1 s e `--untracked-files=no`; reescrita atômica; teste com `git` substituído por stub que dorme além do timeout ⇒ manifesto existe. ≈ 8k tokens.

5. **Gates de corpus da bateria de land que o patch NÃO passa.** (a) Higiene: `class ArgsAndScript(unittest.TestCase)` (patch:1119) e `class CompareAndIndex(unittest.TestCase)` (patch:1155) em `tests/unit/` — raiz varrida (`check-test-env-hygiene.py:65`, «tests»), regra 2 (`:17-19`), hard-fail (`validate.yml:816`); mesma classe do S321 (CLAUDE.md §4). Cura: subclasse `TestEnvContext` (`_lib/testing.py`). (b) Contagens: proposal:63-64 diz que 59→60 e 71→72 «entram no mesmo pacote», mas o patch de 9 paths não toca `CLAUDE.md:53` (59 / 48 wired / 50 registrations / 71) nem `docs/ARCHITECTURE.md:47` (71); `verify-counts.sh:621,644-650,662` parseia esses tokens contra o disco; o LAND exige `touched − scope = ∅`. Cura: hunks de contagem NO patch (60 / 49 / 52 / 72), escopo declarado com 11 paths (os dois docs são não-canônicos: oráculo `--is-canonical` ⇒ 0), e `verify-counts.sh` + `check-test-env-hygiene.py` na bateria da sombra. ≈ 5k tokens.

6. **`relaunch` exato — ou promessa estreitada.** Evidência: patch:792-793 imprime para inline só o hash e remete a `<session>/workflows/<run>.json`, que o harness escreve ao TÉRMINO (plan:39) — morte de processo não termina; plan:103-104 promete gravar o `scriptPath` persistido que a resposta traz, e a referência confirma que toda invocação persiste o script e devolve o path no resultado; `decide_post` (patch:383-396) só extrai o run id. O SC «relaunch reproduz a chamada exata» (plan:221) é falso para inline e para `scriptPath` alterado. Cura: em `decide_post`, extrair o path persistido (regex ancorada no diretório da sessão, nunca um path arbitrário), gravar `script.persisted_path`, `persisted_sha256` e `persisted_matches_inline` — essa igualdade byte a byte inline↔persistido é a MEDIÇÃO que decide se o braço script pode um dia ser enforce (hoje não provada: um byte de diferença bloquearia o rito canônico 100 % das vezes); `relaunch` imprime o path persistido. Se a forma da resposta não for estável, estreitar o SC para «reproduz hash + args; texto via path persistido quando visível». ≈ 12k tokens.

7. **Distribuição: declarar a condição e testá-la.** Evidência: `upgrade.sh:3261-3323` — cerimônia desconhecida ⇒ registrações WITHHELD (`PARTIAL`), só settings comuns; `install.sh:3412` grava `ceremony` no install-state; o merge H8 chaveia por basename (`upgrade.sh:2875`) ⇒ `check_workflow_launch.py` é apendado quando ausente. A claim «sem passo manual» (plan:117-119) vale SÓ para adopter com `request.ceremony` gravada. Cura: plano/doc com a condição; W6 asserta as duas pernas (com cerimônia gravada; sem, via `--ceremony`); AC: ler `request.ceremony` no install-state do consumidor antes do primeiro upgrade. ≈ 6k tokens.

Total dos Must-fix: ≈ 80-140k tokens, 1 sessão na sombra + 1-2 rodadas de rail; a janela advisory do braço script é `external_wait` (≥ 20 sessões ou 30 d), sem custo de agente.

## Nice-to-have

1. **OQ-3:** NÃO comparar `code.head` no guard (retomar sobre WIP commitado é legítimo; só prompt+opts chaveiam o cache) — mas `relaunch` deve avisar quando o `HEAD` atual difere do registrado (já imprime o registrado, patch:802-803).
2. Identidade sem hash: `name` e `scriptPath` ilegível (patch:163-166) dão `sha256` None dos dois lados e casam mesmo com `name` diferente; comparar a tupla `(source, name, path)` quando o hash falta.
3. `extract_run_id` pega o PRIMEIRO token (patch:198): se a resposta ecoar o run retomado antes do novo, vincula ao antigo; preferir o primeiro token ≠ `resume_from_run_id` do manifesto pendente; medir numa retomada real.
4. `ledger_dir` cria o pai com `parents=True` (patch:79): nasce 0755 pelo umask se o ledger for o primeiro escritor do state dir (que hospeda a chave HMAC); usar `runtime_paths.ensure_state_dir()` como `audit_hmac.py:404`.
5. Evento desconhecido cai em `decide_pre` (patch:463-469): `elif hook_event == "PreToolUse"` explícito, resto `{}`.
6. `_ARGS_MAX_BYTES` (patch:142-143) corta em caracteres e produz canônico INVÁLIDO sem marca; `relaunch` o imprimiria como «EXATO»; gravar `truncated: true` e `relaunch` recusa imprimir como exato.
7. Segredos em `args`: `show`/`relaunch` redigem valores de chaves `(?i)token|secret|password|key` salvo `--reveal`; doc: «não passe segredos em args».
8. Doc: `CEO_WORKFLOW_RESUME_FORCE`/`CEO_WORKFLOW_LEDGER` são do ambiente que INICIA a sessão (ou `env` do `settings.local.json`); o modelo não os define — manter assim; o motivo não deve induzir tentativas de contorno.
9. `docs/workflow-recovery.md` não viaja ao consumidor: só há duas rotas de docs (`scripts/delivery-routes.tsv:24-25`); ou uma rota nova (domínio inerte `docs/<n>.md`) ou o rito inteiro no `--help` da CLI, que viaja por `.claude/scripts` (`_framework_manifest_set.sh:180`).
10. Após `mismatch_forced` cujo PostToolUse devolve o mesmo run id, o último `bind` vence (patch:275-283) e a baseline do run passa a ser a forçada — documentar, ou `bind` grava `supersedes`.
11. Follow-up nomeado com gatilho: ação `workflow_resume_forced` na cerimônia do audit (`_KNOWN_ACTIONS`), para o bypass entrar na cadeia HMAC.
12. e2e com `scriptPath` alterado no disco (o incidente literal), além do inline.

## Unseen

1. O substrato SANCIONA retomar sobre script editado (prefixo cacheado): plano e proposta tratam toda mudança de script como a classe de perda; o guard é uma sobre-aproximação e deve nascer medindo (base do Must-fix 2).
2. A resposta da tool devolve o `scriptPath` persistido em toda invocação — o plano prometeu capturá-lo, o patch não o faz; e a igualdade inline↔persistido nunca foi medida (Must-fix 6).
3. O motivo/advisory ao modelo é o mesmo canal de NOMES que o PLAN-179 fechou por remoção (Must-fix 1).
4. O fallback de vínculo só dispara quando é garantidamente errado se `tool_use_id` está presente (Must-fix 3).
5. O override não é tamper-evident (R-SEC6).
6. Dois gates de corpus da bateria de land estão vermelhos no patch atual (Must-fix 5).
7. `docs/` não é entregue ao consumidor (Nice 9) e adopter sem cerimônia gravada não recebe o hook (Must-fix 7).

## What I would NOT change

- Persistir no hook (PreToolUse), não no script do consumidor: é a única superfície que vê `tool_input` inteiro e sobrevive à morte do processo.
- `args` LITERAL (ausente ≠ `null` ≠ `{}`), JSON canônico por ordem de chave; hashes de valores no diff, nunca valores.
- Fail-open só em infraestrutura, kill-switch, e nenhum evento de auditoria nesta wave (cerimônia do dono do audit) — desde que o follow-up fique nomeado.
- Escrita atômica 0600 + índice append-only; `FileLock` best-effort (a API bate com `_lib/filelock.py:27,117-128`).
- Override por variável de ambiente do processo: o modelo NÃO consegue se auto-desbloquear — manter; só documentar.
- Distribuição pelos mecanismos existentes: enumeração de `.claude/hooks` e `.claude/scripts` (`_framework_manifest_set.sh:179-180`), template base + `user` derivado sem subtração, derivador idempotente e anchor-exact.
- Não comparar revisão de código no guard (OQ-3); registrar sim.
