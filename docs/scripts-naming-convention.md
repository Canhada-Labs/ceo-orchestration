# `.claude/scripts/*.py` — naming convention

**Status:** active (PLAN-019 CR-P3-001 closure).
**Last reviewed:** 2026-04-17 (PLAN-019 Phase 4).

## TL;DR

- **kebab-case** (hyphen) for CLI-invokable scripts: `audit-query.py`, `hook-profiler.py`.
- **snake_case** (underscore) for Python modules that are imported by other Python
  code (hooks, other scripts, `_lib`): `confidence_gate.py`, `lesson_ranker.py`,
  `check_contamination.py`, `check_threat_model_coverage.py`, `check_translations_drift.py`.

Both conventions coexist INTENTIONALLY and are NOT to be unified into one.
This matches PEP 8 §Package and Module Names: "Modules should have short,
all-lowercase names. Underscores can be used in the module name if it
improves readability." For importable modules, we pick snake_case to
preserve `import lesson_ranker` ergonomics; for CLI-only tools, we pick
kebab for shell-idiomatic invocation.

## The 5 snake_case outliers (as of PLAN-019)

| File | Imported by | Keep snake_case |
|------|-------------|------|
| `.claude/scripts/check_contamination.py` | `validate-governance.sh` invokes, referenced in ADRs/plans historically (keep stable) | yes |
| `.claude/scripts/check_threat_model_coverage.py` | `.github/workflows/validate.yml` | yes (imported idiom) |
| `.claude/scripts/check_translations_drift.py` | `.github/workflows/validate.yml` | yes |
| `.claude/scripts/confidence_gate.py` | `.claude/hooks/check_confidence_gate.py`, `.claude/scripts/lessons.py` (import) | yes (module import required) |
| `.claude/scripts/lesson_ranker.py` | `.claude/scripts/lessons.py` (module import), referenced in ADRs 010, 015, 018, 019, 031 | yes (module import + ADR stability) |

## Why not unify?

Renaming snake→kebab would:
1. Break `import confidence_gate` and `import lesson_ranker` — Python
   cannot import a module whose filename contains `-`.
2. Trigger canonical-edit sentinel churn on ≥5 ADRs that cite these paths.
3. Require a bash pre-commit hook + 2+ cross-repo refactors for no
   behavior gain.

The audit reviewer flagged the mix as inconsistent; after weighing
the semantic distinction (module vs CLI), the convention is **kept
as-is** with this doc as the authoritative guide.

## Rule for new scripts

When adding a script under `.claude/scripts/`:

1. **Imported anywhere?** (by a hook, another script, or `_lib`?) → **snake_case**.
2. **Only invoked via `python3 .claude/scripts/<name>` or bash wrapper?** → **kebab-case** (preferred).

When in doubt, prefer kebab-case. The 5 outliers above are grandfathered
in; new CLI-only scripts should not add more snake_case files.

## Audit recipe

```bash
# Classify every script under .claude/scripts/*.py.
ls .claude/scripts/*.py | awk -F/ '{print $NF}' | awk '
  { if ($0 ~ /_/) print "snake:", $0; else print "kebab:", $0 }
' | sort
```

Expected output: ~65 kebab + 5 snake (2026-04-17 baseline). Anything
outside the enumerated 5 snake_case modules is a candidate for rename.

## Cross-references

- PLAN-018 audit finding CR-P3-001 (naming inconsistency)
- PLAN-019 Phase 4 (Code Reviewer polish pass)
- PEP 8 §Package and Module Names (Python style guide)
- Google Python style guide §3.16.2 (file names lowercase, underscores OK)
