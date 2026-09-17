# w1-approved — sentinel da W1 do PLAN-190 (DRAFT — assinar como w1-approved.md)

> Assinatura em um passo: `! bash .claude/plans/PLAN-190/w1/OWNER-190-W1-SIGN.sh`
> (preenche Anchor-SHA, Patch-sha256 e Data, assina, aplica o patch, roda a bateria, stageia o
> conjunto EXATO e commita; `--dry-run` ensaia sem assinar nem commitar). Push é decisão sua.

Plan: PLAN-190
Wave: W1 — ledger de lançamento de Workflow + guard de retomada
Patch: .claude/plans/PLAN-190/w1/p190-w1.patch
Patch-sha256: <PREENCHIDO-PELO-SIGN>
Anchor-SHA: <HEAD-NO-MOMENTO-DA-ASSINATURA>
Data: <AAAA-MM-DD>

## Ratificação (Owner, S354)

Ordem verbatim (17/09/2026): «Quero corrigir o ceo-orchestration para que a execução autônoma seja
utilizável nos repositórios consumidores. […] Tornar lançamentos e progresso recuperáveis. Persistir
antes do despacho: identificação da execução e da fase; versão/hash do script; argumentos exatos,
preservando inclusive campos ausentes; opções efetivas relevantes; revisões de código/spec […]. Não
reconstruir argumentos de memória.»

O que esta wave entrega, e nada além: um hook na tool `Workflow` que grava o manifesto do lançamento
ANTES do despacho (sha256 + snapshot dos bytes do script, `args` literal com ausente ≠ null e sem
truncamento, `resumeFromRunId`; a revisão git do `cwd` entra DEPOIS, com orçamento de 1,2 s) e
vincula o run id devolvido (por `tool_use_id`, senão só quando há um único lançamento pendente na
sessão; o resto vira `orphan`); um guard que BLOQUEIA a retomada de um run sobre `args` diferentes do
manifesto vinculado, com motivo só de contagens (a lista de chaves fica no manifesto), trata script
diferente como advisory por padrão e hash indisponível como inconclusivo; as rotas: `ceo-launches.py
relaunch <run>` imprime a chamada exata a partir do snapshot, `ceo-launches.py force <run> --reason`
libera UMA vez com o motivo registrado e anunciado, `CEO_WORKFLOW_RESUME_FORCE=1` /
`CEO_WORKFLOW_RESUME_GUARD=0` / `CEO_WORKFLOW_SCRIPT_GUARD=enforce` / `CEO_WORKFLOW_LEDGER=0` no
ambiente do harness; a CLI de recuperação; testes; o documento do rito; as registrações no settings do
framework e no template base entregue aos consumidores (o `user` deriva por subtração, NÃO exclui este
hook e o nomeia em `blocking_inclusions` com a rota); os inventários derivados (mapa comando→skill→hook,
inventário de variáveis de ambiente, pinos do teste de paridade 52/49) e os bumps de contagem que o
`verify-counts.sh` exige (hooks 59→60, ligados 48→49, registrações 50→52, `_lib` 71→72). Debate r1
(3 críticos, ADJUST ×3, consenso PROCEED como design-coherent) e rail Codex (r1 NO-GO com 7 achados,
todos curados; r2 sobre os bytes finais) registrados em `PLAN-190/debate/round-1/` e `PLAN-190/w1/`.

## Scope

