# Rodada 11 do re-pass da v1.4.0-rc.1 — candidato 6df13ce (2026-09-09 14:21 -03; 7 veredito(s) de 7)

- Parte 1: VERDICT: NO-GO — O envelope omite uma falha P1 de `TMPDIR` que pode sobrescrever um arquivo customizado e interromper o upgrade antes de registrar o fracasso.
- Parte 2: VERDICT: NO-GO — O envelope omite o isolamento obrigatório das variáveis FMS e a condição 74 não cobre os arquivos que o installer realmente reescreve; ambos precisam ser corrigidos antes do corte da rc.1.
- Parte 3: VERDICT: NO-GO — The signed draft omits a P1 manifest-leaf precondition, allowing external provenance to drive `doctor.sh --repair` writes while shipped guidance claims that path is refused.
- Parte 4: VERDICT: NO-GO — The signed draft must add the standalone-commit condition before rc.1 because the new ledger checkpoint rail silently misclassifies a common compound staging-and-commit path.
- Parte 5: VERDICT: NO-GO — A condição 17 declara fechada uma rota ainda aberta, e dois P1 adicionais não constam do envelope assinado.
- Parte 6: VERDICT: NO-GO — Conditions 27 and 28 permit cross-project audit contamination and destructive takeover of adopter-authored state leaves, so the proposed signed envelope is not sufficient for rc.1.
- Parte 7: VERDICT: NO-GO — The signed envelope is not honest or sufficient because condition 70 overpromises continuity, condition 38 contradicts the shipped code, and the undeclared state-store isolation escape is P1.

Sem `RUNNER-OVERALL: rc=0`: esta rodada não é evidência de corte. Os achados entram no envelope
(v41+) e a rodada 12 roda sobre o candidato seguinte. Vereditos íntegros ao lado.
