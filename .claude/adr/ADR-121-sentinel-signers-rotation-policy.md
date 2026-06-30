---
id: ADR-121
title: Sentinel signers rotation policy — hot/cold split + M-of-N quorum + revocation channel
status: ACCEPTED
created: 2026-05-13
proposed_by: CEO (PLAN-089 Wave C.1)
veto_floor: ADR-052
supersedes: []
amends: []
related: [ADR-040, ADR-040-AMEND-2, ADR-049, ADR-052, ADR-064, ADR-113, ADR-115, ADR-116, ADR-116-AMEND-1, ADR-117]
plan: PLAN-089
accepted_at: 2026-05-20
accepting_session: S147
---

# ADR-121 — Sentinel signers rotation policy

<!--
DRAFT STAGING LOCATION NOTE (not part of ADR body):
This file is the Wave C.1 deliverable, staged at
`.claude/plans/PLAN-089/wave-c1-adr-121-draft.md` because the parent
agent's auto-mode classifier denied a sub-agent attempt to write
directly to `.claude/adr/ADR-121-...md` (kernel-protected ADR path).
Parent agent should `git mv` this file to
`.claude/adr/ADR-121-sentinel-signers-rotation-policy.md` at the Wave C
ceremony commit, under `CEO_SENTINEL_UNLOCK=PLAN-089-wave-c1-adr121-draft`
+ `CEO_SENTINEL_UNLOCK_ACK=I-ACCEPT`, and delete this staging copy.
The frontmatter + body below are final-form ready; no edits needed at
move time. Strip this HTML comment block at move time.
-->

## §1 Context

The canonical-edit sentinel trust root in this framework is the
allowlist file `.claude/sentinel-signers.txt`. Today (pre-ADR-121) the
file is a flat, hard-coded list of 40-hex GPG fingerprints — one Owner
hot-key (`0000000000000000000000000000000000000000`) — with **no
metadata**: no `expires_at`, no `revoked_at`, no hot/cold role split,
no quorum threshold, no recovery channel.

`check_canonical_edit.py` reads the file at hook invocation, treats
every line as a valid signer if a sentinel `.asc` verifies against any
listed fingerprint, and emits no per-key lifecycle telemetry. The file
itself is now a tier-0 KERNEL HARD-DENY path per ADR-116 entry #12
(C2 + C3 + C4 — cryptographic-trust ledger).

**The chicken-and-egg recovery hole.** If the Owner hot-key is
compromised, the only on-disk recovery action is to direct-edit
`sentinel-signers.txt`. But the file is in `_KERNEL_PATHS` (entry #12
post-ADR-116), so the edit requires a `CEO_KERNEL_OVERRIDE` ceremony
plus an `approved.md.asc` sentinel — and the canonical-edit hook will
only accept that sentinel if it is signed by a fingerprint already on
the allowlist. The compromised key is the only such fingerprint. The
attacker, having stolen the key, can sign the override sentinel
themselves; the legitimate Owner, having lost exclusive control of the
key, cannot revoke it without first signing with it. There is no
out-of-band recovery channel.

**Forcing functions cited from PLAN-084 SOTA-finalization audit:**

- **R-028** — "sentinel-signers.txt has no rotation policy, no expiry,
  no revocation, no cold-key recovery doctrine" (capability-gap-report
  §axis-5 identity-trust).
- **F-C2-007** — single-edit catastrophic chain: stolen hot-key →
  forged sentinel → arbitrary kernel-path edit → full framework
  takeover. Veto case D defense-in-depth gap.
- **A.IDA-T-0004** — identity-trust archetype P0 finding: no per-signer
  expiry metadata; framework cannot mechanically distinguish a
  current-Owner key from a 5-year-old retired key still on disk.

PLAN-089 Wave C.1 specifies this ADR as the policy artifact; Waves
C.2–C.6 implement the runtime hook + registry + audit events + Owner
ceremony. Wave C is gated on this ADR reaching `status: ACCEPTED`
(plan-level AC5).

ADR-115 maintenance-mode boundary clause #1 (P0 security findings →
PLAN-085+ burn-down) authorises the in-scope debate; no scope creep
beyond sentinel-signer lifecycle. ADR-115 §exception-1 explicitly
admits post-SOTA P0 closure plans; PLAN-089 Wave C is one such closure.

