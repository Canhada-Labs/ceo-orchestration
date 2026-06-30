---
id: ADR-116
title: KERNEL HARD-DENY tier-0 scope extension — 13 entries closing single-edit catastrophic bypass chain + ADR-040-AMEND-2 trust root
status: ACCEPTED
accepted_at: 2026-05-12
accepted_by: "Owner (post-Codex-Pair-Rail-iter-5-ACCEPT 2026-05-12; threads 019e1d07..019e1d22)"
proposed_at: 2026-05-12
proposed_by: CEO (PLAN-085 Wave 0; PLAN-084 F-C2-002 + F-C2-008 driver)
veto_floor: ADR-052 (security-engineer + identity-trust-architect VETO; threat-detection-engineer co-signer)
codex_pair_rail: required (ADR-107 — kernel-scope expansion is veto-floor decision)
related_plans: [PLAN-080, PLAN-082, PLAN-084, PLAN-085, PLAN-089]
related_adrs: [ADR-052, ADR-080, ADR-081, ADR-093, ADR-107, ADR-108, ADR-111, ADR-113, ADR-114]
supersedes: []
tags: [governance, kernel, hard-deny, canonical-guard, defense-in-depth, performance-ceiling]
authorization: PLAN-085 Wave 0 atomic ceremony (`OWNER-CEREMONY-PLAN-085-WAVE-0.sh`) + Wave E.2 implementation (gated by this ADR ACCEPTED)
performance_ceiling_p99_ms: 2
microbench_target: .claude/scripts/tests/perf/test_kernel_hard_deny_microbench.py
---

# ADR-116 — KERNEL HARD-DENY tier-0 scope extension

## §1. Status

PROPOSED at draft time (PLAN-085 Wave 0). Flips to ACCEPTED at the
atomic Wave 0 ceremony commit, gated by:

1. Dedicated Codex MCP Pair-Rail review per ADR-107 (kernel scope
   expansion is veto-floor decision; verdict must be ACCEPT before
   ceremony script flips status).
2. ADR-052 archetypes (security-engineer + identity-trust-architect
   VETO floor; threat-detection-engineer co-signer) consensus on the
   13-entry scope.
3. Microbench artifact landed AT or BEFORE ceremony commit (perf
   ceiling §6 verified empirically — fail-CLOSED if absent).

Wave E.2 implementation lands AFTER this ADR is ACCEPTED, per the AC10
gate (`grep '^status:' ADR-116 returns accepted` before commit-SHA of
E.2 lands). PLAN-085 Wave B blocks Wave E independently (B.1 rename +
B.3 two-writer fix must land first), so the gate is double-locked.

## §2. Context

PLAN-084 SOTA-finalization audit (S107-cont 2026-05-12, shipped tag
v1.18.0) emitted findings F-C2-002 and F-C2-008 in the Wave C subsystem
deep-dive of the canonical-edit + arbitration-kernel surface. The
findings, both **veto case D** (defense-in-depth integrity), document
a **single-edit catastrophic bypass chain**: an agent that obtains
write capability to certain non-kernel paths can compromise the
sentinel/canonical-guard pipeline in one move.

The chain has **four observed attack vectors** documented in PLAN-084
Wave C.2 §1-§4:

1. **Sentinel discovery starvation** — `_find_sentinels()` (in
   `check_canonical_edit.py`) only globs `round-*/approved.md` and
   `wave-*/approved.md`. An edit to any module that the discovery
   reads — e.g., the hook itself if writable, or `_python-hook.sh`
   that pre-empts the Python interpreter — bypasses discovery silently.
2. **Secret-pattern + injection-pattern erosion** — `_lib/secret_patterns.py`
   and `_lib/injection_patterns.py` are CRITICAL leak-detection
   primitives. An attacker editing either to short-circuit pattern
   matching defeats the leak scrub at both adapter and audit
   boundaries (ADR-040 §4 + ADR-035 OTEL precedent).
