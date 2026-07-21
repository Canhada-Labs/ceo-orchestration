---
id: PLAN-161
title: Consolidated maintenance sweep — substrate lint, upgrade.sh, council 3-lane, telemetry
status: reviewed
created: 2026-07-21
reviewed_at: 2026-07-21
reviewed_by: "Owner (João) — chat directive S278 + OQ1/OQ5 structured tie-breaks"
owner: CEO
depends_on: [PLAN-156, PLAN-159, PLAN-160]
budget_tokens: 200-300k
budget_sessions: 2
context_risk: medium
external_wait: none
tags: [substrate, installer, council, perf-gate, telemetry, hooks]
---

# PLAN-161 — Consolidated maintenance sweep

## Context

S278 (2026-07-21) opened with a green boot (23/23 checks, 3 advisory
yellows) and a set of small-but-real pending items accumulated across
S276-S278, none big enough for its own plan but together worth one
consolidated sweep. Sources:

1. **Claude Code CLI startup lint** (observed on every session start in
   this repo AND in adopter repos after upgrade): recent CLI versions
   (≥2.1.216 era) changed permission-rule semantics — `Edit(path)` deny
   rules now cover ALL file-editing tools (Edit, Write, NotebookEdit)
   and `Write(path)` rules are no longer consulted. Our
   `permissions.deny` carries redundant `Write(X)` twins for
   `PROTOCOL.md`, `.claude/settings.json`, `SPEC/**`
   (`.claude/settings.json:731/733/735`), so the CLI prints 3
   deprecation warnings at startup. On CURRENT CLIs no protection is
   lost (each has an `Edit(X)` twin + `check_canonical_edit.py` is
   independent) — on OLDER CLIs the `Write(X)` rule may still be the
   only zero-runtime-dependency fail-closed rail for the Write tool
   (debate CF-10; version-conditional — Owner accepted the residual,
   see §Clarifications OQ5). The twins ship to every fresh install via
   `templates/settings/settings.base.json:592/594/596` and are pinned
   in the `check_harness_config.py:116-124` DENY_BASELINE gate floor
   (invariant: floor ⊆ scanned settings, checked for BOTH live and
   template — `check_harness_config.py:169-172`). The 7-entry baseline
   is ALSO normative text in `ADR-158-harness-config-gate.md:103-112`,
   `docs/PERMISSION-MODEL-DESIGN.md:290-301` and
   `docs/deny-baseline.md:95-104` (codex r1 F3).
2. **Two upgrade.sh bugs found live** during the 2026-07-21 adopter
   upgrade (foxbit, v1.0.x→v1.1.0; both confirmed against the v1.1.0
   tag): (a) the `canonical-5` agent-pin refresh step
   (`upgrade_agents_canonical_only`, `scripts/upgrade.sh:1366-1420`)
   does not honor `--dry-run` — it rewrote `.claude/agents/*.md` sha256
   pins on disk during a dry-run; the writer family audit (debate
   CF-12 + codex r1 F4) found two more target-tree writers entangled
   with dry-run: `mkdir -p "$BAK_DIR"` (`upgrade.sh:567`) and
   `_load_baseline_manifest`'s sanitized-manifest `mktemp` INSIDE
   `$BAK_DIR` (`upgrade.sh:641-647`, called at `:799`) — naively
   guarding the mkdir would break manifest loading (and thus
   provenance classification) under dry-run. (b) the union walk
   (`upgrade.sh:888-891`) — and equally the legacy no-manifest `cp -R`
   branch (`upgrade.sh:1046-1058`) and the manifest writer
   (`_framework_manifest_files`, `scripts/_framework_manifest_set.sh:
   129-134`) — ignore the install.sh framework-internal exclusion set:
   the upgrade installed the dogfood test trees (`hooks/tests/`,
   `scripts/tests/`, `_lib/tests/`, plus `_lib/test_isolation.py` +
   `_lib/testing.py`; ~967 files) into the adopter, re-arming the
   PLAN-119 root-conftest gate and planting fake exchange-key fixtures
   (secret-scanner bait in a trading repo). The union walk's ADD branch
   then RE-ADDS them after the adopter deletes (`upgrade.sh:904-908`).
3. **Council grok-lane arg-contract** (PLAN-160 §Sibling follow-ups):
   grok 0.2.93 `-p/--single` takes the prompt as a CLI arg and does NOT
   read stdin → the mandated one-pipe egress (`redactor-stdout →
   grok-stdin`, prose invariant at `council-audit.js:16-22,160-168`;
   NOTE: ADR-114 itself mandates redaction-before-egress, not the pipe
   shape — codex r1 F10, verified) is structurally uncomposable (grok
   exits rc=2 at clap parse; zero bytes egress). This is THE blocker
   for a clean 3-lane council run and therefore for closing
   PLAN-156-FOLLOWUP (rests at `reviewed` with all F1-F7 fixes
   shipped). Second blocker: the codex lane's ~180s wall-clock budget
   times out on large scopes (W4 run 1).
4. **perf-gate D3 inter-attempt backoff** (PLAN-160 §Sibling follow-ups,
   PLAN-159 follow-up): two doc-only commits (`d0edd88`, `3cf2d2d`)
   defeated the 2-attempt retry under sustained runner load — both
   attempts landed inside the same load window. NOTE (debate CF-2):
   "exactly 2 attempts, never more" is a WRITTEN ADR-163 invariant
   (ADR-163:55-57, restated `validate.yml:1222`) — changing it is an
   ADR amendment; the 16-minute job budget (`validate.yml:1181-1183`)
   fits 2×420s attempts (840s) + smoke + floor + setup with little
   headroom and none for a 3rd attempt.
5. **pair-rail liveness telemetry gap** (boot yellow
   `failopen_rail_liveness_7d`, S278): the check classifies
   `pair_rail_case` / typed labels (`ceo-boot.py:1698-1728`), emitted
   by `check_pair_rail.py` and the dead `codex_invoke.py` path. The
   Stop-event cross-review that actually runs in this repo is
   `codex_review_user_code.py` (wired at `settings.json:590`; NOTE —
   codex r1 F1 corrected the original draft: `check_codex_stop_review.
   py` is the direction-INVERTED rail for the CODEX harness, registered
   only in `templates/codex/hooks.json`, never wired here), and it
   emits only a generic `codex_review_invoked` (`codex_review_user_
   code.py:228`) that the liveness check cannot classify. The rail
   demonstrably works (Stop-hook cross-review returned CLEAN on real
   diffs this week) yet boot reports "no signal in 168h". The signal,
   not the rail, is broken.
