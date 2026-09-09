# Changelog

All notable changes to **ceo-orchestration** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Scope.** This log records *user-visible* changes — new skills, hooks, slash
> commands, schema/contract changes, and behavior an adopter would notice after
> installing or upgrading the framework. Internal refactors, test-only churn, and
> release-engineering bookkeeping are omitted. Counts cited below (as of
> v1.4.0: 166 skills, 27 slash commands, 198 ADRs, 71 `_lib` modules) are
> reproducible from the repository via
> `bash .claude/scripts/local/verify-counts.sh`.

---

## [1.4.0] - 2026-09-07

Continuity, delivery and installer-safety train (PLAN-179 compaction
continuity and work-boundary persistence; PLAN-182 per-project audit
isolation; PLAN-183 delivery routes and an upgrade that finally
delivers `docs/` and `.github/`; PLAN-185 installer write
confinement; PLAN-169 a `user` profile derived from the base instead
of hand-maintained). The headline for an adopter is that
`upgrade.sh` now delivers the two trees it silently skipped for four
releases, and that every delivered-template destination is now confined
to the directory you hand it (the seams that are not — backups, the
schema-doc refresh, `.gitignore` appends, the dispatcher copies, the
`state/` seed — are signed conditions of this rc, with the pre-upgrade
checks in `docs/UPGRADE-PROCEDURE.md`). Two security fixes in the install path, one
audit-log scope change adopters share a machine over, and the honest
part: the compaction-continuity feature this train is named after
shipped only after its first design was measured and found to deliver
nothing. As always: governance and auditability — no speed claim.

### Fixed — `upgrade.sh` silently skipped `docs/` and `.github/` (PLAN-183, ADR-194)

The most consequential adopter-visible defect closed in this release.
From v1.0.0 through v1.3.0, `scripts/upgrade.sh` never delivered the
`docs/` and `.github/` trees that `install.sh` delivers — an adopter
who installed once and upgraded thereafter kept the *original*
`docs/BRANCH-PROTECTION.md`, `docs/rotation-log.md`, `.github/CODEOWNERS`
and the two CI workflow templates forever, with no warning.

- **Upgrade now delivers both trees**, hash-gated against the git
  generations of the SOURCE file: a byte-pristine copy of a known prior
  framework generation is replaced, anything you edited is PRESERVED
  loudly. A pre-existing copy of yours that is byte-identical to ANY
  generation, the current one included, counts as the framework's own
  copy too — replaced or mode-normalised, and registered as
  framework-owned — even if the framework never delivered it (signed
  condition of rc.1: edit or move such a file before upgrading).
  Backups go to `.claude.bak/<timestamp>` without the destination
  confinement the deliveries get: keep that path absent or empty, never
  a symlink (signed condition of rc.1). Delivery is registered
  only after it actually happened, when a prior registration's digest
  still matches, or — the third route — when a pre-existing file's bytes
  equal the current or a historical generation of the source (naked byte
  equality; signed conditions 5 and 42). A delivery that
  fails its PRECONDITION (route table, source, transform) exits 3 and
  persists `upgrade_succeeded: false` in the install-state rather than
  recording a full upgrade that did not happen (`6304f66`); a failure of
  the WRITER or the RENDERER after a route was selected (a read-only
  `docs/`, a failed tempfile or rename, a failed CODEOWNERS render) is
  still reported PRESERVED with exit 0 — signed condition of rc.1: read
  the delivery summary, a PRESERVED route you never edited is a failed
  delivery. A sensitive path already TRACKED by git
  (`.claude/settings.local.json`, `.claude/state`,
  `state/mcp_client_secrets`) aborts the upgrade AFTER hooks, scripts and
  settings were rewritten (signed condition of rc.1: `git ls-files` over
  those paths must print nothing before upgrading).
  A route whose SOURCE file is missing (or not a regular file) in the
  executing checkout is counted SKIPPED, not failed — the run still exits
  0 (signed condition of rc.1: upgrade from a complete checkout and read
  the delivery summary; any SKIPPED route without `--pin` means an
  incomplete upgrade).
  A route whose transform has no renderer in the running version is
  a failed delivery too: named, `upgrade_succeeded: false`, exit 3
  (`5518888`, all four sites of the class).
- **One route table, three readers.** `scripts/delivery-routes.tsv` is
  now the single answer to "which source file produces this
  destination?", read by the manifest generator, `doctor.sh` and the
  parity classifier — no reader carries a private copy. Four separate
  defects (`upgrade.sh` not delivering, the parity classifier and the
  manifest generator resolving the wrong source, and `doctor.sh`
  REPAIRING with the wrong file) all had the same shape: no single
  owner for that question. Contract: ADR-194 (`b6de7cf`, `aaf32c7`,
  `6304f66`, `3bc3638`).
- **`doctor.sh` repaired deliveries from the wrong source** before this
  release; the positive control reproduced a leak of the maintainer's
  live `.github/CODEOWNERS` into an adopter repo. `doctor.sh` now reads
  the same route table (`6304f66`).
- **Shallow-clone caveat, named:** in CI with `actions/checkout` at
  depth 1 the hash gate cannot see older generations, so files are
  PRESERVED (safe) and reported `STALE`. Deepen the history before
  upgrading in CI if you want the refresh.

### Security — delivered-template destinations are confined to the target (PLAN-185, ADR-196)

