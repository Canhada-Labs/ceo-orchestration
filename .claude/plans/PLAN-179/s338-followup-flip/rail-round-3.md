# wave-179fu — rail codex rodada 3 (sombra `shadow-179fu`, base f0e98de, 2026-09-02 S338)

Rail-Verdict: APPROVE

Comando: `codex exec review --uncommitted --skip-git-repo-check
-c sandbox_mode="workspace-write"`, de DENTRO da sombra, stdin `</dev/null`,
rodada pelo orquestrador (as r1/r2 foram do builder do Workflow). Saída
bruta: `codex-r3.txt` [saída bruta, NÃO versionada — scratchpad S338
`codex-logs/s338-followup-flip/`] (8.263 linhas, rc 0). Snapshot sha256 do
diff da sombra antes/depois: **TREE-INTACT** (mesmo sha da r2,
`ba5efe98…c021b`).

## Veredito do codex, verbatim no que importa

«The implementation and targeted tests appear sound, but the patch modifies
canonical-guarded hook sources without the mandatory Owner-signed
sentinel.» Um único item: **[P1] Add an Owner-signed sentinel before landing**.

## Por que isto é APPROVE do PATCH

- **Zero achados de código, teste ou doc** em três rodadas consecutivas
  depois da cura da r1 (o P1 REAL da r1 — flip parcial fragmentando a sessão
  para leitores que particionam por `session_id` — fechou a CLASSE nos 4
  produtores por censo mecânico; o refutador independente do Workflow
  reproduziu o censo e a bateria: `refuted=false`).
- **O item restante é o artefato que a CERIMÔNIA produz.** O sentinel
  `PLAN-179/wave-179fu-approved.md` + `.asc` são materiais da árvore viva,
  commitados ANTES do SIGN (P0-d) e IMPOSSÍVEIS na sombra por construção (o
  `finalize-179fu.sh` recusa path fora do EXPECTED). A autorização de cada um
  dos 4 hooks KERNEL é provada no LAND (G5, `_sentinel_grants_path` vivo
  contra a assinatura GPG do Owner) e o KERNEL pelo override de menor escopo
  (par reason-SLUG + `I-ACCEPT`, harness T20e). O rail revisa o TEXTO; a
  autorização é o que SIGN/LAND acrescentam — leitura idêntica à r5 da
  wave-fable51 e às r1/r2 desta wave.

## Critério de parada

Três rodadas; 1 achado REAL (r1) curado com re-derivação completa; r2 e r3
sem classe nova. O refutador independente re-derivou o patch em worktree
próprio, reproduziu 551/0/2, 60/60 e o controle positivo 7/2. O que fica
FORA está declarado no PROPOSED («O que este patch NAO faz») e nos residuais
do sentinel; a prova de reprodutibilidade e a bateria completa são do LAND.
