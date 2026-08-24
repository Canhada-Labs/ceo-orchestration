# Pair-rail — wave-cli, rodada 5 (S326, 2026-08-24 16:2x–16:3xZ)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre o clone-sombra com o
pacote curado das rodadas 1–4, materiais de cerimônia visíveis (untracked) e o patch finalizado
(`Patch-sha256` preenchido). `RAIL_RC=0`.

**Resumo do revisor (verbatim):** *"The supplied landing workflow omits the newly generated GPG
signature from staging, undermining the required signed-sentinel evidence for guarded changes."*

| # | Sev | Achado | Verificação | Disposição |
|---|---|---|---|---|
| 1 | P1 | O fluxo pós-land instrui `git add -u`, que stageia só modificações de arquivos RASTREADOS; o `wave-cli-approved.md.asc` nasce UNTRACKED no SIGN e ficaria fora do commit — o land canônico subiria sem a evidência da assinatura (AGENTS.md:84-91). | **CONFIRMADO** (`git add -u` nunca inclui untracked). | **CURADO r6:** o `OWNER-S326-LAND.sh` ganha o passo **S** após V6 — `git add -u` + `git add -- <sentinel> <sentinel>.asc` (paths explícitos, sem diretório — lint R4), imprime o conjunto staged e ABORTA se o `.asc` não estiver nele. SIGN/PROPOSED deixam de instruir `git add -u`; o Owner só commita. |

Único achado da rodada; nenhum sobre o conteúdo do patch (12 paths inalterados desde a r4). Rodada 6
para confirmar o fluxo corrigido.
