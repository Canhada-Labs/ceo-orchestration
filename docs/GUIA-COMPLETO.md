# Complete Guide — ceo-orchestration

> **PT-BR:** [GUIA-COMPLETO.pt-BR.md](GUIA-COMPLETO.pt-BR.md) (mirror).
>
> **Read this first.** This document is the single entry point. It
> speaks to two audiences at once: non-devs (first two sections) and
> devs (the rest). Each section marks estimated reading time — skip
> what is not for you.

## Map of this document

| Section | For whom | Time |
|---------|----------|------|
| [1. In 2 minutes](#1-in-2-minutes-non-dev) | Non-dev, PM, founder, client | 2 min |
| [2. In 10 minutes](#2-in-10-minutes-dev) | Dev who has never seen the framework | 10 min |
| [3. What it is, what it is not](#3-what-it-is-what-it-is-not) | Everyone | 5 min |
| [4. When to use, when not to](#4-when-to-use-when-not-to) | Dev | 3 min |
| [5. Install in a NEW project](#5-install-in-a-new-project) | Dev | 10 min |
| [6. Install in an EXISTING project](#6-install-in-an-existing-project) | Dev | 20 min |
| [7. First 10 minutes post-install](#7-first-10-minutes-post-install) | Dev | 10 min |
| [8. Daily use — the basic loop](#8-daily-use--the-basic-loop) | Everyone | 10 min |
| [9. Commands you will use](#9-commands-you-will-use) | Everyone | 5 min |
| [10. How to explain it to the team](#10-how-to-explain-it-to-the-team) | Tech lead | 5 min |
| [11. Troubleshooting](#11-troubleshooting) | Dev | reference |
| [12. Honest limitations](#12-honest-limitations) | Everyone | 3 min |
| [13. References](#13-references) | Dev | reference |

---

## 1. In 2 minutes (non-dev)

### The problem
Claude Code (or any code LLM) on its own is a brilliant but generalist
freelancer. It writes code fast, but:

- Skips security steps because "nobody asked"
- Invents numbers and function names that do not exist
- Does 80% of the request and declares "done"
- Leaves no trail for you to audit later

### What the framework does
It turns that freelancer into **a structured team**:

- A **CEO** (Claude itself, in protocol mode) receives the request
- **VPs** decide strategy (Engineering, Product, Operations)
- **Specialists** execute with a domain checklist
- **Automatic vetoes** block merges without code review, without
  tests, or with security issues
- Everything lands in an **audit log** — you understand AFTER why the
  CEO made each decision

### What do you, a non-dev, get?
- You understand what will be done before it is done (plan in plain
  language)
- You can ask "what's the status?" and get an objective answer (`/status`)
- Your team stops shipping features with obvious security bugs
- No need to learn technical terms — the CEO translates the request

### Analogy
> It is the difference between hiring a **freelancer** (fast, no
> process) and hiring an **agency** (account manager, specialized
> team, review before delivery). The framework is the agency.

That is enough for you to decide whether you want your team using
this. If the answer is yes, move to the next section — or hand it to
a dev to read the rest.

---

## 2. In 10 minutes (dev)

### What you get technically

1. **Skills as mechanical checklists.** 160 skills in
   `.claude/skills/core`, `.claude/skills/frontend`, and
   `.claude/skills/domains/<domain>`. Each skill is a `SKILL.md` with
   verifiable rules ("use decimal, not float", "validate CSRF",
   "require unit test for each boundary"). Not "use good judgment".

2. **Spawn Protocol.** Every agent spawn carries
   `## AGENT PROFILE` + `## SKILL CONTENT` + `## FILE ASSIGNMENT`
   before writing the first line. A Python hook
   (`check_agent_spawn.py`) blocks spawns that do not follow the
   format. Result: no more "generic agent with a pretty name".

3. **Mechanical Python hooks.** 31 hooks run on Claude Code's
   `PreToolUse` and `PostToolUse`, including:
   - `check_agent_spawn` — persona+skill required
   - `check_bash_safety` — blocks `rm -rf /`, `git push --force main`, etc.
   - `check_canonical_edit` — edits to `SKILL.md` / `team.md` require a signed sentinel
   - `check_plan_edit` — plans do not change without approval
   - `check_read_injection` — detects prompt injection in files read
   - `audit_log` — writes everything to JSONL

4. **Debate protocol.** For L3+ tasks (3+ modules, schema, auth),
   `/debate start PLAN-NNN` spawns N specialists in parallel critiquing
   the plan. If 2+ flag the same risk, the plan IS adjusted (not a
   suggestion).

5. **Audit log.** Everything in
   `~/.claude/projects/<slug>/audit-log.jsonl`. `audit-query.py` has
   29 subcommands (summary, by-skill, debate, tokens, health, etc.).

6. **Mandatory vetoes.** Staff Code Reviewer vetoes merges without
   clean `tsc/mypy/go vet`. Staff Security vetoes auth changes without
   review. Each domain has its own vetoes (fintech: Staff Quant
   vetoes float in financial math).

7. **SPEC v1.** Schema-validated contracts in `SPEC/v1/` (state-stores,
   adapters, normalized_envelope, judge-payload, scratchpad,
   session-graph, squad-manifest, skill-index, skill-proposals, etc.).
   SemVer enforced.

8. **9929 tests.** `pytest .claude/hooks/tests .claude/scripts/tests`
   runs in ~30s with ≥86% coverage. You can trust the hooks not to
   troll you.

### How it changes your flow

Before:
```
you write an elaborate prompt → Claude interprets however → ships
code → you review → ask for changes → Claude adjusts → you merge
```

After:
```
you write a natural request → CEO turns it into a P0-P4 plan → you
approve → CEO spawns specialist(s) with skill/persona/files →
specialist ships code that already passed the skill checklist → Code
Reviewer vetoes or approves → you merge
```

It feels more "bureaucratic", but total time drops because you stop
the round-trips of "where's the test?", "where's the validation?",
"why is this a float?".

### When the framework pays off
- Task 10min+
- Cross-file or cross-module
- Sensitive domain (auth, payments, healthcare, financial)
- Project with multiple devs (the audit trail is invaluable)

### When it does NOT pay off
- Typo fix
- Rename a local variable
- Log message tweak
- 5-minute experiment you will throw away

For those, use Claude Code directly. Spawn overhead > benefit.

---

## 3. What it is, what it is not

### It is:
- **A portable framework.** Files you install into `.claude/` in your
  project.
- **Opinionated.** Enforces a protocol. You can customize, but not
  ignore.
- **Stdlib-only in Python.** Zero external dependencies in the hooks.
- **Claude Code first.** A Gemini adapter stub exists, but real parity
  is deferred to v2+.
- **Audited.** Every spawn, every decision, every veto becomes a JSONL
  event.
- **Governed by ADR.** 171 ADRs document every architectural decision.

### It is NOT:
- **A product.** No UI, no SaaS, no login.
- **A library.** You do not `npm install` or `pip install`. You run
  an `install.sh` that copies files.
- **A remote controller.** You do NOT open this repo and command
  Claude to work on another repo. You install the framework INTO the
  other repo and open Claude Code there.
- **A substitute for discipline.** If the codebase is chaotic, the
  framework amplifies chaos. It amplifies good discipline; it does
  not create it.
- **Model-independent.** The "agents" are all the same Claude. The
  difference is forced perspective + loaded checklist.

### Essential vocabulary
| Term | Meaning |
|------|---------|
| **CEO** | Claude operating under the protocol, translates a request into a plan |
| **Owner** | You. The only human in the loop |
| **Skill** | `SKILL.md` file with a checklist for a domain (e.g., security-and-auth) |
| **Persona** | An archetype in `team.md` with background + red flags + mantra |
| **Spawn** | When the CEO calls a sub-agent with persona + skill + file assignment |
| **Plan** | `.claude/plans/PLAN-NNN-slug.md` file tracking a feature |
| **Debate** | Parallel spawn of N agents critiquing an L3+ plan |
| **Veto** | Hard block. Staff specialist denies merge until the issue is resolved |
| **ADR** | Architecture Decision Record in `.claude/adr/` |
| **Squad** | Domain bundle (personas + pitfalls + skills). E.g., fintech, edtech, government |
| **Hook** | Python script that runs before/after a Claude tool-call |

---

## 4. When to use, when not to

### Use when:
- The task has blast radius ≥3 files
- The domain is sensitive (auth, payments, financial, healthcare, compliance)
- You need an audit trail for legal/compliance/post-mortem
- Team has 2+ devs and you want standard consistency
- You are building a new product and want good practices from day 1

### Do not use when:
- It is a throwaway 1-hour script
- It is a POC you will discard
- The team is 1 person AND you will never show the code to anyone
- You want the LLM for rubber-duck conversation (use Claude Code directly)

### Kill-switch
If you need to turn everything off:
```bash
mv .claude .claude.disabled
```
Claude Code reverts to operating as a generic assistant. To re-enable:
```bash
mv .claude.disabled .claude
```

---

## 5. Install in a NEW project

### Prerequisites
- Python 3.9+ (`python3 --version`)
- git
- bash or zsh
- Claude Code CLI installed

### Step 1 — Clone the framework
```bash
cd ~
git clone https://github.com/Canhada-Labs/ceo-orchestration.git
```

### Step 2 — Run install in your project
```bash
cd /path/to/your-project
bash ~/ceo-orchestration/scripts/install.sh
```

This installs the `core` profile (42 universal skills + 8 frontend).

### Step 3 — Add a domain profile (if applicable)
```bash
# Fintech (trading, crypto, payments)
bash ~/ceo-orchestration/scripts/install.sh --profile core,fintech

# SaaS with heavy LGPD
bash ~/ceo-orchestration/scripts/install.sh --profile core,lgpd-heavy-saas

# Low-latency HFT trading
bash ~/ceo-orchestration/scripts/install.sh --profile core,fintech,trading-hft

# Edtech
bash ~/ceo-orchestration/scripts/install.sh --profile core,edtech

# Government / public sector
bash ~/ceo-orchestration/scripts/install.sh --profile core,government

# Free-form combinations
bash ~/ceo-orchestration/scripts/install.sh --profile core,fintech,lgpd-heavy-saas
```

### Step 4 — Customize `CLAUDE.md`
Open `CLAUDE.md` at the project root. Replace placeholders:
```
{{PROJECT_NAME}}  → your project name
{{OWNER_NAME}}    → your name
{{PROJECT_PATH}}  → absolute path
```

### Step 5 — Validate
```bash
# Framework tests
python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ -q
# Expected: ~800+ passed, 0 failed

# Governance check
bash .claude/scripts/validate-governance.sh
# Expected: PASS
```

### Step 6 — Open Claude Code and activate
```bash
cd /path/to/your-project
claude
```

On the first message:
> "Activate the CEO protocol."

Claude will read `CLAUDE.md`, `PROTOCOL.md`, load the
`ceo-orchestration` skill, and respond as CEO.

### Step 7 — Test with a small request
> "I want to understand what we have in the project. Give me a summary."

If it responds by describing the project with references to real
files, it is working.

---

## 6. Install in an EXISTING project

> **Common scenario (e.g., adopter-1).** You already have `.claude/`
> with your custom skills, your agents, your `settings.json`. Running
> `install.sh` raw would overwrite your work. Follow this flow.

### Step 1 — FULL backup
```bash
cd /path/to/adopter-1
cp -r .claude .claude.backup-$(date +%Y%m%d-%H%M)
cp CLAUDE.md CLAUDE.md.backup 2>/dev/null || true
cp .github/CODEOWNERS .github/CODEOWNERS.backup 2>/dev/null || true
```

### Step 2 — Inventory what you have
```bash
cd /path/to/adopter-1

# Current structure
find .claude -maxdepth 3 -type d | sort
find .claude -maxdepth 3 -name "*.md" | sort

# Custom skills? Custom agents?
ls .claude/skills/ 2>/dev/null
ls .claude/agents/ 2>/dev/null

# Current settings
cat .claude/settings.json 2>/dev/null
```

Write down on paper:
- Custom skills YOU created (not the framework's)
- Custom agents/personas
- Customized permissions or hooks in `settings.json`
- Existing `CLAUDE.md` (if any)

### Step 3 — Install the framework fresh into a separate directory
```bash
mkdir -p /tmp/ceo-fresh
cd /tmp/ceo-fresh
bash ~/ceo-orchestration/scripts/install.sh --profile core,fintech
# (adjust --profile to your domain)
```

You now have a clean install to compare against.

### Step 4 — Compare fresh vs your project
```bash
diff -rq /tmp/ceo-fresh/.claude /path/to/adopter-1/.claude
```

Typical output lists 3 categories:
1. **Only in `/tmp/ceo-fresh`** — framework files you do NOT have. Copy to the project.
2. **Only in `/path/to/adopter-1`** — YOUR custom files. Keep.
3. **In both (differ)** — conflict. Manual merge.

### Step 5 — Copy what is framework-standard
```bash
cd /path/to/adopter-1

# Hooks (always copy — framework)
cp -r /tmp/ceo-fresh/.claude/hooks .claude/

# Scripts (always copy)
cp -r /tmp/ceo-fresh/.claude/scripts .claude/

# Commands (always copy)
cp -r /tmp/ceo-fresh/.claude/commands .claude/

# ADR template
cp -r /tmp/ceo-fresh/.claude/adr .claude/ 2>/dev/null || cp /tmp/ceo-fresh/.claude/adr/README.md .claude/adr/

# SPEC contracts
cp -r /tmp/ceo-fresh/SPEC .

# Protocol
cp /tmp/ceo-fresh/PROTOCOL.md .
```

### Step 6 — Manual merge of `CLAUDE.md`
If you already had a `CLAUDE.md`:
```bash
# Compare side by side
diff CLAUDE.md.backup /tmp/ceo-fresh/CLAUDE.md
```

Use the framework's `CLAUDE.md` as the base (it has the 3 GATES) and transplant:
- Stack-specific section from your old one (language, tools)
- Domain-specific context from your project
- Historical CHANGELOG (if any)

### Step 7 — Manual merge of `settings.json`
```bash
# See which hooks the framework requires
cat /tmp/ceo-fresh/.claude/settings.json

# Your original settings
cat .claude/settings.json.backup 2>/dev/null || echo "none"
```

Copy the framework's `"hooks"` section into your existing
`settings.json`. Keep your `permissions` and `mcpServers`. If there
is a hook conflict, the framework always wins (framework hooks are
`fail-open` — they will not get in your way).

### Step 8 — Migrate YOUR custom skills to the framework layout
The framework expects this layout:
```
.claude/skills/
├── core/<skill>/SKILL.md            # universals
├── frontend/<skill>/SKILL.md        # frontend universals
└── domains/<your-domain>/           # your domain squad
    ├── team-personas.md
    ├── pitfalls.yaml
    ├── task-chains.yaml
    └── skills/
        └── <custom-skill>/SKILL.md
```

If your custom skill was at `.claude/skills/reconciliation-logic.md`
(flattened, no subdir), reorganize:

```bash
mkdir -p .claude/skills/domains/ledger/skills/reconciliation-logic
mv .claude/skills/reconciliation-logic.md \
   .claude/skills/domains/ledger/skills/reconciliation-logic/SKILL.md
```

Make sure `SKILL.md` has the required YAML frontmatter:
```yaml
---
name: Reconciliation Logic
description: Debit/credit reconciliation in a double-entry ledger with BR edge cases (NFe, PIX delay, reversal).
trigger: When the task involves accounting reconciliation or period close.
---
```

### Step 9 — Create your domain squad (ADR-009 contract)
For each custom domain (e.g., `ledger`), the 3 files are REQUIRED
or the validator will fail:

**`.claude/skills/domains/ledger/team-personas.md`** — domain-specific
personas (e.g., "Staff Accounting Engineer with VETO on double-entry").

**`.claude/skills/domains/ledger/pitfalls.yaml`** — minimum 12
known pitfalls for the domain:
```yaml
- id: ledger-001
  title: "Double-entry without atomic balancing"
  severity: critical
  pattern: "INSERT INTO ledger_entries without a transaction containing both debit AND credit"
  mitigation: "Use explicit tx; validation trigger on insert"
- id: ledger-002
  ...
```

**`.claude/skills/domains/ledger/task-chains.yaml`** — minimum 2
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

### Step 10 — Shortcut: `/architect` generates a squad automatically
If you do not have the 3 files yet, the framework can generate the
scaffolding for you:

Inside Claude Code:
```
/architect "adopter-1: double-entry accounting with BR tax semantics, NFe integration, PIX reconciliation, LGPD-compliant audit trail"
```

It produces the 3 files + suggested skills. Review, adjust by adding
your custom skills, validate.

### Step 11 — Regenerate the skill inventory
```bash
cd /path/to/adopter-1
bash .claude/scripts/generate-skill-inventory.sh > /tmp/new-inv.md

# Patch the ceo-orchestration skill file between the markers:
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

There is a helper script for this:
```bash
python3 .claude/scripts/patch-skill-inventory.py /tmp/new-inv.md \
    .claude/skills/core/ceo-orchestration/SKILL.md
```

### Step 12 — Validate the squad
```bash
python3 .claude/scripts/validate-squad-contract.py \
    --squad .claude/skills/domains/ledger/
# Expected: exit 0
```

### Step 13 — Tests + governance
```bash
python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ -q
# Expected: all pass

bash .claude/scripts/validate-governance.sh
# Expected: PASS
```

### Step 14 — Update `.github/CODEOWNERS`
If you had CODEOWNERS, add the framework lines:
```
/.claude/skills/core/         @your-handle
/.claude/adr/                 @your-handle
/.claude/plans/PLAN-*.md      @your-handle
/PROTOCOL.md                  @your-handle
/CLAUDE.md                    @your-handle
/SPEC/                        @your-handle
```

### Step 15 — Incremental commit
Do not commit everything in one go. Split:
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

### Step 16 — Test with Claude Code
```bash
cd /path/to/adopter-1
claude
```
Message 1:
> "Activate the CEO protocol."

Message 2:
> "List the installed skills and describe the ledger squad."

If it correctly lists your custom skills, the migration was
successful.

### If it goes wrong — rollback
```bash
cd /path/to/adopter-1
rm -rf .claude
mv .claude.backup-YYYYMMDD-HHMM .claude
mv CLAUDE.md.backup CLAUDE.md 2>/dev/null || true
```

---

## 7. First 10 minutes post-install

Checklist to validate everything is up:

```bash
# 1. Tests green (~30s)
python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ -q

# 2. Governance PASS
bash .claude/scripts/validate-governance.sh

# 3. Consistent skill inventory
python3 .claude/scripts/registry.py list-skills | wc -l
# Expected: 19+ (core) or more depending on the profile

# 4. Personalized CLAUDE.md (no {{PLACEHOLDERS}})
grep -c "{{" CLAUDE.md
# Expected: 0

# 5. Hooks registered in settings.json
python3 -c "import json; s=json.load(open('.claude/settings.json')); print(list(s.get('hooks',{}).keys()))"
# Expected: ['PreToolUse', 'PostToolUse'] or similar
```

Inside Claude Code:
```
/status
```
That command must reply with a project snapshot. If it does, the
framework is live.

---

## 8. Daily use — the basic loop

### Every session starts the same
```
/status
```
Shows: last active plan, last spawns, CI warnings, framework health.

### Making a request
You do NOT write an elaborate prompt. You write in natural language:

> "Add a 100req/min rate limit on /api/orders"

> "Review the checkout before I push to production"

> "I want to redesign the pricing page"

The CEO:
1. Reads the request
2. Classifies L1/L2/L3 (how many modules touched)
3. If L1/L2 → lightweight plan, spawn specialist, deliver
4. If L3+ → propose plan, run debate (`/debate start`), adjust, then
   execute
5. Returns with output + diff for you to review

### Reviewing output
Approve if it is good. Reject with a reason if not. The reason
becomes a lesson (`/lesson-review`) — the framework learns.

### Commit / deploy
The framework **never commits without you asking**. When you ask:
```
commit this
```
The CEO runs the checklist: tests passed? lint passed? security
review? Only then runs `git commit`.

---

## 9. Commands you will use

### Every day
| Command | What it does |
|---------|--------------|
| `/status` | Project snapshot — first command of every session |
| `/spawn "Security Engineer" <task>` | When you know who you want |
| `/veto-check <file>` | Formal code-review + security checklist |
| `/pitfall <domain>` | Before a new feature in a critical domain |

### Every week
| Command | What it does |
|---------|--------------|
| `/debate start PLAN-NNN` | For architectural decisions (schema, migration, new integration) |
| `/audit-page <url>` | Front-end review across 16 dimensions |
| `/lesson-review` | See what the system learned from your mistakes/wins |

### Occasional
| Command | What it does |
|---------|--------------|
| `/agent budget PLAN-NNN` | How much each plan consumed in tokens/cost |
| `/architect "<new domain>"` | Generates squad (personas + skills + pitfalls) for a new domain |
| `/resume PLAN-NNN` | Resume a plan from a previous session |
| `/memory-scratchpad` | Shared memory between agents in the same plan |
| `/skill-review` | Approve/reject proposed patches to skills |
| `/squad-install <tarball>` | Import a third-party squad (marketplace) |

### Shell scripts
```bash
# Query the audit log
python3 .claude/scripts/audit-query.py summary
python3 .claude/scripts/audit-query.py by-skill
python3 .claude/scripts/audit-query.py health

# Local dashboard (SSE at http://localhost:7842)
python3 .claude/scripts/audit-dashboard.py

# Validate governance (also runs in CI)
bash .claude/scripts/validate-governance.sh

# Check staleness of docs/plans
python3 .claude/scripts/check-staleness.py
```

---

## 10. How to explain it to the team

### Elevator pitch (30s)
> "Claude Code alone is a brilliant but generalist freelancer. This
> framework turns it into a team: a CEO that receives the request,
> VPs that set strategy, specialists that execute with a domain
> checklist, and mandatory vetoes on security and code review.
> Everything trackable in an audit log."

### For a senior dev
> "Same Claude, but every spawn carries persona + skill + file
> assignment + domain checklists before writing the first line.
> Python hooks block merges without review, edits to SKILL.md without
> a signed sentinel, unsafe bash. Everything in audit-log.jsonl so
> you can understand AFTER why it made each decision. Reduces
> hallucination because it forces the model to operate inside a
> specific checklist instead of improvising."

### For a junior dev
> "Think of Claude as a team of senior engineers. You do not need to
> know which one to call — you ask in natural language and the 'CEO'
> routes. If you say 'add a login endpoint', the CEO automatically
> calls the Security Engineer to review (because login is
> veto-protected). You will see specialist OUTPUT even without
> knowing how to ask for a specialist. It is a way to learn
> production patterns while shipping."

### For a PM / non-dev
> "Before: you wrote the feature in Notion, handed it to the dev,
> it turned into a prod bug. Now: you write in chat, the CEO turns
> it into a plan (with checkpoints you approve), specialists
> implement, a 'quality gate' automatically blocks if there is a
> security issue or a missing test. You see progress in `/status`
> without having to ask 'any updates?' every hour."

### Golden rules for the team (paste in Slack)
1. Always start the session with `/status`
2. Ask in natural language, not agent jargon
3. When a hook blocks, READ the message — it knows something you
   don't (a lesson someone already paid for)
4. If the CEO asks, answer — ambiguity becomes a bug
5. Do not commit without your explicit permission
6. Before a sensitive feature (auth/payments/PII), run `/pitfall`
7. When you reject output, **explain why** — it becomes a lesson

---

## 11. Troubleshooting

### "A hook blocked my command"
Read the hook message. 95% of the time it is right. Examples:

- `check_bash_safety blocked rm -rf` → move to `/tmp/` instead of
  deleting; if legitimate, use Bash with `dangerouslyDisableSandbox: true`
  after confirming you will not lose data.
- `check_agent_spawn blocked a spawn without SKILL CONTENT` → you
  (or the CEO) forgot to build the prompt with the 3 sections. Use
  `.claude/scripts/inject-agent-context.sh <Agent> <task>` to
  generate it.
- `check_canonical_edit blocked an edit on SKILL.md` → SKILL.md
  needs a signed sentinel. Path: open a plan in `.claude/plans/`,
  ask the Architect to review, sign, and apply.

### "CEO spawned an agent and it failed"
3 common causes:
1. **Wrong skill loaded** — CEO chose skill X when the task needed
   Y. Fix: tell it explicitly which skill.
2. **Incomplete context** — agent did not have access to the
   relevant files. Fix: add an explicit reference in the request.
3. **Poorly specified task** — agent delivered 80% because the
   request was ambiguous. Fix: clearer acceptance criteria.

In all cases: it becomes a **strike** against the agent. 3 strikes
= persona rewritten.

### "Framework tests are failing"
```bash
python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ -v
```
If it fails:
- Python < 3.9? Framework requires 3.9+.
- `_lib` imports broken? Check that `.claude/hooks/_lib/` came in
  the install.
- Missing fixture? May be an incomplete merge in an existing project
  — redo step 5 of install.

### "Audit log is empty"
```bash
ls -la ~/.claude/projects/*/audit-log.jsonl
```
If missing, the `audit_log.py` hook is not registered. Check
`.claude/settings.json` `hooks.PostToolUse` section.

### "I'm paying a lot for tokens"
```bash
python3 .claude/scripts/audit-query.py tokens
```
Usually it is:
- Unnecessary L3+ debate on a small task (adjust blast radius)
- Agent regenerating whole files instead of targeted Edit
  (lesson-review to fix)
- Very long prompts due to bloated skills (review the SKILL.md)

### "I want to turn it off"
```bash
mv .claude .claude.disabled
# Or, for a single session: CEO_SOTA_DISABLE=1 claude
```

### Top reference docs
- `docs/TROUBLESHOOTING.md` — detailed troubleshooting
- `docs/FOR-EMPLOYEES.md` — if you are an Owner's employee
- `docs/GLOSSARY.md` — full vocabulary
- `PROTOCOL.md` — governance contract

---

## 12. Honest limitations

### What is NOT true
- **"Multi-agent with real expertise"** — they are all the same
  LLM. What changes is the loaded context and the enforced
  checklist. An agent with the `financial-correctness` skill does
  not know MORE about decimal than another agent — it is just
  forced to VERIFY systematically. Without the skill, none would
  verify.
- **"Independent review"** — reviewer agent and reviewed agent
  share training data. Identical bias. What works is forced
  perspective (security vs performance vs correctness) finding
  different things, not "independence".
- **"Zero hallucination"** — the framework reduces it by forcing
  a checklist, but Claude still invents function names sometimes.
  Always verify output against real code (grep / read / tests).

### What ONLY works with human discipline
- The codebase has to be reasonably organized
- You must review output, not accept blindly
- `/lesson-review` weekly if you want the system to improve
- ADRs written when a decision is L3+ (the CEO reminds, but you
  need to approve)

### When it does NOT pay off
- Solo throwaway project
- 1-week prototype
- Team that does not want process (the framework will frustrate)
- Owner who does not read the plan before approving (then the
  framework becomes theater)

### Mitigations the framework tries
1. Skills are verifiable checklists, not vibes
2. Output is verified against code (grep/read), not opinion
3. Strikes are based on FACT, not disagreement
4. The Owner is the only truly independent check

---

## 13. References

### Docs in this repo
- `README.md` — bilingual intro (EN + PT-BR)
- `PROTOCOL.md` — governance contract (read once)
- `INSTALL.md` — shorter alternative to section 5 of this guide
- `docs/QUICKSTART.md` — 10min onboarding
- `docs/FOR-EMPLOYEES.md` — for employees of a team that adopted it
- `docs/GLOSSARY.md` — full vocabulary
- `docs/TROUBLESHOOTING.md` — common problems
- `docs/ROADMAP.md` — future of the framework
- `docs/BRANCH-PROTECTION.md` — GitHub branch protection setup
- `docs/audit-dashboard.md` — how to run the local dashboard
- `docs/provider-pricing.md` — LLM prices for `/agent budget`

### Key files in `.claude/`
- `.claude/team.md` — backend roster + ROUTING TABLE + SKILL MAP
- `.claude/frontend-team.md` — frontend roster
- `.claude/pitfalls-catalog.yaml` — universal pitfalls
- `.claude/task-chains.yaml` — 6 universal workflows
- `.claude/adr/` — 171 Architecture Decision Records
- `.claude/plans/` — active plans + archive
- `.claude/skills/core/` — 42 universal skills
- `.claude/skills/frontend/` — 8 frontend skills
- `.claude/skills/domains/<squad>/` — installed squads

### Contracts in `SPEC/v1/`
- `state-stores.schema.md` — unified state backend
- `adapters.schema.md` — LLM adapters (Claude, Gemini, OpenAI, local)
- `normalized_envelope.schema.md` — canonical request envelope
- `judge-payload.schema.md` — LLM-as-judge payload
- `scratchpad.schema.md` — shared memory
- `session-graph.schema.md` — derived session graph
- `squad-manifest.schema.md` — marketplace squad manifest
- `skill-index.schema.md` — skill index
- `skill-proposals.schema.md` — proposed skill patches

### GitHub
- Repo: https://github.com/Canhada-Labs/ceo-orchestration
- Issues: https://github.com/Canhada-Labs/ceo-orchestration/issues
- Releases: https://github.com/Canhada-Labs/ceo-orchestration/releases

---

## Final advice

This framework **amplifies discipline; it does not create
discipline**. If your team already has good practices (code review,
ADR, audit trail), the framework becomes a force multiplier. If
your team is chaotic, installing the framework will be painful for
the first 2 weeks — worth it anyway, because the framework pushes
you toward discipline through mechanical friction (hooks block,
the CEO refuses, the Code Reviewer vetoes).

When in doubt, read `PROTOCOL.md` — it is short, it is the contract,
and it resolves 80% of usage questions.

Good luck.
