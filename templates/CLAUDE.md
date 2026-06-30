# {{PROJECT_NAME}} — Master Context

> **For Claude:** Read THIS file at the start of EVERY session.
> Detailed history → `CLAUDE_FULL.md` (if exists)
> **RULE:** When updating CLAUDE.md, ALWAYS update CLAUDE_FULL.md too.

## 0. Session Protocol (MANDATORY — execute in ORDER)

### GATE 1: Reading (BEFORE any work)
1. Read this CLAUDE.md (auto-memory loaded automatically)
2. Read PROTOCOL.md for governance rules (Plan→Debate→Execute, vetoes, 3-strike)

### GATE 2: CEO Activation (BEFORE any work)
3. **INVOKE skill `ceo-orchestration`** — loads CEO protocol (from `.claude/skills/core/ceo-orchestration/SKILL.md`)
4. **Read `.claude/team.md`** (backend) and/or `.claude/frontend-team.md` (frontend)
5. **Consult ROUTING TABLE** in team.md to know who to spawn
6. If a domain profile is installed (e.g. fintech), also read
   `.claude/skills/domains/<domain>/team-personas.md` for the domain-specific personas and VETOes.

### GATE 3: Plan (BEFORE any code/research)
6. Identify findings/tasks and their **Owners**
7. **Spawn NAMED agents** with persona + skill + file assignment
8. Create plan → debate with team → only then execute

### ⛔ IF YOU SKIPPED ANY GATE → STOP
You are violating governance. Go back to Gate 1.

### At session end:
9. Update Session Handoff in the **native auto-memory location**
   (`~/.claude/projects/<slug>/memory/`) — NOT in the legacy repo-root
   `MEMORY.md`. Claude Code auto-loads the native location every
   session. Also update CHANGELOG below.
10. Deploy block copy-paste ready (Owner is not a terminal expert):
```
cd {{PROJECT_PATH}}
git add <SPECIFIC FILES>
git commit -m "<MESSAGE>"
git push origin main
{{DEPLOY_COMMAND}}
```

### GOVERNANCE (inline — does NOT depend on external file)
- **Plan→Debate→Execute:** NEVER execute without a plan debated with the team
- **Owner Routing:** IF a finding has an Owner → SPAWN that agent. Don't do their work
- **3-Strike:** An agent who fails 3× is fired and rewritten
- **CEO Accountable:** If something goes wrong, the CEO failed first
- **Code Review VETO:** any merge requires approval from the staff code reviewer
- **Security VETO:** any auth/crypto/input change requires approval from the security engineer
- **Domain VETOes:** see `.claude/team.md` for project-specific VETO holders (e.g. financial math, PHI, accessibility)

---

## 1. Quick Reference

| Item | Value |
|------|-------|
| Stack | {{STACK}} |
| Runtime | {{RUNTIME_NOTES}} |
| Database | {{DATABASE}} |
| Deploy | {{DEPLOY_TARGET}} |
| Code | {{FILE_COUNT}} files, {{LINES}} lines |
| Tests | {{TEST_COUNT}} tests, {{TEST_TOOL}} |
| Lint | {{LINT_TOOL}}: 0 errors enforced in CI |
| CI | {{CI_TOOL}}: tsc + lint + test on every push/PR |

---

## 2. Architecture

```
{{ARCHITECTURE_DIAGRAM}}
```

---

## 3. Critical Rules

**Numeric:** {{NUMERIC_RULES}} — e.g. "Use a decimal library for financial values, never floats"
**Architecture:** {{ARCHITECTURE_RULES}} — e.g. "Changes touching 3+ modules require ADR"
**Security:** {{SECURITY_RULES}} — e.g. "JWT in httpOnly cookie, never localStorage"
**Agent Safety:** Refactors crossing 3+ files MUST use `isolation: "worktree"`. Background agents (`run_in_background: true`) for parallel tests/exploration.

---

## 4. Key Modules

- **Endpoints:** {{ENDPOINT_LIST}}
- **Database:** {{DB_TABLES}}
- **Env vars:** {{ENV_VAR_COUNT}}

---

## 5. Deploy & Owner Environment

| Item | Value |
|------|-------|
| Project | {{PROJECT_PATH}} |
| Frontend | {{FRONTEND_PATH}} |
| Deploy | {{DEPLOY_TARGET}} |

---

## Instructions for Claude

1. Read CLAUDE.md (§0 Gate 1)
2. **INVOKE skill `ceo-orchestration`** (§0 Gate 2) — MANDATORY for EVERY session
3. **Read `.claude/team.md`** + consult ROUTING TABLE (§0 Gate 2)
4. Plan with team BEFORE executing (§0 Gate 3)
5. ⛔ If you skipped → STOP → go back to Gate 1
6. **DUAL FILE RULE:** Update BOTH CLAUDE.md + CLAUDE_FULL.md (if exists)
7. Owner may not be a terminal expert — step by step, absolute paths, copy-paste ready
8. **Before commit:** ALWAYS run tests. Zero failures.
9. **OBLIGATORY — Save context** at the end of EACH task
10. **OWNER ROUTING:** IF a finding has an Owner → SPAWN that agent. Don't do their work.

---

## CHANGELOG (last 4 sessions — full history in CLAUDE_FULL.md)

### YYYY-MM-DD - Session N — <title>
- **CONTEXT:** What triggered this session
- **WHAT SHIPPED:** 1-3 bullets
- **TESTS:** count, status
- **DEPLOY:** commit SHA
- **NEXT:** what's pending
