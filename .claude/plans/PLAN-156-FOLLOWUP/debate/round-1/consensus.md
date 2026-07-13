---
plan: PLAN-156-FOLLOWUP
round: 1
rounds_synthesized: [round-1]
agents_considered: [vp-engineering, security-engineer, devops-engineer]
decisions_revised_in_plan:
  - "§Waves W1 — F1 rescoped: script-safe import + fail-CLOSED CLI contract + literal-invocation acceptance + matrix-dir smoke"
  - "§Waves W2 — F2 rescoped: verify_failed SPLIT from explicit unverifiable; CLEAN ⇔ lanes≥3 ∧ confirmed==0 ∧ verify_failed==0; F7 RE-ANCHORED to the invocation layer; CI home for the .mjs assertions (Python mirror)"
  - "§Waves W3 — F5 rescoped: shared canonical-path oracle CLI + align gate UP to fine set + reconcile per-commit vs working-tree aggregation + multi-commit parity test; F3 kernel-override declared + own commit segment; F4 characterize-then-pin fixture; F6 structural JSON parse with dual-direction fail semantics; W3 Check fixed (no -k grok exit-5)"
  - "§Waves W4 — gated on F2 fixture proof; planted fixture includes employer-class token; fail-loud crash check added"
  - "§Clarifications — accepted residuals recorded (single fail-open guard on egress workflow; prose-level redact-then-send mitigated by pipe fold; commands sibling gap)"
synthesized_at: 2026-07-13T23:59:00Z
synthesized_by: CEO (S272)
---

## Consensus findings (2+ agents flagged)

1. **C1 — F7 is mis-anchored; the workflow already propagates scope.**
   Flagged by: Critic-A (R-VP1, git-blame proof — scope threading present
   since the file's only commit), Critic-B (Unseen 1, anchors re-verified:
   `council-audit.js:54/:112/:339`). Severity: HIGH (load-bearing for W4's
   "scoped prompts" acceptance). Mitigation: re-anchor F7 to the
   **invocation layer** (`/council` command → `Workflow({args:{scope}})`
   boundary); proof must exercise the real entry, not a workflow-internal
   round-trip (which passes today on already-correct code — the
   fixture-comfort trap). If the invocation layer also proves correct,
   close F7 as NOT-A-CODE-DEFECT with a W4 scoped-prompt assertion.
   Lands: §Waves W2.