- **`install.sh` wrote outside `$TARGET`** when a destination path was a
  pending symlink or hardlink. One destination-confinement predicate now
  lives in `scripts/_framework_manifest_set.sh`; `install.sh` pre-flies
  every delivered-template destination before the first write and
  refuses by name, `upgrade.sh` consumes the same predicate. E2E in
  bytes: 105/0 after the cure against 22/33 before it (`cc00235`).
  Several seams stay outside that preflight in this release candidate
  and are signed conditions of rc.1: the `state/mcp_client_secrets`
  seed (a symlinked `TARGET/state` is followed by `mkdir -p`/`chmod`);
  a refused SOURCE template (symlink outside the checkout) that install
  reports as `SKIP` and upgrade as `PRESERVED` while still exiting 0; a
  source MISSING from the executing checkout (`SKIP`, exit 0, on both
  install and upgrade); the `.gitignore`/`.claude/.gitignore` appends
  and the `.claude/dispatcher/` copies, which test `-L` only, so a hard
  link there is written through; and `install_dispatcher`, which
  re-copies unconditionally on a rerun (edited dispatcher files are
  overwritten — back them up first); and the deny-baseline merge of
  `install.sh`, which writes a PID-named sibling of `.claude/settings.json`
  outside the preflight (a pre-placed symlink there is written through —
  the `find` check over `.claude/` in `docs/UPGRADE-PROCEDURE.md` catches
  it; run it before a fresh install too).
- **`--github-owner` with a `/` in it left `.github/CODEOWNERS` at zero
  bytes, permanently.** The handle grammar is now shared by producer and
  consumer, the file is rendered through a pipe and written atomically,
  and a truncated CODEOWNERS is recovered from delivery EVIDENCE
  (`cc00235`) — evidence meaning a manifest line that NAMES the path;
  the line's digest grammar is not validated, so keep the manifest
  intact and delete (do not empty) a CODEOWNERS you switched off before
  re-running the installer (signed condition of rc.1).
- **`uninstall.sh` followed a crafted manifest out of the target.** The
  install manifest is a plain file in your repo and is NOT
  integrity-checked before the removal walk; pre-cure, a record naming
  `../outside/victim.txt` was REMOVED, and with a symlinked `docs`
  component the walk deleted an outside file and the backup archived
  bytes read through the link. Every removal, every backup entry and
  every restore member OUTSIDE `.claude/` is now tested lexically
  (absolute paths, `..` segments, control characters, whitespace and glob
  metacharacters, option-like `-` leaders) and physically (a symlinked
  ancestor under the target) (`6160578`); the `.claude` subtree of a
  restore archive is still extracted whole after a name-only check
  (signed condition 57 of rc.1: restore only unmodified archives this
  uninstaller produced).
- **`doctor.sh` stopped discarding unsafe manifest records in silence** —
  traversal, absolute path, any control byte, symlinked ancestor,
  malformed digest and duplicate relpath are each a NAMED discard, capped
  at 20 and folded into `UNRESOLVED` (rc 1); a manifest containing a NUL
  is refused before the parse (`ba15c71`).
- A fail-closed census of installer write sites
  (`check-installer-write-safety.py`) ships as a RATCHET in `validate.yml`
  with its blind spots declared in the plan, not papered over.

### Changed — audit log resolves per PROJECT, not per `$HOME` (PLAN-182, ADR-001)

**Adopter-visible if you run the framework in more than one repository
under the same `$HOME`.** Runtime state — the HMAC audit log, its key,
lock, errors, salt and sidecars — now resolves through one family
resolver (`.claude/hooks/_lib/runtime_paths.py`) using Claude Code's own
path-based project slug, instead of a literal `ceo-orchestration`
directory shared by every project (`9de4efc`, `965fb13`, `3d16070`).

- What this buys, measured: chains that no longer interleave, correct
  `project` attribution for the emitters that carry the field (a handful
  of newly specified actions still omit `project` or `session_id` and
  cannot be attributed in a shared `CEO_AUDIT_LOG_PATH` — rc.1 condition
  23), a `verify_chain()` that means something per project — for stretches
  written by one writer at a time: the previous HMAC is still read before
  the log lock is taken, so two parallel writers can chain to the same
  predecessor and a break is then reported that nobody caused (signed
  condition 67 of rc.1; same order as v1.3.0) — and a per-project HMAC key
  and salt — so `prompt_sha256` stops correlating across your
  repositories. The per-project key is minted on first use and that first
  mint is not exclusive: create it with a single writer before the first
  session (signed condition 68 of rc.1; `docs/UPGRADE-PROCEDURE.md`,
  check 11).
- **The old location is not migrated for you.** The pre-v1.4.0 chain
  under `$HOME/.claude/projects/ceo-orchestration/` stays where it is;
  `SPEC/v1/audit-log.schema.md` records the change as v2.58 and names the
  legacy path.
- **Plan state and scratchpads move too, and are not migrated either.**
  `state_store.py` resolves through the same family resolver, so a
  repository with an ACTIVE plan on v1.3.0 opens a NEW, empty state
  store after the upgrade — `/resume` and inter-agent handoffs report
  missing state while the old SQLite files stay on disk under the
  legacy directory. Two documented routes: set `CEO_PROJECT_NAME` to
  the legacy slug (the explicit escape hatch in `state_store.py`) until
  the plan closes, or copy `<legacy>/state/` into the new per-project
  directory (`python3 .claude/hooks/_lib/runtime_paths.py --state-dir`).
  A migration is a signed condition of rc.1 (see the release envelope).
- **The limit that does NOT go away:** under the same UID one project's
  process can still read another's `0700` directory and `0600` key. A
  real boundary needs a separate UID; that is out of scope by decision,
  and said here rather than implied away.
- The resolver ships with a CLI
  (`python3 .claude/hooks/_lib/runtime_paths.py --state-dir|--slug|--project-dir
  [--project PATH]`) used by the pre-push templates and by
  `ceo-backup`/`ceo-restore` (`3d16070`).

### Changed — upgrade withholds hook registration when the ceremony is unknown (PLAN-169, `5930974`)

- `upgrade.sh` now DERIVES which hooks to register from the settings
  template of the ceremony you actually installed, instead of a
  hardcoded roster that would have silently promoted a `--ceremony user`
  install to the maintainer profile.
- **New behavior you may see:** with no readable install-state, no
  `--ceremony` flag and no `CEO_UPGRADE_CEREMONY`, the upgrade reports
  `PARTIAL (ceremony unknown)` and registers NO hooks — only the settings
  both profiles declare identically. Pass `--ceremony maintainer` or
  `--ceremony user` to register the profile you installed. The previous
  behavior (inferring, and getting it wrong) could turn an advisory hook
  into a blocking one.

