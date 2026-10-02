# Rail — w-auditrace (PLAN-194 W2.0, cura da condição 67) — rodada 3 (FINAL, com anexo)

Rail-Round: 3
Rail-Subject-sha256: c864ff693b1b57cc7e664342030355aa1e9a190b9c5bcb9f9b1997879876b21b
Rail-Text-sha256: 4edf2639e961eb2f8756609608270d8f0279211d5c7170b1c225d59ea38cdf27
Rail-Verdict: DECLARED-P2
Rail-Findings: P0=0 P1=0 P2=4

## Lanes
- Codex 0.156.1 (read-only), rodada 3: NO-GO só por uma frase falsa do texto assinável sobre o estado do sidecar; nenhum P0.
- Refutador Claude, lente mecânica de kernel, rodada 3: APPROVE, 5 P2.
- Anexo (curas de texto e o SIGN na forma da W1): Codex NO-GO por outra frase explicativa sobre os verificadores; refutador Claude APPROVE com P2.
- Final: as frases explicativas sobre o comportamento dos verificadores foram REMOVIDAS do texto assinável (cura por remoção; patch, SIGN e harness inalterados). Codex, checagem final estreita sobre o diff de remoção: GO.

## P2 declarados
- Os abortos por «sentinel virou symlink» (passo 3 e passo 4) não imprimem a receita de restauração.
- O verificador de assinatura e o allowlist são lidos da árvore viva depois da bateria; mudá-los na bateria só gera AVISO.
- Não há conferência pós-commit de `HEAD:<sentinel>` e `HEAD:<sentinel>.asc` contra os blobs do índice.
- A mecânica posterior ao passo 4 (blob do índice, assinatura sobre o índice) não tem cenário negativo no harness.
