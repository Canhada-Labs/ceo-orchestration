<!-- SPDX-License-Identifier: MIT -->
# NOTICE — `.claude/skills/frontend/`

This directory imports reference data from the `ui-ux-pro-max-skill`
project under the MIT License (SPDX: MIT). Per the MIT License terms,
attribution is retained here.

## Imported data (PLAN-035, Wave B Session 38, 2026-04-19)

| Target YAML | Upstream CSV | Entries | License |
|---|---|---|---|
| `design-system-and-components/reference/palettes.yaml` | `src/ui-ux-pro-max/data/colors.csv` | 161 | MIT |
| `design-system-and-components/reference/fonts.yaml` | `src/ui-ux-pro-max/data/typography.csv` | 73 | MIT |
| `accessibility-and-wcag/reference/charts-accessibility.yaml` | `src/ui-ux-pro-max/data/charts.csv` | 25 | MIT |
| `ux-and-user-journeys/reference/guidelines.yaml` | `src/ui-ux-pro-max/data/ux-guidelines.csv` | 99 | MIT |

## Upstream

- **Project:** `ui-ux-pro-max-skill`
- **Repository:** https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
- **License:** MIT © 2024 Next Level Builder
- **License file (upstream):** https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/LICENSE
- **Imported-at commit:** refer to the git history of these YAML files
  for the exact checkout date; the first import commit is the source of
  truth for provenance.

## License (MIT, reproduced)

```
MIT License

Copyright (c) 2024 Next Level Builder

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Fair-use policy for this import

- **Data only:** we import CSV rows (structured data) converted to YAML.
  We do not import source code from the upstream project.
- **No text cloning of upstream docs:** skill descriptions, rationale
  sections, and prose in `SKILL.md` files are written by the
  `ceo-orchestration` CEO from the ingested structured data; they are
  not copies of the upstream README or docs.
- **Derivative work:** the YAML format + our own skill layer counts as
  derivative work. The MIT License permits this without explicit
  permission subject to the notice requirement satisfied here.

## Re-generation procedure

`.claude/scripts/import_ui_ux_pro_max.py` re-fetches the upstream CSVs
and regenerates the 4 YAML files in place. Run it when the upstream
project releases a tagged update. The script is stdlib-only and
deterministic; running it on unchanged inputs produces byte-identical
output (sanity-check with `git diff`).

```bash
python3 .claude/scripts/import_ui_ux_pro_max.py
```

## Contact

If a copyright holder believes this import exceeds the MIT License
terms, open an issue at https://github.com/Canhada-Labs/ceo-orchestration/issues
or email the Owner directly; the import will be removed in < 48 h.