## §2 Decision

Adopt a **hot-key / cold-key split with M-of-N quorum and explicit
revocation channel**, materialised in a new canonical source
`.claude/security/sentinel-signers-registry.yaml`. The flat
`sentinel-signers.txt` becomes a generated artifact derived from the
YAML registry.

**Roles:**

- **Hot-key** — single Owner GPG fingerprint used for daily sentinel
  signing (canonical-edit drafts, plan promotions, ceremony commits).
  Lives on the Owner workstation. Expires at most 12 months after
  `created_at`.
- **Cold-keys** — N=3 GPG fingerprints used **only** for
  registry-mutation quorum and hot-key recovery. Each lives OFFLINE
  (paper backup or HSM) at a **geographically separated** location.
  Owner-physical access required. Expires at most 60 months after
  `created_at`.

**Quorum threshold:** `M=2 of N=3` minimum for any registry mutation
(hot-key rotation, hot-key revocation, cold-key replacement). This
threshold is fixed; reducing it below 2-of-3 requires a NEW ADR with
ADR-052 VETO-floor consensus.

**Why M=2-of-N=3 and not M=2-of-N=2** (R1 IDA P0 fold, locked at plan
draft): a 2-of-2 cold-key scheme means both keys are required and
both keys are sufficient. If the Owner laptop is compromised AND the
home safe is burgled in the same window, the attacker holds the full
quorum and can perform a kernel takeover with no on-disk trace. With
N=3, the Owner can store cold-key #3 at a third geographically
separated location (bank deposit box, family member, or off-continent
escrow); a single laptop + single safe compromise yields only 1-of-3
— below threshold — and the attacker cannot mutate the registry
without also compromising the third site. This is the ONLY
configuration that closes the F-C2-007 single-edit chain under the
realistic threat model of solo-operator-under-physical-duress. 2-of-3
also tolerates a single cold-key LOSS (lost paper, HSM failure)
without locking the Owner out of recovery — 2 surviving keys still
meet quorum.

**Per-key lifecycle metadata** (R1 IDA P0 fold):

- `key_id` — 40-hex uppercase GPG fingerprint
- `role` — `hot` or `cold`
- `cold_key_index` — `1`, `2`, or `3` (cold only; null for hot)
- `created_at` — ISO-8601 UTC
- `expires_at` — ISO-8601 UTC (12mo hot / 60mo cold maximum)
- `revoked_at` — ISO-8601 UTC or `null` (R1 IDA P0 fold: REQUIRED
  separate channel from expiry; revocation reason free-text per
  `revoked_reason`)
- `revoked_reason` — free-text or `null`
- `geographic_location_hint` — opaque label (`workstation`,
  `home-safe`, `bank-deposit-box`, `escrow-N`); never the literal
  address (audit-log exposure)

A signer is **valid** iff `revoked_at IS NULL AND expires_at > now()`.
Both clauses are mandatory. Expiry alone is insufficient — a stolen
key that has not yet expired must be revoked through the explicit
channel, not silently waited out.

## §3 Hook-level verify

A new stdlib-only module `.claude/hooks/_lib/sentinel_signers.py`
encapsulates the validity check. `check_canonical_edit.py` ceases to
read `sentinel-signers.txt` directly; it imports and calls
`is_valid_signer(key_id, now)` instead.

```python
# .claude/hooks/_lib/sentinel_signers.py (sketch — full impl Wave C.2)

def is_valid_signer(key_id: str, now: datetime) -> Tuple[bool, str]:
    """
    Returns (valid, reason_code).
    reason_code is empty string when valid; one of
    {"unknown", "expired", "revoked", "registry_missing",
     "registry_unverified"} when invalid.
    Re-parses .claude/security/sentinel-signers-registry.yaml on EVERY
    call — NO cache in v1.x (see §6).
    """
    registry = load_registry()  # raises RegistryUnverified if YAML
                                # signature check fails
    rec = registry.get(key_id)
    if rec is None:
        return (False, "unknown")
    if rec.revoked_at is not None:
        return (False, "revoked")
    if rec.expires_at <= now:
        return (False, "expired")
    return (True, "")


def quorum_verify(
    signatures: List[Signature],
    threshold: int = 2,
) -> Tuple[bool, str]:
    """
    For registry-mutation paths: verify >=threshold distinct
    VALID cold-key signatures cover the artifact.
    Returns (met, reason_code).
    """
    ...
```

