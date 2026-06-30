---
status: ACCEPTED
---

# ADR-154 — `updatedInput` corrective rewrites: the single-rewriter invariant (H5 force-push pilot)

- **Status:** ACCEPTED (S242, 2026-06-17 — the single-rewriter invariant is in force: `check_bash_safety.py` is the sole `updatedInput` emitter, with the `bash_input_rewritten` audit action; Codex pair-rail satisfied at the PLAN-135 W2 merge `019ec0a1`, re-confirmed Codex R-sweep thread `019ed788`)
- **Date:** 2026-06-12 (proposed) / 2026-06-17 (accepted, S242)
- **Enforcement commit:** `ab5114ab` (PLAN-135 W2 — `_rewrite_git_push_force` in `check_bash_safety.py` + the `bash_input_rewritten` audit action). The force-push rewrite itself is a default-OFF pilot (`CEO_BASH_FORCE_PUSH_REWRITE=1`); the single-rewriter INVARIANT it establishes is in force regardless.
- **Decision drivers:**
  - Harvest item **H5** (`HARVEST-REPORT.md` lines 60-61): the harness exposes `hookSpecificOutput.updatedInput` (PreToolUse) — a hook may *correct* a tool call instead of only blocking it. No repo hook uses this channel today (recon §4: zero `updatedInput` emits on disk; the optimizer explicitly does *not* write a model back). H5 is the FIRST.
  - **Doctrine 1 corollary** (PLAN-135 plan lines 61-67): "a corrective rewrite (`updatedInput`) may NEVER degrade an existing BLOCK into an allow." A more powerful capability than blocking demands its own ADR + Codex review (HARVEST-REPORT H5: "Capacidade mais poderosa que bloquear → exige ADR próprio + pair-rail Codex").
  - **THREAT-MODEL-WORKSHEET §1** (H5 corrective rewrite): the asset is *the integrity of the Bash governance rail's BLOCK semantics* + *audit-chain faithfulness (audited cmd == executed cmd)*; the attack surface is the seam between a token-level detector and a string-level rewriter, and the divergence between the audited and executed input when multiple hooks match.

## Context

`check_bash_safety.py` BLOCKs `git push --force` / `git push -f` and tells the user to use `--force-with-lease`. That is correct but it ends the turn — the user must retype the safe command. The harness `updatedInput` channel lets the rail *do the correction* and re-surface the corrected command for approval. Done naively, a corrective rewrite is a new and dangerous capability:

1. A rewrite that operates on the raw command *string* (`command.replace("--force", "--force-with-lease")`) is an injection seam against a *token-level* detector. `echo "--force" && git push -f` would mis-rewrite the echoed literal, and a quoted `--force` in an unrelated argv position would be corrupted.
2. A rewrite that *silently allows* the rewritten command removes the human from the loop. A bare `--force-with-lease` issued right after a `git fetch` is ≈ a force-push (the lease reflects a freshly-updated ref) — not safe enough for a silent approval.
3. A rewrite whose failure mode falls through to *allow* (or to passing the original `--force` through) would convert a destructive-command BLOCK into an unaudited execution — the exact BLOCK→allow degradation Doctrine 1 forbids.
4. Two hooks that each rewrite the same tool-call, or a rewrite that the audit log does not record, break the invariant that *the audited command equals the executed command*.

The pilot is deliberately ONE pattern. Widening it is a future ADR + Codex, not an in-place edit.

## Decision drivers

- Correct-don't-block is strictly more user-helpful AND strictly more dangerous than block; it earns a dedicated invariant.
- The rail is fail-OPEN by doctrine (§5: hook-infra crashes emit `{}` allow). A *rewrite* error is NOT a hook-infra crash and must NOT inherit fail-open.
- The audit chain is the forensic ground truth; a rewrite that the chain cannot reconstruct is invisible tampering.

## Options considered

- **Option A — string-level `.replace()` + silent allow of the rewritten command.** Rejected: injection seam (driver 1) + removes the human from the loop (driver 2) + no audit faithfulness.
- **Option B — token-level rewrite, `ask` (never silent allow), fail-toward-BLOCK, single-rewriter invariant, before/after hash pair in audit.** ADOPTED. The four NORMATIVE constraints below are the invariant.

## Decision

**The single-rewriter invariant.** A PreToolUse hook MAY emit a corrective `updatedInput` rewrite ONLY under all of:

1. **§1 At most one rewriting hook per tool-call.** `check_bash_safety.py` is the only hook authorized to emit `updatedInput` in this wave. Downstream hooks (and the audit log) see the POST-rewrite input. A second rewriter is NOT permitted without amending this ADR. The pilot scope is EXACTLY one pattern: a single-subcommand `git push --force`/`-f` → `git push --force-with-lease`.
2. **§2 Before/after hash pair in the audit event.** Each rewrite emits `bash_input_rewritten` carrying `before_sha256` + `after_sha256` (sha256 of the original and rewritten command) + the closed-enum `rewrite_class`. The command BYTES are NEVER persisted (a force-push line can carry a remote URL with an inline token); the hash pair lets an auditor prove audited-cmd == executed-cmd without seeing either command. Deny-by-default allowlist `_BASH_INPUT_REWRITTEN_ALLOWLIST`, NEVER `_EMIT_GENERIC_PASSTHROUGH`.

