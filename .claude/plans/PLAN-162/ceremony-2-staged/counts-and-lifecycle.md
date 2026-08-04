# Ceremony 2 — derived-counts map + plan lifecycle recipe

> Prepared 2026-08-03 (S291 follow-up). All numbers below were derived FROM DISK
> at commit `0e55de7` (main) and from `plan-165-draft` (`fa67642`), never from
> memory. Derivation commands are printed inline with their outputs.

## 0. Derived truth (inputs printed)

| Derivation (authority mirror) | main today | post-merge | final (ceremony) |
|---|---|---|---|
| `ls .claude/adr/ADR-*.md \| wc -l` (verify-counts.sh:99) | **184** | 185 (+ADR-185) | **187** (+2 AMENDs) |
| `find .claude/commands -maxdepth 1 -name '*.md' \| wc -l` (verify-counts.sh:180-182) | **26** | **27** (+night-mode.md) | **27** |

- Branch adds exactly **one** ADR: `git diff main...plan-165-draft --name-only | grep .claude/adr/` → `ADR-185-night-mode-posture-toggle.md` only (confirmed `git show plan-165-draft:.claude/adr/ADR-185-night-mode-posture-toggle.md` → `id: ADR-185`, `status: PROPOSED`). No SKILL.md changes on the branch — only `adrs` and `commands` move in this ceremony.
- The ceremony then copies into `.claude/adr/` the two staged AMENDs (both match the `ADR-*.md` glob, so both COUNT — the S285 "AMEND=arquivo" rule):
  - `ceremony-2-staged/ADR-110-AMEND-2-rail-timeout-recalibration.md` → `.claude/adr/ADR-110-AMEND-2-rail-timeout-recalibration.md`
  - `ceremony-2-staged/ADR-164-AMEND-1-draft.md` → `.claude/adr/ADR-164-AMEND-1-cache-partition-and-wall-deadline.md` (copy target declared in the file's own header comment)
- Therefore the branch docs, which already say **185 ADRs / 27 commands**, become STALE for ADRs the moment the AMENDs land: final target is **187 / 27**.

## 1. Site map — every doc site that pins the counts (derived by grep, incl. `#`-comment and `<!-- -->` forms)

Grep scope: `README.md README.pt-BR.md CLAUDE.md docs/ npm/ templates/ .claude/commands/ INSTALL.md`, patterns `\b(180|184|185)\b`, `\b(22|26|27)\b` near command words, plus a `<!--` sweep (only `last-reviewed` markers carry numbers in HTML comments — zero count pins hide there). `templates/`, `.claude/commands/` and `INSTALL.md` carry **no** ADR/command count pins (INSTALL.md's "22 newer domains" is a domain claim, not these metrics).

Line numbers are the **post-merge** ones (from `git show plan-165-draft:<file>`); "main today" shows the pre-merge value at the equivalent site.

### ADR count — 12 sites, all end at **187** (apply-counts.sh does this step)

| # | Site (post-merge file:line) | Form | main today | post-merge | final | Value-watched by |
|---|---|---|---|---|---|---|
| 1 | `CLAUDE.md:54` | prose `**N ADRs**` | 184 | 185 | **187** | check-claude-md-claims.py:141-147 (`\b(\d+)\s+ADRs\b`, tolerance 0, CI: validate.yml) |
| 2 | `README.md:59` | table `\| Architecture decision records \| **N** \|` | 184 | 185 | **187** | verify-counts TABLE_RULES `adrs` (verify-counts.sh:382) → pair `adrs@README.md` |
| 3 | `README.md:186` | comment `# N ADRs` | 184 | 185 | **187** | UNWATCHED for value (no prose rule matches `# N ADRs`) |
| 4 | `README.pt-BR.md:57` | table row | **180 (stale)** | 185 | **187** | UNWATCHED — pt-BR is not in verify-counts DOCS (verify-counts.sh:280-284); the S291-class miss, branch fixes the stale 180 |
| 5 | `README.pt-BR.md:166` | comment `# N ADRs` | **180 (stale)** | 185 | **187** | UNWATCHED (same) |
| 6 | `docs/ARCHITECTURE.md:56` | tree comment `# N architecture decision records` | 184 | 185 | **187** | UNWATCHED for value |
| 7 | `docs/ARCHITECTURE.md:71` | table `\| ADRs \| N \|` | 184 | 185 | **187** | verify-counts TABLE_RULES → pair `adrs@docs/ARCHITECTURE.md` |
| 8 | `docs/ARCHITECTURE.md:237` | prose `(N to date)` | 184 | 185 | **187** | UNWATCHED for value |
| 9 | `docs/FAQ.md:107` | comment `# N ADRs` | 184 | 185 | **187** | UNWATCHED for value (the site the S291 checklist missed — still exists, verified) |
| 10 | `docs/GUIA-COMPLETO.md:167` | prose `N ADRs document` | 184 | 185 | **187** | UNWATCHED for value (the other S291-missed site — still exists, verified) |
| 11 | `npm/README.md:59` | table row | 184 | 185 | **187** | verify-counts TABLE_RULES → pair `adrs@npm/README.md` |
| 12 | `npm/README.md:122` | comment `# N ADRs` | 184 | 185 | **187** | UNWATCHED for value |

### Command count — 12 sites, all end at **27** (fully carried by the merge; apply-counts.sh only VERIFIES)

| # | Site (post-merge file:line) | Form | main today | post-merge = final | Value-watched by |
|---|---|---|---|---|---|
| 1 | `CLAUDE.md:54` | prose `**N slash commands**` | 26 | **27** | verify-counts prose rule `(\d+) slash commands` (verify-counts.sh:363-365) → `commands@CLAUDE.md` |
| 2 | `README.md:58` | table `\| Slash commands \| **N** \|` | 26 | **27** | TABLE_RULES `commands` (verify-counts.sh:385) → `commands@README.md` (=2 with #3) |
| 3 | `README.md:185` | comment `# N slash commands` | 26 | **27** | prose rule → same pair |
| 4 | `README.pt-BR.md:56` | table row | 26 | **27** | UNWATCHED (pt-BR not in DOCS) |
| 5 | `README.pt-BR.md:165` | comment | **22 (stale)** | **27** | UNWATCHED — main pt-BR was internally inconsistent (table 26, comment 22); branch fixes both |
| 6 | `docs/ARCHITECTURE.md:51` | tree comment `# N slash commands (*.md)` | 26 | **27** | prose rule → `commands@docs/ARCHITECTURE.md` (=2 with #7) |
| 7 | `docs/ARCHITECTURE.md:70` | table row | 26 | **27** | TABLE_RULES → same pair |
| 8 | `docs/ARCHITECTURE.md:270` | prose `(N of them — e.g. /spawn...` | **22 (stale)** | **27** | UNWATCHED for value (matches no rule — exactly why it sat at 22 since the 22-command era; branch fixes) |
| 9 | `docs/FAQ.md:106` | comment | 26 | **27** | prose rule → `commands@docs/FAQ.md` |
| 10 | `docs/COMMAND-SKILL-HOOK-MAP.md:128` (main: 127) | `- Commands: N` | 26 | **27** | DERIVED doc — regen gate `gen-command-skill-hook-map.py --check` (validate.yml:268); branch regenerated it (adds `/night-mode` row) |
| 11 | `npm/README.md:58` | table row | 26 | **27** | TABLE_RULES → `commands@npm/README.md` (=2 with #12) |
| 12 | `npm/README.md:121` | comment | 26 | **27** | prose rule → same pair |

## 2. verify-counts manifest (per-site liveness) — what the ceremony must keep true

- **Gate script (real path):** `.claude/scripts/local/verify-counts.sh` — derives `adrs` at line 99, `commands` at lines 177-182; prose rules `RULES` at lines 300-373 (`adrs`: line 325; `commands`: lines 363-365); table-cell rules `TABLE_RULES` at lines 380-391 (`adrs` label regex line 382, `commands` line 385). Watched DOCS list at lines 280-284: `CLAUDE.md, README.md, INSTALL.md, docs/ARCHITECTURE.md, docs/GUIA-COMPLETO.md, docs/FAQ.md, npm/README.md` (+`RELEASE.md` for release_steps only). **README.pt-BR.md is NOT watched** — its sites are discipline-only (and were stale at 180/22/26 on main until this branch).
- **Per-site expectation manifest (the 54 `metric@doc` pairs):** `.claude/scripts/tests/test_verify_counts.py:195-250` (`_EXPECTED_SITES`), asserted with EXACT counts in `test_real_repo_per_document_liveness` (lines 252-274). The 8 pairs this ceremony touches:

  | pair | exact count | claim sites |
  |---|---|---|
  | `adrs@README.md` | 1 | table row :59 |
  | `adrs@docs/ARCHITECTURE.md` | 1 | table row :71 |
  | `adrs@npm/README.md` | 1 | table row :59 |
  | `commands@CLAUDE.md` | 1 | prose :54 |
  | `commands@README.md` | 2 | table :58 + comment :185 |
  | `commands@docs/ARCHITECTURE.md` | 2 | tree comment :51 + table :70 |
  | `commands@docs/FAQ.md` | 1 | comment :106 |
  | `commands@npm/README.md` | 2 | table :58 + comment :121 |

- **Liveness invariant:** the ceremony changes only NUMBERS inside existing phrasings — no claim site is added, dropped, or re-phrased — so `rule_matches_by_doc` is unchanged and `_EXPECTED_SITES` needs **no re-ratification**. (The FAQ's new §12 and TROUBLESHOOTING section carry no count phrasings — verified by grep on the branch.)
- **Value invariant (why atomicity matters):** `test_real_repo_docs_pass` (test_verify_counts.py:146-154) and `check-claude-md-claims.py` (wired in `validate.yml`) both compare doc values against LIVE disk. A commit that lands the AMEND files with docs still at 185 is **CI-red**; a commit that bumps docs to 187 before the AMENDs exist is also red. **The two AMEND copies and the 12-site bump must land in the SAME commit** (or at minimum the same push must end converged — same-commit is the safe shape).

## 3. apply-counts.sh — order of operations in the ceremony

```
1. git merge plan-165-draft            # docs -> 185/27, ADR-185 + night-mode.md arrive
2. cp the two AMENDs into .claude/adr/ # disk becomes 187
3. bash .claude/plans/PLAN-162/ceremony-2-staged/apply-counts.sh   # 185 -> 187, 12 sites
4. Controls (printed by the script): 0 old sites; 12 ADR sites @187; 12 command sites @27
5. bash .claude/scripts/local/verify-counts.sh --no-tests
   python3 .claude/scripts/check-claude-md-claims.py
   python3 -m pytest .claude/scripts/tests/test_verify_counts.py -q
6. Single commit: AMENDs + doc bumps (+ plan status edits below)
```

Script properties: bash 3.2 (no mapfile/assoc arrays), BSD+GNU sed, fail-closed sequencing guard (aborts unless disk already reads 187/27 and the three new ADR files + night-mode.md exist), idempotent (patterns target the OLD literal in exact count context; `ADR-185` literals can never match), prints its inputs before acting. **Not executed** — staged only.

## 4. Plan-file lifecycle recipe (validator-cited)

**Validator:** `.claude/hooks/check_plan_edit.py`, registered in `.claude/settings.json` under `hooks.PreToolUse`, matcher `Edit|Write|MultiEdit` (via `_python-hook.sh`) — it validates each EDIT to a `.claude/plans/PLAN-*.md` file, so each status transition must be its own Edit operation (Write/MultiEdit are synthesized to the same check).

- Transition graph: `check_plan_edit.py:122-130` (`_ALLOWED_TRANSITIONS`).
  - `"reviewed": {"reviewed", "executing", "abandoned", "refused", "superseded"}` — **line 124**. `done` is NOT in the set → **`reviewed → done` direto é ILEGAL**; the hook rejects it at **lines 291-298** ("PLAN-LIFECYCLE: illegal transition ... See .claude/plans/PLAN-SCHEMA.md §4").
  - `"executing": {"executing", "done", ...}` — line 125 — is the only path to `done`.
- Required fields (`_check_required_fields`, lines 300-338):
  - `→ done`: `completed_at: <YYYY-MM-DD>` (**lines 322-326**) AND non-empty `related_commits: [sha1, ...]` (**lines 327-332**).
  - `→ reviewed`: `reviewed_at` (lines 316-320) — already satisfied on both plans.

**Current state (disk):** `PLAN-165-night-mode-owner-autonomy-toggle.md:4` = `status: reviewed`; `PLAN-162-canonical-edit-council-s280-triage.md:4` = `status: reviewed`.

### PLAN-165 — reviewed → executing → done (two separate edits, two commits)

1. **Edit A (before/with the merge commit):** frontmatter `status: reviewed` → `status: executing`. Legal per line 124. Commit it (can ride the ceremony land commit).
2. Execute: merge + probes AC-7/AC-8 + apply-counts + gates green.
3. **Edit B (closeout commit):** `status: executing` → `status: done`, adding in the same edit:
   - `completed_at: 2026-08-0X`
   - `related_commits: [<merge/land sha>, <sentinel sha>, ...]` (non-empty; the ceremony land + sentinel SHAs)
   Legal per line 125; fields per lines 322-332. Skipping Edit A and going `reviewed → done` in one edit is blocked by lines 291-298.

### PLAN-162 — reviewed → executing (stays executing)

1. **One edit:** `status: reviewed` → `status: executing` (legal per line 124). Commit with the ceremony.
2. It REMAINS `executing` until W2 is verified in a later session — no `completed_at`/`related_commits` yet. (Note: `check_plan_edit.py:53-58` will surface an advisory `paperclip_in_progress` breadcrumb if it sits `executing` >24h with no commits touching the plan file — expected, fail-open, not a block.)

## 5. Residual risks / notes for the CEO

- **Same-commit atomicity** (§2) is the one hard constraint: AMEND files + 12-site bump + (ideally) the plan-status edits in one commit keeps every gate (claims, verify-counts real-repo tests) green at every pushed SHA.
- `ADR-164-AMEND-1-draft.md` must be **renamed on copy** to `ADR-164-AMEND-1-cache-partition-and-wall-deadline.md` (its own header names the target). Landing it under the `-draft` name would still count (glob matches) but violates the slug convention.
- ADR-185 lands as `status: PROPOSED` from the branch — if the ceremony ratifies it, flipping to ACCEPTED is an `.claude/adr/**` canonical edit inside the same GPG ceremony scope.
- After landing, regenerate/verify derived surfaces exactly as the S291 checklist prescribes: `gen-command-skill-hook-map.py --check` is CI-enforced (validate.yml:268) but the branch already regenerated the map (Commands: 27 + `/night-mode` row) — zero drift expected.
