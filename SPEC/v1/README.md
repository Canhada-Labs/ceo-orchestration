# ceo-orchestration Compliance SPEC — v1

> **Status:** v1.9.1 (GA patch, aligned with repo `VERSION`)
> **Next:** v2.0.0 (or v1.10.0 per ADR-073 — gated on PLAN-051 Phase 8 outcome)
> **First published:** v1.0.0-rc.1 (2026-04-12); minor-version track
> has added 28 schema files through the v1.x.y line.

This directory is the **public contract** of the ceo-orchestration
framework. A third party can implement a compatible runtime (alternative
IDE adapter, alternative hook engine, alternative dashboard) by
consuming these schemas — no reading of Python source required.

## Contract surface

30 normative files — 28 `*.schema.md` schemas + 2 additional normative
docs (`install-cli.md`, `npm-shim.md`). Grouped by subsystem below.
(`claude-sdk-compat.md` is present in this directory but STAGED, not yet
canonical, so it is not counted in the contract surface.)
**Source of truth** column points at either the in-directory normative
text or an upstream repo-root document; schemas without an upstream
source are fully self-authoritative.

### Core governance

| File | Contract | Source of truth |
|---|---|---|
| [`plan.schema.md`](./plan.schema.md) | Plan file frontmatter + lifecycle | `.claude/plans/PLAN-SCHEMA.md` |
| [`debate.schema.md`](./debate.schema.md) | Debate round directory layout + critique + consensus contract | `.claude/plans/DEBATE-SCHEMA.md` |
| [`audit-log.schema.md`](./audit-log.schema.md) | Event stream JSONL — v1 `agent_spawn` + v2 typed events | `.claude/plans/AUDIT-LOG-SCHEMA.md` |
| [`audit-query.schema.md`](./audit-query.schema.md) | `audit-query.py` CLI envelope | this directory |
| [`hook-io.schema.md`](./hook-io.schema.md) | Hook input payload + output decision shape | this directory |
| [`sentinel-format.schema.md`](./sentinel-format.schema.md) | Canonical-edit sentinel file format (ADR-078) | this directory |

### Skills + agents

| File | Contract | Source of truth |
|---|---|---|
| [`skill-frontmatter.schema.md`](./skill-frontmatter.schema.md) | SKILL.md frontmatter minimum contract | this directory |
| [`skill-index.schema.md`](./skill-index.schema.md) | Skill registry index format | this directory |
| [`skill-proposals.schema.md`](./skill-proposals.schema.md) | SP-NNN proposal format (ADR-031) | this directory |
| [`squad-manifest.schema.md`](./squad-manifest.schema.md) | Domain/squad bundle manifest (ADR-009) | this directory |
| [`scratchpad.schema.md`](./scratchpad.schema.md) | Shared working-memory scratchpad | this directory |
| [`session-graph.schema.md`](./session-graph.schema.md) | Session continuity graph (ADR-038) | this directory |

### Adapters + integrations

| File | Contract | Source of truth |
|---|---|---|
| [`adapters.schema.md`](./adapters.schema.md) | Hook adapter ABI (ADR-008) | this directory |
| [`normalized_envelope.schema.md`](./normalized_envelope.schema.md) | Canonical NormalizedEvent (ADR-008) | this directory |
| [`live-adapters-policy.schema.md`](./live-adapters-policy.schema.md) | LiveCallPolicy contract (ADR-040) | this directory |
| [`mcp-server.schema.md`](./mcp-server.schema.md) | MCP server contract (ADR-042) | this directory |
| [`rag-sidecar.schema.md`](./rag-sidecar.schema.md) | RAG sidecar MCP contract (ADR-062) | this directory |

### Policy + evaluation

| File | Contract | Source of truth |
|---|---|---|
| [`policy-dsl.schema.md`](./policy-dsl.schema.md) | Policy-as-code DSL (ADR-045) | this directory |
| [`tier-policy.schema.md`](./tier-policy.schema.md) | Dynamic tier policy (ADR-064) | this directory |
| [`tournament-report.schema.md`](./tournament-report.schema.md) | Agent-eval tournament output (ADR-063) | this directory |
| [`benchmarks.schema.md`](./benchmarks.schema.md) | Skill-benchmark runner output | this directory |
| [`judge-payload.schema.md`](./judge-payload.schema.md) | LLM-as-judge envelope (ADR-030) | this directory |
| [`red-team-corpus.schema.md`](./red-team-corpus.schema.md) | Adversarial debate corpus | this directory |

### State + operational

