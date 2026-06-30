# ADR-029: Lexical tf-idf Skill Retrieval Baseline

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 11 (PLAN-011 Phase 2)
**Blast radius:** L2 (new subsystem, opt-in CLI flag, no existing behavior change)
**Related:** ADR-001 (runtime state directory), ADR-006 (derived registry), ADR-027 (unified agent state backend)

## Context

Sprint 11 shipped a seam for "retrieved skills" — an optional additional
block injected into an agent prompt that ranks SKILL.md files by
similarity to the task description. The goal is not to replace the
static SKILL MAP routing table in `team.md`; it is to **supplement** it
with quantitative relevance when the routing table is ambiguous (many
agents touching many tiers) or when a skill outside the archetype's
primary list would clearly help.

Three candidate designs surfaced during the round-1 debate:

1. **Static SKILL MAP only** — keep today's behavior, do nothing.
2. **Lexical tf-idf baseline** — stdlib math, sqlite storage,
   sublinear-tf + smoothed-idf, opt-in via `--skill-retrieve`.
3. **Real embeddings** (OpenAI `text-embedding-3-small` or local
   sentence-transformers) — better semantic matching, but requires a
   network dep or a new Python package, plus a rate-limit / cost story.

The consensus finding **H4** demanded a mathematically grounded
baseline (not "hashed-bag-of-words theater") AND a held-out recall@5
gate to check whether the baseline actually beats the routing-table
status quo. If the baseline cannot beat the status quo, `H4` requires
hiding the feature behind `CEO_REAL_EMBEDDINGS=1` so maintainers can
see it works first with a real embedding provider in Sprint 12+.

## Decision drivers

- **Stdlib-only** (ADR-002 — hooks layout). Adding `numpy`,
  `scikit-learn`, or `sentence-transformers` to the base install
  contradicts the "Python >= 3.9 + stdlib" charter.
- **Opt-in** — default behavior of `inject-agent-context.sh` must not
  change. Existing spawn flow stays identical without the new flag.
- **Testable on a judgment set** — the consensus explicitly called out
  that a retrieval change needs a recall gate, not a vibes check.
- **Feature-flag seam for real embeddings** — Sprint 12+ should be able
  to swap in a real embedder without changing the CLI or the sqlite
  schema.
- **Reproducible** — indexes built from the same commit should match.
  Uncommitted skill changes break reproducibility; we surface that in
  `--strict` mode.

## Options considered

### Option A — Static SKILL MAP only (status quo)

No new code. `inject-agent-context.sh` continues to read the SKILL MAP
in `team.md`.

**Pros:**
- Zero new surface area.
- Zero new tests.

**Cons:**
- No mechanical way to say "this task wants skill Y even though its
  archetype's primary is X" — the CEO has to improvise every time.
- No signal for skill relevance; no way to detect a stale or
  low-quality skill description.
- Consensus H4 explicitly asked for a quantitative baseline.

**Rejected** — we're already investing in quantitative governance
(lesson ranker, outcome loop, pruning); retrieval needs a number.

### Option B — Lexical tf-idf baseline (accepted)

Stdlib sublinear-tf (`1 + log(tf)`) + smoothed idf
(`log((N+1)/(df+1)) + 1`) + cosine similarity. Index stored in a sqlite
file outside the repo, built by a `skill-index-build.py` CLI, queried
by `skill-retrieve.py`. `inject-agent-context.sh` gains an opt-in
`--skill-retrieve` flag. `CEO_SOTA_DISABLE=1` short-circuits; a reserved
`CEO_REAL_EMBEDDINGS=1` flag is documented for Sprint 12+.

**Pros:**
- **Stdlib-only.** `math`, `json`, `sqlite3`, `re`, `pathlib`,
  `subprocess` — no new deps.
- **Mathematically grounded.** Sublinear-tf prevents long SKILL.md
  files from drowning short ones; smoothed idf avoids divide-by-zero
  on unseen terms.
- **Recall@5 gate on real judgment set.** 39 hand-crafted
  `task -> expected_top_k` pairs committed to
  `.claude/benchmarks/retrieval-judgment-set.yaml`. Real measurements
  on the current 48-skill inventory:
  **lexical = 0.974 (38/39)**, **static SKILL MAP baseline = 0.641
  (25/39)**. Lexical wins by 33.3 points.
- **Opt-in.** Default spawn flow unchanged. Callers must pass
  `--skill-retrieve`.
- **Feature-flag seam.** `get_embedder()` returns the lexical
  embedder today and will return the real embedder when Sprint 12 lands.
- **Plan-global (not plan-scoped).** Skills are repo-level; an
  index per plan is wasted IO. Separate sqlite file (NOT
  `_lib.state_store`) keeps the surface independent — ADR-027 state
  store is plan-scoped by design.

