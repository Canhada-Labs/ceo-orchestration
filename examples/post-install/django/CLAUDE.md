# acme-crm — Master Context

> **Sample.** This is what a target repo's `CLAUDE.md` looks like *after*
> `scripts/install.sh <target>` (default `--stack none`) and the Owner's
> first editing pass. It is a rendered example of `templates/CLAUDE.md`,
> not a file the framework consumes.

> **For Claude:** Read THIS file at the start of EVERY session.

## 0. Session Protocol (MANDATORY — execute in ORDER)

### GATE 1: Reading (BEFORE any work)
1. Read this `CLAUDE.md` (auto-memory loads from `~/.claude/projects/<cwd-slug>/memory/`).
2. Read `PROTOCOL.md` at repo root (pointer to the full protocol in your
   ceo-orchestration checkout) — governance: Plan → Debate → Execute, vetoes, 3-strike.

### GATE 2: CEO Activation (BEFORE any work)
3. **Invoke skill `ceo-orchestration`** — `.claude/skills/core/ceo-orchestration/SKILL.md`.
4. Read `.claude/team.md` (backend archetypes). Django templates are
   server-rendered — no separate frontend team needed here.
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
| Stack | Python 3.12 + Django 5.0 + DRF |
| Database | PostgreSQL 16 (Django ORM) |
| Test | `pytest` (pytest-django; settings via `DJANGO_SETTINGS_MODULE=config.settings.test`) |
| Lint | `ruff check .` + `ruff format --check .` (0 errors enforced in CI) |
| Migrations | `python manage.py makemigrations` / `migrate`; CI runs `makemigrations --check` |
| Run dev | `python manage.py runserver` (port 8000) |
| CI | GitHub Actions: ruff + `makemigrations --check` + pytest on every push/PR |

---

## 2. Architecture

```
config/           settings split: base.py / dev.py / prod.py / test.py
apps/
  accounts/       custom User model, auth
  crm/            contacts, deals, pipelines (core domain)
  api/            DRF viewsets + serializers (thin — no business logic)
```

---

## 3. Critical Rules

**Migrations discipline (the big one):**
- NEVER edit a migration that has been applied anywhere (CI, staging, a
  teammate's machine). Write a new migration instead.
- Every model change ships WITH its migration in the same commit —
  `makemigrations --check` fails CI otherwise.
- Data migrations are separate from schema migrations, and must be
  reversible (`RunPython` with a real `reverse_code`, not `noop`) unless
  the plan explicitly records why not.
- Squashing migrations is an L3 change → debate first.

**ORM:** no raw SQL without security-engineer review; watch N+1 —
`select_related`/`prefetch_related` on any queryset crossing a FK in a loop.
**Settings:** secrets come from env vars only; nothing secret in `config/`.
**Before commit:** `pytest` + `ruff check .` clean. Zero failures.

**CEO rules (standard):**
- Plans live in `.claude/plans/PLAN-<NNN>-<slug>.md`; ADRs for cross-cutting
  decisions in `.claude/adr/`.
- L3+ (auth, schema/migration squash, cross-app refactor) → `/debate start` first.
- Refactors crossing 3+ files use `isolation: "worktree"`.

---

## 4. Key Modules

- **Endpoints:** `/api/v1/contacts/`, `/api/v1/deals/`, `/admin/`, `/healthz`
- **Database:** `accounts_user`, `crm_contact`, `crm_deal`, `crm_pipeline`
- **Env vars:** 11 (see `.env.example`)

---

## 5. Deploy & Owner Environment

```
cd ~/projects/acme-crm
git add <SPECIFIC FILES>
git commit -m "<MESSAGE>"
git push origin main
# CI runs migrations + deploys on merge to main
```

---

## CHANGELOG (last 4 sessions)

### YYYY-MM-DD - Session N — <title>
- **CONTEXT:** what triggered this session
- **WHAT SHIPPED:** 1–3 bullets
- **TESTS:** count, status
- **NEXT:** what's pending
