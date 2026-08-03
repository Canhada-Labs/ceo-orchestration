# Round 2 — revisao adversarial de seguranca sobre a IMPLEMENTACAO

Agente `verify:security` do workflow wf_8423eec7-05f, read-only, sobre o
diff do branch + arquivos nao-commitados. 11 findings (1 CRITICAL).

FINDINGS — PLAN-165 adversarial security review (read-only)

Scope reviewed: `git diff fd372dd..HEAD` (plan/probes/debate artifacts only) + all uncommitted work in `/Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/worktrees/plan165`: `.claude/scripts/night-mode.py` (678 L), `.claude/scripts/ceo-boot.py` delta (+120), `.claude/commands/night-mode.md`, `.claude/adr/ADR-185-night-mode-posture-toggle.md`, `.claude/scripts/tests/test_night_mode.py`, `.claude/scripts/tests/test_ceo_boot_night_mode.py`, `.claude/plans/PLAN-165/ceremony-staged/{README.md,p1-deny-overlay.patch,p2-audit-action.patch,MANIFEST.sha256}`, docs deltas.

---

**NM-01 / CRITICAL / `off` writes an arbitrary, agent-controllable `defaultMode` — including `bypassPermissions` — laundering a marker write into an overlay write that P1's deny cannot see.**

EVIDENCE: `night-mode.py:466-467` — `if prev_present: new_permissions["defaultMode"] = prev_value` — where `prev_value = marker.get("prev_value")` (`:435`) with **zero** validation. The marker `.claude/state/night-mode.json` is gitignored, is **not** in `_CANONICAL_GUARDS` (`check_canonical_edit.py:113-331`; W0 T0.3 confirms "ZERO hits"), and is **not** in the P1 deny patch (which covers only `.claude/settings.local.json`). Under the very posture night-mode creates (`acceptEdits`), a tool Edit/Write of the marker is auto-accepted. Live probe:

```
$ night-mode.py on --project-root .../nm1        # overlay -> acceptEdits
$ # marker prev_value hand-set to "bypassPermissions"
$ night-mode.py off --project-root .../nm1
night-mode: OFF — local overlay defaultMode restored to bypassPermissions (snapshot). Next session starts on the ratified posture.
$ cat nm1/.claude/settings.local.json
{ "permissions": { "defaultMode": "bypassPermissions" } }
```

The attack needs no Bash approval from the attacker: the designed morning workflow (`/night-mode off`, run by the Owner) is the trigger. This falsifies three load-bearing claims: ADR-185 D1 ":77 Night-mode itself writes only `permissions.defaultMode: \"acceptEdits\"`", `night-mode.py:14-15` "The only mode this script ever writes is `acceptEdits`", and `docs/FAQ.md:117` "`/night-mode` itself never writes `bypassPermissions`". D2's single-writer property is intact; the writer itself is the confused deputy.

FIX: validate on restore — accept `prev_value` only if it is a string in a closed set of modes night-mode could legitimately have snapshotted (explicitly excluding `bypassPermissions`), else fail-CLOSED exit 2 leaving the marker in place; **and** add `Edit(.claude/state/night-mode.json)` + `Write(.claude/state/night-mode.json)` to the P1 deny patch (both files).

---

**NM-02 / HIGH / The crash/desync path re-opens exactly the permanent-weakening hole create-only exists to close, and the command doc's own remediation walks the Owner into it.**

EVIDENCE: create-only is enforced solely by `if marker_file.exists(): return 0` (`:309`). In the AC-5 end-state (settings armed, marker absent — read-back failure at `:355`, marker write failure at `:376`, or crash), `cmd_on` re-runs the snapshot against a file night-mode itself armed. `night-mode.md:121-123` prescribes exactly this: "Fix by running `off` then `on`". Live probe:

```
$ on; rm .../state/night-mode.json          # simulated crash
$ off  -> "already OFF (no marker) — no-op."
$ on   -> "Previous local value: acceptEdits"   # marker prev_value = acceptEdits
$ off  -> "restored to acceptEdits ... Next session starts on the ratified posture."
$ cat settings.local.json -> defaultMode: acceptEdits    # armed, marker gone
$ status -> DISAGREE (no marker, but overlay armed)
```

Result: `acceptEdits` is permanently armed, `off` is now a no-op forever (no marker), and only `status` — which nobody is required to run — reports it. AC-3's invariant holds only for the double-`on` path the test exercises (`test_on_on_off_returns_to_manual_not_acceptedits`); the desync path is untested.

FIX: in `cmd_on`, when the current local `defaultMode == NIGHT_MODE`, record `prev_present=False` / `prev_value=None` (night-mode never snapshots its own value), or fail-CLOSED with the `status`-reconcile diagnostic. Add the desync-then-`on`-then-`off` case to `NightModeCrashDesyncTest`.

---

**NM-03 / HIGH / The "single writer" is itself unguarded: P1 closes the overlay path but leaves the script and the marker tool-writable under `acceptEdits`.**

EVIDENCE: worktree `permissions.deny` (24 entries) contains `Edit(PROTOCOL.md)`, `Edit(.claude/settings.json)`, `Edit(SPEC/**)` and no `.claude/scripts/**`. `_CANONICAL_GUARDS` (`check_canonical_edit.py:113-331`) enumerates `.claude/scripts/` files individually — `lessons.py`, `prune-lessons.py`, `lesson-restore.py`, `lesson_ranker.py` — with no glob; `night-mode.py` and `ceo-boot.py` are absent (W0 T0.3 records this as a convenience: "ZERO hits"). So the escalation ladder D2 claims to close has two remaining rungs that are auto-accepted in night mode: edit the single writer, or edit its snapshot (NM-01). Edits are audited by PostToolUse but not blocked.

FIX: extend `_CANONICAL_GUARDS` with `.claude/scripts/night-mode.py` (sentinel-gated, in the same ceremony as P1), or add `Edit(.claude/scripts/night-mode.py)`/`Write(...)` to the P1 deny hunks. Do not ship the toggle with its own writer softer than the file it writes.

---

**NM-04 / MEDIUM / `--project-root` is a suppressed, unvalidated arbitrary-path posture-write primitive.**

EVIDENCE: `night-mode.py:654-659` — `--project-root` with `help=argparse.SUPPRESS` ("test seam only") — and `:662` `Path(args.project_root).resolve()` with no confinement. `_atomic_write_json` mkdirs parents (`:187`). My probes wrote `.claude/settings.local.json` + `.claude/state/` into `/private/tmp/.../nm1` and `nm2` with no complaint. A Bash-capable agent can therefore arm `acceptEdits` in **any** repo on the machine, including targets where P1's deny and these tests are not installed (ADR-185's own "(−) Adopter installs do not gain the P1 deny rule until they upgrade"). The only guard is the CI refusal. Docs describe the write target as "the per-machine overlay", singular.

FIX: reject a `--project-root` that is not `REPO_ROOT` or does not resolve under it, unless an explicit test-only env var is set; require the target to already contain `.claude/settings.json`.

---

**NM-05 / MEDIUM / The audit trail is blind on exactly the paths a forensic record exists for.**

EVIDENCE: `_emit_audit` is called only at `:391` (successful `on`) and `:518` (successful `off`), always with `result="applied"`. Every refusal (`_refuse_if_ci` `:239`, malformed-input exits `:322`/`:423`/`:432`/`:454`), every idempotent no-op (`:316`, `:413`), and every read-back/write failure (`:354`/`:363`/`:382`/`:489`/`:499`/`:506`) returns without emitting. This contradicts the P2 wrapper it is designed against — `p2-audit-action.patch:130-133` "once per `on` / `off` invocation, whether applied, idempotent-noop, refused, or failed" — leaving `_NIGHT_MODE_RESULT_ENUM` members `noop`, `refused`, `failed` permanently dead. A CI-refusal or a repeated malformed-input probe (an attacker mapping the guard) leaves no row. AC-7 as written only asks for the applied case, so the gap passes the AC.

