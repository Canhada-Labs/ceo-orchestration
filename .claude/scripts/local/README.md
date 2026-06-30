# `.claude/scripts/local/` — local-only ceremony tooling

Scripts that run on the **Owner's machine** only, never as part of CI or
adopter installs. Includes the **ceremony template generator** (PLAN-073
§2) and any one-shot helpers (e.g. `SIGN-WAVE-D-2-SENTINEL.sh`) that get
checked in for forensic record after use.

## `generate-ceremony.sh`

Synthesizes an Owner-GPG ceremony script from a plan-id + sentinel-scope
+ canonical-paths input. Replaces hand-writing `OWNER-CEREMONY.sh` from
scratch each time, codifying every S80+S81 lesson as a mechanical guard.

### Usage

```bash
bash .claude/scripts/local/generate-ceremony.sh \
  --plan PLAN-NNN \
  --round N \
  --scope-file path/to/sentinel-scope.md \
  --canonical-paths "path1,path2,path3" \
  --output OWNER-CEREMONY.sh \
  [--ignore "path-glob1,path-glob2"]
```

### Flags

| Flag | Purpose |
|---|---|
| `--plan` | `PLAN-NNN` identifier (3 zero-padded digits enforced) |
| `--round` | Integer round number (positive int enforced) |
| `--scope-file` | Path to sentinel `approved.md` — must live at `.claude/plans/PLAN-NNN/architect/round-N/approved.md` (parser-discovery glob). Must contain literal `Scope:` and `Approved-By: @<handle> <token>` lines (NOT markdown `## Scope` / `## Approved-By` headings). |
| `--canonical-paths` | Comma-separated list of canonical paths the ceremony will patch. Each must match a guard pattern in `check_canonical_edit.py::_CANONICAL_GUARDS` AND must be declared under `Scope:` in the sentinel. |
| `--output` | Path to write the generated ceremony script. |
| `--ignore` | (Optional) Comma-separated extra path globs the dirty-filter should tolerate (e.g. `.claude/plans/PLAN-074` for a parallel-terminal draft). Globs that would shadow a canonical path are rejected. |

### Generator-level guards

Six fail-fast pre-emit checks (non-zero exit):

| Code | Guard | What it catches |
|---|---|---|
| G1 | Canonical path validation | Misspelled paths, non-canonical paths that don't need a sentinel |
| G2 | Scope file location + parser format | Wrong directory (not under `.claude/plans/PLAN-NNN/architect/round-N/`), wrong basename (not `approved.md`), missing literal `Scope:` / `Approved-By:` lines |
| G3 | Ignore-shadows-canonical | Dirty-filter masking a file the ceremony patches |
| G4 | Generated script syntax | Emitted script fails `bash -n` |
| G5 | PLAN-NNN dir exists | Typo in `--plan` |
| G6 | Canonical path declared in scope | Path missing from sentinel's `Scope:` block (would block at edit time) |

### Generated ceremony's runtime guards

The output script bakes in eight runtime hardenings derived from S80+S81
incidents. These are NOT optional — they are how the script is shaped:

| Code | Hardening | Lesson source |
|---|---|---|
| R1 | `GPG_TTY` auto-setup + `gpgconf --reload gpg-agent` | S80 PLAN-072 PINENTRY-timeout |
| R2 | `SKIP_PREFLIGHT_PYTEST=1` retry-after-fail | S80 ceremony retries |
| R3 | Configurable dirty-filter via `--ignore` | S81 PLAN-074 race-safe |
| R4 | CLAUDE.md size pre-check (≤39800 with 200B headroom) | S81 39887 byte size-cap fail |
| R5 | Idempotent sentinel sign (skip if `.asc` non-empty + verifies clean) | S81 partial-sign retry |
| R6 | Block 5 explicit-add (no `git add -A`) | S81 PLAN-074 + CLAUDE.md drift bundling |
| R7 | Block 4 unsets `CEO_KERNEL_OVERRIDE` before pytest + governance | S77 ceremony override hygiene |
| R8 | Block 3 placeholder with `BEGIN/END` markers; emits `exit 1` until filled | S81 silent-skip prevention |

