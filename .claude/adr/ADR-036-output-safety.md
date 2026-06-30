# ADR-036: Output Safety Harness (PostToolUse Agent Scanner)

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 11 Phase 9
**Supersedes:** none
**Extends:** ADR-005 (event stream v2), ADR-011 (injection_flag v2.1)
**Companion:** ADR-011 (input side — scan-injection.py)

## Context

ADR-011 ships an advisory **input** scanner: when the agent Reads a
file, `check_read_injection.py` flags patterns likely crafted to subvert
the LLM's instructions. This is only half of the story. The other half
is **output** — when the agent responds, does the response leak PII,
credentials, API keys, or other secrets?

Sprint 11 debate round 1 finding H14 identified this gap as CRITICAL
and specified the scanner pipeline order that any output scanner MUST
follow. A regex-first scanner is trivially bypassed by Unicode
normalization attacks (full-width glyphs, zero-width joiners, bidi
overrides), base64 encoding, and entropy-disguise attacks.

## Decision drivers

- **Symmetry with injection scanning.** ADR-011 establishes the
  per-family event shape + advisory contract. Output scanning adopts
  the same shape with a new action literal so operators have one
  tooling path for both directions.
- **Attack-resistance over single-regex simplicity.** H14 is explicit:
  regex alone is defeatable. Mandatory pipeline: NFKC → strip
  invisibles → bounded base64 decode → entropy → regex.
- **False-positive discipline.** Every added pattern must ship with
  control fixtures that MUST NOT match. This is the gate for flipping
  from flag mode → redact mode.
- **Advisory first, enforcement later.** Sprint 11 ships in `flag`
  mode. Sprint 12 considers the `redact` flip after real-world
  false-positive baseline is collected.

## Decision

Introduce:

1. A new audit event action literal **`output_safety_flag`** (v2,
   additive per ADR-005 §1). Emitted by the PostToolUse Agent hook
   whenever the scanner finds at least one match in the agent's
   response.
2. A new canonical pattern library `_lib/pii_patterns.py` with a
   strict 5-step **scanner pipeline** (SCANNER_PIPELINE / scan).
3. A new PostToolUse Agent hook **`check_output_safety.py`** that is
   advisory-only and opt-in (Phase 13 closeout wires it into
   `.claude/settings.json`).
4. ADR-011 `injection_flag` and ADR-036 `output_safety_flag` are
   complementary and both use the same audit stream v2 schema
   (family_counts, match_count, bytes_scanned, truncated,
   snippet_preview).

### Scanner pipeline (MANDATORY ORDER, H14)

The five steps are inseparable — skipping any one is an unpassable
bypass:

1. **NFKC normalization** — `unicodedata.normalize('NFKC', text)`.
   Collapses full-width / compatibility glyphs. Without this,
   `ｓｋ－abcdef...` (full-width chars) defeats a literal `sk-` regex.
2. **Strip invisibles** — zero-width (U+200B–U+200F), bidi overrides
   (U+202A–U+202E), isolate marks (U+2066–U+2069), BOM (U+FEFF), and
   C0/C1 control chars except `\n` / `\t` / `\r`. Without this,
   `s\u200bk-...` defeats a literal `sk-` regex.
3. **Bounded base64 decode (depth = 1)** — for every token matching
   `[A-Za-z0-9+/=_\-]{40,}` with Shannon entropy ≥ 4.0, decode once.
   Inflation cap: decoded bytes ≤ 4× encoded bytes (defeats
   decompression-bomb-style abuse; base64 itself inflates by 4/3).
   Strictly one level; decoded fragments are NOT re-scanned for
   further base64. Both standard and urlsafe alphabets tried.
4. **Shannon entropy** — any 24+ character run from
   `[A-Za-z0-9+/_\-]` with entropy > 4.5 bits/char surfaces in the
   `entropy` family (credential-shape candidate). Computed with
   `math.log2`, stdlib-only.
5. **Canonical regex** — the seven families below, applied to the
   post-steps-1-4 augmented text.

