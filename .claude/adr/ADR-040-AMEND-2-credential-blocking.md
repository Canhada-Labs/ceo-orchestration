---
id: ADR-040-AMEND-2
title: ADR-040 §4 amendment — credential blocking at max-age (emit-only → blocking enforcement)
status: ACCEPTED
accepted_at: 2026-05-12
accepted_by: "Owner (post-Codex-Pair-Rail-iter-5-ACCEPT 2026-05-12; threads 019e1d07..019e1d22)"
amendment_of: ADR-040 (Live Adapter Activation Contract — original 2026-04-14)
amends_section: §4 Credential lifecycle (specifically the 90-day max-age "does not block" clause)
proposed_at: 2026-05-12
proposed_by: CEO (PLAN-085 Wave 0; PLAN-084 F-A-SEC-0011-142cbfe2 driver)
veto_floor: ADR-052 (security-engineer + identity-trust-architect VETO)
codex_pair_rail: required (ADR-107 — credential-handling change is veto-floor)
related_plans: [PLAN-012, PLAN-085]
related_adrs: [ADR-040, ADR-052, ADR-107, ADR-108, ADR-115, ADR-116]
supersedes: []
amends:
  - target: ADR-040 §4 (Credential lifecycle)
    original_clause: "At 90 days the event still fires but the adapter does not block — rotation is an operator workflow."
    amended_clause: "At credential_max_age_days (90 by default) the adapter raises CredentialExpired and blocks the invocation. Emergency override via CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE=<ticket-id> grants a 24h window."
tags: [governance, credential-lifecycle, blocking-enforcement, amendment, anti-churn]
authorization: PLAN-085 Wave 0 atomic ceremony (`OWNER-CEREMONY-PLAN-085-WAVE-0.sh`); PLAN-085 Wave C.2 implementation (gated by this AMEND-2 ACCEPTED)
target_telemetry_window_days: 90
revert_trigger_false_positive_rate: 0.05
---

# ADR-040-AMEND-2 — Credential blocking at max-age (amendment to ADR-040 §4)

## §1. Status

PROPOSED at draft time (PLAN-085 Wave 0). Flips to ACCEPTED at the
atomic Wave 0 ceremony commit, gated by:

1. Dedicated Codex MCP Pair-Rail review per ADR-107 (credential-handling
   change is veto-floor; verdict must be ACCEPT before ceremony script
   flips status).
2. ADR-052 security-engineer + identity-trust-architect VETO consensus
   on the emergency-override design.

Wave C.2 implementation lands AFTER this AMEND-2 is ACCEPTED, per the
AC10 gate (`grep '^status:' ADR-040-AMEND-2 returns accepted` before
commit-SHA of C.2 lands).

## §2. Context

**Driver finding:** PLAN-084 audit emitted F-A-SEC-0011-142cbfe2 +
IDA-P0-02 (veto case B — auth/crypto). Both findings observed that
ADR-040 §4 — Credential lifecycle — declares the 75-day "warn" event
and the 90-day "max-age" event as **emit-only advisories**:

> ADR-040 §4 (verbatim, 2026-04-14):
> "**Age:** 90-day hard maximum. `credential_rotation_due` audit event
> fires on every call once the key is >75 days old (per
> `docs/rotation-log.md`). At 90 days the event still fires but the
> adapter does not block — rotation is an operator workflow."

PLAN-084 audit observed that **in production**, the rotation event has
fired 0 times in the 35-day window between v1.16.0 GA and v1.18.0 GA
despite the Owner's keys exceeding 75 days. Root cause: `_policy.py`
declares `credential_warn_age_days` and `credential_max_age_days`
fields but `claude.py` invoke path NEVER reads them — the gate is
**declared but not wired** (PLAN-084 §B.7 "declared but not wired"
meta-pattern). ADR-040 §4 is "fail open" by intent (operator workflow,
not enforcement); but with zero downstream observability, the
operator workflow itself never triggers.

PLAN-085 Wave C.2 originally proposed extending the emit-only gate to
**blocking enforcement at `invoke()` runtime path**: read credential
creation date from a side-channel (e.g., env var `<KEY>_CREATED_AT` or
`docs/rotation-log.md` parser), compare to `credential_max_age_days`,
raise `CredentialExpired` exception and DENY the call if exceeded.