**R1 IDA P0 fold:** revocation must propagate the moment the YAML is
edited. The hook re-parses on every invocation precisely so that a
revocation committed at T=0 is in force at T=0+1ms for the next hook
fire. No 5-minute cache, no in-process memo. This is the single
biggest reason we eat the YAML parse cost on every hook (see §6 for
the v2.0+ caching contract that preserves this property).

## §4 Chicken-and-egg doctrine

The recovery hole described in §1 is closed by **geographic separation**
of cold-keys (R1 IDA P0 fold). The doctrine:

- Cold-key #1, #2, #3 are generated at distinct Owner-physical
  ceremonies and immediately written to OFFLINE media (paper backup
  in the simple case; HSM in the future-hardened case).
- The three media are stored at **three geographically separated
  locations**. The minimum acceptable configuration is workstation
  safe at home, bank deposit box, off-site escrow. The bank deposit
  box and the off-site escrow MUST NOT be on the same postal address;
  co-located cold-keys defeat the geographic diversity property and
  reduce the scheme to effectively 2-of-N.
- The Owner-physical recovery ceremony requires **2 of 3** cold-keys
  present at the same time and place to sign the registry mutation.
  This is the rare-event ceremony — projected at most twice per year
  (annual hot-key rotation + once-per-incident recovery).

**Threat-model scenarios:**

| Scenario | Outcome |
|---|---|
| **Hot-key compromise** (stolen laptop, lifted from RAM, phished). | Attacker can sign daily sentinels but cannot mutate the registry alone. Owner travels to 2 of 3 cold-key sites, signs a revocation tx (set `revoked_at`, `revoked_reason="compromise"`) plus a hot-key replacement entry, commits the registry mutation under M=2-of-N=3 quorum sentinel. Time-to-recovery: hours to a small number of days (transit + safe access). Audit trail: `sentinel_signer_revoked` + `sentinel_signer_rotated` events emitted at the recovery commit. |
| **Single cold-key compromise** (one safe burgled, one HSM lost). | Below quorum — attacker holds 1 of 3 and cannot mutate the registry. Owner uses the remaining 2 cold-keys to revoke the compromised cold-key and provision a replacement at a fresh geographic site. The framework keeps operating on the hot-key in the interim; no service disruption. |
| **Quorum cold-key compromise** (2 of 3 sites breached in the same window). | This is the catastrophic failure mode. Attacker holds quorum and can mutate the registry — including revoking the surviving cold-key and adding their own. Mitigation is exclusively prevention: geographic separation must be real (different postal codes, different jurisdictions if possible); ceremony attendance must use distinct travel windows so a single coordinated physical attack cannot capture two sites simultaneously. The framework provides no recovery from this scenario — at this point the Owner must rebuild the registry from scratch via a forked repo with hand-distributed trust, accepting the resulting fork as the new canonical line. ADR-115 maintenance-mode does not authorise expanding scope to in-band recovery from full quorum compromise. |
| **Owner death / incapacity.** | The framework provides no built-in succession. Cold-key locations + the recovery procedure should be documented out-of-band by the Owner in their personal continuity-of-operations plan. The framework's only role is to make the cold-keys mechanically equivalent to any other cold-keys — a successor with quorum cold-key control can rotate the hot-key and continue. This is documentation-only; no in-framework artifact tracks succession. |
| **Geographic correlation** (e.g. two cold-keys in the same building, even different floors). | Defeats the scheme. The §4 ceremony documentation MUST enumerate the three physical locations and assert they are not co-located. Owner certifies geographic separation at every cold-key rotation ceremony. False certification is outside the framework's mechanical detection scope; this is an Owner-discipline floor, not a hook-enforced gate. |

## §5 Migration + bootstrap

The flat `sentinel-signers.txt` is **retired as the canonical source**
but retained on disk as a GENERATED artifact (regenerated from the YAML
registry at every Owner ceremony). Existing consumers that read the
text file continue to work without modification during the transition;
the canonical-edit hook switches to the new module per §3.