6. **verify-counts blind spot** ([[feedback-adr-count-drift-unwatched-docs]],
   S275): `.claude/scripts/local/verify-counts.sh` still does not cover
   `ARCHITECTURE.md`, `GUIA-COMPLETO.md`, `FAQ.md`, or the npm README —
   and those docs are ALREADY stale again (codex r1 F8: e.g.
   `docs/ARCHITECTURE.md:47-51,63-71`, `docs/FAQ.md:100-108`,
   `npm/README.md:44-60,115-123`, `docs/GUIA-COMPLETO.md:74-87` —
   the PLAN-160 ADR bump 178→180 updated only the watched surfaces;
   the verifier's own expected-count comments are stale too,
   `verify-counts.sh:29-40`).
7. **Housekeeping:** `HANDOFF-S277-PLAN160.md` (repo root, tracked) is
   consumed — PLAN-160 landed and flipped `done` (`da1397e`).

## Goal

All seven pending threads closed in one sweep: startup lint silent on
fresh installs and here, upgrade.sh dry-run-safe and exclusion-correct
with regression tests, a clean 3-lane council run recorded (closing
PLAN-156-FOLLOWUP), perf-gate retry surviving sustained-load windows,
pair-rail liveness green after a real post-land review round,
verify-counts covering the drift-prone docs (with the docs corrected),
and the stale handoff archived.

## Approach

Group by gating cost, not by topic — but honestly (debate CF-1
corrected the original taxonomy): almost everything here is
canonical-guarded, so W1 holds only the genuinely unguarded work (new
tests, `verify-counts.sh` + doc corrections, `git rm`), and ONE
sentinel ceremony (W2) batches every guarded surface, with per-concern
commit segmentation + a drop-out protocol (CF-8) so one red oracle
cannot stall the rest. Alternative considered and rejected: one plan
per thread — each would pay its own debate + ceremony boot for <1
session of work; the touch sets don't conflict.

Contract changes are named up front (nothing is silent): C2 records a
narrow grok transport exception in ADR-114 (redaction-before-egress
unchanged; the one-pipe prose in council-audit.js is updated — codex
r1 F10), C4 amends ADR-163 in-place (attempt cadence), U3 amends
ADR-155 in-place (first hash-gated, opt-in auto-delete on the
installer surface), C1 amends ADR-158 in-place (7-entry baseline text
loses the Write twins). All four amendments are IN-PLACE edits of
existing ADRs — the ADR file count stays 180 (no derived-surface count
cascade; `verify-counts` still runs at closeout as belt-and-
suspenders).

**W2 sentinel scope (pre-declared, CF-5 — mid-ceremony additions are
the drift the touched−scope=∅ rail exists to block):**

| # | File | Concern | Kernel? |
|---|---|---|---|
| 1 | `.claude/settings.json` | C1 | **KERNEL** |
| 2 | `.claude/hooks/check_harness_config.py` | C1 | no |
| 3 | `templates/settings/settings.base.json` | C1 | no |
| 4 | `.claude/hooks/tests/fixtures/harness-config/settings/*.json` | C1 | no |
| 5 | `scripts/tests/test-install-deny-baseline.sh` | C1 (rides for atomicity) | no |
| 6 | `.claude/adr/ADR-158-harness-config-gate.md` | C1 amend | no |
| 7 | `docs/PERMISSION-MODEL-DESIGN.md` | C1 (rides) | no |
| 8 | `docs/deny-baseline.md` | C1 (rides) | no |
| 9 | `scripts/upgrade.sh` | U1/U2/U3 | no |
| 10 | `scripts/install.sh` | U2 | no |
| 11 | `scripts/_framework_manifest_set.sh` | U2 | no |
| 12 | `.claude/adr/ADR-155-install-baseline-manifest.md` | U3 amend | no |
| 13 | `.claude/workflows/council-audit.js` | C2/C3 | no |
| 14 | `.claude/commands/council.md` | C2 doc (+F12 fix) | no |
| 15 | `scripts/tests/test-council-fixture.mjs` | C2 (one-pipe asserts) | no |
| 16 | `.claude/scripts/tests/test_council_verify_semantics.py` | C2 (one-pipe asserts) | no |
| 17 | `.claude/adr/ADR-114-codex-egress-redaction-symmetry.md` | C2 amend | no |
| 18 | `.github/workflows/validate.yml` | C4 | **KERNEL** |
| 19 | `.claude/adr/ADR-163-hook-latency-gate-percentile-stability.md` | C4 amend | no |
| 20 | `.github/workflows/smoke-install.yml` | CI wiring (L2 e2e) | no |
| 21 | `.claude/hooks/codex_review_user_code.py` | C5 producer | no |
| 22 | `.claude/scripts/ceo-boot.py` | C5 classifier | no |
| 23 | `.claude/hooks/_lib/audit_emit.py` | C5 action registry | **KERNEL** (codex r1 F2: `check_arbitration_kernel.py:90`) |
| 24 | `SPEC/v1/audit-log.schema.md` | C5 schema registration | SPEC (deny-Edit; apply via Bash under sentinel) |
| 25 | `.claude/hooks/tests/test_audit_emit_api_contract.py` | C5 (319-action pin + API protocol, `:685,:700`) | no |
| 26 | `.claude/hooks/tests/test_w5_scrub_enforcement.py` | C5 (count pin `:74`) | no |
| 27 | `.claude/hooks/tests/test_git_bypass_guard.py` | C5 (count pin `:883`) | no |
| 28 | `.claude/hooks/tests/test_codex_egress_proof_telemetry.py` | C5 (count pin `:109`) | no |
| 29 | `.claude/data/audit-registry.golden.txt` (regenerated same-commit via `check-audit-registry-coverage.py:109,858`) | C5 | no |
| 30 | `templates/grok/sandbox.toml.example` | C2 (documents the old `grok -p "<brief>"` transport, `:21`) | no |
| 31 | `SPEC/v1/install-cli.md` | U3 (`--purge-misinstalled` is public CLI API, `:8-10,107-115` — codex r3 F1) | SPEC (deny-Edit; apply via Bash under sentinel) |
| 32 | `.claude/hooks/check_pair_rail.py` | C5 (`pair_rail_review_expected` producer — codex r3 F2) | no |
| 33 | `.claude/hooks/tests/test_codex_review_user_code.py` (new/extended) | C5 producer tests | no |
| 34 | `.claude/scripts/tests/test_ceo_boot_liveness.py` (new/extended) | C5 classifier tests | no |

