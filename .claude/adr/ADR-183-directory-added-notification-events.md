# ADR-183 — DirectoryAdded + Notification hook events: notification-only wiring (observer-WRITER + write-guard consumer)

- **Status:** Accepted (2026-07-28; effective when the PLAN-163 W3 staged pack
  lands at the GPG ceremony)
- **Date:** 2026-07-28
- **Plan:** PLAN-163 (T3.1–T3.5; gap-matrix G7; stop-review S283 findings 2+3;
  FX3 fix-pass consumer hardening H5/M1/M2)
- **Blast radius:** L3+ canonical — `.claude/settings.json` (2 new event
  registrations), `.claude/hooks/check_directory_added.py` +
  `.claude/hooks/check_notification.py` (NEW hook files, 55→57 on disk),
  extension of the existing PreToolUse Edit|Write|MultiEdit write-guard
  stack (consumer), `scripts/upgrade.sh` T5.4 migration table + T3.4 gate,
  `templates/settings/settings.base.json` (deliberate NON-change — residual e)
- **Debate:** PLAN-163 round-1 — 3 critics, 3×ADJUST → PROCEED
  (adjustment 6: probe-first, hardblock-floor, write-guard fallback,
  no-value-echo; adjustment 13: SlashCommand note in this ADR)
- **Cross-vendor review:** codex r1–r5 + grok r1–r4 (findings CF-9, codex
  F7/F10, grok F5/F6/F9/F12 applied); S283 stop-review findings incorporated
  pre-execution (plan Addendum)
- **Probe (normative evidence):**
  `.claude/plans/PLAN-163/probes/diradd-blockability.md` (CC 2.1.220,
  2026-07-28, 5 live child sessions + static binary extraction)
- **Relates to:** ADR-056 (lifecycle-hook family this extends), ADR-146
  (fail-closed-on-input precedent), ADR-153 (W2 event-adoption precedent),
  ADR-155 (upgrade merge policy the T5.4 migration composes with)

## Context

Claude Code 2.1.220 exposes two hook events the framework did not consume:

- **`DirectoryAdded`** — fires after `/add-dir` or the `register_repo_root`
  SDK control request registers a new working directory. Input shape (probe,
  live-captured): `{session_id, transcript_path, cwd, prompt_id,
  hook_event_name:"DirectoryAdded", directory:<abs>,
  source:"slash_command"|"register_repo_root"}`.
- **`Notification`** — lifecycle notifications (`agent_needs_input`,
  `agent_completed`, …). Input shape: `{message, title?, notification_type}`
  (+ base fields); the registration matcher matches `notification_type`; the
  ONLY output arm the harness consumes is `additionalContext`.

The security concern (debate R-SEC2, HIGH): `/add-dir` expands the write
perimeter mid-session. Canonical guards are project-relative
(`CLAUDE_PROJECT_DIR`); a directory added OUTSIDE the project (e.g. `$HOME`)
exposes **`~/.claude/`** — user-scope `settings.json` (permissions, extra
hooks, env), profile and credential surfaces — to Edit/Write with **no
canonical-guard stack and OUTSIDE the HMAC-audited perimeter**. That is the
protected asset this ADR exists for: a write there persists across sessions
and is invisible to the tamper-evident chain.

**SlashCommand note (debate adjustment 13):** the threat model of `/add-dir`
is NOT "human-only". With the SlashCommand tool surface, an *agent* can
invoke `/add-dir` — injected content convincing the agent to add `$HOME` is
the realistic chain, so the control cannot assume a human in the loop at
add-time.

### The blockability probe (HARD GATE CF-9) — verdict: notification-only

T3.1 made any enforcement promise conditional on a live probe. The recorded
verdict (`diradd-blockability.md`) is one line:
`diradd=notification-only; post-facto-window=reads+writes`. Specifically:

1. **`decision:block` is structurally IGNORED** for DirectoryAdded. The
   executor (`a$t` in the 2.1.220 binary) harvests ONLY `systemMessage` from
   hook results — no `decision`, no `blockingError` is ever read. The event
   is absent from the blocking-capable set (`NFy` = PreToolUse, PostToolUse,
   PostToolUseFailure, PermissionRequest, PermissionDenied); it lives only in
   the fire-registry. Live-fire confirmed: a hook returning
   `{"decision":"block"}` exit 0 changed nothing — the directory stayed
   registered and the session continued.
2. **The event is PÓS-FACTO.** Permission/sandbox state is refreshed to
   include the directory BEFORE the hook is dispatched (fire-and-forget
   `.then()` after a synchronous permission-context mutation). By the time
   any hook runs, the added root is already fully live.
3. **The post-facto window is reads+writes, full.** Live Run B read exact
   sentinel bytes AND wrote a file under the added root. There is no
   read-only added-directory state, and nothing a DirectoryAdded hook emits
   can retroactively deny tool calls already authorized.
4. **Notification is likewise non-blocking** (executor discards results;
   output schema has no deny arm) — wireable for telemetry only.

