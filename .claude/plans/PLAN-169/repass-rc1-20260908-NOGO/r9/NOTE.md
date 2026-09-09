# Rodada 9 do re-pass da v1.4.0-rc.1 — candidato 67db623 (2026-09-09 10:31 -03; 6 veredito(s) de 6)

- Parte 1: VERDICT: NO-GO — The signed envelope omits two P1 adopter hazards and must be corrected before rc.1 is cut.
- Parte 2: VERDICT: NO-GO — A condição 61 ainda permite que proveniência malformada reative silenciosamente o CODEOWNERS e fornece uma mitigação incorreta para o opt-out deliberado.
- Parte 3: VERDICT: NO-GO — Condition 61 falsely credits the uninstaller with rejecting duplicate and symlinked manifests, leaving an undeclared P1 deletion path without `--force`.
- Parte 4: VERDICT: NO-GO — A P1 adopter-facing behavior contradiction is absent from the proposed signed conditions.
- Parte 5: VERDICT: NO-GO — O envelope contém uma condição P1 insuficiente e omite dois outros P1 que tornam a continuidade e a evidência forense falsas para caminhos legítimos de upgrade.
- Parte 6: VERDICT: NO-GO — The signed envelope is missing the P1 ownership, file-type, and symlink precondition for the newly claimed `audit-key` path.

Sem `RUNNER-OVERALL: rc=0`: esta rodada não é evidência de corte. Os achados entram no envelope
(v27+) e a rodada 10 roda sobre o candidato seguinte. Vereditos íntegros ao lado.
