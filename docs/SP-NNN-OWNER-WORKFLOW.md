# SP-NNN Owner Workflow — 5 SKILL.md Amendments (Session 38 continuation)

> **Context:** the 5 SKILL.md amendments deferred from Session 38
> Wave B/C closure are now drafted as `SP-001` → `SP-005` under
> `.claude/proposals/`. Each is append-only (pure cross-link addition),
> content hand-authored, SHA-256 pre-computed. Owner needs to GPG-sign
> + apply each in a physical shell with local GPG key.

## The 5 proposals

| ID | Skill | Target plan | Purpose |
|----|-------|-------------|---------|
| SP-001 | `code-review-checklist` | PLAN-038 | §Artifact Paradox sub-section (fluency-bias rubric) |
| SP-002 | `security-and-auth` | PLAN-039 | §OWASP LLM Top 10 (2024) section (inference-path rubric) |
| SP-003 | `design-system-and-components` | PLAN-035 | §Reference Data (palettes + fonts YAMLs) |
| SP-004 | `accessibility-and-wcag` | PLAN-035 | §Reference Data — Chart Accessibility Grading |
| SP-005 | `ux-and-user-journeys` | PLAN-035 | §Reference Data — UX Guidelines (99 items) |

## Pre-flight

```bash
cd /Users/devuser/ceo-orchestration

# Verify your GPG key is reachable:
gpg --list-secret-keys --keyid-format=long

# Verify all 5 proposals exist:
ls -la .claude/proposals/SP-00[1-5]-*.md
```

## Step 1 — GPG-sign all 5 proposals (one-time)

```bash
cd /Users/devuser/ceo-orchestration

for sp in .claude/proposals/SP-00[1-5]-*.md; do
  if [ -f "$sp.asc" ]; then
    echo "SKIP (already signed): $sp"
    continue
  fi
  gpg --detach-sig --armor --output "$sp.asc" "$sp"
  echo "signed: $sp"
done

# Verify every proposal has a sibling .asc:
ls .claude/proposals/SP-00[1-5]-*.md.asc
```

## Step 2 — Apply to SHADOW (installs `SKILL.md.shadow.md` per skill)

```bash
cd /Users/devuser/ceo-orchestration

for sp in .claude/proposals/SP-00[1-5]-*.md; do
  base=$(basename "$sp" .md)
  pid=$(echo "$base" | sed 's/^\(SP-[0-9][0-9][0-9]\)-.*/\1/')
  echo "=== applying $pid ==="
  python3 .claude/scripts/skill-patch-apply.py \
    --proposal "$pid" \
    --signature "$sp.asc" \
    --confirm "I have read $pid"
done
```

Expected:
- Each call writes `<skill-dir>/SKILL.md.shadow.md`.
- The proposal file's `status:` flips from `draft` → `shadow`.
- The proposal gains `applied_at: <now>` + `approved_by: <fpr>`.

## Step 3 — Wait 7 days (shadow soak — ADR-031 contract)

The 7-day soak is MANDATORY. During the window:
- Shadow files are benchmarked against their real counterparts.
- Regressions surface via `audit-query.py` on `skill_patch_applied`
  events.

You can check soak readiness with:
```bash
python3 -c "
import datetime
from pathlib import Path
import re
for p in sorted(Path('.claude/proposals').glob('SP-00[1-5]-*.md')):
    text = p.read_text()
    m = re.search(r'proposed_at:\s*(\S+)', text)
    if not m: continue
    t = datetime.datetime.fromisoformat(m.group(1).rstrip('Z')).replace(tzinfo=datetime.timezone.utc)
    age = datetime.datetime.now(datetime.timezone.utc) - t
    ready = age.days >= 7
    print(f'{p.name}: age={age.days}d, ready_to_promote={ready}')
"
```

## Step 4 — Promote to real `SKILL.md` (after 7 days)

```bash
cd /Users/devuser/ceo-orchestration

for sp in .claude/proposals/SP-00[1-5]-*.md; do
  base=$(basename "$sp" .md)
  pid=$(echo "$base" | sed 's/^\(SP-[0-9][0-9][0-9]\)-.*/\1/')
  echo "=== promoting $pid ==="
  python3 .claude/scripts/skill-patch-apply.py \
    --proposal "$pid" \
    --signature "$sp.asc" \
    --confirm "I have read $pid" \
    --promote
done
```

Each promotion prints a commit message to stdout with a
`Skill-Patch-SHA: <hex>` trailer. Commit normally:

```bash
git add .claude/skills/core/code-review-checklist/SKILL.md \
        .claude/skills/core/security-and-auth/SKILL.md \
        .claude/skills/frontend/design-system-and-components/SKILL.md \
        .claude/skills/frontend/accessibility-and-wcag/SKILL.md \
        .claude/skills/frontend/ux-and-user-journeys/SKILL.md \
        .claude/proposals/SP-00*-*.md

git commit -m "$(cat <<'EOF'
feat(skill-patches): promote SP-001..SP-005 SKILL.md amendments

Post-7-day shadow soak. Cross-link amendments closing PLAN-038
Phase 2 + PLAN-039 Phase 1 + PLAN-035 Phase 2 from the Wave B/C
closure sweep.

Skill-Patch-SHA: <paste 5 trailers here, one per amendment>
EOF
)"
```

## Troubleshooting

- `gpg: can't open ...`: no GPG key installed → `gpg --gen-key`.
- `signature verification failed`: the `.asc` doesn't match the
  `.md` anymore (did you edit the proposal after signing?). Re-sign.
- `exit 3 (confirm phrase mismatch)`: the `--confirm` string must be
  EXACTLY `I have read SP-NNN` (case-sensitive, proposal ID).
- `exit 4 (proposed_at too recent)`: wait until 7 days elapsed since
  `proposed_at`.
- `exit 6 (shadow missing)`: you're calling `--promote` before Step 2
  wrote the shadow. Run Step 2 first.

## ceo-orchestration SKILL.md inventory sync

Separately deferred: `.claude/skills/core/ceo-orchestration/SKILL.md`
auto-generated inventory block is stale (missing `pre-plan-brainstorm`
entry + 19→20 core skill count). This is ALSO gated by ADR-031 —
needs an SP-006 proposal:

```bash
# Regenerate the inventory block:
bash .claude/scripts/generate-skill-inventory.sh > /tmp/inventory.md

# Create SP-006 by hand (or ask the CEO to re-run /tmp/gen_sp_proposals.py
# with a 6th entry for ceo-orchestration pointing at the new inventory).

# Once SP-006 exists, repeat Steps 1-4 above.
```

Alternatively, leave the inventory stale — the auto-generated block is
a nice-to-have, not load-bearing (the routing happens via team.md +
frontend-team.md SKILL MAPs, which are up-to-date).

## Compromise Response — key revocation + succession

> **PLAN-045 Wave 3 P0-11 closure.** PLAN-044 F-15-01 flagged the
> framework's bus-factor-1 + 4-day-old GPG key + no documented
> succession plan as an adopter-credibility P0. This section is the
> runbook.

### 1. Detecting compromise

You suspect a compromise if any of the following:

- An SP-NNN proposal lands in `.claude/proposals/` with a valid
  GPG signature that you did NOT produce.
- `skill-patch-apply.py --promote` succeeds for a proposal you do
  not recognise.
- `git log --show-signature` reveals signed commits you did not author.
- Your 1Password vault reports unauthorised access to the key backup.
- The machine holding the private key is physically lost/stolen.

Under any of these, treat the key as **compromised** and proceed to
§2 immediately. Err on the side of over-reaction: the cost of a false-
positive revocation is ~1 hour of reissue work; the cost of a missed
compromise is every SKILL.md amendment in flight.

### 2. Revocation procedure (do in a physical shell)

```bash
# 2.1 — generate a revocation certificate (if not already stashed).
# Preferred: revocation cert was generated at key creation time and
# is stored in 1Password under "ceo-orchestration GPG key rev cert".
# Fallback: generate fresh now (requires the private key + passphrase).
gpg --output /tmp/gpg-rev-00000000.asc --gen-revoke 0000000000000000000000000000000000000000

# 2.2 — import the revocation into your local keyring.
gpg --import /tmp/gpg-rev-00000000.asc

# 2.3 — export the revoked public key for publication.
gpg --armor --export 0000000000000000000000000000000000000000 > /tmp/00000000-revoked.asc
```

### 3. Publish the revocation

