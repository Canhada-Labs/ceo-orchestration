# .claude/governance/ — Policy contracts and provenance artifacts

This directory contains governance policy files consumed by CI workflows
and local hook scripts. **Do not rename or delete files here without
updating the corresponding CI step.**

## File inventory

| File | Purpose | Consumers |
|---|---|---|
| `governance-waivers.yaml` | Per-plan release-gate waivers (rc_hold, workflow_staleness). Active waivers allow a tag to pass release.yml checks that would otherwise block. | `release.yml` §waiver gate |
| `pair-rail-inputs-hash-manifest.txt` | Declares the input-files that Codex pair-rail reviewed; HMAC-verified by the release gate. | `release.yml` §validate-pair-rail-verdict |
| `codex-cli-pin.txt` | Pinned Codex CLI version range accepted by pair-rail verification. | `release.yml` §codex-pin |
| `codex-cli-binary-sha256.txt` | RETIRED tombstone (ADR-182): the old launcher-hash pin. Comment-only; carries no hex. Kept so historical verdicts keep a referent and the path stays guarded. | `release.yml` §codex-pin (legacy tags only) |
| `codex-cli-pin-manifest.json` | ADR-182 payload pin: sha256 of the NATIVE Codex payload per targetTriple (+ npm dist.integrity provenance). Enforced verify-then-invoke by `check_pair_rail.py`, at pre-flight by `pair-rail-gate.sh` Gate 4, and at tag time by `release.yml` step 15. | `check_pair_rail.py`, `pair-rail-gate.sh`, `release.yml` §codex-pin |
| `audit_tokens_allowlist.json` | Allowlist of audit-token patterns exempt from the canonical-edit sentinel content ban (ADR-031). | `check_arbitration_kernel.py` (PreToolUse hook) |
| `function-length-grandfather.yaml` | Grandfather list of functions that exceed the length policy but predate enforcement (PLAN-066 DIM-07). New functions are not grandfathered. | `check-function-length.py` (local script) |
| `pair-rail-verdict-template.md` | Template for authoring new Codex pair-rail verdict files. | Documentation only |

> The directory may also accumulate historical `pair-rail-verdict-v*.md`
> files — one per tagged release that required a Codex pair-rail review.
> They are permanent provenance records (see Lifecycle rules).

## Lifecycle rules

- `governance-waivers.yaml` entries are time-bounded; review and prune
  after the corresponding plan reaches `status: done`.
- Historical pair-rail verdict files (`pair-rail-verdict-v*.md`) accumulate
  one file per tagged release that required a Codex pair-rail review.
  They are permanent provenance records — do not delete.
- `function-length-grandfather.yaml` shrinks over time as grandfathered
  functions are refactored. Never add new entries without Owner approval.

## Related

- `release.yml` §Codex pair-rail verdict gate
- `.claude/hooks/check_arbitration_kernel.py` — sentinel content ban
- `.claude/scripts/check-function-length.py` — function-length policy
