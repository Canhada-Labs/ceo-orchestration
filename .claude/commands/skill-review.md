---
description: List pending skill-patch proposals + approve/reject
allowed-tools: Bash, Read
---

# /skill-review — review + approve SP-NNN proposals (ADR-031)

The self-improving-skills flow (ADR-031) produces candidate SKILL.md
patches as `SP-NNN-<skill>-<date>.md` files under `.claude/proposals/`.
This command is the Owner's entry point for reviewing them and handing
the approval signature to `skill-patch-apply.py`.

## Subcommands

### `/skill-review` or `/skill-review list`

**Idempotent** read-only listing. Lists every proposal under
`.claude/proposals/` with status, target skill, lesson count, diff size,
and diff hash prefix. Useful for answering "what's queued?".

### `/skill-review approve SP-NNN --confirm "I have read SP-NNN" --signature <path>`

Hands off to `skill-patch-apply.py` (default mode — shadow apply). The
confirm phrase MUST match exactly:

```
I have read SP-NNN
```

(with the actual proposal ID substituted for `SP-NNN`). Any other
phrasing returns exit 3.

### `/skill-review promote SP-NNN --confirm "I have read SP-NNN" --signature <path>`

Hands off to `skill-patch-apply.py --promote`. Requires `proposed_at`
to be at least 7 days old AND the shadow file to already exist from a
prior apply.

## Arguments received

`/skill-review $ARGUMENTS`

Parse `$ARGUMENTS` as:
- empty or `list` → run list flow
- `approve SP-NNN --confirm "..." --signature <path>` → run apply flow
- `promote SP-NNN --confirm "..." --signature <path>` → run promote flow

## Procedure

### Case 1 — list (idempotent)

1. Read every `.claude/proposals/SP-*.md` file (skip
   `SP-REJECTED-*.md`).
2. Parse the YAML frontmatter. Emit a table with columns:
   ID, status, skill_slug, archetype, lesson_count, diff_size,
   sha256_prefix (first 8 chars), proposed_at.
3. If the directory is empty, say "no proposals queued".

### Case 2 — approve

1. Validate that the confirm phrase is EXACTLY `I have read SP-NNN`.
   If not, STOP and tell the Owner the expected phrase.
2. Validate the signature file exists.
3. Run:
   ```bash
   python3 .claude/scripts/skill-patch-apply.py \
       --proposal SP-NNN \
       --signature "<path>" \
       --confirm "I have read SP-NNN"
   ```
4. Interpret exit codes per ADR-031:
   - 0 → tell Owner the shadow file was written.
   - 2 → signature failed. Recommend `gpg --verify <sig> <proposal>`.
   - 3 → confirm phrase wrong. Show the expected literal.
   - 5 → proposal not found or malformed.

### Case 3 — promote

Same as approve but with `--promote` appended. Add interpretation for:
- 4 → too early (<7d). Tell the Owner how long to wait.
- 6 → shadow file missing. Tell the Owner to run `approve` first.
- 7 → already promoted. Nothing to do.

## Safety notes

- The sentinel (`check_skill_patch_sentinel.py`, ADR-031) enforces this
  flow at `Edit|Write|MultiEdit` time. Skipping this command and editing
  a SKILL.md directly will be blocked.
- `CEO_SOTA_DISABLE=1` in your shell disables propose+apply but NOT the
  sentinel — the sentinel is a safety surface.
- The approval phrase is a speedbump against accidental RCE via stuck
  shell history. Read the proposal first, then type the phrase.

## Exit codes (from underlying CLI)

- 0 — shadow apply or promote succeeded
- 2 — signature missing or invalid
- 3 — confirm phrase wrong
- 4 — `--promote` requested <7 days after `proposed_at`
- 5 — proposal not found or malformed
- 6 — shadow file missing when `--promote` requested
- 7 — already promoted
