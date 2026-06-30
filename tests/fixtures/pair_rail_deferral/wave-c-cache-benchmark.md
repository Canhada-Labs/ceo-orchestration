# Wave C — Sentinel session cache benchmark + decision

## Disposition: DEFER ship to PLAN-094 (post-PLAN-090 Phase C ENFORCING)

PLAN-091 §4 Wave C re-evaluated PLAN-087 C.5 (sentinel session cache
for `check_canonical_edit.py`) under the hypothesis that PLAN-090
Phase C ENFORCING flip would amplify sentinel-check volume enough to
make the cache's measurable benefit clear the 5% p99-improvement
gate.

**Empirical context at benchmark point**:

PLAN-090 Phase C has NOT shipped yet — its `external_wait` is gated
on PLAN-091 AC15.5 (this plan), which only landed in commit `c9d8d0c`
on this worktree branch. The benchmark snapshot therefore measures
PRE-Phase-C state, which is structurally identical to the PLAN-087
benchmark point at which C.5 was originally deferred.

The PLAN-087 deferred-rationale was:
> "subprocess isolation resets cache every hook call — real-world
> benefit unmeasurable."

That rationale **applies unchanged at PLAN-091 base SHA `8b5d307`**.
PLAN-090 Wave A is the inflection point at which sentinel-check
volume amplifies; benchmarking before that wave ships produces the
same PLAN-087 verdict.

## Benchmark posture

Per PLAN-091 §6 risk-table entry: "C.5 cache invalidation race"
mitigation specifies key composition `(path, inode, mtime_ns,
file_size, sentinel_sha256, cache_key_version)`. That composite key
remains the CORRECT design when the cache eventually ships — the
intra-second-write tamper surface (mtime 1-second granularity collide)
is real and unconditional regardless of when the cache lands. PLAN-094
or PLAN-093 (whichever first reaches Tier-4 cache infrastructure)
will incorporate the composite key.

## Why DEFER not SHIP

Three independent gates point at defer:

1. **Pre-Phase-C state matches PLAN-087 verdict** — subprocess isolation
   resets cache every hook call. Benefit unmeasurable at this snapshot.
2. **Anti-churn (ADR-115)** — landing a cache module + cache-key SHA
   verifier + invalidation discipline in a HOTFIX tag (v1.22.1)
   without a measured uplift exceeds hotfix scope.
3. **Cross-plan affinity** — PLAN-094 owns frontmatter cache (C.3 from
   PLAN-087's broader cache catalog); landing C.5 alongside C.3
   produces a compound-win evaluation rather than two staggered
   deploys. Single ceremony saves Owner-physical GPG events.

## What PLAN-094 inherits

When PLAN-094 (or its functional successor) reaches the cache wave,
this disposition becomes the baseline:

- Cache key: `(path, inode, mtime_ns, file_size, sentinel_sha256,
  cache_key_version: int)` — see PLAN-091 §6 risk-table row.
- Acceptance gate: p99 improvement ≥5% (or absolute ≥2ms AND ratio
  ≥0.90 per PLAN-091 R1 performance-engineer P2 fold).
- Re-benchmark POST-PLAN-090 Phase C ENFORCING — that is the volume
  inflection point.
- Combine evaluation with PLAN-087 C.3 frontmatter cache for compound
  win.

## Mechanical AC posture (post-PLAN-091)

| AC ref | Mandate | Disposition |
|---|---|---|
| §5 AC7 | PLAN-087 C.5 disposition documented (SHIP or DEFER-PLAN-094) | SATISFIED — this file is the explicit DEFER trace |
| §4 C.4 | DECISION threshold ≥5% | DEFER (insufficient inflection volume at benchmark snapshot) |

## Anti-churn defense

PLAN-091 §3 hotfix discipline applies: "NO new features ... NO
behavior changes for adopters who haven't installed PLAN-088
primitives". Landing the cache module would change behavior for
every adopter who runs `check_canonical_edit.py` (i.e., every
adopter post-S111 PLAN-085). That violates the hotfix invariant
without a measured uplift to justify the change.

## How PLAN-090 picks up

PLAN-090 Wave A external_wait `PLAN-091-callsite-wires-shipped` is
already satisfied (AC15.5 PASS at commit `c9d8d0c`). PLAN-090 does
NOT need C.5 to ship; the cache is orthogonal to Phase C flip.
PLAN-090 may surface a follow-on benchmark request to PLAN-094 once
Phase C is live and volume is observed.
