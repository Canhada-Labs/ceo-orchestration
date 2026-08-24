# Pair-rail — wave-cli, rodada 4 (S326, 2026-08-24 16:10–16:2xZ)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre o clone-sombra com o
pacote curado das rodadas 1–3 e os materiais de cerimônia visíveis (untracked). `RAIL_RC=0`.

**Resumo do revisor (verbatim):** *"The default backup/restore discovery misidentifies the user's
global Claude directory as the project in the documented cron environment. The ceremony also has a
dirty-rename bypass and lacks the required patch-bound signed sentinel artifacts."*

| # | Sev | Achado | Verificação contra o código | Disposição |
|---|---|---|---|---|
| 1 | P1 | Sob o cron documentado (CWD=`$HOME`), o `~/.claude` GLOBAL existe, então o walk-up (`-d "$cur/.claude"`) escolhe `$HOME` como projeto e nunca chega ao fallback do `BASH_SOURCE`; o backup sai 0 com a fonte errada (slug do HOME). Mesmo loop no restore. | **CONFIRMADO.** Meu smoke da r3 usou um HOME falso SEM `.claude/` e por isso não reproduziu — controle fraco. `~/.claude` real existe e não tem `.framework-version`. | **CURADO r5:** o walk-up exige o marcador de INSTALAÇÃO (`.claude/.framework-version` — o mesmo que a OQ-5 do Owner nomeou como evidência de adopter); o fallback do script exige `.claude/scripts` + `.claude/hooks`. Smoke novo: HOME com `.claude/` global (sem marcador) ⇒ resolve o projeto do script. |
| 2 | P1 | G0 do `OWNER-S326-LAND.sh` corta 3 chars do porcelain: um rename `R  old -> .claude/hooks/x.py` vira a string inteira, o oráculo classifica pelo path velho (0) e o land tolera; paths com aspas/newline idem. | **CONFIRMADO.** | **CURADO:** porcelain `-z` (NUL); rename/cópia ⇒ ABORTA; path com newline ⇒ ABORTA (gate falha fechado em entrada que não parseia). Controle positivo: rename simulado para dentro de `.claude/hooks/` ⇒ G0 aborta. |
| 3 | P1 | O sentinel no tree tem `TO-FILL`, e faltam o `S326-CLI-CEREMONY.patch` e o `.asc`. | **Limite de visibilidade** (draft sincronizado antes da finalização). `Anchor-SHA`/`Data`/`Approved-By` são preenchidos pelo SIGN por desenho (precedente S321: preencher cedo produz âncora obsoleta). | **Endereçado r5:** patch finalizado e `Patch-sha256` preenchido, sincronizados no sombra como untracked; os três campos de assinatura continuam placeholders até o SIGN — e o LAND aborta no G0/G1 sem o `.asc`, que é a garantia. |

Rodada 5 sobre o pacote curado.
