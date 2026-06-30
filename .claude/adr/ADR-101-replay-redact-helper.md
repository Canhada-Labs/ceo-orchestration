# ADR-101 — Replay capture redaction helper (`replay_redact`) + R9 LIVE LGPD leak fix

**Status:** ACCEPTED
**Date:** 2026-05-03
**Enforcement commit:** `41c4ae5` (PLAN-070-071 bundle, v1.13.0)

## Decision drivers

- **R9 LIVE LGPD leak (S79 Round 1 P0-SEC-01)**: at HEAD pre-Phase-1, `replay-session.py:354 + :477` wrote `spawn_copy: spawn` verbatim into `state/replay-out/spawn-NNNN.json`, embedding OS-username paths, free-form `desc_preview` strings, and other PII. Live audit-log inspection confirmed `agent_spawn` events on this very repo carry `project: "/Users/devuser/..."` — LGPD Art. 5º OS-username PII leaking on every dry_run/execute artifact write.
- **PLAN-068 Round 1 Sec VETO-CONDITIONAL**: 6 lift conditions (SEC-R1-P0-01 → SEC-R1-P0-06). Track-2 (replay-as-fixture) lifted to PLAN-069 with the conditions intact.
- **`_lib/redact.py` is the wrong primitive**: 12-pattern input-side secret-scrub (no NFKC, no Luhn, no CPF/CNPJ context-gating, no `os_path` family). Phase 0.5 PoC measured Pass 1 (`redact.py`) missing 3 of 5 PII classes deterministically.
- **Stdlib-only at runtime** per PLAN-068 §0.4 R1 + ADR-085 Claude-only positioning. No new external dependencies.

## Context

PLAN-068 Round 1 split produced PLAN-069 (replay extension) carrying 6 Security lift conditions. Phase 0 gap-analysis verdict was `LARGE-GAP`: existing `replay-session.py` (752 LoC, ADR-046, PLAN-014 F.1b) is a **forward replay tool** consuming `audit-log.jsonl` directly with no capture-as-fixture mode, no PII redaction (`redacted_count` at line 705-709 is a proxy/advisory event count, NOT a fresh redaction pass), no `prompt_sha256` salt rebind, and no `replay_capture_*` audit actions.

Phase 0.5 PoC at `.claude/plans/PLAN-069/phase-0-5-poc/` (3-pass × 5-class measurement) confirmed:
- Pass 0 (no-op baseline mirroring R9 raw-write): 10/10 OS paths leak + 7 secret/LGPD instances
- Pass 1 (`_lib/redact.py`): missed 3 of 5 classes (Class A OS path, Class D CPF, Class E PAN)
- Pass 2 (`pii_patterns.SCANNER_PIPELINE` mode='redact'): eliminated 4 of 5; Class A OS path **still leaks** because pii_patterns has no `os_path` family

**Conclusion**: SCANNER_PIPELINE is the correct primitive but requires a **thin OS-username preprocessor** (POSIX/Linux/macOS-scratch/Windows/Volumes) running BEFORE the pipeline.

## Decision

Adopt a new helper module at `.claude/hooks/_lib/replay_redact.py` (canonical-guarded; Wave D ceremony moved it from `.claude/scripts/replay/replay_redact_lib.py`) wrapping the canonical `pii_patterns.SCANNER_PIPELINE` with:

