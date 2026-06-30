# Wave 3 rollback drill spec — install/uninstall integrity

**Source:** PLAN-083 §5.3 row 1.9 (this deliverable) · §5.5 Wave 3 acceptance
**Consumed by:** sub-agents 3.1 through 3.5 (smoke-test YAML reports)
**Invariant proved:** uninstalling the framework leaves user work intact
and restores the pre-install state from the HMAC'd backup.

## Drill procedure (deterministic — 6 steps)

Each Wave 3 smoke-test sub-agent (3.1-3.5) executes these steps in its
designated Owner repo and records the outcome in the `rollback_*`
fields of its YAML smoke report (per PLAN-083 §5.5 schema).

### Step 1 — capture pre-install fingerprint

```bash
cd <repo-under-test>
PRE_FP=$(find . -type f -not -path './.git/*' -not -path './.claude/*' \
  | LC_ALL=C sort | xargs -I {} python3 -c "
import hashlib, sys
with open(sys.argv[1], 'rb') as f:
    print(hashlib.sha256(f.read()).hexdigest(), sys.argv[1])
" {} | sha256sum | awk '{print $1}')
echo "PRE_FP=$PRE_FP"
```

### Step 2 — install framework

```bash
bash /path/to/ceo-orchestration/scripts/install.sh . \
  --profile core,frontend \
  --no-gpg   # only if SOURCE_DIR HEAD not signed in test env
# Record install_exit_code in YAML smoke report
```

Assert: `[ -f .claude/.install-manifest.sha256 ]`

### Step 3 — make 1 trivial user edit to a NON-canonical file

```bash
# Append a comment to a user-authored file that exists OUTSIDE the manifest
echo "# user edit during rollback drill ($(date -u +%FT%TZ))" \
  >> .claude/my-user-notes.md   # file Owner creates; NOT in manifest
```

### Step 4 — uninstall (manifest-honoring)

```bash
bash /path/to/ceo-orchestration/scripts/uninstall.sh .
# Record rollback_exit_code in YAML smoke report
```

Expected stdout includes:
- `Removed:   <N>` where N >= 3 (framework files listed in manifest)
- `Preserved: 0` (no user-modified manifested files in this drill)
- `Manifest:  REMOVED`

### Step 5 — assert user edit + non-manifested files survived

```bash
test -f .claude/my-user-notes.md \
  || { echo "FAIL: user file destroyed"; exit 1; }
grep -q "rollback drill" .claude/my-user-notes.md \
  || { echo "FAIL: user edits lost"; exit 1; }
test ! -d .claude/hooks \
  || { echo "FAIL: framework hooks not removed"; exit 1; }
test ! -f .claude/.install-manifest.sha256 \
  || { echo "FAIL: manifest not cleaned up"; exit 1; }
```

### Step 6 — assert non-.claude/ tree fingerprint unchanged

```bash
POST_FP=$(find . -type f -not -path './.git/*' -not -path './.claude/*' \
  | LC_ALL=C sort | xargs -I {} python3 -c "
import hashlib, sys
with open(sys.argv[1], 'rb') as f:
    print(hashlib.sha256(f.read()).hexdigest(), sys.argv[1])
" {} | sha256sum | awk '{print $1}')
[ "$PRE_FP" = "$POST_FP" ] \
  || { echo "FAIL: files outside .claude/ changed"; exit 1; }
```

## YAML smoke report fields populated by this drill

```yaml
rollback_exit_code: <int>             # Step 4 exit code (expect 0)
rollback_user_file_preserved: <bool>  # Step 5 first assertion result
rollback_framework_removed: <bool>    # Step 5 third assertion result
rollback_manifest_cleaned: <bool>     # Step 5 fourth assertion result
rollback_outside_claude_unchanged: <bool>  # Step 6 result
rollback_drill_passed: <bool>         # all of the above true
```

## Pass criteria (per repo)

All 5 boolean fields above must be `true`. A single `false` is recorded
as a Wave 3 P0 blocker per PLAN-083 §13 risk register row 3.

## Edge cases the drill covers explicitly

1. **User edits manifested files** — separate scenario: edit a file
   inside `.claude/hooks/`, run uninstall, expect `Preserved: 1` and
   the file remains untouched. Optional sub-step for the trading-readonly
   repo (3.3) since that repo carries the highest cost of a destructive
   uninstall bug.

2. **HMAC'd backup tampering** — the uninstall produces
   `.claude.backup-uninstall-<ts>.tar.gz` with sibling `.hmac`. The drill
   may optionally invoke `uninstall.sh --restore <backup>` and assert
   restore succeeds when HMAC matches, fails (rc=4) when tampered.
   Covered by test T8 in the unit harness.

3. **Re-install after rollback** — after Step 5, running `install.sh .`
   again must succeed (fresh-install path) and produce a new manifest.
   Implicitly covered by Wave 3 second-pass sanity check.
