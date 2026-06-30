---
id: ADR-155
title: Install/upgrade baseline SHA-256 manifest — preserve adopter customizations, recover the root PROTOCOL.md
status: ACCEPTED
accepted_at: 2026-06-17
accepting_session: S241
---

# ADR-155 — Install/upgrade baseline SHA-256 manifest

- **Status:** ACCEPTED (S241, 2026-06-17 — shipped + CI green in PLAN-138 Wave C; debate `wf_e01edd9f-4a4` 0-VETO + Codex pair-rail `019ed611` R1→R3 ACCEPT, Codex ≥3-iter on the upgrade engine satisfied)
- **Date:** 2026-06-17
- **Enforcement commit:** `bbe279ea` (PLAN-138 Wave C — shared enumeration + per-file classified walk + root-PROTOCOL.md backup; CI green)
- **spec-kit baseline pin:** **v0.11.0 (2026-06-16)** (PLAN-110 round-1 studied v0.8.11; this is the reserved round-2). Imported idea: a recorded baseline lets an updater distinguish a framework-changed file from an adopter-customized one. NOT imported: spec-kit's 4-tier preset/priority override resolution stack (see ADR-137 below).
- **Decision drivers:**
  - **S238 data-loss class** ([[feedback-upgrade-sh-clobbers-customized-protocol-md]]): `scripts/upgrade.sh` whole-tree `delete + cp -R` (`backup_and_replace`, lines 419-443) silently replaces adopter-customized files inside directory targets, and `_refresh_protocol_pointer()` (lines 450-486) does `cat > "$TARGET/PROTOCOL.md"` at **line 481 with NO `.claude.bak/` backup** — clobbering a customized **root** `PROTOCOL.md` that lives *outside* the `.claude/` tree. The S238 acme population hit exactly this.
  - **install-set ≠ upgrade-set.** `install.sh` writes a *selective* list (`install_hooks_selective`, `install_scripts_selective`, `install_one ".claude/commands"`, the pointer at install.sh:1425); `upgrade.sh` `cp -R` drags whole directories. Two divergent enumerations is itself a defect — one shared, framework-owned enumeration must back both the manifest writer and the classifier.
  - **Fail-open doctrine (CLAUDE.md §5).** A missing/corrupt/unsigned manifest must degrade to *today's* behavior, never to a NEW escalation: the worst case is the current `diff -q` warn-then-clobber, plus the new root-PROTOCOL.md backup that makes even the manifestless case recoverable.

## Context

`upgrade.sh` cannot tell "the framework changed this file" apart from "the adopter changed this file" — it has no record of what it originally wrote. So it backs up and overwrites everything, surfacing only a `diff -q` WARNING. For directory targets (`.claude/hooks`, `.claude/scripts`, `.claude/commands`, `.claude/skills/*`) the overwrite is whole-tree: `find "$dst" -mindepth 1 -delete` then `cp -R`. A per-file customization inside such a directory is lost (recoverable only by hand-digging `.claude.bak/<timestamp>/`).

The verified worst case is the **root `PROTOCOL.md`**. `_refresh_protocol_pointer()` regenerates it unconditionally with `cat >` and, unlike `backup_and_replace`, writes **no backup** first. An adopter who turned the pointer stub into a real customized protocol (the S238 acme case) loses it with no `.claude.bak/` copy at all. This file is *outside* `.claude/`, so a `.claude/`-scoped manifest walk would also miss it — the manifest enumeration and the refresh path must both cover it.

spec-kit records a baseline so it can classify a target file as framework-changed vs locally-customized. We import **only that idea** — a recorded SHA-256 baseline written at install time, re-read at upgrade time, recomputed from disk on the upgrade run, and used to PRESERVE/REFUSE a customized file instead of clobbering it. The manifest is **target-side, unsigned, advisory** — it raises the floor from "silent clobber" to "preserve-or-recover", it is not a trust anchor.

## Decision drivers

