---
id: ADR-116-AMEND-1
title: Kernel HARD-DENY tier-0 extension v2 — +30 deployable / +65 full enumerated paths
status: ACCEPTED
created: 2026-05-13
proposed_at: 2026-05-13
proposed_by: CEO (PLAN-089 Wave A.2; PLAN-084 R-026 driver)
amends: ADR-116
amendment_of: ADR-116 (KERNEL HARD-DENY tier-0 scope extension — original 2026-05-12)
amends_section: §5 Entry list (extends with +30 deployable-subset rows or +65 full-set rows)
veto_floor: ADR-052 (security-engineer + identity-trust-architect VETO; threat-detection-engineer co-signer)
codex_pair_rail: required (ADR-107 — kernel scope expansion is veto-floor decision)
related_plans: [PLAN-084, PLAN-085, PLAN-089]
related_adrs: [ADR-040, ADR-040-AMEND-2, ADR-052, ADR-093, ADR-107, ADR-108, ADR-114, ADR-115, ADR-116, ADR-117, ADR-119]
supersedes: []
tags: [governance, kernel, hard-deny, canonical-guard, defense-in-depth, performance-ceiling, amendment, anti-churn]
authorization: PLAN-089 Wave A.4 atomic ceremony (`OWNER-CEREMONY-PLAN-089-WAVE-A.sh`)
ceremony_env_override: CEO_KERNEL_OVERRIDE=PLAN-089-WAVE-A-KERNEL-EXTENSION-V2
ceremony_env_ack: CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT
performance_ceiling_p99_ms: 2
performance_ceiling_ratio: 1.0
microbench_target: .claude/scripts/tests/perf/test_kernel_hard_deny_microbench.py
deployable_subset_count: 30
full_set_count: 65
honest_deferral_count: 5
plan: PLAN-089
accepted_at: 2026-05-20
accepting_session: S147
---

# ADR-116-AMEND-1 — Kernel HARD-DENY tier-0 extension v2

## §1. Status

PROPOSED at draft time (PLAN-089 Wave A.2). Flips to ACCEPTED at the
atomic Wave A.4 ceremony commit, gated by:

1. Dedicated Codex MCP Pair-Rail R2 review per ADR-107 (kernel scope
   expansion is veto-floor decision; verdict must be ACCEPT before
   ceremony script flips status).
2. ADR-052 archetypes (security-engineer + identity-trust-architect
   VETO floor; threat-detection-engineer co-signer) consensus on the
   30-row deployable-subset OR 65-row full-set scope.
3. Microbench artifact (`.claude/scripts/tests/perf/test_kernel_hard_deny_microbench.py`)
   landed AT or BEFORE ceremony commit (perf ceiling §5 verified
   empirically — fail-CLOSED if absent OR if AC8c ratio >1.0).
4. Wave A.5 parametrized tests (`test_check_canonical_edit_kernel_v2.py`)
   landed AT or BEFORE ceremony commit covering every new entry.

This amendment does NOT modify ADR-116 §4 (Options) or §5 (Decision
criteria C1-C5 inclusion threshold). The 5-criterion test is locked at
S109 (Codex Pair-Rail iter-5 ACCEPT thread `019e1d22`). This amendment
ONLY adds rows to ADR-116 §5 Entry list per the same criteria.

## §2. Context

Original ADR-116 (S109 2026-05-12, ACCEPTED) established tier-0 kernel
HARD-DENY with 14 entries (12 explicit + 1 dispatcher glob + 1
`trusted_env.py` from Codex iter-3 cross-ADR consistency fold). Wave 0
of PLAN-085 landed the 13 net-new entries; subsequent Wave E.2 (S111)
landed an additional +3 (`.claude/settings.json` re-anchored,
`_python-hook.sh`, `_lib/trusted_env.py`) bringing the post-S111
cardinality to **30** entries.

PLAN-084 SOTA-finalization audit (S107-cont, tag v1.18.0) finding
**C.2-002 (R-026)** identified **≥33 additional unguarded critical
paths** fitting the ADR-116 §4 5-criteria test. ADR-116 §2 explicitly
deferred the remaining 22 to PLAN-089: *"The remaining 22 paths in
PLAN-084 R-026's full 33-file kernel sweep are DEFERRED to PLAN-089
(kernel-hardening sweep) per the evolution-roadmap; their inclusion
would expand scope past the catastrophic-bypass-closure mandate and
would need a separate ADR."*

