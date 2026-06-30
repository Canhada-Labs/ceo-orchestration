# Architecture Decision Records (ADRs)

<!-- last-reviewed: 2026-06-06 v1.0.0 -->

This directory captures **cross-cutting architectural decisions** that
affect the ceo-orchestration framework in ways that aren't obvious from
reading the code. ADRs are not essays or postmortems — they are short,
structured records that answer:

> "Why does it work this way? What else did we consider? What do we give up?"

## Note on ADR ID collisions (PLAN-085 Wave B)

Two distinct collision patterns exist in this directory; both are
intentional per the policies below.

**Pattern 1 — ID renamed away (ADR-111 → ADR-120):**
The file `ADR-111-pii-core-promotion.md` originally held `id: ADR-111`,
shipped in PLAN-080 Phase 0a (2026-05-09). When `ADR-111-locked-corpus-governance.md`
landed the next day (2026-05-10, PLAN-081) with the same `id: ADR-111`,
a double-booking emerged. ADR-117 (collision-rename policy, ACCEPTED
2026-05-12) authorized renaming the PII-core file to
`ADR-120-pii-core-promotion.md` (id: ADR-120, `original_id: ADR-111`).
The old file was deleted in PLAN-085 Wave B.1. The locked-corpus
file retains `id: ADR-111` as the sole holder going forward.