3. **HMAC chain integrity** — `_lib/audit_hmac.py` computes
   per-event HMACs that anchor the audit-log tamper-evidence chain.
   An edit to the HMAC seed loading path silently neutralises the
   chain. `_lib/output_scan.py` similarly scrubs egress text for OWASP
   patterns + NFKC normalisation; defeating it admits homoglyph
   injection.
4. **Pair-Rail dispatcher subversion** — `.claude/dispatcher/` is the
   entire Codex MCP cross-LLM enforcement surface (ADR-107/108). An
   edit to ANY dispatcher module disables the asymmetric VETO matrix.
   `_lib/codex_egress_redact.py` is the canonical egress scrubber
   per ADR-114; without it, raw prompt content can exfiltrate to the
   second LLM.

Additional attack surfaces:

- **`.claude/settings.json`** — hook configuration. An edit can disable
  any hook from the matcher list (set `hooks.PreToolUse[].matcher` to
  empty) without touching the hook file itself.
- **`.github/workflows/release.yml` + `validate.yml`** — CI gates that
  back branch protection. An edit could remove `pytest` or
  `validate-governance.sh` steps; the merged result would falsely
  appear ACCEPTED in CI history.
- **`.claude/sentinel-signers.txt`** — the allowlist of GPG keys that
  can sign Owner sentinels. An edit (adding the attacker's own
  public key) makes attacker-signed sentinels accepted by
  `check_canonical_edit.py`'s `gpg_verify`.

These 11 file paths (plus the dispatcher glob) constitute the **TIER-0
SUBSET strictly required** to close the F-C2-008 single-edit chain.
The remaining 22 paths in PLAN-084 R-026's full 33-file kernel sweep
are DEFERRED to PLAN-089 (kernel-hardening sweep) per the
evolution-roadmap; their inclusion would expand scope past the
catastrophic-bypass-closure mandate and would need a separate ADR.

The pre-existing `_KERNEL_PATHS` (in `check_arbitration_kernel.py:76-107`)
covers 14 entries today:

```
.claude/hooks/check_agent_spawn.py
.claude/hooks/check_canonical_edit.py
.claude/hooks/check_plan_edit.py
.claude/hooks/check_arbitration_kernel.py
.claude/hooks/check_skill_patch_sentinel.py
.claude/hooks/_lib/contract.py
.claude/hooks/_lib/policy.py
.claude/hooks/_lib/policy_preprocessors.py
.claude/hooks/_lib/redact.py
.claude/hooks/_lib/pii_patterns.py
.claude/hooks/_lib/audit_emit.py
.claude/hooks/_lib/adapters/claude.py
.claude/policies/*.yaml | .yml | fixtures/*.jsonl  (3 globs)
.claude/hooks/policy_dispatch.py
.claude/agents/*.md
```

This ADR extends the list with **13 NEW entries** (12 explicit + 1
dispatcher glob), bringing the total to 27 entries (+ 22 deferred to
PLAN-089). Entry #13 (`.claude/hooks/_lib/trusted_env.py`) is added
as the trust-root for ADR-040-AMEND-2 Layer 1 emergency-override
snapshot per Codex Pair-Rail iter-3 cross-ADR consistency requirement
(thread `019e1d18`).

## §3. Decision drivers

- **Catastrophic-bypass closure (primary):** every entry in the
  extension is justified by ≥1 of the four attack vectors §2 (1)-(4).
  Without coverage, the single-edit chain remains exploitable.
- **VETO-floor mandate (ADR-052):** kernel scope changes are
  security-engineer + identity-trust-architect VETO; this ADR cannot
  proceed without explicit Pair-Rail Codex ACCEPT per ADR-107.
- **Performance ceiling (Perf-1):** kernel HARD-DENY runs on every
  PreToolUse Edit/Write/MultiEdit event; the additional path-match
  surface must NOT regress hook latency past +2ms p99.
- **Anti-churn (ADR-115 maintenance-mode):** the 22 deferred files
  from R-026 are EXPLICITLY out of scope; PLAN-089 will revisit. No
  scope creep within ADR-116.
