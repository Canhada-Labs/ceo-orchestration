---
id: PLAN-142
title: Restore the Codex pair-rail on codex-cli 0.139.0 (live hook + adapter + pins + CLI-shape helper)
status: done
created: 2026-06-19
reviewed_at: 2026-06-19
executed_at: 2026-06-19
completed_at: 2026-06-19
created_by: "CEO (S245 — substrate-drift diagnosis surfaced during the PLAN-139 Codex pair-rail run)"
reviewed_by: "CEO (S245 — 2-round debate: round-1 REJECT [wrong file] → re-scope → round-2 3×ADJUST, all must-fixes folded)"
executed_by: "CEO (S246 — KERNEL ceremony: 5 scoped paths + non-kernel + 7 test files; V1 tests/gates + real smoke (D5 + strict output-schema smoke-resolved); V2 codex review 2×P2 folded; V3 Owner-GPG)"
related_commits:
  - 61021d6                        # PLAN-142 implementation (Owner-GPG); pair-rail restored on codex-cli 0.139.0
owner: CEO
depends_on: []
related_plans:
  - PLAN-139                       # surfaced this drift; its pair-rail ran via the `codex exec` workaround
related_adrs:
  - ADR-010                        # canonical-edit sentinel ceremony
  - ADR-106                        # pair-rail fail-open-to-ADVISORY contract
  - ADR-107                        # pair-rail mandatory L2+ — this restores the AUTOMATED rail
  - ADR-111                        # locked-corpus pin-update protocol (catch_rate re-run)
  - ADR-114                        # outgoing-prompt egress redaction (fail-closed)
  - ADR-121                        # signer registry
risk_tier: C                       # touches MULTIPLE arbitration-kernel paths — KERNEL-HARD-DENY edits
target_tag: TBD
budget_tokens: TBD
context_risk: medium
debate_round_1: done               # REJECT + 2 ADJUST; wrong-file defect found + plan re-scoped
debate_round_2: done               # 3×ADJUST; D1 ratified, all must-fixes folded into §3/§4
provenance:
  source: "S245 hands-on diagnosis + 2-round debate (each CLI claim re-validated against the live codex-cli 0.139.0 binary)"
---

# PLAN-142 — Restore the Codex pair-rail on codex-cli 0.139.0

> **One-line goal:** restore the AUTOMATED Codex pair-rail (ADR-107) on the
> installed `codex-cli 0.139.0`, fixing the LIVE wired hook `check_pair_rail.py`
> (round-1 caught the original plan fixing the wrong file). Multiple
> arbitration-kernel paths → executed under the KERNEL-HARD-DENY ceremony.
> Debate: round-1 REJECT → re-scope → round-2 3×ADJUST (design-coherent with all
> must-fixes folded in). **Per DEBATE-SCHEMA §13, design-coherence satisfies V0
> only — shipping still needs V1 tests/CI → V2 Codex pair-rail → V3 Owner GPG.**

## 0. Provenance & honest framing

Surfaced during PLAN-139 (S245). Round-1 debate caught a fatal wrong-file defect
(the original plan fixed `make_invoke_command`/`codex_invoke.py`, but the
settings.json:201-wired rail is `check_pair_rail.py:_invoke_codex_review`, which
hand-rolls its own argv). CEO re-validated hands-on: `codex exec --read-only -` →
exit 2 on 0.139. Re-scoped; round-2 (3 critics) ratified the re-scope + the D1
altitude call and surfaced implementation must-fixes, all folded below. Every CLI
claim here was reproduced against the live 0.139 binary. Cross-model coverage
continues meanwhile via the manual `codex exec review --uncommitted` workaround
([[reference-codex-cli-substrate-drift]]).

## 1. Diagnosis (re-validated on the live 0.139 binary)

**Primary (LIVE) rail — `.claude/hooks/check_pair_rail.py` (KERNEL):**
- `_invoke_codex_review` (L407) runs `[codex_bin,'exec','--read-only','-']` with
  `input=prompt`. On 0.139 `--read-only` is REJECTED (exit 2; sandbox is now
  `-s/--sandbox <read-only|workspace-write|danger-full-access>`). Rail returns
  CodexUnavailable on every L2+ edit.
