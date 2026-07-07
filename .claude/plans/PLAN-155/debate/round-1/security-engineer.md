---
round: 1
archetype: Security Engineer
skill: security-and-auth
agent_persona: (security archetype, team.md)
generated_at: 2026-07-07T00:00:00Z
plan: PLAN-155
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- The plan ports the enforcement kernel to a second harness (Codex 0.139)
  via a host-mode adapter, same hooks, new registration surface, inverted
  pair-rail — with a capability matrix that is honest in its labels.
- Strong: residual-in-the-claim vocabulary is applied consistently; the two
  ADVISORY rails (spawn, config tripwire) are never labeled ENFORCED; the
  positive-control replay is the certifying artifact, not config presence.
- Weak: the plan under-models the *silent-full-disarm* class the S254 audit
  already paid for once (pair-rail dead since v1.0.0 via shim fail-open
  `{}`). On Codex every failure-semantics assumption is currently
  UNVERIFIED, the rail's own kill switch (`.codex/` registration surface)
  is not in any protected-path list, and "installed" is conflated with
  "armed".

## Risks

1. **R-SEC-01 — CRITICAL — Adapter mis-resolution silently disarms ALL
   rails (the S254 class, now cross-vendor).**
   `resolve_adapter()` falls back *silently* to `DEFAULT_ADAPTER = "claude"`
   on unknown/empty `CEO_HOOK_ADAPTER` (`_lib/contract.py:218`,
   `contract.py:229-240` — "silent fallback ... emit nothing"). Under a
   Codex host, if the env var fails to propagate through Codex's hook exec
   (typo in `hooks.json`, config-toml merge, future Codex env sanitization),
   every hook parses the Codex envelope with the *claude* adapter — and
   because the two wire vocabularies deliberately overlap
   (`hookEventName`/`permissionDecision`), it will *mostly work in tests*
   and mis-bind only on Codex-specific shapes (`apply_patch` alias). Worse,
   the decision comes back Claude-shaped (`{"decision": "block"}` — today's
   `codex.py:247-263` emits exactly this, "Claude Code is the host IDE");
   if Codex ignores an unrecognized output shape, **deny becomes allow on
   every rail at once, with zero errors anywhere**. This is byte-for-byte
   the S254 P0 pattern (`settings.json` relative path → `_python-hook.sh`
   fail-open `{}`, `_python-hook.sh:269/277/286`, pair-rail dead from
   v1.0.0 unnoticed). PLAN-153 Wave E item 2 exists *because* of this:
   "silence from a fail-open rail is not health."
   **Mitigation:** (a) host/adapter coherence gate in the shared decision
   path — an envelope that is recognizably Codex-wire under a resolved
   adapter of `claude` (and vice versa) is an INPUT/mis-configuration
   failure per the PLAN-152 C4 taxonomy, so fail-CLOSED (deny + breadcrumb),
   not fail-open; (b) apply PLAN-153 Wave E liveness to the Codex
   deployment: a rail that never fires across a Codex session window goes
   RED, and the Wave 6 pre-push/CI breadcrumb assertion must fail RED on
   *absence* of any session records despite new commits — vacuous green is
   the failure mode, not a corner case.

2. **R-SEC-02 — HIGH — Codex failure semantics are assumed, not
   verified; one matrix claim is ahead of its evidence.**
   The plan never establishes what codex-cli 0.139 does when a hook (i)
   times out, (ii) exits non-zero, (iii) emits malformed or foreign-shaped
   JSON, or (iv) emits `{}`. On Claude Code `{}` is a schema-compliant
   allow; if Codex instead treats hook failure as deny, our fail-open shim
   changes meaning — and if Codex treats non-conforming output as allow,
   any adapter bug is a silent allow (feeds R-SEC-01). Separately, the
   matrix (plan line ~139) already claims the inverted pair-rail is
   **PARTIAL (stop-time...)** on the strength of Stop `decision:block`
   auto-continue — but the same research proved `SubagentStart
   continue:false` is *parsed and NOT enforced* on 0.139. Nothing recorded
   shows Stop-block IS enforced. If it is not, the rail is push-time only
   and the matrix row oversells.
   **Mitigation:** Wave 1 fixture-recording session must empirically record
   all four failure-mode behaviors plus a live Stop-block
   enforcement/non-enforcement transcript, BEFORE the matrix rows are
   treated as normative in ADR-161; downgrade the pair-rail row to
   "PARTIAL, pending Stop-block verification" until then.

