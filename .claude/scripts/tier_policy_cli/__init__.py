"""PLAN-043 — Dynamic tier selector (learned-policy from tournament output).

This package implements the tournament → dispatch feedback loop that
PLAN-032 tournament (ADR-063 ACCEPTED) produces empirical win-rate data
for. The policy artifact at ``.claude/tier-policy.json`` + companion
sigchain ``.claude/tier-policy.json.sigchain`` translate tournament
signals into per-agent tier assignments with statistical power gates,
asymmetric promote-auto / demote-Owner-signed gating, and a hardcoded
VETO floor (code-reviewer + security-engineer always Opus 4.8) that
cannot be overridden by learned policy.

Module layout:

    _constants.py  — VETO_HARDCODE (single source of truth; frozen
                     SHA256 anchor for module-load-time byte-identity
                     assertion per defense-in-depth closure C-P0-3)
    types.py       — dataclasses + MODEL_ID Literal + ROLE_TO_TASK_TYPES
                     mapping (C-P0-6, C-P0-9)
    loader.py      — read + schema-validate + HMAC-verify policy JSON;
                     fail-open to ADR-052 static baseline on corruption
    learn.py       — aggregate tournament reports → recommendations;
                     statistical power gate (n≥30 + gap_pp≥25 per cell);
                     cooldown; VETO floor zeroth-check
    apply.py       — promote-auto (cost-envelope gated) / demote-signed;
                     VETO_HARDCODE_APPLY independent literal (defense
                     in depth); filelock on full read-compute-write
                     transaction
    cli.py         — derive / apply / owner-sign / verify / show
                     subcommands

Design invariants preserved (see PLAN-043 + ADR-064 DRAFT):
- stdlib-only (ADR-002)
- Fail-open (ADR-005) — corrupt policy → ADR-052 static fallback
- VETO floor hardcoded (ADR-052 §Invariants + ADR-064 §Decision 2)
- HMAC chain (ADR-055 pattern) on policy + sigchain
- Two-factor kill-switch (CEO_TIER_POLICY_ENABLE + sentinel file)
- Adopter override preserved (PLAN-021 contract)

Post Round 1 debate (2026-04-19), the package scope expanded to
incorporate 14 convergent P0 + 8 P1 closures. See
``.claude/plans/PLAN-043/debate/round-1/consensus.md`` for the
blocking-closure list.
"""
