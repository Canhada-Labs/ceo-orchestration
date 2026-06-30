---
description: Single-glance overview of current project state — /status
allowed-tools: Read, Glob, Grep, Bash
---

# /status — Framework state overview

Snapshot do estado atual do projeto. Lê o audit log, plans, lessons,
e imprime resumo em menos de 40 linhas.

## Arguments received

`/status $ARGUMENTS`

Se `$ARGUMENTS` for `--json`, emita JSON; caso contrário, formato
human-readable.

Se `$ARGUMENTS` incluir `--since <date>`, filtra eventos posteriores
a essa data.

## Procedure

### Step 1 — Active plan

Encontra o plano com `status: executing`:
```bash
grep -l "^status: executing$" .claude/plans/PLAN-*.md 2>/dev/null | head -1
```

Se existe: lê frontmatter (`id`, `title`, `sprint`). Calcula
aproximadamente % de progresso contando checkboxes ✅/❌ na seção
`## Success criteria` ou similar.

Se não existe: reporta último `status: done` como "último sprint
fechado".

### Step 2 — Recent spawns (últimas 5)

```bash
python3 .claude/scripts/audit-query.py since --hours 24 --action agent_spawn 2>/dev/null | tail -5
```

Para cada linha, extrai: timestamp, subagent_type, skill, resultado
(allow/block se disponível).

### Step 3 — Lessons escritas (últimas 24h)

```bash
python3 .claude/scripts/audit-query.py since --hours 24 --action lesson_write 2>/dev/null | wc -l
python3 .claude/scripts/audit-query.py since --hours 24 --action lesson_outcome 2>/dev/null | wc -l
```

Conta escritas + outcomes.

### Step 4 — Warnings ativos

```bash
# Audit log errors (breadcrumbs de falhas)
LINES=$(wc -l < ~/.claude/projects/ceo-orchestration/audit-log.errors 2>/dev/null || echo 0)

# Vetos disparados últimas 24h
python3 .claude/scripts/audit-query.py since --hours 24 --action veto_triggered 2>/dev/null | wc -l

# Injection flags advisory
python3 .claude/scripts/audit-query.py since --hours 24 --action injection_flag 2>/dev/null | wc -l
```

### Step 5 — CI status último commit

```bash
# Requires gh CLI
gh run list --branch main --limit 3 --json conclusion,name,createdAt 2>/dev/null
```

Se `gh` não instalado, reporta "gh CLI não instalado".

### Step 6 — Tokens spent (últimas 24h)

```bash
python3 .claude/scripts/audit-query.py tokens --since $(date -v-1d +%Y-%m-%d) 2>/dev/null | head -10
```

Reporta total input + output + por skill (top 3).

### Step 7 — Framework health

```bash
python3 .claude/scripts/audit-query.py health 2>/dev/null
```

Extrai verdict: `PASS`, `WARN`, `FAIL`, `NO_DATA`.

### Step 7b — Official Claude Code Analytics (O3, fail-soft)

Cross-check oficial da Anthropic (estimated cost por usuário/dia,
commits/PRs **feitos pelo Claude Code** = numerador "de graça" do §7,
accept/reject por ferramenta). **Snapshot-read only — NUNCA toca a
rede.** O snapshot é escrito separadamente pelo Owner com a chave Admin
provisionada (custódia: `THREAT-MODEL-WORKSHEET.md §3` + `rotation-log`).

```bash
python3 .claude/scripts/cc-analytics-pull.py --summary --json 2>/dev/null
```

- Se sair `{"available": false, "dormant": true, ...}` → reporta
  **"Analytics: dormant"** (built-but-dormant, OQ4 — sem chave Admin /
  sem snapshot). Esse é o estado normal; **nunca** trate como erro.
- Se sair um summary → mostra `estimated_cost` (oficial), `commits by
  CC`, `PRs by CC`, e `acceptance_rate` das ferramentas, lado a lado
  com a contagem de spawns derivada do audit-log (cross-check, não
  substituição). `cc-analytics-pull.py` é **fail-soft exit 0** sempre.

### Step 8 — Format output

Human-readable (default):

```
## /status — 2026-04-13 18:40 UTC

**Active plan:** PLAN-007 "Release v1.0.0" (sprint 7, 6/7 tasks done)
**Framework health:** PASS
**CI status:** ✅ main verde (último push: CI fix pyyaml, 2 min atrás)

### Recent spawns (últimas 5, 24h)
- 18:28 VP Engineering / architecture-decisions [allow]
- 18:35 Staff Backend / public-api-design [allow]
- 18:38 DevOps / devops-ci-cd [allow]
- 18:40 VP Engineering / architecture-decisions [allow]
- — nenhum bloqueio nas últimas 24h —

### Reflexion
- 3 lessons escritas últimas 24h
- 12 outcomes registrados (8 hit / 4 miss, hit_rate 66%)

### Tokens (últimas 24h)
- Total: 145,230 in + 89,410 out = 234,640
- Top skills: architecture-decisions (80k), public-api-design (60k), devops-ci-cd (35k)

### Warnings
- ⚠ 2 vetos disparados últimas 24h (ambos em check_bash_safety — rm -rf blocked)
- ✓ audit-log.errors: empty
- ✓ 0 injection flags

### Analytics (oficial, O3)
- Analytics: dormant (sem chave Admin / snapshot — built-but-dormant, OQ4)
  _ou, quando o snapshot existe:_
- Estimated cost (oficial): $4.19 · commits by CC: 12 · PRs by CC: 3 · acceptance 84%
```

JSON output (quando `--json`):

```json
{
  "active_plan": {"id": "PLAN-007", "title": "...", "progress_pct": 85},
  "health": "PASS",
  "ci": {"status": "green", "last_push_sha": "..."},
  "spawns_24h": [...],
  "lessons_24h": {"written": 3, "outcomes": 12, "hit_rate": 0.66},
  "tokens_24h": {"total_in": 145230, "total_out": 89410, "top_skills": [...]},
  "warnings": {"vetos_24h": 2, "audit_errors": 0, "injection_flags": 0},
  "analytics": {"available": false, "dormant": true, "reason": "no snapshot"}
}
```

`analytics` mirrors `cc-analytics-pull.py --summary --json`: when a
snapshot exists it is `{"available": true, "summary": {estimated_cost_usd,
commits_by_cc, prs_by_cc, tool_actions{acceptance_rate, ...}, ...}}`;
otherwise `{"available": false, "dormant": true}` (the OQ4 default).

## Fail-open

Se qualquer comando falhar, reporta a seção como "(indisponível)" e
continua com as outras. Nunca exit != 0.

## Exit codes

- 0 — sempre (advisory command)
