# ROADMAP — ceo-orchestration (RETIRED — historical only)

> **RETIRED 2026-04-29 (Session 74).** This file is preserved as
> historical context for Sprints 8-11 only. The framework no longer
> publishes a forward-looking roadmap because per ADR-096
> (`vibecoder-only by design`) and PLAN-051 §3 anti-goals, the
> framework entered **reactive maintenance mode** at v1.11.0 GA
> (Session 67, 2026-04-27). No more sprints, no more feature dev —
> only reactive ADRs in response to incidents/audits/security.
>
> **For the current state, do NOT read this file.** Read instead:
>
> - `CLAUDE.md` §6 "Current Work" — most recent session
> - `CLAUDE.md` §CHANGELOG — chronological session log
> - `docs/READINESS-STATUS.md` — current adoption verdict
>   (`MAINTENANCE-MODE-VIBECODER` per ADR-096)
> - `CHANGELOG.md` — release-tagged version log
> - `.claude/adr/` — 97 ADRs (latest: ADR-097)
>
> **Last forward-looking-content snapshot:** v1.7.0-rc.1 (tag
> 2026-04-15), 52 skills, 64 ADRs. The framework has since shipped
> v1.7.0 → v1.8.0 → v1.9.0 → v1.9.1 → v1.10.0 → v1.11.0 → v1.11.1 →
> v1.11.2 (current at Session 74) and reached 53 skills + 97 ADRs.
> None of those increments produced a new roadmap revision; they were
> reactive maintenance. ADR-096 makes that pattern terminal.

## Historical status (pre-Sprint-28, preserved below)

## Status atual: v1.0.0-rc.1 → v1.1.0 → v1.2.0 → v1.3.0-rc.1 (chain; Owner action sequential)

### Sprint 11 (PLAN-011) State-of-the-Art Orchestration adicionou sobre Sprint 10:

- **Phase 0 — Unified State Backend** — `_lib/state_store.py` sqlite
  driver + 3 audit events + SPEC/v1/state-stores.schema.md. Plan-
  scoped filesystem isolation, 64 KiB per-key cap, mandatory
  redaction, TTL + prune. ADR-027.
- **Multi-LLM canonical envelope parity (Phase 1)** — real Gemini
  rewrite + OpenAI + local adapters; SPEC/v1/normalized_envelope +
  adapters.schema + drift detector + credential-hygiene tests.
  CI matrix rotates non-claude adapter per PR (cost cap +500 min/wk
  per H17). ADR-028.
- **Lexical tf-idf retrieval (Phase 2)** — stdlib-only tf-idf baseline
  with 39-pair judgment set; H4 recall@5 gate PASSED (lexical 0.974
  vs static 0.641). `CEO_REAL_EMBEDDINGS=1` hook for Sprint 12.
  `--skill-retrieve` opt-in flag. ADR-029.
- **LLM-as-judge (Phase 3)** — two-pass position-bias; κ calibration
  protocol (N≥50); cross-provider guard; deterministic fallback
  scorer (H7); golden-prompt hash; judge-payload default-deny (H6);
  judge rotation schedule. ADR-030.
- **Self-improving skills (Phase 4, CRITICAL CR1)** — 10-point
  mitigation bundle addressing Unicode bidi / zero-width / homoglyph
  attack surface: scan-injection pre-draft + NFKC-strip preview + AST
  validate + diff <200 + GPG sig + 7-day shadow + hash trailer +
  approval phrase. `check_skill_patch_sentinel.py` + /skill-review.
  ADR-031.
- **N-round debate + Red Team (Phase 5)** — multi-round orchestrator
  with Jaccard 0.7 convergence; Red Team contingent archetype MANDATORY
  if convergence ≤2 rounds (M1 anti-groupthink); M6 secret-redaction
  feed-forward. DEBATE-SCHEMA §12. ADR-032.
- **Token budget kill-switch (Phase 6)** — State 0 advisory;
  `CEO_MAX_PLAN_TOKENS` + `CEO_MAX_SPAWN_TOKENS`; Owner-only
  `CEO_BUDGET_BYPASS=1` with 10/24h rate-limit per H13; /agent-budget
  + budget-summary.py + docs/provider-pricing.md (8/9 rows TBD).
  ADR-033.
- **Shared scratchpad (Phase 7)** — plan-id derived from audit (M2 no
  env spoof); `check_scratchpad_access.py` cross-plan gate;
  /memory-scratchpad namespaced (M8); clear-on-rollback. ADR-034.
