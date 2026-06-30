# Autonomous-Loop Parallelism — Adopter Guide

> **Status:** scaffold shipped (Sprint 30, WAR-ROOM P06). Worktree
> orchestration + policy-engine wiring deferred to PLAN-017 follow-up
> sprints. Default OFF. Two-factor activation required.

## 0. Native autonomy first (PLAN-135 W4 D3 doctrine)

Before reaching for this guide's swarm machinery — or the ADR-133
opt-in autonomous loop — check whether a **native harness primitive**
already covers the objective. The native primitives need zero
framework config and carry their own kill switches; the framework
loop earns its complexity only on explorable solution spaces (§1).

| Objective shape | Native primitive | Doctrine |
|---|---|---|
| **Bounded objective with an independent pass/fail check** ("CI green on this PR", "all tests pass") | `/goal` | PREFER over the ADR-133 loop: independent verifier, zero config. The ADR-133 loop / swarm is for explorable solution spaces (§1), not bounded objectives. |
| **Long unit that shouldn't hold the foreground session** | `claude --bg --name PLAN-NNN-<unit>` | Naming convention is MANDATORY: `--name PLAN-NNN-<unit>` so every background session is attributable to a plan unit at triage time. Run it in an isolated worktree — never against the live checkout. |
| **Recurring hygiene on an interval** | `/loop 24h /nightly-hygiene` | Native recurrence before OS cron or swarm loops. Its kill switch is `CLAUDE_CODE_DISABLE_CRON` — inventory it alongside the swarm layers in §6. |
| **Post-ceremony CI vigil** | Monitor armed on `gh run watch` | PRESCRIBED runbook step after every Owner ceremony lands: arm Monitor on `gh run watch` for the triggered runs. This kills the red-discovered-next-session failure class — the S228 exec-bit red would have been auto-triaged. |
| **Gate waiting on Owner GPG** | PushNotification (+ Remote Control) | When a finish script / ceremony gate blocks on Owner GPG, fire a PushNotification instead of idling; Remote Control lets the Owner approve from the phone. |

**Decision rule:** bounded → `/goal`; background → `claude --bg`;
recurring → `/loop`; vigil/approval → Monitor + PushNotification.
Only an **explorable solution space** with a measurable objective
justifies the ADR-133 / swarm machinery below. Surface selection for
scheduled work (local vs cloud vs Desktop — **meta-repo secrets never
go cloud**) is the table in `docs/MECHANISM-SELECTION.md` §6.

## 1. What it is

Ship N parallel autonomous-optimization loops with a safety envelope:

- N independent loops, each iterating `try → measure → keep/revert`
- Cross-loop memory (opt-in) so they learn from each other's misses
- Tournament selector that promotes the best-of-N candidate
- Circuit breakers + 6-layer kill switch
- Checkpoint + `--resume` recovery

**When to use:** problems with an **explorable solution space** — test
speed optimization, bundle size reduction, LLM prompt iteration,
benchmark tuning, property-based-test corpus expansion.

**When NOT to use:** single deterministic tasks, governance-critical
paths (auth, canonical edits, schema migrations), or any task where
the "best" outcome is subjective rather than measurable.

## 2. Architecture at a glance

```
Owner sets budget + goal
       │
       ▼
Swarm Coordinator   ←──── kill switch (env, file, iter counter,
       │                              SIGKILL, cgroups, watchdog)
       │
       ├──→ Loop 1  (hypothesis A)  ──┐
       ├──→ Loop 2  (hypothesis B)  ──┤
       ├──→ Loop 3  (hypothesis C)  ──┤
       └──→ Loop N  (hypothesis …)  ──┤
                                      │
                                      ▼
                              Tournament scorer
                                      │
                                      ▼
                              Winner promoted → N
                              losers preserved as .rejected
```

## 3. Default OFF — activation gate

The swarm **refuses to dispatch** unless BOTH conditions are true:

1. Environment variable: `CEO_SWARM=1`
2. Sentinel file absent: `<project>/.claude/swarm-kill` does NOT exist

Either condition missing → coordinator returns `{"status":"refused"}`
and emits no loops. This is Design Principle #1 (PLAN-017 Round 1
consensus) — never activate by accident.

## 4. Quick start (dry-run)

```bash
cd /absolute/path/to/your/project
export CEO_SWARM=1
python3 .claude/scripts/swarm/coordinator.py \
    --loops 3 \
    --budget-tokens 10000 \
    --goal "reduce test suite runtime" \
    --dry-run
```

Expected output:

```json
{
  "status": "dry_run",
  "config": {
    "n_loops": 3,
    "budget_tokens": 10000,
    "goal": "reduce test suite runtime",
    "jaccard_threshold": 0.7,
    "max_strikes": 3,
    "max_iterations": 20
  }
}
```

