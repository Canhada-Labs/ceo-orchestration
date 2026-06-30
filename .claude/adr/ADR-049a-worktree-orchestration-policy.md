---
id: ADR-049a
title: Worktree orchestration policy — cooperative, not adversarial isolation
status: ACCEPTED
created: 2026-04-22
accepted_at: 2026-04-22
proposed_by: CEO (Session 52, PLAN-050 Phase 6.5)
accepted_by: Owner (round-17 sentinel, GPG key 00000000…00000000, Session 56)
related_plans: [PLAN-050, PLAN-017, PLAN-051]
related_adrs: [ADR-049, ADR-031]
blast_radius: L3-wide
supersedes: none
superseded_by: none
---

**Status:** ACCEPTED (2026-04-22, round-17 canonical promote)

# ADR-049a — Worktree orchestration policy (cooperative, not adversarial isolation)

> **Status:** ACCEPTED. Canonical at `.claude/adr/ADR-049a-worktree-orchestration-policy.md`
> via round-17 GPG-signed sentinel promote (Session 56 commit
> `42c104a`). Enforcement binding live. Flipped DRAFT-STAGED →
> ACCEPTED in PLAN-051 Phase 2 (2026-04-22).

> **Note on ID adjacency:** this ADR (ADR-049a) governs **worktree
> orchestration policy**. The numerically adjacent ADR
> [`ADR-049`](ADR-049-policy-engine-dual-path-deprecation.md) covers
> **policy engine dual-path deprecation** — a structurally unrelated
> topic. The shared `049` prefix is a drafting-order coincidence
> (PLAN-050 wrote the `049a` suffix to avoid colliding with the
> already-drafted ADR-049 number). Both are PRESERVED rather than
> renamed to keep git-blame stable (per `F-A-IDA-T-0010` PLAN-087 W-F
> housekeeping). The two ADRs neither supersede nor amend each other.

## Context

PLAN-017 (autonomous loop parallelism) + PLAN-050 Phase 7 require
per-loop filesystem isolation so that N swarm iterations can run in
parallel without stepping on each other's working trees. The natural
mechanism in git is `git worktree add`, which creates a sibling
checkout sharing the main repo's `.git/objects/`, `.git/refs/`, and
per-worktree metadata under `.git/worktrees/<name>/`.

PLAN-017 Round 1 deferred the worktree decision pending this ADR:
the question the debate could not settle in 2026-04-21 is **what
isolation contract does `git worktree` actually provide, and is it
sufficient for the threat model?**

PLAN-050 Sprint 31 debate Round 1 (2026-04-22) surfaced four
additional concerns that must be answered here before Phase 7
executes:

1. **Shared object DB** — `.git/objects/` is one store; a malicious
   loop that writes arbitrary object blobs contaminates siblings.
2. **Shared index lock** — parallel `git` commands in sibling
   worktrees contend on `.git/index.lock`, causing intermittent
   failures and cascading retries.
3. **Sibling filesystem readability** — worktree A has
   unrestricted read access to worktree B's working tree. Any secret
   staged in B is visible to A via `cat ../loop-B/some-file`.
4. **Kill-switch races** — if a loop `fork()`s faster than the
   parent can `kill()`, the fork escapes the kill-switch unless
   process groups (`setsid` + `killpg`) are used.

## Decision drivers

- **Swarm production requires a decided isolation boundary.** A
  scaffold that says "isolation is 'good enough'" is not a
  deliverable — it is a deferred decision masquerading as a
  feature.
- **The Owner runs on Darwin (macOS).** Any isolation primitive that
  requires Linux-only kernel features (namespaces, landlock, prctl)
  must have a documented macOS-native equivalent OR be gated to
  Linux-only with an explicit unsupported-mode on Darwin.
- **Adversarial isolation is out of scope for Sprint 31.** Delivering
  fully-sandboxed loops (separate UIDs, namespaces, landlock /
  bwrap) is a separate plan. Sprint 31 ships cooperative isolation
  with documented threat model.
- **Same-LLM reality.** All loops run the same underlying Claude
  model. A "compromised loop" in the adversarial sense requires a
  prompt-injection attack that pivots a loop into adversarial
  behavior. The dominant risk in the same-LLM regime is **resource
  exhaustion and coordinator deadlock**, not **tenant escape**.

## Decision

**Adopt `git worktree`-based loop isolation as COOPERATIVE, NOT
ADVERSARIAL.** Specifically:

### What git worktree IS sufficient for

1. **Isolating working-tree state across concurrent loops** — each
   loop sees its own checkout; `git diff` is per-worktree; CI
   commits from one loop do not appear in another.
