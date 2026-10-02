# rail-round-2 — W1 do PLAN-194

Rail-Round: 2
Rail-Subject: .claude/plans/PLAN-194/wave-w1/w1.patch
Rail-Subject-sha256: ed767edbac205c644fc7dd5f06f917c5ee7b73bc91a910107a27fd93049b2d43
Rail-Verdict: FINDINGS
Rail-Findings: P0=0 P1=2 P2=16

## Triagem

- Codex (read-only): NO-GO — P1: a comparação do validate-governance perdia violações do mesmo grupo; P2: shellcheck podia ser omitido.
- Refutador Claude, lente CI e matriz: P1 — o item (d) do sentinel afirmava cobertura de medição inexistente; 5 P2.
- Refutador Claude, lente mecânica: APPROVE, 9 P2.
- Achado de classe na mesma noite (W3b.1): o parser do bloco verbatim do revisor encerrava a seção em qualquer «## ». Curado na rodada 3 com gramática fechada.
