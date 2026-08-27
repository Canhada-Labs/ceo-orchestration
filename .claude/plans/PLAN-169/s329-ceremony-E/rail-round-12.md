# Pacote E — rail codex rodada 12 (shadow-E curada do r11, 2026-08-27 ~17:15 -03)

Rail-Verdict: APPROVE
Comando: `codex exec review --uncommitted --skip-git-repo-check` na shadow-E após a cura do r11 (scratch via `_up_tmpbase`, trap fixo, settings.json um documento; unit 88/88; e2e 71/0 medido pelo finalize na worktree). Modelo `gpt-5.6`, esforço xhigh. Saída bruta: `<scratchpad 02edd09e>/rail-E-round-12.txt`.

## Achados

- **[P1] Regenerate and sign the sentinel for this exact diff** — o sentinel segue `TO-FILL-AT-SIGN` sem `.asc`, e a CÓPIA da sombra traz um `Patch-sha256` antigo. **Por construção, nos dois pontos:** a sombra é o estado pré-SIGN; o sentinel NÃO viaja no patch (o `finalize-E.sh` o reescreve no repositório vivo com Scope/`Patch-sha256`/`Patch-base` derivados dos bytes atuais — commit `chore(PLAN-169 s329-E): patch derivado…`), e o `OWNER-S329-E-SIGN.sh` preenche Anchor/Data/Approved-By e assina; o LAND recusa sem isso (G1/G2). Mesma disposição das rodadas 2, 3, 7 e 11.
- **Código:** nenhum achado. Rodada LIMPA sobre `scripts/upgrade.sh`, os dois testes, o `smoke-install.yml` composto e o `DESIGN-E.md` (§10–§16).

## Histórico da manhã (rodadas 6–12, sobre a sombra re-derivada após o land de C)

r6: 1 P1 real (cerimônia ignorada) → r7: 1 P1 real (`.env` não viajava) + 2 P2 → r8: 1 P1 real (inferido ≠ gravado) + 1 P2 → r9: 2 P1 + 1 P2 (postura SHARED não provável — arquitetura trocada: nenhum hook sem cerimônia dita) → r10: 1 P2 (`.env` malformado no template) → r11: 3 P2 (scratch, trap, settings um documento) → **r12: limpa**. Cada rodada com controle vermelho onde havia oráculo novo; unidade 49 → 88; e2e 51 → 71.

## Disposição

- Pacote assinável: o SIGN exige que o ÚLTIMO registro (este) seja APPROVE. Residuais declarados: OQ-E5 (`settings.user.json` defasado em 16 hooks não-deliberados — wave própria, fora do Scope); OQ-E1 (recusa hook a hook) alarga-se ao `.env` (DESIGN-E §12).
