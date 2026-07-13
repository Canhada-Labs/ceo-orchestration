---
round: 1
archetype: Security Engineer
skill: security-and-auth
agent_persona: Staff Security Engineer (VETO — auth/token/input-handling)
generated_at: 2026-07-13T00:00:00Z
---

## Verdict

ADJUST — the 7 findings are real (I re-verified each at the drifted anchors),
the thesis is sound, and the scope is right. But four fixes (F1, F2, F5, F6)
are described at a level of detail that OMITS the security-load-bearing part:
the *failure direction*. Executed naively, three of them convert a currently
fail-CLOSED control into a fail-OPEN one. Those are named below as
**VETO-TRIPWIRES** — I do not veto the plan, I veto a specific wrong
implementation of it. Address the must-fix list and this is a clean PROCEED.

## Summary (≤ 3 bullets)

- The plan correctly diagnoses that the 11/11 fixture suite proved parse logic,
  not the live egress path, and every anchor I checked is a genuine mechanical
  defect (F1 ImportError, F2 vacuous-CLEAN, F3 exact-path guard, F4 substring
  trust probe, F5 fingerprint divergence, F6 substring exit-map).
- Its weakness is that "add a CLI" (F1), "parse the field" (F6), and "align the
  fingerprint" (F5) each have a SAFE and an UNSAFE implementation, and the plan
  does not pin the safe one. For an egress + governance instrument, the failure
  semantics ARE the fix — the happy path is the easy 20%.
- Two findings the 7 miss: F7 is mis-anchored (the code already reads
  `args.scope`; the live bug is upstream in the invocation layer, so a
  council-audit.js round-trip fixture goes GREEN while the live bug persists —
  the exact fixture-comfort trap this whole plan exists to reject), and the W4
  planted-fixture proof (OQ2) tests one generic token, not the employer-class
  secrets the pair-rail exists to catch.

## Risks

Ordered most-severe first.

- **R-SEC1 — F5 aligning "down" to the coarse set is a fail-open review-reuse
  primitive. [VETO-TRIPWIRE]**
  Severity: HIGH.
  Description: I verified both sides. The recorder
  (`check_codex_stop_review.py:314-328` → `_is_l3_path` :264-277) fingerprints
  the **fine** `check_canonical_edit._is_canonical` set over the **working
  tree**. The gate (`pre-push-review-gate.sh:69-76` `_is_canonical_path`,
  fingerprint at :167) fingerprints a **coarse** first-segment set
  (`.claude/*|.github/*|scripts/*|SPEC/*|PROTOCOL.md`) **per-commit**. The OQ
  asks which direction to align. A coarse fingerprint is COLLISION-PRONE: two
  distinct pushes that touch the same top-level prefixes but different actual
  files hash identically, so one recorded APPROVE clears an unrelated canonical
  edit (`_sidecar_has_approve` at :137-148 matches on fingerprint equality
  alone). Aligning both sides to the coarse set therefore manufactures a
  review-reuse bypass.
  Mitigation: align UP to the **fine** `_is_canonical` set on BOTH sides, never
  down. The recorder already uses it; the gate is bash and cannot import the
  Python predicate — so make the gate **shell out** to a one-line
  `python3 -c "import check_canonical_edit ..."` helper (single source of
  truth) rather than re-implement the glob list in bash (re-implementation IS
  the drift class we are fixing). On shell-out failure, fall back to the coarse
  set — over-trigger review = fail-CLOSED = the safe direction, symmetric with
  the recorder's own fallback (:245-251).

