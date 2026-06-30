---
description: Scan a file for veto-worthy code-review + security patterns — /veto-check
allowed-tools: Bash, Read
---

# /veto-check — Machine-verifiable veto scan

Runs regex-based red-flag patterns against a single file and returns
a structured JSON report. Assertable in CI / debate rounds — no prose
interpretation.

## Arguments received

`/veto-check $ARGUMENTS`

`$ARGUMENTS` must start with a file path. Optional trailing `--text`
switches output to human-readable.

## Procedure

### Step 1 — Parse

Extract `FILE` (first positional token) and `FORMAT` (`json` default,
`text` if `--text` flag seen).

### Step 2 — Run scan

```bash
python3 .claude/scripts/veto-check.py --file "$FILE" --format "$FORMAT"
```

Do NOT pass `$ARGUMENTS` through a shell-interpolated string; pass
only the parsed `$FILE` value as an argv argument.

### Step 3 — Interpret exit code

- `0` → no vetoes triggered. Tell the user "clean — 0 vetoes".
- `1` → one or more vetoes. Print the JSON / text as-is; for each
  triggered rule, call out `id`, `line`, `message`. Recommend a fix.
- `2` → file not found or unreadable. Surface stderr and stop.

### Step 4 — Follow-up

If vetoes were triggered, suggest the user either:
- fix the code, re-run `/veto-check`, then proceed, or
- if it's a false positive, open an issue to refine the pattern in
  `.claude/scripts/veto-check.py` (`_RULES` table).

## Pattern coverage (as of Sprint 10 Phase 5)

- `code-review`: parseFloat, Number() cast, @ts-ignore, console.log
- `security`: dangerouslySetInnerHTML, eval, rm -rf, hardcoded secrets,
  subprocess shell=True, md5/sha1

Add new patterns by appending to `_RULES` in
`.claude/scripts/veto-check.py` — each rule is
`{id, domain, pattern, message}`.

## Exit codes

- 0 — scanned, clean
- 1 — scanned, vetoes triggered
- 2 — usage error
