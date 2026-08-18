# ceo-orchestration — Operating Contract (CLAUDE.md)

> **For Claude Code:** Read this file at the start of **every** session.
> This repo **is the framework itself** — you are working *on* it, not
> inside an installed copy. The CEO protocol still applies: you operate
> as the CEO of the `ceo-orchestration` meta-project, and the "product"
> is the framework's own evolution (dogfooding).

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
- **Governance hooks** — 57 Python hook scripts on disk (46 wired into `.claude/settings.json` (48 event registrations)), built on 68 stdlib-only `_lib/` modules.
- **194 ADRs** (architecture decision records, `.claude/adr/`) and **27 slash commands** (`.claude/commands/`).

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
| Tests            | ~730 test files; `make test-collect` (pytest `--collect-only`) reports ~14,000 parametrized cases |
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
- **Spawn protocol (claim rewritten S307 — PLAN-178 Lote B landed, ADR-191 ACCEPTED):** every named spawn carries `## AGENT PROFILE`, `## SKILL CONTENT` (or `## SKILL REFERENCE` with `@path sha256=<hex>` body), `## PROMPT DEFENSE` (≥6 bullets when the task touches untrusted content), and `## FILE ASSIGNMENT` in the ADR-191 grammar (`- CAN edit: <concrete paths>` or `- CAN edit: NONE-READ-ONLY`; globs/placeholders taint the whole declaration). What `check_agent_spawn.py` mechanically BLOCKS today: missing skill material, missing prompt-defense, and — ONLY under `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1`, currently UNSET (measure-first window) — absent/unparseable FILE ASSIGNMENT. `## AGENT PROFILE` remains a named-spawn DETECTION strategy, not an enforced section. FILE ASSIGNMENT omission is VISIBLE now: every named spawn emits `spawn_file_assignment_recorded` (`path_count=0` on omission/read-only/tainted) — the collision rail sees all spawns. The enforce flip + `CEO_SPAWN_OVERLAP_GUARD` are a FUTURE ceremony gated on the advisory window (≥30d or ≥20 sessions, would-block/TP-FP table). Recovery route: `CEO_SOTA_DISABLE=1` forces advisory. Generate prompts via `inject-agent-context.sh` (`--files=a,b` or read-only default), never by hand.
- **Install/upgrade ownership is ONE decision, not a cascade (PLAN-167, landed `7c0828a`; PLAN-168 closed the follow-ups).** Whether the framework owns `PROTOCOL.md`, `SPEC/v1` or `.claude/.framework-version` is answered by `_ownership_verdict()` in `scripts/_framework_manifest_set.sh` — a pure function of 10 dimensions returning `"<VERDICT> <HASH_SOURCE>"`. `install.sh` and `upgrade.sh` **observe → call → execute**; they do not decide. Contract: `docs/ownership-decision-table.md`. Truth: `scripts/tests/ownership_table.tsv`. Two oracles read that same table — a unit one (`test-ownership-verdict-unit.sh`, milliseconds: catches a wrong DECISION) and an e2e one (`test-ownership-table.sh`, ~25 min of real installs: catches a wrong OBSERVATION), plus the INV-4 e2e (`test-protocol-pointer-inv4.sh`: install and upgrade render the pointer through the ONE shared generator — byte-identical, degraded bodies CURED with backup, adopter edits preserved). CI: the unit oracle + fast controls run per-PR in `smoke-install.yml`; the full e2e runs in `ownership-nightly.yml`, whose gate (`ownership-nightly-gate.sh`) compares the exact RED id set against `ownership-expected-reds.txt` and fails on ANY difference. **The e2e ends 62 green / 3 red by design** (`OWN-0024`/`0027` test defects, `OWN-0016` product — causes in ADR-190; `OWN-0074` was closed by PLAN-168 W2). An all-green run means the table changed — stop and find out why. Adding a branch that decides ownership locally re-opens the class this replaced.
- **Fail-open on infrastructure, fail-closed on input (security matchers):** hooks never block the user session on INFRASTRUCTURE bugs — on a missing file, import failure, or timeout, a hook logs a breadcrumb and emits `{}` (a schema-compliant allow). But an INPUT-parse failure inside a security matcher is fail-CLOSED by design: content the guard cannot parse is blocked, not waved through (precedents in `check_bash_safety.py`: the `_e3` whole-command parse gate and `_check_credential_leak`; codified by PLAN-152, debate C4). **Deliberate exception (ADR-186):** the canonical-edit matcher's per-invocation wall deadline is fail-CLOSED — a timeout *there* is an incomplete verification, not infrastructure; the recovery route is the provenance-pinned unlock (`CEO_SENTINEL_UNLOCK` + `CEO_SESSION_ANCHOR_SHA` or `CEO_SENTINEL_UNLOCK_SHA256`).

## 5. Honest limitations

