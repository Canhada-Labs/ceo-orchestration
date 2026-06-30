# Translation tracker

> EN is the Single Source of Truth. All translated files below are
> mirrors — if they disagree with the English source, the English wins.
> Corrections to translations are welcome via PR.

## Tracked pairs

| English source (SSOT) | Language | Translated file | Source commit | Translator | Status |
|---|---|---|---|---|---|
| `README.md` | PT-BR | `README.pt-BR.md` | `initial` | CEO / Owner | synced 2026-04-12 |
| `PROTOCOL.md` | PT-BR | `PROTOCOL.pt-BR.md` | `HEAD` | CEO / Owner | synced 2026-06-22 |
| `CONTRIBUTING.md` | PT-BR | `CONTRIBUTING.pt-BR.md` | `HEAD` | CEO / Owner | synced 2026-06-22 |
| `docs/QUICKSTART.md` | PT-BR | `docs/QUICKSTART.pt-BR.md` | `HEAD` | CEO / Owner | synced 2026-06-22 |
| `docs/GUIA-COMPLETO.md` | PT-BR | `docs/GUIA-COMPLETO.pt-BR.md` | `HEAD` | CEO / Owner | synced 2026-06-22 |
| `docs/FOR-EMPLOYEES.md` | PT-BR | `docs/FOR-EMPLOYEES.pt-BR.md` | `HEAD` | CEO / Owner | synced 2026-06-22 |
| `docs/TROUBLESHOOTING.md` | PT-BR | `docs/TROUBLESHOOTING.pt-BR.md` | `HEAD` | CEO / Owner | synced 2026-06-22 |
| `docs/GLOSSARY.md` | PT-BR | `docs/GLOSSARY.pt-BR.md` | `HEAD` | CEO / Owner | synced 2026-06-22 |

Columns:

- **Source commit** — the git SHA of the EN file version this translation mirrors
- **Translator** — who owns keeping this pair in sync
- **Status** — `synced` \| `drifted` \| `stale` \| `pending`

## Drift policy

The workflow `.github/workflows/translations-drift.yml` runs on pushes
to `main` and emits an **advisory warning** (never blocks merge) when
an EN source has advanced **> 20 commits** beyond its recorded
translation commit.

Drift is a signal, not a failure:
- `synced`: translation within 20 commits
- `drifted`: 20–50 commits behind EN
- `stale`: > 50 commits behind, or > 60 days without update
- `pending`: translation does not yet exist for a recently-added EN file

## Adding a new translation

1. **Open an issue first** — we defer new languages (ES, ZH, …) until
   50+ stars (positioning decision per PLAN-004 Phase 9).
2. If approved, create the translated file at the appropriate
   extension (`.pt-BR.md`, `.es-ES.md`, `.zh-Hans.md`).
3. Add a row to this tracker.
4. In the translated file, include a banner pointing at the EN source.

## Updating an existing translation

1. Read the diff between your recorded commit and `HEAD` for the EN source.
2. Apply the equivalent changes to the translated file.
3. Update the `Source commit` column in this tracker.
4. PR with both the translated file + this tracker update in the same commit.

## Languages we do NOT ship today

- Spanish (ES) — Sprint 8+ conditional on adoption
- Chinese (ZH) — Sprint 8+ conditional on adoption
- All others — open an issue first

## Why EN-only for most docs

- `INSTALL.md`, `CHANGELOG.md`, `SPEC/v1/*`, `CODE_OF_CONDUCT.md` — all
  EN-only. These are reference docs; duplicating them across languages
  creates more drift than adoption value at our scale.
- `PROTOCOL.md` is the English canonical governance contract. It carries a
  maintained PT-BR mirror — `PROTOCOL.pt-BR.md` (tracked above). It is not
  translated to other languages. If the two diverge, `PROTOCOL.md` wins.
- `README.md` is the main adoption entry point — it gets the PT-BR mirror
  because PT-BR is the Owner's native language. Additional languages wait
  for organic demand.