- **OpenTelemetry export (Phase 8, CRITICAL CR3)** — HTTPS-only
  allowlist + host allowlist empty-default + double `redact_secrets` +
  drop `description_hash` + `otel_export_dropped` audit; stdlib
  `http.server` smoke receiver. otel-smoke.yml weekly. ADR-035.
- **Output safety (Phase 9)** — 5-step pipeline per H14 (NFKC → ZW
  strip → b64 decode ≤1 → Shannon entropy >4.5 → regex); 7 pattern
  families + Luhn; flag mode default (redact flip Sprint 12 per
  ADR-036 criterion).
- **Load + Chaos (Phase 10)** — thread-based p99 on PR (all hooks
  <225ms); process-based nightly; chaos-inject.py 3-gate lockdown
  (M4: CEO_CHAOS_ALLOWED + pytest parent + cwd); chaos.yml weekly.
  ADR-037.
- **Session graph + /resume (Phase 11)** — strictly-derived from
  audit+git (M3 no new source of truth); 30-day retention (not
  90d); age→gpg→plaintext-WARNING encrypt path; SPEC/v1/session-
  graph.schema.md with reverse map. ADR-038.
- **Squad marketplace (Phase 12, CRITICAL CR2)** — sig-before-parse
  (gpg --verify line precedes tarfile.open line — source-inspection
  test) + refuse symlinks/.. + `squad_allowlist` empty-default +
  revocation ledger + 5MB cap + `squad_imported` audit.
  /squad-install. ADR-039.
- **1529 tests total** (+673 from Sprint 10 baseline 856; target was
  +180 — superou by 493).
- **38 ADRs at Sprint 10 close** (grown to 64 ADRs by Session 44;
  ADRs 027-039 added in Sprint 10, 040-064 in Sprints 12-29).
- **15 SPEC/v1 files** (+6 new).
- **14 slash commands** (+6: /agent-budget, /memory-scratchpad,
  /skill-review, /resume, /squad-install, /debate extended).
- **CEO_SOTA_DISABLE=1** global kill-switch per consensus §S4.

### Sprint 10 (PLAN-010) Quality + Polish adicionou sobre Sprint 9:

- **E2E harness** `tests/integration/` com 17 cenários (TestEnvContext
  obrigatório, filelock contention, governance hooks).
- **Hook profiler measure-only** (`hook-profiler.py`) — baseline macOS
  all p99 <61ms; `perf-profile.yml` weekly. ADR-024.
- **Docs-freshness advisory** — state-machine markdown scanner, 10
  fixtures. ADR-023.
- **Dashboard polish**: 4 painéis + auth + timeout + client cap.
- **3 slash commands**: `/pitfall`, `/veto-check` (JSON), `/lesson-review`.
- **Admin tooling**: `admin-invite.py` + `backup-audit.py` (filelock
  shared, 500MB cap). ADR-001 amended.
- **2 squads**: `edtech` + `government` (52 skills total, 8 squads).
  ADR-025/026.
- **`validate-governance.sh` size_check** (CLAUDE.md <40k).
- **`validate-squad-contract.py`** (ADR-009 mandatory fields).
- **856 tests total** (+128 from Sprint 9 baseline 728).

**Quarterly review** (`docs/docs-freshness-allowlist.txt`): primeiro
ciclo 2026-07-14.

### Sprint 9 adicionou ao v1.0 base:

- **Confidence gate em state 2** (advisory-hook). Owner pode flip
  para state 3 (enforcing) via `CEO_CONFIDENCE_ENFORCE=1` depois de
  coletar 30 dias de FPR baseline (< 5% em 50+ spawns).
- **Pruning knobs**: `--min-miss-ratio`, `--min-age-days`, `--min-archive-age-days`,
  `--force-dangerous-threshold`. ADR-020 supersedes ADR-017.
- **3 novos audit-query sub-commands**: `prune-restore-ratio`,
  `architect-outcomes`, `lessons-effectiveness`.
- **SPEC/v1/audit-query.schema.md** envelope contract.
- **Audit schema v2.3**: consumer enum + lesson_outcome_undone +
  confidence_gate truncated + lesson_outcome inference fields.
- **import_resolves claim kind** (syntactic-only, ADR-018 v1.1).
- **lesson_ranker.py** módulo para effectiveness ranking.
- **728 testes** (+125 desde v1.0 base).
- **ADRs at v1.0 close:** 20 files (2 new + 4 amended in v1.1); repo now has 64.


### O que está shipped (v1.0)

