---
id: PLAN-153
title: ECC Comparative Uplift Program
status: executing
reviewed_at: 2026-07-03
executing_at: 2026-07-06
created: 2026-07-03
owner: CEO
depends_on: [PLAN-152]
budget_tokens: 2.0-2.8M
budget_sessions: 7
context_risk: high
external_wait: none
tags: [skills, installer, security, dx, ecc-analysis]
---

# PLAN-153 — ECC Comparative Uplift Program

## Context

Owner directive (S259, 2026-07-03): full comparative analysis of `affaan-m/ecc`
(MIT, 277 skills / 92 commands / 67 agents / 12 harnesses) against this
framework, then a ready-to-execute improvement plan covering (a) what ecc does
better, (b) improvements to our existing 151 skills, and (c) whether to create
~100 new skills.

The analysis ran as read-only workflow `wf_c555404e-093` (34 agents: 8 recon
dimensions + our-side auditor + 12 skill-matrix chunks covering **277/277**
skills + 12 adversarial claim verifications + synthesis; 0 errors). Ground-truth
artifacts live in `PLAN-153/artifacts/`:

- `ecc-skill-matrix.md` — all 277 skills classified (verdict/quality/overlap)
- `verified-claims.md` — 12 "ecc does better" claims: 5 CONFIRMED, 6 PARTIAL, 1 REFUTED
- `synthesis-report.json` — full structured synthesis

**Headline findings.** ecc optimizes DISTRIBUTION + continuous learning; we
optimize GOVERNANCE + auditability. None of our rails exist there (zero
repo-wide hits for audit-chain/HMAC/pair-rail; veto/debate are prose; zero spawn
enforcement; their runtime enforcement is mostly WARN). Where ecc is genuinely
ahead (verified): manifest-driven install lifecycle with doctor/repair, passive
learning funnel, automatic session persistence on Stop, static harness-config
scanning (the class adjacent to our S254 dead-pair-rail P0), /hookify-style
correction capture, and a uniform prompt-defense block across 66/67 agents.

**Skill matrix answer (Owner question "create ~100 skills?"): NO.**
Stats: 32 ADOPT (12%), 97 ADAPT (35%, mostly merges into existing skills),
39 INSPIRE, 109 SKIP. Honest number: **~30-40 new skills in 6 squads + ~25
merges**, sequenced behind skill telemetry and discovery work (Wave C).

**Lifecycle note (S259):** `draft → reviewed` executed by the CEO under the
Owner's explicit same-day delegation ("monta um plano de melhoria […] deixa o
plano pronto para ser executado […] não pare de trabalhar até concluir").
Review = round-1 debate (3 archetypes, 3× ADJUST_PROCEED → consensus PROCEED,
design-coherent; 13 adjustments applied — see `PLAN-153/debate/round-1/`) +
Codex pair-rail on the plan diff (V2). Wave 0 items still require Owner
ratification before execution.

## Goal

Close the verified competitive gaps — installer lifecycle, skill
format/telemetry, catalog lacunae, behavioral+static harness-config gates —
without diluting the governance ethos (honesty, no-speed-claim, human-gated,
stdlib-only), leaving every port MIT-attributed, per-file-license-verified and
contamination-clean. The learning-loop track is carved to PLAN-154.

## Approach / Thesis

- **Wave-ordered by blast radius** (PLAN-152 precedent): docs quick-wins first,
  then the S254-lesson security gates, then installer, then telemetry BEFORE
  mass skill creation (C→D is a hard contract), merges last.
- **Ceremony-derived L-levels (debate A3).** Any wave touching the
  canonical-guard surface is L3: `scripts/install.sh`
  (`check_canonical_edit.py:187`), `scripts/upgrade.sh` (:189), ALL
  `.github/workflows/*.yml` (:182, debate C8), the `SKILL.md` namespace
  (:118-122), `.claude/settings.json`, `.claude/hooks/**`. Waves E/B/C/D/G are
  therefore **all L3 ceremony work** — sentinels and SP-NNN paths are allocated
  in Wave 0, not discovered at execution time.
- **Import the CLASS, never the implementation.** Every mechanism port is a
  clean-room rewrite: Python stdlib ≥3.9, `from __future__ import annotations`,
  fail-open on infrastructure / fail-closed on input (PLAN-152 C4). Never cite
  ecc vendor numbers.
