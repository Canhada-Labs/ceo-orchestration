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

1. **Skills as mechanical checklists.** 151 skills in
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
# ...
# <!-- END AUTO-GENERATED SKILL INVENTORY -->
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