### Changed — the `user` ceremony profile is now DERIVED, not hand-maintained (PLAN-169, ADR-197)

- `templates/settings/settings.user.json` is generated from
  `settings.base.json` by a declared subtraction recorded in its own
  `_derivation` key, applied by `.claude/scripts/gen-settings-user-template.py`,
  with a byte-for-byte `--check` mode wired into `validate.yml` (`303ae55`).
- The prose it replaces had rotted: it claimed the profile removed
  "exactly 10" hooks while a census measured 26 removed basenames, a
  hand-narrowed matcher, a silently dropped second registration and four
  hand-edited annotations. **The `user` profile therefore registers more
  hooks than in v1.3.0** (20 → 29 registrations, 28 basenames); every
  newly included hook that can still block is named in
  `_derivation.blocking_inclusions` together with its escape route.

### Added — compaction continuity and work-boundary persistence (PLAN-179, ADR-195)

Two new hooks, both **advisory, both fail-open, neither blocks a tool
call today**:

- **`check_compact_pinning.py`** (`SessionStart`, matcher `compact`):
  after a context compaction, re-states the pinned governance
  constraints from a CODE constant (`_lib/pinned_constraints.py`) via
  `additionalContext`, so the summarizer cannot evict them. Kill switch:
  `CEO_CONSTRAINT_PINNING=0`.
- **`check_ledger_checkpoint.py`** (`PreToolUse`, matcher `Bash`): on a
  STANDALONE `git commit` (staging done in earlier tool calls; exactly one
  commit in the Bash call) that lands plan-scoped work, reports whether
  that plan's `LEDGER.md` is in the same commit. Scope is derived
  MECHANICALLY from the paths staged at the moment the hook fires, BEFORE
  the command runs: `git add x && git commit`, `git commit -a` after a
  mutation in the same call, and several commits in one call are
  `skipped`, not observed (signed condition 77 of rc.1). No branch in the
  module returns a decision —
  there is no deny arm to disarm. Kill switches:
  `CEO_LEDGER_CHECKPOINT=0`, `CEO_SOTA_DISABLE=1` (`b07be9b`, `bc82651`).
- **`session_memory_delta_observed`** at `SessionEnd` records whether the
  project's memory directory saw activity inside this session's time window
  (stat-only: no memory content is read or logged). The directory is shared
  by every session of the project and a stat carries no author, so a
  concurrent session's write counts too: `written` is window activity, never
  proof that THIS session wrote memory. The window opens at the whole second
  after the recorded session start, so a write inside that first second is
  not counted (signed condition 20 of rc.1).
- **Audit-log SPEC v2.55 → v2.60**, additive as always
  (`SPEC/v1/audit-log.schema.md`); the known-action set is 331 entries.
- **The honest part.** ADR-153's original continuity design shipped in an
  earlier train and delivered NOTHING: the real autocompact fired both
  hooks and produced `snapshot_outcome=scratchpad_unavailable`,
  `plan_id=unknown`, because plan resolution required an event from the
  session's own history — 2 such events in 12,515 log lines. The rebuilt
  version falls back to a SESSION-scoped snapshot when no plan resolves
  (the plan id itself still comes from the audit history) and carries a
  separate ledger INDEX derived from the last commit's paths — a pointer,
  not a copy. Related
  measurement that corrects a number this project published: the context
  floor re-paid after a compaction was measured at **97,292 tokens** at a
  real compaction boundary (independent cold control: 97,097), roughly
  twice the ~45-55k this repository previously claimed, and it is not a
  constant — a 41-sample series spreads 51.7% around its mean.

### Added — the CI template we deliver is now actually EXECUTED in the smoke test (PLAN-183, `6160578`)

- `scripts/tests/smoke-install.sh` activates the delivered
  `validate.yml.template` in a throwaway target and runs its steps in
  order, one `bash -eo pipefail` per step, stopping at the first red. Any
  workflow shape outside the frozen subset is a parse FAILURE, never a
  vacuous green. Runs on Linux with `CI=true` or
  `CEO_SMOKE_EXECUTE_CI=1`; elsewhere it lists the steps with a note.
- **The delivered template changed accordingly:** it is SHA-pinned
  (`actions/checkout`), honors a `CEO_SOTA_DISABLE=1` repository variable
  as a kill switch, raises its own timeout 5 → 15 minutes, installs PyYAML
  in CI when it is absent and FAILS the YAML catalog syntax check if no
  parser can be had (a syntax gate that skips silently is a gate that
  fails open; a slim offline runner therefore goes red, by design), and
  verifies the SHA-256 of the actionlint release asset before running it.
  It ships INERT with a `.template` suffix; activation is still an
  explicit `mv -n` you perform.

### Added — `claude-fable-5-1` in the model allowlist (`ab56e76`)

- `claude-fable-5-1` joins `availableModels` in `.claude/settings.json`
  and in the maintainer/base settings template (the advisory `user`
  profile deliberately carries no `availableModels`). Adopting a new model is
  deliberately never automatic: the VETO floor, the pins and the agent
  definitions stay Owner-signed by design (ADR-149 remains the single
  source for the model catalog).

### Fixed — seven VETO-bearing skills were demoted to name-only (`b7dad83`)

- `kill-switches`, `latency-budgets`, `equity-research`,
  `financial-correctness-and-math`, `financial-display`,
  `prediction-markets` and `trading-execution` were listed under
  `skillOverrides` as `name-only`, which withholds their body from the
  agent — including from the veto paths that are supposed to read them.
  All seven are undemoted in BOTH settings profiles on a FRESH install.
  An existing v1.3.0 installation keeps its own `skillOverrides` on
  upgrade (the upgrader preserves settings outside the enumerated
  additive migrations), so the undemotion reaches upgraded adopters
  only through a baseline-aware migration — a signed condition of rc.1
  (lands before GA). Four skills with no
  veto role (`cpp-testing`, `frontend-slides`, `prisma-patterns`,
  `ui-demo`) were added to the name-only list in their place — in the
  framework checkout's own live settings only; the delivered templates
  (`templates/settings/`) do not carry them, so a fresh install and an
  upgraded adopter see neither the four names nor the undemotion.

