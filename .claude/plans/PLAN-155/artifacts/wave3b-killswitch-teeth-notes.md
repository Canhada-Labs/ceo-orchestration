# PLAN-155 Wave 3b (SENT-CX-E) — kill-switch teeth: build + proof notes

The teeth Waves 2/3 deferred (debate A8, circular-disarm gap). The `.codex`
registration/rules/managed surface + operator `AGENTS.md` become
canonical-guarded at edit time AND boot-tripwire-tracked, so an agent under
codex can no longer rewrite `.codex/hooks.json` (or the rest of the
surface) and disarm every ENFORCED rail while the tripwire stays silent.

## What changed (three guarded files + four test companions)

1. **`check_canonical_edit.py` (KERNEL, ADD-ONLY)** — extended
   `_CANONICAL_GUARDS` with the exact kill-switch set
   (`.codex/hooks.json`, `.codex/config.toml`, `.codex/rules/ceo.rules`,
   `requirements.toml`, `AGENTS.md`) AND extended the fast-path
   `_CANONICAL_PREFIXES` frozenset with `.codex` / `requirements.toml` /
   `AGENTS.md`. **The prefix extension is load-bearing:** `_is_canonical`
   bails on any first-segment not in `_CANONICAL_PREFIXES` BEFORE
   consulting `_CANONICAL_GUARDS` — omitting it leaves the new guards dead
   (the S254 class). Diff vs the wave-1 base is exactly two additive
   blocks; no other byte changed (S258 `touched − SIGNED SCOPE = ∅`).

2. **`SessionStart.py` (KERNEL)** — new boot-time re-hash of the
   kill-switch surface. NO-OP unless a `.codex/` install marker
   (`hooks.json`/`config.toml`/`ceo.rules`) is present — so this framework
   repo (no `.codex/`, but a reviewer-contract root `AGENTS.md`) never
   engages it (no yellow-fatigue, no real-HOME baseline write in tests).
   Baseline manifest persisted under the per-project state dir
   (`CEO_PROJECT_STATE_DIR` else HOME-based, the `onboarded.flag`
   precedent). First sight → baseline (informational). A tracked file
   later MISSING or MUTATED vs baseline → **RED**: stderr breadcrumb
   `KILLSWITCH-TRIPWIRE-RED` + a systemMessage note. RED does NOT
   overwrite the baseline (signal persists); a NEW surface component
   refreshes it (legit install extension). SessionStart never blocks
   (`continue:true` always) — fail-open per ADR-005.

3. **`_lib/effective_config.py` (CANONICAL)** — new
   `TAMPER_CODEX_KILLSWITCH_MISSING` class + `_check_codex_killswitch_census`
   wired into `classify_tampering`. Fires ONLY when a `.codex/` install
   marker is present AND (a) the registration was removed (only `ceo.rules`
   left, no `hooks.json`/`config.toml`) OR (b) a hook the registration
   references is missing under `.claude/hooks/`. Stateless, one-directional,
   fail-open. No-op on every existing `.claude`-only fixture.

## Test commands + results (Python 3.9.6, repo floor; overlay = HEAD + sent-f + wave-1 + wave-2 + wave-3b)

| suite | CEO_HOOK_ADAPTER unset | =codex |
|---|---|---|
| `test_session_start` (29 tests, minus the pre-existing `/`-walk env-hang) | OK | OK |
| `test_effective_config` (60 tests) | OK | OK |
| `test_check_canonical_edit` (47 tests) | OK | OK |
| `test_codex_killswitch_teeth` (5 tests, NEW) | OK | OK |
| `test_codex_positive_controls` (6) — unchanged, exercises my hook | OK | OK |
| `test_codex_templates` (20, 1 skip tomllib<3.11) | OK | OK |
| `test_adapter_golden` (34) / `test_adapter_seam_dispatch` (8) | OK | OK |

## Mutation controls (the certifying suite has teeth)

- **Guard-dead mutation:** removing the three kill-switch entries from
  `_CANONICAL_PREFIXES` → `test_each_killswitch_path_denied_unsentineled`
  goes RED (**5 failures**, one per kill-switch path) — proves the fast-path
  prefix extension is load-bearing, not decorative.
- **Tripwire-dead mutation:** forcing `_check_killswitch_surface` to always
  return `absent` → `test_mutated_killswitch_file_reddens_boot_rehash` goes
  RED (**1 failure**) — proves the boot re-hash actually detects mutation.

## Behavioral coverage (test_codex_killswitch_teeth.py)

- (a) each of the 5 kill-switch paths, planted as a recorded codex-cli
  0.139 apply_patch UPDATE envelope, replayed as a SUBPROCESS on the
  byte-identical `check_canonical_edit.py` command line shipped in
  `templates/codex/hooks.json` (`CEO_HOOK_ADAPTER=codex`, argv-split from a
  project cwd) → `permissionDecision: deny` + `CANONICAL-EDIT-BLOCKED`.
- (b) copied-marker-still-reddens: a sentinel scoping a DIFFERENT path does
  NOT disarm the edit (deny holds); a sentinel scoping the exact path DOES
  grant it (surface is sentinel-GATED, not blanket-denied).
- (c) mutated `.codex/hooks.json` across two SUBPROCESS boots on the shipped
  `SessionStart.py` command line → boot #2 emits `KILLSWITCH-TRIPWIRE-RED`;
  absent surface → no RED (no yellow-fatigue).

## Ceremony (wave-3b main commit)

SENT-CX-E + `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-KILLSWITCH-GUARD-EXTENSION`
+ `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`. The override covers BOTH KERNEL rows
(`check_canonical_edit.py` guard-list AND `SessionStart.py` boot re-hash —
pair-rail S265 F2). `effective_config.py` is sentinel-only canonical. The
four `hooks/tests/**` companions ride the same commit (not sentinel-blocked).
Land AFTER wave-1 (base of `check_canonical_edit.py`) and wave-2 (template +
fixtures the teeth test reads), BEFORE Wave 5 ships the paths via installer.

## Open items handed to the ceremony / later waves (see MANIFEST-A Open issues #9-13)

- Root `AGENTS.md` guarding is a behavior change in this repo — ratify at
  signing (#9).
- Boot-tripwire baseline is agent-writable — documented residual, edit-time
  guard is the real protection (#10).
- Matrix-row flip (ABSENT → ENFORCED-at-edit + boot-ADVISORY) + ADR-161
  KERNEL-override note are plan/ADR surfaces, NOT in this batch's file
  scope (#11).
- `test_check_config_change._AuditEmitSlotGuard` standalone failure is a
  runner import-order artifact, orthogonal to wave-3b (verified against
  unmodified repo code) (#13).
