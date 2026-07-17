---
plan: PLAN-160
round: 1
archetype: security-engineer
veto_authority: gate-decision, fail-open/closed
verdict: ADJUST
veto_exercised: false
created_at: 2026-07-17
---

# PLAN-160 round-1 — Security Engineer critique

Scope reviewed: `.claude/hooks/check_canonical_edit.py` — `main()` multi-candidate
loop L1334-1406, `decide()` L1119-1161, `_is_canonical` L683-703,
`_compute_sentinel_cache_key` L818-840 + `_sentinel_grants_path` L852-898,
`_extract_mcp_target_paths` L359-385, SKILL.md unicode guard L1417-1434.

## Verdict

**ADJUST.** I do **NOT** exercise VETO on the plan as written — verification-first
is sound and the fix directions are security-positive. But this is a kernel
security gate and I hold VETO on gate-decision and fail-open/closed changes, so I
am recording the **exact conditions under which VETO attaches at Wave 2**:

- **V-A.** Fix A lands with the per-candidate `except Exception: continue`
  (L1373-1374) still fail-OPEN — a classification exception on a canonical
  candidate must fail-CLOSED, not skip the candidate.
- **V-C.** Finding C's `except` on a confirmed-canonical path is left
  `_emit_allow()` (fail-open), OR is dispositioned "unreachable" on the strength
  of the D-scenario repro (which cannot reach C — see Risk R2).
- **V-F-coupling.** Wave 2 lands an ADR/claim that the "multi-candidate bypass is
  closed" without recording that A's fix is only most-restrictive over the
  *reported* candidate set, and that under-reported paths (finding F,
  out-of-scope) remain an accepted residual.

Clear those three and the ADJUST is satisfied; none is a design-blocker.

## Summary

A/C/B/D are real code facts (I re-confirmed all four against HEAD). The plan's
**shapes** are right; its **sequencing** has one methodological flaw (C and D are
bundled but have different root causes — R2), and its two HIGH/MED fixes each
introduce a fail-open sub-hazard the proposal does not name (the loop's
`except: continue`, and the candidate-set completeness bound). Severity calls are
defensible: A is a **real** bypass in the codex/MCP multi-file harness (the
`apply_patch_paths` surface at L1342-1350 is demonstrably reachable and the
attacker controls patch-op ordering), not theoretical. C is a narrow **TOCTOU**
fail-open, not the D-coupled thing the plan describes. B is genuinely LOW and the
comment-fix is the honest disposition. D's fix (repo_root anchor) is directionally
right but under-specified — a single wrong anchor choice opens a *different* miss.

## Risks

- **R1 — Fix A's `except: continue` is a fail-open the proposal inherits silently.**
  The selection loop L1368-1374 skips any candidate whose `_is_canonical` raises.
  Today that is "merely" a selection heuristic backstopped by decide()'s outer
  fail-closed wrapper (L1378). The moment the canonical determination becomes the
  *decision authority* (most-restrictive-wins), a candidate that raises during
  classification and is `continue`d is a canonical path waved through. An attacker
  crafts one pathological path in an otherwise-granted multi-file event; it is
  skipped; the event allows. This is a **new** fail-open created by the fix if
  ported naively. Fail-CLOSED on per-candidate classification exceptions.

- **R2 — C and D are bundled but cannot share a repro; risk of a false "C dead"
  disposition.** The Wave-1 plan (§Wave 1, "C+D together") induces C via a
  relative path + `CWD != CLAUDE_PROJECT_DIR`. But that D-scenario makes
  `_is_canonical` return **False** at L698/L692 → `decide()` early-returns allow at
  L1132 → **execution never reaches the C `except` at L1137-1139.** C's only real
  divergence source is **TOCTOU** between the resolve inside `_is_canonical` (L691)
  and the second resolve at L1137 (symlink component swapped/looped mid-call). If
  Wave 1 tries to reach C through the D setup, it will "fail to reproduce" and may
  wrongly retire C as a dead `except` — when it is a live, if narrow, TOCTOU
  fail-open. **Verify C with a symlink-race repro, not the D path.**

