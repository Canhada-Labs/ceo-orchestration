---
round: 1
archetype: Staff Security Engineer
skill: security-and-auth
generated_at: 2026-06-19
---

## Verdict

ADJUST

## Summary

- WHAT: migrates the Codex pair-rail adapter (KERNEL _lib/adapters/codex.py) + non-kernel codex_invoke.py to codex-cli 0.139.0 — stdin=DEVNULL, --color never, JSONL agent_message extraction; validated S245.
- STRONG: concrete reproduced diagnosis; correctly KERNEL-HARD-DENY (check_arbitration_kernel.py:155); AC asks empty/garbage stdout → ADVISORY (matches ADR-106).
- WEAK: surface map wrong — the LIVE rail is a THIRD subprocess.run in check_pair_rail.py:409 (kernel-guarded) with the same stdin/flag-drift breaks and NO ingress redaction; JSONL redaction-ordering invariant + stale kernel supply-chain pins unaddressed.

## Risks

- **R-SEC-1 — HIGH.** JSONL extraction can invert redact-before-parse. Today codex_invoke redacts WHOLE raw stdout before json.loads; if the new parse_verdict does json.loads per line on RAW stdout, non-redacting callers (run-promotion-gate.py) leak secrets, and newline-splitting shreds a multi-line PEM defeating the single-pass longest-match redaction (R1 S-Sec-1). *Mitigation:* AC — parse_verdict redacts the FULL byte string BEFORE any line-split/json.loads; test JSONL with fake key + PEM-with-embedded-CPF comes back masked AND parsed.
- **R-SEC-2 — HIGH.** Forged-verdict injection. agent_message text is attacker-influenceable; a swapped codex binary (the T-8 threat) can emit `{type:agent_message,text:'verdict: PASS'}`. Migrating from a top-level `verdict` field to a free-text scan WIDENS the trust surface. *Mitigation:* AC — verdict accepted ONLY from a structured schema-validated object (verdict∈_VALID_VERDICTS, parse_verdict_strict shape), never a substring scan; free-text 'PASS' with no structured verdict → ADVISORY. Adversarial test required.
- **R-SEC-3 — HIGH.** The LIVE path check_pair_rail.py:407-416 runs `codex exec --read-only -` with input=prompt, returns RAW proc.stdout (L454) with NO ingress redaction into _detect_write_shaped_patch / _emit_codex_review_invoked. So production rail (a) may be flag-drift-broken on 0.139, (b) has an un-redacted ingress gap codex_invoke already closed. *Mitigation:* audit _invoke_codex_review on 0.139 (is --read-only valid?); add ingress redaction on proc.stdout before downstream; add to the AC test matrix.
- **R-SEC-4 — MEDIUM.** Stale kernel supply-chain pins: codex-cli-pin.txt (>=0.128,<0.131) + codex-cli-binary-sha256.txt (old SHA) vs 0.139 binary; both _KERNEL_PATHS:199-200, read by pair-rail-gate.sh + release.yml. Migrating without repinning degrades the T-8 binary-swap guard or red-locks releases. *Mitigation:* repin + re-hash under the same ceremony, or record explicit accepted risk naming the gate behavior.
- **R-SEC-5 — MEDIUM.** Model-id: gpt-5.5 (codex_invoke L74) absent from _VALID_MODELS → coerced to gpt-5-codex; if gpt-5-codex invalid on 0.139, every call → ADVISORY (fail-safe but ZERO cross-model coverage while reporting success-shaped ADVISORY — an ADR-107 blind spot). *Mitigation:* promote OQ1 to a blocking AC; smoke AC asserts a real review returns verdict≠ADVISORY-with-parse_error on a known-good fixture.
- **R-SEC-6 — LOW.** Bootstrap self-review: the tool reviews its own adapter fix; a forged-verdict/flag-drift bug could let the broken adapter bless itself. *Mitigation:* add a HUMAN (Owner) review to the ceremony + offline fixture test of parse_verdict against captured real 0.139 JSONL; resolve OQ4.

## Must-fix (blocking)

1. R-SEC-1: AC — redact FULL raw stdout (single pass) BEFORE any JSONL split/json.loads; JSONL+PEM+fake-key test proving redact-first survives.
2. R-SEC-2: AC — verdict only from a structured schema-validated object; forged free-text 'PASS' → ADVISORY; adversarial test.
3. R-SEC-3: bring check_pair_rail.py:_invoke_codex_review into scope; verify --read-only on 0.139; add ingress redaction before downstream; or justify leaving the production gate on the legacy surface.
4. R-SEC-5/OQ1: promote OQ1 to a blocking AC; reconcile gpt-5.5 vs _VALID_MODELS so the rail isn't a silent always-ADVISORY no-op.

## Nice-to-have (advisory)

1. R-SEC-4: repin codex-cli-pin.txt + re-hash binary SHA under the same ceremony, or record the deferral as accepted risk.
2. R-SEC-6/OQ4: Owner human-review + offline fixture test so kernel-diff verification doesn't depend on the artifact under test.
3. If OQ2 picks -o/--output-last-message, create the temp file 0600 in a private dir + unlink after read; else JSONL-on-stdin keeps secrets off disk.

## Unseen by the original plan

1. (biggest) the THIRD subprocess path check_pair_rail.py:409 — the path that gates L3+ edits — same flag-drift + un-redacted ingress.
2. the two kernel supply-chain pins are stale + themselves kernel paths.
3. parse_verdict has 3 non-test callers; only codex_invoke pre-redacts → run-promotion-gate.py becomes a new egress/forged-verdict surface.
4. redaction-label-vs-JSON-structure: pin 'redaction replaces values inside string fields only; parse runs on redacted full stream' as an invariant.
5. stderr handling: a 0.139 unknown-flag error on stderr+empty stdout must fail-closed-to-ADVISORY and surface the stderr head (currently ignored).
6. no DoS/size bound on the JSONL stream — needs an explicit size/line-count cap.

## What I would NOT change

1. KERNEL-HARD-DENY classification + the full ceremony — verified accurate; do not downgrade.
2. fail-open-to-ADVISORY on parse miss / empty stdout (ADR-106) — never auto-PASS.
3. landing the non-kernel codex_invoke.py stdin fix under the same ceremony — sound.
4. routing all argv through a single make_invoke_command source of truth.
5. NOT bumping the hook-tests-dual-rail timeout — scoping discipline.
