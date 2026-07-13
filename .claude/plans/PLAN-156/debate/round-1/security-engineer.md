---
round: 1
archetype: Security Engineer
skill: security-and-auth
agent_persona: Principal Security Engineer
generated_at: 2026-07-10T00:00:00Z
---

## Verdict

ADJUST — the plan is security-literate and names most of the right surfaces, but three of them are under-specified in ways that would ship a *silently-fail-open* rail. None are REJECT-grade; all are concrete, addressable adjustments before `draft → reviewed`.

## Summary (≤ 3 bullets)

- **What it does:** adds a third host harness (Grok Build) via the PLAN-155 adapter seam, refreshes the codex lane to GPT-5.6 through the ADR-111 pin ceremony, and builds a read-only three-vendor audit council. The doctrine is right: certify ENFORCED by behavioral positive-control, never by config existence; fail-loud lanes; advisory-only council.
- **Strong:** the honest ADVISORY labeling of Grok's non-blocking Stop/UserPromptSubmit/SubagentStart (push-time is the teeth), the fail-loud `STATUS: unavailable` council doctrine, and keeping the council advisory-only. Do not let anyone "improve" these into fake enforcement.
- **Weak:** the exit-2 fail-open linchpin is architecturally decoupled from decision-emission in the *current* code and the plan doesn't say where the coupling lives; the matcher tool-name-mismatch is a dead-gate class that fixture-replay tests cannot catch; and the council egress path (repo content → two external authenticated vendors) has no stated redaction chokepoint.

## Risks

1. **R-SEC1 — exit-2 discipline is decoupled from decision-emission; the "wrapper" has no committed chokepoint. [CRITICAL]**
   In today's architecture (`_python-hook.sh:291` does `exec "$FOUND_PY" "$HOOK_SCRIPT"`), the process exit code is whatever the Python hook returns; the adapter's `emit_decision`/`write_decision` (codex.py) only write JSON to *stdout* and NEVER call `sys.exit`. Under Claude a deny is signaled by JSON-block OR exit 2; under Codex by JSON alone; **under Grok deny requires exit 2 *specifically*, and any other exit — including an uncaught-exception exit 1 — is fail-OPEN.** So a Grok matcher can emit a perfectly correct `{"decision":"deny"}` on stdout and STILL silently allow, because nothing coupled that deny to `exit 2`. The proposal's own open question ("should the wrapper live in the shared shim so it's impossible to forget?") is not rhetorical — it is the difference between a rail and a decoration.
   *Mitigation:* commit to ONE shared chokepoint that owns the decision→exit mapping (a Python dispatch entry all hooks route through, or the shim dropping `exec` to capture stdout+exit and remap). Derive the exit code FROM the emitted decision (deny→2, allow→0), not from the Python exit code. Prefer an UNCONDITIONAL mapping over a `CEO_HOOK_ADAPTER=grok`-gated one (see R-SEC2), pending the W0 check that `exit 2` is inert on Codex.

2. **R-SEC2 — a blanket "exit 1 → exit 2 under Grok" would invert the fail-open-on-infra half of the doctrine, AND depends on adapter resolution being correct. [HIGH]**
   CLAUDE.md §4 requires fail-OPEN on infrastructure (missing file, import failure, timeout) and fail-CLOSED only on INPUT-parse failure inside a security matcher. The process exit code alone cannot distinguish an `ImportError` (infra → must allow) from a `KeyError` parsing hostile input (input → must deny) — both are exit 1. A naive Grok remap that turns every non-zero exit into a deny would fail-CLOSE on transient infra and can brick the Grok session; a naive remap to 0 preserves the fail-open bug. Worse, if the coupling is gated on `CEO_HOOK_ADAPTER=grok`, then any session where that env var is unset/misresolved runs the OLD fail-open mapping under Grok.
   *Mitigation:* make the *hook body* emit an explicit structured deny + exit 2 for input-class failures (the codex.py coherence-gate pattern already does the deny-JSON half — extend it to also drive the exit), and let the shared chokepoint map "a deny decision was emitted → exit 2" and "hook crashed with no decision → fail-open ALLOW (infra)". Exit is decision-derived, not exit-code-derived. Adapter resolution under a non-Claude harness must itself fail to a SAFE exit mapping, never silently to the Claude default.