Each step records its count in `ScanResult.pipeline_step_counts` so
the audit / observability layer can confirm the pipeline actually ran.

### Pattern families (7)

| Family | Pattern sketch | Gate |
|---|---|---|
| `api_key` | `sk-*`, `ghp_*`, `github_pat_*`, `AKIA[0-9A-Z]{16}`, `aws_(secret\|session)_key=*` | length/alphabet |
| `jwt` | `eyJ...\....\....` (three base64url segments) | pattern only |
| `bearer` | `Bearer <token>` | pattern only |
| `cpf_cnpj` | Brazilian CPF / CNPJ digit shape | **context keyword** (`cpf`/`CPF`/`cnpj`) within 40 chars |
| `credit_card_pan` | Visa/MC/Amex/Discover PAN shape | **Luhn checksum validates** |
| `email_in_log` | RFC email shape with bounded quantifiers | **context keyword** (`user`/`email`/`login`/`mail`) within 20 chars |
| `entropy` | 24+ char high-entropy token not already covered by regex | Shannon > 4.5 |

**Context gating for CPF/CNPJ/email is NOT optional.** Raw 11/14
digit sequences appear frequently in routine log output (order IDs,
tracking numbers, SKUs). Email addresses appear in docs and code
comments. Context gates are the primary false-positive defense.

### Performance ceiling

The scanner bounds input at 1 MiB per call (`_MAX_BYTES`). All
regex quantifiers are upper-bounded to prevent catastrophic
backtracking (e.g. the email local-part is `{1,64}` not `+`). An
early short-circuit on email scanning (skip if `@` not in text)
protects the hot path.

Phase 10 (nightly profile) will measure p99 against the H15 target
of <50ms/scan. Phase 9 ships measure-only; Phase 10 rotates if the
ceiling is breached.

### Modes + kill switch

Environment variables:

- **`CEO_OUTPUT_SAFETY_MODE`** — `flag` (default, Sprint 11) or
  `redact`. In redact mode, matches are replaced with
  `[REDACTED:FAMILY]` in the audit snippet; the emitted event carries
  `redaction_applied=true`.
- **`CEO_SOTA_DISABLE=1`** (consensus S4) — full kill switch. Hook
  returns `{"decision":"allow"}` and emits zero events.

### Audit event schema

```json
{
  "ts": "2026-04-14T15:00:00Z",
  "event_schema": "v2",
  "action": "output_safety_flag",
  "source": "agent:<tool_name>",
  "family_counts": {"api_key": 1, "jwt": 1},
  "match_count": 2,
  "bytes_scanned": 1234,
  "redaction_applied": false,
  "triggered_by_tool": "Agent",
  "snippet_preview": "<redacted, ≤200 chars>",
  "truncated": false,
  "session_id": "<optional>",
  "project": "<CLAUDE_PROJECT_DIR>"
}
```

### Sprint 11 → Sprint 12 flip criterion

- **Flag default (Sprint 11):** output preserved; audit event only.
- **Redact flip (Sprint 12 candidate):** replace matches in-scope.
  Flip criterion: ≤1 false-positive per 1000 real-world outputs
  across a 30-day observation window. Flip is Owner-gated and
  recorded as an ADR amendment, not a silent default.

## False-positive test discipline

`tests/fixtures/output_safety/` contains:

- **Positive (15):** one per family plus NFKC / zero-width / bidi /
  base64-encoded-secret attack variants. Every one MUST produce at
  least one match of the expected family.
- **Control (5):** random hash log (sha256 hex), docs mentioning
  "email" without an address, partial JWT (2 segments only), raw
  11-digit sequence with no CPF context, credit-card-shape with
  invalid Luhn. Every one MUST NOT match.

Regression policy: when adding a pattern family, the CI must show
positive-fixture match AND control-fixture no-match before the
change can merge.

## Non-goals

- **Does NOT scan inputs.** That is `check_read_injection.py`'s job
  (ADR-011). The two hooks are complementary.
- **Does NOT block.** Advisory Sprint 11. Even in enforcement mode
  (future), the hook blocks only via a separate ADR.
