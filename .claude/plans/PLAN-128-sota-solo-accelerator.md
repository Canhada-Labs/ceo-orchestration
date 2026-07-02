---
id: PLAN-128
title: SOTA solo accelerator stack
status: done
created: 2026-07-02
owner: CEO
depends_on: []
completed_at: 2026-07-02
related_commits:
  - 9777a8d
tags: [accelerators, measurement, provenance]
---

# PLAN-128 — SOTA solo accelerator stack (restored provenance record)

> **Restored provenance record (PLAN-152 governance-05 / dead-code-03).**
> PLAN-128 was planned, debated, and executed in the pre-release private
> repository. The v1.0.0 clean-room migration (commit `9777a8d`) shipped its
> live artifacts (`.claude/plans/PLAN-128/` + the accelerator hooks) but not
> the plan file, leaving the directory an orphan under PLAN-SCHEMA §1 (a
> `PLAN-<NNN>/` subdir must match an existing plan file). This minimal plan
> file restores the match. `created:`/`completed_at:` are the dates of this
> restored record, not the original private-repo lifecycle; full execution
> history lives in the private archive.

## Context

PLAN-128 built the accelerator stack — the $0/opt-in quality guard-rails
(`verify_after_edit.py`, `codex_review_user_code.py`, `adequacy_gate.py`,
`route.py`, `accel_dispatch.py`, `turbo_profile.py`, `review_loop.py`,
`latency_report.py`, `auto_boot.py` under `.claude/hooks/`) and the §7
honest-measurement doctrine (no unmeasured speed claim; catch-rate 0/0/0 on
meta-work is expected — measure in a real app repo).

## Goal

Ship opt-in accelerator guard-rails plus an honest OFF-vs-ON A/B measurement
protocol, without making a throughput claim the data does not support.

## Items

- [x] Waves 1-2 — accelerator hooks + wiring (shipped pre-release; see the
  `PLAN-128` markers throughout `.claude/hooks/`). Check: none (historical
  record; shipped in `9777a8d`).
- [x] §7 — measurement artifacts `PLAN-128/AB-PROTOCOL.md` +
  `PLAN-128/measure-state.sh`, consumed by `docs/ACCELERATORS.md` and
  `scripts/install-accelerators.sh`. Check: none (historical record; shipped
  in `9777a8d`).

## Success criteria

- [x] Accelerator hooks live under `.claude/hooks/` (v1.0.0). Check: none
  (historical record).
- [x] `.claude/plans/PLAN-128/` carries the live §7 measurement artifacts and
  has a matching top-level plan file (this file). Check:
  `bash .claude/scripts/validate-governance.sh` — PLAN-SCHEMA §1 section
  reports no orphan PLAN-NNN subdirs.

## Known gap (tracked separately — NOT closed by this record)

Both §7 artifacts depend on `PLAN-128/wave1/measure_multiplier.py`, which was
not shipped in the clean-room migration: `measure-state.sh` exits FATAL at its
wave1 preflight, and `AB-PROTOCOL.md` §"Computar o multiplicador" invokes the
same missing script (`scripts/install-accelerators.sh` also prints both
paths). Restoring or degrading that tooling needs its own follow-up item;
it is out of scope for PLAN-152 governance-05.
