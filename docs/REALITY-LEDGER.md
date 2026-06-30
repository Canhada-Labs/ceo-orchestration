# Reality Ledger

> **See also:** [`docs/ADAPTIVE-EXECUTION-KERNEL.md`](ADAPTIVE-EXECUTION-KERNEL.md) — companion pre-task classifier.

`reality-ledger.py` is an **advisory drift-detection tool** that cross-checks
claims documented in ADRs, docs, and agent configs against mechanical evidence
in source code, tests, and configuration files. It surfaces gaps like "this
ADR says the feature is wired but no code reads the env-var" or "this action
appears in an emit call but is missing from `_KNOWN_ACTIONS`." It never blocks
a session or CI pipeline — exit code 0 always (advisory), exit code 2 on
internal error only.

---

## Detectors (v1.14.0)

Five detectors ship in the initial release. Detector #5 (`default_flip_orphan`)
is deferred to v1.15.0+ pending a separate enumeration of `_DEFAULTS` baseline.

### Detector 1 — `runtime_read_missing`

Scans for env-vars documented as "this feature is enabled/disabled by
`ENV_VAR`" that have zero **enforcement-level** reads in source code. Operates
at AST level: searches for `os.environ.get('VAR')`, `os.getenv('VAR')`,
`subprocess.run(env={..."VAR":...})` patterns. Cosmetic mentions in comments,
docstrings, and `owner-ceremony/archive/**` are excluded. A finding means the
documented behavior cannot be exercised at runtime.

**Known live finding (v1.14.0):** `CEO_MODEL_DOWNSHIFT` documented in
`docs/CEO-MODEL-ROUTING.md` — 3 cosmetic matches in source, 0 enforcement
reads. The ADR-067 `ACCEPTED-WITH-LIVE-TRAFFIC-FOLLOWUP` status reflects this
openly; detector #1 makes it mechanically observable.

### Detector 2 — `installable_claim_drift`

Checks any component documented as "ACCEPTED, opt-in" where the install script
or requirements file fails at HEAD. Attempts `pip install -r <path>` (or
equivalent) for each declared requirements file; non-zero exit = finding.

**Known live finding (v1.14.0):** `.claude/rag/requirements.lock` is a
placeholder by design; detector #2 surfaces this as a tracked drift item.

### Detector 3 — `model_assignment_divergence`

Cross-checks model assignments claimed in ADRs and `.claude/agents/*.md`
frontmatter against the model actually observed in `audit-log.jsonl` for the
last 30 days. A finding means an archetype declared `model: haiku-3-5` but
every audit-log entry shows `sonnet-4-6`.

### Detector 4 — `enforcement_commit_unpopulated`

Scans all ADRs with `status: ACCEPTED` for a missing or placeholder
`## Enforcement commit` section (literal text `(populated on flip)` or
absent section). A finding means the ADR was accepted but never wired to a
specific commit.

**Known live finding (v1.14.0):** `ADR-067` line 171 has an unpopulated
enforcement commit.

### Detector 6 — `audit_action_phantom`

Cross-checks actions emitted in source code against `audit_emit._KNOWN_ACTIONS`
and vice versa. A finding in one direction means "this action is emitted but
never registered"; a finding in the other means "this action is registered but
never emitted or documented."

**Precedent:** the Codex S76 `skill_bootstrap_used` action was caught as a
phantom before this detector existed — detector #6 codifies that class of
finding mechanically.

---

## Running the tool

```bash
# Human-readable markdown report (stdout) — includes file paths for local triage
python3 .claude/scripts/reality-ledger.py --format markdown

# Filter to medium severity or higher
python3 .claude/scripts/reality-ledger.py --format markdown --severity medium

# Run a single detector
python3 .claude/scripts/reality-ledger.py --detector runtime_read_missing

# JSONL stream for CI / audit-log integration — file paths EXCLUDED from output
python3 .claude/scripts/reality-ledger.py --format jsonl --since 30d

# Write report to a file
python3 .claude/scripts/reality-ledger.py --format markdown --output /tmp/ledger-report.md

# Override per-detector timeout (default 5000ms)
python3 .claude/scripts/reality-ledger.py --detector-timeout-ms 10000
```