- **Reversibility:** kernel scope reductions are HIGH-reversibility
  (delete the line, restart hook); kernel scope expansions are LOW
  (any access-pattern that depends on the path becomes blocked
  retroactively). Each entry MUST cite specific attack-vector
  justification (decision criteria §5).

## §4. Options considered

### Option A — Full 33-file R-026 sweep in ADR-116 (rejected)

Adopt every path identified by PLAN-084 R-026 as kernel-tier — all 33.

**Pros:** single sweep eliminates the kernel-coverage backlog.

**Cons:** the perf-ceiling p99 budget would be exceeded by the
additional path-match patterns (Perf-1 microbench projected from
PLAN-084 §B.6 = +3-5ms incremental on the 33-file scan). Many of
the 22 deferred paths are NOT attack-vector-justified per the
F-C2-008 chain analysis — they're hardening for hypothetical chains
not yet observed. Violates anti-churn doctrine. **REJECTED**.

### Option B — TIER-0 SUBSET strictly required to close F-C2-008 (CHOSEN)

Adopt the 13 entries that DIRECTLY close one or more of the four
documented attack vectors from F-C2-008. Defer the remaining 22 to
PLAN-089 with explicit non-criterion-match rationale in §7.

**Pros:** scope minimised to bypass-closure mandate; perf ceiling
respected (microbench-verified +1-2ms p99 incremental); each entry
mechanically justifiable; deferred items get their own ADR in
PLAN-089 with proper debate.

**Cons:** future audits may identify NEW attack vectors that require
additional kernel-tier paths; each such expansion requires a NEW ADR
(this is the intended cost — kernel scope changes are veto-floor and
must be deliberate).

### Option C — Defer entire kernel extension to PLAN-089 (rejected)

Ship PLAN-085 without kernel extension; close F-C2-008 via
defense-in-depth at the Bash matcher (E.3 + E.4) only.

**Pros:** zero kernel-scope change in PLAN-085.

**Cons:** F-C2-008's veto case D requires defense-in-depth, not
defense-instead-of. Bash matcher catches Bash-mediated edits but
NOT Edit/Write/MultiEdit tool-call edits. The single-edit chain remains
exploitable through tool-call paths. **REJECTED**.

### Option D — Move kernel HARD-DENY enforcement out of `check_arbitration_kernel.py` into a separate hook (rejected)

Refactor: extract HARD-DENY into `check_kernel_hard_deny.py` decoupled
from the arbitration kernel.

**Pros:** cleaner separation of concerns (HARD-DENY is a special-case
of canonical-guard; arbitration kernel is a different abstraction).

**Cons:** L3+ refactor with unclear benefit; introduces a new hook to
the PreToolUse matcher chain with its own latency surface; doubles the
test/deploy surface. **REJECTED** as out-of-scope for v1.19.0.

## §5. Decision

**Adopt Option B** — extend `_KERNEL_PATHS` with 13 new entries
covering the TIER-0 SUBSET strictly required to close F-C2-008.

### Decision criteria (per R1 Sec-7 requirement)

The list is **mechanically applicable**: any future kernel expansion
ADR must justify each entry against the 5 criteria below. Entries that
fail to meet the threshold are MOVED to PLAN-089 deferred bucket per
§7 with explicit non-criterion-match rationale.

**Inclusion threshold:** each entry MUST satisfy **≥2 of the 5
criteria, AND at least ONE of {C2, C4, C5}** (the
"security-floor" criteria — cryptographic invariant, audit/CI integrity
floor, or cross-LLM trust boundary). A path that only satisfies the
operational-property criteria (C1 + C3) without a security-floor link
is NOT a kernel-tier candidate; it's a hardening candidate (PLAN-089
scope).

1. **C1 — Consulted on every hook-fired event.** The module is read
   (imported or invoked) by ≥1 of the 5 PreToolUse hooks
   (`check_agent_spawn`, `check_canonical_edit`, `check_plan_edit`,
   `check_arbitration_kernel`, `check_bash_safety`) OR by ≥1 of the
   PostToolUse hooks (`audit_log`) OR by `.github/workflows/` on every
   governance-relevant tool call / push event.
