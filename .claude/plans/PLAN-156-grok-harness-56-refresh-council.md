---
id: PLAN-156
title: Multi-Harness Expansion — Grok Build adapter, GPT-5.6 lane refresh, Cross-Vendor Audit Council
status: done
created: 2026-07-10
reviewed_at: 2026-07-10
executing_at: 2026-07-12
completed_at: 2026-07-12
owner: CEO
depends_on: [PLAN-155]
budget_tokens: 1.2-1.8M
budget_sessions: 4
context_risk: medium
external_wait: grok-cli-install-and-auth (Owner), codex-cli-upgrade (Owner ratifies pin)
tags: [harness-compat, adapters, grok, codex, gpt-5.6, audit-council, cross-vendor]
# spec_ref DELIBERATELY UNSET while draft/reviewed (pair-rail R5 P1): the
# ADR-058 brainstorm lives at PLAN-156/artifacts/spec-draft-S266.md (§Brainstorm
# spec below). spec_ref is set to the guarded .claude/plans/PLAN-156/spec.md
# ONLY at W0b, when that trusted SPEC-CONTEXT-injectable surface is created
# under the sentinel — never point spec_ref at a mutable unguarded artifact.
---

# PLAN-156 — Multi-Harness Expansion: Grok + GPT-5.6 + Conselho

## Context

Owner directive (S266, 2026-07-10): **"quero que o ceo funcione no codex e
no grok além do claude"** + investigar a família GPT-5.6 (Sol/Luna) +
**"crie uma espécie de conselho, pra gente fazer audit com codex e grok"**.

Demand signal + primitives both exist (the PLAN-155 admission bar):

1. **Grok Build** (official xAI CLI, binary `grok`, launched 2026-05-14,
   proprietary, v0.2.94 at drafting, **daily release cadence**) has
   lifecycle hooks with a **blocking PreToolUse**: stdin JSON envelope
   (`hookEventName`, `sessionId`, `cwd`, `workspaceRoot`, `toolName`,
   `toolInput`), decision via stdout `{"decision":"deny","reason":…}`,
   exit codes **0=allow, 2=deny, any other = FAIL-OPEN** (source:
   docs.x.ai/build/features/hooks, S266 research). It reads
   `.claude/settings.json` as legacy compat and auto-maps Claude tool
   names (`Bash`→`run_terminal_cmd`, `Edit`→`search_replace`,
   `Read`→`read_file`). Blocking primitive parity with codex-cli 0.139
   — in places a superset. **NOT to be confused with the third-party
   `superagent-ai/grok-cli`** (unaffiliated wrapper; out of scope).
