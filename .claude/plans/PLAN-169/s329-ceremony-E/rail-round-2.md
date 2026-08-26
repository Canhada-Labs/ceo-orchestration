# Pacote E — rail codex rodada 2 (shadow-E, 2026-08-26T21:25:16Z)

Rail-Verdict: REJECT
Comando: `codex exec review --uncommitted --skip-git-repo-check` na shadow-E (após as 3 curas da rodada 1 + wiring smoke-install.yml)
Achados: 1 P1 + 1 P2. Disposição do CEO: o P1 (ausência de sentinel assinado) é POR CONSTRUÇÃO — a sombra é revisada antes da cerimônia; o sentinel é o próprio pacote E (`wave-s329-E-approved.md`, assinado pelo Owner na manhã). O P2 (valor de evento do template não-array) é REAL — cura despachada ao agente u3-upgrade-hooks-derived-writer-r2 (18:25).

Full review comments:

- [P1] Supply an Owner-signed sentinel for guarded edits — scripts/upgrade.sh:2461-2461
  This patch modifies both `scripts/upgrade.sh` and `.github/workflows/`, but the staged, unstaged, and untracked set contains no Owner-signed ceremony-E sentinel. These are canonical-guarded surfaces whose edits require signed evidence ([AGENTS.md:84-91](AGENTS.md#L84-L91), [AGENTS.md:110-114](AGENTS.md#L110-L114)); without it, canonical-edit/landing verification must reject the change.

- [P2] Reject templates whose event values are not arrays — scripts/upgrade.sh:2573-2573
  If the source template is valid JSON with an object `.hooks` but an event value is an object, scalar, or null, this guard accepts it. The later `$te.value[]?` then either silently omits that event or iterates object values and can append nested blocks, rather than treating the structurally invalid template as advisory failure; validate that every event value is an array before running the merge.
The guarded-surface changes currently lack mandatory signed authorization, which blocks landing. The new template-derived merge also accepts malformed per-event template structures instead of failing open with a diagnostic.

