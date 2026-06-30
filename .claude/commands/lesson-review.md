---
description: Review recent lessons and optionally undo a lesson outcome — /lesson-review
allowed-tools: Bash
---

# /lesson-review — Review + undo lessons

Lists the top-K most recent lessons from `.claude/scripts/lessons.py`
and guides the user through optional undo of a lesson outcome.

No new backing script — reuses the existing `lessons.py list` CLI
and the `lessons.py undo` sub-command (PLAN-136 W3 F1), which delegates
to `lessons.undo_outcome()`.

## Arguments received

`/lesson-review $ARGUMENTS`

- no args → list all lessons (`lessons.py list`; listing is not capped)
- `--undo <lesson-id>` → skip listing, go straight to undo

## Procedure

### Step 1 — Decide mode

If `$ARGUMENTS` contains `--undo <id>`, go to Step 3. Otherwise list.

### Step 2 — List

```bash
python3 .claude/scripts/lessons.py list
```

Print the output, then ask:
"Quer desfazer algum outcome? Rode `/lesson-review --undo <lesson-id>`."

Do not assume the user wants undo — they may just be browsing.

### Step 3 — Undo (idempotent)

```bash
python3 .claude/scripts/lessons.py undo "$LESSON_ID"
```

Interpret output (and exit code):

- If it prints `already_undone` (exit 0) → tell the user
  "outcome já estava desfeito (no-op)". Do NOT treat as error.
- If it prints `undone:` (exit 0) → confirm with the undone lesson id
  and the resulting hit/miss counts shown in the message.
- If it prints `not found` (exit 3) → surface the message + suggest
  re-listing to widen the window.

Idempotency contract: running `/lesson-review --undo X` twice in a
row must never raise on the second call — the second call lands in the
`already_undone` no-op branch (exit 0).

## Fail-open

If `lessons.py` is missing (old install) or its `undo` sub-command is
unavailable, report the gap and stop — do not silently succeed.

## Exit codes

- `0` — listing, or undo succeeded / already-undone (idempotent no-op)
- `3` — undo target not found (no live lesson with that id)
