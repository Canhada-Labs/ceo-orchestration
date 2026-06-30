# State recovery — how to resume work across sessions

> **PLAN-056 Phase 6 / ADR-086 deliverable.** Documents the patterns
> CEO + Owner already use to resume work across CLI restarts, mid-debate,
> mid-ceremony, mid-phase-execute. No new APIs — this doc explains which
> existing artifact answers each resume question.

## Why no `checkpoint(state) → resume(state)` API

Per ADR-086, the framework refuses to add a dedicated checkpointing
API. The reason is empirical: every recovery scenario operators have
encountered is already answered by an existing artifact:

| Scenario | Canonical artifact | How to use |
|---|---|---|
| **Resume after CLI restart** | `~/.claude/projects/<slug>/memory/MEMORY.md` + `CLAUDE.md` | Auto-loaded at Gate 1; CEO reads `git log -10` for last context |
| **Resume mid-debate** | `.claude/plans/PLAN-NNN/audit/round-N/consensus.md` | Plan field `status:` + `audit/round-N/proposal.md` + verdict files |
| **Resume mid-ceremony** | Sentinel `.asc` + `staged-code/` dir | If `.asc` exists, ceremony completed; else re-run `OWNER-PLAN-NNN-CEREMONY.sh` |
| **Resume mid-phase-execute** | Plan file `status: executing` + `executing_at:` + last commit message | Read the plan, read recent commits, continue |
| **Resume after Owner physical action** | `git log` + `.claude/plans/PLAN-NNN/POST-CEREMONY-PROMOTE.sh` | Owner runs the post-ceremony script; CEO continues from where it left off |
| **Resume after debug interruption** | `audit-log.jsonl` last 100 events | `python3 .claude/scripts/audit-query.py recent --limit 100` |
| **Resume after kernel-override** | `audit-log.jsonl` `kernel_override_used` event | `audit-query.py grep --action veto_triggered --reason kernel_override_used` |

## The 4-tier state hierarchy

ceo-orchestration captures state at four orthogonal granularities.
Recovery starts at the coarsest tier that has a clean answer.

### Tier 1 — `git history` (commit-level state)

```bash
git log --oneline -20                # last 20 commits
git show <sha>                        # specific commit + diff
git diff <sha-A>..<sha-B>             # state delta
```

Every commit is durable + signed (CODEOWNERS). Branch protection
prevents force-push. **Use this tier when:** you need to know what
shipped vs what's in-flight.

### Tier 2 — `.claude/plans/PLAN-NNN/` (plan-level state)

```
.claude/plans/PLAN-NNN-<slug>.md         # plan file (frontmatter + body)
.claude/plans/PLAN-NNN/spec.md            # brainstorm spec (per ADR-058)
.claude/plans/PLAN-NNN/architect/         # debate + sentinel rounds
.claude/plans/PLAN-NNN/staged-code/       # pre-ceremony artifacts
.claude/plans/PLAN-NNN/audit/             # audit findings + consensus
.claude/plans/PLAN-NNN/baselines/         # perf snapshots
```

Plan frontmatter fields are the resume contract:

- `status: draft | reviewed | executing | done | refused`
- `created`, `reviewed_at`, `executing_at`, `completed_at` timestamps
- `related_commits: [<sha>, <sha>, ...]` — what shipped per phase
- `spec_ref:` — pointer to brainstorm spec
- `level: L1|L2|L3|L4` — blast radius

**Use this tier when:** you need to know what phase you're in and
what's been signed off.

### Tier 3 — `~/.claude/projects/<slug>/memory/*.md` (cross-session knowledge)

```
~/.claude/projects/<slug>/memory/MEMORY.md             # index
~/.claude/projects/<slug>/memory/user_owner.md         # who Owner is
~/.claude/projects/<slug>/memory/feedback_*.md         # corrections
~/.claude/projects/<slug>/memory/project_plan_*.md     # per-plan notes
~/.claude/projects/<slug>/memory/reference_*.md        # external pointers
```