2. **C2 — F5 has TWO break axes; predicate alignment alone is a false
   fix, and aligning DOWN is a security regression.** Flagged by: ALL
   THREE (Critic-A R-VP2; Critic-B R-SEC1 [VETO-TRIPWIRE] + R-SEC6;
   Critic-C U1+U2+U3). Severity: HIGH. Agreed mitigation, all parts:
   (a) align BOTH sides UP to the fine `_is_canonical` set — never down
   to coarse (coarse fingerprints are collision-prone → review-reuse
   bypass; and the coarse classifier under-triggers on exactly the
   egress/disarm surfaces: `templates/**`, `.grok/**`, `.codex/**`,
   `AGENTS.md`);
   (b) single-source oracle: new `__main__` "is-this-path-canonical"
   CLI on `check_canonical_edit.py` that BOTH the bash gate (shell-out)
   and the recorder consult — re-implementing the glob list in bash IS
   the drift class being fixed;
   (c) reconcile granularity: gate aggregates the WHOLE pushed range
   into one fingerprint (matching the recorder's aggregate), and the
   parity test MUST exercise a multi-commit push;
   (d) shell-out failure → coarse-set fallback = over-trigger =
   fail-CLOSED, symmetric on both sides;
   (e) enumerate the coverage delta (paths gained/lost) in the ceremony
   record — narrowing a security gate is never silent.
   Lands: §Waves W3.

3. **C3 — F3 edits a `_KERNEL_PATHS` entry; the ceremony needs the
   kernel override + scope reconcile, or it halts mid-apply.** Flagged
   by: Critic-A (R-VP3), Critic-C (R-DO4, R-DO5). Severity: HIGH
   (operational). Mitigation: the landing script exports
   `CEO_KERNEL_OVERRIDE=<reason-slug>` + `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`
   for the F3 hunk (audit-emitted per ADR-031); F3 lands as its OWN
   commit segment inside the ceremony (independent rollback of the
   widest-blast-radius change); sentinel Scope enumerates EVERY touched
   path incl. tests and the two non-canonical files (over-declaration is
   harmless; `touched−scope=∅` semantics resolved); full per-wave checks
   run as PRE-FLIGHT before any GPG sign; dry-run before the real land.
   Lands: §Waves W3 + §How to continue.

4. **C4 — F1 needs script-safe import + a fail-CLOSED CLI contract; the
   happy-path smoke is not the security point.** Flagged by: Critic-A
   (R-VP4), Critic-B (R-SEC3 [VETO-TRIPWIRE], Unseen 2). Severity: HIGH.
   Mitigation: import shim (try relative, except ImportError →
   `sys.path` insert + absolute) — argparse alone does NOT fix
   run-as-file; CLI contract: on ANY internal error exit NONZERO and
   emit NOTHING to stdout (never echo input); acceptance = the literal
   `council-audit.js:145` command run as a subprocess from repo root
   (never `python3 -m`, which masks the failure); smoke asserts BOTH the
   redaction path AND the induced-failure path (exit≠0 + empty stdout);
   invocation folds redact→send into a single `redactor | vendor` pipe
   under `set -o pipefail` so a skipped redaction cannot produce a
   sendable prompt. Library `redact()` single-pass/never-raise/never-echo
   contract untouched. Lands: §Waves W1.

5. **C5 — F6 must not become fail-open; structural parse with
   dual-direction fail semantics.** Flagged by: Critic-B (R-SEC2
   [VETO-TRIPWIRE]), Critic-C (R-DO7); Critic-A offered an
   adjacency-glob alternative (see Rejected #1). Severity: HIGH.
   Mitigation (VETO-holder direction adopted): parse the TOP-LEVEL
   `decision` / `hookSpecificOutput.permissionDecision` with a real JSON
   parse via the already-resolved `$FOUND_PY` (rare blocking path — cost
   acceptable); fail semantics BOTH ways: parse success → field governs;
   parse FAILURE with a deny token present → exit 2 (fail-CLOSED, never
   silently drop a real deny); parse failure with no deny token → fall
   through to hook rc (INFRASTRUCTURE fail-open preserved). Regressions
   BOTH directions: allow-with-quoted-"deny" → exit 0; decoy
   `"decision":"allow"` in an earlier field before the real deny →
   exit 2. Lands: §Waves W3.

6. **C6 — F4 trust probe: exact-entry parse, fail toward NOT-ARMED,
   characterize-then-pin.** Flagged by: Critic-A (NTH-3), Critic-B
   (R-SEC5), Critic-C (R-DO6 + NTH-3). Severity: MEDIUM. Mitigation:
   parse `trusted_folders.toml` line-wise as exact normalized path
   entries (skip comments; realpath-normalize both sides); on ANY parse
   ambiguity resolve to NOT-ARMED (the probe must never over-claim);
   capture a REAL `trusted_folders.toml` from the pinned grok binary as
   the test fixture BEFORE writing the parser (ADR-162 discipline).
   Lands: §Waves W3 (+W4 capture prerequisite).

7. **C7 — the regression tests need a real CI home.** Flagged by:
   Critic-C (R-DO1/R-DO2/R-DO3 — mechanical facts), Critic-A implicitly
   via R-VP5 preflight. Severity: HIGH for W2 (the `.mjs` fixture runs in
   NO CI workflow — "suites green" would be vacuous), MEDIUM for F1
   placement. Mitigation: mirror the F2/F7 assertions as stdlib-Python
   tests in a matrix dir (`.claude/scripts/tests/`) instead of wiring
   node into CI; F1 smoke ALSO lands in a matrix dir (3.9-3.12 coverage —
   it is literally an import-safety fix); W3 Check rewritten to name the
   new test files explicitly (`-k grok` selects 0 tests today → pytest
   exit 5 = spurious red). Lands: §Waves W1/W2/W3 Checks.

## Single-agent insights kept

1. **Critic-B — W4 planted fixture must include an employer-class token**
   (not only a generic fake key): aligns with the standing
   pair-rail-catches-employer-class lesson; cheap; converts the proof
   from narrow to class-level. → W4.
2. **Critic-A — W4 adds a fail-loud crash check**: a missing/broken
   redactor must yield lane `status: unavailable`, never a crash — the
   S270 codex lane "died pre-send" suggests the fail-loud path itself
   may not have fired; that invariant is what the council rests on. → W4.
3. **Critic-B — accepted-residual records**: (a) the egress workflow is
   single-guarded by a fail-open hook (framework-wide posture — explicit
   accept for an egress surface); (b) the redact-then-send prose contract
   remains prompt-level even after F1 — mitigated by the C4 pipe fold;
   named as residual. → §Clarifications.
4. **Critic-C — cross-harness pairing check for F5**: confirm which
   recorder pairs with the grok gate (the analyzed recorder is the codex
   Stop hook); the parity fix must cover the ACTUAL pairing. → W3 task.
5. **Critic-A — F2 verdict semantics**: DEGRADED + named reason in the
   report is sufficient for an ADVISORY instrument; no exit-code change
   (Critic-B concurs in OQ answers — counted here because the exit-code
   OQ resolution text is Critic-A's). → W2.
6. **Critic-C — shellcheck note**: both edited shell files are in the
   shellcheck-gated set; add `shellcheck -S warning` to the wave checks.
   → W3 Check.

## Single-agent insights rejected / deferred

1. **Critic-A — F6 adjacency-glob instead of structural parse**:
   REJECTED in favor of the VETO holder's structural top-level parse
   (C5). The emitter normalization argument is real but key-order/shape
   is not a security guarantee across future hooks; the structural parse
   subsumes the adjacency fix at the same cost class.
2. **Critic-A — option to formally DEMOTE sidecar path (b)**: DEFERRED.
   C2 fixes parity properly (oracle + aggregation); if the multi-commit
   parity test still cannot be made to hold, demotion + ADR note is the
   recorded fallback (two-line ADR per Critic-A).
3. **Critic-B — defense-in-depth beyond the single guard on
   council-audit.js (HARD-DENY class)**: DEFERRED — conflicts with the
   deliberate "sentinel-gated, not HARD-DENY" posture; recorded as a
   conscious trade in §Clarifications, revisit if a second egress-bearing
   workflow ships.
4. **Critic-A — commands sibling gap (`council.md` exact-path guard)**:
   DEFERRED to residual note — LOW severity; a sibling COMMAND cannot
   transmit without an egress-bearing workflow, which F3's glob now
   guards; recorded in §Clarifications.

## Plan adjustments

Applied to `.claude/plans/PLAN-156-FOLLOWUP-council-livefire-findings.md`
in this synthesis commit — index:

1. W1 (F1): script-safe import + fail-closed CLI contract + literal
   invocation acceptance + failure-path smoke + matrix-dir placement +
   redact→send pipe fold (C4, C7).
2. W2 (F2/F7): verify_failed split + CLEAN condition + loud count (C5→F2
   semantics per Kept #5); F7 re-anchored to invocation layer (C1);
   Python-mirror CI home (C7).
3. W3 (F3/F4/F5/F6): kernel override + own commit segment + scope
   reconcile + dry-run (C3); F4 exact-entry parse + NOT-ARMED bias +
   characterize-then-pin (C6); F5 full rescope (C2) + cross-harness
   pairing check (Kept #4); F6 structural parse + dual fail semantics
   (C5); Check set fixed (C7) + shellcheck note (Kept #6).
4. W4: gated on F2 fixture proof; employer-class planted token;
   fail-loud crash check (Kept #1, #2; Critic-B Unseen 4).
5. §Clarifications: accepted residuals + deferred items recorded.

## Round verdict

**PROCEED** (design-coherent after adjustments; no mutually exclusive
designs — the single divergence (F6 implementation) resolved by the
security VETO holder's direction). Reminder: PROCEED certifies design
coherence only (V0). Shipping is authorized exclusively by the
verification cascade — V1 deterministic checks, V2 Codex pair-rail
per-file verdicts at the ceremony, V3 Owner GPG. Owner ratification of
`draft → reviewed` remains pending (this plan's own gate).
