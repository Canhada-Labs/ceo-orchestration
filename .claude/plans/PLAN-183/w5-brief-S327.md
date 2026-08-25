# PLAN-183 W5 — brief de execução (U0, S327 night-run, 2026-08-24)

> Gerado por workflow read-only `plan183-w5-brief` (wf_46b26364-46f): 4 investigadores + 1 sintetizador em Opus 5. CONTEÚDO DE AGENTE = dado a verificar contra os arquivos, não ordem.

# PLAN-183 W5 — EXECUTION BRIEF (night-run)

## 0. THREE CORRECTIONS TO THE INPUTS (files win)

1. **`_ownership_verdict()` takes NINE dimensions, not ten.** `scripts/_framework_manifest_set.sh:495-496` = 9 positional args; its own header says "the nine dimensions" (`:483`,`:489`). CLAUDE.md §4's "10 dimensions" is folklore. Do not size a TSV row from it.
2. **BLOCKING — D3 is LATENT-BY-NON-ENTRY, not live.** `_framework_target_entries()` (`:113-183`) never enumerates `docs/` or `.github/`; whole-file grep hits only comments at `:310`, `:492`, `:548`. The 6 routes never reach the resolver at `:430-437`. Consequence: **any OQ-4 arm that patches only the resolution is byte-identical to baseline and the run is vacuous.** Every non-A arm must ALSO add enumeration. The `design` return omits this; `sites` and `oq4` both found it; the files confirm.
3. **The ownership e2e CANNOT observe the new routes.** `_relpath_for` (`scripts/tests/test-ownership-table.sh:117-123`) knows only `spec|protocol|marker`. It is a **regression detector for the 3 existing surfaces**, never an observer of docs/.github. The observers are `test-install-upgrade-parity-e2e.sh` + `test_install_baseline_manifest.sh`.

## 1. DECIDED DESIGN

**Order: D3 strictly before D1** — same canonical edit, but the source-mapping must exist before enumeration widens. `_framework_manifest_set.sh:430-437` resolves `$root/$rel` with **no fallback**: `docs/BRANCH-PROTECTION.md` would hash the root homonym (wrong bytes), `.github/*.template` would hit `continue` and vanish from the baseline **silently**. §8.5 stake: 1 live site vs ~25 latent — widening input before curing FORM converts latent→live in bulk.

**D2 = CURED (`b6de7cf`), D4 = CURED (`aaf32c7`).** Post-D2 the e2e is `STALE 3 / UNCLASSIFIED 0` — three fatals, ONE cause. **D1 is load-bearing for green**; D2 bought diagnosis only (`templates/docs/BRANCH-PROTECTION.md` diverged `61025a16`→`966e0571`).

**OQ-5 (RATIFIED, route ii + amendment).** `scripts/upgrade.sh:798-799` sets `CEREMONY_EFFECTIVE="user"` on unreadable install-state; delivery is gated `CEREMONY != user` (`install.sh:1484`, `:1525`) ⇒ the historical adopter gets nothing. **Amendment:** unreadable install-state **but `.claude/.framework-version` present ⇒ treat as adopter and DELIVER.** Never-installed dir default unchanged. Probe belongs adjacent to `:798-799`, **before** the overrides at `:805-816`, and **MUST NOT set `_CEREMONY_PERSIST=1`** (`:801-803`: only RECORDED/EXPLICIT may persist; persisting an inference makes one missed migration permanent). **Check must run without the `v1.2.0` pin** (`test-install-upgrade-parity-e2e.sh:110` `PIN="${CEO_PARITY_PIN:-v1.2.0}"`) — pinned, install.sh already writes `.install-state.json`, so the leg is structurally blind (debate class C2).

**OQ-4 (NOT ratified — MEASURE first).** Measured: `_wbm_is_conditional` (`:320-325`) and `_wbm_declared_hash_source` (`:311-318`) each cover exactly 4 paths (`SPEC/v1`, `SPEC/v1/*`, `PROTOCOL.md`, `.claude/.framework-version`). All 6 routes fall on the NON-conditional lane. `HASH_SOURCE` has ONE consumer (`:395-405`) behind `elif _wbm_is_conditional` ⇒ on the non-conditional lane new TSV rows are **inert**. Hypothesis to test (not decide): **MIXED lane** — 5 verbatim stay non-conditional, only `.github/CODEOWNERS` (rendered; bytes exist in no checkout) enters conditional ⇒ OQ-4 shrinks ~13 → ~2-3 rows. **Until the verdict, ZERO rows may be written to `scripts/tests/ownership_table.tsv`.**

**Registration rule.** Precedent `install.sh:1318-1329`: `if [[ "$INSTALL_ONE_WROTE" = "1" ]] || cmp -s <src> <target>` — registers **also when it did not write**, by byte-compare. The draft's "PRESERVED/SKIPPED stay out" is a REGRESSION: it drops all 5 registrations on a SECOND install and ships GREEN (no Check runs install twice). Reconcile against `upgrade.sh:3110-3115` (keeps INSTALLED/REFRESHED/**IDENTICAL**, excludes PRESERVED/SKIPPED) — decide explicitly, do not pick blind. **Trap:** `install_docs_template` (`install.sh:1446-1474`) **never sets `INSTALL_ONE_WROTE`** (owned by `install_one` at `:877`,`:905`,`:919`) ⇒ the idiom is not copy-pasteable; add a wrote-flag, and the `cmp -s` half must compare the **SOURCE relpath** — which is exactly what has no resolver (D3).