### Fixed — the test suite was writing into the live HMAC chain (`2ae16d2`, `7a618c9`, `3d16070`)

- Measured: 2,356 `policy_*` events over 7 days — 19 processes × exactly
  124 — all with an empty `session_id`, 79% of the live segment. The
  emitter was `python3 -m pytest --collect-only`, run before every
  commit: the isolation layer popped the environment carrier at import
  time but redirected the log in a session FIXTURE, and `--collect-only`
  runs the first without the second. Cured in two layers, with a positive
  control and an anti-rot guard. Adopter-relevant only if you run this
  repository's own suite; recorded here because it corrupted the
  integrity signal this project sells.

### Fixed — `git log --since=<N>h` was a silent misparse (`9af6114`)

- Two instruments passed an hour-suffixed window to `git log --since`,
  which git's approxidate parser DISCARDS — collapsing the window
  silently rather than erroring. Both sites cured, twelve regression
  tests added.

### Changed — documentation

- `docs/UPGRADE-PROCEDURE.md` said `--pin` was "durable; subsequent
  `upgrade.sh` calls honor the pinned version". **It is not, and never
  was.** The pin checks the source tree out at the ref, runs the upgrade,
  and restores the original branch on exit; only `--profile` and
  `--stack` are replayed from the install-state. The document is
  corrected to match `VERSIONING.md`, which was right all along.
- New: `docs/CONTEXT-CONTINUITY-GUIDE.md`, `docs/task-classifier-2b.md`,
  an expanded `docs/threat-model.md`, and
  `docs/BUG-REPORT-adopter-harness-config-replay-fixtures.pt-BR.md`. These are
  framework-repo documents; `install.sh` delivers only the two `docs/`
  files named in `scripts/delivery-routes.tsv`.

### Governance

- ADRs 191 → **197** by NUMBER; 198 ADR files on disk (amendments are
  separate files counted by `verify-counts.sh`): ADR-192 gate-scripts
  checksum manifest, ADR-193 break-glass repo kill switches, ADR-194
  delivery-route resolution, ADR-195 work-boundary persistence, ADR-196
  installer write confinement, ADR-197 user-profile derivation.
- Counts moved: hook scripts on disk 57 → **59**; wired in
  `settings.json` 46 → **48** (48 → **50** event registrations); shared
  `_lib` modules 68 → **71**; ADR files 192 → **198**; collected test
  cases ~14,000 → **~15,400**. Unchanged since v1.3.0: **166 skills**
  (42 core + 8 frontend + 116 domain), **27 slash commands**, **32
  `SPEC/v1` files** (28 `*.schema.md`), **4 TLA+ specifications**.
- Commit count since v1.3.0: `git rev-list --count v1.3.0..<tag>` at the
  tagged commit (a number written here ages with every candidate).
  Canonical changes landed as Owner-GPG-signed ceremonies with per-phase
  sentinels and closed scopes.

### Known issues

Carried into 1.4.0 deliberately, each with its state named:

- **The `PROTOCOL.md` pointer delivered to an adopter is absolute**, not
  relative — it embeds the maintainer's framework path. Found in field
  testing at S315, still OPEN; the cure is PLAN-183 W1 and did not make
  this release.
- **The CI hook-latency gate is sensitive to a slow runner.** The probe
  measures spawn cost and cannot see runner contention: the same hooks at
  the same SHA measured 77 ms locally and 209-435 ms in CI, failing three
  afternoon runs and passing at night. A RELATIVE gate
  (`hook_p50 ≤ K × ref_p50`) is landed in phase 1 ADVISORY only
  (`4bd7def`); making it the enforcing gate is decided but not shipped.
- **The pair-rail is inert until you install Codex separately**, and it
  is a same-class reviewer — unchanged from v1.3.0, restated because it
  is the most misread property of this framework.
- **The ownership e2e ends 62 green / 3 red by design**
  (`OWN-0016`/`0024`/`0027`, causes in ADR-190). An all-green run means
  the decision table changed — stop and find out why.
- **Fence-shadow variant 5 in the release verdict gate** stays outside
  the threat model (the signer is the Owner); the fixed-format envelope
  that closes it is named for a future release.
- **The formal model is still not in CI.** The TLA+ specifications under
  `docs/formal-verification/` are specifications, not a verified claim.
- **`upgrade.sh` under `--pin <ref>` where `<ref>` predates `aaf32c7`**
  finds no route table in the pinned tree; the running upgrader now
  copies the table's bytes out of its own checkout first, so the pinned
  upgrade still delivers.

## [1.3.0] - 2026-08-04

Night-mode + doctrine + release-engineering train (PLAN-162/165
ceremony 2; PLAN-166/167/168 release-hold closure and install/upgrade
ownership; PLAN-177 GA re-pass cures; PLAN-178 spawn acceptance
contract v2, native cost cross-check and vacuity lint). The headline
feature is night-mode; one cross-rail security P0
closed, one published-contract conflict settled by ADR instead of by
silence, and the install/upgrade ownership decision collapsed into a
single audited function. As always: governance and auditability — no
speed claim.

### Added — night-mode: Owner-invoked autonomy posture toggle (PLAN-165, ADR-185)

- **`/night-mode` command + `.claude/scripts/night-mode.py`**: the Owner
  flips the per-machine autonomy posture (`permissions.defaultMode`
  overlay in the gitignored `.claude/settings.local.json`) with
  next-session semantics — "arm before sleep, autonomous overnight
  session, disarm in the morning". The tracked `settings.json` posture is
  never touched; templates and adopter defaults are unchanged.