- `.claude/hooks/_lib/launch_ledger.py` — biblioteca (canônico, novo)
- `.claude/hooks/check_workflow_launch.py` — hook PreToolUse/PostToolUse `Workflow` (canônico, novo)
- `.claude/settings.json` — 2 registrações `matcher: "Workflow"` (canônico)
- `templates/settings/settings.base.json` — as mesmas 2 registrações (canônico)
- `templates/settings/settings.user.json` — regenerado por `gen-settings-user-template.py --write`, com o hook em `_derivation.blocking_inclusions` e sua rota (canônico, derivado)
- `.claude/scripts/ceo-launches.py` — CLI `list · show · relaunch · check · force · bind · orphans · report` (novo)
- `.claude/scripts/env-inventory.json` — regenerado por `env-inventory-check.py --generate` (4 variáveis novas + drift pré-existente)
- `.claude/hooks/tests/test_check_workflow_launch.py` — 25 testes e2e (novo)
- `.claude/hooks/tests/test_template_dogfood_parity.py` — pinos 50/47 → 52/49 (relação 52 == 49 + 1 + 2)
- `tests/unit/test_launch_ledger.py` — 13 testes unitários (novo)
- `docs/workflow-recovery.md` — rito de recuperação, guard dividido, rotas e limitações declaradas (novo)
- `docs/COMMAND-SKILL-HOOK-MAP.md` — regenerado por `gen-command-skill-hook-map.py --write`
- `CHANGELOG.md` — cabeçalho de inventário (`_lib` 71→72)
- `CLAUDE.md` — §1 contagens (60 hooks / 49 ligados / 52 registrações / 72 `_lib`)
- `INSTALL.md` — contagens
- `README.md` — contagens
- `README.pt-BR.md` — contagens
- `docs/ARCHITECTURE.md` — contagens e árvore
- `docs/README.md` — contagens
- `docs/GUIA-COMPLETO.md` — contagens
- `docs/CTO-GUIDE.md` — contagens
- `npm/README.md` — contagens

## Evidência (sombra `wt-p190-w1`, branch `p190-w1`, CLI 2.1.274)

    python3 -m pytest .claude/hooks/tests/test_check_workflow_launch.py tests/unit/test_launch_ledger.py \
      .claude/hooks/tests/test_template_dogfood_parity.py .claude/scripts/tests/test_gen_command_skill_hook_map.py -q
      -> 73 passed
    python3 .claude/scripts/env-inventory-check.py --check                -> ENV-DRIFT: 0
    python3 .claude/scripts/gen-command-skill-hook-map.py --check        -> in sync
    python3 .claude/scripts/check-test-env-hygiene.py            -> OK (0 violações novas)
    python3 .claude/scripts/gen-settings-user-template.py --check -> OK (template user bate com a derivação)
    python3 .claude/scripts/check-active-hooks-executable.py     -> OK: 95 referências presentes e executáveis
    bash .claude/scripts/local/verify-counts.sh                  -> no drift detected
    bash .claude/scripts/check-contamination.sh                  -> ✓ (2 regras)
    git diff --numstat -- .claude/settings.json templates/settings/  -> só adições (24 linhas em cada)

Registrações geradas pelo derivador idempotente `add-workflow-hook-registration.py`; contagens pelo
derivador `bump-counts.py` (mesmas regexes do gate). Debate r1 e rail Codex registrados em
`.claude/plans/PLAN-190/debate/round-1/` e `.claude/plans/PLAN-190/w1/rail-round-*.md`.

## Consequência DECLARADA

A partir deste commit, TODO lançamento da tool `Workflow` neste repo e nos consumidores que fizerem
`upgrade.sh` deixa um manifesto em `<state-dir>/launches/` e uma retomada sobre entradas diferentes é
recusada por padrão. O hook não emite evento de auditoria (registrar a ação em `_KNOWN_ACTIONS` +
SPEC é cerimônia do dono do audit — follow-up nomeado no plano); os manifestos são o registro.

## Residual

O guard vê a chamada da tool `Workflow`, não os `agent()` internos, e não impede o harness de
re-chavear o cache de resultados — impede o OPERADOR de retomar sobre entradas diferentes sem saber.
Não há checkpoint dentro de um `agent()` (limite do runner; W2 dá o checkpoint por fase em arquivo).
O run id é extraído da resposta por forma (`wf_<hex8>[-<hex>]`); outra versão da CLI ⇒ `bind` manual.