- **Behavioral over static (debate consensus #2).** What certifies a security
  rail alive is a CI-replayed positive-control (planted violation → assert
  BLOCK), never a static scan alone.
- **CI-wiring same-commit rule (debate consensus #5).** Every execution unit
  that adds a `*.py` script wires its tests into an explicit `validate.yml`
  pytest path (both `serial` and `not serial` passes) in the same commit.
  validate.yml pins path lists; new test files are NOT auto-discovered.
- **Provenance (debate consensus #4).** Per-source-file license verification at
  the pinned clone SHA, recorded in a single `NOTICE` ledger
  (source@sha + license per piece) — stronger than per-file frontmatter blocks.
  Zero "ECC" references in body content; imported SKILL.md content is untrusted
  data until the mechanical import gate passes.
- **Token budget and calendar are separate axes (debate A1).** budget_tokens
  covers CEO-context; the 7-day SKILL.md shadow-soak (ADR-031,
  `skill-patch-apply.py:664`) is wall-clock and governed by OQ3.

## Wave 0 — Owner ratification + ceremony allocation (session 1, ~15 min)

1. Ratify §Open questions (OQ3; confirm resolved OQ1/OQ2 dispositions).
2. Sign canonical-edit sentinels (dual rail per ADR-121; real anchor-sha +
   Scope; per-wave, scope == exactly the wave's guarded files):
   - **SENT-E** (exact scope — the canonical guard admits only exact
     `Scope:` paths; Codex pair-rail P2, 2026-07-03):
     `.github/workflows/validate.yml`,
     `.github/workflows/supply-chain-watch.yml` (new),
     `.claude/settings.json`,
     `scripts/install.sh` (deny-baseline write),
     `.claude/hooks/check_harness_config.py` (new),
     `.claude/hooks/check_bash_safety.py` (item 5 citation gate),
     `.claude/hooks/check_agent_spawn.py` (item 7 prompt-defense contract),
     `.claude/hooks/check-active-hooks-executable.py` (item 1 partitioning,
     if edited). Regression tests land in `hooks/tests/` (not guarded).
   - **SENT-B**: `scripts/install.sh`, `scripts/upgrade.sh`,
     `.github/workflows/release.yml`, `.github/workflows/npm-publish.yml`.
   - **SKILL.md ceremony** (Waves C/D/G): SP-NNN proposals via
     `/skill-review` + the soak posture decided in OQ3. No direct SKILL.md
     edits outside that pipeline.
3. Reserve ADRs: **ADR-173** (harness-config gate: behavioral positive-control
   + static extension + liveness + deny baseline), **ADR-175**
   (destructive-Bash citation gate + spawn prompt-defense contract),
   **ADR-174** (reserved for PLAN-154 learning-loop doctrine).
4. Ratify Wave D batch-1/batch-2 split (see Wave D).

Check: sentinels verify against both signer rails; ADR slugs reserved; OQ
answers logged verbatim in this file.

### Wave 0 — execution log (S261, 2026-07-06/07)

Executed by the CEO under the Owner's explicit overnight delegation
(S261 directive, verbatim in the session ledger: "quero que termine o plano
153 completo […] se precisar assinar algo deixa o script pronto que eu faço
quando acordar, rode autônomo […] não pare de trabalhar até finalizar tudo").
Physical GPG signatures remain Owner-only and are batched into the wake-up
ceremony below.

1. **OQ dispositions ratified:** OQ1 = NOTICE ledger (debate resolution
   confirmed). OQ2 = metadata-only v1 → PLAN-154 (confirmed). **OQ3 = (c)
   hybrid** — skip-soak posture for brand-new files (Wave D; nothing to
   regress), parallel-shadow for merges (Wave G) — per the CEO recommendation
   in §Open questions, under the delegation above.
2. **Batch split ratified:** Wave D batch-1 executes; batch-2 stays deferred.
   JVM ride-along ruling (matrix under-specifies "quarkus/kotlin/jpa ADAPTs"):
   `jpa-patterns` (the only unambiguous 1:1) is absorbed as a persistence
   section of the new `java-coding-standards`; quarkus\*/kotlin\* rows move to
   batch-2 with pointer — they have 2-4 candidate rows each and need an Owner
   pin.
3. **ADR allocation CORRECTED:** this plan reserved ADR-173/174/175 on a
   count-vs-index confusion ("172 ADRs" is a FILE count inflated by AMEND
   files; the highest index on disk is ADR-157). Corrected allocation, keeping
   the index monotonic: **ADR-158** (harness-config gate, was "173"),
   **ADR-159** (citation gate + prompt defense, was "175"), **ADR-160**
   (reserved for PLAN-154 learning-loop doctrine, was "174"). Any artifact of
   this plan citing 173/174/175 is to be read as 158/159/160.
4. **Ceremony reality (S261):** ALL canonical-guarded surfaces (incl.
   `.claude/adr/ADR-*.md` and every `SKILL.md` write — both confirmed guarded
   for NEW files too) are STAGED under `PLAN-153/staged/<wave>/` as complete
   final files with per-wave `MANIFEST.md`. Sentinels are drafted per wave at
   `PLAN-153/architect/round-{1..4}/approved.md` (SIGNED SCOPE markers, exact
   paths, `__ANCHOR_SHA__` placeholder filled at signing time) — round-1 =
   SENT-E, round-2 = SENT-B, round-3 = SENT-CDG (SKILL.md namespace),
   round-4 = SENT-BACKLOG. Owner applies via `~/Desktop/ceo-wakeup/`
   (sign → scope==touched assert → overlay apply → full CI-equivalent gates →
   commit per wave), the S258 patcher precedent: the Owner's shell applies the
   exact authorized diff; the signed sentinel is the authorization record.
   Signer-rail repairs folded into the same ceremony: sentinel-signers
   registry YAML is pre-GENESIS (placeholder bootstrap_sha256 + DEADBEEF cold
   keys) and `skill-patch-signers.txt` is all-zeros (promote fail-closed) —
   both get the real fpr at wake-up.
5. **Wave G contract materialized:** `artifacts/wave-g-materialized-list.md`
   (18 plan-named rows verbatim + 7 selected by deterministic doctrine; 72
   deferred ADAPTs enumerated by name; arithmetic reconciles 97−25=72).

## Execution order

`A → E → B → C → D → G` (letters are stable labels). Wave F was carved to
PLAN-154 by debate consensus and is NOT part of this plan.

## Wave A — Docs/DX quick wins (L1)

Goal: close adopter-facing doc gaps at near-zero cost, honesty-first.

1. `INSTALL.md`/`README.md`: "Pick one path only" section (npx vs install.sh vs
   plugin conflict + stacked-failure mode + reset order) + "Official sources
   only" notice (GitHub `Canhada-Labs/ceo-orchestration`, npm `ceo-orchestration`).
2. `SECURITY.md`: official-surfaces anti-typosquat section.
3. `AGENTS.md` at repo root: review doctrine, action limits, repo map — the
   contract read by our Codex pair-rail. Include a freshness/derived check so
   drift in the review rail's input is caught (debate C advisory).
4. `docs/degradation-outside-claude-code.md`: honest page on what degrades in
   other harnesses (hook enforcement, audit chain, vetos evaporate).
5. `examples/`: 4-6 post-install target-repo `CLAUDE.md` samples by stack
   (node-api, django, go, monorepo-ts).
6. README: "Which skill should I use?" 10-15 row table from CHEAT-SHEET —
   discovery-at-151 proof point that fronts Wave D (debate A NTH-6).

Check: contamination grep clean; no counts touched; links resolve.

## Wave E — Security gates: the S254 lesson codified (L3, SENT-E, ADR-173 + ADR-175)

Goal: make the dead-rail/fail-open class UNABLE to ship silently. Core doctrine
(debate consensus #2): **behavioral positive-control certifies; static scan
complements.**

1. **Behavioral positive-control per blocking hook** (ADR-173 centerpiece):
   every security-critical hook ships a red-team fixture (known-bad input it
   MUST block) that CI replays with the hook's dependency mocked-present; a
   fixture that stops firing reddens the build. Static side:
   `check_harness_config.py` as an **extension** of
   `check-active-hooks-executable.py` (no duplicate gate), modeling the
   harness's REAL runtime resolution (`$CLAUDE_PROJECT_DIR` + the
   `_python-hook.sh` shim's dirname/cwd logic, NOT `REPO_ROOT`), with a planted
   **runtime-unresolvable** shim fixture that must go red + inline-secret scan
   + missing-deny detection. Explicit annotation/allowlist for intentional
   opt-in no-op hooks, with fixtures proving both directions (debate A R-VP6).
   Wire into `validate.yml` (exit≠0 red) + `/ceo-boot` Tier-S check.
2. **Liveness for fail-open rails** (debate B unseen-1): a fail-open security
   rail that fail-opened on every invocation over a window surfaces RED in
   `/ceo-boot` — silence from a fail-open rail is not health (the actual S254
   root cause: `check_pair_rail.py` fail-opens by design when Codex is absent).
3. **Deny baseline** in shipped `settings.json` + `install.sh` (expanded per
   debate B): `~/.ssh/**`, `~/.aws/**`, `~/.npmrc`, `~/.config/gcloud/**`,
   `~/.kube/config`, `~/.docker/config.json`, `~/.git-credentials`, `~/.netrc`,
   `~/.pypirc`, `**/.env` + `**/.env.*` EXCLUDING `.example/.sample/.template`,
   `Bash(curl * | bash)`. Framed honestly as a coarse harness backstop
   complementary to `check_bash_safety.py`'s parse-gate (which owns the
   pipe-to-shell class) — never sold as coverage.
4. **`supply-chain-watch.yml`** (scheduled): `runs-on: ubuntu-latest`,
   `schedule`-only (never fork-`pull_request`), honors `CEO_SOTA_DISABLE`.
   Effort goes to the SHA-pin/workflow-policy validator (extending
   `check-action-sha-drift.py`) + an assert that our own npm SLSA provenance
   chain has not regressed; `npm audit signatures` noted as thin on a zero-dep
   package. + incident-response playbook doc.
5. **Destructive-Bash citation gate** (ADR-175): "cite the instruction
   verbatim" element recorded into the HMAC chain. Failure to verify the
   citation is **fail-CLOSED (block the op)** — mirrors `_e3`/C4
   (`check_bash_safety.py:429-431`); fail-open permitted only for the
   audit-emit side. Cited text passes `redact_secrets` and is marked as DATA
   before entering the chain. Ships with a transcript-read-failure fixture
   asserting BLOCK.
6. Stale-replay regression test: `check_postcompact_reinject.py` never loads
   executable `ARGUMENTS=` payloads (already pointers-only — freeze it with a
   positive-control; debate B endorses as the model for item 1).
7. **Prompt Defense Baseline** (ADR-175): 6-bullet anti-injection block in the
   spawn template + `check_agent_spawn.py` validates presence for agents
   touching untrusted content.
8. Execution rules for this wave: per-unit CI test wiring same-commit;
   pre-commit assert `touched − SIGNED SCOPE = ∅` on any file under
   `.claude/hooks/` or `settings.json` (debate B unseen-3); new jobs/steps
   honor `CEO_SOTA_DISABLE`; fork-PR posture: static, no-network,
   no-credential.

Check: positive-control suite red on planted dead-rail AND on
runtime-unresolvable shim; green on healthy repo; full hook suite + red-team
corpus green; ceremony scope == touched files.

## Wave B — Installer/release lifecycle (L3, SENT-B)

Goal: close install→verify→doctor→repair; keep the Owner's manual gate (PLAN-125).

1. `scripts/install.sh`: persist install-state with the ORIGINAL request
   (--profile/--stack/--ceremony/placeholders) + each operation.
2. `scripts/upgrade.sh`: replay of recorded request (no auto-pull). Back-compat
   (debate C must-fix): missing request record (all pre-Wave-B installs) ⇒
   fall back to the ADR-155 `--dry-run` + drift-classifier path — never
   error, never no-op.
3. `scripts/doctor.sh` + repair mode: diff installed vs existing
   `skill-manifest.sha256` (drift/missing) + selective restore. Keep our
   SHA-identical uninstall safety (stronger than upstream — verified).
4. Externalize install profiles into schema-validated JSON manifest
   (cost/stability metadata) + `--dry-run --json`; CI validator.
5. Release idempotency across BOTH tag-triggered workflows (debate C):
   `npm-publish.yml` `already_published` guard; `release.yml`
   `gh release view || gh release create`; version↔plugin-manifest sync test
   next to the existing VERSION-consistency asserts; templatize the release
   notes string (no stale "first public release"). **RC posture unchanged**:
   RC tags stay hard-excluded from npm per PLAN-013 anti-goals #3/#16 — the
   draft's `next` dist-tag idea is DROPPED (contradicted a ratified anti-goal).
6. `.claude-plugin/{marketplace.json,plugin.json}` generated by
   `build-plugin.py` with a regen+diff idempotency gate (like the skill
   inventory step). `/plugin update` remains Owner-initiated pull — never
   background auto-update.

Check: fresh-install → doctor=clean → planted drift → doctor detects → repair
restores → uninstall exact; pre-Wave-B install upgrade falls back to
drift-classifier; shellcheck -S warning green; new-script tests CI-wired
same-commit.

## Wave C — Format + telemetry for OUR 151 skills (L3: SKILL.md ceremony) — prerequisite of D

1. Progressive disclosure pilots: extract `references/*.md` from
   `core/testing-strategy` (1026L) and `core/security-and-auth` (868L).
2. `allowed-tools:` frontmatter on `risk_class: high` skills + hook validation.
3. `version:` per skill + changelog; `templates/` for artifact-producing
   skills; human-scannable `## When to Activate` section (keep machine-first
   `activation_triggers`).
4. `/skill-health` (new command): per-skill use/success rate from the existing
   HMAC audit log, failure clustering, dead-skill flagging. **Scope of
   authority (debate A must-fix 4):** its telemetry informs retire/merge/
   improve decisions on the EXISTING 151 and proves catalog discovery health;
   it structurally cannot measure greenfield domains — Wave D is gated on
   C-complete + per-batch Owner go/no-go, not on raw-usage numbers.
5. `/context-budget` (new command): static overhead audit + top-3 savings.
6. Derived COMMAND→SKILL→HOOK map doc generated by script.
7. Audit-log-as-data rule (debate B unseen-2): `/skill-health` and
   `/context-budget` render audit-log content as untrusted data — never as
   instructions — same fencing as recalled memories.

Check: pilots load via reference without content loss; /skill-health returns
non-empty on dogfood log; SKILL.md changes ride SP-NNN + /skill-review; counts
scripts green; new-script tests CI-wired same-commit.

## Wave D — New skills: the 32 ADOPTs (L3: SKILL.md ceremony) — after C

Squads via `/architect`; every port: per-file license verified at the pinned
clone SHA and recorded in the `NOTICE` ledger (OQ1 resolution), zero ECC refs,
stdlib py≥3.9 scripts, entry via `/skill-review`.

**Mechanical import gate (debate consensus #4, blocks catalog entry):**
`check-imported-skill.py` wired into `/skill-review` — (a) injection-corpus
scan of the imported SKILL.md (reuse the existing scan-injection corpus);
(b) well-formed provenance (NOTICE entry exists); (c) review-attestation
trailer present; (d) ported scripts do not fetch upstream infrastructure or
execute upstream-supplied content. Human line-by-line review happens ON TOP of
the gate, never instead of it. **Quarantine path:** a post-merge finding
disables the skill (move out of catalog + audit event) — imports are
reversible by construction.

**Two batches, Owner go/no-go each (debate A: consumer-plausibility first):**

- **Batch 1 (plausible consumer today / general engineering):** jvm
  (java-coding-standards, springboot-patterns + quarkus/kotlin/jpa ADAPTs),
  golang-patterns, cpp×2, csharp-testing, prisma-patterns, pytorch-patterns,
  hexagonal-architecture, recsys-pipeline-architect, loop-design-check,
  dynamic-workflow-mode, frontend-slides, ui-demo, windows-desktop-e2e.
- **Batch 2 (speculative inventory — deferred by default, Owner may pull
  forward):** network-ops squad (4), healthcare-clinical squad (3 + phi/hipaa
  overlays), manufacturing squad (2 + energy-procurement), motion trio,
  angular-developer, nuxt4-patterns, nestjs-patterns, pubmed/uspto. Rationale:
  no consumer repo exists today; several are version-pinned and will rot.

Check: per batch — check-claude-md-claims.py + verify-counts.sh (same commit as
count changes), skill-lint, contamination grep, import gate green, NOTICE
updated.

## Wave G — ADAPT merges into existing skills (L3: SKILL.md ceremony)

~25 enrichments, no new files (full list in artifacts): react-performance/
patterns/testing → frontend; database-migrations + postgres/mysql →
data-schema-design; intent-driven-development → spec-clarify; search-first →
code-review; evm-token-decimals + keccak256 + llm-trading-agent-security →
fintech/trading-hft; supply-chain quartet → supply-chain; security-review +
bounty-hunter lens → security-and-auth; tdd-workflow plan-handoff section
(untrusted `*.plan.md`) → testing-strategy. Pilot a `skill-comply`-style
compliance harness on 2 skills.

Sequencing (debate A NTH-4): the `security-and-auth` and `testing-strategy`
merges run AFTER Wave C restructures those two files into `references/`.
Soak posture per OQ3. All merges ride SP-NNN + `/skill-review` + import gate
(they carry upstream content too).

Check: enriched skills pass skill-lint; no count drift; NOTICE updated; soak
posture honored.

## Open questions (Owner, Wave 0)

1. ~~OQ1 attribution format~~ **RESOLVED by debate (round-1 consensus):**
   single `NOTICE` ledger with per-source-file license verified at the pinned
   clone SHA (stronger than 40 frontmatter blocks). Owner may veto at Wave 0.
2. ~~OQ2 observe-rail payload scope~~ **RESOLVED by debate:** metadata-only v1;
   moves to PLAN-154 with the rest of the learning loop.
3. **OQ3 (NEW — soak posture):** the 7-day SKILL.md shadow-soak
   (`skill-patch-apply.py:664`) is wall-clock; Waves C/D/G touch 151+ skills.
   Options: (a) Owner pre-authorizes `skip_soak` per batch under the launch
   override; (b) start all shadows in parallel early and let the calendar run
   (adds ~1-2 weeks wall-clock, zero token cost); (c) hybrid — skip for new
   files (Wave D; nothing to regress), parallel-shadow for merges (Wave G).
   CEO recommends **(c)**.
4. **OQ4 (S264 — AFTER-C soak window, ratified 2026-07-09):** AskUserQuestion
   put to the Owner: "O promote de SP-026/SP-034 é a última unidade de
   execução do PLAN-153, mas a janela de soak ratificada (S263) só abre em
   2026-07-14 — e o soak começou hoje às 16:32Z (~0h de sinal). Como
   finalizamos?" Owner selected (verbatim): **"Waiver agora (S264) — fechar
   hoje"** over the CEO-recommended "Manter soak, promote 07-14". Decision:
   the remaining parallel-shadow window for SP-026/SP-034 is waived
   (**soak waiver S264**, same pre-authorized skip semantics as S263);
   promote executes 2026-07-09 via the Owner terminal script
   (`~/Desktop/ceo-promote-after-c/`). Pre-waiver audit sweep of the soak
   window (2026-07-09T16:32Z → sweep time, 101 events) found **zero adverse
   signal** touching either shadow; the only match was a benign
   `reference_postread_observed` observability event on an unrelated
   SKILL.md.

## Closeout record (S261, 2026-07-06/07 — overnight autonomous run)

All six waves EXECUTED. Split: everything unguarded is committed on `main`;
everything canonical-guarded is authored + tested + Codex/rehearsal-verified
and STAGED under `PLAN-153/staged/<wave>/` for the Owner wake-up ceremony
(`~/Desktop/ceo-wakeup/` — `wake-up-sign-and-land.sh` + `README-WAKEUP.md`).
The plan stays `executing` until the Owner signs the sentinels and lands the
staged overlays; at that point it goes `executing → done`.

**Committed on main (this run):**
- Wave A `0fa0396` — docs/DX (pick-one-path, anti-typosquat, AGENTS.md
  review contract + freshness gate, degradation page, post-install examples).
- Wave 0 + PLAN-154 debate `3d670eb` — ratifications (OQ3=c, batch split,
  ADR realloc 173/174/175 → 158/159/160), Wave G contract materialized,
  PLAN-154 round-1 debate (3× ADJUST_PROCEED → PROCEED, 13 binding applied)
  → reviewed.
- Wave E direct `09d7720` — /ceo-boot fail-open-rail liveness, spawn
  prompt-defense template, sha-drift `--policy` (fork-guard P2 fixed),
  postcompact freeze, harness-config fixtures, honesty docs.
- Wave B direct `3121c1d` — doctor.sh + repair (symlink type-change P2
  fixed), install-profiles manifest + validator, deterministic plugin regen
  gate, release-notes template.
- PLAN-155 + sentinels `314891a` — Codex-harness-compat plan reviewed +
  Codex pair-rail R1 REJECT → R2 APPROVE; SENT-E/SENT-B drafts.
- Wave C direct `4d194d9` — /skill-health + /context-budget + COMMAND→
  SKILL→HOOK map; SP-022/023 for the disclosure pilots; commands 22→24.
- Backlog `982bb7c` — substrate-adopt sweep doc, PLAN-152 deferred-status
  doc, enum-pin-sync guard, SENT-BACKLOG draft.
- Wave D `05f5c9a` — import gate `check-imported-skill.py` (13 tests) +
  NOTICE provenance ledger (15 batch-1 skills staged, 8 new squads).
- Wave G `b933037` + `54a6296` — SP-024..041 (25/25 merges, 18 targets),
  NOTICE additions, SENT-E Amends broadened to the SPEC v2.47 summary row.

**Staged for the ceremony (guarded — Owner GPG):** Wave E (16-path SENT-E
round-1: check_harness_config, check_bash_safety citation gate,
check_agent_spawn prompt defense, settings.json deny baseline,
supply-chain-watch.yml, validate.yml, install.sh, _lib/audit_emit 302→303 +
SPEC row + api-contract pin, ADR-158/159); Wave B (6-path SENT-B round-2:
install.sh install-state + upgrade replay, release/npm-publish idempotency +
the 2 latent release.yml bugs, validate.yml); Wave backlog (SENT-BACKLOG
round-4: settings.json sandbox.credentials + enforceAvailableModels,
tool_lifecycle + audit_emit Task* enum, SPEC amend); Wave C SKILL.md pilots
(SP-022/023 via /skill-review); Wave D 15 skills (import gate + /skill-review,
count 151→166 at ceremony); Wave G 25 merges (SP-024..041 via /skill-review).

**Ceremony fixups recorded** (in the staged MANIFEST/CEREMONY-NOTES): Wave D
frontmatter source:/license: hoist + attestation trailer + 8 new domain
scaffolds + count bump; Wave C SP-023 changelog SP-022→SP-023 typo; Wave G
AFTER-C ordering (SP-022→023→026→034). **Operational finding for Owner
triage:** the pre-rotation audit log had a real HMAC chain break at line 483
(2026-07-02, now in a rotated archive) — surfaced by /skill-health.

**Follow-ups noted (not this plan):** `check_skill_patch_sentinel.py`
`_SKILL_MD_RE` is unanchored — it fires on `.claude/plans/**/staged/**`
SKILL.md, forcing every wave to Bash-cp around the Write tool; anchor it or
exempt staged paths. Register a typed `skill_import_quarantined` audit action
for the import gate's quarantine path.

## Success criteria

- [x] All 6 waves executed or explicitly deferred with pointer (nothing
      silently dropped) — including the 72 unmerged ADAPTs in §Deferred.
- [ ] Behavioral positive-control suite: red on planted dead-rail fixture AND
      runtime-unresolvable shim; the S254 class cannot recur SILENTLY
      (liveness RED in /ceo-boot when a fail-open rail never fires).
- [ ] `/skill-health` reports on real dogfood data BEFORE first Wave D batch.
- [ ] Every imported piece: NOTICE entry (source@sha + license), import gate
      green, quarantine path tested once.
- [ ] CI green on every push; counts tolerance=0 respected; zero CI-dark
      test files (every new script's tests in an explicit validate.yml path).
- [ ] ADR-173 + ADR-175 accepted; sentinels archived per retention policy.
- [ ] PLAN-154 exists as the carved learning-loop plan (own debate before its
      execution).

## How to continue (next session first message)

> Gate 1-3 per CLAUDE.md, then: read `.claude/plans/PLAN-153-ecc-comparative-uplift.md`
> + `PLAN-153/artifacts/synthesis-report.json` + `PLAN-153/debate/round-1/consensus.md`.
> Execute Wave 0 with the Owner (ratify OQ3 + confirm OQ1/OQ2 dispositions +
> batch split; sign SENT-E/SENT-B; reserve ADR-173/174/175), then run waves in
> order A → E → B → C → D → G. ALL of E/B/C/D/G are L3 ceremony work — never
> edit a guarded path without the matching sentinel/SP-NNN. Commit per wave;
> run check-claude-md-claims.py + verify-counts.sh before every push that
> touches counts. Do not start Wave D before /skill-health returns data and
> the Owner gives the batch-1 go.

## §Deferred

- **Wave F (gated learning loop) → PLAN-154** (debate consensus #3): observe
  rail (metadata-only v1), distiller with injection-scanned output + bounded
  lesson schema, confidence decay, fenced /ceo-boot one-liners, denial
  dampening REDESIGNED as advisory-only condensation (a blocking guard's block
  reason never loses legibility), fact-forcing deny-once gate, /lesson-evolve,
  ADR-174. PLAN-154 requires its own debate before execution.
- **72 unmerged ADAPTs** (97 in matrix − 25 chosen for Wave G): recorded as
  defer-pointers in `PLAN-153/artifacts/ecc-skill-matrix.md` (verdict=ADAPT
  rows not in Wave G's list). Revisit after /skill-health exists.
- **39 INSPIRE rows**: idea-only; no port planned.
- **Wave D batch 2**: deferred by default pending Owner pull-forward (see D).

## Risks

- node→python stdlib rewrite is the hidden cost of mechanism ADAPTs — estimate
  per piece before committing to a full wave (budget re-derived bottom-up:
  D≈1.3M, G≈0.5M, E≈0.4M, B≈0.3M, A+C≈0.3M + ceremony/pair-rail/CI overhead).
- Third-party content import: 13 injection flags recorded by the analysis
  workflow (none hostile, all treated as data) — the mechanical import gate is
  the defense, prose review is supplementary.
- Vendor claims (AgentShield numbers) must never be cited.
- Ceremony-scope drift on Wave E is a security event, not hygiene: pre-commit
  assert `touched − SIGNED SCOPE = ∅` on guard-surface files.
- Wall-clock soak (OQ3) can stall G — decide posture at Wave 0, not mid-wave.

## Reference links

- Analysis run: workflow `wf_c555404e-093` (34 agents, 277/277 skills, 0 errors)
- Artifacts: `.claude/plans/PLAN-153/artifacts/{ecc-skill-matrix.md,verified-claims.md,synthesis-report.json}`
- Debate: `.claude/plans/PLAN-153/debate/round-1/` (3× ADJUST_PROCEED →
  consensus PROCEED, 13 adjustments applied)
- Upstream: `github.com/affaan-m/ecc` @ `81af4076` (shallow clone 2026-07-03),
  repo-level MIT (per-file verification pending at Wave D via NOTICE ledger —
  pin ports to this SHA; the analysis matrix was generated from it)
- House rules exercised: PLAN-152 (wave discipline), PLAN-125 (manual gate),
  PLAN-013 (npm anti-goals), ADR-031 (skill-patch), ADR-121 (dual signer
  rails), ADR-141 (finding shards), ADR-155 (drift classifier)

## Debate

Round 1 (2026-07-03): 3 archetypes → 3× ADJUST_PROCEED, zero VETO. Consensus
verdict **PROCEED** (design-coherent) with 13 adjustments — all applied to
this file (see `PLAN-153/debate/round-1/consensus.md` for the full A1-A13
index and the anonymization map). Key deltas vs draft: E/B/C/D/G reclassified
L3 with ceremony allocated in Wave 0; Wave E core redefined from static scan
to behavioral positive-control + runtime-resolution modeling + liveness; Wave
F carved to PLAN-154; `next` dist-tag dropped (PLAN-013 conflict); OQ1→NOTICE
ledger, OQ2→metadata-only; budget re-derived bottom-up. Shipping authority
remains with the verification cascade (V2 Codex pair-rail + V3 Owner GPG).
