# ADR-048: Cross-plan shared memory (pattern library)

**Status:** ACCEPTED (flipped from PROPOSED on PLAN-014 Phase G commit fdc2d89)
**Date:** 2026-04-16
**Supersedes:** none
**Superseded by:** none
**Related:** ADR-010 (canonical-edit sentinel), ADR-007 (SemVer + additive-only), ADR-027 (state store — scratchpad), ADR-002 (stdlib-only)

## Context

PLAN-014 Phase F.5 ships `_lib/memory_shared.py` with `put_pattern(topic, content)` / `query(topic, k=5)` primitives. The scenario: plan N discovers a useful pattern ("when debating live-adapter ADRs, always include a 6-revisit-conditions block"); plan N+1 should be able to find that pattern without re-deriving.

Existing scratchpad (ADR-027) is PLAN-SCOPED. What's missing: a KNOWLEDGE LAYER TRANSVERSAL TO PLANS.

Debate Round 1 (2026-04-17 Session 23) surfaced four constraints:
1. **C3 CRITICAL — Canonical-edit guard required if repo-committed.** If storage is `.claude/memory-shared/`, attacker-authored commit could slip past reviewer since edits look like docs. Must be in `_CANONICAL_GUARDS`.
2. **C28 — Storage path choice IRREVERSIBLE once files commit.** Q4 default (local-only) reduces L3 blast to L2; repo-committed requires explicit L3 declaration.
3. **C32 — Adversarial floods.** Attacker fills topic space, dominates rankings.
4. **Redact-on-ingest mandatory.** `put_pattern()` MUST pass content through `redact_secrets()` before disk write.

Co-landing with PLAN-014 Phase F.5 (per Phase 0.3 ADR→Phase dependency; §Decision MUST lock BEFORE F.5 storage path commits).

## Decision drivers

- **Q4 storage choice** — local-only default (L2 blast) vs repo-committed (L3 + canonical-edit guard mandatory)
- **Tampering vector** (RR-7 appended to threat model)
- **Adversarial floods** (C32) → per-topic cap + normalized-token ranking (not raw recency)
- **Canonical-edit coverage** (C3) → `_CANONICAL_GUARDS` extension + 8 regression tests if repo-committed
- **Redact-on-ingest** — all put_pattern content passes through redact_secrets
- **Stdlib-only** (ADR-002 invariant)

## Options considered

### Option A — Local-only per-user (`~/.claude/projects/<slug>/memory-shared/`)

**Shape:** Storage lives in the user's home directory under the project slug. Not committed to git. Each operator has their own memory-shared namespace.

**Pros:**
- L2 blast radius (per-user; bug affects one operator at most)
- No canonical-edit guard required (not in repo)
- No commit-review bottleneck (operator writes freely)
- Zero risk of secret-in-commit

**Cons:**
- Not shared across team (each operator re-derives)
- Not shared across machines (dev laptop vs CI runner = two silos)
- Lost on OS reinstall (operator-managed backup)

**Risk:** LOW — no cross-operator attack surface; worst case one operator's patterns drift.
**Evidence:** Pattern precedent: `audit-log.jsonl` lives under `~/.claude/projects/<slug>/` for the same Tier 2 isolation.

### Option B — Repo-committed curated (`.claude/memory-shared/`)

**Shape:** Storage lives in repo. Every put_pattern creates a file that commits via PR. Canonical-edit guard blocks direct edits; only approved PRs merge.

**Pros:**
- Team-shared (one source of truth)
- CI-validated (patterns pass tests before merge)
- Cross-machine consistency (git pull syncs)
- Long-term persistence

**Cons:**
- L3 blast radius (repo-wide — bug affects entire team)
- Canonical-edit guard MANDATORY (C3); adds maintenance
- Commit-review bottleneck (every put = PR)
- Attacker path: craft adversarial "pattern" in PR, hope for merge
- Secret-in-commit risk (despite redact-on-ingest, false negative = public leak)

**Risk:** HIGH — L3 blast + commit-review dependency; secret leak is one missed redact_secrets pattern away.
**Evidence:** `.claude/team.md`, `.claude/skills/` live in repo with canonical-edit guard; same pattern applies but with significantly higher review burden for small pattern files.

### Option C — Hybrid (local-only default; repo-committed opt-in per adopter)

**Shape:** Default is Option A. Adopter can opt into Option B by setting `CEO_MEMORY_SHARED_PATH=.claude/memory-shared/` + enabling canonical-edit guard. Same module, two storage roots.