**Collision argument (for the ADR).** The boundary is CONTENT, not the `.template` suffix. Bytes-identical is origin proof when content is framework-specific: rendered CODEOWNERS is 33 lines / 1442 b naming `.claude/skills/**`, `.claude/hooks/**`, `.claude/plans/PLAN-*.md`, `PROTOCOL.md`. Residual blast radius = `docs/*` (an adopter can plausibly own such a doc); `uninstall.sh` removes by hash. Generations derive from **git history per file** (`upgrade.sh:3204-3212`), never from tags.

## 2. CODE SITES

| unit | site |
|---|---|
| D3 route reader | `scripts/_framework_manifest_set.sh` — new `_wbm_route_src`, idiom copied verbatim from `scripts/doctor.sh:418-449` (`_route_source`, linear scan; bash 3.2 has no `declare -A`). rc 0=identity src / 1=no route / 2=rendered-or-malformed. **`${_rs_transform:-}` must stay unbraced-default-empty** — `${_rs_transform:-identity}` was the fail-OPEN rail finding. |
| D3 enumeration | `_framework_target_entries()` `:113-183`, gated on new `FMS_DELIVERED_TEMPLATES`, mirroring `FMS_DELIVERED_*` at `:122,:129,:140,:157,:160` |
| D3 resolution | `:430-437` non-conditional branch |
| D1 install signal | `install.sh:1446-1474` (`install_docs_template`) + `:1476-1482` / `:1488-1523`; gates `:1484`, `:1525`; render `:1508` |
| D1 upgrade delivery | `scripts/upgrade.sh` — insert **before** `_write_baseline_manifest` `:3470`; precedent is PLAN-177 W1 `.gitignore` at `:3388-3436`; export `FMS_DELIVERED_*` next to `:3529-3534`; `export FMS_HASH_ROOT="$SOURCE_DIR"` at `:3475` is what makes D3 bite |
| OQ-5 amendment | `scripts/upgrade.sh:798-803` region |
| route table | `scripts/delivery-routes.tsv` — 6 rows, cols `dest src transform flag_dep origin note`; readers today: `scripts/tests/_parity_classify.py`, `scripts/doctor.sh`; **third (canonical) reader = 0** (`grep -c delivery-routes scripts/_framework_manifest_set.sh` → 0) |

## 3. OQ-4 EXPERIMENT (arms A/B/C, shadow worktree)

Legal because `_fnmatch_segments` (`check_canonical_edit.py:949-958`) is anchored and no guard starts with `**` ⇒ **absolute `$SHADOW/...` paths never match**. Patch via `python3 - <<'PY'` heredoc — never Edit/Write, never a relative path after `cd $SHADOW`.

- **A** = unchanged HEAD. **B** = enumeration + route reader + non-conditional resolution, all 6 routes. **C** = B minus CODEOWNERS from route resolution, plus `.github/CODEOWNERS` added to `_wbm_is_conditional` `:320-325` and a `case` arm in `_wbm_declared_hash_source` `:311-318` → `${FMS_HASH_SOURCE_CODEOWNERS:-}`, exported from install/upgrade (`HASH_TARGET` on fresh, `HASH_PRIOR_RECORD` on continuity — the `PROTOCOL.md` shape at `install.sh:2504`).
- **Runtime:** unit oracle **0.064 s measured** (`PASS=63 FAIL=0 SKIPPED=2` = OWN-0024, OWN-0027). Ownership e2e **~25 min/arm** (documented; `CELL_TIMEOUT` default 60 at `:41`, CI uses 180 at `ownership-nightly.yml:131` — **pin 180 in every arm** or a loaded machine flakes into TIMEOUT, which the gate fails outright). Parity e2e minutes/arm. Budget ~90-120 min for 3 arms.
- **"No regression" per arm:** (i) e2e RED id-set **exactly** `{OWN-0016, OWN-0024, OWN-0027}`, zero TIMEOUT/ESCAPE/AMBIG, `HARNESS-ERR=0`, rc=1; (ii) unit oracle `FAIL=0`; (iii) parity fatal counts no worse than **arm A's own measured numbers** (never the prose); (iv) `test_install_baseline_manifest.sh` green.
- **All-green is a STOP signal**, not success (`ownership-nightly-gate.sh:6-9`) — shrinkage means the truth table changed.
- **Verdict output:** names conditional / non-conditional / MIXED, with `git -C $SHADOW diff --stat` as the line budget per arm.

## 4. VERIFICATION MATRIX

| unit | oracle | command | runtime |
|---|---|---|---|
| D3 reader | mutate-a-row / delete-table controls | all THREE consumers RED **naming the row** | s |
| D3 baseline | `bash scripts/tests/test_install_baseline_manifest.sh` | 6 routes recorded, right digest | min |
| D1 install | 4-case wrote-flag assert 1,0,0,0 | new test | s |
| D1 upgrade | `bash scripts/tests/test-install-upgrade-parity-e2e.sh --mode maintainer` / `--mode user` | user must stay 0 | min |
| OQ-5 | `CEO_PARITY_PIN=<older-tag> … --mode maintainer` | + negative control: never-installed dir | min |
| regression | `bash scripts/tests/ownership-nightly-gate.sh` | id-set == expected-reds | ~25 min |
| fast regression | `bash scripts/tests/test-ownership-verdict-unit.sh --quiet` | PASS=63 FAIL=0 | 0.064 s |
| D2/D4 intact | `python3 -m pytest .claude/scripts/tests/test_parity_source_resolution.py -q`; `bash scripts/tests/test-doctor-delivery-route.sh` | 26 assertions | s |