### Block 3 is yours to fill in

The generator stubs Block 3 with markers:

```bash
# >>>>> CEREMONY-PATCHES-BEGIN >>>>>
# ... fill in your patches here ...
exit 1
# <<<<< CEREMONY-PATCHES-END <<<<<
```

Reference patterns (see `OWNER-WAVE-D-CEREMONY.sh` /
`OWNER-WAVE-D-2-CEREMONY.sh` for canonical examples):

1. **Python heredoc exact-replace** — preferred for textual patches:

   ```bash
   python3 - <<'PYEOF'
   from pathlib import Path
   p = Path("path/to/file.py")
   content = p.read_text()
   old = "literal anchor text"
   new = "replacement text"
   if old not in content:
       raise SystemExit("FAIL: cannot find anchor")
   p.write_text(content.replace(old, new, 1))
   PYEOF
   ```

2. **`git mv`** — canonical file moves:

   ```bash
   if [ -f path/from.py ] && [ ! -f path/to.py ]; then
     git mv path/from.py path/to.py
   fi
   ```

3. **`cp staging → canonical`** — promote-from-staging flows:

   ```bash
   cp .claude/plans/PLAN-NNN/staging/canonical/X.md .claude/adr/X.md
   ```

After filling Block 3, re-run `bash -n OWNER-CEREMONY.sh` to confirm
syntax stays clean. Owner runs `bash OWNER-CEREMONY.sh` (paste in their
TTY for the GPG passphrase prompt).

### Tests

Run the suite:

```bash
bash .claude/scripts/local/tests/test_generate_ceremony.sh
```

Covers 8 of the 9 PLAN-073 §2.4 acceptance items (T6 markdown-heading
parser-fail is covered indirectly by T5 location check + the existing
`test_check_canonical_edit.py` regression corpus).

## `release-dry-run.py`

Reproduces locally **16 always-run + 1 conditional sigstore** validation
gates from `.github/workflows/release.yml` so the Owner can verify a tag
before pushing.

**PLAN-078 Wave 3 deliverable** — Owner-machine local pre-tag check.
Catches the same failure classes that release.yml catches in CI, but in
~5-30s instead of ~8 min × N retries.

### Usage

```bash
# Fast iteration (skip tests, install, network):
python3 .claude/scripts/local/release-dry-run.py \
  --target-version 1.15.0-rc.1 \
  --skip-tests --skip-install --skip-network

# Full local run (mirrors release.yml minus CI-only steps):
python3 .claude/scripts/local/release-dry-run.py --target-version 1.14.0

# Strict mode — treat skipped gates as failures:
python3 .claude/scripts/local/release-dry-run.py \
  --target-version 1.14.0 --strict
```

### Flags

| Flag | Effect |
|---|---|
| `--target-version` | Version to validate (e.g. `1.14.0` or `1.15.0-rc.1`). Inferred from `git describe --tags --exact-match` if omitted. |
| `--skip-tests` | Skip pytest suites (gates 6, 7, 8) — useful when iterating on canonical edits |
| `--skip-install` | Skip smoke install + self-SHA validation (gates 9, 10) |
| `--skip-network` | Skip GitHub API check (gate 12 weekly workflow status) |
| `--strict` | Exit non-zero on any skipped gate (default: SKIP == PASS) |
| `--repo-root` | Override repo root (default: cwd) |

### 16 + 1 gates mirrored

