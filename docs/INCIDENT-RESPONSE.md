# Incident Response Runbook

> When something looks wrong, do these things in this order. Each
> scenario lists detection signals, the **first 5 minutes**, the
> full investigation, and the post-mortem template. Designed for
> read-on-pager urgency — keep open in a tab.

## Severity classification

Match observed signals to a tier before acting. Tier dictates urgency
and who to involve.

| Tier | Examples | First action |
|------|----------|--------------|
| **SEV-1** | Arbitration kernel bypass; credential exfiltration; production deploy on bad commit | Stop all sessions; preserve evidence; contact Owner immediately |
| **SEV-2** | Suspected prompt injection succeeded; audit-log tampering; canonical-edit slipped | Isolate the affected session; preserve audit-log segment; investigate within 24h |
| **SEV-3** | Hook fail-open under malformed input; non-canonical drift; benchmark regression | Document; investigate during business hours |
| **SEV-4** | Doc drift; misleading error message; UX rough edge | File issue; fix in next sprint |

The four scenarios below are the SEV-1 / SEV-2 cases that warrant a
runbook. SEV-3+ go to GitHub issues.

---

## Scenario 1 — Suspected prompt injection (SEV-2)

### Detection signals

- `injection_flag` events appearing in audit log:
  ```bash
  python3 .claude/scripts/audit-query.py raw --action injection_flag --limit 20
  ```
  per `SPEC/v1/audit-log.schema.md` v2.1 (ADR-011), each flag carries
  `family_counts` (which injection families matched) and
  `triggered_by_tool` (which tool surfaced the payload).
- Sub-agent producing output that ignores the spawn task and instead
  follows instructions visibly embedded in a Read result.
- Skill/SKILL.md or external content referencing strings like
  "ignore previous instructions", "you are now", system-prompt
  injection markers caught by `scan-injection.py`.

### First 5 minutes

1. **Stop the affected Claude Code session.** Do not let the
   sub-agent continue; the next turn could exfiltrate secrets
   surfaced by the injection.
   ```bash
   # In the Claude Code window: Ctrl+C, then close the session
   ```
2. **Preserve the audit log** for that session:
   ```bash
   AUDIT=~/.claude/projects/<your-slug>/audit-log.jsonl
   cp "$AUDIT" "$AUDIT.incident.$(date +%Y%m%dT%H%M%SZ).bak"
   ```
3. **Snapshot the affected files**. If the injection came from a
   read of a specific file (skill, plan, external doc):
   ```bash
   sha256sum <suspect-file> >> ~/incident-evidence.txt
   cp <suspect-file> ~/incident-evidence/<suspect-file>.snapshot
   ```
4. **Check whether credentials were touched**. Look for any tool
   calls that read secrets, env files, or external services:
   ```bash
   python3 .claude/scripts/audit-query.py raw \
     --action live_adapter_call_succeeded --since 1h
   ```
5. **Notify the Owner**. SEV-2 always escalates.

### Full investigation

1. Run the injection scanner against the suspect file(s):
   ```bash
   python3 .claude/scripts/scan-injection.py <file-or-directory>
   ```
   Output identifies which family triggered (`role_overwrite`,
   `instruction_override`, `system_marker`, `data_exfiltration`,
   etc.) per the documented family taxonomy.
2. Review `injection_flag` events from the past 7 days for pattern
   detection:
   ```bash
   python3 .claude/scripts/audit-query.py raw \
     --action injection_flag --since 7d --format json | \
     jq '.[] | {ts, source, triggered_by_tool, family_counts}'
   ```
3. If the injection succeeded (sub-agent acted on injected
   instructions), determine the blast radius:
   - Did it issue any Write / Edit calls? Check `git status` for
     unexpected changes.
   - Did it issue any Bash commands? Check shell history for the
     session.
   - Did it call any live adapter (HTTP)? Check
     `live_adapter_call_succeeded` events for unexpected providers
     or destinations.
4. If credentials were potentially exposed (Bash commands echoing
   secrets, live adapters with credentials in URLs), **rotate
   them**. See `docs/rotation-log.md` for the rotation log format.
5. **Quarantine the source** — if a third-party skill or external
   doc was the vector, remove it from the project until reviewed
   and re-import via the signed channel (`/squad-install` if from a
   marketplace bundle).

