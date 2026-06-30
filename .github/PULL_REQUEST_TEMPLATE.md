<!-- PLAN-013 Phase E.5 — PR template. -->

## Summary

<!-- 1-3 bullets describing what changed. Focus on the "why" more than
the "what" (the diff shows the "what"). -->

-
-

## Test plan

<!-- Checklist of what you ran locally. Copy-paste ready. -->

- [ ] `bash .claude/scripts/validate-governance.sh` — zero errors
- [ ] `python3 -m unittest discover -s .claude/hooks/tests` — all pass
- [ ] `python3 -m unittest discover -s .claude/scripts/tests` — all pass
- [ ] `python3 -m unittest discover -s tests/integration` — if integration-touching
- [ ] `actionlint .github/workflows/*.yml` — if workflows changed
- [ ] Screenshots attached if UI/dashboard changed

## Governance compliance

<!-- Check each box that applies; N/A the rest. -->

- [ ] **Code Reviewer VETO** criteria met (see `.claude/skills/core/code-review-checklist/SKILL.md`)
- [ ] **Security VETO** not triggered (no hook/auth/credential change) — OR Security Engineer tagged
- [ ] **ADR present** for L3+ changes (3+ modules, new contract, new dep)
- [ ] **Debate artifact** at `.claude/plans/PLAN-NNN/debate/round-N/` for L3+ changes
- [ ] **Canonical-edit hook** did NOT fire (no edits to `.claude/team.md`, `PROTOCOL.md`, SKILL.md files without Owner-signed sentinel)
- [ ] **Translations drift** unchanged (if touching `README.md`, `PROTOCOL.md`, or `docs/*.md` pairs)

## Blast radius

- [ ] L1 — 1-2 files, contained
- [ ] L2 — one subsystem
- [ ] L3+ — 3+ modules, new contract, or new dep (ADR required — cite below)

ADR(s) referenced: …

## Anti-goal check (PLAN-013)

- [ ] Does NOT add a new skill beyond the 48-skill floor (unless replacing one)
- [ ] Does NOT introduce a runtime dependency (stdlib only per ADR-002)
- [ ] Does NOT weaken MUST/MUST NOT/NEVER/ALWAYS in `PROTOCOL.md` or `team.md`
- [ ] Does NOT auto-publish from tag without manual approval env (anti-goal #16)
- [ ] Does NOT deploy to public (Sprint 17 conditional — repo stays private)

## Related

Closes #… / Relates to PLAN-### / Blocked-by #…

<!-- Co-author attribution when delegated to a Claude agent:
Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
-->
