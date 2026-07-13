# SENT-GK-B — PLAN-156 Wave 4+6 audit chain (grok + council)

Registers 3 metadata-only actions in _KNOWN_ACTIONS (grok_tool_recorded,
grok_turn_ended — Wave 4; council_lane_invoked — Wave 6, landed together
in the one audit_emit.py) + their typed emitters + closed-enum allowlists,
the audit_log.py grok dispatch, the golden (+3 → 319), and the SPEC
audit-log rows (via Bash). Count-pin test companions (unguarded) ride this
commit. audit_emit.py + audit_log.py are _KERNEL_PATHS.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: ac87869fcca87df3ca4bdbbab2779986e3b4d844
Plans: PLAN-156
Kernel-Override: PLAN-156-GROK-AUDIT-ACTIONS (+ CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT)
Scope:
  - .claude/hooks/_lib/audit_emit.py
  - .claude/hooks/audit_log.py
  - .claude/data/audit-registry.golden.txt
  - SPEC/v1/audit-log.schema.md
Amends: SPEC/v1/audit-log.schema.md — 3 action rows (grok_tool_recorded,
  grok_turn_ended, council_lane_invoked) + version-history rows v2.50/v2.51.
  Applied via .claude/plans/PLAN-156/staged/spec-patches/apply-spec-audit-log.py.
  _KNOWN_ACTIONS 316 → 319.
<!-- END SIGNED SCOPE -->
