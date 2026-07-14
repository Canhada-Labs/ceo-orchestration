# Guia Completo — ceo-orchestration

> **EN (fonte canônica):** [GUIA-COMPLETO.md](GUIA-COMPLETO.md).
>
> **Leia isso primeiro.** Este documento é o ponto de entrada único.
> Ele fala com dois públicos ao mesmo tempo: quem NÃO é dev (primeiras
> duas seções) e quem É dev (resto). Cada seção marca o tempo estimado
> de leitura — pule o que não for pra você.

## Mapa deste documento

| Seção | Para quem | Tempo |
|-------|-----------|-------|
| [1. Em 2 minutos](#1-em-2-minutos-não-dev) | Não-dev, PM, founder, cliente | 2 min |
| [2. Em 10 minutos](#2-em-10-minutos-dev) | Dev que nunca viu o framework | 10 min |
| [3. O que é, o que não é](#3-o-que-é-o-que-não-é) | Todos | 5 min |
| [4. Quando usar, quando não usar](#4-quando-usar-quando-não-usar) | Dev | 3 min |
| [5. Instalar em projeto NOVO](#5-instalar-em-projeto-novo) | Dev | 10 min |
| [6. Instalar em projeto EXISTENTE](#6-instalar-em-projeto-existente) | Dev | 20 min |
| [7. Primeiros 10 minutos pós-install](#7-primeiros-10-minutos-pós-install) | Dev | 10 min |
| [8. Uso diário — o loop básico](#8-uso-diário--o-loop-básico) | Todos | 10 min |
| [9. Comandos que você vai usar](#9-comandos-que-você-vai-usar) | Todos | 5 min |
| [10. Como explicar pro time](#10-como-explicar-pro-time) | Líder técnico | 5 min |
| [11. Troubleshooting](#11-troubleshooting) | Dev | consulta |
| [12. Limitações honestas](#12-limitações-honestas) | Todos | 3 min |
| [13. Referências](#13-referências) | Dev | consulta |

---

## 1. Em 2 minutos (não-dev)

### O problema
O Claude Code (ou qualquer LLM de código) sozinho é um freelancer
genial mas generalista. Ele escreve código rápido, mas:

- Pula etapas de segurança porque "ninguém pediu"
- Inventa números e nomes de função que não existem
- Faz 80% do pedido e declara "pronto"
- Não deixa trilha pra você auditar depois

### O que o framework faz
Transforma esse freelancer em **um time estruturado**:

- Um **CEO** (o próprio Claude, em modo protocolo) recebe o pedido
- **VPs** decidem estratégia (Engenharia, Produto, Operações)
- **Especialistas** executam com checklist do domínio
- **Vetos automáticos** bloqueiam merge sem code review, sem teste, ou
  com problema de segurança
- Tudo fica num **audit log** — você entende DEPOIS por que o CEO
  tomou cada decisão

### Você, não-dev, ganha o quê?
- Entende o que vai ser feito antes de ser feito (plano em português)
- Pode perguntar "cadê o status?" e ter resposta objetiva (`/status`)
- Seu time para de entregar feature com bug de segurança óbvio
- Não precisa aprender termos técnicos — o CEO traduz o pedido

### Analogia
> É a diferença entre contratar um **freelancer** (rápido, sem
> processo) e contratar uma **agência** (gerente de conta, equipe
> especializada, revisão antes de entregar). O framework é a agência.

Pronto. Você já sabe o suficiente pra decidir se quer seu time usando
isso. Se a resposta é sim, passa pra próxima seção — ou manda um dev
ler o resto.

---

## 2. Em 10 minutos (dev)

### O que você ganha tecnicamente

1. **Skills como checklists mecânicos.** 160 skills em
   `.claude/skills/core`, `.claude/skills/frontend`, e
   `.claude/skills/domains/<dominio>`. Cada skill é um `SKILL.md` com
   regras verificáveis ("use decimal, não float", "valide CSRF",
   "exige teste de unidade para cada boundary"). Não é "use bom senso".

2. **Spawn Protocol.** Todo agent spawn carrega
   `## AGENT PROFILE` + `## SKILL CONTENT` + `## FILE ASSIGNMENT`
   antes de escrever a primeira linha. Um hook Python
   (`check_agent_spawn.py`) bloqueia spawns que não seguem o formato.
   Resultado: você não recebe mais "agent genérico com nome bonito".

3. **Hooks mecânicos em Python.** 31 hooks rodam no `PreToolUse` e
   `PostToolUse` do Claude Code, incluindo:
   - `check_agent_spawn` — persona+skill obrigatórios
   - `check_bash_safety` — bloqueia `rm -rf /`, `git push --force main`, etc
   - `check_canonical_edit` — edits em `SKILL.md` / `team.md` exigem sentinel assinado
   - `check_plan_edit` — plano não muda sem aprovação
   - `check_read_injection` — detecta prompt injection em arquivos lidos
   - `audit_log` — grava tudo em JSONL

4. **Debate protocol.** Pra task L3+ (3+ módulos, schema, auth),
   `/debate start PLAN-NNN` spawna N especialistas em paralelo
   critiquing o plano. Se 2+ apontam mesmo risco, plano É ajustado
   (não é sugestão).

5. **Audit log.** Tudo em
   `~/.claude/projects/<slug>/audit-log.jsonl`. `audit-query.py` tem
   29 subcomandos (summary, by-skill, debate, tokens, health, etc).

6. **Vetos obrigatórios.** Staff Code Reviewer veta merge sem
   `tsc/mypy/go vet` limpo. Staff Security veta mudanças de auth sem
   revisão. Domínio tem vetos próprios (fintech: Staff Quant veta uso
   de float em cálculo financeiro).

7. **SPEC v1.** Contratos schema-validados em `SPEC/v1/` (state-stores,
   adapters, normalized_envelope, judge-payload, scratchpad, session-graph,
   squad-manifest, skill-index, skill-proposals, etc). SemVer enforced.

8. **9929 testes.** `pytest .claude/hooks/tests .claude/scripts/tests`
   roda em ~30s e tem cobertura ≥86%. Você pode confiar que os hooks
   não vão te trollar.

### Como ele muda seu fluxo

Antes:
```
você escreve prompt elaborado → Claude interpreta como quer →
entrega código → você revisa → pede mudança → Claude ajusta →
você dá merge
```

Depois:
```
você escreve pedido natural → CEO vira plano P0-P4 → você aprova →
CEO spawna especialista(s) com skill/persona/files → especialista
entrega código que já passou no checklist do skill → Code Reviewer
veta ou aprova → você dá merge
```

A sensação é que ficou "mais burocrático", mas o tempo total cai
porque você para de fazer round-trip "cadê o teste?", "cadê a
validação?", "por que isso tá em float?".

### Quando o framework paga
- Task 10min+
- Cross-file ou cross-module
- Domínio sensível (auth, pagamento, saúde, financeiro)
- Projeto com múltiplos devs (a trilha de audit é inestimável)

### Quando NÃO paga
- Typo fix
- Renomear variável local
- Log message tweak
- Experiment de 5 minutos que você vai jogar fora

Pra esses, usa Claude Code direto. Overhead de spawn > benefício.

---

## 3. O que é, o que não é

### É:
- **Um framework portável.** Arquivos que você instala em `.claude/` do
  seu projeto.
- **Opinativo.** Impõe protocolo. Você pode customizar, mas não
  ignorar.
- **Stdlib-only em Python.** Zero dependências externas nos hooks.
- **Claude Code primeiro.** Adapter stub pra Gemini existe, mas
  parity real fica pra v2+.
- **Auditado.** Cada spawn, cada decision, cada veto vira evento em
  JSONL.
- **Governed por ADR.** 171 ADRs documentam toda decisão arquitetural.

### NÃO é:
- **Um produto.** Não tem UI, não tem SaaS, não tem login.
- **Uma biblioteca.** Você não faz `npm install` ou `pip install`.
  Você roda um `install.sh` que copia arquivos.
- **Um controlador remoto.** Você NÃO abre este repo e manda o Claude
  trabalhar em outro repo. Você instala o framework NO outro repo e
  abre o Claude Code lá.
- **Substituto de disciplina.** Se o código-base é caótico, framework
  amplifica o caos. Ele amplifica disciplina boa, não cria disciplina.
- **Independente de modelo.** Os "agentes" são todos o mesmo Claude.
  A diferença é perspectiva forçada + checklist carregado.

### Vocabulário essencial
| Termo | Significado |
|-------|-------------|
| **CEO** | Claude operando sob o protocolo, traduz pedido em plano |
| **Owner** | Você. Única pessoa humana no loop |
| **Skill** | Arquivo `SKILL.md` com checklist pra um domínio (ex: security-and-auth) |
| **Persona** | Um archetype em `team.md` com background + red flags + mantra |
| **Spawn** | Quando o CEO chama um sub-agent com persona + skill + file assignment |
| **Plan** | Arquivo `.claude/plans/PLAN-NNN-slug.md` que rastreia uma feature |
| **Debate** | Spawn paralelo de N agents pra critiquing um plano L3+ |
| **Veto** | Hard block. Staff specialist nega merge até issue ser resolvido |
| **ADR** | Architecture Decision Record em `.claude/adr/` |
| **Squad** | Bundle de domínio (personas + pitfalls + skills). Ex: fintech, edtech, government |
| **Hook** | Script Python que roda antes/depois de tool-call do Claude |

---

## 4. Quando usar, quando não usar

### Use quando:
- Task tem blast radius ≥3 arquivos
- Domínio é sensível (auth, pagamento, financeiro, saúde, compliance)
- Você precisa de trilha de audit pra legal/compliance/post-mortem
- Time tem 2+ devs e você quer coerência de padrão
- Você está montando produto novo e quer boas práticas desde dia 1

### Não use quando:
- É um script throwaway de 1h
- É um POC que você vai jogar fora
- Time é 1 pessoa E você nunca vai mostrar o código pra ninguém
- Você quer LLM pra rubber-duck conversa (use Claude Code direto)

### Kill-switch
Se precisar desligar tudo:
```bash
mv .claude .claude.disabled
```
Claude Code volta a operar como assistente genérico. Pra religar:
```bash
mv .claude.disabled .claude
```

---

## 5. Instalar em projeto NOVO

### Pré-requisitos
- Python 3.9+ (`python3 --version`)
- git
- bash ou zsh
- Claude Code CLI instalado

### Passo 1 — Clonar o framework
```bash
cd ~
git clone https://github.com/Canhada-Labs/ceo-orchestration.git
```

### Passo 2 — Rodar o install no seu projeto
```bash
cd /caminho/do/seu-projeto
bash ~/ceo-orchestration/scripts/install.sh
```

Isso instala o perfil `core` (42 skills universais + 8 frontend).

### Passo 3 — Adicionar perfil de domínio (se aplicável)
```bash
# Fintech (trading, cripto, pagamentos)
bash ~/ceo-orchestration/scripts/install.sh --profile core,fintech

# SaaS com LGPD pesado
bash ~/ceo-orchestration/scripts/install.sh --profile core,lgpd-heavy-saas

# Trading HFT de baixa latência
bash ~/ceo-orchestration/scripts/install.sh --profile core,fintech,trading-hft

# Edtech
bash ~/ceo-orchestration/scripts/install.sh --profile core,edtech

# Governo / setor público
bash ~/ceo-orchestration/scripts/install.sh --profile core,government

# Combinações livres
bash ~/ceo-orchestration/scripts/install.sh --profile core,fintech,lgpd-heavy-saas
```

### Passo 4 — Personalizar `CLAUDE.md`
Abre `CLAUDE.md` na raiz do projeto. Substitui placeholders:
```
{{PROJECT_NAME}}  → nome do seu projeto
{{OWNER_NAME}}    → seu nome
{{PROJECT_PATH}}  → caminho absoluto
```

### Passo 5 — Validar
```bash
# Testes do framework
python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ -q
# Esperado: ~800+ passed, 0 failed

# Governance check
bash .claude/scripts/validate-governance.sh
# Esperado: PASS
```

### Passo 6 — Abrir Claude Code e ativar
```bash
cd /caminho/do/seu-projeto
claude
```

Na primeira mensagem:
> "Ativa o protocolo CEO."

O Claude vai ler `CLAUDE.md`, `PROTOCOL.md`, carregar a skill
`ceo-orchestration`, e responder como CEO.

### Passo 7 — Teste com um pedido pequeno
> "Quero entender o que temos no projeto. Faz um resumo."

Se ele responder descrevendo o projeto com referência a arquivos
reais, tá funcionando.

---

## 6. Instalar em projeto EXISTENTE

> **Cenário comum (ex: adopter-1).** Você já tem `.claude/` com suas
> skills custom, seus agents, seu `settings.json`. Rodar `install.sh`
> cru vai sobrescrever coisa sua. Siga este fluxo.

### Passo 1 — Backup INTEIRO
```bash
cd /caminho/do/adopter-1
cp -r .claude .claude.backup-$(date +%Y%m%d-%H%M)
cp CLAUDE.md CLAUDE.md.backup 2>/dev/null || true
cp .github/CODEOWNERS .github/CODEOWNERS.backup 2>/dev/null || true
```

### Passo 2 — Inventário do que você tem
```bash
cd /caminho/do/adopter-1

# Estrutura atual
find .claude -maxdepth 3 -type d | sort
find .claude -maxdepth 3 -name "*.md" | sort

# Skills custom? Agents custom?
ls .claude/skills/ 2>/dev/null
ls .claude/agents/ 2>/dev/null

# Settings atual
cat .claude/settings.json 2>/dev/null
```

Anote em papel:
- Skills custom que VOCÊ criou (não do framework)
- Agents/personas custom
- Permissions ou hooks customizados no `settings.json`
- Arquivo `CLAUDE.md` existente (se houver)

### Passo 3 — Instalar framework fresh em diretório separado
```bash
mkdir -p /tmp/ceo-fresh
cd /tmp/ceo-fresh
bash ~/ceo-orchestration/scripts/install.sh --profile core,fintech
# (ajusta --profile ao seu domínio)
```

Agora você tem uma instalação limpa para comparar.

### Passo 4 — Comparar fresh vs seu projeto
```bash
diff -rq /tmp/ceo-fresh/.claude /caminho/do/adopter-1/.claude
```

Saída típica vai listar 3 categorias:
1. **Só em `/tmp/ceo-fresh`** — framework files que você NÃO tem. Copia pro projeto.
2. **Só em `/caminho/do/adopter-1`** — SEUS arquivos custom. Mantém.
3. **Em ambos (differ)** — conflito. Merge manual.

### Passo 5 — Copiar o que é framework-padrão
```bash
cd /caminho/do/adopter-1

# Hooks (sempre copiar — são do framework)
cp -r /tmp/ceo-fresh/.claude/hooks .claude/

# Scripts (sempre copiar)
cp -r /tmp/ceo-fresh/.claude/scripts .claude/

# Commands (sempre copiar)
cp -r /tmp/ceo-fresh/.claude/commands .claude/

# ADR template
cp -r /tmp/ceo-fresh/.claude/adr .claude/ 2>/dev/null || cp /tmp/ceo-fresh/.claude/adr/README.md .claude/adr/

# SPEC contracts
cp -r /tmp/ceo-fresh/SPEC .

# Protocol
cp /tmp/ceo-fresh/PROTOCOL.md .
```

### Passo 6 — Merge manual do `CLAUDE.md`
Se você já tinha `CLAUDE.md`:
```bash
# Compara lado a lado
diff CLAUDE.md.backup /tmp/ceo-fresh/CLAUDE.md
```

Use o `CLAUDE.md` do framework como base (tem as 3 GATES) e transplante:
- Seção de stack-specific do seu antigo (linguagem, ferramentas)
- Contexto de domínio específico do seu projeto
- CHANGELOG histórico (se houver)

### Passo 7 — Merge manual do `settings.json`
```bash
# Veja hooks que o framework exige
cat /tmp/ceo-fresh/.claude/settings.json

# Seu settings original
cat .claude/settings.json.backup 2>/dev/null || echo "não havia"
```

Copia a seção `"hooks"` do framework pro seu `settings.json`
existente. Mantém seu `permissions` e `mcpServers`. Se houver
conflito de hooks, o framework sempre ganha (hooks do framework são
`fail-open` — não vão te atrapalhar).

### Passo 8 — Migrar SUAS skills custom pro layout do framework
Framework espera esse layout:
```
.claude/skills/
├── core/<skill>/SKILL.md            # universais
├── frontend/<skill>/SKILL.md        # universais frontend
└── domains/<seu-dominio>/           # squad do seu domínio
    ├── team-personas.md
    ├── pitfalls.yaml
    ├── task-chains.yaml
    └── skills/
        └── <skill-custom>/SKILL.md
```

Se sua skill custom estava em `.claude/skills/reconciliation-logic.md`
(achatado, sem subdir), reorganiza:

```bash
mkdir -p .claude/skills/domains/ledger/skills/reconciliation-logic
mv .claude/skills/reconciliation-logic.md \
   .claude/skills/domains/ledger/skills/reconciliation-logic/SKILL.md
```

Garante que `SKILL.md` tem frontmatter YAML obrigatório:
```yaml
---
name: Reconciliation Logic
description: Reconciliação de débito/crédito em double-entry ledger com edge cases BR (NFe, PIX delay, estorno).
trigger: Quando a task envolve reconciliação contábil ou fechamento de período.
---
```

### Passo 9 — Criar o squad do seu domínio (contrato ADR-009)
Para cada domínio custom (ex: `ledger`), os 3 arquivos são
OBRIGATÓRIOS senão o validator falha:

**`.claude/skills/domains/ledger/team-personas.md`** — personas
específicas (ex: "Staff Accounting Engineer com VETO em double-entry").

**`.claude/skills/domains/ledger/pitfalls.yaml`** — mínimo 12
pitfalls conhecidos do domínio:
```yaml
- id: ledger-001
  title: "Double-entry sem balanceamento atomico"
  severity: critical
  pattern: "INSERT INTO ledger_entries sem transação envolvendo débito E crédito"
  mitigation: "Usar tx explícita; trigger de validação no insert"
- id: ledger-002
  ...
```

**`.claude/skills/domains/ledger/task-chains.yaml`** — mínimo 2
workflows:
```yaml
- name: close-period
  steps:
    - lock-period-entries
    - reconcile-balances
    - generate-statements
    - freeze-period
- name: handle-refund
  ...
```

### Passo 10 — Atalho: `/architect` gera squad automaticamente
Se você ainda não tem os 3 arquivos, o framework pode gerar o
scaffolding pra você:

Dentro do Claude Code:
```
/architect "adopter-1: double-entry accounting with BR tax semantics, NFe integration, PIX reconciliation, LGPD-compliant audit trail"
```

Ele vai produzir os 3 arquivos + skills sugeridas. Revisa, ajusta
adicionando suas skills custom, valida.

### Passo 11 — Regenerar inventory de skills
```bash
cd /caminho/do/adopter-1
bash .claude/scripts/generate-skill-inventory.sh > /tmp/new-inv.md

# Patcha o arquivo da skill ceo-orchestration entre os marcadores:
# <!-- BEGIN AUTO-GENERATED SKILL INVENTORY -->
<!-- Source: bash .claude/scripts/generate-skill-inventory.sh -->
<!-- Regenerate after adding/removing skills. CI will diff in Sprint 2+. -->

### Core (universal)

- `agent-architect` — Meta-agent that drafts a new squad bundle (team-personas, pitfalls, skill-selection, personas roster, rationale) from an Owner-supplied domain brief.
- `ai-llm-orchestration` — AI system and LLM Council management for {{PROJECT_NAME}}.
- `architecture-decisions` — Architecture decision-making framework for {{PROJECT_NAME}}.
- `ceo-orchestration` — How Claude (the CEO) orchestrates a named team of specialist agents.
- `chaos-and-resilience` — Chaos engineering, resilience patterns, failure recovery, and fault tolerance for the {{PROJECT_NAME}}.
- `code-intelligence-lsp` — Engineering doctrine for using Language Server Protocol tools in agent code-analysis workflows for {{PROJECT_NAME}}.
- `code-review-checklist` — Structured code review process for the {{PROJECT_NAME}}.
- `codebase-onboarding` — > Structured codebase orientation workflow for {{PROJECT_NAME}}.
- `compliance-lgpd` — LGPD (Lei 13.709/2018) compliance for a Brazilian SaaS platform.
- `consent-lifecycle` — Consent as an auditable state machine for Brazilian LGPD and equivalent regimes.
- `cookbook-advisor` — Advise on 4 Anthropic Cookbook 2026 patterns (COOK-P1..P4) — surface UX hints when a task signature matches a pattern trigger class.
- `coverage-audit` — Read-only cross-artifact consistency analyzer (port of spec-kit /analyze).
- `cross-llm-pair-review` — Cross-LLM Pair-Rail dispatch + verdict interpretation — when to invoke, Cases A-F asymmetric matrix outcomes, Owner override semantics, post-verdict labeling protocol, promotion...
- `data-schema-design` — PostgreSQL schema design including migration strategy and cross-ORM migration tooling (Prisma, Drizzle, Kysely, Django, golang-migrate), retention policy design, index strategy, keyset pagination, queue-claim patterns, disaster recovery DDL, SECURITY DEFINER safety, RLS policy patterns and RLS performance, naming conventions, and cross-engine notes for MySQL/MariaDB.
- `devops-ci-cd` — CI/CD pipeline design, Docker optimization, PaaS deployment, health check engineering, rollback strategies, monitoring infrastructure, and secret management for backend services.
- `dpo-reporting` — Data Protection Officer reporting discipline for Brazilian LGPD compliance.
- `evidence-based-qa` — Evidence-based quality assurance doctrine for {{PROJECT_NAME}}.
- `git-workflow-discipline` — > Authoritative git workflow doctrine for {{PROJECT_NAME}}.
- `growth-and-launch` — Invite-only product launch, coupon systems, referral tracking, trial-to-paid conversion, and waitlist management for SaaS platforms.
- `help-me` — Natural-language assistant that recommends <=3 contextual skills/commands for the Owner's current task.
- `identity-and-trust-architecture` — > Identity and trust doctrine for {{PROJECT_NAME}} — token lifecycle (JWT access <= 1h, mandatory refresh rotation), authorization patterns (RBAC/ABAC, scope-based, least privilege), service-to-service trust (mTLS, signed JWTs, no implicit trust), OAuth/OIDC pitfalls (PKCE, state parameter, callback validation, alg=none and audience-check defenses), and zero-trust principles.
- `incident-management` — Live-incident operational doctrine for the {{PROJECT_NAME}} — severity classification, role assignment under load, escalation discipline, blame-free post-incident review, communication cadence, and rollback-first bias.
- `incremental-refactoring` — Safely evolving existing production codebases through incremental refactoring.
- `llm-routing-and-finops` — LLM routing and cost-governance doctrine for {{PROJECT_NAME}}.
- `mcp-server-authoring` — Engineering doctrine for building MCP (Model Context Protocol) servers within {{PROJECT_NAME}}.
- `minimal-change-discipline` — Operational doctrine for scoping code changes to the minimum necessary to fulfill a task in {{PROJECT_NAME}}.
- `monetization-and-billing` — Implementing Stripe billing, subscription management, tiered access control, and payment infrastructure for SaaS platforms.
- `observability-and-ops` — Designing observability into systems from the start, including metrics, health checks, staleness detection, quality signals, admin dashboards, and operational alerts.
- `parallelization-by-default` — Detect decomposable tasks and dispatch <=6 sub-agents in parallel.
- `performance-engineering` — Performance engineering for Node.js real-time systems.
- `pii-data-flow` — Inventorying and governing personally identifiable information (PII) as it flows through a B2B SaaS under LGPD.
- `pre-plan-brainstorm` — Requirements elicitation checklist run by the CEO or a delegated VP Product/VP Engineering before drafting an L3+ plan.
- `product-conversion-readiness` — Patterns for transforming a functional product into one that converts users to paying customers.
- `public-api-design` — Designing and implementing public-facing APIs with versioning, self-service API key management, per-tier rate limiting, consumer-facing documentation, developer onboarding, and SDK patterns.
- `receiving-review` — Use when receiving code-review feedback or a critique — from the Owner, the Codex pair-rail, a debate archetype, or any reviewer — and deciding whether to implement, clarify, or push back.
- `requirement-quality-checklist` — > 'Unit Tests for English' — validates requirements writing quality, NOT implementation.
- `security-and-auth` — Security architecture, authentication, authorization, and hardening for the {{PROJECT_NAME}}.
- `spec-clarify` — Disciplined ambiguity reduction for PLAN-NNN.
- `state-machines-and-invariants` — Governing correctness through explicit state machines and enforced invariants.
- `technical-writing` — Doctrine for authoring clear, precise technical documentation in {{PROJECT_NAME}}.
- `terse-mode` — Output-economy skill for research-heavy flows.
- `testing-strategy` — Testing strategy, patterns, and quality assurance for the project.

_Total in Core (universal): 42 skill(s)._

### Frontend (universal)

- `accessibility-and-wcag` — WCAG 2.1 AA compliance, ARIA patterns, keyboard navigation, focus management, screen reader support, color contrast, and accessible data visualization for the {{PROJECT_NAME}} frontend.
- `code-quality-and-typescript` — TypeScript strict mode governance, ESLint rule strategy, type assertion audit, dead code detection, circular dependency prevention, `:any` evaluation criteria, naming conventions, and code review quality gates for the {{PROJECT_NAME}} frontend.
- `design-system-and-components` — Design token governance, component architecture patterns, shared component organization, empty/loading/error state standards, component library integration (e.g.
- `frontend-accessibility` — Accessibility and internationalization for the {{PROJECT_NAME}} frontend.
- `frontend-data-layer` — Universal frontend data-layer patterns — server state library architecture (e.g.
- `frontend-patterns` — > Universal frontend development patterns for the {{PROJECT_NAME}} platform.
- `frontend-performance-optimization` — Bundle analysis, code splitting, lazy loading strategy, rendering optimization, virtualization patterns, Core Web Vitals targets, memoization correctness, network performance, image optimization, and build tool tuning (e.g.
- `ux-and-user-journeys` — User experience design, journey mapping, information architecture, navigation patterns, responsive/mobile strategy, onboarding flows, empty state messaging, progressive disclosure, micro-interactions, and conversion-oriented UX for the {{PROJECT_NAME}} frontend.

_Total in Frontend (universal): 8 skill(s)._

### Domain: academic-humanities

- `anthropologist` — | Anthropological lens for product, market, and organizational research.
- `geographer` — | Geographic lens for product, market, and operational analysis.
- `historian` — | Historical method discipline for product, organisational, and market analysis.
- `narratologist` — | Narrative analysis applied to product, brand, and organisational communications.
- `psychologist` — | Applied psychology discipline for product, organisational, and research contexts.

_Total in Domain: academic-humanities: 5 skill(s)._

### Domain: agents-meta

- `dynamic-workflow-mode` — Design task-local harnesses, eval gates, and reusable-skill extraction for the case where an agent can generate or adapt its own workflow instead of only following a fixed command flow.
- `loop-design-check` — Design a goal-oriented agent loop and review it for the ways loops fail — spinning and burning tokens, Goodhart-gaming the verifier, or driving a wrong answer to completion.

_Total in Domain: agents-meta: 2 skill(s)._

### Domain: architecture

- `hexagonal-architecture` — > Ports & Adapters (hexagonal) design discipline for keeping business logic independent of frameworks, transport, and persistence.
- `recsys-pipeline-architect` — > Spec-and-scaffold discipline for composable recommendation, ranking, and feed pipelines built on the six-stage pattern Source → Hydrator → Filter → Scorer → Selector → SideEffect.

_Total in Domain: architecture: 2 skill(s)._

### Domain: business-support

- `analytics-reporter` — | Business intelligence reporting discipline covering data-source-of-truth selection, dashboard design, narrative reporting, statistical literacy, visualisation discipline, and audience-tailored output.
- `executive-summary` — | Executive summary authoring discipline covering Pyramid Principle (Minto SCQ), one-page architecture, decision-enabling structure, audience-aware compression, and the never-bury-bad-news rule.
- `finance-tracker` — | SMB and startup finance tracking — cash-flow projection, runway calculation, burn-rate diagnostics, founder-finance literacy, monthly close-light cadence, and founder-friendly tooling (Brex / Mercury / Stripe Atlas / Conta Azul / Omie).
- `support-responder` — | Customer support response discipline covering ticket triage, severity assessment, response template and macro discipline, escalation path ownership, voice-of-customer feedback loops, and multi-channel support operations across email, chat, phone, and social.

_Total in Domain: business-support: 4 skill(s)._

### Domain: civil-engineering

- `civil-engineer` — > Civil engineering practice spanning structural analysis, geotechnical assessment, hydraulic and hydrologic design, transportation engineering, construction project management, and multi-jurisdiction code compliance (IBC / ASCE-7 / AISC / ACI / AASHTO; Eurocodes EN 1990–1999; NBR-ABNT 6118 / 8800 / 6122).

_Total in Domain: civil-engineering: 1 skill(s)._

### Domain: community

- `advanced-evaluation` — > Production-grade patterns for LLM-as-judge evaluation systems, covering approach selection (direct scoring, pairwise comparison, reference-based, G-Eval, and Constitutional), systematic bias mitigation (position swap-symmetry, verbosity length-control, self-enhancement separation, order randomization), calibration against human ground truth with inter-rater agreement thresholds, rubric design with falsifiable criteria, statistical discipline for sample sizing and confidence intervals, and automated pipeline architecture with drift detection.
- `agent-evaluation` — > Rigorous testing and benchmarking of LLM agents—covering behavioral contract verification, capability boundary probing, reliability metric collection, and production monitoring.
- `agentic-actions-auditor` — > Static security analysis for GitHub Actions workflows that invoke AI coding agents (Claude Code Action, Gemini CLI, OpenAI Codex, GitHub AI Inference).

_Total in Domain: community: 3 skill(s)._

### Domain: cpp

- `cpp-coding-standards` — > Modern C++ (C++17/20/23) coding standard grounded in the public C++ Core Guidelines.
- `cpp-testing` — > Testing workflow for modern C++ (C++17/20) with GoogleTest / GoogleMock driven through CMake and CTest.

_Total in Domain: cpp: 2 skill(s)._

### Domain: data-ml

- `prisma-patterns` — > Production patterns and footgun avoidance for the Prisma ORM in TypeScript backends: schema and index design, ID strategy, include-vs-select and DTO mapping, transaction form selection, the PrismaClient singleton, cursor pagination, soft delete, typed error translation, and serverless connection pooling.
- `pytorch-patterns` — > Idiomatic PyTorch for robust, reproducible, memory-conscious training pipelines: device-agnostic placement, full seed control, explicit tensor shape tracking, clean nn.Module construction, weight initialisation, correct train/eval mode discipline, the standard training and validation loops, efficient Dataset/DataLoader configuration, variable-length collation, resumable checkpointing, and the performance levers (mixed precision, gradient checkpointing, torch.compile).

_Total in Domain: data-ml: 2 skill(s)._

### Domain: desktop

- `windows-desktop-e2e` — > End-to-end UI testing for native Windows desktop applications — WPF, WinForms, Win32/MFC, and Qt (5.x and 6.x) — driven through pywinauto on top of the built-in Windows UI Automation (UIA) accessibility API.

_Total in Domain: desktop: 1 skill(s)._

### Domain: devrel

- `developer-advocate` — > Developer relations and advocacy discipline covering technical content production (tutorials, cookbooks, deep-dives, quickstarts, migration guides), documentation engineering with CI runnability gates, sample app authorship grounded in production patterns, conference and meetup proposal craft, community operations across Discord/Slack/GitHub/forums, developer-experience feedback synthesis routed to product, and internal evangelism including new-feature dogfood and release-note authorship.
- `frontend-slides` — > Build zero-dependency, animation-rich HTML presentations — from a topic, from rough notes, or by converting an existing PowerPoint deck to the web.
- `ui-demo` — > Record a polished demo/walkthrough video of a web application with a browser automation driver (Playwright).

_Total in Domain: devrel: 3 skill(s)._

### Domain: dotnet

- `csharp-testing` — > Testing discipline for C# / .NET applications.

_Total in Domain: dotnet: 1 skill(s)._

### Domain: edtech

- `assessment-integrity` — Engineering anti-cheat, proctoring, and grade-tamper resistance for K-12 and higher-ed assessment platforms.
- `learning-analytics` — Engagement metrics, dropout prediction, and early-warning systems for K-12 and higher-ed with explicit fairness and privacy trade-off discipline.
- `student-data-privacy` — Privacy engineering for K-12 and higher-ed student data under FERPA (US), LGPD-educational (BR), and COPPA (US under-13).
- `study-abroad-advisory` — | End-to-end advisory doctrine for international study pathways covering destination selection, profile assessment, school-list construction, essay coaching, application timeline management, standardized test strategy, visa preparation, and post-arrival adaptation.

_Total in Domain: edtech: 4 skill(s)._

### Domain: embedded

- `embedded-firmware` — > Governance and hard-rules for embedded firmware development on resource-constrained microcontrollers.

_Total in Domain: embedded: 1 skill(s)._

### Domain: finance-accounting

- `bookkeeper-controller` — | SMB bookkeeping and controller discipline covering chart of accounts design, double-entry transaction recording, bank and credit-card reconciliation, accounts-receivable and accounts-payable cycles, month-end close management, financial statement preparation (P&L, Balance Sheet, Cash Flow), SOX-lite internal controls, payroll integration, and multi-entity consolidation.
- `financial-analyst` — | Corporate FP&A and financial analyst discipline covering variance analysis, KPI dashboard architecture, business-unit P&L review, scenario modelling, capital-allocation evaluation, and board-pack preparation.
- `fpa-analyst` — | Senior FP&A discipline for annual planning, rolling forecast cycles, driver-based modelling, capital-expenditure governance, headcount and workforce planning, cost-centre management, and cross-functional finance partnership.
- `tax-strategist` — > Corporate tax strategy across multi-jurisdiction portfolios — US federal and state nexus, EU corporate income tax, VAT, Digital Services Tax, Pillar 2 GloBE minimum tax, and Brazil Lucro Real / Presumido / Simples Nacional plus ICMS, PIS-COFINS, and the Reforma Tributária transition.

_Total in Domain: finance-accounting: 4 skill(s)._

### Domain: fintech

- `blockchain-security-audit` — Audit-grade security review for EVM smart contracts and DeFi protocols on Solidity ^0.8.24 with OpenZeppelin Contracts v5.x.
- `equity-research` — | Fundamental and quantitative equity research discipline for public markets.
- `exchange-api-integration` — Integrating with cryptocurrency exchange APIs (REST and WebSocket), handling exchange-specific quirks, discrete limits, rate limits, symbol mapping, depth constraints, sequencing, and fallback logic.
- `exchange-onboarding-playbook` — Step-by-step operational playbook for adding new cryptocurrency exchanges to a trading platform.
- `financial-correctness-and-math` — Ensuring mathematical correctness and determinism in financial systems.
- `financial-display` — Financial data display correctness for a crypto trading platform frontend.
- `frontend-data-layer` — Fintech-specific frontend data-layer patterns — Financial Display Rules (safe-number helpers, locale-aware formatters, precision-per-pair), order-book-specific WS throttling/rAF batching (30 books/frame, 50ms per exchange:pair), price/volume caching concerns, project-specific endpoint audit findings (/stats, fear-greed, duplicate keys), and trading-domain data patterns.
- `frontend-patterns` — Fintech-specific frontend patterns — financial data formatting (BRL/USD/USDT/ multi-currency), trading terminal component architecture (order book virtualization, trading form), real-time price update patterns, PRO tier gating (Free/Pro/Trader/Quant ladder), accessibility rules specific to dense financial data, and fintech anti-patterns.
- `prediction-markets` — Prediction market integration and trading strategy for a crypto trading platform.
- `real-time-market-systems` — Designing, reviewing, and evolving real-time market data systems, including order book engines, WebSocket ingestion, exchange adapters, pair normalization, depth aggregation, VWAP calculation, and latency-sensitive financial infrastructure.
- `solidity-smart-contracts` — > Governance and hard-rules for authoring, reviewing, and deploying Solidity smart contracts on EVM-compatible chains.
- `trading-execution` — Trading execution architecture for a crypto trading platform.

_Total in Domain: fintech: 12 skill(s)._

### Domain: golang

- `golang-patterns` — > Idiomatic Go engineering discipline: writing, reviewing, and refactoring Go so it stays boring, predictable, and easy to maintain.

_Total in Domain: golang: 1 skill(s)._

### Domain: government

- `accessibility-section-508` — Section 508 + WCAG 2.1 AA compliance for public-sector software.
- `digital-presales` — > Presales engineering for government and public-sector digital transformation engagements.
- `foia-and-records` — FOIA (5 USC §552) compliance engineering — records lifecycle, retention schedules, redaction audit trails, and request fulfillment.
- `public-procurement` — Public-sector procurement engineering — bid confidentiality until award, contractor vetting against debarment lists, conflict-of-interest declarations, audit trails for every contract decision, and set-aside compliance.

_Total in Domain: government: 4 skill(s)._

### Domain: healthcare

- `healthcare-customer-service` — | Healthcare patient-facing customer service discipline covering appointment scheduling, billing inquiries, complaint handling, insurance navigation, and escalation across clinical, billing, privacy-breach, and safety paths.
- `marketing-compliance` — | Healthcare marketing compliance discipline covering the full pre-publication review lifecycle: claim substantiation against clinical-evidence hierarchy, FDA / FTC / Anvisa RDC 96 / EMA / EFPIA promotional rules, off-label use prohibition, fair-balance obligations (efficacy and safety in proportion), testimonial and HCP-engagement restrictions under Sunshine Act / Open Payments / EFPIA Disclosure Code, and PII / PHI handling in campaign analytics (HIPAA marketing authorisation, tracking-pixel case-law, LGPD Art.

_Total in Domain: healthcare: 2 skill(s)._

### Domain: hospitality

- `guest-services` — | Operating doctrine for hospitality guest services across hotel, vacation rental, and restaurant operations — covering check-in and check-out flow, complaint resolution, special-request fulfillment, multi-channel communication, online review management, and service recovery.

_Total in Domain: hospitality: 1 skill(s)._

### Domain: hr

- `hr-onboarding` — | Employee onboarding doctrine covering pre-boarding paperwork and document collection, day-one orientation, first-30 / first-60 / first-90 plans, role and mission induction, team and culture integration, system and access provisioning under least-privilege discipline, benefits enrolment with window enforcement, compliance training completion tracking, and manager check-in cadence.
- `recruitment-specialist` — | End-to-end talent acquisition across the full hiring lifecycle.

_Total in Domain: hr: 2 skill(s)._

### Domain: i18n-business

- `cultural-intelligence` — | Cross-cultural business strategy discipline for international operations, partnerships, and multicultural teams.
- `french-consulting` — | France-specific business consulting covering Convention Collective navigation, RGPD compliance specifics distinct from generic GDPR guidance, Bpifrance funding programmes, Crédit Impôt Recherche eligibility, French professional formality and relationship register, syndicat and CSE labour relations, and droit du travail obligations.
- `korean-business` — | Korea-specific business skill covering chaebol relationship navigation, poom-ui (품의) consensus-approval mechanics, PIPA (Personal Information Protection Act) and PIPC compliance, Fair Trade Act constraints on conglomerate conduct, hierarchical Confucian register calibration, military-service awareness in hiring, hwesik (회식) culture, vendor- onboarding ritual, and IP enforcement specifics.
- `language-translator` — | Professional translation discipline covering source-target language pairing, register and tone fidelity, machine-translation post-editing (MTPE), glossary and style guide management, certified translation for legal, medical, and regulatory contexts, and the transcreation vs.

_Total in Domain: i18n-business: 4 skill(s)._

### Domain: identity-systems

- `identity-graph-operator` — | Customer identity graph operations for marketing and customer-data platforms.

_Total in Domain: identity-systems: 1 skill(s)._

### Domain: jvm

- `java-coding-standards` — > Coding standards for modern Java (17+) services on the two dominant JVM backend stacks — Spring Boot and Quarkus.
- `springboot-patterns` — > Spring Boot architecture and API patterns for production-grade services — layered controller/service/repository design, REST endpoint shape, Spring Data access, DTO validation, centralised exception handling, caching, async processing, scheduled jobs, request filters, pagination, resilient external calls, rate limiting, and observability.

_Total in Domain: jvm: 2 skill(s)._

### Domain: legal

- `client-intake` — Legal client intake discipline for conflict-of-interest screening, capacity assessment, scope-of-engagement definition, fee-agreement authoring, identity verification, AML/KYC compliance, and attorney-client privilege establishment.
- `document-review` — | Legal document review for discovery, due-diligence, and regulatory submissions.
- `legal-billing` — | Legal billing and time-tracking discipline for law firms and legal departments.

_Total in Domain: legal: 3 skill(s)._

### Domain: marketing-global

- `agentic-search-optimizer` — > Discipline for optimising content and interactive surfaces for agentic-search workflows — multi-step LLM-driven research, browsing-agent traversal, and computer-use pipelines (Anthropic computer-use, OpenAI deep-research, Perplexity browser, Edge Copilot).
- `ai-citation-strategist` — > Answer Engine Optimisation (AEO) discipline covering citation-eligibility analysis, LLM-readable content structure, schema and entity discipline, per- platform citation tracking (Perplexity, ChatGPT-search, Google AI Overview, Bing Copilot), and cross-platform source authority enforcement.
- `app-store-optimizer` — > App Store Optimization discipline covering keyword targeting across the relevance × volume × difficulty matrix, conversion-optimised metadata and visual assets for Apple App Store and Google Play, systematic A/B test cadence, platform-algorithm awareness for both crawler models, review-rating economy management, and post-install retention loop diagnostics.
- `book-co-author` — > Ghostwriting and co-authorship discipline covering voice capture, narrative architecture, chapter structure, source management, attribution clarity, and the manuscript-to-published lifecycle.
- `carousel-growth-engine` — > Cross-platform carousel post engineering — slide architecture, visual hierarchy, hook-to-payoff arc, and save-share mechanics across Instagram, LinkedIn, Twitter (X carousel / document), TikTok photo series, and Pinterest.
- `content-creator` — > Cross-platform content creation discipline covering narrative architecture, distribution-aware editing, repurposing matrix design, audience research methodology, and voice consistency enforcement.
- `growth-hacker` — > Experiment-driven discipline for product and market growth covering funnel diagnostics across the full AAARRR (Awareness / Acquisition / Activation / Retention / Referral / Revenue) model, statistically rigorous experiment design, scalable channel discovery, and growth-loop architecture.
- `instagram-curator` — > Instagram strategy discipline covering Reels-led growth, Carousel save-engine mechanics, Stories community loops, and Feed permanence architecture.
- `linkedin-content-creator` — > LinkedIn content strategy for professional positioning and B2B audience development — covers text post, carousel document, native video, and long-form article selection matched to goal and audience; hook construction doctrine that treats the first two lines as the entire argument; dwell-time optimisation through format and structure choices; thought-leadership architecture built on 3-5 defensible content pillars; professional POV consistency that pairs opinion with evidence and caveat; and engagement frame that prioritises genuine reply depth over like volume.
- `podcast-strategist` — > Podcast production and growth discipline covering show concept architecture, episode structure engineering, guest relations protocols, audio production standards, multi-platform distribution mechanics, and monetisation integrity.
- `reddit-community-builder` — Reddit community participation and brand presence — subreddit-specific norms, mod relations, AMA discipline, value-first contribution, and anti-self-promotion compliance.
- `seo-specialist` — Technical and content SEO for software products — covers Core Web Vitals, schema.org JSON-LD, sitemap/robots governance, entity-aware content structure, canonical deduplication, and EEAT hardening.
- `social-media-strategist` — > Cross-channel social media strategy orchestration: platform mix selection against audience density and commercial intent, integrated content calendar design at theme-topic-day granularity, brand-voice unification across register variants, and channel-fit diagnosis before any new platform commitment.
- `tiktok-strategist` — > TikTok platform strategy discipline covering algorithm-aware content framing, hook-first scripting, watch-time optimization, trend velocity capture, and monetisation discipline.
- `twitter-engager` — > Twitter / X engagement strategy — thread architecture (hook tweet → development → CTA; numbered vs unnumbered tradeoffs), reply economy (reply-as-discovery; quote-tweet vs reply tradeoffs), list and community building, trend-hijack discipline with topic relevance gate, posting cadence with reply ratio floor, and crisis response (delete-vs-correct; 4-hour rule).
- `video-optimization-specialist` — > Long-form video discipline — YouTube-first, with application to IG-Reels long-cuts and TikTok Stories — covering title and thumbnail optimisation as a coupled pair, retention curve diagnostics, watch-time architecture, A/B testing for packaging variants, end-screen and cards strategy, and SEO-grounded discovery.

_Total in Domain: marketing-global: 16 skill(s)._

### Domain: mobile

- `mobile-app-builder` — Mobile application development discipline covering iOS native (Swift / SwiftUI), Android native (Kotlin / Jetpack Compose), React Native, and Flutter cross-platform approaches.

_Total in Domain: mobile: 1 skill(s)._

### Domain: paid-media

- `auditor` — > Paid-media account audit discipline: systematic evaluation of account structure, spend-waste detection, attribution-integrity verification, conversion-tracking validation, and agency-vs-internal performance benchmarking across Google Ads, Microsoft Ads, and Meta.
- `creative-strategist` — > Performance ad creative discipline covering concept framework selection (Problem/Agitate/Solve, AIDA, PAS, Hook-Turn-Payoff, Founder-Story, Testimonial, Comparison), creative brief architecture, format-specific iteration cadence, fatigue diagnostics, UGC and creator strategy, and performance creative testing.
- `paid-social-strategist` — > Paid social discipline covering campaign-objective mapping, platform selection scoring, Advantage-Plus versus manual structure, post-iOS-14.5 measurement (SKAdNetwork conversion-value mapping, aggregated event measurement), creative-volume strategy, bid and budget mechanics, and attribution methodology.
- `ppc-strategist` — > Pay-per-click strategy across Google Ads, Microsoft Ads, and Meta: campaign structure design at account/campaign/ad-group/keyword hierarchy, intent-based keyword research with negative-keyword discipline, bid strategy selection matched to data-maturity level, responsive search ad testing with statistical-significance thresholds, landing page message-match and conversion-element validation, budget pacing diagnostics via impression-share signals, and attribution model selection beyond last-click.
- `programmatic-buyer` — > Programmatic display, video, and CTV buying discipline covering DSP selection and capability mapping, supply-path optimisation, brand-safety and viewability enforcement, invalid traffic (IVT) detection, data targeting across 1P/2P/3P and cookieless signals, private marketplace deal structures, and attribution methodology.
- `search-query-analyst` — > Search query analysis discipline for paid search accounts: STR and SQR mining at configurable frequency cadence, intent classification across informational / commercial / transactional / navigational axes, negative-keyword harvest at account / campaign / ad-group scope, query-to-keyword matching diagnostics across match types, automated bidding signal interpretation against data-sufficiency thresholds, and irrelevant-traffic detection via geo / device / language / parameter-stuffing vectors.
- `tracking-specialist` — > Ad-tracking and measurement engineering discipline covering pixel deployment, GA4 / Meta CAPI / TikTok Events API server-side tracking, consent-mode v2, cross-domain identity stitching, conversion-value modeling, and data-quality assurance.

_Total in Domain: paid-media: 7 skill(s)._

### Domain: project-management

- `experiment-tracker` — > Product and growth experiment lifecycle manager covering hypothesis registry, experiment-design quality assurance, in-flight monitoring, results synthesis, learnings library, and experiment-fatigue detection.
- `project-shepherd` — | Operational steward discipline for accountable execution across functional teams — distinct from strategic program management.
- `studio-operations` — > Creative studio and agency operations discipline covering utilisation tracking, billable-rate enforcement, capacity planning, project profitability per client, retainer-vs-project revenue mix, freelance-network management, and studio-margin economics.
- `studio-producer` — | Creative-project producer discipline — scope definition, creative-brief authoring, talent and vendor selection, schedule and budget management, delivery cadence, client expectations management, and post-mortem.

_Total in Domain: project-management: 4 skill(s)._

### Domain: real-estate-finance

- `buyer-seller-agent` — | Residential real estate transaction discipline for buyer and seller representation.
- `loan-officer-assistant` — > Residential mortgage loan origination support covering application intake, pre-qualification math (DTI / LTV / housing-expense ratio / cash-to-close), document collection and expiration tracking, credit/income/asset verification, AUS run-up (DU / LP / GUS), and regulatory compliance (RESPA / TILA / TRID disclosure timing / ECOA Reg-B fair-lending / HMDA / LGPD-financial / current BCB / CMN housing-credit resolutions in Brazil — verify the operative authority at engagement time / EU MCD).

_Total in Domain: real-estate-finance: 2 skill(s)._

### Domain: retail

- `customer-returns` — > Governs retail and e-commerce returns operations: RMA workflow design, return reason taxonomy with root-cause analytics, restocking disposition decisions, refund / credit / exchange policy across payment channels, fraud detection covering wardrobing and serial-returner patterns using cross-account graph signals, and reverse logistics cost optimisation.

_Total in Domain: retail: 1 skill(s)._

### Domain: saas-platforms

- `cms-developer` — > CMS and DXP development across headless (Sanity, Contentful, Strapi, Payload) and traditional (WordPress, Drupal, Sitecore) platforms.
- `filament-specialist` — | Filament v3 (Laravel TALL stack admin panel) optimisation for teams building or maintaining Laravel back-office applications.
- `salesforce-architect` — Salesforce platform architecture — Sales / Service / Marketing / Experience / Commerce Cloud selection, declarative-first / programmatic-when-justified discipline, governor limit budget management, data model design (standard object reuse, custom objects, Master-Detail vs Lookup vs Junction), Apex + LWC + Flow trade-offs, integration pattern selection (REST / Bulk / Streaming API / Platform Events / CDC), and authorisation-model design (profiles / permission sets / OWD sharing rules).

_Total in Domain: saas-platforms: 3 skill(s)._

### Domain: sales

- `account-strategist` — > Post-sale account strategy discipline covering land-and-expand execution, stakeholder mapping across multi-threaded relationships, QBR facilitation as forward-looking planning sessions, and retention math anchored to Net Revenue Retention (NRR) and Gross Revenue Retention (GRR) targets.
- `deal-strategist` — > MEDDPICC qualification, competitive positioning, and win planning for complex B2B sales cycles.
- `discovery-coach` — > Governs discovery methodology for sales conversations: question design using SPIN-style sequencing, current-state mapping co-built with the buyer, gap quantification expressed in the buyer's own currency, and call structure that surfaces real buying motivation before any pitch occurs.
- `outbound-strategist` — > Governs signal-based outbound prospecting: ICP definition with falsifiable exclusion criteria, trigger-signal taxonomy ranked by intent strength and decay window, multi-channel sequence architecture matched to buyer persona, and personalization tiering that separates deeply researched effort from broadcast automation.
- `pipeline-analyst` — > Revenue operations pipeline analysis discipline covering health diagnostics, deal velocity mathematics, forecast accuracy methodology, and data-driven sales coaching from CRM data.
- `proposal-strategist` — > Strategic proposal architecture for RFP response and competitive opportunity pursuit.
- `sales-coach` — Rep development, pipeline review facilitation, call coaching methodology, deal strategy, and forecast accuracy for {{PROJECT_NAME}} sales teams.
- `sales-engineer` — | Pre-sales engineering across the full technical evaluation lifecycle: structured discovery to surface architecture context, integration surfaces, security posture, and regulatory constraints; demo engineering built on buyer-documented outcomes rather than feature walkthroughs; POC scoping with written acceptance criteria agreed before the first configuration; and competitive battlecards grounded in verifiable fact.
- `sales-outreach` — > Consultative B2B sales outreach — cold prospecting, lead follow-up, objection handling, proposal-stage messaging, and pipeline management for {{PROJECT_NAME}} sales teams.

_Total in Domain: sales: 9 skill(s)._

### Domain: supply-chain

- `supply-chain-strategist` — Supply chain strategy across sourcing, supplier qualification, demand planning, inventory optimisation, S&OP, lead-time management, freight and carrier strategy, customs and trade compliance, logistics exception and claims management, risk diversification, and ESG traceability compliance for {{PROJECT_NAME}}.

_Total in Domain: supply-chain: 1 skill(s)._

### Domain: trading-hft

- `kill-switches` — Kill-switch and circuit-breaker engineering for HFT systems — independence from order paths, cancel-all flow correctness, position-flatten guarantees, panic dashboards, and term...
- `latency-budgets` — Latency budget engineering for HFT systems — wire-to-wire targets, hot-path discipline (no allocations / no syscalls / no locks), GC pause analysis, NUMA placement, and continuo...
- `order-routing` — Order routing for high-frequency trading systems — venue selection, IOC/FOK semantics, child-order slicing, retry vs.

_Total in Domain: trading-hft: 3 skill(s)._

### Domain: training-l-and-d

- `corporate-training-designer` — > Corporate L&D specialist covering the full instructional-design lifecycle: performance-gap diagnosis, learning-objective authoring at Bloom's taxonomy levels, curriculum architecture with spaced practice, blended-modality selection (synchronous ILT / asynchronous self-paced / SPOC cohort / on-the-job), formative and summative assessment design, and transfer-of- learning measurement via Kirkpatrick four levels and Phillips ROI.

_Total in Domain: training-l-and-d: 1 skill(s)._

### Domain: voice-ai

- `voice-ai-integration` — > Production discipline for voice AI integration covering ASR provider selection (Whisper-large / AssemblyAI / Deepgram / Speechmatics / Google STT) by accuracy, latency, pricing, and language coverage; TTS provider selection (ElevenLabs / OpenAI / Cartesia / Azure Neural / Google Cloud TTS) with latency-to-first-byte and emotional control tradeoffs; real-time streaming via WebRTC and WebSocket with partial transcription and jitter buffer configuration; speaker diarization with error rate budgets; end-to-end latency budgets anchored to hard numbers; conversational state management with barge-in and VAD; fallback handling across provider degradation events; and PII redaction, consent recording, and LGPD/GDPR compliance per jurisdiction.

_Total in Domain: voice-ai: 1 skill(s)._

<!-- END AUTO-GENERATED SKILL INVENTORY -->
```

Há um script helper pra isso:
```bash
python3 .claude/scripts/patch-skill-inventory.py /tmp/new-inv.md \
    .claude/skills/core/ceo-orchestration/SKILL.md
```

### Passo 12 — Validar o squad
```bash
python3 .claude/scripts/validate-squad-contract.py \
    --squad .claude/skills/domains/ledger/
# Esperado: exit 0
```

### Passo 13 — Testes + governance
```bash
python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ -q
# Esperado: todos passam

bash .claude/scripts/validate-governance.sh
# Esperado: PASS
```

### Passo 14 — Atualizar `.github/CODEOWNERS`
Se você tinha CODEOWNERS, adiciona linhas do framework:
```
/.claude/skills/core/         @seu-handle
/.claude/adr/                 @seu-handle
/.claude/plans/PLAN-*.md      @seu-handle
/PROTOCOL.md                  @seu-handle
/CLAUDE.md                    @seu-handle
/SPEC/                        @seu-handle
```

### Passo 15 — Commit incremental
Não commite tudo de uma vez. Separa:
```bash
git add .claude/hooks .claude/scripts .claude/commands
git commit -m "chore(claude): install ceo-orchestration framework — infra (hooks+scripts+commands)"

git add .claude/skills/core .claude/skills/frontend SPEC/ PROTOCOL.md
git commit -m "chore(claude): install ceo-orchestration framework — skills + contracts"

git add .claude/skills/domains/ledger
git commit -m "feat(squad): migrate custom skills into ledger squad"

git add CLAUDE.md .claude/settings.json .claude/team.md
git commit -m "chore(claude): wire CLAUDE.md + team + hooks registration"
```

### Passo 16 — Teste com Claude Code
```bash
cd /caminho/do/adopter-1
claude
```
Mensagem 1:
> "Ativa o protocolo CEO."

Mensagem 2:
> "Lista as skills instaladas e descreve o squad ledger."

Se ele listar suas skills custom corretamente, migração foi bem.

### Se der errado — rollback
```bash
cd /caminho/do/adopter-1
rm -rf .claude
mv .claude.backup-YYYYMMDD-HHMM .claude
mv CLAUDE.md.backup CLAUDE.md 2>/dev/null || true
```

---

## 7. Primeiros 10 minutos pós-install

Checklist pra validar que tudo subiu:

```bash
# 1. Testes verdes (~30s)
python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ -q

# 2. Governance PASS
bash .claude/scripts/validate-governance.sh

# 3. Inventário de skills consistente
python3 .claude/scripts/registry.py list-skills | wc -l
# Esperado: 19+ (core) ou mais dependendo do profile

# 4. CLAUDE.md personalizado (sem {{PLACEHOLDERS}})
grep -c "{{" CLAUDE.md
# Esperado: 0

# 5. Hooks registrados em settings.json
python3 -c "import json; s=json.load(open('.claude/settings.json')); print(list(s.get('hooks',{}).keys()))"
# Esperado: ['PreToolUse', 'PostToolUse'] ou similar
```

Dentro do Claude Code:
```
/status
```
Esse comando tem que responder com snapshot do projeto. Se responder,
framework tá live.

---

## 8. Uso diário — o loop básico

### Toda sessão começa igual
```
/status
```
Vê: último plano ativo, últimos spawns, warnings de CI, health do
framework.

### Pedindo algo
Você NÃO escreve prompt elaborado. Escreve em português natural:

> "Adiciona rate limit de 100req/min no /api/orders"

> "Revisa o checkout antes de eu subir pra produção"

> "Quero redesenhar a página de pricing"

O CEO:
1. Lê o pedido
2. Classifica L1/L2/L3 (quantos módulos mexidos)
3. Se L1/L2 → plano leve, spawna especialista, entrega
4. Se L3+ → propõe plano, roda debate (`/debate start`), ajusta,
   então executa
5. Retorna com output + diff pra você revisar

### Revisando output
Aprova se tá bom. Rejeita com motivo se não. O motivo vira lesson
(`/lesson-review`) — o framework aprende.

### Commit / deploy
Framework **nunca commita sem você pedir**. Quando você pedir:
```
commita isso
```
O CEO roda checklist: testes passaram? lint passou? security review?
Só depois faz `git commit`.

---

## 9. Comandos que você vai usar

### Todo dia
| Comando | O que faz |
|---------|-----------|
| `/status` | Snapshot do projeto — primeiro comando de toda sessão |
| `/spawn "Security Engineer" <task>` | Quando você sabe quem quer |
| `/veto-check <arquivo>` | Checklist formal de code review + security |
| `/pitfall <dominio>` | Antes de feature nova em domínio crítico |

### Toda semana
| Comando | O que faz |
|---------|-----------|
| `/debate start PLAN-NNN` | Pra decisões arquiteturais (schema, migração, nova integração) |
| `/audit-page <url>` | Review de front-end em 16 dimensões |
| `/lesson-review` | Olha o que o sistema aprendeu sobre seus erros/acertos |

### Ocasional
| Comando | O que faz |
|---------|-----------|
| `/agent budget PLAN-NNN` | Quanto cada plano consumiu de token/custo |
| `/architect "<novo domínio>"` | Gera squad (personas + skills + pitfalls) pra domínio novo |
| `/resume PLAN-NNN` | Retoma plano de sessão anterior |
| `/memory-scratchpad` | Memória compartilhada entre agentes no mesmo plano |
| `/skill-review` | Aprovar/rejeitar patches propostos pras skills |
| `/squad-install <tarball>` | Importar squad de terceiro (marketplace) |

### Scripts de shell
```bash
# Query do audit log
python3 .claude/scripts/audit-query.py summary
python3 .claude/scripts/audit-query.py by-skill
python3 .claude/scripts/audit-query.py health

# Dashboard local (SSE em http://localhost:7842)
python3 .claude/scripts/audit-dashboard.py

# Validar governance (roda no CI também)
bash .claude/scripts/validate-governance.sh

# Verificar staleness de docs/plans
python3 .claude/scripts/check-staleness.py
```

---

## 10. Como explicar pro time

### Elevator pitch (30s)
> "O Claude Code sozinho é um freelancer genial mas generalista. Esse
> framework transforma ele num time: um CEO que recebe o pedido, VPs
> que decidem estratégia, especialistas que executam com checklist de
> domínio, e vetos obrigatórios em segurança e code review. Tudo
> rastreável em audit log."

### Pra dev sênior
> "Mesmo Claude, mas cada spawn carrega persona + skill + file
> assignment + checklists do domínio antes de escrever a primeira
> linha. Hooks em Python bloqueiam merge sem review, edit em SKILL.md
> sem sentinel assinado, bash perigoso. Tudo em audit-log.jsonl pra
> você entender DEPOIS por que ele tomou cada decisão. Reduz
> alucinação porque força o modelo a operar dentro de um checklist
> específico em vez de improvisar."

### Pra dev júnior
> "Pensa no Claude como um time de senior engineers. Você não precisa
> saber qual deles chamar — pede em linguagem natural e o 'CEO'
> distribui. Se você pedir 'adiciona um endpoint de login', o CEO
> automaticamente chama o Security Engineer pra revisar (porque login
> é veto-protected). Você vai ver OUTPUT de especialista mesmo sem
> saber pedir pra especialista. É um jeito de aprender padrões de
> produção enquanto produz."

### Pra PM / não-dev
> "Antes: você escrevia a feature em Notion, passava pro dev, virava
> bug em produção. Agora: você escreve no chat, o CEO transforma em
> plano (com checkpoints que você aprova), especialistas implementam,
> um 'quality gate' bloqueia automaticamente se tiver problema de
> segurança ou ausência de teste. Você vê o progresso em `/status`
> sem precisar perguntar 'e aí?' toda hora."

### Regras de ouro pro time (cola no Slack)
1. Sempre começa a sessão com `/status`
2. Pede em natural, não em jargão de agente
3. Quando o hook bloqueia, LEIA a mensagem — ele sabe de algo que
   você não sabe (lição de merda já vivida por alguém)
4. Se o CEO pergunta, responde — ambiguidade vira bug
5. Não commita sem permissão explícita sua
6. Antes de feature sensível (auth/pagamento/PII), roda `/pitfall`
7. Quando rejeita output, **explica o porquê** — vira lesson

---

## 11. Troubleshooting

### "Hook bloqueou meu comando"
Leia a mensagem do hook. 95% das vezes ele tem razão. Exemplos:

- `check_bash_safety bloqueou rm -rf` → mova pra `/tmp/` em vez de
  deletar; se for legítimo, use Bash com `dangerouslyDisableSandbox: true`
  após confirmar que não vai perder dado.
- `check_agent_spawn bloqueou spawn sem SKILL CONTENT` → você (ou o
  CEO) esqueceu de montar o prompt com as 3 seções. Use
  `.claude/scripts/inject-agent-context.sh <Agent> <task>` pra gerar.
- `check_canonical_edit bloqueou edit em SKILL.md` → SKILL.md precisa
  de sentinel assinado. Caminho: abra um plano em `.claude/plans/`,
  pede pro Architect revisar, assina e aplica.

### "CEO spawnou agent e ele falhou"
3 causas comuns:
1. **Skill errada carregada** — CEO escolheu skill X quando a task
   precisava da Y. Solução: você diz explicitamente qual skill.
2. **Contexto incompleto** — agent não tinha acesso aos arquivos
   relevantes. Solução: adiciona referência explícita no pedido.
3. **Task mal especificada** — agent entregou 80% porque pedido
   tinha ambiguidade. Solução: acceptance criteria mais claro.

Em todos os casos: vira **strike** pro agent. 3 strikes = persona é
reescrita.

### "Tests do framework estão falhando"
```bash
python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ -v
```
Se falhar:
- Python < 3.9? Framework exige 3.9+.
- `_lib` imports quebrados? Verifica se `.claude/hooks/_lib/` veio
  no install.
- Fixture faltando? Pode ser merge incompleto em projeto existente —
  refaz passo 5 do install.

### "Audit log vazio"
```bash
ls -la ~/.claude/projects/*/audit-log.jsonl
```
Se não existe, hook `audit_log.py` não está registrado. Verifica
`.claude/settings.json` seção `hooks.PostToolUse`.

### "Tô pagando muito de token"
```bash
python3 .claude/scripts/audit-query.py tokens
```
Geralmente é:
- Debate L3+ desnecessário em task pequena (ajuste blast radius)
- Agent regenerando arquivos inteiros em vez de Edit pontual
  (lesson-review pra corrigir)
- Prompts muito longos por skill inflada (revisa o SKILL.md)

### "Quero desligar"
```bash
mv .claude .claude.disabled
# Ou, pra apenas uma sessão: CEO_SOTA_DISABLE=1 claude
```

### Top docs de referência
- `docs/TROUBLESHOOTING.pt-BR.md` — troubleshooting detalhado
- `docs/FOR-EMPLOYEES.pt-BR.md` — se você é funcionário do Owner
- `docs/GLOSSARY.pt-BR.md` — vocabulário completo
- `PROTOCOL.md` — contrato de governance

---

## 12. Limitações honestas

### O que NÃO é verdade
- **"Multi-agent com expertise real"** — são todos o mesmo LLM. O
  que muda é contexto carregado e checklist enforçado. Um agent com
  skill `financial-correctness` não sabe MAIS de decimal que outro
  agent — ele só é forçado a VERIFICAR sistematicamente. Sem a skill,
  nenhum verificaria.
- **"Review independente"** — agent revisor e agent revisado
  compartilham training data. Viés idêntico. O que funciona é
  perspectiva forçada (security vs performance vs correctness)
  encontrar coisas diferentes, não "independência".
- **"Zero alucinação"** — framework reduz por forçar checklist, mas
  Claude ainda inventa nome de função às vezes. Sempre verifica
  output contra código real (grep / read / tests).

### O que SÓ funciona com disciplina humana
- Code base tem que ser razoavelmente organizado
- Você precisa revisar output, não aceitar cegamente
- `/lesson-review` semanalmente se você quer que o sistema melhore
- ADRs escritos quando decisão é L3+ (CEO lembra, mas você precisa
  aprovar)

### Quando NÃO compensa
- Projeto solo throwaway
- Protótipo de 1 semana
- Time que não quer processo (framework vai frustrar)
- Owner que não lê plano antes de aprovar (aí o framework vira
  teatro)

### Mitigações que o framework tenta
1. Skills são checklists verificáveis, não vibes
2. Output é verificado contra código (grep/read), não opinion
3. Strikes baseados em FATO, não desacordo
4. Owner é a única checagem verdadeiramente independente

---

## 13. Referências

### Docs neste repo
- `README.md` — intro bilíngue (EN + PT-BR)
- `PROTOCOL.md` — contrato de governance (leia uma vez)
- `INSTALL.md` — alternativa mais curta à seção 5 deste guia
- `docs/QUICKSTART.pt-BR.md` — 10min onboarding
- `docs/FOR-EMPLOYEES.pt-BR.md` — para funcionários de time que adotou
- `docs/GLOSSARY.pt-BR.md` — vocabulário completo
- `docs/TROUBLESHOOTING.pt-BR.md` — problemas comuns
- `docs/ROADMAP.md` — futuro do framework
- `docs/BRANCH-PROTECTION.md` — setup de GitHub branch protection
- `docs/audit-dashboard.md` — como rodar o dashboard local
- `docs/provider-pricing.md` — preços dos LLMs pra `/agent budget`

### Arquivos-chave em `.claude/`
- `.claude/team.md` — roster backend + ROUTING TABLE + SKILL MAP
- `.claude/frontend-team.md` — roster frontend
- `.claude/pitfalls-catalog.yaml` — pitfalls universais
- `.claude/task-chains.yaml` — 6 workflows universais
- `.claude/adr/` — 171 Architecture Decision Records
- `.claude/plans/` — planos ativos + arquivo
- `.claude/skills/core/` — 42 skills universais
- `.claude/skills/frontend/` — 8 skills frontend
- `.claude/skills/domains/<squad>/` — squads instalados

### Contratos em `SPEC/v1/`
- `state-stores.schema.md` — backend de estado unificado
- `adapters.schema.md` — adapters LLM (Claude, Gemini, OpenAI, local)
- `normalized_envelope.schema.md` — envelope canônico de request
- `judge-payload.schema.md` — payload do LLM-as-judge
- `scratchpad.schema.md` — memória compartilhada
- `session-graph.schema.md` — grafo derivado de sessões
- `squad-manifest.schema.md` — manifest de squad do marketplace
- `skill-index.schema.md` — índice de skills
- `skill-proposals.schema.md` — patches propostos pra skills

### GitHub
- Repo: https://github.com/Canhada-Labs/ceo-orchestration
- Issues: https://github.com/Canhada-Labs/ceo-orchestration/issues
- Releases: https://github.com/Canhada-Labs/ceo-orchestration/releases

---

## Último conselho

Este framework **amplifica disciplina, não cria disciplina**. Se seu
time já tem boas práticas (code review, ADR, trilha de audit), o
framework vira força multiplicadora. Se seu time é caótico, instalar
o framework vai ser doloroso nas primeiras 2 semanas — vale a pena
mesmo assim, porque o framework força a caminhar pra disciplina por
atrito mecânico (hooks bloqueiam, CEO recusa, Code Reviewer veta).

Quando em dúvida, leia `PROTOCOL.md` — ele é curto, é o contrato, e
resolve 80% das dúvidas de uso.

Boa sorte.
