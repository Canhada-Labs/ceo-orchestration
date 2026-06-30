# PLAN-143 — Round 1 critique — Staff Security Engineer

> Critic lens: security blast radius of each debt item, with VETO authority
> over auth/governance-surface changes. Focus: the governance kill-switches
> (item 1) and the audit_emit allowlist (item 3, ADR-153-class scrub control).
> One of 3 independent critics; I have not seen the others.

## 1. Verdict

**ADJUST.**

The plan is directionally sound and correctly treats the audit allowlist and
the canonical-guarded files as security-relevant surfaces. But the item-1
framing ("25 NEW consumed env vars … including governance kill-switches") is
**factually wrong in a way that drives the security decision** (D3/OQ2), and
the AC for item 1 must not be allowed to "document a kill-switch surface" that
does not exist as a consumed surface. No VETO-magnitude defect blocks the plan,
but two must-fix corrections are required before execution and one AC must be
re-worded so it cannot regress a security control.

## 2. Summary

Items 2, 3, 4 are correctly diagnosed and the preferred fixes are the right
security calls: hasattr-guard the rotation probe (item 2), extend the
closed-enum allowlist on the canonical path rather than mutate the kernel
(item 3), doc-only floor fix (item 4). Item 1's "kill-switch" framing is the
one real problem: the five named switches (`CEO_TRUST_BYPASS`,
`CEO_CANONICAL_GUARD_DISABLE`, `CEO_ALLOW_NO_VERIFY`, `CEO_HOOKS_DISABLE`,
`CEO_SKIP_HOOKS`) have **zero live `getenv`/`environ` consumers** — they enter
the inventory only as documentation tokens inside `env_persist_allowlist.py`,
the very security control whose job is to *exclude* them. The plan must not
"document a surface" that is actually a non-surface, and must not let the
inventory regen quietly enroll override-family names as if they were features.

## 3. Risks

- **R1 (security-control misread → wrong remediation).** The env-inventory
  checker (`env-inventory-check.py:58`, `TOKEN_RE`) is an explicit
  *token-level superset* — its own docstring (lines 11-14) says it captures any
  `CEO_*`/`CLAUDE_*`/`ANTHROPIC_*` token, "a superset of strictly-consumed
  vars." The five kill-switches match because they are *named as forbidden
  strings* in `env_persist_allowlist.py` (lines 32-45) and `_FORBIDDEN_KEY_SUBSTRINGS`
  (lines 97-110). They are not consumed. Treating them as "unreviewed env
  surfaces that must be documented where consumed" (plan §3 AC-1, §2 item-1)
  inverts reality: they are the *output* of a deny-list, not an input surface.
  If the remediation "documents the kill-switch surface" it manufactures the
  appearance of a bypass that the codebase deliberately does not implement.

- **R2 (inventory regen as a silent allowlist-of-bypasses).** Item-1's fix is
  "regenerate `env-inventory.json` in WRITE mode after confirming each of 25
  names." `env-inventory.json` is a generated data file, but regenerating it
  *normalizes* every override/escape-hatch token into an "inventoried,
  intended" set. There is a real test coupling here:
  `test_env_persist_allowlist.py` grep-proves the persist-allowlist is disjoint
  from the override/bypass families. The inventory regen must not become a
  second, weaker registry that launders bypass-family names into "blessed."

- **R3 (allowlist extension is a real security-control edit, correctly
  flagged).** Item 3 extends `_CODEX_INVOKE_DISPATCHED_ALLOWLIST`
  (`audit_emit.py:9555`). This is a deny-by-default scrub allowlist
  (ADR-153-class: closed-enum + per-action allowlist, NEVER
  `_EMIT_GENERIC_PASSTHROUGH`). The plan correctly treats extending it as a
  justified-only change. The security cost of adding `exit_code` is low (a
  bounded small int, no PII, no free-text), but the *precedent* — "we extended
  an audit scrub allowlist to make a dropped field survive" — must be recorded
  so the next extension is not waved through on this one's authority.

- **R4 (manifest re-touch during a verdict-gate transition).** Item 3 (canonical
  locus) re-touches `pair-rail-inputs-hash-manifest.txt` while the
  `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` window is open (PLAN-142). A manifest
  re-hash during a transition window is a window where the pair-rail's own
  integrity reference is in motion — low blast radius (it is a hash manifest,
  not an auth path) but it must be folded into the existing window, not opened
  as a second uncoordinated edit.

