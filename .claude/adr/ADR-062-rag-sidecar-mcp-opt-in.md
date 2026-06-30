---
id: ADR-062
title: RAG sidecar MCP opt-in (stdlib-only preserved)
status: ACCEPTED
date: 2026-04-19
accepted_date: 2026-04-19
deciders: CEO + Owner + 5-agent debate round 1 (code-reviewer + security-engineer + performance-engineer + qa-architect + devops) — all ADJUST verdict; security VETO lifted after A4/A8/A9/A10 closures
related_plans: [PLAN-041, PLAN-027]
blast_radius: moderate
---

# ADR-062 — RAG sidecar MCP opt-in (stdlib-only preserved)

## Status

ACCEPTED — Round 1 debate consensus reached Session 36 (2026-04-19).
All 5 agents returned ADJUST. 11 P0 consensus adjustments (A1-A11)
landed in PLAN-041 Phases 2-6. Security VETO automatically lifted
when A4 (output_scan integration), A8 (requirements.lock +
--require-hashes), A9 (pre-embed secret scan + storage perms), A10
(Unix socket mandatory POSIX + tokenized TCP Windows) all closed.

See `.claude/plans/PLAN-041/debate/round-1/consensus.md` for the
full synthesis, and `consensus.md §A1-A11` for the concrete
adjustment items (all applied in commits `af8a8ce`, `3132d9a`,
`4abc97d`, and this closeout).

## Context

External audit PLAN-026 (Session 34, 2026-04-18) evaluated LightRAG
(HKUDS EMNLP 2025, MIT, 33.8k stars) — a mature graph+vector RAG
implementation. Initial classification was **T2 WATCH** because
LightRAG requires:

- Python 3.10+ (framework core is pinned 3.9+ per ADR-002)
- Chroma vector store
- Embedding models (sentence-transformers ~100 MiB download)
- At least 1-2 GiB RAM at 500 k LoC index size

Embedding LightRAG directly into the framework would break the
**stdlib-only invariant (ADR-002)** that makes the framework
dependency-free, auditable, and portable.

However, Owner disclosed Session 34 that the target install
codebase (adopter-1) is ~500 k LoC across engine + frontend. At
that scale Claude consistently hits context-window limits during
cross-module queries without a pre-processed index. The value
proposition of retrieval-augmented retrieval at 500 k LoC is
established (LightRAG paper §4 + independent benchmarks).

The tension: (a) framework must stay stdlib-only for core adopters;
(b) 500 k LoC adopters gain disproportionate value from RAG.

## Decision

Ship **LightRAG as an opt-in sidecar process** bridged via MCP
(Model Context Protocol), not embedded in the framework core.

### Architecture

```
┌──────────────────────────────────┐       ┌──────────────────────────┐
│ ceo-orchestration framework core │       │  LightRAG sidecar (opt-in)│
│ - Python 3.9+                    │       │ - Python 3.10+            │
│ - stdlib-only                    │       │ - isolated venv            │
│ - bridge.py (stdlib MCP client)  │──MCP──│ - Chroma + embeddings      │
│ - CEO_RAG_SIDECAR=0 default      │       │ - `~/.ceo-orchestration/  │
│ - fallback → grep on timeout     │       │    rag/<project-id>/`     │
└──────────────────────────────────┘       └──────────────────────────┘
```

### Invariants preserved

- ✅ **stdlib-only (ADR-002):** framework core imports nothing
  non-stdlib. The MCP bridge in `.claude/rag/bridge.py` uses only
  `json`, `socket`, `subprocess`, `urllib` from stdlib. LightRAG
  and its deps live in an **isolated venv** under
  `.claude/rag/venv/` (git-ignored).
- ✅ **Python ≥3.9 framework:** sidecar venv can require 3.10+
  independently; framework unaffected.
- ✅ **Fail-open (ADR-005):** sidecar down / slow / missing →
  bridge returns `None`; caller must handle `None` as "RAG
  unavailable, fall back to grep". Framework never blocks on
  sidecar state.
- ✅ **Audit-log v2.8+ (ADR-055):** 3 new audit actions —
  `rag.query.issued`, `rag.query.returned`, `rag.query.fallback`.
- ✅ **MIT license:** LightRAG is MIT per HKUDS repo. Compatible
  with framework license.
- ✅ **Zero credential hardcoding:** sidecar reads config from
  `~/.ceo-orchestration/rag/config.json` (opt-in, user-created)
  or env vars `CEO_RAG_*`. No secrets in framework git.
- ✅ **Opt-in default:** `CEO_RAG_SIDECAR=0` is the default —
  adopters must explicitly enable. Zero overhead when off.

### Interface (MCP tools exposed)

The sidecar exposes 3 MCP tools that the framework bridge calls:

- `rag.search(query: str, top_k: int = 5) → list[result]` —
  semantic search across the indexed corpus. Returns file+line
  refs with match scores.
- `rag.timeline(symbol: str) → list[related]` — temporal view of
  symbol evolution (when defined, when changed, cross-references).
- `rag.get_observations(id: str) → str` — full retrieval of a
  node's content by opaque id from a prior search result.

