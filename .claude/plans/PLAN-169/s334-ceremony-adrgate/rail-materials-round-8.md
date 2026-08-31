# wave-adrgate — rail de MATERIAIS rodada 8 (FINAL, S334)

Rail-Verdict: APPROVE

> APPROVE — no findings. At commit 2f030c1, _fin_captured=0 is
> initialized before the trap and becomes 1 only after _fin_restore is
> defined. All four scripts pass Bash syntax, ShellCheck warning-level,
> and ceremony lint with zero unwaived blocking findings.

Fechamento do rail de materiais: **8 rodadas, 20 defeitos reais**
(r1: 1P1+2P2 · r2: 4P1+4P2 · r3: 3P2 · r4: 3P2+redesenho · r5: 3 ·
r6: 1 · r7: 1), harness 22/0/0 SEM escape na árvore commitada. O rail
do PATCH fechou separado na rodada 2 (`rail-round-2.md`, APPROVE).
Saída bruta: `<scratchpad S334>/adrgate-materials-r8.txt`.