2. **Atomic completion** — a loop either succeeds (merges to a
   staging branch) or fails (worktree is discarded). No
   half-applied state contaminates main.
3. **Branch/HEAD independence** — each worktree has its own HEAD;
   `git checkout` in loop A does not affect loop B.

### What git worktree is NOT sufficient for

1. **Preventing sibling worktree read access** — worktree A can
   `cat ../loop-B/secret.txt` freely. Any secret staged in B is
   visible to A.
2. **Preventing shared-object-DB contamination** — a loop that
   writes adversarial git objects contaminates all siblings.
3. **Preventing resource exhaustion** — a runaway loop can fork-bomb
   and starve siblings of CPU / FDs / memory. Process-group
   + resource-cap mitigations (Phase 7 kill-switch layers 4+6 +
   circuit breakers 6-9) are the correct defense; worktree
   isolation alone does not suffice.
4. **Defending against malicious commit objects** — a loop that
   writes a commit with crafted parent/tree SHAs can confuse
   sibling `git log` views. Content-addressable storage is
   adversarial-safe at the object level (SHA-1 is
   collision-hard-enough for this threat), but metadata
   interpretation (refs, reflog) is shared state.

### Consequences

Accepting this decision means:

1. **Documentation**: PROTOCOL.md and
   `docs/AUTONOMOUS-LOOP-GUIDE.md` explicitly state "loops are
   cooperatively isolated" in their threat-model sections.
2. **Circuit breakers are mandatory** (not optional) — Phase 7 must
   ship all 6 kill-switch layers and circuit breakers 6-9 (disk /
   FDs / wall-clock / parent-death) before marking PLAN-017
   production-ready.
3. **Secrets MUST NOT be staged in loop worktrees** — worktrees are
   expected to contain task-specific code, not credentials. Any
   credential-needing step must read from an
   environment-variable-scoped path outside the worktree (e.g.
   `$HOME/.netrc`, `~/.ssh/`).
4. **An adversarial-isolation follow-up ADR is flagged** for Sprint
   32+ if the project evolves to untrusted-tenant use cases
   (adopter running untrusted user code inside loops). This ADR
   does NOT preclude future tightening; it documents the
   present contract.

## Portability matrix

| Feature | Linux | Darwin | Windows |
|---------|-------|--------|---------|
| `git worktree add / remove / prune` | ✅ | ✅ | ✅ |
| `os.setsid()` (new process group) | ✅ | ✅ | ❌ |
| `os.killpg(pgid, signal)` | ✅ | ✅ | ❌ |
| `prctl(PR_SET_PDEATHSIG)` (parent-death) | ✅ | ❌ (absent) | ❌ |
| `select.kqueue` + `NOTE_EXIT` (parent-death) | ❌ | ✅ | ❌ |
| `unshare(CLONE_NEWPID)` (PID namespace) | ✅ (rootless OK) | ❌ | ❌ |
| `landlock` / `bwrap` (fs sandbox) | ✅ (recent) | ❌ | ❌ |
| `fanotify` (fs-escape watch) | ✅ | ❌ | ❌ |
| `fsevents` (fs-change watch) | ❌ | ✅ | ❌ |
| `inotify` (fs-escape watch) | ✅ | ❌ | ❌ |

**Tier-1 support:** Linux + Darwin. **Windows:** explicitly
unsupported for swarm production (`CEO_SWARM=1` on Windows emits
a startup warning and refuses).

Portability abstractions land in:

- `.claude/hooks/_lib/parent_death.py` — `_prctl_backend` (Linux) +
  `_kqueue_backend` (Darwin) + `_polling_backend` (Windows fallback,
  advisory-only).
- `.claude/hooks/_lib/process_group.py` — `setsid_then_exec()` +
  `killpg_wrapper()` stdlib-portable on POSIX; Windows raises
  `NotImplementedError` with explicit message.

## Decision matrix considered

| Option | Isolation | Portability | Owner ceremony | Verdict |
|--------|-----------|-------------|----------------|---------|
| `git worktree` (this ADR) | Cooperative | Linux + Darwin | None (git native) | **ACCEPTED** |
| Separate UIDs (`sudo -u loop-N`) | Adversarial | Linux (sudo) | Heavy (sudoers edit) | Deferred to Sprint 32+ |
| `bwrap` / `firejail` sandbox | Adversarial | Linux-only | Package dependency | Deferred |
| `landlock` (recent Linux) | Adversarial | Linux 5.13+ only | Kernel dependency | Deferred |
| Docker-per-loop | Adversarial | Everywhere | Heavy (daemon) | Overkill for Sprint 31 |
| No isolation (single working tree) | None | Universal | None | REJECTED (race-prone) |

