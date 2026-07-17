---
id: PLAN-160-canonical-edit-council-findings
parent: PLAN-156-FOLLOWUP
title: check_canonical_edit.py hardening — verify + fix the S276 council findings (A/C/B/D)
status: reviewed
reviewed_at: 2026-07-17
created: 2026-07-17
owner: CEO
# W0 debate DONE 2026-07-17 (3× ADJUST → PROCEED, design-coherent; consensus in
# PLAN-160/debate/round-1/consensus.md). Reviewed — NOT ship-authorized: the
# code still goes through the V2 Codex pair-rail + V3 kernel ceremony at Wave 3.
depends_on: [PLAN-156-FOLLOWUP]
budget_tokens: 120-180k
budget_sessions: 1-2
context_risk: medium
external_wait: none
tags: [security, canonical-guard, council, kernel, gate-bypass]
---

# PLAN-160 — check_canonical_edit.py council-findings hardening

## Context

The S276 Wave-4 council live-fire (run `wf_cd40731f-205`, scope
`.claude/hooks/check_canonical_edit.py`) closed **2-lane DEGRADED but with a
CLEAN verification cascade** (`verify_failed=0`) and surfaced **6 distinct
findings**, 4 of which are genuine candidate defects in the canonical-edit
gate. **The CEO independently re-read the cited code for all four** — every
claim is grounded in real lines (not lane hallucination), but each carries an
exploitability caveat that this plan must resolve BEFORE any fix. This is the
"live-fire catches what fixtures miss" lesson realized: the council found these
on a file the PLAN-156-FOLLOWUP ceremony had just touched.

> **These are ADVISORY findings.** A council verdict authorizes nothing
> (PROTOCOL.md V0-V3 unchanged). This plan's Wave 1 is exactly the independent
> verification the council cannot itself provide. Do not fix a finding whose
> repro Wave 1 cannot produce — a code smell that is not reachable is a
> readability fix, not a security fix, and is dispositioned as such.

### The four findings (CEO-verified grounded; exploitability = Wave 1's job)

| # | Severity (pre-verify) | Location | Claim | CEO code-read note |
|---|---|---|---|---|
| **A** | **HIGH — gate-bypass** | `main()` L1367-1374 | Multi-candidate event (`mcp__*` or `len(candidate_paths)>1`) `break`s at the FIRST `_is_canonical` candidate and calls `decide()` ONCE (L1377). A multi-file MCP `apply_patch` with a sentinel-GRANTED canonical path ordered before an UNGRANTED canonical path lets the 2nd ride through ungated. | **Confirmed structurally**: loop breaks at first canonical (L1372), decide() runs once (L1377). Convergent — claude+codex found it independently. Reachability hinges on the MCP adapter emitting multi-file `apply_patch_paths`; Wave 1 must build that event. |
| **C** | MED — fail-open on canonical path | `decide()` L1136-1139 | After `_is_canonical` returns True (L1131), the repo-relative resolve for sentinel matching (L1137) is wrapped in `except (ValueError, OSError): return _emit_allow()` — fail-OPEN on a path already confirmed canonical, contradicting the F-01-07 fail-CLOSED contract. `main()`'s fail-closed wrapper (L1378) never sees it (the inner except swallows). | **Confirmed code. CORRECTED by round-1 debate (CF1):** this is NOT D-coupled — the D input makes `_is_canonical` return False → `decide()` allows at L1132 → C's except is NEVER reached on that path. C is a **provably DEAD except** absent a same-process **TOCTOU** (symlink-race between the two identical pure resolves). Instrument = deadness property test + white-box forced-branch test (monkeypatch resolve to raise → assert block), NOT a failing-first repro. Harden to fail-closed anyway (zero brick risk — it never fires). |
| **B** | LOW — revocation staleness (bounded) | `_compute_sentinel_cache_key` L827-840 | Cache key hashes only sentinel bytes+stat+target_rel — omits `.asc`/signer-allowlist/registry, so a mid-session signer revocation isn't honored until process death; the "`.asc`-covered" comment (L802-803) is false. | **Confirmed code + false comment**. BUT the cache is module-scope and each hook runs as a FRESH subprocess (`hook-profiler.py:178` proves per-invocation processes) — so "process death" ≈ one hook invocation (ms). Blast radius is likely negligible; Wave 1 decides hardening-vs-comment-fix-only. |
| **D** | MED — path-resolution bypass (SHARED predicate) | `_is_canonical` L689-694 | `Path(path_str).resolve()` is CWD-anchored but compared via `relative_to(repo_root)` where `repo_root = CLAUDE_PROJECT_DIR or cwd`; a RELATIVE canonical path when `CWD != CLAUDE_PROJECT_DIR` makes `relative_to` raise → `return False` → treated non-canonical → allowed. | **Confirmed code + round-1 debate UNSEEN (SK1):** `_is_canonical` is a SHARED predicate with 3 consumers, incl. the F5 `--is-canonical` oracle (`_cli_is_canonical` L1231, landed last ceremony) that the grok/codex pre-push gates depend on and whose anchoring invariant (L1258-60) Fix-D silently rewrites → new false comment. **D needs its OWN ADR** + Wave-3 preflight must exercise the CLI oracle path. Anchor BOTH repo_root AND cwd most-restrictively (SK6); absolute-path regression twin; subprocess `cwd=` repro (not os.chdir — xdist flake). |