3. **R-SEC-03 — HIGH — The rail's own kill switch is outside every
   protected-path list.**
   The Config-protection row (plan line ~141) claims "Edit-time PreToolUse
   block ENFORCED" for `.claude/settings.json` + hook sources — but the
   surface that actually disarms Codex enforcement is the NEW registration
   surface: `.codex/hooks.json`, `[hooks]` in `.codex/config.toml`,
   `.codex/rules/ceo.rules`, `requirements.toml`, and the operator
   `AGENTS.md`. None of these appear in the plan's guarded-path story. An
   agent that edits `.codex/hooks.json` to deregister hooks produces a next
   session where the boot-time tripwire *itself* never fires (it was a
   registered hook) — circular disarm. The Wave 6 "breadcrumb asserted
   present per session window" backstop only catches this if
   absence-of-breadcrumb is RED (see R-SEC-01b). Also: "requirements.toml
   MANAGED hooks are ... non-disableable" is only true when
   requirements.toml lives outside agent-writable scope (admin/org config);
   an in-repo or user-writable requirements.toml is disableable by
   definition.
   **Mitigation:** add the full `.codex/` registration surface +
   requirements.toml + operator AGENTS.md to the PreToolUse deny/canonical
   matcher AND to the boot-time hash tripwire scope; ADR-161 states the
   managed-hooks "non-disableable" claim is conditional on placement.

4. **R-SEC-04 — HIGH — Trust-hash coverage is unknown, and both the
   friction risk and the consent story depend on it.**
   `/hooks` trust is "keyed to the hook file's hash." Which file? If it is
   the *registered command's file* — our `_python-hook.sh` shim — then (a)
   the §Risks claim "every framework upgrade invalidates trust" is largely
   FALSE (most upgrades touch `_lib/` and hook `.py` files, not the shim),
   and (b) the consent-first framing of OQ1 is weaker than stated: the
   operator's trust attests a dispatcher, while the enforcement logic it
   dispatches to can change under standing trust with no re-prompt — the
   only guards on that logic are our own edit-time hooks (self-referential)
   and boot-time hash checks. If instead trust hashes the whole transitive
   set, the friction story is as written. These are opposite worlds.
   **Mitigation:** empirically pin the hash-keying semantics on 0.139
   (edit shim → re-prompt? edit `check_bash_safety.py` → re-prompt?) during
   Wave 2 live-fire; ADR-161 gets a normative paragraph "what /hooks trust
   does and does not attest"; OQ1 ratification happens with this fact in
   front of the Owner, not before.

