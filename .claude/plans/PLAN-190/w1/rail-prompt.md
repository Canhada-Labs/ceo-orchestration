# Pair-rail prompt — PLAN-190 W1 (Codex, read-only, cold)

Você é o revisor cruzado (V2 da cascata de verificação — PROTOCOL.md §Verification cascade).
Revise o patch `.claude/plans/PLAN-190/w1/p190-w1.patch` (mudança proposta a ESTE repositório,
ainda não aplicada na árvore; branch `p190-w1`). Contexto: `.claude/plans/PLAN-190-autonomous-execution-recoverable.md`
(wave W1) e `.claude/plans/PLAN-190/debate/round-1/proposal.md`.

O patch acrescenta: `.claude/hooks/_lib/launch_ledger.py` (biblioteca), `.claude/hooks/check_workflow_launch.py`
(hook PreToolUse/PostToolUse na tool `Workflow`), `.claude/scripts/ceo-launches.py` (CLI), dois testes,
`docs/workflow-recovery.md`, duas registrações em `.claude/settings.json` e em
`templates/settings/settings.base.json` (o `settings.user.json` é derivado por
`.claude/scripts/gen-settings-user-template.py`), e bumps de contagem em 10 docs.

Critérios: correção (o guard bloqueia SÓ retomada com script/args diferentes do manifesto vinculado;
`args` ausente ≠ `null`; fail-open em infraestrutura; nunca exit ≠ 0), segurança (o motivo de bloqueio
vai ao modelo — carrega nomes de chaves de `args` e hashes, nunca valores; escrita atômica 0600 sob
o diretório de estado do projeto; sem leitura de transcripts), regressões (parity dos templates,
`gen-settings-user-template.py --check`, `verify-counts.sh`, `check-active-hooks-executable.py`),
Python ≥ 3.9 stdlib-only, isolamento de testes (`TestEnvContext`), e distribuição (o hook chega aos
consumidores pela enumeração de `.claude/hooks/` + template base no `upgrade.sh`).

Saída: lista de achados com severidade `P0 | P1 | P2`, cada um com `arquivo:linha` no patch e cura
concreta; ao final UMA linha `VERDICT: GO | GO-WITH-CONDITIONS | NO-GO` seguida das condições, se
houver. Não proponha JEV nem capacidade não aprovada do fornecedor. Não altere arquivos.