**Verification is NOT grep** (debate C3): S325 measured that pointing a row at a wrong-but-existing source kept all 10 tests green — tautology. Truth must be independent: the `install.sh` call-sites.

## 5. CEREMONY PACKAGE (S327)

`.claude/plans/PLAN-183/wave-w5-approved.md` (+ `.asc`) — **filename must match the glob `PLAN-*/wave-*-approved.md`** (`check_canonical_edit.py:1012`). Grant region `<!-- BEGIN SIGNED SCOPE -->…<!-- END SIGNED SCOPE -->`; order inside: `Approved-By:` → `Plans:` → `Scope:` + `  - <path>` bullets (`Plans:` after `Scope:` truncates the list — it is a terminator, `:496-501`). File >64 KiB ⇒ rejected outright.

Package dir `PLAN-183/w5-ceremony/`: `S327-W5-DELIVERY.patch`, `PROPOSED-PATCH.md`, `COMMIT-MSG.txt`, `finalize_patch.py`, `rail-round-*.md`, gate positive controls (`g0-block.sh`, `p0-block.sh`, `stage-block.sh`, `sabotage.sh`). Scripts `OWNER-S327-SIGN.sh` / `OWNER-S327-LAND.sh` copied from `PLAN-182/OWNER-S326-{SIGN,LAND}.sh`; **only constants change** (`PLAN_DIR`, `SENTINEL`, `PATCH`, `MSG`, `MATERIALS`, rail glob). Both carry `CEREMONY-LINT: handwritten-exception:`.

**Scope (oracle-measured).** canonical=1: `scripts/install.sh`, `scripts/upgrade.sh`, `scripts/_framework_manifest_set.sh`, `.github/workflows/smoke-install.yml`, `.github/workflows/ownership-nightly.yml`, `.claude/governance/gate-scripts-manifest.txt`. canonical=0 **but still in Scope** (G4 has no canonicity filter): `scripts/doctor.sh`, `scripts/delivery-routes.tsv`, `scripts/tests/_parity_classify.py`, `scripts/tests/ownership_table.tsv`, `scripts/tests/ownership-expected-reds.txt`, `docs/ownership-decision-table.md`, `.claude/plans/PLAN-183-adopter-fitness.md`, new tests. **Derive Scope from `git apply --numstat`, never by hand** — it was corrected twice already this plan and was still incomplete both times.

**LAND fix (mandatory).** `OWNER-S326-LAND.sh:303-306` only PRINTS a suggested message; the Owner ran bare `git commit` and landed in vim. S327 must `git commit -F .claude/plans/PLAN-183/w5-ceremony/COMMIT-MSG.txt --no-edit` then `git push origin main`, printing the hash. Print the escape line: `Esc Esc, :q!, Enter`.

## 6. RISKS / PRECEDENTS

- **24-cell regression** — `install.sh:2508-2511`: *"the previous attempt at this wave regressed 24 cells precisely because it left fresh installs undeclared."* Any arm declaring hash_source only on continuity repeats it.
- **ADR-192 trap** — `scripts/tests/ownership-nightly-gate.sh` and `ownership-expected-reds.txt` print oracle **0** yet ARE manifest members (verified in `.claude/governance/gate-scripts-manifest.txt`). Touching either requires ceremony **and** a manifest sha bump ⇒ the manifest (canonical=1) joins Scope. Exactly the `verify-counts.sh` lesson from S326.
- **Ceremony debt** — `scripts/delivery-routes.tsv` is absent from both `paths:` lists in `smoke-install.yml` (grep count 0). Once a canonical script reads it, close this in the same ceremony.
- **`finalize_patch.py` uses bare `git diff`** ⇒ untracked NEW files vanish from the signed patch silently. S326 never exercised that leg (zero `new file mode`). W5 adds new test files ⇒ `git add -N` in the shadow first, with its own positive control.
- **bash 3.2 floor** — no `declare -A`; linear scan only.
- **CODEOWNERS rows are mutually exclusive** per run (`install.sh:1496` elif vs `:1511` else) ⇒ enumeration must not emit both, or one is a guaranteed spurious miss.
- **main is RED by design** (D1 open ⇒ `STALE 3`). The V block must declare the expected baseline and compare against it.
- **C5 unresolved:** FILE vs DIRECTORY entries in `_framework_target_entries`. The D3 Check silently assumes one — fix before writing.
- **Stale prunable worktree** at `.../cbec69fd-.../scratchpad/rc3-wt` — `git worktree prune` before `worktree add`.
- **Owner decision still OPEN:** W5-b checklist re-sequencing (debate C1 says current order is inexecutable; C2 vacuous Checks must be replaced first). The unit plan below is PROPOSED, not ratified.


## Unit plan (proposto, não ratificado)

- **U1** Fix the census pattern as a TEST, then count consumers of the route table — touches: .claude/scripts/tests/test_delivery_route_consumers.py; canonical=False; ~35 min
  - proves: the two S324 censuses (11 files/34 sites vs 10/29) stop disagreeing because the pattern is fixed as a test, not a session measurement | a 4th consumer carrying its own dest->src map turns the test RED and names the offending file