Findings **E** (envelope `parse_error → allow`) and **F** (`apply_patch` blobs
unparsed) from the same run are **NOT in scope**: E is a documented infra-class
fail-open (CLAUDE.md §4 — correct by design, the verifier itself flagged the
"should fail closed" framing as contestable); F is a documented Layer-A/Layer-B
boundary, a dependency note not a defect. Record both as "reviewed, no action"
in Wave 0 so they are not re-litigated.

## Round-1 debate adjustments (applied 2026-07-17 — verdict PROCEED, 3× ADJUST)

Full record: `.claude/plans/PLAN-160/debate/round-1/consensus.md` (+ the 3
critiques). All three critics endorsed the spine (verify-first, kernel edit
last, most-restrictive-wins, E/F out); these are the mechanical refinements the
Wave descriptions below are SUPERSEDED by where they conflict:

1. **Finding C re-diagnosed (CF1, was a methodological flaw):** C is NOT
   D-coupled — it is a **dead `except`** absent a same-process TOCTOU. Instrument
   = deadness **property test** + white-box **forced-branch test**, NOT a
   failing-first repro. Harden fail-closed anyway (never fires → zero brick risk).
2. **Fix-A shape (CF2/CF3/CF4/SK5):** factor a **pure grant predicate**, emit
   allow/block/persona-coverage **ONCE** (never call side-effecting `decide()`
   per candidate — it fires `_emit_persona_coverage_synthesized` L1146); the loop
   `except: continue` (L1373-74) must be **fail-CLOSED per candidate** (5th
   micro-defect, VETO trigger V-A); block reason names the **offending**
   candidate, not `candidate_paths[0]` (L1358); **hoist `_find_sentinels`** out of
   the loop + **cap candidate count** (O(N·M) → perf-gate/timeout → infra
   fail-open).
3. **Wave-1 acceptance is per-finding-instrument (CF5/CF1):** A/D = failing-first
   repro (FAILS on HEAD); **B = characterization test that PASSES on HEAD** (fix =
   correct the false "`.asc`-covered" comment; key-hardening optional); C =
   deadness property (passes) + forced-branch. The uniform "every repro FAILS on
   HEAD" gate was green-vacuous for B and absent for C.
