---
plan: PLAN-161
round: 1
critic: staff-security-engineer
lens: security (ADR-052 VETO surface: auth, input handling, egress, guard surfaces)
created_at: 2026-07-21
---

# PLAN-161 round-1 critique — Staff Security Engineer

## Verdict

**ADJUST** — with one VETO-flagged item inside Must-fix (MF-1: the three
`Write(...)` deletions in `templates/settings/settings.base.json`). The
sweep's security reasoning is mostly sound and two of the four priority
surfaces (C2, C5) can land STRONGER than status quo if the Must-fix
structure is required rather than left to execution discretion. The plan's
flat back-compat claim for C1 ("No protection is lost") is
version-conditional and wrong as stated for the template surface.

## Summary

Verified all four priority surfaces first-hand. (a) C1: the deny pairs
exist exactly as claimed (`.claude/settings.json:731/733/735`,
`check_harness_config.py:116-124`, `settings.base.json:592/594/596`) and
`check_canonical_edit.py` independently guards all three paths on the
`Edit|Write|MultiEdit|mcp__.*` PreToolUse matcher in BOTH live settings
and template — but the permission deny is the only rail with no runtime
dependency (fail-closed at the harness), and on an older CLI whose
`Edit(path)` rules cover only the Edit tool, deleting the `Write(X)` twin
from the template removes that rail for the Write tool entirely. The
back-compat answer the task demands: **removal is safe for the live repo,
NOT unconditionally safe for templates** — templates should keep the pair
(the floor can still shrink; subset invariant holds since floor ⊆
template) or removal must be gated on an install-time CLI floor. (b) C2:
today's "one-pipe" enforcement is itself prose in a prompt
(`council-audit.js:159-168`); the redactor CLI is genuinely fail-closed
(`codex_egress_redact.py:293-312`: nonzero exit + empty stdout on ANY
error), which makes a structurally fail-closed artifact handoff
achievable via create-under-mkdtemp + rename-into-place — but the plan
must pin the composition (argv-content vs file-pointer) and amend
ADR-114. (c) U3: the sanitizer to reuse exists
(`upgrade.sh:607-637`); the purge must never trust adopter-resident
manifest hashes for deletion decisions and must be lstat/no-follow,
regular-files-only. (d) C5: FALSE GREEN is real and specific — the
`no L3 paths touched` early return (`check_codex_stop_review.py:512-519`)
fires on every ordinary session stop; any healthy emit there paints the
rail green for 7 days with zero reviews. Also, the D6 "append a distinct
classifier" alternative CANNOT go green by itself: overall status is
worst-of and a zero-event rail row stays yellow
(`ceo-boot.py:1794-1803`).

Fail-open/fail-closed contract statement per item (task §3):

- **C1** — permission deny rules: fail-closed, zero runtime dependency
  (the harness enforces them; no python3, no hook file needed). The
  canonical-edit hook is fail-closed on parse/resolve faults
  (PLAN-160) but structurally cannot fire if python3/the hook file is
  absent — the CLI's hook-failure posture then governs. Removing the
  Write twin on an old-CLI adopter therefore converts Write-tool
  protection from two independent rails (one unconditionally
  fail-closed) to one conditionally-available rail. **That is a
  residual-protection contract change for the template surface → per
  the plan's own §Approach rule it needs an ADR, or templates keep the
  pair** (MF-1/MF-2).
- **C2** — redactor: fail-closed today (verified). Lane-unavailable:
  fail-loud today; plan keeps it. The composition change (pipe →
  artifact) amends a written BLOCKING invariant
  (`council-audit.js:16-22` cites ADR-114's one-pipe as the single
  chokepoint) → **ADR-114 amendment required** (MF-5); contract
  direction preserved only if MF-4's structural gating is mandatory.
- **U3** — upgrade.sh today NEVER deletes adopter files
  (`refuse|theirs|backup` on conflict, `upgrade.sh:115`, backups at
  `BAK_DIR` :549); adding deletion is a NEW destructive capability on
  the installer surface → contract change → OQ1 ratification must
  cover the flag shape (opt-in vs default-on), and the capability
  deserves an ADR or at minimum a plan-recorded contract note (MF-6).
- **C5** — the liveness check is advisory fail-open (never blocks,
  `ceo-boot.py:1750-1752`); `decide()` gating semantics are untouched
  by the plan. Adding an emit changes no gating contract → no ADR
  needed IF the already-registered typed labels are reused; keying per
  MF-7 is what prevents false green.

## Risks