This proposal **CONTRADICTS ADR-040 §4** as originally written (the
adapter "does not block"). Per anti-churn doctrine (ADR-115
maintenance-mode), CONTRADICTING an ACCEPTED ADR requires an explicit
amendment, NOT silent override in PLAN-085 §4.

ADR-040-AMEND-2 is that amendment. PLAN-085 declared it in its
`adrs_proposed` frontmatter (4th entry) and ships it through the same
atomic Wave 0 ceremony as ADR-116/117/120.

## §3. Decision drivers

- **Production posture (anti-emit-only):** PLAN-084 evidence shows
  emit-only advisory fails when downstream observability gap exists.
  Blocking enforcement is the **mechanical floor** that closes the gap.
- **Anti-churn (ADR-115):** the original ADR-040 §4 emit-only design
  was deliberate (operator workflow). Changing to blocking is a
  semantic shift that requires explicit amendment, NOT a unilateral
  callsite change.
- **Reversibility:** the amendment includes an **explicit revert
  path** (§5 below) — if v1.19.0+ telemetry shows >5% false-positive
  rate (operator legitimately needs to use a >90-day key for a
  recovery scenario), the framework reverts to emit-only without a
  new ADR.
- **Operator escape hatch:** the emergency-override env var
  (`CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE=<ticket-id>`) preserves
  operator ability to invoke during incident response (with audit
  trail).
- **VETO-floor mandate (ADR-052):** credential lifecycle changes are
  identity-trust-architect VETO; this amendment cannot proceed
  without explicit Pair-Rail Codex ACCEPT per ADR-107.

## §4. Decision (the amendment)

Replace ADR-040 §4 Age clause as follows. PLAN-085 Wave C.2
implementation commits BOTH this AMEND-2 file AND a direct edit to
`.claude/adr/ADR-040-live-adapter-activation-contract.md` §4 (the
ADR-040 file edit is the canonical-content update; THIS file is the
amendment-decision record).

### §4-amended (effective at v1.19.0)

> **Age:** 90-day hard maximum. `credential_rotation_due` audit event
> fires on every call once the key is >`credential_warn_age_days`
> (default 75) days old (per `docs/rotation-log.md`). At
> `credential_max_age_days` (default 90) **the adapter emits
> `credential_blocked_due_to_age` and raises `CredentialExpired` —
> the invocation is DENIED**. Emergency override:
> `CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE=<ticket-id>` env var
> grants a 24h emergency window (audit emits
> `credential_emergency_override_used` with ticket-id payload; CI
> rejects non-empty value at lint to prevent persistent override).

### §4-amended additions

1. **Enforcement point:** the runtime adapter `invoke()` path (NOT
   module-import time). Module-import is too early (CI imports
   modules without intent to invoke; would generate
   `credential_rotation_due` noise on every `pytest` run). The
   enforcement is gated by `CEO_LIVE_<PROVIDER>=1` env var being
   set, which is the explicit operator activation gate per ADR-040
   §6.
2. **Credential creation date source:** PLAN-085 Wave C.2 reads from
   `docs/rotation-log.md` parser. If the rotation log is absent or
   malformed, fail-CLOSED (DENY with
   `reason: rotation_log_unreadable`).
