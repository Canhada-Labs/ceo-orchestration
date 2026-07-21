---
plan: PLAN-161
round: 1
critic: VP Engineering
verdict: ADJUST
created_at: 2026-07-21
---

# PLAN-161 round-1 critique — VP Engineering

## Verdict

ADJUST

## Summary

The consolidation thesis (group by gating cost, pay the ceremony cascade
once) is the right architecture, and every one of the seven threads is
real — I verified each factual claim against the code and all seven
reproduce (evidence anchored below). But the plan's wave taxonomy is
built on a misclassification: **four of Wave 1's six "ungated" items
touch canonical-guarded files** (`scripts/upgrade.sh` and
`scripts/install.sh` are sentinel-gated at
`check_canonical_edit.py:187-189`; `templates/settings/settings.base.json`
at `:305-306`), so U1, U2, U3, and T1 cannot land without the very
ceremony the wave claims to avoid. Once those move into W2, the sentinel
scope roughly doubles (~9-10 files, two of them KERNEL), and the plan's
single-sentinel batching survives only if it adds what it currently
lacks: a pre-declared complete scope, per-concern commit segmentation,
and a drop-out protocol so the one genuinely novel item (C2) cannot
stall six mechanical fixes. Separately, two of the fixes contradict
recorded ADR invariants the plan never mentions (C4 vs ADR-163's
"EXACTLY 2 attempts"; C2 vs the ADR-114 one-pipe mandate written into
`council-audit.js:160-168`), and one batched file
(`scripts/_grok_harness.sh`) is documented in its own header as *not*
canonical-guarded — so it is either wrongly in the ceremony batch or is
an unclosed guard gap, and the plan must say which.

## Risks

- **R1 — single-ceremony coupling.** C2 is the only concern with new
  code against an external CLI contract (grok 0.2.93 argv semantics) and
  OS-sandbox interaction; batching it with five mechanical fixes means
  its oracle failure stalls everything, and the Owner-run GPG ceremony
  is the most expensive resource in the plan (S277: not rehearsable by
  Claude). Without a drop-out protocol, worst-case latency of the whole
  sweep = latency of C2.
- **R2 — CLI version skew on the deny-rule removal.** The claim "no
  protection is lost" is verified only for CLI versions with the new
  `Edit(path)`-covers-all semantics. The template ships to fresh
  installs running arbitrary CLI versions; on an older CLI that still
  consults `Write(path)`, removing the twins removes a live rail
  (defense-in-depth for the case where `check_canonical_edit.py` is
  itself the failure). Conjecture as to prevalence, but the trade-off is
  real and the plan does not state it.
- **R3 — C2 redesigns a security invariant, not just a bug.** The
  one-pipe shape exists so "a skipped/failed redaction can never yield a
  sendable prompt" (`council-audit.js:20-21`); the file-artifact design
  must reproduce that property structurally, and its oracle has a known
  trap: `$(cat file)` command substitution strips trailing newlines, so
  the "prompt bytes == redactor output bytes" fixture will fail or lie
  unless the argv transform is pinned down. Redacted-brief bytes in argv
  are also `ps`-visible and ARG_MAX-bounded — acceptable for a local
  operator instrument, but it should be said out loud.
- **R4 — U3 is the first auto-delete in the upgrade path.** The walk's
  own doctrine is "removed-from-source files are reported (never
  auto-deleted — destructive removals stay manual)"
  (`scripts/upgrade.sh:880-881`). Hash-gating and backups bound the
  blast radius, but this is a policy reversal in a distribution surface,
  not a bug fix.
- **R5 — budget optimism.** 1-2 sessions for seven threads including a
  Owner GPG ceremony, an Owner-gated egress run, and a live-fire
  end-to-end upgrade proof is the happy path. The drop-out protocol (R1)
  is also the budget hedge.

## Must-fix

