# Changelog

All notable changes to **ceo-orchestration** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Scope.** This log records *user-visible* changes — new skills, hooks, slash
> commands, schema/contract changes, and behavior an adopter would notice after
> installing or upgrading the framework. Internal refactors, test-only churn, and
> release-engineering bookkeeping are omitted. Counts cited below (as of
> v1.0.1: 151 skills, 22 slash commands, 172 ADRs, 67 `_lib` modules) are
> reproducible from the repository via
> `bash .claude/scripts/local/verify-counts.sh`.

---

## [1.0.1] - 2026-07-02

v1.0.1 hardening sweep (PLAN-152) — remediation of the 2026-07-01 post-release
audit fan-out (run `wf_071ef6c5`: 41 confirmed findings) + v1.0.1 backlog.
No new features; security fixes, CI truth, tarball hygiene, model modernization.

### Security (P0 — shipped-broken in v1.0.0)
- **check_pair_rail PreToolUse gate was FAIL-OPEN since v1.0.0** — the
  settings.json registration passed a relative path the shim could not
  resolve (`hook not found` + `{}` allow). Fixed to the basename +
  `"$CLAUDE_PROJECT_DIR"` form used by the other 43 registrations
  (governance-01).
- **bash-safety destructive-command guard fail-opened on quoted metachars**
  (`rm -rf ~ ";"` passed). Fixed with a quote-aware subcommand splitter
  (char-walk honoring quotes/escapes/adjacent operators); 16-case
  adversarial battery; kill-switch `CEO_BASH_RAWSCAN=0` (error-handling-01).
- **_python-hook.sh interpreter-cache TOCTOU/symlink hardening** — cache dir
  must be owner-held, non-symlink, not group/world-writable; symlink
  rejected before chmod (security-01).
- Match.snippet in `_lib/pii_patterns.py` now honors its "redacted /
  preview-safe" contract: matched span masked AND surrounding context
  re-swept by the module's own family+entropy redaction (adjacent-secret
  leak found by the Codex pair-rail) (error-handling-02).

### CI / tests
- **~1,600 formerly CI-dark tests wired into validate.yml** as explicit
  paths (tests/unit + 8 roots: _lib/tests, swarm, replay, federation,
  mcp-server, detectors, predict-budget, forensic, synthetic), two-pass
  serial split preserved (tests-01/02/07). 13 root test files (incl. 3
  SECURITY suites) relocated to tests/unit/. Stale tests exposed by the
  wiring fixed (codex token telemetry ×2, predict-budget spool-write race).
- env-hygiene burndown: 55 violations (swarm 43 + mcp-server 12) refactored
  to TestEnvContext; the 3 cleaned roots added to the enforcing scan tuple
  (tests-03).
- coverage.yml: stale "78%" floor claims reconciled with the real enforcing
  `--fail-under=67` (tests-04); dead doc refs corrected (tests-05: ADR-042
  now cites mcp-smoke.yml).
- validate-governance.sh: new orphan PLAN-<NNN>/ dir guard (PLAN-SCHEMA §1
  matching-plan-file rule now enforced + seed test) (governance-05).

### npm tarball (backlog #2)
- **Selective staging replaces blanket `cp -r .claude npm/`** in
  npm-publish.yml + install-npm.sh (rsync excludes: **/tests/, **/fixtures/,
  red-team-corpus, eval, numbered plan trees, _lib/testing.py +
  test_isolation.py; keeps plans schemas/examples + policies/fixtures).
  v1.0.0 shipped 2373 files incl. 1029 test files; v1.0.1 ships 1158 with
  zero FORBIDDEN framework-internal artifacts (the two deliberate
  carve-outs — `.claude/policies/fixtures/` and the adopter-facing
  `templates/oidc-proxy/tests/` — keep shipping by contract) (tarball-01).
- **Packlist gate** (`npm pack --dry-run --json` + forbidden-pattern assert)
  added to validate.yml (PR/push) and npm-publish.yml (pre-publish)
  (tarball-02). npm/.npmignore comments corrected (entries are INERT under
  the package.json `files` whitelist — staging excludes are the rail).
- npm-publish.yml false "OIDC trusted publisher" header corrected (auth is
  a granular token + Sigstore --provenance; Trusted Publishing tracked for
  v1.0.2; NPM_TOKEN expires ~2026-09-28).

### Hot-path economics
- check_output_secrets: deprecated aggregate sidecar emit removed (halves
  HMAC appends + filelocks per scan hit) (economics-01).
- check_read_injection: A2 unicode guard now gated on CEO_UNICODE_HARDBLOCK
  BEFORE any work + re-read capped at 1 MiB (was: unconditional 2nd
  uncapped full-file read on EVERY Read) (economics-02).
- anti-CEO-overhead 5-min window now per-SESSION (parallel sanctioned
  fan-outs no longer pool one budget) + stale-window GC (economics-03).

### Workflow robustness (backlog #4)
- audit-fanout / nightly-hygiene / eval-baseline-n20 null-guarded against
  agent() resolving null on terminal API error (the wf_071ef6c5 crash
  class); audit-fanout gains a deterministic mechanical verdict — CLEAN is
  inadmissible over unaudited dimensions (error-handling-03).

### Model / substrate (backlog #3)
- **ADR-157**: Sonnet 5 (`claude-sonnet-5`) added to the closed MODEL_ID
  enum — member only; M-tier routing default UNCHANGED and pinned by
  regression tests (routing flip = own future plan per OQ1).
- model-deprecations ledger: fast-mode fuses added (claude-opus-4-6-fast
  retired 2026-06-29 silent fallback; claude-opus-4-7-fast retires
  2026-07-24 hard error).

### Docs / dead code
- Dead refs + stale counts fixed across GUIA-COMPLETO (EN/pt-BR), INSTALL,
  CTO-GUIDE, RELEASE, QUICKSTART, SBOM, TROUBLESHOOTING (EN/pt-BR),
  release-checklist, .coveragerc, performance-budgets (docs-01..08,
  dependencies-01, economics-04).
- PLAN-128 orphan dir resolved with a restored provenance plan file
  (dead-code-03); 7 shipped ceremony scripts moved to
  scripts/local/historical/ (dead-code-04); null-valued benchmark JSONL
  removed (dead-code-06); check-version-drift docstring corrected
  (dead-code-01); install-accelerators stale note fixed (dead-code-02).

### Deferred to v1.0.2 (on-disk pointers in PLAN-152)
- `_lib/tests` 128-site env-hygiene burndown; npm Trusted Publishing (OIDC);
  kernel-matcher expansion (governance-04/07); nested-subagent red-team
  corpus; PLAN-128 wave1 measurement tooling restore.

## [1.0.0] — 2026-06-29

First public release — the clean public baseline of **ceo-orchestration**.

Prior versions were private internal iterations and are intentionally not part of
this repository's history; v1.0.0 is the zero-history genesis of the public
project.

### Included
- **Plan → Debate → Execute** governance gating for L3+ changes, with vetoes and
  a three-strike rule (`PROTOCOL.md`).
- A **tamper-evident, HMAC-chained audit log** with chain verification.
- A **cross-LLM pair-rail**: a second model reviews canonical edits before they land.
- A **skill library** (151 skills: 42 core + 8 frontend + 101 domain).
- **Governance hooks** (Python, stdlib-only) wired through `.claude/settings.json`.
- **171 ADRs** and **22 slash commands**.

> **No speed claim.** Internal experiments found no general speedup over an
> optimized solo workflow — the value here is governance and auditability, not
> throughput.

---

[1.0.0]: https://github.com/Canhada-Labs/ceo-orchestration/releases/tag/v1.0.0