- Returns RAW `proc.stdout` (L454); `decide()` feeds it to
  `_detect_write_shaped_patch` (a FREE-TEXT grammar scan, → binary block/accept)
  and `_emit_codex_review_invoked` — it NEVER calls `parse_verdict`. So the
  structured-verdict trust model does not exist on the live rail today
  (round-2 R-VP-D / R-SEC-2 / R-OPS-4), and ingress is un-redacted.

**Secondary (promotion-gate / debug) path — `codex_invoke.py` (NON-kernel) +
`_lib/adapters/codex.py:make_invoke_command` (KERNEL):**
- `make_invoke_command` emits `--no-color` (→ `--color never`), `--json`, and on
  their code paths `--strict-json` (REJECTED on 0.139 → "unexpected argument") and
  `--resume <id>` (now an `exec resume` SUBCOMMAND) — full dead-flag set (R-OPS-2).
- `parse_verdict` + `parse_usage_from_codex_stdout` both `json.loads` the WHOLE
  stdout → 'Extra data line 2' on the `--json` JSONL event stream.
- `codex_invoke.py` `subprocess.run` doesn't close stdin (positional path).

**Cross-cutting (round-1 + round-2):**
- Silent model coercion: `invoke_codex` default `gpt-5.5` ∉ `_VALID_MODELS` →
  coerced to `gpt-5-codex` (demoted S120) at make_invoke_command:643 regardless of
  the wrapper default (C3 / R-OPS unseen).
- Stale kernel supply-chain pins: `codex-cli-pin.txt` (>=0.128,<0.131) +
  `codex-cli-binary-sha256.txt` (baefc1…) vs the live 0.139 binary (d3be84…) (C2).
- `substrate-watch.json` has no `codex_cli` component — the detector that should
  have caught this is blind (R-OPS-6).

## 2. Governance — kernel + release-time entanglements (5, per round-2)

KERNEL-HARD-DENY paths (each needs sentinel GPG `.asc` + `CEO_KERNEL_OVERRIDE=<token>`
+ `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`; discover the exact per-path token at execution):
1. `.claude/hooks/check_pair_rail.py` (_KERNEL_PATHS:170) — live rail invoke + consume.
2. `.claude/hooks/_lib/adapters/codex.py` (_KERNEL_PATHS:155) — parsers + delegation to the helper.
3. `.claude/governance/codex-cli-pin.txt` (_KERNEL_PATHS:199) — widen to admit 0.139.
4. `.claude/governance/codex-cli-binary-sha256.txt` (_KERNEL_PATHS:200) — re-hash to the trusted 0.139 binary.

Release-time coupling (round-2 R-OPS-1 — the 5th entanglement, NOT a kernel edit
but a release blocker): both edited kernel files are in
`.claude/governance/pair-rail-inputs-hash-manifest.txt`. `release.yml` step 15
(`validate-pair-rail-verdict.py --recompute-inputs-hash`) git-hashes every manifest
entry → editing them changes `inputs_hash` → the next release's
`pair-rail-verdict-<tag>.md` MUST be regenerated (tool_versions.codex_cli=0.139.0,
new binary SHA, recomputed inputs_hash) OR the first post-edit release ships under
`CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` with that bypass explicitly recorded.

Non-kernel files: `codex_invoke.py`, `.claude/hooks/_lib/codex_cli_shape.py` (NEW),
`.claude/scripts/substrate-watch.json`, tests, the reference memory.

- Run order: this plan is `reviewed`; execution = KERNEL ceremony across paths 1-4.
- ADR-111: 0.128→0.139 (+ possible reviewer-model change gpt-5.5↔gpt-5-codex) is a
  large jump — run the locked-corpus catch_rate check, OR defer with a rationale that
  NAMES the security consequence (possible reduced detection sensitivity), not a
  generic process deferral (R-SEC-7 / R-OPS-7).
