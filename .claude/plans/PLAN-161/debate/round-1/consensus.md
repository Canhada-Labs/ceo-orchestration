---
plan: PLAN-161
round: 1
created_at: 2026-07-21
critiques: [Critic-A, Critic-B, Critic-C]
verdicts: [ADJUST, ADJUST, ADJUST]
round_verdict: PROCEED
consensus_adjustments: 12
---

# PLAN-161 round-1 consensus

Three ADJUST, zero REJECT. All seven thread premises verified true on
disk by all three critics independently. The plan's architecture (one
consolidated sweep, one sentinel ceremony) is unanimously endorsed; the
wave TAXONOMY was factually broken and is rebuilt below. One
VETO-flagged item requires an Owner tie-break (CF-10). Verdict:
PROCEED after adjustments — design-coherent; shipping authorized only
by the verification cascade.

## Consensus findings (2+ critics)

- **CF-1 [A+B+C, load-bearing]** W1 "ungated" is false for its biggest
  items: `scripts/upgrade.sh`, `scripts/install.sh`,
  `scripts/_framework_manifest_set.sh` and
  `templates/settings/settings.base.json` are canonical-guarded
  (`check_canonical_edit.py:187,189,197,305-306`). U1/U2/U3/T1 source
  edits move into the W2 ceremony; W1 keeps only genuinely unguarded
  work: new tests under `scripts/tests/`, V1
  (`.claude/scripts/local/verify-counts.sh` — verified unguarded), H1.
