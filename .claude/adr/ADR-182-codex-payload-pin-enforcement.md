---
id: ADR-182
title: Codex payload pin + verify-then-invoke enforcement
status: PROPOSED
proposed: 2026-07-28
related_plan: [PLAN-163, PLAN-081, PLAN-156]
related_adr: [ADR-111, ADR-117, ADR-161]
supersedes: "ADR-111 §pin clauses + PLAN-081 Phase 6-bis launcher-hash pin (codex-cli-binary-sha256.txt)"
enforcement_commit: <set at the GATE-PIN ceremony commit>
---

# ADR-182 — Codex payload pin + verify-then-invoke enforcement

> Status: PROPOSED — to be ACCEPTED at the PLAN-163 GATE-PIN ceremony
> (a SEPARATE, Owner-signed sentinel ceremony that lands the pin-pack:
> manifest + hook + gate + validator + this ADR atomically).

## Context — the pin attested the wrong artifact

The T-8 supply-chain defense (PLAN-081 Phase 6-bis,
`docs/CROSS-LLM-THREAT-MODEL.md §T-8`) pinned
`shasum -a 256 $(which codex)` in
`.claude/governance/codex-cli-binary-sha256.txt`. That procedure has a
structural flaw discovered during the PLAN-163 S282 cross-vendor review
and proven by probe (`.claude/plans/PLAN-163/probes/payload-sha-evidence.md`):

- `which codex` is an npm symlink to the JS **launcher**
  (`@openai/codex/bin/codex.js`). `shasum` follows the symlink and
  hashes the launcher.
- The launcher's `findCodexExecutable()` resolves and spawns a NATIVE
  per-platform payload at
  `@openai/codex-<platform>/vendor/<targetTriple>/bin/codex`
  (~260 MB Rust binary). **That payload is what executes; it was never
  hashed.**
- The launcher JS is version-stable: the pin minted for codex-cli
  **0.144.1** (SENT-CX-PIN, S269) still byte-matches under **0.144.6**,
  so the 0.144.1 → 0.144.6 payload change passed the "pin" with zero
  gate trips.

Compounding this, runtime enforcement was a stub: the pin was consulted
only by `pair-rail-gate.sh` pre-flight intent (itself a Phase-7
"documented intent — NOT YET IMPLEMENTED" stub), never at
`check_pair_rail.py` invocation time — and even a correct pre-flight
hash of one path does not constrain which file the launcher later
spawns.

## Decision

### 1. Pin the payload, per targetTriple — `codex-cli-pin-manifest.json`

`.claude/governance/codex-cli-binary-sha256.txt` is RETIRED in place as
a comment-only tombstone (path kept on disk, still canonical- and
kernel-guarded, so historical verdicts keep a referent and a
launcher-hash "pin" cannot be silently revived there). The new trust
root is `.claude/governance/codex-cli-pin-manifest.json`, exact schema:

```json
{
  "schema": 1,
  "package_version": "<semver>",
  "npm_integrity": "<sri>",
  "payloads": {
    "<targetTriple>": {
      "path": "@openai/codex-<platform>/vendor/<targetTriple>/bin/codex",
      "sha256": "<64-hex>"
    }
  }
}
```

- `package_version` — the `@openai/codex` semver the payload shas were
  recorded against (must sit inside the `codex-cli-pin.txt` range).
- `npm_integrity` — registry `dist.integrity` (SRI) of the platform
  package artifact, recorded as provenance linking the local payload to
  the registry artifact.
- `payloads.<triple>.path` — the package-relative payload path exactly
  as the launcher resolves it; `payloads.<triple>.sha256` — sha256 of
  those payload bytes.

The manifest is canonical-guarded (`.claude/governance/*.json` glob in
`_CANONICAL_GUARDS`) and enrolled in `check_arbitration_kernel.py
_KERNEL_PATHS` in the same wave that creates it (PLAN-156 SENT-GK-0
precedent).

### 2. Runtime enforcement — verify-then-invoke in `check_pair_rail.py`

`_resolve_codex_bin()` no longer returns whatever `$PATH` yields. It:

1. finds the `codex` launcher on `$PATH` (unchanged discovery);
2. mirrors the launcher's `findCodexExecutable()` (require.resolve
   walk-up over `node_modules/` joining the manifest entry `path`, plus
   the `<pkg>/vendor/<triple>/bin/codex` fallback) to resolve the
   native payload for the host targetTriple;
