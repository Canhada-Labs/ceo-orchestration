# Rodada 13 do re-pass da v1.4.0-rc.1 — candidato cbb27b6 (2026-09-10 04:50 -03; 6 veredito(s) de 7)

- Parte 1: VERDICT: NO-GO — O envelope congelado é insuficiente porque três P1 não condicionados afetam o caminho v1.3.0→rc.1 e exigem cura seguida de novo re-pass.
- Parte 2: VERDICT: NO-GO — A condição 75 e o aviso correspondente em INSTALL.md fazem uma afirmação universal refutada pelo próprio filtro do manifesto; o envelope precisa ser corrigido, re-hashado e submetido a novo re-pass antes da rc.1.
- Parte 3: SEM VEREDITO (runner saiu antes da decisão; ver transcript no arquivo completo)
- Parte 4: VERDICT: GO-WITH-CONDITIONS — No new P0/P1 is missing from the frozen envelope; the declared conditions are honest and sufficient for the stated copy-mode rc.1 cohort, with the smoke-trigger gap retained as a P2 follow-up.
- Parte 5: VERDICT: NO-GO — As condições 19, 27 e 70 prometem uma recuperação por `/resume` que não existe, e o diff acrescenta uma garantia falsa de orçamento, exigindo correção e novo re-pass antes da rc.1.
- Parte 6: VERDICT: NO-GO — Condition 28 omits a reproducible adopter-file deletion path, so the frozen envelope is insufficient for rc.1.
- Parte 7: VERDICT: NO-GO — The frozen envelope is materially false about `/resume` recovery and ceremony-lint removal detection, so rc.1 requires correction and a new re-pass.

Sem `RUNNER-OVERALL: rc=0`: esta rodada não é evidência de corte. Os achados entram no envelope
(v56+) e a rodada seguinte roda sobre o candidato seguinte. Vereditos íntegros ao lado.