3. **Emergency override semantics:**
   - **Override-source provenance (Codex Pair-Rail iter-1 P1 + iter-2
     mechanism fix — threads `019e1d0b` + `019e1d13`):** the env var
     `CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE` MUST be read ONLY from
     a **session-start trusted snapshot** of `os.environ`, captured
     at framework initialisation time BEFORE any untrusted code path
     (spawn-payload construction, hook subprocess, prompt content,
     workflow env block) can influence process environment. Reading
     live `os.environ` at adapter `invoke()` entry is **NOT
     sufficient** — a child process launched with the override in its
     initial environment is indistinguishable from a real parent-shell
     export at module-import time.

     **Enforcement points (concrete, multi-layer per Codex iter-2):**

     - **Layer 1 — Trusted session-start snapshot.** New module
       `.claude/hooks/_lib/trusted_env.py` (PLAN-085 Wave C.2
       deliverable; in kernel per ADR-116 entry candidate). On
       framework import (first hook firing in the session), capture
       `_TRUSTED_ENV_SNAPSHOT = dict(os.environ)`. This snapshot is
       the SOLE source of `CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE`
       for adapter override checks. Live `os.environ` is NOT
       consulted post-snapshot for this variable.
     - **Layer 2 — Spawn-payload sanitisation.**
       `.claude/hooks/check_agent_spawn.py` MUST strip
       `CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE` from any spawn-payload
       `env:` field before allowing the spawn. If the var is present
       in the payload, emit `agent_spawn_override_var_stripped` audit
       event (advisory; not blocking, since the strip itself defeats
       the bypass — but trace for forensics).
     - **Layer 3 — Hook subprocess sanitisation.** Any framework hook
       or script that spawns a subprocess (via `subprocess.run`,
       `subprocess.Popen`, etc.) MUST pass `env=` parameter constructed
       as `{k: v for k, v in os.environ.items() if k !=
       'CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE'}` to prevent
       inheritance. PLAN-085 Wave F (test plan addendum) adds a
       parametrized test `test_no_subprocess_inherits_override_env.py`
       that greps the framework for `subprocess.{run,Popen,call}`
       calls and asserts the env-sanitisation pattern.
     - **Layer 4 — CI workflow lint.** `.github/workflows/validate.yml`
       greps all `.github/workflows/*.yml` files for the env-var name
       in any `env:` block and FAILS the CI run if present (operator
       intervention only; not automated). This is per the threat
       model: even an attacker who controls a workflow PR cannot
       set this override via workflow `env:`.

     The framework-level invariant: **only a parent shell that started
     the Claude Code process can grant emergency override**.
     Layers 2-4 are MANDATORY prevention against pre-launch
     child-env injection (an attacker who controls a spawn payload,
     workflow `env:`, or subprocess launch context can inject the
     override env var into the child process's INITIAL environment
     BEFORE any framework code runs — Layer 1 cannot
     differentiate this from a real parent-shell export at
     module-import time, since both are present in `os.environ`
     when Python starts). Layer 1 protects ONLY against post-init
     mutation (e.g., `os.environ[var] = ...` set by Python code or
     a tool subprocess that runs AFTER the framework has booted)
     and serves as defense-in-depth, NOT as a substitute for
     Layers 2-4. The trust boundary is therefore enforced
     **before process launch** at Layers 2-4, with Layer 1 closing
     the residual post-init mutation surface.
   - Env var value MUST be a non-empty ticket-id matching regex
     `^[A-Z][A-Z0-9]*-\d+$` (e.g., `INC-1234`, `SEV1-42`).
     <!-- PLAN-117 WS-A (S176) typo-correction: the original regex
     `^[A-Z]+-\d+$` rejected this section's own `SEV1-42` example (the `1`
     in the prefix is a digit). Broadened to a letter-led alphanumeric prefix
     so code == ADR == both cited examples. Internal-contradiction fix, NOT a
     semantic amendment — intent (a structured incident-ticket reference) is
     unchanged. Implemented at `_lib/adapters/live/claude.py::_OVERRIDE_TICKET_RE`. -->
   - Empty / unset / malformed value → fail-CLOSED (DENY).
   - On accept, emit `credential_emergency_override_used` with
     `ticket_id` in payload (Sec MF-3 whitelisted field).
   - Override window: 24h from first use. After 24h, override
     re-fails until env var is re-set (forces operator to
     re-acknowledge).
   - CI lint (`.github/workflows/validate.yml`) rejects any commit
     that sets this env var in a workflow file (operator intervention
     only; not automated).
   - **Tests required — 6 cases total (PLAN-085 Wave C.2 + Wave F
     test plan addition; covers Layers 1-4):**
     - **Layer 1 (snapshot):**
       `test_trusted_env_snapshot.py::test_snapshot_captured_at_init`
       (verify `_TRUSTED_ENV_SNAPSHOT` is populated before any
       hook fires).
       `test_trusted_env_snapshot.py::test_parent_shell_env_in_snapshot_allows`
       (env-var present in parent-shell-supplied env at framework
       start → snapshot captures it → adapter allows valid ticket).
       `test_trusted_env_snapshot.py::test_late_set_env_not_in_snapshot_rejected`
       (env-var set via `os.environ[var]=...` AFTER framework init
       → not in snapshot → adapter rejects with
       `credential_override_late_set_ignored`).
     - **Layer 2 (spawn-payload sanitisation):**
       `test_check_agent_spawn_strips_override_env.py::test_payload_env_var_stripped`
       (spawn payload with `env: {CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE: INC-1234}`
       → strip + emit `agent_spawn_override_var_stripped` + spawn proceeds
       WITHOUT the var in child env).
     - **Layer 3 (subprocess sanitisation):**
       `test_no_subprocess_inherits_override_env.py::test_framework_subprocess_calls_strip_env`
       (parametrised grep of all `subprocess.{run,Popen,call}` calls
       in `.claude/hooks/` + `.claude/scripts/` — assert each
       constructs `env=` with the var excluded).
     - **Layer 4 (CI workflow lint):**
       `test_workflow_env_block_rejected_at_lint.py::test_workflow_yaml_grep_rejects_override_var`
       (mock `.github/workflows/test.yml` with `env: {CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE: INC-1234}`
       → lint script `check-workflow-override-env.py` exits non-zero).