Dry-run validates configuration without spawning any loop. Use it
every time you change a parameter.

## 5. Configuration profiles

| Profile | N loops | Budget cap | Unattended | Human review |
|---|---|---|---|---|
| `solo` (default) | 0 (disabled) | n/a | n/a | n/a |
| `team` (opt-in) | ≤2 | ≤$5/session | never | mandatory per finalize |
| `enterprise` (opt-in) | ≤8 | configurable | gated (ADR-053) | per run |

Set via `.claude/settings.json`:

```json
{
  "autonomous_loops": {
    "enabled": false,
    "profile": "solo",
    "max_parallel": 0,
    "budget_cap_tokens": 0,
    "budget_cap_wallclock_hours": 0,
    "kill_switch_path": ".claude/swarm-kill",
    "disk_cap_gb": 10,
    "fd_cap": 128
  }
}
```

**Never hand-edit `autonomous_loops.enabled` to `true` in a shared
repo without Owner sign-off.** The env-var + sentinel pair is there
to make accidental activation impossible; a committed `enabled: true`
undermines that.

## 6. Kill switches (6 layers)

| Layer | Trigger | Scope |
|---|---|---|
| 1. Env var | `CEO_SWARM=0` OR `CEO_AUTONOMOUS_LOOPS_DISABLE=1` | entire swarm |
| 2. File sentinel | `touch .claude/swarm-kill` | entire swarm |
| 3. Iteration counter | `max_iterations` reached | one loop |
| 4. SIGTERM → SIGKILL | 30s grace then hard kill | process |
| 5. cgroups/ulimit | CPU / mem / FD cap (OS-level) | process |
| 6. Parent-process watchdog | CEO process died → zombie detected | process |

Layers 4-6 are coordinator-wired in PLAN-017 follow-up. Layers 1-3
(in-process) ship today.

**Kill a running swarm:**

```bash
# Fastest — file sentinel (graceful halt + checkpoint preserved):
touch .claude/swarm-kill

# Nuclear — env var (halts on next iteration tick):
export CEO_SWARM=0

# Surgical — kill one loop (via coordinator CLI, deferred):
python3 .claude/scripts/swarm/coordinator.py --kill-loop L3
```

**Native-scheduling kill switch (PLAN-135 W4 D3):** recurring work
scheduled through the native harness (`/loop <interval> /<command>`,
§0) is NOT governed by the 6 swarm layers above — its kill switch is
`CLAUDE_CODE_DISABLE_CRON`. Inventory it alongside the layers in this
table whenever you audit "what autonomous things can run here."

## 7. Circuit breakers (9 mandatory)

| # | Breaker | Scope | Action |
|---|---|---|---|
| 1 | Budget exceeded (Σ tokens) | swarm | HALT |
| 2 | Convergence (Jaccard ≥0.7) | loop | PAUSE loser, keep leader |
| 3 | Error rate (3-strike) | loop | KILL loop |
| 4 | Noise floor (MAD ratio) | loop | DEPRIORITIZE |
| 5 | Manual kill (sentinel) | swarm | HALT |
| 6 | Disk exhaustion | swarm | HALT |
| 7 | FD exhaustion | swarm | HALT |
| 8 | Wall-clock per iteration | loop | KILL loop |
| 9 | Parent-process death | swarm | HALT |

CB #1-5 ship today as pure predicates. CB #6-9 land when the
coordinator wires the real worktree + subprocess layer.

## 8. Tournament + finalize

When all active loops complete (or get killed), the Tournament scorer
ranks candidates:

- Regression → disqualified (`tests_failed > 0` → score = `-∞`)
- Non-regressed → weighted sum of metric + tests_passed - LoC penalty
- Winner gets promoted to `main`; losers preserved as `.rejected`
  branches

Custom weights via `ScoreWeights(metric=1.0, tests_passed=0.1,
tests_failed_penalty=10.0, loc_delta_penalty=0.001)`.

## 9. Cost considerations

**Token burn compounds linearly with N.** A 3-loop swarm ≈ 3× a
single-session cost. Set `--budget-tokens` explicitly; the coordinator
enforces it as CB #1.

Typical costs (rough):
- 2-loop × 10 iterations × simple benchmark: ~\$2-5
- 4-loop × 20 iterations × complex benchmark: ~\$20-50
- Enterprise 8-loop × 20 iterations: ~\$80-150

**Always dry-run first.** The `--dry-run` flag prints the config; use
it before real dispatch.

## 10. Convergence tuning

Default Jaccard threshold is 0.7 (loops touching ≥70% of the same
files get the later-indexed one killed).

- **0.5** — aggressive convergence, only 1-2 loops usually survive.
  Good when problem is narrow + diversity isn't paying off.
- **0.7** (default) — balanced; 60% of loops typically survive
  through 3 iterations.
