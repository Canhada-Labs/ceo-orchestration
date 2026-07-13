---
round: 1
archetype: DevOps & Platform Engineer
skill: devops-ci-cd
agent_persona: DevOps & Platform Engineer
generated_at: 2026-07-13T00:00:00Z
---

## Verdict

ADJUST — all 7 findings are real (verified at file:line), direction is
correct, but the plan under-specifies the CI test *placement* and the
single-ceremony *landing mechanics*, and F5's "parity" has a second break
axis the plan does not name. None of these block the design; they block a
green Validate + a working live-fire unless fixed first.

## Summary (≤ 3 bullets)

- Sound: 7 mechanical defects, each anchored; fix-then-live-fire is the
  right shape and a second confirmation of the fixtures-miss-live thesis.
- Weak (my lane): three of the four wave *checks* don't run where the plan
  thinks — the council `.mjs` runs in NO CI job, the F1 smoke lands in a
  dir the 3.9–3.12 matrix skips, and W3's `-k grok` currently selects zero
  tests (pytest exit 5 = spurious wave-gate failure).
- Weak (ceremony): the touch set is MIXED canonical/non-canonical and F3
  edits a KERNEL path — "one sentinel ceremony" as written will trip the
  kernel guard and the `touched−scope=∅` invariant unless the landing
  script carries the kernel override and a reconciled scope.

## Risks

- **R-DO1 — CRITICAL — F2/F7 regression tests have NO CI home.**
  `scripts/tests/test-council-fixture.mjs` (the W2 check) is invoked by
  **no workflow** — the only `setup-node` in `.github/workflows/` is
  `npm-publish.yml` (publish, not test), and `council-audit.js` is
  referenced by zero CI jobs. So "suites green" + "Validate green on
  closeout" can be satisfied while the F2 fail-loud and F7 scope
  assertions are never executed by CI. This is precisely the
  fixture-green-≠-enforced trap the FOLLOWUP exists to close, reintroduced
  one layer up.
  *Mitigation:* wire the `.mjs` into a real workflow (add `actions/setup-node`
  + a `node scripts/tests/test-council-fixture.mjs` step in `validate.yml`),
  OR mirror the F2/F7 assertions as a stdlib-Python test under a matrix dir
  (`.claude/scripts/tests/`). Node-in-CI is a new surface — prefer the
  Python mirror if you want it green this session without a node toolchain
  in the runner image.

- **R-DO2 — HIGH — F1 smoke test placement misses the version matrix.**
  The 3.9–3.12 matrix (`hook-tests-python-matrix`, validate.yml:1279–1310)
  runs exactly `.claude/hooks/tests/ .claude/scripts/tests/
  .claude/scripts/optimizer/tests/`. `.claude/hooks/_lib/tests/` is run
  only by the single-version "v1.0.1 test roots" job (validate.yml:~441–458).
  F1 is literally an "absolute-import safe" CLI entrypoint — the exact
  import/version failure class (a stray PEP 604 `|`, a `match`, a 3.9
  stdlib gap) that ONLY the matrix catches. Placed solely in `_lib/tests/`
  it is not matrix-covered.
  *Mitigation:* add the redactor-CLI smoke to a matrix dir too
  (`.claude/scripts/tests/` or `.claude/hooks/tests/`), or extend the
  matrix dir list to include `.claude/hooks/_lib/tests`.

- **R-DO3 — HIGH — W3 check command self-fails: `-k grok` selects 0 tests.**
  No test in `.claude/scripts/tests/` matches `grok` today (verified: zero
  `*grok*` files there; the only grok tests are
  `.claude/hooks/tests/test_codex_stop_review.py` and the by-name shell
  test `scripts/tests/test-install-harness-grok.sh`). `pytest -k grok`
  with zero selected tests exits **5**, which fails the `&&` chain in the
  Wave-3 check and reads as a red wave gate even when everything passes.
  *Mitigation:* the new F4/F5 tests must exist and be discoverable under
  the named dir before that check runs; drop `-k grok` in favor of naming
  the new test files explicitly, or add `|| [ $? -eq 5 ]` tolerance. Also
  note the F4 subject (`scripts/_grok_harness.sh`) is top-level `scripts/`,
  not `.claude/scripts/` — pin the test path to where it actually collects.

- **R-DO4 — HIGH — single ceremony trips the kernel guard on F3.**
  F3 edits `check_canonical_edit.py`'s `_CANONICAL_GUARDS`
  (check_canonical_edit.py:113–322). That file is in `_KERNEL_PATHS`
  (check_arbitration_kernel.py:79) → HARD-DENY that a GPG sentinel alone
  does NOT satisfy; it needs `CEO_KERNEL_OVERRIDE=<slug>` +
  `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` (check_arbitration_kernel.py:31–32,
  316–323) in the same session. The proposal's "ONE sentinel ceremony
  (land-plan156.sh pattern)" does not mention the kernel half.
  *Mitigation:* the landing script must export the kernel override for the
  F3 edit; assert the override reason-slug is audit-logged. Verify against
  a dry-run before the real land.