- **R3 — Fix A's soundness is bounded by candidate-set completeness, which F (out
  of scope) says is NOT guaranteed.** `_extract_mcp_target_paths` (L359-385) only
  harvests keys in the fixed `_MCP_WRITE_PATH_KEYS` set; `apply_patch_paths` is
  host-adapter-surfaced (L1342-1350). If the real write-set ⊋ the extracted
  candidate set (a hunk header, a rename source, a nested/novel MCP schema),
  most-restrictive-wins iterates over an incomplete set and the unreported
  canonical path sails through regardless of the fix. A's repro will go green
  while the bypass class is only *partially* closed. This must be stated as A's
  residual, or the fix over-claims.

- **R4 — D's repo_root anchor can create a hook/tool target mismatch (a different
  miss).** Anchoring `path_str` to `repo_root` before `relative_to` is only correct
  if the *writing tool* also resolves relative paths against repo_root. If a given
  adapter resolves relative paths against **CWD**, the hook would gate
  `repo_root/path` while the tool writes `cwd/path` — the guard inspects a different
  (possibly non-existent) file and MISSES the actual canonical write. Swapping a
  CWD-anchor bypass for a wrong-anchor bypass is not a net fix. The anchor must
  match the tool's resolution semantics per adapter, or gate **both**
  interpretations most-restrictively.

- **R5 — O(n·m) sentinel re-scan under attacker-controlled candidate count →
  timeout → infra fail-open.** decide() calls `_find_sentinels` + per-sentinel
  `read_bytes()`+sha256 (L829-837, L1141-1143). Iterating over N canonical
  candidates makes this O(N·M) filesystem reads/hashes. A multi-file event with a
  large candidate list (each ≤4 KiB per L379, but the list itself is uncapped at
  L1347-1350) can push the hook past its timeout budget; hooks fail-OPEN on
  timeout (CLAUDE.md §4 infra class). The fix amplifies an existing DoS→bypass
  vector.

- **R6 — Multi-file SKILL.md unicode guard gap (fix-A-adjacent regression
  surface).** The invisible-unicode hardblock keys on the single `file_path`
  (L1421-1422 `file_path.endswith("SKILL.md")`). In a multi-file event where the
  canonical SKILL.md is candidate[k>0] and the event is otherwise allowed (all
  granted), the guard inspects candidate_paths[0], not the SKILL.md → the
  per-file unicode block is skipped. Fix A should make this guard multi-candidate-
  aware, or at minimum not regress it.

## Must-fix (ADJUST conditions)

1. **A — fail-CLOSED on per-candidate classification exception.** Replace the
   loop's `except Exception: continue` (L1373-1374) semantics: an exception while
   classifying a candidate in a canonical-bearing multi-file event must **block**
   (`canonical_edit_hook_fault`), never skip. (Closes R1 / V-A.)

2. **A — do NOT literally call `decide()` per candidate.** `decide()` is not pure:
   it fires `_emit_persona_coverage_synthesized` (L1146) and returns a terminal
   emit payload. Factor a pure predicate `(is_canonical AND granted?)` per
   candidate, aggregate most-restrictive, and **emit exactly once**. Naively
   looping `decide()` yields N coverage emits + ambiguity over which payload is
   written.

3. **A — the block emit/audit must name the ungranted candidate(s), not
   `candidate_paths[0]`.** Otherwise the veto record (L1408-1415) and block reason
   mis-attribute the offending path — a forensics failure on a security block.

4. **A — record the candidate-set-completeness residual explicitly** (R3). A's
   fix closes ordering-bypass over the *reported* set only; F (under-reporting)
   remains out-of-scope and must be logged as accepted residual in the Wave-2 ADR.
   Do not let a green A-repro imply the whole multi-candidate class is closed. Add
   a Wave-1 assertion that the extracted candidate set is at least as large as the
   host adapter's declared write-set for the test event (an extraction oracle),
   even if closing the gap is deferred. (Closes V-F-coupling.)

