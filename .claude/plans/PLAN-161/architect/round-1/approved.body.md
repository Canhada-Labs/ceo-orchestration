---
plan: PLAN-161
round: 1
type: architect-sentinel
segment: MAINTENANCE-SWEEP
---

# PLAN-161 consolidated maintenance sweep — Owner sentinel

Anchor-SHA: __ANCHOR_SHA__

Approved-By: @Canhada-Labs (Owner GPG — signed inline by the ceremony)
Approved-At: 2026-07-27

## Guard-class concentration (CF-5 / R-9 — sign this breadth KNOWINGLY)

This ONE sentinel authorizes edits across FIVE distinct guard classes in a
single ceremony (per-concern commit segmentation + CF-8 drop-out protocol):

1. **Harness deny baseline** (`.claude/settings.json` — KERNEL — + gate floor
   + template + fixtures): removes the 3 redundant `Write()` deny twins
   (OQ5(a), Security VETO lift condition (ii); old-CLI residual accepted).
2. **Installer / upgrade surface** (`upgrade.sh`, `install.sh`,
   `_framework_manifest_set.sh` + ADR-155 amend + SPEC/v1/install-cli.md):
   dry-run identity, exclusion predicate, and the FIRST hash-gated opt-in
   auto-delete capability on the installer surface (`--purge-misinstalled`,
   OQ1 Owner-ratified).
3. **Egress path** (`council-audit.js` + council docs/tests + grok template):
   grok-lane artifact transport (narrow transport exception; redaction-
   before-egress unchanged) + mechanical codex budget watchdog.
4. **CI gate** (`.github/workflows/validate.yml` — KERNEL — + ADR-163 amend
   + smoke-install wiring): perf-gate probe-gated 3rd attempt + backoff,
   timeout 16→28.
5. **Audit schema** (`.claude/hooks/_lib/audit_emit.py` — KERNEL — +
   SPEC/v1/audit-log.schema.md + golden + producers + boot classifier):
   two new typed actions (`codex_review_verdict`,
   `pair_rail_review_expected`), `_KNOWN_ACTIONS` 319 → 321.

THREE kernel segments, each its own commit under `CEO_KERNEL_OVERRIDE`:
`PLAN-161-C1-DENY-BASELINE` (settings.json), `PLAN-161-C4-PERF-GATE`
(validate.yml), `PLAN-161-C5-LIVENESS-ACTIONS` (audit_emit.py). The two
SPEC surfaces are deny-Edit and are applied via Bash under this sentinel.
ADR count stays 180 (all four ADR changes are in-place amendments).

## Scope

Scope:
  - .claude/settings.json
  - .claude/hooks/check_harness_config.py
  - templates/settings/settings.base.json
  - .claude/hooks/tests/fixtures/harness-config/settings/settings_good.json
  - .claude/hooks/tests/fixtures/harness-config/settings/settings_inline_secret.json
  - .claude/hooks/tests/fixtures/harness-config/settings/settings_noop_allowlisted.json
  - .claude/hooks/tests/fixtures/harness-config/settings/settings_noop_unlisted.json
  - .claude/hooks/tests/fixtures/harness-config/settings/settings_runtime_unresolvable.json
  - scripts/tests/test-install-deny-baseline.sh
  - .claude/adr/ADR-158-harness-config-gate.md
  - docs/PERMISSION-MODEL-DESIGN.md
  - docs/deny-baseline.md
  - scripts/upgrade.sh
  - scripts/install.sh
  - scripts/_framework_manifest_set.sh
  - .claude/adr/ADR-155-install-baseline-manifest.md
  - SPEC/v1/install-cli.md
  - .claude/workflows/council-audit.js
  - .claude/commands/council.md
  - scripts/tests/test-council-fixture.mjs
  - .claude/scripts/tests/test_council_verify_semantics.py
  - templates/grok/sandbox.toml.example
  - .github/workflows/validate.yml
  - .claude/adr/ADR-163-hook-latency-gate-percentile-stability.md
  - .github/workflows/smoke-install.yml
  - .claude/hooks/codex_review_user_code.py
  - .claude/hooks/check_pair_rail.py
  - .claude/scripts/ceo-boot.py
  - .claude/hooks/_lib/audit_emit.py
  - SPEC/v1/audit-log.schema.md
  - .claude/data/audit-registry.golden.txt
  - .claude/hooks/tests/test_audit_emit_api_contract.py
  - .claude/hooks/tests/test_w5_scrub_enforcement.py
  - .claude/hooks/tests/test_git_bypass_guard.py
  - .claude/hooks/tests/test_codex_egress_proof_telemetry.py
  - .claude/hooks/tests/test_codex_review_user_code.py
  - .claude/hooks/tests/test_check_pair_rail_matrix.py
  - .claude/scripts/tests/test_ceo_boot_liveness.py

## What is authorized

The PLAN-161 consolidated maintenance sweep W2 pack, exactly as pinned by
the tracked `inputs.sha256` manifest (`shasum -c` fail-closed in the
ceremony preflight): staged bytes verified by the W1 red-first oracles
(test-upgrade-dryrun-identity, test-upgrade-exclusions,
test-council-grok-artifact, proof-retry-matrix) flipping GREEN in staged
mode, the named regression suites, and the codex pair-rail review of the
pack. `scripts/_grok_harness.sh` is DELIBERATELY absent (CF-4:
installer-emission surface; egress logic landing there = F3 class,
guard-enroll first). `check_codex_stop_review.py` is DELIBERATELY absent
(codex-harness inverted rail, not wired here).
