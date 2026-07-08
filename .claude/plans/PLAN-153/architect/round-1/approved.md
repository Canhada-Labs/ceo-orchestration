# SENT-E — PLAN-153 Wave E landing sentinel (round-1)

Drafted S261 (2026-07-07, overnight run) by the CEO under the Owner's
delegation; **inert until the Owner fills the anchor and detach-signs**
(`approved.md.asc`). Scope below is the EXACT staged-overlay file set of
`.claude/plans/PLAN-153/staged/wave-E/` (mirror layout = repo-relative
targets). The wake-up ceremony asserts `touched − SIGNED SCOPE = ∅` before
applying.

Application path (S258 precedent, PLAN-152 round-3): the Owner's shell
applies the staged overlay via `~/Desktop/ceo-wakeup/wake-up-sign-and-land.sh`
— for the SELF-MODIFICATION-class rows (`.claude/settings.json`,
`.claude/hooks/check_bash_safety.py`) this Owner-shell copy IS the sanctioned
patcher route; the signed sentinel is the authorization record. ADR-158/159
land with this wave and flip PROPOSED→ACCEPTED in the landing series.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs 71a2ef5f8dc52aabe8ba2c848e65b7c6b895a5c1
Plans: PLAN-153
Scope:
  Wave E — security gates (behavioral positive-controls, harness-config
  gate, deny baseline, supply-chain watch, citation gate, prompt defense),
  landed as the complete staged overlay of PLAN-153/staged/wave-E/:
  - .claude/hooks/check_harness_config.py
  - .claude/hooks/tests/test_check_harness_config.py
  - .claude/hooks/check_bash_safety.py
  - .claude/hooks/tests/test_bash_citation_gate.py
  - .claude/hooks/check_agent_spawn.py
  - .claude/hooks/tests/test_prompt_defense_baseline.py
  - .claude/hooks/_lib/audit_emit.py
  - .github/workflows/supply-chain-watch.yml
  - .github/workflows/validate.yml
  - .claude/settings.json
  - scripts/install.sh
  - scripts/tests/test-install-deny-baseline.sh
  - .claude/adr/ADR-158-harness-config-gate.md
  - .claude/adr/ADR-159-citation-gate-and-prompt-defense.md
  - .claude/hooks/tests/test_audit_emit_api_contract.py
  - SPEC/v1/audit-log.schema.md
Amends: SPEC/v1/audit-log.schema.md — adds the spawn_prompt_defense_gate
  action row (closed-enum fields keyword/present/enforced, Sec MF-3
  allowlist) AND the matching v2.47 version-summary-table row (SPEC
  internal consistency; v2.46 carries one); required by the _KNOWN_ACTIONS
  302→303 registration landing in .claude/hooks/_lib/audit_emit.py under
  this same sentinel.
<!-- END SIGNED SCOPE -->
