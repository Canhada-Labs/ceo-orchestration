# Lane Claude — painel de 6 lentes com refutacao adversarial

Workflow `wf_00bee7e7-a08`: 6 finders independentes + 1 refutador por lente + sintese.
13 agentes, 0 erros, 1.811.833 tokens de subagente, 24min.

Apenas findings que SOBREVIVERAM a refutacao adversarial aparecem abaixo.
O campo `why` e do refutador, nao do finder — inclui rebaixamentos e correcoes.

---

## P2 — conventions-acceptance-command-wrong-runner

**CLAIM.** AC line 172-173 names `python3 -m unittest discover -s .claude/scripts/tests` — a runner CI never uses. CI runs a two-pass pytest, and `unittest discover` skips `.claude/scripts/tests/conftest.py`, which is what seeds sys.path and registers the audit-dir isolation fixtures.

**FIX.** Replace the AC command with the CI commands verbatim: `python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -n auto -m 'not serial' --strict-markers` then the same paths with `-m 'serial'`; add that the new tests must also pass in the 3.9-3.12 matrix job (which additionally collects `.claude/hooks/tests/`).

**REFUTADOR.** Verified: validate.yml:424-425 is the two-pass pytest; the matrix job repeats it at :1448-1456 over 3.9/3.10/3.11/3.12. `.claude/scripts/tests/conftest.py` seeds `.claude/scripts` + `.claude/hooks` on sys.path and imports `_ceo_audit_isolation_session` from `_lib.test_isolation`; 23 modules in that tree reference pytest, and `serial` is a registered marker under `--strict-markers` (pytest.ini). Under `unittest discover` the parametrized tests silently do not run and conftest-dependent imports break. Downgraded from P1: CI is still the real gate, and the plan's own T1.3 mandates TestEnvContext, which independently isolates HOME and the audit env — so the audit-pollution horn of the claim is weaker than stated. The AC line is still wrong and must be fixed.

---

## P2 — conventions-doc-count-sites-incomplete

**CLAIM.** T2.2's doc list does not contain a single count-gated site, and the 26->27 edit lands in eight places across five files — one of which is CLAUDE.md, a Gate-1 cache-stable file the operating contract says may only be edited at closeout.

**FIX.** Enumerate the gated sites in T2.2 — CLAUDE.md:54, README.md:58 (table) + :185, npm/README.md:58 (table) + :121, docs/ARCHITECTURE.md:51 (tree comment) + :70 (table), docs/FAQ.md:106 — sequence the CLAUDE.md edit into the closeout per Gate-1 cache discipline, and keep CHEAT-SHEET/TROUBLESHOOTING as separate ungated adopter-surface tasks.

**REFUTADOR.** Verified: verify-counts.sh DOCS = CLAUDE.md, README.md, INSTALL.md, docs/ARCHITECTURE.md, docs/GUIA-COMPLETO.md, docs/FAQ.md, npm/README.md; metric `commands` is `exact` via prose rule `(\d+) slash commands` (:301) and TABLE_RULES `^Slash commands\b` (:322). Grep confirms exactly those eight `26` sites; CHEAT-SHEET/TROUBLESHOOTING carry no gated count. Downgraded from P1 because the plan already says to run verify-counts.sh before push and that gate enumerates every miss, so a missed site is loud, not silent. The genuinely additive defect is the CLAUDE.md closeout sequencing, which the plan never mentions.

---

## P1 — conventions-tamper-tripwire-fires-on-full

**CLAIM.** The §Security claim that the toggle leaves `settings_tamper_tripwires` attesting the ratified posture is false for `--full`: `permissions.defaultMode: bypassPermissions` in settings.local.json is exactly the payload that tripwire detects, so /ceo-boot goes RED and emits a `settings_tamper_detected` event every boot for the whole night-mode window.

**FIX.** Either drop `--full` from scope, or add a design section owning the interaction: state that `--full` makes check 21 red and emits one tamper breadcrumb per boot for the duration, and decide explicitly whether an Owner-acknowledged suppression is wanted — that suppression is itself a governance change needing an ADR, not a W2 task.

**REFUTADOR.** Verified end to end: `ceo-boot.py:1555` `check_settings_tamper_tripwires` scans the resolved multi-layer settings 'including the gitignored, sentinel-blind settings.local.json', lists class (d) `permissions.defaultMode: bypassPermissions`, maps 'findings present -> red', and side-effects one `settings_tamper_detected` emit per class. `effective_config.py` declares the rule at :178-181 (`equals:bypassPermissions`) and enforces it per layer at :534-542; LAYER_LOCAL is in LAYER_MERGE_ORDER (:76,:84) and resolves to `<project>/.claude/settings.local.json` (:318). `acceptEdits` matches no tamper class, so this is specific to `--full` — exactly as the candidate scoped it. This is the one place the plan states something about its own safety that is factually wrong.

---

## P2 — conventions-probe-misses-permissions-deep-merge

**CLAIM.** T0.1 probes only that local `defaultMode` beats project `manual`; it never asserts that the project deny baseline survives the overlay. Cheap to add, and a FAIL would be a hard kill rather than a pivot.

**FIX.** Extend T0.1: launch a session with a local-layer `permissions: {defaultMode: acceptEdits}` and verify a baseline-denied action (e.g. `Edit(PROTOCOL.md)`) is still denied; record it as its own evidence file and mark a FAIL as a kill, not a pivot to the fallback.

**REFUTADOR.** The probe gap is real — T0.1 names only defaultMode, and the deny baseline in `.claude/settings.json` (`Edit(PROTOCOL.md)`, `Edit(.claude/settings.json)`, `Edit(SPEC/**)`) is what a whole-key replace would drop. But the claim's framing is overstated and I corrected the severity: the repo already documents the answer — `effective_config.py:23-28` states the live harness deep-merges `permissions` ('allow/deny lists concatenate'), so this is an unprobed documented behavior, not a load-bearing unknown. It survives only because the plan's own doctrine is 'MUST be live-fire probed, not trusted' and the assertion costs one extra line in the same probe session.

---

## P2 — conventions-state-marker-path-ambiguous

**CLAIM.** 'state marker under the project's `~/.claude/projects/<slug>/` dir' is ambiguous between two live slug conventions and ignores the repo's own state-root resolver, risking the writer (T1.1) and the /ceo-boot reader (T2.1) disagreeing on one path.

**FIX.** Name the resolver, not a slug: marker at `${CEO_STATE_ROOT:-$HOME/.claude/projects/${CEO_PROJECT_NAME:-ceo-orchestration}/state}/night-mode.json`, resolved by a function at call time, and cite it in both T1.1 and T2.1 so writer and reader cannot drift.

**REFUTADOR.** Verified: both `~/.claude/projects/--Users-joaocanhada-canhada-labs-ceo-orchestration/` (CC-native, the long cwd-slug CLAUDE.md documents) and `~/.claude/projects/ceo-orchestration/` (framework dir holding audit-log/audit-key) exist on this box. `state_store.py:114 _state_root()` is the canonical resolver, honoring `CEO_STATE_ROOT` then `CEO_PROJECT_NAME` (default `ceo-orchestration`), documented in its module docstring and surfaced in docs/CHEAT-SHEET.md:129-130. Downgraded from P1: the failure mode is a banner that never renders, caught by the T2.1 test, not a governance or security hole.

---

## P1 — conventions-ceremony-rider-underspecified

**CLAIM.** R1 as written ('`_KNOWN_ACTIONS` += `night_mode_toggled`') is provably insufficient: the in-code invariant makes a bare addition fail the ghost-action guard test and reach the default-deny `else`, dropping every caller kwarg. It also skips the SPEC row and the golden regeneration.

**FIX.** Rewrite R1 to enumerate: (1) the `_KNOWN_ACTIONS` literal at audit_emit.py:154; (2) EITHER a dispatch-gate scrub branch with a field allowlist OR an explicit `_EMIT_GENERIC_PASSTHROUGH` entry (the invariant demands exactly one of the three); (3) the 'Required fields per v2 action' row in `SPEC/v1/audit-log.schema.md`, which is inside the same sentinel scope (`SPEC/v1/*.md` is guarded at check_canonical_edit.py:179); (4) `python3 .claude/scripts/check-audit-registry-coverage.py --write-golden` to regenerate `.claude/data/audit-registry.golden.txt`. Drop the candidate's 'floor lock bump' item — it is wrong.

**REFUTADOR.** Verified: audit_emit.py:1672-1680 states the trichotomy invariant and that 'A NEW action added to `_KNOWN_ACTIONS` therefore defaults to fail-closed (default-deny)'; the enforcing test `.claude/hooks/tests/test_audit_emit_ghost_action_guard.py` exists; `check-audit-registry-coverage.py` cross-checks the SPEC table and asserts the 8100-byte golden. I refuted one element of the candidate's fix: `.claude/scripts/.known_actions_floor.lock` is a 0-byte FileLock mutex, not a stored count — the floor lives in `_FLOOR_TABLE` (:39-44) and is a MINIMUM, so adding an action can never trip it. Kept at P1 because the failure lands at the most expensive gate in the repo (signed GPG ceremony + pair-rail inputs_hash recompute).

---

## P3 — conventions-check-claude-md-claims-does-not-gate-commands

**CLAIM.** T2.2 names `check-claude-md-claims.py` as a command-count gate; it contains zero references to commands. Factually wrong, but harmless — the plan also names the gate that actually runs.

**FIX.** Drop `check-claude-md-claims.py` from the T2.2 command-count gate list (or keep it only as a general CLAUDE.md drift check) and name `bash .claude/scripts/local/verify-counts.sh` as the gate for the 26->27 change.

**REFUTADOR.** Verified: `grep -ic command .claude/scripts/check-claude-md-claims.py` returns 0; the file exists (10790 bytes) and gates ADR/skill/test/plan claims only. The command count is gated solely by verify-counts.sh metric `commands`. Downgraded P2 -> P3: since T2.2 already lists verify-counts.sh alongside it, the wrong name costs at most one redundant script run — no execution path is broken by it.

---

## P2 — conventions-testenvcontext-state-isolation-gap

**CLAIM.** TestEnvContext sets HOME and the audit-log env but never `CEO_STATE_ROOT`, so an import-time marker-path constant in night-mode.py would resolve against the real `~/.claude` while the tests still pass.

**FIX.** State in T1.1 that the marker path is resolved inside a function at call time (so the isolated HOME applies), and in T1.3 that tests subclass TestEnvContext and set `CEO_STATE_ROOT` only via `unittest.mock.patch.dict` — never raw `os.environ[...] =` — with an assertion that the real `~/.claude` tree is untouched.

**REFUTADOR.** Verified: `_lib/testing.py:148-154` sets HOME, CLAUDE_PROJECT_DIR and the four CEO_AUDIT_LOG_* vars; `CEO_PROJECT_STATE_DIR` appears only in the subprocess-env helper at :291 and `CEO_STATE_ROOT` never. Call-time resolution is the safe pattern (`state_store.py:114`), because `_state_root()` reads `os.environ['HOME']` at call time and therefore lands inside the isolated tree. The env-mutation style constraint is real and CI-hard: `check-test-env-hygiene.py` runs as hard-fail at validate.yml:694-697, and `test_ceo_info.py:11-15` documents the patch.dict convention. Scoped correctly at P2 — a real pollution path with a one-line design fix.

---

## P3 — conventions-hyphenated-script-not-importable

**CLAIM.** T1.3 does not say how the tests load a hyphenated script; the repo has one exact precedent it should name.

**FIX.** Add one line to T1.3: load via `importlib.util.spec_from_file_location` with `REPO_ROOT = Path(__file__).resolve().parents[3]` and a `sys.path.insert` of `.claude/hooks` (the `test_ceo_info.py:29-44` pattern) — or rename the script `night_mode.py` and keep the slash command hyphenated.

**REFUTADOR.** Verified: `test_ceo_info.py:29-44` is exactly that pattern (parents[3], hooks on sys.path, `from _lib.testing import TestEnvContext`, `_load_module()` with spec_from_file_location('ceo_info', SCRIPT)), and `lesson_ranker.py` is the underscore-filename alternative. Real but low value — an implementer copying the nearest sibling test gets this right by default, and nothing fails silently. Downgraded P2 -> P3.

---

## P2 — conventions-ceo-boot-mirror-invariant

**CLAIM.** T2.1 cites only the recommendation-engine sanitization; the drift-prone invariant is that ceo-boot keeps two hand-mirrored recommendation functions in sync, with a <=5 cap that can drop a new rule.

**FIX.** Rewrite T2.1 to name both `_make_recommendations` (ceo-boot.py:2541) and `_recommendations_with_severity` (:2693), the shared sort-key + <=5 cap, the severity bucket the new rule gets, and the Sec MF-4 sanitizer; add a test asserting the two functions agree on the night-mode rule.

**REFUTADOR.** Verified: `:2670-2671` shows `recs.sort(...)` + `recs[:5]`; the header comment at :2674-2692 says 'Mirrors `_make_recommendations` ordering exactly (same sort key + <=5 cap)' and enumerates the severity buckets, and :2705 repeats 'Mirror `_make_recommendations` exactly (Codex CDX-W5-iter3-P1)'. The comment block itself records prior mirror-additions (PLAN-135 W1 S3 tamper rule, PLAN-153 rules 006/007), so this is a documented live drift class, not a hypothetical. P2 is right: a missed mirror produces a silently absent severity marker, not a crash.

---

## P2 — conventions-typed-ack-transport-undefined

**CLAIM.** The `--full` typed ack `NIGHT-MODE-FULL-I-ACCEPT` has no defined transport, so T1.3's '`--full` refuses without ack' is not yet a testable assertion; and any new `CEO_*` var carries a registration obligation the plan does not mention.

**FIX.** Specify the transport in the Approach (repo convention is an env-var pair, e.g. `CEO_NIGHT_MODE_FULL_ACK=I-ACCEPT`, mirroring `CEO_KERNEL_OVERRIDE`/`CEO_KERNEL_OVERRIDE_ACK`), register the name in `.claude/scripts/env-inventory.json`, and restate T1.3's assertion against that transport.

**REFUTADOR.** Verified: the plan gives the ack string but no channel. The env-var ack convention is real — `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` appears throughout `check_canonical_edit.py` (:152,:163,:218,:229,:238) and in docs/CHEAT-SHEET.md:132-133. The registration obligation is real: `env-inventory-check.py` token-scans framework code for `CEO_*`/`CLAUDE_*`/`ANTHROPIC_*` names and `--check` exits 1 on any name entering the surface without an inventory entry (nightly-hygiene dimension vi); `env-inventory.json` already carries 424 such entries. I discount one sub-claim: an interactive-stdin ack does NOT strictly need a pty (subprocess `input=` works), so that argument is weaker than stated — the transport gap and the inventory obligation carry the finding.

---

## P3 — conventions-command-frontmatter-and-terse-precedent

