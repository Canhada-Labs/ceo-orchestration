# Disaster Recovery

> Procedures to restore framework state after corruption, accidental
> deletion, or systemic loss. Pair with `INCIDENT-RESPONSE.md` (which
> covers active intrusions) and `BACKUP procedures` in
> `docs/CHEAT-SHEET.md` (which covers the snapshot tooling).

## What's at stake

The framework relies on three categories of state:

| State | Location | Recovery source |
|-------|----------|------------------|
| **Audit log** | `~/.claude/projects/<slug>/audit-log.jsonl` (out-of-repo) | `ceo-backup.sh` snapshots; rotated archives `audit-log-YYYY-MM.jsonl` |
| **Auto-memory** | `~/.claude/projects/<slug>/memory/*.md` (out-of-repo) | `ceo-backup.sh` snapshots; mostly low-churn |
| **Plans + skills + ADRs** | In-repo under `.claude/` | `git` history (authoritative) |
| **Sentinels** | In-repo at `.claude/plans/PLAN-NNN/architect/round-N/approved.md` | `git` history; signed via GPG (Owner) |
| **Native agents** | In-repo at `.claude/agents/<slug>.md` | `git` history; framework upgrade restores canonical-5 |
| **Settings** | `.claude/settings.json` (in-repo) | `git` history; rebuild via `bash scripts/install.sh .` |
| **Adopter overrides** | Same paths as above (in-repo) | `git` history; preserved by `upgrade.sh` per ADR-052 §Adopter override |

**Recovery objectives:**

| Objective | Target |
|-----------|--------|
| **RPO** (Recovery Point Objective) — max data loss | ≤ 24 hours (default daily backup); ≤ 1 hour if you increase cadence |
| **RTO** (Recovery Time Objective) — time to restore | ≤ 1 hour (manual; well-rehearsed) |

Adopters with stricter requirements should mirror the audit log to
WORM storage (see `INCIDENT-RESPONSE.md` Scenario 2 §Honest
limitation).

---

## Scenario A — Audit log corrupted (file unreadable)

### Symptoms

- `python3 .claude/scripts/audit-query.py recent` errors with
  `JSONDecodeError` on a specific line.
- File ends mid-line (truncated; SIGKILL during write).
- File has gaps (lines missing in `ts` sequence).
- `audit_log.py` reports errors in `audit-log.errors`.

### Recovery

1. **Quarantine the broken file**:
   ```bash
   AUDIT=~/.claude/projects/<your-slug>/audit-log.jsonl
   mv "$AUDIT" "$AUDIT.broken.$(date +%Y%m%dT%H%M%SZ)"
   ```
2. **Restore from latest backup**:
   ```bash
   bash .claude/scripts/ceo-restore.sh \
     ~/.ceo-backups/<slug>/<latest>.tar.gz \
     --dry-run                       # verify what will land
   bash .claude/scripts/ceo-restore.sh \
     ~/.ceo-backups/<slug>/<latest>.tar.gz \
     --apply                         # commit
   ```
3. **Salvage trailing entries** from the broken file (best-effort):
   ```bash
   # Take only valid JSON lines and append to restored audit log
   python3 -c "
   import json
   for line in open('$AUDIT.broken.$(date +%Y%m%dT%H%M%SZ)'):
       try:
           json.loads(line)
           print(line, end='')
       except Exception:
           continue
   " >> "$AUDIT"
   ```
4. **Verify**:
   ```bash
   python3 .claude/scripts/audit-query.py recent --limit 20
   ```
5. **Investigate root cause** — was it disk pressure, a hook bug,
   or operator action? See `INCIDENT-RESPONSE.md` Scenario 2 if
   intentional tampering is suspected.

### Acceptance

- `audit-query.py recent` succeeds.
- Last 24h of events visible.
- `audit-log.errors` not growing.

---

## Scenario B — Plan state corrupted (invalid YAML frontmatter)

### Symptoms

- `bash .claude/scripts/validate-governance.sh` errors on a plan
  file: "missing required field" / "YAML parse error".
- `check_plan_edit.py` rejects edits with `transition_legal: false`.
- `/status` slash command errors when reading plan frontmatter.

### Recovery

1. **Identify the broken plan**:
   ```bash
   for p in .claude/plans/PLAN-*.md; do
     python3 -c "
     import sys, re
     content = open('$p').read()
     m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
     if not m: print(f'{p!r}: no frontmatter')
     " 2>&1 | grep -v "^$"
   done
   ```
2. **Diff against last-known-good**:
   ```bash
   git log --oneline -- .claude/plans/<broken-plan>.md | head -10
   git diff <known-good-sha> HEAD -- .claude/plans/<broken-plan>.md
   ```
3. **Restore the frontmatter section only** (preserve body):
   ```bash
   git show <known-good-sha>:.claude/plans/<broken-plan>.md | \
     awk '/^---$/{c++} c==2{exit} {print}' > /tmp/restored-frontmatter.md

   # Manually paste over the broken frontmatter
   ```
