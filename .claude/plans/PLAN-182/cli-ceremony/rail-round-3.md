# Pair-rail — wave-cli, rodada 3 (S326, 2026-08-24 15:55–16:1xZ)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre o clone-sombra com o
pacote curado das rodadas 1–2 (+ correção do guard sincronizada do `7a618c9`). `RAIL_RC=0`.

**Resumo do revisor (verbatim):** *"The documented unattended backup path now exits before producing
a backup, and the guarded changes claim signed ceremony artifacts that are absent from the tree."*

| # | Sev | Achado | Verificação contra o código | Disposição |
|---|---|---|---|---|
| 1 | P1 | `docs/DISASTER-RECOVERY.md:306-314` documenta o cron `bash /abs/path/.claude/scripts/ceo-backup.sh ... > /dev/null 2>&1`: sob cron, `CLAUDE_PROJECT_DIR` está unset e CWD=`$HOME`, então o walk-up (cura r1 P2) não acha `.claude/` e o script sai 2 SEM backup — e o redirecionamento documentado esconde a falha. Antes da wave, o literal "funcionava" (para o dir compartilhado errado). | **CONFIRMADO** (doc lido; o walk-up parte do CWD). Regressão introduzida por mim na r1. | **CURADO r4:** `_project_root()` ganha o 3º degrau — o projeto que CONTÉM o script (`BASH_SOURCE`, `<projeto>/.claude/scripts/`), nos dois scripts. Smoke: CWD=`$HOME`, sem `CLAUDE_PROJECT_DIR`, invocação por path absoluto ⇒ resolve o projeto do script. Sem nada ⇒ ainda falha alto. |
| 2 | P1 | O tree revisado não contém `OWNER-S326-LAND.sh`, `wave-cli-approved.md` nem `.asc`, mas o plano afirma que a assinatura é commitada com o land; AGENTS.md:86-91/103-109 exige evidência de sentinel assinado para `.claude/hooks/**` e `.claude/governance/**`. | **Limite do que o sombra mostra** (mesma classe da r2 #2): os materiais vivem na árvore VIVA e a assinatura nasce no SIGN; o `.asc` só existe depois. | **Endereçado r4:** os materiais (sentinel-draft, SIGN, LAND, registros de rail) foram sincronizados no sombra como UNTRACKED — fora do patch — para o revisor verificar os gates G1–G5 e V1–V6. A frase do plano descreve o estado exato do commit em que ela entra na árvore (o land). |

Rodada 4 sobre o pacote curado, com os materiais visíveis.