- **U2** OQ-4 lane experiment arms A/B/C in a shadow worktree (measurement only, ZERO rows written to ownership_table.tsv) — touches: $SHADOW/scripts/_framework_manifest_set.sh, $SHADOW/scripts/install.sh, $SHADOW/scripts/upgrade.sh; canonical=False; ~120 min
  - proves: verdict names conditional / non-conditional / MIXED | per-arm RED id-set == {OWN-0016,OWN-0024,OWN-0027} with HARNESS-ERR=0 and zero TIMEOUT/ESCAPE/AMBIG | unit oracle FAIL=0 on every arm | parity fatal counts no worse than arm A's own measured numbers | git diff --stat gives the true OQ-4 line budget: enumeration + hash_source declaration + route resolution, NOT 'TSV rows'
- **U3** Decide C5 (FILE vs DIRECTORY entries) and the registration rule (byte-compare vs result-only) BEFORE any expected count is written — touches: .claude/plans/PLAN-183/w5-ceremony/DESIGN-NOTE.md; canonical=False; ~40 min
  - proves: a second-consecutive-install e2e keeps the delivered count == 5 under the chosen rule | install.sh:1318-1329 (registers by byte-compare even without writing) is reconciled explicitly against upgrade.sh:3110-3115 (excludes PRESERVED/SKIPPED)
- **U4** D3 - third reader: _framework_manifest_set.sh reads scripts/delivery-routes.tsv via _wbm_route_src (doctor.sh:418-449 idiom verbatim, bash 3.2 linear scan, fail-CLOSED on non-literal identity) — touches: scripts/_framework_manifest_set.sh; canonical=True; ~90 min
  - proves: mutating one TSV row turns ALL THREE consumers RED naming the mutated row | deleting the table turns all three RED | the U1 census test stays green | verification compares against install.sh call-sites, never against the table itself (S325 tautology finding)
- **U5** D3 - enumerate the 6 routes in _framework_target_entries behind FMS_DELIVERED_TEMPLATES (only AFTER U4 lands the resolver) — touches: scripts/_framework_manifest_set.sh; canonical=True; ~75 min
  - proves: test_install_baseline_manifest.sh records all 6 routes with the correct digest | no path is lost to the `continue` at :430-437 | a second consecutive upgrade reclassifies nothing (AC-10)
- **U6** D1 - per-destination delivery signal in install_docs_template (install_one semantics; install.sh:874-876) — touches: scripts/install.sh; canonical=True; ~60 min
  - proves: 4 cases assert 1,0,0,0 for wrote / EXISTS-skip / source-missing / dry-run | no FMS_DELIVERED_* may be declared before this is green | the cmp -s half compares the SOURCE relpath resolved through the TSV, not the destination relpath
- **U7** D1 - upgrade.sh delivers docs/ and .github/, hash-gated against git-derived generations, per-path/per-result — touches: scripts/upgrade.sh; canonical=True; ~120 min
  - proves: parity e2e maintainer fatals drop from the arm-A baseline | parity e2e user stays at 0 | second consecutive upgrade diff scoped to .github/ + docs/ is empty | precondition delivered-count == 5 asserted FIRST so count 0 is a FAIL, not a vacuous pass (AC-9)
- **U8** OQ-5 amendment: .framework-version present + unreadable install-state => DELIVER (no _CEREMONY_PERSIST) — touches: scripts/upgrade.sh; canonical=True; ~70 min
  - proves: a parity e2e run WITHOUT the v1.2.0 pin observes delivery to the historical-adopter population | negative control: a never-installed directory keeps the fail-safe user default | _CEREMONY_PERSIST stays 0 for the inferred resolution (upgrade.sh:801-803)
- **U9** Fixture legs: partial trees, CODEOWNERS coexistence, pre-Wave-B-with-owner => PRESERVE, plus uninstall.sh legs (debate C4) — touches: scripts/tests/; canonical=False; ~90 min
  - proves: the manifest lists exactly the newly delivered paths | every pre-existing file is byte-identical after upgrade | a rendered CODEOWNERS is left untouched and unclaimed | uninstall removes nothing outside $TARGET and the empty-dir policy is asserted
- **U10** if: always() on the parity positive control and the two other skipped steps (plan section 9.8) — touches: .github/workflows/smoke-install.yml; canonical=True; ~45 min
  - proves: a run with the main step RED shows the positive control as success or failure, never `skipped` | the same commit closes the delivery-routes.tsv omission from both paths: lists
- **U11** ADR (AMEND ADR-155 or new) carrying the collision argument + derived-count bump — touches: .claude/adr/, CLAUDE.md; canonical=False; ~50 min
  - proves: python3 .claude/scripts/check-claude-md-claims.py returns 0 in the SAME commit | the CLAUDE.md edit is sequenced explicitly against the section-0 cache-discipline rule (closeout-only)
- **U12** Ceremony package S327: sentinel-draft, patch, finalize_patch.py with git add -N, SIGN/LAND parameterized, LAND commits with -F --no-edit — touches: .claude/plans/PLAN-183/wave-w5-approved.md, .claude/plans/PLAN-183/w5-ceremony/, .claude/plans/PLAN-183/OWNER-S327-SIGN.sh, .claude/plans/PLAN-183/OWNER-S327-LAND.sh; canonical=False; ~120 min
  - proves: Scope is DERIVED from git apply --numstat, never hand-enumerated | _sentinel_grants_path returns True for every canonical path in Scope | LAND G0..G5 pass with G4 touched-minus-scope empty | the V block declares the expected RED baseline and compares against it | the Owner never lands in an editor (git commit -F --no-edit then push)