**CLAIM.** T1.2 leaves the command-file shape unspecified, and the plan never addresses why night-mode writes files when /terse — the repo's only other on|off|status toggle — deliberately does not.

**FIX.** Specify in T1.2: `description`, `argument-hint: "on|off|status [--full]"`, `allowed-tools: Bash`, plus the `$ARGUMENTS` parse section and the fenced `python3 .claude/scripts/night-mode.py $ARGUMENTS` procedure block; add one line to §Approach contrasting with /terse's no-file-write design.

**REFUTADOR.** Verified: all 26 files in `.claude/commands/` carry `description:` frontmatter; `terse.md:3` carries `argument-hint: "on|off|status"`; `ceo-info.md:2-3` carries `description` + `allowed-tools: Bash`. /terse does implement on/off/status purely via `terse_mode_start`/`terse_mode_end` audit breadcrumbs and writes no files. Downgraded P2 -> P3: the frontmatter is mechanical and an implementer copying `terse.md`/`ceo-info.md` gets it right; the /terse contrast is useful context rather than a defect, since night-mode's whole point (next-session settings layer) requires a write /terse does not.

---

## P3 — conventions-cheat-sheet-surface-unspecified

**CLAIM.** T2.2 lists docs/CHEAT-SHEET.md without saying what changes there, and the file has two tables the plan's 'boot-visible, reversible' goal depends on.

**FIX.** Spell out the two CHEAT-SHEET edits in T2.2: one row in the slash-command table (starts :19) for `/night-mode on|off|status`, and one row in the env-var table (near :130, beside `CEO_STATE_ROOT`) if a new `CEO_*` ack or state var is introduced.

**REFUTADOR.** Verified: docs/CHEAT-SHEET.md has a slash-command table under '## Slash commands (Claude Code chat)' at :12 (18 `| \`/...` rows) and an env-var table containing `CEO_STATE_ROOT` at :130. Neither is count-gated by verify-counts.sh (CHEAT-SHEET is not in DOCS), so this is pure task-specificity, correctly rated P3.

---

## P2 — conventions-l2-level-contradicts-t14

**CLAIM.** The plan asserts both that the surface is 'VETO-relevant per PROTOCOL §Vetoes' (T1.4) and that the L3 trigger 'VETO-protected domain change' is not met (§Level). Those cannot both stand unargued, and the answer decides whether a debate is mandatory.

**FIX.** Resolve it explicitly in §Level before execution: either argue in one sentence that harness permission posture is not the PROTOCOL 'auth' domain (and keep L2 + the T1.4 security review), or accept L3 and run `/debate start PLAN-165` per CLAUDE.md §4. Fixing the `--full` tamper interaction first may make the L2 argument easy.

**REFUTADOR.** Verified against PROTOCOL.md: the mandatory-debate list at :135 reads 'Any change in a VETO-protected domain (e.g. financial math, auth, PHI handling)', and §Vetoes:157 gives the Staff Security Engineer veto over 'Any auth / token / input handling change'. Whether a harness permission-mode overlay is that 'auth' domain is genuinely arguable — which is exactly why the plan cannot leave the two sentences pointing opposite ways. P2 is correct: cheap to resolve, but the downside of getting it wrong is executing an L3 change without the mandatory debate.

---

## P1 — security-full-nullifies-deny-baseline

**CLAIM.** `--full` (bypassPermissions) plausibly voids the 24-entry native `permissions.deny` baseline; the plan never states that blast radius and W0 has no probe for it.

**FIX.** Add a fourth W0 probe (T0.4): under `defaultMode: bypassPermissions` in the local layer, does a `Read(~/.aws/**)` / `Read(**/.env)` deny rule still fire? Run it on a scratch install, not the live tree. If deny does not survive, `--full` must either not ship or the same merge-write must re-assert the full DENY_BASELINE into `settings.local.json`, with `status` printing the resolved deny-rule count and an AC asserting >= 24. Regardless of probe outcome, name the residual class in §Security: the credential-store Read entries (~/.ssh, ~/.aws, ~/.netrc, .env family) are the ones with NO hook-level twin.

**REFUTADOR.** Verified: deny has 24 entries (settings.json:768-790); effective_config.py:538-542 emits the 'nullifies the native permission floor' text; plan lines 179-183 describe --full only as 'a genuine control weakening'; W0 (116-129) probes only precedence, escalation, and guard inventory. The gap is real. Two corrections that drop this from P0 to P1: (a) the 'repo's own code asserts' evidence is a finding-text rationale in a tamper CLASSIFIER, not verified CLI behavior — docs/PERMISSION-MODEL-DESIGN.md:368 marks 'Native deny actually fires' as PENDING-LIVE, so the repo has never confirmed deny fires under ANY mode; (b) the governance half of the baseline (Edit(.claude/settings.json), Edit(PROTOCOL.md), Edit(SPEC/**)) is double-covered by _CANONICAL_GUARDS hooks, which are unaffected by permission mode (disableAllHooks is a separate key). The genuine residual is narrower than 'the entire 24-entry baseline'. Also non-default and typed-ack-gated. P1, not P0.

---

## P1 — security-audit-trail-absent

**CLAIM.** The plan's stated interim audit mechanism does not exist: `audit_log.py` is PostToolUse matcher `Agent`, so a Bash/`!` invocation of night-mode.py emits nothing into the HMAC chain, contradicting the Goal's 'audited'.

**FIX.** Delete the false sentence at plan lines 99-101 ('the L6 audit_log.py observer already chains the invocation forensically'). Then either promote the `_KNOWN_ACTIONS` += `night_mode_toggled` registration to a hard blocker on W1 (ceremony first, toggle second) or restate the Goal as 'boot-visible and reversible' with audit explicitly deferred. If promoted, add an AC: after `on` and after `off`, a matching `night_mode_toggled` line exists in audit-log.jsonl and `verify_chain()` still passes.

**REFUTADOR.** Verified by parsing settings.json hooks: audit_log.py is registered once, PostToolUse matcher 'Agent', _comment 'one JSONL line per Agent spawn'. The only PostToolUse Bash registrations are check_bash_canonical_forensic.py (docstring lines 1-12: emits only when write-shape operators reference a CANONICAL path — and .claude/settings.local.json is absent from _CANONICAL_GUARDS) and check_output_secrets.py (a secrets scanner). So the interim state is zero audit, not 'L6 observer only'. Not refutable as 'the plan already handles it': the plan acknowledges the DEFERRAL but asserts an interim mechanism that is factually absent. audit_emit.py IS in the pair-rail inputs manifest (line 27), so the plan's ceremony-routing reasoning is correct — only the interim claim is false.

---

## P1 — security-tamper-tripwire-collision

**CLAIM.** Plan §Security lines 184-185 ('tripwires keep attesting the ratified posture') is false for `--full`: writing bypassPermissions into the LOCAL layer is the exact scenario the repo has a test for, producing red /ceo-boot + a `settings_tamper_detected` emit.

**FIX.** Delete or scope the claim at 184-185 to the DEFAULT (acceptEdits) path. Then state explicitly how an operator distinguishes night-mode's bypass finding from a real T-05 tamper — the honest answer is the marker file, which means status/boot must cross-check marker-vs-resolved-config. Do NOT add a night-mode allowlist to FORBIDDEN_KEYS: that is a security-control weakening and re-enters the VETO gate under PROTOCOL.md:436 ('Security carve-out (hard rule)').

**REFUTADOR.** Strongest of the set; verified three ways. effective_config.py:177-181 FORBIDDEN_KEYS entry (surface settings / permissions.defaultMode / equals:bypassPermissions / TAMPER_PERMISSION_BYPASS); the runtime branch fires per layer with no layer exemption; _layer_paths() includes project_dir/.claude/settings.local.json as layer 'local'; ceo-boot.py:1605-1620 calls _emit_settings_tamper_detected_safe(findings) then returns 'red'. Decisive: .claude/scripts/tests/test_ceo_boot_tamper_tripwires.py:255-261 test_class_d_bypass_permissions_red constructs local_settings='{"permissions": {"defaultMode": "bypassPermissions"}}' and asserts red. Two scoping corrections: /ceo-boot is manual, so it is 'every boot check while --full is on', not literally 'every night'; and there is no collision at all on the default acceptEdits path. Severity P1 holds.

---

## P2 — security-acceptedits-undetectable

**CLAIM.** The default `on` mode (acceptEdits) has no independent detector anywhere in the repo, so the common path's only evidence is the plan's own marker file.

**FIX.** Do NOT put a FORBIDDEN_KEYS change in this plan's wave (see why). Instead: (a) derive the /ceo-boot line from `_lib/effective_config.resolve_settings(REPO_ROOT)` so the DEFAULT path has a resolver-backed signal rather than a marker-only one; (b) if an advisory acceptEdits-in-local-layer finding class is wanted, add it to the already-queued sentinel ceremony alongside `night_mode_toggled`, and say so in the Ceremony rider section.