- **Arming autonomy is a HUMAN action** (Owner-ratified OQ1-redo): the
  toggle refuses under CI; the writer script carries a self-path guard
  and the Bash rail carries a best-effort invocation matcher (defense in
  depth — the real boundary is the script's own guard plus the session
  deny surface, and the docs say exactly that, not more).
- **Audited**: every `on`/`off`/refusal emits `night_mode_toggled` into
  the HMAC chain (schema row in `SPEC/v1/audit-log.schema.md`); live-fire
  proven — toggle events and a negative-control `refused` line verified
  on-chain before this release.
- `bypassPermissions` was deliberately CUT from the design: it would trip
  the `settings_tamper_tripwires` boot check by construction. The honest
  escape valve stays `claude --permission-mode bypassPermissions` (one
  session, explicit, ephemeral).

### Security — sentinel unlock now requires provenance inside git worktrees (ADR-119 Invariant 5)

- **Adopter-visible tightening of the recovery contract** (SPEC/v1
  `sentinel-format.schema.md` §unlock): inside a git work tree, the
  `CEO_SENTINEL_UNLOCK` + `CEO_SENTINEL_UNLOCK_ACK` pair alone no longer
  grants — you must also provide provenance via
  `CEO_SESSION_ANCHOR_SHA=$(git rev-parse HEAD)` (captured BEFORE the
  session) **or** `CEO_SENTINEL_UNLOCK_SHA256=<sha256 of approved.md>`.
  The block message teaches both forms when a window is armed. This
  closes a real escalation: during an unlock window the agent could
  author its own `approved.md` (a path guarded by neither rail) and
  self-grant. Classified MINOR under this repo's published policy
  (`VERSIONING.md` §MINOR: "a new trust boundary adopters must
  understand"); MAJOR is reserved for schema-consumer breakage
  (removed/renamed fields, dropped event types), which this is not.
  **Action needed only if you scripted the 2-var unlock inside a git
  worktree** — add one of the two exports above.

### Fixed — case-fold bypass on canonical AND kernel rails (PLAN-162 W2, P0)

- On case-insensitive filesystems (APFS default), `fnmatch.fnmatchcase`
  let `.claude/settings.JSON` / `.claude/hooks/_lib/audit_emit.PY` slip
  past BOTH guard rails while the write lands on the real file. Both
  rails now case-fold before matching. Found first-hand during the
  PLAN-162 debate; verified by red-first tests on both rails.

### Changed — hook-deadline doctrine settled by ADR-186 (fail-CLOSED)

- The canonical-edit matcher now enforces a **per-invocation wall
  deadline that fails CLOSED** (`_HOOK_WALL_BUDGET_S`, injectable clock),
  replacing the unbounded sentinel sweep — and the published
  fail-open-on-infrastructure contract in `CLAUDE.md` §4 / `AGENTS.md` §1
  now names this exception explicitly: a timeout *inside the matcher* is
  an incomplete verification, not infrastructure. Recovery route:
  provenance-pinned unlock (`CEO_SENTINEL_UNLOCK` +
  `CEO_SESSION_ANCHOR_SHA` or `CEO_SENTINEL_UNLOCK_SHA256`).
- Sentinel-verification **cache partitioned** (signature validity no
  longer keyed per-target). This closes the measured saturation window —
  4.16 s consumed of a 5 s budget at 20 candidate paths — that made the
  old fail-open deadline attacker-reachable by planting sentinels
  (ADR-164-AMEND-1). A correctness/security fix; no throughput claim.
- Deadline blocks are **countable in the chain**: the veto breadcrumb
  carries `reason_code=canonical_edit_hook_fault` instead of
  masquerading as a missing-sentinel block.

### Changed — pair-rail recalibrated 120/150 → 180/210 (ADR-110-AMEND-2)

- Internal cap 180 s under a 210 s registration, ratified only after a
  live substrate probe proved the harness honors a 210 s hook
  registration (evidence committed:
  `.claude/plans/PLAN-162/probe-210s-GO-EVIDENCE.md`).
- `pair_rail_case` events now carry `timeout_ms` (int — a float in an
  HMAC-covered field silently drops the whole event), and the §3
  escalation trigger is the **censoring rate**, not p95 (the p95 of a
  censored sample is inestimable).

### Fixed — scheduled workflows that were red without surfacing in push CI

- **mutation-gate**: kill-rate now parsed from mutmut's junitxml (the old
  regex parser NEVER reported a rate — historical "96.7%" came from an
  inflated formula), artifact redaction inlined and fail-closed, and the
  `actions/checkout` SHA re-pinned (which also cures the
  supply-chain-watch drift red present since 2026-07-20).
- **tournament**: stderr banner no longer merged into the cost-projection
  JSON (`2>&1` unmerge).
- **reality-ledger**: required labels created idempotently
  (`gh label create --force`) so fresh installs cannot red on a missing
  label.
- **ceo-boot**: 24th Tier-S check `scheduled_workflows_red` closes the
  "scheduled gate red for weeks, invisible" class — with cure-detection
  (a red scheduled lane whose newest completed run across ALL trigger
  events is green reports `cured_pending_cron`, not red).

### Changed — install/upgrade semantics (PLAN-166/167/168)

Adopter-visible behavior of `scripts/install.sh` / `scripts/upgrade.sh`
changed in this release — what a v1.2.0 adopter notices when upgrading:

- **Ownership is ONE decision, not a cascade (ADR-190).** On upgrade,
  whether the framework owns `PROTOCOL.md`, `SPEC/v1` or
  `.claude/.framework-version` is answered by a single pure decision
  function (`_ownership_verdict()` in
  `scripts/_framework_manifest_set.sh`) over the observed ownership
  dimensions — execution-state faults (e.g. a failed backup) stay
  caller-side by design; `upgrade.sh` observes → calls → executes
  instead of deciding locally. Fresh installs sit BEFORE the decision:
  they record the registered delivery (the ADR-155 baseline manifest)
  that upgrade's observations later read. Contract:
  `docs/ownership-decision-table.md`.
