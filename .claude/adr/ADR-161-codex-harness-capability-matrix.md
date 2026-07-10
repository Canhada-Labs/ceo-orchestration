# ADR-161: Codex harness capability matrix + host-adapter doctrine

**Status:** PROPOSED (PLAN-155, S265, 2026-07-10 — flips ACCEPTED in the
landing series. `.claude/adr/` is canonical-guarded — NEW files included
(S261 confirmation) — so this record does NOT land direct: it rides the
**SENT-CX-A ceremony batch** (Wave 1) with the rest of the guarded
host-adapter surface, under
`CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-HOST-ADAPTER` + `..._ACK=I-ACCEPT` for
its kernel co-travellers. The Wave 3b matrix-reconciliation edit to this
record — flipping the kill-switch row from ABSENT — lands in the SENT-CX-E
batch, not silently widened into SENT-CX-A; see Decision 7.)
**Date:** 2026-07-10
**Decision drivers:** Owner directive (S261/S262) to make the framework
FUNCTIONAL on OpenAI Codex — an installable, enforcing rail, not a stub
matrix row; the house honesty invariant that every "runs on Codex" claim be
read as "same guarantees as Claude Code" unless each rail carries its label
and residual in-claim; the S254 dead-gate lesson (a registered rail that
silently resolves to nothing) which the empirical failure-semantics work
proved is the DEFAULT failure mode of the Codex harness, not an edge case.
**Related decisions:** ADR-008 (adapter layer — this is its second host),
ADR-158 (behavioral-positive-control-certifies doctrine — the certifying
instrument here is the subprocess replay, not a config-file scan), ADR-107 /
ADR-145 (pair-rail + cross-model review modality — inverted here), ADR-121
(dual signer rails governing the SENT-CX landings), ADR-111 (codex-cli pin
ceremony this record binds fixtures to), ADR-116-AMEND-1 (the PLAN-153
kernel-extension-v2 that put the adapter/audit/SessionStart modules in
`_KERNEL_PATHS`, driving the S265 override requirements). PLAN-152 debate C4
(fail-open-on-infrastructure / fail-closed-on-input) is carried unchanged.

## Context

Codex-cli 0.139 ships a lifecycle-hooks system nearly identical to Claude
Code's, speaking the same `hookEventName` / `permissionDecision` /
`hookSpecificOutput` / `additionalContext` vocabulary our adapter layer
(ADR-008) already emits. That surface similarity is real but partial, and
"partial" is where every overclaim would live. Before any doc or matrix row
in PLAN-155 could be treated as normative, the debate (round-1
ADJUST_PROCEED, A1–A26) required the wire to be recorded from the LIVE local
binary, not read from vendor docs. This record fixes what was observed, in
the vocabulary the house uses for every capability claim: **ENFORCED /
ADVISORY / ABSENT**, each ENFORCED claim naming its residual and its
backstop. It also fixes the host-adapter doctrine that makes the ENFORCED
rows true rather than dead — the seam, the coherence gate, the emit-shape
correctness lesson, and the KERNEL-override ceremony that guards the
kill-switch surface.

All empirical claims below are grounded in artifacts recorded against
`codex-cli 0.139.0` (verbatim `codex --version`), archived under
`.claude/plans/PLAN-155/artifacts/`: `failure-semantics-matrix.md`,
`stop-block-transcript.md`, `subagentstart-transcript.md`,
`trust-keying-A6.md`, `normalization-notes.md`, `live-fire-canonical-deny.md`.

## Decision

### 1. The capability matrix is normative (ENFORCED / ADVISORY / ABSENT)

Every outward document (`docs/degradation-outside-claude-code.md`,
`docs/adapters.md`, `docs/provider_capability_matrix.md`,
`docs/HONEST-LIMITATIONS.md`, README/INSTALL) MUST reflect this matrix, and
no rail may be described without its residual. Every Codex row is verified
against `codex-cli 0.139.0`; the fixtures follow the PIN, not upstream
(Decision 6).