- **R-SEC2 — F6 "parse the decision field" as a first-occurrence substring is a
  fail-open spoof. [VETO-TRIPWIRE]**
  Severity: HIGH (bounded: exit-2 is the belt-and-suspenders half — see "What I
  would NOT change").
  Description: Current code (`_python-hook.sh:462-468`) is
  `case $stdout in *'"decision"'*'"deny"'*)`. Today's failure is an ALLOW whose
  `reason` quotes "deny" → spurious exit 2 = over-block = fail-CLOSED (safe,
  merely annoying). The proposed fix "first `"decision"` key value" INVERTS the
  safety: a hook that emits a user-influenced field BEFORE the decision key —
  `{"reason":"... \"decision\": \"allow\" ...","decision":"deny"}` — makes a
  first-substring/first-regex parser latch onto the decoy `allow` and MISS the
  real deny → exit rc → fail-OPEN on grok. `_emit_block` (check_canonical_edit
  :545-548) happens to put decision first, but key order is not a security
  guarantee and a future hook may differ.
  Mitigation: parse the **top-level** `decision` (and
  `hookSpecificOutput.permissionDecision`) with a real JSON parser — the shim
  already has `$FOUND_PY` resolved and already spends one `sed` subprocess on
  this rare blocking path, so one `"$FOUND_PY" -c 'json.load(sys.stdin)...'` is
  the same cost class. Preserve fail-CLOSED on parse failure: malformed stdout
  that still contains a deny token must keep exiting 2 (never silently drop to
  the hook's rc).

- **R-SEC3 — F1 CLI that echoes input on error is an unredacted-egress leak.
  [VETO-TRIPWIRE]**
  Severity: HIGH.
  Description: The mandated command
  (`council-audit.js:145`) is
  `printf '%s' "$BRIEF" | python3 codex_egress_redact.py --outgoing`, and the
  redacted stdout becomes the vendor CLI prompt. The library `redact()`
  (`codex_egress_redact.py:62-93`) never raises and never echoes input — good.
  But the NEW `__main__` wrapper is where the risk lives: an
  `except: print(text)` (echo original) or an `except: pass` that leaves prior
  partial output would push UNREDACTED repo bytes to xAI/OpenAI. The plan's F1
  check tests only the happy path (`printf 'x' | ... exit 0, redacted`) — it
  does not test the failure mode, which is the whole security point.
  Mitigation: the CLI contract must be: on ANY internal error, exit NONZERO and
  emit NOTHING to stdout (never the input). The smoke test must assert the
  fail-closed path (induce a failure; assert exit!=0 AND empty stdout), not only
  that redaction works. Recommend the invocation use `set -o pipefail` so the
  pipe fails hard rather than feeding `$BRIEF` onward.

- **R-SEC4 — F2 verify_failed must be DISTINCT from explicit unverifiable, or
  the false-green persists in a new disguise.**
  Severity: MEDIUM-HIGH.
  Description: Verified the vacuous-CLEAN
  (`council-audit.js:265-268` null/throw → `{verdicts:[]}`; :273-276 every group
  defaults to `unverifiable`; :328-330 `confirmed=0 && lanes>=3 → CLEAN`). The
  root cause is that TWO different states collapse to one label: (a) the refuter
  RAN and judged `unverifiable`, vs (b) the refuter produced NO verdict for this
  key (crash/omission). The fix must not just rename — it must SPLIT them: the
  synthesized-default (no verdict returned) becomes `verify_failed`; the
  refuter's explicit `unverifiable` stays. Only then can CLEAN be blocked on
  (b) without making CLEAN unreachable whenever the refuter legitimately refutes
  everything (`confirmed=0` via real refutation is a VALID CLEAN and must stay
  reachable).
  Mitigation: CLEAN requires `lanes>=3 AND confirmed==0 AND verify_failed==0`.
  A wholesale refuter failure yields all-`verify_failed` → DEGRADED
  automatically (the per-key rule subsumes the null/throw case — no separate
  flag needed). Surface the `verify_failed` count PROMINENTLY in the report; a
  silent DEGRADED with no reason is still a soft failure.

- **R-SEC5 — F4 trust probe must fail toward NOT-ARMED, never toward false
  ARMED.**
  Severity: MEDIUM (observability/arming surface, not runtime enforcement).
  Description: `_grok_harness.sh:333` is
  `grep -qF "$target" trusted_folders.toml` — a fixed-substring match. A sibling
  entry `/home/u/repo-backup` matches `$target=/home/u/repo` (prefix substring),
  and a commented `# /home/u/repo (revoked)` line matches too → false
  `VERDICT: ARMED` (:347-352). Because grok hooks fail OPEN, a false ARMED tells
  the operator enforcement is live when it is not — the dangerous direction.
  Mitigation: parse `trusted_folders.toml` as TOML (or line-wise), skip
  comments, and match a **normalized exact path entry**. On any parse ambiguity,
  resolve to NOT-ARMED — the probe must never over-claim. This is my red-flag
  class "substring parsing of security-relevant structured data"; it is not in
  my four named VETO domains, so it is a strong MEDIUM, not a tripwire.

- **R-SEC6 — F5 granularity axis (per-commit vs working-tree) is unaddressed by
  "align the set".**
  Severity: MEDIUM.
  Description: Even after set-parity, the gate hashes per-commit
  (`_canonical_paths_in_commit` per `git rev-list` entry, :156-167) while the
  recorder hashes the aggregate working tree (`l3_paths` over
  `git diff HEAD` + untracked, :314-322). A push spreading canonical paths
  across 2 commits yields 2 per-commit fingerprints, neither equal to the
  recorder's single aggregate — the sidecar acceptance path (b) never matches,
  forcing everything onto commit trailers (path a). Fail-closed today, but "fix
  the set" alone will NOT make path (b) work.
  Mitigation: reconcile granularity too — either the gate aggregates the whole
  pushed range before fingerprinting, or the recorder emits per-commit
  fingerprints. Pick one and make the parity test exercise a multi-commit push.

## Must-fix (blocking)

1. **F5 direction is fine-only, single-source, symmetric-fallback (R-SEC1,
   R-SEC6).** Align BOTH sides to `check_canonical_edit._is_canonical`; make the
   gate shell out to it rather than duplicate the glob list; coarse over-trigger
   is the fail-closed fallback on both sides; reconcile per-commit vs
   working-tree granularity; enumerate and explicitly accept every path class
   that LOSES pre-push review coverage when narrowing coarse→fine (e.g.
   `.claude/plans/*.md`). **VETO-TRIPWIRE: any implementation that aligns both
   sides to the coarse set is rejected (fingerprint-collision review-reuse).**
2. **F6 is a top-level JSON parse, not first-substring (R-SEC2).** Parse the
   structural `decision` / `permissionDecision`; preserve fail-CLOSED on parse
   failure. Add the regression the plan names (allow payload with quoted "deny"
   → exit 0) AND its inverse (decoy `"decision":"allow"` in a field BEFORE the
   real deny → still exit 2). **VETO-TRIPWIRE: a first-occurrence substring/
   regex implementation is rejected.**
3. **F1 CLI fails CLOSED (R-SEC3).** On any error: exit nonzero, emit nothing,
   never echo input. Smoke test must assert the FAILURE path (exit!=0 + empty
   stdout), not only the happy path. Recommend `set -o pipefail` at the
   invocation and keep `redact()`'s never-raise / never-echo library contract
   intact. **VETO-TRIPWIRE: a CLI that can emit input bytes on error is
   rejected.**
4. **F2 splits verify_failed from unverifiable (R-SEC4).** CLEAN ⇔
   `lanes>=3 AND confirmed==0 AND verify_failed==0`; keep legitimate
   refute-everything CLEAN reachable; surface the verify_failed count in the
   report. Fixture must cover BOTH a null refuter AND a refuter that omits one
   key.
5. **F3 glob covers the authoring surface, matching the `.grok/hooks/**`
   precedent.** The dir is flat + all-`.js` today (4 files: council-audit,
   audit-fanout, eval-baseline-n20, nightly-hygiene — confirm the Owner accepts
   all four becoming ceremony-gated, per OQ1). But guard
   `.claude/workflows/**/*.js` (subdirs) and consider non-`.js` extensions — "a
   file we choose not to ship is exactly the file an attacker would CREATE" is
   the plan's OWN reasoning for `.grok/hooks/`; apply it here. No
   `_CANONICAL_PREFIXES` addition is needed (`.claude` is already at :654 — do
   NOT add a redundant prefix, but DO confirm this in the sibling-write test).

## Nice-to-have (advisory)

1. **W4 planted fixture (OQ2) should include an employer-class token, not just a
   generic fake API key.** The redactor is only as strong as
   `secret_patterns.ALL_PATTERNS`; the standing lesson is that name-based scans
   miss the employer CLASS (`x-fb-api-key`, `*.com.br`). Prove the redactor
   catches a class token, or the proof is narrower than "egress provably
   redacted" claims.
2. Consider whether the egress-bearing `council-audit.js` warrants
   defense-in-depth beyond the single fail-open `check_canonical_edit.py` guard
   (see Unseen 3) — noting this conflicts with "sentinel-gated, not
   HARD-DENY", so it is a deliberate trade, not a default.

## Unseen by the original plan

1. **F7 is mis-anchored — the fix location is wrong and its fixture will lie.**
   `council-audit.js` ALREADY reads `args.scope` (:54) and threads SCOPE into
   `laneBrief` (:112) and the return (:339). The live-fire scope=`.` bug is
   therefore UPSTREAM — in the `/council` invocation / `council.md` arg-threading
   (:52 is only a doc template), not the workflow. A council-audit.js round-trip
   fixture would pass TODAY and the live bug would survive — the precise
   fixture-comfort trap this plan was written to reject. Re-anchor F7 to the
   invocation layer and make its proof exercise the real `/council` entry, not a
   workflow-internal assertion.
2. **F1's fail-closed egress guarantee rests on an LLM following prose, not on
   code.** `council-audit.js:143-147` INSTRUCTS the lane agent to redact-then-
   send and to treat redactor-unavailable as `unavailable`. That is a prompt
   directive an agent can non-deterministically split or skip. Adding the CLI
   (F1) makes the redactor executable but does not make the redact→send step
   atomic. Strongest fix: fold redaction into a single mechanical step (redactor
   CLI emits only redacted bytes that ARE the sole input to the vendor CLI, via
   `redactor | vendor` with `pipefail`), so a skipped redaction cannot produce a
   sendable prompt. At minimum, treat the two-step prose contract as a KNOWN
   RESIDUAL and name it, as the plan names the R-SEC2 grok residual.
3. **The egress workflow has ONE guard, and it fail-opens.**
   `check_canonical_edit.py` fail-opens on any internal exception (docstring
   :37-40); unlike the arbitration-kernel subset (:104-112), workflows are NOT
   double-guarded. The one surface that transmits repo content externally relies
   on a single fail-open control. Not a blocker (it is the framework-wide
   posture), but worth an explicit accept for an egress surface.
4. **Single-ceremony ordering (OQ answer).** No intra-ceremony window exists IF
   the ceremony lands as ONE atomic commit — F1 (enables egress) and F3 (guards
   it) become live simultaneously. The real sequencing constraint is external:
   W4 live-fire must run STRICTLY AFTER F1+F2 are landed AND verified — never
   run live external egress while the fail-loud verify (F2) is still the vacuous
   version. Gate W4 on F2's fixture proof, not just on the grok sandbox install.

## What I would NOT change

- **Do not remove the exit-2 map or over-escalate F6.** The
  `_python-hook.sh` design is correct: the stdout JSON decision is the PRIMARY
  block on grok, exit-2 is explicitly belt-and-suspenders (:373-374, "block with
  exit 2 STILL fail-opens ... solved by the registration always setting
  CEO_HOOK_ADAPTER=grok"). That bounds R-SEC2's blast radius — do not turn a
  secondary rail into a blocking rewrite or widen the fix into a "nonzero→deny"
  remap (:340-342 correctly rejects that; it would break the INFRASTRUCTURE
  fail-open half).
- **Keep the redactor's single-pass invariant and never-raise/never-echo library
  contract (`codex_egress_redact.py` R1 S-Sec-1, :20-33/:62-93).** F1 adds a CLI
  around it — the CLI must not refactor the library into a chain or add an echo
  path. The AST conformance test that pins single-pass must keep passing.
- **Keep `f.vendor = lane.vendor` (:202) — trusting lane identity over the
  model-written field.** That is the correct anti-spoof posture for attribution;
  do not "simplify" it to trust the finding's self-reported vendor.
- **Keep OS-level containment as the sandbox, not hooks (:21-27 invariant 2).**
  "hooks fail open on grok, so hooks-as-sandbox is circular" is exactly right;
  no fix here should reintroduce a hooks-based containment claim.

## Answers to the proposal's open questions (security-touching only)

- **Single-ceremony batching:** safe as one atomic commit; the ordering risk is
  not in the ceremony but in W4 — sequence live egress strictly after F1+F2 land
  and F2's fail-loud fixture is green (Unseen 4).
- **F2 exit code:** blocking CLEAN → DEGRADED is SUFFICIENT for an ADVISORY
  instrument (nothing gates on a run exit code; forcing one is a category error).
  Necessary complement: split verify_failed from unverifiable and surface the
  count loudly (R-SEC4 / Must-fix 4).
- **F5 direction:** align UP to the fine `_is_canonical` set, NEVER down to
  coarse (coarse → fingerprint collision → review-reuse, R-SEC1); single-source
  via shell-out; reconcile granularity (R-SEC6). Enumerate the coverage the gate
  LOSES when narrowing and get explicit sign-off — narrowing a security gate is
  never silent.
- **F6 new bypass:** YES if implemented as a first-`"decision"`-key substring/
  regex — a decoy allow-field placed before the real deny defeats it (R-SEC2).
  Eliminated only by a top-level structural JSON parse with fail-closed on parse
  error.
- **What the 7 miss:** F7 mis-anchoring + fixture-comfort trap (Unseen 1); the
  W4 planted fixture testing a generic token instead of an employer-class secret
  (Nice-to-have 1); and the prompt-level (not code-level) enforcement of F1's
  redact-then-send step (Unseen 2).

---

### Verification notes (anchors re-checked against disk; line numbers drifted)

- F1 confirmed: `codex_egress_redact.py:47` `from . import secret_patterns`; no
  `__main__` block anywhere in the file → ImportError when run as a script.
- F2 confirmed: `council-audit.js:265-268` (null/throw→`{verdicts:[]}`),
  :273-276 (default `unverifiable`), :328-330 (`confirmed=0 && lanes>=3`→CLEAN).
- F3 confirmed: `check_canonical_edit.py:320-321` lists `council-audit.js` and
  `council.md` as EXACT paths; siblings unguarded. Fast-path prefix `.claude`
  already present (:654) — glob-ization needs no prefix add.
- F4 confirmed: `_grok_harness.sh:333` `grep -qF "$target"` substring; false
  ARMED at :347-352.
- F5 confirmed BOTH axes: recorder fine+working-tree
  (`check_codex_stop_review.py:264-277,314-328`); gate coarse+per-commit
  (`pre-push-review-gate.sh:69-76,156-167`).
- F6 confirmed: `_python-hook.sh:462-468` order-sensitive substring glob over
  whole stdout.
- F7 REFUTED as anchored: `council-audit.js:54` already reads `args.scope`; the
  bug is upstream (UNVERIFIED which exact invocation-layer file drops it — the
  live-fire evidence, not re-runnable here, is the source).