- **R-DO5 — MEDIUM — `touched − scope = ∅` breaks on the mixed touch set.**
  Of the 7, F4 (`scripts/_grok_harness.sh`) and the F5 *gate*
  (`templates/grok/pre-push-review-gate.sh`) are **not** canonical (both
  self-declared/absent from `_CANONICAL_GUARDS`; `templates/` is only
  guarded for `templates/settings/*`). The rest (F1, F2/F7, F3,
  F5-recorder `check_codex_stop_review.py`, F6 `_python-hook.sh`) are
  canonical. The landing invariant "verifique touched−scope=∅ ANTES de
  commitar" will flag the two non-canonical files unless the invariant is
  "touched-*canonical* − scope = ∅" or they are over-declared in Scope.
  *Mitigation:* decide the invariant semantics up front; simplest is to
  list all touched files in Scope (over-declaration of non-canonical paths
  is harmless) and document why two of them aren't sentinel-gated.

- **R-DO6 — MEDIUM — F4 fix parses an ASSUMED TOML schema until W4 proves it.**
  The trust probe (`_grok_harness.sh:333`, `grep -qF "$target"`) is a
  substring match over `trusted_folders.toml`; the fix must parse real
  entries. But the real on-disk schema is only produced when
  `grok --trust` runs (W4). Writing the parser against an assumed shape
  and landing it in W3 risks a false-NOT-ARMED if grok 0.2.93 writes a
  different structure — same "characterize before you pin" discipline the
  version/SHA pin already enforces (ADR-162).
  *Mitigation:* capture a real `trusted_folders.toml` (from `grok --trust`
  on the pinned binary) as a test fixture BEFORE writing the F4 parser, or
  sequence F4 after that capture.

- **R-DO7 — MEDIUM — F6 field-parse in a bash shim needs a fail-open JSON read.**
  The exit-2 map (`_python-hook.sh:463–464`) is bash; parsing "the decision
  FIELD" correctly (defeating a crafted first `"decision"` key — the
  plan's own open question) needs real JSON parsing, which bash can't do
  natively. A `python3 -c` parse re-introduces a Python dependency on the
  critical exit-mapping path that the shim header (lines 324–342)
  deliberately keeps interpreter-independent.
  *Mitigation:* on ANY parse failure fall through to the hook's own rc
  (never spuriously `exit 2`, never swallow a real deny) — the fail-open
  invariant. The parse runs only on the already-rare grok blocking path
  (post block→deny rewrite at :447–448), so one more subprocess is
  acceptable; the fail-open fallback is the load-bearing part.

## Must-fix (blocking)

1. **Give F2/F7 a CI home (R-DO1).** No merge should claim "suites green"
   while the council fixture runs nowhere in CI. Either wire node into
   `validate.yml` or mirror F2/F7 as Python matrix tests.
2. **Move/duplicate the F1 smoke into a matrix dir (R-DO2)** so the
   redactor CLI is import-tested on 3.9–3.12, not just one version.
3. **Fix the W3 check so it can't exit-5 (R-DO3):** name the new test
   files or add exit-5 tolerance; pin the F4 test to the correct
   (top-level `scripts/` vs `.claude/scripts/`) collection path.
4. **Landing script must carry the F3 kernel override (R-DO4)** in addition
   to the GPG sentinel, and reconcile the `touched−scope` invariant for the
   two non-canonical files (R-DO5). Dry-run the land before the real one.
5. **F5 parity fix must address BOTH break axes and use ONE oracle**
   (see Unseen U1) — aligning only the classifier leaves the sidecar path
   broken for the common multi-commit push.

## Nice-to-have (advisory)

1. Consider splitting F3 into its own ceremony segment (or at least its
   own revertable commit): a bad `_CANONICAL_GUARDS` edit changes what
   EVERY future edit is gated on — the widest blast radius in this batch —
   and independent rollback of the kernel change is cheap insurance.
2. Add an `actionlint`/`shellcheck -S warning` pass note to the wave
   checks for the two edited shell files (F4 `_grok_harness.sh`, F5-gate
   `pre-push-review-gate.sh`) — both are in the shellcheck-gated set; a
   fix that passes `bash -n` but not shellcheck is a same-session CI-red.
3. F4: normalize (realpath) the target on BOTH sides before comparison —
   the substring bug can also produce false-NOT-ARMED via symlink/realpath
   mismatch, not only false-ARMED.

## Unseen by the original plan

