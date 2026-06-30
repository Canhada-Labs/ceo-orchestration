# PLAN-143 — Round 1 critique — DevOps & Platform Engineer

> Lens: CI/CD impact, release coupling, verification mechanics, operational
> testability. One of 3 independent critics; I have not seen the others.

## 1. Verdict

**ADJUST**

## 2. Summary

The four items are real, correctly triaged by nightly dimension, and three of
four are CI-neutral (env-inventory regen is not release-gated; the rotation
probe is already fail-open; the tests-floor doc is explicitly `--no-tests` in
CI Governance). The one item with genuine release-coupling blast radius is
**item 3**, and the plan's preferred locus (D2 — extend the `audit_emit.py`
allowlist) materially compounds the pair-rail release-coupling debt that
PLAN-142 deliberately parked behind `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1`. The plan
acknowledges this in prose ("fold into the existing transition window") but does
not give it the sequencing rigor it needs, and several ACs are written as
"a test asserts" without naming the test rail or the assertion mechanics. Adjust
to (a) sequence item 3 explicitly against verdict regeneration, and (b) harden
the verification language on items 1–3.

## 3. Risks

- **R1 (release-coupling, item 3 — the load-bearing risk).** `audit_emit.py` is
  line 22 of `pair-rail-inputs-hash-manifest.txt`. The verdict validator
  (`validate-pair-rail-verdict.py:106 compute_inputs_hash`) computes
  `inputs_hash` as `sha256(canonical_json({ path: git hash-object(path) }))`
  over every manifest entry. Editing `audit_emit.py` (current
  `git hash-object` = `6fc81824…`) changes that file's object hash → changes the
  recomputed `inputs_hash` → **invalidates the declared `inputs_hash` of every
  pre-existing verdict artifact** (`pair-rail-verdict-v1.16.0.md`,
  `…-rc.1.md`). Today this is masked because `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1`
  is set as a GHA variable, so step 15 is `continue-on-error: true` and a
  mismatch is a soft-fail. The risk is **latent**: the day someone flips the
  variable back to `0` (the documented end-of-transition action), the FIRST
  release after this edit hard-fails step 15 unless a fresh verdict bound to the
  post-edit tree was regenerated. This is exactly the coupling PLAN-142 put into
  transition mode; item 3 as written deepens it rather than draining it.
- **R2 (double-touch of the manifest, item 3 alt-locus).** The kernel
  alternative (`check_pair_rail.py`, manifest line 27) is ALSO in the manifest.
  There is no "manifest-free" fix locus for item 3 — both candidate files are
  coupled. So D2's framing ("canonical preferred to avoid a second KERNEL-HARD-
  DENY ceremony; the cost is re-touching the manifest") is half-stated: BOTH
  loci re-touch the manifest. The real trade is canonical-GPG ceremony vs
  kernel-hard-deny ceremony — the inputs_hash invalidation is identical either
  way. The plan should not imply the kernel path avoids the release-coupling.
- **R3 (two-channel emit divergence — unseen by the plan).** There are two emit
  paths. The breadcrumb at `check_pair_rail.py:571` uses
  `emit_generic("codex_invoke_dispatched", exit_code=…)`. The structured helper
  `emit_codex_invoke_dispatched()` (`audit_emit.py:9564`) does not even accept an
  `exit_code` kwarg. Extending only `_CODEX_INVOKE_DISPATCHED_ALLOWLIST`
  (line 9555) fixes the generic path but leaves the structured helper
  asymmetric. A fix that adds the field to the allowlist without reconciling the
  two producers is incomplete and will read as inconsistent to the next auditor.
- **R4 (verify-counts floor brittleness, item 4).** The `tests` rule is a
  *floor* (`grep '(\d+)\+ tests'`). The live count moves every time a test file
  is added/removed. Pinning INSTALL.md to the exact `~11.7k` (one of D-options)
  will re-break `verify-counts.sh` (full) the next time the suite grows or
  shrinks — re-creating this exact nightly RED. The whole point of the floor
  rule (per the script header: "so adding a test never churns the docs — AC6")
  is defeated by an exact number. This is a verification-mechanics trap.
- **R5 (env-inventory regen captures unintended surface — item 1).** `--generate`
  is a blind snapshot: it writes whatever the token scan currently finds, with
  zero gate on whether a name is *intended*. If even one of the 25 NEW names is
  an accidental/typo/dead reference, `--generate` launders it into the
  "reviewed" inventory and the drift signal goes green while the footgun
  persists. The S218 footgun class this instrument exists to catch is precisely
  "an env surface nobody reviewed" — a mechanical regen without the per-name
  review defeats the instrument's purpose.

## 4. Must-fix (blocking)

