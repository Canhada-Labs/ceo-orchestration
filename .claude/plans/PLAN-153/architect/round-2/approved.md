# SENT-B — PLAN-153 Wave B landing sentinel (round-2)

Drafted S261 (2026-07-07, overnight run) by the CEO under the Owner's
delegation; **inert until the Owner fills the anchor and detach-signs**
(`approved.md.asc`). Scope below is the EXACT staged-overlay file set of
`.claude/plans/PLAN-153/staged/wave-B/`.

**Landing order (STRICT): Wave E (round-1) FIRST, then Wave B.** Two files
in this scope — `scripts/install.sh` and `.github/workflows/validate.yml` —
are the SUPERSEDING copies: the wave-B staged versions CONTAIN the wave-E
content plus the wave-B additions. The wake-up ceremony applies the wave-E
overlay then the wave-B overlay in order, so wave-B's copies win; never
apply wave-E's copies of these two after wave-B's (would revert wave-B's
install-state + CI wiring). `scripts/install.sh` is a canonical guard-list
entry; the Owner-shell overlay copy is the sanctioned patcher route
(S258 precedent), the signed sentinel is the authorization record.

The plan's original SENT-B path list (PLAN-153 §Wave 0) was stale — it
omitted `.github/workflows/validate.yml` and
`scripts/tests/test_install_state_replay.sh`. This signed scope is
authoritative and matches the built overlay exactly.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs 24d2a27885405f1bcacd10a15d1dfbb4300f692a
Plans: PLAN-153
Scope:
  Wave B — installer/release lifecycle (install-state persistence + upgrade
  replay with ADR-155 back-compat fallback, doctor/repair already landed
  direct, release/npm-publish idempotency + the 2 PLAN-152 §Deferred latent
  release.yml bugs, wave-B CI wiring), landed as the complete staged overlay
  of PLAN-153/staged/wave-B/:
  - scripts/install.sh
  - scripts/upgrade.sh
  - scripts/tests/test_install_state_replay.sh
  - .github/workflows/release.yml
  - .github/workflows/npm-publish.yml
  - .github/workflows/validate.yml
<!-- END SIGNED SCOPE -->
