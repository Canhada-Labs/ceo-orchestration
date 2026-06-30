---
description: List pitfalls from the universal catalog (and optionally a domain) — /pitfall
allowed-tools: Bash
---

# /pitfall — Pitfalls catalog lookup

Prints the pitfalls Claude Code consults before spawning agents.
Universal catalog always; add a domain (e.g. `fintech`, `trading-hft`,
`lgpd-heavy-saas`) to stack domain-specific rules on top.

## Arguments received

`/pitfall $ARGUMENTS`

- no args → universal catalog only (text)
- one arg → treated as `--domain <name>`
- `--json` anywhere → JSON output

## Procedure

### Step 1 — Resolve flags

Parse `$ARGUMENTS`:
- first non-flag token = `--domain <token>`
- presence of `--json` → `--format=json`

### Step 2 — Run backing script

```bash
python3 .claude/scripts/pitfall-query.py ${DOMAIN:+--domain "$DOMAIN"} ${FORMAT:+--format "$FORMAT"}
```

- Exit 0 → print stdout verbatim.
- Exit 2 → unknown domain. stderr lists available domains; surface
  that to the user and stop.

### Step 3 — Guidance

After printing, remind the user:

- "These rules are what the CEO auto-injects into agent prompts via
  `inject-agent-context.sh`."
- "Domain pitfalls live at `.claude/skills/domains/<domain>/pitfalls.yaml`."

## Fail-open

If the script errors unexpectedly (non-0/2 exit), surface the stderr
text and stop — do not pretend the catalog is empty.

## Exit codes

- 0 — listed
- 2 — unknown domain (message + available list shown)
