I'll verify the plan's claims against the live repo—settings posture, guards, boot surface, counts, and audit paths—before issuing defect findings.Checking one more failure mode around recommendation priority and whether `acceptEdits` is documented as still honoring deny lists:ID: F1  
SEVERITY: P0  
CLAIM: Default `on` (`acceptEdits`) creates a silent escalation ladder into real posture collapse because `settings.local.json` is not on the native deny floor and Write/Edit of that layer will auto-accept.  
EVIDENCE: Live deny list has `Edit(.claude/settings.json)` but no `Edit(.claude/settings.local.json)` (`.claude/settings.json` ~770–772; deny-baseline comments say Edit rules cover all file-editing tools on CC ≥2.1.216). Threat model already calls `settings.local.json` the sentinel-blind prime tamper layer (`docs/threat-model.md` ~2037–2058; `docs/PERMISSION-MODEL-DESIGN.md` §10.2(c)). Under `acceptEdits`, an overnight agent can Write/Edit local to set `bypassPermissions`, `disableAllHooks`, or endpoint remaps without the plan’s `--full` ack; next session (or any process that reloads settings) inherits the weakened posture. Plan Security notes only gate `bypassPermissions` behind `--full` and never harden the local layer.  
FIX: In W0, probe that deny still wins under `acceptEdits`. In W1, make night-mode’s local write also install a sticky deny for `Edit(.claude/settings.local.json)` (and document the dual channel Bash/python rewrite path), OR refuse to use `acceptEdits` without that deny; treat any non-`--full` path that can reach `bypassPermissions` as a hard fail in security review.

---

ID: F2  
SEVERITY: P1  
CLAIM: The plan’s security claim that tripwires “keep attesting the ratified posture” because tracked files are untouched is false for both default `on` and `--full`.  
EVIDENCE: `/ceo-boot` `settings_tamper_tripwires` scans RESOLVED multi-layer settings **including** gitignored `settings.local.json` (`.claude/scripts/ceo-boot.py` ~1556–1572; SPEC/audit-log + `effective_config.FORBIDDEN_KEYS`). `permissions.defaultMode: bypassPermissions` is class `settings_tamper_permission_bypass` (`.claude/hooks/_lib/effective_config.py` ~178–180, ~534–541; unit test writes local bypass and expects the finding). `acceptEdits` is **not** a forbidden value (test treats it as non-bypass). So: default night-mode is invisible to tripwires; `--full` forces a permanent **red** boot every night until off — neither is “attesting the ratified posture.”  
FIX: Rewrite Security notes to the real matrix: (a) default `on` must rely on marker + explicit status of **resolved** `defaultMode`; (b) `--full` must either be accepted as intentional red/tamper, or get a narrow allow/annotation path that does not train the Owner to ignore tamper reds; (c) add ACs that assert this behavior in tests.

---

ID: F3  
SEVERITY: P1  
CLAIM: L2 / “no debate” is mis-leveled: the plan ships a VETO-adjacent security-control escape hatch, which PROTOCOL treats as L3.  
EVIDENCE: PROTOCOL §When debate is mandatory: “Any change in a **VETO-protected domain** (e.g. … auth …) — the VETO owner must debate.” Plan itself schedules T1.4 Security Engineer as “VETO-relevant surface per PROTOCOL §Vetoes” and cites the security carve-out for the ack gate, then asserts L2 because “DEFAULT posture and guarded files are untouched.” Introducing an Owner-facing lever whose job is to weaken ask-first is still a security-control change even if the shipped default stays manual.  
FIX: Reclassify to L3 (or L2-with-explicit-Owner-waiver recorded in the plan), run `/debate` focused on the local-layer ladder + `--full` UX vs tamper classifier, and keep T1.4 as V1/V2 evidence rather than a substitute for debate.

---

ID: F4  
SEVERITY: P1  
CLAIM: `on`/`off` state model can silently leave the machine in a weakened posture (or “restore” the wrong mode) under ordinary failure paths the plan does not design.  
EVIDENCE: Approach stores autonomy in **two** places (`settings.local.json` + `state/night-mode.json` under `~/.claude/projects/<slug>/`) with no atomic pair, no write order, no orphan recovery. Classic defects not specified: (1) double-`on` re-snapshots `acceptEdits` over the original mode so `off` “restores” autonomy; (2) crash after local write / before marker (or reverse) → boot banner lies; (3) manual edit / external editor of local (ConfigChange is blind to outside-harness writes — `check_config_change.py` ~22–23) leaves autonomy with no marker; (4) `off` with missing marker but residual local `defaultMode` is undefined. AC only says double-on/off is tested, not how snapshot-once works.  
FIX: Specify: snapshot only if marker absent; write local first then marker (or single transactional temp+rename for both); `off` always clears **resolved** night-mode leaf even if marker missing; `status` reports four states (clean / armed / orphan-local / orphan-marker) and non-zero on orphans; tests for each.