**Pros:**
- Safe default (L2)
- Flexibility for adopters who want team-shared
- No forced canonical-edit guard for solo operators

**Cons:**
- Two code paths (though module-internal, not API-visible)
- Adopters who opt-in must also configure canonical-edit guard (two-step; easy to forget)
- SPEC must document BOTH modes

**Risk:** MEDIUM — complexity tax; adopter misconfig = L3 breach.
**Evidence:** Q4 default resolution (Session 23) chose local-only; debate explicitly warned against "hybrid where the safe path and unsafe path share code surface".

## Trade-off matrix

| Dimension | A: Local-only | B: Repo-committed | C: Hybrid |
|---|---|---|---|
| Blast radius | L2 (low) | L3 (high) | L2 default / L3 opt-in |
| Team sharing | None | Full | Opt-in |
| Commit-review burden | None | Per-pattern | Opt-in |
| Secret-leak risk | Low | Medium | Medium |
| Canonical-edit guard | Optional | Required | Required-if-opted |
| Adopter onboarding | Trivial | Requires CI setup | Requires mode-decision |
| Long-term persistence | Operator | Git (strong) | Mixed |
| Weighted sum | 84 | 62 | 71 |

Winner: **Option A (Local-only)** — 84 vs 71, margin +18% (exceeds ADR-044 10% floor).

## Decision

**Option A — Local-only per-user. Storage at `~/.claude/projects/<project-slug>/memory-shared/`. Q4 = local-only. L2 blast. Canonical-edit guard NOT required in v1 (flipped to required only if Q4 reverses in v2).**

### Why not B or C

- **B rejected:** L3 blast + commit-review bottleneck + secret-leak-via-missed-redact scenarios outweigh team-sharing benefit for v1 pre-adopter phase.
- **C rejected:** hybrid creates misconfig cliff — adopter flips `CEO_MEMORY_SHARED_PATH` without enabling canonical-edit guard = unguarded L3 breach. Better to force new SPEC+ADR for repo-committed later.

### 6 revisit conditions

Re-evaluate if ANY of:

1. **Adopter strongly requests team-sharing** (adopter-1 post-Sprint-15) → evaluate Option C with hardened config-validation (fail-fast if `CEO_MEMORY_SHARED_PATH=repo-committed` without canonical-edit guard).
2. **Secret leak incident via memory-shared** → regardless of cause, escalate to ADR-048 SUPERSEDED + redesign (stricter redact, or storage encryption).
3. **Adversarial flood saturates topic space** (C32) → tighten per-topic cap + evaluate automatic eviction by hash-frequency (LFU).
4. **Normalized-token overlap ranking measurably worse** than BM25 / TF-IDF in adopter feedback → evaluate BM25 overlay (stdlib implementation, no deps).
5. **Size-cap breach rate >5%** of put_pattern calls → evaluate auto-eviction policy.
6. **Cross-machine consistency becomes a bottleneck** (operator's dev vs CI can't share patterns) → promote to Option C with explicit opt-in.

## Consequences

### Positive

1. **Knowledge-transfer primitive unlocked.** Plans can now share patterns (not PLAN-scoped like scratchpad). Before: re-derive per plan. After: query("audit-registry-extension") returns prior patterns.
2. **L2 blast.** Per-user storage; one operator's pattern library doesn't impact the team.
3. **No canonical-edit guard overhead.** v1 ships without the extra guard + 8 regression tests that C option would require.
4. **Redact-on-ingest** prevents secret-in-disk. `_redact.redact_secrets()` on every put_pattern.
5. **No commit-review bottleneck.** Operator writes freely; no PR per-pattern.
6. **Relevance-biased ranking.** Normalized-token overlap (§Ranking) prevents flood-by-recency attack.

### Negative

1. **No team sharing in v1.** Each operator has their own silo. Workaround: operators can manually `scp` or git-export their `memory-shared/` for team onboarding.
2. **Lost on OS reinstall.** Operator is responsible for backup. Mitigation: document in `docs/GUIA-COMPLETO.md` that `~/.claude/projects/` is precious.
3. **No auto-eviction.** Unbounded retention — operator manually evicts. At 256 KiB cap, worst case = operator hits `storage_full` ValueError + must evict.
4. **Ranking algorithm is simplistic.** Token overlap misses semantic similarity. Option A.1 (v1.1.0) could add BM25 overlay if adopter signal demands.