- The implementation diff's cross-model pass: manual `codex exec review
  --uncommitted` (bootstrap) PLUS an Owner human review (R-SEC-6).

## 3. Acceptance criteria

**Live rail (the core fix):**
- `[P0][check_pair_rail.py]` `_invoke_codex_review` no longer uses `--read-only`;
  builds its argv via the NEW non-kernel shape helper (§4 D2); a REAL
  Stop/PreToolUse pair-rail run returns a verdict, not CodexUnavailable. (C1)
- `[P0][check_pair_rail.py]` consume side: read the `-o` last-message file →
  single-pass redact the FULL byte-string → `parse_verdict_strict` (verdict ∈
  `_VALID_VERDICTS`, fail-CLOSED-to-ADVISORY) → `decide()`. `_detect_write_shaped_patch`
  is RETAINED only as a secondary defense-in-depth scan on the redacted text, never
  the primary verdict signal. (R-VP-D, R-SEC-2, R-OPS-4)
- `[P0][check_pair_rail.py]` tmpfile hygiene (the untrusted binary is the WRITER —
  TOCTOU): `tempfile.mkdtemp(0o700)` per call; rail creates the file
  `O_CREAT|O_EXCL|0o600` at an absolute path; REFUSE to read if it is a symlink /
  not a regular file / not owned by us; `finally:` unlink + rmdir on the read,
  timeout, AND exception paths. Degradation matrix → ADVISORY (file missing after
  exit-0 / empty / oversize-cap / present after exit≠0), never raise. (R-SEC-4, R-VP-E, R-OPS-5)

**Adapter + CLI-shape helper:**
- `[P0][NEW _lib/codex_cli_shape.py — non-kernel]` THE single argv builder. It owns
  ALL CLI-shape: flag names (`exec`, `--color never`, `-s/--sandbox`, `-o`,
  `--output-schema`, `--json`), the model-id list (`_VALID_MODELS` moves here), and
  the dead-flag migration (`--strict-json` dropped, `--resume`→subcommand).
  `make_invoke_command`, `codex_invoke.py`, and `check_pair_rail.py` all DELEGATE to
  it (no private argv, no "OR inline argv"). (R-VP-B, R-VP-C, R-OPS-2)
- `[P0][grep gate]` after the ceremony, no CLI literal (`exec`, `--[a-z]`,
  `gpt-5*`/`o3*`/`o4*`, `_VALID_MODELS`) remains in `check_pair_rail.py` or
  `codex.py` — all routed through the helper. The kernel keeps ONLY trust-boundary
  logic (`_VALID_VERDICTS`, fail-open-to-ADVISORY, redaction, finding
  normalization). This is what makes the NEXT codex-cli bump a NON-kernel edit. (R-VP-C)
- `[P0][_lib/adapters/codex.py]` redaction runs on the FULL raw output BEFORE any
  `json.loads`; safe for non-redacting callers (run-promotion-gate.py). (R-SEC-1)
- `[P0][_lib/adapters/codex.py]` verdict accepted ONLY from a structured,
  schema-validated object (`verdict ∈ _VALID_VERDICTS`), NEVER a free-text scan;
  forged free-text 'PASS' with no structured verdict → ADVISORY. (R-SEC-2)
- `[P0][model-id]` reconcile `gpt-5.5` with `_VALID_MODELS` (now in the helper);
  unknown-model coercion is LOUD (audit breadcrumb / hard-fail), not silent; argv
  carries the intended model; confirm it is a valid 0.139 id. (C3)
- `[P0][output contracts converge]` BOTH the live rail and the promotion path build
  argv via the helper using `-o <tmpfile>` for the verdict. The live rail uses `-o`
  ONLY (it has no token-usage consumer — usage telemetry consciously DROPPED on the
  rail, R-SEC-5). The promotion path (codex_invoke.py / run-promotion-gate.py) MAY
  add `--json` to keep `parse_usage` (rewritten to read the last usage event
  per-line from JSONL stdout, NOT whole-stdout json.loads). AC: a real
  run-promotion-gate.py invocation on 0.139 returns a parsed verdict, not 'Extra
  data line 2'. (R-VP-A, R-OPS-3, R-SEC-5)
- `[P1][--output-schema]` pass `--output-schema <FILE>` (present on 0.139) with a
  JSON Schema for `{verdict,findings,summary}` so the CLI ENFORCES the
  structured-verdict shape at generation time — R-SEC-2 becomes CLI-enforced, not
  prompt-dependent. (R-VP-F, R-OPS nice)

**Supply-chain + governance:**
- `[P0][pins]` widen `codex-cli-pin.txt` to admit 0.139 + re-hash
  `codex-cli-binary-sha256.txt`; honor or consciously defer the ADR-111 catch_rate
  re-run with a rationale that names the model-behavior change. (C2, R-SEC-7)
- `[P0][release coupling]` regenerate `pair-rail-verdict-<tag>.md` against the
  post-edit tree (codex_cli=0.139, new SHA, recomputed inputs_hash) OR record the
  `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` bypass for the first post-edit release. (R-OPS-1)
- `[P0][T-8 attribution]` state in writing that the binary-SHA pin (release-time) —
  NOT the structured object — is the forged-verdict (T-8) defense; record the
  mid-session PATH-decoy runtime gap (`_resolve_codex_bin` doesn't hash at
  invocation) as an ACCEPTED RISK (runtime SHA check is a possible follow-up, not a
  5th kernel touch this ceremony). (R-SEC-3)
- `[P1][substrate-watch.json]` register a `codex_cli` component with a watch_for
  note encoding the 0.139 exec flag surface (`--color`, `-s/--sandbox` enum, `-o`,
  `--output-schema`, `--json`, the `--strict-json`/`--read-only` removals) so the
  next bump is a nightly advisory. (R-OPS-6)

**Tests:**
- `[P0][tests]` OFFLINE golden-fixture tests (the kernel edit can't be
  dogfooded): a captured REAL 0.139 `-o` last-message file → redact →
  `parse_verdict_strict` → verdict; plus forged-free-text-PASS → ADVISORY,
  oversize, symlink-refusal, empty, exit≠0. A `CEO_PAIR_RAIL_FIXTURE_RESPONSE`-
  injected `check_pair_rail.decide()` test exercising the consume path without the
  live binary. One opt-in network-gated smoke test (skipped in CI). (R-SEC-6, R-OPS-6, R-VP-E)
- `[P1][tests]` a captured `--json` stdout sample fixture for the rewritten
  `parse_usage` (last-event-per-line). (R-VP-A)

## 4. Design decisions (ratified round-2)

- **D1 — `-o/--output-last-message <tmpfile>`** for the verdict (CLI isolates one
  structured object; no event-schema coupling; verified on 0.139:
  `{"verdict":"PASS"}` written clean). Verdict comes from a structured object the
  prompt requests AND `--output-schema` enforces (D-new). Usage telemetry is
  DROPPED on the live rail (no consumer) and kept via `--json` only on the
  non-kernel promotion path.
- **D2 — single argv builder = NEW non-kernel `_lib/codex_cli_shape.py`.** All
  CLI-shape (flags, model ids, dead-flag migration) lives there; kernel files
  delegate. This is the structural fix for the recurring GPG tax (next bump =
  non-kernel edit), enforced by the §3 grep gate.
- **D3 — `_detect_write_shaped_patch` retained as secondary defense-in-depth**, not
  the primary verdict signal (the primary is `parse_verdict_strict`).
- **D4 — T-8 forgery defense = the binary-SHA pin** (release-time); the runtime
  PATH-decoy gap is an accepted risk this ceremony (runtime hash = follow-up).
- **D5 — OQ1 model id** (gpt-5-codex vs gpt-5.5) resolved at execution against the
  live 0.139 catalog; coercion made loud.

## 5. Status

**REVIEWED — execution-ready (design).** 2-round debate complete: round-1 REJECT
(wrong-file defect) → re-scope → round-2 3×ADJUST with all must-fixes folded into
§3/§4. Execution = the KERNEL-HARD-DENY ceremony across the 4 kernel paths + the
release-time verdict regen, under `/spawn` or direct Owner-GPG ceremony. The
`hook-tests-dual-rail` timeout bump (also a kernel path) stays consciously
DROPPED. Pair-rail coverage continues via the manual workaround meanwhile.
Per DEBATE-SCHEMA §13: this satisfies V0 only — ship via V1 (tests/CI) → V2
(Codex pair-rail, once restored, or the manual workaround + Owner review) → V3
(Owner GPG).
