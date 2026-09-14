---
plan: PLAN-169
release: v1.4.0 (GA)
attempt: repass-ga r5 (2026-09-13, S351)
status: NO-GO (1/7 escrita; parte 3 interrompida) — condição 52 falsa POR CAUSA do kit; cura de texto; r6
---

# Re-pass do GA v1.4.0 — tentativa r5 (NO-GO na parte 7; interrompida)

- **Candidato:** `168d29124439c186d3dd29e848d711d86481f209` (r4 + condição 63 SEM enumeração de sítios).
- **Lançado 22:00; interrompido 22:3x** depois de 6 vereditos, porque a parte 7 já tinha escrito NO-GO (o run não pode mais ser 7/7) e esperar a parte 3 só custava tempo. Evidência parcial em `~/.rc2-backup/repass-ga-20260913-NOGO-r5/` (com `runner-r5.log`); aqui os 6 vereditos, a proveniência parcial e o candidato.

## Vereditos

| Parte | Veredito |
|---|---|
| 1 `upgrade.sh` | **GO-WITH-CONDITIONS — a condição 63 sem enumeração PASSOU** (4.ª forma; as 3 anteriores caíram por listar sítios) |
| 2 | GO-WITH-CONDITIONS |
| 3 | (interrompida sem veredito; GWC em r2, r3, r4) |
| 4, 5, 6 | GO-WITH-CONDITIONS |
| 7 | **NO-GO — condição 52 falsa no candidato do GA** |

## O achado da parte 7, verificado (13/09, 22:2x)

A 52 (herdada da rc.1) dizia: «o piso é re-pinado no CENSO do candidato (127 neste), de modo que qualquer remoção falha o gate». Medido com o próprio `check-ceremony-script.py --list` em worktrees detached: **rc.1 = 127; candidato do GA = 130** — os três `.sh` do kit do corte (`OWNER-GA-CUT.sh`, `repass-ga/run-ga-repass.sh`, `test-ga-kit.sh`) entram no censo, e `DEFAULT_FLOOR` continua 127 ⇒ até três remoções passam. (A árvore VIVA dá 143 porque os `staged/` gitignorados de planos antigos são o ponto cego declarado do lint; o CI e o revisor medem o commit.) Defeito **auto-infligido pelo kit**, não pelo texto herdado: nenhum revisor das rodadas r1–r4 o pegou; o da r5 pegou.

**Cura (texto):** a 52 passa a dizer «127 = censo da rc.1; o candidato do GA acrescenta os três scripts do próprio kit: 130 contra piso 127, logo até três remoções passam pelo gate até o re-pin seguinte — neste candidato o gate NÃO é fail-closed por contagem». Re-pinar o piso seria edição de gate script (cerimônia) e mudaria bytes entregues: fica para a 1.4.1 (o residual «pinar o conjunto exato de caminhos» já estava declarado).

**Lição para o derivador:** ao derivar um envelope de um candidato para outro, varrer as condições por claims que dependem da COMPOSIÇÃO da árvore (contagens, censos, «neste candidato»); o kit do GA muda o censo de scripts de cerimônia por construção.
