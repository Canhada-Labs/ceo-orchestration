---


id: SP-015
skill_slug: testing-strategy
archetype: qa-architect
proposed_at: 2026-04-20T21:40:00Z
source_lessons:
  - plan-044-p0-12-testing-strategy
scan_injection_pass: true
diff_size_added: 32
diff_size_removed: 0
sha256_of_diff: e7a76058ed33e22c05fdc6395d8c91e3ce4d04650b239d4978195695f4319394
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-20T15:58:37Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-015 — skill patch proposal

**Target:** `.claude/skills/core/testing-strategy/SKILL.md`
**Archetype:** qa-architect
**Kind:** PLAN-044 P0-12 SKILL.md adopter-note append (append-only)

## Rationale

PLAN-044 P0-12 closure. `testing-strategy/SKILL.md` is the largest core skill (951 lines) and carries the heaviest originating-project flavour (`vitest 4.x`, `src/__tests__/`, reconnect/checksum/streaming language, IPC/worker_threads assumptions). The top-of-file portability note is one sentence; fresh adopters skim past it. This proposal appends an explicit per-subsection mapping so the adopter can do a targeted substitute-rename rather than a full skill rewrite. In-place rewrite of §Current State was considered — rejected because the table has worked-example value and an append disclaimer is cheaper for the same adopter-UX win.

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
--- a/.claude/skills/core/testing-strategy/SKILL.md
+++ b/.claude/skills/core/testing-strategy/SKILL.md
@@ -949,3 +949,35 @@
 | Testing in production only | Typo deploys to prod | CI runs tests before deploy |
 | `any` in test types | Hides type mismatches | Use proper types in tests too |
 | Testing private methods | Couples to implementation | Test via public interface |
+## Adopter Note — Runner Framing + Example Biases (PLAN-044 P0-12)
+
+This skill's top portability note ("Examples use vitest, but
+the patterns apply to Jest, Mocha, pytest, Go testing, and
+any mainstream test runner") is honest — but several
+subsections below carry originating-project biases that are
+worth naming explicitly for fresh adopters:
+
+- §Current State table lists `Framework: vitest 4.x`,
+  `src/__tests__/` location, and `TypeScript errors: 0
+  target / tsc --noEmit clean`. Replace with your runner,
+  your test-file location, and your typecheck tool before
+  citing in review.
+- §External integration test design references `mocking
+  transport, simulating reconnect, checksum validation for
+  streaming sources` — that is the originating ingestion-
+  engine's test shape. Your integration-test shape may be
+  HTTP-mocking, fixture-replay, or sandbox-environment.
+- §Domain math tests reference `boundary values, precision
+  edge cases` — universal when your domain has math, but
+  the originating-project examples come from financial-
+  instrument pricing. Substitute your own domain's
+  boundary cases.
+- §E2E multi-process tests (IPC, worker lifecycle) assume
+  Node's cluster/worker model. On other runtimes the
+  equivalent is different (Python multiprocessing, Go
+  goroutine test harnesses, JVM test containers).
+
+The patterns (mocking at the transport seam, asserting on
+observable state not private calls, mutation testing to
+verify test quality, CI-runs-tests-before-deploy) all
+transfer. The tool names and file paths do not.
```
