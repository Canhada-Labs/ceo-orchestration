# ADR-085 — Framework landscape 2026-04 — Claude-only positioning thesis

## Status

ACCEPTED — Wave A re-ceremony 2026-04-27 — round-21 sentinel — Owner key 0000000000000000000000000000000000000000

## Context

Session 60 (2026-04-24) executed a thorough landscape audit at Owner
request: 10 thread-viral repos + 4 mainstream orchestrators + 3
adjacencies = **17 frameworks compared** across 22 capabilities.

The original PLAN-056 framing identified "model-agnostic" as a gap
and proposed PLAN-057 to close it. Session 67 (2026-04-27) Owner
directive reframed: ceo-orchestration is **THE Claude orchestrator**;
the thesis is depth over breadth.

This ADR formalizes the Claude-only positioning as durable record.

## Landscape summary (17 frameworks)

### Round 1 — 10 thread-viral repos (Session 60)

| Framework | Type | Comparison verdict |
|---|---|---|
| OpenHands | runtime/agent harness | orthogonal (runtime, not orchestrator) |
| Aider | code-edit CLI | orthogonal (single-task) |
| Cline | VS Code agent | orthogonal (IDE plugin) |
| Claude Task Master | task tracker | partial overlap (workflow-only) |
| CrewAI | multi-agent orchestrator | direct competitor (multi-LLM) |
| LangGraph | DAG agent framework | direct competitor (multi-LLM) |
| n8n | workflow automation | orthogonal (general-purpose) |
| Coolify | deployment platform | orthogonal (DevOps) |
| PostHog | product analytics | orthogonal (observability) |
| Chatwoot | customer support | orthogonal (CRM) |

### Round 2 — 4 mainstream orchestrators + 3 adjacencies (Session 60)

| Framework | Type | Verdict |
|---|---|---|
| **MetaGPT** | multi-agent | **paralelo filosófico mais direto** ("Code = SOP(Team)" — same thesis as our skill+team protocol) |
| Microsoft Agent Framework | multi-agent (AutoGen successor) | competitor in maintenance mode |
| **OpenAI Agents SDK** | multi-agent (Swarm successor) | **arch-convergence** — Guardrails primitive in core |
| Google ADK | multi-agent | competitor (Google-stack focus) |
| Claude Agent SDK | our base | dependency (Anthropic upstream) |
| Semantic Kernel | multi-agent | competitor (Microsoft-stack focus) |
| Portkey Gateway | LLM router | adjacency (200+ providers) |
| Arize Phoenix | observability | adjacency (LLM observability) |

## 22 capability × 17 framework matrix (summary, full in memory)

### 14 capabilities EXCLUSIVE to ceo-orchestration

1. **VETO-floor model assignment** (ADR-052) — staff archetypes
   pinned to Opus 4.7
2. **ADR lifecycle with refused taxonomy** — proposed/accepted/refused
   reasons enumerated (PLAN-051 §3.1)
3. **Debate consensus per ADR-058** — multi-archetype Round-1 + 2
   convergence rule
4. **3-strike persona accountability** (per `team.md`)
5. **Hook governance enforcement** — PreToolUse/PostToolUse hooks
   blocking spawn governance
6. **Canonical-edit sentinel** (ADR-010) — Owner-signed approval for
   canonical paths
7. **Audit-log HMAC chain** (ADR-055) — tamper detection
8. **Refused-ADR taxonomy** — formalized cap (≤2/5 items per sprint)
9. **Conformance TLA+ harness** — formal verification of swarm
   coordinator
10. **Token-economy detectors** — 6 named detectors
    (retry_churn, tool_cascade, looping, wasteful_thinking,
    weak_model, overpowered)
11. **Memory by type** (user/feedback/project/reference)
12. **SPEC v1 published compliance contract** — public schema files
13. **Install profile (`--profile core,fintech`)** — domain skills
14. **Plan lifecycle** — draft/reviewed/executing/done/refused

### 5 capabilities at parity with best-in-class

1. Multi-agent orchestration (CrewAI, LangGraph, MS Agent Framework,
   OpenAI Agents SDK, MetaGPT all comparable)