5. **R-SEC-05 — MEDIUM/HIGH — Installed ≠ armed.**
   With the recommended OQ1 default (`/hooks` guided flow), an operator who
   skips or forgets the trust step gets a repo with a complete-looking
   `.codex/` bundle and ZERO enforcement. The success criteria certify
   bundle *production* on a scratch repo; nothing certifies the rail is
   *armed* on the target — the plan's own behavioral-over-static thesis
   (PLAN-153 consensus #2) stops at the installer's door.
   **Mitigation:** post-install arming verification: `doctor`-style check
   (compose with PLAN-153 Wave B machinery once landed) that runs a benign
   positive-control probe and reports ARMED / NOT-ARMED-(untrusted) /
   BROKEN; installer output states loudly that nothing is enforced until
   trust is granted.

6. **R-SEC-06 — MEDIUM — Spawn-rail "re-gained ENFORCED via ^Bash$"
   inherits the interception residual.** Matrix row ~138 says Bash-routed
   spawns "re-gain the ENFORCED gate" — bounded by the same official caveat
   ("doesn't intercept all shell calls yet"). The inheritance must be in
   the row, or the ADVISORY rail borrows an ENFORCED label it doesn't own.

7. **R-SEC-07 — MEDIUM — Operator AGENTS.md injection surface is wider
   than the 32 KiB cap test.** (a) *Nearest-wins shadowing:* discovery is
   git-root→cwd nearest-wins — a planted `subdir/AGENTS.md` (guarded
   nowhere) silently replaces the operator governance contract for sessions
   rooted there. (b) *Truncation padding:* if content past
   `project_doc_max_bytes` is silently dropped, appended padding can push
   governance text off the cliff — the unit test asserts the *template*
   size, not the installed file's drift. (c) `additionalContext` is a
   prompt-shaped channel by design: our injections are fixed strings, and
   hooks must never echo tool-derived/untrusted content into it
   unsanitized (precedent: `check_codex_response.py` ingress-scan).
   **Mitigation:** binding governance summary at the TOP of the template;
   boot-time check warns on size ≥ cap and on a non-root AGENTS.md
   shadowing the operator file; template comments state the shadowing
   rule; additionalContext payloads are static or redacted.

8. **R-SEC-08 — LOW — Wave 4 C oversells headless coverage.** "so headless
   usage still lands in the chain" — only *wrapper-invoked* headless usage
   does; direct `codex exec` bypasses the bracketing. One word fixes it:
   name the wrapper-bypass residual.

9. **R-SEC-09 — LOW — Canonical-edit MCP residual unnamed.** The
   `mcp__.*` deny matcher protects only writes the normalizer can *see*: an
   MCP server with foreign arg names (no recognizable `file_path`) can
   carry a write past the guard. Same class exists on Claude Code; the
   matrix row ~134 should name it alongside the shell-escape class.

10. **R-SEC-10 — LOW — Inverted-rail reviewer-unavailable posture
    unstated.** If `claude` CLI is missing/broken on the target, SPEC §4
    fail-open-on-infrastructure says the Stop gate opens. That is the
    correct doctrine call — but say it in ADR-161, and state that the
    pre-push/CI record check is the guaranteed floor. Verdict-parse
    failures stay fail-closed-to-Owner (never self-approve), per the
    existing V2 doctrine.

11. **R-SEC-11 — LOW — Version-skew arming risk at install time.**
    Operators will install onto codex-cli ≠ 0.139.0 (0.142.5 already
    upstream). Behavioral drift in hook semantics is another silent-disarm
    vector. Installer records the detected codex version in the manifest
    and warns outside the tested range; docs state the tested pin.

## Must-fix (blocking)

1. **R-SEC-01** — host/adapter coherence gate (mis-resolution = INPUT
   failure → fail-closed) + Codex-side liveness per PLAN-153 Wave E, with
   the Wave 6 breadcrumb/chain assertions defined RED-on-absence (no
   vacuous green). Land the coherence gate inside SENT-CX-A scope (adapter
   layer) and the liveness/absence semantics as explicit Wave 6 exit
   criteria text in the plan.
2. **R-SEC-02** — empirical failure-semantics matrix (timeout / non-zero /
   malformed output / `{}` / Stop-block enforcement) recorded as Wave 1
   fixtures BEFORE ADR-161 normativity; pair-rail matrix row marked pending
   until the Stop-block transcript exists.
3. **R-SEC-03** — `.codex/hooks.json` + `config.toml [hooks]` +
   `rules/ceo.rules` + `requirements.toml` + operator `AGENTS.md` added to
   the edit-time deny surface and the boot-time hash tripwire; "managed =
   non-disableable" claim conditioned on placement.
4. **R-SEC-04** — trust-hash coverage empirically determined and written
   into ADR-161 ("what /hooks trust attests"); OQ1 ratified only after.
5. **R-SEC-05** — post-install arming verification (behavioral probe,
   doctor-composed) + explicit NOT-ARMED-until-trusted installer output;
   add to Wave 5 exit criteria and Success criteria.

## Nice-to-have (advisory)

1. R-SEC-06 — inherited-residual wording in the spawn matrix row.
2. R-SEC-07 — AGENTS.md shadowing/truncation/additionalContext hygiene.
3. R-SEC-08 — wrapper-bypass residual wording in Wave 4 C.
4. R-SEC-09 — MCP arg-shape residual named in the canonical-edit row.
5. R-SEC-10 — reviewer-unavailable posture paragraph in ADR-161.
6. R-SEC-11 — installer version-skew record + warning.

## Unseen by the original plan

1. The **cross-adapter mis-binding** failure (R-SEC-01): the plan's
   dual-role-`codex.py` risk covers regression of the reviewer-egress
   helpers, but not the env-drop → wrong-adapter → wrong-output-shape →
   silent-allow chain, which is the highest-consequence single failure in
   the whole design.
2. **Circular disarm of the boot-time tripwire** (R-SEC-03): the tripwire
   is itself a registered hook; deregistration kills the detector along
   with the detected. Only RED-on-absence semantics in pre-push/CI break
   the circle.
3. **Trust-attestation gap** (R-SEC-04): the plan discusses rekeying as
   *friction*; it never asks what the hash actually attests — the security
   meaning of the consent flow is currently unknown.
4. **Codex's default disposition on hook failure** (R-SEC-02): every
   fail-open/fail-closed sentence in the plan implicitly assumes
   Claude-Code semantics (`{}` = allow) transfer. Unverified.
5. **AGENTS.md nearest-wins shadowing** as a governance-context bypass
   (R-SEC-07a) — the placement doctrine is documented for correctness, not
   examined as an attack surface.

## What I would NOT change

- The **capability-matrix vocabulary as binding text** with residuals
  inside the claim — this is the best honesty instrument in the plan;
  ADR-161 carrying it as normative is right.
- Keeping the **spawn and config-tripwire rails labeled ADVISORY** with
  named backstops, and refusing to let CI teeth "promote" them — correct,
  do not let a later round talk this into ENFORCED.
- **Positive-control replay as the certifying artifact** (Wave 1) — the
  correct PLAN-153 Wave E doctrine; my adjustments extend it to
  deployment/arming, they do not replace it.
- **Fail-closed on input, fail-open on infrastructure** carried over
  unchanged (`check_bash_safety.py:1068`
  `bash_parse_failed_fail_closed`; PLAN-152 C4) — the C4 taxonomy is also
  exactly the lever that makes R-SEC-01's coherence gate doctrinally
  clean (mis-configuration is input, not infrastructure).
- **Wave 0 substrate watch-item BEFORE code ships**, and the hard
  install.sh sequencing rule against PLAN-153 (S258 scope-assert as the
  tripwire) — both are the right paranoia.
- Refusing to "solve" trust-rekeying friction by discouraging hook
  updates (§Risks) — keep that sentence verbatim.