```bash
# 3.1 — append a revocation entry to the ledger (create the file if
# it doesn't exist). This is an append-only jsonl log tracked under
# canonical-edit sentinel (round-3 scope).
cd /Users/devuser/ceo-orchestration
cat >> .claude/gpg-revocations.jsonl <<EOF
{"ts": "$(date -u +%Y-%m-%dT%H:%M:%SZ)", "fpr": "0000000000000000000000000000000000000000", "reason": "<short reason slug>", "revoked_by": "@Canhada-Labs", "successor_fpr": "<pending>"}
EOF

# 3.2 — publish publicly (GitHub issue + keyservers).
gpg --send-keys 0000000000000000000000000000000000000000  # keyservers
# Also post /tmp/00000000-revoked.asc as a gist + link from the
# README.md until a successor key is active.
```

### 4. CI gate (automated rejection of signatures from revoked fprs)

`.github/workflows/validate.yml` runs a step that parses
`.claude/gpg-revocations.jsonl` and fails the PR if any unmerged
`.claude/proposals/*.md.asc` was signed by a revoked fpr. Until the
CI step ships (Wave 3 item), manual review catches this.

### 5. Successor key — bootstrap

Bus-factor > 1 is the long-term goal. For an interim successor key:

```bash
# 5.1 — generate the new key pair (ed25519, passphrase required).
gpg --full-generate-key
# Choose: 9) ECC + sign + cert; curve 25519; never expires (or 2y);
# real name: "<Your Name>"; email: <your@email>; passphrase from
# 1Password.

# 5.2 — note the new fpr.
gpg --list-secret-keys --keyid-format long | grep -A1 sec

# 5.3 — Append to .claude/skill-patch-signers.txt AND
#        .claude/sentinel-signers.txt. Both are under round-3 sentinel
# scope, so edit via the sentinel-approved Edit tool flow.

# 5.4 — Update .claude/gpg-revocations.jsonl to fill in successor_fpr
# on the revoked-key entry.

# 5.5 — Update docs/rotation-log.md with the key transition event.
```

### 6. Re-sign in-flight SP-NNN proposals

Every SP-NNN proposal in `.claude/proposals/` that was signed by the
revoked key must be re-signed by the successor OR abandoned:

```bash
# For each SP-NNN.asc signed by the revoked key:
rm .claude/proposals/SP-NNN-<name>.md.asc
gpg --armor --detach-sign \
    --local-user <successor-fpr> \
    --output .claude/proposals/SP-NNN-<name>.md.asc \
    .claude/proposals/SP-NNN-<name>.md
```

Shadow-applied proposals (status=shadow) that have not yet promoted
can stay in shadow as-is; promotion after the 7-day soak still works
because the shadow file already exists on disk. But the provenance
ledger (frontmatter `approved_by:` field) carries the revoked fpr —
document this in the next promotion's commit message.

### 7. Adopter disclosure

If you operate a downstream framework using ceo-orchestration, post
a disclosure to your adopter channel within **24 hours** of the
revocation:

```markdown
## Security notice — ceo-orchestration upstream GPG key revoked

On <date>, the upstream ceo-orchestration Owner GPG key
0000000000000000000000000000000000000000 was revoked due to
<reason>. Any skill imports or SP-NNN proposals you have applied
since <date-of-last-known-clean-state> should be audited.

Successor key: <fpr> (rotation entry in docs/rotation-log.md).

No confirmed downstream impact at this time / <describe known impact>.

Recommended action:
1. `gpg --refresh-keys` to pick up the revocation.
2. `gpg --verify` every .asc in .claude/proposals/ — any GOODSIG from
   the revoked fpr triggers manual review.
3. Re-pin any imported skill commits to versions signed under the
   successor key.
```

### 8. Long-term — multi-signer (2-of-N)

Current state: single-signer. PLAN-045 Wave 4 + Sprint 30+ will design
2-of-N signing: any SP-NNN proposal requires signatures from 2 of the
N authorised signers. ADR-031 §Open questions #4 tracks the work.

This §8 is forward-looking — the current runbook (§2-§7) operates at
bus-factor-1 and is the best we have today. Adopters who need
bus-factor > 1 today should:

1. Fork the framework + maintain their own signer allowlist.
2. Upstream SP-NNN proposals reviewed by your team before rebasing.
3. Pin to `v1.7.0` (GA, post-PLAN-045) — NOT `v1.7.0-rc.1` which
   shipped pre-audit per CHANGELOG §Release narrative.

### 9. Contact

- Owner channel: `<owner-email>`
- Repo issues: open a security issue at
  `github.com/Canhada-Labs/ceo-orchestration/security/advisories/new`.
- Emergency: use the 1Password shared vault "ceo-orchestration
  emergency contact" entry if you're an authorised downstream
  operator.
