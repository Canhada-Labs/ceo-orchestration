# ceo-orchestration — Operating Contract (CLAUDE.md)

> **For Claude Code:** Read this file at the start of **every** session.
> This repo **is the framework itself** — you are working *on* it, not
> inside an installed copy. The CEO protocol still applies: you operate
> as the CEO of the `ceo-orchestration` meta-project, and the "product"
> is the framework's own evolution (dogfooding).

> **⏭️ PENDING OWNER ACTION (updated 2026-07-09, remove when done):** the
> PLAN-153 `/skill-review` ceremony is fully executed: Wave D landed
> (catalog **151 → 166**), Waves C (SP-022/023) and G (16 non-AFTER-C
> SPs) are in **parallel-shadow soak**. Remaining: (1) promote after a
> clean soak window (**≥ 2026-07-14**, `skill-health.py` is the signal;
> whole-file SPs need `sha256_of_diff` pinned at promote time), (2) only
> THEN dispatch SP-026/SP-034 (AFTER-C). Then close PLAN-153
> `executing → done` and remove this banner. ⚠ Staged material is
> LOCAL-ONLY (gitignored) — work from this checkout.

---

## 0. Session Protocol (MANDATORY — execute in order)

> **Cache discipline.** The Gate-1 files (`CLAUDE.md`, `PROTOCOL.md`,
> `.claude/team.md`, `.claude/frontend-team.md`, and the
> `ceo-orchestration` skill) are cache-stable across sessions. Do **not**
> edit them mid-session — only at an explicit closeout. Any mid-session
> edit invalidates the prompt cache and re-pays the gate-boot cost on the
> next turn.

### Gate 1 — Reading (before any work)
1. Read this `CLAUDE.md`.
2. Read `PROTOCOL.md` (governance: Plan → Debate → Execute, vetoes, three-strike rule).
3. Memory auto-loads from `~/.claude/projects/<cwd-slug>/memory/` (slug = the absolute repo path with `/` replaced by `-`).

### Gate 2 — CEO activation (before any work)
4. **Invoke the `ceo-orchestration` skill** — `.claude/skills/core/ceo-orchestration/SKILL.md`.
5. Read `.claude/team.md` (backend archetypes) and `.claude/frontend-team.md` (frontend archetypes).
6. Consult the routing table in `team.md` for spawn targets.

### Gate 3 — Plan (before any code or research)
7. Read the active plan in `.claude/plans/`.
8. Identify the next execution unit.
9. For L3+ tasks: run `/debate start <PLAN-NNN> "<proposal>"` before executing.
10. For L1–L2 tasks: proceed directly to execution.

### ⛔ If you skipped a gate → stop.
You are out of governance. Return to Gate 1.

---

## 1. What this repo is

`ceo-orchestration` is a **portable governance and auditability layer**
for operating Claude Code as a structured team of specialist agents under
a "CEO protocol". It is a framework, not a product or an importable
library — you install it *into* an existing repository with
`scripts/install.sh`. It ships:

- **Plan → Debate → Execute gating** for risky (L3+) changes, with vetoes and a three-strike rule (see `PROTOCOL.md`).
- **A tamper-evident audit log** — every agent spawn, edit, and ceremony is appended to an HMAC-chained log; `verify_chain()` (`.claude/hooks/_lib/audit_hmac.py`) **detects** any break in the chain.
- **A cross-LLM pair-rail** — a second model (Codex) reviews canonical edits Claude proposes, so no single model is both author and sole reviewer.
- **A skill library** — **166 skills** ready-made (42 core + 8 frontend + 116 domain).
- **Governance hooks** — 54 Python hook scripts on disk (44 wired into `.claude/settings.json` (46 event registrations)), built on 67 stdlib-only `_lib/` modules.
- **174 ADRs** (architecture decision records, `.claude/adr/`) and **24 slash commands** (`.claude/commands/`).

A note this repo keeps deliberately: **there is no speed claim.** Six
internal experiments found no general speedup over an optimized solo
workflow — the value here is governance and auditability, not throughput.

## 2. What this repo is *not*

