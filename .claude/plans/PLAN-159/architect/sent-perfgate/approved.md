# SENT-PERFGATE — PLAN-159 Wave 1: hook-latency gate percentile stability

Raises the opus-4-7-profiler-smoke hook-latency gate from N=20 to N=200
warm iterations, adds a single deterministic in-step retry that is
fail-closed by construction (if-not form, EXACTLY 2 attempts, 420s
per-attempt wall-cap, explicit exit 1 on double failure, attempt
percentiles in the step summary whenever a parseable report exists and
an explicit no-report note otherwise), bumps the job timeout 5->16min
(contended 2xcap + overhead), hardens the profiler (fail-loud
percentile_indices_collapsed precondition min N=22; TimeoutExpired
folded into the fail-closed hook_failed sink; default N 20->200) with 9
staged unit tests, ships ADR-163 (canonical N>=200
percentile-stability record + invariants + measured evidence), and
repairs the ADR-071 citation drift in validate.yml +
test_hook_latency.py. Ceilings UNCHANGED (p95<120ms / p99<160ms).
Root cause measured in .claude/plans/PLAN-159/measurements.md: at N=20
the nearest-rank index collapses (idx_p95 == idx_p99 == 2nd-largest
sample; p99 was dead code) — 8 load-flakes S272/S273 on doc-only
commits. Detection: an injected over-ceiling regression fails BOTH
attempts (proven post-land by wave2-regression-proof.sh THROUGH the
wrapper). Debate round-1: 3x ADJUST -> consensus PROCEED, all
must-fixes resolved + mirror-clone proven. OQ1-OQ3 ratified (plan
§Open questions); pair-rail V2 verdict at
.claude/plans/PLAN-159/pair-rail-verdict-wave1.md.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: a1e6f7d013d3d53ba1a937ea12f3acede2814c64
Plans: PLAN-159
Kernel-Override: (none — .github/workflows/*.yml + .claude/adr/*.md are CANONICAL class, not _KERNEL_PATHS; profiler + tests are unguarded)
Scope:
  - .github/workflows/validate.yml
  - .claude/adr/ADR-163-hook-latency-gate-percentile-stability.md
  - .claude/scripts/profile-opus-4-7.py
  - .claude/scripts/tests/test_profile_opus47_latency_gate.py
  - .claude/hooks/tests/test_hook_latency.py
  - CLAUDE.md
<!-- END SIGNED SCOPE -->
