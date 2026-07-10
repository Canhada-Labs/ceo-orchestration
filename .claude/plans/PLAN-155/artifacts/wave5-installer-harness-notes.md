# PLAN-155 Wave 5 — installer `--harness codex` (SENT-CX-C) build + proof notes

**Date:** 2026-07-10. **Base rule:** `scripts/install.sh` and
`scripts/upgrade.sh` bases are the **repo files** — PLAN-153's installer waves
(B, E) are LANDED on main (`2094175`, `24d2a27`), and PLAN-154 sent-f has no
`scripts/` dir. No earlier PLAN-155 wave staged the installer. So repo base for
both.

## What shipped (staged under `PLAN-155/staged/wave-5/`)

| file | class | role |
|---|---|---|
| `scripts/install.sh` | UNGUARDED (SENT-CX-C scope) | `--harness <claude\|codex>` + codex emission, gated so the claude path is byte-identical |
| `scripts/upgrade.sh` | UNGUARDED (SENT-CX-C scope) | `--harness` replay from `request.harness`; codex bundle refresh under `--on-conflict` |
| `scripts/_codex_harness.sh` | **NEW UNGUARDED COMPANION** | single source of truth for codex emit/arming/uninstall/version — sourced by BOTH install.sh + upgrade.sh (same pattern as `_hash_lib.sh`) |
| `scripts/tests/test-install-harness-codex.sh` | NEW UNGUARDED TEST | the debate-A11 nine-case matrix + uninstall bonus |
| `scripts/tests/_case2_probe.py` | NEW UNGUARDED TEST HELPER | runtime-resolution subprocess probe over the INSTALLED `.codex/hooks.json` |
| `ceremony-riders/validate-yml-installer-matrix.diff` | KERNEL RIDER (not staged as file) | exact `git apply` diff wiring the matrix into `validate.yml` (F5) |