| Rail | Codex primitive | Status | Residual + backstop |
|---|---|---|---|
| Canonical-edit guard (`check_canonical_edit.py`) | PreToolUse `apply_patch\|Edit\|Write\|mcp__.*` → `permissionDecision: deny` | **ENFORCED** (edit-time; live-fire proven, `live-fire-canonical-deny.md`) | Residual: writes smuggled through complex/opaque shell; multi-file `apply_patch` path-gated but Update-hunk content NOT reconstructable from the wire (Decision 8, Open-issue #3). Backstops: the `^Bash$` rail sees the full command string; CODEOWNERS + branch protection at push. |
| Bash safety (`check_bash_safety.py`) | PreToolUse `^Bash$` running our exact parser + `.codex/rules/ceo.rules` execpolicy `prefix_rule(decision=forbidden)` coarse backstop | **ENFORCED** | Residual: official caveat — Codex "doesn't intercept all shell calls yet, only the simple ones"; opaque single commands may not fire the hook. Our hook receives the full string on every event that DOES fire and applies its own parser (the `_e3` whole-command gate stays fail-closed on input). |
| Plan lifecycle (`check_plan_edit.py`) | PreToolUse on `.claude/plans/**` writes; Add-op content synthesized per-op from the patch (`codex.py`) | **ENFORCED** (edit-time) | Residual: illegal transitions smuggled through `apply_patch` **Update** hunks are path-gated but not content-gated (full new content absent from the wire — Open-issue #3); CI plan-schema checks at push. |
| Arbitration kernel (`check_arbitration_kernel.py`) | PreToolUse unconditional deny on kernel paths; any kernel path in a multi-file patch is picked out | **ENFORCED** (edit-time) | Same shell-escape residual class; kernel paths also in CODEOWNERS. |
| Spawn governance (`check_agent_spawn.py`) | Two distinct primitives — see Decision 3 | **SPLIT: ENFORCED for collab spawns, ADVISORY for SubagentStart** | `SubagentStart` `continue:false` is parsed but does NOT stop the subagent (`subagentstart-transcript.md` §A). BUT the collab spawn is itself a `PreToolUse` `tool_name: spawn_agent`, and `permissionDecision: deny` there DOES block it (§B — no SubagentStart fires). Residual: only collab-tool spawns are ENFORCED; Bash-smuggled spawns re-enter the `^Bash$` rail; `additionalContext` injection is the ADVISORY mitigation for the SubagentStart path (§C, verified end-to-end). Backstop: Wave-6 chain scan over spawn records. |
| Pair-rail review | **INVERTED**: Codex operates, reviewer = `claude -p` (non-interactive); Stop hook `decision:block` auto-continues until the review ran; git pre-push backstop | **ENFORCED at stop-time + push-time** (Stop-block enforcement now VERIFIED, `stop-block-transcript.md` — the row is no longer "pending") | Residual: nothing forces per-edit review mid-turn; killing the session (or refusing twice) abandons the Stop gate — the pre-push gate is then the teeth. Reviewer-model pin PROVISIONAL (OQ3, `claude-opus-4-8`, override `CEO_PAIR_RAIL_REVIEWER_MODEL`). |
| Audit HMAC chain (`audit_log.py` + emit hooks) | PostToolUse `*` per-tool-call append + SessionStart boot + `notify`/wrapper turn-ended backstop | **ENFORCED, completeness-bounded** | Residual: per-tool completeness is best-effort while shell interception is partial — absence of an entry is NOT evidence of absence of activity. `verify_chain()` is untouched and green over what was written. |
| Config protection (`.claude/settings.json`, hook sources) | Edit-time PreToolUse deny ENFORCED + `requirements.toml` MANAGED-hooks option (Decision 5) | **ENFORCED at edit time; ADVISORY between sessions** | Codex has NO ConfigChange event — the continuous tamper tripwire degrades to boot-time-only re-check (SessionStart). Backstop: boot-time hash re-check + CI. |
| Kill-switch protection (`.codex/hooks.json`, `.codex/config.toml`, `.codex/rules/ceo.rules`, `requirements.toml`, operator `AGENTS.md`) | The rail's OWN registration surface entering the PreToolUse deny/canonical matcher + SessionStart boot-hash tripwire | **ENFORCED at edit-time + boot-time-ADVISORY once Wave 3b (SENT-CX-E) lands; ABSENT until then** | Until Wave 3b lands, an agent under Codex can rewrite the kill-switch files and disarm every rail above (the circular-disarm gap, debate A8). Residual after Wave 3b: the boot-tripwire baseline is itself agent-writable (Open-issue #10) — the EDIT-TIME canonical guard is the real protection, the boot re-hash is the backstop, CODEOWNERS/CI at push is the final backstop. See Decision 7. |
| Skills | `.codex/skills/` — same `SKILL.md` + frontmatter format | Available (optional Wave 8) | Not a rail; install-time copy only, zero new skill files in this repo (counts tolerance=0 untouched). |

**ABSENT on Codex 0.139 today** (each carries a substrate-watch WATCH
pointer, Decision 6): total shell-call interception; a ConfigChange
lifecycle event; a SubagentStart that hard-blocks (`continue:false` is
parsed-but-not-enforced upstream behavior). If any promotes upstream, the
matrix row moves ADVISORY/ABSENT → ENFORCED via a one-line change and the
Wave-6 teeth stay as defense-in-depth.

### 2. Adapter parity is strict normalized-input equality, not identical output

`_lib/adapters/codex.py` is a HOST adapter in host mode (parse Codex hook
envelopes, emit `hookSpecificOutput.permissionDecision`) AND the pre-existing
pair-rail reviewer-egress helper (`parse_verdict*`, `make_invoke_command*`,
`parse_usage_from_codex_stdout`) — one module, two documented roles; the
egress helpers are UNTOUCHED by host mode. **Parity** (ADR-025 sense) is
defined as: for a given logical event, the claude and codex adapters produce
STRICTLY EQUAL `NormalizedEvent` on the normalized-input side; the egress
(output) side is per-harness by contract — the codex host `write_decision`
emits the codex wire shape, deliberately NOT the Claude shape. The old
Claude-shaped codex output was the "symbolic parity" era; no production
caller consumed it host-side, so the golden change is intentional and
recorded in the Wave-1 golden update.

### 3. Spawn governance is a two-primitive split, not a single ADVISORY row

The matrix spawn row is the one place where the naive reading ("SubagentStart
is ADVISORY, therefore spawn governance is ADVISORY") is WRONG and must not
propagate into docs. Empirically (`subagentstart-transcript.md`):

- `SubagentStart` `{"continue": false}` is parsed without error and the
  subagent runs to completion — **ADVISORY** for that primitive. This
  transcript is the normative citation; it is on the substrate-watch
  per-bump re-test list.
- The collab spawn is ALSO a `PreToolUse` event with
  `tool_name: "spawn_agent"`; a `permissionDecision: deny` there blocks the
  spawn and NO SubagentStart fires — **ENFORCED** for the collab-tool path.
- `SubagentStart` `additionalContext` injection reaches the subagent and
  dominates its behaviour (verified end-to-end) — the Wave-2 spawn-protocol
  mitigation is real, not cosmetic, but it is a mitigation, never sold as
  enforcement.

Residual named in-claim: only collab-tool spawns are ENFORCED; spawns
smuggled through Bash re-enter the `^Bash$` rail; the Wave-6 chain scan is
the backstop for the SubagentStart advisory path.

### 4. Empirical failure semantics (PLAN-152 C4 mapping) — normative

Recorded live (`failure-semantics-matrix.md`), the harness's default is
**fail-open on everything except an explicit deny**:

| Hook behaviour | codex-cli 0.139 | Class |
|---|---|---|
| exit 0 + `permissionDecision: deny` | tool BLOCKED | ENFORCED deny |
| exit 2 (stderr = reason) | tool BLOCKED | ENFORCED deny (exit-2 alias) |
| timeout (hook killed at deadline) | tool PROCEEDS, no model-visible error | **fail-open** |
| non-zero exit ≠ 2 | tool PROCEEDS | **fail-open** |
| malformed / non-JSON stdout | tool PROCEEDS | **fail-open** |
| well-formed foreign JSON | tool PROCEEDS (unknown fields ignored) | **fail-open** |
| `{}` | tool PROCEEDS (normal allow) | allow |
| Stop + `{"decision":"block"}` | session AUTO-CONTINUES | ENFORCED block |
| SubagentStart + `{"continue":false}` | subagent RUNS ANYWAY | ADVISORY |

Consequences that bind the adapter and every ENFORCED claim:

- The C4 fail-closed-on-INPUT invariant must be implemented INSIDE our hooks
  (parse failure at a security matcher → emit the deny envelope / exit 2),
  never delegated to the harness — the harness would wave it through.
- A hook that dies (timeout/crash) is indistinguishable from a hook that
  allowed. Per-hook `timeout` values in `templates/codex/hooks.json` must be
  generous enough that the guard never self-kills into an allow; the Wave-6
  RED-on-absence breadcrumb assertions are the ONLY detection layer for
  silent hook death. Silence from a fail-open rail is not health (ADR-158).
- Every ENFORCED Codex row therefore carries the standing residual: "hook
  death or de-trust degrades to silent allow; backstops: boot-time arming
  check (Wave 5 A7), RED-on-absence chain assertions (Wave 6), CODEOWNERS/CI
  at push."
- **Kernel garbage-stdin under codex** (Open-issue #4): the repo's edit-class
  matchers fail-CLOSED on unparseable stdin on the CLAUDE wire; under codex
  the legacy-shaped block is foreign JSON → harness fail-open. This is
  C4-consistent (an infrastructure/wire-shape failure, not an input-parse
  bypass of a live matcher), and is recorded here so it is not rediscovered
  as a regression.

### 5. Hermetic test posture — three tiers, honestly labelled (debate A3)

- **T1 — hermetic CI (recorded-wire replay).** The golden suite + the
  subprocess positive/negative/malformed controls replay recorded envelopes;
  NO codex binary runs in CI. This is what every push certifies.
- **T2 — local live smoke, per pinned version.** Gated on
  `shutil.which("codex")` + the pin range; `pytest.mark`-skipped in CI with a
  reason string that names the local runbook (visible, never silent).
- **T3 — release gate.** The step-15 verdict envelope records the fixture-set
  version certified against.

Normative sentence, to appear verbatim in the docs honesty sweep (Wave 7):
**"CI certifies fixture-replay against a recorded wire; only local live-fire certifies the real binary, per pinned version."**

### 6. Fixture↔pin coupling + per-bump re-verification checklist (debate A12)

Fixtures follow the PIN (`.claude/governance/codex-cli-pin.txt`), never
upstream. Every recorded fixture carries `_meta.codex_cli_version`; a unit
test asserts that version ∈ the pin range — a pin bump goes RED until
fixtures are re-recorded or explicitly waived. To record on a newer CLI,
**bump the pin FIRST via the ADR-111 ceremony, then re-record** — the
PLAN-142 substrate-drift class (`codex_invoke.py` vs 0.139 empty-stdout) is
what this coupling exists to prevent, now on a second vendor.

Per-bump re-verification checklist (the substrate-watch alert text points
here; time-box **≤ 2 hours** of local live-fire before the bump is trusted):

1. Re-record the ≥17 input fixtures + normalized expectations from the new
   CLI (`hooks/tests/fixtures/adapters/codex/{in,normalized,out}/`).
2. Re-run the failure-semantics matrix (9 rows) — confirm deny/exit-2 still
   ENFORCED and the fail-open set unchanged.
3. Re-run the Stop-block enforcement probe (`stop-block-transcript.md`
   method) — the inverted pair-rail depends on it.
4. Re-run the SubagentStart `continue:false` non-enforcement probe AND the
   `spawn_agent` PreToolUse-deny probe (the Decision-3 split).
5. Re-confirm the trust-hash keying semantics (Decision 6a below) and the
   `--dangerously-bypass-hook-trust` behaviour.
6. Re-test the **git-worktree hook-discovery gap** (Open-issue #2): 0.139
   silently returns ZERO hooks inside a git worktree (plain repo works) — the
   Wave-5 arming check must detect-and-warn, Wave-7 docs must name it; a bump
   that closes this promotes a residual.
7. Record the `mcp__*` PreToolUse fixture (Open-issue #5, unrecorded in the
   0.139 lab — no MCP server) and raise `_MIN_IN_FIXTURES['codex']`.

#### 6a. What `/hooks` trust does and does NOT attest (debate A6, OQ1 gate)

Empirically pinned (`trust-keying-A6.md`, cross-checked against
`codex-rs/hooks` at tag `rust-v0.139.0` AFTER live observation): **the trust
hash covers ONLY the registration entry, NOT the hook program.** The
`sha256:` `currentHash` is computed over the normalized TOML serialization of
`{event_name, matcher, hooks:[{type, command, timeout, statusMessage}]}` —
the command STRING is inside the hash; the FILE the command executes is not.

- Editing the registered script's body after trust → still fires, no
  re-prompt, `trustStatus` stays `trusted`.
- Editing one byte of the command string in `hooks.json` → `trustStatus:
  modified`, hook silently does NOT fire (no warning anywhere).

Consequence (normative for OQ1 and the installer): `/hooks` trust is consent
to a COMMAND LINE, not to code. For our shim architecture
(`_python-hook.sh <hook>.py`), a framework upgrade that changes only hook
`.py` bodies does NOT re-prompt — the S261 "every upgrade re-prompts"
friction estimate was WRONG for body-only upgrades. Equally, an attacker who
can write the hook `.py` files inherits trusted execution with no re-prompt:
registration-file integrity is codex's to hash; **hook-BODY integrity is
OURS to defend** — precisely the canonical-edit guard over `.claude/hooks/**`
plus the Wave-3b kill-switch/boot-re-hash surface. An untrusted or modified
hook is a SILENT no-op (no execution, no stderr, exit 0) — "installed but
untrusted" is indistinguishable from healthy at runtime, which is the
strongest argument for the Wave-5 post-install arming check and the Wave-6
RED-on-absence assertions.

### 7. KERNEL guard-extension override for the kill-switch surface (debate A8)

The kill-switch surface (`.codex/hooks.json`, `.codex/config.toml`,
`.codex/rules/ceo.rules`, `requirements.toml`, operator `AGENTS.md`) is the
rail's own registration underbelly: an agent that rewrites it disarms every
ENFORCED rail while the tripwire that should detect the change stays silent
(circular disarm). Waves 2/3 EMIT these template files as unguarded L2
files; the TEETH are the separate **L3 Wave 3b (SENT-CX-E)** — extending
`_CANONICAL_GUARDS` in `check_canonical_edit.py` (edit-time deny) AND the
`SessionStart.py` boot-hash tripwire AND the `effective_config.py` disk
census.

`check_canonical_edit.py` and `SessionStart.py` are both in `_KERNEL_PATHS`
(the ADR-116-AMEND-1 kernel-extension-v2 added the SessionStart/adapter/audit
modules). Extending the guard list from within a file that IS the guard list
is therefore a KERNEL-class edit requiring, IN ADDITION to the SENT-CX-E
sentinel, the plan-specific double-gate
**`CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-KILLSWITCH-GUARD-EXTENSION`** +
**`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`**. This slug is recorded here alongside
its precedents — the same double-gate used by
`PLAN-080-PHASE-0B-SCHEMA-GUARD-EXTENSION`,
`PLAN-081-PHASE-2-DISPATCHER-GUARD-EXTENSION`,
`PLAN-081-PHASE-4-BIS-CORPUS-GUARD-EXTENSION`, and
`PLAN-081-PHASE-6-BIS-GOVERNANCE-GUARD-EXTENSION`
(`check_canonical_edit.py:149-152` and the following guard-list blocks;
`check_arbitration_kernel.py:302-304`). The single override covers BOTH
kernel rows of Wave 3b; `effective_config.py` is canonical-guarded
(sentinel-only, no kernel row).

The two other Wave-N kernel-override slugs allocated by PLAN-155 are recorded
for the same audit-trail reason:
**`PLAN-155-CODEX-HOST-ADAPTER`** (Wave 1 — `codex.py` / `adapters/__init__.py`
/ `contract.py` / the four ENFORCED-hook entrypoints, all KERNEL per
`check_arbitration_kernel.py:85,165,168` + the seam-migrated hooks) and
**`PLAN-155-CODEX-AUDIT-ACTIONS`** (Wave 4 — `audit_log.py` /
`_lib/audit_emit.py`, KERNEL per `:200,90`, registering the new per-tool and
turn-ended audit actions).

**Managed-hooks non-disableable claim is CONDITIONAL on placement (A8).**
`requirements.toml` MANAGED hooks are trusted-by-policy and not
user-toggleable — but that "non-disableable" property holds ONLY when the
`requirements.toml` lives at admin/org scope (not agent-writable). Shipped as
an agent-writable project file it is neither managed-in-force nor a teeth
claim; the installer emits it behind an explicit `--managed-hooks` opt-in
(OQ1 consent-first) and the docs state the placement condition wherever the
non-disableable claim appears. Managed posture was NOT live-tested in the
0.139 lab (needs an admin-scope requirements file) — that live-fire is a
Wave-2/Owner follow-up, not an asserted fact.

### 8. Host-adapter emit-shape correctness is proven by the subprocess control, not the unit test (S265 lesson)

The load-bearing lesson from the Wave-1 integration pass: **the adapter unit
test passed while the integration wire was wrong.** The seam-migrated hooks
emitted decisions WITHOUT threading the parsed event to the egress, and the
codex host shape is EXPLICIT-only — so under `CEO_HOOK_ADAPTER=codex` every
decision came out Claude-shaped, which on the codex wire is foreign JSON =
harness fail-open (Decision 4). A green `test_adapter_golden.py` did not
catch it because the unit test called the adapter directly; only the
**subprocess positive-control replaying a recorded envelope on the
byte-identical command line shipped in `templates/codex/hooks.json`**
(`CEO_HOOK_ADAPTER=codex`, stdin = recorded envelope, assert
`permissionDecision: deny`) exercised the real ingress→hook→egress path and
went RED. This is the ADR-158 doctrine specialized to the adapter seam:
**in-process import-and-call replay is insufficient — it would have stayed
green through the S254 dead gate.** The certifying artifact for every
ENFORCED Codex row is the subprocess replay on the shipped command line, plus
one live-fire transcript per critical rail; the unit golden is a complement,
not the certificate. (Proof the control has teeth: blinding the host
adapter's emit path turns the positive-control suite RED;
`live-fire-canonical-deny.md` shows the real 0.139 end-to-end deny.)

### 9. Reviewer-unavailable posture (debate A20, direction-neutral)

If the pair-rail reviewer cannot be reached (binary absent, timeout, empty
verdict), the rail records the attempt as `UNAVAILABLE` and does NOT silently
approve and does NOT block forever: it allows with a loud RED-on-absence
breadcrumb, and the push-time gate + CI remain the backstops. A rail that
blocked indefinitely on a broken reviewer would be a denial-of-service on the
operator; a rail that silently approved would be the S254 dead gate. The
honest middle is: record the gap, allow with noise, backstop downstream.

The same-vendor caveat is direction-neutral: **no single model is both author
and sole reviewer of a canonical edit** — under Claude Code the operator is
Anthropic and the reviewer is OpenAI Codex; under the Codex harness the
direction inverts. This reduces single-model blind spots; it does NOT
eliminate shared-substrate failure modes (a defect both vendors share is
caught by neither seat). The pair-rail buys cross-vendor diversity, not
independence; CODEOWNERS, branch protection, CI, and human review at merge
are the other layers.

## Consequences

- "Runs on Codex" can no longer ship as an unqualified claim: every rail
  carries its ENFORCED/ADVISORY/ABSENT label and residual in-claim, and the
  two honest ADVISORY rails (SubagentStart spawn, continuous config tripwire)
  plus the audit completeness bound are named in the same breath as the
  ENFORCED rails.
- The certifying instrument for a Codex rail is the subprocess replay on the
  shipped command line (Decision 8), not the existence of a config file or a
  green unit golden — the S254 class stays closed on the new harness.
- The kill-switch surface is guarded ONLY after Wave 3b lands under
  `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-KILLSWITCH-GUARD-EXTENSION` + ACK; until
  then the matrix row reads ABSENT and CODEOWNERS/branch-protection is the
  only backstop. The Wave-3b matrix-reconciliation edit to this record lands
  in the SENT-CX-E batch.
- Codex substrate drift is now a tracked risk on a second vendor: the pin
  binds the fixtures, the ≤2h per-bump checklist (Decision 6) is the runbook,
  and the substrate-watch item owns the alert. A CLI bump without fixture
  re-record is a RED build by construction.
- Three residuals are on the permanent record, not hidden: apply_patch
  Update-hunk content is path-gated but not content-gated (#3); the git
  worktree hook-discovery gap makes hooks silently absent inside a worktree
  (#2); kernel garbage-stdin under codex degrades to harness fail-open (#4).

## Alternatives considered

- **A single "Codex: supported" claim.** Rejected — the whole record exists
  because the surface similarity to Claude Code is partial, and an
  unqualified claim reads as "same guarantees" precisely where they differ.
- **Certifying rails by config-file presence / unit golden.** Rejected — the
  S265 integration pass is the existence proof that a green unit golden
  coexisted with a dead wire; only the subprocess replay on the shipped
  command line certifies (Decision 8), mirroring ADR-158.
- **Treating the spawn row as uniformly ADVISORY.** Rejected — it understates
  the ENFORCED `spawn_agent` PreToolUse deny and would leave the collab-spawn
  path documented as weaker than it is (Decision 3).
- **Delegating fail-closed-on-input to the harness.** Rejected — the harness
  fail-opens on timeout/crash/malformed/foreign (Decision 4); the C4
  invariant must live inside our hooks or it does not exist under Codex.
- **Shipping `requirements.toml` managed hooks by default.** Rejected — the
  non-disableable property is conditional on admin-scope placement (Decision
  7); a default agent-writable managed file is neither teeth nor consent-first.
- **Blocking forever on an unavailable reviewer.** Rejected — that is a
  denial-of-service; the honest posture is record-the-gap + allow-with-noise
  + downstream backstop (Decision 9).
- **Recording fixtures from the latest upstream CLI.** Rejected — fixtures
  follow the pin; recording ahead of the pin re-opens the PLAN-142 drift
  class. Bump the pin via ADR-111 first, then re-record (Decision 6).