---

ID: F5  
SEVERITY: P1  
CLAIM: Boot “impossible to forget” banner is not guaranteed: recommendations are hard-capped at 5 and night-mode has no reserved priority.  
EVIDENCE: `_make_recommendations` sorts then `return … recs[:5]` (`.claude/scripts/ceo-boot.py` ~2541–2545, ~2669–2671). Tamper reds, fail-open rail, harness gate, sentinels, stranded plans, etc. already occupy high-priority slots (`005-*` … `02-*`). A low-priority night-mode line can be dropped exactly when the Owner is most likely distracted (busy boot / red noise). Plan T2.1 only says “advisory line … mirrors sanitization.”  
FIX: Render night-mode outside the ≤5 rec list (dedicated always-on digest line / header), or give it a reserved sort key that cannot be truncated when marker exists; add a unit test that injects ≥5 higher recs and still surfaces night-mode.

---

ID: F6  
SEVERITY: P1  
CLAIM: Marker path uses an unspecified `<slug>` while the repo has multiple incompatible project-dir conventions; boot and toggle can disagree and the banner never fires.  
EVIDENCE: Plan: `~/.claude/projects/<slug>/…/night-mode.json`. Live code: path-slug with leading `-` (`ceo-info.py` / `ceo-cost.py` / audit helpers), path-slug without leading `-` (`lessons.py`, `lesson_evolve.py`), fixed `CEO_PROJECT_NAME` default `ceo-orchestration` (`state_store.py` ~114–126), and `ceo-boot.py` lessons slug `str(Path).replace("/", "-")` (~882). No single “project slug” contract is named.  
FIX: Pin one resolver (prefer the same helper ceo-boot will use), put the marker under that exact tree, document env overrides (`HOME`, `CLAUDE_PROJECT_DIR`, `CEO_STATE_ROOT` / `CEO_PROJECT_NAME` if used), and test with `TestEnvContext` that boot and `night-mode status` read the same file.

---

ID: F7  
SEVERITY: P1  
CLAIM: Precedence / merge semantics for `permissions` are under-specified relative to what the repo already documents, so a “merge-write” can clobber allow/deny or be misreported by `status`.  
EVIDENCE: `effective_config` states top-level key wins for the **file resolver**, while the **live harness** deep-merges `permissions` allow/deny and concatenates lists (`.claude/hooks/_lib/effective_config.py` ~7–28). Plan assumes local `permissions.defaultMode` overrides project `manual` and that unrelated keys are preserved, but does not say: deep-merge inside local `permissions`, never replace the whole `permissions` object, and `status` must report harness-effective posture (not a home-grown top-level merge). W0 probes defaultMode override only, not allow/deny preservation under a partial local `permissions` object.  
FIX: Expand W0: (T0.1b) local sets only `defaultMode` while project keep allow/deny — assert both still present in a live session; implement night-mode with deep merge + atomic write (`tmp` + `os.replace`); implement `status` via `effective_config.resolve_settings` (or document honest limits if not).

---

ID: F8  
SEVERITY: P1  
CLAIM: `--full` is specified as Owner-intended control weakening but has no design for the fact it is already classified as hostile tamper, so the product teaches the Owner to ignore red tripwires.  
EVIDENCE: Same classifier path as F2; tests intentionally flag local `bypassPermissions` as tamper (`test_effective_config.py` / `test_ceo_boot_tamper_tripwires.py`). Plan’s only mitigations are typed ack + boot banner; it never decides whether red is desired signal, false-positive fatigue, or a reason to drop `--full` from v1.  
FIX: OQ decision recorded before W1: either remove `--full` from v1 (launcher note only), or document “expected red while full” and force `status`/`ceo-boot` to co-label “Owner night-mode FULL (marker) + tamper class X” so red is not generic “rail integrity suspect” alone; never suppress the tamper class.

---

ID: F9  
SEVERITY: P2  
CLAIM: Count-drift coverage is incomplete for a new slash command.  
EVIDENCE: Plan updates 26→27 via `check-claude-md-claims.py` + `verify-counts.sh` + CHEAT-SHEET/TROUBLESHOOTING. Disk today: 26 command files; **hardcoded 26 also in** `README.md` (table + shell comment), `CHANGELOG.md` counts block, `CLAUDE.md` §1. `check-claude-md-claims.py` only validates **CLAUDE.md** claims (`--help` / module docstring). Tolerance=0 elsewhere will not catch README/CHANGELOG drift.  
FIX: Explicit T2.2 checklist: `CLAUDE.md`, `README.md`, `CHANGELOG.md` (if shipping), `docs/CHEAT-SHEET.md`, and `.claude/scripts/local/verify-counts.sh` in one commit; run both count gates before push.