2. **GPT-5.6 family**: local empirical probe (S266) proved
   `gpt-5.6-sol` and `gpt-5.6-luna` EXIST server-side but our pinned
   codex-cli 0.139.0 CANNOT run them ("requires a newer version of
   Codex"); `gpt-5.6` base is API-only ("not supported when using Codex
   with a ChatGPT account"). Restoring frontier-model access on the
   codex lane REQUIRES a CLI bump past our pin `<0.140.0` — which by
   contract (ADR-111 §pin-update-protocol) is a ceremony, not an edit.
3. **Cross-vendor audit council**: the S266 fable-advisor analysis
   (MIT, DannyMac180/fable-advisor) articulated the doctrine this wave
   adopts: models from one family share blind spots; lanes must fail
   LOUD (`STATUS: unavailable`), never silently substitute another
   vendor. Credited via `inspired_by` where skill text is adapted.

## Brainstorm spec (ADR-058)

The pre-plan brainstorm artifact is checked in at
`.claude/plans/PLAN-156/artifacts/spec-draft-S266.md` (problem statement,
evidence base, options-considered with rejections, constraints, success
shape). It is NOT yet the `spec_ref` target: the canonical
`.claude/plans/PLAN-156/spec.md` is an ADR-010-guarded, SPEC-CONTEXT-
injectable trusted surface, so it is created (and `spec_ref` set) only at
W0b under the sentinel — pointing `spec_ref` at the mutable unguarded
artifact would expose a trusted prompt surface to unsentineled edits
(pair-rail R5 P1). The artifact is the brainstorm of record until then.

## Level: L3

Touches the arbitration kernel (`KNOWN_ADAPTERS`, contract.py:216),
canonical hooks, installer, validate.yml, and creates a new external-LLM
invocation surface (council). Debate before execution; sentinel per
guarded wave; kernel overrides per ADR-116/ADR-031.

## Thesis

PLAN-155 built the adapter seam precisely so a third harness is a
bounded, provable increment: one adapter module + templates + installer
emission + capability matrix row, all certified by behavioral positive
controls — never by config existence. Grok's hook surface is
Claude-shaped enough that the marginal cost is low; the risks are
concentrated in three Grok-specific semantics (block→deny normalization,
exit-2 fail-closed discipline, advisory Stop) and in the 0.x daily-release
volatility (pin + substrate watch mandatory). The 5.6 refresh is the
same discipline pointed at the existing codex lane: the pin ceremony IS
the compatibility mechanism. The council converts our third-vendor
access into an audit instrument with vendor-attributed verdicts.

## Waves

### Wave 0 — Prep + empirical characterization (SPLIT: 0a unguarded / 0b guarded SENT-GK-0)

**W0a (unguarded)**: the Owner CLI installs, the grok wire-fixture
recording, the research-lacunae resolution, the `substrate-watch.json`
additions (substrate-watch is data, not a kernel path), and **DRAFTS
staged under `PLAN-156/artifacts/`** — the sentinel drafts AND the
ADR-162 draft (`.claude/adr/` is a canonical guarded surface, so the ADR
draft lives in artifacts and is PROMOTED to `.claude/adr/ADR-162-*.md`
under a sentinel in a guarded wave, never created directly in W0a).
**W0b (guarded, SENT-GK-0)**: creating
`.claude/governance/grok-cli-pin.txt` + binary-SHA file, enrolling both
in `_KERNEL_PATHS` (`check_arbitration_kernel.py`), AND promoting the
ADR-162 + spec.md drafts to their canonical homes — all canonical/kernel
edits landing under the sentinel with
`CEO_KERNEL_OVERRIDE=PLAN-156-GROK-PIN-ENROLL`, never as an unguarded
edit. The pin files are created and enrolled in the SAME guarded step so
the Wave-4 registry edit meets an already-guarded pin, not a surprise.

- **[OWNER ACTION]** Install Grok Build **fetch-hash-THEN-execute**
  (pair-rail R9 — NOT `curl … | bash`): `curl -fsSL
  https://x.ai/cli/install.sh -o /tmp/grok-install.sh`, display + record
  the SHA-256, inspect, and only then `bash /tmp/grok-install.sh`. For a
  proprietary rolling 0.x installer, piping straight to bash executes a
  possibly-compromised script BEFORE any hash evidence exists — recording
  the SHA after the fact is forensics, not prevention, and contradicts
  the plan's own fetch-hash-then-execute mitigation. Then `grok login`.
  Prerequisite: SuperGrok / X Premium+ subscription (OQ5).
- **[OWNER ACTION]** Upgrade codex-cli to the ratified target version
  (OQ4) alongside; keep 0.139.0 binary path noted for A/B fixture
  comparison.
- Record **grok wire fixtures** (the PLAN-155 A14 pattern): live
  sessions capturing every hook event's stdin envelope + accepted
  decision shapes, `_meta.grok_cli_version` pinned. Empirically resolve
  ALL research lacunae (shard §Lacunas): (a) does the stdin `toolName`
  carry the native or the Claude-mapped name? (b) does
  `{"decision":"block"}` work or must it be `"deny"`? (c) is there a
  `Task`-equivalent spawn tool name the matcher can see? (d)
  instructions-file surface (AGENTS.md equivalent)? (e) **native/OS
  read-only containment for headless runs** (gates the council grok
  lane — see Wave 6)? (f) do `--cwd` / `--permission-mode` actually
  exist natively (seen only in third-party usage — possibly
  compat-layer artifacts)? (g) **double-fire probe**: with BOTH native
  `.grok/hooks/` and the legacy `.claude/settings.json` compat present
  (forced coexistence in a dual-harness repo), do hooks fire twice, with
  which tool-name vocabulary each, and what does that do to dedup on
  the audit chain? (h) **is `exit 2` inert/ignored on Codex?** — gates
  whether the C1 decision→exit mapping (Wave 2) can be UNCONDITIONAL
  across harnesses or must be adapter-aware (debate C14 / Sec unseen-4).
- **Enumerate every DIRECT (non-shim) hook registration** in BOTH the
  live `.claude/settings.json` AND the install templates (pair-rail
  R7/R9): today `check_codex_filewrite.py` runs via raw `python3` at
  `.claude/settings.json:291` AND `templates/settings/settings.base.json:108`
  — fixing only the dogfood settings leaves NEW installs inheriting the
  same fail-open under Grok legacy-compat. The Wave-2 exit-2 chokepoint
  fix + the CI meta-test cover the TEMPLATE registrations too (the list
  is the input to that wave's routing decision). **NOTE (pair-rail R13)**:
  `templates/settings/**` is NOT currently in the canonical guard-list
  (`check_canonical_edit.py` guards `.claude/settings.json` + the
  install/upgrade distribution scripts, NOT `templates/settings/`) — so
  Wave 2/3 MUST either add `templates/settings/settings.base.json` to the
  guard-list (recommended — it is a fail-open-bearing install surface)
  **AND add `templates` to `_CANONICAL_PREFIXES`** (pair-rail R14 — same
  dead-guard class as `.grok`: `_is_canonical()` returns before glob
  matching unless the first path segment is a known prefix, and
  `templates` is not currently one, so the guard would be INERT without
  it) OR rely on the CI meta-test as the sole protection and say so
  explicitly. Do NOT assert it is sentinel-guarded when it is not; pick
  one branch and make it fully true in the wave (prefix + glob, or CI).
- `substrate-watch.json`: add TWO watch items — grok-build release
  channel (daily cadence ⇒ weekly staleness check) and codex-cli
  releases (the silent-model-fallback class from the fable-advisor
  README rides here too, per S266 finding).
- Create `.claude/governance/grok-cli-pin.txt` (exact-version pin — 0.x
  daily releases make a semver range meaningless) + binary SHA file,
  mirroring the codex pair. **Enroll BOTH in `_KERNEL_PATHS`
  (`check_arbitration_kernel.py`) in THIS wave** (debate C12) so the
  Wave-4 registry edit does not trip a surprise kernel-guard block; the
  Wave-0 sentinel scope declares them.
- Draft the FULL sentinel set the guarded waves consume (pair-rail R7):
  **SENT-GK-0** (W0b pin/kernel enroll), **SENT-GK-{A,B,C,D,E}** (Waves
  2-5), **SENT-GK-F** (W6a council audit action) — every guarded wave
  has a pre-planned Owner-signable sentinel, none deferred to an ad-hoc
  ceremony. + ADR-162 skeleton
  (grok capability matrix + exit-2 discipline), anchors progressive,
  same ceremony mechanics as PLAN-155 (land-plan155.sh pattern).

### Wave 1 — Codex 5.6 refresh (SENT-CX-PIN; independent of Grok waves)

Facts base: `PLAN-156/artifacts/research-gpt56-codex-cli-S266.md` +
S266 local probe. Family = `gpt-5.6-{sol,terra,luna}` (bare `gpt-5.6`
aliases Sol@medium; **no `-codex` suffix exists in the 5.6 generation**).
5.6 first-class in codex-cli **0.143.0**; latest **0.144.1** (2026-07-09).

- **Pin-update ceremony per ADR-111**: bump
  `.claude/governance/codex-cli-pin.txt` upper bound to the ratified
  target — **RECOMMENDED `>=0.128.0,<0.145.0`** (widen upper only; the
  `>=0.128.0` lower bound is UNCHANGED — a target that also raised the
  lower bound, e.g. `>=0.144.1`, is exactly the C10 hazard: it drops an
  in-flight 0.139 RC verdict out of range and red-locks the GA cut).
  OQ4; triage the four open 0.144.0 model-availability bugs
  `#31869/#31873/#31860/#31826` before fixing the exact ceiling; update
  `codex-cli-binary-sha256.txt`; run the locked-corpus catch_rate check
  (>5pp shift ⇒ ADR-111 amendment; Owner elects run-vs-defer at signing,
  S246 precedent: run it). (debate C10 / R-OPS-5): the pin's real
  enforced consumer is `release.yml` step-15
  (`verdict.tool_versions.codex_cli in range`; `pair-rail-gate.sh` Gate-4
  is a stub-pass, NOT the gate); raising the lower bound would drop an
  in-flight RC verdict out of range and red-lock the GA cut. The
  `codex-cli-binary-sha256.txt` edit (a `_KERNEL_PATHS` path) is the real
  supply-chain gate. **Do not run the bump during an open release window.**
- **0.143 flag-rename audit**: 0.143.0 renamed the sandbox
  permission-profile CLI flag — grep every `codex exec` call site
  (`codex-exec-wrapper.sh`, `codex-advisory-teeth.py`,
  `check_codex_stop_review.py`, pair-rail invoke, docs) for the old
  spelling and assert against the new binary's `--help` before landing.
- **Reasoning-effort enum guard**: the enum is validated CLIENT-SIDE at
  startup (old binaries hard-fail on `xhigh`/`max` before any request;
  `max` first-class @0.143). Any config we template must match the
  pinned binary's enum, asserted empirically (`ultra` is
  interactive-product-only — do not template it).
- **Re-verify the PLAN-155 capability matrix on the new CLI**:
  re-record codex golden fixtures with new `_meta.codex_cli_version`,
  run `test_adapter_drift_detector.py`, replay the behavioral positive
  controls (canonical-deny live-fire, Stop `decision:block` enforcement,
  SubagentStart non-enforcement). Hooks schema is reported STABLE
  0.139→0.144 (0.142 loosened hooks.json metadata validation —
  permissive direction) — the replay proves it rather than trusting it.
  Any flip in an ENFORCED/ADVISORY cell updates
  `provider_capability_matrix.md` + ADR-161 amendment.
- 5.6 in the lanes: document `gpt-5.6-sol` (flagship, $5/$30),
  `gpt-5.6-terra` (balanced, $2.50/$15), `gpt-5.6-luna` (fast, $1/$6,
  1.05M ctx) as operator models; pair-rail reviewer invocation gains an
  optional explicit model pin (`CEO_PAIR_RAIL_CODEX_MODEL`, default =
  account default, mirroring `CEO_PAIR_RAIL_REVIEWER_MODEL` on the
  inverted rail).
- **Deprecation entries** for `check-model-deprecations.py` source:
  `gpt-5.2` + `gpt-5.3-codex` (API requests blocked 2026-06-30, endpoint
  removal 2026-12-31), `gpt-5`/`o3` snapshots (2026-12-11). `gpt-5.5` is
  NOT deprecated.

### Wave 2 — Grok host adapter (SENT-GK-A; kernel-class)

- `_lib/adapters/grok.py` host mode: `read_event()` normalizes the
  camelCase envelope + native tool names to `NormalizedEvent`;
  `write_decision()` emits `{"decision":"deny"|"allow","reason":…}`.
  Normalizes our internal `block` → grok `deny`.
- **Exit-2 chokepoint (the wave's linchpin — debate C1, Sec R-SEC1/2)**:
  today the deny-JSON emit and the process exit are DECOUPLED
  (`_python-hook.sh` execs the hook; `write_decision` only writes stdout,
  never `sys.exit`). On Grok, deny REQUIRES exit 2 specifically — a
  correct `{"decision":"deny"}` on stdout still fail-OPENs if nothing
  set exit 2. Fix, committed here (not left as an open question):
  - **ONE shared chokepoint owns the decision→exit mapping**, in the
    shared shim (`_python-hook` entrypoint) — the single path every hook
    routes through, and where native `.grok/hooks/` point. It cannot
    live in Python dispatch (interpreter crash / ImportError / signal
    never reach Python).
  - The exit code is **decision-derived, not exit-code-derived**: a
    hook that EMITTED a deny decision → exit 2; emitted allow → exit 0;
    **crashed with NO decision → fail-OPEN allow (infra half of CLAUDE.md
    §4 preserved)**. This distinguishes an `ImportError` (infra → allow)
    from an input-class deny (→ exit 2) without inspecting the raw exit
    code — the shim captures stdout to see whether a decision was
    emitted. Security matchers emit the structured deny themselves on
    input-parse failure (the codex.py coherence-gate pattern, extended
    to also drive the exit); the shim maps emitted-deny→2.
  - **UNCONDITIONAL mapping preferred over `CEO_HOOK_ADAPTER=grok`-gated**
    (Sec R-SEC2: an unset/misresolved env under Grok would silently run
    the old fail-open mapping) — SAFE iff Wave-0 lacuna (h) confirms
    `exit 2` is inert on Codex; if not, the mapping is adapter-aware with
    a fail-SAFE default when adapter resolution is uncertain.
  - **The shim is NOT the single path today (pair-rail R7)**:
    `.claude/settings.json:291` registers `check_codex_filewrite.py`
    DIRECTLY with `python3` (not via `_python-hook.sh`), and it emits a
    Claude-shaped `block` while exiting 0 — under Grok that fail-closed
    matcher still fail-OPENs even after the shim gains the mapping.
    Wave-0 enumerates EVERY direct (non-shim) hook registration; Wave 2
    either re-routes each through the chokepoint OR gives it an
    equivalent decision→exit-2 wrap, and the CI meta-test (below)
    iterates the FULL registered-hook set, not just shim-routed ones —
    so a direct registration that fail-opens under Grok reddens CI.
- **SPEC/v1 amendment for the exit ABI (pair-rail R4 — guarded)**:
  `SPEC/v1/hook-io.schema.md` currently mandates every hook exit 0
  regardless of decision, and `adapters.schema.md` defines
  `write_decision()` as stdout-only. Mapping emitted-deny→exit-2 on
  non-Claude hosts is an ABI change — it lands as a GUARDED SPEC
  amendment (SPEC/v1 carries `deny: Edit(SPEC/**)`; apply via the
  sentinel scope, Bash-under-sentinel per the S265 filetype-guard
  playbook), not a silent divergence. **Scope of the amendment (pair-rail
  R11)**: because the preferred mapping is UNCONDITIONAL in the SHARED
  shim, the exit-2-on-emitted-deny behavior applies to EVERY adapter the
  shim routes, not just grok — so the amendment cannot be grok-scoped or
  the ABI and impl diverge for Claude/Codex. It documents the
  decision-derived rule for all shim-routed adapters
  (emitted-deny→2, emitted-allow→0, no-decision-crash→fail-open-0) and
  notes each host's tolerance: Claude already accepts exit-2 as a deny
  alias, Codex accepts exit-2+stderr, grok REQUIRES exit-2. **If Wave-0
  lacuna (h) finds exit-2 is NOT inert on Codex**, the shim falls back to
  adapter-aware mapping and the amendment is correspondingly scoped to
  the adapters where exit-2 is safe — the SPEC scope tracks the shim
  scope, never narrower.
- **CI teeth for the exit-2 class (debate C2, DevOps R-OPS-2)**: a
  hermetic meta-test (no grok binary) that FAILS if any hook can emit a
  deny while the process exits non-2 under the grok mapping — feed each
  security matcher an INPUT it cannot parse so it EMITS a structured deny
  (NOT a bare interpreter crash — that is infra and must fail-open),
  assert deny+exit-2; plus the paired infra case (simulated ImportError →
  allow). Rides the **Wave-2 golden/drift suite** (RED-on-absence, like
  validate.yml's fail-open-rail self-test), NOT a Wave-7-only local
  artifact. "Impossible to forget" is a test, not reviewer vigilance.
- **Matcher tool-name vocabulary (debate C3, Sec R-SEC3)**: Grok
  evaluates the matcher and decides whether to spawn our hook process
  BEFORE our Python runs — so in-adapter `read_event` normalization is
  too late to save a matcher that never fired. If matcher + stdin both
  carry the NATIVE name, `^Bash$` never matches `run_terminal_cmd` and
  bash-safety silently no-ops (S254 dead-gate; invisible to fixture
  replay, which enters AFTER the matcher gate). W3 matchers MUST cover
  BOTH native and mapped names; the ENFORCED claim is GATED on Wave-0
  fixture (a); the W7 positive control drives a NATIVE-named call
  (`run_terminal_cmd` for `rm -rf ~`) — a mapped-name-only test proves
  nothing.
- `KNOWN_ADAPTERS` += `"grok"` (contract.py + ADAPTER_REGISTRY;
  `CEO_KERNEL_OVERRIDE=PLAN-156-GROK-HOST-ADAPTER`).
- **Enroll `grok.py` in `_KERNEL_PATHS` (pair-rail R4/R5)**:
  `check_arbitration_kernel.py` enumerates adapter modules INDIVIDUALLY
  (`claude.py`, `codex.py`), not by glob — so `grok.py` must be added to
  `_KERNEL_PATHS` in THIS same kernel-guarded wave, else later edits to
  the new enforcement adapter are only sentinel-gated, unlike the
  existing host adapters (an asymmetry a future edit would exploit).
- Golden + drift-detector + seam-dispatch tests from Wave-0 fixtures;
  characterization tests lock the reviewer-egress surface untouched.

### Wave 3 — Grok templates + kill-switch extension (SENT-GK-E)

- `templates/grok/`: native `.grok/hooks/ceo.json` (schema is
  Claude-shaped; matchers regex over tool names — cover BOTH native and
  mapped names until Wave-0 fixture data settles which fires),
  `config.toml` example, trust-flow doc (`/hooks-trust`,
  `~/.grok/trusted_folders.toml`), instructions-file template per
  Wave-0 finding (e).
- **OQ1**: ship native `.grok/hooks/` (recommended — explicit, pinned,
  and the legacy `.claude/settings.json` compat layer's coverage is
  undocumented) with the legacy-compat path documented as fallback.
- **Double-fire resolution (debate C6, Sec R-SEC5)**: coexistence of
  native `.grok/hooks/` + legacy `.claude/settings.json` is FORCED in a
  dual-harness repo and would fire every hook twice — deny stays
  idempotent, but `grok_tool_recorded`/`grok_turn_ended` append twice
  (HMAC double-count, completeness/reconciliation drift, filelock race).
  Resolve the surface empirically at Wave-0 (g), pick EXACTLY ONE, and
  assert INERTness with a positive control that counts hook invocations
  per tool call: **total == 1 (chosen == 1, non-chosen == 0)**, not
  merely "deny observed" — a deny-only test cannot distinguish
  fired-twice / fired-once / never-fired (the C3 dead-gate).
- Kill-switch guard-list extension in `check_canonical_edit.py`:
  `.grok/hooks/**`, `.grok/config.toml` (project-level; the global
  `~/.grok/` surface is out of repo reach — documented residual, same
  class as codex `~/.codex`). **CRITICAL impl detail (pair-rail R4)**:
  `_is_canonical()` returns EARLY unless the path's first segment is in
  `_CANONICAL_PREFIXES` — so adding the `.grok/**` patterns to
  `_CANONICAL_GUARDS` WITHOUT also adding `.grok` to `_CANONICAL_PREFIXES`
  leaves the new guards INERT (unsentineled `.grok/hooks/` edits sail
  through). Both edits land in THIS wave's guarded scope. SessionStart
  boot re-hash tripwire covers the new files (Wave-3b PLAN-155 pattern).

### Wave 4 — Grok audit chain + installer (SENT-GK-B + SENT-GK-C)

- Audit actions `grok_tool_recorded`, `grok_turn_ended` (+2 over the
  **live golden count at land time** — 320 lines at drafting; never a
  hardcoded prior, the tolerance-0 gate reconciles) + tamper-mirror
  parity with the codex pair; completeness bound documented (hook
  coverage on Grok is per-event, same absence-is-not-evidence caveat).
- **SPEC/v1 audit-log amendment (pair-rail R4/R11 — guarded)**: the
  Wave-4 actions `grok_tool_recorded` + `grok_turn_ended` join the
  published contract `SPEC/v1/audit-log.schema.md` WITH a version-history
  row (the prior `codex_*` actions set the precedent) — else generated
  logs carry actions absent from the compliance schema. **`council_lane_invoked`
  is NOT amended here (pair-rail R11)**: Wave 6 may slip without blocking
  W0-5, so publishing its contract action in Wave 4 would either couple
  W0-5 to W6 or publish an action the framework cannot yet emit. That
  schema row lands in W6a alongside its emitter/golden registration.
  Guarded SPEC edit, same sentinel-scoped mechanism as the hook-io
  amendment.
- Installer `--harness grok` via sourced `scripts/_grok_harness.sh`
  (mirror of `_codex_harness.sh`): emits templates, arming check.
- **`upgrade.sh` replay coverage (pair-rail R11)**: `--harness` is not
  install-only — `scripts/upgrade.sh` sources the harness helper and
  REPLAYS the recorded harness value on every framework upgrade. Wave 4
  extends `upgrade.sh` to source `_grok_harness.sh` and re-arm the grok
  surface (templates + guard-list + pin re-check) on upgrade, mirroring
  the codex round-trip — else a repo installed `--harness grok` silently
  loses (or fails to re-arm) its grok rail on the next upgrade. The
  install-matrix test adds an upgrade round-trip case (install grok →
  upgrade → assert grok surface still armed).
- **Arming refuse-on-drift (debate C11, Sec R-SEC7)**: the arming check
  asserts `grok --version == grok-cli-pin.txt` AND binary-SHA match;
  on mismatch the harness SETUP fails closed (never the user session) —
  refuse to run governance against an uncharacterized binary rather than
  degrade silently. Every auto-update is a substrate-watch trigger that
  re-runs the capability-matrix positive controls before the new
  binary's ENFORCED cells are trusted.
- **CI hermeticity is an ACCEPTANCE CRITERION (debate C7, R-OPS-1)**:
  `scripts/tests/test-install-harness-grok.sh` runs fixture/recorded-wire
  replay — **ZERO grok binary, ZERO xAI secret on any runner** (mirror
  the codex property at validate.yml:348-351, not just "mirror the
  script"). Live-fire is the local T2 tier (Owner's authed machine).
- **validate.yml anchor (debate C9, R-OPS-4)**: do NOT add adjacent
  steps to the anchor two PLAN-155 riders already occupy. Extend the
  existing `for adapter in claude codex` loop (validate.yml:374) to
  `claude codex grok` with an adapter-shape-aware body (grok takes the
  fixture-replay path) — no new step. For any edit that must be new,
  consolidate ALL grok validate.yml changes into ONE signed patch
  (under a single SENT-GK) rather than splitting across sentinels, or
  append at a fresh anchor at the end of the job.

### Wave 5 — Grok inverted pair-rail (SENT-GK-D)

- Honest labels first: on Grok, **Stop is NON-blocking** ⇒ the
  Stop-review gate is ADVISORY by construction; the **git pre-push
  gate is the teeth** (reuse `templates/codex/pre-push-review-gate.sh`
  generalized to `templates/shared/` or a grok copy — decided at
  execution by diff size). Reviewer = `claude -p` with the OQ3 pins
  from PLAN-155 (`claude-opus-4-8`, 100k ceiling, env overrides).
- validate.yml advisory-teeth rider extension for grok session records.
- capability-matrix row certified by behavioral replay, not config.

### Wave 6 — Cross-Vendor Audit Council (SPLIT: 6a guarded SENT-GK-F incl. workflow guard-listing / 6b docs unguarded)

**The Owner's "conselho"**: a read-only, three-vendor audit instrument.

**Guarded split (pair-rail R2 + R9 findings)**: 
- **W6a under SENT-GK-F** — the `council_lane_invoked` audit action
  registers in `.claude/hooks/_lib/audit_emit.py` +
  `audit-registry.golden.txt` **AND its `SPEC/v1/audit-log.schema.md`
  row lands HERE, not in Wave 4** (pair-rail R11 — so a slipped Wave 6
  never publishes a contract action W0-5 cannot emit); +1 over the live
  golden AFTER Wave 4's +2, i.e. 322→323 if drafting-time 320 holds;
  reconcile against the live count at land time, tolerance-0 gate — never
  a hardcoded prior. **PLUS**: `council-audit.js` OWNS the live
  external-lane egress (redactor invocation, budget hard-kill, no-CI
  fence) — so `.claude/workflows/council-audit.js` and the `/council`
  command are **added to the canonical guard-list** (`.claude/workflows/`
  is NOT currently canonical-guarded — verified: only `.github/workflows/*`
  is, `check_canonical_edit.py:182`). Without this, a later ordinary edit
  could strip the redactor/fence and transmit repo content unredacted.
  The guard-list extension + the workflow/command land under SENT-GK-F.
- **W6b (unguarded)** — docs (`/council` usage in README/adapters). W6b
  depends on W6a (the workflow emits the action + must be guard-listed
  first) — landing order enforces it.

**Dependency: Wave 6 consumes Wave 1** (the codex lane invokes the
post-bump CLI + ratified model) and is INDEPENDENT of Waves 2-5 for its
Claude+Codex lanes; the grok lane additionally gates on Wave 0 finding
(e). Wave 6 carries its own mini threat model (below) and slips to a
follow-up plan without blocking Waves 0-5 if debate round 3 objects.

- `.claude/workflows/council-audit.js` extending the audit-fanout shape
  (find → refute → synthesize, ADR-141 8-field shards, ADR-136-AMEND-1
  read-only confinement) with **vendor lanes**:
  - *Claude lane*: existing finder/refuter agents (in-harness). Confined
    by **ADR-136-AMEND-1 workflow read-only confinement** (workflow
    agents write NO files — the harness-structural guarantee), NOT an OS
    sandbox. This is a DIFFERENT containment mechanism than the CLI lanes
    (pair-rail R13): the acceptance bar is "zero file writes proven per
    lane by its appropriate mechanism", not "every lane OS-sandboxed".
  - *Codex lane*: `codex exec --sandbox read-only --skip-git-repo-check`
    fed the dimension brief + shard schema; output parsed to shards
    (OS-level containment — the sandbox flag, not our hooks).
  - *Grok lane*: `grok -p … --output-format json` headless.
    **Containment (debate R1 + codex R1 convergent finding, adopted):
    requires NATIVE/OS-level read-only containment** (native flag or
    macOS sandbox-exec / read-only bind, resolved by Wave-0 lacuna (e));
    a deny-all-writes CEO hooks profile rides on top as
    defense-in-depth but is NEVER the load-bearing layer — on Grok,
    hook failure is fail-open, so hooks-as-sandbox is circular. If no
    OS containment is available, the grok lane reports
    `STATUS: unavailable` (fail-loud) and the council runs 2-lane.
  - *Mini threat model (lane-shared)*: repo content flows OUT to two
    authenticated external LLMs; lane responses flow IN as untrusted data.
- **EGRESS through the ADR-114 redactor (debate C4, Sec R-SEC4 — BLOCKING)**:
  EVERY external-lane prompt (codex AND grok) routes through the existing
  pair-rail egress redactor (`codex_egress_redact`, ADR-114 §AC9) before
  it leaves the process — reuse that single chokepoint, forbid a second
  unredacted path. A secret in any scanned file otherwise transmits to
  two third parties (training/retention), and the grok lane sends under
  the Owner's paid X account. HONEST-LIMITATION "repo content is
  transmitted to xAI/OpenAI" added; **OQ5 becomes a privacy/egress
  ratification, not merely "does the subscription exist."**
- **INGRESS as untrusted (debate C13, Sec nice-to-have 1)**: lane
  responses are size-capped, schema-conformed, fail-closed-to-ADVISORY
  (`parse_verdict_strict` pattern), and the shard text is FENCED as
  untrusted data in the Claude synthesis prompt — a hostile file cannot
  smuggle instructions into the synthesizer via a vendor lane.
- **Fail-loud doctrine** (adapted from fable-advisor, credited): lane
  unavailable/timeout ⇒ shard `STATUS: unavailable` in the synthesis
  table — NEVER silent vendor substitution; a lapsed grok subscription
  is just another `unavailable`, not a red build (DevOps unseen-2);
  quorum degrades explicitly (3-lane → 2-lane verdict labeled as such).
- **Reduce with vendor attribution**: every verdict carries which
  vendors confirmed/refuted; cross-vendor DISAGREEMENT is a first-class
  signal escalated in the report (that disagreement surface is the
  council's reason to exist).
- **Council is FENCED OUT of CI (debate C8, R-OPS-3 — BLOCKING)**:
  operator/local-only; NO CI job invokes a live lane (three vendor
  secrets on a runner + unbounded token burn + nondeterminism + egress
  on every trigger are all forbidden). CI may exercise ONLY the
  shard-parse + fail-loud degradation logic against FIXTURE lane outputs
  (a mocked `unavailable` lane).
- `/council` command: `/council <scope>` → runs the workflow, renders
  the vendor-attributed verdict table. Council output is ADVISORY
  evidence for the Owner — it authorizes nothing by itself (same
  demotion as debate, PROTOCOL.md §Verification cascade).
- **Budget ceilings per lane (OQ6) = HARD KILL, not advisory** (Sec
  nice-to-have 4: an external LLM in a fanout is a cost-DoS surface if a
  lane loops) — a hard default cap enforced in the workflow before the
  first live run. Each lane invocation emits a `council_lane_invoked`
  audit action (who asked what, when) so cross-vendor egress is itself
  auditable (completeness caveat applies).

### Wave 7 — Positive controls, docs, closeout (docs unguarded; matrix guarded via SENT-GK-D scope or standalone)

- Live-fire artifacts under `PLAN-156/artifacts/`: grok canonical-deny
  replay transcript; **exit-2 fail-CLOSED proof via an INPUT-PARSE
  failure that emits a structured deny** (feed a security matcher hostile
  input it cannot parse → it emits deny → the chokepoint maps to exit 2 →
  assert the tool is blocked). NOT a bare interpreter crash — a crash
  with no emitted decision is INFRA and must fail-OPEN per Wave 2 /
  CLAUDE.md §4; asserting deny on a bare crash would push toward a
  blanket nonzero→deny remap that breaks the fail-open-on-infra half.
  Both halves are proven: (i) input-parse deny → blocked+exit-2;
  (ii) simulated ImportError/infra crash → ALLOWED (fail-open). Plus
  Stop-advisory demonstration and council 3-lane + degraded 2-lane runs.
- `docs/adapters.md` + `provider_capability_matrix.md` gain the grok
  column with residuals; `docs/degradation-outside-claude-code.md`
  updated; INSTALL/README `--harness grok`; HONEST-LIMITATIONS: curl|bash
  installer, 0.x volatility, advisory Stop, subscription requirement.
- ADR-162 (grok capability matrix + exit-2 discipline) accepted; counts
  closeout (hooks/ADR/actions/lib per verify-counts) + CLAUDE.md bump.
- Lesson check: run the S266 clean-clone proof on every wave that lands
  tests authored in staging ([[feedback-ci-mirror-needs-clean-clone]]).

## Open Questions (Owner ratifies at Wave-0 signing)

1. **OQ1 — hooks surface**: native `.grok/hooks/` (RECOMMENDED) vs the
   undocumented `.claude/settings.json` legacy-compat path.
2. **OQ2 — grok pin policy**: exact-version pin + weekly substrate-watch
   staleness (RECOMMENDED, daily releases) vs semver range.
3. **OQ3 — council lane models**: grok lane `grok-4.5` vs
   `grok-build-0.1`; codex lane default post-bump (RECOMMENDED:
   `gpt-5.6-terra` for council refuters — balanced tier, 2.5x cheaper
   than Sol; Sol reserved for explicit deep-review asks).
4. **OQ4 — codex-cli target version**: RECOMMENDED `>=0.128.0,<0.145.0`
   (widen upper bound ONLY — lower bound stays `>=0.128.0`) after
   triaging open bugs #31869/#31873/#31860/#31826; ratify whether the
   locked-corpus catch_rate run happens at ceremony (S246 precedent: run
   it). Facts: `PLAN-156/artifacts/research-gpt56-codex-cli-S266.md`.
5. **OQ5 — subscription**: confirm SuperGrok/X Premium+ available for
   `grok login` (blocks every Grok wave; Wave 1 proceeds regardless).
6. **OQ6 — council budget**: per-lane token/time ceilings per audit run.

## Acceptance criteria

- [ ] Wave 1: codex-cli at ratified version; `codex exec --model
      gpt-5.6-sol` (or luna) returns output, not a version error;
      capability matrix re-certified on the new CLI; pin files + ADR-111
      trail complete; upper-bound WIDENED only (lower bound unchanged);
      0.143 flag-rename audited against the new binary `--help`.
- [ ] Wave 2-5: `CEO_HOOK_ADAPTER=grok` positive controls — a canonical
      edit via grok is DENIED at edit-time (live-fire transcript);
      **a NATIVE-named call (`run_terminal_cmd` for `rm -rf ~`) trips
      bash-safety** (mapped-name-only proves nothing); Stop-review
      labeled ADVISORY with the pre-push gate proven blocking; installer
      `--harness grok` matrix green; audit chain records grok rails.
- [ ] **Exit-2 CI teeth**: a hermetic meta-test (no grok binary) FAILS
      if any hook emits a deny while exiting non-2 under the grok
      mapping; rides the Wave-2 golden/drift suite (RED-on-absence).
- [ ] **Double-fire**: an invocation-COUNT positive control asserts
      TOTAL hook invocations per tool call == 1 (chosen surface == 1,
      non-chosen surface == 0) — not a deny-observed test, which cannot
      tell fired-twice from fired-once from never-fired.
- [ ] **Grok CI hermeticity**: the grok installer matrix runs
      fixture/recorded-wire replay with ZERO grok binary and ZERO xAI
      secret on any runner (asserted, not implied).
- [ ] Wave 6: `/council <scope>` returns a vendor-attributed verdict
      table from ≥2 live lanes; a killed lane shows `unavailable`
      (never silent substitution); **zero file writes proven per lane by
      its appropriate mechanism** — Claude lane by ADR-136 workflow
      confinement, Codex/Grok lanes by OS sandbox (Grok `unavailable`
      until its OS containment qualifies; the CLI lane that CAN write
      must be OS-sandboxed, not hooks-only); every external-lane prompt
      passed through the ADR-114 egress redactor; NO CI job invokes a
      live lane.
- [ ] Full suites green + clean-clone proof; counts reconciled against
      the live golden at land time; capability matrix + ADR-162 landed;
      no speed claim added.

## Honest limitations (carried into docs)

- Grok Stop/UserPromptSubmit are non-blocking: session-end review is
  advisory there; push-time is the enforcement point.
- Grok SubagentStart parsed but non-blocking (same honest-ADVISORY row
  as codex spawn governance).
- Grok Build is proprietary, 0.x, daily releases: surface may shift
  under the pin; the substrate watch is load-bearing, not decorative.
- Fail-open-on-crash is NOT Grok-unique: the PLAN-155 failure-semantics
  matrix already records Codex timeout / non-2 exit / crash as fail-open
  (an existing residual). Grok's distinction is that deny REQUIRES exit 2
  specifically (Claude also accepts JSON-block; Codex accepts JSON-only),
  so the decision-derived exit-2 chokepoint is mandatory THERE, its
  absence in any future hook is a security regression class, and the
  hermetic CI meta-test is what keeps it from silently recurring. The
  chokepoint is shared, so it hardens the Codex residual too.
- **Council egress**: running a council transmits the audited repo scope
  to xAI (grok lane, under the Owner's paid X account) and OpenAI (codex
  lane) — third-party training/retention applies. Egress is redacted
  (ADR-114) but not eliminated; the Owner ratifies this at OQ5 as a
  privacy decision.
- **Recurring operational load**: a third proprietary daily-0.x harness
  adds a standing weekly substrate-watch + re-fixture obligation no CI
  can automate (no binary/secret on the runner). The Owner ratifies the
  RECURRING commitment at Wave-0 signing, not just the one-time build
  (CLAUDE.md §5 bus-factor).
- The Grok installer is an unpinned proprietary rolling script; the
  Wave-0 runbook mandates fetch-hash-inspect-THEN-execute (never
  `curl … | bash`), and the binary-SHA pin is the real supply-chain gate.
  Residual: the installer script itself is trust-on-first-fetch (no
  publisher signature verified), documented for the Owner.
- Council verdicts are advisory evidence with vendor attribution — not
  a truth gate; the verification cascade (V0-V3) is unchanged.