## 4. Must-fix (blocking)

- **MF1 — Re-frame item 1; the five "kill-switches" are NOT a consumed
  surface.** Before any inventory regen, the plan must state the verified fact:
  these five names have zero `getenv`/`environ.get` consumers in the live tree
  (I grepped all access patterns; the only hits are the `env_persist_allowlist.py`
  docstring + `_FORBIDDEN_KEY_SUBSTRINGS` and the inventory JSON itself). The
  `TOKEN_RE` superset is doing exactly what it documents. Item-1 work is an
  **inventory-accuracy reconciliation**, NOT a "document the bypass surface"
  task. Rewrite §2-item-1 and §3 AC-1 accordingly.

- **MF2 — AC-1 must NOT require "kill-switch surfaces documented where
  consumed."** As written, AC-1's clause "Kill-switch surfaces documented where
  consumed" is unsatisfiable for the five names (there is no consumption site)
  and, if forced, would push someone to *implement* a consumption site or write
  documentation implying one exists. Replace with: "each NEW token is classified
  as {consumed | forbidden-family-mention | descriptor}; forbidden-family
  mentions are recorded as such and explicitly NOT enrolled as intended
  surfaces." Any token that IS genuinely newly consumed (the `ANTHROPIC_MODEL`
  routing trio is the plausible real-consumer subset) gets the actual review.

- **MF3 — Inventory regen must preserve the deny-list disjointness invariant.**
  The regen step must assert (or the plan must require a check) that no
  override/escape-hatch/kill-switch-family name lands in any *allowlist*
  (`ENV_PERSIST_ALLOWLIST`) as a side effect, and that
  `test_env_persist_allowlist.py` still passes post-regen. Enrolling a name in
  the *inventory* (a descriptive census) is fine; enrolling it in a *persist
  allowlist* is a security regression. Make the plan name this boundary so the
  two "allowlists" are not conflated during execution.

- **MF4 — Item 3: keep the canonical (allowlist) locus; do NOT drop the kwarg
  in the kernel.** From a security standpoint the correct fix is to make the
  closed-enum allowlist *honestly reflect* the field the producer emits, not to
  silently delete the producer's kwarg. Note that the live callsite
  (`check_pair_rail.py:571`) uses the **generic** path
  `emit_generic("codex_invoke_dispatched", exit_code=...)`, while the typed
  emitter `emit_codex_invoke_dispatched()` (`audit_emit.py:9564`) does not even
  accept `exit_code`. The fix must (a) add `exit_code` to
  `_CODEX_INVOKE_DISPATCHED_ALLOWLIST`, (b) clamp/coerce it (`int`, bounded —
  it is a process return code, range it to e.g. 0..255 or store the raw int but
  type-guard it), and (c) the regression test must assert the field survives
  AND that no *other* field newly survives (allowlist did not widen beyond the
  one intended key). A scrub-allowlist edit without a "nothing else leaked"
  assertion is how side-channel fields creep in.

## 5. Nice-to-have

- **NH1 — One-line provenance comment on the allowlist entry.** When `exit_code`
  is added to `_CODEX_INVOKE_DISPATCHED_ALLOWLIST`, annotate it inline
  (`# PLAN-143: process return code, bounded int, no PII`) so the next reviewer
  sees the justification at the edit site, matching the existing per-entry
  comment style in that file.

- **NH2 — Record the allowlist-extension precedent in the plan's design notes.**
  A two-line note: "extending a deny-by-default scrub allowlist requires (i) the
  field is a closed type with no free-text/PII, (ii) a 'nothing else leaked'
  test, (iii) named in the plan." This is cheap and stops the precedent from
  being cited loosely later.

- **NH3 — Item 2 regression test should assert the audit log still ROTATES on a
  real writer.** The hasattr-guard fixes the AttributeError on the shim, but the
  security-relevant property is that the audit log *does* rotate on the real
  `audit_emit` object (an unrotated, unbounded audit log is its own integrity/
  availability risk). Cover both the shim path (no raise) and the real path
  (rotation still invoked).

## 6. Unseen (what the plan does not address)

- **U1 — Why did the rotation probe silently skip for ~2 days (since 2026-06-18)
  with no alarm?** Item 2 is "rotation silently skipped." The security question
  is not just "fix the AttributeError" but "what is the detection latency on a
  governance component (audit-log rotation) failing?" The nightly sweep caught
  it on 06-20; that is the *only* reason it surfaced. The plan should note
  whether audit-rotation health has any signal other than the once-a-night
  hygiene grep — and accept that residual gap explicitly if not.