Three KERNEL segments (settings.json, validate.yml, audit_emit.py),
each its own commit under `CEO_KERNEL_OVERRIDE=<slug>` + `_ACK`.
The ceremony record MUST name the guard-class concentration (deny
baseline + installer + egress path + CI gate + audit schema) so the
Owner signs the breadth knowingly (CF-5/R-9).
`scripts/_grok_harness.sh` is DELIBERATELY absent: installer-emission
surface; C2 keeps all egress composition inside guarded surfaces
(CF-4). Residual + revisit trigger: if egress logic ever lands there,
that is the F3 class — guard-enroll first (kernel override).
`check_codex_stop_review.py` is DELIBERATELY absent (codex r1 F1): it
is the Codex-harness inverted rail, not wired in this repo; its
liveness story belongs to the codex-harness surface, out of scope.

## Waves

### Wave 0 — debate + ratification
Check: none (ceremony gate)
- [x] Debate L3 (`/debate start PLAN-161`) — round 1 DONE 2026-07-21:
  3× ADJUST → consensus PROCEED, 12 adjustments applied
  (`PLAN-161/debate/round-1/consensus.md`); one VETO-flagged item
  escalated as OQ5.
- [x] Codex pair-rail round 1 (2026-07-21): REJECT, 12 findings (8 P1,
  4 P2) — 11 confirmed and applied in this revision (F1 producer
  correction, F2 kernel marking, F3 C1 surface completion, F4 third
  writer, F5 one-pipe tests, F6 portable watchdog, F7 C4 math+
  acceptance reconciliation, F8 stale-doc correction into V1, F9
  umask+attestation, F11 L5 mechanism, F12 council.md claim); F10
  confirmed in substance (one-pipe is workflow prose, not ADR-114
  text — ADR-114 contains zero "pipe" mentions) though its filename
  citation was wrong.
- [x] Codex pair-rail round 2 (2026-07-21): REJECT, 9 findings (7 P1,
  2 P2) — ALL applied: F1 C5 registration cascade completed (golden +
  four 319-action count pins in scope, rows 25-29); F2 strict bounded
  verdict parser + (diff-hash, outcome) telemetry dedupe; F3
  sub-rails SPLIT (`stop_review` new row; `pair_rail` row kept for
  check_pair_rail + made activity-conditioned) + L4 asserts window
  counts; F4 composed EXIT trap (upgrade.sh:431 restoration
  preserved) + --pin restoration tests; F5 proof-retry-matrix.sh for
  the extended truth table, cited by the ADR amend; F6
  sandbox.toml.example transport update (row 30); F7 four-entry-floor
  success criterion; F8 watchdog spec corrected (install.sh probes
  then runs bare — precedent for the probe only); F9 dropped the
  nonexistent "trusted-caller allowlist" claim (typed closed schema
  is the protection). Round 2 also confirmed r1 F2/F5/F7-F12
  resolved, the scope-table arithmetic, and the C4 inequality.
- [x] Codex pair-rail round 3 (2026-07-21): REJECT, 7 findings (5 P1,
  2 P2) — ALL applied: F1 `SPEC/v1/install-cli.md` in scope (row 31,
  `--purge-misinstalled` is public CLI API); F2 durable activity
  signal = `pair_rail_review_expected` from `check_pair_rail.py`
  (row 32) + session id passed explicitly + count pins now 319→321
  (two new actions); F3 `detected_only` outcome added
  (unclassified-neutral in the classifier — never green, never
  failopen); F4 contention verdict pinned (parse floor JSON, p50 ≤
  200ms uncontended, exit-code alone invalid, malformed → contended);
  F5 exact paths (golden = `.claude/data/audit-registry.golden.txt`;
  producer/classifier test files predeclared, rows 33-34); F6 stale
  "24-row" count removed; F7 W3 check made conditional on the
  recorded OQ3 decision. Round 3 confirmed r2 F4/F6-F9 substantively
  present.
- [x] Codex pair-rail round 4 (2026-07-21): REJECT, 4 findings (3 P1,
  1 P2) — ALL applied: F1 session-id threading into BOTH
  `pair_rail_review_expected` and `pair_rail_case` + per-session
  expected/outcome correlation + cross-session mismatch test; F2 L4
  healthy path pinned (fresh risky diff via Stop hook under
  `CEO_CODEX_USER_REVIEW_AUTO=1` — detect-only default emits neutral
  `detected_only` and can never green the row); F3 OQ3 semantics
  fixed (only an Owner decision ACCEPTING the 2-lane fallback
  satisfies W3; a HOLD leaves L3 and the plan open); F4 proof case
  added (nonzero probe exit overrides below-threshold JSON →
  contended). Round 4 confirmed r3 F1/F3/F5/F6 correct and F4
  behavior-correct.
- [x] Codex pair-rail round 5 (2026-07-21): REJECT, 2 findings (2 P1)
  — ALL applied: F1 L3 gains the accepted-fallback branch (Owner
  ACCEPT of 2-lane → FOLLOWUP `reviewed → executing → done` with the
  acceptance recorded; HOLD keeps everything open); F2 W1 check
  inverted to an expected-failure proof (`!` + REPRO-CONFIRMED
  marker — the new upgrade tests must be RED on HEAD; green runs
  exclusively in the W2 staged oracle). Round 5 confirmed r4
  F1/F2/F4 substantively specified.
- [x] Codex pair-rail round 6 (2026-07-21): REJECT, 1 finding (1 P1)
  — applied: the W1 check now VALIDATES the failure mode executable-y
  (per-test: nonzero exit AND `REPRO-CONFIRMED` present AND
  `SCAFFOLD-ERROR` absent), not just a negated exit code. Round 6
  confirmed both r5 fixes. Further rounds until explicit APPROVE.
- [x] Owner tie-breaks recorded (2026-07-21, S278, structured choice —
  see §Clarifications): OQ5 → (a) remove template twins (VETO lifted);
  OQ1 → purge ratified as proposed.