4. **Or restore the full file**:
   ```bash
   git checkout <known-good-sha> -- .claude/plans/<broken-plan>.md
   ```
5. **Validate**:
   ```bash
   bash .claude/scripts/validate-governance.sh
   ```

### Acceptance

- `validate-governance.sh` PASS.
- `/status` reads the plan without error.
- Plan body content preserved (frontmatter-only fix didn't
  collateral-damage the body).

---

## Scenario C — Skill corpus tampered or corrupted

### Symptoms

- `bash .claude/scripts/check-skill-health.sh` reports stale or
  missing skills.
- `validate-governance.sh` reports skill referenced in `team.md`
  but missing on disk.
- `check_skill_reference_read.py` rejects spawn with
  `reference_postread_mismatch` (PostToolUse hook detected SHA
  drift on the SKILL.md sub-agent Read).
- A skill file changed unexpectedly (compare `git status`).

### Recovery

1. **Snapshot current state** (before any restore):
   ```bash
   tar czf ~/skill-corpus-pre-restore-$(date +%Y%m%dT%H%M%SZ).tar.gz \
     .claude/skills/
   ```
2. **Identify which skills changed**:
   ```bash
   git status -s .claude/skills/
   git log --since="7 days ago" --name-only -- .claude/skills/ | sort -u
   ```
3. **Decide restore strategy**:
   - **Single skill drift**: `git checkout HEAD -- .claude/skills/<slug>/`
   - **Multiple skills**: `git checkout <last-known-good-sha> -- .claude/skills/`
   - **Total loss / never-committed adopter skills**: re-install
     base skills via framework `bash scripts/install.sh .` (preserves adopter customizations
     under `domains/<your-domain>/`)
4. **Re-validate**:
   ```bash
   bash .claude/scripts/validate-governance.sh
   bash .claude/scripts/check-skill-health.sh
   ```
5. **If the SHA pin in a `## SKILL REFERENCE` sentinel** referenced
   the broken hash, regenerate native agent dispatch:
   ```bash
   python3 .claude/scripts/generate-dispatch.py
   ```

### Acceptance

- `validate-governance.sh` reports `Skills referenced: N / N`
  (no missing).
- `check-skill-health.sh` clean.
- Native agent dispatch regenerated; no SHA-pin mismatches.

---

## Scenario D — Complete framework state loss

### Symptoms

- `~/.claude/projects/<slug>/` directory deleted.
- Project repo intact but `.claude/` subdir wiped.
- New laptop / new machine with project clone but no out-of-repo
  state.

### Recovery

1. **Re-bootstrap audit log + memory dirs** from the latest backup:
   ```bash
   bash .claude/scripts/ceo-restore.sh \
     ~/.ceo-backups/<slug>/<latest>.tar.gz \
     --dry-run

   bash .claude/scripts/ceo-restore.sh \
     ~/.ceo-backups/<slug>/<latest>.tar.gz \
     --apply
   ```
2. **If no backup** (worst case): the audit log is non-recoverable.
   Recreate the audit dir empty:
   ```bash
   mkdir -p ~/.claude/projects/<your-slug>/
   ```
   Future spawns will append to a fresh log. Memory dir starts
   empty; framework continues to function.
3. **Re-bootstrap settings + hooks** from the repo:
   ```bash
   cd /path/to/your/project
   bash scripts/install.sh .
   ```
   This is idempotent — it will not overwrite adopter customizations
   in `team.md`, `frontend-team.md`, `CLAUDE.md`.
4. **Verify**:
   ```bash
   bash .claude/scripts/validate-governance.sh
   python3 .claude/scripts/ceo-health.py
   ```
5. **Set up backups going forward** (it shouldn't be a near miss
   twice):
   ```bash
   bash .claude/scripts/ceo-backup.sh
   # Schedule via cron — see "Backup cadence" below
   ```

### Acceptance

- `ceo-health.py` exits 0.
- `validate-governance.sh` PASS.
- New spawns successfully append to audit log.

---

## Scenario E — Git history rewrite / force push

### Symptoms

- `git log` shows different commit SHAs than expected.
- `git status` reports diverged from origin.
- A canonical-edit sentinel that you remember authoring is missing.
- A skill file at a known-good SHA is now different.

### Recovery

1. **Stop all writes** — do not commit anything until reconciled.
2. **Examine reflog** (local recovery first):
   ```bash
   git reflog | head -30
   ```
   Find the commit you remember. If present, you can recover the
   tree from there.
3. **Check forks/clones** for the missing history:
   ```bash
   # On a colleague's clone
   git log --all --oneline | head -50
   ```
4. **Coordinate a re-push** if the rewrite was unauthorized:
   - Identify who pushed (via `git log` author + push event in
     GitHub UI).
   - If unauthorized, treat as SEV-1 supply-chain incident; see
     `INCIDENT-RESPONSE.md`.
