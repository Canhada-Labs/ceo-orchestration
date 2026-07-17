# API key rotation log

> Append-only log of `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` rotations.
> See `docs/BRANCH-PROTECTION.md` §"API Key Hygiene" for the rotation
> procedure and policy.
>
> **Format per entry:**
> - date (ISO 8601)
> - key (which one — `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or other)
> - reason (suspicion / compromise / scheduled / initial setup)
> - rotated_by (handle)
> - outcome (ok / reverted / incident)
>
> NEVER paste a key into this file. The key's presence anywhere in
> version control is itself a rotation trigger.

## Log

| Date       | Key                | Reason          | Rotated by  | Outcome | Notes                                                          |
|------------|--------------------|-----------------|-------------|---------|----------------------------------------------------------------|
| 2026-04-14 | ANTHROPIC_API_KEY  | initial setup   | @Canhada-Labs | ok      | ANTHROPIC_API_KEY first provisioned for ceo-orchestration dev. |
| 2026-05-09 | OPENAI_API_KEY     | initial setup   | @Canhada-Labs | ok      | OPENAI_API_KEY initial provisioning for Codex MCP / Pair-Rail (PLAN-081 Phase 1-full). 90-day cadence kicks in from this date. |
| 2026-06-03 | ANTHROPIC_API_KEY  | compromise      | @Canhada-Labs | ok      | S206: key leaked in a urllib error trace during the $250-credit advisor setup. ALL prior Anthropic keys REVOKED in the console; new key provisioned + verified (HTTP 200 on /v1/models). Local leaked-copies neutralized: ~/.config/anthropic/key.save shredded, ~/.zsh_history key lines scrubbed. Repo confirmed clean (strict scan: no real key in git tree/history). No key value committed anywhere. |
| 2026-07-16 | NPM_TOKEN          | retired (OIDC)  | @Canhada-Labs | ok      | PLAN-158 GA v1.1.0: first Trusted Publishing (OIDC) publish succeeded — tokenless + provenance (sigstore transparency log). Granular token `ceo-orchestration-ci` (was set to expire 2026-09-28) DELETED on npmjs.com; the `NPM_TOKEN` secret DELETED from the `production-npm` environment (it never existed at repo scope). npm publish auth is now 100% OIDC via the registered trusted publisher (repo `Canhada-Labs/ceo-orchestration` + workflow `npm-publish.yml` + env `production-npm`). Rollback path if ever needed: playbook Recovery B (`.claude/plans/PLAN-158/oidc-failure-playbook.md`) — mint a NEW token; nothing to un-revoke. |

<!-- PLAN-045 Wave 3 F-14-04 closure: the "no rotations yet" stub was
replaced with an explicit initial-stand-up entry so the log has a
baseline reader can diff future rotations against. Monthly CI reminder
tracked in .github/workflows/rotation-monthly-reminder.yml (Sprint 30+
deliverable). -->

**Latest rotation window (Anthropic):** 2026-06-03 (unscheduled — leak/compromise rotation, S206).
Next scheduled review: 2026-09-03 (quarterly cadence per ``docs/BRANCH-PROTECTION.md`` §API Key Hygiene).

**Latest rotation window (OpenAI):** 2026-05-09. Next scheduled review: 2026-08-07
(90-day cadence per PLAN-081 R1 S-Sec-6 — see §Codex API key rotation policy below).

## Codex API key rotation policy (R1 S-Sec-6 — PLAN-081 Phase 1-full)

PLAN-081 R1 S-Sec-6 mandated that the Codex API key (`OPENAI_API_KEY` slot
used by the Codex MCP server) MUST have a 90-day rotation cadence. This
was MOVED from Phase 6 → Phase 1 because keeping the key in production
for the ~38-58h compute window of PLAN-081 itself without a rotation
policy is unacceptable.

**Cadence:**

- **90 days hard refresh** — a fresh key issued + the prior key revoked.
- **75 days warn** — `pair-rail-gate.sh` Phase 1 pre-flight emits a
  warning when the last logged rotation is >75 days old.
- **90 days refuse** — `pair-rail-gate.sh` exits non-zero when the last
  logged rotation is >90 days old, refusing to invoke Codex until rotated.
- **Override:** `CEO_CODEX_KEY_ROTATION_OVERRIDE=1` env var bypasses the
  refusal for emergency / off-cycle rotations. Override emits an audit
  event for forensic record.

**Rotation procedure:**

1. Issue a new key from the OpenAI dashboard (Settings → API Keys → Create
   new secret key — `sk-proj-…` format).
2. Update the local `.env` / `direnv` / `.envrc` file (NEVER commit).
3. Verify Codex CLI works with the new key: `codex exec --model gpt-5-codex
   --sandbox read-only -- "ping"` should return cleanly.
4. Append a new row to the **Log** table above with `OPENAI_API_KEY` in the
   `Key` column and `scheduled` in the `Reason` column.
5. Revoke the old key from the OpenAI dashboard.
6. Verify revocation: previous key fails with `401 invalid_api_key` on a
   manual probe.
7. Run `bash .claude/scripts/local/pair-rail-gate.sh --phase 1` to confirm
   the pre-flight asserts a fresh rotation date.

**Compromise procedure:**

1. **Immediately** revoke the compromised key from the OpenAI dashboard.
2. Run steps 1-6 above with `compromise` in the `Reason` column.
3. Audit `~/.claude/projects/ceo-orchestration/audit-log.jsonl` for any
   `pair_rail_*` events that may have used the compromised key during the
   exposure window.
4. File a security incident note in `.claude/plans/PLAN-NNN-codex-key-
   compromise-<DATE>.md` (use a fresh PLAN-NNN per ADR-031).

---

## Provider pricing refresh

Separate cadence from API-key rotation above: the per-model token
cost table at `docs/provider-pricing.md` is refreshed on a rolling
90-day schedule so the `/agent budget` rollup and
`audit-dashboard.py` stay aligned with published provider pricing.

- **Refresh cadence:** every 90 days (rolling; earlier refresh
  encouraged when a provider announces a public rate-card change).
- **Last refresh:** 2026-04-14 (PLAN-012 Phase 0 D1).
- **Next refresh due:** 2026-07-14.
- **Owner:** CEO (coordinates with DevOps Engineer archetype).
- **Source URLs:** documented inline in the header of
  `docs/provider-pricing.md`. Anthropic / Google / OpenAI canonical
  pricing pages only — no third-party aggregators, no marketing
  pages.
- **CI guard:** `.github/workflows/validate.yml` step
  `D1 pricing TBD guard` fail-fast-rejects any `TBD` left in the
  primary pricing table's data rows. Prose TBD mentions in policy
  paragraphs are ignored by design.
- **Automation candidate:** Sprint 13+ — a paths-filtered
  `.github/workflows/pricing-refresh.yml` weekly cron that opens a
  PR surfacing stale rows (`Last verified` > 90 days). Until then,
  refresh is CEO-initiated.

### Pricing refresh log

| Date       | Providers refreshed | Rows touched | Refreshed by | Notes                                         |
|------------|---------------------|--------------|--------------|-----------------------------------------------|
| 2026-04-14 | Anthropic, Google, OpenAI, Local | 9 primary + 2 embeddings | CEO / DevOps | PLAN-012 Phase 0 D1 — initial full population with confidence field + source URLs. 2/9 rows at confidence=medium (claude-haiku-4-5, gpt-4.1) pending next GA rate-card check. |