- [x] Owner ratifies `draft → reviewed`. Pre-authorized 2026-07-21
  (S278) by Owner chat directive ("abre o plano, debate, codex etc… e
  deixa pronto pra ser executado ai resolvemos tudo de uma vez");
  flipped 2026-07-21 after codex round 7 APPROVE (pair-rail
  transcripts archived at `PLAN-161/pair-rail/round-{1..7}.md`).

### Wave 1 — ungated work only (CF-1)
Check: expected-failure proof (codex r5 F2 + r6 F1) — the new upgrade
tests are EXPECTED-RED against HEAD and the check validates the
failure MODE, not just the exit code; their green run belongs
exclusively to the W2 staged oracle:

```bash
for t in test-upgrade-dryrun-identity test-upgrade-exclusions; do
  out="$(bash "scripts/tests/$t.sh" 2>&1)"; rc=$?
  [ "$rc" -ne 0 ] || { echo "FAIL: $t unexpectedly green on HEAD"; exit 1; }
  printf '%s' "$out" | grep -q 'REPRO-CONFIRMED' \
    || { echo "FAIL: $t red without REPRO-CONFIRMED"; exit 1; }
  printf '%s' "$out" | grep -q 'SCAFFOLD-ERROR' \
    && { echo "FAIL: $t failed on scaffolding"; exit 1; }
done
python3 -m pytest .claude/scripts/tests/ -q -k "counts" \
  && bash .claude/scripts/local/verify-counts.sh
```

(each test must fail on the SEEDED ASSERTION — nonzero exit AND the
`REPRO-CONFIRMED` marker AND no `SCAFFOLD-ERROR` marker, validated
independently per test; new `.sh` tests named explicitly — pytest
`-k` cannot collect them)
- [ ] **W1a — author the new regression tests** (files under
  `scripts/tests/` are unguarded; they land here, RED against current
  sources where the bug reproduces, and flip green when W2 lands —
  each W2 concern's staged oracle):
  - `test-upgrade-dryrun-identity.sh`: fixture adopter via the real
    installer in `mktemp -d` (pattern:
    `test_install_baseline_manifest.sh:52-75`, bash-3.2-safe,
    `CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0`); oracle =
    FULL TREE LISTING (files+dirs+symlinks) + per-file sha256 before vs
    after `--dry-run` (CF-12), PLUS the semantic assertions (codex r1
    F4): under dry-run the baseline manifest still LOADS (classifier
    verdicts present in the log) and the purge preview still prints —
    byte-identity alone would pass on a dry-run that silently lost
    provenance classification.
  - `test-upgrade-exclusions.sh`: (a) manifest-BEARING and (b)
    manifest-LESS fixture adopters (CF-7 — the legacy `cp -R` branch);
    asserts excluded trees neither installed nor manifest-recorded;
    seeded mis-install purged under `--purge-misinstalled` ONLY
    (hash-gated, backup present); symlink inside an excluded tree →
    warn-and-skip; byte-identical intended-keep file outside provenance
    rails → kept + warned; upgrade run TWICE → second run purge no-op,
    no new backup content.
  - C2 fixture (staged, exercised via W2 dry-run): artifact bytes ==
    redactor stdout; argv contains NO repo-derived bytes; induced
    redactor failure → final artifact path DOES NOT EXIST; artifact
    mode 0600 / parent dir 0700 VERIFIED before grok would run (codex
    r1 F9).
  - `PLAN-161/proof-retry-matrix.sh` (codex r2 F5): the C4 extended
    truth-table proof (see C4) — authored here, cited by the ADR-163
    amendment, run in the W2 staged oracle.
- [ ] **V1 — verify-counts coverage + doc correction (codex r1 F8):**
  FIRST derive current counts from disk and correct the stale claims
  in the four newly-governed docs (`docs/ARCHITECTURE.md`,
  `docs/GUIA-COMPLETO.md`, `docs/FAQ.md`, `npm/README.md` — all
  unguarded) AND the verifier's own expected-count comments
  (`verify-counts.sh:29-40`); THEN extend
  `.claude/scripts/local/verify-counts.sh` to scan those docs,
  including markdown-table cells where number and label sit in
  separate cells (the S275 miss class). Tolerance stays 0. Test seeds
  a drift in a table cell and asserts it is caught. Ordering matters:
  enabling tolerance-0 scanning before correcting the docs reds the
  oracle instantly.
- [ ] **H1 — housekeeping:** `git rm HANDOFF-S277-PLAN160.md` (content
  preserved in git history + PLAN-160 §How-to-continue).

### Wave 2 — canonical batch (ONE sentinel ceremony, scope table above)
Check: `land-plan161.sh --dry-run` green (runs the W1a oracles in
STAGED mode + full named test set); touched ⊆ sentinel scope; per-
concern commit segmentation; drop-out protocol armed (CF-8: a concern
whose staged oracle is red at ceremony time is DROPPED — touched ⊆
scope stays legal — and deferred, never stalls the batch)
- [ ] **C1 — deny-rule removal (one atomic commit + riders — CF-11 +
  codex r1 F3):** remove the 3 `Write(...)` entries from live
  `.claude/settings.json` `permissions.deny` (KERNEL segment) + the
  `check_harness_config.py:116-124` DENY_BASELINE floor + the
  harness-config fixtures + `test-install-deny-baseline.sh:173-179`
  expectations (asserts `Write(PROTOCOL.md)` at `deny[2]`) +
  `templates/settings/settings.base.json:592/594/596` (OQ5(a),
  Owner-ratified). Riders in the same commit: ADR-158 in-place amend
  (`:103-112` normative 7-entry baseline), `docs/PERMISSION-MODEL-
  DESIGN.md:290-301`, `docs/deny-baseline.md:95-104`, the
  `_deny_baseline_comment` "Entries 8-27" index references
  (`settings.json:726`, shift by 3), and BOTH stale anchors in
  `check_harness_config.py` (`:37-40` and `:114-115`). `Edit(X)`
  twins stay everywhere (they carry the protection). Floor ⊆ every
  scanned settings file must hold at every commit boundary.
- [ ] **U1 — upgrade.sh dry-run guard (CF-12 + codex r1 F4 + r2 F4):**
  guard `upgrade_agents_canonical_only` (upgrade.sh:1366-1420) and the
  `$BAK_DIR` mkdir (:567); RELOCATE `_load_baseline_manifest`'s
  sanitized-manifest mktemp (:641-647) to a secure temp dir OUTSIDE
  `$TARGET` — so dry-run creates nothing in the target while manifest
  loading (and provenance classification) keeps working. TRAP
  DISCIPLINE (r2 F4): upgrade.sh already installs an EXIT trap that
  restores the pinned source checkout (`:431`) — a later plain
  `trap … EXIT` would CLOBBER it; use ONE composed cleanup function
  (temp-manifest removal + branch restoration), and W1a adds non-dry
  `--pin` success/failure cases proving the source branch is restored
  either way. Oracle = W1a byte-identity + semantic test.
- [ ] **U2 — exclusion predicate, three points (CF-7):**
  `_framework_path_excluded()` — bash-3.2-safe case-statement predicate
  in `scripts/_framework_manifest_set.sh` (the existing single
  canonical enumeration; no new mechanism, no generated file) —
  applied at: union walk (upgrade.sh:888-891), legacy no-manifest
  `cp -R` branch (upgrade.sh:1046-1058), and
  `_framework_manifest_files` (:129-134). install.sh's structural
  exclusions (`:972-988`, `install_lib_selective:1000-1009`) refactor
  onto the same predicate.
- [ ] **U3 — opt-in hash-gated purge (CF-6; ADR-155 in-place amend;
  OQ1 Owner-ratified):** explicit `--purge-misinstalled` flag (NEVER
  default-on — hash reads provenance, not intent). Nomination =
  hardcoded walk of the excluded trees only (the manifest cannot
  nominate), lstat/no-follow, regular files only, relpaths through
  `_baseline_relpath_unsafe` (upgrade.sh:607-637 — reuse).
  Authorization = hash match against current framework-source bytes
  OR the target manifest-recorded baseline hash (cross-version
  provenance); neither → keep + warn. Always backup first
  (symlink-preserving). Second-run no-op. Default run (no flag)
  prints the would-purge list + the flag hint. The flag is PUBLIC CLI
  API (r3 F1): document it in `SPEC/v1/install-cli.md` (`:8-10`
  declares every flag public; upgrade flag table `:107-115`) — opt-in
  default, preview behavior, hash authorization, backup semantics,
  exit behavior — applied via Bash under the sentinel (SPEC deny-Edit).
- [ ] **C2 — grok-lane composition (CF-3; ADR-114 amend as a NARROW
  TRANSPORT EXCEPTION — codex r1 F10: ADR-114's redaction-before-
  egress mandate is unchanged; the one-pipe prose lives in
  council-audit.js:16-22,160-168 and is updated there):** in
  `council-audit.js` (composition stays shell-side; the KERNEL
  redactor is untouched): `umask 077` subshell (codex r1 F9),
  redactor writes `brief.tmp` inside a fresh `mkdtemp` 0700 dir under
  scratch (never the repo tree, never bare /tmp), mode verified 0600,
  rename-into-place `&&`-chained → the final artifact path EXISTS
  ONLY IF the redactor exited 0 (structural fail-closed — redactor
  verified fail-closed, `codex_egress_redact.py:293-312`). grok argv =
  FIXED non-repo-derived pointer instruction referencing the artifact
  (the `council` sandbox profile already reads everywhere — no
  widening); `$(cat …)` argv-content FORBIDDEN (ps visibility,
  ARG_MAX, trailing-newline). trap-EXIT cleanup + start-of-run
  stale-artifact sweep; SIGKILL/budget-kill residue (post-redaction
  bytes only) named as accepted residual in the ADR. Run report
  attests sent bytes: artifact sha256 captured at hand-off into a NEW
  lane-schema attestation field (council-audit.js:109-118 — codex r1
  F9; post-run bytes are not evidence, sandbox allows temp writes).
  UPDATE the one-pipe assertions in `test-council-fixture.mjs:280-300`
  and `test_council_verify_semantics.py:177-197` to the new
  vendor-specific invariants (codex-lane keeps stdin pipe; grok-lane
  asserts artifact transport) — both files in scope, both run in the
  staged oracle (codex r1 F5). Fix the false `council.md:52-59` claim
  (scope does NOT default to `.` — the workflow rejects empty scope,
  council-audit.js:61-68; fixture-mode-only fallback :70-71) while
  updating the lane table (codex r1 F12). Update
  `templates/grok/sandbox.toml.example:21` — it still documents the
  forbidden `grok -p "<brief>"` transport in the operator template
  the installer ships (`_grok_harness.sh:167` emits it; the harness
  itself stays untouched) — to the fixed-pointer artifact transport +
  residual guidance (codex r2 F6).
- [ ] **C3 — codex lane budget:** scope-aware wall-clock bound wired
  MECHANICALLY into the lane pipeline via a PORTABLE watchdog: probe
  `timeout` → `gtimeout` (the install.sh:1125 probe — which then runs
  BARE because its python callee is internally bounded, so it is a
  precedent for the probe only, NOT a fallback pattern — codex r2
  F8); when neither exists (macOS default), a fully-specified stdlib
  watchdog: process-group spawn, SIGTERM→grace→SIGKILL, DISTINCT
  timeout exit status, missing-python3 → lane `unavailable`
  (fail-loud). All three branches tested, including
  no-GNU-timeout. Never only the prose number at `:169`.
  Scope size measured from the RESOLVED file/byte count of the scope
  argument, not the brief string length (scope `"."` is 1 char for the
  whole repo — codex r1 F6). Bounded growth with a HARD upper cap
  (the budget is a cost-DoS control). Fail-loud timeout semantics
  unchanged.
- [ ] **C4 — perf-gate retry (CF-2; ADR-163 in-place amend + KERNEL
  validate.yml hunk; math + acceptance reconciled per codex r1 F7):**
  design = 2 attempts (420s cap each = 840s) + inter-attempt backoff
  B=60s + a 3rd attempt GATED on a contention pre-probe
  (`profile-opus-4-7.py --floor`, capped at 30s wall-clock — the floor
  run gets an explicit timeout, it has none today) + second backoff
  B=60s. Worst-case inequality PINNED in the ADR amendment:
  3×420 + 2×60 + 2×30 + setup/smoke/floor headroom (measured ≈180s) ≈
  1620s ≈ 27min → `timeout-minutes: 28` in the SAME kernel hunk.
  **Contention verdict pinned (r3 F4):** the probe PARSES the floor's
  JSON report and applies the numeric threshold — uncontended ⇔
  subprocess-startup p50 ≤ 200ms (the existing gate threshold,
  `validate.yml:1290-1304`); exit-code alone is NOT a signal
  (`profile-opus-4-7.py:812-816` exits 0 whenever metrics are
  produced); malformed report / probe timeout / nonzero exit →
  treated as CONTENDED (fail-safe). The proof matrix exercises the
  real parser at below/equal/above-threshold boundaries.
  Probe still-contended → NO 3rd attempt: fail fast with a DISTINCT
  `::error` ("still-contended VM — infrastructure, re-run when quiet"
  vs "regression"). ACCEPTANCE (reconciled): the gate must never
  require a manual re-run for a failure the probe deems UNCONTENDED;
  a still-contended fail-fast is an ACCEPTED, distinctly-labeled
  infrastructure outcome (rare by construction — the probe ran after
  ≥900s of elapsed job time). N=200 percentile semantics untouched.
  **Executable proof (r2 F5):** the amended ADR-163 must cite a NEW
  proof script (`PLAN-161/proof-retry-matrix.sh`, authored in W1a —
  plan subdirs are ungated) covering the extended truth table:
  pass-on-1, pass-on-2, contended-probe→NO-3rd-attempt,
  uncontended-pass-on-3, uncontended-fail-on-3, malformed/timeout
  probe → treated as contended (fail-safe), nonzero probe exit WITH a
  valid below-threshold report → contended (exit status overrides
  apparently-uncontended JSON — r4 F4), caps/backoffs exercised
  WITHOUT real sleeps (env-faked) — the PLAN-159 matrix
  (`wave1-wrapper-matrix-proof.sh:106`) covers only the 2-attempt
  cases and goes stale. Step-summary markers stay backward-compatible
  for the 2-attempt paths (the historical PLAN-159
  `wave2-regression-proof.sh:134` greps "FAILED on BOTH"); new
  3rd-attempt markers are ADDITIVE.
- [ ] **C5 — pair-rail liveness emit (CF-9; producer corrected per
  codex r1 F1; semantics + cascade completed per codex r2 F1-F3/F9):**
  producer = `codex_review_user_code.py` (the Stop hook actually
  wired in this repo, `settings.json:590`). Emit a NEW registered
  typed action — NOT `pair_rail_codex_unavailable` (would pollute the
  dispatcher's Codex-outage predicate, `disable_predicate_eval.py:
  81-89,283-309`): `codex_review_verdict`, closed-enum `outcome` ∈
  {clean, findings, skipped_failopen, detected_only}, fields
  deny-by-default scrub + closed enum + diff hash only (no content;
  NOTE r2 F9: there is no "trusted-caller allowlist" primitive —
  `_EMIT_GENERIC_PASSTHROUGH` is an action partition,
  `audit_emit.py:1594` — the protection is the typed emitter's closed
  schema, claim nothing more).
  **Producer semantics (r2 F2 + r3 F3):** the hook today accepts ANY
  nonempty stdout as a verdict (`codex_review_user_code.py:106,222`)
  — add a STRICT BOUNDED verdict parser; malformed/unparseable
  output → `skipped_failopen`, NEVER healthy; healthy-class ({clean,
  findings}) only from a parsed verdict on a risky diff; the hook's
  infra fail-open branch (timeout/nonzero/stderr-only) →
  `skipped_failopen`; DETECT-ONLY default mode (`:201-211` — risky
  diff detected, review NUDGED but not run) → `detected_only` (it is
  neither a verdict nor an infra failure — r3 F3); the no-risky-diff
  no-op emits NOTHING. Session id passed explicitly to the emitter
  (the typed default is empty, `audit_emit.py:9628-9629` — r3 F2).
  Telemetry dedupe is SEPARATE from review-status dedupe: key =
  (diff-hash, outcome), one event per distinct pair, so Stop-retry
  loops re-review without re-emitting (`:212`).
  **Activity signal (r3 F2 + r4 F1):** the `pair_rail` row's
  activity-conditioning needs a DURABLE, session-correlated
  denominator — today check_pair_rail's non-review breadcrumbs reach
  only a test sink/stderr (`check_pair_rail.py:725-749`) and the
  durable `pair_rail_case` fires only after a classified outcome
  (`:1491-1504`), DISCARDING the hook payload's session id
  (`:1133-1165,1493-1504`; typed default empty,
  `audit_emit.py:9628-9629`). Add a second registered action
  `pair_rail_review_expected`, emitted by `check_pair_rail.py` when
  the review path is ENTERED (before any outcome; sentinel-bypass and
  out-of-scope calls excluded), AND thread `event["session_id"]`
  explicitly into BOTH `pair_rail_review_expected` and
  `pair_rail_case`. The classifier correlates expected/outcome counts
  PER nonempty session id — a healthy outcome from session B must
  never mask an expected-but-missing outcome from session A. Tests
  cover activity-without-outcome → escalation AND the cross-session
  mismatch case.
  **Registration cascade (r2 F1), same commit:**
  SPEC/v1/audit-log.schema.md + `audit_emit.py` typed emitters (KERNEL
  segment) + `.claude/data/audit-registry.golden.txt` regenerated
  (`check-audit-registry-coverage.py:109,858`) + the 319→321
  action-count pins — TWO new actions (`codex_review_verdict`,
  `pair_rail_review_expected`) — in
  (`test_audit_emit_api_contract.py:685,700`,
  `test_w5_scrub_enforcement.py:74`, `test_git_bypass_guard.py:883`,
  `test_codex_egress_proof_telemetry.py:109`) + the predeclared
  producer/classifier tests (scope rows 33-34).
  **Classifier (r2 F3 — sub-rails split, NOT merged):** append a
  `stop_review` row to `FAILOPEN_RAIL_CLASSIFIERS` for
  `codex_review_verdict`: {clean, findings} → healthy;
  `skipped_failopen` → failopen; `detected_only` → UNCLASSIFIED-
  NEUTRAL (visible in counts, never green-contributing, never
  failopen — a review that was nudged but never ran is not health,
  and mapping it to failopen would falsify the L4 oracle — r3 F3).
  The existing `pair_rail` row keeps observing `check_pair_rail.py`
  (its purpose, `ceo-boot.py:1653` — merging would let a healthy Stop
  review MASK a silent canonical rail) and becomes
  ACTIVITY-CONDITIONED on `pair_rail_review_expected`: zero expected
  + zero outcomes → green (vacuous-but-true); expected WITHOUT
  outcomes → escalate (the S254 class — today's flat "silence =
  yellow" understates it); outcomes present → today's semantics.
  Noted: the liveness signal is exactly as trustworthy as the review
  path it observes — no new authority.
- [ ] **CI wiring:** L2 e2e upgrade test + `test-install-deny-
  baseline.sh` into `smoke-install.yml` (already path-triggers on
  upgrade.sh; add the new test paths to BOTH filters;
  `timeout-minutes` 5→~8).
- [ ] Ceremony mechanics: `land-plan161.sh` follows `land-plan160.sh`
  (tracked sha256 inputs manifest, `shasum -c` fail-closed preflight,
  behavioral oracle that FAILS unless staged bytes carry C1+C2+U1,
  dry-run restores tree AND index on any exit). THREE kernel segments
  (settings.json, validate.yml, audit_emit.py), each its own commit
  under `CEO_KERNEL_OVERRIDE=<slug>` + `_ACK=I-ACCEPT`. SPEC edit
  applied via Bash under the sentinel (SPEC/** is deny-Edit).

### Wave 3 — live-fire validation (partially Owner-gated)
Check: fresh `claude` session start in this repo prints ZERO
`Permission deny rule` warnings; council run report shows quorum
3-lane + verify_failed=0 OR an explicit Owner decision ACCEPTING the
documented 2-lane fallback (codex r3 F7 + r4 F3 — an OQ3 HOLD
decision does NOT satisfy this check: it leaves L3 open and this
plan cannot close on the council criterion until resolved);
`/ceo-boot` after the first POST-LAND review round shows
`failopen_rail` green
- [ ] **L1 — lint + denial proof:** fresh session start shows none of
  the THREE specific rule warnings (assert on rule names, not "zero
  warnings"); `check_harness_config` gate green on live AND template;
  **positive Write-denial probe (CF-10):** on the pinned CLI, a
  Write-tool attempt against `PROTOCOL.md` with only
  `Edit(PROTOCOL.md)` present is refused BY THE PERMISSION LAYER
  (distinguishable from the hook's `CANONICAL-EDIT-BLOCKED` message) —
  the "Edit covers all editing tools" premise is proven, not assumed.
- [ ] **L2 — upgrade proof:** the W1a e2e suite green locally AND in
  `smoke-install.yml`; includes dry-run byte-identity + semantic
  assertions, both adopter shapes, purge fixture matrix, second-run
  no-op.
- [ ] **L3 — 3-lane council run [OWNER-GATED: egress auth]:** `/council`
  on scope `check_canonical_edit.py` (narrow enough for the codex
  budget; doubles as the PLAN-160 W4 optional clean re-audit). Clean =
  3 lanes AVAILABLE + verify_failed=0. Outcomes (r5 F1):
  (a) CLEAN → flip PLAN-156-FOLLOWUP `reviewed → executing → done`
  (legal path; completed_at + related_commits) — its last open
  criterion is this run. (b) DEGRADED for a NEW reason → record +
  escalate to Owner (OQ3); if the Owner explicitly ACCEPTS the
  documented 2-lane result, that acceptance closes the criterion the
  same way: flip the FOLLOWUP `reviewed → executing → done` with the
  acceptance recorded in its §Clarifications. (c) Owner HOLDS →
  FOLLOWUP stays `reviewed`, L3 stays OPEN, and this plan cannot
  close on the council criterion until resolved.
- [ ] **L4 — liveness proof (timing per CF-9; aggregation per codex
  r2 F3; healthy path pinned per r4 F2):** the W2 ceremony is
  reviewed by the PRE-C5 hook and cannot observe its own landing; the
  signal arrives after the FIRST POST-LAND review of a risky diff.
  The default hook mode is DETECT-ONLY (`settings.json:585-592`,
  `codex_review_user_code.py:201-211`) — it emits `detected_only`,
  which is neutral and can NEVER turn the row green, and a manual
  `codex review --uncommitted` does not traverse the producer. The
  proof therefore explicitly exercises: a FRESH risky diff through
  the Stop hook under `CEO_CODEX_USER_REVIEW_AUTO=1`, producing a
  REAL parsed verdict with a fresh review-state hash and the live
  session id — THEN asserts `/ceo-boot`. Acceptance asserts WINDOW
  COUNTS on the `stop_review` sub-rail, not unconditional
  first-success green: healthy ≥1 AND failopen == 0 in-window → row
  green; any healthy+failopen mixture correctly stays yellow
  (`ceo-boot.py:1779`) and is NOT a C5 failure — it is the check
  working. The `pair_rail` row goes green via its new
  activity-conditioning (no in-session canonical-edit activity →
  vacuously green) — overall check green requires BOTH rows, which
  is reachable in a normal post-land week and asserted as such.
- [ ] **L5 — adopter residual stated (CF-10/UN-1; mechanism corrected
  per codex r1 F11):** existing adopters keep their current
  `permissions.deny` — the settings-merge step is an ADDITIVE jq merge
  of lifecycle hooks that never rewrites `permissions.deny`
  (`upgrade.sh:1232-1248`; the `:1235-1237` skip branch fires only
  when settings.json is MISSING) → they keep the 3 warnings until
  they hand-edit; documented in the upgrade output (one advisory line
  naming the 3 exact rule strings to delete — exact strings, never
  line numbers), NOT auto-rewritten (the deny list is
  adopter-customizable).

### Wave 4 — closeout
Check: Validate workflow green on closeout commit; plan → done
- [ ] CI green under the C4 cadence. Acceptance per C4: no manual
  re-run for probe-uncontended failures; a still-contended fail-fast
  with the distinct label is acceptable.
- [ ] ADR count unchanged at 180 (all four amendments in-place —
  verify with `.claude/scripts/local/verify-counts.sh` +
  `check-claude-md-claims.py`; the S275 lesson says regenerate
  derived surfaces whenever ADR/skill/command surfaces move).
- [ ] Plan → `done` via `executing` (+ completed_at + related_commits).

## Open questions

- **OQ3 — FOLLOWUP closure fallback.** If L3 degrades again for a NEW
  cause: accept a documented 2-lane as sufficient or hold FOLLOWUP at
  `reviewed` for another cycle? CEO default: hold + escalate with the
  new cause named.
- ~~OQ1 — U3 purge ratification~~ **CLOSED 2026-07-21** (Owner
  ratified as proposed — see §Clarifications).
- ~~OQ2 — C2 artifact mechanism~~ **CLOSED by debate CF-3** (mkdtemp
  0700 + 0600 artifact + rename-into-place + fixed pointer argv).
- ~~OQ4 — C4 shape~~ **CLOSED by debate CF-2 + codex r1 F7** (in-place
  ADR-163 amend; probe-gated 3rd attempt + backoff; pinned worst-case
  inequality; timeout 16→28).
- ~~OQ5 — template Write twins~~ **CLOSED 2026-07-21** (Owner chose
  removal; Security VETO lifted via condition (ii) — see
  §Clarifications).

## Clarifications

- 2026-07-21 (S278, Owner via AskUserQuestion structured tie-break):
  **OQ5 → "Remover do template (Recomendado)"** — the Owner explicitly
  accepts the old-CLI residual (on an older CLI a fresh install's
  Write tool retains the `Edit(X)` deny + the canonical-edit hook, but
  loses the redundant zero-runtime-dependency `Write(X)` rail). This
  is Security VETO lift condition (ii), recorded; C1 removes the
  twins from ALL surfaces including the template. **OQ1 → "Ratificar
  como proposto (Recomendado)"** — opt-in `--purge-misinstalled`,
  hash-gated (current-source OR target-manifest baseline), excluded
  trees only, lstat/no-follow, sanitized relpaths, backup always,
  keep+warn otherwise, ADR-155 in-place amendment. First auto-delete
  capability on the installer surface, knowingly granted.
- 2026-07-21 (S278, debate round-1 consensus — accepted residuals +
  deferrals): (a) `scripts/_grok_harness.sh` stays unguarded (CF-4) —
  installer-emission surface, no egress composition; revisit trigger:
  egress logic landing there = F3 class, guard-enroll first. (b) The
  C5 liveness signal is exactly as trustworthy as the review path it
  observes — no new authority, noted not fixed here. (c) Install-time
  minimum-CLI-version check deferred to backlog (Critic-B NTH-2).
  (d) `.claude.bak` retention pruning deferred; one doc sentence
  only. (e) Fleet-wide stranded-adopter tracking out of scope; the
  residual is documented per-surface (L5).
- 2026-07-21 (S278, codex pair-rail r1 triage): F10's filename
  citation (`ADR-114-structured-redactor.md`) does not exist on disk —
  the real file is `ADR-114-codex-egress-redaction-symmetry.md`; the
  finding's SUBSTANCE (no one-pipe invariant in ADR-114 text; zero
  "pipe" mentions — verified) is accepted and applied.

## How to continue

**Status `reviewed`** (S278, 2026-07-21): debate round 1 DONE (3×
ADJUST → PROCEED, 12 adjustments); codex pair-rail ran SEVEN rounds —
r1 REJECT (12 findings) → r2 (9) → r3 (7) → r4 (4) → r5 (2) → r6 (1)
→ **r7 APPROVE** (explicit, zero findings) — every finding applied,
transcripts at `PLAN-161/pair-rail/`; Owner OQ1/OQ5 tie-breaks
recorded; `draft → reviewed` flipped under the Owner's
pre-authorization.
**Execution session (S279+) START HERE:** Wave 1 first (author the
regression tests — they must come up RED on HEAD with
`REPRO-CONFIRMED`, per the W1 check block — plus V1 doc corrections
and H1), then stage Wave 2 behind `land-plan161.sh` (34-file sentinel
scope table above; 3 kernel segments + 2 SPEC surfaces), then request
Owner GPG + egress auth for W2-land/L3 in ONE handoff. L3 closes
PLAN-156-FOLLOWUP; L4 needs one post-land risky-diff review under
`CEO_CODEX_USER_REVIEW_AUTO=1`.

## Success criteria

- [ ] Zero `Permission deny rule` startup warnings here AND on fresh
  install (OQ5(a)); positive Write-denial probe passed;
  `check_harness_config` floor invariant green (live + template);
  ADR-158/docs baseline texts consistent with the post-change
  FOUR-entry floor (codex r2 F7 — "seven-entry" survives only as
  historical text).
- [ ] upgrade.sh: `--dry-run` provably writes nothing in the target
  (full-tree listing + hash oracle) WHILE manifest classification
  still functions (semantic assertions); excluded trees neither
  installed nor manifest-recorded on BOTH manifest-bearing and
  manifest-less adopters; seeded mis-install purged only under
  `--purge-misinstalled` (hash-gated, backed up, symlink-safe,
  second-run no-op). All under regression tests, wired into
  smoke-install.yml.
- [ ] Clean 3-lane council run recorded (or an explicit Owner
  decision ACCEPTING the 2-lane fallback — an OQ3 HOLD leaves this
  criterion OPEN and the plan unclosed, r4 F3) → PLAN-156-FOLLOWUP
  `done`; council one-pipe tests updated to vendor-specific
  invariants and green.
- [ ] `failopen_rail_liveness_7d` green (both sub-rails: `stop_review`
  healthy≥1 ∧ failopen==0 in-window; `pair_rail`
  activity-conditioned) after the first post-land risky-diff review;
  healthy emits impossible without a PARSED verdict on a risky diff
  (strict bounded parser — malformed → `skipped_failopen`; test);
  telemetry dedupe (diff-hash, outcome) proven; dispatcher
  Codex-outage predicate unpolluted (no `pair_rail_codex_unavailable`
  from the Stop hook); audit-registry golden + all four action-count
  pins updated in the same commit.
- [ ] perf-gate: pinned worst-case inequality holds
  (`timeout-minutes: 28`); no manual re-run for probe-uncontended
  failures; still-contended fail-fast distinctly labeled; ADR-163
  amended in-place.
- [ ] verify-counts covers the 4 previously-unwatched docs, the docs
  themselves corrected first, seeded table-cell drift caught (test).
- [ ] ADR count stays 180 (in-place amendments only); Validate green
  on closeout; plan `done` via legal lifecycle.
