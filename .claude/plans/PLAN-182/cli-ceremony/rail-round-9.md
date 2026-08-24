# Pair-rail — wave-cli, rodada 9 (confirmação; S326, 2026-08-24 17:10–17:3xZ)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre o clone-sombra com o
pacote curado das rodadas 1–8 (patch `Patch-sha256 fa78673e…`) e todos os materiais (SIGN com P0
novo, LAND com G0 de materiais rastreados + staging exato). `RAIL_RC=0`.

**Resumo do revisor (verbatim):** *"The guarded changes currently lack the repository-required signed
sentinel. The proposed signing workflow also has deterministic ordering and retry failures that
obstruct completing that authorization safely."*

| # | Sev | Achado | Verificação | Disposição |
|---|---|---|---|---|
| 1 | P1 | O sentinel ainda tem `TO-FILL-AT-SIGN` e não há `.asc`; edições em `.claude/hooks/**` e `.claude/governance/**` exigem sentinel assinado (AGENTS.md:84-91). | **Por construção** — é o estado PRÉ-assinatura; o G0/G1 do LAND abortam sem `.asc`. Não é acionável antes do Owner assinar. | Sem ação: é exatamente o que o SIGN produz e o LAND verifica. |
| 2 | P2 | O P0 do SIGN tolera materiais untracked, mas o LAND os exige rastreados; commitá-los DEPOIS de assinar muda o HEAD e o G3 aborta — o fluxo SIGN→LAND falharia deterministicamente nesse caso. | **CONFIRMADO** (no tree revisado os materiais estavam untracked; na árvore viva já foram commitados em `7d788ba`, mas nada VERIFICAVA a ordem). | **CURADO (pós-r9, no SIGN):** P0 exige os mesmos materiais/registros rastreados que o LAND (`git ls-files --error-unmatch`). |
| 3 | P2 | Se o GPG falhar no P4 (o "no pinentry" documentado), o P3 já reescreveu o sentinel; o re-run aborta no P0 por "modificação rastreada" e a recuperação é manual. | **CONFIRMADO.** | **CURADO (pós-r9, no SIGN):** em falha do gpg, o sentinel é restaurado do HEAD e o `.asc` parcial removido; a mensagem manda repetir o script do zero. |

**Critério de assinatura atingido:** nenhum achado no CONTEÚDO do patch (12 paths) desde a r7; r8 e
r9 só tocaram o fluxo dos scripts, curado com controles. As duas curas desta rodada alteram apenas o
`OWNER-S326-SIGN.sh` (não-canônico) e foram verificadas por `bash -n`, shellcheck, ceremony-lint e
controle do P0 na árvore viva. O próximo terminal pode assinar diretamente; se preferir uma rodada
extra sobre o SIGN alterado, o custo é ~10 min.