4. **Audit events emitted (new — register via PLAN-085 Wave D
   `_KNOWN_ACTIONS` extension; whitelisted fields per Sec MF-3):**
   - `credential_blocked_due_to_age` — DENY path; fields: `provider`,
     `age_days`, `max_age_days`.
   - `credential_emergency_override_used` — override-ACCEPT path;
     fields: `provider`, `ticket_id`, `age_days`,
     `override_remaining_hours`.
   - `credential_override_late_set_ignored` — Layer 1 forensic event;
     fields: `provider`, `attempted_var_name`, `provenance_hint`
     (e.g., `late_os_environ_set` | `spawn_payload_env` |
     `subprocess_inherited`).
   - `agent_spawn_override_var_stripped` — Layer 2 spawn-payload
     sanitisation event; fields: `agent_name`, `stripped_var_name`,
     `caller`.

## §5. Revert path (explicit per R2 iter-1 C4 requirement)

This amendment is **conditionally reversible**. If post-v1.19.0
telemetry shows that the blocking enforcement causes operational
friction exceeding tolerable threshold, the framework reverts to
emit-only WITHOUT a new ADR (this AMEND-2 itself authorises the
revert).

### Revert triggers (any one)

1. **False-positive rate >5% over 90-day window.** Defined as: the
   ratio of `credential_blocked_due_to_age` audit events that are
   followed by `credential_emergency_override_used` (with valid
   ticket-id) within the same 24h window. If this ratio exceeds 5%
   over a rolling 90-day window, revert.
2. **Single critical-severity incident** where blocking the
   credential prevented operator from accessing the framework during
   active P0 production incident response (manual operator declaration
   in `docs/rotation-log.md`).
3. **Owner explicit revert directive** (audit-trail captured in
   `docs/rotation-log.md` with reason).

### Revert mechanic

- Edit `_policy.py`: set `credential_max_age_days_enforce: bool = False`
  (NEW field; default `True` per this amendment; `False` reverts to
  emit-only).
- Edit ADR-040 §4 back to original wording.
- Update this AMEND-2 status to `SUPERSEDED-BY-REVERT`; add
  `reverted_at` + `reverted_by_reason` fields.
- Single GPG-signed Owner commit; no new ADR needed.

### Re-amendment path

If post-revert evidence emerges that emit-only is again the wrong
posture, a NEW amendment ADR (e.g., ADR-040-AMEND-3) must be drafted
through the standard ADR ceremony (NOT a re-flip of this AMEND-2). This
preserves the audit trail of decision oscillation.

## §6. Consequences

**Positive:**

- F-A-SEC-0011-142cbfe2 closed at the mechanical floor (credential
  rotation enforced by adapter, not by operator vigilance alone).
- "Declared but not wired" meta-pattern (PLAN-084 §B.7) eliminated for
  the credential-lifecycle gate.
- Emergency-override env var preserves operator ability to invoke
  during incident response (with audit trail).
- Revert path §5 prevents this amendment from becoming irreversible —
  if blocking causes operational friction, revert without new ADR.
