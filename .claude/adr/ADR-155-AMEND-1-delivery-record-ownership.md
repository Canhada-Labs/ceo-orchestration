# ADR-155-AMEND-1 — Framework ownership derives from the REGISTERED DELIVERY; SPEC/v1 joins the upgrade surface (forced route); root VERSION stays out — deliberately


---
adr_id: ADR-155-AMEND-1
title: Install/upgrade ownership model — every conditional framework-owned entry (PROTOCOL.md, SPEC/v1, .claude/.framework-version) derives from the registered delivery record, never from ceremony alone or file presence; SPEC/v1 gets a FORCED refresh route with pristine-content legacy migration; the root VERSION is exempt from upgrade forever
status: ACCEPTED
amends: ADR-155
proposed_at: 2026-08-05
proposed_by: CEO (PLAN-166 F3 — ADR-103 re-pass NO-GO finding on v1.3.0-rc.1; debate rounds r6/r7/r8/r9/r13/r17/r19/r20)
session_origin: 2026-08-05 (S295, W1 ceremony pack)
accepted_at: 2026-08-05
authorization: PLAN-166 W1 Owner-GPG ceremony — this file reaches the canonical tree ONLY via that ceremony; a landed copy implies the gate fired
risk_tier: A
debate_required: true
debate_record: .claude/plans/PLAN-166/debate/ (3 rounds, 3 scoped VETOs raised and LIFTED with literal verification) + codex pair-rail 20 rounds (~55 findings applied)
related_plans: [PLAN-138, PLAN-153, PLAN-161, PLAN-166]
related_adrs: [ADR-155]
---

## §1 What this amendment changes

ADR-155 built the baseline-manifest engine on one shared enumeration
(`scripts/_framework_manifest_set.sh`) and enumerated the root
`PROTOCOL.md` **unconditionally** (decision (i)). The v1.3.0-rc.1 re-pass
(PLAN-166 finding F3) showed that unconditional — or ceremony-only —
enumeration is itself an ownership defect, and that `SPEC/v1` (shipped by
`install.sh` since PLAN-087 but never enumerated, never refreshed) had
become a stale, unwatched contract on every upgraded adopter. This
amendment decides four things:

1. **The delivery-record ownership rule (general).** Every CONDITIONAL
   entry of the framework-owned enumeration — `PROTOCOL.md`, `SPEC/v1`
   and the new `.claude/.framework-version` marker — derives from the
   **registered delivery**, never from the ceremony alone and never from
   file presence (§3).
2. **`SPEC/v1` joins the upgrade surface via a FORCED route** — not the
   generic `backup_and_replace` classified walk — with a deterministic
   pristine-content migration for v1.2-and-earlier legacy installs (§4).
3. **`.claude/.framework-version`** becomes a tracked file of the
   framework repo, written explicitly on install (`install_one`,
   skip-if-exists) and force-refreshed + read-back-validated on upgrade;
   marker-first readers consult the SAME delivery record before trusting
   it (§5).
4. **The root `VERSION` file stays OUT of the upgrade surface and OUT of
   the enumeration — permanently and deliberately** (§2). This section
   exists so the next maintainer does not "fix" the asymmetry and reopen
   the class.

## §2 Why root VERSION is exempt — do not repair this asymmetry

`install.sh`'s `install_one` is **skip-if-exists**: on an adopter repo
that already carries its own `VERSION` (most real repos version
themselves), the framework **never wrote that file**. Any upgrade-side
refresh of `VERSION` — `backup_and_replace` or a forced route — would
therefore TAKE an adopter-owned file. That is not hypothetical: it is the
exact shape of the S238 acme data-loss ("the verified worst case" in
ADR-155's own words), and the baseline classifier would *confirm* the
clobber rather than prevent it, because the recorded baseline would hash
the framework's value (trap C.5, documented inside
`_framework_manifest_set.sh`).

So the asymmetry is: **every other framework-derived surface refreshes on
upgrade; `VERSION` does not, ever.** The consequence — the root `VERSION`
of an upgraded adopter reports the ORIGINAL install version forever — is
absorbed by the marker (§5) and named in `INSTALL.md` (the forensic-anchor
section now prefers `.claude/.framework-version` with a `VERSION`
fallback). A future maintainer who notices "upgrade refreshes the marker
but not VERSION — inconsistent!" is looking at a decided invariant, not an
oversight. Reopening it requires amending THIS amendment.

Inside the framework repo itself nothing changes: every framework-repo
gate (`check-canonical-doc-freshness.py`, `verify-counts.sh`,
`check_tier_a_spec_version_drift`) keeps reading `VERSION` as the
authority. The marker-first preference is exclusive to readers operating
on an ADOPTER tree — today, `.claude/scripts/check-framework-updates.sh`
(without it, the checker re-reads the stale root `VERSION` post-upgrade,
exits `behind-minor` and demands the same upgrade in an eternal loop —
r8). `check_tier_a_npm_version_match` deliberately does NOT adopt the
marker: in an adopter tree the root `package.json` is the APP's, and
comparing the framework marker against the app version would be a
permanent false-red; that check keeps its VERSION×package.json semantics
(or skips when VERSION is absent).

