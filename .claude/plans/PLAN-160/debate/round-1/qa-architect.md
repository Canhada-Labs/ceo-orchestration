---
plan: PLAN-160
round: 1
archetype: qa-architect
role: Principal QA Architect (test-strategy critic)
verdict: ADJUST
created_at: 2026-07-17
---

# PLAN-160 round-1 critique — Principal QA Architect

Scope of this critique: the **verification spine** — "failing-first repro per
finding before any fix" — for A/C/B/D in `check_canonical_edit.py`. I judge each
finding purely on whether an honest, non-vacuous repro is constructible through
the real code path, and whether the Wave-2 "repro now passes" gates can be gamed.

## Verdict

**ADJUST.** The sequencing (verify-first, risky-kernel-edit LAST, fix only what
reproduces) is correct and is exactly the "live-fire catches what fixtures miss"
discipline done right. But the plan's uniform *"failing-first repro per finding"*
spine is only literally achievable for **A and D**. For **C it is impossible via
real input** (the `except` is provably dead absent a same-process TOCTOU), and
for **B it inverts** (the characterization test PASSES on HEAD, not fails). The
plan half-says this in prose but the Wave-1 CHECK line and Success Criteria still
assert "every repro FAILS against HEAD" — which will be **green-vacuous for B and
absent for C**, giving false confidence. Plus the A-repro has a concrete
harness trap (an existing test helper re-implements the very bug) and the fix-A
shape has an un-costed audit side-effect and a per-candidate fail-open the plan
doesn't address. All fixable in Wave-0/Wave-1 specification; none sink the plan.

## Summary

- **A** (`main()` L1367-1374): genuinely reproducible **only** end-to-end
  through `main()` via subprocess, and **only** with a granting sentinel. The
  established `_invoke` harness (`test_check_canonical_edit.py:30-56` +
  `_write_sentinel` :71-83 + the `CEO_SENTINEL_UNLOCK` env override :46-47) is
  the right instrument. The wrong instrument — `_LayerABase._decide`
  (`test_check_canonical_edit_mcp.py:67-86`) — **re-implements the buggy loop,
  including the `break` at :81**, so a repro built on it tests a copy of the bug
  and passes both before and after a `main()` fix. Naming the harness is
  load-bearing.
- **C** (`decide()` L1136-1139): `_is_canonical` (L689-694) and `decide()`
  (L1137) run the **identical** `p.resolve().relative_to(repo_root.resolve())`
  on the identical inputs. `_is_canonical` returns True only if that resolve
  *succeeded*; the same resolve at L1137 then cannot raise. The `except` is
  **provably dead** on a single-threaded static-filesystem invocation. It is not
  input-reachable — only a genuine mid-call TOCTOU separates the two calls.
- **D** (`_is_canonical` L689-694): cleanly and deterministically reproducible
  via subprocess `cwd=` divergence + a relative canonical path. Fully honest
  repro.
- **B** (`_compute_sentinel_cache_key` L818-840): "ephemeral→negligible" IS
  testable at the subprocess boundary, but the test *passes* on HEAD — it's a
  characterization/bound test, not a failing-first repro.

## Risks