4. **A-repro harness pinned (SK2/SK3):** MUST drive `main()` end-to-end via the
   subprocess `_invoke` pattern (`test_check_canonical_edit.py:30-56` +
   `CEO_SENTINEL_UNLOCK`). MUST NOT use `_LayerABase._decide`
   (`test_check_canonical_edit_mcp.py:67-86`) — it **re-implements the buggy loop
   incl. the `break` at :81** (false-green). Add controls: single `{granted}`→
   allow, single `{ungranted}`→block, and BOTH orderings of `{granted,ungranted}`.
5. **Anti-over-block test (SK4):** `{grantedByS1, grantedByS2}` (each path its own
   sentinel) → **allow** — most-restrictive-wins must not become "one sentinel
   covers all" (bricking regression). Plus fix-A×B cross-candidate cache-leak
   regression (distinct `target_rel` → distinct key L838).
6. **D own ADR + shared-predicate care (SK1/SK6):** D changes `_is_canonical`
   (3 consumers incl. the F5 `--is-canonical` oracle) → own ADR; Wave-3 preflight
   exercises the **CLI oracle**, not just the hook; anchor BOTH repo_root and cwd;
   absolute-path regression twin (`Path(repo_root) / "/abs"` discards repo_root —
   assert, don't assume).
7. **W2/W3 not separable (SK7):** the file is `_KERNEL_PATHS` → W2 = fix authored
   in the STAGED tree + repros green in staged mode; W3 = the ceremony that lands
   it. W2 cannot "green a fix" on a file it cannot write.
8. **Scope notes:** F recorded as A's explicit residual (A is most-restrictive
   only over the *reported* candidate set; `_extract_mcp_target_paths` has no
   extracted⊇write oracle — DEFERRED, own effort). SK8: SKILL.md unicode guard
   (L1421-22) keys on single `file_path` → multi-file evasion — Wave-0 scope call.

**Security VETO** not exercised; its 3 triggers (V-A per-candidate fail-open,
V-C dead-except-left-allow, V-F-coupling residual-unrecorded) are folded into the
above — Wave 2 lands green against them or the VETO attaches.

## Goal

Each of A/C/B/D is either (a) fixed with a regression test that FAILS before /
PASSES after, or (b) formally dispositioned as not-reachable / accepted-boundary
with the repro attempt recorded. No finding is silently dropped; no fix lands
without a failing-first repro proving the defect was real.

## Waves

### Wave 0 — debate + disposition (ceremony gate)
Check: none (design gate)
- [ ] **Debate L3** (`/debate start PLAN-160`) — kernel touch set
  (`check_canonical_edit.py`), security-VETO archetype present. The debate's
  job: agree the fix SHAPE for A (iterate `decide()` over ALL canonical
  candidates, most-restrictive-wins — vs. a cheaper guard), and set the
  bar for "reachable" that Wave 1 must clear per finding.
- [ ] Record E + F as **reviewed / no-action** with the one-line rationale
  above (infra fail-open; documented Layer boundary).
- [x] **Debate DONE 2026-07-17** (3× ADJUST → PROCEED; consensus applied). Plan
  → `reviewed` per Owner directive to make PLAN-160 execution-ready. E/F
  recorded no-action.

### Wave 1 — VERIFY (per-finding INSTRUMENT — not a uniform failing-first repro; debate CF1/CF5)
Check: `python3 -m pytest .claude/hooks/tests/test_canonical_edit_council_findings.py -q` — A/D repros FAIL on HEAD; B characterization + C deadness-property PASS on HEAD; C forced-branch PASSES (asserts the not-yet-added defense). Each finding's acceptance names its instrument type (a uniform "all FAIL on HEAD" gate is green-vacuous for B and absent for C).
- [ ] **A → failing-first repro (FAILS on HEAD).** Drive `main()` end-to-end via
  the subprocess `_invoke` harness (`test_check_canonical_edit.py:30-56` +
  `CEO_SENTINEL_UNLOCK`); NEVER `_LayerABase._decide` (re-implements the bug incl.
  `break` at `test_check_canonical_edit_mcp.py:81` → false-green, SK2). Assert the
  multi-candidate `{granted, ungranted}` event ALLOWS the ungranted edit, WITH
  controls: single `{granted}`→allow, single `{ungranted}`→block, and BOTH
  orderings (SK3). If it cannot be built, A is downgraded and the plan says so.