- **MF1 — Sequence item 3 against verdict regeneration (directly answers OQ3).**
  Add an explicit ordering AC: item 3's canonical edit to `audit_emit.py` MUST
  be followed, in the same plan, by regenerating the pair-rail verdict bound to
  the post-edit tree (new `inputs_hash` over the updated manifest file set)
  BEFORE the next release tag is cut. Do NOT ship item 3 and leave a stale
  verdict relying on `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` to paper over the
  resulting `inputs_hash` mismatch — that converts a transition-mode bridge into
  a permanent crutch. If verdict regeneration cannot happen this plan,
  **item 3 must wait** until it can (see OQ3 answer below). The plan currently
  says "fold into the existing transition window" — that is necessary but not
  sufficient; the window is for *parent_sha* legacy bridging, not for shipping
  fresh inputs_hash drift under cover.
- **MF2 — Name the verification rail + assertion for each test AC.** AC
  `[P1][audit-errors-02]` and `[P2][audit-errors-04]` say "a regression test
  covers…" / "a test asserts…" without specifying WHERE. Per repo convention
  (memory: `_lib/tests/` is canonical-guarded; `hooks/tests/` is not), state the
  target test file and that new tests subclass `TestEnvContext` + use
  `mock.patch.dict` (never `os.environ[...]=`), or the env-hygiene gate rejects
  them. For item 3 specifically, the assertion must verify the emitted event
  RETAINS `exit_code` AND that the `_scrub_ceo_boot_event` drop-counter
  (`audit_emit.py:5854`) no longer logs the forbidden-field warning — assert on
  the survival, not just on "no exception".
- **MF3 — Make the item-2 regression test exercise the real defect, not a
  no-op.** The probe at `spool_writer.py:1729` is ALREADY inside a
  `try/except Exception` fail-open block (lines 1726–1746). That is why the
  AttributeError surfaces as a benign breadcrumb, not a crash. A regression test
  that merely asserts "no exception escapes" will pass even with the bug present
  (the outer try swallows it). The test MUST assert the *positive* contract:
  given a shim object lacking `_rotate_if_needed_safe`, the probe takes the
  intended branch (rotation correctly skipped/handled) AND does NOT emit the
  AttributeError breadcrumb to `audit-log.errors`. Otherwise the AC is
  vacuously satisfiable.
- **MF4 — Item 4: keep the floor a floor.** Reject the "pin to exact ~11.7k"
  option. Set INSTALL.md to a robust floor (e.g. `11000+`) that is currently
  satisfied (live 11752 ≥ 11000) and gives headroom so normal suite churn does
  not re-trigger the nightly RED. Document in the AC that the value is a FLOOR by
  design (cross-reference the verify-counts.sh header rule), so a future editor
  does not "tighten" it back to exact and reintroduce the drift.
- **MF5 — Item 1: gate the regen behind explicit per-name review.** The AC must
  require that each of the 25 NEW names is individually classified
  (intended-surface | dead-ref-to-remove) and that the kill-switch subset
  (`CEO_TRUST_BYPASS`, `CEO_CANONICAL_GUARD_DISABLE`, `CEO_HOOKS_DISABLE`,
  `CEO_SKIP_HOOKS`, `CEO_ALLOW_NO_VERIFY`) is documented at its consumer site
  BEFORE `--generate` runs. The regen is the last step, not the work. As written
  (`status=current` after regen) the AC is satisfiable by a blind snapshot,
  which is the failure mode the instrument exists to prevent.

## 5. Nice-to-have

- **NH1.** Add a post-merge verification step to the regression AC `[P2]`: run
  `env-inventory-check.py --check`, `verify-counts.sh` (full, no `--no-tests`),
  and a targeted re-emit of `codex_invoke_dispatched` locally, then re-run
  `nightly-hygiene` and capture the GREEN. The plan already gestures at this
  ("a follow-up nightly run returns GREEN") — make the three individual
  reproducible commands explicit so the verification is mechanical, not
  narrative.
- **NH2.** For item 3, reconcile the two-channel emit (R3): either route the
  breadcrumb through `emit_codex_invoke_dispatched()` with a new `exit_code`
  param, or leave one producer and document the other as intentionally
  field-narrow. Pick one explicitly so the next auditor does not re-flag the
  asymmetry as a new finding.
- **NH3.** Consider peeling item 4 off (D1) and shipping it as a trivial
  doc-only commit NOW. It is not canonical-guarded, not CI-gated, and has zero
  coupling to items 1–3. Bundling a 1-line doc fix into a canonical-GPG +
  verdict-regen ceremony needlessly widens that commit's blast radius and slows
  the doc fix.
- **NH4.** Record (ADR or plan note) that BOTH item-3 loci re-touch the manifest
  (R2), so the next person choosing a fix locus is not misled by D2's framing
  into thinking the kernel path avoids the inputs_hash coupling.

## 6. Unseen (gaps the plan does not address)

