# SENT-BACKLOG — PLAN-153 wave-backlog landing sentinel (round-4)

Drafted S261 (2026-07-07, overnight run) by the CEO under the Owner's
delegation; **inert until the Owner fills the anchor and detach-signs**
(`approved.md.asc`). Scope below covers the EXACT staged-overlay file set of
`.claude/plans/PLAN-153/staged/wave-backlog/` (mirror layout = repo-relative
targets) PLUS the one Amends-only target applied by anchored edit
(`SPEC/v1/audit-log.schema.md` — the permission layer denies staging a
complete copy; the edit payload is
`.claude/plans/PLAN-153/artifacts/SPEC-AMEND-audit-log-v2.48.md` after the
BLOCKER-2 move, applied by the Owner via Bash under this sentinel). The
wake-up ceremony asserts `touched − SIGNED SCOPE = ∅` before applying.

**Landing order (STRICT): this wave lands LAST** (wake-up WAVES array:
E → B → C → D → G → backlog). Two files in this scope —
`.claude/settings.json` and `.claude/hooks/_lib/audit_emit.py` — are the
SUPERSEDING copies: the wave-backlog staged versions CONTAIN the wave-E
staged content plus the backlog additions. Never apply wave-E's copies of
these two after the backlog's (would revert `sandbox.credentials` /
`enforceAvailableModels` and the v2.48 enum extension — the latter turns the
pin-sync guard RED by design).

Pre-signature checklist (from `staged/wave-backlog/MANIFEST.md`):
BLOCKER 1 — the BK2 lifecycle-stamp matcher fold-in must be applied to the
staged `settings.json` BEFORE signing; BLOCKER 2 — move the two root-level
metadata files out of the wave dir (SCOPE DRIFT trip); BLOCKER 3 — apply the
v2.48 anchored SPEC edits between overlay and gates.

Application path (S258 precedent): the Owner's shell applies the staged
overlay via `~/Desktop/ceo-wakeup/wake-up-sign-and-land.sh` — for the
SELF-MODIFICATION-class row (`.claude/settings.json`) this Owner-shell copy
IS the sanctioned patcher route; for the `SPEC/**` rows the Owner-shell
`cp`/anchored-edit under this sentinel is the sanctioned route; the signed
sentinel is the authorization record.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs 2094175a55fbe9f341e42baffa0ab06898aaa357
Plans: PLAN-153
Scope:
  Wave backlog — PLAN-152 §Deferred + Anthropic ADOPT-PLANNED substrate
  hardening (sandbox.credentials + enforceAvailableModels settings rails,
  TodoWrite→Task-tools lifecycle enum v2.48 with 3-way pin, npm-shim
  §Publishing false-claim correction), landed as the staged overlay of
  PLAN-153/staged/wave-backlog/ plus the anchored v2.48 SPEC amendment:
  - .claude/settings.json
  - .claude/hooks/_lib/tool_lifecycle.py
  - .claude/hooks/_lib/audit_emit.py
  - .claude/hooks/tests/test_tool_lifecycle_task_tools.py
  - SPEC/v1/npm-shim.md
  - SPEC/v1/audit-log.schema.md
Amends: SPEC/v1/audit-log.schema.md — v2.48 ADDITIVE closed-enum extension
  on `tool_call_lifecycle_recorded.tool_name_enum` (+ TaskCreate /
  TaskUpdate / TaskGet / TaskList; TodoWrite retained for back-compat),
  applied as the two anchored edits in SPEC-AMEND-audit-log-v2.48.md
  (actions-table enum row + one v2.48 version-history row). No new action,
  no new fields, `event_schema` stays v2, `_KNOWN_ACTIONS` unchanged;
  required by the enum extension landing in .claude/hooks/_lib/audit_emit.py
  and .claude/hooks/_lib/tool_lifecycle.py under this same sentinel
  (3-way pin, regression-guarded by
  hooks/tests/test_tool_lifecycle_enum_pin_sync.py).
Amends: SPEC/v1/npm-shim.md — §Publishing corrected to the SHIPPED auth
  mechanism (repo-scoped npm granular token behind the production-npm
  manual gate; the per-run OIDC JWT feeds ONLY the Sigstore --provenance
  attestation); the never-configured "OIDC trusted publisher" claim removed;
  spec version 1.0.0-rc.1 → 1.0.1-rc.1. Documentation-only, no contract or
  behavioral change; closes PLAN-152 §Deferred spec-npm-shim-oidc-wording
  (this sentinel carries the SPEC path, per that item's closure clause);
  the Trusted-Publishing migration itself remains deferred (backlog-oidc,
  v1.0.2).
<!-- END SIGNED SCOPE -->