**New canonical source:** `.claude/security/sentinel-signers-registry.yaml`.
The file is itself a kernel-tier path (added to `_KERNEL_PATHS` in
ADR-116-AMEND-1 alongside ADR-121 ceremony).

**GENESIS first-write (R1 Sec P0 + IDA P0 fold — chicken-and-egg
loop closure):** the first commit that creates the registry YAML
requires **joint signature by the existing hot-key AND cold-key #1**.
Two detached `.asc` files at the same commit, both verifying against
the same YAML bytes. A single-key first-write is REJECTED by the hook
with `reason_code=genesis_requires_joint_signature`. This closes the
single-key trust-root mutability gap: even at GENESIS, the hot-key
alone cannot establish the initial trust anchor.

After GENESIS, the hot-key never again signs a registry mutation;
all subsequent edits require cold-key 2-of-3 quorum sentinel (NOT
hot-key alone — closes single-key trust-root mutability post-genesis).
The hot-key continues to sign daily canonical-edit sentinels for
non-registry paths.

**Existing hot-key as GENESIS hot:** the current Owner fingerprint
`0000000000000000000000000000000000000000` is grandfathered as the
GENESIS hot-key with `created_at=2026-04-20` (Owner's documented key
creation date per `sentinel-signers.txt` comment line 23) and
`expires_at=2027-05-13` (12 months from this ADR's `created` date
per the §2 hot-key max-age clause). Cold-keys #1/#2/#3 are generated
fresh at the PLAN-089 Wave C.6 Owner ceremony — no legacy cold-key
material exists pre-ADR-121.

**`_BOOTSTRAP_REGISTRY_SHA256` constant:** a 64-hex SHA256 of the
GENESIS registry YAML is baked into `check_canonical_edit.py` source
as a module-level constant. On every hook invocation, the hook
verifies the on-disk registry matches the baked constant before
calling `load_registry()`. This closes the cold-start integrity
problem: if an attacker swaps the YAML file for a malicious version
before the first hook-fire of a session, the constant mismatch
detects it and the hook fails-CLOSED with
`reason_code=bootstrap_sha_mismatch`.

