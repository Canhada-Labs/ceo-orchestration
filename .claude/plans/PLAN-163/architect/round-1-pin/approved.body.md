---
plan: PLAN-163
round: 1-pin
type: architect-sentinel
segment: GATE-PIN-CODEX-PAYLOAD
---

# PLAN-163 GATE-PIN — codex payload-pin ceremony (Owner sentinel)

Anchor-SHA: __ANCHOR_SHA__

Approved-By: @Canhada-Labs (Owner GPG — signed inline by the ceremony)
Approved-At: __APPROVED_AT__

## What this sentinel authorizes (sign this KNOWINGLY)

FIRST of the TWO declared PLAN-163 ceremonies (gate order: GATE-PIN →
GATE-V2 fresh-liveness → 3-vendor pack review → pack GPG ceremony).
Scope = the pin-pack ONLY (20 files, `staged/pin-pack/MANIFEST.sha256`,
tracked twin `inputs-pin.sha256`). It lands ADR-182 (codex payload-pin +
verify-then-invoke enforcement) end-to-end:

1. **Supply-chain fix (T5.2 / G13):** the old sha pin attested the npm
   JS *launcher* (`codex.js`), not the native payload that executes —
   the 0.144.1→0.144.6 payload bump passed the "pin" without any gate
   trip. `codex-cli-binary-sha256.txt` becomes a TOMBSTONE; the new
   authority is `codex-cli-pin-manifest.json` (schema 1, per-targetTriple
   payload sha256, npm dist.integrity provenance).
2. **Enforcement in the LIVE rail:** `check_pair_rail.py` now resolves
   the native payload, verifies its sha256 against the manifest BEFORE
   the subprocess (block on mismatch, fail-closed on triple-missing) and
   invokes EXACTLY the verified path (verify-then-invoke — no
   verify-A-execute-B gap). `--verify-codex-pin` CLI shares the same
   verification surface with `pair-rail-gate.sh` Gate 4 (unstubbed).
3. **Consumers migrated:** `validate-pair-rail-verdict.py` (+ tests,
   `--codex-pin-manifest-file`), `release.yml` (verdict envelope carries
   payload sha + targetTriple; legacy semantics preserved for
   pre-ADR-182 tags), verdict template, threat-model doc §ceremony/runtime.
4. **Ledger repair:** ADR-111 frontmatter/index repair — the false
   "SUPERSEDED by ADR-120" relation is removed (ADR-120 is the PII ADR;
   locked-corpus kept id 111 per ADR-117). ADR-182 is a NEW ADR:
   ADR count 180 → **181** (CLAUDE.md/docs count surfaces update in the
   session-closeout commit BEFORE push — cache discipline).

ONE kernel surface in this scope, applied under
`CEO_KERNEL_OVERRIDE=PLAN-163-T5-CODEX-PIN`: `.github/workflows/release.yml`.
The Owner-shell apply route (cp/git) does not trip in-session canonical
hooks — this signed sentinel IS the authorization record (S261 precedent);
the kernel-override export is the ADR-031 declaration.

Post-ceremony this sentinel's commit timestamp is the GATE-V2 ANCHOR:
the fresh-liveness proof counts ONLY events after it (plan §Gates,
S283 any-in-window correction).

## Scope

Scope:
  - .claude/adr/ADR-111-locked-corpus-governance.md
  - .claude/adr/ADR-182-codex-payload-pin-enforcement.md
  - .claude/adr/README.md
  - .claude/governance/README.md
  - .claude/governance/codex-cli-binary-sha256.txt
  - .claude/governance/codex-cli-pin-manifest.json
  - .claude/governance/pair-rail-verdict-template.md
  - .claude/hooks/check_arbitration_kernel.py
  - .claude/hooks/check_pair_rail.py
  - .claude/hooks/tests/test_check_pair_rail.py
  - .claude/hooks/tests/test_check_pair_rail_golden.py
  - .claude/hooks/tests/test_check_pair_rail_matrix.py
  - .claude/hooks/tests/test_check_pair_rail_payload_pin.py
  - .claude/scripts/check-substrate-watch.py
  - .claude/scripts/local/pair-rail-gate.sh
  - .claude/scripts/tests/test_check_substrate_watch.py
  - .github/scripts/tests/test_validate_pair_rail_verdict.py
  - .github/scripts/validate-pair-rail-verdict.py
  - .github/workflows/release.yml
  - docs/CROSS-LLM-THREAT-MODEL.md