**Pattern 2 — Base-ID share with `a` suffix (ADR-049 + ADR-049a):**
`ADR-049-dual-path` and `ADR-049a-worktree` intentionally share base-ID
with the `a` suffix discipline per the PLAN-061 precedent (`a` =
amendment / clarifier of the base ADR's scope, NOT a separate decision).
The base file remains canonical; the `a`-suffixed file extends or
clarifies it. This is NOT a rename and NOT a collision; the `a` form
is structurally distinct from the renamed-away pattern above. Codex
REFUTE on F-A-SEC-T-0002 (PLAN-084) confirmed the non-collision read.

Future ADR authors:
- Prefer ALLOCATING a fresh ID over reusing a renamed-away one (the
  rename history is preserved in the target's `original_id` field).
- Use the `<base>a-...` form ONLY for amendments to a base ADR (per
  PLAN-061 precedent). Document the relationship inline.

## Known amendment chain gaps (honest documentation)

Some AMEND chains in this directory skip AMEND-N numbers. This section
documents each gap so the chain self-consistent record does not require
a reader to guess.

**ADR-040: base → AMEND-2 (no AMEND-1)**

`ADR-040-live-adapter-activation-contract.md` (base, ACCEPTED 2026-04-14)
is directly amended by `ADR-040-AMEND-2-credential-blocking.md` with no
intervening `ADR-040-AMEND-1`. This is intentional: the base ADR-040 was
originally amended in-place at the text level (prose edits to §4 credential
lifecycle language) on multiple occasions during PLAN-012/PLAN-085 Wave A/B
without a formal AMEND-1 record. When PLAN-085 Wave C.2 introduced a
*semantic reversal* (from emit-only to blocking enforcement at max-age),
the anti-churn doctrine (ADR-115) required an explicit amendment file.
Rather than backfilling a historical AMEND-1 for the earlier prose edits
(which were not semantic reversals), the AMEND-2 label was chosen to
signal that AMEND-1 exists only as in-place prose revisions within the
base ADR-040 file itself. This gap is by design, not an error.

## When to write an ADR

Write an ADR when a decision has **L3+ blast radius** — i.e., it touches
3+ modules, changes a contract between producers and consumers, or
represents a trade-off that a future maintainer would otherwise have to
re-derive from scratch.

**Examples that warrant an ADR:**
- Choosing one of several plausible directory layouts for a new subsystem
- Replacing a mechanism (e.g. skill signing) with a different approach
- Picking a language, runtime, or version minimum
- Deciding where state lives (in-repo vs out-of-repo, local vs shared)

**Examples that do NOT warrant an ADR:**
- A single-file bug fix (put the rationale in the commit message)
- A localized refactor (use a code comment)
- A typo, log message tweak, or config adjustment
- Anything a future reader can verify in 5 minutes by grep

## Format

Every ADR follows the same 7-section template from the
`architecture-decisions` core skill:

```markdown
# ADR-<NNN>: <short title>

**Status:** PROPOSED | ACCEPTED | DEPRECATED | SUPERSEDED by ADR-<NNN> | RETRACTED
**Date:** YYYY-MM-DD
**Enforcement commit:** <commit-sha> | n/a (documentation-only)   # RECOMMENDED — see §Enforcement
**Decision drivers:** <bullets — what forced the decision>

## Context

What is the situation? What problem needs a decision?

## Decision drivers

- Driver 1
- Driver 2

## Options considered

### Option A: <name>
Pros / cons.

### Option B: <name>
Pros / cons.

## Decision

The chosen option + a one-sentence summary.

## Consequences

Positive (+), negative (-), neutral (~). Be honest about trade-offs.

## Blast radius

L1 | L2 | L3+ — how many modules/contracts are touched.
```

### `Enforcement commit:` requirement (PLAN-045 Wave 3 P0-16)

Every ADR that claims **runtime behavior** — a hook, a script, a
policy, a check, a ``_lib/`` primitive — SHOULD include an
``Enforcement commit:`` field pointing at the git commit SHA where
that runtime behavior actually lands (post audit-v2 2026-04-27 — see
**Enforcement status** below for the current RECOMMENDED posture). ADRs that document
architectural principles, naming conventions, or directory layouts
with no runtime artifact set ``Enforcement commit: n/a
(documentation-only)``.

This field closes the **"declared but not wired" meta-pattern**
(PLAN-044 §Consolidated findings Pattern 1, 7 confirmed instances):
ADRs described mechanisms like ``CEO_MULTIMODEL_ENABLE`` kill-switch
or ``reset_chain_on_rotation()`` call site but the code did not
enforce them. The field gives reviewers and auditors a concrete
anchor: "this ADR is real if and only if commit ``<sha>`` touches a
file under ``.claude/hooks/`` or ``.claude/scripts/``".

**Enforcement status (post audit-v2 2026-04-27, C1-P0-08 Path A):**
field is **RECOMMENDED, not required**.
``.claude/scripts/validate-governance.sh`` emits **WARNING** (not ERROR)
when an ADR-065+ ACCEPTED ADR lacks the ``Enforcement commit:`` field.
The original PLAN-045 P0-16 intent is better served by targeted audit
spot-checks than by mass back-fill across all ADRs.

For reference, the pre-audit-v2 failing-CI rule was:

> `validate-governance.sh` fails CI when an ADR with `Status: ACCEPTED`
> has: No `Enforcement commit:` field, OR a commit SHA that does not
> reference a file in `.claude/hooks/` or `.claude/scripts/` (`git show
> --stat` check), UNLESS the value is `n/a (documentation-only)`.

That rule is **superseded** by the warning-only Path A approach above.
New ADRs SHOULD include the field from day one; back-fill of the 64
existing pre-PLAN-045 ADRs remains a low-priority polish task.

Back-fill of the 64 existing ADRs is a Wave 5 polish task
(PLAN-045/phase-1-2-3-partial-closure.md §Deferred); new ADRs post
PLAN-045 Wave 3 SHOULD include the field from day one.

## Naming convention

`ADR-<NNN>-<kebab-case-slug>.md` where `<NNN>` is a zero-padded
3-digit sequence number. Numbers never get reused, even after an ADR is
deprecated or superseded.

## Lifecycle

- **PROPOSED** → the ADR is a draft discussion, open for input
- **ACCEPTED** → the decision is live; the code/config matches it
- **DEPRECATED** → the decision is no longer preferred but the code
  may still reflect it; do not use this choice for new work
- **SUPERSEDED by ADR-<NNN>** → replaced by a newer ADR; that newer
  ADR links back in its Context section
- **RETRACTED** → the ADR was PROPOSED but never reached ACCEPTED; it
  is the terminal state when a proposal is withdrawn before acceptance.
  A RETRACTED ADR is NOT superseded — it simply never became live.
- **ACCEPTED-as-RESERVED** → the ADR ID slot is formally allocated but
  the decision content is intentionally deferred; the slot is held to
  prevent ID collision.

### Status field conventions (multi-convention coexistence)

ADRs in this directory use several status-marker patterns that
accumulated across different sprint eras. All are valid; no mass
back-fill is planned. When authoring a new ADR, prefer the **combined**
form (FM + heading):

1. **Frontmatter `status:` field** — machine-parseable; used by
   `generate-adr-index.py` and `validate-governance.sh`.
2. **Bold `**Status:**` line** — human-readable; original convention.
3. **`## Status` H2 heading** — structured block for ADRs that carry
   a Transition Log (per ADR-041).

New ADRs should include BOTH a frontmatter `status:` field AND a bold
`**Status:**` inline line for maximum compatibility.

## Current ADRs


<!-- BEGIN ADR-INDEX (generated by .claude/scripts/generate-adr-index.py) -->

_Auto-generated: 170 ADR(s) on disk. Run `python3 .claude/scripts/generate-adr-index.py --write` to refresh._

| ID | Title | Status |
|---|---|---|
| [ADR-001](ADR-001-runtime-state-directory.md) | Runtime state directory convention | ACCEPTED |
| [ADR-002](ADR-002-hooks-package-layout.md) | Python hooks package layout + version shim | ACCEPTED |
| [ADR-003](ADR-003-branch-protection-replaces-skill-signing.md) | Branch protection replaces skill signing | ACCEPTED |
| [ADR-004](ADR-004-defer-bash-legacy-removal.md) | Defer bash legacy hook removal (SUPERSEDED — removed in PLAN-006 Phase 6b) | SUPERSEDED |
| [ADR-005](ADR-005-event-stream-v2.md) | Promote audit-log.jsonl to typed event stream v2 | ACCEPTED |
| [ADR-006](ADR-006-registry-derived-manifests.md) | Derived skill + archetype registry (no side-car YAML) | ACCEPTED |
| [ADR-007](ADR-007-spec-v1-semver-rc-policy.md) | Compliance SPEC v1, SemVer, and the release candidate policy | ACCEPTED |
| [ADR-008](ADR-008-hook-adapter-layer.md) | Hook Adapter Layer (neutral event/decision contract) | ACCEPTED |
| [ADR-009](ADR-009-squad-contract.md) | Squad bundle contract | ACCEPTED |
| [ADR-010](ADR-010-canonical-edit-sentinel.md) | Canonical-edit sentinel for meta-agent drafts | ACCEPTED |
| [ADR-011](ADR-011-event-stream-v2.1-injection-flag.md) | Event stream v2.1 — `injection_flag` action | ACCEPTED |
| [ADR-012](ADR-012-cross-adapter-golden-fixtures.md) | Cross-adapter golden fixtures + OIDC NPM publisher | ACCEPTED |
| [ADR-013](ADR-013-squad-trading-hft.md) | Squad — trading-hft | ACCEPTED |
| [ADR-014](ADR-014-hook-migration-batch-policy.md) | Hook Adapter Migration Batch Policy | ACCEPTED |
| [ADR-015](ADR-015-reflexion-v2-outcome-loop.md) | Reflexion v2 — Outcome Loop + Top-K Cap + Index | ACCEPTED |
| [ADR-016](ADR-016-spawn-token-tracking.md) | Spawn Token Tracking — Contract and Null Semantics | ACCEPTED |
| [ADR-017](ADR-017-lesson-pruning-policy.md) | Lesson Pruning Policy — Advisory Sprint 6, Bounded Execute Sprint 8 | SUPERSEDED by ADR-020 |
| [ADR-018](ADR-018-claim-grammar.md) | Claim Grammar for Confidence Gate | ACCEPTED |
| [ADR-019](ADR-019-confidence-gate-enforcement-lifecycle.md) | Confidence gate enforcement lifecycle | ACCEPTED |
| [ADR-019-AMEND-1](ADR-019-AMEND-1-confidence-gate-block-mode-lifecycle.md) | Confidence-gate per-class block-mode lifecycle | ACCEPTED |
| [ADR-019-AMEND-2](ADR-019-AMEND-2-CLASS-SHA_EXISTS-promote-to-high-confidence-block.md) | CLASS-SHA_EXISTS: Promote `sha_exists` claim class to HIGH_CONFIDENCE_BLOCK | ACCEPTED |
| [ADR-020](ADR-020-lesson-pruning-policy-v2.md) | Lesson pruning policy v2 | ACCEPTED |
| [ADR-021](ADR-021-e2e-harness-contract.md) | E2E integration harness contract | ACCEPTED |
| [ADR-022](ADR-022-reserved-slot.md) | Reserved Slot (ACCEPTED-as-RESERVED) | ACCEPTED-as-RESERVED |
| [ADR-023](ADR-023-docs-freshness-lifecycle.md) | Docs-as-code freshness enforcement lifecycle | ACCEPTED |
| [ADR-024](ADR-024-perf-baseline-policy.md) | Hook performance baseline policy (measure-only Sprint 10, gate Sprint 11) | ACCEPTED |
| [ADR-025](ADR-025-squad-edtech.md) | Squad edtech + Agent Architect dogfood outcome | ACCEPTED |
| [ADR-026](ADR-026-squad-government.md) | Squad government + Agent Architect dogfood v2 outcome | ACCEPTED |
| [ADR-027](ADR-027-unified-agent-state-backend.md) | Unified Agent State Backend | ACCEPTED |
| [ADR-028](ADR-028-multi-llm-canonical-parity.md) | Multi-LLM Canonical Envelope Parity | ACCEPTED |
| [ADR-029](ADR-029-lexical-tfidf-retrieval.md) | Lexical tf-idf Skill Retrieval Baseline | ACCEPTED |
| [ADR-030](ADR-030-llm-as-judge-methodology.md) | LLM-as-Judge Methodology (hybrid with deterministic fallback) | ACCEPTED |
| [ADR-031](ADR-031-self-improving-skills.md) | Self-improving skills (Owner-gated, shadow-mode) | ACCEPTED |
| [ADR-032](ADR-032-interactive-debate-protocol.md) | Interactive multi-round debate protocol with Jaccard convergence + Red Team gate | ACCEPTED |
| [ADR-033](ADR-033-cost-budget-enforcement.md) | Cost/Budget enforcement lifecycle (advisory Sprint 11, gate conditional Sprint 12) | ACCEPTED |
| [ADR-034](ADR-034-shared-working-memory.md) | Shared Working Memory (Scratchpad) | ACCEPTED |
| [ADR-035](ADR-035-otel-export.md) | OpenTelemetry export (OTLP/HTTP JSON) with defense-in-depth | ACCEPTED |
| [ADR-036](ADR-036-output-safety.md) | Output Safety Harness (PostToolUse Agent Scanner) | ACCEPTED |
| [ADR-037](ADR-037-chaos-testing-methodology.md) | Chaos + load testing methodology (thread-PR, process-nightly, weapon-locked) | ACCEPTED |
| [ADR-038](ADR-038-session-graph-continuity.md) | Session-graph continuity (derived-only, encrypted-at-rest) | ACCEPTED |
| [ADR-039](ADR-039-skill-marketplace-protocol.md) | Skill (squad) marketplace protocol | ACCEPTED |
| [ADR-040](ADR-040-live-adapter-activation-contract.md) | Live Adapter Activation Contract | ACCEPTED |
| [ADR-040-AMEND-2](ADR-040-AMEND-2-credential-blocking.md) | §4 amendment — credential blocking at max-age (emit-only → blocking enforcement) | ACCEPTED |
| [ADR-041](ADR-041-transition-log-convention.md) | Transition Log Convention for State-Machine ADRs | ACCEPTED |
| [ADR-042](ADR-042-mcp-server-contract.md) | MCP Server Contract | ACCEPTED |
| [ADR-042-AMEND-1](ADR-042-AMEND-1-read-only-mcp-tools-expansion.md) | Read-only MCP tools expansion (PLAN-096) | ACCEPTED |
| [ADR-043](ADR-043-soc2-audit-trail-mapping.md) | SOC2 Audit Trail Mapping | ACCEPTED |
| [ADR-044](ADR-044-formal-verification-pilot.md) | Formal Verification Pilot | ACCEPTED |
| [ADR-045](ADR-045-policy-as-code-engine.md) | Policy-as-code engine (stdlib YAML DSL) for selected hooks | ACCEPTED |
| [ADR-046](ADR-046-deterministic-replay.md) | Deterministic replay of session graph + audit log | ACCEPTED |
| [ADR-047](ADR-047-predictive-budgeting.md) | Predictive budgeting for plan cost estimation | ACCEPTED |
| [ADR-048](ADR-048-cross-plan-memory.md) | Cross-plan shared memory (pattern library) | ACCEPTED |
| [ADR-049](ADR-049-policy-engine-dual-path-deprecation.md) | Policy Engine Dual-Path Deprecation | ACCEPTED |
| [ADR-049a](ADR-049a-worktree-orchestration-policy.md) | Worktree orchestration policy — cooperative, not adversarial isolation | ACCEPTED |
| [ADR-050](ADR-050-native-subagents-dual-rail.md) | Native Subagents Dual-Rail | ACCEPTED |
| [ADR-051](ADR-051-skill-reference-expanded-trust-boundary.md) | Skill-by-reference expanded trust boundary | ACCEPTED |
| [ADR-052](ADR-052-multi-model-dispatch-by-role.md) | Multi-model dispatch by role | ACCEPTED |
| [ADR-053](ADR-053-sentinel-hmac-deferred.md) | Sentinel HMAC deferred — SHA-256 + CODEOWNERS sufficient under current threat model | ACCEPTED |
| [ADR-054](ADR-054-github-token-rotation.md) | GitHub Token Rotation Cadence | ACCEPTED |
| [ADR-054-AMEND-1](ADR-054-AMEND-1-anthropic-admin-key-tier.md) | Anthropic Admin API key tier (admin blast radius ≠ inference blast radius) | PROPOSED |
| [ADR-055](ADR-055-audit-log-hmac-chain.md) | Audit-log HMAC chain for tamper detection | ACCEPTED |
| [ADR-055-AMEND-1](ADR-055-AMEND-1-spool-writer-async-drain.md) | §Components amendment — multi-PID spool-writer with async drain + 4-tuple total order | ACCEPTED |
| [ADR-055-AMEND-2](ADR-055-AMEND-2-chain-reset-marker.md) | HMAC chain rotation chain_reset_marker + rotation manifest sidecar | ACCEPTED |
| [ADR-056](ADR-056-hook-lifecycle-expansion.md) | Hook lifecycle expansion — SessionStart / SessionEnd / UserPromptSubmit / Stop | ACCEPTED |
| [ADR-057](ADR-057-output-scan-redaction.md) | Output-scan redaction — unicode / telemetry / OWASP LLM Top 10 | ACCEPTED |
| [ADR-058](ADR-058-brainstorm-gate-and-two-pass-review.md) | Brainstorm gate pre-Plan + two-pass adversarial review | ACCEPTED |
| [ADR-059](ADR-059-skill-bootstrap-env-knob.md) | Skill bootstrap env-var bypass for `check_skill_patch_sentinel` | ACCEPTED |
| [ADR-060](ADR-060-curated-skill-import-pipeline.md) | Curated skill import pipeline (SP-NNN chain) | ACCEPTED |
| [ADR-061](ADR-061-runtime-cost-streaming.md) | Runtime cost streaming + OTLP export | ACCEPTED |
| [ADR-062](ADR-062-rag-sidecar-mcp-opt-in.md) | RAG sidecar MCP opt-in (stdlib-only preserved) | ACCEPTED |
| [ADR-062-AMEND-1](ADR-062-AMEND-1-rag-conditional-default-on-supersedes-opt-in.md) | RAG conditional default-ON via repo-profile LARGE — supersedes §default-OFF clause for LARGE profile only | ACCEPTED |
| [ADR-063](ADR-063-agent-eval-empirical-dispatch-validation.md) | Agent-eval tournament framework — empirical ADR-052 dispatch validation | ACCEPTED |
| [ADR-064](ADR-064-dynamic-tier-policy-learned-dispatch.md) | Dynamic tier policy — learned dispatch with VETO floor hardcode | ACCEPTED |
| [ADR-065](ADR-065-audit-event-naming-convention.md) | Audit-event naming convention — `<surface>_<verb>[_modifier]` freeze | ACCEPTED |
| [ADR-066](ADR-066-context-mode-orthogonal-to-manifest.md) | Context-mode as orthogonal capability to Manifest (not redundant) | ACCEPTED |
| [ADR-067](ADR-067-ceo-model-downshift-static-routing.md) | CEO model downshift — static routing rule (Sonnet-default + Opus-upgrade-upfront) | ACCEPTED |
| [ADR-069](ADR-069-wondelai-skills-import-refused.md) | wondelai/skills import — refused (formal closure of Session 55 audit verdict) | ACCEPTED |
| [ADR-070](ADR-070-audit-emit-package-layout.md) | audit_emit package layout — split mechanism for 1921-LoC monolith | RETRACTED |
| [ADR-071](ADR-071-benchmark-comparison-methodology.md) | Benchmark comparison methodology — Nível 2 (offline + public baselines) | ACCEPTED |
| [ADR-072](ADR-072-test-discovery-via-conftest.md) | Test discovery via conftest.py — sys.path.insert retirement (97 sites retired in tests/) | ACCEPTED |
| [ADR-073](ADR-073-semver-bump-criteria-sprint-32.md) | SemVer bump criteria for Sprint 32 closeout — v1.9.0 / v1.10.0 / v2.0.0 decision | ACCEPTED |
| [ADR-074](ADR-074-sprint-32-phase-3-b1-refused.md) | Sprint 32 Phase 3 B1 (audit_emit split v2) — REFUSED via technical-infeasibility | ACCEPTED |
| [ADR-075](ADR-075-sprint-32-phase-5-b5-benchmark-refused.md) | Sprint 32 Phase 5 B5 (head-to-head benchmarks) — REFUSED via technical-infeasibility | ACCEPTED |
| [ADR-076](ADR-076-sprint-32-final-closure.md) | Sprint 32 Final Closure — 9 done + 2 refused + 0 pending | ACCEPTED |
| [ADR-077](ADR-077-2026-04-24-webfetch-injection-incident.md) | 2026-04-24 WebFetch harness-mimicry injection incident — forensic + remediation | ACCEPTED |
| [ADR-078](ADR-078-sentinel-cosign-clarification.md) | Sentinel co-sign vs. ADR forensic co-sign — semantic distinction (PLAN-064 amendment — lexical scope markers) | ACCEPTED |
| [ADR-079](ADR-079-prompt-sha-salt-hmac-impact.md) | prompt_sha per-installation salt + HMAC chain impact analysis | ACCEPTED |
| [ADR-080](ADR-080-rail-anomaly-h4-defense-in-depth.md) | Rail anomaly H4 — defense-in-depth via fabrication detection + experimental harness | ACCEPTED |
| [ADR-081](ADR-081-token-as-time-unit.md) | Canonical time/budget unit — Claude tokens, not human dev-time | ACCEPTED |
| [ADR-082](ADR-082-l7c-mitigation-default-on.md) | L7c Mitigation Default-On — `--dispatch=mitigated` becomes default for non-`code-reviewer` archetypes | ACCEPTED |
| [ADR-083](ADR-083-mcp-injection-scanner.md) | MCP injection scanner — close C-P0-01 G4 + advisory observability | ACCEPTED |
| [ADR-084](ADR-084-multi-adapter-refused-claude-only.md) | PLAN-057 multi-adapter expansion REFUSED — Claude-only by design | SUPERSEDED |
| [ADR-085](ADR-085-framework-landscape-claude-only.md) | Framework landscape 2026-04 — Claude-only positioning thesis | ACCEPTED |
| [ADR-086](ADR-086-checkpointing-refused.md) | Phase checkpointing REFUSED — audit-log + memory cover the use case | ACCEPTED |
| [ADR-087](ADR-087-otel-emit-refused.md) | OpenTelemetry span emit REFUSED — audit-log JSONL is canonical observability | ACCEPTED |
| [ADR-087-AMEND-1](ADR-087-AMEND-1-otel-consume-native-opt-in.md) | OTel consume-native opt-in profile (the dashboard, not the truth) | PROPOSED |
| [ADR-088](ADR-088-guardrails-library-refused.md) | Guardrails-library standalone export REFUSED — depth-over-breadth thesis | ACCEPTED |
| [ADR-089](ADR-089-sec-cluster-disposition.md) | PLAN-059 Phase 1 SEC-P0 cluster disposition (Session 67) | ACCEPTED |
| [ADR-090](ADR-090-framework-activation-defaults.md) | Framework activation defaults (PLAN-059 Phase 2 bundle) | ACCEPTED |
| [ADR-091](ADR-091-dogfood-validation-deferred.md) | PLAN-059 Phase 4 dogfood validation DEFERRED to passive observation (RETRACTED — see audit-v2 R2 NEW-P0) | RETRACTED |
| [ADR-092](ADR-092-plan-closure-honest-deferral.md) | Plan closure honest-deferral framework | ACCEPTED |
| [ADR-093](ADR-093-refused-adr-moratorium.md) | 60-day refused-ADR moratorium + per-plan refusal cap (§moratorium SUPERSEDED-BY-ADR-103; §per-plan-cap PRESERVED) | SUPERSEDED |
| [ADR-094](ADR-094-claude-sdk-compat-version-pinning.md) | Claude Agent SDK compat matrix + version-pinning policy | PROPOSED |
| [ADR-095](ADR-095-calendar-gate-retraction.md) | Calendar gate retraction (14d CI green + 30d no-retag) | ACCEPTED |
| [ADR-096](ADR-096-vibecoder-only-by-design.md) | Vibecoder-only by design (closes C7-DB-01 + C7-DB-02) | ACCEPTED |
| [ADR-097](ADR-097-function-length-advisory-permanent.md) | Function-length advisory-permanent + 344-function grandfather list | ACCEPTED |
| [ADR-098](ADR-098-ceo-boot-audit-emit-register.md) | `/ceo-boot` audit_emit lifecycle action register + v1.12.1 wiring extensions | ACCEPTED |
| [ADR-099](ADR-099-changesets-adoption.md) | `changesets` workflow adoption (closeout aggregator, soft co-existence with CLAUDE.md narrative) | ACCEPTED |
| [ADR-100](ADR-100-trusted-dependencies-re-affirm.md) | `trustedDependencies` allowlist re-affirm — SP-NNN sign chain documents the same discipline | ACCEPTED |
| [ADR-101](ADR-101-replay-redact-helper.md) | Replay capture redaction helper (`replay_redact`) + R9 LIVE LGPD leak fix | ACCEPTED |
| [ADR-102](ADR-102-mcp-introspection-extends-042.md) | MCP introspection tools extending ADR-042 | ACCEPTED |
| [ADR-103](ADR-103-calendar-gate-final-purge.md) | Calendar gate final purge (extends ADR-095, supersedes ADR-093 §moratorium) | ACCEPTED |
| [ADR-104](ADR-104-adaptive-execution-kernel-advisory.md) | Adaptive Execution Kernel + Reality Ledger (advisory-only) | ACCEPTED |
| [ADR-104-AMEND-1](ADR-104-AMEND-1-aek-dated-promotion-criteria.md) | AEK Calibration Phases C2-C4 + Dated Promotion Criteria | PROPOSED |
| [ADR-105](ADR-105-multi-llm-coordinated-supersede.md) | Multi-LLM Sub-Agent Rail — Coordinated Supersede of ADRs 084 + 085 + 096 | ACCEPTED |
| [ADR-106](ADR-106-codex-mcp-adapter-contract.md) | Codex MCP Adapter Contract + Hook Coverage Mechanism | ACCEPTED |
| [ADR-107](ADR-107-pair-rail-mandatory-l2-plus.md) | Pair-Rail Mandatory L2+ — Asymmetric VETO Matrix Cases A-F | ACCEPTED |
| [ADR-108](ADR-108-cross-llm-veto-floor.md) | Cross-LLM VETO Floor — Extends ADR-052 | ACCEPTED |
| [ADR-109](ADR-109-codex-skill-rehash-protocol.md) | Codex SKILL.md Re-Hash Protocol — Format B Compatibility for Cross-LLM | ACCEPTED |
| [ADR-110](ADR-110-codex-pretool-enforcement.md) | Codex Pre-Tool Enforcement Hook — Block Mechanism for Asymmetric VETO Matrix | ACCEPTED |
| [ADR-111](ADR-111-locked-corpus-governance.md) | Locked Corpus Governance — Pair-Rail Promotion Gate | SUPERSEDED |
| [ADR-112](ADR-112-grandfather-cap-scope-clarification.md) | Grandfather-cap scope clarification — individual_skills cap vs domain_bundles cap | ACCEPTED |
| [ADR-113](ADR-113-plan-084-canonical-guard-extension.md) | PLAN-084 canonical guard extension — `.claude/plans/PLAN-084/canonical/*` | ACCEPTED |
| [ADR-114](ADR-114-codex-egress-redaction-symmetry.md) | Codex MCP egress redaction symmetry across ALL callsites | ACCEPTED |
| [ADR-115](ADR-115-post-sota-maintenance-mode.md) | Framework enters post-SOTA maintenance mode after PLAN-084 | ACCEPTED |
| [ADR-116](ADR-116-kernel-hard-deny-tier-0-extension.md) | KERNEL HARD-DENY tier-0 scope extension — 13 entries closing single-edit catastrophic bypass chain + ADR-040-AMEND-2 trust root | ACCEPTED |
| [ADR-116-AMEND-1](ADR-116-AMEND-1-kernel-extension-v2.md) | Kernel HARD-DENY tier-0 extension v2 — +30 deployable / +65 full enumerated paths | ACCEPTED |
| [ADR-117](ADR-117-adr-id-collision-rename-policy.md) | ADR-ID collision rename policy — going-forward doctrine | ACCEPTED |
| [ADR-118](ADR-118-god-mode-auto-usable-state.md) | Framework reaches god-mode AUTO-USABLE state on PLAN-088 close — capability_surface_delta=0 by mechanical SHA-pin | ACCEPTED |
| [ADR-118-AMEND-1](ADR-118-AMEND-1-phase-c-enforcing-flip.md) | Phase C — flip 4-persona AUTO defaults from advisory to enforcing | ACCEPTED |
| [ADR-119](ADR-119-sentinel-unlock-contract.md) | Sentinel-Unlock Contract Tightening | ACCEPTED |
| [ADR-120](ADR-120-pii-core-promotion.md) | PII core promotion — pii-data-flow + consent-lifecycle + dpo-reporting (renamed from ADR-111) | ACCEPTED |
| [ADR-121](ADR-121-sentinel-signers-rotation-policy.md) | Sentinel signers rotation policy — hot/cold split + M-of-N quorum + revocation channel | ACCEPTED |
| [ADR-122](ADR-122-dpop-mcp-bearer-replay-defense.md) | R-031 — DPoP MCP bearer-replay defense (Defer-to-v2.0 path with §A spec preserved) | ACCEPTED |
| [ADR-123](ADR-123-streaming-adapter-canonical-source.md) | BatchClaudeLiveAdapter — canonical source for batch + streaming dispatch | ACCEPTED |
| [ADR-124](ADR-124-post-audit-sota-execution-mode.md) | Post-audit-SOTA-execution-mode supersedes ADR-096 terminal verdict | ACCEPTED |
| [ADR-125](ADR-125-risk-tiered-defaulting-doctrine.md) | Risk-tiered defaulting doctrine for capability rollout | ACCEPTED |
| [ADR-126](ADR-126-governed-sidecar-capability-model.md) | Governed sidecar capability model (option D) — refines ADR-002 stdlib-only invariant | ACCEPTED |
| [ADR-127](ADR-127-pair-rail-advisory-promotion.md) | Pair-Rail Case B procedural-block advisory promotion + Phase 4 substantive-block pre-emptive advisory doctrine | ACCEPTED |
| [ADR-128](ADR-128-c2-vector-memory-capability-class.md) | C2 vector-memory capability class authorizing ADR | ACCEPTED |
| [ADR-129](ADR-129-c1-crypto-capability-class.md) | C1 crypto capability class — stdlib ssl MVP + cryptography sidecar reserved | ACCEPTED |
| [ADR-129-AMEND-1](ADR-129-AMEND-1-key-floor-waiver-lift.md) | C1 crypto capability class — lift §Key-floor-waiver + introduce SPKI pin + 90d key rotation cycle | ACCEPTED |
| [ADR-131](ADR-131-c5-dev-tools-capability-class.md) | C5 dev-tools capability class — first C-class authorizing ADR per ADR-126 §Part 7 | ACCEPTED |
| [ADR-132](ADR-132-goap-advisory-planning-doctrine.md) | GOAP advisory-only planning doctrine | ACCEPTED |
| [ADR-133](ADR-133-autonomous-loop-opt-in-capability-doctrine.md) | Autonomous-loop opt-in capability doctrine | ACCEPTED |
| [ADR-135](ADR-135-federation-contract-mvp.md) | Federation contract MVP — cross-machine trust boundary + 2-stage sentinel + audit-chain stitching | ACCEPTED |
| [ADR-135-AMEND-1](ADR-135-AMEND-1-write-mode-trust-boundary.md) | Federation contract — write-mode trust boundary + per-method RBAC + SPKI migration | ACCEPTED |
| [ADR-135-AMEND-2](ADR-135-AMEND-2-write-mode-activation.md) | Federation write-mode ACTIVATION — default-OFF wiring + activation pre-conditions | PROPOSED |
| [ADR-136](ADR-136-workflow-engine-doctrine.md) | Workflow-engine doctrine — spec-kit port study (SKIP recommended) | ACCEPTED |
| [ADR-136-AMEND-1](ADR-136-AMEND-1-workflow-primitive-adoption.md) | Workflow-primitive adoption (ADOPT-CONFINED) | ACCEPTED |
| [ADR-137](ADR-137-skill-priority-stack-decision.md) | Skill-priority-stack decision — spec-kit presets port (SKIP-DEFER) | ACCEPTED |
| [ADR-138](ADR-138-ac-format-priority-and-story-anchor.md) | AC format extension — priority + user-story + path discipline | ACCEPTED |
| [ADR-139](ADR-139-coverage-doctrine-tiered.md) | Tiered coverage doctrine — subprocess capture + per-module Tier-1 gate | ACCEPTED |
| [ADR-140](ADR-140-receiving-review-doctrine.md) | Receiving-review anti-sycophancy doctrine — superpowers BORROW-3 | ACCEPTED |
| [ADR-141](ADR-141-reduce-protocol.md) | Evidence-bound REDUCE protocol for swarm fan-out — Kimi-inspired, internally grounded | ACCEPTED |
| [ADR-142](ADR-142-opus-4-8-model-bump.md) | Opus 4.8 model bump — atomic VETO-floor + dispatch-table modernization | ACCEPTED |
| [ADR-143](ADR-143-git-hook-bypass-guard.md) | Git hook-bypass guard — new audit action + dual-auth escape hatch + fail-closed parse mode | ACCEPTED |
| [ADR-144](ADR-144-subagent-model-tiering-frontmatter.md) | Subagent model tiering via per-agent frontmatter — global CLAUDE_CODE_SUBAGENT_MODEL override prohibited | ACCEPTED |
| [ADR-145](ADR-145-cross-model-review-persona-demand-modality.md) | Cross-model Codex review as a recognized persona-demand satisfaction modality | (UNKNOWN) |
| [ADR-146](ADR-146-adversary-review-hook.md) | Adversary local-rules review hook — deterministic deny/ask gate, no model on the hot path | ACCEPTED |
| [ADR-147](ADR-147-eval-harness-doctrine.md) | Eval-harness doctrine — real-task reward benchmark, nightly/on-demand, quota-capped, no-float reward | PROPOSED |
| [ADR-148](ADR-148-canonical-pricing-source.md) | Canonical model-pricing source — models.dev-provenanced table, Owner-fetched, checksum-fail-CLOSED, advisory reconcile | ACCEPTED |
| [ADR-149](ADR-149-model-id-allowlist.md) | VETO-floor model allowlist (generation-portable governance) | (UNKNOWN) |
| [ADR-150](ADR-150-commit-signing-policy.md) | Commit-signing policy: signed-tag ratification + tiered signing requirement | (UNKNOWN) |
| [ADR-151](ADR-151-fan-plan-advisory-bridge.md) | /fan-plan advisory bridge — parse [P?][USn][path] ACs into a PROPOSE-only read-only fan-out | ACCEPTED |
| [ADR-152](ADR-152-claude-md-decomposition.md) | CLAUDE.md decomposition — `@imports` vs `.claude/rules/` + `paths:` (D1-measurement-gated) | PROPOSED |
| [ADR-153](ADR-153-compaction-continuity.md) | Compaction-continuity: PreCompact snapshot + PostCompact governance reinjection (H1) | ACCEPTED |
| [ADR-154](ADR-154-updatedinput-single-rewriter.md) | `updatedInput` corrective rewrites: the single-rewriter invariant (H5 force-push pilot) | ACCEPTED |
| [ADR-155](ADR-155-install-baseline-manifest.md) | Install/upgrade baseline SHA-256 manifest — preserve adopter customizations, recover the root PROTOCOL.md | ACCEPTED |
| [ADR-156](ADR-156-constitution-sync-cascade.md) | Constitution sync-cascade — advisory dependent-set re-verify + Sync Impact Report | ACCEPTED |

<!-- END ADR-INDEX -->

## Why retroactive ADRs

ADR-001 was written in Sprint 2 even though the decision was made
implicitly in Sprint 1. The debate round 1 on PLAN-002 flagged this as
a governance gap: "Sprint 1 made the decision, Sprint 2 should not repeat
it without documenting the first one." Retroactive ADRs are allowed when
(a) the decision is clearly load-bearing, (b) the code already encodes
it, and (c) a future reader would otherwise re-debate the same question.