- Closing S238 *prevention* (manifest present → preserve/refuse) and S238 *recovery* (manifest absent → back up the root PROTOCOL.md before overwrite) are separable and both cheap.
- A single shared enumeration removes the install≠upgrade drift at the root cause rather than patching one side.
- The classifier must recompute both `H_dst` and `H_src` from disk *on the upgrade run* — a cached `H_src` from the manifest cannot be trusted (the source moved since install).

## Options considered

- **Option A — signed/GPG baseline manifest (trust anchor).** Rejected for v1.47: the GPG ceremony is the Owner-side install/upgrade signing, not a per-target artifact; a per-adopter signed manifest is a much larger surface (key distribution, rotation) for marginal gain over the fail-open fences. OUT OF SCOPE this round (OQ-trust).
- **Option B — import spec-kit's 4-tier override/priority resolution stack.** **REFUSED.** ADR-137 SKIP-DEFERs the preset/priority-stack; PLAN-138 anti-goal #5 forbids it. We import the manifest idea ONLY, never the override stack.
- **Option C — target-side unsigned baseline manifest + per-file classification + shared enumeration + root-PROTOCOL.md backup, fail-open to today's behavior.** ADOPTED. The six decisions below.

## Decision

1. **(i) Single shared framework-owned enumeration.** `scripts/_framework_manifest_set.sh` exports the ONE canonical list of framework-owned files the upgrade overwrites, reconciling `install.sh`'s selective write-list with `upgrade.sh`'s `cp -R` targets. Both `write_install_manifest` (install) and `_classify_against_baseline` (upgrade) source it. Profile-aware: a `--profile core` install does not enumerate absent frontend/domain files. It covers root `PROTOCOL.md` + `.claude/{team.md, frontend-team.md, skills, hooks, scripts, commands, pitfalls-catalog.yaml, task-chains.yaml}`; it EXCLUDES the manifest dotfile itself + `.claude.bak/`.
2. **(ii) Per-file classification.** Upgrade reworks directory-target overwrite from whole-tree `delete + cp -R` to a per-file walk calling `_classify_against_baseline(rel_file)` per file. Four outcomes keyed on baseline `H_base`, destination `H_dst` (recomputed this run), source `H_src` (recomputed this run): FRAMEWORK-CHANGED (`H_dst==H_base && H_src!=H_base`) → auto-update; ADOPTER-CUSTOMIZED (`H_dst!=H_base && H_src==H_base`) → preserve; CONFLICT (both differ) → refuse per `--on-conflict={refuse|theirs|backup}` (default `refuse` = per-file skip-and-report-and-CONTINUE, never abort the whole upgrade); manifest-line-absent/malformed/LINK → FALL BACK to today's `diff -q` warn-then-clobber.
3. **(iii) Cover root-level refresh targets.** `_refresh_protocol_pointer()` (the verified S238 driver, upgrade.sh:450-486) backs up `$TARGET/PROTOCOL.md` to `$BAK_DIR/PROTOCOL.md` **before** the `cat >` overwrite, and classifies the root `PROTOCOL.md` against the baseline — preserving/refusing a customized one instead of clobbering.
4. **(iv) Upgrade re-writes the manifest.** After a successful upgrade, upgrade.sh (re)writes the baseline manifest via the install-side generator, so a long-lived adopter who upgrades but never re-runs `install.sh` (the S238 acme population) acquires/refreshes a manifest.
5. **(v) Provenance / path hardening (CWE-345/494/22).** The manifest grammar accepts EITHER a hash record `^[0-9a-f]{64}  <relpath>$` OR a link record `^LINK  <relpath>  <target>$` (a `--mode link` symlink's content == source, so a content hash is meaningless — classification short-circuits LINK). Any line matching NEITHER grammar, or a relpath that is absolute / contains `..` / control chars / duplicates a prior relpath / traverses a symlinked component (lstat, do not follow), causes that file to FALL BACK — never the silent FRAMEWORK-CHANGED branch on an unverified baseline. The raw manifest is NEVER piped into `shasum -c`; the updater recomputes + compares in-process per validated relpath.
6. **(vi) Fail-open to today's behavior + always back up the root PROTOCOL.md.** A missing/corrupt manifest degrades to the current `diff -q` warn-then-clobber for `.claude/` targets; the root-PROTOCOL.md backup in (iii) applies EVEN when no manifest exists, so the loss is recoverable on a first upgrade. No new hook emits `permissionDecision`; the classifier never increments governance `ERRORS`.

## Consequences

- **(+)** S238 data-loss class is closed two ways: *prevented* when a manifest is present (per-file customization + the root PROTOCOL.md preserved/refused), *recoverable* when it is absent (root PROTOCOL.md backed up to `$BAK_DIR` before the `cat >` overwrite in `_refresh_protocol_pointer`).
- **(+)** The install≠upgrade enumeration drift is removed at the source: one `_framework_manifest_set.sh` backs both sides.
- **(+)** `scripts/_hash_lib.sh` + `scripts/_framework_manifest_set.sh` are added to `_CANONICAL_GUARDS` in `check_canonical_edit.py` — they are sourced by the GPG-gated install/upgrade and must not be a soft underbelly.
- **(−) The manifest is target-side, unsigned, and best-effort.** It is NOT a trust anchor: an attacker who can already write the target tree can also rewrite the manifest. **Adopters are told not to over-trust it** — an unsigned, best-effort, target-side record is advisory only. Its value is solely raising the floor from "silent clobber" to "preserve-or-recover"; the provenance fences in decision (v) ensure a tampered/garbage manifest degrades to today's behavior, never to a NEW escalation. A signed/GPG manifest is OUT OF SCOPE this round (Option A, OQ-trust).
- **(~)** Upgrade is now a per-file walk for directory targets (more I/O than a single `cp -R`), bounded by the framework-owned file count; the `find … -delete` idiom is retained only for emptying a replaced directory, never `rm -rf`.

## Residual risks

- **Unsigned manifest (accepted).** See Consequences (−). Mitigated by the decision-(v) provenance fences + fail-open: the worst case equals today's behavior.
- **Tampered `H_base==H_dst` line (accepted, Codex R1 P0#1).** Because the manifest is unsigned, an attacker (or accidental corruption) could set a customized file's recorded baseline to its *current* hash, mis-classifying it as FRAMEWORK-CHANGED → auto-update. This cannot be detected without a signed baseline. It is fenced two ways so the worst case stays "today's behavior, recoverable": (a) the FRAMEWORK-CHANGED branch is **NON-SILENT** — it always backs the original up to `$BAK_DIR` first and surfaces the overwrite + backup path on stderr (it is not a quiet `UPDATED`), and (b) duplicate relpaths are rejected entirely (not first-wins) so an attacker cannot shadow a genuine line. A genuinely-customized file overwritten this way is therefore always recoverable from `$BAK_DIR`.
- **First-upgrade-without-manifest window.** Closed for the root PROTOCOL.md by decision (iii)'s unconditional backup; `.claude/` directory targets fall back to today's `diff -q` warn-then-clobber on a first manifestless upgrade, then acquire a manifest via decision (iv) so the *second* upgrade is protected.
- **Classification depends on disk state at upgrade time.** A file an adopter reverted to byte-identity with the framework reads as FRAMEWORK-CHANGED (no customization to preserve) — correct by construction, recorded here for completeness.

## Blast radius

L3 — an upgrade-engine rewrite, not a bolt-on: it reworks `upgrade.sh`'s directory-target overwrite path + `_refresh_protocol_pointer`, adds two sourced helpers under `scripts/` to `_CANONICAL_GUARDS`, and edits `install.sh`'s post-install path. It imports ONLY spec-kit's baseline-manifest idea and explicitly REFUSES ADR-137's preset/priority override stack (anti-goal #5). Codex ≥3-iter pair-rail review is mandatory for this unit at execution (ADR-107 L2+).