| File | Contract | Source of truth |
|---|---|---|
| [`state-stores.schema.md`](./state-stores.schema.md) | Unified agent-state backend (ADR-027) | this directory |
| [`memory-shared.schema.md`](./memory-shared.schema.md) | Shared working memory (ADR-034) | this directory |
| [`replay.schema.md`](./replay.schema.md) | Deterministic replay (ADR-046) | this directory |
| [`predict-budget.schema.md`](./predict-budget.schema.md) | Predictive budgeting (ADR-047) | this directory |
| [`soc2-control-map.schema.md`](./soc2-control-map.schema.md) | SOC2 audit trail mapping (ADR-043) | this directory |

### Installer + distribution

| File | Contract | Source of truth |
|---|---|---|
| [`install-cli.md`](./install-cli.md) | `install.sh` CLI flags as versioned API | this directory |
| [`npm-shim.md`](./npm-shim.md) | NPM tarball distribution shim | this directory |

### Authoritative-source pattern

SPEC/v1 ships schemas in **two compatible patterns**; the front-matter
declares which:

| Pattern | Header field | Examples | Meaning |
|---|---|---|---|
| **Mirror** | `Normative source: <path>` | `audit-log.schema.md`, `plan.schema.md`, `debate.schema.md`, `skill-frontmatter.schema.md`, `hook-io.schema.md` | The schema mirrors a repo-internal authoritative source; external drift is an error. |
| **Self-authoritative** | `Normative source: SELF` | `tier-policy.schema.md`, `tournament-report.schema.md`, `rag-sidecar.schema.md`, `predict-budget.schema.md`, `memory-shared.schema.md`, 18+ others | This file IS the authority; there is no internal document paired with it. |

Both patterns carry equal contract weight. The difference is internal:
mirror schemas track an authoritative doc inside the repo; self-
authoritative schemas track external consumer-facing contracts only.
ADR-007 §Scope documents when each applies.

Adopters reading the SPEC contract surface do not need to distinguish
the two — every `*.schema.md` file is a published contract. The
frontmatter distinction is for CI drift-checks (mirror-pattern
schemas get a bidirectional drift test; self-authoritative schemas
do not).

## SemVer contract

The Compliance SPEC is versioned with **SemVer 2.0.0**. The SPEC version
is in `VERSION` at repo root. Adopters pin their local install to a SPEC
version via `upgrade.sh --pin v1.x.y`.

### What counts as MAJOR (breaking)

- Removing or renaming a field in any schema
- Changing a hook I/O shape (input field names, decision JSON keys)
- Changing audit-log event discriminators (`action`, `event_schema`)
- Removing an `install.sh` flag or changing its argument semantics
- Removing an `action` literal from the audit-log v2 known set
- Increasing minimum Python version

### What counts as MINOR (additive)

- Adding an optional field to any schema
- Adding a new hook (default-off or fail-open)
- Adding a new archetype to team.md
- Adding a new skill or skill tier
- Adding a new `install.sh` flag
- Adding a new `action` literal to the audit-log v2 known set (requires a new ADR)

### What counts as PATCH (non-behavioral)

- Bug fixes that preserve observable behavior
- Documentation improvements
- Test additions
- Shell portability fixes

### Deprecation policy

Fields or flags marked for removal ship with:

```yaml
deprecated_in: "1.4.0"
removed_in: "2.0.0"
```

A minimum **90-day window** between `deprecated_in` and `removed_in`.
`validate-governance.sh` warns on use of deprecated items; the CLI
prints a deprecation notice mirroring HTTP `Sunset` + `Deprecation` +
`Link` headers.

### Experimental fields

Fields prefixed with `x-` are experimental; they can be added or
removed in MINOR releases without a deprecation window. Production
consumers MUST NOT depend on `x-*` fields.

## What "ceo-orchestration compliant" means

A system is compliant with SPEC v1 if:

1. It can parse and validate plan files per `plan.schema.md`
2. It can emit audit-log events conforming to `audit-log.schema.md` v1 (v2 optional for observers)
3. Its governance hooks emit decisions conforming to `hook-io.schema.md`
4. It documents skill frontmatter per `skill-frontmatter.schema.md`
5. If it provides an installer, the CLI conforms to `install-cli.md`

Compliance is self-declared; there is no certification body.

## Conformance test suite

Not yet shipped in v1.0.0-rc.1. Deferred to Sprint 5 (consensus
rejected/deferred item §1). Until then, `validate-governance.sh` in
this repo is the reference check.

## Change log

See [`CHANGELOG.md`](../../CHANGELOG.md) at repo root.

## References

- ADR-007: SemVer contract and the release candidate policy
- ADR-005: Audit log event stream v2 (informs `audit-log.schema.md`)
- ADR-006: Derived registry (informs `skill-frontmatter.schema.md`)
