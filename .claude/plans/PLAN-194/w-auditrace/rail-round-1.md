# Rail — w-auditrace (PLAN-194 W2.0, cura da condição 67) — rodada 1

Rail-Round: 1
Rail-Subject-sha256: (patch da rodada 1, anterior; ver PROPOSED-AUDITRACE.md)
Rail-Verdict: REQUEST-CHANGES
Rail-Findings: P0=0 P1=1 P2=2

## Lanes
- Codex 0.156.1 (read-only): REQUEST-CHANGES — P1: o texto assinável descrevia de forma errada a falha parcial do marcador; P2: o censo aceitava gravadores com apelidos das primitivas; P2: o teste não provava intercalação entre tipos de gravador.

## Desfecho
- Os três achados foram curados na rodada 2 (afirmação corrigida; censo por AST que acusa apelidos; intercalação conferida por tipo).