### Post-mortem template

File at `.claude/plans/PLAN-NNN/incidents/INC-<date>-<slug>.md`:

```markdown
# Incident INC-<date>-<slug>

**Severity:** SEV-2
**Classification:** prompt-injection
**Detection time:** <ISO 8601>
**Resolution time:** <ISO 8601>
**Owner:** <name>

## Summary
<1-paragraph plain-English description>

## Detection
- Signal that fired
- How long between attack surface and detection

## Root cause
- Vector (which file / which skill / which external source)
- Family (which injection technique succeeded; reference scan-injection.py family list)
- Why our defenses failed (or correctly fired late)

## Impact
- Files modified
- Credentials potentially exposed (rotated? Y/N)
- Audit log evidence preserved (path)

## Containment + remediation
- Steps taken in first 5 min
- Steps taken in investigation
- Permanent fix (skill rewrite / scan-injection rule update / hook hardening / ADR amendment)

## Defense gaps
- What we should have caught earlier
- ADR-NNN to file (if defense gap warrants new mitigation)

## Timeline
- T-0: <event>
- T+5m: <event>
- ...
```

---

## Scenario 2 — Suspected audit-log tampering (SEV-2)

### Detection signals

- `audit-log.jsonl` file size shrinks unexpectedly.
- Gaps in `ts` sequence (events expected but missing — use
  `python3 .claude/scripts/audit-query.py freshness` for gap
  detection).
- Off-disk backup compare shows divergence:
  ```bash
  diff <(sha256sum ~/.claude/projects/<slug>/audit-log.jsonl) \
       <(cat ~/.ceo-backups/<slug>/last-audit-sha256.txt)
  ```
- Hook `audit_log.py` reports `audit-log.errors` entries:
  ```bash
  cat ~/.claude/projects/<slug>/audit-log.errors
  ```
- An `agent_spawn` event you remember executing is missing.

### First 5 minutes

1. **Snapshot current audit-log.jsonl AND audit-key TOGETHER**
   (before any further writes). The HMAC chain forensics depend on
   the pair — a tampered log without its matching key is unverifiable:
   ```bash
   AUDIT=~/.claude/projects/<your-slug>/audit-log.jsonl
   KEY=~/.claude/projects/<your-slug>/audit-key
   SIDECAR=~/.claude/projects/<your-slug>/audit-log.last-hmac
   STAMP=$(date +%Y%m%dT%H%M%SZ)
   cp "$AUDIT" "$AUDIT.tamper-incident.$STAMP.bak"
   cp "$KEY" "$KEY.tamper-incident.$STAMP.bak" 2>/dev/null || true
   cp "$SIDECAR" "$SIDECAR.tamper-incident.$STAMP.bak" 2>/dev/null || true
   ```
2. **Run the HMAC verifier** to get an authoritative tamper report
   (PLAN-023 Phase B / ADR-055):
   ```bash
   python3 .claude/scripts/audit-verify-chain.py \
     --log-file "$AUDIT" --verbose --json > /tmp/verify-chain.$STAMP.json 2>&1
   echo "exit=$?"
   ```
   Exit 0 → chain intact (log unchanged or tamper happened outside
   the HMAC-covered zone); 1 → tamper detected (line-level report in
   stderr and structured JSON); 2 → key missing; 3 → malformed JSONL;
   4 → permission error.
3. **Stop all Claude Code sessions**. Concurrent writes mask the
   tampering forensics.
4. **Compare with the most recent backup** if available:
   ```bash
   bash .claude/scripts/ceo-backup.sh   # if you don't have one yet
   ls -lt ~/.ceo-backups/<slug>/
   ```
5. **Check filesystem permissions** on the audit dir + key:
   ```bash
   ls -la ~/.claude/projects/<slug>/
   stat ~/.claude/projects/<slug>/audit-log.jsonl
   stat ~/.claude/projects/<slug>/audit-key
   ```
   The key MUST be 0600 owned by the operator. Any deviation is its
   own incident (possible key compromise).
6. **Notify the Owner**.

### HMAC chain semantics — detection vs prevention

The HMAC chain (`hmac = hmac_sha256(key, prev_hmac ||
canonical_json(entry_sans_hmac))`) is **tamper-evident**, not
tamper-proof. It defends:

- **Forgery** — bit flip in any covered field breaks the chain forward.
- **Reorder** — swapping entries produces a different HMAC.
- **Deletion of interior entries** — next-entry HMAC verification fails.
- **Transition-rule violation** — hmac-bearing entry followed by
  hmac-less entry (one-way rule).

It does **NOT** defend:

- **Tail truncation** — attacker deletes the last N entries; head
  verifies clean. Mitigation path (post-v1.6.0): external OTEL anchor.
- **Key theft** — attacker with `$HOME` read-access can forge.
- **Rollback** — attacker restores an older (log, key) snapshot; chain
  verifies against old key.
- **Log + key co-deletion** — deny-of-forensics.

For full tamper-proof forensics mirror the audit log to immutable
storage (S3 Object Lock, Azure Immutable Blob) via the OTEL exporter.
See ADR-055 §Threat Model §Out-of-scope for the complete residual list.

### Full investigation

1. **Identify what's missing.** Replay your memory of the session
   against the audit log:
   ```bash
   python3 .claude/scripts/audit-query.py recent --limit 100
   ```
   Cross-check against your shell history (`history | tail -200`)
   for spawns you remember running.
2. **Identify what was added.** Look for events with timestamps
   before the previous backup:
   ```bash
   python3 .claude/scripts/audit-query.py raw --since 7d --format json | \
     jq '.[].ts' | sort | uniq -c
   ```
3. **Determine the access vector.** Was the file modified by:
   - A user-space process? Check shell history + `lsof` on the file.
   - A Claude Code hook bug? Check `audit-log.errors` for ERROR
     entries from `audit_log.py`.
   - An external attacker? Check filesystem-level audit (auditd on
     Linux, fs_usage on macOS) if available.
4. **Restore from backup** if tampering confirmed:
   ```bash
   bash .claude/scripts/ceo-restore.sh ~/.ceo-backups/<slug>/<latest>.tar.gz --dry-run
   bash .claude/scripts/ceo-restore.sh ~/.ceo-backups/<slug>/<latest>.tar.gz --apply
   ```
5. **Increase backup cadence** going forward (e.g. cron every hour
   instead of daily) until the access vector is identified.

### Post-mortem

Same template as Scenario 1, classification `audit-log-tampering`.
Add an explicit section: "Did we have backups? Were they
sufficient?".

---

## Scenario 3 — Suspected skill poisoning (SEV-2)

### Detection signals

- A skill `.md` file modified outside the `SP-NNN` skill-patch
  chain (per ADR-031). Verify with:
  ```bash
  git log --since="7 days ago" -- .claude/skills/
  ```
- An agent spawned with a skill exhibits behavior contradicting the
  skill's documented checklist (e.g. security-engineer skipping
  CSRF check).
- `scan-injection.py` flags content in a SKILL.md.
- `validate-governance.sh` reports unknown skill, content drift, or
  unexpected SKILL.md frontmatter.
- `check-skill-health.sh` reports stale `src/...` references — not
  always poisoning, but a signal worth investigating.

### First 5 minutes

1. **Identify which skill** and which file:
   ```bash
   git diff HEAD~1 -- .claude/skills/
   ```
2. **Check the change provenance** — was it via `SP-NNN`?
   ```bash
   git log --all --grep="SP-" -- .claude/skills/<skill-slug>/
   ```
3. **Snapshot current state**:
   ```bash
   tar czf ~/incident-evidence/skill-<slug>-snapshot.tar.gz \
     .claude/skills/<slug>/
   ```
4. **Revert to last known-good** via git:
   ```bash
   # Find the last known-good commit
   git log --oneline --all -- .claude/skills/<slug>/SKILL.md | head -5

   # Revert
   git checkout <known-good-sha> -- .claude/skills/<slug>/SKILL.md
   ```
5. **Stop spawns of that skill** until cleared.

### Full investigation

1. **Diff the suspect skill** against its blessed version:
   ```bash
   git diff <last-known-good-sha> HEAD -- .claude/skills/<slug>/SKILL.md
   ```
2. **Run the injection scanner** on the modified content:
   ```bash
   python3 .claude/scripts/scan-injection.py .claude/skills/<slug>/
   ```
