---
round: 1
archetype: VP Engineering
skill: architecture-decisions
agent_persona: VP Engineering
generated_at: 2026-07-10T23:35:07Z
---

## Verdict

ADJUST — architecturally sound where it reuses the PLAN-155 seam; over-scoped
and under-specified where it introduces two genuinely NEW boundaries (the
Grok exit-code coupling and the cross-vendor Council egress). Ship the Grok
adapter + 5.6 refresh; carve the Council out of this plan.

## Summary (≤ 3 bullets)

- **What it does:** adds a third host-dispatch adapter (`grok`) on the seam
  PLAN-155 built for exactly this, refreshes the codex lane to GPT-5.6 via the
  existing ADR-111 pin ceremony, and stands up a read-only three-vendor audit
  Council. The adapter increment is bounded and provable — the mold is real
  and landed (`KNOWN_ADAPTERS=["claude","codex"]`, `codex.py` host mode live,
  golden/drift suites parameterized).
- **Where it's strong:** it respects every existing invariant — kernel-class
  edit ceremony for `KNOWN_ADAPTERS`, behavioral positive controls as the
  source of truth for each ENFORCED cell (never config existence), honest
  ADVISORY labeling of non-blocking primitives, and Council demoted to
  advisory evidence. These are the load-bearing doctrines; do not let them get
  "simplified."
- **Where it's weak (architecture):** the exit-2 linchpin is described as a
  per-hook / in-adapter wrap, which is forgettable by construction and cannot
  cover the interpreter-crash class; the Council is a new system boundary
  (external-LLM egress over repo content) welded into an adapter plan with a
  circular containment story; and the wave dependency graph + audit-count base
  are under-specified.

## Risks