- **R-1 (C1):** The premise "CLI ≥2.1.216 no longer consults
  `Write(path)` and `Edit(path)` covers all editing tools" is a
  substrate observation, unverifiable from this repo. If it is wrong in
  the OTHER direction (Write rules ignored AND Edit rules do not cover
  the Write tool), removal opens Write at the permission layer
  everywhere, not just for old CLIs. L1 as written only proves the
  WARNINGS are gone — it never proves the Edit rule actually denies a
  Write-tool attempt (MF-1 probe).
- **R-2 (C2):** If "grok argv references THAT artifact" is implemented
  as `grok -p "$(cat artifact)"`, the redacted brief bytes land in
  argv — world-visible via `ps`/`/proc` to every local user for the
  process lifetime. The one-pipe design had no such at-rest or in-argv
  exposure. Post-redaction bytes are bounded-sensitivity, but this is a
  new local exposure class the plan does not name (MF-3).
- **R-3 (C2):** `trap`-guaranteed cleanup does not survive SIGKILL —
  and the lane's own budget rule says "KILL it" at ~180s
  (`council-audit.js:169-170`). The kill path is exactly the path most
  likely to strand a redacted-but-scope-derived brief on disk (MF-5).
- **R-4 (U3):** A byte-identical file the adopter INTENDED to keep is
  indistinguishable from a mis-installed one by hash — hash-gating
  reads provenance, not intent. Deletion default-on would make the
  upgrade destroy a dependency the adopter chose to rely on, with only
  the backup as recourse (MF-6.3).
- **R-5 (U3):** `shasum` follows symlinks; a symlink inside an excluded
  tree pointing outside the repo would be hashed THROUGH, and a naive
  backup (`cp -r` variants) can copy through it. The purge walk must
  lstat and refuse non-regular files (MF-6.1).
- **R-6 (C5):** A healthy emit keyed to the wrong branch creates
  structural false green: the `no L3 paths` early return fires on every
  trivial stop; `--record` accepts arbitrary stdin from any Bash caller
  (`echo "VERDICT: APPROVE" | --record` — the hook's own documented
  provenance gap, `check_codex_stop_review.py:52-58`). The liveness
  signal inherits that gap at best; keyed wrongly, it amplifies it
  (MF-7).
- **R-7 (C5):** If the UNAVAILABLE/ABANDONED branches emit nothing,
  the check can read green (one stale healthy event in the window)
  while every subsequent stop fail-opens — the exact S254 class the
  check exists to expose (MF-7).
- **R-8 (C1/D2):** Three surfaces must stay mutually consistent under
  the gate: floor (`DENY_BASELINE`), live deny, template deny — the
  gate checks floor ⊆ deny for BOTH files (`check_harness_config.py:
  169-172`). The only red-free orderings are "floor shrinks with live
  in the same commit" (plan has this) and "template may keep a
  superset" (plan currently removes it — see MF-1).
- **R-9 (D1):** One sentinel spanning deny baseline + egress path + CI
  gate + a Stop hook concentrates blast radius: a single GPG ceremony
  authorizes edits across four distinct guard classes. `touched −
  scope = ∅` still holds, but per-change review granularity is
  deliberately traded away. Acceptable, but it should be named in the
  ceremony record, not implicit.

## Must-fix

- **MF-1 (C1 — VETO-flagged).** VETO line:
  `templates/settings/settings.base.json:592,594,596` — do not delete
  the three `Write(...)` entries from the TEMPLATE. Condition to lift,
  either of: (i) an install-time CLI version floor (install.sh has
  none today — verified) refuses/warns below the version where
  `Edit(path)` covers the Write tool, with the residual documented; or
  (ii) the Owner explicitly accepts the old-CLI residual as an OQ
  answer, recorded in the plan. Independently, extend L1 with a
  **positive denial probe**: on the pinned CLI, a Write-tool attempt
  against `PROTOCOL.md` with only `Edit(PROTOCOL.md)` present must be
  refused **by the permission layer** — distinguishable from the
  hook's `CANONICAL-EDIT-BLOCKED` message — so the "Edit covers all
  editing tools" premise is proven, not assumed. Removing the pairs
  from the LIVE `.claude/settings.json` + the floor
  (`check_harness_config.py:116-124`) in one commit is fine (floor ⊆
  template still holds when the template keeps a superset).
- **MF-2 (C1).** Qualify the plan's §Context item 1 claim: "No
  protection is lost" is true only for CLI versions with the new
  semantics. If after MF-1 the template pair is still removed, that is
  a residual-protection contract change for a class of adopters → ADR
  required per the plan's own §Approach sentence.