5. **C — fail-CLOSED unconditionally; do not gate the fix on D-reachability.**
   The `except (ValueError, OSError)` on a confirmed-canonical path (L1138-1139)
   must `_emit_block(canonical_edit_hook_fault)`, matching F-01-07. Its true
   trigger is TOCTOU (R2), which is real and does not require D. Bricking risk is
   negligible: a benign canonical edit that passed `_is_canonical` passes the
   second resolve too, absent an active race; the only benign hit is a transient
   FS fault, on which fail-closed is the correct posture for a canonical path.
   (Closes V-C.)

6. **C — verify with a symlink-race repro, not the D scenario** (R2). If a
   deterministic TOCTOU repro cannot be built, still fail-close (defense-in-depth,
   one line) and annotate the divergence window — do NOT dispose as dead.

## Nice-to-have

- **D — gate both anchors most-restrictively** (R4): block if EITHER the
  CWD-anchored or repo_root-anchored resolution of a relative `path_str` lands on a
  canonical path. Removes the "picked the wrong anchor" failure mode without
  needing to prove each adapter's semantics. Confirm `Path(repo_root) / abs_path`
  correctly *keeps* absolute paths absolute (pathlib discards the left operand on
  an absolute right operand) so the join only affects relative inputs.
- **R5 — cap candidate count on canonical-bearing events**: if
  `len(candidate_paths)` exceeds a sane bound (e.g. 256), fail-CLOSED rather than
  risk a timeout fail-open.
- **B — correct the false comment (L800-803, L879) is the mandatory minimum**; a
  security comment that claims `.asc` coverage the key does not provide will
  mislead the next auditor. Adding `.asc` mtime/size + `sentinel-signers.txt` hash
  to the key is cheap and makes the key honest — worth doing since Fix A raises the
  per-process re-verify count, even though I confirmed it is **not** exploitable
  (each candidate has a distinct `target_rel` → distinct cache key L818-840, and
  there is no attacker execution point between synchronous loop iterations).
- **R6 — make the unicode-guard scan every allowed canonical SKILL.md candidate**,
  not just `file_path`.

## Unseen

- **U1 (primary) — the loop `except: continue` fail-open** (R1). Not among A/C/B/D
  as framed, but it is the single most dangerous line once the loop becomes
  decision-authoritative. It is a 5th latent fail-open in the same gate.
- **U2 — candidate extraction is a silent trust boundary** (R3). `_MCP_WRITE_PATH_KEYS`
  is a fixed allowlist of input keys; there is no oracle that extracted-set ⊇
  actual-write-set. This is the structural reason A can never be *fully* closed in
  isolation from F.
- **U3 — timeout→fail-open amplification** (R5): a governance gate whose cost
  scales with attacker-controlled input, on an infra-fail-open substrate, is a
  bypass primitive. New with the multi-candidate iteration.
- **U4 — regression: multi-file SKILL.md unicode-guard evasion** (R6).
- **U5 — cache poisoning is NOT reachable** (I checked, so the debate need not
  re-litigate it): distinct `target_rel` per candidate ⇒ distinct key; env-override
  bypasses the cache entirely (L891); process-per-invocation bounds lifetime. B
  stays LOW.

## What I would NOT change

- **E and F stay OUT of scope** — E (envelope `parse_error → allow`, L1323-1325) is
  the documented infra fail-open contract; flipping it bricks sessions on benign
  parse hiccups. F is a real Layer-A/B boundary. Correct dispositions — with the
  one caveat that F must be *recorded as A's residual* (Must-fix 4), not forgotten.
- **The verification-first gate** — keep exactly. No fix without a failing-first
  repro through the same adapter path `main()` consumes.
- **The single-candidate fast path** (L1367 guard) — keep outcome-identical; do not
  perturb the Claude Code Edit/Write common path.
- **Kernel ceremony + the preflight behavioral oracle** (Wave 3) — keep; the oracle
  that fails unless the staged bytes actually carry the A-fix is essential (never
  sign a claim the bytes don't hold).
- **`_find_sentinels` symlink drop** (L780-791) and the `_CANONICAL_PREFIXES`
  fast-path (L662-680) — do not weaken while touching this file.
- **The `CEO_SENTINEL_UNLOCK` cache bypass** (L891) — correct; leave it.