- **Does NOT mutate the agent's `tool_response`.** Claude Code hooks
  cannot retroactively rewrite a PostToolUse response; the
  `redaction_applied` flag marks intent in the audit event and the
  snippet_preview is what's persisted, not the tool_response itself.
- **Does NOT stop at the scan boundary.** Matches always audit-emit
  (via `emit_output_safety_flag`); consumers handle downstream
  redaction / alerting / pruning.

## Consequences

### Positive

- One audit channel for input (`injection_flag`) and output
  (`output_safety_flag`) observability, identical tooling path.
- Pipeline order is reviewable in code (`_lib/pii_patterns.py`
  `scan()` function reads top-to-bottom: NFKC → strip → b64 →
  entropy → regex). H14 is enforced structurally, not by comment.
- New pattern families are PATCH-version events.
- Fixture-first discipline (15 positive + 5 control) prevents
  greedy-pattern regressions.

### Negative

- Scanner adds PostToolUse latency per Agent invocation. Bounded at
  1 MiB input and 353ms per 1 MiB worst-case (profiled on macOS
  Python 3.9). Phase 10 will profile in CI and flip measure-only
  → baseline per ADR-024 criteria.
- `family_counts` is a free-form map (per ADR-005 forward-compat
  clause). Consumers that enumerate families must tolerate new ones.
- False-positives are possible even with context gating —
  `cpf_cnpj` / `email_in_log` rely on nearby keywords, but a log
  line mentioning "email" in a non-PII context near an unrelated
  address WILL match. Sprint 12 flip criterion explicitly guards
  against greedy redaction.

### Neutral

- Hook is opt-in via `.claude/settings.json` PostToolUse Agent
  matcher. Phase 13 closeout wires it; adopters can disable by
  setting `CEO_SOTA_DISABLE=1` or removing the hook entry.

## Blast radius

**L2** (pattern library + PostToolUse hook + new audit action +
tests + fixtures + SPEC schema note).

- `_lib/pii_patterns.py` (NEW)
- `.claude/hooks/check_output_safety.py` (NEW — PostToolUse Agent)
- `_lib/audit_emit.py` — `emit_output_safety_flag` + action literal
  (CEO pre-staged in Phase 0 closeout)
- `.claude/hooks/tests/test_pii_patterns.py` (NEW)
- `.claude/hooks/tests/test_check_output_safety.py` (NEW)
- `.claude/hooks/tests/fixtures/output_safety/` (NEW — 15 positive + 5 control)
- `.claude/settings.json` — Phase 13 closeout wires `matcher: "Agent"`
- `SPEC/v1/audit-log.schema.md` — Phase 13 closeout appends action
  row (additive, v2)

**Reversibility:** HIGH — action literal can be deprecated in a
future MAJOR; the hook is opt-in (removal is invisible to
non-adopters); `CEO_SOTA_DISABLE=1` is a runtime kill switch.

## Transition Log

*This appendix follows ADR-041 Transition Log Convention. Each row records
a state transition triggered by a flip criterion in its window.*

| Date | From-State | To-State | Evidence-Link | PR-Ref | Signer |
|------|------------|----------|---------------|--------|--------|
| _(empty — first flip pending per PLAN-012)_ | | | | | |

## References

- ADR-005 (event stream v2 contract, additive evolution clause)
- ADR-007 (SemVer + RC policy — drives v2 additive patch bump)
- ADR-011 (injection_flag action, ancestor schema shape)
- ADR-019 (advisory → enforcement lifecycle precedent —
  output-safety will follow the same gate pattern in Sprint 12 IFF
  baseline supports flip)
- ADR-024 (perf-baseline policy — Phase 10 profile ceiling)
- PLAN-011 Phase 9 (this phase)
- Consensus round-1 H14 (scanner pipeline mandate)
- Consensus round-1 H15 (performance ceiling companion)
- Consensus round-1 S4 (CEO_SOTA_DISABLE contract)
- Consensus round-1 S5 (per-test behavior assertion discipline)

## Enforcement commit

`b768b5327298` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