Each tool respects a hard 2 s timeout (`CEO_RAG_QUERY_TIMEOUT_MS`
configurable). Timeout → `None` → fallback.

### Storage layout

```
~/.ceo-orchestration/rag/
├── <project-id>/        # sha256 of repo path
│   ├── index.sqlite     # LightRAG graph store
│   ├── chroma/          # vector store
│   ├── embeddings.bin   # model weights (shared across projects)
│   └── manifest.json    # last-indexed commit, corpus hash
└── config.json          # global sidecar config
```

Per-project isolation + shared embeddings = compact footprint.

### Indexing policy

- **Full index:** on first `ceo-rag index` invocation. Walks repo
  per `.gitignore`. Extracts: symbols (Python AST), docstrings,
  markdown prose, ADRs. Emits embeddings via LightRAG default
  model.
- **Incremental:** on `ceo-rag index --incremental`, diff HEAD vs
  last-indexed commit; update only affected nodes. Target <1 min
  per commit at 500 k LoC.
- **Manifest verification:** bridge checks manifest freshness before
  querying; if stale beyond threshold, emits warning but still
  returns results (fail-open).

### Sidecar lifecycle

- **Start:** `ceo-rag start` launches the MCP server on a
  local-only Unix socket at `~/.ceo-orchestration/rag/sidecar.sock`.
- **Stop:** `ceo-rag stop` sends SIGTERM.
- **Health:** bridge probes `rag.search("__health__", 0)` on first
  query per session; records sidecar availability for the session.
- **Crash recovery:** if sidecar crashes mid-query, bridge times
  out → fallback. Next query re-probes health.
- **Auto-start:** explicitly NOT. Adopter must start manually.
  Rationale: keeps the "zero background process by default" promise.

### Authentication

Local Unix socket with `0600` permissions. No network exposure.
No token-based auth (over-engineering for local process).
Loopback-only TCP (127.0.0.1:port) available via config for
Windows/WSL compatibility — port bound with `SO_EXCLUSIVEADDRUSE`
on Windows.

## Consequences

### Positive

- Adopters at 500 k + LoC get retrieval-augmented context at
  framework-aware granularity (symbol + docstring + ADR).
- Stdlib-only invariant preserved; smaller adopters pay zero cost.
- LightRAG upgrade path independent of framework releases.
- Sidecar crash does not break the CEO session.
- Clean separation of governance-critical (framework) from
  resource-heavy (RAG index).

### Negative

- Operational complexity: adopters must start sidecar explicitly.
  Mitigated by `docs/INSTALL-RAG.md` + `ceo-health.py` RAG probe.
- Two Python runtimes to keep in sync (framework 3.9+, sidecar
  3.10+). Mitigated by sidecar venv isolation.
- Indexing 500 k LoC takes ~4 h one-time. Mitigated by incremental
  updates per commit.
- MCP protocol subset — if LightRAG changes MCP surface, bridge
  needs update.

### Neutral

- New ADR-062 + new `.claude/rag/` directory. No existing file
  modifications beyond `settings.json` + 1 line in
  `.claude/hooks/_lib/rag_events.py`.

## Alternatives considered

1. **Embed LightRAG in framework core.** Rejected — breaks
   stdlib-only invariant.
2. **Ship a framework-native toy RAG.** Rejected — reinventing
   LightRAG's graph+vector implementation poorly.
3. **Vendor-specific (OpenAI embeddings).** Rejected — introduces
   network dependency + credential surface.
4. **No RAG, rely on Claude's 1 M context.** Rejected — even at
   1 M tokens, 500 k LoC is ~1 GiB raw; cross-module queries
   need structured retrieval, not raw concat.

## Kill-switches

- `CEO_RAG_SIDECAR=0` — framework ignores sidecar completely
  (default). Zero overhead. Fallback path unchanged.
- `CEO_RAG_QUERY_TIMEOUT_MS=2000` — bridge timeout (default 2 s).
- `CEO_RAG_HEALTH_PROBE=0` — skip health probe on first query
  (for tests + offline dev).
- `CEO_RAG_DOWN_LOG_LEVEL=warn` — sidecar-down log level (warn
  default; switch to `debug` to silence in production).

## References

- LightRAG paper (HKUDS, EMNLP 2025) — graph+vector RAG
- PLAN-026 external audit (Session 34) — initial WATCH → HIGH
  reclassification
- PLAN-027 UltraFramework roadmap §Wave A+
- PLAN-041 — this implementation plan
- ADR-002 (stdlib-only invariant)
- ADR-005 (fail-open contract)
- ADR-055 (audit-log HMAC chain, v2.8)

## Open questions (resolved in debate Round 1)

1. **Sidecar auto-start?** — NO. Explicit. [See debate §lifecycle]
2. **Auth token?** — NO. 0600 Unix socket. [See debate §security]
3. **Storage dir: `~` vs repo?** — `~/.ceo-orchestration/rag/<project-id>/`
   to survive `git clean -fdx`. [See debate §storage]
4. **Incremental frequency?** — per-commit, opt-in git hook.
   [See debate §indexing]
5. **Bridge timeout?** — 2 s. [See debate §performance]

## Enforcement commit

`af8a8ceaaec2` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