- [ ] **D → failing-first repro (FAILS on HEAD).** Relative canonical `path_str`
  with `CWD != CLAUDE_PROJECT_DIR` via subprocess `cwd=` (NOT `os.chdir` — xdist
  flake); assert current code treats it non-canonical → allows. Paired
  absolute-path twin proves the fix leaves absolute-path classification
  byte-identical. NOTE: D and C are MUTUALLY EXCLUSIVE on this input (it makes
  `_is_canonical` return False, so C's except is never reached) — do NOT use it
  to verify C.
- [ ] **C → deadness property test (PASSES) + white-box forced-branch (PASSES).**
  Property: over many relative/absolute/symlink/over-long paths, assert
  `_is_canonical(p)==True ⇒ decide()`'s L1137 resolve also succeeds (the two are
  the same pure resolve → the `except` is dead absent a same-process TOCTOU).
  Then monkeypatch the resolve to raise and assert the (to-be-added) fail-closed
  branch returns `block`/`canonical_edit_hook_fault` — labeled "branch-coverage
  of defense-in-depth, NOT a repro". This replaces the vacuous D-coupled check.
- [ ] **B → characterization test that PASSES on HEAD.** Behavioral (not
  stat-introspective): invocation A caches a grant → mutate the sentinel scope on
  disk → invocation B (fresh subprocess) HONORS the mutation (blocks) — proving
  blast radius = one invocation. Fix = correct the false "`.asc`-covered" comment
  (L802-803); key-hardening only if a same-process re-entrancy window is found.

### Wave 2 — FIX (only the Wave-1-confirmed defects)
Check: the Wave-1 repros now PASS; full `.claude/hooks/tests/` green; no
existing canonical-guard test regresses
- [ ] **A** (if confirmed): evaluate a **pure grant predicate** over EVERY
  canonical candidate, most-restrictive-wins (ANY ungranted canonical path
  blocks the event) — do NOT call side-effecting `decide()` per candidate (it
  fires `_emit_persona_coverage_synthesized` L1146); emit allow/block/coverage
  **ONCE** (CF2). Per-candidate classification exception → **fail-CLOSED** (not
  the current `except: continue`, CF3). Block reason names the **offending**
  candidate, not `candidate_paths[0]` (CF4). **Hoist `_find_sentinels`** out of
  the loop + cap candidate count (SK5). Preserve the single-candidate fast path
  (byte-identical — prove via `test_byte_identity_fuzzer.py`). Anti-over-block:
  `{grantedByS1, grantedByS2}` → allow (SK4).
- [ ] **C** (if reachable): the `except` on a confirmed-canonical path must
  fail-CLOSED (block with `canonical_edit_hook_fault`), matching F-01-07 — NOT
  `_emit_allow()`. If Wave 1 proved it unreachable, either make it fail-closed
  anyway (defense-in-depth, cheap) or annotate as provably-dead with the proof.
- [ ] **D** (if reachable): resolve `path_str` against `repo_root` (not CWD)
  before `relative_to`, or normalize both to absolute under the same anchor.
- [ ] **B**: at minimum fix the false comment; add allowlist/`.asc` to the key
  only if Wave 1 found a same-process re-entrancy window.