So the plan's SE-notification-only branch is the PROVEN branch: any "block"
wiring on DirectoryAdded would be a false sense of security, and the ADR
records the post-facto semantics as a hard limit of the control — the
floor/deny below must never be sold as total exposure prevention.

## Decision

Wire BOTH events in the dogfood install, in the notification-only
architecture: **observer-WRITER + write-guard CONSUMER**.

### 1. `DirectoryAdded` → `check_directory_added.py` (observer-WRITER)

- Records every session-added workspace root into the session-roots registry
  `.claude/state/session-roots.json` — schema versioned, scoped by
  `session_id`, TTL = session; `.claude/state/` is non-commit/gitignored
  (declared policy). The write is source-attributed
  (`slash_command` vs `register_repo_root`).
- The hook itself never blocks (the harness could not honor it anyway —
  probe fact 1). Fail-OPEN on infrastructure per CLAUDE.md §4. Where a
  future harness DOES support a block decision, the entry's narrowed
  hardblock floor (grok F12: `$HOME` root, `~/.claude/`, any foreign
  `**/.claude/**` tree; project-dir ancestors REMOVED from the floor)
  becomes meaningful without a re-wire.
- Registration (canonical entry, byte-normative in the `upgrade.sh` T5.4
  table): matcher `""`, timeout 5,
  statusMessage "Recording added workspace root...".
- Kill-switch: `CEO_DIRECTORY_ADDED_GUARD=0`.

### 2. Enforcement lives in the CONSUMER: write-guard extension

- The deny point that CAN fire is PreToolUse on the Edit|Write|MultiEdit
  family (blocking-capable set). The consumer reads the session-roots
  registry and DENIES writes under a registered, non-allowlisted added root.
- It is an **EXTENSION of an existing wired PreToolUse write-guard — never a
  third new hook file** (T6.4 count contract: hooks on disk 55→57 = exactly
  the two files above).
- Matching is by **ABSOLUTE path + `realpath`** — the existing guards are
  project-relative, and the whole point is roots OUTSIDE the project; the
  extension is explicit about that.
- **Fail-CLOSED in the consumer on unparseable/uncanonicalizable paths**
  (security-matcher input rule, CLAUDE.md §4; precedent ADR-146 /
  check_bash_safety). Fail-OPEN remains reserved for infrastructure bugs of
  the hook itself. The fail-CLOSED surface is explicitly broadened by the
  FX3 hardening (stop-review S283 findings M1/M2), each a security-matcher
  input the guard cannot bind to a boundary:
  - **Missing session identity (M1).** An event carrying NO `session_id`
    (absent/empty) WHILE the registry holds registered sessions cannot be
    bound to any session's roots, yet roots exist → boundary unknowable →
    external writes are DENIED. This closes the neutralize-by-clearing-
    `CLAUDE_SESSION_ID` path: a blind allow there would have let an
    unidentified event slip every registered root. Repo-internal writes
    stay governed by the canonical stack (the guard scopes to external
    writes only); an empty registry with no session_id still allows
    (nothing to bound).
  - **Non-absolute root directory (M2).** A registry entry whose
    `directory` is not `os.path.isabs` is classed MALFORMED (same class as
    `unparseable:true`) and DENIES external writes, because a relative
    value would be silently resolved against the process CWD by
    `os.path.realpath` and mis-scope the boundary.
- Without the writer the guard would be born green: the red-first probe is
  the write under a registered root BEFORE the guard exists.

### 3. `Notification` → `check_notification.py` (telemetry observer)

- Typed audit emit for lifecycle notifications (`agent_needs_input` /
  `agent_completed`) with **no-value-echo**: `message`/`title` CONTENT is
  NEVER persisted — only the closed-enum `notification_type` class and
  counts. Feeds liveness telemetry (the pair-rail/stop-review liveness
  watch class).
- ADVISORY, fail-open; never blocks (the harness discards results anyway).
- Registration: matcher `""`, timeout 5,
  statusMessage "Recording notification lifecycle event...".
- Kill-switch: `CEO_NOTIFICATION_TELEMETRY=0`.

### 4. Counts and surfaces (T6.4 contract)

| Surface | Before | After |
|---|---|---|
| Hooks on disk | 55 | **57** (only the 2 new observers) |
| Hooks wired (dogfood) | 44 | **46** |
| Registrations, `.claude/settings.json` (dogfood) | 46 | **48** |
| Registrations, `templates/settings/settings.base.json` | 45 | **45** (deferred — residual e) |

Adopters receive the registrations via the `upgrade.sh` T5.4 baseline
migration, GATED (below). Parity oracles derive expectations from the
artifacts (`upgrade.sh --print-settings-baselines` + the settings files),
never re-hardcoded literals (`test_template_dogfood_parity.py`,
`test_upgrade_settings_migration.py`); the intentional
`check_cost_envelope.py` dogfood-only exclusion is preserved.

## Named residuals (explicit dispositions — none silenced)

- **(a) READS under an added root are UNCOVERED** (CF-9 / S283 finding 2).
  The observer-writer + write-guard consumer covers only Edit|Write|MultiEdit
  under a registered root. Read/Grep/Glob of a foreign `~/.claude/` under an
  added root lands BEFORE any observer can react and is not denied.
  Disposition: a read-guard extension (PreToolUse on Read, keyed off the
  same registry) is a NAMED FOLLOW-UP — not silently absorbed here.