1. **F5 fingerprint parity has a SECOND break axis the plan never names:
   per-commit vs whole-working-tree aggregation.** The gate fingerprints
   each pushed commit's canonical path-set
   (`pre-push-review-gate.sh:156–167`, one `_fp` per commit `_c`), while
   the recorder fingerprints the ENTIRE working-tree diff
   (`check_codex_stop_review.py:472,511` → `l3_paths(repo_root)` over
   `git diff HEAD` + untracked). Even with an identical classifier, a
   multi-commit push produces N per-commit fingerprints that will never
   equal the recorder's single whole-tree fingerprint. So the sidecar
   acceptance-path (b) is effectively dead for any push that isn't exactly
   one commit whose canonical set equals the whole tree's. Aligning only
   the classifier (the plan's stated fix) declares parity while leaving
   this broken — and a single-commit fixture would pass, hiding it. The
   parity test MUST exercise a multi-commit push. (The hash *construction*
   is already parity-correct: both do sorted-unique, `\n`-joined, no
   trailing newline — verified. The break is purely which-paths + which-
   aggregation.)

2. **The classifier divergence runs in BOTH directions — and the
   dangerous direction is the one the plan omits.** The plan's F5 example
   ("coarse-only paths, e.g. `.claude/plans/*.md`") is the *safe*
   direction (gate over-triggers review on plan files the precise
   predicate skips). But the precise `_is_canonical`
   (check_canonical_edit.py:653–694) ALSO covers first segments the coarse
   gate classifier (`pre-push-review-gate.sh:69–76`:
   `.claude|.github|scripts|SPEC|PROTOCOL.md`) misses ENTIRELY —
   `templates/**`, `.codex/**`, `.grok/**`, `AGENTS.md`,
   `requirements.toml`. Those include `templates/settings/settings.base.json`
   (the fail-open-bearing distribution surface PLAN-156 W3 explicitly
   guarded) and the `.grok`/`.codex` kill-switch surfaces. The push gate
   today does NOT require review for edits to those — it UNDER-triggers on
   exactly the egress/disarm surfaces, directly contradicting the gate's
   own comment that it "OVER-triggers review (safe direction)"
   (pre-push-review-gate.sh:39–42). Answer to the open question, operational
   side: **align the gate UP to the precise set** — the reason is not the
   coarse-only plan files, it's these precise-only surfaces the coarse
   classifier never fires on.

3. **F5's "make gate and recorder hash the same set" spans a shell↔Python
   boundary with no shared oracle.** The gate is bash; the recorder imports
   `check_canonical_edit._is_canonical` in-process
   (check_codex_stop_review.py:254–277). "Align on the precise set" for a
   shell script means either reimplementing the guard list in bash (a
   second implementation = the exact drift F5 is trying to kill) or shelling
   out to a canonical-path CLI. `check_canonical_edit.py` has NO CLI today
   (it's a PreToolUse hook) — so F5, like F1, implicitly needs a new
   argv/`__main__` "is-this-path-canonical" entrypoint that BOTH the gate
   and the recorder consult as the single source of truth. Without it,
   parity is a snapshot that drifts on the next guard-list edit.

4. **`check_codex_stop_review.py` is the Codex-harness Stop hook, wired in
   `templates/codex/hooks.json`, but the F5 gate under debate is the
   *grok* `templates/grok/pre-push-review-gate.sh`.** The plan pairs the
   grok push gate against the codex recorder. Confirm the grok rail's
   recorder/gate pair uses the same predicate — if the grok side has its
   own recorder, the parity fix must cover THAT pairing, not the codex one.
   (Flagging as a cross-harness scoping check, not asserting a defect.)

## What I would NOT change

- **The fix-all-7-then-full-quorum-live-fire shape.** Landing the mechanical
  fixes and re-running a real 3-lane council is exactly right; a fixture
  pass would not prove the egress path.
- **The single-ceremony *instinct* for the canonical subset.** Batching the
  canonical edits into one Owner GPG ceremony is sound and keeps the audit
  chain clean — my R-DO4/R-DO5/NTH-1 refine *how*, not *whether*.
- **W4's planted-fixture redaction proof (OQ2, already ratified).** Keep it;
  "no egress observed" → "egress provably redacted" is the difference
  between a claim and a control, and it's cheap.
- **The coarse classifier's over-trigger bias where it applies.** Do NOT
  "optimize" the gate to be minimal — over-triggering review on a superset
  is the safe failure direction; U2's fix is to ADD the missed precise-only
  surfaces, not to trim the coarse ones.
- **Fail-open on grok hook infrastructure.** The exit-2 map's fail-open-on-
  no-decision (`_python-hook.sh:459–470`) is correct and must survive the
  F6 field-parse change — do not let "parse the field" become "nonzero →
  deny".

---

### Open-question answers (operational)

- **F5 direction:** align the GATE to the recorder's precise `_is_canonical`
  set (Unseen U2), via a shared canonical-path CLI oracle (U3), and fix the
  per-commit-vs-whole-tree aggregation too (U1) — otherwise parity is
  cosmetic.
- **Single-ceremony batching:** safe IF the landing script (a) carries the
  F3 `CEO_KERNEL_OVERRIDE` (R-DO4), (b) reconciles `touched−scope` for the
  two non-canonical files (R-DO5), (c) is dry-run first. Splitting buys you
  only independent rollback of the kernel edit (F3) — worth it for F3
  alone (NTH-1), not for the rest.