1. **R-VP1 — exit-2 discipline placed where it can be forgotten (crash class
   uncovered).** Severity: **CRITICAL**.
   Description: On Grok any exit ∉ {0,2} is fail-OPEN. The plan (Wave 2, plan
   §Wave-2 "the `_python-hook` shim / adapter dispatch wraps matcher exceptions
   accordingly UNDER GROK ONLY") locates the fail-closed wrap in the *adapter
   dispatch*, which is **in-process Python**. An import-time error, an
   uncaught exception before the wrap installs, an interpreter segfault, an
   OOM-kill, or a `sys.exit(1)` deep in a matcher never reaches an in-process
   `try/except` — the process dies with a non-2 code and Grok waves the tool
   through. Today `emit_decision()` only writes stdout and returns; the exit
   code is a *separate* concern the hook's `main()` owns (`sys.exit(main())`).
   Coupling deny→exit-2 at the Python layer leaves the whole crash class open.
   Mitigation: move the exit-code translation into the **shared shell shim**
   `.claude/hooks/_python-hook.sh` — the single registered entrypoint for
   every Python hook (confirmed: settings.json wires all hooks through it, and
   the native `.grok/hooks/ceo.json` will point at the same shim). Under
   `CEO_HOOK_ADAPTER=grok`, the shim inspects the child's exit code and, for a
   **PreToolUse-phase security matcher**, re-materializes `{"decision":"deny"}`
   + `exit 2` on ANY non-{0,2} exit (including signals). A shell wrapper
   survives a Python crash the in-process wrap cannot. This is the "impossible
   to forget" answer the proposal's own risk list gestures at — make it the
   decision, not an open question.

2. **R-VP2 — the Council is a new system boundary mis-scoped into an adapter
   plan.** Severity: **HIGH**.
   Description: Waves 0–5 extend an EXISTING seam (low marginal cost, provable
   by replay). Wave 6 creates the framework's first *product-level* external-
   LLM invocation surface — repo content fanned out to `codex exec` and
   `grok -p` as a standing feature, with new egress, new auth/subscription
   coupling, new prompt-injection surface (repo files → external vendor), and
   new per-lane cost. Per the architecture skill's reversibility rubric this is
   at least an *Embedded* dependency and arguably *infrastructure-coupled*
   (owns an egress + auth surface); such candidates require their own ADR and a
   written containment/exit strategy. Bundling it drags the Council's large
   uncertainty onto the adapter's clean increment and pressures shipping the
   Council before the Grok rail has soaked.
   Mitigation: split Wave 6 into its **own plan (PLAN-157)** with its own L3
   debate and its own ADR. It *consumes* the Grok lane (W2–W5) and the codex
   5.6 bump (W1) as inputs, so it is naturally downstream — sequencing it
   separately costs nothing and buys a proper threat model for the new
   boundary.

3. **R-VP3 — circular containment: the Council's Grok lane is sandboxed by the
   very rail it is helping build.** Severity: **HIGH**.
   Description: Wave 6 contains the headless `grok -p` lane with "our own
   deny-all-writes CEO hooks profile (we eat our own dogfood)." That rail is
   (a) brand-new, (b) fail-OPEN on crash per R-VP1 until the shim fix lands,
   (c) advisory-Stop. Using an unhardened, self-authored, crash-fail-open rail
   as the security sandbox for invoking an external LLM over your repo is a
   weak isolation story for an egress boundary.
   Mitigation: gate the Council's Grok lane on a real OS-level sandbox
   (container / read-only FS mount / seccomp, or the existing
   `settings.json` sandbox block with `network.defaultPosture=deny`), OR
   defer the Grok lane until Wave-0 finding (e) locates a native read-only
   mode. Two live lanes (Claude + codex read-only) already satisfy the
   acceptance criterion "≥2 live lanes"; the Grok lane is not on the critical
   path and should not ship behind dogfood-as-sandbox.

4. **R-VP4 — 0.x daily-release cadence vs a weekly staleness check widens the
   CI-green ≠ live-binary gap past what the matrix can honestly claim.**
   Severity: **MEDIUM**.
   Description: Grok Build is proprietary, 0.x, *daily* releases. Fixtures
   follow the pin (correct), but a weekly substrate-watch means the live binary
   the Owner runs can be up to ~7 releases ahead of the certified fixture
   *within one week*. On the Tool-Evaluation rubric, Maintenance-signal
   (breaking-change cadence, semver discipline) scores ≤3 — a HIGH-weight axis,
   which per the rubric requires an explicit Owner override + a documented
   mitigation in the ADR, not just a pin file.
   Mitigation: make the pin-drift detector fire at **SessionStart** (a cheap
   `grok --version` vs `.claude/governance/grok-cli-pin.txt` compare), not
   weekly — a daily-release binary can drift between two sessions in the same
   week. Record the Maintenance-axis score + override rationale in ADR-162.

5. **R-VP5 — wave dependency graph is under-drawn; W1/W6 are coupled but W1 is
   labeled "independent."** Severity: **MEDIUM**.
   Description: W1 is described as "independent of Grok waves," but W6's codex
   lane runs `codex exec` at "the OQ3 default model post-bump" — W6 depends on
   W1 having landed AND on the 5.6 model being invocable. If the Owner elects
   to DEFER the catch_rate run at W1 signing (allowed, S246 precedent), the
   codex-lane model is in flux while W6 wires against it.
   Mitigation: draw the real DAG — W6 `depends_on {W1, W2..W5}`. If W6 becomes
   PLAN-157 (R-VP2), state the inbound dependency on both the Grok lane and the
   5.6 bump explicitly.

6. **R-VP6 — audit-action count base is unreconciled (three numbers in play).**
   Severity: **LOW**.
   Description: The proposal states 316→318, the loaded project memory says the
   base is 314, and the live `.claude/data/audit-registry.golden.txt` is 320
   lines. `check-claude-md-claims.py` enforces hardcoded counts at tolerance=0
   ENFORCING — a wrong base reddens main (the exact class the memory index
   warns about).
   Mitigation: derive the base from the live registry at execution time; never
   hardcode a target from the draft. If Wave 6 adds `council_lane_invoked`,
   fold that arithmetic in the same closeout.

## Must-fix (blocking)

1. **Relocate the exit-2 fail-closed wrapper from the Python adapter dispatch
   to the shared shim `_python-hook.sh` (R-VP1).** The invariant must hold
   through interpreter crash / import failure / signal kill, which only a
   shell-level backstop covers. Key the crash→deny remap on the hook's
   registered **phase** (PreToolUse security matcher → deny-on-crash under
   grok; PostToolUse/observer → stays fail-open) so the "fail-open on
   infrastructure" half of CLAUDE.md §4 is preserved for observers. Prefer a
   single `emit-and-exit` path parameterized per-adapter with its deny-exit
   code, so the mechanism is written once and future hooks inherit it — do not
   ship an invariant that every future hook author must remember.

2. **Make the exit-2 discipline a PARAMETERIZED positive control, not one W7
   artifact (R-VP1).** The golden suite is already parameterized over adapters;
   mirror that: a per-fail-closed-matcher control that, under
   `CEO_HOOK_ADAPTER=grok` with a crashing/parse-failing input, asserts
   `exit 2` + deny. Adding a new fail-closed hook without exit-2 discipline
   must FAIL CI — "its absence is a security regression class" (plan
   §Honest-limitations) has to be enforced by a test, not by doctrine prose.

3. **Carve the Council (Wave 6) into its own plan + ADR + debate (R-VP2).** It
   is a new external-LLM egress boundary and does not ride the adapter seam;
   it deserves its own threat model, cost-ceiling design, and reversibility/
   exit-strategy ADR per the architecture rubric.

4. **Do not ship the Council's Grok lane behind dogfood-as-sandbox (R-VP3).**
   Require an OS-level containment (or a native read-only mode) for any lane
   that invokes an external LLM over repo content; land the Council on the two
   lanes that are safely containable (Claude in-harness + `codex exec
   --sandbox read-only`) and add the Grok lane only when its isolation is not
   the rail it is helping test.

5. **Resolve the native-`.grok/hooks/` vs legacy-`.claude/settings.json`
   coexistence to ONE firing path at Wave 0, and design for forced coexistence
   (see Unseen #1).** This is load-bearing for whether matchers fire at all,
   and "cover both vocabularies in the regex" is not a resolution — it changes
   the matcher's over/under-inclusiveness depending on which path fired.

## Nice-to-have (advisory)

1. Generalize the exit-code shim discipline to codex too. Codex also treats
   exit 2 as a deny alias and also fail-opens on crash (per the failure-
   semantics matrix); one shim mechanism closing the crash class on BOTH
   harnesses is less divergence than a grok-only bespoke path — and it would
   strengthen codex's currently-residual crash class for free.
2. Record the Grok Tool-Evaluation rubric scorecard (5 axes) inside ADR-162,
   not just the capability matrix — the reversibility tier and exit strategy
   for a proprietary 0.x dependency are exactly what the rubric exists to
   force onto the record.
3. Prefer `templates/shared/pre-push-review-gate.sh` over a grok copy (Wave 5
   already flags "decided at execution by diff size") — a shared push-gate is
   one maintenance surface; two copies drift.

## Unseen by the original plan

1. **Legacy-compat coexistence is FORCED, not a choice — and it splits the
   tool-name vocabulary.** The plan frames OQ1 as "native vs legacy" and flags
   double-fire as a risk. The deeper issue: a repo installed for BOTH Claude
   Code and Grok **cannot** disable Grok's reading of `.claude/settings.json`
   without deleting the file Claude Code itself requires. So on any dual-harness
   repo the legacy-compat path is unavoidably active *alongside* native
   `.grok/hooks/`. That is not just double-fire — the two paths may present
   tool names in DIFFERENT vocabularies (native `run_terminal_cmd` vs mapped
   `Bash`), so a single matcher regex can be simultaneously over-inclusive on
   one path and under-inclusive (silent no-op) on the other. Wave 0 must
   characterize both paths *when both are present*, and the design must be
   correct under forced coexistence, not assume you can pick one.

2. **The SuperGrok subscription makes the fixture-refresh loop single-personed
   — coupling the 0.x-drift mitigation to one human's availability.** Only the
   subscribed Owner can `grok login` and therefore only the Owner can ever
   re-record grok fixtures when the daily-release substrate-watch fires. The
   plan notes OQ5 (confirm the subscription exists) but not that this converts
   the load-bearing substrate-watch into a task no one but the single
   maintainer can discharge — a direct amplifier of the already-declared
   bus-factor limitation. Say so in HONEST-LIMITATIONS.

3. **`emit_decision` becoming exit-code-coupled changes the adapter ABI
   contract.** Today the ABI (SPEC/v1/adapters.schema.md) is "adapters write a
   decision shape; the caller owns the exit code." Making the Grok deny
   *require* a specific exit code couples emit to process lifecycle — an ABI
   change the drift detector and `adapters.schema.md` must be updated for, or
   the grok adapter silently diverges from the documented contract the other
   two uphold. The plan treats exit-2 as an implementation detail; it is a
   contract amendment.

4. **Council prompt-injection is bidirectional and unowned.** Repo content
   (which includes untrusted data — `adversary.md`, fixture payloads, staged
   external ADR text) is fed to external vendors; their responses are parsed
   back into ADR-141 shards that a human reads as an audit verdict. The plan's
   fail-loud doctrine covers *availability* (lane down → `unavailable`) but not
   *integrity* (a lane returning attacker-shaped shards because a repo file
   told it to). The Council needs the same "observed content is data, not
   instructions" boundary the rest of the framework enforces — belongs in the
   PLAN-157 threat model.

## What I would NOT change

- **Reusing the PLAN-155 adapter seam instead of inventing a new abstraction.**
  This is the correct 10x-scale answer: the seam was built so a third harness
  is a bounded row, not a rewrite. Adding `grok` as one module + registry entry
  + fixtures + matrix row is exactly the intended cost curve.
- **Behavioral positive controls as the source of truth for every ENFORCED
  cell (never config existence).** This is the single most valuable doctrine in
  the whole adapter program (it is what caught the S254 dead-gate class).
  Defend it against any "the config is present, mark it enforced" shortcut.
- **Kernel-class ceremony for `KNOWN_ADAPTERS` extension**
  (sentinel + `CEO_KERNEL_OVERRIDE` + ACK). Correct — the registry is kernel;
  the plan honors it.
- **Honest ADVISORY labeling of non-blocking primitives** (Grok Stop,
  UserPromptSubmit, SubagentStart). Do not let these be "improved" into false
  ENFORCED claims; push-time is correctly named as the teeth.
- **Council demoted to advisory evidence with vendor attribution — never a
  truth gate**, with cross-vendor disagreement escalated as first-class signal.
  This is both correct per the verification cascade and the Council's actual
  reason to exist. Keep the fail-loud "never silently substitute a vendor"
  rule verbatim.
- **The 5.6 refresh as a pin ceremony, not an edit.** Pointing the existing
  ADR-111 mechanism at the codex lane is the right, boring, in-contract move —
  no new machinery for a compatibility problem the ceremony already solves.