#### Protocolo de governança
- ✅ Session protocol: 3 gates (read → activate → plan)
- ✅ Plan → Debate → Execute workflow
- ✅ Spawn protocol (persona + skill + file assignment)
- ✅ 2 vetos universais (Code Reviewer + Security Engineer)
- ✅ 3-strike policy por agente
- ✅ Anti-collision rules (0/1-3/4+ files in common)
- ✅ Plan lifecycle: draft → reviewed → executing → done

#### Hooks (mechanical governance, Python single-file)
- ✅ `check_agent_spawn.py` — bloqueia spawn sem persona/skill
- ✅ `check_bash_safety.py` — bloqueia `rm -rf`, `git reset --hard`, `push --force`
- ✅ `check_plan_edit.py` — valida transições de lifecycle
- ✅ `check_read_injection.py` — flag conteúdo com pattern de injection
- ✅ `check_canonical_edit.py` — sentinel-gated edits em SKILL.md/team.md
- ✅ `audit_log.py` — PostToolUse observer, grava tudo em JSONL

Todos os 6 usam Adapter Layer (Sprint 6 migration).

#### Skills (42 total)
- ✅ 19 core universais
- ✅ 8 frontend universais
- ✅ 9 fintech domain
- ✅ 3 lgpd-heavy-saas domain
- ✅ 3 trading-hft domain

#### Meta-agents
- ✅ Agent Architect (`/architect` — meta-cria squads)

#### Slash commands
- ✅ `/spawn "<Agente>" <task>`
- ✅ `/debate start|round2|round3|status PLAN-NNN`
- ✅ `/architect "<brief>"`
- ✅ `/audit-page <url>`
- ✅ `/status` (novo v1.0)

#### Scripts / ferramentas
- ✅ `audit-query.py` (14 sub-commands incluindo tokens v1.0)
- ✅ `audit-dashboard.py` (SSE local read-only)
- ✅ `run-skill-benchmark.py` (median-of-3, absolute floor 0.6)
- ✅ `lessons.py` (CRUD + rank + top-K + index)
- ✅ `prune-lessons.py` (dry-run + `--execute` env-gated, Sprint 8)
- ✅ `lesson-restore.py` (reverts archive, Sprint 8)
- ✅ `confidence_gate.py` (advisory claim verification, Sprint 8)
- ✅ `check-staleness.py` (plans/ADRs/benchmarks)
- ✅ `check-tier-boundaries.py` (core/frontend → domains)
- ✅ `check-contamination.sh/.py` (allowlist)
- ✅ `registry.py` (derived manifest of skills + archetypes)
- ✅ `validate-governance.sh` (14-step check)
- ✅ `inject-agent-context.sh` (builds hook-compliant Agent prompts)
- ✅ `status.py` (novo v1.0)

#### Hook adapter layer
- ✅ Contract `_lib/contract.py` (NormalizedEvent + Decision)
- ✅ `adapters/claude.py` (production)
- ✅ `adapters/gemini.py` (stub — deferido Sprint 8+)
- ✅ `_lib/tokens.py` (extractor para audit tokens_in/out)
- ✅ Cross-adapter golden fixtures

#### CI/CD
- ✅ `validate.yml` (governança + contamination + shellcheck + hook/script tests)
- ✅ `coverage.yml` **enforcing 86%** (Sprint 6 Phase 3)
- ✅ `smoke-install.yml` (simula install em repo vazio, paths filter inclui hooks)
- ✅ `release.yml` (7 gates on tag push, OIDC)
- ✅ `benchmarks.yml` (advisory skill benchmarks)
- ✅ `translations-drift.yml` (EN vs PT mirror check)
- ✅ `npm-publish.yml` (OIDC trusted publisher para @ceo-orch/init)
- ✅ `dependabot.yml` (PRs automáticos para action SHAs)

#### SPEC v1 (published contract)
- ✅ `SPEC/v1/audit-log.schema.md` (com tokens_* null semantics; PLAN-025 Batch C: also v2.2+ — confidence_gate, lesson_read, lesson_archived, lesson_restored events)
- ✅ `SPEC/v1/hook-io.schema.md` (hook I/O contract — absorbed event-stream + hook-adapter material in Sprint 14 consolidation)
- ✅ `SPEC/v1/plan.schema.md` (plan frontmatter schema — renamed from `plan-frontmatter.md` in Sprint 14 to match SPEC naming convention)
- ✅ `SPEC/v1/install-cli.md`
- ✅ `SPEC/v1/npm-shim.md`
- ✅ `SPEC/v1/benchmarks.schema.md` (Sprint 8 Phase 5)