**REFUTADOR.** The fact is verified: grep for 'acceptEdits' across .claude/hooks/_lib/ and .claude/hooks/*.py returns nothing; check_config_change.py:23 confirms a disk write to settings.local.json fires no ConfigChange event; .gitignore:78 confirms the layer is untracked. But the P1 framing overstates the exposure — acceptEdits does NOT nullify deny and does NOT disarm hooks, so every PreToolUse guard (canonical-edit, bash-safety, kernel deny) still fires; the machine is 'less prompt-y', not 'ungoverned'. And the proposed fix is repo-illegal as written: .claude/hooks/_lib/*.py is in _CANONICAL_GUARDS, so 'as part of THIS plan (not a rider)' would force exactly the sentinel ceremony the plan deliberately kept out of its wave. Survives at P2 with a repo-legal fix.

---

## P2 — security-banner-cosmetic-and-desyncable

**CLAIM.** §Security's 'the boot banner makes the state impossible to forget silently' overclaims: /ceo-boot is manual, and the banner is driven by a marker that is a different source of truth from the settings layer that actually weakens the machine.

**FIX.** Soften line 180-181 to what the banner is (an advisory reminder for operators who run /ceo-boot). Compute the banner from `_lib/effective_config.resolve_settings(REPO_ROOT)` — the same resolver the tamper tripwire uses — so it reflects what the harness will obey; demote the marker to decoration (timestamp, hostname, which mode night-mode wrote), never the presence signal.

**REFUTADOR.** Verified: the only SessionStart registrations are SessionStart.py and turbo_sessionstart.py; auto_boot.py:91 returns False unless CEO_AUTO_BOOT=='1', and CEO_AUTO_BOOT appears in settings.json only inside the :535 comment, never as a set value. Plan 96-98 does self-describe the line as advisory/fail-open, so the finding cannot claim the plan hides this — the surviving defect is narrower: the §Security sentence at 180-181 asserts a reliability the mechanism does not have, plus the marker/settings source-of-truth split is real. Downgraded P1->P2: it is a doc overclaim plus a cheap design-precision fix, and the compensating design (next-session semantics, explicit off, red tripwire on --full per the collision finding) already exists.

---

## P1 — security-snapshot-poisoning-off-restores-weak

**CLAIM.** `off` is specified as a replay of a captured value with no exclusion for values night-mode itself wrote, so `on --full` -> `on` -> `off` restores bypassPermissions while reporting success.

**FIX.** Make `off` an absolute idempotent restore to a known-good target — remove the key, or write the ratified `manual` — never a replay of a captured value. Record in the marker the exact value night-mode wrote and refuse to snapshot a value equal to it. Add tests for both poisoning orders: `on` -> `on --full` -> `off` and `on --full` -> `on` -> `off`.

**REFUTADOR.** Not refutable from the plan's own text. Lines 84-89 specify 'snapshot of any pre-existing permissions.defaultMode saved for restore'; 92-93 specify 'off restores the snapshotted value (or removes the key)'; the T1.3 test list (136-139) covers 'snapshot round-trip' and 'idempotent double-on/double-off' — 'double-on' means a same-args repeat and does not cover a mode CHANGE while on, which is the poisoning sequence; AC 168-169 tests off only from the plain-on state. I checked the more dangerous ordering the candidate names and it is the correct one: `on --full` then `on` snapshots bypassPermissions, and `off` then restores bypassPermissions while printing success — a fail-UNSAFE restore. P1 stands.

---

## P1 — security-toggle-script-and-command-unguarded

**CLAIM.** T0.3 makes 'ZERO _CANONICAL_GUARDS hits' the success criterion, leaving the repo's only permission-posture-mutating script and its operator trigger ordinary-writable — and night-mode's own acceptEdits window is precisely when an agent could rewrite them without a prompt.

**FIX.** Route `.claude/scripts/night-mode.py` and `.claude/commands/night-mode.md` into _CANONICAL_GUARDS via the already-queued sentinel ceremony (KERNEL HARD-DENY extension, same double-gate as PLAN-156-COUNCIL-GUARD-EXTENSION), and reword T0.3 so a guard hit is a design REQUIREMENT to satisfy, not a scope failure to avoid. Independently, make `off` verify by re-reading the resolved config rather than trusting its own write, so a tampered script cannot silently lie. If the Owner declines the ceremony cost, record that as a ratified accepted risk in §Security.

**REFUTADOR.** Every cited precedent verified verbatim. _CANONICAL_GUARDS carries no broad .claude/scripts/*.py or .claude/commands/*.md glob — only lessons.py, prune-lessons.py, lesson-restore.py, lesson_ranker.py (:129-132) and .claude/commands/council.md (:330), the latter with the rationale 'it is the operator entry point to egress' (:315-316) and the F3 note 'a file we choose not to ship is exactly the file an attacker would CREATE' (:319-322). Plan T0.3 (126-129) and Goal line 69 ('without touching any canonical-guarded file in the main wave') together confirm zero-hits is the plan's stated aim. The chain strengthens under scrutiny: editing .claude/scripts/*.py prompts under `manual` but does NOT prompt under the acceptEdits the toggle itself enables, so night-mode creates the exact window in which night-mode can be silently rewritten — self-referential, and compounded by the absent audit line and absent acceptEdits detector. P1.

---

## P1 — security-l2-misclassified-veto-contradiction

**CLAIM.** The plan asserts both 'VETO-relevant surface per PROTOCOL §Vetoes' (T1.4) and 'the L3 trigger VETO-protected domain change is not met' (§Level). Those cannot both stand.

**FIX.** Resolve the contradiction in one direction and say which. Either (a) reclassify L3, run `/debate start PLAN-165` per CLAUDE.md §4, and write an ADR for the permission-model decision (precedent surface already has docs/PERMISSION-MODEL-DESIGN.md); or (b) drop the 'VETO-relevant surface' sentence at 141-142 and justify why an authorization-posture toggle falls outside PROTOCOL.md:376's 'auth / token / input handling' domain. Given --full plus the queued ceremony rider, (a) is the defensible call.

**REFUTADOR.** The internal contradiction is verified verbatim and stands regardless of how PROTOCOL is read: plan 140-142 vs 198-203. PROTOCOL.md's 'When debate is mandatory (L3+)' block does list 'Any change in a VETO-protected domain ... the VETO owner must debate', and :376 assigns Security the veto over 'Any auth / token / input handling change'. One correction to the finding's confidence: PROTOCOL's Security block-rules are all web-app-flavored (tokens in insecure storage, CSRF, open redirects, PII in URL params, XSS, iframe sandbox) and none match a local permission-mode toggle, so 'the trigger is unambiguously met' is a stretch — the plan's escape is weak but not obviously wrong. What is not arguable is that the plan asserts VETO-relevance in one section and denies the resulting trigger in another. P1 in a repo whose product IS the gating.

---

## P2 — security-threat-model-row10-unreconciled

**CLAIM.** The plan ships a supported writer into the exact layer its own threat model classifies as the unmitigated T-05 rail-tamper vector, citing neither docs/threat-model.md row 10 nor PERMISSION-MODEL-DESIGN.md §10.2(c).

**FIX.** Cite both in Context §3 and state why a first-party writer into that layer is acceptable (gitignored, next-session semantics, explicit off, tripwire still fires). Add a W2 task amending docs/threat-model.md:2037 row 10 and PERMISSION-MODEL-DESIGN.md:336/:355-359 so the governance record reflects the new supported writer; route through the Security Engineer approval gate (PROTOCOL.md:402).

**REFUTADOR.** Verified verbatim. docs/threat-model.md:2037 row 10 lists 'permissions.defaultMode: bypassPermissions ... settings.local.json layer (T-05 class)' with the native-floor column reading 'None — settings.local.json is gitignored and sentinel-blind'. PERMISSION-MODEL-DESIGN.md:336 and :355 carry the matching prose. Plan Context (42-56) references neither and frames the layer purely as convenience that 'avoids the whole interaction class'. Not refutable on 'already handled' — the plan discusses tripwires in Context §4 but never the T-05 classification of the layer it writes to. P2 is correct: a governance-record gap, not a runtime defect.

---

## P2 — security-off-not-atomic-no-verify

**CLAIM.** The write contract is unspecified — no atomic write, no read-back verification, no exit-code contract, no behavior for absent/unparseable/foreign-content settings.local.json — and the failure asymmetry is unsafe: a failed `on` fails safe, a failed `off` leaves the weakened key.

**FIX.** Mandate tmp-file + os.replace (+ fsync) in T1.1; after every write, re-resolve via `_lib/effective_config.resolve_settings` and exit non-zero unless the resolved permissions.defaultMode equals the intended value. Add ACs for: local file absent, local file unparseable JSON (must refuse and exit non-zero, never clobber), local file carrying an unrelated `permissions` block (must preserve it), and interrupted write.

**REFUTADOR.** Verified: plan 84-95 specifies merge/snapshot/restore semantics with zero durability or verification language; ACs 166-175 are happy-path plus the --full-without-ack case. The asymmetry argument is correct and the unparseable-JSON case matters concretely — a naive merge-write onto malformed JSON either crashes mid-flight or clobbers operator content. The resolver already exists and is already imported by a non-_lib caller (ceo-boot.py:1605 calls resolve_settings(REPO_ROOT)), so read-back verification costs nothing and needs no ceremony. Minor evidence correction: the call is at :1605, not :1600. P2 correct — spec gap, not a shipped defect.

---

## P3 — security-status-reimplements-layer-resolver

**CLAIM.** `status` is specified to report per-layer provenance without naming the authoritative resolver, so a second layer-precedence implementation could report a posture the harness does not obey.

**FIX.** One line in T1.1/T1.3: `night-mode.py status` and the /ceo-boot line MUST call `_lib/effective_config.resolve_settings`; no local reimplementation of layer precedence. Add a test asserting status agrees with resolve_settings on a crafted 3-layer fixture (TestEnvContext-isolated).

**REFUTADOR.** The underlying facts check out — effective_config owns LAYER_MERGE_ORDER, _layer_paths() covering user/project/local/managed, and _read_json_layer 'NEVER raises — degraded-but-typed'; ceo-boot.py already imports it, so a read-only import from .claude/scripts/ has precedent and needs no ceremony. But the finding overstates: plan line 95-96 says status 'prints the effective posture ... and the layer each value comes from' — it never says 'reimplement', and any competent implementer would import the existing module. Marginal beyond security-banner-cosmetic-and-desyncable and security-off-not-atomic-no-verify, which both already demand the same resolver. Downgraded P2->P3: worth one sentence in the plan, not a blocker.

---

## P3 — security-no-ci-tty-fence

**CLAIM.** 'CI or headless-runner autonomy' is a declared non-goal with no enforcement anywhere in the waves or ACs.

**FIX.** Add to T1.1: refuse to run when `CI` or `GITHUB_ACTIONS` is set, and refuse `--full` when stdin is not a TTY (this also delivers the interactive-ack hardening from security-typed-ack-is-argv-not-presence). Add one test per refusal path in T1.3.

**REFUTADOR.** Verified: plan line 76 declares the non-goal and no wave item, AC, or script requirement enforces it; the /council no-CI fence precedent is real (check_canonical_edit.py:307-311, 'enforces the per-lane budget hard-kill, and carries the no-CI fence'). But the exposure is speculative — night-mode.py would only run in CI if something invoked it, and nothing would; gitignoring settings.local.json already means a CI write is discarded per-checkout. Value here is defense-in-depth plus subsuming the TTY hardening, not a live hole. Downgraded P2->P3.

---

## P3 — security-worktree-slug-scope-unspecified

**CLAIM.** The plan calls the toggle 'per-machine' but writes to a per-TREE file, and never says which .claude/ tree it targets in a repo that actively uses worktrees.

**FIX.** Resolve the settings target from CLAUDE_PROJECT_DIR explicitly and PRINT the absolute path written on every invocation of on/off/status; make `status` warn when the marker's recorded project path differs from the current tree. Also fix the wording: the toggle is per-repo-tree, not per-machine.

**REFUTADOR.** The worktree half is verified — .claude/worktrees/plan165/ carries its own complete .claude/ tree (own settings.json, hooks, commands), so an `on` in the main tree leaves a worktree session unchanged, and plan lines 84-91 name a repo-relative settings path and a cwd-derived marker dir with no resolution rule. The slug half is weaker than claimed: BOTH ~/.claude/projects/--Users-joaocanhada-canhada-labs-ceo-orchestration/ (path-slug, holds memory, matches CLAUDE.md) and ~/.claude/projects/ceo-orchestration/ (short, holds audit-log.jsonl per settings.json:351) exist — two conventions coexist, so 'the marker directory the plan assumes may not be the one in use' is hedged, not established. Impact is low: worktrees are for plan execution, not overnight autonomous runs. Downgraded P2->P3, narrowed to the per-tree mismatch plus print-the-path.

---

## P3 — security-stale-posture-comment

**CLAIM.** `_posture_comment` documents `disableAutoMode=true` two lines above the live `"disableAutoMode": "disable"`; the plan's Context §1 rests on this key and leaves the drift in place.

**FIX.** Fold a one-line _posture_comment correction into the already-queued sentinel ceremony alongside `_KNOWN_ACTIONS` += night_mode_toggled (and, if adopted, the _CANONICAL_GUARDS additions) — .claude/settings.json is guarded, so it cannot ride this plan's wave.

**REFUTADOR.** Verified exactly: settings.json:763 _posture_comment reads "disableAutoMode=true (no automatic permission-mode escalation mid-session)" while :764 carries "disableAutoMode": "disable" — the S286 hotfix 838527a changed the value and not the prose. Plan lines 32-37 correctly describe the string-enum reality, which makes this plan the natural place to notice it. Weakest form of survival: not PLAN-165's defect and it causes no runtime behavior change (the comment is a _-prefixed doc key). Survives at P3 purely because a ceremony touching settings.json is already queued and the marginal cost is one line.

---

## P2 — failuremodes-permissions-key-replacement-nukes-deny

**CLAIM.** CORRECTED: the 'live harness drops the deny baseline' mechanism is NOT established — but W0 still never asserts the deny floor survives the new layer, which is the only evidence standard the repo's own permission doctrine accepts.

**FIX.** Extend W0 T0.1 to assert, on the resolved/live view after the local write, that the 24 deny entries are still in force (or at minimum that `permissions.deny` is non-empty in the merged view the harness obeys). Cheaper and stronger: add a post-write self-check to `on` that calls `effective_config.resolve_settings()` and fails loud if `permissions.deny` shrank. Separately (pre-existing, not plan-caused): `/ceo-boot` has zero `deny` references — a resolved-settings deny-floor assertion belongs there.

**REFUTADOR.** REFUTED as stated at P0. The finding's own evidence contains the refutation: `effective_config.py:23-28` states the live harness deep-merges — '`hooks` from ALL layers run, and `permissions` allow/deny lists concatenate'. The per-top-level-key replacement at `:743-747` is that module's documented approximation of the harness, explicitly compensated for by scanning every layer individually; it is not evidence about harness behaviour. So branch (a) is contradicted by the repo, and branch (b) is a pre-existing resolver-fidelity note the plan does not create. A finding stated as a disjunction where one branch is repo-contradicted and the other is not plan-attributable does not carry P0. What DOES survive is narrow and real: `docs/PERMISSION-MODEL-DESIGN.md:355-360` mandates that only a resolved-settings assertion counts as proof the floor is armed, PLAN-165 introduces a brand-new layer into that resolution, and T0.1 (plan:118-121) probes only `defaultMode`. `check_harness_config.py:167-171` DEFAULT_SETTINGS_REL does scope its DENY_BASELINE subset check to `.claude/settings.json` + the template, confirming nothing else covers the merged view.

---

## P1 — failuremodes-audit-claim-false

**CLAIM.** The plan's audit fallback is factually false: `audit_log.py` is registered on matcher `Agent` only, so a `!`/slash-command invocation of night-mode.py emits no audit event — and the plan defers the dedicated action to a future ceremony on the strength of that false claim.

**FIX.** Delete the false sentence at plan:99-101. Then either pull ceremony rider R1 (`night_mode_toggled` in `_KNOWN_ACTIONS`) into this plan's gating so `on`/`off` are auditable on day one, or state explicitly in the plan and in `status` output that posture flips are UNAUDITED until that ceremony lands, and make that an Owner ratification item (a new OQ) rather than a footnote.

**REFUTADOR.** Could not refute; verified from the parsed settings tree, not by grep. Programmatic walk of `.claude/settings.json` hooks: PostToolUse carries exactly two relevant registrations — matcher `Agent` → `audit_log.py`, matcher `Bash` → `check_bash_canonical_forensic.py`. The forensic hook gates every emit behind `_is_canonical()` (`check_bash_canonical_forensic.py:63-69`, delegating to `check_canonical_edit._is_canonical`), and grep of that guard list shows only `.claude/settings.json`, `templates/settings/settings.base.json`, `templates/settings/*.json` — `.claude/settings.local.json` is absent. `check_config_change.py:22-23` independently confirms the third possible channel is dead too: 'blind to edits made entirely outside the harness (a text editor writing settings.local.json on disk fires no ConfigChange event)'. All three channels are silent. P1 stands: a plan justifying a deferral with a control that does not exist is exactly the class this repo's claim-verify discipline exists to catch.

---

## P1 — failuremodes-full-mode-trips-tamper-red-and-contradicts-threat-model

**CLAIM.** `--full` writes the exact key/value the tamper classifier flags in ANY layer: `/ceo-boot` goes RED with `settings_tamper_permission_bypass` every boot for the whole night, `gate_pass` flips false, and a HIGH `005-settings-tamper` recommendation fires — while the plan's Security note claims the tripwires keep attesting the ratified posture.

**FIX.** Correct plan:184-186 — the claim is true for `acceptEdits`, false for `--full`. Then choose: (a) drop `--full` (the plan already makes `acceptEdits` the default and OQ1 already recommends it), or (b) keep it and add a marker-correlated suppression so the boot rail can distinguish Owner-invoked night-mode from tamper, PLUS amend `docs/threat-model.md` row 10 in the same change — otherwise the repo ships a first-class tool that performs its own documented T-05 attack with preventive control 'None'.

**REFUTADOR.** Could not refute; verified end to end in code. `classify_tampering` (`effective_config.py:796-804`) loops EVERY layer and calls `_check_settings_layer`, which at `:534-543` emits `TAMPER_PERMISSION_BYPASS` on `permissions.defaultMode == 'bypassPermissions'` — the local layer is in `LAYER_MERGE_ORDER` (`:84-86`) and therefore in `resolved['layers']`. Consumer verified: `ceo-boot.py:1608-1620` returns `('red', ...)` and calls `_emit_settings_tamper_detected_safe(findings)`; `005-settings-tamper` is wired at `:2589/:2732/:2808` and mapped to `high` at `:2681`. `docs/threat-model.md` row 10 verified verbatim, including 'None' as the native preventive control. The only softening available is that this bites `--full` only, not the default `acceptEdits` path — but the plan's Security note is stated unconditionally, and `--full` is the branch the note is defending. P1 stands.

---

## P2 — failuremodes-double-on-destroys-snapshot

**CLAIM.** The snapshot is not specified as create-only, so a second `on` can re-snapshot the value the first `on` wrote — leaving `off` restoring `acceptEdits` instead of removing the key. The plan names the test but never states the invariant, so the test can be written to whatever the implementation does.

**FIX.** State the invariant in the Approach: the snapshot is written ONCE per on-cycle and never overwritten while it exists, and it must encode 'no pre-existing key' distinguishably (e.g. `{"had_key": false}`) from 'no snapshot recorded' — the two drive different `off` behaviour. Add an AC: `on; on; off` leaves `permissions.defaultMode` absent from the local layer.

**REFUTADOR.** Partially refuted, so severity drops. The plan is NOT silent: T1.3 (plan:139) explicitly requires an 'idempotent double-on/double-off' test, and 'idempotent' at the observable level already forbids the described end state. The finding's real residual is narrower than claimed — the invariant lives only in a test name, not in the Approach or the ACs, so the implementer defines the semantics after the fact. That is a genuine spec-tightening item on a plan this repo will execute from, but it is a specification gap on a draft with the test already named, not a design defect: P2, not P1. The 'snapshot storage location is never specified' sub-point is real but is the same defect as failuremodes-marker-slug-drift, so it is not double-counted here.

---

## P2 — failuremodes-marker-slug-drift

**CLAIM.** '`~/.claude/projects/<slug>/`' is ambiguous — three slug conventions are simultaneously live on this machine, and two env vars can move the target between shells. A writer/reader mismatch leaves the posture live with the banner silent.

**FIX.** Pin the marker to exactly one resolver: import `_state_root()` from `.claude/hooks/_lib/state_store.py` (importing `_lib` needs no ceremony; only editing it does) and have the `/ceo-boot` reader call the same function. Anchor the settings path on `$CLAUDE_PROJECT_DIR` or `git rev-parse --git-common-dir`, never cwd. Make `status` print both absolute resolved paths so a mismatch is one command away.

**REFUTADOR.** Could not refute; every fact checked out. `state_store.py:114-126` is verbatim as described — `$CEO_STATE_ROOT` else `$HOME/.claude/projects/${CEO_PROJECT_NAME:-ceo-orchestration}/state`, a FIXED short name. `CLAUDE.md` Gate 1 line 3 defines the memory slug as the absolute cwd path with `/`→`-`. `ls ~/.claude/projects/` confirms all three coexist: `ceo-orchestration/`, `-Users-joaocanhada-canhada-labs-ceo-orchestration/`, and `--Users-joaocanhada-canhada-labs-ceo-orchestration/` — the last carrying its own `state/` dir. The worktree case is not hypothetical: this review is reading the plan from `.claude/worktrees/plan165/`, where both the cwd-derived slug and the `.claude/settings.local.json` resolution differ from the main checkout. Held at P2 rather than P1 because the failure is a wrong-path write, self-evident the moment `status` is run once, and fully fixed by a one-import change — not a silent security regression.

---

## P2 — failuremodes-nonatomic-write-corrupts-local-layer

**CLAIM.** 'merge-writes' with no atomicity: a crash mid-write truncates settings.local.json, the harness skips it, and the boot tamper rail degrades to YELLOW with that layer's scan silently skipped. The plan also never says what to do when the EXISTING file is unparseable.

**FIX.** Temp file in the same directory + `flush()` + `os.fsync()` + `os.replace()` — the repo already ships the pattern at `_lib/cost_envelope.py:205 _atomic_write_state` (`os.replace` at :210). Separately and more importantly: if the existing `settings.local.json` fails to parse, REFUSE to write and exit non-zero with the path. Clobbering unparseable Owner data is worse than not toggling, and a fail-open-by-reflex implementer in this repo will otherwise catch the JSONDecodeError and default to `{}`.

**REFUTADOR.** Could not refute the mechanism, but the severity is inflated. Verified: the plan (84-92) says only 'merge-writes'; `effective_config.py:355-362` degrades a corrupt layer to `ok=False, data={}` so `_check_settings_layer` never scans it; `ceo-boot.py:1626-1632` then returns YELLOW 'no tamper indicators; N unparseable settings layer(s)'. The 838527a parallel the finding draws is real. Downgraded to P2 because the crash-window path needs an interrupt inside a sub-millisecond write of a small file, and atomic-write is standard practice the repo already has a template for — it is an implementation requirement, not a design flaw. The clobber-unparseable-input half is the part with no timing dependence and is the reason this survives at all; I have folded it to the front of the fix.

---

## P2 — failuremodes-crash-between-writes-both-orders-bad

**CLAIM.** Two writes (settings + marker) with no ordering and no reconciliation: marker-then-settings leaves the banner asserting ON while the next session still boots `manual` — the Owner sleeps believing the run is armed and wakes to a session stalled at the first prompt, exactly the need the plan quotes.

**FIX.** Remove the two-source-of-truth design. Derive `status` and the `/ceo-boot` line from the RESOLVED settings (`_lib/effective_config.resolve_settings()` + `sources`) — the thing that actually governs the session — and demote the marker to a pure annotation (when, by whom, which mode was intended). A crash in either order then self-heals, because the authority is the file the harness reads.

**REFUTADOR.** Could not refute the design point, though the crash framing overstates it. Verified that the plan specifies no ordering (84-98) and that the boot line is marker-gated (96-98). Downgraded to P2 because the trigger is a crash between two adjacent small writes — genuinely rare — so this is not a P1 on likelihood. It survives at P2 on a stronger basis than the crash window: the marker and the settings file are two independent sources of truth for one fact, and the marker is the one that is NOT authoritative yet IS what the banner reads. Every other marker-related finding here (slug drift, double-on snapshot, off-without-marker) is a symptom of that split; this is the cleanest statement of the class and its fix subsumes them. Note it dissolves entirely under failuremodes-fallback-design-is-strictly-safer, since a launcher has no persisted state to desync.

---

## P2 — failuremodes-typed-ack-is-model-typable

**CLAIM.** The `--full` typed ack is satisfiable by the model, not only by a human: the shipped slash-command shape runs the script from a model-issued Bash call with model-controlled `$ARGUMENTS`, and the command's own `.md` will document the literal. The stdin alternative is worse — no TTY under a slash command, so `input()` raises EOFError, a traceback rather than a refusal.

**FIX.** Move the ack to a channel the model cannot fabricate: `CEO_NIGHT_MODE_FULL_ACK=I-ACCEPT` exported by the Owner in an Owner-typed `!` command, matching the `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` precedent (`check_canonical_edit.py:152,163,218,229,238,250,289,319`). Have `night-mode.md` instruct the model to STOP and ask the Owner rather than set it. Add an AC: the ack cannot be satisfied from `$ARGUMENTS` alone.

**REFUTADOR.** Could not refute the structural claim, but there is an unacknowledged mitigation that costs it a level. Verified: `.claude/commands/ceo-info.md` has `allowed-tools: Bash` and a Procedure block `python3 .claude/scripts/ceo-info.py $ARGUMENTS`, so the shape is exactly as described, and the `CEO_KERNEL_OVERRIDE_ACK` / `CEO_SENTINEL_UNLOCK_ACK` precedents are real (`check_canonical_edit.py:942,964`). What the finding omits: the ratified posture is `defaultMode: manual`, so the Bash call invoking night-mode.py itself raises a permission prompt showing the Owner the full command line including the ack literal — and `acceptEdits` (the mode a prior night-mode would have set) auto-approves edits, not arbitrary Bash, so escalation to `--full` still prompts. The residual risk is therefore 'Owner rubber-stamps a prompt', not 'model silently escalates to bypassPermissions'. That is a real weakening of a control the plan calls unsoftenable (plan:179-183), but it is P2, not P1. The EOFError point is correct and is why the fix must not route through stdin.

---

## P2 — failuremodes-ceo-info-reports-zero-hooks

**CLAIM.** The moment night-mode succeeds, `/ceo-info` reports `effective: .claude/settings.local.json`, `effective_hook_registrations: 0` — it uses whole-file-wins, not a merge. The plan names `/ceo-info` output as the W0 probe evidence artifact, so the probe's own instrument produces a false 'no hooks effective' reading on success.

**FIX.** Do not use `/ceo-info` as the W0 evidence instrument — use `_lib/effective_config.resolve_settings()` + `sources`, which models the layers correctly. Separately, `_effective_settings()` should not overwrite `hook_count` from a layer that has no `hooks` key (report per-key provenance, or skip the overwrite), and `.claude/commands/ceo-info.md`'s 'last valid file wins as the effective override' line should be corrected — it contradicts the real resolver.

**REFUTADOR.** Could not refute; verified line by line and confirmed the consequence is NEW rather than pre-existing. `ceo-info.py:183-187` `_settings_candidates()` returns `[settings.json, settings.local.json]`; `:190-222` loops both and, inside the try for every valid file, sets `effective = entry['path']` and `hook_count = n` where `n` is counted from that file's `hooks` block alone — last valid file wins wholesale. A night-mode-created local layer has no `hooks` key, so `n = 0`. This is not a latent bug that already fires: `ls .claude/settings.local.json` → No such file, so today `/ceo-info` correctly reports settings.json with its real count, and PLAN-165 would be the first thing to trip it. `.claude/commands/ceo-info.md` §Path/settings resolution confirms the doc carries the same wrong model. P2 is right — it is an instrument-fidelity defect, not a control failure.

---

## P3 — failuremodes-managed-layer-silently-outranks-local

**CLAIM.** Narrowed: on an adopter machine carrying an enterprise managed-settings.json that pins `permissions.defaultMode`, night-mode's write is a silent no-op — marker written, banner ON, session boots manual. Not reproducible on the Owner's machine, so a one-machine W0 probe cannot detect it.

**FIX.** One cheap line that covers the whole silent-no-op class, managed or not: after writing, have `on` call `resolve_settings()` and verify `sources['permissions'] == 'local'`; if a higher layer won, exit non-zero, do NOT write the marker, and name the layer that won. Make `status`'s already-promised 'layer each value comes from' (plan:95) authoritative rather than cosmetic. Note in docs that CLI-arg overrides sit above local and are structurally invisible to any file resolver (`effective_config.py:19-21`).

**REFUTADOR.** Mechanism confirmed, exposure refuted, so severity drops two levels. `LAYER_MERGE_ORDER` at `effective_config.py:84-86` is `(user, project, local, managed)` with 'later wins', and the docstring `:7-13` states `managed > local > project > user`; `_managed_settings_paths()` (`:312-322`) probes the three OS locations at runtime. But neither exists here — `ls` of both `/Library/Application Support/ClaudeCode/managed-settings.json` and `/etc/claude-code/managed-settings.json` returns No such file — so there is no live break, and the finding itself scopes to 'any machine with an enterprise managed-settings.json'. For a public OSS framework with corporate adopters that is a plausible portability concern, not a defect in this plan's execution: P3. It survives only because the recommended fix is a post-write verification that costs one call and closes every silent-no-op path, including the ones the other findings describe.

---

## P3 — failuremodes-byte-preserved-ac-unmeetable

**CLAIM.** The AC '`settings.local.json` unrelated keys byte-preserved' is unsatisfiable by a JSON load/dump round-trip, so the test will be written to a weaker claim than the AC states — in a repo that runs its derived-count gates at tolerance=0.

**FIX.** Restate the AC semantically: '`json.load()` of the file before and after `on`/`off` is equal except for `permissions.defaultMode`'. If byte-preservation is genuinely wanted, say so explicitly — it forces a surgical textual edit instead of a parse/serialize round-trip, which is a materially larger and more fragile task and should be a recorded decision, not an implied one.

**REFUTADOR.** Could not refute the technical point — a `json.load` → mutate → `json.dump` cycle demonstrably does not preserve indentation width, separator spacing, trailing newline, or key order — and the repo's own settings files are a live counter-example (`.claude/settings.json` interleaves `_credentials_comment`:50, `_deny_baseline_comment`:762, `_posture_comment`:763 among real keys at a specific indent, none of which a default `json.dump` reproduces), with `INSTALL.md:427` confirming hand-creation is the expected adopter path. Downgraded from P2 to P3: this is a wording defect in one acceptance criterion with no runtime consequence, and the file does not exist today, so on the Owner's machine night-mode would be creating it from scratch and byte-preservation would be vacuous on first use. It survives because an unsatisfiable AC gets silently weakened at test-writing time, which this repo treats as a governance smell.

---

## P2 — failuremodes-banner-is-not-a-forcing-function

**CLAIM.** The Security section's 'impossible to forget silently' — also the stated reason to reject a TTL in OQ2 — is false: `/ceo-boot` is opt-in (`CEO_AUTO_BOOT=1`) and no mandatory gate runs it, so the only warning sits behind a command nobody invoked.

**FIX.** Render the warning from a surface that always runs — `turbo_sessionstart.py` is registered unconditionally on SessionStart matcher `""` (`.claude/settings.json:540`) and already emits the turbo what's-on line, which also makes the posture visible to the DAYTIME session that inherits it. Or accept OQ2's TTL so the weakened posture expires on its own. Either way, strike the current banner-only rationale from OQ2 before it goes to the Owner — the recommendation is sound but the reason given for it is not.

**REFUTADOR.** Could not refute the factual core. Verified `.claude/settings.json:535` describes the SessionStart registration as '(opt-in CEO_AUTO_BOOT=1) /ceo-boot nudge', and `CLAUDE.md` §0 Gates 1-3 — the MANDATORY protocol — never invoke `/ceo-boot`. Held at P2 rather than dropped, even though OQ2 already flags expiry for Owner ratification, because the defect is precisely in the ratification input: the Owner is being asked to choose 'banner only' on a premise ('visible') that does not hold, which is how a bad default gets ratified. The fix is cheap and the alternative surface already exists and always fires, so there is no reason to ship the weaker rationale.

---

## P2 — failuremodes-fallback-design-is-strictly-safer

**CLAIM.** The plan ranks the `night-claude` launcher as the fallback contingent on a W0 probe failing. The flag it needs is already confirmed present on the pinned CLI, and the launcher is safer than the file-write design on every failure mode found in this pass.

**FIX.** Invert the ranking: make `claude --permission-mode acceptEdits` the primary and the `settings.local.json` write the fallback. The availability question W0 was going to answer is already settled — verify by re-running `claude --help` at execution and record that as the T0.1 artifact. If adopted, W1 shrinks to a documented launcher plus a `status` that reports the resolved posture, and the `--full` / tamper-tripwire / threat-model-row-10 conflict never arises.

**REFUTADOR.** Could not refute, and the evidence got stronger than the finding claimed. The finding argued the launcher avoids the other failure modes; I verified the premise it depends on and which the plan left as an open risk: on the live pinned CLI, `claude --version` = 2.1.220 and `claude --help` lists `--permission-mode <mode>` with choices `acceptEdits, auto, bypassPermissions, manual, dontAsk, plan`. Per `effective_config.py:19-21` CLI-arg overrides sit between managed and local, so the flag outranks both the project posture and any local layer — which also means it cannot be silently outranked the way the file write can. The elimination argument holds by construction: no file written ⇒ no clobber, no lock question, no marker desync, no local-layer bypassPermissions for the tripwire to flag, no false `/ceo-info` zero-hooks reading. Kept at P2 rather than raised, because this is a design-ranking recommendation on a draft rather than a defect in shipped behaviour — but it is the highest-leverage single change in this set, and the plan's own stated ordering condition for it is already satisfied.

---

## P1 — counts-01

**CLAIM.** W2.2 omits the only generated derived surface gated on the command count: docs/COMMAND-SKILL-HOOK-MAP.md must be regenerated with gen-command-skill-hook-map.py --write or validate.yml goes red — and the two gates W2.2 DOES name both stay green while it is stale (false-green preflight).

**FIX.** Add an explicit W2.2 step: `python3 .claude/scripts/gen-command-skill-hook-map.py --write`, commit docs/COMMAND-SKILL-HOOK-MAP.md in the same commit as .claude/commands/night-mode.md, and state that the diff is 3 places (the §1 per-command row, the §2 reverse index if the command names a skill, and §5 `- Commands: 27`). If the command body cites `.claude/scripts/night-mode.py`, _SCRIPT_PATH_RE (generator:54) picks it up into the §1 'backing scripts' cell automatically.

**REFUTADOR.** Confirmed, could not refute. validate.yml:288-291 runs `gen-command-skill-hook-map.py --check`; check() (generator:389-393) regenerates to a temp file and returns 1 on drift; §5 line 127 is `- Commands: 26`, emitted by generator:349 `len(commands)`. Ran both gates live: map --check EXIT=0, verify-counts --no-tests EXIT=0 today. Decisive point the candidate under-sold: grep over Makefile, scripts/ and .claude/scripts/local/ finds NO other call site, and .git/hooks holds only *.sample — so there is no local pre-push catch, and the plan's own named gates (check-claude-md-claims, verify-counts) do not cover this doc. The plan's phrase 'regenerate derived surfaces' is not enough of a mitigation to refute: it is attached to a docs list in which nothing is generated (see counts-03), so an executor reading W2.2 literally never reaches this generator. P1 stands (hard CI red).

---

## P3 — counts-02

**CLAIM.** W2.2 names check-claude-md-claims.py as a gate for 26->27; that script has no command check, so it contributes zero coverage for this metric (it is superfluous, not a coverage hole — verify-counts.sh, also named, does cover the metric).

**FIX.** Drop check-claude-md-claims.py from the 26->27 gate sentence and keep verify-counts.sh as the real oracle for that metric; run the claims script only as part of the normal pre-push set. Do NOT add a 'Slash command count' ClaimCheck as the candidate proposes — it would duplicate verify-counts.sh's existing exact rule and add churn to a script for no new coverage.

**REFUTADOR.** Facts confirmed, severity refuted down from P1. CHECKS holds exactly five entries (ADR count:141, Core:150, Frontend:160, Total skills:168, PLAN count:175); live `--verbose` prints five PASS lines and 'PLAN count: optional claim absent (ok)' — so it is genuinely inert for PLAN-165 (the new plan file does not even trip the PLAN check, since claim_regex r'(\d+)\s+PLAN\s+files' matches nothing in CLAUDE.md). But the 'false assurance' framing is overstated: the same W2.2 sentence names verify-counts.sh, which enforces the command count at tolerance=0 across 8 sites via the prose rule r'(\d+) slash commands' (verify-counts.sh:301) and TABLE_RULES ('commands','exact', r'^Slash commands\b') at :322. Nothing goes uncaught because of this line; it is a precision nit, not a P1.

---

## P1 — counts-03

**CLAIM.** W2.2's doc list (CHEAT-SHEET, TROUBLESHOOTING, FAQ) names only one file that actually carries the number; the 8 gated sites — including CLAUDE.md, which §0 says is edited only at closeout — are hand-written literals with no generator, so 'regenerate derived surfaces' is not a procedure for them.

**FIX.** Replace 'regenerate derived surfaces' with the explicit 8-site list: CLAUDE.md:54, README.md:58 (table) + :185 (bash comment), docs/ARCHITECTURE.md:51 (tree comment) + :70 (table), docs/FAQ.md:106, npm/README.md:58 (table) + :121. Add: docs/GUIA-COMPLETO.md is in DOCS but carries no command count (no edit needed), and CHEAT-SHEET/TROUBLESHOOTING stay as content tasks only. Add the ordering note that CLAUDE.md:54 collides with the Gate-1 cache-discipline rule, so either the whole sweep lands at closeout or the push is deliberately sequenced.

**REFUTADOR.** Confirmed by direct grep across CLAUDE.md/README/INSTALL/docs/npm and by reading verify-counts.sh:238-244 (DOCS) with rules at :301 and :322. The 8 sites are exactly right. docs/CHEAT-SHEET.md carries no command count (its §Slash commands table is a curated subset; grep for the number returns only unrelated PLAN-022 examples) and docs/TROUBLESHOOTING.md carries no numeric claim — so 2 of the 3 docs W2.2 names are irrelevant to this metric while 5 of the 6 real gated files are unnamed. tolerance=0 and validate.yml runs the drift check, so this is a hard CI red, not cosmetics. P1 stands.

---

## P2 — counts-04

**CLAIM.** README.pt-BR.md carries the command count and is NOT in verify-counts.sh's DOCS list, so 26->27 drifts silently in a shipped, user-facing doc that is already stale on five other counts — and the same hole exists in docs/README.md:80, which the candidate missed.

**FIX.** Pick one explicitly in W2.2: (a) add 'README.pt-BR.md' (and ideally 'docs/README.md') to DOCS in .claude/scripts/local/verify-counts.sh — noting that file is `.claude/scripts/local/*`, inside check_pair_rail._L3_PLUS_GLOB_PATTERNS, so the edit draws a pair-rail review; or (b) hand-edit README.pt-BR.md:56 in the W2.2 sweep and file the pre-existing staleness as a separate debt item. Do not leave it unmentioned.

**REFUTADOR.** Fact confirmed, severity corrected P1->P2. DOCS (verify-counts.sh:238-244) = CLAUDE.md, README.md, INSTALL.md, docs/ARCHITECTURE.md, docs/GUIA-COMPLETO.md, docs/FAQ.md, npm/README.md — README.pt-BR.md absent. Staleness confirmed but the candidate's line numbers are off by one on two rows: line 53 = 'Scripts de hook (em disco) | **55**' vs live 57; line 54 = 'Hooks ligados | **44**' (and '46 registros') vs live 47/48; line 56 = 'Slash commands | **26**'; line 57 = 'ADRs | **180**' vs live 184; :165 '# 22 slash commands'; :166 '# 180 ADRs'. Additional unwatched site the candidate missed: docs/README.md:80 '| Slash commands | **22** |' (already stale by 4). Downgraded because the failure mode is doc-only drift in a translated README with zero CI, functional, or security consequence — unlike counts-01/03, nothing goes red and nothing breaks.

---

## P3 — counts-05

**CLAIM.** docs/ARCHITECTURE.md:270 states the command count in a phrasing no verify-counts rule matches ('22 of them') — a watched FILE with an unwatched PHRASE, already stale at 22 vs live 26.

**FIX.** In the W2.2 sweep, rewrite line 270 to the self-gating phrasing '…(27 slash commands — e.g. `/spawn`, `/debate`, …)' so the existing prose regex catches it forever, fixing the current 22->27 error in the same edit.

**REFUTADOR.** Confirmed: ARCHITECTURE.md:270 reads '(22 of them — e.g. `/spawn`…)'; neither r'(\d+) slash commands' (:301) nor the table rule r'^Slash commands\b' (:322) can match it, while the file's other two sites (:51, :70) do match — so verify-counts reports parity for a file that is off by four. Severity corrected P2->P3: this is pre-existing prose debt, causes no CI red, no gate failure, and no behavioral risk; its value is that PLAN-165 is already editing that file's two gated sites, making the fix nearly free. Same class as counts-04 but one parenthetical rather than a whole unwatched user-facing README.

---

## P1 — counts-07

**CLAIM.** Ceremony rider R1 is written as a one-liner, but adding night_mode_toggled to _KNOWN_ACTIONS trips two hard CI reds (sha256 + two count pins), a third hard red (SPEC table drift), one silent drift (the live golden is ungated), and a fail-closed default that would make the emit a no-op.

**FIX.** Rewrite R1 as a six-item checklist: (1) _KNOWN_ACTIONS += night_mode_toggled; (2) add the row to SPEC/v1/audit-log.schema.md's 'Required fields per action' table; (3) `check-audit-registry-coverage.py --write-golden` + commit .claude/data/audit-registry.golden.txt; (4) rebaseline _EXPECTED_KNOWN_ACTIONS_SHA256 (test_audit_emit_api_contract.py:485, asserted :760) and the 323 literals at :772 and test_audit_emit_plan163_lifecycle_actions.py:166 -> 324; (5) choose and document the scrub path (dedicated dispatch branch vs _EMIT_GENERIC_PASSTHROUGH) so the emit is not default-denied; (6) recompute inputs_hash. File (d) as separate debt: validate.yml:480 should run the gate with --check, not --verbose only.

**REFUTADOR.** All five sub-claims confirmed; only line numbers needed correcting. (a) the sha constant is at test_audit_emit_api_contract.py:485 (not :720 — :719 is its comment), asserted :760, count literal :772. (b) test_audit_emit_plan163_lifecycle_actions.py:166 pins 323. (c) _compute_drift:610 `missing_in_schema = known_actions - schema_actions` against SCHEMA_REL='SPEC/v1/audit-log.schema.md' (:104), and SPEC/v1/*.md + SPEC/**/*.md are in _CANONICAL_GUARDS (check_canonical_edit.py:179-180). (d) refutation attempt failed: I checked whether any unit test pins the LIVE golden — test_check_audit_registry_coverage.py exercises --write-golden/--check only inside tmpdir fixture repos (:122-124), and validate.yml:480 passes --verbose only, with build_registry_golden:744 folding known_actions into the inventory, so a stale 327-line golden really does sail through CI. (e) audit_emit.py's own comment states a new _KNOWN_ACTIONS member 'defaults to fail-closed (default-deny) until the author either gives it a scrub branch or consciously lists it here', enforced by test_audit_emit_ghost_action_guard.py (file exists). Both gates are green today (registry --check EXIT=0), so every one of these is a fresh break introduced by the rider. P1 stands.

