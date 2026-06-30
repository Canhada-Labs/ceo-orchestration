---
name: Bug report
about: Something is broken or not behaving as documented
title: "[bug] "
labels: ["bug", "needs-triage"]
assignees: []
---

## Environment

- Framework version (`cat VERSION`):
- Python version (`python3 --version`):
- OS + version:
- Claude Code version (CLI / desktop / web / IDE):
- Install profile (`core` / `core,fintech` / etc.):

## Expected behavior

What should have happened?

## Actual behavior

What happened instead? Include exact error messages + audit log snippet if
available (`jq '.' ~/.claude/projects/<slug>/audit-log.jsonl | tail`).

## Reproduction steps

1. ...
2. ...
3. ...

Minimal reproducer if possible (~10 lines or one test case).

## Evidence

- [ ] Governance validation (`bash .claude/scripts/validate-governance.sh`) was clean BEFORE the bug appeared
- [ ] Hook tests (`python3 -m unittest discover -s .claude/hooks/tests`) pass
- [ ] Script tests (`python3 -m unittest discover -s .claude/scripts/tests`) pass
- [ ] Audit log shows the offending tool call (paste the JSON line)
- [ ] Attach any relevant plan/debate artifact from `.claude/plans/` if applicable

## Workaround (if any)

What you did to get unblocked. Helps maintainers understand urgency.

## Additional context

Screenshots, links to related issues, ADR references, etc.