## Kill-switch matrix (6 layers) — referenced by PLAN-050 Phase 7

| Layer | Name | Trigger | Mechanism | Portability |
|-------|------|---------|-----------|-------------|
| 1 | Env kill-switch | `CEO_SWARM=0` env var | Startup refusal | All |
| 2 | File kill-switch | `touch .claude/swarm-kill` | Coordinator polls | All |
| 3 | CLI abort | `coordinator.py --abort <swarm_id>` | Targeted SIGTERM | All |
| 4 | SIGTERM + grace + SIGKILL | Resource cap exceeded (Tier 1) | 5s grace → `killpg(SIGKILL)` | Linux + Darwin |
| 5 | Instant SIGKILL | VETO triggered / kill-file detected (Tier 2) | No grace → `killpg(SIGKILL)` | Linux + Darwin |
| 6 | Parent-death watchdog | Coordinator process dies | `prctl` (Linux) / `kqueue NOTE_EXIT` (Darwin) | Linux + Darwin |

## Circuit breakers 6-9 (referenced by PLAN-050 Phase 7)

| CB | Metric | Trigger | Action |
|----|--------|---------|--------|
| 6 | Disk usage per worktree | ≥2 GiB | Force Tier 1 kill |
| 7 | File descriptors per loop | ≥1024 | Force Tier 1 kill |
| 8 | Wall-clock per iteration | ≥600 s | Force Tier 1 kill |
| 9 | Parent-death | Coordinator PID dies | Layer 6 fires on all loops |

## Implementation contract

1. `swarm/coordinator.py` uses a **worktree pool** (not per-iter
   allocation): `N=max_parallel` worktrees allocated at
   `init_swarm()`; each iteration reuses a pool slot via
   `git reset --hard HEAD`. This cuts per-iter git overhead from
   ~1207ms to ~50ms (measured Darwin 25.4.0).
2. Each loop spawns its subagent in a fresh process group
   (`os.setsid()` in child pre-exec). Kill-switch sends signals to
   the negative PID: `os.killpg(-pgid, SIGKILL)`. Protects against
   fork-race kill evasion.
3. **Circuit breaker 9** (parent-death) uses `parent_death.py`
   abstraction; all backends call same `watch_parent()` API.
4. **Worktree escape detector** (optional, Phase 7 stretch):
   `fanotify` (Linux) / `fsevents` (Darwin) watcher triggers Tier
   2 SIGKILL if any loop `open()`s a path outside its own worktree.
   Default off; gated `CEO_SWARM_ESCAPE_DETECTOR=1`.
5. **Benchmark reporting**: any swarm metrics MUST itemize
   `git_overhead_ms` separately from `work_ms`. A benchmark that
   reports combined wall-clock is not Phase 7 production-ready.

## Validation

Phase 7 cannot be marked done unless:

- [ ] `.claude/hooks/_lib/parent_death.py` exists and unit-tests
  both Linux + Darwin backends.
- [ ] `.claude/hooks/_lib/process_group.py` exists with
  `setsid_then_exec()` + `killpg_wrapper()`.
- [ ] `swarm/coordinator.py` implements worktree pool (not per-iter).
- [ ] `swarm/kill_switch.py` implements 2-tier abort (5s grace vs
  instant SIGKILL).
- [ ] TLA+ specs include invariants for **worktree-pool
  reentrance** and **process-group-scoped kill-switch coverage**
  (named in plan: `NoDeadWorker`, `ProgressGuaranteed`,
  `KillSwitchHalts`, `MaxParallelRespected`).
- [ ] TLC model-check completes ≤60 s at `MaxIter=4, MaxParallel=2`.
- [ ] `docs/AUTONOMOUS-LOOP-GUIDE.md` §Threat model documents
  cooperative-isolation contract.
- [ ] `PROTOCOL.md` §Autonomous-loop-parallelism references this
  ADR.

## Out of scope for this ADR (flagged for future ADRs)

- **ADR-049b (future)**: Adversarial isolation via namespaces or
  UID separation, for adopters running untrusted code in loops.
- **ADR-049c (future)**: Cross-loop communication contract (when
  loops MUST share state, what is the allowed medium? — e.g.
  TournamentScorer reading all outputs).
- **ADR-049d (future)**: Worktree-pool resize under load (auto-scale
  vs. static `max_parallel`).

