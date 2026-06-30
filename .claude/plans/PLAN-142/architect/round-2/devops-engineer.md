---
round: 2
archetype: DevOps & Platform Engineer
skill: devops-ci-cd
generated_at: 2026-06-19
---

## Verdict

ADJUST

## Summary

- RE-SCOPE CORRECT, every substrate claim re-validated on the live 0.139 binary (/opt/homebrew/bin/codex): --read-only gone (now -s/--sandbox enum); 4 kernel paths real; pin >=0.128,<0.131 excludes 0.139; SHA pin baefc1… ≠ actual d3be84…. C1 holds.
- D1 SOUND: `-o/--output-last-message` exists; single object avoids the JSONL 'Extra data line 2' noise. Verified `--json --color never -o <file>` all coexist → token telemetry need NOT be dropped (parallel capture is technically free).
- FOUR gaps remain (→ ADJUST): dead-flags incomplete, --output-schema unused, inputs-hash replay manifest (5th entanglement) unaddressed, live-rail consume side unspecified.

## Risks

- **R-OPS-1 — HIGH.** inputs-hash replay manifest = unbudgeted 5th governance entanglement. Both edited kernel files are in pair-rail-inputs-hash-manifest.txt; release.yml step 15 (validate-pair-rail-verdict.py --recompute-inputs-hash) git-hashes every entry → editing them changes inputs_hash → the next release verdict file must be regenerated or step 15 BLOCKS. *Mitigation:* §2 obligation — fresh post-edit pair-rail-verdict-<tag>.md (codex_cli=0.139, new SHA, recomputed inputs_hash) OR first release under CEO_PAIR_RAIL_VERDICT_OPTIONAL=1 recorded; name validate-pair-rail-verdict.py + the manifest.
- **R-OPS-2 — MEDIUM.** Dead-flag set incomplete: `--strict-json` (verified → unexpected argument) and `--resume` (now an `exec resume` SUBCOMMAND) are also dead; make_invoke_command emits both. *Mitigation:* P0 AC enumerating the full 0.139 dead-flag set; do the audit in the _lib/codex_cli_shape.py helper in one pass.
- **R-OPS-3 — MEDIUM.** D1 leaves the secondary parse contract broken: codex_invoke.py + run-promotion-gate.py still call make_invoke_command (--json) + parse_verdict(whole stdout) → still 'Extra data line 2'. *Mitigation:* both contracts converge on `-o tmpfile`; AC — run-promotion-gate.py returns a parsed verdict on 0.139.
- **R-OPS-4 — MEDIUM.** Live-rail downstream consume unspecified: decide() uses _detect_write_shaped_patch (free-text), not parse_verdict. *Mitigation:* AC — _invoke_codex_review returns the parsed structured verdict; decide() routes through the whitelist; specify _detect_write_shaped_patch fate.
- **R-OPS-5 — LOW.** tmpfile leaks on timeout/crash if unlink is 'after read'. *Mitigation:* try/finally unlink on timeout + exception paths.
- **R-OPS-6 — LOW.** substrate-watch codex_cli registration needs a real watch_for note (exec flag surface) to catch the next drift. *Mitigation:* specify watch_for content; refresh SHA pin in the same edit.
- **R-OPS-7 — LOW.** ADR-111 defer across a 9-minor + model jump must name WHY catch_rate is assumed stable. *Mitigation:* defer rationale addresses the gpt-5.5 vs gpt-5-codex model-behavior change.

## Must-fix (blocking)

1. R-OPS-1: add the inputs-hash replay manifest + validate-pair-rail-verdict.py to the §2 release.yml step-15 set; a fresh post-edit verdict file or recorded bypass is required.
2. R-OPS-2: enumerate the FULL 0.139 dead-flag set (--no-color→--color never, --strict-json gone, --resume→subcommand) in the shape helper, one ceremony.
3. R-OPS-3: converge BOTH output contracts on `-o tmpfile`; AC that run-promotion-gate.py returns a parsed verdict on 0.139.
4. R-OPS-4: specify the live-rail consume contract (decide() routes the structured verdict through the whitelist; _detect_write_shaped_patch retained-as-advisory or removed).

## Nice-to-have (advisory)

1. Adopt --output-schema <FILE> (CLI-enforces R-SEC-2 structured-only — stronger than a prompt instruction).
2. Record that --json + -o coexist (token telemetry parallel-capture is free); or drop with that fact stated.
3. Runtime binary-SHA check in _resolve_codex_bin (mid-session PATH-decoy window).
4. tmpfile cleanup in try/finally (timeout/exception paths).

## Unseen by the original plan

1. (highest) pair-rail-inputs-hash-manifest.txt replay binding — editing both kernel files invalidates the next release's inputs_hash; release.yml:536-544 blocks unless a fresh verdict file is produced.
2. --strict-json + --resume dead on 0.139; make_invoke_command emits both.
3. --output-schema exists — CLI-native R-SEC-2 enforcement, unmentioned.
4. D1's -o migration doesn't propagate to the --json-consuming secondary parsers — divergent contracts.
5. live-rail downstream is _detect_write_shaped_patch (free-text), not parse_verdict.
6. model coercion happens in make_invoke_command:643 regardless of wrapper default — fix must touch _VALID_MODELS.

## What I would NOT change

1. Re-scope pivot to check_pair_rail.py:_invoke_codex_review — C1 real, keep.
2. D1 (--output-last-message over JSONL) — verified, single object, lowest churn; keep.
3. CLI-shape in _lib/codex_cli_shape.py, trust logic in kernel — correct; do it THIS ceremony.
4. 4-kernel-path enumeration — accurate as far as it goes (R-OPS-1 adds the manifest/verdict coupling).
5. egress redaction already correct at the live rail (L383, fail-CLOSED ADR-114) — scope only the ingress gap.
6. manual workaround + Owner human review as interim bootstrap — sound.