- **0.9** — loose; only identical-file-set loops converge. Good for
  high-diversity exploration.

## 11. Recovery — `--resume <swarm_id>`

The coordinator writes a `SwarmCheckpoint` JSON file after every
iteration. On crash or manual kill:

```bash
python3 .claude/scripts/swarm/coordinator.py \
    --resume <swarm_id> \
    --checkpoint-path .claude/swarm-state/<swarm_id>.json
```

The checkpoint preserves:
- Each loop's `LoopState` (iteration, tokens, files, strikes, status)
- Last kill-switch decision + reasons
- Worktrees preserved (paths) — restored on resume

**Canonical-projection:** timestamps, PIDs, and paths are stripped
at replay time per `SPEC/v1/replay.schema.md` (PLAN-017 Phase 0.11).

## 12. Example workflow — test suite speedup

```bash
# Day 1: profile the test suite.
python3 .claude/scripts/performance-baseline.py --suite tests/

# Day 2: dispatch swarm to find speedups.
export CEO_SWARM=1
python3 .claude/scripts/swarm/coordinator.py \
    --loops 3 \
    --budget-tokens 20000 \
    --goal "reduce pytest runtime from 120s to <60s" \
    --max-iterations 15 \
    --jaccard-threshold 0.5

# Day 3: review the winner.
git log --oneline main..swarm-winner
python3 .claude/scripts/benchmark-compare.py \
    --baseline main --candidate swarm-winner

# Day 4: if Owner approves, merge.
git checkout main && git merge swarm-winner
```

## 13. Anti-patterns — NEVER do

1. **Never** enable unattended mode without ADR-053 option (B)
   FULLY approved (2FA + time-windows + daily cap + heartbeat +
   external monitor + dead-man switch).
2. **Never** commit `autonomous_loops.enabled: true` to a shared
   `settings.json` — force per-session opt-in via env var instead.
3. **Never** let a loop modify governance files (`hooks/`, policy
   YAMLs, ADRs, SPEC, coordinator code, own kill switch). The output
   filter rejects these commits automatically; don't work around it.
4. **Never** trust a swarm benchmark without verifying the winner's
   `tests_passed` matches baseline (regression disqualifier is
   advisory, not cryptographic).
5. **Never** run a swarm on a dirty working tree — use worktrees.
   Scaffold enforces this in follow-up via ADR-049a isolation model.

## 14. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `{"status":"refused"}` despite `CEO_SWARM=1` | Scaffold-only; worktree orchestration not shipped | Wait for PLAN-017 follow-up |
| All loops status=killed within seconds | Sentinel file present | `rm .claude/swarm-kill` |
| Tournament returns `winner=None` | All candidates had regressions | Widen diversity (jaccard=0.5), check benchmark |
| Budget exceeded on iteration 1 | Token-per-iter underestimate | Increase `--budget-tokens` or reduce `--loops` |
| Convergence kills all but L1 | Hypothesis generator too narrow | Pre-seed disjoint `files_touched` sets |

## 15. Honest limitations

- **Same-LLM bias applies.** All N loops are the same model; "parallel
  search" is a stochastic sampler, not N independent experts.
  Diversity comes from the hypothesis generator, not the model.
- **Reproducibility is canonical-projection, not byte-identity.**
  Strip rules in `SPEC/v1/replay.schema.md` — timestamps, PIDs, paths,
  counters are normalized. Two runs may differ byte-for-byte but
  canonicalize to the same event stream.
- **Python GIL + OS scheduling are not seedable.** Race conditions
  are proved (or disproved) via TLA+ in Phase 3.5, not via "set a
  seed and rerun" — that's probabilistic flake-reduction, not
  correctness.

## 16. See also

- `.claude/plans/PLAN-017-autonomous-loop-parallelism.md` — full plan
  (6 phases, 21 consensus adjustments from Round 1 debate)
- `.claude/scripts/swarm/` — coordinator / loop_runner / file_assignment
  / kill_switch / tournament / recovery source
- `.claude/plans/PLAN-017/staged-code/` — staged canonical-guarded
  patches (audit-dashboard tab, audit_emit kernel batch, team.md row)
- `docs/HONEST-LIMITATIONS.md` — same-LLM disclosure
- `docs/MECHANISM-SELECTION.md` §6 — scheduling-surface selection
  table (local vs cloud vs Desktop; meta-repo secrets never go cloud)
- PLAN-032 `tournament/` — learned-weighting tournament framework
  (opt-in integration deferred to follow-up)

---

**Last updated:** 2026-06-12 — §0 native-autonomy doctrine + §6
native-scheduling kill-switch note added (PLAN-135 W4 D3). Previous:
2026-04-21, WAR-ROOM P06 dispatch. For the full 9-week execution plan
(this ships the Sprint-30 scaffold only), see PLAN-017 §Success
criteria (Round 1 updated).