## Procedimento OQ-4 (braços A/B/C)
```bash
export SHADOW=/private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-183
export OUT=/private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/oq4-out && mkdir -p "$OUT"
git -C /Users/joaocanhada/canhada-labs/ceo-orchestration worktree prune   # a stale prunable worktree exists (rc3-wt at 0cb09c3) and will collide with worktree add
git -C /Users/joaocanhada/canhada-labs/ceo-orchestration worktree add --detach "$SHADOW" HEAD
git -C "$SHADOW" tag -l v1.2.0   # MUST print v1.2.0 or the legacy_pristine fixtures die (test-ownership-table.sh:39)
bash "$SHADOW/scripts/tests/test-ownership-table.sh" --list | awk '{print $1}' | grep -E '^OWN-' | LC_ALL=C sort > "$OUT/all-ids.txt"
grep -E '^OWN-' /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/tests/ownership-expected-reds.txt | LC_ALL=C sort > "$OUT/expected.red"   # OWN-0016 OWN-0024 OWN-0027
# ---------- ARM A (baseline, unchanged generator) ----------
cd "$SHADOW" && CELL_TIMEOUT=180 bash "$SHADOW/scripts/tests/test-ownership-table.sh" > "$OUT/armA.map" 2> "$OUT/armA.err"; echo "rc=$?" >> "$OUT/armA.err"   # ~25 min; CELL_TIMEOUT=180 matches ownership-nightly.yml:131 - the 60s default flakes into TIMEOUT under load and the gate fails outright
grep -E '^OWN-[0-9]+[[:space:]]' "$OUT/armA.map" | awk '$2 == "RED" {print $1}' | LC_ALL=C sort > "$OUT/armA.red"
grep -E '^OWN-[0-9]+[[:space:]]' "$OUT/armA.map" | awk '$2 != "GREEN" && $2 != "RED" {print $1" "$2}' > "$OUT/armA.other"   # MUST be empty - TIMEOUT/ESCAPE/AMBIG fail the gate even with an unchanged id-set
diff -u "$OUT/expected.red" "$OUT/armA.red"; echo "delta_rc=$?"
grep -E '^GREEN=[0-9]+[[:space:]]+RED=[0-9]+[[:space:]]+AMBIG=[0-9]+[[:space:]]+HARNESS-ERR=0$' "$OUT/armA.map"
grep -E '^OWN-[0-9]+[[:space:]]' "$OUT/armA.map" | awk '{print $1}' | LC_ALL=C sort > "$OUT/armA.ids"; diff -u "$OUT/all-ids.txt" "$OUT/armA.ids"   # anti-partial-run: a partial run certifies nothing
bash "$SHADOW/scripts/tests/test-ownership-verdict-unit.sh" --quiet > "$OUT/armA.unit" 2>&1; echo "unit_rc=$?" >> "$OUT/armA.unit"   # 0.064s measured; expect PASS=63 FAIL=0 SKIPPED=2
cd "$SHADOW" && bash "$SHADOW/scripts/tests/test-install-upgrade-parity-e2e.sh" --mode maintainer > "$OUT/armA.parity-maintainer" 2>&1; echo "rc=$?" >> "$OUT/armA.parity-maintainer"
cd "$SHADOW" && bash "$SHADOW/scripts/tests/test-install-upgrade-parity-e2e.sh" --mode user > "$OUT/armA.parity-user" 2>&1; echo "rc=$?" >> "$OUT/armA.parity-user"   # MUST stay 0 fatals
cd "$SHADOW" && bash "$SHADOW/scripts/tests/test_install_baseline_manifest.sh" > "$OUT/armA.baseline" 2>&1; echo "rc=$?" >> "$OUT/armA.baseline"
# ARM A IS THE BASELINE. Judge B and C against these measured numbers, NEVER against CLAUDE.md prose and NEVER against zero (main is RED by design: D1 open => STALE 3).
# ---------- ARM B (all 6 routes on the NON-conditional lane) ----------
python3 - <<'PY'
import io, os
S = os.environ['SHADOW']
p = os.path.join(S, 'scripts', '_framework_manifest_set.sh')   # ABSOLUTE path: never matches _CANONICAL_GUARDS (_fnmatch_segments is anchored, no guard starts with **)
src = io.open(p, encoding='utf-8').read()
# (1) _framework_target_entries :113-183 -- emit the 6 dest relpaths behind FMS_DELIVERED_TEMPLATES (mirror the FMS_DELIVERED_* idiom at :122,:129,:140,:157,:160)
# (2) add _wbm_route_src -- copy scripts/doctor.sh:418-449 VERBATIM (bash 3.2 linear scan; ${_rs_transform:-} unbraced-default-EMPTY, never :-identity)
# (3) :430-437 -- when FMS_HASH_ROOT is set and _wbm_route_src yields a src, hash $_wbm_hash_root/<src>; substitute:* rows => continue
io.open(p, 'w', encoding='utf-8').write(src)
PY
python3 - <<'PY'
import io, os
S = os.environ['SHADOW']
for name in ('install.sh', 'upgrade.sh'):
    p = os.path.join(S, 'scripts', name)   # export FMS_DELIVERED_TEMPLATES (install.sh near :2540; upgrade.sh near :3529)
    src = io.open(p, encoding='utf-8').read()
    io.open(p, 'w', encoding='utf-8').write(src)
PY
bash -n "$SHADOW/scripts/_framework_manifest_set.sh" && bash -n "$SHADOW/scripts/install.sh" && bash -n "$SHADOW/scripts/upgrade.sh"
git -C "$SHADOW" diff --stat   # THE ANSWER OQ-4 ASKS FOR: the real line budget of arm B
cd "$SHADOW" && CELL_TIMEOUT=180 bash "$SHADOW/scripts/tests/test-ownership-table.sh" > "$OUT/armB.map" 2> "$OUT/armB.err"; echo "rc=$?" >> "$OUT/armB.err"
grep -E '^OWN-[0-9]+[[:space:]]' "$OUT/armB.map" | awk '$2 == "RED" {print $1}' | LC_ALL=C sort > "$OUT/armB.red"; diff -u "$OUT/expected.red" "$OUT/armB.red"; echo "delta_rc=$?"
grep -E '^OWN-[0-9]+[[:space:]]' "$OUT/armB.map" | awk '$2 != "GREEN" && $2 != "RED" {print $1" "$2}'   # must be empty
bash "$SHADOW/scripts/tests/test-ownership-verdict-unit.sh" --quiet; echo "unit_rc=$?"
cd "$SHADOW" && bash "$SHADOW/scripts/tests/test-install-upgrade-parity-e2e.sh" --mode maintainer > "$OUT/armB.parity-maintainer" 2>&1; echo "rc=$?" >> "$OUT/armB.parity-maintainer"
cd "$SHADOW" && bash "$SHADOW/scripts/tests/test-install-upgrade-parity-e2e.sh" --mode user > "$OUT/armB.parity-user" 2>&1; echo "rc=$?" >> "$OUT/armB.parity-user"
cd "$SHADOW" && bash "$SHADOW/scripts/tests/test_install_baseline_manifest.sh" > "$OUT/armB.baseline" 2>&1; echo "rc=$?" >> "$OUT/armB.baseline"
# ---------- reset, then ARM C (MIXED lane hypothesis) ----------
git -C "$SHADOW" checkout -- scripts/ && git -C "$SHADOW" status --porcelain   # must be empty before arm C
python3 - <<'PY'
import io, os
S = os.environ['SHADOW']
p = os.path.join(S, 'scripts', '_framework_manifest_set.sh')
src = io.open(p, encoding='utf-8').read()
# arm B edits, MINUS .github/CODEOWNERS from the route-resolution branch, PLUS:
#   _wbm_is_conditional :320-325        -> add .github/CODEOWNERS
#   _wbm_declared_hash_source :311-318  -> case arm -> ${FMS_HASH_SOURCE_CODEOWNERS:-}
# install.sh/upgrade.sh export FMS_HASH_SOURCE_CODEOWNERS: HASH_TARGET on fresh delivery (rendered bytes exist in NO checkout), HASH_PRIOR_RECORD on continuity (the PROTOCOL.md shape at install.sh:2504).
# DECLARE ON EVERY DELIVERY PATH, not only continuity -- install.sh:2508-2511 records that the previous attempt regressed 24 cells by leaving fresh installs undeclared.
io.open(p, 'w', encoding='utf-8').write(src)
PY
bash -n "$SHADOW/scripts/_framework_manifest_set.sh" && bash -n "$SHADOW/scripts/install.sh" && bash -n "$SHADOW/scripts/upgrade.sh"
git -C "$SHADOW" diff --stat   # if arm C is ~2-3 lines vs arm B's ~13, the MIXED hypothesis is supported
cd "$SHADOW" && CELL_TIMEOUT=180 bash "$SHADOW/scripts/tests/test-ownership-table.sh" > "$OUT/armC.map" 2> "$OUT/armC.err"; echo "rc=$?" >> "$OUT/armC.err"
grep -E '^OWN-[0-9]+[[:space:]]' "$OUT/armC.map" | awk '$2 == "RED" {print $1}' | LC_ALL=C sort > "$OUT/armC.red"; diff -u "$OUT/expected.red" "$OUT/armC.red"; echo "delta_rc=$?"
grep -E '^OWN-[0-9]+[[:space:]]' "$OUT/armC.map" | awk '$2 != "GREEN" && $2 != "RED" {print $1" "$2}'   # must be empty
bash "$SHADOW/scripts/tests/test-ownership-verdict-unit.sh" --quiet; echo "unit_rc=$?"
cd "$SHADOW" && bash "$SHADOW/scripts/tests/test-install-upgrade-parity-e2e.sh" --mode maintainer > "$OUT/armC.parity-maintainer" 2>&1; echo "rc=$?" >> "$OUT/armC.parity-maintainer"
cd "$SHADOW" && bash "$SHADOW/scripts/tests/test-install-upgrade-parity-e2e.sh" --mode user > "$OUT/armC.parity-user" 2>&1; echo "rc=$?" >> "$OUT/armC.parity-user"
cd "$SHADOW" && bash "$SHADOW/scripts/tests/test_install_baseline_manifest.sh" > "$OUT/armC.baseline" 2>&1; echo "rc=$?" >> "$OUT/armC.baseline"
# ---------- report, then teardown ----------
# Per arm report: {arm, red_ids[], green_count, red_count, ambig_count, harness_err, delta_vs_expected, parity_counts_maintainer{IDENTICAL,PERSONALIZED,STALE,MISSING_IN_B,UNCLASSIFIED,ONLY_IN_B,ONLY_IN_B_OUTSIDE_CLAUDE,MODE_DIFF,ACCEPTED,KNOWN-OPEN}, parity_counts_user{same 10}, unit_oracle{PASS,FAIL,SKIPPED}, diff_stat_lines, runtime_s}
# VERDICT = conditional | non-conditional | MIXED. Until it is recorded, ZERO rows may be added to scripts/tests/ownership_table.tsv (Owner rule).
git -C /Users/joaocanhada/canhada-labs/ceo-orchestration worktree remove --force "$SHADOW"
```