3. computes sha256 of the payload and compares it against
   `payloads[<triple>].sha256`;
4. returns the **verified payload path**, and `_invoke_codex_review()`
   execs EXACTLY that path (`cmd = [verified_native_path, ...]`) —
   the artifact that was hashed is the artifact that runs. No launcher
   indirection remains between verification and execution.

Failure classification (follows the hook's standing doctrine —
fail-open on INFRA, fail-closed on security input, PLAN-152 debate C4):

| Arm | Class | Behavior |
|---|---|---|
| manifest missing / unreadable / bad JSON-shape | INFRA | `CodexUnavailable` → fail-OPEN advisory (same as missing binary today) |
| launcher not on PATH / payload file not resolvable | INFRA | `CodexUnavailable` → fail-OPEN advisory |
| targetTriple underivable or absent from manifest | SECURITY | `CodexPinMismatch` → **fail-CLOSED `{decision: block}`** |
| manifest entry malformed (non-64-hex sha, empty path) | SECURITY | `CodexPinMismatch` → **fail-CLOSED block** |
| payload sha256 != manifest entry | SECURITY | `CodexPinMismatch` → **fail-CLOSED block** |

Rationale for the fail-closed arms: a hash mismatch is exactly the T-8
compromise signal; degrading it to advisory reproduces the silent
0.144.1→0.144.6 pass this ADR exists to close. The block carries audit
`pair_rail_codex_pin_mismatch` (breadcrumb until the audit-register
ceremony promotes the action) and pairs the invocation's
`pair_rail_review_expected` emit as a Case-B `pair_rail_case`.
No environment variable relaxes the sha check. `CEO_PAIR_RAIL_CODEX_BIN`,
if set, is routed through `verify_codex_payload(payload_override=…)` — the
pointed binary is hashed and compared to the manifest entry for the current
triple exactly as the derived payload would be; a mismatch (or a set-but-
missing override) fails CLOSED (`CodexPinMismatch` → `{decision: block}`),
never trusted on existence alone. `CEO_PAIR_RAIL_PIN_MANIFEST` /
`CEO_PAIR_RAIL_TARGET_TRIPLE` are test seams honoured ONLY under
`CEO_PAIR_RAIL_TEST_MODE=1`; on the live path they are ignored (real host
triple derivation / repo-canonical manifest), so they cannot redirect
verification to an attacker-controlled manifest or triple in production.
The only true bypass is the global `CEO_PAIR_RAIL_DISABLE=1` kill-switch.

### 3. One verification kernel, three consumers

`verify_codex_payload()` in `check_pair_rail.py` is the single
algorithm; consumers never re-implement it:

- **Runtime hook** — §2 above.
- **`pair-rail-gate.sh` Gate 4** — replaces the semver-only stub with
  `python3 .claude/hooks/check_pair_rail.py --verify-codex-pin
  "$CODEX_PATH"`; exit 0 = verified, 1 = mismatch/triple-missing,
  3 = infra. Owner pre-flight is strict: any non-zero fails the gate.
- **Release gate** — §4 below (compares DECLARED envelope values
  against the manifest; the runner does not hash a local codex).

### 4. Verdict-envelope wire-shape (exact — grok r4 nit)

The release verdict envelope (`pair-rail-verdict-<tag>.md` YAML block)
carries two NEW scalar fields under `tool_versions`:

```yaml
tool_versions:
  codex_cli: <semver, codex-cli-pin.txt range — unchanged>
  codex_target_triple: <targetTriple of the generating run, e.g. aarch64-apple-darwin>
  codex_payload_sha256: <64-hex sha256 of the NATIVE payload for that triple>
```

`validate-pair-rail-verdict.py --codex-pin-manifest-file` asserts
`codex_payload_sha256 == payloads[codex_target_triple].sha256`.
Fail-CLOSED (`VERDICT_INVALID`, exit 3) on: missing either field,
triple absent from the manifest, malformed manifest entry, or sha
mismatch. Manifest file unreadable → infra (exit 1; release.yml
decides via `CEO_PAIR_RAIL_VERDICT_OPTIONAL`, default hard-block).
`codex_cli_binary_sha256` (launcher hash) is DEPRECATED: not declared
in new verdicts; the legacy `--codex-cli-binary-sha256-file` check
remains wired only so pre-ADR-182 tags keep their semantics (the
tombstone pin file parses as "no pin" → advisory skip).

