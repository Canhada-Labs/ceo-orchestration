---
round: 2
archetype: VP Engineering
skill: architecture-decisions
generated_at: 2026-06-19
---

## Verdict

ADJUST

## Summary

- RE-SCOPE IS CORRECT (verified): check_pair_rail.py:407 hand-rolls `[codex_bin,'exec','--read-only','-']`, never calls make_invoke_command/parse_verdict; 4 kernel paths confirmed; pin stale; substrate-watch has no codex_cli. Round-1 C1 holds.
- D1 ALTITUDE CALL SOUND + verified on 0.139: `-o/--output-last-message` exists, `--color never` valid, `--no-color`/`--read-only` gone. One isolated object lowers kernel churn — right call.
- Two D1 defects + an under-budgeted rewrite remain.

## Risks

- **R-VP-A — HIGH.** Telemetry loss is a FALSE DILEMMA: `--json` and `-o` compose in ONE 0.139 call. *Mitigation:* one `codex exec --color never --json -o <tmpfile> -- <prompt>`; rewrite parse_usage to read last usage event per-line; close the §4 'round-2 to confirm' wording.
- **R-VP-B — HIGH.** Contradiction: §3 'route through make_invoke_command' but make_invoke_command emits `--json --no-color` (the rejected shape). *Mitigation:* the NON-kernel shape helper is THE single argv builder; make_invoke_command + codex_invoke + check_pair_rail all delegate to it; drop the 'OR inline argv' escape hatch.
- **R-VP-C — HIGH.** Helper split not concrete: for the next bump to be non-kernel, kernel files need ZERO CLI literals (flags, model ids, _VALID_MODELS). *Mitigation:* AC — grep finds no CLI literal in check_pair_rail.py/codex.py; move _VALID_MODELS + model default into the helper.
- **R-VP-D — MEDIUM.** Live rail has NO structured-verdict consumption — uses _detect_write_shaped_patch (free-text scan), never parse_verdict. Wiring it is a NEW consumer (rewrite), not an argv swap. *Mitigation:* AC — live rail derives decision from parse_verdict(redacted_last_message); decide the fate of _detect_write_shaped_patch.
- **R-VP-E — MEDIUM.** tmpfile adds failure modes (create/race/partial/unlink/disk-full). *Mitigation:* AC degradation matrix (missing/empty/oversize/exit≠0 → ADVISORY, never raise) + finally-unlink.
- **R-VP-F — LOW.** `--output-schema <FILE>` (present on 0.139) unused; R-SEC-2 rests on a prompt instruction. *Mitigation:* evaluate --output-schema as CLI-enforced backstop.

## Must-fix (blocking)

1. R-VP-A: pass `--json` AND `-o` in one call; rewrite parse_usage per-line; delete the telemetry-drop open question.
2. R-VP-B: name ONE argv builder (the non-kernel helper); make_invoke_command + both consumers delegate; drop 'OR inline argv'.
3. R-VP-C: literal-string boundary AC (no CLI literal in kernel files); move _VALID_MODELS + model default to the helper.
4. R-VP-D: AC that the live rail decides via parse_verdict(redacted last message); budget as a rail-logic rewrite.

## Nice-to-have (advisory)

1. R-VP-E: tmpfile degradation-matrix AC + finally-unlink.
2. R-VP-F: evaluate --output-schema as the CLI-enforced structured-verdict backstop.
3. Freeze a real 0.139 --output-last-message tmpfile + a --json stdout sample as golden fixtures (D3/OQ4).

## Unseen by the original plan

1. `--json` + `-o` compose — the telemetry dilemma is false.
2. `--output-schema` exists — the missing CLI-enforced R-SEC-2 backstop.
3. make_invoke_command emits the rejected shape — the §3 'source of truth' AC self-contradicts D1.
4. live rail free-text-scans raw stdout (never parse_verdict) — R-SEC-2 currently VIOLATED by the rail itself.
5. _VALID_MODELS + model literals must also leave the kernel for the next bump to be non-kernel.

## What I would NOT change

1. Re-scope to the live rail (check_pair_rail.py) — correct + verified.
2. D1 (--output-last-message over JSONL) — right architecture; keep.
3. 4-kernel-path enumeration + KERNEL-HARD-DENY ceremony — accurate; don't downgrade.
4. ADR-111 catch_rate re-run-or-documented-deferral — right governance hook.
5. parse_verdict already requires structured verdict∈_VALID_VERDICTS + ADVISORY coercion — route the rail through it, don't change it.