## Arquivos do pacote
- `.claude/plans/PLAN-183/wave-w5-approved.md`
- `.claude/plans/PLAN-183/wave-w5-approved.md.asc`
- `.claude/plans/PLAN-183/OWNER-S327-SIGN.sh`
- `.claude/plans/PLAN-183/OWNER-S327-LAND.sh`
- `.claude/plans/PLAN-183/w5-ceremony/S327-W5-DELIVERY.patch`
- `.claude/plans/PLAN-183/w5-ceremony/PROPOSED-PATCH.md`
- `.claude/plans/PLAN-183/w5-ceremony/COMMIT-MSG.txt`
- `.claude/plans/PLAN-183/w5-ceremony/finalize_patch.py`
- `.claude/plans/PLAN-183/w5-ceremony/DESIGN-NOTE.md`
- `.claude/plans/PLAN-183/w5-ceremony/oq4-verdict.md`
- `.claude/plans/PLAN-183/w5-ceremony/rail-round-1.md`
- `.claude/plans/PLAN-183/w5-ceremony/g0-block.sh`
- `.claude/plans/PLAN-183/w5-ceremony/p0-block.sh`
- `.claude/plans/PLAN-183/w5-ceremony/stage-block.sh`
- `.claude/plans/PLAN-183/w5-ceremony/sabotage.sh`
- `scripts/_framework_manifest_set.sh`
- `scripts/install.sh`
- `scripts/upgrade.sh`
- `scripts/doctor.sh`
- `scripts/delivery-routes.tsv`
- `scripts/tests/_parity_classify.py`
- `scripts/tests/ownership_table.tsv`
- `scripts/tests/ownership-expected-reds.txt`
- `.claude/governance/gate-scripts-manifest.txt`
- `.github/workflows/smoke-install.yml`
- `.github/workflows/ownership-nightly.yml`
- `docs/ownership-decision-table.md`
- `.claude/adr/ADR-NNN-delivery-route-resolution.md`
- `.claude/plans/PLAN-183-adopter-fitness.md`
- `CLAUDE.md`