---

## P3 — counts-09

**CLAIM.** T2.1 does not commit to WHERE the /ceo-boot night-mode line lives; if implemented as a Tier-S check rather than a recommendation, five hard-coded count literals in two test files break.

**FIX.** State in T2.1: 'implemented as a RECOMMENDATION entry (_make_recommendations), NOT a new TIER_S_CHECKS/TIER_A_CHECKS member — the literals at test_ceo_boot.py:59, :112, :639 (23) and test_ceo_boot_enhanced.py:256 (10), :280 (33), :285 (23) must stay untouched.'

**REFUTADOR.** Literals confirmed and live values match (imported ceo-boot.py: TIER_S=23, TIER_A=10); the candidate said 'four ... in two files' but there are five/six — :285 was missed. Severity corrected P2->P3 because the plan is closer to committed than the candidate allows: T2.1 already says 'advisory line off the marker (fail-open; mirrors the existing recommendation-engine sanitization)' and 'never blocks boot', which points at _make_recommendations (tested at test_ceo_boot.py:412-470 with no count pin), not at the check registry. The value is cheap explicitness, not a budgeted CI red.

---

## P3 — counts-10

**CLAIM.** .claude/commands/*.md is watched by no count gate, and .claude/commands/ceo-boot.md is stale at '15 Tier-S checks' (7 sites) vs live 23 — the exact doc T2.1 touches. The docs/SKILL-ACTIVATION-MODES.md site the candidate cites does not exist.

**FIX.** While W2/T2.1 is already editing that surface, correct ceo-boot.md's 15 -> 23 at lines 2, 10, 24, 34, 36, 42, 128 and docs/GOVERNANCE.md:146; record the class as debt ('.claude/commands/*.md and docs/GOVERNANCE.md carry numeric claims no gate watches'). Drop docs/SKILL-ACTIVATION-MODES.md:57 from the list.

**REFUTADOR.** Confirmed with one refutation: ceo-boot.md repeats '15' at :2, :10, :24, :34, :36, :42, :128 while test_ceo_boot.py:59 and the live import both give 23; docs/GOVERNANCE.md:146 also says '15 Tier-S digest'. But docs/SKILL-ACTIVATION-MODES.md:57 is REFUTED — that line is the /coverage-audit anti-pattern paragraph, and no '15 Tier-S' string exists in that file. No gate covers .claude/commands/*.md numeric prose (not in verify-counts DOCS; check-claude-md-claims reads CLAUDE.md only) — confirmed. Severity P2->P3: pre-existing prose debt, no CI or behavior impact, adjacent-cheap only because T2.1 is already in that file.

---

## P2 — counts-11

**CLAIM.** The AC 'Templates and shipped defaults byte-identical (no adopter drift)' is wrong for the adopter surface: /night-mode ships to every adopter via install.sh and to the plugin namespace as /ceo:night-mode — and the plan carries no security note that a permission-posture-flipping command reaches adopter trees.

**FIX.** Reword the AC to what is true and testable: 'templates/ and the tracked posture/settings files are byte-identical; the new command intentionally ships to adopters via .claude/commands (install.sh:1266) and to the plugin tier (build-plugin.py:411), so night-mode must be inert-by-default in an adopter tree (no marker, no settings.local.json write until explicitly invoked).' Add a §Security bullet stating the command ships to adopters and that --full/typed-ack is the only path to bypassPermissions there too.

**REFUTADOR.** Confirmed. scripts/install.sh:1265-1266 records op 'install_commands_and_catalogs' and calls `install_one ".claude/commands"` (whole directory); scripts/build-plugin.py:411 `n_cmd = copy_dir(".claude/commands", "commands", "*.md")` and the README template at ~:315 emits '**{ncmds} commands**'. Verified the candidate's negative claims too: templates/ contains no commands copy (find returned nothing), dist/ is gitignored (.gitignore:192, `git ls-files dist` = 0), and neither .claude-plugin/plugin.json (17 lines) nor marketplace.json carries a command count — so build-plugin.py --check (check_manifests:133-141, MANIFESTS = REPO/'.claude-plugin' at :40) cannot catch anything here. Partial defense of the plan: in context ('Non-goals: changing the shipped default posture; templates keep the fail-closed keys') 'shipped defaults' plausibly means posture, not file inventory — but 'no adopter drift' is unqualified and the missing adopter security note is real, so P2 holds rather than P1.

---

## P3 — counts-12

**CLAIM.** The tracked .claude/settings.json documents the ILLEGAL boolean form of the very key this plan is about: _posture_comment (:763) says disableAutoMode=true while the live value (:764) is "disable" — the S286 hotfix's missed sibling, sitting next to rollback instructions.

**FIX.** Add a one-line rider item to the queued sentinel ceremony (settings.json is canonical-guarded, so it does NOT belong in W1/W2): correct _posture_comment to `disableAutoMode='disable' (string enum; the ONLY legal value — a boolean makes CC 2.1.220 skip this file entirely, S286 838527a)`.

**REFUTADOR.** Verified verbatim and the plan's own line numbers check out: :763 _posture_comment contains "disableAutoMode=true (no automatic permission-mode escalation mid-session)" and ends with the rollback sentence; :764 is `"disableAutoMode": "disable"`; :767 is `"defaultMode": "manual"`. Nothing gates prose inside settings.json, so this survives indefinitely. P3 is correct — it is a comment, inert at runtime, and the fix is one line inside an already-queued ceremony; its value is that the comment is the exact confusion PLAN-165 exists to resolve.

---

## P3 — counts-13

**CLAIM.** T0.3 reaches the right answer for its four paths from _CANONICAL_GUARDS alone (so it is not 'falsely clean' as claimed), but it should still name check_pair_rail._L3_PLUS_GLOB_PATTERNS, because any W2 fix to verify-counts.sh (counts-04/05) lands in `.claude/scripts/local/*` and draws a pair-rail review the plan has not budgeted.

**FIX.** Restate T0.3 as: 'confirm ZERO hits for each planned write path against (i) check_canonical_edit._CANONICAL_GUARDS — matching path-by-path, since `.claude/commands/council.md` proves an exact-path command entry exists even though there is no `.claude/commands/**` glob — and (ii) check_pair_rail._L3_PLUS_GLOB_PATTERNS; and record that any verify-counts.sh edit falls under (ii).'

**REFUTADOR.** Facts verified but the claim as written is refuted and rewritten. _CANONICAL_GUARDS (check_canonical_edit.py:113-331) has no `.claude/commands/**` glob and only four named `.claude/scripts/*.py` (:129-132), so `.claude/commands/night-mode.md` and `.claude/scripts/night-mode.py` are genuinely unguarded — i.e. reading only the one list T0.3 names yields a TRUE clean for all four planned paths, not a false one. _L3_PLUS_GLOB_PATTERNS (check_pair_rail.py:157-169) does include `.claude/scripts/local/*`, and check_arbitration_kernel._KERNEL_PATHS (:72+) is a third list — but the kernel list covers only .claude/hooks/** and is irrelevant to every path in scope, so I dropped it from the fix. Severity P3 confirmed; the surviving value is the conditional coupling to counts-04/05 plus the council.md near-miss (guards are per-path, so 'commands/ is unguarded' is the wrong inference to carry forward).

---

## P3 — counts-14

**CLAIM.** The AC's test command (`unittest discover -s .claude/scripts/tests`) does not match how CI runs that tree — different runner, no marker split, no xdist, and it omits the optimizer root and the env-hygiene AST gate.

**FIX.** Replace the AC command with the two exact CI invocations: `python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -n auto -m 'not serial' --strict-markers --tb=no -q` then the same with `-m 'serial'`; and add `python3 .claude/scripts/check-test-env-hygiene.py --verbose` so T1.3's TestEnvContext commitment has an oracle.

**REFUTADOR.** Confirmed against validate.yml:419-425 (the two-pass pytest step, both roots, --strict-markers) and the separate hard-fail step 'TestEnvContext hygiene — AST check' running check-test-env-hygiene.py at ~:694-697. This is the repo's own logged failure class (pre-commit/local subset green while CI is red). Severity stays P3 rather than P2 because the same AC bullet already says 'suites + governance gates green (V1)', which commits the executor to the full gate set — so the defect is imprecision in the AC's oracle, not an unguarded path to a red main.

---

## P2 — planschema-rider-kernel-gate-wrong

**CLAIM.** The Ceremony rider mis-states the gate on `_lib/audit_emit.py`: it is an ARBITRATION-KERNEL path with NO sentinel escape, so folding R1 into 'the already-queued sentinel ceremony' will be hard-denied.

**FIX.** Rewrite the rider to name the real gate: Owner-signed sentinel AND `CEO_KERNEL_OVERRIDE=<slug>` + `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` exported in the Owner's ceremony shell (pre-declare the slug, e.g. `PLAN-165-NIGHT-MODE-AUDIT-ACTION`). Note that the override emits a `veto_triggered` / `reason_code=kernel_override_used` audit event and that a spawned agent cannot set it — so the step is Owner-executed, not CEO-executed.

**REFUTADOR.** CONFIRMED against the live tree. `.claude/hooks/check_arbitration_kernel.py:90` carries the literal `".claude/hooks/_lib/audit_emit.py"` inside `_KERNEL_PATHS`, and the module docstring (lines 31-40) states verbatim: 'Absent BOTH env vars, the edit is blocked regardless of any sentinel' plus the anti-forgery rationale. Corroborated by `test_audit_emit_callsite_coverage_matrix.py:30-43`, whose `KNOWN_4SOURCE_GAPS` entries are annotated 'pending kernel ceremony' (5x) — the routine idiom for this file is kernel, not sentinel. SEVERITY CORRECTED P0->P2: the rider is explicitly declared out of this plan's waves ('NOT this plan's wave'), so nothing in W0-W2 is blocked; the failure mode is a fail-CLOSED hard-deny surfaced the instant the ceremony is attempted, i.e. wasted Owner ceremony time, not a silent or unsafe outcome. Not P0/P1 — no plan wave depends on it and there is no data-loss or bypass risk.

---

## P2 — planschema-rider-incomplete-4source

**CLAIM.** R1 is scoped as a one-line `_KNOWN_ACTIONS +=`, but registering an action is a 4-source, multi-guarded change; as written it reddens two invariant tests and silently drops every caller field.

**FIX.** Expand R1 into the full unit: (i) `_KNOWN_ACTIONS` member, (ii) an explicit `action ==` dispatch-gate scrub branch with a field allowlist (or a conscious `_EMIT_GENERIC_PASSTHROUGH` / `_RESERVED_ACTIONS` entry, the latter requiring an ACCEPTED gating ADR), (iii) a `SPEC/v1/audit-log.schema.md` row, (iv) `test_audit_emit_coverage` coverage + >=1 fixture under `.claude/hooks/tests/fixtures/` (or a `KNOWN_4SOURCE_GAPS` exemption, ceiling 25, currently 6), and (v) correct the note to 'TWO pair-rail manifest paths change'.

**REFUTADOR.** Every sub-fact CONFIRMED. `test_audit_emit_callsite_coverage_matrix.py:1-11` states the 4-source contract verbatim. `audit_emit.py:1673-1679` states the ghost-action invariant verbatim including 'A NEW action added to `_KNOWN_ACTIONS` therefore defaults to fail-closed (default-deny)'. `_RESERVED_ACTIONS` (1653-1661) does map members to gating ADRs. `_KNOWN_ACTIONS` is at line 154 exactly as the plan says. The two-manifest-path claim is CONFIRMED: `.claude/governance/pair-rail-inputs-hash-manifest.txt` contains BOTH `.claude/hooks/_lib/audit_emit.py` AND `SPEC/v1/audit-log.schema.md` (18 entries total), and `SPEC/**/*.md` is in `_CANONICAL_GUARDS` (check_canonical_edit.py:179-180). SEVERITY CORRECTED P1->P2 for the same reason as the sibling finding: the rider is out of this plan's waves, so the incompleteness costs a failed ceremony attempt, not a shipped defect. The candidate's demand for an ADR is partly refuted — an ADR is only mandatory if the action lands in `_RESERVED_ACTIONS`; a scrub branch + SPEC row + fixture needs no ADR.

---

## P1 — planschema-audit-observer-claim-false

**CLAIM.** The Approach's audit story is factually wrong — `audit_log.py` does not observe Bash/`!` invocations — so 'the L6 audit_log.py observer already chains the invocation forensically' is false and the Goal word 'audited' is unsupported.

**FIX.** Pick one and state it plainly: (a) declare night-mode UNAUDITED until the kernel ceremony lands, and say so in the Goal AND in `/night-mode status` output; or (b) pull the audit registration into the critical path, which makes this a kernel-ceremony plan (not L2); or (c) name a Bash-side emitter that actually fires. Whichever is chosen, add an explicit acceptance criterion for the audit trail — the plan currently has none.

**REFUTADOR.** CONFIRMED and STRONGER than the candidate stated. Parsing `.claude/settings.json` (48 hook registrations total) yields exactly ONE `audit_log.py` entry: `PostToolUse`, `matcher: "Agent"`. No Bash matcher routes to it. The only PostToolUse-Bash hook is `check_bash_canonical_forensic.py`, whose docstring scopes it to commands 'referenc[ing] a canonical governance path' — and night-mode writes the gitignored, non-canonical `settings.local.json`, so it would not fire either. Additionally, `grep -rn '\bL6\b'` over `docs/*.md`, `.claude/hooks/*.py` and `PROTOCOL.md` returns ZERO hits: the label 'L6' is not defined anywhere in the repo, so the sentence is an invented citation on top of a false one. P1 held (not deflated): in a framework whose stated product is auditability, the plan's own Goal claims 'audited' and the false claim is the sole justification for deferring the dedicated action.

---

## P2 — planschema-tripwire-claim-inverted

**CLAIM.** The Security-notes claim that not editing tracked files keeps `settings_tamper_tripwires` and `harness_config_gate` 'attesting the ratified posture' is wrong in both directions: the tamper tripwire reads the local layer and goes RED under `--full`; the harness gate never reads the local layer and keeps attesting a posture that is no longer effective.

**FIX.** Replace the bullet with the verified behaviour and a decision: state that `--full` intentionally turns `settings_tamper_tripwires` RED and emits a `TAMPER_PERMISSION_BYPASS` finding, and record explicitly whether that is accepted noise (documented in `status` + the boot line) or needs an Owner-intent-aware branch (which is itself a canonical `_lib/effective_config.py` edit). Drop `harness_config_gate` from the attestation claim entirely — it is blind to the layer being changed.

**REFUTADOR.** CONFIRMED in both directions. `_lib/effective_config.py:177-181` carries `{surface: 'settings', key: 'permissions.defaultMode', rule: 'equals:bypassPermissions', tamper_class: TAMPER_PERMISSION_BYPASS}` with surface 'settings' defined at 127-131 as 'checked in EVERY settings layer'; the layer classifier fires on `mode == "bypassPermissions"`. `ceo-boot.py:1555-1572` documents the scan as 'user / project / local / managed — including the gitignored, sentinel-blind settings.local.json'. Conversely `check_harness_config.py:167-171` `DEFAULT_SETTINGS_REL = ('.claude/settings.json', 'templates/settings/settings.base.json')` — settings.local.json is absent. SEVERITY CORRECTED P1->P2: the RED path only triggers under the already-heavily-gated `--full`, and a RED tripwire on a genuine bypass is arguably correct behaviour, not a defect; the residual harm is an unverified plan claim plus one unhandled operational consequence, which is moderate, not serious.

---

## P2 — planschema-derived-surface-gap-ci-red

**CLAIM.** T2.2's derived-surface list names a tool with no command-count logic, writes the wrong path for the count gate, and never names the actual hard CI gate for a new command.

**FIX.** Rewrite T2.2 as concrete commands: `python3 .claude/scripts/gen-command-skill-hook-map.py --write` (then `--check` to confirm), `bash .claude/scripts/local/verify-counts.sh --no-tests --quiet` (note the `local/` segment), and a hand-edit pass over the UNWATCHED surfaces — `README.pt-BR.md:165` and the `(N of them)` prose at `docs/ARCHITECTURE.md:270`. Drop `check-claude-md-claims.py` from the command-count claim.

**REFUTADOR.** Core facts CONFIRMED. `grep -in 'command' .claude/scripts/check-claude-md-claims.py` returns ZERO hits — it has no command logic at all. The count gate lives at `.claude/scripts/local/verify-counts.sh` (the bare `.claude/scripts/verify-counts.sh` does not exist), invoked at `validate.yml:112`; its `DOCS` list (lines 238-242) excludes `README.pt-BR.md`, and its `commands` regex is exactly `r'(\d+) slash commands'` (line 301), which cannot match `docs/ARCHITECTURE.md:270` 'The slash commands in `.claude/commands/` (22 of them'. Both surfaces are ALREADY stale at 22 against a live count of 26 — bumping to 27 widens the drift. The `gen-command-skill-hook-map.py --check` hard gate is real (`validate.yml:291`). SEVERITY CORRECTED P1->P2: the candidate's 'as written, W2 lands CI-red' is OVERSTATED — T2.2 does say 'regenerate derived surfaces', which a competent executor reads as covering the generated map, so CI-red is not guaranteed. What is certain is the misnamed tool, the wrong path, and two stale unwatched surfaces.

---

## P1 — planschema-level-l2-understated

**CLAIM.** The `## Level / debate` L2 argument is unsupportable: the plan hits multiple PROTOCOL L3 triggers, plans no ADR despite the 3+-module approval rule, and its own W1 text contradicts the VETO assertion.

**FIX.** Reclassify L3: run `/debate start PLAN-165 "<proposal>"` before execution, add an ADR capturing the three cross-cutting choices a future maintainer would re-litigate (local-layer-over-project precedence, the toggle mechanism, and the `--full` gate), and route T1.4 through the Staff Security Engineer VETO rather than as an ordinary wave item.

**REFUTADOR.** CONFIRMED, and the strongest evidence is internal to the plan. `PROTOCOL.md:130-135` lists verbatim 'Change in 3+ modules', 'New feature affecting multiple subsystems', 'Any change in a VETO-protected domain'; `PROTOCOL.md:402` requires 'Architecture changes touching 3+ modules — needs ADR with trade-off matrix'. The plan's real surface spans `.claude/scripts/`, `.claude/commands/`, `.claude/scripts/tests/`, `ceo-boot.py`, `docs/` + derived map, root count-claim docs, PLAN-163's body, plus the kernel/SPEC rider — comfortably 3+ modules, and no ADR is proposed anywhere. Decisively, the plan CONTRADICTS ITSELF: W1 T1.4 says 'VETO-relevant surface per PROTOCOL §Vetoes' while §Level asserts 'the L3 trigger "VETO-protected domain change" is not met'. `PROTOCOL.md:376` assigns the Staff Security Engineer veto over 'Any auth / token / input handling change', which a permission-floor toggle plainly is. I partially refute the candidate's use of `PROTOCOL.md:436-442`: that security carve-out governs how review FEEDBACK is received, not how a change is CLASSIFIED — the self-contradiction in the plan body is the load-bearing evidence, not the carve-out. P1 held: skipping a mandatory L3 debate is a governance-gate bypass in a governance framework.

---

## P2 — planschema-vcheck-doctrine-bypassed

**CLAIM.** The plan is inside the §13 prospective window yet declares ZERO `Check:` lines, passing the enforcer only vacuously because the Waves section uses plain bullets instead of checkboxes.

**FIX.** Convert T0.1-T2.4 to `- [ ]` checkboxes and add block-level `Check:` lines directly under each wave heading, matching PLAN-164's shape — e.g. W1 `Check: python3 -m pytest .claude/scripts/tests/test_night_mode.py -q`; W2 `Check: python3 .claude/scripts/gen-command-skill-hook-map.py --check && bash .claude/scripts/local/verify-counts.sh --no-tests --quiet`; doc-only units `Check: none (doc-only)`.

**REFUTADOR.** CONFIRMED by executing the real enforcer against the worktree file. `validate_governance_fast._vcheck_scan_body(PLAN-165)` returns `[]` — zero errors — while `grep -c 'Check:'` on the same file returns 0 (PLAN-164 returns 20). The vacuity mechanism is exact: `_VCHECK_CHECKBOX_RE = r'^\s*-\s\[[ xX~]\]\s*(.*)$'` only matches real checkboxes, and `_VCHECK_SECTION_PREFIXES = ('wave', 'progress log', 'items', 'sprint plan')` — so PLAN-165's `- T0.1 ...` bullets under `### W0` are invisible to the scan, and its `- [ ]` items under `## Acceptance criteria` sit outside an enforced section. Frontmatter `created: 2026-08-02` >= `_VCHECK_ENFORCE_FROM = 2026-06-12` and `status: draft` is in `_VCHECK_STATUSES`, so the plan IS in the enforcement window. P2 held: real doctrine bypass, trivially fixable at draft stage, no shipped consequence.

---

## P3 — planschema-missing-required-sections

**CLAIM.** The plan omits PLAN-SCHEMA §5 body sections, including `## How to continue` (the session-durability section) and `## Success criteria` (the section §4 names as the done-gate).

**FIX.** Add `## How to continue` containing the literal first message a fresh session should send, and rename `## Acceptance criteria` to `## Success criteria` (or add it as the done-gate checklist). `## Progress log` is worth adding once the session budget is corrected.

**REFUTADOR.** Facts CONFIRMED: `PLAN-SCHEMA.md:413-425` lists the seven sections; `:392` states verbatim 'executing -> done is the quality gate: all success criteria must be met (see the plan's own `## Success criteria` section)'; PLAN-165 has neither `## How to continue` nor `## Success criteria`, while PLAN-164 carries both (lines 282, 293) plus `## Progress log` (244). SEVERITY CORRECTED P2->P3 on two verified grounds the candidate omitted: (a) §5 is explicitly permissive — 'Plans of any non-trivial size SHOULD contain these sections' — not MUST; (b) `validate_governance_fast._check_plan_schema` (lines 185-206) validates only filenames and subdirectory names, so NOTHING mechanically enforces body sections. The `## Acceptance criteria` section already serves the done-gate role, so only `## How to continue` is genuinely absent with no substitute. Cosmetic-plus, not moderate.

---

## P2 — planschema-ac-not-verifiable

**CLAIM.** Several acceptance criteria are not mechanically verifiable, and the headline test AC names a runner that is not the CI gate.

**FIX.** Rewrite each AC as a command plus expected exit/output: use the CI marker split (`python3 -m pytest .claude/scripts/tests/ -n auto -m 'not serial' --strict-markers` then `-m 'serial'`), replace 'byte-preserved' with 'parse-equal (json.load round-trip)', use `git status --porcelain` over tracked paths, name `/ceo-info` (which reads both layers) as the posture oracle, and give on-disk paths for the security review and the codex verdict. Add the missing ACs for the audit trail, the W0 fallback branch, and OQ ratification.

**REFUTADOR.** Every sub-fact CONFIRMED. (a) `validate.yml:424-425` runs `python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -n auto -m 'not serial' --strict-markers` then the `serial` pass — pytest, not `unittest discover`; `.claude/scripts/tests/conftest.py` exists, and `mcp-smoke.yml:208` records the exact gotcha 'unittest discover doesn't load root conftest.py', so a green unittest run is not evidence of V1 green. (b) A stdlib `json.dump` merge-write cannot preserve bytes — parse-equality is the checkable property. (d) `ceo-info.py:187` returns `[base/'settings.json', base/'settings.local.json']` and :213 comments that the local layer 'is the effective override' — it is the obvious oracle and the plan never names it. (c), (e), (f) are correct as untyped/absent. P2 held.

---

## P2 — planschema-w0-gate-has-no-predicate

**CLAIM.** W0 is declared the 'kill/pivot decision point' but defines only evidence artifacts, no pass/fail predicate — a gate whose criterion is 'evidence exists' cannot kill or pivot.

**FIX.** State the predicate inline: T0.1 PASSES iff, with `permissions.defaultMode: "acceptEdits"` in `.claude/settings.local.json` and `"manual"` in the project file, `/ceo-info` reports the effective mode as acceptEdits AND a non-allowlisted Edit executes without a prompt; otherwise FAIL -> pivot to the `night-claude` launcher fallback. Give T0.2 an equivalent observable. Record the predicate in the plan body, not only the transcript.

**REFUTADOR.** CONFIRMED by reading the plan: T0.1/T0.2 name destinations ('Evidence (session transcript + `/ceo-info` output`) -> .claude/plans/PLAN-165/probes/') and a consequence ('FAIL -> pivot') but never define what constitutes FAIL. The file contains zero `Check:` lines (verified by grep), so no mechanical predicate exists anywhere. `PLAN-SCHEMA.md` §13.1 doctrine ('Declaring the check at plan-time forces the author to know, before execution starts, what deterministic evidence will close the unit') is real, and the PLAN-164 contrast is verified — its W0 fixed N, the statistic and the escalation threshold in-body before the wave ran (lines 94-107). P2 held: this is the plan's own declared decision point and it is unfalsifiable as written.

---

## P2 — planschema-adopter-surface-contradiction

**CLAIM.** The Non-goal 'adopter behavior unchanged' and the AC 'Templates and shipped defaults byte-identical (no adopter drift)' are both satisfiable while every adopter install silently gains a posture-weakening command.

**FIX.** Either exclude the command (and script) from the installed set and say how, or drop the 'adopter behavior unchanged' non-goal and add an AC covering the INSTALLED surface plus an adopter-facing doc note that `/night-mode --full` disables the ask-first floor. Note the exposure is wider than the candidate says — the script ships too.

**REFUTADOR.** CONFIRMED and broader than claimed. `scripts/install.sh:1266` is a bare `install_one ".claude/commands"` over the whole directory, with `install_one` (849-880) doing no per-file filtering — so `night-mode.md` lands in every adopter repo. I additionally verified `install.sh:1104` installs `.claude/scripts` top-level ('top-level only, tests/ excluded'), so `night-mode.py` ships as well; the exclusion machinery (`_framework_path_excluded`, used at 1042-1043 for `_lib`) is not applied to either path. The plan's AC inspects only templates and default settings VALUES, which stay byte-identical, so both statements are simultaneously true while the adopter surface grows. P2 held: shipping a `bypassPermissions` path into every adopter of a fail-closed governance framework is material, though the command is inert until invoked.

---

## P2 — planschema-full-ack-not-owner-proof

**CLAIM.** The `--full` typed ack `NIGHT-MODE-FULL-I-ACCEPT` is not an Owner-presence control — any model or agent with Bash can type it — yet it is the sole gate on a real permission-floor bypass.

**FIX.** Bind `--full` to something the model cannot forge: require an env var the Owner exports in their own shell (the repo's existing pattern), a GPG-signed marker, or refuse `--full` entirely in W1 and defer it to a separate Owner-ratified plan. Restate the AC as a POSITIVE control — an in-session agent attempt to invoke `--full` must fail.

**REFUTADOR.** CONFIRMED, and the repo supplies its own refutation of the design. `check_arbitration_kernel.py:38-40` states the contrasting reasoning verbatim: 'This is stricter than sentinel gating on purpose: a spawned sub-agent cannot set env vars in the parent Claude process, so the ACK token cannot be forged by an agent spawn.' A string typed into an argv is exactly the forgeable case that sentence rules out, and nothing in PLAN-165's §Approach or §Security notes binds the ack to a human. P2 held rather than raised: OQ1's recommended default is `acceptEdits` (not bypass), and W1 T1.4 routes the surface to a security review that would plausibly catch this — but the plan pre-commits that 'no reviewer feedback may soften the ack gate', which treats the weak gate as settled.

---

## P3 — planschema-budget-sessions-self-contradictory

**CLAIM.** `budget_sessions: 1` / `context_risk: low` contradicts the plan's own next-session semantics and its acceptance criteria, which require at least three distinct sessions to observe.

**FIX.** Set `budget_sessions: 3` (or 2 with the split stated explicitly), raise `context_risk` to medium, and mark in W0/AC which units require a session restart so the resume path is obvious.

**REFUTADOR.** Contradiction CONFIRMED from the plan text: frontmatter lines 9-10 vs §Context item 5 ('Settings are read at session start; a toggle takes effect on the NEXT session') and two ACs that each begin '`/night-mode on|off` + new session'. W0's two live-fire probes each additionally require a fresh session. SEVERITY CORRECTED P2->P3: `budget_sessions` sits in PLAN-SCHEMA §3 OPTIONAL frontmatter under the ADR-081 'recommended for plans 2026-04-25+' heading, and I found no validator, hook, or CI gate that reads it — it is an advisory estimate. Real internal inconsistency, negligible blast radius.

---

## P3 — planschema-state-path-underspecified

**CLAIM.** The state-marker location `~/.claude/projects/<slug>/` is ambiguous — two live slug conventions exist on this machine — and the plan ignores the framework's existing state-root helper.

**FIX.** Name `_lib/state_store._state_root()` / the `CEO_STATE_ROOT` + `CEO_PROJECT_NAME` env contract explicitly as the marker root (importing `_lib` is unguarded; only edits are), and have the script, its tests, and the `/ceo-boot` line all resolve through that one helper rather than re-deriving a slug.

**REFUTADOR.** CONFIRMED. `_lib/state_store.py:28-30` documents `${CEO_STATE_ROOT:-$HOME/.claude/projects/ceo-orchestration/state}/` and `_state_root()` (114-126) resolves `CEO_STATE_ROOT`, else `$HOME/.claude/projects/${CEO_PROJECT_NAME:-ceo-orchestration}/state`. On disk BOTH conventions exist and are live: `~/.claude/projects/ceo-orchestration/` holds `audit-log-*.jsonl`, `audit-key`, `advisory-dampen`, while `~/.claude/projects/--Users-joaocanhada-canhada-labs-ceo-orchestration/` also exists — and CLAUDE.md §0 describes the memory slug as the absolute path with `/` replaced by `-`. A writer/reader split between script, tests and the boot line is a genuine risk. P3 held: real but easily pinned at implementation time.

---

## P3 — planschema-depends-on-and-plan163-amend

**CLAIM.** `depends_on: []` understates the graph given the plan's premise is entirely derived from PLAN-163, and T2.3 mutates a terminal `done` plan's body.

**FIX.** Set `depends_on: [PLAN-163]`. Keep the dated note in PLAN-163 if desired, but make the authoritative record of the posture decision the plan's own ADR (already required by the L3 reclassification) rather than a mutation buried in a closed plan's Open-questions section.

**REFUTADOR.** The PRIMARY claim is CONFIRMED: PLAN-163 frontmatter reads `status: done`, `completed_at: 2026-07-30`; PLAN-165's §Context derives its whole premise from 'PLAN-163 T5.3 / OQ5(c)' yet declares `depends_on: []`, while PLAN-SCHEMA §7 (443-446) defines `depends_on` as 'this plan assumes the work in PLAN-NNN is complete' and reserves `[]` for 'fresh plans with no priors'. I PARTIALLY REFUTE the second half: the candidate asserts 'the repo's documented convention for revisiting an accepted decision is an ADR amendment', but PLAN-SCHEMA §1.4 (140-146) invokes `ADR-NNN-AMEND-M` only as a NAMING analogy for FOLLOWUP plans — there is no documented rule requiring an ADR amendment here, and `check_plan_edit.py:129` explicitly permits `done -> done`, so the edit is fully legal. SEVERITY CORRECTED P3 (as given) with the fix narrowed to the part that verifies.

---

## P3 — planschema-oq-ratification-too-late

**CLAIM.** All three OQs are deferred to 'Owner ratification via AskUserQuestion at execution', but OQ1 and OQ3 determine file names, the derived command map, and the security surface T1.4 reviews — so the draft->reviewed human gate would approve a plan whose load-bearing choices are still open.

**FIX.** Move OQ1 and OQ3 ratification into W0 as blocking units with their own `Check:` lines, write the ratified answers back into the plan body before the `draft -> reviewed` transition, and leave only OQ2 (expiry) as an execution-time refinement.

**REFUTADOR.** CONFIRMED. `PLAN-SCHEMA.md:387-389` states verbatim that 'draft -> reviewed is the human-gate: the Owner must read the plan before execution begins'. OQ3 fixes `.claude/commands/<name>.md`, which is the input to the `gen-command-skill-hook-map.py --check` hard gate at `validate.yml:291`; OQ1 fixes whether the default write is `acceptEdits` or the tripwire-firing `bypassPermissions`, i.e. exactly what T1.4 reviews. The PLAN-164 precedent is verified verbatim at lines 104-107: 'OQ1-OQ4 RATIFICADAS pelo Owner (tie-break estruturado, 2026-07-29)' as a `- [x]` W0 unit with a `Check:` line, answers written into the body before staging. P3 held (as given): this is a sequencing/process improvement with a clear in-repo precedent, not a defect that breaks anything mechanically.

---

## P2 — precedence-deny-floor-merge-unprobed

**CLAIM.** W0 probes only that the local layer's `permissions.defaultMode` wins; it never asserts that the project layer's 24-entry `permissions.deny` floor survives the merge when the local layer supplies a `permissions` object.

**FIX.** Add one assertion INSIDE T0.1 (no new task needed): with the local layer carrying only `permissions.defaultMode`, attempt a denied action (`Edit(PROTOCOL.md)`) and an allowlisted one (`Bash(git status)`) and record both outcomes in the probe file. Do NOT adopt the candidate's fix of copying the full `permissions` block into `settings.local.json` — that duplicates the deny floor into a gitignored, sentinel-blind, drift-prone twin, which is worse than the risk it treats.

**REFUTADOR.** The gap is real (no deny probe exists in W0, and `defaultMode` does live inside the same `permissions{}` object as the floor at settings.json:766-793). But the P0 rested on a false premise: the two 'contradicting models' do not contradict — effective_config.py:23-28 EXPLICITLY disclaims its own per-top-level-key merge (:746-748) as a model of the harness and states the live harness deep-merges (`hooks` from all layers, `permissions` allow/deny concatenate), which is exactly why every tamper check scans layers individually. Probability of silent deny-loss is therefore low, and a wholesale replacement would also drop the ~60-entry allow list — a loud symptom the T0.1 session would hit immediately. Cheap probe, low likelihood: P2, not P0.

---

## P1 — precedence-tamper-tripwire-contradiction

**CLAIM.** §Security's 'settings_tamper_tripwires keeps attesting the ratified posture' is false for `--full`: the tripwire reads the local layer, so `bypassPermissions` there turns a Tier-S check RED and emits a tamper audit event on every boot of the night session.

**FIX.** Rewrite the §Security sentence to scope it to the `acceptEdits` default (which fires nothing — the rule is `equals:bypassPermissions` only), and state explicitly that `--full` WILL red the Tier-S check and emit `settings_tamper_detected{layer=local}`. Make that an AC ('--full ⇒ ceo-boot shows the tamper red') so the RED is the designed signal, not a surprise. Do not add a suppression carve-out — that would be a tamper-detector exemption needing its own ratification.

**REFUTADOR.** Verified end to end: ceo-boot.py:1565-1595 scans the RESOLVED multi-layer settings 'including the gitignored, sentinel-blind settings.local.json', registered at TIER_S_CHECKS (~:2253); effective_config `_layer_paths` (:316-332) includes LAYER_LOCAL; `_check_settings_layer` (:534-543) flags `permissions.defaultMode == 'bypassPermissions'` per layer; docstring status mapping: findings present -> red. The plan's claim is affirmatively wrong for the `--full` path, and a recurring RED on a tamper tripwire is alarm-fatigue on exactly the detector this repo relies on for T-05.

---

## P3 — precedence-disableautomode-semantics-unevidenced

**CLAIM.** Context item #3 (disableAutoMode blocks only MID-SESSION escalation) sits under a header claiming all five facts were 'verified S288 against the live tree', but the repo carries no binary/schema evidence for the semantics — only prose in a comment that is itself stale about that key.

**FIX.** Relabel #3 as a hypothesis whose falsification is the W0 kill/pivot (T0.2), not a verified fact. Add the `workflowSizeGuideline`-shaped evidence (zod byte offset + describe text + binary sha256) as the preferred T0.2 artifact, with the behavioral pass as the fallback.

**REFUTADOR.** Verified: repo-wide grep for `disableAutoMode` yields only the live value (settings.json:764), the two prose comments (settings.json:763, templates/settings/settings.base.json:593), PLAN-163 planning lines and CHANGELOG.md:94-99 — no extraction, in contrast to the sibling key whose comment cites byte offset 226825131 / sha256 8addc857. So the 'unevidenced' half is true. But P1 is inflated: the plan already routes this through T0.2 in a wave it labels 'kill/pivot decision point', so a false #3 pivots the plan rather than shipping a defect. What survives is the mislabeling plus the missed chance to use the extraction shape that already worked once.

---

## P2 — precedence-toggle-has-no-owner-proof

**CLAIM.** §Security assumes the Owner is the caller but never says what enforces it. The enforcement that actually exists is the harness permission prompt under the ratified `manual` posture — which makes 'never allowlist this command' a load-bearing, currently-unwritten constraint.

**FIX.** State in §Security that Owner presence is proven by the harness prompt on the Bash/slash invocation under `defaultMode: manual`, and add an explicit non-goal: `/night-mode` and `night-mode.py` must NEVER be added to `permissions.allow` (that single line would remove the only Owner gate). Record T-05 as pre-existing and unchanged. Skip the GPG-sentinel proposal.

**REFUTADOR.** Repo facts confirmed: `.claude/scripts/night-mode.py` hits no `_CANONICAL_GUARDS` entry (only lessons.py / prune-lessons.py / lesson-restore.py / lesson_ranker.py / `**/conftest.py` under `.claude/scripts/`), `permissions.deny` has `Edit(.claude/settings.json)` (:771) with no local twin, and I re-ran the live probe: a `bash -c` body naming `.claude/settings.local.json` runs clean while one naming a canonical path is denied. But the proposed GPG gate is refuted: the script is unguarded, so any actor able to run it can equally edit the check out of it — or skip it and write `settings.local.json` directly, which threat-model.md:2037 already classifies as T-05 with no mitigation. The plan therefore adds no new capability class, only a convenient path; the real, cheap control is the prompt plus a written prohibition on allowlisting.

---

## P2 — precedence-state-marker-slug-ambiguous

**CLAIM.** '`state/night-mode.json` under `~/.claude/projects/<slug>/`' is ambiguous: CLAUDE.md defines the slug as the path-mangled absolute path, `_lib/state_store` uses `CEO_PROJECT_NAME` (default `ceo-orchestration`), and all three variants exist on this machine — so a marker written by the script and read by ceo-boot can diverge while TestEnvContext tests stay green.

**FIX.** Name `_lib/state_store` as the marker store in §Approach (import only — no canonical edit, so no ceremony), and add a live-fire AC: after `/night-mode on`, a REAL new session's `/ceo-boot` shows the banner. Keep the TestEnvContext unit tests, but do not let them stand as the only evidence.

**REFUTADOR.** Verified: `_state_root()` (state_store.py:113-126) = `$HOME/.claude/projects/${CEO_PROJECT_NAME:-ceo-orchestration}/state`; on disk `~/.claude/projects/` holds `ceo-orchestration/` (the live one, with audit-key + audit-log + state/), `-Users-joaocanhada-canhada-labs-ceo-orchestration/` (session transcripts) and `--Users-...`. The plan's `state/` suffix hints at the state_store convention but `<slug>` invites the CLAUDE.md reading. Same-resolver-both-sides under TestEnvContext makes the mismatch invisible — the repo's documented false-green class. Impact is lost visibility, not unsafety: P2.

---

## P1 — precedence-l2-misclassified

**CLAIM.** The plan self-classifies L2 to skip debate while its own T1.4 calls the surface 'VETO-relevant per PROTOCOL §Vetoes' — PROTOCOL.md:135 makes debate mandatory for any change in a VETO-protected domain, and CLAUDE.md §4 requires an ADR for the cross-cutting decision ('a supported unsigned path to change session permission posture').

**FIX.** Reclassify L3, run `/debate start PLAN-165 "..."`, and add an ADR task capturing the decision + residual (T-05 unchanged, prompt-as-Owner-proof, `--full` weakening). The debate appears to be in flight already for this plan — make the plan's own Level section say so instead of asserting 'no debate mandatory'.

**REFUTADOR.** PROTOCOL.md:135 and :376 verified verbatim; the L3 trigger keys on the DOMAIN, not on which files are touched, so the plan's rationale ('the DEFAULT posture and all guarded files are untouched') answers a different question. Precedent is decisive: PLAN-163 T5.3, which ESTABLISHED this posture, ran a full debate with a security-engineer round (`.claude/plans/PLAN-163/debate/round-1/security-engineer.md`). The missing ADR is the more durable half — nothing else records why an unsigned path to posture change is acceptable.

---

## P2 — precedence-doc-count-list-incomplete

**CLAIM.** T2.2 says 'Command count 26→27: regenerate derived surfaces' without enumerating the eight count-bearing occurrences — including two the tolerance-0 gate does NOT watch, one of which (docs/ARCHITECTURE.md:270, '22 of them') is already stale today.

**FIX.** Enumerate in T2.2: CLAUDE.md:54, README.md:58 (table cell) + :185, docs/ARCHITECTURE.md:51 + :70 (table cell) + :270 (prose '22 of them', unwatched + already wrong), docs/FAQ.md:106, npm/README.md:58 (table cell) + :121, CHANGELOG.md:12 + :104 (Counts block, unwatched). Promote 'verify-counts.sh + check-claude-md-claims.py green' from prose to an AC.

**REFUTADOR.** Verified live: DOCS in verify-counts.sh:238-242, prose rule `(\d+) slash commands` (:299-302) and TABLE_RULES `^Slash commands\b` (:322); `ls .claude/commands/*.md | wc -l` = 26. But the candidate misread the plan: `docs/CHEAT-SHEET.md` / `docs/TROUBLESHOOTING.md` are listed as places to DOCUMENT the new command (CHEAT-SHEET.md:12 has the '## Slash commands' section), not as the count-bearing list — so 'names the wrong files' is wrong. The candidate's own enumeration is also incomplete: it missed README.md:58 and docs/ARCHITECTURE.md:70, both watched table cells. Downgraded to P2 because the tolerance-0 gate the plan already names catches this loudly at push — the cost is a rework loop, not a shipped defect.

---

## P2 — precedence-ceo-info-cannot-evidence

**CLAIM.** T0.1 names `/ceo-info` output as evidence for the precedence claim, but ceo-info never reads or prints `permissions.defaultMode` — that half of the W0 kill-gate's evidence is vacuous.

**FIX.** Replace `/ceo-info output` with a behavioral artifact: attempt an action that prompts under `manual` and record that it did not prompt, plus the harness-reported mode from the transcript, captured to `.claude/plans/PLAN-165/probes/`. Keep `/ceo-info` only as corroboration that the local layer exists and parses.

**REFUTADOR.** Verified: `_effective_settings()` (ceo-info.py:190-223) returns `files[]`, `effective` (a path) and `effective_hook_registrations` (an int); the renderer (:904-915) prints exactly those; `defaultMode` appears in `.claude/scripts/` only as a ceo-boot docstring and a self_test fixture. W0 is the plan's kill/pivot gate, so a vacuous evidence artifact there means the pivot decision rests on nothing — this repo's 'registered-vacuous' / 'fixture verde ≠ enforcement provado' class. P2 holds.

---

## P2 — precedence-ceo-info-misreports-rail

**CLAIM.** Merely creating `settings.local.json` makes `/ceo-info` report the governance rail as `source: .claude/settings.local.json (0 hook registrations)` — silent misreporting on the very command the plan probes with, made routine by night-mode.

**FIX.** Either fix `_effective_settings()` to report a per-layer/merged view before shipping night-mode, or add an AC that `/ceo-info` output with night-mode ON is checked and its known misreport recorded. Do not leave a reader to conclude the rail is dead.

**REFUTADOR.** Verified: `_settings_candidates()` (:186-188) = [settings.json, settings.local.json]; the loop unconditionally sets `effective = entry['path']` and `hook_count = n` for each valid file with the comment 'settings.local.json (if present + valid) is the effective override' (:213). A permissions-only local file has no `hooks{}` ⇒ n=0. `exit_nonzero` keys only on required paths (:825-859), so it is silent, not a gate failure — and the rail is in fact intact (effective_config.py:25-26: hooks from ALL layers run). Note the file does not exist on this machine today (`ls` = No such file), so night-mode is what makes this the normal state.

---

## P2 — precedence-l2-scope-understated

**CLAIM.** T2.1 ('ceo-boot advisory line off the marker') is not a one-function change: the recommendations engine derives lines exclusively from check results, is duplicated under an explicit mirror invariant, and a new Tier-S check would trip a hard count assert.

**FIX.** Re-scope T2.1 with the concrete edit list — `_make_recommendations`, `_recommendations_with_severity` (mirror invariant), the mirror tests in test_ceo_boot_liveness.py / test_ceo_boot_tamper_tripwires.py, and `assert len(TIER_S_CHECKS) == 23` if a check is added — then re-derive the level from the real footprint.

**REFUTADOR.** Verified: `_make_recommendations(results: List[CheckResult])` (ceo-boot.py:2541) has no marker/state input; `_recommendations_with_severity` (:2695-2705) carries 'Mirror `_make_recommendations` exactly'; `assert len(TIER_S_CHECKS) == 23` at :2263. A yellow check with no named rule produces no recommendation line, so a second data source must be threaded through both mirrored functions. Independent of the veto question, this plus night-mode.py + command + tests + 5-7 count-bearing docs makes the PROTOCOL.md:131 '3+ modules' trigger arguable on its own.

---

## P2 — precedence-no-atomic-write-or-postwrite-validation

**CLAIM.** §Approach specifies a 'merge-write' of a settings file with no atomicity and no post-write re-parse — on the exact file class that already made this repo boot with zero governance hooks.

**FIX.** Require temp-file + `os.replace`, a `json.loads` re-parse of the written bytes before reporting success (revert + exit non-zero on failure — fail-closed, this is input the harness must parse), and an AC that `off` recovers from a corrupted `settings.local.json`.

**REFUTADOR.** Precedent verified verbatim at CHANGELOG.md:94-99: a schema-invalid value made CC 2.1.220 skip the whole settings.json, 'governance fully absent, and no error surfaced… found by live-fire, not by any fixture'. Degradation is quiet by design: `_read_json_layer` (effective_config.py:335-367) sets ok=False and the boot check yellows at best. No AC covers atomicity, re-parse, or corrupt-file recovery, and `off`'s restore path depends on that file being parseable. Cheap, specific, and matches the repo's fail-closed-on-input doctrine.

---

## P3 — precedence-snapshot-clobber

**CLAIM.** The `on -> on --full -> off` transition can leave the snapshot holding a night-mode value, so `off` restores `acceptEdits` instead of removing the key.

**FIX.** Snapshot exactly once, at marker creation, and store it inside the marker; a mode change while the marker exists rewrites `defaultMode` only, never the snapshot. Add `on -> on --full -> off` explicitly to T1.3.

**REFUTADOR.** The design hole is real — §Approach says 'snapshot of any pre-existing permissions.defaultMode saved for restore' with no write-once rule, and AC 2 only ever exercises the single cycle. But T1.3 already lists 'idempotent double-on/double-off', and a correctly written double-on test (assert `off` restores the ORIGINAL) catches the identical re-snapshot bug; only the mode-CHANGING variant is genuinely uncovered. Partially handled ⇒ P3, not P2.

---

## P2 — precedence-ac-test-command-not-ci

**CLAIM.** AC 5 gates on `unittest discover`, which is not what CI runs: CI runs two pytest marker passes over `.claude/scripts/tests/` AND `.claude/scripts/optimizer/tests/`.

**FIX.** Make AC 5 the exact CI invocation — `python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -n auto -m 'not serial' --strict-markers --tb=no -q` followed by the `-m 'serial'` pass — and add `.claude/scripts/check-test-env-hygiene.py` (it exists) since new files under `.claude/scripts/tests/` are subject to it.

**REFUTADOR.** Verified: validate.yml:424-425 runs both marker passes; Makefile:14 (`test-quick`) is pytest, not unittest — note there is no `make test` target, a small inaccuracy in the candidate that does not touch the substance. `unittest discover` honors no markers, never runs the serial pass, skips optimizer/tests, and cannot surface the xdist/`__pycache__`-copytree flake class. AC 5's trailing 'suites + governance gates green (V1)' softens it but is vague where the repo's own lesson ('pre-commit de subconjunto passa com CI falhando') demands the exact command. P2 held.

---

## P3 — precedence-stale-posture-comment

**CLAIM.** `.claude/settings.json:763` still glosses the key as 'disableAutoMode=true (no automatic permission-mode escalation mid-session)' while :764 is `"disable"` — and the plan inherits that gloss as claim #3 without flagging it.

**FIX.** Stop citing the stale gloss as support for #3 (its evidence is T0.2, not the comment). Add the `_posture_comment` correction to the queued sentinel ceremony rider alongside RC3-F7 / GA-F3 — the corrected wording already exists at templates/settings/settings.base.json:593 and can be copied.

**REFUTADOR.** Verified: `838527a` changed only the value; the comment at :763 still says `true`. `.claude/settings.json` is both `_CANONICAL_GUARDS` (check_canonical_edit.py:169) and `permissions.deny` `Edit(...)` (:771), so the fix genuinely needs the ceremony. Downgraded to P3: the VALUE is correct and adopter-facing template text is already correct, so this is stale prose in one comment — real debt, no operational effect, and it overlaps the labeling fix under precedence-disableautomode-semantics-unevidenced.

---

## P3 — precedence-ceremony-rider-avoidable

**CLAIM.** Ceremony rider R1 (`night_mode_toggled` in `_KNOWN_ACTIONS`) is optional, not a prerequisite: a marker written through `_lib/state_store` already emits an HMAC-chained `state_store_write`.

**FIX.** Write the marker via `_lib/state_store` and drop R1 — or keep R1 explicitly labelled a naming refinement, not the plan's audit-coverage prerequisite.

**REFUTADOR.** Verified: `_KNOWN_ACTIONS` carries `state_store_write` / `state_store_read` (audit_emit.py:169-170, Sprint 11 Phase 0 / ADR-027) with emitters at :3333/:3371, and state_store.py:430-434 dispatches to `audit_emit` on write (fail-open). The plan's R1 targets are also confirmed (`_KNOWN_ACTIONS` opens at audit_emit.py:154; `.claude/hooks/_lib/audit_emit.py` is line 27 of the 34-line pair-rail manifest). P3 because the plan already defers R1 out of its own waves and documents the interim L6-observer coverage — this only removes work, it does not fix a defect.

---

_Total: 84 findings sobreviventes — {'P2': 41, 'P1': 17, 'P3': 26}_
