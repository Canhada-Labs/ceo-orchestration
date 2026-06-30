# Admin tooling — onboarding packs + audit backups

PLAN-010 Phase 6. Two small stdlib-only CLIs for Owner / admin use:

- `.claude/scripts/admin-invite.py` — build an onboarding pack for a
  new team member.
- `.claude/scripts/backup-audit.py` — snapshot + rotate the audit log.

Both scripts assume Python 3.9+. They write OUTSIDE the repo by default
(debate C13): onboarding packs live under `~/ceo-onboarding-packs/`,
audit backups under `~/.claude/projects/<name>/backups/` (ADR-001
amendment, 2026-04-14).

## admin-invite.py

Generates a self-contained directory a new employee can work through on
their first session.

### Usage

```bash
# Default out-dir: ~/ceo-onboarding-packs/pack-<slug>/
python3 .claude/scripts/admin-invite.py --name "Alice Martins"

# Explicit output dir
python3 .claude/scripts/admin-invite.py \
  --name "Alice" \
  --out-dir ~/share/alice-pack

# Overwrite an existing non-empty dir
python3 .claude/scripts/admin-invite.py --name "Alice" --force
```

### Pack contents

- `FOR-EMPLOYEES.md` — framework ground rules (veto gates, spawn
  protocol, conditional gates).
- `first-session-checklist.md` — ordered bullet list of first-session
  steps.
- `memory-seed.md` — templates for `user_role.md` and
  `feedback_preferences.md` memory files.
- `README.md` — short personalized welcome.

### Exit codes

| Code | Meaning                                    |
|-----:|--------------------------------------------|
|   0  | Pack built                                  |
|   1  | Output dir exists and is non-empty (re-run with `--force`) |
|   2  | Usage / missing `--name`                   |

### Safety notes

- Default path is under `$HOME`, never cwd — prevents accidental git
  commits of the pack.
- Tests assert that no generated file contains a canary env var pattern
  (`ANTHROPIC_*`, `GITHUB_*`, `AWS_*`) or any current process env var
  name. The script only copies static docs, but the invariant is
  enforced by CI so future changes can't regress.
- `onboarding-pack-*/` is in `.gitignore` in case someone runs with
  `--out-dir .` anyway.

## backup-audit.py

Gzipped daily snapshot of the audit log. Safe against concurrent writers
via the shared `_lib/filelock.py` primitive (debate C9 HIGH).

### Usage

```bash
# Default: snapshot ~/.claude/projects/ceo-orchestration/audit-log.jsonl
#          into   ~/.claude/projects/ceo-orchestration/backups/
python3 .claude/scripts/backup-audit.py

# Custom dirs (tests / multi-project)
python3 .claude/scripts/backup-audit.py \
  --audit-dir  /tmp/audit \
  --backup-dir /tmp/audit/backups \
  --keep-days  30 \
  --max-total-bytes 500000000
```

### Rotation policy

- Filenames: `audit-YYYY-MM-DD.jsonl.gz` (UTC date — DST safe).
- Delete snapshots older than `--keep-days` (default 30).
- If the total size of the backup dir exceeds `--max-total-bytes`
  (default 500 MB), delete oldest first until under cap. The single
  newest snapshot is always kept.

### Exit codes

| Code | Meaning                                                       |
|-----:|---------------------------------------------------------------|
|   0  | Snapshot written (or graceful no-op if audit-log is missing)  |
|   1  | Lock contention — couldn't acquire audit-log lock in time     |
|   2  | Usage error                                                   |

### Safety notes

- Uses `FileLock(audit-log.jsonl.lock)` — same lock `audit_log.py` uses
  when writing. Blocks live writers during the copy and vice-versa.
  Concurrency tested with multiprocessing (see `test_backup_audit.py`).
- Atomic rename: snapshot is written to `*.tmp` then `os.replace()`d.
- Lock is released via context-manager `__exit__`, even on errors.
- UTC-only date math avoids DST ambiguity in `America/Sao_Paulo` etc.

## Running from cron

```cron
# daily 03:15 UTC snapshot
15 3 * * * /usr/bin/python3 /path/to/ceo-orchestration/.claude/scripts/backup-audit.py >> ~/.ceo-backup.log 2>&1
```