## Riscos
- VACUOUS EXPERIMENT (blocking): _framework_target_entries() (scripts/_framework_manifest_set.sh:113-183) never enumerates docs/ or .github/ - verified, only comments at :310, :492, :548. The 6 routes never reach the resolver at :430-437, so D3 is latent-by-non-entry. An OQ-4 arm that patches only resolution is byte-identical to baseline and proves nothing. Every non-A arm MUST add enumeration first; this also reshapes the OQ-4 line budget from 'TSV rows' to enumeration + hash_source declaration + route resolution.
- WRONG INSTRUMENT: the ownership e2e cannot observe docs/.github at all - _relpath_for (scripts/tests/test-ownership-table.sh:117-123) knows only spec|protocol|marker. It is the REGRESSION detector for the 3 existing surfaces. The observers of the new routes are test-install-upgrade-parity-e2e.sh and test_install_baseline_manifest.sh. Any plan expecting the ownership e2e to flip on the new routes is measuring the wrong thing.
- 24-CELL PRECEDENT: install.sh:2508-2511 records that the previous attempt at this wave regressed 24 cells precisely because it left fresh installs undeclared. Declare hash_source on EVERY delivery path, never only on continuity.
- REGISTRATION REGRESSION: the draft rule 'PRESERVED/SKIPPED stay out' contradicts install.sh:1318-1329, which registers by byte-compare even when it did not write. Adopting the draft drops all 5 registrations on a SECOND install and ships GREEN, because no current Check runs install twice. upgrade.sh:3110-3115 keeps IDENTICAL in but PRESERVED/SKIPPED out - reconcile the two explicitly before fixing any expected count.
- install_docs_template (install.sh:1446-1474) never sets INSTALL_ONE_WROTE (owned by install_one at :877/:905/:919), so the :1318-1329 idiom is not copy-pasteable for the 6 routes. Add a wrote-flag; and the cmp -s half must compare the SOURCE relpath - precisely what has no resolver until D3 lands.
- ADR-192 MANIFEST TRAP: scripts/tests/ownership-nightly-gate.sh and scripts/tests/ownership-expected-reds.txt print oracle 0 yet are members of .claude/governance/gate-scripts-manifest.txt (verified, lines 5-6). Touching either requires the ceremony AND a sha bump, pulling the canonical manifest into Scope. This is exactly the verify-counts.sh lesson from S326, caught by the Smoke Install integrity step.
- ALL-GREEN IS A FAILURE: ownership-nightly-gate.sh fails on ANY difference from the expected RED set including shrinkage (:115-121). An all-green run means the truth table changed - stop and find out why, never 'fix' the expected set to absorb a flip.
- CELL_TIMEOUT default is 60s (test-ownership-table.sh:41) while CI uses 180 (ownership-nightly.yml:131 - the oq4 investigator cited :124-127; the file says :131). On a loaded local machine 60 flakes into TIMEOUT, which the gate treats as outright failure even with an unchanged id-set. Pin 180 in every arm or the arms are not comparable.
- finalize_patch.py uses bare `git diff`, which does NOT capture untracked new files. S326 never exercised that leg (zero `new file mode` lines in its patch). W5 adds new test files, so a new file would vanish from the SIGNED patch in silence. The recreated helper needs `git add -N` in the shadow plus its own positive control.
- SCOPE MUST BE DERIVED, not hand-listed: it was corrected twice already in this plan (doctor.sh, then .github/workflows/smoke-install.yml) and was still incomplete both times. Derive from `git apply --numstat`. G4 has no canonicity filter - every touched path must appear, canonical or not.
- MAIN IS RED BY DESIGN (D1 open => templates/docs/BRANCH-PROTECTION.md diverged 61025a16 -> 966e0571 => STALE 3, which is FATAL). The LAND V block must declare the expected baseline and compare against it, or every V run is noise and the land never passes.
- LONG E2E IN THE LAND BLOCK: ownership-nightly-gate.sh is ~25 min and the parity e2e runs real installs; S326's V block fit in minutes and W5's will not. Decide explicitly in PROPOSED-PATCH.md which runs inside the land vs deferred to CI - and a --skip-slow flag can NEVER have a default (a parameter that changes the verdict has no default).
- CEREMONY UX DEFECT: OWNER-S326-LAND.sh:303-306 only prints a suggested message; the Owner ran bare `git commit`, landed in vim and typed :wq as text. S327 must run `git commit -F <tracked msg> --no-edit` then `git push origin main` and print the hash, plus the editor-escape line.
- VERIFICATION BY GREP IS TAUTOLOGICAL: S325 measured that pointing a route row at a wrong-but-existing source kept all 10 tests green, because assertions compared against the table's own claim. Truth must come from the install.sh call-sites, independent of the table.
- scripts/delivery-routes.tsv is absent from both paths: lists in .github/workflows/smoke-install.yml (grep count 0, verified). A typo confined to the table fires no e2e. Once a CANONICAL script reads it, close this in the same ceremony.
- bash 3.2 floor: no declare -A, so the canonical reader must be a linear scan copied from doctor.sh:418-449. Keep ${_rs_transform:-} unbraced-default-EMPTY - ${_rs_transform:-identity} was the fail-OPEN rail finding that reopened a real contamination leak.
- .github/CODEOWNERS and .github/CODEOWNERS.template are MUTUALLY EXCLUSIVE per run (install.sh:1496 elif vs :1511 else). Enumeration must not emit both or one row is a guaranteed spurious miss.
- C5 UNRESOLVED: whether the two trees enter _framework_target_entries as FILE or DIRECTORY entries is never fixed; the D3 Check silently assumes one. Decide before writing.
- OQ-5 amendment must NOT set _CEREMONY_PERSIST=1 (upgrade.sh:801-803: only RECORDED or EXPLICIT resolutions may persist; persisting the inference makes one missed migration permanent), and its Check must run with CEO_PARITY_PIN pointing somewhere other than v1.2.0 or it is blind for the same reason as today.
- The stale prunable worktree at /private/tmp/claude-501/.../cbec69fd-.../scratchpad/rc3-wt (0cb09c3) will collide with `worktree add` - run `git worktree prune` first.