---

## Triage workflow

### Local (markdown)

```
1. Run:  python3 .claude/scripts/reality-ledger.py --format markdown
2. Each finding shows:
     detector:              runtime_read_missing
     severity:              medium
     confidence:            0.95
     claim_source_sha256:   <hex>       ← stable cross-session reference
     claim_source_path:     docs/CEO-MODEL-ROUTING.md:30   ← local triage only
     advisory_action:       either wire the runtime read or amend the doc

3. Decide: wire it, amend the doc, or accept as known-drift (add to suppression list)
```

`claim_source_path` is included only in `--format markdown` output (local
stdout). It is intentionally excluded from `--format json` and `--format jsonl`
to prevent file paths from appearing in GitHub issue bodies or audit-log lines.

### CI / audit-log (jsonl)

```
1. Weekly GitHub Actions workflow (reality-ledger.yml) runs:
     python3 .claude/scripts/reality-ledger.py \
       --format markdown --severity medium
2. If findings > 0: workflow opens or updates a single ongoing GitHub issue
   (idempotent; issue body uses claim_source_sha256, never claim_source_path)
3. Pipeline never blocks — advisory only
```

---

## Output field reference

### `--format markdown` (local triage)

| Field | Description |
|-------|-------------|
| `detector` | Detector slug (e.g. `runtime_read_missing`) |
| `severity` | `low` / `medium` / `high` |
| `confidence` | 0.0–1.0 float |
| `claim_source_sha256` | SHA-256 of the source file at finding time |
| `claim_source_path` | File + line for local triage — **never in JSON/jsonl** |
| `expected_evidence` | What the detector looked for |
| `actual_evidence_redacted` | What it found (secrets scrubbed via `redact_secrets()`) |
| `first_observed_at` | ISO-8601 timestamp |
| `advisory_action` | Suggested next step |

### `--format json` / `--format jsonl` (CI / audit)

Same fields as markdown **except** `claim_source_path` is **mandatorily
absent**. A contract test asserts this invariant: `--format json` output has
`claim_source_sha256` and does NOT have `claim_source_path`.

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Ran successfully — findings present OR zero findings (advisory, never blocks) |
| `2` | Internal detector error (import failure, filesystem error, unrecoverable exception) |

The tool **never** exits with a non-zero code based on finding count. CI jobs
should use `exit 0` unconditionally and inspect finding count separately if
blocking behavior is desired (not recommended for advisory-only tooling).

---

## Latency budget

Full suite p95 target: **< 30 seconds** at repo scale (4400+ tests, 105+ ADRs,
170+ Python source files). Per-detector default timeout: 5000ms. On timeout the
detector emits a fail-open breadcrumb, skips itself, and the suite continues.
Override with `--detector-timeout-ms N`.

---

## Known false-negative window

**Detector #6 (`audit_action_phantom`) pre-PLAN-065 baseline:**

The audit-log baseline before v1.12.1 GA (2026-05-04) does not include the
`ceo_boot_emitted` action. Detector #6 will report 0 hits for that action when
run against audit-log windows that predate v1.12.1. This is correct behavior,
not a regression — `/ceo-boot` and its audit emission shipped in PLAN-065.

If your audit-log only contains entries from before 2026-05-04, detector #6
findings for `ceo_boot_emitted` absence are expected and should not be
triaged as production gaps.

---

## Suppression (future)

A suppression list for known-accepted drift items is planned for v1.15.0+.
For now, findings for known live gaps (listed in each detector section above)
can be acknowledged in the ongoing GitHub issue without closing it.

---

## Security notes

- `actual_evidence` fields pass through `_lib.redact.redact_secrets()` before
  emission; credentials in scanned source are replaced with `[API_KEY]` etc.
- Detector #1, #4, and #6 explicitly exclude `task-route.py` and
  `reality-ledger.py` themselves from grep targets (anti-self-referential).
- `claim_source_path` is **never** committed to repo or included in issue
  bodies — SHA-256 reference only in persistent outputs.
