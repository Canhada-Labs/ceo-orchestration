# GLOSSARY — Dicionário de termos do ceo-orchestration

> **EN (fonte canônica):** [GLOSSARY.md](GLOSSARY.md).

Termos que aparecem em `CLAUDE.md`, `PROTOCOL.md`, logs, plans, etc.

## Conceitos centrais

**CEO** — O papel que o Claude assume quando o framework está ativo.
Não é um agente separado; é o **Claude principal** orquestrando um
time. Pensa em "maestro" mais que "executor".

**Owner** — Você. O humano que toma a decisão final. O CEO reporta
pro Owner. Owner pode demitir CEO (reescrever a persona se ela falhar
3 vezes).

**Agent / Subagent** — Um Claude spawnado pelo CEO com uma persona +
skill específicas. Age em paralelo ou sequencial. Retorna com output.

**Persona** — Perfil de um agente (nome, background, mantra, red
flags, anti-patterns). Fica em `.claude/team.md` ou
`<domain>/team-personas.md`.

**Skill** — Manual técnico. Checklist, não "vibe". Fica em
`.claude/skills/<tier>/<nome>/SKILL.md`. Cada agente tem 1-2 skills.

**Archetype** — Papel genérico (ex: "VP Engineering", "Staff
Security"). Personas concretas instanciam archetypes.

**Squad** — Conjunto coeso de personas + skills + pitfalls + task
chains para um domínio específico (fintech, lgpd-heavy-saas,
trading-hft).

## Governança

**PROTOCOL** — O contrato de governança. Vive em `PROTOCOL.md`. Define
gates (GATE 1 ler, GATE 2 ativar, GATE 3 planejar), vetos, 3-strike.

**Gate (1, 2, 3)** — Etapas obrigatórias no início de toda sessão.
Gate 1 = ler docs. Gate 2 = invocar skill ceo-orchestration + ler
team. Gate 3 = planejar antes de código.

**Plan** — Arquivo `.claude/plans/PLAN-NNN-slug.md` com frontmatter
(id, title, status, owner). Planos sobrevivem sessões.

**Lifecycle** — Estados do plan: `draft → reviewed → executing →
done` (ou `abandoned`). Transições governadas por hook.

**ADR** — Architecture Decision Record. Arquivo `.claude/adr/ADR-NNN`
que registra decisões arquiteturais irreversíveis. Tem Status,
Context, Options, Decision, Consequences, Blast Radius.

**Blast radius** — Escopo do impacto de uma mudança. L1 = 1 arquivo,
L5 = dezenas de módulos.

## Debate

**/debate** — Slash command para rodar debate multi-especialista num
plano. Entry forms: `start`, `round2`, `round3`, `status`.

**Round** — Iteração de debate. Cada round spawna 3 agentes
(archetypes do time), cada um critica o plano do ângulo da sua skill.

**Consensus finding** — Risco flagado por 2+ agentes. Se consensus, o
CEO **tem que** ajustar o plano (não é negociável).

**Round verdict** — Ao fim do round: `PROCEED` (seguir), `RUN-
ANOTHER-ROUND` (mais 1 rodada), `ESCALATE` (não consegue resolver
sozinho, chama Owner).

## Vetos e aprovações

**VETO** — Hard block. Se quem tem veto diz "não", não shippa.
Universais: Staff Code Reviewer (qualquer merge), Staff Security
Engineer (auth/input/token).

**3-strike policy** — Agente com 3 erros factuais consecutivos é
"demitido" — persona reescrita com novo nome. Strikes rastreados em
`.claude/agent-metrics.md`.

## Hooks (mecânica)

**Hook** — Script Python em `.claude/hooks/` que roda em pontos
específicos da sessão (PreToolUse, PostToolUse). Bloqueia ações
anti-pattern.

**PreToolUse** — Hook que roda ANTES da ferramenta executar. Pode
bloquear (`{"decision":"block"}`).

**PostToolUse** — Hook que roda DEPOIS. Geralmente silent observer
(ex: `audit_log` gravando o que aconteceu).

**Fail-open** — Regra: hook nunca bloqueia usuário por bug próprio.
Parse error, timeout, arquivo faltando → emite `allow`. Segurança
via garantia de que hook NUNCA fica no caminho crítico.

**Adapter Layer** — Camada de tradução entre shape específica do IDE
(Claude Code, Gemini CLI) e NormalizedEvent interno. V1.0 é 100%
Claude. Gemini é stub.

## Memória e audit

**Auto-memory** — Arquivos em `~/.claude/projects/<slug>/memory/` que
o Claude auto-carrega toda sessão. 4 tipos: user, feedback, project,
reference.

**Audit log** — JSONL em `~/.claude/projects/<slug>/audit-log.jsonl`.
Append-only. Redactado de secrets. Consultado via `audit-query.py`.

**Event schema v2** — Formato atual do audit log. Actions: agent_spawn,
debate_event, plan_transition, veto_triggered, benchmark_run,
lesson_write, injection_flag, lesson_outcome.

**Redaction** — Processo que remove secrets/PII do texto antes de
logar. Implementado em `_lib/redact.py`.

## Reflexion

**Reflexion** — Sistema que aprende com erros do benchmark. Escreve
lições ao falhar. Lições injetadas em prompts futuros.

**Lesson** — Arquivo JSON em `lessons/<id>.json` com
`remember_this`, `scope_tags`, `archetype`, `hit_count`, `miss_count`.

**Hit / Miss** — Outcome de uma lesson aplicada. Hit = cenário passou.
Miss = falhou. Registrado por `record_outcome()`.

**Top-K** — Cap de quantas lessons são consideradas por spawn (K=50
hard ceiling em V1.0).

**Pruning** — Remoção de lições com `hit_rate < 0.3` após `n >= 5`.
V1.0 é só dry-run; enforcement em Sprint 7+ depois de FPR medido.

## CI/CD e release

**Governance check** — Workflow `.github/workflows/validate.yml`.
Verifica estrutura de skills, team, plans, CODEOWNERS.

**Coverage gate** — Workflow `.github/workflows/coverage.yml`. V1.0
enforcing at 86% (`--fail-under=86`).

**Smoke install** — Workflow `smoke-install.yml`. Simula install em
repo limpo.

**Release gate** — Workflow `release.yml`. Fires on tag push. 7 gates
incluindo smoke install, SPEC version match, CHANGELOG.

**SemVer** — Major.Minor.Patch. V1.0.0-rc.1 = release candidate 1.

## Papéis (archetypes principais)

**VP Engineering** — Arquitetura, ADRs, revisão de mudanças 3+ módulos.

**VP Product** — Features, conversão, revenue.

**VP Operations** — Deploys, monitoring, SRE.

**Staff Code Reviewer** — VETO de merge.

**Staff Security Engineer** — VETO de auth/token/input. (Também existe
Staff Quant em fintech, Staff Privacy em healthcare, etc.)

**Principal Performance Engineer** — Latency, memory, GC.

**Principal Data Engineer** — Schema, migrations, RLS.

**Principal QA Architect** — Tests, regression, edge cases.

**Chaos & Resilience Engineer** — Circuit breakers, failure modes.

**Growth Engineer** — Funnel, onboarding.

## Siglas rápidas

- **L1-L5** — blast radius levels
- **ADR** — Architecture Decision Record
- **RLS** — Row-Level Security (postgres)
- **RC** — Release Candidate
- **FPR** — False Positive Rate
- **PR** — Pull Request
- **SHA** — git commit hash (prefixo 7 chars = enough)
- **IPC** — Inter-Process Communication
- **WCAG** — Web Content Accessibility Guidelines