2. Skill protocol (overlapping with MetaGPT's roles + tools)
3. Audit log JSONL (Phoenix has spans; ours has actions; comparable)
4. CLI ergonomics (Claude Code parity with Aider/Cline)
5. Hooks/middleware extensibility (LangGraph + ADK + Semantic Kernel
   all extensible; our hooks are Claude-stack-specific)

### 3 gaps identified (Session 60) — REVISED Session 67

| Gap | Original plan | Session 67 disposition |
|---|---|---|
| **Checkpointing** (LangGraph has it) | Phase 4 of PLAN-056 (3-5 dev-dias) | **REFUSED** via separate ADR — audit-log JSONL captures intermediate state; ad-hoc resume via memory + plan files; no concrete dogfood need observed |
| **Guardrails-library exportable** (OpenAI Agents SDK has it) | Phase 1 of PLAN-056 (2-3 dev-dias) | **REFUSED** via separate ADR — Claude-only directive: framework guardrails are first-class internal; standalone export contradicts depth-over-breadth thesis |
| **OpenTelemetry-native emit** (Phoenix has it) | Phase 5 of PLAN-056 (1-2 dev-dias) | **REFUSED** via separate ADR — audit-log JSONL is canonical observability; `audit-telemetry.py` covers Owner queries; OTel adds dependency without proven uplift |

## Decision

The **Claude-only positioning is the framework's strategic moat**.
Documented as binding decision:

1. **Multi-LLM expansion is permanently refused** (ADR-084).
2. **Framework guardrails remain Claude-stack-specific**, not
   exported (ADR-088).
3. **Checkpointing remains audit-log-based**, not separate state
   machine (ADR-086).
4. **Observability remains audit-log JSONL + audit-telemetry.py**,
   not OTel (ADR-087).

These decisions reframe the original PLAN-056 "5 deliverables to
close gaps" into "3 deliverables that document depth + 3 ADRs that
refuse breadth":

| Item | Disposition |
|---|---|
| Phase 1 Guardrails skill repackaging | **REFUSED via ADR-088** |
| Phase 2 Claude Agent SDK compat matrix | **SHIPPED** as `SPEC/v1/claude-sdk-compat.md` |
| Phase 3 Framework Landscape ADR + memory | **SHIPPED** as ADR-085 (this) + memory file |
| Phase 4 Debate + phase checkpointing | **REFUSED via ADR-086** |
| Phase 5 OpenTelemetry span emit | **REFUSED via ADR-087** |
| Phase 6 Closeout + v1.11.0 tag | **SHIPPED** Session 67 D5 |

## Consequences

### Positive

- Strategic positioning is now load-bearing artifact (ADR), not
  marketing copy. Auditors + adopters can cite this ADR.
- Roadmap clarity: 18-25 dev-dias of PLAN-057 + 6-10 dev-dias of
  PLAN-056 Phase 1+4+5 removed permanently. Total ~25-35 dev-dias
  freed.
- Maintenance burden is 1-vendor (Anthropic Claude); no per-vendor
  bug surface.
- All depth-axis capabilities (governance, audit, hooks, MCP, skill
  protocol) remain first-class.

### Negative

- Adopters wanting Gemini/OpenAI must use a different orchestrator.
  Acceptable — the framework is opinionated.
- 1 of 5 parity capabilities (model-agnostic) becomes intentional
  permanent gap. README must say so explicitly.
- 3 of 22 capability gaps are refused rather than closed. README
  must explain why with positive framing ("optimized for X, not Y").

### Neutral

- Existing PRs / ADRs / hooks remain valid; this is positional, not
  technical.
- Future Claude vendor moves (e.g. Anthropic ships native MCP
  provenance) free this framework's roadmap; we get more time to
  deepen Claude-stack specificity.

## Alternatives considered

### A. Multi-LLM expansion via PLAN-057 (REJECTED)

See ADR-084 for full reasoning. Cost-vs-benefit + thesis dilution.

### B. Hybrid (Claude-default + multi-LLM opt-in) (REJECTED)

Half-step. Either we are Claude-only (clean thesis) or multi-LLM
(must commit to per-vendor maintenance). Hybrid combines worst of both.

### C. Generic abstraction layer (no specific vendors) (REJECTED)

YAGNI. Speculative architecture without concrete consumer.

## Enforcement commit

To be filled in at Session 67 D5 closeout (this ADR's promotion to
canonical path lands in the closeout commit + README/GOVERNANCE.md
updates).

## References

- ADR-084 — PLAN-057 multi-adapter REFUSED (sister deliverable)
- ADR-086 — Phase checkpointing REFUSED (sister deliverable)
- ADR-087 — OpenTelemetry emit REFUSED (sister deliverable)
- ADR-088 — Guardrails-library export REFUSED (sister deliverable)
- PLAN-051 §3.1 — Refused-ADR taxonomy (reasons enumerated)
- PLAN-056 — Framework Landscape closeout (this plan's parent;
  shipping Phase 2 + 3 + 6, refusing 1 + 4 + 5)
- Memory `project_framework_landscape_2026_04_27.md` — full matrix
  + Claude-only thesis amendment.