- **CF-2 [A+C]** C4 amends a WRITTEN ADR-163 invariant ("exactly 2
  attempts", ADR-163:55-57, restated validate.yml:1222). Resolution:
  in-place AMEND of ADR-163 inside the ceremony (no ADR-count ripple),
  `timeout-minutes` 16→~25 in the same kernel hunk with the budget math
  stated (2×420s already ≈940s of 960); 3rd attempt gated on a cheap
  contention pre-probe (`profile-opus-4-7.py --floor`, ~2s) — still-
  contended VM → fail fast with a DISTINCT message, never burn 420s
  blind.
- **CF-3 [A+B+C]** C2 amends ADR-114's one-pipe shape
  (council-audit.js:16-22,160-168) → ADR-114 amendment REQUIRED in W2
  scope. Composition pinned NOW (was OQ2): argv carries a FIXED,
  non-repo-derived pointer instruction; the redacted brief lives in a
  0600 artifact inside a fresh `mkdtemp` 0700 dir under scratch (never
  the repo tree, never bare /tmp); redactor writes `brief.tmp` then
  rename-into-place, `&&`-chained → the path grok references EXISTS
  ONLY IF the redactor exited 0 (structural fail-closed; redactor
  verified fail-closed at codex_egress_redact.py:293-312).
  `$(cat artifact)` argv-content is FORBIDDEN (ps visibility, ARG_MAX,
  trailing-newline stripping breaks the byte oracle). Cleanup: trap
  EXIT + start-of-run stale-artifact sweep; SIGKILL/budget-kill residue
  named as accepted residual (post-redaction bytes only) in the ADR.
  Regressions: artifact bytes == redactor stdout; argv contains no
  repo-derived bytes; induced redactor failure → final artifact path
  DOES NOT EXIST; artifact 0600 / dir 0700 asserted.
- **CF-4 [A+C]** `scripts/_grok_harness.sh` guard status DECIDED: it is
  installer-emission surface, NOT the live egress path — C2 keeps ALL
  egress composition inside already-guarded surfaces
  (`.claude/workflows/council-audit.js`; the kernel redactor stays
  untouched — composition is shell-side in the lane pipeline). No guard
  enrollment this plan; recorded residual with revisit trigger: if
  egress logic ever lands in `_grok_harness.sh`, that is the F3 class →
  guard-enroll (kernel override) first.
- **CF-5 [A+B]** Sentinel scope PRE-DECLARED in the plan (mid-ceremony
  scope additions are the drift the touched−scope=∅ rail blocks).
  Kernel is decidable now: `.claude/settings.json` + `validate.yml` =
  the two kernel hunks (`check_arbitration_kernel.py:125,135`).
  The ceremony record must NAME the four-guard-class concentration
  (deny baseline + egress + CI gate + Stop hook) so the Owner signs the
  breadth knowingly.
- **CF-6 [B+C CONFLICT → resolved]** U3 purge provenance. C: current-
  source hashes cannot match bytes mis-installed by an OLDER framework
  version (purge inert). B: the adopter-resident manifest must never
  both nominate and authorize a deletion. Synthesis honoring both:
  **nomination** = hardcoded walk of the excluded trees only (the
  manifest cannot nominate paths), lstat/no-follow, regular files only,
  relpaths through `_baseline_relpath_unsafe` (upgrade.sh:607-637 —
  reuse, never reimplement); **authorization** = hash match against
  EITHER current framework-source bytes OR the target
  manifest-recorded baseline hash (needed across versions); neither →
  keep + warn. Purge is NOT default-on: explicit
  `--purge-misinstalled` flag (hash reads provenance, not intent);
  always backup first (symlink-preserving); dry-run oracle covers the
  purge step; regression runs the upgrade TWICE (second run = purge
  no-op, no new backup content). ADR-155 in-place amendment records
  the doctrine change (today's rule is "never auto-delete",
  upgrade.sh:880-881).
- **CF-7 [A+C]** U2 exclusion predicate applied at all THREE
  upgrade-side points: union walk (upgrade.sh:888-891), legacy
  no-manifest `cp -R` branch (upgrade.sh:1046-1058 — the stale-adopter
  path), and `_framework_manifest_files` (_framework_manifest_set.sh:
  129-134). Single-source home = a bash-3.2-safe predicate function
  (`_framework_path_excluded()`) in `_framework_manifest_set.sh` (the
  file already IS the single canonical enumeration — of the include
  set). Regression covers a manifest-LESS fixture adopter.
- **CF-8 [A+B]** Per-concern commit segmentation under the single
  sentinel (bisectability/per-concern revert = the real D1 rollback
  answer) + drop-out protocol: a concern whose staged oracle is red at
  ceremony time (most likely C2) is DROPPED from the batch (touched ⊆
  scope stays legal) and deferred — never stalls the other six.
- **CF-9 [A+B]** C5 emit keying, exact: healthy-class ONLY from
  `decide()` branches where a session+fingerprint-matched record gated
  a NON-EMPTY L3 path set with verdict APPROVE/REJECT
  (check_codex_stop_review.py:524-560); NEVER from the no-L3 early
  return (:512-519) nor from `_record_main` (arbitrary-stdin surface);
  UNAVAILABLE (:561-571) and ABANDONED (:574-583) branches MUST emit
  failopen-class. D6 RESOLVED: reuse the already-registered typed
  labels `pair_rail_review_passed`/`pair_rail_codex_unavailable`
  (classified ceo-boot.py:1717-1720; a NEW classifier row can never go
  green while the dead `pair_rail` row sits at zero — worst-of,
  ceo-boot.py:1794-1803) + producer field for attribution;
  `audit_emit.py` trusted-caller allowlist entry planned in W2 scope.
  L4 acceptance corrected: green arrives after the FIRST POST-LAND
  review round (the ceremony that lands C5 is reviewed by the
  pre-C5 hook — it cannot observe its own landing). Dedupe healthy
  emits per (session, fingerprint).
- **CF-10 [B VETO-flagged + A R-2 — OWNER TIE-BREAK]** Template
  `Write(...)` twins (`settings.base.json:592,594,596`): on an older
  CLI that still consults `Write(path)`, the twin is the only
  zero-runtime-dependency fail-closed rail for the Write tool on fresh
  installs. VETO lift conditions: (i) install-time CLI floor, or
  (ii) Owner explicitly accepts the old-CLI residual, recorded.
  → escalated to the Owner as restructured OQ5 (see plan). Regardless
  of the answer: LIVE settings + floor removal in one commit is safe
  (floor ⊆ template holds either way); L1 gains a POSITIVE
  Write-denial probe (prove `Edit(PROTOCOL.md)` alone denies a
  Write-tool attempt on the pinned CLI, distinguishable from the
  hook's block message — the "Edit covers all" premise is
  substrate-observed, never proven); and the plan states explicitly
  that EXISTING adopters keep their warnings either way (upgrade.sh
  EXISTS-SKIPs settings.json:1235-1237) — deliberate, documented.
- **CF-11 [A+C]** C1/T1 atomicity is FIVE surfaces in ONE commit:
  live settings (kernel segment) + `check_harness_config.py:116-124`
  floor + harness-config fixtures + template (per OQ5 outcome) +
  `test-install-deny-baseline.sh:173-179` (asserts `Write(PROTOCOL.md)`
  at deny[2] — reddens the moment the template drops the twin). Plus:
  `_deny_baseline_comment` "Entries 8-27" index shift, and the stale
  "lines 644-653" docstring anchor in check_harness_config.py:114-115.
- **CF-12 [A+C]** U1 family audit COMPLETE (Critic-C): exactly two
  unguarded writers — `upgrade_agents_canonical_only`
  (upgrade.sh:1366-1420) and `mkdir -p "$BAK_DIR"` (:567). Dry-run
  oracle = full tree LISTING (files+dirs+symlinks) + per-file sha256,
  covering backup/scaffold writes.

## Single-critic insights kept

- [C] W3-L2 CI wiring: fixture-adopter e2e test into `smoke-install.yml`
  (ubuntu, already path-triggers on upgrade.sh; timeout 5→~8; test
  bash-3.2-safe so the Owner can run it on macOS). Also wire
  `test-install-deny-baseline.sh` (currently NO workflow runs it).
- [C] W1 check line must name the new `.sh` tests explicitly (pytest
  `-k` collects the python tree only).
- [B] C3 keeps a HARD upper cap (budget is a cost-DoS control) —
  bounded growth, never proportional-unbounded; [C] make the budget
  mechanical (`timeout ${N}` interpolated into the pipeline), not an
  LLM-honored prose number.
- [B] L1 asserts on the three specific rule names, not "zero warnings".
- [B] L2 fixture seeds a symlink inside an excluded tree + a
  byte-identical intended-keep file (proves warn-and-skip posture).
- [B] Council report attests sent bytes by hashing the artifact at
  hand-off (post-run artifact is not evidence — sandbox allows temp
  writes).
- [B] Liveness signal is exactly as trustworthy as the review record
  store (`--record` provenance gap) — noted in plan, no new authority.
- [A] Precise paths throughout the scope declaration.

## Single-critic insights rejected / deferred

- [B NTH-2] Install-time minimum-CLI-version check in install.sh —
  DEFERRED to backlog (bigger surface than this sweep; OQ5 route (ii)
  suffices if chosen).
- [A] "Stranded adopter population" tracking beyond stating the
  residual — DEFERRED: the sweep documents who keeps warnings (UN-1)
  and the upgrade fix reaches test-tree cleanup on next adopter
  upgrade; fleet tracking is out of scope for a framework repo.
- [C NTH-7] `.claude.bak` retention pruning — DEFERRED (one-sentence
  doc note only; pruning is its own risk surface).

## Plan adjustments applied (index)

1. Waves rebuilt per CF-1 (W1 = tests/V1/H1 only; W2 scope +4 files).
2. W2 sentinel scope enumerated file-by-file; kernel hunks named
   (settings.json, validate.yml); four-guard-class concentration named
   as ceremony-record requirement (CF-5).
3. C2 rewritten: composition pinned, ADR-114 amendment, structural
   fail-closed mechanics, regressions extended (CF-3); OQ2 CLOSED.
4. C4 rewritten: ADR-163 in-place amend + timeout bump + floor-probe
   gate (CF-2); OQ4 CLOSED.
5. C5 rewritten: exact keying, typed-label reuse, allowlist entry,
   L4 timing fix (CF-9); D6 CLOSED.
6. U2/U3 rewritten per CF-6/CF-7 (three-point predicate, dual-rail
   provenance, opt-in flag, ADR-155 amend); OQ1 restated to ratify the
   REAL boundary.
7. C1/T1 five-surface atomic commit + comment/docstring fixes (CF-11).
8. U1 oracle widened per CF-12.
9. CF-4 residual recorded (grok harness guard status).
10. CF-8 segmentation + drop-out protocol added to W2.
11. L1 positive Write-denial probe + adopter-residual statement
    (CF-10); OQ5 (Owner tie-break) added.
12. Single-critic keeps folded (CI wiring, hard cap, rule-name
    asserts, seeded fixtures, handoff hash, check-line naming).

## Round verdict

**PROCEED** (design-coherent) — contingent on the OQ5/OQ1 Owner
tie-breaks recorded in the plan before `reviewed`. Shipping authority
remains with the verification cascade (V2 Codex pair-rail → V3 Owner
GPG), not this debate.
