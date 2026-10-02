# Rail — w-auditrace (PLAN-194 W2.0, cura da condição 67) — rodada 2

Rail-Round: 2
Rail-Subject-sha256: e8d231e83e339ee3700c405505c002e6ec79e772b1cf52b547a989ce867b5080
Rail-Verdict: APPROVE
Rail-Findings: P0=0 P1=0 P2=17

## Lanes
- Codex 0.156.1 (read-only): APPROVE, «NENHUM ACHADO».
- Refutador Claude, lente cadeia HMAC e concorrência: APPROVE, 7 P2.
- Refutador Claude, lente mecânica da cerimônia de kernel: APPROVE, 10 P2.

## Desfecho
- Os P2 de maior risco foram curados na rodada 3 (teste da janela serial; tolerância zero para falha dos testes da cura; Rail-Text-sha256; evidência exigida commitada; recusa nomeada de cabeçalho estrutural; desfazer). Os demais foram declarados no texto assinável.
