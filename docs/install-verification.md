# Install verification

> **Audience:** adopter running `./scripts/install.sh` for the first time, wanting to confirm the framework is wired correctly before a real session.
> **Budget:** ≤5 min.
> **Exit condition:** every step below returns green; no red errors.

This is the smoke-test promised by the `install.sh` script and referenced from QUICKSTART (PT-BR + EN). It validates the installed framework end-to-end without spawning a real agent.

## Preconditions

- You ran `./scripts/install.sh [--profile core,<domain>]` in your target repo (fresh install or existing).
- You opened a terminal in the target repo root.
- `python3 --version` is ≥ 3.9.

## Step 1 — Governance validate

```bash
bash .claude/scripts/validate-governance.sh 2>&1 | tail -15
```

**Expected last line:** `PASS: Governance files validated.`

If it fails, re-run `./scripts/install.sh --force` or inspect `team.md` / `settings.json` for placeholder leaks (`{{OWNER_NAME}}` etc.).

## Step 2 — Health check

```bash
python3 .claude/scripts/ceo-health.py 2>&1 | tail -30
```

**Expected first line:** `ceo-health: HEALTHY` (or `DEGRADED` with advisory hooks listed — not fatal).

Every line with `✓` = green. Every `⚠ [advisory]` = optional hook not executable; safe for most adopters. A `✗` = required hook missing/broken; resolve before using the framework.

## Step 3 — Parse settings.json

```bash
python3 -c "import json; json.load(open('.claude/settings.json'))" && echo "settings.json OK"
```

**Expected:** `settings.json OK`. Any JSON parse error means the install corrupted the settings; re-run `install.sh` with `--force`.

## Step 4 — Dispatch table coherence

```bash
python3 .claude/scripts/generate-dispatch.py --check 2>&1 | tail -5
```

**Expected:** `OK: dispatch table in sync` (or equivalent). If out of sync, run `python3 .claude/scripts/generate-dispatch.py --write`.

## Step 5 — CODEOWNERS present (governance)

```bash
test -f .github/CODEOWNERS && echo "CODEOWNERS: OK" || echo "CODEOWNERS: MISSING (configure branch protection)"
```

**Expected:** `CODEOWNERS: OK`. If missing, branch protection governance is not wired; see `docs/BRANCH-PROTECTION.md`.

## Step 6 — Contamination scan (no stale Owner handles)

```bash
bash .claude/scripts/check-contamination.sh 2>&1 | tail -10
```

**Expected:** `PASS: no contamination detected` (or equivalent green). If it flags hits, they must all appear in `.github/CODEOWNERS` or the `test-env-hygiene-allowlist.yaml`.

## Step 7 — Unit tests collect (no import errors)

```bash
python3 -m pytest --co -q .claude/hooks/tests .claude/scripts/tests 2>&1 | tail -3
```

**Expected:** `N tests collected` with N ≥ 4000 for v1.7.0-rc.1. Import errors = broken install.

## Step 8 — Cost snapshot

```bash
python3 .claude/scripts/ceo-cost.py --since 1h 2>&1 | tail -20
```

**Expected:** a cost table (may show 0 entries if no spawns yet). No Python tracebacks.

## Step 9 — Audit-log writable

```bash
python3 .claude/scripts/audit-query.py tail --limit 3 2>&1 | tail -10
```

**Expected:** either the last 3 audit entries or a clean "no entries yet" message. Any `PermissionError` / `FileNotFoundError` on the audit-log path means the `~/.claude/projects/<slug>/` directory isn't writable; check ownership + perms.

## If all 9 steps pass

You have a correctly installed framework. Proceed to your first real session — open Claude Code in this target repo and the GATE-1/2/3 protocol from `CLAUDE.md` will activate automatically.

## If a step fails

1. Re-read the step's expected output carefully — some failures are cosmetic (warnings, advisory hooks).
2. Check `docs/TROUBLESHOOTING.md` for the specific error.
3. Run `./scripts/install.sh --force --profile <your-profile>` to re-lay files.
4. Open a GitHub issue with the failing step + full output if the install is fundamentally broken.

## Why this doc exists

Before PLAN-024 F-ux-005 (2026-04-18), QUICKSTART.md and QUICKSTART.en.md both referenced this file without it existing — an adopter would follow the link and hit 404. This doc closes that loop. The 9-step verification above is the smoke-test contract between the framework install and the adopter's first use.
