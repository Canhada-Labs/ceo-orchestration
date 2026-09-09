# Rodada 8 do re-pass da v1.4.0-rc.1 — candidato cd08704 (2026-09-09 07:50 -03; 6 veredito(s) de 6)

- Parte 1: VERDICT: NO-GO — O envelope atual omite dois P1 que permitem, respectivamente, um upgrade parcial sem estado final e uma entrega incompleta registrada como sucesso.
- Parte 2: VERDICT: NO-GO — Antes da rc.1, a condição 5 precisa ser corrigida e a aceitação de registro malformado por `_codeowners_provenance` precisa ser curada ou declarada como condição DURA precisa.
- Parte 3: VERDICT: NO-GO — The envelope contains a false hard condition and omits a newly introduced blocking behavior in the advertised user profile.
- Parte 4: VERDICT: NO-GO — Condition 58 is demonstrably false and the shipped CHANGELOG makes an unimplemented restore-safety promise, so this candidate is not yet sufficient for rc.1 even with the proposed signed envelope.
- Parte 5: VERDICT: NO-GO — The declared payload-5 conditions are accurate, but they omit four P1 conditions required for an honest and sufficiently constrained rc.1 envelope.
- Parte 6: VERDICT: NO-GO — O envelope omite duas falhas P1 de concorrência que podem quebrar a nova cadeia HMAC por projeto sem adulteração.

Sem `RUNNER-OVERALL: rc=0`: esta rodada não é evidência de corte. Os achados entram no envelope
(v21+) e a rodada 9 roda sobre o candidato seguinte. Vereditos íntegros ao lado.