- **`SPEC/v1` is a forced route on upgrade.** A framework-owned
  `SPEC/v1` is backed up to `.claude.bak/<timestamp>/SPEC/v1` and
  replaced wholesale — a local edit is a fork of the published
  compliance contract, not a customization. A pre-existing `SPEC/v1`
  with no delivery record is byte-compared against the pristine SPECs
  shipped at v1.2.0 and earlier: a match refreshes it, anything else is
  preserved in place with a named WARNING (ADR-155-AMEND-1). Skipped on
  `--ceremony user` installs.
- **`.claude/.framework-version` is the version marker.** Written on
  install and refreshed on framework-owned, unskipped upgrades;
  `check-framework-updates.sh` and forensic triage read it MARKER-FIRST
  — a well-formed marker validated against its delivery record is the
  signal; an absent, unrecorded, malformed or integrity-failed marker
  falls back to root `VERSION`. The adopter repo's root `VERSION` file
  is deliberately never touched by upgrade — after a framework-owned
  upgrade, the validated marker (not root `VERSION`) is what carries
  the installed framework version.
- **`PROTOCOL.md` pointer has ONE generator.** Install and upgrade
  render the pointer through the same shared generator (byte-identical
  output on both paths); a degraded pointer body is cured with a backup
  and adopter edits are preserved. Skipped on `--ceremony user`
  installs, which never create root files.

### Fixed — release-verdict readers share ONE fail-closed grammar (PLAN-177)

The GA re-pass over rc.3 ended NO-GO; the cures landed inside this
train (rc.4) instead of being deferred:

- **Both release decision gates** — the server-side
  `validate-pair-rail-verdict.py` (step 15) and the local
  `_release_tag_guard.py` (all-modes enforcement) — now parse the
  signed verdict with the same strict ASCII/YAML grammar: indented
  continuations of a scalar, comments glued to the value, Unicode
  whitespace stuck to the token (`GO<U+00A0>` is NOT `GO`) and
  separator-less keys (`verdict:GO`) are each a NAMED rejection, never
  a silent normalization into the authorizing token. Proven by
  cross-reader probe fixtures that run the two rails on every key
  shape and require identical answers.
- **Gitignore delivery is symlink-safe**: the three writers refuse to
  follow a symlinked `.gitignore`/`.claude/.gitignore`, dry-run
  previews print what WOULD be appended (never "asserted clean" over
  debris), and the root-gitignore symlink guard is part of the
  baseline enumeration.
- **plans/ schema docs refresh is hash-gated on upgrade**: only a
  byte-pristine copy of a KNOWN prior framework generation of
  `PLAN-SCHEMA.md`/`DEBATE-SCHEMA.md` is replaced (with backup);
  an adopter-modified schema is PRESERVED loudly. Closes the F3 STALE
  signature the parity e2e flagged. The refresh writes over the
  existing inode (`cp`, not an atomic rename), so a hard link to that
  file outside the target changes with it — signed condition of rc.1:
  no hard links or symlinks anywhere under `.claude/`, `docs/`, `.github/`
  and `SPEC/` before upgrading (two `find` commands in
  `docs/UPGRADE-PROCEDURE.md`; the hook, script, command, skill and
  agent deliveries copy through a link the same way). A `--ceremony
  user` repository upgrades with `--no-settings-migrate` (signed
  condition of rc.1: the leaf migration adds three maintainer-profile
  keys to the advisory profile otherwise).
- **Pre-state ceremony migration fails safe to `user`** and only an
  EXPLICIT `--ceremony` flag / env / recorded state persists into the
  synthesized install-state — the fail-safe inference itself is never
  persisted.
- **npm honesty**: `npm/INTEGRITY.md` names the packlist exceptions
  that actually ship; `SBOM.md`, `install-npm.sh` and `INSTALL.md`
  claims re-verified against behavior.

### Added — spawn acceptance contract v2 (PLAN-178 Lote B, ADR-191)

- **FILE ASSIGNMENT grammar with taint semantics** in
  `check_agent_spawn.py`: every named spawn declares `- CAN edit:
  <concrete paths>` or `- CAN edit: NONE-READ-ONLY`; globs, Unicode
  whitespace, control characters or non-whitelisted list lines taint
  the whole declaration. Advisory-first: omission is VISIBLE
  (`spawn_file_assignment_recorded`, `path_count=0`) and the enforce
  flip stays a future ceremony gated on the measure-first window.
- **Fenced + capped inter-agent ingest** in the four shipped Workflow
  skills (byte-identical COMMON block): PROMPT DEFENSE ≥6, explicit
  FILE ASSIGNMENT, anti-spoof fencing with a 24000-char cap whose
  truncation poisons the owning dimension — plus a pre-dispatch
  validator of the reduced ADR-191 grammar in the workflow scripts
  themselves (the Workflow rail does not pass through the spawn hook;
  honest limitation recorded in ADR-191 §4).
- **Shared-memory `query()` returns are fenced**
  (`_lib/memory_shared.py`, ADR-089-AMEND-1) with a derivable
  SEC-P0-02 reopen trigger.
- **Multi-plan budget cap cure** (`check_budget.py`): the previously
  INERT cap (early-allow with ≥2 active plans) now resolves the
  active plan by an explicit tie-break and emits a breadcrumb instead
  of silently allowing.
- **Native cost cross-check in `/agent-budget`** (PLAN-178 W1.2):
  a read-only, fail-soft, zero-network puller reads Claude Code's own
  per-subagent usage records and `budget-summary.py` joins them
  against the audit-log estimate (exact match on session + description
  hash, ordinal fallback; unmatched residue VISIBLE on both sides;
  cache-billable split priced correctly). Opt-in via `--native` /
  `CEO_BUDGET_NATIVE=1` — the default output stays byte-identical —
  with a `CEO_NATIVE_COST_DISABLE` kill-switch. Doctrine recorded in
  the command doc: a cross-check, never an authority swap.