**The four NORMATIVE constraints (debate R1 security must-fix; THREAT-MODEL-WORKSHEET §1 mitigations):**

- **(a) Failure mode is BLOCK.** The rewrite path NEVER passes the original `--force` input through on a half-applied or ambiguous rewrite. Any condition that is not trivially safe to reconstruct — a compound command (more than one subcommand split on `&&`/`||`/`;`/`|`), an unparseable chunk, a token that does not round-trip, a no-op rewrite — returns `None` from `_rewrite_git_push_force` and the caller emits the legacy BLOCK. Fail-open §5 covers hook-INFRA crashes only, NOT rewrite errors.
- **(b) The rewritten command still goes through the permission prompt.** The decision is `permissionDecision: "ask"` (never a silent `allow`), and `permissionDecisionReason` NAMES the rewrite (force → force-with-lease, with the rationale). A bare `--force-with-lease` after a fetch is not safe enough for silent approval — a human stays in the loop.
- **(c) The rewrite operates on the SAME normalized token list the detector uses.** `_rewrite_git_push_force` rebuilds the command token-by-token from `_normalize_command_tokens(...)` output (the same view the detector saw) and re-quotes each token with `shlex.quote`. No string-level substitution against the raw command — that is the injection seam THREAT-MODEL-WORKSHEET §1 names.
- **(d) This ADR declares the single-rewriter invariant** (§1 + §2 above).

**Opt-in flag (default-OFF):** the rewrite is ENABLED only when `CEO_BASH_FORCE_PUSH_REWRITE == "1"`; any other value (including unset) leaves the legacy force-push BLOCK in place. Read from the import-time `trusted_env` snapshot (NOT live `os.environ`), so a late-set value cannot toggle the rewriter mid-op. The pilot ships **default-OFF** so the existing force-push BLOCK — and every byte-identity fixture asserting it — is unchanged on install; the rewrite is opted into per-environment during the pilot. The conservative state is the legacy BLOCK: when the snapshot is unavailable (or `trusted_env` failed to import) the rewriter stays DISABLED (fail toward BLOCK, never toward a weaker guarantee). Even when ENABLED, the safe state is still `ask` + the BLOCK fallback for any ambiguous command.

## Consequences

- **(+)** `git push --force` becomes a one-approval correction instead of a retype-the-command dead-end; the user is steered to `--force-with-lease` with the human still in the loop.
- **(+)** The audit chain records that the rail rewrote the input (hash pair), preserving audited-cmd == executed-cmd faithfulness — closing the THREAT-MODEL-WORKSHEET §1 "divergence between audited and executed input" vector.
- **(+)** The injection seam (string-vs-token) and the BLOCK→allow degradation are both structurally closed: compound/ambiguous commands fall back to BLOCK, the rewrite is token-level, and the decision is always `ask`.
- **(−)** A new public emitter (`emit_bash_input_rewritten`) + 1 new closed-enum action (`bash_input_rewritten`) + the SPEC v2.43 row. H5 contributes exactly one action to the shared W2 `_KNOWN_ACTIONS` set (W1 base 293 → W2 consolidated 299 across H2 config_change ×2, H1 compaction ×2, H5 bash_input_rewritten, H3 subagent_lifecycle_observed); the count/SHA pins are shared W2 consolidation surface re-derived at arc-verify (`staged/w2/actions-added.md`).
- **(~)** `updatedInput` is now a live capability in the codebase. Any future use is gated by this ADR's single-rewriter invariant; a second rewriting hook requires an amendment.

## Residual risks

- **Bare-lease semantics.** `--force-with-lease` (no explicit `<refname>:<expect>`) is weaker than a lease-with-expected-ref: it leases against the local remote-tracking ref, so a `git fetch` immediately before re-acquires the lease and the push behaves ≈ a plain force-push. ACCEPTED because constraint (b) retains the permission prompt — the human approves the rewritten command, in the loop. Recorded here per THREAT-MODEL-WORKSHEET §1 residual.
- **Pilot scope is one pattern.** Widening (`updatedInput` for other commands or a second rewriting hook) is OUT OF SCOPE and requires a new ADR + Codex review — the PLAN-135 guardrail "No `updatedInput` rollout beyond the single H5 pilot hook until its ADR proves no BLOCK→ALLOW" (plan lines 558-562).

## Blast radius

L3+ — touches the Bash governance rail's decision shape (a security-critical Tier-1 hook), introduces a new harness output channel (`updatedInput`) to the codebase, and adds a closed-enum audit action. Codex pair-rail review is mandatory for this unit (PLAN-135 plan line 622: "V2 Codex pair-rail (mandatory for W2 hooks)").
