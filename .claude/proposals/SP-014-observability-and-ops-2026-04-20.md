---


id: SP-014
skill_slug: observability-and-ops
archetype: observability-engineer
proposed_at: 2026-04-20T21:40:00Z
source_lessons:
  - plan-044-p0-12-observability-and-ops
scan_injection_pass: true
diff_size_added: 25
diff_size_removed: 0
sha256_of_diff: 4bf2601e649242c9129a9a1cc74e6caeecc159c61a14ab1e3b687c49fc7d78a3
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-20T15:58:37Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-014 — skill patch proposal

**Target:** `.claude/skills/core/observability-and-ops/SKILL.md`
**Archetype:** observability-engineer
**Kind:** PLAN-044 P0-12 SKILL.md adopter-note append (append-only)

## Rationale

PLAN-044 P0-12 closure. `observability-and-ops/SKILL.md` is architecturally biased toward a real-time WebSocket-fed ingestion engine — its metric names (`feed.*`, `ws.*`, `entity.*`, `state.transitions`) are dogfood-specific. Fresh adopter for a CRUD API / batch worker / mobile BFF would mis-apply the names. This proposal appends a disclaimer naming the bias explicitly and pointing at the pattern level vs the name level. Pure-addition; §Metrics block rewrite is out of scope here (would exceed diff cap) and flagged for CEO.

## Provenance note

This proposal was hand-authored via `/tmp/gen_sp_006_015.py` as part of
the PLAN-044 Phase 5 / P0-12 SKILL.md generalisation sweep (PLAN-045
Wave 4 equivalent, Session 41 handoff). The diff is a **pure addition**
— append-only — and applies cleanly via `skill-patch-apply.py` which
collects `+`-prefixed lines from the ```diff fence below. No code
execution, no automated mutation; the amendment is a doc-only adopter-
note section appended to the end of the target `SKILL.md`. Stdlib-only
generator; no network; no third-party deps.

Rollback-safe: if promote fails, reverting removes ONLY the added
lines. No other file is touched. No state change. This is what shadow
mode guarantees per ADR-031.

## Proposed diff

```diff
--- a/.claude/skills/core/observability-and-ops/SKILL.md
+++ b/.claude/skills/core/observability-and-ops/SKILL.md
@@ -297,3 +297,28 @@
 - **`--no-tail` log commands often return only ~100 lines** — use streaming logs or grep for real debugging.
 - **SLO freshness breaches are normal for the first 5-10min after deploy** — cold start fills caches gradually. Don't page on startup staleness.
 - **Health endpoints can lie:** a trivial `/healthz` may return OK while the main process HTTP is unresponsive. Fix: `/healthz` must check real metrics (active sessions, event loop latency, memory).
+## Adopter Note — Metric Names + Architecture Bias (PLAN-044 P0-12)
+
+The §Three Pillars / §Metrics block enumerates concrete
+Prometheus metric names (`feed.events_received`, `feed.events_
+rejected`, `feed.processing_errors`, `ws.reconnects`, `entity.
+normalization_failures`, `state.transitions`, `feed.data_age_
+ms`, `feed.active_sessions`, `ws.active_connections`) drawn
+from the originating `ceo-orchestration` dogfood ingestion
+engine — a WebSocket-fed entity-normalisation pipeline.
+
+Those metric names are **illustrative**. The patterns they
+exemplify (counter for every observable event, gauge for every
+observable level, histogram for every observable latency-like
+value, labels for cardinality you care about) transfer to any
+service. The specific names (`feed.*` / `ws.*` / `entity.*`)
+should be renamed to fit your domain (e.g. `http.*` / `db.*` /
+`job.*` for a web API, or `mq.*` / `batch.*` for a worker).
+
+Likewise, the §Pitfalls section's `--no-tail` / `/healthz`
+examples come from the dogfood project's operational log
+culture — substitute your own log-tool invocations and your
+own health-endpoint path when spawning this skill in an
+adopter context. The observations (log commands can truncate
+silently; health endpoints can be trivial and lie) are
+universal; the tool names are not.
```