#### ADRs (17)
- ADR-001 runtime state dir
- ADR-002 hooks package layout
- ADR-003 branch protection
- ADR-004 bash legacy defer (SUPERSEDED by PLAN-006 Phase 6b)
- ADR-005 event stream v2
- ADR-006 derived registry
- ADR-007 SPEC v1 + SemVer + RC
- ADR-008 Hook Adapter Layer
- ADR-009 squad contract
- ADR-010 canonical-edit sentinel
- ADR-011 event stream v2.1 injection_flag
- ADR-012 cross-adapter fixtures
- ADR-013 squad trading-hft
- ADR-014 hook migration batch policy
- ADR-015 Reflexion v2 outcome loop
- ADR-016 spawn token tracking
- ADR-017 lesson pruning policy (AMENDED Sprint 8 — bounded execute)
- ADR-018 claim grammar (Sprint 8)

#### Docs para humanos (v1.0 new)
- ✅ `docs/QUICKSTART.md` — 10-min onboarding
- ✅ `docs/FOR-EMPLOYEES.md` — regras de engajamento
- ✅ `docs/TROUBLESHOOTING.md` — top issues
- ✅ `docs/GLOSSARY.md` — dicionário de termos
- ✅ `examples/first-session.md` — tutorial narrativo
- ✅ `RELEASE.md` — procedimento de tag pro Owner
- ✅ `.github/release-checklist.md` — checklist operacional

### Métricas
- 537+ unit tests (Sprint 6 baseline; Sprint 7 adds)
- 86% coverage enforcing
- 17 ADRs
- 52 skills
- 3 squads
- 15 docs EN (SSOT) com mirrors PT onde aplicável

## v1.0 closed — não faz mais parte do core

Foram tentados ou considerados, mas descopados para release:

- ❌ Multi-IDE adapter production parity (Gemini/Codex)
- ❌ Lesson-debate round em /debate (separate schema vai sair Sprint 9+)

**Shipped em Sprint 8 (pós-v1 bundle):**
- ✅ ADR-018 claim grammar + confidence gate CLI (advisory)
- ✅ Pruning enforcement (env-gated, capped, restore companion)
- ✅ Agent Architect injeta top-K lessons
- ✅ 2 novos benchmarks core (architecture-decisions, code-review-checklist)

## Pós-v1.0 (quando/se demanda aparecer)

### Sprint 8 — "Learning Loop" ✅ DONE (2026-04-13)

Shipped:
- ADR-018 claim grammar (quoting + code-block exemption + 5 kinds)
- `confidence_gate.py` advisory CLI + `audit-query claims` sub-command
- Pruning enforcement (env-gated + capped + restore)
- Agent Architect lessons injection (task-desc keyword extraction +
  `lesson_read` audit event)
- 2 new benchmarks (architecture-decisions, code-review-checklist)
- 4 new audit events (v2.2)
- CI cost guard + 15-min timeout

### Sprint 9+ — "Continuous hardening"

Foco: usar dados coletados na Sprint 8 pra ajustar e expandir.

**Confidence gate enforcement** — alta prioridade
- Medir FPR em 30 dias de dados Sprint 8
- Se FPR < 15%, promover pra PostToolUse hook (bloqueante opt-in via
  `CEO_CONFIDENCE_ENFORCE=1`)
- Adicionar claim kind `import_resolves` (v1.1)

**Pruning threshold refinement**
- Medir FPR do `--execute` via `lesson_archived` + `lesson_restored`
  events
- Se FPR > 5%, ADR-017 re-opens, rollback execute
- Se FPR < 5%, considerar remover cap + env-gate

**/architect outcome tracking** — pequeno, alto ROI
- Correlate `lesson_read` events com benchmark outcomes
- Classificar hit/miss por lessons injetadas via /architect
- Fecha loop pro Architect path (Sprint 8 fechou só via benchmarks)

**Benchmarks adicionais** — médio valor
- ~~`public-api-design`~~ — **shipped Sprint 9 Phase 4** (10 scenarios)
- `state-machines-and-invariants` — deferido pra Sprint 10 (A24
  Option D: ship 1 por sprint; mede custo CI antes de adicionar +1)
- `financial-correctness-and-math`
- `lesson_effectiveness` derived metric no audit-query

**Lesson-debate schema** — novo esquema
- Separate `.claude/plans/LESSON-DEBATE-SCHEMA.md`
- Agent propõe lesson → 2+ critics reviewam → accept/reject

### Sprint 10+ — "Multi-IDE" (deferido)

Foco: adapters reais, não stub.

**Gemini CLI adapter real**
- Capturar payload real (precisa alguém rodando Gemini)
- Fechar `fixtures/adapters/gemini/GAPS.md`
- Real parity (mesmo contrato que claude.py)

