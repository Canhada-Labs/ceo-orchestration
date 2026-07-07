# acme-api — Master Context

> **Sample.** This is what a target repo's `CLAUDE.md` looks like *after*
> `scripts/install.sh <target> --stack node` and the Owner's first editing
> pass (placeholders filled in). It is a rendered example of
> `templates/CLAUDE.md`, not a file the framework consumes.

> **For Claude:** Read THIS file at the start of EVERY session.

## 0. Session Protocol (MANDATORY — execute in ORDER)

### GATE 1: Reading (BEFORE any work)
1. Read this `CLAUDE.md` (auto-memory loads from `~/.claude/projects/<cwd-slug>/memory/`).
2. Read `PROTOCOL.md` at repo root (pointer to the full protocol in your
   ceo-orchestration checkout) — governance: Plan → Debate → Execute, vetoes, 3-strike.

### GATE 2: CEO Activation (BEFORE any work)
3. **Invoke skill `ceo-orchestration`** — `.claude/skills/core/ceo-orchestration/SKILL.md`.
4. Read `.claude/team.md` (backend archetypes). This repo has no frontend.
5. Consult the ROUTING TABLE in `team.md` for spawn targets.

### GATE 3: Plan (BEFORE any code/research)
6. Read the active plan in `.claude/plans/` (naming: `PLAN-<NNN>-<slug>.md`,
   `NNN` zero-padded, monotonic — schema in `.claude/plans/PLAN-SCHEMA.md`).
7. For L3+ tasks: run `/debate start PLAN-<NNN> "<proposal>"` before executing.
8. For L1–L2 tasks: proceed directly to execution.

### ⛔ IF YOU SKIPPED ANY GATE → STOP
You are out of governance. Go back to Gate 1.

### GOVERNANCE (inline — does NOT depend on external file)
- **Plan → Debate → Execute:** never execute an L3+ change without a debated plan.
- **Spawn protocol:** every named spawn includes `## AGENT PROFILE`,
  `## SKILL CONTENT`, and `## FILE ASSIGNMENT` — `check_agent_spawn.py` blocks
  non-compliant spawns.
- **Code Review VETO:** any merge requires staff code reviewer approval.
- **Security VETO:** any auth/crypto/input change requires security engineer approval.
- **3-Strike:** an agent that fails 3× is fired and rewritten.
- **Commit only when the Owner asks.** Never auto-commit.

---

## 1. Quick Reference

| Item | Value |
|------|-------|
| Stack | Node.js 20 + TypeScript 5 (strict) + Fastify |
| Database | PostgreSQL 16 via Prisma |
| Test | `npm test` (vitest) |
| Type check | `npx tsc --noEmit` |
| Lint | `npm run lint` (eslint, 0 errors enforced in CI) |
| Run dev | `npm run dev` (port 3000) |
| CI | GitHub Actions: tsc + lint + test on every push/PR |
| Pre-commit | tsc + vitest gate (installed by the `--stack node` overlay) |

---

## 2. Architecture

```
src/
  routes/       Fastify route handlers (thin — validate, delegate, reply)
  services/     business logic (no HTTP types in here)
  db/           Prisma schema + client wrapper
  middleware/   auth, rate-limit, request-id
```

---

## 3. Critical Rules

**TypeScript:** `strict: true` stays on. No `any`, no `@ts-ignore`, no
non-null `!` in new code — the code reviewer VETOes them.
**Validation:** every route body/query is schema-validated at the edge
(Fastify JSON schema). Services receive typed, validated input only.
**Errors:** never swallow a rejected promise; handlers return typed error
envelopes, never raw stack traces.
**Layering:** routes must not import Prisma directly — go through `services/`.
**Before commit:** `npx tsc --noEmit` + `npm test` both clean. Zero failures.

**CEO rules (standard):**
- Plans live in `.claude/plans/PLAN-<NNN>-<slug>.md`; ADRs for cross-cutting
  decisions in `.claude/adr/`.
- L3+ (auth, schema, cross-module refactor) → `/debate start` first.
- Refactors crossing 3+ files use `isolation: "worktree"`.

---

## 4. Key Modules

- **Endpoints:** `POST /api/v1/orders`, `GET /api/v1/orders/:id`, `GET /healthz`
- **Database:** `orders`, `customers`, `idempotency_keys`
- **Env vars:** 9 (see `.env.example`)

---

## 5. Deploy & Owner Environment

```
cd ~/projects/acme-api
git add <SPECIFIC FILES>
git commit -m "<MESSAGE>"
git push origin main
# CI deploys on merge to main — no manual deploy step
```

---

## CHANGELOG (last 4 sessions)

### YYYY-MM-DD - Session N — <title>
- **CONTEXT:** what triggered this session
- **WHAT SHIPPED:** 1–3 bullets
- **TESTS:** count, status
- **NEXT:** what's pending