## Acceptance

**Status: DRAFT-STAGED in non-canonical plans/.** Next steps to promote:

1. Debate Round 1 (5 archetypes per PROTOCOL.md §Debate):
   Staff Code Reviewer, Security Engineer, Performance Engineer,
   Staff Backend Engineer, DevOps Engineer.
2. Converge on isolation contract. If ≥2 archetypes flag an attack
   path invalidating the "cooperative" premise, re-open with
   adversarial options.
3. Owner signs round-17 canonical sentinel scoping
   `.claude/adr/ADR-049a-*.md`.
4. `git mv .claude/plans/PLAN-050/adr-drafts/ADR-049a-*.md
   .claude/adr/ADR-049a-*.md` under sentinel.
5. Flip frontmatter `status: DRAFT-STAGED` → `status: ACCEPTED`.
6. Proceed with Phase 7 implementation.

## Enforcement commit

**Enforcement commit:** `42c104a` (Session 56 round-17 canonical
promote, 2026-04-22). This commit atomically moved ADR-049a from
`.claude/plans/PLAN-050/adr-drafts/` to canonical `.claude/adr/`
under GPG-signed round-17 sentinel (Owner's Ed25519 key
00000000…00000000, signature verified via `gpg --verify`).

Promotion chain:
- Round-17 sentinel: `9e31517` (GPG detach-sign Owner approved.md)
- Canonical promote: `42c104a` (5× git mv staged → canonical; this
  commit is the Enforcement commit)
- Closure pointer: `73ec919` (Session 56 closeout, PLAN-050 done)
- PLAN-051 Phase 2 ACCEPT flip: `<this commit>` (DRAFT-STAGED →
  ACCEPTED + status field edit)

Live enforcement via `.claude/scripts/swarm/_worktree_pool.py`
(Session 54 commit `11eb9f1`) — honors the cooperative-not-
adversarial semantics declared in §Decision.

---

## Amendment 1 — Enforced parallel-writer rule (PLAN-125 WS-2)

**Status:** PROPOSED (Owner GPG required to promote to ACCEPTED-AMENDED).
**Proposed_by:** CEO (PLAN-125 WS-2, kooky-harvest, S2xx).
**Related:** PLAN-125 (§3/§4/§9 MF-SEC-6/7, MF-QA-C, MF-4); the S191
worktree-bleed lesson (`feedback_background_agent_worktree_bleeds_into_main_checkout.md`).
**Relationship to the base ADR:** **additive.** AMEND-1 tightens
*enforcement* on the writer path; it does NOT reopen adversarial
isolation (still deferred to the flagged ADR-049b). The §"What git
worktree is NOT sufficient for" caveats (sibling-read, shared-object-DB)
remain unchanged.

### Why

The base ADR adopted `git worktree` isolation as the cooperative
substrate, and `.claude/scripts/swarm/_worktree_pool.py` provides
create/dispose/crash-safe slots. But the pool is an **allocator/recycler,
not an enforcement guard** — nothing *forces* a writer onto its slot. The
S191 bleed slipped through exactly there: a background agent's
worktree/rsync wrote AND reverted canonical files in the shared **main
checkout** because no boundary asserted "the writer's resolved write
target is inside its assigned worktree." AMEND-1 adds that one enforced
rule.

### 1. Enforced rule

When **parallel-writer mode is active** (the opt-in env below is set), a
background/parallel writer **NEVER operates on the shared main checkout.**
Every write the hook can RESOLVE (`Edit`/`Write`/`MultiEdit` targets, plus
`Bash` writes via recognized shapes — redirects, `cp`/`mv`/`rsync`/`install`/
`ln`/`touch`/`mkdir`/`rmdir`/`rm` incl. `-t`/`--target-directory`, `git` write
subcommands, and a `cd`/`git -C` retarget; `$VAR`/`~` are expanded first and a
residual `$`/backtick fails CLOSED) MUST resolve to a path inside the writer's
assigned dedicated worktree; otherwise it is **DENIED (fail-CLOSED).**
Enforcement is **UNCONDITIONAL once active** — the opt-in env gates *whether the
mode is on*, not *whether the boundary is checked* (MF-SEC-6).

**Scope boundary (cooperative / accidental-bleed model — do NOT overclaim).**
This is a *static* Bash analysis, not a sandbox. It catches the accidental S191
bleed, not a malicious or arbitrary writer: an unknown program that writes into
main via a flag the hook cannot know is a destination (e.g.
`python build.py --out "$CLAUDE_PROJECT_DIR/x"`) is NOT detectable, because
statically distinguishing a write-arg from a read-arg for an arbitrary command
is impossible and denying every main-referencing arg would also break
legitimate READS from main (reads are not the bleed). The strong guarantee —
a writer that physically cannot touch main (read-only bind-mount / separate FS
namespace) — is **ADR-049b**, deliberately out of scope here.

