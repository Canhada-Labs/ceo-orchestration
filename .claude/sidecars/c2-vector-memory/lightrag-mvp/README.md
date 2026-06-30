# C2 vector-memory sidecar — `lightrag-mvp` (PLAN-097 / ADR-128)

This sidecar wraps the PLAN-041 LightRAG sidecar in the ADR-126
governed-sidecar capability model (manifest schema + boundary test
contract). It is the FIRST concrete C2 vector-memory sidecar.

## Quick facts

- **Capability class**: C2 vector-memory (per ADR-126 §Part 3)
- **Default tier**: B (conditional default-ON for routing per ADR-125)
- **Install tier**: C (Owner interactive consent in `install.sh`)
- **Authorizing ADR**: ADR-128
- **Kill-switch**: `CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED=0`
- **Legacy kill-switch (alias)**: `CEO_RAG_SIDECAR=0`
- **Min Python**: 3.10
- **Disk requirement**: ≥2 GiB free
- **RAM requirement**: ≥4 GiB (sidecar peaks 1-2 GiB @ 500k LoC)

## Activation predicate

The framework routes retrieval queries to this sidecar when ALL three
sub-clauses evaluate true:

1. `repo_profile == LARGE` per `detect-repo-profile.py` (LoC ≥ 200,000)
2. `sidecar_installed` — manifest file exists AND venv is intact
3. `sidecar_running` — Unix socket at `~/.ceo-orchestration/rag/sidecar.sock`
   responds to health probe within `CEO_RAG_QUERY_TIMEOUT_MS` (default 2s)

ANY kill-switch (class or legacy alias) set to `0` ALWAYS wins regardless
of predicate state (per ADR-062-AMEND-1 §Kill-switch precedence).

## Layout

```
.claude/sidecars/c2-vector-memory/lightrag-mvp/
├── manifest.json       # ADR-126 §Part 4 schema, validated by check-sidecar-manifest.py
├── boundary_test.py    # ADR-126 §Part 5 + ADR-128 §4 — fail-CLOSED in CI
├── install.sh          # (delegates to .claude/rag/install-sidecar.sh — preserved)
├── README.md           # this file
├── sidecar_code/       # non-stdlib code (chromadb / sentence-transformers / lightrag)
└── tests/              # sidecar-internal tests (pytest)
```

## Installation

```bash
# From repo root — Owner physical consent required (Tier-C per ADR-125)
bash .claude/rag/install-sidecar.sh
```

The existing PLAN-041 install script is preserved at `.claude/rag/`
for backward compatibility. The C2 manifest at this path delegates
to that installer; future migration to a self-contained installer
at `.claude/sidecars/c2-vector-memory/lightrag-mvp/install.sh` is
tracked under PLAN-097-FOLLOWUP if needed.

## Operation

1. **Start sidecar**: `ceo-rag start` (no change from PLAN-041 ADR-062)
2. **Build index**: `ceo-rag index` (one-time at 500k LoC ~4h)
3. **Verify health**: `ceo-rag status`
4. **Stop sidecar**: `ceo-rag stop`

Framework auto-wires routing when LARGE profile detected AND sidecar
running. No flag-flipping required.

## Boundary contract

Per ADR-126 §Part 5 + ADR-128 §4:

- **No core path imports `chromadb` / `sentence_transformers` / `lightrag`**.
  Enforced by `boundary_test.py` AST scan in CI.
- **No workflow invokes the sidecar directly** except via the canonical
  pattern declared in `manifest.isolation.allowed_workflow_invocation_patterns`.
- **No direct audit-log writes** — sidecar emits via brokered IPC; framework
  core writes the HMAC-protected chain.
- **No network egress at query time** — model download is one-time at
  install (governed by AC15 cost-envelope + AC13 fail-mode 2 no-net).

## References

- ADR-126 (governed sidecar capability model)
- ADR-128 (C2 vector-memory authorizing ADR)
- ADR-062 + ADR-062-AMEND-1 (RAG sidecar opt-in + LARGE-profile auto-wire)
- ADR-125 (risk-tiered defaulting doctrine — Tier B routing + Tier C install)
- PLAN-097 (this sidecar's implementing plan)
- PLAN-041 (original RAG sidecar plan)
- PLAN-062 (CAG/RAG adopter docs — CAG fallback always available)