### 5. Pin update ceremony

After a legitimate codex upgrade, the Owner:

1. runs `python3 .claude/hooks/check_pair_rail.py --verify-codex-pin`
   — the JSON output names the resolved payload, its sha256, and the
   triple (expected to report `mismatch` against the old pin);
2. fetches `npm view @openai/codex@<ver>-<platform> dist.integrity`
   (dereference the optional-dep alias — the platform artifact is
   published as `@openai/codex@<ver>-<platform>`);
3. edits `codex-cli-pin-manifest.json` (sentinel-gated: canonical +
   kernel guard) with `package_version`, `npm_integrity`, and the new
   per-triple `sha256`; bumps `codex-cli-pin.txt` if the semver range
   moved;
4. re-runs `--verify-codex-pin` (must exit 0) and
   `pair-rail-gate.sh --phase 6`;
5. applies the ADR-111 §2 reopen trigger unchanged: if a Phase-4 corpus
   re-run shifts catch_rate >5pp under the new binary, corpus reopen +
   ADR amendment.

### 6. Relationship to ADR-111 (and the ADR-120 ledger bug)

- This ADR **supersedes the pin-procedure clauses** that shipped under
  the PLAN-081 Phase 6-bis umbrella and are referenced in ADR-111 §2
  ("Codex CLI version bump" reopen criterion's pin mechanics) and in
  the retired `codex-cli-binary-sha256.txt` header: everywhere those
  texts say "pin = `shasum -a 256 $(which codex)`", the ADR-182 payload
  manifest + ceremony above now governs. ADR-111's **locked-corpus
  substance is NOT superseded** and ADR-111 keeps its id per ADR-117.
- **ADR-120 is the PII core-promotion ADR** (renamed FROM the id
  ADR-111 per ADR-117; see `.claude/adr/README.md` §collision
  patterns). The `superseded_by: ADR-120` frontmatter that
  `ADR-111-locked-corpus-governance.md` carried was a **ledger bug** —
  it conflated the rename of the *other* ADR-111 file with a
  supersession of the locked-corpus record (whose substance appears
  nowhere in ADR-120). The pin-pack repairs ADR-111's frontmatter
  (status back to ACCEPTED, `amended_by: ADR-182`); ADR-120 itself is
  deliberately NOT touched.

## Consequences

- (+) The pin now attests the bytes that execute; a payload swap under
  a stable launcher fails CLOSED at the next L3+ invocation, at Owner
  pre-flight, and at tag time — three independent consumers of one
  kernel.
- (+) The failure mode for pin-lag moved from invisible (stale pin
  silently matching the launcher) to visible friction (a block naming
  the re-pin ceremony).
- (−) Every L3+ Codex invocation now hashes a ~260 MB file before
  exec. This is a deliberate governance cost consistent with the
  repo's no-speed-claim posture; if it proves operationally heavy, a
  follow-up may cache by (payload path, mtime, size) — fail-closed on
  any cache doubt — via a new amendment, not silently.
- (−) Hosts whose targetTriple is not enumerated in the manifest
  fail CLOSED (adopters must run the ceremony per platform they use).
- Residual: hash→exec TOCTOU on one already-resolved absolute path
  (accepted; no launcher indirection remains); `validate-governance.sh`
  REQUIRED_FILES does not yet assert the manifest exists (§Deferred —
  release.yml step 15 is the backstop).

## References

- `.claude/plans/PLAN-163/probes/payload-sha-evidence.md` — launcher
  algorithm transcription + hash evidence (S283+, 2026-07-28).
- `.claude/plans/PLAN-163/probes/pin-manifest-draft.json` — first
  manifest instance (0.144.6, aarch64-apple-darwin).
- `docs/CROSS-LLM-THREAT-MODEL.md` §T-8 (updated in the same pack).
- ADR-111 (locked corpus — pin clauses superseded here), ADR-117
  (collision-rename policy), ADR-161 (codex harness capability matrix,
  per-bump re-verification checklist).
