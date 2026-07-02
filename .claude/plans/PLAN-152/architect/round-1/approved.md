# PLAN-152 — Canonical-Edit Sentinel (round 1)

Authorizes the guarded/canonical edits of PLAN-152 (v1.0.1 Hardening Sweep),
Waves A/B/C/D/F, per the OQ2 resolution (ONE sentinel; Scope = enumerated
explicit-file allowlist, no globs). Wave labels inside the Scope block are
grouping sub-headers only — authorization is per-file; a file listed once is
authorized for every in-plan touch (e.g. coverage.yml carries both the Wave B
tests-04 floor-claim fix and the Wave E docs-06 dead-ref fix at :5).

Anchor commit c88daf922d0ba124ef2bb3592554774e6a8a2eba is the repo HEAD this
sentinel was signed against (the committed `status: reviewed` plan revision).

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs c88daf922d0ba124ef2bb3592554774e6a8a2eba
Plans: PLAN-152
Scope:
  Wave A (P0 security fail-opens):
  - .claude/settings.json
  - .claude/hooks/check_bash_safety.py
  - .claude/hooks/_python-hook.sh
  Wave B (CI-dark tests + coverage-truth):
  - .github/workflows/validate.yml
  - .github/workflows/coverage.yml
  - .claude/adr/ADR-042-mcp-server-contract.md
  Wave C (hot-path economics):
  - .claude/hooks/check_output_secrets.py
  - .claude/hooks/check_read_injection.py
  - .claude/hooks/check_anti_ceo_overhead.py
  - .claude/hooks/_lib/pii_patterns.py
  Wave D (npm tarball hygiene):
  - .github/workflows/npm-publish.yml
  - scripts/install-npm.sh
  Wave F (model/substrate modernization):
  - .claude/hooks/_lib/tier_policy/_types.py
  - .claude/adr/ADR-157-sonnet-5-tier.md
<!-- END SIGNED SCOPE -->

Authorization: Owner-signed GPG detached signature (approved.md.asc), signer
fingerprint AE9B236FDAF0462874060C6BCFCFACF00335DC74, verified against both
signer rails (.claude/sentinel-signers.txt + the ADR-121 YAML registry).

Kernel-override note: `.claude/settings.json`, `check_bash_safety.py`,
`_python-hook.sh`, the three `.github/workflows/*.yml` entries, and
`_lib/tier_policy/_types.py` are ALSO in `_KERNEL_PATHS`
(check_arbitration_kernel.py — HARD-DENY, no sentinel escape). Editing them
requires, IN ADDITION to this sentinel, the launch-environment pair
`CEO_KERNEL_OVERRIDE=PLAN-152-v1-0-1-hardening` +
`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` (hooks read the Claude Code PROCESS env —
a Bash-tool export mid-session never reaches hook invocations; Codex pair-rail
R3-P2). Compensating controls for the session-wide override scope: this signed
allowlist + mechanical `touched−scope=∅` re-check at EVERY wave boundary +
`kernel_override_used` audit emit on every use (ADR-031) + manual
`codex exec review --uncommitted` APPROVE recorded per guarded commit (the
auto pair-rail is DEAD for the whole run — hooks load at session start), plus
one deliberate out-of-scope dry-run probe exercising this gate itself (OQ2).

ADR number allocation: ADR-157 is allocated HERE for the Wave F Sonnet-5
envelope ADR (next free NNN after ADR-156 at anchor time) because the
canonical-edit hook exact-matches Scope entries — a placeholder `ADR-NNN-…`
path would authorize nothing (Codex R5-P2).