2. **C2 — Enforces a cryptographic invariant.** The module computes,
   verifies, or stores cryptographic state (HMAC, GPG signature
   verification, nonce, replay window) whose silent neutralisation
   would break audit-tamper-evidence or sentinel-trust assumptions.
3. **C3 — Referenced by ≥2 other kernel modules.** The module is
   imported (Python `import` statement OR Bash `source` invocation,
   OR consulted by ≥2 entries in `_KERNEL_PATHS` at runtime — including
   shim layers and config files) by ≥2 other kernel-tier modules. This
   captures the "load-bearing dependency" property: even if the module
   itself doesn't appear on a hook's hot path, mutating it cascades.
4. **C4 — Controls audit/log/CI integrity floor.** The module
   determines whether an action is observed (audit emit), retained
   (CI history), or scrubbed (egress redact). Silent neutralisation
   defeats the **ability to detect** the attack post-hoc, even if the
   attack itself is blocked by other defenses.
5. **C5 — Controls cross-LLM trust boundary.** The module is part of
   the Pair-Rail dispatcher surface (ADR-107/108) or its egress-redact
   primitive (ADR-114). Silent neutralisation invalidates Codex MCP
   verdict trustworthiness for the current session.

Below: each new entry tagged with the criteria it satisfies plus a
one-line justification for each criterion.

### Entry list (13 new entries — TIER-0 SUBSET)