---

ID: F10  
SEVERITY: P2  
CLAIM: Corrupt / partial `settings.local.json` failure mode is unspecified and can degrade the local layer while leaving autonomy or yellow-only noise.  
EVIDENCE: ceo-boot maps unparseable layers to yellow (`ceo-boot.py` ~1624–1630). Plan requires merge-write and “byte-preserved unrelated keys” but not atomic rewrite, JSON validation before replace, or fail-closed refuse-to-write if parse fails. A bad write can drop the local layer (posture falls back to project manual) **or** leave a half-applied file depending on harness behavior — neither is AC’d.  
FIX: Read→validate→deep-merge→write temp→`os.replace`; on parse failure of existing local, abort non-zero without marker change (or quarantine + explicit `--force-reset`); tests for corrupt pre-existing local.

---

ID: F11  
SEVERITY: P2  
CLAIM: Default `on` has no Owner-intent gate comparable to `--full`, so arming is only as strong as one Bash approval in a manual session.  
EVIDENCE: Only `--full` requires typed ack `NIGHT-MODE-FULL-I-ACCEPT`. Default `on` is a real weakening (auto file edits overnight). Slash command / `!` script path is agent-runnable once Bash is approved; allowlist does not include `python3 .claude/scripts/…` (allow is only narrow git/ls/grep family). That is better than free arming, but weaker than the plan’s own security doctrine for posture changes.  
FIX: Require a short typed ack for default `on` as well (e.g. `NIGHT-MODE-ON`), or require tty/interactive confirm; document that non-interactive `on` is rejected.

---

ID: F12  
SEVERITY: P2  
CLAIM: W0 is missing the deny-under-`acceptEdits` and “local cannot delete keys” probes the design depends on.  
EVIDENCE: T0.1–T0.3 cover defaultMode override, disableAutoMode+acceptEdits autonomy, and guard inventory. Design still depends on: deny floor still enforced under `acceptEdits`; local overlay cannot remove `disableAutoMode` (stated as fact, not probed); partial `permissions` merge preserves deny/allow (F7). S286 taught that unprobed schema claims burn sessions.  
FIX: Add T0.4 deny-still-blocks under `acceptEdits` (e.g. `Edit(PROTOCOL.md)`); T0.5 local without `disableAutoMode` still has project `"disable"` effective; T0.1b permissions deep-merge (F7).

---

ID: F13  
SEVERITY: P3  
CLAIM: Ceremony-rider audit action is correctly deferred, but “L6 observer only” is oversold as forensic coverage for posture changes.  
EVIDENCE: Dedicated `night_mode_toggled` needs `_KNOWN_ACTIONS` + pair-rail inputs path `audit_emit.py` (manifest line 28; `_KNOWN_ACTIONS` starts ~154 — claim OK). Bash L6 observes command text, not semantic before/after mode, hostname, or whether write succeeded. `off`/`on` success is not chain-evident without stdout capture discipline.  
FIX: Until ceremony lands, have the script print a stable one-line machine summary (`mode=… local=… marker=…`) and AC that `status` is the source of truth; do not claim “forensically chained toggle.”

---

ID: F14  
SEVERITY: P3  
CLAIM: Guard-surface inventory claim for main-wave paths is consistent with `_CANONICAL_GUARDS` today, but T2.1 ceo-boot edit is a high-churn surface that needs an explicit non-guard confirmation in W0.  
EVIDENCE: Spot-check against `check_canonical_edit._CANONICAL_GUARDS`: `.claude/scripts/night-mode.py`, `.claude/commands/night-mode.md`, `.claude/settings.local.json`, `.claude/scripts/ceo-boot.py` are clear; `_lib/audit_emit.py` is guarded (correctly ceremony-only). T0.3 lists the first set but omits `ceo-boot.py` even though W2 edits it.  
FIX: Add `ceo-boot.py` (and any test files under `.claude/scripts/tests/`) to T0.3 inventory explicitly.

---

ID: F15  
SEVERITY: P3  
CLAIM: Line-number posture claims for `settings.json` are currently true but must not be treated as stable contracts.  
EVIDENCE: Verified live: `disableAutoMode: "disable"` at L764, `permissions.defaultMode: "manual"` at L767, `workflowSizeGuideline: "medium"`. Comment at L763 still narrates `disableAutoMode=true` (stale prose vs string enum) — not introduced by this plan, but shows comment drift risk.  
FIX: Cite keys by name in the plan; keep line numbers only as “as of S288” footnotes.

---

VERDICT: REJECT