### Wave 3 — ceremony land (KERNEL)
Check: `land-*.sh --dry-run` green (full named test set in STAGED mode);
touched ⊆ sentinel scope
- [ ] `check_canonical_edit.py` is a `_KERNEL_PATHS` entry → stage + GPG
  sentinel ceremony with `CEO_KERNEL_OVERRIDE`; the `land-followup.sh` pattern.
  A behavioral oracle in preflight must FAIL unless the staged bytes actually
  carry the A-fix (never sign a claim the bytes don't hold).
- [ ] ADR for any decision that changes the gate's fail-open/closed contract
  (C) or the multi-candidate policy (A).

### Wave 4 — closeout
Check: CI green on closeout commit; plan → done
- [ ] Optional: re-run `/council` on the fixed file (a clean re-audit) — but
  only once the council grok-lane arg-contract is fixed (sibling follow-up), so
  it can actually reach 3-lane.

## Open questions

- **OQ1** — Fix A shape: iterate-decide()-over-all-candidates (correct, O(n)
  sentinel lookups) vs. a cheaper "any ungranted canonical → block" short
  circuit. CEO default: iterate, most-restrictive-wins (correctness over
  micro-perf; the event count is tiny).
- **OQ2** — If Wave 1 proves C and/or D unreachable in the real harness, do we
  still harden them (defense-in-depth) or annotate-and-leave? CEO default:
  harden C (fail-closed is cheap and contract-correct); annotate D if truly
  unreachable.

## Sibling follow-ups (NOT this plan — noted so they are not lost)

- **Council grok-lane arg-contract** (own plan): grok 0.2.93 `-p/--single`
  takes the prompt as a CLI arg and does NOT read stdin, so the ADR-114
  one-pipe egress (`redactor | grok-stdin`) is uncomposable → grok lane
  structurally unsendable, blocking a clean 3-lane. Fix must reconcile grok's
  arg-based input with the redactor WITHOUT a forbidden unredacted-arg path
  (e.g. redactor writes to a fifo/heredoc the grok arg references, still
  single-chokepoint). Canonical (`council-audit.js` + `_grok_harness.sh`) →
  ceremony.
- **perf-gate D3 inter-attempt backoff** (PLAN-159 follow-up): two doc-only
  commits (`d0edd88`, `3cf2d2d`) defeated the 2-attempt retry under sustained
  runner load. Add a short inter-attempt backoff (drain the load window)
  and/or a bounded 3rd attempt. `validate.yml` is canonical → ceremony.

## Success criteria

- [ ] A/C/B/D each: fixed-with-failing-first-repro OR dispositioned
  not-reachable/accepted with the repro attempt recorded. None silent.
- [ ] `.claude/hooks/tests/` green; no canonical-guard regression.
- [ ] Any fail-open/closed contract change (C) or policy change (A) carries an
  ADR.
- [ ] Validate green on closeout.

## How to continue

**START HERE next terminal — status is `reviewed`, Wave 0 debate is DONE**
(3× ADJUST → PROCEED, 2026-07-17; consensus + the 8 applied adjustments are in
`.claude/plans/PLAN-160/debate/round-1/consensus.md` and the "Round-1 debate
adjustments" section above — the adjustments GOVERN where any wave text below
conflicts). **Do NOT re-run the debate.** Begin at **Wave 1**, which is pure
verification (read-only reads + NEW tests) and needs no ceremony — the safe
place to start.

Wave 1 uses a **per-finding instrument** (NOT a uniform "failing-first repro"):
- **A, D** → failing-first repro (FAILS on HEAD, PASSES after fix). A-repro
  MUST drive `main()` end-to-end via the subprocess `_invoke` harness; NEVER
  `_LayerABase._decide` (it re-implements the bug → false-green).
- **B** → **characterization test that PASSES on HEAD** (proves the ephemeral
  bound); the fix is correcting the false "`.asc`-covered" comment.
- **C** → **deadness property test (passes) + white-box forced-branch test**;
  C is a dead `except` absent a TOCTOU, NOT a D-coupled repro.

Only **Wave 2/3** edit `check_canonical_edit.py` — and they are NOT separable:
the file is `_KERNEL_PATHS`, so the fix is authored in the STAGED tree +
repros validated in staged mode (W2), then landed by the GPG sentinel ceremony
with a per-finding ADR incl. one for **D** (shared-predicate → the F5
`--is-canonical` oracle) (W3). The risky part (touching a live security gate)
happens LAST and only for defects Wave 1 actually confirmed.
