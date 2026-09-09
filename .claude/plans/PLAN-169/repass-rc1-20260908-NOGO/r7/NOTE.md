# Rodada 7 do re-pass da v1.4.0-rc.1 — candidato e92e74a (2026-09-09 04:35 -03; 3 veredito(s) de 6)

- Parte 1: VERDICT: NO-GO — O envelope atual omite a quebra P1 do perfil user e oferece uma checagem P1 de confinamento que não cobre vários escritores ativos do upgrader.
- Parte 2: VERDICT: NO-GO. O envelope v17 precisa curar ou declarar operacionalmente o tempfile previsível do deny-baseline antes de assinar a rc.1.
- Parte 3: VERDICT: NO-GO — Signed condition 16 is demonstrably false, and the restore parser plus advertised manual Codex gate add two undeclared P1 fail-open paths.
- Parte 4: não executada
- Parte 5: não executada
- Parte 6: não executada

Parte 4: o runner ABORTOU no controle de contagem de linhas do payload (2538 -> 2537) antes de
chamar o codex — o redator de saída aplica spans NFKC no texto original (item 58 do envelope);
partes 5 e 6 não chegaram a começar.

Sem `RUNNER-OVERALL: rc=0`: esta rodada não é evidência de corte. Os achados entram no envelope
(v18+) e a rodada 8 roda sobre o candidato seguinte. Vereditos íntegros ao lado.