| # | release.yml step | Local mirror |
|---|---|---|
| 1 | `:37` VERSION matches tag | `VERSION` file vs `--target-version` |
| 2 | `:70` 24h Codex re-pass (GA only) | `git tag -l --sort=-creatordate v{ver}-rc.*` + waiver-aware |
| 3 | `:132` CHANGELOG entry | `^## \[{ver}\]` regex on `CHANGELOG.md` |
| 4 | `:143` Registry validation | invokes `registry.py --validate` |
| 5 | `:146` Governance structural | invokes `validate-governance.sh` |
| 6 | `:158` Hook test suite | `pytest .claude/hooks/tests` |
| 7 | `:162` Script test suite | `pytest .claude/scripts/tests` |
| 8 | `:165` Replay test suite | `pytest .claude/scripts/replay/tests` |
| 9 | `:172` Smoke install | `install.sh` into tmpdir + 4-essential check |
| 10 | `:192` install.sh self-SHA | trailer placeholder check (full E2E in CI only) |
| 11 | `:253` Audit-log schema additivity | grep 14 v1 fields in `AUDIT-LOG-SCHEMA.md` |
| 12 | `:288` Weekly workflow status | `gh run list` last 3 + 14d staleness + waiver-aware |
| 13 | `:401` Generate CycloneDX SBOM | invokes `generate-sbom.py` |
| 14 (C) | `:408` Sigstore signing | always SKIP on `*-rc*` + `cosign` presence |
| 15 | `:419` Verify owner.asc | `gpg --show-keys` on `.claude/trust/owner.asc` |
| 16 | `:437` Verify tag GPG | `git tag --verify` (skip if tag absent locally) |

### Output

Markdown table on stdout with PASS / FAIL / SKIP per gate + per-gate
duration_ms + final summary. Exit 0 = clean (or all skipped without
`--strict`). Exit 1 = any FAIL.

### Tests

```bash
cd .claude/scripts/local && python3 -m unittest tests.test_release_dry_run -q
```

34 tests covering each gate's pass/fail/skip path + CLI behavior +
edge cases (missing files, malformed waivers, pyyaml import error).

### Dependencies

`pyyaml` (lazy import via `_ensure_pyyaml()` per
`docs/stdlib-exceptions.md`). Exit 2 with install hint if missing.

---

## `dependency-graph.py`

Renders a static, offline-safe HTML+SVG visualization of plan
dependencies parsed from `.claude/plans/PLAN-*.md` frontmatter.

**PLAN-078 Wave 4 spike** — non-canonical, no GPG required. Produced
without the bundled ceremony of PLAN-078 because the script lives under
`.claude/scripts/local/` and the output HTML is gitignored.

### Usage

```bash
python3 .claude/scripts/local/dependency-graph.py \
  [--plans-dir .claude/plans] \
  [--output .claude/scripts/local/dependency-graph.html] \
  [--strict-cycles] \
  [--max-bytes 524288]
```

Default output lives **outside** `.claude/plans/` (under
`.claude/scripts/local/`) so it doesn't conflict with the PLAN-SCHEMA §1
filename validator in `validate-governance.sh`.

Open the resulting `.html` in any browser. Pure SVG inline, no JS, no
network calls — safe to open offline.

### Field whitelist

Only these frontmatter keys are read (PLAN-SCHEMA §2-3 + extension
precedent per PLAN-078 §Wave 4 CDX-UNIQUE-05):
`id, title, status, created, owner, depends_on, sprint, tags,
external_wait, related_plans, parent_plan, level`. Everything else is
dropped. Plan markdown body is **never** rendered.

### Edges

| Kind | Style |
|---|---|
| `depends_on` | solid |
| `external_wait` | dashed |
| `related_plans` | dotted |
| `parent_plan` | dash-dot |

### Tests

```bash
python3 -m unittest discover .claude/scripts/local/tests -v
```

17 tests cover frontmatter parsing, whitelist enforcement, cycle
detection (2- and 3-node), topological layout, HTML/SVG escape (XSS
safety), and CLI exits.

### Output cap

Default 500 KB cap (PLAN-078 §Wave 4 PERF-P1-04). Current run on 74
plans = ~47 KB.

---

### Why this lives under `.claude/scripts/local/`

The path is **deliberately not** `.claude/scripts/` because:

- `.claude/scripts/` ships in the framework distribution (templates,
  install.sh propagation).
- `.claude/scripts/local/` is **out of scope for adopters** — the
  ceremony generator only makes sense for the framework's own
  contributors operating on canonical-guarded paths.
- `scripts/local/historical/` (root-level) is the forensic ceremony
  archive (PLAN-063 §S5); this dir is the *active* tooling that
  produces ceremonies before they get archived.

The contamination check allowlist (`check_contamination.py`) does NOT
list `.claude/scripts/local/*` as a special zone because it should not
contain owner handles or paths — only generator logic.