3. **Check for `SP-NNN` chain compliance**. Skill content edits
   require an `SP-NNN` proposal signed by the Owner per ADR-031.
   If the change has no `SP-NNN` reference, that itself is the
   issue.
4. **Audit recent spawns** that loaded the suspect skill:
   ```bash
   python3 .claude/scripts/audit-query.py raw --action agent_spawn --since 7d --format json | \
     jq --arg s "<slug>" '.[] | select(.skill == $s)'
   ```
   Review their outputs (in your conversation history or saved
   transcripts) for behavior consistent with poisoning.
5. **Restore the blessed version** via the `SP-NNN` chain if a
   legitimate change is desired:
   ```bash
   python3 .claude/scripts/skill-patch-propose.py <slug>
   ```

### Post-mortem

Same template, classification `skill-poisoning`. Document whether
`check_canonical_edit.py` should have caught this (skills under
canonical guard) and whether the sentinel was correctly enforced.

---

## Scenario 4 — Governance bypass suspected (SEV-2)

### Detection signals

- A spawn happened without `## SKILL CONTENT` or `## SKILL REFERENCE`
  but the audit log shows `has_profile: true`.
- A canonical path edited outside an approved sentinel (compare
  recent commits against `.claude/plans/PLAN-NNN/.../approved.md`
  sentinel scope).
- `validate-governance.sh` exits non-zero in CI but locally passes —
  possible env divergence hiding a bug.
- A `veto_triggered` event has `decision: "block"` but the operation
  visibly went through anyway.

### First 5 minutes

1. **Capture environment**:
   ```bash
   env | grep -E '^CEO_' > ~/incident-evidence/ceo-env.txt
   echo "---" >> ~/incident-evidence/ceo-env.txt
   cat .claude/settings.json >> ~/incident-evidence/ceo-env.txt
   ```
2. **Verify hooks are wired**:
   ```bash
   for h in .claude/hooks/check_*.py .claude/hooks/audit_log.py; do
     ls -la "$h"
   done
   bash .claude/hooks/_python-hook.sh --version 2>&1 | head -3
   ```
3. **Verify settings.json is parseable** and references the right
   hooks:
   ```bash
   python3 -c "import json; print(json.dumps(json.load(open('.claude/settings.json')), indent=2))"
   ```
4. **Restart Claude Code** completely (`pkill -f claude || true; claude`).
5. **Re-run** the operation that bypassed and check the audit log.

### Full investigation

1. **Reproduce in isolation**. Open a fresh Claude Code session with
   only the suspect operation.
2. **Compare HOOK output**. The hook returns `{"decision": "..."}`
   on stdout. If `block` returned but operation proceeded, the hook
   integration is broken. Check Claude Code's stderr / debug log.
3. **Check for kernel override**:
   ```bash
   echo "CEO_KERNEL_OVERRIDE=$CEO_KERNEL_OVERRIDE"
   echo "CEO_KERNEL_OVERRIDE_ACK=$CEO_KERNEL_OVERRIDE_ACK"
   ```
   If either is set in the operator's shell, that explains the
   bypass — the kernel override is Owner-only and audit-logged.
4. **Check sentinel coverage** for canonical edits:
   ```bash
   ls .claude/plans/PLAN-*/architect/round-*/approved.md 2>/dev/null
   ```
   The most recent sentinel determines what's currently bypass-able.
5. **File an SEV-1 if the bypass is mechanical** (i.e. not operator
   error). Hook integration failure means EVERY governance
   guarantee is at risk.

### Post-mortem

Same template, classification `governance-bypass`. Add: "How would
we detect this same bypass automatically next time?" and propose an
ADR if a structural defense is needed.

---

## Ending an incident — three-condition close

> Doctrine source of record: `.claude/skills/core/incident-management/SKILL.md`
> §"Ending an Incident". This runbook mirrors it; if the two ever diverge,
> the SKILL is canonical.

Recovery is a **state, not a vibe**. Do not close on "metrics look better"
alone. All **three** conditions are required before the IC declares
"resolved":

1. **Symptoms gone in observed metrics.** Whatever the page paged on —
   error rate, latency p99, queue depth — back inside SLO with margin.
