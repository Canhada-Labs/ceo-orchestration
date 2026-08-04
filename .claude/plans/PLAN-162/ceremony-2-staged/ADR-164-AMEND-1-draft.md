# ADR-164-AMEND-1 — The "near-cap GPG cost" residual reopened: cache partition + fail-closed wall deadline

<!-- Ceremony copy target: .claude/adr/ADR-164-AMEND-1-cache-partition-and-wall-deadline.md -->

---
adr_id: ADR-164-AMEND-1
title: Canonical-edit gate — the accepted "near-cap all-granted GPG cost" residual is refuted by measurement (O(candidates × sentinels) amplification, 4.16 s of a 5 s budget at 20 targets); fix = signature/grant cache partition + fail-closed wall-clock deadline
status: ACCEPTED
amends: ADR-164
proposed_at: 2026-08-03
proposed_by: CEO (PLAN-162 round-1 debate, consensus C1/C2/C3 + S3/S8 — finding #1 of the S280 council triage)
session_origin: 2026-08-03 (S291)
accepted_at: 2026-08-03
authorization: PLAN-162/165 consolidated Owner-GPG ceremony 2 commit tagged [SENT-S291] — this file reaches the canonical tree ONLY via that ceremony; a landed copy implies the gate fired
risk_tier: A
debate_required: true
debate_record: .claude/plans/PLAN-162/debate/round-1/consensus.md (3 lanes, 3× ADJUST → PROCEED; C1 [3/3] re-diagnosis, C2 [2/3] cap-is-regression, C3 [2/3] deadline-not-from-settings, S3 amend-not-new-finding, S8 injectable clock)
related_plans: [PLAN-094, PLAN-160, PLAN-162]
related_adrs: [ADR-010, ADR-164, ADR-165]
---

## §1 What this amendment changes

ADR-164 ("Residual risk (pair-rail, accepted)", `.claude/adr/ADR-164-canonical-multicandidate-and-failclosed.md:119-127`)
accepted the **"near-cap all-granted GPG cost"** residual on three premises,
each stated in that block:

1. exposure is *"bounded by the 512 cap"* and *"requires 512 distinct
   validly-signed+scoped canonical paths in a single event — operationally
   absurd"*;
2. the sentinel verification is *"cached by `(sentinel, target_rel)`"*, i.e.
   the cache was assumed to be doing its job;
3. the mitigation (*"per-`rel` grant memoization within the scan, or a lower
   cap"*) was *"a follow-up, not a blocker"*.

The PLAN-162 round-1 measurement (§2) refutes all three. The residual was a
real defect wearing an acceptance: the failure mode it waved off — hook
approaches the timeout, harness kills it, kill is treated as **allow** — is
reachable at **~47 distinct targets, not 512**, needs **zero valid
signatures**, and the sketched mitigations are respectively insufficient
(per-`rel` memoization) and a **security regression** (lower cap, consensus
C2). This amendment supersedes the `:119-127` residual block and decides the
fix: **partition the sentinel cache into a target-independent signature rail
and a cheap per-target grant rail, plus a fail-CLOSED global wall-clock
deadline — both in the same patch** (`plan162-w2-fixes`, staged in this same
ceremony pack under `.claude/plans/PLAN-162/ceremony-2-staged/`).

Everything else in ADR-164 stands: the most-restrictive multi-candidate
scan, emit-once, offender naming, the fail-closed over-cap block at
`_PLAN160_MAX_CANDIDATES = 512` (`check_canonical_edit.py:701`), and the
finding-C fail-closed resolve are all untouched. The 512 cap REMAINS as a
fail-closed absurdity guard — it just no longer carries the cost-bounding
argument, because it cannot: the budget dies an order of magnitude below it.

## §2 Evidence — measured, inputs on the record

Measured independently by two debate lanes on the same machine (repo HEAD at
2165-2166 lines of `check_canonical_edit.py`, healthy `gpg-agent`, 16 live
sentinels as enumerated by `_find_sentinels` at measurement time; full
protocol in `.claude/plans/PLAN-162/debate/round-1/consensus.md` C1):

| Scenario | Measured | Hook budget |
|---|---|---|
| 1 GPG `verify_detached` subprocess | ≈ 17-18 ms | — |
| 1 target, 16 sentinels | 0.22-0.29 s | 5 s |
| 20 targets (a real ceremony-pack event) | **4.16 s** (0 cache hits / 320 misses) | 5 s |
| 40 targets | 4.23 s | 5 s |
| extrapolated to the 512 cap | ~54 s | 5 s |

The 5 s budget is the harness registration for this hook — verified in
kernel `.claude/settings.json` (`check_canonical_edit.py` PreToolUse entry,
`"timeout": 5`). A hook killed at that boundary emits nothing and the event
proceeds: **fail-open on the kernel's own gate**.

**Mechanism, not load.** The cost is amplification, not latency:
`_SENTINEL_VERIFY_CACHE` is a single dict whose key includes `target_rel`
(`check_canonical_edit.py:895-897`; key built at `:907-929`, `target_rel` is
element 6 at `:927`; keyed lookup at `:981`), while the expensive operation —
`verify_detached` — takes **no target at all** (signature validity is a
property of the sentinel bytes). Result: the same sentinel is re-verified by
subprocess once per distinct target. 20 targets × 16 sentinels = 320 GPG
subprocesses where 16 suffice.

**Refutation arithmetic (reproducible from the table).** The 40-target run
prices the marginal verify at 4.23 s / 640 ≈ 6.6 ms; the 5 s budget is
crossed at 5 / (16 × 0.0066) ≈ **47 distinct targets** (consensus S3's
figure) — 10.9× below the cap the residual leaned on. And the premise
"validly-signed+scoped" was doubly wrong:

- the 320 misses are verifications of **already-existing** sentinels; the
  event's candidate paths need no grant, no signature, nothing — any
  multi-path canonical event pays the full matrix before a single grant
  decision is made;
- the sentinel dimension is attacker-growable at zero signatures, because
  the sentinel set itself is unguarded (PLAN-162 finding S2, fixed
  separately in the same plan): 60 planted `approved.md` files were measured
  at 0.48 s/event, and ~628 trivial files put **every** canonical event over
  budget.

The dimension also grows with governance success: every signed ceremony adds
a sentinel (17 live today by the hook's own `_find_sentinels(repo_root)`,
enumerated first-hand for this amendment, vs 16 at measurement) — so the
cost of the honest path ratchets upward monotonically until partitioned.

## §3 Decision

Implemented by the `plan162-w2-fixes` patch staged in this ceremony
(fold **#1+#10** of the PLAN-162 triage — the partition forces the new cache
key that finding #10 required anyway). Normative content:

**D1 — Cache partition (the fix, not a tune-up).** Split
`_SENTINEL_VERIFY_CACHE` into two module-scope caches:

- `_SIG_VERIFY_CACHE[(path, ino, mtime_ns, size, sha256_full, fmt_ver)] → bool`
  — the signature rail. Target-independent, matching what `verify_detached`
  actually computes. One GPG subprocess per distinct sentinel per process.
- `_GRANT_CACHE[(…same…, target_rel, fmt_ver)] → bool` — the scope rail.
  Text parse only, no subprocess.

Collapses the measured 20-target event from 320 GPG subprocesses to 16 —
one per distinct sentinel instead of one per (sentinel × target). The point
is BUDGET COMPLIANCE, not throughput (this repo makes no speed claims): the
measured event consumed 4.16 s of the 5 s registered budget, i.e. the gate
was one canonical-heavy event away from being killed mid-decision; with the
partition the same event fits the budget with room for the fail-closed
deadline to act (D2). Both caches stay module-scope only, never file-backed
(PLAN-094 Wave C contract), and honor
`CEO_SENTINEL_SESSION_CACHE_DISABLED=1`.

**D2 — Fail-CLOSED global wall-clock deadline, per invocation.** A module
constant (`_HOOK_WALL_BUDGET_S`, set in the patch with explicit headroom
under the registered 5 s), checked at the top of the sentinel-grant loops
(`check_canonical_edit.py:1249`, `:1290` at current HEAD). On expiry the
hook emits `_emit_block(canonical_edit_hook_fault)` — **never** "allow
because we didn't finish deciding", **never** "stop verifying sentinels and
proceed". This inverts the failure mode the residual accepted: cost overrun
becomes a visible, recoverable block (re-run, or ceremony) instead of a
silent harness kill treated as allow.

- **Not read from `settings.json` at runtime** (consensus C3): the budget
  lives in the file this hook guards — reading it back is circular, and a
  hot-path JSON parse worsens the path being fixed. A CI drift test asserts
  `_HOOK_WALL_BUDGET_S <= registered timeout` (the `verify-counts.sh`
  shape).
- **Injectable clock** (consensus S8): module-level `_now = time.monotonic`
  seam, monkeypatchable, decided in the same patch — otherwise the red-first
  test is a real multi-second sleep, flaky under runner load (documented
  class in this repo).
- **Per-verify subprocess timeout bounded by remaining budget:**
  `verify_detached` defaults to `timeout=15.0`
  (`.claude/hooks/_lib/gpg_verify.py:239`) — three times the entire hook
  registration. The patch passes a timeout derived from the remaining wall
  budget so a single hung `gpg` cannot ride past the deadline into the
  harness kill.

**D3 — Same-patch coupling is non-negotiable** (consensus C3): a deadline
without the partition trips at the measured 4.16 s and **denies the very
ceremony pack the Owner just signed** — it would introduce the self-DoS the
design debate (OQ3) feared. Partition and deadline land together or not at
all.

## §4 Consequences and blast radius

- **Blast radius: L3** — same surface as ADR-164: `check_canonical_edit.py`,
  a `_KERNEL_PATHS` entry; single hook file + its tests. Reaches the tree
  only via this Owner-GPG ceremony.
- The 20-target ceremony-pack event stops consuming 83 % of the registered
  budget, so it no longer sits one canonical-heavy event away from being
  killed mid-decision; and because the remaining GPG work scales with the
  number of distinct SENTINELS rather than (sentinels × targets), the
  budget headroom no longer erodes as sentinel history accumulates. This
  is a safety/budget invariant, not a performance claim — this repo makes
  no speed claims.
- The over-budget failure mode flips from fail-OPEN-by-kill (invisible) to
  fail-CLOSED-with-reason (`canonical_edit_hook_fault`, auditable in the
  HMAC chain).
- ADR-164's residual block `:119-127` is **superseded** by this amendment;
  the "Pre-cap materialization" note in the same block is unaffected.
- Single-candidate Edit/Write fast path (the overwhelming common case) is
  untouched — the ADR-164 byte-identity property still holds.
- Regression coverage: PLAN-162 W1 red-first tests under the
  `PLAN162_FIX_<N>` / `xfail(strict=True)` convention inherited from
  `test_canonical_edit_council_findings.py`, including the in-process
  two-call cache test (subprocess-per-event repros XPASS by accident —
  consensus S5) and ≥1 interaction pass with the neighbouring PLAN-162
  fixes (consensus S6).

## §5 Alternatives rejected

- **(a) Lower candidate/sentinel cap** — the residual's own sketch.
  REJECTED as a security regression (consensus C2, 2/3 with none against):
  `_find_sentinels` returns pattern-sorted results, and the newest ceremony
  pack is the highest-numbered — a cap of N drops exactly **the sentinel the
  Owner just signed**. Self-DoS with the signature in hand. A cap also
  bounds nothing that hangs: one stuck `gpg` costs its subprocess timeout
  even at cap = 1.
- **(b) Per-`rel` grant memoization within the scan** — the residual's other
  sketch. REJECTED as insufficient: it only collapses repeats of the *same*
  target rel inside one event; distinct rels (the actual ceremony-pack
  shape, and the attack shape) still pay the full O(candidates × sentinels)
  matrix. The invariant worth encoding is that signature validity is
  independent of the target — that is D1, not a memo.
- **(c) Read the wall budget from `settings.json` at runtime.** REJECTED
  (consensus C3): circular — the budget would live in the file this hook
  guards — and adds hot-path JSON parsing to the path being repaired.
  Module constant + CI drift test instead.
- **(d) Raise the registered timeout instead.** REJECTED: treats
  amplification as latency. The extrapolated cost at cap is ~54 s — no
  sane registration covers it, and every second added lengthens the
  synchronous hold an attacker can inflict on benign sessions. The
  diagnosis (consensus C1, 3/3) is amplification; the fix must remove the
  multiplier, not chase it.
- **(e) Keep the acceptance as-is.** REJECTED by measurement (§2). Landing
  the fix while the ADR still said "accepted, operationally absurd" would
  be governance drift — an ACCEPTED record contradicted by shipped code
  (consensus S3: the deliverable is an amendment, not a new finding).

## §6 Named residuals (accepted, on the record)

- **(i) Deadline granularity is per-candidate, not preemptive.** The wall
  check runs at loop tops; it cannot interrupt a `verify_detached` call
  already in flight. D2's remaining-budget subprocess timeout bounds that
  window; what remains is one subprocess-timeout of overshoot in the worst
  case, which stays under the registration by the constant's headroom.
- **(ii) The sentinel set is still the unguarded trust anchor.** The planted
  sentinel vector (§2) is neutralized here only in its COST dimension; the
  S2 authorization exposure (`CEO_SENTINEL_UNLOCK` window + agent-written
  `approved.md`) is a separate PLAN-162 fix with its own tests, not this
  amendment.
- **(iii) The signature rail deliberately caches validity per process
  lifetime.** Signer-rotation-within-a-process remains the accepted
  PLAN-094 trade-off; the partition narrows the key but does not revisit
  that acceptance.
