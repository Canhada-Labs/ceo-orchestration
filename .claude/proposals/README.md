# `.claude/proposals/` — skill-patch proposals (ADR-031)

This directory holds **SP-NNN skill-patch proposals** drafted by
`.claude/scripts/skill-patch-propose.py` from accreted lessons. Each
proposal is a candidate edit to a single `SKILL.md` file.

**None of these files get applied to `SKILL.md` automatically.** The
flow is deliberately Owner-gated with a 7-day shadow soak:

1. `skill-patch-propose.py` drafts `SP-NNN-<skill-slug>-<date>.md`
2. Owner reviews, creates a **detached GPG signature** `SP-NNN-*.md.asc`
3. `skill-patch-apply.py` verifies signature + Owner confirm phrase, then
   writes a sibling `SKILL.md.shadow.md` file — never the real SKILL.md
4. After 7 days of shadow benchmarks, Owner re-runs apply with `--promote`;
   the tool prints the commit message with a `Skill-Patch-SHA:` trailer
5. Owner commits the real `SKILL.md` change. Two sentinels gate the
   commit: `check_canonical_edit.py` (ADR-010) + `check_skill_patch_sentinel.py`
   (ADR-031).

Rejection artifacts (`SP-REJECTED-<timestamp>.md`) document attempted
proposals that failed the CR1 mitigation bundle:

- Unicode bidirectional override (U+202E)
- Zero-width joiner/space (U+200B–U+200F)
- Homoglyph substitution
- Prompt-injection patterns (via `.claude/scripts/scan-injection.py`)
- Fenced executable code without `CEO_SKILL_PATCH_ALLOW_CODE=1`
- Diff exceeding 200 added+removed lines
- Source lesson containing a line >8000 chars (truncation attack)

## Related

- `ADR-031-self-improving-skills.md` — decision doc + 10-point mitigation
  table
- `SPEC/v1/skill-proposals.schema.md` — frontmatter schema + lifecycle
- `.claude/hooks/check_skill_patch_sentinel.py` — the new sentinel
- `.claude/hooks/check_canonical_edit.py` — the existing sentinel (ADR-010)

## Kill switch

`CEO_SOTA_DISABLE=1` disables **propose** and **apply**. The sentinel
remains active — it's a safety surface, not a feature flag.