1. **OS-username preprocessor** `_strip_os_username(text)` — NFKC-normalize then regex-replace POSIX `/Users/<NAME>/`, Linux `/home/<NAME>/`, macOS scratch `/private/var/folders/<...>`, Windows `C:\Users\<NAME>\` (both backslash and forward-slash variants), network `/Volumes/<NAME>/`. Token shape mirrors `pii_patterns._apply_redactions` (`[REDACTED:OS_PATH]`).
2. **`redact_text(text, stats=None)`** — preprocess → SCANNER_PIPELINE(mode='redact') → return `redacted_text`. Fail-CLOSED via `RedactionFailure` on any pipeline exception.
3. **`redact_event(event, nonce=None, stats=None)`** — recursive walk of dict/list/str leaves. With `nonce`: HMAC-rebinds keys in `_HASH_FIELDS_TO_REBIND` = frozenset({`prompt_sha256`, `desc_hash`, `payload_hash`}) using `HMAC-SHA256(nonce, field_name || 0x1F || value)` truncated to 16 hex chars. Without `nonce` (R9 dry_run/execute path): hash fields pass through unchanged; leaf strings still go through `redact_text`.
4. **Per-fixture HMAC salt rebind** — `new_fixture_salt()` returns 32 bytes via `secrets.token_bytes` (CSPRNG). Stored in `_meta.salt_b64` on capture; never reused, never persisted outside the fixture.
5. **`build_meta(...)` + `verify_fixture_meta(...)`** — fixture trust boundary. Schema `v2.16`. Required fields: `_meta`, `schema`, `salt_b64`, `pii_patterns_version`, `replay_redact_version`, `captured_at`, `plan_id`, `original_session_id`, `event_count`, `captured_by_hash` (= SHA-256 over ordered redacted lines, P1-SEC-01 forgery defense). `verify_fixture_meta` is fail-CLOSED; rejects schema-newer-than-current, malformed base64 (catching `binascii.Error` per Wave B QA P1-B finding), wrong nonce length, missing version fields.
6. **`post_load_defense_in_depth(event)`** — runs `pii_patterns.scan(mode='flag')` over every string leaf; returns `(clean, leaks)` for caller to fail-CLOSED on tampered fixtures.

`replay-session.py` extension (non-canonical, no ceremony):
- `--mode=capture` produces redacted JSONL fixture under `$CLAUDE_PROJECT_DIR`. Refuses out-of-project `--out`, refuses symlinks at any path component (P1-SEC-04), refuses `--audit-log` outside `$CLAUDE_PROJECT_DIR/.claude/projects/` (P1-SEC-02).
- `--mode=replay-fixture` reads + verifies fixture; runs post-load defense-in-depth.
- `--redact-pii` parser accepts EXACT literal `enforced` only; any other token → `EXIT_USAGE` (Round 1 condition #2).
- `--allow-live` + `--owner-confirm` HARD-IGNORED in capture/replay-fixture modes; passing them → `EXIT_USAGE` before any FS write (Round 1 P0-SEC-04).
- **R9 fix at lines 354 + 477**: `spawn_copy` field now routes through `_redact_spawn_for_artifact(spawn)` which calls `redact_event(spawn, nonce=None)` and returns `{_redaction_failed: True, ...}` sentinel envelope on `RedactionFailure` (fail-CLOSED).

## Audit-action registration (Wave D, this ADR)

The 2 new audit-log actions — `replay_capture_started` and `replay_capture_completed` — are registered across all 5 byte-identity surfaces:

1. `audit_emit._KNOWN_ACTIONS` set (canonical; 95 → 97 entries)
2. `audit_emit.emit_replay_capture_started` + `audit_emit.emit_replay_capture_completed` functions (canonical)
3. `test_audit_emit_api_contract.py::_EXPECTED_PUBLIC_SYMBOLS` (50 → 52 emitters)
4. `test_audit_emit_api_contract.py::_EXPECTED_KNOWN_ACTIONS_SHA256` (recomputed) + `test_known_actions_count_fixed` (95 → 97)
5. `SPEC/v1/audit-log.schema.md` v2.16 — 2 new event-shape rows + version-history row + version-label disambiguation row

`replay-session.py:capture_run` wires the new emit functions in capture mode (replacing the prior `_emit_completed` reuse-of-replay_completed).

## Round 1 lift conditions — disposition

| # | Condition (verbatim) | Codified at | Test |
|---|---|---|---|
| 1 | `_lib/replay_redact.py` (NEW) wires `pii_patterns.SCANNER_PIPELINE(mode='redact')` over EVERY string field; fail-CLOSED on any pipeline exception. | `replay_redact.py:_strip_os_username, redact_text, redact_event, RedactionFailure` | `test_replay_redact_lib.py` Sections A+B+C |
| 2 | No `--redact-pii=skip` / equivalent. CLI parses single literal `enforced` only; any other token → `EXIT_USAGE`. | `replay-session.py:main` capture pre-flight gate | `test_replay_session_capture.py` H-01..H-03 |
| 3 | Per-fixture HMAC-SHA256 salt rebind: `os.urandom(32)` nonce in fixture `_meta.salt_b64`, formula `HMAC(nonce, field_name \|\| 0x1F \|\| value)`, applied to every content-hash field. | `replay_redact.py:new_fixture_salt, rebind_hash, _HASH_FIELDS_TO_REBIND` | `test_replay_redact_lib.py` Sections C+D |
| 4 | ≥56 adversarial fixtures (7 × 8 categories) with paired positive + negative controls. | `.claude/scripts/replay/tests/fixtures/<56 .jsonl>` | `test_replay_redact_lib.py::TestAdversarialFixtures` parametrized |
| 5 | New `replay_capture_started` / `replay_capture_completed` actions registered across all **5 byte-identity surfaces** + R9 `spawn_copy` raw-write fix bundled in same PR. | **R9 fix shipped Wave A** (`replay-session.py:_redact_spawn_for_artifact`); audit action registration **Wave D ceremony** (canonical-guarded `audit_emit.py` + SPEC + 2 emit functions + 2 byte-identity test surfaces) | R9 covered by `test_replay_session_capture.py::TestR9DryRunRedaction`; action wire validated by `test_audit_emit_api_contract.py` |
| 6 | Replay-fixture trust boundary: HMAC chain verify + salt-nonce presence/length verify + schema-version-not-newer + post-load `pii_patterns.scan(mode='flag')` defense-in-depth. | `replay_redact.py:verify_fixture_meta, post_load_defense_in_depth` + `replay-session.py:replay_fixture_run` | `test_replay_redact_lib.py` Sections E+F+G + `test_replay_session_capture.py` I-01..I-06 |

**6/6 conditions codified post-Wave-D ceremony.**

## Consequences

### Positive
- R9 LIVE LGPD leak closed at HEAD on all dry_run + execute artifact writes
- Capture mode produces a redacted, salt-rebound, content-hashed fixture suitable for committed regression corpora without cross-corpus oracle (Round 1 P0-SEC-03 closed)
- Same-LLM same-installation correlation defeated by per-fixture nonce + HMAC keyed-MAC (RFC 2104 §5 truncation safe)
- 89 tests at 97.02% combined coverage on the new lib (line 96.9% / branch 97.1%); 56 adversarial fixtures with paired positive/negative controls; 3 property-based tests with explicit seeds; 3-run determinism verified
- Phase 0.5 PoC + reproducer-notes preserved at `.claude/plans/PLAN-069/phase-0-5-poc/` for future regression measurement

### Negative
- 1 Wave D Owner GPG passphrase ceremony required to move `replay_redact_lib.py` → `.claude/hooks/_lib/replay_redact.py` (canonical), register `replay_capture_started` / `replay_capture_completed` in `audit_emit._KNOWN_ACTIONS` (canonical), bump SPEC schema (canonical), and update test byte-identity surface (canonical). Single ceremony, atomic blast radius.
- Two version fields (`pii_patterns_version` + `replay_redact_version`) in fixture `_meta` per Phase 0.5 §6 disposition — adopters must read both for forward-drift defense.
- Class A OS-path post-load detection requires either (a) producer-side preprocess discipline (current state — fail-CLOSED on capture, defense-in-depth on replay-fixture catches API keys / PAN / CPF but NOT OS paths), or (b) future addition of `os_path` family to `pii_patterns.py` (out of scope; canonical-guarded).
- Bare-username scalar fields (e.g. `"user": "Canhada-Labs"` without path-shaped wrapping) are NOT redacted — this is by-design (the preprocessor is path-shaped) and out of scope for PLAN-069 Phase 1. Adopters with high-PII bare-username fields must extend.

### Neutral
- The wrapper does NOT modify `pii_patterns.py` (canonical, audited surface). Round 1 P0-SEC-02 mandate: do not migrate functionality from forbidden `redact.py` into the wrapper; extend `pii_patterns` family list in a separate ADR if needed.
- Fixture schema version `v2.16` chosen to align with audit-log schema convention (S71 Wave D-4 schema v2.14 precedent + 2 increments — v2.15 was S76 audit-v3 skill-bootstrap closure).

## Alternatives considered

- **Option A — Use `_lib/redact.py` directly**: REJECTED. Phase 0.5 measured 3 of 5 PII classes leak past `redact.py` (no NFKC, no Luhn, no CPF/CNPJ, no os_path). PLAN-069 R1 P0-SEC-02.
- **Option B — Pure SHA-256 hash without HMAC nonce**: REJECTED. Plan IDs + agent slugs + `desc_preview` shapes are enumerable; offline brute-force trivial. HMAC keyed-MAC defeats it. PLAN-069 R1 P0-SEC-03.
- **Option C — Per-record salt instead of per-fixture**: REJECTED. Breaks intra-fixture correlation needed for divergence detection; same prompt twice should produce same hash within one fixture.
- **Option D — Per-installation salt (the existing `injection_salt.py`)**: REJECTED. A committed fixture would forever-stable-correlate with that installation's salt; if `~/.claude/projects/.../.salt` later leaks, every committed fixture's hashes become plaintext correlation keys. PLAN-069 R1 P0-SEC-03.
- **Option E — `--allow-prompts` env var instead of capture-mode-hard-ignore**: REJECTED. Passing `--allow-live --owner-confirm` in capture mode is inherently mode-collapse-ambiguous; HARD-IGNORE + EXIT_USAGE matches PROTOCOL.md fail-CLOSED-on-security-surface invariant.

## References

- PLAN-069 frontmatter `adrs_proposed: [ADR-101-snapshot-review-helper]` (renamed to `replay-redact-helper` to match shipped scope)
- Round 1 critique: `.claude/plans/PLAN-069/debate/round-1/security-engineer.md` (verdict VETO-CONDITIONAL with 6 lift conditions)
- Phase 0 gap-analysis: `.claude/plans/PLAN-069/gap-analysis.md` (LARGE-GAP verdict)
- Phase 0.5 PoC: `.claude/plans/PLAN-069/phase-0-5-poc/sec-s9-reproducer.py` + `REPRODUCER-NOTES.md`
- Wave A production: `.claude/scripts/replay/replay_redact_lib.py` (NEW, 463 LoC) + `.claude/scripts/replay/replay-session.py` (modified, +428 LoC)
- Wave B tests: `.claude/scripts/replay/tests/test_replay_redact_lib.py` (NEW, 886 LoC) + `.claude/scripts/replay/tests/test_replay_session_capture.py` (NEW, 484 LoC) + `.claude/scripts/replay/tests/fixtures/<56 .jsonl>` (NEW)
- Wave D ceremony: `.claude/plans/PLAN-073/OWNER-WAVE-D-CEREMONY.sh` + sentinel `.claude/architect/round-1-plan-069-wave-d/approved.md.asc`
- Parent: ADR-046 (replay deterministic harness, ACCEPTED 2026-04-20, PLAN-014 F.1b)
- Sibling ADR-077 (prompt-injection-class defense — fail-CLOSED security surface precedent)
- Sibling ADR-051 (skill-reference TOCTOU/symlink-rejection precedent — applied to `--out` / `--audit-log` / `--fixture` path resolution)
