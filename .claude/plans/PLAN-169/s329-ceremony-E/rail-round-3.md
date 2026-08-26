# Pacote E — rail codex rodada 3 (shadow-E, 2026-08-26T21:42:19Z)

Rail-Verdict: REJECT
Comando: `codex exec review --uncommitted --skip-git-repo-check` na shadow-E (estado das 18:34, após a cura da rodada 2 em curso)
Achados: 1 P1 (sentinel — POR CONSTRUÇÃO, disposto: o pacote E é o sentinel; repete em toda revisão de sombra não-assinada) + 2 P2 reais (bloco malformado dentro de evento do template; SKIP-EVENT reportado como «tudo presente») — curas despachadas ao agente u3-upgrade-hooks-derived-writer-r2 (19:10).

Full review comments:

- [P1] Include the signed sentinel for guarded edits — scripts/upgrade.sh:2461-2462
  This patch changes guarded `scripts/upgrade.sh` and `.github/workflows`, but the staged set contains no Owner-approved sentinel or signature for package E. The reviewer contract requires signed sentinel evidence for guarded edits and lists both paths ([AGENTS.md:86-91](AGENTS.md#L86-L91), [AGENTS.md:110-114](AGENTS.md#L110-L114)); without it, this change is not landable or auditable.

- [P2] Reject malformed blocks in the source template — scripts/upgrade.sh:2681-2685
  When a template event is an array containing a malformed block such as `null`, `{}`, or `{"hooks":[]}`, the outer validation passes, `_keys` returns no keys, and this branch silently skips that block while merging valid siblings. This produces a partial roster despite the all-or-nothing template-validation contract; validate every block and its command identity before starting the reduction.

- [P2] Do not report skipped events as fully registered — scripts/upgrade.sh:2748-2750
  If an adopter has a preserved non-array event such as `PreCompact: null` and every other template registration is present, the report contains only `SKIP-EVENT`, leaving `_adds == 0`. The dry-run and apply paths then claim every framework registration is already present even though the skipped hook is absent; track skipped events separately and report a partial/preserved result instead.
The guarded changes lack required signed sentinel evidence. The merge also accepts malformed template blocks as a partial roster and can falsely report skipped adopter events as fully registered.