- **U1 — npm/ mirror divergence.** Every coupled file exists twice:
  `.claude/…` AND `npm/.claude/…` (audit_emit.py, check_pair_rail.py,
  env-inventory-check.py, verify-counts.sh, the manifest, env-inventory.json all
  have an `npm/` twin). The plan names only the `.claude/` paths. If the npm
  mirror is shipped/validated independently, fixes applied to one tree and not
  the other create a fresh drift the next sweep (or a packaging step) will flag.
  The plan must state whether the npm mirror is in scope and, if so, that each
  edit is applied to both trees (or that a sync step regenerates the mirror).
- **U2 — verdict TTL interaction.** Step 15 enforces `--max-age-hours 24` on the
  verdict (`generated_at` within 24h, ADR-103). Even if item 3 regenerates the
  verdict (MF1), a verdict authored more than 24h before the eventual GA tag
  will fail the TTL independently of the inputs_hash fix. The plan should note
  that verdict regeneration and the release tag must fall inside the same 24h
  window — otherwise item 3 "fixed" the hash but the tag still can't ship once
  `OPTIONAL` is flipped off.
- **U3 — no rollback/abort path for the canonical ceremony.** Items 2+3 require
  GPG-signed canonical edits to `_lib/spool_writer.py` and `_lib/audit_emit.py`.
  The plan has no stated abort path if the canonical-edit sentinel ceremony
  fails mid-flight (e.g. signer not in both rails per the GPG-cascade memory).
  Note the bail-out: revert the working tree, no partial sentinel left behind.
- **U4 — does flipping OPTIONAL→0 belong to THIS plan?** The plan treats
  `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` as a fixed backdrop. But item 3 is the kind
  of change that should ideally end the transition. The plan does not decide
  whether closing the transition (var→0) is in scope or explicitly deferred. It
  should say one or the other, so the transition-mode debt has an owner and an
  exit, rather than drifting indefinitely.

## 7. What I would NOT change

- The triage-by-nightly-dimension structure and the honest provenance framing
  (items 1-2-4 pre-date PLAN-142; item 3 is a PLAN-142 follow-up made observable
  by the restored rail). This is accurate and well-sourced against the live
  tree.
- The correct identification that item 4 is NOT CI-gated (Governance runs
  `verify-counts.sh --no-tests`) — verified: the `tests` rule is skipped under
  `--no-tests` (`if metric == "tests" and no_tests: continue`). The plan's claim
  is exactly right; do not "harden" this into a CI gate (it would make every
  test add/remove a release blocker — wrong trade).
- The fail-open posture of the item-2 probe. Do NOT convert the rotation probe
  into a hard-failing path "for visibility"; the surrounding fail-open
  `try/except` is correct framework doctrine (CLAUDE.md §4 fail-open on
  infrastructure). The fix is to stop the AttributeError at the source, keeping
  the fail-open envelope intact.
- D2's preference for the canonical locus OVER the kernel locus for item 3 — on
  ceremony-cost grounds that is the lighter path (canonical-GPG < kernel-hard-
  deny). My objection (R2/NH4) is only to the *framing* that it avoids the
  manifest coupling; the locus choice itself is reasonable.

---

### OQ3 — does item 3 compound the release-coupling debt, and should it wait?

**Yes, it compounds it, and it should not ship as a bare allowlist edit while
the transition window is open — it must ship *paired with* verdict
regeneration, or wait.**

Mechanically: `audit_emit.py` is a manifest input (line 22). The verdict's
`inputs_hash` is `sha256` over `git hash-object` of every manifest file. Editing
`audit_emit.py` mutates its object hash → mutates the recomputed `inputs_hash` →
makes every existing verdict's declared `inputs_hash` stale. Right now
`CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` makes step 15 `continue-on-error`, so the
mismatch is invisible. That is the trap: shipping item 3 under the transition
flag does not *resolve* the coupling, it *hides a fresh increment of it* behind
the same flag PLAN-142 set to drain the OLD coupling. When the Owner flips the
flag back to `0` (the transition's whole purpose), the first release after this
edit hard-fails step 15.

So the disposition is conditional, not a flat "wait":
- **If this plan can regenerate the verdict** (recompute `inputs_hash` over the
  post-edit tree, GPG-sign, land it within the 24h TTL of the next tag) → item 3
  may proceed, with MF1 as a hard sequencing AC.
- **If verdict regeneration is out of scope** for this plan → item 3 should
  **wait** until the regeneration (or the OPTIONAL→0 closure) is scheduled,
  because a bare allowlist edit silently grows the very debt the transition flag
  exists to retire. The other three items have no such coupling and should not
  be held hostage to item 3 — split it out (D1) if it must wait.

This is the single most consequential sequencing decision in the plan, and it is
why my overall verdict is ADJUST rather than ACCEPT.

VERDICT: ADJUST
