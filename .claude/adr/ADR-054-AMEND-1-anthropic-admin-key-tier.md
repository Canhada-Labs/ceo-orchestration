# ADR-054-AMEND-1 — Anthropic Admin API key tier (admin blast radius ≠ inference blast radius)

---
adr_id: ADR-054-AMEND-1
title: Anthropic Admin API key tier — categorically larger blast radius, own custody + cadence
status: PROPOSED
amends: ADR-054
proposed_at: 2026-06-12
proposed_by: CEO (PLAN-135 W5, unit O9)
session_origin: PLAN-135 W5 exec session (branch plan-135-exec, 2026-06-12)
risk_tier: B
debate_required: true
related_plans: [PLAN-135, PLAN-134]
related_adrs: [ADR-054, ADR-150]
---

## §1 Scope

ADR-054 ("GitHub Token Rotation Cadence", ACCEPTED 2026-04-18) defines the
rotation schedule for the framework's credential classes: fine-grained PAT,
classic PAT, `ANTHROPIC_API_KEY` (inference), `GITHUB_TOKEN`, NPM OIDC. It has
**no Anthropic *Admin* API key class at all** — PLAN-135 W5 introduces one
(`key-hygiene.py` Admin-API list/deactivate; O3 `cc-analytics-pull.py` is the
read-only analytics consumer of the same tier), so the tier must be doctrined
BEFORE any standing admin credential exists.

This amendment ADDS the admin-key tier to ADR-054's table and custody rules.
Every existing ADR-054 row and procedural rule is **unchanged**.

## §2 The load-bearing doctrine

**The Anthropic Admin API key's blast radius is categorically LARGER than
inference keys — not a bigger quantity of the same risk, a different
category.** Per `THREAT-MODEL-WORKSHEET.md` §3 (PLAN-135, debate R1):

> Org-level Anthropic Admin API key — blast radius categorically larger than
> inference keys: deactivate ALL org keys, read org-wide usage/cost.

A leaked inference key burns quota (bounded by spend alerts; ADR-054 treats it
as a 90-day-cadence vault secret). A leaked admin key (`sk-ant-admin…`, or an
`org:admin` OAuth token) can **deactivate every API key in the organization**
(an org-wide availability kill-switch — the S206 incident response weaponized
against us) and **read org-wide usage/cost data** (cross-workspace privacy
exposure). No spend alert bounds either. Therefore the admin tier gets
strictly stronger custody than any row already in ADR-054 — quota-burn
mitigations are NOT accepted as sufficient for this class.

## §3 Amendment to the ADR-054 rotation table

ADD one row:

| Token class | Cadence | Target scope | Evidence |
|-------------|---------|--------------|----------|
| Anthropic Admin API key (`sk-ant-admin…`) | **Provision-on-demand, deactivate within 24h of use.** Any deliberately-standing admin key: 90-day rotation + quarterly necessity review (default answer: do not keep one) | Org key management + org-wide usage/cost read. **NEVER CI, NEVER repo, NEVER settings.json** | `docs/rotation-log.md` row per provision / use / deactivation (`key-hygiene.py` auto-appends the mutation rows — the audit pair) |

## §4 Custody rules (per THREAT-MODEL-WORKSHEET.md §3 mitigations — normative)

1. **Never in repo or settings.** The admin key lives in the OS keychain /
   Owner-launch environment ONLY (`ANTHROPIC_ADMIN_KEY`), exported for the
   single command that needs it. Its *name* (not value) is documented in
   `docs/rotation-log.md`. `key-hygiene.py` deliberately exposes **no CLI
   flag** for the key and redacts every `sk-ant-…`-shaped substring from all
   error paths (the S206 urllib-trace leak class).
2. **Read-only by default.** The O3 analytics client (`cc-analytics-pull.py`)
   is READ-ONLY (analytics endpoints; no key-management writes) and fail-soft
   when the key is absent.
3. **Human gate on every mutation.** The `key-hygiene.py` deactivate path
   requires interactive Owner confirmation (explicit `--confirm`; refusal
   with zero network I/O without it) and writes a rotation-log entry — the
   **audit pair**: no admin-key mutation without a paired append-only record.
4. **No agent autonomy.** No agent, hook, workflow, or routine may invoke the
   deactivate/incident path autonomously. `--confirm` is an Owner act.
5. **WIF retires the long-lived CI inference secret.** With the GitHub-OIDC
   federation path live (`docs/BRANCH-PROTECTION.md` §WIF, this same O9
   unit), the standing-CI-secret class that motivated S206 shrinks toward
   zero — and the admin key must never be its replacement in CI.

## §5 Threat model (worksheet §3, verbatim-faithful)

- **Threat actors:** (a) key leakage via repo/transcript/audit-log; (b) an
  agent invoking `key-hygiene.py` destructively; (c) CI secret theft (the
  S206 class).
- **Attack vectors:** committed key; key echoed into transcripts;
  `key-hygiene.py deactivate` called without a human gate; long-lived CI
  secret reuse.
- **Mappings:** vector 1-2 → custody rule 1 (env-only + redaction); vector 3
  → custody rules 3-4 (`--confirm` + no-autonomy); vector 4 → custody rule 5
  (WIF) + the table row's NEVER-CI scope.

## §6 Residual risk (recorded, not mitigated here)

A read-only analytics scope still reads **org-wide** usage — a privacy (not
integrity) exposure. PLAN-135 §OQ4 puts the provisioning decision explicitly
on the Owner: whether an admin-tier key exists at all, and with which scope,
is an Owner call per provisioning event, not a framework default.

## §7 Consequences

- (+) The S206 incident response becomes one audited command
  (`key-hygiene.py incident --confirm`) instead of a manual Console sweep.
- (+) Auditors get an explicit tier for the highest-blast-radius credential
  the org can mint, with evidence in the same append-only log as every other
  class.
- (−) Provision-on-demand adds ~2-5 min of Owner friction per admin
  operation. Accepted: admin operations are rare (incidents, quarterly
  reviews) and the friction IS the control.
- (~) ADR-054's existing rows, procedures, and residuals (`RR-1` markdown
  ledger falsifiability) are unchanged and inherited by the new row.

## §8 Promotion gates + revisit triggers

Stays PROPOSED until the PLAN-135 W5 ceremony (debate per plan §W5 "O9's
ADR — each needs its ceremony" + Codex pair-rail + Owner-GPG sentinel on the
canonical `.claude/adr/` copy).

Revisit when: (a) Anthropic ships finer-grained admin scopes (split
key-management from usage-read → re-tier); (b) the first standing admin key
is provisioned (necessity review becomes live, not hypothetical); (c) a WIF
path exists for admin-scoped operations (would retire the standing-key
question entirely).

## References

- `.claude/adr/ADR-054-github-token-rotation.md` — the amended base
- `.claude/plans/PLAN-135/research/THREAT-MODEL-WORKSHEET.md` §3 admin-keys
- `.claude/plans/PLAN-135-anthropic-surface-harvest.md` §W5 O9
- `.claude/scripts/key-hygiene.py` — list/deactivate/incident + audit pair
- `docs/BRANCH-PROTECTION.md` §"WIF — keyless CI via GitHub OIDC"
- `docs/rotation-log.md` — 2026-06-03 S206 compromise row (the motivating
  incident)
- ADR-150 — commit-signing policy (sibling credential-provenance doctrine)