**Cons:**
- Lexical retrieval misses synonyms ("authentication" vs "auth",
  "P&L" vs "profit and loss"). The current corpus is dense with
  domain jargon, so this bites less than it would on free-text docs,
  but it's a known limitation.
- Needs a real rebuild when a SKILL.md changes — we ship
  `--check-stale` advisory mode.

**Accepted.**

### Option C — Real embeddings (deferred)

Vendor SDK call (`openai.embeddings.create` with `text-embedding-3-small`)
OR local `sentence-transformers` model wrapper.

**Pros:**
- Synonym handling.
- Cross-language transfer (ES/PT SKILL.md can match EN queries).

**Cons:**
- New dependency (network + SDK, or large local model).
- Rate-limit + cost story (OpenAI) or install-size hit (local).
- Opaque vectors — hard to debug ranking bugs.
- Contradicts ADR-002 stdlib-only charter.

**Deferred to Sprint 12+** behind `CEO_REAL_EMBEDDINGS=1`. The hook
exists in `_lib.embeddings.get_embedder()` — the follow-up work is
picking a provider and wiring it in.

## Decision

**Option B.** Ship lexical tf-idf as the default retrieval baseline,
opt-in via `--skill-retrieve`, with `CEO_REAL_EMBEDDINGS=1` reserved
for Sprint 12+ real-embeddings drop-in.

## Flip criterion — Sprint 12+ to real embeddings

The consensus finding H4 left the door open to upgrade the default
embedder if real embeddings demonstrably outperform lexical by a
measurable margin:

```
IF real_embeddings_recall_at_5 > lexical_recall_at_5 + 0.05  AND
   maintainer can absorb the dependency cost  AND
   the judgment set has >= 50 pairs (up from 39)
THEN flip `get_embedder()` default from lexical to real
ELSE stay on lexical
```

The +0.05 margin exists so we don't flip on noise. 5 percentage points
out of a 39-pair judgment set is ~2 pairs — a reproducible signal.

The framework's current lexical baseline is 0.974 on the real
judgment set — so "real embeddings" will need to hit >0.99 to justify
flipping. If the judgment set grows and the ceiling is still 0.974,
lexical is good enough and real embeddings stay opt-in.

## CI signing (M5 — deferred to Sprint 12)

The consensus finding **M5** called for "CI-only, checksum-pinned"
index builds — so a dev running `skill-index-build.py` locally cannot
accidentally serve a different ranking than what CI produces. Sprint
11 ships the advisory uncommitted-changes check (`--strict` mode);
Sprint 12+ adds:

- A nightly CI job that rebuilds the index, compares the content_sha
  of each skill row to what CI produced last time, and emits a stale
  advisory when the signed manifest and the live corpus disagree.
- A `--verify-signature <sig-file>` flag on `skill-retrieve.py` that
  refuses to query an index lacking a matching CI-signed manifest.

This split is intentional: Sprint 11 proves the retrieval math works;
Sprint 12 adds the supply-chain controls around it.

## Consequences

- `_lib/embeddings.py` becomes the authoritative place for retrieval
  math. Any future retrieval feature (session-graph similarity,
  pitfall retrieval, lesson retrieval) uses the same primitives.
- A new file convention (`~/.claude/projects/<proj>/skill-index.sqlite`)
  joins the existing audit-log.jsonl and state-store files in the
  per-project runtime directory. ADR-001 still applies.
- The `--skill-retrieve` flag becomes part of the SPEC v1 contract
  for `inject-agent-context.sh`. Removing it is a MAJOR version bump.
- The feature flag `CEO_REAL_EMBEDDINGS` is reserved; Sprint 12+
  consumers MUST NOT break back-compat when turning it on.

## References

- PLAN-011 Phase 2 — this ADR's implementing work.
- `.claude/hooks/_lib/embeddings.py` — math primitives.
- `.claude/scripts/skill-index-build.py` — builder CLI.
- `.claude/scripts/skill-retrieve.py` — query CLI.
- `.claude/benchmarks/retrieval-judgment-set.yaml` — 39-pair gold set.
- `.claude/benchmarks/tests/test_retrieval_recall_gate.py` — H4 gate.
- `SPEC/v1/skill-index.schema.md` — public contract for the index.
- Round-1 consensus H4 — "recall@5 gate ≥30 pairs; if below static
  SKILL MAP, hide behind `CEO_REAL_EMBEDDINGS=1`."
- Round-1 consensus M5 — "index build should be CI-only, checksum-pinned"
  (Sprint 12 follow-up).

## Enforcement commit

`8c30d131ceed` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
