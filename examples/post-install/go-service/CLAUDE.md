# acme-gateway — Master Context

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
| Stack | Go 1.22 (modules), net/http + chi router |
| Database | PostgreSQL 16 via pgx (no ORM) |
| Test | `go test ./...` (add `-race` before merge) |
| Lint | `golangci-lint run` + `go vet ./...` (0 findings enforced in CI) |
| Format | `gofmt`/`goimports` — CI fails on unformatted files |
| Build | `go build ./cmd/gateway` |
| Run dev | `go run ./cmd/gateway` (port 8080) |
| CI | GitHub Actions: vet + lint + `go test -race ./...` on every push/PR |

---

## 2. Architecture

```
cmd/gateway/      main.go — wiring only (flags, config, DI, serve)
internal/
  handler/        HTTP handlers (thin — decode, delegate, encode)
  service/        business logic (context-aware, no HTTP types)
  store/          pgx queries + migrations (golang-migrate)
  middleware/     auth, request-id, rate-limit
```

---

## 3. Critical Rules

**Table-driven tests (the house style):** every new function with ≥2
behaviors gets a table-driven test (`tests := []struct{...}` +
`t.Run(tc.name, ...)`). Reviewers VETO one-off copy-pasted test bodies.
**Errors:** wrap with `%w` and context (`fmt.Errorf("load order %s: %w", id, err)`);
never discard with `_` outside tests; sentinel errors compared with
`errors.Is`/`errors.As`, never string matching.
**Context:** every function that does I/O takes `ctx context.Context` as
its first parameter and propagates it. No `context.Background()` below `main`.
**No panics in request paths:** handlers return errors; a recover
middleware exists for defense, not as a control-flow mechanism.
**Concurrency:** any new goroutine has a documented shutdown path;
`go test -race ./...` must pass before merge.
**Before commit:** `go vet ./...` + `golangci-lint run` + `go test ./...` clean.

**CEO rules (standard):**
- Plans live in `.claude/plans/PLAN-<NNN>-<slug>.md`; ADRs for cross-cutting
  decisions in `.claude/adr/`.
- L3+ (auth, store schema, concurrency model changes) → `/debate start` first.
- Refactors crossing 3+ files use `isolation: "worktree"`.

---

## 4. Key Modules

- **Endpoints:** `POST /v1/routes`, `GET /v1/routes/{id}`, `GET /healthz`, `GET /metrics`
- **Database:** `routes`, `upstreams`, `api_keys`
- **Env vars:** 7 (see `.env.example`)

---

## 5. Deploy & Owner Environment

```
cd ~/projects/acme-gateway
git add <SPECIFIC FILES>
git commit -m "<MESSAGE>"
git push origin main
# CI builds the container + deploys on merge to main
```

---

## CHANGELOG (last 4 sessions)

### YYYY-MM-DD - Session N — <title>
- **CONTEXT:** what triggered this session
- **WHAT SHIPPED:** 1–3 bullets
- **TESTS:** count, status
- **NEXT:** what's pending