### Neutral

1. **Storage is Tier 2.** Directory 0o700, files 0o600. Same sensitivity tier as audit log.
2. **Audit trail free.** `pattern_stored` / `pattern_queried` / `pattern_evicted` events emitted.
3. **Topic canonicalization** (Unicode NFC + lowercase + dash-separated) is standard + deterministic.

## Blast radius

**L2** (local-only default; this ADR's decision).

If Q4 flipped to repo-committed in a future ADR, the blast becomes **L3** and MUST be declared explicitly per ADJ-007, with canonical-edit guard MANDATORY per C3.

**Reversibility:** HIGH. To disable entirely: delete `_lib/memory_shared.py` + remove from SPEC index + ADR-048 SUPERSEDED. Existing `~/.claude/projects/<slug>/memory-shared/` files remain as operator-owned artifacts; no cross-repo cleanup needed.

## Ranking algorithm (normative)

`query(topic, k)` returns top-k patterns by **normalized-token overlap**:

```python
def score(q_canonical: str, t_canonical: str) -> float:
    q_tokens = set(q_canonical.split("-"))
    t_tokens = set(t_canonical.split("-"))
    if not q_tokens or not t_tokens:
        return 0.0
    intersection = q_tokens & t_tokens
    return len(intersection) / max(len(q_tokens), len(t_tokens))
```

Rationale:
- **Deterministic** — same inputs = same outputs, cacheable
- **Flood-resistant** — attacker puts N patterns under "attacker-topic"; queries for unrelated topics don't see them (zero token overlap)
- **Stdlib-only** — no numpy, no scikit-learn

Future overlay (v1.1.0+): BM25 weighting on term frequency within pattern content. Out of v1 scope.

## Security considerations

### Tier 2 classification

Storage files are Tier 2 (same as audit log). Mode 0o600 (files) / 0o700 (dirs).

### Redact-on-ingest (mandatory)

Every `put_pattern(topic, content)` call passes `content` through `_lib.redact.redact_secrets()` BEFORE write. Recognized secret patterns (JWT, `sk-*`, GitHub PAT, AWS key, bearer, hex ≥32, URL-with-creds, `password=` assignments) are masked. The pre-redact form is NEVER persisted.

### Adversarial test fixture

Per QA R-QA9, adversarial test fixture at `.claude/hooks/tests/test_memory_shared.py::TestAdversarial`:
- Flood attack (100 patterns under one topic) — verify rankings not dominated for UNRELATED queries
- Topic confusion (Unicode homoglyph attack: "apple" vs "аpple" with Cyrillic a) — verify NFC + lowercase defeats
- Content-embedded secret — verify redact_secrets fires
- Oversize content (5 KiB) — verify rejection with `content_too_large`
- Oversize storage (257 KiB total) — verify rejection with `storage_full`

### Concurrency safety

Index file (`index.jsonl`) under `_lib.filelock.FileLock` with 2.5s timeout. Multi-process put/evict race-free. Query is lock-free (content files are immutable, content-addressed).

## Transition Log

Per ADR-041 format.

| Date | From | To | Evidence-link | PR-ref |
|------|------|-----|---------------|--------|
| 2026-04-16 | stub | PROPOSED (full draft) | PLAN-014 §Phase F.6 | pending |

## References

- **PLAN-014 §Phase F.5 / §F.5a / §F.5.a / §F.6** — deliverables
- **ADR-010** — Canonical-edit sentinel (pattern for §F.5.a if Q4 flipped)
- **ADR-007** — SemVer + additive-only (SPEC/v1/memory-shared.schema.md v1.0.0-rc.1 governance)
- **ADR-002** — Stdlib-only invariant
- **ADR-027** — State store / scratchpad (plan-scoped; this ADR adds cross-plan layer)
- **SPEC/v1/memory-shared.schema.md** — 11-section normative contract (created Phase F.5a)
- **`_lib/redact.py`** — `redact_secrets()` used on ingest
- **`_lib/filelock.py`** — index file locking
- **PLAN-014/debate/round-1/consensus.md** — C3 (CRITICAL — canonical-edit guard), C28, C32
- **`audit-log.schema.md` v2.6** — 3 registered events

---

**End of ADR-048 PROPOSED full draft.** Flips ACCEPTED on PLAN-014 Phase G merge.

## Enforcement commit

`1551f00110be` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