Memory files persist across CLI sessions. CLAUDE.md Gate 1 auto-loads
them. **Use this tier when:** you need to know what the framework
+ Owner already concluded.

### Tier 4 — `audit-log.jsonl` (event-level state)

```
~/.claude/projects/<slug>/audit-log.jsonl              # append-only
~/.claude/projects/<slug>/audit-key                    # HMAC key (0600)
~/.claude/projects/<slug>/audit-log.last-hmac          # chain sidecar
```

Every tool call + agent spawn + governance event + skill load.
**Use this tier when:** you need exact-time-ordered playback of
what happened.

Tooling:

```bash
python3 .claude/scripts/audit-query.py recent           # last 50 events
python3 .claude/scripts/audit-query.py grep --action agent_spawn
python3 .claude/scripts/audit-telemetry.py --window 7d  # aggregates
python3 .claude/scripts/audit-verify-chain.py           # HMAC verify
```

### Chain-length canary forward-only

The chain-length canary (`audit_hmac.read_chain_length()` /
`write_chain_length()`) was wired in production emitters at **Wave D-2
(2026-04-28)** to close audit-v2 finding C6-P0-03. Before that commit,
the canary helpers existed but were not invoked — the counter stayed at
0 forever, so `verify_chain(strict_against_counter=True)` could not
detect tail truncation.

**Implication for adopters running pre-wire audit logs:**

- Tail-truncation detection via `verify_chain(strict_against_counter=True)`
  is **active for entries written AFTER the canary-wire commit**.
- Pre-wire entries are protected only by the per-entry HMAC chain
  (which detects modification but NOT truncation of an unmodified suffix).
- If you upgrade from <v1.11.2 to v1.11.x with this fix and run
  `verify_chain(strict_against_counter=True)` on a log that has pre-wire
  entries, the counter is initially 0 (or absent); first post-wire emit
  advances to 1. Walker-count over the full log will exceed the counter
  — `verify_chain` treats walker-count >= counter as PASS (this is
  intentional for the migration window).
- For a "clean" tail-truncation defense across the full log, archive the
  pre-wire log and start a fresh one at the upgrade point.

**Threat model: counter sidecar plaintext (deferred hardening)**

The chain-length sidecar at `<state>/audit-log.chain-length` is stored
as a plaintext decimal counter. An attacker with **write access to the
audit directory** can:

1. Truncate `audit-log.jsonl`.
2. Walk the truncated file, count remaining lines (e.g., N').
3. Overwrite the sidecar with N'.

After this, `verify_chain(strict_against_counter=True)` returns PASS
even though the log was truncated. The counter as currently designed
defends against **truncate-only attackers** (e.g., a write-only logging
collector that exposes the log path but not the sidecar location), not
against attackers with full audit-dir write access.

Hardening track: HMAC-protected counter sidecar (audit-v2 follow-up
**C6-P0-03b**). Format will become `<n>:<hmac(secret, "chainlen:" + n)>`
with `hmac.compare_digest` verification on read. Until then, treat the
canary as a forensic indicator, not a tamper-proof seal.

**Recovery procedure when canary fires:**

If `verify_chain(strict_against_counter=True)` returns
`STATUS_TAMPER` with `reason="chain_length_truncation"`:

1. Do NOT delete or overwrite the existing log.
2. Capture the current state:
   `cp -p audit-log.jsonl audit-log.tampered.jsonl`
3. Capture the sidecar:
   `cp -p audit-log.chain-length audit-log.chain-length.tampered`
4. Inspect via
   `python3 .claude/scripts/audit-query.py --tail 100 --verify-chain`.
5. Report incident via the workflow in `docs/INCIDENT-RESPONSE.md`.
6. Owner-physical decides whether to: (a) preserve the log and start a
   fresh chain (recommended for forensic preservation), or (b) accept
   the loss and rotate.

## Recovery patterns by failure mode

### Case 1 — CLI killed mid-tool-call

**Recovery:**
1. `git status` — anything dirty?
2. `git log --oneline -5` — last commit; what was in flight?
3. `audit-query.py recent --limit 20` — last 20 events; what tool was running?
4. Resume by re-running the last tool call OR completing the in-progress edit.

### Case 2 — Mid-debate, terminal lost

**Recovery:**
1. Read plan file: `.claude/plans/PLAN-NNN-<slug>.md` → `status:`?
2. Read consensus if exists: `.claude/plans/PLAN-NNN/audit/round-N/consensus.md`
3. List archetype verdict files: `ls .claude/plans/PLAN-NNN/audit/round-N/`
4. If verdict files incomplete → re-spawn missing archetypes (per debate-orchestrate.py lifecycle).
5. Run `consensus.md` synthesis when all 5 (or 4 with anomaly note) verdicts present.

### Case 3 — Owner ceremony interrupted before GPG signature

**Recovery:**
1. Check `ls .claude/plans/PLAN-NNN/architect/round-N/`
2. If `approved.md` exists but `.asc` missing → re-run ceremony (ceremony script is idempotent — checks for existing files).
3. If both exist → ceremony complete, CEO can continue.
4. If neither exists → ceremony hasn't started; run `OWNER-PLAN-NNN-CEREMONY.sh`.

### Case 4 — Mid-phase-execute, agent spawn died

**Recovery:**
1. `audit-query.py grep --action agent_spawn --since-minutes 30`
2. Identify which spawn was last + whether it completed (look for matching `agent_completed` event).
3. If incomplete → re-spawn with same prompt; the agent will re-do the work (idempotent at framework level since file edits are durable in git).
4. If completed but verdict file missing → check `.claude/plans/PLAN-NNN/audit/round-N/<archetype>.md` — may be there but un-committed.

### Case 5 — Kernel override fired during emergency edit

**Recovery:**
1. `audit-query.py grep --action veto_triggered --reason kernel_override_used --since-hours 24`
2. Read the override's reason-slug + ack message.
3. Document the incident in a memory file (`feedback_kernel_override_<date>.md`).
4. Decide: was the override warranted? If yes, document. If no, revert + add to ADR-079 phantom rejection list.

## Anti-patterns

### ❌ Don't checkpoint at API boundary

The framework does NOT export `framework.checkpoint()` / `.resume()`.
If you find yourself reaching for one, instead:
- Write to memory files (durable cross-session).
- Update plan file frontmatter (durable timestamped state).
- Commit incrementally (durable per-step state).
- Audit-log captures it for free.

### ❌ Don't store mid-flight state in tmpfs

If CEO needs cross-session state, write to `.claude/plans/PLAN-NNN/`
(committed) or memory file (durable in `~/.claude/`). Tmpfs / `/tmp/`
is for transient fixtures only (e.g. PLAN-060 `/tmp/h4-layer7-fixtures/`).

### ❌ Don't expect `audit-log.jsonl` to recover work that was never written

Audit-log captures what happened, not what was intended. If a plan
phase was attempted but no commit landed and no audit event fired,
treat that phase as un-started.

## When this doc fails you

If you hit a recovery scenario this doc doesn't cover:

1. Open a memory file `feedback_recovery_<scenario>.md` describing
   the gap.
2. Update this doc in the next plan closeout.
3. If the gap is structural (i.e. existing artifacts don't capture
   the state), reopen ADR-086 with the new evidence.

## References

- ADR-086 — Phase checkpointing REFUSED (this doc's parent)
- ADR-085 — Framework landscape Claude-only thesis
- ADR-055 — Audit-log HMAC chain (durable event ledger)
- ADR-058 — Pre-plan brainstorm (spec.md durable state)
- ADR-010 — Sentinel discipline (Owner-signed canonical state)
- `CLAUDE.md` §Memory section — memory protocol
- `SPEC/v1/audit-log.schema.md` — event ledger schema