**Codex CLI adapter** (só se houver user real)
- Mesmo processo: capture → fixture → implement

### Sprint 10+ — "Enterprise"

Foco: adoção em empresas reais.

**Squad healthcare-PHI** — LGPD médica
- 5 personas, 3 skills (phi-handling, audit-trail, consent-medical)
- 15+ pitfalls

**Squad edtech** — plataformas educacionais
- Compliance COPPA/LGPD infantil
- Gamification patterns

**Squad government** — sistemas públicos
- Acessibilidade pesada
- Auditoria externa pattern

**Translations ES/ZH** — se estrelas > 50
- Espanhol prioritário (LATAM)
- Mandarim (mercado CN)

**Lighthouse adopters** — 3 projetos externos
- Recruitment contínuo
- Case studies publicados

## Non-goals (explícito — NÃO fazer)

- ❌ SaaS hospedado (framework é self-hosted, cada projeto instala local)
- ❌ Telemetry remoto (privacidade — tudo fica no `~/.claude/projects/`)
- ❌ Charge/licença (framework é open, sem versão paga planejada)
- ❌ Web UI (tudo CLI/file-based por design; dashboard é local SSE read-only)
- ❌ Suporte a outros LLMs além de Claude/Gemini/Codex (Anthropic API
  only; local models = outro projeto)

## Critérios para fechar v1.0 (histórico — fechado 2026-04-12)

Todos os critérios originais de v1.0 foram atingidos. Framework em
uso interno desde `v1.0.0-rc.1` (tag 2026-04-12). Para a rota
atual em direção a v1.7.0 GA, consulte `.claude/plans/PLAN-045/
NEXT-TERMINAL-PROMPT-100.md` (coverage ~54%/72% de Session 46, meta
85-90%/95% code-closable ceiling em Session 49).

- [x] Todos os hooks na Adapter Layer
- [x] Coverage gate enforcing
- [x] Docs para humanos (QUICKSTART + FOR-EMPLOYEES + TROUBLESHOOTING)
- [x] Tutorial end-to-end (`examples/first-session.md`)
- [x] Release procedure (`RELEASE.md`)
- [x] Slash command `/status`
- [x] 64 ADRs (era meta: 17) — dobrado no caminho pós v1.0
- [x] 4400+ tests green (era meta: 537+) — 8× multiplicado
- [x] Dependabot PRs merged (checkout v6, setup-python v6, upload-artifact v7)
- [x] Branch protection ativo
- [x] Tag `v1.0.0-rc.1` (Owner) — 2026-04-12
- [x] 7-day hold — cumprido
- [x] Tag `v1.0.0` stable + posteriores (v1.1..v1.7.0-rc.1)
- [x] Primeiro funcionário onboarded (Owner-dogfood; external adopter
  é PLAN-015 Phase 1 gated em PLAN-045 closure)

## Critérios para fechar v1.7.0 GA (atual)

- [x] PLAN-044 SOTA audit DONE (2026-04-20 Session 39)
- [ ] PLAN-045 SOTA closure → ~85% code-closable ceiling
      (in-flight; Session 46 atingiu ~54%/72%, target Session 49)
- [ ] SP-001..015 promote (2026-04-27 calendar-gated)
- [ ] Owner Session 47 ceremony (round-10 + waves 6/7)
- [ ] ADR-024 State 0→1 perf baseline (2026-05-04 calendar-gated)
- [ ] Session 48 F-04-* closure
- [ ] Session 49 CTO Round 3 verdict SOTA-READY
- [ ] Tag `v1.7.0-rc.2` (Owner)
- [ ] 7-day hold
- [ ] Tag `v1.7.0` GA (Owner)
- [ ] PLAN-015 Phase 1 adopter-1 install unblocked

Quando todos os ✅, v1.7.0 GA cortado e PLAN-015 (adopter-1 real
install) desbloqueado.

## Quem decide prioridades

**Owner** (the maintainer) — decide roadmap, feature cortes, release timing.
**CEO** (Claude) — executa com debate quando L3+, reporta pro Owner
blockers e decisões irreversíveis.
**Funcionários** — feedback via issue ou PR; participam de debate
quando convidados.

## Como contribuir (quando abrir)

Pós-v1.0, contributing flow:
1. Abre issue com `area/<area>` label
2. Owner ou CEO triage + assign
3. PR com `/debate` se L3+
4. Staff Code Reviewer aprova
5. Merge

Por enquanto (pré-v1.0), toda mudança vai via CEO orquestrando.