FIX: emit on every terminating path with the matching `result`; keep it inside the existing try/except no-op envelope.

---

**NM-06 / MEDIUM / The boot advisory hardcodes "ratified" and does not restrict to the overriding layer — it will assert a false ratification claim in any repo that ratified a non-manual posture.**

EVIDENCE: `ceo-boot.py` `_NIGHT_MODE_RATIFIED_DEFAULT_MODE = "manual"` (literal) and `_night_mode_advisory_rec()` renders whenever the resolver-effective mode is any string `!= "manual"`, with no check on `sources["permissions"]`. If a repo's **tracked** `.claude/settings.json` ratifies `acceptEdits` or `plan`, every boot renders a high-severity line reading "not the ratified 'manual'" — about the Owner-ratified value itself — and burns one of the five rec slots forever. Tests only cover the local-layer case (`arm()` writes `settings.local.json`; `test_any_non_manual_string_renders` likewise); there is no project-layer test.

FIX: derive "ratified" from the project layer's own `permissions.defaultMode` and render only when the winning layer is `local` (or `user`) and differs from it.

---

**NM-07 / MEDIUM / W0's kill-gate was declared PASS on evidence weaker than the plan demanded, and T0.3's stated basis is wrong.**

EVIDENCE: plan `:231-235` requires for T0.1 "transcript de sessão **mais** `resolve_settings()`". `W0-EVIDENCE.md` T0.1 records resolver-level only and defers the harness proof: "obediência do HARNESS ao defaultMode não é diferenciável em headless … a prova harness-level fica para a primeira sessão interativa pós-`on`". AC-1 ("sessão nova ⇒ sessão inicia em acceptEdits") is therefore unverified while W0 is stamped PASS. Separately, T0.3 states `_CANONICAL_GUARDS` = "{team.md, frontend-team.md, pitfalls-catalog.yaml, skills/{core,frontend}/*/SKILL.md}" — the live list is ~100 patterns spanning lines 113-331 including `.claude/hooks/*.py`, `.claude/hooks/_lib/**/*.py`, `scripts/install.sh`, `scripts/upgrade.sh`. The "ZERO hits" conclusion happens to hold, but the recorded basis is a five-entry abbreviation, and the same abbreviation is what makes NM-03 read as harmless.

FIX: mark AC-1 explicitly OPEN pending the first interactive session; correct the T0.3 record to the real guard list and re-derive the "ZERO hits" claim from it.

---

**NM-08 / MEDIUM (gating, not a code defect) / W1+W2 exist while P1/P2 are still staged patches; AC-7 and AC-8 are unsatisfiable today.**

EVIDENCE: worktree `permissions.deny` has no `settings.local.json` entry (P1 unlanded); `night_mode_toggled` is absent from `_KNOWN_ACTIONS` (P2 unlanded), so `_emit_audit` → `emit_generic` drops every event with a breadcrumb — zero audit rows. Plan §Security: "Até P1 landar, o plano não deve ser executado: enviar o toggle sem a regra de deny cria exatamente o caminho de escalação que o toggle deveria tornar deliberado." Ceremony bundle is well-formed: `shasum -a 256 -c MANIFEST.sha256` → 3/3 OK; both patches `git apply --check` clean against canonical HEAD `91e690aa1da0ca2a0eb2446bd764240e892b2035`.

FIX: do not merge this branch before the ceremony lands; run AC-8's positive probe after.

---

**NM-09 / LOW / No directory fsync after `os.replace`; contract item 2's durability is file-level only.** EVIDENCE: `_atomic_write_json:199-205` fsyncs the temp fd but never the parent directory; `cmd_off:482` `os.unlink` of the overlay is likewise unfenced. A power loss can lose the rename after a passing read-back — the exact torn-state class item 2 cites (S286). FIX: `os.open(parent, O_RDONLY)` + `os.fsync` + close after `os.replace`, best-effort.