- **Vacuous-check lint + a live cure** (PLAN-178 Lote A):
  `check-vacuous-checks.py` fails any boot check whose reachable local
  returns can never go red (structured head-only waiver:
  `# CEO-INFORMATIONAL-ONLY: <reason>`), with positive controls on the
  lint itself. The known-vacuous `check_tier_a_spec_version_drift` is
  CURED for real: framework-vs-SPEC major comparison with a reachable
  red, ownership-aware source and ADR-155-AMEND-1 §5 provenance
  (no provenance ⇒ yellow "suspected", never red).

### Governance

- ADRs 184 → **191** by NUMBER; 192 ADR files on disk — amendments
  (e.g. ADR-089-AMEND-1) are separate files counted by
  verify-counts.sh (ADR-185 night-mode; ADR-186 hook-deadline policy;
  ADR-110-AMEND-2; ADR-164-AMEND-1; ADR-155-AMEND-1 delivery-record
  ownership; ADR-190 ownership-decision-table contract; ADR-191 spawn
  acceptance contract v2; ADR-089-AMEND-1 shared-memory fence). Slash
  commands 26 → **27**
  (`/night-mode`). All ceremony phases landed as separable
  Owner-GPG-signed commits with per-phase sentinels and closed scopes —
  PLAN-178 Lote B under its own sentinel (SENT-PLAN178-LOTEB) and a
  44-round cross-model rail.

## [1.2.0] - 2026-07-30

Substrate + rail release (PLAN-160/161/163/164). The headline is not a new
feature: it is that the cross-model pair-rail **completed a live in-hook
review for the first time in the audit log's history**. Everything else is
the substrate work that made that possible. As always: governance and
auditability — no speed claim.

### Fixed — the pair-rail was 100% fail-open (PLAN-164, ADR-110-AMEND-1)

- **`CEO_PAIR_RAIL_TIMEOUT_S` internal default 30 → 120 s**, and the
  `check_pair_rail.py` PreToolUse **registration timeout 60 → 150 s** in both
  kernel `.claude/settings.json` and `templates/settings/settings.base.json`
  (parity enforced). The 30 s value was an implementation literal, never a
  decided one, and it sat structurally *below* the latency of a real Codex
  verdict: **every one of the 12 `pair_rail_case` events in the entire life of
  the audit log was case F / TIMEOUT.** The rail had never once completed a
  live review. Measured calibration (N=9, same machine): p95 ≈ 75 s, which
  crosses the measurement protocol's own 70 s escalation threshold and selects
  120/150 rather than the 100/120 first draft.
- **The layering invariant is now tested, not assumed**
  (`test_pair_rail_timeout_invariant.py`): kernel registration == template
  registration, and `registration >= internal + 30`. A unilateral flip of any
  of the three literals now goes red in the suite and in the pack preflight.
- **`statusMessage` on the registration** — a session held by a synchronous
  cross-model review shows "may take up to ~3 min" instead of appearing
  frozen. (Shipped in 1.2.0 as "may take 1-2 min"; the wording tracks the
  budget and was retuned by ADR-110-AMEND-2 when it moved to 180/210 s.)
- **From zero completed reviews to ten.** The log now holds 10 healthy cases
  (7 × case A, 3 × case B) alongside 14 case F. Median verdict latency 70.5 s;
  observed maximum 120.0 s.
- **The §3 recalibration trigger (≥10 healthy cases) is met, and it points
  upward — with the caveat it deserves.** No sample actually exceeded 120 s;
  the p95 figure of 122.2 s is an *interpolation above the observed maximum*
  on exactly ten points, not a measured latency. What is solid: the three
  slowest healthy reviews (115 / 115 / 120 s) leave 0–5 s of headroom, and the
  trigger's own query is **right-censored by construction** — any review slower
  than the budget becomes a case F and never enters the healthy set, so this
  p95 can only ever under-report the true distribution. An upward
  `ADR-110-AMEND-2` is therefore indicated, but the new pair is deliberately
  **not** chosen here: §3 requires a new amendment via ceremony, and the number
  belongs to the C5 measurement protocol plus a debate, not to a changelog
  line.

### Changed — substrate uplift to Claude Code 2.1.220 + Claude 5 (PLAN-163, ADR-181)

- Model registry refreshed to the **Claude 5 family**. Adopter installs are
  migrated in place by the landed `scripts/upgrade.sh` — including the
  pair-rail **registration-timeout cap 60 → 150 s** (the settings half of
  ADR-110-AMEND-1; applied only when the adopter's value is still the old
  default, so an operator-chosen value is never clobbered).
- **Dated pricing is now event-date-aware** rather than resolved against wall
  clock, so a historical audit event prices at the rate in force when it
  happened.
- `opus-4-8-fast` recognized; stale-model scan updated.

### Added — Codex payload pin enforcement (PLAN-163, ADR-182)

- **Verify-then-invoke.** The previous SHA pin attested the *launcher*, not the
  payload it executed — a pin that proved the wrong artifact. The pin now
  verifies the payload before invocation and fails closed.

### Changed — canonical-edit gate hardening (PLAN-160/161, ADR-164, ADR-165)

- Multi-candidate sentinel resolution is **fail-closed**, with a shared
  predicate and dual-anchor validation; `resolve_anchor` is suffix-newest and
  revert-aware. Three redundant `Write()` deny twins removed.

### Added — upgrade + liveness instrumentation (PLAN-161)

- Red-first **upgrade oracles** (dry-run identity, exclusion predicate, opt-in
  purge) wired into the `smoke-install` CI job — an adopter upgrade that
  silently changes behavior now fails a gate instead of shipping.
- **Pair-rail liveness telemetry**: two typed audit actions, so "the rail is
  fail-open" is a queryable fact rather than an inference.
- Perf-gate backoff with a probe-gated third attempt (runner-load flake).
- `ADR-183` — directory-added notification events.

### Fixed — `disableAutoMode` silently disabled every hook

- The value was a boolean; Claude Code 2.1.220's settings schema rejects it and
  **skips the entire `settings.json`** — a session would boot with none of the
  48 hook registrations, governance fully absent, and no error surfaced. Now
  the string `"disable"`. Found by live-fire on the first boot after the
  substrate pack, not by any fixture.

