# acme-platform — Master Context

> **Sample.** This is what a target repo's `CLAUDE.md` looks like *after*
> `scripts/install.sh <target> --stack node --profile core,frontend` and
> the Owner's first editing pass. It is a rendered example of
> `templates/CLAUDE.md`, not a file the framework consumes.

> **For Claude:** Read THIS file at the start of EVERY session.

## 0. Session Protocol (MANDATORY — execute in ORDER)

### GATE 1: Reading (BEFORE any work)
1. Read this `CLAUDE.md` (auto-memory loads from `~/.claude/projects/<cwd-slug>/memory/`).
2. Read `PROTOCOL.md` at repo root (pointer to the full protocol in your
   ceo-orchestration checkout) — governance: Plan → Debate → Execute, vetoes, 3-strike.

### GATE 2: CEO Activation (BEFORE any work)
3. **Invoke skill `ceo-orchestration`** — `.claude/skills/core/ceo-orchestration/SKILL.md`.
4. Read `.claude/team.md` (backend archetypes) **and**
   `.claude/frontend-team.md` (frontend archetypes) — this monorepo has both.
5. Consult the ROUTING TABLE in `team.md`: `apps/api` + `packages/db` work
   routes to backend archetypes; `apps/web` + `packages/ui` to frontend.

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
  non-compliant spawns. In a monorepo the FILE ASSIGNMENT names packages,
  not just files: two agents never share a package.
- **Code Review VETO:** any merge requires staff code reviewer approval.
- **Security VETO:** any auth/crypto/input change requires security engineer approval.
- **Accessibility VETO:** `apps/web` UI changes require the frontend
  accessibility reviewer (see `.claude/frontend-team.md`).
- **3-Strike:** an agent that fails 3× is fired and rewritten.
- **Commit only when the Owner asks.** Never auto-commit.

---

## 1. Quick Reference

| Item | Value |
|------|-------|
| Stack | pnpm 9 workspaces + Turborepo; TypeScript 5 strict everywhere |
| Apps | `apps/web` (Next.js 14), `apps/api` (Fastify) |
| Packages | `packages/ui`, `packages/db` (Prisma), `packages/config` |
| Test (all) | `pnpm turbo run test` |
| Test (affected only) | `pnpm turbo run test --filter='...[origin/main]'` |
| Type check | `pnpm turbo run typecheck` |
| Lint | `pnpm turbo run lint` (eslint, 0 errors enforced in CI) |
| Run dev | `pnpm turbo run dev` (web :3000, api :3001) |
| CI | GitHub Actions: affected-scope typecheck + lint + test on PR; full graph on main |

---

## 2. Architecture

```
apps/
  web/            Next.js 14 (app router) — imports packages/ui, never apps/api source
  api/            Fastify — imports packages/db, exposes REST for web
packages/
  ui/             shared React components (no app-specific logic)
  db/             Prisma schema + generated client (single source of DB truth)
  config/         shared tsconfig / eslint presets
```

---

## 3. Critical Rules

**Affected-package test scoping (the big one):** during iteration, agents
run `pnpm turbo run test --filter='...[origin/main]'` — the affected
subgraph only, never the full matrix. The FULL `pnpm turbo run test` runs
once before commit and always in CI on main. A green affected run is NOT
a green repo — say which scope you ran.
**Package boundaries:** no cross-package deep imports
(`@acme/ui/src/internal/...` is banned — import the package's public
entry point). Dependency direction: `apps/* → packages/*`, never
package → app, never app → app.
**Single DB truth:** only `packages/db` touches Prisma. Apps consume its
exported client and types.
**Versioning:** shared-package API changes go through a changeset
(`pnpm changeset`) in the same PR.
**Before commit:** full `pnpm turbo run typecheck && pnpm turbo run test`
clean. Zero failures.

**CEO rules (standard):**
- Plans live in `.claude/plans/PLAN-<NNN>-<slug>.md`; ADRs for cross-cutting
  decisions in `.claude/adr/`. A change spanning 2+ packages is L3 by
  default → `/debate start` first.
- Refactors crossing 3+ files use `isolation: "worktree"` — mandatory for
  any cross-package refactor.

---

## 4. Key Modules

- **Endpoints (api):** `POST /v1/projects`, `GET /v1/projects/:id`, `GET /healthz`
- **Pages (web):** `/`, `/projects`, `/projects/[id]`, `/settings`
- **Database:** `projects`, `members`, `activity_log`
- **Env vars:** 12 across both apps (see each app's `.env.example`)

---

## 5. Deploy & Owner Environment

```
cd ~/projects/acme-platform
git add <SPECIFIC FILES>
git commit -m "<MESSAGE>"
git push origin main
# CI deploys affected apps on merge to main
```

---

## CHANGELOG (last 4 sessions)

### YYYY-MM-DD - Session N — <title>
- **CONTEXT:** what triggered this session
- **WHAT SHIPPED:** 1–3 bullets
- **TESTS:** count, status
- **NEXT:** what's pending