- **R1 — C+D shared repro is mis-specified (false-confidence risk).** Wave-1
  says "C+D together: … a relative canonical `path_str` with `CWD !=
  CLAUDE_PROJECT_DIR` … observe whether `_is_canonical` and `decide()`
  disagree." That single input makes `_is_canonical` return **False** (D's
  mechanism), so `decide()` returns allow at L1132 and **never reaches the C
  `except` at L1138 at all**. D and C are **mutually exclusive on that input**.
  Wave-1 will "find no divergence," record "C is a dead except," and be *right by
  accident for the wrong reason* — a textbook vacuous disposition. The honest
  reason C is dead is "two adjacent identical pure resolves cannot disagree
  without a TOCTOU," not "CWD divergence didn't trigger it."
- **R2 — the A repro's "allow" is ambiguous without controls.** Wave-1 A says
  only "assert current code ALLOWS the ungranted edit." An `allow` could mean
  *the bypass fired* OR *both candidates happened to be granted* OR *the override
  env was misconfigured so nothing was canonical*. Without single-candidate
  control assertions the failing-first repro can pass for the wrong reason.
- **R3 — fix-A re-runs `decide()`'s side effects N times.** `decide()` is not
  pure: on the allow branch it calls `_emit_persona_coverage_synthesized(rel)`
  (L1146), an audit/telemetry emit. The proposed shape ("iterate `decide()` over
  every candidate") fires that emit up to **N times per multi-candidate event** —
  audit-log/metric amplification, and a persona-coverage skew regression. The
  fix should compute a per-candidate grant *predicate* and emit **once**, not
  call the full side-effecting `decide()` per candidate.
- **R4 — fix-A block reason may name the wrong path.** `main()` pins
  `file_path = candidate_paths[0]` (L1358) for "legacy file_path-keyed downstream
  logic" and the post-decide veto emit (L1408+). If the fix blocks on
  candidate\[k>0] but the emitted reason/audit still references candidate_paths\[0],
  the block message names a *granted* path while the *ungranted* one triggered it
  — a misleading forensic record on the security gate's own block path.
- **R5 — Wave-1 pytest gate is green-vacuous for B.** The gate
  (`test_..._council_findings.py` — "every repro that represents a REAL defect
  FAILS against current HEAD") passes trivially for B because B's assertion
  (cache non-persistence) is *already true* on HEAD. A green Wave-1 gate does not
  prove B was investigated.
- **R6 — fix-A perf: per-candidate `_find_sentinels` re-glob.** A naive
  iterate-`decide()` re-runs `_find_sentinels(repo_root)` (dir glob + per-sentinel
  GPG) for every candidate; the session cache (finding B) does **not** amortize
  across candidates because each has a distinct `target_rel` → distinct cache key
  (L838) → miss → full verify. A many-file `apply_patch` becomes N full sentinel
  scans and can trip the perf-gate p95/p99. Hoist sentinel discovery out of the
  per-candidate loop.

## Must-fix (before Wave-1 executes)

1. **Pin the A-repro harness explicitly to `main()` end-to-end.** The repro MUST
   use the subprocess `_invoke` pattern (`test_check_canonical_edit.py:30-56`)
   so the L1367-1374 loop is the code under test. It MUST NOT use, extend, or
   copy `_LayerABase._decide` (`test_check_canonical_edit_mcp.py:67-86`), which
   re-implements the loop **with the same `break` bug at :81** and structurally
   cannot exercise a `main()` fix. Add a Wave-0 note that this helper is latent
   drift debt and Wave-2 should retire/re-point it to `main()` so the suite has
   one source of truth for the loop.
2. **Give the A-repro two disambiguating controls** (kills R2): in the same
   test, assert (a) single-candidate event `{granted}` → **allow** (control:
   sentinel really grants path1), and (b) single-candidate event `{ungranted}` →
   **block** (control: path2 really is ungated canonical). Only then is the
   multi-candidate `{granted, ungranted}` → **allow** result unambiguously *the
   bypass*. Also test **both orderings** — `{granted, ungranted}` and
   `{ungranted, granted}` — since the bug is order-dependent and a complete fix
   must be order-invariant.
3. **Re-specify C's disposition; drop the "failing-first repro" requirement for
   C.** State the real reason it is dead: L689-694 and L1137 are the *same pure
   resolve on the same inputs*; `_is_canonical`→True implies L1137 cannot raise
   absent a mid-call TOCTOU, which a single-threaded hook subprocess does not
   induce. C is therefore **not input-reachable**. Verify deadness with a
   **property/enumeration test** (many relative/absolute/symlink/over-long paths:
   assert `_is_canonical(p)==True ⇒ decide()`'s L1137 resolve also succeeds) — a
   passing property test is the evidence, not a failing repro. Then harden to
   fail-closed (OQ2 default) and add a **white-box** test that *forces* the raise
   (monkeypatch resolve) to assert the new branch returns `block` with
   `canonical_edit_hook_fault` — explicitly labeled "not a repro; branch-coverage
   of the defense-in-depth path."
4. **Split the Wave-1 CHECK and Success Criteria per finding-instrument.**
   "Every repro FAILS against HEAD" applies to **A and D only**. B's instrument
   is a **characterization test that PASSES on HEAD** (proves the ephemeral
   bound); C's instrument is a **deadness property test (passes) + forced-branch
   test**. As written, the uniform gate can go green while B and C carry no real
   evidence (R5). Make each finding's Wave-1 acceptance name its instrument type.
5. **Fix-A shape must be side-effect-once and fail-CLOSED per candidate.**
   (a) Iterate a *pure* grant predicate, emit persona-coverage / allow / block
   **once** for the event, not per candidate (kills R3). (b) On block, the
   emitted reason + audit must name the **actual offending candidate**, not
   `candidate_paths[0]` (kills R4). (c) The loop's current
   `except Exception: continue` (L1373) fails **OPEN per candidate** — a
   candidate that errors during classification is silently dropped from gating.
   The fix must treat a classification exception as **fail-CLOSED (block)**, per
   CLAUDE.md §4 "fail-closed on input in security matchers." This is a genuine
   fifth micro-defect neither the council nor the plan names (see Unseen U1).
6. **D-repro must include an absolute-path regression twin.** The relative-path
   repro (CWD-divergent) proves the bypass; a paired **absolute-path** case must
   prove the fix (`repo_root`-anchored resolve, or `Path("/abs")` under `/`
   join) leaves the high-traffic absolute-path classification **byte-identical**.
   `Path(repo_root) / "/abs"` discards `repo_root` in pathlib — assert that,
   don't assume it.

## Nice-to-have

- **Order the D repro on subprocess `cwd=`, not `os.chdir`.** The precedent
  `test_mcp_canonical_guard.py:1032-1067` uses in-process `os.chdir("/tmp")` with
  a try/finally restore — unsafe under `pytest -n auto` (shared CWD across xdist
  workers = flake). Prefer `subprocess.run(..., cwd=<neutral tmp>)` in the
  `_invoke` harness; it is hermetic and needs no restore.
- **Add the cross-candidate cache-leak regression for fix-A × finding-B.**
  Fix-A turns "one `_sentinel_grants_path` call per process" into "N calls per
  process." Prove no cross-candidate grant leak: candidate1 (granted,
  target_rel=path1) populates `cache[key(sentinel,path1)]=True`; candidate2
  (target_rel=path2) must **miss** (distinct `target_rel` in key at L838) and
  re-verify scope. Pin this so a future "optimization" that drops `target_rel`
  from the key (undoing the iter-1 P0 fix) can't silently re-open a
  most-restrictive-wins bypass.
- **B characterization test should be behavioral, not stat-introspective.**
  `sentinel_cache_stats()` counters are not on the hook wire; prove the bound by
  behavior: invocation A (would cache a grant) → mutate the sentinel scope on
  disk → invocation B (fresh subprocess) **honors the mutation** (blocks). That
  demonstrates "blast radius = one invocation" without reaching into internals.
- **Regression watch-list for Wave-2** (run these explicitly, don't rely on the
  full-suite average): `test_adapter_golden.py` + `test_byte_identity_fuzzer.py`
  (single-candidate byte-identity — the fix-A "outcome-identical fast path"
  claim), `test_mcp_canonical_guard.py` (79 KB, the broad matrix), and
  `test_check_canonical_edit_coverage.py` (in-process fail-open/closed
  hook-fault, per its docstring L8). Note that most of
  `test_check_canonical_edit_mcp.py` is already `@unittest.skip`-ped
  (PLAN-070-followup debt) → it will NOT catch an A-regression; do not count it.

## Unseen

- **U1 — a fifth defect the council missed: the candidate loop fails OPEN per
  candidate.** `main()` L1373 `except Exception: continue` — if `_is_canonical`
  raises for a candidate (today near-dead because `_is_canonical` swallows its
  own OSError/ValueError and returns False, but any *other* exception, or a
  future refactor, escapes), that candidate is silently skipped from gating. This
  is the same fail-open class as A, one layer down, and fix-A's "iterate all
  candidates" must convert it to fail-CLOSED or the "most-restrictive-wins"
  guarantee has a hole. Fold into fix-A (Must-fix 5c).
- **U2 — the repro-suite can encode the bug as the oracle.** Because
  `_LayerABase._decide` mirrors the buggy loop, when Wave-2 fixes `main()` the
  helper's expected-behavior tests (currently skipped) would assert the *old*
  wrong outcome if un-skipped. A repro that "passes" against that helper is false
  green. This is the single highest false-confidence vector in the plan and is
  invisible unless someone reads test_check_canonical_edit_mcp.py:78-84. (Root of
  Must-fix 1.)
- **U3 — Wave-3 preflight oracle is under-specified.** The plan says "a
  behavioral oracle in preflight must FAIL unless the staged bytes actually carry
  the A-fix." Make that oracle the **exact failing-first A-repro** re-run against
  the *staged* tree: it must go red on unstaged HEAD and green on staged — never
  a grep for a code token (a grep passes on a comment that mentions the fix).
  This is where "never sign a claim the bytes don't hold" is actually enforced.
- **U4 — no test asserts single-vs-multi decision equivalence when all canonical
  candidates are independently granted by *different* sentinels.** "Most-
  restrictive-wins" must not become "one sentinel must cover all": `{grantedByS1,
  grantedByS2}` → **allow**. Missing this test risks a fix that over-blocks
  legitimate multi-file apply_patch events where each path has its own sentinel —
  a bricking regression that only shows up in real ceremonies, not in the A repro
  (which uses one sentinel).

## What I would NOT change

- **The verify-first, fix-only-what-reproduces spine.** Correct and non-
  negotiable for a kernel gate; keep it as the plan's identity.
- **Risky kernel edit LAST (Wave-2/3), read-only verification FIRST (Wave-1).**
  Wave-1 is pure new-test + read; it needs no ceremony and is the safe place to
  start. Keep.
- **E and F out of scope, recorded no-action in Wave-0.** Agreed — E is the
  documented infra fail-open (CLAUDE.md §4), F is a Layer-A/B boundary note.
  Re-litigating them would be scope creep.
- **OQ1 default (iterate, most-restrictive-wins) over the cheaper short-circuit**
  — correct on *outcome*; my Must-fix 5 changes the *mechanism* (pure predicate,
  emit-once, per-candidate fail-closed, hoisted sentinel discovery), not the
  policy. The policy is right.
- **OQ2 default (harden C fail-closed even if unreachable).** Correct: since C is
  a dead `except`, fail-closing it has **zero brick risk for real sessions**
  (it never fires) and is contract-correct if a future concurrent-hook model ever
  makes the two resolves diverge. Cheap defense-in-depth; keep.
- **TestEnvContext for env/HOME/CLAUDE_PROJECT_DIR isolation.** The right base;
  the subprocess `_invoke` already inherits its `CLAUDE_PROJECT_DIR`. Keep — I
  only add subprocess `cwd=` for the D-repro determinism (Nice-to-have 1).