### Design decision — the shared helper
`_codex_harness.sh` is a NEW unguarded companion (rides the SENT-CX-C commit
like the tests do; not canonical-guarded). It keeps the ~200-line codex emit
logic in ONE place instead of duplicating it across install.sh and upgrade.sh
— the professionally correct call, matching the repo's existing sourced-helper
pattern (`_hash_lib.sh`, `_framework_manifest_set.sh`). install.sh maps its
`codex_journal` recorder onto `_state_record_op`; upgrade.sh onto
`_up_record_op` (later definition wins over the helper's no-op default).

## Codex path emits (all debate/plan items)
1. operator `AGENTS.md` (rendered from `templates/codex/AGENTS.md`)
2. `.codex/hooks.json` + `.codex/rules/ceo.rules` (from wave-2 templates)
3. trust-flow guidance (consent-first — NEVER writes trust into `$CODEX_HOME`)
4. `requirements.toml` behind `--managed-hooks` (OQ1: `/hooks` guided default,
   managed opt-in) — a REVIEWABLE policy file, not a headless trust write
5. `--with-codex-skills`: N/A-guarded no-op until Wave 8 (OQ2)
6. **MCP reviewer registration INVERTED**: the codex path does NOT install the
   Claude-host `.mcp.json` codex server; it prints the inverted-pair-rail
   guidance naming `claude -p` as the reviewer CLI + `CEO_REVIEWER_MODEL`
   (OQ3). The Stop-hook that USES it is Wave 6.
7. **post-install ARMING check (A7)** printed as the installer's FINAL
   instruction: `ARMED / NOT-ARMED-(untrusted) / BROKEN`; states loudly that
   NOTHING is enforced until `/hooks` trust is granted. Detects the
   **git-worktree discovery gap** (BROKEN) and **version skew** (A15).
8. **lifecycle symmetry (A9)**: a manifest ledger
   (`.codex/.ceo-harness-manifest`, schema `ceo.codex-harness/v1`) drives
   `--uninstall` (removes emitted paths + restores `--force` backups). The
   ledger is generic so Wave 6's `.git/` pre-push hook APPENDS its line and
   uninstall reaches it (the third install surface).
9. **collision policy (A10)**: atomic pre-flight — an un-forced collision
   REFUSES the whole bundle with a printed diff and ZERO writes; `--force`
   backs up (`<path>.ceo-bak-<ts>`) then overwrites. Idempotent re-run
   identical-skips (no error, no backup).
10. `--harness` round-trips through `.install-state.json` (`request.harness` +
    `managed_hooks`) into `upgrade.sh` replay (mirrors PLAN-153 B2
    profile/stack replay); `_write_upgrade_state` already preserves the
    `request` dict, so the harness survives upgrades.

## Byte-identical claude path (case 1, the load-bearing guarantee)
Everything codex is gated behind `HARNESS == "codex"`. The default/`--harness
claude` path adds only: inert flag-parser arms, inert var inits, a sourced
helper (functions defined, never called), and two extra keys in the volatile
`.install-state.json`. Case 1 installs no-flag and `--harness claude` into the
**same** target path (wipe between) and asserts `diff -r` empty (excluding the
volatile state/manifest files) + zero codex artifacts.

## Proof — the nine-case matrix ran GREEN end-to-end (live, macOS, py3.13)
`bash scripts/tests/test-install-harness-codex.sh` → **10 passed, 0 failed**
(9 cases + uninstall bonus). Real installs into throwaway targets from a
throwaway SOURCE overlay (repo + sent-f + wave-1 + wave-2 + wave-5, landing
order). Case 2 ran every registered `.codex/hooks.json` command as a
subprocess from a foreign cwd → all resolved (shim absolute + executable, hook
bare-name resolves under `.claude/hooks/`), no shim ERROR breadcrumb (the S254
vacuous-green control). Rendered `AGENTS.md` = 7385 bytes (≤ 32768).

- `shellcheck -S warning`: CLEAN on all four `.sh` (install/upgrade/helper/test).
- `bash -n`: clean. `_case2_probe.py`: `ast.parse` + `py_compile` clean (py3.9
  floor syntax: `from __future__ import annotations`, `typing`, no PEP-604).
- CI rider: `git apply --check` CLEAN (body) against post-PLAN-153/154 main.

## Landing order (BINDING for the SENT-CX-C ceremony)
1. PLAN-153 install.sh waves — ALREADY LANDED (precondition satisfied).
2. wave-2 templates (`templates/codex/**`) must be on main first — the
   installer copies them (test/install hard-fail loudly if absent).
3. wave-5 commit under **SENT-CX-C** (anchor-sha on post-PLAN-153/154 main).
   SENT-CX-C scope names `scripts/install.sh` + `scripts/upgrade.sh`; the NEW
   companions (`scripts/_codex_harness.sh`, `scripts/tests/*`) are unguarded
   and ride the same commit (name them in the sentinel prose so the coupling
   is not discovered at execution time). `install.sh`/`upgrade.sh` are NOT in
   `_KERNEL_PATHS` — no kernel-override needed for Wave 5 (unlike 1/3b/4/6).
4. The `validate.yml` rider (KERNEL, F5) is applied in the SENT-CX-C commit if
   signing scopes validate.yml, else in the Wave-6 SENT-CX-D commit under
   `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-PAIRRAIL-TEETH` + ACK.

## Open issues / residuals (named, not papered over)
1. **Wave-6 `.git/` pre-push hook** is bound by this wave's manifest/uninstall
   contract — Wave 6 MUST append its emitted path to
   `.codex/.ceo-harness-manifest` (an `emit\t.git/hooks/pre-push` line) so
   `--uninstall` reaches it. Documented in the helper header.
2. **Partial-emit rollback residual**: the collision pre-flight makes an
   un-forced refusal atomic (zero writes). A HARD error mid-emit (rc 1, e.g.
   `cp` failure after some files written) leaves those `.codex/` files behind
   — the install.sh rollback trap only restores `.claude/`. Low-risk (local
   FS writes rarely fail mid-bundle); named for ADR-161's failure-semantics.
3. **Arming check trust detection** is best-effort: it positively confirms
   ARMED only when `$CODEX_HOME/config.toml` shows the project
   `trust_level = "trusted"` (tomllib on py≥3.11, else a literal scan). It
   NEVER assumes trusted — default verdict is NOT-ARMED-(untrusted), the
   honest floor.
4. **CI shellcheck scope**: the validate.yml shellcheck step scans
   `.claude/{scripts,hooks}` only, NOT top-level `scripts/` — so these `.sh`
   are not gated by that step. Verified clean manually; flag for a future
   shellcheck-scope widening (out of Wave 5 scope — widening could surface
   pre-existing warnings in other top-level scripts and is not mine to green).
5. **`--managed-hooks` requirements.toml** ships the single-repo posture only;
   the enterprise/org-scale rollout guide stays deferred (plan §Deferred).