- **MF-1 — Wave 1 misclassifies U1-U3 as ungated.** `scripts/upgrade.sh`
  and `scripts/install.sh` are canonical-guarded
  (`check_canonical_edit.py:187-189` lists both by exact path), so every
  U1/U2/U3 edit is sentinel-gated. Wave 1 as written cannot land its
  main content. Restructure: W1 = author + test in staged form (V1, H1,
  and fixture updates are the only truly ungated landings — V1's
  `.claude/scripts/local/verify-counts.sh` is not in the guard list;
  H1's `git rm` is not an Edit); U1-U3 land inside the W2 ceremony.
  This is the load-bearing fix — the plan's "group by gating cost"
  sorting is currently wrong about its own biggest work item.
- **MF-2 — T1 cannot be W1 either, and is commit-coupled to C1.**
  `templates/settings/settings.base.json` is itself canonical-guarded
  (`check_canonical_edit.py:305-306`) AND scanned by the harness gate —
  `DEFAULT_SETTINGS_REL` includes the template
  (`check_harness_config.py:169-172`), and the DENY_BASELINE floor
  applies to every scanned settings file (`:111-116`). Dropping
  `Write(...)` from the template while the floor still lists them turns
  the gate RED. The plan hedges with "execution decides the split"; the
  evidence is decidable now: T1 lands in W2, same commit as C1, same
  commit as the floor change. Remove the hedge.
- **MF-3 — C4 contradicts a recorded ADR invariant.** validate.yml
  carries "Retry contract (ADR-163 invariant — EXACTLY 2 attempts, never
  more, never unbounded)" (`.github/workflows/validate.yml:1222-1223`;
  `.claude/adr/ADR-163-hook-latency-gate-percentile-stability.md`
  exists). A bounded 3rd attempt is a change to that invariant, so the
  plan's claim "PLAN-159/ADR-163 untouched; only retry cadence changes"
  is wrong — the retry cadence IS the ADR-163 invariant. Amend ADR-163
  in-place inside the ceremony (in-place AMEND avoids an ADR
  file-count ripple through verify-counts/CLAUDE.md claims) and
  pre-declare the ADR path in the sentinel scope.
- **MF-4 — C2 amends ADR-114 semantics and must say so.** The lane
  prompt currently mandates the exact shape C2 abolishes: "Run EXACTLY
  this pipeline shape (never a two-step redact-to-variable-then-send,
  and never the unredacted $BRIEF as a CLI argument...)"
  (`.claude/workflows/council-audit.js:160-168`). Replacing one-pipe
  with redact-to-0600-artifact-then-argv is an ADR-114 amendment
  (`.claude/adr/ADR-114-codex-egress-redaction-symmetry.md`), not a
  code-local fix. Also constrain the design: the redactor
  (`codex_egress_redact.py`) is KERNEL
  (`check_arbitration_kernel.py:132`) — do the composition shell-side
  (`redactor > artifact`) so the kernel file stays untouched, or accept
  and pre-declare a kernel hunk.