- Audit events `credential_blocked_due_to_age` +
  `credential_emergency_override_used` create observable telemetry
  for the rotation-discipline workflow (which today fires 0 times).

**Negative:**

- Operators with >90-day keys see DENY on next invocation; requires
  immediate rotation (or emergency-override env var with ticket-id).
  Mitigation: 75-day warn event already fires for 15 days before
  block; operator has runway.
- `docs/rotation-log.md` becomes a runtime-readable file (was
  documentation-only). Mitigation: parser is fail-CLOSED; absent log
  = DENY (with `reason: rotation_log_unreadable`).
- Adds a new fail-open vector if the rotation-log parser has a
  parse bug. Mitigation: 6 unit tests in `test_credential_rotation_emit.py`
  cover parse-failure scenarios (PLAN-085 §4 Wave C.2 test plan).
- CI cost: lint check on `.github/workflows/` for emergency-override
  env var. Trivial overhead.

**Neutral:**

- Original ADR-040 §4 "fail-open by intent" doctrine is preserved
  for the **75-day warn** event (advisory). Only the **90-day max**
  is upgraded to blocking. The 75-day warn → 90-day block window is
  unchanged in shape; only the terminal action changes.

## §7. Authorization

ADR-040-AMEND-2 is a doctrine ADR (documentation-only); the runtime
artifact (Wave C.2 implementation) is the canonical enforcement
moment. Acceptance ceremony is the PLAN-085 Wave 0 atomic commit
signed by Owner GPG.

This amendment does NOT require `CEO_KERNEL_OVERRIDE` (the amended
ADR-040 file is NOT in `_KERNEL_PATHS`; only the kernel-tier modules
in ADR-116 are). However, PLAN-085 Wave C.2's edit to ADR-040 itself
(updating §4 to reflect this amendment) IS a canonical-guard path —
sentinel-signed via the standard `approved.md` + `.asc` pattern per
`feedback_sentinel_signing_discipline.md`.

## §8. Related work

- ADR-040 — Live Adapter Activation Contract (original, 2026-04-14).
  This amendment narrows §4 90-day max-age clause from emit-only to
  blocking + emergency-override.
- ADR-052 — VETO floor archetypes (identity-trust-architect VETO
  authority on this amendment).
- ADR-093 — canonical-guard moratorium retract + kernel-override
  discipline (precedent for explicit-revert-path requirement in
  amendments).
- ADR-107 — Codex MCP Pair-Rail asymmetric VETO matrix (this
  amendment's review subject to ACCEPT verdict).
- ADR-108 — Codex Pair-Rail dispatcher protocol.
- ADR-115 — post-SOTA maintenance-mode doctrine (anti-churn:
  ACCEPTED ADRs require explicit amendment to override, not silent
  callsite change).
- ADR-116 — KERNEL HARD-DENY tier-0 extension (concurrent Wave 0 ADR
  for the catastrophic-bypass-chain closure).
- PLAN-084 F-A-SEC-0011-142cbfe2 — driver finding (declared but not
  wired).
- PLAN-084 IDA-P0-02 — identity-trust-architect P0 finding.
- PLAN-084 §B.7 — "declared but not wired" meta-pattern.
- PLAN-085 Wave C.2 — implementation (gated by this amendment ACCEPTED).
- PLAN-085 Wave D — audit-emit registration of 4 new events
  (`credential_blocked_due_to_age` +
  `credential_emergency_override_used` +
  `credential_override_late_set_ignored` (Layer 1) +
  `agent_spawn_override_var_stripped` (Layer 2)).
- `_lib/adapters/live/_policy.py:104-108` — declares
  `credential_warn_age_days` + `credential_max_age_days`; Wave C.2
  wires read+enforce at invoke path.
- `_lib/adapters/live/claude.py:83-93` — Wave C.2 enforcement point.
- `docs/rotation-log.md` — credential creation-date source-of-truth.

## §9. Enforcement commit

This amendment ADR is documentation-only. The runtime enforcement
artifact (the wiring of `credential_max_age_days` blocking + emergency
override) ships at the PLAN-085 Wave C.2 ceremony commit. The ADR-040
§4 text update (the actual wording change in the original ADR-040 file)
ships in the SAME Wave C.2 commit. Both SHAs recorded in PLAN-085
progress log §11.