### 2. Self-identification contract (no IPC, no daemon — MF-FIN-4)

The writer declares itself via two env vars it sets in its own process
environment:

- `CEO_PARALLEL_WRITER=1` — "I am a parallel/background writer."
- `CEO_ASSIGNED_WORKTREE=<abs-path>` — the pool slot it `acquire()`d
  (`<repo>/.claude/swarm-worktrees/loop-<i>`).

Absence of `CEO_PARALLEL_WRITER` = owner/normal session = the rule is
**inert** (default-OFF, zero impact on the common case — one env lookup →
allow). This is the same already-validated idiom S191's fix used
(`CEO_WS3_APPLY_OK=1`, set only by the ceremony). The hook does NOT infer
background-ness from the process tree (that genuinely would need IPC); the
writer announces itself, and the decision uses only (a) the opt-in env,
(b) the assigned-worktree env, and (c) the hook process's own
`os.getcwd()` — all in-process and synchronous. If `CEO_PARALLEL_WRITER=1`
but `CEO_ASSIGNED_WORKTREE` is unset/empty → **DENY all writes** (a
parallel writer with no slot must not write anywhere).

### 3. Boundary placement

Enforcement is a **NEW PreToolUse writer hook**
(`.claude/hooks/check_worktree_writer.py`, matcher
`Bash|Edit|Write|MultiEdit`) — **NOT** `swarm_enable_gate` (which only
gates swarm *class* enablement and observes no `Bash`/`Edit` calls), and
**NOT** the live `coordinator.py` (still a scaffold; worktree
orchestration deferred). cwd is resolved at the PreToolUse decision point;
a later `cd` / `pushd` / `git -C` / `--git-dir` / `--work-tree` inside a
Bash command is parsed and re-resolved, so there is **no TOCTOU window**
(MF-SEC-6). An opaque indirection the hook cannot statically follow
(`eval`, `xargs`, interpreter `-c <body>`, etc.) is treated **fail-CLOSED**
while active.

### 4. Argv-git discipline (MF-SEC-7)

The substrate already runs git via **argv arrays, never a shell string**
(`_worktree_pool._run_git`), which closes *shell* injection — all the
upstream `kooky` argv discipline buys. argv-safety does **NOT** close
*option* injection: a ref/path beginning with `-` is still parsed as a git
flag. Therefore any attacker-influenceable ref/path the hook (or any
future writer wiring) passes to git MUST:

- be preceded by a **`--` end-of-options separator**; and
- pass an **allowlist regex `^[A-Za-z0-9._/-]+$`** that **rejects a
  leading `-`** and **rejects `..`** (path traversal),

before use. Fail-CLOSED on any ref/path that fails the regex while
parallel-writer mode is active.

### 5. Scope honesty (MF-4 — anti-vanity, BINDING)

This is **infrastructure for non-conflicting parallel reads/reviews**
(fan-out reviewers — the pattern we already use). It makes **NO throughput
/ speed claim.** PLAN-123 E2 closed the speed thesis (S201). The guard's
job is to stop the *accidental* S191 bleed (a well-behaved bg writer whose
path resolution lands on main), not to contain a *malicious* writer (out
of scope — ADR-049b). The env-based scheme trusts the writer to set its own
flag; a writer that "forgets" `CEO_PARALLEL_WRITER` is simply treated as
the owner session — the correct fail-direction for the cooperative (not
adversarial) threat model this ADR already declares (§Same-LLM reality).

### Validation

- [ ] `.claude/hooks/check_worktree_writer.py` exists, default-INERT
  unless `CEO_PARALLEL_WRITER=1`, fail-CLOSED when active.
- [ ] Registered PreToolUse `Bash|Edit|Write|MultiEdit` in BOTH
  `.claude/settings.json` and `templates/settings/settings.base.json`
  (template-dogfood parity green).
- [ ] `.claude/hooks/tests/test_worktree_writer.py` covers: deny a write
  whose resolved cwd/target is the shared main checkout while active;
  allow the same write inside the assigned worktree; `--`+allowlist
  ref/path discipline; per-PID/slot isolation; default-OFF allow.
- [ ] No change to `_worktree_pool.py` semantics; the pool remains the
  cooperative substrate (§Decision unchanged).
