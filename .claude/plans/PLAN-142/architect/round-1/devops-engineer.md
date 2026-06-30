---
round: 1
archetype: DevOps & Platform Engineer
skill: devops-ci-cd
generated_at: 2026-06-19
---

## Verdict

ADJUST

## Summary

- WHAT: migrates the Codex pair-rail adapter to codex-cli 0.139.0 via 3 validated fixes — stdin=DEVNULL (non-kernel), --color never + JSONL parse_verdict (kernel).
- STRONG: each break reproduced hands-on (S245); correct kernel-hard-deny framing; honest that the manual workaround keeps coverage alive.
- WEAK: fix-site enumeration INCOMPLETE — the LIVE wired rail check_pair_rail.py has its own broken `codex exec --read-only -` argv that bypasses make_invoke_command; plus a stale version/SHA pin and zero codex coverage in substrate-watch.

## Risks

- **R-OPS-1 — CRITICAL.** The plan fixes the non-live path. The wired hook is check_pair_rail.py (settings.json:201). _invoke_codex_review (L407) builds its OWN `[codex_bin,'exec','--read-only','-']`, pipes input=prompt, no --json, `--read-only` not `--sandbox read-only`. None of the 3 fixes reach it; codex_invoke.py is referenced only by tests/ADRs. check_pair_rail.py is ALSO a kernel path (~L170) — a second kernel edit never scoped. *Mitigation:* add _invoke_codex_review to scope; route through make_invoke_command; P0 AC that the WIRED hook returns a verdict on 0.139; re-scope §2 for BOTH kernel paths + BOTH override tokens.
- **R-OPS-2 — HIGH.** substrate-watch.json watches only claude_code + agent_sdk_ts + agent_sdk_py — `grep codex` returns nothing. Dimension vii was structurally blind to the 0.128→0.139 jump. *Mitigation:* P1 — register a codex_cli component with a watch_for note (exec/--color/--sandbox/--json + flag removals) so the next bump is a nightly advisory.
- **R-OPS-3 — HIGH.** Pins stale + ignored: codex-cli-pin.txt (>=0.128,<0.131) and codex-cli-binary-sha256.txt (0.130-era) vs 0.139 binary; both kernel paths feeding release.yml step 15. A release now fails the pin (or is bypassed via CEO_PAIR_RAIL_VERDICT_OPTIONAL). *Mitigation:* widen pin + refresh SHA under the same ceremony; surface whether step-15 has been silently bypassed.
- **R-OPS-4 — MEDIUM.** Model mis-pinned at two layers: invoke_codex gpt-5.5 → coerced to gpt-5-codex (absent from _VALID_MODELS). S120 PROMOTED gpt-5.5 because gpt-5-codex missed findings → the live rail has silently run the demoted reviewer. *Mitigation:* add intended id to _VALID_MODELS; unknown-id coercion emits an audit breadcrumb / hard-fails; P1 AC argv carries the requested model.
- **R-OPS-5 — MEDIUM.** stdin=DEVNULL is correct for codex_invoke (positional prompt) but would DISCARD the prompt on the live `input=prompt`+`-` pipe path. *Mitigation:* per-call-site remedy — DEVNULL for positional; for the pipe path keep input= (confirm 0.139 accepts it) or convert to positional `-- <prompt>` + DEVNULL; repro AC for the live path.
- **R-OPS-6 — MEDIUM.** Test strategy (OQ4) under-specified for the live path; risk JSONL added, plain-text (which check_pair_rail uses) silently dropped. *Mitigation:* golden-file unit tests (captured 0.139 JSONL + plain-text → both yield verdict, no live binary); CEO_PAIR_RAIL_FIXTURE_RESPONSE-injected decide() test; one network-gated opt-in smoke test; name the backward-compat invariant.
- **R-OPS-7 — LOW.** OQ2 open; --strict-json + --resume never re-validated on 0.139 (may have drifted like --no-color) → strict path silently ADVISORY. *Mitigation:* resolve OQ2; AC re-validates --strict-json + --resume on 0.139; gate behind a version check if removed.

## Must-fix (blocking)

1. Add check_pair_rail.py:_invoke_codex_review (L407) to scope as a third fix site + second kernel edit; P0 AC that the SETTINGS-WIRED hook returns a verdict on 0.139; one argv source of truth.
2. Reconcile governance pins with 0.139 in the same ceremony (widen codex-cli-pin.txt + refresh codex-cli-binary-sha256.txt); both kernel paths feeding release.yml step 15.
3. Register codex_cli in substrate-watch.json so the next drift fails loud (dimension vii is currently blind).
4. Per-call-site stdin remedy + model-id handling (DEVNULL discards the prompt on the live pipe path; gpt-5.5/_VALID_MODELS coercion runs the weaker model silently — make it loud + add the id).

## Nice-to-have (advisory)

1. Make _resolve_codex_bin honor codex-cli-binary-sha256.txt at RUNTIME, not just release CI (mid-session PATH decoy uncaught today).
2. Resolve OQ2 in the plan body (-o/--output-last-message vs JSONL + golden fixture).
3. Re-validate --strict-json + --resume on 0.139.
4. Update the stale check_pair_rail.py L402-406 comment ('validated 0.128.0') after migration.

## Unseen by the original plan

1. (biggest) make_invoke_command claimed 'single source of truth' but the live hook hand-rolls its own argv and never calls it; codex_invoke.py is not wired into settings.json.
2. version pin + binary-sha pin already violated by 0.139 and themselves kernel paths, entangled with release.yml step 15.
3. substrate-watch.json has no codex_cli entry — the instrument meant to catch this drift doesn't watch the component that drifted.
4. silent model coercion gpt-5.5→gpt-5-codex (demoted reviewer) with no audit signal — pre-existing correctness defect.
5. runtime supply-chain gap: _resolve_codex_bin doesn't verify binary SHA at invocation.
6. per-call-site stdin semantics diverge (positional vs pipe) — one-size DEVNULL doesn't transfer.

## What I would NOT change

1. codex_invoke.py stdin fix in the same ceremony — harmless alone, minimizes ceremony count.
2. honest framing that coverage isn't lost meanwhile (manual workaround) — de-escalates urgency correctly.
3. manual `codex exec review --uncommitted` for the diff's own pass — acceptable labeled bootstrap.
4. consciously DROPPING the hook-tests-dual-rail timeout bump — good scope hygiene.
5. fail-open-to-ADVISORY in parse_verdict (ADR-106) — preserve through the JSONL migration.