The bootstrap constant rotates only when the registry's signing set
itself rotates (e.g. a cold-key is replaced). Rotation of the constant
is a KERNEL HARD-DENY path edit (the hook source file is in
`_KERNEL_PATHS` entry #4) — ADR-116-AMEND-1 documents the ceremony
flow; this ADR does not duplicate it.

## §6 Revocation propagation

**Re-parse on every hook invocation; NO cache in v1.x scope.** The
`load_registry()` call in `is_valid_signer()` reads the YAML, parses
it, and verifies its `.asc` sentinel on every single hook fire. The
projected per-call overhead is ~3-5ms for a registry with N ≤ 8 keys
(measured at the C.2 microbench harness; see plan AC8c). This is
within the aggregate PreToolUse budget of 15ms documented in ADR-116
§6 perf ceiling.

The rationale (R2 Codex iter-2 P1 fold, disambiguated): a cached
registry creates a revocation-propagation race. If the cache TTL is
T seconds, then any compromised-key sentinel signed within T seconds
after the revocation commit lands as accepted. T=0 is the only safe
TTL in v1.x.

**If a cache is introduced in v2.0+**, the cache key composition MUST
be `(path, inode, mtime_ns, file_size, sha256)` minimum, per the
PLAN-091 Wave C precedent for sentinel cache invalidation. mtime
alone is insufficient (clock resync attacks); inode + sha256 forces
content-equality not just stat-equality. The v2.0+ cache contract is
out of scope for this ADR; PLAN-089 ships the v1.x no-cache form.

**Audit emit (R1 IDA P0 fold + R1 TDE P0 fold):** five new actions are
registered in `_lib/audit_emit.py` (Wave C.5):

- `sentinel_signer_rotated` — registry mutation success: a hot-key or
  cold-key entry was added/replaced.
- `sentinel_signer_expiry_warned` — fires 60 days before `expires_at`
  (advisory; gives Owner runway to schedule rotation ceremony).
- `sentinel_signer_revoked` — explicit revocation channel (R1 IDA P0
  fold — SEPARATE from `_rotated`; revocation is forensically distinct
  from end-of-life rotation and must be queryable independently for SOC
  consumption).
- `sentinel_signer_quorum_failed` — fires on quorum-short mutation
  attempt (R1 TDE P0 fold — without this event, cold-key compromise
  is undetectable until a successful rotation reveals the attacker
  tried earlier; quorum-failed is the canary).
- `sentinel_signer_quorum_attempted` — fires on every quorum attempt
  regardless of outcome (R1 IDA P2 fold — forensic completeness; lets
  the audit log distinguish "attacker probed quorum 47 times and
  finally succeeded" from "Owner did one clean rotation").

**Same-second revocation propagation test (R1 QA P0 fold):** the test
suite (`test_sentinel_signers.py`) MUST include a case where the YAML
is mutated to set `revoked_at` and `is_valid_signer()` is called in
the same second. The test asserts the second call returns
`(False, "revoked")` — proves the no-cache contract holds at
sub-second granularity.

## §7 ATLAS / ATT&CK technique-ID binding

Audit events bind to MITRE ATT&CK technique IDs in `_ATLAS_REGISTRY`
per PLAN-088 ADR-118 pattern. Bindings for the five new actions:

| Audit action | ATT&CK technique | Rationale |
|---|---|---|
| `sentinel_signer_rotated` | **T1556** (Modify Authentication Process) | Adds/replaces an authenticator in the trust root. Even legitimate rotations match the technique mechanically — taxonomy correctness, not attribution. |
| `sentinel_signer_revoked` | **T1556** | Same technique class; the event is the revocation half of the auth-process modification cycle. |
| `sentinel_signer_quorum_failed` | **T1556** | Failed authenticator modification — the attempted technique was T1556 even though the attempt was blocked. |
| `sentinel_signer_quorum_attempted` | **T1556** | Forensic completeness wrapper; same technique class. |
| `sentinel_signer_expiry_warned` | **T1556** | Advisory event tied to the same lifecycle surface; bound for consistency in SOC dashboards. |

**Cross-scenario bindings** (referenced from §4 threat model, not
emitted as direct events):

- Cold-key compromise scenarios — **T1584** (Compromise
  Infrastructure). T1584 covers attacker takeover of trust-anchor
  infrastructure including credential/key compromise; this is the
  correct binding for the physical theft of a cold-key.
- Sentinel forgery via canonical file manipulation — **T1565.001**
  (Stored Data Manipulation). Direct edit of `sentinel-signers.txt`
  or `sentinel-signers-registry.yaml` to inject an attacker key
  matches T1565.001's modifying-stored-data-to-manipulate-trust-decisions
  pattern.

**Explicitly NOT applicable** (R2 Codex iter-1 P1 fold — taxonomy
correction; superseded earlier draft references):

- **AML.T0018** (Backdoor ML Model) — no ML model artifact is
  mutated in any cold-key compromise scenario. The cold-key is a
  cryptographic credential, not a model.
- **AML.T0048.004** — same rationale; AML.T0048 family is restricted
  to ML model artifact manipulation. Cold-keys are out of scope for
  AML taxonomy regardless of analogical resemblance to model signing.
  Bind to T1584 instead.

## §8 Acceptance criteria

This ADR is the policy artifact for PLAN-089 Wave C. The plan-level
ACs that are ADR-121-scoped (per §5 of PLAN-089):

- **AC3** — `_lib/sentinel_signers.py` exports `is_valid_signer` and
  `quorum_verify` (Wave C.2 deliverable; verified mechanically via
  `python3 -c "from sentinel_signers import is_valid_signer,
  quorum_verify"`).
- **AC4** — `sentinel-signers-registry.yaml` exists and is jointly
  signed by the hot-key + cold-key #1 at GENESIS (R1 IDA P0 fold
  genesis joint-signature; verified by `gpg --verify` of BOTH `.asc`
  files yielding GOOD signatures against the same YAML bytes).
- **AC5** — ADR-121 reaches `status: ACCEPTED` (this artifact;
  verified by `grep` for ACCEPTED status in this file post-ceremony).
- **AC6** — the five new audit events are registered in
  `_lib/audit_emit.py:_KNOWN_ACTIONS` (verified by grep).
- **AC9** — Codex MCP R2 ACCEPT on the consolidated PLAN-089 Wave C
  diff (cross-LLM VETO-floor per ADR-108).
- **AC10** — Wave D anti-regression suite passes; specifically the
  test case asserting `sentinel-signers.txt` legacy callers still
  resolve correctly through the new module (no silent breakage of
  unrelated callsites).

The remaining plan-level ACs (AC1/AC2 kernel scope; AC7 CI subset;
AC8a-c microbench) are Wave A and Wave B scoped and not blocked on
this ADR's content.

## §9 Risks + alternatives considered

| Alternative | Why rejected |
|---|---|
| **M=2 with N=2** (no third cold-key) | Single laptop + single safe compromise yields full quorum. R1 IDA P0 fold mandates N ≥ 3 with geographic separation. Storage overhead of one extra paper backup is trivial against the catastrophic failure mode it closes. |
| **Hot-key-only registry mutability** (no cold-key quorum for post-genesis edits) | Recreates the chicken-and-egg single-edit bypass: a stolen hot-key can mutate the registry to add attacker fingerprints. R1 Sec P0 fold mandates cold-key quorum on every post-genesis registry mutation. The hot-key retains daily sentinel signing for non-registry canonical paths; only the registry itself is locked to quorum. |
| **In-memory registry cache in v1.x** | Revocation propagation race. R2 Codex iter-2 P1 fold disambiguation: any non-zero cache TTL admits a window where a compromised-key sentinel signed AFTER revocation lands as accepted. v1.x mandates re-parse on every hook fire; v2.0+ may revisit with a sha256-content-keyed cache, but that contract is outside ADR-121 scope. |
| **AML.T0018 binding for cold-key compromise** | Taxonomy error. R2 Codex iter-1 P1 fold corrected this: cold-keys are cryptographic credentials, not ML model artifacts. AML family applies to model weights and training artifacts. The correct bindings are T1556 / T1584 / T1565.001 per §7. |

## §10 Implementation

| File | Status | Wave |
|---|---|---|
| `.claude/adr/ADR-121-sentinel-signers-rotation-policy.md` | THIS FILE — new | C.1 |
| `.claude/hooks/_lib/sentinel_signers.py` | new (≥150 LoC stdlib; PyYAML-free parser) | C.2 |
| `.claude/security/sentinel-signers-registry.yaml` | new canonical source (GENESIS joint-signed) | C.3 |
| `.claude/hooks/check_canonical_edit.py` | edit — consult new module instead of flat file | C.4 |
| `.claude/hooks/_lib/audit_emit.py` | edit — register 5 new `_KNOWN_ACTIONS` + 5 ATLAS bindings | C.5 |
| `.claude/hooks/tests/test_sentinel_signers.py` | new — ≥30 cases incl. same-second revocation | C.2 |
| `scripts/local/historical/OWNER-CEREMONY-PLAN-089-WAVE-C.sh` | new — cold-key generation + GENESIS joint-sign | C.6 |

**Ceremony commit emits** `veto_triggered(reason_code=kernel_override_used)`
twice — once at the registry-genesis commit (registry path is
kernel-tier via ADR-116-AMEND-1) and once at the `check_canonical_edit.py`
patch commit (entry #4 in the base `_KERNEL_PATHS`). Both override
events visible in `audit-query.py since 24h` per ADR-116 §9 ceremony
discipline.

## §11 Open questions parked for Owner sign-off

- **Cold-key #3 geographic site selection.** The §4 doctrine requires
  three geographically separated locations and lists workstation safe,
  bank deposit box, off-site escrow as the minimum acceptable. The
  third site identity is Owner-physical and not constrained by the
  framework. Sign-off should confirm the intended third site (or
  accept "deferred to Wave C.6 ceremony day") before this ADR flips
  ACCEPTED.
- **Hot-key max-age.** §2 sets 12 months; this matches ADR-040 §4
  credential-lifecycle 90-day max for runtime credentials but is
  intentionally LONGER because Owner-physical key-replacement
  ceremonies are higher-friction than runtime credential rotations.
  Sign-off should confirm 12 months is acceptable or counter-propose.
- **Bootstrap-SHA rotation cadence.** §5 specifies the constant
  rotates only when the signing set rotates. An alternative is
  forced rotation at hot-key expiry even if no cold-key changes. The
  latter adds a ceremony step but tightens the cold-start integrity
  guarantee against year-old YAML replays. Sign-off should pick.