- **U2 — The 20 *non*-kill-switch NEW names are unexamined here.** I verified the
  five named switches are non-consumed mentions; I did NOT verify the other 20
  (model-routing trio, `CEO_COMPACTION_CONTINUITY`, `CEO_SUBAGENT_LIFECYCLE*`,
  `CLAUDE_ENV_FILE`, etc.). Several of THOSE may be genuinely consumed and some
  (`CLAUDE_ENV_FILE` — an env-file path; `CEO_COMPACTION_CONTINUITY` — a
  kill-switch for the ADR-153 compaction hooks) are themselves security-adjacent.
  The plan's "confirm each of the 25" must apply the MF2 classification to all
  25, and the genuinely-consumed security-adjacent ones (`CLAUDE_ENV_FILE`
  especially — a file-path env surface) deserve the real review the plan
  reserves for "kill-switches."

- **U3 — `emit_generic` vs typed-emitter divergence is a latent class.** The
  fact that `check_pair_rail.py` reaches the audit wire via `emit_generic(...)`
  with a kwarg the typed emitter never declared means OTHER `emit_generic`
  callsites may be silently dropping fields against allowlists they don't know
  exist. Item 3 fixes one instance; the plan does not ask whether this is a
  pattern. A one-line follow-up note ("audit other `emit_generic` callsites for
  silently-scrubbed kwargs") would be honest.

## 7. What I would NOT change

- **Keep the canonical locus for item 3 (D2).** Routing the field through the
  `audit_emit` allowlist rather than the kernel (`check_pair_rail.py`
  KERNEL-HARD-DENY) is the correct security call: it keeps the closed-enum scrub
  contract intact and avoids a second kernel ceremony. The allowlist *is* the
  right place for "which fields may travel" to be decided.

- **Keep the deny-by-default scrub architecture.** Nothing here argues for
  relaxing ADR-153's "dedicated `_scrub_` branch + per-action allowlist, NEVER
  `_EMIT_GENERIC_PASSTHROUGH`." The bug is a *missing* allowlist entry, not an
  over-strict control. Do not "fix" it by widening the passthrough path.

- **Keep the env-inventory `TOKEN_RE` as a superset scanner.** It is doing
  exactly what it claims. The fix is the *interpretation* of its output (MF1/MF2),
  not the scanner. A superset census that over-reports is the safe failure
  direction for a drift detector — do not narrow it to "only `getenv` calls"
  and risk missing a real dynamically-constructed consumer.

## OQ answers

- **OQ2 (do the kill-switches need an ADR?):** **No** — and an ADR here would be
  actively harmful. The five named switches are not implemented bypass surfaces;
  they are forbidden-family *mentions* inside the persist deny-list. Writing an
  ADR "documenting the kill-switch surface" would (a) imply these bypasses exist
  and are governed when they do not, and (b) create a canonical record that the
  next inventory regen could cite to justify enrolling override-family names.
  The correct artifact is the existing inline documentation in
  `env_persist_allowlist.py` plus the MF2 classification note in the inventory.
  IF, during the "confirm each of 25" review, any name turns out to be a
  *genuinely consumed* bypass with no current governing record, THAT specific
  one earns an ADR — but none of the five flagged switches is that case on the
  evidence I have.

- **OQ3 (re-touching the pair-rail manifest while the verdict gate is in
  transition):** Acceptable ONLY if folded into the existing
  `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` window (plan §2 item-3 already says this).
  Do not open a second, independent manifest re-hash. The manifest is a hash
  reference, not an auth path, so blast radius is low — but coordinating it with
  the open window keeps a single coherent integrity-reference transition rather
  than two overlapping ones. Confirm the re-hash is re-signed under the same
  ceremony that the window already requires.

- **Security framing of extending the audit allowlist (item 3):** Justified.
  `exit_code` is a bounded process return code with no PII, no free-text, no
  endpoint/credential content — exactly the closed-enum shape the scrub control
  is designed to permit. The extension makes the audit record *more* faithful
  (the dispatch outcome is forensically relevant for the AML.T0050 dual-rail
  technique this event maps to). The two guardrails are non-negotiable: the
  field must be type-coerced/clamped (MF4), and the regression test must prove
  the allowlist did not widen beyond this one key (MF4). With those, extending
  the allowlist is the right, security-positive change.

VERDICT: ADJUST