## §3 The delivery-record ownership rule

**"Delivered" means REGISTERED ACTUAL DELIVERY, not ceremony (r17), and
not file presence (r7/r13):**

- A `--ceremony user` install SKIPS `install_spec_v1`,
  `install_version` and `install_protocol_pointer` (WS4 guards). If the
  enumeration emitted those paths unconditionally,
  `write_install_manifest` would hash the ADOPTER's own `SPEC/v1` or root
  `PROTOCOL.md` as framework-owned — and a later `uninstall.sh` (which
  removes manifest-recorded, hash-matching files) could DELETE the
  adopter's files (r7/r13).
- Ceremony-conditional enumeration is still not enough: on a
  `maintainer` install where the destination ALREADY had its own
  `SPEC/v1`, `install_one` EXISTS-skips — the file on disk is the
  adopter's, under a maintainer ceremony (r17).

Mechanics (both writers, one reader):

- `install.sh` flips `_DELIVERED_{SPEC,PROTOCOL,MARKER}` only where the
  write ACTUALLY happened (`install_one` reports COPIED/LINKED via
  `INSTALL_ONE_WROTE`; the pointer heredoc sets the flag on its own write
  path, unreachable from the pre-existing early-return), journals a
  `delivered_*` op into `.install-state.json`, and exports the flags as
  `FMS_DELIVERED_*` to the shared enumeration.
- The **baseline manifest** (`.claude/.install-manifest.sha256`) is
  thereby the persistent delivery record: it carries records for the
  three conditional paths **iff** they were delivered.
- `upgrade.sh` resolves prior ownership from the pre-upgrade baseline
  records (`_baseline_has_spec_record` / `_baseline_has_marker_record` /
  the existing `_baseline_lookup "PROTOCOL.md"`), refreshes what it owns,
  and re-exports the flags for the post-upgrade C.7 rewrite.
- `doctor.sh` resolves the SAME flags from the sanitized baseline —
  never from ceremony — before its orphan-scan enumeration: only-ceremony
  would re-include paths a user install skipped and `--strict-orphans`
  would flag the adopter's own files as orphans (r19); a blanket
  maintainer default would do the same, and a blanket user default would
  hide a delivered SPEC from a maintainer (r9 P2).
- The enumeration's fail direction is pinned: an unset flag means NOT
  enumerated. **Under-claiming ownership is recoverable (a file goes
  unwatched); over-claiming is the delete-the-adopter's-file class.**

The upgrade-side ceremony read is **replay-independent** (r9):
`upgrade.sh --no-replay` sets `REPLAY=0` and skips
`_read_install_state_request` entirely, so a ceremony that rode the
replay would silently revert a user install to maintainer under the
documented `--no-replay` flag. A dedicated `_read_install_state_ceremony`
reader always runs, validates against the closed enum
`{maintainer, user}`, and **fails open to `maintainer`** when the state
is absent/unreadable (all pre-Wave-B installs) — the pre-existing
behavior, named as a consequence in `INSTALL.md`. The same read gates
`_refresh_protocol_pointer`, which previously ran unconditionally and
`cat >`-created a root `PROTOCOL.md` that a user install deliberately
never has (the latent bug the PLAN-166 F4 tree-comparison e2e exposes).

## §4 SPEC/v1: forced route + pristine-content legacy migration

The generic route cannot carry the SPEC. For a directory target with a
baseline, `backup_and_replace` runs the per-file classified walk — which
PRESERVES adopter edits. From the **second** upgrade on (baseline then
contains SPEC records), an edited SPEC would classify ADOPTER-CUSTOMIZED
and the stale-contract failure would return (r6). The declared semantics
(OQ-3): `SPEC/v1` is the published compliance CONTRACT — an adopter edit
is a **fork of the contract**, not a customization. Three-way merge is
complexity without a consumer; refuse-and-instruct would block every
upgrade that ships a SPEC change. Hence `_refresh_spec_contract`:
framework-owned ⇒ backup whole tree to `.claude.bak/<ts>/SPEC/v1` +
replace wholesale; user-ceremony installs never receive it.

**Legacy migration (r20).** v1.2-and-earlier installs have NO delivery
record for SPEC (the enumeration never included it), so
framework-installed and adopter-authored `SPEC/v1` are indistinguishable
by record. The ambiguity resolves by CONTENT: the target tree's
fingerprint (sha256 over the `LC_ALL=C`-sorted `"<sha256(file)>  <relpath>"`
lines of every file under `SPEC/v1`) is compared against the PRISTINE
fingerprints of every SPEC/v1 the framework shipped at **v1.2.0 and
earlier** — nine tags, three distinct trees, derived deterministically
from pinned tag content (`git ls-tree` + `git show`; the derivation
command is embedded next to the constants in `upgrade.sh`):