### Counts (reproducible via `verify-counts.sh`)

166 skills (42 core / 8 frontend / 116 domain) · 26 slash commands · **184
ADRs** (178 → 184) · 57 hook scripts on disk, 46 wired into `settings.json`
across 48 event registrations · 68 `_lib` modules.

---

## [1.1.0] - 2026-07-13

Feature release (PLAN-153/154/155/156): two new host harnesses (Codex CLI
and Grok Build run the same enforcement hooks), a cross-vendor audit
council, a gated learning loop, and a skill-catalog uplift 151 → 166. As
always: governance and auditability — no speed claim.

### Added — multi-harness (PLAN-155, PLAN-156)
- **`--harness codex`** (PLAN-155, ADR-161): the installer emits a Codex
  bundle (`.codex/hooks.json`, `.codex/rules/ceo.rules`, operator
  `AGENTS.md`) that runs the **same** hooks under `CEO_HOOK_ADAPTER=codex`.
  Per-rail truth (verified against codex-cli 0.139.0): canonical-edit,
  bash-safety, plan-lifecycle, kernel-deny, config, and kill-switch are
  ENFORCED at edit time; audit chain ENFORCED but completeness-bounded;
  pair-rail inverted (Codex operates, `claude -p` reviews) and PARTIAL;
  spawn governance ADVISORY. Installer ends with an
  `ARMED / NOT-ARMED-(untrusted) / BROKEN` arming check.
- **`--harness grok`** (PLAN-156, ADR-162): single-surface install — Grok
  Build reads the shipped `.claude/settings.json` directly (no second
  bundle; arming both surfaces would double-fire every hook). Prevention
  rails ENFORCED via grok's `pre_tool_use`; pair-rail is Stop-passive, so
  a **git pre-push review gate is the teeth**. Verified against grok
  0.2.93 (exact pin). Emits `AGENTS.md` + `.grok/*.example` config.
- New docs: [`docs/adapters.md`](docs/adapters.md) +
  [`docs/provider_capability_matrix.md`](docs/provider_capability_matrix.md)
  (per-rail, per-harness enforcement matrix — what is actually enforced
  vs advisory under each harness).
- Audit-chain action registry extended for both harnesses (314 → 319
  registered actions, tamper-mirror coverage included).
- codex-cli version pin bumped to `<0.145.0` (GPT-5.6 line) in
  `codex-cli-pin.txt`; release gate hard-blocks verdicts from unpinned
  codex binaries.

### Added — cross-vendor audit council (PLAN-156)
- **`/council <scope>`** — read-only, three-vendor audit (Claude in-harness
  agents + Codex `exec --sandbox read-only` + Grok `-p --sandbox council`)
  with vendor-attributed verdicts, adversarial re-verification, and
  explicit fail-loud quorum degradation (an unavailable lane reports
  STATUS: unavailable, never a silent substitution). Every external-lane
  prompt passes the ADR-114 egress redactor; ADVISORY evidence only;
  operator/local only — never CI.

### Added — gated learning loop (PLAN-154)
- Hooks accrue **lesson candidates** from live sessions; nothing renders
  or persists as advice until explicitly approved: **`/lesson-review`**
  (approve / reject / undo, HMAC-recorded), **`/lesson-evolve`** (cluster
  approved lessons into SP-NNN skill-patch drafts for the existing
  /skill-review ceremony), and an opt-in boot surface
  (`CEO_LEARNING_BOOT_LESSONS=1`) that renders ≤3 verified one-liners as
  fenced untrusted data — verify-before-render against the HMAC chain,
  fail-closed drops, count-only integrity notes. Default OFF
  (`CEO_SOTA_DISABLE=1` master kill precedence).

### Added — skill catalog + commands (PLAN-153)
- Skill catalog **151 → 166**: 15 imported domain skills land through a
  new import gate with a NOTICE provenance ledger; 20+ SP-NNN adaptation
  patches promoted shadow → live through the new **`/skill-review`**
  ceremony (staged shadow-soak, Owner-waivable).
- New commands: **`/skill-health`** (per-skill telemetry from the HMAC
  audit log — invocations, failure-proxy clusters, dead-skill flagging)
  and **`/context-budget`** (static context-overhead audit of the skill
  catalog + governance surface).
- `COMMAND→SKILL→HOOK` map (`docs/COMMAND-SKILL-HOOK-MAP.md`) with a
  validate.yml drift gate — regenerate via
  `.claude/scripts/gen-command-skill-hook-map.py --write`.

### Added — security gates (PLAN-153 Wave E)
- Harness-config gate (tamper tripwires over `settings.json` hook
  registrations), citation gate, spawn prompt-defense template, deny
  baseline, and supply-chain watch — all wired into `/ceo-boot` +
  validate.yml.

### Added — installer / release lifecycle (PLAN-153 Wave B)
- `doctor.sh` + repair mode, install-state manifest + replay,
  install-profiles manifest, deterministic plugin-manifest regeneration
  (`build-plugin.py --check` CI drift gate), release idempotency +
  release-notes template. Fixes the two latent v1.0.x release.yml bugs
  (RC-version-mismatch; hardcoded release notes).

### Changed
- `/ceo-boot` extended with liveness checks (fail-open rail silence is
  now surfaced, not mistaken for health) and the harness-config gate.
- README / plugin description / manifests: counts reconciled to disk
  truth (166 skills, 55 hook scripts, 68 `_lib` modules, 26 commands,
  178 ADRs).

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
- **`CEO_UNICODE_HARDBLOCK=1` Read scan streams the whole file** — the
  economics-02 capped re-read silently fail-opened the opt-in fail-closed
  guard for invisible-unicode payloads past 1 MiB. Found by the Codex
  release re-pass (RC window, R1 REJECT); the armed path now scans in
  cap-sized chunks (per-code-point detection — chunking exact); flag-off
  hot path unchanged (PLAN-152 round-2).

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