2. **User-facing verification.** Someone actually exercises the broken
   surface (the endpoint or the flow) and confirms it works. A `200 OK`
   on a dashboard is not sufficient.
3. **Sustained observation window with no fresh alerts.** SEV-1 = 30 min;
   SEV-2 = 15 min; SEV-3 = 5 min. If anything pops in the window, the
   window restarts.

If any of the three is missing, the incident is **still open**. (For the
framework's security scenarios above, condition 2 means the relevant
verifier exits clean: e.g. `audit-verify-chain.py` exit 0 for the
audit-tampering scenario, `scan-injection.py` clean for prompt-injection.)

## Universal post-incident actions

After any incident, regardless of scenario:

0. **Hold the post-incident review (PIR) within 48 hours** of resolution,
   while context is still recoverable — blame-free, framed in terms of
   system gaps, with action items tagged `detect` / `prevent` / `recover`
   and each carrying an owner + due date. Use the post-mortem template in
   the scenario above; the SKILL's §"Post-Incident Review" lists the full
   required sections. A repeat incident whose prior action item is still
   `open` is itself a finding in the new review.
1. **File a `lesson_write` event** via the lessons system to capture
   the failure mode:
   ```bash
   python3 .claude/scripts/lessons.py write \
     --archetype <relevant> \
     --trigger incident-response \
     --summary "<1-line takeaway>"
   ```
2. **Update [`docs/HONEST-LIMITATIONS.md`](HONEST-LIMITATIONS.md)** if
   the incident exposed a structural gap not previously documented.
3. **Update [`docs/threat-model.md`](threat-model.md)** if the
   incident was novel — add a scenario, update residual risks, or
   flag a primary residual.
4. **Open a PR** for any code/skill/doc fix; tag with
   `incident:<scenario-slug>` label.
5. **Schedule a follow-up** for 30 days out to verify the fix held.

## Drills (aspirational — not yet executed)

> **PLAN-113 W7-OPS honesty note (2026-05-25):** No drill has been executed
> in this project to date. The schedule below is aspirational. Until a drill
> is completed, treat this section as a *design spec*, not a *verified
> procedure*. When the first drill runs, record it in
> `docs/incident-drill-log.md` (create that file on first use).

**Recommended cadence:** quarterly when the framework has active adopters;
at minimum before the first production deploy of any adopter project.

1. **Tabletop**: walk through Scenario 1 with synthetic
   `injection_flag` events injected into a temp audit log. Time the
   first-5-min response.
2. **Backup restore drill**: actually run `ceo-restore.sh
   --dry-run` on a recent backup. Verify the dry-run output matches
   expected paths.
3. **Hook bypass attempt**: try to spawn an agent without skill
   content; verify the hook blocks. Try with `CEO_SOTA_DISABLE=1`;
   verify it doesn't bypass mandatory governance (only optional
   features).
4. **Audit-log cardinality test**: spawn 100 quick agents; verify
   audit log captured exactly 100 `agent_spawn` events.

To record a completed drill, create or append to `docs/incident-drill-log.md`:

```markdown
## YYYY-MM-DD drill log

- Drill type: <tabletop | restore | hook-bypass | cardinality>
- Participants: <names/roles>
- Outcome: <pass | fail | partial — brief description>
- Action items: <list or "none">
```

## Escalation contacts

| Tier | Owner | Backup |
|------|-------|--------|
| SEV-1 / SEV-2 | Project Owner (see CLAUDE.md) | Per `SECURITY.md` |
| SEV-3 | GitHub issue | None |
| SEV-4 | GitHub issue | None |

For framework-level incidents (vulnerability in upstream
ceo-orchestration itself, not your adopter project), report via
[`SECURITY.md`](../SECURITY.md).

When designing or reviewing the on-call rotation that feeds this runbook,
consult `.claude/skills/core/incident-management/SKILL.md` §"On-Call
Hygiene" (minimum rotation size of four, two-week cap on consecutive
primary weeks, shadow-before-primary, business-hours handoff). A degraded
rotation produces degraded incidents.

Last reviewed: 2026-05-25 (PLAN-113 W7 — reconciled three-condition close +
48h PIR + on-call hygiene with `core/incident-management` SKILL doctrine;
prior review 2026-04-18 / Session 33 / PLAN-022 Phase 2).