- **Pair-rail decision gate (curado no trem rc.4 — PLAN-177, re-pass t2..t13; fechado 2026-08-16, GA cortado 2026-08-17).** Os DOIS validadores exigem `verdict ∈ {GO, GO-WITH-CONDITIONS}` fail-closed: `.github/scripts/validate-pair-rail-verdict.py` (exit 3; defesa em profundidade — `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` põe `continue-on-error` no step) e `.claude/scripts/local/_release_tag_guard.py` (`E_DECISION=13`; o enforcement em TODOS os modos — sem continue-on-error, invocado por `release.sh tag` com `|| die`). O re-pass do candidato rc.4 reabriu e CUROU a classe fence-shadow em rodadas sucessivas: abridor canônico (t9), **fechador canônico + exit 3 para conteúdo rejeitado + controle de CR em leitura raw on-disk** (t10, com controle positivo em bytes — `read_text()` não vê mais o CR antes do regex), **first-fence binding** nos twins (t12). Malformado/duplicado/desconhecido ⇒ rejeição nomeada, nunca INFRA — agora com teste combinatório de fence e o argv literal do step-15 em `test_release_bump_sites.py`. **Residual declarado NO material assinado do GA (R1):** fence-shadow variante 5 (bloco yaml escondido em comentário HTML cru pelo PRÓPRIO signatário de um envelope Owner-GPG-signed) está fora do threat model (signer == Owner); cura definitiva = envelope de formato fixo nos DOIS twins, item nomeado da v1.4.0. A checagem `GO`-exato do `OWNER-GA-CUT.sh` é OUTRA superfície (saída bruta do rail), deliberadamente mais estrita — as duas coexistem por design.

- **Continuidade de compaction NÃO entrega (ADR-153 — fires-proof cumprido e NEGATIVO, S309 2026-08-16).** O autocompact real de 09:34Z disparou os dois hooks e entregou nada: `snapshot_outcome=scratchpad_unavailable`, `plan_id=unknown`, `snapshot_found=false`, `pointer_count=1`. Causa ESTRUTURAL: `resolve_plan_id` exige um `plan_transition` **da própria sessão**, e transição só ocorre em mudança de status — censo real: **2 eventos em 12.515 linhas**, ambos de outra sessão. A continuidade só funciona em sessões CURTAS, anti-correlacionada com o próprio caso de uso. O "residual risk #3" do ADR-153 é o caminho DOMINANTE, não a borda. Some-se: nada ESCREVE memória (`SessionEnd.py` só verifica gravabilidade), e o piso de thrashing deste repo é `T ≈ 60k` — **abaixo do mínimo que a API permite** (`trigger.value=50000`), com `F`(Gate 1+2 + índice) ≈ 45–55k. Cura desenhada em **PLAN-179** (W0–W4, `draft`; GA v1.3.0 saiu 2026-08-17 — debate L3 iniciado na S312, execução após `design-coherent` + review do Owner); inclui **Constraint Pinning** — ponteiro NÃO é restrição, e compactação apaga governança (medido em outro setup: 0% → 30–59% de violação). Não tratar `additionalContext` em PostCompact como canal provado: sonda pendente (W0-1).

- **Rail Workflow fora do gate de spawn (MITIGADO — PLAN-178 Lote B, S307).** `agent()` de Workflow segue NÃO passando pelo `check_agent_spawn` (probe `wf_d7af49d9`: `blocked=false` — limite do substrato), mas as 4 skills Workflow shipadas agora validam a gramática REDUZIDA do ADR-191 PRÉ-despacho no próprio script (bloco COMMON byte-idêntico: PROMPT DEFENSE ≥6 + FILE ASSIGNMENT explícito + HARD-RULES marker; mecanismo provado em `wf_f2707efc`) e todo ingest de retorno inter-agente é fenced + capped 24000 com truncamento envenenando a dimensão dona. Residual: um workflow NOVO que esqueça o bloco COMMON nasce descoberto (ADR-191 §4); fan-out que ESCREVE segue fora do Workflow até existir gate no substrato.
- **Bus factor.** Single primary maintainer; treat operational continuity accordingly.
- **Same-vendor reviewer caveat.** The pair-rail reduces single-model blind spots but does not eliminate shared-vendor or shared-training-data failure modes.
- **Formal model not in CI.** A TLA+ specification of the core state machine exists (`docs/formal-verification/`), but model-checking is not yet wired into CI — these are specifications, not a "formally verified" claim.
- **Alternatives.** If you want multi-agent orchestration without this governance layer, look at AutoGen, MetaGPT, or LangGraph; `ceo-orchestration` trades raw flexibility for auditability and gating.

## 6. At session end (closeout only)

1. Update memory at `~/.claude/projects/<cwd-slug>/memory/` (`project_current_state.md`, plus the `MEMORY.md` index if new topics were added).
2. Update this `CLAUDE.md` only if the durable operating contract changed — not for session narration.
