# PLAN-152 — Canonical-Edit Sentinel (round 3 — step-15 verdict ceremony)

Authorizes the two guarded governance edits required to satisfy the
`release.yml` step-15 pair-rail verdict gate for the `v1.0.1` GA — the first
release where the gate hard-blocks (v1.0.0 shipped under the
`CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` transition variable, deliberately deleted
by the Owner at launch closeout):

1. **CREATE** `.claude/governance/pair-rail-verdict-v1.0.1.md` — the
   validator-parsed verdict envelope (S104 `parent_sha` bind, fresh
   `generated_at` within the 24h TTL, deterministic `inputs_hash`, codex-cli
   pins already verified matching the live binary), backed by a fresh Codex
   release re-pass (R3) run this sitting.
2. **AMEND** `.claude/governance/pair-rail-inputs-hash-manifest.txt` — remove
   the dead entry `.claude/plans/PLAN-081/corpus/locked/MANIFEST.md`
   (stripped in the clean-room migration; `git hash-object` on it makes the
   step-15 validator INFRA-fail for every future release). The manifest
   header itself prescribes amendment via this ceremony class.

Anchor commit ab3678ce6ca1258db6b94ee2ab4eedf312d8af9b is the repo HEAD this
sentinel was signed against; it is also the verdict's `parent_sha` (the GA
tag will be re-cut at the verdict commit, whose parent this is).

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs ab3678ce6ca1258db6b94ee2ab4eedf312d8af9b
Plans: PLAN-152
Scope:
  Step-15 verdict ceremony (v1.0.1 GA):
  - .claude/governance/pair-rail-verdict-v1.0.1.md
  - .claude/governance/pair-rail-inputs-hash-manifest.txt
<!-- END SIGNED SCOPE -->

Authorization: Owner-signed GPG detached signature (approved.md.asc), signer
fingerprint AE9B236FDAF0462874060C6BCFCFACF00335DC74, verified against both
signer rails (.claude/sentinel-signers.txt + the ADR-121 YAML registry).

Application path: Edit-under-sentinel attempted first; if the arbitration
kernel hard-denies (as it did for `check_read_injection.py` in round-2), the
fallback is the S258 patcher precedent — the Owner applies the exact
authorized diff via `git apply .claude/plans/PLAN-152/architect/round-3/fix.patch`
(committed alongside as evidence).

Deliberate exclusions (not canonical-guarded, land direct):
`.claude/plans/**` (ceremony evidence, closeout narration), `CHANGELOG.md`.

Rationale:
  - pair-rail-verdict-v1.0.1.md — the honest completion of the gate the
    Owner armed by deleting the transition variable: a real verdict envelope
    (GO, per Codex R1 REJECT → remediation → R2 APPROVE → fresh R3), real
    transcript_hash, single-line-encoded real GPG signature (validator's
    line-oriented YAML parser cannot carry a multi-line armor block; the raw
    `.asc` ships as a sibling evidence file).
  - pair-rail-inputs-hash-manifest.txt — dead-path removal only; no entry
    additions. Every remaining path verified present (18/18).
