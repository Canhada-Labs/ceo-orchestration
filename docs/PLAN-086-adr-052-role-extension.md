---
plan: PLAN-086
wave: B
note_type: appendix
relates_to_adr: ADR-052
provenance:
  - PLAN-074 Wave 1c (canonical-5 → canonical-8 VETO-floor expansion)
  - ADR-052 §Veto-floor expansion (lines 186-210)
  - ADR-115 (post-SOTA maintenance — anti-churn rationale)
mutates_adr_bytes: false
---

# PLAN-086 Wave B — ADR-052 Role-Extension §Note Appendix

> **Anti-churn discipline per ADR-115:** this §Note appendix records
> the 4 row additions to `_ADR_052_ROLE_TO_MODEL` in
> `.claude/hooks/audit_log.py`. **ADR-052 canonical bytes are NOT
> mutated.** The 4 rows ship inline in code with a `# PLAN-074 Wave 1c
> provenance` cross-reference comment pointing back here.

## 1. What this appendix documents

PLAN-086 Wave B extends the `_ADR_052_ROLE_TO_MODEL` policy table in
`.claude/hooks/audit_log.py` with four archetype rows that were
declared in ADR-052 §Veto-floor expansion (lines 186-210) and
PLAN-074 Wave 1c but were never added to the runtime lookup. The gap
was surfaced by PLAN-084 B.12 capability-gap §AC11c (51% mis-routing).

## 2. The four added rows

| Archetype | Model floor | VETO per ADR-052 | Provenance |
|---|---|---|---|
| `incident-commander` | `claude-opus-4-7` | Yes (§187) | PLAN-074 Wave 1c |
| `identity-trust-architect` | `claude-opus-4-7` | Yes (§186) | PLAN-074 Wave 1c |
| `threat-detection-engineer` | `claude-opus-4-7` | Yes (§188) | PLAN-074 Wave 1c |
| `llm-finops-architect` | `claude-opus-4-7` | No (§190) | PLAN-074 Wave 1c |

### Why `llm-finops-architect` carries Opus floor

1. **Mis-routing prevention.** Without the row, `_resolve_archetype_model`
   returns `None` → dispatcher silently falls back to CEO default.
2. **Cost-ceiling integrity.** FinOps decisions govern cost ceiling for
   every other dispatch (PLAN-084 finding C.5: 58-85× undercount).
3. **Symmetry.** Reduces operator surprise; future cost-recovery mode
   (`CEO_MODEL_DOWNSHIFT=1`, PLAN-088 W2.2) can selectively downshift.

## 3. Why ADR-052 bytes NOT mutated (ADR-115 anti-churn)

Mutating ADR-052 for a row-addition already declared in §Veto-floor
expansion would:
- Force new R1+R2 debate cycle on a settled choice
- Drift ADR-052 SHA pinned in 7 downstream references
- Spend ~$50-100 CEO compute on documentation-only flip

The §Note appendix pattern is the maintenance-mode mechanism. AC B.5 enforces.

## 4. Verification

```bash
for archetype in incident-commander identity-trust-architect \
                 threat-detection-engineer llm-finops-architect; do
  grep -q "\"$archetype\"" .claude/hooks/audit_log.py || {
    echo "missing $archetype"; exit 1; }
done
pytest .claude/hooks/tests/test_adr_052_role_to_model_coverage.py -x
```

## 5. Downstream consumers

- `audit_log.py:_resolve_archetype_model` (silent benefit)
- `_lib/tier_policy/recommendation.py` (PLAN-086 Wave A) — empty
  recommended_model rate drops <20%
- PLAN-088 W2.2 full `_lib/model_routing.resolve()` — overlays
  tier-policy on top of this floor

## 6. References

- ADR-052 §Veto-floor expansion (lines 186-210)
- ADR-115 (post-SOTA maintenance mode)
- PLAN-074 Wave 1c (archetype-creation ceremony)
- PLAN-084 capability-gap §AC11c (51% mis-routing baseline)
- PLAN-086-p1-burn-down.md §4 Wave B AC B.1-B.5