3. **R-SEC3 — matcher tool-name mismatch is a dead-gate that fixture-replay CANNOT catch. [HIGH]**
   Grok auto-maps `Bash→run_terminal_cmd`, `Edit→search_replace`, `Read→read_file`. Our `settings.json` matchers are keyed on Claude names (`^Bash$`, `Edit|Write|MultiEdit`). Grok evaluates the matcher and decides whether to even spawn our hook process BEFORE our Python runs — so `read_event`'s in-adapter normalization is too late. If the stdin `toolName` and the matcher both carry the NATIVE name, `^Bash$` never fires for `run_terminal_cmd`, the bash-safety guard silently no-ops, and `rm -rf` sails through. This is the S254 dead-gate class, and it is invisible to the golden/drift suites because fixtures enter the pipeline AFTER the matcher gate.
   *Mitigation:* W0 fixture question (a) is load-bearing and must GATE the ENFORCED claim. Matchers must cover BOTH native and mapped names (W3), and W7 must include a positive control that drives a NATIVE-named tool call (`run_terminal_cmd` for `rm -rf ~`) and asserts the deny fires — a mapped-name-only test proves nothing.

4. **R-SEC4 — council egress: repo content leaves to two external authenticated vendors with no stated redaction chokepoint. [HIGH]**
   The council feeds dimension briefs + file excerpts to `codex exec` (→ OpenAI) and `grok -p` (→ xAI, under the Owner's authenticated personal X subscription). The pair-rail already treats this exact boundary as fail-CLOSED egress through a single redactor (`codex_egress_redact`, ADR-114 §AC9). W6 describes containment of grok's *writes* (deny-all-writes profile) but says NOTHING about what LEAVES the process to the vendor. A secret in any scanned file is transmitted to two third parties (with training/retention implications), and the grok lane sends it under the Owner's paid account.
   *Mitigation:* route EVERY external-lane prompt (codex + grok) through the ADR-114 egress redactor before it leaves the process — reuse the pair-rail chokepoint, do not build a second unredacted path. Add an explicit HONEST-LIMITATION that repo content is transmitted to xAI/OpenAI, and have the Owner ratify that at OQ5 (it is a privacy/egress decision, not merely "does the subscription exist").

5. **R-SEC5 — double-fire makes "fired twice", "fired zero times", and "fired once" indistinguishable to a deny-only test. [MEDIUM]**
   If Grok reads `.claude/settings.json` (legacy compat) AND native `.grok/hooks/`, every hook fires twice. Deny is idempotent so enforcement survives, but: `grok_tool_recorded`/`grok_turn_ended` append twice → HMAC chain double-counts → completeness/absence analysis and count reconciliation drift; two processes race the audit filelock (more benign `drain lock timeout` yellows); and if the two surfaces ever DISAGREE the merge is undefined. A green test that only asserts "a deny happened" cannot tell double-fire from single-fire from the matcher-mismatch no-op above.
   *Mitigation:* resolve the surface empirically at W0 and pick EXACTLY ONE; assert the other is inert with a positive control that counts hook invocations per tool call (== 1), not just "deny observed."

6. **R-SEC6 — the council's grok containment is circular: it sandboxes an external autonomous agent with the very rail this plan is still building. [MEDIUM]**
   W6's grok lane is contained by "our own deny-all-writes CEO hooks profile (dogfood-as-sandbox)." That rail's ENFORCED status rests on the exit-2 discipline (R-SEC1) that is not yet proven. Containing an external agent with an unproven-fail-open rail is a single point of failure.
   *Mitigation:* make the W6 grok lane HARD-depend on the W7 exit-2 positive control passing, and add a belt-and-suspenders OS-level backstop (the `settings.json` sandbox block scoped to the council subprocess, or grok's native read-only mode if W0 finds one) rather than relying solely on our hooks to contain the external tool.

7. **R-SEC7 — supply chain: `curl|bash` of a proprietary 0.x binary on a DAILY cadence; weekly watch leaves up to 7 days of uncharacterized drift. [MEDIUM]**
   `curl -fsSL https://x.ai/cli/install.sh | bash` executes a rolling script with no signature/checksum-before-execute; recording the SHA AFTER piping to bash is forensics, not prevention. Pinning the binary SHA (planned — good) defends the binary, but a daily release cadence + weekly staleness check means a breaking upstream release can leave the ENFORCED cells silently ABSENT for up to a week — for a *security-load-bearing* binary that is too slow.
   *Mitigation:* fetch to a file, display+record the hash, execute only after (documented for the Owner). The installer/arming check must assert `grok --version == pin` and fail the harness SETUP (not the user session) on mismatch — refuse to run governance against an uncharacterized binary rather than degrade silently.

## Must-fix (blocking)

1. **Commit the exit-2 chokepoint in the plan text (R-SEC1/R-SEC2).** Name the single shared location that owns decision→exit mapping, specify it is decision-derived (deny→2, allow→0) not exit-code-derived, and specify that a crashing matcher with no emitted decision fails-OPEN as infra while an emitted input-class deny fails-CLOSED with exit 2. If the shim must drop `exec` to remap, say so and carry the perf note (it is a Gate-1 cache-stable file).
2. **Add a mechanical regression gate for the exit-2 class.** A meta-test that FAILS if any hook can emit a deny decision while the process exits non-2 under the Grok mapping. The "impossible to forget" property must be enforced by a test, not by reviewer vigilance — otherwise every future hook is a latent Grok fail-open.
3. **W7 positive control must drive a NATIVE-named tool call (R-SEC3).** Prove `run_terminal_cmd` (not just `Bash`) trips bash-safety, and `search_replace` trips the canonical guard. Gate the ENFORCED matrix claim on it. A mapped-name-only replay is insufficient evidence.
4. **Route council external lanes through the ADR-114 egress redactor (R-SEC4).** Reuse the pair-rail chokepoint; forbid a second unredacted path to codex/grok. Add the "repo content → xAI/OpenAI" HONEST-LIMITATION and fold it into OQ5 Owner ratification.
5. **Resolve the double-fire surface before claiming any ENFORCED cell (R-SEC5).** Pick one surface at W0; assert the other inert with an invocation-COUNT positive control (== 1 per tool call), not a deny-observed test.
6. **Council grok containment: hard-depend on the W7 exit-2 proof + add an OS-level backstop (R-SEC6).** The dogfood sandbox may not be the SOLE containment for an external autonomous agent.
7. **Arming check refuses on version drift (R-SEC7).** `grok --version == pin` or the harness setup fails closed; treat every auto-update as a substrate-watch trigger that re-runs the capability-matrix positive controls before the new binary's ENFORCED cells are trusted.

## Nice-to-have (advisory)

1. Treat the untrusted external-lane RESPONSE with the same strictness the codex verdict parser already uses: size-cap, schema-conform, fail-closed-to-ADVISORY (`parse_verdict_strict` pattern), and FENCE the shard text as untrusted data in the synthesis prompt so a hostile file cannot smuggle instructions into the Claude synthesizer via a vendor lane.
2. Add a `council_lane_invoked` audit action per lane so cross-vendor egress is itself auditable (who was asked what, when) — the completeness caveat already applies.
3. Document the `~/.grok/` global surface as an explicit out-of-repo residual (same class as `~/.codex`), so the kill-switch guard's coverage boundary is honest.
4. Per-lane budget ceilings (OQ6) should be enforced as a hard kill, not advisory — an external LLM in a fanout is a cost-DoS surface if a lane loops.

## Unseen by the original plan

1. **The deny-JSON and the process exit are DECOUPLED today.** The plan treats "emit the deny wire" and "exit 2" as one act; codex.py proves they are two. Any grok hook that emits correct deny JSON still fail-opens unless something *else* sets exit 2. This is the root of R-SEC1 and the plan does not name it.
2. **Matcher evaluation happens upstream of our Python.** In-adapter tool-name normalization cannot save a matcher that Grok never fired. The dead-gate is created before any code we control runs — so it cannot be closed inside the adapter, only in the matcher config + a native-name positive control.
3. **The council grok lane authenticates as the Owner's personal paid X account.** That couples governance-audit egress to a personal subscription and sends repo content under an identity that may be trained on — an identity/data-governance surface the plan frames only as "does the sub exist" (OQ5).
4. **`exit 2` semantics on Codex are unverified.** An unconditional decision→exit-2 mapping (the strongest anti-forget design) is only safe if `exit 2` is inert/ignored on Codex. That is a W0 empirical question the plan should add to the fixture list.

## What I would NOT change

- The honest ADVISORY labeling of Grok's non-blocking Stop/UserPromptSubmit/SubagentStart, and "push-time is the enforcement point." This mirrors the codex inverted-rail precedent and is exactly correct — reject any attempt to fake a blocking Stop on Grok.
- Fail-loud council lanes (`STATUS: unavailable`, never silent vendor substitution). Silent substitution would destroy the cross-vendor-disagreement signal that is the council's entire reason to exist AND could mask a compromised/unreachable lane. Keep it.
- Council is ADVISORY evidence, authorizes nothing; verification cascade V0–V3 unchanged. An external-LLM verdict must never become a truth gate — this demotion is right.
- Certifying every ENFORCED cell by behavioral positive-control replay rather than config existence. This is the doctrine that catches R-SEC3/R-SEC5; keep it as the admission bar for every matrix row.
- Pinning the grok binary SHA + exact version (the pin files mirroring the codex pair). Correct posture for a 0.x daily-cadence binary — the only adjustment is refuse-on-drift (Must-fix 7), not the pin itself.