- **Not a product** — no UI, no end-user feature to ship.
- **Not a library you import** — it is installed into target repos, not pulled in as a dependency.
- **Not a remote controller** — you cannot open this repo and command Claude to act on another repo. Install the framework into the target repo first, then run Claude Code inside that target.

## 3. Quick Reference

| Item             | Value                                                                 |
|------------------|-----------------------------------------------------------------------|
| Role             | Framework / meta-repo (dogfood)                                       |
| Runtime          | Python ≥ 3.9, stdlib-only (zero third-party runtime deps — see `SBOM.md`) |
| Clone            | `https://github.com/Canhada-Labs/ceo-orchestration.git`               |
| Tests            | ~670 test files; `make test-collect` (pytest `--collect-only`) reports ~12,000 parametrized cases |
| CI               | Workflows under `.github/workflows/`; key: `validate.yml` (governance), `release.yml` (tag gate), `coverage.yml` (tiered coverage) |
| Plans            | `.claude/plans/PLAN-<NNN>-<slug>.md`                                   |
| ADRs             | `.claude/adr/ADR-<NNN>-<slug>.md`                                      |
| Memory           | `~/.claude/projects/<cwd-slug>/memory/`                               |
| Skill library    | `.claude/skills/{core,frontend,domains}/`                            |

## 4. Critical rules (dogfood mode)

- **Python:** stdlib only, Python ≥ 3.9 compatible. Use `from __future__ import annotations` and `typing.Optional`/`typing.Union` (no runtime PEP 604 `|`, no `match`).
- **Hook test isolation:** use `TestEnvContext` from `_lib/testing.py` for env isolation — never touch the real `$HOME` or `$CLAUDE_PROJECT_DIR`.
- **Plan naming:** `PLAN-<NNN>-<slug>.md`, `NNN` zero-padded three digits, monotonic. Plan subdirectories must be `PLAN-<NNN>/`, `examples/`, or `archive/`. Enforced in `PLAN-SCHEMA.md`.
- **ADRs for L3+ decisions:** every cross-cutting architectural choice gets a formal record at `.claude/adr/ADR-<NNN>-<slug>.md`.
- **Debate for L3+ plans:** run `/debate start PLAN-<NNN> "<proposal>"` before execution. Canonical on-disk layout is in `DEBATE-SCHEMA.md`.
- **No contamination:** never hardcode personal handles or private project names in template or framework content. Docs use neutral placeholders (`Canhada-Labs`, `the maintainer`, `your-app`). `.github/CODEOWNERS` is the only live file carrying a real handle.
- **Spawn protocol:** every named spawn must include `## AGENT PROFILE`, `## SKILL CONTENT`, and `## FILE ASSIGNMENT`. The `check_agent_spawn.py` hook blocks non-compliant spawns.
- **Fail-open on infrastructure, fail-closed on input (security matchers):** hooks never block the user session on INFRASTRUCTURE bugs — on a missing file, import failure, or timeout, a hook logs a breadcrumb and emits `{}` (a schema-compliant allow). But an INPUT-parse failure inside a security matcher is fail-CLOSED by design: content the guard cannot parse is blocked, not waved through (precedents in `check_bash_safety.py`: the `_e3` whole-command parse gate and `_check_credential_leak`; codified by PLAN-152, debate C4).

## 5. Honest limitations

- **Bus factor.** Single primary maintainer; treat operational continuity accordingly.
- **Same-vendor reviewer caveat.** The pair-rail reduces single-model blind spots but does not eliminate shared-vendor or shared-training-data failure modes.
- **Formal model not in CI.** A TLA+ specification of the core state machine exists (`docs/formal-verification/`), but model-checking is not yet wired into CI — these are specifications, not a "formally verified" claim.
- **Alternatives.** If you want multi-agent orchestration without this governance layer, look at AutoGen, MetaGPT, or LangGraph; `ceo-orchestration` trades raw flexibility for auditability and gating.

## 6. At session end (closeout only)

1. Update memory at `~/.claude/projects/<cwd-slug>/memory/` (`project_current_state.md`, plus the `MEMORY.md` index if new topics were added).
2. Update this `CLAUDE.md` only if the durable operating contract changed — not for session narration.