| # | Path | Criteria met | Justification (per criterion) | Attack vector closed |
|---|---|---|---|---|
| 1 | `.claude/settings.json` | C1, C3, C4 | C1: read by Claude Code on every tool call (hooks matcher resolution). C3: referenced by every hook (matcher block determines invocation). C4: matcher mutation disables audit_log PostToolUse → no observability. | Hook deactivation via matcher edit |
| 2 | `.claude/hooks/_python-hook.sh` | C1, C3, C4 | C1: invoked by every hook (Python version shim). C3: referenced by all 5 PreToolUse + 1 PostToolUse hook entries in settings.json. C4: shim mutation replaces the interpreter → audit emits suppressed (no events fire). | Interpreter pre-emption (shim layer) |
| 3 | `.claude/hooks/_lib/gpg_verify.py` | C2, C3, C4 | C2: GPG signature verification primitive. C3: imported by `check_canonical_edit.py` + `check_skill_patch_sentinel.py` (both in kernel). C4: signature-trust gate defeating it admits non-allowlisted signer sentinels (audit-integrity break). | Sentinel signature trust |
| 4 | `.claude/hooks/_lib/audit_hmac.py` | C1, C2, C3, C4 | C1: invoked by `audit_emit.py` on every event. C2: HMAC cryptographic invariant. C3: imported by `audit_emit.py` (kernel) + `audit_log.py`. C4: silently neutralised = audit-tamper-evidence broken. | §2(3) HMAC chain integrity |
| 5 | `.claude/hooks/_lib/secret_patterns.py` | C1, C3, C4 | C1: read by `_lib/redact.py` (kernel) on every redaction event. C3: imported by `_lib/redact.py` + `check_bash_safety.py`. C4: credential-leak scrub layer; defeating it admits secrets to audit-log. | §2(2) credential-leak detection |
| 6 | `.claude/hooks/_lib/injection_patterns.py` | C1, C3, C4 | C1: read by `_lib/redact.py` + UserPromptSubmit hooks. C3: imported by `_lib/redact.py` + `_lib/output_scan.py` (this entry #7). C4: injection-detection floor defeated → prompt-injection admitted. | §2(2) injection-pattern detection |
| 7 | `.claude/hooks/_lib/output_scan.py` | C1, C3, C4 | C1: invoked at every Codex egress + audit-emit boundary. C3: imported by `_lib/codex_egress_redact.py` (this entry #8) + `_lib/audit_emit.py` (kernel). C4: OWASP egress scrub + NFKC normalisation; defeated = homoglyph injection + LLM06 side-channel. | OWASP egress scrub + NFKC normalisation |
| 8 | `.claude/hooks/_lib/codex_egress_redact.py` | C1, C3, C4, C5 | C1: invoked at every Codex MCP review (dispatcher hot path). C3: imported by `check_pair_rail.py` + `scripts/codex_invoke.py` + `_lib/adapters/codex.py` + `_lib/mcp/canonical_guard.py` (ADR-114 4 callsites). C4: egress redact = pre-leak floor. C5: ADR-114 outgoing-redaction symmetry primitive. | §2(4) Pair-Rail egress redact (ADR-114) |
| 9 | `.claude/dispatcher/**/*` (glob) | C1, C3, C5 | C1: dispatcher runs on every Codex MCP review event. C3: referenced by `check_pair_rail.py` (Pair-Rail entry hook) + `_lib/codex_egress_redact.py` (egress entry #8). C5: ADR-107/108 entire cross-LLM trust boundary. | §2(4) Pair-Rail dispatcher subversion (ADR-107/108) |
| 10 | `.github/workflows/release.yml` | C1, C3, C4 | C1: GitHub Actions reads on every tag push event (release gate). C3: workflow `uses:` + `runs:` of `validate-governance.sh` + pytest + branch protection contract. C4: CI-gate floor; mutation skips test/lint steps → false-ACCEPTED in CI history. | CI-gate floor; release surface |
| 11 | `.github/workflows/validate.yml` | C1, C3, C4 | C1: GitHub Actions reads on every PR/push event. C3: workflow drives `validate-governance.sh` + `pytest` + actionlint. C4: governance-validation chain floor; mutation skips governance lint. | CI-gate floor; governance validation chain |
| 12 | `.claude/sentinel-signers.txt` | C2, C3, C4 | C2: GPG-public-key allowlist (cryptographic-trust ledger). C3: read by `_lib/gpg_verify.py` (entry #3) + indirectly by `check_canonical_edit.py` + `check_skill_patch_sentinel.py`. C4: silent allowlist mutation = attacker-key sentinels accepted (audit-integrity break). | Sentinel-trust allowlist |
| 13 | `.claude/hooks/_lib/trusted_env.py` | C1, C3, C4 | C1: imported at framework init (first hook-fire); module-level captures `_TRUSTED_ENV_SNAPSHOT`. C3: imported by adapter `invoke()` (Wave C.2 wiring) + `check_agent_spawn.py` (Layer 2 spawn-payload sanitisation per ADR-040-AMEND-2). C4: SOLE trusted source for `CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE` audit decisions; silent neutralisation = override-bypass forensics broken. Per ADR-040-AMEND-2 Layer 1 trust-root mandate. | Emergency-override trust root (per ADR-040-AMEND-2) |

**Threshold compliance:** all 13 entries satisfy the inclusion
threshold (≥2 criteria with at least ONE of {C2, C4, C5} —
security-floor link present in every row). Entry #4 satisfies all 4
applicable criteria (most load-bearing); entries #7, #8, #11, #12,
#13 satisfy ≥3 with multiple security-floor links.

### Performance ceiling (per R1 Perf-1 — handoff §10.1)

- **Per-call overhead ceiling:** `p99 ≤ 2ms incremental` for the
  HARD-DENY pattern scan vs pre-extension baseline.
- **Microbench artifact:**
  `.claude/scripts/tests/perf/test_kernel_hard_deny_microbench.py`
- **Sample size:** N ≥ 30 per pattern (uses `hyperfine --warmup 5
  --runs 30` baseline + Python `time.perf_counter_ns` for per-pattern
  timings).
- **CI gate:** relative — `p99(post-extension) ≤ p99(pre-extension) + 2ms`.
  Microbench writes both arrays to a JSON artifact; CI parses + asserts.
- **Fail posture:** fail-CLOSED if microbench absent OR if microbench
  reports >2ms incremental.
- **Re-baseline trigger:** any future kernel-scope ADR (PLAN-089+)
  MUST re-baseline against the current `_KERNEL_PATHS` snapshot at
  proposal time; the absolute ceiling is the per-extension delta,
  NOT a cumulative bound.

### Authorization to extend (ceremony)

This ADR's acceptance + Wave E.2's implementation commit BOTH require
the kernel override env vars (the modification of
`check_arbitration_kernel.py:_KERNEL_PATHS` is itself a kernel-path
edit — circular self-protection):

```
CEO_KERNEL_OVERRIDE="ADR-116-KERNEL-HARD-DENY-TIER-0-EXTENSION"
CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT"
```

The override emits `veto_triggered(reason_code=kernel_override_used)`
for forensic trail (visible in `audit-query.py since 24h`).

## §6. Consequences

**Positive:**

- F-C2-008 single-edit catastrophic bypass chain closed at the
  mechanical floor (defense-in-depth across hook layer + Bash matcher
  E.3 + PostToolUse forensic E.4).
- 4 documented attack vectors (sentinel discovery, secret/injection
  pattern erosion, HMAC chain, Pair-Rail subversion) require
  kernel-override (which a sub-agent cannot forge per
  `check_arbitration_kernel.py` §Escape hatch).
- Decision criteria §5 list is reusable for PLAN-089 expansion (no
  per-case re-debate of what qualifies for kernel-tier).
- Perf ceiling p99 ≤ 2ms preserves hook latency budget (handoff §10.1
  aggregate PreToolUse budget = 15ms).
- CI workflow files are themselves kernel-protected — `.github/`
  edits now require `CEO_KERNEL_OVERRIDE` + `CEO_KERNEL_OVERRIDE_ACK`
  env vars per session (the standard kernel-override escape hatch
  documented in `check_arbitration_kernel.py` §Escape hatch). Sentinel
  signing is NOT the gate for kernel-tier paths; the override env
  vars are.

**Negative:**

- 13 paths transition to kernel HARD-DENY — any LEGITIMATE edit (Owner
  reconfiguring `.claude/settings.json`, dependabot bumping
  `.github/workflows/`) now requires `CEO_KERNEL_OVERRIDE` env vars
  per session. Mitigation: documented Owner workflow + Adopter
  upgrade-path note in `INSTALL.md` (PLAN-085 Wave A.4 documents).
- The dispatcher glob `.claude/dispatcher/**/*` covers any future
  dispatcher subdirectory; if PLAN-089+ introduces a NEW dispatcher
  module with intentionally-mutable config, that path needs an
  ADR-117-style amendment carve-out.
- Microbench overhead in CI: ~30 invocations × per-call cost. Run
  weekly, not per-PR (Monday 12:00 UTC stagger per ADR-040 §S6
  precedent).
- 22 R-026 paths DEFERRED to PLAN-089 — surfaced friction during the
  ~30-90-day interim where the catastrophic-chain is closed but
  long-tail kernel hardening remains open. This is the intended
  trade-off (anti-churn). PLAN-085 progress log §11 records the
  deferred list.

**Neutral:**

- The base 14 `_KERNEL_PATHS` entries are unchanged; this ADR is
  additive only.
- ADR-052 archetype VETO authority is unchanged (the security +
  identity-trust archetypes retain VETO on any future kernel
  scope change).
- ADR-107 Codex Pair-Rail asymmetric VETO matrix (Cases B/C/D/F)
  applies to this ADR's review; required ACCEPT before ceremony.

## §7. Deferred paths (DEFERRED to PLAN-089 — kernel-hardening sweep)

The following 22 paths from PLAN-084 R-026's full 33-file list are
NOT included in ADR-116. Each row carries a non-criterion-match
rationale — specifically, the path fails the §5 inclusion threshold
(≥2 criteria including ≥1 security-floor criterion from {C2, C4, C5}),
not just the criteria-count itself. Paths that satisfy only
operational-property criteria (C1 + C3) without a security-floor link
land here.

| Path | Failing criteria | Non-criterion-match rationale |
|---|---|---|
| `.claude/skills/core/*/SKILL.md` (21 files) | C2 (no cryptographic invariant), C5 (no LLM-trust boundary) | SKILL.md content is read by `Skill` tool invocation; mutation changes future agent behavior but does NOT bypass the hook layer directly. Defense-in-depth via sentinel-signing per `feedback_sentinel_signing_discipline.md`. PLAN-089 to debate kernel-tier inclusion vs SKILL.md sentinel-only. |
| `.claude/skills/frontend/*/SKILL.md` (8 files) | C2, C5 | Same rationale as core SKILL.md. |
| `.claude/skills/domains/*/skills/*/SKILL.md` (~30 files) | C2, C5 | Same rationale as core SKILL.md. Total skill body ~143 files; PLAN-089 to define kernel-tier inclusion policy. |
| `.claude/commands/*.md` | C2 (no cryptographic invariant) | Slash-command body content. Mutation changes future user-invoked behavior but does NOT bypass hooks. |
| `.claude/team.md` + `frontend-team.md` | C2 | Routing table. Mutation changes spawn-target selection but `check_agent_spawn.py` (which IS in kernel) is the floor; spawn payload still goes through compliance check. |
| `CLAUDE.md` | C2, C5 | Master context. Edits go through `check_plan_edit.py` (kernel) for `.claude/plans/` references but root `CLAUDE.md` itself is mutable at-session by CEO. PLAN-051 §3 maintenance-mode discipline applies. |
| `PROTOCOL.md` | C2, C5 | Governance text. Same rationale as CLAUDE.md. |
| `.claude/pitfalls-catalog.yaml` | C2, C5 | Pitfall corpus. Read at /pitfall invocation; mutation changes future guidance display but is not on hook hot path. |
| `.claude/task-chains.yaml` | C2, C5 | Workflow templates. Same rationale. |
| `.claude/hooks/_lib/team.py` | C2 (no crypto), C4 (advisory only) | Spawn routing helper. Read by `check_agent_spawn.py` but does NOT cryptographically gate; defeating it changes ROUTING, not GATE. PLAN-089 to revisit if routing-bypass attack vector surfaces. |
| `.claude/hooks/_lib/file_walker.py` | C2, C4 | File-system walker helper. Used by scripts; not on hook hot path. |
| `.claude/hooks/_lib/plan_frontmatter.py` | C2, C5 | Plan frontmatter parser. Used by `check_plan_edit.py` but mutating the parser is detected by `check_plan_edit` itself (since the parser change would be loaded post-edit). |
| `.claude/hooks/_lib/testing.py` | C1, C2, C4 | Test environment context manager. Used by tests only; not on hot path. |
| `.claude/hooks/_lib/metrics.py` | C2, C4 | Metrics emitter. Advisory only; not on enforcement path. |
| `.claude/hooks/_lib/tokens.py` | C2, C5 | Token accounting. Cost layer per ADR-033/ADR-052; not on security-floor enforcement. |
| `.claude/hooks/_lib/payload.py` | C2 | Payload normaliser. Used widely but not cryptographic. |
| `.claude/hooks/_lib/filelock.py` | C2 | File locking. Concurrency-correctness primitive but not on security-floor. |
| `.claude/hooks/_lib/mcp/canonical_guard.py` | (overlap with `_lib/codex_egress_redact.py` and dispatcher glob) | Wave E.2 PLAN-085 staging conflict — PLAN-080 already extended canonical-guard surface; PLAN-089 to reconcile. |
| `.claude/hooks/_lib/contract.py` | (already in kernel) | No-op — already in `_KERNEL_PATHS:85`. |
| `.claude/scripts/validate-skill-frontmatter.py` | C1 (not on hook hot path; CI-only) | Scripts are CI-validation surface; defense-in-depth via `.github/workflows/validate.yml` (which IS in kernel via this ADR). |
| `.claude/scripts/check-skill-health.sh` | C1 (CI-only) | Same rationale. |
| `.claude/scripts/check-canonical-edit-fixtures.py` | C1 (CI-only) | Same rationale. |

The PLAN-089 kernel-hardening sweep is scheduled for v1.20.x maintenance
window per `evolution-roadmap.md`.

## §8. Rollback plan

Recovery time: approximately 5-10 min Owner-physical (single session;
no GPG re-ceremony if rollback within 1 session of original).

| Artifact | Rollback action |
|---|---|
| `_KERNEL_PATHS` extension in `check_arbitration_kernel.py` | `git revert <wave-E.2-commit-SHA>` (the implementation commit). The ceremony commit itself is documentation-only; reverting only the kernel-list change is sufficient. |
| ADR-116 status | Edit `status: ACCEPTED` → `status: SUPERSEDED-BY-ROLLBACK`; add `retracted_at` + `retracted_by_reason` fields; cite the audit-emit evidence that prompted rollback. |
| Microbench artifact | `.claude/scripts/tests/perf/test_kernel_hard_deny_microbench.py` retained (advisory; informs future re-attempt). |
| `.github/workflows/` entries | If the workflows themselves need urgent edit, escape-hatch via `CEO_KERNEL_OVERRIDE` for the specific edit; revert is the cleaner path. |

Post-rollback: run `validate-governance.sh` + `pytest` to confirm
baseline restored. Audit emit `veto_triggered(reason_code=kernel_extension_rolled_back)`
for forensic trail — uses the existing registered `veto_triggered`
action with a specific reason-code suffix (per
`_lib/audit_emit.py:_KNOWN_ACTIONS` `veto_triggered` registration; no
new action registration needed for rollback path).

## §9. Authorization

KERNEL HARD-DENY extension. `check_arbitration_kernel.py` itself is in
`_KERNEL_PATHS:81`. Extension requires:

```
CEO_KERNEL_OVERRIDE="ADR-116-KERNEL-HARD-DENY-TIER-0-EXTENSION"
CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT"
```

Override emits `veto_triggered(reason_code=kernel_override_used)` for
forensic trail. The audit event MUST appear in `audit-query.py since
1h` at both the Wave 0 ceremony commit AND the Wave E.2 implementation
commit (two separate kernel-path edits requiring two override events).

## §10. Related work

- ADR-052 — VETO floor archetypes (security-engineer +
  identity-trust-architect VETO authority on this ADR).
- ADR-080 — Pair-Rail dispatcher canonical surface (precedent for
  kernel HARD-DENY extensions).
- ADR-081 — PLAN-082 batch canonical-guard extension precedent.
- ADR-093 — canonical-guard moratorium retract + kernel-override
  discipline (this ADR follows the same ceremony pattern).
- ADR-107 — Codex MCP Pair-Rail asymmetric VETO matrix (Cases
  B/C/D/F); this ADR's review subject to ACCEPT verdict.
- ADR-108 — Codex Pair-Rail dispatcher protocol (dispatcher glob in
  §5 entry #9 protects the surface ADR-108 defines).
- ADR-113 — PLAN-084 canonical guard extension (precedent for
  atomic ADR + canonical-path extension ceremony).
- ADR-114 — Codex egress redaction symmetry (entry #8 protects
  the redact primitive).
- PLAN-080 — original canonical-guard extension at PLAN-080 Phase 0a.
- PLAN-082 — batch canonical-guard extension precedent.
- PLAN-084 R-026 / F-C2-002 / F-C2-008 — driver findings;
  catastrophic-bypass chain documented in Wave C.2 deep-dive.
- PLAN-085 Wave E.2 — implementation (gated by this ADR ACCEPTED).
- PLAN-089 (planned) — kernel-hardening sweep that revisits the 22
  deferred paths.

## §11. Enforcement commit

The runtime enforcement artifact (the 13-entry extension to
`_KERNEL_PATHS:76-107` in `check_arbitration_kernel.py`) ships at the
PLAN-085 Wave E.2 ceremony commit. SHA recorded in PLAN-085 progress
log §11 once Wave E.2 lands.

This ADR's own ACCEPTED moment is the PLAN-085 Wave 0 atomic
ceremony commit (SHA recorded separately). Both commits emit the
`veto_triggered(reason_code=kernel_override_used)` audit event per §9.
