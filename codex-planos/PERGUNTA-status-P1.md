# PISTA 1 — Onda 1A: decisão de ciclo de vida pendente

2026-11-01. Branch `tracks/ceo-w1-staleness-plans-reviewmd`.

Implementado: `REVIEW.md` e `.github/pull_request_template.md`; o PLAN-195
recebeu `executing_at: 2026-10-02`, data da W0 em `b2ab8805`. O commit
`6ee8c218` confirma que a execução começou na W0 e que o status foi corrigido
depois. Os sete `related_commits` dos PLAN-194/195 resolvem para commits
existentes; o PLAN-194 já está `done`.

Validação após a alteração, em palco descartável com temporários em tmpfs:

- `/var/tmp/pista-22/venv/bin/python3 -m pytest .claude/scripts/tests/test_check_staleness.py -v`:
  `============================== 10 passed in 0.20s ==============================`.
  Inclui `TestRealRepo::test_real_repo_no_unhealthy_today` e os nove casos de
  `TestStaleness`. Nenhum caso novo; mutantes não se aplicam à alteração documental.
- `bash .claude/scripts/validate-governance.sh`: `Errors:   0`,
  `Warnings: 65`, `PASS: Governance files validated.`
- Higiene: `OK: test-env hygiene clean (337 flagged files, all allowlisted).`
  Ceremony lint: `blocking não-waivado: 0`. Contagens:
  `(no drift detected — all doc counts match the live source)`.

**Ainda não é PRONTO:** `check-staleness.py` mantém 16 alertas
(11 `degraded`, 5 `stranded`, zero `unhealthy`). Os planos registram pendências
reais, incluindo gates do Owner; atualizar `created` ou declarar `done` apenas
para silenciar o verificador não corresponde ao histórico. Nenhuma regra ou
asserção do verificador foi relaxada.

**Proposta enviada ao Owner:** consolidar todo o escopo pendente dos planos
alertados em um novo plano de backlog, preservando suas condições e vínculos;
somente então marcar os anteriores como `superseded` com `superseded_by`,
conforme PLAN-SCHEMA §11. Alternativa: preservar os estados e aceitar os
alertas até a execução. A decisão ainda não foi recebida.

Pré-checagem: pendente quanto ao objetivo de zero alertas. `autobahnctl
pre-juiz --delta --json` não está disponível (`command not found`). Consulta
aos PRs indisponível: `gh` sem autenticação. O roteiro de `/var/tmp/pista-1`
continua apontando para a tarefa antiga M16-01; não há próxima fatia deste
projeto liberada nele. `PISTA-1.md` permanece para a retomada da tarefa 1.
