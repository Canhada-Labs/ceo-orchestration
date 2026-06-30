---
round: 1
archetype: VP Engineering
skill: architecture-decisions
generated_at: 2026-06-19
---

## Verdict

REJECT

## Summary

- WHAT: migrates the Codex pair-rail to codex-cli 0.139.0 via 3 fixes — stdin=DEVNULL in codex_invoke.py (non-kernel), --no-color→--color never and JSONL parsing in _lib/adapters/codex.py (kernel, HARD-DENY ceremony).
- STRONG: diagnosis is hands-on-validated; kernel-altitude/ceremony framing is correct; parse_verdict fail-open-to-ADVISORY contract preserved.
- WEAK (fatal): the plan fixes the WRONG file. The LIVE wired pair-rail hook is check_pair_rail.py (settings.json:201), whose _invoke_codex_review (L407) has its OWN hardcoded argv that bypasses make_invoke_command AND pipes over stdin — none of the 3 fixes restore the actual production rail.

## Risks

- **R-VP-1 — CRITICAL.** Plan fixes make_invoke_command + codex_invoke.py, but the LIVE pair-rail is check_pair_rail.py:407 `[codex_bin,'exec','--read-only','-']` — never calls make_invoke_command, pipes `input=prompt` over stdin `-` (the exact stdin-block), uses bare `--read-only` (legacy sibling of the removed --no-color → likely rejected too), returns raw stdout. Fixing make_invoke_command is dead code for the real rail; the plan would land a green ceremony and still leave the rail broken. *Mitigation:* add check_pair_rail.py:_invoke_codex_review (also _KERNEL_PATHS:170) as a first-class fix; route through make_invoke_command; positional prompt not stdin `-`; AC that a real pair-rail run returns a verdict.
- **R-VP-2 — HIGH.** parse_usage_from_codex_stdout (codex.py:527) does the IDENTICAL json.loads(whole-stdout) → same 'Extra data line 2' on JSONL; token telemetry silently zeroes. *Mitigation:* shared _extract_agent_message_text helper routed through BOTH parsers in this ceremony.
- **R-VP-3 — HIGH.** Pin-gate contradiction: codex-cli-pin.txt pins >=0.128,<0.131; binary is 0.139. Both pin files are _KERNEL_PATHS:199-200 → a THIRD/FOURTH kernel edit; ADR-111 needs a corpus re-run if catch_rate shifts >5pp. Ceremony scope undercounted. *Mitigation:* repin + refresh SHA in scope; enumerate ALL kernel paths; honor or consciously defer the corpus re-run.
- **R-VP-4 — MEDIUM.** JSONL heuristic under-specified (multi agent_message, reasoning items, truncated streams). 'extract+join' reproduces 'Extra data line 2' one layer down. *Mitigation:* per-line try/except, take LAST agent_message (not join), ignore reasoning, degrade to ADVISORY; unit ACs for each case.
- **R-VP-5 — MEDIUM.** OQ2 (JSONL vs -o/--output-last-message) unresolved; JSONL bakes event-schema into a KERNEL file (every schema rename = new ceremony). *Mitigation:* decide OQ2; prefer --output-last-message for least kernel churn, or isolate CLI-shape behind a non-kernel helper.
- **R-VP-6 — MEDIUM.** Altitude: CLI surface (flags, event schema) encoded in KERNEL-HARD-DENY file; codex-cli already broke twice. Recurring GPG tax with no security value (CLI shape is not the trust boundary; verdict-validation is). *Mitigation:* split CLI-shape into a non-kernel helper; keep trust logic in kernel.
- **R-VP-7 — LOW.** make_invoke_command coerces unknown model → gpt-5-codex (L643); invoke_codex defaults gpt-5.5 (NOT in _VALID_MODELS) → silently coerced. *Mitigation:* reconcile _VALID_MODELS + wrapper default; AC asserts the model reaching codex exec is intended.

## Must-fix (blocking)

1. R-VP-1: add check_pair_rail.py:_invoke_codex_review to scope; route via make_invoke_command; AC that a real run returns a verdict.
2. R-VP-2: route parse_usage_from_codex_stdout through the same JSONL extraction in this ceremony.
3. R-VP-3: resolve codex-cli-pin.txt contradiction; enumerate all kernel paths; honor/defer ADR-111 corpus re-run.
4. R-VP-4: specify the JSONL parsing contract + unit ACs (multi-message, reasoning-interleaved, truncated).
5. R-VP-5/OQ2: decide JSONL-parse vs --output-last-message; if JSONL, isolate CLI-shape behind a non-kernel helper.

## Nice-to-have (advisory)

1. R-VP-6: split CLI-shape out of the kernel (do it in this ceremony to avoid paying the GPG tax twice).
2. R-VP-7/OQ1: reconcile _VALID_MODELS with the gpt-5.5 default.
3. Freeze the S245 0.139 JSONL sample as a test fixture (answers OQ4 — can't dogfood the broken rail).
4. Document the manual workaround as interim coverage; gate the reference-doc retirement on R-VP-1, not just parse_verdict.

## Unseen by the original plan

1. (highest) check_pair_rail.py:_invoke_codex_review is the real production rail with its own broken Codex call none of the 3 fixes touch — a scope/diagnosis gap, not a missing AC.
2. parse_usage_from_codex_stdout — second whole-stdout json.loads, breaks identically.
3. codex-cli-pin.txt vs 0.139 binary: pre-flight gate rejects 0.139 even after a perfect adapter fix.
4. --strict-json (codex.py:661) referenced as a real flag but unverified on 0.139 — may be dead like --no-color.
5. stdin block is a CLASS bug (every subprocess.run to codex exec), not a per-file one.
6. No rollback/verification plan for a kernel edit that cannot be dogfooded.

## What I would NOT change

1. Kernel-altitude framing is correct — keep the sentinel-GPG + CEO_KERNEL_OVERRIDE ceremony.
2. Splitting the non-kernel codex_invoke.py fix into the same commit is right.
3. Preserving parse_verdict fail-open-to-ADVISORY (ADR-106) is correct.
4. The conscious DROP of the hook-tests-dual-rail timeout bump is good governance hygiene.
5. The manual `codex exec review --uncommitted` as the interim bootstrap pass is acceptable.