- **(b) Launch-time `--add-dir` fires NO DirectoryAdded event** (probe
  Q-iii: registry blind spot — the log stayed empty on the launch path,
  which is also the only path that can introduce a tree outside cwd).
  Disposition: documented residual; candidate mitigation is a SessionStart
  snapshot of the effective working-root set into the same registry (cheap,
  follow-up), which would make the consumer cover launch-added roots too.
- **(c) Post-facto window**: even with the consumer wired, reads+writes are
  live from the moment of addition until the consumer's first deny — the
  event fires after permission state already includes the root. The control
  is containment-after-the-fact plus audit, NOT prevention of exposure.
- **(d) Monorepo floor residual** (inherited from the plan): project-dir
  ancestors were removed from the hardblock floor (grok F12 narrowing), so
  a monorepo parent added as a root is not floor-listed; Owner allowlist
  option documented in the plan.
- **(e) Template registrations DEFERRED** (CEO decision S284):
  `templates/settings/settings.base.json` stays at 45 registrations. The
  T3.4 feature gate in `upgrade.sh`
  (`_T34_VERSION_FLOOR_PROBE_PASSED=0`, env override
  `CEO_T34_NEW_EVENT_REGISTRATIONS={1|0}`) ships DEFAULT OFF: SUPPORT.md
  declares the adopter floor `>=2.0`, and unknown-event-key tolerance is
  proven on 2.1.202/2.1.220 but the 2.0.x floor was NOT probed. Emission
  into adopter settings/templates waits for the version-floor probe (or an
  explicit floor raise keeping SUPPORT/install/upgrade coherent) — flipped
  in the SAME change that records the probe verdict.
- **(f) REGISTRY-REWRITE BYPASS — the write-guard is best-effort, not a
  hard boundary** (stop-review S283 finding H5; FX3). The session-roots
  registry `.claude/state/session-roots.json` is repo-INTERNAL and
  agent-writable, and by design (residual scope + the repo-internal write
  exemption) writes to it are governed by the canonical stack above, NOT by
  this guard. A determined in-session agent can therefore still fully neutralize the guard only ONE way: (i) overwrite the registry with
  `{"schema":1,"sessions":{}}` — a legitimate EMPTY parse → no active
  session → silent allow; or (ii) corrupt/truncate it. Path (ii) no longer degrades to an allow: per C3 (codex/grok R4) a registry that is PRESENT and readable but does not PARSE now fails CLOSED, denying any write not provably repo-internal; only an ABSENT file or an INFRASTRUCTURE read error (PermissionError, transient IO) stays fail-open. **Scope is confused/non-adversarial deputy, NOT adversarial
  containment.** The guard exists to stop the *accidental*,
  notification-blind write that the post-facto DirectoryAdded window opens
  (residual c) — the write an agent makes without realizing the perimeter
  grew. It does NOT stop an agent that deliberately edits the registry to
  clear the boundary; nothing that lives in an agent-writable, guard-exempt
  file can. **Mitigation combines PREVENTION (fail-closed on a present-but-unparseable registry) with OBSERVABILITY.** The
  present-but-unparseable (corrupt / non-utf-8 / unknown-schema) fail-CLOSED
  path now emits a
  `session_roots_registry_unreadable` audit event (on the already-registered
  `veto_triggered` action — no new action minted) so a corrupt-registry tamper leaves a forensic trace in the HMAC-chained log even on the repo-internal-only branch that still allows (present-but-unparseable fails CLOSED for external writes; an absent file or infra read error stays fail-open, CLAUDE.md section 4). The empty-overwrite path
  (i) is a *valid* registry state, so it is NOT signalled as tamper — it is
  named here as the residual instead. And the read residual (a) is wholly
  untouched by any of this: a registry-rewrite plus a read under the added
  root stays entirely undiscovered by this write-path guard. This control
  is never sold as prevention of a determined adversary.

## Consequences

- The `~/.claude/` user-scope surface gains its first in-framework control:
  source-attributed audit of every mid-session root addition plus a
  blocking write-deny at the only point the harness can actually block.
  Honest boundary: residuals (a)–(f) mean exposure of an added tree is
  reduced and evidenced, not eliminated — and (f) in particular means the
  write-deny is a confused-deputy control, defeatable by a determined agent
  via registry rewrite, with audit-on-tamper as the only backstop.
- Two new kill-switches enter the inventory
  (`CEO_DIRECTORY_ADDED_GUARD`, `CEO_NOTIFICATION_TELEMETRY`) — both
  observer-side; the consumer's kill discipline follows its host guard.
- The T5.4 migration + T3.4 gate keep adopters on a provable path: the
  canonical entries are byte-normative in one table, oracles derive from it,
  and a future gate flip is a one-line, test-coupled change.
- Rollback: remove the two registrations (dogfood) and the two hook files;
  the registry file is session-TTL state with no persistence obligations.
  Each piece is independent; no other key depends on them.
