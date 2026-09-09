# Rodada 10 do re-pass da v1.4.0-rc.1 — candidato ab194c9 (2026-09-09 13:12 -03; 3 veredito(s) de 6)

- Parte 1: VERDICT: NO-GO — A condição DURA 14 aceita manifestos que acionam o fallback destrutivo, portanto o envelope ainda não é honesto nem suficiente para a rc.1.
- Parte 2: VERDICT: NO-GO — O envelope v36 omite três P1 concretos nesta superfície e ainda não é suficiente para assinar a rc.1.
- Parte 3: VERDICT: NO-GO — Condition 69’s leaf-only manifest cure misses a P1 ancestor-symlink escape affecting both doctor and uninstall.
- Parte 4: não executada
- Parte 5: não executada
- Parte 6: não executada
- Parte 7: não executada

Sem `RUNNER-OVERALL: rc=0`: esta rodada não é evidência de corte. Os achados entram no envelope
(v37+) e a rodada 11 roda sobre o candidato seguinte. Vereditos íntegros ao lado.