Deliberate exclusions (NOT authorized by this sentinel):
  - `.claude/workflows/*.js` (audit-fanout / nightly-hygiene / eval-baseline
    null-guards) — NOT canonical-guarded (debate C3); lands direct.
  - `hooks/tests/**`, `templates/**`, `.claude/scripts/**` (incl.
    check_contamination.py, test-env-hygiene-allowlist.yaml,
    model-deprecations.json + tests), `.claude/data/**`, `pytest.ini`,
    `tests/unit/**`, `docs/**`, `CLAUDE.md`, `VERSION`, `CHANGELOG.md`,
    `npm/package.json` — not canonical-guarded; land direct.

Pre-decisions pinned by this Scope (flipping any requires an `Amends:`
sentinel per PLAN-085 Wave E.5):
  - tests-05 takes the ADR-text branch: correct the dead citation at
    ADR-042:629 to name the real workflow. Shipping a NEW
    `.github/workflows/mcp-coverage.yml` is NOT authorized.
  - economics-04 takes the record-the-deferral branch for the aggregate
    latency-gate ADR (no new ADR file authorized beyond ADR-157).
  - `scripts/install-npm.sh` is authorized CONDITIONALLY (tarball-01
    verify-first): touch it only if it actually stages the `.claude` tree;
    otherwise the entry stays unused (allowlist superset is harmless).

Rationale by path:
  - .claude/settings.json — governance-01: fix the check_pair_rail.py
    PreToolUse registration (:201) to basename + "$CLAUDE_PROJECT_DIR" shim
    invocation, matching the other 43 registrations.
  - .claude/hooks/check_bash_safety.py — error-handling-01: raw-text rescan
    branch on shlex.ValueError (debate C4), default-on kill-switch
    (CEO_BASH_RAWSCAN=0 reverts), fix the :277-280 "fail-safe" docstring.
  - .claude/hooks/_python-hook.sh — security-01: harden the interpreter-cache
    fast path (:120-173): ownership check + symlink rejection.
  - .github/workflows/validate.yml — tests-01: wire tests/unit + the 8
    CI-dark roots as explicit paths (two-pass `not serial`/`serial` split,
    replay/tests after swarm/tests); tarball-02: PR-side packlist gate.
  - .github/workflows/coverage.yml — tests-04: reconcile the three stale
    "78%" floor claims with the enforcing --fail-under=67; also the Wave E
    docs-06 dead-ref fix at :5.
  - .claude/adr/ADR-042-mcp-server-contract.md — tests-05: fix the dead
    mcp-coverage.yml citation (:629), ADR-text branch.
  - .claude/hooks/check_output_secrets.py — economics-01: remove the
    deprecated aggregate sidecar emit (PLAN-106 window elapsed).
  - .claude/hooks/check_read_injection.py — economics-02: cap the second
    full-file read_text (:320); gate the unicode sanitize on
    CEO_UNICODE_HARDBLOCK before doing the work.
  - .claude/hooks/check_anti_ceo_overhead.py — economics-03: session-scope
    (or exempt sanctioned read-only fan-outs from) the 5-min project-wide
    window (:175/:221).
  - .claude/hooks/_lib/pii_patterns.py — error-handling-02: make
    Match.snippet actually redacted OR correct the :114 preview-safe
    docstring.
  - .github/workflows/npm-publish.yml — tarball-01: selective rsync staging
    replacing the blanket `cp -r .claude npm/` (numeric-plan glob only; KEEP
    PLAN-SCHEMA.md + examples/); fix the false OIDC header comment (:3);
    tarball-02: keep the release-side packlist assert.
  - scripts/install-npm.sh — tarball-01: mirror the selective staging IF it
    stages (verify-first, see Pre-decisions).
  - .claude/hooks/_lib/tier_policy/_types.py — sonnet5-tier: ADD the Sonnet-5
    MODEL_ID member; docstring-only OPUS47 reconcile at :12/:41/:94 (NO
    member rename — stable identifier).
  - .claude/adr/ADR-157-sonnet-5-tier.md — sonnet5-tier: author the
    cost/capability envelope ADR (intro $2/$10 → $10 std, -33% vs 4.6,
    tokenizer +30%), new file at the exact pinned path.