- **MF-3 (C2).** Pin the composition. Three candidate mechanisms hide
  under "grok argv references THAT artifact": (i) a grok file-prompt
  flag (existence unverified — conjecture; must be fixture-proven);
  (ii) `$(cat artifact)` substitution → redacted bytes in argv (`ps`
  leak, R-2) — forbid, or explicitly accept in the ADR with the
  exposure named; (iii) a FIXED, non-repo-derived pointer instruction
  in argv ("read the brief at <path> and follow it") + grok reads the
  0600 artifact itself — viable because the `council` sandbox profile
  extends `read-only` = read everywhere
  (`templates/grok/sandbox.toml.example:49-52`), so no sandbox
  widening is needed; the artifact must live in $TMPDIR-scratch, never
  under the repo tree. Update regression (a) accordingly: assert
  artifact bytes == redactor stdout bytes AND argv contains no
  repo-derived bytes.
- **MF-4 (C2).** Make "grok never runs if redaction failed" structural,
  not prose: artifact created inside a fresh `mkdtemp` 0700 dir (never
  a bare temp file in shared /tmp — symlink attack surface); redactor
  writes to `brief.tmp` then `mv` (rename-into-place) to the final
  name, `&&`-chained — so the path grok's argv references EXISTS ONLY
  IF the redactor exited 0. This is sound precisely because the
  redactor is verified fail-closed (nonzero + empty stdout on any
  error, `codex_egress_redact.py:293-312`). Extend regression (b): on
  induced redactor failure, assert the final artifact path does not
  exist (not merely "grok not invoked"). This is the pipefail
  equivalent the task asks about — it exists and must be REQUIRED in
  C2's acceptance, not left as an execution choice.
- **MF-5 (C2).** ADR-114 amendment (or successor) is REQUIRED in W2
  scope, not conditional: `council-audit.js:16-22` cites the one-pipe
  shape as a BLOCKING invariant; C2 replaces that shape. The ADR must
  carry the cleanup contract: `trap` EXIT cleanup, the SIGKILL/budget-
  kill residue named as accepted residual (post-redaction bytes only),
  and a start-of-run sweep of stale artifacts from prior runs.
- **MF-6 (U3).** Pin four properties in the plan text: (1) candidate
  set = a walk of the TARGET's excluded-tree paths, lstat/no-follow,
  regular files only — symlinks are never followed, never hashed-
  through, at most warn-and-skip; backups symlink-preserving. (2) The
  hash gate compares target bytes against FRAMEWORK-SOURCE bytes
  recomputed from the upgrade payload — NEVER against the
  adopter-resident manifest hash (the manifest is adopter-controlled
  data; a tampered entry must not be able to both nominate and
  "authorize" a deletion). If manifest relpaths are consulted at all,
  they must pass `_baseline_relpath_unsafe` (`upgrade.sh:607-637` —
  absolute, `..`, control chars, symlinked components all rejected;
  reuse it, do not reimplement). (3) OQ1 must ratify the FLAG SHAPE,
  not just "hash-gated yes/no": recommend purge NOT default-on in its
  first release (explicit `--purge-misinstalled`, or a listed plan +
  confirm), because hash-equality cannot see adopter intent (R-4) and
  this is a new destructive capability on the installer contract. (4)
  U1's dry-run byte-identity oracle must cover the purge step.
- **MF-7 (C5).** Key the emit exactly: healthy-class ONLY from
  `decide()` branches where a session+fingerprint-matched record gated
  a NON-EMPTY L3 path set with verdict APPROVE or REJECT
  (`check_codex_stop_review.py:524-560`). Explicitly NO emit from the
  `no L3 paths touched` early return (:512-519) and NO healthy emit
  from `_record_main` (:452-494, arbitrary-stdin surface). The
  UNAVAILABLE-verdict branch (:561-571) and the ABANDONED branch
  (:574-583) MUST emit failopen-class — they are this rail's ADR-106-
  style fail-open allows, and without them the check cannot distinguish
  a rotting reviewer from health (R-7). State this keying in the plan
  as C5 acceptance, alongside the behavioral boot-green check.
