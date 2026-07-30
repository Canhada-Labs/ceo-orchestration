---
plan: PLAN-164
round: 1
type: architect-sentinel
segment: RAIL-TIMEOUT-UPLIFT
---

# PLAN-164 GATE-RAIL — pair-rail timeout uplift ceremony (Owner sentinel)

Anchor-SHA: d97eae2ea8391105a9e11467903f9c02b7cf9078

Approved-By: @Canhada-Labs (Owner GPG — signed inline by the ceremony)
Approved-At: 2026-07-30

## What this sentinel authorizes (sign this KNOWINGLY)

Single declared PLAN-164 ceremony (incident fix ratified S285, tie-break
OQ1-OQ4; debate round 1: 3x ADJUST -> PROCEED). Scope = the rail-pack ONLY
(`staged/rail-pack/MANIFEST.sha256`, tracked twin `inputs-rail.sha256`).
Root cause is MEASURED, not inferred (PLAN-163/probes/
GATE-V2-2026-07-29-FAIL-diagnosis.md): the default
`CEO_PAIR_RAIL_TIMEOUT_S=30` is structurally below the real latency of a
codex verdict (N=9: p95 ~75 s incl. 75.1 s under load; 12 of 12
`pair_rail_case` in the log's entire history are F/TIMEOUT — the rail
never completed a live review). This ceremony lands:

1. **Internal budget uplift (OQ1 = 120 s):** `check_pair_rail.py` env
   default `"30"` -> `"120"` + fallback/clamp-reset `30.0` -> `120.0`
   (docstring updated; `>600` clamp kept; env-knob semantics unchanged —
   the sub-floor residual stays auditable via case F, named in the amend).
2. **Harness registration uplift (OQ2 = 150 s):** kernel
   `.claude/settings.json` pair-rail registration `timeout: 60` -> `150`,
   template `settings.base.json` in parity (same value), `statusMessage`
   added to both (frozen-session UX, consensus kept-5), stale
   "(default 30s)" `_comment` updated. Margin invariant restored:
   150 >= 120 + 30.
3. **Cross-layer invariant as a mechanical TEST (consensus C2):**
   `test_pair_rail_timeout_invariant.py` parses kernel + template + the
   hook's literal default and asserts (a) kernel registration == template
   registration; (b) registration >= internal + 30; (c) statusMessage
   present. A unilateral flip of any single layer goes RED in the suite.
4. **Adopter surfaces (consensus C4-ii, cross-pack-safe split):**
   `scripts/doctor.sh` gains the advisory warn on
   registration < internal + 30 (lands HERE — doctor.sh is not in the
   frozen main-pack, no clobber). The `upgrade.sh` value migration
   (60 -> 150 IFF currently 60, custom preserved, idempotent) does NOT
   land here: `scripts/upgrade.sh` belongs to the frozen PLAN-163
   main-pack (which carries the settings-migration machinery and
   `test_upgrade_settings_migration.py`); a live-based copy in this pack
   would cross-clobber whichever ceremony lands second (S284 class). The
   migration was implemented INSIDE the main-pack's staged `upgrade.sh`
   (cap derived at runtime from the template artifact, never hardcoded)
   and is part of the audited 4-file pack delta (baseline twin `341ffc3`;
   overlay proof: migration suite 36/36 green).
5. **Record (AMEND-1 of ADR-110) as a SEPARATE FILE per house convention**
   (`ADR-110-AMEND-1-rail-timeout-contract.md`; 17 AMEND-file precedents).
   This moves the ADR file count 181 -> 182 — the fail-closed ADR-count
   gates of `land-plan163-pack.sh` were therefore bumped (pre-apply
   181 -> 182; post-apply 183 -> 184; expect dict and closeout text in
   sync) in the PRE-ceremony tooling commit `8f21b25`, NOT in this pack
   (see the split rationale below). The frozen main-pack BYTES are not
   touched by that bump — only the (non-canonical) ceremony script that
   gates them.
   The rail closeout MUST bump the ADR count 181 -> 182 across CLAUDE.md
   + the 6-doc sweep BEFORE the claims check (the ceremony prints the
   exact sed list). The amend names: the env-knob sub-floor residual, the
   recalibration trigger (>=10 healthy cases -> p95 of
   `case.ts − expected.ts` revisits the numbers), the
   `check_codex_filewrite.py` MCP note, and the rejected alternatives
   (async post-facto review; per-invocation reasoning-effort downgrade).

ONE kernel surface in this scope, applied under
`CEO_KERNEL_OVERRIDE=PLAN-164-RAIL-TIMEOUT`: `.claude/settings.json`.
The Owner-shell apply route (cp/git) does not trip in-session canonical
hooks — this signed sentinel IS the authorization record (S261 precedent);
the kernel-override export is the ADR-031 declaration.

Two PLAN-163 plan scripts are NOT Scope entries: they landed in their own
PRE-ceremony commit (non-canonical `.claude/plans/` tooling) so the
fail-closed anchor validator SURVIVES a ceremony rollback — if it rode in
the ceremony commit, `git revert` would restore the old blindly-trusting
resolver exactly when the fail-closed guarantee matters (codex r4 HIGH).
Declared here for transparency (consensus C1/C4-i/kept-3):

- `land-plan163-pin.sh`: `resolve_anchor()` becomes fail-closed pointer
  validation (`ts` derived from `git log -1 --format=%cI <sha>`, never
  read from the file; the sha must be a CEREMONY commit — one whose
  SUBJECT line ENDS with `[SENT-PLAN163-PIN]` or `[SENT-PLAN164-RAIL]`;
  fallback when the file is absent = the NEWEST such commit, which keeps
  post-revert recovery possible while the suffix rule kills the
  mid-message laundering vector — closeout/rollback messages never carry
  the bracketed tag; any failure -> die, no command substitution so the
  specific FATAL reaches the terminal) + pin-pack retirement guard (apply
  dies once a `[SENT-PLAN164-RAIL]` ceremony commit exists — the staged
  pin-pack still carries the old default 30 and a re-apply would silently
  revert this fix; `--gate-v2` remains valid and remains THE verdict).
- `land-plan163-pack.sh`: ADR-count gate bumps 182/184 only (see item 5).

**RE-ANCHOR (OQ3, pin mechanics):** a commit cannot contain its own sha —
POST-commit, the ceremony rewrites
`.claude/plans/PLAN-163/GATE-PIN-ANCHOR` with the sha+ts of the
`[SENT-PLAN164-RAIL]` commit; the anchor is committed in the IMMEDIATE
closeout (all via bash). The append-only HMAC log made `failopen==0`
unsatisfiable against the old anchor `a4371c7`; the re-anchored GATE-V2
PASS proves "liveness under ADR-182 pin + new timeout" — strictly
stronger, the pin is NOT touched (consensus kept-8).

ASYMMETRY-WINDOW DISCIPLINE (consensus kept-2, condition of this
signature): the new internal budget is per-invocation; the 150 s
registration only holds POST-RESTART of the harness. In the ceremony
session, post-apply: NO canonical Edit/Write/MultiEdit — closeout
entirely via `!`/bash; canonical-edit FREEZE in ALL sessions until the
W3 PASS is recorded. A canonical edit inside the window would emit a
post-anchor deficit and re-poison the gate.

## Scope

Scope:
  - .claude/adr/ADR-110-AMEND-1-rail-timeout-contract.md
  - .claude/hooks/check_pair_rail.py
  - .claude/hooks/tests/test_pair_rail_timeout_invariant.py
  - .claude/settings.json
  - scripts/doctor.sh
  - templates/settings/settings.base.json
