# Ecosystem Parity · Cluster 1.2 — Context-mode orthogonal to Manifest

**Status:** ADR-066 ACCEPTED (Session 49 P04). Documentation-only
this wave; implementation opt-in per adopter (future).

## Why this exists

Framework already ships **Manifest** via ADR-062 (LightRAG sidecar
MCP): semantic compression of background corpus. It reduces token
cost by summarizing.

**Context-mode** is different. It preserves *literal* slices of
context — last-N messages, hot-path diffs, specific file patches —
without compression, with budget-aware truncation. Losing those
slices regresses quality in long-horizon sessions even when the
Manifest summary is good.

ADR-066 records: these are **orthogonal**, not redundant. An
adopter can (and often should) activate both simultaneously.

## Quick decision tree

```
Session running > 3 turns?
│
├── No  → Manifest is probably enough. context-mode off.
│
└── Yes → Sub-agents hallucinating or missing recent edits?
    │
    ├── No  → Manifest enough; context-mode off.
    │
    └── Yes → Activate context-mode for hot-path slices.
             Keep Manifest on for cold corpus.
```

## Capability matrix

| Concern | Manifest (ADR-062) | context-mode (ADR-066) |
|---|---|---|
| **Target** | cold corpus (docs, specs, old logs) | hot slices (last-N msgs, recent diffs) |
| **Compression** | semantic summary | none (literal) |
| **Budget** | large — big corpus inputs | small — bounded by turn count |
| **Failure mode** | summary misses detail | budget exceeded → truncation |
| **Adopter install** | `pip install lightrag` + sidecar config | none (stdlib opt-in) |
| **Kill switch** | `CEO_RAG_SIDECAR=off` | `CEO_CONTEXT_MODE=off` |

## Activation plan (future — today is docs-only)

ADR-066 is ACCEPTED with `blast_radius: L2-narrow`. No code is wired
yet. A future PLAN-046 wave will ship:

- `.claude/hooks/_lib/context_mode.py` — bounded literal-slice
  capture.
- Integration in `_lib/payload.py::build_turn_context` (canonical-
  guarded path; requires Owner-signed sentinel round).
- Adopter env var `CEO_CONTEXT_MODE_TURNS=N` (default 3).

For now, adopters with the need can either:

1. Wait for the implementation wave.
2. Implement a project-specific wrapper in their own hooks (the
   pattern is straightforward; see the spec for a minimal scaffold).

## Cost calculator

If your sessions average `T` turns with `M` messages/turn and `K`
characters/message, a literal last-N (N=3) context-mode slice adds
roughly `3 × M × K` chars per turn. Sample numbers:

| Workload | M × K per msg | Adds/turn |
|---|---|---|
| Chat-heavy | 20 msg × 200 char | ~12 KiB |
| Code-review | 5 msg × 2 KiB | ~30 KiB |
| Research deep-dive | 10 msg × 1 KiB | ~30 KiB |

Compare to Manifest summary which typically runs 2-8 KiB. They stack
additively, hence the importance of the kill-switch guidance above.

## When NOT to activate context-mode

- Short sessions (< 3 turns) — Manifest alone is enough.
- Sub-agents are not hallucinating; Manifest summary covers every-
  thing they need.
- Budget is the binding constraint; you can't afford +30 KiB/turn
  even if quality improves slightly.

## Clean-room note

The capability name and decomposition are from the public
awesome-context repo's discussion threads. No code is lifted; the
framework's implementation (when it lands) will be a stdlib-only
bounded-queue wrapper around the existing payload layer.

## Related

- ADR-066 — this capability's architectural record
- ADR-062 — Manifest via LightRAG sidecar
- PLAN-046 — ecosystem parity roadmap
- PLAN-026 — external audit that surfaced the re-classification

## Rollback

Since there's nothing wired in this wave, rollback is:

- Revert the ADR-066 commit (flips ACCEPTED → rejected), which is
  a docs-only change.
- The adopter guide stays in-repo as a reference for the decision
  history, marked superseded.