- **MF-5 — resolve `scripts/_grok_harness.sh`'s guard status
  explicitly.** It appears in neither the canonical list nor
  `_KERNEL_PATHS` (grep both hooks: no match), and its own header says
  "NEW unguarded companion... not canonical-guarded"
  (`scripts/_grok_harness.sh:13-15`). So either (a) it does not belong
  in the "guarded files" ceremony batch (it is the *installer emission*
  surface, not the live council egress path — the arg-contract fix
  plausibly lives in `council-audit.js` + templates, not here), or
  (b) if C2 gives it egress-composition logic, it becomes exactly the
  F3 class ("a file we choose not to ship is exactly the file an
  attacker would CREATE", `check_canonical_edit.py:321-328`) and must be
  guard-enrolled — which is a KERNEL-HARD-DENY list extension needing
  its own `CEO_KERNEL_OVERRIDE` slug. The plan must pick one.
- **MF-6 — pre-declare the complete sentinel scope; the kernel question
  is decidable now.** D2 says "if any file is `_KERNEL_PATHS`" — it is
  not an if: `.claude/settings.json` (`check_arbitration_kernel.py:125`)
  and `.github/workflows/validate.yml` (`:135`) are kernel; the other
  batched files are canonical-only (`check_harness_config.py` and
  `check_codex_stop_review.py` via the `.claude/hooks/*.py` glob at
  `check_canonical_edit.py:137`; `council-audit.js` via
  `.claude/workflows/**/*.js` at `:329`). With MF-1/MF-2 the scope is
  ~9-10 files plus 1-2 ADR paths and possibly
  `.claude/commands/council.md` (`:330` — its lane table at
  `council.md:36-37` documents the egress mechanics C2 changes).
  Enumerate all of it in the plan before the sentinel is signed:
  mid-ceremony scope additions are precisely the drift the
  touched−scope=∅ rail exists to block.
- **MF-7 — mandate per-concern commit segmentation + a drop-out
  protocol.** The plan segments only kernel hunks. Require every concern
  (C1..C5, U1-U3, T1) to land as its own commit under the single
  sentinel — that is what actually preserves bisectability and
  per-concern revert, which is the real rollback/attribution answer for
  D1. And pre-agree: if one concern's staged oracle is red at ceremony
  time (most likely C2), it is dropped from the batch (touched ⊆ scope
  stays legal) and deferred to a follow-up ceremony rather than stalling
  the rest.
- **MF-8 — record the U3 doctrine change as an ADR-155 amendment.** The
  never-auto-delete rule is codified in the ADR-155 implementation
  (`scripts/upgrade.sh:880-881`); OQ1 chat ratification is necessary but
  not a durable record for reversing it. One paragraph amendment in
  `.claude/adr/ADR-155-install-baseline-manifest.md`, inside the
  ceremony (ADR files are canonical, `check_canonical_edit.py:176`).

## Nice-to-have

- **NTH-1 — state the CLI-version floor for item 1.** Name the minimum
  CLI version whose semantics make the `Write(...)` twins redundant, and
  the residual: adopters below that floor lose a redundant rail on fresh
  install. Also decide (and write down) the fate of *existing* adopters:
  upgrade.sh EXISTS-SKIPs settings.json (`scripts/upgrade.sh:1235-1237`),
  so they keep printing the warnings after this sweep — deliberate
  deferral is fine, silence is not.
- **NTH-2 — fix L4's timing assumption.** "W2's own landing provides
  it" is wrong: the Stop-hook round that reviews W2 runs the PRE-C5 hook
  (the staged emission code is not yet the installed hook). Liveness
  green arrives after the first post-land round. Reword the acceptance
  to "after the first post-land review round" so a red boot immediately
  after W2 is not misread as a C5 failure.
- **NTH-3 — correct the item-2 causal story.** The re-add after adopter
  deletion is driven by the union walk's ADD branch ("New framework
  file: absent at dst. Just install it.",
  `scripts/upgrade.sh:904-908`), not by the manifest recording; the
  manifest is a downstream consumer. Point the U2 regression at the
  walk, and note that install.sh's exclusion knowledge is *structural*
  (selective copy convention `scripts/install.sh:972-988` + the
  case-skip in `install_lib_selective` at `:1000-1009`), not a list —
  U2's "single-source the list" is really "derive a list from code
  structure, then refactor three consumers onto it"; scope it honestly.
- **NTH-4 — U1's byte-identity oracle must include backup dirs.** The
  canonical-5 step writes `$BAK_DIR` backups and `mkdir -p` on the
  target unconditionally (`scripts/upgrade.sh:1381,1393,1395`); define
  "target tree" in the oracle so backup/scaffold writes under
  `--dry-run` also fail it. The guarded family members are
  `backup_and_replace` (`:983`), `_refresh_protocol_pointer` (`:1106`),
  `_merge_lifecycle_hooks_into_settings` (`:1289`), and the manifest
  rewrite (`:1438`) — `upgrade_agents_canonical_only` is the confirmed
  outlier; the family sweep should enumerate and check all of them.
