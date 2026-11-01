# Review Guide

This guide sets expectations for pull request review in this repository. The
[protocol](PROTOCOL.md), including its vetoes and escalation rules, remains
authoritative; this guide does not claim that these review steps are automated.

## Pre-PR Verification

Before requesting review, run the tests and linters applicable to the change,
and run:

```bash
bash .claude/scripts/validate-governance.sh
```

Record the commands and literal results in the pull request. Report failures
and unavailable checks rather than presenting them as passing; resolve failures
or escalate them under the protocol before seeking approval.

## What Failure Looks Like by Directory

- `.claude/hooks/` and `.claude/hooks/_lib/`: a security bypass, a broken HMAC
  chain (see [`audit_hmac.py`](.claude/hooks/_lib/audit_hmac.py)), unhandled
  exceptions, or blocking or draining work beyond the requested 500 ms budget.
  Measure the affected path and its environment; the budget is a review target,
  not a claim that every hook has an enforced 500 ms deadline. Infrastructure
  failures normally fail open with a breadcrumb; the canonical-edit matcher's
  wall deadline deliberately fails closed as incomplete verification under
  [ADR-186](.claude/adr/ADR-186-hook-deadline-policy.md).
- [`scripts/install.sh`](scripts/install.sh) and
  [`scripts/upgrade.sh`](scripts/upgrade.sh): writes outside the authorized
  manifest, TOCTOU exposure, POSIX/BSD/GNU incompatibility, or loss of
  idempotence on a repeated run.
- `.claude/skills/` and `.claude/adr/`: broken references, private-path
  contamination, or index drift.

## Zero-Nitpick & Evidence Rule

Discard style-only comments. Each proposed blocking P0, P1, or P2 finding must
include `file:line`, a reproducible case or verifiable counterexample, and
Codex and Claude pair-rail consensus. Record disagreement for escalation;
absence of consensus is not approval. The runtime pair-rail has its own
[verdict matrix](docs/PAIR-RAIL-VERDICT-MATRIX.md); this review convention does
not replace its hook behavior or the protocol's vetoes.

## Review Round Cap

Limit review to three rounds. Starting with round 2, review only the delta
(`--delta-only`): changes since the prior round and their necessary context.
Do not reopen findings already discarded. At the cap, escalate unresolved
issues under the protocol; do not treat the cap as approval or override a veto.
