---
id: PLAN-160-canonical-edit-council-findings
parent: PLAN-156-FOLLOWUP
title: check_canonical_edit.py hardening — verify + fix the S276 council findings (A/C/B/D)
status: draft
created: 2026-07-17
owner: CEO
# Draft until its own Wave 0 debate runs — check_canonical_edit.py is a
# _KERNEL_PATH and every fix here changes a security gate's decision.
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
| **C** | MED — fail-open on canonical path | `decide()` L1136-1139 | After `_is_canonical` returns True (L1131), the repo-relative resolve for sentinel matching (L1137) is wrapped in `except (ValueError, OSError): return _emit_allow()` — fail-OPEN on a path already confirmed canonical, contradicting the F-01-07 fail-CLOSED contract. `main()`'s fail-closed wrapper (L1378) never sees it (the inner except swallows). | **Confirmed code**. BUT reachability is coupled to D: `_is_canonical` (L691) does the SAME `resolve().relative_to()` and returns True only if it succeeded; for L1137 to then raise, the two resolves must DIVERGE (TOCTOU, or the D-class CWD mismatch). Wave 1 must prove a divergence exists or dispose C as a dead `except`. |
| **B** | LOW — revocation staleness (bounded) | `_compute_sentinel_cache_key` L827-840 | Cache key hashes only sentinel bytes+stat+target_rel — omits `.asc`/signer-allowlist/registry, so a mid-session signer revocation isn't honored until process death; the "`.asc`-covered" comment (L802-803) is false. | **Confirmed code + false comment**. BUT the cache is module-scope and each hook runs as a FRESH subprocess (`hook-profiler.py:178` proves per-invocation processes) — so "process death" ≈ one hook invocation (ms). Blast radius is likely negligible; Wave 1 decides hardening-vs-comment-fix-only. |
| **D** | MED — path-resolution bypass | `_is_canonical` L689-694 | `Path(path_str).resolve()` is CWD-anchored but compared via `relative_to(repo_root)` where `repo_root = CLAUDE_PROJECT_DIR or cwd`; a RELATIVE canonical path when `CWD != CLAUDE_PROJECT_DIR` makes `relative_to` raise → `return False` → treated non-canonical → allowed. | **Confirmed code**. Exploitability needs the harness to pass a relative path AND run the hook with CWD ≠ project dir. Wave 1 must confirm whether Claude Code / the MCP adapters ever do so (if never, D is a robustness fix, not a live bypass). |

Findings **E** (envelope `parse_error → allow`) and **F** (`apply_patch` blobs
unparsed) from the same run are **NOT in scope**: E is a documented infra-class
fail-open (CLAUDE.md §4 — correct by design, the verifier itself flagged the
"should fail closed" framing as contestable); F is a documented Layer-A/Layer-B
boundary, a dependency note not a defect. Record both as "reviewed, no action"
in Wave 0 so they are not re-litigated.

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
- [ ] **Owner ratifies `draft → reviewed`.**

### Wave 1 — VERIFY (failing-first repro per finding)
Check: `python3 -m pytest .claude/hooks/tests/test_canonical_edit_council_findings.py -q` — every repro that represents a REAL defect FAILS against current HEAD
- [ ] **A**: construct a multi-candidate MCP `apply_patch` event (granted
  canonical path first, ungranted canonical path second) through the SAME
  adapter path `main()` consumes; assert current code ALLOWS the ungranted
  edit (the bypass). This is the load-bearing repro — if it cannot be built,
  A is downgraded and the plan says so.
- [ ] **C+D together**: attempt to induce a resolve divergence — a relative
  canonical `path_str` with `CWD != CLAUDE_PROJECT_DIR` — and observe whether
  `_is_canonical` and `decide()` disagree (D → false-negative bypass; C → the
  fail-open `except` firing on a canonical path). If no divergence is
  reachable, dispose C as a dead-`except` (harden anyway or annotate) and D as
  robustness-only, with the attempt recorded.
- [ ] **B**: assert the cache does NOT persist across hook subprocess
  invocations (fresh process = fresh allowlist read). If confirmed ephemeral,
  B collapses to a comment-correctness fix (delete the false "`.asc`-covered"
  claim); if a same-process re-entrancy path exists, harden the key.

### Wave 2 — FIX (only the Wave-1-confirmed defects)
Check: the Wave-1 repros now PASS; full `.claude/hooks/tests/` green; no
existing canonical-guard test regresses
- [ ] **A** (if confirmed): iterate `decide()` over EVERY canonical candidate
  (most-restrictive-wins — ANY ungranted canonical path blocks the event), not
  just the first. Preserve the single-candidate fast path (outcome-identical).
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

**START HERE next terminal.** Read this plan + the W4 section of
`PLAN-156-FOLLOWUP-council-livefire-findings.md` (the run that produced these).
Status is `draft` → run Wave 0 debate FIRST (kernel/L3, security-VETO). Then
Wave 1 is pure verification (read-only + new failing tests) — no canonical edit
yet, so it needs no ceremony and is the safest place to start. Only Wave 2
edits `check_canonical_edit.py`; Wave 3 is the kernel ceremony. The whole plan
is designed so the risky part (touching a security gate) happens LAST and only
for defects Wave 1 actually reproduced.