PLAN-089 Wave A.1 enumeration audit
(`.claude/plans/PLAN-089/kernel-extension-v2-enumeration.md`)
catalogued **65 recommended-EXTEND rows** + **5 honest deferrals**,
each row literally citing ≥2 of the 5 ADR-116 §5 inclusion criteria
with at least one of {C2, C4, C5} (security-floor link). The
enumeration's row count exceeded R-026's coarser 33-file sweep
because the criteria walk surfaced additional load-bearing paths
(package-init shim-attack surface, mcp/* canonical-guard sibling,
tier_policy/* loader cluster, governance-anchor files at
`.claude/governance/`, etc.) that R-026 missed at coarser depth.

This amendment selects between:

- **Deployable subset (30 entries)** — the highest-leverage rows
  covering all 14 `_lib/` entries + 5 tier_policy entries + 6
  hot-path hooks + 5 governance anchors. Used as fallback if
  the Wave A microbench shows >2ms incremental or >1.0 ratio at
  the full 65-row scope.
- **Full set (65 entries)** — every criterion-justified row from
  Wave A.1 enumeration. Used ONLY if Wave A microbench AC8c
  p95+p99 ≤1.0 baseline ratio is verified pre-ceremony.

The selection is **mechanical** (perf-gated, not a policy debate).
Wave A.4 ceremony script reads the microbench JSON artifact, applies
the conditional, and emits the appropriate `_KERNEL_PATHS` extension
delta.

## §3. Decision drivers

- **PLAN-084 R-026 closure (primary):** every Wave A.1 row directly
  closes one or more attack vectors from the ADR-116 §2 4-vector
  taxonomy (sentinel discovery / pattern erosion / HMAC chain /
  Pair-Rail dispatcher) OR the auxiliary attack-surface labels
  enumerated in ADR-116 §2 (hook deactivation via matcher,
  interpreter pre-emption, sentinel signature trust, CI-gate floor,
  sentinel-trust allowlist, emergency-override trust root). Without
  coverage of the 30-65 additional paths, the F-C2-008 catastrophic
  chain remains exploitable through the un-extended surfaces.
- **Anti-churn (ADR-115 maintenance-mode):** ADR-116 §5 criteria
  locked at S109. This amendment ONLY ADDS ROWS — it does NOT
  re-debate the criteria, change the inclusion threshold (≥2 of 5
  with at least one of {C2, C4, C5}), or redefine the 4-vector
  attack taxonomy. The amendment is mechanical row-addition under
  unchanged rules.
- **VETO-floor mandate (ADR-052):** kernel scope changes are
  security-engineer + identity-trust-architect VETO; this amendment
  cannot proceed without explicit Codex Pair-Rail R2 ACCEPT per
  ADR-107.
- **Performance ceiling (Perf-1):** the ADR-116 +2ms p99 ceiling and
  ratio-1.0 gate are PRESERVED unchanged in this amendment. The
  deployable subset is the fallback if the full set breaches.
- **Reversibility:** kernel scope expansions are LOW-reversibility
  (any access-pattern that depends on the path becomes blocked
  retroactively). Each entry in §4 below cites specific
  criterion-justification AND attack-vector closed, mirroring the
  per-row format of ADR-116 §5 Entry list. The deployable-subset
  fallback PRESERVES reversibility at the per-row level (rows tagged
  Subset=NO are deferred to a future amendment if the microbench
  breaches).
- **ADR-117 rename policy:** this file is named
  `ADR-116-AMEND-1-kernel-extension-v2.md` per ADR-117 §3 amendment
  filename pattern (`ADR-NNN-AMEND-M-<slug>.md`). The slug
  `kernel-extension-v2` is distinct from the parent slug
  `kernel-hard-deny-tier-0-extension` to avoid collision per
  ADR-117 §4.

## §4. Decision (enumerated additions to ADR-116 §5 Entry list)

Extend `_KERNEL_PATHS` in `.claude/hooks/check_arbitration_kernel.py`
from **30 → 30 + N entries** where N is selected mechanically by the
Wave A microbench JSON artifact:

- **If microbench reports ratio ≤1.0 at +65 entries:** N = 65 (full
  set; all rows below).
- **Else if microbench reports ratio ≤1.0 at +30 entries:** N = 30
  (deployable subset; rows tagged Subset=YES below).
- **Else:** fail-CLOSED; ceremony aborts; Wave A.4 deferred until
  microbench is re-baselined OR scope is further reduced via a
  follow-up amendment.

The amendment does NOT modify ADR-116 §4 criteria — criteria locked
at S109. This amendment only adds rows. Each row inherits the
ADR-116 §5 criterion-justification format (per-criterion one-line
rationale).

### §4.1 Criterion shorthand legend

Per Wave A.1 enumeration §Method, the 5-criterion shorthand maps to
ADR-116 §5 criteria as follows:

| Shorthand | ADR-116 §5 criterion |
|---|---|
| **tier-0-governance** | C1 — Consulted on every hook-fired event |
| **identity-trust** | C2 — Enforces a cryptographic invariant (GPG / HMAC / signer / nonce) |
| **kernel-overrider-self-reference** | C3 — Referenced by ≥2 other kernel modules (self-protection sub-case) |
| **audit-integrity** | C4 — Controls audit/log/CI integrity floor |
| **KERNEL HARD-DENY enforcer** | C5 — Cross-LLM trust / dispatcher / egress-redact equivalent (file's execution implements HARD-DENY or Pair-Rail enforcement semantics) |

Every row below cites ≥2 shorthand names. At least one of {C2, C4,
C5} (identity-trust, audit-integrity, KERNEL HARD-DENY enforcer) is
present in every row per the ADR-116 §5 inclusion threshold.

### §4.2 Attack-vector taxonomy (ADR-116 §2 reference)

The "Attack vector closed" column below uses these labels (ADR-116 §2
4-vector + auxiliary surfaces):

- **§2(1) sentinel discovery starvation** — bypass of
  `_find_sentinels()` glob discovery in `check_canonical_edit.py`.
- **§2(2) credential-leak detection** — mutation of `secret_patterns`
  / `redact` pipeline (ADR-040-AMEND-2 trust root).
- **§2(2) injection-pattern detection** — mutation of
  `injection_patterns` / `output_scan` pipeline.
- **§2(3) HMAC chain integrity** — `audit_hmac` + per-event HMAC
  seed loading.
- **§2(4) Pair-Rail dispatcher subversion** — mutation of
  `.claude/dispatcher/**/*` or egress-redact / Codex MCP boundary
  per ADR-107/108/114.
- **Hook deactivation via matcher edit** — `.claude/settings.json`
  matcher block emptied.
- **Interpreter pre-emption (shim layer)** — `_python-hook.sh`
  replaced.
- **Sentinel signature trust** — `_lib/gpg_verify.py` mutation.
- **Sentinel-trust allowlist** — `.claude/sentinel-signers.txt`
  attacker-key insertion.
- **CI-gate floor (release / validate / mutation / coverage / actionlint)** —
  workflow file mutation.
- **Emergency-override trust root** — `_lib/trusted_env.py` Layer 1
  snapshot per ADR-040-AMEND-2.
- **Tier-policy / VETO-floor mutation** — silent ADR-052 demotion
  via tier_policy loader/constants/types path.
- **Cross-LLM adapter spoofing** — `_lib/adapters/codex.py` /
  `_lib/adapters/_constants.py` synthetic ACCEPT.
- **Package-init shim attack** — `__init__.py` re-export attack
  silently no-ops every kernel callsite.
- **MCP envelope-mediated kernel write** — `mcp/canonical_guard.py`
  sibling-of-canonical-edit at MCP boundary.
- **MCP transport bearer/nonce replay** — `mcp/bearer_replay.py`
  DPoP-style replay window.
- **Audit-log rotation / lock / state-store mutation** —
  `audit_rotation.py` / `filelock.py` / `state_store.py` tamper-window
  primitives.
- **SPEC context poisoning** — `spec_context_sanitizer.py` mutation.
- **MCP-side injection floor** — `mcp_injection_scan.py` mutation.
- **Replay-redact forensic stripping** — `replay_redact.py` mutation.
- **Injection-salt determinism collapse** — `injection_salt.py`
  constant-seed mutation.
- **Sub-agent identity spoofing** — `check_subagent_fabrication.py`
  mutation.
- **Confidence-gate downgrade** — `check_confidence_gate.py` mutation.
- **Anti-CEO-overhead masking** — `check_anti_ceo_overhead.py`
  forensic suppression.
- **Scratchpad ACL bypass** — `check_scratchpad_access.py` mutation.
- **Budget gate bypass** — `check_budget.py` token-cost ceiling
  bypass.
- **Prompt-entry audit suppression** — `check_fluency_nudge.py`
  mutation.
- **Skill-bootstrap TOCTOU** — `check_skill_bootstrap_post.py`
  mutation (PLAN-024 chaos-class).
- **Read/WebFetch injection scan bypass** —
  `check_read_injection.py` / `check_webfetch_injection.py`
  mutation.
- **Egress secret/output safety bypass** — `check_output_secrets.py`
  / `check_output_safety.py` mutation.
- **MCP response inspection bypass** — `check_mcp_response.py`
  mutation.
- **Tier-policy classifier bypass** — `check_tier_policy.py` /
  `check_tier_policy_misrouting_24h.py` mutation.
- **Session-boundary audit dropout** — `SessionStart.py` /
  `SessionEnd.py` / `Stop.py` / `UserPromptSubmit.py` mutation.
- **Architect-outcome event suppression** —
  `emit_architect_outcome.py` mutation.
- **Codex MCP filewrite envelope bypass** —
  `check_codex_filewrite.py` mutation (F-C2-004).
- **Codex MCP response egress bypass** — `check_codex_response.py`
  mutation.
- **Bash-mediated kernel write (PostToolUse forensic blind spot)** —
  `check_bash_canonical_forensic.py` mutation.
- **Bash matcher bypass (PreToolUse)** — `check_bash_safety.py`
  mutation (F-C2-003 chain stage 2).
- **Pair-Rail decision flip (synthetic ACCEPT)** —
  `pair_rail_decide.py` mutation.
- **MCP / spawn routing redirection** — `mcp_routing.py` /
  `model_routing.py` mutation.
- **Agent-frontmatter model-field rewrite** —
  `agent_frontmatter.py` mutation (F-01-03 class).
- **Tier-policy anchor mutation (JSON + sigchain)** —
  `tier-policy.json` / `tier-policy.json.sigchain` mutation.
- **Governance-waiver injection** —
  `governance-waivers.yaml` mutation.
- **Codex CLI version-skew / binary-swap** —
  `codex-cli-pin.txt` / `codex-cli-binary-sha256.txt` mutation.
- **Pair-Rail inputs hash / verdict-template spoofing** —
  `pair-rail-inputs-hash-manifest.txt` /
  `pair-rail-verdict-template.md` mutation.
- **Function-length / audit-token allowlist injection** —
  `function-length-grandfather.yaml` / `audit_tokens_allowlist.json`
  mutation.
- **Branch-protection / reviewer carve-out** — `.github/CODEOWNERS`
  mutation.
- **Canonical-JSON serialiser desynchronisation** —
  `_lib/canonical_json.py` mutation (silent HMAC anchor break).
- **Escalation-signal tag suppression** —
  `_lib/escalation_signals.py` mutation (forensic blind spot during
  active attack).

### §4.3 Enumerated additions (full set — 65 rows)

| # | Path / glob | Criteria | Attack-vector closed | Subset? |
|---|---|---|---|---|
| 1 | `.claude/hooks/_lib/mcp/canonical_guard.py` | tier-0-governance + KERNEL HARD-DENY enforcer + audit-integrity | MCP envelope-mediated kernel write | YES |
| 2 | `.claude/hooks/_lib/mcp/bearer_replay.py` | identity-trust + audit-integrity | MCP transport bearer/nonce replay | YES |
| 3 | `.claude/hooks/_lib/credentials.py` | identity-trust + tier-0-governance | §2(2) credential-leak detection (ADR-040-AMEND-2 trust root) | YES |
| 4 | `.claude/hooks/_lib/canonical_json.py` | identity-trust + audit-integrity | Canonical-JSON serialiser desynchronisation (silent HMAC anchor break) | YES |
| 5 | `.claude/hooks/_lib/audit_rotation.py` | audit-integrity + tier-0-governance | Audit-log rotation / lock / state-store mutation | YES |
| 6 | `.claude/hooks/_lib/replay_redact.py` | identity-trust + audit-integrity | Replay-redact forensic stripping | YES |
| 7 | `.claude/hooks/_lib/injection_salt.py` | identity-trust + audit-integrity | Injection-salt determinism collapse | YES |
| 8 | `.claude/hooks/_lib/mcp_injection_scan.py` | tier-0-governance + audit-integrity | MCP-side injection floor | YES |
| 9 | `.claude/hooks/_lib/spec_context_sanitizer.py` | tier-0-governance + audit-integrity | SPEC context poisoning | YES |
| 10 | `.claude/hooks/_lib/state_store.py` | audit-integrity + kernel-overrider-self-reference | Audit-log rotation / lock / state-store mutation | YES |
| 11 | `.claude/hooks/_lib/filelock.py` | tier-0-governance + audit-integrity | Audit-log rotation / lock / state-store mutation (torn HMAC frames) | YES |
| 12 | `.claude/hooks/_lib/adapters/codex.py` | KERNEL HARD-DENY enforcer + identity-trust | Cross-LLM adapter spoofing | YES |
| 13 | `.claude/hooks/_lib/adapters/_constants.py` | KERNEL HARD-DENY enforcer + tier-0-governance | Cross-LLM adapter spoofing (constants re-routing) | YES |
| 14 | `.claude/hooks/_lib/__init__.py` | kernel-overrider-self-reference + tier-0-governance | Package-init shim attack | YES |
| 15 | `.claude/hooks/_lib/adapters/__init__.py` | kernel-overrider-self-reference + KERNEL HARD-DENY enforcer | Package-init shim attack (adapter surface) | NO |
| 16 | `.claude/hooks/_lib/mcp/__init__.py` | kernel-overrider-self-reference + tier-0-governance | Package-init shim attack (mcp surface) | NO |
| 17 | `.claude/hooks/_lib/tier_policy/loader.py` | tier-0-governance + identity-trust | Tier-policy / VETO-floor mutation | YES |
| 18 | `.claude/hooks/_lib/tier_policy/__init__.py` | kernel-overrider-self-reference + tier-0-governance | Package-init shim attack (tier_policy surface) | YES |
| 19 | `.claude/hooks/_lib/tier_policy/_constants.py` | tier-0-governance + identity-trust | Tier-policy / VETO-floor mutation (constants) | YES |
| 20 | `.claude/hooks/_lib/tier_policy/_agent_frontmatter.py` | tier-0-governance + identity-trust | Tier-policy / VETO-floor mutation (frontmatter resolver) | YES |
| 21 | `.claude/hooks/_lib/tier_policy/_types.py` | kernel-overrider-self-reference + tier-0-governance | Tier-policy / VETO-floor mutation (type widening) | YES |
| 22 | `.claude/hooks/_lib/agent_frontmatter.py` | tier-0-governance + identity-trust | Agent-frontmatter model-field rewrite (F-01-03) | NO |
| 23 | `.claude/hooks/_lib/model_routing.py` | tier-0-governance + identity-trust | MCP / spawn routing redirection | NO |
| 24 | `.claude/hooks/_lib/mcp_routing.py` | tier-0-governance + KERNEL HARD-DENY enforcer | MCP / spawn routing redirection | NO |
| 25 | `.claude/hooks/_lib/pair_rail_decide.py` | KERNEL HARD-DENY enforcer + audit-integrity | Pair-Rail decision flip (synthetic ACCEPT) | NO |
| 26 | `.claude/hooks/_lib/escalation_signals.py` | audit-integrity + tier-0-governance | Escalation-signal tag suppression | NO |
| 27 | `.claude/hooks/check_pair_rail.py` | KERNEL HARD-DENY enforcer + identity-trust | §2(4) Pair-Rail dispatcher subversion (hot path) | YES |
| 28 | `.claude/hooks/check_bash_safety.py` | tier-0-governance + audit-integrity | Bash matcher bypass (PreToolUse) — F-C2-003 chain stage 2 | YES |
| 29 | `.claude/hooks/check_bash_canonical_forensic.py` | audit-integrity + tier-0-governance | Bash-mediated kernel write (PostToolUse forensic blind spot) | YES |
| 30 | `.claude/hooks/check_codex_filewrite.py` | KERNEL HARD-DENY enforcer + identity-trust | Codex MCP filewrite envelope bypass (F-C2-004) | YES |
| 31 | `.claude/hooks/check_codex_response.py` | KERNEL HARD-DENY enforcer + identity-trust | Codex MCP response egress bypass | YES |
| 32 | `.claude/hooks/check_skill_bootstrap_post.py` | tier-0-governance + audit-integrity | Skill-bootstrap TOCTOU (PLAN-024 chaos-class) | NO |
| 33 | `.claude/hooks/check_skill_reference_read.py` | tier-0-governance + identity-trust | Skill-content load against canonical SHA bypass | NO |
| 34 | `.claude/hooks/check_read_injection.py` | tier-0-governance + audit-integrity | Read/WebFetch injection scan bypass (Read) | NO |
| 35 | `.claude/hooks/check_webfetch_injection.py` | tier-0-governance + audit-integrity | Read/WebFetch injection scan bypass (WebFetch) | NO |
| 36 | `.claude/hooks/check_output_secrets.py` | audit-integrity + identity-trust | Egress secret/output safety bypass (secrets) | NO |
| 37 | `.claude/hooks/check_output_safety.py` | audit-integrity + tier-0-governance | Egress secret/output safety bypass (safety floor) | NO |
| 38 | `.claude/hooks/check_mcp_response.py` | tier-0-governance + KERNEL HARD-DENY enforcer | MCP response inspection bypass | NO |
| 39 | `.claude/hooks/check_tier_policy.py` | tier-0-governance + identity-trust | Tier-policy classifier bypass | NO |
| 40 | `.claude/hooks/check_tier_policy_misrouting_24h.py` | audit-integrity + tier-0-governance | Tier-policy misrouting 24h detection bypass | NO |
| 41 | `.claude/hooks/check_subagent_fabrication.py` | tier-0-governance + identity-trust | Sub-agent identity spoofing (PLAN-058 R-002) | NO |
| 42 | `.claude/hooks/check_confidence_gate.py` | audit-integrity + tier-0-governance | Confidence-gate downgrade (ADR-019 advisory mode) | NO |
| 43 | `.claude/hooks/check_anti_ceo_overhead.py` | tier-0-governance + audit-integrity | Anti-CEO-overhead masking (forensic dimension) | NO |
| 44 | `.claude/hooks/check_scratchpad_access.py` | tier-0-governance + audit-integrity | Scratchpad ACL bypass | NO |
| 45 | `.claude/hooks/check_budget.py` | tier-0-governance + audit-integrity | Budget gate bypass (PLAN-020 token accounting) | NO |
| 46 | `.claude/hooks/check_fluency_nudge.py` | tier-0-governance + audit-integrity | Prompt-entry audit suppression | NO |
| 47 | `.claude/hooks/audit_log.py` | audit-integrity + tier-0-governance | Session-boundary audit dropout (PostToolUse observer) | YES |
| 48 | `.claude/hooks/SessionStart.py` | audit-integrity + tier-0-governance | Session-boundary audit dropout (SessionStart) | NO |
| 49 | `.claude/hooks/SessionEnd.py` | audit-integrity + tier-0-governance | Session-boundary audit dropout (SessionEnd) | NO |
| 50 | `.claude/hooks/Stop.py` | audit-integrity + tier-0-governance | Session-boundary audit dropout (Stop) | NO |
| 51 | `.claude/hooks/UserPromptSubmit.py` | tier-0-governance + identity-trust | Session-boundary audit dropout (UserPromptSubmit; injection-salt consumer) | NO |
| 52 | `.claude/hooks/emit_architect_outcome.py` | audit-integrity + tier-0-governance | Architect-outcome event suppression (debate FSM trust loss) | NO |
| 53 | `.claude/tier-policy.json` | identity-trust + tier-0-governance | Tier-policy anchor mutation (JSON) | NO |
| 54 | `.claude/tier-policy.json.sigchain` | identity-trust + audit-integrity | Tier-policy anchor mutation (sigchain HMAC) | NO |
| 55 | `.claude/governance/governance-waivers.yaml` | audit-integrity + tier-0-governance | Governance-waiver injection (release gate) | YES |
| 56 | `.claude/governance/codex-cli-pin.txt` | identity-trust + audit-integrity | Codex CLI version-skew | YES |
| 57 | `.claude/governance/codex-cli-binary-sha256.txt` | identity-trust + audit-integrity | Codex CLI binary-swap (supply-chain trust anchor) | YES |
| 58 | `.claude/governance/pair-rail-inputs-hash-manifest.txt` | identity-trust + audit-integrity | Pair-Rail inputs hash anchor compromise | YES |
| 59 | `.claude/governance/pair-rail-verdict-template.md` | identity-trust + tier-0-governance | Pair-Rail verdict-template spoofing | NO |
| 60 | `.claude/governance/function-length-grandfather.yaml` | audit-integrity + tier-0-governance | Function-length lint grandfather injection | NO |
| 61 | `.claude/governance/audit_tokens_allowlist.json` | audit-integrity + tier-0-governance | Audit-token allowlist injection (ghost-token-waste detector silenced) | NO |
| 62 | `.github/CODEOWNERS` | tier-0-governance + identity-trust | Branch-protection / reviewer carve-out (merge-side trust boundary) | YES |
| 63 | `.github/workflows/mutation-gate.yml` | audit-integrity + tier-0-governance | CI-gate floor (mutation testing, PLAN-050 R-021) | NO |
| 64 | `.github/workflows/coverage.yml` | audit-integrity + tier-0-governance | CI-gate floor (coverage, R-032 / R-035) | NO |
| 65 | `.github/workflows/actionlint.yml` | audit-integrity + tier-0-governance | CI-gate floor (workflow-file lint; re-opens release/validate mutation surface if bypassed) | NO |

**Deployable-subset selection (30 rows, Subset=YES):**

- 14 `_lib/` foundation entries: rows #1-#14 (`mcp/canonical_guard`,
  `mcp/bearer_replay`, `credentials`, `canonical_json`,
  `audit_rotation`, `replay_redact`, `injection_salt`,
  `mcp_injection_scan`, `spec_context_sanitizer`, `state_store`,
  `filelock`, `adapters/codex`, `adapters/_constants`,
  `_lib/__init__`).
- 5 `_lib/tier_policy/` entries: rows #17-#21 (`loader`,
  `__init__`, `_constants`, `_agent_frontmatter`, `_types`).
- 6 hot-path hook entries: rows #27-#31 (`check_pair_rail`,
  `check_bash_safety`, `check_bash_canonical_forensic`,
  `check_codex_filewrite`, `check_codex_response`) + #47
  (`audit_log` PostToolUse observer).
- 5 governance anchors: rows #55-#58 (`governance-waivers`,
  `codex-cli-pin`, `codex-cli-binary-sha256`,
  `pair-rail-inputs-hash-manifest`) + #62 (`CODEOWNERS`).

**Subset total: 14 + 5 + 6 + 5 = 30 rows** (matches Wave A.1 §Final
tallies deployable-subset count).

**Full-set total: 65 rows** (per Wave A.1 §Final tallies).

**Sanity:** every row tagged Subset=YES contains either C2
(identity-trust), C4 (audit-integrity), or C5 (KERNEL HARD-DENY
enforcer) per the ADR-116 §5 security-floor inclusion threshold.
Every row tagged Subset=NO ALSO satisfies the threshold (else it
would be in §5 honest deferrals, not §4 enumerated additions); the
Subset=NO tag indicates a perf-budget deferral, not a criteria
failure.

## §5. Honest deferrals (rows that fail ADR-116 §5 inclusion threshold)

Per ADR-116 §5 inclusion threshold (≥2 of 5 criteria with at least
ONE of {C2, C4, C5}), the following 5 paths are honest deferrals —
each satisfies fewer than the required criterion count OR lacks any
security-floor link. Each row literally cites the "only N of 5"
rationale.

| Path | Criteria reached | Why deferred (per Wave A.1 §Honest deferrals) |
|---|---|---|
| `.claude/hooks/_lib/payload.py` | only 1 of 5 (tier-0-governance — wide read) | Pure payload normaliser; not on cryptographic-trust path. No security-floor link per ADR-116 §5 inclusion threshold. Owner-edit cost > attack-surface gain. Re-evaluate if a payload-mutation attack vector surfaces (PLAN-093+). |
| `.claude/hooks/_lib/team.py` | only 1 of 5 (tier-0-governance — advisory) | Spawn-routing helper used by `check_agent_spawn.py` (kernel). Mutation affects ROUTING, not the GATE. ADR-116 §7 row 10 already deferred this; no new evidence forces promotion. |
| `.claude/hooks/_lib/file_walker.py` | only 1 of 5 (tier-0-governance — wide read) | Filesystem walker helper used by scripts; NOT on hook hot path. Same disposition as ADR-116 §7 row 11. |
| `.claude/hooks/_lib/plan_frontmatter.py` | only 1 of 5 (tier-0-governance — wide read) | Plan frontmatter parser consumed by `check_plan_edit.py` (kernel). Self-protecting at the consumer (loaded post-edit by the guard itself). ADR-116 §7 row 12 disposition retained. |
| `.claude/hooks/_lib/testing.py` | 0 of 5 (test-only) | Test environment context manager — used only by tests, never on hot path. ADR-116 §7 row 13 disposition retained. |

**Honest deferrals: 5** (within the Wave A.1 ≤5 cap and ≤15% of
the R-026 33-candidate target — 5/33 ≈ 15.2%).

### §5.1 Near-misses NOT folded into deferrals (per Wave A.1 §Notes)

For audit-completeness, the following Wave A.1 §Notes near-miss paths
are documented as out-of-scope for this AMEND-1 (not counted in the
5-deferral cap; tracked for PLAN-090+ if a fresh attack vector
surfaces):

- `_lib/metrics.py`, `_lib/tokens.py` — advisory cost/metrics layers
  (ADR-116 §7 rows 14-15 disposition).
- `_lib/quiet_mode.py` — toggling suppresses display, not enforcement.
- `_lib/memory_shared.py`, `scratchpad_lib.py` — defense at hook
  layer #44 (`check_scratchpad_access.py`) is sufficient.
- `_lib/otel_emit.py` — silent disable detectable via OTel pipeline
  gap, not in-kernel guard.
- `_lib/rag_bridge.py`, `_lib/rag_events.py` — PLAN-097 conditional
  RAG (FASE 4); will be promoted in PLAN-097 if/when default-ON.
- `_lib/confidence_labels.py` — fed by `check_confidence_gate.py`
  (row #42 above); defense-in-depth at consumer is sufficient.
- `_lib/embeddings.py`, `_lib/exceptions.py`, `_lib/frontmatter.py` —
  utility libs without security-floor link.
- `.claude/scripts/local/**` — Owner-local / CI-only;
  defense-in-depth via `.github/workflows/validate.yml` (kernel).

## §6. Ceremony

This amendment is enforced via Wave A.4 Owner-physical ceremony.

**Ceremony script:** `scripts/local/historical/OWNER-CEREMONY-PLAN-089-WAVE-A.sh`

**Env tokens (both required, in subshell — bypass discipline per
S109/S111/S116 precedent):**

```
CEO_KERNEL_OVERRIDE=PLAN-089-WAVE-A-KERNEL-EXTENSION-V2
CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT
```

**Sentinel:**

- PLAN-089 Wave A.4 amendment sentinel covering BOTH:
  - the `_KERNEL_PATHS` extension delta in
    `.claude/hooks/check_arbitration_kernel.py`, AND
  - the ADR file itself (`.claude/adr/ADR-116-AMEND-1-kernel-extension-v2.md`).
- Sentinel `.asc` produced in the SAME commit (detached GPG-signed
  per `feedback_sentinel_signing_discipline.md` — byte-level
  tamper evidence; commit-level `-S` is insufficient).

**Idempotency:** re-running ceremony with identical env values is a
no-op (entries deduplicated against existing `_KERNEL_PATHS` by exact
string match; ADR status flip is a no-op if already ACCEPTED).

**Tag:** closure folded into PLAN-089 v1.23.0 tag (per PLAN-089
plan-master target v1.23.0).

**Microbench gate (mechanical):** ceremony script reads JSON artifact
from `.claude/scripts/tests/perf/test_kernel_hard_deny_microbench.py`
output. If `ratio_p95 ≤ 1.0` AND `ratio_p99 ≤ 1.0` at full-set
extension, deploy 65 rows. Else if ratios ≤1.0 at deployable-subset
extension, deploy 30 rows (Subset=YES). Else fail-CLOSED (abort
ceremony; emit
`kernel_extension_microbench_breach` audit event; require
re-baseline or scope reduction before retry).

## §7. Acceptance criteria (mechanical)

| AC | Verify | Wave |
|---|---|---|
| AC1 | `len(_KERNEL_PATHS) >= 30 + 30` (deployable subset) OR `>= 30 + 65` (full set) per microbench gate | A.4 |
| AC2 | Each new entry has a matching parametrized test in `.claude/hooks/tests/test_check_canonical_edit_kernel_v2.py` (parametrize over the deployed N) | A.5 |
| AC3 | Wave A microbench p95 + p99 ratio ≤1.0 vs pre-Wave-A baseline (AC8c gate) — JSON artifact present, parsable, ratios verified | A.4 |
| AC4 | Status flip `PROPOSED → ACCEPTED` requires sentinel `.asc` + Owner GPG `00000000…` per `feedback_sentinel_signing_discipline.md` | A.4 |
| AC5 | ADR file landed at `.claude/adr/ADR-116-AMEND-1-kernel-extension-v2.md` (filename pattern per ADR-117 §3) | A.4 |
| AC6 | Wave A.1 enumeration source-of-truth file (`.claude/plans/PLAN-089/kernel-extension-v2-enumeration.md`) referenced in §2 and unmodified post-amendment (locked artifact) | A.4 |
| AC7 | Codex MCP Pair-Rail R2 verdict ACCEPT recorded in PLAN-089 progress log (ADR-107 mandate; veto-floor change requires explicit ACCEPT) | A.4 pre-flip |
| AC8 | Ceremony emits `kernel_extension_v2_landed` audit event with payload `{deployed_count: N, deferred_count: 65-N, microbench_p99_ratio: <float>}` (ATLAS T1556 binding) | A.4 |

## §8. Risks + alternatives considered

| Alternative | Why rejected |
|---|---|
| Defer all 30-65 rows to a future ADR-116-AMEND-2 | Single-edit catastrophic chain (F-C2-008) is only partially closed by the original ADR-116 13-entry subset. PLAN-089 plan-level AC requires ≥58 entries post-Wave-A; deferring all 65 misses by ≥28. PLAN-084 R-026 explicitly carries the remaining 22 paths into PLAN-089 scope per ADR-116 §2; further deferral re-creates the kernel-coverage backlog. |
| Adopt full 65-row set unconditionally (no microbench gate) | Perf regression risk: hot-path scan over `_KERNEL_PATHS` is invoked on every PreToolUse Edit/Write/MultiEdit event. ADR-116 §6 +2ms ceiling is the load-bearing operational invariant; bypassing the gate breaches the original ADR-116 contract (semantic shift requires explicit super-amendment, not silent override). The microbench gate is the mechanical floor. |
| Adopt only the deployable subset (30 rows) — drop the full-set option entirely | Loss of optionality: if Wave A microbench shows headroom at 65, deferring the additional 35 rows for no perf reason is a missed closure opportunity. Subset-only doctrine would require a follow-up AMEND-2 for every future microbench-headroom batch (ADR churn). |
| Replace ADR-116 entirely (supersede instead of amend) | ADR-117 rename policy + ADR-115 anti-churn require AMEND when criteria are UNCHANGED. ADR-116 §5 criteria are unchanged by this work; only the row count grows. Supersession would mis-state the doctrine evolution (criteria locked at S109; PLAN-089 only adds rows under the locked criteria). |
| Adopt a NEW criterion (e.g., "C6 — Persona-layer routing trust") to justify additional rows | Anti-churn violation (ADR-115 §3): adding criteria without S109-equivalent VETO-floor + Codex Pair-Rail iter-5 ACCEPT is doctrine-drift. All Wave A.1 rows fit the existing 5-criteria framework; no new criterion needed. |
| Defer to PLAN-094 (sentinel session cache) or PLAN-095 (PLAN-084 final closure) instead of PLAN-089 | PLAN-089 master plan explicitly scoped Wave A as "kernel extension v2"; PLAN-094 and PLAN-095 have different acceptance criteria. Cross-plan reassignment would require plan-frontmatter changes that haven't been Codex-R2-reviewed at this scope. |

## §9. Implementation

The following files land in the Wave A.4 atomic ceremony commit:

- `.claude/hooks/check_arbitration_kernel.py` — extend `_KERNEL_PATHS`
  list with the deployed N rows (Wave A.4 ceremony under
  `CEO_KERNEL_OVERRIDE`).
- `.claude/hooks/tests/test_check_canonical_edit_kernel_v2.py` —
  Wave A.5 parametrized test, one row per new entry (asserts
  HARD-DENY fires on Edit/Write/MultiEdit attempt to each path AND
  ALLOW fires on identical attempt with both override env vars set).
- `.claude/plans/PLAN-089/wave-a4-kernel-extension-v2-sentinel/round-1/approved.md` +
  `.../approved.md.asc` — Wave A.4 sentinel + detached GPG.
- `scripts/local/historical/OWNER-CEREMONY-PLAN-089-WAVE-A.sh` —
  Wave A.3 ceremony script (applies extension delta + status flip
  in single atomic commit).
- `.claude/adr/ADR-116-AMEND-1-kernel-extension-v2.md` (this file,
  post-git-mv from staging location) — flips `status: PROPOSED →
  ACCEPTED` + populates `accepted_at` + `accepted_by`.
- `.claude/scripts/tests/perf/test_kernel_hard_deny_microbench_v2.py` —
  re-baselined microbench artifact (extends ADR-116 §6 microbench
  to the new entry count).

## §10. Anti-regression

Closeout commit (Wave A.4 ceremony OR PLAN-089 v1.23.0 tag closeout)
MUST include:

1. **`_KERNEL_PATHS` count assertion.** Add to
   `.claude/hooks/tests/test_kernel_subsumes_security_critical_lib.py`:

   ```python
   def test_post_plan_089_count() -> None:
       """Post-PLAN-089 Wave A.4: _KERNEL_PATHS must contain at least
       30 + 30 (deployable subset) or 30 + 65 (full set) entries
       depending on the deployed delta. Read the deployed count from
       the Wave A.4 ceremony artifact JSON; assert exact match.
       """
       from check_arbitration_kernel import _KERNEL_PATHS
       deployed = _read_ceremony_artifact_deployed_count()
       assert len(_KERNEL_PATHS) == 30 + deployed
       assert deployed in (30, 65)
   ```

2. **ATLAS binding.** Confirm `kernel_extension_v2_landed` audit
   event emitted at Wave A.4 ceremony carries ATLAS `T1556` (Modify
   Authentication Process) binding in `_lib/audit_emit.py` /
   `_ATLAS_REGISTRY` per the PLAN-088 W1 +6 ATLAS pattern. If not
   yet registered, Wave A.5 adds the binding under the SAME
   ceremony `CEO_KERNEL_OVERRIDE` scope.

3. **Test parametrize sweep.** Verify
   `test_check_canonical_edit_kernel_v2.py` parametrize list matches
   `_KERNEL_PATHS` post-extension entries exactly (no missing rows,
   no extra rows). Mechanical via:

   ```python
   def test_parametrize_matches_kernel_paths() -> None:
       from check_arbitration_kernel import _KERNEL_PATHS
       from test_check_canonical_edit_kernel_v2 import _NEW_KERNEL_ENTRIES
       new_set = set(_KERNEL_PATHS) - _BASELINE_30_ENTRIES
       assert new_set == set(_NEW_KERNEL_ENTRIES)
   ```

4. **Microbench artifact retention.** Wave A.4 microbench JSON
   artifact committed at
   `.claude/scripts/tests/perf/test_kernel_hard_deny_microbench_v2_baseline.json`
   (read-only post-commit; future amendments re-baseline against
   this artifact per ADR-116 §6 "Re-baseline trigger" clause).

5. **PLAN-089 progress log entry.** Wave A.4 closeout updates
   PLAN-089 progress log §11 with deployed-count + microbench
   ratios + Codex Pair-Rail thread ID + sentinel SHA.

## §11. Authorization

ADR-116-AMEND-1 is a doctrine ADR (documentation-only at the file
level); the runtime artifact (the `_KERNEL_PATHS` extension in
`check_arbitration_kernel.py`) is the canonical enforcement moment.
Acceptance ceremony is the PLAN-089 Wave A.4 atomic commit signed
by Owner GPG `00000000…`.

This amendment DOES require `CEO_KERNEL_OVERRIDE` AND
`CEO_KERNEL_OVERRIDE_ACK` env tokens because:

- The kernel-edit operation itself (modifying
  `check_arbitration_kernel.py:_KERNEL_PATHS`) is a kernel-path
  edit (the file is in `_KERNEL_PATHS` per ADR-116 entry-list
  baseline) — circular self-protection requires explicit override.
- The destination path of this AMEND-1 file
  (`.claude/adr/ADR-116-AMEND-1-kernel-extension-v2.md`) lands
  under `.claude/adr/**` which is canonical-edit-guarded; the
  staging-to-canonical `git mv` is itself a guarded operation.

This is the SAME ceremony discipline as ADR-116 original
(Wave 0 atomic ceremony with kernel-override env tokens), per
the precedent established by S109 commit `4301127` and confirmed
by S111 `aa3690f` (Wave E.2 +3 entries closeout).

## §12. Related work

- **ADR-116** — KERNEL HARD-DENY tier-0 scope extension (original,
  2026-05-12). This amendment narrows §5 Entry list by ADDING ROWS
  under the locked §5 inclusion criteria. §4 Options + §5 Criteria
  + §6 Performance ceiling are UNCHANGED.
- **ADR-117** — ADR-ID collision rename policy. This amendment is
  filename `ADR-116-AMEND-1-kernel-extension-v2.md` per §3 amendment
  pattern (slug `kernel-extension-v2` distinct from parent slug).
- **ADR-115** — post-SOTA maintenance-mode doctrine. This amendment
  is in-scope per ADR-115 §4 "amendment to ACCEPTED ADR that adds
  rows under locked criteria" carve-out (no new criteria proposed;
  no ADR churn).
- **ADR-040-AMEND-2** — credential-blocking trust root (precedent
  style for this amendment; same author + same atomic-ceremony
  pattern + same `amendment_of` / `amends_section` frontmatter
  shape).
- **ADR-052** — VETO-floor archetypes (security-engineer +
  identity-trust-architect + threat-detection-engineer VETO
  authority on this amendment).
- **ADR-093** — canonical-guard moratorium retract +
  kernel-override discipline (precedent for explicit kernel-override
  env token discipline).
- **ADR-107** — Codex MCP Pair-Rail asymmetric VETO matrix (this
  amendment's review subject to ACCEPT verdict).
- **ADR-108** — Codex Pair-Rail dispatcher protocol.
- **ADR-114** — egress-redact symmetry (entry #12 +#31 trust root
  dependency).
- **ADR-119** — kernel boundary modulus (PLAN-086 §I.1) — UNLOCK
  regex per role; this amendment respects the regex (Wave A.4
  ceremony script DOES match the canonical `UNLOCK=PLAN-089-WAVE-A-*`
  pattern).
- **PLAN-084 R-026 / F-C2-002 / F-C2-008** — driver findings (the
  33-file kernel-coverage backlog originally identified by the
  SOTA-finalization audit).
- **PLAN-089 Wave A.1** — enumeration source-of-truth
  (`.claude/plans/PLAN-089/kernel-extension-v2-enumeration.md`).
- **PLAN-089 Wave A.4** — ceremony commit (this amendment ACCEPTED
  + `_KERNEL_PATHS` extension landed atomically).
- **PLAN-089 Wave A.5** — parametrized test
  (`test_check_canonical_edit_kernel_v2.py`).
- **PLAN-089 plan target** — v1.23.0 tag closeout.

## §13. Enforcement commit

This amendment ADR is documentation-only. The runtime enforcement
artifact (the `_KERNEL_PATHS` extension wiring) ships at the
PLAN-089 Wave A.4 ceremony commit. Both SHAs (the ADR file ACCEPTED
flip + the `_KERNEL_PATHS` extension) recorded in PLAN-089 progress
log §11 in the same row (atomic ceremony).

The microbench artifact
(`test_kernel_hard_deny_microbench_v2_baseline.json`) ships in the
SAME commit. The PLAN-089 v1.23.0 tag references this commit as the
Wave A closure SHA.