- **MF-8 (C5).** Name the D6 mechanical trap: appending a NEW
  `FAILOPEN_RAIL_CLASSIFIERS` row cannot reach green while the dead
  `pair_rail` row stays at zero events — overall is worst-of and a
  signal-less rail is yellow by design (`ceo-boot.py:1794-1803`). The
  workable routes: (i) emit the already-registered typed labels
  `pair_rail_review_passed` / `pair_rail_codex_unavailable` (classified
  at `ceo-boot.py:1717-1720`; registered `audit_emit.py:510-511`; typed
  emitter exists :9320) with a producer field for forensic attribution;
  or (ii) retire/merge the dead row in the same change. Note the
  emit-path trusted-caller allowlist is default-deny
  (`audit_emit.py:1595-1609`) — adding the Stop hook as a producer may
  need an allowlist entry; that is audit-surface ceremony scope, plan
  for it in W2.

## Nice-to-have

- **NTH-1 (C5):** Dedupe healthy emits per (session, fingerprint) — an
  APPROVE record consulted across multiple stops in one session would
  otherwise mint multiple healthy events from one review. Liveness only
  needs ≥1; inflated counts skew the partial-fail-open ratio.
- **NTH-2 (C1/general):** An install-time minimum-CLI-version check in
  install.sh benefits more than this item (hook schema drift, matcher
  semantics); worth its own backlog line even if MF-1 is satisfied via
  the OQ route.
- **NTH-3 (C2):** Fixture asserts artifact mode 0600 and parent dir
  0700 (umask can silently widen), and that the artifact path is under
  the scratch root, not the repo.
- **NTH-4 (U3/L2):** Seed the L2 fixture adopter with (a) a symlink
  inside an excluded tree and (b) a byte-identical file the "adopter"
  marks as intended-keep, proving warn-and-skip and the R-4 posture.
- **NTH-5 (C3):** Scope-aware codex budget must keep a HARD upper cap —
  the budget is a cost-DoS control (`council-audit.js:43-44,75-79`);
  "larger scope → larger bound" must be bounded growth, never
  proportional-unbounded.
- **NTH-6 (L1):** Assert on the three specific rule names in the lint
  output, not just "zero warnings" — a future CLI could re-class the
  warning text and vacuously pass the check.

## Unseen

- **UN-1:** Existing adopters are untouched by T1 — templates fix fresh
  installs only, and upgrade.sh does not rewrite an adopter's
  `permissions.deny`. Existing adopters keep the pairs (and, on new
  CLIs, the warnings). If the sweep's goal is "lint silent for
  adopters", either upgrade.sh needs a settings reconciliation step
  (bigger surface — the deny list is adopter-customizable) or the plan
  should state explicitly that existing adopters keep the warnings.
- **UN-2:** The C5 healthy emit inherits the `--record` provenance gap:
  a forged `VERDICT: APPROVE` piped into `--record` already rides the
  gate (documented limitation, pre-push/CI backstops); after C5 it also
  mints liveness credit. Not new authority, but the ADR/plan should
  note the liveness signal is exactly as trustworthy as the review
  record store — no more.
- **UN-3:** The grok `council` sandbox permits WRITES to temp dirs
  (`sandbox.toml.example:41-46`). Grok can therefore modify or replace
  the brief artifact after reading it — harmless for egress (already
  sent) but a forensic caveat: the on-disk artifact after a run is not
  evidence of what was sent. If the run report wants to attest sent
  bytes, hash the artifact at hand-off time.
- **UN-4:** W2's single sentinel spans four guard classes (deny
  baseline, egress path, CI gate, Stop hook) — R-9. Name the
  concentration in the ceremony record so the Owner signs the breadth
  knowingly, not by default.

## What I would NOT change

- The **fail-loud lane-unavailable posture** for C2 (redaction failure
  → `unavailable`, never a retry-without-redaction) — this is the right
  contract and the plan preserves it verbatim.
- The **hash-gated purge concept** itself (U3) — provenance-by-bytes
  plus backup is the correct trust boundary for deleting inside an
  adopter repo; my adjustments constrain its inputs and default, not
  its design.
- Keeping the **`Edit(X)` deny rules and the canonical-edit hook**
  untouched — correct; the protection genuinely lives there on current
  CLIs.
- **C4's scope discipline** — retry cadence only, N=200 percentile
  semantics (PLAN-159/ADR-163) untouched. No gate-weakening smell.
- The **behavioral acceptance framing** (L1-L4): proving the lint gone,
  the purge inert under dry-run, boot green after a REAL review round —
  this is the fixture-vs-livefire lesson applied correctly.
- **D1 consolidation + D5's hold-at-`reviewed` fallback** — one
  well-scoped ceremony is acceptable with R-9/UN-4 named, and refusing
  to silently accept a newly-degraded council quorum is the right
  default.