**NM-10 / LOW / `off` restores non-string `prev_value` unvalidated, silently disabling the Owner's entire overlay.** EVIDENCE: same line as NM-01; `prev_value` may be any JSON type. A dict/list/number lands in `permissions.defaultMode`, which CC 2.1.220's schema rejects — and a schema mismatch makes the harness skip the **whole** settings file (the S286 live-fire the code documents at `:19-20`), so every other key in the Owner's overlay dies. Direction is fail-open toward the project's `manual`, so not an escalation — but silent. FIX: covered by NM-01's closed-set validation.

**NM-11 / LOW / `off`'s success line asserts the ratified posture unconditionally.** EVIDENCE: `:523-527` always prints "Next session starts on the ratified posture", including after restoring `plan`, `acceptEdits` (NM-02) or a tampered value (NM-01) — both probe transcripts above show the false line. FIX: name the restored value's relation to the project layer, or drop the clause.

---

CONFIRMED-CORRECT (adversarially checked, no finding): FileLock wraps both whole mutation sequences (`:307`, `:409`; parent mkdir handled in `filelock.acquire`, timeout → `FileLockTimeout` → `main`'s catch-all → exit 2, no write). Atomic write is same-dir mkstemp + flush + fsync + `os.replace` with mode preservation and temp cleanup on any `BaseException`. Read-back re-parses and treats any failure as mismatch, and marker creation is correctly skipped on settings-read-back failure (`test_readback_failure_exits_nonzero_and_skips_marker`). Malformed input is fail-CLOSED byte-for-byte on both `on` and `off`. Ordering is settings→marker / settings→marker-removal. CI refusal is fail-closed on env-var **presence**. Nothing writes outside `<root>/.claude/{settings.local.json,state/}` and no canonical path is touched (tracked-settings byte-equality pinned by `test_tracked_project_settings_untouched`). Both toggle targets are gitignored (`git check-ignore`: `.gitignore:78`, `.gitignore:71`) — tracked tree stays clean (AC-1's second half). The boot advisory is fail-OPEN end to end, is a rec and never a `CheckResult`, uses `_sanitize_for_recs` on every interpolated value, resolves its root at call time from `CLAUDE_PROJECT_DIR`, and is emitted through one shared helper into both hand-mirrored pipelines with parity asserted (`test_severity_pipeline_carries_same_text_high`) and the `recs[:5]` cap proven non-restructured. `grep -rn bypassPermissions` over every changed/new file: no code path constructs the literal (the residual is behavioral — NM-01). P1's patch adds `Edit(.claude/settings.local.json)` **and** `Write(.claude/settings.local.json)` to **both** `.claude/settings.json` (appended after `Bash(curl * | bash)`, preserving the positional `install.sh DENY_BASELINE_ENTRIES` mirror and `check_harness_config.DENY_BASELINE`'s subset invariant) and `templates/settings/settings.base.json`; no test asserts an exact deny list, so neither hunk reds parity. Gates green in the worktree: 53/53 new tests pass, `verify-counts.sh` no drift (commands 27, adrs 185), `check-claude-md-claims.py` exit 0, `check-test-env-hygiene.py` clean, `build-plugin.py --check` in sync, `COMMAND-SKILL-HOOK-MAP.md` regenerated (not hand-edited).

VERDICT: REJECT

NM-01 is a live, reproducible escalation to `bypassPermissions` through the feature's own disarm command, defeating D1, D2 and the P1 deny in one step; NM-02 makes the posture permanently weak along the plan's own documented recovery path; NM-03 leaves the single writer softer than the file it guards. NM-01 + NM-02 + NM-03 must be fixed and re-reviewed, and the P1 patch must be regenerated to cover the marker (and preferably the script) before the ceremony runs. This branch must not merge before P1/P2 land (NM-08).