- **NTH-5 — use precise paths in the scope declaration.** The plan says
  bare "council-audit.js"; the file lives at
  `.claude/workflows/council-audit.js`. In a document whose whole job is
  scoping a sentinel, path precision is not cosmetics.
- **NTH-6 — pin the C2 artifact→argv transport in OQ2.** temp-file vs
  FIFO is only half the question; the other half is path-in-argv (grok
  must then read the file — the `--sandbox council` profile must allow
  that path, and `-p` takes a prompt string, not a file) vs
  content-substitution (`ps` visibility, ARG_MAX, trailing-newline
  stripping). The fixture design in C2(a) depends on which one is
  chosen; decide it in the plan, not mid-execution.

## Unseen

- **U1-U3/T1 are canonical.** The plan's central sorting principle
  (gating cost) was applied without checking the guard lists for its
  own Wave-1 files. (MF-1/MF-2 — listed here because it is the thing
  the plan most completely does not see.)
- **Two ADR invariants are being amended silently.** C4 vs ADR-163's
  exactly-2-attempts; C2 vs ADR-114's one-pipe shape. The plan's own
  §Approach promises "if execution discovers otherwise, that change gets
  an ADR" — both are discoverable at plan time, and the ADR edits change
  the sentinel scope (MF-3/MF-4).
- **The stranded-adopter population.** Existing installs keep both the
  `Write()` warnings (EXISTS-SKIP settings) and — until they run the
  fixed upgrade.sh — the mis-installed test trees. The sweep's success
  criteria measure only this repo + fresh installs + the one live
  fixture; nothing tracks whether the fix actually reaches the adopter
  population that motivated items 1-3.
- **C5's self-referential proof window.** The ceremony that lands the
  liveness emitter is reviewed by the pre-emitter hook (NTH-2) — the
  plan's acceptance chain quietly assumes the new code observes its own
  landing, which it structurally cannot.
- **Stale anchor trivia** (label: minor): DENY_BASELINE's docstring
  cites "lines 644-653" of settings.json
  (`check_harness_config.py:114-115`); the live entries sit at 728-756.
  Harmless today, but C1's edit is the natural moment to fix the
  breadcrumb.

## What I would NOT change

- **The consolidation itself (D1).** One plan, one ceremony is right:
  the cascade cost genuinely dominates, the touch sets do not conflict,
  and per-thread plans would pay 5-7 debate+ceremony boots for <1
  session of work each. The fixes above make the batch safe; they do
  not argue for splitting it.
- **D2's atomicity core** — C1 floor+live (now +template, MF-2) in one
  commit is exactly right; the floor-⊆-live invariant breaking red on a
  partial land is the correct failure mode.
- **D3's trust boundary (OQ1 default).** Hash-gated purge with backup
  and warn-keep reuses the classifier's existing trust model
  (`_classify_against_baseline`, `scripts/upgrade.sh:776-797`) instead
  of inventing a new one. Correct — just record it (MF-8).
- **D4's temp-file default over FIFO** — auditable, inspectable,
  retry-friendly; FIFO's single-read lifecycle under a timeout is
  exactly the kind of cleverness this codebase's history punishes.
- **D5's hold-and-escalate on a NEW degradation cause** — never
  silently accepting a degraded quorum is the council's whole identity
  (`council-audit.js` fail-loud doctrine).
- **The behavioral acceptance criteria throughout** — byte-identity
  dry-run oracle, boot-green-after-a-real-round, seeded-drift-caught:
  all are the "positive control, run as the harness runs" pattern the
  repo's own feedback memory says is the only proof that counts.
- **Reusing the PLAN-160 landing-script pattern** (tracked sha256
  manifest, `shasum -c` preflight, tree+index-restoring dry-run) — it
  is proven, and the ceremony mechanics are not where this plan's risk
  lives.