5. **If authorized but accidental** (e.g. someone ran `git push
   --force`), restore the missing commits from reflog or
   colleague clone via:
   ```bash
   git reset --hard <recovered-sha>
   git push origin main --force-with-lease  # ONLY after team coordination
   ```

### Acceptance

- `git log` matches expected history.
- All canonical files intact.
- All sentinels intact.

**Prevention:** enable branch protection per
[`docs/BRANCH-PROTECTION.md`](BRANCH-PROTECTION.md). The framework
ships the workflows; the Owner flips the GitHub setting. The block
list includes "force-push to protected branch".

---

## Backup cadence (recommended)

| Component | Cadence | Method |
|-----------|---------|--------|
| `audit-log.jsonl` + `memory/` + `agent-metrics.md` | Daily | `bash .claude/scripts/ceo-backup.sh` (cron) |
| Repo (`.claude/` + plans + ADRs + skills) | Per commit | `git push` (already daily-ish) |
| Settings.json + sentinels | Per change | `git commit` of the change |
| Off-site mirror | Weekly | `aws s3 sync` / `gdrive sync` of `~/.ceo-backups/` |

### Set up daily cron

```bash
# Edit crontab
crontab -e

# Add — daily at 03:00 local
0 3 * * * /bin/bash /Users/<you>/path/to/project/.claude/scripts/ceo-backup.sh > /dev/null 2>&1
```

### Rotation policy (default)

`ceo-backup.sh` keeps:
- Last **7** daily backups
- Last **4** weekly backups (Sundays)
- Last **3** monthly backups (1st of month)

Older backups are pruned automatically. Override via flags
documented in `bash .claude/scripts/ceo-backup.sh --help`.

### Off-site mirror (recommended for production adopters)

The default backup location is `~/.ceo-backups/<slug>/`. For
disaster scenarios that take out the laptop entirely, mirror this
directory to off-site storage:

```bash
# Example: AWS S3 with versioning enabled
aws s3 sync ~/.ceo-backups/ s3://your-bucket/ceo-backups/ \
  --storage-class STANDARD_IA

# Example: Google Drive via rclone
rclone sync ~/.ceo-backups/ remote:ceo-backups/
```

Wire that into your existing personal backup tooling — Time
Machine, Backblaze, Borg, restic, etc. The framework doesn't ship
its own off-site mirror; that's a personal-environment decision.

---

## Recovery validation drill

Run quarterly. Total time ~30 minutes.

1. **Pick a recent backup**:
   ```bash
   ls -t ~/.ceo-backups/<slug>/ | head -1
   ```
2. **Restore to a temp dir** (does not affect live state):
   ```bash
   mkdir -p /tmp/dr-test
   tar xzf ~/.ceo-backups/<slug>/<latest>.tar.gz -C /tmp/dr-test/
   ls -la /tmp/dr-test/
   ```
3. **Verify content integrity**:
   ```bash
   python3 .claude/scripts/audit-query.py recent --limit 5 \
     --audit-log /tmp/dr-test/audit-log.jsonl
   ```
4. **Run `ceo-restore.sh --dry-run`** against current state:
   ```bash
   bash .claude/scripts/ceo-restore.sh \
     ~/.ceo-backups/<slug>/<latest>.tar.gz \
     --dry-run
   ```
5. **Confirm rotation** — verify older backups were pruned per
   policy:
   ```bash
   ls ~/.ceo-backups/<slug>/ | wc -l
   ```

If any step fails, that's a backup-tooling defect — file an issue
with the failing step.

---

## What the framework does NOT recover

Be honest about scope:

- **Anthropic conversation history.** The framework cannot replay
  past Claude Code conversations beyond what's captured in audit
  log + memory. If you lose your Claude Code chat history, that's
  upstream territory.
- **Lost API tokens.** If you rotated the wrong key and locked
  yourself out, that's an Anthropic account recovery issue.
- **Production data in your application.** The framework recovers
  framework state, not your application's database, user data, or
  business state. That's your responsibility per your stack.
- **Files outside `.claude/` or the audit/memory dirs.** Out of
  scope; use your normal backup discipline (Time Machine, etc.).

---

## References

- `docs/CHEAT-SHEET.md` — backup + restore command summary
- `docs/INCIDENT-RESPONSE.md` — when corruption is suspected
  intentional
- `docs/UPGRADE-PROCEDURE.md` — version bumps that may affect
  state schema
- `SPEC/v1/audit-log.schema.md` — audit log format (additive
  evolution)
- `bash .claude/scripts/ceo-backup.sh --help` — backup CLI
- `bash .claude/scripts/ceo-restore.sh --help` — restore CLI

Last reviewed: 2026-04-18 (Session 33 / PLAN-022 Phase 2).
