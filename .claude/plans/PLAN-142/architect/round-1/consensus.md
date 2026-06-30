---
plan: PLAN-142
round: 1
rounds_synthesized: [round-1]
agents_considered: [vp-engineering, security-engineer, devops-engineer]
decisions_revised_in_plan:
  - "§1 — re-diagnosed around the LIVE rail check_pair_rail.py:_invoke_codex_review (not make_invoke_command)"
  - "§2 — kernel scope expanded from 2 to 4 paths"
  - "§3 — added security + correctness ACs (redaction ordering, forged-verdict, model-id, JSONL contract, substrate-watch, per-call-site stdin)"
synthesized_at: 2026-06-19
synthesized_by: CEO
verdict_label: NOT-design-coherent (REJECT + 2 ADJUST; fundamental scope defect)
---

> Synthesis consumed anonymized critiques (Critic-A/B/C). Map in
> `anonymization-map.md`. Verdicts: one REJECT, two ADJUST.

## Consensus findings (2+ critics flagged)

- **C1 — CRITICAL (Critic-A, B, C — unanimous).** The plan fixes the WRONG
  file. The settings.json:201-wired pair-rail is `check_pair_rail.py`, whose
  `_invoke_codex_review` (L407) hand-rolls `codex exec --read-only -` (pipes
  `input=prompt`, no `--json`, returns raw stdout) and never calls
  `make_invoke_command`. **CEO re-validated hands-on:** `codex exec --read-only -`
  → exit 2 `unexpected argument '--read-only'` on 0.139. So the live rail is
  broken by the SAME flag-drift class, and the plan's make_invoke_command +
  codex_invoke.py fixes are dead code for it. `check_pair_rail.py` is itself a
  kernel path (_KERNEL_PATHS:170). → §1 + §2 + §3.
- **C2 — HIGH (A, B, C).** Kernel scope undercounted. `codex-cli-pin.txt`
  (>=0.128,<0.131) + `codex-cli-binary-sha256.txt` are stale vs the 0.139 binary
  AND are themselves kernel paths (199-200), feeding release.yml step 15. The
  real ceremony touches ~4 kernel files, not 2; ADR-111 may require a corpus
  re-run. → §2.
- **C3 — HIGH/MEDIUM (A, B, C).** Silent model coercion: `invoke_codex` defaults
  `gpt-5.5`, absent from `_VALID_MODELS`, coerced to `gpt-5-codex` — the reviewer
  S120 explicitly DEMOTED. The live rail has silently run the weaker model with
  no audit signal. → §3 (make coercion loud + reconcile).
- **C4 — MEDIUM (A, C).** JSONL parse contract under-specified — 'extract+join'
  reproduces 'Extra data line 2'. Contract: per-line try/except, take the LAST
  agent_message (not join), ignore reasoning items, degrade to ADVISORY on
  truncated/zero-message. → §3 (unit ACs).
- **C5 — MEDIUM (A, C).** OQ2 unresolved: JSONL parse bakes the event-schema
  into a kernel file (recurring GPG tax). Prefer `-o/--output-last-message`, OR
  isolate CLI-shape behind a non-kernel helper. → round-2 decision + §3.

## Single-agent insights kept

1. **Critic-A:** `parse_usage_from_codex_stdout` (codex.py:527) is a SECOND
   whole-stdout `json.loads` — breaks identically on JSONL, silently zeroing
   token telemetry. Route both parsers through one shared helper this ceremony.
2. **Critic-B:** redaction MUST run on the FULL raw stdout BEFORE any JSONL
   line-split (newline-splitting shreds a multi-line PEM, defeating single-pass
   redaction); applies to non-redacting callers (run-promotion-gate.py) too.
3. **Critic-B:** a verdict must come ONLY from a structured schema-validated
   object, NEVER a free-text scan of `agent_message` — else a swapped binary
   (T-8) forges a PASS. Fail-closed-to-ADVISORY on malformed.
4. **Critic-B:** `check_pair_rail.py` returns raw stdout into
   `_detect_write_shaped_patch`/`_emit_codex_review_invoked` with NO ingress
   redaction — add it to match codex_invoke ordering.
5. **Critic-C:** `substrate-watch.json` has no `codex_cli` component — the
   detector meant to catch this drift is blind. Register it (non-kernel, cheap).
6. **Critic-C:** `stdin=DEVNULL` is per-call-site: it would DISCARD the prompt on
   the live `input=prompt`+`-` pipe path — convert that path to positional
   `-- <prompt>` + DEVNULL.

## Single-agent insights rejected / deferred

- None rejected — all are valid and grounded. The R-VP-6/C5 architectural
  decision (split CLI-shape into a non-kernel helper vs keep JSONL in-kernel) is
  DEFERRED to round-2 as the central design choice to ratify.

## Plan adjustments (index; edits live in PLAN-142.md)

1. §1 Diagnosis — re-centered on the LIVE rail `check_pair_rail.py:407`
   (`--read-only` rejected on 0.139, re-validated); make_invoke_command/
   codex_invoke demoted to secondary (promotion-gate/debug) paths.
2. §2 Governance — kernel scope expanded to 4 paths (check_pair_rail.py, codex.py,
   codex-cli-pin.txt, codex-cli-binary-sha256.txt) + substrate-watch.json
   (non-kernel); all override tokens discovered at execution.
3. §3 ACs — added: live-rail fix + AC, redaction-before-parse, structured-only
   verdict, loud model-id, JSONL contract, parse_usage shared helper,
   substrate-watch codex_cli, per-call-site stdin, pin repin + corpus decision.
4. §4 Status — stays `draft`; round-2 required to ratify the re-scoped plan +
   the C5 altitude decision.

## Round verdict

**RUN-ANOTHER-ROUND.** Round 1 surfaced a fundamental scope/diagnosis defect
(C1, unanimous, CEO-re-validated). The CEO re-scopes PLAN-142 per the
adjustments above; round-2 ratifies the re-scoped plan (does the live-rail fix
hold? is the C5 altitude decision sound? is the 4-kernel-path ceremony correctly
budgeted?). The plan does NOT move to `reviewed` until round-2 returns
design-coherent. Per DEBATE-SCHEMA §13: even a clean round-2 only satisfies V0 —
shipping still needs the verification cascade (V1 tests/CI → V2 Codex pair-rail →
V3 Owner GPG).
