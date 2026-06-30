# Templates

Files under this directory are installed into target projects by
`scripts/install.sh`. They are not consumed by the framework itself.

## Contents

| File | Installed? | Purpose |
|---|---|---|
| `CLAUDE.md` | always | Per-project master context (session protocol, current work, changelog) |
| `MEMORY.md` | deprecated stub | Pre-native-memory file; kept for migration guidance only |
| `settings/` | always | Base settings.json + per-stack overlays merged at install |
| `docs/` | always | `BRANCH-PROTECTION.md` and sibling docs for target repo governance |
| `team-personas-reference.md` | **opt-in only** | Reference personas (fictional composites). See "Reference personas" below |

## Reference personas (opt-in)

`team-personas-reference.md` ships 8 fictional composite personas as a
starting point for projects that prefer vivid named personas over
archetype labels. **It is NOT copied by default.**

To include it:

```bash
bash scripts/install.sh <target> --with-reference-personas
```

Without that flag, the archetype-based `.claude/team.md` remains the
default (per PLAN-004 Phase 10 positioning decision — the archetype
model is the default; reference personas are examples, never defaults).

## Variable substitution

Files in this directory use `{{PLACEHOLDER}}` markers for values
resolved at install time:

| Placeholder | Source |
|---|---|
| `{{PROJECT_NAME}}` | derived from target directory basename |
| `{{OWNER_NAME}}` | user-edited after install |
| `{{OWNER_HANDLE}}` | `--github-owner` flag value |
| `{{STACK}}` | `--stack` flag value |

Unrendered `{{PLACEHOLDERS}}` that leak past install are caught by
`.github/workflows/validate.yml` (placeholder lint step) and by the
smoke-install test (`scripts/tests/smoke-install.sh`).