| pristine fingerprint (sha256) | shipped by |
|---|---|
| `a4a4504a224d72a975a853dd71a75d8e678fef034a70deb49df291dbb712c161` | v1.0.0, v1.0.1, v1.0.1-rc.1 |
| `94aa62f781285ce4897ad1220edf15e97b4e9d7b629f9f7ba3389da5d45f22b1` | v1.1.0, v1.1.0-rc.1 |
| `469a49238867be181490214305b43bc7299f2bae3ef0b282a5452f6caf327f0b` | v1.2.0, v1.2.0-rc.1, v1.2.0-rc.2, v1.2.0-rc.3 |

Match ⇒ framework-owned (byte-identical to a shipped release; the forced
refresh loses nothing) ⇒ refresh + named NOTE. No match ⇒ ADOPTER-FORK ⇒
**preserve in place** + snapshot to `.claude.bak/<ts>/SPEC/v1` + named
WARNING with the hand-refresh instruction. A partial/unhashable tree
never produces a fingerprint (fail toward preserve). Both legacy cases
are fixtures; the pristine-match branch is additionally exercised
end-to-end by the F4 install-v1.2.0→upgrade comparison job.

## §5 The marker: forced+validated write, record-gated readers

`.claude/.framework-version` is a **tracked file of the framework repo**
(one line, byte-identical to `VERSION`) — not generated-only-at-destination,
so the release protections are real and unconditional: the version bump
writes it as its 12th site, `verify-counts.sh` cross-checks it against
`VERSION` in every release, and `release.yml` asserts marker == VERSION
fail-closed. In the enumeration it is a NORMAL file entry (the
`FMS_HASH_ROOT` baseline rewrite preserves it with no special-case),
conditional on delivery like the other two.

Delivery is by **explicit writes on both paths** (the enumeration never
delivers — it only records; r7): `install_one ".claude/.framework-version"`
on install (skip-if-exists ⇒ a pre-existing adopter marker is NOT
delivered), and a **forced + read-back-validated** rewrite on upgrade
(differing pre-existing copy backed up first; a write that fails
validation is NOT recorded as delivered). It lives inside `.claude/`, so
both ceremonies receive it (the WS4 guard only forbids root files) and it
is committable like the rest of `.claude/`.

**Every marker-first reader consults the SAME record** (r20):
`check-framework-updates.sh` trusts the marker only when the baseline
manifest carries its delivery record, else falls back to `VERSION` — on a
target where the marker pre-existed and was skipped, an unconditional
read would report a stale version in a loop.

## §6 Enforcement

- `scripts/tests/test-upgrade-spec-ownership.sh` — record-owned forced
  refresh with backup (the 2nd-upgrade scenario), user-ceremony +
  `--no-replay` skip, legacy adopter-fork preserve, marker delivery +
  pre-existing-marker fallback, doctor orphan-scan in both modes,
  update-checker no-loop regression (AC-3).
- The PLAN-166 F4 e2e (`smoke-install.yml`) compares install-built vs
  upgrade-built trees per ceremony mode; its historical leg
  (install v1.2.0 → upgrade) exercises the pristine-match migration.
- `_framework_manifest_set.sh`, `install.sh`, `upgrade.sh` remain
  `_CANONICAL_GUARDS` surfaces; this amendment's edits land only via the
  PLAN-166 W1 Owner-GPG ceremony.

## Consequences

- **(+)** A `--ceremony user` install can never have its own `SPEC/v1`,
  root `PROTOCOL.md` or marker inventoried as framework-owned — closing
  the uninstall-deletes-adopter-files corridor (r7/r13/r17).
- **(+)** Upgraded adopters get a fresh SPEC contract every upgrade, with
  fork preservation and a deterministic legacy migration.
- **(+)** Post-upgrade version reporting is truthful (marker), without
  ever touching the adopter's root `VERSION`.
- **(−)** Pre-Wave-B installs (no `.install-state.json`) are treated as
  `maintainer` on upgrade — fail-open, named in `INSTALL.md`; a user-mode
  pre-Wave-B adopter must re-run `install.sh --ceremony user` once to
  record the ceremony.
- **(−)** The delivery record inherits the baseline manifest's trust
  class: target-side, UNSIGNED, advisory (ADR-155 Consequences). A
  tampered record can add/remove ownership — the fail direction on a
  MISSING record is preserve/fallback (today's behavior), never a new
  escalation.
- **(~)** An adopter whose fork of `SPEC/v1` is byte-identical to a
  shipped release is claimed as framework-owned by the legacy migration —
  accepted: the forced refresh is content-preserving up to the shipped
  bytes they already had.
