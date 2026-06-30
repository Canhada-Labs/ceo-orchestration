# Changelog

All notable changes to **ceo-orchestration** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Scope.** This log records *user-visible* changes — new skills, hooks, slash
> commands, schema/contract changes, and behavior an adopter would notice after
> installing or upgrading the framework. Internal refactors, test-only churn, and
> release-engineering bookkeeping are omitted. Counts cited below (151 skills,
> 22 slash commands, 171 ADRs, 67 `_lib` modules) are reproducible from the
> repository via `bash .claude/scripts/local/verify-counts.sh`.

---

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