## Seções incompletas / decisões pendentes
- W5-b checklist re-sequencing: the THIRD Owner decision is still OPEN. Debate w5-round-1 returned ESCALATE/ESCALATE/PROCEED-WITH-CONDITIONS (24 findings, 15 P0); convergence C1 says the current checklist order is inexecutable ([P1] items are prerequisites of [P0]) and C2 says the vacuous Checks must be replaced before any line is written. The 12-unit plan is PROPOSED, not ratified.
- OQ-4 verdict: not produced. The night must MEASURE the generator lane (arms A/B/C) and record conditional | non-conditional | MIXED. Until then zero rows may be added to scripts/tests/ownership_table.tsv, so that file cannot be finalized in the signed Scope and the S327 package must not be signed.
- Arm-A parity baseline numbers were NOT measured in this read-only pass. CLAUDE.md records maintainer = STALE 3 + UNCLASSIFIED 0 post-D2 (CI run 32658998831) and user = 0, but arm A must re-derive its own numbers; never assert the prose. Likewise the ~25 min ownership e2e runtime is DOCUMENTED, not measured here (measured this session: unit oracle 0.064s, PASS=63 FAIL=0 SKIPPED=2 = OWN-0024, OWN-0027).
- Registration rule (byte-compare vs result-only) and C5 (FILE vs DIRECTORY entries) are named as decisions the night must take, but neither is decided in this brief - both are prerequisites of any expected-count assertion.
- CLAUDE.md canonicality was not measured; the ADR-count bump forces a same-commit CLAUDE.md edit against the section-0 cache-discipline rule (closeout-only). Sequence that explicitly before the ceremony.
- AC-9/AC-10 cannot both be validated by an e2e pinned to v1.2.0: CODEOWNERS.template and docs/rotation-log.md are byte-identical pin<->HEAD, so Checks over them are vacuous unless divergence is PLANTED. The planting strategy is not designed here.
- Which long e2e runs INSIDE the LAND V block vs deferred to CI is an open decision that must be recorded in PROPOSED-PATCH.md before signing.
- Rail rounds: none run. The corrected section-8.5.2 prose (S324) has never been railed and is named as the mandatory FIRST unit of W5-b; no rail round over the W5 patch exists yet.
